#pragma once

/// @file registry.hpp
/// @brief Provider factory registry

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/provider/provider.hpp>

#include <functional>
#include <memory>
#include <string>
#include <unordered_map>

namespace retro_metadata {

/// @brief Factory function type for creating providers
using ProviderFactoryFunc = std::function<std::unique_ptr<Provider>(
    const ProviderConfig& config, std::shared_ptr<Cache> cache)>;

/// @brief Singleton registry for provider factories
///
/// Allows providers to register themselves and be created by name.
class ProviderRegistry {
public:
    /// @brief Returns the singleton instance
    static ProviderRegistry& instance();

    /// @brief Registers a provider factory
    ///
    /// @param name Provider name (e.g., "igdb", "mobygames")
    /// @param factory Factory function to create the provider
    void register_provider(const std::string& name, ProviderFactoryFunc factory);

    /// @brief Creates a provider by name
    ///
    /// @param name Provider name
    /// @param config Provider configuration
    /// @param cache Optional cache backend
    /// @return Created provider or nullptr if not registered
    [[nodiscard]] std::unique_ptr<Provider> create(
        const std::string& name,
        const ProviderConfig& config,
        std::shared_ptr<Cache> cache = nullptr) const;

    /// @brief Checks if a provider is registered
    [[nodiscard]] bool has_provider(const std::string& name) const;

    /// @brief Returns all registered provider names
    [[nodiscard]] std::vector<std::string> registered_providers() const;

private:
    ProviderRegistry() = default;
    std::unordered_map<std::string, ProviderFactoryFunc> factories_;
};

/// @brief Helper class for auto-registration of providers
///
/// Use the REGISTER_PROVIDER macro instead of using this directly.
class ProviderRegistrar {
public:
    ProviderRegistrar(const std::string& name, ProviderFactoryFunc factory) {
        ProviderRegistry::instance().register_provider(name, std::move(factory));
    }
};

/// @brief Macro to register a provider factory
///
/// Usage:
/// @code
/// REGISTER_PROVIDER("igdb", [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
///     return std::make_unique<IGDBProvider>(config, cache);
/// });
/// @endcode
#define REGISTER_PROVIDER(name, factory)                               \
    static ::retro_metadata::ProviderRegistrar provider_registrar_##__LINE__(name, factory)

/// @brief Convenience function to register a provider
inline void register_provider(const std::string& name, ProviderFactoryFunc factory) {
    ProviderRegistry::instance().register_provider(name, std::move(factory));
}

/// @brief Convenience function to create a provider
[[nodiscard]] inline std::unique_ptr<Provider> create_provider(
    const std::string& name,
    const ProviderConfig& config,
    std::shared_ptr<Cache> cache = nullptr) {
    return ProviderRegistry::instance().create(name, config, std::move(cache));
}

}  // namespace retro_metadata
