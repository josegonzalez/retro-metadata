// Package screenscraper provides the ScreenScraper metadata provider implementation.
package screenscraper

import (
	"context"
	"encoding/base64"
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

// SSTagRegex matches ScreenScraper ID tags in filenames like (ssfr-12345)
var SSTagRegex = regexp.MustCompile(`(?i)\(ssfr-(\d+)\)`)

// Default developer credentials (from romm project)
var (
	ssDevID       = decodeB64("enVyZGkxNQ==")
	ssDevPassword = decodeB64("eFRKd29PRmpPUUc=")
)

func decodeB64(s string) string {
	b, _ := base64.StdEncoding.DecodeString(s)
	return string(b)
}

// Sensitive keys to strip from URLs
var sensitiveKeys = map[string]bool{
	"ssid": true, "sspassword": true, "devid": true, "devpassword": true,
}

// Default region and language priorities
var (
	defaultRegions   = []string{"us", "wor", "ss", "eu", "jp", "unk"}
	defaultLanguages = []string{"en", "fr"}
)

// Provider implements the ScreenScraper metadata provider.
type Provider struct {
	*provider.BaseProvider
	baseURL          string
	userAgent        string
	devID            string
	devPassword      string
	httpClient       *http.Client
	regionPriority   []string
	languagePriority []string
}

// NewProvider creates a new ScreenScraper provider instance.
func NewProvider(config retrometadata.ProviderConfig, c cache.Cache) (*Provider, error) {
	p := &Provider{
		BaseProvider:     provider.NewBaseProvider("screenscraper", config, c),
		baseURL:          "https://api.screenscraper.fr/api2",
		userAgent:        "retro-metadata/1.0",
		devID:            ssDevID,
		devPassword:      ssDevPassword,
		httpClient:       &http.Client{Timeout: 30 * time.Second},
		regionPriority:   append([]string{}, defaultRegions...),
		languagePriority: append([]string{}, defaultLanguages...),
	}
	p.SetMinSimilarityScore(0.6)
	return p, nil
}

func (p *Provider) username() string {
	return p.GetCredential("username")
}

func (p *Provider) password() string {
	return p.GetCredential("password")
}

func (p *Provider) buildAuthParams() map[string]string {
	params := map[string]string{
		"output":     "json",
		"softname":   "retro-metadata",
		"ssid":       p.username(),
		"sspassword": p.password(),
	}
	if p.devID != "" {
		params["devid"] = p.devID
	}
	if p.devPassword != "" {
		params["devpassword"] = p.devPassword
	}
	return params
}

func (p *Provider) request(ctx context.Context, endpoint string, params map[string]string) (map[string]interface{}, error) {
	u, err := url.Parse(p.baseURL + "/" + endpoint)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL: %w", err)
	}

	q := u.Query()
	for k, v := range p.buildAuthParams() {
		q.Set(k, v)
	}
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

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	// Check for login error in response text
	if strings.Contains(string(body), "Erreur de login") {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderAuth}
	}

	if resp.StatusCode == 401 {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderAuth}
	}

	if resp.StatusCode == 429 {
		return nil, &retrometadata.ProviderError{Provider: p.Name(), Err: retrometadata.ErrProviderRateLimit}
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return result, nil
}

// AddAuthToURL adds authentication parameters to a ScreenScraper media URL.
func (p *Provider) AddAuthToURL(mediaURL string) string {
	if mediaURL == "" {
		return mediaURL
	}

	params := map[string]string{
		"devid":       p.devID,
		"devpassword": p.devPassword,
		"ssid":        p.username(),
		"sspassword":  p.password(),
	}

	separator := "&"
	if !strings.Contains(mediaURL, "?") {
		separator = "?"
	}

	var parts []string
	for k, v := range params {
		if v != "" {
			parts = append(parts, fmt.Sprintf("%s=%s", k, url.QueryEscape(v)))
		}
	}

	return mediaURL + separator + strings.Join(parts, "&")
}

func (p *Provider) getPreferredName(names []interface{}) string {
	for _, region := range p.regionPriority {
		for _, n := range names {
			if nMap, ok := n.(map[string]interface{}); ok {
				if getString(nMap, "region") == region {
					return getString(nMap, "text")
				}
			}
		}
	}
	// Fallback to first name
	if len(names) > 0 {
		if nMap, ok := names[0].(map[string]interface{}); ok {
			return getString(nMap, "text")
		}
	}
	return ""
}

