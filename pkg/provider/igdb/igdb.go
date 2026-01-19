// Package igdb provides the IGDB metadata provider implementation.
package igdb

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/josegonzalez/retro-metadata/pkg/cache"
	"github.com/josegonzalez/retro-metadata/pkg/internal/matching"
	"github.com/josegonzalez/retro-metadata/pkg/internal/normalization"
	"github.com/josegonzalez/retro-metadata/pkg/platform"
	"github.com/josegonzalez/retro-metadata/pkg/provider"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// IGDBTagRegex matches IGDB ID tags in filenames like (igdb-12345)
var IGDBTagRegex = regexp.MustCompile(`(?i)\(igdb-(\d+)\)`)

// gamesFields contains the fields to fetch for full game details
var gamesFields = []string{
	"id", "name", "slug", "summary", "total_rating", "aggregated_rating",
	"first_release_date", "cover.url", "screenshots.url", "platforms.id",
	"platforms.name", "alternative_names.name", "genres.name", "franchise.name",
	"franchises.name", "collections.name", "game_modes.name",
	"involved_companies.company.name", "expansions.id", "expansions.slug",
	"expansions.name", "expansions.cover.url", "dlcs.id", "dlcs.name",
	"dlcs.slug", "dlcs.cover.url", "remakes.id", "remakes.slug",
	"remakes.name", "remakes.cover.url", "remasters.id", "remasters.slug",
	"remasters.name", "remasters.cover.url", "ports.id", "ports.slug",
	"ports.name", "ports.cover.url", "similar_games.id", "similar_games.slug",
	"similar_games.name", "similar_games.cover.url", "age_ratings.rating_category",
	"videos.video_id", "multiplayer_modes.campaigncoop", "multiplayer_modes.dropin",
	"multiplayer_modes.lancoop", "multiplayer_modes.offlinecoop",
	"multiplayer_modes.offlinecoopmax", "multiplayer_modes.offlinemax",
	"multiplayer_modes.onlinecoop", "multiplayer_modes.onlinecoopmax",
	"multiplayer_modes.onlinemax", "multiplayer_modes.splitscreen",
	"multiplayer_modes.splitscreenonline", "multiplayer_modes.platform.id",
	"multiplayer_modes.platform.name",
}

// searchFields contains the fields to fetch for search results
var searchFields = []string{
	"id", "name", "slug", "cover.url", "platforms.name", "first_release_date",
}

// GameType represents IGDB game category types
type GameType int

const (
	GameTypeMainGame     GameType = 0
	GameTypeDLCAddon     GameType = 1
	GameTypeExpansion    GameType = 2
	GameTypeBundle       GameType = 3
	GameTypeStandalone   GameType = 4
	GameTypeMod          GameType = 5
	GameTypeEpisode      GameType = 6
	GameTypeSeason       GameType = 7
	GameTypeRemake       GameType = 8
	GameTypeRemaster     GameType = 9
	GameTypeExpandedGame GameType = 10
	GameTypePort         GameType = 11
	GameTypeFork         GameType = 12
)

// Provider implements the IGDB metadata provider.
type Provider struct {
	*provider.BaseProvider
	baseURL       string
	twitchURL     string
	userAgent     string
	httpClient    *http.Client
	oauthToken    string
	oauthMu       sync.RWMutex
	paginationLimit int
}

// NewProvider creates a new IGDB provider instance.
func NewProvider(config retrometadata.ProviderConfig, c cache.Cache) (*Provider, error) {
	return &Provider{
		BaseProvider:    provider.NewBaseProvider("igdb", config, c),
		baseURL:         "https://api.igdb.com/v4",
		twitchURL:       "https://id.twitch.tv/oauth2/token",
		userAgent:       "retro-metadata/1.0",
		httpClient:      &http.Client{Timeout: 30 * time.Second},
		paginationLimit: 200,
	}, nil
}

func (p *Provider) clientID() string {
	return p.GetCredential("client_id")
}

func (p *Provider) clientSecret() string {
	return p.GetCredential("client_secret")
}

