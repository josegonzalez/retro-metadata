// Example: Multi-Provider Search
//
// This example demonstrates how to search across multiple metadata providers
// concurrently and aggregate results.
//
// To run:
//
//	export IGDB_CLIENT_ID="your_client_id"
//	export IGDB_CLIENT_SECRET="your_client_secret"
//	export MOBYGAMES_API_KEY="your_api_key"
//	go run main.go
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"sync"
	"time"

	"github.com/josegonzalez/retro-metadata/pkg/provider/igdb"
	"github.com/josegonzalez/retro-metadata/pkg/provider/mobygames"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// Provider wraps a metadata provider with a name
type Provider struct {
	Name     string
	Searcher interface {
		Search(ctx context.Context, query string, opts retrometadata.SearchOptions) ([]retrometadata.SearchResult, error)
	}
}

func main() {
	// Get credentials from environment variables
	igdbClientID := os.Getenv("IGDB_CLIENT_ID")
	igdbClientSecret := os.Getenv("IGDB_CLIENT_SECRET")
	mobyAPIKey := os.Getenv("MOBYGAMES_API_KEY")

	// Create providers list
	var providers []Provider

	// Create IGDB provider if credentials are available
	if igdbClientID != "" && igdbClientSecret != "" {
		igdbConfig := retrometadata.ProviderConfig{
			Enabled: true,
			Credentials: map[string]string{
				"client_id":     igdbClientID,
				"client_secret": igdbClientSecret,
			},
			Timeout: 30,
		}
		igdbProvider, err := igdb.NewProvider(igdbConfig, nil)
		if err == nil {
			providers = append(providers, Provider{Name: "IGDB", Searcher: igdbProvider})
		}
	}

	// Create MobyGames provider if credentials are available
	if mobyAPIKey != "" {
		mobyConfig := retrometadata.ProviderConfig{
			Enabled: true,
			Credentials: map[string]string{
				"api_key": mobyAPIKey,
			},
			Timeout: 30,
		}
		mobyProvider, err := mobygames.NewProvider(mobyConfig, nil)
		if err == nil {
			providers = append(providers, Provider{Name: "MobyGames", Searcher: mobyProvider})
		}
	}

	if len(providers) == 0 {
		log.Fatal("No providers available. Please set at least one of:\n" +
			"  IGDB_CLIENT_ID and IGDB_CLIENT_SECRET\n" +
			"  MOBYGAMES_API_KEY")
	}

	fmt.Printf("Using %d provider(s)\n\n", len(providers))

	// Search query
	query := "Chrono Trigger"
	ctx := context.Background()

	// Search all providers concurrently
	fmt.Printf("Searching for '%s' across all providers...\n\n", query)
	start := time.Now()

	var wg sync.WaitGroup
	resultsChan := make(chan struct {
		providerName string
		results      []retrometadata.SearchResult
		err          error
	}, len(providers))

	for _, p := range providers {
		wg.Add(1)
		go func(provider Provider) {
			defer wg.Done()
			results, err := provider.Searcher.Search(ctx, query, retrometadata.SearchOptions{Limit: 5})
			resultsChan <- struct {
				providerName string
				results      []retrometadata.SearchResult
				err          error
			}{provider.Name, results, err}
		}(p)
	}

	// Wait for all searches to complete
	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	// Collect results
	allResults := make(map[string][]retrometadata.SearchResult)
	for result := range resultsChan {
		if result.err != nil {
			fmt.Printf("[%s] Error: %v\n", result.providerName, result.err)
		} else {
			allResults[result.providerName] = result.results
		}
	}

	fmt.Printf("Search completed in %v\n\n", time.Since(start))

	// Print results by provider
	for providerName, results := range allResults {
		fmt.Printf("═══ %s Results ═══\n", providerName)
		if len(results) == 0 {
			fmt.Println("  No results found")
		} else {
			for i, result := range results {
				fmt.Printf("%d. %s\n", i+1, result.Name)
				if result.ReleaseYear != nil {
					fmt.Printf("   Year: %d\n", *result.ReleaseYear)
				}
				if len(result.Platforms) > 0 {
					fmt.Printf("   Platforms: %v\n", result.Platforms)
				}
			}
		}
		fmt.Println()
	}
}
