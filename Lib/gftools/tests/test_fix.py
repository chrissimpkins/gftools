from fontTools.ttLib import newTable, TTFont
from gftools.fix import *
import pytest
import os
from copy import deepcopy


@pytest.fixture
def static_font():
    return TTFont(os.path.join("data", "test", "Lora-Regular.ttf"))


@pytest.fixture
def var_font():
    return TTFont(os.path.join("data", "test", "Inconsolata[wdth,wght].ttf"))


def test_remove_tables(static_font):
    # Test removing a table which is part of UNWANTED_TABLES
    tsi1_tbl = newTable("TSI1")
    static_font["TSI1"] = tsi1_tbl
    assert "TSI1" in static_font

    tsi2_tbl = newTable("TSI2")
    static_font["TSI2"] = tsi2_tbl
    remove_tables(static_font, ["TSI1", "TSI2"])
    assert "TSI1" not in static_font
    assert "TSI2" not in static_font

    # Test removing a table which is essential
    remove_tables(static_font, ["glyf"])
    assert "glyf" in static_font


def test_add_dummy_dsig(static_font):
    assert "DSIG" not in static_font
    add_dummy_dsig(static_font)
    assert "DSIG" in static_font


def test_fix_hinted_font(static_font):
    static_font["head"].flags &= ~(1 << 3)
    assert static_font["head"].flags & (1 << 3) != (1 << 3)
    fix_hinted_font(static_font)
    assert static_font["head"].flags & (1 << 3) == (1 << 3)


def test_fix_unhinted_font(static_font):
    for tbl in ("prep", "gasp"):
        if tbl in static_font:
            del static_font[tbl]

    fix_unhinted_font(static_font)
    assert static_font["gasp"].gaspRange == {65535: 15}
    assert "prep" in static_font


def test_fix_fs_type(static_font):
    static_font["OS/2"].fsType = 1
    assert static_font["OS/2"].fsType == 1
    fix_fs_type(static_font)
    assert static_font["OS/2"].fsType == 0


# Taken from https://github.com/googlefonts/gf-docs/tree/master/Spec#supported-styles
STYLE_HEADERS = "style, weight_class, fs_selection, mac_style"
STYLE_TABLE = [
    ("Thin", 100, (1 << 6), (0 << 0)),
    ("ExtraLight", 200, (1 << 6), (0 << 0)),
    ("Light", 300, (1 << 6), (0 << 0)),
    ("Regular", 400, (1 << 6), (0 << 0)),
    ("Medium", 500, (1 << 6), (0 << 0)),
    ("SemiBold", 600, (1 << 6), (0 << 0)),
    ("Bold", 700, (1 << 5), (1 << 0)),
    ("ExtraBold", 800, (1 << 6), (0 << 0)),
    ("Black", 900, (1 << 6), (0 << 0)),
    ("Thin Italic", 100, (1 << 0), (1 << 1)),
    ("ExtraLight Italic", 200, (1 << 0), (1 << 1)),
    ("Light Italic", 300, (1 << 0), (1 << 1)),
    ("Italic", 400, (1 << 0), (1 << 1)),
    ("Medium Italic", 500, (1 << 0), (1 << 1)),
    ("SemiBold Italic", 600, (1 << 0), (1 << 1)),
    ("Bold Italic", 700, (1 << 0) | (1 << 5), (1 << 0) | (1 << 1)),
    ("ExtraBold Italic", 800, (1 << 0), (1 << 1)),
    ("Black Italic", 900, (1 << 0), (1 << 1)),
    # Variable fonts may have tokens other than weight and italic in their names
    ("SemiCondensed Bold Italic", 700, (1 << 0) | (1 << 5), (1 << 0) | (1 << 1)),
    ("12pt Italic", 400, (1 << 0), (1 << 1)),
]

@pytest.mark.parametrize(
    STYLE_HEADERS,
    STYLE_TABLE
)
def test_fix_weight_class(static_font, style, weight_class, fs_selection, mac_style):
    name = static_font["name"]
    name.setName(style, 2, 3, 1, 0x409)
    name.setName(style, 17, 3, 1, 0x409)
    fix_weight_class(static_font)
    assert static_font["OS/2"].usWeightClass == weight_class


def test_unknown_weight_class(static_font):
    name = static_font["name"]
    name.setName("Foobar", 2, 3, 1, 0x409)
    name.setName("Foobar", 17, 3, 1, 0x409)
    from gftools.fix import WEIGHT_NAMES

    with pytest.raises(ValueError, match="Cannot determine usWeightClass"):
        fix_weight_class(static_font)


@pytest.mark.parametrize(
    STYLE_HEADERS,
    STYLE_TABLE
)
def test_fs_selection(static_font, style, weight_class, fs_selection, mac_style):
    # disable fsSelection bits above 6
    for i in range(7, 12):
        static_font["OS/2"].fsSelection &= ~(1 << i)
    name = static_font["name"]
    name.setName(style, 2, 3, 1, 0x409)
    name.setName(style, 17, 3, 1, 0x409)
    fix_fs_selection(static_font)
    assert static_font["OS/2"].fsSelection == fs_selection


