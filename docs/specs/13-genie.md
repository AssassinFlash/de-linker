# #13 Genie - Linker's AI assistant

依据：`docs/research/2026-10-09/old-repo-006-target-architecture.md`（工具契约与走查）、`platform-ai-shopping-assistants.md`（对标骨架）、`reusable-commerce-agent-components.md`、`knowledge-audit.md`、`name-check.md`、AGENTS.md §1–§3。

## 产品定义
客户从产品分类页、产品页、Lösungsentwurf 页、账户页或常驻入口打开 Genie；用自然语言给出条件（行业顺序：项目类型含加装 → 相数 → kWp/kW → HV/48 V 与 kWh → 备用 → 接口），Genie 返回合格产品卡（与正文同一集合、每张带"为什么合格"与配对状态）、对比表、一个决定性追问（可跳过），并能执行动作：加入 Lösungsentwurf、加入保存的方案、打开配置器（预填）、查看询盘状态（登录）、转人工（一句团队邮箱 + 摘要）。公司、服务、物流类问题只返回团队邮箱句。首条消息："Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system." / "Hallo, ich bin Genie, der KI-Assistent von Linker. Sie chatten mit einem KI-System."

## 三层
### A. Abilities（`plugins/linker-commerce`，`wp-abilities/v1`，命名空间 `Linker\Commerce\Abilities\`，一类一文件一 schema 一测试）
| ability | 输入 | 输出 |
|---|---|---|
| `linker/search-products` | `{device_class?, application?, phase?, pv_kwp?, kwh_min?, kwh_max?, brand?, series?, future?:['battery'], text?, with_pairings?:bool, lang, limit≤12}` | `{qualified:[{product_id, title, url, why:[{field,value,match:true|'unknown'}], facts:SelectionFactSet, commerce:{price_visible, price?, in_stock:bool, rfq_only:bool}, pairings?:[{product_id,verdict,conditions[],documents[]}]}], excluded:{by_reason:{...}}, unknown_fields:[...]}`。资格：device_class、application、phase、`pv_input_kw ≥ pv_kwp`、kWh 范围、已发布且在售；unknown 保留。排序：全匹配 > 含 unknown；再按 `|ac_power_kw − pv_kwp|`；再价格。 |
| `linker/get-product` | `{product_id, lang}` | 商品记录（图值、参数表、FAQ、文档 URL） |
| `linker/compare-products` | `{product_ids[2..4], lang}` | 维度行 × 商品列（电池能量与逆变器输出不混） |
| `linker/check-compatibility` | `{inverter_id, battery_id}` 或 `{product_ids}` | `{verdict: released|released_with_accessory|not_released|unknown, conditions[], documents[]}`（#8 的 compatibility.json） |
| `linker/size-hint` | `{pv_kwp?, annual_load_kwh?, phase?, backup?, plz?}` | `{summary, configurator_url(预填)}`（调 #14 引擎） |
| `linker/inquiry-status` | `{}`（登录） | 本账户询盘列表与状态 |
| `linker/handoff-team` | `{summary}` | `{sentence_en, sentence_de, mailto}` |
| `linker/search-knowledge` | `{query, lang, product_ids?}` | #10 的检索结果（块 ID、文档、页） |
只读 ability 匿名可调；写动作（加入 Lösungsentwurf、加入方案）不是 ability，由浏览器执行。

### B. 服务（`services/genie`，FastAPI + Pydantic AI）
- `POST /turn`（SSE 流）：`{conversation_id, messages[], locale, page_context:{type: category|product|draft|account|other, product_id?, draft_ids?}, user:{logged_in, partner?}}`。
- Agent：工具 = A 的 ability（HTTP，服务令牌只用于 inquiry-status 的用户上下文透传，不持 WP 写权限）；每轮 ≤4 次工具调用；strict 结构化输出 `{language, blocks:[{type:'text', text, refs:[fact_id]} | {type:'ask', field, options[]} | {type:'cards', product_ids[]} | {type:'compare', product_ids[]} | {type:'action', name, args} | {type:'handoff', summary}]}`；文本不含数字，写 `{fact:ID}` 占位。
- 运行时只有两个机制，都复刻自对标物：① **结构化输出**——模型只能产出带商品/事实 ID 的结构（Pydantic AI strict schema；非法结构由库拒绝并重答一次，再不行回退为"只列 qualified 卡 + 一个追问"的模板）；② **服务端填数（hydration，Rufus 的做法）**——文本里的数值由服务端从本轮工具结果填入。**没有文本改写，没有正则，没有审查层。** 范围外意图由模型按 schema 选择 handoff 块（提示词定义），不由代码判词。
- 水合：服务端把占位符替换为工具结果里的值与单位；卡片数据由壳按 product_id 再取。
- 模型：唯一对话模型 deepseek-flash，直连 DeepSeek 官方 API（`https://api.deepseek.com`，`DEEPSEEK_BASE_URL`/`GENIE_BASE_URL` 可覆盖；密钥 `DEEPSEEK_API_KEY`，`GENIE_API_KEY` 可覆盖，缺省从 `~/.config/terravolt-builder/deepseek.env` 回填；代码常量 `agent.py::CHAT_PROVIDER`，无供应商开关——业主裁定 2026-10-11 连同 Anthropic 选项一并删除）。aihubmix 密钥只用于 Jev 评审级联与 gemini-embedding-2 索引（#33/#10），与 Genie 对话无关。历史口径：deepseek-chat 在 2026-10-10 面板实测核验失败率 80%（R1/R2 流），修复提示词后 20–40%（claude-haiku-4-5）；deepseek-flash 直连的复跑口径见 `docs/acceptance/2026-10-11/13/deepseek-flash/`。
- 提示词 `prompts/{en,de}/system.md`：范围、口径、追问顺序、"每轮最多一个追问"、"不写数字"。
- 日志：每轮工具调用、核验结果、模型元数据、用户点赞/点踩（SQLite）。发布：`ops/release.sh`（版本目录 + current 软链 + 回滚）。

