"""
design_audit — Accessibility auditing and design token generation.

Actions: wcag_check, contrast_audit, aria_guidance, generate_tokens
WCAG 2.2 rules, token format conversion.
"""

import json
import math
import re


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.2."""
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    r1, g1, b1 = _hex_to_rgb(color1)
    r2, g2, b2 = _hex_to_rgb(color2)
    l1 = _relative_luminance(r1, g1, b1)
    l2 = _relative_luminance(r2, g2, b2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# WCAG 2.2 Success Criteria (key ones for UI)
WCAG_CRITERIA = {
    "1.4.3": {"level": "AA", "title": "Contrast (Minimum)", "requirement": "Text: 4.5:1, Large text: 3:1"},
    "1.4.6": {"level": "AAA", "title": "Contrast (Enhanced)", "requirement": "Text: 7:1, Large text: 4.5:1"},
    "1.4.11": {"level": "AA", "title": "Non-text Contrast", "requirement": "UI components and graphics: 3:1"},
    "1.4.12": {"level": "AA", "title": "Text Spacing", "requirement": "Line height ≥1.5x, paragraph spacing ≥2x, letter spacing ≥0.12em, word spacing ≥0.16em"},
    "1.4.13": {"level": "AA", "title": "Content on Hover/Focus", "requirement": "Dismissible, hoverable, persistent"},
    "2.4.7": {"level": "AA", "title": "Focus Visible", "requirement": "Focus indicator visible on all interactive elements"},
    "2.4.11": {"level": "AA", "title": "Focus Not Obscured (Minimum)", "requirement": "Focused element not entirely hidden"},
    "2.5.5": {"level": "AAA", "title": "Target Size (Enhanced)", "requirement": "Target size ≥44x44 CSS pixels"},
    "2.5.8": {"level": "AA", "title": "Target Size (Minimum)", "requirement": "Target size ≥24x24 CSS pixels"},
    "3.2.6": {"level": "A", "title": "Consistent Help", "requirement": "Help mechanisms in consistent location"},
    "3.3.7": {"level": "A", "title": "Redundant Entry", "requirement": "Don't ask for same info twice"},
}

# ARIA role guidance
ARIA_GUIDANCE = {
    "button": {
        "role": "button",
        "required_attrs": [],
        "recommended_attrs": ["aria-label (if no visible text)", "aria-pressed (toggle)", "aria-expanded (disclosure)"],
        "keyboard": "Enter/Space to activate",
        "notes": "Use native <button> when possible. Only use role='button' on non-button elements.",
    },
    "dialog": {
        "role": "dialog",
        "required_attrs": ["aria-labelledby OR aria-label"],
        "recommended_attrs": ["aria-describedby", "aria-modal"],
        "keyboard": "Escape to close, Tab trapped within",
        "notes": "Focus first focusable element on open. Return focus to trigger on close.",
    },
    "navigation": {
        "role": "navigation",
        "required_attrs": ["aria-label (if multiple navs)"],
        "recommended_attrs": ["aria-current='page'"],
        "keyboard": "Tab through links",
        "notes": "Use <nav> element. Label with aria-label if page has multiple nav landmarks.",
    },
    "tab": {
        "role": "tablist > tab + tabpanel",
        "required_attrs": ["aria-selected", "aria-controls", "aria-labelledby"],
        "recommended_attrs": ["aria-orientation"],
        "keyboard": "Arrow keys between tabs, Tab into panel",
        "notes": "Only selected tab in tab order. Panels associated via aria-labelledby.",
    },
    "alert": {
        "role": "alert",
        "required_attrs": [],
        "recommended_attrs": ["aria-live='assertive'", "aria-atomic='true'"],
        "keyboard": "N/A (announced automatically)",
        "notes": "Use sparingly. For non-urgent messages use role='status' with aria-live='polite'.",
    },
    "form": {
        "role": "form",
        "required_attrs": ["aria-label OR aria-labelledby"],
        "recommended_attrs": ["aria-describedby (for instructions)"],
        "keyboard": "Tab through fields, Enter to submit",
        "notes": "Every input needs a label. Use aria-invalid and aria-errormessage for validation.",
    },
    "menu": {
        "role": "menu > menuitem",
        "required_attrs": ["aria-label (on menu)"],
        "recommended_attrs": ["aria-haspopup (on trigger)", "aria-expanded"],
        "keyboard": "Arrow keys to navigate, Enter to select, Escape to close",
        "notes": "For action menus, not navigation. Use menuitemcheckbox/menuitemradio for toggles.",
    },
}


def _wcag_check(component_type: str, properties: dict) -> dict:
    """Check a component against relevant WCAG criteria."""
    issues = []
    passes = []

    # Check contrast if colors provided
    fg = properties.get("foreground_color")
    bg = properties.get("background_color")
    if fg and bg:
        ratio = _contrast_ratio(fg, bg)
        font_size = properties.get("font_size_px", 16)
        is_large = font_size >= 24 or (font_size >= 18.66 and properties.get("font_weight", 400) >= 700)
        required = 3.0 if is_large else 4.5

        if ratio >= required:
            passes.append({"criterion": "1.4.3", "detail": f"Contrast {ratio:.2f}:1 ≥ {required}:1"})
        else:
            issues.append({"criterion": "1.4.3", "severity": "error", "detail": f"Contrast {ratio:.2f}:1 < {required}:1 required"})

    # Check target size
    width = properties.get("width_px")
    height = properties.get("height_px")
    if width and height:
        if width >= 44 and height >= 44:
            passes.append({"criterion": "2.5.5", "detail": f"Target {width}x{height}px ≥ 44x44px (AAA)"})
        elif width >= 24 and height >= 24:
            passes.append({"criterion": "2.5.8", "detail": f"Target {width}x{height}px ≥ 24x24px (AA)"})
        else:
            issues.append({"criterion": "2.5.8", "severity": "error", "detail": f"Target {width}x{height}px < 24x24px minimum"})

    # Check text spacing
    line_height = properties.get("line_height")
    if line_height and line_height < 1.5 and component_type not in ("heading", "button"):
        issues.append({"criterion": "1.4.12", "severity": "warning", "detail": f"Line height {line_height} < 1.5x recommended"})

    # Check focus indicator
    has_focus = properties.get("has_focus_indicator", None)
    if has_focus is False:
        issues.append({"criterion": "2.4.7", "severity": "error", "detail": "No visible focus indicator"})
    elif has_focus is True:
        passes.append({"criterion": "2.4.7", "detail": "Focus indicator present"})

    return {
        "component_type": component_type,
        "issues": issues,
        "passes": passes,
        "score": f"{len(passes)}/{len(passes) + len(issues)} checks passed",
        "wcag_level": "Fail" if any(i["severity"] == "error" for i in issues) else "AA",
    }


def _generate_tokens(tokens: dict, formats: list) -> dict:
    """Convert W3C DTCG tokens to multiple output formats."""
    outputs = {}

    # W3C DTCG JSON (source of truth)
    if "dtcg" in formats or "json" in formats:
        outputs["dtcg_json"] = json.dumps(tokens, indent=2)

    # CSS Custom Properties
    if "css" in formats:
        css_lines = [":root {"]
        for group_name, group in tokens.items():
            if isinstance(group, dict):
                for token_name, token_val in group.items():
                    if isinstance(token_val, dict) and "$value" in token_val:
                        css_name = f"--{group_name}-{token_name}".replace("_", "-")
                        css_lines.append(f"  {css_name}: {token_val['$value']};")
        css_lines.append("}")
        outputs["css"] = "\n".join(css_lines)

    # SCSS Variables
    if "scss" in formats:
        scss_lines = []
        for group_name, group in tokens.items():
            if isinstance(group, dict):
                for token_name, token_val in group.items():
                    if isinstance(token_val, dict) and "$value" in token_val:
                        scss_name = f"${group_name}-{token_name}".replace("_", "-")
                        scss_lines.append(f"{scss_name}: {token_val['$value']};")
        outputs["scss"] = "\n".join(scss_lines)

    # Tailwind Config
    if "tailwind" in formats:
        tw = {}
        for group_name, group in tokens.items():
            if isinstance(group, dict):
                tw[group_name] = {}
                for token_name, token_val in group.items():
                    if isinstance(token_val, dict) and "$value" in token_val:
                        # camelCase for JS
                        parts = token_name.split("-")
                        camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
                        tw[group_name][camel] = token_val["$value"]
        outputs["tailwind_config"] = f"// tailwind.config.ts\nexport default {{\n  theme: {{\n    extend: {json.dumps(tw, indent=6)}\n  }}\n}}"

    # JS/TS Export
    if "js" in formats or "ts" in formats:
        js_tokens = {}
        for group_name, group in tokens.items():
            if isinstance(group, dict):
                js_tokens[group_name] = {}
                for token_name, token_val in group.items():
                    if isinstance(token_val, dict) and "$value" in token_val:
                        parts = token_name.split("-")
                        camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
                        js_tokens[group_name][camel] = token_val["$value"]
        outputs["typescript"] = f"export const tokens = {json.dumps(js_tokens, indent=2)} as const;"

    return outputs


def execute(agent: dict, args: dict) -> dict:
    action = args.get("action", "")

    if action == "wcag_check":
        component_type = args.get("component_type", "generic")
        properties = args.get("properties", {})
        result = _wcag_check(component_type, properties)
        return {"status": "ok", "action": "wcag_check", **result}

    elif action == "contrast_audit":
        pairs = args.get("color_pairs", [])
        if not pairs:
            return {"status": "error", "message": "Provide 'color_pairs' array of {foreground, background, context} objects."}

        results = []
        for pair in pairs[:20]:  # Max 20 pairs
            fg = pair.get("foreground", "#000000")
            bg = pair.get("background", "#ffffff")
            ratio = _contrast_ratio(fg, bg)
            results.append({
                "foreground": fg,
                "background": bg,
                "context": pair.get("context", ""),
                "ratio": round(ratio, 2),
                "wcag_aa_normal": ratio >= 4.5,
                "wcag_aa_large": ratio >= 3.0,
                "wcag_aaa_normal": ratio >= 7.0,
                "wcag_aaa_large": ratio >= 4.5,
            })

        failing = [r for r in results if not r["wcag_aa_normal"]]
        return {
            "status": "ok",
            "action": "contrast_audit",
            "results": results,
            "summary": {
                "total_pairs": len(results),
                "passing_aa": len(results) - len(failing),
                "failing_aa": len(failing),
            },
        }

    elif action == "aria_guidance":
        component = args.get("component", "")
        if component not in ARIA_GUIDANCE:
            return {
                "status": "error",
                "message": f"Unknown component '{component}'. Available: {list(ARIA_GUIDANCE.keys())}",
            }
        return {"status": "ok", "action": "aria_guidance", "component": component, **ARIA_GUIDANCE[component]}

    elif action == "generate_tokens":
        tokens = args.get("tokens", {})
        formats = args.get("formats", ["dtcg", "css", "tailwind", "ts"])

        if not tokens:
            return {"status": "error", "message": "Provide 'tokens' object in W3C DTCG format."}

        valid_formats = {"dtcg", "json", "css", "scss", "tailwind", "js", "ts"}
        invalid = set(formats) - valid_formats
        if invalid:
            return {"status": "error", "message": f"Invalid formats: {invalid}. Available: {valid_formats}"}

        outputs = _generate_tokens(tokens, formats)
        return {
            "status": "ok",
            "action": "generate_tokens",
            "formats_generated": list(outputs.keys()),
            "outputs": outputs,
        }

    else:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Available: wcag_check, contrast_audit, aria_guidance, generate_tokens",
        }
