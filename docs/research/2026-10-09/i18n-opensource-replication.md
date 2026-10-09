# 用开源组件复刻 WPML / Polylang-for-WooCommerce：de-linker.com 自有 i18n 插件设计（研究报告）

日期：2026-10-09 · 性质：只读研究（无任何生产写入） · 作者：research agent

方法与证据等级
- 外部事实全部经 Apify 获取（2026-10-09）：`apify/google-search-scraper`（58 个 EN/DE 查询，用于发现）、`apify/website-content-crawler`（文档/HTML 页）、`apify/rag-web-browser`（raw.githubusercontent.com 源码，raw-http 模式）、`thenetaji/http-request-scraper`（wordpress.org 插件 API 与 GitHub REST JSON）。Token 只在进程内读取，未打印、未落盘。注：主账号该 HTTP actor 的 50 条免费额度已用完，后续 3 批用 `APIFY_API_TOKEN_ALT`；`apify/cheerio-scraper` 需要控制台 full-permission 授权（未授予，未使用）。
- 本地证据：交付链尖 `refs/landed/chain-tip` = `f007a9dd`（linker-i18n 0.5.78，PHP 8,896 行）；`docs/audit/2026-08-29-i18n-architecture-audit.md`；`docs/adr/0031-…`；LiveCanvas 4.9.3 源码（本地副本 `~/Documents/de-linker-worktrees/erp-sim-site/wp-content/plugins/livecanvas/`）；线上只读探针（`/de-sitemap.xml`、Store API 响应头）。
- 标注：**OBSERVED** = 源码/页面原文直接可见；**INFERRED** = 由证据推理、需在 staging 验证。来源编号见文末 §12。

---

## 0. 结论（TL;DR）

1. **基座选 Polylang 免费版（GPLv3，3.8.10，2026-09-28 发布，90 万+ 安装，WP 7.1 测试通过）**[S1][S3]。它免费提供我们最难自己写、且最容易出错的那一层：语言对象、帖子/分类“孪生”与翻译分组、`/de/` 目录式 URL + 默认语言不带前缀、前台全量查询按语言过滤、hreflang、语言切换器、静态首页/博客页按语言、菜单/小工具、字符串翻译表、**WPML API 兼容层**（LiveCanvas 正是通过 `wpml_object_id` 取页眉/页脚，见 §7.1）、语言与设置的 REST（`pll/v1/languages|settings`，3.7 起免费）[S9][S11][S34]。
2. **Pro 与 Polylang for WooCommerce（PLLWC）里我们必须自己复刻的只有 4+1 块**：共享 slug、翻译 URL 基段（product→produkt 等）、保存即机翻建孪生（用我们现有 DeepSeek 管线替代 DeepL/“复制内容”）、REST 列表按 `lang` 过滤（Store API/我们自己的端点）；外加一个**窄版 Woo 桥**（简单商品、无在线支付，详见 §3.2、§6.2）。PLLWC 十年 changelog 里的大量边角（可变商品、订阅、预订、多域购物车、CSV 语言列……）对本站不适用，不复刻 [S15]。
3. **商品“一条记录”原则**：德语商品是**真实的 Woo `product` 对象**（Polylang 孪生），只承载可翻译文案；**SKU、库存数量只存在于英文主记录**，价格/库存状态/可见性等对孪生是**单向投影**（只由一个同步函数写入，人和 ERP 永远只写英文）；购物车/订单行**一律规范化到英文 product_id**，德语页面上只换展示名与链接。这样 ERP 按 SKU 推送（ADR-0031 的 `POST tvb2b/v1/stock`）、库存镜像、`wc_get_product_id_by_sku()` 都保持唯一性 [L3][S23]。
4. **不选**：Bogo（维护中但无 WPML API、无术语对象翻译、无 Woo，自写量更大）、WP Multilang / qTranslate-XT（单记录+语言标记，免费版保不住现有德语页面 slug、与 LiveCanvas 直接编辑 post_content 冲突、qTranslate-XT 仅 GitHub 且只测到 WP 6.8.3）、无基座自研（等于重写 Polylang 的查询过滤/链接/后台层，估 3–4 千行新基础设施）。WordPress 核心多语言仍是“Phase 4 长期路线”，7.2（2026-12-10）不含 [S29][S30][S31][S32]。
5. **代码量**：新插件常驻约 **5,700 行 PHP**（其中约 2,900 行是现有 translator/document/product/store/vocabulary 原样保留，约 2,350 行新胶水，jobs 精简到约 450 行），另有约 400 行一次性迁移代码；对比现有 8,896 行。被删除的正是“整页 DOM/字符串替换”那一套：`chrome.php`(895)、`render.php`(799)、`dates.php`(249)、`router`(567)、`slugs`(260)、`class-lang`(414) 等 [L1]。

---

## 1. 需求 → 机制 → 证据（总表）

| # | 需求 | 机制（新设计） | 关键证据 |
|---|---|---|---|
| R1 | EN/DE 对等；英文先写；保存即 AI 生成德语（DeepSeek、术语表、禁用词、型号校验） | 英文保存 → 队列 → `Translator` 生成/更新**德语孪生**（复用 `translator.php`/`document.php`/`product.php`/`store.php`/`vocabulary.php`） | 现有函数清单 [L1]；Polylang 免费版不含机翻（Pro=DeepL）[S4] |
| R2 | `/de/` 子目录 | Polylang “language set from directory” + “hide default language” | [S2][S11 links-directory.php] |
| R3 | 104 个 `/de/produkt/<英文 slug>/` 与页面 URL 原样不变 | 自写 **共享 slug**（同一语言内唯一）+ **翻译基段**（product→produkt、product-category→produkt-kategorie、商店归档 products→produkte） | 免费版：帖子 `-2`、术语 `-fr` 后缀；共享/翻译 slug 均为 Pro [S5][S6]；线上 150 个 DE URL 盘点 [L5] |
| R4 | 德语商品是真实 Woo 对象，或经 REST/Store API 带 `lang` 完整暴露 | Polylang 商品孪生 + 自写 REST 语言过滤（Store API、wc/v3、我们自己的命名空间） | 免费版 REST：`lang` 只设当前语言、不过滤列表 [S8][S11 rest-request.php]；Store API 用 `new WP_Query` 无专用参数过滤器 [S23] |
| R5 | hreflang / canonical / sitemap / 404 正确 | Polylang 自动 hreflang（`pll_rel_hreflang_attributes` 加 x-default）；canonical 由 SEOPress 按孪生 permalink 输出；SEOPress sitemap 含两种语言；DE 关闭 404 猜测；旧 `/de/<英文 slug>/` 301 | [S12][S33]；现有 404 猜测关闭逻辑 [L2] |
| R6 | 库存/价格/SKU/ERP 只写一条记录（ERP 按 SKU 推） | SKU 与库存数量只在 EN；孪生的商业字段是单向投影；购物车/订单规范化到 EN | `get_product_id_by_sku()` `LIMIT 1`（重复 SKU 即歧义）；`update_product_stock()` 直接 SQL 不触发 meta 钩子 [S23]；ADR-0031 [L3] |
| R7 | 店员在标准 WP 编辑器审校德语 | 德语孪生就是普通 post/product：LC 编辑器、Woo 商品页、b2b-core 商品编辑器（`product-editor.php` 写 `_tv_legacy_acf_json`）原样可用；人工改动回写词典（STATUS_HUMAN） | Polylang 语言 metabox/列表列 [S2]；`Store::STATUS_HUMAN` [L1] |
| R8 | 插件 UI 字符串走 gettext（.po/.mo + `wp i18n make-json`） | 删 chrome map；b2b-core 已有 1,065 处 gettext + de_DE .po/.mo；React 应用用 `@wordpress/i18n` + `wp_set_script_translations` + `make-json --use-map` | [S35]；计数 [L7] |
| R9 | LiveCanvas 营销页（post_content 内 HTML）与 SEOPress meta 翻译 | 页/页眉页脚/动态模板都建孪生；SEOPress 单篇 meta 写在孪生上；全局选项走 Polylang 字符串翻译 | LC 4.9.3：页眉页脚 `apply_filters('wpml_object_id', …)`、模板 `lc_modify_template_id` [S34]；Polylang 免费版实现 `wpml_object_id` [S11]；SEOPress 指南 [S33] |
| R10 | 不做整页 DOM/字符串替换 | 删除输出缓冲 `strtr`、日期正则、链接扫描；德语存成真实内容，链接在**写入时**本地化 | 现有 buffer 设计 [L2 §1.4] |

