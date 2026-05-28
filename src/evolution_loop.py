"""
evolution_loop.py — Daily self-evolution cron agent.

The core innovation: scan session logs for correction signals,
identify skill gaps, and patch skills automatically.

Run as a daily cron job (recommended: 04:00).
Zero infrastructure — depends only on the agent platform's
native session_search and skill_manage capabilities.

Cost: ~500-1000 tokens per run (≈ $0.0002/day at DeepSeek pricing).
"""

import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

# ─── Correction signals ────────────────────────────────────────────

CORRECTION_KEYWORDS = [
    "不对", "错了", "不是", "重来", "注意", "应该",
    "不是这样", "错了", "不对吧", "wrong", "no,",
    "incorrect", "that's not", "fix it", "纠正",
]

SKILL_INDICATORS = {
    "sql_injection": ["sql", "注入", "sqli", "parameterized", "prepare"],
    "path_traversal": ["路径穿越", "../", "path traversal", "directory"],
    "auth_bypass": ["认证", "auth", "bypass", "未授权", "login"],
    "tool_install": ["安装", "install", "pip", "npm", "gem"],
    "container": ["docker", "容器", "k8s", "kubernetes"],
    "network": ["端口", "port", "curl", "wget", "ssh"],
    "code_review": ["代码", "review", "审查", "code"],
    "debugging": ["debug", "调试", "报错", "error", "traceback"],
}


# ─── Data models ──────────────────────────────────────────────────


@dataclass
class CorrectionSignal:
    """A user correction found in session logs."""
    session_id: str
    message_id: int
    keyword: str
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    agent_response: str = ""
    user_correction: str = ""


@dataclass
class SkillPatch:
    """A recommended patch to a skill based on a correction."""
    skill_name: str
    patch_type: str  # "add_pitfall", "fix_step", "add_step", "new_skill"
    content: str
    confidence: float  # 0.0 - 1.0
    evidence: str = ""


# ─── Analyzers ────────────────────────────────────────────────────


class SessionAnalyzer:
    """Analyze session logs for correction patterns."""

    def __init__(self, lookback_days: int = 3):
        self.lookback_days = lookback_days

    def find_corrections(self, session_logs: list[dict]) -> list[CorrectionSignal]:
        """Scan session logs for correction keywords."""
        signals = []
        for session in session_logs:
            messages = session.get("messages", [])
            for i, msg in enumerate(messages):
                if msg.get("role") != "user":
                    continue
                text = msg.get("content", "")
                for kw in CORRECTION_KEYWORDS:
                    if kw in text:
                        # Get context window
                        ctx_before = [
                            m.get("content", "")[:200]
                            for m in messages[max(0, i - 3):i]
                            if m.get("role") == "assistant"
                        ]
                        ctx_after = [
                            m.get("content", "")[:200]
                            for m in messages[i + 1:i + 2]
                            if m.get("role") == "assistant"
                        ]
                        signals.append(CorrectionSignal(
                            session_id=session.get("id", "?"),
                            message_id=msg.get("id", 0),
                            keyword=kw,
                            context_before=ctx_before,
                            context_after=ctx_after,
                            timestamp=datetime.fromtimestamp(
                                msg.get("timestamp", 0)
                            ) if msg.get("timestamp") else None,
                            user_correction=text[:300],
                            agent_response=ctx_before[-1] if ctx_before else "",
                        ))
        return signals


