// Test data loader for shared JSON test files
#pragma once

#include <filesystem>
#include <fstream>
#include <nlohmann/json.hpp>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace retro_metadata::testutil {

using json = nlohmann::json;

// Skip configuration for specific languages
struct SkipConfig {
    std::optional<std::string> python;
    std::optional<std::string> go;
    std::optional<std::string> cpp;

    bool should_skip_cpp() const { return cpp.has_value() && !cpp->empty(); }
};

// Single test case from shared test data
struct TestCase {
    std::string id;
    std::string description;
    std::string category;
    json input;
    std::optional<std::vector<json>> operations;
    std::optional<json> config;
    json expected;
    std::optional<double> expected_min;
    std::optional<double> expected_max;
    std::optional<json> expected_contains;
    std::optional<json> expected_not_contains;
    std::optional<SkipConfig> skip;

    // Helper methods to access input as different types
    std::string input_string() const {
        if (input.is_string()) {
            return input.get<std::string>();
        }
        return "";
    }

    bool input_has_key(const std::string& key) const {
        return input.is_object() && input.contains(key);
    }

    template <typename T>
    T input_get(const std::string& key, const T& default_value = T{}) const {
        if (input.is_object() && input.contains(key)) {
            return input[key].get<T>();
        }
        return default_value;
    }

    // Helper methods to access expected as different types
    std::string expected_string() const {
        if (expected.is_string()) {
            return expected.get<std::string>();
        }
        return "";
    }

    double expected_float() const {
        if (expected.is_number()) {
            return expected.get<double>();
        }
        return 0.0;
    }

    int expected_int() const {
        if (expected.is_number()) {
            return expected.get<int>();
        }
        return 0;
    }

    bool expected_bool() const {
        if (expected.is_boolean()) {
            return expected.get<bool>();
        }
        return false;
    }

    std::vector<std::string> expected_string_slice() const {
        std::vector<std::string> result;
        if (expected.is_array()) {
            for (const auto& item : expected) {
                if (item.is_string()) {
                    result.push_back(item.get<std::string>());
                }
            }
        }
        return result;
    }

    bool is_expected_null() const { return expected.is_null(); }

    bool should_skip_cpp() const { return skip.has_value() && skip->should_skip_cpp(); }
};

// Parsed test data file structure
struct TestData {
    std::string version;
    std::string test_suite;
    std::string description;
    std::vector<TestCase> test_cases;
};

// JSON parsing for SkipConfig
inline void from_json(const json& j, SkipConfig& s) {
    if (j.contains("python") && j["python"].is_string()) {
        s.python = j["python"].get<std::string>();
    }
    if (j.contains("go") && j["go"].is_string()) {
        s.go = j["go"].get<std::string>();
    }
    if (j.contains("cpp") && j["cpp"].is_string()) {
        s.cpp = j["cpp"].get<std::string>();
    }
}

// JSON parsing for TestCase
inline void from_json(const json& j, TestCase& tc) {
    tc.id = j.value("id", "");
    tc.description = j.value("description", "");
    tc.category = j.value("category", "");
    tc.input = j.value("input", json{});
    tc.expected = j.value("expected", json{});

    if (j.contains("operations")) {
        tc.operations = j["operations"].get<std::vector<json>>();
    }
    if (j.contains("config")) {
        tc.config = j["config"];
    }
    if (j.contains("expected_min")) {
        tc.expected_min = j["expected_min"].get<double>();
    }
    if (j.contains("expected_max")) {
        tc.expected_max = j["expected_max"].get<double>();
    }
    if (j.contains("expected_contains")) {
        tc.expected_contains = j["expected_contains"];
    }
    if (j.contains("expected_not_contains")) {
        tc.expected_not_contains = j["expected_not_contains"];
    }
    if (j.contains("skip")) {
        SkipConfig skip;
        from_json(j["skip"], skip);
        tc.skip = skip;
    }
}

// JSON parsing for TestData
inline void from_json(const json& j, TestData& td) {
    td.version = j.value("version", "");
    td.test_suite = j.value("test_suite", "");
    td.description = j.value("description", "");
    if (j.contains("test_cases")) {
        td.test_cases = j["test_cases"].get<std::vector<TestCase>>();
    }
}

// Loader for test data from shared JSON files
class Loader {
  public:
    explicit Loader(const std::filesystem::path& testdata_dir) : testdata_dir_(testdata_dir) {}

    // Create loader that finds testdata directory from current working directory
    static Loader from_repo() {
        auto testdata_dir = find_testdata_dir();
        if (!testdata_dir) {
            throw std::runtime_error("testdata directory not found");
        }
        return Loader(*testdata_dir);
    }

    // Create loader using TESTDATA_DIR compile-time definition
    static Loader from_compile_definition() {
#ifdef TESTDATA_DIR
        return Loader(std::filesystem::path(TESTDATA_DIR));
#else
        return from_repo();
#endif
    }

    // Load test data from a JSON file
    TestData load(const std::string& category, const std::string& test_suite) const {
        auto file_path = testdata_dir_ / category / (test_suite + ".json");

        if (!std::filesystem::exists(file_path)) {
            throw std::runtime_error("Test data file not found: " + file_path.string());
        }

        std::ifstream file(file_path);
        if (!file.is_open()) {
            throw std::runtime_error("Failed to open test data file: " + file_path.string());
        }

        json j;
        file >> j;

        TestData data;
        from_json(j, data);
        return data;
    }

    // Load test data and filter by category
    TestData load_with_filter(const std::string& category, const std::string& test_suite,
                              const std::string& filter_category) const {
        auto data = load(category, test_suite);

        if (filter_category.empty()) {
            return data;
        }

        std::vector<TestCase> filtered;
        for (const auto& tc : data.test_cases) {
            if (tc.category == filter_category) {
                filtered.push_back(tc);
            }
        }
        data.test_cases = std::move(filtered);

        return data;
    }

    // Get all non-skipped test cases for C++
    std::vector<TestCase> get_test_cases(const std::string& category,
                                         const std::string& test_suite) const {
        auto data = load(category, test_suite);

        std::vector<TestCase> cases;
        for (const auto& tc : data.test_cases) {
            if (!tc.should_skip_cpp()) {
                cases.push_back(tc);
            }
        }

        return cases;
    }

    const std::filesystem::path& testdata_dir() const { return testdata_dir_; }

  private:
    std::filesystem::path testdata_dir_;

    static std::optional<std::filesystem::path> find_testdata_dir() {
        auto dir = std::filesystem::current_path();

        while (true) {
            auto testdata_path = dir / "testdata";
            if (std::filesystem::exists(testdata_path) &&
                std::filesystem::is_directory(testdata_path)) {
                return testdata_path;
            }

            auto parent = dir.parent_path();
            if (parent == dir) {
                break;
            }
            dir = parent;
        }

        return std::nullopt;
    }
};

}  // namespace retro_metadata::testutil
