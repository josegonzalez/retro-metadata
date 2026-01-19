package provider_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/josegonzalez/retro-metadata/pkg/provider/igdb"
	"github.com/josegonzalez/retro-metadata/pkg/provider/mobygames"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// findTestdataDir searches for the testdata directory by walking up from the current directory.
func findTestdataDir() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}

	for {
		testdataPath := filepath.Join(dir, "testdata")
		if info, err := os.Stat(testdataPath); err == nil && info.IsDir() {
			return testdataPath, nil
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}

	return "", nil
}

// loadFixture loads a fixture file from testdata/fixtures.
func loadFixture(t *testing.T, provider, filename string) []byte {
	testdataDir, err := findTestdataDir()
	if err != nil || testdataDir == "" {
		t.Skipf("Skipping test: testdata directory not found")
	}

	path := filepath.Join(testdataDir, "fixtures", provider, filename)
	data, err := os.ReadFile(path)
	if err != nil {
		t.Skipf("Skipping test: fixture %s not found", path)
	}

	return data
}

func TestIGDBSearchIntegration(t *testing.T) {
	searchResponse := loadFixture(t, "igdb", "search_mario.json")

	// Create mock server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Handle OAuth token request
		if strings.Contains(r.URL.Path, "oauth2/token") {
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{
				"access_token": "test_token",
				"expires_in":   3600,
				"token_type":   "bearer",
			})
			return
		}

		// Handle games search
		if strings.Contains(r.URL.Path, "/games") {
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write(searchResponse)
			return
		}

		http.NotFound(w, r)
	}))
	defer server.Close()

	// Create IGDB provider with mock server
	config := retrometadata.ProviderConfig{
		Enabled: true,
		Credentials: map[string]string{
			"client_id":     "test_client_id",
			"client_secret": "test_client_secret",
		},
		Timeout: 30,
	}

	provider, err := igdb.NewProviderWithOptions(config, nil, igdb.Options{
		BaseURL:  server.URL + "/v4",
		TokenURL: server.URL + "/oauth2/token",
	})
	if err != nil {
		t.Fatalf("Failed to create provider: %v", err)
	}

	ctx := context.Background()

	results, err := provider.Search(ctx, "Super Mario", retrometadata.SearchOptions{Limit: 10})
	if err != nil {
		t.Fatalf("Search error: %v", err)
	}

	if len(results) == 0 {
		t.Fatal("Expected results, got none")
	}

	// Verify first result
	if results[0].Name != "Super Mario World" {
		t.Errorf("Expected first result to be 'Super Mario World', got %q", results[0].Name)
	}

	if results[0].Provider != "igdb" {
		t.Errorf("Expected provider 'igdb', got %q", results[0].Provider)
	}

	if results[0].ProviderID != 1074 {
		t.Errorf("Expected ProviderID 1074, got %d", results[0].ProviderID)
	}
}

func TestIGDBGetByIDIntegration(t *testing.T) {
	gameResponse := loadFixture(t, "igdb", "game_1074.json")

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.Contains(r.URL.Path, "oauth2/token") {
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{
				"access_token": "test_token",
				"expires_in":   3600,
				"token_type":   "bearer",
			})
			return
		}

		if strings.Contains(r.URL.Path, "/games") {
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write(gameResponse)
			return
		}

		http.NotFound(w, r)
	}))
	defer server.Close()

	config := retrometadata.ProviderConfig{
		Enabled: true,
		Credentials: map[string]string{
			"client_id":     "test_client_id",
			"client_secret": "test_client_secret",
		},
		Timeout: 30,
	}

	provider, err := igdb.NewProviderWithOptions(config, nil, igdb.Options{
		BaseURL:  server.URL + "/v4",
		TokenURL: server.URL + "/oauth2/token",
	})
	if err != nil {
		t.Fatalf("Failed to create provider: %v", err)
	}

	ctx := context.Background()

	result, err := provider.GetByID(ctx, 1074)
	if err != nil {
		t.Fatalf("GetByID error: %v", err)
	}

	if result == nil {
		t.Fatal("Expected result, got nil")
	}

	// Verify game details
	if result.Name != "Super Mario World" {
		t.Errorf("Expected name 'Super Mario World', got %q", result.Name)
	}

	if result.Summary == "" {
		t.Error("Expected summary, got empty string")
	}

	// Verify metadata
	if len(result.Metadata.Genres) == 0 {
		t.Error("Expected genres, got none")
	}

	if len(result.Metadata.Companies) == 0 {
		t.Error("Expected companies, got none")
	}

	// Verify artwork
	if result.Artwork.CoverURL == "" {
		t.Error("Expected cover URL, got empty string")
	}

	if len(result.Artwork.ScreenshotURLs) == 0 {
		t.Error("Expected screenshots, got none")
	}
}

