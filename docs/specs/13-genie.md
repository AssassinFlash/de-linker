# #13 Genie - Linker's AI assistant

依据：`docs/research/2026-10-09/old-repo-006-target-architecture.md`（工具契约与走查）、`platform-ai-shopping-assistants.md`（对标骨架）、`reusable-commerce-agent-components.md`、`knowledge-audit.md`、`name-check.md`、AGENTS.md §1–§3。

## 产品定义
客户从产品分类页、产品页、Lösungsentwurf 页、账户页或常驻入口打开 Genie；用自然语言给出条件（行业顺序：项目类型含加装 → 相数 → kWp/kW → HV/48 V 与 kWh → 备用 → 接口），Genie 返回合格产品卡（与正文同一集合、每张带"为什么合格"与配对状态）、对比表、一个决定性追问（可跳过），并能执行动作：加入 Lösungsentwurf、加入保存的方案、打开配置器（预填）、查看询盘状态（登录）、转人工（一句团队邮箱 + 摘要）。公司、服务、物流类问题只返回团队邮箱句。首条消息："Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system." / "Hallo, ich bin Genie, der KI-Assistent von Linker. Sie chatten mit einem KI-System."

## 目标（业主 2026-10-17，#240；依据 `docs/research/2026-10-17-ai-assistants/`）

本节优先于上文的产品定义；实现票以本节为准。

1. **本职**：产品选型助手——找对产品 → 配对 → 文档 → Lösungsentwurf → 询盘。公司、物流、售后问题照旧一句话转团队，同时可一键"让 Linker 联系我"。全站只有 Genie 一个对话入口。
2. **理解（理解层，业主 2026-10-17，实测见 `docs/research/2026-10-17-jev-intent/`）**：每条消息先由代码对产品数据做确定性匹配（品牌 / 型号 / 系列 / SKU / 分类，EN/DE）；同时由 **Jev**（typesafe/jev-1.13，仅经 OpenRouter `/api/v1/systemone`）一次回答有类型的小问题——意图（找产品 / 配对兼容 / 文档参数 / 对比 / 选型 / 询盘状态 / 找人 / 公司物流服务 / 闲聊 / 其他）、是否问本页、是否找人或不满、是否需要追问；**代码按答案路由**：高置信（起始阈值 0.8）直接调对应工具（产品、文档向量检索、兼容、询盘状态、转人工），低置信交 deepseek-flash 决定；**deepseek-flash 只根据工具结果写回答**。实测意图准确率 97%（高置信 98%），"saj"判为找产品，每条约 2.6 秒、$0.00003。产品词永不当称呼。能读铭牌照片与附件（数据表、图纸；PDF 先转文字或页面图片，见 `docs/research/2026-10-17-deepseek-flash-vision/`）。**零件清单 → 产品**：粘贴、上传表格或拍照的清单逐行匹配，有疑问逐条问，一次填进 Lösungsentwurf。
3. **页面感知**：每轮带 URL、页面类型与对象 ID，服务端解析成页面的真实内容；打开即点名当前产品或分类；"这款"不用重打型号；每类页面（首页、产品、分类、解决方案、博客、FAQ、Lösungsentwurf、账户）至少两条本页建议。
4. **主动预览卡**（小卡片，不是完整对话）：首页、产品、分类、解决方案页。滚过主内容并停留约 8 秒出现；首页在滚过 hero 之后出现，话题展示 Genie 能做的事（报型号找产品、拍铭牌、上传清单、比较品牌）。每次访问最多一次；对话进行中不出现；关掉后该访客 30 天不再出现；表单、询盘、登录页不出现；手机端只在 Genie 圆钮上出标记；不抢焦点。阈值是起始值，由原型调定。
5. **替客户做事**：加入 Lösungsentwurf、存方案、打开配置器、查询盘。**对话内询盘**：Genie 起草，确认卡逐行显示将发送的内容（产品与数量、留言、是否附对话摘要、一个工作日内回复的承诺），只有客户点"发送"才发送，模型文字永远不能触发；访客在卡上填邮箱与姓名，与访客询盘表单一致。
6. **转人工**：客户要求找人，立即提供"让 Linker 联系我"；同一问题重复三轮时提议一次，不连续提议两次；承诺一个工作日内回复；已登录客户不再问联系方式；团队收到对话全文链接、摘要、所在页面与 Lösungsentwurf。
7. **记忆**：每个会话都保留，可切换、可清除、可发到自己的邮箱；访客的全部会话保存在本浏览器；登录后并入账户并跨设备可见。
8. **价格**：跟账号走，与产品页一致——已批准看净价，访客、待审、限制账号看不到。
9. **回答形态**：产品卡带图，参数在卡内展开，长回答不自动滚到底；每条回答后两到三个可点的下一步；首次接触（含预览卡）即可见 AI 标识与"可能出错"一句（EU AI Act 第 50 条）。
10. **首页 hero**：变体 B（就地展开），见 `docs/prototypes/2026-10-17-hero/DECISION.md`。

验收：业主同意的六条（任何品牌 / 型号词出产品；本页建议并能答本页问题；会话不丢；拍铭牌一步到产品；每个回答给下一步；不编造）+ `docs/research/2026-10-17-ai-assistants/INTL.md` §8 的 A1–A14 + `CN.md` 的补充验收。

对照题集（业主 2026-10-17 定 Genie 不换之后加）：`docs/research/2026-10-17-knocket/raw/trial/questions.json` 的 20 道 EN/DE 题，用 `raw/trial/genie.py` 对本地实例重跑。过关线：第 2、3、4、5、13 题（Knocket 答对的）和第 8 题（正确答案是 OCEAN 2 单相、三相都有，并按相数给出额定功率；见 TRIAL.md 文末更正），Genie 必须全部答对；20 题里零答错；第 1、9、10、14 题（#233 / #257 指出的失分）必须给出产品、手册里的步骤或数字，或者引向配置器，不能用兜底话术，也不能转给 sales@。#257 与 #233 合并后由本线重跑，结果记在这两张票上。

### 战役质量门槛与缺陷分级（#329 地图；#338 锁定，业主 2026-10-19 接受 grilling round 1 推荐值；业主可改）

**七条过关线**——任何一条不过即缺陷未清零，战役（#329）不得宣告完成：
1. 确定性产品词命中 100%：品牌/型号/系列/SKU/分类，EN/DE（对抗变体——错拼、大小写、连字符/空格——的处理策略与阈值按 #330 首轮实测数据另行定，dossier §1.1 判该区无先例）。
2. 回答 0 编造数字：每个数字可溯源到本轮工具结果、检索块或页面事实（`{fact}` 水合链为准）。
3. 100 题对照集 100/100（#336 扩集）：第 1/8/10/14 题必须给产品、手册步骤或配置器，不兜底、不转 sales@。
4. EN/DE 同结构：同题同判分；德语独立撰写、Sie 体（不是英文直译）。
5. 无静默降级：任何降级/失败在轮次 meta 与回答里显性可见；OpenRouter 失败显性暴露（AGENTS §5 铁律）。
6. 每条回答有下一步（≥1 个可点的后续）。
7. 询盘/联系只由客户点击发送（模型文字永不触发；`ground._no_sent_claim` 为证）。

延迟门槛：p95 ≤ 30 s，目标 ≤ 15 s（#336 埋测落地后生效；dossier §1.14——无竞品 SLO 先例，属自定线）。

**缺陷分级**（对抗批 #330–#335 的每条缺陷按此定级）：
- **P0**：错误事实到达客户（编造数字、错型号、价格出现在不该出现的账号/表面）、铁律破坏（价格泄漏、模型文字触发发送、静默换模型）、崩溃或空白 UI。修复阻断一切合并。
- **P1**：破坏过关线但不撒谎（确定性词未命中、旧话题条件串进新回答、SSE 断流后 UI 卡死无恢复、p95 超线、注入顺从迹象）。进当批修复队列，战役结束前必须清零。
- **P2**：体验损伤、有绕行（延迟形态、措辞、建议相关性弱）。记台账随批清。
每条缺陷按地图协议分层归因（确定性匹配 / Jev 路由 / 工具 / 检索 / 提示词 / 水合 / UI 状态 / i18n / 基础设施），并标注复刻 / 须自行设计（引 `docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md` 章节）。

**修复权边界**：触碰三条铁律（模型路由、价格门、询盘点击发送）或任何客户可见承诺/措辞基调的改动＝单独业主裁定；dossier 判"复刻"区内的实现改动＝执行者改、本线评审合并；dossier 判"须自行设计"区的改动＝修复票先写设计理由（引 dossier 对应节）再动手。

## 三层
### A. Abilities（`plugins/linker-commerce`，`wp-abilities/v1`，命名空间 `Linker\Commerce\Abilities\`，一类一文件一 schema 一测试）
| ability | 输入 | 输出 |
|---|---|---|
| `linker/search-products` | `{device_class?, device_classes?:[同枚举], application?, phase?, pv_kwp?, ac_power_min?, kwh_min?, kwh_max?, brand?, series?, future?:['battery'], text?, with_pairings?:bool, extreme?:smallest\|largest\|cheapest, lang, limit≤12}` | `{qualified:[{product_id, title, url, why:[{field,value,match:true\|'unknown'}], facts:SelectionFactSet, commerce:{price_visible, price?, price_line, price_reason?:login\|pending\|restricted\|project\|unpriced, in_stock:bool, rfq_only:bool}, pairings?:[{product_id,verdict,conditions[],documents[]}]}], excluded:{by_reason:{...}}, unknown_fields:[...], extreme?:{kind, applied, product_id?, field?:ac_power_kw\|usable_kwh\|nominal_kwh\|kwh, value?, model?, reason?:price_hidden\|none}}`。资格：device_class、application、phase、`pv_input_kw ≥ pv_kwp`、kWh 范围、已发布且在售；unknown 保留。`ac_power_min` 要求 `ac_power_kw ≥ N`，未知 AC 功率排除（极值是一项断言，未知值不能充当）。`device_classes` 是一组类别（电池两类），未知类别排除。排序：全匹配 > 含 unknown；再按 `|ac_power_kw − pv_kwp|`；再价格。`extreme` 改为在合格集上聚合：smallest/largest 取该下限对应的最小值或最大值，合格列表只留这一件；cheapest 只按该账号可见的价格排序，价格不可见时 `applied: false, reason: price_hidden`，不按隐藏价格排序（#368）。 |
| `linker/get-product` | `{product_id, lang}` | 商品记录（图值、参数表、FAQ、文档 URL） |
| `linker/compare-products` | `{product_ids[2..4], lang}` | 维度行 × 商品列（电池能量与逆变器输出不混） |
| `linker/check-compatibility` | `{inverter_id, battery_id}` 或 `{product_ids}` | `{verdict: released|released_with_accessory|not_released|unknown, conditions[], documents[]}`（#8 的 compatibility.json） |
| `linker/size-hint` | `{pv_kwp?, annual_load_kwh?, phase?, backup?, plz?}` | `{summary, configurator_url(预填)}`（调 #14 引擎） |
| `linker/inquiry-status` | `{}`（登录） | 本账户询盘列表与状态 |
| `linker/handoff-team` | `{summary}` | `{sentence_en, sentence_de, mailto}` |
只读 ability 匿名可调；带客户令牌时按该客户回答（价格，见「价格跟账号走」）。写动作（加入 Lösungsentwurf、加入方案）不是 ability，由浏览器执行。文档检索 `linker/search-knowledge` 不是 WordPress ability：它是服务自己的工具（见 B 与规格 10「唯一检索源」，#257）。

