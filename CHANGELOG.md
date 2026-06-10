# Changelog

## 0.1.0 (2026-06-10)

### Initial Release

- **Enforcer Rule Engine**: YAML-defined behavior rules with keyword triggers, condition matching, and priority-based conflict resolution
  - Rule types: `always_block`, `require_tools`, `only_block_tools`, `transform`
  - Hot-reload support
- **Domain Router**: Maps natural language keywords to specialized skills/workflows
  - Zero-config extension model
- **Quality Gate (PID)**: Control-theory-inspired error correction loop
  - P-loop: Immediate single-error correction
  - I-loop: Rule persistence for recurring errors
  - D-loop: Accelerating error detection
- **Project Scaffold**: Complete config, docs, test, and example structure