func (p *Provider) getPreferredText(items []interface{}, langKey string) string {
	for _, lang := range p.languagePriority {
		for _, item := range items {
			if itemMap, ok := item.(map[string]interface{}); ok {
				if getString(itemMap, langKey) == lang {
					return getString(itemMap, "text")
				}
			}
		}
	}
	if len(items) > 0 {
		if itemMap, ok := items[0].(map[string]interface{}); ok {
			return getString(itemMap, "text")
		}
	}
	return ""
}

func (p *Provider) getMediaURL(medias []interface{}, mediaType string) string {
	for _, region := range p.regionPriority {
		for _, m := range medias {
			if mMap, ok := m.(map[string]interface{}); ok {
				if getString(mMap, "type") == mediaType &&
					getString(mMap, "region") == region &&
					getString(mMap, "parent") == "jeu" {
					return stripSensitiveParams(getString(mMap, "url"))
				}
			}
		}
	}
	// Fallback without region
	for _, m := range medias {
		if mMap, ok := m.(map[string]interface{}); ok {
			if getString(mMap, "type") == mediaType && getString(mMap, "parent") == "jeu" {
				return stripSensitiveParams(getString(mMap, "url"))
			}
		}
	}
	return ""
}

func stripSensitiveParams(u string) string {
	if !strings.Contains(u, "?") {
		return u
	}

	parts := strings.SplitN(u, "?", 2)
	base := parts[0]
	queryStr := parts[1]

	var newParams []string
	for _, param := range strings.Split(queryStr, "&") {
		if strings.Contains(param, "=") {
			key := strings.SplitN(param, "=", 2)[0]
			if !sensitiveKeys[strings.ToLower(key)] {
				newParams = append(newParams, param)
			}
		} else {
			newParams = append(newParams, param)
		}
	}

	if len(newParams) == 0 {
		return base
	}
	return base + "?" + strings.Join(newParams, "&")
}

// Search searches for games by name.
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	params := map[string]string{"recherche": query}

	if opts.PlatformID != nil {
		params["systemeid"] = strconv.Itoa(*opts.PlatformID)
	}

	result, err := p.request(ctx, "jeuRecherche.php", params)
	if err != nil {
		return nil, err
	}

	response, _ := result["response"].(map[string]interface{})
	games, ok := response["jeux"].([]interface{})
	if !ok {
		return nil, nil
	}

	// SS returns [{}] when no results
	if len(games) == 1 {
		if g, ok := games[0].(map[string]interface{}); ok && len(g) == 0 {
			return nil, nil
		}
	}

	limit := opts.Limit
	if limit == 0 {
		limit = 30
	}

	var searchResults []retrometadata.SearchResult
	for i, g := range games {
		if i >= limit {
			break
		}
		game, ok := g.(map[string]interface{})
		if !ok || getString(game, "id") == "" {
			continue
		}

		names, _ := game["noms"].([]interface{})
		medias, _ := game["medias"].([]interface{})

		name := p.getPreferredName(names)
		coverURL := p.getMediaURL(medias, "box-2D")

		sr := retrometadata.SearchResult{
			Provider:   p.Name(),
			ProviderID: getInt(game, "id"),
			Name:       strings.ReplaceAll(name, " : ", ": "),
			CoverURL:   coverURL,
		}

		// Extract platform
		if systeme, ok := game["systeme"].(map[string]interface{}); ok {
			sr.Platforms = []string{getString(systeme, "text")}
		}

		// Extract release year
		if dates, ok := game["dates"].([]interface{}); ok && len(dates) > 0 {
			if dateMap, ok := dates[0].(map[string]interface{}); ok {
				dateText := getString(dateMap, "text")
				if len(dateText) >= 4 {
					if year, err := strconv.Atoi(dateText[:4]); err == nil {
						sr.ReleaseYear = &year
					}
				}
			}
		}

		searchResults = append(searchResults, sr)
	}

	return searchResults, nil
}

