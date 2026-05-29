"""Skill patcher — generates and applies skill patches from correction records.

The patcher maps detected corrections to existing skills and
generates structured patch content (new pitfalls, refined steps, etc.)
that can be applied via Hermes Agent's skill_manage tool.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .analyzer import CorrectionRecord


# Known skills with their correction-relevant sections
SKILL_SECTIONS = {
    "codex-style-coding": {
        "path": "software-development/codex-style-coding/SKILL.md",
        "correction_sections": ["硬性规定", "预检清单", "3次失败断路器"],
    },
    "tool-security-audit": {
        "path": "devops/tool-security-audit/SKILL.md",
        "correction_sections": ["步骤", "Pitfalls"],
    },
    "systematic-debugging": {
        "path": "software-development/systematic-debugging/SKILL.md",
        "correction_sections": ["步骤", "Pitfalls"],
    },
    "github-repo-management": {
        "path": "github/github-repo-management/SKILL.md",
        "correction_sections": ["步骤", "注意事项"],
    },
    "opsec-checklist": {
        "path": "red-teaming/opsec-checklist/SKILL.md",
        "correction_sections": ["步骤", "Pitfalls"],
    },
    "writing-plans": {
        "path": "software-development/writing-plans/SKILL.md",
        "correction_sections": ["步骤", "规则"],
    },
}


class PatchProposal:
    """A proposed skill patch derived from a correction record."""

    def __init__(
        self,
        correction: CorrectionRecord,
        skill_name: str,
        section: str,
        patch_content: str,
        confidence: float,
        reasoning: str,
    ):
        self.correction = correction
        self.skill_name = skill_name
        self.section = section
        self.patch_content = patch_content
        self.confidence = confidence
        self.reasoning = reasoning
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "section": self.section,
            "patch_content": self.patch_content,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "correction": self.correction.to_dict(),
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return (
            f"<Patch {self.skill_name}/{self.section} "
            f"confidence={self.confidence:.2f}>"
        )


def _load_skill_files(skills_dir: Path) -> Dict[str, Path]:
    """Scan skills directory for all SKILL.md files."""
    skill_files = {}
    if not skills_dir.exists():
        return skill_files

    for root, dirs, files in os.walk(skills_dir):
        for f in files:
            if f == "SKILL.md":
                rel_path = Path(root) / f
                # Extract skill name from parent dir name
                skill_name = Path(root).name
                skill_files[skill_name] = rel_path

    return skill_files


def _extract_section_content(path: Path, section_name: str) -> Optional[str]:
    """Extract a markdown section's content from a SKILL.md file."""
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
        return None

    # Find ## or ### heading matching section_name
    pattern = re.compile(
        r"^#+\s+" + re.escape(section_name) + r"\s*$",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        return None

    start = match.end()
    # Find next section heading
    next_section = re.search(r"^#+\s+\S", content[start:], re.MULTILINE)
    end = start + next_section.start() if next_section else len(content)
    return content[start:end].strip()


def _classify_correction_type(user_message: str) -> str:
    """Classify what kind of correction the user made."""
    msg = user_message.lower()

    if any(w in msg for w in ["没跑", "不跑验证", "没验证", "skip", "跳过"]):
        return "verification_skip"
    if any(w in msg for w in ["没读需求", "需求不清晰", "理解错了", "方向错了"]):
        return "requirement_misread"
    if any(w in msg for w in ["没scan", "没看结构", "codebase_map", "不理解代码"]):
        return "structure_miss"
    if any(w in msg for w in ["报错", "错误", "error", "exception", "traceback"]):
        return "error_not_handled"
    if any(w in msg for w in ["加戏", "乱加", "不需要", "多余"]):
        return "over_engineering"
    return "general"


def propose_patches(
    corrections: List[CorrectionRecord],
    skills_dir: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
) -> List[PatchProposal]:
    """Generate patch proposals from correction records."""
    proposals = []

    if config:
        from mfi.config import resolve_paths
        paths = resolve_paths(config)
        skills_dir = skills_dir or paths["skills"]

    if not skills_dir:
        # Try default
        from mfi.config import DEFAULT_CONFIG
        from mfi.config import resolve_paths
        paths = resolve_paths(DEFAULT_CONFIG)
        skills_dir = skills_dir or paths["skills"]

    # Ensure skills_dir exists
    if not skills_dir.exists():
        print(f"[mfi] warning: skills dir not found at {skills_dir}")
        return proposals

    skill_files = _load_skill_files(skills_dir)

    for c in corrections:
        correction_type = _classify_correction_type(c.user_message)
        target_skill = c.skill_hint or _map_correction_to_skill(correction_type)

        if target_skill and target_skill in skill_files:
            proposal = _build_patch_proposal(
                c, target_skill, correction_type, skill_files[target_skill]
            )
            if proposal:
                proposals.append(proposal)
        elif target_skill:
            # Skill exists in SKILL_SECTIONS registry but not installed
            proposal = _build_generic_proposal(c, target_skill, correction_type)
            proposals.append(proposal)

    return proposals


def _map_correction_to_skill(correction_type: str) -> str:
    """Map correction type to the most likely skill."""
    mapping = {
        "verification_skip": "codex-style-coding",
        "requirement_misread": "codex-style-coding",
        "structure_miss": "codex-style-coding",
        "error_not_handled": "systematic-debugging",
        "over_engineering": "codex-style-coding",
    }
    return mapping.get(correction_type, "codex-style-coding")


def _build_patch_proposal(
    correction: CorrectionRecord,
    skill_name: str,
    correction_type: str,
    skill_path: Path,
) -> Optional[PatchProposal]:
    """Build a concrete patch proposal for an installed skill."""
    try:
        skill_content = skill_path.read_text()
    except OSError:
        return None

    # Determine which section to patch and what content to add
    section, patch_content, reasoning = _generate_patch(
        correction, correction_type, skill_content
    )

    if not patch_content:
        return None

    confidence = _calc_confidence(correction_type, correction.assistant_message)
    return PatchProposal(
        correction=correction,
        skill_name=skill_name,
        section=section,
        patch_content=patch_content,
        confidence=confidence,
        reasoning=reasoning,
    )


def _build_generic_proposal(
    correction: CorrectionRecord,
    skill_name: str,
    correction_type: str,
) -> PatchProposal:
    """Build a proposal for a known but not-installed skill."""
    section, patch_content, reasoning = _generate_patch(
        correction, correction_type, ""
    )
    if not patch_content:
        section = "Pitfalls"
        patch_content = f"\n- {correction.user_message[:100]}"
        reasoning = "User correction suggests new pitfall for this skill"

    confidence = _calc_confidence(correction_type, correction.assistant_message)
    final_section: str = section or "Pitfalls"
    return PatchProposal(
        correction=correction,
        skill_name=skill_name,
        section=final_section,
        patch_content=patch_content,
        confidence=confidence,
        reasoning=reasoning,
    )


def _generate_patch(
    correction: CorrectionRecord,
    correction_type: str,
    skill_content: str,
) -> Tuple[Optional[str], str, str]:
    """Generate specific patch content based on correction type."""
    user_msg = correction.user_message

    if correction_type == "verification_skip":
        return (
            "硬性规定",
            (
                "\n- [ ] 写完了？→ 立刻跑验证，不准跳过\n"
                "**不跑验证就交代码 = 没写完。**"
            ),
            "User corrected agent for skipping verification step"
        )

    if correction_type == "requirement_misread":
        return (
            "硬性规定",
            (
                "\n不确定需求时，用 `clarify` 或直接问用户，"
                "不准猜测。猜错了重写成本比问一句高10倍。"
            ),
            "Agent misread requirements and delivered wrong implementation"
        )

    if correction_type == "structure_miss":
        return (
            "第零步",
            (
                "\n**不codebase_map scan不准改代码，这是死命令。**"
            ),
            "Agent modified code without understanding dependencies first"
        )

    if correction_type == "error_not_handled":
        return (
            "第四步",
            (
                "\n报错先读完整traceback的**最后一行**（调用栈底部），"
                "找到真正原因再修。只看第一行瞎猜是浪费时间。"
            ),
            "Agent fixed errors without reading full traceback"
        )

    if correction_type == "over_engineering":
        return (
            "硬性规定",
            (
                "\n只做用户明确要求的，不猜补充需求，不加戏。"
                "加任何会触发外部通知的东西（CI/CD、webhook、"
                "监控告警）必须先问用户让不让加。"
            ),
            "Agent added unrequested features that caused notification spam"
        )

    return (None, "", "")


def _calc_confidence(correction_type: str, assistant_msg: str) -> float:
    """Calculate confidence score for a patch proposal."""
    base = 0.5
    # High confidence types
    if correction_type in ("verification_skip", "requirement_misread", "over_engineering"):
        base += 0.3
    # If assistant acknowledged the mistake, higher confidence
    if any(w in assistant_msg.lower() for w in ["sorry", "fix", "correct", "抱歉", "修", "改"]):
        base += 0.2
    return min(base, 1.0)


def print_proposals(proposals: List[PatchProposal], verbose: bool = False) -> None:
    """Pretty-print patch proposals."""
    if not proposals:
        print("[mfi] no patch proposals to display")
        return

    print(f"[mfi] {len(proposals)} patch proposal(s):\n")
    for i, p in enumerate(proposals, 1):
        print(f"  #{i}  skill={p.skill_name}/{p.section}")
        print(f"       confidence={p.confidence:.0%}  type={p.reasoning}")
        if verbose:
            for line in p.patch_content.strip().split("\n"):
                print(f"       | {line}")
        print()
