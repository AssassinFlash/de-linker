# Genie · 竞品调研（国际与 B2B 半）：AI 导购助手怎样感知页面、主动建议、替客户做事、记忆与转人工

- 日期：2026-10-17（研究票 #241，地图 #220；下游：#240 目标定义，#233–#236、#242–#244 实现票）
- 范围：国际与 B2B 助手——Amazon Alexa for Shopping（原 Rufus）与 Amazon Business Assistant、Walmart Sparky、Zalando Assistant、IKEA、Home Depot Magic Apron、Lowe's Mylow、Alibaba.com Accio / AI Mode、Grainger 与欧洲工业分销商（Würth、Conrad/voelkner、RS、Mouser、DigiKey）、Shopify Inbox agent、欧洲光伏批发商（Memodo、Krannich、BayWa r.e.、Wattkraft、Segen、Libra），以及一手 UX 研究（NN/g、Baymard、Google、W3C）与转人工 / 线索平台（Intercom Fin、Zendesk、HubSpot、Drift）。中国助手（淘宝、京东、美团）由另一份卷宗覆盖，本卷不涉及。
- 性质：只读研究。没有改插件、服务、生产站、WordPress 或 VPS；没有向任何第三方提交表单或下单；观测页面时唯一的点击是关闭 Cookie 同意横幅。
- 外部取证：全部经 Apify（附录 A 列出 run id、actor、起止时间）。每条外部事实附 URL 与抓取时间（UTC）；抓取集中在 2026-10-17 05:29–06:30 UTC。原文照录，不翻译。
- 原始数据：`raw-intl/`。`apify/*.json` 是各次运行的数据集（去掉了 html/text 重复字段；第三方 CDN 的签名 URL 一律替换为 `<signed-url-removed>`）；`pages/*.md` 是逐页正文，页首注释写明来源 URL、抓取时间与 run；`scripts/` 是可重跑的脚本（令牌只从环境变量读取）。提交前做过令牌扫描（JWT、Apify 令牌形态与环境中三个 Apify 令牌的字面值），结果为 0。
- 旧研究 `docs/research/2026-10-09/platform-ai-shopping-assistants.md` 只当线索：本卷复用的每一条都重新抓取核对过，对不上的地方在 §7 写明。

---

## 0 结论（先读这一节）

### 0.1 一句话

国际同行里做得好的助手，**都知道你在哪一页、在看哪个产品，并在打开时把这一点说出来**；**几乎都不自己弹出整窗**（Amazon、Zalando、Shopify、Rufus DE 都是用户点开），主动性体现在页面内的小提示与"打开时的页面专属建议"；**会替你做事，但凡是提交、付款类的最后一步都留给用户点一次**（Amazon "review and check out"、Accio "you only make the key decisions"、OpenAI "explicitly confirm each step"）；**转人工时把上下文一起交出去**（Shopify、Zendesk、Intercom），客户不必重说一遍。B2B 的助手（Amazon Business Assistant、Accio、Home Depot / Lowe's 的 Pro 工具）比 B2C 多两样东西：**账号与价格上下文**，以及**"把材料清单变成报价单"**。

### 0.2 Genie 能不能在对话里提交询盘？——**能，但只能是"Genie 起草，客户在卡片上点一次发送"**

依据：
1. **最近的 B2B 同类（Accio）就是在对话里替用户发询盘的**："the user specifies how many units of each item they want to purchase, and Accio drafts outreach to be sent to the selected suppliers automatically"（WWD，抓取 2026-10-17T05:31:23Z）；Accio Sourcing Expert 的官方模板："once I've chosen, send an inquiry email to the supplier"，并写明 "the whole process runs automatically — you only make the key decisions"（accio.com，05:39:23Z）。同一家把**付款**单列为必须明确批准的动作："Sensitive actions like payments require explicit user approval."（accio.com/wow/doc-help-about.html，05:39:18Z）；"High stakes actions involving finances or file access require explicit user approval"（PR Newswire 2026-03-23，05:31:07Z）。
2. de-linker 的询盘不是付款：它不产生付款义务，Proforma 之后全部线下（AGENTS.md §1）。它比"在对话里结账"风险低——而行业从对话内结账后撤，后撤的是**支付**这一步：OpenAI "we're allowing merchants to use their own checkout experiences while we focus our efforts on product discovery"（CNBC 2026-03-24 引 OpenAI，05:42:24Z）。
3. 但询盘是对外可见、有后果的动作：触发团队通知、触发"一个工作日内回复"的承诺（业主 2026-10-09 裁定）、消耗共享的发信额度（Hostinger `mail()` 100 封/24 小时，AGENTS.md §4）。这正是 NN/g 说的"decision gate"："points where an agentic AI requests confirmation from a human before taking significant actions with potential adverse consequences"（NN/g，05:46:12Z）。Amazon 的同类做法是"automatically add items to your cart, which you can then review before checking out"（aboutamazon 2025-11-18，05:30:15Z）；B2B 的 Home Depot Pro 清单工具同样"draft … they can edit before accepting"（2026-01-26，06:15:39Z）；OpenAI 的商务协议原则是 "Users stay in control — they explicitly confirm each step before any action is taken."（openai.com，05:42:24Z）。
4. 所以答案是"做，按 decision gate 做"：Genie 把产品与数量放进 Lösungsentwurf，生成**询盘确认卡**（逐行产品、数量、客户备注、对话摘要、联系人与公司——全部来自账号与本轮工具结果，不来自模型自由文本），卡上一个"发送询盘 / Anfrage senden"按钮；**只有按钮点击能发送**，模型文字永远不能触发发送；只对已登录且有权提交询盘的账号显示；缺地址、VAT 等询盘页必填信息时，按钮换成"在询盘页补全并发送"（直达预填好的询盘页）。发送走与询盘页同一条 Woo 结账管线（不另建第二套询盘实现，AGENTS.md §5"三件套原生优先"）。发送后在对话里给出询盘号、状态 "Inquiry received / Anfrage eingegangen"、"一个工作日内回复"的承诺与账户页链接。细则见 §5.2。

### 0.3 自动弹开：业主已定"滚到一定位置自动弹开并给出本页建议"——证据给出的边界

一手研究对"站点主动弹出的聊天"评价很差：Baymard "most users generally perceive live chat as **just another annoying, site-initiated distraction**"，并给出若必须主动时的三条缓解：限定页面、"often once is enough"、延时（baymard.com，05:36:51Z）；Baymard 还写明这类对话框"are generally more warranted to have as desktop-only features"。HubSpot 的产品设计与之吻合：手机端只提供"Pop open the welcome message as a prompt"或"Only show the chat launcher"，访客最小化后"HubSpot will respect that visitor behavior across pages and chatflows until the … cookie expires after 24 hours"（knowledge.hubspot.com，05:44:41Z）。所以落地为**一张不抢焦点的小"预览卡"**（不是整窗），规则：

| 规则 | 建议 | 依据 |
|---|---|---|
| 形态 | 启动钮上方的小卡：一句"我看到你在看 X"+ 2–3 个本页建议胶囊 + 关闭；**不展开整个对话面板**，不遮主内容与主按钮 | Intercom 建议"less disruptive snippet"、整屏 post 只用于"very important announcements"（05:44:50Z）；Google 要求"use banners that take up only a small fraction of the screen"（05:31:40Z）；Zalando / Rufus 的"打开时说出你在看什么"（§2.3、§2.1） |
| 触发 | 只在产品页、产品分类 / 商城页、解决方案页；**滚过本页主内容锚点**（产品页：技术参数区进入视口；分类页：第一行产品之后）**且**在页停留达到起步阈值、且没有输入框获得焦点、且没有其它对话框（Cookie 横幅）打开 | 业主 Q2 裁定（滚动位置）；Baymard"having a time delay before showing live chat"；HubSpot 的触发器就是"Percentage of the page scrolled / Time on page in seconds / On exit intent"（05:44:41Z）；Zendesk"Visitor is on the page … spends a set amount of time"（05:45:01Z） |
| 禁区 | 询盘页、Lösungsentwurf 的提交区、登录 / 注册 / 账户表单、错误页；用户正在输入时 | Baymard"making some pages off-limits for live chat (e.g., … in the checkout flow)"；WCAG 3.2.1 不得因焦点改变上下文（05:31:53Z） |
| 频率 | 每个浏览会话最多一次（全站）；对话进行中不再弹 | Baymard"often once is enough"；Zendesk 频率选项"One time only, once per customer visit, or every time"，且"Proactive messages aren't sent to customers in currently active messaging conversations"（05:45:01Z）；Drift"once, once per session, or on every page load"（Google 片段，见 §2.12） |
| 关闭记忆 | 用户点关闭后 30 天不再自动弹；用户自己打开过 Genie 的会话内不再弹 | HubSpot 关闭记 1 天（cookie "prevent the chat widget welcome message from appearing again for one day after it is dismissed"，05:44:49Z）；Intercom 默认"Seen — Send the Workflow to customers once, then not again, whether or not they interact with or dismiss it"（05:44:50Z）；30 天取两者之间、偏向 Intercom 的默认，是起步值，按 §5.3 的计数校准 |
| 手机（< 768 px） | **不自动展开任何卡片**；只在启动钮上显示一个小标记（数字或点），点开才出本页建议 | Baymard"desktop-only"；HubSpot 手机端只有 prompt / launcher 两种；Google 侵入式对话框指引；Baymard 实测手机上悬浮聊天元素挡住筛选、色块、自动补全 |
| 无障碍 | 预览卡出现时不移动焦点，用 `aria-live="polite"` 播报；Esc 关闭；尊重 `prefers-reduced-motion`；设置里可以关掉"自动建议" | WCAG 3.2.1（A 级）；WCAG 2.2.4"Let people delay or turn off updates"（05:31:53Z） |

数字（停留秒数、30 天）没有行业统一值，上表把来源写明为"起步值"，按 AGENTS.md"每个数字与阈值必须有来源"，由原型票与上线后计数（弹出次数、经预览卡打开次数、关闭次数，分页面类型）校准。

### 0.4 八个视角的结论（详见 §2–§3）

1. **页面感知与主动**：同行普遍把"知道你在看什么"做成**打开时的页面专属建议**与"this product"式问法（Zalando、Rufus、NN/g 2026 研究）；Conrad 集团的 KAI（voelkner.de）明说"weiß immer genau, auf welcher Seite sich der Nutzer gerade befindet, bietet proaktiv Hilfe an"，但实地观测首屏停留 50 秒它并没有自己展开（§2.10a），入口是搜索框旁的"Frag KAI"、右下角启动钮与页脚横幅。主动弹整窗的大站没有找到；Amazon 的主动性是搜索结果里的提示与建议问题（"Alexa may proactively surface tips, insights, and other content"）。
2. **理解输入**：问句与关键词同一入口（Amazon 搜索框识别问句）；拍照普遍（Amazon、Home Depot、Zalando、Walmart、Accio 以图找厂）；B2B 特有的是**上传清单 / 手写单 / 图纸转材料表**（Lowe's Material Lists、Home Depot Materials List Builder 与 Blueprint Takeoffs、Amazon 手写清单进购物车、Accio 解析采购清单）；语音有分歧（NN/g 建议提供，voelkner KAI 的测试用户不接受）。
3. **动作**：加购 / 建清单 / 比较 / 查单是常规；付款或下单类动作要么停在"用户复核后结账"，要么需要事先明确授权（Amazon Auto-buy 带 24 小时免费取消）；B2B 的 Accio 在用户选定后代发询盘。
4. **记忆与历史**：Amazon 跨设备、跨渠道记住对话，可查看与清除历史，DE/UK 的 Rufus 用 28 天内的对话做上下文；Zalando 只保留 20 分钟、同设备；Intercom 访客（cookie）→ 登录后合并为用户；Shopify 会话内偏好只用于本次对话。
5. **转人工与线索**：Intercom Fin 的默认升级条件（明确要人、强烈不满、三轮循环）与"不连续两次提议"规则；Shopify 在员工不在时给出店铺邮箱；IKEA 企业客户聊天有人工时段、时段外由聊天机器人接；Zalando 明说没有人工。B2B 买家仍要人工确认：Gartner 2026"69% of B2B buyers prefer to validate AI-generated insights with sales reps"。
6. **把上下文交出去**：Shopify "The AI's prior context carries over to your staff"，并在会话里显示购物车事件；Zendesk 交接时附"full transcript, concise summary, and a detected intent"；Lowe's 给 Pro 柜台员工一键生成客户项目摘要。
7. **价格与账号**：Amazon Business Assistant 只在登录后的 Business Settings 页出现，且坦白"Knowledge of any custom pricing is limited"；Walmart CEO 承诺"We won't use the information you share with us on Sparky … to raise your price"；Shopify 查订单前要求登录。价格跟着账号走、不跟着对话走，是国际同行的共同口径。
8. **回答形态与信任**：建议问题做成按钮、每次回答后都有（NN/g）；产品带图；可点赞点踩（Amazon、Shopify、Amazon Business）；明示"may not always get things right"；AI 身份告知自 2026-08-02 起是欧盟法定义务（AI Act 第 50 条）。

