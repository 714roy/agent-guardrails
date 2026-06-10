"""
AgentGuard — LLM Agent behavior rule engine.

Core engine that powers the Hermes Agent enforcer plugin.
Can also be used standalone for testing or custom integrations.

Architecture:
  pre_llm_call    → one per turn, classify user topic, activate matching rules
  pre_tool_call   → before each tool call, check active rule conditions, block if unmet
  transform_output → after LLM generates reply, apply regex transforms

Rules are defined in YAML (see config/enforcer-rules.md.example).
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level state — shared across hook calls
# ---------------------------------------------------------------------------

# Default path for the rules file (overridable via AGENTGUARD_RULES env var)
_DEFAULT_RULES_PATH = os.path.join(
    os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")),
    "workspace",
    "agent-guardrails-rules.md",
)
_RULES_PATH = os.environ.get("AGENTGUARD_RULES", _DEFAULT_RULES_PATH)

# _turn_state[session_id] = {
#     "user_message": str,
#     "turn_active": bool,
#     "active_rules": dict,       # {rule_name: rule_dict}
#     "satisfied": dict,          # {rule_name: {tool_pattern: bool}}
#     "blocked_tools": dict,      # {rule_name: int}
#     "tool_call_count": int,
#     "always_block": bool,
# }
_turn_state: dict[str, dict] = {}
_turn_counters: dict[str, int] = {}

# Rule cache — hot-reloads on file change, no restart needed
_rules_cache_mtime: float = 0
_rules_cache: list[dict] = []

# Routing table cache
_routing_table_cache: str = ""
_routing_table_mtime: float = 0

# Environment bypass switch
ENFORCER_DISABLE = os.environ.get("AGENTGUARD_DISABLE", "0") == "1"


# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------

def _read_frontmatter(path: str) -> dict:
    """Read YAML frontmatter from a Markdown file (between --- delimiters)."""
    if not os.path.exists(path):
        logger.warning("Rules file not found: %s", path)
        return {}
    try:
        with open(path) as f:
            content = f.read()
        parts = re.split(r"^---\s*$", content, maxsplit=2, flags=re.MULTILINE)
        if len(parts) < 3:
            logger.warning("No YAML frontmatter found in %s", path)
            return {}
        return yaml.safe_load(parts[1]) or {}
    except Exception as exc:
        logger.error("Failed to parse frontmatter: %s", exc)
        return {}


def load_rules(path: str | None = None) -> list[dict]:
    """Load rules from file, with hot-reload on mtime change.

    Rules are sorted by priority descending (higher = evaluated first).
    Rules without priority default to 0.
    """
    global _rules_cache_mtime, _rules_cache
    path = path or _RULES_PATH
    try:
        new_mtime = os.path.getmtime(path)
        if new_mtime != _rules_cache_mtime:
            data = _read_frontmatter(path)
            _rules_cache = data.get("rules", []) if isinstance(data, dict) else []
            _rules_cache.sort(key=lambda r: -r.get("priority", 0))
            _rules_cache_mtime = new_mtime
            logger.info(
                "Rules reloaded (%d rules, sorted by priority) from %s",
                len(_rules_cache), path,
            )
        return _rules_cache
    except Exception as exc:
        logger.error("Failed to load rules: %s", exc)
        return _rules_cache or []


def load_routing_table(path: str | None = None) -> str:
    """Load routing table from the same rules file."""
    global _routing_table_cache, _routing_table_mtime
    path = path or _RULES_PATH
    try:
        new_mtime = os.path.getmtime(path)
        if new_mtime != _routing_table_mtime:
            data = _read_frontmatter(path)
            _routing_table_cache = (
                data.get("routing_table", "") if isinstance(data, dict) else ""
            )
            _routing_table_mtime = new_mtime
            logger.info("Routing table reloaded from %s", path)
        return _routing_table_cache
    except Exception as exc:
        logger.warning("Failed to load routing table: %s", exc)
        return _routing_table_cache or ""


# ---------------------------------------------------------------------------
# Tool matching utilities
# ---------------------------------------------------------------------------

def _matches_tool(tool_name: str, pattern: str) -> bool:
    """Check if tool name matches a glob pattern (supports * wildcard)."""
    return fnmatch.fnmatch(tool_name, pattern)


def _args_contain(args: dict, keywords: list[str]) -> bool:
    """Check if any value in args dict contains any of the keywords."""
    for key, value in args.items():
        if isinstance(value, str):
            for kw in keywords:
                if kw.lower() in value.lower():
                    return True
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    for kw in keywords:
                        if kw.lower() in item.lower():
                            return True
    return False


def _message_matches(message: str, rule: dict) -> bool:
    """Check if user message matches the rule's keyword triggers."""
    triggers = rule.get("triggers", {})
    keywords = triggers.get("keywords", [])
    if not keywords:
        return False
    mode = triggers.get("mode", "any")
    msg_lower = message.lower()
    if mode == "all":
        return all(kw.lower() in msg_lower for kw in keywords)
    return any(kw.lower() in msg_lower for kw in keywords)