### B. 服务（`services/genie`，FastAPI + Pydantic AI）
- `POST /turn`（SSE 流）：`{conversation_id, messages[], locale, page_context:{type: home|product|category|solution|blog|faq|draft|account|other, url?, title?, product_id?, post_id?, category_id?, draft_ids?}, user:{logged_in, partner, context?}, attachments?:[{name, type, data}], readings?:[…]}`（`partner` 与 `context` 见「价格跟账号走」）（页面上下文见下文"页面感知"；`attachments` 与 `readings` 见"附件与铭牌"；`type` 另收 `text/csv` 与 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，reading 的 `kind` 另收 `list`，见"零件清单 → 产品"）。SSE 事件：`meta`、本轮每个附件一条 `attachment` 与一条 `reading`、每块一条 `block`、`done`。
- Ability 调用的瞬态失败重试：5xx 与连接层异常（httpx `TransportError`）退避重试（3 次尝试、指数退避 0.25 s/0.5 s），仍失败抛 `AbilityError` 进既有兜底——失败写入轮次 meta（`fallback`/`failures`），不静默、不从服务层 500 逃逸（`abilities.py::AbilityClient._get`）。WordPress 侧的对象缓存（Redis）抖动是这一失败的主要历史来源：实例的 drop-in 现以 `WP_REDIS_GRACEFUL` 运行（规格 5、17），读失败降级为请求内缓存而非杀请求。
- 文档检索：`linker/search-knowledge`（`{query, lang, product_ids?}`）在服务进程内读 VPS 上发布的 SQLite 索引（`linker_genie/knowledge.py`，规格 10「唯一检索源」）。路由的调用（`understand._run_calls`）和模型的工具调用走同一个 `knowledge.record`。模型读到的块文本里，每个数字都标成 `[nK=值]`；回答里写 `{fact:块ID.nK}`，水合时填入。答案依据的块由服务端加成文档链接（文档块，#233）。路由的文档检索失败时（编码或索引出错），这一轮直接进兜底，不会写出一个缺少所需文档的回答；同样不退回关键词。
- Agent：工具 = A 的 ability（HTTP；服务自己不持任何 WP 身份，只把客户的短时令牌带在按客户回答的 ability 上，见「价格跟账号走」）；每轮 ≤4 次工具调用；strict 结构化输出 `{language, blocks:[{type:'text', text, refs:[fact_id]} | {type:'ask', field, options[]} | {type:'cards', product_ids[]} | {type:'compare', product_ids[]} | {type:'action', name, args} | {type:'handoff', summary}]}`；文本不含数字，写 `{fact:ID}` 占位。
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
- **会话全部保留（#235，目标 7，验收 A9、A12）**——浏览器端存储与服务端记录的关系：
  - **记录只在服务端**：每个会话是一篇 `linker_conversation` 私有文章（线程在它的 meta，见 `Thread`）。浏览器不存对话内容，只存两把钥匙，都是 httponly、SameSite=Lax 的 cookie：`linker_genie_browser`（本浏览器的随机钥匙，32 位十六进制，128 位随机数）与 `linker_conversation`（当前会话 `id.HMAC 签名`，dock 与整页工作区共用它切换）。
  - **"访客的全部会话保存在本浏览器"的实现**：访客新开的每个会话都带 meta `linker_genie_browser` = 钥匙的 sha256（库里不存钥匙本身，读库拿不到能打开会话的 cookie）。列表 = 本浏览器钥匙标记的全部未归属会话 + 当前 cookie 指名的会话，按**最近活动**新→旧：meta `linker_genie_activity`（`Thread::ACTIVITY`，unix 时间）在新开会话和每轮回答完成时写入，命名与登录认领都不改它（它们改的是文章的修改时间，所以不用修改时间排序）；没有这条 meta 的旧会话排在后面、按开始时间。登录客户的列表同一规则。上限 `LIST_LIMIT` 40 条。钥匙只在第一次新开会话时生成；此前只有单一会话 cookie 的旧访客，下一次新开会话时把那个会话也打上钥匙，不丢。
  - **cookie 寿命跟保留策略走**：两枚 cookie 的有效期都是 `Retention::RETENTION_DAYS`（90 天），每次写入重新计时；钥匙在每次新开会话时重写，所以只要服务端还留着某个访客会话（开始后 90 天内），浏览器就还握着通往它的钥匙。服务端的清理规则不变（`Retention`：未归属会话开始 90 天后删除）。清掉浏览器 cookie 等于放弃这些访客会话（无法再认领），它们按 90 天规则清理。
  - **登录并入账户**：`wp_login`（账户页表单）与 `set_logged_in_cookie`（WooCommerce 注册后直接登录不触发 `wp_login`）两处都调用同一个认领：本浏览器钥匙标记的全部未归属会话 + 当前 cookie 的会话改归该用户，并删掉钥匙标记；**认领后浏览器换一把新钥匙**。此后它们属于账户：任何设备登录都列出（按作者查询），`Retention` 对有邮箱的账户不清理。**退出登录（`wp_logout`）**：清掉当前会话 cookie、换新钥匙，同一浏览器的下一个人从空白的访客开始，看不到账户的会话。**User Switching 不认领**：它在设置被切换用户的 auth cookie 前先写或清自己的 old-user cookie（`set_olduser_cookie` / `clear_olduser_cookie`），这一请求里的 `set_logged_in_cookie` 不当作本浏览器访客的登录。
  - **清除**：`DELETE linker-ai/v1/genie/conversations/<id>` 经 `Conversations::delete()` 用 `wp_delete_post(…, true)` 连同线程删除，之后不再作为任何上下文；只能删自己能用的（访客=本浏览器，登录=本人）；删的是当前会话时清掉当前 cookie，面板回到空白（登录客户回到最新的另一会话）。界面：每行一个删除标记（指向/聚焦时出现，触屏常显），行内确认"Delete this conversation permanently?"后才删。
  - **发到自己邮箱**（评审第 1 轮定的设计）：`POST linker-ai/v1/genie/conversations/<id>/email`（`ConversationMail`）。
    - 登录客户：直接发到账户邮箱（请求里的地址被忽略，回执告诉面板是哪个地址）。
    - 访客：**先确认地址**。请求带蜜罐 `website` 与签名起始时间（mount 的 `data-mail-started` / `data-mail-started-nonce`，`ConversationMail::stamp()`，与询盘、联系两扇门同一做法，至少 3 秒）；不过关的请求照常回 202 `confirm` 但什么都不发。过关则只发一封固定文案的确认邮件（`Linker\Commerce\Genie\ConfirmAddressEmail`），带一次性链接（`admin-post.php?action=linker_tools_genie_email&token=<id>.<64 位十六进制>`，库里只存 sha256，有效 `LINK_LIFETIME` = 24 小时，即 WordPress 密码重置链接的寿命），**不含任何对话内容**。链接被打开后才把对话发到这个地址，链接随即作废；之后跳回 Genie 整页并带 `genie_email=<结果>`，页面显示一行结果。
    - **限额**（`RateLimit`：选项表里每个窗口一行，判断与加一是同一条 UPDATE，并发请求不会越过上限）：每个连接每小时 3 次（`LIMIT`，同联系表单）；**全站每天 10 封**（`DAILY_CAP`，确认邮件与对话邮件合计，主机 100 封/24 小时四站共用的十分之一，询盘、审批、联系邮件留足余量）。超限直接拒绝（429，`throttled` / `capped`），不排队。
    - 内容是完整对话：存储的 messages + 最后一轮流里的文字块（`Thread::transcript()`，与壳的 `assistantMessage()` 同一规则），每条回答下列出它的卡片里的产品（名称链到产品页、型号，邮件语言；`Thread::PRODUCTS` 按回答文字的 sha1 记每轮卡片的产品 id）。
    - 邮件由 linker-commerce 发：linker-tools 在 `linker_tools_genie_send_conversation` 与 `linker_tools_genie_confirm_address` 两个过滤器上请求，`Genie\{ConversationEmail,ConfirmAddressEmail}`（WooCommerce 客户邮件，经 Outbox，From / Reply-To 为站点客户发件人 `Linker <sales@de-linker.com>`）只发给这一个地址、无 Bcc，语言跟页面。每次发送新建邮件对象：`WC_Email` 第一次读默认主题时把它缓存进 settings，复用会把第一封的语言带进下一封（g235 实测）。
    - 结果词一处定义：PHP `ConversationMail` 的常量（含 HTTP 映射），TS `EMAIL_OUTCOMES`（`src/genie/api/turn.ts`）。文案评审 `docs/acceptance/2026-10-18/235/copy-review.md`。
  - **侧栏不再因切换或新建而收起**：整页工作区宽屏（≥768 px）的侧栏是停靠的，新建、切换都保持访客摆放的开合；768 px 以下侧栏是盖在对话上的浮层，选中或新建后收起才看得见对话（与原型的手机规则一致）。dock 的新建从不收起 dock。
- 保留策略（`Retention`）：`linker_conversation` 无界增长的收口（issue #67，GAP-18）——匿名/无邮箱会话 90 天过期清理（90 为起步值，改它属策略决定），注册用户（有邮箱的账号）会话保留。WP cron daily 扫描（`init` 懒登记），过期者逐个交给 Action Scheduler 一次性 job，删除走 `wp_delete_post`，不裸 SQL；job 执行时重查规则（扫描与执行之间可能被登录认领）。WP_Query 无法按 `post_author = 0` 过滤（核心对 author=0 不建条件，t67 实测），故扫描按日期分批（批 100、至多 20 批/日）后在 PHP 侧套用唯一规则实现；批界是保留线程（每用户一条）不堵塞清理的保证。
- Entries（**各面的现行入口形态，2026-10-16 按实例取证重述**——原条目把产品页与账户页的入口写成芯片组，那两个芯片组的挂载钩子在现行 LiveCanvas 模板下不触发）。同一个组件两副形态：页面芯片（`linker-genie-chip`，`[linker_genie_chips]` 或注册在 Woo 钩子上的 `*_chips()` 打印）与常驻 dock 的开场提示（mount 的 `data-prompts`，随页面类型给 2–3 条）。入口逐面：
  - **产品分类页与商城**（`archive_product.html` 与 `shop_page.html`，各 [linker_products_head] 的 `.wb-acts` 与 [linker_products_actions] 的移动条两处）：搜索框识别问句出现的 "Ask Genie" 芯片（`[linker_genie_ask]` + `[linker_genie_chips page_type="category"]`）。**分类面条目只此一枚**——业主 2026-10-13 再确认：线上那排里的 batch item numbers 与 nameplate photo 不补齐。
  - **产品页**：工具行的 "Ask Genie" 按钮（`[linker_pdp_tools]` 的 `[data-pdp-ask]`，`pdp-ui.js` 广播 `linker-genie-ask`）与项目选择按钮（`[linker_pdp_project_choices]` 三阶段）；三条点名本产品的问句（与预览卡同一组，见"页面感知"）以 dock 的开场提示出现（`data-page-type="product"`），**不是页面芯片**——#174 重设计的既定入口形态，验收基准是原型变体 A 的 `.tools-row` 与 `.plan-with`。
  - **Lösungsentwurf（购物车）**：`Entries::draft_chips()` 挂在 `woocommerce_before_cart`——`[woocommerce_cart]` 走 Woo 自己的 `cart.php`，该钩子真的触发：芯片 "Check my draft" / "Meinen Entwurf prüfen"、"What happens next?" / "Wie geht es weiter?"。
  - **空 Proforma 请求页**：登录门的 Genie pill（`LoginGate::genie_pill()`，`data-linker-genie-open`），#184 验收过的 `gates.html?gate=empty-proforma` 形态。
  - **账户页**：无页面芯片（账户面渲染自己的 overview，不触发 `woocommerce_account_dashboard`）；入口是常驻 dock——mount 带 `data-page-type="account"`，开场提示即 "Where is my Proforma?" / "Wo steht meine Proforma?" 与 "What happens next?"。**账户面条目只此一枚**。
  - **站头站脚**：`/genie/` 的链接（页头菜单卡、移动链接、站脚 Plan with Linker 面板）与全站常驻 dock；工作区页（`/genie/`）由 `[linker_genie_workspace]` 承载。
  - **首页 hero**（#232）：首页 `.hero-cinematic` 自己的输入框、发送、胶囊、拍照、附件与语音按钮；见下节"首页 hero"。
  - `Entries::*_chips()` 仍是可挂载的钩子（Woo 模板面：`woocommerce_single_product_summary` / `woocommerce_account_dashboard`），当前 LiveCanvas 模板不触发；`[linker_genie_chips page_type="…"]` 可随时显式挂载。首次点击才加载 JS。
- 组件：线程、消息、追问芯片、ProductCard（加入 Lösungsentwurf 并读回数量；加入方案；状态 pending/added/unverified/retry 在卡内、高度稳定）、CompareTable、Handoff。
- 文案：按 AGENTS.md 规则逐处写，EN/DE；对抗评审记录附 PR。

