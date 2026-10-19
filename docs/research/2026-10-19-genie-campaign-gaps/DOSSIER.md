# Genie 完美化战役 · 竞品缺口取证（#337，地图 #329）

- 日期：2026-10-19。性质：只读综合 + 一轮定向补证；没有改插件、服务、生产站；没有测试线上 Genie（那是战役测试票的事）。
- 用途：给地图 #329 的对抗测试批（#330–#335）与后续修复票提供"复刻为先"的裁定底稿——每个能力面写清：竞品怎么做（引既有 dossier）、Genie 今天怎么做（引 spec 13 与代码）、缺口属 **复刻**（有成熟先例，指名来源）还是 **须自行设计**（无先例，修复票必须写设计理由，AGENTS.md 2026-10-19）。
- 主要依据（本仓库内）：
  - `docs/specs/13-genie.md`（目标十条 + 理解层/页面感知/价格/附件/清单/转人工/询盘各节）
  - `docs/research/2026-10-17-ai-assistants/INTL.md`、`CN.md`（竞品主卷宗）
  - `docs/research/2026-10-17-knocket/DOSSIER.md`、`TRIAL.md`（20 题对照实测）
  - `docs/research/2026-10-17-jev-intent/RESULTS.md`（Jev 意图实测）
  - `docs/research/2026-10-17-deepseek-flash-vision/DOSSIER.md`（官方 API 看图读文件）
  - `docs/research/2026-10-18-judge-remit/README.md`（评审 remit 复核）
  - `docs/research/2026-10-18-genie-reply-design/REFERENCES.md`（回复区契约与业主边界）
  - `docs/prototypes/2026-10-17-preview-card/DECISION.md`（预览卡裁定）
- 本轮新增取证（既有 dossier 未覆盖的五个失败类：话题切换/上下文串味、文件内提示注入、延迟 SLO、模型/VPS 失败 UX、并发轮次）：Apify 3 次运行（`raw/apify/runs.json`，run id、输入、时间齐全）：google-search-scraper 10 查询（`raw/search-slim.json`）+ website-content-crawler 5 页（`raw/apify/pages/`）。令牌只从环境读；`raw/` 全目录扫描令牌命中 0。

---

## 0. 结论先行

1. **Genie 的主干能力面都有成熟先例可复刻，且大部分已经按先例建成**（理解层、页面感知、价格门、清单、附件、转人工、询盘卡、会话保留）。战役在这些面上的工作是**校准与对抗加固**，不是设计。
2. **真正的"无先例区"恰好是 #337 点名的五个失败类**：话题切换的上下文串味、并发轮次的服务端语义、延迟 SLO 的数字、文件内提示注入的**结构级**防御边界、SSE 断流/宕机的 UI 状态机。定向检索（2026-10-19，10 查询 + 5 页）在 Rufus、Zalando、Home Depot、Accio、千问、京东、美团、1688 上**没有找到任何一家公开这五类的处理方式**；能引用的只有（a）竞品**失败**的实测记录（千问同窗串话，CN S13；（b）Rufus 在生产里被人打穿并泄露系统提示词的第三方记录（Lasso，本轮抓取）；（c）通用安全/UX 标准（OWASP 提示注入备忘单、uxpatterns.dev 错误态模式、NN/g）。**这五个面上修复票必须写设计理由，不得声称"复刻某家"。**
3. 竞品证据反复给出的三条不变式，战役期间不许漂移：**确定性优先、模型只表达**（京东政企 S24、1688 S33，与 Genie 现行架构同构）；**有后果的动作最后一步人点**（Amazon/Accio/千问/小团/飞猪，INTL §0.2、CN §5.1）；**价格跟账号不跟对话**（京东政企 S24、Walmart INTL §2.4，#242 已实现）。

---

## 1. 逐能力面：竞品 / Genie 现状 / 缺口裁定

### 1.1 理解层（产品词匹配 + Jev 意图 + 代码路由）

