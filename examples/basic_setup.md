# Model-Free Intelligence Example: Basic Self-Evolution Setup

This guide shows how to set up a Model-Free Intelligence evolution loop
on any LLM agent platform that supports:
- Cron jobs (scheduled tasks)
- Session history search (by keywords)
- Skill management (read/modify skills)

## 1-Minute Setup

```bash
# Create the self-evolution cron job
hermes cron create \
  --name "self-evolve" \
  --schedule "0 4 * * *" \
  --prompt "你的自进化prompt" \
  --toolsets session_search,skills,file
```

## Prompt Template

```
翻最近3天的session日志，找用户纠正信号。
搜索关键词: "不对" "错了" "不是" "重来" "注意" "应该"
分析上下文 → 确定相关skill → 确认是重复模式 → skill_manage patch
无变更输出"[SILENT]"，有变更报告具体改动。
```

## Verification

```bash
# Check if it ran
hermes cron logs self-evolve

# Check for skill changes
ls -lt ~/.hermes/skills/*/SKILL.md | head -10
```

## Cost Tracking

| Metric | Value |
|--------|-------|
| Tokens per run | ~500-1000 |
| Daily cost (DeepSeek) | ~$0.0002 |
| Monthly cost | ~$0.006 |
| Skill improvements/month | ~10-30 |
