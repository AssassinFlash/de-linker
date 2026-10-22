# de-linker · 工作规则

这里没有硬规则。每一条都可以被证据推翻；推翻时写明是哪条证据，并改这份文件。
本文件只写做事的依据，不写历史、不写流程仪式。详细证据在 `docs/research/`。

## 1. 这是什么

de-linker.com：Linker Technology GmbH 的 B2B 光伏储能询盘网站，WordPress + WooCommerce，英德同等。
客户是安装商、EPC、经销商。链路只有一条：产品分类与产品 → 询盘（以 Proforma 呈现）→ 之后全部线下。
订单→询盘/Proforma 链、付款、发货、采购、分组、发票与任何后续处理不存在；**账号审批三态已于 2026-10-11 恢复**（票 #73：通过/限制/拒绝+原因邮件，WP 后台入口）。

两个客户可见的工具：
- **Genie - Linker's AI assistant**（德语 "Genie – der KI-Assistent von Linker"）：平台级 AI 助手，嵌在产品、询盘、账户各入口；首条消息明说这是 AI 系统。德语里不写 "Linker Genie" 连写；不注册商标。
- **Solution Configurator / Lösungskonfigurator**：输入 → 整套方案（可全部加入 Lösungsentwurf）→ 设计报告（自给率、自用比例、产量、选型依据、兼容放行与文件引用、Stückliste；可带 Logo 的 PDF；不给回本期）。屋顶描绘是它的可选一步。

## 2. 业主裁定（事实，按日期）

- 2026-10-02：产品分类里没有光伏组件；组件只出现在系统设计与项目报价。经销商是客户。库存只说有货。不说 Incoterms。
- 2026-10-05：对客户只说 Product / Model / Series（Produkt / Modell / Serie）。公司、服务、物流类问题一句话转团队邮箱 sales@de-linker.com。
- 2026-10-07：老板只要一个普通网站：注册登录、询盘后公司收到通知；交易线下完成。
- 2026-10-10：设计范围：营销页、产品页、博客页的设计**遵循线上现有设计**（照线上样式重建，不改版）；工具页（Genie、Solution Configurator，含屋顶步）的设计**可以改动**。**本地实例外观与线上一致是硬要求**：用于开发与验收的本地站必须先装入线上快照（主题与 uploads）；裸 WordPress 实例只作管线冒烟，不得用于任何 UI 工作或交付展示。
- 2026-10-10（补充，业主巡查本地实例后）：**商务页设计层的归属已查明**——线上购物车/询盘/账户/确认页的视觉不在主题里，而在被全拆的旧插件 CSS（storefront.css/commerce-ui.css/contact-*.css 等）里。裁定：**所有客户可见页面**（含商务全链：Lösungsentwurf、询盘提交、确认、账户、PI 下载）一律遵循线上现有设计——重建时必须**移植这层设计**到新结构（单一实现），不得只带机制不带视觉地留下裸 WooCommerce 店面；只有工具应用内页（Genie 对话、配置器三屏）可有自己的设计。**视觉验收的 parity 对照按页型逐一做**（本地 vs 线上对应页），首页对照不够。
- 2026-10-09：
  - 产品与 SKU 原样保留，不建套装 SKU；组合由工具按兼容合同即时算出。用途（Application）按厂商说法。**产品事实冲突时以我们托管的数据手册为准**（例：1959 CHS2-29.9K 的功率按数据手册 29 999 W；草稿 4124 的容量按手册）；手册取不到就记"无法核实"并保持现值。
  - 正式发票与网站无关。Proforma 有效期 30 天；承诺一个工作日内回复询盘（承诺了就必须执行）。
  - 营销正文的主动文案改写保持原裁定；德语自动翻译范围以 2026-10-17 补充裁定为准。工具相关文案全部重写。**客户可见文案（含事务邮件的主题与正文）一律走文案对抗评审**（业主 2026-10-11 裁定：只要是文案就要好好做）：初稿→评审意见→定稿记录在案（先例 docs/acceptance/2026-10-10/12/copy-review.md），EN 先行、DE 独立撰写非翻译，基准=linker-copywriting Hard Stops（email subjects 属公开面）+ 线上既有措辞与 .po 术语。所有 FAQ 均为编造，问题角度保留，答案逐产品由模型独立生成并对抗评审。
  - 全拆：旧仓库的自定义代码一行不以代码形式留下；带走的只有内容与数据、裁定、证据、核实过的规格。
  - 不买任何新的付费插件；现有许可（LiveCanvas、SEOPress PRO）可继续用。
  - 全部在本地建成后一次性更新原站，同域名同 URL；期间业主不改线上。
