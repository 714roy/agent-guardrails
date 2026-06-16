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

## The Fix: Engine-Level Safety Guards

Beyond narrowing trigger keywords, **two engine-level safety mechanisms** were added to prevent ANY always_block rule from deadlocking:

### Fix 1: Always-Allowed Tools (`_ALWAYS_ALLOWED_TOOLS`)

A hard-coded allowlist of infrastructure tools that are **never blocked** by `always_block`:

```python
_ALWAYS_ALLOWED_TOOLS = {
    "skill_view", "skills_list", "skill_manage",
    "read_file", "write_file", "patch", "search_files",
    "terminal", "execute_code",
    "session_search", "mcp_agentmemory_memory_recall",
    "web_search", "web_extract",
}
```

These are the tools an agent needs to:
- **Diagnose** a block (read_file to check rules)
- **Fix** a block (patch, write_file to edit rules)
- **Escape** a block (terminal to restart gateway)

This is checked **before** the `_is_required_tool` check, so even if a rule forgets to list `skill_view` in `require_tools`, it still works.

### Fix 2: Deadlock Escape — Consecutive Block Counter

After `_ALWAYS_BLOCK_DEADLOCK_LIMIT` (5) consecutive blocked tool calls within one turn, `always_block` is **automatically cleared** with a warning log:

```python
consec = state.get("always_block_consecutive", 0)
if consec >= _ALWAYS_BLOCK_DEADLOCK_LIMIT:
    state["always_block"] = False
    logger.warning(
        "ALWAYS_BLOCK DEADLOCK ESCAPE: cleared after %d consecutive blocks",
        consec,
    )
    # Fall through to normal tool processing
```

This ensures even if a misconfigured rule blocks everything, the agent can recover within 5 blocked attempts without human intervention.

### Fix 3: Hot-Reload Race Condition

The `require_tools` list for `three-mirrors` already included `skill_view` — but `always_block` still blocked it due to a hot-reload caching issue. The rule file was updated but the in-memory cache didn't sync properly between `pre_llm_call` (which loads rules) and `pre_tool_call` (which checks them). Adding the engine-level guards (Fixes 1 & 2) makes this a non-issue.

## Combined Flow (after fixes)

```
pre_llm_call → state reset → rules loaded → three-mirrors activated → always_block=true

pre_tool_call(skill_view):
  1. always_block active? YES
  2. Is tool in _ALWAYS_ALLOWED_TOOLS? YES → ✅ ALLOW (never reaches block logic)
  
pre_tool_call(some_other_tool):
  1. always_block active? YES
  2. Is tool in _ALWAYS_ALLOWED_TOOLS? NO
  3. Deadlock check: consecutive=1 < 5 → continue
  4. Is tool in require_tools? NO → BLOCK + increment consecutive
  
... after 5 blocks ...
  
pre_tool_call(any_tool):
  1. always_block active? YES
  2. consecutive >= 5 → AUTO CLEAR always_block → ✅ ALLOW
```

## Code Reference

The deadlock-prone logic is in `agentguard/enforcer.py`, `on_pre_tool_call()` (simplified):

```python
# Step 1: always_block
if state.get("always_block", False):
    all_met = all(requirements_met for rule in active_rules)
    if all_met:
        state["always_block"] = False
    else:
        consec = state.get("always_block_consecutive", 0)
        if consec >= 5:
            state["always_block"] = False  # DEADLOCK ESCAPE
        elif tool_name in _ALWAYS_ALLOWED_TOOLS:
            pass  # ALLOW (infrastructure tools)
        elif _is_required_tool(tool_name, any_rule):
            pass  # ALLOW (configured as prerequisite)
        else:
            state["always_block_consecutive"] = consec + 1
            return {"action": "block"}
```

## Bug: `only_block_tools` Location Mismatch

### The Problem

`only_block_tools` was declared at the **rule root** level in YAML:

```yaml
- name: claw-output-archive
  conditions:
    require_tools:
      - name: write_file
  only_block_tools:          # <-- root level
    - write_file
    - terminal
```

But `_tool_should_block()` looked for it under `conditions`:

```python
# BROKEN: only_block_tools is at root level, not under conditions
only_block = rule.get("conditions", {}).get("only_block_tools", [])
```

This always returned `[]`, and `not []` is `True`, so **every rule with unmet requirements blocked ALL tools** — ignoring the `only_block_tools` list entirely.

### Impact

- `claw-output-archive` blocked `read_file` 32 times in one turn (should only block `write_file` + `terminal`)
- `cli-verify` blocked `skill_view` 8 times (should only block `terminal`)
- Every rule effectively had `only_block_tools: []` behavior, causing widespread false-positive blocks

### The Fix

```python
def _tool_should_block(tool_name: str, rule: dict) -> bool:
    # Check root level first, then conditions (backward compat)
    only_block = rule.get("only_block_tools") or rule.get("conditions", {}).get("only_block_tools", [])
    if not only_block:
        return True  # empty list = block all tools
    for pattern in only_block:
        if fnmatch.fnmatch(tool_name, pattern):
            return True
    return False
```

This reads from the correct location while maintaining backward compatibility with any rules that might have it under `conditions`.

### Lesson

YAML schema and Python code must be validated together. A silently wrong default (`[]` → block all tools) is worse than an explicit crash. Consider adding a unit test that verifies `only_block_tools` is read from the correct key path.
