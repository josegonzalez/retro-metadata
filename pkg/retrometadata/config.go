package retrometadata

import "sort"

// ProviderConfig contains configuration for an individual metadata provider.
type ProviderConfig struct {
	// Enabled indicates whether this provider is enabled
	Enabled bool `json:"enabled"`
	// Credentials contains provider-specific credentials
	Credentials map[string]string `json:"credentials,omitempty"`
	// Priority is the priority order for this provider (lower = higher priority)
	Priority int `json:"priority"`
	// Timeout is the request timeout in seconds
	Timeout int `json:"timeout"`
	// RateLimit is the maximum requests per second (0 = unlimited)
	RateLimit float64 `json:"rate_limit"`
	// Options contains additional provider-specific options
	Options map[string]any `json:"options,omitempty"`
}

// GetCredential returns a credential value by key.
func (c *ProviderConfig) GetCredential(key string) string {
	if c.Credentials == nil {
		return ""
	}
	return c.Credentials[key]
}

// IsConfigured returns true if the provider has credentials configured.
func (c *ProviderConfig) IsConfigured() bool {
	return c.Enabled && len(c.Credentials) > 0
}

// DefaultProviderConfig returns a default provider configuration.
func DefaultProviderConfig() ProviderConfig {
	return ProviderConfig{
		Enabled:  false,
		Priority: 100,
		Timeout:  30,
	}
}

// CacheConfig contains configuration for the cache backend.
type CacheConfig struct {
	// Backend is the cache backend type ("memory", "redis", "sqlite")
	Backend string `json:"backend"`
	// TTL is the default time-to-live in seconds
	TTL int `json:"ttl"`
	// MaxSize is the maximum number of entries for memory cache
	MaxSize int `json:"max_size"`
	// ConnectionString is the connection string for redis/sqlite backends
	ConnectionString string `json:"connection_string,omitempty"`
	// Options contains additional backend-specific options
	Options map[string]any `json:"options,omitempty"`
}

// DefaultCacheConfig returns a default cache configuration.
func DefaultCacheConfig() CacheConfig {
	return CacheConfig{
		Backend: "memory",
		TTL:     3600, // 1 hour
		MaxSize: 10000,
	}
}

// Config is the main configuration for the Client.
type Config struct {
	// Provider configurations
	IGDB              ProviderConfig `json:"igdb"`
	MobyGames         ProviderConfig `json:"mobygames"`
	ScreenScraper     ProviderConfig `json:"screenscraper"`
	RetroAchievements ProviderConfig `json:"retroachievements"`
	SteamGridDB       ProviderConfig `json:"steamgriddb"`
	HLTB              ProviderConfig `json:"hltb"`
	LaunchBox         ProviderConfig `json:"launchbox"`
	Hasheous          ProviderConfig `json:"hasheous"`
	TheGamesDB        ProviderConfig `json:"thegamesdb"`
	Flashpoint        ProviderConfig `json:"flashpoint"`
	Playmatch         ProviderConfig `json:"playmatch"`
	Gamelist          ProviderConfig `json:"gamelist"`

	// Cache is the cache configuration
	Cache CacheConfig `json:"cache"`

	// DefaultTimeout is the default request timeout in seconds
	DefaultTimeout int `json:"default_timeout"`
	// MaxConcurrentRequests is the maximum concurrent requests across all providers
	MaxConcurrentRequests int `json:"max_concurrent_requests"`
	// UserAgent is the user agent string for HTTP requests
	UserAgent string `json:"user_agent"`
	// PreferredLocale is the preferred locale for localized content
	PreferredLocale string `json:"preferred_locale,omitempty"`
	// RegionPriority is the list of region codes in priority order
	RegionPriority []string `json:"region_priority"`
}

// DefaultConfig returns a configuration with sensible defaults.
func DefaultConfig() Config {
	return Config{
		IGDB:                  DefaultProviderConfig(),
		MobyGames:             DefaultProviderConfig(),
		ScreenScraper:         DefaultProviderConfig(),
		RetroAchievements:     DefaultProviderConfig(),
		SteamGridDB:           DefaultProviderConfig(),
		HLTB:                  DefaultProviderConfig(),
		LaunchBox:             DefaultProviderConfig(),
		Hasheous:              DefaultProviderConfig(),
		TheGamesDB:            DefaultProviderConfig(),
		Flashpoint:            DefaultProviderConfig(),
		Playmatch:             DefaultProviderConfig(),
		Gamelist:              DefaultProviderConfig(),
		Cache:                 DefaultCacheConfig(),
		DefaultTimeout:        30,
		MaxConcurrentRequests: 10,
		UserAgent:             "retro-metadata/1.0",
		RegionPriority:        []string{"us", "wor", "eu", "jp"},
	}
}

