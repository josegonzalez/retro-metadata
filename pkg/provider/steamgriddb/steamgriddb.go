// Package steamgriddb provides artwork from SteamGridDB.
package steamgriddb

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"

	retrometadata "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// SGDBDimension represents SteamGridDB grid dimension options.
type SGDBDimension string

const (
	// Vertical grids
	DimSteamVertical SGDBDimension = "600x900"
	DimGOGGalaxy     SGDBDimension = "342x482"
	DimSquare        SGDBDimension = "512x512"
	DimSquareIcon    SGDBDimension = "256x256"

	// Horizontal grids
	DimSteamHorizontal SGDBDimension = "460x215"
	DimLegacy          SGDBDimension = "920x430"
	DimOld             SGDBDimension = "460x215"

	// Heroes
	DimHeroBlurred  SGDBDimension = "1920x620"
	DimHeroMaterial SGDBDimension = "3840x1240"

	// Logos
	DimLogoCustom SGDBDimension = "custom"
)

// SGDBStyle represents SteamGridDB artwork style options.
type SGDBStyle string

const (
	// Grid styles
	StyleAlternate SGDBStyle = "alternate"
	StyleBlurred   SGDBStyle = "blurred"
	StyleWhiteLogo SGDBStyle = "white_logo"
	StyleMaterial  SGDBStyle = "material"
	StyleNoLogo    SGDBStyle = "no_logo"

	// Logo styles
	StyleLogoOfficial SGDBStyle = "official"
	StyleLogoWhite    SGDBStyle = "white"
	StyleLogoBlack    SGDBStyle = "black"
	StyleLogoCustom   SGDBStyle = "custom"
)

// SGDBMime represents SteamGridDB MIME type options.
type SGDBMime string

const (
	MimePNG  SGDBMime = "image/png"
	MimeJPEG SGDBMime = "image/jpeg"
	MimeWEBP SGDBMime = "image/webp"
	MimeICO  SGDBMime = "image/vnd.microsoft.icon"
)

var (
	// Regex to detect SteamGridDB ID tags in filenames like (sgdb-12345)
	sgdbTagRegex = regexp.MustCompile(`(?i)\(sgdb-(\d+)\)`)

	// ErrProviderDisabled is returned when the provider is disabled.
	ErrProviderDisabled = fmt.Errorf("provider is disabled")
)

// Provider implements the SteamGridDB artwork provider.
type Provider struct {
	config    *retrometadata.ProviderConfig
	client    *http.Client
	baseURL   string
	userAgent string
	nsfw      bool
	humor     bool
	epilepsy  bool
}

// New creates a new SteamGridDB provider.
func New(config *retrometadata.ProviderConfig) *Provider {
	timeout := time.Duration(config.Timeout) * time.Second
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	p := &Provider{
		config:    config,
		client:    &http.Client{Timeout: timeout},
		baseURL:   "https://www.steamgriddb.com/api/v2",
		userAgent: "retro-metadata/1.0",
		nsfw:      false,
		humor:     true,
		epilepsy:  true,
	}

	// Check options for content filters
	if config.Options != nil {
		if nsfw, ok := config.Options["nsfw"].(bool); ok {
			p.nsfw = nsfw
		}
		if humor, ok := config.Options["humor"].(bool); ok {
			p.humor = humor
		}
		if epilepsy, ok := config.Options["epilepsy"].(bool); ok {
			p.epilepsy = epilepsy
		}
	}

	return p
}

// Name returns the provider name.
func (p *Provider) Name() string {
	return "steamgriddb"
}

func (p *Provider) apiKey() string {
	return p.config.GetCredential("api_key")
}

