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
- Ability 调用的瞬态失败重试：5xx 与连接层异常（httpx `TransportError`）退避重试（3 次尝试、指数退避 0.25 s/0.5 s），仍失败抛 `AbilityError` 进既有兜底——失败写入轮次 meta（`fallback`/`failures`），不静默、不从服务层 500 逃逸（`abilities.py::AbilityClient._get`）。WordPress 侧的对象缓存（Redis）抖动是这一失败的主要历史来源：实例的 drop-in 现以 `WP_REDIS_GRACEFUL` 运行（规格 5、17），读失败降级为请求内缓存而非杀请求。
- Agent：工具 = A 的 ability（HTTP，服务令牌只用于 inquiry-status 的用户上下文透传，不持 WP 写权限）；每轮 ≤4 次工具调用；strict 结构化输出 `{language, blocks:[{type:'text', text, refs:[fact_id]} | {type:'ask', field, options[]} | {type:'cards', product_ids[]} | {type:'compare', product_ids[]} | {type:'action', name, args} | {type:'handoff', summary}]}`；文本不含数字，写 `{fact:ID}` 占位。
- 运行时只有两个机制，都复刻自对标物：① **结构化输出**——模型只能产出带商品/事实 ID 的结构（Pydantic AI strict schema；非法结构由库拒绝并重答一次，再不行回退为"只列 qualified 卡 + 一个追问"的模板）；② **服务端填数（hydration，Rufus 的做法）**——文本里的数值由服务端从本轮工具结果填入。**没有文本改写，没有正则，没有审查层。** 范围外意图由模型按 schema 选择 handoff 块（提示词定义），不由代码判词。
- 水合：服务端把占位符替换为工具结果里的值与单位；卡片数据由壳按 product_id 再取。
- 模型：唯一对话模型 deepseek-flash，直连 DeepSeek 官方 API（`https://api.deepseek.com`，`DEEPSEEK_BASE_URL`/`GENIE_BASE_URL` 可覆盖；密钥 `DEEPSEEK_API_KEY`，`GENIE_API_KEY` 可覆盖，缺省从 `~/.config/terravolt-builder/deepseek.env` 回填；代码常量 `agent.py::CHAT_PROVIDER`，无供应商开关——业主裁定 2026-10-11 连同 Anthropic 选项一并删除）。aihubmix 密钥只用于 Jev 评审级联与 gemini-embedding-2 索引（#33/#10），与 Genie 对话无关。历史口径：deepseek-chat 在 2026-10-10 面板实测核验失败率 80%（R1/R2 流），修复提示词后 20–40%（claude-haiku-4-5）；deepseek-flash 直连的复跑口径见 `docs/acceptance/2026-10-11/13/deepseek-flash/`。
- 提示词 `prompts/{en,de}/system.md`：范围、口径、追问顺序、"每轮最多一个追问"、"不写数字"。
- 日志：每轮工具调用、核验结果、模型元数据、用户点赞/点踩（SQLite）。发布：`ops/release.sh`（版本目录 + current 软链 + 回滚）。

### C 之后：产品分类页的搜索框（票 #68）

markup 归 archive 的 LC 模板（#16 重建），行为与数据归本票，三件各自可独立复核：

- **芯片（可挂载部件）**：`[linker_genie_ask]`（`Linker\Tools\Genie\Entries::ask_chip()`）
  打印一个 `hidden` 的 `button`（`data-linker-genie-open data-linker-ask-genie`，标签 "Ask Genie"
  / "Genie fragen"）。挂载点=archive 模板里 `[linker_catalog_head]` 的 `.wb-bar`（搜索表单旁；
  #16 集成）。不带 JS 时它一直隐藏，搜索框就是原生表单。
