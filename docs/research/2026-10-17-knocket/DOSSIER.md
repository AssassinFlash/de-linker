# Genie · Knocket（trtc.io）能否替代 Genie（#259）

- 日期：2026-10-17；取证窗口 UTC 08:12–08:40
- 票：#259（地图 #220）。对照基准：`docs/specs/13-genie.md`"目标"十条与验收 A1–A14（`docs/research/2026-10-17-ai-assistants/INTL.md` §6），AGENTS.md §2、§5
- 取证通道：外部文档全部经 Apify（11 次本人运行，actor、run id、用途见 `raw/apify/runs.json`；同一时段另有 2 次不属于本票的运行已剔除）。产品本身的行为是一手实测：SDK 文件用 curl 取回做静态阅读；业主那段 snippet 只在一个本机一次性页面（`http://127.0.0.1:8765`）里加载过，没有贴到任何站点或仓库代码里；没有向业主的 Knocket 租户发过任何消息。AI 回答质量的实测打的是 **Knocket 自己官网上的 AI**（它们自己的租户），2 条消息
- 密钥：Apify 令牌只在进程环境里，没有打印或落盘。Knocket 接口返回给访客的 `userSig` 在写盘前一律替换成 `<redacted>`（`raw/scripts/slim.py` 写盘时逐个断言）

## 0. 结论先行

**不替代 Genie，也不建议作为补充装到 de-linker.com 上。** Knocket 是一个免费的"在线客服气泡 + 联系页 + 统一收件箱"，AI 只是挂在收件箱前面的一层"按上传资料答常见问题、答不了转人工"。业主要的 Genie 是能查我们 Woo 产品、懂当前页面、替客户加 Lösungsentwurf 和发询盘的选型助手，两者不是同一种东西。逐条对照：十条目标里 0 条满足、3 条部分满足；A1–A14 里 0 条满足、4 条部分满足；AGENTS.md 的五项硬约束一项也过不了（§6）。

最硬的五条证据：

1. **厂商自己说它不是 AI 助手套件。** 原话："Knocket is not a CRM, helpdesk, or AI chatbot suite. It is a lightweight contact widget for indie makers and early ecommerce teams."（S9，Knocket 官方 WooCommerce 文章）
2. **不懂页面、不能做事，这是它自己的 AI 当面说的。** 我在 Knocket 官网的 Web Widget 产品页上问它"我现在在看哪一页"，它答"Ob Sie gerade genau diese Übersichtsseite sehen, kann ich ohne weitere Angaben nicht bestätigen"；问它能不能调我自己的 REST API 查登录客户的价格并加购，它答"Nein … sie kann auch keine Aktionen wie das Hinzufügen zum Warenkorb über Ihre REST-API ausführen"（§4.4，`raw/probe/ai.slim.json`）。SDK 里也找不到任何把页面、身份、语言传给它的接口（§4.2）。
3. **知识库上限 30 条。** "Up to **10 items per tab** — 10 FAQs, 10 URLs, 10 files"（S2）。我们有几百个 SKU 和成百份托管 PDF，覆盖不了，也没有结构化产品数据、兼容合同、按账号的价格。
4. **违反模型路由铁律。** 对话模型可以自带 key、可以选 DeepSeek，但知识库的向量化由平台托管："Embedding credentials for the knowledge base are managed by the Knocket platform — you only configure the chat-completion side here."（S2）。这是第五条、名字都不公开的模型通道，AGENTS.md §5 明令不得出现。
5. **DSGVO 过不了。** 不点任何东西、页面一加载，脚本就在腾讯服务器上建访客、上报完整页面 URL、开 SSE 和 WebSocket、写 4 个 localStorage 键（§3.1）；业主这个租户的聊天走 Knocket 共用的腾讯 IM 应用，WebSocket 主机是 SDK 自带区域表里的 **SINGAPORE** 节点（§3.2）。新加坡不在欧盟充分性决定名单上（S24）。腾讯的隐私政策写明可能转移"例如到中国大陆"（S18）。打开面板还会从 `fonts.gstatic.com` 拉字体（§3.1）。

能借鉴的只有一处：它的"转人工短语库"（50 种语言、218+ 条、命中就转、不调用模型，S5）。Genie 目标 6 可以照这个思路，在服务端维护一张短语数据表。这只是一个思路，不需要引入 Knocket。

## 1. Knocket 是什么

腾讯云 TRTC（Tencent RTC）于 2026 年 3 月推出的免费"联系层"产品，域名 `knocket.trtc.io`，联系页在 `knocket.ai/<slug>`。三种形态（S3）：