func (p *Provider) request(ctx context.Context, endpoint string, params url.Values) (map[string]interface{}, error) {
	reqURL := p.baseURL + endpoint
	if params != nil && len(params) > 0 {
		reqURL += "?" + params.Encode()
	}

	req, err := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", p.userAgent)
	req.Header.Set("Authorization", "Bearer "+p.apiKey())

	resp, err := p.client.Do(req)
	if err != nil {
		return nil, retrometadata.NewProviderError(p.Name(), "request", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		return nil, &retrometadata.AuthError{Provider: p.Name(), Details: "invalid API key"}
	}
	if resp.StatusCode == http.StatusTooManyRequests {
		return nil, &retrometadata.RateLimitError{Provider: p.Name()}
	}
	if resp.StatusCode != http.StatusOK {
		return nil, &retrometadata.ConnectionError{Provider: p.Name(), Details: fmt.Sprintf("HTTP %d", resp.StatusCode)}
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	return result, nil
}

func (p *Provider) buildFilterParams(dimensions []SGDBDimension, styles []SGDBStyle, mimes []SGDBMime) url.Values {
	params := url.Values{}

	// Content filters
	if p.nsfw {
		params.Set("nsfw", "any")
	} else {
		params.Set("nsfw", "false")
	}
	if p.humor {
		params.Set("humor", "any")
	} else {
		params.Set("humor", "false")
	}
	if p.epilepsy {
		params.Set("epilepsy", "any")
	} else {
		params.Set("epilepsy", "false")
	}

	if len(dimensions) > 0 {
		var dims []string
		for _, d := range dimensions {
			dims = append(dims, string(d))
		}
		params.Set("dimensions", strings.Join(dims, ","))
	}
	if len(styles) > 0 {
		var stys []string
		for _, s := range styles {
			stys = append(stys, string(s))
		}
		params.Set("styles", strings.Join(stys, ","))
	}
	if len(mimes) > 0 {
		var ms []string
		for _, m := range mimes {
			ms = append(ms, string(m))
		}
		params.Set("mimes", strings.Join(ms, ","))
	}

	return params
}

func (p *Provider) fetchGrids(ctx context.Context, gameID int) ([]map[string]interface{}, error) {
	params := p.buildFilterParams(nil, nil, nil)
	result, err := p.request(ctx, fmt.Sprintf("/grids/game/%d", gameID), params)
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return nil, nil
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, nil
	}

	var grids []map[string]interface{}
	for _, item := range data {
		if grid, ok := item.(map[string]interface{}); ok {
			grids = append(grids, grid)
		}
	}
	return grids, nil
}

func (p *Provider) fetchHeroes(ctx context.Context, gameID int) ([]map[string]interface{}, error) {
	params := p.buildFilterParams(nil, nil, nil)
	result, err := p.request(ctx, fmt.Sprintf("/heroes/game/%d", gameID), params)
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return nil, nil
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, nil
	}

	var heroes []map[string]interface{}
	for _, item := range data {
		if hero, ok := item.(map[string]interface{}); ok {
			heroes = append(heroes, hero)
		}
	}
	return heroes, nil
}

func (p *Provider) fetchLogos(ctx context.Context, gameID int) ([]map[string]interface{}, error) {
	params := p.buildFilterParams(nil, nil, nil)
	result, err := p.request(ctx, fmt.Sprintf("/logos/game/%d", gameID), params)
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return nil, nil
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, nil
	}

	var logos []map[string]interface{}
	for _, item := range data {
		if logo, ok := item.(map[string]interface{}); ok {
			logos = append(logos, logo)
		}
	}
	return logos, nil
}

func (p *Provider) fetchIcons(ctx context.Context, gameID int) ([]map[string]interface{}, error) {
	params := p.buildFilterParams(nil, nil, nil)
	result, err := p.request(ctx, fmt.Sprintf("/icons/game/%d", gameID), params)
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return nil, nil
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, nil
	}

	var icons []map[string]interface{}
	for _, item := range data {
		if icon, ok := item.(map[string]interface{}); ok {
			icons = append(icons, icon)
		}
	}
	return icons, nil
}

func (p *Provider) fetchAllArtwork(ctx context.Context, gameID int) retrometadata.Artwork {
	artwork := retrometadata.Artwork{}

	// Fetch grids (covers)
	if grids, err := p.fetchGrids(ctx, gameID); err == nil && len(grids) > 0 {
		if url, ok := grids[0]["url"].(string); ok {
			artwork.CoverURL = url
		}
	}

	// Fetch heroes (banners/backgrounds)
	if heroes, err := p.fetchHeroes(ctx, gameID); err == nil && len(heroes) > 0 {
		if url, ok := heroes[0]["url"].(string); ok {
			artwork.BackgroundURL = url
		}
		if len(heroes) > 1 {
			if url, ok := heroes[1]["url"].(string); ok {
				artwork.BannerURL = url
			}
		}
	}

	// Fetch logos
	if logos, err := p.fetchLogos(ctx, gameID); err == nil && len(logos) > 0 {
		if url, ok := logos[0]["url"].(string); ok {
			artwork.LogoURL = url
		}
	}

	// Fetch icons
	if icons, err := p.fetchIcons(ctx, gameID); err == nil && len(icons) > 0 {
		if url, ok := icons[0]["url"].(string); ok {
			artwork.IconURL = url
		}
	}

	return artwork
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	result, err := p.request(ctx, "/search/autocomplete/"+url.PathEscape(query), nil)
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return nil, nil
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, nil
	}

	limit := opts.Limit
	if limit == 0 {
		limit = 10
	}

	var results []retrometadata.SearchResult
	for i, item := range data {
		if i >= limit {
			break
		}

		game, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		gameID := int(getFloat64(game, "id"))
		if gameID == 0 {
			continue
		}

		// Try to get cover image
		coverURL := ""
		if grids, err := p.fetchGrids(ctx, gameID); err == nil && len(grids) > 0 {
			if url, ok := grids[0]["url"].(string); ok {
				coverURL = url
			}
		}

		var releaseYear *int
		if year, ok := game["release_date"].(float64); ok && year > 0 {
			y := int(year)
			releaseYear = &y
		}

		results = append(results, retrometadata.SearchResult{
			Name:        getString(game, "name"),
			Provider:    p.Name(),
			ProviderID:  gameID,
			CoverURL:    coverURL,
			ReleaseYear: releaseYear,
		})
	}

	return results, nil
}

