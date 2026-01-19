#include <retro_metadata/cache/memory.hpp>

namespace retro_metadata {

MemoryCache::MemoryCache(MemoryCacheOptions options) : options_(std::move(options)) {
    cleanup_thread_ = std::thread(&MemoryCache::cleanup_loop, this);
}

MemoryCache::~MemoryCache() {
    close();
}

MemoryCache::MemoryCache(MemoryCache&& other) noexcept
    : options_(std::move(other.options_)),
      cache_(std::move(other.cache_)),
      lru_(std::move(other.lru_)),
      hits_(other.hits_.load()),
      misses_(other.misses_.load()),
      stop_cleanup_(other.stop_cleanup_.load()) {
    other.stop_cleanup_ = true;
    if (other.cleanup_thread_.joinable()) {
        other.cleanup_thread_.join();
    }
    cleanup_thread_ = std::thread(&MemoryCache::cleanup_loop, this);
}

MemoryCache& MemoryCache::operator=(MemoryCache&& other) noexcept {
    if (this != &other) {
        close();

        options_ = std::move(other.options_);
        cache_ = std::move(other.cache_);
        lru_ = std::move(other.lru_);
        hits_ = other.hits_.load();
        misses_ = other.misses_.load();
        stop_cleanup_ = false;

        other.stop_cleanup_ = true;
        if (other.cleanup_thread_.joinable()) {
            other.cleanup_thread_.join();
        }
        cleanup_thread_ = std::thread(&MemoryCache::cleanup_loop, this);
    }
    return *this;
}

void MemoryCache::cleanup_loop() {
    while (!stop_cleanup_.load()) {
        std::this_thread::sleep_for(options_.cleanup_interval);
        if (!stop_cleanup_.load()) {
            cleanup_expired();
        }
    }
}

void MemoryCache::cleanup_expired() {
    std::unique_lock lock(mutex_);

    for (auto it = lru_.begin(); it != lru_.end();) {
        if (it->is_expired()) {
            cache_.erase(it->key);
            it = lru_.erase(it);
        } else {
            ++it;
        }
    }
}

void MemoryCache::evict_if_needed() {
    while (static_cast<int>(lru_.size()) >= options_.max_size) {
        if (lru_.empty()) break;
        auto oldest = lru_.begin();
        cache_.erase(oldest->key);
        lru_.erase(oldest);
    }
}

std::optional<std::any> MemoryCache::get(const std::string& key) {
    std::unique_lock lock(mutex_);

    auto it = cache_.find(key);
    if (it == cache_.end()) {
        misses_.fetch_add(1);
        return std::nullopt;
    }

    auto& entry = *it->second;
    if (entry.is_expired()) {
        lru_.erase(it->second);
        cache_.erase(it);
        misses_.fetch_add(1);
        return std::nullopt;
    }

    // Move to back (most recently used)
    lru_.splice(lru_.end(), lru_, it->second);
    hits_.fetch_add(1);
    return entry.value;
}

void MemoryCache::set(const std::string& key, std::any value, std::chrono::seconds ttl) {
    std::unique_lock lock(mutex_);

    if (ttl == std::chrono::seconds{0}) {
        ttl = options_.default_ttl;
    }

    std::chrono::steady_clock::time_point expires_at;
    if (ttl.count() > 0) {
        expires_at = std::chrono::steady_clock::now() + ttl;
    }

    // Check if key already exists
    auto it = cache_.find(key);
    if (it != cache_.end()) {
        lru_.splice(lru_.end(), lru_, it->second);
        it->second->value = std::move(value);
        it->second->expires_at = expires_at;
        return;
    }

    // Evict if at capacity
    evict_if_needed();

    // Add new entry
    lru_.push_back(Entry{key, std::move(value), expires_at});
    cache_[key] = std::prev(lru_.end());
}

bool MemoryCache::remove(const std::string& key) {
    std::unique_lock lock(mutex_);

    auto it = cache_.find(key);
    if (it == cache_.end()) {
        return false;
    }

    lru_.erase(it->second);
    cache_.erase(it);
    return true;
}

bool MemoryCache::exists(const std::string& key) {
    std::shared_lock lock(mutex_);

    auto it = cache_.find(key);
    if (it == cache_.end()) {
        return false;
    }

    return !it->second->is_expired();
}

void MemoryCache::clear() {
    std::unique_lock lock(mutex_);
    cache_.clear();
    lru_.clear();
}

void MemoryCache::close() {
    stop_cleanup_ = true;
    if (cleanup_thread_.joinable()) {
        cleanup_thread_.join();
    }
    clear();
}

CacheStats MemoryCache::stats() const {
    std::shared_lock lock(mutex_);

    int expired_count = 0;
    for (const auto& entry : lru_) {
        if (entry.is_expired()) {
            ++expired_count;
        }
    }

    return CacheStats{
        .size = static_cast<int>(lru_.size()),
        .max_size = options_.max_size,
        .expired_count = expired_count,
        .hits = hits_.load(),
        .misses = misses_.load()};
}

size_t MemoryCache::size() const {
    std::shared_lock lock(mutex_);
    return lru_.size();
}

std::unordered_map<std::string, std::any> MemoryCache::get_many(
    const std::vector<std::string>& keys) {
    std::unordered_map<std::string, std::any> result;
    for (const auto& key : keys) {
        auto value = get(key);
        if (value) {
            result[key] = std::move(*value);
        }
    }
    return result;
}

void MemoryCache::set_many(
    const std::unordered_map<std::string, std::any>& items, std::chrono::seconds ttl) {
    for (const auto& [key, value] : items) {
        set(key, value, ttl);
    }
}

int MemoryCache::delete_many(const std::vector<std::string>& keys) {
    int count = 0;
    for (const auto& key : keys) {
        if (remove(key)) {
            ++count;
        }
    }
    return count;
}

std::shared_ptr<MemoryCache> make_memory_cache() {
    return std::make_shared<MemoryCache>();
}

std::shared_ptr<MemoryCache> make_memory_cache(MemoryCacheOptions options) {
    return std::make_shared<MemoryCache>(std::move(options));
}

}  // namespace retro_metadata
