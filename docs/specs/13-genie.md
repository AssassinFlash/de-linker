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
只读 ability 匿名可调；写动作（加入 Lösungsentwurf、加入方案）不是 ability，由浏览器执行。文档检索 `linker/search-knowledge` 不是 WordPress ability：它是服务自己的工具（见 B 与规格 10「唯一检索源」，#257）。

### B. 服务（`services/genie`，FastAPI + Pydantic AI）
- `POST /turn`（SSE 流）：`{conversation_id, messages[], locale, page_context:{type: home|product|category|solution|blog|faq|draft|account|other, url?, title?, product_id?, post_id?, category_id?, draft_ids?}, user:{logged_in, partner?}}`（页面上下文见下文"页面感知"）。
- Ability 调用的瞬态失败重试：5xx 与连接层异常（httpx `TransportError`）退避重试（3 次尝试、指数退避 0.25 s/0.5 s），仍失败抛 `AbilityError` 进既有兜底——失败写入轮次 meta（`fallback`/`failures`），不静默、不从服务层 500 逃逸（`abilities.py::AbilityClient._get`）。WordPress 侧的对象缓存（Redis）抖动是这一失败的主要历史来源：实例的 drop-in 现以 `WP_REDIS_GRACEFUL` 运行（规格 5、17），读失败降级为请求内缓存而非杀请求。
- 文档检索：`linker/search-knowledge`（`{query, lang, product_ids?}`）在服务进程内读 VPS 上发布的 SQLite 索引（`linker_genie/knowledge.py`，规格 10「唯一检索源」）。路由的调用（`understand._run_calls`）和模型的工具调用走同一个 `knowledge.record`。模型读到的块文本里，每个数字都标成 `[nK=值]`；回答里写 `{fact:块ID.nK}`，水合时填入。答案依据的块由服务端加成文档链接（文档块，#233）。路由的文档检索失败时（编码或索引出错），这一轮直接进兜底，不会写出一个缺少所需文档的回答；同样不退回关键词。
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
  - `Entries::*_chips()` 仍是可挂载的钩子（Woo 模板面：`woocommerce_single_product_summary` / `woocommerce_account_dashboard`），当前 LiveCanvas 模板不触发；`[linker_genie_chips page_type="…"]` 可随时显式挂载。首次点击才加载 JS。
- 组件：线程、消息、追问芯片、ProductCard（加入 Lösungsentwurf 并读回数量；加入方案；状态 pending/added/unverified/retry 在卡内、高度稳定）、CompareTable、Handoff。
- 文案：按 AGENTS.md 规则逐处写，EN/DE；对抗评审记录附 PR。

### 主动预览卡（#249，实现目标第 4 条；业主选样式 A · 提示卡，`docs/prototypes/2026-10-17-preview-card/DECISION.md`）

