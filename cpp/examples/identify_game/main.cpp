// Example: Identify Game from Filename
//
// This example demonstrates how to identify a game from its ROM filename.
//
// To run:
//   export IGDB_CLIENT_ID="your_client_id"
//   export IGDB_CLIENT_SECRET="your_client_secret"
//   ./identify_game "Super Mario World (USA).sfc"

#include <cstdlib>
#include <iostream>
#include <retro_metadata/config.hpp>
#include <retro_metadata/filename/filename.hpp>
#include <retro_metadata/provider/registry.hpp>
#include <retro_metadata/types.hpp>

int main(int argc, char* argv[]) {
    using namespace retro_metadata;

    // Get filename from command line
    if (argc < 2) {
        std::cout << "Usage: " << argv[0] << " <filename>\n";
        std::cout << "Example: " << argv[0] << " \"Super Mario World (USA).sfc\"\n";
        return 1;
    }
    std::string rom_filename = argv[1];

    // Get credentials from environment variables
    const char* client_id_env = std::getenv("IGDB_CLIENT_ID");
    const char* client_secret_env = std::getenv("IGDB_CLIENT_SECRET");

    if (!client_id_env || !client_secret_env) {
        std::cerr << "Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables\n";
        return 1;
    }

    std::string client_id = client_id_env;
    std::string client_secret = client_secret_env;

    // Parse the filename first
    std::cout << "Parsing filename: " << rom_filename << "\n\n";

    // Get file extension
    auto ext = filename::get_file_extension(rom_filename);
    std::cout << "Extension: " << ext << "\n";

    // Extract region
    auto region = filename::extract_region(rom_filename);
    std::cout << "Region: " << region << "\n";

    // Clean the filename to get the game name
    auto clean_name = filename::clean_filename(rom_filename, true);
    std::cout << "Clean name: " << clean_name << "\n\n";

    // Create provider configuration
    ProviderConfig config;
    config.enabled = true;
    config.credentials["client_id"] = client_id;
    config.credentials["client_secret"] = client_secret;
    config.timeout = std::chrono::seconds(30);

    // Create IGDB provider
    auto provider = Registry::instance().create("igdb", config, nullptr);
    if (!provider) {
        std::cerr << "Failed to create IGDB provider\n";
        return 1;
    }

    // Identify the game
    IdentifyOptions options;

    try {
        auto result = provider->identify(rom_filename, options);

        if (!result) {
            std::cout << "No game found\n";
            return 0;
        }

        // Print result
        std::cout << "Game Identified:\n";
        std::cout << "  Name: " << result->name << "\n";
        std::cout << "  Match Score: " << result->match_score << "\n";

        if (!result->summary.empty()) {
            std::string summary = result->summary;
            if (summary.length() > 200) {
                summary = summary.substr(0, 200) + "...";
            }
            std::cout << "  Summary: " << summary << "\n";
        }

        if (!result->metadata.genres.empty()) {
            std::cout << "  Genres: ";
            for (size_t i = 0; i < result->metadata.genres.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << result->metadata.genres[i];
            }
            std::cout << "\n";
        }

        if (!result->metadata.companies.empty()) {
            std::cout << "  Companies: ";
            for (size_t i = 0; i < result->metadata.companies.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << result->metadata.companies[i];
            }
            std::cout << "\n";
        }

        if (result->metadata.release_year) {
            std::cout << "  Year: " << *result->metadata.release_year << "\n";
        }

        if (!result->artwork.cover_url.empty()) {
            std::cout << "  Cover: " << result->artwork.cover_url << "\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Identify failed: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
