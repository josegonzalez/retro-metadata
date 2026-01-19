// Package hasheous provides the Hasheous metadata provider implementation.
// Hasheous is a service that matches ROM hashes to game metadata.
package hasheous

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/josegonzalez/retro-metadata/pkg/cache"
	"github.com/josegonzalez/retro-metadata/pkg/provider"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// HasheousTagRegex matches Hasheous ID tags in filenames like (hasheous-xxxxx)
var HasheousTagRegex = regexp.MustCompile(`(?i)\(hasheous-([a-f0-9-]+)\)`)

// API keys for client authentication
const (
	HasheousAPIKeyProduction = "JNoFBA-jEh4HbxuxEHM6MVzydKoAXs9eCcp2dvcg5LRCnpp312voiWmjuaIssSzS"
	HasheousAPIKeyDev        = "UUvh9ef_CddMM4xXO1iqxl9FqEt764v33LU-UiGFc0P34odXjMP9M6MTeE4JZRxZ"
)

// API URLs
const (
	HasheousProductionURL = "https://hasheous.org/api/v1"
	HasheousBetaURL       = "https://beta.hasheous.org/api/v1"
)

// Provider implements the Hasheous metadata provider.
type Provider struct {
	*provider.BaseProvider
	baseURL    string
	apiKey     string
	userAgent  string
	httpClient *http.Client
	devMode    bool
}

// NewProvider creates a new Hasheous provider instance.
func NewProvider(config retrometadata.ProviderConfig, c cache.Cache) (*Provider, error) {
	return NewProviderWithMode(config, c, false)
}

// NewProviderWithMode creates a new Hasheous provider with dev mode option.
func NewProviderWithMode(config retrometadata.ProviderConfig, c cache.Cache, devMode bool) (*Provider, error) {
	baseURL := HasheousProductionURL
	apiKey := HasheousAPIKeyProduction
	if devMode {
		baseURL = HasheousBetaURL
		apiKey = HasheousAPIKeyDev
	}

	p := &Provider{
		BaseProvider: provider.NewBaseProvider("hasheous", config, c),
		baseURL:      baseURL,
		apiKey:       apiKey,
		userAgent:    "retro-metadata/1.0",
		httpClient:   &http.Client{Timeout: 30 * time.Second},
		devMode:      devMode,
	}
	p.SetMinSimilarityScore(0.6)
	return p, nil
}

func (p *Provider) request(ctx context.Context, method, endpoint string, params map[string]string, body interface{}) (interface{}, error) {
	u, err := url.Parse(p.baseURL + endpoint)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL: %w", err)
	}

	if params != nil {
		q := u.Query()
		for k, v := range params {
			q.Set(k, v)
		}
		u.RawQuery = q.Encode()
	}

	var bodyReader io.Reader
	if body != nil {
		bodyBytes, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal body: %w", err)
		}
		bodyReader = bytes.NewReader(bodyBytes)
	}

	req, err := http.NewRequestWithContext(ctx, method, u.String(), bodyReader)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("User-Agent", p.userAgent)
	req.Header.Set("Accept", "application/json")
	req.Header.Set("Content-Type", "application/json-patch+json")
	req.Header.Set("X-Client-API-Key", p.apiKey)

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderConnection}
	}
	defer resp.Body.Close()

	if resp.StatusCode == 429 {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderRateLimit}
	}

	if resp.StatusCode == 404 {
		return nil, nil
	}

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result interface{}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return result, nil
}

// Search searches for games by name.
// Note: Hasheous primarily works with hashes, not name searches.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	params := map[string]string{"q": query}
	if opts.PlatformID != nil {
		params["platform"] = strconv.Itoa(*opts.PlatformID)
	}

	result, err := p.request(ctx, "GET", "/search", params, nil)
	if err != nil {
		return nil, err
	}

	games, ok := result.([]interface{})
	if !ok {
		return nil, nil
	}

	limit := opts.Limit
	if limit == 0 {
		limit = 20
	}

	var searchResults []retrometadata.SearchResult
	for i, g := range games {
		if i >= limit {
			break
		}
		game, ok := g.(map[string]interface{})
		if !ok {
			continue
		}

		gameID := getString(game, "id")
		if gameID == "" {
			continue
		}

		sr := retrometadata.SearchResult{
			Provider:   p.Name(),
			ProviderID: getInt(game, "id"),
			Name:       getString(game, "name"),
			CoverURL:   getString(game, "cover_url"),
		}

		if platforms, ok := game["platforms"].([]interface{}); ok {
			for _, pl := range platforms {
				if plStr, ok := pl.(string); ok {
					sr.Platforms = append(sr.Platforms, plStr)
				}
			}
		}

		searchResults = append(searchResults, sr)
	}

	return searchResults, nil
}

