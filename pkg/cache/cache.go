// Package cache provides cache backends for storing metadata lookup results.
package cache

import (
	"context"
	"time"
)

// Cache is the interface for cache backends.
type Cache interface {
	// Get retrieves a value from the cache.
	// Returns nil if the key is not found or expired.
	Get(ctx context.Context, key string) (any, error)

	// Set stores a value in the cache.
	// If ttl is 0, the default TTL is used.
	Set(ctx context.Context, key string, value any, ttl time.Duration) error

	// Delete removes a value from the cache.
	// Returns true if the key was deleted, false if it didn't exist.
	Delete(ctx context.Context, key string) (bool, error)

	// Exists checks if a key exists in the cache.
	Exists(ctx context.Context, key string) (bool, error)

	// Clear removes all entries from the cache.
	Clear(ctx context.Context) error

	// Close closes any connections and cleans up resources.
	Close() error
}

// BulkCache extends Cache with bulk operations for better performance.
type BulkCache interface {
	Cache

	// GetMany retrieves multiple values from the cache.
	// Returns a map of key to value for found keys.
	GetMany(ctx context.Context, keys []string) (map[string]any, error)

	// SetMany stores multiple values in the cache.
	SetMany(ctx context.Context, items map[string]any, ttl time.Duration) error

	// DeleteMany removes multiple values from the cache.
	// Returns the number of keys that were deleted.
	DeleteMany(ctx context.Context, keys []string) (int, error)
}

// StatsProvider provides cache statistics.
type StatsProvider interface {
	// Stats returns cache statistics.
	Stats(ctx context.Context) (Stats, error)
}

// Stats contains cache statistics.
type Stats struct {
	// Size is the current number of entries
	Size int `json:"size"`
	// MaxSize is the maximum number of entries (for memory cache)
	MaxSize int `json:"max_size,omitempty"`
	// ExpiredCount is the number of expired entries
	ExpiredCount int `json:"expired_count,omitempty"`
	// Hits is the number of cache hits
	Hits int64 `json:"hits,omitempty"`
	// Misses is the number of cache misses
	Misses int64 `json:"misses,omitempty"`
}

// NullCache is a cache that doesn't cache anything.
// Useful for testing or disabling caching.
type NullCache struct{}

// NewNullCache creates a new NullCache.
func NewNullCache() *NullCache {
	return &NullCache{}
}

// Get always returns nil.
func (c *NullCache) Get(_ context.Context, _ string) (any, error) {
	return nil, nil
}

// Set does nothing.
func (c *NullCache) Set(_ context.Context, _ string, _ any, _ time.Duration) error {
	return nil
}

// Delete always returns false.
func (c *NullCache) Delete(_ context.Context, _ string) (bool, error) {
	return false, nil
}

// Exists always returns false.
func (c *NullCache) Exists(_ context.Context, _ string) (bool, error) {
	return false, nil
}

// Clear does nothing.
func (c *NullCache) Clear(_ context.Context) error {
	return nil
}

// Close does nothing.
func (c *NullCache) Close() error {
	return nil
}

// PrefixedCache wraps a cache with a key prefix.
type PrefixedCache struct {
	cache  Cache
	prefix string
}

// NewPrefixedCache creates a new cache that prefixes all keys.
func NewPrefixedCache(cache Cache, prefix string) *PrefixedCache {
	return &PrefixedCache{
		cache:  cache,
		prefix: prefix,
	}
}

func (c *PrefixedCache) prefixKey(key string) string {
	return c.prefix + ":" + key
}

// Get retrieves a value with the prefixed key.
func (c *PrefixedCache) Get(ctx context.Context, key string) (any, error) {
	return c.cache.Get(ctx, c.prefixKey(key))
}

// Set stores a value with the prefixed key.
func (c *PrefixedCache) Set(ctx context.Context, key string, value any, ttl time.Duration) error {
	return c.cache.Set(ctx, c.prefixKey(key), value, ttl)
}

// Delete removes a value with the prefixed key.
func (c *PrefixedCache) Delete(ctx context.Context, key string) (bool, error) {
	return c.cache.Delete(ctx, c.prefixKey(key))
}

// Exists checks if a prefixed key exists.
func (c *PrefixedCache) Exists(ctx context.Context, key string) (bool, error) {
	return c.cache.Exists(ctx, c.prefixKey(key))
}

// Clear clears all entries (note: only clears prefixed keys if supported).
func (c *PrefixedCache) Clear(ctx context.Context) error {
	return c.cache.Clear(ctx)
}

// Close closes the underlying cache.
func (c *PrefixedCache) Close() error {
	return c.cache.Close()
}