// GetByID gets game artwork by SteamGridDB ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	result, err := p.request(ctx, fmt.Sprintf("/games/id/%d", gameID), nil)
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return nil, nil
	}

	game, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, nil
	}

	artwork := p.fetchAllArtwork(ctx, gameID)

	providerID := gameID
	return &retrometadata.GameResult{
		Name:       getString(game, "name"),
		Provider:   p.Name(),
		ProviderID: &providerID,
		ProviderIDs: map[string]int{
			"steamgriddb": gameID,
		},
		Artwork: artwork,
		Metadata: retrometadata.GameMetadata{
			ReleaseYear: getIntPtr(game, "release_date"),
		},
		RawResponse: game,
	}, nil
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	// Check for SteamGridDB ID tag in filename
	if matches := sgdbTagRegex.FindStringSubmatch(filename); len(matches) > 1 {
		var taggedID int
		if _, err := fmt.Sscanf(matches[1], "%d", &taggedID); err == nil {
			result, err := p.GetByID(ctx, taggedID)
			if err == nil && result != nil {
				return result, nil
			}
		}
	}

	// Clean the filename
	searchTerm := cleanFilename(filename)

	// Search for the game
	result, err := p.request(ctx, "/search/autocomplete/"+url.PathEscape(searchTerm), nil)
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return nil, nil
	}

	data, ok := result["data"].([]interface{})
	if !ok || len(data) == 0 {
		return nil, nil
	}

	// Build name to game map
	gamesByName := make(map[string]map[string]interface{})
	for _, item := range data {
		if game, ok := item.(map[string]interface{}); ok {
			if name := getString(game, "name"); name != "" {
				gamesByName[name] = game
			}
		}
	}

	// Find best match
	var names []string
	for name := range gamesByName {
		names = append(names, name)
	}

	bestMatch, score := findBestMatch(searchTerm, names)
	if bestMatch == "" {
		return nil, nil
	}

	game := gamesByName[bestMatch]
	gameID := int(getFloat64(game, "id"))

	artwork := p.fetchAllArtwork(ctx, gameID)

	providerID := gameID
	return &retrometadata.GameResult{
		Name:       getString(game, "name"),
		Provider:   p.Name(),
		ProviderID: &providerID,
		ProviderIDs: map[string]int{
			"steamgriddb": gameID,
		},
		Artwork: artwork,
		Metadata: retrometadata.GameMetadata{
			ReleaseYear: getIntPtr(game, "release_date"),
		},
		MatchScore:  score,
		RawResponse: game,
	}, nil
}

// GetArtworkForSteamID gets artwork using a Steam App ID.
func (p *Provider) GetArtworkForSteamID(ctx context.Context, steamAppID int) (retrometadata.Artwork, error) {
	if !p.config.Enabled {
		return retrometadata.Artwork{}, nil
	}

	result, err := p.request(ctx, fmt.Sprintf("/games/steam/%d", steamAppID), nil)
	if err != nil {
		return retrometadata.Artwork{}, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		return retrometadata.Artwork{}, nil
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return retrometadata.Artwork{}, nil
	}

	gameID := int(getFloat64(data, "id"))
	return p.fetchAllArtwork(ctx, gameID), nil
}

// Heartbeat checks if the provider is available.
func (p *Provider) Heartbeat(ctx context.Context) error {
	if !p.config.Enabled {
		return ErrProviderDisabled
	}

	// Try a simple search to check connectivity
	_, err := p.request(ctx, "/search/autocomplete/test", nil)
	return err
}

// Close closes the provider.
func (p *Provider) Close() error {
	return nil
}

// Helper functions

func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}

func getFloat64(m map[string]interface{}, key string) float64 {
	if v, ok := m[key].(float64); ok {
		return v
	}
	return 0
}

func getIntPtr(m map[string]interface{}, key string) *int {
	if v, ok := m[key].(float64); ok && v > 0 {
		i := int(v)
		return &i
	}
	return nil
}

func cleanFilename(filename string) string {
	// Remove extension
	name := regexp.MustCompile(`\.[^.]+$`).ReplaceAllString(filename, "")
	// Remove tags in parentheses/brackets
	name = regexp.MustCompile(`\s*[\(\[][^\)\]]*[\)\]]`).ReplaceAllString(name, "")
	return strings.TrimSpace(name)
}

func findBestMatch(query string, candidates []string) (string, float64) {
	if len(candidates) == 0 {
		return "", 0
	}

	// Simple similarity based on common prefix and lowercase comparison
	queryLower := strings.ToLower(query)
	bestMatch := ""
	bestScore := 0.0

	for _, candidate := range candidates {
		candidateLower := strings.ToLower(candidate)

		// Exact match
		if candidateLower == queryLower {
			return candidate, 1.0
		}

		// Contains match
		if strings.Contains(candidateLower, queryLower) || strings.Contains(queryLower, candidateLower) {
			score := float64(len(queryLower)) / float64(max(len(queryLower), len(candidateLower)))
			if score > bestScore {
				bestScore = score
				bestMatch = candidate
			}
		}
	}

	if bestScore >= 0.6 {
		return bestMatch, bestScore
	}

	// Return first candidate as fallback
	return candidates[0], 0.5
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
