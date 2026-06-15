# AgentGuard

> **LLM Agent 行为规则引擎 —— 工具调用层行为治理。**
> 基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的插件系统。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

AgentGuard 在**工具调用层**做行为约束——不是改 prompt，不是过滤输出，而是在 Agent 调用工具的那一刻拦截检查。它作为 **Hermes Agent 插件**运行，注册三个生命周期钩子：`pre_llm_call`、`pre_tool_call`、`transform_llm_output`。

---

## 安装

把下面这段话**直接复制发给你的 Hermes Agent**，它就会自动装好：

> 去 GitHub 装 agent-guardrails 规则引擎插件，执行：
> 1. `pip install https://github.com/714roy/agent-guardrails/releases/download/v1.1.0/agentguard-1.1.0-py3-none-any.whl`
> 2. `git clone https://github.com/714roy/agent-guardrails.git ~/agent-guardrails && mkdir -p ~/.hermes/plugins/agent-guardrails && cp -r ~/agent-guardrails/agentguard-plugin/* ~/.hermes/plugins/agent-guardrails/ && cp ~/agent-guardrails/config/enforcer-rules.md.example ~/.hermes/workspace/agent-guardrails-rules.md`
> 3. 在 `~/.hermes/config.yaml` 的 `plugins.enabled` 里加上 `agent-guardrails`
> 4. 重启 Gateway

> **⚠️ 装完后注意事项：**
> - **规则文件名**：插件默认读 `agent-guardrails-rules.md`。如果规则文件用了别的名字（比如 `hermes-enforcer-rules.md`），建个软链接或设 `AGENTGUARD_RULES` 环境变量
> - **YAML 转义坑**：双引号字符串里 `\`` 这样的非法转义会导致整个规则集解析失败→**所有规则静默不生效**，没有报错。写完规则记得验证 `yaml.safe_load()` 一下
> - **验证生效**：看 Gateway 日志 `journalctl --user -u hermes-gateway -n 30 | grep agentguard`，应有 `AgentGuard loaded: N rules`
> - **更多细节**：[docs/HERMES-INTEGRATION.md](docs/HERMES-INTEGRATION.md)

👉 **小白教程**：[docs/BEGINNER-GUIDE.md](docs/BEGINNER-GUIDE.md)（10 分钟逐步说明）
👉 **集成指南**：[docs/HERMES-INTEGRATION.md](docs/HERMES-INTEGRATION.md)

## 用法

装好即用，**零配置**。默认规则已涵盖常见行为约束：

| 能力 | 效果 |
|:-----|:-----|
| **规则拦截** | 用户触发关键词后自动激活规则，条件不满足前工具调用被拦住 |
| **输出转换** | 自动替换 LLM 回复内容（如 emoji → 颜文字） |
| **热重载** | 修改 `~/.hermes/workspace/agent-guardrails-rules.md`，下一轮对话自动生效 |

修改规则文件即可自定义行为，语法见 [`config/enforcer-rules.md.example`](config/enforcer-rules.md.example)。

**禁用方法：** 启动前设环境变量 `AGENTGUARD_DISABLE=1`

---

## 工作原理

```
用户发消息
    │
    ▼
pre_llm_call 钩子 ── 识别消息话题，激活匹配的规则
    │                   └─ 规则状态初始化
    ▼
Agent 调用工具
    │
    ▼
pre_tool_call 钩子 ── 检查活跃规则：
    │                   ① 工具满足了某规则的前置条件？→ 标记已满足，放行
    │                   ② 所有前置条件已满足？→ 放行
    │                   ③ 条件未满足，工具在拦截名单里？→ 🚫 拦截
    ▼
放行 / 拦截
```

### 规则类型

| 类型 | 说明 |
|:-----|:------|
| **`always_block`** | 硬拦截：条件不满足前所有工具调用都被拦住 |
| **`require_tools`** | Agent 必须先调指定工具（含参数约束） |
| **`only_block_tools`** | 仅拦截特定工具（空列表=拦截所有） |
| **`transform`** | 正则替换输出转换（emoj → 颜文字等） |
| **`track_turns`** | 对话轮数超过阈值时注入上下文提醒 |

### 规则示例

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
    block_message: "敏感命令请先加 --dry-run 验证"
```

> **⚠️ 注意事项：**
> - **规则文件名**：插件默认读取 `~/.hermes/workspace/agent-guardrails-rules.md`，如果文件名不一致需建软链接或设 `AGENTGUARD_RULES` 环境变量
> - **YAML 转义**：双引号字符串中 `\`` 等非法转义会导致整个 frontmatter 解析失败→**所有规则静默失效**（无运行时错误）。详见 [docs/HERMES-INTEGRATION.md](docs/HERMES-INTEGRATION.md#yaml-pitfalls-️)

---

## 目录结构

```
agent-guardrails/
├── agentguard/                   # pip 可安装的引擎包
│   ├── __init__.py               # 包入口
│   └── enforcer.py               # 核心规则引擎（~500 行）
├── hermes-plugin/                # Hermes Agent 插件桥接
│   ├── __init__.py               # 薄桥接层 + register(ctx)
│   └── plugin.yaml               # 插件清单
├── config/
│   ├── enforcer-rules.md.example   # 规则配置示例
│   └── routing-table.yaml.example    # 路由表示例
├── docs/
│   └── HERMES-INTEGRATION.md     # Hermes 集成指南（英文）
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## 方案对比

| 方案 | 约束层级 | 场景 | 特点 |
|:----|:---------|:-----|:-----|
| Guardrails AI | 输出层 | 结构化输出 | prompt 级约束 |
| LlamaGuard | 输入/输出层 | 内容安全 | 分类模型 |
| **AgentGuard** | **工具调用层** | **Agent 行为治理** | **规则引擎 + 三钩子** |

---

## 依赖

- Python 3.10+
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)（插件模式必须）
- PyYAML（规则解析）

## 开源协议

MIT

---

[🇬🇧 English](README.en.md)