| 形态 | 是什么 |
|---|---|
| Web Widget | 网站右下角的聊天气泡，一行 `<script>` 安装（业主拿到的就是这个） |
| Contact Page | 类似 link-in-bio 的联系页，`knocket.ai/<slug>` |
| Mobile Widget | 用 WebView 把联系页嵌进 App |

三种形态背后是同一个收件箱，可以接 Telegram（引用回复直达访客）和邮件别名（S3）。官方定位："Knocket is built for the kind of team that does not have a support team yet."（S3）；"Knocket is for people still looking for their first 100 users."（S12，WordPress.org 插件页）。

**AI Agent**（控制台左栏一组三页，S2）：

- Setting：总开关、覆盖哪些渠道、什么时间值守（Always / When offline）；Bot 卡（头像、名字、欢迎语 ≤400 字、System Prompt ≤2000 字）；LLM 卡（provider、API key、API URL、model ID，要求 OpenAI Chat Completions 兼容）；Handoff 卡（转人工短语、通知渠道：浏览器推送、Telegram）。
- Knowledge：FAQ、URL 抓取、文件上传（PDF/TXT/DOC/DOCX/HTML/MD/CSV/XLSX，每个 ≤10 MB），每类最多 10 条。
- Usage：请求数、转人工数、平均响应时间、按模型的 token 用量。

AI 的工作方式："The AI Agent sits between an incoming visitor message and your inbox. If it can answer confidently using the knowledge you've provided, it replies instantly in the visitor's language. If it can't — or the visitor asks for a human — it silently transfers the chat"（S2）。转人工两层：短语库命中直接转、不调用模型；其余由模型调内置的 `transfer_to_human` 工具（S3）。这是文档里提到的唯一一个工具。

**Web Widget 能配置的东西**（S4）：界面语言（一个下拉，整只气泡一种语言）、主色、气泡样式（圆钮或"Chat with us"药丸）、首页 FAQ、欢迎标题与描述、Live Chat 卡、会议预约链接、四个社媒链接、助手名字、问候语、在线时间（时区 + 时段）、离线留言、访客信息表单（Off / 对话前 / 离线时；姓名、邮箱、电话、留言各自可选必填）。附件："attachments (images, videos, files) are supported in every conversation and land in your inbox and Telegram"（S4）——附件进的是人工收件箱，文档没有说 AI 会读。

文档还说"Proactive greeting … after a configurable delay"，以及可以在脚本前声明 `window.knocketConfig` 来"Set custom user IDs, pass session context"（S3）。**这两样在当前 SDK 里都不存在**：3.19 MB 的 SDK 里 `knocketConfig`、`proactive` 出现 0 次，脚本只从 URL 读 `identifier`、`type`、`autoShow` 三个参数（§4.2，`raw/sdk/sdk-facts.json`）。

## 2. 模型

- **对话模型可自带。** "This wires the agent to any provider that speaks the OpenAI Chat Completions protocol."；"pick a preset (OpenAI, Hunyuan, DeepSeek, etc.) or choose **Custom**"；示例 model ID 写着 `kimi-k3`、`deepseek-v4-flash`（S2）。控制台默认值："The default in the console today is `kimi-k3` via the Tencent MaaS tokenhub"（S3）。所以技术上可以填 `https://api.deepseek.com` + 业主的 DeepSeek key + `deepseek-flash`。
- **但调用从腾讯服务器发出，key 存在腾讯。** "API Key — the secret for the selected provider. Stored encrypted"（S2）。对话内容先经腾讯 IM 与 Knocket 后端，再由它们转给 DeepSeek。
- **向量模型不可选，也不公开。** 原文见 §0 第 4 条（S2）；FAQ 又重复了一次："Embedding for the knowledge base is managed by the platform and included."（S2）。知识库与（大概率）每条访客查询都要过这个模型。
- **失败是否显性暴露：未知。** 文档只说 Test Connection 会显示原始 HTTP 错误；运行时 LLM 失败后是报错、转人工还是静默，文档没写，我也没有在业主租户上开 AI 去试（见 §8）。
- **"不拿你的数据训练第三方模型"**："Knowledge base contents and conversation transcripts are used only for retrieval at reply time and analytics inside your own account."（S2）。这是 FAQ 里的一句话，不是合同条款。

对照铁律（AGENTS.md §5）："全站只存在四条模型通道……禁止临时起意用任何其他模型替代……OpenRouter 调用失败必须显性暴露"。Knocket 的平台托管向量模型就是第五条通道，单这一条就不满足；对话模型即使配成 deepseek-flash，路由也多了腾讯这一跳，失败语义未知。

## 3. 数据保护（DSGVO）

### 3.1 实测：加载就上报，不等同意

