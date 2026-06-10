"""
AgentGuard — LLM Agent behavior rule engine.

A pip-installable package that provides the core enforcer engine.
See hermes-plugin/ for the Hermes Agent plugin integration.
"""

from .enforcer import (
    load_rules,
    load_routing_table,
    on_pre_llm_call,
    on_pre_tool_call,
    on_transform_output,
    ENFORCER_DISABLE,
)

__all__ = [
    "load_rules",
    "load_routing_table",
    "on_pre_llm_call",
    "on_pre_tool_call",
    "on_transform_output",
    "ENFORCER_DISABLE",
]
