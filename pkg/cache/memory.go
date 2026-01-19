package cache

import (
	"container/list"
	"context"
	"sync"
	"sync/atomic"
	"time"
)

// entry represents a single cache entry.
type entry struct {
	key       string
	value     any
	expiresAt time.Time
}

func (e *entry) isExpired() bool {
	if e.expiresAt.IsZero() {
		return false
	}
	return time.Now().After(e.expiresAt)
}

// MemoryCache is an in-memory LRU cache with TTL support.
type MemoryCache struct {
	mu              sync.RWMutex
	cache           map[string]*list.Element
	lru             *list.List
	maxSize         int
	defaultTTL      time.Duration
	cleanupInterval time.Duration
	stopCleanup     chan struct{}
	hits            atomic.Int64
	misses          atomic.Int64
}

// MemoryCacheOption is a functional option for MemoryCache.
type MemoryCacheOption func(*MemoryCache)

// WithMaxSize sets the maximum number of entries.
func WithMaxSize(size int) MemoryCacheOption {
	return func(c *MemoryCache) {
		c.maxSize = size
	}
}

// WithDefaultTTL sets the default TTL for entries.
func WithDefaultTTL(ttl time.Duration) MemoryCacheOption {
	return func(c *MemoryCache) {
		c.defaultTTL = ttl
	}
}

// WithCleanupInterval sets the interval for expired entry cleanup.
func WithCleanupInterval(interval time.Duration) MemoryCacheOption {
	return func(c *MemoryCache) {
		c.cleanupInterval = interval
	}
}

// NewMemoryCache creates a new in-memory cache.
func NewMemoryCache(opts ...MemoryCacheOption) *MemoryCache {
	c := &MemoryCache{
		cache:           make(map[string]*list.Element),
		lru:             list.New(),
		maxSize:         10000,
		defaultTTL:      time.Hour,
		cleanupInterval: time.Minute,
		stopCleanup:     make(chan struct{}),
	}

	for _, opt := range opts {
		opt(c)
	}

	// Start background cleanup goroutine
	go c.cleanupLoop()

	return c
}

func (c *MemoryCache) cleanupLoop() {
	ticker := time.NewTicker(c.cleanupInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			c.cleanupExpired()
		case <-c.stopCleanup:
			return
		}
	}
}

func (c *MemoryCache) cleanupExpired() {
	c.mu.Lock()
	defer c.mu.Unlock()

	for elem := c.lru.Front(); elem != nil; {
		next := elem.Next()
		e := elem.Value.(*entry)
		if e.isExpired() {
			c.lru.Remove(elem)
			delete(c.cache, e.key)
		}
		elem = next
	}
}

func (c *MemoryCache) evictIfNeeded() {
	for c.lru.Len() >= c.maxSize {
		oldest := c.lru.Front()
		if oldest != nil {
			e := oldest.Value.(*entry)
			c.lru.Remove(oldest)
			delete(c.cache, e.key)
		}
	}
}

// Get retrieves a value from the cache.
func (c *MemoryCache) Get(_ context.Context, key string) (any, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	elem, ok := c.cache[key]
	if !ok {
		c.misses.Add(1)
		return nil, nil
	}

	e := elem.Value.(*entry)
	if e.isExpired() {
		c.lru.Remove(elem)
		delete(c.cache, key)
		c.misses.Add(1)
		return nil, nil
	}

	// Move to back (most recently used)
	c.lru.MoveToBack(elem)
	c.hits.Add(1)
	return e.value, nil
}

// Set stores a value in the cache.
func (c *MemoryCache) Set(_ context.Context, key string, value any, ttl time.Duration) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if ttl == 0 {
		ttl = c.defaultTTL
	}

	var expiresAt time.Time
	if ttl > 0 {
		expiresAt = time.Now().Add(ttl)
	}

	// Check if key already exists
	if elem, ok := c.cache[key]; ok {
		c.lru.MoveToBack(elem)
		e := elem.Value.(*entry)
		e.value = value
		e.expiresAt = expiresAt
		return nil
	}

	// Evict if at capacity
	c.evictIfNeeded()

	// Add new entry
	e := &entry{
		key:       key,
		value:     value,
		expiresAt: expiresAt,
	}
	elem := c.lru.PushBack(e)
	c.cache[key] = elem

	return nil
}

// Delete removes a value from the cache.
func (c *MemoryCache) Delete(_ context.Context, key string) (bool, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	elem, ok := c.cache[key]
	if !ok {
		return false, nil
	}

	c.lru.Remove(elem)
	delete(c.cache, key)
	return true, nil
}

// Exists checks if a key exists in the cache.
func (c *MemoryCache) Exists(_ context.Context, key string) (bool, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	elem, ok := c.cache[key]
	if !ok {
		return false, nil
	}

	e := elem.Value.(*entry)
	if e.isExpired() {
		return false, nil
	}

	return true, nil
}

// Clear removes all entries from the cache.
func (c *MemoryCache) Clear(_ context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.cache = make(map[string]*list.Element)
	c.lru.Init()
	return nil
}

// Close stops the cleanup goroutine and clears the cache.
func (c *MemoryCache) Close() error {
	close(c.stopCleanup)
	return c.Clear(context.Background())
}

// Size returns the current number of entries in the cache.
func (c *MemoryCache) Size() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.lru.Len()
}

// Stats returns cache statistics.
func (c *MemoryCache) Stats(_ context.Context) (Stats, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	expiredCount := 0
	for elem := c.lru.Front(); elem != nil; elem = elem.Next() {
		e := elem.Value.(*entry)
		if e.isExpired() {
			expiredCount++
		}
	}

	return Stats{
		Size:         c.lru.Len(),
		MaxSize:      c.maxSize,
		ExpiredCount: expiredCount,
		Hits:         c.hits.Load(),
		Misses:       c.misses.Load(),
	}, nil
}

// GetMany retrieves multiple values from the cache.
func (c *MemoryCache) GetMany(ctx context.Context, keys []string) (map[string]any, error) {
	result := make(map[string]any, len(keys))
	for _, key := range keys {
		value, err := c.Get(ctx, key)
		if err != nil {
			return nil, err
		}
		if value != nil {
			result[key] = value
		}
	}
	return result, nil
}

// SetMany stores multiple values in the cache.
func (c *MemoryCache) SetMany(ctx context.Context, items map[string]any, ttl time.Duration) error {
	for key, value := range items {
		if err := c.Set(ctx, key, value, ttl); err != nil {
			return err
		}
	}
	return nil
}

// DeleteMany removes multiple values from the cache.
func (c *MemoryCache) DeleteMany(ctx context.Context, keys []string) (int, error) {
	count := 0
	for _, key := range keys {
		deleted, err := c.Delete(ctx, key)
		if err != nil {
			return count, err
		}
		if deleted {
			count++
		}
	}
	return count, nil
}
