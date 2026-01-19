"""Main artwork download logic."""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from retro_metadata.artwork.cache import ArtworkCache, CachedArtwork
from retro_metadata.artwork.config import ARTWORK_TYPES, ArtworkConfig
from retro_metadata.artwork.exceptions import (
    ArtworkDownloadError,
    ArtworkNotFoundError,
    ArtworkTimeoutError,
    InvalidArtworkTypeError,
)
from retro_metadata.artwork.utils import (
    generate_output_filename,
    get_extension_from_content_type,
    get_extension_from_url,
    sanitize_filename,
    transform_url_for_size,
)

if TYPE_CHECKING:
    from retro_metadata.core.client import MetadataClient
    from retro_metadata.types.common import Artwork, GameResult

logger = logging.getLogger(__name__)

# Common ROM extensions by platform
ROM_EXTENSIONS: dict[str, list[str]] = {
    "snes": [".sfc", ".smc", ".fig", ".swc"],
    "nes": [".nes", ".unf", ".unif"],
    "n64": [".n64", ".v64", ".z64"],
    "gb": [".gb"],
    "gbc": [".gbc"],
    "gba": [".gba"],
    "nds": [".nds"],
    "3ds": [".3ds", ".cia"],
    "genesis": [".gen", ".md", ".smd", ".bin"],
    "megadrive": [".gen", ".md", ".smd", ".bin"],
    "sega32x": [".32x"],
    "segacd": [".iso", ".cue", ".bin"],
    "mastersystem": [".sms"],
    "gamegear": [".gg"],
    "saturn": [".iso", ".cue", ".bin"],
    "dreamcast": [".gdi", ".cdi", ".chd"],
    "psx": [".iso", ".bin", ".cue", ".chd", ".pbp"],
    "ps2": [".iso", ".bin", ".chd"],
    "psp": [".iso", ".cso", ".pbp"],
    "arcade": [".zip"],
    "mame": [".zip"],
    "neogeo": [".zip"],
    "atari2600": [".a26", ".bin"],
    "atari5200": [".a52", ".bin"],
    "atari7800": [".a78", ".bin"],
    "jaguar": [".j64", ".jag"],
    "lynx": [".lnx"],
    "pcengine": [".pce"],
    "turbografx16": [".pce"],
    "supergrafx": [".sgx"],
    "wonderswan": [".ws"],
    "wonderswancolor": [".wsc"],
    "ngp": [".ngp"],
    "ngpc": [".ngc"],
    "vectrex": [".vec"],
    "colecovision": [".col"],
    "intellivision": [".int"],
    "msx": [".rom", ".mx1", ".mx2"],
    "msx2": [".rom", ".mx1", ".mx2"],
    "zxspectrum": [".tap", ".tzx", ".z80", ".sna"],
    "amstradcpc": [".dsk", ".cdt", ".sna"],
    "c64": [".d64", ".t64", ".prg", ".crt"],
    "amiga": [".adf", ".ipf", ".dms"],
}

# All extensions for auto-detection
ALL_ROM_EXTENSIONS: set[str] = set()
for _exts in ROM_EXTENSIONS.values():
    ALL_ROM_EXTENSIONS.update(_exts)


def _get_rom_extensions_for_platform(platform: str) -> set[str]:
    """Get ROM extensions for a platform.

    Args:
        platform: Platform slug

    Returns:
        Set of file extensions
    """
    if platform in ROM_EXTENSIONS:
        return set(ROM_EXTENSIONS[platform])
    return ALL_ROM_EXTENSIONS


@dataclass
class ArtworkDownloadResult:
    """Result of a single artwork download.

    Attributes:
        artwork_type: Type of artwork (cover, screenshot, etc.)
        url: Original URL
        path: Path where artwork was saved
        from_cache: Whether artwork came from cache
        provider: Provider name
        width: Image width in pixels
        height: Image height in pixels
    """

    artwork_type: str
    url: str
    path: Path
    from_cache: bool
    provider: str
    width: int | None = None
    height: int | None = None


