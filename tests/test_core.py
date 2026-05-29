"""Tests for the MFI package — core modules."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from mfi.config import (
    load_config,
    save_config,
    init_config,
    default_config_path,
    resolve_paths,
    DEFAULT_CONFIG,
)
from mfi.analyzer import (
    detect_correction,
    deduplicate_corrections,
    extract_skill_hint,
    CorrectionRecord,
    _match_keyword,
)
from mfi.patcher import (
    propose_patches,
    PatchProposal,
    _classify_correction_type,
    _calc_confidence,
)


# ─── Analyzer Tests ─────────────────────────────────────────────


class TestMatchKeyword:
    def test_chinese_keyword_match(self):
        assert _match_keyword("这个不对", ["不对", "错了"]) == "不对"
        assert _match_keyword("你错了", ["不对", "错了"]) == "错了"
        assert _match_keyword("不是这样做的", ["不对", "不是"]) == "不是"

    def test_english_keyword_match(self):
        assert _match_keyword("that's wrong", ["wrong", "incorrect"]) == "wrong"
        assert _match_keyword("not right at all", ["wrong", "not right"]) == "not right"

    def test_no_match(self):
        assert _match_keyword("everything is fine", ["不对", "错了"]) == ""


class TestSkillHint:
    def test_coding_skill_hint(self):
        assert extract_skill_hint("代码写得不对") == "codex-style-coding"
        assert extract_skill_hint("write code for this") == "codex-style-coding"

    def test_tool_security_hint(self):
        assert extract_skill_hint("run tool security audit first") == "tool-security-audit"

    def test_github_hint(self):
        assert extract_skill_hint("use github-repo-management") == "github-repo-management"

    def test_no_hint(self):
        assert extract_skill_hint("hello world") == ""


class TestDetectCorrection:
    def test_detect_simple_correction(self):
        messages = [
            {"role": "assistant", "content": "I'll write the code to add the visualizer module"},
            {"role": "user", "content": "这个不对，不要乱加东西"},
        ]
        corrections = detect_correction(messages, ["不对", "乱加"], "test-session")
        assert len(corrections) == 1
        assert corrections[0].correction_keyword == "不对"
        assert corrections[0].skill_hint == "codex-style-coding"

    def test_no_correction_in_normal_conversation(self):
        messages = [
            {"role": "user", "content": "帮我写一个Python脚本"},
            {"role": "assistant", "content": "好的，我来写..."},
        ]
        corrections = detect_correction(messages, ["不对", "错了"], "test-session")
        assert len(corrections) == 0

    def test_multiple_corrections(self):
        messages = [
            {"role": "assistant", "content": "Here's the code"},
            {"role": "user", "content": "不对，少了个参数"},
            {"role": "assistant", "content": "Fixed it"},
            {"role": "user", "content": "还是不对，你看看"},
        ]
        corrections = detect_correction(messages, ["不对", "错了"], "test-session")
        assert len(corrections) == 2


class TestDeduplicate:
    def test_dedup_same_session(self):
        c1 = CorrectionRecord("s1", "", "不对", "", "不对", "codex-style-coding", 5)
        c2 = CorrectionRecord("s1", "", "不对", "", "不对", "codex-style-coding", 7)
        deduped = deduplicate_corrections([c1, c2])
        assert len(deduped) == 1  # Same session + same hint + same msg_id/10

    def test_keep_different_sessions(self):
        c1 = CorrectionRecord("s1", "", "不对", "", "不对", "codex", 5)
        c2 = CorrectionRecord("s2", "", "不对", "", "不对", "codex", 5)
        deduped = deduplicate_corrections([c1, c2])
        assert len(deduped) == 2


# ─── Patcher Tests ──────────────────────────────────────────────


class TestClassifyCorrection:
    def test_verification_skip(self):
        assert _classify_correction_type("你没跑验证就交了") == "verification_skip"
        assert _classify_correction_type("skip verification") == "verification_skip"

    def test_requirement_misread(self):
        assert _classify_correction_type("需求理解错了") == "requirement_misread"
        assert _classify_correction_type("方向错了") == "requirement_misread"

    def test_structure_miss(self):
        assert _classify_correction_type("你没scan代码结构") == "structure_miss"

    def test_error_not_handled(self):
        assert _classify_correction_type("你看报错了吗") == "error_not_handled"
        assert _classify_correction_type("traceback都不看") == "error_not_handled"

    def test_over_engineering(self):
        assert _classify_correction_type("不要乱加东西") == "over_engineering"
        assert _classify_correction_type("多余的功能") == "over_engineering"

    def test_general(self):
        assert _classify_correction_type("你好") == "general"


class TestCalcConfidence:
    def test_high_confidence_types(self):
        c = CorrectionRecord("s1", "", "你没跑验证", "sorry, fixing", "没跑验证", "", 0)
        assert _calc_confidence("verification_skip", "sorry, I'll fix it") > 0.7

    def test_lower_confidence(self):
        assert _calc_confidence("general", "") == 0.5


# ─── Config Tests ────────────────────────────────────────────────


class TestConfig:
    def test_default_config(self):
        config = load_config()
        assert "hermes_home" in config
        assert "correction_keywords" in config
        assert "evolution" in config

    def test_config_override(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "config.json"
            custom = {"hermes_home": "/custom/path", "evolution": {"max_corrections_per_run": 5}}
            save_config(custom, cfg_path)
            loaded = load_config(cfg_path)
            assert loaded["hermes_home"] == "/custom/path"
            assert loaded["evolution"]["max_corrections_per_run"] == 5
            # Default should still be present for unset keys
            assert "correction_keywords" in loaded

    def test_init_creates_config(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "mfi.json"
            cfg = init_config(cfg_path)
            assert cfg_path.exists()
            assert "hermes_home" in cfg

    def test_resolve_paths(self):
        config = {
            "hermes_home": "/test/hermes",
            "sessions_dir": "sessions",
            "skills_dir": "skills",
        }
        paths = resolve_paths(config)
        assert str(paths["sessions"]) == "/test/hermes/sessions"
        assert str(paths["skills"]) == "/test/hermes/skills"
