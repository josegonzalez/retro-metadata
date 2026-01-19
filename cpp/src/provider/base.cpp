#include <retro_metadata/provider/base.hpp>

namespace retro_metadata {

BaseProvider::BaseProvider(
    std::string name, ProviderConfig config, std::shared_ptr<Cache> cache)
    : name_(std::move(name)), config_(std::move(config)), cache_(std::move(cache)) {}

bool BaseProvider::is_enabled() const {
    return config_.enabled && config_.is_configured();
}

std::string BaseProvider::get_credential(const std::string& key) const {
    return config_.get_credential(key);
}

std::string BaseProvider::normalize_search_term(const std::string& name) const {
    return normalization::normalize_search_term_default(name);
}

std::string BaseProvider::normalize_cover_url(const std::string& url) const {
    return normalization::normalize_cover_url(url);
}

matching::BestMatchResult BaseProvider::find_best_match(
    const std::string& search_term, const std::vector<std::string>& candidates) const {
    return matching::find_best_match(
        search_term,
        candidates,
        matching::FindBestMatchOptions{
            .min_similarity_score = min_similarity_score_, .normalize = true});
}

matching::BestMatchResult BaseProvider::find_best_match_with_options(
    const std::string& search_term,
    const std::vector<std::string>& candidates,
    const matching::FindBestMatchOptions& opts) const {
    return matching::find_best_match(search_term, candidates, opts);
}

void BaseProvider::set_min_similarity_score(double score) {
    min_similarity_score_ = score;
}

std::optional<int> BaseProvider::extract_id_from_filename(
    const std::string& filename, const std::regex& pattern) const {
    std::smatch match;
    if (std::regex_search(filename, match, pattern) && match.size() > 1) {
        try {
            return std::stoi(match[1].str());
        } catch (...) {
            return std::nullopt;
        }
    }
    return std::nullopt;
}

std::vector<std::string> BaseProvider::split_search_term(const std::string& name) const {
    return normalization::split_search_term(name);
}

std::optional<std::any> BaseProvider::get_cached(const std::string& key) const {
    if (!cache_) {
        return std::nullopt;
    }
    return cache_->get(name_ + ":" + key);
}

void BaseProvider::set_cached(const std::string& key, std::any value) const {
    if (cache_) {
        cache_->set(name_ + ":" + key, std::move(value));
    }
}

}  // namespace retro_metadata
