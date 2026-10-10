# de-linker · 工作规则

这里没有硬规则。每一条都可以被证据推翻；推翻时写明是哪条证据，并改这份文件。
本文件只写做事的依据，不写历史、不写流程仪式。详细证据在 `docs/research/`。

## 1. 这是什么

de-linker.com：Linker Technology GmbH 的 B2B 光伏储能询盘网站，WordPress + WooCommerce，英德同等。
客户是安装商、EPC、经销商。链路只有一条：产品分类与产品 → 询盘（以 Proforma 呈现）→ 之后全部线下。
网站没有订单、付款、发货、采购、分组、审批、发票和任何后续处理的概念。

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
  - 营销十页文案冻结；工具相关文案全部重写。所有 FAQ 均为编造，问题角度保留，答案逐产品由模型独立生成并对抗评审。
  - 全拆：旧仓库的自定义代码一行不以代码形式留下；带走的只有内容与数据、裁定、证据、核实过的规格。
  - 不买任何新的付费插件；现有许可（LiveCanvas、SEOPress PRO）可继续用。
  - 全部在本地建成后一次性更新原站，同域名同 URL；期间业主不改线上。

业主只回答事实（产品数据、价格、承诺、厂商怎么说）。产品范围、工具存废、架构、措辞由本线按竞品映射与证据决定；决定只因新证据改变，改变时写明证据。

## 3. 用词

产品、产品分类；不说目录（catalogue）、文章（article）、篮子（basket/cart）。
客户的工作清单：Solution draft / Lösungsentwurf。方案内的清单：Bill of materials / Stückliste。
询盘四状态：Inquiry received / Anfrage eingegangen · Proforma invoice issued / Proformarechnung ausgestellt · Completed / Abgeschlossen · Cancelled / Storniert。
德语用 Sie 体（locale `de_DE_formal`）；禁止 "不是…而是…"、三连排比等 AI 句式；英德永远同步交付。

## 4. 技术选型（按复刻与适用定，证据见 docs/research/2026-10-09/framework-choice.md）

- 前端：React + TypeScript，用 WordPress 自带的 React；`@wordpress/scripts` 构建；`@wordpress/i18n` + `wp i18n make-json`。每个插件一个 npm 包，三类工具是同一包的入口。
- PHP：Composer + PSR-4 命名空间，一类一文件；PHPUnit 9.6（WP_Mock）；PHPStan level 8；WPCS 3 + woocommerce-sniffs；Composer 锁 PHP 8.3。
- Python 服务（VPS，Python 3.12）：uv + pyproject；FastAPI + Pydantic AI；ruff、mypy、pytest。
- 多语言：Polylang 免费版做基座 + 我们自己的窄插件（同 slug、URL 段翻译、保存即翻译、REST lang、Woo 最小同步）。
- 商品数据：Woo 商品是唯一手工源；兼容合同与约 3 条工程覆盖层是数据；引擎读生成的 feed。
- 知识库：我们自己托管的 PDF 按页检索（Docling 解析 → SQLite FTS5 + sqlite-vec → 混合检索）；模型只能引用检索块 ID，数字由服务端填入。
- 邮件：Hostinger `mail()`（10 封/分钟、100 封/24 小时，四站共用），一封加 Bcc，重试覆盖 24 小时，生产环境禁止发信测试。
- 模块化由框架约定定义（一个组件/类/模块一个文件、按功能分目录、每个模块有测试），不以行数为指标。每个数字与阈值必须有来源注释。

## 5. 交付

- 管线：本地 → 评审站 → 线上。线上不是任何功能第一次被看到的地方。
- 每张票一个新会话；先 `just up` 拉起本地栈。分支 → PR → CI 绿 → 本线 review → 合并。执行会话用 Opus。
- 验收三件套，缺一不交付：Spec + Standards 双评审（全量 diff）；改动所在层的真实夹具测试；Computer Use 视觉验收（1440 与 390，EN 与 DE，逐状态截图，以设计稿、需求与交互预期为基准）。
- 本轮发现的问题本轮修，不开 follow-up，不留 TODO。
- 生产写入走 SSH（`ssh hostinger-de-linker`，WP-CLI 在 `/usr/local/bin/wp`），每次部署先备份、后读回。密钥、令牌永不进仓库。

## 6. 研究与核实

外部事实只走 Apify（令牌来自环境 `APIFY_TOKEN` / `~/.config/terravolt-builder/apify.env`，永不写入文件）。Apify 坏了就修，不绕开。
能看、能试、能查的先做再说；只问业主只有业主知道的事。
代码、注释、文档、旧 ADR 里的数字与规则都不是事实；追到业主裁定、行业证据或 Woo 原生能力三者之一，追不到就改。
