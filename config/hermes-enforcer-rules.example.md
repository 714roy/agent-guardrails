---
rules:
  - name: code-exec-approval
    enabled: true
    priority: 20
    description: >-
      修改代码(write_file/patch/execute_code)或执行命令(terminal)前，
      必须先文字询问用户同意。禁止擅自操作。
    triggers:
      keywords:
        - "帮我"
        - "改一下"
        - "写个"
        - "重构"
        - "跑一下"
        - "跑个"
        - "部署"
        - "执行"
        - "运行"
        - "修一下"
        - "修改"
        - "写一个"
        - "做一个"
      mode: any
    conditions:
      require_tools:
        - name: send_message
    only_block_tools:
      - write_file
      - patch
      - execute_code
      - terminal
    block_message: >-
      🚫 动代码/执行命令前需先文字询问用户同意！
      QQ 没有弹窗，直接发消息问用户（如"改这个xxx，行吗？"），
      等用户回复确认后再执行。禁止先干再说。
  - name: three-mirrors
    enabled: true
    priority: 10
    description: 三镜分析框架：分析类必走 three-mirrors + karpathy-llm-wiki，禁止裸分析
    triggers:
      keywords: ["三镜", "三镜分析", "三镜角度", "用三镜"]
      mode: any
    conditions:
      require_tools:
        - name: skill_view
          args_contains: ["three-mirrors"]
        - name: skill_view
          args_contains: ["karpathy"]
    only_block_tools: []
    always_block: true
    block_message: "⚠️ 分析类问题请先加载三镜：skill_view(name='three-mirrors') + skill_view(name='karpathy-llm-wiki')。禁止裸分析。"
  - name: three-mirrors-archive
    enabled: true
    priority: 11
    description: 三镜分析回复前必须归档到存档库，否则拦截 send_message
    triggers:
      keywords: ["三镜分析", "三镜角度"]
      mode: any
    conditions:
      require_tools:
        - name: write_file
          args_contains: ["存档库/分析/"]
    only_block_tools:
      - send_message
    block_message: "⚠️ 三镜分析还没归档！先走 Step 6：write_file 保存到存档库/分析/ 再回复用户。"
  - name: dep-map-check
    enabled: true
    priority: 9
    description: 全局变更（改名/删skill/改路由）前必须查 DEPENDENCY_MAP.md
    triggers:
      keywords: ["改名", "重命名", "迁移", "删除 skill", "改路由", "牵动全局"]
      mode: any
    conditions:
      require_tools:
        - name: read_file
          args_contains: ["DEPENDENCY_MAP"]
    only_block_tools:
      - skill_manage
      - patch
    block_message: "⚠️ 全局变更前先查 DEPENDENCY_MAP.md 确认影响范围，改完后同步更新该文件。"
  - name: no-wheel-reinvent
    enabled: true
    priority: 8
    description: 遇到新需求先搜现有方案，不重复造轮子
    triggers:
      keywords: ["新建", "创建", "开发", "搭建", "设计"]
      mode: any
    conditions:
      require_tools:
        - name: web_search
        - name: search_files
          args_contains: [".hermes/skills"]
    only_block_tools:
      - write_file
      - skill_manage
    block_message: "🚫 创建新项目前需先搜现有方案：web_search + 搜索已有 skills"
  - name: reasoning-force
    enabled: true
    priority: 10
    description: 约束题/逻辑推理强制走 chiasmus Z3/Python 穷举
    triggers:
      keywords: ["推理", "逻辑", "约束", "匹配", "判断", "组合", "排列"]
      mode: any
    conditions:
      require_tools:
        - name: mcp_chiasmus_chiasmus_formalize
        - name: mcp_chiasmus_chiasmus_verify
    only_block_tools:
      - terminal
    block_message: "🚫 约束题/逻辑推理请先调 chiasmus 形式化验证工具"
  - name: memory-force
    enabled: true
    priority: 7
    description: 涉及前文信息先用 session_search 查证，不靠 context window 硬记
    triggers:
      keywords: ["之前", "刚才", "上回", "前面", "刚才说的", "我记得", "你之前"]
      mode: any
    conditions:
      require_tools:
        - name: session_search
    only_block_tools:
      - terminal
      - write_file
      - web_search
    block_message: "🚫 涉及前文信息请先调用 session_search 查证"
  - name: agentmemory-save
    enabled: true
    priority: 6
    description: 持久化记忆优先使用 agentmemory HTTP API（无限容量），替代内置 memory tool（2200字符限制）
    triggers:
      keywords: ["记住", "记录", "记下", "保存记忆", "存入记忆", "写入记忆", "复盘", "梦境", "日志", "归档", "笔记存档",
        "教训", "经验", "踩坑", "翻车", "决策", "决定", "结论", "模式", "pattern",
        "存一下", "保存这条", "学习到", "学到", "这个记住了", "这个重要",
        "有用", "值得记", "记一笔", "存档"]
      mode: any
    conditions:
      require_tools:
        - name: terminal
          args_contains: ["agentmemory"]
    only_block_tools:
      - memory
    block_message: "🚫 持久化记忆请走 agentmemory：python3 ~/.hermes/scripts/am.py save \"内容\" --type decision|pattern|fact|workflow。搜索用 am.py search \"关键词\"。内置 memory tool 只存铁律/偏好/关键配置等热事实。"
  - name: session-start-recall
    enabled: true
    priority: 7
    description: 新对话/话题延续必须先搜 agentmemory 冷记忆，不依赖热内存里的过期信息
    triggers:
      keywords: ["新对话", "接着聊", "接着上次", "继续上次", "继续之前", "之前说的", "之前那个",
        "新会话", "换话题", "今天聊", "回来了"]
      mode: any
    conditions:
      require_tools:
        - name: terminal
          args_contains: ["am.py"]
    only_block_tools:
      - send_message
    block_message: "🚫 新对话/话题延续先查 agentmemory 冷记忆：python3 ~/.hermes/scripts/am.py search \"关键词\" 或 mcp_agentmemory_memory_recall。搜完再回。"
  - name: stop-command
    priority: 100
    description: 用户叫停指令，拦截本轮所有后续工具调用
    triggers:
      keywords: ["停", "不要", "取消", "撤回", "住手", "停下"]
      mode: any
    conditions:
      require_tools: []
    only_block_tools: []
    always_block: true
    block_message: "🚫 已检测到停止指令，本轮所有工具调用已被拦截。如需继续请发新消息。"
  - name: cli-verify
    enabled: true
    priority: 9
    description: 敏感 CLI 操作需先验证再执行
    triggers:
      keywords: ["删除", "卸载", "清除", "rm", "kill", "关机", "重启"]
      mode: any
    conditions:
      require_tools:
        - name: terminal
          args_contains: ["--dry-run", "-n", "确认"]
    only_block_tools:
      - terminal
    block_message: "🚫 敏感操作请先用 --dry-run 或 -n 验证后再执行"
  - name: gateway-restart-notify
    enabled: true
    priority: 6
    description: gateway 重启后通知用户
    triggers:
      keywords: ["重启gateway", "重启网关", "restart gateway", "gateway restart"]
      mode: any
    conditions:
      require_tools:
        - name: send_message
    only_block_tools: []
    block_message: "🚫 Gateway 重启后请发送通知给用户确认状态"

  - name: no-token-truncate
    enabled: true
    priority: 10
    description: "全天候硬拦截：涉及 token/key/密码/凭证的 terminal 命令禁用 ... 截断，且规则本身也不使用 ... 占位"
    triggers:
      keywords:
        - "token"
        - "key"
        - "密码"
        - "password"
        - "secret"
        - "凭证"
        - "credential"
        - "ghp_"
        - "sk-"
        - "API_KEY"
        - "截断"
        - "truncat"
        - "PAT"
      mode: any
    conditions:
      require_tools: []
    only_block_tools:
      - terminal
    block_message: "⛔ 截断重罪：涉及 token/key 的 terminal 命令中出现了 ... 截断。必须使用完整值，一个字不能少。这条规则本身也禁止使用 ... 占位符——整段话重写，用完整真实值。"

  - name: install-approval
    enabled: true
    priority: 10
    description: 安装软件/插件/包/项目前必须经过用户文字同意，禁止擅自安装或下载
    triggers:
      keywords: ["安装", "下载", "装一下", "装个", "装一个", "装", "npm install", "pip install", "apt install", "git clone", "brew install"]
      mode: any
    conditions:
      require_tools:
        - name: send_message
    only_block_tools:
      - terminal
    block_message: "🚫 安装/下载操作需先文字询问用户同意！QQ 没有弹窗，直接发消息问：'安装xxx，行吗？'，等用户回复确认后再执行。"

  - name: emoji-to-kaomoji
    enabled: true
    priority: 1
    description: 自动替换 emoji 为颜文字（transform_llm_output 钩子）
    triggers: {}
    transform:
      mode: regex_replace
      mappings:
        - pattern: "😅"
          replacement: "(^_^;)"
        - pattern: "✅"
          replacement: "(｀・ω・´)b"
        - pattern: "❌"
          replacement: "(´；ω；`)"

  - name: ocr-image
    enabled: true
    priority: 10
    description: 收到图片/截图/图表用 siliconflow_vision.py 分析，不用 vision_analyze（deepseek-v4-flash 不支持原生视觉）
    triggers:
      keywords:
        - "用户发送了一张图片"
        - "image you couldn't see"
        - "vision_analyze"
        - "image_cache"
        - "sent an image"
        - "failed to deserialize"
        - "vision API rejected"
        - "Invalid image source"
        - "Error analyzing image"
        - "img_"
        - ".png"
        - "sleep data"
        - "图表"
        - "截图"
        - "这张图"
      mode: any
    conditions:
      require_tools:
        - name: terminal
          args_contains: ["siliconflow_vision.py"]
    only_block_tools:
      - vision_analyze
    block_message: "🚫 当前模型不支持原生视觉。收到图片请用硅基流动视觉模型：python3 ~/.hermes/skills/openclaw-imports/qwencloud-vision/scripts/siliconflow_vision.py <图片路径> \"<提示词>\""

  - name: claw-output-archive
    enabled: true
    priority: 7
    description: 除缓存/临时文件外，产出内容优先存到 Nutstore Files/工坊/ 下对应分类目录。禁止用 cp/mv 把产物放 /tmp 而不归档
    triggers:
      keywords: ["保存", "存档", "写入文件", "归档", "生成文件", "产出", "导出"]
      mode: any
    conditions:
      require_tools:
        - name: write_file
          args_not_contains: ["/tmp/", "/home/roy/.hermes/cron/output", "/home/roy/.hermes/audio_cache", "/home/roy/.hermes/image_cache", "/home/roy/Nutstore Files/工坊/"]
        - name: terminal
          args_contains: ["/tmp/docgraph", "/tmp/skill", "/tmp/产出"]
          args_not_contains: ["Nutstore Files/工坊"]
    only_block_tools:
      - write_file
      - terminal
    block_message: "📂 产出的文件请存到 Nutstore Files/工坊/ 下（如 Claw/技术/ 或 Claw/文档/），不要放 /tmp。已经生成的东西跑一遍 cp 移到 Claw 目录再结束。"

  - name: skill-mcp-manual-sync
    enabled: true
    priority: 7
    description: 新增/删除/修改 skill 或 MCP 后必须：① 跑审计脚本 ② 更新路由表 ③ 更新技能与MCP说明书.md
    triggers:
      keywords: ["skill_manage", "npx skills add", "git clone", "install skill", "install mcp", "新 skill", "新 MCP", "删除 skill", "删除 mcp"]
      mode: any
    conditions:
      require_tools:
        - name: terminal
          args_contains: ["audit-routing-gaps"]
        - name: write_file
          args_contains: ["文档/清单/技能与MCP说明书.md"]
    only_block_tools:
      - skill_manage
      - write_file
    block_message: "📋 修改了 skill/MCP！三步走：\n1️⃣ 先跑审计: terminal `python3 ~/.hermes/scripts/audit-routing-gaps.py`\n2️⃣ 根据审计结果更新路由表（patch hermes-enforcer-rules.md）\n3️⃣ 更新 技能与MCP说明书.md\n\n缺一步都会被拦住 👀"
  - name: context-turn-warning
    enabled: true
    priority: 1
    description: 对话轮数超过阈值时注入上下文提醒
    triggers: {}
    track_turns:
      warn_at: [30, 50, 70, 90]
      message: "⚠️ 对话已进行 {turns} 轮，建议 /new 新会话释放内存"

  - name: purchase-history-check
    enabled: true
    priority: 9
    description: >
      涉及购买/设备/硬件推荐话题，先用 session_search
      查历史参与度再回复，避免重复推荐或自打脸
    triggers:
      keywords:
        - "入手"
        - "买个"
        - "推荐"
        - "耳机"
        - "耳放"
        - "音箱"
        - "DAC"
        - "设备"
        - "升级"
        - "换一个"
        - "种草"
        - "下单"
        - "值得买"
        - "哪个好"
      mode: any
    conditions:
      require_tools:
        - name: session_search
    only_block_tools:
      - send_message
    block_message: >
      📋 购买/设备咨询请先 session_search 查历史讨论！
      之前买过的、推荐过的、踩过的坑都在历史对话里。
      搜到相关内容再回复，避免自相矛盾。

