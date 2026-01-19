// Package mobygames provides the MobyGames metadata provider implementation.
package mobygames

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
	"time"

	"github.com/josegonzalez/retro-metadata/pkg/cache"
	"github.com/josegonzalez/retro-metadata/pkg/internal/normalization"
	"github.com/josegonzalez/retro-metadata/pkg/platform"
	"github.com/josegonzalez/retro-metadata/pkg/provider"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// MobyGamesTagRegex matches MobyGames ID tags in filenames like (moby-12345)
var MobyGamesTagRegex = regexp.MustCompile(`(?i)\(moby-(\d+)\)`)

// SonySerialRegex matches PS1/PS2/PSP serial codes like SLUS-12345, SCUS-97328
var SonySerialRegex = regexp.MustCompile(`(?i)([A-Z]{4})[_-](\d{5})`)

// PS2OPLRegex matches PS2 OPL format like SLUS_123.45
var PS2OPLRegex = regexp.MustCompile(`(?i)([A-Z]{4})_(\d{3})\.(\d{2})`)

// SwitchTitleDBRegex matches Nintendo Switch 16-character hex IDs
var SwitchTitleDBRegex = regexp.MustCompile(`([0-9A-Fa-f]{16})`)

// SwitchProductIDRegex matches Switch product IDs like LA-H-AAAAA
var SwitchProductIDRegex = regexp.MustCompile(`(?i)[A-Z]{2}-[A-Z]-([A-Z0-9]{5})`)

// MAMEArcadeRegex matches MAME ROM names
var MAMEArcadeRegex = regexp.MustCompile(`(?i)^([a-z0-9_]+)$`)

// Provider implements the MobyGames metadata provider.
type Provider struct {
	*provider.BaseProvider
	baseURL    string
	userAgent  string
	httpClient *http.Client
}

// NewProvider creates a new MobyGames provider instance.
func NewProvider(config retrometadata.ProviderConfig, c cache.Cache) (*Provider, error) {
	p := &Provider{
		BaseProvider: provider.NewBaseProvider("mobygames", config, c),
		baseURL:      "https://api.mobygames.com/v1",
		userAgent:    "retro-metadata/1.0",
		httpClient:   &http.Client{Timeout: 30 * time.Second},
	}
	p.SetMinSimilarityScore(0.6)
	return p, nil
}

func (p *Provider) apiKey() string {
	return p.GetCredential("api_key")
}

func (p *Provider) request(ctx context.Context, endpoint string, params map[string]string) (interface{}, error) {
	u, err := url.Parse(p.baseURL + endpoint)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL: %w", err)
	}

	q := u.Query()
	q.Set("api_key", p.apiKey())
	for k, v := range params {
		q.Set(k, v)
	}
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, "GET", u.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("User-Agent", p.userAgent)

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderConnection}
	}
	defer resp.Body.Close()

	if resp.StatusCode == 401 {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderAuth}
	}

	if resp.StatusCode == 429 {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderRateLimit}
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var result interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return result, nil
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	params := map[string]string{
		"title": query,
		"limit": strconv.Itoa(max(opts.Limit, 10)),
	}

	if opts.PlatformID != nil {
		params["platform"] = strconv.Itoa(*opts.PlatformID)
	}

	result, err := p.request(ctx, "/games", params)
	if err != nil {
		return nil, err
	}

	resultMap, ok := result.(map[string]interface{})
	if !ok {
		return nil, nil
	}

	games, ok := resultMap["games"].([]interface{})
	if !ok {
		return nil, nil
	}

	var searchResults []retrometadata.SearchResult
	for _, g := range games {
		game, ok := g.(map[string]interface{})
		if !ok {
			continue
		}

		sr := retrometadata.SearchResult{
			Provider:   p.Name(),
			ProviderID: int(getFloat64(game, "game_id")),
			Name:       getString(game, "title"),
		}

		// Extract cover URL
		if sampleCover, ok := game["sample_cover"].(map[string]interface{}); ok {
			sr.CoverURL = getString(sampleCover, "image")
		}

		// Extract platforms
		if platforms, ok := game["platforms"].([]interface{}); ok {
			for _, pl := range platforms {
				if plMap, ok := pl.(map[string]interface{}); ok {
					sr.Platforms = append(sr.Platforms, getString(plMap, "platform_name"))
				}
			}
		}

		// Extract release year
		if platforms, ok := game["platforms"].([]interface{}); ok && len(platforms) > 0 {
			if firstPlatform, ok := platforms[0].(map[string]interface{}); ok {
				dateStr := getString(firstPlatform, "first_release_date")
				if len(dateStr) >= 4 {
					if year, err := strconv.Atoi(dateStr[:4]); err == nil {
						sr.ReleaseYear = &year
					}
				}
			}
		}

		searchResults = append(searchResults, sr)
	}

	return searchResults, nil
}

