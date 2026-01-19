#include <retro_metadata/platform/slug.hpp>

#include <unordered_map>

namespace retro_metadata {

namespace {

// Maps slugs to human-readable names
const std::unordered_map<std::string_view, std::string_view> kSlugNames = {
    {platform_slug::k3DO, "3DO Interactive Multiplayer"},
    {platform_slug::kAcpc, "Amstrad CPC"},
    {platform_slug::kAmiga, "Amiga"},
    {platform_slug::kAmigaCD, "Amiga CD"},
    {platform_slug::kAmigaCD32, "Amiga CD32"},
    {platform_slug::kAmstradGX4000, "Amstrad GX4000"},
    {platform_slug::kAndroid, "Android"},
    {platform_slug::kAppleII, "Apple II"},
    {platform_slug::kAppleIIGS, "Apple IIGS"},
    {platform_slug::kArcade, "Arcade"},
    {platform_slug::kAtari2600, "Atari 2600"},
    {platform_slug::kAtari5200, "Atari 5200"},
    {platform_slug::kAtari7800, "Atari 7800"},
    {platform_slug::kAtari8bit, "Atari 8-bit"},
    {platform_slug::kAtariJaguarCD, "Atari Jaguar CD"},
    {platform_slug::kAtariST, "Atari ST"},
    {platform_slug::kAtariXEGS, "Atari XEGS"},
    {platform_slug::kBBCMicro, "BBC Micro"},
    {platform_slug::kC128, "Commodore 128"},
    {platform_slug::kC16, "Commodore 16"},
    {platform_slug::kC64, "Commodore 64"},
    {platform_slug::kCPlus4, "Commodore Plus/4"},
    {platform_slug::kColecovision, "ColecoVision"},
    {platform_slug::kCommodoreCDTV, "Commodore CDTV"},
    {platform_slug::kCPS1, "CPS-1"},
    {platform_slug::kCPS2, "CPS-2"},
    {platform_slug::kCPS3, "CPS-3"},
    {platform_slug::kDC, "Sega Dreamcast"},
    {platform_slug::kDOS, "DOS"},
    {platform_slug::kEvercade, "Evercade"},
    {platform_slug::kFairchildChannelF, "Fairchild Channel F"},
    {platform_slug::kFamicom, "Famicom"},
    {platform_slug::kFDS, "Famicom Disk System"},
    {platform_slug::kFMTowns, "FM Towns"},
    {platform_slug::kGameGear, "Sega Game Gear"},
    {platform_slug::kGamate, "Gamate"},
    {platform_slug::kGameDotCom, "Game.com"},
    {platform_slug::kGB, "Game Boy"},
    {platform_slug::kGBA, "Game Boy Advance"},
    {platform_slug::kGBC, "Game Boy Color"},
    {platform_slug::kGenesis, "Sega Genesis"},
    {platform_slug::kGizmondo, "Gizmondo"},
    {platform_slug::kIOS, "iOS"},
    {platform_slug::kIntellvision, "Intellivision"},
    {platform_slug::kJaguar, "Atari Jaguar"},
    {platform_slug::kLinux, "Linux"},
    {platform_slug::kLynx, "Atari Lynx"},
    {platform_slug::kMac, "Mac"},
    {platform_slug::kMSX, "MSX"},
    {platform_slug::kMSX2, "MSX2"},
    {platform_slug::kMSX2Plus, "MSX2+"},
    {platform_slug::kN3DS, "Nintendo 3DS"},
    {platform_slug::kN64, "Nintendo 64"},
    {platform_slug::kN64DD, "Nintendo 64DD"},
    {platform_slug::kNDS, "Nintendo DS"},
    {platform_slug::kNeoGeoAES, "Neo Geo AES"},
    {platform_slug::kNeoGeoCD, "Neo Geo CD"},
    {platform_slug::kNeoGeoMVS, "Neo Geo MVS"},
    {platform_slug::kNeoGeoPocket, "Neo Geo Pocket"},
    {platform_slug::kNeoGeoPocketColor, "Neo Geo Pocket Color"},
    {platform_slug::kNES, "Nintendo Entertainment System"},
    {platform_slug::kNewNintendo3DS, "New Nintendo 3DS"},
    {platform_slug::kNGage, "N-Gage"},
    {platform_slug::kNGC, "Nintendo GameCube"},
    {platform_slug::kNintendoDSi, "Nintendo DSi"},
    {platform_slug::kOdyssey2, "Magnavox Odyssey 2"},
    {platform_slug::kOuya, "Ouya"},
    {platform_slug::kPC8800, "PC-8800 Series"},
    {platform_slug::kPC9800, "PC-9800 Series"},
    {platform_slug::kPCFX, "PC-FX"},
    {platform_slug::kPlaydate, "Playdate"},
    {platform_slug::kPocketstation, "PocketStation"},
    {platform_slug::kPokemonMini, "Pokemon Mini"},
    {platform_slug::kPS2, "PlayStation 2"},
    {platform_slug::kPS3, "PlayStation 3"},
    {platform_slug::kPS4, "PlayStation 4"},
    {platform_slug::kPS5, "PlayStation 5"},
    {platform_slug::kPSP, "PlayStation Portable"},
    {platform_slug::kPSVita, "PlayStation Vita"},
    {platform_slug::kPSVR, "PlayStation VR"},
    {platform_slug::kPSVR2, "PlayStation VR2"},
    {platform_slug::kPSX, "PlayStation"},
    {platform_slug::kSatellaview, "Satellaview"},
    {platform_slug::kSaturn, "Sega Saturn"},
    {platform_slug::kSega32, "Sega 32X"},
    {platform_slug::kSegaCD, "Sega CD"},
    {platform_slug::kSegaCD32, "Sega CD 32X"},
    {platform_slug::kSegaPico, "Sega Pico"},
    {platform_slug::kSeriesXS, "Xbox Series X|S"},
    {platform_slug::kSFam, "Super Famicom"},
    {platform_slug::kSG1000, "Sega SG-1000"},
    {platform_slug::kSharpX68000, "Sharp X68000"},
    {platform_slug::kSMS, "Sega Master System"},
    {platform_slug::kSNES, "Super Nintendo"},
    {platform_slug::kStadia, "Google Stadia"},
    {platform_slug::kSuperGrafx, "SuperGrafx"},
    {platform_slug::kSupervision, "Supervision"},
    {platform_slug::kSwitch, "Nintendo Switch"},
    {platform_slug::kTG16, "TurboGrafx-16"},
    {platform_slug::kTurboGrafxCD, "TurboGrafx-CD"},
    {platform_slug::kVectrex, "Vectrex"},
    {platform_slug::kVIC20, "VIC-20"},
    {platform_slug::kVirtualBoy, "Virtual Boy"},
    {platform_slug::kWii, "Wii"},
    {platform_slug::kWiiU, "Wii U"},
    {platform_slug::kWin, "Windows"},
    {platform_slug::kWin3x, "Windows 3.x"},
    {platform_slug::kWonderSwan, "WonderSwan"},
    {platform_slug::kWonderSwanColor, "WonderSwan Color"},
    {platform_slug::kX1, "Sharp X1"},
    {platform_slug::kXbox, "Xbox"},
    {platform_slug::kXbox360, "Xbox 360"},
    {platform_slug::kXboxOne, "Xbox One"},
    {platform_slug::kZX80, "ZX80"},
    {platform_slug::kZX81, "ZX81"},
    {platform_slug::kZXS, "ZX Spectrum"},
};

}  // namespace

bool is_valid_slug(std::string_view slug) {
    return kSlugNames.find(slug) != kSlugNames.end();
}

std::string slug_name(std::string_view slug) {
    auto it = kSlugNames.find(slug);
    if (it != kSlugNames.end()) {
        return std::string(it->second);
    }
    return std::string(slug);
}

std::vector<std::string_view> all_slugs() {
    std::vector<std::string_view> slugs;
    slugs.reserve(kSlugNames.size());
    for (const auto& [slug, _] : kSlugNames) {
        slugs.push_back(slug);
    }
    return slugs;
}

}  // namespace retro_metadata
