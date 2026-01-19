#pragma once

/// @file cache.hpp
/// @brief Cache interface for the retro-metadata library

#include <any>
#include <chrono>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>

namespace retro_metadata {

/// @brief Cache statistics
struct CacheStats {
    /// Current number of entries
    int size = 0;
    /// Maximum number of entries (for memory cache)
    int max_size = 0;
    /// Number of expired entries
    int expired_count = 0;
    /// Number of cache hits
    int64_t hits = 0;
    /// Number of cache misses
    int64_t misses = 0;
};

/// @brief Abstract cache interface
///
/// All cache backends must implement this interface.
class Cache {
public:
    virtual ~Cache() = default;

    /// @brief Retrieves a value from the cache
    /// @param key The cache key
    /// @return The cached value, or std::nullopt if not found or expired
    [[nodiscard]] virtual std::optional<std::any> get(const std::string& key) = 0;

    /// @brief Stores a value in the cache
    /// @param key The cache key
    /// @param value The value to store
    /// @param ttl Time-to-live (0 = use default TTL)
    virtual void set(
        const std::string& key,
        std::any value,
        std::chrono::seconds ttl = std::chrono::seconds{0}) = 0;

    /// @brief Removes a value from the cache
    /// @param key The cache key
    /// @return true if the key was deleted, false if it didn't exist
    [[nodiscard]] virtual bool remove(const std::string& key) = 0;

    /// @brief Checks if a key exists in the cache
    /// @param key The cache key
    /// @return true if the key exists and is not expired
    [[nodiscard]] virtual bool exists(const std::string& key) = 0;

    /// @brief Removes all entries from the cache
    virtual void clear() = 0;

    /// @brief Closes any connections and cleans up resources
    virtual void close() = 0;
};

/// @brief Cache with statistics support
class StatsCache : public Cache {
public:
    /// @brief Returns cache statistics
    [[nodiscard]] virtual CacheStats stats() const = 0;
};

/// @brief Cache with bulk operations support
class BulkCache : public StatsCache {
public:
    /// @brief Retrieves multiple values from the cache
    /// @param keys The cache keys
    /// @return Map of key to value for found keys
    [[nodiscard]] virtual std::unordered_map<std::string, std::any> get_many(
        const std::vector<std::string>& keys) = 0;

    /// @brief Stores multiple values in the cache
    /// @param items Map of key to value
    /// @param ttl Time-to-live (0 = use default TTL)
    virtual void set_many(
        const std::unordered_map<std::string, std::any>& items,
        std::chrono::seconds ttl = std::chrono::seconds{0}) = 0;

    /// @brief Removes multiple values from the cache
    /// @param keys The cache keys
    /// @return Number of keys that were deleted
    [[nodiscard]] virtual int delete_many(const std::vector<std::string>& keys) = 0;
};

/// @brief A cache that doesn't cache anything
///
/// Useful for testing or disabling caching.
class NullCache : public Cache {
public:
    [[nodiscard]] std::optional<std::any> get(const std::string& /*key*/) override {
        return std::nullopt;
    }

    void set(
        const std::string& /*key*/,
        std::any /*value*/,
        std::chrono::seconds /*ttl*/) override {}

    [[nodiscard]] bool remove(const std::string& /*key*/) override { return false; }

    [[nodiscard]] bool exists(const std::string& /*key*/) override { return false; }

    void clear() override {}

    void close() override {}
};

/// @brief Wraps a cache with a key prefix
class PrefixedCache : public Cache {
public:
    PrefixedCache(std::shared_ptr<Cache> cache, std::string prefix)
        : cache_(std::move(cache)), prefix_(std::move(prefix)) {}

    [[nodiscard]] std::optional<std::any> get(const std::string& key) override {
        return cache_->get(prefix_key(key));
    }

    void set(const std::string& key, std::any value, std::chrono::seconds ttl) override {
        cache_->set(prefix_key(key), std::move(value), ttl);
    }

    [[nodiscard]] bool remove(const std::string& key) override {
        return cache_->remove(prefix_key(key));
    }

    [[nodiscard]] bool exists(const std::string& key) override {
        return cache_->exists(prefix_key(key));
    }

    void clear() override { cache_->clear(); }

    void close() override { cache_->close(); }

private:
    [[nodiscard]] std::string prefix_key(const std::string& key) const {
        return prefix_ + ":" + key;
    }

    std::shared_ptr<Cache> cache_;
    std::string prefix_;
};

}  // namespace retro_metadata
