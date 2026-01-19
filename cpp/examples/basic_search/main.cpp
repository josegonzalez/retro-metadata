// Example: Basic Search
//
// This example demonstrates how to search for a game using the IGDB provider.
//
// To run:
//   export IGDB_CLIENT_ID="your_client_id"
//   export IGDB_CLIENT_SECRET="your_client_secret"
//   ./basic_search

#include <cstdlib>
#include <iostream>
#include <retro_metadata/config.hpp>
#include <retro_metadata/provider/registry.hpp>
#include <retro_metadata/types.hpp>

int main() {
    using namespace retro_metadata;

    // Get credentials from environment variables
    const char* client_id_env = std::getenv("IGDB_CLIENT_ID");
    const char* client_secret_env = std::getenv("IGDB_CLIENT_SECRET");

    if (!client_id_env || !client_secret_env) {
        std::cerr << "Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables\n";
        return 1;
    }

    std::string client_id = client_id_env;
    std::string client_secret = client_secret_env;

    // Create provider configuration
    ProviderConfig config;
    config.enabled = true;
    config.credentials["client_id"] = client_id;
    config.credentials["client_secret"] = client_secret;
    config.timeout = std::chrono::seconds(30);

    // Create IGDB provider using the registry
    auto provider = Registry::instance().create("igdb", config, nullptr);
    if (!provider) {
        std::cerr << "Failed to create IGDB provider\n";
        return 1;
    }

    // Search for games
    SearchOptions options;
    options.limit = 5;

    try {
        auto results = provider->search("Super Mario World", options);

        // Print results
        std::cout << "Found " << results.size() << " results for 'Super Mario World':\n\n";
        int i = 1;
        for (const auto& result : results) {
            std::cout << i++ << ". " << result.name << "\n";
            std::cout << "   Provider: " << result.provider << "\n";
            std::cout << "   ID: " << result.provider_id << "\n";
            if (result.release_year) {
                std::cout << "   Year: " << *result.release_year << "\n";
            }
            if (!result.cover_url.empty()) {
                std::cout << "   Cover: " << result.cover_url << "\n";
            }
            std::cout << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Search failed: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
