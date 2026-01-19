package cache

import (
	"context"
	"encoding/json"
	"reflect"
	"testing"
	"time"

	"github.com/josegonzalez/retro-metadata/pkg/testutil"
)

func TestMemoryCacheFromSharedData(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to create test data loader: %v", err)
	}

	testCases, err := loader.GetTestCases("cache", "memory_cache")
	if err != nil {
		t.Fatalf("Failed to load test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			// Parse config if present
			var maxSize int
			var defaultTTL time.Duration
			if tc.Config != nil {
				if size, ok := tc.Config["max_size"].(float64); ok {
					maxSize = int(size)
				}
				if ttlMs, ok := tc.Config["default_ttl_ms"].(float64); ok {
					defaultTTL = time.Duration(ttlMs) * time.Millisecond
				}
			}

			// Create cache with config
			var opts []MemoryCacheOption
			if maxSize > 0 {
				opts = append(opts, WithMaxSize(maxSize))
			}
			if defaultTTL > 0 {
				opts = append(opts, WithDefaultTTL(defaultTTL))
			}
			opts = append(opts, WithCleanupInterval(time.Hour)) // Disable auto cleanup for tests

			cache := NewMemoryCache(opts...)
			defer cache.Close()

			ctx := context.Background()

			// Use Operations field for cache tests
			operations := tc.Operations
			if operations == nil {
				t.Fatalf("No operations defined for test case")
			}

			for i, opRaw := range operations {
				op, ok := opRaw.(map[string]interface{})
				if !ok {
					t.Fatalf("Operation %d: invalid format", i)
				}

				action, _ := op["action"].(string)
				key, _ := op["key"].(string)

				switch action {
				case "set":
					value := op["value"]
					ttl := time.Duration(0)
					if ttlMs, ok := op["ttl_ms"].(float64); ok {
						ttl = time.Duration(ttlMs) * time.Millisecond
					}
					if err := cache.Set(ctx, key, value, ttl); err != nil {
						t.Errorf("Operation %d: Set(%q) error: %v", i, key, err)
					}

				case "get":
					result, err := cache.Get(ctx, key)
					if err != nil {
						t.Errorf("Operation %d: Get(%q) error: %v", i, key, err)
						continue
					}

					// Check expected value
					if expected, hasExpected := op["expected"]; hasExpected {
						if expected == nil {
							if result != nil {
								t.Errorf("Operation %d: Get(%q) = %v, expected nil", i, key, result)
							}
						} else if !jsonEqual(result, expected) {
							t.Errorf("Operation %d: Get(%q) = %v, expected %v", i, key, result, expected)
						}
					}

					// Check expected_not value
					if expectedNot, hasExpectedNot := op["expected_not"]; hasExpectedNot {
						if expectedNot == nil && result == nil {
							t.Errorf("Operation %d: Get(%q) = nil, expected not nil", i, key)
						}
					}

				case "delete":
					if _, err := cache.Delete(ctx, key); err != nil {
						t.Errorf("Operation %d: Delete(%q) error: %v", i, key, err)
					}

				case "clear":
					if err := cache.Clear(ctx); err != nil {
						t.Errorf("Operation %d: Clear() error: %v", i, err)
					}

				case "sleep":
					if ms, ok := op["ms"].(float64); ok {
						time.Sleep(time.Duration(ms) * time.Millisecond)
					}

				default:
					t.Fatalf("Operation %d: unknown action %q", i, action)
				}
			}
		})
	}
}

// jsonEqual compares two values for JSON equivalence
func jsonEqual(a, b interface{}) bool {
	aJSON, err1 := json.Marshal(a)
	bJSON, err2 := json.Marshal(b)
	if err1 != nil || err2 != nil {
		return reflect.DeepEqual(a, b)
	}
	return string(aJSON) == string(bJSON)
}

