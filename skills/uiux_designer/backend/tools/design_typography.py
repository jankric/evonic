"""
design_typography — Typography system generation.

Actions: type_scale, font_pairing, line_height, tracking
Pure math: modular scale ratios, golden ratio calculations.
"""

import json
import math

# Modular scale ratios
SCALE_RATIOS = {
    "minor-second": 1.067,
    "major-second": 1.125,
    "minor-third": 1.2,
    "major-third": 1.25,
    "perfect-fourth": 1.333,
    "augmented-fourth": 1.414,
    "perfect-fifth": 1.5,
    "golden-ratio": 1.618,
}

# Curated font pairings (Warm Organic defaults first)
FONT_PAIRINGS = {
    "warm-organic": {
        "heading": "Plus Jakarta Sans",
        "body": "Inter",
        "mono": "Fira Code",
        "rationale": "Friendly geometric heading + highly legible body. The Notion/Slack vibe."
    },
    "editorial": {
        "heading": "Playfair Display",
        "body": "Source Serif 4",
        "mono": "JetBrains Mono",
        "rationale": "High-contrast serif heading + readable serif body. Magazine feel."
    },
    "technical": {
        "heading": "Space Grotesk",
        "body": "IBM Plex Sans",
        "mono": "IBM Plex Mono",
        "rationale": "Geometric precision heading + neutral body. Developer-focused."
    },
    "minimal": {
        "heading": "Inter",
        "body": "Inter",
        "mono": "Fira Code",
        "rationale": "Single-family simplicity. Clean, no-nonsense."
    },
    "expressive": {
        "heading": "Sora",
        "body": "Nunito Sans",
        "mono": "Fira Code",
        "rationale": "Soft geometric heading + rounded body. Playful yet professional."
    },
}


def _generate_type_scale(base_size: float, ratio_name: str, steps_up: int, steps_down: int) -> list:
    """Generate a modular type scale."""
    ratio = SCALE_RATIOS.get(ratio_name, 1.25)
    scale = []
    names_up = ["base", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl", "7xl", "8xl"]
    names_down = ["sm", "xs", "2xs"]

    for i in range(min(steps_down, len(names_down)), 0, -1):
        size = base_size / (ratio ** i)
        scale.append({
            "name": names_down[i - 1],
            "size_px": round(size, 1),
            "size_rem": round(size / 16, 4),
        })

    for i in range(min(steps_up + 1, len(names_up))):
        size = base_size * (ratio ** i)
        scale.append({
            "name": names_up[i],
            "size_px": round(size, 1),
            "size_rem": round(size / 16, 4),
        })

    return scale


def _calc_line_height(font_size_px: float, content_type: str = "body") -> dict:
    """Calculate optimal line-height based on font size and content type."""
    # Larger text needs tighter line-height
    if content_type == "heading":
        if font_size_px >= 48:
            lh = 1.1
        elif font_size_px >= 32:
            lh = 1.15
        elif font_size_px >= 24:
            lh = 1.2
        else:
            lh = 1.25
    elif content_type == "ui":
        lh = 1.4
    else:  # body
        if font_size_px <= 14:
            lh = 1.7
        elif font_size_px <= 16:
            lh = 1.6
        elif font_size_px <= 20:
            lh = 1.5
        else:
            lh = 1.4

    return {
        "font_size_px": font_size_px,
        "content_type": content_type,
        "line_height": lh,
        "line_height_px": round(font_size_px * lh, 1),
        "paragraph_spacing_px": round(font_size_px * lh * 0.75, 1),
    }


def _calc_tracking(font_size_px: float) -> dict:
    """Calculate letter-spacing (tracking) based on font size."""
    # Larger text → tighter tracking; smaller text → looser
    if font_size_px >= 48:
        tracking_em = -0.022
    elif font_size_px >= 32:
        tracking_em = -0.015
    elif font_size_px >= 24:
        tracking_em = -0.01
    elif font_size_px >= 16:
        tracking_em = 0.0
    elif font_size_px >= 12:
        tracking_em = 0.01
    else:
        tracking_em = 0.02

    return {
        "font_size_px": font_size_px,
        "tracking_em": tracking_em,
        "tracking_px": round(font_size_px * tracking_em, 2),
        "css_value": f"{tracking_em}em",
    }


def execute(agent: dict, args: dict) -> dict:
    action = args.get("action", "")

    if action == "type_scale":
        base = args.get("base_size", 16)
        ratio = args.get("ratio", "major-third")
        steps_up = args.get("steps_up", 6)
        steps_down = args.get("steps_down", 2)

        if ratio not in SCALE_RATIOS:
            return {"status": "error", "message": f"Unknown ratio '{ratio}'. Available: {list(SCALE_RATIOS.keys())}"}

        scale = _generate_type_scale(base, ratio, steps_up, steps_down)
        actual_ratio = SCALE_RATIOS[ratio]

        # Generate CSS custom properties
        css_vars = []
        for step in scale:
            css_vars.append(f"  --font-size-{step['name']}: {step['size_rem']}rem;")

        return {
            "status": "ok",
            "action": "type_scale",
            "config": {"base_size_px": base, "ratio_name": ratio, "ratio_value": actual_ratio},
            "scale": scale,
            "css_variables": ":root {\n" + "\n".join(css_vars) + "\n}",
        }

    elif action == "font_pairing":
        style = args.get("style", "warm-organic")
        if style not in FONT_PAIRINGS:
            return {"status": "error", "message": f"Unknown style '{style}'. Available: {list(FONT_PAIRINGS.keys())}"}

        pairing = FONT_PAIRINGS[style]
        # Generate CSS @import suggestion
        fonts = [pairing["heading"], pairing["body"]]
        if pairing["heading"] != pairing["body"]:
            families = "+".join(f.replace(" ", "+") for f in fonts) + "&display=swap"
        else:
            families = fonts[0].replace(" ", "+") + "&display=swap"

        return {
            "status": "ok",
            "action": "font_pairing",
            "style": style,
            "pairing": pairing,
            "google_fonts_url": f"https://fonts.googleapis.com/css2?family={families}",
            "css_variables": (
                f":root {{\n"
                f"  --font-heading: '{pairing['heading']}', system-ui, sans-serif;\n"
                f"  --font-body: '{pairing['body']}', system-ui, sans-serif;\n"
                f"  --font-mono: '{pairing['mono']}', ui-monospace, monospace;\n"
                f"}}"
            ),
        }

    elif action == "line_height":
        font_size = args.get("font_size", 16)
        content_type = args.get("content_type", "body")
        if content_type not in ("body", "heading", "ui"):
            return {"status": "error", "message": "content_type must be 'body', 'heading', or 'ui'."}
        return {
            "status": "ok",
            "action": "line_height",
            **_calc_line_height(font_size, content_type),
        }

    elif action == "tracking":
        font_size = args.get("font_size", 16)
        return {
            "status": "ok",
            "action": "tracking",
            **_calc_tracking(font_size),
        }

    else:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Available: type_scale, font_pairing, line_height, tracking",
        }
