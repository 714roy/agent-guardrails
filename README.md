# AgentGuard

> **Tool-call level behavior governance for LLM agents.**
> Built for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

AgentGuard enforces behavior at the **tool-call layer** — not at the prompt/output
layer like traditional guardrail solutions. When your agent tries to call a tool,
AgentGuard checks: *Does this user message activate any rules? Are the prerequisites
met?* If not, the tool call is blocked until requirements are satisfied.

It works as a **Hermes Agent plugin** with three hooks:
`pre_llm_call`, `pre_tool_call`, and `transform_llm_output`.

---

## Quick Start (Hermes Agent)

```bash
# 1. Install the engine
pip install agentguard

# 2. Link the Hermes plugin
mkdir -p ~/.hermes/plugins/hermes-enforcer
cp hermes-plugin/* ~/.hermes/plugins/hermes-enforcer/

# 3. Set up rules
cp config/enforcer-rules.yaml.example ~/.hermes/workspace/hermes-enforcer-rules.md

# 4. Enable in Hermes config (~/.hermes/config.yaml)
# plugins:
#   enabled:
#     - hermes-enforcer

# 5. Restart
systemctl --user restart hermes-gateway
```

**Full integration guide**: [docs/HERMES-INTEGRATION.md](docs/HERMES-INTEGRATION.md)

---

## How It Works

```
User sends message
    │
    ▼
pre_llm_call hook ── Classifies message, activates matching rules
    │                   └─ Rule state + tracking initialized
    ▼
Agent calls a tool
    │
    ▼
pre_tool_call hook ── Checks active rules:
    │                   ① Tool satisfies a rule's prerequisite? → Mark done, allow
    │                   ② All prerequisites met? → Allow
    │                   ③ Prerequisites unmet, tool in block list? → 🚫 BLOCK
    ▼
Allow / Block
```

### Rule Types

| Type | Description |
|:-----|:------------|
| **`always_block`** | Hard block: agent cannot proceed without meeting conditions |
| **`require_tools`** | Agent MUST call specific tools with specific args first |
| **`only_block_tools`** | Block specific tools when triggered (empty = block all) |
| **`transform`** | Regex-based output transformation (emoji → kaomoji, etc.) |
| **`track_turns`** | Inject context warnings after N turns |

### Example Rule

```yaml
rules:
  - name: sensitive-command
    enabled: true
    priority: 20
    triggers:
      keywords: ["rm", "shutdown", "drop table"]
    conditions:
      require_tools:
        - name: terminal
          args_contains: ["--dry-run"]
    block_message: "Sensitive commands require --dry-run verification first."
```

---

## Project Structure

```
agent-guardrails/
├── agentguard/                   # pip-installable engine package
│   ├── __init__.py               # Package entry point
│   └── enforcer.py               # Core rule engine (~500 lines)
├── hermes-plugin/                # Hermes Agent plugin bridge
│   ├── __init__.py               # Thin bridge with register(ctx)
│   └── plugin.yaml               # Plugin manifest
├── config/
│   ├── enforcer-rules.yaml.example   # Example rule definitions
│   └── routing-table.yaml.example    # Example domain routing
├── docs/
│   └── HERMES-INTEGRATION.md     # Full Hermes setup guide
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## Comparison

| Solution | Layer | Scope | Mechanism |
|:---------|:------|:------|:----------|
| Guardrails AI | Output | Response structure | Prompt templates + validators |
| LlamaGuard | Input/Output | Content safety | Classification model |
| **AgentGuard** | **Tool-call** | **Agent behavior** | **Rule engine + hooks** |

---

## Requirements

- Python 3.10+
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) (for plugin mode)
- PyYAML (for rule parsing)

## License

MIT

---

[🇨🇳 中文版](README.zh-CN.md)
