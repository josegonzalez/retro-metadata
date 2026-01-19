// Package retrometadata provides a unified interface for fetching game metadata
// from various providers like IGDB, MobyGames, ScreenScraper, and more.
package retrometadata

import "time"

// Platform represents a gaming platform.
type Platform struct {
	// Slug is the universal platform identifier (e.g., "snes", "ps2")
	Slug string `json:"slug"`
	// Name is the human-readable platform name
	Name string `json:"name"`
	// ProviderIDs maps provider names to their platform IDs
	ProviderIDs map[string]int `json:"provider_ids,omitempty"`
}

// AgeRating represents an age rating for a game.
type AgeRating struct {
	// Rating is the rating value (e.g., "E", "T", "M", "PEGI 12")
	Rating string `json:"rating"`
	// Category is the rating system (e.g., "ESRB", "PEGI", "CERO")
	Category string `json:"category"`
	// CoverURL is the URL to the rating icon/image
	CoverURL string `json:"cover_url,omitempty"`
}

// MultiplayerMode represents multiplayer capabilities for a game on a specific platform.
type MultiplayerMode struct {
	Platform           *Platform `json:"platform,omitempty"`
	CampaignCoop       bool      `json:"campaign_coop"`
	DropIn             bool      `json:"drop_in"`
	LANCoop            bool      `json:"lan_coop"`
	OfflineCoop        bool      `json:"offline_coop"`
	OfflineCoopMax     int       `json:"offline_coop_max"`
	OfflineMax         int       `json:"offline_max"`
	OnlineCoop         bool      `json:"online_coop"`
	OnlineCoopMax      int       `json:"online_coop_max"`
	OnlineMax          int       `json:"online_max"`
	SplitScreen        bool      `json:"split_screen"`
	SplitScreenOnline  bool      `json:"split_screen_online"`
}

// RelatedGame represents a related game (DLC, expansion, remake, etc.).
type RelatedGame struct {
	// ID is the provider-specific ID
	ID int `json:"id"`
	// Name is the game name
	Name string `json:"name"`
	// Slug is the URL-friendly slug
	Slug string `json:"slug,omitempty"`
	// RelationType is the type of relation (expansion, dlc, remaster, remake, port, similar)
	RelationType string `json:"relation_type,omitempty"`
	// CoverURL is the URL to cover art
	CoverURL string `json:"cover_url,omitempty"`
	// Provider is the provider name this came from
	Provider string `json:"provider,omitempty"`
}

// Artwork contains game artwork URLs.
type Artwork struct {
	// CoverURL is the URL to the main cover art
	CoverURL string `json:"cover_url,omitempty"`
	// ScreenshotURLs is a list of screenshot URLs
	ScreenshotURLs []string `json:"screenshot_urls,omitempty"`
	// BannerURL is the URL to a banner image
	BannerURL string `json:"banner_url,omitempty"`
	// IconURL is the URL to an icon image
	IconURL string `json:"icon_url,omitempty"`
	// LogoURL is the URL to the game logo
	LogoURL string `json:"logo_url,omitempty"`
	// BackgroundURL is the URL to a background image
	BackgroundURL string `json:"background_url,omitempty"`
}

// GameMetadata contains extended metadata for a game.
type GameMetadata struct {
	// TotalRating is the aggregated user rating (0-100)
	TotalRating *float64 `json:"total_rating,omitempty"`
	// AggregatedRating is the critic aggregated rating (0-100)
	AggregatedRating *float64 `json:"aggregated_rating,omitempty"`
	// FirstReleaseDate is the Unix timestamp of first release
	FirstReleaseDate *int64 `json:"first_release_date,omitempty"`
	// YouTubeVideoID is the YouTube video ID for trailer
	YouTubeVideoID string `json:"youtube_video_id,omitempty"`
	// Genres is a list of genre names
	Genres []string `json:"genres,omitempty"`
	// Franchises is a list of franchise names
	Franchises []string `json:"franchises,omitempty"`
	// AlternativeNames is a list of alternative titles
	AlternativeNames []string `json:"alternative_names,omitempty"`
	// Collections is a list of game collections/series
	Collections []string `json:"collections,omitempty"`
	// Companies is a list of companies involved
	Companies []string `json:"companies,omitempty"`
	// GameModes is a list of game modes
	GameModes []string `json:"game_modes,omitempty"`
	// AgeRatings is a list of age ratings
	AgeRatings []AgeRating `json:"age_ratings,omitempty"`
	// Platforms is a list of platforms
	Platforms []Platform `json:"platforms,omitempty"`
	// MultiplayerModes is multiplayer capabilities per platform
	MultiplayerModes []MultiplayerMode `json:"multiplayer_modes,omitempty"`
	// PlayerCount is the human-readable player count string
	PlayerCount string `json:"player_count,omitempty"`
	// Expansions is related expansion games
	Expansions []RelatedGame `json:"expansions,omitempty"`
	// DLCs is related DLC content
	DLCs []RelatedGame `json:"dlcs,omitempty"`
	// Remasters is related remastered versions
	Remasters []RelatedGame `json:"remasters,omitempty"`
	// Remakes is related remakes
	Remakes []RelatedGame `json:"remakes,omitempty"`
	// ExpandedGames is related expanded editions
	ExpandedGames []RelatedGame `json:"expanded_games,omitempty"`
	// Ports is related ports to other platforms
	Ports []RelatedGame `json:"ports,omitempty"`
	// SimilarGames is similar games
	SimilarGames []RelatedGame `json:"similar_games,omitempty"`
	// Developer is the primary developer name
	Developer string `json:"developer,omitempty"`
	// Publisher is the primary publisher name
	Publisher string `json:"publisher,omitempty"`
	// ReleaseYear is the release year
	ReleaseYear *int `json:"release_year,omitempty"`
	// RawData is the original provider-specific data
	RawData map[string]any `json:"raw_data,omitempty"`
}

