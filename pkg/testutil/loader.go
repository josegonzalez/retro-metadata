// Package testutil provides utilities for loading shared test data.
package testutil

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// TestData represents the structure of a shared test data file.
type TestData struct {
	Version     string     `json:"version"`
	TestSuite   string     `json:"test_suite"`
	Description string     `json:"description"`
	TestCases   []TestCase `json:"test_cases"`
}

// TestCase represents a single test case.
type TestCase struct {
	ID                  string      `json:"id"`
	Description         string      `json:"description"`
	Category            string      `json:"category"`
	Input               interface{} `json:"input"`
	Expected            interface{} `json:"expected"`
	ExpectedMin         *float64    `json:"expected_min,omitempty"`
	ExpectedMax         *float64    `json:"expected_max,omitempty"`
	ExpectedContains    interface{} `json:"expected_contains,omitempty"`
	ExpectedNotContains interface{} `json:"expected_not_contains,omitempty"`
	Skip                *SkipConfig `json:"skip,omitempty"`
}

// SkipConfig contains skip conditions for specific languages.
type SkipConfig struct {
	Python string `json:"python,omitempty"`
	Go     string `json:"go,omitempty"`
}

// ShouldSkipGo returns true if this test should be skipped in Go.
func (tc *TestCase) ShouldSkipGo() bool {
	return tc.Skip != nil && tc.Skip.Go != ""
}

// InputString returns the input as a string, if it is one.
func (tc *TestCase) InputString() (string, bool) {
	s, ok := tc.Input.(string)
	return s, ok
}

// InputMap returns the input as a map, if it is one.
func (tc *TestCase) InputMap() (map[string]interface{}, bool) {
	m, ok := tc.Input.(map[string]interface{})
	return m, ok
}

// ExpectedString returns the expected value as a string, if it is one.
func (tc *TestCase) ExpectedString() (string, bool) {
	s, ok := tc.Expected.(string)
	return s, ok
}

// ExpectedFloat returns the expected value as a float64, if it is one.
func (tc *TestCase) ExpectedFloat() (float64, bool) {
	f, ok := tc.Expected.(float64)
	return f, ok
}

// ExpectedBool returns the expected value as a bool, if it is one.
func (tc *TestCase) ExpectedBool() (bool, bool) {
	b, ok := tc.Expected.(bool)
	return b, ok
}

// ExpectedStringSlice returns the expected value as a string slice, if it is one.
func (tc *TestCase) ExpectedStringSlice() ([]string, bool) {
	arr, ok := tc.Expected.([]interface{})
	if !ok {
		return nil, false
	}
	result := make([]string, len(arr))
	for i, v := range arr {
		s, ok := v.(string)
		if !ok {
			return nil, false
		}
		result[i] = s
	}
	return result, true
}

// ExpectedMap returns the expected value as a map, if it is one.
func (tc *TestCase) ExpectedMap() (map[string]interface{}, bool) {
	m, ok := tc.Expected.(map[string]interface{})
	return m, ok
}

// IsExpectedNull returns true if the expected value is null/nil.
func (tc *TestCase) IsExpectedNull() bool {
	return tc.Expected == nil
}

// Loader loads test data from shared JSON files.
type Loader struct {
	testdataDir string
}

// NewLoader creates a new test data loader.
// The testdataDir should be the path to the testdata directory.
func NewLoader(testdataDir string) *Loader {
	return &Loader{testdataDir: testdataDir}
}

// findTestdataDir searches for the testdata directory by walking up from the current directory.
func findTestdataDir() (string, error) {
	// Start from the current working directory
	dir, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("getting current directory: %w", err)
	}

	// Walk up to find testdata directory
	for {
		testdataPath := filepath.Join(dir, "testdata")
		if info, err := os.Stat(testdataPath); err == nil && info.IsDir() {
			return testdataPath, nil
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			// Reached root without finding testdata
			break
		}
		dir = parent
	}

	return "", fmt.Errorf("testdata directory not found")
}

// NewLoaderFromRepo creates a loader that automatically finds the testdata directory.
func NewLoaderFromRepo() (*Loader, error) {
	testdataDir, err := findTestdataDir()
	if err != nil {
		return nil, err
	}
	return NewLoader(testdataDir), nil
}

// Load loads test data from a JSON file.
func (l *Loader) Load(category, testSuite string) (*TestData, error) {
	filePath := filepath.Join(l.testdataDir, category, testSuite+".json")

	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("reading test data file %s: %w", filePath, err)
	}

	var testData TestData
	if err := json.Unmarshal(data, &testData); err != nil {
		return nil, fmt.Errorf("parsing test data file %s: %w", filePath, err)
	}

	return &testData, nil
}

// LoadWithFilter loads test data and filters by category.
func (l *Loader) LoadWithFilter(category, testSuite, filterCategory string) (*TestData, error) {
	data, err := l.Load(category, testSuite)
	if err != nil {
		return nil, err
	}

	if filterCategory == "" {
		return data, nil
	}

	// Filter test cases
	var filtered []TestCase
	for _, tc := range data.TestCases {
		if tc.Category == filterCategory {
			filtered = append(filtered, tc)
		}
	}
	data.TestCases = filtered

	return data, nil
}

// GetTestCases returns all non-skipped test cases for Go.
func (l *Loader) GetTestCases(category, testSuite string) ([]TestCase, error) {
	data, err := l.Load(category, testSuite)
	if err != nil {
		return nil, err
	}

	var cases []TestCase
	for _, tc := range data.TestCases {
		if !tc.ShouldSkipGo() {
			cases = append(cases, tc)
		}
	}

	return cases, nil
}
