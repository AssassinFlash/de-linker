# 德语全面体检（票 #255，地图 #220）

日期：2026-10-17。对象：线上 https://de-linker.com 的德语面，只读。
裁定基准：AGENTS.md §2 2026-10-17"切到德语时一切都是德语专属——地址、标题、文案"；§3 用词（Sie 体、不说 Warenkorb / Artikel（文章）/ Katalog）；§2 2026-10-05（Produkt / Modell / Serie）。

## 结论

**能用，但不完整。** 设计的骨架是对的：Polylang 管语言与孪生，`linker-i18n` 管德语 URL 段与同 slug，界面字符串走 `.po/.mo` 与 JSON。实测下来，德语界面字符串、Sie 体、数字与货币格式、表单报错、注册流程、配置器、Genie 回答都是德语，页头语言切换在 55 个英文页上都落到对应的德语孪生页。

业主"感觉不对"是有原因的，问题集中在三处，都不是个别字符串的毛病：

1. **链接不跟语言走。** 德语产品页的"Produkt anfragen"把客户送到英文联系页；德语法律页互相链到英文法律页；页脚语言切换在每一页都失效；分类面包屑的"STARTSEITE"回英文首页。根因是插件代码到处手写 `home_url( '/contact/' )`、`home_url( '/' )`。仓库里已经有统一入口 `PageUrls::translated()`，但没有强制使用。另外 Polylang 只给主题模板里的 `home_url()` 加语言前缀，插件里调用的不加。
2. **德语内容是一次性迁移的副本，之后没人维护。** 自动翻译在线上从未运行（#253）；德语正文里的链接改写（`LinkLocalizer`）只在翻译任务里执行，任务不跑，德语博客里的旧英文链接就一直留着。
3. **"与线上像素一致"的复刻规则把旧站的德语缺陷原样搬了过来。** 代码注释明写：分类面包屑"德语页也印英文分类名，因为线上就是这样"（`ProductShortcodes.php` 129–137 行）；德语博客模板把日期格式写死为英文 `M j, Y`。2026-10-17 的裁定要求德语专属，这些缺陷要进变更台账，不再受像素门约束。

按严重度共 **23 项：高 5、中 11、低 7**。另外复核了 4 项已知问题，均仍然存在。

## 方法

- 从德语 sitemap（`/sitemaps.xml` → post/page/product/product_cat 四个子图）取出 151 个德语地址（25 页、10 文 + 博客索引、104 商品、10 分类）。全部 151 页用服务端 HTML 扫描禁用词、英文残留与 Sie 体。
- 59 个代表页（全部页面、文章、分类，5 个品牌 9 个商品，搜索、404、注册、找回密码、博客分类）用 Playwright Chromium 在 **1440 与 390** 下各渲染一次（locale de-DE），采集可见文本、aria-label/placeholder/title/alt、`<title>`、meta description、canonical/hreflang、指向非 `/de/` 的站内链接，以及数字、日期、货币格式。
- 语言切换：另取 55 个英文页，检查页头与页脚的"Deutsch"链接，并实际点击页头和页脚的"Englisch"各一次。
- 交互（全部只读）：访客看 Lösungsentwurf、点"Produkt anfragen"、看 Proforma 请求页；配置器首屏点空的"System berechnen"（只在客户端校验）；联系、登录、注册表单点空提交。为看服务端报错，登录与注册各发了一次空提交：空表单建不出账号，也不发信。没有完成任何注册，没有发送任何表单或询盘。
- Genie：/de/genie/ 上两个德语问题，产品页 dock 上一个（点"Genie fragen"会自动发出预填句，所以 dock 实际发了 2 条）。之前一轮脚本中途停下，已经发出 2 条，Genie 共收到 6 条消息。
- 代码只读：`plugins/linker-commerce/includes/Mail/`、`Registration/Emails/`、`linker-i18n/includes/`，以及三个插件的 `.po/.mo/.json` 覆盖率（逐条比较 .po 与 .mo，结果一致）。
- 生产只读一次（SSH + WP-CLI `eval`/`language list`），确认翻译密钥状态和已装语言包。没有任何写操作。

