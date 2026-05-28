"""
session_analyzer.py — Session log pattern extractor.

Scans Hermes agent session logs to extract:
- Correction patterns (user corrected the agent → skill gap)
- Recurring task types
- Tool usage patterns
- Success/failure signals

Output: structured Experience objects for evolution pipeline.
"""

import re
import os
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class CorrectionSignal:
    """A user correction that indicates a skill gap."""
    trigger_phrase: str          # e.g., "不对", "不是", "错了"
    context_before: str          # what agent did wrong
    context_after: str           # what user expected
    domain_tags: List[str]       # e.g., ["cron", "deployment"]
    session_id: str = ""
    timestamp: str = ""


@dataclass
class Experience:
    """Structured learning from a session."""
    source: str                  # session_id or file path
    agent: str                   # agent name
    pattern: str                 # what was learned
    category: str                # tool | workflow | domain | correction
    payload: Dict[str, Any]      # structured data
    confidence: float = 0.7


CORRECTION_PHRASES = [
    "不对", "不是", "错了", "不对吗",
    "不是这个", "我说的是", "你理解错了",
    "不要", "停", "重来", "不是这样",
    "no", "wrong", "not what I meant",
    "that's not right", "incorrect",
]


def scan_logs(log_dir: str, max_files: int = 50) -> List[CorrectionSignal]:
    """Scan session log files for correction signals."""
    signals = []
    if not os.path.isdir(log_dir):
        return signals

    json_files = [f for f in os.listdir(log_dir) if f.endswith('.json')]
    for fname in json_files[-max_files:]:
        fpath = os.path.join(log_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue

        for phrase in CORRECTION_PHRASES:
            idx = content.find(phrase)
            if idx >= 0:
                start = max(0, idx - 200)
                end = min(len(content), idx + 400)
                signals.append(CorrectionSignal(
                    trigger_phrase=phrase,
                    context_before=content[start:idx],
                    context_after=content[idx:end],
                    domain_tags=_infer_tags(content[idx:idx+500]),
                    session_id=fname.replace('.json', ''),
                ))
                break
    return signals


def _infer_tags(text: str) -> List[str]:
    """Infer domain tags from text context."""
    tags = []
    patterns = {
        "cron": r"cron|crontab|schedule|定时",
        "docker": r"docker|container|compose",
        "deployment": r"deploy|ssh|server|nginx",
        "python": r"python|pip|venv|virtualenv",
        "github": r"github|gh |git |push|commit",
        "security": r"vuln|cve|exploit|漏洞",
    }
    for tag, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            tags.append(tag)
    return tags


def extract_patterns(signals: List[CorrectionSignal]) -> List[Experience]:
    """Convert raw signals to structured experiences."""
    experiences = []
    seen = set()

    for sig in signals:
        key = hash(sig.context_before[:100]) ^ hash(sig.trigger_phrase)
        if key in seen:
            continue
        seen.add(key)

        exp = Experience(
            source=sig.session_id,
            agent="unknown",
            pattern=f"Correction: {sig.trigger_phrase}",
            category="correction",
            payload={
                "trigger": sig.trigger_phrase,
                "before_snippet": sig.context_before[:100],
                "after_snippet": sig.context_after[:200],
                "tags": sig.domain_tags,
            },
            confidence=0.6 if len(sig.context_before) < 50 else 0.8,
        )
        experiences.append(exp)

    return experiences


def analyze_session(session_dir: str) -> Dict[str, Any]:
    """Full session analysis: corrections + patterns + stats."""
    signals = scan_logs(session_dir)
    experiences = extract_patterns(signals)

    return {
        "files_scanned": len([f for f in os.listdir(session_dir) if f.endswith('.json')]) if os.path.isdir(session_dir) else 0,
        "corrections_found": len(signals),
        "experiences_extracted": len(experiences),
        "top_tags": _top_tags(experiences),
        "experiences": [{
            "pattern": e.pattern,
            "category": e.category,
            "tags": e.payload.get("tags", []),
            "confidence": e.confidence,
        } for e in experiences],
    }


def _top_tags(experiences: List[Experience], n: int = 5) -> List[Tuple[str, int]]:
    """Return most common domain tags."""
    from collections import Counter
    counter: Counter = Counter()
    for e in experiences:
        for t in e.payload.get("tags", []):
            counter[t] += 1
    return counter.most_common(n)