### 首页 hero（#232，实现目标第 10 条；业主 2026-10-17 选变体 B · 就地展开，`docs/prototypes/2026-10-17-hero/DECISION.md`）

- **未交互时不动**：首页 hero 是 LiveCanvas 页面自己的标记（`section.hero-cinematic`，输入框 `.hero-prompt`、发送 `.hero-send`、胶囊 `.hero-capsule`、拍照/附件/语音 `[data-linker-assistant-open]`）。`Linker\Tools\Genie\Hero` 只在 `is_front_page()` 加载构建入口 `hero`（`src/hero/`），它不替换这些元素。页面加载时只多几样不可见的东西：一个 hidden 的文件输入、一个 hidden 的空对话容器（`#linker-genie-hero-surface`，供 `aria-controls`）、一个 `data-linker-genie-hero="ready"` 就绪标记，以及六个触发控件上的 `aria-expanded` / `aria-controls` 属性；不点击任何 hero 控件时不出现可见的新 DOM、类或样式，静止页面与线上逐像素一致（像素门见下）。
- **每个控件原地开聊、不跳页**：输入框回车（Shift+Enter 换行）、点发送、点胶囊、拍照、附件、语音都展开对话。发送与胶囊在线上是 `<a href="/linker-advisor/">`：脚本只阻止这一次导航，href 仍是无 JavaScript 时的回退；语音用浏览器自带听写，没有听写时只展开并聚焦追问框。
- **展开后的组成**：眉题、标题、副标题、胶囊、脚注收起；对话区插在 `.hero-dialog` 顶部、页面自己的 textarea 之上，textarea 仍是追问框（placeholder 换成 "Ask a follow-up…" / "Stellen Sie eine Rückfrage …"，关闭时复原）。对话区顶部是 "Genie - Linker's AI assistant" ＋ "Continue in the side panel" ＋ ×；首条写明 "Genie is Linker's AI assistant." 与答案依据、可能出错（目标 9）。答案里的产品卡桌面四列、手机两列（`src/hero/hero.css`；窄屏 860 px 与 dock 的断点一致）。hero 内渲染回答文字、产品卡、对比、文档、追问芯片、附件卡，以及 #250 的询盘确认卡（逐行产品与数量、留言、摘要开关、访客邮箱/姓名/公司/同意）与 #243 的联系卡（"让 Linker 联系我"）；两张卡发送后在对话里留下记录（询盘号与状态 / 已联系），与 dock 的同一会话一致（目标 5、6 在 hero 入口同样成立）。
- **一个会话**：`src/hero/session.ts` 在展开时读一次浏览器已有的会话（`readThread`，与 dock 同一 cookie 指向的会话文章），并且**每次发送前重读**，再把这整条线程连同新问题发送；`Proxy::turn` 记录的是请求里的整条线程，hero 与 dock 同时开着时，不重读就会用旧线程覆盖 dock 刚写下的一轮。关闭对话区只是卸载 hero 的视图，会话留在服务端；再展开或转到 dock 都是同一条。
- **继续与复原**：× 关闭对话区，hero 复原（类、注入的 DOM、placeholder、输入值全部还原）。hero 整体滚出视口后，右下角 Genie 圆钮旁出现 "Your Genie conversation · continue" / „Ihre Genie-Unterhaltung · fortsetzen"；点它、或点对话区顶部的 "Continue in the side panel"，都经 dock 加载器的 `linker-genie-ask` `{refresh:true, fromHome:true}` 把会话交给 dock：App 重读线程（`showStored`）并在面板顶部标出 "Asked from the homepage" / "Auf der Startseite begonnen"；dock 开着时返回入口收起，dock 关掉且 hero 仍在视口外时再出现。
- **附件（#236）**：拍照与附件按钮用同一个 `src/genie/attachments/prepare.ts`、`useAttachments` 与代理 `attachments` 字段，以及同一个 `ACCEPT`（图片与 PDF；两个按钮共用一个接受集，类型不符的由 `prepare` 拒绝）。文件准备好的那一刻作为这一轮的问题发出（照片/文档本身就是问题）；读到的铭牌渲染 `AttachmentCard`，确认按钮发普通消息，"No, type the model" / "Type the model" 把 "My device is the " 填进 hero 的追问框并聚焦。被拒的文件（类型、大小、读不了）在发送前就说明原因，不发问题、不到服务；对话区已在点击拍照/附件时展开（与原型一致）。
- **可访问性**（评审第 1 轮第 3 项）：六个触发控件（textarea、发送、每个胶囊、拍照、附件、语音）都带 `aria-expanded` 与 `aria-controls="linker-genie-hero-surface"`，展开时置 true、关闭时置 false。展开时焦点移进对话区（关闭按钮），关闭时焦点回到触发它的控件。新答案经一个 `role="status"` / `aria-live="polite"` 的 live region 播报（视觉隐藏）。dock 的既有回答没有 live region；这是先前就存在的缺口，本票只补 hero，不改 dock。
- **样式边界**（评审第 1 轮第 6 项）：`src/hero/hero.css` 对 LC 页面自己的类（`.hero-cinematic`、`.hero-stage`、`.hero-dialog`、`.hero-badge/title/...`）的规则只在插件加的 `.linker-genie-hero--open` 存在时生效，其余规则都挂在插件自己的类上。这是业主 2026-10-10 工具面设计裁定的例外，也是 AGENTS §4"插件对站点页面零 CSS"的唯一例外；静止状态没有插件样式参与，像素门 0 已证。变更台账见 `docs/acceptance/2026-10-19/232/change-ledger.md`。
- **文案**：六条新文案走对抗评审，记录 `docs/acceptance/2026-10-19/232/copy-review.md`；其余复用 dock 与 #236 已评审的条目。文案在 `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`，JSON 由 `just i18n-tools` 生成。
- **测试与验收**：`src/hero/state.test.ts`（状态机）、`src/hero/session.test.ts`（共享会话，含"每次发送前重读"）、`src/hero/Hero.test.tsx`（含 #243/#250 卡、live region）、`src/hero/controller.test.tsx`（六个控件、ARIA/焦点、关闭、返回入口、附件桥）、`src/genie/shared/*.test.*`（共用的提问/拒绝/卡片/听写）、`tests/php/Unit/HeroTest.php`（只在首页加载）、`tests/e2e/specs/genie-hero.spec.ts`（EN/DE × 1440/390，真实 Genie、标题与五个收起元素断言、附件四态、询盘与联系卡的发送、dock 交接）。像素门 `docs/acceptance/2026-10-19/232/pixel/`：首页 EN/DE × 1440/390，掩膜外差异 0；截图 `docs/acceptance/2026-10-19/232/shots/`。

### 主动预览卡（#249，实现目标第 4 条；业主选样式 A · 提示卡，`docs/prototypes/2026-10-17-preview-card/DECISION.md`）

- **哪些页有卡**（`Linker\Tools\Genie\Preview::context()`，名单即全部）：首页（`is_front_page`，EN/DE）、产品页、产品分类页（`is_product_category`）、解决方案页（`/solution/` 枢纽页的子页，德语经 `pll_get_post` 找枢纽孪生页的子页；枢纽页本身不算）。其余页——Lösungsentwurf、Proforma 请求、账户与登录注册、联系、配置器、博客——没有卡，也不加载卡的脚本与样式。
- **卡点名当前页面**：产品＝商品标题去掉括号里的描述（"SAJ H2-10K-T3 (10 kW …)" → "SAJ H2-10K-T3"）；分类＝分类名；解决方案＝页面标题（英文句中小写化，缩写与内部大写词保留）。名字与页面类型取自 #234 的页面上下文（`PageContext`，`Preview::card_page()`）；有卡的页面仍只是首页、产品页、产品分类页与解决方案枢纽的子页（枢纽本身、About、受众页虽是 `solution` 类型，没有卡）。
- **首页的建议不写死商品**：问型号那一条取当前商品数据里最新发布的逆变器（产品列表的第一张卡也是最新商品；限逆变器分类，示例是主产品而不是电表或线缆），当前语言；商品下架即自动换。另一条不点名商品（SAJ 与 GoodWe 两个品牌的比较）。第三条是目标 4 的"拍铭牌"（#236）："Look up my device from a nameplate photo" / „Welches Modell steht auf meinem Typenschild?"（`Preview::copy()` 的 `photo`，`data-linker-genie-peek-attach`）：点它不发问题，而是经 dock 加载器的 `linker-genie-ask` `{attach:true}` 打开 Genie，面板在输入框上方给出"Choose a photo"按钮（文件选择框只能由访客自己的点击打开）。"上传清单"（#251）是同形的第四条入口，代替了原先的"配什么电池"一条，保持在目标 4 的 2–4 条内（商品范围为空、取不到示例型号时，问句回退到"配什么电池"以保住目标 3 的每页至少两条问句；照片/清单一类附件动作不计入问句）："Turn a parts list into products" / „Teileliste in Produkte umwandeln"（`Preview::copy()` 的 `list`，`data-linker-genie-peek-attach-list`）：`{attach:true, list:true}` 打开 Genie，面板给出"Choose a file"，选择框接受 CSV、Excel 与清单照片。
- **组成**：PHP 在 `wp_footer` 打印隐藏的 `<aside data-linker-genie-peek>`（语义标记 + 类名，文案经 `.po`），`src/preview/`（构建入口 `preview`，不是 React 应用）决定何时显示；样式 `src/preview/preview.css` 随入口构建，只在有卡的页面加载（工具面的设计，同 dock 的 genie.css 先例）。无 JavaScript 时卡永不出现。
- **规则**（`src/preview/rules.ts`，每个数字带来源注释，起步值见 `docs/research/2026-10-17-ai-assistants/INTL.md` §0.3、`CN.md` §5.2）：
  - 锚点（每类页面一个 LC 模板选择器：首页 `.hero-cinematic`、产品 `.pdp-layout`、分类第一张 `.product-card`、解决方案 = hero 之后的第一个区块 `:is(.lk-hero-cinematic, .lk-hero-utility) ~ section`——住宅、工商业页是能力条，大型储能页是系统区；只滚过 hero 不算）的底边升到视口 40% 线以上＝滚过主内容；之后停留 8 秒才出现。页面上找不到锚点时按滚过四分之三屏算（e2e 断言每类页面的锚点都在，回落不会悄悄生效）。
  - **每次访问最多一次，跨标签页**（本线评审裁定）：访问记在 `localStorage`（所有标签共享）——最后活动时刻、本次是否已出现、是否开过 Genie；30 分钟无活动（页面浏览、滚动）即为新访问（来源：GA4 会话超时默认 30 分钟，`src/preview/memory.ts`）。
  - **对话进行中**（本线评审裁定）：本次访问里从任何入口打开过 Genie（圆钮、页面芯片、产品页 Ask、卡上的建议），或 dock 正开着，就不再出预览卡。
  - **Esc＝×**（本线评审裁定）：卡内按 Esc 与点 × 一样，30 天不出现（`localStorage` 记到期时刻）。浏览器存储读不了时按"已关闭"处理，不出现。
  - 访客正在输入框里打字时不出现，离开输入框后再出现；卡从不取焦点、不开 dock、不出遮罩，出现时以 `aria-live="polite"` 播报；卡一直留着，直到关闭、点建议或打开 Genie。
  - 点建议：卡收起，经 dock 加载器的 `linker-genie-ask` 事件把建议原文作为第一问发给真实 Genie（与产品页 Ask 同一入口）。点建议不算关闭。
  - **手机端**（本线评审裁定）：860 px 及以下（与线上隐藏圆钮的断点一致）静止时不变，圆钮仍隐藏；只有触发后圆钮才带红点出现（红色取 `--proto-sem-danger`）；点圆钮照常打开 Genie，标记随之消失。
- **样式**：颜色、圆角、阴影、焦点环全部取 `tokens.css` 的设计变量（WindPress 编译缓存，每页都加载），不另起一套十六进制颜色；尺寸与间距照原型。
- **像素门**：卡与样式只在触发后可见，静止页面与线上逐像素一致——`docs/acceptance/2026-10-18/249/pixel/`（首页、产品、分类、解决方案，EN/DE，1440 与 390，截图工具预设 `linker-genie-peek-dismissed-until`）。
- 测试：`src/preview/*.test.ts`（规则与控制器）、`tests/php/Unit/PreviewTest.php`、`tests/e2e/specs/genie-preview.spec.ts`（1440/390 × EN/DE，逐条规则，`page.clock` 快进）。验收与文案评审：`docs/acceptance/2026-10-18/249/`。

