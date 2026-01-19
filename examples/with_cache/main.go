// Example: Using Cache with Providers
//
// This example demonstrates how to use an in-memory cache with providers
// to reduce API calls and improve performance.
//
// To run:
//
//	export IGDB_CLIENT_ID="your_client_id"
//	export IGDB_CLIENT_SECRET="your_client_secret"
//	go run main.go
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/josegonzalez/retro-metadata/pkg/cache"
	"github.com/josegonzalez/retro-metadata/pkg/provider/igdb"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

func main() {
	// Get credentials from environment variables
	clientID := os.Getenv("IGDB_CLIENT_ID")
	clientSecret := os.Getenv("IGDB_CLIENT_SECRET")

	if clientID == "" || clientSecret == "" {
		log.Fatal("Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables")
	}

	// Create an in-memory cache
	// Options:
	// - WithMaxSize: Maximum number of cached items (default: 10000)
	// - WithDefaultTTL: How long items stay cached (default: 1 hour)
	// - WithCleanupInterval: How often to clean expired items (default: 1 minute)
	memCache := cache.NewMemoryCache(
		cache.WithMaxSize(1000),
		cache.WithDefaultTTL(30*time.Minute),
		cache.WithCleanupInterval(5*time.Minute),
	)
	defer memCache.Close()

	// Create provider configuration
	config := retrometadata.ProviderConfig{
		Enabled: true,
		Credentials: map[string]string{
			"client_id":     clientID,
			"client_secret": clientSecret,
		},
		Timeout: 30,
	}

	// Create IGDB provider with cache
	provider, err := igdb.NewProvider(config, memCache)
	if err != nil {
		log.Fatalf("Failed to create provider: %v", err)
	}

	ctx := context.Background()
	query := "The Legend of Zelda"

	// First search - will hit the API
	fmt.Println("First search (no cache)...")
	start := time.Now()
	results1, err := provider.Search(ctx, query, retrometadata.SearchOptions{Limit: 5})
	if err != nil {
		log.Fatalf("Search failed: %v", err)
	}
	fmt.Printf("Found %d results in %v\n\n", len(results1), time.Since(start))

	// Second search - should be cached
	fmt.Println("Second search (should be cached)...")
	start = time.Now()
	results2, err := provider.Search(ctx, query, retrometadata.SearchOptions{Limit: 5})
	if err != nil {
		log.Fatalf("Search failed: %v", err)
	}
	fmt.Printf("Found %d results in %v\n\n", len(results2), time.Since(start))

	// Print cache stats
	stats, _ := memCache.Stats(ctx)
	fmt.Printf("Cache Stats:\n")
	fmt.Printf("  Size: %d / %d\n", stats.Size, stats.MaxSize)
	fmt.Printf("  Hits: %d\n", stats.Hits)
	fmt.Printf("  Misses: %d\n", stats.Misses)

	// Print results
	fmt.Printf("\nResults for '%s':\n", query)
	for i, result := range results1 {
		fmt.Printf("%d. %s (%s)\n", i+1, result.Name, result.Provider)
	}
}
