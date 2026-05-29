"""Evolution metrics dashboard — terminal-based evolution status display."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import load_config, resolve_paths


def _load_history(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def status(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get current evolution status summary."""
    config = load_config(config_path)
    paths = resolve_paths(config)
    history_path = paths["hermes_home"] / "mfi_history.json"
    history = _load_history(history_path)

    # Session count
    session_dir = paths["sessions"]
    session_count = 0
    if session_dir.exists():
        session_count = len([f for f in session_dir.iterdir()
                            if f.name.endswith(".json") and f.name != "sessions.json"])

    # Skills count
    skills_dir = paths["skills"]
    skill_count = 0
    if skills_dir.exists():
        skill_count = len([f for f in skills_dir.rglob("SKILL.md")])

    # Evolution stats
    total_runs = len(history)
    total_corrections = sum(h.get("corrections_found", 0) for h in history)
    total_patches = sum(h.get("patches_applied", 0) for h in history)

    last_run = history[-1] if history else None
    last_corrections = last_run.get("corrections_found", 0) if last_run else 0
    last_patches = last_run.get("patches_applied", 0) if last_run else 0

    return {
        "sessions": session_count,
        "skills": skill_count,
        "evolution_runs": total_runs,
        "total_corrections_found": total_corrections,
        "total_patches_applied": total_patches,
        "last_run_corrections": last_corrections,
        "last_run_patches": last_patches,
        "last_run_timestamp": last_run.get("timestamp", "never") if last_run else "never",
        "history": history[-10:] if history else [],
    }


def print_status(status_data: Dict[str, Any]) -> None:
    """Print evolution status to terminal."""
    print("╔══════════════════════════════════════════╗")
    print("║   Model-Free Intelligence Status         ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Sessions:   {status_data['sessions']:>4} files                      ║")
    print(f"║  Skills:     {status_data['skills']:>4} SKILL.md files               ║")
    print(f"║  Runs:       {status_data['evolution_runs']:>4} total                     ║")
    print(f"║  Found:      {status_data['total_corrections_found']:>4} corrections              ║")
    print(f"║  Patches:    {status_data['total_patches_applied']:>4} applied                   ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Last run:   {status_data['last_run_timestamp'][:19]}       ║")
    print(f"║  Found:      {status_data['last_run_corrections']} corrections               ║")
    print(f"║  Applied:    {status_data['last_run_patches']} patches                   ║")
    print("╚══════════════════════════════════════════╝")

    history = status_data.get("history", [])
    if history:
        print(f"\n  Recent runs:")
        for h in history[-5:]:
            ts = h.get("timestamp", "?")[5:19]
            corr = h.get("corrections_found", 0)
            appl = h.get("patches_applied", 0)
            marker = "✅" if appl else ("📝" if corr else "—")
            print(f"    {marker} {ts}  found={corr}  applied={appl}")
