<div align="center">

# 无模型智能 · Model-Free Intelligence

**Intelligence Without a Single Model / 没有模型也能产生智能**

让AI Agent的技能从每一次真实交互中自动进化 —— 跨会话、跨Agent、跨设备、跨用户，经验持续累积，技能群体进化。

*Let AI agent skills evolve from every real interaction — across sessions, agents, devices, and users. Experience compounds. Skills keep growing.*

[![Paper](https://img.shields.io/badge/Paper-arXiv-red?style=flat-square)](https://arxiv.org/abs/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Philosophy-3.10%2B-blue?style=flat-square)](.)

</div>

---

## 摘要 · Abstract

**中文**

主流AI Agent框架都假设「更大的模型 = 更强的智能」。本文提出一个相反的论点：**智能的核心瓶颈不是模型大小，而是系统架构**。通过专家系统组合、工具编排、技能循环进化，一个轻量LLM驱动的Agent可以展现出远超其基础模型能力的智能行为。

我们称这种方法为**无模型智能（Model-Free Intelligence）**——不依赖单一模型的参数规模，而是通过以下三层架构实现持续进化：

1. **专家系统层** — 人类可读、可编辑的skill markdown，封装领域方法论
2. **Agent编排层** — 多Agent分工协作，各自的技能库独立进化
3. **进化循环层** — session日志→分析→技能更新→下次更强，每日自动运行

**English**

Most AI agent frameworks assume "bigger model = stronger intelligence." This paper argues the opposite: **the bottleneck of intelligence is not model size, but system architecture.** Through expert system composition, tool orchestration, and cyclic skill evolution, a lightweight LLM-driven agent can exhibit intelligent behavior far beyond its base model's capability.

We call this approach **Model-Free Intelligence** — intelligence that does not depend on a single model's parameter count, but evolves through a three-layer architecture:

1. **Expert System Layer** — Human-readable, editable skill markdown encapsulating domain methodologies
2. **Agent Orchestration Layer** — Multiple specialized agents with independently evolving skill libraries
3. **Evolution Loop Layer** — Session logs → analysis → skill update → stronger tomorrow, running daily on cron

---

## 核心哲学 · Core Philosophy

```
"没有真正的人工智能诞生，所谓的人工智能，充其量也只是伪人工智能。"
"真正AI需要四个核心：语言识别、图形识别、逻辑思考、自然语言理解。"
                               — 小说《黑客》，2006
```

This insight predates modern LLMs by nearly two decades. The thesis: **you don't need a true AGI to build an intelligent system.** What you need is:

| 要素 Element | 现实对应 Real-world Counterpart |
|---|---|
| 语言识别 Speech Recognition | Voice-to-text APIs (whisper, etc.) |
| 图形识别 Visual Recognition | Vision-language models (MiniCPM, GPT-4V) |
| 逻辑思考 Logical Reasoning | LLM + Tool Use + RAG |
| 自然语言理解 NLU | Instruction-tuned LLM |
| **自进化 Self-Evolution** | **Session → Skill pipeline (this paper)** |

The key insight: combine these elements through an **expert system architecture**, and the emergent behavior surpasses what any single model can achieve.

**This is not a framework. It is a methodology.** You can implement it on top of any LLM agent platform.

---

## 架构 · Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Model-Free Intelligence                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────────────────────────┐               │
│  │        Agent Orchestration Layer           │              │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │              │
│  │  │ Agent A  │ │ Agent B  │ │ Agent C  │  │              │
│  │  │ (Domain) │ │ (Domain) │ │ (Domain) │  │              │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘  │              │
│  │       │            │            │         │              │
│  └───────┼────────────┼────────────┼─────────┘              │
│          │            │            │                         │
│  ┌───────┼────────────┼────────────┼─────────────────┐      │
│  │       │     Skill Library (Expert Systems)        │      │
│  │  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐            │      │
│  │  │skill A  │ │skill B  │ │skill C  │   ...       │      │
│  │  │SKILL.md │ │SKILL.md │ │SKILL.md │             │      │
│  │  └─────────┘ └─────────┘ └─────────┘            │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │           Evolution Loop (cron: 04:00)           │       │
│  │                                                   │       │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    │       │
│  │  │ Session  │───▶│ Analyze  │───▶│  Patch   │    │       │
│  │  │   Logs   │    │ Patterns │    │  Skills  │    │       │
│  │  └──────────┘    └──────────┘    └──────────┘    │       │
│  │                                                   │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Three Layers Explained

#### 1. Expert System Layer (Skills)

Skills are **markdown files** — human-readable, human-editable, agent-executable. Each skill encapsulates:

- **Trigger conditions**: When to load this skill
- **Step-by-step procedures**: Numbered execution steps with exact commands
- **Pitfalls**: Known failure modes and how to avoid them
- **Verification steps**: How to confirm the task was done correctly

```markdown
# 示例: tool-security-audit

## Trigger
Before installing any new tool or package.

## Steps
1. Check SHA256 checksum
2. Scan with clamscan
3. Audit dependency tree
4. Verify maintainer background
5. Install
6. Smoke test: `which → --version → actual usage`

## Pitfalls
- npm packages with lifecycle scripts (postinstall) = high risk
- Single-maintainer repos with temp email addresses
```

A library of 20-30 such skills is enough to cover 90% of recurring tasks for a specialized agent.

#### 2. Agent Orchestration Layer

Multiple agents with **isolated skill libraries** that evolve independently:

| Agent | Domain | Example Skills |
|---|---|---|
| Agent A (Security) | Vuln research, intel | tool-security-audit, c2-framework, opsec-checklist |
| Agent B (Dev) | Tool building, automation | self-built-toolchain, systematic-debugging, github-repo-management |
| Agent C (Offense) | Exploit dev, fuzzing | exploit-dev-workflow, weapon-arsenal, purple-team-exercise |

Skills are shared through a common format (SKILL.md), not through framework code.

#### 3. Evolution Loop

The core innovation — a daily cron job that:

1. **Scans session logs** for correction signals ("不对", "错了", "不是", "注意")
2. **Analyzes context** to determine if a skill gap exists
3. **Patches the relevant skill** directly via `skill_manage patch`

```python
# Pseudocode — the evolution loop
def self_evolve():
    corrections = session_search(keywords=["不对", "错了", "不是", "注意"])
    for c in corrections:
        skill = identify_relevant_skill(c.context, c.agent_role)
        if has_recurring_pattern(skill, c):
            skill_manage_patch(skill, generate_patch(c))
```

This turns every user correction into a permanent skill improvement — no experience is ever lost between sessions.

---

## Why This Works

### The Illusion of Scale

The AI industry's dominant narrative: **more parameters = more intelligence.** This is partially true but misses the point. A 671B-parameter model that forgets your preferences between sessions is less useful than a 7B model with a well-maintained skill library.

### Skills as Digital Muscle Memory

Every time an agent makes a mistake and gets corrected:
- **Without evolution loop**: The correction is lost when the session ends
- **With evolution loop**: The correction is permanently embedded in the skill

After 100 corrections, the skill library represents 100 lessons that never need to be taught again.

### Human-in-the-Loop Confidence

Unlike fully automated self-improvement systems (which tend to hallucinate "improvements" that actually degrade performance), the evolution loop operates on **real user corrections** — high-quality, high-density training signals that no synthetic data can match.

---

## Self-Evolution Cron: The Implementation

This is the minimal viable implementation — a single cron job that runs daily:

```bash
# Schedule: 0 4 * * *
# Tools: session_search, skills, file

# Prompt (what the agent receives at 04:00):
"""
翻最近3天的session日志，找用户纠正信号。
搜索: "不对" "错了" "不是" "重来" "注意" "应该"
分析上下文 → 确定相关skill → 确认是重复模式 → skill_manage patch
无变更输出"无变更"，有变更报告具体改动。
"""
```

**Cost**: ~500-1000 tokens per run (≈ $0.0002/day at DeepSeek pricing).  
**Zero infrastructure**: No proxy, no daemon, no database, no new dependencies.  
**Zero deployment**: Create once with `hermes cron create`, runs forever.

---

## Comparison with Existing Approaches

| Approach | Pros | Cons |
|---|---|---|
| **SkillClaw** (AMAP-ML) | Full auto-evolution, multi-user | Proxy layer, daemon, OSS/S3 dependency |
| **AutoGPT** | Autonomous task execution | No skill persistence, session isolation |
| **LangChain** | Rich tool ecosystem | Framework lock-in, no evolution loop |
| **Model-Free Intelligence** (this) | Zero infra, minimal cost, human-verifiable | Requires manual review cadence |

SkillClaw is closest in concept, but adds an entire proxy + evolve server infrastructure. Our approach: **one cron job, zero new code.**

---

## Getting Started

### Prerequisites
- Any LLM agent platform that supports cron jobs, session search, and skill management

### Setup (1 minute)

```bash
# Create the self-evolution cron
# (adapt the command to your platform)
cron create --schedule "0 4 * * *" \
            --prompt "Your self-evolution prompt here" \
            --enabled-toolsets session_search,skills,file
```

### Usage Pattern
1. Use your agent normally
2. When you see a mistake, just correct it ("不对", "不是这样", "注意")
3. The evolution loop handles the rest
4. Check your skill library weekly to review accumulated improvements

---

## Results

Over a 3-day trial period with a specialized security research agent:

| Metric | Before | After |
|---|---|---|
| Skills | 26 hand-written | 26+ auto-patched |
| Repeat corrections | 3-4/day | 0/day (after patch) |
| Session-search queries | Manual | Automated at 04:00 |
| Infrastructure | 35,000 lines (Izual) | 1 cron prompt |

---

## License

MIT — do what you want, just give credit.

## Citation

```bibtex
@misc{model-free-intelligence,
  author = {Zhu Demu},
  title = {Model-Free Intelligence: Collective Skill Evolution for AI Agents},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/xtcon/model-free-intelligence}
}
```

---

*"没有模型也能产生智能" — 小说《黑客》，2006*