---

## 2. Polylang 免费版（问题 1）

### 2.1 维护与基本面（OBSERVED）
- 3.8.10（2026-09-28，含反序列化与 XSS 安全修复）；3.8.1→3.8.10 在 2026-03 至 2026-09 间每月发布；GitHub `polylang/polylang` 最近 push 2026-10-09，3.9-beta2 于 2026-09-28；许可 **GPLv3 or later**；要求 WP ≥ 6.8（readme）、PHP ≥ 7.4；Tested up to 7.1 [S1][S2][S3]。
- 数据模型：语言是 `language` 分类法的术语（术语语言用 `term_language`），翻译分组是 `post_translations` / `term_translations` 术语，其 description 保存 `lang => id` 映射 [S11 query.php、crud-posts.php:569、wpml-api.php:222-227][S36]。

### 2.2 免费版提供什么（OBSERVED，[S2][S4][S11]）
- 翻译：文章、页面、媒体、分类、标签、自定义文章类型与分类法（非 public 的类型用 `pll_get_post_types`/`pll_get_taxonomies` 过滤器加入）[S12]。
- URL：目录（`/de/`）、子域或独立域名；默认语言可隐藏前缀。
- 同步选项（免费）：Taxonomies、Custom fields、Comment/Ping status、Sticky、Published date、Post format、Page parent、Page template、Page order、Featured image [S11 settings-sync.php:107-117]。注意：custom fields 同步**排除受保护（下划线开头）meta**，通过 `pll_copy_post_metas` 才能加入；且同步是**双向**的 [S11 sync-post-metas.php][S13]。
- 切换器：区块（3.8 起免费）、经典小工具、导航菜单项；`pll_the_languages()` [S2]。
- hreflang：自动输出；x-default 用 `pll_rel_hreflang_attributes` 一行加 [S12][S11 frontend-links.php]。
- 字符串翻译表（站点标题、日期格式、小工具、`wpml-config.xml` 注册的选项；代码里写死的字符串仍走 .po/.mo）[S12]。
- REST：`pll/v1/languages`（3.7 起免费，CRUD）与 `pll/v1/settings`（免费）[S9]；**`?lang=` 在 REST 请求中只设置当前语言**（`rest_pre_dispatch`，触发 `pll_language_defined`），**不过滤列表、不输出 `lang/translations` 字段**；创建文章时 `?lang=de` 能把新文章设为德语 [S8][S11 rest-request.php、Capabilities/Create/Post.php]。
- WPML API 兼容（`wpml_object_id` → `icl_object_id` 等）[S11 wpml-api.php:69]。
- 缓存兼容：缓存页无 Set-Cookie 时用 JS 写 `pll_language`；开启“浏览器语言检测+隐藏默认语言”时首页 `DONOTCACHEPAGE` [S11 cache-compat.php]。

### 2.3 Pro 独占（免费版只有“设置预览”）（OBSERVED）
共享 slug、翻译 URL slug（CPT/分类法基段、作者基段等）、创建翻译时复制内容、同步文章（内容级）、停用语言、XLIFF、PO 导入导出、ACF Pro 集成、REST `lang` 过滤与 `translations` 字段、站点编辑器、DeepL 机翻、按语言权限、WP-CLI（3.8 Pro）[S4][S5][S6][S7][S10][S38]。免费源码中 `src/modules/share-slug/load.php` 与 `translate-slugs/load.php` 仅注册 `PLL_Settings_Preview_*`（升级提示），没有实现 [S11]。

### 2.4 官方对 WooCommerce 的立场与“没有 PLLWC 会坏什么”
- 官方 FAQ 原意：要让两者协同，需要付费的 Polylang for WooCommerce [S3]。PLLWC 2.2.6（2026-10-05），99€/年 [S4][S15]。
- 商品作为 CPT 可以被免费版翻译，但以下缺口需要 PLLWC 或自写（OBSERVED 来源于 PLLWC 文档/changelog 与 Woo 源码，INFERRED 部分已注明）：
  1. **SKU 唯一性**：Woo 拒绝重复 SKU（`wc_product_has_unique_sku` 过滤器）；`get_product_id_by_sku()` 只取 `LIMIT 1` [S23]。PLLWC/Hyyan 让译本共享 SKU 并改写唯一性判断 [S13][S19]——这会让 ERP 按 SKU 查询出现两条。
  2. **库存**：`update_product_stock()` 直接 SQL 更新 `_stock` 并触发 `woocommerce_updated_product_stock`，Polylang 的 meta 同步（挂在 `added/updated_post_meta`）永远看不到 [S23][S11]；PLLWC/Hyyan 用 `woocommerce_product_set_stock` 等 Woo 动作同步 [S19]。
  3. **Woo 页面**：`wc_get_page_id()` 走 `woocommerce_get_{page}_page_id`，不按语言就会把 /de/ 用户送到英文购物车/结账页 [S23][S19 Pages.php]。
  4. **购物车/订单**：切换语言时购物车商品名、链接不变；订单与邮件语言需要记录与切换 [S15][S19 Cart.php、Order.php]。
  5. **商品元数据**：价格、税、尺寸、图片/图库、上下架可见性、属性、关联商品不会自动在译本间保持一致（免费同步不含受保护 meta）[S13][S11]。
  6. **属性**：全局属性术语与属性名（存于 `wc_attribute_taxonomies`）需要翻译 [S13]。
  7. **区块/Store API**：PLLWC changelog 多次修复“store blocks 未翻译”“cart/checkout 区块语言”“lookup table”等 [S15]。
  8. **REST**：PLLWC 的 Woo REST 支持本身也要求 Pro [S2][S16]。
  9. **必须先给存量内容分配语言**，否则商品在前台不显示 [S13]（迁移顺序约束，见 §8）。

---

## 3. GPL/开源桥接与程序化接口（问题 2）

