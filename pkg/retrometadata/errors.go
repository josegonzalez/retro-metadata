package retrometadata

import (
	"errors"
	"fmt"
)

// Common sentinel errors for the library.
var (
	// ErrProviderNotFound indicates that a requested provider is not found or not configured.
	ErrProviderNotFound = errors.New("provider not found or not configured")

	// ErrProviderAuth indicates that provider authentication failed.
	ErrProviderAuth = errors.New("provider authentication failed")

	// ErrProviderConnection indicates that connection to a provider failed.
	ErrProviderConnection = errors.New("provider connection failed")

	// ErrProviderRateLimit indicates that a provider rate limit was exceeded.
	ErrProviderRateLimit = errors.New("provider rate limit exceeded")

	// ErrGameNotFound indicates that a game was not found.
	ErrGameNotFound = errors.New("game not found")

	// ErrInvalidConfig indicates that the configuration is invalid.
	ErrInvalidConfig = errors.New("invalid configuration")

	// ErrCacheOperation indicates that a cache operation failed.
	ErrCacheOperation = errors.New("cache operation failed")
)

// ProviderError wraps an error with provider context.
type ProviderError struct {
	// Provider is the name of the provider that caused the error
	Provider string
	// Op is the operation that failed
	Op string
	// Err is the underlying error
	Err error
}

// Error implements the error interface.
func (e *ProviderError) Error() string {
	if e.Op != "" {
		return fmt.Sprintf("%s: %s: %v", e.Provider, e.Op, e.Err)
	}
	return fmt.Sprintf("%s: %v", e.Provider, e.Err)
}

// Unwrap returns the underlying error.
func (e *ProviderError) Unwrap() error {
	return e.Err
}

// NewProviderError creates a new ProviderError.
func NewProviderError(provider, op string, err error) *ProviderError {
	return &ProviderError{
		Provider: provider,
		Op:       op,
		Err:      err,
	}
}

// RateLimitError represents a rate limit error with retry information.
type RateLimitError struct {
	// Provider is the name of the provider
	Provider string
	// RetryAfter is the number of seconds to wait before retrying
	RetryAfter int
	// Details provides additional context
	Details string
}

// Error implements the error interface.
func (e *RateLimitError) Error() string {
	msg := fmt.Sprintf("rate limit exceeded for provider '%s'", e.Provider)
	if e.RetryAfter > 0 {
		msg += fmt.Sprintf(" (retry after %ds)", e.RetryAfter)
	}
	if e.Details != "" {
		msg += fmt.Sprintf(": %s", e.Details)
	}
	return msg
}

// Unwrap returns the underlying sentinel error.
func (e *RateLimitError) Unwrap() error {
	return ErrProviderRateLimit
}

// AuthError represents an authentication error.
type AuthError struct {
	// Provider is the name of the provider
	Provider string
	// Details provides additional context
	Details string
}

// Error implements the error interface.
func (e *AuthError) Error() string {
	msg := fmt.Sprintf("authentication failed for provider '%s'", e.Provider)
	if e.Details != "" {
		msg += fmt.Sprintf(": %s", e.Details)
	}
	return msg
}

// Unwrap returns the underlying sentinel error.
func (e *AuthError) Unwrap() error {
	return ErrProviderAuth
}

// ConnectionError represents a connection error.
type ConnectionError struct {
	// Provider is the name of the provider
	Provider string
	// Details provides additional context
	Details string
}

// Error implements the error interface.
func (e *ConnectionError) Error() string {
	msg := fmt.Sprintf("connection failed for provider '%s'", e.Provider)
	if e.Details != "" {
		msg += fmt.Sprintf(": %s", e.Details)
	}
	return msg
}

// Unwrap returns the underlying sentinel error.
func (e *ConnectionError) Unwrap() error {
	return ErrProviderConnection
}

// GameNotFoundError represents a game not found error.
type GameNotFoundError struct {
	// SearchTerm is the search term that was used
	SearchTerm string
	// Provider is the provider that was searched (optional)
	Provider string
}

// Error implements the error interface.
func (e *GameNotFoundError) Error() string {
	msg := fmt.Sprintf("game not found: '%s'", e.SearchTerm)
	if e.Provider != "" {
		msg += fmt.Sprintf(" in provider '%s'", e.Provider)
	}
	return msg
}

// Unwrap returns the underlying sentinel error.
func (e *GameNotFoundError) Unwrap() error {
	return ErrGameNotFound
}

// ConfigError represents a configuration error.
type ConfigError struct {
	// Field is the configuration field with the error
	Field string
	// Details provides additional context
	Details string
}

// Error implements the error interface.
func (e *ConfigError) Error() string {
	if e.Field != "" {
		return fmt.Sprintf("invalid configuration for '%s': %s", e.Field, e.Details)
	}
	return fmt.Sprintf("invalid configuration: %s", e.Details)
}

// Unwrap returns the underlying sentinel error.
func (e *ConfigError) Unwrap() error {
	return ErrInvalidConfig
}

// CacheError represents a cache operation error.
type CacheError struct {
	// Op is the operation that failed
	Op string
	// Details provides additional context
	Details string
}

// Error implements the error interface.
func (e *CacheError) Error() string {
	msg := fmt.Sprintf("cache %s failed", e.Op)
	if e.Details != "" {
		msg += fmt.Sprintf(": %s", e.Details)
	}
	return msg
}

// Unwrap returns the underlying sentinel error.
func (e *CacheError) Unwrap() error {
	return ErrCacheOperation
}
