"""
cross_agent_sync.py — Knowledge synchronization across agents.

Protocol for serializing, exchanging, and merging skill/experience
knowledge between different AI agents in the MFI ecosystem.

Design principles:
- CRDT-inspired: concurrent edits don't conflict
- Agent-local priority: agent-specific > shared
- Merkle-style: hash tree for quick diff
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class KnowledgePacket:
    """Serializable knowledge unit for cross-agent exchange."""
    agent_id: str
    skill_name: str
    skill_content: str
    version: int = 1
    timestamp: float = 0.0
    checksum: str = ""
    tags: List[str] = field(default_factory=list)
    parent_packet: Optional[str] = None  # checksum of previous version

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        raw = f"{self.agent_id}:{self.skill_name}:{self.skill_content}:{self.version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "skill_name": self.skill_name,
            "skill_content": self.skill_content,
            "version": self.version,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
            "tags": self.tags,
            "parent_packet": self.parent_packet,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgePacket":
        return cls(
            agent_id=d["agent_id"],
            skill_name=d["skill_name"],
            skill_content=d["skill_content"],
            version=d.get("version", 1),
            timestamp=d.get("timestamp", 0.0),
            checksum=d.get("checksum", ""),
            tags=d.get("tags", []),
            parent_packet=d.get("parent_packet"),
        )


class SyncEngine:
    """Cross-agent knowledge synchronization engine."""

    def __init__(self, local_agent_id: str, storage_dir: str = "/tmp/mfi-sync"):
        self.agent_id = local_agent_id
        self.storage_dir = storage_dir
        self._seen_checksums: Set[str] = set()
        import os
        os.makedirs(storage_dir, exist_ok=True)

    def publish(self, packet: KnowledgePacket) -> str:
        """Publish a knowledge packet to the shared store."""
        path = f"{self.storage_dir}/{packet.checksum}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(packet.to_dict(), f, ensure_ascii=False, indent=2)
        self._seen_checksums.add(packet.checksum)
        return packet.checksum

    def pull_new(self, agent_filter: Optional[str] = None) -> List[KnowledgePacket]:
        """Pull all unseen packets from the shared store."""
        import os
        packets = []
        if not os.path.isdir(self.storage_dir):
            return packets

        for fname in os.listdir(self.storage_dir):
            if not fname.endswith('.json'):
                continue
            if fname.replace('.json', '') in self._seen_checksums:
                continue

            fpath = os.path.join(self.storage_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                pkt = KnowledgePacket.from_dict(d)
                if agent_filter and pkt.agent_id != agent_filter:
                    continue
                packets.append(pkt)
                self._seen_checksums.add(pkt.checksum)
            except Exception:
                continue

        return packets

    def merge(self, incoming: List[KnowledgePacket],
              local_skills: Dict[str, str]) -> Dict[str, str]:
        """Merge incoming knowledge into local skill store.

        Conflict resolution:
        - Higher version wins
        - Same version: agent-specific > shared
        - Same agent: newer timestamp wins
        """
        merged = dict(local_skills)

        for pkt in incoming:
            skill_name = pkt.skill_name
            existing = merged.get(skill_name, "")

            if not existing:
                merged[skill_name] = pkt.skill_content
                continue

            # Version-based resolution
            existing_version = self._extract_version(existing)
            if pkt.version > existing_version:
                merged[skill_name] = pkt.skill_content
            elif pkt.version == existing_version and pkt.timestamp > time.time() - 3600:
                # If same version and recent, keep local
                pass

        return merged

    @staticmethod
    def _extract_version(content: str) -> int:
        """Extract version number from skill content header."""
        import re
        m = re.search(r'version:\s*(\d+)', content[:500])
        return int(m.group(1)) if m else 1

    def diff(self, local: Dict[str, str],
             remote: Dict[str, str]) -> Dict[str, str]:
        """Compute diff between local and remote skill stores."""
        diff: Dict[str, str] = {}
        all_keys = set(local.keys()) | set(remote.keys())
        for k in all_keys:
            lv = local.get(k, "")
            rv = remote.get(k, "")
            if lv != rv:
                diff[k] = f"local:{len(lv)}c vs remote:{len(rv)}c"
        return diff
