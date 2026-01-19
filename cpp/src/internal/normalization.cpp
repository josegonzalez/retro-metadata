#include <retro_metadata/internal/normalization.hpp>

#include <algorithm>
#include <cctype>
#include <regex>
#include <sstream>

#ifdef RETRO_METADATA_NO_ICU
// Simplified fallback without ICU
#else
#include <unicode/normalizer2.h>
#include <unicode/uchar.h>
#include <unicode/unistr.h>
#endif

namespace retro_metadata {
namespace normalization {

namespace {

// Regex patterns
const std::regex kLeadingArticlePattern(R"(^(a|an|the)\b)", std::regex::icase);
const std::regex kCommaArticlePattern(R"(,\s(a|an|the)\b(?:\s*[^\w\s]|$))", std::regex::icase);
const std::regex kNonWordSpacePattern(R"([^\w\s])");
const std::regex kMultipleSpacePattern(R"(\s+)");
const std::regex kSearchTermSplitPattern(R"([:\-/&])");
const std::regex kSearchTermNormalizer(R"(\s*[:-]\s+)");

// Convert string to lowercase
std::string to_lower(std::string_view str) {
    std::string result(str);
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

// Replace all occurrences
std::string replace_all(std::string str, std::string_view from, std::string_view to) {
    if (from.empty()) return str;
    size_t pos = 0;
    while ((pos = str.find(from, pos)) != std::string::npos) {
        str.replace(pos, from.length(), to);
        pos += to.length();
    }
    return str;
}

// Trim whitespace
std::string trim(std::string_view str) {
    const auto start = str.find_first_not_of(" \t\n\r");
    if (start == std::string_view::npos) return "";
    const auto end = str.find_last_not_of(" \t\n\r");
    return std::string(str.substr(start, end - start + 1));
}

}  // namespace

const std::map<std::string, bool> kDefaultSensitiveKeys = {
    {"authorization", true}, {"client-id", true},     {"client-secret", true},
    {"client_id", true},     {"client_secret", true}, {"api_key", true},
    {"ssid", true},          {"sspassword", true},    {"devid", true},
    {"devpassword", true},   {"y", true},
};

bool has_non_ascii(std::string_view str) {
    return std::any_of(
        str.begin(), str.end(), [](unsigned char c) { return c > 127; });
}

std::string remove_accents(std::string_view str) {
#ifdef RETRO_METADATA_NO_ICU
    // Simplified ASCII-only fallback - just return as-is
    // This is a best-effort approach without ICU
    std::string result;
    result.reserve(str.size());

    for (unsigned char c : str) {
        // Common accent replacements for Latin characters
        switch (c) {
        // Uppercase accented A
        case 0xC0:
        case 0xC1:
        case 0xC2:
        case 0xC3:
        case 0xC4:
        case 0xC5:
            result += 'A';
            break;
        case 0xC6:
            result += "AE";
            break;
        case 0xC7:
            result += 'C';
            break;
        case 0xC8:
        case 0xC9:
        case 0xCA:
        case 0xCB:
            result += 'E';
            break;
        case 0xCC:
        case 0xCD:
        case 0xCE:
        case 0xCF:
            result += 'I';
            break;
        case 0xD1:
            result += 'N';
            break;
        case 0xD2:
        case 0xD3:
        case 0xD4:
        case 0xD5:
        case 0xD6:
        case 0xD8:
            result += 'O';
            break;
        case 0xD9:
        case 0xDA:
        case 0xDB:
        case 0xDC:
            result += 'U';
            break;
        case 0xDD:
            result += 'Y';
            break;
        // Lowercase accented a
        case 0xE0:
        case 0xE1:
        case 0xE2:
        case 0xE3:
        case 0xE4:
        case 0xE5:
            result += 'a';
            break;
        case 0xE6:
            result += "ae";
            break;
        case 0xE7:
            result += 'c';
            break;
        case 0xE8:
        case 0xE9:
        case 0xEA:
        case 0xEB:
            result += 'e';
            break;
        case 0xEC:
        case 0xED:
        case 0xEE:
        case 0xEF:
            result += 'i';
            break;
        case 0xF1:
            result += 'n';
            break;
        case 0xF2:
        case 0xF3:
        case 0xF4:
        case 0xF5:
        case 0xF6:
        case 0xF8:
            result += 'o';
            break;
        case 0xF9:
        case 0xFA:
        case 0xFB:
        case 0xFC:
            result += 'u';
            break;
        case 0xFD:
        case 0xFF:
            result += 'y';
            break;
        default:
            if (c < 128) {
                result += static_cast<char>(c);
            }
            // Skip other non-ASCII characters
            break;
        }
    }
    return result;
#else
    // Use ICU for proper Unicode normalization
    UErrorCode status = U_ZERO_ERROR;
    const icu::Normalizer2* normalizer = icu::Normalizer2::getNFDInstance(status);
    if (U_FAILURE(status)) {
        return std::string(str);
    }

    icu::UnicodeString ustr = icu::UnicodeString::fromUTF8(icu::StringPiece(str.data(), str.size()));
    icu::UnicodeString normalized;
    normalizer->normalize(ustr, normalized, status);
    if (U_FAILURE(status)) {
        return std::string(str);
    }

    // Remove combining marks (accents)
    icu::UnicodeString result;
    for (int32_t i = 0; i < normalized.length(); ++i) {
        UChar32 c = normalized.char32At(i);
        if (!u_hasBinaryProperty(c, UCHAR_DEFAULT_IGNORABLE_CODE_POINT) &&
            u_charType(c) != U_NON_SPACING_MARK) {
            result.append(c);
        }
    }

    std::string resultStr;
    result.toUTF8String(resultStr);
    return resultStr;
#endif
}

std::string normalize_search_term(
    std::string_view name, bool remove_articles, bool remove_punctuation) {
    // Lowercase and replace underscores
    std::string result = to_lower(name);
    result = replace_all(result, "_", " ");

    // Remove articles
    if (remove_articles) {
        result = std::regex_replace(result, kLeadingArticlePattern, "");
        result = std::regex_replace(result, kCommaArticlePattern, "");
    }

    // Remove punctuation and normalize spaces
    if (remove_punctuation) {
        result = std::regex_replace(result, kNonWordSpacePattern, " ");
        result = std::regex_replace(result, kMultipleSpacePattern, " ");
    }

    // Unicode normalization and accent removal
    if (has_non_ascii(result)) {
        result = remove_accents(result);
    }

    return trim(result);
}

std::string normalize_search_term_default(std::string_view name) {
    return normalize_search_term(name, true, true);
}

std::string normalize_cover_url(std::string_view cover_url) {
    if (cover_url.empty()) {
        return "";
    }
    std::string url(cover_url);
    // Ensure https:// prefix
    if (url.substr(0, 6) == "https:") {
        url = url.substr(6);
    }
    return "https:" + url;
}

std::vector<std::string> split_search_term(std::string_view name) {
    std::vector<std::string> parts;
    std::string input(name);

    std::sregex_token_iterator iter(
        input.begin(), input.end(), kSearchTermSplitPattern, -1);
    std::sregex_token_iterator end;

    for (; iter != end; ++iter) {
        std::string part = trim(*iter);
        if (!part.empty()) {
            parts.push_back(part);
        }
    }

    return parts;
}

std::string normalize_for_api(std::string_view search_term) {
    return std::regex_replace(std::string(search_term), kSearchTermNormalizer, ": ");
}

std::string strip_sensitive_query_params(
    std::string_view raw_url, const std::map<std::string, bool>& custom_sensitive_keys) {
    // Parse URL
    std::string url(raw_url);

    size_t query_start = url.find('?');
    if (query_start == std::string::npos) {
        return url;
    }

    const auto& keys = custom_sensitive_keys.empty() ? kDefaultSensitiveKeys : custom_sensitive_keys;

    std::string base = url.substr(0, query_start);
    std::string query = url.substr(query_start + 1);

    std::vector<std::string> new_params;
    std::istringstream param_stream(query);
    std::string param;

    while (std::getline(param_stream, param, '&')) {
        size_t eq = param.find('=');
        std::string key = (eq != std::string::npos) ? param.substr(0, eq) : param;
        std::string key_lower = to_lower(key);

        if (keys.find(key_lower) == keys.end()) {
            new_params.push_back(param);
        }
    }

    if (new_params.empty()) {
        return base;
    }

    std::ostringstream result;
    result << base << "?";
    for (size_t i = 0; i < new_params.size(); ++i) {
        if (i > 0) result << "&";
        result << new_params[i];
    }
    return result.str();
}

std::map<std::string, std::string> mask_sensitive_values(
    const std::map<std::string, std::string>& values) {
    std::map<std::string, std::string> masked;

    for (const auto& [key, val] : values) {
        if (val.empty()) {
            masked[key] = "";
            continue;
        }

        std::string key_lower = to_lower(key);

        if (key == "Authorization" && val.substr(0, 7) == "Bearer ") {
            std::string token = val.substr(7);
            if (token.size() > 4) {
                masked[key] = "Bearer " + token.substr(0, 2) + "***" +
                              token.substr(token.size() - 2);
            } else {
                masked[key] = "Bearer ***";
            }
        } else if (kDefaultSensitiveKeys.find(key_lower) != kDefaultSensitiveKeys.end()) {
            if (val.size() > 4) {
                masked[key] = val.substr(0, 2) + "***" + val.substr(val.size() - 2);
            } else {
                masked[key] = "***";
            }
        } else {
            masked[key] = val;
        }
    }

    return masked;
}

}  // namespace normalization
}  // namespace retro_metadata