### C. 壳与前端（`plugins/linker-tools`：PHP `Linker\Tools\Genie\{Proxy,Entries}`；React 入口 `genie`）
- Proxy：`linker-ai/v1/genie/turn` → 服务（鉴权、locale、page_context、conversation_id、流式回传）；会话存储用 WP 原生：匿名以 cookie 绑定的自定义文章类型 `linker_conversation`，登录后归属用户（无自建表）。
- 保留策略（`Retention`）：`linker_conversation` 无界增长的收口（issue #67，GAP-18）——匿名/无邮箱会话 90 天过期清理（90 为起步值，改它属策略决定），注册用户（有邮箱的账号）会话保留。WP cron daily 扫描（`init` 懒登记），过期者逐个交给 Action Scheduler 一次性 job，删除走 `wp_delete_post`，不裸 SQL；job 执行时重查规则（扫描与执行之间可能被登录认领）。WP_Query 无法按 `post_author = 0` 过滤（核心对 author=0 不建条件，t67 实测），故扫描按日期分批（批 100、至多 20 批/日）后在 PHP 侧套用唯一规则实现；批界是保留线程（每用户一条）不堵塞清理的保证。
- Entries：产品分类页搜索框识别问句出现 "Ask Genie" 芯片；产品页芯片组（"What pairs with this model?" / "Was passt zu diesem Modell?"、"Compare with…"、"Documents"）；Lösungsentwurf 页（"Check my draft" / "Meinen Entwurf prüfen"、"What happens next?"）；账户页（"Where is my Proforma?" / "Wo steht meine Proforma?"）；常驻入口按页面类型给 2–3 条提示；首次点击才加载 JS。
- 组件：线程、消息、追问芯片、ProductCard（加入 Lösungsentwurf 并读回数量；加入方案；状态 pending/added/unverified/retry 在卡内、高度稳定）、CompareTable、Handoff。
- 文案：按 AGENTS.md 规则逐处写，EN/DE；对抗评审记录附 PR。

## 验收

旧 Advisor 的 190/191 只是症状。下面的保证与面板是**构建时的测试与评估集**（Rufus 用评估集和 LLM-as-judge 衡量质量，见 `docs/research/2026-10-09/platform-ai-shopping-assistants.md` 第 155、191 行），不是运行时组件；每条标注复刻来源。

### 结构保证（每条一个自动化测试，任一失败不合并）
- 模型输出里不出现数字，数值由服务端填入——复刻 Rufus 的 hydration（报告第 151、171 行）。
- 正文引用 ⊆ 本轮工具结果；卡片 ⊆ 正文引用；推荐 ⊆ `search-products` 的 qualified——复刻全部对标物的共同骨架 (a)"答案锚定平台目录与实时状态"（第 12、65 行）。
- 动作只能是允许列表里的，参数只来自工具结果——复刻 Accio 的"高风险动作需用户批准"（第 89 行）与 Sidekick 的小工具面。
- 范围外意图只有 handoff 块——业主 10-05 裁定，由提示词与 schema 实现。
- 披露句出现一次——复刻 Shopify（第 102 行）。
- 卡片反馈态在卡内、按钮高度不变——普通组件测试（Storybook），与助手无关。

### 行为面板（`docs/acceptance/genie-panel.md`，≥30 问，EN/DE 各一遍；由 #16 做成端到端套件）
覆盖：每个产品分类至少 2 问；四个入口各 2 问；条件齐全 / 冲突 / 事实不足 / 加装 / 48 V 与 HV / 备用 / 品牌偏好 / 对比 / 文档 / 库存与价格（登录与未登录）/ 范围外（公司、物流、安装）/ 多轮追问后出结果 / 动作（加入 Lösungsentwurf、加入方案、打开配置器、查询盘）。每问写明期望集合（从 `docs/research/2026-10-09/old-repo-live-catalogue-facts.md` 推导）与期望行为。通过标准：期望集合一致率 100%，追问不超过一个，披露句出现一次。

