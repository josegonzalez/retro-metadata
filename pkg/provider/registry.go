package provider

import (
	"fmt"
	"sync"

	"github.com/josegonzalez/retro-metadata/pkg/cache"
	"github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

// Factory is a function that creates a provider instance.
type Factory func(config retrometadata.ProviderConfig, cache cache.Cache) (Provider, error)

// Registry manages provider factories and instances.
type Registry struct {
	mu        sync.RWMutex
	factories map[string]Factory
}

// NewRegistry creates a new provider registry.
func NewRegistry() *Registry {
	return &Registry{
		factories: make(map[string]Factory),
	}
}

// Register registers a provider factory.
func (r *Registry) Register(name string, factory Factory) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.factories[name] = factory
}

// Create creates a provider instance by name.
func (r *Registry) Create(name string, config retrometadata.ProviderConfig, c cache.Cache) (Provider, error) {
	r.mu.RLock()
	factory, ok := r.factories[name]
	r.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("%w: %s", retrometadata.ErrProviderNotFound, name)
	}

	return factory(config, c)
}

// List returns a list of registered provider names.
func (r *Registry) List() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()

	names := make([]string, 0, len(r.factories))
	for name := range r.factories {
		names = append(names, name)
	}
	return names
}

// Has returns true if a provider is registered.
func (r *Registry) Has(name string) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	_, ok := r.factories[name]
	return ok
}

// DefaultRegistry is the global provider registry.
var DefaultRegistry = NewRegistry()

// Register registers a provider factory in the default registry.
func Register(name string, factory Factory) {
	DefaultRegistry.Register(name, factory)
}

// Create creates a provider instance from the default registry.
func Create(name string, config retrometadata.ProviderConfig, c cache.Cache) (Provider, error) {
	return DefaultRegistry.Create(name, config, c)
}

// List returns provider names from the default registry.
func List() []string {
	return DefaultRegistry.List()
}

// Has checks if a provider is in the default registry.
func Has(name string) bool {
	return DefaultRegistry.Has(name)
}