### 0.5 六条之外，建议再加的验收（全文见 §6）

页面感知可见（打开即说出当前产品）、预览卡规则逐条可测、每次回答后有可点的下一步、转人工三触发 + 不重复提议 + 承诺时限、团队收到对话摘要与页面与 Lösungsentwurf、对话内询盘只能由按钮发送、会话列表 + 登录合并 + 可清除、记忆使用要说明依据、价格与产品页一致、产品推荐带图且详情原地展开、长回答不自动滚到底、可把对话发到邮箱 / 下载、只有一个助手入口。

---

## 1 方法与证据边界

**Apify（必经）**，两个账号（`APIFY_TOKEN_PREV` 为主，`APIFY_TOKEN_ALT` 在并发内存满时分流）：

- 发现：`apify/google-search-scraper` 5 轮共 94 个查询（英、德）。
- 正文：`apify/website-content-crawler` 8 次运行，按 URL 列表只抓起始页（深度 0）；对 Amazon、Zalando、Zendesk、Intercom 等先用数据中心代理、失败或正文被截断时改用 RESIDENTIAL 代理与 Firefox，并改 `htmlTransformer: none` 以保留可读性算法丢掉的列表项（Intercom、Zendesk 的条件清单就是这样补回的）。
- 实地观测：`apify/playwright-scraper` 4 次运行。第一次在 15 个首页读出聊天 / 助手组件的脚本、iframe 与 DOM 特征；其余三次（§2.10a）在 1440×900 视口（及一次 390×844，被拒）下关掉 Cookie 横幅后停留约 50 秒，逐步记录助手组件是否自己出现、出现在哪、多大（脚本也尝试了滚动，但滚动没有生效，结果只代表首屏停留）。
- 排错：Walmart.com（"Robot or human?"）与 Lowes.com（"Access Denied"）的产品页在住宅代理下仍被拦，改用两家的 corporate / IR 一手稿；amazon.de 帮助页第一次只拿到验证码页，改用德国住宅代理与 Chrome 后取到；voelkner.de 对移动视口请求回 403 与超时（§2.10）。没有更改任何账户设置。

**本地只读核对**：`docs/specs/13-genie.md`；`services/genie/src/linker_genie/schema.py`（`PageContext`）；`plugins/linker-tools/includes/Genie/Conversations.php`；`plugins/linker-tools/src/genie/`（无任何滚动或定时自动打开逻辑，`Handoff.tsx` 只渲染一句摘要）；`plugins/linker-commerce/includes/Gating/CommerceState.php`；实现票 #233–#236、#242–#244 的"已知"段。

**边界**：
- 同行的界面会改版；本卷结论只代表抓取时刻。Amazon 的 Alexa for Shopping 只在美国，德国站仍是 Rufus（§2.1）。
- 第三方助手大多要登录或在 App 内，本卷没有登录任何同行账号，所以"登录后的行为"只能引用对方自己的说明。
- 二手报道（Retail Dive、Digital Commerce 360、SFGate、Distribution Strategy）只用于补充，并标明。

---

## 2 逐个助手（按八个视角）

视角编号：①页面感知与主动 ②理解输入 ③动作与确认 ④记忆与历史 ⑤转人工与线索 ⑥上下文交接 ⑦价格与账号 ⑧回答形态与信任。

### 2.1 Amazon：Alexa for Shopping（美国，原 Rufus）／ Rufus（德国、英国）

名称与状态：2026-05-13 起美国站改名 Alexa for Shopping，"Amazon brings together Rufus and Alexa+"（aboutamazon.com/news/retail/alexa-for-shopping-ai-assistant，2026-10-17T05:30:14Z）；CNBC 同日："The stand-alone Rufus chatbot will be discontinued"（05:30:33Z）。德国站仍叫 Rufus：amazon.de 帮助页标题 "About Rufus"，"Rufus is an AI-powered shopping experience that lets you ask all kinds of shopping questions in the Amazon Shopping app and on Amazon.de."（05:37:43Z）。2024-10-29 起在德国、奥地利以 Beta 提供桌面版："Der neue Shopping-Assistent ist als Beta-Version für alle Kunden und Kundinnen in Deutschland und Österreich verfügbar."（aboutamazon.de，05:44:31Z）。

① **页面感知与主动**
- 知道当前产品与购物车：官方示例问句 "Does this blender crush ice?"、"Compare this with espresso machine in my cart."（aboutamazon 2025-11-18，05:30:15Z）。NN/g 2026 实测："On a product page, _Rufus_ surfaced questions specific to that product — immediately signaling that it knew what the user was looking at."（nngroup.com/articles/ai-chatbots-design-guidelines，05:36:14Z）。
- 主动内容在页面里，不是弹整窗："As you navigate Amazon.com or the Amazon Shopping app, Alexa may proactively surface tips, insights, and other content to help you as you shop. … Alexa may also suggest refinements to your product search query … To start a chat with Alexa, you can tap on a suggested question or ask a question in the Alexa for Shopping chat window."（amazon.com AfS FAQ，05:34:59Z）。CNBC："if users browse for certain products, a chat window will appear with information and a few recommended items"——出现在搜索结果里（05:30:33Z）。
- 搜索框分流：问句会被带进对话，"If you want to stop chatting with Alexa and get standard product search results instead, you can always do that as well."（05:34:59Z）。
- 德国 / 英国桌面：用户点导航栏的 Rufus 按钮，"a chat window will appear on the bottom left corner of the page"；可关闭或"the minimize button to drop it down the lower left-hand corner"（amazon.de 帮助页，05:37:43Z）。

② **输入**：文字、麦克风（"tap on the mic icon in the Alexa for Shopping chat window"）、拍照或上传（"tap "+" in the Alexa for Shopping chat window to take or upload an image"）、手写购物清单拍照进购物车（05:34:59Z；05:30:15Z）。图片在聊天历史里可查看 30 天（05:34:59Z）。

③ **动作与确认**：加购、按对话建购物车、复购、价格提醒、Auto Buy、Buy for Me、查单。复购与建车的终点是用户复核："leveraging agentic AI capabilities to automatically add items to your cart, which you can then review before checking out"（05:30:15Z）；定时任务"will either notify you or add relevant items directly to your cart … so all you have to do is review and check out"（05:30:14Z）。唯一不经复核就下单的是用户事先设定的 Auto Buy，并有兜底："send a notification with free 24-hour cancellation if you change your mind after the order is placed. Auto-buy requests stay active for six months or until you cancel"（05:30:15Z）。

④ **记忆与历史**：美国 "Alexa maintains context for the profile you're logged into, and remembers conversations across Amazon's website and app, as well as Alexa on Echo devices … so you can easily pick up where you left off."；"you can view your recent chats"（05:34:59Z）。偏好可看可改："View and update details like family members, pets … by simply asking Alexa for Shopping what it knows about you."（05:30:14Z）。德国 / 英国 Rufus："We use your chats with Rufus to provide context for future responses for up to 28 days or until you clear your chat history from view."，并给出"Clear chat history"四步（amazon.de/Rufus 页，05:37:43Z）。使用要登录："Simply sign in to your Amazon account to start shopping with Alexa."（05:34:59Z）。

⑤ **转人工**："if needed, connect you with a live customer service representative"（05:30:15Z）。

⑥ **上下文交接**：没有找到对客服交接内容的公开说明。

⑦ **价格与账号**：价格历史"the lowest Featured Offer price"（05:34:59Z）。Amazon Business 账号："Amazon Business customers can shop with Alexa on Amazon.com by signing in through their Amazon Business account. Alexa for Shopping is currently not available on the Amazon Business mobile app."（05:34:59Z）；德国站："Rufus is currently only available to Amazon Business customers through the Amazon Shopping app."（05:37:43Z）。没有找到"商业价格在助手里如何显示"的一手说明（§7）。

⑧ **形态与信任**：建议问题可点（"tap one of the suggested questions"，aboutamazon 2024，05:30:31Z）；从搜索结果勾选多件并排比较；产品页"Compare with Similar"、"Why you might like this"（05:35:06Z）；点赞点踩并声明"Alexa for Shopping is an AI-powered shopping experience and may not always get things right."（05:35:00Z）；德国页还写"please don't rely on it for professional, medical, legal, or financial advice"与"We may also choose not to respond to certain questions."（05:37:43Z）。架构：模型生成界面标记、服务端填数据（"a process called hydration"，amazon.science，05:30:31Z）；评测"LLM-as-a-judge"（AWS 博客，05:30:41Z）——这两条已在 Genie 规格里（13-genie.md §B、验收），本卷复核原文仍在。

NN/g 的反面观察：Rufus 产品下的"More details"会生成一条新消息、把产品列表推出视野，"a better design would have expanded the details in place"（05:36:14Z）。

### 2.2 Amazon Business Assistant（美国，B2B）

- ①：只在登录后的 Business Settings 页面出现，右下角图标："Log into your Amazon Business account and select Business Settings, then look for the orange Amazon Business Assistant icon in the lower right corner."（business.amazon.com，05:45:18Z）。**有条件地主动出现**："When an opportunity is identified to make purchasing easier or more efficient, the tool appears on the account page and provides support based on account settings."（Amazon 新闻稿 2025-11-12，05:41:58Z）。
- 分工：产品问题交给 Alexa for Shopping，账号与采购功能交给它："Alexa for Shopping can help you research and compare products, while Amazon Business Assistant is focused on helping you set up and get the most from your procurement features."（05:45:18Z）。
- ③④⑦：账号上下文问答 "Do I have any approvals needing my attention?"、"What's the status of order #1234?"（business.amazon.com 博客 2026-05-14，05:45:13Z）；按过去 12 个月均价算节省建议，并坦白"Knowledge of any custom pricing is limited and may not be reflected in savings guidance."（05:45:18Z）。
- ⑤⑧："For support beyond the AI assistant, Amazon's Customer Service team is available to help."；"Amazon Business Assistant is AI-powered and may not always get things right. … rating the answers with a thumbs up or thumbs down, and sharing feedback with your Account Executive."（05:45:18Z）。

对 de-linker 的含义：B2B 助手的"主动"是**账号上下文触发**，而且一家公司把"产品选型"与"账户 / 流程"两类问题分清楚了——Genie 两类都做，但应该在账户页给账户类建议、在产品页给产品类建议（§5.1）。

### 2.3 Zalando Assistant

- ①：**打开时**按所在分区给开场建议："The Zalando Assistant also takes into account where you are on the Zalando platform and provides tailored conversation starters accordingly. For instance, if a customer is browsing the denim section for women and opens the Zalando Assistant, it will acknowledge this with prompts like, "I see you are interested in Women's jeans" and suggest relevant queries such as "Show me flared jeans"."（zalando.de FAQ，05:36:01Z；同文见 corporate.zalando.com 2025-03-27，05:44:14Z）。
- ②：文字与图片（"When you submit a question or an image"，05:36:01Z）。③：推荐商品、"Where is my order"按钮查单（05:36:01Z）。
- ④：**只保留 20 分钟、同设备**："You can get back to your previous chat by clicking on the Zalando Assistant icon on the same device. However, it will only be available for 20 minutes after you wrote your last chat message."（05:36:01Z）。个性化：只对登录客户，"connected to customer accounts … During a pilot phase, we observed a +40% increase in high-value interactions"（05:44:14Z）。
- ⑤：**没有人工**："The Zalando Assistant is not supported by a human advisor."（05:36:01Z）。
- ⑧："AI-generated answers can sometimes be subjective, inaccurate, or influenced by biases."；有恶意意图分类器（05:36:01Z）。

### 2.4 Walmart Sparky

- 能力（Walmart 一手）："Sparky helps shoppers find and compare products, build lists, get personalized recommendations and plan for occasions by synthesizing reviews and product data … emerging voice and camera capabilities enable Sparky to support customers seamlessly from discovery through checkout. With our Customer Support Assistant, agents are routing inquiries, resolving common issues"（corporate.walmart.com/about/technology，05:38:04Z）；派对规划生成清单（2025-10-31 新闻稿，05:37:51Z）。
- ⑦ **价格不跟对话走**（2026-09-25 CEO 公开信）："We'll hold our shopping tools to the same promise. We won't use the information you share with us on Sparky or otherwise to raise your price or hide lower-priced options that meet your needs."；"You decide whether to share additional details for more personalized help."（05:37:50Z）。2026-10-05 公开信再申明"Information customers share with us is not used to raise their individual prices."（05:37:50Z）。
- 外部渠道：Sparky 进入 ChatGPT 时由 Walmart 自己的环境完成账号、会员与支付（Retail Dive 2026-03-25，05:46:25Z，二手）。
- 未取到：walmart.com 的 Sparky 页面被反爬拦截（§1），所以①④⑤⑧没有一手细节。

