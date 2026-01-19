package platform

// PlatformInfo contains information about a platform across multiple providers.
type PlatformInfo struct {
	// Slug is the universal platform slug
	Slug Slug `json:"slug"`
	// Name is the human-readable platform name
	Name string `json:"name"`
	// IGDBID is the IGDB platform ID
	IGDBID *int `json:"igdb_id,omitempty"`
	// MobyGamesID is the MobyGames platform ID
	MobyGamesID *int `json:"mobygames_id,omitempty"`
	// ScreenScraperID is the ScreenScraper platform ID
	ScreenScraperID *int `json:"screenscraper_id,omitempty"`
	// RetroAchievementsID is the RetroAchievements console ID
	RetroAchievementsID *int `json:"retroachievements_id,omitempty"`
}

// IGDB platform ID mappings
var igdbPlatformMap = map[Slug]int{
	Slug3DO:               50,
	SlugAcpc:              25,
	SlugAmstradGX4000:     158,
	SlugAndroid:           34,
	SlugIOS:               39,
	SlugAppleII:           75,
	SlugAppleIIGS:         115,
	SlugMac:               14,
	SlugArcade:            52,
	SlugCPS1:              52,
	SlugCPS2:              52,
	SlugCPS3:              52,
	SlugNeoGeoMVS:         79,
	SlugNeoGeoAES:         80,
	SlugAtari2600:         59,
	SlugAtari5200:         66,
	SlugAtari7800:         60,
	SlugAtari8bit:         65,
	SlugAtariJaguarCD:     171,
	SlugAtariST:           63,
	SlugAtariXEGS:         111,
	SlugJaguar:            62,
	SlugLynx:              61,
	SlugWonderSwan:        57,
	SlugWonderSwanColor:   123,
	SlugAmiga:             16,
	SlugAmigaCD:           114,
	SlugAmigaCD32:         117,
	SlugC128:              15,
	SlugC16:               93,
	SlugC64:               15,
	SlugCPlus4:            94,
	SlugCommodoreCDTV:     116,
	SlugVIC20:             71,
	SlugDOS:               13,
	SlugLinux:             3,
	SlugWin:               6,
	SlugWin3x:             6,
	SlugXbox:              11,
	SlugXbox360:           12,
	SlugXboxOne:           49,
	SlugSeriesXS:          169,
	SlugPC8800:            125,
	SlugPC9800:            149,
	SlugPCFX:              274,
	SlugSuperGrafx:        128,
	SlugTG16:              86,
	SlugTurboGrafxCD:      150,
	SlugNeoGeoCD:          136,
	SlugNeoGeoPocket:      119,
	SlugNeoGeoPocketColor: 120,
	SlugFamicom:           99,
	SlugFDS:               51,
	SlugN64:               4,
	SlugN64DD:             416,
	SlugNES:               18,
	SlugNGC:               21,
	SlugSatellaview:       58,
	SlugSFam:              58,
	SlugSNES:              19,
	SlugSwitch:            130,
	SlugWii:               5,
	SlugWiiU:              41,
	SlugGB:                33,
	SlugGBA:               24,
	SlugGBC:               22,
	SlugN3DS:              37,
	SlugNDS:               20,
	SlugNewNintendo3DS:    137,
	SlugNintendoDSi:       20,
	SlugVirtualBoy:        87,
	SlugDC:                23,
	SlugGameGear:          35,
	SlugGenesis:           29,
	SlugSaturn:            32,
	SlugSega32:            30,
	SlugSegaCD:            78,
	SlugSegaCD32:          78,
	SlugSG1000:            84,
	SlugSMS:               64,
	SlugSegaPico:          339,
	SlugSharpX68000:       112,
	SlugX1:                77,
	SlugPocketstation:     76,
	SlugPS2:               8,
	SlugPS3:               9,
	SlugPS4:               48,
	SlugPS5:               167,
	SlugPSP:               38,
	SlugPSVita:            46,
	SlugPSVR:              165,
	SlugPSVR2:             390,
	SlugPSX:               7,
	SlugBBCMicro:          69,
	SlugMSX:               27,
	SlugMSX2:              53,
	SlugMSX2Plus:          161,
	SlugZX80:              26,
	SlugZX81:              26,
	SlugZXS:               26,
	SlugColecovision:      68,
	SlugFairchildChannelF: 127,
	SlugIntellvision:      67,
	SlugOdyssey2:          133,
	SlugVectrex:           70,
	SlugGamate:            340,
	SlugGameDotCom:        122,
	SlugGizmondo:          121,
	SlugNGage:             42,
	SlugPlaydate:          308,
	SlugPokemonMini:       207,
	SlugSupervision:       343,
	SlugStadia:            170,
	SlugOuya:              72,
}

