package filename

import (
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