func (p *Provider) getOAuthToken(ctx context.Context) (string, error) {
	// Check if we have a cached token
	p.oauthMu.RLock()
	if p.oauthToken != "" {
		token := p.oauthToken
		p.oauthMu.RUnlock()
		return token, nil
	}
	p.oauthMu.RUnlock()

	// Check cache
	cached, err := p.GetCached(ctx, "oauth_token")
	if err == nil && cached != nil {
		if token, ok := cached.(string); ok && token != "" {
			p.oauthMu.Lock()
			p.oauthToken = token
			p.oauthMu.Unlock()
			return token, nil
		}
	}

	// Request new token from Twitch
	data := url.Values{}
	data.Set("client_id", p.clientID())
	data.Set("client_secret", p.clientSecret())
	data.Set("grant_type", "client_credentials")

	req, err := http.NewRequestWithContext(ctx, "POST", p.twitchURL+"?"+data.Encode(), nil)
	if err != nil {
		return "", fmt.Errorf("failed to create OAuth request: %w", err)
	}

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return "", &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderConnection}
	}
	defer resp.Body.Close()

	if resp.StatusCode == 400 {
		return "", &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderAuth}
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read OAuth response: %w", err)
	}

	var tokenResp struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int    `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &tokenResp); err != nil {
		return "", fmt.Errorf("failed to parse OAuth response: %w", err)
	}

	if tokenResp.AccessToken == "" {
		return "", &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderAuth}
	}

	// Cache the token
	p.oauthMu.Lock()
	p.oauthToken = tokenResp.AccessToken
	p.oauthMu.Unlock()

	// Store in cache with TTL
	if tokenResp.ExpiresIn > 60 {
		_ = p.SetCached(ctx, "oauth_token", tokenResp.AccessToken)
	}

	return tokenResp.AccessToken, nil
}

func (p *Provider) request(ctx context.Context, endpoint string, searchTerm string, fields []string, where string, limit int) ([]map[string]interface{}, error) {
	token, err := p.getOAuthToken(ctx)
	if err != nil {
		return nil, err
	}

	// Build query
	var queryParts []string
	if searchTerm != "" {
		queryParts = append(queryParts, fmt.Sprintf(`search "%s";`, searchTerm))
	}
	if len(fields) > 0 {
		queryParts = append(queryParts, fmt.Sprintf("fields %s;", strings.Join(fields, ",")))
	}
	if where != "" {
		queryParts = append(queryParts, fmt.Sprintf("where %s;", where))
	}
	if limit > 0 {
		queryParts = append(queryParts, fmt.Sprintf("limit %d;", limit))
	}

	body := strings.Join(queryParts, " ")

	req, err := http.NewRequestWithContext(ctx, "POST", p.baseURL+"/"+endpoint, strings.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Accept", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Client-ID", p.clientID())
	req.Header.Set("User-Agent", p.userAgent)

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderConnection}
	}
	defer resp.Body.Close()

	if resp.StatusCode == 401 {
		// Token expired, clear and retry
		p.oauthMu.Lock()
		p.oauthToken = ""
		p.oauthMu.Unlock()
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderAuth}
	}

	if resp.StatusCode == 429 {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderRateLimit}
	}

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result []map[string]interface{}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return result, nil
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	var where string
	if opts.PlatformID != nil {
		where = fmt.Sprintf("platforms=[%d]", *opts.PlatformID)
	}

	limit := opts.Limit
	if limit == 0 {
		limit = 10
	}

	results, err := p.request(ctx, "games", query, searchFields, where, limit)
	if err != nil {
		return nil, err
	}

	var searchResults []retrometadata.SearchResult
	for _, game := range results {
		sr := retrometadata.SearchResult{
			Provider:   p.Name(),
			ProviderID: int(getFloat64(game, "id")),
			Name:       getString(game, "name"),
			Slug:       getString(game, "slug"),
		}

		// Extract cover URL
		if cover, ok := game["cover"].(map[string]interface{}); ok {
			coverURL := getString(cover, "url")
			sr.CoverURL = p.normalizeCoverURL(coverURL, "t_cover_big")
		}

		// Extract platforms
		if platforms, ok := game["platforms"].([]interface{}); ok {
			for _, pl := range platforms {
				if plMap, ok := pl.(map[string]interface{}); ok {
					sr.Platforms = append(sr.Platforms, getString(plMap, "name"))
				}
			}
		}

		// Extract release year
		if timestamp := getFloat64(game, "first_release_date"); timestamp > 0 {
			year := time.Unix(int64(timestamp), 0).Year()
			sr.ReleaseYear = &year
		}

		searchResults = append(searchResults, sr)
	}

	return searchResults, nil
}

// GetByID gets game details by IGDB ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	results, err := p.request(ctx, "games", "", gamesFields, fmt.Sprintf("id=%d", gameID), 1)
	if err != nil {
		return nil, err
	}

	if len(results) == 0 {
		return nil, nil
	}

	return p.buildGameResult(results[0]), nil
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	// Check for IGDB ID tag in filename
	if match := IGDBTagRegex.FindStringSubmatch(filename); len(match) > 1 {
		if id, err := strconv.Atoi(match[1]); err == nil {
			result, err := p.GetByID(ctx, id)
			if err == nil && result != nil {
				return result, nil
			}
		}
	}

	// Clean the filename
	searchTerm := cleanFilename(filename)
	searchTerm = p.NormalizeSearchTerm(searchTerm)

	if opts.PlatformID == nil {
		return nil, nil
	}

	// Search with game type filter first
	categories := []GameType{
		GameTypeMainGame,
		GameTypeExpandedGame,
		GameTypePort,
		GameTypeRemake,
		GameTypeRemaster,
	}
	catStrings := make([]string, len(categories))
	for i, c := range categories {
		catStrings[i] = strconv.Itoa(int(c))
	}
	gameTypeFilter := fmt.Sprintf("& category=(%s)", strings.Join(catStrings, ","))
	where := fmt.Sprintf("platforms=[%d] %s", *opts.PlatformID, gameTypeFilter)

	results, err := p.request(ctx, "games", searchTerm, gamesFields, where, p.paginationLimit)
	if err != nil {
		return nil, err
	}

	if len(results) == 0 {
		// Try without game type filter
		where = fmt.Sprintf("platforms=[%d]", *opts.PlatformID)
		results, err = p.request(ctx, "games", searchTerm, gamesFields, where, p.paginationLimit)
		if err != nil {
			return nil, err
		}
	}

	if len(results) == 0 {
		return nil, nil
	}

	// Find best match
	gamesByName := make(map[string]map[string]interface{})
	var names []string
	for _, g := range results {
		name := getString(g, "name")
		if name != "" {
			gamesByName[name] = g
			names = append(names, name)
		}
	}

	bestMatch, score := matching.FindBestMatch(searchTerm, names, matching.FindBestMatchOptions{
		MinSimilarityScore: matching.DefaultMinSimilarity,
		Normalize:          true,
	})

	if bestMatch != "" {
		if game, ok := gamesByName[bestMatch]; ok {
			result := p.buildGameResult(game)
			result.MatchScore = score
			return result, nil
		}
	}

	return nil, nil
}

// Heartbeat checks if the provider API is accessible.
func (p *Provider) Heartbeat(ctx context.Context) error {
	_, err := p.getOAuthToken(ctx)
	return err
}

func (p *Provider) buildGameResult(game map[string]interface{}) *retrometadata.GameResult {
	providerID := int(getFloat64(game, "id"))
	result := &retrometadata.GameResult{
		Provider:    p.Name(),
		ProviderID:  &providerID,
		ProviderIDs: map[string]int{"igdb": providerID},
		Name:        getString(game, "name"),
		Slug:        getString(game, "slug"),
		Summary:     getString(game, "summary"),
		RawResponse: game,
	}

	// Extract cover URL
	if cover, ok := game["cover"].(map[string]interface{}); ok {
		coverURL := getString(cover, "url")
		result.Artwork.CoverURL = p.normalizeCoverURL(coverURL, "t_1080p")
	}

	// Extract screenshots
	if screenshots, ok := game["screenshots"].([]interface{}); ok {
		for _, s := range screenshots {
			if sMap, ok := s.(map[string]interface{}); ok {
				ssURL := getString(sMap, "url")
				result.Artwork.ScreenshotURLs = append(result.Artwork.ScreenshotURLs, p.normalizeCoverURL(ssURL, "t_720p"))
			}
		}
	}

	// Extract metadata
	result.Metadata = p.extractMetadata(game)

	return result
}

func (p *Provider) extractMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	metadata := retrometadata.GameMetadata{
		RawData: game,
	}

	// Total rating
	if rating := getFloat64(game, "total_rating"); rating > 0 {
		metadata.TotalRating = &rating
	}

	// Aggregated rating
	if rating := getFloat64(game, "aggregated_rating"); rating > 0 {
		metadata.AggregatedRating = &rating
	}

	// First release date
	if timestamp := getFloat64(game, "first_release_date"); timestamp > 0 {
		ts := int64(timestamp)
		metadata.FirstReleaseDate = &ts
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

	// Alternative names
	if altNames, ok := game["alternative_names"].([]interface{}); ok {
		for _, n := range altNames {
			if nMap, ok := n.(map[string]interface{}); ok {
				if name := getString(nMap, "name"); name != "" {
					metadata.AlternativeNames = append(metadata.AlternativeNames, name)
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

	// Game modes
	if modes, ok := game["game_modes"].([]interface{}); ok {
		for _, m := range modes {
			if mMap, ok := m.(map[string]interface{}); ok {
				if name := getString(mMap, "name"); name != "" {
					metadata.GameModes = append(metadata.GameModes, name)
				}
			}
		}
	}

	// Platforms
	if platforms, ok := game["platforms"].([]interface{}); ok {
		for _, pl := range platforms {
			if plMap, ok := pl.(map[string]interface{}); ok {
				platform := retrometadata.Platform{
					Name:        getString(plMap, "name"),
					ProviderIDs: map[string]int{"igdb": int(getFloat64(plMap, "id"))},
				}
				metadata.Platforms = append(metadata.Platforms, platform)
			}
		}
	}

	// Videos (YouTube)
	if videos, ok := game["videos"].([]interface{}); ok {
		if len(videos) > 0 {
			if vMap, ok := videos[0].(map[string]interface{}); ok {
				if videoID := getString(vMap, "video_id"); videoID != "" {
					metadata.YouTubeVideoID = videoID
				}
			}
		}
	}

	// Related games
	metadata.Expansions = p.extractRelatedGames(game, "expansions", "expansion")
	metadata.DLCs = p.extractRelatedGames(game, "dlcs", "dlc")
	metadata.Remasters = p.extractRelatedGames(game, "remasters", "remaster")
	metadata.Remakes = p.extractRelatedGames(game, "remakes", "remake")
	metadata.Ports = p.extractRelatedGames(game, "ports", "port")
	metadata.SimilarGames = p.extractRelatedGames(game, "similar_games", "similar")

	return metadata
}

func (p *Provider) extractRelatedGames(game map[string]interface{}, key, relationType string) []retrometadata.RelatedGame {
	var related []retrometadata.RelatedGame
	if items, ok := game[key].([]interface{}); ok {
		for _, item := range items {
			if itemMap, ok := item.(map[string]interface{}); ok {
				rg := retrometadata.RelatedGame{
					ID:           int(getFloat64(itemMap, "id")),
					Name:         getString(itemMap, "name"),
					Slug:         getString(itemMap, "slug"),
					RelationType: relationType,
					Provider:     p.Name(),
				}
				if cover, ok := itemMap["cover"].(map[string]interface{}); ok {
					rg.CoverURL = p.normalizeCoverURL(getString(cover, "url"), "t_1080p")
				}
				related = append(related, rg)
			}
		}
	}
	return related
}

func (p *Provider) normalizeCoverURL(url string, size string) string {
	if url == "" {
		return ""
	}
	url = normalization.NormalizeCoverURL(url)
	// Replace thumbnail size with requested size
	url = strings.Replace(url, "t_thumb", size, 1)
	return url
}

// GetPlatform returns platform information for a slug.
func (p *Provider) GetPlatform(slug string) *retrometadata.Platform {
	platformSlug := platform.Slug(slug)
	platformID := platform.GetIGDBPlatformID(platformSlug)
	if platformID == nil {
		return nil
	}

	name := IGDBPlatformNames[*platformID]
	if name == "" {
		name = strings.ReplaceAll(slug, "-", " ")
	}

	return &retrometadata.Platform{
		Slug:        slug,
		Name:        name,
		ProviderIDs: map[string]int{"igdb": *platformID},
	}
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
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func getFloat64(m map[string]interface{}, key string) float64 {
	if v, ok := m[key]; ok {
		if f, ok := v.(float64); ok {
			return f
		}
	}
	return 0
}

// IGDBPlatformNames maps IGDB platform IDs to names
var IGDBPlatformNames = map[int]string{
	3:   "Linux",
	4:   "Nintendo 64",
	5:   "Wii",
	6:   "PC (Microsoft Windows)",
	7:   "PlayStation",
	8:   "PlayStation 2",
	9:   "PlayStation 3",
	11:  "Xbox",
	12:  "Xbox 360",
	13:  "DOS",
	14:  "Mac",
	15:  "Commodore C64/128/MAX",
	16:  "Amiga",
	18:  "NES",
	19:  "Super Nintendo Entertainment System",
	20:  "Nintendo DS",
	21:  "Nintendo GameCube",
	22:  "Game Boy Color",
	23:  "Dreamcast",
	24:  "Game Boy Advance",
	25:  "Amstrad CPC",
	26:  "ZX Spectrum",
	27:  "MSX",
	29:  "Sega Mega Drive/Genesis",
	30:  "Sega 32X",
	32:  "Sega Saturn",
	33:  "Game Boy",
	34:  "Android",
	35:  "Sega Game Gear",
	37:  "Nintendo 3DS",
	38:  "PlayStation Portable",
	39:  "iOS",
	41:  "Wii U",
	42:  "N-Gage",
	46:  "PlayStation Vita",
	48:  "PlayStation 4",
	49:  "Xbox One",
	50:  "3DO Interactive Multiplayer",
	51:  "Family Computer Disk System",
	52:  "Arcade",
	53:  "MSX2",
	57:  "WonderSwan",
	58:  "Super Famicom",
	59:  "Atari 2600",
	60:  "Atari 7800",
	61:  "Atari Lynx",
	62:  "Atari Jaguar",
	63:  "Atari ST/STE",
	64:  "Sega Master System/Mark III",
	65:  "Atari 8-bit",
	66:  "Atari 5200",
	67:  "Intellivision",
	68:  "ColecoVision",
	69:  "BBC Micro",
	70:  "Vectrex",
	71:  "Commodore VIC-20",
	72:  "Ouya",
	75:  "Apple II",
	76:  "PocketStation",
	77:  "Sharp X1",
	78:  "Sega CD",
	79:  "Neo Geo MVS",
	80:  "Neo Geo AES",
	84:  "SG-1000",
	86:  "TurboGrafx-16/PC Engine",
	87:  "Virtual Boy",
	93:  "Commodore 16",
	94:  "Commodore Plus/4",
	99:  "Family Computer (Famicom)",
	111: "Atari XEGS",
	112: "Sharp X68000",
	114: "Amiga CD",
	115: "Apple IIGS",
	116: "Commodore CDTV",
	117: "Amiga CD32",
	119: "Neo Geo Pocket",
	120: "Neo Geo Pocket Color",
	121: "Gizmondo",
	122: "Game.com",
	123: "WonderSwan Color",
	125: "PC-8801",
	127: "Fairchild Channel F",
	128: "PC Engine SuperGrafx",
	130: "Nintendo Switch",
	132: "Amazon Fire TV",
	133: "Magnavox Odyssey 2",
	136: "Neo Geo CD",
	137: "New Nintendo 3DS",
	149: "PC-9801",
	150: "Turbografx-16/PC Engine CD",
	158: "Amstrad GX4000",
	161: "MSX2+",
	165: "PlayStation VR",
	167: "PlayStation 5",
	169: "Xbox Series X|S",
	170: "Google Stadia",
	171: "Atari Jaguar CD",
	207: "Pokemon mini",
	274: "PC-FX",
	308: "Playdate",
	339: "Sega Pico",
	340: "Gamate",
	343: "Watara Supervision",
	390: "PlayStation VR2",
	416: "Nintendo 64DD",
}

func init() {
	// Register the provider factory
	retrometadata.RegisterProvider("igdb", func(config retrometadata.ProviderConfig, c cache.Cache) (retrometadata.Provider, error) {
		return NewProvider(config, c)
	})
}
