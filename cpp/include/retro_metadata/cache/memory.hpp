#pragma once

/// @file memory.hpp
/// @brief In-memory LRU cache implementation

#include <retro_metadata/cache/cache.hpp>

#include <atomic>
#include <chrono>
#include <list>
#include <mutex>
#include <shared_mutex>
#include <thread>
#include <unordered_map>

namespace retro_metadata {

/// @brief Configuration options for MemoryCache
struct MemoryCacheOptions {
    /// Maximum number of entries
    int max_size = 10000;
    /// Default TTL for entries
    std::chrono::seconds default_ttl = std::chrono::hours{1};
    /// Interval for expired entry cleanup
    std::chrono::seconds cleanup_interval = std::chrono::minutes{1};
};

/// @brief In-memory LRU cache with TTL support
///
/// Thread-safe implementation using a doubly-linked list for LRU ordering
/// and a hash map for O(1) lookups.
class MemoryCache : public BulkCache {
public:
    explicit MemoryCache(MemoryCacheOptions options = {});
    ~MemoryCache() override;

    // Disable copy
    MemoryCache(const MemoryCache&) = delete;
    MemoryCache& operator=(const MemoryCache&) = delete;

    // Allow move
    MemoryCache(MemoryCache&&) noexcept;
    MemoryCache& operator=(MemoryCache&&) noexcept;

    // Cache interface
    [[nodiscard]] std::optional<std::any> get(const std::string& key) override;
    void set(const std::string& key, std::any value, std::chrono::seconds ttl) override;
    [[nodiscard]] bool remove(const std::string& key) override;
    [[nodiscard]] bool exists(const std::string& key) override;
    void clear() override;
    void close() override;

    // StatsCache interface
    [[nodiscard]] CacheStats stats() const override;

    // BulkCache interface
    [[nodiscard]] std::unordered_map<std::string, std::any> get_many(
        const std::vector<std::string>& keys) override;
    void set_many(
        const std::unordered_map<std::string, std::any>& items, std::chrono::seconds ttl) override;
    [[nodiscard]] int delete_many(const std::vector<std::string>& keys) override;

    /// @brief Returns the current number of entries
    [[nodiscard]] size_t size() const;

private:
    struct Entry {
        std::string key;
        std::any value;
        std::chrono::steady_clock::time_point expires_at;

        [[nodiscard]] bool is_expired() const {
            if (expires_at == std::chrono::steady_clock::time_point{}) {
                return false;
            }
            return std::chrono::steady_clock::now() > expires_at;
        }
    };

    void cleanup_loop();
    void cleanup_expired();
    void evict_if_needed();

    MemoryCacheOptions options_;
    mutable std::shared_mutex mutex_;
    std::unordered_map<std::string, std::list<Entry>::iterator> cache_;
    std::list<Entry> lru_;
    std::atomic<int64_t> hits_{0};
    std::atomic<int64_t> misses_{0};
    std::atomic<bool> stop_cleanup_{false};
    std::thread cleanup_thread_;
};

/// @brief Creates a memory cache with default options
[[nodiscard]] std::shared_ptr<MemoryCache> make_memory_cache();

/// @brief Creates a memory cache with custom options
[[nodiscard]] std::shared_ptr<MemoryCache> make_memory_cache(MemoryCacheOptions options);

}  // namespace retro_metadata
