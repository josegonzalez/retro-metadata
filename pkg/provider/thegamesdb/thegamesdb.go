// Package thegamesdb provides metadata from TheGamesDB.
package thegamesdb

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
	// Regex to detect TheGamesDB ID tags in filenames like (tgdb-12345)
	tgdbTagRegex = regexp.MustCompile(`(?i)\(tgdb-(\d+)\)`)

	// ErrProviderDisabled is returned when the provider is disabled.
	ErrProviderDisabled = fmt.Errorf("provider is disabled")
)

// Provider implements the TheGamesDB metadata provider.
type Provider struct {
	config    *retrometadata.ProviderConfig
	client    *http.Client
	baseURL   string
	userAgent string
}

// New creates a new TheGamesDB provider.
func New(config *retrometadata.ProviderConfig) *Provider {
	timeout := time.Duration(config.Timeout) * time.Second
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &Provider{
		config:    config,
		client:    &http.Client{Timeout: timeout},
		baseURL:   "https://api.thegamesdb.net/v1",
		userAgent: "retro-metadata/1.0",
	}
}

// Name returns the provider name.
func (p *Provider) Name() string {
	return "thegamesdb"
}

func (p *Provider) apiKey() string {
	return p.config.GetCredential("api_key")
}

func (p *Provider) request(ctx context.Context, endpoint string, params url.Values) (map[string]interface{}, error) {
	if params == nil {
		params = url.Values{}
	}
	params.Set("apikey", p.apiKey())

	reqURL := p.baseURL + endpoint + "?" + params.Encode()

	req, err := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", p.userAgent)

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

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	params := url.Values{}
	params.Set("name", query)
	params.Set("fields", "players,publishers,genres,overview,rating")
	params.Set("include", "boxart")

	if opts.PlatformID != nil {
		params.Set("filter[platform]", strconv.Itoa(*opts.PlatformID))
	}

	result, err := p.request(ctx, "/Games/ByGameName", params)
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, nil
	}

	games, ok := data["games"].([]interface{})
	if !ok {
		return nil, nil
	}

	boxartData := getBoxartData(result)
	baseURL := getBoxartBaseURL(boxartData)

	limit := opts.Limit
	if limit == 0 {
		limit = 20
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

		gameID := int(getFloat64(game, "id"))
		if gameID == 0 {
			continue
		}

		// Get cover image
		coverURL := getCoverURL(boxartData, gameID, baseURL)

		var releaseYear *int
		if dateStr := getString(game, "release_date"); dateStr != "" && len(dateStr) >= 4 {
			if year, err := strconv.Atoi(dateStr[:4]); err == nil {
				releaseYear = &year
			}
		}

		results = append(results, retrometadata.SearchResult{
			Name:        getString(game, "game_title"),
			Provider:    p.Name(),
			ProviderID:  gameID,
			CoverURL:    coverURL,
			Platforms:   []string{strconv.Itoa(int(getFloat64(game, "platform")))},
			ReleaseYear: releaseYear,
		})
	}

	return results, nil
}