routing_table: |

  ▸=== 命理 / 人生决策 / 心理 ===
  ▸ 人生决策/职业规划/八字/命理 → load three-mirrors + karpathy-llm-wiki → 分析存档到存档库/wiki/分析/
  ▸ 心理情绪/焦虑/抑郁/焦虑/咨询/心理 → load psych-profile
  ▸ 关系分析/人际关系/亲密关系/矛盾 → load ljg-relationship + psych-profile
  ▸ 身心健康/药物/睡眠/冥想 → load psych-profile

  ▸=== 阅读 / 学习 / 知识 ===
  ▸ 读书/拆书/读一本书/这本书在讲什么 → load ljg-book + ljg-read + weread-skills
  ▸ 学习成长/学习方法/记忆/Anki/闪卡 → load encoding-first + english-learning-system
  ▸ 思维模型/概念深钻/概念解剖 → load ljg-think + ljg-learn + karpathy-llm-wiki
  ▸ 知识检索/查知识库/我记得/之前学过 → load karpathy-llm-wiki + gbrain-workflows + recall
  ▸ 英语学习/背单词/英语课/EF → load english-learning-system + ljg-word
  ▸ 论文/读论文/学术文献 → load ljg-paper + ljg-paper-river + paper-lookup

  ▸=== 创作 / 写作 / 表达 ===
  ▸ 网文创作/写小说/日更/写书 → load story + novel-craft
  ▸ 网文扫榜/拆文/市场分析 → load story-long-scan + story-long-analyze / story-short-scan + story-short-analyze
  ▸ 短篇写作/知乎盐选/短故事 → load story-short-write
  ▸ 网文封面/封面生成 → load story-cover
  ▸ 网文审查/去AI味 → load story-review + story-deslop
  ▸ 写作/深度文章/观点输出 → load ljg-writes + ljg-card
  ▸ 演讲/演示/PPT → load ljg-present + pptx-generator / ppt-master
  ▸ 做图/卡片/海报/可视化 → load ljg-card + taste-skill + ian-xiaohei-illustrations
  ▸ 白话说/解释/降维 → load ljg-plain

  ▸=== 投资 / 财经 / 赚钱 ===
  ▸ 投资理财/股票/基金/A股/行情 → load three-mirrors + 查 Jin10 财经数据（mcp_jin10_*）
  ▸ 投资分析/项目评估/币圈/融资 → load ljg-invest
  ▸ AI赚钱/GitHub变现/Fiverr → load ai-monetization + cross-border-payments
  ▸ 二手转卖/闲鱼/回血 → load marketplace-seller

  ▸=== 时事 / 资讯 / 科技 ===
  ▸ 时事资讯/新闻/今天发生了什么 → load daily-news-briefing
  ▸ AI资讯/AI日报/今天AI圈/大模型发布 → load aihot + ai-frontier-scout
  ▸ 舆情/最近大家都在说什么/舆论 → load last30days（搜Reddit/X/B站/知乎等）

  ▸=== 职业 / 求职 ===
  ▸ 求职/找工作/跳槽/简历 → load career-ops + job-scout
  ▸ 跨境收款/出海赚美元/收款 → load cross-border-payments

  ▸=== 开发 / 工程 / AI ===
  ▸ 编程开发/TDD/重构 → load ponytail + test-driven-development + build-your-own-x
  ▸ 代码审查/PR/代码质量 → load hermes-features（文档优先）+ code review 流程
  ▸ 架构分析/系统设计/拆解 → load prism
  ▸ 搭个自动化/循环任务/Loop → load loop-builder
  ▸ 调API/找接口/Public APIs → load public-apis
  ▸ 科研绘图/数据可视化/论文配图 → load scipilot-figure-skill
  ▸ 项目规划/任务拆解/进度跟踪 → load planning-with-files
  ▸ 逻辑推理/约束求解/Z3 → 走 chiasmus MCP（mcp_chiasmus_*）

  ▸=== MCP 工具（底层能力，按场景触发） ===
  ▸ 财经行情/美黄金/外汇/日历 → mcp_jin10_*（get_quote, get_kline, 日历等）
  ▸ 八字/紫微/占卜/黄历/择日 → mcp_mingyu_*（bazi, ziwei, almanac 等）
  ▸ 求职/简历/猎聘 → mcp_liepin*
  ▸ 网页搜索/深度内容 → mcp_exa_*（web_search_exa, web_fetch_exa）
  ▸ 知识库检索/大脑搜索 → mcp_gbrain_*（think, query, recall）
  ▸ 记忆存储/检索 → mcp_agentmemory_*（recall, save, smart_search）
  ▸ 空间操作/桌面环境 → mcp_agent_workspace_*

  ▸=== 文档 / 办公 / 输出 ===
  ▸ 做文档/Word/报告/合同 → load minimax-docx + minimax-pdf
  ▸ 做表格/Excel/数据/报表 → load minimax-xlsx
  ▸ 做演示/PPT/幻灯片/路演 → load pptx-generator / ppt-master + ljg-present
  ▸ PDF处理/读PDF/提取文本 → load pdf + markitdown-pdf
  ▸ 双语对照/翻译/中英 → load ljg-read（伴读模式）

  ▸=== 知识管理 / 笔记 ===
  ▸ 知识管理/Obsidian/FlowUs/Seek/wiki维护 → load karpathy-llm-wiki + seek-sync + docgraph + obsidian-cli
  ▸ 记忆管理/记得/存档/回顾/忘记 → load recall + remember + forget + memory-architecture
  ▸ 复盘/回顾/今天做了什么 → load recap + session-history + evening-review

  ▸=== 系统 / 运维 / Hermes 自身 ===
  ▸ CLI配置/排障/Hermes自身/装插件 → load hermes-admin + hermes-features + hermes-workspace-guide
  ▸ 服务器/Linux/系统运维 → load hermes-admin
  ▸ 安全审计/MCP审计/密钥轮换 → load audit-mcp + rotate-secrets + spam-trap
  ▸ Skills管理/新skill/技能整理 → load skill-creator + skill-manager + skill-vetter
  ▸ Agent协作/多agent工作流 → load agent-collaboration + git-agent-pair

  ▸=== 生活 / 购物 / 消费 ===
  ▸ 耳机/HiFi/音响/选耳机 → load headphone-science + hifi-system-building
  ▸ 京东购物/比价/商品 → load jd-shopping-guide
  ▸ 找资源/免费资源/看电影 → load fmhy-scout
  ▸ 旅行/博物馆/古建/出发前功课 → load ljg-travel
  ▸ 宠物/猫/云云/米米 → 无专用 skill，直接回答
  ▸ 手办/模型/GK → 无专用 skill，直接回答

  ▸=== 元能力（自动触发，不直接路由） ===
  ▸ 学到教训/踩坑/翻车 → self-evolution（自动记录 lessons.md + patterns.json）
  ▸ Token费用/余额查询 → token-cost-calc（自动每20轮查余额）
