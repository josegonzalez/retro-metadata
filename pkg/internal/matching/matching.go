// Package matching provides string matching utilities using Jaro-Winkler similarity.
package matching

import (
	"strings"

	"github.com/adrg/strutil"
	"github.com/adrg/strutil/metrics"
	"github.com/josegonzalez/retro-metadata/pkg/internal/normalization"
)

// DefaultMinSimilarity is the default minimum similarity score for a match.
const DefaultMinSimilarity = 0.75

// jaroWinkler is a reusable Jaro-Winkler metric instance.
var jaroWinkler = metrics.NewJaroWinkler()

// JaroWinklerSimilarity calculates the Jaro-Winkler similarity between two strings.
// The comparison is case-insensitive and returns a value between 0 and 1,
// where 1 indicates an exact match.
func JaroWinklerSimilarity(s1, s2 string) float64 {
	return strutil.Similarity(strings.ToLower(s1), strings.ToLower(s2), jaroWinkler)
}

// FindBestMatchOptions contains options for FindBestMatch.
type FindBestMatchOptions struct {
	// MinSimilarityScore is the minimum similarity score to consider a match
	MinSimilarityScore float64
	// SplitCandidateName splits candidates by delimiters and matches against last part
	SplitCandidateName bool
	// Normalize indicates whether to normalize strings before comparison
	Normalize bool
	// FirstNOnly limits matching to the first N candidates
	FirstNOnly int
}

// DefaultFindBestMatchOptions returns sensible defaults for FindBestMatch.
func DefaultFindBestMatchOptions() FindBestMatchOptions {
	return FindBestMatchOptions{
		MinSimilarityScore: DefaultMinSimilarity,
		SplitCandidateName: false,
		Normalize:          true,
		FirstNOnly:         0, // no limit
	}
}

// FindBestMatch finds the best matching name from a list of candidates.
// It returns the best match and its similarity score, or ("", 0.0) if no match
// meets the minimum threshold.
func FindBestMatch(searchTerm string, candidates []string, opts FindBestMatchOptions) (string, float64) {
	if len(candidates) == 0 {
		return "", 0.0
	}

	// Normalize the search term once
	var searchTermNormalized string
	if opts.Normalize {
		searchTermNormalized = normalization.NormalizeSearchTermDefault(searchTerm)
	} else {
		searchTermNormalized = strings.ToLower(strings.TrimSpace(searchTerm))
	}

	// Determine which candidates to check
	candidatesToCheck := candidates
	if opts.FirstNOnly > 0 && opts.FirstNOnly < len(candidates) {
		candidatesToCheck = candidates[:opts.FirstNOnly]
	}

	var bestMatch string
	var bestScore float64

	for _, candidate := range candidatesToCheck {
		// Normalize the candidate name
		var candidateNormalized string
		if opts.Normalize {
			candidateNormalized = normalization.NormalizeSearchTermDefault(candidate)
		} else {
			candidateNormalized = strings.ToLower(strings.TrimSpace(candidate))
		}

		// If split mode is enabled and candidate contains delimiters, try the last part
		if opts.SplitCandidateName {
			parts := normalization.SplitSearchTerm(candidate)
			if len(parts) > 1 {
				lastPart := parts[len(parts)-1]
				if opts.Normalize {
					candidateNormalized = normalization.NormalizeSearchTermDefault(lastPart)
				} else {
					candidateNormalized = strings.ToLower(strings.TrimSpace(lastPart))
				}
			}
		}

		// Calculate similarity
		score := JaroWinklerSimilarity(searchTermNormalized, candidateNormalized)

		if score > bestScore {
			bestScore = score
			bestMatch = candidate

			// Early exit for perfect match
			if score == 1.0 {
				break
			}
		}
	}

	if bestScore >= opts.MinSimilarityScore {
		return bestMatch, bestScore
	}

	return "", 0.0
}

// FindBestMatchSimple is a convenience function that uses default options.
func FindBestMatchSimple(searchTerm string, candidates []string) (string, float64) {
	return FindBestMatch(searchTerm, candidates, DefaultFindBestMatchOptions())
}

// MatchResult represents a match result with its score.
type MatchResult struct {
	Name  string
	Score float64
}

// FindAllMatches finds all matching names above the minimum similarity threshold.
// Results are sorted by score in descending order.
func FindAllMatches(searchTerm string, candidates []string, minScore float64, maxResults int) []MatchResult {
	if len(candidates) == 0 {
		return nil
	}

	// Normalize the search term once
	searchTermNormalized := normalization.NormalizeSearchTermDefault(searchTerm)

	var matches []MatchResult

	for _, candidate := range candidates {
		candidateNormalized := normalization.NormalizeSearchTermDefault(candidate)
		score := JaroWinklerSimilarity(searchTermNormalized, candidateNormalized)

		if score >= minScore {
			matches = append(matches, MatchResult{Name: candidate, Score: score})
		}
	}

	// Sort by score descending using insertion sort (typically small lists)
	for i := 1; i < len(matches); i++ {
		j := i
		for j > 0 && matches[j].Score > matches[j-1].Score {
			matches[j], matches[j-1] = matches[j-1], matches[j]
			j--
		}
	}

	if maxResults > 0 && len(matches) > maxResults {
		matches = matches[:maxResults]
	}

	return matches
}

// IsExactMatch checks if two strings are an exact match after normalization.
func IsExactMatch(s1, s2 string, normalize bool) bool {
	if normalize {
		return normalization.NormalizeSearchTermDefault(s1) == normalization.NormalizeSearchTermDefault(s2)
	}
	return strings.ToLower(strings.TrimSpace(s1)) == strings.ToLower(strings.TrimSpace(s2))
}

// MatchConfidence returns a human-readable confidence level for a match.
func MatchConfidence(searchTerm, matchedName string, normalize bool) string {
	var s1, s2 string
	if normalize {
		s1 = normalization.NormalizeSearchTermDefault(searchTerm)
		s2 = normalization.NormalizeSearchTermDefault(matchedName)
	} else {
		s1 = strings.ToLower(strings.TrimSpace(searchTerm))
		s2 = strings.ToLower(strings.TrimSpace(matchedName))
	}

	if s1 == s2 {
		return "exact"
	}

	score := JaroWinklerSimilarity(s1, s2)

	switch {
	case score >= 0.95:
		return "high"
	case score >= 0.85:
		return "medium"
	case score >= 0.75:
		return "low"
	default:
		return "none"
	}
}
