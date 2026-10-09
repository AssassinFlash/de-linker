# linker-i18n 去留复核：纳入付费方案后的重新比较

日期：2026-10-09。性质：调研 + 只读审计（未写站点、未改仓库）。
代码基线：`refs/landed/chain-tip` = `f007a9dd`，`plugins/linker-i18n` 0.5.78。
线上只读探测：匿名 cache-busted GET 与管理员 REST 只读 GET（凭据只由脚本读取，未打印），约 2026-10-09 07:00–07:25 UTC。
外部证据：全部经 Apify（`apify/rag-web-browser`、`apify/google-search-scraper`，REST 调用，token 取自 `~/.config/terravolt-builder/apify.env`，未打印、未落盘）。每条外部事实标 [S#]，见文末来源表（URL + 抓取时间 UTC）。内部证据标 [E#]。
标注：**SOURCED**＝有外部来源；**OBSERVED**＝本次实测/读码；**INFERRED**＝推断，未直接证实。

上一份结论（同日 `i18n-audit.md`，路线 H：保留核心 + 瘦身）把 WPML 写成"按要求排除（付费）"、把 Polylang for WooCommerce 判为"付费，违反 Law 3"。这条排除规则已被确认是错的（店主持有 ACF PRO、LiveCanvas、SEOPress PRO 许可，接受付费插件）。本报告在同样的事实基础上，把付费方案放回比较，并逐条检验上一结论。

---

## 0. 结论

**上一结论不成立。推荐排序：**

1. **替换为 WPML（Multilingual CMS：WPML + String Translation + WPML Multilingual & Multicurrency for WooCommerce），用 "Translate Everything Automatically"（TEA）+ PTC 引擎 + WPML Glossary 产出德语**；SEOPress PRO、LiveCanvas、ACF PRO、WindPress 不动。**有条件**：先在 staging 过 §7 的 6 道门槛（同 slug 的 /de/ URL、LiveCanvas 模板、b2b-core 孪生商品接缝、REST、性能、PTC 质量）。
2. **门槛失败时的替补：Polylang Pro + Polylang for WooCommerce（Business Pack）做结构，保留我们自己的"保存即翻译"任务**（DeepSeek + 词表 + 校验器写入德语孪生对象），删除 linker-i18n 的路由、渲染替换、chrome map、slug 表、sitemap/hreflang、前端 runtime。
3. **两者都失败才保留 linker-i18n 核心并瘦身**（上一结论），且要承认保留也意味着继续新增自研（后台界面、REST 德语暴露、SEO 修复）。

不推荐：TranslatePress、Weglot、WP Multilang、qTranslate-XT、Falang、MultilingualPress、等待 WordPress 核心。

**三条最强理由（WPML）：**

1. **它是唯一现成覆盖"保存即同步的 AI 德语 + 词表 + 公司内无人读德语"的存储式方案。** TEA 在发布时翻译新文章/页面/商品，商品文案改写后自动重译且不再计费（直到内容超过已付字数）[S4][S7][S8]；Glossary 在后台可锁定译法、标"不翻译"、写上下文说明 [S5]；语体（Sie/du）可经 "Improve Translations" 固定为规则 [S6]。对照：Polylang Pro 的 DeepL 是逐条手点，原文改了译文**不会**更新 [S21]；TranslatePress 是整页输出缓冲 + 字典替换（与我们的 chrome map 同类）[S39][S33]；Weglot 每个翻译页面浏览都调用其翻译 API，按词计费、€790/年起才有翻译 URL [S40]。
2. **维护面从约 2.98 万行降到"配置 + 薄适配"。** 现在：插件 PHP 8,896 行 + JS/CSS 555 行 + 插件外 54 个工具/测试/fixture 文件 20,378 行 [E1]，b2b-core 与 Advisor 有 43 个文件 180 处引用 linker-i18n 符号 [E2]。换成 WPML 后，商品 JSON 载荷 `_tv_legacy_acf_json` 可用 `wpml-config.xml` 的 `encoding="json"` + 子键清单声明翻译 [S10]，不再需要 `product.php` 的叶子白名单、两条 meta 读取替换、整页 `strtr`、路由改写、slug 表、sitemap/hreflang 代码和 16 KB 前端 runtime。
3. **德语变成真实的 WooCommerce 对象，React 应用读到的就是德语对象本身。** WCML 官方文档：`GET wc/v3/products?lang=de`，订单、分类同样支持 `lang`，响应带 `translations` 映射 [S9]；德语商品的名称、描述、分类、属性、permalink 都是该对象自己的字段，不需要逐字段替换代码。剩下的缺口只是公开 Store API 怎么选语言（无官方文档，§3.1、G4）。今天的系统差得多：线上 Store API 带 `X-Linker-Locale: de` 时，100 个商品只有 `short_description` 是德语，`name`/`description`/分类名/属性/permalink 全是英文 [E6]，保留方案要为每个字段补替换。

---

## 1. 对上一结论的逐条检验

| 上一结论的理由 | 检验 | 结果 |
|---|---|---|
| ① "没有可替换的免费存储式方案"（Polylang 管商品要付费、WPML 付费、TranslatePress 免费版是整页替换） | 前提就是"不准付费"。允许付费后，有两个成熟的存储式方案：WPML+WCML（€99/年起，含 WooCommerce）[S1]，Polylang Pro+Polylang for WooCommerce（Business Pack €139/年，续费 5 折）[S20] | **不成立** |
| ② "问题集中在重造 WordPress 原生能力的那几层" | 仍然成立（整页 strtr、7 套文案机制、仓库 fixture + Snippet 桥、无后台界面）。但这条理由推出的是"把这些层交给成熟插件"，不是"自己逐层改写" | **成立，但方向反转** |
| ③ "核心实测是好的，风险可局部修" | 核心正确性属实（服务端渲染、hreflang/canonical/sitemap 正确）。但"局部修"清单——后台界面、7 套文案归一、按页 noindex、去自动跳转、/de/ 英文 slug 301、商品新鲜度门、数字/完整性校验、REST 德语暴露——每一项都是新增自研，与"减少自研面"目标相反。另外本次实测 Store API 德语只覆盖 `short_description` [E6]，缺口比上次写的大 | **部分成立（正确性），不足以支撑"保留"** |
| 隐含前提："一个商品一行"（ADR-0031/0032/0034）不能破 | 按要求当作主张审查。语言孪生是 WPML/Polylang 的标准模型，SKU、价格、库存由插件同步（Polylang 官方文档明确 [S24]；WPML 有官方"跨语言统一管理库存"表述 [S15] 和第三方"库存与 SKU 跨译本同步"表述 [S52]）。真正的代价在 b2b-core 按商品 ID 工作的几处接缝（§5.2），是一次性适配，不是禁区 | **是成本，不是约束** |
| 2026-08-29 审计说"换平台会重开所有已解决的故障" | 逐项看：slug 路由、按句回退、商品载荷翻译、邮件语言、SEO 归属——WPML/WCML 都有原生机制（翻译 slug 与商店 base [S8][S15]、`encoding="json"` 自定义字段 [S10]、订单语言发邮件 [S8]、SEOPress 官方兼容 [S12]）。真正被重新打开的是"孪生商品 × 自研台账"的对齐，这是可测试的局部问题 | **夸大** |

---

## 2. 本站事实基线（含本次新测）

- **线上插件**（管理员 REST 只读，`/wp/v2/plugins`）[E5]：WooCommerce 11.1.0、ACF PRO 6.3.1、LiveCanvas 4.9.3、SEOPress 10.3 + PRO 10.2.1、WindPress 3.2.88、Classic Editor 1.7.0、Code Snippets 3.10.2、Linker i18n 0.5.78、Linker B2B Core 0.12.413、Linker AI Assistant 0.13.474。
- **ACF PRO 不承载商品字段（OBSERVED）**：`git grep` 在 `plugins/` 与 `snippets/live/` 中找不到任何 `get_field(`/`acf_add_local_field_group`/`update_field(` [E3]。商品文案在 JSON 字符串 meta `_tv_legacy_acf_json`（规格表/FAQ/卖点）和 `_tv_b2b_figures`（关键数值，自带 `value_de`）。商品页由 b2b-core 的 `template_include` 渲染（`theme-compat.php:22-44`），LiveCanvas 的 product-single 模板里虽有 `acf_repeater` 标签，但对商品不生效（INFERRED：死模板）。**结论：各插件的 "ACF 兼容" 不是决策因素；"能否翻译 JSON 自定义字段" 才是。**
- **德语 URL 形态（OBSERVED，`/de-sitemap.xml` 150 条）** [E9]：104 条 `/de/produkt/<与英文相同的 slug>/`，32 条页面（德语 slug，如 `/de/ueber-uns/`、`/de/linker-planer/`），10 条 `/de/produkt-kategorie/…`。迁移必须让商品在两种语言下**共用同一 slug**，否则要 104 条 301。
- **内容量（OBSERVED，管理员 REST 读取 + 线上商品快照）** [E8]：可翻译英文约 **120,036 个字母词 / 795,356 字符**（商品 JSON 载荷中已翻译的叶子 91,268 词，其中去重句段 55,200 词；商品名/短描述/长描述 9,428；27 个页面 17,643；10 篇文章 1,697）。**未计**页眉页脚、7 个模板、SEO 元数据、媒体 alt、界面字符串。
- **React/REST 现状（OBSERVED）** [E6]：`/wp-json/wc/store/v1/products?per_page=100`，EN 与 DE（`X-Linker-Locale: de`）对比：响应头 `Content-Language: de` 正确；`short_description` 100/100 为德语；`name` 0/100、`description` 0/100 不同；分类名一致为英文（"Backup Power"…）；属性一致；permalink 为 `/product/…`。
- **REST JSON 被污染（OBSERVED，旁证）** [E7]：匿名 `GET /wp-json/wp/v2/pages?per_page=20&page=2&_fields=id,content` 在 JSON 前多出 35,122 字节 `<style data-name="tangible-template-inline-style">`，任何 JSON 客户端都会解析失败（管理员 `context=edit` 同页为 105,366 字节）。LiveCanvas 4.9.4（2026-09-16）更新说明："REST API isolation. The bundled Tangible template system is no longer loaded during REST API requests" [S30]；线上是 4.9.3。与 i18n 方案无关，但会挡住 React 应用读页面内容（INFERRED：升级 LiveCanvas 可消除）。
- **linker-i18n 体量与耦合（OBSERVED）** [E1][E2]：见 §0 理由 2。b2b-core 内：`is_de()` 47 处、`Linker_I18n` 92 处；`tv_b2b_material_for_product` 41 处；`wc_get_product_id_by_sku` 在 `erp-stock.php:67`、`bulk-order.php:323`、`product-page-storefront.php:1142-1143`；库存镜像 `stock-mirror.php:346-349` 用 `set_stock_status()` + `save()` 写库存，并有"识别外来写入"的监听器 [E4]。

---

## 3. 各方案逐项（2026-10 现状）

### 3.1 WPML + WCML（Multilingual CMS）

- **价格**（SOURCED）：Multilingual Blog €39（不含 WooCommerce、不含 String Translation）、**Multilingual CMS €99**（含 ATE、String Translation、WooCommerce 支持、页面构建器支持、**22,500 个 AI 翻译词**）、Agency €199；均为一年更新与支持；不续费插件照常工作、只是不能更新 [S1]。2026 价格页未写续费价；2021 年公告的续费政策是首年价的 −25%（CMS 当时 $99→$74）[S17]（历史值，未证实仍适用）。
- **AI 翻译与计费**（SOURCED）[S2][S4]：引擎 PTC（WPML 自有）为默认，DeepL/Google/Microsoft 标为 legacy（DeepL/Google 价格为 PTC 的 50%，将被退役）。**TEA 只能在 PTC 上新开启**。TEA+PTC "每页每语言付一次，之后编辑免费，直到内容超过已付字数"；其他路径按更新词计费。PAYG：每月 500 词免费，之后每千词 €3.00 递减到 €0.40；表内累计上限：5,000 词 €13、15,000 词 €37、100,000 词 €182。按本站约 12 万词全部重译，按表累进约 €206（未扣 22,500 赠送词）；若迁移现有德语，首译成本接近 0。
- **保存即同步**（SOURCED）：TEA "translates new posts, pages, and products as you publish them"[S4]；商品描述改写后 "each update re-translates without a new charge"[S7][S8]；可选直接发布或进审阅队列 [S4][S6]。
- **词表**（SOURCED）[S5]：后台 WPML→Translations→Glossary；可锁定译法、标"不翻译"、每条带描述作为上下文；CSV 导入导出；每条 ≤200 字符、只收单数；仅 PTC 与 DeepL 使用词表（PTC 总是遵守，DeepL 可能忽略）；词表过大会降质；改词表后可"Update translations"重译近 30 天内容。另有 "Improve Translations" 把重复修改变成全站规则，含语体（Sie/du）[S6]。
- **与本站词表的差距（INFERRED）**：我们 `data/glossary-de.json` 的 `never` 可映射为"不翻译"，`sense/unless` 只能写进描述当上下文；`banned-vocabulary.json`（不写 KI/AI）与校验器（占位符、标签结构、型号完整性）在 WPML 里没有对应的运行时拦截，需要改成离线核查。
- **WooCommerce**（SOURCED）：商品、变体、分类、属性、购物车/结账（含 block checkout）、我的账户、邮件按下单语言发送 [S7][S8]；商店 base（product/category/tag/attribute）可在 "Store URLs" 按语言翻译 [S15]；WCML 5.6.3，2 天前更新，10 万+ 安装，测试到 WP 7.1.3；宣称"Inventory Tracking: manage inventory across all languages in one dashboard"[S15]。一个已解决的已知问题：WCML 使 REST 批量更新商品变慢（2023 报、2026-09-16 更新，状态 Resolved）[S14]。
- **自定义字段 JSON**（SOURCED）[S10]：`<custom-field action="translate" encoding="json">`，`<custom-fields-texts>` 可按子键、通配符声明要翻的键；`copy` 保持同步、`copy-once`、`ignore`。正好覆盖 `_tv_legacy_acf_json` 与 `_tv_b2b_figures`。
- **SEOPress**（SOURCED）：WPML 官方页："Es gibt keine ungelösten Kompatibilitätsprobleme"；SEOPress 在目录模式下生成含所有语言的 sitemap，hreflang 由 WPML 输出 [S12]；曾有的 "商品归档 slug 未翻进 sitemap" 已在 SEOPress 8.4 解决 [S13]。
- **LiveCanvas**（SOURCED）：LiveCanvas 3.8.0（2023-10-06）"Added Header & Footer WPML compatibility filtering"[S30]；WPML 的页面构建器推荐表里没有 LiveCanvas [S19]。LiveCanvas 页面是 Classic Editor 下 post_content 里的 HTML，动态模板是 CPT（INFERRED：可按普通内容翻译；Tangible 模板标签能否完好通过 ATE 未证实）。
- **REST**（SOURCED）：WC REST `lang` 读商品/订单/分类，`translation_of` 建译本，返回 `translations` [S9]；WP REST `?lang=de`（第三方文章，2026-09-14）[S18]。**Store API（公开、浏览器可直接调用的那套）没有官方文档**：EN/DE 关键词共 6 次检索，只找到两条已下线的 WPML 论坛帖摘要——有人通过 `wc/store/v1` 取属性得到错误语言（2025-03-26）、有人问 WPML 对 Store API 是否与 WC REST 行为一致 [S55]；WPML 公开论坛已关闭、帖子不再在线 [S55]。注意 `wc/v3` 需要鉴权，不适合浏览器里的公开 React 应用；所以 Store API 按语言返回是 staging 必测项（不行就在 `rest_pre_dispatch` 里按参数调用 WPML 的语言切换，或写一个小的只读端点，INFERRED）。
- **同 slug（未证实）**：WPML 2026 slug 文档未说明不同语言可共用同一 slug [S16]；2011 年的 WPML 2.4.1 更新说明称重复 slug 只对 posts 开放 [S54]。这决定 104 个商品 URL 能否原样保留，必须在 staging 验证。

### 3.2 Polylang Pro + Polylang for WooCommerce

- **价格**（SOURCED）[S20]：Pro €99/年起、for WooCommerce €99/年起、**Business Pack €139/年**（原价 €198），续费 5 折；不续费照常工作。免费 Polylang 3.8.10，80 万+ 安装，测试到 7.1.3，需付费扩展才支持 WooCommerce [S28]。
- **AI 翻译**（SOURCED）[S21][S22]：只有 DeepL（自备 key；文档称 DeepL API Developer 计划含一次性 100 万字符额度——本站约 79.5 万字符全量可一次放下）。**逐条翻译、不是批量；原文修改后译文不会自动更新，要手改或删掉译本重生成**；不支持 Elementor/Divi 等构建器存储格式与 FSE，Classic/Block 编辑器可用。可设正式/非正式语体；3.8（2026-02-24）起可选 DeepL glossary（词表在 DeepL 后台维护）；字符串可用 DeepL 批量翻译（3.7+，只翻未翻的）。
- **WooCommerce 同步**（SOURCED）[S24]：SKU、价格、税"copies and synchronizes"；重量尺寸运费类同步；"synchronizes the stock across the different languages when a customer purchases a product"。扩展 2.2.6（2026-10-05）已适配 WC 11.2 [S25]。
- **同 slug**（SOURCED）[S27]：Pro 支持页面、文章、自定义类型、分类等跨译本共用 slug——本站 104 个商品 URL 可原样保留。
- **JSON 自定义字段**（SOURCED）[S26]：支持 `wpml-config.xml`，`encoding="json"` 自 Polylang 3.8 起；`translate` 字段可被 DeepL/XLIFF 处理。
- **SEOPress / LiveCanvas**（SOURCED）：SEOPress 官方 Polylang 指南（2026-03-12），按语言生成 sitemap [S29]；LiveCanvas 3.1.0（2022-08-30）"Polylang compatibility: allows translating of template partials (Header & Footer)"[S30]。
- **REST**（SOURCED）：Pro 提供 `GET /wp/v2/posts?lang=fr`，响应含 `lang` 与 `translations`，可 `POST …?lang=fr&translations[en]=…` 关联 [S23]；WooCommerce REST API 需 Pro [S28]。Store API 语言：未找到文档。
- **对本站**：结构面与 WPML 同等，且同 slug 与更轻；**缺的是"保存即同步"**，所以只有和我们自己的翻译任务配合才满足要求（即排序第 2 的混合方案）。

### 3.3 TranslatePress

- **价格**（SOURCED）[S31]：Personal €99/年（1 站、5 万 AI 词、URL slug 翻译、SEO Pack）；Business €199/年（3 站、20 万 AI 词、DeepL 扩展）；Developer €349/年；加购 10 万词 €24。插件 3.3.7，40 万+ 安装，测试到 7.1.3 [S32]。
- **架构**（SOURCED）：`ob_start(array($this,'translate_page'))` 对整页 HTML 解析后查字典替换 [S39]；译文存在 `wp_trp_dictionary_*` 等表 [S34]；"Any alteration of the original string will invalidate the front-end translation"[S33]；自动翻译可能由前台访问触发 [S32]。即：和我们的 chrome map 同一类做法（按节点整串匹配，不是子串 `strtr`，INFERRED：复合词啃坏那类事故不同，但"源文一改译文失效"相同）。
- **SEO**（SOURCED）：SEO Pack 翻 slug、标题、描述、alt、OG，并扩展主流 SEO 插件的 sitemap [S38]；SEOPress 自称兼容 TranslatePress [S51]。
- **REST**（SOURCED）：更新日志有"Fixed translating WooCommerce product through REST API""Added support for WordPress search REST API""translating tags … through REST API"[S36]；第三方插件文档说明"TranslatePress’s own output buffer does not run for REST requests"，自定义端点要自己翻 [S37]。Store API：无文档。
- **迁移**（SOURCED）：官方支持回复"we don’t have support for importing/exporting translations"（2024-05-07）[S35]；只能整表 SQL 迁移 [S34]。我们的德语要写进它的字典表，句段切分必须与它一致，否则会被重新机翻。
- **结论**：保留"一个商品一行"是它唯一的结构优势；代价是把自研 chrome map 换成通用版、无法正规导入现有德语、词表能力未见文档、REST 半覆盖。**横移，不推荐。**

### 3.4 Weglot

- **价格**（SOURCED）[S40]：按"所有语言合计的唯一译词"计费：Starter €150/年（1 万词）、Business €290/年（5 万词）、**Pro €790/年（20 万词，卡片上列出 "translated URLs"）**、**Advanced €2,990/年（100 万词，卡片上列出 "Export & import"）**。本站约 8–12 万词 → 至少 Pro；导入现有德语按卡片看要 Advanced（INFERRED 自卡片列项）。
- **能力**（SOURCED）：词表规则（always/never translate）、翻译记忆、语体选择、子目录；"Monthly translation requests … approximately equal to the number of monthly translated page views"，即每次德语页面浏览都要调用 Weglot 翻译 API [S40]；WordPress 插件默认翻译 admin-ajax 的 JSON 响应 [S41]。WP REST/Store API：无文档。
- **结论**：最贵、SaaS 依赖、REST 未覆盖、导入门槛高。**不推荐。**

### 3.5 qTranslate-XT

- （SOURCED）不在 wordpress.org，需手动或 GitHub Updater 安装；README "Tested up to 6.8.3"、Gutenberg 部分支持；内容"stored in single post"（同一字段存多语言）[S42]。最后发布 3.16.1 = **2025-10-07**[S43]，master 最后提交 **2025-11-11**[S44]——到今天约 11 个月无提交。**风险最高，排除。**

### 3.6 WP Multilang

- （SOURCED）[S45]：2.4.34，2 天前更新，1 万+ 安装，测试到 7.1.3；REST 支持 `lang` 参数；"in title field are stored titles for all languages"（同字段多语言存储）；自动翻译、URL slug 翻译为付费版。对 SEOPress、我们的 JSON 载荷、ERP、REST 消费者都要求理解它的多语言串格式（INFERRED）。**排除。**

### 3.7 Falang

- （SOURCED）[S46]：1.4.5，2 个月前更新，1,000+ 安装，测试到 7.0.7；原生支持 WooCommerce；DeepL/ChatGPT 在 Pro；Google 摘要显示 "Translation are set in the meta"（架构与 linker-i18n 最像）、价格 Basic €44.90 / Standard €79.90 [S47]。用户量太小、REST/SEOPress 无文档。**排除。**

### 3.8 MultilingualPress

- （SOURCED）€149/年起，基于 Multisite [S48]；免费 v2 已于 2025 初退役 [S49]；WooCommerce 官方文档："MultilingualPress does not centralize the stock inventory. Each version of the product will still be managed separately"，且"does not connect custom fields"[S53]。要把单站改成 Multisite、每个语言一套 Woo、库存分开——与 ERP 按 SKU 推库存直接冲突。**排除。**

### 3.9 WordPress 核心

- （SOURCED）[S50]：Phase 3（协作）进行中；Phase 4 "Multilingual — Core implementation" 仍是长期项；2026 年大目标没有多语言；下一版 7.2 计划 2026-12-10。**近期无可依赖的核心方案。**

---

## 4. 对比矩阵

| 维度 | WPML（TEA/PTC） | Polylang + 自有翻译任务 | 保留 linker-i18n 并瘦身 | TranslatePress | Weglot |
|---|---|---|---|---|---|
| 正确性 / SEO | 每语言真实对象、hreflang、翻译 slug、SEOPress 官方兼容；商品同 slug 未证实 | 同左；商品同 slug 有文档 | 现在正确；有整站 noindex 一票否决、自动跳转、/de/ 英文 slug 200、DE 首字节 +0.3–0.9 s（上次审计） | 整页输出缓冲替换；SEO Pack 齐全 | 每次翻译页面浏览调用 Weglot API（SaaS）；翻译 URL 需 Pro |
| 保存即同步的 AI 德语 | **原生（TEA）** | 我们的任务实现（现有能力迁移） | 现有（shutdown + cron） | 渲染时自动翻 | 自动 |
| 词表 | 后台 Glossary + 上下文 + 语体 | 我们的 `glossary-de.json` + 校验器原样保留 | 同左 | 未见文档 | 词表规则 |
| 非德语员工操作 | 后台全流程，无需开发 | 后台结构 + 我们的任务（需要状态面板） | 只有商品面板；其余靠脚本和 Snippet 桥 | 前台可视编辑 | SaaS 后台 |
| 维护面 | 删 ~2.98 万行；留 config + 适配 + 接缝 | 删大半；留翻译器约 2–3 千行（INFERRED） | ~9k + ~20k，逐步缩小 | 删引擎；REST 要补 | 删引擎；REST 要补 |
| 本站兼容 | SEOPress ✔、LiveCanvas 页眉页脚 ✔、JSON meta ✔、WC REST `lang` ✔；孪生 × b2b-core 接缝 ✘需适配 | 同左 | 天然一行；REST 德语只有短描述 | 一行 ✔；REST 半覆盖 | 一行 ✔；REST ✘ |
| 从 `_linker_de_*` 迁移 | 脚本建孪生（WPML API / WC REST `translation_of`） | 同左（`pll_set_post_language` / REST） | 无 | 无官方导入，SQL 写字典 | 导入在 Advanced 档 |
| 费用/年（不含税） | €99 首年 + AI 词（小额） | €139 首年，约 €70 续费 + DeepSeek | €0 许可 | €99–199 | €790–2,990 |

---

## 5. 与"保留核心"的诚实对照

### 5.1 保留并不等于不花功夫
要让保留方案满足本次需求，必须新增：(a) 页面/文章/SEO/分类的后台德语面板和任务状态；(b) 把 7 套界面文案归到 gettext；(c) Store API/REST 的德语暴露（name、description、分类、属性、permalink——今天都没有 [E6]）；(d) 上次审计列出的 SEO 修复；(e) 性能（整页缓冲）。这些全是自研，维护面不降反升。

### 5.2 替换的真实代价在 b2b-core 的商品 ID 接缝（OBSERVED 位置，INFERRED 影响）
- 物料绑定 `tv_b2b_material_for_product()`（41 处调用，ADR-0034 说注册模块是"唯一接缝"）：德语孪生 ID 要先归一到原文 ID（`wpml_object_id` / `pll_get_post`）。
- SKU 查找 `wc_get_product_id_by_sku()`（ERP 端点、批量下单、店面各 1 处）：孪生共用 SKU，要归一到原文。
- 库存镜像 `set_stock_status()+save()` 与"外来写入"监听器：插件把库存同步到孪生时，会被监听器当成外来写入（风险：丢戳或来回写），必须在 staging 实测。
- 报价/Project 行按 Article（商品 ID）、Advisor 的商品记录与 FAQ：按语言读孪生即可，身份归一到原文。
- `is_de()` 47 处 + 其余 linker-i18n 符号：保留一个薄的语言适配（委托给 WPML/Polylang 的当前语言），不在 180 处逐个改。
- 商品编辑器的德语并排栏（ADR-0033）被 WPML 翻译编辑器取代；`email-voice.php` 的 Sie 覆盖改由 `de_DE_formal` 语言包或 String Translation 承担（两插件能否把德语映射到 `de_DE_formal` 未证实）。

---

## 6. 推荐与理由

**排序**：WPML（有条件）> Polylang + 自有翻译任务 > 保留并瘦身 > TranslatePress > Weglot；排除 qTranslate-XT、WP Multilang、Falang、MultilingualPress、核心。

**三条最强理由**：见 §0。补一句为什么 WPML 而不是 Polylang 排第一：两者结构面相当，Polylang 在同 slug、轻量、续费价上更好；决定性差别是本站"无人读德语、德语必须随保存同步"——WPML 的 TEA 原生做到，Polylang 的 DeepL 明确"不会自动更新"[S21]，只能靠我们继续养翻译器。如果 staging 证明 PTC 质量或性能不过关，这个优势消失，就换 Polylang 混合方案。

**成本口径**：许可费在 €99–139/年量级（WPML 首年 €99、Polylang Business Pack 首年 €139），AI 词费取决于新增量：表值为单月新增 5,000 词 €13、15,000 词 €37；TEA+PTC 下不增加字数的改写不计费 [S2][S4]；主要成本是一次性的迁移与 b2b-core 接缝适配，不是年费。

**为什么不 TranslatePress（虽然它保留一行商品）**：它在架构上就是 chrome map 的通用版 [S39]，无法正规导入我们已有的德语 [S35]，REST 只覆盖部分核心端点 [S36][S37]，词表无文档。

---

## 7. 迁移路径（WPML）

**阶段 0：staging 证明（先于任何生产改动）**。顺带把 LiveCanvas 升到 4.9.5（消除 REST JSON 污染，与方案无关，§2）。Hostinger staging 克隆；装 WPML + String Translation + WCML；EN 默认、DE 子目录；导入一个切片：首页（LiveCanvas）+ 页眉页脚 partial + 1 个 `lc_dynamic_template` + 5 个商品 + 2 个分类。门槛（任一失败即转 Polylang 混合方案或回到保留）：

| 门槛 | 通过标准 |
|---|---|
| G1 URL 原样 | 切片的 /de/ URL 与 `/de-sitemap.xml` 完全一致，尤其 `/de/produkt/<同 slug>/`、`/de/produkt-kategorie/…` |
| G2 LiveCanvas | 页眉页脚按语言切换；动态模板与 Tangible 标签经 ATE/PTC 后无损 |
| G3 b2b-core 接缝 | DE 商品页读孪生载荷；ERP 模拟推送后两个孪生的 `stock_status` 一致且镜像不来回写；报价行与 Advisor 归一到原文物料 |
| G4 REST | `wc/v3/products?lang=de` 返回德语 name/description/分类/permalink；公开的 Store API 能否按语言返回（不能则补一个按参数切换语言的小钩子或只读端点） |
| G5 性能 | EN/DE TTFB 不差于现状（现状 DE 比 EN 慢 0.3–0.9 s） |
| G6 PTC 质量 | 10 个对象对比现有德语：词表遵守、型号与数字不变、Sie 语体、无 "KI" |

**阶段 1：代码适配（b2b-core / Advisor）**：语言适配层（切换前委托 linker-i18n、切换后委托 WPML，保证同一份代码跨切换窗口可用）、§5.2 的 ID/SKU 归一、库存镜像孪生处理、`wpml-config.xml`（`product`、`lc_partial`、`lc_dynamic_template` 可翻；`_tv_legacy_acf_json` translate + `encoding="json"` + 子键清单，取代 `product.php` 白名单；`_tv_b2b_figures`、`_delinker_*` copy；`_linker_de_*` ignore）、`commerce-strings-en.json` 转 gettext。

**阶段 2：数据迁移脚本（幂等、先 dry-run）**：对 27 页 + 10 文 + 106 商品 + LiveCanvas partial/模板，用 `_linker_de_title/_content/_excerpt`、`_linker_de_acf_json` 建德语孪生；slug 取 `linker_i18n_slug_map` 与 `slug-bases-de.json`/`shelf-slugs-de.json`（商品同 slug）；SEOPress 德语标题/描述从 chrome map 的英德对取；分类名取 `taxonomy-de.json`；用 WPML API / WC REST `translation_of` 关联并标记完成，确保 TEA 不覆盖已迁移译文（需在 G6 一并验证）。`wp_linker_string` 只作存档，不导入。

**阶段 3：切换**（按部署顺序法则，单一维护窗口）：部署代码 → 激活 WPML → 跑迁移 → 关闭 `linker_i18n_serve_all` 并停用 linker-i18n → 公开 DE → 核对 150 条 DE URL、hreflang、SEOPress sitemap、结账与邮件、ERP 推送 → 打开 TEA。回滚：停用 WPML、重新启用 linker-i18n（其数据在阶段 4 前不动）。

**阶段 4：清理（验收后）**：删除 `plugins/linker-i18n` 与 54 个工具/测试/fixture 文件；`_linker_de_*` 与 `wp_linker_string` 先导出存档再删除。

**替补路径（Polylang 混合）**：阶段 0–4 结构相同，差别是保留并改造 `translator.php` + 词表 + 校验器为"保存时写德语孪生"的任务（删除路由、渲染替换、chrome map、slug 表、sitemap/hreflang、runtime JS）。

---

## 8. 未证实与风险

1. WPML 商品能否跨语言共用 slug（Polylang Pro 有文档 [S27]，WPML 未见）。
2. WPML/Polylang 的 Store API 语言支持（两者只对 wc/v3、wp/v2 有文档；WPML 用户曾报 `wc/store/v1` 返回错误语言 [S55]）。公开 React 应用走 Store API，这一条决定要不要补一个小端点。
3. LiveCanvas 动态模板与 Tangible 标签经 WPML ATE 的保真度。
4. 库存镜像监听器与插件库存同步的相互作用。
5. Hostinger 共享主机上的性能（WPML 只有"不会变慢，否则 30 天退款"的厂商承诺 [S1]）。
6. PTC 在光伏/储能 B2B 术语上的质量与词表遵守；我们的禁用词与校验器在 WPML 中无运行时等价物。
7. WPML 2026 续费价未公布（2021 年政策 −25%）。
8. 两插件能否把德语映射到 `de_DE_formal`。
9. 未计入的界面/页眉页脚/SEO/alt 文字量。

---

## 来源

外部（全部经 Apify，抓取时间 UTC，2026-10-09）：

- [S1] https://app.wpml.org/purchase — 06:44:44Z
- [S2] https://wpml.org/documentation/automatic-translation/automatic-translation-pricing/ — 06:44:44Z
- [S3] https://wpml.org/documentation/automatic-translation/ — 06:44:38Z
- [S4] https://wpml.org/documentation/automatic-translation/translate-everything-automatically/ — 06:48:04Z
- [S5] https://wpml.org/documentation/translating-your-contents/glossary/ （页面注明 2026-07-01 更新）— 06:44:44Z
- [S6] https://wpml.org/documentation/translating-your-contents/edit-automatic-translations/ （2026-07-02）— 06:44:42Z
- [S7] https://wpml.org/documentation/wpml-core-and-add-on-plugins/woocommerce-multilingual/ — 06:44:38Z
- [S8] https://wpml.org/documentation/translating-your-contents/translate-woocommerce/ — 07:01:55Z
- [S9] https://wpml.org/documentation/support/wcml-rest-api/ （2026-07-01）— 06:44:43Z
- [S10] https://wpml.org/documentation/support/language-configuration-files/custom-fields-translation-options/ （2026-01-29）— 06:48:14Z
- [S11] https://wpml.org/documentation/translating-your-contents/acf/ — 06:44:38Z
- [S12] https://wpml.org/de/documentation-3/plugins-kompatibilitaet/wpml-websites-suchmaschinen-optimieren-seopress/ （2024-10-23）— 06:48:35Z
- [S13] https://wpml.org/errata/seopress-product-archive-slug-not-translated-in-sitemaps/ — 07:13:58Z
- [S14] https://wpml.org/errata/woocommerce-multilingual-significantly-slows-down-rest-api-response-during-bulk-product-updates/ — 07:01:51Z
- [S15] https://wordpress.org/plugins/woocommerce-multilingual/ — 07:03:40Z（商店 base 可翻译另见 Google 摘要 https://fr.wordpress.org/plugins/woocommerce-multilingual/ ，约 07:16Z）
- [S16] https://wpml.org/documentation/getting-started-guide/translating-page-slugs/ （2026-03-25）— 07:16:25Z
- [S17] https://wpml.org/announcements/2021/07/upcoming-wpml-price-increase-how-to-save-by-signing-up-for-automatic-renewals/ — 07:03:01Z
- [S18] https://latw.ai/blog/wpml-rest-api-language-parameter/ （第三方，2026-09-14）— 06:44:45Z
- [S19] https://wpml.org/plugin-functionality/page-builder/ — 06:48:28Z
- [S20] https://polylang.pro/pricing/ — 06:46:16Z
- [S21] https://polylang.pro/documentation/support/guides/how-to-use-deepl-machine-translation-with-polylang-pro/ — 06:46:32Z
- [S22] https://polylang.pro/polylang-3-8-is-now-available-whats-new/ （2026-02-24）— 07:09:07Z
- [S23] https://polylang.pro/documentation/support/developers/rest-api/ — 06:46:28Z
- [S24] https://polylang.pro/documentation/support/guides/managing-products/ — 06:46:22Z
- [S25] https://polylang.pro/polylang-for-woocommerce-changelog/ — 06:48:14Z
- [S26] https://polylang.pro/documentation/support/developers/the-wpml-config-xml-file/ — 06:48:15Z
- [S27] https://polylang.pro/documentation/support/guides/share-the-same-posts-or-terms-url-slugs-across-translations/ — 07:16:25Z
- [S28] https://wordpress.org/plugins/polylang/ — 07:09:12Z
- [S29] https://www.seopress.org/support/guides/seopress-polylang-multilingual-seo-guide/ — 07:14:01Z
- [S30] https://livecanvas.com/changelog/ — 06:50:32Z
- [S31] https://translatepress.com/pricing/ — 06:51:31Z
- [S32] https://wordpress.org/plugins/translatepress-multilingual/ — 06:52:20Z
- [S33] https://translatepress.com/docs/frequently-asked-questions/ — 06:56:36Z
- [S34] https://translatepress.com/docs/migrate-translations-across-sites/ — 06:56:30Z
- [S35] https://wordpress.org/support/topic/translate-content-using-database-export-import/ （官方回复 2024-05-07）— 06:56:34Z
- [S36] https://translatepress.com/docs/translatepress-free-changelog/ — 07:08:33Z
- [S37] https://webberzone.com/support/knowledgebase/multilingual-support-top-10/ （第三方）— 07:08:32Z
- [S38] https://translatepress.com/docs/addons/seo-pack/ — 06:52:32Z
- [S39] https://plugins.svn.wordpress.org/translatepress-multilingual/trunk/includes/class-translation-render.php — 05:50:48Z（同日上一份审计抓取）
- [S40] https://www.weglot.com/pricing — 06:51:26Z
- [S41] https://developers.weglot.com/wordpress/use-cases/how-to-not-translate-specific-ajax-action — 06:51:44Z
- [S42] https://github.com/qtranslate/qtranslate-xt — 06:55:32Z
- [S43] https://github.com/qtranslate/qtranslate-xt/releases/tag/3.16.1 （HTML `datetime="2025-10-07T11:09:02Z"`）— 06:58:45Z
- [S44] https://github.com/qtranslate/qtranslate-xt/commits/master/ （最新 "Commits on Nov 11, 2025"）— 06:59:01Z
- [S45] https://wordpress.org/plugins/wp-multilang/ — 06:55:29Z
- [S46] https://wordpress.org/plugins/falang/ — 06:55:35Z
- [S47] Google 结果（apify/google-search-scraper，约 07:15Z）：https://id.wordpress.org/plugins/falang/ 、https://www.faboba.com/en/component/hikashop/product/17-falang-for-wordpress-standard.html 、https://www.faboba.com/component/hikashop/product/16-falang-for-wordpress-basic.html
- [S48] https://multilingualpress.org/ — 05:40:42Z（同日上一份审计抓取）
- [S49] https://wordpress.org/plugins/multilingual-press/ — 05:40:53Z（同上）
- [S50] https://wordpress.org/about/roadmap/ — 06:57:31Z
- [S51] Google 结果（约 07:13Z）：https://www.seopress.org/es/soporte/preguntas-frecuentes/que-plugins-multilingues-son-compatibles-con-seopress/ （摘要："WPML, Polylang, TranslatePress, Weglot y Multilingual Press"）
- [S52] https://funnelkit.com/woocommerce-multilingual/ （第三方，2026-08-14 更新）— 07:06:29Z
- [S53] https://woocommerce.com/document/woocommerce-multilingualpress/ — 06:58:13Z
- [S54] Google 结果（约 07:16Z）：https://wpml.org/ru/changelog/2011/11/wpml-2-4-1-finally-duplicate-slugs-for-different-languages/ （摘要："duplicate slugs are available for 'posts' only"，2011-11-14）
- [S55] Google 结果（约 07:24Z）：https://wpml.org/forums/topic/wc-store-v1-api-retrieving-wrong-language-for-endpoint-products-attributes-attr_id/ （2025-03-26）、https://wpml.org/forums/topic/integration-with-wc-store-api/ ；直接抓取两帖均返回 WPML 404 页，正文写明 "The public support forum is closed and its threads are no longer online"（07:24:27Z）

内部：

- [E1] `refs/landed/chain-tip`：`plugins/linker-i18n` PHP 8,896 行、`assets/` 555 行；插件外路径含 i18n/german 的 54 个文件 20,378 行（清单：scratchpad `i18nr/tooling-files.txt`）。
- [E2] `git grep` b2b-core + linker-ai-assistant 对 `Linker_I18n|linker_i18n_|Linker\I18n|LinkerI18n`：43 个文件 180 处。
- [E3] `git grep` `plugins/` + `snippets/live/`：ACF API 调用 0 处；商品 meta 键见线上 `wc/v3/products` 快照；`theme-compat.php:22-44`。
- [E4] `erp-stock.php:67`、`bulk-order.php:323`、`product-page-storefront.php:1142-1143`、`stock-mirror.php:346-349`。
- [E5] 管理员 REST 只读 `GET /wp-json/wp/v2/plugins`，约 07:20Z。
- [E6] 匿名 `GET /wp-json/wc/store/v1/products?per_page=100`，EN 与 `X-Linker-Locale: de` 各一次，约 07:18Z。
- [E7] 匿名 `GET /wp-json/wp/v2/pages?per_page=20&page=2&_fields=id,content`，约 07:22Z（对照：`page=1` 与 `_fields=id,slug` 无前缀）。
- [E8] 管理员 REST 只读 `wp/v2/pages|posts?context=edit`（27 + 10）+ 线上商品快照（106，`_tv_legacy_acf_json` 与 `_linker_de_acf_json` 逐叶对比）；计数为字母词。
- [E9] `/de-sitemap.xml`（同日 13:27 CST 抓取，scratchpad `i18n-live/desitemap.xml`）。
- [E10] 同日上一份审计：scratchpad `i18n-audit.md`（A2/A3 的 SEO 风险、运营与 DE 首字节数据）。