// GetByID gets game details by ScreenScraper ID.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	result, err := p.request(ctx, "jeuInfos.php", map[string]string{"gameid": strconv.Itoa(gameID)})
	if err != nil {
		return nil, err
	}

	response, _ := result["response"].(map[string]interface{})
	game, ok := response["jeu"].(map[string]interface{})
	if !ok || getString(game, "id") == "" {
		return nil, nil
	}

	return p.buildGameResult(game), nil
}

// LookupByHash looks up a game by ROM hash.
func (p *Provider) LookupByHash(ctx context.Context, platformID int, md5, sha1, crc string, romSize int64) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	if md5 == "" && sha1 == "" && crc == "" {
		return nil, nil
	}

	params := map[string]string{"systemeid": strconv.Itoa(platformID)}
	if md5 != "" {
		params["md5"] = md5
	}
	if sha1 != "" {
		params["sha1"] = sha1
	}
	if crc != "" {
		params["crc"] = crc
	}
	if romSize > 0 {
		params["romtaille"] = strconv.FormatInt(romSize, 10)
	}

	result, err := p.request(ctx, "jeuInfos.php", params)
	if err != nil {
		return nil, err
	}

	response, _ := result["response"].(map[string]interface{})
	game, ok := response["jeu"].(map[string]interface{})
	if !ok || getString(game, "id") == "" {
		return nil, nil
	}

	return p.buildGameResult(game), nil
}

// IdentifyByHash implements the HashProvider interface for hash-based identification.
func (p *Provider) IdentifyByHash(ctx context.Context, hashes retrometadata.FileHashes, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if opts.PlatformID == nil {
		return nil, nil
	}
	return p.LookupByHash(ctx, *opts.PlatformID, hashes.MD5, hashes.SHA1, hashes.CRC32, 0)
}

// Identify identifies a game from a ROM filename.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	if !p.IsEnabled() {
		return nil, nil
	}

	// Check for ScreenScraper ID tag in filename
	if match := SSTagRegex.FindStringSubmatch(filename); len(match) > 1 {
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

	// Clean the filename
	searchTerm := cleanFilename(filename)

	// Search for the game
	params := map[string]string{
		"recherche": url.QueryEscape(searchTerm),
		"systemeid": strconv.Itoa(*opts.PlatformID),
	}

	result, err := p.request(ctx, "jeuRecherche.php", params)
	if err != nil {
		return nil, err
	}

	response, _ := result["response"].(map[string]interface{})
	games, _ := response["jeux"].([]interface{})

	// SS returns [{}] when no results
	if len(games) == 1 {
		if g, ok := games[0].(map[string]interface{}); ok && len(g) == 0 {
			games = nil
		}
	}

	if len(games) == 0 {
		// Try splitting by special characters
		terms := normalization.SplitSearchTerm(searchTerm)
		if len(terms) > 1 {
			params["recherche"] = url.QueryEscape(terms[len(terms)-1])
			result, err = p.request(ctx, "jeuRecherche.php", params)
			if err != nil {
				return nil, err
			}
			response, _ = result["response"].(map[string]interface{})
			games, _ = response["jeux"].([]interface{})
			if len(games) == 1 {
				if g, ok := games[0].(map[string]interface{}); ok && len(g) == 0 {
					games = nil
				}
			}
		}
	}

	if len(games) == 0 {
		return nil, nil
	}

	// Build name mapping
	gamesByName := make(map[string]map[string]interface{})
	var names []string
	for _, g := range games {
		if game, ok := g.(map[string]interface{}); ok {
			gameID := getString(game, "id")
			if gameID == "" {
				continue
			}
			if gameNoms, ok := game["noms"].([]interface{}); ok {
				for _, n := range gameNoms {
					if nMap, ok := n.(map[string]interface{}); ok {
						nameText := getString(nMap, "text")
						if nameText != "" {
							// Keep the game with lowest ID if duplicate names
							if existing, exists := gamesByName[nameText]; exists {
								existingID := getInt(existing, "id")
								newID := getInt(game, "id")
								if newID < existingID {
									gamesByName[nameText] = game
								}
							} else {
								gamesByName[nameText] = game
								names = append(names, nameText)
							}
						}
					}
				}
			}
		}
	}

	// Find best match
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
	_, err := p.request(ctx, "jeuRecherche.php", map[string]string{"recherche": "test"})
	return err
}