def _requirement_met(
    rule_name: str, tool_name: str, args: dict, satisfied: dict
) -> bool:
    """Check if this tool call satisfies one of the rule's require_tools entries."""
    rule = satisfied.get(rule_name, {})
    for req_idx, req_tool in enumerate(rule.get("_defs", [])):
        key = f"_req_{req_idx}"
        if rule.get(key, False):
            continue  # already satisfied
        pattern = req_tool.get("name", "")
        if not _matches_tool(tool_name, pattern):
            continue
        args_kw = req_tool.get("args_contains", [])
        if args_kw and not _args_contain(args, args_kw):
            continue
        # Match! Mark as satisfied
        rule[key] = True
        logger.debug(
            "Rule '%s' req '%s' satisfied by tool_call %s args=%s",
            rule_name, pattern, tool_name, args,
        )
        return True
    return False


def _all_requirements_met(rule_name: str, satisfied: dict) -> bool:
    """Check if all require_tools for a rule are satisfied."""
    rule = satisfied.get(rule_name, {})
    defs = rule.get("_defs", [])
    if not defs:
        return True
    return all(rule.get(f"_req_{i}", False) for i in range(len(defs)))


def _tool_should_block(tool_name: str, rule: dict) -> bool:
    """Check if a tool should be blocked by this rule."""
    only_block = rule.get("conditions", {}).get("only_block_tools", [])
    if not only_block:
        return True  # empty list = block all tools
    for pattern in only_block:
        if _matches_tool(tool_name, pattern):
            return True
    return False


def _is_required_tool(tool_name: str, rule: dict) -> bool:
    """Check if a tool is a required prerequisite (should NOT be blocked)."""
    req_tools = rule.get("conditions", {}).get("require_tools", [])
    for req in req_tools:
        pattern = req.get("name", "")
        if not pattern:
            continue
        if _matches_tool(tool_name, pattern):
            return True
    return False


def _apply_transforms(text: str, rules: list[dict]) -> str:
    """Apply all transform configs from rules to the text."""
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        transform = rule.get("transform")
        if not transform:
            continue
        mode = transform.get("mode")
        if mode == "regex_replace":
            mappings = transform.get("mappings", [])
            for mapping in mappings:
                pattern = mapping.get("pattern", "")
                replacement = mapping.get("replacement", "")
                if pattern:
                    text = re.sub(pattern, replacement, text)
    return text


# ---------------------------------------------------------------------------
# Hook callbacks (for Hermes Agent integration)
# ---------------------------------------------------------------------------

def on_pre_llm_call(
    session_id: str,
    user_message: str,
    is_first_turn: bool = False,
    **kwargs,
) -> dict | None:
    """
    pre_llm_call hook: one per turn.

    Classifies user message, activates matching rules, resets turn state.
    Does NOT inject context (pure observation/state management).
    Returns routing table on first turn, turn warnings as needed.
    """
    if ENFORCER_DISABLE:
        return None

    # Reset turn state
    state = {
        "user_message": user_message,
        "turn_active": True,
        "active_rules": {},
        "satisfied": {},
        "blocked_tools": {},
        "tool_call_count": 0,
        "always_block": False,
    }
    _turn_state[session_id] = state

    # Persistent turn counter
    turn_count = _turn_counters.get(session_id, 0) + 1
    _turn_counters[session_id] = turn_count
    state["turn_count"] = turn_count

    rules = load_rules()
    if not rules:
        return None

    matched_any = False
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        rule_name = rule.get("name", "unknown")
        triggers = rule.get("triggers", {})
        keywords = triggers.get("keywords", [])

        if not keywords:
            # No trigger keywords = always active (e.g. multi-step-throttle)
            state["active_rules"][rule_name] = rule
            req_tools = rule.get("conditions", {}).get("require_tools", [])
            state["satisfied"][rule_name] = {"_defs": req_tools}
            state["blocked_tools"][rule_name] = 0
            logger.info(
                "Always-active rule '%s' registered for session %s",
                rule_name, session_id,
            )
            continue

        if _message_matches(user_message, rule):
            matched_any = True
            state["active_rules"][rule_name] = rule
            req_tools = rule.get("conditions", {}).get("require_tools", [])
            state["satisfied"][rule_name] = {"_defs": req_tools}
            state["blocked_tools"][rule_name] = 0
            logger.info(
                "Rule '%s' activated for session %s (msg: %.60s)",
                rule_name, session_id, user_message,
            )

            if rule.get("always_block", False):
                state["always_block"] = True
                logger.info(
                    "ALWAYS_BLOCK activated by rule '%s' for session %s",
                    rule_name, session_id,
                )

    if not matched_any:
        logger.debug("No rules activated for session %s", session_id)

    # Turn warnings (track_turns rules)
    if not is_first_turn:
        for rule in rules:
            if not rule.get("enabled", True):
                continue
            track = rule.get("track_turns")
            if track and isinstance(track, dict):
                warn_at = track.get("warn_at", [])
                if turn_count in warn_at:
                    msg = track.get("message", "⚠️ Conversation at {turns} turns")
                    logger.info(
                        "TURN_WARN: session=%s turn=%d", session_id, turn_count,
                    )
                    return {"context": msg.replace("{turns}", str(turn_count))}

    # Inject routing table on first turn
    if is_first_turn:
        routing = load_routing_table()
        if routing:
            logger.info("Injecting routing table for new session %s", session_id)
            return {"context": routing}

    return None  # Don't inject context