截图在 `screens/`。红框和黄色标签是审计脚本画上去的，标签里是该链接的 `href`。`text-*.txt` 是 `<head>` 与重定向这类截图拍不到的证据。

## 已知项复核（仍然成立，不重复立票）

| 已知项 | 复核结果 | 证据 |
|---|---|---|
| #253 德语自动翻译从未运行 | 成立。生产 `wp eval` 读 `getenv("DEEPSEEK_API_KEY")` → `key:unset`（WP-CLI 进程；PHP-FPM 进程同样读环境变量，与票内取证一致） | 本文"方法"一节 |
| #254 `/de/warenkorb/`、`/de/mein-konto/register/`（标题同登录页）、`/de/faq-download/` | 成立，三个地址仍在 sitemap 中返回 200；`/de/loesungsentwurf/`、`/de/mein-konto/registrieren/` 仍是 404。另有扩展项，见 M7、M11 | `screens/known-254-register-1440.jpg`、`screens/text-m7-account-titles.txt` |
| #229 德语页头在 1440 折叠成汉堡 | 成立。1440 下德语页头只有 Logo、搜索、Lösungsentwurf、账户、EN/DE、"Menü öffnen"；展开后的菜单内容是德语 | `screens/known-229-header-hamburger-1440.jpg`、`screens/known-229-mobile-menu-open-390.jpg` |
| hreflang、canonical、html lang | 成立。59 页全部 `lang="de-DE"`、`og:locale=de_DE`，canonical 指向自身；只有 register 与 lost-password 的 canonical 指向 `/de/mein-konto/`（Woo 端点的正常行为） | — |

## 发现：高（5）

### H1 德语产品页"Produkt anfragen"跳到英文联系页
- **页面**：全部 104 个德语产品页，例如 `/de/produkt/saj-b2-10-0-hv1/`（1440 与 390 都是这样）。
- **问题**：按钮的 href 是 `https://de-linker.com/contact/?intent=product…`。客户点击后进入英文联系页（"Let's work on what comes next."）。这个页面表单里隐藏的 `lang` 是 `en`，所以联系回执邮件（`Contact/Emails/ReceiptEmail`，按表单语言发）也会是英文。
- **证据**：`screens/h1-pdp-anfragen-button-1440.jpg`、`screens/h1-pdp-anfragen-button-390.jpg`、`screens/h1-pdp-anfragen-landing-1440.jpg`
- **根因**：`plugins/linker-commerce/includes/Storefront/ProductView.php` 358 行 `home_url( '/contact/' )`。
- **修法**：改用 `PageUrls::translated( 'contact' )`；`Contact/Handler.php` 130/134 行与 `Form.php` 314 行的兜底地址同样处理。
- **票**：新（与 #246"询盘对所有人开放、两扇门一份记录"相邻，实现时一起做）。

### H2 页脚语言切换在每一页都失效
- **页面**：所有页面的页脚"Sprache: Englisch | Deutsch"。
- **问题**：德语页上"Englisch"的 href 是 `/de/`，从 `/de/kontakt/` 点进去落在德语首页，不是 `/contact/`。英文页上"Deutsch"统一指向 `/de/`（德语首页），不是对应的孪生页。页头的切换是对的（55/55 落到孪生页）。
- **证据**：`screens/h2-footer-lang-de-page-1440.jpg`、`screens/h2-footer-lang-de-page-390.jpg`、`screens/h2-footer-lang-en-page-1440.jpg`、`screens/h2-footer-englisch-click-landing-1440.jpg`、`screens/text-h2-language-switch-targets.txt`
- **根因**：页脚 partial 里的语言链接是静态 href（服务端 HTML 就是 `<a data-lnk-flang="en" href="/de/">`），没有走页头使用的 Polylang 翻译 URL。
- **修法**：页脚语言段改用和页头同一来源（`pll_the_languages` / `pll_translation_url`），英德两份 partial 一起改。
- **票**：新（#229 只管页头）。

