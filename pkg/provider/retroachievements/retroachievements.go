// Package retroachievements provides the RetroAchievements metadata provider implementation.
package retroachievements

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
	"github.com/josegonzalez/retro-metadata/pkg/platform"
	"github.com/josegonzalez/retro-metadata/pkg/provider"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// RATagRegex matches RetroAchievements ID tags in filenames like (ra-12345)
var RATagRegex = regexp.MustCompile(`(?i)\(ra-(\d+)\)`)

// Base URLs for media assets
const (
	RAMediaURL = "https://media.retroachievements.org"
	RABadgeURL = "https://media.retroachievements.org/Badge"
)

// RAGameAchievement represents a RetroAchievements achievement.
type RAGameAchievement struct {
	ID               int    `json:"id"`
	Title            string `json:"title"`
	Description      string `json:"description"`
	Points           int    `json:"points"`
	BadgeID          string `json:"badge_id"`
	BadgeURL         string `json:"badge_url"`
	BadgeURLLocked   string `json:"badge_url_locked"`
	Type             string `json:"type"`
	NumAwarded       int    `json:"num_awarded"`
	NumAwardedHard   int    `json:"num_awarded_hardcore"`
	DisplayOrder     int    `json:"display_order"`
}

// Provider implements the RetroAchievements metadata provider.
type Provider struct {
	*provider.BaseProvider
	baseURL    string
	userAgent  string
	httpClient *http.Client
}

// NewProvider creates a new RetroAchievements provider instance.
func NewProvider(config retrometadata.ProviderConfig, c cache.Cache) (*Provider, error) {
	p := &Provider{
		BaseProvider: provider.NewBaseProvider("retroachievements", config, c),
		baseURL:      "https://retroachievements.org/API",
		userAgent:    "retro-metadata/1.0",
		httpClient:   &http.Client{Timeout: 30 * time.Second},
	}
	p.SetMinSimilarityScore(0.6)
	return p, nil
}

func (p *Provider) apiKey() string {
	return p.GetCredential("api_key")
}

func (p *Provider) username() string {
	v := p.GetCredential("username")
	if v == "" {
		return "retro-metadata"
	}
	return v
}

func (p *Provider) request(ctx context.Context, endpoint string, params map[string]string) (interface{}, error) {
	u, err := url.Parse(p.baseURL + endpoint)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL: %w", err)
	}

	q := u.Query()
	q.Set("z", p.username())
	q.Set("y", p.apiKey())
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
// Note: RetroAchievements doesn't have a search endpoint, so this fetches the
// game list for the platform and filters locally.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	if opts.PlatformID == nil {
		return nil, nil
	}

	// Get game list for platform
	params := map[string]string{
		"i": strconv.Itoa(*opts.PlatformID),
		"f": "1", // Only games with achievements
		"h": "0", // Don't include hashes
	}

	result, err := p.request(ctx, "/API_GetGameList.php", params)
	if err != nil {
		return nil, err
	}

	games, ok := result.([]interface{})
	if !ok {
		return nil, nil
	}

	// Filter by query
	queryLower := strings.ToLower(query)
	limit := opts.Limit
	if limit == 0 {
		limit = 25
	}

	var searchResults []retrometadata.SearchResult
	for _, g := range games {
		game, ok := g.(map[string]interface{})
		if !ok {
			continue
		}

		title := getString(game, "Title")
		if !strings.Contains(strings.ToLower(title), queryLower) {
			continue
		}

		icon := getString(game, "ImageIcon")
		coverURL := ""
		if icon != "" {
			coverURL = RAMediaURL + icon
		}

		sr := retrometadata.SearchResult{
			Provider:   p.Name(),
			ProviderID: getInt(game, "ID"),
			Name:       title,
			CoverURL:   coverURL,
			Platforms:  []string{getString(game, "ConsoleName")},
		}

		searchResults = append(searchResults, sr)
		if len(searchResults) >= limit {
			break
		}
	}

	return searchResults, nil
}

// GetByID gets game details by RetroAchievements ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	result, err := p.request(ctx, "/API_GetGameExtended.php", map[string]string{"i": strconv.Itoa(gameID)})
	if err != nil {
		return nil, err
	}

	game, ok := result.(map[string]interface{})
	if !ok || getInt(game, "ID") == 0 {
		return nil, nil
	}

	return p.buildGameResult(game), nil
}

