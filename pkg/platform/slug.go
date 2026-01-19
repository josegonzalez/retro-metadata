// Package platform provides platform slug constants and provider ID mappings.
package platform

// Slug represents a universal platform identifier.
// These slugs serve as common identifiers that can be mapped to
// provider-specific platform IDs (IGDB, MobyGames, ScreenScraper, etc.).
type Slug string

// Platform slug constants for cross-provider compatibility.
const (
	Slug3DO                   Slug = "3do"
	SlugAcpc                  Slug = "acpc"
	SlugAmiga                 Slug = "amiga"
	SlugAmigaCD               Slug = "amiga-cd"
	SlugAmigaCD32             Slug = "amiga-cd32"
	SlugAmstradGX4000         Slug = "amstrad-gx4000"
	SlugAndroid               Slug = "android"
	SlugAppleII               Slug = "appleii"
	SlugAppleIIGS             Slug = "apple-iigs"
	SlugArcade                Slug = "arcade"
	SlugAtari2600             Slug = "atari2600"
	SlugAtari5200             Slug = "atari5200"
	SlugAtari7800             Slug = "atari7800"
	SlugAtari8bit             Slug = "atari8bit"
	SlugAtariJaguarCD         Slug = "atari-jaguar-cd"
	SlugAtariST               Slug = "atari-st"
	SlugAtariXEGS             Slug = "atari-xegs"
	SlugBBCMicro              Slug = "bbcmicro"
	SlugC128                  Slug = "c128"
	SlugC16                   Slug = "c16"
	SlugC64                   Slug = "c64"
	SlugCPlus4                Slug = "c-plus-4"
	SlugColecovision          Slug = "colecovision"
	SlugCommodoreCDTV         Slug = "commodore-cdtv"
	SlugCPS1                  Slug = "cps1"
	SlugCPS2                  Slug = "cps2"
	SlugCPS3                  Slug = "cps3"
	SlugDC                    Slug = "dc"
	SlugDOS                   Slug = "dos"
	SlugEvercade              Slug = "evercade"
	SlugFairchildChannelF     Slug = "fairchild-channel-f"
	SlugFamicom               Slug = "famicom"
	SlugFDS                   Slug = "fds"
	SlugFMTowns               Slug = "fm-towns"
	SlugGameGear              Slug = "gamegear"
	SlugGamate                Slug = "gamate"
	SlugGameDotCom            Slug = "game-dot-com"
	SlugGB                    Slug = "gb"
	SlugGBA                   Slug = "gba"
	SlugGBC                   Slug = "gbc"
	SlugGenesis               Slug = "genesis"
	SlugGizmondo              Slug = "gizmondo"
	SlugIOS                   Slug = "ios"
	SlugIntellvision          Slug = "intellivision"
	SlugJaguar                Slug = "jaguar"
	SlugLinux                 Slug = "linux"
	SlugLynx                  Slug = "lynx"
	SlugMac                   Slug = "mac"
	SlugMSX                   Slug = "msx"
	SlugMSX2                  Slug = "msx2"
	SlugMSX2Plus              Slug = "msx2plus"
	SlugN3DS                  Slug = "3ds"
	SlugN64                   Slug = "n64"
	SlugN64DD                 Slug = "64dd"
	SlugNDS                   Slug = "nds"
	SlugNeoGeoAES             Slug = "neogeoaes"
	SlugNeoGeoCD              Slug = "neo-geo-cd"
	SlugNeoGeoMVS             Slug = "neogeomvs"
	SlugNeoGeoPocket          Slug = "neo-geo-pocket"
	SlugNeoGeoPocketColor     Slug = "neo-geo-pocket-color"
	SlugNES                   Slug = "nes"
	SlugNewNintendo3DS        Slug = "new-nintendo-3ds"
	SlugNGage                 Slug = "ngage"
	SlugNGC                   Slug = "ngc"
	SlugNintendoDSi           Slug = "nintendo-dsi"
	SlugOdyssey2              Slug = "odyssey-2"
	SlugOuya                  Slug = "ouya"
	SlugPC8800                Slug = "pc-8800-series"
	SlugPC9800                Slug = "pc-9800-series"
	SlugPCFX                  Slug = "pc-fx"
	SlugPlaydate              Slug = "playdate"
	SlugPocketstation         Slug = "pocketstation"
	SlugPokemonMini           Slug = "pokemon-mini"
	SlugPS2                   Slug = "ps2"
	SlugPS3                   Slug = "ps3"
	SlugPS4                   Slug = "ps4"
	SlugPS5                   Slug = "ps5"
	SlugPSP                   Slug = "psp"
	SlugPSVita                Slug = "psvita"
	SlugPSVR                  Slug = "psvr"
	SlugPSVR2                 Slug = "psvr2"
	SlugPSX                   Slug = "psx"
	SlugSatellaview           Slug = "satellaview"
	SlugSaturn                Slug = "saturn"
	SlugSega32                Slug = "sega32"
	SlugSegaCD                Slug = "segacd"
	SlugSegaCD32              Slug = "segacd32"
	SlugSegaPico              Slug = "sega-pico"
	SlugSeriesXS              Slug = "series-x-s"
	SlugSFam                  Slug = "sfam"
	SlugSG1000                Slug = "sg1000"
	SlugSharpX68000           Slug = "sharp-x68000"
	SlugSMS                   Slug = "sms"
	SlugSNES                  Slug = "snes"
	SlugStadia                Slug = "stadia"
	SlugSuperGrafx            Slug = "supergrafx"
	SlugSupervision           Slug = "supervision"
	SlugSwitch                Slug = "switch"
	SlugTG16                  Slug = "tg16"
	SlugTurboGrafxCD          Slug = "turbografx-cd"
	SlugVectrex               Slug = "vectrex"
	SlugVIC20                 Slug = "vic-20"
	SlugVirtualBoy            Slug = "virtualboy"
	SlugWii                   Slug = "wii"
	SlugWiiU                  Slug = "wiiu"
	SlugWin                   Slug = "win"
	SlugWin3x                 Slug = "win3x"
	SlugWonderSwan            Slug = "wonderswan"
	SlugWonderSwanColor       Slug = "wonderswan-color"
	SlugX1                    Slug = "x1"
	SlugXbox                  Slug = "xbox"
	SlugXbox360               Slug = "xbox360"
	SlugXboxOne               Slug = "xboxone"
	SlugZX80                  Slug = "zx80"
	SlugZX81                  Slug = "zx81"
	SlugZXS                   Slug = "zxs"
)

