// Tests for platform slug and mapping functionality
#include <gtest/gtest.h>

#include <retro_metadata/platform/mapping.hpp>
#include <retro_metadata/platform/slug.hpp>

#include "testutil/loader.hpp"

using namespace retro_metadata;
using namespace retro_metadata::testutil;
using namespace retro_metadata::platform;

class PlatformTest : public ::testing::Test {
  protected:
    void SetUp() override { loader_ = std::make_unique<Loader>(Loader::from_compile_definition()); }

    std::unique_ptr<Loader> loader_;
};

// Test get_igdb_platform_id using shared test data
TEST_F(PlatformTest, GetIGDBPlatformId) {
    auto test_cases = loader_->get_test_cases("platform", "get_igdb_platform_id");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto slug = tc.input_string();
        auto expected = tc.expected_int();
        auto result = get_igdb_platform_id(slug);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " (slug: " << slug << ")";
    }
}

// Test get_mobygames_platform_id using shared test data
TEST_F(PlatformTest, GetMobygamesPlatformId) {
    auto test_cases = loader_->get_test_cases("platform", "get_mobygames_platform_id");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto slug = tc.input_string();
        auto expected = tc.expected_int();
        auto result = get_mobygames_platform_id(slug);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " (slug: " << slug << ")";
    }
}

// Test get_screenscraper_platform_id using shared test data
TEST_F(PlatformTest, GetScreenscraperPlatformId) {
    auto test_cases = loader_->get_test_cases("platform", "get_screenscraper_platform_id");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto slug = tc.input_string();
        auto expected = tc.expected_int();
        auto result = get_screenscraper_platform_id(slug);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " (slug: " << slug << ")";
    }
}

// Test get_retroachievements_platform_id using shared test data
TEST_F(PlatformTest, GetRetroAchievementsPlatformId) {
    auto test_cases = loader_->get_test_cases("platform", "get_retroachievements_platform_id");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto slug = tc.input_string();
        auto expected = tc.expected_int();
        auto result = get_retroachievements_platform_id(slug);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " (slug: " << slug << ")";
    }
}

// Test get_platform_info using shared test data
TEST_F(PlatformTest, GetPlatformInfo) {
    auto test_cases = loader_->get_test_cases("platform", "get_platform_info");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto slug = tc.input_string();
        auto info = get_platform_info(slug);

        if (tc.is_expected_null()) {
            EXPECT_FALSE(info.has_value()) << "Test case: " << tc.id << " - expected no platform info";
        } else if (tc.expected.is_object()) {
            ASSERT_TRUE(info.has_value()) << "Test case: " << tc.id << " - expected platform info";

            if (tc.expected.contains("name")) {
                EXPECT_EQ(info->name, tc.expected["name"].get<std::string>())
                    << "Test case: " << tc.id;
            }
            if (tc.expected.contains("slug")) {
                EXPECT_EQ(info->slug, tc.expected["slug"].get<std::string>())
                    << "Test case: " << tc.id;
            }
            if (tc.expected.contains("igdb_id")) {
                EXPECT_EQ(info->igdb_id, tc.expected["igdb_id"].get<int>())
                    << "Test case: " << tc.id;
            }
            if (tc.expected.contains("mobygames_id")) {
                EXPECT_EQ(info->mobygames_id, tc.expected["mobygames_id"].get<int>())
                    << "Test case: " << tc.id;
            }
        }
    }
}

// Direct unit tests for slug functions
TEST_F(PlatformTest, SlugToString) {
    EXPECT_EQ(to_string(kSNES), "snes");
    EXPECT_EQ(to_string(kNES), "nes");
    EXPECT_EQ(to_string(kGenesisSlash), "genesis");
    EXPECT_EQ(to_string(kPS2), "ps2");
    EXPECT_EQ(to_string(kN64), "n64");
}

TEST_F(PlatformTest, SlugFromString) {
    EXPECT_EQ(from_string("snes"), kSNES);
    EXPECT_EQ(from_string("nes"), kNES);
    EXPECT_EQ(from_string("genesis"), kGenesisSlash);
    EXPECT_EQ(from_string("ps2"), kPS2);
    EXPECT_EQ(from_string("n64"), kN64);
    EXPECT_EQ(from_string("unknown_platform"), "unknown_platform");
}

TEST_F(PlatformTest, SlugName) {
    EXPECT_EQ(slug_name(kSNES), "Super Nintendo Entertainment System");
    EXPECT_EQ(slug_name(kNES), "Nintendo Entertainment System");
    EXPECT_EQ(slug_name(kPS2), "PlayStation 2");
}

TEST_F(PlatformTest, CommonPlatformMappings) {
    // Test common platforms have IDs for major providers
    EXPECT_GT(get_igdb_platform_id(kSNES), 0);
    EXPECT_GT(get_mobygames_platform_id(kSNES), 0);
    EXPECT_GT(get_screenscraper_platform_id(kSNES), 0);

    EXPECT_GT(get_igdb_platform_id(kNES), 0);
    EXPECT_GT(get_mobygames_platform_id(kNES), 0);

    EXPECT_GT(get_igdb_platform_id(kPS2), 0);
    EXPECT_GT(get_mobygames_platform_id(kPS2), 0);
}

TEST_F(PlatformTest, UnknownPlatformReturnsZero) {
    EXPECT_EQ(get_igdb_platform_id("nonexistent_platform"), 0);
    EXPECT_EQ(get_mobygames_platform_id("unknown_slug"), 0);
    EXPECT_EQ(get_screenscraper_platform_id("fake_platform"), 0);
    EXPECT_EQ(get_retroachievements_platform_id("invalid"), 0);
}

TEST_F(PlatformTest, SlugFromProviderIds) {
    // Test reverse lookup from provider IDs
    auto slug = slug_from_igdb_id(19);  // SNES
    EXPECT_TRUE(slug.has_value());
    if (slug.has_value()) {
        EXPECT_EQ(*slug, kSNES);
    }

    slug = slug_from_mobygames_id(15);  // SNES
    EXPECT_TRUE(slug.has_value());

    // Unknown ID
    slug = slug_from_igdb_id(99999);
    EXPECT_FALSE(slug.has_value());
}
