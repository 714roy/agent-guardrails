"""
Hermes Agent plugin — AgentGuard enforcer integration.

This is a thin bridge that connects the AgentGuard rule engine
to Hermes Agent's hook system.

Usage:
  1. Copy this directory to ~/.hermes/plugins/agent-guardrails/
  2. Ensure agentguard is installed: pip install https://github.com/714roy/agent-guardrails/releases/download/v1.1.0/agentguard-1.1.0-py3-none-any.whl
  3. Restart Hermes Gateway

  Or use the hermes-plugin/install.sh script for automated setup.
"""

import logging

from agentguard import (
    on_pre_llm_call,
    on_pre_tool_call,
    on_transform_output,
    ENFORCER_DISABLE,
)

logger = logging.getLogger("agentguard-hermes")


def register(ctx):
    """Register all three hooks with Hermes Agent."""
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("transform_llm_output", on_transform_output)

    from agentguard.enforcer import load_rules
    rule_count = len(load_rules())
    logger.info(
        "AgentGuard loaded: %d rules, disable with AGENTGUARD_DISABLE=1",
        rule_count,
    )