本机一次性页面只放业主的 snippet，Chromium、`de-DE`、1440 与 390 两个视口，各加载一次（`raw/probe/load-1440.json`、`load-390.json`，UTC 2026-10-17 08:20 前后）。**没有任何点击**的情况下：

| 时序 | 请求 | 内容 |
|---|---|---|
| 1 | `GET trtc.io/knocket-sdk/sdk.js` | 3 187 989 字节（brotli 传输 883 074 字节），`cache-control: no-cache` |
| 2 | `GET trtc.io/knocket-sdk/sdk.css` | 插进宿主页 `<head>` 的全局样式表 |
| 3 | `POST api.trtc.io/common/portal-api-lc` `ModifyTenantWidgetStatus` | `{"identifier":"f145fd3b67d64f4704","type":"widget","host":"http://127.0.0.1:8765/index.html"}`——**完整页面 URL** |
| 4 | 同上 `CreateVisitor` | 在腾讯侧建访客 `web_b956bbcbb9` |
| 5 | 同上 `DescribeWidgetConfig`、`DescribeContactFormState`、`DescribeWidgetUiVersion` | 取配置 |
| 6 | `GET api.trtc.io/common/portal-live-chat-events?...`（EventSource） | 常驻长连接 |
| 7 | 同上 `DescribeUserSig` | 下发访客 IM 登录凭证（已打码） |
| 8 | `wss://20032564w4s.my-imcloud.com/binfo` | 腾讯 IM 长连接，SDKAppID 20032564 |
| 9 | `GET web.sdk.qcloud.com/im/download/error-message/...` | IM SDK 资源 |

加载后 localStorage 多了 4 个键：`tim_error_assistance`、`visitorId-f145fd3b67d64f4704`、`imUserInfo-f145fd3b67d64f4704`、`TIM_20032564_f145fd3b67d64f4704_vis_web_b956bbcbb9_profile`；没有 cookie。打开面板后，请求的主机里多了 `fonts.gstatic.com` 与 `console.trtc.io`（`raw/probe/open-1440.json` 的 `hosts`）。

含义：

- 往终端设备写 localStorage 属于 § 25 TDDDG 管的范围，非"绝对必要"就要事先同意（S26 检索结果）。气泡只是被加载、访客还没想聊，写入就已经发生，很难说成"绝对必要"。所以要上就只能放在 Complianz 后面、同意后才加载（Knocket 自己的博客也是这么建议的："If your site uses a consent banner, load the script after the visitor has accepted the relevant category."，S10）。后果是没点同意的访客根本看不到助手。
- 打开面板就从 Google 拉字体，等于把访客 IP 交给 Google。LG München I 2022-01-20 判决（3 O 17493/20）认定未经同意动态加载 Google Fonts 违法（S25 检索结果）。

### 3.2 聊天记录存在哪里

- 腾讯 IM 的存储地点由应用（SDKAppID）创建时选的数据中心决定："Chat provides Southeast Asia (Singapore and Jakarta, Indonesia), Northeast Asia (Seoul, South Korea and Tokyo, Japan), Europe (Frankfurt, Germany), North America (Silicon Valley, USA), and Saudi Arabia (Riyadh) Data Centers for selection. Your business stores data in the Data Center selected when you Create Application"（S19）。
- 业主租户实测连的是 `wss://20032564w4s.my-imcloud.com`。SDK 自带的区域表里，`*w4s.my-imcloud.com` 属于 `SINGAPORE`，德国是 `*w4g.my-imcloud.com`（`raw/sdk/sdk-facts.json` 的 `im_region_table_excerpt`）。DNS 解析只得到腾讯全球加速器的任播地址（`raw/apify/dns.json`），定不了位，区域表才是决定性证据。
- SDKAppID 20032564 是 Knocket 的应用，不是业主自己的：访客 IM 账号形如 `f145fd3b67d64f4704_vis_web_b956bbcbb9`，业主后台账号是 `f145fd3b67d64f4704_adm`（租户 ID 作前缀）。由此推断（未经厂商确认）：所有 Knocket 租户共用这一个新加坡应用，业主没法给自己选法兰克福。Mobile Widget 页面写着"Data region controls in the console"（S11），我没有业主控制台的登录权限，核实不了这个开关是否存在、能不能作用到 Web Widget（§8）。
- `api.trtc.io` 后端（访客、表单、配置、AI 调用）的机房地点：未公开，DNS 指向 EdgeOne 边缘节点，定不了位。
- 新加坡不在欧盟充分性决定名单上（S24，名单里有 Andorra、Argentina、Brazil、Canada、Japan 等，没有 Singapore，也没有 China）。

