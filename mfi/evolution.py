"""Evolution loop orchestrator — the core MFI loop.

The evolution loop:
1. Analyze recent session logs for corrections
2. Generate patch proposals
3. Apply patches (in auto mode) or report (in review mode)
4. Record evolution metrics
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analyzer import CorrectionRecord, analyze, print_corrections
from .patcher import PatchProposal, propose_patches, print_proposals
from .config import load_config, resolve_paths, default_config_path


class EvolutionReport:
    """Report from a single evolution run."""

    def __init__(self):
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.sessions_scanned: int = 0
        self.corrections_found: int = 0
        self.patches_proposed: int = 0
        self.patches_applied: int = 0
        self.patches_skipped: int = 0
        self.errors: List[str] = []
        self.proposals: List[PatchProposal] = []
        self.applied_skills: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "sessions_scanned": self.sessions_scanned,
            "corrections_found": self.corrections_found,
            "patches_proposed": self.patches_proposed,
            "patches_applied": self.patches_applied,
            "patches_skipped": self.patches_skipped,
            "errors": self.errors,
            "applied_skills": self.applied_skills,
        }

    def summary(self) -> str:
        parts = [
            f"[mfi] │ sessions scanned: {self.sessions_scanned}",
            f"     │ corrections found: {self.corrections_found}",
            f"     │ patches proposed:  {self.patches_proposed}",
        ]
        if self.patches_applied:
            parts.append(f"     │ patches applied:   {self.patches_applied} ✅")
            for s in self.applied_skills:
                parts.append(f"     │   → {s}")
        if self.patches_skipped:
            parts.append(f"     │ patches skipped:   {self.patches_skipped}")
        if self.errors:
            parts.append(f"     │ errors:            {len(self.errors)}")
            for e in self.errors[:3]:
                parts.append(f"     │   ⚠ {e}")
        if not self.corrections_found and not self.errors:
            parts.append("     │ no changes needed")

        return "\n".join(parts)


def _load_history(history_path: Path) -> List[Dict[str, Any]]:
    """Load evolution history from JSON."""
    if not history_path.exists():
        return []
    try:
        with open(history_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_history(history_path: Path, reports: List[Dict[str, Any]], max_entries: int = 100) -> None:
    """Save evolution history, keeping only latest entries."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = reports[-max_entries:]
    with open(history_path, "w") as f:
        json.dump(trimmed, f, indent=2, ensure_ascii=False)


def run_evolution(
    config_path: Optional[Path] = None,
    auto_apply: bool = True,
    days: int = 3,
    verbose: bool = False,
) -> EvolutionReport:
    """Run one iteration of the evolution loop.

    Args:
        config_path: Path to MFI config (default: ~/.mfi/config.json)
        auto_apply: If True, apply high-confidence patches automatically
        days: How many days of session logs to scan
        verbose: Print detailed output
    """
    config = load_config(config_path)
    paths = resolve_paths(config)

    report = EvolutionReport()

    # Step 1: Analyze session logs
    if verbose:
        print("[mfi] scanning session logs...")

    corrections = analyze(
        sessions_dir=paths["sessions"],
        config=config,
        days=days,
    )
    report.corrections_found = len(corrections)
    report.sessions_scanned = len(list(paths["sessions"].glob("*.json"))) - 1  # exclude index

    if verbose and corrections:
        print_corrections(corrections, verbose=verbose)

    if not corrections:
        if verbose:
            print("[mfi] no corrections found, evolution complete")
        _record_history(paths, report)
        return report

    # Step 2: Generate patch proposals
    if verbose:
        print("\n[mfi] generating patch proposals...")

    proposals = propose_patches(
        corrections=corrections,
        skills_dir=paths["skills"],
        config=config,
    )
    report.patches_proposed = len(proposals)
    report.proposals = proposals

    if verbose and proposals:
        print_proposals(proposals, verbose=verbose)

    if not proposals:
        if verbose:
            print("[mfi] no patch proposals generated")
        _record_history(paths, report)
        return report

    # Step 3: Apply patches (if auto_apply)
    min_confidence = config.get("evolution", {}).get("min_confidence", 0.3)

    for p in proposals:
        if p.confidence < min_confidence:
            report.patches_skipped += 1
            if verbose:
                print(f"[mfi] skipping low-confidence patch: {p.skill_name} ({p.confidence:.0%})")
            continue

        if auto_apply:
            success = _apply_patch(p, paths["hermes_home"], verbose)
            if success:
                report.patches_applied += 1
                report.applied_skills.append(p.skill_name)
            else:
                report.errors.append(f"Failed to apply patch to {p.skill_name}")
        else:
            report.patches_skipped += 1
            if verbose:
                print(f"[mfi] review mode: patch for {p.skill_name} ready (confidence={p.confidence:.0%})")

    # Record history
    _record_history(paths, report)

    if verbose:
        print(f"\n[mfi] evolution complete")
        print(report.summary())

    return report


def _apply_patch(
    proposal: PatchProposal,
    hermes_home: Path,
    verbose: bool = False,
) -> bool:
    """Apply a patch to the skill file on disk.

    This is a filesystem-level patch. For Hermes Agent integration,
    this would use skill_manage tool; here we do direct file editing.
    """
    # Find the skill file
    for root, dirs, files in os.walk(hermes_home / "skills"):
        for f in files:
            if f == "SKILL.md" and Path(root).name == proposal.skill_name:
                skill_path = Path(root) / f
                break
        else:
            continue
        break
    else:
        if verbose:
            print(f"[mfi] skill file not found: {proposal.skill_name}")
        return False

    try:
        content = skill_path.read_text()
    except OSError as e:
        if verbose:
            print(f"[mfi] cannot read {skill_path}: {e}")
        return False

    # Find the target section
    section_header = f"### {proposal.section}"
    if section_header not in content:
        # Try ## header
        section_header = f"## {proposal.section}"
        if section_header not in content:
            if verbose:
                print(f"[mfi] section '{proposal.section}' not found in {proposal.skill_name}")
            return False

    # Append content at end of section
    section_end = content.find(section_header)
    next_section = content.find("\n## ", section_end + 1)
    if next_section == -1:
        next_section = content.find("\n### ", section_end + 1)
    if next_section == -1:
        insert_pos = len(content)
    else:
        insert_pos = next_section

    # Insert before the next section
    new_content = (
        content[:insert_pos]
        + "\n"
        + proposal.patch_content
        + "\n"
        + content[insert_pos:]
    )

    try:
        skill_path.write_text(new_content)
        if verbose:
            print(f"[mfi] ✅ patched {proposal.skill_name}/{proposal.section}")
        return True
    except OSError as e:
        if verbose:
            print(f"[mfi] cannot write {skill_path}: {e}")
        return False


def _record_history(paths: Dict[str, Path], report: EvolutionReport) -> None:
    """Record evolution run to history file."""
    history_path = paths["hermes_home"] / "mfi_history.json"
    history = _load_history(history_path)
    history.append(report.to_dict())
    _save_history(history_path, history)