### 2.5 IKEA

- 面向顾客的生成式助手只在 ChatGPT 的 GPT Store（2024，"currently available for GPT Plus users in the US market only"，ingka.com，抓取见附录 B）。官网上的是客服聊天：德国站聊天入口列出常见诉求按钮（"Wo ist meine Bestellung?"、"Ich habe Fragen zu einem Produkt"、"Ich möchte einen Termin buchen"），并说明**企业客户有单独的人工聊天时段**："Unser Chat Team für Unternehmen ist in der Zeit von Montag bis Freitag zwischen 8:00 und 17:50 Uhr gerne persönlich für dich da … Außerhalb der Chat-Öffnungszeiten hilft dir unser Chatbot bei deinen Anliegen weiter."（ikea.com/de，05:44:12Z）。
- ⑤ 转人工写进隐私政策："We use an AI assistant to answer common questions when you contact us. If the AI assistant cannot help or if you request to speak with a co-worker, your call will be transferred to a co-worker."（ikea.com/se，05:45:48Z）。规模：Billie "from 2021 to 2023 it resolved approximately 47% of customer enquiries it received"，同时 8,500 名同事转做远程设计顾问（ingka.com 2023，附录 B）。

### 2.6 Home Depot Magic Apron（含 Pro）

- ①：在"millions of product pages"上（2025-03-06，05:38:18Z）。但 NN/g 2026 实测它**没有让用户知道它看得见当前产品**："One participant assumed the bot couldn't see the product he was viewing and manually copied and pasted product names into the chat. "Does this know that I'm on this page? I don't think it does.""；它其实记得同一会话里看过的水槽，"but nothing in the interface had suggested it could do this."；而且**结账时消失**："_Magic Apron_ disappeared once the user began the checkout process"，同站另有一个"Live Chat"造成混淆（05:36:14Z）。
- ②："text questions, use voice-to-text, upload pictures, and interact in their preferred language"（IR 2026-08-27，05:38:23Z）。
- ③ **Pro（B2B）**：Materials List Builder"Create actionable job lists in minutes using natural language, voice-to-text, or spreadsheet uploads"；Blueprint Takeoffs"deliver complete material lists and project quotes in days instead of weeks"（corporate.homedepot.com 2026-03-30，05:38:30Z）；"describe a project via voice or text, or even upload a list of products the pro already has. The agent then interprets the project intent to quickly generate a comprehensive, grouped list of materials, even suggesting essential missed items"（与 Google Cloud 联合稿 2026-01-11，05:38:29Z）。**先给草稿、客户改完再接受，接受后才按客户自己的价格出产品**："Regardless of input, Pros will receive a draft material list organized by each project phase, they can edit before accepting. Once accepted, product recommendations will populate beneath each section, complete with the Pro's preferred pricing and inventory availability."；输入方式包括"Paste an existing list from spreadsheets, texts, emails, notes apps or other documents"；只对 Pro Xtra 会员（2026-01-26，06:15:39Z）。
- ⑦：在店模式按所选门店给库存与货架位置（05:38:23Z）。
- ⑧：每次回答后可点的追问按钮、带图产品轮播（NN/g 正面例，05:36:14Z）。
- 人与 AI 的定位："Our associates remain at the center of the shopping experience"（05:38:23Z）。

### 2.7 Lowe's Mylow（含 Pro）

- 上线时只对会员："Mylow is available for MyLowe's Rewards loyalty members or by visiting lowes.com/Mylow"；可按预算、邮编细化本地推荐（新闻稿 2025-03-05，05:38:50Z）。
- 效果："Mylow users convert at three times the rate of online shoppers who do not use Mylow, according to Lowe's Q2 2026 earnings call."（openai.com/index/lowes，05:39:02Z，引 Lowe's 财报会）。
- **Pro 的需求不同**（Lowe's 高管访谈，Retail Dive 2026-03-12，05:40:21Z，二手）："For them, it is very much [about] product availability in large quantities … they also often form relationships with their local pro desk Lowe's associate"；员工端 Pro Companion 把准备客户来电资料的时间从几小时缩到一分钟——这是"把对话 / 项目摘要交给销售"的实例。
- ② **清单转报价**："Material Lists, an AI-powered solution that converts handwritten notes, photos, spreadsheets and other supported file types into quote-ready orders in minutes … Using SKU matching and automated list digitization"（2026-05-21，05:45:11Z）。

### 2.8 Alibaba.com：Accio 与 AI Mode（最近的 B2B 同类）

- 2024-11 起：文字或图片提问，"At the end of the search, the tool lists a number of procurement options for the business to discuss directly with each supplier."；支持英、德、法、葡、西（CNBC，05:31:22Z）。
- ③ **代发询盘**（Accio Agent，WWD，05:31:23Z）：给任务 → 分子任务列合格供应商 → 追加约束收窄（如只要 Oeko-Tex）→ "the user specifies how many units of each item they want to purchase, and Accio drafts outreach to be sent to the selected suppliers automatically. Once inquiries have been sent, users can interface directly with suppliers through Accio's platform."
- Accio Sourcing Expert（accio.com，05:39:23Z）："From refining requirements to a supplier shortlist, the whole process runs automatically — you only make the key decisions."；模板"Based on the attached purchase list, parse my requirements and send batch inquiries directly to matching suppliers"、"Check my current inquiry progress"。
- 确认边界："Sensitive actions like payments require explicit user approval."（05:39:18Z）；"High stakes actions involving finances or file access require explicit user approval"（05:31:07Z）。
- Alibaba.com AI Mode（2025-12）：可读"technical specifications, engineering blueprints, product sketches, and certification documents"（Digital Commerce 360 品牌稿 2025-11-26，二手）。

对 de-linker 的映射：工程约束 → 合格产品 → 追加约束 → 数量 → 起草询盘 → 用户决定是否发送；B2B 买家习惯"上传清单 / 文件"。

### 2.9 Shopify Inbox agent（单店、小目录的最近参照）

- ①：知道店铺目录、政策与页面内容，"uses your store's product catalog, store policies, and page content"（help.shopify.com，05:31:01Z）；**用户点按钮才打开**："When a customer clicks the chat button on your online store, a chat window opens … When your Inbox agent is active, it provides conversation starters"（05:40:11Z）。
- ③："Answer questions about product details, availability, and pricing"、"Add recommended products directly to the customer's cart"、查单"The customer is prompted to sign in before the Inbox agent shares order information."（05:31:01Z）；买单在店铺自己的结账："When they're ready to purchase, checkout happens on your store directly"（Shop app 文档，05:40:35Z）。
- ④⑦："Customers can start and continue chatting with the Inbox agent without signing in."；"The Inbox agent can use preferences that customers share during a chat to improve responses in that conversation."；"It might mention the detail that shaped a recommendation, such as a saved size or a product that the customer bought from your store."（05:31:01Z）。
- ⑤⑥ **交接**："If staff handoff is available, then the conversation moves to your staff. The AI's prior context carries over to your staff. If staff aren't available, then the Inbox agent shares your store's sender email address so the customer can email you."（05:31:01Z）；"The Inbox agent can't send email on your behalf. The customer must initiate email contact."；购物车事件与小计显示在会话里；客户离开后"a message indicates that your reply is sent to the customer's email address, if the customer provided one or signed in."（05:37:27Z）。线索：可要求"Require sign-in to chat with staff"，或旧账号体系的"pre-chat form"收姓名邮箱（05:45:57Z）。
- ⑧ 披露不可删改："Customers receive a notice that the chat is powered by Shopify and that they're chatting with AI. This notice is displayed automatically and can't be removed or customized."（05:31:01Z）。

### 2.10 欧洲工业分销商与光伏批发商

**Conrad 集团 / voelkner.de：KAI**（新闻稿 2026-06，conrad.de，05:41:18Z）——本卷找到的唯一一个德国 B2B/B2P 商城的生成式导购：
- "KAI weiß immer genau, auf welcher Seite sich der Nutzer gerade befindet, bietet proaktiv Hilfe an und verweist auf passendes Zubehör, wie beispielsweise Hygienemittel für einen Luftbefeuchter."
- "Ein speziell entwickeltes und intuitives Interface bietet anklickbare Vorschläge, minimiert die Tipparbeit"。
- 语音被用户拒绝："Auch eine Sprachein- und -ausgabe waren ursprünglich geplant, wurden vom Testpublikum aber nicht angenommen."
- 面向 B2C 与 B2B："Als B2P-Unternehmen … wendet sich voelkner.de sowohl an B2C- als auch an B2B-Kunden."
- Conrad CEO 对 B2B 的边界（computer-automation.de 访谈 2026-07，05:40:22Z）："KI bereitet vor, bei kritischen Fällen hat jedoch heute noch der Mensch das letzte Wort."；"B2B lebt von Beziehungen und persönliche Betreuung ist ein entscheidender Baustein verlässlicher Partnerschaft."
- 实地观测：见 §2.10a。

**Würth**：搜到的 PICO 是给外勤销售的语音助手（news.wuerth.com 2024），不是客户侧导购；客户侧没有找到一手证据。**RS、Mouser、DigiKey**：两轮检索只找到产品与技术文章，没有找到面向客户的对话助手的一手发布（DigiKey 有供 AI 客户端调用的 Product Search API，见搜索结果，不是站内助手）。**Grainger**：CEO 在 2026 Q1 财报会把 AI 分为"internal productivity and customer-facing digital capabilities"，后者是"AI-powered search and merchandising"（Distribution Strategy 转述，05:43:04Z，二手）；Databricks 案例里是 RAG 搜索与"enhanced the ability of call center agents"（05:43:15Z）。三家都没有找到站内对话导购——工业分销的主流是"AI 搜索 + 给客服 / 销售的助手"。

**欧洲光伏批发商**（Memodo、Krannich、BayWa r.e.、Wattkraft、Segen UK/EU、Libra）：两轮德英检索都没有找到任何一家的 AI 导购发布；首页组件检测（run `FKuKcGSqqiocOoheg`，05:39–05:41Z，未接受 Cookie）在前五家没有检测到聊天组件，Libra 有一个人工聊天 iframe（标题 "Ask us anything. We will reply as soon as possible."）。接受 Cookie 后的复测见 §2.10a。结论：**直接竞品里还没有 AI 导购**，Genie 做好就是差异点。

#### 2.10a 实地观测（桌面 1440×900，接受 Cookie 后滚动 8 步并停留）

方法：`raw-intl/scripts/mk_observe.py`（run `ATaPSVjATuEW9qBlM`，德国住宅代理，06:15–06:23Z；原始数据 `raw-intl/apify/observe-eu-desktop.json`，用 `scripts/observe_show.py` 可读）。每页先等 6 秒，点掉 Cookie 横幅，然后尝试滚动 8 步、每步 3.5 秒，最后停留 15 秒，共约 50 秒；每一步记录可见的聊天 / 助手元素（滚动未生效，见下方局限）。

| 站点 | Cookie | 50 秒内是否有助手 / 聊天自己展开 | 可见的入口 |
|---|---|---|---|
| Memodo（memodo.de → /photovoltaik/） | 已接受 | 否 | 无聊天 / 助手元素 |
| Krannich（krannich-solar.com/de-de/） | 已接受（Cookiebot） | 否 | 无（只有 Cookiebot 的 4×4 空 iframe） |
| Wattkraft（wattkraft.com） | 无横幅 | 否 | 无 |
| Segen EU（segensolar.eu） | 已接受 | 否 | 无 |
| Libra Energy（libra.energy/en） | 无横幅 | 否 | 左下角 60×60 的 Trengo 人工聊天按钮（iframe 标题 "Open chat"），全程未自己展开 |
| Würth（wuerth.de） | 无横幅 | 否 | 右下角 53×53 的无障碍工具按钮（eye-able），不是聊天 |
| Conrad（conrad.de） | 已接受（Usercentrics） | 否 | 无 |
| BayWa r.e.、Mouser、DigiKey | — | 未取到（页面超时 / 被拦） | — |

voelkner.de（KAI）：

