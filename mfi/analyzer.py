"""Session log analyzer — detects user correction signals in agent conversations.

Scans Hermes Agent session JSON files for correction keywords,
extracts context, and produces structured correction records
that can drive skill evolution.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class CorrectionRecord:
    """A detected correction from session logs."""

    def __init__(
        self,
        session_id: str,
        timestamp: str,
        user_message: str,
        assistant_message: str,
        correction_keyword: str,
        skill_hint: str = "",
        message_id: int = 0,
    ):
        self.session_id = session_id
        self.timestamp = timestamp
        self.user_message = user_message
        self.assistant_message = assistant_message
        self.correction_keyword = correction_keyword
        self.skill_hint = skill_hint
        self.message_id = message_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "correction_keyword": self.correction_keyword,
            "skill_hint": self.skill_hint,
            "message_id": self.message_id,
            "user_message": self.user_message,
            "assistant_message": self.assistant_message,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CorrectionRecord":
        return cls(
            session_id=d["session_id"],
            timestamp=d["timestamp"],
            user_message=d.get("user_message", ""),
            assistant_message=d.get("assistant_message", ""),
            correction_keyword=d.get("correction_keyword", ""),
            skill_hint=d.get("skill_hint", ""),
            message_id=d.get("message_id", 0),
        )

    def __repr__(self) -> str:
        return (
            f"<Correction '{self.correction_keyword}' "
            f"in {self.session_id[:20]}"
            f"{' ~ ' + self.skill_hint[:20] if self.skill_hint else ''}>"
        )


# Skill name patterns — heuristic detection from message content
SKILL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?:skill|skills?)\s*[`'\"]?(\w[\w-]*)"), r"\1"),
    (re.compile(r"tool[-\s]?security[-\s]?audit", re.I), "tool-security-audit"),
    (re.compile(r"code[-\s]?review", re.I), "code-review"),
    (re.compile(r"debu[g{2,3}]ing", re.I), "systematic-debugging"),
    (re.compile(r"codebase[-\s]?map", re.I), "codebase-map"),
    (re.compile(r"opsec|operation[-\s]?security", re.I), "opsec-checklist"),
    (re.compile(r"c2[-\s]?framework|c2 ?infra", re.I), "c2-framework"),
    (re.compile(r"purple[-\s]?team|red[-\s]?team", re.I), "purple-team-exercise"),
    (re.compile(r"weapon[-\s]?arsenal", re.I), "weapon-arsenal"),
    (re.compile(r"cve|vuln[-\s]?research|exploit", re.I), "exploit-dev-workflow"),
    (re.compile(r"github[-\s]?repo|github[-\s]?manage", re.I), "github-repo-management"),
    (re.compile(r"plan|implementation[-\s]?plan", re.I), "writing-plans"),
    (re.compile(r"代码|编码|coding|write code|code\b|脚本|script", re.I), "codex-style-coding"),
    (re.compile(r"docker|container|deploy", re.I), "devops"),
]

# Context window: messages to include before/after a correction
CONTEXT_BEFORE = 3
CONTEXT_AFTER = 2


def load_session_index(sessions_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load the sessions.json index file."""
    index_path = sessions_dir / "sessions.json"
    if not index_path.exists():
        return {}
    try:
        with open(index_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def list_session_files(
    sessions_dir: Path,
    max_age_days: int = 90,
    limit: int = 200,
) -> List[Path]:
    """List session JSON files, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    files = []
    for f in sessions_dir.iterdir():
        if not f.name.endswith(".json") or f.name == "sessions.json":
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff:
                files.append(f)
        except OSError:
            continue

    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def load_session_messages(path: Path) -> List[Dict[str, Any]]:
    """Load and parse a session JSON file, returning message list."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    # Hermes session JSON has direct message structure
    messages = data if isinstance(data, list) else data.get("messages", data.get("conversation", []))
    if isinstance(messages, dict):
        messages = list(messages.values())

    return messages


def extract_skill_hint(text: str) -> str:
    """Heuristically extract a likely skill name from text."""
    for pattern, skill_name in SKILL_PATTERNS:
        m = pattern.search(text)
        if m:
            if "{group}" in skill_name or skill_name.startswith("r'"):
                # Use named group from match
                return m.group(1) if m.lastindex else skill_name
            return skill_name
    return ""


def detect_correction(
    messages: List[Dict[str, Any]],
    keywords: List[str],
    session_id: str,
) -> List[CorrectionRecord]:
    """Scan messages for correction signals.

    A correction pattern: user says a keyword → assistant's previous
    message was wrong/incorrect → needs a patch.
    """
    corrections = []

    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        if role != "user":
            continue

        keyword = _match_keyword(content, keywords)
        if not keyword:
            continue

        # Get the assistant's response that follows (the correction reply)
        assistant_reply = ""
        for j in range(i + 1, min(i + 1 + CONTEXT_AFTER, len(messages))):
            if messages[j].get("role") == "assistant":
                assistant_reply = messages[j].get("content", "")
                break

        # Get the assistant's previous message (what the user is correcting)
        assistant_before = ""
        for j in range(i - 1, max(i - 1 - CONTEXT_BEFORE, -1), -1):
            if messages[j].get("role") == "assistant":
                assistant_before = messages[j].get("content", "")
                break

        skill_hint = extract_skill_hint(content + " " + assistant_before)

        corrections.append(CorrectionRecord(
            session_id=session_id[:40],
            timestamp=msg.get("timestamp", msg.get("created_at", "")),
            user_message=content[:500],
            assistant_message=assistant_before[:500],
            correction_keyword=keyword,
            skill_hint=skill_hint,
            message_id=i,
        ))

    return corrections


def _match_keyword(text: str, keywords: List[str]) -> str:
    """Check if any keyword appears in text. Returns the matched keyword."""
    text_lower = text.lower()
    for kw in keywords:
        if kw in text or kw.lower() in text_lower:
            return kw
    return ""


def deduplicate_corrections(
    corrections: List[CorrectionRecord],
    window_hours: int = 24,
) -> List[CorrectionRecord]:
    """Remove duplicate corrections within a time window.

    If the same skill hint appears from the same session ID
    within the window, keep only the first.
    """
    seen: Set[Tuple[str, str, int]] = set()
    deduped = []

    for c in corrections:
        key = (c.session_id[:20], c.skill_hint, c.message_id // 10)
        if key not in seen:
            seen.add(key)
            deduped.append(c)

    return deduped


def analyze(
    sessions_dir: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
    days: int = 3,
    limit: int = 100,
) -> List[CorrectionRecord]:
    """Main entry point: scan recent session logs for corrections."""
    if config:
        from mfi.config import resolve_paths
        paths = resolve_paths(config)
        sessions_dir = sessions_dir or paths["sessions"]
    if not sessions_dir:
        raise ValueError("sessions_dir required")

    keywords = (config or {}).get("correction_keywords", [
        "不对", "错了", "不是", "重来", "注意",
        "wrong", "incorrect", "not right",
    ])

    session_files = list_session_files(sessions_dir, max_age_days=days, limit=limit)
    all_corrections = []

    for sf in session_files:
        session_id = sf.stem.replace("session_", "", 1) if sf.stem.startswith("session_") else sf.stem
        messages = load_session_messages(sf)
        if not messages:
            continue
        corrections = detect_correction(messages, keywords, session_id)
        all_corrections.extend(corrections)

    # Remove duplicates within 24h window
    window = (config or {}).get("evolution", {}).get("dedup_window_hours", 24)
    all_corrections = deduplicate_corrections(all_corrections, window_hours=window)

    # Apply max per run limit
    max_per_run = (config or {}).get("evolution", {}).get("max_corrections_per_run", 10)
    return all_corrections[:max_per_run]


def print_corrections(corrections: List[CorrectionRecord], verbose: bool = False) -> None:
    """Pretty-print correction records."""
    if not corrections:
        print("[mfi] no corrections found across recent sessions")
        return

    print(f"[mfi] found {len(corrections)} correction(s):\n")
    for i, c in enumerate(corrections, 1):
        print(f"  #{i}  keyword='{c.correction_keyword}'  skill_hint='{c.skill_hint}'")
        print(f"       session={c.session_id[:30]}  msg_id={c.message_id}")
        if verbose:
            um = c.user_message[:200].replace("\n", " ")
            print(f"       user: {um}")
            if c.assistant_message:
                am = c.assistant_message[:200].replace("\n", " ")
                print(f"       prev: {am}")
        print()
