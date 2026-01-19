package retrometadata

import (
	"context"
	"sync"
	"time"

	"github.com/josegonzalez/retro-metadata/pkg/cache"
)

// Provider is the interface that all metadata providers must implement.
// This is defined here to avoid import cycles between retrometadata and provider packages.
type Provider interface {
	// Name returns the provider name (e.g., "igdb", "mobygames").
	Name() string

	// Search searches for games by name.
	Search(ctx context.Context, query string, opts SearchOptions) ([]SearchResult, error)

	// GetByID gets game details by provider-specific ID.
	GetByID(ctx context.Context, gameID int) (*GameResult, error)

	// Identify identifies a game from a ROM filename.
	Identify(ctx context.Context, filename string, opts IdentifyOptions) (*GameResult, error)

	// Heartbeat checks if the provider API is accessible.
	Heartbeat(ctx context.Context) error

	// Close cleans up provider resources.
	Close() error
}

// HashProvider is an optional interface for providers that support hash-based identification.
type HashProvider interface {
	Provider

	// IdentifyByHash identifies a game using file hashes.
	IdentifyByHash(ctx context.Context, hashes FileHashes, opts IdentifyOptions) (*GameResult, error)
}

// ProviderFactory is a function that creates a provider instance.
type ProviderFactory func(config ProviderConfig, cache cache.Cache) (Provider, error)

// providerRegistry holds registered provider factories.
var providerRegistry = struct {
	mu        sync.RWMutex
	factories map[string]ProviderFactory
}{
	factories: make(map[string]ProviderFactory),
}

// RegisterProvider registers a provider factory.
func RegisterProvider(name string, factory ProviderFactory) {
	providerRegistry.mu.Lock()
	defer providerRegistry.mu.Unlock()
	providerRegistry.factories[name] = factory
}

// Client is the main client for fetching game metadata from various providers.
type Client struct {
	config    Config
	cache     cache.Cache
	providers map[string]Provider
	mu        sync.RWMutex
}

// NewClient creates a new metadata client with the given options.
func NewClient(opts ...Option) (*Client, error) {
	config := DefaultConfig()
	for _, opt := range opts {
		opt(&config)
	}

	c := &Client{
		config:    config,
		providers: make(map[string]Provider),
	}

	// Initialize cache
	var err error
	c.cache, err = c.initCache()
	if err != nil {
		return nil, err
	}

	// Initialize providers
	if err := c.initProviders(); err != nil {
		return nil, err
	}

	return c, nil
}

func (c *Client) initCache() (cache.Cache, error) {
	switch c.config.Cache.Backend {
	case "memory":
		return cache.NewMemoryCache(
			cache.WithMaxSize(c.config.Cache.MaxSize),
			cache.WithDefaultTTL(time.Duration(c.config.Cache.TTL)*time.Second),
		), nil
	case "null", "none", "":
		return cache.NewNullCache(), nil
	default:
		return cache.NewNullCache(), nil
	}
}

func (c *Client) initProviders() error {
	providerRegistry.mu.RLock()
	defer providerRegistry.mu.RUnlock()

	enabledProviders := c.config.GetEnabledProviders()

	for _, name := range enabledProviders {
		providerConfig := c.config.GetProviderConfig(name)
		if providerConfig == nil {
			continue
		}

		factory, ok := providerRegistry.factories[name]
		if !ok {
			continue
		}

		p, err := factory(*providerConfig, c.cache)
		if err != nil {
			continue // Skip providers that fail to initialize
		}
		c.providers[name] = p
	}

	return nil
}

// Search searches for games by name across all enabled providers.
func (c *Client) Search(ctx context.Context, query string, opts SearchOptions) ([]SearchResult, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	if opts.Limit == 0 {
		opts.Limit = 10
	}

	var allResults []SearchResult

	for _, p := range c.providers {
		results, err := p.Search(ctx, query, opts)
		if err != nil {
			continue // Skip providers that fail
		}
		allResults = append(allResults, results...)
	}

	// Limit total results
	if len(allResults) > opts.Limit {
		allResults = allResults[:opts.Limit]
	}

	return allResults, nil
}

