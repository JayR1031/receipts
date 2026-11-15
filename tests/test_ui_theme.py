"""The UI's theme, CSS and header (lane L5): the look the landing page sets. No network."""

from __future__ import annotations

import base64
import re
import struct
from importlib.resources import files

import gradio as gr
from gradio.themes import Base as BaseTheme
from gradio.themes.utils import colors

import receipts.ui.app as ui_app
from receipts.fakes import FakeRunService
from receipts.ui.theme import (
    CSS,
    HEADER_HTML,
    LANDING_URL,
    LOGO_ALT,
    LOGO_DATA_URI,
    TAGLINE,
    THEME,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
DATA_URI_PREFIX = "data:image/png;base64,"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
# The two status colours (emerald-400, red-400) are the only chromatic values allowed.
STATUS_COLOURS = {"#34d399", "#f87171"}
HUES = ("primary", "secondary", "neutral")
SHADES = ("50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950")


def _packaged_logo() -> bytes:
    return files("receipts.ui").joinpath("assets", "logo.png").read_bytes()


def _is_grey(hex_colour: str) -> bool:
    r, g, b = (hex_colour[i : i + 2].lower() for i in (1, 3, 5))
    return r == g == b


def test_logo_is_embedded_as_a_png_data_uri_of_the_packaged_asset() -> None:
    assert LOGO_DATA_URI.startswith(DATA_URI_PREFIX)
    decoded = base64.b64decode(LOGO_DATA_URI.removeprefix(DATA_URI_PREFIX), validate=True)
    assert decoded.startswith(PNG_MAGIC)
    assert decoded == _packaged_logo()
    # IHDR width and height: the header's 142x32 box assumes the owner's 640x144 asset
    assert struct.unpack(">II", decoded[16:24]) == (640, 144)


def test_header_shows_the_logo_with_alt_text_the_tagline_and_the_about_link() -> None:
    assert f'src="{LOGO_DATA_URI}"' in HEADER_HTML
    assert f'alt="{LOGO_ALT}"' in HEADER_HTML
    assert LOGO_ALT == "Receipts"
    assert TAGLINE in HEADER_HTML
    assert f'href="{LANDING_URL}"' in HEADER_HTML
    assert LANDING_URL == "https://receipts-landing-nine.vercel.app"
    assert ">About<" in HEADER_HTML
    # an outbound link opened in a new tab must not hand the page a window.opener
    assert 'rel="noopener noreferrer"' in HEADER_HTML


def test_theme_and_css_are_importable_and_the_app_uses_them() -> None:
    assert isinstance(THEME, BaseTheme)
    assert isinstance(CSS, str) and CSS.strip()
    assert ui_app.THEME is THEME
    assert ui_app.CSS is CSS


def test_build_ui_puts_the_header_first(fake_run_service: FakeRunService) -> None:
    blocks = ui_app.build_ui(fake_run_service)
    htmls = [b for b in blocks.blocks.values() if isinstance(b, gr.HTML)]
    assert [h.value for h in htmls] == [HEADER_HTML]
    first = min(blocks.blocks.values(), key=lambda b: b._id)
    assert first is htmls[0], "the header is not the first component"


def test_no_emerald_primary_hue_remains() -> None:
    emerald = {getattr(colors.emerald, f"c{shade}").lower() for shade in SHADES}
    for hue in HUES:
        for shade in SHADES:
            value = str(getattr(THEME, f"{hue}_{shade}")).lower()
            assert value not in emerald, f"{hue}_{shade} is emerald ({value})"
            assert _is_grey(value), f"{hue}_{shade} is not a grey ({value})"


def test_every_variable_has_the_same_value_in_light_and_dark_mode() -> None:
    values = {k: v for k, v in vars(THEME).items() if isinstance(v, str)}
    pairs = [k.removesuffix("_dark") for k in values if k.endswith("_dark")]
    assert pairs, "no _dark variables found"
    differ = {
        k: (values[k], values[f"{k}_dark"]) for k in pairs if values[k] != values[f"{k}_dark"]
    }
    assert differ == {}


def test_buttons_are_monochrome_in_light_and_dark_mode() -> None:
    for suffix in ("", "_dark"):
        assert getattr(THEME, f"button_primary_background_fill{suffix}").lower() == "#ffffff"
        assert getattr(THEME, f"button_primary_text_color{suffix}").lower() == "#000000"
        assert getattr(THEME, f"button_primary_background_fill_hover{suffix}").lower() == "#e5e5e5"
        assert getattr(THEME, f"button_secondary_background_fill{suffix}") == "transparent"
        assert getattr(THEME, f"body_background_fill{suffix}").lower() == "#000000"


def test_the_only_chromatic_colours_are_the_two_status_colours() -> None:
    theme_values = [v for k, v in vars(THEME).items() if isinstance(v, str) and k != "name"]
    found = {_expand_3_to_6_hex(c) for text in [*theme_values, CSS] for c in _css_hex_colours(text)}
    chromatic = {c for c in found if not _is_grey(c)}
    assert chromatic <= STATUS_COLOURS, f"unexpected colours: {sorted(chromatic - STATUS_COLOURS)}"
    rgb = {m for text in [*theme_values, CSS] for m in RGB.findall(text)}
    assert all(r == g == b for r, g, b in rgb), f"non-grey rgb() values: {sorted(rgb)}"


def test_no_theme_font_is_fetched_from_a_third_party() -> None:
    """Fonts must not load from Google (or any host): a visitor's IP would go to a third party
    that ADR-0004 doesn't list. Plain family names resolve locally and fetch nothing."""
    from gradio.themes import Font

    from receipts.ui.theme import THEME

    fonts = [*THEME._font, *THEME._font_mono]
    fetched = [f.name for f in fonts if isinstance(f, Font) and f.stylesheet()["url"]]
    assert fetched == []


def _hex_channel(hex_pair: str) -> float:
    return int(hex_pair, 16) / 255.0


def _srgb_to_linear(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_colour: str) -> float:
    r = _srgb_to_linear(_hex_channel(hex_colour[1:3]))
    g = _srgb_to_linear(_hex_channel(hex_colour[3:5]))
    b = _srgb_to_linear(_hex_channel(hex_colour[5:7]))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg: str, bg: str) -> float:
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def _expand_hex_colour(colour: str) -> str:
    colour = colour.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{6}", colour):
        return colour
    if re.fullmatch(r"#[0-9a-f]{3}", colour):
        return "#" + "".join(ch * 2 for ch in colour[1:])
    raise ValueError(f"unsupported colour format: {colour!r}")


