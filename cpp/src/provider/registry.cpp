#include <retro_metadata/provider/registry.hpp>

namespace retro_metadata {

ProviderRegistry& ProviderRegistry::instance() {
    static ProviderRegistry instance;
    return instance;
}

void ProviderRegistry::register_provider(const std::string& name, ProviderFactoryFunc factory) {
    factories_[name] = std::move(factory);
}

std::unique_ptr<Provider> ProviderRegistry::create(
    const std::string& name,
    const ProviderConfig& config,
    std::shared_ptr<Cache> cache) const {
    auto it = factories_.find(name);
    if (it == factories_.end()) {
        return nullptr;
    }
    return it->second(config, std::move(cache));
}

bool ProviderRegistry::has_provider(const std::string& name) const {
    return factories_.find(name) != factories_.end();
}

std::vector<std::string> ProviderRegistry::registered_providers() const {
    std::vector<std::string> names;
    names.reserve(factories_.size());
    for (const auto& [name, _] : factories_) {
        names.push_back(name);
    }
    return names;
}

}  // namespace retro_metadata
