"""
design_flow — User flow and UX analysis tools.

Actions: user_flow, heuristic_eval, ux_copy
Mermaid diagram generation, Nielsen heuristics evaluation.
"""

import json

# Nielsen's 10 Usability Heuristics
NIELSEN_HEURISTICS = [
    {
        "id": 1,
        "name": "Visibility of System Status",
        "description": "The design should always keep users informed about what is going on, through appropriate feedback within a reasonable amount of time.",
        "examples": ["Loading indicators", "Progress bars", "Success/error toasts", "Breadcrumbs", "Active states"],
    },
    {
        "id": 2,
        "name": "Match Between System and Real World",
        "description": "The design should speak the users' language. Use words, phrases, and concepts familiar to the user, rather than internal jargon.",
        "examples": ["Shopping cart icon", "Trash can for delete", "Natural language labels", "Familiar icons"],
    },
    {
        "id": 3,
        "name": "User Control and Freedom",
        "description": "Users often perform actions by mistake. They need a clearly marked 'emergency exit' to leave the unwanted action without having to go through an extended process.",
        "examples": ["Undo/redo", "Cancel buttons", "Back navigation", "Close modals with Escape", "Draft auto-save"],
    },
    {
        "id": 4,
        "name": "Consistency and Standards",
        "description": "Users should not have to wonder whether different words, situations, or actions mean the same thing. Follow platform and industry conventions.",
        "examples": ["Consistent button styles", "Standard icon meanings", "Predictable navigation", "Uniform spacing"],
    },
    {
        "id": 5,
        "name": "Error Prevention",
        "description": "Good error messages are important, but the best designs carefully prevent problems from occurring in the first place.",
        "examples": ["Confirmation dialogs", "Input validation", "Disabled invalid actions", "Smart defaults", "Constraints"],
    },
    {
        "id": 6,
        "name": "Recognition Rather Than Recall",
        "description": "Minimize the user's memory load by making elements, actions, and options visible. The user should not have to remember information from one part to another.",
        "examples": ["Visible labels", "Recent items", "Autocomplete", "Contextual help", "Tooltips"],
    },
    {
        "id": 7,
        "name": "Flexibility and Efficiency of Use",
        "description": "Shortcuts — hidden from novice users — can speed up the interaction for the expert user so that the design can cater to both inexperienced and experienced users.",
        "examples": ["Keyboard shortcuts", "Gestures", "Customizable UI", "Power-user features", "Cmd+K palettes"],
    },
    {
        "id": 8,
        "name": "Aesthetic and Minimalist Design",
        "description": "Interfaces should not contain information that is irrelevant or rarely needed. Every extra unit of information competes with relevant information.",
        "examples": ["Clean layouts", "Progressive disclosure", "Whitespace", "Focused content", "Hidden complexity"],
    },
    {
        "id": 9,
        "name": "Help Users Recognize, Diagnose, and Recover from Errors",
        "description": "Error messages should be expressed in plain language (no error codes), precisely indicate the problem, and constructively suggest a solution.",
        "examples": ["Inline validation", "Helpful error text", "Suggested fixes", "Clear error states", "Recovery paths"],
    },
    {
        "id": 10,
        "name": "Help and Documentation",
        "description": "It's best if the system doesn't need additional explanation. However, it may be necessary to provide documentation to help users understand how to complete their tasks.",
        "examples": ["Onboarding tours", "Tooltips", "FAQ", "Contextual help", "Empty state guidance"],
    },
]

# UX copy patterns
UX_COPY_PATTERNS = {
    "button": {
        "primary_action": {"pattern": "Verb + Object", "examples": ["Save changes", "Create project", "Send message", "Upload file"]},
        "confirmation": {"pattern": "Verb + Context", "examples": ["Yes, delete", "Confirm payment", "Accept invite"]},
        "navigation": {"pattern": "Destination/Action", "examples": ["Go to dashboard", "View details", "Learn more"]},
    },
    "error": {
        "validation": {"pattern": "What's wrong + How to fix", "examples": ["Email is required. Enter a valid email address.", "Password must be at least 8 characters."]},
        "system": {"pattern": "What happened + What to do", "examples": ["Connection lost. Check your internet and try again.", "Something went wrong. Please refresh the page."]},
        "permission": {"pattern": "Why blocked + How to proceed", "examples": ["You don't have access. Ask your admin for permission.", "This action requires a Pro plan."]},
    },
    "empty_state": {
        "first_use": {"pattern": "What this is + How to start", "examples": ["No projects yet. Create your first project to get started.", "Your inbox is empty. Messages will appear here."]},
        "no_results": {"pattern": "Acknowledge + Suggest", "examples": ["No results for 'xyz'. Try different keywords.", "No matches found. Adjust your filters."]},
    },
    "success": {
        "completion": {"pattern": "What happened + What's next", "examples": ["Project created! Invite your team to collaborate.", "Payment successful. You'll receive a confirmation email."]},
    },
    "loading": {
        "progress": {"pattern": "What's happening", "examples": ["Saving your changes...", "Uploading file...", "Generating report..."]},
    },
}