// GetByID gets game details by MobyGames ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	result, err := p.request(ctx, fmt.Sprintf("/games/%d", gameID), nil)
	if err != nil {
		return nil, err
	}

	game, ok := result.(map[string]interface{})
	if !ok || getFloat64(game, "game_id") == 0 {
		return nil, nil
	}

	return p.buildGameResult(game), nil
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	// Check for MobyGames ID tag in filename
	if match := MobyGamesTagRegex.FindStringSubmatch(filename); len(match) > 1 {
		if id, err := strconv.Atoi(match[1]); err == nil {
			result, err := p.GetByID(ctx, id)
			if err == nil && result != nil {
				return result, nil
			}
		}
	}

	if opts.PlatformID == nil {
		return nil, nil
	}

	var searchTerm string

	// Try Sony serial format for PS1/PS2/PSP platforms
	// MobyGames platform IDs: PS1=6, PS2=7, PSP=46
	platformID := *opts.PlatformID
	if platformID == 6 || platformID == 7 || platformID == 46 {
		if serial := extractSerialCode(filename); serial != "" {
			searchTerm = serial
		}
	}

	// Try Nintendo Switch ID formats (platform ID 203)
	if platformID == 203 && searchTerm == "" {
		_, productID := extractSwitchID(filename)
		if productID != "" {
			searchTerm = productID
		}
	}

	// Try MAME format for arcade platform (ID 143)
	if platformID == 143 && searchTerm == "" {
		if isMAMEFormat(filename) {
			searchTerm = regexp.MustCompile(`\.[^.]+$`).ReplaceAllString(filename, "")
		}
	}

	// Fall back to cleaned filename
	if searchTerm == "" {
		searchTerm = cleanFilename(filename)
	}

	// Search for the game
	params := map[string]string{
		"title":    url.QueryEscape(searchTerm),
		"platform": strconv.Itoa(platformID),
	}

	result, err := p.request(ctx, "/games", params)
	if err != nil {
		return nil, err
	}

	resultMap, ok := result.(map[string]interface{})
	if !ok {
		return nil, nil
	}

	games, ok := resultMap["games"].([]interface{})
	if !ok || len(games) == 0 {
		// Try splitting by special characters
		terms := normalization.SplitSearchTerm(searchTerm)
		if len(terms) > 1 {
			params["title"] = url.QueryEscape(terms[len(terms)-1])
			result, err = p.request(ctx, "/games", params)
			if err != nil {
				return nil, err
			}
			resultMap, ok = result.(map[string]interface{})
			if ok {
				games, _ = resultMap["games"].([]interface{})
			}
		}
	}

	if len(games) == 0 {
		return nil, nil
	}

	// Find best match
	gamesByName := make(map[string]map[string]interface{})
	var names []string
	for _, g := range games {
		if game, ok := g.(map[string]interface{}); ok {
			title := getString(game, "title")
			if title != "" {
				gamesByName[title] = game
				names = append(names, title)
			}
		}
	}

	bestMatch, score := p.FindBestMatch(searchTerm, names)

	if bestMatch != "" {
		if game, ok := gamesByName[bestMatch]; ok {
			gameResult := p.buildGameResult(game)
			gameResult.MatchScore = score
			return gameResult, nil
		}
	}

	return nil, nil
}

// Heartbeat checks if the provider API is accessible.
func (p *Provider) Heartbeat(ctx context.Context) error {
	_, err := p.request(ctx, "/games", map[string]string{"limit": "1"})
	return err
}

