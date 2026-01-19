// Tests for text normalization functionality
#include <gtest/gtest.h>

#include <retro_metadata/internal/normalization.hpp>

#include "testutil/loader.hpp"

using namespace retro_metadata;
using namespace retro_metadata::testutil;
using namespace retro_metadata::internal;

class NormalizationTest : public ::testing::Test {
  protected:
    void SetUp() override { loader_ = std::make_unique<Loader>(Loader::from_compile_definition()); }

    std::unique_ptr<Loader> loader_;
};

// Test normalize_search_term using shared test data
TEST_F(NormalizationTest, NormalizeSearchTerm) {
    auto test_cases = loader_->get_test_cases("normalization", "normalize_search_term");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_string();
        auto result = normalize_search_term(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description
                                    << " (input: \"" << input << "\")";
    }
}

// Test split_search_term using shared test data
TEST_F(NormalizationTest, SplitSearchTerm) {
    auto test_cases = loader_->get_test_cases("normalization", "split_search_term");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_string_slice();
        auto result = split_search_term(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description;
    }
}

// Direct unit tests for normalization functions
TEST_F(NormalizationTest, NormalizeCoverUrl) {
    // Test IGDB URL conversion
    auto result = normalize_cover_url("//images.igdb.com/igdb/image/upload/t_thumb/co1234.jpg");
    EXPECT_EQ(result, "https://images.igdb.com/igdb/image/upload/t_cover_big/co1234.jpg");

    // Test already absolute URL
    result = normalize_cover_url("https://example.com/image.jpg");
    EXPECT_EQ(result, "https://example.com/image.jpg");

    // Test empty URL
    result = normalize_cover_url("");
    EXPECT_EQ(result, "");
}

TEST_F(NormalizationTest, RemoveAccents) {
    // Basic accent removal
    auto result = remove_accents("café");
    EXPECT_EQ(result, "cafe");

    result = remove_accents("résumé");
    EXPECT_EQ(result, "resume");

    // No accents
    result = remove_accents("hello");
    EXPECT_EQ(result, "hello");

    // Empty string
    result = remove_accents("");
    EXPECT_EQ(result, "");
}

TEST_F(NormalizationTest, StripSensitiveQueryParams) {
    // Strip API key
    auto result = strip_sensitive_query_params("https://example.com?api_key=secret&name=test");
    EXPECT_FALSE(result.find("secret") != std::string::npos);
    EXPECT_TRUE(result.find("name=test") != std::string::npos);

    // Strip key parameter
    result = strip_sensitive_query_params("https://example.com?key=password");
    EXPECT_FALSE(result.find("password") != std::string::npos);

    // No sensitive params
    result = strip_sensitive_query_params("https://example.com?foo=bar");
    EXPECT_EQ(result, "https://example.com?foo=bar");

    // Empty string
    result = strip_sensitive_query_params("");
    EXPECT_EQ(result, "");
}

TEST_F(NormalizationTest, NormalizeSearchTermEdgeCases) {
    // Multiple spaces
    auto result = normalize_search_term("Super    Mario    World");
    EXPECT_EQ(result, "super mario world");

    // Leading/trailing whitespace
    result = normalize_search_term("  test  ");
    EXPECT_EQ(result, "test");

    // Mixed case
    result = normalize_search_term("SUPER Mario WoRlD");
    EXPECT_EQ(result, "super mario world");

    // Empty string
    result = normalize_search_term("");
    EXPECT_EQ(result, "");

    // Only whitespace
    result = normalize_search_term("   ");
    EXPECT_EQ(result, "");
}

TEST_F(NormalizationTest, SplitSearchTermEdgeCases) {
    // Single word
    auto result = split_search_term("mario");
    EXPECT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0], "mario");

    // Multiple words
    result = split_search_term("super mario world");
    EXPECT_EQ(result.size(), 3u);

    // Empty string
    result = split_search_term("");
    EXPECT_TRUE(result.empty());

    // Only whitespace
    result = split_search_term("   ");
    EXPECT_TRUE(result.empty());
}