def on_pre_tool_call(
    tool_name: str,
    args: dict | None = None,
    task_id: str = "",
    **kwargs,
) -> dict | None:
    """
    pre_tool_call hook: before each tool call.

    Checks active rules from current turn:
    1. If this call satisfies a rule's require_tools → mark satisfied, allow
    2. If all requirements are met → allow
    3. If requirements not met and tool should be blocked → BLOCK
    """
    if ENFORCER_DISABLE:
        return None

    session_id = kwargs.get("session_id", kwargs.get("session", task_id))
    if not session_id:
        return None

    state = _turn_state.get(session_id)
    if not state or not state.get("turn_active"):
        return None

    active_rules = state.get("active_rules", {})
    if not active_rules:
        return None

    args = args or {}
    satisfied = state.get("satisfied", {})
    blocked = state.get("blocked_tools", {})

    # Update tool call count
    state["tool_call_count"] = state.get("tool_call_count", 0) + 1
    tool_count = state["tool_call_count"]

    # Step 1: always_block — block non-required tools only until all prereqs met
    if state.get("always_block", False):
        # If ALL active rules' requirements are met, clear always_block
        all_met = all(
            _all_requirements_met(rule_name, state.get("satisfied", {}))
            for rule_name, rule in active_rules.items()
        )
        if all_met:
            state["always_block"] = False
            logger.info("ALWAYS_BLOCK cleared: all requirements met")
        else:
            # Check if this tool is required by any active rule (don't block required tools)
            is_required = False
            for r_name, r_rule in active_rules.items():
                if _is_required_tool(tool_name, r_rule):
                    is_required = True
                    break
            if not is_required:
                state["blocked_tools"] = blocked
                logger.info(
                    "ALWAYS_BLOCK: blocked tool=%s for session=%s",
                    tool_name, session_id,
                )
                return {
                    "action": "block",
                    "message": "⛔ Tool blocked: prerequisites not met. Call required tools first.",
                }

    # Step 2: max_consecutive_calls (multi-step throttle)
    for rule_name, rule in active_rules.items():
        max_calls = rule.get("max_consecutive_calls", 0)
        if max_calls > 0 and tool_count > max_calls:
            state["blocked_tools"] = blocked
            msg = rule.get(
                "block_message",
                f"⛔ Multi-step throttle: over {max_calls} tool calls. Report progress first.",
            )
            logger.info(
                "THROTTLE: session=%s tool=%s count=%d limit=%d",
                session_id, tool_name, tool_count, max_calls,
            )
            return {"action": "block", "message": msg}

    # Step 3: check if this call satisfies any rule's require_tools
    for rule_name in list(active_rules.keys()):
        if _requirement_met(rule_name, tool_name, args, satisfied):
            logger.debug(
                "Tool %s satisfied a requirement for rule '%s'",
                tool_name, rule_name,
            )

    # Step 4: check if any rule needs to block this call
    for rule_name, rule in active_rules.items():
        if _all_requirements_met(rule_name, satisfied):
            continue  # All requirements met, don't block

        if not _tool_should_block(tool_name, rule):
            continue  # This tool not in block list

        if _is_required_tool(tool_name, rule):
            continue  # Required tools can't be blocked

        # Needs blocking
        blocked[rule_name] = blocked.get(rule_name, 0) + 1
        state["blocked_tools"] = blocked
        msg = rule.get("block_message", f"⛔ Rule '{rule_name}' prerequisites not met")
        logger.info(
            "BLOCKED: session=%s rule=%s tool=%s (blocked x%d this turn)",
            session_id, rule_name, tool_name, blocked[rule_name],
        )
        return {"action": "block", "message": msg}

    return None  # Allow


def on_transform_output(
    response_text: str = "",
    session_id: str = "",
    **kwargs,
) -> str | None:
    """
    transform_llm_output hook: after LLM generates response, before output.

    Reads transform configs from rules and applies regex replacements.
    Currently supports: regex_replace mode.
    """
    if not response_text:
        return None

    rules = load_rules()
    if not rules:
        return None

    has_transform = any(
        r.get("transform") for r in rules if r.get("enabled", True)
    )
    if not has_transform:
        return None

    modified = _apply_transforms(response_text, rules)
    if modified != response_text:
        logger.info(
            "TRANSFORM: session=%s applied transforms", session_id,
        )
    return modified