// MobyGames platform ID mappings
var mobygamesPlatformMap = map[Slug]int{
	Slug3DO:               35,
	SlugAcpc:              60,
	SlugAmstradGX4000:     198,
	SlugAndroid:           91,
	SlugIOS:               86,
	SlugAppleII:           31,
	SlugAppleIIGS:         39,
	SlugMac:               74,
	SlugArcade:            143,
	SlugCPS1:              143,
	SlugCPS2:              143,
	SlugCPS3:              143,
	SlugNeoGeoMVS:         36,
	SlugNeoGeoAES:         36,
	SlugAtari2600:         28,
	SlugAtari5200:         33,
	SlugAtari7800:         34,
	SlugAtari8bit:         39,
	SlugAtariJaguarCD:     17,
	SlugAtariST:           24,
	SlugAtariXEGS:         39,
	SlugJaguar:            17,
	SlugLynx:              18,
	SlugWonderSwan:        48,
	SlugWonderSwanColor:   49,
	SlugAmiga:             19,
	SlugAmigaCD:           56,
	SlugAmigaCD32:         56,
	SlugC128:              61,
	SlugC16:               115,
	SlugC64:               27,
	SlugCPlus4:            115,
	SlugCommodoreCDTV:     83,
	SlugVIC20:             43,
	SlugDOS:               2,
	SlugLinux:             1,
	SlugWin:               3,
	SlugWin3x:             5,
	SlugXbox:              13,
	SlugXbox360:           69,
	SlugXboxOne:           142,
	SlugSeriesXS:          289,
	SlugPC8800:            94,
	SlugPC9800:            95,
	SlugPCFX:              59,
	SlugSuperGrafx:        127,
	SlugTG16:              40,
	SlugTurboGrafxCD:      45,
	SlugNeoGeoCD:          54,
	SlugNeoGeoPocket:      52,
	SlugNeoGeoPocketColor: 53,
	SlugFamicom:           22,
	SlugFDS:               22,
	SlugN64:               9,
	SlugN64DD:             9,
	SlugNES:               22,
	SlugNGC:               14,
	SlugSatellaview:       15,
	SlugSFam:              15,
	SlugSNES:              15,
	SlugSwitch:            203,
	SlugWii:               82,
	SlugWiiU:              132,
	SlugGB:                10,
	SlugGBA:               12,
	SlugGBC:               11,
	SlugN3DS:              101,
	SlugNDS:               44,
	SlugNewNintendo3DS:    174,
	SlugNintendoDSi:       87,
	SlugVirtualBoy:        38,
	SlugPokemonMini:       152,
	SlugDC:                8,
	SlugGameGear:          25,
	SlugGenesis:           16,
	SlugSaturn:            23,
	SlugSega32:            21,
	SlugSegaCD:            20,
	SlugSegaCD32:          20,
	SlugSG1000:            114,
	SlugSMS:               26,
	SlugSegaPico:          103,
	SlugSharpX68000:       106,
	SlugX1:                121,
	SlugPocketstation:     147,
	SlugPS2:               7,
	SlugPS3:               81,
	SlugPS4:               141,
	SlugPS5:               288,
	SlugPSP:               46,
	SlugPSVita:            105,
	SlugPSVR:              286,
	SlugPSVR2:             286,
	SlugPSX:               6,
	SlugBBCMicro:          92,
	SlugMSX:               57,
	SlugMSX2:              57,
	SlugMSX2Plus:          57,
	SlugFMTowns:           102,
	SlugZXS:               41,
	SlugZX80:              119,
	SlugZX81:              120,
	SlugColecovision:      29,
	SlugFairchildChannelF: 76,
	SlugIntellvision:      30,
	SlugOdyssey2:          78,
	SlugVectrex:           37,
	SlugGamate:            189,
	SlugGameDotCom:        50,
	SlugGizmondo:          55,
	SlugSupervision:       109,
	SlugStadia:            273,
	SlugOuya:              144,
	SlugPlaydate:          298,
	SlugEvercade:          294,
}

// ScreenScraper platform ID mappings
var screenscraperPlatformMap = map[Slug]int{
	Slug3DO:               29,
	SlugN3DS:              17,
	SlugN64:               14,
	SlugArcade:            75,
	SlugAtari2600:         26,
	SlugAtari5200:         40,
	SlugAtari7800:         41,
	SlugC64:               66,
	SlugDC:                23,
	SlugDOS:               135,
	SlugFamicom:           3,
	SlugFDS:               106,
	SlugGB:                9,
	SlugGBA:               12,
	SlugGBC:               10,
	SlugGenesis:           1,
	SlugGameGear:          21,
	SlugJaguar:            27,
	SlugLynx:              28,
	SlugMSX:               113,
	SlugMSX2:              116,
	SlugNDS:               15,
	SlugNeoGeoCD:          70,
	SlugNeoGeoPocket:      25,
	SlugNeoGeoPocketColor: 82,
	SlugNeoGeoAES:         142,
	SlugNES:               3,
	SlugNGC:               13,
	SlugPCFX:              72,
	SlugPS2:               58,
	SlugPS3:               59,
	SlugPSP:               61,
	SlugPSVita:            62,
	SlugPSX:               57,
	SlugSaturn:            22,
	SlugSega32:            19,
	SlugSegaCD:            20,
	SlugSFam:              4,
	SlugSG1000:            109,
	SlugSMS:               2,
	SlugSNES:              4,
	SlugSuperGrafx:        105,
	SlugSwitch:            225,
	SlugTG16:              31,
	SlugTurboGrafxCD:      114,
	SlugVectrex:           102,
	SlugVirtualBoy:        11,
	SlugWii:               16,
	SlugWiiU:              18,
	SlugWonderSwan:        45,
	SlugWonderSwanColor:   46,
	SlugXbox:              32,
	SlugXbox360:           33,
	SlugZXS:               76,
}

