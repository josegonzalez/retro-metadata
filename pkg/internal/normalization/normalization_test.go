package normalization

import (
	"strings"
	"testing"

	"github.com/josegonzalez/retro-metadata/pkg/testutil"
)

func TestNormalizeSearchTerm(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to create test data loader: %v", err)
	}

	testCases, err := loader.GetTestCases("normalization", "normalize_search_term")
	if err != nil {
		t.Fatalf("Failed to load test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputMap()
			if !ok {
				t.Fatalf("Invalid input format")
			}

			name, _ := input["name"].(string)
			removeArticles := true
			if val, ok := input["remove_articles"].(bool); ok {
				removeArticles = val
			}
			removePunctuation := true
			if val, ok := input["remove_punctuation"].(bool); ok {
				removePunctuation = val
			}

			result := NormalizeSearchTerm(name, removeArticles, removePunctuation)

			// Handle different assertion types
			if expected, ok := tc.ExpectedString(); ok {
				if result != expected {
					t.Errorf("NormalizeSearchTerm(%q) = %q, expected %q", name, result, expected)
				}
			} else if tc.ExpectedContains != nil {
				expectedContains, _ := tc.ExpectedContains.(string)
				if !strings.Contains(result, expectedContains) {
					t.Errorf("NormalizeSearchTerm(%q) = %q, expected to contain %q", name, result, expectedContains)
				}
			} else if tc.ExpectedNotContains != nil {
				expectedNotContains, _ := tc.ExpectedNotContains.(string)
				if strings.Contains(result, expectedNotContains) {
					t.Errorf("NormalizeSearchTerm(%q) = %q, expected not to contain %q", name, result, expectedNotContains)
				}
			}
		})
	}
}

func TestNormalizeSearchTermDefault(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Super Mario World", "super mario world"},
		{"The Legend of Zelda", "legend of zelda"},
		{"  extra  spaces  ", "extra spaces"},
	}

	for _, tt := range tests {
		result := NormalizeSearchTermDefault(tt.input)
		if result != tt.expected {
			t.Errorf("NormalizeSearchTermDefault(%q) = %q, expected %q", tt.input, result, tt.expected)
		}
	}
}

func TestNormalizeCoverURL(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"", ""},
		{"https://example.com/image.jpg", "https://example.com/image.jpg"},
		{"//images.igdb.com/image.jpg", "https://images.igdb.com/image.jpg"},
	}

	for _, tt := range tests {
		result := NormalizeCoverURL(tt.input)
		if result != tt.expected {
			t.Errorf("NormalizeCoverURL(%q) = %q, expected %q", tt.input, result, tt.expected)
		}
	}
}

func TestSplitSearchTerm(t *testing.T) {
	tests := []struct {
		input    string
		minParts int
	}{
		{"Zelda: A Link to the Past", 2},
		{"Super-Mario-World", 3},
		{"Donkey Kong & Diddy Kong", 2},
		{"Simple Game", 1},
	}

	for _, tt := range tests {
		result := SplitSearchTerm(tt.input)
		if len(result) < tt.minParts {
			t.Errorf("SplitSearchTerm(%q) returned %d parts, expected at least %d", tt.input, len(result), tt.minParts)
		}
	}
}

func TestNormalizeForAPI(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Zelda: A Link to the Past", "Zelda: A Link to the Past"},
		{"Game - Subtitle", "Game: Subtitle"},
	}

	for _, tt := range tests {
		result := NormalizeForAPI(tt.input)
		if result != tt.expected {
			t.Errorf("NormalizeForAPI(%q) = %q, expected %q", tt.input, result, tt.expected)
		}
	}
}

func TestStripSensitiveQueryParams(t *testing.T) {
	tests := []struct {
		input    string
		contains string
	}{
		{"https://api.example.com?api_key=secret&name=test", "name=test"},
		{"https://api.example.com?client_id=abc&data=123", "data=123"},
	}

	for _, tt := range tests {
		result := StripSensitiveQueryParams(tt.input, nil)
		if !strings.Contains(result, tt.contains) {
			t.Errorf("StripSensitiveQueryParams(%q) should contain %q, got %q", tt.input, tt.contains, result)
		}
		if strings.Contains(result, "secret") || strings.Contains(result, "abc") {
			t.Errorf("StripSensitiveQueryParams(%q) should not contain sensitive values, got %q", tt.input, result)
		}
	}
}

func TestMaskSensitiveValues(t *testing.T) {
	values := map[string]string{
		"Authorization": "Bearer abcdef123456",
		"api_key":       "secretkey123",
		"name":          "test",
		"empty":         "",
	}

	result := MaskSensitiveValues(values)

	if result["name"] != "test" {
		t.Errorf("Non-sensitive value 'name' should not be masked")
	}
	if result["empty"] != "" {
		t.Errorf("Empty value should remain empty")
	}
	if result["api_key"] == "secretkey123" {
		t.Errorf("Sensitive value 'api_key' should be masked")
	}
	if !strings.Contains(result["Authorization"], "***") {
		t.Errorf("Authorization header should be masked")
	}
}

func TestRemoveAccents(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"café", "cafe"},
		{"naïve", "naive"},
		{"Pokémon", "Pokemon"},
	}

	for _, tt := range tests {
		result := removeAccents(tt.input)
		if result != tt.expected {
			t.Errorf("removeAccents(%q) = %q, expected %q", tt.input, result, tt.expected)
		}
	}
}

func TestHasNonASCII(t *testing.T) {
	tests := []struct {
		input    string
		expected bool
	}{
		{"hello", false},
		{"café", true},
		{"", false},
		{"123", false},
		{"日本語", true},
	}

	for _, tt := range tests {
		result := hasNonASCII(tt.input)
		if result != tt.expected {
			t.Errorf("hasNonASCII(%q) = %v, expected %v", tt.input, result, tt.expected)
		}
	}
}