### 3.1 hyyan/woo-poly-integration（OBSERVED）
- wordpress.org：**2026-10-05 关闭，“临时关闭，等待完整审查”**（与我们的审计一致）；评论区报告 PHP 8 致命错误 [S17]。
- GitHub：已归档（archived=true），**MIT** 许可，最后提交 2021-12-29，描述 “Looking for maintainers!” [S18]。
- 实现（`readme.txt` 功能清单 + 源码）：页面翻译、端点翻译、商品（分类/标签/属性/运费类/元数据同步/可变商品/图库）、订单翻译、库存同步、购物车同步、优惠券同步、邮件、报表按语言过滤/合并 [S18]。关键做法：
  - 元数据同步清单：`_sku`、`_manage_stock/_stock/_stock_status/_backorders`、价格五项、尺寸重量、`_product_attributes`、税、可下载等；通过 `pll_copy_post_metas` 注入 [S19 Product/Meta.php:632-734]。
  - SKU：覆盖 `wc_product_has_unique_sku`，“只有同语言重复才算重复” [S19 Meta.php:898-958]。
  - 库存：挂 `woocommerce_product_set_stock` / `woocommerce_variation_set_stock`，对译本调用 `wc_update_product_stock(…,'set',true)` + `wc_update_product_stock_status()`，并临时解绑防递归 [S19 Product/Stock.php]。
  - 购物车：`woocommerce_add_to_cart_product_id`（已有任一译本则复用）、`woocommerce_cart_item_product` 换成当前语言译本对象、`woocommerce_cart_item_permalink` [S19 Cart.php]——只覆盖经典购物车模板。
  - 页面：`woocommerce_get_%s_page_id` / `option_woocommerce_%s_page_id` → `pll_get_post()` [S19 Pages.php:42-43]。
- 2025–2026 的 fork（OBSERVED，GitHub compare API）：`integrITsolutions`（领先 12 个提交，全部集中在 2026-05-09/10，“gauntlet round A–I”式批量修补，0 star）、`nordhauser`（2026-06-06 新建，自称“maintained fork for PHP 8.2/WC 10.x HPOS/Polylang 3.x”，当天 3 个提交，MIT）、`lpmcsn`（+2，NumberFormatter 修复）、`okapteinis/fifle/smtturkan-droid`（0 差异）。另有独立小项目 `510AS/Polylang-WooCommerce-Data-Sync`、`proVject/Polylang-WooCommerce-Lite` v0.1.0、`BytesPulse-OE/…Product-Sync`（3 star）[S18]。**判断**：没有一个具备“持续维护”证据（单作者、单日爆发、0–3 star），不能作为依赖；但 MIT/GPL 代码可在我们 GPL 插件中参考或复用。
- 另一个 wp.org 插件 `woocommerce-polylang-integration` 于 2022-03-15 应作者请求永久关闭 [S39]。

### 3.2 PLLWC 功能清单 → 我们的处置

| PLLWC 能力 [S13][S14][S15] | 本站处置 | 理由 |
|---|---|---|
| 翻译简单/可变/组合商品 | **只做简单商品** | 2026-09-05 快照 229 个商品全部 simple [L6] |
| 分类/标签/全局属性术语翻译 | `product_cat` 与 `pa_phase`、`pa_battery-voltage`、`pa_application` 做术语孪生；`pa_brand`、`pa_model` 保持语言中立；无 tag | 属性值含 “Single-phase / High Voltage / Commercial & Industrial” 等需德语，品牌型号是专有名词 [L6] |
| 元数据同步（SKU、价格、税、尺寸、运费类、图片、属性、关联商品） | **EN→DE 单向投影**（不含 SKU 与库存数量） | 满足“一条记录可写”；关联商品为空 [L6] |
| 购买后库存跨语言同步 | **不需要**：订单行永远是 EN；只投影 `stock_status` | `manage_stock` 全为 false，库存语义是状态 [L6][L3] |
| SKU 共享 | **不共享**：孪生无 SKU；展示与 JSON-LD 经 view 过滤器读 EN | 保持 `get_product_id_by_sku()` 唯一 [S23] |
| 购物车跨语言同步 | **规范化到 EN + 德语展示** | Store API 有 `woocommerce_store_api_add_to_cart_data`（WC 8.8+）[S23][S24] |
| Woo 页面翻译（商店/购物车/结账/我的账户） | 做（页面 ID 映射 + 商店归档基段） | |
| 端点 slug 翻译 | 不做（保留英文端点） | 现有 DE URL 清单中无端点 URL [L5] |
| 订单语言、按语言发邮件、主题/标题翻译 | 做（移植现有 `_linker_i18n_locale` 与邮件 locale 切换） | 现有实现 [L2 §1.7] |
| 一键复制商品连同译本、CSV 语言列、优惠券限制映射、报表合并、订阅/预订/捆绑兼容、多域购物车 | 不做 | 不适用或因 EN 规范化而自动成立 |
| Woo REST（需 Pro） | 自写：wc/v3 默认只列 EN（显式 `lang` 例外） | 我们的工具/ERP 会遍历商品 |
| 区块/Store API 语言 | 自写 Store API 语言过滤；若用 Woo 区块再加 apiFetch 中间件附 `lang` | [S15] |

### 3.3 程序化创建翻译（OBSERVED）
- 公共函数（免费版 `src/api.php`）：`pll_set_post_language()`(458)、`pll_save_post_translations()`(491)、`pll_set_term_language()`(475)、`pll_save_term_translations()`(512)、`pll_get_post()`(205)、`pll_get_term()`(229)、`pll_get_post_translations()`(592)、`pll_register_string()`(273)、`pll__()`(288)、`pll_translate_string()`(372)、`pll_is_translated_post_type()`(402) [S11]。
- REST：免费版创建时 `?lang=de` 可设语言；**关联翻译需要自建端点**调用 `pll_save_post_translations()`（rinblog 在 3.8.9/WP 7.1 实测并给出几十行实现）[S8]。语言与设置可直接用 `pll/v1/languages|settings`（免费）[S9]。
- WP-CLI：`wp pll …` 只在 Pro 3.8；社区包 `diggy/polylang-cli` 2020 年归档 [S10][S18]。
- 已知坑：3.8.9 程序化插入根分类后再 `pll_set_term_language()` 会留下“脱钩的 term_translations 分组”；实测可行的规避是在 `create_term` 优先级 0 的回调里先设语言 [S36]。

---

## 4. 备选基座与“无基座”（问题 3）

| 维度 | Polylang 免费 | Bogo | WP Multilang | qTranslate-XT | 无基座（自研孪生） |
|---|---|---|---|---|---|
| 维护（2026） | 3.8.10 / 2026-09-28；90 万+；仓库当天有 push [S1] | 3.9.3 / 2026-08-18；1 万+；GitHub 活跃 [S29] | 2.4.34 / 2026-10-07；1 万+；作者已变为 Magazine3；原 GitHub 已归档 [S30] | 不在 wp.org；3.16.1 / 2025-10-07；末次提交 2025-11-11；只测到 WP 6.8.3；287 open issues [S31] | — |
| 模型 | 每语言一篇，分类法关联 | 每语言一篇，`_locale`/`_original_post` meta 关联 [S29] | 单记录 + 语言标记 | 单记录 + 语言标记 | 自定 |
| `/de/` + 默认语言无前缀 | 是 | 是（`bogo_lang_slug` 可过滤）[S29] | 是 | 是 | 自写 |
| 不同语言不同 slug（`/de/kontakt/` vs `/contact/`） | 是（天然） | 是（天然） | **否，URL slug 翻译是付费版** [S30] | 有 slugs 模块 | 自写 |
| 共享 slug（商品） | 自写 | 页面路径按 locale 解析 `bogo_get_page_by_path()` [S29] | 天然 | 天然 | 自写 |
| 术语作为对象翻译 | 是 | 否（INFERRED：Bogo 有 Terms Translation 屏与 `pomo.php`，术语名按 .mo 翻译，未逐行核对）| 是 | 是 | 自写 |
| WPML API（LiveCanvas 页眉页脚） | 是 [S11] | 否（源码无 wpml）[S29] | 未证实 | 未证实 | 自写 |
| Woo 支持 | 无（PLLWC 付费） | 无 | 免费内置 | 内置模块 | 自写 |
| 与 LiveCanvas 直接写 post_content 的兼容 | 好（每语言独立 post_content） | 好 | **INFERRED 风险**：LC 整体保存 post_content 会覆盖标记格式 | 同左 | 好 |
| 自写量 | 约 2.35k 行胶水 | 约 3k+（术语、LC 映射、Woo 全部自写） | 不满足 R3/R9 | 不满足（维护/兼容） | 约 5–6k 新基础设施 |

