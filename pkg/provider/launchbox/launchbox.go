// Package launchbox provides metadata from local LaunchBox XML files.
package launchbox

import (
	"context"
	"encoding/xml"
	"fmt"
	"io"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	retrometadata "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

const (
	launchboxImageURL = "https://images.launchbox-app.com"
)

var (
	// Regex to detect LaunchBox ID tags in filenames like (launchbox-12345)
	launchboxTagRegex = regexp.MustCompile(`(?i)\(launchbox-(\d+)\)`)

	// Cover image type priority
	coverPriority = []string{
		"Box - Front",
		"Box - 3D",
		"Fanart - Box - Front",
		"Cart - Front",
		"Cart - 3D",
	}

	// ErrProviderDisabled is returned when the provider is disabled.
	ErrProviderDisabled = fmt.Errorf("provider is disabled")
)

// Provider implements the LaunchBox metadata provider.
type Provider struct {
	config        *retrometadata.ProviderConfig
	metadataPath  string
	gamesByID     map[int]map[string]string
	gamesByName   map[string]map[int]map[string]string // name -> platformID -> game
	imagesByID    map[int][]map[string]string
	loaded        bool
}

// New creates a new LaunchBox provider.
func New(config *retrometadata.ProviderConfig) *Provider {
	metadataPath := ""
	if config.Options != nil {
		if path, ok := config.Options["metadata_path"].(string); ok {
			metadataPath = path
		}
	}

	return &Provider{
		config:       config,
		metadataPath: metadataPath,
		gamesByID:    make(map[int]map[string]string),
		gamesByName:  make(map[string]map[int]map[string]string),
		imagesByID:   make(map[int][]map[string]string),
	}
}

// Name returns the provider name.
func (p *Provider) Name() string {
	return "launchbox"
}

// LoadMetadata loads metadata from LaunchBox XML files.
func (p *Provider) LoadMetadata(ctx context.Context, path string) error {
	if path == "" {
		path = p.metadataPath
	}
	if path == "" {
		return fmt.Errorf("no metadata path provided")
	}

	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()

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
			if se.Name.Local == "Game" {
				game := make(map[string]string)
				if err := parseGame(decoder, &se, game); err != nil {
					continue
				}

				dbIDStr := game["DatabaseID"]
				if dbIDStr == "" {
					continue
				}

				dbID, err := strconv.Atoi(dbIDStr)
				if err != nil {
					continue
				}

				p.gamesByID[dbID] = game

				// Index by name and platform
				nameLower := strings.ToLower(game["Name"])
				if nameLower != "" {
					if _, ok := p.gamesByName[nameLower]; !ok {
						p.gamesByName[nameLower] = make(map[int]map[string]string)
					}
					platformID := getPlatformIDByName(game["Platform"])
					if platformID > 0 {
						p.gamesByName[nameLower][platformID] = game
					}
				}
			}
		}
	}

	// Try to load images from a separate Images.xml file
	imagesPath := strings.TrimSuffix(path, ".xml") + "/../Images.xml"
	if imagesFile, err := os.Open(imagesPath); err == nil {
		defer imagesFile.Close()
		p.loadImages(imagesFile)
	}

	p.loaded = true
	return nil
}

func (p *Provider) loadImages(file *os.File) {
	decoder := xml.NewDecoder(file)
	for {
		token, err := decoder.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return
		}

		switch se := token.(type) {
		case xml.StartElement:
			if se.Name.Local == "GameImage" {
				image := make(map[string]string)
				if err := parseGame(decoder, &se, image); err != nil {
					continue
				}

				dbIDStr := image["DatabaseID"]
				if dbIDStr == "" {
					continue
				}

				dbID, err := strconv.Atoi(dbIDStr)
				if err != nil {
					continue
				}

				p.imagesByID[dbID] = append(p.imagesByID[dbID], image)
			}
		}
	}
}

func parseGame(decoder *xml.Decoder, start *xml.StartElement, game map[string]string) error {
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
			game[t.Name.Local] = content
		case xml.EndElement:
			if t.Name.Local == start.Name.Local {
				return nil
			}
		}
	}
}

