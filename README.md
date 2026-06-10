# AgentGuard

> A rule-based behavior governance system for LLM agents.  
> Not prompt engineering — system engineering for agent behavior.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Why AgentGuard

LLM agents are powerful but unpredictable. When given tools and autonomy, they can:

- Execute dangerous shell commands without verification
- Call tools in the wrong order or wrong context
- Forget past decisions and repeat mistakes
- Drift into unreliable behavior patterns over time

Most existing guardrail solutions (Guardrails AI, LlamaGuard) work at the **prompt/output level** — they constrain what an agent says, not what it **does**.

**AgentGuard** operates at the **tool-call level**: it governs agent behavior through a rule engine, domain router, and self-healing PID control loop. It doesn't tell the agent what to say — it enforces what it can do.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                       AgentGuard                          │
│                                                            │
│  ┌─────────────┐  ┌──────────┐  ┌───────────────┐        │
│  │  Enforcer    │  │  Router  │  │  Quality       │        │
│  │  Rule Engine │◄─┤  Skill   │◄─┤  Gate (PID)   │        │
│  │  (N rules)   │  │  Router  │  │  Closed Loop  │        │
│  └──────┬──────┘  └────┬─────┘  └──────┬────────┘        │
│         │              │     ↗         │                  │
│         │              │  Feedback     │                  │
│         │              │  Channel      │                  │
│         ▼              ▼               ▼                  │
│  ┌─────────────────────────────────────────────┐         │
│  │         LLM Agent Behavior Layer             │         │
│  │   Tool calls / Reasoning / Output / Memory   │         │
│  └─────────────────────┬───────────────────────┘         │
│                        │                                  │
│                        ▼                                  │
│  ┌─────────────────────────────────────────────┐         │
│  │         Audit Trail                          │         │
│  │   Logs: rule triggers / routing decisions    │         │
│  └─────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Enforcer — Rule Engine

A YAML-defined rule engine that intercepts, requires, or transforms agent behavior before it reaches system tools.

- **Keyword triggers** + **condition matching** → decide when a rule applies
- **Rule types**: hard block (`always_block`), tool requirement (`require_tools`), tool restriction (`only_block_tools`), output transformation (`transform`)
- **Priority field** — resolves conflicts when multiple rules fire simultaneously
- **Hot-reload** — rules update without restarting the agent

```yaml
rules:
  - name: reasoning-force
    priority: 10
    triggers:
      keywords: ["推理", "logic", "constraint"]
    conditions:
      require_tools:
        - mcp_chiasmus_chiasmus_formalize
    only_block_tools:
      - terminal
    block_message: "Please use formal verification tools for logic problems."
```

#### 2. Router — Domain Routing Table

Maps natural language keywords to specialized skills/workflows, enabling context-aware routing without complex intent classification.

- Keyword → Skill mapping (N+ domains)
- Zero-config extension (add one row to add a new domain)
- Cold-start fallback handler for unmapped inputs

#### 3. Quality Gate — PID Closed Loop

Applies control theory to agent behavior correction, inspired by the PID (Proportional–Integral–Derivative) controller:

| Loop | Trigger | Action |
|------|---------|--------|
| **P** (Proportional) | Single error | Immediate output correction |
| **I** (Integral) | 2+ same-type errors | Persist to rule/memory |
| **D** (Derivative) | Accelerating errors | Trigger full audit + reset |

Integrated with **Consilium** — a multi-model cross-validation system — as external audit.

### Supporting Systems

- **Audit Trail**: Every rule trigger, routing decision, and PID action is logged with full context for debugging and compliance
- **Feedback Channel**: Router → PID and PID → Router signals enable continuous system evolution

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/<your-username>/agent-guardrails.git
cd agent-guardrails

# Set up the rule engine
cp config/enforcer-rules.yaml.example config/enforcer-rules.yaml

# Run the tests
python -m pytest tests/

# See it in action
bash examples/demo.sh
```

### Configuration

Define rules in `config/enforcer-rules.yaml`:

```yaml
rules:
  - name: sensitive-command
    enabled: true
    priority: 20
    triggers:
      keywords: ["rm", "shutdown", "drop table"]
    conditions:
      require_tools:
        - terminal
          args_contains: ["--dry-run"]
    block_message: "Sensitive commands require --dry-run verification first."
```

---

## Comparison

| Solution | Layer of Control | Scope | Mechanism |
|----------|-----------------|-------|-----------|
| Guardrails AI | Output | Response structure | Prompt templates + validators |
| LlamaGuard | Input/Output | Content safety | Classification model |
| **AgentGuard** | **Tool-call** | **Agent behavior** | **Rule engine + Router + PID** |

---

## Project Structure

```
agent-guardrails/
├── config/                   # Rule definitions (sanitized)
│   ├── enforcer-rules.yaml
│   └── routing-table.yaml
├── docs/                     # Architecture & design docs
├── bin/                      # Executable scripts
├── tests/                    # Unit & integration tests
├── examples/                 # Usage scenarios
└── benchmark/                # Performance comparisons
```

---

## When to Use AgentGuard

- Your LLM agent has **tool access** (shell, browser, API calls)
- You need **behavioral constraints** beyond prompt engineering
- You want a **self-healing system** that learns from mistakes
- You need **audit trails** for compliance or debugging
- You're building **multi-agent systems** with shared tools

---

## License

MIT

---

## Related Work

- [Guardrails AI](https://github.com/guardrails-ai/guardrails) — Structured output guardrails
- [Consilium](https://github.com/openadapt-ai/consilium) — Multi-model cross-validation
- [Guidance](https://github.com/guidance-ai/guidance) — Structured generation