### H3 德语法律页互相链到英文法律页
- **页面**：`/de/impressum/`、`/de/datenschutz/`、`/de/verkaufsbedingungen/`、`/de/rueckgabe-erstattung/`。
- **问题**：右栏"Rechtliche Dokumente"的四个链接都指向 `/imprint/`、`/privacy-policy/`、`/terms-of-sale/`、`/refund-returns/`。德语客户在法律文本之间跳转会进入英文版本。
- **证据**：`screens/h3-legal-links-impressum-1440.jpg`、`screens/h3-legal-links-datenschutz-390.jpg`
- **修法**：德语法律页正文里的链接改成德语孪生页地址（数据修复），并加上 H2/S1 里说的渲染期链接本地化兜底。
- **票**：新。

### H4 `/de/produkte/` 的标题和 meta description 是英文
- **页面**：`/de/produkte/`（德语产品总览，也就是商城页）。
- **问题**：`<title>Browse Inverters, Batteries and Systems | Linker</title>`，description 也是英文原文，和英文页逐字相同。会出现在浏览器标签和德语搜索结果里。
- **证据**：`screens/text-h4-head-de-produkte.txt`
- **修法**：给德语商城页写 SEOPress 标题和描述（德语独立撰写，走文案评审），并查明为什么 Woo 商城页在德语下读到英文页的 meta。推测原因是 SEOPress 按 `wc_get_page_id('shop')` 取值，没有经过语言映射，需要在实例上核实。
- **票**：#254（每个德语页面有自己的德语标题）的扩展。

### H5 分类面包屑：英文分类名，"STARTSEITE"回英文首页
- **页面**：10 个德语产品分类（1440 与 390）、`/de/produkte/`；比较页的"Startseite"也回到 `/`。
- **问题**：面包屑显示 `STARTSEITE / PRODUKTE / COMMERCIAL STORAGE / ALL-IN-ONE SYSTEMS`，其他分类分别是 `HOME STORAGE`、`INVERTERS`、`BACKUP POWER` 等，H1 却是德语"All-in-One-Systeme"。"STARTSEITE"链接到 `https://de-linker.com/`。这是德语分类页顶部最显眼的一行。
- **证据**：`screens/h5-category-breadcrumb-1440.jpg`、`screens/h5-category-breadcrumb-390.jpg`、`screens/known-229-mobile-menu-open-390.jpg`（390 下可见"STARTSEITE / PRODUKTE / INVERTERS"）
- **根因**：`ProductShortcodes.php` 138 行 `home_url( '/' )`（Polylang 不给插件调用加前缀）；分类名由 `category_crumb_name()` 故意取英文名。注释写明"线上德语归档也印 INVERTERS"，即为了像素一致复制了旧站缺陷。
- **修法**：首页链接改用 `Languages::home_url( 'de' )` 或 `pll_home_url()`，分类名用当前语言词项名；把这一项作为"德语专属"变更记入变更台账，豁免像素门。
- **票**：新。

## 发现：中（11）

### M1 博客：英文日期、英文作者名、英文分享标签、英文图片 alt
- **页面**：`/de/blog/`、`/de/category/*/`、`/de/?s=…`（日期）；10 篇德语文章（分享按钮、作者）；3 张图片的 alt（博客索引与文章）。
- **问题**：日期显示为"May 29, 2026"（德语应为"29.05.2026"，相关卡片已经是这个格式）；作者显示"Von de-linker Editorial Team"；分享按钮 `title="Share on Facebook / Twitter / Whatsapp / Telegram"`；alt 为"A three-phase smart meter, current transformers and an energy-management gateway"、"Solar inverter and battery storage system"、"A GoodWe battery and hybrid inverter mounted on the outside wall of a house"。
- **证据**：`screens/m1-blog-index-date-1440.jpg`、`screens/m1-blog-search-date-author-1440.jpg`、`screens/m1-blog-share-titles-1440.jpg`
- **根因**：`plugins/linker-commerce/content/livecanvas/de/blog_index.html` 79 行、`de/category_archive.html` 97 行、`de/search.html` 95 行写死 `date_format="M j, Y"`；分享按钮来自 LiveCanvas 的 `lc-sharing-buttons`，标题是插件里的英文硬编码，生产上也没有装 LiveCanvas 的德语语言包；作者名与 alt 是数据。
- **修法**：德语模板改为 `d.m.Y`；分享按钮改成模板里的自有标记（德语标题"Auf Facebook teilen"等）；作者显示名与媒体 alt 按语言维护（媒体不翻译时，德语页在模板里不输出英文 alt，或在德语孪生上写 alt）。
- **票**：新。