func (p *Provider) buildGameResult(game map[string]interface{}) *retrometadata.GameResult {
	names, _ := game["noms"].([]interface{})
	synopsis, _ := game["synopsis"].([]interface{})
	medias, _ := game["medias"].([]interface{})

	name := p.getPreferredName(names)
	summary := p.getPreferredText(synopsis, "langue")

	providerID := getInt(game, "id")
	result := &retrometadata.GameResult{
		Provider:    p.Name(),
		ProviderID:  &providerID,
		ProviderIDs: map[string]int{"screenscraper": providerID},
		Name:        strings.ReplaceAll(name, " : ", ": "),
		Summary:     summary,
		RawResponse: game,
	}

	// Extract artwork
	result.Artwork.CoverURL = p.getMediaURL(medias, "box-2D")

	if ssURL := p.getMediaURL(medias, "ss"); ssURL != "" {
		result.Artwork.ScreenshotURLs = append(result.Artwork.ScreenshotURLs, ssURL)
	}
	if titleScreen := p.getMediaURL(medias, "sstitle"); titleScreen != "" {
		result.Artwork.ScreenshotURLs = append(result.Artwork.ScreenshotURLs, titleScreen)
	}
	if fanart := p.getMediaURL(medias, "fanart"); fanart != "" {
		result.Artwork.ScreenshotURLs = append(result.Artwork.ScreenshotURLs, fanart)
	}

	result.Artwork.LogoURL = p.getMediaURL(medias, "wheel-hd")
	if result.Artwork.LogoURL == "" {
		result.Artwork.LogoURL = p.getMediaURL(medias, "wheel")
	}
	result.Artwork.BannerURL = p.getMediaURL(medias, "screenmarquee")

	// Extract metadata
	result.Metadata = p.extractMetadata(game)

	return result
}

func (p *Provider) extractMetadata(game map[string]interface{}) retrometadata.GameMetadata {
	metadata := retrometadata.GameMetadata{
		RawData: game,
	}

	// Genres (English names)
	if genres, ok := game["genres"].([]interface{}); ok {
		for _, g := range genres {
			if gMap, ok := g.(map[string]interface{}); ok {
				if gNoms, ok := gMap["noms"].([]interface{}); ok {
					for _, n := range gNoms {
						if nMap, ok := n.(map[string]interface{}); ok {
							if getString(nMap, "langue") == "en" {
								if name := getString(nMap, "text"); name != "" {
									metadata.Genres = append(metadata.Genres, name)
								}
								break
							}
						}
					}
				}
			}
		}
	}

	// Franchises
	if families, ok := game["familles"].([]interface{}); ok {
		for _, f := range families {
			if fMap, ok := f.(map[string]interface{}); ok {
				if fNoms, ok := fMap["noms"].([]interface{}); ok {
					text := p.getPreferredText(fNoms, "langue")
					if text != "" {
						metadata.Franchises = append(metadata.Franchises, text)
					}
				}
			}
		}
	}

	// Game modes
	if modes, ok := game["modes"].([]interface{}); ok {
		for _, m := range modes {
			if mMap, ok := m.(map[string]interface{}); ok {
				if mNoms, ok := mMap["noms"].([]interface{}); ok {
					text := p.getPreferredText(mNoms, "langue")
					if text != "" {
						metadata.GameModes = append(metadata.GameModes, text)
					}
				}
			}
		}
	}

	// Alternative names
	if noms, ok := game["noms"].([]interface{}); ok {
		for _, n := range noms {
			if nMap, ok := n.(map[string]interface{}); ok {
				if text := getString(nMap, "text"); text != "" {
					metadata.AlternativeNames = append(metadata.AlternativeNames, text)
				}
			}
		}
	}

	// Companies
	if editeur, ok := game["editeur"].(map[string]interface{}); ok {
		if text := getString(editeur, "text"); text != "" {
			metadata.Companies = append(metadata.Companies, text)
			metadata.Publisher = text
		}
	}
	if dev, ok := game["developpeur"].(map[string]interface{}); ok {
		if text := getString(dev, "text"); text != "" {
			// Avoid duplicates
			found := false
			for _, c := range metadata.Companies {
				if c == text {
					found = true
					break
				}
			}
			if !found {
				metadata.Companies = append(metadata.Companies, text)
			}
			metadata.Developer = text
		}
	}

	// Rating (SS scores are out of 20, normalize to 100)
	if note, ok := game["note"].(map[string]interface{}); ok {
		if noteStr := getString(note, "text"); noteStr != "" {
			if noteVal, err := strconv.ParseFloat(noteStr, 64); err == nil {
				rating := noteVal * 5
				metadata.TotalRating = &rating
			}
		}
	}

	// Player count
	if joueurs, ok := game["joueurs"].(map[string]interface{}); ok {
		if text := getString(joueurs, "text"); text != "" && text != "null" && text != "none" {
			metadata.PlayerCount = text
		} else {
			metadata.PlayerCount = "1"
		}
	} else {
		metadata.PlayerCount = "1"
	}

	// Release date
	if dates, ok := game["dates"].([]interface{}); ok && len(dates) > 0 {
		// Find earliest date
		var earliest string
		for _, d := range dates {
			if dMap, ok := d.(map[string]interface{}); ok {
				dateText := getString(dMap, "text")
				if earliest == "" || dateText < earliest {
					earliest = dateText
				}
			}
		}
		if earliest != "" {
			if t, err := time.Parse("2006-01-02", earliest); err == nil {
				ts := t.Unix()
				metadata.FirstReleaseDate = &ts
			} else if len(earliest) >= 4 {
				// Try just year
				if year, err := strconv.Atoi(earliest[:4]); err == nil {
					t := time.Date(year, 1, 1, 0, 0, 0, 0, time.UTC)
					ts := t.Unix()
					metadata.FirstReleaseDate = &ts
					metadata.ReleaseYear = &year
				}
			}
		}
	}

	return metadata
}

