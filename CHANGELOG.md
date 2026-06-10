# Changelog

## 1.0.0 (2026-06-10)

### Major Release — Now with Actual Code!

- **Core Engine** (`agentguard/enforcer.py`): ~500 lines of Python, the actual rule engine
  - `pre_llm_call` hook: topic classification, rule activation, turn tracking
  - `pre_tool_call` hook: tool-level enforcement with prerequisite checking
  - `transform_llm_output` hook: regex-based output transformation
  - Hot-reload rules without restarting (file mtime detection)
  - Priority-based rule evaluation
- **Hermes Plugin Bridge** (`hermes-plugin/`): thin integration layer
  - `register(ctx)` function for Hermes Agent hook system
  - `plugin.yaml` manifest with all three hooks declared
- **Package Structure**: `pyproject.toml` for pip install
- **Documentation**:
  - English README with Quick Start for Hermes
  - Chinese README (中文版)
  - `docs/HERMES-INTEGRATION.md` full setup guide
- **Example Configs**: sanitized enforcer-rules and routing-table examples

### Changed
- Complete repo restructure from config-only to actual plugin package
- All personal references sanitized (names, paths, project IDs)
- Config files renamed to `.example` to avoid overwrite

## 0.1.0 (2026-06-10)

- Initial scaffold: README, config examples, project framework
