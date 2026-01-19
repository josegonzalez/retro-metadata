// Example: Basic Search
//
// This example demonstrates how to search for a game using the IGDB provider.
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

	// Create provider configuration
	config := retrometadata.ProviderConfig{
		Enabled: true,
		Credentials: map[string]string{
			"client_id":     clientID,
			"client_secret": clientSecret,
		},
		Timeout: 30,
	}

	// Create IGDB provider
	provider, err := igdb.NewProvider(config, nil)
	if err != nil {
		log.Fatalf("Failed to create provider: %v", err)
	}

	// Search for games
	ctx := context.Background()
	results, err := provider.Search(ctx, "Super Mario World", retrometadata.SearchOptions{
		Limit: 5,
	})
	if err != nil {
		log.Fatalf("Search failed: %v", err)
	}

	// Print results
	fmt.Printf("Found %d results for 'Super Mario World':\n\n", len(results))
	for i, result := range results {
		fmt.Printf("%d. %s\n", i+1, result.Name)
		fmt.Printf("   Provider: %s\n", result.Provider)
		fmt.Printf("   ID: %d\n", result.ProviderID)
		if result.ReleaseYear != nil {
			fmt.Printf("   Year: %d\n", *result.ReleaseYear)
		}
		if result.CoverURL != "" {
			fmt.Printf("   Cover: %s\n", result.CoverURL)
		}
		fmt.Println()
	}
}
