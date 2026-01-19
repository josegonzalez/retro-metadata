// Example: Identify Game from Filename
//
// This example demonstrates how to identify a game from its ROM filename.
//
// To run:
//
//	export IGDB_CLIENT_ID="your_client_id"
//	export IGDB_CLIENT_SECRET="your_client_secret"
//	go run main.go "Super Mario World (USA).sfc"
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/josegonzalez/retro-metadata/pkg/filename"
	"github.com/josegonzalez/retro-metadata/pkg/provider/igdb"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

func main() {
	// Get filename from command line
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run main.go <filename>")
		fmt.Println("Example: go run main.go \"Super Mario World (USA).sfc\"")
		os.Exit(1)
	}
	romFilename := os.Args[1]

	// Get credentials from environment variables
	clientID := os.Getenv("IGDB_CLIENT_ID")
	clientSecret := os.Getenv("IGDB_CLIENT_SECRET")

	if clientID == "" || clientSecret == "" {
		log.Fatal("Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables")
	}

	// Parse the filename first
	fmt.Printf("Parsing filename: %s\n\n", romFilename)

	// Get file extension
	ext := filename.GetFileExtension(romFilename)
	fmt.Printf("Extension: %s\n", ext)

	// Extract region
	region := filename.ExtractRegion(romFilename)
	fmt.Printf("Region: %s\n", region)

	// Clean the filename to get the game name
	cleanName := filename.CleanFilename(romFilename, true)
	fmt.Printf("Clean name: %s\n\n", cleanName)

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

	// Identify the game
	ctx := context.Background()
	result, err := provider.Identify(ctx, romFilename, retrometadata.IdentifyOptions{})
	if err != nil {
		log.Fatalf("Identify failed: %v", err)
	}

	if result == nil {
		fmt.Println("No game found")
		return
	}

	// Print result
	fmt.Println("Game Identified:")
	fmt.Printf("  Name: %s\n", result.Name)
	fmt.Printf("  Match Score: %.2f\n", result.MatchScore)

	if result.Summary != "" {
		summary := result.Summary
		if len(summary) > 200 {
			summary = summary[:200] + "..."
		}
		fmt.Printf("  Summary: %s\n", summary)
	}

	if len(result.Metadata.Genres) > 0 {
		fmt.Printf("  Genres: %v\n", result.Metadata.Genres)
	}

	if len(result.Metadata.Companies) > 0 {
		fmt.Printf("  Companies: %v\n", result.Metadata.Companies)
	}

	if result.Metadata.ReleaseYear != nil {
		fmt.Printf("  Year: %d\n", *result.Metadata.ReleaseYear)
	}

	if result.Artwork.CoverURL != "" {
		fmt.Printf("  Cover: %s\n", result.Artwork.CoverURL)
	}
}