---


## 规则: auto-pattern-172848 (auto-from-evolution)

**目的:** 避免重复违规：用户发的 token/key/密码等完整值，禁止用 ... 或任何形式截断。terminal 命令中必须使用完整真实值。触发特征：涉及 ghp_/sk-/token/key/密码 等词汇时尤其警惕。
**来源:** self-evolution patterns.json (置信度 4)
**生成时间:** 2026-06-11 17:28

```yaml
- name: auto-pattern-172848
  description: "用户发的 token/key/密码等完整值，禁止用 ... 或任何形式截断。terminal 命令中必须使用完整真实值。触发特征：涉及 ghp_/sk-/token/key/密码 等词汇时尤其警惕。"
  triggers:
    keywords: ["禁止截断"]
  action: block
  block_message: "🚫 自动拦截：用户发的 token/key/密码等完整值，禁止用 ... 或任何形式截断。terminal 命令中必须使用完整真实值。触发特征：涉及 ghp_/sk-/token/key/密码 等词汇时尤其警惕。（此规则由 self-evolution 自动生成）"
```

## 规则: auto-pattern-225249 (auto-from-evolution)

**目的:** 避免重复违规：说了3次都不改→上插件+enforcer。已装hermes-time-perception插件(每轮自动注入时间)+enforcer #19(提到时间词先查date)。教训：同类型问题第3次还犯就走插件拦截，别再用文本规则。
**来源:** self-evolution patterns.json (置信度 3)
**生成时间:** 2026-06-12 22:52

```yaml
- name: auto-pattern-225249
  description: "说了3次都不改→上插件+enforcer。已装hermes-time-perception插件(每轮自动注入时间)+enforcer #19(提到时间词先查date)。教训：同类型问题第3次还犯就走插件拦截，别再用文本规则。"
  triggers:
    keywords: ["时间感失准"]
  action: block
  block_message: "🚫 自动拦截：说了3次都不改→上插件+enforcer。已装hermes-time-perception插件(每轮自动注入时间)+enforcer #19(提到时间词先查date)。教训：同类型问题第3次还犯就走插件拦截，别再用文本规则。（此规则由 self-evolution 自动生成）"
```