"""
design_component — Component design and code generation.

Actions: structure, props_api, variants, code_output
Framework-aware: React, Vue, Svelte, HTML output.
"""

import json

# Warm Organic default styles
WARM_ORGANIC_TOKENS = {
    "border-radius": "12px",
    "border-radius-sm": "8px",
    "border-radius-lg": "16px",
    "border-radius-full": "9999px",
    "shadow-sm": "0 1px 3px rgba(120, 100, 80, 0.06)",
    "shadow-md": "0 4px 12px rgba(120, 100, 80, 0.08)",
    "shadow-lg": "0 8px 24px rgba(120, 100, 80, 0.1)",
    "transition": "all 200ms ease-out",
    "font-family": "'Plus Jakarta Sans', system-ui, sans-serif",
}

# Common component patterns
COMPONENT_PATTERNS = {
    "button": {
        "description": "Interactive button with multiple variants",
        "anatomy": ["container", "label", "icon-start?", "icon-end?", "loading-spinner?"],
        "states": ["default", "hover", "active", "focus", "disabled", "loading"],
        "sizes": ["sm", "md", "lg"],
        "variants": ["primary", "secondary", "ghost", "destructive", "outline"],
    },
    "input": {
        "description": "Text input field with label and validation",
        "anatomy": ["wrapper", "label", "input-container", "input", "prefix?", "suffix?", "helper-text?", "error-text?"],
        "states": ["default", "focus", "filled", "error", "disabled", "readonly"],
        "sizes": ["sm", "md", "lg"],
        "variants": ["outlined", "filled", "underlined"],
    },
    "card": {
        "description": "Content container with optional header/footer",
        "anatomy": ["container", "header?", "media?", "body", "footer?"],
        "states": ["default", "hover", "active", "selected"],
        "sizes": ["sm", "md", "lg"],
        "variants": ["elevated", "outlined", "filled"],
    },
    "modal": {
        "description": "Dialog overlay for focused interactions",
        "anatomy": ["backdrop", "container", "header", "body", "footer", "close-button"],
        "states": ["open", "closing", "closed"],
        "sizes": ["sm", "md", "lg", "full"],
        "variants": ["default", "drawer", "bottom-sheet"],
    },
    "avatar": {
        "description": "User representation with image or initials",
        "anatomy": ["container", "image?", "initials?", "status-badge?"],
        "states": ["default", "loading"],
        "sizes": ["xs", "sm", "md", "lg", "xl"],
        "variants": ["circle", "rounded", "square"],
    },
    "badge": {
        "description": "Small status indicator or label",
        "anatomy": ["container", "dot?", "label", "icon?"],
        "states": ["default"],
        "sizes": ["sm", "md"],
        "variants": ["solid", "soft", "outline", "dot"],
    },
    "toast": {
        "description": "Temporary notification message",
        "anatomy": ["container", "icon?", "content", "title?", "description", "action?", "close?"],
        "states": ["entering", "visible", "exiting"],
        "sizes": ["sm", "md"],
        "variants": ["info", "success", "warning", "error"],
    },
    "tabs": {
        "description": "Tabbed navigation for content sections",
        "anatomy": ["container", "tab-list", "tab-item", "tab-indicator", "tab-panel"],
        "states": ["default", "active", "disabled"],
        "sizes": ["sm", "md", "lg"],
        "variants": ["underline", "pills", "enclosed"],
    },
}


def _generate_structure(component: str) -> dict:
    """Generate component structure/anatomy."""
    pattern = COMPONENT_PATTERNS.get(component)
    if not pattern:
        return {"status": "error", "message": f"Unknown component '{component}'. Available: {list(COMPONENT_PATTERNS.keys())}"}

    return {
        "status": "ok",
        "action": "structure",
        "component": component,
        **pattern,
        "accessibility": {
            "role": _get_aria_role(component),
            "required_attrs": _get_required_aria(component),
            "keyboard": _get_keyboard_interactions(component),
        },
    }