移动视口（390×844，run `SkeeRx9DrKVHOo2pF`）两次被拒（403、页面超时）；桌面改用 Firefox 重试成功（run `dzXoHxcufaFQGN6NR`，06:26–06:30Z，`raw-intl/apify/observe-voelkner-desktop.json`）：
- 首页：搜索框旁一个"Frag KAI"按钮（135×40，aria-label "Zur KI-gestützten Suche wechseln"）——**AI 入口放在搜索框里**；右下角固定的 65×65 启动钮（aria-label "Jetzt KI-Assistenten starten"）；页脚一条静态横幅"Hi, ich bin KAI Dein persönlicher KI-Assistent … Produkte finden, Geschenke suchen oder individuelle Beratung - ich bin immer für Dich da."与按钮"KAI etwas fragen"。
- 产品页（Luftbefeuchter）：同一条页脚横幅与"KAI etwas fragen"按钮。
- 约 50 秒停留内，**KAI 没有自己展开对话窗**。新闻稿说的"bietet proaktiv Hilfe an"在这次观测里没有出现，可能发生在对话内部（打开后按页面给建议、推荐配件）或需要更长停留 / 滚动才触发，本卷不能判定（§7）。

观测局限：脚本的 8 次滚轮操作在这几个站点上都没有改变滚动位置（记录的滚动深度在各步之间不变），所以以上结果等于"首屏停留约 50 秒"，不能代表"滚到页面深处后"的行为。

结论：七个欧洲光伏 / 工业站点（含 voelkner 的 KAI）**在桌面首屏停留约 50 秒内没有一家自己弹出助手或聊天**；有入口的（Libra、voelkner）都是一个小启动钮，voelkner 另把 AI 入口放进搜索框与页脚横幅。业主要的"滚动后自动弹出建议"在直接竞品中没有先例——它会是差异点，也正因为没有先例，§0.3 的克制规则更重要。

### 2.11 Intercom Fin（转人工与线索的参照）

- 默认升级条件（05:43:37Z，`htmlTransformer: none` 重抓）："When a customer clearly asks to speak to a human."、"When Fin detects strong frustration or anger — though Fin may first attempt to resolve the issue before escalating."、"When the customer is stuck in a repetitive loop."；提议升级的情形包括"**Loop:** The customer repeats themselves across three turns."、"**First-turn escalation:** The customer tries to escalate immediately after Fin introduces itself."；"Fin will never offer escalation twice in a row."；"If no human routing target is configured ("bot only" mode), Fin will not offer escalation."；对话里以文字提议，"not through a button"。
- 交接前收集："Ask for more information before handover"、"Collect more information when a customer asks to speak to the team"；"you could set expectations for when your team will reply or collect additional information that will help route the conversation"（05:43:37Z）。
- 线索：访客开始对话即成为 lead，"they're automatically prompted to enter their email address in case they leave before they get an answer"；"A lead becomes a user when they sign up to your product, or log into an existing account. All of the information and conversations you've had with them remain in their user profile."；"We only automatically merge leads into users when they share the same device cookie."（05:43:49Z）。Fin for Sales：在 playbook 里定义"Data to collect"，资格判定后建 CRM 线索、约 Calendly 会议（05:43:49Z）。
- 没有人工可转时（"bot only"）："Fin does not offer escalation. The conversation ends with a "get more help" instead of routing to a team."；并提示"Do not write contact details (email addresses, phone numbers) directly into Escalation Guidance text. Deliver this information through Workflow messaging steps instead"（06:16:01Z）——联系方式由流程组件给出，不交给模型自由生成；Genie 现在用服务端填入团队邮箱句，方向一致。
- 记忆（Fin Memory，beta）：最近消息与摘要保留 45 天、客户明确说过的事实保留 180 天，只对已识别用户；"Customers cannot directly view or edit their Fin Memory."，并提醒"you may need to update your own privacy notice"（06:15:59Z）。与 Amazon"可以问它知道你什么、可以改"相反——对 de-linker 应取 Amazon 的透明做法（§5.3-3）。
- 主动消息形态："send your chat as a snippet (which shows the first few words of your message) … Then your website visitors can open your message at a time that suits them"；整屏 post"Only use them for very important announcements, when you definitely want to interrupt customers."（05:44:50Z）。频率："**Seen (default)** — Send the Workflow to customers once, then not again, whether or not they interact with or dismiss it."；若关闭或打开 Messenger，"it will be hidden for the remainder of their session"（05:44:50Z）。

### 2.12 Zendesk、HubSpot、Drift（主动触发与交接的参照）

- Zendesk 主动消息：条件"Visitor loads the page / Visitor is on the page … spends a set amount of time on the page"；频率"One time only, once per customer visit, or every time"；"Proactive messages aren't sent to customers in currently active messaging conversations."（05:45:01Z）。AI 代理本身不跟踪行为："The AI agent doesn't track individual customer activity on your website in real time … This setup looks like real‑time engagement, but it relies on the rules you define."（05:45:10Z）。交接："Escalated calls can be sent to human agents in Agent Workspace with a full transcript, concise summary, and a detected intent, so agents always start informed."（语音 AI 代理文档，05:44:00Z）；"Out-of-office triggers can set a customer's expectations"；"Continuous conversations let you automatically send email notifications to end users who have left a conversation"（05:44:00Z）。
- HubSpot（05:44:41Z）：桌面三种显示——"Pop open the welcome message as a prompt"、"Only show the chat launcher"、"Show the welcome message then pop open the chat when a trigger is met"；触发器"On exit intent"、"Time on page in seconds"、"Percentage of the page scrolled"；**手机端只有前两种**；最小化在 24 小时内跨页面生效。
- Drift（Salesloft 帮助中心，Google 片段，`serp-en-b2b-ux.json`，05:30Z）："Set the Frequency to have your Playbook deliver to your audience once, once per session, or on every page load!"；目标条件含"Seconds on site"。正文页未抓取，只作旁证。

### 2.13 一手 UX 研究与法规

- **NN/g《10 Guidelines for Designing Your Site's AI Chatbots》（2026-04-24，05:36:14Z）**——本卷最直接的一手研究：1 合并为一个聊天入口；2 跨页面常驻（"A chatbot that disappears between pages is one that users will stop trying to use."）；3 打开信息说明能做什么，并"tailor the opening message to the page the user is on"；"If your chatbot knows what the user is looking at or can remember what they've browsed, inform them about those capabilities."；4 建议问题做成按钮、回答后继续给，但"followup questions can feel annoying when irrelevant or repetitive"；5 推荐带图；6 详情原地展开；7 不要自动滚到长回答末尾（"keep the user's scroll position at the top of the new message"）；8 可调窗口大小；9 可保存 / 分享对话；10 考虑语音输入。
- **NN/g《Customer-Service Chat: 20 Guidelines》（05:31:38Z）**：浮动按钮放右下角且不能是唯一入口；产品页要有入口；"Keep Users Updated on How Fast They Will Get a Response"；"ensure that if the user does attempt to resume an interrupted chat session, the context (and the progress) is saved"；"Don't Make Users Type Their Question Multiple Times"；可上传文件；可保存记录；"Be Upfront About Using a Bot"。
- **Baymard（05:36:51Z；05:36:49Z）**：见 §0.3；指南 #940 "Avoid Automatic Live Chat Boxes"："Site-initiated live chat dialogs are disruptive and annoying, and "sticky" chat elements often block critical page content on mobile devices."
- **Google Search Central（05:31:40Z）**："Intrusive dialogs and interstitials make it hard for Google and other search engines to understand your content, which may lead to poor search performance."；"use banners that take up only a small fraction of the screen"。
- **W3C WCAG 2.2**：3.2.1 On Focus（A 级）"Do not change a user's context when items get focus"，上下文变化包括 focus；2.2.4 Interruptions（AAA）"Let people delay or turn off updates"（05:31:53Z）。
- **EU AI Act 第 50 条**（AI Act Service Desk，05:44:16Z）："Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system"；"at the latest at the time of the first interaction or exposure"；"From 2 August 2026 onwards, if the AI agent is intended to interact with natural persons or generate content, transparency rules will apply (Article 50 AI Act)"（FAQ，05:46:00Z）。Genie 的首条披露句已满足"首次交互时告知"；预览卡也算首次接触，应带 AI 标识（§5.2）。
- **Gartner（B2B 买家）**："67% of B2B buyers state that they prefer a rep‑free experience … 45% reporting they used AI during a recent purchase"（2026-03-09，05:46:16Z）；"Sixty-nine percent of B2B buyers prefer to validate AI-generated insights with sales reps"；"Fifty-one percent of buyers say they are more likely to encounter misleading information from GenAI"（2026-05-20，05:45:23Z）。含义：自助 + 随时一键找人，两样都要。

---

## 3 横向模式表

●＝一手证据；○＝二手或部分；—＝明确没有；空＝未见证据。Az＝Amazon AfS / Rufus；AB＝Amazon Business Assistant；Wm＝Walmart Sparky；Za＝Zalando；IK＝IKEA；HD＝Home Depot；Lo＝Lowe's；Ac＝Accio；Sh＝Shopify Inbox agent；KAI＝voelkner；IC＝Intercom Fin；ZD＝Zendesk。

| 能力 | Az | AB | Wm | Za | IK | HD | Lo | Ac | Sh | KAI | IC | ZD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 知道当前产品 / 页面 | ● |  |  | ●（分区） |  | ●（不告知） |  |  | ●（页面内容） | ● |  | — |
| 打开时给本页建议 | ● |  |  | ● | ●（诉求按钮） | ○ |  |  | ● | ● |  |  |
| 自己弹出整窗 | —（搜索结果内提示） | ○（有机会时出现） |  | — |  |  |  |  | — | —（50 秒首屏未弹，§2.10a） | 可配置（默认 snippet） | 可配置 |
| 频率 / 关闭记忆可配 |  |  |  |  |  |  |  |  |  |  | ● | ● |
| 拍照 / 上传图片 | ● |  | ○ | ● |  | ● | ● | ● |  |  |  |  |
| 上传清单 / 文件转产品 | ●（手写单） |  |  |  |  | ●（Pro） | ●（Pro） | ● |  |  |  |  |
| 语音 | ● |  | ○ |  |  | ● | ● |  |  | —（测试被拒） |  |  |
| 加购 / 建清单 | ● |  | ● |  |  | ● | ● |  | ● | ● |  |  |
| 代发询盘 / RFQ |  |  |  |  |  |  | ○（报价单） | ● |  |  |  |  |
| 提交 / 付款前用户确认 | ● |  | ○ |  |  |  |  | ● | ●（店铺结账） |  |  |  |
| 查单 / 询盘状态（需登录） | ● | ● |  | ● |  |  |  | ● | ● |  |  |  |
| 跨会话记忆 | ●（28 天 / 跨设备） | ○ |  | —（20 分钟） |  |  |  |  | ○（会话内） |  | ●（cookie→用户） | ● |
| 可查看 / 清除历史与记忆 | ● |  | ○（自愿分享） |  |  |  |  |  |  |  |  |  |
| 转人工 | ● | ● | ○ | — | ● |  | ○（Pro 柜台） |  | ● |  | ● | ● |
| 交接带上下文 / 摘要 |  |  |  |  |  |  | ○ |  | ● |  | ● | ● |
| 人工不在时给邮箱 / 时段 |  |  |  |  | ●（时段） |  |  |  | ●（邮箱） |  | ● | ● |
| 价格跟账号 | ○ | ●（坦白有限） | ●（不按人定价） | ○ |  | ●（按门店） |  |  |  |  |  |  |
| 点赞点踩 | ● | ● |  |  | ●（帮助页） |  |  |  | ●（店主评分） |  |  |  |
| "可能出错"声明 | ● | ● |  | ● |  |  |  |  | ● |  |  |  |
| 不可删改的 AI 披露 |  |  |  |  |  |  |  |  | ● |  |  |  |

共同骨架（按证据强弱）：页面专属开场建议（Amazon、Zalando、Shopify、KAI、NN/g）；用户点开、不自己弹整窗（Amazon、Zalando、Shopify、Rufus DE；Baymard 反对站点主动弹出）；提交前复核（Amazon、Shopify、Accio、OpenAI）；交接带上下文（Shopify、Zendesk、Intercom）；明示可能出错 + 反馈（Amazon、Amazon Business、Zalando、Shopify）。

---

## 4 与现在 Genie 的差距

现状依据：`docs/specs/13-genie.md`、#240 第一轮、实现票 #233–#236 与 #242–#244 的"已知"段（均为 2026-10-17 取证）。

