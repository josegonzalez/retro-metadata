// Example: Filename Parsing
//
// This example demonstrates how to parse ROM filenames to extract
// game information, regions, tags, and other metadata.
//
// To run:
//
//	go run main.go
package main

import (
	"fmt"

	"github.com/josegonzalez/retro-metadata/pkg/filename"
)

func main() {
	// Example ROM filenames
	examples := []string{
		"Super Mario World (USA).sfc",
		"Legend of Zelda, The - A Link to the Past (USA, Europe) (Rev 1).sfc",
		"Sonic the Hedgehog (Japan, Korea).md",
		"Pokemon - Red Version (USA, Europe) (SGB Enhanced).gb",
		"Chrono Trigger (USA) [!].sfc",
		"Final Fantasy VI (Japan) (Beta).sfc",
		"Street Fighter II' Turbo - Hyper Fighting (USA) (Virtual Console).sfc",
	}

	for _, romFilename := range examples {
		fmt.Printf("Filename: %s\n", romFilename)
		fmt.Println("────────────────────────────────────────────────")

		// Get file extension
		ext := filename.GetFileExtension(romFilename)
		fmt.Printf("  Extension: %s\n", ext)

		// Extract region
		region := filename.ExtractRegion(romFilename)
		fmt.Printf("  Region: %s\n", region)

		// Extract tags (parenthesized content)
		tags := filename.ExtractTags(romFilename)
		if len(tags) > 0 {
			fmt.Printf("  Tags: %v\n", tags)
		}

		// Clean the filename (remove extension and tags)
		cleanName := filename.CleanFilename(romFilename, true)
		fmt.Printf("  Clean Name: %s\n", cleanName)

		// Check if it's a BIOS file
		if filename.IsBiosFile(romFilename) {
			fmt.Printf("  Note: This is a BIOS file\n")
		}

		// Check if it's a demo
		if filename.IsDemoFile(romFilename) {
			fmt.Printf("  Note: This is a demo/beta file\n")
		}

		// Check if it's unlicensed
		if filename.IsUnlicensed(romFilename) {
			fmt.Printf("  Note: This is an unlicensed ROM\n")
		}

		fmt.Println()
	}

	// No-Intro filename parsing example
	fmt.Println("═══════════════════════════════════════════════")
	fmt.Println("No-Intro Filename Parsing")
	fmt.Println("═══════════════════════════════════════════════")

	noIntroExamples := []string{
		"Super Mario World (USA).sfc",
		"Legend of Zelda, The - A Link to the Past (USA, Europe) (Rev 1).sfc",
	}

	for _, romFilename := range noIntroExamples {
		fmt.Printf("\nFilename: %s\n", romFilename)
		parsed := filename.ParseNoIntroFilename(romFilename)
		fmt.Printf("  Name: %s\n", parsed.Name)
		fmt.Printf("  Region: %s\n", parsed.Region)
		if parsed.Version != "" {
			fmt.Printf("  Version: %s\n", parsed.Version)
		}
		if len(parsed.Tags) > 0 {
			fmt.Printf("  Tags: %v\n", parsed.Tags)
		}
		if len(parsed.Languages) > 0 {
			fmt.Printf("  Languages: %v\n", parsed.Languages)
		}
	}
}