- 单记录插件的历史教训：qTranslate-X 于 2021-08-31 因安全问题被 wp.org 关闭，站点内容被锁死在标记格式中 [S39]。
- 其他：Sublanguage（600 安装，只测到 6.6）、Falang（Woo 需付费版）、MultilingualPress 免费版（2025-01 停更，只测到 5.2）、Lingotek（2026-07-31 因安全关闭）、TranslatePress/GTranslate/Linguise（输出层替换，违反 R10）、WCML（需 WPML）均排除 [S39]。
- 核心：官方路线图把多语言列为 Phase 4 长期目标；2026 年聚焦 Phase 3 协作与 7.x 发布，7.2 计划 2026-12-10 [S32]。

**结论**：Polylang 免费版能把“自研量”压到最低，且它正是 LiveCanvas 已经对接的 WPML API 提供者。无基座方案需要重写 Polylang 已被 90 万站点验证的查询过滤、链接过滤、后台 UI、静态首页按语言等层，风险与工作量都更大。

---

## 5. 共享 slug 与翻译基段（问题 4）

### 5.1 免费版现状（OBSERVED）
- 帖子/页面：WordPress 对第二篇同名 slug 自动加 `-2`；术语：免费版生成 `…-fr` 形式；共享 slug 只在 Pro，且“停用 Pro 后，共享同一 slug 的条目只会显示其中一个” [S5]。
- 免费版创建新文章时的语言来源顺序：`new_lang` → `$_REQUEST['lang']` → REST `lang` → 父页面语言 → 后台偏好语言 → 前台当前语言 → 默认语言 [S11 Create/Post.php]。**因此程序化插入时，`wp_unique_post_slug` 运行那一刻孪生还没有德语身份**，按“同语言内唯一”判断会误判为与英文冲突 → `-2`。

### 5.2 本站必须保持的清单（线上 2026-10-09，OBSERVED [L5]）
- `/de-sitemap.xml` 共 150 个 URL：104 个商品全部是 `/de/produkt/<slug>/` ⇄ `/product/<同一 slug>/`；10 个分类 `/de/produkt-kategorie/…`（其中 `ems-monitoring` 两种语言同 slug，其余德语 slug 来自 `data/shelf-slugs-de.json`）；页面/文章 35 个，其中 **3 个同 slug**：`/de/compare-products/`、`/de/faq-download/`、`/de/blog/`；其余为德语 slug（来自 `linker_i18n_slug_map`）。

### 5.3 自写模块设计
**SharedSlugs（约 250 行；参考 grappler/polylang-slug GPLv2+ 与 dbrabyn/polylang-slug-toolkit GPLv2+）[S20][S21]**
- 保存侧：`wp_unique_post_slug` 过滤——只与**同语言**同类型（层级类型再加同父级）比较。术语侧要覆盖免费版自己的后缀逻辑（`PLL_Term_Slug`，产生 `…-de`）[S11 term-slug.php][S5]，只对 `ems-monitoring` 这 1 个同名分类生效；注意 Polylang 2026-10-02 刚为 WP 7.2 的 `wp_unique_term_slug()` 变更调整测试 [S11 commits]，此处需随 7.2 复验。
- 两步插入（解决 §5.1 时序）：先以临时 slug 插入孪生 → `pll_set_post_language()` → `pll_save_post_translations()` → `wp_update_post(['post_name'=>目标 slug])`（此时语言已确定，唯一性判断正确）。
- 查询侧：
  - 商品（非层级 CPT）：前台 Polylang 已对所有查询加语言 tax_query（`PLL_Frontend::parse_query` → `PLL_Query::filter_query`）[S11]，`name=slug` 自然命中德语孪生，无需额外代码。
  - 页面（层级）：WP 用 `get_page_by_path()` 先按路径找 ID，**语言盲**；在 `request`/`parse_request` 阶段对 `pagename` 按当前语言解析（自写 SQL 加 `term_relationships` 语言 join，或沿用 grappler 的 query 过滤思路）。grappler 通过改写核心 SQL 字符串实现，跨 WP 版本脆弱——我们只对 3 个同 slug 页面需要，采用“按语言解析 pagename → page_id”更稳。
  - 已知的语言盲调用点必须改：Store API `ProductsBySlug`（`get_page_by_path($slug, OBJECT, 'product')`）[S23]；b2b-core `bulk-order.php:328`、`legacy-redirects.php:699`、`compare-products.php:49` [L4]。

**TranslatedBases（约 250 行；参考 KLicheR（2016，product→produit 示例）与 dbrabyn 的 archive 基段实现）[S21][S22]**
- 规则：`^de/produkt/([^/]+)/?$` → `product=$1&lang=de`；`^de/produkt-kategorie/(.+?)/?$`（含分页）；`^de/produkte/?$`（商店归档，含分页）。用 Polylang 的 `pll_modify_rewrite_rule` 阻止它再给这些规则套 `(de)/` 前缀，规则注入在 Polylang 之后 [S11 links-directory.php][S21]。
- 链接：`post_type_link`（商品）、`term_link`（product_cat）、`post_type_archive_link`（商店）按语言输出；**同时过滤 `pll_translation_url`**，否则切换器与 hreflang 会只替换语言段、给出错误基段（dbrabyn README 明确指出）[S21]。
- 旧基段 301：`/de/product/<slug>/` → `/de/produkt/<slug>/`（Polylang 原规则仍能解析旧路径）。
- 自动 flush：以“规则集 + 插件版本”指纹触发一次 `flush_rewrite_rules()`。

---

## 6. Store API 与语言（问题 5）

### 6.1 事实（OBSERVED）
- Polylang 免费版在 REST 中读取 `lang` 设置 `curlang` 并触发 `pll_language_defined`（因此 gettext 会切德语），但不加查询过滤 [S11 rest-request.php][S8]。
- Store API 商品集合：`ProductQuery::get_results()` 直接 `new \WP_Query($args)`，只临时加 `posts_clauses`，没有专用 args 过滤器 → 用 `parse_query`/`pre_get_posts` 挂钩并调用 `PLL_Query::filter_query(PLL()->curlang)` 即可复用 Polylang 自己的过滤逻辑 [S23][S11 query.php]。
- 按 slug 取单品：`ProductsBySlug` → `get_page_by_path()`（语言盲）[S23]。
- 加购：`CartAddItem` 先过 `woocommerce_store_api_add_to_cart_data`（可改 `id`，WC 8.8.0 起），然后 `wc_get_product($request['id'])` [S23][S24]。
- 购物车项：`name` = `$product->get_title()`（过 `woocommerce_product_title`），`permalink` 过 `woocommerce_cart_item_permalink`；不经过 `woocommerce_cart_item_product`（所以 Hyyan 的经典模板做法对 Store API 无效）[S23]。
- 下单：经典与 Store API 结账都调用 `WC_Checkout::create_order_line_items()`，行项目设置后触发 `woocommerce_checkout_create_order_line_item`，可在此写入德语名称 [S23]。
- 线上现状：`GET /wp-json/wc/store/v1/products?per_page=1&lang=de` 返回 `content-language: en`——现插件只认 `X-Linker-Locale` 头/`locale` 参数，`lang` 无效；两次请求与 DE 商品页均**未见 `x-litespeed-cache` 头** [L5]。