### M2 德语正文与模板里的链接指向英文页或 404
- **页面与链接**：
  - 4 篇德语文章的行动链接 → `/product-category/residential-storage/res-accessories/`、`…/res-batteries/`（旧英文地址，301 到英文分类）：`/de/fernueberwachung-nach-installation/`、`/de/gateway-zaehler-cloud-ueberwachung-datenebene/`、`/de/innen-vs-aussen-akku-planung/`、`/de/installateur-checkliste-wechselrichter-akku/`。
  - `/de/danke/` → `/blog/`。
  - `/de/category/system-design/` 的"Unsere Produkte ansehen" → `/product/`（**404**），写死在 `content/livecanvas/de/category_archive.html` 142 行。
  - 比较页面包屑"Startseite" → `/`。
- **证据**：`screens/m2-blog-cta-english-category-1440.jpg`、`screens/m2-danke-blog-link-1440.jpg`、`screens/m2-category-archive-product-404-1440.jpg`
- **根因**：`LinkLocalizer` 只在翻译任务写入德语版时改写链接（见 S1）；德语 LC 模板里的链接是手写的。
- **修法**：数据层修掉这些链接；模板里的 `/product/` 改成 `/de/produkte/`；加 CI 检查：德语模板里每个站内 href 必须以 `/de/` 开头。
- **票**：新（与 #253 相关）。

### M3 禁用词："Artikel"（文章）、"Katalog"、购物用语
- **页面与字样**：
  - 博客 UI（索引、搜索、10 篇文章）："Artikel lesen"、"Alle Artikel anzeigen"、"Verwandte Artikel"、"Artikelkontext"、"Artikelautor"、"Artikeldetails"、"Artikel suchen"、"Neueste Artikel"、"Machen Sie aus Ihren Artikelnotizen ein Projektangebot."；搜索无结果时显示"Keine passenden Artikel gefunden."。
  - 至少 16 个产品页的运费句："…für einen lieferfähigen Artikel … Fracht für mehrere Artikel…"（`linker-commerce` .po）。
  - "Katalog"：`/de/loesung/`"…ein Angebot über den Katalog hinaus braucht"；文档标题"Chint DTSU666 Katalog (EN)"。
  - 购物用语：比较页"Weiter einkaufen"；`/de/datenschutz/`"Dieser Shop verwendet…"。
- **证据**：`screens/m3-blog-artikel-wording-1440.jpg`、`screens/m3-compare-weiter-einkaufen-1440.jpg`
- **修法**：博客用"Beitrag / Beiträge"；运费句用"ein lieferbares Produkt / mehrere Produkte"；"über das Sortiment hinaus"；文档标题用"Produktkatalog"之外的词（"Datenblatt"或"Produktübersicht"）；"Weiter zu den Produkten"；"Diese Website verwendet…"。法律页改字需要业主确认。全部走文案评审。
- **票**：新。

### M4 "Series"没有译成"Serie"
- **页面**：产品页 kicker"ET SERIES"（例 `/de/produkt/goodwe-gw80k-et-g10/`，正文里却写"ET-Serie"）；分类卡片和 aria-label 里的"ET Series"、"ESA Series"（7 个分类页）；产品系列属性"EcoFlow OCEAN 2 (Three-Phase)"；文档标题"GoodWe ET 50–100 kW Solution Manual (EN)"。
- **证据**：`screens/m4-pdp-et-series-1440.jpg`、`screens/m4-category-series-card-1440.jpg`
- **修法**：系列名的数据源（属性词项或 meta）按语言提供"ET-Serie"；德语里的"Three-Phase"改为"dreiphasig"。
- **票**：新（AGENTS §2 2026-10-05：Produkt / Modell / Serie）。

