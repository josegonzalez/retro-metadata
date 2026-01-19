#pragma once

/// @file retro_metadata.hpp
/// @brief Main header for the retro-metadata C++ library
///
/// This is the unified include for all retro-metadata functionality.
/// Include this single header to access all types, providers, cache, etc.

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/cache/memory.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/filename/filename.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/platform/mapping.hpp>
#include <retro_metadata/platform/slug.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>
#include <retro_metadata/types.hpp>

/// @namespace retro_metadata
/// @brief The retro_metadata library namespace
///
/// Contains all types, providers, cache implementations, and utilities
/// for fetching game metadata from various providers.
namespace retro_metadata {

/// Library version string
constexpr const char* kVersion = "1.0.0";

/// Library version as integers
constexpr int kVersionMajor = 1;
constexpr int kVersionMinor = 0;
constexpr int kVersionPatch = 0;

}  // namespace retro_metadata