## 附件与铭牌（#236，实现目标第 2 条"能读铭牌照片与附件"）

依据：`docs/research/2026-10-17-deepseek-flash-vision/DOSSIER.md`（官方 `deepseek-flash` 收图、不收 PDF）。评测 `services/genie/eval/attachments/`，结果 `docs/acceptance/2026-10-18/236/`。

**一条链**：dock 的回形针（`src/genie/attachments/`，hero #232 用同一个 `useAttachments` 与 `prepare`）→ 代理 `Attachments` 检查 → 服务 `attachments.py` 读一次 → 读到的东西（reading）随会话保存、逐轮带回；**文件本身从不保存**。除了照片与 PDF，同一条链也承载零件清单的 CSV 与 Excel（#251，见"零件清单 → 产品"）：它们读成 `kind="list"` 的 reading（表行以制表符分隔），从不发给模型。

- **浏览器**（`prepare.ts`）：照片（JPEG/PNG/WebP；HEIC 在能解码的浏览器里，Safari）用 `createImageBitmap(…, {imageOrientation:'from-image'})` 摆正、经 canvas 重画成约 1.69 MP（1300×1300 面积，API 自己的缩放目标）的 JPEG（质量 0.85），canvas 不带 EXIF，GPS 不离开手机；PDF 原样。其他类型、超限、解不开的 HEIC 当场拒绝并说明原因，不发送。文件名进问句（"Attached: <名>"），字节走请求的 `attachments` 字段，不进 `messages`。
- **代理**（`Linker\Tools\Genie\Attachments`）：按首字节认类型（JPEG、PNG、WebP、PDF；声明类型必须一致），每轮至多 `MAX_FILES` 3 个，图片 ≤6 MiB、PDF ≤16 MiB、每轮 ≤20 MiB（来源注释在常量上；服务 `schema.py` 同值，`tests/test_attachments.py` 锁定两边）；每个文件计入调用者每小时 `LIMIT` 20 个的额度（`RateLimit`，一条 UPDATE 判断加一；访客按连接地址，登录客户按账号），超限 429，让 deepseek 花费不能被刷。拒绝即 `linker_genie_attachment_<原因>`（count/type/unreadable/size/throttled），记 `wc_get_logger` 的 `linker-genie` 源，不打开会话、不到服务。
- **服务**（`attachments.py`、`vision.py`）：再查一遍类型与大小；图片用 Pillow 带像素上限（5000 万）打开、摆正、重编码（不写 EXIF/ICC）；PDF 用 PDFium（`pypdfium2`）打开，**不执行任何脚本或表单**：有文字层（≥200 字符）的页读文字，没有的页（扫描、图纸）渲染成约 1.69 MP 的图，每个文件至多 `MAX_RENDERED_PAGES` 4 页，至多读 60 页，读不到的页在读取结果里点名。读图是 deepseek-flash 官方 API 的**单独一次调用**（`image_url` base64，关闭思考：开思考一张铭牌 6.5–25 s 且有一张两次超时，关掉后 2–4 s 读出同样的型号，见验收目录 `thinking.md`）：照片要 `json_object`（`kind` nameplate/document/photo、品牌、型号、产品类型、额定值、看不清写 null、不抄序列号与地址），扫描页要纯文字（`max_tokens` 2500，被截断的页写明"其余未读"）。失败一律显式：4xx 立即报错并记日志（含 API 原话），5xx/429/断连重试一次后报错；该文件的 reading 带 `failed`，本轮照常回答并说明读不到。没有 deepseek 密钥时记 `no_reader`。`build_model` 的 profile 设 `openai_chat_supports_document_input: False`：误把文档交给对话 agent 时在本地报错，不花一次请求。**PDF 在独立进程里解析**（`pdfwork.py`，每个文件一个子进程，带墙钟超时与内存上限）：PDFium 不是线程安全的，一次崩溃或挂起只让本轮这一个文件失败（`pdf_timeout`/`pdf_failed`），不带走服务。服务只认壳的令牌（`gate.py`）：所有 POST 要求 `X-Linker-Service-Token`，VPS 上与 `LINKER_GENIE_SERVICE_TOKEN`（站点 wp-config.php）同值；未配置时 POST 一律 503、`/health` 仍开放。部署时 `ops/activate.sh` 要求 `/etc/linker-genie.env` 里有 `GENIE_SERVICE_TOKEN`，否则以退出码 3 拒绝启动单元。请求体在解析前按整轮上限截断（`schema.MAX_REQUEST_BYTES`）。
- **数字只经事实**：每个 reading 作为工具 `linker/read-attachment` 的结果登记（`facts._from_attachment`；质检 `facts.collect` 同样认得）：`attN`（文件名）、`attN.text`、`attN.nK`（`figures.tag` 标出的数字）。铭牌额定值里粘在一起的单位与区间（"1000Vd.c."、"200...850Vd.c."）先加空格再标（`_spaced`），否则会被当成型号码而不可引用。回答引用 `attN`、数字写 `{fact:attN.nK}`，与文档块同一套核验与水合。附件文字是客户的数据、从不是指令（系统提示词"Attached files"一段，EN/DE）；长文件按问题选段（`page.select`，≤12 000 字符）。
- **铭牌的确定程度由产品数据定**（`nameplate.identify`，不用模型自评）：印的型号在产品词里逐字命中 = `exact`；命中我们的系列或型号的一部分 = `partial`（出该系列的候选）；读到了型号但不在我们的范围 = `none`（同品牌的产品可以提，但不得说成同一设备）；**没读到型号** = `unreadable`（只有品牌不足以判断我们有没有）。本轮有新铭牌时路由是 `nameplate`（`route.nameplate`，不问 Jev）：exact 搜出该型号并要求出卡，partial 出候选卡，none 按品牌搜但不强制出卡，unreadable 不调用、不出卡。
- **确认**：服务为每个新附件发一条 `attachment` 事件（`nameplate.card`：种类、读到的品牌/型号/产品类型、`match`、可确认的产品与其型号、PDF 的页数），壳渲染成卡（`AttachmentCard`）：exact → "In our range: …. Is this your device?" 与 "Yes, show its documents" / "Yes, what works with it?" / "No, type the model"；partial → 每个候选 "It's the …"；none → "This model is not in our product range."；unreadable → "Choose another photo" 与 "Type the model"。确认按钮发出的是一条以按钮原话开头、带型号的普通消息（"Yes, it's the SAJ H2-10K-T3. What works with it?"），下一轮照常由产品词与路由走到产品、文档或配对；"Type the model" 把 "My device is the " 放进输入框并聚焦（手动输入出口）。
- **保存与清理（随会话保留策略）**：服务把本轮读到的东西作为 `reading` 事件交给代理；代理把它们存进会话文章的 meta `Thread::READINGS`（最新 10 条，`schema.MAX_READINGS`），并从存档与回给浏览器的流里去掉这些事件（`Thread::split`）。之后每一轮代理把这些 readings 放进请求的 `readings`（只来自会话自己的 meta，从不采信浏览器），所以追问不必重传、原图也不会逐轮重发。readings 跟着会话：客户删除会话或 `Retention` 清理访客会话（开始 90 天后）时随文章一起删除；登录客户的会话按账户保留。原始文件：浏览器内存 → 代理请求 → 服务内存，**不写任何文件、不进 web 根目录、不对外提供**。服务的轮次日志（`turns.sqlite`）记 `read-attachment` 的结果（读到的文字，不含文件字节）：每条 reading 只在读到它的那一轮记全文，之后的轮次只记 id（`earlier`）；客户删除会话或 `Retention` 清理时，代理调用服务的 `forget`，把该会话每一轮里 reading 的文字、以及由这段文字生成的调用（如铭牌型号的产品搜索，`from_reading`；文件读成的零件清单的 `parts` 行文字）的参数与结果一并清掉（只留 id、kind、页数、失败与 `purged`；清单行留状态、数量与我们的产品名，清空原文），`understanding` 路由日志里的同一段文字同样清除；质检只读到剩余部分。模型自己的回答（`output`）与客户问句保留为质检记录：它们是模型生成的文本与客户自己的话，不是文件原文（文件原文可能带 PII，只在 reading 与派生参数里，已清）。
- **评测**（2026-10-18，g236，真实 deepseek-flash 官方通道）：读图用例 15 个——11 张真实铭牌照片（SAJ 2、GoodWe 6、Pylontech 1 及其缩略图、EcoFlow 1）、研究的合成 SAJ 铭牌，以及从我们自托管文档抽出的 3 张铭牌图（GoodWe GW112.6-BAT-AC-G10 ×2 exact、GW5KN-ET ×1 none；SAJ 与 Pylontech 的托管文档没有铭牌，README 记录排查范围）；问答用例 11 个——三份真实 PDF（EN、DE 数据表，GoodWe 图纸式快速安装指南）与手写的价格表、交货条款（EN/DE，答案不得出现金额/时效，交货走 handoff）。照片在仓库 `photos/`（业主 2026-10-18 确认授权），文档抽出的标签图在仓库外（`--labels`）。结果见验收目录 `README.md`。

## 零件清单 → 产品（#251，实现目标第 2 条）

依据：`docs/research/2026-10-17-ai-assistants/`（Lowe's Material Lists、Home Depot Materials List Builder、京东 AI 清单选品 S24、淘宝 61 项清单 S32）；验收 `docs/acceptance/2026-10-19/251/`。

**一条链**：粘贴清单 / 上传 CSV 或 Excel / 拍手写清单 → 代码逐行解析 → #233 的产品词表逐行匹配 → 服务自己的回答与 `parts` 卡（行状态、第一条待确认行的候选、一个加入动作）→ 客户逐条确认 → 浏览器**一次** `store.addAll` 写入 Lösungsentwurf。文件走 #236 的通道（同一 `attachments` 载荷、同一会话 readings），**文件本身从不保存**；清单状态不另存：源文本留在会话消息或 reading 里，客户的回答是普通消息，每轮由 `parts.find` / `parts.build` 重建。

