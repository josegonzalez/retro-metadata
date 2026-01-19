#include <retro_metadata/filename/filename.hpp>

#include <algorithm>
#include <cctype>
#include <regex>
#include <set>

namespace retro_metadata {
namespace filename {

const std::map<std::string, std::string> kRegionTags = {
    {"usa", "us"},      {"u", "us"},          {"us", "us"},       {"america", "us"},
    {"world", "wor"},   {"w", "wor"},         {"wor", "wor"},     {"europe", "eu"},
    {"e", "eu"},        {"eu", "eu"},         {"eur", "eu"},      {"japan", "jp"},
    {"j", "jp"},        {"jp", "jp"},         {"jpn", "jp"},      {"jap", "jp"},
    {"korea", "kr"},    {"k", "kr"},          {"kr", "kr"},       {"kor", "kr"},
    {"china", "cn"},    {"ch", "cn"},         {"cn", "cn"},       {"chn", "cn"},
    {"taiwan", "tw"},   {"tw", "tw"},         {"asia", "as"},     {"as", "as"},
    {"australia", "au"},{"au", "au"},         {"brazil", "br"},   {"br", "br"},
    {"france", "fr"},   {"fr", "fr"},         {"germany", "de"},  {"de", "de"},
    {"ger", "de"},      {"italy", "it"},      {"it", "it"},       {"spain", "es"},
    {"es", "es"},       {"spa", "es"},        {"netherlands", "nl"},{"nl", "nl"},
    {"sweden", "se"},   {"se", "se"},         {"russia", "ru"},   {"ru", "ru"},
};

namespace {

// Regex patterns
const std::regex kTagPattern(R"([\(\[]([^\)\]]+)[\)\]])");
const std::regex kExtensionPattern(R"(\.([a-zA-Z0-9]+)$)");

// Demo/prototype tags
const std::set<std::string> kDemoTags = {
    "demo", "sample", "trial", "preview", "proto", "prototype", "beta", "alpha"};

// Unlicensed tags
const std::set<std::string> kUnlicensedTags = {"unl", "unlicensed", "pirate", "hack"};

// Language codes
const std::set<std::string> kLanguageCodes = {
    "en", "ja", "de", "fr", "es", "it", "nl", "pt", "sv", "ko", "zh"};

std::string to_lower(std::string_view str) {
    std::string result(str);
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

std::string trim(std::string_view str) {
    const auto start = str.find_first_not_of(" \t\n\r");
    if (start == std::string_view::npos) return "";
    const auto end = str.find_last_not_of(" \t\n\r");
    return std::string(str.substr(start, end - start + 1));
}

// Get base filename from path
std::string basename(std::string_view path) {
    auto pos = path.find_last_of("/\\");
    if (pos != std::string_view::npos) {
        return std::string(path.substr(pos + 1));
    }
    return std::string(path);
}

}  // namespace

std::string get_file_extension(std::string_view filename) {
    std::smatch match;
    std::string fname(filename);
    if (std::regex_search(fname, match, kExtensionPattern)) {
        return to_lower(match[1].str());
    }
    return "";
}

std::vector<std::string> extract_tags(std::string_view filename) {
    std::vector<std::string> tags;
    std::string fname(filename);
    std::sregex_iterator iter(fname.begin(), fname.end(), kTagPattern);
    std::sregex_iterator end;

    for (; iter != end; ++iter) {
        tags.push_back((*iter)[1].str());
    }

    return tags;
}

std::string extract_region(std::string_view filename) {
    auto tags = extract_tags(filename);

    for (const auto& tag : tags) {
        std::string tag_lower = to_lower(tag);

        // Handle comma-separated regions (e.g., "USA, Europe")
        size_t pos = 0;
        std::string part;
        while (pos < tag_lower.size()) {
            size_t comma_pos = tag_lower.find(',', pos);
            if (comma_pos == std::string::npos) {
                part = trim(tag_lower.substr(pos));
                pos = tag_lower.size();
            } else {
                part = trim(tag_lower.substr(pos, comma_pos - pos));
                pos = comma_pos + 1;
            }

            auto it = kRegionTags.find(part);
            if (it != kRegionTags.end()) {
                return it->second;
            }
        }
    }

    return "";
}

std::string clean_filename(std::string_view filename, bool remove_extension) {
    // Get just the filename if a path was provided
    std::string name = basename(filename);

    // Save and remove extension if keeping it
    std::string ext;
    if (!remove_extension) {
        std::smatch match;
        if (std::regex_search(name, match, kExtensionPattern)) {
            ext = match[0].str();
        }
    }

    // Remove extension from name for processing
    name = std::regex_replace(name, kExtensionPattern, "");

    // Remove all tags in parentheses and brackets
    name = std::regex_replace(name, kTagPattern, "");

    // Clean up extra whitespace
    static const std::regex kMultiSpace(R"(\s+)");
    name = std::regex_replace(name, kMultiSpace, " ");
    name = trim(name);

    // Reattach extension if keeping it
    if (!ext.empty()) {
        name += ext;
    }

    return name;
}

ParsedFilename parse_no_intro_filename(std::string_view filename) {
    ParsedFilename result;

    result.name = clean_filename(filename, true);
    result.tags = extract_tags(filename);
    result.region = extract_region(filename);
    result.extension = get_file_extension(filename);

    // Try to identify version
    for (const auto& tag : result.tags) {
        std::string tag_lower = to_lower(tag);
        if (tag_lower.substr(0, 4) == "rev " || tag_lower[0] == 'v' ||
            tag_lower.substr(0, 7) == "version") {
            result.version = tag;
            break;
        }
    }

    // Try to identify languages
    for (const auto& tag : result.tags) {
        std::string tag_lower = to_lower(tag);
        if (kLanguageCodes.count(tag_lower) > 0 || tag_lower.find('+') != std::string::npos) {
            result.languages.push_back(tag);
        }
    }

    return result;
}

bool is_bios_file(std::string_view filename) {
    std::string name_lower = to_lower(filename);
    return name_lower.find("bios") != std::string::npos ||
           name_lower.find("[bios]") != std::string::npos ||
           name_lower.find("(bios)") != std::string::npos;
}

bool is_demo_file(std::string_view filename) {
    auto tags = extract_tags(filename);
    for (const auto& tag : tags) {
        if (kDemoTags.count(to_lower(tag)) > 0) {
            return true;
        }
    }
    return false;
}

bool is_unlicensed(std::string_view filename) {
    auto tags = extract_tags(filename);
    for (const auto& tag : tags) {
        if (kUnlicensedTags.count(to_lower(tag)) > 0) {
            return true;
        }
    }
    return false;
}

}  // namespace filename
}  // namespace retro_metadata
