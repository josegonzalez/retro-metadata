#pragma once

/// @file mapping.hpp
/// @brief Platform ID mappings for various providers

#include <optional>
#include <string>
#include <string_view>

namespace retro_metadata {

/// @brief Contains information about a platform across multiple providers
struct PlatformInfo {
    /// Universal platform slug
    std::string slug;
    /// Human-readable platform name
    std::string name;
    /// IGDB platform ID
    std::optional<int> igdb_id;
    /// MobyGames platform ID
    std::optional<int> mobygames_id;
    /// ScreenScraper platform ID
    std::optional<int> screenscraper_id;
    /// RetroAchievements console ID
    std::optional<int> retroachievements_id;
};

/// @brief Returns the IGDB platform ID for a universal platform slug
[[nodiscard]] std::optional<int> get_igdb_platform_id(std::string_view slug);

/// @brief Returns the MobyGames platform ID for a universal platform slug
[[nodiscard]] std::optional<int> get_mobygames_platform_id(std::string_view slug);

/// @brief Returns the ScreenScraper platform ID for a universal platform slug
[[nodiscard]] std::optional<int> get_screenscraper_platform_id(std::string_view slug);

/// @brief Returns the RetroAchievements platform ID for a universal platform slug
[[nodiscard]] std::optional<int> get_retroachievements_platform_id(std::string_view slug);

/// @brief Returns comprehensive platform information for a universal platform slug
[[nodiscard]] std::optional<PlatformInfo> get_platform_info(std::string_view slug);

/// @brief Returns the universal platform slug from an IGDB platform ID
[[nodiscard]] std::string slug_from_igdb_id(int igdb_id);

/// @brief Returns the universal platform slug from a MobyGames platform ID
[[nodiscard]] std::string slug_from_mobygames_id(int moby_id);

/// @brief Returns the universal platform slug from a ScreenScraper platform ID
[[nodiscard]] std::string slug_from_screenscraper_id(int ss_id);

/// @brief Returns the universal platform slug from a RetroAchievements platform ID
[[nodiscard]] std::string slug_from_retroachievements_id(int ra_id);

}  // namespace retro_metadata