- **输入**：dock 的输入框是 `textarea`（原型本来就是 `.gp-composer textarea`）：Enter 发送、Shift+Enter 换行，粘贴的多行清单保留换行并按行解析；一行问题仍是原来的发送方式。粘贴清单无需附件。
- **来源**（`parts.find`）：本轮的新 CSV/Excel reading 永远是清单；照片或 PDF 的转写在本轮消息含清单词或转写本身是清单（≥2 行产品）时是清单；先前的清单只在最新消息是确认（`Row N:`、或一个**属于待确认行**的短型号）、跳过或"加入草稿"请求时继续。清单已定后，数据表/型号问题交给模型；待确认行期间一条无关的短消息不会确认该行（无行号的型号必须命中该行候选、同品牌、同系列或同类别才算回答）。普通产品问题（两个型号写在一行、无数量、无清单词）不是清单。
- **文件**（`attachments.py`、`parts.rows_of`）：`text/csv`（≤1 MiB）与 `.xlsx`（≤6 MiB）。**旧版二进制 `.xls` 不收**：只认 Excel 的 OOXML `.xlsx`；加 `.xls` 解析需要新依赖，是业主裁定，不是本票的静默收窄。CSV 先 UTF-8（去 BOM），否则 Windows-1252（Excel 德语导出的 ANSI）；分隔符取逗号、分号与制表符中出现最多者。Excel 只读第一张工作表（zip + XML，标准库，不执行公式或宏）：每个条目按流读、超过 8 MiB 即拒（不只看 zip 头里的长度），单元格引用限制在 1,024 列与 Excel 的 1,048,576 行内（伪造的 `ZZZZZZ1`、越界行、单行过多单元格都拒），含 `<!DOCTYPE`/`<!ENTITY` 的 XML 直接拒绝（防实体膨胀）。行数上限 `MAX_ROWS = 200`（研究中最大清单 61 行，淘宝 S32）；行数或字符（`MAX_READING_CHARS = 60 000`）任一超限时 reading 带 `truncated`、文本以 `[the rest of the list was not read]` 结尾且仍在 60 000 字符内（不 500，不静默丢行），回答说明只读了清单的前一部分（不写死"200 行"，因为字符截断可能发生在 200 行以内）。读不出的 CSV/Excel 仍是 `kind="list"` 的失败 reading，壳给出"Choose a file"而不是"Choose another photo"。解析：行首/行尾数量（`2x`、`3 Stk.`、`4 pcs`、`x2`、` - 2`；最多六位数字，超过 Store API 的 9999 上限即钳到 9999）、表头数量列（qty / quantity / Menge / Anzahl / Stk / Stück 等）、无表头时取独立整数单元格；表头行丢弃；型号尾部 `-20` 不当作数量。
- **匹配**（`parts.build`，词表来自 #233）：型号命中且只指向一个产品 = `matched`；只命中品牌、系列或分类 = `uncertain`，候选按系列成员、品牌成员或设备类别取，品牌与系列同时出现时按品牌过滤（过滤为空则保留系列），品牌与类别同时出现时取交集（交集为空则保留品牌）；型号命中多个产品也 `uncertain`；什么都没有 = `missing`。候选最多 `MAX_OPTIONS = 6`（与 search-products 的六张卡同数），按型号名排序；同一产品的多行在加入时合并成一行。
- **逐条问**：`ask_line` 是第一条 `uncertain` 行；卡上只有该行给出候选芯片（`Row N: <型号>` / „Zeile N: <型号>"）、"Type the model"（聚焦输入框，客户直接打型号）与 "Skip this line"（`Row N: skip`）。服务按 `Row N:` 的精确行号确认；无行号的短消息且只命中一个型号、并命中该行的候选/品牌/系列/类别时确认当前第一条待确认行（同系列里第 7 个以后、不在 6 个候选里的型号也可以）；跳过同理。已确认或跳过的行不被后续消息改写；清单源之前的消息不算回答。
- **一次写入**：全部 `uncertain` 行确认或跳过之后，`parts.add` 才出现（未确认时不写半份清单）；它把 `matched` 行按产品合并成 `items`（产品 ID + 数量），壳的卡上一个按钮调用**一次** `store.addAll`（Woo Store API 的 `cart/add-item` + 读回，见规格 14；读回短于请求时再读一次后才报 unverified）；不建套装 SKU、不写商品数据、不经过服务端写接口。按钮状态 pending/added/unverified/retry 与产品卡相同。
- **不经模型**：路由名 `parts`，`app._answer` 直接返回 `parts.answer` 的文字块与 `parts` 块；轮次日志 provider=`service`、model=`none`；Jev 不问，工具调用 0。回答里的行数由代码写，模型无法编造产品、数量或"已加入"。
- **文案**：`docs/acceptance/2026-10-19/251/copy-review.md`（EN 先定稿，DE 独立撰写，Sie 体；`.po` 为德语权威）。

## 页面感知（#234，实现目标第 3 条）

**页面上下文**（`plugins/linker-tools/includes/Genie/PageContext.php`，一处实现，dock、预览卡、代理共用）：每轮带 `{type, url, title, product_id?, post_id?, category_id?, draft_ids?}`。八类页面 + `other`：
| type | 哪些页 | ID |
|---|---|---|
| `home` | `is_front_page()`（EN/DE） | `post_id` |
| `product` | `is_product()` | `product_id`＝英文商品（轮次里的商品 ID 一律英文，`pll_get_post`）；`post_id`＝本语言的商品文章 |
| `category` | `is_product_category()`；商城 `/products/` 与其他商品分类法页没有 `category_id` | `category_id`（本语言的分类） |
| `solution` | 英文路径首段是 `solution`、`about`、`for-epc`、`for-installer`、`services-support` 的页面及其子页（德语经英文孪生页判断；线上页面清单 2026-10-18） | `post_id` |
| `blog` | 单篇博文（有 `post_id`）；博客首页、博客分类与标签（无） | `post_id` |
| `faq` | 英文路径 `faq-download` 及其德语孪生页 | `post_id` |
| `draft` | `is_cart()` | `draft_ids`：**代理**从访客自己的 Lösungsentwurf 读（`wc_load_cart()`，英文商品），从不采信浏览器 |
| `account` | `is_account_page()` | — |
| `other` | 其余（联系、法律页、Proforma 请求、工具页、搜索结果） | 页面有 `post_id` 时带上 |

dock 的 mount 以 `data-page` 打印整份上下文，应用逐轮原样发回；代理（`PageContext::sanitize`）只保留上表的键与类型，`type` 不在表内即 `other`。

**页面内容来源**（`services/genie/src/linker_genie/page.py`，工具名 `linker/read-page`）：服务以匿名访客的身份 GET 该页自己的地址，取 `<main>` 的文字，隐藏元素与脚本、样式、SVG、下拉框不算；缓存 10 分钟。理由（2026-10-18 实测）：WP 原生 REST 的 `content.rendered` 不是访客看到的页面——FAQ 页的 REST 内容是带未渲染短代码的旧正文，而页面由 LiveCanvas 动态模板呈现 244 条 FAQ 与 159 份文档；商城、商品分类、Lösungsentwurf、账户、博客首页都没有正文。生成的内容包要在每次编辑与每次德语自动翻译后重建发布。读页面本身不需要 WordPress 端代码（AGENTS.md §5 原生优先）。德语页即德语内容（Polylang 的 `/de/` 路径）。
- **取页安全**（PR #295 评审第 1 轮）：只取浏览器所给地址的路径（列表页——商品分类、带筛选或搜索的页——连同查询串；以 `post_id` 指名的单页去掉查询串），拼到本服务服务的站点 `GENIE_WP_URL` 上；`/wp-admin`、`/wp-json`、`/wp-content`、`/wp-includes`、`/wp-login.php`、`/xmlrpc.php`、feed 与任何带扩展名（`.html` 除外）的路径不请求；重定向只跟协议、主机、端口都相同的站内地址，至多 3 次；响应须是 `text/html`，流式读取、超过 2 000 000 字节即停（线上最大页面德语 FAQ 718 375 字节）；客户端不收也不发 cookie，每次读取都是匿名访客。
- **价格与运费不从页面来**：匿名页面上的价格门（"Net price after partner sign-in"）与已批准合作伙伴看到的价格相反，运费属物流（业主 2026-10-05）。类名含 price 的元素（`pdp-price`、`sf-card-price`、Woo 的 `price`）、运费说明 `pdp-avail-note`、店面的 `data-card-price` / `data-card-gate`、任何写着金额的段落、以及只是价格门的短句都不进页面文字。价格只来自产品工具的 commerce 对象（随客户账号，#242），只出现在产品卡上，正文不写；问到运费、发货、运输的本页问题一律转团队（`route._LOGISTICS`，与 Jev 的判断无关）。
- **只给模型与问题相关的部分**：页面切成段落（遇标题或 700 字符断开），总长 ≤12 000 字符时整页给出（首页 7 300、分类 8 400、住宅储能 10 400）；更长（FAQ 页 118 000）时给开头 1 500 字符 + 与问题词重合最多的段落，另附页面标题大纲（≤40 条）。数字按文档块的办法标成 `[nK=值]`，模型写 `{fact:page.nK}`、`refs` 写 `page`，水合填值（核验同文档块，`facts._from_page`）。页面文字是站点的数据、从不是给模型的指令（`page.RULE`，系统提示词各语言一处）。
- **个人页面不匿名读**：Lösungsentwurf 的内容是它的商品（`draft_ids` → Store API `include`，商品可作卡片）；已登录客户的账户是他的询盘（路由调 inquiry-status）。访客的账户页即登录页，照常读。
- **读不到**：`PageUnavailable` 记入轮次日志 `page_error` 与 `call_failures`，回答照常进行；提示词要求模型说明这次读不到页面，不得猜。
- **日志**：读页结果整份记入轮次日志的工具调用（事后质检要看模型当时读到的文字），保存与删除跟随轮次日志（`turns.sqlite`）本身。

**何时读**（`route.with_page`）：Jev 的 `about_this_page`（≥0.5，与 #233 判本页产品同一切线）为真时加读页面（Lösungsentwurf：read-page + 至多两对逆变器×电池的 check-compatibility；已登录账户：inquiry-status）。找人、公司物流、询盘状态三类路由不读页面；问本页能否转团队不由本票决定（#243），路由的 `no_handoff` 照旧。调用按固定优先级装进每轮 4 次：路由自己的调用（含主语的 get-product）→ 读页面 → 草稿的配对；文档路由留 1 次给模型的追加检索；装不下的记入轮次日志 `dropped_calls`，没查的配对写进提示，让回答说明还没查。路由的调用彼此独立，并行执行（读页面不再排在前面加时）。Jev 不确定或不可用时，模型可自行调用 `linker_read_page`（无参数）。每轮提示词都写明 `page=`、`page_title=`、`page_url=`，"这页 / 这款 / here / this one" 指本页或本页产品；产品页上没有型号词的问题照旧以本页商品为主语（#233）。Jev 的页面状态加上 `title`，类型取自 `schema.PageType`，新类型以词语命名（`home_page`、`solution_page`、`faq_and_documents_page`）。

**开场建议**（`Entries::prompts`，2–3 条，点名本页）：有预览卡的页面（首页、产品、产品分类、解决方案）用预览卡同一组问题（`Preview::asks`，#249 的评审定稿）；其余：商城 "Which model fits my project?" + SAJ/GoodWe 比较；博文 "Summarize this post" + "Which products does this post apply to?"；博客首页 "Which of these posts cover hybrid inverters?" + "Summarize this page"；FAQ 与文档页 "Is there a datasheet for my model?" + "Which batteries work with my inverter?"（FAQ 的答案是站点文案、不作事实来源，AGENTS.md 2026-10-09）；枢纽、About、受众页 "Summarize this page" + "Which products fit my project?"；Lösungsentwurf 与账户沿用既有两条；其余页（联系、法律页、表单、工具）"Which model fits my project?" + "Which batteries work with my inverter?"（不对法律文本做摘要）。德语独立撰写在 `.po`，文案评审 `docs/acceptance/2026-10-18/234/copy-review.md`。

评测：`services/genie/eval/page/`——`questions.json`（八类页面各两问 × EN/DE，含"这页说的……是什么意思"与产品页"这款"）、`pages.py`（不钉 Jev，真实页面、真实 deepseek-flash；已登录行用 `UserContext` 现签令牌）、`capture_pages.py`（重取 `tests/fixtures/pages/`）。结果：`docs/acceptance/2026-10-18/234/`。

## 价格跟账号走（#242，实现目标第 8 条）

**规则只有一条**：`plugins/linker-commerce/includes/Gating/CommerceState.php`。已批准的合作伙伴账号看净价；访客、待审、限制账号看不到；按项目报价的商品（`rfq_only`，线上 1957）谁都看不到。原因的先后由 `CommerceState::reason( $product, CARD|PAGE )` 一个函数决定，两个表面各按线上现状：`CARD`（Woo 自己的价格 HTML——Woo 列表与 Store API 的 `price_html`、Lösungsentwurf 与询盘的行、草稿汇总）先说商品（线上访客的 `/wc/store/v1/products/1957` 的 `price_html` 是 "Quoted per project"）；`PAGE`（产品页、对比页、Genie 的产品卡）先说账号（线上访客的 1957 产品页是 "Net price after partner sign-in"）。Genie 的卡用 `PAGE`，因为完成标准是"与产品页一致"。