- **JS**：`plugins/linker-tools/assets/search-ask.js`（纯 asset，无构建）。绑定 `#search-box`
  （线上锚点）与芯片；问句判定=含 `?` 或问句/请求开头词（EN+DE 双方言，≥8 字符，型号与品号
  不命中）；命中时显示芯片。芯片点击只广播一次 `linker-genie-ask`，携带原问句；
  与 PDP Ask 共用 `Entries.php` 的单一 dock loader。loader 保留待交付问句、只 boot 一次，
  等 `App.tsx` 安装监听器并报告 `linker-genie-ready` 后，清空待交付状态并发出一次
  `linker-genie-open`（含问句）。圆钮/商城开钮走同一 loader 的无问句打开，不主动发送消息。
  App 先恢复已有对话，再将首问追加一次；Hide/open 通过 `linker-genie-state` 回传壳层，
  同步 mount 的 hidden 与入口 aria-expanded。不再写 pending 属性或另点一次圆钮。
  **加载失败协议**：应用包或任一依赖加载失败时，loader 复位 `loaded`、移除本批失败脚本、
  在 mount 里显示可见错误面（"Genie could not load." / "Genie konnte nicht geladen werden."
  与 "Try again" / "Erneut versuchen"，来自 dock payload）；排队首问保留，重试点击按原问句
  交付一次；成功仍只加载一次应用，失败的应用脚本永不执行（无依赖完成→不追加应用脚本）。
  提交路径：问句→与芯片同路（preventDefault）；其余查询→`linker/v1/catalog-search?q=&limit=2&lang=`
  恰好一个命中则直达产品页，否则原生 GET 交回 archive（`q` 过滤，CatalogFilters）。
  端点超时/失败一律回落到原生提交。
- **数据端点**：`GET /wp-json/linker/v1/catalog-search?q=&limit=&lang=`（`Linker\Commerce\Catalog\CatalogSearch`
  + `CatalogSearchController`，匿名可缓存）。匹配=型号/品号归一化（去 `- . /` 与空白、小写）后
  对商品 name+SKU 做包含，集合=已发布且 catalog-visible 的商品（Woo 隐藏商品不可枚举），
  顺序=目录顺序，limit 1..12（默认 8），q 最短 2 字符（`rest_invalid_param`/`rest_missing_callback_param`）。
  返回 `{query, items:[{id,title,sku,url,facts}]}`，`facts` 即 #7 的 SelectionFactSet（同一天然层；
  无价格——端点匿名且可缓存，价格在登录门后）。`?lang=en|de` 由 linker-i18n 的 RestLang 生效
  （德语返回德语孪生与 `/de/…` 地址）。
  archive 的 `q` 过滤与端点共用 `CatalogSearch::normalize()/matches()`（一条规则一处实现）。
- **`?s=` 结果页范围（原 GAP-1 尾项，2026-10-14 按线上复核收回）**：站内搜索的主查询若**未指名 post_type**，
  限定为 `post`（`Linker\Commerce\Products\SearchScope`，`pre_get_posts`）。
  依据：线上旧实现把隐式搜索限定为文章，结果页是博客文章模板（带图文章卡、无分页）；
  目录商品由目录搜索框（`q` 与 `linker/v1/catalog-search`）承担，不进 `?s=`。
  2026-10-14 线上复核（缺陷族 17、23）确认当前线上 `?s=PV` 把商品渲染成文章卡并分页，
  与旧线上 7 篇带图文章卡不符；本条因此从 `product`+`post` 收回为文章。
  显式指名 post_type 的请求（集成、单类型搜索）不受影响。页面、LC 模板、attachment、商品永不进隐式结果。

