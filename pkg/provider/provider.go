// Package provider defines the interface for metadata providers.
package provider

import (
	"context"
	"fmt"
	"regexp"

	"github.com/josegonzalez/retro-metadata/pkg/cache"
	"github.com/josegonzalez/retro-metadata/pkg/internal/matching"
	"github.com/josegonzalez/retro-metadata/pkg/internal/normalization"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// Provider is the interface that all metadata providers must implement.
type Provider interface {
	// Name returns the provider name (e.g., "igdb", "mobygames").
	Name() string

	// Search searches for games by name.
	Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error)

	// GetByID gets game details by provider-specific ID.
	GetByID(ctx context.Context, gameID int) (*retrometadata.GameResult, error)

	// Identify identifies a game from a ROM filename.
	Identify(ctx context.Context, filename string, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error)

	// Heartbeat checks if the provider API is accessible.
	Heartbeat(ctx context.Context) error

	// Close cleans up provider resources.
	Close() error
}

// HashProvider is an optional interface for providers that support hash-based identification.
type HashProvider interface {
	Provider

	// IdentifyByHash identifies a game using file hashes.
	IdentifyByHash(ctx context.Context, hashes retrometadata.FileHashes, opts retrometadata.IdentifyOptions) (*retrometadata.GameResult, error)
}

// BaseProvider provides common functionality for providers.
type BaseProvider struct {
	name              string
	config            retrometadata.ProviderConfig
	cache             cache.Cache
	minSimilarityScore float64
}

// NewBaseProvider creates a new BaseProvider.
func NewBaseProvider(name string, config retrometadata.ProviderConfig, c cache.Cache) *BaseProvider {
	return &BaseProvider{
		name:              name,
		config:            config,
		cache:             c,
		minSimilarityScore: matching.DefaultMinSimilarity,
	}
}

// Name returns the provider name.
func (p *BaseProvider) Name() string {
	return p.name
}

// Config returns the provider configuration.
func (p *BaseProvider) Config() retrometadata.ProviderConfig {
	return p.config
}

// Cache returns the cache backend.
func (p *BaseProvider) Cache() cache.Cache {
	return p.cache
}

// IsEnabled returns true if the provider is enabled and configured.
func (p *BaseProvider) IsEnabled() bool {
	return p.config.Enabled && p.config.IsConfigured()
}

// GetCredential returns a credential value by key.
func (p *BaseProvider) GetCredential(key string) string {
	return p.config.GetCredential(key)
}

// NormalizeSearchTerm normalizes a search term for comparison.
func (p *BaseProvider) NormalizeSearchTerm(name string) string {
	return normalization.NormalizeSearchTermDefault(name)
}

// NormalizeCoverURL normalizes a cover image URL.
func (p *BaseProvider) NormalizeCoverURL(url string) string {
	return normalization.NormalizeCoverURL(url)
}

// FindBestMatch finds the best matching name from candidates.
func (p *BaseProvider) FindBestMatch(searchTerm string, candidates []string) (string, float64) {
	return matching.FindBestMatch(searchTerm, candidates, matching.FindBestMatchOptions{
		MinSimilarityScore: p.minSimilarityScore,
		Normalize:          true,
	})
}

// FindBestMatchWithOptions finds the best match with custom options.
func (p *BaseProvider) FindBestMatchWithOptions(searchTerm string, candidates []string, opts matching.FindBestMatchOptions) (string, float64) {
	return matching.FindBestMatch(searchTerm, candidates, opts)
}

// SetMinSimilarityScore sets the minimum similarity score for matching.
func (p *BaseProvider) SetMinSimilarityScore(score float64) {
	p.minSimilarityScore = score
}

// ExtractIDFromFilename extracts a provider ID from a filename using a regex pattern.
func (p *BaseProvider) ExtractIDFromFilename(filename string, pattern *regexp.Regexp) *int {
	match := pattern.FindStringSubmatch(filename)
	if len(match) > 1 {
		var id int
		if n, err := fmt.Sscanf(match[1], "%d", &id); err == nil && n == 1 {
			return &id
		}
	}
	return nil
}

// SplitSearchTerm splits a search term by common delimiters.
func (p *BaseProvider) SplitSearchTerm(name string) []string {
	return normalization.SplitSearchTerm(name)
}

// GetCached retrieves a value from cache if available.
func (p *BaseProvider) GetCached(ctx context.Context, key string) (any, error) {
	if p.cache == nil {
		return nil, nil
	}
	return p.cache.Get(ctx, p.name+":"+key)
}

// SetCached stores a value in cache if available.
func (p *BaseProvider) SetCached(ctx context.Context, key string, value any) error {
	if p.cache == nil {
		return nil
	}
	return p.cache.Set(ctx, p.name+":"+key, value, 0)
}

// Close is a no-op by default. Providers should override if cleanup is needed.
func (p *BaseProvider) Close() error {
	return nil
}