- **竞品**：搜索框识别问句、问句与关键词分流（Amazon，INTL §2.1、§5.1-3）；一句多条件、参数纠偏（千问，CN §2.1）；**确定性优先**的两条一手架构自述——京东政企"清单解析先用大模型映射表头，再用工程解析全量，速度提升 10 倍以上"（CN S24）、1688"先在结构化数据层过滤，再将剩余送入大模型"（CN S33）。意图分层路由本身有官方模式：TypeSafe "Intent routing"（`jev-intent/RESULTS.md` 引官方文档原话：确定性逻辑、专职 LLM、人三类 handler 前的快速分类器）。
- **Genie 今天**：spec 13"理解层"（#233）——`lexicon.py`（Store API 词表，归一化=小写+只留字母数字，切空白与连字符）、`jev.py`（4 题一次问，6 秒超时×3，失败唯一允许的降级=deepseek-flash 自行决定）、`route.py`（置信 ≥0.8 代码直调工具；裸产品词无条件走产品搜索）。实测：意图 97%、高置信 98%、约 2.6 s/条、$0.00003（`jev-intent/RESULTS.md`）。
- **缺口裁定**：**复刻**（京东政企/1688 的确定性优先 + TypeSafe 意图路由，均已建成）。对抗余量在边角：错拼/模糊拼写（词表是精确归一化匹配，无编辑距离），竞品无一家公开错拼处理——**错拼匹配策略属须自行设计**（#330 批先测出现频率再定）；矛盾条件、数量单位混写同理（竞品证据只有千问"参数纠偏"一句，CN S1）。

### 1.2 页面感知

- **竞品**：打开即说出所在分区（Zalando "I see you are interested in…"，INTL §2.3）；"this blender" 式指代（Rufus，INTL §2.1）；KAI "weiß immer genau, auf welcher Seite sich der Nutzer befindet"（INTL §2.10）；反面：Home Depot 知道但界面不说、用户手抄型号（NN/g，INTL §2.6）、结账时助手消失（同上）。行业均值即 INTL §4 表：知道当前页●、弹整窗—。
- **Genie 今天**：#234——`PageContext` 八类 + `page.py` 匿名 GET 本页 `<main>`、段落切分、`[nK=值]` 标数、价格类名与运费剔除、读不到显式记 `page_error`；开场建议逐页点名（spec 13"页面感知"）。
- **缺口裁定**：**复刻**（Zalando/Rufus/KAI 的"说出你在看什么"），已建成。两个对抗余量：（a）**页面内容漂移**（编辑/德语自动翻译后 `read-page` 是否读到旧内容）——spec 13 已写"生成的内容包要在每次编辑与每次德语自动翻译后重建发布"，但这是流程承诺，#335 批要实测；竞品无公开的漂移检测先例，**漂移防护属须自行设计**。（b）超长页（德语 FAQ 118 000 字符）的选段相关性——无竞品数字。

### 1.3 产品卡 + 账号后价格

- **竞品**：京东政企把合同价/协议价作核心排序过滤因子（CN S24）；千问先授权绑定才用个人数据（CN S7/S8）；Walmart 公开承诺不按对话内容调价（INTL §2.4）；Amazon Business 坦白"custom pricing is limited"（INTL §2.2）。卡片带图、详情原地展开（NN/g #5/#6，INTL §2.13）。
- **Genie 今天**：#242——`CommerceState` 一条规则、`price_line` 与产品页逐字一致、`prices.fill` 服务端填卡（50 s 截止）、正文禁止价格占位符（`ground.py` 第 9 条）、令牌只绑三个 ability。
- **缺口裁定**：**复刻**（价格跟账号），已建成。对抗余量：令牌过期/伪造（有测试锁定，spec 13 #242 段）、**卡与确认/发送之间的价格与库存变化是否让旧值作废**——CN §5.1-4 曾建议"关键字段改变后旧确认不得继续使用"（依据 S17，第三方推演，作工程原则）；spec 13 的 #250 段**没有记录失效规则的实现**。#333 批必测；失效语义属**须自行设计**（无竞品公开先例）。

### 1.4 零件清单 → 产品