- 2026-10-11：**库存事实裁定**（票 #69；翻案记录 `docs/audit/2026-10-11-surface-inventory.md` GAP-9）：真实 ERP 存在、之后接入，本地模拟先行；**Woo 原生库存为唯一权威**（`_stock_quantity`/`_stock_status` 及其同步词项，无 TTL、无衰减语义）；**托管库存（开启"管理库存"）的商品数量为王**——状态由数量推导，分歧的状态词被拒（`state` 只对未托管库存的商品有效）。2026-10-02 的"库存只说有货"由此收窄为：对客户只说状态（有货/暂时无货）、从不说数量（`woocommerce_stock_format = no_amount`）。
- 2026-10-17（业主实测注册链与 Genie 后；地图 #220）：
  - **内部通知收件人**：新注册、VAT 复核、新询盘、联系表单留言、每日摘要等内部通知，暂时只发 sales@sunriverinverter.com，先确保整体走通；**不发 sales@de-linker.com**（老板的邮箱）；chester@de-linker.com 确认能收到才保留作抄送。客户可见的地址（Proforma 卖方邮箱、页脚、Genie 转人工句、发件人）仍是 sales@de-linker.com。chester@ 暂无腾讯企业邮 SMTP 授权码，发信仍走 Hostinger `mail()`。
  - **审批依据**：业主按注册时提供的信息自己查证，属实即批。注册只收够他查证的最少信息，其余在询盘 / Proforma 时再收。
  - **注册国家**：全部开放，欧洲为重点。
  - **看图与读文件**：铭牌拍照识别与附件读取用 deepseek-flash 做（官方 API 收图；PDF 先转成文字或页面图片，证据 `docs/research/2026-10-17-deepseek-flash-vision/`）。模型通道不变。
  - **首页 hero**：未交互时外观照旧（像素门不变）；打字、点胶囊、拍照、附件、语音之后的交互可以重新设计。
  - **线上实走验收**：账号链与 Genie 的验收包括按业主路径在线上实走。每次注册产生的真实邮件只限通知、已收到、已批准三封，收件人只限 sales@sunriverinverter.com 与业主指定的测试邮箱；其余测试照旧守测试邮件纪律。
  - **Genie 不换，继续改；不采用 Knocket**（依据 `docs/research/2026-10-17-knocket/TRIAL.md`：同一模型下 Genie 10 对 0 错、Knocket 6 对 1 错，且 Knocket 结构上做不到产品、价格、草稿、页面感知）。改造的过关线见 `docs/specs/13-genie.md` "目标"一节的验收。
  - **注册表单**：两步——第 1 步"您的公司"（公司名、业务类型、国家、网站或 VAT ID 至少一项），第 2 步"您和您的登录"（名、姓、邮箱、密码）；顶部两段进度条加 "Step 1 of 2 · Your company"；不收地址和电话（原型 `docs/prototypes/2026-10-17-registration/` 变体 B）。
  - **询盘对所有人开放**：不需要账号也能发询盘（推翻"发询盘需要账号"）。访客只填邮箱、姓名、公司（选填）和一个开放留言框，不问国家；Lösungsentwurf 里的产品一并带上。Proforma 请求页左右分栏（左表单、右草稿），已登录客户资料折叠成一行；地址、VAT 由团队开 Proforma 时补或从账号预填。联系表单保持现状；联系留言与询盘"两扇门、一份记录"（原型 `docs/prototypes/2026-10-17-inquiry/`）。
  - **账号状态**：待审账号注册后保持登录，只是不显示价格，也能发询盘；"限制"用于告诉客户信息不够（缺 VAT、公司资料等），原因给客户看。
  - **/wp-admin**：WooCommerce 把客户从 /wp-admin 转到 my-account 是保护行为，保留，但给说明页；员工以客户视角测试用 User Switching（免费插件，已装线上）。
  - **德语**：切到德语时一切都是德语专属——地址、标题、文案；德语自动翻译必须在线上运行，模型是 deepseek-flash（仅官方 API），全部页面（含营销页）、产品、博客及既有可翻译词项均由英文源自动同步，机器译文自动生效，无人工待审、批准或营销冻结名单。已有人工德语原样保留，没有基线时只记录当前英文基线，不调用模型；以后只翻英文改动且能对齐的句子，不做全站重译。对不上时保留原德语，状态为“德语未跟上：结构不同”，在后台与每日摘要显示异常；仓库部署的模板只由 present 发布，保留 Polylang 配对，排除机器翻译。失败保留上一版德语并在后台与每日摘要中可见（本票会话业主补充裁定，推翻先前的待审与营销冻结要求）。
  - **本地与线上同步**：本地实例是讨论与修改的参照，必须与线上一致（拉取后施加本地密钥，后台无杂项提示）。
  - **Genie 目标**：见 `docs/specs/13-genie.md` 的"目标"一节（主动预览卡选提示卡样式，原型 `docs/prototypes/2026-10-17-preview-card/`）。
  - **分工**：调研票与原型票由 Claude 完成，实现票交给其他 AI；实现完成后业主视情况请 Claude 评审。