def _theme_colour(attr: str) -> str:
    value = str(getattr(THEME, attr))
    return _expand_hex_colour(value)


def test_css_guards_no_imports_and_no_external_urls() -> None:
    assert "@import" not in CSS
    assert "@font-face" not in CSS
    assert re.search(r"url\(\s*['\"]?\s*(https?:)?//", CSS, flags=re.IGNORECASE) is None


def test_tagline_constant_matches_the_product_copy() -> None:
    assert TAGLINE == "Every claim carries a receipt."


def _css_hex_colours(text: str) -> set[str]:
    return {m.group(0).lower() for m in re.finditer(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", text)}


def _expand_3_to_6_hex(colour: str) -> str:
    c = colour.lower()
    if re.fullmatch(r"#[0-9a-f]{3}", c):
        return "#" + "".join(ch * 2 for ch in c[1:])
    return c


def _theme_string_values() -> list[str]:
    return [v for k, v in vars(THEME).items() if isinstance(v, str) and k != "name"]


CSS_NAMED_COLOURS = {
    "aliceblue",
    "antiquewhite",
    "aqua",
    "aquamarine",
    "azure",
    "beige",
    "bisque",
    "black",
    "blanchedalmond",
    "blue",
    "blueviolet",
    "brown",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "cyan",
    "darkblue",
    "darkcyan",
    "darkgoldenrod",
    "darkgray",
    "darkgreen",
    "darkgrey",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "darksalmon",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkslategrey",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dimgrey",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "ghostwhite",
    "gold",
    "goldenrod",
    "gray",
    "green",
    "greenyellow",
    "grey",
    "honeydew",
    "hotpink",
    "indianred",
    "indigo",
    "ivory",
    "khaki",
    "lavender",
    "lavenderblush",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightcyan",
    "lightgoldenrodyellow",
    "lightgray",
    "lightgreen",
    "lightgrey",
    "lightpink",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightslategrey",
    "lightsteelblue",
    "lightyellow",
    "lime",
    "limegreen",
    "linen",
    "magenta",
    "maroon",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orange",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "pink",
    "plum",
    "powderblue",
    "purple",
    "rebeccapurple",
    "red",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "silver",
    "skyblue",
    "slateblue",
    "slategray",
    "slategrey",
    "snow",
    "springgreen",
    "steelblue",
    "tan",
    "teal",
    "thistle",
    "tomato",
    "turquoise",
    "violet",
    "wheat",
    "white",
    "whitesmoke",
    "yellow",
    "yellowgreen",
}


def test_theme_colours_have_no_named_tokens_and_no_hsl_or_hsla() -> None:
    theme_values = [str(v).strip().lower() for v in _theme_string_values()]
    named_theme = [v for v in theme_values if v in CSS_NAMED_COLOURS]
    assert named_theme == [], f"named theme colours found: {sorted(set(named_theme))}"

    raw = "\n".join([*theme_values, CSS]).lower()
    scrubbed = re.sub(r"url\(\"data:image/svg\+xml,.*?\"\)", "", raw)

    css_named = re.findall(r"\b[a-z]+\b", scrubbed)
    offenders = sorted({tok for tok in css_named if tok in CSS_NAMED_COLOURS})
    assert offenders == [], f"named CSS colours found: {offenders}"

    assert re.search(r"hsla?\(", scrubbed) is None


def test_all_hex_colours_are_6_digit_or_3_digit_only_no_4_or_8_digit_alpha() -> None:
    theme_values = _theme_string_values()
    raw = "\n".join([*theme_values, CSS])

    bad = re.findall(r"#[0-9a-fA-F]{4}\b|#[0-9a-fA-F]{8}\b", raw)
    assert bad == [], f"alpha hex colours found: {sorted(set(bad))}"


def test_wcag_contrast_for_secondary_text_and_focus_border_is_at_least_4_5_to_1() -> None:
    bg = _theme_colour("body_background_fill")
    secondary = _theme_colour("body_text_color_subdued")
    focus = _theme_colour("border_color_accent")

    assert _contrast_ratio(secondary, bg) >= 4.5
    assert _contrast_ratio(focus, bg) >= 4.5


def test_status_class_rules_are_present_with_expected_colours() -> None:
    assert ".status-verified { color: #34d399; }" in CSS
    assert ".status-dropped { color: #f87171; }" in CSS