func TestMobyGamesSearchIntegration(t *testing.T) {
	searchResponse := loadFixture(t, "mobygames", "search_zelda.json")

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.Contains(r.URL.Path, "/games") {
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write(searchResponse)
			return
		}

		http.NotFound(w, r)
	}))
	defer server.Close()

	config := retrometadata.ProviderConfig{
		Enabled: true,
		Credentials: map[string]string{
			"api_key": "test_api_key",
		},
		Timeout: 30,
	}

	provider, err := mobygames.NewProviderWithOptions(config, nil, mobygames.Options{
		BaseURL: server.URL,
	})
	if err != nil {
		t.Fatalf("Failed to create provider: %v", err)
	}

	ctx := context.Background()

	results, err := provider.Search(ctx, "Legend of Zelda", retrometadata.SearchOptions{Limit: 10})
	if err != nil {
		t.Fatalf("Search error: %v", err)
	}

	if len(results) == 0 {
		t.Fatal("Expected results, got none")
	}

	// Verify first result
	if results[0].Name != "The Legend of Zelda: A Link to the Past" {
		t.Errorf("Expected first result to be 'The Legend of Zelda: A Link to the Past', got %q", results[0].Name)
	}

	if results[0].Provider != "mobygames" {
		t.Errorf("Expected provider 'mobygames', got %q", results[0].Provider)
	}

	if results[0].ProviderID != 564 {
		t.Errorf("Expected ProviderID 564, got %d", results[0].ProviderID)
	}
}

func TestMobyGamesGetByIDIntegration(t *testing.T) {
	gameResponse := loadFixture(t, "mobygames", "game_564.json")

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.Contains(r.URL.Path, "/games/564") {
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write(gameResponse)
			return
		}

		http.NotFound(w, r)
	}))
	defer server.Close()

	config := retrometadata.ProviderConfig{
		Enabled: true,
		Credentials: map[string]string{
			"api_key": "test_api_key",
		},
		Timeout: 30,
	}

	provider, err := mobygames.NewProviderWithOptions(config, nil, mobygames.Options{
		BaseURL: server.URL,
	})
	if err != nil {
		t.Fatalf("Failed to create provider: %v", err)
	}

	ctx := context.Background()

	result, err := provider.GetByID(ctx, 564)
	if err != nil {
		t.Fatalf("GetByID error: %v", err)
	}

	if result == nil {
		t.Fatal("Expected result, got nil")
	}

	// Verify game details
	if result.Name != "The Legend of Zelda: A Link to the Past" {
		t.Errorf("Expected name 'The Legend of Zelda: A Link to the Past', got %q", result.Name)
	}

	// Verify metadata
	if len(result.Metadata.Genres) == 0 {
		t.Error("Expected genres, got none")
	}

	// Verify artwork
	if result.Artwork.CoverURL == "" {
		t.Error("Expected cover URL, got empty string")
	}
}

// TestProviderErrorHandling tests that providers handle errors correctly.
func TestProviderErrorHandling(t *testing.T) {
	// Server that always returns 500
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// For IGDB, we need to handle token request first
		if strings.Contains(r.URL.Path, "oauth2/token") {
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{
				"access_token": "test_token",
				"expires_in":   3600,
				"token_type":   "bearer",
			})
			return
		}
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
	}))
	defer server.Close()

	t.Run("IGDB_500_Error", func(t *testing.T) {
		config := retrometadata.ProviderConfig{
			Enabled: true,
			Credentials: map[string]string{
				"client_id":     "test_client_id",
				"client_secret": "test_client_secret",
			},
			Timeout: 30,
		}

		provider, err := igdb.NewProviderWithOptions(config, nil, igdb.Options{
			BaseURL:  server.URL + "/v4",
			TokenURL: server.URL + "/oauth2/token",
		})
		if err != nil {
			t.Fatalf("Failed to create provider: %v", err)
		}

		ctx := context.Background()
		_, err = provider.Search(ctx, "Test", retrometadata.SearchOptions{})

		if err == nil {
			t.Error("Expected error, got nil")
		}
	})

	t.Run("MobyGames_500_Error", func(t *testing.T) {
		config := retrometadata.ProviderConfig{
			Enabled: true,
			Credentials: map[string]string{
				"api_key": "test_api_key",
			},
			Timeout: 30,
		}

		provider, err := mobygames.NewProviderWithOptions(config, nil, mobygames.Options{
			BaseURL: server.URL,
		})
		if err != nil {
			t.Fatalf("Failed to create provider: %v", err)
		}

		ctx := context.Background()
		_, err = provider.Search(ctx, "Test", retrometadata.SearchOptions{})

		if err == nil {
			t.Error("Expected error, got nil")
		}
	})
}

// TestDisabledProvider tests that disabled providers return nil without error.
func TestDisabledProvider(t *testing.T) {
	config := retrometadata.ProviderConfig{
		Enabled: false,
		Credentials: map[string]string{
			"api_key": "test_api_key",
		},
		Timeout: 30,
	}

	provider, err := mobygames.NewProvider(config, nil)
	if err != nil {
		t.Fatalf("Failed to create provider: %v", err)
	}

	ctx := context.Background()
	results, err := provider.Search(ctx, "Test", retrometadata.SearchOptions{})

	if err != nil {
		t.Errorf("Expected no error for disabled provider, got %v", err)
	}

	if results != nil {
		t.Error("Expected nil results for disabled provider")
	}
}