// GetByID gets game details by TheGamesDB ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	params := url.Values{}
	params.Set("id", strconv.Itoa(gameID))
	params.Set("fields", "players,publishers,genres,overview,rating,platform")
	params.Set("include", "boxart")

	result, err := p.request(ctx, "/Games/ByGameID", params)
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, nil
	}

	games, ok := data["games"].([]interface{})
	if !ok || len(games) == 0 {
		// Try as a map
		gamesMap, ok := data["games"].(map[string]interface{})
		if !ok {
			return nil, nil
		}
		game, ok := gamesMap[strconv.Itoa(gameID)].(map[string]interface{})
		if !ok {
			return nil, nil
		}
		return p.buildGameResult(game, getBoxartData(result)), nil
	}

	game, ok := games[0].(map[string]interface{})
	if !ok {
		return nil, nil
	}

	return p.buildGameResult(game, getBoxartData(result)), nil
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	// Check for TheGamesDB ID tag in filename
	if matches := tgdbTagRegex.FindStringSubmatch(filename); len(matches) > 1 {
		var taggedID int
		if _, err := fmt.Sscanf(matches[1], "%d", &taggedID); err == nil {
			result, err := p.GetByID(ctx, taggedID)
			if err == nil && result != nil {
				return result, nil
			}
		}
	}

	if opts.PlatformID == nil {
		return nil, nil
	}

	// Clean the filename
	searchTerm := cleanFilename(filename)

	params := url.Values{}
	params.Set("name", searchTerm)
	params.Set("filter[platform]", strconv.Itoa(*opts.PlatformID))
	params.Set("fields", "players,publishers,genres,overview,rating")
	params.Set("include", "boxart")

	result, err := p.request(ctx, "/Games/ByGameName", params)
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].(map[string]interface{})
	if !ok {
		return nil, nil
	}

	games, ok := data["games"].([]interface{})
	if !ok || len(games) == 0 {
		return nil, nil
	}

	boxartData := getBoxartData(result)

	// Build name to game map
	gamesByName := make(map[string]map[string]interface{})
	for _, item := range games {
		if game, ok := item.(map[string]interface{}); ok {
			if name := getString(game, "game_title"); name != "" {
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
	gameResult := p.buildGameResult(game, boxartData)
	gameResult.MatchScore = score
	return gameResult, nil
}

func (p *Provider) buildGameResult(game map[string]interface{}, boxartData map[string]interface{}) *retrometadata.GameResult {
	gameID := int(getFloat64(game, "id"))
	baseURL := getBoxartBaseURL(boxartData)

	coverURL := getCoverURL(boxartData, gameID, baseURL)
	screenshotURLs := getBackCoverURLs(boxartData, gameID, baseURL)

	metadata := p.extractMetadata(game)

	providerID := gameID
	return &retrometadata.GameResult{
		Name:       getString(game, "game_title"),
		Summary:    getString(game, "overview"),
		Provider:   p.Name(),
		ProviderID: &providerID,
		ProviderIDs: map[string]int{
			"thegamesdb": gameID,
		},
		Artwork: retrometadata.Artwork{
			CoverURL:       coverURL,
			ScreenshotURLs: screenshotURLs,
		},
		Metadata:    metadata,
		RawResponse: game,
	}
}

func (p *Provider) extractMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	var releaseYear *int
	if dateStr := getString(game, "release_date"); dateStr != "" && len(dateStr) >= 4 {
		if year, err := strconv.Atoi(dateStr[:4]); err == nil {
			releaseYear = &year
		}
	}

	// Genres
	genres := []string{}
	if genresData, ok := game["genres"].([]interface{}); ok {
		for _, g := range genresData {
			if gs, ok := g.(string); ok {
				genres = append(genres, gs)
			}
		}
	} else if genresMap, ok := game["genres"].(map[string]interface{}); ok {
		for _, v := range genresMap {
			if gs, ok := v.(string); ok {
				genres = append(genres, gs)
			}
		}
	}

	// Player count
	playerCount := strconv.Itoa(int(getFloat64(game, "players")))
	if playerCount == "0" {
		playerCount = "1"
	}

	// Rating
	var totalRating *float64
	if rating := getString(game, "rating"); rating != "" {
		// TGDB uses "Rating: X.XX/10" format
		if strings.Contains(rating, "/") {
			parts := strings.Split(rating, "/")
			numStr := strings.TrimPrefix(parts[0], "Rating: ")
			if num, err := strconv.ParseFloat(strings.TrimSpace(numStr), 64); err == nil {
				r := num * 10
				totalRating = &r
			}
		} else if num, err := strconv.ParseFloat(rating, 64); err == nil {
			r := num * 10
			totalRating = &r
		}
	}

	// Publishers and Developers
	publishers := getStringSliceOrMap(game, "publishers")
	developers := getStringSliceOrMap(game, "developers")

	companies := append(publishers, developers...)
	// Remove duplicates
	seen := make(map[string]bool)
	uniqueCompanies := []string{}
	for _, c := range companies {
		if !seen[c] {
			seen[c] = true
			uniqueCompanies = append(uniqueCompanies, c)
		}
	}

	developer := ""
	if len(developers) > 0 {
		developer = developers[0]
	}

	publisher := ""
	if len(publishers) > 0 {
		publisher = publishers[0]
	}

	return retrometadata.GameMetadata{
		TotalRating: totalRating,
		Genres:      genres,
		Companies:   uniqueCompanies,
		PlayerCount: playerCount,
		ReleaseYear: releaseYear,
		Developer:   developer,
		Publisher:   publisher,
		RawData:     game,
	}
}

// Heartbeat checks if the provider is available.
func (p *Provider) Heartbeat(ctx context.Context) error {
	if !p.config.Enabled {
		return ErrProviderDisabled
	}

	// Try a simple search to check connectivity
	params := url.Values{}
	params.Set("name", "test")
	_, err := p.request(ctx, "/Games/ByGameName", params)
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

func getStringSliceOrMap(m map[string]interface{}, key string) []string {
	result := []string{}
	if arr, ok := m[key].([]interface{}); ok {
		for _, v := range arr {
			if s, ok := v.(string); ok {
				result = append(result, s)
			}
		}
	} else if mapData, ok := m[key].(map[string]interface{}); ok {
		for _, v := range mapData {
			if s, ok := v.(string); ok {
				result = append(result, s)
			}
		}
	}
	return result
}

func getBoxartData(result map[string]interface{}) map[string]interface{} {
	include, ok := result["include"].(map[string]interface{})
	if !ok {
		return nil
	}
	boxart, ok := include["boxart"].(map[string]interface{})
	if !ok {
		return nil
	}
	return boxart
}

func getBoxartBaseURL(boxartData map[string]interface{}) map[string]string {
	if boxartData == nil {
		return nil
	}
	baseURL, ok := boxartData["base_url"].(map[string]interface{})
	if !ok {
		return nil
	}
	result := make(map[string]string)
	for k, v := range baseURL {
		if s, ok := v.(string); ok {
			result[k] = s
		}
	}
	return result
}

func getCoverURL(boxartData map[string]interface{}, gameID int, baseURL map[string]string) string {
	if boxartData == nil || baseURL == nil {
		return ""
	}

	data, ok := boxartData["data"].(map[string]interface{})
	if !ok {
		return ""
	}

	gameBoxart, ok := data[strconv.Itoa(gameID)].([]interface{})
	if !ok {
		return ""
	}

	for _, art := range gameBoxart {
		artMap, ok := art.(map[string]interface{})
		if !ok {
			continue
		}
		if getString(artMap, "side") == "front" {
			if thumb, ok := baseURL["thumb"]; ok {
				return thumb + getString(artMap, "filename")
			}
		}
	}
	return ""
}

func getBackCoverURLs(boxartData map[string]interface{}, gameID int, baseURL map[string]string) []string {
	if boxartData == nil || baseURL == nil {
		return nil
	}

	data, ok := boxartData["data"].(map[string]interface{})
	if !ok {
		return nil
	}

	gameBoxart, ok := data[strconv.Itoa(gameID)].([]interface{})
	if !ok {
		return nil
	}

	var urls []string
	for _, art := range gameBoxart {
		artMap, ok := art.(map[string]interface{})
		if !ok {
			continue
		}
		if getString(artMap, "side") == "back" {
			if original, ok := baseURL["original"]; ok {
				urls = append(urls, original+getString(artMap, "filename"))
			}
		}
	}
	return urls
}

func cleanFilename(filename string) string {
	name := regexp.MustCompile(`\.[^.]+$`).ReplaceAllString(filename, "")
	name = regexp.MustCompile(`\s*[\(\[][^\)\]]*[\)\]]`).ReplaceAllString(name, "")
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
