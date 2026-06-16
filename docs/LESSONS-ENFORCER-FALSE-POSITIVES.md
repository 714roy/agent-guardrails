# Enforcer Rule Design: Lessons from False-Positive Deadlocks

**Date:** 2026-06-16
**Author:** Roy's agent (production Hermes deployment)

## Background

The AgentGuard enforcer runs as a Hermes plugin with three hooks:
- `pre_llm_call` — classifies user message, activates matching rules
- `pre_tool_call` — blocks tools that don't satisfy rule conditions
- `transform_llm_output` — applies regex transforms to LLM output

Rules are defined in YAML frontmatter of a markdown file (`agent-guardrails-rules.md`), hot-reloaded on file change.

## The Problem: False-Positive Tool Lockdown

Several rules had **overly broad trigger keywords** that matched everyday conversation, combined with **`always_block: true`** which blocks ALL tools until conditions are met — creating a deadlock where even the required tool (`date`, `am.py`) couldn't run.

### Rule 1: `three-mirrors` — Analysis Guard

**Before:**
```yaml
triggers:
  keywords: ["分析", "怎么看", "什么情况", "为什么", "怎么回事", "评估", "判断", "预测", "趋势", "理解", "解梦", "怎么看这个"]
always_block: true
only_block_tools: []
```

**Failure:** User casually said "怎么误拦了，什么情况" — `"什么情况"` matched → `always_block` locked all tools. Agent couldn't even read the rules file to fix it.

**Fix:** Trigger only on explicit intent:
```yaml
keywords: ["三镜", "三镜分析", "三镜角度", "用三镜"]
```

### Rule 2: `time-awareness` — Date Check Guard

**Before:**
```yaml
triggers:
  keywords: ["点", "点钟", "今天", "明天", "昨晚", "凌晨", "晚上", "早上", "中午", "下午", "现在"]
always_block: true
conditions:
  require_prior_tool:
    - name: terminal
      command_contains: ["date"]
  require_recent_seconds: 120
```

**Failure:** User asked "现在都好了吧" — `"现在"` matched → `always_block` blocked ALL tools including `date` itself. True deadlock: the required tool is also blocked.

**Fix:** Remove "现在" from triggers (too common in casual speech):
```yaml
keywords: ["点", "点钟", "今天", "明天", "昨晚", "凌晨", "晚上", "早上", "中午", "下午"]
```

### Rule 3: `session-start-recall` — Memory Check Guard

**Before:**
```yaml
keywords: ["新对话", "接着聊", "接着上次", "继续", "继续上次", "继续之前", ...]
```

**Failure:** User said "继续修" — bare `"继续"` matched (substring match), blocking `send_message`.

**Fix:** Remove the bare keyword, keep only compound phrases:
```yaml
keywords: ["新对话", "接着聊", "接着上次", "继续上次", "继续之前", ...]
```

### Rule 4: `multi-step-throttle` — Cascading Blocks

This rule has no trigger keywords (always active) and blocks after 3 consecutive tool calls without a response. During the deadlock, the agent was repeatedly blocked by different rules while trying to fix the first one, which incremented the consecutive-call counter and triggered this throttle too — a cascading multi-rule lock.

## Root Cause Analysis

| Cause | Impact |
|-------|--------|
| **Substring matching** (`kw.lower() in msg_lower`) | Single-character keywords like "现", "继" in larger words trigger accidentally |
| **`always_block` + empty `only_block_tools`** | Creates a total lockdown with no escape path |
| **`require_prior_tool` inside `always_block`** | Required tool is also blocked — true deadlock |
| **Cascading rules** | First block triggers more blocks (multi-step throttle, session recall) as agent tries to recover |
| **No graceful degradation** | No timeout, no bypass flag, no "user override" mechanism |

## Recommendations for Rule Design

1. **Prefer narrow trigger keywords over broad ones.** Test against casual conversation. `"三镜"` is better than `"分析"`. `"继续上次"` is better than `"继续"`.

2. **Never use `always_block: true` with `only_block_tools: []`.** This creates a total lockdown. At minimum, allow `read_file` and `terminal` to escape.

3. **Don't require a tool inside `always_block` that itself would be blocked.** `date` is blocked by the same rule that requires it.

4. **Consider a "deadlock timeout"** — if `always_block` has been active for >30 seconds with no progress, auto-clear and log a warning.

5. **Add per-rule bypass** — a special message like `"bypass: <rule_name>"` that the human can send to force-clear a stuck rule.

6. **Batch rule changes** — if the agent triggers rule A and B while trying to fix rule C, it hits the multi-step throttle. Consider a "repair mode" that temporarily suspends non-critical rules.

## Code Reference

The deadlock-prone logic is in `agentguard/enforcer.py`, `on_pre_tool_call()`:

```python
# Step 1: always_block — block non-required tools only until all prereqs met
if state.get("always_block", False):
    all_met = all(
        _all_requirements_met(rule_name, state.get("satisfied", {}))
        for rule_name, rule in active_rules.items()
    )
    if all_met:
        state["always_block"] = False
    else:
        is_required = False
        for r_name, r_rule in active_rules.items():
            if _is_required_tool(tool_name, r_rule):
                is_required = True
                break
        if not is_required:
            return {"action": "block", "message": "..."}
```

The `_is_required_tool` check only recognizes `conditions.require_tools`, **not** `conditions.require_prior_tool`. So `date` (specified in `require_prior_tool`) is never recognized as "required" and always blocked.

This is a bug independent of the keyword breadth issue.