- **令牌**（`Linker\Tools\Genie\UserContext`，沿用 inquiry-status 已有的那枚）：壳为已登录客户签 `user|expiry|HMAC-SHA256`（`wp_salt('auth')`），有效期 `UserContext::TTL`（来源注释在常量上：壳的 60 秒轮次超时的两倍）。随轮次交给服务（`user.context`）；服务只在 `abilities.USER_CONTEXT_ABILITIES` 上以请求头 `X-Linker-User-Context` 送回：`linker/inquiry-status`、`linker/search-products`、`linker/get-product`（答案随客户而变的）。**WordPress 一侧绑定同样的范围**：`UserContext::enter` 挂在 `rest_pre_dispatch`，只对 WordPress 解析出的路由（不是地址文字）是这三个 ability 的 `/run`、且方法是 GET 的请求，在签名与有效期都对、且没有 cookie 会话时把请求登录为该客户；`rest_post_dispatch` 上再登出，并给这份回答加 `Cache-Control: no-store, private`（WordPress 自己的 no-cache 在派发前按访客决定）。别的路由、别的 ability、只是在查询串里写了 ability 路由的请求，一律按访客回答（单元测试 + 实例 HTTP 测试；main 上同一伪造请求返回 200，本分支 401）。令牌不写日志、不进轮次库、不给浏览器。
- **`partner`**：壳经过滤器 `linker_commerce_visitor_sees_prices`（唯一回答者是 linker-commerce 的 `PriceDisplay::sees_prices()` = `CommerceState::visitor_sees_prices()`；没有 linker-commerce 时缺省 false）填写，不用"已登录"。轮次日志把它记成 `approved`，质检的第二道门读它（规格 33）。模型的每轮提示写 `partner=`，只用来措辞，不决定价格。
- **商品的价格行**（`ProductCommerce`，search-products 与 get-product 的 `commerce`）：`price_line` = 客户自己的产品页在价格位置印的那一行（`ProductView::price_html`，在轮次语言的 locale 里生成，经 `Mail\LocaleSwitch` 重载本插件的目录）：已批准账号是价格（`€1,680.00` / `1.680,00 €`），其他账号是产品页原句（"Account under review. Prices after approval." / "Ihr Konto wird geprüft. Preise nach Freigabe." 等）；`price_reason` 说明为何没有价格：`login` / `pending` / `restricted` / `project` / `unpriced`。
- **模型正文不写价格**：没有价格占位符（`ground.py` 第 9 条拒绝任何 `{fact:….price}`；正文本就不许有裸数字）。问价时模型出产品卡，说卡上显示价格。`pID.price` 仍登记为事实，只供质检核对。
- **卡片由服务填**（`prices.fill`，正常与兜底两条路都走）：每个 `cards` 块带 `prices:[{product_id, text, reason?}]`，`text` 就是该商品 `commerce` 的 `price_line`。本轮没有任何工具给出它的 `commerce`（配对放行的电池、Lösungsentwurf 的商品、对比）时，服务以客户身份补 get-product：并行，统一截止于轮次开始后 `prices.LOOKUP_DEADLINE` = 50 秒（壳等 60 秒，`SHELL_TIMEOUT`；余下 10 秒留给日志、SSE 与壳存会话，三者在 g242 实测合计不到 0.1 秒），答了的记入轮次日志的工具调用，没赶上的记 `price_failures`（不阻塞，测试钉住慢 ability 推不过截止）。这样的卡：账号本身决定价格行时（访客、待审、限制——产品页对每个商品印同一句），用本轮任一 `commerce` 的那句；已批准账号的价格行随商品而定，该卡不显示价格行。`prices` 不在模型看到的 JSON Schema 里（`SkipJsonSchema`），模型写了也被覆盖。
- **壳**（`GenieCard` → 共享 `ProductCard` 的 `price`）：只渲染服务送来的 `text`，有 `reason` 时是 `linker-card__price--note`（灰），否则 `--net`（粗体）。壳不持有任何价格句子，德语句子来自 linker-commerce 的目录。卡上的价格行随最后一轮的 SSE 存在会话里（`Thread`），重载时显示的是那一轮当时的价格行。
- **顺带修掉的产品页与对比页问题**（同一条规则的漏洞，变更台账见规格 11）：已批准账号在按项目报价的商品上读到 "Not available for your account" → "Quoted per project"；德语孪生 6800 没有自己的 `rfq_only`，德语产品页向已批准账号显示 33.250,00 € → 读英文商品的标记；对比页 "Net price" 行对所有看不到价格的情况都写 "Net price after partner sign-in" → 与产品页共用 `ProductView::price_html`。访客看到的页面不变（像素门）。
- **测试**：`plugins/linker-commerce/tests/php/Unit/Gating/CommerceStateTest.php`（两个表面的顺序、德语孪生、未知表面）、`Unit/Abilities/ProductCommerceTest.php`（四种账号 + 按项目报价 + 无价 + 德语）、`Gating/PriceDisplayTest.php`（过滤器）；`plugins/linker-tools/tests/php/Unit/UserContextTest.php`（路由绑定、伪造查询串、其他 ability、会话优先、登出与 no-store）、`Unit/ProxyTest.php`（`partner` 取自规则）；**真实实例**：`plugins/linker-tools/tests/php/Integration/GeniePricesTest.php`（四种账号经 HTTP 带令牌调用 get-product，价格行与各自产品页逐字一致，EN/DE；1957 英德两页；对比页价格行；令牌只在三个 ability 上生效；伪造与过期令牌按访客）；服务 `services/genie/tests/test_prices.py`（夹具 `tests/fixtures/prices.json` 由 `eval/prices/capture_prices.py` 从实例的四种账号取得；截止与并行）；壳 `src/genie/CardPrice.test.tsx`；端到端 `tests/e2e/specs/genie-prices.spec.ts`（四种账号 × EN/DE × 1440/390，卡上价格行 = 产品页价格行，截图入 `docs/acceptance/2026-10-18/242/`）。

## 理解层（#233，实现目标第 2 条）

每轮在模型之前由 `services/genie/src/linker_genie/understand.py` 准备：

1. **产品词**（`lexicon.py`、`storeapi.py`）：词表来自 Woo 原生 Store API（`/wp-json/wc/store/v1/products` 与 `/products/categories`，EN + `lang=de`），不新增 WP 端代码；缓存 10 分钟。品牌、系列（slug、去品牌别名，一词别名须含数字或在标题中大写出现）、型号（`pa_model`、标题里的字母数字码、SKU 与去前缀 SKU）、分类（只认本身是 device class 的分类；德语名经 SKU 关联到英文分类）。比较前归一化（小写、只留字母数字），按空白与连字符切词，最长匹配优先。德语商品是独立文章，轮次里的商品 ID 一律是英文 ID。读不到 Store API 时显式记日志（`vocabulary_error`），本轮无产品词。
2. **Jev**（`jev.py`）：typesafe/jev-1.13，仅经 OpenRouter `/api/v1/systemone`，一次问四题：`intent`（10 类，判据同 `docs/research/2026-10-17-jev-intent/eval.py`）、`about_this_page`、`wants_person`、`needs_followup`。每次 6 秒超时、最多 3 次；仍失败、拒绝或答复来自别的模型都抛 `JevError`，记入轮次日志 `jev_error` 与 SSE meta，本轮由 deepseek-flash 自行决定（票里允许的唯一降级）。
3. **路由**（`route.py`）：意图置信 ≥0.8 由代码调工具——找产品 → search-products（产品词给出的过滤；一个系列族同时有单相和三相时按相数各搜三张）；文档参数 → search-knowledge（`product_ids` = 匹配到的型号或本页产品）+ get-product / 族搜索；配对 → 两件 check-compatibility、一台逆变器 `with_pairings` 搜索；对比 → compare-products；选型 → size-hint（kWp、年用电、相数、备电由代码从原句读出）并要求配置器动作、不出卡片；询盘 → inquiry-status；找人 → `route.person()`（不调工具、不跑模型，见"转人工"）；公司物流 → handoff-team。整条消息都是产品词（裸词）时，无论 Jev 怎样答都走产品搜索并要求出卡片；长句里的产品词，Jev 最倾向 documents_specs 时（置信度不论）由代码同时调用 search-products 与 search-knowledge（只有系列时 `product_ids` 取该系列的商品）；其余 Jev 不确定的情况照搜但不强制卡片。其余交 deepseek-flash 决定。路由的调用计入每轮 4 次工具预算，结果以 JSON 放进提示词。
4. **核验**（`ground.py` 第 6–8 条）：文档只以 `document` 块出现（模型只写 `ref`，服务填标签与 `#page=N` 链接；get-product 的文档是 `pID.document.N`；同一文件只出一个链接，多页合并为"pp. 3, 7"/"S. 3, 7"；配置器动作的 URL 也由服务按 size-hint 填写），正文与占位符里不得有 URL；AGENTS.md §3 禁用词（article/catalogue/cart/basket，Artikel/Katalog/Warenkorb）；路由要求（产品词出卡、选型带配置器无卡、产品与文档类不转团队、找人与公司类只有 handoff 块）。兜底按路由出形状（选型 = 配置器、文档 = 文档链接、产品 ≤6 张卡）。
5. **事实**：get-product 的数据表 `figures`（`n_mppt` 等）按轮次语言登记为 `pID.<key>`；功率与能量类选择事实水合时补单位（kW/kWh）。

评测：`services/genie/eval/understanding/`——`bare_words.json`（75 条裸词 EN/DE，离线测试与线上实例共用）、`jev_cases.json`（#260 的 60 条 + 线上真实问句 15 条）、`run.py`、`jev_eval.py`、`capture.py`（重取 Store API 夹具 `tests/fixtures/storeapi.json`）。结果：`docs/acceptance/2026-10-17/233/`。

## 转人工："让 Linker 联系我"（#243，实现目标第 6 条，验收 A5、A6）

**何时提供**（`services/genie/src/linker_genie/contact.py`，服务在回答之后附上 `contact` 块，模型的输出结构里没有它，模型文字永远不能提供或发送转人工）：

| 原因 `reason` | 触发 | 回答 | 连续两轮 |
|---|---|---|---|
| `asked` | ① 确定性找人短语表（EN/DE 两张表总是都查，Knocket 外层的做法：NFKC、小写、去标点、按词边界匹配，只收明确的找人说法：人称名词（person、someone、human、Mitarbeiter、jemandem……），"team" 只在属于某人时算（your team、the Linker team、Ihrem Team），agent 只带冠词时算；"expert""engineer""Techniker"与裸 "team" 也指软件、模式与手册（"the team portal""expert mode""the engineer's guide"），不收（评审第 1 轮）；裸名词如 customer service 留给 Jev；短语所在分句里有否定词则不算，"I don't want to talk to a person" 照常交 Jev；`contact.PHRASES`）命中即走 `person` 路由，**不调 Jev、不调模型**；② 没命中而 Jev 以 ≥0.8 置信判意图 `talk_to_person` | 服务自己的一句（`contact.ANSWER`）+ 联系卡，不经模型 | 客户每次要求都提供 |
| `service` | 公司、物流、售后（`service` 路由） | 团队邮箱句（handoff 块）每次都有；联系卡附在其后 | 卡：上一轮已提供则不提供（邮箱句照旧） |
| `dissatisfied` | Jev 的 `wants_person`（"找人或不满"）≥0.8，意图是别的 | 照常按路由回答 + 联系卡 | 上一轮已提供则不提供 |
| `repeat` | 客户连续第三轮问同一个问题（`contact.same_question`：去掉 EN/DE 虚词，再去掉填充与时间词（now、today、right now、currently、still、jetzt、heute、gerade、noch、aktuell；please 与 bitte 本来就是虚词。#375 校准表，词来自 #331 s5 攻击句 now/today/right now 与库内同槽位问法；not/nicht 与带数字的词不去）后，后一句不加任何实词、型号与数量词（带数字的词）不变、两句仍共有 ≥0.5 的词（Jaccard），至少两个实词；加了功能或数量（"…with backup?""…für 15 kWh?"）或换了同系列型号（H2-10K-T3 → H2-8K-T3）都是新问题。在 `eval/contact/repeats.json` 39 对 EN/DE（含 8 对真实追问反例）上测定：0 到 0.75 之间任何切线都 39 对全对，取中间 0.5） | 照常回答 + 联系卡 | 上一轮已提供则不提供；同一个问题的这一串里提供过一次就不再提供 |

哪几轮提供过由服务自己的轮次日志判定（`TurnLog.offers`，按 `conversation_id`，最新在前；日志的 `contact` 列存 `contact.decide` 定下的原因，日志本身不读块），不信浏览器。附卡后服务以 `ground.shipped` 检查整份出货回答：至多一张卡、在最后、正是 `decide` 定下的那一种；公司类回答只有邮箱句和卡——不过即去掉卡（服务自己的错，不由模型改）。不经模型的找人回答在轮次日志里记 `provider=service`、`model=none`。提供之后 Genie 照常回答后续问题（不学 Knocket 的 30 分钟静音，TRIAL.md §3）。Jev 不可用时短语表与重复规则照常生效。