### M5 Genie：回答是德语 Sie 体，周边有英文与 du 体
- **好的部分**：/de/genie/ 两问都用德语 Sie 体回答，价格问题转到 sales@de-linker.com，首条消息声明是 AI 系统。
- **问题**：
  1. 回答里夹英文术语"Pairing"、"Pairing-Unterlagen"，引用的是英文 PDF（`…Configuration_Instructions_V1.0_en.pdf`），没有说明语言。
  2. dock 底部链接"FAQ & Downloads"是英文。`linker-tools` 的 JSON 里这条译文与原文相同，而站内其他地方都叫"FAQ & Dokumente"。
  3. 产品页"Genie fragen"和"Neues System / erweitern / ersetzen"三个提示卡，会以客户的口吻发出一段 du 体指令："Nenne mir … und sag mir …"、"Frage danach immer nur nach der nächsten fehlenden Angabe … und prüfe …"。这段话在对话里显示为客户自己的气泡，等于把提示词暴露给客户。
  4. （不属于 i18n，顺带记录）回答"9 nutzbare und 10 nominelle Kapazität"缺单位 kWh。
- **证据**：`screens/m5-genie-page-answers-1440.jpg`、`screens/m5-genie-dock-390.jpg`
- **修法**：德语术语表加"Pairing → Kombination / freigegebene Kombination"并在系统提示里强制；引用文档时附上语言（DE/EN）；"FAQ & Dokumente"；提示卡改成客户会说的 Sie 体短问句，指令部分放进页面上下文（#234 读当前页面）。
- **票**：1、2、3 新；3 与 #234 相关；4 交给 Genie 线（#233）。

### M6 两个德语营销页的 meta description 是正文自动截取
- **页面**：`/de/fuer-installateur/`（description 以"LINKER DEUTSCHLAND · SOLAR- & SPEICHERLÖSUNGEN FÜR INSTALLATEURE DEUTSCHER BETRIEB Partnerportal sales@de-linker.com …"开头）、`/de/loesung/gewerbespeicher/`（"GEWERBLICHER SPEICHER Schlanker …"）。对应英文页有手写的 description。
- **证据**：`screens/text-m6-meta-description-dumps.txt`
- **修法**：给德语孪生页写 SEOPress description（德语独立撰写）。顺带一提：商品页的 description 英德都为空，不是 i18n 问题。
- **票**：#254 扩展。

### M7 找回密码页也和登录页同标题、同描述
- **页面**：`/de/mein-konto/`、`/de/mein-konto/register/`、`/de/mein-konto/lost-password/` 三页都是"Partnerkonto: Anmelden oder Registrieren | Linker"，description 也相同。#254 只点名了 register。
- **证据**：`screens/text-m7-account-titles.txt`
- **修法**：三个端点各写一个标题（例如"Passwort zurücksetzen | Linker"）。
- **票**：#254 扩展。

### M8 Polylang 301 会删掉查询参数里 URL 的 `/de/`
- **问题**：`/de/kontakt/?intent=product&source=https://de-linker.com/de/produkt/saj-b2-10-0-hv1/` 被 301 到 `…source=https://de-linker.com/produkt/saj-b2-10-0-hv1/`（`x-redirect-by: Polylang`），这个地址是 404。团队从德语联系留言或询盘看到的"来源页"链接因此失效。`?s=` 搜索参数也有同样现象（`x-redirect-by: WordPress`）。
- **证据**：`screens/text-m8-redirect-strips-de.txt`
- **修法**：来源 URL 不用完整地址做查询参数，改为只传 `source_id`（已经有）。或者先在本地复现 Polylang 的 canonical 重定向为何改写查询值，再决定是否加过滤器。
- **票**：新。