// GetPlatform returns platform information for a slug.
func (p *Provider) GetPlatform(slug string) *retrometadata.Platform {
	platformSlug := platform.Slug(slug)
	platformID := platform.GetScreenScraperPlatformID(platformSlug)
	if platformID == nil {
		return nil
	}

	name := ScreenScraperPlatformNames[*platformID]
	if name == "" {
		name = strings.ReplaceAll(slug, "-", " ")
	}

	return &retrometadata.Platform{
		Slug:        slug,
		Name:        name,
		ProviderIDs: map[string]int{"screenscraper": *platformID},
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

// ScreenScraperPlatformNames maps ScreenScraper platform IDs to names
var ScreenScraperPlatformNames = map[int]string{
	1:   "Mega Drive",
	2:   "Master System",
	3:   "NES",
	4:   "Super Nintendo",
	9:   "Game Boy",
	10:  "Game Boy Color",
	12:  "Game Boy Advance",
	13:  "GameCube",
	14:  "Nintendo 64",
	15:  "Nintendo DS",
	16:  "Wii",
	17:  "Nintendo 3DS",
	18:  "Wii U",
	19:  "32X",
	20:  "Mega CD",
	21:  "Game Gear",
	22:  "Saturn",
	23:  "Dreamcast",
	25:  "Neo Geo Pocket",
	26:  "Atari 2600",
	27:  "Jaguar",
	28:  "Lynx",
	29:  "3DO",
	31:  "TurboGrafx-16",
	40:  "Atari 5200",
	41:  "Atari 7800",
	42:  "Atari ST",
	43:  "Atari 8-bit",
	45:  "WonderSwan",
	46:  "WonderSwan Color",
	48:  "ColecoVision",
	57:  "PlayStation",
	58:  "PlayStation 2",
	59:  "PlayStation 3",
	61:  "PSP",
	62:  "PS Vita",
	63:  "Android",
	64:  "Amiga",
	65:  "Amstrad CPC",
	66:  "Commodore 64",
	68:  "Neo Geo MVS",
	70:  "Neo Geo CD",
	72:  "PC-FX",
	75:  "Arcade",
	76:  "ZX Spectrum",
	82:  "Neo Geo Pocket Color",
	105: "SuperGrafx",
	106: "Famicom Disk System",
	109: "SG-1000",
	114: "TurboGrafx-CD",
	122: "64DD",
	142: "Neo Geo AES",
	225: "Nintendo Switch",
	234: "Sega Pico",
	243: "PlayStation 4",
	244: "PlayStation 5",
}

func init() {
	// Register the provider factory
	retrometadata.RegisterProvider("screenscraper", func(config retrometadata.ProviderConfig, c cache.Cache) (retrometadata.Provider, error) {
		return NewProvider(config, c)
	})
}