func getPlatformIDByName(platformName string) int {
	// Simplified platform name to ID mapping
	platformMap := map[string]int{
		"3DO Interactive Multiplayer":          1,
		"Nintendo 3DS":                         24,
		"Amstrad CPC":                          3,
		"Commodore Amiga":                      2,
		"Android":                              4,
		"Arcade":                               5,
		"Atari 2600":                           6,
		"Atari 5200":                           7,
		"Atari 7800":                           8,
		"Nintendo Game Boy":                    17,
		"Nintendo Game Boy Advance":            18,
		"Nintendo Game Boy Color":              19,
		"Sega Game Gear":                       47,
		"Sega Genesis":                         49,
		"Sega Dreamcast":                       52,
		"Nintendo 64":                          25,
		"Nintendo DS":                          26,
		"Nintendo Entertainment System":        27,
		"Nintendo GameCube":                    20,
		"Nintendo Wii":                         29,
		"Nintendo Wii U":                       30,
		"Nintendo Switch":                      61,
		"Sony Playstation":                     55,
		"Sony Playstation 2":                   56,
		"Sony Playstation 3":                   57,
		"Sony PSP":                             58,
		"Sony Playstation Vita":                59,
		"Microsoft Xbox":                       31,
		"Microsoft Xbox 360":                   32,
		"Super Nintendo Entertainment System":  60,
	}
	return platformMap[platformName]
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	if !p.loaded {
		if err := p.LoadMetadata(ctx, ""); err != nil {
			return nil, err
		}
	}

	queryLower := strings.ToLower(query)
	limit := opts.Limit
	if limit == 0 {
		limit = 20
	}

	var results []retrometadata.SearchResult
	for name, platforms := range p.gamesByName {
		if !strings.Contains(name, queryLower) {
			continue
		}

		for platformID, game := range platforms {
			if opts.PlatformID != nil && platformID != *opts.PlatformID {
				continue
			}

			dbIDStr := game["DatabaseID"]
			dbID, _ := strconv.Atoi(dbIDStr)

			coverURL := p.getBestCover(dbID)

			var releaseYear *int
			if dateStr := game["ReleaseDate"]; dateStr != "" && len(dateStr) >= 4 {
				if year, err := strconv.Atoi(dateStr[:4]); err == nil {
					releaseYear = &year
				}
			}

			results = append(results, retrometadata.SearchResult{
				Name:        game["Name"],
				Provider:    p.Name(),
				ProviderID:  dbID,
				CoverURL:    coverURL,
				Platforms:   []string{game["Platform"]},
				ReleaseYear: releaseYear,
			})

			if len(results) >= limit {
				break
			}
		}

		if len(results) >= limit {
			break
		}
	}

	return results, nil
}

// GetByID gets game details by LaunchBox database ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	if !p.loaded {
		if err := p.LoadMetadata(ctx, ""); err != nil {
			return nil, err
		}
	}

	game, ok := p.gamesByID[gameID]
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

	// Check for LaunchBox ID tag in filename
	if matches := launchboxTagRegex.FindStringSubmatch(filename); len(matches) > 1 {
		var taggedID int
		if _, err := fmt.Sscanf(matches[1], "%d", &taggedID); err == nil {
			result, err := p.GetByID(ctx, taggedID)
			if err == nil && result != nil {
				return result, nil
			}
		}
	}

	if !p.loaded {
		if err := p.LoadMetadata(ctx, ""); err != nil {
			return nil, err
		}
	}

	// Clean the filename
	searchTerm := cleanFilename(filename)
	// LaunchBox uses ": " instead of " - "
	searchTerm = regexp.MustCompile(`\s?-\s`).ReplaceAllString(searchTerm, ": ")
	searchTermLower := strings.ToLower(searchTerm)

	// Look for exact match first
	if platforms, ok := p.gamesByName[searchTermLower]; ok {
		if opts.PlatformID != nil {
			if game, ok := platforms[*opts.PlatformID]; ok {
				return p.buildGameResult(game), nil
			}
		}
		// Return first match if no platform specified
		for _, game := range platforms {
			return p.buildGameResult(game), nil
		}
	}

	// Fuzzy match
	var names []string
	for name := range p.gamesByName {
		names = append(names, name)
	}

	bestMatch, score := findBestMatch(searchTermLower, names)
	if bestMatch == "" {
		return nil, nil
	}

	platforms := p.gamesByName[bestMatch]
	var game map[string]string
	if opts.PlatformID != nil {
		if g, ok := platforms[*opts.PlatformID]; ok {
			game = g
		}
	}
	if game == nil {
		for _, g := range platforms {
			game = g
			break
		}
	}

	if game == nil {
		return nil, nil
	}

	result := p.buildGameResult(game)
	result.MatchScore = score
	return result, nil
}

func (p *Provider) getBestCover(gameID int) string {
	images, ok := p.imagesByID[gameID]
	if !ok {
		return ""
	}

	for _, coverType := range coverPriority {
		for _, image := range images {
			if image["Type"] == coverType {
				if filename := image["FileName"]; filename != "" {
					return launchboxImageURL + "/" + filename
				}
			}
		}
	}

	return ""
}

func (p *Provider) getScreenshots(gameID int) []string {
	images, ok := p.imagesByID[gameID]
	if !ok {
		return nil
	}

	var screenshots []string
	for _, image := range images {
		if strings.Contains(image["Type"], "Screenshot") {
			if filename := image["FileName"]; filename != "" {
				screenshots = append(screenshots, launchboxImageURL+"/"+filename)
			}
		}
	}

	return screenshots
}