### 3.3 合同与政策

- Knocket 的法务页就是腾讯云通用条款。欧洲经济区客户的签约方是 Tencent Cloud Europe B.V.（阿姆斯特丹），适用英格兰与威尔士法（S7 §3(a)）。
- DPA：腾讯云有通用的 Data Processing and Security Agreement（S17），引用 2021/914 新版 SCC（Module 2/3），可以充当 AVV。但它允许在服务区之外处理："Tencent, for operational, regulatory or other reasons, may need to Process Personal Data outside the Service Region from time to time"（S17 §5.2）；子处理者采用一般书面授权（S17，SCC Clause 9 Option 2）。Knocket 这种免费产品是否以及怎样纳入这份 DPSA，页面上没有写（§8）。
- Knocket 的隐私页（"Last updated: 2026-10-15"）是腾讯 IM 通用模块，讲的是 IM 日志、监控、配置数据，**没有一个字讲 AI Agent、知识库、LLM key 或第三方模型**（S6）。
- 腾讯云主隐私政策写明："To the extent data is transferred outside of the EEA or UK for processing (for example, to Mainland China), we rely on the European Commission's model contracts … pursuant to Decision 2001/497/EC … and Decision 2004/915/EC"（S18）。这两份旧版 SCC 决定已被 2021/914 取代，政策正文还在引用旧依据，DPSA 用的是新版，两份文件之间不一致。
- 第三方参考：EU Sovereignty Score 把 Tencent Cloud 列为"GDPR compliance is limited or unclear"（S20）。这是聚合站的评分，仅作旁证。

结论：按现状装上去，de-linker 作为控制者要为"加载即上报 + 新加坡存储 + 可能流向中国大陆 + 政策里没写 AI 处理"逐项做 TIA 和隐私声明，而且这些问题都不在我们能配置的范围内。

## 4. 集成

### 4.1 它在页面上做了什么（静态阅读 + 实测）

- 脚本在 `DOMContentLoaded` 后自动执行：往 `<head>` 插 `sdk.css`，往 `<body>` 末尾插 `div#contact-widget-auto`，在里面 `attachShadow({mode:"open"})`，React 应用的样式全部注入 shadow DOM（`raw/sdk/sdk-facts.json`）。
- 样式隔离实测是好的：加载前后宿主页 `body` 的字体、字号、外边距不变（`Georgia, serif|18px|40px` → 同值）。`sdk.css` 只含 `.widget-sdk-*`、`.trtc-*` 类选择器，没有 `html`/`body`/`*` 规则（19 067 字节）。
- 体积：每页 3.19 MB 原始 JS（传输约 883 KB），响应头 `cache-control: no-cache`，每次加载都要回源校验。
- 对外接口只有 `window.contactWidget`：`show/hide/toggle/setContainerStyle/openFloat/hideFloat/showChat/hideChat/showChatCard/setOverlayStyle/on/once/off/emit`，事件 `ready/firstMessageSent/chatReady`。**没有**设置用户身份、页面上下文、语言或预填消息的入口；SDK 里 `navigator.language`、`documentElement.lang`、`document.referrer` 都是 0 次。
- 界面语言是租户级单一设置。业主租户现在是 `"language":"en"`，浏览器 `de-DE` 打开面板也是英文（`raw/probe/open-1440.png`、`open-390.png`）。我们的德语页面没法让它自动变德语，除非每种语言各开一个租户再按语言换 snippet。
- SDK 内置 50 种界面语言，德语用 Sie（如"Bitte geben Sie die E-Mail-Adresse erneut ein."）。界面文字是厂商写死的：首页卡片固定显示"We reply within a few minutes"；英文版邮箱校验错误写成"The order could not be found. Please re-enter."（`raw/sdk/sdk-facts.json`）。这些都过不了文案对抗评审，我们也改不了。

### 4.2 能不能接我们的 WordPress / WooCommerce

不能。知识只有三种来源：手写 FAQ、抓取公开 URL、上传文件，每类最多 10 条（S2）。没有自定义工具、没有 webhook 进 AI、没有函数调用（文档提到的唯一工具是内置的 `transfer_to_human`，S3）。没有身份接口，所以分不出访客、待审、已批准账号，价格只能写死进知识文本，那等于对访客公开价格，违反价格门。访客留下的联系方式走 `SubmitContactDetails` 进 Knocket 收件箱（`raw/sdk/sdk-facts.json`），不进 WordPress、不进 Outbox，也就绕过了 2026-10-17 定的内部通知链（sales@sunriverinverter.com）。