// GetEnabledProviders returns a list of enabled provider names sorted by priority.
func (c *Config) GetEnabledProviders() []string {
	type providerPriority struct {
		name     string
		priority int
	}

	providers := []providerPriority{}

	providerConfigs := map[string]ProviderConfig{
		"igdb":              c.IGDB,
		"mobygames":         c.MobyGames,
		"screenscraper":     c.ScreenScraper,
		"retroachievements": c.RetroAchievements,
		"steamgriddb":       c.SteamGridDB,
		"hltb":              c.HLTB,
		"launchbox":         c.LaunchBox,
		"hasheous":          c.Hasheous,
		"thegamesdb":        c.TheGamesDB,
		"flashpoint":        c.Flashpoint,
		"playmatch":         c.Playmatch,
		"gamelist":          c.Gamelist,
	}

	for name, config := range providerConfigs {
		if config.Enabled {
			providers = append(providers, providerPriority{name: name, priority: config.Priority})
		}
	}

	// Sort by priority (lower = higher priority)
	sort.Slice(providers, func(i, j int) bool {
		return providers[i].priority < providers[j].priority
	})

	result := make([]string, len(providers))
	for i, p := range providers {
		result[i] = p.name
	}

	return result
}

// GetProviderConfig returns the configuration for a specific provider.
func (c *Config) GetProviderConfig(name string) *ProviderConfig {
	switch name {
	case "igdb":
		return &c.IGDB
	case "mobygames":
		return &c.MobyGames
	case "screenscraper":
		return &c.ScreenScraper
	case "retroachievements":
		return &c.RetroAchievements
	case "steamgriddb":
		return &c.SteamGridDB
	case "hltb":
		return &c.HLTB
	case "launchbox":
		return &c.LaunchBox
	case "hasheous":
		return &c.Hasheous
	case "thegamesdb":
		return &c.TheGamesDB
	case "flashpoint":
		return &c.Flashpoint
	case "playmatch":
		return &c.Playmatch
	case "gamelist":
		return &c.Gamelist
	default:
		return nil
	}
}

// Option is a functional option for configuring the Client.
type Option func(*Config)

// WithIGDB configures the IGDB provider.
func WithIGDB(clientID, clientSecret string) Option {
	return func(c *Config) {
		c.IGDB.Enabled = true
		c.IGDB.Credentials = map[string]string{
			"client_id":     clientID,
			"client_secret": clientSecret,
		}
		c.IGDB.Priority = 1
	}
}

// WithMobyGames configures the MobyGames provider.
func WithMobyGames(apiKey string) Option {
	return func(c *Config) {
		c.MobyGames.Enabled = true
		c.MobyGames.Credentials = map[string]string{
			"api_key": apiKey,
		}
		c.MobyGames.Priority = 2
	}
}

// WithScreenScraper configures the ScreenScraper provider.
func WithScreenScraper(devID, devPassword, ssID, ssPassword string) Option {
	return func(c *Config) {
		c.ScreenScraper.Enabled = true
		c.ScreenScraper.Credentials = map[string]string{
			"devid":       devID,
			"devpassword": devPassword,
			"ssid":        ssID,
			"sspassword":  ssPassword,
		}
		c.ScreenScraper.Priority = 3
	}
}

// WithRetroAchievements configures the RetroAchievements provider.
func WithRetroAchievements(username, apiKey string) Option {
	return func(c *Config) {
		c.RetroAchievements.Enabled = true
		c.RetroAchievements.Credentials = map[string]string{
			"username": username,
			"api_key":  apiKey,
		}
		c.RetroAchievements.Priority = 4
	}
}

// WithSteamGridDB configures the SteamGridDB provider.
func WithSteamGridDB(apiKey string) Option {
	return func(c *Config) {
		c.SteamGridDB.Enabled = true
		c.SteamGridDB.Credentials = map[string]string{
			"api_key": apiKey,
		}
		c.SteamGridDB.Priority = 5
	}
}

// WithHLTB enables the HowLongToBeat provider.
func WithHLTB() Option {
	return func(c *Config) {
		c.HLTB.Enabled = true
		c.HLTB.Priority = 10
	}
}

// WithCache configures the cache backend.
func WithCache(backend string, ttl, maxSize int) Option {
	return func(c *Config) {
		c.Cache.Backend = backend
		c.Cache.TTL = ttl
		c.Cache.MaxSize = maxSize
	}
}

// WithRedisCache configures a Redis cache backend.
func WithRedisCache(connectionString string, ttl int) Option {
	return func(c *Config) {
		c.Cache.Backend = "redis"
		c.Cache.ConnectionString = connectionString
		c.Cache.TTL = ttl
	}
}

// WithSQLiteCache configures a SQLite cache backend.
func WithSQLiteCache(dbPath string, ttl int) Option {
	return func(c *Config) {
		c.Cache.Backend = "sqlite"
		c.Cache.ConnectionString = dbPath
		c.Cache.TTL = ttl
	}
}

// WithUserAgent sets the user agent string.
func WithUserAgent(userAgent string) Option {
	return func(c *Config) {
		c.UserAgent = userAgent
	}
}

// WithTimeout sets the default timeout.
func WithTimeout(seconds int) Option {
	return func(c *Config) {
		c.DefaultTimeout = seconds
	}
}

// WithMaxConcurrentRequests sets the maximum concurrent requests.
func WithMaxConcurrentRequests(max int) Option {
	return func(c *Config) {
		c.MaxConcurrentRequests = max
	}
}

// WithPreferredLocale sets the preferred locale.
func WithPreferredLocale(locale string) Option {
	return func(c *Config) {
		c.PreferredLocale = locale
	}
}

// WithRegionPriority sets the region priority order.
func WithRegionPriority(regions []string) Option {
	return func(c *Config) {
		c.RegionPriority = regions
	}
}
