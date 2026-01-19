// Example: Using Cache with Providers
//
// This example demonstrates how to use an in-memory cache with providers
// to reduce API calls and improve performance.
//
// To run:
//   export IGDB_CLIENT_ID="your_client_id"
//   export IGDB_CLIENT_SECRET="your_client_secret"
//   ./with_cache

#include <chrono>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <retro_metadata/cache/memory.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/provider/registry.hpp>
#include <retro_metadata/types.hpp>

int main() {
    using namespace retro_metadata;
    using namespace std::chrono;

    // Get credentials from environment variables
    const char* client_id_env = std::getenv("IGDB_CLIENT_ID");
    const char* client_secret_env = std::getenv("IGDB_CLIENT_SECRET");

    if (!client_id_env || !client_secret_env) {
        std::cerr << "Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables\n";
        return 1;
    }

    std::string client_id = client_id_env;
    std::string client_secret = client_secret_env;

    // Create an in-memory cache
    // Parameters: max_size, ttl
    auto mem_cache = std::make_shared<cache::MemoryCache>(1000, minutes(30));

    // Create provider configuration
    ProviderConfig config;
    config.enabled = true;
    config.credentials["client_id"] = client_id;
    config.credentials["client_secret"] = client_secret;
    config.timeout = seconds(30);

    // Create IGDB provider with cache
    auto provider = Registry::instance().create("igdb", config, mem_cache);
    if (!provider) {
        std::cerr << "Failed to create IGDB provider\n";
        return 1;
    }

    const std::string query = "The Legend of Zelda";
    SearchOptions options;
    options.limit = 5;

    try {
        // First search - will hit the API
        std::cout << "First search (no cache)...\n";
        auto start = high_resolution_clock::now();
        auto results1 = provider->search(query, options);
        auto duration = duration_cast<milliseconds>(high_resolution_clock::now() - start);
        std::cout << "Found " << results1.size() << " results in " << duration.count() << "ms\n\n";

        // Second search - should be cached
        std::cout << "Second search (should be cached)...\n";
        start = high_resolution_clock::now();
        auto results2 = provider->search(query, options);
        duration = duration_cast<milliseconds>(high_resolution_clock::now() - start);
        std::cout << "Found " << results2.size() << " results in " << duration.count() << "ms\n\n";

        // Print cache stats
        auto stats = mem_cache->stats();
        std::cout << "Cache Stats:\n";
        std::cout << "  Size: " << stats.size << "\n";
        std::cout << "  Hits: " << stats.hits << "\n";
        std::cout << "  Misses: " << stats.misses << "\n";

        // Print results
        std::cout << "\nResults for '" << query << "':\n";
        int i = 1;
        for (const auto& result : results1) {
            std::cout << i++ << ". " << result.name << " (" << result.provider << ")\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Search failed: " << e.what() << "\n";
        return 1;
    }

    // Close the cache
    mem_cache->close();

    return 0;
}
