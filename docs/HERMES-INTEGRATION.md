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
# Assuming you cloned to ~/agent-guardrails/
# Create the plugin directory
mkdir -p ~/.hermes/plugins/agent-guardrails

# Copy plugin files (note: source dir is agentguard-plugin, not hermes-plugin)
cp ~/agent-guardrails/agentguard-plugin/* ~/.hermes/plugins/agent-guardrails/

# Or symlink for easy updates (avoids re-copying on pull)
ln -s ~/agent-guardrails/agentguard-plugin/__init__.py ~/.hermes/plugins/agent-guardrails/__init__.py
ln -s ~/agent-guardrails/agentguard-plugin/plugin.yaml ~/.hermes/plugins/agent-guardrails/plugin.yaml
```

> **💡 Note**: The plugin directory name under `~/.hermes/plugins/` is arbitrary — `agent-guardrails` is just a convention. You can name it anything (e.g. `hermes-enforcer`), just match it in Step 4's config.

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

## YAML Pitfalls ⚠️

### Escape sequences in double-quoted strings

YAML double-quoted strings support only specific escape sequences (`\n`, `\t`, `\\`, `\"`, `\uXXXX`, etc.).
Characters that look "escaped" but aren't valid will **silently break** the entire frontmatter parse,
causing **all rules to be ignored** with no runtime error.

| ❌ Wrong | ✅ Correct | Reason |
|:---------|:-----------|:-------|
| `replacement: "(´；ω；\`)"` | `replacement: "(´；ω；\`)"` | `` \` `` is not a valid YAML escape; backticks don't need escaping |

**To verify your rules parse correctly:**
```bash
cd ~/.hermes/workspace && python3 -c "
import yaml
with open('agent-guardrails-rules.md') as f:
    data = yaml.safe_load(f)
print(f'OK: {len(data.get(\"rules\", []))} rules loaded')
"
```

If this prints 0 rules, check your YAML frontmatter for escape issues.

### Default rules file path

The plugin reads `$HERMES_HOME/workspace/agent-guardrails-rules.md` by default.
If your rules file has a **different filename**, create a symlink or set `AGENTGUARD_RULES`:

```bash
# Option A: Symlink (easiest)
ln -s your-rules-file.md ~/.hermes/workspace/agent-guardrails-rules.md

# Option B: Environment variable (set in ~/.hermes/.env)
AGENTGUARD_RULES=/home/user/.hermes/workspace/your-rules-file.md
```

## Troubleshooting

**Plugin doesn't load**
- Check `~/.hermes/plugins/agent-guardrails/` exists with both `__init__.py` and `plugin.yaml`
- Verify `agentguard` is installed: `pip show agentguard`
- Check Gateway logs: `journalctl --user -u hermes-gateway -n 50 | grep -i agentguard`

**Rules not applying**
- Verify the rules file exists at the expected path
- Check YAML syntax with the verification command above — a parse error **silently yields 0 rules**
- Check Gateway logs for parse errors: `journalctl --user -u hermes-gateway -n 100 | grep -i "Failed to parse"`
- Ensure rules have `enabled: true`
- Make sure the rules file name matches the default (`agent-guardrails-rules.md`) or set `AGENTGUARD_RULES`
- Test in the Hermes venv:
  ```bash
  source ~/.hermes/hermes-agent/.venv/bin/activate
  python3 -c "from agentguard.enforcer import load_rules; print(f'{len(load_rules())} rules')"
  ```

**Transform rules not working (emoji → kaomoji, etc.)**
- Same root cause as above: if YAML frontmatter fails to parse, **all rules** (including transforms) are silently disabled
- Check for invalid escape sequences in `replacement:` fields
- Verify the rule is enabled and transform mode is `regex_replace`
- Quick test:
  ```bash
  source ~/.hermes/hermes-agent/.venv/bin/activate
  python3 -c "
  from agentguard.enforcer import on_transform_output
  r = on_transform_output(response_text='test 😅', session_id='test')
  print('Transformed:', repr(r if r else '(no change)'))
  "
  ```

**AGENTGUARD_DISABLE not working**
- Must be set **before** Gateway starts (in `~/.hermes/.env` or systemd override)
- Hot-reload not supported for disable flag