### 6.2 设计（RestLanguage 约 150 行 + Cart 约 150 行）
1. **契约**：所有语言相关 GET 一律用查询参数 `?lang=en|de`（进入 URL，可被缓存安全区分）；React 应用由页面 `data-locale` 生成；退役 `X-Linker-Locale` 头（29 处引用/14 个文件需迁移 [L7]）。
2. 查询过滤：REST 请求中、`curlang` 已设且查询类型为已翻译类型（product、page、post）时，`parse_query` 调 `PLL_Query::filter_query()`；Store API 的 `sku=` 参数在 DE 下先按 EN 查 ID 再映射孪生。
3. `ProductsBySlug` 与我们自己的按 slug 端点：结果语言 ≠ 请求语言时替换为 `pll_get_post($id,$lang)`（或改用 `?slug=x&lang=de` 走集合查询）。
4. **后台/工具 REST 默认 EN**：`wc/v3/products`、`wp/v2` 列表在未带 `lang` 时只返回 EN（`lang=all` 显式取全部）——否则我们的物料同步、校验脚本、ERP 模拟器会看到 212 个商品。
5. **购物车规范化**：`woocommerce_store_api_add_to_cart_data` 与经典 `woocommerce_add_to_cart_product_id` 把孪生 ID 换成 EN ID；`is_purchasable`、价格、库存都在 EN 上判断。
6. **德语展示**：DE 上下文中，`woocommerce_product_title`、`woocommerce_cart_item_name`、`woocommerce_cart_item_permalink`、`woocommerce_order_item_permalink` 映射到孪生；`woocommerce_checkout_create_order_line_item` 把德语名写入订单行（`product_id` 仍是 EN，`wc_reduce_stock_levels()` 用 `$item->get_product()` 因而扣 EN）[S23]。
7. 若使用 Woo Cart/Checkout 区块：加 20 行 apiFetch 中间件附 `lang`（PLLWC changelog 显示这是常见问题源）[S15]。

### 6.3 LiteSpeed 坑（OBSERVED + INFERRED）
- LSCWP 设置 “Cache REST API” **默认开启**；缓存 vary 只认 cookie（`_lscache_vary*` 或配置的 Vary Cookies）和一个环境值，**不认任意请求头** → 以请求头传语言的 REST GET 一旦被缓存会串语言；必须把 `lang` 放进 URL [S26]。
- LSCWP 内置第三方集成只有 `wpml.cls.php`、`wcml.cls.php`（仅把 WPML 语言域名加入内部域名），**没有 Polylang 集成** [S27] → 依赖 Polylang 自己的 cache-compat（JS 写 cookie）。
- 浏览器语言检测会让首页不可缓存（Polylang issue #294；Polylang 在该场景主动 `DONOTCACHEPAGE`）[S28][S11] → 保持关闭（Google 也按 EN 抓取）。
- 好消息（INFERRED）：孪生是独立 post，LSCWP 按帖子保存自动清理对应 URL/归档；审计指出的“翻译变更不触发清缓存”（`linker_i18n_translation_changed` 无触发点）在新模型中结构性消失 [L2 §3.6]。
- 购物车/结账端点按会话与 nonce，不应被页缓存（WC 文档：Store API 数据反映当前客户、写操作需 nonce）[S25]。

---

## 7. LiveCanvas 与 SEOPress（R9 细节）

### 7.1 LiveCanvas 4.9.3（OBSERVED，本地副本源码）[S34]
- 页眉/页脚：`get_post_field('post_content', apply_filters('wpml_object_id', lc_get_partial_postid('is_header', $variant), 'lc_partial'))`（`livecanvas-plugin-index.php:819/836`）。Polylang 免费版把 `wpml_object_id` 映射到 `icl_object_id`/`pll_get_post` [S11] → **只要 `lc_partial` 是可翻译类型，LC 自动取德语页眉/页脚孪生**。
- `lc_get_partial_postid()` = 取带 `is_header`/`is_footer` meta 的**最新**一篇（`orderby ID DESC`，`:888-898`）。孪生若复制了该 meta，在没有当前语言的上下文里可能取到德语那篇（INFERRED 风险，需在编辑器/REST/邮件渲染场景验证）；在前台有 `curlang` 时 Polylang 会给这个 `get_posts` 加语言过滤。
- 动态模板：`lc_get_template_id()` 用 `get_posts(meta_key=模板名)`，并提供 `lc_modify_template_id` 过滤器（`templating.php:115`）→ 用该过滤器显式映射到德语模板孪生，更确定。
- 两个类型都是 `public => false`（`:1392/:1423`）→ 需 `pll_get_post_types` 加入 [S12]。LC 官方文档目录没有多语言章节 [S34]。
- 现有 LC 页面的私有 meta（LC 启用标志、页面设置等）需在建孪生时复制（Polylang 免费同步不含受保护 meta）[S11]。

### 7.2 SEOPress
- 单篇：标题/描述/OG 都是 post meta → 写在孪生上，由翻译任务生成；canonical 即孪生 permalink（新模型下自然正确）。
- 全局：SEOPress 文档说明 Polylang 下在 “Languages → Strings translations” 过滤 `wp-seopress` 即可翻译全局选项 [S33]。
- sitemap：SEOPress 称会把每种语言的译文收录进 XML sitemap [S33]；wp.org 有“Polylang 免费版下 sitemap 内缺 hreflang”的报告（head 内 hreflang 正常）[S33]——head hreflang 已足够，sitemap 内 hreflang 不作为验收门槛；现有自建 `/de-sitemap.xml` 退役。

---

## 8. 迁移方案（问题 6）

### 8.1 输入盘点
- 内容：27 页、10 文、106 商品（任务给定）；线上 DE sitemap 150 URL [L5]；LC 页眉/页脚 partial（17/18）+ 7 个动态模板 [L1 jobs.php:1029-1035]。
- 德语来源：`_linker_de_title/_content/_excerpt/_acf_json/_status/_source_sha/_updated_at`；词典表 `wp_linker_string`（含 `STATUS_HUMAN=2`）；页面 slug 映射 `linker_i18n_slug_map/_rmap`；基段 `data/slug-bases-de.json`；分类 slug `data/shelf-slugs-de.json`；分类名 `data/taxonomy-de.json` [L1][L2]。
- 新鲜度：`_linker_de_source_sha` 与 `Translator::content_sha()` 不一致的条目先重译再迁移（或接受该单元英文回退）。