### M9 从后台触发的德语客户邮件，正文德语、链接英文（读代码推断，待夹具证实）
- **问题**：`linker-commerce` 的客户邮件（Approved / Restricted / Rejected、Inquiry received、Proforma issued、Contact receipt）用 `Mail/LocaleSwitch` 切语言。它只调用 `switch_to_locale()` 和插件的 .mo，不切 Polylang 的当前语言（`PLL()->curlang`）。邮件语言本身选得对：注册时 `Fields.php` 170 行把 `locale` 写入用户，询盘写 `_linker_locale`，联系表单带 `lang`。但当业主在 wp-admin 点"通过"或开 Proforma 时，邮件模板里的 `wc_get_page_permalink( 'shop' )`、`wc_get_page_permalink( 'myaccount' )`、`$order->get_view_order_url()` 按当前 Polylang 语言解析，结果是 `/products/`、`/my-account/`、`/my-account/view-order/…`；`Account/DocumentDownload.php` 51/66 行直接用 `home_url( '/' )`。客户收到的是德语正文里的英文页链接。
- **证据**：代码：`Mail/LocaleSwitch.php` 42–59 行，`templates/emails/linker-approval-approved.php` 26/28 行，`Proforma/Emails/ProformaIssuedEmail.php` 117–118 行。对照：`linker-i18n/includes/Languages.php` 231–243 行的 `enter()` 会同时切 curlang、locale 和 Polylang 字符串。
- **修法**：所有客户邮件和 Proforma PDF 改用同一个 `enter()/leave()`（见 S3）。补夹具：后台审批与后台开 Proforma 两种触发上下文下，Outbox 中德语邮件的链接都以 `/de/` 开头（守测试邮件纪律，只做队列断言）。
- **票**：新。

### M10 FAQ & Dokumente：误译"im Bestand"、英文出处、多语文档标成 EN
- **页面**：`/de/faq-download/`。
- **问题**：
  1. 页头"Datenblätter, Handbücher und Handelsregeln zu den Geräten im Bestand"和计数"404 im Bestand"里的 "im Bestand" 意思是"有库存"。英文原文是"on file"（已存档）。库存在本站是有裁定的概念，这里会误导客户。
  2. FAQ 答案的出处标签是英文，例如"GoodWe ESA Series 5–30 kW user manual (EN, V1.5), S. 80"、"SAJ H2 10-30K user manual, German and English (covers the H2-10K-T3)"。
  3. 多语手册（标题写着"(EN, DE, FR, IT, ES, NL, SV)"）的语言徽标只写"EN Englisch"。
  4. 德语页显示 160 份文档，英文页 159 份（差 1 份，原因待查）。
- **证据**：`screens/m10-faq-im-bestand-1440.jpg`、`screens/m10-faq-english-citations-1440.jpg`
- **修法**：用"hinterlegt"（"404 hinterlegt"、"…zu den hinterlegten Geräten"）；出处标签使用文档的德语标题；多语文档徽标显示"Mehrsprachig"（产品页已经有这个值）；核对文档数差异。
- **票**：新。

### M11 德语地址里还有英文：#254 之外的部分
- **问题**：
  - 56/104 个德语产品地址带英文词，例如 `…-three-phase-hybrid-inverter`、`…-battery-module-…`、`…-ev-charger`、`…-residential-energy-manager`、`…-data-collector-wifi-lan-bluetooth`、`…-2026-flagship`。这是 `SameSlug` 有意保持与英文同 slug 的结果（spec 9）。
  - `/de/compare-products/`（在德语 sitemap 里）。
  - 博客分类 `/de/category/system-design/` 等：分类基 `category` 和 5 个分类 slug 都是英文（spec 9 修订 2026-10-14 有意同 slug）。
  - Woo 账户端点 `register`、`lost-password`，以及邮件链接里会出现的 `view-order`、`edit-account` 等。
- **证据**：`screens/text-m12-de-product-slugs-english.txt`
- **修法**：#254 的"全站德语地址逐条扫一遍"按这份清单执行。产品 slug 是否翻译要先定：翻译的话旧地址全部 301，sitemap 与 hreflang 同步，并且推翻 spec 9 的同 slug 设计；不翻译则需要业主确认这是例外。
- **票**：#254 扩展（产品 slug 需要决定）。

## 发现：低（7）

