# AgentGuard

> 基于规则引擎的 LLM Agent 行为治理系统。
> 不是调 prompt——是系统工程。

---

## 为什么要 AgentGuard

大模型 Agent 能力很强，但不稳定。给了工具和自主权之后，它们会：

- 未经确认就执行危险的 shell 命令
- 工具调用顺序搞错、用错上下文
- 忘记之前的决策，重复犯同样的错
- 时间长了行为模式越来越不可控

现有的防御方案（Guardrails AI、LlamaGuard）都在 **输入/输出层面** 做约束——管的是 Agent 说什么，不是它 **做什么**。

**AgentGuard 不一样。它在工具调用层面** 做行为治理——通过规则引擎、领域路由和 PID 闭环控制，约束 Agent 的行为边界，而不是约束它的回答内容。

---

## 架构

```
┌──────────────────────────────────────────────────────────┐
│                       AgentGuard                          │
│                                                            │
│  ┌─────────────┐  ┌──────────┐  ┌───────────────┐        │
│  │  Enforcer    │  │  Router  │  │  Quality       │        │
│  │  规则引擎     │◄─┤  Skill   │◄─┤  Gate (PID)   │        │
│  │  (N条规则)    │  │  路由表   │  │  闭环控制      │        │
│  └──────┬──────┘  └────┬─────┘  └──────┬────────┘        │
│         │              │     ↗         │                  │
│         │              │  Feedback     │                  │
│         │              │  Channel      │                  │
│         ▼              ▼               ▼                  │
│  ┌─────────────────────────────────────────────┐         │
│  │         LLM Agent 行为层                      │         │
│  │  工具调用 / 推理 / 输出 / 记忆 / 路由          │         │
│  └─────────────────────┬───────────────────────┘         │
│                        │                                  │
│                        ▼                                  │
│  ┌─────────────────────────────────────────────┐         │
│  │         审计日志 (Audit Trail)               │         │
│  │  记录：规则触发 / 路由决策 / 拦截事件          │         │
│  └─────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

### 三大核心组件

#### 1️⃣ Enforcer — 规则引擎

YAML 定义的行为规则，在 Agent 调用系统工具之前拦截、要求或转换行为。

- **关键词触发 + 条件匹配** → 灵活定义规则生效场景
- **规则类型**：硬拦截（`always_block`）、工具前置依赖（`require_tools`）、工具禁用（`only_block_tools`）、输出转换（`transform`）
- **优先级机制**：多条规则同时触发时按 priority 裁决
- **热加载**：修改规则文件无需重启 Agent

```yaml
rules:
  - name: sensitive-command
    priority: 20
    triggers:
      keywords: ["rm", "shutdown", "drop table"]
    conditions:
      require_tools:
        - terminal
          args_contains: ["--dry-run"]
    block_message: "敏感命令请先加 --dry-run 验证"
```

#### 2️⃣ Router — 领域路由表

将自然语言输入的关键词映射到专业 Skill 和工作流，无需复杂的意图分类模型。

- 关键词 → Skill 自动匹配（覆盖 13+ 领域）
- 零配置扩展——加一行就是新领域
- 冷启动默认 fallback 兜底

#### 3️⃣ Quality Gate — PID 闭环控制

把控制理论用到 Agent 行为纠偏上，灵感来自 PID 控制器：

| 环节 | 触发条件 | 动作 |
|:----|:---------|:-----|
| **P** (比例) | 单次错误 | 即时修正当前输出 |
| **I** (积分) | 同类错误 2+ 次 | 固化为规则/记忆 |
| **D** (微分) | 错误加速增多 | 触发全面审计+重置 |

集成 **Consilium** 多模型交叉验证作为外部审计。

### 支撑系统

- **审计日志**：每次规则触发、路由决策、PID 动作都记录上下文，可追溯调试
- **反馈通道**：Router → PID / PID → Router 双向信号，驱动系统持续进化

---

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/714roy/agent-guardrails.git
cd agent-guardrails

# 配置规则
cp config/enforcer-rules.yaml.example config/enforcer-rules.yaml

# 运行测试
python -m pytest tests/

# 查看示例
bash examples/demo.sh
```

### 配置示例

`config/enforcer-rules.yaml` 中定义规则：

```yaml
rules:
  - name: production-deploy-guard
    enabled: true
    priority: 20
    triggers:
      keywords: ["deploy", "release", "production"]
    conditions:
      require_tools:
        - terminal
          args_contains: ["--dry-run"]
    block_message: "生产部署需先 --dry-run 验证"
```

---

## 方案对比

| 方案 | 约束层级 | 场景 | 特点 |
|:----|:---------|:-----|:----|
| Guardrails AI | 输出层 | 结构化输出 | prompt 级约束 |
| LlamaGuard | 输入/输出层 | 内容安全 | 分类模型 |
| **AgentGuard** | **工具调用层** | **Agent 行为治理** | **规则引擎 + 路由 + PID 闭环** |

---

## 适用场景

- 你的 LLM Agent **有工具权限**（shell、浏览器、API 调用）
- 你需要的不仅是**改 prompt 就能解决**的行为约束
- 你希望系统 **自己从错误中学习**
- 你需要**可追溯的审计日志**用于合规或调试
- 你在构建**多 Agent 系统**，需要统一的行为管控

---

## 开源协议

MIT

---

## 相关项目

- [Guardrails AI](https://github.com/guardrails-ai/guardrails) — 结构化输出防护
- [Consilium](https://github.com/openadapt-ai/consilium) — 多模型交叉验证
- [Guidance](https://github.com/guidance-ai/guidance) — 结构化生成控制

---

[🇬🇧 English](README.md)
