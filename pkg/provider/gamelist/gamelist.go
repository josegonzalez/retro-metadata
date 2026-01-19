// Package gamelist provides metadata from local gamelist.xml files (EmulationStation format).
package gamelist

import (
	"context"
	"encoding/xml"
	"fmt"
	"hash/fnv"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	retrometadata "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

var (
	// XML tag to media URL key mapping
	xmlTagMap = map[string]string{
		"image":         "image_url",
		"cover":         "box2d_url",
		"backcover":     "box2d_back_url",
		"box3d":         "box3d_url",
		"fanart":        "fanart_url",
		"manual":        "manual_url",
		"marquee":       "marquee_url",
		"miximage":      "miximage_url",
		"physicalmedia": "physical_url",
		"screenshot":    "screenshot_url",
		"title_screen":  "title_screen_url",
		"thumbnail":     "thumbnail_url",
		"video":         "video_url",
	}

	// ES-DE media folder mapping
	esdeMediaMap = map[string]string{
		"image_url":        "images",
		"box2d_url":        "covers",
		"box2d_back_url":   "backcovers",
		"box3d_url":        "3dboxes",
		"fanart_url":       "fanart",
		"manual_url":       "manuals",
		"marquee_url":      "marquees",
		"miximage_url":     "miximages",
		"physical_url":     "physicalmedia",
		"screenshot_url":   "screenshots",
		"title_screen_url": "titlescreens",
		"thumbnail_url":    "thumbnails",
		"video_url":        "videos",
	}

	// ErrProviderDisabled is returned when the provider is disabled.
	ErrProviderDisabled = fmt.Errorf("provider is disabled")
)

// Provider implements the Gamelist metadata provider.
type Provider struct {
	config          *retrometadata.ProviderConfig
	romsPath        string
	gamesByFilename map[string]map[string]string
	gamesByPath     map[string]map[string]string
	platformDir     string
	loaded          bool
}

// New creates a new Gamelist provider.
func New(config *retrometadata.ProviderConfig) *Provider {
	romsPath := ""
	if config.Options != nil {
		if path, ok := config.Options["roms_path"].(string); ok {
			romsPath = path
		}
	}

	return &Provider{
		config:          config,
		romsPath:        romsPath,
		gamesByFilename: make(map[string]map[string]string),
		gamesByPath:     make(map[string]map[string]string),
	}
}

// Name returns the provider name.
func (p *Provider) Name() string {
	return "gamelist"
}

// LoadGamelist loads games from a gamelist.xml file.
func (p *Provider) LoadGamelist(ctx context.Context, gamelistPath string, platformDir string) error {
	if gamelistPath == "" {
		return fmt.Errorf("no gamelist path provided")
	}

	file, err := os.Open(gamelistPath)
	if err != nil {
		return err
	}
	defer file.Close()

	if platformDir != "" {
		p.platformDir = platformDir
	} else {
		p.platformDir = filepath.Dir(gamelistPath)
	}

	decoder := xml.NewDecoder(file)
	for {
		token, err := decoder.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}

		switch se := token.(type) {
		case xml.StartElement:
			if se.Name.Local == "game" {
				game := make(map[string]string)
				if err := parseGame(decoder, &se, game, p.platformDir); err != nil {
					continue
				}

				// Index by filename
				gamePath := game["path"]
				if gamePath != "" {
					filename := filepath.Base(gamePath)
					p.gamesByFilename[filename] = game
					p.gamesByPath[gamePath] = game
				}
			}
		}
	}

	p.loaded = true
	return nil
}

func parseGame(decoder *xml.Decoder, start *xml.StartElement, game map[string]string, platformDir string) error {
	coreFields := []string{"path", "name", "desc", "rating", "releasedate", "developer",
		"publisher", "genre", "players", "md5", "lang", "region", "family"}

	for {
		token, err := decoder.Token()
		if err != nil {
			return err
		}

		switch t := token.(type) {
		case xml.StartElement:
			var content string
			if err := decoder.DecodeElement(&content, &t); err != nil {
				continue
			}

			tagName := t.Name.Local

			// Core fields
			for _, field := range coreFields {
				if tagName == field {
					game[tagName] = content
					break
				}
			}

			// Media fields
			if mediaKey, ok := xmlTagMap[tagName]; ok {
				game[mediaKey] = resolvePath(content, platformDir)
			}

		case xml.EndElement:
			if t.Name.Local == start.Name.Local {
				// Try to find media in ES-DE folder structure
				romPath := game["path"]
				if romPath != "" {
					romStem := strings.TrimSuffix(filepath.Base(romPath), filepath.Ext(romPath))
					for mediaKey, folderName := range esdeMediaMap {
						if _, exists := game[mediaKey]; !exists {
							mediaPath := findMediaFile(romStem, folderName, platformDir)
							if mediaPath != "" {
								game[mediaKey] = mediaPath
							}
						}
					}
				}
				return nil
			}
		}
	}
}

func resolvePath(path string, platformDir string) string {
	path = strings.TrimPrefix(path, "./")

	if platformDir != "" {
		fullPath := filepath.Join(platformDir, path)
		if _, err := os.Stat(fullPath); err == nil {
			absPath, _ := filepath.Abs(fullPath)
			return "file://" + absPath
		}
	}

	return path
}

func findMediaFile(romStem, folderName, platformDir string) string {
	if platformDir == "" {
		return ""
	}

	searchPattern := filepath.Join(platformDir, folderName, romStem+".*")
	matches, err := filepath.Glob(searchPattern)
	if err != nil || len(matches) == 0 {
		return ""
	}

	absPath, _ := filepath.Abs(matches[0])
	return "file://" + absPath
}