| # | 页面 | 问题 | 证据 | 修法 | 票 |
|---|---|---|---|---|---|
| L1 | 联系、登录、注册表单 | 必填项的浏览器气泡跟随浏览器界面语言，不跟页面语言：德语页在英文浏览器里显示"Please fill out this field."。配置器有自己的德语提示（"Geben Sie eine deutsche Postleitzahl mit fünf Ziffern ein."），是对的 | `screens/l1-contact-html5-bubble-1440.jpg`、`screens/ok-configurator-validation-1440.jpg` | 表单用 `setCustomValidity()` 输出页面语言的提示，或 `novalidate` 加服务端德语报错（服务端报错已经是德语：`screens/ok-register-server-errors-1440.jpg`） | 新 |
| L2 | 产品正文 | 数字格式不一致："9000 Wp"、"max. 1000 V" 与同页"1.000 V" | — | 产品文案数据统一用德语千分位 | 新（数据） |
| L3 | `linker-commerce` .po | 54 条未译，全部是 Abilities / REST schema 的标签和描述（例："Compare products"、"Get a product"），客户看不到；源码里有 1 条团队健康检查邮件没有进 .po（团队邮件按裁定用英文） | — | 补译或标为不译 | 新 |
| L4 | 产品页、产品列表 | "Artikelnr. / Artikelnummer" 显示 SKU。§2 2026-10-05 对客户只说 Produkt / Modell / Serie | — | 需要定：保留"Artikelnummer"（德语商务通用词）还是改为"Bestellnummer"或不显示 | 新（决策） |
| L5 | 产品页"Dokumente"、FAQ 文档列表 | PDF 链接没有 `hreflang` 属性，只有文字标签（DE / EN / Mehrsprachig） | — | 在链接上加 `hreflang` | 新 |
| L6 | 全站 | 没有 cookie / 同意横幅（Datenschutz 写明只用技术必要的 cookie），所以没有需要翻译的横幅 | — | 无 | — |
| L7 | `linker-tools` 语言文件 | 没有 `.pot`。JSON（257 条 JS 字符串，覆盖完整）和 `.po`（28 条 PHP 字符串）分开维护，JSON 不是从 .po 生成的。目前没有缺失，但违背 §4"`wp i18n make-json`"的约定，下次加字符串容易漏 | — | 生成 `.pot`，JS 字符串也进 .po，JSON 由 `wp i18n make-json` 生成 | 新 |

（另记：英文 `/proforma-request/` 的标题是"Checkout | Linker"，属于英文面问题，不在本票范围。）

## 正常的部分（实测通过）

- 界面字符串：页头、页脚、菜单（390 展开后）、产品页、分类、筛选、商城、Lösungsentwurf（访客空态）、Proforma 请求页（访客）、配置器首屏、404、账户三页、Genie 外壳，都是德语。151 页全扫，du 体 0 处，"nicht …, sondern" 0 处，Warenkorb 字样 0 处（只出现在地址里，属 #254）。截图：`screens/ok-draft-guest-390.jpg`、`screens/ok-proforma-guest-390.jpg`、`screens/ok-configurator-1440.jpg`、`screens/ok-404-1440.jpg`、`screens/known-229-mobile-menu-open-1440.jpg`。
- 格式：德语页 `14,90 €`、`65,00 € bis 200,00 €`、`98,1 %`、`1.000 V`，英文页 `€65.00`、`1,000 V`，按语言分开。法律页日期为"29. September 2026"。
- 报错：登录"Benutzername oder Passwort ist nicht korrekt."；注册空提交"Fehler: Firmenname ist ein Pflichtfeld. …"；国家列表是德语。
- 产品页的文档列表按语言标注（DE / EN / Mehrsprachig）。
- 页头语言切换：55/55 落到孪生页（含搜索 `?s=`、博客分类、注册端点）。
- 邮件语言的选择：注册时写入用户 locale；询盘记录 `_linker_locale`（结账表单带 `lang`）；联系表单带 `lang`。三个插件的 `.po` 与 `.mo` 逐条一致，客户邮件模板的字符串都有德语译文。

## 结构性弱点