官方 WooCommerce 文章对"触发"的说法："Knocket is intentionally simple, so think of 'triggers' as buyer moments and message placement—not complex automation rules."（S9）

### 4.3 业主租户的当前配置（`DescribeWidgetConfig` / `DescribeContactFormState` 实测返回）

`heading:"Welcome👋"`、`yourName:"Assistant"`、`language:"en"`、`timezone:"UTC+08:00"`、`timeRanges` 周一到周五 09:00–21:00 但 `availableTime:"always"`、`faqs.enabled:false`、邮箱必填的访客表单 `contactFormTiming:"off"`、`logoUrl` 是 de-linker logo；`AiActive:false`、`AiCapabilityAvailable:false`；`UpdatedAt:"2026-10-17T08:00:06.135Z"`。也就是说，此刻装上去只是一个**纯人工**的聊天气泡，消息进业主的 Knocket 收件箱，没有任何 AI。

### 4.4 AI 质量实测（Knocket 自己的租户 `6322e0c8aa1daebe1c`，`AiActive:true`）

在 `https://knocket.trtc.io/products/web-widget/`（Knocket Web Widget 的产品页）打开它自己的气泡，发 2 条（`raw/probe/ai.slim.json`、`ai-2.png`）：

| UTC | 发出 | 它的回答（原文） |
|---|---|---|
| 08:32:34 | Guten Tag. Welche Seite sehe ich mir gerade an, und welches Produkt wird hier beschrieben? | "Guten Tag! Das hier beschriebene Produkt ist Knocket, eine Plattform mit Pages, dem Web Widget und einer Inbox. … Ob Sie gerade genau diese Übersichtsseite sehen, kann ich ohne weitere Angaben nicht bestätigen. Können Sie mir kurz den Seitentitel oder die Adresse nennen?" |
| 08:33:15 | Can your AI agent call my own REST API to look up a product's price for a logged-in customer and add it to their cart? | "Nein. Die KI verarbeitet keine Bestellungen oder Zahlungen, und sie kann auch keine Aktionen wie das Hinzufügen zum Warenkorb über Ihre REST-API ausführen. Sie kann Produkte, Preise und Richtlinien beschreiben und führt Kaufaktionen an Ihr Team weiter. …" |

观察：① 站在 Web Widget 产品页上，它说不出当前页面；② 自认不能调外部 API、不能加购；③ 第二条是英文提问，它用德语回答，和文档"replies in the visitor's language"不符；④ 回答是纯文本气泡，没有卡片、没有可点的下一步；⑤ 面板顶部只有"AI Assistant · Offline"，没有"可能出错"一类的固定提示。

## 5. 价格、锁定、成熟度

- **价格**：核心功能永久免费，含 AI（自带模型 key 的 token 费自付）："Everything we ship today is free forever — and that already includes AI."（S8）。以后收费的方向："more integrations, more automation, developer APIs, team collaboration features"（S8）。
- **限制**：知识库每类 10 条、文件 ≤10 MB（S2）；第三方测评引用 Toolradar 称没有团队角色、联系页不能用自定义域名、没有原生回复 App（S13，聚合评述，未逐条核实）。
- **锁定**：会话、访客、知识库都在 Knocket；导出能力文档没写（§8）。腾讯条款允许随时改动或停止服务："Tencent may discontinue or make any changes to the Services (or any portion thereof) at any time without incurring liability to you."（S7 §4(e)）
- **成熟度**：
  - 2026-03-19 Tencent RTC 的 Medium 文章："It works great for live chat, but it had no AI features."（S16）；LinkedIn 帖（6 个月前）："Just 2 weeks ago, we launched Knocket"（S15）。
  - WordPress.org 插件 1.0.2 仍把 AI Agent 列在"Coming soon"，"There are no reviews for this plugin."（S12）；PeerPush 2026-07-27 上架，"Reviews (0)"（S14）；Product Hunt 页两次抓取都只拿到外壳（§8）。
  - 隐私模块 2026-10-15 更新；SDK 文件 `last-modified: Thu, 15 Oct 2026`。上线约 7 个月，AI 功能更新，没有找到任何独立用户评价。

## 6. 打分

记号：✅ 满足 · ◐ 部分 · ✕ 不满足。

### 6.1 Genie 目标十条

