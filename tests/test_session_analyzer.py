"""Tests for session_analyzer module."""

import json
import os
import tempfile

from src.session_analyzer import CorrectionSignal, analyze_session, extract_patterns, scan_logs


def test_correction_signal_creation():
    sig = CorrectionSignal(
        trigger_phrase="不对",
        context_before="agent said x",
        context_after="user said not x",
        domain_tags=["cron"],
    )
    assert sig.trigger_phrase == "不对"
    assert "cron" in sig.domain_tags


def test_scan_logs_empty_dir():
    with tempfile.TemporaryDirectory() as d:
        signals = scan_logs(d)
        assert isinstance(signals, list)
        assert len(signals) == 0


def test_scan_logs_finds_correction():
    with tempfile.TemporaryDirectory() as d:
        log = {
            "role": "assistant",
            "content": "I think we should use Docker here"
        }
        with open(os.path.join(d, "session_1.json"), "w") as f:
            json.dump(log, f)

        signals = scan_logs(d)
        # "不对" not in content, should not match any
        assert len(signals) == 0


def test_scan_logs_finds_chinese_correction():
    with tempfile.TemporaryDirectory() as d:
        log = {"role": "user", "content": "不对，我不是这个意思"}
        with open(os.path.join(d, "session_2.json"), "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False)

        signals = scan_logs(d)
        assert len(signals) > 0
        assert signals[0].trigger_phrase == "不对"


def test_extract_patterns():
    signals = [
        CorrectionSignal("不对", "ctx1", "ctx2", ["docker"]),
        CorrectionSignal("不是", "ctx3", "ctx4", ["cron"]),
    ]
    exps = extract_patterns(signals)
    assert len(exps) == 2
    assert exps[0].category == "correction"


def test_analyze_session_empty():
    with tempfile.TemporaryDirectory() as d:
        result = analyze_session(d)
        assert result["files_scanned"] == 0
        assert result["corrections_found"] == 0


def test_infer_tags():
    from src.session_analyzer import _infer_tags
    tags = _infer_tags("docker run nginx deployment")
    assert "docker" in tags
    assert "deployment" in tags


def test_infer_tags_cron():
    from src.session_analyzer import _infer_tags
    tags = _infer_tags("crontab schedule定时任务")
    assert "cron" in tags


def test_infer_tags_security():
    from src.session_analyzer import _infer_tags
    tags = _infer_tags("CVE-2026-12345 vulnerability exploit")
    assert "security" in tags