func (p *Provider) buildGameResult(game map[string]string) *retrometadata.GameResult {
	dbIDStr := game["DatabaseID"]
	dbID, _ := strconv.Atoi(dbIDStr)

	coverURL := p.getBestCover(dbID)
	screenshots := p.getScreenshots(dbID)

	metadata := p.extractMetadata(game)

	providerID := dbID
	return &retrometadata.GameResult{
		Name:       game["Name"],
		Summary:    game["Overview"],
		Provider:   p.Name(),
		ProviderID: &providerID,
		ProviderIDs: map[string]int{
			"launchbox": dbID,
		},
		Artwork: retrometadata.Artwork{
			CoverURL:       coverURL,
			ScreenshotURLs: screenshots,
		},
		Metadata:    metadata,
		RawResponse: stringMapToAnyMap(game),
	}
}

func (p *Provider) extractMetadata(game map[string]string) retrometadata.GameMetadata {
	var firstReleaseDate *int64
	var releaseYear *int
	if dateStr := game["ReleaseDate"]; dateStr != "" {
		if t, err := time.Parse("2006-01-02T15:04:05-07:00", dateStr); err == nil {
			ts := t.Unix()
			firstReleaseDate = &ts
			year := t.Year()
			releaseYear = &year
		}
	}

	// Genres
	genres := []string{}
	if genresStr := game["Genres"]; genresStr != "" {
		genres = strings.Split(genresStr, ";")
	}

	// Companies
	companies := []string{}
	if pub := game["Publisher"]; pub != "" {
		companies = append(companies, pub)
	}
	if dev := game["Developer"]; dev != "" && dev != game["Publisher"] {
		companies = append(companies, dev)
	}

	// Age rating
	var ageRatings []retrometadata.AgeRating
	if esrb := game["ESRB"]; esrb != "" {
		rating := strings.Split(esrb, " - ")[0]
		ageRatings = append(ageRatings, retrometadata.AgeRating{
			Rating:   strings.TrimSpace(rating),
			Category: "ESRB",
		})
	}

	// Player count
	playerCount := game["MaxPlayers"]
	if playerCount == "" {
		playerCount = "1"
	}

	// YouTube video
	youtubeVideoID := extractVideoID(game["VideoURL"])

	// Rating
	var totalRating *float64
	if ratingStr := game["CommunityRating"]; ratingStr != "" {
		if rating, err := strconv.ParseFloat(ratingStr, 64); err == nil {
			// LaunchBox ratings are 0-5, convert to 0-100
			r := rating * 20
			totalRating = &r
		}
	}

	// Game modes
	gameModes := []string{}
	if maxPlayers := game["MaxPlayers"]; maxPlayers != "" {
		if max, err := strconv.Atoi(maxPlayers); err == nil {
			if max == 1 {
				gameModes = append(gameModes, "Single player")
			}
			if max > 1 {
				gameModes = append(gameModes, "Multiplayer")
			}
		}
	}
	if strings.ToLower(game["Cooperative"]) == "true" {
		gameModes = append(gameModes, "Co-op")
	}

	return retrometadata.GameMetadata{
		TotalRating:      totalRating,
		FirstReleaseDate: firstReleaseDate,
		YouTubeVideoID:   youtubeVideoID,
		Genres:           genres,
		GameModes:        gameModes,
		Companies:        companies,
		AgeRatings:       ageRatings,
		PlayerCount:      playerCount,
		Developer:        game["Developer"],
		Publisher:        game["Publisher"],
		ReleaseYear:      releaseYear,
		RawData:          stringMapToAnyMap(game),
	}
}

func extractVideoID(url string) string {
	if url == "" {
		return ""
	}

	if strings.Contains(url, "youtube.com/watch?v=") {
		parts := strings.Split(url, "v=")
		if len(parts) > 1 {
			return strings.Split(parts[1], "&")[0]
		}
	} else if strings.Contains(url, "youtu.be/") {
		parts := strings.Split(url, "/")
		if len(parts) > 0 {
			return strings.Split(parts[len(parts)-1], "?")[0]
		}
	}

	return ""
}

// Heartbeat checks if the provider is available.
func (p *Provider) Heartbeat(ctx context.Context) error {
	if !p.config.Enabled {
		return ErrProviderDisabled
	}

	if p.metadataPath == "" {
		return fmt.Errorf("no metadata path configured")
	}

	if _, err := os.Stat(p.metadataPath); os.IsNotExist(err) {
		return fmt.Errorf("metadata file not found: %s", p.metadataPath)
	}

	return nil
}

// Close clears loaded data.
func (p *Provider) Close() error {
	p.gamesByID = make(map[int]map[string]string)
	p.gamesByName = make(map[string]map[int]map[string]string)
	p.imagesByID = make(map[int][]map[string]string)
	p.loaded = false
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
