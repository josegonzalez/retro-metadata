// Package flashpoint provides metadata from the Flashpoint Archive project.
package flashpoint

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

	retrometadata "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

var (
	// Regex to detect Flashpoint ID tags in filenames (UUID format)
	flashpointTagRegex = regexp.MustCompile(`(?i)\(fp-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\)`)

	// UUID regex for filename extraction
	uuidRegex = regexp.MustCompile(`(?i)[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}`)

	// ErrProviderDisabled is returned when the provider is disabled.
	ErrProviderDisabled = fmt.Errorf("provider is disabled")
)

// Provider implements the Flashpoint metadata provider.
type Provider struct {
	config    *retrometadata.ProviderConfig
	client    *http.Client
	baseURL   string
	userAgent string
}

// New creates a new Flashpoint provider.
func New(config *retrometadata.ProviderConfig) *Provider {
	timeout := time.Duration(config.Timeout) * time.Second
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &Provider{
		config:    config,
		client:    &http.Client{Timeout: timeout},
		baseURL:   "https://db-api.unstable.life",
		userAgent: "retro-metadata/1.0",
	}
}

// Name returns the provider name.
func (p *Provider) Name() string {
	return "flashpoint"
}

func buildImageURL(gameID string, imageType string) string {
	if len(gameID) < 4 {
		return ""
	}
	return fmt.Sprintf("https://infinity.unstable.life/images/%s/%s/%s/%s?type=jpg",
		imageType, gameID[:2], gameID[2:4], gameID)
}

func (p *Provider) request(ctx context.Context, endpoint string, params url.Values) (interface{}, error) {
	reqURL := p.baseURL + endpoint
	if len(params) > 0 {
		reqURL += "?" + params.Encode()
	}

	req, err := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", p.userAgent)

	resp, err := p.client.Do(req)
	if err != nil {
		return nil, &retrometadata.ConnectionError{Provider: p.Name(), Details: err.Error()}
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, &retrometadata.ConnectionError{Provider: p.Name(), Details: fmt.Sprintf("HTTP %d", resp.StatusCode)}
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	return result, nil
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	params := url.Values{}
	params.Set("smartSearch", query)
	params.Set("filter", "false")

	result, err := p.request(ctx, "/search", params)
	if err != nil {
		return nil, err
	}

	games, ok := result.([]interface{})
	if !ok {
		return nil, nil
	}

	limit := opts.Limit
	if limit == 0 {
		limit = 30
	}

	var results []retrometadata.SearchResult
	for i, item := range games {
		if i >= limit {
			break
		}

		game, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		gameID := getString(game, "id")
		if gameID == "" {
			continue
		}

		coverURL := buildImageURL(gameID, "Logos")

		var releaseYear *int
		if dateStr := getString(game, "releaseDate"); dateStr != "" && len(dateStr) >= 4 {
			if year := parseYear(dateStr); year > 0 {
				releaseYear = &year
			}
		}

		results = append(results, retrometadata.SearchResult{
			Name:        getString(game, "title"),
			Provider:    p.Name(),
			ProviderID:  0, // Flashpoint uses UUID strings, not integers
			Slug:        gameID,
			CoverURL:    coverURL,
			Platforms:   []string{getString(game, "platform")},
			ReleaseYear: releaseYear,
		})
	}

	return results, nil
}

// GetByID gets game details by Flashpoint UUID.
func (p *Provider) GetByID(ctx context.Context, gameID string) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	params := url.Values{}
	params.Set("id", gameID)
	params.Set("filter", "false")

	result, err := p.request(ctx, "/search", params)
	if err != nil {
		return nil, err
	}

	games, ok := result.([]interface{})
	if !ok || len(games) == 0 {
		return nil, nil
	}

	game, ok := games[0].(map[string]interface{})
	if !ok || getString(game, "id") == "" {
		return nil, nil
	}

	return p.buildGameResult(game), nil
}

// GetByIntID is not supported for Flashpoint (uses UUIDs).
func (p *Provider) GetByIntID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	return nil, nil
}