- 2026-10-18（第 1 批全部合并后；地图 #220）：
  - **执行分工改定**：Genie 相关的票由 Claude 用子代理执行，一个子代理接一张票；其余的票交给 Codex，一个 Codex 任务接一张票。Claude 负责开任务、评审、合并、部署，并在合并后开启被解锁的票。先各试一张（子代理 #249、Codex #246），通过后再铺开。执行者一律在自己的工作树和本地实例里干活，不部署、不合并、不写生产。
  - **生产写入默认已获同意**：部署和票所需的数据写入不必再逐次请示；照旧先备份、后读回，并把改动与回滚方法记在票上。超出票计划的不可逆操作（例如删除旧的 `wp_genie_*` 表）仍单独请示。
- 2026-10-19：**Genie、Solution Configurator 与 RoofTop Canvas 的修改以复刻为先。**任何逻辑或功能层面的修改、测试、优化与工具间集成之前，先参照各工具既有的功能建立（规格、原型、现有实现与验收记录）与竞品研究（`docs/research/` 下对应 dossier；Genie 另有 Knocket `TRIAL.md` 与 `2026-10-18-judge-remit/`）；有成熟模式就复刻，没有先例才写设计理由再改。不拍脑袋发明。
- 2026-10-23：**统一配置器允许独立现代前端。**业主明确先正确使用，再采用当前稳定、现代的技术；允许调整架构和引入库，前提是保护既有站点。配置器的局部运行环境与构建例外见 `docs/adr/0002-isolated-planner-runtime.md`；此授权不等于构建、计算或生产验收通过。

业主只回答事实（产品数据、价格、承诺、厂商怎么说）。产品范围、工具存废、架构、措辞由本线按竞品映射与证据决定；决定只因新证据改变，改变时写明证据。

## 3. 用词

产品、产品分类；不说目录（catalogue）、文章（article）、篮子（basket/cart）。
客户的工作清单：Solution draft / Lösungsentwurf。方案内的清单：Bill of materials / Stückliste。
询盘四状态：Inquiry received / Anfrage eingegangen · Proforma invoice issued / Proformarechnung ausgestellt · Completed / Abgeschlossen · Cancelled / Storniert。
德语用 Sie 体（locale `de_DE_formal`）；禁止 "不是…而是…"、三连排比等 AI 句式；英德永远同步交付。

## 4. 技术选型（按复刻与适用定，证据见 docs/research/2026-10-09/framework-choice.md）

