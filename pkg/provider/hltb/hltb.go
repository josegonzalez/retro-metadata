// Package hltb provides metadata from HowLongToBeat.
package hltb

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"

	retrometadata "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

const (
	hltbImageURL          = "https://howlongtobeat.com/games/"
	githubHLTBAPIURL      = "https://raw.githubusercontent.com/rommapp/romm/refs/heads/master/backend/handler/metadata/fixtures/hltb_api_url"
	defaultSearchEndpoint = "search"
)

var (
	// Regex to detect HLTB ID tags in filenames like (hltb-12345)
	hltbTagRegex = regexp.MustCompile(`(?i)\(hltb-(\d+)\)`)

	// ErrProviderDisabled is returned when the provider is disabled.
	ErrProviderDisabled = fmt.Errorf("provider is disabled")
)

// Provider implements the HowLongToBeat metadata provider.
type Provider struct {
	config         *retrometadata.ProviderConfig
	client         *http.Client
	baseURL        string
	userAgent      string
	securityToken  string
	searchEndpoint string
}

// New creates a new HLTB provider.
func New(config *retrometadata.ProviderConfig) *Provider {
	timeout := time.Duration(config.Timeout) * time.Second
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &Provider{
		config:    config,
		client:    &http.Client{Timeout: timeout},
		baseURL:   "https://howlongtobeat.com/api",
		userAgent: "retro-metadata/1.0",
	}
}

// Name returns the provider name.
func (p *Provider) Name() string {
	return "hltb"
}

func (p *Provider) fetchSearchEndpoint(ctx context.Context) string {
	if p.searchEndpoint != "" {
		return p.searchEndpoint
	}

	req, err := http.NewRequestWithContext(ctx, "GET", githubHLTBAPIURL, nil)
	if err != nil {
		p.searchEndpoint = defaultSearchEndpoint
		return p.searchEndpoint
	}

	resp, err := p.client.Do(req)
	if err != nil {
		p.searchEndpoint = defaultSearchEndpoint
		return p.searchEndpoint
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		p.searchEndpoint = defaultSearchEndpoint
		return p.searchEndpoint
	}

	p.searchEndpoint = strings.TrimSpace(string(body))
	return p.searchEndpoint
}

func (p *Provider) fetchSecurityToken(ctx context.Context) string {
	if p.securityToken != "" {
		return p.securityToken
	}

	req, err := http.NewRequestWithContext(ctx, "GET", p.baseURL+"/search/init", nil)
	if err != nil {
		return ""
	}

	req.Header.Set("User-Agent", p.userAgent)

	resp, err := p.client.Do(req)
	if err != nil {
		return ""
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return ""
	}

	if token, ok := result["token"].(string); ok {
		p.securityToken = token
	}

	return p.securityToken
}

func (p *Provider) request(ctx context.Context, endpoint string, data map[string]interface{}) (map[string]interface{}, error) {
	// Use dynamic search endpoint if this is a search request
	if endpoint == "search" {
		endpoint = p.fetchSearchEndpoint(ctx)
	}

	url := p.baseURL + "/" + endpoint

	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(jsonData))
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", p.userAgent)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Origin", "https://howlongtobeat.com")
	req.Header.Set("Referer", "https://howlongtobeat.com")

	// Add security token if available
	if token := p.fetchSecurityToken(ctx); token != "" {
		req.Header.Set("X-Auth-Token", token)
	}

	resp, err := p.client.Do(req)
	if err != nil {
		return nil, &retrometadata.ConnectionError{Provider: p.Name(), Details: err.Error()}
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, &retrometadata.ConnectionError{Provider: p.Name(), Details: fmt.Sprintf("HTTP %d", resp.StatusCode)}
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result, nil
}

func buildSearchData(query string, limit int) map[string]interface{} {
	return map[string]interface{}{
		"searchType":  "games",
		"searchTerms": strings.Split(query, " "),
		"searchPage":  1,
		"size":        limit,
		"searchOptions": map[string]interface{}{
			"games": map[string]interface{}{
				"userId":        0,
				"platform":      "",
				"sortCategory":  "popular",
				"rangeCategory": "main",
				"rangeTime":     map[string]interface{}{"min": 0, "max": 0},
				"gameplay":      map[string]interface{}{"perspective": "", "flow": "", "genre": ""},
				"modifier":      "",
			},
			"users":      map[string]interface{}{"sortCategory": "postcount"},
			"filter":     "",
			"sort":       0,
			"randomizer": 0,
		},
	}
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	limit := opts.Limit
	if limit == 0 {
		limit = 20
	}

	result, err := p.request(ctx, "search", buildSearchData(query, limit))
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, nil
	}

	var results []retrometadata.SearchResult
	for _, item := range data {
		game, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		gameID := int(getFloat64(game, "game_id"))
		if gameID == 0 {
			continue
		}

		coverURL := ""
		if img := getString(game, "game_image"); img != "" {
			coverURL = hltbImageURL + img
		}

		var releaseYear *int
		if year := int(getFloat64(game, "release_world")); year > 0 {
			releaseYear = &year
		}

		platforms := []string{}
		if platform := getString(game, "profile_platform"); platform != "" {
			platforms = strings.Split(platform, ", ")
		}

		results = append(results, retrometadata.SearchResult{
			Name:        getString(game, "game_name"),
			Provider:    p.Name(),
			ProviderID:  gameID,
			CoverURL:    coverURL,
			Platforms:   platforms,
			ReleaseYear: releaseYear,
		})
	}

	return results, nil
}