| 视角 | 同行做法（证据） | Genie 现状 | 差距 | 对应票 |
|---|---|---|---|---|
| ① 页面感知 | 打开即说出当前产品 / 分区（Zalando、Rufus、NN/g #3） | `PageContext` 只有 type + product_id + draft_ids；首页、博客、FAQ、解决方案页都是 other；dock 开场提示按页面类型写死 2–3 条 | 不认识大多数页面；开场不说出产品名；没有"这一页说的……"的能力 | #234 |
| ① 主动 | 页面内小提示、snippet；手机不弹（Baymard、HubSpot、Intercom） | 只有用户点击才打开；首次点击才加载 JS | 业主要的滚动预览卡不存在；需要 §0.3 的规则 | 新票（建议） |
| ② 裸词 / 品牌 | 搜索框识别问句、关键词直达（Amazon） | 模型自己决定查不查库；"saj"两次 tools=[] | 产品词被当称呼 | #233 |
| ② 图片 / 文件 | 拍照、清单 / 图纸转产品表（Amazon、HD、Lowe's、Accio） | 附件只发文件名 | 铭牌一步到产品、上传 Stückliste 都没有 | #236 |
| ② 语音 | 多数提供；KAI 被拒 | 无 | 证据有分歧，放"以后" | — |
| ③ 动作 | 加购、比较、查单；提交前复核；B2B 代发询盘（Accio） | 加入 Lösungsentwurf、加入方案、打开配置器、查询盘状态；不能发询盘 | 缺"询盘确认卡 + 一次点击发送" | 新票（建议，接 #244） |
| ④ 记忆 | 会话列表、跨设备、可清除；cookie→登录合并（Amazon、Intercom） | 访客只有一条（cookie）会话；新建会话收起面板；访客 90 天清理 | 没有会话列表、不能切换、登录只认领当前 cookie 那一条；没有"清除" | #235 |
| ⑤ 转人工 | 明确要人 / 不满 / 循环三种触发；不重复提议；人工不在给邮箱与时段（Intercom、Shopify） | 范围外问题只出一句团队邮箱（`Handoff.tsx` 只渲染摘要句） | 没有"让 Linker 联系我"按钮、没有收联系方式、没有承诺时限 | #243 |
| ⑥ 交接 | 交接附全文、摘要、意图（Zendesk）；上下文转给员工（Shopify） | 无 | 团队看不到对话 | #243、#244 |
| ⑦ 价格 | 价格跟账号（Amazon Business、Walmart 承诺、Shopify 查单要登录） | 所有产品能力匿名调用；已批准伙伴在 Genie 里看不到价格 | 与产品页不一致 | #242 |
| ⑧ 形态 | 回答后可点追问、带图、原地展开、不自动滚底、点赞点踩、"可能出错"（NN/g、Amazon） | 卡片、对比表、一个追问、动作块、点赞点踩（`VoteButtons.tsx`）、披露句一次、服务端填数 | 缺"每次回答后 2–3 个可点下一步"的常态、缺保存 / 发邮件、缺"可能出错"提示；图片、自动滚动、原地展开需在原型里核对 | 新验收（§6） |
| ⑧ 一个入口 | NN/g #1：只留一个助手 | 站内只有 Genie | 保持；不要再加第二个聊天组件（人工也走 Genie 转交） | — |

---

## 5 对 de-linker 的建议（按优先级）

### 5.1 必须（MUST）——每条都对应业主已定的方向或已有实现票

1. **打开即说出当前页面**（#234）：产品页开场写出型号（"Sie sehen gerade … / You're looking at …"）并给 3 个本产品问题；分类页给本分类的选型问题；Lösungsentwurf 给"检查我的草稿 / 缺什么配件"；账户页给询盘状态类问题；首页、解决方案、博客、FAQ 按页面内容给。依据：Zalando、Rufus、NN/g #3（"Users won't assume a chatbot knows what they're looking at unless the chatbot makes it explicit to them."）。
2. **滚动预览卡**按 §0.3 的规则做（新票）：桌面、每会话一次、关闭记 30 天、手机只给标记、不抢焦点、禁区页面。依据：业主 Q2 + Baymard / HubSpot / Intercom / Zendesk / WCAG。
3. **产品词先查库**（#233）：裸品牌 / 型号 / 系列一律先走确定性匹配出卡片。依据：Amazon 搜索框把问句与关键词分流（"the search experience recognizes when you're asking a question"）。
4. **会话不丢、可列可切、登录合并**（#235）：访客按 cookie 保存多条会话并列出；登录后把该设备上的全部访客会话并入账户（Intercom 只自动合并同一设备 cookie，正是这一口径）；登录用户跨设备可见；提供"清除对话"。依据：Amazon（跨设备、可清除）、Intercom、NN/g chat #10。
5. **让 Linker 联系我**（#243）：随时可点；Genie 在三种情形下主动提议——客户明确要人、表达不满、同一问题重复三轮（Intercom 默认），且不连续两次提议；登录客户不再问联系方式，访客只问邮箱（与公司名，可选）；告诉客户"一个工作日内回复"（业主 2026-10-09 承诺，NN/g"Keep Users Updated on How Fast They Will Get a Response"）；团队收到对话全文、摘要、当前页面、Lösungsentwurf 内容（Zendesk"full transcript, concise summary, and a detected intent"、Shopify"prior context carries over"）。内部通知收件人按 2026-10-17 裁定发 sales@sunriverinverter.com。
6. **询盘附对话摘要**（#244）：同 5 的摘要格式；客户在发送前能看到摘要并可删去（与 §5.2 的确认卡同一处），隐私政策写明。
7. **价格跟账号**（#242）：已批准伙伴在 Genie 里看到与产品页相同的净价；其他人看到"登录后显示价格"；Genie 的文字永远不报未经工具返回的价格（服务端填数规则已在）。价格只随账号审批状态变化，不随对话内容变化（Walmart 公开承诺的口径）。
8. **拍照与附件**（#236）：铭牌一步到产品卡（已定）；另加"上传 Stückliste / 采购清单 → 逐行匹配产品 → 一键加入 Lösungsentwurf"，未匹配行明确列出。依据：Lowe's Material Lists、Home Depot Materials List Builder、Accio "parse my requirements"。

### 5.2 询盘在对话里提交：细则（MUST，新票，接 #244）

1. 入口：Lösungsentwurf 非空、客户已登录且有权提交询盘时，Genie 在回答后给"准备询盘"动作；客户也可以直接说"发询盘"。
2. Genie 生成**确认卡**（UI 组件，不是模型文字）：逐行产品（型号、数量）、价格行为与产品页一致、客户备注（可编辑）、对话摘要（可删）、联系人与公司（来自账号）、承诺"一个工作日内回复"。
3. **只有卡上的"发送询盘 / Anfrage senden"按钮能发送**；模型输出里出现"已发送"之类的话不触发任何动作（与现行"动作只在允许列表、参数只来自工具结果"的结构保证一致）。
4. 询盘页的必填项（账单地址、VAT 等，见注册卷宗把地址挪到 Proforma 页的建议）不全时，按钮改为"在询盘页补全"，打开预填好的询盘页；不在对话里收地址。
5. 发送走询盘页同一条 Woo 管线；成功后对话里显示询盘号、状态、承诺时限、账户页链接；失败显式报错并保留草稿。
6. 访客：不显示发送按钮，显示"登录后发送询盘"与"让 Linker 联系我"两条路。
7. 依据：§0.2 第 1–4 条。

### 5.3 应该（SHOULD）

1. **每次回答后 2–3 个可点的下一步**（按钮），不重复客户已拒绝的追问（NN/g #4）；现有"一个决定性追问"保留为其中之一。
2. **产品推荐带图、详情原地展开**、长回答流式输出时停在新消息开头（NN/g #5–#7）。
3. **记忆可见**：Genie 用到账号里的项目事实（相数、kWp、已买设备）时说明依据，并能回答"你知道我什么"（Amazon、Shopify"might mention the detail that shaped a recommendation"）。
4. **把对话发到邮箱 / 下载 PDF**（NN/g chat #14、AI #9）；与"让 Linker 联系我"的摘要同一格式。
5. **"可能出错"一句 + 每条回答的点赞点踩**（已有点赞点踩；补"may not always get things right"式一句，放在披露句旁，EN/DE 走文案评审）。
6. **账户页的有条件主动**：账户页只在有可做的事时出预览卡（例如"你的询盘已出 Proforma"），照 Amazon Business Assistant"When an opportunity is identified … the tool appears on the account page"。
7. **预览卡计数**：记录各页面类型的弹出、经卡打开、关闭次数（只计数、不记个人），两周后与业主复核阈值。
8. **Genie 在询盘页与 Lösungsentwurf 常驻**（不自动弹），避免 Home Depot"结账时助手消失"的问题（NN/g #1、#2）。

### 5.4 以后（LATER）

1. 语音输入（NN/g #10 建议；voelkner KAI 测试用户不接受——先看 #236 上线后的拍照使用率再定）。
2. "复购上次询盘"（Amazon 复购、Lowe's / Home Depot Pro 的清单复用；安装商重复下同类单）。
3. 询盘状态变化的主动提醒（Amazon Business Assistant 的审批提醒类）。
4. 外部代理可读的产品数据（OpenAI ACP、Shopify Catalog）——与 Genie 本身无关，列作 GEO 方向。

---

## 6 验收：六条之外再加的条目

业主已同意的六条：任何品牌 / 型号词都出产品；页面专属建议 + 能回答本页问题；会话永不丢；铭牌照片一步到产品；每个回答都有下一步；不编造。建议再加：

| # | 验收条目 | 判据（可测） | 依据 |
|---|---|---|---|
| A1 | 打开即显示页面感知 | 产品页打开 Genie，开场句含当前型号；分类、草稿、账户、首页、解决方案、博客、FAQ 各至少 2 条本页建议；EN/DE | Zalando、Rufus、NN/g #3 |
| A2 | "这个产品"不需要重打型号 | 产品页问"Passt dazu ein Speicher?"，回答引用当前产品；评测集每类页面 2 问 | Rufus"Does this …"；NN/g（HD 用户复制粘贴型号的反例） |
| A3 | 预览卡规则 | 不在页面加载时出现；只在白名单页面；滚过锚点 + 停留后出现；每会话最多一次；关闭后 30 天不出现；会话进行中不出现；390 宽只出标记；不移动焦点、不遮挡主按钮（1440 / 390 截图） | §0.3 |
| A4 | 每次回答后有可点的下一步 | 每条助手消息后 2–3 个按钮；客户拒绝过的追问不再出现 | NN/g #4 |
| A5 | 转人工触发与承诺 | 说"Ich möchte mit jemandem sprechen"立即给出"让 Linker 联系我"；重复同一问题三轮时提议一次、不连续两次；回复里写明一个工作日内回复；登录客户不被问联系方式 | Intercom 默认；NN/g chat #7；业主承诺 |
| A6 | 团队收到完整上下文 | 内部通知（Outbox 队列断言）含对话全文链接、摘要、页面 URL、Lösungsentwurf 行 | Zendesk、Shopify |
| A7 | 不重复输入 | 对话里给过的数量、项目条件、备注出现在询盘页 / 联系请求的预填里 | NN/g chat #11 |
| A8 | 对话内询盘只能由按钮发送 | 模型输出注入"已发送"文本不产生询盘；确认卡展示的行与最终询盘逐行一致；访客看不到发送按钮；缺必填项时转询盘页 | §5.2；NN/g decision gate |
| A9 | 会话列表与合并 | 访客连开三个会话都可切回；登录后三个都在账户下；另一台设备登录可见；"清除"后不再作为上下文 | Amazon、Intercom、#235 |
| A10 | 价格一致 | 同一产品：已批准账号在卡片里的价格 = 产品页价格；访客 / 待审看不到价格 | #242；Amazon Business、Walmart |
| A11 | 推荐带图、原地展开、不自动滚底 | 产品卡有图；"更多参数"在卡内展开；长回答流式时视口停在新消息开头 | NN/g #5–#7 |
| A12 | 可保存对话 | 可把对话 / 摘要发到客户邮箱（测试邮件纪律下只发 tester）或下载 | NN/g chat #14、AI #9 |
| A13 | AI 告知与"可能出错" | 首次接触（含预览卡）即可见 AI 标识；披露句出现一次；"可能出错"一句在场 | AI Act 第 50 条；Amazon、Shopify |
| A14 | 只有一个助手 | 全站只有 Genie 一个对话入口；询盘页与 Lösungsentwurf 上 Genie 仍可打开 | NN/g #1、#2 |

---

## 7 未知与未核实

