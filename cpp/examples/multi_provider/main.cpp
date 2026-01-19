// Example: Multi-Provider Search
//
// This example demonstrates how to search across multiple metadata providers
// concurrently and aggregate results.
//
// To run:
//   export IGDB_CLIENT_ID="your_client_id"
//   export IGDB_CLIENT_SECRET="your_client_secret"
//   export MOBYGAMES_API_KEY="your_api_key"
//   ./multi_provider

#include <chrono>
#include <cstdlib>
#include <future>
#include <iostream>
#include <map>
#include <memory>
#include <retro_metadata/config.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>
#include <retro_metadata/types.hpp>
#include <string>
#include <vector>

struct ProviderResult {
    std::string provider_name;
    std::vector<retro_metadata::SearchResult> results;
    std::string error;
};

int main() {
    using namespace retro_metadata;
    using namespace std::chrono;

    // Get credentials from environment variables
    const char* igdb_client_id = std::getenv("IGDB_CLIENT_ID");
    const char* igdb_client_secret = std::getenv("IGDB_CLIENT_SECRET");
    const char* moby_api_key = std::getenv("MOBYGAMES_API_KEY");

    // Create providers list
    std::vector<std::pair<std::string, std::shared_ptr<Provider>>> providers;

    // Create IGDB provider if credentials are available
    if (igdb_client_id && igdb_client_secret) {
        ProviderConfig igdb_config;
        igdb_config.enabled = true;
        igdb_config.credentials["client_id"] = igdb_client_id;
        igdb_config.credentials["client_secret"] = igdb_client_secret;
        igdb_config.timeout = seconds(30);

        auto provider = Registry::instance().create("igdb", igdb_config, nullptr);
        if (provider) {
            providers.emplace_back("IGDB", std::move(provider));
        }
    }

    // Create MobyGames provider if credentials are available
    if (moby_api_key) {
        ProviderConfig moby_config;
        moby_config.enabled = true;
        moby_config.credentials["api_key"] = moby_api_key;
        moby_config.timeout = seconds(30);

        auto provider = Registry::instance().create("mobygames", moby_config, nullptr);
        if (provider) {
            providers.emplace_back("MobyGames", std::move(provider));
        }
    }

    if (providers.empty()) {
        std::cerr << "No providers available. Please set at least one of:\n"
                  << "  IGDB_CLIENT_ID and IGDB_CLIENT_SECRET\n"
                  << "  MOBYGAMES_API_KEY\n";
        return 1;
    }

    std::cout << "Using " << providers.size() << " provider(s)\n\n";

    // Search query
    const std::string query = "Chrono Trigger";

    // Search all providers concurrently
    std::cout << "Searching for '" << query << "' across all providers...\n\n";
    auto start = high_resolution_clock::now();

    SearchOptions options;
    options.limit = 5;

    // Launch async searches
    std::vector<std::future<ProviderResult>> futures;
    for (auto& [name, provider] : providers) {
        futures.push_back(std::async(std::launch::async, [&name, &provider, &query, &options]() {
            ProviderResult result;
            result.provider_name = name;
            try {
                result.results = provider->search(query, options);
            } catch (const std::exception& e) {
                result.error = e.what();
            }
            return result;
        }));
    }

    // Collect results
    std::map<std::string, std::vector<SearchResult>> all_results;
    for (auto& future : futures) {
        auto result = future.get();
        if (!result.error.empty()) {
            std::cout << "[" << result.provider_name << "] Error: " << result.error << "\n";
        } else {
            all_results[result.provider_name] = std::move(result.results);
        }
    }

    auto duration = duration_cast<milliseconds>(high_resolution_clock::now() - start);
    std::cout << "Search completed in " << duration.count() << "ms\n\n";

    // Print results by provider
    for (const auto& [provider_name, results] : all_results) {
        std::cout << "=== " << provider_name << " Results ===\n";
        if (results.empty()) {
            std::cout << "  No results found\n";
        } else {
            int i = 1;
            for (const auto& result : results) {
                std::cout << i++ << ". " << result.name << "\n";
                if (result.release_year) {
                    std::cout << "   Year: " << *result.release_year << "\n";
                }
                if (!result.platforms.empty()) {
                    std::cout << "   Platforms: ";
                    for (size_t j = 0; j < result.platforms.size(); ++j) {
                        if (j > 0) std::cout << ", ";
                        std::cout << result.platforms[j].name;
                    }
                    std::cout << "\n";
                }
            }
        }
        std::cout << "\n";
    }

    return 0;
}