| # | 目标 | 分 | 依据 |
|---|---|---|---|
| 1 | 本职：找产品→配对→文档→Lösungsentwurf→询盘；公司类问题转团队；"让 Linker 联系我"；全站唯一对话入口 | ✕ | 只有知识问答 + 转人工 + 访客表单（§1、§4.2）；无配对、无 Lösungsentwurf、无询盘；表单进 Knocket 收件箱不进 WP |
| 2 | 理解：确定性匹配产品数据；铭牌照片、附件；零件清单逐行匹配 | ✕ | 只有 ≤30 条资料的检索（S2）；附件进人工收件箱（S4）；无结构化产品数据 |
| 3 | 页面感知：每轮带 URL/页面类型/对象 ID；点名当前产品；每类页面两条建议 | ✕ | SDK 无上下文接口（§4.1）；它自己的 AI 说不出当前页（§4.4） |
| 4 | 主动预览卡：滚动+停留、每次访问一次、30 天、白名单页、手机只出标记、不抢焦点 | ✕ | 文档说有延时问候（S3），SDK 里没有 `proactive`；`openFloat()` 可由我们自己的 JS 调用，但规则与内容都得我们写，内容也不能按页定制 |
| 5 | 替客户做事；对话内询盘只能由按钮发送 | ✕ | 无业务工具；它的 AI 自认不能调 API、不能加购（§4.4） |
| 6 | 转人工：立即提供；三轮重复提议一次；一个工作日承诺；登录客户不问联系方式；团队收到全文链接、摘要、页面、Lösungsentwurf | ◐ | 短语库 + 模型判断转人工、对话摘要（S3、S5）有；三轮规则、页面、Lösungsentwurf、身份没有；面板写死"We reply within a few minutes"，与"一个工作日"承诺冲突 |
| 7 | 记忆：会话可切换/清除/发邮箱；访客存本浏览器；登录后并入账户跨设备 | ◐ | 访客 ID 存 localStorage、历史在 IM 里（§3.1）；无会话列表、清除、发邮箱；无登录合并 |
| 8 | 价格跟账号走 | ✕ | 无身份、无实时数据（§4.2） |
| 9 | 回答形态：带图产品卡、卡内展开、不自动滚底、每条 2–3 个下一步、AI 标识与"可能出错" | ◐ | 只有纯文本；AI 名称与问候语可配，"可能出错"只能写进问候语（§4.4） |
| 10 | 首页 hero 变体 B（就地展开） | ✕ | 只有右下角浮动气泡，不能嵌进 hero |

合计：✅ 0 · ◐ 3 · ✕ 7。

### 6.2 验收 A1–A14

| # | 条目 | 分 | 一句话依据 |
|---|---|---|---|
| A1 | 打开即显示页面感知 | ✕ | 欢迎语全站同一句，无页面上下文 |
| A2 | "这个产品"不用重打型号 | ✕ | 同上；实测它反问页面地址 |
| A3 | 预览卡规则 | ✕ | 见目标 4 |
| A4 | 每条回答后 2–3 个可点的下一步 | ✕ | 纯文本气泡 |
| A5 | 转人工触发与承诺 | ◐ | 立即转有；三轮规则与一个工作日承诺没有 |
| A6 | 团队收到完整上下文（Outbox 队列断言） | ◐ | Knocket 收件箱里有全文和摘要；没有页面、Lösungsentwurf；不进我们的 Outbox，无法按 AGENTS.md 测试邮件纪律做队列断言 |
| A7 | 不重复输入（对话内容预填询盘） | ✕ | 无询盘 |
| A8 | 对话内询盘只能由按钮发送 | ✕ | 无询盘能力 |
| A9 | 会话列表与登录合并 | ✕ | 无 |
| A10 | 价格一致 | ✕ | 无 |
| A11 | 带图卡片、原地展开、不自动滚底 | ✕ | 无卡片 |
| A12 | 可把对话发邮箱或下载 | ✕ | SDK 无此功能 |
| A13 | AI 告知与"可能出错" | ◐ | 名称、问候语可配，能写进去；没有固定位置的披露 |
| A14 | 只有一个助手 | ◐ | 若与 Genie 并存即违反；若替换 Genie，入口仍是一个，但功能面见上 |

合计：✅ 0 · ◐ 4 · ✕ 10。

### 6.3 AGENTS.md 硬约束

| 约束 | 分 | 依据 |
|---|---|---|
| 模型路由铁律（§5） | ✕ | 平台托管、不具名的向量模型是第五条通道（S2）；对话即使配成 deepseek-flash 也要经腾讯转发，key 托管在腾讯，失败语义未知 |
| DSGVO / 数据驻留 | ✕ | 加载即上报 + localStorage + 长连接（§3.1）；共用新加坡 IM 应用（§3.2）；政策未覆盖 AI 处理、提及转移到中国大陆（§3.3）；打开面板拉 Google Fonts |
| 三件套原生优先；样式只在 WindPress；PHP 不做设计 | ✕ | 第三方 shadow DOM 应用，外观只能在 Knocket 控制台里配，不走 LC 模板、不走 WindPress，也读不到 Woo 数据 |
| 复刻面像素零差异 | ◐ | 样式隔离实测良好，不污染宿主页（§4.1）；气泡本身是新增像素，要走变更台账，且它与 Genie 圆钮会抢同一个右下角 |
| 文案对抗评审；EN/DE 同步、DE 独立撰写 | ✕ | 界面文字由厂商写死、不能改（§4.1）；一个租户只有一种界面语言；实测英文提问得到德语回答 |
| 承诺一个工作日内回复；询盘通知链 | ✕ | 写死"We reply within a few minutes"；联系表单进 Knocket，不进 WP 与 Outbox |

