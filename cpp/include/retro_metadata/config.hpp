#pragma once

/// @file config.hpp
/// @brief Configuration types for the retro-metadata library

#include <any>
#include <functional>
#include <map>
#include <string>
#include <vector>

namespace retro_metadata {

/// @brief Contains configuration for an individual metadata provider
struct ProviderConfig {
    /// Whether this provider is enabled
    bool enabled = false;
    /// Provider-specific credentials
    std::map<std::string, std::string> credentials;
    /// Priority order for this provider (lower = higher priority)
    int priority = 100;
    /// Request timeout in seconds
    int timeout = 30;
    /// Maximum requests per second (0 = unlimited)
    double rate_limit = 0.0;
    /// Additional provider-specific options
    std::map<std::string, std::any> options;

    /// Get a credential value by key
    [[nodiscard]] std::string get_credential(const std::string& key) const {
        auto it = credentials.find(key);
        return it != credentials.end() ? it->second : "";
    }

    /// Returns true if the provider has credentials configured
    [[nodiscard]] bool is_configured() const { return enabled && !credentials.empty(); }
};

/// @brief Returns a default provider configuration
[[nodiscard]] ProviderConfig default_provider_config();

/// @brief Contains configuration for the cache backend
struct CacheConfig {
    /// Cache backend type ("memory", "redis", "sqlite")
    std::string backend = "memory";
    /// Default time-to-live in seconds
    int ttl = 3600;
    /// Maximum number of entries for memory cache
    int max_size = 10000;
    /// Connection string for redis/sqlite backends
    std::string connection_string;
    /// Additional backend-specific options
    std::map<std::string, std::any> options;
};

/// @brief Returns a default cache configuration
[[nodiscard]] CacheConfig default_cache_config();

/// @brief Main configuration for the library
struct Config {
    // Provider configurations
    ProviderConfig igdb;
    ProviderConfig mobygames;
    ProviderConfig screenscraper;
    ProviderConfig retroachievements;
    ProviderConfig steamgriddb;
    ProviderConfig hltb;
    ProviderConfig launchbox;
    ProviderConfig hasheous;
    ProviderConfig thegamesdb;
    ProviderConfig flashpoint;
    ProviderConfig playmatch;
    ProviderConfig gamelist;

    /// Cache configuration
    CacheConfig cache;

    /// Default request timeout in seconds
    int default_timeout = 30;
    /// Maximum concurrent requests across all providers
    int max_concurrent_requests = 10;
    /// User agent string for HTTP requests
    std::string user_agent = "retro-metadata/1.0";
    /// Preferred locale for localized content
    std::string preferred_locale;
    /// List of region codes in priority order
    std::vector<std::string> region_priority = {"us", "wor", "eu", "jp"};

    /// Returns a list of enabled provider names sorted by priority
    [[nodiscard]] std::vector<std::string> get_enabled_providers() const;

    /// Returns the configuration for a specific provider
    [[nodiscard]] ProviderConfig* get_provider_config(const std::string& name);
    [[nodiscard]] const ProviderConfig* get_provider_config(const std::string& name) const;
};

/// @brief Returns a configuration with sensible defaults
[[nodiscard]] Config default_config();

/// @brief Functional option type for configuring the library
using ConfigOption = std::function<void(Config&)>;

/// @brief Configures the IGDB provider
[[nodiscard]] ConfigOption with_igdb(
    const std::string& client_id, const std::string& client_secret);

/// @brief Configures the MobyGames provider
[[nodiscard]] ConfigOption with_mobygames(const std::string& api_key);

/// @brief Configures the ScreenScraper provider
[[nodiscard]] ConfigOption with_screenscraper(
    const std::string& dev_id,
    const std::string& dev_password,
    const std::string& ss_id,
    const std::string& ss_password);

/// @brief Configures the RetroAchievements provider
[[nodiscard]] ConfigOption with_retroachievements(
    const std::string& username, const std::string& api_key);

/// @brief Configures the SteamGridDB provider
[[nodiscard]] ConfigOption with_steamgriddb(const std::string& api_key);

/// @brief Enables the HowLongToBeat provider
[[nodiscard]] ConfigOption with_hltb();

/// @brief Configures the cache backend
[[nodiscard]] ConfigOption with_cache(const std::string& backend, int ttl, int max_size);

/// @brief Configures a Redis cache backend
[[nodiscard]] ConfigOption with_redis_cache(const std::string& connection_string, int ttl);

/// @brief Configures a SQLite cache backend
[[nodiscard]] ConfigOption with_sqlite_cache(const std::string& db_path, int ttl);

/// @brief Sets the user agent string
[[nodiscard]] ConfigOption with_user_agent(const std::string& user_agent);

/// @brief Sets the default timeout
[[nodiscard]] ConfigOption with_timeout(int seconds);

/// @brief Sets the maximum concurrent requests
[[nodiscard]] ConfigOption with_max_concurrent_requests(int max_requests);

/// @brief Sets the preferred locale
[[nodiscard]] ConfigOption with_preferred_locale(const std::string& locale);

/// @brief Sets the region priority order
[[nodiscard]] ConfigOption with_region_priority(const std::vector<std::string>& regions);

}  // namespace retro_metadata
