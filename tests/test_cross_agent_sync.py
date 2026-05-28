"""Tests for cross_agent_sync module."""

import tempfile

from src.cross_agent_sync import KnowledgePacket, SyncEngine


def test_packet_creation():
    pkt = KnowledgePacket(
        agent_id="max",
        skill_name="web-exploit",
        skill_content="# Web Exploit\nSteps...",
    )
    assert pkt.agent_id == "max"
    assert pkt.checksum  # auto-generated
    assert len(pkt.checksum) == 16


def test_packet_to_from_dict():
    pkt = KnowledgePacket(
        agent_id="tong",
        skill_name="blue-team",
        skill_content="# Blue Team\nSteps...",
        version=2,
        tags=["defense", "monitoring"],
    )
    d = pkt.to_dict()
    restored = KnowledgePacket.from_dict(d)
    assert restored.agent_id == "tong"
    assert restored.skill_name == "blue-team"
    assert restored.version == 2
    assert restored.checksum == pkt.checksum


def test_publish_and_pull():
    with tempfile.TemporaryDirectory() as d:
        engine = SyncEngine("max", d)
        pkt = KnowledgePacket("max", "test-skill", "content")
        checksum = engine.publish(pkt)

        # Pull should find the packet (clear seen to simulate another agent)
        engine._seen_checksums.clear()
        pulled = engine.pull_new()
        assert len(pulled) == 1
        assert pulled[0].checksum == checksum

        # Second pull should be empty (already seen)
        pulled2 = engine.pull_new()
        assert len(pulled2) == 0


def test_pull_with_agent_filter():
    with tempfile.TemporaryDirectory() as d:
        engine = SyncEngine("max", d)
        engine.publish(KnowledgePacket("max", "skill-a", "content"))
        engine.publish(KnowledgePacket("tong", "skill-b", "content"))

        # Reset seen to test filter
        engine._seen_checksums.clear()

        pulled = engine.pull_new(agent_filter="max")
        assert len(pulled) == 1
        assert pulled[0].agent_id == "max"


def test_merge_new_skill():
    with tempfile.TemporaryDirectory() as d:
        engine = SyncEngine("max", d)
        pkt = KnowledgePacket("tong", "new-skill", "# New Skill\ncontent")
        merged = engine.merge([pkt], {})
        assert "new-skill" in merged
        assert merged["new-skill"] == "# New Skill\ncontent"


def test_merge_higher_version_wins():
    with tempfile.TemporaryDirectory() as d:
        engine = SyncEngine("max", d)
        pkt = KnowledgePacket("tong", "skill-x", "# v2 content", version=2)
        local = {"skill-x": "# v1 content"}
        merged = engine.merge([pkt], local)
        assert "skill-x" in merged
        assert merged["skill-x"] == "# v2 content"


def test_diff_same():
    with tempfile.TemporaryDirectory() as d:
        engine = SyncEngine("max", d)
        local = {"a": "1", "b": "2"}
        remote = {"a": "1", "b": "2"}
        diff = engine.diff(local, remote)
        assert len(diff) == 0


def test_diff_different():
    with tempfile.TemporaryDirectory() as d:
        engine = SyncEngine("max", d)
        local = {"a": "1", "b": "2"}
        remote = {"a": "1", "b": "3"}
        diff = engine.diff(local, remote)
        assert "b" in diff