**联系卡**（`plugins/linker-tools/src/genie/components/ContactCard.tsx`，样式在 `genie.css` 末节，全部取该表已有的值）：出现时 GET `linker-ai/v1/genie/contact` 取签名起始时间、已登录客户的地址、本会话是否已转出、客户可见的团队邮箱（过滤器 `linker_genie_team_mailbox`，commerce 以 `Options::team_mailbox()` 回答；被拒时卡上给出它，找人的客户不走进死胡同）。已登录客户**不问联系方式**，卡上点名账户地址（账单邮箱，没有时用登录邮箱），一键发送；访客只留邮箱，并勾选站内公开表单共用的同意句（"I agree that my details may be used to respond to this message."，#246 的措辞；已登录客户注册时已同意）。卡上承诺一个工作日内回复（AGENTS.md 2026-10-09），并说明 Genie 继续回答其它问题。发出后卡显示"已转给团队"与回复地址；这张已发出的卡留在对话历史里，紧跟提供它的那条回答，之后的轮次与重载后都在（`ContactSent`；会话读取路由 `linker-ai/v1/genie/conversation` 返回 `contacts: [{after, email, receipt}]`，`after` 是发出时已存消息数，即那条回答的位置；评审第 1 轮）。整张卡是同一个 `aria-live` 区，状态变化会被播报。回复渠道是邮件，文案说明这一点（"by email / per E-Mail"）。客户收到与联系表单一样的回执（#246 的 `InquiryReceivedEmail`，客户的语言），受站点回执日上限（`ReceiptLimit::DAILY_CAP` 10，只拦回执、不拦记录与团队邮件）约束；超过上限时卡与历史里的卡照实说"We have not sent a confirmation email."（#246 联系表单的同一句）。文案评审 `docs/acceptance/2026-10-18/243/copy-review.md`。

**转给团队**（`Linker\Tools\Genie\ContactRequest`，POST 同一路由）：
- 公开表单的防护（`FormGuard`，与 #235 的 `ConversationMail` 共用一个类，评审第 1 轮）：蜜罐 `website`；签名起始时间 `started` + `started_nonce`（HMAC，站点 nonce salt，门名在签名里，一扇门的戳到另一扇门无效），早于 `MIN_SECONDS`（3 秒）、晚于 `STAMP_LIFETIME`（一天）或签名不对即拒；每个连接每小时、全站每天各一个 `RateLimit`（一条带条件的 SQL `UPDATE`，同一时刻的请求不会共占最后一个名额），每扇门自带有出处的上限：本门 `ContactRequest::LIMIT` 3/小时（联系表单的限额）、`ContactRequest::DAILY` 20/天（站点占主机 100 封/日中的 80 封；加上会话邮件 `ConversationMail::DAILY_CAP` 10，Genie 共 30 封，余 50 封；线上邮件日志最多的一天 2026-10-17 发了 7 封）；超出即 429 拒绝，**不排队**。蜜罐命中按已发送回答、什么都不发。
- 同一会话、此后没有新消息、同一地址的第二次请求不再发信（幂等）。
- 交接内容（`ContactRequest::handoff()`）：后台整段对话的链接（`admin.php?page=linker-genie-quality&conversation=<ID>`，该页现在按 `Thread::transcript()` 显示含最后一轮回答的整段对话，并列出本会话的转人工记录）、摘要（客户最近 5 条消息，最新在前：重复规则的三轮加此前两轮）、当时的页面（类型、标题、本站地址；外站地址丢弃）、Lösungsentwurf（`wc_load_cart()` 读访客自己的草稿：产品名、SKU、数量）、原因与它的标签（`ContactRequest::reason_label()` 是原因标签唯一的地方，以站点语言写进交接，团队邮件与后台会话页都显示它）、语言、客户（用户 ID、地址、姓名）。
- **一份记录**（评审第 1 轮，#246 合并后）：Genie 的交接是"经 Genie 来的联系留言"，走 #246 的唯一入口。`ContactRequest` 以过滤器 `linker_tools_genie_contact_team` 交出交接，`Linker\Commerce\Genie\Module::contact()` 以 `Contact\Submission::from_handoff()`（访客只给邮箱，名字可空）调 `Inquiry\Sender::message()`：一条 Woo 订单记录（来源 `contact`，`created_via=linker_contact`，客户留言 = 客户最后一句），交接存在记录的 `_linker_genie_handoff` meta（`Sender::message()` 的第二个参数，状态变更发信之前写入）；#246 的团队邮件（`NewInquiryEmail`，`Mail\TeamEmail`：收件人与 Bcc 来自内部通知入口 `notify_to()` / `notify_bcc()`，发件人 `notify_sender()`，Reply-to 是客户）在记录带交接时插入"Through Genie"一节（`templates/emails/linker-genie-handoff.php`：原因标签、页面、客户最近的消息、整段对话链接、Lösungsentwurf 行，"Genie promised a reply within one business day."）——#246 的邮件能带上这些，所以不另设团队邮件，原先的 `Genie\ContactEmail` 已删除。回执是 #246 的。过滤器回答 `{order, receipt}`；没有回答（commerce 未启用）时路由回 503，卡上说暂时转不出。
- 会话文章上另记一条 `linker_genie_contact` meta（时间、原因、标签、地址、用户、页面、消息数、记录号、回执是否发出），后台会话页与历史里的已发出卡读它。

**测试**：`services/genie/tests/test_contact.py`（短语表正反例、同问判定按 31 对测定集、四种原因与"不连续两次 / 一个问题一次"）、`test_turn.py`（找人不跑模型、不满附卡、日志判连续、第三轮一次）、`test_understand.py`（短语命中不调 Jev）；`test_ground_understanding.py`（出货检查）；`plugins/linker-tools/src/genie/components/ContactCard.test.tsx`、`App.test.tsx`（卡出现、提供后照常回答、已发出的卡在下一轮与重载后留在历史里且只一张）、`api/turn.test.ts`、`tests/php/Unit/FormGuardTest.php`、`ProxyTest.php`；`plugins/linker-commerce/tests/php/Integration/GenieContactTest.php`（真实实例：记录（#246 的联系记录、交接在 meta 里、页面语言）、Outbox 队列断言团队邮件的收件人与内容齐全、回执一行到客户、回执上限时只有团队邮件且卡说没有回执、访客未同意即拒、已登录不问地址、蜜罐、签名起始时间、连接限额、全站日上限、幂等、十个进程并发只有 3 个拿到名额）与 `NotificationRoutingTest`（Genie 一行：#246 的团队邮件与回执）。评测 `services/genie/eval/contact/`（真实服务：短语表、Jev、deepseek-flash，EN/DE），结果 `docs/acceptance/2026-10-18/243/`。

## 验收

旧 Advisor 的 190/191 只是症状。下面的保证与面板是**构建时的测试与评估集**（Rufus 用评估集和 LLM-as-judge 衡量质量，见 `docs/research/2026-10-09/platform-ai-shopping-assistants.md` 第 155、191 行），不是运行时组件；每条标注复刻来源。

### 结构保证（每条一个自动化测试，任一失败不合并）
- 模型输出里不出现数字，数值由服务端填入——复刻 Rufus 的 hydration（报告第 151、171 行）。
- 正文引用 ⊆ 本轮工具结果；卡片 ⊆ 正文引用；推荐 ⊆ `search-products` 的 qualified——复刻全部对标物的共同骨架 (a)"答案锚定平台目录与实时状态"（第 12、65 行）。
- 动作只能是允许列表里的，参数只来自工具结果——复刻 Accio 的"高风险动作需用户批准"（第 89 行）与 Sidekick 的小工具面。
- 范围外意图只有 handoff 块——业主 10-05 裁定，由提示词与 schema 实现；服务提供联系卡时为 handoff 块 + 卡（#243，`ground.shipped`，卡不连续两轮）。
- 披露句出现一次——复刻 Shopify（第 102 行）。
- 卡片反馈态在卡内、按钮高度不变——普通组件测试（Storybook），与助手无关。

### 行为面板（`docs/acceptance/genie-panel.md`，≥30 问，EN/DE 各一遍；由 #16 做成端到端套件）
覆盖：每个产品分类至少 2 问；四个入口各 2 问；条件齐全 / 冲突 / 事实不足 / 加装 / 48 V 与 HV / 备用 / 品牌偏好 / 对比 / 文档 / 库存与价格（登录与未登录）/ 范围外（公司、物流、安装）/ 多轮追问后出结果 / 动作（加入 Lösungsentwurf、加入方案、打开配置器、查询盘）。每问写明期望集合（从 `docs/research/2026-10-09/old-repo-live-catalogue-facts.md` 推导）与期望行为。通过标准：期望集合一致率 100%，追问不超过一个，披露句出现一次。

### 必过项（回归表 `docs/acceptance/protocol.md` §5 的 R1–R14）
- [ ] R1/R2（EN/DE 住宅三相 10 kWp 原句）：qualified ⊆ #7 的住宅三相集合；无 ETR/ESA；卡片 ⊆ 正文引用；一个追问。
- [ ] R3 冲突（12 kWp vs HS3-5K）、R4 事实不足（追问相数）、R5 产品页配对、R8 范围外只有邮箱句（附联系卡时为邮箱句 + 卡）、R10 加装只列有放行的电池、R14 披露句。
- [ ] 核验注入测试五类全部拦截；核验失败率写入 PR。
- [ ] ProductCard：加入 Lösungsentwurf 的 pending/added/unverified/retry 与加入方案的 saving/saved/failed 均在卡内可见，按钮高度不变，内容不越过卡片（旧票 191 的验收行）；工作区与常驻 × 1440/390。
- [ ] 视觉验收：四入口 + 常驻 × 状态 × EN/DE × 1440/390。