### 8.2 步骤（幂等、可重复、分批）
形态：插件内一个 `manage_options` 的临时 REST 路由（`linker-i18n/v1/migrate?dry_run=1&batch=20`）+ 本地 Python 驱动（`tools/`），因为主机写入“超时但实际成功”，必须靠幂等重试；全部以 `pll_get_post($en,'de')` 判定“已存在则更新、否则创建”。迁移完成后删除该路由与代码。
0. **演练**：在本地 ERP 模拟站（已有 LC 4.9.3 与 Woo）全量演练；生产先做 `tools/backend_snapshot.py` 备份；关闭现有翻译任务开关。
1. 安装 Polylang 免费版；用免费的 `pll/v1/languages` 建 `en`（`en_US`，默认）与 `de`；用 `pll/v1/settings` 设目录模式、隐藏默认语言、关浏览器检测、关媒体翻译、同步项只开 taxonomies / page parent / page template / menu order / featured image（**关 custom fields**，商业字段由我们单向投影）[S9][S11]。具体键名以该端点 GET 返回为准（INFERRED：未逐键核对，必要时在后台设置页一次性完成）。
2. 新插件先上线“配置模块”（`pll_get_post_types`：page、post、product、lc_partial、lc_dynamic_template；`pll_get_taxonomies`：category、product_cat、pa_phase、pa_battery-voltage、pa_application）。
3. **同一维护窗口内**把全部存量对象设为 `en`（官方：未分配语言的商品前台不显示）[S13]。
4. 建术语孪生：10 个 `product_cat`（德语名/slug 来自 shelf map；父级映射）、属性术语（Einphasig/Dreiphasig、Hochvolt/Niedervolt、Gewerbe & Industrie 等由翻译任务给出）；用 `create_term` 优先级 0 先设语言，规避 3.8.9 脱钩分组 [S36]。
5. 建帖子孪生（按依赖顺序：父页面 → 子页面；首页、博客页、Woo 页面；LC partial/模板；文章；商品）：两步插入定 slug（§5.3）→ 写德语标题/正文/摘要/SEOPress meta → 复制 LC 私有 meta → 商品写 `_tv_legacy_acf_json`（来自 `_linker_de_acf_json`）、`product_cat`/属性术语映射、商业投影（不写 `_sku`、不写 `_stock`）→ `pll_save_post_translations(['en'=>…, 'de'=>…])`。
6. 写入时本地化正文内链接：EN 内链 → `pll_get_post()` 后的 DE permalink（替代现行渲染期链接扫描）。
7. 静态首页/博客页语言映射由 Polylang 处理；Woo 页面 ID 映射由新模块处理。
8. 切换：启用 TranslatedBases/SharedSlugs → flush 规则 → 关闭旧 overlay 与输出缓冲 → 清 LSCache。
9. 验收（只测会改变决策的点）：150 个 DE URL 全部 200 且路径不变、对应 EN URL 不变；每页 hreflang 成对（含 x-default）；`/wc/store/v1/products?lang=de` 返回 106 个德语名称、价格/库存状态与 EN 一致；ERP 按 SKU 推一次状态 → EN 与 DE 同时变化；DE 加购→下单：订单行 `product_id`=EN、名称为德语、邮件德语；改一次 EN 正文 → DE 孪生在队列周期内更新且人工改过的单元保留。
10. 回滚：旧插件数据（`_linker_de_*`、词典、slug map）全程不删；回滚 = 先把 DE 孪生撤为草稿（否则停用 Polylang 后同 slug 冲突，官方原话“只会显示其中一个”）[S5] → 停用新模块与 Polylang → 恢复旧开关。

---

## 9. 自写代码估算（问题 7）

现状（链尖，PHP 8,896 行）[L1]：translator 1,448；linker-i18n.php 1,304；jobs 1,057；chrome 895；render 799；document 634；router 567；product 453；class-lang 414；store 301；slugs 260；dates 249；translation-events 130；cache 120；vocabulary 81；taxonomy 77；search 54；mu-loader 53。另有 runtime JS 380 行、CSS 175 行。

| 模块 | 作用 | 估算行数 | 依据 |
|---|---|---|---|
| 保留：Translator / Document / Product / Store / Vocabulary | 机翻、单元切分、校验、词典、禁用词、术语表、型号保护 | ~2,900（基本不动） | [L1] |
| jobs（精简） | 队列、断路器、cron 补扫；删掉 chrome 重建/SEO 串/商业串/公开就绪测量 | ~450 | [L1] |
| Bootstrap + Polylang Setup + `Linker_I18n_Lang` 门面 | 注册类型/分类法、配置断言、对 24 个文件的 69 处 `Linker_I18n_Lang::` 调用保持接口 | ~270 | [L7] |
| SharedSlugs | §5.3 | ~250 | grappler 333 行、dbrabyn 共享模块约 10 KB [S20][S21] |
| TranslatedBases + 旧基段/旧 slug 301 | §5.3 | ~330 | dbrabyn base 模块约 18 KB（仅 archive）[S21] |
| Twin Writer + 写入期链接本地化 | 建/更新孪生、字段映射、LC/SEOPress meta、术语映射 | ~420 | — |
| Woo：页面映射、商业投影、SKU 展示、购物车/订单、邮件 locale、属性标签 | §6.2 | ~560 | Hyyan 对应文件：Cart 9.8 KB、Stock 4.9 KB、Pages 6.1 KB、Order 4.4 KB [S19] |
| REST 语言 | §6.2 1–4 | ~150 | — |
| 人工审校 | 识别 DE 孪生的人工修改并按单元写回词典（STATUS_HUMAN）、状态列、待审列表、重译按钮 | ~250 | 复用 `Document::pair_text()/revise()` [L1] |
| SEO + 切换器 | x-default、DE 关闭 404 猜测、SEOPress 胶水、切换器短代码（`pll_the_languages(['raw'=>1])`） | ~140 | [S12] |
| 合计常驻 | | **~5,700** | 现有 8,896 → 约 -36% |
| 迁移（一次性，切换后删除） | §8 | ~400 | — |

插件外的必要连带改动（不是新功能，是迁移的直接后果）：
- b2b-core：`tv_b2b_product_commerce_state()`（`status.php:303`）入口规范化到 EN ID（Law 4：一条规则一个实现，孪生不得分叉）；库存镜像（`stock-mirror.php:346-349` 用 `set_stock_status+save`）与其“外部写入”监听要跳过非 EN 商品；3 处 `get_page_by_path` [L3][L4]；6 处直接读 `_linker_de_*` 的代码改读孪生 [L7]；`commerce-strings-en.json` 的 70 条字符串改为 b2b-core gettext。
- Advisor/React：`wc_get_product_id_by_sku()` 返回 EN ID（多处 [L7]），德语对话展示时经 `pll_get_post()` 取孪生；请求统一带 `lang`。
- 语言包：推荐 Polylang 的德语 locale 用 `de_DE_formal`（WooCommerce 在 translate.wordpress.org 有 German (Formal) 项目，编辑者已译 >11k 串 [S37]），从而用官方 Sie 体替代 `email-voice.php` 的覆盖表；我们自己的 .mo 相应以 `de_DE_formal` 命名。是否完整需在 staging 装包验证（INFERRED）。

---

## 10. 需复刻功能清单（汇总）

**A. 来自 Polylang Pro**
1. 共享 slug（商品 104、页面 3、分类 1；同语言内唯一 + 按语言解析）。
2. 翻译 URL 基段（product→produkt、product-category→produkt-kategorie、products→produkte）及其链接/切换器/hreflang 一致性与旧基段 301。
3. 保存即生成译文（替代“复制内容/DeepL”）：英文保存 → 德语孪生自动创建/更新，校验失败不发布、保留上一版。
4. REST `lang` 列表过滤与语言感知查找（Store API、wc/v3 默认 EN、我们的命名空间）。

**B. 来自 PLLWC（窄版）**
5. 商品/分类/属性术语孪生；属性标签走 gettext（`woocommerce_attribute_label`）。
6. Woo 页面 ID 映射与商店归档识别。
7. EN→DE 商业投影（价格、税、`stock_status`、可见性、尺寸、图片/图库、属性结构）；SKU 与库存数量只在 EN。
8. 购物车规范化到 EN + 德语展示；订单行德语名；订单语言与邮件语言。
9. Store API/区块语言；ERP/工具 REST 默认 EN。