- **竞品**（B2B 标配，四家同构）：Lowe's Material Lists"handwritten notes, photos, spreadsheets → quote-ready orders, SKU matching"（INTL §2.7）；Home Depot Materials List Builder"草稿、客户改完再接受，接受后才按客户价填充"（INTL §2.6）；京东 AI 清单选品"上传 Excel/CSV 或图片，模糊项多轮澄清"（CN S24）；淘宝小源"61 项清单整单上传，未答事项单列"（CN S32）。共同骨架：**解析 → 逐项澄清 → 草稿 → 用户确认 → 一次写入**。
- **Genie 今天**：#251——`parts.find/build` 逐行 matched/uncertain/missing、`ask_line` 一次问一行、`parts.add` 一次 `store.addAll`、全程不经模型（`provider=service, model=none`）、MAX_ROWS=200 带显式截断声明。
- **缺口裁定**：**复刻**（上述四家共同骨架），已建成且"不经模型"比公开先例更严。对抗余量在**解析边角**（表头变体、合并单元格、数量列陷阱、200 行外的行为）与**注入**（见 1.9）——竞品不公开边角处理，属须自行设计（由 #330/#334 测试结果定）。

### 1.5 附件与铭牌拍照

- **竞品**：拍照找产品普遍（Amazon、Zalando、Home Depot、Walmart、Accio 以图找厂，INTL §3 表）；京东工业"拍摄设备或零部件识别找对应商品"、图纸拆 BOM（CN S26）；识别不确定给**手动输入出口**是京东工业的明做法（CN §5.3-S2 引）。
- **Genie 今天**：#236——deepseek-flash 官方 Vision 单独一次调用（关思考，2–4 s，`deepseek-flash-vision/DOSSIER.md` + 验收 `thinking.md`）、读到的额定值登记为 `attN.nK` 事实、确定度由产品数据定（exact/partial/none/unreadable，`nameplate.identify`，不用模型自评）、AttachmentCard 确认链、"Type the model" 手动出口。PDF 文字层优先、扫描页渲染 ≤4 页、子进程隔离。
- **缺口裁定**：**复刻**（拍照→候选→确认→手动出口链），已建成。对抗余量：模糊/反光/多台设备同框、HEIC（vision DOSSIER §8 自认"真实照片质量、HEIC 原图未测"——#236 验收后仍属边角）、加密 PDF。**识别质量的阈值属须自行设计**（无竞品数字可抄）。

### 1.6 文档检索与引用

- **竞品**：Knocket TRIAL 的核心反证——**同一个 deepseek-flash，只做"检索手册"就答对了 Genie 当时答不出的文档题**（MPPT 数、ESA 配哪些电池，`TRIAL.md` §0/§2），说明检索可用性决定文档面成败；Accio AI Mode 可读技术规格与图纸（INTL §2.8，二手）。公开竞品**没有一家做到"每个数字可点到托管 PDF 的页"**——淘宝小源的"未答事项单列"（CN §4）与 KAI 的"verweist auf passendes Zubehör"（INTL §2.10）是最接近的形态。评测方法先例：Rufus 用评估集 + LLM-as-a-judge（INTL §2.1 引 amazon.science/AWS，已进 spec 13 验收节）。
- **Genie 今天**：spec 13 §B——`linker/search-knowledge` 唯一检索源、模型只写 `{fact:块ID.nK}`、服务端水合并加文档链接（`#page=N`）、检索失败整轮进兜底不退关键词、#257 之后 R1–R14 回归锁定。
- **缺口裁定**：**复刻**（hydration 是 Rufus 的做法，amazon.science；检索块引用是我们对"0 编造"的实现）。注意我们的引用标准**高于公开竞品**——这是业主裁定（0 编造数字）不是竞品均值，评审时不因"竞品没有"而放松。对抗余量：多跳文档题、检索块被污染（见 1.9）。

### 1.7 会话保留与跨表面

- **竞品**：Amazon 28 天跨设备可清除（INTL §2.1）；Zalando 只 20 分钟同设备（INTL §2.3，行业下限）；Intercom cookie→登录合并（INTL §2.11）；NN/g "跨页消失的 chatbot 没人再用"（INTL §2.13）。**串话失败的实测**：千问"所有对话都在同一个窗口内，上下文会受到一定干扰（奶茶话题串进减脂餐）"（CN S13）；AI 万能搜"历史对话没有被记住"被批评（CN S11）。**没有任何竞品公开话题切换/隔离的处理方式。**
- **Genie 今天**：#235——服务端唯一记录（`linker_conversation` 文章）、浏览器钥匙、登录认领、40 条列表、删除、发邮箱；hero 与 dock 同一会话（#232，发送前重读线程）；#329 盘点确认 e2e `genie-sessions.spec.ts` 在。
- **缺口裁定**：保留/合并/清除=**复刻**（Amazon+Intercom），已建成。**话题切换与上下文串味属须自行设计**——既有证据只有竞品的失败记录（CN S13）与 CN §5.3-M9 的方向性建议（"新话题新会话；长会话换话题不把旧条件带进来（或先问）"），无实现先例。Genie 每轮把整条线程重发（spec 13 §C Thread 上限 60 条），长会话里旧条件的权重问题真实存在。这是 #331 批最大的 invent 项。