// GetByID gets game details by Hasheous ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	result, err := p.request(ctx, "GET", fmt.Sprintf("/games/%d", gameID), nil, nil)
	if err != nil {
		return nil, err
	}

	game, ok := result.(map[string]interface{})
	if !ok {
		return nil, nil
	}

	return p.buildGameResult(game), nil
}

// LookupByHash looks up a game by ROM hash.
func (p *Provider) LookupByHash(ctx context.Context, md5, sha1, crc string, returnAllSources bool) (map[string]interface{}, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	if md5 == "" && sha1 == "" && crc == "" {
		return nil, nil
	}

	// Build request data with Hasheous's expected field names
	hashes := make(map[string]string)
	if md5 != "" {
		hashes["mD5"] = md5
	}
	if sha1 != "" {
		hashes["shA1"] = sha1
	}
	if crc != "" {
		hashes["crc"] = crc
	}

	params := map[string]string{
		"returnAllSources": fmt.Sprintf("%v", returnAllSources),
		"returnFields":     "Signatures, Metadata, Attributes",
	}

	result, err := p.request(ctx, "POST", "/Lookup/ByHash", params, hashes)
	if err != nil {
		return nil, err
	}

	resultMap, ok := result.(map[string]interface{})
	if !ok {
		return nil, nil
	}

	return resultMap, nil
}

// IdentifyByHash implements the HashProvider interface for hash-based identification.
func (p *Provider) IdentifyByHash(ctx context.Context, hashes retrometadata.FileHashes, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	result, err := p.LookupByHash(ctx, hashes.MD5, hashes.SHA1, hashes.CRC32, true)
	if err != nil || result == nil {
		return nil, err
	}

	// Try to get IGDB game data
	igdbGame, err := p.GetIGDBGame(ctx, result)
	if err == nil && igdbGame != nil {
		return p.buildGameResultFromIGDB(igdbGame), nil
	}

	// Fall back to basic result
	return p.buildGameResultFromHashLookup(result), nil
}

// GetIGDBGame gets IGDB game data through Hasheous proxy.
func (p *Provider) GetIGDBGame(ctx context.Context, hasheousResult map[string]interface{}) (map[string]interface{}, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	// Check for IGDB ID in the Hasheous result
	var igdbID int

	// Look in metadata list
	if metadataList, ok := hasheousResult["metadata"].([]interface{}); ok {
		for _, meta := range metadataList {
			if metaMap, ok := meta.(map[string]interface{}); ok {
				if getString(metaMap, "source") == "IGDB" {
					igdbID = getInt(metaMap, "immutableId")
					break
				}
			}
		}
	}

	// Also check direct igdb_id field
	if igdbID == 0 {
		igdbID = getInt(hasheousResult, "igdb_id")
	}
	if igdbID == 0 {
		igdbID = getInt(hasheousResult, "igdbId")
	}

	if igdbID == 0 {
		return nil, nil
	}

	// Fetch IGDB data through Hasheous proxy
	params := map[string]string{
		"Id":            strconv.Itoa(igdbID),
		"expandColumns": "age_ratings, alternative_names, collections, cover, dlcs, expanded_games, franchise, franchises, game_modes, genres, involved_companies, platforms, ports, remakes, screenshots, similar_games, videos",
	}

	result, err := p.request(ctx, "GET", "/MetadataProxy/IGDB/Game", params, nil)
	if err != nil {
		return nil, err
	}

	resultMap, ok := result.(map[string]interface{})
	if !ok {
		return nil, nil
	}

	return resultMap, nil
}

