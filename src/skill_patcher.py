"""
skill_patcher.py — Platform-agnostic skill patching routines.

Parses SKILL.md content, identifies structural sections,
and generates precise patches for the evolution loop.
"""

import re

# ─── Skill structure ──────────────────────────────────────────────

SKILL_SECTIONS = {
    "title": r"^#\s+(.+)$",
    "trigger": r"^##\s+Trigger",
    "steps": r"^##\s+Steps",
    "pitfalls": r"^##\s+Pitfalls",
    "verification": r"^##\s+Verification",
    "references": r"^##\s+References",
    "notes": r"^##\s+Notes",
}


def parse_skill(markdown: str) -> dict:
    """
    Parse a SKILL.md file into its structural sections.

    Returns:
        {section_name: content_lines}
    """
    lines = markdown.split("\n")
    sections = {}
    current_section = "preamble"
    current_lines = []

    for line in lines:
        # Check if this line starts a new section
        for section_name, pattern in SKILL_SECTIONS.items():
            if re.match(pattern, line.strip()):
                # Save previous section
                sections[current_section] = "\n".join(current_lines)
                # Start new section
                current_section = section_name
                current_lines = [line]
                break
            elif section_name == "title" and re.match(r"^##?\s+", line.strip()):
                # Also catch any ## heading as potential section
                pass
        else:
            current_lines.append(line)

    # Save last section
    sections[current_section] = "\n".join(current_lines)
    return sections


def generate_pitfall_patch(
    current_content: str,
    pitfall_text: str,
) -> str:
    """
    Add a new pitfall entry to the Pitfalls section.
    Creates the section if it doesn't exist.
    """
    sections = parse_skill(current_content)

    if "pitfalls" in sections:
        # Append to existing pitfalls
        pitfalls = sections["pitfalls"]
        # Find where to insert (after the ## Pitfalls header)
        lines = pitfalls.split("\n")
        # Add after header
        new_lines = lines[:1]  # Keep header
        # Check if there's already content after header
        if len(lines) > 1 and lines[1].strip().startswith("-"):
            new_lines.extend(lines[1:])
        new_lines.append(f"- {pitfall_text}")
        sections["pitfalls"] = "\n".join(new_lines)
    else:
        # Create new pitfalls section at the end
        sections["pitfalls"] = f"## Pitfalls\n\n- {pitfall_text}"

    # Reassemble
    result = []
    for section_name in [
        "preamble", "title", "trigger", "steps",
        "pitfalls", "verification", "references", "notes"
    ]:
        if section_name in sections and sections[section_name].strip():
            content = sections[section_name].strip()
            if result:
                result.append("")  # spacing
            result.append(content)

    return "\n".join(result)


def generate_step_patch(
    current_content: str,
    new_step: str,
    position: int = -1  # -1 = append
) -> str:
    """
    Add a new step to the Steps section.
    """
    sections = parse_skill(current_content)

    if "steps" not in sections:
        sections["steps"] = "## Steps"
        steps_lines = [sections["steps"]]
    else:
        steps_lines = sections["steps"].split("\n")

    # Count existing steps
    existing = [line for line in steps_lines if re.match(r"^\d+\.", line.strip())]
    step_num = len(existing) + 1

    if position == -1 or position >= len(steps_lines):
        steps_lines.append(f"{step_num}. {new_step}")
    else:
        steps_lines.insert(position, f"{step_num}. {new_step}")

    sections["steps"] = "\n".join(steps_lines)
    # Reassemble
    result = []
    for sn in [
        "preamble", "title", "trigger", "steps",
        "pitfalls", "verification", "references", "notes"
    ]:
        if sn in sections and sections[sn].strip():
            content = sections[sn].strip()
            if result:
                result.append("")
            result.append(content)

    return "\n".join(result)


def diff_skills(old: str, new: str) -> str:
    """
    Simple line-based diff between old and new skill content.
    Returns a human-readable change summary.
    """
    old_lines = old.split("\n")
    new_lines = new.split("\n")

    added = [line for line in new_lines if line not in old_lines and line.strip()]
    removed = [line for line in old_lines if line not in new_lines and line.strip()]

    changes = []
    if added:
        changes.append(f"+{len(added)} lines added")
    if removed:
        changes.append(f"-{len(removed)} lines removed")

    return "; ".join(changes) if changes else "no structural change"