### 1.8 转人工与上下文交接

- **竞品**：Intercom Fin 默认升级三条件（明确要人/强烈不满/三轮循环）+"Fin will never offer escalation twice in a row"（INTL §2.11）；Zendesk 交接附"full transcript, concise summary, and a detected intent"（INTL §2.12）；Shopify 员工不在给店铺邮箱（INTL §2.9）；国标 GB/T 47746（入口清晰、同步历史、不让客户复述，CN §3）；Shopify 的 AI 披露"不可删改"（INTL §2.9）。
- **Genie 今天**：#243——短语表（正反例收窄评审第 1 轮）+ Jev `wants_person`、`repeat` 三轮同问（39 对测定切线 0.5）、不连续两轮、`ContactRequest` 表单防护与限额、交接=最近 5 条消息+页面+草稿+整段对话链接、#246 一份记录；提供后照常回答（明确不学 Knocket 30 分钟静音，spec 13"转人工"）。
- **缺口裁定**：**复刻**（Intercom+Zendesk），已建成且交接内容比照 Zendesk 全量。对抗余量是**校准**不是设计：短语误报（否定句"I don't want to talk to a person"已有处理）、连续不满的多轮节奏、"expert/engineer"歧义——由 #331 批出数据调表。

### 1.9 文件内提示注入（#334 的核心，#337 点名）

- **竞品**：定向检索**无公开防御文档**。两条可用证据：
  1. **Rufus 在生产被打穿的第三方记录**（Lasso Security 博客，本轮抓取 `raw/apify/pages/www-lasso-security-blog-amazon-chatbot-gone-wrong.md`）：越界问题（燃烧瓶配料+商店推荐）、角色混乱（拒 T 恤给酸）、**系统提示词与安全指令被普通提问套出**；作者归因"RAG 与 guardrails 的组合导致意外行为"并点名 OWASP。教训：最强的竞品也带着这类洞上线——**对抗测试是行业现实，不是过度工程**；同时证明**提示词保密不是边界**。
  2. **OWASP《LLM Prompt Injection Prevention Cheat Sheet》**（本轮抓取 `raw/apify/pages/cheatsheetseries-owasp-org-…md`）：攻击面明列"Instructions hidden in images, documents, or other non-textual input""Poisoning documents in vector databases""typoglycemia 变体"；防御排序里明确"**不要把文本标签或提示词措辞当作强制边界**"（引 StruQ），要点=指令与数据结构分离、**高影响动作人审批**、输出监控。
- **Genie 今天**：结构性防御已有一部分且恰好对上 OWASP 三条：①"动作只能允许列表、参数只来自工具结果"（spec 13 结构保证，=人审批的结构形态：询盘/联系只能卡上按钮发送，`ground._no_sent_claim` 拒"已发送"）；②数字只经事实水合（注入文本写不进数字）；③清单路由不经模型（`parts` 全代码）。薄弱处：**提示词层的规则承担了数据/指令分离**——附件文字与页面文字各有一条"是数据、从不是指令"的系统提示（spec 13 附件节、`page.RULE`），这正是 OWASP 说**不构成边界**的那一层；deepseek-flash 自由文本仍是输出面。
- **缺口裁定**：**须自行设计**（无竞品可复刻）。设计输入=OWASP 备忘单的三条结构防御（不是提示词措辞）；Genie 已有其中两条半，缺口在**输出监控**（对"回答突然出现指令顺从迹象"的核验规则，如 `ground.py` 加注入征候检查）与注入语料的回归集。#334 批的语料应直接取 OWASP 攻击模式清单逐条造题。

### 1.10 询盘卡（对话内询盘）