// GetByID gets game details by HLTB ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	searchData := buildSearchData("", 1)
	searchData["gameId"] = gameID

	result, err := p.request(ctx, "search", searchData)
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].([]interface{})
	if !ok || len(data) == 0 {
		return nil, nil
	}

	game, ok := data[0].(map[string]interface{})
	if !ok {
		return nil, nil
	}

	return p.buildGameResult(game), nil
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	// Check for HLTB ID tag in filename
	if matches := hltbTagRegex.FindStringSubmatch(filename); len(matches) > 1 {
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
	result, err := p.request(ctx, "search", buildSearchData(searchTerm, 20))
	if err != nil {
		return nil, err
	}

	data, ok := result["data"].([]interface{})
	if !ok || len(data) == 0 {
		return nil, nil
	}

	// Build name to game map
	gamesByName := make(map[string]map[string]interface{})
	for _, item := range data {
		if game, ok := item.(map[string]interface{}); ok {
			if name := getString(game, "game_name"); name != "" {
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
	gameID := int(getFloat64(game, "game_id"))

	coverURL := ""
	if img := getString(game, "game_image"); img != "" {
		coverURL = hltbImageURL + img
	}

	metadata := p.extractMetadata(game)

	providerID := gameID
	return &retrometadata.GameResult{
		Name:       getString(game, "game_name"),
		Provider:   p.Name(),
		ProviderID: &providerID,
		ProviderIDs: map[string]int{
			"hltb": gameID,
		},
		Artwork: retrometadata.Artwork{
			CoverURL: coverURL,
		},
		Metadata:    metadata,
		RawResponse: game,
	}
}

func (p *Provider) extractMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	var releaseYear *int
	if year := int(getFloat64(game, "release_world")); year > 0 {
		releaseYear = &year
	}

	var totalRating *float64
	if score := getFloat64(game, "review_score"); score > 0 {
		totalRating = &score
	}

	gameModes := []string{}
	if getFloat64(game, "comp_main") > 0 {
		gameModes = append(gameModes, "Single Player")
	}
	if getFloat64(game, "comp_plus") > 0 {
		gameModes = append(gameModes, "Completionist")
	}

	developer := getString(game, "profile_dev")

	platformsStr := getString(game, "profile_platform")
	platforms := []string{}
	if platformsStr != "" {
		platforms = strings.Split(platformsStr, ",")
		for i := range platforms {
			platforms[i] = strings.TrimSpace(platforms[i])
		}
	}

	return retrometadata.GameMetadata{
		ReleaseYear: releaseYear,
		TotalRating: totalRating,
		GameModes:   gameModes,
		Developer:   developer,
		RawData: map[string]any{
			"main_story":       getFloat64(game, "comp_main"),
			"main_plus_extras": getFloat64(game, "comp_plus"),
			"completionist":    getFloat64(game, "comp_100"),
			"all_styles":       getFloat64(game, "comp_all"),
			"platforms":        platforms,
			"profile_popular":  getFloat64(game, "profile_popular"),
			"count_comp":       getFloat64(game, "count_comp"),
			"count_playing":    getFloat64(game, "count_playing"),
			"count_backlog":    getFloat64(game, "count_backlog"),
			"count_replay":     getFloat64(game, "count_replay"),
			"count_retired":    getFloat64(game, "count_retired"),
			"review_score":     getFloat64(game, "review_score"),
		},
	}
}

// GetCompletionTimes returns completion times for a game.
func (p *Provider) GetCompletionTimes(ctx context.Context, gameID int) (map[string]float64, error) {
	result, err := p.GetByID(ctx, gameID)
	if err != nil || result == nil {
		return nil, err
	}

	times := make(map[string]float64)
	if rawData := result.Metadata.RawData; rawData != nil {
		if v, ok := rawData["main_story"].(float64); ok {
			times["main_story"] = v
		}
		if v, ok := rawData["main_plus_extras"].(float64); ok {
			times["main_plus_extras"] = v
		}
		if v, ok := rawData["completionist"].(float64); ok {
			times["completionist"] = v
		}
		if v, ok := rawData["all_styles"].(float64); ok {
			times["all_styles"] = v
		}
	}

	return times, nil
}

// Heartbeat checks if the provider is available.
func (p *Provider) Heartbeat(ctx context.Context) error {
	if !p.config.Enabled {
		return ErrProviderDisabled
	}

	// Try to fetch the security token to check connectivity
	token := p.fetchSecurityToken(ctx)
	if token == "" {
		return &retrometadata.ConnectionError{Provider: p.Name(), Details: "failed to get security token"}
	}
	return nil
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
