// Package normalization provides text normalization utilities for game name matching.
package normalization

import (
	"net/url"
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/unicode/norm"
)

var (
	// leadingArticlePattern matches leading articles (a, an, the)
	leadingArticlePattern = regexp.MustCompile(`(?i)^(a|an|the)\b`)

	// commaArticlePattern matches comma-separated articles
	commaArticlePattern = regexp.MustCompile(`(?i),\s(a|an|the)\b(?:\s*[^\w\s]|$)`)

	// nonWordSpacePattern matches non-word, non-space characters
	nonWordSpacePattern = regexp.MustCompile(`[^\w\s]`)

	// multipleSpacePattern matches multiple consecutive spaces
	multipleSpacePattern = regexp.MustCompile(`\s+`)

	// searchTermSplitPattern splits by common delimiters
	searchTermSplitPattern = regexp.MustCompile(`[:\-/&]`)

	// searchTermNormalizer normalizes colon/dash patterns
	searchTermNormalizer = regexp.MustCompile(`\s*[:-]\s+`)

	// sensitiveKeys is the set of keys that should be masked in URLs
	sensitiveKeys = map[string]bool{
		"authorization":  true,
		"client-id":      true,
		"client-secret":  true,
		"client_id":      true,
		"client_secret":  true,
		"api_key":        true,
		"ssid":           true,
		"sspassword":     true,
		"devid":          true,
		"devpassword":    true,
		"y":              true,
	}
)

// NormalizeSearchTerm normalizes a search term for comparison.
// It performs the following transformations:
// - Converts to lowercase
// - Replaces underscores with spaces
// - Optionally removes articles (a, an, the)
// - Optionally removes punctuation
// - Normalizes Unicode characters and removes accents
func NormalizeSearchTerm(name string, removeArticles, removePunctuation bool) string {
	// Lowercase and replace underscores
	name = strings.ToLower(name)
	name = strings.ReplaceAll(name, "_", " ")

	// Remove articles
	if removeArticles {
		name = leadingArticlePattern.ReplaceAllString(name, "")
		name = commaArticlePattern.ReplaceAllString(name, "")
	}

	// Remove punctuation and normalize spaces
	if removePunctuation {
		name = nonWordSpacePattern.ReplaceAllString(name, " ")
		name = multipleSpacePattern.ReplaceAllString(name, " ")
	}

	// Unicode normalization and accent removal
	if hasNonASCII(name) {
		name = removeAccents(name)
	}

	return strings.TrimSpace(name)
}

// NormalizeSearchTermDefault normalizes a search term with default options (remove articles and punctuation).
func NormalizeSearchTermDefault(name string) string {
	return NormalizeSearchTerm(name, true, true)
}

// hasNonASCII checks if the string contains non-ASCII characters.
func hasNonASCII(s string) bool {
	for _, r := range s {
		if r > 127 {
			return true
		}
	}
	return false
}

// removeAccents removes diacritical marks from Unicode characters.
func removeAccents(s string) string {
	// Normalize to NFD form (decomposed)
	normalized := norm.NFD.String(s)

	// Build result without combining marks
	var result strings.Builder
	for _, r := range normalized {
		if !unicode.Is(unicode.Mn, r) { // Mn = Mark, Nonspacing
			result.WriteRune(r)
		}
	}

	return result.String()
}

// NormalizeCoverURL normalizes a cover image URL to ensure consistent format.
func NormalizeCoverURL(coverURL string) string {
	if coverURL == "" {
		return coverURL
	}
	// Ensure https:// prefix
	coverURL = strings.Replace(coverURL, "https:", "", 1)
	return "https:" + coverURL
}

// SplitSearchTerm splits a search term by common delimiters.
func SplitSearchTerm(name string) []string {
	return searchTermSplitPattern.Split(name, -1)
}

// NormalizeForAPI normalizes a search term for API queries.
func NormalizeForAPI(searchTerm string) string {
	return searchTermNormalizer.ReplaceAllString(searchTerm, ": ")
}

// StripSensitiveQueryParams removes sensitive query parameters from a URL for logging.
func StripSensitiveQueryParams(rawURL string, customSensitiveKeys map[string]bool) string {
	parsedURL, err := url.Parse(rawURL)
	if err != nil {
		return rawURL
	}

	keys := sensitiveKeys
	if customSensitiveKeys != nil {
		keys = customSensitiveKeys
	}

	query := parsedURL.Query()
	for key := range query {
		if keys[strings.ToLower(key)] {
			query.Del(key)
		}
	}

	parsedURL.RawQuery = query.Encode()
	return parsedURL.String()
}

// MaskSensitiveValues masks sensitive values for safe logging.
func MaskSensitiveValues(values map[string]string) map[string]string {
	masked := make(map[string]string, len(values))

	for key, val := range values {
		if val == "" {
			masked[key] = ""
			continue
		}

		if key == "Authorization" && strings.HasPrefix(val, "Bearer ") {
			token := strings.TrimPrefix(val, "Bearer ")
			if len(token) > 4 {
				masked[key] = "Bearer " + token[:2] + "***" + token[len(token)-2:]
			} else {
				masked[key] = "Bearer ***"
			}
		} else if sensitiveKeys[strings.ToLower(key)] {
			if len(val) > 4 {
				masked[key] = val[:2] + "***" + val[len(val)-2:]
			} else {
				masked[key] = "***"
			}
		} else {
			masked[key] = val
		}
	}

	return masked
}
