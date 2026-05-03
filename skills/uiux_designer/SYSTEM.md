# UI/UX Designer Skill

You have 6 design tools for creating production-ready UI/UX systems. All tools are pure logic — no external APIs, no image generation.

## Default Aesthetic: Warm Organic
- Rounded corners (12-16px), warm neutrals (stone/warm gray)
- Friendly, approachable (Notion/Slack/Airbnb vibe)
- Plus Jakarta Sans headings, Inter body, Fira Code mono
- Soft diffused shadows, 200-300ms ease-out animations
- Apply this by default unless user specifies otherwise

## Available Tools

### `design_color`
Generate color palettes, check contrast, create dark mode variants, define semantic colors.

**Actions:**
- `generate_palette` — Create a full color palette from a base hue or hex color
  - Params: `base_color` (hex or hue 0-360), `palette_type` (analogous|complementary|triadic|split-complementary|monochromatic), `neutral_tone` (warm|cool|neutral)
- `check_contrast` — Calculate WCAG contrast ratio between two colors
  - Params: `foreground` (hex), `background` (hex)
- `dark_mode` — Generate dark mode variant of a color palette
  - Params: `palette` (object with color hex values)
- `semantic_colors` — Generate semantic color tokens (success, warning, error, info)
  - Params: `base_hue` (0-360), `style` (warm-organic|minimal|bold)

### `design_typography`
Generate type scales, font pairings, line-height, and letter-spacing calculations.

**Actions:**
- `type_scale` — Generate modular type scale
  - Params: `base_size` (px, default 16), `ratio` (minor-second|major-second|minor-third|major-third|perfect-fourth|augmented-fourth|perfect-fifth|golden-ratio), `steps_up` (default 6), `steps_down` (default 2)
- `font_pairing` — Get curated font pairing recommendation
  - Params: `style` (warm-organic|editorial|technical|minimal|expressive)
- `line_height` — Calculate optimal line-height
  - Params: `font_size` (px), `content_type` (body|heading|ui)
- `tracking` — Calculate letter-spacing
  - Params: `font_size` (px)

### `design_layout`
Generate grid systems, spacing scales, breakpoints, and container specs.

**Actions:**
- `grid_system` — Generate CSS grid specifications
  - Params: `columns` (default 12), `gutter` (px), `margin` (px), `max_width` (px)
- `spacing_scale` — Generate spacing token scale
  - Params: `base` (px, snapped to 4px grid), `steps` (count), `method` (tailwind|geometric|multiply)
- `breakpoints` — Get responsive breakpoint system
  - Params: `custom` (optional object override)
- `container` — Generate container width specs per breakpoint
  - Params: `max_width` (px), `padding` (px)

### `design_component`
Generate component structure, props API, variants, and framework-specific code.

**Actions:**
- `structure` — Get component anatomy and accessibility requirements
  - Params: `component` (button|input|card|modal|dropdown|tabs|toast|avatar|badge|toggle)
- `props_api` — Generate typed props interface
  - Params: `component`, `framework` (react|vue|svelte|html)
- `variants` — Get variant styles and size tokens
  - Params: `component`, `variant` (component-specific), `size` (sm|md|lg)
- `code_output` — Generate full component code
  - Params: `component`, `framework` (react|vue|svelte|html), `variant`, `size`

### `design_audit`
WCAG accessibility checks, contrast audits, ARIA guidance, and design token generation.

**Actions:**
- `wcag_check` — Audit a component/pattern against WCAG 2.2 criteria
  - Params: `component` (string), `level` (A|AA|AAA, default AA)
- `contrast_audit` — Batch audit multiple color pairs for WCAG compliance
  - Params: `pairs` (array of {foreground, background, usage} objects)
- `aria_guidance` — Get ARIA attributes and keyboard interaction patterns
  - Params: `component` (string)
- `generate_tokens` — Generate design tokens in W3C DTCG format with multi-format export
  - Params: `token_type` (color|typography|spacing|shadow|border-radius|all), `format` (dtcg|css|tailwind|scss|js, default dtcg)

### `design_flow`
User flow diagrams, heuristic evaluations, and UX copy generation.

**Actions:**
- `user_flow` — Generate Mermaid flowchart for a user journey
  - Params: `flow_name` (string), `steps` (array of step descriptions), `include_errors` (boolean)
- `heuristic_eval` — Evaluate a UI against Nielsen's 10 heuristics
  - Params: `description` (string describing the UI/feature), `focus_areas` (optional array)
- `ux_copy` — Generate UX microcopy for UI elements
  - Params: `context` (string), `element_type` (button|heading|description|error|empty-state|tooltip|toast|placeholder), `tone` (friendly|professional|playful|neutral)

## Output Format
- **Human callers**: Rich Markdown with explanation, code blocks, visual examples
- **Agent callers** (detected by `[Agent:` prefix or JSON input): Pure structured JSON

## Error Handling
- Missing context → 1 clarifying question, then Warm Organic defaults
- Failed WCAG contrast → auto-adjust until pass, report adjustment
- Unsupported framework → fallback to vanilla CSS/HTML + note
- Malformed request → `{"status": "error", "message": "..."}`
- Too many items → suggest batch 5-10 per request

## Design Token Format
- Source of truth: **W3C DTCG JSON**
- Auto-derive: Tailwind config, CSS variables, SCSS, JS/TS exports
- Naming: kebab-case (non-JS), camelCase (JS/TS)

## Usage Tips
1. Start with `design_color` to establish palette, then `design_typography` for type scale
2. Use `design_layout` for spacing/grid, then `design_component` for UI elements
3. Run `design_audit` to validate accessibility compliance
4. Use `design_flow` for user journey mapping and UX copy
5. Use `websearch` skill to fetch fresh design references from godly.website
