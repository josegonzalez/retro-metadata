package platform

import (
	"testing"

	"github.com/josegonzalez/retro-metadata/pkg/testutil"
)

func TestGetIGDBPlatformID(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("platform", "get_igdb_platform_id")
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

			result := GetIGDBPlatformID(Slug(input))

			if tc.IsExpectedNull() {
				if result != nil {
					t.Errorf("GetIGDBPlatformID(%q) = %d, want nil", input, *result)
				}
			} else {
				expected, ok := tc.ExpectedInt()
				if !ok {
					t.Skipf("Expected is not an int")
					return
				}
				if result == nil {
					t.Errorf("GetIGDBPlatformID(%q) = nil, want %d", input, expected)
				} else if *result != expected {
					t.Errorf("GetIGDBPlatformID(%q) = %d, want %d", input, *result, expected)
				}
			}
		})
	}
}

func TestGetMobyGamesPlatformID(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("platform", "get_mobygames_platform_id")
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

			result := GetMobyGamesPlatformID(Slug(input))

			if tc.IsExpectedNull() {
				if result != nil {
					t.Errorf("GetMobyGamesPlatformID(%q) = %d, want nil", input, *result)
				}
			} else {
				expected, ok := tc.ExpectedInt()
				if !ok {
					t.Skipf("Expected is not an int")
					return
				}
				if result == nil {
					t.Errorf("GetMobyGamesPlatformID(%q) = nil, want %d", input, expected)
				} else if *result != expected {
					t.Errorf("GetMobyGamesPlatformID(%q) = %d, want %d", input, *result, expected)
				}
			}
		})
	}
}

func TestGetScreenScraperPlatformID(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("platform", "get_screenscraper_platform_id")
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

			result := GetScreenScraperPlatformID(Slug(input))

			if tc.IsExpectedNull() {
				if result != nil {
					t.Errorf("GetScreenScraperPlatformID(%q) = %d, want nil", input, *result)
				}
			} else {
				expected, ok := tc.ExpectedInt()
				if !ok {
					t.Skipf("Expected is not an int")
					return
				}
				if result == nil {
					t.Errorf("GetScreenScraperPlatformID(%q) = nil, want %d", input, expected)
				} else if *result != expected {
					t.Errorf("GetScreenScraperPlatformID(%q) = %d, want %d", input, *result, expected)
				}
			}
		})
	}
}

func TestGetRetroAchievementsPlatformID(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("platform", "get_retroachievements_platform_id")
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

			result := GetRetroAchievementsPlatformID(Slug(input))

			if tc.IsExpectedNull() {
				if result != nil {
					t.Errorf("GetRetroAchievementsPlatformID(%q) = %d, want nil", input, *result)
				}
			} else {
				expected, ok := tc.ExpectedInt()
				if !ok {
					t.Skipf("Expected is not an int")
					return
				}
				if result == nil {
					t.Errorf("GetRetroAchievementsPlatformID(%q) = nil, want %d", input, expected)
				} else if *result != expected {
					t.Errorf("GetRetroAchievementsPlatformID(%q) = %d, want %d", input, *result, expected)
				}
			}
		})
	}
}

func TestGetPlatformInfo(t *testing.T) {
	loader, err := testutil.NewLoaderFromRepo()
	if err != nil {
		t.Fatalf("Failed to load test data: %v", err)
	}

	testCases, err := loader.GetTestCases("platform", "get_platform_info")
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

			result := GetPlatformInfo(Slug(input))

			if tc.IsExpectedNull() {
				if result != nil {
					t.Errorf("GetPlatformInfo(%q) = %+v, want nil", input, result)
				}
			} else {
				expected, ok := tc.ExpectedMap()
				if !ok {
					t.Skipf("Expected is not a map")
					return
				}
				if result == nil {
					t.Errorf("GetPlatformInfo(%q) = nil, want non-nil", input)
					return
				}

				// Check slug
				expectedSlug, _ := expected["slug"].(string)
				if string(result.Slug) != expectedSlug {
					t.Errorf("GetPlatformInfo(%q).Slug = %q, want %q", input, result.Slug, expectedSlug)
				}

				// Check IGDB ID
				if expectedIGDB, ok := expected["igdb_id"]; ok && expectedIGDB != nil {
					if id, ok := expectedIGDB.(float64); ok {
						expectedID := int(id)
						if result.IGDBID == nil {
							t.Errorf("GetPlatformInfo(%q).IGDBID = nil, want %d", input, expectedID)
						} else if *result.IGDBID != expectedID {
							t.Errorf("GetPlatformInfo(%q).IGDBID = %d, want %d", input, *result.IGDBID, expectedID)
						}
					}
				} else {
					if result.IGDBID != nil {
						t.Errorf("GetPlatformInfo(%q).IGDBID = %d, want nil", input, *result.IGDBID)
					}
				}

				// Check MobyGames ID
				if expectedMoby, ok := expected["mobygames_id"]; ok && expectedMoby != nil {
					if id, ok := expectedMoby.(float64); ok {
						expectedID := int(id)
						if result.MobyGamesID == nil {
							t.Errorf("GetPlatformInfo(%q).MobyGamesID = nil, want %d", input, expectedID)
						} else if *result.MobyGamesID != expectedID {
							t.Errorf("GetPlatformInfo(%q).MobyGamesID = %d, want %d", input, *result.MobyGamesID, expectedID)
						}
					}
				} else {
					if result.MobyGamesID != nil {
						t.Errorf("GetPlatformInfo(%q).MobyGamesID = %d, want nil", input, *result.MobyGamesID)
					}
				}

				// Check ScreenScraper ID
				if expectedSS, ok := expected["screenscraper_id"]; ok && expectedSS != nil {
					if id, ok := expectedSS.(float64); ok {
						expectedID := int(id)
						if result.ScreenScraperID == nil {
							t.Errorf("GetPlatformInfo(%q).ScreenScraperID = nil, want %d", input, expectedID)
						} else if *result.ScreenScraperID != expectedID {
							t.Errorf("GetPlatformInfo(%q).ScreenScraperID = %d, want %d", input, *result.ScreenScraperID, expectedID)
						}
					}
				} else {
					if result.ScreenScraperID != nil {
						t.Errorf("GetPlatformInfo(%q).ScreenScraperID = %d, want nil", input, *result.ScreenScraperID)
					}
				}

				// Check RetroAchievements ID
				if expectedRA, ok := expected["retroachievements_id"]; ok && expectedRA != nil {
					if id, ok := expectedRA.(float64); ok {
						expectedID := int(id)
						if result.RetroAchievementsID == nil {
							t.Errorf("GetPlatformInfo(%q).RetroAchievementsID = nil, want %d", input, expectedID)
						} else if *result.RetroAchievementsID != expectedID {
							t.Errorf("GetPlatformInfo(%q).RetroAchievementsID = %d, want %d", input, *result.RetroAchievementsID, expectedID)
						}
					}
				} else {
					if result.RetroAchievementsID != nil {
						t.Errorf("GetPlatformInfo(%q).RetroAchievementsID = %d, want nil", input, *result.RetroAchievementsID)
					}
				}
			}
		})
	}
}