- **S1 德语是迁移出来的副本，维护它的流程没有在跑。** 英文改了，德语不跟（#253）；正文链接的德语化（`LinkLocalizer`）只在翻译时执行，所以德语正文里的英文链接（H3、M2）不会被修好。只要翻译任务停着，问题就会累积。
- **S2 "当前语言下某个页面的地址"没有唯一入口。** `PageUrls::translated()` 是 #184 为此建的，但插件里还有约 20 处手写 `home_url( '/contact/' )`、`home_url( '/de/genie/' )`、`home_url( '/' )`。Polylang 只给主题模板里的 `home_url()` 加语言前缀，插件调用拿到的是英文地址（H1、H5、M9 都是这个原因）。页脚与页头的语言切换也是两套实现（H2）。
- **S3 邮件切语言有两套机制。** `linker-commerce` 的 `LocaleSwitch`（只切 locale）和 `linker-i18n` 的 `Languages::enter()`（切 locale + Polylang + 字符串）并存，订单语言也存了两份 meta（`_linker_locale` 与 `_linker_i18n_language`）。`EmailPolicy` 关掉了除重置密码外的全部 Woo 客户邮件，所以 `linker-i18n/Woo/Orders` 的客户邮件切换实际不会生效，真正发出去的邮件用的是较弱的那套（M9）。
- **S4 像素门与 10-17 裁定冲突。** 复刻规则让代码有意保留了旧站的德语缺陷（H5 的注释、M1 的日期格式、分享按钮）。没有"德语专属修复"的变更台账，修复会被像素门判为 FAIL。
- **S5 德语文本分散在四处，没有统一检查。** `.po`（PHP）、手工维护的 JSON（JS，L7）、每语言的 LC 模板（`content/livecanvas/de/*.html`，含写死的链接与日期格式）、数据库内容（页面、文章、SEOPress meta、词项名、媒体 alt）。禁用词、英文残留、链接语言没有 CI 检查，只能靠人眼发现。
- **S6 URL 策略和新裁定矛盾。** spec 9 的同 slug 设计让一半德语产品地址和全部博客分类地址保留英文（M11），需要明确决定。

## 我会怎么改（按收益排序）

1. **建一个语言感知的 URL 入口，并用 CI 强制。** `PageUrls` 扩展出 `home()` 与 `page( slug )`，H1、H5、M9 和约 20 处手写地址全部迁过去；在 CI 里加 grep/phpcs 检查，禁止客户面代码出现 `home_url( '/…' )` 字面量。页脚语言段改用 Polylang 翻译 URL。
2. **渲染期链接兜底。** 德语请求下，对正文与 LC 输出中的站内英文链接做一次 `LinkLocalizer::url()` 映射（有缓存）。这样即使翻译任务停摆，链接也是德语的。改写时的写入逻辑保留，渲染期只负责兜底。
3. **邮件语言统一用 `Languages::enter()/leave()`**（locale + Polylang + 字符串），删掉 `LocaleSwitch` 和重复的订单语言 meta。按"前台请求 / 后台操作 / 定时任务"三种触发上下文各写一个 Outbox 夹具，断言德语邮件的主题、正文和链接。
4. **德语检查进 CI。** 扫 `.po`、JSON、`content/livecanvas/de/*.html`：禁用词（Warenkorb、Artikel 作"文章"、Katalog、Shop / einkaufen、du 体）；模板 href 必须是 `/de/` 或站外；日期格式必须是德语格式。上线后用本次的扫描方法（sitemap → 全页扫描）每周跑一次。
5. **"德语专属"变更台账。** H5、M1 等德语修复登记为裁定过的变更，豁免像素门，并请业主过目。
6. 先把 #253（翻译真正运行、带审阅）和 #254（地址与标题，含 M7、M11 与产品 slug 决策）做完。本报告的新项可以并成 3 张实现票：**链接与语言入口**（H1、H2、H3、H5、M2、M8、M9）、**德语文案与数据**（H4、M1、M3、M4、M5-1/2、M6、M10）、**检查与工具链**（L1、L5、L7 与第 4 条）。
