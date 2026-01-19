// Tests for provider infrastructure and basic functionality
#include <gtest/gtest.h>

#include <retro_metadata/cache/memory.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>
#include <retro_metadata/types.hpp>

using namespace retro_metadata;

class ProviderTest : public ::testing::Test {
  protected:
    void SetUp() override {
        // Create a basic provider config
        config_.enabled = true;
        config_.timeout = std::chrono::seconds(30);
    }

    ProviderConfig config_;
};

// Test provider registry
TEST_F(ProviderTest, RegistryHasProviders) {
    auto& registry = Registry::instance();
    auto names = registry.provider_names();

    // Should have at least the basic providers registered
    EXPECT_FALSE(names.empty());

    // Check for known providers
    bool has_igdb = false;
    bool has_hltb = false;
    for (const auto& name : names) {
        if (name == "igdb") has_igdb = true;
        if (name == "hltb") has_hltb = true;
    }
    EXPECT_TRUE(has_igdb) << "IGDB provider should be registered";
    EXPECT_TRUE(has_hltb) << "HLTB provider should be registered";
}

TEST_F(ProviderTest, RegistryCreateProvider) {
    auto& registry = Registry::instance();

    // Try to create HLTB provider (doesn't require credentials)
    auto provider = registry.create("hltb", config_, nullptr);
    ASSERT_NE(provider, nullptr);
    EXPECT_EQ(provider->name(), "hltb");
}

TEST_F(ProviderTest, RegistryCreateWithCache) {
    auto& registry = Registry::instance();

    // Create a memory cache
    auto cache = std::make_shared<cache::MemoryCache>(100, std::chrono::minutes(5));

    auto provider = registry.create("hltb", config_, cache);
    ASSERT_NE(provider, nullptr);
    EXPECT_EQ(provider->name(), "hltb");
}

TEST_F(ProviderTest, RegistryCreateUnknownProvider) {
    auto& registry = Registry::instance();

    auto provider = registry.create("nonexistent_provider", config_, nullptr);
    EXPECT_EQ(provider, nullptr);
}

TEST_F(ProviderTest, ProviderDisabled) {
    auto& registry = Registry::instance();

    ProviderConfig disabled_config;
    disabled_config.enabled = false;

    auto provider = registry.create("hltb", disabled_config, nullptr);
    ASSERT_NE(provider, nullptr);

    // Search on disabled provider should return empty
    SearchOptions opts;
    auto results = provider->search("test", opts);
    EXPECT_TRUE(results.empty());
}

// Test SearchOptions
TEST_F(ProviderTest, SearchOptionsDefaults) {
    SearchOptions opts;
    EXPECT_EQ(opts.limit, 0);  // 0 means use provider default
    EXPECT_FALSE(opts.platform_id.has_value());
}

TEST_F(ProviderTest, SearchOptionsWithPlatform) {
    SearchOptions opts;
    opts.platform_id = 19;  // SNES
    opts.limit = 10;

    EXPECT_TRUE(opts.platform_id.has_value());
    EXPECT_EQ(*opts.platform_id, 19);
    EXPECT_EQ(opts.limit, 10);
}

// Test IdentifyOptions
TEST_F(ProviderTest, IdentifyOptionsDefaults) {
    IdentifyOptions opts;
    EXPECT_FALSE(opts.platform_id.has_value());
}

TEST_F(ProviderTest, IdentifyOptionsWithPlatform) {
    IdentifyOptions opts;
    opts.platform_id = 19;

    EXPECT_TRUE(opts.platform_id.has_value());
    EXPECT_EQ(*opts.platform_id, 19);
}

// Test FileHashes
TEST_F(ProviderTest, FileHashesEmpty) {
    FileHashes hashes;
    EXPECT_TRUE(hashes.md5.empty());
    EXPECT_TRUE(hashes.sha1.empty());
    EXPECT_TRUE(hashes.sha256.empty());
    EXPECT_TRUE(hashes.crc32.empty());
}

TEST_F(ProviderTest, FileHashesWithValues) {
    FileHashes hashes;
    hashes.md5 = "d41d8cd98f00b204e9800998ecf8427e";
    hashes.sha1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709";
    hashes.crc32 = "00000000";

    EXPECT_EQ(hashes.md5, "d41d8cd98f00b204e9800998ecf8427e");
    EXPECT_EQ(hashes.sha1, "da39a3ee5e6b4b0d3255bfef95601890afd80709");
    EXPECT_EQ(hashes.crc32, "00000000");
}

// Test ProviderConfig
TEST_F(ProviderTest, ProviderConfigCredentials) {
    ProviderConfig config;
    config.credentials["api_key"] = "test_key";
    config.credentials["client_id"] = "test_client";

    EXPECT_EQ(config.credentials.at("api_key"), "test_key");
    EXPECT_EQ(config.credentials.at("client_id"), "test_client");
}