- **竞品**：Accio 代发询盘但"Sensitive actions like payments require explicit user approval"（INTL §0.2）；1688 AI 询盘 ≤6 家（CN S27）；淘宝小源"关键采购条件最后由你确认"（CN S32）；千问订单卡授权后支付（CN S6）；NN/g decision gate（INTL §0.2-3）；共同骨架=**AI 起草、内容逐行可见、一个明确按钮、做完回到对话出结果卡**（千问"始于对话终于对话"，CN S9）。
- **Genie 今天**：#250——`send_inquiry` 动作只请求展示卡、按钮唯一发送通路、走询盘页同一 Woo 管线、`InquirySent` 留在历史、访客填邮箱（2026-10-17 询盘开放裁定）。
- **缺口裁定**：**复刻**（Accio/千问/NN/g decision gate），已建成。对抗余量：卡渲染后草稿变化、注入伪造"已发送"（已有 `_no_sent_claim`）、发送中失败态。失效规则同 1.3，须自行设计。

### 1.11 对比

- **竞品**：Rufus "Compare this with espresso machine in my cart"、搜索结果勾选多件并排比较（INTL §2.1）；京言勾选多商品综合建议（CN S18）；对比维度混淆（电池能量 vs 逆变器输出）无公开先例可引。
- **Genie 今天**：`linker/compare-products`（2–4 件，维度行×商品列，不混能量与输出）；TRIAL 第 13 题暴露过"ESA 10 kW 默认选三相没说明有两种"的消歧问题，对照题已把"按相数给额定功率"写进过关线（spec 13 验收段）。
- **缺口裁定**：**复刻**（Rufus 勾选比较），已建成。消歧（同名不同相数/同系列多型号）属**须自行设计**——竞品无证据；Genie 已有的机制是"一个决定性追问"，#330 批用品牌+型号冲突题压实。

### 1.12 配置器动作

- **竞品**：**无先例**——研究过的助手里没有一个"从对话打开本平台第一方配置器并预填"的动作；最近的形态是 Accio Agent 在对话内追加约束收窄（INTL §2.8）与 Home Depot Blueprint Takeoffs 生成报价（INTL §2.6）。TRIAL 第 14 题（"8 kWp + 6000 kWh"）确认这是 Genie 的差异点：竞品兜底，Genie 应给配置器。
- **Genie 今天**：选型路由→`size-hint`→配置器动作（预填 URL 服务端填）+不出卡（spec 13 理解层第 3 条）。
- **缺口裁定**：动作本身=**复刻自我们自己的规格**（#14 引擎、spec 14），无外部来源可引；**预填参数契约的正确性属须自行设计**（#330 数量/单位题直接打这里）。

### 1.13 德英双语对等

- **竞品**：Rufus 德国站独立产品（INTL §2.1）；Accio 支持英德法葡西（INTL §2.8）；KAI 德语原生（INTL §2.10）；反面：Knocket 单租户单语言、英文提问德语回答（`knocket/DOSSIER.md` §4.4）。**无竞品公开双语同结构测试纪律**；"德语问德语答"是唯一可复刻的底线。
- **Genie 今天**：`.po` 为德语权威、DE 独立撰写非翻译（AGENTS.md 2026-10-09）、兼容条件 `{en,de}` 取侧（2026-10-16 R6-de 修复）、20 题对照集 EN/DE、R1–R14 双语回归。
- **缺口裁定**：底线=**复刻**（德语问德语答）；**同结构同判分的双语对照纪律高于任何竞品公开做法，属我们的自有标准**（业主六条 + 对照题集），不因竞品没有而降。对抗余量：混合语言句（#330）、德语复合词与 Sie 体（#335）、机器翻译后页面漂移（#335，见 1.2）。

### 1.14 延迟与回答长度