@pytest.mark.parametrize(
    STYLE_HEADERS,
    STYLE_TABLE
)
def test_fix_mac_style(static_font, style, weight_class, fs_selection, mac_style):
    name = static_font["name"]
    name.setName(style, 2, 3, 1, 0x409)
    name.setName(style, 17, 3, 1, 0x409)
    fix_mac_style(static_font)
    assert static_font["head"].macStyle == mac_style


STYLENAME_HEADERS = "family_name, style, id1, id2, id16, id17"
STYLENAME_TABLE = [
    # Roman
    ("Test Family", "Thin", "Test Family Thin", "Regular", "Test Family", "Thin"),
    ("Test Family", "ExtraLight", "Test Family ExtraLight", "Regular", "Test Family", "ExtraLight"),
    ("Test Family", "Light", "Test Family Light", "Regular", "Test Family", "Light"),
    ("Test Family", "Regular", "Test Family", "Regular", "", ""),
    ("Test Family", "Medium", "Test Family Medium", "Regular", "Test Family", "Medium"),
    ("Test Family", "SemiBold", "Test Family SemiBold", "Regular", "Test Family", "SemiBold"),
    ("Test Family", "Bold", "Test Family", "Bold", "", ""),
    ("Test Family", "ExtraBold", "Test Family ExtraBold", "Regular", "Test Family", "ExtraBold"),
    # Italics
    ("Test Family", "Thin Italic", "Test Family Thin", "Italic", "Test Family", "Thin Italic"),
    ("Test Family", "ExtraLight Italic", "Test Family ExtraLight", "Italic", "Test Family", "ExtraLight Italic"),
    ("Test Family", "Light Italic", "Test Family Light", "Italic", "Test Family", "Light Italic"),
    ("Test Family", "Italic", "Test Family", "Italic", "", ""),
    ("Test Family", "Medium Italic", "Test Family Medium", "Italic", "Test Family", "Medium Italic"),
    ("Test Family", "SemiBold Italic", "Test Family SemiBold", "Italic", "Test Family", "SemiBold Italic"),
    ("Test Family", "Bold Italic", "Test Family", "Bold Italic", "", ""),
    ("Test Family", "ExtraBold Italic", "Test Family ExtraBold", "Italic", "Test Family", "ExtraBold Italic"),
    ("Test Family", "Black Italic", "Test Family Black", "Italic", "Test Family", "Black Italic"),
    ("Test Family", "Black", "Test Family Black", "Regular", "Test Family", "Black"),
]
@pytest.mark.parametrize(
    STYLENAME_HEADERS,
    STYLENAME_TABLE
)
def test_update_nametable(static_font, family_name, style, id1, id2, id16, id17):
    update_nametable(static_font, family_name, style)
    nametable = static_font["name"]
    assert nametable.getName(1, 3, 1, 0x409).toUnicode() == id1
    assert nametable.getName(2, 3, 1, 0x409).toUnicode() == id2
    if id16 and id17:
        assert nametable.getName(16, 3, 1, 0x409).toUnicode() == id16
        assert nametable.getName(17, 3, 1, 0x409).toUnicode() == id17
    else:
        assert nametable.getName(16, 3, 1, 0x409) == None
        assert nametable.getName(17, 3, 1, 0x409) == None


# TODO test fix_nametable once https://github.com/fonttools/fonttools/pull/2078 is merged


def _get_fvar_instance_names(var_font):
    inst_names = []
    for inst in var_font['fvar'].instances:
        inst_name = var_font['name'].getName(inst.subfamilyNameID, 3, 1, 0x409)
        inst_names.append(inst_name.toUnicode())
    return inst_names


def test_fix_fvar_instances(var_font):
    roman_instances = [
        "ExtraLight",
        "Light",
        "Regular",
        "Medium",
        "SemiBold",
        "Bold",
        "ExtraBold",
        "Black"
    ]
    italic_instances = [
        "ExtraLight Italic",
        "Light Italic",
        "Italic",
        "Medium Italic",
        "SemiBold Italic",
        "Bold Italic",
        "ExtraBold Italic",
        "Black Italic",
    ]
    var_font["fvar"].instances = []

    fix_fvar_instances(var_font)
    inst_names = _get_fvar_instance_names(var_font)
    assert inst_names == roman_instances


    # Let's rename the font style so the font becomes an Italic variant
    var_font2 = deepcopy(var_font)
    var_font2["name"].setName("Italic", 2, 3, 1, 0x409)
    var_font2["name"].setName("Italic", 17, 3, 1, 0x409)

    fix_fvar_instances(var_font2)
    inst_names = _get_fvar_instance_names(var_font2)
    assert inst_names == italic_instances


    # Let's mock an ital axis so the font has both ital and wght axes
    new_fvar = deepcopy(var_font["fvar"])
    new_fvar.axes[1].axisTag = "ital"
    new_fvar.axes[1].minValue = 0
    new_fvar.axes[1].maxValue = 1
    new_fvar.axes[1].defaultValue = 0

    var_font3 = deepcopy(var_font)
    var_font3['fvar'] = new_fvar
    fix_fvar_instances(var_font3)

    inst_names = _get_fvar_instance_names(var_font3)
    assert inst_names == roman_instances + italic_instances
