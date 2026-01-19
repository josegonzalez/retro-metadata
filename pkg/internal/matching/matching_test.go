package matching

import (
	"testing"

	"github.com/josegonzalez/retro-metadata/pkg/testutil"
)

func TestJaroWinklerSimilarity(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to create test data loader: %v", err)
	}

	testCases, err := loader.GetTestCases("matching", "jaro_winkler_similarity")
	if err != nil {
		t.Fatalf("Failed to load test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputMap()
			if !ok {
				t.Fatalf("Invalid input format")
			}

			s1, _ := input["s1"].(string)
			s2, _ := input["s2"].(string)

			result := JaroWinklerSimilarity(s1, s2)

			// Handle different assertion types
			if expected, ok := tc.ExpectedFloat(); ok {
				if result != expected {
					t.Errorf("JaroWinklerSimilarity(%q, %q) = %v, expected %v", s1, s2, result, expected)
				}
			} else if tc.ExpectedMin != nil {
				if result < *tc.ExpectedMin {
					t.Errorf("JaroWinklerSimilarity(%q, %q) = %v, expected >= %v", s1, s2, result, *tc.ExpectedMin)
				}
			} else if tc.ExpectedMax != nil {
				if result > *tc.ExpectedMax {
					t.Errorf("JaroWinklerSimilarity(%q, %q) = %v, expected <= %v", s1, s2, result, *tc.ExpectedMax)
				}
			}
		})
	}
}

func TestFindBestMatch(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to create test data loader: %v", err)
	}

	testCases, err := loader.GetTestCases("matching", "find_best_match")
	if err != nil {
		t.Fatalf("Failed to load test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputMap()
			if !ok {
				t.Fatalf("Invalid input format")
			}

			searchTerm, _ := input["search_term"].(string)
			candidatesRaw, _ := input["candidates"].([]interface{})
			minScore := DefaultMinSimilarity
			if score, ok := input["min_similarity_score"].(float64); ok {
				minScore = score
			}

			candidates := make([]string, len(candidatesRaw))
			for i, c := range candidatesRaw {
				candidates[i], _ = c.(string)
			}

			opts := FindBestMatchOptions{
				MinSimilarityScore: minScore,
				Normalize:          true,
			}

			if firstN, ok := input["first_n_only"].(float64); ok {
				opts.FirstNOnly = int(firstN)
			}

			match, score := FindBestMatch(searchTerm, candidates, opts)

			expected, ok := tc.ExpectedMap()
			if !ok {
				t.Fatalf("Invalid expected format")
			}

			// Check match
			if expectedMatch, ok := expected["match"]; ok {
				if expectedMatch == nil {
					if match != "" {
						t.Errorf("Expected no match, got %q", match)
					}
				} else if expectedMatchStr, ok := expectedMatch.(string); ok {
					if match != expectedMatchStr {
						t.Errorf("Expected match %q, got %q", expectedMatchStr, match)
					}
				}
			}

			// Check match_not
			if matchNot, ok := expected["match_not"].(string); ok {
				if match == matchNot {
					t.Errorf("Match should not be %q", matchNot)
				}
			}

			// Check exact score
			if expectedScore, ok := expected["score"].(float64); ok {
				if score != expectedScore {
					t.Errorf("Expected score %v, got %v", expectedScore, score)
				}
			}

			// Check minimum score
			if expectedScoreMin, ok := expected["score_min"].(float64); ok {
				if score < expectedScoreMin {
					t.Errorf("Expected score >= %v, got %v", expectedScoreMin, score)
				}
			}
		})
	}
}

func TestFindBestMatchSimple(t *testing.T) {
	match, score := FindBestMatchSimple("Super Mario World", []string{"Super Mario World", "Zelda"})
	if match != "Super Mario World" {
		t.Errorf("Expected 'Super Mario World', got %q", match)
	}
	if score != 1.0 {
		t.Errorf("Expected score 1.0, got %v", score)
	}
}

func TestFindAllMatches(t *testing.T) {
	candidates := []string{"Super Mario World", "Super Mario Bros", "Super Mario Kart", "Zelda"}
	matches := FindAllMatches("Super Mario", candidates, 0.7, 3)

	if len(matches) == 0 {
		t.Errorf("Expected matches, got none")
	}

	// Results should be sorted by score descending
	for i := 1; i < len(matches); i++ {
		if matches[i].Score > matches[i-1].Score {
			t.Errorf("Results not sorted by score descending")
		}
	}
}

func TestIsExactMatch(t *testing.T) {
	tests := []struct {
		s1, s2    string
		normalize bool
		expected  bool
	}{
		{"test", "test", false, true},
		{"TEST", "test", false, true},
		{"Super Mario World", "super mario world", true, true},
		{"The Legend of Zelda", "legend of zelda", true, true},
		{"different", "strings", true, false},
	}

	for _, tt := range tests {
		result := IsExactMatch(tt.s1, tt.s2, tt.normalize)
		if result != tt.expected {
			t.Errorf("IsExactMatch(%q, %q, %v) = %v, expected %v", tt.s1, tt.s2, tt.normalize, result, tt.expected)
		}
	}
}

func TestMatchConfidence(t *testing.T) {
	tests := []struct {
		searchTerm, matchedName string
		normalize               bool
		expected                string
	}{
		{"Super Mario World", "Super Mario World", true, "exact"},
		{"Super Mario Wrld", "Super Mario World", true, "high"},
		{"completely different", "strings", true, "none"},
	}

	for _, tt := range tests {
		result := MatchConfidence(tt.searchTerm, tt.matchedName, tt.normalize)
		if result != tt.expected {
			t.Errorf("MatchConfidence(%q, %q, %v) = %q, expected %q", tt.searchTerm, tt.matchedName, tt.normalize, result, tt.expected)
		}
	}
}