// GetByID gets game details by provider-specific ID.
func (c *Client) GetByID(ctx context.Context, providerName string, gameID int) (*GameResult, error) {
	c.mu.RLock()
	p, ok := c.providers[providerName]
	c.mu.RUnlock()

	if !ok {
		return nil, &ProviderError{
			Provider: providerName,
			Err:      ErrProviderNotFound,
		}
	}

	return p.GetByID(ctx, gameID)
}

// Identify identifies a game from a ROM filename.
func (c *Client) Identify(ctx context.Context, filename string, opts IdentifyOptions) (*GameResult, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	// Try each provider in priority order
	for _, name := range c.config.GetEnabledProviders() {
		p, ok := c.providers[name]
		if !ok {
			continue
		}

		result, err := p.Identify(ctx, filename, opts)
		if err != nil {
			continue
		}
		if result != nil {
			return result, nil
		}
	}

	return nil, &GameNotFoundError{
		SearchTerm: filename,
	}
}

// IdentifyByHash identifies a game using file hashes.
func (c *Client) IdentifyByHash(ctx context.Context, hashes FileHashes, opts IdentifyOptions) (*GameResult, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	// Try hash-capable providers first
	for _, name := range c.config.GetEnabledProviders() {
		p, ok := c.providers[name]
		if !ok {
			continue
		}

		// Check if provider supports hash-based identification
		hashProvider, ok := p.(HashProvider)
		if !ok {
			continue
		}

		result, err := hashProvider.IdentifyByHash(ctx, hashes, opts)
		if err != nil {
			continue
		}
		if result != nil {
			return result, nil
		}
	}

	return nil, &GameNotFoundError{
		SearchTerm: hashes.MD5,
	}
}

// IdentifySmart uses a 3-tier strategy: hash first, then filename, then search.
func (c *Client) IdentifySmart(ctx context.Context, filename string, hashes *FileHashes, opts IdentifyOptions) (*GameResult, error) {
	// Tier 1: Try hash-based identification if hashes provided
	if hashes != nil {
		result, err := c.IdentifyByHash(ctx, *hashes, opts)
		if err == nil && result != nil {
			result.MatchType = "hash"
			return result, nil
		}
	}

	// Tier 2: Try filename-based identification
	result, err := c.Identify(ctx, filename, opts)
	if err == nil && result != nil {
		result.MatchType = "filename"
		return result, nil
	}

	return nil, &GameNotFoundError{
		SearchTerm: filename,
	}
}

// Heartbeat checks if all enabled providers are accessible.
func (c *Client) Heartbeat(ctx context.Context) []ProviderStatus {
	c.mu.RLock()
	defer c.mu.RUnlock()

	statuses := make([]ProviderStatus, 0, len(c.providers))

	for name, p := range c.providers {
		status := ProviderStatus{
			Name:      name,
			LastCheck: time.Now(),
		}

		if err := p.Heartbeat(ctx); err != nil {
			status.Available = false
			status.Error = err.Error()
		} else {
			status.Available = true
		}

		statuses = append(statuses, status)
	}

	return statuses
}

// GetProvider returns a specific provider by name.
func (c *Client) GetProvider(name string) (Provider, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	p, ok := c.providers[name]
	return p, ok
}

// EnabledProviders returns the list of enabled provider names.
func (c *Client) EnabledProviders() []string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	names := make([]string, 0, len(c.providers))
	for name := range c.providers {
		names = append(names, name)
	}
	return names
}

// Close closes all providers and the cache.
func (c *Client) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	var lastErr error

	for _, p := range c.providers {
		if err := p.Close(); err != nil {
			lastErr = err
		}
	}

	if c.cache != nil {
		if err := c.cache.Close(); err != nil {
			lastErr = err
		}
	}

	return lastErr
}
