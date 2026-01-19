// Package filename provides filename parsing utilities for ROM files.
package filename

import (
	"path/filepath"
	"regexp"
	"strings"
)

// RegionTags maps region indicators to normalized region codes.
var RegionTags = map[string]string{
	"usa":         "us",
	"u":           "us",
	"us":          "us",
	"america":     "us",
	"world":       "wor",
	"w":           "wor",
	"wor":         "wor",
	"europe":      "eu",
	"e":           "eu",
	"eu":          "eu",
	"eur":         "eu",
	"japan":       "jp",
	"j":           "jp",
	"jp":          "jp",
	"jpn":         "jp",
	"jap":         "jp",
	"korea":       "kr",
	"k":           "kr",
	"kr":          "kr",
	"kor":         "kr",
	"china":       "cn",
	"ch":          "cn",
	"cn":          "cn",
	"chn":         "cn",
	"taiwan":      "tw",
	"tw":          "tw",
	"asia":        "as",
	"as":          "as",
	"australia":   "au",
	"au":          "au",
	"brazil":      "br",
	"br":          "br",
	"france":      "fr",
	"fr":          "fr",
	"germany":     "de",
	"de":          "de",
	"ger":         "de",
	"italy":       "it",
	"it":          "it",
	"spain":       "es",
	"es":          "es",
	"spa":         "es",
	"netherlands": "nl",
	"nl":          "nl",
	"sweden":      "se",
	"se":          "se",
	"russia":      "ru",
	"ru":          "ru",
}

var (
	// tagPattern matches tags in parentheses or brackets
	tagPattern = regexp.MustCompile(`[\(\[]([^\)\]]+)[\)\]]`)

	// extensionPattern matches file extensions
	extensionPattern = regexp.MustCompile(`\.([a-zA-Z0-9]+)$`)

	// demoTags are tags that indicate a demo/prototype file
	demoTags = map[string]bool{
		"demo":      true,
		"sample":    true,
		"trial":     true,
		"preview":   true,
		"proto":     true,
		"prototype": true,
		"beta":      true,
		"alpha":     true,
	}

	// unlicensedTags are tags that indicate an unlicensed game
	unlicensedTags = map[string]bool{
		"unl":        true,
		"unlicensed": true,
		"pirate":     true,
		"hack":       true,
	}
)

// GetFileExtension returns the file extension from a filename (without the dot, lowercased).
func GetFileExtension(filename string) string {
	match := extensionPattern.FindStringSubmatch(filename)
	if len(match) > 1 {
		return strings.ToLower(match[1])
	}
	return ""
}

// ExtractTags extracts all tags from a filename.
// Tags are text within parentheses or brackets.
func ExtractTags(filename string) []string {
	matches := tagPattern.FindAllStringSubmatch(filename, -1)
	tags := make([]string, 0, len(matches))
	for _, match := range matches {
		if len(match) > 1 {
			tags = append(tags, match[1])
		}
	}
	return tags
}

// ExtractRegion extracts the region code from a filename.
// Returns the normalized region code (us, eu, jp, etc.) or empty string if not found.
func ExtractRegion(filename string) string {
	tags := ExtractTags(filename)

	for _, tag := range tags {
		tagLower := strings.ToLower(strings.TrimSpace(tag))

		// Handle comma-separated regions (e.g., "USA, Europe")
		for _, part := range strings.Split(tagLower, ",") {
			part = strings.TrimSpace(part)
			if region, ok := RegionTags[part]; ok {
				return region
			}
		}
	}

	return ""
}

// CleanFilename cleans a filename by removing tags and optionally the extension.
func CleanFilename(filename string, removeExtension bool) string {
	// Get just the filename if a path was provided
	name := filepath.Base(filename)

	// Save and remove extension if keeping it
	var ext string
	if !removeExtension {
		match := extensionPattern.FindStringSubmatch(name)
		if len(match) > 0 {
			ext = match[0]
		}
	}

	// Remove extension from name for processing
	name = extensionPattern.ReplaceAllString(name, "")

	// Remove all tags in parentheses and brackets
	name = tagPattern.ReplaceAllString(name, "")

	// Clean up extra whitespace
	name = strings.Join(strings.Fields(name), " ")

	// Reattach extension if keeping it
	if ext != "" {
		name = name + ext
	}

	return strings.TrimSpace(name)
}

// ParsedFilename contains components parsed from a No-Intro filename.
type ParsedFilename struct {
	// Name is the cleaned game name
	Name string `json:"name"`
	// Region is the normalized region code (us, eu, jp, etc.)
	Region string `json:"region"`
	// Version is the version tag if found (e.g., "Rev 1", "v1.1")
	Version string `json:"version"`
	// Languages is a list of language tags
	Languages []string `json:"languages"`
	// Extension is the file extension
	Extension string `json:"extension"`
	// Tags is all extracted tags
	Tags []string `json:"tags"`
}

// ParseNoIntroFilename parses a No-Intro naming convention filename.
// No-Intro filenames follow the format: Title (Region) (Language) (Version) (Other Tags)
func ParseNoIntroFilename(filename string) ParsedFilename {
	name := CleanFilename(filename, true)
	tags := ExtractTags(filename)
	region := ExtractRegion(filename)
	extension := GetFileExtension(filename)

	// Try to identify version
	var version string
	for _, tag := range tags {
		tagLower := strings.ToLower(tag)
		if strings.HasPrefix(tagLower, "rev ") ||
			strings.HasPrefix(tagLower, "v") ||
			strings.HasPrefix(tagLower, "version") {
			version = tag
			break
		}
	}

	// Try to identify languages
	languageCodes := map[string]bool{
		"en": true, "ja": true, "de": true, "fr": true, "es": true,
		"it": true, "nl": true, "pt": true, "sv": true, "ko": true, "zh": true,
	}
	var languages []string
	for _, tag := range tags {
		tagLower := strings.ToLower(tag)
		if languageCodes[tagLower] || strings.Contains(tagLower, "+") {
			languages = append(languages, tag)
		}
	}

	return ParsedFilename{
		Name:      name,
		Region:    region,
		Version:   version,
		Languages: languages,
		Extension: extension,
		Tags:      tags,
	}
}

// IsBiosFile checks if a filename appears to be a BIOS file.
func IsBiosFile(filename string) bool {
	nameLower := strings.ToLower(filename)
	biosIndicators := []string{"bios", "[bios]", "(bios)"}
	for _, indicator := range biosIndicators {
		if strings.Contains(nameLower, indicator) {
			return true
		}
	}
	return false
}

// IsDemoFile checks if a filename appears to be a demo, prototype, or beta.
func IsDemoFile(filename string) bool {
	tags := ExtractTags(filename)
	for _, tag := range tags {
		if demoTags[strings.ToLower(tag)] {
			return true
		}
	}
	return false
}

// IsUnlicensed checks if a filename indicates an unlicensed game.
func IsUnlicensed(filename string) bool {
	tags := ExtractTags(filename)
	for _, tag := range tags {
		if unlicensedTags[strings.ToLower(tag)] {
			return true
		}
	}
	return false
}