def _generate_props_api(component: str, framework: str) -> dict:
    """Generate props/API definition for a component."""
    pattern = COMPONENT_PATTERNS.get(component)
    if not pattern:
        return {"status": "error", "message": f"Unknown component '{component}'. Available: {list(COMPONENT_PATTERNS.keys())}"}

    props = _build_props(component, pattern)

    if framework == "react":
        code = _props_to_typescript(component, props)
    elif framework == "vue":
        code = _props_to_vue_defineprops(component, props)
    elif framework == "svelte":
        code = _props_to_svelte(component, props)
    else:
        code = _props_to_jsdoc(component, props)

    return {
        "status": "ok",
        "action": "props_api",
        "component": component,
        "framework": framework,
        "props": props,
        "code": code,
    }


def _generate_variants(component: str) -> dict:
    """Generate variant specifications with styles."""
    pattern = COMPONENT_PATTERNS.get(component)
    if not pattern:
        return {"status": "error", "message": f"Unknown component '{component}'. Available: {list(COMPONENT_PATTERNS.keys())}"}

    variants_detail = {}
    for variant in pattern["variants"]:
        variants_detail[variant] = _get_variant_styles(component, variant)

    return {
        "status": "ok",
        "action": "variants",
        "component": component,
        "variants": variants_detail,
        "sizes": {size: _get_size_styles(component, size) for size in pattern["sizes"]},
    }


def _generate_code(component: str, framework: str, variant: str = "primary", size: str = "md") -> dict:
    """Generate component code output."""
    pattern = COMPONENT_PATTERNS.get(component)
    if not pattern:
        return {"status": "error", "message": f"Unknown component '{component}'. Available: {list(COMPONENT_PATTERNS.keys())}"}

    if framework == "react":
        code = _code_react(component, variant, size)
    elif framework == "vue":
        code = _code_vue(component, variant, size)
    elif framework == "svelte":
        code = _code_svelte(component, variant, size)
    else:
        code = _code_html(component, variant, size)

    return {
        "status": "ok",
        "action": "code_output",
        "component": component,
        "framework": framework,
        "variant": variant,
        "size": size,
        "code": code,
        "styles": _get_component_css(component, variant, size),
    }


# --- Helper functions ---

def _get_aria_role(component: str) -> str:
    roles = {"button": "button", "input": "textbox", "card": "article", "modal": "dialog",
             "avatar": "img", "badge": "status", "toast": "alert", "tabs": "tablist"}
    return roles.get(component, "generic")


def _get_required_aria(component: str) -> list:
    attrs = {
        "button": ["aria-label (if icon-only)"],
        "input": ["aria-label or aria-labelledby", "aria-describedby (if helper text)", "aria-invalid (if error)"],
        "modal": ["aria-labelledby", "aria-describedby", "aria-modal=true"],
        "tabs": ["aria-selected", "aria-controls", "role=tab on items", "role=tabpanel on panels"],
        "toast": ["aria-live=polite", "role=status"],
    }
    return attrs.get(component, [])


def _get_keyboard_interactions(component: str) -> list:
    kb = {
        "button": ["Enter/Space: activate", "Tab: focus next"],
        "input": ["Tab: focus", "Escape: clear/close dropdown"],
        "modal": ["Escape: close", "Tab: trap focus within", "Shift+Tab: reverse trap"],
        "tabs": ["Arrow Left/Right: switch tabs", "Home: first tab", "End: last tab"],
    }
    return kb.get(component, ["Tab: focus"])