def _generate_user_flow(name: str, steps: list, include_errors: bool = True) -> dict:
    """Generate a user flow with Mermaid diagram."""
    # Normalize steps: accept both strings and objects
    normalized = []
    for i, step in enumerate(steps):
        if isinstance(step, str):
            stype = "start" if i == 0 else ("end" if i == len(steps) - 1 else "action")
            normalized.append({"label": step, "type": stype})
        else:
            normalized.append(step)
    steps = normalized

    # Build Mermaid flowchart
    mermaid_lines = ["graph TD"]
    node_id = 0

    for i, step in enumerate(steps):
        current_id = f"S{node_id}"
        step_label = step.get("label", f"Step {i+1}")
        step_type = step.get("type", "action")

        # Node shape based on type
        if step_type == "start":
            mermaid_lines.append(f"    {current_id}([\"{step_label}\"])")
        elif step_type == "end":
            mermaid_lines.append(f"    {current_id}([\"{step_label}\"])")
        elif step_type == "decision":
            mermaid_lines.append(f"    {current_id}{{\"{step_label}\"}}")
        elif step_type == "input":
            mermaid_lines.append(f"    {current_id}[/\"{step_label}\"/]")
        else:  # action
            mermaid_lines.append(f"    {current_id}[\"{step_label}\"]")

        # Connect to next
        if i < len(steps) - 1:
            next_id = f"S{node_id + 1}"
            edge_label = step.get("edge_label", "")
            if edge_label:
                mermaid_lines.append(f"    {current_id} -->|\"{edge_label}\"| {next_id}")
            else:
                mermaid_lines.append(f"    {current_id} --> {next_id}")

        # Error branch
        if include_errors and step.get("error"):
            err_id = f"E{node_id}"
            mermaid_lines.append(f"    {err_id}[\"{step['error']}\"]")
            mermaid_lines.append(f"    {current_id} -.->|\"error\"| {err_id}")
            # Error recovery
            if step.get("recovery_to") is not None:
                recovery_target = f"S{step['recovery_to']}"
                mermaid_lines.append(f"    {err_id} -.->|\"retry\"| {recovery_target}")

        node_id += 1

    # Styling
    mermaid_lines.append("")
    mermaid_lines.append("    classDef start fill:#d4edda,stroke:#28a745")
    mermaid_lines.append("    classDef end fill:#d4edda,stroke:#28a745")
    mermaid_lines.append("    classDef error fill:#f8d7da,stroke:#dc3545")
    mermaid_lines.append("    classDef decision fill:#fff3cd,stroke:#ffc107")

    # Apply classes
    for i, step in enumerate(steps):
        if step.get("type") in ("start", "end"):
            mermaid_lines.append(f"    class S{i} {step['type']}")
        elif step.get("type") == "decision":
            mermaid_lines.append(f"    class S{i} decision")

    return {
        "name": name,
        "steps_count": len(steps),
        "mermaid": "\n".join(mermaid_lines),
        "steps_detail": steps,
    }


def _heuristic_eval(screens: list, context: str = "") -> dict:
    """Perform heuristic evaluation on described screens."""
    findings = []

    for screen in screens:
        screen_name = screen.get("name", "Unknown")
        screen_desc = screen.get("description", "")
        elements = screen.get("elements", [])

        screen_findings = []
        for h in NIELSEN_HEURISTICS:
            # Generate contextual check questions
            checks = _get_heuristic_checks(h["id"], elements)
            screen_findings.append({
                "heuristic_id": h["id"],
                "heuristic_name": h["name"],
                "checks": checks,
                "severity": "review",  # Default to review — agent should assess
            })

        findings.append({
            "screen": screen_name,
            "description": screen_desc,
            "findings": screen_findings,
        })

    return {
        "context": context,
        "screens_evaluated": len(screens),
        "findings": findings,
        "heuristics_reference": [{"id": h["id"], "name": h["name"]} for h in NIELSEN_HEURISTICS],
    }