func TestMemoryCacheBasic(t *testing.T) {
	cache := NewMemoryCache(WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	// Test Set and Get
	err := cache.Set(ctx, "key1", "value1", 0)
	if err != nil {
		t.Fatalf("Set error: %v", err)
	}

	val, err := cache.Get(ctx, "key1")
	if err != nil {
		t.Fatalf("Get error: %v", err)
	}
	if val != "value1" {
		t.Errorf("Get = %v, expected %v", val, "value1")
	}
}

func TestMemoryCacheExists(t *testing.T) {
	cache := NewMemoryCache(WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	// Key doesn't exist
	exists, err := cache.Exists(ctx, "nonexistent")
	if err != nil {
		t.Fatalf("Exists error: %v", err)
	}
	if exists {
		t.Error("Exists should return false for nonexistent key")
	}

	// Set key
	cache.Set(ctx, "key1", "value1", 0)

	// Key exists
	exists, err = cache.Exists(ctx, "key1")
	if err != nil {
		t.Fatalf("Exists error: %v", err)
	}
	if !exists {
		t.Error("Exists should return true for existing key")
	}
}

func TestMemoryCacheSize(t *testing.T) {
	cache := NewMemoryCache(WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	if cache.Size() != 0 {
		t.Errorf("Size = %d, expected 0", cache.Size())
	}

	cache.Set(ctx, "key1", "value1", 0)
	cache.Set(ctx, "key2", "value2", 0)

	if cache.Size() != 2 {
		t.Errorf("Size = %d, expected 2", cache.Size())
	}

	cache.Delete(ctx, "key1")

	if cache.Size() != 1 {
		t.Errorf("Size = %d, expected 1", cache.Size())
	}
}

func TestMemoryCacheStats(t *testing.T) {
	cache := NewMemoryCache(WithMaxSize(100), WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	cache.Set(ctx, "key1", "value1", 0)
	cache.Get(ctx, "key1") // hit
	cache.Get(ctx, "key1") // hit
	cache.Get(ctx, "key2") // miss

	stats, err := cache.Stats(ctx)
	if err != nil {
		t.Fatalf("Stats error: %v", err)
	}

	if stats.Size != 1 {
		t.Errorf("Stats.Size = %d, expected 1", stats.Size)
	}
	if stats.MaxSize != 100 {
		t.Errorf("Stats.MaxSize = %d, expected 100", stats.MaxSize)
	}
	if stats.Hits != 2 {
		t.Errorf("Stats.Hits = %d, expected 2", stats.Hits)
	}
	if stats.Misses != 1 {
		t.Errorf("Stats.Misses = %d, expected 1", stats.Misses)
	}
}

func TestMemoryCacheGetMany(t *testing.T) {
	cache := NewMemoryCache(WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	cache.Set(ctx, "key1", "value1", 0)
	cache.Set(ctx, "key2", "value2", 0)

	result, err := cache.GetMany(ctx, []string{"key1", "key2", "key3"})
	if err != nil {
		t.Fatalf("GetMany error: %v", err)
	}

	if len(result) != 2 {
		t.Errorf("GetMany returned %d results, expected 2", len(result))
	}
	if result["key1"] != "value1" {
		t.Errorf("GetMany[key1] = %v, expected value1", result["key1"])
	}
	if result["key2"] != "value2" {
		t.Errorf("GetMany[key2] = %v, expected value2", result["key2"])
	}
	if _, ok := result["key3"]; ok {
		t.Error("GetMany[key3] should not exist")
	}
}

func TestMemoryCacheSetMany(t *testing.T) {
	cache := NewMemoryCache(WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	items := map[string]any{
		"key1": "value1",
		"key2": "value2",
		"key3": "value3",
	}

	err := cache.SetMany(ctx, items, 0)
	if err != nil {
		t.Fatalf("SetMany error: %v", err)
	}

	if cache.Size() != 3 {
		t.Errorf("Size = %d, expected 3", cache.Size())
	}

	for k, v := range items {
		val, _ := cache.Get(ctx, k)
		if val != v {
			t.Errorf("Get(%q) = %v, expected %v", k, val, v)
		}
	}
}

func TestMemoryCacheDeleteMany(t *testing.T) {
	cache := NewMemoryCache(WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	cache.Set(ctx, "key1", "value1", 0)
	cache.Set(ctx, "key2", "value2", 0)
	cache.Set(ctx, "key3", "value3", 0)

	count, err := cache.DeleteMany(ctx, []string{"key1", "key2", "nonexistent"})
	if err != nil {
		t.Fatalf("DeleteMany error: %v", err)
	}

	if count != 2 {
		t.Errorf("DeleteMany returned count %d, expected 2", count)
	}

	if cache.Size() != 1 {
		t.Errorf("Size = %d, expected 1", cache.Size())
	}

	val, _ := cache.Get(ctx, "key3")
	if val != "value3" {
		t.Error("key3 should still exist")
	}
}

func TestMemoryCacheTTLExpiration(t *testing.T) {
	cache := NewMemoryCache(WithDefaultTTL(50*time.Millisecond), WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	cache.Set(ctx, "key1", "value1", 0)

	val, _ := cache.Get(ctx, "key1")
	if val != "value1" {
		t.Error("Value should exist before TTL")
	}

	time.Sleep(100 * time.Millisecond)

	val, _ = cache.Get(ctx, "key1")
	if val != nil {
		t.Error("Value should be nil after TTL")
	}
}

func TestMemoryCacheLRUEviction(t *testing.T) {
	cache := NewMemoryCache(WithMaxSize(3), WithCleanupInterval(time.Hour))
	defer cache.Close()

	ctx := context.Background()

	cache.Set(ctx, "key1", "value1", 0)
	cache.Set(ctx, "key2", "value2", 0)
	cache.Set(ctx, "key3", "value3", 0)

	// Access key1 to make it recently used
	cache.Get(ctx, "key1")

	// Add key4, should evict key2 (least recently used)
	cache.Set(ctx, "key4", "value4", 0)

	// key2 should be evicted
	val, _ := cache.Get(ctx, "key2")
	if val != nil {
		t.Error("key2 should be evicted")
	}

	// key1, key3, key4 should exist
	for _, key := range []string{"key1", "key3", "key4"} {
		val, _ := cache.Get(ctx, key)
		if val == nil {
			t.Errorf("%s should exist", key)
		}
	}
}
