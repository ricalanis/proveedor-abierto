"""AA contrast for the Comprobante palette: the OKLCH tokens in tokens.css, converted to sRGB here (no browser), for
the text/background pairs the templates actually use, in both themes. Text needs 4.5:1; stamp and rule shapes that
carry status need 3:1 (WCAG 1.4.11, non-text contrast)."""

import math
import re
from pathlib import Path

import pytest

TOKENS = Path(__file__).parents[1] / "app" / "proveedor_app" / "static" / "tokens.css"
DECL = re.compile(r"--([\w-]+):\s*oklch\(\s*([\d.]+)%\s+([\d.]+)\s+([\d.]+)\s*\)")


def oklch_to_srgb(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    """OKLCH (L in 0..1) -> linear sRGB, clipped to the gamut the way a browser paints it (per channel)."""
    a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    lc, mc, sc = l_ ** 3, m_ ** 3, s_ ** 3
    rgb = (4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc,
           -1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc,
           -0.0041960863 * lc - 0.7034186147 * mc + 1.7076147010 * sc)
    return tuple(min(1.0, max(0.0, c)) for c in rgb)


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb  # already linear
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: tuple, bg: tuple) -> float:
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def themes() -> dict[str, dict[str, tuple]]:
    css = TOKENS.read_text()
    light_block, dark_block = css.split("@media (prefers-color-scheme: dark)", 1)
    parse = lambda block: {m[0]: oklch_to_srgb(float(m[1]) / 100, float(m[2]), float(m[3]))
                           for m in DECL.findall(block)}
    light = parse(light_block)
    return {"light": light, "dark": {**light, **parse(dark_block)}}


TEXT_PAIRS = [  # (foreground, background): every place these tokens are text on that surface
    ("color-ink", "color-paper"), ("color-ink", "color-slip"), ("color-ink", "color-paper-2"),
    ("color-ink", "color-signal-soft"), ("color-ink", "color-marker"), ("color-ink", "color-marker-soft"),
    ("color-ink-2", "color-paper"), ("color-ink-2", "color-slip"), ("color-ink-2", "color-signal-soft"),
    ("color-ink-2", "color-marker-soft"), ("color-ink-2", "color-paper-2"),
    ("color-ink-3", "color-paper"), ("color-ink-3", "color-slip"), ("color-ink-3", "color-paper-2"),
    ("color-stamp", "color-paper"), ("color-stamp", "color-slip"), ("color-stamp", "color-marker-soft"),
    ("color-signal", "color-paper"), ("color-signal", "color-slip"), ("color-signal", "color-signal-soft"),
    ("color-missing", "color-slip"), ("color-missing", "color-paper"),
    ("color-paper", "color-ink"), ("color-paper", "color-stamp"),  # buttons, the stamped ticker
]
SHAPE_PAIRS = [("color-signal-bright", "color-signal-soft"), ("color-signal-bright", "color-paper"),
               ("color-rule-strong", "color-paper"), ("color-focus", "color-paper"), ("color-focus", "color-slip")]


def test_conversion_matches_known_colours():
    white, black = oklch_to_srgb(1.0, 0, 0), oklch_to_srgb(0.0, 0, 0)
    assert contrast(white, black) == pytest.approx(21, abs=0.05)
    # oklch(62.8% 0.2577 29.23) is sRGB red (#ff0000): linear (1, 0, 0) within rounding
    assert oklch_to_srgb(0.628, 0.2577, 29.23) == pytest.approx((1, 0, 0), abs=0.01)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_pairs_meet_aa(theme):
    t = themes()[theme]
    low = {f"{fg} on {bg}": round(contrast(t[fg], t[bg]), 2) for fg, bg in TEXT_PAIRS if contrast(t[fg], t[bg]) < 4.5}
    assert low == {}


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_status_shapes_meet_non_text_contrast(theme):
    t = themes()[theme]
    low = {f"{fg} on {bg}": round(contrast(t[fg], t[bg]), 2) for fg, bg in SHAPE_PAIRS if contrast(t[fg], t[bg]) < 3}
    assert low == {}


def test_signals_are_amber_never_red():
    hues = [float(m[3]) for m in DECL.findall(TOKENS.read_text()) if m[0].startswith("color-signal")]
    assert len(hues) == 6 and all(50 <= h <= 80 for h in hues)  # 3 signal tokens x 2 themes, all in the amber band