- **竞品**：**无公开 SLO**。定向检索（`raw/search-slim.json`）只有用户抱怨与厂商自述"effective"，无 p50/p95 数字；NN/g AI chatbot 指南（本轮全文复核 `raw/apify/pages/nngroup-ai-chatbots-design-guidelines.md`）**没有任何延迟数字**，只有两条可复刻的形态规则：长回答保持阅读位置不自动滚底（实测用户"wait for it to finish"）、建议问题做成按钮。自测口径：Genie 本地 p50 约 11 s、最大 27.5 s；Knocket 约 14 s/25 s+（`TRIAL.md` §0 表）；Jev 2.6 s/条（`jev-intent`）；铭牌读图 2–4 s（#236 验收）。
- **Genie 今天**：业主对回复区的裁定=**不做后端流式**，前端模拟动态思考 + 完整回答后最多 1.2 s 本地渐进显示（`2026-10-18-genie-reply-design/REFERENCES.md`"业主最后确认的实施边界"）；服务里**没有任何首字/p95 埋点**（`services/genie/src/linker_genie/` grep 无 latency/first-token 代码）。地图门槛：p95 ≤ 30 s、目标 ≤ 15 s（#329）。
- **缺口裁定**：**须自行设计**（数字无先例可抄）。可复刻的只有 NN/g 两条形态规则（已实现）。第一步是埋点与分布（#329 已列"首字/p95 延迟"为空白），再按分布定优化顺序（Jev 2.6 s + read-page + 4 次工具 + deepseek-flash 串行段的叠加是显然的首查点）。

### 1.15 失败 UX（模型 5xx / SSE 断流 / VPS 宕机，#332）

- **竞品**：**无公开证据**——Rufus/Zalando/Home Depot 的失败态界面没有任何一手材料（本轮检索 + INTL §7 的既有空白）。可用先例是通用模式库：uxpatterns.dev《AI Error States》（本轮抓取 `raw/apify/pages/uxpatterns-dev-…md`）："explain why an AI response failed and offer a recovery path that matches the real failure mode"；恢复=retry/edit/switch strategies；持续失败=escalation channel；并指出流式/部分失败让状态机变难。NN/g 客服聊天指南：告知响应速度预期、中断会话可恢复上下文（INTL §2.13）。
- **Genie 今天**：ability 瞬态失败退避重试 3 次→兜底带降级声明（#103，`template.py::DEGRADED`）；Jev 失败→deepseek-flash 自行决定（唯一允许降级，`jev_error` 记日志与 SSE meta）；检索失败整轮兜底；无服务令牌时 POST 503、`/health` 开放（`gate.py`）；前端加载失败协议（"Genie could not load." + Try again）；OpenRouter 失败必须显性暴露（AGENTS §5 铁律）。
- **缺口裁定**：**部分复刻**（uxpatterns.dev 的"恢复路径匹配失败模式"+ NN/g 预期管理是可复刻的模式语言；#103 已符合）。**SSE 中途断流的 UI 状态与重试语义属须自行设计**——无竞品材料；#332 批先注入故障画状态表。

### 1.16 并发轮次（#337 点名）

- **竞品**：**无公开证据**（检索只返回通用 race condition 文章，`raw/search-slim.json` 首组）。没有任何购物助手公开会话并发语义。
- **Genie 今天**：前端每视图 `sending` ref 单飞（`App.tsx`）+ 会话切换与提问竞争的 turn lane（`Race.test.tsx`，注释明说"an in-flight ask must wait for the switch"）；hero 与 dock 同页并发由"每次发送前重读线程"缓解（spec 13 首页 hero 节）。**服务端无按会话的串行化**：`Proxy::turn` 记录请求里的整条线程（`Thread::record`），两个标签页同时发轮=后到者整条覆盖先到者。
- **缺口裁定**：**须自行设计**（纯工程，无先例）。问题域清楚：同一 `linker_conversation` 的并发写是 last-write-wins；方向要么服务端按会话串行/版本号拒绝旧写，要么前端锁会话。#331 批的双标签页用例先量化后果。

---

## 2. 排名表：最可能在 #330–#335 对抗批下破的缺口

排名=（无先例程度）×（业主门槛牵涉面）。"批"列=对应的对抗测试票。