- 前端：既有插件用 WordPress 自带的 React、`@wordpress/scripts`、`@wordpress/i18n` + `wp i18n make-json`；每个插件一个 npm 包。统一配置器按 2026-10-23 裁定采用隔离的 `apps/planner` 包，不升级站点全局 React；样式仍走同一 WindPress 管线。
- PHP：Composer + PSR-4 命名空间，一类一文件；PHPUnit 9.6（WP_Mock）；PHPStan level 8；WPCS 3 + woocommerce-sniffs；Composer 锁 PHP 8.3。
- Python 服务（VPS，Python 3.12）：uv + pyproject；FastAPI + Pydantic AI；ruff、mypy、pytest。
- 多语言：Polylang 免费版做基座 + 我们自己的窄插件（同 slug、URL 段翻译、保存即翻译、REST lang、Woo 最小同步）。
- 商品数据：Woo 商品是唯一手工源；兼容合同与工程覆盖层（现 1 条，Trina 参考组件）是数据；引擎读生成的 feed。
- 知识库：我们自己托管的 PDF 按页检索（Docling 解析；构建产物是随 Genie 发布到 VPS 的 SQLite 索引——FTS5 + sqlite-vec，服务读 `current/index.sqlite`；`--mariadb` 可另导出共享主机 MariaDB 的 VECTOR + FULLTEXT SQL）；检索是 dense 单路，查询向量由索引自己的模型编码（gemini-embedding-2 仅经 OpenRouter 的 API，或构建机上的 ONNX），BM25 为所在主机没有查询编码器时的回退（embedding-bakeoff.md §2）；模型只能引用检索块 ID，数字由服务端填入。
- 邮件：Hostinger `mail()`（10 封/分钟、100 封/24 小时，四站共用），一封加 Bcc，重试覆盖 24 小时，生产环境禁止发信测试。
- 模块化由框架约定定义（一个组件/类/模块一个文件、按功能分目录、每个模块有测试），不以行数为指标。每个数字与阈值必须有来源注释。
- 呈现层（业主批准 2026-10-10，依据 LC/WindPress 正统实践调研与偏离审计）：**现状栈正规化**——LiveCanvas 动态模板承接 Woo 四类页面（商城/购物车/结账/账户/商品页，官方 starter 当底稿，B2B 数据经短代码供给）；德语页头页脚走每语言 partial（Twins，翻译 ID 经 Polylang 官方 API 解析：`pll_get_post`/`pll_get_term`）；tokens 进 WindPress 卷（`content/windpress/tokens.css`，`present` 安装并移除任何遗留的 Additional CSS 副本；消除页头生命周期耦合）；**WindPress 真用起来**（业主裁定：装了就是有用的，没有用到是失职）——Tailwind 类是新模板的样式词汇、插件输出 HTML 的表面注册 provider 进扫描面（`f!windpress/core/cache:compile.providers`，参考 picostrap 实现）、部署流程含缓存强制重建（消除陈旧缓存缺陷）、React 工具应用的类写进源码经同一条 WindPress 管线产出（不建第二条 tailwind 构建）。插件对站点页面零 CSS（语义 HTML 继承主题与设计体系）。旧实现的五项偏离（运行时字符串翻译/token 内联 partial/四通道 CSS/WindPress 荒废/PHP_INT_MAX 模板抢占）在新树上已不存在：翻译是随插件发布的 `.po/.mo`；tokens 经 `present` 进 WindPress 卷（同一份 `tokens.css`）；插件对站点页面零 CSS；WindPress 经 providers 注册进扫描面、样式只在后台编译进缓存；页面由 LC 动态模板承接，新树对模板钩子只做移除旧插件抢占（`tv_b2b_template_include` 的 PHP_INT_MAX）的动作，自己不抢占。偏离的载体随旧插件在切换时删除。

## 5. 交付