// String returns the string representation of the slug.
func (s Slug) String() string {
	return string(s)
}

// IsValid checks if the slug is a known platform.
func (s Slug) IsValid() bool {
	_, exists := slugNames[s]
	return exists
}

// Name returns the human-readable name for the platform.
func (s Slug) Name() string {
	if name, ok := slugNames[s]; ok {
		return name
	}
	return string(s)
}

// slugNames maps slugs to human-readable names.
var slugNames = map[Slug]string{
	Slug3DO:               "3DO Interactive Multiplayer",
	SlugAcpc:              "Amstrad CPC",
	SlugAmiga:             "Amiga",
	SlugAmigaCD:           "Amiga CD",
	SlugAmigaCD32:         "Amiga CD32",
	SlugAmstradGX4000:     "Amstrad GX4000",
	SlugAndroid:           "Android",
	SlugAppleII:           "Apple II",
	SlugAppleIIGS:         "Apple IIGS",
	SlugArcade:            "Arcade",
	SlugAtari2600:         "Atari 2600",
	SlugAtari5200:         "Atari 5200",
	SlugAtari7800:         "Atari 7800",
	SlugAtari8bit:         "Atari 8-bit",
	SlugAtariJaguarCD:     "Atari Jaguar CD",
	SlugAtariST:           "Atari ST",
	SlugAtariXEGS:         "Atari XEGS",
	SlugBBCMicro:          "BBC Micro",
	SlugC128:              "Commodore 128",
	SlugC16:               "Commodore 16",
	SlugC64:               "Commodore 64",
	SlugCPlus4:            "Commodore Plus/4",
	SlugColecovision:      "ColecoVision",
	SlugCommodoreCDTV:     "Commodore CDTV",
	SlugCPS1:              "CPS-1",
	SlugCPS2:              "CPS-2",
	SlugCPS3:              "CPS-3",
	SlugDC:                "Sega Dreamcast",
	SlugDOS:               "DOS",
	SlugEvercade:          "Evercade",
	SlugFairchildChannelF: "Fairchild Channel F",
	SlugFamicom:           "Famicom",
	SlugFDS:               "Famicom Disk System",
	SlugFMTowns:           "FM Towns",
	SlugGameGear:          "Sega Game Gear",
	SlugGamate:            "Gamate",
	SlugGameDotCom:        "Game.com",
	SlugGB:                "Game Boy",
	SlugGBA:               "Game Boy Advance",
	SlugGBC:               "Game Boy Color",
	SlugGenesis:           "Sega Genesis",
	SlugGizmondo:          "Gizmondo",
	SlugIOS:               "iOS",
	SlugIntellvision:      "Intellivision",
	SlugJaguar:            "Atari Jaguar",
	SlugLinux:             "Linux",
	SlugLynx:              "Atari Lynx",
	SlugMac:               "Mac",
	SlugMSX:               "MSX",
	SlugMSX2:              "MSX2",
	SlugMSX2Plus:          "MSX2+",
	SlugN3DS:              "Nintendo 3DS",
	SlugN64:               "Nintendo 64",
	SlugN64DD:             "Nintendo 64DD",
	SlugNDS:               "Nintendo DS",
	SlugNeoGeoAES:         "Neo Geo AES",
	SlugNeoGeoCD:          "Neo Geo CD",
	SlugNeoGeoMVS:         "Neo Geo MVS",
	SlugNeoGeoPocket:      "Neo Geo Pocket",
	SlugNeoGeoPocketColor: "Neo Geo Pocket Color",
	SlugNES:               "Nintendo Entertainment System",
	SlugNewNintendo3DS:    "New Nintendo 3DS",
	SlugNGage:             "N-Gage",
	SlugNGC:               "Nintendo GameCube",
	SlugNintendoDSi:       "Nintendo DSi",
	SlugOdyssey2:          "Magnavox Odyssey 2",
	SlugOuya:              "Ouya",
	SlugPC8800:            "PC-8800 Series",
	SlugPC9800:            "PC-9800 Series",
	SlugPCFX:              "PC-FX",
	SlugPlaydate:          "Playdate",
	SlugPocketstation:     "PocketStation",
	SlugPokemonMini:       "Pokemon Mini",
	SlugPS2:               "PlayStation 2",
	SlugPS3:               "PlayStation 3",
	SlugPS4:               "PlayStation 4",
	SlugPS5:               "PlayStation 5",
	SlugPSP:               "PlayStation Portable",
	SlugPSVita:            "PlayStation Vita",
	SlugPSVR:              "PlayStation VR",
	SlugPSVR2:             "PlayStation VR2",
	SlugPSX:               "PlayStation",
	SlugSatellaview:       "Satellaview",
	SlugSaturn:            "Sega Saturn",
	SlugSega32:            "Sega 32X",
	SlugSegaCD:            "Sega CD",
	SlugSegaCD32:          "Sega CD 32X",
	SlugSegaPico:          "Sega Pico",
	SlugSeriesXS:          "Xbox Series X|S",
	SlugSFam:              "Super Famicom",
	SlugSG1000:            "Sega SG-1000",
	SlugSharpX68000:       "Sharp X68000",
	SlugSMS:               "Sega Master System",
	SlugSNES:              "Super Nintendo",
	SlugStadia:            "Google Stadia",
	SlugSuperGrafx:        "SuperGrafx",
	SlugSupervision:       "Supervision",
	SlugSwitch:            "Nintendo Switch",
	SlugTG16:              "TurboGrafx-16",
	SlugTurboGrafxCD:      "TurboGrafx-CD",
	SlugVectrex:           "Vectrex",
	SlugVIC20:             "VIC-20",
	SlugVirtualBoy:        "Virtual Boy",
	SlugWii:               "Wii",
	SlugWiiU:              "Wii U",
	SlugWin:               "Windows",
	SlugWin3x:             "Windows 3.x",
	SlugWonderSwan:        "WonderSwan",
	SlugWonderSwanColor:   "WonderSwan Color",
	SlugX1:                "Sharp X1",
	SlugXbox:              "Xbox",
	SlugXbox360:           "Xbox 360",
	SlugXboxOne:           "Xbox One",
	SlugZX80:              "ZX80",
	SlugZX81:              "ZX81",
	SlugZXS:               "ZX Spectrum",
}

// AllSlugs returns all defined platform slugs.
func AllSlugs() []Slug {
	slugs := make([]Slug, 0, len(slugNames))
	for slug := range slugNames {
		slugs = append(slugs, slug)
	}
	return slugs
}