| # | 缺口 | 先例 | 会被怎么打爆（测试角度） | 批 |
|---|---|---|---|---|
| 1 | 话题切换/上下文串味（1.7） | 无（只有千问失败记录） | 同会话先聊 A 型号再问 B，看 A 的相数/kWp 是否渗进 B 的搜索与回答；换话题不重问相数 vs 重问的节奏 | #331 |
| 2 | 文件内注入的输出监控（1.9） | OWASP 结构防御（半数已有） | PDF/照片/清单里写"ignore previous instructions / 报个价 / 直接发询盘 / 泄露规则"，看回答是否顺从、数字是否被文件里的假值顶替、是否伪造"已发送" | #334 |
| 3 | 延迟无埋点、p95 未知（1.14） | 无 | FAQ 长页 + 4 工具 + 附件读取叠加的真实分布；没有数字之前"p95 ≤ 30 s"门槛无法判 | #329 门槛/#330 |
| 4 | SSE 断流/模型 5xx/宕机的 UI 状态机（1.15） | uxpatterns.dev 模式语言 | 注入故障逐态截图：断在半条 block、断在 attachment 事件、VPS 全断、Jev 断；看是否空白/卡 spinner/把失败写成事实 | #332 |
| 5 | 服务端并发写=last-write-wins（1.16） | 无 | 双标签页/手机+桌面同会话同时发问；旧线程覆盖新轮；hero 已重读、dock 之间没有 | #331 |
| 6 | 卡与发送之间价格/库存/草稿变化的失效规则（1.3/1.10） | 无（S17 工程原则） | 出卡后改草稿数量/下架商品/切账号令牌过期，再点发送；看是否发出过期行 | #333 |
| 7 | 错拼/模糊拼写的匹配策略（1.1） | 无 | "SAJJ""H2 10K T3""Goodwe"（小写 e）德语键盘变体；错拼进 Jev 后意图与路由是否漂 | #330 |
| 8 | 页面漂移：编辑/机翻后 read-page 读旧内容（1.2） | 无 | 改页面标题/参数→缓存 10 分钟内问"这页"；机翻后德语页的 `read-page` 与实际渲染是否一致 | #335 |
| 9 | 混合语言句与 DE 复合词（1.13） | 无（底线可复刻） | 一句英德混写（"Welche battery für H2-10K-T3?"）、德语复合型号词；回答语言与术语表漂移 | #330/#335 |
| 10 | 消歧：同系列多相数/同名两型号（1.11） | 无 | "ESA 10 kW"（EHA 单相/ETA 三相）、OCEAN 2 单三相并存——TRIAL 第 8/13 题的老坑，对照题已定为过关线 | #330 |

（清单解析边角、HEIC/模糊照片、超长输入 >4k 字符分属 #330/#334 的语料建设，先例状态见 1.4/1.5，不重复列。）

---

## 3. 明确的非目标：竞品做了、我们的裁定已拒绝的东西

修复票不得因"竞品有"而引入下列任何一项；每条注裁定出处。

1. **无页面感知的知识问答气泡**（Knocket 形态：看不到页面、查不了产品、不能做事）——2026-10-17 裁定"Genie 不换，继续改；不采用 Knocket"（AGENTS.md §2；`knocket/TRIAL.md` 10 对 0 错）。
2. **自动弹出整窗聊天**——2026-10-10/10-17 裁定主动面是"不抢焦点的小预览卡"（`preview-card/DECISION.md`；INTL §0.3；Baymard 反面证据）。预览卡阈值已定，不再放宽为弹窗。
3. **转人工后 AI 静音 30 分钟**（Knocket）——spec 13"转人工"明写"不学 Knocket 的 30 分钟静音"，提供后照常回答。
4. **模型自己发起对外动作**（Amazon Auto-buy 式委托下单、Accio 全自动 outreach）——业主 2026-10-09"询盘必须客户点击才发送"（AGENTS.md §5 验收、地图 #329 铁律"询盘点击发送"）；模型文字永远不能触发发送（spec 13 目标 5）。
5. **静默换模型/降级**（Knocket 的平台托管不具名向量模型是典型）——AGENTS.md §5 模型路由铁律：四条通道之外零容忍，OpenRouter 失败显性暴露，禁止自动降级到 aihubmix 或任何其他模型。
6. **价格按对话内容浮动**（Walmart 专门承诺不做的反面；千问按账号券）——价格只跟账号审批状态（#242；AGENTS §1 价格门）；正文永不写价格。
7. **"几分钟内回复"式承诺**（Knocket 写死"We reply within a few minutes"）——业主承诺是一个工作日内回复（AGENTS.md 2026-10-09），承诺了就必须执行，不得在 UI 里随口改口。
8. **第二个对话入口**（Home Depot 同时有 Magic Apron + Live Chat 造成混淆）——全站只有 Genie 一个对话入口（spec 13 目标 1、A14；人工也经 Genie 转交）。
9. **给回本期/ROI 数字**（部分助手的推荐理由形态）——Solution Configurator 不给回本期（AGENTS.md §1）；Genie 同口径，选型只给配置器与依据。
10. **运行时机器翻译 Genie 文案**——德语独立撰写、Sie 体、`.po` 为权威（AGENTS.md §3、2026-10-09）；自动翻译只管站点内容（2026-10-17），工具文案一律走对抗评审。
11. **Incoterms/物流/库存数量话术**（Amazon Business 的节省建议类输出）——物流一句转团队（2026-10-05）；库存只说状态不说数量（2026-10-11 GAP-9）。