def _build_props(component: str, pattern: dict) -> list:
    """Build props list for a component."""
    base_props = [
        {"name": "variant", "type": "\x27" + "\x27 | \x27".join(pattern["variants"]) + "\x27", "default": pattern["variants"][0], "required": False},
        {"name": "size", "type": "\x27" + "\x27 | \x27".join(pattern["sizes"]) + "\x27", "default": "md", "required": False},
        {"name": "className", "type": "string", "default": "''", "required": False},
    ]

    component_props = {
        "button": [
            {"name": "children", "type": "ReactNode", "default": None, "required": True},
            {"name": "disabled", "type": "boolean", "default": "false", "required": False},
            {"name": "loading", "type": "boolean", "default": "false", "required": False},
            {"name": "iconStart", "type": "ReactNode", "default": None, "required": False},
            {"name": "iconEnd", "type": "ReactNode", "default": None, "required": False},
            {"name": "onClick", "type": "() => void", "default": None, "required": False},
        ],
        "input": [
            {"name": "label", "type": "string", "default": None, "required": True},
            {"name": "value", "type": "string", "default": "''", "required": False},
            {"name": "placeholder", "type": "string", "default": "''", "required": False},
            {"name": "error", "type": "string", "default": None, "required": False},
            {"name": "helperText", "type": "string", "default": None, "required": False},
            {"name": "disabled", "type": "boolean", "default": "false", "required": False},
            {"name": "onChange", "type": "(value: string) => void", "default": None, "required": False},
        ],
        "card": [
            {"name": "children", "type": "ReactNode", "default": None, "required": True},
            {"name": "title", "type": "string", "default": None, "required": False},
            {"name": "subtitle", "type": "string", "default": None, "required": False},
            {"name": "hoverable", "type": "boolean", "default": "false", "required": False},
            {"name": "onClick", "type": "() => void", "default": None, "required": False},
        ],
    }

    return base_props + component_props.get(component, [])


def _props_to_typescript(component: str, props: list) -> str:
    name = component.capitalize()
    lines = [f"interface {name}Props {{"]
    for p in props:
        req = "" if p["required"] else "?"
        lines.append(f"  {p['name']}{req}: {p['type']};")
    lines.append("}")
    return "\n".join(lines)


def _props_to_vue_defineprops(component: str, props: list) -> str:
    lines = ["defineProps<{"]
    for p in props:
        req = "" if p["required"] else "?"
        lines.append(f"  {p['name']}{req}: {p['type']};")
    lines.append("}>()")
    return "\n".join(lines)


def _props_to_svelte(component: str, props: list) -> str:
    lines = []
    for p in props:
        default = f" = {p['default']}" if p.get("default") and p["default"] != "None" else ""
        lines.append(f"  export let {p['name']}: {p['type']}{default};")
    return "<script lang=\"ts\">\n" + "\n".join(lines) + "\n</script>"


def _props_to_jsdoc(component: str, props: list) -> str:
    lines = ["/**"]
    for p in props:
        req = "(required)" if p["required"] else "(optional)"
        lines.append(f" * @param {{{p['type']}}} {p['name']} - {req}")
    lines.append(" */")
    return "\n".join(lines)


def _get_variant_styles(component: str, variant: str) -> dict:
    """Get CSS styles for a variant."""
    base = {"border-radius": WARM_ORGANIC_TOKENS["border-radius"], "transition": WARM_ORGANIC_TOKENS["transition"]}

    if component == "button":
        styles = {
            "primary": {**base, "background": "var(--color-primary)", "color": "white", "border": "none", "box-shadow": WARM_ORGANIC_TOKENS["shadow-sm"]},
            "secondary": {**base, "background": "var(--color-secondary)", "color": "var(--color-text)", "border": "none"},
            "ghost": {**base, "background": "transparent", "color": "var(--color-text)", "border": "none"},
            "destructive": {**base, "background": "var(--color-error)", "color": "white", "border": "none"},
            "outline": {**base, "background": "transparent", "color": "var(--color-primary)", "border": "1.5px solid var(--color-primary)"},
        }
    elif component == "card":
        styles = {
            "elevated": {**base, "background": "var(--color-surface)", "box-shadow": WARM_ORGANIC_TOKENS["shadow-md"], "border": "none"},
            "outlined": {**base, "background": "var(--color-surface)", "box-shadow": "none", "border": "1px solid var(--color-border)"},
            "filled": {**base, "background": "var(--color-surface-variant)", "box-shadow": "none", "border": "none"},
        }
    else:
        styles = {v: base for v in COMPONENT_PATTERNS.get(component, {}).get("variants", [])}

    return styles.get(variant, base)


