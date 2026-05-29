<div align="center">

# 无模型智能 · Model-Free Intelligence

**Intelligence Without a Single Model / 没有模型也能产生智能**

让AI Agent的技能从每一次真实交互中自动进化 —— 跨会话、跨Agent、跨设备、跨用户，经验持续累积，技能群体进化。

[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)](pyproject.toml)

</div>

---

## 一句话

**智能的核心瓶颈不是模型大小，是系统架构。** 通过 skill 专家系统 + 会话进化循环，一个轻量模型驱动的 Agent 可以展现出远超其基础模型能力的智能行为。

这是这套方法论的 **Python 实现** —— `mfi` CLI 工具。

---

## 安装

```bash
pip install model-free-intelligence
```

或从源码安装：

```bash
git clone https://github.com/xtcon/model-free-intelligence
cd model-free-intelligence
pip install -e .
```

---

## 快速开始

### 1. 初始化

```bash
mfi init
```

生成默认配置 `~/.mfi/config.json`：

```json
{
  "hermes_home": "~/.hermes",
  "sessions_dir": "sessions",
  "skills_dir": "skills",
  "correction_keywords": ["不对", "错了", "不是", "重来", "注意", "wrong", "incorrect"],
  "evolution": {
    "max_corrections_per_run": 10,
    "min_confidence": 0.3,
    "dedup_window_hours": 24
  }
}
```

### 2. 查看状态

```bash
mfi status
```

显示 session 数量、skill 数量、进化运行次数、累计 patch 数。

### 3. 扫描纠正信号

```bash
mfi analyze --days 7
```

扫描最近 7 天的 session 日志，找用户纠正信号（"不对"、"错了" 等关键词），提取上下文。

### 4. 生成 patch 提案

```bash
mfi propose --days 7
```

基于纠正信号生成 skill patch 提案，包括目标 skill、目标段落、patch内容和置信度。

### 5. 运行进化循环

```bash
mfi evolve --days 7        # 自动应用高置信度patch
mfi evolve --days 7 --review  # 仅提案，不自动应用
```

---

## 完整流程

```
                           ┌──────────────────────┐
                           │   用户与Agent对话      │
                           │   （每次会话）          │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │   用户纠正信号检测      │
                           │  "不对" "错了" "不是"   │
                           └──────────┬───────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────┐
│                    mfi evolve (cron: 每天)                │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │  analyze      │───▶│  propose     │───▶│  apply     │  │
│  │  扫描session   │    │  生成patch    │    │  写回skill  │  │
│  └──────────────┘    └──────────────┘    └────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │   Skill 库自动进化      │
                           │  下次会话更强            │
                           └──────────────────────┘
```

---

## 架构

### 三层架构

| 层 | 职责 | 对应文件 |
|---|---|---|
| **专家系统层** (Skills) | 人类可读可编辑的 SKILL.md，封装领域方法论 | `~/.hermes/skills/**/SKILL.md` |
| **Agent 编排层** | 多Agent分工协作，各自的技能库独立进化 | Hermes Agent 多Agent系统 |
| **进化循环层** | session日志→分析→技能更新→下次更强 | `mfi evolve` |

### 包结构

```
mfi/
├── __init__.py      # 版本信息
├── cli.py           # CLI入口 (mfi命令)
├── config.py        # 配置管理
├── analyzer.py      # Session日志分析器
├── patcher.py       # Skill patch生成
├── evolution.py     # 进化循环编排
└── dashboard.py     # 状态看板
```

---

## 命令参考

| 命令 | 说明 |
|---|---|
| `mfi init` | 初始化配置 |
| `mfi status` | 显示进化状态 |
| `mfi analyze --days N` | 扫描最近N天session，找纠正信号 |
| `mfi propose --days N` | 生成patch提案 |
| `mfi evolve --days N` | 运行完整进化循环 |
| `mfi evolve --review` | 仅提案不自动应用 |

选项：
- `--config / -c` 指定配置文件路径
- `--verbose / -v` 详细输出
- `--days` 指定扫描天数（默认3天）

---

## 核心哲学

```
Intelligence is not about the size of a model, but the architecture of the system.
```

- **技能即数字肌肉记忆** — 每次纠正都是永久性的 skill 提升，不会随会话结束丢失
- **人回路置信** — 进化循环基于**真实的用户纠正**，不是合成数据，质量远高于自动自我改进
- **轻量可嵌入** — `mfi` 可以集成到任何 LLM Agent 平台，不绑定特定框架

---

## 与 Hermes Agent 集成

`mfi` 默认读取 Hermes Agent 的 session 和 skill 目录。切换到其他平台只需修改 `hermes_home` 配置：

```bash
mfi init --config /path/to/custom/config.json
# 然后编辑 config.json 中的路径
```

---

## License

MIT