func (p *Provider) buildGameResult(game map[string]interface{}) *retrometadata.GameResult {
	providerID := int(getFloat64(game, "game_id"))
	result := &retrometadata.GameResult{
		Provider:    p.Name(),
		ProviderID:  &providerID,
		ProviderIDs: map[string]int{"mobygames": providerID},
		Name:        getString(game, "title"),
		Summary:     getString(game, "description"),
		RawResponse: game,
	}

	// Extract cover URL
	if sampleCover, ok := game["sample_cover"].(map[string]interface{}); ok {
		result.Artwork.CoverURL = getString(sampleCover, "image")
	}

	// Extract screenshots
	if screenshots, ok := game["sample_screenshots"].([]interface{}); ok {
		for _, s := range screenshots {
			if sMap, ok := s.(map[string]interface{}); ok {
				if imgURL := getString(sMap, "image"); imgURL != "" {
					result.Artwork.ScreenshotURLs = append(result.Artwork.ScreenshotURLs, imgURL)
				}
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

	// Genres
	if genres, ok := game["genres"].([]interface{}); ok {
		for _, g := range genres {
			if gMap, ok := g.(map[string]interface{}); ok {
				if name := getString(gMap, "genre_name"); name != "" {
					metadata.Genres = append(metadata.Genres, name)
				}
			}
		}
	}

	// Alternative names
	if altTitles, ok := game["alternate_titles"].([]interface{}); ok {
		for _, t := range altTitles {
			if tMap, ok := t.(map[string]interface{}); ok {
				if title := getString(tMap, "title"); title != "" {
					metadata.AlternativeNames = append(metadata.AlternativeNames, title)
				}
			}
		}
	}

	// Platforms
	if platforms, ok := game["platforms"].([]interface{}); ok {
		for _, pl := range platforms {
			if plMap, ok := pl.(map[string]interface{}); ok {
				platform := retrometadata.Platform{
					Name:        getString(plMap, "platform_name"),
					ProviderIDs: map[string]int{"mobygames": int(getFloat64(plMap, "platform_id"))},
				}
				metadata.Platforms = append(metadata.Platforms, platform)
			}
		}
	}

	// Rating (MobyGames scores are out of 10, convert to 100)
	if mobyScore := getFloat64(game, "moby_score"); mobyScore > 0 {
		rating := mobyScore * 10
		metadata.TotalRating = &rating
	}

	return metadata
}

// GetPlatform returns platform information for a slug.
func (p *Provider) GetPlatform(slug string) *retrometadata.Platform {
	platformSlug := platform.Slug(slug)
	platformID := platform.GetMobyGamesPlatformID(platformSlug)
	if platformID == nil {
		return nil
	}

	name := MobyGamesPlatformNames[*platformID]
	if name == "" {
		name = strings.ReplaceAll(slug, "-", " ")
	}

	return &retrometadata.Platform{
		Slug:        slug,
		Name:        name,
		ProviderIDs: map[string]int{"mobygames": *platformID},
	}
}

func extractSerialCode(filename string) string {
	// Try PS2 OPL format first (SLUS_123.45)
	if match := PS2OPLRegex.FindStringSubmatch(filename); len(match) > 3 {
		prefix := strings.ToUpper(match[1])
		part1 := match[2]
		part2 := match[3]
		return fmt.Sprintf("%s-%s%s", prefix, part1, part2)
	}

	// Try standard Sony serial format (SLUS-12345 or SLUS_12345)
	if match := SonySerialRegex.FindStringSubmatch(filename); len(match) > 2 {
		prefix := strings.ToUpper(match[1])
		number := match[2]
		return fmt.Sprintf("%s-%s", prefix, number)
	}

	return ""
}

func extractSwitchID(filename string) (titleID, productID string) {
	// Try titleID format (16-char hex)
	if match := SwitchTitleDBRegex.FindStringSubmatch(filename); len(match) > 1 {
		titleID = strings.ToUpper(match[1])
	}

	// Try productID format (LA-H-AAAAA)
	if match := SwitchProductIDRegex.FindStringSubmatch(filename); len(match) > 1 {
		productID = strings.ToUpper(match[1])
	}

	return titleID, productID
}

func isMAMEFormat(filename string) bool {
	// Remove extension first
	name := regexp.MustCompile(`\.[^.]+$`).ReplaceAllString(filename, "")
	// MAME names are typically short (under 20 chars) and alphanumeric
	if len(name) > 20 {
		return false
	}
	return MAMEArcadeRegex.MatchString(name)
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

// MobyGamesPlatformNames maps MobyGames platform IDs to names
var MobyGamesPlatformNames = map[int]string{
	1:   "Linux",
	2:   "DOS",
	3:   "Windows",
	4:   "PC Booter",
	5:   "Windows 3.x",
	6:   "PlayStation",
	7:   "PlayStation 2",
	8:   "Dreamcast",
	9:   "Nintendo 64",
	10:  "Game Boy",
	11:  "Game Boy Color",
	12:  "Game Boy Advance",
	13:  "Xbox",
	14:  "GameCube",
	15:  "SNES",
	16:  "Genesis",
	17:  "Jaguar",
	18:  "Lynx",
	19:  "Amiga",
	20:  "SEGA CD",
	21:  "SEGA 32X",
	22:  "NES",
	23:  "Saturn",
	24:  "Atari ST",
	25:  "Game Gear",
	26:  "SEGA Master System",
	27:  "Commodore 64",
	28:  "Atari 2600",
	29:  "ColecoVision",
	30:  "Intellivision",
	31:  "Apple II",
	32:  "N-Gage",
	33:  "Atari 5200",
	34:  "Atari 7800",
	35:  "3DO",
	36:  "Neo Geo",
	37:  "Vectrex",
	38:  "Virtual Boy",
	39:  "Atari 8-bit",
	40:  "TurboGrafx-16",
	41:  "ZX Spectrum",
	44:  "Nintendo DS",
	46:  "PSP",
	48:  "WonderSwan",
	49:  "WonderSwan Color",
	69:  "Xbox 360",
	74:  "Macintosh",
	81:  "PlayStation 3",
	82:  "Wii",
	86:  "iOS",
	91:  "Android",
	101: "Nintendo 3DS",
	105: "PlayStation Vita",
	132: "Wii U",
	141: "PlayStation 4",
	142: "Xbox One",
	143: "Arcade",
	203: "Nintendo Switch",
	288: "PlayStation 5",
	289: "Xbox Series X|S",
}

func init() {
	// Register the provider factory
	retrometadata.RegisterProvider("mobygames", func(config retrometadata.ProviderConfig, c cache.Cache) (retrometadata.Provider, error) {
		return NewProvider(config, c)
	})
}
