// Tests for filename parsing functionality
#include <gtest/gtest.h>

#include <retro_metadata/filename/filename.hpp>

#include "testutil/loader.hpp"

using namespace retro_metadata;
using namespace retro_metadata::testutil;
using namespace retro_metadata::filename;

class FilenameTest : public ::testing::Test {
  protected:
    void SetUp() override { loader_ = std::make_unique<Loader>(Loader::from_compile_definition()); }

    std::unique_ptr<Loader> loader_;
};

// Test get_file_extension using shared test data
TEST_F(FilenameTest, GetFileExtension) {
    auto test_cases = loader_->get_test_cases("filename", "get_file_extension");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_string();
        auto result = get_file_extension(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description;
    }
}

// Test extract_tags using shared test data
TEST_F(FilenameTest, ExtractTags) {
    auto test_cases = loader_->get_test_cases("filename", "extract_tags");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_string_slice();
        auto result = extract_tags(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description;
    }
}

// Test extract_region using shared test data
TEST_F(FilenameTest, ExtractRegion) {
    auto test_cases = loader_->get_test_cases("filename", "extract_region");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_string();
        auto result = extract_region(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description;
    }
}

// Test clean_filename using shared test data
TEST_F(FilenameTest, CleanFilename) {
    auto test_cases = loader_->get_test_cases("filename", "clean_filename");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto filename = tc.input_get<std::string>("filename");
        auto remove_ext = tc.input_get<bool>("remove_extension", true);
        auto expected = tc.expected_string();
        auto result = clean_filename(filename, remove_ext);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description;
    }
}

// Test parse_no_intro_filename using shared test data
TEST_F(FilenameTest, ParseNoIntroFilename) {
    auto test_cases = loader_->get_test_cases("filename", "parse_no_intro_filename");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto result = parse_no_intro_filename(input);

        if (tc.expected.is_object()) {
            auto& exp = tc.expected;
            EXPECT_EQ(result.original_filename, exp.value("original_filename", ""))
                << "Test case: " << tc.id;
            EXPECT_EQ(result.clean_name, exp.value("clean_name", "")) << "Test case: " << tc.id;
            EXPECT_EQ(result.extension, exp.value("extension", "")) << "Test case: " << tc.id;
            EXPECT_EQ(result.region, exp.value("region", "")) << "Test case: " << tc.id;

            if (exp.contains("tags") && exp["tags"].is_array()) {
                auto expected_tags = exp["tags"].get<std::vector<std::string>>();
                EXPECT_EQ(result.tags, expected_tags) << "Test case: " << tc.id;
            }

            if (exp.contains("is_bios")) {
                EXPECT_EQ(result.is_bios, exp["is_bios"].get<bool>()) << "Test case: " << tc.id;
            }
            if (exp.contains("is_demo")) {
                EXPECT_EQ(result.is_demo, exp["is_demo"].get<bool>()) << "Test case: " << tc.id;
            }
            if (exp.contains("is_unlicensed")) {
                EXPECT_EQ(result.is_unlicensed, exp["is_unlicensed"].get<bool>())
                    << "Test case: " << tc.id;
            }
        }
    }
}

// Test is_bios_file using shared test data
TEST_F(FilenameTest, IsBiosFile) {
    auto test_cases = loader_->get_test_cases("filename", "is_bios_file");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_bool();
        auto result = is_bios_file(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description
                                    << " (input: " << input << ")";
    }
}

// Test is_demo_file using shared test data
TEST_F(FilenameTest, IsDemoFile) {
    auto test_cases = loader_->get_test_cases("filename", "is_demo_file");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_bool();
        auto result = is_demo_file(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description
                                    << " (input: " << input << ")";
    }
}

// Test is_unlicensed using shared test data
TEST_F(FilenameTest, IsUnlicensed) {
    auto test_cases = loader_->get_test_cases("filename", "is_unlicensed");
    ASSERT_FALSE(test_cases.empty()) << "No test cases loaded";

    for (const auto& tc : test_cases) {
        auto input = tc.input_string();
        auto expected = tc.expected_bool();
        auto result = is_unlicensed(input);
        EXPECT_EQ(result, expected) << "Test case: " << tc.id << " - " << tc.description
                                    << " (input: " << input << ")";
    }
}

// Direct unit tests for REGION_TAGS map
TEST_F(FilenameTest, RegionTags) {
    EXPECT_EQ(REGION_TAGS.at("USA"), "USA");
    EXPECT_EQ(REGION_TAGS.at("Europe"), "Europe");
    EXPECT_EQ(REGION_TAGS.at("Japan"), "Japan");
    EXPECT_EQ(REGION_TAGS.at("World"), "World");
}