func hashFilename(filename string) int {
	h := fnv.New32a()
	h.Write([]byte(filename))
	return int(h.Sum32())
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	if !p.loaded {
		return nil, nil
	}

	queryLower := strings.ToLower(query)
	limit := opts.Limit
	if limit == 0 {
		limit = 20
	}

	var results []retrometadata.SearchResult
	for filename, game := range p.gamesByFilename {
		name := game["name"]
		if !strings.Contains(strings.ToLower(name), queryLower) &&
			!strings.Contains(strings.ToLower(filename), queryLower) {
			continue
		}

		coverURL := game["box2d_url"]
		if coverURL == "" {
			coverURL = game["image_url"]
		}

		results = append(results, retrometadata.SearchResult{
			Name:       name,
			Provider:   p.Name(),
			ProviderID: hashFilename(filename),
			CoverURL:   coverURL,
			Platforms:  []string{},
		})

		if len(results) >= limit {
			break
		}
	}

	return results, nil
}

// GetByID gets game details by ID (hash of filename).
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.config.Enabled || !p.loaded {
		return nil, nil
	}

	// Find by matching hash
	for filename, game := range p.gamesByFilename {
		if hashFilename(filename) == gameID {
			return p.buildGameResult(game, filename), nil
		}
	}

	return nil, nil
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.config.Enabled || !p.loaded {
		return nil, nil
	}

	// Try exact match first
	if game, ok := p.gamesByFilename[filename]; ok {
		return p.buildGameResult(game, filename), nil
	}

	// Try fuzzy match
	var names []string
	for name := range p.gamesByFilename {
		names = append(names, name)
	}

	bestMatch, score := findBestMatch(filename, names)
	if bestMatch == "" {
		return nil, nil
	}

	game := p.gamesByFilename[bestMatch]
	result := p.buildGameResult(game, bestMatch)
	result.MatchScore = score
	return result, nil
}

func (p *Provider) buildGameResult(game map[string]string, filename string) *retrometadata.GameResult {
	// Get artwork
	coverURL := game["box2d_url"]
	if coverURL == "" {
		coverURL = game["image_url"]
	}

	var screenshotURLs []string
	for _, key := range []string{"screenshot_url", "title_screen_url", "fanart_url"} {
		if url := game[key]; url != "" {
			screenshotURLs = append(screenshotURLs, url)
		}
	}

	metadata := p.extractMetadata(game)

	providerID := hashFilename(filename)
	return &retrometadata.GameResult{
		Name:       game["name"],
		Summary:    game["desc"],
		Provider:   p.Name(),
		ProviderID: &providerID,
		ProviderIDs: map[string]int{
			"gamelist": hashFilename(filename),
		},
		Artwork: retrometadata.Artwork{
			CoverURL:       coverURL,
			ScreenshotURLs: screenshotURLs,
			LogoURL:        game["marquee_url"],
		},
		Metadata:    metadata,
		RawResponse: stringMapToAnyMap(game),
	}
}

func (p *Provider) extractMetadata(game map[string]string) retrometadata.GameMetadata {
	// Rating (gamelist uses 0-1 scale)
	var totalRating *float64
	if ratingStr := game["rating"]; ratingStr != "" {
		if rating, err := strconv.ParseFloat(ratingStr, 64); err == nil {
			r := rating * 100
			totalRating = &r
		}
	}

	// Release year
	var releaseYear *int
	if releasedate := game["releasedate"]; releasedate != "" && len(releasedate) >= 4 {
		if year, err := strconv.Atoi(releasedate[:4]); err == nil {
			releaseYear = &year
		}
	}

	// Genres
	genres := []string{}
	if genre := game["genre"]; genre != "" {
		for _, g := range strings.Split(genre, ",") {
			genres = append(genres, strings.TrimSpace(g))
		}
	}

	// Companies
	companies := []string{}
	if dev := game["developer"]; dev != "" {
		companies = append(companies, dev)
	}
	if pub := game["publisher"]; pub != "" && pub != game["developer"] {
		companies = append(companies, pub)
	}

	// Franchises
	franchises := []string{}
	if family := game["family"]; family != "" {
		franchises = []string{family}
	}

	// Player count
	playerCount := game["players"]
	if playerCount == "" {
		playerCount = "1"
	}

	return retrometadata.GameMetadata{
		TotalRating: totalRating,
		Genres:      genres,
		Franchises:  franchises,
		Companies:   companies,
		PlayerCount: playerCount,
		Developer:   game["developer"],
		Publisher:   game["publisher"],
		ReleaseYear: releaseYear,
		RawData:     stringMapToAnyMap(game),
	}
}

// ClearCache clears the loaded gamelist data.
func (p *Provider) ClearCache() {
	p.gamesByFilename = make(map[string]map[string]string)
	p.gamesByPath = make(map[string]map[string]string)
	p.platformDir = ""
	p.loaded = false
}

// Heartbeat checks if the provider is available.
func (p *Provider) Heartbeat(ctx context.Context) error {
	if !p.config.Enabled {
		return ErrProviderDisabled
	}

	// Gamelist is a local file provider, just check if enabled
	return nil
}

// Close clears loaded data.
func (p *Provider) Close() error {
	p.ClearCache()
	return nil
}

// Helper functions

func stringMapToAnyMap(m map[string]string) map[string]any {
	result := make(map[string]any, len(m))
	for k, v := range m {
		result[k] = v
	}
	return result
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

	if len(candidates) > 0 {
		return candidates[0], 0.5
	}

	return "", 0
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
