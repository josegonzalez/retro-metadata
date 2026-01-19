// Package playmatch provides hash-matching to external metadata providers.
package playmatch

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"

	retrometadata "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// GameMatchType represents the type of match returned by Playmatch.
type GameMatchType string

const (
	MatchSHA256          GameMatchType = "SHA256"
	MatchSHA1            GameMatchType = "SHA1"
	MatchMD5             GameMatchType = "MD5"
	MatchFileNameAndSize GameMatchType = "FileNameAndSize"
	MatchNoMatch         GameMatchType = "NoMatch"
)

var (
	// ErrProviderDisabled is returned when the provider is disabled.
	ErrProviderDisabled = fmt.Errorf("provider is disabled")
)

// Provider implements the Playmatch hash-matching provider.
type Provider struct {
	config    *retrometadata.ProviderConfig
	client    *http.Client
	baseURL   string
	userAgent string
}

// New creates a new Playmatch provider.
func New(config *retrometadata.ProviderConfig) *Provider {
	timeout := time.Duration(config.Timeout) * time.Second
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &Provider{
		config:    config,
		client:    &http.Client{Timeout: timeout},
		baseURL:   "https://playmatch.retrorealm.dev/api",
		userAgent: "retro-metadata/1.0",
	}
}

// Name returns the provider name.
func (p *Provider) Name() string {
	return "playmatch"
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

	resp, err := p.client.Do(req)
	if err != nil {
		return nil, &retrometadata.ConnectionError{Provider: p.Name(), Details: err.Error()}
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, nil
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

// Search is not supported by Playmatch (hash-based only).
func (p *Provider) Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error) {
	return nil, nil
}

// GetByID is not supported by Playmatch.
func (p *Provider) GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error) {
	return nil, nil
}

// Identify is not the primary method for Playmatch. Use LookupByHash instead.
func (p *Provider) Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error) {
	return nil, nil
}

// LookupResult contains the result of a hash lookup.
type LookupResult struct {
	IGDBID           *int
	MatchType        GameMatchType
	ExternalMetadata []map[string]interface{}
}

// LookupByHash looks up a ROM by hash to get external provider IDs.
func (p *Provider) LookupByHash(ctx context.Context, filename string, fileSize int64, md5, sha1 string) (*LookupResult, error) {
	if !p.config.Enabled {
		return nil, nil
	}

	params := url.Values{}
	params.Set("fileName", filename)
	params.Set("fileSize", strconv.FormatInt(fileSize, 10))

	if md5 != "" {
		params.Set("md5", md5)
	}
	if sha1 != "" {
		params.Set("sha1", sha1)
	}

	result, err := p.request(ctx, "/identify/ids", params)
	if err != nil {
		return nil, err
	}

	if result == nil {
		return nil, nil
	}

	matchType := GameMatchType(getString(result, "gameMatchType"))
	if matchType == MatchNoMatch || matchType == "" {
		return nil, nil
	}

	externalMetadata, ok := result["externalMetadata"].([]interface{})
	if !ok || len(externalMetadata) == 0 {
		return nil, nil
	}

	// Extract IGDB ID if available
	var igdbID *int
	for _, meta := range externalMetadata {
		metaMap, ok := meta.(map[string]interface{})
		if !ok {
			continue
		}
		if getString(metaMap, "providerName") == "IGDB" {
			if providerID := getString(metaMap, "providerId"); providerID != "" {
				if id, err := strconv.Atoi(providerID); err == nil {
					igdbID = &id
				}
			}
			break
		}
	}

	// Convert external metadata
	var metadataList []map[string]interface{}
	for _, meta := range externalMetadata {
		if metaMap, ok := meta.(map[string]interface{}); ok {
			metadataList = append(metadataList, metaMap)
		}
	}

	return &LookupResult{
		IGDBID:           igdbID,
		MatchType:        matchType,
		ExternalMetadata: metadataList,
	}, nil
}

// GetIGDBID is a convenience method to get just the IGDB ID for a ROM.
func (p *Provider) GetIGDBID(ctx context.Context, filename string, fileSize int64, md5, sha1 string) (*int, error) {
	result, err := p.LookupByHash(ctx, filename, fileSize, md5, sha1)
	if err != nil || result == nil {
		return nil, err
	}
	return result.IGDBID, nil
}

// Heartbeat checks if the provider is available.
func (p *Provider) Heartbeat(ctx context.Context) error {
	if !p.config.Enabled {
		return ErrProviderDisabled
	}

	_, err := p.request(ctx, "/health", nil)
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