**C. 保留自现有插件**
10. 翻译器、校验器、术语表（65 条）、禁用词、型号保护、词典（含人工批准状态）、断路器 [L1]。
11. 订单/用户 locale 记录与 Woo 邮件 locale 切换 [L2 §1.7]。
12. 退役 slug 与旧英文 slug 的 301 [L1 slugs `retired_de_target`]。

**D. 明确不复刻**：可变/组合商品、端点 slug 翻译、CSV 语言列、一键复制商品+译本、优惠券映射、报表合并、多域购物车、XLIFF/PO 导入导出（.po 用标准工具）、按语言权限、站点编辑器支持、媒体孪生（图片 alt 在内容里随译文、Woo 图片 alt 用 `wp_get_attachment_image_attributes` 按语言取值）。

---

## 11. 风险（逐条附证据）

1. **依赖 Polylang 免费版内部/钩子**（`PLL_Query`、`pll_modify_rewrite_rule`、`pll_translation_url`、`curlang`）——Polylang 月更且常含安全修复（3.8.8、3.8.10）[S2]，3.9 已在 beta、且刚为 WP 7.2 的术语 slug 变更做适配 [S11 commits]；缓解：固定版本、每次升级先在本地模拟站跑 §8.2-9 验收；我们的胶水只用文档化过滤器与公共函数为主。
2. **共享 slug 的语言盲调用**：`get_page_by_path()`（WP 页面解析、Store API `ProductsBySlug`、b2b-core 3 处）在同 slug 时返回任意一篇 [S23][L4]；若我们的 SharedSlugs 失效，官方明言只显示其中一个 [S5]；缓解：模块失效时 fail-closed（不发布同 slug 孪生）+ 改造已知调用点。
3. **程序化插入时序**：语言在 `save_post` 才确定，`wp_unique_post_slug` 更早运行 → `-2`；缓解：两步插入 [S11]。
4. **术语分组脱钩**（3.8.9，2026-09-15 报告）[S36]；缓解：`create_term` 优先级 0 设语言。
5. **免费 REST 不过滤列表** → 孪生出现在 wc/v3、wp/v2 列表，影响 ERP 模拟器、物料同步、校验脚本 [S8]；缓解：后台 REST 默认 EN。
6. **库存镜像互相干扰**：ADR-0031 说明镜像会把非自身写入视为“外部写入” [L3]；投影写孪生会触发同一钩子；缓解：镜像与其监听只处理 EN（语言判断一行）。
7. **一条记录原则被投影稀释**：孪生上存在派生副本；任何绕过 Woo 钩子的写入（直接 SQL）会造成漂移 [S23]；缓解：投影只由一个幂等函数写，除 EN 保存与库存钩子外，顺带挂在库存镜像已有的夜间 pass 上重投影一次（不新增监控）；孪生的商业字段在后台隐藏/只读，避免人工写入。
8. **Polylang 同步是双向的**：若误开 custom fields 同步，孪生上的改动会回写 EN [S13][S11]；缓解：只开 taxonomies 等结构项，商业字段走自有单向投影。
9. **LiveCanvas partial 选择**：按 meta 取“最新一篇”，无语言上下文时可能取到德语 partial [S34]；缓解：验证编辑器/REST/cron 渲染路径，必要时孪生不带 `is_header` 而完全依赖 `wpml_object_id` 映射。
10. **LiteSpeed**：REST 缓存默认开且不按请求头 vary [S26]；无 Polylang 集成 [S27]；浏览器检测使首页不可缓存 [S28]；缓解：`lang` 入 URL、关检测、依赖按帖清理。
11. **跨插件耦合**：`Linker_I18n_Lang::` 69 处/24 文件，`linker_i18n_*` 40 处/18 文件，`X-Linker-Locale` 29 处/14 文件，`_linker_de_*` 6 处/5 文件 [L7]；缓解：保留 `Linker_I18n_Lang` 公共接口（以 Polylang 实现），其余逐处迁移——这是有真实读者的兼容层，不是臆造。
12. **gettext 时序**：WP 6.7+ 文本域按需加载，REST 的语言在 `rest_pre_dispatch` 才确定；现有 mu-loader 正是为“文本域加载前定语言”而存在 [L2 §1.1]；Polylang 通过 `pll_language_defined` 重新加载被覆盖的文本域 [S11]——INFERRED，需在 staging 验证 REST 响应里的 b2b-core 字符串为德语。
13. **桥接插件不可依赖**：Hyyan 已关闭/归档，fork 无维护证据 [S17][S18]；我们只借鉴写法（MIT/GPL 可复用）。
14. **规模**：商品行 106→212、lookup 表与 sitemap 翻倍；后台列表需按语言筛选（Polylang 自带）——INFERRED 影响小。
15. **SEO 过渡**：URL 不变但 HTML 来源改变（孪生）；hreflang/canonical 改由 Polylang/SEOPress 输出；风险点是切换窗口内的缓存与 x-default；缓解：切换后全量清缓存并按 §8.2-9 抽验。

无需业主决策的事项：以上全部为技术与语言选择，按 CLAUDE.md 由我们决定。仅提示：现有“首次访问按浏览器语言 JS 跳转”属于 UX 行为，新方案建议取消（SEO/缓存更稳），如业主希望保留可用 JS 方式在不影响缓存的前提下恢复。

---

## 12. 来源（全部于 2026-10-09 经 Apify 获取，除标注“本地/线上”外）

