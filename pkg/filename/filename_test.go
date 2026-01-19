package filename

import (
	"reflect"
	"testing"

	"github.com/josegonzalez/retro-metadata/pkg/testutil"
)

func TestGetFileExtension(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "get_file_extension")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputString()
			if !ok {
				t.Skipf("Input is not a string")
				return
			}

			expected, _ := tc.ExpectedString()
			result := GetFileExtension(input)

			if result != expected {
				t.Errorf("GetFileExtension(%q) = %q, want %q", input, result, expected)
			}
		})
	}
}

func TestExtractTags(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "extract_tags")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputString()
			if !ok {
				t.Skipf("Input is not a string")
				return
			}

			expectedTags, ok := tc.ExpectedStringSlice()
			if !ok {
				t.Skipf("Expected is not a string slice")
				return
			}

			result := ExtractTags(input)

			if len(result) != len(expectedTags) {
				t.Errorf("ExtractTags(%q) returned %d tags, want %d", input, len(result), len(expectedTags))
				return
			}

			for i, tag := range expectedTags {
				if result[i] != tag {
					t.Errorf("ExtractTags(%q)[%d] = %q, want %q", input, i, result[i], tag)
				}
			}
		})
	}
}

func TestExtractRegion(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "extract_region")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputString()
			if !ok {
				t.Skipf("Input is not a string")
				return
			}

			result := ExtractRegion(input)

			if tc.IsExpectedNull() {
				if result != "" {
					t.Errorf("ExtractRegion(%q) = %q, want empty string", input, result)
				}
			} else {
				expected, _ := tc.ExpectedString()
				if result != expected {
					t.Errorf("ExtractRegion(%q) = %q, want %q", input, result, expected)
				}
			}
		})
	}
}

func TestIsBiosFile(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "is_bios_file")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputString()
			if !ok {
				t.Skipf("Input is not a string")
				return
			}

			expected, ok := tc.ExpectedBool()
			if !ok {
				t.Skipf("Expected is not a bool")
				return
			}

			result := IsBiosFile(input)

			if result != expected {
				t.Errorf("IsBiosFile(%q) = %v, want %v", input, result, expected)
			}
		})
	}
}

func TestIsDemoFile(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "is_demo_file")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputString()
			if !ok {
				t.Skipf("Input is not a string")
				return
			}

			expected, ok := tc.ExpectedBool()
			if !ok {
				t.Skipf("Expected is not a bool")
				return
			}

			result := IsDemoFile(input)

			if result != expected {
				t.Errorf("IsDemoFile(%q) = %v, want %v", input, result, expected)
			}
		})
	}
}

func TestIsUnlicensed(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "is_unlicensed")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputString()
			if !ok {
				t.Skipf("Input is not a string")
				return
			}

			expected, ok := tc.ExpectedBool()
			if !ok {
				t.Skipf("Expected is not a bool")
				return
			}

			result := IsUnlicensed(input)

			if result != expected {
				t.Errorf("IsUnlicensed(%q) = %v, want %v", input, result, expected)
			}
		})
	}
}

func TestCleanFilename(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "clean_filename")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputMap()
			if !ok {
				t.Fatalf("Invalid input format")
			}

			filename, _ := input["filename"].(string)
			removeExtension := true
			if val, ok := input["remove_extension"].(bool); ok {
				removeExtension = val
			}

			expected, _ := tc.ExpectedString()
			result := CleanFilename(filename, removeExtension)

			if result != expected {
				t.Errorf("CleanFilename(%q, %v) = %q, want %q",
					filename, removeExtension, result, expected)
			}
		})
	}
}

func TestParseNoIntroFilename(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("filename", "parse_no_intro_filename")
	if err != nil {
		t.Fatalf("Failed to get test cases: %v", err)
	}

	for _, tc := range testCases {
		t.Run(tc.ID, func(t *testing.T) {
			input, ok := tc.InputString()
			if !ok {
				t.Fatalf("Invalid input format")
			}

			expected, ok := tc.ExpectedMap()
			if !ok {
				t.Fatalf("Invalid expected format")
			}

			result := ParseNoIntroFilename(input)

			// Check name
			expectedName, _ := expected["name"].(string)
			if result.Name != expectedName {
				t.Errorf("ParseNoIntroFilename(%q).Name = %q, want %q",
					input, result.Name, expectedName)
			}

			// Check region
			expectedRegion := ""
			if region, ok := expected["region"].(string); ok {
				expectedRegion = region
			}
			if result.Region != expectedRegion {
				t.Errorf("ParseNoIntroFilename(%q).Region = %q, want %q",
					input, result.Region, expectedRegion)
			}

			// Check extension
			expectedExt, _ := expected["extension"].(string)
			if result.Extension != expectedExt {
				t.Errorf("ParseNoIntroFilename(%q).Extension = %q, want %q",
					input, result.Extension, expectedExt)
			}

			// Check version (can be null)
			expectedVersion := ""
			if version, ok := expected["version"].(string); ok {
				expectedVersion = version
			}
			if result.Version != expectedVersion {
				t.Errorf("ParseNoIntroFilename(%q).Version = %q, want %q",
					input, result.Version, expectedVersion)
			}

			// Check tags
			expectedTags := []string{}
			if tags, ok := expected["tags"].([]interface{}); ok {
				for _, tag := range tags {
					if s, ok := tag.(string); ok {
						expectedTags = append(expectedTags, s)
					}
				}
			}
			if !reflect.DeepEqual(result.Tags, expectedTags) {
				t.Errorf("ParseNoIntroFilename(%q).Tags = %v, want %v",
					input, result.Tags, expectedTags)
			}
		})
	}
}