### C. 壳与前端（`plugins/linker-tools`：PHP `Linker\Tools\Genie\{Proxy,Entries}`；React 入口 `genie`）
- Proxy：`linker-ai/v1/genie/turn` → 服务（鉴权、locale、page_context、conversation_id、流式回传）；会话存储用 WP 原生：匿名以 cookie 绑定的自定义文章类型 `linker_conversation`，登录后归属用户（无自建表）。
- 保留策略（`Retention`）：`linker_conversation` 无界增长的收口（issue #67，GAP-18）——匿名/无邮箱会话 90 天过期清理（90 为起步值，改它属策略决定），注册用户（有邮箱的账号）会话保留。WP cron daily 扫描（`init` 懒登记），过期者逐个交给 Action Scheduler 一次性 job，删除走 `wp_delete_post`，不裸 SQL；job 执行时重查规则（扫描与执行之间可能被登录认领）。WP_Query 无法按 `post_author = 0` 过滤（核心对 author=0 不建条件，t67 实测），故扫描按日期分批（批 100、至多 20 批/日）后在 PHP 侧套用唯一规则实现；批界是保留线程（每用户一条）不堵塞清理的保证。
- Entries：产品分类页搜索框识别问句出现 "Ask Genie" 芯片（见下；**条目只此一枚**——业主 2026-10-13 再确认：线上那排里的 batch item numbers 与 nameplate photo 不补齐）；产品页芯片组（"What pairs with this model?" / "Was passt zu diesem Modell?"、"Compare with…"、"Documents"）；Lösungsentwurf 页（"Check my draft" / "Meinen Entwurf prüfen"、"What happens next?"）；账户页（"Where is my Proforma?" / "Wo steht meine Proforma?"）；常驻入口按页面类型给 2–3 条提示；首次点击才加载 JS。
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
- 2026-10-14（线上复核族 17、23）：`?s=` 隐式主查询从 `product`+`post` 收回为 `post`。证据：旧线上 `?s=PV`（EN 与 DE）是 7 篇带图博客卡、无分页；当前线上同查询把 GoodWe ESA 商品渲染成文章卡并分页（1 2 3 … 8）。目录搜索仍走 `q` 与 `linker/v1/catalog-search`，不走 `?s=`。显式指名 post_type 的请求不动。
- 2026-10-13（登记册 C2，PR #96 交回）：未登录德语「Wo steht meine Proforma?」不再能落到团队邮箱句。`facts.py` 已把 inquiry-status 的 401 记成 `inquiry.login_required`；提示词（`prompts/de/system.md`、`prompts/en/system.md`、`agent.py` 的每轮提醒）要求该事实只回答登录句，不得调用 handoff-team。grounding 拒掉邮箱句与任何其它形状，`template.login_required` 是兜底的唯一句子。兜底模板的其余两形留在协议集合内：有合格商品时只出合格卡片且正文引用它们，德语行不混英文功能词；无可引用事实时，本轮已有 handoff 句就出该邮箱句，仅当 handoff-team 没跑时出降级声明。判分测试：`tests/test_cycle.py`、`tests/test_ground.py`、`tests/test_agent.py`。
- 2026-10-11（#16 回归套件段：R7 登录路径与消息 reload 行为落地）：
  - **消息 reload = 恢复线程**（原为"归 #16"）。理由：会话本来就是这个站点自己的记录（`linker_conversation` 文章，cookie 或登录用户绑定），而规格 §C 让客户从分类页／产品页／Lösungsentwurf／账户页四个入口反复打开同一个 Genie——刷新或换页就清空，等于把已建好的上下文丢掉。实现：`Proxy::turn` 把这一轮浏览器发来的 messages 与该轮 SSE 原文写在该会话文章的 meta（`Thread`，上限 60 条），新增只读路由 `GET linker-ai/v1/genie/conversation` 读回（`Conversations::existing_id()`——读回永不新建会话文章），前端挂载时 `readThread()` 用与实时轮次**同一个**解析器还原线程与最后一轮的可渲染块（`assistantMessage()` 是"助手消息正文"的唯一实现）。
  - **R7 登录路径：用户上下文透传落地**（原为"完成前 AbilityClient 保持匿名、不配 token"）。实现即 §B 已写的设计——服务令牌只用于 `linker/inquiry-status`：壳为登录客户签一个两分钟有效（`UserContext::TTL` = 120 秒，无已用标记）的 HMAC 令牌（`UserContext`，`wp_salt('auth')`），随轮次交给服务，服务只在那一个 ability 调用上以 `X-Linker-User-Context` 送回，WordPress 只对 `/wp-abilities/` 请求、且仅在校验签名与有效期后采信（`determine_current_user` 上已有会话时忽略）。未登录或不带令牌时该 ability 仍回 401 → `login_required` 事实，行为与旧文档一致。
  - 回归：`tests/e2e/specs/genie.spec.ts`（服务层 R1–R14 + Jev 级联判分）、`genie-dock.spec.ts`（披露句、R13 芯片带 product_id、R7 登录、reload 恢复）。
