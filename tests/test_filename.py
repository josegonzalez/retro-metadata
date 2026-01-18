"""Tests for the filename parsing utilities."""

import pytest

from retro_metadata.utils.filename import (
    clean_filename,
    extract_region,
    extract_tags,
    get_file_extension,
    is_bios_file,
    is_demo_file,
    is_unlicensed,
    parse_no_intro_filename,
)


class TestGetFileExtension:
    """Tests for get_file_extension function."""

    def test_basic_extension(self):
        """Test getting basic file extension."""
        assert get_file_extension("game.sfc") == "sfc"

    def test_uppercase_extension(self):
        """Test that extension is lowercased."""
        assert get_file_extension("game.SFC") == "sfc"

    def test_no_extension(self):
        """Test file with no extension."""
        assert get_file_extension("game") == ""

    def test_multiple_dots(self):
        """Test file with multiple dots."""
        assert get_file_extension("game.name.sfc") == "sfc"


class TestExtractTags:
    """Tests for extract_tags function."""

    def test_parentheses_tags(self):
        """Test extracting tags in parentheses."""
        tags = extract_tags("Super Mario World (USA).sfc")
        assert "USA" in tags

    def test_bracket_tags(self):
        """Test extracting tags in brackets."""
        tags = extract_tags("Super Mario World [!].sfc")
        assert "!" in tags

    def test_multiple_tags(self):
        """Test extracting multiple tags."""
        tags = extract_tags("Game (USA) (Rev 1) [!].sfc")
        assert "USA" in tags
        assert "Rev 1" in tags
        assert "!" in tags

    def test_no_tags(self):
        """Test file with no tags."""
        tags = extract_tags("game.sfc")
        assert tags == []


class TestExtractRegion:
    """Tests for extract_region function."""

    def test_usa_region(self):
        """Test extracting USA region."""
        assert extract_region("Game (USA).sfc") == "us"
        assert extract_region("Game (U).sfc") == "us"

    def test_europe_region(self):
        """Test extracting Europe region."""
        assert extract_region("Game (Europe).sfc") == "eu"
        assert extract_region("Game (E).sfc") == "eu"

    def test_japan_region(self):
        """Test extracting Japan region."""
        assert extract_region("Game (Japan).sfc") == "jp"
        assert extract_region("Game (J).sfc") == "jp"

    def test_world_region(self):
        """Test extracting World region."""
        assert extract_region("Game (World).sfc") == "wor"

    def test_comma_separated_regions(self):
        """Test comma-separated regions."""
        region = extract_region("Game (USA, Europe).sfc")
        assert region == "us"  # Returns first match

    def test_no_region(self):
        """Test file with no region."""
        assert extract_region("Game [!].sfc") is None


class TestCleanFilename:
    """Tests for clean_filename function."""

    def test_basic_cleaning(self):
        """Test basic filename cleaning."""
        result = clean_filename("Super Mario World (USA) [!].sfc")
        assert result == "Super Mario World"

    def test_keep_extension(self):
        """Test keeping the extension."""
        result = clean_filename("Super Mario World (USA).sfc", remove_extension=False)
        assert result == "Super Mario World.sfc"

    def test_multiple_tags(self):
        """Test removing multiple tags."""
        result = clean_filename("Game (USA) (Rev 1) [!] (En,Fr).sfc")
        assert result == "Game"

    def test_path_handling(self):
        """Test handling full paths."""
        result = clean_filename("/path/to/Game (USA).sfc")
        assert result == "Game"


class TestParseNoIntroFilename:
    """Tests for parse_no_intro_filename function."""

    def test_basic_parsing(self):
        """Test basic No-Intro filename parsing."""
        result = parse_no_intro_filename("Super Mario World (USA) (Rev 1).sfc")
        assert result["name"] == "Super Mario World"
        assert result["region"] == "us"
        assert result["extension"] == "sfc"

    def test_version_parsing(self):
        """Test parsing version tag."""
        result = parse_no_intro_filename("Game (USA) (Rev 2).sfc")
        assert result["version"] == "Rev 2"

    def test_all_tags(self):
        """Test that all tags are captured."""
        result = parse_no_intro_filename("Game (USA) (En,Fr) [!].sfc")
        assert "USA" in result["tags"]
        assert "En,Fr" in result["tags"]
        assert "!" in result["tags"]


class TestIsBiosFile:
    """Tests for is_bios_file function."""

    def test_bios_in_name(self):
        """Test detecting BIOS in name."""
        assert is_bios_file("[BIOS] PlayStation.bin")
        assert is_bios_file("BIOS - PlayStation.bin")

    def test_bios_in_brackets(self):
        """Test detecting BIOS tag."""
        assert is_bios_file("scph1001.bin [BIOS]")

    def test_not_bios(self):
        """Test non-BIOS files."""
        assert not is_bios_file("Super Mario World (USA).sfc")


class TestIsDemoFile:
    """Tests for is_demo_file function."""

    def test_demo_tag(self):
        """Test detecting demo tag."""
        assert is_demo_file("Game (Demo).bin")
        assert is_demo_file("Game (Sample).bin")

    def test_prototype_tag(self):
        """Test detecting prototype tag."""
        assert is_demo_file("Game (Proto).bin")
        assert is_demo_file("Game (Prototype).bin")

    def test_beta_tag(self):
        """Test detecting beta tag."""
        assert is_demo_file("Game (Beta).bin")

    def test_not_demo(self):
        """Test non-demo files."""
        assert not is_demo_file("Super Mario World (USA).sfc")


class TestIsUnlicensed:
    """Tests for is_unlicensed function."""

    def test_unlicensed_tag(self):
        """Test detecting unlicensed tag."""
        assert is_unlicensed("Game (Unl).bin")
        assert is_unlicensed("Game (Unlicensed).bin")

    def test_pirate_tag(self):
        """Test detecting pirate tag."""
        assert is_unlicensed("Game (Pirate).bin")

    def test_hack_tag(self):
        """Test detecting hack tag."""
        assert is_unlicensed("Game (Hack).bin")

    def test_not_unlicensed(self):
        """Test licensed files."""
        assert not is_unlicensed("Super Mario World (USA).sfc")
