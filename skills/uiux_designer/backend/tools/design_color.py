"""
Design Color tool — pure-math color system generation.

Actions: generate_palette, check_contrast, dark_mode, semantic_colors
Uses HSL manipulation and WCAG 2.1 relative luminance formula.
"""

import math
import json
from typing import Any, Dict, List, Tuple


# --- Color Math Utilities ---

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex (#RRGGBB or #RGB) to (R, G, B) tuple."""
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex string."""
    return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"


def _rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB (0-255) to HSL (h:0-360, s:0-100, l:0-100)."""
    r1, g1, b1 = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(r1, g1, b1), min(r1, g1, b1)
    l = (mx + mn) / 2.0
    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r1:
            h = (g1 - b1) / d + (6 if g1 < b1 else 0)
        elif mx == g1:
            h = (b1 - r1) / d + 2
        else:
            h = (r1 - g1) / d + 4
        h /= 6.0
    return round(h * 360, 1), round(s * 100, 1), round(l * 100, 1)


def _hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL (h:0-360, s:0-100, l:0-100) to RGB (0-255)."""
    h1, s1, l1 = h / 360.0, s / 100.0, l / 100.0
    if s1 == 0:
        v = int(round(l1 * 255))
        return v, v, v

    def hue2rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    q = l1 * (1 + s1) if l1 < 0.5 else l1 + s1 - l1 * s1
    p = 2 * l1 - q
    r = hue2rgb(p, q, h1 + 1/3)
    g = hue2rgb(p, q, h1)
    b = hue2rgb(p, q, h1 - 1/3)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


def _relative_luminance(r: int, g: int, b: int) -> float:
    """WCAG 2.1 relative luminance calculation."""
    def linearize(c):
        c1 = c / 255.0
        return c1 / 12.92 if c1 <= 0.03928 else ((c1 + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    l1 = _relative_luminance(*_hex_to_rgb(color1))
    l2 = _relative_luminance(*_hex_to_rgb(color2))
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def _adjust_for_contrast(fg_hex: str, bg_hex: str, target_ratio: float = 4.5) -> str:
    """Auto-adjust foreground lightness until WCAG target is met."""
    r, g, b = _hex_to_rgb(fg_hex)
    h, s, l = _rgb_to_hsl(r, g, b)
    bg_lum = _relative_luminance(*_hex_to_rgb(bg_hex))

    # Determine direction: darken if bg is light, lighten if bg is dark
    direction = -1 if bg_lum > 0.5 else 1

    for _ in range(100):
        rgb = _hsl_to_rgb(h, s, l)
        current_hex = _rgb_to_hex(*rgb)
        ratio = _contrast_ratio(current_hex, bg_hex)
        if ratio >= target_ratio:
            return current_hex
        l += direction * 1.0
        if l < 0 or l > 100:
            break
    return fg_hex  # Return original if can't meet target


# --- Palette Generation ---

WARM_ORGANIC_BASE = {
    "primary": {"h": 24, "s": 80, "l": 55},      # Warm amber/orange
    "secondary": {"h": 16, "s": 65, "l": 48},     # Terracotta
    "neutral": {"h": 30, "s": 10, "l": 50},       # Warm gray (stone)
    "accent": {"h": 35, "s": 90, "l": 60},        # Golden
    "success": {"h": 145, "s": 55, "l": 42},      # Warm green
    "warning": {"h": 38, "s": 92, "l": 50},       # Amber
    "error": {"h": 0, "s": 72, "l": 51},          # Warm red
    "info": {"h": 200, "s": 60, "l": 50},         # Soft blue
}


def _generate_shade_scale(h: float, s: float, l: float, name: str) -> Dict:
    """Generate 50-950 shade scale from a base HSL color."""
    shades = {}
    steps = [
        ("50", 97), ("100", 93), ("200", 86), ("300", 76),
        ("400", 64), ("500", l), ("600", 43), ("700", 35),
        ("800", 27), ("900", 20), ("950", 12),
    ]
    for label, lightness in steps:
        # Desaturate slightly at extremes
        sat_adjust = s * 0.6 if lightness > 90 else (s * 0.85 if lightness < 20 else s)
        rgb = _hsl_to_rgb(h, sat_adjust, lightness)
        hex_val = _rgb_to_hex(*rgb)
        shades[label] = {
            "hex": hex_val,
            "hsl": f"hsl({h}, {round(sat_adjust)}%, {lightness}%)"
        }
    return {"name": name, "shades": shades}


def _generate_palette(args: Dict) -> Dict:
    """Generate a full color palette."""
    style = args.get("style", "warm-organic")
    base_color = args.get("base_color")  # Optional hex override
    roles = args.get("roles", ["primary", "secondary", "neutral", "accent"])

    palette = {}

    if base_color:
        r, g, b = _hex_to_rgb(base_color)
        h, s, l = _rgb_to_hsl(r, g, b)
        palette["primary"] = _generate_shade_scale(h, s, l, "primary")
        # Generate complementary
        palette["secondary"] = _generate_shade_scale((h + 30) % 360, s * 0.8, l, "secondary")
        palette["neutral"] = _generate_shade_scale(h, 10, 50, "neutral")
        palette["accent"] = _generate_shade_scale((h + 180) % 360, s * 0.7, l + 5, "accent")
    else:
        base = WARM_ORGANIC_BASE
        for role in roles:
            if role in base:
                b = base[role]
                palette[role] = _generate_shade_scale(b["h"], b["s"], b["l"], role)

    # Add semantic colors
    for sem in ["success", "warning", "error", "info"]:
        if sem in WARM_ORGANIC_BASE:
            b = WARM_ORGANIC_BASE[sem]
            palette[sem] = _generate_shade_scale(b["h"], b["s"], b["l"], sem)

    return {
        "style": style,
        "palette": palette,
        "tokens_format": "w3c-dtcg",
        "usage_note": "Use 500 as base, 50-100 for backgrounds, 700-900 for text"
    }


def _check_contrast(args: Dict) -> Dict:
    """Check contrast ratio between two colors."""
    fg = args.get("foreground", "#000000")
    bg = args.get("background", "#ffffff")
    ratio = _contrast_ratio(fg, bg)

    wcag_aa_normal = ratio >= 4.5
    wcag_aa_large = ratio >= 3.0
    wcag_aaa_normal = ratio >= 7.0
    wcag_aaa_large = ratio >= 4.5

    result = {
        "foreground": fg,
        "background": bg,
        "contrast_ratio": ratio,
        "wcag_aa_normal_text": "PASS" if wcag_aa_normal else "FAIL",
        "wcag_aa_large_text": "PASS" if wcag_aa_large else "FAIL",
        "wcag_aaa_normal_text": "PASS" if wcag_aaa_normal else "FAIL",
        "wcag_aaa_large_text": "PASS" if wcag_aaa_large else "FAIL",
    }

    if not wcag_aa_normal:
        adjusted = _adjust_for_contrast(fg, bg, 4.5)
        result["suggested_foreground"] = adjusted
        result["suggested_ratio"] = _contrast_ratio(adjusted, bg)
        result["adjustment_note"] = "Auto-adjusted lightness to meet WCAG AA (4.5:1)"

    return result


def _dark_mode(args: Dict) -> Dict:
    """Generate dark mode variant of a color palette."""
    colors = args.get("colors", {})
    if not colors:
        return {"error": "Provide 'colors' dict with role:hex pairs"}

    dark_palette = {}
    for role, hex_val in colors.items():
        r, g, b = _hex_to_rgb(hex_val)
        h, s, l = _rgb_to_hsl(r, g, b)

        if role == "neutral" or "background" in role or "surface" in role:
            # Invert lightness for backgrounds
            dark_l = max(5, 100 - l - 10)
            dark_s = s * 0.7
        else:
            # Slightly desaturate and lighten for readability on dark
            dark_l = min(80, l + 15)
            dark_s = min(100, s * 0.85)

        dark_rgb = _hsl_to_rgb(h, dark_s, dark_l)
        dark_hex = _rgb_to_hex(*dark_rgb)

        # Verify contrast against dark background (#1a1a1a)
        ratio = _contrast_ratio(dark_hex, "#1a1a1a")
        if ratio < 4.5 and role not in ("neutral", "background", "surface"):
            dark_hex = _adjust_for_contrast(dark_hex, "#1a1a1a", 4.5)

        dark_palette[role] = {
            "hex": dark_hex,
            "original": hex_val,
            "contrast_on_dark": _contrast_ratio(dark_hex, "#1a1a1a")
        }

    return {
        "mode": "dark",
        "background": "#1a1a1a",
        "surface": "#262626",
        "colors": dark_palette
    }


def _semantic_colors(args: Dict) -> Dict:
    """Generate semantic color tokens for a design system."""
    base_color = args.get("base_color")
    style = args.get("style", "warm-organic")

    if base_color:
        r, g, b = _hex_to_rgb(base_color)
        h, s, l = _rgb_to_hsl(r, g, b)
    else:
        h, s, l = 24, 80, 55  # Warm Organic default

    tokens = {
        "$type": "color",
        "brand": {
            "primary": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, s, l))},
            "primary-hover": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, s, l - 8))},
            "primary-active": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, s, l - 15))},
            "secondary": {"$value": _rgb_to_hex(*_hsl_to_rgb((h + 30) % 360, s * 0.8, l))},
        },
        "text": {
            "primary": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 8, 12))},
            "secondary": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 6, 40))},
            "tertiary": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 5, 60))},
            "inverse": {"$value": "#ffffff"},
        },
        "background": {
            "default": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 15, 98))},
            "subtle": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 12, 95))},
            "muted": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 10, 90))},
        },
        "border": {
            "default": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 10, 85))},
            "strong": {"$value": _rgb_to_hex(*_hsl_to_rgb(h, 10, 70))},
        },
        "feedback": {
            "success": {"$value": "#2d8a56"},
            "warning": {"$value": "#d4860a"},
            "error": {"$value": "#c53030"},
            "info": {"$value": "#3182ce"},
        }
    }

    return {"format": "w3c-dtcg", "tokens": tokens}


# --- Main Execute ---

def execute(agent: dict, args: dict) -> dict:
    """Execute design_color tool."""
    action = args.get("action", "generate_palette")

    actions = {
        "generate_palette": _generate_palette,
        "check_contrast": _check_contrast,
        "dark_mode": _dark_mode,
        "semantic_colors": _semantic_colors,
    }

    if action not in actions:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Available: {list(actions.keys())}"
        }

    try:
        result = actions[action](args)
        return {"status": "ok", "action": action, "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
