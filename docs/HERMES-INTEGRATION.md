# Integrating AgentGuard with Hermes Agent

> **AgentGuard requires [Hermes Agent](https://github.com/NousResearch/hermes-agent)**
> to function as a behavior enforcement plugin. Below are the exact steps.

## Overview

AgentGuard registers three hooks into Hermes Agent's pipeline:

| Hook | When | What it does |
|:-----|:-----|:-------------|
| `pre_llm_call` | Each turn start | Classifies user message, activates matching rules |
| `pre_tool_call` | Before each tool call | Checks active rules, blocks if prerequisites not met |
| `transform_llm_output` | After LLM response | Applies regex transforms (e.g. emoji → kaomoji) |

## Installation

### 1. Install the engine

```bash
pip install https://github.com/714roy/agent-guardrails/releases/download/v1.1.0/agentguard-1.1.0-py3-none-any.whl
```

Or install from source:

```bash
git clone https://github.com/714roy/agent-guardrails.git
cd agent-guardrails
pip install -e .
```

### 2. Link the Hermes plugin

```bash
# Create the plugin directory
mkdir -p ~/.hermes/plugins/agent-guardrails

# Copy plugin files
cp agent-guardrails/hermes-plugin/* ~/.hermes/plugins/agent-guardrails/

# Or symlink for easy updates
ln -s $(pwd)/agent-guardrails/hermes-plugin/__init__.py ~/.hermes/plugins/agent-guardrails/__init__.py
ln -s $(pwd)/agent-guardrails/hermes-plugin/plugin.yaml ~/.hermes/plugins/agent-guardrails/plugin.yaml
```

### 3. Create the rules file

Copy the example rules to Hermes workspace:

```bash
cp agent-guardrails/config/enforcer-rules.md.example ~/.hermes/workspace/agent-guardrails-rules.md
```

Or use the `rules.md` format (YAML frontmatter):

```markdown
---
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
---
```

> **File path**: The plugin reads `~/.hermes/workspace/agent-guardrails-rules.md` by default.
> Override with the `AGENTGUARD_RULES` environment variable.

### 4. Enable the plugin in Hermes config

Edit `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - agent-guardrails
```

Or if using a custom plugins directory:

```yaml
plugins:
  dir: ~/.hermes/plugins
  enabled:
    - agent-guardrails
```

### 5. Restart Gateway

```bash
systemctl --user restart hermes-gateway
```

Check it loaded:

```bash
journalctl --user -u hermes-gateway --since "5 min ago" | grep agentguard
# Expected: AgentGuard loaded: 7 rules, disable with AGENTGUARD_DISABLE=1
```

## Configuration

### Environment variables

| Variable | Default | Purpose |
|:---------|:--------|:--------|
| `AGENTGUARD_RULES` | `$HERMES_HOME/workspace/agent-guardrails-rules.md` | Path to rules file |
| `AGENTGUARD_DISABLE` | `0` | Set to `1` to completely disable enforcement |
| `HERMES_HOME` | `~/.hermes` | Hermes Agent home directory |

### Rule format

See [config/enforcer-rules.md.example](../config/enforcer-rules.md.example) for a
complete reference. Each rule supports:

- **`triggers.keywords`** — user message keywords to activate the rule
- **`conditions.require_tools`** — tools that must be called first
- **`conditions.only_block_tools`** — which tools to block (empty = all)
- **`always_block`** — unconditional block on activation
- **`max_consecutive_calls`** — throttle after N tool calls without response
- **`transform`** — regex replacements for output transformation
- **`track_turns`** — inject warnings after N turns

Rules hot-reload: modify the rules file and the plugin detects changes automatically
at the start of the next turn. No restart needed for rule changes.

## Testing Without Hermes

You can use the engine standalone for testing:

```python
from agentguard import load_rules, on_pre_llm_call, on_pre_tool_call

# Load rules from a custom path
rules = load_rules("/path/to/rules.yaml")
print(f"Loaded {len(rules)} rules")

# Test a rule activation
result = on_pre_llm_call(
    session_id="test-session",
    user_message="analyze this situation",
    is_first_turn=True,
)
# result contains routing context or None
```

## Troubleshooting

**Plugin doesn't load**
- Check `~/.hermes/plugins/agent-guardrails/` exists with both `__init__.py` and `plugin.yaml`
- Verify `agentguard` is installed: `pip show agentguard`
- Check Gateway logs: `journalctl --user -u hermes-gateway -n 50 | grep -i agentguard`

**Rules not applying**
- Verify the rules file exists at the expected path
- Check rule syntax with: `python3 -c "import yaml; yaml.safe_load(open('rules.md'))"`
- Ensure rules have `enabled: true`

**AGENTGUARD_DISABLE not working**
- Must be set **before** Gateway starts (in `~/.hermes/.env` or systemd override)
- Hot-reload not supported for disable flag