// GameResult represents a game result from metadata lookup.
// This is the main type returned by the Client for game lookups.
type GameResult struct {
	// Name is the game name
	Name string `json:"name"`
	// Summary is the game description/summary
	Summary string `json:"summary,omitempty"`
	// Provider is the provider name this result came from
	Provider string `json:"provider,omitempty"`
	// ProviderID is the provider-specific game ID
	ProviderID *int `json:"provider_id,omitempty"`
	// ProviderIDs maps provider names to IDs
	ProviderIDs map[string]int `json:"provider_ids,omitempty"`
	// Slug is the URL-friendly slug
	Slug string `json:"slug,omitempty"`
	// Artwork is the game artwork URLs
	Artwork Artwork `json:"artwork"`
	// Metadata is the extended metadata
	Metadata GameMetadata `json:"metadata"`
	// MatchScore is the similarity score if result was from a search (0-1)
	MatchScore float64 `json:"match_score,omitempty"`
	// MatchType is the type of match (hash+filename, hash, filename, etc.)
	MatchType string `json:"match_type,omitempty"`
	// RawResponse is the raw provider response for debugging
	RawResponse map[string]any `json:"raw_response,omitempty"`
}

// CoverURL returns the cover URL for convenience.
func (g *GameResult) CoverURL() string {
	return g.Artwork.CoverURL
}

// ScreenshotURLs returns the screenshot URLs for convenience.
func (g *GameResult) ScreenshotURLs() []string {
	return g.Artwork.ScreenshotURLs
}

// SearchResult represents a search result with minimal information.
// Used for displaying search results before fetching full details.
type SearchResult struct {
	// Name is the game name
	Name string `json:"name"`
	// Provider is the provider name
	Provider string `json:"provider"`
	// ProviderID is the provider-specific ID
	ProviderID int `json:"provider_id"`
	// Slug is the URL-friendly slug
	Slug string `json:"slug,omitempty"`
	// CoverURL is the URL to cover art thumbnail
	CoverURL string `json:"cover_url,omitempty"`
	// Platforms is the platforms the game is available on
	Platforms []string `json:"platforms,omitempty"`
	// ReleaseYear is the release year if known
	ReleaseYear *int `json:"release_year,omitempty"`
	// MatchScore is the similarity score (0-1)
	MatchScore float64 `json:"match_score,omitempty"`
}

// SearchOptions contains options for search operations.
type SearchOptions struct {
	// PlatformID is the provider-specific platform ID to filter by
	PlatformID *int
	// Limit is the maximum number of results to return
	Limit int
	// MinScore is the minimum similarity score for fuzzy matching
	MinScore float64
}

// DefaultSearchOptions returns sensible default search options.
func DefaultSearchOptions() SearchOptions {
	return SearchOptions{
		Limit:    10,
		MinScore: 0.75,
	}
}

// IdentifyOptions contains options for identify operations.
type IdentifyOptions struct {
	// PlatformID is the provider-specific platform ID
	PlatformID *int
	// Hashes contains file hashes for hash-based identification
	Hashes *FileHashes
}

// FileHashes contains various hash values for a ROM file.
type FileHashes struct {
	MD5    string `json:"md5,omitempty"`
	SHA1   string `json:"sha1,omitempty"`
	CRC32  string `json:"crc32,omitempty"`
	SHA256 string `json:"sha256,omitempty"`
}

// ProviderStatus represents the health status of a provider.
type ProviderStatus struct {
	// Name is the provider name
	Name string `json:"name"`
	// Available indicates if the provider API is accessible
	Available bool `json:"available"`
	// LastCheck is the time of the last health check
	LastCheck time.Time `json:"last_check"`
	// Error contains the error message if unavailable
	Error string `json:"error,omitempty"`
}