## 变更记录
- 2026-10-19（#368 极值问题）：`linker/search-products` 增加 `ac_power_min`、`device_classes` 与 `extreme`（smallest/largest/cheapest）。路由从英德问句读出下限与极值，代码先聚合再交给模型命名那一件；价格对当前账号不可见时 cheapest 不排序、不点名。品牌或系列上的极值是这一次聚合，不是型号冲突。消息里写了两个及以上型号，或一个型号与所写品牌冲突时，仍按型号逐个搜索。依据 dossier §1.1 末段与 §1.11：极值/消歧无竞品先例，设计理由在该票的 PR。
- 2026-10-19（#336 延迟埋测，#329 图）：新增服务模块 `timing.py`（被动计时，零行为变更：不动模型路由、重试、提示词与顺序）；轮次日志加 `timing` 列（旧库自动补列；INSERT 只写各阶段、无 `total`，流结束后由 `set_timing` 补完整记录 `total` / `first_event`——未流出完的轮次记为 incomplete，不进百分位），SSE meta 加 `timing` 对象（#336B 基线逐题读取此处，壳忽略未知字段）。新增 `turn_starts` 表：每轮开始记一行、轮次行落地即删；模型挂起/进程被杀留下的开始行由 ops 记为 unfinished（该表不进 `turns`，质检队列不受影响）。阶段口径：`understand`（`vocabulary` / `attachments` / `jev`（含重试退避，成功调用自身的秒数仍在 `understanding.jev.seconds`）/ `parts` / `calls` 与逐调用 `understand.call.<ability>`）、`model`（`attempt_1` / `attempt_2` 与模型自己的每次工具调用 `model.tool.<ability>`）、`ground`、`hydrate`（水合＋补价查询）、`template`（兜底渲染）、`log`；未跑的阶段不出现（非 null）。`ops/turn_latency.py`（stdlib）打印 completed/incomplete/unfinished 计数与各阶段及总时长的 count/p50/p95/max（nearest-rank，只统计 completed），并可按 `--conversation` / `--locale` / `--since` / `--until` 切片。服务端 `total` 是流水线口径；客户可见 p95 由 #336B 基线在客户端测（WP 代理缓冲整包，壳另加最多 1.2 s 渐进显示）。数字与阶段为自行设计：无公开竞品 SLO（dossier `2026-10-19-genie-campaign-gaps` §1.14）；业主裁定无后端流式，故无首字可测，以"到首个 SSE 事件"代替（`2026-10-18-genie-reply-design/REFERENCES.md` 实施边界）。
- 2026-10-19（#251 零件清单变成产品）：见"零件清单 → 产品"。新增服务模块 `parts.py`（解析、匹配、逐条确认、一次加入）与 `parts` 块（`schema.PartsBlock`，服务写、模型不可写）；`lexicon` 加 `brand_members` / `brand_of`；`attachments` 收 CSV 与 .xlsx 并读成 `kind="list"` 的 reading（`AttachmentReading.truncated`）；`Understander` 在铭牌之后、Jev 之前判定清单，路由 `parts` 不经模型；壳新增 `PartsCard`（`src/genie/components/`）与 `store.addAll` 的一次写入（读回短于请求时再读一次，见规格 14 的实现 `store.ts`）；dock 输入框改为 textarea（多行粘贴，Enter 发送、Shift+Enter 换行）；附件选择接受 CSV/Excel，预览卡首页第四条改为"上传清单"（替换"配什么电池"，保持目标 4 的 2–4 条）。规格 13 的附件一节与 §B 的请求字段同步。文案评审 `docs/acceptance/2026-10-19/251/copy-review.md`，验收 `docs/acceptance/2026-10-19/251/`。
- 2026-10-18（#236 拍照识别与附件读取）：见"附件与铭牌"。新增服务模块 `attachments` / `vision` / `nameplate`、路由 `nameplate`、工具名 `linker/read-attachment`（`facts` 与质检认得）、`TurnRequest.attachments` / `readings`、SSE `attachment` / `reading` 事件；`build_model` 的 profile 关闭文档输入；系统提示词加"Attached files"一段（EN/DE）。壳：`Attachments`（类型、大小、每小时额度）、`Thread::READINGS` 与 `Thread::split`、dock 的回形针真正发送文件（`src/genie/attachments/`、`AttachmentCard`、`AttachmentChips`）、首页预览卡第四条"拍铭牌"与加载器的 `{attach:true}`。依赖：`pillow`、`pypdfium2` 进服务主依赖（锁文件版本不变）。规格 10 的"不在 VPS 上解析"改写为只管知识索引。文案评审 `docs/acceptance/2026-10-18/236/copy-review.md`，验收 `docs/acceptance/2026-10-18/236/`。
- 2026-10-18（#243 转人工，评审第 1 轮之二，#246 合并后）：交接经 `Submission::from_handoff()` → `Sender::message()` 成为 #246 的一条联系记录，团队邮件是 #246 的（带 Genie 一节），访客收到同样的回执（受回执上限），卡与历史照实说明；访客勾选同意句；`Genie\ContactEmail`、动作 `linker_genie_contact_requested` 删除，改为过滤器 `linker_tools_genie_contact_team`。
- 2026-10-18（#243 转人工，评审第 1 轮）：短语表收窄（"team""expert""engineer"不再单独算人）；公司类联系卡也不连续两轮；重复判定改为"后一句不加词、型号与数量不变"，39 对测定；`FormGuard` 合并两扇公开表单的防护；原因标签一处；日志存 `contact` 列、不读块；不经模型的轮次 `model=none`；已发出的卡留在历史里；`ground.shipped` 检查附卡后的出货回答。
- 2026-10-18（#243 转人工）：见"转人工"一节。`route.person()` 不再调 handoff-team，找人不经模型；Jev 意图不确定而 `wants_person` 高的轮次不再整轮转人工，改为照常回答并附联系卡；`ground` 的"handoff 块独占"只管 `service`。新增服务模块 `contact.py`、`TurnLog.offers`；壳 `ContactRequest`、`ContactGuard`、`ContactCard`，mount 加 `data-contact-url`；commerce `Genie\Module`、`Genie\ContactEmail`，`Mail\TeamEmail::notify()` 收 `null`（访客，Reply-to 由子类给出）。
- 2026-10-18（#242 价格跟账号走）：见「价格跟账号走」一节。客户令牌从只带在 inquiry-status 上扩到 search-products 与 get-product，WordPress 一侧按解析出的路由绑定这三个 ability；壳发送 `partner`（站点价格规则）；`commerce` 加 `price_line` / `price_reason`；`cards` 块加服务填写的 `prices`（补查有截止）；正文禁止价格占位符；质检的职责说明改为正文从不写价格、卡上价格过两道门（规格 33）。顺带修掉产品页与对比页的三处（变更台账见规格 11）。评审第 1 轮（PR #301）：原因顺序收成一个带表面参数的函数、令牌绑定路由、TTL 与截止加来源、壳不再持有价格句子。验收 `docs/acceptance/2026-10-18/242/`。
- 2026-10-18（#235 会话全部保留）：见 §C"会话全部保留"。`Conversations` 增加浏览器钥匙（认领后与退出后更换，User Switching 不认领）、全部认领（`wp_login` + `set_logged_in_cookie`）与 `delete()`，列表按最近活动（`Thread::ACTIVITY`）排序；新增 `ConversationMail`（访客先确认地址、蜜罐与签名起始时间、全站每日上限与每连接上限）、`RateLimit`（一条语句的判断加一）、`Thread::transcript()`（带每条回答的产品）、`Proxy` 的 DELETE 与 `/email` 两条路由、admin-post 的确认链接；linker-commerce 新增 `Genie\{Module,Conversation,GenieEmail,ConversationEmail,ConfirmAddressEmail}` 与两个模板；壳：工作区侧栏宽屏不再因新建/切换收起，列表行可删除，"Email me this conversation"，确认链接结果一行。genie 的 JS 德语译文进 `linker-tools-de_DE_formal.po`（引用 `build/genie.js`），JSON 由 `wp i18n make-json` 生成。验收 `docs/acceptance/2026-10-18/235/`。
- 2026-10-18（#234 页面感知）：见"页面感知"一节。新增 `Linker\Tools\Genie\PageContext` 与服务模块 `page.py`（工具 `linker/read-page`）；`PageType` 加 `home`、`solution`、`blog`、`faq`，`PageContext` 加 `url`、`title`、`post_id`、`category_id`（只增不改）；代理按键清洗页面上下文并自己填 `draft_ids`；产品页 dock 的开场提示由三条不点名的问句换成预览卡那三条点名本产品的问句；预览卡改从页面上下文取类型与名字。验收 `docs/acceptance/2026-10-18/234/`。
- 2026-10-18（#249 主动预览卡）：见 §C"主动预览卡"。新增 `Linker\Tools\Genie\Preview` 与构建入口 `preview`（`src/preview/`）；手机端的"圆钮标记"让 860 px 以下本来隐藏的圆钮在出标记时出现（目标 4 的裁定变更，静止状态外观不变）。评审第 1 轮（PR #287）：每次访问改为跨标签页（localStorage + 30 分钟无活动）、解决方案页锚点改为 hero 之后的第一个区块、颜色改用设计变量、首页建议不写死商品、像素门入档；手机标记、对话进行中、Esc＝×、首页暂不放拍铭牌与上传清单四条裁定写入本节。验收 `docs/acceptance/2026-10-18/249/`。
- 2026-10-17（#233 理解层）：见上文"理解层"一节。新增 `lexicon` / `storeapi` / `jev` / `route` / `understand` 五个模块与 `document` 块（`DocumentBlock`，壳 `DocumentLink.tsx`）；轮次日志加 `understanding` 列（旧库自动补列），SSE meta 加 `route` / `intent` / `jev_error`。证据 `docs/acceptance/2026-10-17/233/`。
- 2026-10-16（入面取证，欠账 P1）：§C 的 Entries 条目按实例实测重述（原文把产品页与账户页的入口写成芯片组）。取证（snapshot 实例 `nbatch` + 本检出代码，逐面读 HTML）：分类/商城 2 枚 `linker-genie-chip`（短代码挂载）；产品页 `[data-pdp-ask]` 1 枚、无芯片，dock mount 带 `data-page-type="product"` 与三条产品问句的 `data-prompts`；购物车有货态 2 枚 `data-page-type="draft"` 芯片（`woocommerce_before_cart` 经 `[woocommerce_cart]` 的 Woo 模板真的触发）；空 Proforma 请求页 1 枚 `linker-gate-genie-pill`；账户页 0 芯片、dock mount 带 `data-page-type="account"` 与两条账户问句的 `data-prompts`。逐面对照验收过的设计（#174 原型变体 A 只有 `.tools-row` 与 `.plan-with`，无芯片组；#184 原型的 Genie pill 只在 `gates.html?gate=empty-proforma`，工作台各页零 Genie）：**每个面的既定入口都已挂着**，无需回挂代码；`Entries::product_chips/account_chips` 与其 Woo 钩子留作可挂载部件（`[linker_genie_chips page_type="…"]` 可显式挂载），删它们属另一裁定。判分行的入口随之更正（`genie-panel.md` B1–B3、B6、B7）。
- 2026-10-16（德语四行 e2e 恢复）：R3-de / R5-de / R6-de / R7-de 自 2026-10-11 的 `pending-main` 全部撤除。**R6-de 是服务缺陷**：兼容合同的条件是 `{en, de}` 双语对（`plugins/linker-commerce/data/compatibility.json`），而 `facts.collect` 恒取英文侧——德语轮次里 `{fact:compat.condition…}` 水合后会把英文句子插进德语答案（该行的判据：德语答案不得含英文功能词）。修复：`collect` / `AbilityClient.record` / `_ability_runner` 透传轮次 locale（`agent.py` 从 `TurnRequest` 取；`INPUT_DOCS` 与工具签名不变），条件按轮次语言取侧、缺侧回退到存在的另一侧（与 `TradeRules::word` 同规则）；`_condition_text` 同时服务 search-products 的 pairings 与 check-compatibility 两个调用点。**R7-de 是套件过期**：2026-10-13 文案评审定稿句「Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.」用的是可分动词，spec 旧正则只认 `anmelden`，永不匹配——正则补上定稿句的形态。R3-de / R5-de 复测恢复（2026-10-11 记录的失分是采样落进兜底的路径；2026-10-13 的兜底修复后多次重采样未再复现）。判分测试：`tests/test_hydrate.py`（德语取侧与半写对回退）、`tests/test_agent.py`（locale 透传）；实测与证据 `docs/acceptance/2026-10-16/genie-de-e2e/`。同轮修掉套件行循环的采样判定：`expect(attempts).toEqual([])` 会把"首采样失分、后采样达标"的行记红，与文件头、`askRow` 注释及 PR #96 的既定语义相反（#96 前段"两次都不过才算失败"、后段"最多三次采样…全不过才算失败"，新判定两者同时满足）（暴露：R6-en 2026-10-16 首采样占位符失分、二采样达标仍红）——改判 `result === null`，三采样全失才是失败/pending skip。
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
- 2026-10-17：新增"目标"一节（业主在 #240 的两轮答复 + 竞品调研 #241）；上文的产品定义与入口按本节修订，实现票以本节为准。
- 2026-10-17：目标第 2 条加入理解层（Jev 意图识别 + 代码路由 + deepseek-flash 兜底与写作），依据 #260 实测。
- 2026-10-18（#250 对话内询盘确认卡）：见"目标"第 5 条。模型可写动作 `send_inquiry`（`schema.ActionName`），客户明说"发询盘"时服务自己补上（`inquiry.py`），动作只请求展示卡；卡的写入口是 `InquiryRequest`（`linker-ai/v1/genie/inquiry`），POST 经 `Inquiry\Sender::request()` 走询盘页同一条 Woo 管线（`Genie\Module::INQUIRY_FILTER`），摘要沿用 #244（卡的开关决定是否存 `_linker_genie_summary`）；模型说"已发送"的句子由 `ground._no_sent_claim` 拒绝（A8）。壳：`InquiryCard` / `InquirySent`，已发出的卡随 `inquiries[]` 留在历史里；`Sender::request()` 加 `$summary` 参数；`InquirySummary` 的缓存键加语言（同一会话 EN/DE 两页各得各的摘要）；`.po` 30 条新译文。文案评审 `docs/acceptance/2026-10-18/250/copy-review.md`，验收 `docs/acceptance/2026-10-18/250/`。
- 2026-10-19（#232 首页 hero）：见"首页 hero"一节。新增 `Linker\Tools\Genie\Hero` 与构建入口 `hero`（`src/hero/`）；`Entries` 的 dock 加载器把 `linker-genie-ask` 的 `refresh` / `fromHome` 传给 App，App 用 `showStored()` 重读 hero 写的线程并显示来源行；hero 与 dock 共用会话文章与 cookie（`Conversation` 的既有规则，不改数据层）。验收 `docs/acceptance/2026-10-19/232/`，像素门外差异 0（首页 EN/DE × 1440/390）。