def _get_size_styles(component: str, size: str) -> dict:
    """Get size-specific styles."""
    sizes = {
        "button": {
            "sm": {"padding": "6px 12px", "font-size": "13px", "height": "32px"},
            "md": {"padding": "8px 16px", "font-size": "14px", "height": "40px"},
            "lg": {"padding": "12px 24px", "font-size": "16px", "height": "48px"},
        },
        "input": {
            "sm": {"padding": "6px 10px", "font-size": "13px", "height": "32px"},
            "md": {"padding": "8px 12px", "font-size": "14px", "height": "40px"},
            "lg": {"padding": "12px 16px", "font-size": "16px", "height": "48px"},
        },
    }
    return sizes.get(component, {}).get(size, {"padding": "8px 16px", "font-size": "14px"})


def _get_component_css(component: str, variant: str, size: str) -> str:
    """Generate CSS for a component."""
    vs = _get_variant_styles(component, variant)
    ss = _get_size_styles(component, size)
    all_styles = {**vs, **ss}

    lines = [f".{component} {{"]
    for prop, val in all_styles.items():
        lines.append(f"  {prop}: {val};")
    lines.append("}")
    return "\n".join(lines)


def _code_react(component: str, variant: str, size: str) -> str:
    name = component.capitalize()
    return (
        f"import {{ cn }} from '@/lib/utils';\n\n"
        f"export function {name}({{ variant = '{variant}', size = '{size}', className, children, ...props }}) {{\n"
        f"  return (\n"
        f"    <{_get_html_tag(component)}\n"
        f"      className={{cn('{component}', `{component}--${{variant}}`, `{component}--${{size}}`, className)}}\n"
        f"      {{...props}}\n"
        f"    >\n"
        f"      {{children}}\n"
        f"    </{_get_html_tag(component)}>\n"
        f"  );\n"
        f"}}"
    )


def _code_vue(component: str, variant: str, size: str) -> str:
    name = component.capitalize()
    tag = _get_html_tag(component)
    return (
        f"<template>\n"
        f"  <{tag} :class=\"['{component}', `{component}--${{variant}}`, `{component}--${{size}}`]\">\n"
        f"    <slot />\n"
        f"  </{tag}>\n"
        f"</template>\n\n"
        f"<script setup lang=\"ts\">\n"
        f"withDefaults(defineProps<{{\n"
        f"  variant?: string;\n"
        f"  size?: string;\n"
        f"}}>(), {{\n"
        f"  variant: '{variant}',\n"
        f"  size: '{size}',\n"
        f"}});\n"
        f"</script>"
    )


def _code_svelte(component: str, variant: str, size: str) -> str:
    tag = _get_html_tag(component)
    return (
        f"<script lang=\"ts\">\n"
        f"  export let variant = '{variant}';\n"
        f"  export let size = '{size}';\n"
        f"</script>\n\n"
        f"<{tag} class=\"{component} {component}--{{variant}} {component}--{{size}}\">\n"
        f"  <slot />\n"
        f"</{tag}>"
    )


def _code_html(component: str, variant: str, size: str) -> str:
    tag = _get_html_tag(component)
    return f'<{tag} class="{component} {component}--{variant} {component}--{size}">\n  <!-- content -->\n</{tag}>'


def _get_html_tag(component: str) -> str:
    tags = {"button": "button", "input": "input", "card": "div", "modal": "dialog",
            "avatar": "div", "badge": "span", "toast": "div", "tabs": "div"}
    return tags.get(component, "div")


def execute(agent: dict, args: dict) -> dict:
    action = args.get("action", "")

    if action == "structure":
        component = args.get("component", "button")
        return _generate_structure(component)

    elif action == "props_api":
        component = args.get("component", "button")
        framework = args.get("framework", "react")
        if framework not in ("react", "vue", "svelte", "html"):
            return {"status": "error", "message": "framework must be 'react', 'vue', 'svelte', or 'html'."}
        return _generate_props_api(component, framework)

    elif action == "variants":
        component = args.get("component", "button")
        return _generate_variants(component)

    elif action == "code_output":
        component = args.get("component", "button")
        framework = args.get("framework", "html")
        variant = args.get("variant", "primary")
        size = args.get("size", "md")
        if framework not in ("react", "vue", "svelte", "html"):
            return {"status": "error", "message": "Unsupported framework. Available: react, vue, svelte, html. Falling back to html."}
        return _generate_code(component, framework, variant, size)

    else:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Available: structure, props_api, variants, code_output",
        }
