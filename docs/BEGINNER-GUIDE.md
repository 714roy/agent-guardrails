# AgentGuard 小白教程

> 看完这个，你也能给自己的 AI Agent 装上「行为规则引擎」

---

## 这是干什么的？

你有一个 AI 助手（Hermes Agent），它能调用各种工具——查网页、跑命令、写文件。

问题来了：它有时候会乱来。比如你让它「分析一下」，它可能直接 `rm -rf /` 了（夸张，但意思到了）。

**AgentGuard 就是给 AI 装个「交规」**——红灯停、绿灯行，违规就拦下来。

---

## 先搞清三件事

| 术语 | 大白话 |
|:----|:-------|
| **Hermes Agent** | 你的 AI 助手，能调工具（查网页、跑命令、读文件等） |
| **AgentGuard** | 给 AI 装的行车记录仪 + 交规，不让它乱来 |
| **规则文件** | 一张「什么能做、什么不能做」的清单，写在一个文件里 |

---

## 安装（一共 5 步，10 分钟）

### 前提：你已经装好了 Hermes Agent

### 第 1 步：安装引擎

打开终端，复制粘贴这行：

```bash
pip install agentguard
```

等它跑完，显示 `Successfully installed agentguard` 就行了。

验证一下：
```bash
python3 -c "from agentguard import load_rules; print('OK')"
```
输出 `OK` 表示装好了。

---

### 第 2 步：创建插件目录

```bash
mkdir -p ~/.hermes/plugins/hermes-enforcer
```

> 💡 这行命令的意思是：在 Hermes 的插件文件夹里，新建一个叫 `hermes-enforcer` 的文件夹。

---

### 第 3 步：下载插件文件

去 GitHub 下载这两个文件：
- https://github.com/714roy/agent-guardrails/blob/main/hermes-plugin/__init__.py
- https://github.com/714roy/agent-guardrails/blob/main/hermes-plugin/plugin.yaml

放到你刚创建的 `~/.hermes/plugins/hermes-enforcer/` 目录里。

> 💡 不会下载？点链接 → 点 Raw 按钮 → 右键另存为

或者用命令行（如果你会的话）：
```bash
cd ~/.hermes/plugins/hermes-enforcer
wget https://raw.githubusercontent.com/714roy/agent-guardrails/main/hermes-plugin/__init__.py
wget https://raw.githubusercontent.com/714roy/agent-guardrails/main/hermes-plugin/plugin.yaml
```

---

### 第 4 步：创建规则文件

复制粘贴这整段到一个新文件 `~/.hermes/workspace/hermes-enforcer-rules.md`：

```markdown
---
rules:
  - name: no-dangerous-commands
    enabled: true
    priority: 10
    description: "危险命令必须先 dry-run 验证"
    triggers:
      keywords: ["rm", "shutdown", "reboot", "删除", "卸载"]
      mode: any
    conditions:
      require_tools:
        - name: terminal
          args_contains: ["--dry-run"]
    only_block_tools:
      - terminal
    block_message: "⚠️ 危险命令请先加 --dry-run 验证一下再执行"

  - name: think-before-create
    enabled: true
    priority: 8
    description: "新建东西之前先搜搜有没有现成的"
    triggers:
      keywords: ["新建", "创建", "写一个", "做个"]
      mode: any
    conditions:
      require_tools:
        - name: web_search
    only_block_tools:
      - write_file
    block_message: "⚠️ 先搜一下有没有现成的，别重复造轮子"
---
```

> 💡 不会创建文件？用记事本/VSCode，把上面的内容粘贴进去，保存为 `hermes-enforcer-rules.md`，放到 `~/.hermes/workspace/` 目录。

---

### 第 5 步：启用插件 + 重启

编辑 Hermes 配置文件 `~/.hermes/config.yaml`，找到 `plugins:` 这一段，改成：

```yaml
plugins:
  enabled:
    - hermes-enforcer
```

然后重启 Gateway：

```bash
systemctl --user restart hermes-gateway
```

等几秒钟，验证是否生效：

```bash
journalctl --user -u hermes-gateway --since "1 min ago" | grep agentguard
```

如果看到 `AgentGuard loaded: 2 rules` 就成功了！

---

## 测试：看看它是不是真的在工作

装好之后，跟你的 AI 说一句：

> 「帮我删掉这个文件」

它应该会回答类似：

> ⚠️ 危险命令请先加 --dry-run 验证一下再执行

而不是直接去跑 `rm` 命令。

再试试说：

> 「帮我写一个博客系统」

它应该会先搜一下有没有现成的方案，而不是直接动手写。

---

## 怎么改规则

规则文件在 `~/.hermes/workspace/hermes-enforcer-rules.md`。

可以用记事本打开编辑。格式很简单：

```yaml
- name: 规则名字          # 随便起，别重复就行
    enabled: true          # true=开启，false=关闭
    description: "说明"     # 写给人看的
    triggers:              # 触发条件——用户说什么话会激活这条规则
      keywords: ["关键词1", "关键词2"]
      mode: any            # any=任一关键词就触发，all=全部触发
    conditions:            # 条件——必须满足才能继续
      require_tools:       # 必须先调什么工具
        - name: "工具名"
    only_block_tools:      # 拦截哪些工具（留空=拦全部）
      - "工具名"
    block_message: "拦截时回复的话"
```

改完之后**不需要重启**，等下一轮对话自动生效。

---

## 常见问题

**Q: 怎么临时关掉 AgentGuard？**
A: 在终端运行 `export AGENTGUARD_DISABLE=1`，然后重启 Gateway。

**Q: 怎么永久删掉？**
A: 删掉 `~/.hermes/plugins/hermes-enforcer/` 目录，然后从 `~/.hermes/config.yaml` 里去掉 `hermes-enforcer`，重启 Gateway。

**Q: 规则不生效？**
A: 检查文件是不是 `.md` 格式（不是 `.yaml`）。检查 `enabled: true` 有没有写。检查关键词有没有拼错。

**Q: 报 YAML 错误？**
A: 用这个网站验证你的规则文件：https://www.yamllint.com/

---

## 进阶（以后再看）

想了解更多规则类型、路由表、输出转换等高级功能，看完整文档：
- [docs/HERMES-INTEGRATION.md](HERMES-INTEGRATION.md)（英文，讲得详细）
- [config/enforcer-rules.yaml.example](../config/enforcer-rules.yaml.example)（更多规则示例）

---

*搞不定的话，把报错信息复制给我，我帮你看 (^_^)*