// Identify identifies a game from a filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	// Check for Flashpoint ID tag in filename
	if matches := flashpointTagRegex.FindStringSubmatch(filename); len(matches) > 1 {
		result, err := p.GetByID(ctx, matches[1])
		if err == nil && result != nil {
			return result, nil
		}
	}

	// Check for UUID in filename
	if uuidMatch := uuidRegex.FindString(filename); uuidMatch != "" {
		result, err := p.GetByID(ctx, uuidMatch)
		if err == nil && result != nil {
			return result, nil
		}
	}

	// Clean the filename and search
	searchTerm := cleanFilename(filename)

	params := url.Values{}
	params.Set("smartSearch", searchTerm)
	params.Set("filter", "false")

	result, err := p.request(ctx, "/search", params)
	if err != nil {
		return nil, err
	}

	games, ok := result.([]interface{})
	if !ok || len(games) == 0 {
		return nil, nil
	}

	// Build name to game map
	gamesByName := make(map[string]map[string]interface{})
	for _, item := range games {
		if game, ok := item.(map[string]interface{}); ok {
			if name := getString(game, "title"); name != "" {
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
	gameResult := p.buildGameResult(game)
	gameResult.MatchScore = score
	return gameResult, nil
}

func (p *Provider) buildGameResult(game map[string]interface{}) *retrometadata.GameResult {
	gameID := getString(game, "id")

	coverURL := buildImageURL(gameID, "Logos")
	screenshotURL := buildImageURL(gameID, "Screenshots")

	var screenshotURLs []string
	if screenshotURL != "" {
		screenshotURLs = []string{screenshotURL}
	}

	metadata := p.extractMetadata(game)

	return &retrometadata.GameResult{
		Name:        getString(game, "title"),
		Summary:     getString(game, "originalDescription"),
		Provider:    p.Name(),
		ProviderID:  nil, // Flashpoint uses UUIDs
		Slug:        gameID,
		ProviderIDs: map[string]int{}, // Will store UUID in slug instead
		Artwork: retrometadata.Artwork{
			CoverURL:       coverURL,
			ScreenshotURLs: screenshotURLs,
		},
		Metadata:    metadata,
		RawResponse: game,
	}
}

func (p *Provider) extractMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	var firstReleaseDate *int64
	var releaseYear *int
	if dateStr := getString(game, "releaseDate"); dateStr != "" {
		if t, err := time.Parse("2006-01-02", dateStr); err == nil {
			ts := t.Unix()
			firstReleaseDate = &ts
			year := t.Year()
			releaseYear = &year
		}
	}

	// Genres from tags
	genres := []string{}
	if tags, ok := game["tags"].([]interface{}); ok {
		for _, t := range tags {
			if s, ok := t.(string); ok {
				genres = append(genres, s)
			}
		}
	} else if tagsStr := getString(game, "tags"); tagsStr != "" {
		for _, g := range strings.Split(tagsStr, ",") {
			genres = append(genres, strings.TrimSpace(g))
		}
	}

	// Companies
	companies := []string{}
	if dev := getString(game, "developer"); dev != "" {
		companies = append(companies, dev)
	}
	if pub := getString(game, "publisher"); pub != "" {
		found := false
		for _, c := range companies {
			if c == pub {
				found = true
				break
			}
		}
		if !found {
			companies = append(companies, pub)
		}
	}

	// Franchises from series
	franchises := []string{}
	if series, ok := game["series"].(string); ok && series != "" {
		franchises = []string{series}
	} else if seriesList, ok := game["series"].([]interface{}); ok {
		for _, s := range seriesList {
			if str, ok := s.(string); ok {
				franchises = append(franchises, str)
			}
		}
	}

	// Game modes
	gameModes := []string{}
	if playMode := getString(game, "playMode"); playMode != "" {
		gameModes = []string{playMode}
	}

	return retrometadata.GameMetadata{
		FirstReleaseDate: firstReleaseDate,
		ReleaseYear:      releaseYear,
		Genres:           genres,
		Franchises:       franchises,
		Companies:        companies,
		GameModes:        gameModes,
		Developer:        getString(game, "developer"),
		Publisher:        getString(game, "publisher"),
		RawData: map[string]any{
			"source":   getString(game, "source"),
			"status":   getString(game, "status"),
			"version":  getString(game, "version"),
			"language": getString(game, "language"),
			"library":  getString(game, "library"),
			"platform": getString(game, "platform"),
			"notes":    getString(game, "notes"),
		},
	}
}

// Heartbeat checks if the provider is available.
func (p *Provider) Heartbeat(ctx context.Context) error {
	if !p.config.Enabled {
		return ErrProviderDisabled
	}

	params := url.Values{}
	params.Set("smartSearch", "test")
	params.Set("filter", "false")

	_, err := p.request(ctx, "/search", params)
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

func parseYear(dateStr string) int {
	if len(dateStr) < 4 {
		return 0
	}
	year, _ := strconv.Atoi(dateStr[:4])
	return year
}

func cleanFilename(filename string) string {
	name := regexp.MustCompile(`\.[^.]+$`).ReplaceAllString(filename, "")
	name = regexp.MustCompile(`\s*[\(\[][^\)\]]*[\)\]]`).ReplaceAllString(name, "")
	// Remove UUID patterns
	name = uuidRegex.ReplaceAllString(name, "")
	return strings.TrimSpace(name)
}

func findBestMatch(query string, candidates []string) (string, float64) {
	if len(candidates) == 0 {
		return "", 0
	}

	queryLower := strings.ToLower(query)
	bestMatch := ""
	bestScore := 0.0

	for _, candidate := range candidates {
		candidateLower := strings.ToLower(candidate)

		if candidateLower == queryLower {
			return candidate, 1.0
		}

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

	return candidates[0], 0.5
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
