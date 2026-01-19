// Tests for string matching functionality
#include <gtest/gtest.h>

#include <cmath>
#include <retro_metadata/internal/matching.hpp>

#include "testutil/loader.hpp"

using namespace retro_metadata;
using namespace retro_metadata::testutil;
using namespace retro_metadata::internal;

class MatchingTest : public ::testing::Test {
  protected:
    void SetUp() override { loader_ = std::make_unique<Loader>(Loader::from_compile_definition()); }

    std::unique_ptr<Loader> loader_;
};

// Test jaro_winkler_similarity using shared test data
TEST_F(MatchingTest, JaroWinklerSimilarity) {
    auto test_cases = loader_->get_test_cases("matching", "jaro_winkler_similarity");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto s1 = tc.input_get<std::string>("s1");
        auto s2 = tc.input_get<std::string>("s2");
        auto result = jaro_winkler_similarity(s1, s2);

        // Handle exact expected value
        if (!tc.expected.is_null() && tc.expected.is_number()) {
            auto expected = tc.expected_float();
            EXPECT_NEAR(result, expected, 0.01) << "Test case: " << tc.id << " - " << tc.description;
        }

        // Handle expected_min
        if (tc.expected_min.has_value()) {
            EXPECT_GE(result, *tc.expected_min)
                << "Test case: " << tc.id << " - result " << result
                << " should be >= " << *tc.expected_min;
        }

        // Handle expected_max
        if (tc.expected_max.has_value()) {
            EXPECT_LE(result, *tc.expected_max)
                << "Test case: " << tc.id << " - result " << result
                << " should be <= " << *tc.expected_max;
        }
    }
}

// Test find_best_match using shared test data
TEST_F(MatchingTest, FindBestMatch) {
    auto test_cases = loader_->get_test_cases("matching", "find_best_match");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto query = tc.input_get<std::string>("query");
        auto candidates_json = tc.input.at("candidates");
        std::vector<std::string> candidates;
        for (const auto& c : candidates_json) {
            candidates.push_back(c.get<std::string>());
        }

        auto threshold = tc.input_get<double>("threshold", 0.0);
        auto result = find_best_match(query, candidates, threshold);

        if (tc.is_expected_null()) {
            EXPECT_FALSE(result.has_value())
                << "Test case: " << tc.id << " - expected no match but got " << result->match;
        } else if (tc.expected.is_object()) {
            ASSERT_TRUE(result.has_value()) << "Test case: " << tc.id << " - expected a match";
            auto expected_match = tc.expected.value("match", "");
            auto expected_score = tc.expected.value("score", 0.0);
            auto expected_index = tc.expected.value("index", -1);

            EXPECT_EQ(result->match, expected_match) << "Test case: " << tc.id;
            EXPECT_NEAR(result->score, expected_score, 0.01) << "Test case: " << tc.id;
            if (expected_index >= 0) {
                EXPECT_EQ(result->index, static_cast<size_t>(expected_index))
                    << "Test case: " << tc.id;
            }
        }
    }
}

// Direct unit tests for matching functions
TEST_F(MatchingTest, FindAllMatches) {
    std::vector<std::string> candidates = {"Super Mario World", "Super Mario Bros",
                                           "Super Mario Kart", "Zelda"};

    auto matches = find_all_matches("Super Mario", candidates, 0.5);

    EXPECT_GE(matches.size(), 3u);
    for (const auto& m : matches) {
        EXPECT_GE(m.score, 0.5);
    }
}

TEST_F(MatchingTest, IsExactMatch) {
    EXPECT_TRUE(is_exact_match("test", "test"));
    EXPECT_TRUE(is_exact_match("TEST", "test"));
    EXPECT_TRUE(is_exact_match("Test", "TEST"));
    EXPECT_FALSE(is_exact_match("test", "testing"));
    EXPECT_FALSE(is_exact_match("abc", "xyz"));
}

TEST_F(MatchingTest, MatchConfidenceHigh) {
    auto confidence = match_confidence("Super Mario World", "Super Mario World");
    EXPECT_EQ(confidence, MatchConfidence::High);
}

TEST_F(MatchingTest, MatchConfidenceMedium) {
    auto confidence = match_confidence("Super Mario World", "Super Mario World 2");
    EXPECT_EQ(confidence, MatchConfidence::Medium);
}

TEST_F(MatchingTest, MatchConfidenceLow) {
    auto confidence = match_confidence("Super Mario World", "Zelda");
    EXPECT_EQ(confidence, MatchConfidence::Low);
}

TEST_F(MatchingTest, EmptyStrings) {
    EXPECT_EQ(jaro_winkler_similarity("", ""), 1.0);
    EXPECT_EQ(jaro_winkler_similarity("", "test"), 0.0);
    EXPECT_EQ(jaro_winkler_similarity("test", ""), 0.0);
}

TEST_F(MatchingTest, CaseInsensitive) {
    auto score1 = jaro_winkler_similarity("MARIO", "mario");
    auto score2 = jaro_winkler_similarity("mario", "MARIO");
    EXPECT_NEAR(score1, 1.0, 0.01);
    EXPECT_NEAR(score2, 1.0, 0.01);
}