## 7. 结论与理由

**不用。** 理由按分量排：

1. 它解决的问题和 Genie 不同。Knocket 是给"还没有客服团队"的小团队用的人工在线聊天，AI 是挡在人工前面的 FAQ 层；Genie 的价值全在"读我们的产品数据、懂页面、替客户把东西放进 Lösungsentwurf 和询盘"，这一层 Knocket 既没有，也没有接口让我们补。
2. 铁律和 DSGVO 两条硬约束过不了，而且都是厂商侧的结构，我们配不掉。
3. 作为补充也没有合适的位置：全站只有 Genie 一个对话入口是业主 2026-10-17 定下的（目标 1、A14）；"让 Linker 联系我"已经在 Genie 目标 6 里，而且走的是我们自己的通知链；业主 2026-10-07 要的是"询盘后公司收到通知、交易线下完成"，不需要一个另外的实时人工聊天收件箱。
4. 产品很新：2026 年 3 月上线，AI 是后加的，没有找到任何独立用户评价；条款允许腾讯随时改动或停止服务。

给业主的一句话版本：Knocket 是一个免费的在线客服气泡，AI 只能照着最多 30 份资料回答常见问题，看不到客户在哪一页、查不了我们的产品和价格、也不能替客户加方案或发询盘；聊天数据存在新加坡的腾讯服务器上，页面一打开就开始上报。它不能替代 Genie，也不建议装。

业主在 Knocket 上建的账户目前只有外观配置、AI 未开启（§4.3），不装 snippet 就不会产生任何访客数据。

## 8. 未知与未核实

- 业主控制台里有没有"数据区域"开关、能不能把 Web Widget 的数据放到法兰克福（S11 只有一句"Data region controls in the console"）。需要业主登录控制台看一眼，或问厂商。
- `api.trtc.io` 后端与 AI 调用实际在哪个机房处理；Knocket 免费账户是否以及怎样纳入腾讯云 DPSA；子处理者清单。
- 平台托管的向量模型是哪个、在哪里运行。
- LLM 运行时失败时的行为（报错、转人工还是静默）。没有在业主租户上开 AI 试，避免产生配置与费用。
- 会话导出能力。
- 业主注册时填的国家（决定签约主体与适用法，S7 §3(a)）。
- Product Hunt 页面两次抓取都只拿到外壳（"Product Hunt – The best new products in tech."），评论区内容未取到；chatgate.ai 转述的 Toolradar 测评没有逐条核实。

## 9. 来源

外部来源全部经 Apify；时间是 Apify 记录的页面加载时间（UTC）。页面原文在 `raw/apify/pages/`（每个文件首行带来源与时间），检索结果在 `raw/apify/search-*.json`，运行清单在 `raw/apify/runs.json`。