// GetRAGame gets RetroAchievements game data through Hasheous proxy.
func (p *Provider) GetRAGame(ctx context.Context, hasheousResult map[string]interface{}) (map[string]interface{}, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	// Check for RetroAchievements ID in the Hasheous result
	var raID int

	// Look in metadata list
	if metadataList, ok := hasheousResult["metadata"].([]interface{}); ok {
		for _, meta := range metadataList {
			if metaMap, ok := meta.(map[string]interface{}); ok {
				if getString(metaMap, "source") == "RetroAchievements" {
					raID = getInt(metaMap, "immutableId")
					break
				}
			}
		}
	}

	// Also check direct ra_id field
	if raID == 0 {
		raID = getInt(hasheousResult, "ra_id")
	}
	if raID == 0 {
		raID = getInt(hasheousResult, "retroAchievementsId")
	}

	if raID == 0 {
		return nil, nil
	}

	// Fetch RA data through Hasheous proxy
	result, err := p.request(ctx, "GET", "/MetadataProxy/RA/Game", map[string]string{"Id": strconv.Itoa(raID)}, nil)
	if err != nil {
		return nil, err
	}

	resultMap, ok := result.(map[string]interface{})
	if !ok {
		return nil, nil
	}

	return resultMap, nil
}

// GetSignatureMatches extracts signature matching flags from Hasheous lookup result.
func (p *Provider) GetSignatureMatches(hasheousResult map[string]interface{}) map[string]bool {
	matches := map[string]bool{
		"tosec_match":       false,
		"nointro_match":     false,
		"redump_match":      false,
		"mame_arcade_match": false,
		"mame_mess_match":   false,
		"whdload_match":     false,
		"ra_match":          false,
		"fbneo_match":       false,
		"puredos_match":     false,
	}

	signatures, ok := hasheousResult["signatures"].(map[string]interface{})
	if !ok {
		return matches
	}

	signatureKeys := make(map[string]bool)
	for key := range signatures {
		signatureKeys[key] = true
	}

	matches["tosec_match"] = signatureKeys["TOSEC"]
	matches["nointro_match"] = signatureKeys["NoIntros"]
	matches["redump_match"] = signatureKeys["Redump"]
	matches["mame_arcade_match"] = signatureKeys["MAMEArcade"]
	matches["mame_mess_match"] = signatureKeys["MAMEMess"]
	matches["whdload_match"] = signatureKeys["WHDLoad"]
	matches["ra_match"] = signatureKeys["RetroAchievements"]
	matches["fbneo_match"] = signatureKeys["FBNeo"]
	matches["puredos_match"] = signatureKeys["PureDOS"]

	return matches
}

// Identify identifies a game from a ROM filename.
// Note: Hasheous works best with hash lookups rather than filename matching.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	// Check for Hasheous ID tag in filename
	if match := HasheousTagRegex.FindStringSubmatch(filename); len(match) > 1 {
		if id, err := strconv.Atoi(match[1]); err == nil {
			result, err := p.GetByID(ctx, id)
			if err == nil && result != nil {
				return result, nil
			}
		}
	}

	// Hasheous primarily works with hashes, so name-based identification
	// has limited functionality. Try a search instead.
	searchTerm := cleanFilename(filename)
	platformID := 0
	if opts.PlatformID != nil {
		platformID = *opts.PlatformID
	}

	results, err := p.Search(ctx, searchTerm, retrometadata.SearchOptions{
		PlatformID: &platformID,
		Limit:      10,
	})
	if err != nil || len(results) == 0 {
		return nil, err
	}

	// Find best match
	gamesByName := make(map[string]retrometadata.SearchResult)
	var names []string
	for _, r := range results {
		gamesByName[r.Name] = r
		names = append(names, r.Name)
	}

	bestMatch, score := p.FindBestMatch(searchTerm, names)

	if bestMatch != "" {
		if sr, ok := gamesByName[bestMatch]; ok {
			// Get full details
			fullResult, err := p.GetByID(ctx, sr.ProviderID)
			if err == nil && fullResult != nil {
				fullResult.MatchScore = score
				return fullResult, nil
			}
		}
	}

	return nil, nil
}

// Heartbeat checks if the provider API is accessible.
func (p *Provider) Heartbeat(ctx context.Context) error {
	_, err := p.request(ctx, "GET", "/search", map[string]string{"q": "test"}, nil)
	return err
}