@dataclass
class ArtworkBatchResult:
    """Result of a batch artwork download operation.

    Attributes:
        successful: List of successful downloads
        failed: List of failed downloads with error info
        skipped: List of files that were skipped (no artwork found)
        total_files: Total number of files processed
        from_cache: Number of downloads served from cache
    """

    successful: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    total_files: int = 0
    from_cache: int = 0


class ArtworkDownloader:
    """Downloads artwork from metadata providers with caching support."""

    def __init__(
        self,
        client: MetadataClient,
        config: ArtworkConfig | None = None,
    ) -> None:
        """Initialize the artwork downloader.

        Args:
            client: MetadataClient instance for fetching game metadata
            config: Artwork configuration (uses defaults if None)
        """
        self.client = client
        self.config = config or ArtworkConfig()
        self._cache = ArtworkCache(self.config)
        self._http_client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None

    async def __aenter__(self) -> ArtworkDownloader:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
        return self._http_client

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create concurrency semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        return self._semaphore

    def _validate_artwork_types(self, artwork_types: list[str]) -> None:
        """Validate that all artwork types are valid."""
        for artwork_type in artwork_types:
            if artwork_type not in ARTWORK_TYPES:
                raise InvalidArtworkTypeError(artwork_type, list(ARTWORK_TYPES))

    def _add_screenscraper_auth(self, url: str) -> str:
        """Add ScreenScraper authentication to a URL.

        Args:
            url: The URL to authenticate

        Returns:
            URL with authentication parameters added
        """
        try:
            ss_provider = self.client._providers.get("screenscraper")
            if ss_provider and hasattr(ss_provider, "add_auth_to_url"):
                return ss_provider.add_auth_to_url(url)
        except Exception as e:
            logger.debug("Failed to add ScreenScraper auth: %s", e)
        return url

    def _mask_sensitive_url(self, url: str) -> str:
        """Mask sensitive parameters in URL for logging.

        Args:
            url: URL that may contain sensitive params

        Returns:
            URL with sensitive params masked
        """
        import re
        # Mask common auth params
        masked = re.sub(r"(ssid|sspassword|devid|devpassword|password)=[^&]+", r"\1=***", url)
        return masked

    def _get_artwork_url(
        self,
        artwork: Artwork,
        artwork_type: str,
        index: int = 0,
    ) -> str | None:
        """Get artwork URL from Artwork object by type.

        Args:
            artwork: Artwork object
            artwork_type: Type of artwork to get
            index: Index for types that have multiple (screenshots)

        Returns:
            URL string or None if not available
        """
        if artwork_type == "cover":
            return artwork.cover_url or None
        elif artwork_type == "banner":
            return artwork.banner_url or None
        elif artwork_type == "icon":
            return artwork.icon_url or None
        elif artwork_type == "logo":
            return artwork.logo_url or None
        elif artwork_type == "background":
            return artwork.background_url or None
        elif artwork_type == "screenshots":
            urls = artwork.screenshot_urls
            if urls and index < len(urls):
                return urls[index]
            return None
        return None

    async def _download_image(
        self,
        url: str,
        provider: str,
    ) -> tuple[bytes, str | None]:
        """Download image from URL.

        Args:
            url: Image URL
            provider: Provider name (for size transformation)

        Returns:
            Tuple of (image_data, content_type)
        """
        # Transform URL for size constraints
        transformed_url = transform_url_for_size(
            url,
            provider,
            self.config.max_width,
            self.config.max_height,
        )

        # Add authentication for ScreenScraper URLs
        if provider == "screenscraper" or "screenscraper.fr" in transformed_url:
            transformed_url = self._add_screenscraper_auth(transformed_url)

        logger.debug("Downloading artwork from URL: %s", self._mask_sensitive_url(transformed_url))
        if transformed_url != url:
            logger.debug("Original URL was: %s", self._mask_sensitive_url(url))

        client = await self._get_http_client()

        try:
            response = await client.get(transformed_url)
            response.raise_for_status()

            content_type = response.headers.get("content-type")
            logger.debug(
                "Downloaded %d bytes (content-type: %s)",
                len(response.content),
                content_type,
            )
            return response.content, content_type

        except httpx.TimeoutException as e:
            logger.debug("Download timed out after %ds: %s", self.config.timeout, url)
            raise ArtworkTimeoutError(url, self.config.timeout) from e
        except httpx.HTTPStatusError as e:
            logger.debug("HTTP error %d for URL: %s", e.response.status_code, url)
            raise ArtworkDownloadError(
                url, provider, f"HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.debug("Request error for URL %s: %s", url, e)
            raise ArtworkDownloadError(url, provider, str(e)) from e

    async def download_for_game(
        self,
        game: GameResult,
        output_dir: Path,
        rom_filename: str | None = None,
        artwork_types: list[str] | None = None,
    ) -> dict[str, Path]:
        """Download artwork for a game.

        Args:
            game: GameResult object with artwork URLs
            output_dir: Directory to save artwork
            rom_filename: Original ROM filename (for output naming)
            artwork_types: List of artwork types to download (uses config default if None)

        Returns:
            Dictionary mapping artwork_type to saved file path
        """
        types_to_download = artwork_types or self.config.artwork_types
        self._validate_artwork_types(types_to_download)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Use game name if rom_filename not provided
        base_filename = rom_filename or sanitize_filename(game.name)

        results: dict[str, Path] = {}
        provider = game.provider

        for artwork_type in types_to_download:
            if artwork_type == "screenshots":
                # Handle multiple screenshots
                screenshot_urls = game.artwork.screenshot_urls
                for i, url in enumerate(screenshot_urls or []):
                    if not url:
                        continue

                    try:
                        result = await self._download_single(
                            url=url,
                            provider=provider,
                            output_dir=output_dir,
                            base_filename=base_filename,
                            artwork_type=f"screenshot_{i + 1}",
                        )
                        results[f"screenshot_{i + 1}"] = result.path
                    except ArtworkDownloadError:
                        # Continue with other screenshots on failure
                        pass
            else:
                url = self._get_artwork_url(game.artwork, artwork_type)
                if not url:
                    continue

                try:
                    result = await self._download_single(
                        url=url,
                        provider=provider,
                        output_dir=output_dir,
                        base_filename=base_filename,
                        artwork_type=artwork_type,
                    )
                    results[artwork_type] = result.path
                except ArtworkDownloadError:
                    # Continue with other artwork types on failure
                    pass

        return results

    async def _download_single(
        self,
        url: str,
        provider: str,
        output_dir: Path,
        base_filename: str,
        artwork_type: str,
    ) -> ArtworkDownloadResult:
        """Download a single artwork file.

        Args:
            url: Artwork URL
            provider: Provider name
            output_dir: Directory to save file
            base_filename: Base filename for output
            artwork_type: Type of artwork

        Returns:
            ArtworkDownloadResult
        """
        logger.debug(
            "Downloading %s artwork for '%s' from %s",
            artwork_type,
            base_filename,
            provider,
        )

        semaphore = self._get_semaphore()

        async with semaphore:
            # Check cache first
            if self.config.cache_enabled:
                cached = await self._cache.get(url)
                if cached and cached.path.exists():
                    logger.debug("Cache hit for URL: %s", url)
                    # Copy from cache to output
                    extension = cached.path.suffix
                    output_filename = generate_output_filename(
                        base_filename,
                        artwork_type,
                        extension,
                        self.config.filename_format,
                    )
                    output_path = output_dir / output_filename
                    shutil.copy2(cached.path, output_path)
                    logger.debug("Copied cached file to: %s", output_path)

                    return ArtworkDownloadResult(
                        artwork_type=artwork_type,
                        url=url,
                        path=output_path,
                        from_cache=True,
                        provider=provider,
                        width=cached.width,
                        height=cached.height,
                    )

            logger.debug("Cache miss, downloading from URL: %s", url)

            # Download image
            data, content_type = await self._download_image(url, provider)

            # Determine extension
            if content_type:
                extension = get_extension_from_content_type(content_type)
            else:
                extension = get_extension_from_url(url)

            # Generate output filename
            output_filename = generate_output_filename(
                base_filename,
                artwork_type,
                extension,
                self.config.filename_format,
            )
            output_path = output_dir / output_filename

            # Write file
            output_path.write_bytes(data)
            logger.debug("Saved artwork to: %s", output_path)

            # Cache the downloaded image
            cached_artwork: CachedArtwork | None = None
            if self.config.cache_enabled:
                cached_artwork = await self._cache.put(url, provider, data, content_type)
                logger.debug("Cached artwork for future use")

            return ArtworkDownloadResult(
                artwork_type=artwork_type,
                url=url,
                path=output_path,
                from_cache=False,
                provider=provider,
                width=cached_artwork.width if cached_artwork else None,
                height=cached_artwork.height if cached_artwork else None,
            )

    async def download_with_fallback(
        self,
        filename: str,
        platform: str,
        output_dir: Path,
        identify_providers: list[str] | None = None,
        artwork_providers: list[str] | None = None,
        artwork_types: list[str] | None = None,
        game_name: str | None = None,
    ) -> dict[str, Path]:
        """Download artwork with cross-provider matching.

        Identifies the game using one set of providers, then fetches artwork
        from potentially different providers.

        Args:
            filename: ROM filename (can be full path, basename will be extracted)
            platform: Platform slug
            output_dir: Directory to save artwork
            identify_providers: Providers to use for game identification
            artwork_providers: Providers to use for artwork download
            artwork_types: Types of artwork to download
            game_name: If provided, skip identification and use this name to search
                       in artwork providers directly

        Returns:
            Dictionary mapping artwork_type to saved file path
        """
        types_to_download = artwork_types or self.config.artwork_types
        self._validate_artwork_types(types_to_download)

        # Extract just the filename if a full path was provided
        rom_filename = Path(filename).name
        logger.debug("Processing artwork download for: %s", rom_filename)
        logger.debug("Platform: %s, artwork types: %s", platform, types_to_download)

        # If game_name is provided, skip identification and use it directly
        if game_name:
            logger.debug(
                "Using pre-identified game name: '%s' (skipping identification)",
                game_name,
            )
            identified_name = game_name
            game = None  # No game object when using pre-identified name
        else:
            # Step 1: Identify game using identify_providers
            logger.debug(
                "Identifying game with providers: %s",
                identify_providers or "default",
            )
            game = await self.client.identify(
                filename=rom_filename,
                platform=platform,
                providers=identify_providers,
            )

            if not game:
                logger.debug("Game not identified for filename: %s", rom_filename)
                raise ArtworkNotFoundError(rom_filename, "any", None)

            identified_name = game.name

        if game:
            logger.debug(
                "Game identified: '%s' (provider: %s, id: %s)",
                game.name,
                game.provider,
                game.provider_id,
            )

            # Log available artwork URLs
            if game.artwork:
                if game.artwork.cover_url:
                    logger.debug("Cover URL available: %s", game.artwork.cover_url)
                else:
                    logger.debug("No cover URL available from %s", game.provider)
                if game.artwork.screenshot_urls:
                    logger.debug(
                        "Screenshot URLs available: %d",
                        len(game.artwork.screenshot_urls),
                    )

        # Step 2: Try to get artwork from artwork_providers
        if artwork_providers:
            logger.debug("Trying artwork providers: %s", artwork_providers)
            # Search for game in artwork providers by name
            for provider_name in artwork_providers:
                logger.debug(
                    "Searching for '%s' in provider: %s",
                    identified_name,
                    provider_name,
                )
                try:
                    search_results = await self.client.search(
                        query=identified_name,
                        platform=platform,
                        providers=[provider_name],
                        limit=1,
                    )

                    if search_results:
                        logger.debug(
                            "Found match in %s: %s (id: %s)",
                            provider_name,
                            search_results[0].name,
                            search_results[0].provider_id,
                        )
                        # Get full game details from this provider
                        artwork_game = await self.client.get_by_id(
                            provider=provider_name,
                            game_id=search_results[0].provider_id,
                        )

                        if artwork_game and artwork_game.artwork:
                            # Check if this provider has the artwork we need
                            has_artwork = False
                            for artwork_type in types_to_download:
                                url = self._get_artwork_url(
                                    artwork_game.artwork, artwork_type
                                )
                                if url:
                                    logger.debug(
                                        "Provider %s has %s artwork: %s",
                                        provider_name,
                                        artwork_type,
                                        url,
                                    )
                                    has_artwork = True
                                    break

                            if has_artwork:
                                return await self.download_for_game(
                                    game=artwork_game,
                                    output_dir=output_dir,
                                    rom_filename=rom_filename,
                                    artwork_types=types_to_download,
                                )
                            else:
                                logger.debug(
                                    "Provider %s has no matching artwork types",
                                    provider_name,
                                )
                    else:
                        logger.debug("No results from provider: %s", provider_name)
                except Exception as e:
                    logger.debug(
                        "Error searching provider %s: %s: %s",
                        provider_name,
                        type(e).__name__,
                        e,
                    )
                    # Continue to next provider on error
                    continue

        # If artwork_providers was explicitly specified but none worked, raise an error
        if artwork_providers:
            providers_str = ", ".join(artwork_providers)
            logger.debug(
                "All specified artwork providers (%s) failed to return artwork",
                providers_str,
            )
            raise ArtworkNotFoundError(
                game_name=rom_filename,
                artwork_type=", ".join(types_to_download),
                provider=providers_str,
            )

        # No artwork_providers specified, use original game's artwork
        return await self.download_for_game(
            game=game,
            output_dir=output_dir,
            rom_filename=rom_filename,
            artwork_types=types_to_download,
        )

    async def download_batch(
        self,
        directory: Path,
        platform: str,
        output_dir: Path,
        recursive: bool = False,
        extensions: list[str] | None = None,
        identify_providers: list[str] | None = None,
        artwork_providers: list[str] | None = None,
        artwork_types: list[str] | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ArtworkBatchResult:
        """Download artwork for a directory of ROM files.

        Args:
            directory: Directory containing ROM files
            platform: Platform slug
            output_dir: Directory to save artwork
            recursive: Whether to scan subdirectories
            extensions: File extensions to include (None = all common ROM extensions)
            identify_providers: Providers for game identification
            artwork_providers: Providers for artwork download
            artwork_types: Types of artwork to download
            progress_callback: Callback function(current, total, filename)

        Returns:
            ArtworkBatchResult with download statistics
        """
        types_to_download = artwork_types or self.config.artwork_types
        self._validate_artwork_types(types_to_download)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine extensions to scan
        if extensions:
            ext_set = {
                e.lower() if e.startswith(".") else f".{e.lower()}"
                for e in extensions
            }
        else:
            ext_set = _get_rom_extensions_for_platform(platform)

        # Find ROM files
        pattern = "**/*" if recursive else "*"
        rom_files = [
            f for f in directory.glob(pattern)
            if f.is_file() and f.suffix.lower() in ext_set
        ]
        rom_files = sorted(rom_files)

        result = ArtworkBatchResult(total_files=len(rom_files))

        for i, rom_path in enumerate(rom_files):
            if progress_callback:
                progress_callback(i + 1, len(rom_files), rom_path.name)

            try:
                downloaded = await self.download_with_fallback(
                    filename=rom_path.name,
                    platform=platform,
                    output_dir=output_dir,
                    identify_providers=identify_providers,
                    artwork_providers=artwork_providers,
                    artwork_types=types_to_download,
                )

                if downloaded:
                    result.successful.append({
                        "file": str(rom_path),
                        "artwork": {k: str(v) for k, v in downloaded.items()},
                    })
                else:
                    result.skipped.append({
                        "file": str(rom_path),
                        "reason": "No artwork found",
                    })

            except ArtworkNotFoundError:
                result.skipped.append({
                    "file": str(rom_path),
                    "reason": "Game not identified",
                })
            except Exception as e:
                result.failed.append({
                    "file": str(rom_path),
                    "error": str(e),
                })

        return result

    async def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return await self._cache.get_stats()

    async def clear_cache(self, provider: str | None = None) -> int:
        """Clear the artwork cache.

        Args:
            provider: If specified, only clear cache for this provider

        Returns:
            Number of entries cleared
        """
        if provider:
            return await self._cache.clear_provider(provider)
        return await self._cache.clear_all()

    async def clear_expired_cache(self) -> int:
        """Clear expired cache entries.

        Returns:
            Number of entries cleared
        """
        return await self._cache.clear_expired()

    async def close(self) -> None:
        """Close HTTP client and cache connections."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

        await self._cache.close()