### 必过项（回归表 `docs/acceptance/protocol.md` §5 的 R1–R14）
- [ ] R1/R2（EN/DE 住宅三相 10 kWp 原句）：qualified ⊆ #7 的住宅三相集合；无 ETR/ESA；卡片 ⊆ 正文引用；一个追问。
- [ ] R3 冲突（12 kWp vs HS3-5K）、R4 事实不足（追问相数）、R5 产品页配对、R8 范围外只有邮箱句、R10 加装只列有放行的电池、R14 披露句。
- [ ] 核验注入测试五类全部拦截；核验失败率写入 PR。
- [ ] ProductCard：加入 Lösungsentwurf 的 pending/added/unverified/retry 与加入方案的 saving/saved/failed 均在卡内可见，按钮高度不变，内容不越过卡片（旧票 191 的验收行）；工作区与常驻 × 1440/390。
- [ ] 视觉验收：四入口 + 常驻 × 状态 × EN/DE × 1440/390。

## 变更记录
- 2026-10-11（#13 供应商收口，PR #61：6c271ce + 6224b4b + 本条）：**业主裁定落地——Genie 唯一对话模型 deepseek-flash，直连 DeepSeek 官方 API；Anthropic 选项连同 `GENIE_PROVIDER` 开关整个删除**（`agent.py::CHAT_PROVIDER` 常量，测试锁死陈旧变量无效），aihubmix 密钥只留 Jev 评审级联与 gemini-embedding-2 索引（#33/#10）。端点适配实测：思考型模型（`reasoning_content` 回传）、`json_object` 支持无栅栏、`json_schema` 400、强制 `tool_choice` 400（`build_model` 以 DeepSeekProvider + profile 声明降级为 auto）。复跑 11 行（新增 R1 原句）全 grounded、零回退，存档 `docs/acceptance/2026-10-11/13/deepseek-flash/`；**核验失败率：行级（§B 口径）0/11 = 0% < 5%，默认成立**；生成级 3/14 ≈ 21% 并列记录（失败原因按设计不落盘）。Jev 级联首次真跑（jev-1.13 首道 + deepseek-flash 直连升级，gemini-3.8-flash 按裁定全部清除）：11 轮 30 问与确定性核验一致 29/30 ≈ 96.7%，唯一分歧为试点构造歧义（R5），判据与驱动进仓库（`eval/judges/turns.py`/`pilot.py`/`tests/test_turns.py`），报告 `docs/acceptance/2026-10-11/13/jev-pilot.md`。DE 截图因旧 shot 含旧模型回答重拍（`.scratch/t13-shots/home-de-{1440,390}-panel-ds.png`）。收口检查：`just check` exit 0、`just test` exit 0（php 124+21、vitest 61、e2e 10、pytest 139+112+87+21+103）。Leftovers 不变（同上条，归 #16）。
- 2026-10-11（#13 收口）：评审修复轮完成（PR #61：工程项 4541bd7 + Spec 必改 1–4 2b39746）。§B 默认模型已切 Anthropic 并落代码（`provider_name()`；依据：DeepSeek 实测核验失败 80%、提示词修复后 20–40%，超 §B 的 5% 线）。范围外轮次先调 handoff-team，邮箱句以 `{fact:handoff.sentence_*}` 进 handoff 块并水合。pairing 问句走逆变器侧 `with_pairings` 搜索（pairings 载荷含 documents[]）。复跑 10 行（R2 EN/DE 含 cards、R5 七放行电池+文件、R8/R14 邮箱句、R10 加装链、r3/r4/r11/r13 拼写数字类）全部过线，存档 `docs/acceptance/2026-10-11/13/`；DE 截图重拍归档。**Leftovers（按 PR #61 评审裁定归类）**：R12 回退可接受（不再排队）；R7 登录路径与知识索引导入归 #16；消息持久化 reload 行为归 #16；服务令牌/用户上下文透传归 #16（完成前 AbilityClient 保持匿名、不配 token）；面板 ≥30 问的端到端持续套件归 #16；复跑残余核验失败率（13/23）记 PR，作为 §B 默认模型的持续依据。
- 2026-10-09（#5）：Genie 服务的地址在选项 `linker_genie_url`：本地由 `just serve <name>` 写入 `http://127.0.0.1:<端口>`，线上由切换（#17）写入 VPS 地址；壳的 Proxy 从这个选项读。
- 2026-10-11（#67，GAP-18）：新增 `Linker\Tools\Genie\Retention`。WordPress 核心对自定义文章类型没有过期机制（只有回收站按 `EMPTYTRASH_DAYS` 的另一套清理），扫描是本插件的；调度、队列、删除全部原生：WP cron daily + Action Scheduler 一次性 job + `wp_delete_post`。验收：单元 `RetentionTest`（10 项，含批界与认领竞争分支）+ 实例集成 `ConversationRetentionTest`（真实 `linker_conversation` 夹具：cron 钩子触发扫描，过期匿名被排 job 并经 `ActionScheduler_QueueRunner` 执行删除；新线与已认领线保留）。
