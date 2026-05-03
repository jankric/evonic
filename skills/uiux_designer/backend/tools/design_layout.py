"""
design_layout — Layout and spacing system generation.

Actions: grid_system, spacing_scale, breakpoints, container
Pure logic: 4px/8px grid math.
"""

import json
import math


# Standard breakpoints (mobile-first)
DEFAULT_BREAKPOINTS = {
    "xs": {"min_width": 0, "max_width": 479, "label": "Mobile S"},
    "sm": {"min_width": 480, "max_width": 639, "label": "Mobile L"},
    "md": {"min_width": 640, "max_width": 767, "label": "Tablet"},
    "lg": {"min_width": 768, "max_width": 1023, "label": "Tablet L"},
    "xl": {"min_width": 1024, "max_width": 1279, "label": "Desktop"},
    "2xl": {"min_width": 1280, "max_width": 1535, "label": "Desktop L"},
    "3xl": {"min_width": 1536, "max_width": None, "label": "Wide"},
}


def _generate_spacing_scale(base: int, steps: int, method: str = "multiply") -> list:
    """Generate spacing scale from base unit."""
    scale = []
    names = ["0", "px", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4", "5", "6", "7", "8", "9", "10", "11", "12", "14", "16", "20", "24", "28", "32", "36", "40", "44", "48", "52", "56", "60", "64", "72", "80", "96"]

    if method == "tailwind":
        # Tailwind-style: 0, 1px, 2px, 4px, 6px, 8px, 10px, 12px, 14px, 16px, 20px, 24px...
        values = [0, 1, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 96]
        for i, val in enumerate(values[:steps]):
            scale.append({
                "token": f"space-{i}",
                "value_px": val,
                "value_rem": round(val / 16, 4) if val > 0 else 0,
            })
    elif method == "geometric":
        # Geometric progression: base * 2^n
        for i in range(steps):
            val = base * (2 ** i) if i > 0 else 0
            if i == 1:
                val = base
            scale.append({
                "token": f"space-{i}",
                "value_px": val,
                "value_rem": round(val / 16, 4) if val > 0 else 0,
            })
    else:  # linear multiply
        for i in range(steps):
            val = base * i
            scale.append({
                "token": f"space-{i}",
                "value_px": val,
                "value_rem": round(val / 16, 4) if val > 0 else 0,
            })

    return scale


def _generate_grid(columns: int, gutter: int, margin: int, max_width: int) -> dict:
    """Generate grid system specifications."""
    content_width = max_width - (margin * 2)
    total_gutters = columns - 1
    total_gutter_width = gutter * total_gutters
    column_width = (content_width - total_gutter_width) / columns

    return {
        "columns": columns,
        "gutter_px": gutter,
        "margin_px": margin,
        "max_width_px": max_width,
        "content_width_px": round(content_width, 1),
        "column_width_px": round(column_width, 1),
        "css_grid": (
            f".grid {{\n"
            f"  display: grid;\n"
            f"  grid-template-columns: repeat({columns}, 1fr);\n"
            f"  gap: {gutter}px;\n"
            f"  max-width: {max_width}px;\n"
            f"  margin-inline: auto;\n"
            f"  padding-inline: {margin}px;\n"
            f"}}"
        ),
        "responsive_overrides": {
            "mobile": {"columns": min(4, columns), "gutter": max(12, gutter - 8), "margin": 16},
            "tablet": {"columns": min(8, columns), "gutter": gutter, "margin": max(24, margin - 8)},
            "desktop": {"columns": columns, "gutter": gutter, "margin": margin},
        },
    }


def _generate_container(max_width: int, padding: int) -> dict:
    """Generate container specifications for each breakpoint."""
    containers = {}
    for bp_name, bp in DEFAULT_BREAKPOINTS.items():
        if bp["min_width"] == 0:
            containers[bp_name] = {"width": "100%", "padding_px": 16}
        elif bp["min_width"] < 768:
            containers[bp_name] = {"width": "100%", "padding_px": padding}
        elif bp["min_width"] < 1024:
            containers[bp_name] = {"width": f"{min(bp['min_width'] - 48, max_width)}px", "padding_px": padding}
        else:
            containers[bp_name] = {"width": f"{min(bp['min_width'] - 64, max_width)}px", "padding_px": padding}

    css = ".container {\n  width: 100%;\n  margin-inline: auto;\n"
    css += f"  padding-inline: {padding}px;\n"
    css += f"  max-width: {max_width}px;\n}}"

    return {
        "max_width_px": max_width,
        "padding_px": padding,
        "breakpoint_widths": containers,
        "css": css,
    }


def execute(agent: dict, args: dict) -> dict:
    action = args.get("action", "")

    if action == "grid_system":
        columns = args.get("columns", 12)
        gutter = args.get("gutter", 24)
        margin = args.get("margin", 32)
        max_width = args.get("max_width", 1280)

        # Snap to 4px grid
        gutter = round(gutter / 4) * 4
        margin = round(margin / 4) * 4

        grid = _generate_grid(columns, gutter, margin, max_width)
        return {"status": "ok", "action": "grid_system", **grid}

    elif action == "spacing_scale":
        base = args.get("base", 4)
        steps = args.get("steps", 16)
        method = args.get("method", "tailwind")

        if method not in ("tailwind", "geometric", "multiply"):
            return {"status": "error", "message": "method must be 'tailwind', 'geometric', or 'multiply'."}

        # Snap base to 4px grid
        base = max(4, round(base / 4) * 4)
        scale = _generate_spacing_scale(base, min(steps, 25), method)

        css_vars = [f"  --space-{s['token'].split('-')[1]}: {s['value_rem']}rem;" for s in scale if s['value_px'] > 0]

        return {
            "status": "ok",
            "action": "spacing_scale",
            "config": {"base_px": base, "method": method, "steps": len(scale)},
            "scale": scale,
            "css_variables": ":root {\n" + "\n".join(css_vars) + "\n}",
        }

    elif action == "breakpoints":
        custom = args.get("custom", None)
        breakpoints = custom if custom else DEFAULT_BREAKPOINTS

        # Generate CSS media queries
        media_queries = []
        for name, bp in breakpoints.items():
            if bp["min_width"] > 0:
                media_queries.append(f"/* {bp.get('label', name)} */\n@media (min-width: {bp['min_width']}px) {{ }}")

        # Tailwind config
        tw_screens = {}
        for name, bp in breakpoints.items():
            if bp["min_width"] > 0:
                tw_screens[name] = f"{bp['min_width']}px"

        return {
            "status": "ok",
            "action": "breakpoints",
            "breakpoints": breakpoints,
            "media_queries": "\n\n".join(media_queries),
            "tailwind_screens": tw_screens,
        }

    elif action == "container":
        max_width = args.get("max_width", 1280)
        padding = args.get("padding", 32)

        # Snap to 4px grid
        padding = round(padding / 4) * 4

        container = _generate_container(max_width, padding)
        return {"status": "ok", "action": "container", **container}

    else:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Available: grid_system, spacing_scale, breakpoints, container",
        }