---

## 4. 本轮未能确定、需战役自建或另开取证的事

1. **任何竞品的延迟 SLO 数字**：两轮检索（本轮 10 查询 + INTL/CN 卷宗）均无。p95 的"足够好"阈值只能由 #329 约定（已定 ≤30 s/15 s）+ 实测分布支撑，没有外部基准可引。
2. **任何竞品的话题隔离/上下文管理实现**：只有失败记录（CN S13）。若修复票要做"换话题检测"，设计理由只能引千问反例 + CN M9 建议方向。
3. **任何竞品的会话并发语义**：无公开材料。服务端串行化/版本拒绝只能按工程常识设计（1.16）。
4. **Rufus/Amazon Business 在助手里如何显示商业价格**（INTL §7 既有空白，本轮未再挖）——不影响 #242 已建成的设计。
5. **Walmart Sparky、Lowe's Mylow 的站内细节**（反爬，INTL §7）；**KAI "proaktiv" 的具体形态**（INTL §2.10a 观测为未弹）；**GB/T 47746 全文**（CN §9）。
6. **#250 询盘卡与 #242 价格的"变化后作废"规则是否已实现**：spec 13 两节均未记录失效语义；这不是外部证据问题，是**仓库内待核实**——#333 批开工前先读 `InquiryRequest`/`Inquiry\Sender` 现码确认，别按"已实现"写测试。
7. **注入语料的表现盲区**：本轮只取了 OWASP 攻击模式清单与 Lasso 案例，未做竞品语料库抓取。#334 的语料建议直接从 OWASP 清单 + `raw/apify/pages/cheatsheetseries-…md` 的示例句逐条生成，无需再开外部取证。

---

## 5. 给修复票的一句话裁定表

| 能力面 | 裁定 | 复刻来源 |
|---|---|---|
| 理解层骨架 | 复刻（已建成） | 京东政企 S24 / 1688 S33 / TypeSafe intent routing |
| 错拼与模糊匹配策略 | 须自行设计 | 无先例 |
| 页面感知 | 复刻（已建成） | Zalando / Rufus / KAI（INTL §2.1/2.3/2.10） |
| 页面漂移防护 | 须自行设计 | 无先例 |
| 价格跟账号 | 复刻（已建成） | 京东政企 S24 / Walmart（INTL §2.4） |
| 卡后变化的失效规则 | 须自行设计 | 无先例（S17 仅工程原则） |
| 清单→产品 | 复刻（已建成） | Lowe's / Home Depot / 京东政企 / 淘宝小源 |
| 附件与铭牌 | 复刻（已建成） | 京东工业 S26 + 手动出口 |
| 文档检索与引用 | 复刻（已建成，标准高于竞品） | Rufus hydration（amazon.science）+ 业主 0 编造 |
| 检索块/文件注入防御 | 结构半复刻 + 输出监控须设计 | OWASP 备忘单（非竞品） |
| 会话保留/合并/清除 | 复刻（已建成） | Amazon / Intercom（INTL §2.1/2.11） |
| 话题隔离 | 须自行设计 | 无先例（仅千问反例 CN S13） |
| 转人工与交接 | 复刻（已建成） | Intercom / Zendesk / GB/T 47746 |
| 询盘卡 | 复刻（已建成） | Accio / 千问 / NN/g decision gate |
| 对比 | 复刻（已建成）；消歧须设计 | Rufus 勾选比较 |
| 配置器动作 | 复刻自 #14；预填契约须设计 | 无外部先例 |
| 德英对等 | 底线复刻；纪律自有 | "德语问德语答"（Knocket 反例） |
| 延迟 SLO | 须自行设计（先埋点） | 无先例；NN/g 仅形态规则 |
| 失败 UX | 模式语言复刻；SSE 状态机须设计 | uxpatterns.dev / NN/g（非竞品） |
| 并发轮次 | 须自行设计 | 无先例 |