- 2026-10-11（#13 供应商收口，PR #61：6c271ce + 6224b4b + 本条）：**业主裁定落地——Genie 唯一对话模型 deepseek-flash，直连 DeepSeek 官方 API；Anthropic 选项连同 `GENIE_PROVIDER` 开关整个删除**（`agent.py::CHAT_PROVIDER` 常量，测试锁死陈旧变量无效），aihubmix 密钥只留 Jev 评审级联与 gemini-embedding-2 索引（#33/#10）。端点适配实测：思考型模型（`reasoning_content` 回传）、`json_object` 支持无栅栏、`json_schema` 400、强制 `tool_choice` 400（`build_model` 以 DeepSeekProvider + profile 声明降级为 auto）。复跑 11 行（新增 R1 原句）全 grounded、零回退，存档 `docs/acceptance/2026-10-11/13/deepseek-flash/`；**核验失败率：行级（§B 口径）0/11 = 0% < 5%，默认成立**；生成级 3/14 ≈ 21% 并列记录（失败原因按设计不落盘）。Jev 级联首次真跑（jev-1.13 首道 + deepseek-flash 直连升级，gemini-3.8-flash 按裁定全部清除）：11 轮 30 问与确定性核验一致 29/30 ≈ 96.7%，唯一分歧为试点构造歧义（R5），判据与驱动进仓库（`eval/judges/turns.py`/`pilot.py`/`tests/test_turns.py`），报告 `docs/acceptance/2026-10-11/13/jev-pilot.md`。DE 截图因旧 shot 含旧模型回答重拍（`.scratch/t13-shots/home-de-{1440,390}-panel-ds.png`）。收口检查：`just check` exit 0、`just test` exit 0（php 124+21、vitest 61、e2e 10、pytest 139+112+87+21+103）。Leftovers 不变（同上条，归 #16）。
- 2026-10-11（#13 收口）：评审修复轮完成（PR #61：工程项 4541bd7 + Spec 必改 1–4 2b39746）。§B 默认模型已切 Anthropic 并落代码（`provider_name()`；依据：DeepSeek 实测核验失败 80%、提示词修复后 20–40%，超 §B 的 5% 线）。范围外轮次先调 handoff-team，邮箱句以 `{fact:handoff.sentence_*}` 进 handoff 块并水合。pairing 问句走逆变器侧 `with_pairings` 搜索（pairings 载荷含 documents[]）。复跑 10 行（R2 EN/DE 含 cards、R5 七放行电池+文件、R8/R14 邮箱句、R10 加装链、r3/r4/r11/r13 拼写数字类）全部过线，存档 `docs/acceptance/2026-10-11/13/`；DE 截图重拍归档。**Leftovers（按 PR #61 评审裁定归类）**：R12 回退可接受（不再排队）；R7 登录路径与知识索引导入归 #16；消息持久化 reload 行为归 #16；服务令牌/用户上下文透传归 #16（完成前 AbilityClient 保持匿名、不配 token）；面板 ≥30 问的端到端持续套件归 #16；复跑残余核验失败率（13/23）记 PR，作为 §B 默认模型的持续依据。
- 2026-10-09（#5）：Genie 服务的地址在选项 `linker_genie_url`：本地由 `just serve <name>` 写入 `http://127.0.0.1:<端口>`，线上由切换（#17）写入 VPS 地址；壳的 Proxy 从这个选项读。
- 2026-10-11（#67，GAP-18）：新增 `Linker\Tools\Genie\Retention`。WordPress 核心对自定义文章类型没有过期机制（只有回收站按 `EMPTYTRASH_DAYS` 的另一套清理），扫描是本插件的；调度、队列、删除全部原生：WP cron daily + Action Scheduler 一次性 job + `wp_delete_post`。验收：单元 `RetentionTest`（10 项，含批界与认领竞争分支）+ 实例集成 `ConversationRetentionTest`（真实 `linker_conversation` 夹具：cron 钩子触发扫描，过期匿名被排 job 并经 `ActionScheduler_QueueRunner` 执行删除；新线与已认领线保留）。
- 2026-10-11（#68，GAP-1）：搜索框收口——`[linker_genie_ask]` 芯片（#16 在 archive 模板挂载）、`assets/search-ask.js`（问句识别+直连/回落）、`linker/v1/catalog-search`（SelectionFacts 层、匿名可缓存、lang 感知）、`CatalogFilters` 增 `q`（与端点共用同一条匹配规则）、`SearchScope` 定 `?s=` 范围为 product+post（写进本规格 §C 之后）。顺带修 `Entries::script_deps()` 自引用（app 双载双挂）与 Genie app 的 pending-ask 通路。文案评审 docs/acceptance/2026-10-11/68/copy-review.md，验收 docs/acceptance/2026-10-11/68/README.md。
- 2026-10-12（#103）：ability 调用瞬态失败重试与兜底降级声明（`abilities.py`、`template.py::DEGRADED`）。评审站实例 e2e 期间的 PHP 错误日志记录了成片 `Predis\Connection\ConnectionException`，时刻与失败轮次一一对应——对象缓存抖动把 ability 打成 500，轮次跌进兜底模板且不声明降级。三层修复：实例 drop-in 以 `WP_REDIS_GRACEFUL` 运行（规格 5）；服务对 5xx/连接异常退避重试 3 次后才进兜底；兜底无可引用事实时明确声明本轮无法作答并给出重试与团队出路（EN/DE，文案对抗评审 `docs/acceptance/2026-10-12/103/copy-review.md`）。单测覆盖连接异常分支（`tests/test_abilities.py` 重试与放弃、`tests/test_cycle.py` 两次 ability 失败→降级声明）。