- [S1] wordpress.org 插件 API JSON：`polylang`（3.8.10，last_updated 2026-09-28，active_installs 900000，tested 7.1.3，requires_php 7.4）— `https://api.wordpress.org/plugins/info/1.2/?action=plugin_information&request[slug]=polylang`（thenetaji/http-request-scraper）
- [S2] https://wordpress.org/plugins/polylang/ （功能分节与 changelog 3.8–3.8.10）（website-content-crawler）
- [S3] https://raw.githubusercontent.com/polylang/polylang/master/readme.txt （GPLv3+、Requires 6.8、FAQ“需要 Polylang for WooCommerce”）（http-request-scraper）
- [S4] https://polylang.pro/pricing/ （免费/Pro/PLLWC/商业包功能矩阵，99€/年）
- [S5] https://polylang.pro/documentation/support/guides/share-the-same-posts-or-terms-url-slugs-across-translations/
- [S6] https://polylang.pro/documentation/support/guides/translating-urls-slugs/
- [S7] https://polylang.pro/documentation/support/developers/rest-api/
- [S8] https://rinblog.org/en/polylang-free-rest-api-translations-en/ （2025-12-05；Polylang 3.8.9 + WP 7.1 实测）
- [S9] https://polylang.pro/documentation/support/developers/languages-rest-api/ ； https://polylang.pro/documentation/support/developers/settings-rest-api/
- [S10] https://polylang.pro/documentation/support/developers/polylang-cli/ ；GitHub API `diggy/polylang-cli`（archived，2020-08-24）
- [S11] Polylang master 源码（rag-web-browser，raw）：`src/rest-request.php`、`src/modules/REST/Request.php`、`src/query.php`、`src/frontend/frontend.php`、`src/frontend/frontend-links.php`、`src/frontend/canonical.php`、`src/links-directory.php`、`src/crud-posts.php`、`src/term-slug.php`、`src/modules/sync/{sync-metas,sync-post-metas,settings-sync}.php`、`src/modules/share-slug/load.php`、`src/modules/translate-slugs/load.php`、`src/integrations/cache/cache-compat.php`、`src/modules/wpml/wpml-api.php`、`src/api.php`、`src/Capabilities/Create/Post.php`、`src/frontend/frontend-auto-translate.php`；GitHub API `repos/polylang/polylang`（GPL-3.0，pushed 2026-10-09）与 commits
- [S12] https://polylang.pro/documentation/support/developers/filter-reference/ ； https://polylang.pro/documentation/support/developers/function-reference/ ； https://polylang.pro/documentation/support/guides/strings-translation/ ； https://polylang.pro/documentation/support/guides/multilingual-custom-post-types-and-taxonomies/
- [S13] https://polylang.pro/documentation/support/guides/managing-products/
- [S14] https://polylang.pro/pricing/polylang-for-woocommerce/ （Last update 2026-10-05）
- [S15] https://polylang.pro/polylang-for-woocommerce-changelog/ （2.2.6 2026-10-05 及历史条目）
- [S16] https://polylang.pro/how-to-create-a-multilingual-store-with-polylang-and-woocommerce/ ； https://polylang.pro/documentation/support/guides/translating-woocommerce-urls-and-strings/
- [S17] wordpress.org 插件 API `woo-poly-integration`（closed 2026-10-05，“temporary, pending a full review”）；https://wordpress.org/plugins/woo-poly-integration/
- [S18] GitHub API：`repos/hyyan/woo-poly-integration`（archived，MIT，pushed 2022-01-31）、commits、forks、`compare/master...{lpmcsn,okapteinis,integrITsolutions,smtturkan-droid,fifle}:master`；`nordhauser/woo-poly-integration`、`510AS/Polylang-WooCommerce-Data-Sync`、`proVject/Polylang-WooCommerce-Lite`、`BytesPulse-OE/Woocommerce-Polylang-Product-Sync`；`hyyan/…/readme.txt`
- [S19] Hyyan 源码（raw）：`src/Hyyan/WPI/Product/{Meta,Stock,Product}.php`、`Cart.php`、`Order.php`、`Pages.php`、`Emails.php`、`Endpoints.php`、`Coupon.php`、`Reports.php`
- [S20] https://github.com/grappler/polylang-slug 及 `polylang-slug.php`（GPLv2+，“not being actively developed”，tested 4.9.6）
- [S21] https://github.com/dbrabyn/polylang-slug-toolkit （GPLv2+，2026-06-09～2026-08-15）及 GitHub tree
- [S22] https://github.com/KLicheR/wp-polylang-translate-rewrite-slugs （pushed 2016-03-30）
- [S23] WooCommerce trunk 源码（raw）：`src/StoreApi/Utilities/{ProductQuery,CartController,OrderController}.php`、`src/StoreApi/Routes/V1/{CartAddItem,ProductsBySlug}.php`、`src/StoreApi/Schemas/V1/CartItemSchema.php`、`includes/data-stores/class-wc-product-data-store-cpt.php`、`includes/wc-stock-functions.php`、`includes/wc-product-functions.php`、`includes/wc-page-functions.php`、`includes/class-wc-checkout.php`；wp.org API `woocommerce` 11.2.0（2026-10-07）
- [S24] https://wp-kama.com/plugin/woocommerce/hook/woocommerce_store_api_add_to_cart_data （WC 8.8.0）
- [S25] https://developer.woocommerce.com/docs/apis/store-api/ ； …/resources-endpoints/products/ ； …/resources-endpoints/cart/
- [S26] https://docs.litespeedtech.com/lscache/lscwp/cache/ （Cache REST API：ON）； https://docs.litespeedtech.com/lscache/devguide/advanced/ （vary = cookie + 环境值）
- [S27] GitHub API `litespeedtech/lscache_wp` tree（thirdparty 目录）与 `thirdparty/wpml.cls.php`
- [S28] https://github.com/polylang/polylang/issues/294
- [S29] wp.org API `bogo`（3.9.3，2026-08-18，10000）；https://wordpress.org/plugins/bogo/ ；GitHub `rocklobster-in/bogo`（commits 2026-10-01）与 `includes/{post,query,rest-api,language-functions,rewrite}.php`
- [S30] wp.org API `wp-multilang`（2.4.34，2026-10-07，10000）；https://wordpress.org/plugins/wp-multilang/ ；GitHub `VaLeXaR/wp-multilang`（archived）
- [S31] https://github.com/qtranslate/qtranslate-xt 与 releases；GitHub API commits
- [S32] https://wordpress.org/about/roadmap/ ；https://wordpress.org/support/topic/wordpress-core-multilingual-roadmap-and-multisite-language-switcher/ （2026-08-12）；https://github.com/WordPress/gutenberg/issues/59250
- [S33] https://www.seopress.org/support/guides/seopress-polylang-multilingual-seo-guide/ （2026-03-12）；https://www.seopress.org/support/guides/translate-seopress-options-with-wpml-polylang/ ；https://wordpress.org/support/topic/hreflang-tags-missing-from-xml-sitemap-with-polylang-free-version/
- [S34] 本地：LiveCanvas 4.9.3 源码（`livecanvas-plugin-index.php:819,836,888-898,1392,1423`；`modules/templating.php:115,149`）；https://docs.livecanvas.com/ （目录无多语言页）
- [S35] https://developer.wordpress.org/cli/commands/i18n/make-json/ ；https://make.wordpress.org/core/2018/11/09/new-javascript-i18n-support-in-wordpress/
- [S36] https://wordpress.org/support/topic/polylang-3-8-9-detached-term_translations-after-term-language-change/ （2026-09-15）
- [S37] https://translate.wordpress.org/locale/de/formal/wp-plugins/woocommerce/
- [S38] https://polylang.pro/polylang-3-8-is-now-available-whats-new/ （2026-02-24）；https://polylang.pro/polylang-pro-3-9-rest-api-deepl-license-management/
- [S39] wp.org API：`lingotek-translation`（2026-07-31 安全关闭）、`qtranslate-x`（2021-08-31 安全关闭）、`multilingual-press` 2.11.3、`sublanguage` 2.12、`falang` 1.4.5、`woocommerce-multilingual` 5.6.3、`translatepress-multilingual` 3.3.7、`wp-seopress` 10.3、`litespeed-cache` 7.9.1、`loco-translate` 2.8.9、`woocommerce-polylang-integration`（2022-03-15 永久关闭）
- [L1] 本地：`refs/landed/chain-tip`（f007a9dd）`plugins/linker-i18n/`（0.5.78）逐文件行数与函数清单
- [L2] 本地：`docs/audit/2026-08-29-i18n-architecture-audit.md`
- [L3] 本地：`docs/adr/0031-an-erp-writes-stock-through-the-stock-endpoint.md`；`plugins/terravolt-b2b-core/includes/stock-mirror.php`；`status.php:303`
- [L4] 本地：`plugins/terravolt-b2b-core/includes/{bulk-order.php:328,legacy-redirects.php:699,compare-products.php:49}`
- [L5] 线上只读（2026-10-09）：`https://de-linker.com/de-sitemap.xml`（150 URL 分类统计）；`/wp-json/wc/store/v1/products?per_page=1&lang=de` 响应头 `content-language: en`；未见 `x-litespeed-cache`
- [L6] 本地：`data/catalog-snapshot/2026-09-05-products-full.json.gz`（全部 simple、无 tag、属性分布、`manage_stock` 全 false）
- [L7] 本地：链尖 `git grep` 计数（b2b-core + assistant + snippets/live）