- **谁能在 de-linker 提交询盘**（待审 / 限制账号能否提交）：本卷只读了价格门 `CommerceState`（"a pending or restricted account reads the site like a guest"），没有核对询盘提交的门；§5.2 写成"与询盘页同一规则"，实现票须先核对。
- **Amazon Business 账号在 Alexa for Shopping / Rufus 里是否显示商业价格**：没有一手说明。
- **Walmart Sparky、Lowe's Mylow 站内界面**：walmart.com、lowes.com 产品页被反爬拦截（住宅代理亦然），两家的页面感知、记忆、转人工细节只有 corporate / 二手材料。
- **voelkner KAI 的"proaktiv"具体形态**：以 §2.10a 的观测为准；移动视口两次被拒（403 / 超时）。
- **Drift 频率设置**：只有搜索片段，正文页未抓。
- **Würth、RS、Mouser、DigiKey、Grainger 的客户侧对话助手**：两轮检索未见一手发布，不等于不存在。
- **旧研究的出入**：旧卷称 Zalando 升级稿"未抓到日期"——一手页面写明 2025-03-27；旧卷说 Shopify 人工交接"带上 AI 已有的上下文"——仍成立（05:31:01Z）；旧卷说 OpenAI"2026 年初结束 Instant Checkout"——一手原话是"allowing merchants to use their own checkout experiences while we focus our efforts on product discovery"（CNBC 2026-03-24 引 OpenAI），属"转为商家自有结账"，不是功能彻底删除。
- **数字阈值**（停留秒数、关闭记忆天数）没有行业统一值，§0.3 给的是有来源的起步值，需原型与上线计数校准。

---

## 附录 A：Apify 运行

<!-- RUNS -->

| run id | actor | 用途 | 状态 | 开始 / 结束（UTC） | 条目 | raw 文件 |
|---|---|---|---|---|---|---|
| `wMiryS2Msj89wxsxS` | apify/google-search-scraper | serp-en-retail | SUCCEEDED | 2026-10-17T05:29:02.888Z / 2026-10-17T05:30:18.922Z | 20 | `apify/serp-en-retail.json` |
| `nHX4krqE6orRQgckQ` | apify/google-search-scraper | serp-en-b2b-ux | SUCCEEDED | 2026-10-17T05:29:05.735Z / 2026-10-17T05:30:35.635Z | 20 | `apify/serp-en-b2b-ux.json` |
| `knr4azgOa2H5Yj4Ac` | apify/google-search-scraper | serp-de | SUCCEEDED | 2026-10-17T05:29:08.877Z / 2026-10-17T05:29:59.393Z | 10 | `apify/serp-de.json` |
| `TrRwuJPIOXuAAY33r` | apify/website-content-crawler | wcc-known-1 | SUCCEEDED | 2026-10-17T05:30:00.934Z / 2026-10-17T05:32:01.332Z | 17 | `apify/wcc-known-1.json` |
| `6ep3kFtfDlq2qhpn0` | apify/website-content-crawler | wcc-protected-residential | SUCCEEDED | 2026-10-17T05:34:45.551Z / 2026-10-17T05:36:31.423Z | 12 | `apify/wcc-protected-residential.json` |
| `RprqhMkO9aiKCS8l1` | apify/website-content-crawler | wcc-b1 | SUCCEEDED | 2026-10-17T05:34:28.577Z / 2026-10-17T05:41:25.338Z | 58 | `apify/wcc-b1.json` |
| `nhYEE2N8zACk3aduc` | apify/website-content-crawler | wcc-b3 | SUCCEEDED | 2026-10-17T05:40:46.070Z / 2026-10-17T05:46:53.290Z | 20 | `apify/wcc-b3.json` |
| `441FEIMGdGRPUOGLw` | apify/website-content-crawler | wcc-b4-lists | SUCCEEDED | 2026-10-17T05:43:28.512Z / 2026-10-17T05:44:46.971Z | 14 | `apify/wcc-b4-lists.json` |
| `E1sNAhO4fHbn0XWme` | apify/google-search-scraper | serp-round2 | SUCCEEDED | 2026-10-17T05:35:14.724Z / 2026-10-17T05:37:45.182Z | 24 | `apify/serp-round2.json` |
| `YpnX9oE6RPNjc2bk2` | apify/website-content-crawler | wcc-amazon-de-uk | SUCCEEDED | 2026-10-17T05:37:35.034Z / 2026-10-17T05:38:00.175Z | 3 | `apify/wcc-amazon-de-uk.json` |
| `FKuKcGSqqiocOoheg` | apify/playwright-scraper | widgets-1 | SUCCEEDED | 2026-10-17T05:38:49.718Z / 2026-10-17T05:43:48.674Z | 9 | `apify/widgets-1.json` |
| `6cWvgsX21KLnfovkN` | apify/google-search-scraper | serp-round3 | SUCCEEDED | 2026-10-17T05:40:26.168Z / 2026-10-17T05:42:20.642Z | 20 | `apify/serp-round3.json` |
| `OMFaxlpG6yfbQwyQN` | apify/website-content-crawler | wcc-b5 | SUCCEEDED | 2026-10-17T05:44:32.940Z / 2026-10-17T05:46:26.946Z | 18 | `apify/wcc-b5.json` |
| `d19YtZUInid3VHh3l` | apify/website-content-crawler | wcc-b6 | SUCCEEDED | 2026-10-17T06:15:29.541Z / 2026-10-17T06:20:43.859Z | 8 | `apify/wcc-b6.json` |
| `ATaPSVjATuEW9qBlM` | apify/playwright-scraper | observe-eu-desktop | SUCCEEDED | 2026-10-17T06:15:00.970Z / 2026-10-17T06:23:03.473Z | 7 | `apify/observe-eu-desktop.json` |
| `SkeeRx9DrKVHOo2pF` | apify/playwright-scraper | observe-voelkner-mobile | SUCCEEDED | 2026-10-17T06:15:08.488Z / 2026-10-17T06:18:13.481Z | 0 | `apify/observe-voelkner-mobile.json` |
| `dzXoHxcufaFQGN6NR` | apify/playwright-scraper | observe-voelkner-desktop | SUCCEEDED | 2026-10-17T06:26:19.137Z / 2026-10-17T06:29:56.065Z | 2 | `apify/observe-voelkner-desktop.json` |

## 附录 B：逐页来源索引（URL、抓取时间、run、raw 文件）

<!-- INDEX -->