- 管线：本地 → 评审站 → 线上。线上不是任何功能第一次被看到的地方。
- 每张票一个新会话；先 `just up` 拉起本地栈。分支 → PR → CI 绿 → 本线 review → 合并。执行会话：Genie 票用 Claude（Opus）子代理，其余票用 Codex（2026-10-18 分工）。
- 验收三件套，缺一不交付：Spec + Standards 双评审（全量 diff）；改动所在层的真实夹具测试；Computer Use 视觉验收（1440 与 390，EN 与 DE，逐状态截图，以设计稿、需求与交互预期为基准）。
- **测试邮件纪律（业主 2026-10-11）：测试只发一封、只发 tester**。任何测试场景（夹具、e2e、验收、切换冒烟）中，邮件 To/Cc/Bcc 一律重写为 tester 单地址，一封送达即证明投递链路畅通；多收件路由（客户副本/团队/Bcc）的正确性以 **Outbox 队列收件人数据断言**验证——写在队列里即正确，不做多封实发。实现形态：测试模式收件人重写开关（选项或 env，WP-CLI 可设/可撤），#17 切换冒烟用同一开关，验证后关闭。
- **复刻面像素零差异（业主 2026-10-11：1 个像素点的偏差都算不通过）**：营销/产品/商城/分类/博客/页头页脚的视觉验收标准是**像素级**——live|local 全页截图由同一浏览器同机同视口拍摄（禁动画、等字体图片加载），像素比对**掩膜外差异数=0**；掩膜只许记录真实动态区（如随日期变的计数）且逐项报业主，未声明的差异像素即 FAIL。允许的像素差异只有一种：裁定过的变更（工具改名/工具页重设计/bug 修复）经变更台账呈现给业主过目。工具页不受像素门约束（重设计裁定）。
- **PHP 不解决设计问题，Snippet 不滥用（业主 2026-10-11）**：客户可见页面的组成只在 LC 动态模板、样式只在 WindPress。PHP 短代码只做数据装配、输出语义标记+类名的数据片段（零内联样式、零设计决策）；任何视觉差距的修复落点只能是 LC markup 或 WindPress 样式。禁止 PHP 页面类/布局模板；禁止经 Code Snippets 通道加代码（代码只进仓库插件，实例 snippets 表不动——旧项目的教训）。
- **模型路由铁律（业主 2026-10-11，零漂移）**：全站只存在四条模型通道——①**Genie 对话 = deepseek-flash，仅经官方 api.deepseek.com 直连**；②**Jev = typesafe/jev-1.13，仅经 OpenRouter 原生 /v1/systemone 端点**（chat 接口的 jev-router 是元路由、逐调用转包他人，禁用）；③**gemini-embedding-2 = 仅经 OpenRouter**；④**deepseek-flash 作为 Jev 级联升级判分器，仅经官方 API**（业主 Jev 设计的既有角色）。deepseek-flash（同一官方通道）另用于德语自动翻译（业主 2026-10-17）。**OpenRouter 上只允许 jev 与 embedding-2 两个模型出现**；**aihubmix 永不作默认**（仅业主明示切换时作 embedding 备用，禁止自动降级）；**禁止临时起意用任何其他模型替代**（gpt/gemini/claude/kimi/grok 等一律不出现）；OpenRouter 调用失败必须显性暴露（重试+报错），禁止静默降级。任何模型改动=业主裁定。
- **三件套原生优先（业主 2026-10-11：WooCommerce/LiveCanvas/WindPress 不得每次都被忽略）**：客户可见面的实现顺序=① LC 原生 tag（词汇表从实例 livecanvas 插件提取维护：lc_loop/lc_get_cf/lc_wc_product/lc_wc_related/lc_wc_product_tab_*/lc_wp_func…）② Woo 原生机制（属性/meta/related/tabs/模板函数）③ WindPress 管线（样式）。自定义代码是**最后手段**，须在规格文档留逐项穷尽证明（合格先例：B2B 价格门=`Gating\PriceDisplay` 在源头隐藏价格，Woo 原生不做门）；只做数据装配，零设计决策。
- 本轮发现的问题本轮修，不开 follow-up，不留 TODO。
- **旧政权词汇零容忍（业主多次明令）**：旧仓库的 Law/ADR 编号/旧工单号不得作为"依据"出现在本仓库任何代码注释、提交信息、文档、报告与评审结论里。旧材料只有一种合法用法：作为"线上现状/旧系统行为"的中性证据**改述**（不引旧编号）；规则依据只有本文件、新仓库票据与业主当期裁定。
- **全拆审计是常设门槛**（业主 2026-10-11，三次旧世界回流事件后）：任何票的评审包含旧代码缺失检查——旧标识符 grep（tv_b2b_/Linker_AI_/dlk- 等）+ 高风险区（引擎物理链、翻译器、账号链、NLU）的结构比对；**裁定过的新通道必须核到"真的在生效"**（如 LC 动态模板真的在渲染），"已登记待替换"不构成合格交付；#17 切换前做一次全树旧代码审计（方法与命令入库 docs/audit/，任何人可重跑）。携带物只限白名单：内容与数据、裁定、证据、核实过的规格。；**移除旧通道前必须先证明新通道对等承载**（外观与行为 parity 实证）——先删后证同罪（2026-10-11 事故：演示级 LC 模板在复刻设计未移植前接管 shop/产品/分类三页型，业主当场发现与线上完全不同）
- 生产写入走 SSH（`ssh hostinger-de-linker`，WP-CLI 在 `/usr/local/bin/wp`），先备份、后读回，按改动分层（业主 2026-10-18，#305）：**代码部署**＝部署自带的数据库快照（流到本机，主机不留文件）＋原子切换保留上一版代码（`rollback-deploy`）；**数据写入**（导入、批量修改、迁移、删表）前做完整备份（增量）；完整备份另每周一次。备份只存本机，不占服务器空间（主机上只留原子切换所需的上一版代码，约 28 MB）。密钥、令牌永不进仓库。

## 6. 研究与核实

外部事实只走 Apify（令牌来自环境 `APIFY_TOKEN` / `~/.config/terravolt-builder/apify.env`，永不写入文件）。Apify 坏了就修，不绕开。
能看、能试、能查的先做再说；只问业主只有业主知道的事。
代码、注释、文档、旧 ADR 里的数字与规则都不是事实；追到业主裁定、行业证据或 Woo 原生能力三者之一，追不到就改。

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`gh` CLI); the engineering skills read and write there. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles (needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` at the root, ADRs under `docs/adr/`. See `docs/agents/domain.md`.