| 编号 | 来源 | 抓取时间（UTC） | raw |
|---|---|---|---|
| S1 | https://knocket.trtc.io/ | 2026-10-17T08:17:29Z | `pages/knocket-home.md` |
| S2 | https://knocket.trtc.io/tutorials/ai-agent/ | 08:19:35Z | `pages/knocket-tutorial-ai-agent.md` |
| S3 | https://knocket.trtc.io/tutorials/add-ai-assistant-to-website/ | 08:17:27Z | `pages/knocket-tutorial-complete-guide.md` |
| S4 | https://knocket.trtc.io/tutorials/web-widget/ | 08:19:35Z | `pages/knocket-tutorial-web-widget.md` |
| S5 | https://knocket.trtc.io/tutorials/ai_agent_handoff_phrases/ | 08:29:04Z | `pages/knocket-handoff-phrases.md` |
| S6 | https://knocket.trtc.io/legal/privacy/ | 08:19:04Z | `pages/knocket-legal-privacy.md` |
| S7 | https://knocket.trtc.io/legal/terms/ | 08:17:51Z | `pages/knocket-legal-terms.md` |
| S8 | https://knocket.trtc.io/why-free/ | 08:17:30Z | `pages/knocket-why-free.md` |
| S9 | https://knocket.trtc.io/blog/woocommerce-live-chat/ | 08:21:05Z | `pages/knocket-blog-woocommerce.md` |
| S10 | https://knocket.trtc.io/blog/javascript-live-chat/ | 08:19:51Z | `pages/knocket-blog-javascript-consent.md` |
| S11 | https://knocket.trtc.io/products/mobile-widget/ | 08:17:51Z | `pages/knocket-product-mobile-widget.md` |
| S12 | https://wordpress.org/plugins/knocket-live-chat-widget/ | 08:28:39Z | `pages/wporg-knocket-plugin.md` |
| S13 | https://chatgate.ai/de/post/knocket | 08:28:46Z | `pages/chatgate-knocket.md` |
| S14 | https://peerpush.com/p/knocket | 08:28:46Z | `pages/peerpush-knocket.md` |
| S15 | https://www.linkedin.com/posts/tencentrtc_ai-vibecoding-openclaw-activity-7442900598418661376-mzsI | 08:19:33Z | `pages/linkedin-tencentrtc-launch.md` |
| S16 | https://tencentrtc.medium.com/how-i-added-ai-auto-reply-to-a-free-website-chat-widget-in-openclaw-aa99789f2aae | 08:30:18Z | `pages/medium-tencentrtc-openclaw.md` |
| S17 | https://www.tencentcloud.com/document/product/301/17347（DPSA） | 08:28:26Z | `pages/tencent-dpsa.md` |
| S18 | https://www.tencentcloud.com/document/product/301/17345（腾讯云隐私政策） | 08:19:00Z | `pages/tencent-privacy-policy.md` |
| S19 | https://www.tencentcloud.com/document/product/1047/33513（Chat 概览，数据中心） | 08:28:26Z | `pages/tencent-chat-overview-data-centres.md` |
| S20 | https://eusovereigntyscore.eu/en/vendors/tencent-cloud | 08:19:49Z | `pages/eusovereigntyscore-tencent.md` |
| S21 | https://www.reddit.com/r/buildinpublic/comments/1rq0130/i_launched_knocket_a_free_oneline_widget_for_chat/ | 08:22:30Z | `pages/reddit-buildinpublic-launch.md` |
| S22 | https://trtc.io/company/compliance-privacy | 08:18:21Z | `pages/trtc-compliance.md` |
| S23 | https://knocket.trtc.io/products/web-widget/ | 08:17:27Z | `pages/knocket-product-web-widget.md` |
| S24 | https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en | 08:37:25Z | `pages/ec-adequacy-decisions.md` |
| S25 | Google 检索"LG München I 3 O 17493/20 Google Fonts Urteil"（gesetze-bayern.de、datenschutz.hessen.de 等结果摘要） | 08:35:27Z（运行开始） | `search-4.json` |
| S26 | Google 检索"§ 25 TDDDG localStorage Einwilligung"（dejure.org、datenschutz.bremen.de 等结果摘要） | 08:35:27Z（运行开始） | `search-4.json` |
| S27 | DNS-over-HTTPS（dns.google）：api.trtc.io、20032564w4s.my-imcloud.com、wsssgp/wssger.im.qcloud.com | 08:23:53–58Z | `dns.json` |

一手实测（不经 Apify，产品本身的行为）：

| 编号 | 内容 | 时间（UTC） | raw |
|---|---|---|---|
| P1 | `curl` 取回 `https://trtc.io/knocket-sdk/sdk.js?identifier=f145fd3b67d64f4704&v=1792224006909` 与 `sdk.css`，静态阅读；SDK 本体 3 MB 不入库，只留哈希、头与摘录 | 08:17:58 | `sdk/sdk-facts.json` |
| P2 | 本机一次性页面加载业主 snippet，1440 / 390，各一次；记录请求、localStorage、cookie、body 样式 | 08:20:24、08:21:16 | `probe/load-*.json`、`load-1440.png` |
| P3 | 同页打开面板（不发消息），记录面板文字与请求主机 | 08:22:26（390）、08:35:11（1440，含主机统计） | `probe/open-*.json`、`open-1440.png`、`open-390.png` |
| P4 | Knocket 官网自己的 AI，2 条消息 | 08:32:34、08:33:15 | `probe/ai.slim.json`、`ai-2.png` |

复现脚本在 `raw/scripts/`：`apify.py`（Apify REST，令牌只从环境读）、`runs.py`（列运行）、`show.py`（读数据集）、`load_probe.py`、`open_probe.py`、`ai_probe.py`（Playwright 实测，写盘前打码 `userSig`）、`slim.py`（组装 raw）。