// GetAchievements gets all achievements for a game.
func (p *Provider) GetAchievements(ctx context.Context, gameID int) ([]RAGameAchievement, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	result, err := p.request(ctx, "/API_GetGameExtended.php", map[string]string{"i": strconv.Itoa(gameID)})
	if err != nil {
		return nil, err
	}

	game, ok := result.(map[string]interface{})
	if !ok {
		return nil, nil
	}

	achievementsData, ok := game["Achievements"].(map[string]interface{})
	if !ok || len(achievementsData) == 0 {
		return nil, nil
	}

	var achievements []RAGameAchievement
	for _, achData := range achievementsData {
		if ach, ok := achData.(map[string]interface{}); ok {
			badgeID := getString(ach, "BadgeName")
			badgeURL := ""
			badgeURLLocked := ""
			if badgeID != "" {
				badgeURL = fmt.Sprintf("%s/%s.png", RABadgeURL, badgeID)
				badgeURLLocked = fmt.Sprintf("%s/%s_lock.png", RABadgeURL, badgeID)
			}

			achievements = append(achievements, RAGameAchievement{
				ID:             getInt(ach, "ID"),
				Title:          getString(ach, "Title"),
				Description:    getString(ach, "Description"),
				Points:         getInt(ach, "Points"),
				BadgeID:        badgeID,
				BadgeURL:       badgeURL,
				BadgeURLLocked: badgeURLLocked,
				Type:           getString(ach, "type"),
				NumAwarded:     getInt(ach, "NumAwarded"),
				NumAwardedHard: getInt(ach, "NumAwardedHardcore"),
				DisplayOrder:   getInt(ach, "DisplayOrder"),
			})
		}
	}

	return achievements, nil
}

// LookupByHash looks up a game by ROM MD5 hash.
func (p *Provider) LookupByHash(ctx context.Context, platformID int, md5 string) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	if md5 == "" {
		return nil, nil
	}

	// Get game list with hashes
	params := map[string]string{
		"i": strconv.Itoa(platformID),
		"f": "1", // Only games with achievements
		"h": "1", // Include hashes
	}

	result, err := p.request(ctx, "/API_GetGameList.php", params)
	if err != nil {
		return nil, err
	}

	games, ok := result.([]interface{})
	if !ok {
		return nil, nil
	}

	// Find matching hash
	md5Lower := strings.ToLower(md5)
	for _, g := range games {
		game, ok := g.(map[string]interface{})
		if !ok {
			continue
		}

		hashes, ok := game["Hashes"].([]interface{})
		if !ok {
			continue
		}

		for _, h := range hashes {
			if hash, ok := h.(string); ok {
				if strings.ToLower(hash) == md5Lower {
					// Get full game details
					return p.GetByID(ctx, getInt(game, "ID"))
				}
			}
		}
	}

	return nil, nil
}