- **哪些页有卡**（`Linker\Tools\Genie\Preview::context()`，名单即全部）：首页（`is_front_page`，EN/DE）、产品页、产品分类页（`is_product_category`）、解决方案页（`/solution/` 枢纽页的子页，德语经 `pll_get_post` 找枢纽孪生页的子页；枢纽页本身不算）。其余页——Lösungsentwurf、Proforma 请求、账户与登录注册、联系、配置器、博客——没有卡，也不加载卡的脚本与样式。
- **卡点名当前页面**：产品＝商品标题去掉括号里的描述（"SAJ H2-10K-T3 (10 kW …)" → "SAJ H2-10K-T3"）；分类＝分类名；解决方案＝页面标题（英文句中小写化，缩写与内部大写词保留）。名字与页面类型取自 #234 的页面上下文（`PageContext`，`Preview::card_page()`）；有卡的页面仍只是首页、产品页、产品分类页与解决方案枢纽的子页（枢纽本身、About、受众页虽是 `solution` 类型，没有卡）。
- **首页的建议不写死商品**：问型号那一条取当前商品数据里最新发布的逆变器（产品列表的第一张卡也是最新商品；限逆变器分类，示例是主产品而不是电表或线缆），当前语言；商品下架即自动换。另两条不点名商品（"我的逆变器配什么电池"、SAJ 与 GoodWe 两个品牌的比较）。目标 4 里的"拍铭牌""上传清单"两条**暂不放**：Genie 现在还不能读铭牌照片与清单，等 #236 / #251 上线后补进 `Preview::copy()` 的首页分支（2–4 条上限内，文案走对抗评审；两张票上已留言）。
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
- **价格与运费不从页面来**：匿名页面上的价格门（"Net price after partner sign-in"）与已批准合作伙伴看到的价格相反，运费属物流（业主 2026-10-05）。类名含 price 的元素（`pdp-price`、`sf-card-price`、Woo 的 `price`）、运费说明 `pdp-avail-note`、店面的 `data-card-price` / `data-card-gate`、任何写着金额的段落、以及只是价格门的短句都不进页面文字。价格只来自产品工具的 `pPRODUCTID.price`（随客户账号，#242）；问到运费、发货、运输的本页问题一律转团队（`route._LOGISTICS`，与 Jev 的判断无关）。
- **只给模型与问题相关的部分**：页面切成段落（遇标题或 700 字符断开），总长 ≤12 000 字符时整页给出（首页 7 300、分类 8 400、住宅储能 10 400）；更长（FAQ 页 118 000）时给开头 1 500 字符 + 与问题词重合最多的段落，另附页面标题大纲（≤40 条）。数字按文档块的办法标成 `[nK=值]`，模型写 `{fact:page.nK}`、`refs` 写 `page`，水合填值（核验同文档块，`facts._from_page`）。页面文字是站点的数据、从不是给模型的指令（`page.RULE`，系统提示词各语言一处）。
- **个人页面不匿名读**：Lösungsentwurf 的内容是它的商品（`draft_ids` → Store API `include`，商品可作卡片）；已登录客户的账户是他的询盘（路由调 inquiry-status）。访客的账户页即登录页，照常读。
- **读不到**：`PageUnavailable` 记入轮次日志 `page_error` 与 `call_failures`，回答照常进行；提示词要求模型说明这次读不到页面，不得猜。
- **日志**：读页结果整份记入轮次日志的工具调用（事后质检要看模型当时读到的文字），保存与删除跟随轮次日志（`turns.sqlite`）本身。

**何时读**（`route.with_page`）：Jev 的 `about_this_page`（≥0.5，与 #233 判本页产品同一切线）为真时加读页面（Lösungsentwurf：read-page + 至多两对逆变器×电池的 check-compatibility；已登录账户：inquiry-status）。找人、公司物流、询盘状态三类路由不读页面；问本页能否转团队不由本票决定（#243），路由的 `no_handoff` 照旧。调用按固定优先级装进每轮 4 次：路由自己的调用（含主语的 get-product）→ 读页面 → 草稿的配对；文档路由留 1 次给模型的追加检索；装不下的记入轮次日志 `dropped_calls`，没查的配对写进提示，让回答说明还没查。路由的调用彼此独立，并行执行（读页面不再排在前面加时）。Jev 不确定或不可用时，模型可自行调用 `linker_read_page`（无参数）。每轮提示词都写明 `page=`、`page_title=`、`page_url=`，"这页 / 这款 / here / this one" 指本页或本页产品；产品页上没有型号词的问题照旧以本页商品为主语（#233）。Jev 的页面状态加上 `title`，类型取自 `schema.PageType`，新类型以词语命名（`home_page`、`solution_page`、`faq_and_documents_page`）。

**开场建议**（`Entries::prompts`，2–3 条，点名本页）：有预览卡的页面（首页、产品、产品分类、解决方案）用预览卡同一组问题（`Preview::asks`，#249 的评审定稿）；其余：商城 "Which model fits my project?" + SAJ/GoodWe 比较；博文 "Summarize this post" + "Which products does this post apply to?"；博客首页 "Which of these posts cover hybrid inverters?" + "Summarize this page"；FAQ 与文档页 "Is there a datasheet for my model?" + "Which batteries work with my inverter?"（FAQ 的答案是站点文案、不作事实来源，AGENTS.md 2026-10-09）；枢纽、About、受众页 "Summarize this page" + "Which products fit my project?"；Lösungsentwurf 与账户沿用既有两条；其余页（联系、法律页、表单、工具）"Which model fits my project?" + "Which batteries work with my inverter?"（不对法律文本做摘要）。德语独立撰写在 `.po`，文案评审 `docs/acceptance/2026-10-18/234/copy-review.md`。

