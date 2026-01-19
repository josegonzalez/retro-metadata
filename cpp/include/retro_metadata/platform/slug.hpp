#pragma once

/// @file slug.hpp
/// @brief Platform slug constants and utilities

#include <string>
#include <string_view>
#include <vector>

namespace retro_metadata {

/// @brief Platform slug constants for cross-provider compatibility
///
/// These slugs serve as common identifiers that can be mapped to
/// provider-specific platform IDs (IGDB, MobyGames, ScreenScraper, etc.).
namespace platform_slug {

// Console platforms
inline constexpr std::string_view k3DO = "3do";
inline constexpr std::string_view kAcpc = "acpc";
inline constexpr std::string_view kAmiga = "amiga";
inline constexpr std::string_view kAmigaCD = "amiga-cd";
inline constexpr std::string_view kAmigaCD32 = "amiga-cd32";
inline constexpr std::string_view kAmstradGX4000 = "amstrad-gx4000";
inline constexpr std::string_view kAndroid = "android";
inline constexpr std::string_view kAppleII = "appleii";
inline constexpr std::string_view kAppleIIGS = "apple-iigs";
inline constexpr std::string_view kArcade = "arcade";
inline constexpr std::string_view kAtari2600 = "atari2600";
inline constexpr std::string_view kAtari5200 = "atari5200";
inline constexpr std::string_view kAtari7800 = "atari7800";
inline constexpr std::string_view kAtari8bit = "atari8bit";
inline constexpr std::string_view kAtariJaguarCD = "atari-jaguar-cd";
inline constexpr std::string_view kAtariST = "atari-st";
inline constexpr std::string_view kAtariXEGS = "atari-xegs";
inline constexpr std::string_view kBBCMicro = "bbcmicro";
inline constexpr std::string_view kC128 = "c128";
inline constexpr std::string_view kC16 = "c16";
inline constexpr std::string_view kC64 = "c64";
inline constexpr std::string_view kCPlus4 = "c-plus-4";
inline constexpr std::string_view kColecovision = "colecovision";
inline constexpr std::string_view kCommodoreCDTV = "commodore-cdtv";
inline constexpr std::string_view kCPS1 = "cps1";
inline constexpr std::string_view kCPS2 = "cps2";
inline constexpr std::string_view kCPS3 = "cps3";
inline constexpr std::string_view kDC = "dc";
inline constexpr std::string_view kDOS = "dos";
inline constexpr std::string_view kEvercade = "evercade";
inline constexpr std::string_view kFairchildChannelF = "fairchild-channel-f";
inline constexpr std::string_view kFamicom = "famicom";
inline constexpr std::string_view kFDS = "fds";
inline constexpr std::string_view kFMTowns = "fm-towns";
inline constexpr std::string_view kGameGear = "gamegear";
inline constexpr std::string_view kGamate = "gamate";
inline constexpr std::string_view kGameDotCom = "game-dot-com";
inline constexpr std::string_view kGB = "gb";
inline constexpr std::string_view kGBA = "gba";
inline constexpr std::string_view kGBC = "gbc";
inline constexpr std::string_view kGenesis = "genesis";
inline constexpr std::string_view kGizmondo = "gizmondo";
inline constexpr std::string_view kIOS = "ios";
inline constexpr std::string_view kIntellvision = "intellivision";
inline constexpr std::string_view kJaguar = "jaguar";
inline constexpr std::string_view kLinux = "linux";
inline constexpr std::string_view kLynx = "lynx";
inline constexpr std::string_view kMac = "mac";
inline constexpr std::string_view kMSX = "msx";
inline constexpr std::string_view kMSX2 = "msx2";
inline constexpr std::string_view kMSX2Plus = "msx2plus";
inline constexpr std::string_view kN3DS = "3ds";
inline constexpr std::string_view kN64 = "n64";
inline constexpr std::string_view kN64DD = "64dd";
inline constexpr std::string_view kNDS = "nds";
inline constexpr std::string_view kNeoGeoAES = "neogeoaes";
inline constexpr std::string_view kNeoGeoCD = "neo-geo-cd";
inline constexpr std::string_view kNeoGeoMVS = "neogeomvs";
inline constexpr std::string_view kNeoGeoPocket = "neo-geo-pocket";
inline constexpr std::string_view kNeoGeoPocketColor = "neo-geo-pocket-color";
inline constexpr std::string_view kNES = "nes";
inline constexpr std::string_view kNewNintendo3DS = "new-nintendo-3ds";
inline constexpr std::string_view kNGage = "ngage";
inline constexpr std::string_view kNGC = "ngc";
inline constexpr std::string_view kNintendoDSi = "nintendo-dsi";
inline constexpr std::string_view kOdyssey2 = "odyssey-2";
inline constexpr std::string_view kOuya = "ouya";
inline constexpr std::string_view kPC8800 = "pc-8800-series";
inline constexpr std::string_view kPC9800 = "pc-9800-series";
inline constexpr std::string_view kPCFX = "pc-fx";
inline constexpr std::string_view kPlaydate = "playdate";
inline constexpr std::string_view kPocketstation = "pocketstation";
inline constexpr std::string_view kPokemonMini = "pokemon-mini";
inline constexpr std::string_view kPS2 = "ps2";
inline constexpr std::string_view kPS3 = "ps3";
inline constexpr std::string_view kPS4 = "ps4";
inline constexpr std::string_view kPS5 = "ps5";
inline constexpr std::string_view kPSP = "psp";
inline constexpr std::string_view kPSVita = "psvita";
inline constexpr std::string_view kPSVR = "psvr";
inline constexpr std::string_view kPSVR2 = "psvr2";
inline constexpr std::string_view kPSX = "psx";
inline constexpr std::string_view kSatellaview = "satellaview";
inline constexpr std::string_view kSaturn = "saturn";
inline constexpr std::string_view kSega32 = "sega32";
inline constexpr std::string_view kSegaCD = "segacd";
inline constexpr std::string_view kSegaCD32 = "segacd32";
inline constexpr std::string_view kSegaPico = "sega-pico";
inline constexpr std::string_view kSeriesXS = "series-x-s";
inline constexpr std::string_view kSFam = "sfam";
inline constexpr std::string_view kSG1000 = "sg1000";
inline constexpr std::string_view kSharpX68000 = "sharp-x68000";
inline constexpr std::string_view kSMS = "sms";
inline constexpr std::string_view kSNES = "snes";
inline constexpr std::string_view kStadia = "stadia";
inline constexpr std::string_view kSuperGrafx = "supergrafx";
inline constexpr std::string_view kSupervision = "supervision";
inline constexpr std::string_view kSwitch = "switch";
inline constexpr std::string_view kTG16 = "tg16";
inline constexpr std::string_view kTurboGrafxCD = "turbografx-cd";
inline constexpr std::string_view kVectrex = "vectrex";
inline constexpr std::string_view kVIC20 = "vic-20";
inline constexpr std::string_view kVirtualBoy = "virtualboy";
inline constexpr std::string_view kWii = "wii";
inline constexpr std::string_view kWiiU = "wiiu";
inline constexpr std::string_view kWin = "win";
inline constexpr std::string_view kWin3x = "win3x";
inline constexpr std::string_view kWonderSwan = "wonderswan";
inline constexpr std::string_view kWonderSwanColor = "wonderswan-color";
inline constexpr std::string_view kX1 = "x1";
inline constexpr std::string_view kXbox = "xbox";
inline constexpr std::string_view kXbox360 = "xbox360";
inline constexpr std::string_view kXboxOne = "xboxone";
inline constexpr std::string_view kZX80 = "zx80";
inline constexpr std::string_view kZX81 = "zx81";
inline constexpr std::string_view kZXS = "zxs";

}  // namespace platform_slug

/// @brief Checks if a slug is a known platform
[[nodiscard]] bool is_valid_slug(std::string_view slug);

/// @brief Returns the human-readable name for a platform slug
[[nodiscard]] std::string slug_name(std::string_view slug);

/// @brief Returns all defined platform slugs
[[nodiscard]] std::vector<std::string_view> all_slugs();

}  // namespace retro_metadata
