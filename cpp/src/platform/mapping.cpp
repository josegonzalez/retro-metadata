#include <retro_metadata/platform/mapping.hpp>
#include <retro_metadata/platform/slug.hpp>

#include <unordered_map>

namespace retro_metadata {

namespace {

// IGDB platform ID mappings
const std::unordered_map<std::string_view, int> kIgdbPlatformMap = {
    {platform_slug::k3DO, 50},          {platform_slug::kAcpc, 25},
    {platform_slug::kAmstradGX4000, 158},{platform_slug::kAndroid, 34},
    {platform_slug::kIOS, 39},          {platform_slug::kAppleII, 75},
    {platform_slug::kAppleIIGS, 115},   {platform_slug::kMac, 14},
    {platform_slug::kArcade, 52},       {platform_slug::kCPS1, 52},
    {platform_slug::kCPS2, 52},         {platform_slug::kCPS3, 52},
    {platform_slug::kNeoGeoMVS, 79},    {platform_slug::kNeoGeoAES, 80},
    {platform_slug::kAtari2600, 59},    {platform_slug::kAtari5200, 66},
    {platform_slug::kAtari7800, 60},    {platform_slug::kAtari8bit, 65},
    {platform_slug::kAtariJaguarCD, 171},{platform_slug::kAtariST, 63},
    {platform_slug::kAtariXEGS, 111},   {platform_slug::kJaguar, 62},
    {platform_slug::kLynx, 61},         {platform_slug::kWonderSwan, 57},
    {platform_slug::kWonderSwanColor, 123},{platform_slug::kAmiga, 16},
    {platform_slug::kAmigaCD, 114},     {platform_slug::kAmigaCD32, 117},
    {platform_slug::kC128, 15},         {platform_slug::kC16, 93},
    {platform_slug::kC64, 15},          {platform_slug::kCPlus4, 94},
    {platform_slug::kCommodoreCDTV, 116},{platform_slug::kVIC20, 71},
    {platform_slug::kDOS, 13},          {platform_slug::kLinux, 3},
    {platform_slug::kWin, 6},           {platform_slug::kWin3x, 6},
    {platform_slug::kXbox, 11},         {platform_slug::kXbox360, 12},
    {platform_slug::kXboxOne, 49},      {platform_slug::kSeriesXS, 169},
    {platform_slug::kPC8800, 125},      {platform_slug::kPC9800, 149},
    {platform_slug::kPCFX, 274},        {platform_slug::kSuperGrafx, 128},
    {platform_slug::kTG16, 86},         {platform_slug::kTurboGrafxCD, 150},
    {platform_slug::kNeoGeoCD, 136},    {platform_slug::kNeoGeoPocket, 119},
    {platform_slug::kNeoGeoPocketColor, 120},{platform_slug::kFamicom, 99},
    {platform_slug::kFDS, 51},          {platform_slug::kN64, 4},
    {platform_slug::kN64DD, 416},       {platform_slug::kNES, 18},
    {platform_slug::kNGC, 21},          {platform_slug::kSatellaview, 58},
    {platform_slug::kSFam, 58},         {platform_slug::kSNES, 19},
    {platform_slug::kSwitch, 130},      {platform_slug::kWii, 5},
    {platform_slug::kWiiU, 41},         {platform_slug::kGB, 33},
    {platform_slug::kGBA, 24},          {platform_slug::kGBC, 22},
    {platform_slug::kN3DS, 37},         {platform_slug::kNDS, 20},
    {platform_slug::kNewNintendo3DS, 137},{platform_slug::kNintendoDSi, 20},
    {platform_slug::kVirtualBoy, 87},   {platform_slug::kDC, 23},
    {platform_slug::kGameGear, 35},     {platform_slug::kGenesis, 29},
    {platform_slug::kSaturn, 32},       {platform_slug::kSega32, 30},
    {platform_slug::kSegaCD, 78},       {platform_slug::kSegaCD32, 78},
    {platform_slug::kSG1000, 84},       {platform_slug::kSMS, 64},
    {platform_slug::kSegaPico, 339},    {platform_slug::kSharpX68000, 112},
    {platform_slug::kX1, 77},           {platform_slug::kPocketstation, 76},
    {platform_slug::kPS2, 8},           {platform_slug::kPS3, 9},
    {platform_slug::kPS4, 48},          {platform_slug::kPS5, 167},
    {platform_slug::kPSP, 38},          {platform_slug::kPSVita, 46},
    {platform_slug::kPSVR, 165},        {platform_slug::kPSVR2, 390},
    {platform_slug::kPSX, 7},           {platform_slug::kBBCMicro, 69},
    {platform_slug::kMSX, 27},          {platform_slug::kMSX2, 53},
    {platform_slug::kMSX2Plus, 161},    {platform_slug::kZX80, 26},
    {platform_slug::kZX81, 26},         {platform_slug::kZXS, 26},
    {platform_slug::kColecovision, 68}, {platform_slug::kFairchildChannelF, 127},
    {platform_slug::kIntellvision, 67}, {platform_slug::kOdyssey2, 133},
    {platform_slug::kVectrex, 70},      {platform_slug::kGamate, 340},
    {platform_slug::kGameDotCom, 122},  {platform_slug::kGizmondo, 121},
    {platform_slug::kNGage, 42},        {platform_slug::kPlaydate, 308},
    {platform_slug::kPokemonMini, 207}, {platform_slug::kSupervision, 343},
    {platform_slug::kStadia, 170},      {platform_slug::kOuya, 72},
};

// MobyGames platform ID mappings
const std::unordered_map<std::string_view, int> kMobygamesPlatformMap = {
    {platform_slug::k3DO, 35},          {platform_slug::kAcpc, 60},
    {platform_slug::kAmstradGX4000, 198},{platform_slug::kAndroid, 91},
    {platform_slug::kIOS, 86},          {platform_slug::kAppleII, 31},
    {platform_slug::kAppleIIGS, 39},    {platform_slug::kMac, 74},
    {platform_slug::kArcade, 143},      {platform_slug::kCPS1, 143},
    {platform_slug::kCPS2, 143},        {platform_slug::kCPS3, 143},
    {platform_slug::kNeoGeoMVS, 36},    {platform_slug::kNeoGeoAES, 36},
    {platform_slug::kAtari2600, 28},    {platform_slug::kAtari5200, 33},
    {platform_slug::kAtari7800, 34},    {platform_slug::kAtari8bit, 39},
    {platform_slug::kAtariJaguarCD, 17},{platform_slug::kAtariST, 24},
    {platform_slug::kAtariXEGS, 39},    {platform_slug::kJaguar, 17},
    {platform_slug::kLynx, 18},         {platform_slug::kWonderSwan, 48},
    {platform_slug::kWonderSwanColor, 49},{platform_slug::kAmiga, 19},
    {platform_slug::kAmigaCD, 56},      {platform_slug::kAmigaCD32, 56},
    {platform_slug::kC128, 61},         {platform_slug::kC16, 115},
    {platform_slug::kC64, 27},          {platform_slug::kCPlus4, 115},
    {platform_slug::kCommodoreCDTV, 83},{platform_slug::kVIC20, 43},
    {platform_slug::kDOS, 2},           {platform_slug::kLinux, 1},
    {platform_slug::kWin, 3},           {platform_slug::kWin3x, 5},
    {platform_slug::kXbox, 13},         {platform_slug::kXbox360, 69},
    {platform_slug::kXboxOne, 142},     {platform_slug::kSeriesXS, 289},
    {platform_slug::kPC8800, 94},       {platform_slug::kPC9800, 95},
    {platform_slug::kPCFX, 59},         {platform_slug::kSuperGrafx, 127},
    {platform_slug::kTG16, 40},         {platform_slug::kTurboGrafxCD, 45},
    {platform_slug::kNeoGeoCD, 54},     {platform_slug::kNeoGeoPocket, 52},
    {platform_slug::kNeoGeoPocketColor, 53},{platform_slug::kFamicom, 22},
    {platform_slug::kFDS, 22},          {platform_slug::kN64, 9},
    {platform_slug::kN64DD, 9},         {platform_slug::kNES, 22},
    {platform_slug::kNGC, 14},          {platform_slug::kSatellaview, 15},
    {platform_slug::kSFam, 15},         {platform_slug::kSNES, 15},
    {platform_slug::kSwitch, 203},      {platform_slug::kWii, 82},
    {platform_slug::kWiiU, 132},        {platform_slug::kGB, 10},
    {platform_slug::kGBA, 12},          {platform_slug::kGBC, 11},
    {platform_slug::kN3DS, 101},        {platform_slug::kNDS, 44},
    {platform_slug::kNewNintendo3DS, 174},{platform_slug::kNintendoDSi, 87},
    {platform_slug::kVirtualBoy, 38},   {platform_slug::kPokemonMini, 152},
    {platform_slug::kDC, 8},            {platform_slug::kGameGear, 25},
    {platform_slug::kGenesis, 16},      {platform_slug::kSaturn, 23},
    {platform_slug::kSega32, 21},       {platform_slug::kSegaCD, 20},
    {platform_slug::kSegaCD32, 20},     {platform_slug::kSG1000, 114},
    {platform_slug::kSMS, 26},          {platform_slug::kSegaPico, 103},
    {platform_slug::kSharpX68000, 106}, {platform_slug::kX1, 121},
    {platform_slug::kPocketstation, 147},{platform_slug::kPS2, 7},
    {platform_slug::kPS3, 81},          {platform_slug::kPS4, 141},
    {platform_slug::kPS5, 288},         {platform_slug::kPSP, 46},
    {platform_slug::kPSVita, 105},      {platform_slug::kPSVR, 286},
    {platform_slug::kPSVR2, 286},       {platform_slug::kPSX, 6},
    {platform_slug::kBBCMicro, 92},     {platform_slug::kMSX, 57},
    {platform_slug::kMSX2, 57},         {platform_slug::kMSX2Plus, 57},
    {platform_slug::kFMTowns, 102},     {platform_slug::kZXS, 41},
    {platform_slug::kZX80, 119},        {platform_slug::kZX81, 120},
    {platform_slug::kColecovision, 29}, {platform_slug::kFairchildChannelF, 76},
    {platform_slug::kIntellvision, 30}, {platform_slug::kOdyssey2, 78},
    {platform_slug::kVectrex, 37},      {platform_slug::kGamate, 189},
    {platform_slug::kGameDotCom, 50},   {platform_slug::kGizmondo, 55},
    {platform_slug::kSupervision, 109}, {platform_slug::kStadia, 273},
    {platform_slug::kOuya, 144},        {platform_slug::kPlaydate, 298},
    {platform_slug::kEvercade, 294},
};

// ScreenScraper platform ID mappings
const std::unordered_map<std::string_view, int> kScreenscraperPlatformMap = {
    {platform_slug::k3DO, 29},          {platform_slug::kN3DS, 17},
    {platform_slug::kN64, 14},          {platform_slug::kArcade, 75},
    {platform_slug::kAtari2600, 26},    {platform_slug::kAtari5200, 40},
    {platform_slug::kAtari7800, 41},    {platform_slug::kC64, 66},
    {platform_slug::kDC, 23},           {platform_slug::kDOS, 135},
    {platform_slug::kFamicom, 3},       {platform_slug::kFDS, 106},
    {platform_slug::kGB, 9},            {platform_slug::kGBA, 12},
    {platform_slug::kGBC, 10},          {platform_slug::kGenesis, 1},
    {platform_slug::kGameGear, 21},     {platform_slug::kJaguar, 27},
    {platform_slug::kLynx, 28},         {platform_slug::kMSX, 113},
    {platform_slug::kMSX2, 116},        {platform_slug::kNDS, 15},
    {platform_slug::kNeoGeoCD, 70},     {platform_slug::kNeoGeoPocket, 25},
    {platform_slug::kNeoGeoPocketColor, 82},{platform_slug::kNeoGeoAES, 142},
    {platform_slug::kNES, 3},           {platform_slug::kNGC, 13},
    {platform_slug::kPCFX, 72},         {platform_slug::kPS2, 58},
    {platform_slug::kPS3, 59},          {platform_slug::kPSP, 61},
    {platform_slug::kPSVita, 62},       {platform_slug::kPSX, 57},
    {platform_slug::kSaturn, 22},       {platform_slug::kSega32, 19},
    {platform_slug::kSegaCD, 20},       {platform_slug::kSFam, 4},
    {platform_slug::kSG1000, 109},      {platform_slug::kSMS, 2},
    {platform_slug::kSNES, 4},          {platform_slug::kSuperGrafx, 105},
    {platform_slug::kSwitch, 225},      {platform_slug::kTG16, 31},
    {platform_slug::kTurboGrafxCD, 114},{platform_slug::kVectrex, 102},
    {platform_slug::kVirtualBoy, 11},   {platform_slug::kWii, 16},
    {platform_slug::kWiiU, 18},         {platform_slug::kWonderSwan, 45},
    {platform_slug::kWonderSwanColor, 46},{platform_slug::kXbox, 32},
    {platform_slug::kXbox360, 33},      {platform_slug::kZXS, 76},
};

// RetroAchievements platform ID mappings
const std::unordered_map<std::string_view, int> kRetroachievementsPlatformMap = {
    {platform_slug::k3DO, 43},          {platform_slug::kN64, 2},
    {platform_slug::kArcade, 27},       {platform_slug::kAtari2600, 25},
    {platform_slug::kAtari7800, 51},    {platform_slug::kDC, 40},
    {platform_slug::kFamicom, 1},       {platform_slug::kGB, 4},
    {platform_slug::kGBA, 5},           {platform_slug::kGBC, 6},
    {platform_slug::kGenesis, 1},       {platform_slug::kGameGear, 15},
    {platform_slug::kJaguar, 17},       {platform_slug::kLynx, 13},
    {platform_slug::kMSX, 29},          {platform_slug::kNDS, 18},
    {platform_slug::kNeoGeoPocket, 14}, {platform_slug::kNeoGeoAES, 27},
    {platform_slug::kNES, 7},           {platform_slug::kNGC, 16},
    {platform_slug::kPCFX, 49},         {platform_slug::kPS2, 21},
    {platform_slug::kPSP, 41},          {platform_slug::kPSX, 12},
    {platform_slug::kSaturn, 39},       {platform_slug::kSega32, 10},
    {platform_slug::kSegaCD, 9},        {platform_slug::kSFam, 3},
    {platform_slug::kSG1000, 33},       {platform_slug::kSMS, 11},
    {platform_slug::kSNES, 3},          {platform_slug::kSuperGrafx, 8},
    {platform_slug::kTG16, 8},          {platform_slug::kVectrex, 46},
    {platform_slug::kVirtualBoy, 28},   {platform_slug::kWonderSwan, 53},
};

}  // namespace

std::optional<int> get_igdb_platform_id(std::string_view slug) {
    auto it = kIgdbPlatformMap.find(slug);
    if (it != kIgdbPlatformMap.end()) {
        return it->second;
    }
    return std::nullopt;
}

std::optional<int> get_mobygames_platform_id(std::string_view slug) {
    auto it = kMobygamesPlatformMap.find(slug);
    if (it != kMobygamesPlatformMap.end()) {
        return it->second;
    }
    return std::nullopt;
}

std::optional<int> get_screenscraper_platform_id(std::string_view slug) {
    auto it = kScreenscraperPlatformMap.find(slug);
    if (it != kScreenscraperPlatformMap.end()) {
        return it->second;
    }
    return std::nullopt;
}

std::optional<int> get_retroachievements_platform_id(std::string_view slug) {
    auto it = kRetroachievementsPlatformMap.find(slug);
    if (it != kRetroachievementsPlatformMap.end()) {
        return it->second;
    }
    return std::nullopt;
}

std::optional<PlatformInfo> get_platform_info(std::string_view slug) {
    if (!is_valid_slug(slug)) {
        return std::nullopt;
    }

    PlatformInfo info;
    info.slug = std::string(slug);
    info.name = slug_name(slug);
    info.igdb_id = get_igdb_platform_id(slug);
    info.mobygames_id = get_mobygames_platform_id(slug);
    info.screenscraper_id = get_screenscraper_platform_id(slug);
    info.retroachievements_id = get_retroachievements_platform_id(slug);
    return info;
}

std::string slug_from_igdb_id(int igdb_id) {
    for (const auto& [slug, id] : kIgdbPlatformMap) {
        if (id == igdb_id) {
            return std::string(slug);
        }
    }
    return "";
}

std::string slug_from_mobygames_id(int moby_id) {
    for (const auto& [slug, id] : kMobygamesPlatformMap) {
        if (id == moby_id) {
            return std::string(slug);
        }
    }
    return "";
}

std::string slug_from_screenscraper_id(int ss_id) {
    for (const auto& [slug, id] : kScreenscraperPlatformMap) {
        if (id == ss_id) {
            return std::string(slug);
        }
    }
    return "";
}

std::string slug_from_retroachievements_id(int ra_id) {
    for (const auto& [slug, id] : kRetroachievementsPlatformMap) {
        if (id == ra_id) {
            return std::string(slug);
        }
    }
    return "";
}

}  // namespace retro_metadata