| 来源 URL | 抓取时间（UTC） | Apify run | raw 文件 |
|---|---|---|---|
| https://advertising.amazon.com/library/news/agentic-shopping-advertising | 2026-10-17T05:36:13.440Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/advertising-amazon-com-library-news-agentic-shopping-advertising.md` |
| https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50 | 2026-10-17T05:44:16.975Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/ai-act-service-desk-ec-europa-eu-en-ai-act-article-50.md` |
| https://ai-act-service-desk.ec.europa.eu/en/ai-act/faq/how-are-ai-agents-addressed-within-ai-act-0 | 2026-10-17T05:46:00.019Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/ai-act-service-desk-ec-europa-eu-en-ai-act-faq-how-are-ai-agents-addressed-within-ai-act-0.md` |
| https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act | 2026-10-17T05:46:03.974Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/ai-act-service-desk-ec-europa-eu-en-ai-act-timeline-timeline-implementation-eu-ai-act.md` |
| https://aws.amazon.com/blogs/machine-learning/how-rufus-scales-conversational-shopping-experiences-to-millions-of-amazon-customers-with-amazon-bedrock/ | 2026-10-17T05:30:41.943Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/aws-amazon-com-blogs-machine-learning-how-rufus-scales-conversational-shopping-experiences-to-millio.md` |
| https://baymard.com/blog/ecommerce-cro | 2026-10-17T05:37:00.920Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/baymard-com-blog-ecommerce-cro.md` |
| https://baymard.com/blog/ecommerce-ux-best-practices | 2026-10-17T05:36:49.434Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/baymard-com-blog-ecommerce-ux-best-practices.md` |
| https://baymard.com/research-articles/live-chat-usability-issues | 2026-10-17T05:36:51.149Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/baymard-com-research-articles-live-chat-usability-issues.md` |
| https://business.amazon.com/en/blog/ai-powered-assistant-launch | 2026-10-17T06:15:43.842Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/business-amazon-com-en-blog-ai-powered-assistant-launch.md` |
| https://business.amazon.com/en/blog/new-assistant-conversational-skills | 2026-10-17T05:45:13.696Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/business-amazon-com-en-blog-new-assistant-conversational-skills.md` |
| https://business.amazon.com/en/solutions/streamlined-purchasing/ab-assistant | 2026-10-17T05:45:18.063Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/business-amazon-com-en-solutions-streamlined-purchasing-ab-assistant.md` |
| https://corporate.homedepot.com/news/company/ai-home-depot-look-future-home-improvement | 2026-10-17T05:38:30.843Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-homedepot-com-news-company-ai-home-depot-look-future-home-improvement.md` |
| https://corporate.homedepot.com/news/company/home-depot-launches-ai-powered-blueprint-takeoffs | 2026-10-17T06:15:53.549Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/corporate-homedepot-com-news-company-home-depot-launches-ai-powered-blueprint-takeoffs.md` |
| https://corporate.homedepot.com/news/company/home-depot-launches-ai-powered-material-lists-help-pros-save-time-building-complete | 2026-10-17T06:15:39.910Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/corporate-homedepot-com-news-company-home-depot-launches-ai-powered-material-lists-help-pros-save-ti.md` |
| https://corporate.homedepot.com/news/company/unveiling-magic-apron-home-depots-smartest-tool-yet | 2026-10-17T05:38:18.451Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-homedepot-com-news-company-unveiling-magic-apron-home-depots-smartest-tool-yet.md` |
| https://corporate.homedepot.com/news/partnerships/home-depot-and-google-cloud-launch-agentic-ai-tools-help-customers-and-associates | 2026-10-17T05:38:29.130Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-homedepot-com-news-partnerships-home-depot-and-google-cloud-launch-agentic-ai-tools-help-c.md` |
| https://corporate.lowes.com/newsroom/press-releases/lowes-boosts-pro-efficiency-ai-driven-material-lists-new-tool-delivers-product-quotes-minutes-05-21-26 | 2026-10-17T05:45:11.898Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/corporate-lowes-com-newsroom-press-releases-lowes-boosts-pro-efficiency-ai-driven-material-lists-new.md` |
| https://corporate.lowes.com/newsroom/press-releases/lowes-launches-first-ai-powered-home-improvement-virtual-advisor-03-05-25 | 2026-10-17T05:38:50.038Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-lowes-com-newsroom-press-releases-lowes-launches-first-ai-powered-home-improvement-virtual.md` |
| https://corporate.lowes.com/newsroom/stories/inside-lowes/meet-mylow-lowes-unveils-first-ever-ai-powered-virtual-home-improvement-assistant | 2026-10-17T05:44:32.325Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/corporate-lowes-com-newsroom-stories-inside-lowes-meet-mylow-lowes-unveils-first-ever-ai-powered-vir.md` |
| https://corporate.walmart.com/about/everyday-affordability/letter-from-our-ceo | 2026-10-17T05:37:50.026Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-walmart-com-about-everyday-affordability-letter-from-our-ceo.md` |
| https://corporate.walmart.com/about/technology | 2026-10-17T05:38:04.741Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-walmart-com-about-technology.md` |
| https://corporate.walmart.com/news/2025/06/06/walmart-the-future-of-shopping-is-agentic-meet-sparky | 2026-10-17T05:44:15.250Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/corporate-walmart-com-news-2025-06-06-walmart-the-future-of-shopping-is-agentic-meet-sparky.md` |
| https://corporate.walmart.com/news/2025/10/31/walmart-announces-new-holiday-shopping-experiences | 2026-10-17T05:37:51.635Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-walmart-com-news-2025-10-31-walmart-announces-new-holiday-shopping-experiences.md` |
| https://corporate.walmart.com/news/2026/10/correcting-the-record | 2026-10-17T05:37:50.033Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/corporate-walmart-com-news-2026-10-correcting-the-record.md` |
| https://corporate.zalando.com/en/company/winning-battle-attention | 2026-10-17T05:43:54.047Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/corporate-zalando-com-en-company-winning-battle-attention.md` |
| https://corporate.zalando.com/en/fashion/tracking-future-why-zalando-uniquely-placed-lead-next-era-retail | 2026-10-17T05:43:53.960Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/corporate-zalando-com-en-fashion-tracking-future-why-zalando-uniquely-placed-lead-next-era-retail.md` |
| https://corporate.zalando.com/en/technology/more-personal-and-smarter-zalando-assistant-enhanced-capabilities-inspire-customers | 2026-10-17T05:44:14.806Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/corporate-zalando-com-en-technology-more-personal-and-smarter-zalando-assistant-enhanced-capabilitie.md` |
| https://corporate.zalando.com/en/technology/zalando-brings-its-ai-powered-assistant-all-markets-and-adds-four-new-cities-its-trend | 2026-10-17T05:44:14.807Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/corporate-zalando-com-en-technology-zalando-brings-its-ai-powered-assistant-all-markets-and-adds-fou.md` |
| https://developers.google.com/search/blog/2016/08/helping-users-easily-access-content-on | 2026-10-17T05:34:42.778Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/developers-google-com-search-blog-2016-08-helping-users-easily-access-content-on.md` |
| https://developers.google.com/search/docs/appearance/avoid-intrusive-interstitials | 2026-10-17T05:31:40.721Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/developers-google-com-search-docs-appearance-avoid-intrusive-interstitials.md` |
| https://distributionstrategy.com/2026/05/grainger-embeds-ai-across-warehouse-operations-customer-service-and-ecommerce/ | 2026-10-17T05:43:04.361Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/distributionstrategy-com-2026-05-grainger-embeds-ai-across-warehouse-operations-customer-service-and.md` |
| https://distributionstrategy.com/2026/05/lowes-tightens-its-grip-on-the-small-pro-with-ai-tools-trades-investment/ | 2026-10-17T05:43:28.963Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/distributionstrategy-com-2026-05-lowes-tightens-its-grip-on-the-small-pro-with-ai-tools-trades-inves.md` |
| https://help.shopify.com/en/manual/inbox | 2026-10-17T05:40:34.731Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/help-shopify-com-en-manual-inbox.md` |
| https://help.shopify.com/en/manual/inbox/agent-persona | 2026-10-17T05:45:58.178Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/help-shopify-com-en-manual-inbox-agent-persona.md` |
| https://help.shopify.com/en/manual/inbox/assigning-your-ai-staff-member | 2026-10-17T05:31:01.420Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/help-shopify-com-en-manual-inbox-assigning-your-ai-staff-member.md` |
| https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance | 2026-10-17T05:40:47.434Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/help-shopify-com-en-manual-inbox-chat-settings-and-appearance.md` |
| https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/availability-and-first-reply | 2026-10-17T05:40:11.940Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/help-shopify-com-en-manual-inbox-chat-settings-and-appearance-availability-and-first-reply.md` |
| https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/instant-answers | 2026-10-17T05:40:11.832Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/help-shopify-com-en-manual-inbox-chat-settings-and-appearance-instant-answers.md` |
| https://help.shopify.com/en/manual/inbox/chat-settings-and-appearance/settings | 2026-10-17T05:45:57.092Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/help-shopify-com-en-manual-inbox-chat-settings-and-appearance-settings.md` |
| https://help.shopify.com/en/manual/inbox/conversations | 2026-10-17T05:37:27.066Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/help-shopify-com-en-manual-inbox-conversations.md` |
| https://help.shopify.com/en/manual/online-sales-channels/shop/customer-experience | 2026-10-17T05:40:35.449Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/help-shopify-com-en-manual-online-sales-channels-shop-customer-experience.md` |
| https://ir.homedepot.com/news-releases/2026/08-27-2026-130112388 | 2026-10-17T05:38:23.137Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/ir-homedepot-com-news-releases-2026-08-27-2026-130112388.md` |
| https://knowledge.hubspot.com/chatflows/create-a-live-chat | 2026-10-17T05:44:41.169Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/knowledge-hubspot-com-chatflows-create-a-live-chat.md` |
| https://knowledge.hubspot.com/chatflows/create-and-customize-a-mobile-chatflow | 2026-10-17T05:44:40.317Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/knowledge-hubspot-com-chatflows-create-and-customize-a-mobile-chatflow.md` |
| https://knowledge.hubspot.com/privacy-and-consent/what-cookies-does-hubspot-set-in-a-visitor-s-browser | 2026-10-17T05:44:49.283Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/knowledge-hubspot-com-privacy-and-consent-what-cookies-does-hubspot-set-in-a-visitor-s-browser.md` |
| https://openai.com/index/buy-it-in-chatgpt/ | 2026-10-17T05:42:24.265Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/openai-com-index-buy-it-in-chatgpt.md` |
| https://openai.com/index/lowes/ | 2026-10-17T05:39:02.933Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/openai-com-index-lowes.md` |
| https://press.aboutamazon.com/2025/11/amazon-business-unveils-next-generation-ai-solutions-to-help-organizations-and-small-businesses-save-time-and-money | 2026-10-17T05:41:58.663Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/press-aboutamazon-com-2025-11-amazon-business-unveils-next-generation-ai-solutions-to-help-organizat.md` |
| https://seller.alibaba.com/businessblogs/alibabacom-unveils-ai-mode----while-fueling-57-surge-in-european-orders-and-a-50-increase-in-worldwide-supplier-growth-px002dhxt | 2026-10-17T05:42:05.553Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/seller-alibaba-com-businessblogs-alibabacom-unveils-ai-mode-while-fueling-57-surge-in-european-order.md` |
| https://seller.alibaba.com/businessblogs/meet-accio-work---your-agentic-business-team-px002dj6w | 2026-10-17T05:39:50.138Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/seller-alibaba-com-businessblogs-meet-accio-work-your-agentic-business-team-px002dj6w.md` |
| https://sellercentral.amazon.com/help/hub/reference/external/GYYH9SLHSTHKT3CZ | 2026-10-17T05:35:28.888Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/sellercentral-amazon-com-help-hub-reference-external-GYYH9SLHSTHKT3CZ.md` |
| https://support.zendesk.com/hc/en-us/articles/10169333291290-About-voice-AI-agents | 2026-10-17T05:44:00.321Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/support-zendesk-com-hc-en-us-articles-10169333291290-About-voice-AI-agents.md` |
| https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback | 2026-10-17T05:44:00.117Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/support-zendesk-com-hc-en-us-articles-4408824482586-Managing-conversation-handoff-and-handback.md` |
| https://support.zendesk.com/hc/en-us/articles/4408829019162-Routing-messaging-tickets-and-notifying-agents | 2026-10-17T05:44:03.359Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/support-zendesk-com-hc-en-us-articles-4408829019162-Routing-messaging-tickets-and-notifying-agents.md` |
| https://support.zendesk.com/hc/en-us/articles/5381304334234-About-proactive-messages | 2026-10-17T05:45:01.590Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/support-zendesk-com-hc-en-us-articles-5381304334234-About-proactive-messages.md` |
| https://support.zendesk.com/hc/en-us/articles/5511218058650-Proactive-messaging-conditions-and-events-reference | 2026-10-17T05:45:01.459Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/support-zendesk-com-hc-en-us-articles-5511218058650-Proactive-messaging-conditions-and-events-refere.md` |
| https://support.zendesk.com/hc/en-us/articles/9801049560218-Does-my-AI-agent-track-activity-on-my-website | 2026-10-17T05:45:10.177Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/support-zendesk-com-hc-en-us-articles-9801049560218-Does-my-AI-agent-track-activity-on-my-website.md` |
| https://wwd.com/sourcing-journal/industry-news/alibaba-artificial-intelligence-agentic-sourcing-international-commerce-1238855697/ | 2026-10-17T05:31:23.707Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/wwd-com-sourcing-journal-industry-news-alibaba-artificial-intelligence-agentic-sourcing-internationa.md` |
| https://www.aboutamazon.com/news/retail/alexa-for-shopping-ai-assistant | 2026-10-17T05:30:14.834Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-aboutamazon-com-news-retail-alexa-for-shopping-ai-assistant.md` |
| https://www.aboutamazon.com/news/retail/alexa-for-shopping-learn-and-be-curious-podcast | 2026-10-17T05:35:44.045Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-aboutamazon-com-news-retail-alexa-for-shopping-learn-and-be-curious-podcast.md` |
| https://www.aboutamazon.com/news/retail/amazon-about-you-personalization-preferences | 2026-10-17T05:35:35.933Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-aboutamazon-com-news-retail-amazon-about-you-personalization-preferences.md` |
| https://www.aboutamazon.com/news/retail/amazon-agentic-ai-gen-ai-shopping | 2026-10-17T05:35:40.729Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-aboutamazon-com-news-retail-amazon-agentic-ai-gen-ai-shopping.md` |
| https://www.aboutamazon.com/news/retail/amazon-rufus-ai-assistant-personalized-shopping-features | 2026-10-17T05:30:15.309Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-aboutamazon-com-news-retail-amazon-rufus-ai-assistant-personalized-shopping-features.md` |
| https://www.aboutamazon.com/news/retail/how-to-use-amazon-rufus | 2026-10-17T05:30:31.116Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-aboutamazon-com-news-retail-how-to-use-amazon-rufus.md` |
| https://www.aboutamazon.com/news/retail/how-to-use-amazon-shopping-ai-assistant | 2026-10-17T05:35:06.079Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-aboutamazon-com-news-retail-how-to-use-amazon-shopping-ai-assistant.md` |
| https://www.aboutamazon.de/news/amazon-prime-und-shopping/rufus-ki-shopping-assistent | 2026-10-17T05:44:31.232Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/www-aboutamazon-de-news-amazon-prime-und-shopping-rufus-ki-shopping-assistent.md` |
| https://www.aboutamazon.eu/news/retail/amazon-announces-the-launch-of-rufus-a-new-generative-ai-powered-conversational-shopping-assistant-in-beta-across-europe | 2026-10-17T05:40:26.927Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-aboutamazon-eu-news-retail-amazon-announces-the-launch-of-rufus-a-new-generative-ai-powered-conv.md` |
| https://www.accio.com/wow/agent-rfq-assistant.html | 2026-10-17T05:39:22.568Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-accio-com-wow-agent-rfq-assistant-html.md` |
| https://www.accio.com/wow/agent-sourcing-expert.html | 2026-10-17T05:39:23.509Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-accio-com-wow-agent-sourcing-expert-html.md` |
| https://www.accio.com/wow/doc-help-about.html | 2026-10-17T05:39:18.660Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-accio-com-wow-doc-help-about-html.md` |
| https://www.accio.com/wow/usecase-prompt-sourcing-inquiry.html | 2026-10-17T05:39:24.274Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-accio-com-wow-usecase-prompt-sourcing-inquiry-html.md` |
| https://www.alizila.com/alibaba-international-unveils-enterprise-ai-agent-platform-for-global-smes/ | 2026-10-17T05:31:15.440Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-alizila-com-alibaba-international-unveils-enterprise-ai-agent-platform-for-global-smes.md` |
| https://www.amazon.co.uk/gp/help/customer/display.html?nodeId=Tvh55TTsQ5XQSFc7Pr | 2026-10-17T05:37:51.593Z | YpnX9oE6RPNjc2bk2 (wcc-amazon-de-uk) | `pages/www-amazon-co-uk-gp-help-customer-display-html-nodeId-Tvh55TTsQ5XQSFc7Pr.md` |
| https://www.amazon.com/b?ie=UTF8&node=216450446011 | 2026-10-17T05:34:59.395Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/www-amazon-com-b-ie-UTF8-node-216450446011.md` |
| https://www.amazon.com/gp/help/customer/display.html?nodeId=GQ2FT94RCVV5BA3Z | 2026-10-17T05:35:15.210Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/www-amazon-com-gp-help-customer-display-html-nodeId-GQ2FT94RCVV5BA3Z.md` |
| https://www.amazon.com/gp/help/customer/display.html?nodeId=THQ1gV8HWJ6jzUS6ed | 2026-10-17T06:17:12.858Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/www-amazon-com-gp-help-customer-display-html-nodeId-THQ1gV8HWJ6jzUS6ed.md` |
| https://www.amazon.com/gp/help/customer/display.html?nodeId=Tvh55TTsQ5XQSFc7Pr | 2026-10-17T05:35:00.100Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/www-amazon-com-gp-help-customer-display-html-nodeId-Tvh55TTsQ5XQSFc7Pr.md` |
| https://www.amazon.de/Rufus/b?ie=UTF8&node=100898398031 | 2026-10-17T05:37:43.379Z | YpnX9oE6RPNjc2bk2 (wcc-amazon-de-uk) | `pages/www-amazon-de-Rufus-b-ie-UTF8-node-100898398031.md` |
| https://www.amazon.de/gp/help/customer/display.html?nodeId=Tvh55TTsQ5XQSFc7Pr | 2026-10-17T05:37:43.305Z | YpnX9oE6RPNjc2bk2 (wcc-amazon-de-uk) | `pages/www-amazon-de-gp-help-customer-display-html-nodeId-Tvh55TTsQ5XQSFc7Pr.md` |
| https://www.amazon.science/blog/the-technology-behind-amazons-genai-powered-shopping-assistant-rufus | 2026-10-17T05:30:31.903Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-amazon-science-blog-the-technology-behind-amazons-genai-powered-shopping-assistant-rufus.md` |
| https://www.cnbc.com/2024/11/12/alibaba-launches-ai-search-for-small-biz-says-purchase-intent-jumps.html | 2026-10-17T05:31:22.606Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-cnbc-com-2024-11-12-alibaba-launches-ai-search-for-small-biz-says-purchase-intent-jumps-html.md` |
| https://www.cnbc.com/2026/03/24/openai-revamps-shopping-experience-in-chatgpt-after-instant-checkout.html | 2026-10-17T05:42:24.468Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-cnbc-com-2026-03-24-openai-revamps-shopping-experience-in-chatgpt-after-instant-checkout-html.md` |
| https://www.cnbc.com/2026/05/13/amazon-ditches-rufus-ai-chatbot-in-favor-of-alexa-shopping-agent.html | 2026-10-17T05:30:33.313Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-cnbc-com-2026-05-13-amazon-ditches-rufus-ai-chatbot-in-favor-of-alexa-shopping-agent-html.md` |
| https://www.computer-automation.de/produktionssoftware/ralf-buehler-conrad-wie-ki-den-b2b-einkauf-veraendert.htm | 2026-10-17T05:40:22.639Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-computer-automation-de-produktionssoftware-ralf-buehler-conrad-wie-ki-den-b2b-einkauf-veraendert.md` |
| https://www.conrad.de/de/ueber-conrad/presse/pressemeldungen/unternehmensmeldung/chatbot.html | 2026-10-17T05:41:18.326Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-conrad-de-de-ueber-conrad-presse-pressemeldungen-unternehmensmeldung-chatbot-html.md` |
| https://www.databricks.com/customers/grainger | 2026-10-17T05:43:15.051Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-databricks-com-customers-grainger.md` |
| https://www.digitalcommerce360.com/2025/11/26/amid-a-50-increase-in-worldwide-supplier-growth-alibaba-com-unveils-new-ai-functions/ | 2026-10-17T05:41:59.747Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-digitalcommerce360-com-2025-11-26-amid-a-50-increase-in-worldwide-supplier-growth-alibaba-com-un.md` |
| https://www.digitalcommerce360.com/2026/03/24/alibaba-international-announces-ai-agent-fleets-via-accio-work/ | 2026-10-17T05:39:37.040Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-digitalcommerce360-com-2026-03-24-alibaba-international-announces-ai-agent-fleets-via-accio-work.md` |
| https://www.digitalcommerce360.com/2026/05/21/lowes-ai-online-sales-q1-fy26/ | 2026-10-17T05:43:33.345Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-digitalcommerce360-com-2026-05-21-lowes-ai-online-sales-q1-fy26.md` |
| https://www.digitalcommerce360.com/2026/05/22/walmart-sparky-agent-ai-sales-supply-chain/ | 2026-10-17T05:42:47.060Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-digitalcommerce360-com-2026-05-22-walmart-sparky-agent-ai-sales-supply-chain.md` |
| https://www.estrategy-consulting.de/en/insights/marketplace-leaders-ralf-buehler-conrad-electronic/ | 2026-10-17T05:44:21.100Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-estrategy-consulting-de-en-insights-marketplace-leaders-ralf-buehler-conrad-electronic.md` |
| https://www.fool.com/earnings/call-transcripts/2026/05/07/grainger-gww-q1-2026-earnings-transcript/ | 2026-10-17T05:43:26.364Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-fool-com-earnings-call-transcripts-2026-05-07-grainger-gww-q1-2026-earnings-transcript.md` |
| https://www.gartner.com/en/newsroom/press-releases/2026-03-09-gartner-sales-survey-finds-67-percent-of-b2b-buyers-prefer-a-rep-free-experience | 2026-10-17T05:46:16.326Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/www-gartner-com-en-newsroom-press-releases-2026-03-09-gartner-sales-survey-finds-67-percent-of-b2b-b.md` |
| https://www.gartner.com/en/newsroom/press-releases/2026-05-20-gartner-survey-finds-sixty-nine-percent-of-b-two-b-buyers-turn-to-sales-reps-to-validate-ai-generated-insights | 2026-10-17T05:45:23.568Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/www-gartner-com-en-newsroom-press-releases-2026-05-20-gartner-survey-finds-sixty-nine-percent-of-b-t.md` |
| https://www.ikea.com/de/de/customer-service/knowledge/articles/f426b8f6-fdg2-411e-83bf-b6dggc645g8c.html | 2026-10-17T05:44:12.127Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/www-ikea-com-de-de-customer-service-knowledge-articles-f426b8f6-fdg2-411e-83bf-b6dggc645g8c-html.md` |
| https://www.ikea.com/se/en/customer-service/privacy-policy/privacy-policy-for-ikea-customers-pub019133cd/ | 2026-10-17T05:45:48.719Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/www-ikea-com-se-en-customer-service-privacy-policy-privacy-policy-for-ikea-customers-pub019133cd.md` |
| https://www.ingka.com/newsroom/ai-and-remote-selling-bring-ikea-design-expertise-to-the-many/ | 2026-10-17T05:39:52.772Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-ingka-com-newsroom-ai-and-remote-selling-bring-ikea-design-expertise-to-the-many.md` |
| https://www.ingka.com/newsroom/ikea-launches-new-ai-powered-assistant-in-openai-gpt-store/ | 2026-10-17T05:39:42.957Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-ingka-com-newsroom-ikea-launches-new-ai-powered-assistant-in-openai-gpt-store.md` |
| https://www.intercom.com/changes/en/80878-new-ui-for-fin-answers-and-handover-to-teammates-in-the-messenger | 2026-10-17T05:37:13.375Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-intercom-com-changes-en-80878-new-ui-for-fin-answers-and-handover-to-teammates-in-the-messenger.md` |
| https://www.intercom.com/help/en/articles/10032299-use-fin-ai-agent-in-workflows | 2026-10-17T05:43:37.099Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/www-intercom-com-help-en-articles-10032299-use-fin-ai-agent-in-workflows.md` |
| https://www.intercom.com/help/en/articles/12396892-manage-fin-ai-agent-s-escalation-guidance-and-rules | 2026-10-17T05:43:37.175Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/www-intercom-com-help-en-articles-12396892-manage-fin-ai-agent-s-escalation-guidance-and-rules.md` |
| https://www.intercom.com/help/en/articles/13128480-fin-for-sales-integrations-create-leads-in-your-crm | 2026-10-17T05:43:50.009Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/www-intercom-com-help-en-articles-13128480-fin-for-sales-integrations-create-leads-in-your-crm.md` |
| https://www.intercom.com/help/en/articles/13927077-how-to-train-fin-for-sales | 2026-10-17T05:43:49.014Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/www-intercom-com-help-en-articles-13927077-how-to-train-fin-for-sales.md` |
| https://www.intercom.com/help/en/articles/13927115-fin-for-sales-faqs | 2026-10-17T05:44:59.159Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/www-intercom-com-help-en-articles-13927115-fin-for-sales-faqs.md` |
| https://www.intercom.com/help/en/articles/15234261-configure-fin-s-behavior-when-no-human-agents-are-available | 2026-10-17T06:16:01.040Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/www-intercom-com-help-en-articles-15234261-configure-fin-s-behavior-when-no-human-agents-are-availab.md` |
| https://www.intercom.com/help/en/articles/16001516-fin-memory | 2026-10-17T06:15:59.048Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/www-intercom-com-help-en-articles-16001516-fin-memory.md` |
| https://www.intercom.com/help/en/articles/16198358-ask-a-teammate-for-help-with-fin-s-replies-human-in-the-loop | 2026-10-17T06:16:00.841Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/www-intercom-com-help-en-articles-16198358-ask-a-teammate-for-help-with-fin-s-replies-human-in-the-l.md` |
| https://www.intercom.com/help/en/articles/1729-setting-up-chats-and-posts-for-maximum-impact | 2026-10-17T05:44:50.559Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/www-intercom-com-help-en-articles-1729-setting-up-chats-and-posts-for-maximum-impact.md` |
| https://www.intercom.com/help/en/articles/2499085-customer-visits-a-page | 2026-10-17T05:44:50.873Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/www-intercom-com-help-en-articles-2499085-customer-visits-a-page.md` |
| https://www.intercom.com/help/en/articles/310-how-do-visitors-leads-and-users-work-in-intercom | 2026-10-17T05:43:49.409Z | 441FEIMGdGRPUOGLw (wcc-b4-lists) | `pages/www-intercom-com-help-en-articles-310-how-do-visitors-leads-and-users-work-in-intercom.md` |
| https://www.intercom.com/help/en/articles/8205718-fin-ai-agent-outcomes | 2026-10-17T05:37:05.446Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-intercom-com-help-en-articles-8205718-fin-ai-agent-outcomes.md` |
| https://www.lowes.com/l/about/ai-at-lowes | 2026-10-17T05:36:20.136Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/www-lowes-com-l-about-ai-at-lowes.md` |
| https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/ | 2026-10-17T05:43:46.975Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-microsoft-com-en-us-haxtoolkit-ai-guidelines.md` |
| https://www.nngroup.com/articles/ai-chatbots-design-guidelines/ | 2026-10-17T05:36:14.235Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-nngroup-com-articles-ai-chatbots-design-guidelines.md` |
| https://www.nngroup.com/articles/chat-ux/ | 2026-10-17T05:31:38.916Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-nngroup-com-articles-chat-ux.md` |
| https://www.nngroup.com/articles/chatbots/ | 2026-10-17T05:36:30.326Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-nngroup-com-articles-chatbots.md` |
| https://www.nngroup.com/articles/designing-use-case-prompt-suggestions/ | 2026-10-17T05:36:29.130Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-nngroup-com-articles-designing-use-case-prompt-suggestions.md` |
| https://www.nngroup.com/articles/impressions-chatgpt-agent/ | 2026-10-17T05:46:12.689Z | OMFaxlpG6yfbQwyQN (wcc-b5) | `pages/www-nngroup-com-articles-impressions-chatgpt-agent.md` |
| https://www.nngroup.com/articles/intelligent-assistant-usability/ | 2026-10-17T06:16:08.960Z | d19YtZUInid3VHh3l (wcc-b6) | `pages/www-nngroup-com-articles-intelligent-assistant-usability.md` |
| https://www.nngroup.com/articles/prompt-controls-genai/ | 2026-10-17T05:36:29.938Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-nngroup-com-articles-prompt-controls-genai.md` |
| https://www.nngroup.com/articles/prompt-suggestions/ | 2026-10-17T05:36:14.147Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-nngroup-com-articles-prompt-suggestions.md` |
| https://www.prnewswire.com/apac/news-releases/alibaba-international-launches-accio-work-an-enterprise-ai-agent-for-global-businesses-302721781.html | 2026-10-17T05:31:07.921Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-prnewswire-com-apac-news-releases-alibaba-international-launches-accio-work-an-enterprise-ai-age.md` |
| https://www.retail-week.com/fashion/app-tour-how-zalandos-ai-powered-chatbot-is-changing-customer-engagement/7051397.article | 2026-10-17T05:44:07.364Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-retail-week-com-fashion-app-tour-how-zalandos-ai-powered-chatbot-is-changing-customer-engagement.md` |
| https://www.retaildive.com/news/lowes-tailors-ai-assistant-mylow-different-customers/814461/ | 2026-10-17T05:40:21.440Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-retaildive-com-news-lowes-tailors-ai-assistant-mylow-different-customers-814461.md` |
| https://www.retaildive.com/news/walmart-sparky-chatgpt-instant-checkout/815647/ | 2026-10-17T05:46:25.053Z | nhYEE2N8zACk3aduc (wcc-b3) | `pages/www-retaildive-com-news-walmart-sparky-chatgpt-instant-checkout-815647.md` |
| https://www.sfgate.com/shopping/article/home-depot-magic-apron-ai-22413086.php | 2026-10-17T05:38:30.930Z | RprqhMkO9aiKCS8l1 (wcc-b1) | `pages/www-sfgate-com-shopping-article-home-depot-magic-apron-ai-22413086-php.md` |
| https://www.w3.org/WAI/WCAG22/Understanding/interruptions.html | 2026-10-17T05:31:53.326Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-w3-org-WAI-WCAG22-Understanding-interruptions-html.md` |
| https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html | 2026-10-17T05:31:53.509Z | TrRwuJPIOXuAAY33r (wcc-known-1) | `pages/www-w3-org-WAI-WCAG22-Understanding-on-focus-html.md` |
| https://www.walmart.com/cp/sparky/5291783 | 2026-10-17T05:35:33.961Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/www-walmart-com-cp-sparky-5291783.md` |
| https://www.zalando.de/campaigns/zfa/ | 2026-10-17T05:35:59.008Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/www-zalando-de-campaigns-zfa.md` |
| https://www.zalando.de/faq/how-does-the-fashion-assistant-work.html | 2026-10-17T05:36:01.059Z | 6ep3kFtfDlq2qhpn0 (wcc-protected-residential) | `pages/www-zalando-de-faq-how-does-the-fashion-assistant-work-html.md` |