func (p *Provider) buildGameResult(game map[string]interface{}) *retrometadata.GameResult {
	providerID := getInt(game, "id")
	result := &retrometadata.GameResult{
		Provider:    p.Name(),
		ProviderID:  &providerID,
		ProviderIDs: map[string]int{"hasheous": providerID},
		Name:        coalesce(getString(game, "name"), getString(game, "title")),
		Summary:     coalesce(getString(game, "description"), getString(game, "overview")),
		RawResponse: game,
		Artwork: retrometadata.Artwork{
			CoverURL: coalesce(getString(game, "cover_url"), getString(game, "boxart")),
		},
	}

	if screenshots, ok := game["screenshots"].([]interface{}); ok {
		for _, s := range screenshots {
			if sStr, ok := s.(string); ok {
				result.Artwork.ScreenshotURLs = append(result.Artwork.ScreenshotURLs, sStr)
			}
		}
	}

	result.Metadata = p.extractMetadata(game)
	return result
}

func (p *Provider) buildGameResultFromHashLookup(result map[string]interface{}) *retrometadata.GameResult {
	gameResult := &retrometadata.GameResult{
		Provider:    p.Name(),
		RawResponse: result,
	}

	// Extract basic info from signatures if available
	if signatures, ok := result["signatures"].(map[string]interface{}); ok {
		for source, data := range signatures {
			if dataMap, ok := data.(map[string]interface{}); ok {
				if gameResult.Name == "" {
					gameResult.Name = getString(dataMap, "name")
				}
				if gameResult.Summary == "" {
					gameResult.Summary = getString(dataMap, "description")
				}
				// Store signature source in provider IDs
				if gameResult.ProviderIDs == nil {
					gameResult.ProviderIDs = make(map[string]int)
				}
				gameResult.ProviderIDs[source] = 1 // Mark as matched
			}
		}
	}

	return gameResult
}

func (p *Provider) buildGameResultFromIGDB(game map[string]interface{}) *retrometadata.GameResult {
	providerID := getInt(game, "id")
	result := &retrometadata.GameResult{
		Provider:    "igdb",
		ProviderID:  &providerID,
		ProviderIDs: map[string]int{"igdb": providerID},
		Name:        getString(game, "name"),
		Summary:     getString(game, "summary"),
		Slug:        getString(game, "slug"),
		RawResponse: game,
	}

	// Extract cover
	if cover, ok := game["cover"].(map[string]interface{}); ok {
		url := getString(cover, "url")
		if url != "" {
			// Normalize cover URL
			if strings.HasPrefix(url, "//") {
				url = "https:" + url
			}
			url = strings.Replace(url, "t_thumb", "t_1080p", 1)
			result.Artwork.CoverURL = url
		}
	}

	// Extract screenshots
	if screenshots, ok := game["screenshots"].([]interface{}); ok {
		for _, s := range screenshots {
			if sMap, ok := s.(map[string]interface{}); ok {
				url := getString(sMap, "url")
				if url != "" {
					if strings.HasPrefix(url, "//") {
						url = "https:" + url
					}
					url = strings.Replace(url, "t_thumb", "t_720p", 1)
					result.Artwork.ScreenshotURLs = append(result.Artwork.ScreenshotURLs, url)
				}
			}
		}
	}

	// Extract metadata
	result.Metadata = p.extractIGDBMetadata(game)

	return result
}

func (p *Provider) extractMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	metadata := retrometadata.GameMetadata{
		RawData: game,
	}

	// Genres
	if genres, ok := game["genres"].([]interface{}); ok {
		for _, g := range genres {
			if gStr, ok := g.(string); ok {
				metadata.Genres = append(metadata.Genres, gStr)
			}
		}
	} else if genreStr := getString(game, "genres"); genreStr != "" {
		for _, g := range strings.Split(genreStr, ",") {
			metadata.Genres = append(metadata.Genres, strings.TrimSpace(g))
		}
	}

	// Companies
	if publisher := getString(game, "publisher"); publisher != "" {
		metadata.Companies = append(metadata.Companies, publisher)
		metadata.Publisher = publisher
	}
	if developer := getString(game, "developer"); developer != "" {
		found := false
		for _, c := range metadata.Companies {
			if c == developer {
				found = true
				break
			}
		}
		if !found {
			metadata.Companies = append(metadata.Companies, developer)
		}
		metadata.Developer = developer
	}

	// Player count
	if players := getInt(game, "players"); players > 0 {
		metadata.PlayerCount = strconv.Itoa(players)
	}

	// Release year
	releaseDate := getString(game, "release_date")
	if releaseDate == "" {
		releaseDate = getString(game, "year")
	}
	if releaseDate != "" {
		if len(releaseDate) >= 4 {
			if year, err := strconv.Atoi(releaseDate[:4]); err == nil {
				metadata.ReleaseYear = &year
			}
		}
	}

	return metadata
}

