#pragma once

/// @file errors.hpp
/// @brief Error types and exception classes for the retro-metadata library

#include <exception>
#include <string>

namespace retro_metadata {

/// @brief Error codes for categorizing errors
enum class ErrorCode {
    None = 0,
    ProviderNotFound,
    ProviderAuth,
    ProviderConnection,
    ProviderRateLimit,
    GameNotFound,
    InvalidConfig,
    CacheOperation
};

/// @brief Base exception class for all retro-metadata errors
class RetroMetadataError : public std::exception {
public:
    explicit RetroMetadataError(std::string message, ErrorCode code = ErrorCode::None)
        : message_(std::move(message)), code_(code) {}

    [[nodiscard]] const char* what() const noexcept override { return message_.c_str(); }
    [[nodiscard]] ErrorCode code() const noexcept { return code_; }

protected:
    std::string message_;
    ErrorCode code_;
};

/// @brief Error wrapping provider context
class ProviderError : public RetroMetadataError {
public:
    ProviderError(std::string provider, std::string op, std::string details)
        : RetroMetadataError(format_message(provider, op, details), ErrorCode::ProviderNotFound),
          provider_(std::move(provider)),
          op_(std::move(op)),
          details_(std::move(details)) {}

    [[nodiscard]] const std::string& provider() const noexcept { return provider_; }
    [[nodiscard]] const std::string& op() const noexcept { return op_; }
    [[nodiscard]] const std::string& details() const noexcept { return details_; }

private:
    static std::string format_message(
        const std::string& provider, const std::string& op, const std::string& details) {
        if (!op.empty()) {
            return provider + ": " + op + ": " + details;
        }
        return provider + ": " + details;
    }

    std::string provider_;
    std::string op_;
    std::string details_;
};

/// @brief Rate limit error with retry information
class RateLimitError : public RetroMetadataError {
public:
    RateLimitError(std::string provider, int retry_after = 0, std::string details = "")
        : RetroMetadataError(
              format_message(provider, retry_after, details), ErrorCode::ProviderRateLimit),
          provider_(std::move(provider)),
          retry_after_(retry_after),
          details_(std::move(details)) {}

    [[nodiscard]] const std::string& provider() const noexcept { return provider_; }
    [[nodiscard]] int retry_after() const noexcept { return retry_after_; }
    [[nodiscard]] const std::string& details() const noexcept { return details_; }

private:
    static std::string format_message(
        const std::string& provider, int retry_after, const std::string& details) {
        std::string msg = "rate limit exceeded for provider '" + provider + "'";
        if (retry_after > 0) {
            msg += " (retry after " + std::to_string(retry_after) + "s)";
        }
        if (!details.empty()) {
            msg += ": " + details;
        }
        return msg;
    }

    std::string provider_;
    int retry_after_;
    std::string details_;
};

/// @brief Authentication error
class AuthError : public RetroMetadataError {
public:
    AuthError(std::string provider, std::string details = "")
        : RetroMetadataError(format_message(provider, details), ErrorCode::ProviderAuth),
          provider_(std::move(provider)),
          details_(std::move(details)) {}

    [[nodiscard]] const std::string& provider() const noexcept { return provider_; }
    [[nodiscard]] const std::string& details() const noexcept { return details_; }

private:
    static std::string format_message(const std::string& provider, const std::string& details) {
        std::string msg = "authentication failed for provider '" + provider + "'";
        if (!details.empty()) {
            msg += ": " + details;
        }
        return msg;
    }

    std::string provider_;
    std::string details_;
};

/// @brief Connection error
class ConnectionError : public RetroMetadataError {
public:
    ConnectionError(std::string provider, std::string details = "")
        : RetroMetadataError(format_message(provider, details), ErrorCode::ProviderConnection),
          provider_(std::move(provider)),
          details_(std::move(details)) {}

    [[nodiscard]] const std::string& provider() const noexcept { return provider_; }
    [[nodiscard]] const std::string& details() const noexcept { return details_; }

private:
    static std::string format_message(const std::string& provider, const std::string& details) {
        std::string msg = "connection failed for provider '" + provider + "'";
        if (!details.empty()) {
            msg += ": " + details;
        }
        return msg;
    }

    std::string provider_;
    std::string details_;
};

/// @brief Game not found error
class GameNotFoundError : public RetroMetadataError {
public:
    GameNotFoundError(std::string search_term, std::string provider = "")
        : RetroMetadataError(format_message(search_term, provider), ErrorCode::GameNotFound),
          search_term_(std::move(search_term)),
          provider_(std::move(provider)) {}

    [[nodiscard]] const std::string& search_term() const noexcept { return search_term_; }
    [[nodiscard]] const std::string& provider() const noexcept { return provider_; }

private:
    static std::string format_message(
        const std::string& search_term, const std::string& provider) {
        std::string msg = "game not found: '" + search_term + "'";
        if (!provider.empty()) {
            msg += " in provider '" + provider + "'";
        }
        return msg;
    }

    std::string search_term_;
    std::string provider_;
};

/// @brief Configuration error
class ConfigError : public RetroMetadataError {
public:
    ConfigError(std::string field, std::string details)
        : RetroMetadataError(format_message(field, details), ErrorCode::InvalidConfig),
          field_(std::move(field)),
          details_(std::move(details)) {}

    [[nodiscard]] const std::string& field() const noexcept { return field_; }
    [[nodiscard]] const std::string& details() const noexcept { return details_; }

private:
    static std::string format_message(const std::string& field, const std::string& details) {
        if (!field.empty()) {
            return "invalid configuration for '" + field + "': " + details;
        }
        return "invalid configuration: " + details;
    }

    std::string field_;
    std::string details_;
};

/// @brief Cache operation error
class CacheError : public RetroMetadataError {
public:
    CacheError(std::string op, std::string details = "")
        : RetroMetadataError(format_message(op, details), ErrorCode::CacheOperation),
          op_(std::move(op)),
          details_(std::move(details)) {}

    [[nodiscard]] const std::string& op() const noexcept { return op_; }
    [[nodiscard]] const std::string& details() const noexcept { return details_; }

private:
    static std::string format_message(const std::string& op, const std::string& details) {
        std::string msg = "cache " + op + " failed";
        if (!details.empty()) {
            msg += ": " + details;
        }
        return msg;
    }

    std::string op_;
    std::string details_;
};

}  // namespace retro_metadata