class SkillAnalyzer:
    """Identify which skill needs patching based on correction context."""

    def __init__(self, skills_manifest: dict[str, str]):
        self.skills = skills_manifest  # {skill_name: skill_content}

    def identify_skill(self, signal: CorrectionSignal) -> Optional[str]:
        """Map a correction signal to the most relevant skill."""
        context = " ".join(signal.context_before + signal.context_after)
        context += " " + signal.user_correction

        best_skill = None
        best_score = 0

        for skill_name, indicators in SKILL_INDICATORS.items():
            # Check if the skill exists in our manifest
            if skill_name not in self.skills:
                continue
            score = sum(
                2 if ind in context else 0
                for ind in indicators
            )
            if score > best_score:
                best_score = score
                best_skill = skill_name

        return best_skill if best_score > 0 else None

    def analyze_recurring(self, signals: list[CorrectionSignal]) -> list[SkillPatch]:
        """Detect recurring patterns → generate patches."""

        patches = []
        context_groups: dict[str, list[CorrectionSignal]] = {}

        for s in signals:
            skill = self.identify_skill(s)
            if not skill:
                continue
            if skill not in context_groups:
                context_groups[skill] = []
            context_groups[skill].append(s)

        for skill_name, group in context_groups.items():
            if len(group) >= 2:
                # Recurring → high confidence patch needed
                last_signal = group[-1]
                patches.append(SkillPatch(
                    skill_name=skill_name,
                    patch_type="add_pitfall",
                    content=f"⚠️ 重复纠正（{len(group)}次）: "
                            f"{last_signal.user_correction[:100]}",
                    confidence=0.8 + min(0.15, len(group) * 0.05),
                    evidence=f"出现{len(group)}次纠正信号于{skill_name}相关上下文",
                ))

        return patches

    def generate_patch_content(self, patch: SkillPatch) -> str:
        """Generate the actual markdiff/patch content for a skill."""
        if patch.patch_type == "add_pitfall":
            return (
                f"\n## Pitfalls\n"
                f"- {patch.content}\n"
            )
        return patch.content


# ─── Evolution Loop ───────────────────────────────────────────────


class EvolutionLoop:
    """
    The core evolution loop.

    Designed to be called by a cron job. The actual session_search
    and skill_manage calls are platform-specific and should be
    injected via the `session_search_fn` and `skill_manage_fn` hooks.
    """

    def __init__(
        self,
        session_search_fn=None,
        skill_manage_fn=None,
        lookback_days: int = 3,
    ):
        self.session_search = session_search_fn
        self.skill_manage_fn = skill_manage_fn
        self.analyzer = SessionAnalyzer(lookback_days=lookback_days)
        self.stats = {
            "sessions_scanned": 0,
            "corrections_found": 0,
            "patches_generated": 0,
            "patches_applied": 0,
        }

    def run(self) -> dict:
        """Execute one evolution cycle."""
        report = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "changes": [],
            "stats": self.stats,
        }

        # Step 1: Fetch session logs
        sessions = self._fetch_sessions()
        if not sessions:
            report["status"] = "no_sessions"
            return report

        self.stats["sessions_scanned"] = len(sessions)

        # Step 2: Find corrections
        signals = self.analyzer.find_corrections(sessions)
        self.stats["corrections_found"] = len(signals)

        if not signals:
            return report

        # Step 3: Load skill manifest
        skills = self._load_skills()
        if not skills:
            report["status"] = "no_skills"
            return report

        skill_analyzer = SkillAnalyzer(skills)

        # Step 4: Detect recurring patterns
        patches = skill_analyzer.analyze_recurring(signals)
        self.stats["patches_generated"] = len(patches)

        # Step 5: Apply patches
        for patch in patches:
            if patch.confidence >= 0.8:
                success = self._apply_patch(patch)
                if success:
                    self.stats["patches_applied"] += 1
                    report["changes"].append({
                        "skill": patch.skill_name,
                        "type": patch.patch_type,
                        "confidence": patch.confidence,
                        "evidence": patch.evidence,
                    })

        return report

    def _fetch_sessions(self) -> list[dict]:
        """Fetch recent sessions via the injected function."""
        if self.session_search:
            return self.session_search(
                keywords=CORRECTION_KEYWORDS,
                lookback_days=self.analyzer.lookback_days,
            )
        return []

    def _load_skills(self) -> dict[str, str]:
        """Load available skills."""
        return {}

    def _apply_patch(self, patch: SkillPatch) -> bool:
        """Apply a patch to a skill."""
        if self.skill_manage_fn:
            content = SkillAnalyzer.generate_patch_content(patch)
            return self.skill_manage_fn(
                action="patch",
                name=patch.skill_name,
                content=content,
            )
        return False


# ─── CLI entry point ──────────────────────────────────────────────


def main():
    """Run the evolution loop (standalone mode for testing)."""
    loop = EvolutionLoop()
    report = loop.run()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