评测：`services/genie/eval/page/`——`questions.json`（八类页面各两问 × EN/DE，含"这页说的……是什么意思"与产品页"这款"）、`pages.py`（不钉 Jev，真实页面、真实 deepseek-flash；已登录行用 `UserContext` 现签令牌）、`capture_pages.py`（重取 `tests/fixtures/pages/`）。结果：`docs/acceptance/2026-10-18/234/`。

## 理解层（#233，实现目标第 2 条）

每轮在模型之前由 `services/genie/src/linker_genie/understand.py` 准备：

1. **产品词**（`lexicon.py`、`storeapi.py`）：词表来自 Woo 原生 Store API（`/wp-json/wc/store/v1/products` 与 `/products/categories`，EN + `lang=de`），不新增 WP 端代码；缓存 10 分钟。品牌、系列（slug、去品牌别名，一词别名须含数字或在标题中大写出现）、型号（`pa_model`、标题里的字母数字码、SKU 与去前缀 SKU）、分类（只认本身是 device class 的分类；德语名经 SKU 关联到英文分类）。比较前归一化（小写、只留字母数字），按空白与连字符切词，最长匹配优先。德语商品是独立文章，轮次里的商品 ID 一律是英文 ID。读不到 Store API 时显式记日志（`vocabulary_error`），本轮无产品词。
2. **Jev**（`jev.py`）：typesafe/jev-1.13，仅经 OpenRouter `/api/v1/systemone`，一次问四题：`intent`（10 类，判据同 `docs/research/2026-10-17-jev-intent/eval.py`）、`about_this_page`、`wants_person`、`needs_followup`。每次 6 秒超时、最多 3 次；仍失败、拒绝或答复来自别的模型都抛 `JevError`，记入轮次日志 `jev_error` 与 SSE meta，本轮由 deepseek-flash 自行决定（票里允许的唯一降级）。
3. **路由**（`route.py`）：意图置信 ≥0.8 由代码调工具——找产品 → search-products（产品词给出的过滤；一个系列族同时有单相和三相时按相数各搜三张）；文档参数 → search-knowledge（`product_ids` = 匹配到的型号或本页产品）+ get-product / 族搜索；配对 → 两件 check-compatibility、一台逆变器 `with_pairings` 搜索；对比 → compare-products；选型 → size-hint（kWp、年用电、相数、备电由代码从原句读出）并要求配置器动作、不出卡片；询盘 → inquiry-status；找人 → `route.person()`（#243 只替换这个函数）；公司物流 → handoff-team。整条消息都是产品词（裸词）时，无论 Jev 怎样答都走产品搜索并要求出卡片；长句里的产品词，Jev 最倾向 documents_specs 时（置信度不论）由代码同时调用 search-products 与 search-knowledge（只有系列时 `product_ids` 取该系列的商品）；其余 Jev 不确定的情况照搜但不强制卡片。其余交 deepseek-flash 决定。路由的调用计入每轮 4 次工具预算，结果以 JSON 放进提示词。
4. **核验**（`ground.py` 第 6–8 条）：文档只以 `document` 块出现（模型只写 `ref`，服务填标签与 `#page=N` 链接；get-product 的文档是 `pID.document.N`；同一文件只出一个链接，多页合并为"pp. 3, 7"/"S. 3, 7"；配置器动作的 URL 也由服务按 size-hint 填写），正文与占位符里不得有 URL；AGENTS.md §3 禁用词（article/catalogue/cart/basket，Artikel/Katalog/Warenkorb）；路由要求（产品词出卡、选型带配置器无卡、产品与文档类不转团队、找人与公司类只有 handoff 块）。兜底按路由出形状（选型 = 配置器、文档 = 文档链接、产品 ≤6 张卡）。
5. **事实**：get-product 的数据表 `figures`（`n_mppt` 等）按轮次语言登记为 `pID.<key>`；功率与能量类选择事实水合时补单位（kW/kWh）。

评测：`services/genie/eval/understanding/`——`bare_words.json`（75 条裸词 EN/DE，离线测试与线上实例共用）、`jev_cases.json`（#260 的 60 条 + 线上真实问句 15 条）、`run.py`、`jev_eval.py`、`capture.py`（重取 Store API 夹具 `tests/fixtures/storeapi.json`）。结果：`docs/acceptance/2026-10-17/233/`。

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