func (p *Provider) extractIGDBMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	metadata := retrometadata.GameMetadata{
		RawData: game,
	}

	// Genres
	if genres, ok := game["genres"].([]interface{}); ok {
		for _, g := range genres {
			if gMap, ok := g.(map[string]interface{}); ok {
				if name := getString(gMap, "name"); name != "" {
					metadata.Genres = append(metadata.Genres, name)
				}
			}
		}
	}

	// Franchises
	if franchise, ok := game["franchise"].(map[string]interface{}); ok {
		if name := getString(franchise, "name"); name != "" {
			metadata.Franchises = append(metadata.Franchises, name)
		}
	}
	if franchises, ok := game["franchises"].([]interface{}); ok {
		for _, f := range franchises {
			if fMap, ok := f.(map[string]interface{}); ok {
				if name := getString(fMap, "name"); name != "" {
					metadata.Franchises = append(metadata.Franchises, name)
				}
			}
		}
	}

	// Collections
	if collections, ok := game["collections"].([]interface{}); ok {
		for _, c := range collections {
			if cMap, ok := c.(map[string]interface{}); ok {
				if name := getString(cMap, "name"); name != "" {
					metadata.Collections = append(metadata.Collections, name)
				}
			}
		}
	}

	// Companies
	if companies, ok := game["involved_companies"].([]interface{}); ok {
		for _, ic := range companies {
			if icMap, ok := ic.(map[string]interface{}); ok {
				if company, ok := icMap["company"].(map[string]interface{}); ok {
					if name := getString(company, "name"); name != "" {
						metadata.Companies = append(metadata.Companies, name)
					}
				}
			}
		}
	}

	// Rating
	if rating := getFloat64(game, "total_rating"); rating > 0 {
		metadata.TotalRating = &rating
	}

	// First release date
	if timestamp := getFloat64(game, "first_release_date"); timestamp > 0 {
		ts := int64(timestamp)
		metadata.FirstReleaseDate = &ts
	}

	return metadata
}

func cleanFilename(filename string) string {
	// Remove extension
	name := regexp.MustCompile(`\.[^.]+$`).ReplaceAllString(filename, "")
	// Remove common tags like (USA), [!], etc.
	name = regexp.MustCompile(`\s*[\(\[][^\)\]]*[\)\]]`).ReplaceAllString(name, "")
	return strings.TrimSpace(name)
}

func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key]; ok {
		switch val := v.(type) {
		case string:
			return val
		case float64:
			return strconv.FormatFloat(val, 'f', -1, 64)
		case int:
			return strconv.Itoa(val)
		}
	}
	return ""
}

func getInt(m map[string]interface{}, key string) int {
	if v, ok := m[key]; ok {
		switch val := v.(type) {
		case float64:
			return int(val)
		case int:
			return val
		case string:
			if i, err := strconv.Atoi(val); err == nil {
				return i
			}
		}
	}
	return 0
}

func getFloat64(m map[string]interface{}, key string) float64 {
	if v, ok := m[key]; ok {
		if f, ok := v.(float64); ok {
			return f
		}
	}
	return 0
}

func coalesce(values ...string) string {
	for _, v := range values {
		if v != "" {
			return v
		}
	}
	return ""
}

func init() {
	// Register the provider factory
	retrometadata.RegisterProvider("hasheous", func(config retrometadata.ProviderConfig, c cache.Cache) (retrometadata.Provider, error) {
		return NewProvider(config, c)
	})
}