// IdentifyByHash implements the HashProvider interface for hash-based identification.
func (p *Provider) IdentifyByHash(ctx context.Context, hashes retrometadata.FileHashes, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if opts.PlatformID == nil {
		return nil, nil
	}
	return p.LookupByHash(ctx, *opts.PlatformID, hashes.MD5)
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	// Check for RetroAchievements ID tag in filename
	if match := RATagRegex.FindStringSubmatch(filename); len(match) > 1 {
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

	// Clean the filename and search
	searchTerm := cleanFilename(filename)

	// Get game list for platform
	params := map[string]string{
		"i": strconv.Itoa(*opts.PlatformID),
		"f": "1",
		"h": "0",
	}

	result, err := p.request(ctx, "/API_GetGameList.php", params)
	if err != nil {
		return nil, err
	}

	games, ok := result.([]interface{})
	if !ok || len(games) == 0 {
		return nil, nil
	}

	// Build name mapping
	gamesByName := make(map[string]map[string]interface{})
	var names []string
	for _, g := range games {
		if game, ok := g.(map[string]interface{}); ok {
			title := getString(game, "Title")
			if title != "" {
				gamesByName[title] = game
				names = append(names, title)
			}
		}
	}

	// Find best match
	bestMatch, score := p.FindBestMatch(searchTerm, names)

	if bestMatch != "" {
		if game, ok := gamesByName[bestMatch]; ok {
			gameResult, err := p.GetByID(ctx, getInt(game, "ID"))
			if err == nil && gameResult != nil {
				gameResult.MatchScore = score
				return gameResult, nil
			}
		}
	}

	return nil, nil
}

// Heartbeat checks if the provider API is accessible.
func (p *Provider) Heartbeat(ctx context.Context) error {
	_, err := p.request(ctx, "/API_GetGameList.php", map[string]string{"i": "1", "f": "1", "h": "0"})
	return err
}

func (p *Provider) buildGameResult(game map[string]interface{}) *retrometadata.GameResult {
	// Build artwork URLs
	icon := getString(game, "ImageIcon")
	titleImg := getString(game, "ImageTitle")
	ingameImg := getString(game, "ImageIngame")
	boxartImg := getString(game, "ImageBoxArt")

	coverURL := ""
	if boxartImg != "" {
		coverURL = RAMediaURL + boxartImg
	} else if titleImg != "" {
		coverURL = RAMediaURL + titleImg
	}

	var screenshotURLs []string
	if ingameImg != "" {
		screenshotURLs = append(screenshotURLs, RAMediaURL+ingameImg)
	}
	if titleImg != "" && titleImg != boxartImg {
		screenshotURLs = append(screenshotURLs, RAMediaURL+titleImg)
	}

	iconURL := ""
	if icon != "" {
		iconURL = RAMediaURL + icon
	}

	providerID := getInt(game, "ID")
	result := &retrometadata.GameResult{
		Provider:    p.Name(),
		ProviderID:  &providerID,
		ProviderIDs: map[string]int{"retroachievements": providerID},
		Name:        getString(game, "Title"),
		Summary:     "", // RA doesn't provide game descriptions
		RawResponse: game,
		Artwork: retrometadata.Artwork{
			CoverURL:       coverURL,
			ScreenshotURLs: screenshotURLs,
			IconURL:        iconURL,
		},
	}

	// Extract metadata
	result.Metadata = p.extractMetadata(game)

	return result
}

func (p *Provider) extractMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	metadata := retrometadata.GameMetadata{
		RawData: game,
	}

	// Genre
	if genre := getString(game, "Genre"); genre != "" {
		metadata.Genres = []string{genre}
	}

	// Companies
	if publisher := getString(game, "Publisher"); publisher != "" {
		metadata.Companies = append(metadata.Companies, publisher)
		metadata.Publisher = publisher
	}
	if developer := getString(game, "Developer"); developer != "" {
		// Avoid duplicates
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

	// Release date
	if released := getString(game, "Released"); released != "" {
		// Handle "YYYY-MM-DD extra info" format
		dateStr := strings.Split(released, " ")[0]
		if t, err := time.Parse("2006-01-02", dateStr); err == nil {
			ts := t.Unix()
			metadata.FirstReleaseDate = &ts
			year := t.Year()
			metadata.ReleaseYear = &year
		}
	}

	// Platform info
	if consoleName := getString(game, "ConsoleName"); consoleName != "" {
		metadata.Platforms = []retrometadata.Platform{
			{
				Name:        consoleName,
				ProviderIDs: map[string]int{"retroachievements": getInt(game, "ConsoleID")},
			},
		}
	}

	return metadata
}

// GetPlatform returns platform information for a slug.
func (p *Provider) GetPlatform(slug string) *retrometadata.Platform {
	platformSlug := platform.Slug(slug)
	platformID := platform.GetRetroAchievementsPlatformID(platformSlug)
	if platformID == nil {
		return nil
	}

	name := RAPlatformNames[*platformID]
	if name == "" {
		name = strings.ReplaceAll(slug, "-", " ")
	}

	return &retrometadata.Platform{
		Slug:        slug,
		Name:        name,
		ProviderIDs: map[string]int{"retroachievements": *platformID},
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

// RAPlatformNames maps RetroAchievements console IDs to names
var RAPlatformNames = map[int]string{
	1:  "Mega Drive",
	2:  "Nintendo 64",
	3:  "SNES",
	4:  "Game Boy",
	5:  "Game Boy Advance",
	6:  "Game Boy Color",
	7:  "NES",
	8:  "TurboGrafx-16",
	9:  "Mega CD",
	10: "32X",
	11: "Master System",
	12: "PlayStation",
	13: "Lynx",
	14: "Neo Geo Pocket",
	15: "Game Gear",
	16: "GameCube",
	17: "Jaguar",
	18: "Nintendo DS",
	19: "Wii",
	21: "PlayStation 2",
	23: "Odyssey 2",
	24: "Pokemon Mini",
	25: "Atari 2600",
	27: "Arcade",
	28: "Virtual Boy",
	29: "MSX",
	33: "SG-1000",
	34: "ZX Spectrum",
	36: "Atari ST",
	37: "Amstrad CPC",
	38: "Apple II",
	39: "Saturn",
	40: "Dreamcast",
	41: "PSP",
	43: "3DO",
	44: "ColecoVision",
	45: "Intellivision",
	46: "Vectrex",
	47: "PC-8000/8800",
	48: "PC-9800",
	49: "PC-FX",
	50: "Atari 5200",
	51: "Atari 7800",
	52: "Sharp X68000",
	53: "WonderSwan",
	56: "Neo Geo CD",
	57: "Fairchild Channel F",
	63: "Watara Supervision",
	69: "Mega Duck",
	71: "Arduboy",
	72: "WASM-4",
	73: "Arcadia 2001",
	75: "Interton VC 4000",
	76: "SuperGrafx",
	77: "Atari Jaguar CD",
	78: "Nintendo DSi",
	80: "Uzebox",
}

func init() {
	// Register the provider factory
	retrometadata.RegisterProvider("retroachievements", func(config retrometadata.ProviderConfig, c cache.Cache) (retrometadata.Provider, error) {
		return NewProvider(config, c)
	})
}