// RetroAchievements platform ID mappings
var retroachievementsPlatformMap = map[Slug]int{
	Slug3DO:          43,
	SlugN64:          2,
	SlugArcade:       27,
	SlugAtari2600:    25,
	SlugAtari7800:    51,
	SlugDC:           40,
	SlugFamicom:      1,
	SlugGB:           4,
	SlugGBA:          5,
	SlugGBC:          6,
	SlugGenesis:      1,
	SlugGameGear:     15,
	SlugJaguar:       17,
	SlugLynx:         13,
	SlugMSX:          29,
	SlugNDS:          18,
	SlugNeoGeoPocket: 14,
	SlugNeoGeoAES:    27,
	SlugNES:          7,
	SlugNGC:          16,
	SlugPCFX:         49,
	SlugPS2:          21,
	SlugPSP:          41,
	SlugPSX:          12,
	SlugSaturn:       39,
	SlugSega32:       10,
	SlugSegaCD:       9,
	SlugSFam:         3,
	SlugSG1000:       33,
	SlugSMS:          11,
	SlugSNES:         3,
	SlugSuperGrafx:   8,
	SlugTG16:         8,
	SlugVectrex:      46,
	SlugVirtualBoy:   28,
	SlugWonderSwan:   53,
}

// GetIGDBPlatformID returns the IGDB platform ID for a universal platform slug.
func GetIGDBPlatformID(slug Slug) *int {
	if id, ok := igdbPlatformMap[slug]; ok {
		return &id
	}
	return nil
}

// GetMobyGamesPlatformID returns the MobyGames platform ID for a universal platform slug.
func GetMobyGamesPlatformID(slug Slug) *int {
	if id, ok := mobygamesPlatformMap[slug]; ok {
		return &id
	}
	return nil
}

// GetScreenScraperPlatformID returns the ScreenScraper platform ID for a universal platform slug.
func GetScreenScraperPlatformID(slug Slug) *int {
	if id, ok := screenscraperPlatformMap[slug]; ok {
		return &id
	}
	return nil
}

// GetRetroAchievementsPlatformID returns the RetroAchievements platform ID for a universal platform slug.
func GetRetroAchievementsPlatformID(slug Slug) *int {
	if id, ok := retroachievementsPlatformMap[slug]; ok {
		return &id
	}
	return nil
}

// GetPlatformInfo returns comprehensive platform information for a universal platform slug.
func GetPlatformInfo(slug Slug) *PlatformInfo {
	if !slug.IsValid() {
		return nil
	}

	return &PlatformInfo{
		Slug:                slug,
		Name:                slug.Name(),
		IGDBID:              GetIGDBPlatformID(slug),
		MobyGamesID:         GetMobyGamesPlatformID(slug),
		ScreenScraperID:     GetScreenScraperPlatformID(slug),
		RetroAchievementsID: GetRetroAchievementsPlatformID(slug),
	}
}

// SlugFromIGDBID returns the universal platform slug from an IGDB platform ID.
func SlugFromIGDBID(igdbID int) Slug {
	for slug, id := range igdbPlatformMap {
		if id == igdbID {
			return slug
		}
	}
	return ""
}

// SlugFromMobyGamesID returns the universal platform slug from a MobyGames platform ID.
func SlugFromMobyGamesID(mobyID int) Slug {
	for slug, id := range mobygamesPlatformMap {
		if id == mobyID {
			return slug
		}
	}
	return ""
}

// SlugFromScreenScraperID returns the universal platform slug from a ScreenScraper platform ID.
func SlugFromScreenScraperID(ssID int) Slug {
	for slug, id := range screenscraperPlatformMap {
		if id == ssID {
			return slug
		}
	}
	return ""
}

// SlugFromRetroAchievementsID returns the universal platform slug from a RetroAchievements platform ID.
func SlugFromRetroAchievementsID(raID int) Slug {
	for slug, id := range retroachievementsPlatformMap {
		if id == raID {
			return slug
		}
	}
	return ""
}