TEST_F(ProviderTest, ProviderConfigTimeout) {
    ProviderConfig config;
    config.timeout = std::chrono::seconds(60);

    EXPECT_EQ(config.timeout, std::chrono::seconds(60));
}

// Test SearchResult structure
TEST_F(ProviderTest, SearchResultConstruction) {
    SearchResult result;
    result.name = "Super Mario World";
    result.provider = "igdb";
    result.provider_id = 1234;
    result.cover_url = "https://example.com/cover.jpg";
    result.release_year = 1990;

    EXPECT_EQ(result.name, "Super Mario World");
    EXPECT_EQ(result.provider, "igdb");
    EXPECT_EQ(result.provider_id, 1234);
    EXPECT_EQ(result.cover_url, "https://example.com/cover.jpg");
    EXPECT_TRUE(result.release_year.has_value());
    EXPECT_EQ(*result.release_year, 1990);
}

// Test GameResult structure
TEST_F(ProviderTest, GameResultConstruction) {
    GameResult result;
    result.name = "The Legend of Zelda";
    result.provider = "igdb";
    result.summary = "A classic adventure game";
    result.match_score = 0.95;

    EXPECT_EQ(result.name, "The Legend of Zelda");
    EXPECT_EQ(result.provider, "igdb");
    EXPECT_EQ(result.summary, "A classic adventure game");
    EXPECT_NEAR(result.match_score, 0.95, 0.001);
}

// Test Artwork structure
TEST_F(ProviderTest, ArtworkConstruction) {
    Artwork artwork;
    artwork.cover_url = "https://example.com/cover.jpg";
    artwork.background_url = "https://example.com/bg.jpg";
    artwork.screenshot_urls = {"https://example.com/ss1.jpg", "https://example.com/ss2.jpg"};

    EXPECT_EQ(artwork.cover_url, "https://example.com/cover.jpg");
    EXPECT_EQ(artwork.background_url, "https://example.com/bg.jpg");
    EXPECT_EQ(artwork.screenshot_urls.size(), 2u);
}

// Test GameMetadata structure
TEST_F(ProviderTest, GameMetadataConstruction) {
    GameMetadata metadata;
    metadata.genres = {"Action", "Adventure"};
    metadata.companies = {"Nintendo"};
    metadata.developer = "Nintendo EAD";
    metadata.publisher = "Nintendo";
    metadata.release_year = 1991;

    EXPECT_EQ(metadata.genres.size(), 2u);
    EXPECT_EQ(metadata.companies.size(), 1u);
    EXPECT_EQ(metadata.developer, "Nintendo EAD");
    EXPECT_EQ(metadata.publisher, "Nintendo");
    EXPECT_TRUE(metadata.release_year.has_value());
    EXPECT_EQ(*metadata.release_year, 1991);
}

// Test Platform structure
TEST_F(ProviderTest, PlatformConstruction) {
    Platform platform;
    platform.name = "Super Nintendo";
    platform.slug = "snes";
    platform.provider_ids["igdb"] = 19;
    platform.provider_ids["mobygames"] = 15;

    EXPECT_EQ(platform.name, "Super Nintendo");
    EXPECT_EQ(platform.slug, "snes");
    EXPECT_EQ(platform.provider_ids.at("igdb"), 19);
    EXPECT_EQ(platform.provider_ids.at("mobygames"), 15);
}

// Test provider names registration
TEST_F(ProviderTest, AllExpectedProvidersRegistered) {
    auto& registry = Registry::instance();
    auto names = registry.provider_names();

    std::vector<std::string> expected_providers = {
        "hltb",
        "igdb",
        "mobygames",
        "screenscraper",
        "retroachievements",
        "steamgriddb",
        "thegamesdb",
        "launchbox",
        "hasheous",
        "flashpoint",
        "playmatch",
        "gamelist"
    };

    for (const auto& expected : expected_providers) {
        bool found = false;
        for (const auto& name : names) {
            if (name == expected) {
                found = true;
                break;
            }
        }
        EXPECT_TRUE(found) << "Provider '" << expected << "' should be registered";
    }
}

// Test creating each provider
TEST_F(ProviderTest, CreateAllProviders) {
    auto& registry = Registry::instance();
    auto names = registry.provider_names();

    for (const auto& name : names) {
        auto provider = registry.create(name, config_, nullptr);
        ASSERT_NE(provider, nullptr) << "Failed to create provider: " << name;
        EXPECT_EQ(provider->name(), name) << "Provider name mismatch for: " << name;
    }
}