def _get_heuristic_checks(heuristic_id: int, elements: list) -> list:
    """Generate specific check questions based on heuristic and UI elements."""
    checks_map = {
        1: [
            "Does the UI show loading states for async operations?",
            "Are there clear success/error feedback messages?",
            "Can users tell where they are in a multi-step process?",
        ],
        2: [
            "Are labels written in user-friendly language (not developer jargon)?",
            "Do icons match real-world metaphors?",
            "Is information organized in a logical, natural order?",
        ],
        3: [
            "Can users undo destructive actions?",
            "Is there a clear way to cancel/go back?",
            "Can modals be dismissed easily (Escape, click outside)?",
        ],
        4: [
            "Are similar elements styled consistently?",
            "Do interactive elements follow platform conventions?",
            "Is terminology consistent throughout?",
        ],
        5: [
            "Are destructive actions guarded with confirmation?",
            "Does input validation happen before submission?",
            "Are constraints communicated upfront?",
        ],
        6: [
            "Are all options visible rather than requiring memorization?",
            "Is there autocomplete/suggestions where helpful?",
            "Are recently used items easily accessible?",
        ],
        7: [
            "Are keyboard shortcuts available for frequent actions?",
            "Can power users customize their workflow?",
            "Is there a command palette or quick-action feature?",
        ],
        8: [
            "Is the layout clean with adequate whitespace?",
            "Is non-essential information hidden via progressive disclosure?",
            "Does every element serve a clear purpose?",
        ],
        9: [
            "Are error messages in plain language?",
            "Do errors suggest how to fix the problem?",
            "Are error states visually distinct and accessible?",
        ],
        10: [
            "Is there onboarding for first-time users?",
            "Are empty states helpful and actionable?",
            "Is contextual help available where needed?",
        ],
    }
    return checks_map.get(heuristic_id, ["Review this heuristic for the screen."])


def _generate_ux_copy(context: str, element_type: str, tone: str = "warm") -> dict:
    """Generate UX copy suggestions for a given context."""
    tone_modifiers = {
        "warm": {"adjectives": "friendly, approachable, encouraging", "style": "Use contractions, be conversational"},
        "professional": {"adjectives": "clear, confident, respectful", "style": "Be direct, avoid slang"},
        "playful": {"adjectives": "fun, witty, energetic", "style": "Use humor sparingly, be creative"},
        "minimal": {"adjectives": "concise, clean, essential", "style": "Fewest words possible, no fluff"},
    }

    tone_info = tone_modifiers.get(tone, tone_modifiers["warm"])
    patterns = UX_COPY_PATTERNS.get(element_type, {})

    suggestions = []
    for category, pattern_info in patterns.items():
        suggestions.append({
            "category": category,
            "pattern": pattern_info["pattern"],
            "examples": pattern_info["examples"],
            "tone_guidance": tone_info["style"],
        })

    return {
        "context": context,
        "element_type": element_type,
        "tone": tone,
        "tone_characteristics": tone_info["adjectives"],
        "writing_style": tone_info["style"],
        "patterns": suggestions,
        "general_guidelines": [
            "Lead with the verb (action-oriented)",
            "Use sentence case, not Title Case",
            "Keep it under 5 words for buttons, under 15 for descriptions",
            "Be specific — 'Save project' not just 'Save'",
            "Avoid double negatives",
            "Use 'you/your' not 'my/mine' (except for destructive: 'Delete my account')",
        ],
    }


def execute(agent: dict, args: dict) -> dict:
    action = args.get("action", "")

    if action == "user_flow":
        name = args.get("flow_name", args.get("name", "User Flow"))
        steps = args.get("steps", [])
        include_errors = args.get("include_errors", True)

        if not steps:
            return {"status": "error", "message": "steps is required. Provide an array of step objects with 'label', 'type' (start|action|decision|input|end), and optional 'error'/'recovery_to'."}

        flow = _generate_user_flow(name, steps, include_errors)
        return {"status": "ok", "action": "user_flow", **flow}

    elif action == "heuristic_eval":
        screens = args.get("screens", [])
        description = args.get("description", "")
        context = args.get("context", "")

        # Accept a simple description string as a single screen
        if not screens and description:
            screens = [{"name": "Main Screen", "description": description, "elements": []}]

        if not screens:
            return {"status": "error", "message": "Provide 'description' (string) or 'screens' (array of {name, description, elements})."}

        result = _heuristic_eval(screens, context)
        return {"status": "ok", "action": "heuristic_eval", **result}

    elif action == "ux_copy":
        context = args.get("context", "")
        element_type = args.get("element_type", "button")
        tone = args.get("tone", "warm")

        # Normalize kebab-case to snake_case
        element_type = element_type.replace("-", "_")

        valid_types = list(UX_COPY_PATTERNS.keys())
        if element_type not in valid_types:
            return {"status": "error", "message": f"Unknown element_type '{element_type}'. Available: {valid_types}"}

        valid_tones = ["warm", "professional", "playful", "minimal"]
        if tone not in valid_tones:
            return {"status": "error", "message": f"Unknown tone '{tone}'. Available: {valid_tones}"}

        result = _generate_ux_copy(context, element_type, tone)
        return {"status": "ok", "action": "ux_copy", **result}

    else:
        return {
            "status": "error",
            "message": f"Unknown action '{action}'. Available: user_flow, heuristic_eval, ux_copy",
        }
