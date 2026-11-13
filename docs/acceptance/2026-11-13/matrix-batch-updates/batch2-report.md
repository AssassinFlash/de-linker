# `template-matrix.json` 31 行收口实证调查报告（Batch 2）

- **日期**：2026-11-13
- **范围**：`docs/acceptance/2026-10-22/full-site/template-matrix.json` 全部 31 行（26 个 `lc_dynamic_template` + 5 个 `lc_partial`）；全程只读，未修改任何仓库已跟踪文件。
- **数据来源与约束**：
  1. 仓库源码静态核查（`plugins/linker-commerce`、`plugins/linker-i18n`、`themes/picostrap5-child-base`）与生产 LiveCanvas 插件源码只读核对；
  2. 生产 SSH 只读 WP-CLI（`wp post list` / `wp eval` 只读查询 `lc_dynamic_template`、`lc_partial`、`lc_use_template_of_slug`、Polylang 语言配对与内容 SHA256，零写操作）；
  3. 生产只读 HTTP `curl`（读取 LiveCanvas 渲染注释 `<!-- LC DT ID: <id> -->` 与 `<script id="lc_script_tag">`）；
  4. Playwright Headless Chromium（来自 `tests/e2e/node_modules/@playwright/test`）对 5 个 `lc_partial` 在生产长短页 × EN/DE × 1440/390 做只读 GET 与非破坏性 UI 交互验证（无登录、无表单提交）。
- **更新提案文件**：`docs/acceptance/2026-11-13/matrix-batch-updates/batch2-rows.json`（31 条）。

---

## 一、模板-路由映射与渲染机制（含源码定位）

### 1.1 接管与防抢占机制

- `plugins/linker-commerce/includes/Plugin.php:84,112-114`：`stand_down_legacy_template_preemption()` 在 `plugins_loaded` 移除旧插件 `remove_filter( 'template_include', 'tv_b2b_template_include', PHP_INT_MAX )`，确保 LiveCanvas 动态模板是商务与内容页型的唯一渲染通道。
- 主题 `themes/picostrap5-child-base/functions.php` 不参与 `template_include` 路由；仅负责 `<html class="js">`（`:22-25`）、`data-theme="light"`（`:34-40`）和博客分类 Schema（`:49-54`）。

### 1.2 LiveCanvas 动态模板主解析链（生产 `livecanvas/modules/templating.php`）

`lc_use_dynamic_templates()` 挂载在 `template_include` 优先级 `99998`（`livecanvas/modules/templating.php:4`），按以下顺序依次覆盖 `$template_id`：

1. **单篇内容（`is_singular() && !lc_post_is_using_livecanvas($post->ID)`）**（`templating.php:18-35`）：先查 `is_single_<post_type>__in_<tax>_<slug>`，未命中则查 `is_single_<post_type>`（匹配 `is_single_post`、`is_single_product`）。
2. **归档页（`is_archive()`）**（`templating.php:38-74`）：依次检查 `is_author`、`is_date`、`is_category`（`is_archive_for_tax_category`）、`is_tag`、`is_tax`（先查 `is_archive_for_tax_<tax>__<slug>`，后查 `is_archive_for_tax_<tax>`），若仍为 false 再兜底 `is_archive_for_post_type_<post_type>`。
   - **重要联动**：`plugins/linker-commerce/includes/Presentation/ArchiveAssignments.php:20-29,71-97` 在 `present` 时为英文模板 `231` 与德文模板 `6905` 写入了所有公开产品分类法（`product_cat`、`product_brand`、`pa_brand`、`pa_series`、`pa_phase`、`pa_battery-voltage` 等共 11 个）的 `is_archive_for_tax_<tax>=1`，确保空归档（如 `/brand/ecoflow/`）与共享分类归档仍能命中 `231` / `6905`。
3. **特殊页（`templating.php:78-84`）**：`!is_front_page() && is_home()` → `is_blog_posts_index`；`is_front_page()` → `is_front_page`（当前首页为页面自身 LiveCanvas 内容，不使用动态模板）；`is_search()` → `is_search`；`is_404()` → `is_404`。
4. **WooCommerce 专用页（`templating.php:89-100`）**：依次检查 `is_shop()` → `is_shop_page`、`is_cart()` → `is_cart_page`、`is_checkout()` → `is_checkout_page`、`is_account_page()` → `is_account_page`。仅当 `$wc_specific_template_id` 为真时才覆盖 `$template_id`（`:98`）。
5. **单页显式指定模板（`templating.php:103-106`）**：若 `is_singular()` 页面存在 `lc_use_template_of_slug` post meta，调用 `lc_get_template_id_by_slug($slug)` 覆盖 `$template_id`。
   - `plugins/linker-commerce/includes/Presentation/Templates.php:141-158,858-867`（`PAGES` 与 `assign_pages()`）为 8 个工具/功能页（EN/DE 的 `compare`、`faq`、`advisor`、`configurator`）写入对应的 `lc_use_template_of_slug`。
   - **跨语言细节**：虽然 `6968` (`linker-compare-de`)、`6970` (`linker-faq-de`)、`6972` (`linker-advisor-de`)、`6974` (`linker-configurator-de`) 在数据库中因 `Templates::sync_page_template()` 调用 `assign_source_language()`（`Templates.php:816,943-951`）而被标为 `pll_lang = "en"`，但 `lc_get_template_id_by_slug()`（`templating.php:143-151`）使用 `get_posts(['post_type' => 'lc_dynamic_template', 'name' => $slug, ...])`——由于 WordPress 对带 `name` 的单篇查询忽略分类法（语言）条件（`plugins/linker-i18n/includes/SameSlug/Lookup.php:154-155` 有同款源码说明），所以 `/de/` 页面依然精确解析到对应 `-de` 模板 ID。
6. **多语言兜底过滤器 `lc_modify_template_id`**（`templating.php:109`）：
   - 由 `plugins/linker-i18n/includes/Plugin.php:157` 挂入 `DynamicTemplates::template()`（`plugins/linker-i18n/includes/DynamicTemplates.php:90-101`）。
   - Polylang 将 `lc_dynamic_template` 与 `lc_partial` 纳入翻译类型（`plugins/linker-i18n/includes/TranslatedTypes.php:27,64-70`），因此 `lc_get_template_id()` 的 `get_posts()` 默认被 Polylang `parse_query` 过滤到当前请求语言。
   - 当请求语言为 `de` 且 `$template_id` **为空/false** 时，若请求属于 `is_shop` / `is_cart` / `is_checkout` / `is_account_page` 之一，`DynamicTemplates::english_template()` 临时将 `PLL()->curlang` 切到 `en` 查找英文结构模板（`DynamicTemplates.php:122-146`）。
   - **本轮发现的关键逻辑缺陷**：`DynamicTemplates::template()` 第 91 行 `if ( $template_id || ... ) return $template_id;` 假设未翻译的页面 `$template_id` 为 false，但 `is_shop()` 同时满足 `is_archive()`，详见第四节缺陷分析。
7. **渲染签名**：`lc_render_dynamic_template($template_id)`（`templating.php:154-169`）在输出首部固定写入 HTML 注释 `<!-- LC DT ID: <template_post_id> -->`，为生产路由命中提供确定性身份指纹。

### 1.3 `lc_partial`（页头、页脚、Global JS）渲染机制

- **Header (`17` / `6909`) 与 Footer (`18` / `6911`)**：
  - 主题 `picostrap5/header.php:33` 与 `picostrap5/footer.php:15` 调用 `lc_custom_header()` / `lc_custom_footer()`（`livecanvas-plugin-index.php:856-870`）。
  - `lc_get_header()`（`livecanvas-plugin-index.php:817-830`）与 `lc_get_footer()`（`:834-847`）先经 `lc_get_partial_postid('is_header'|'is_footer')`（被 Polylang 过滤到当前语言），再经 `apply_filters('wpml_object_id', ..., 'lc_partial')` 解析双语孪生（`17↔6909`、`18↔6911`），分别包裹在 `<header id='lc-header'>` 与 `<footer id='lc-footer'>` 中输出。
  - `Templates::sync_header_partials()` / `sync_footer_partials()`（`Templates.php:549-768`）通过 `pll_get_post($en_id, 'de')` 同步双语内容；仓库 `partials/{header,footer}.html` 与 `partials/de/{header,footer}.html` 和生产 SHA256 完全一致。
- **Global JavaScript Code (`30`)**：
  - `lc_global_script_tag()`（`livecanvas-plugin-index.php:128-132`）在 `wp_footer` 中输出 `<script id="lc_script_tag" type="module"><?php echo lc_get_partial_by_cf("is_global_js") ?></script>`。
  - 生产数据库 `ID=30` `post_content` 长度为 0（空字符串 SHA256 `e3b0c442...`），与 `docs/audit/2026-11-04-lc-global-js-partial.md` 记录完全吻合，为刻意保留的空槽位。

---

## 二、31 行逐行实证结论

> 注：本轮只读 WP-CLI 核实生产 31 个模板**全部为 `post_status=publish`**，且 28 个由 `plugins/linker-commerce/content/livecanvas/**/*.html` 托管的模板与当前仓库 HEAD 字节级（SHA256）完全一致；其中 20 行的生产 SHA256 已较 2026-10-22 `template-matrix.json` 初建基线更新（在 `batch2-rows.json` 的 `verified_checks.template_binding_20261113.production_content_sha256` 中逐一留证）。

| ID | Slug | 类型 | 有效语言 | 基线 SHA=生产? | 生产实证命中路由与身份标记 | 确认的 `applicable_states` | 新 `status` |
|---|---|---|---|---|---|---|---|
| 6969 | `linker-faq` | dynamic | en | False（与 `faq_page.html` 一致） | `GET /faq-download/` (200), `/?tab=documents` (200) → `LC DT ID: 6969` | `anonymous-guest`, `en`, `singular-page-lc_use_template_of_slug`, `faq-tab`, `documents-tab` | `partially-verified` |
| 6970 | `linker-faq-de` | dynamic | de (`pll_lang=en`) | False（与 `de/faq_page.html` 一致） | `GET /de/faq-dokumente/` (200), `/?tab=documents` (200) → `LC DT ID: 6970` | `anonymous-guest`, `de`, `singular-page-lc_use_template_of_slug`, `faq-tab`, `documents-tab` | `partially-verified` |
| 6971 | `linker-advisor` | dynamic | en | True (`advisor_page.html`) | `GET /genie/` (200) → `LC DT ID: 6971` | `anonymous-guest`, `en`, `singular-page-lc_use_template_of_slug` | `partially-verified` |
| 6972 | `linker-advisor-de` | dynamic | de (`pll_lang=en`) | True (`de/advisor_page.html`) | `GET /de/genie/` (200) → `LC DT ID: 6972` | `anonymous-guest`, `de`, `singular-page-lc_use_template_of_slug` | `partially-verified` |
| 6973 | `linker-configurator` | dynamic | en | False（与 `configurator_page.html` 一致） | `GET /solution-configurator/` (200) → `LC DT ID: 6973` | `anonymous-guest`, `en`, `singular-page-lc_use_template_of_slug` | `partially-verified` |
| 6974 | `linker-configurator-de` | dynamic | de (`pll_lang=en`) | False（与 `configurator_page.html` 一致） | `GET /de/loesungskonfigurator/` (200) → `LC DT ID: 6974` | `anonymous-guest`, `de`, `singular-page-lc_use_template_of_slug` | `partially-verified` |
| 6961 | `shop-page` | dynamic | en, de (期望) | False（与 `shop_page.html` 一致） | **EN** `/products/`, `/?orderby=title`, `/?product-page=2` (200) → `LC DT ID: 6961`；**DE `/de/produkte/` 实际命中 `6905`（缺陷）** | `anonymous-guest`, `en`, `shop-page`, `sorting`, `pagination`, `de-binding-defect` | `partially-verified` *(含缺陷)* |
| 6962 | `solution-draft` | dynamic | en, de | False（与 `cart_page.html` 一致） | `GET /cart/` (200), `GET /de/loesungsentwurf/` (200) → `LC DT ID: 6962` | `anonymous-guest`, `en`, `de`, `empty-draft` | `partially-verified` |
| 6963 | `proforma-request` | dynamic | en, de | True (`checkout_page.html`) | `GET /proforma-request/` (200), `GET /de/proforma-anfrage/` (200) → `LC DT ID: 6963` | `anonymous-guest`, `en`, `de`, `empty-draft-inquiry-form` | `partially-verified` |
| 6964 | `account` | dynamic | en, de | True (`account_page.html`) | `GET /my-account/`, `/register/`, `/lost-password/` (200) & `/de/mein-konto/`, `/registrieren/`, `/passwort-zuruecksetzen/` (200) → `LC DT ID: 6964` | `anonymous-guest`, `en`, `de`, `sign-in`, `register`, `lost-password` | `partially-verified` |
| 6967 | `linker-compare` | dynamic | en | True (`compare_page.html`) | `GET /compare-products/` (200), `/?ids=1832,6530` (200) → `LC DT ID: 6967` | `anonymous-guest`, `en`, `singular-page-lc_use_template_of_slug`, `empty-selection`, `populated-comparison` | `partially-verified` |
| 6968 | `linker-compare-de` | dynamic | de (`pll_lang=en`) | True (`de/compare_page.html`) | `GET /de/produkte-vergleichen/` (200), `/?ids=1832,6530` (200) → `LC DT ID: 6968` | `anonymous-guest`, `de`, `singular-page-lc_use_template_of_slug`, `empty-selection`, `populated-comparison` | `partially-verified` |
| 940 | `template-for-404` | dynamic | en | True | `GET /_coverage-review-missing-route/`, `/products/?pa_brand=nonexistent_zzz`, `/products/page/999/`, `/author/admin/` (404) → `LC DT ID: 940` | `anonymous-guest`, `en`, `http-404`, `out-of-range-pagination`, `missing-route` | `partially-verified` |
| 6861 | `vorlage-fur-404` | dynamic | de | False（DB 内容已更新） | `GET /de/_coverage-review-missing-route/`, `/de/produkte/?pa_brand=nonexistent_zzz`, `/de/produkte/seite/999/`, `/de/mein-konto/passwort-vergessen/` (404) → `LC DT ID: 6861` | `anonymous-guest`, `de`, `http-404`, `out-of-range-pagination`, `missing-route` | `partially-verified` |
| 619 | `template-for-search` | dynamic | en | False（与 `search.html` 一致） | `GET /?s=SAJ` (200), `/?s=nonexistent_zzz_123` (200), `/?s=SAJ&post_type=post` (200) → `LC DT ID: 619` | `anonymous-guest`, `en`, `search-with-results`, `search-empty-results`, `journal-search` | `partially-verified` |
| 6875 | `vorlage-fur-die-suche` | dynamic | de | False（与 `de/search.html` 一致） | `GET /de/?s=SAJ` (200), `/de/?s=nonexistent_zzz_123` (200), `/de/?s=Notstrom&post_type=post` (200) → `LC DT ID: 6875` | `anonymous-guest`, `de`, `search-with-results`, `search-empty-results`, `journal-search` | `partially-verified` |
| 613 | `template-for-single-post` | dynamic | en | False（与 `blog_single.html` 一致） | `GET /hybrid-inverter-vs-ac-coupled-storage/` (200) → `LC DT ID: 613`（并保留原 649 路由） | `anonymous-guest`, `en`, `single-post` | `partially-verified` |
| 6877 | `vorlage-fur-einzelnen-beitrag` | dynamic | de | False（与 `de/blog_single.html` 一致） | `GET /de/hybridwechselrichter-vs-ac-speicher/` (200) → `LC DT ID: 6877`（并保留原 649 路由） | `anonymous-guest`, `de`, `single-post` | `partially-verified` |
| 607 | `template-for-archive-for-tax-category` | dynamic | en | False（与 `category_archive.html` 一致） | `GET /category/applications-blog/` (200) → `LC DT ID: 607` | `anonymous-guest`, `en`, `taxonomy-archive-category` | `partially-verified` |
| 6879 | `vorlage-fur-archiv-der-steuerkategorie` | dynamic | de | False（与 `de/category_archive.html` 一致） | `GET /de/kategorie/anwendungen/` (200) → `LC DT ID: 6879` | `anonymous-guest`, `de`, `taxonomy-archive-category` | `partially-verified` |
| 574 | `template-for-blog-posts-index` | dynamic | en | False（与 `blog_index.html` 一致） | `GET /blog/` (200) → `LC DT ID: 574`（`/blog/page/2/` 重定向至 `/blog/`） | `anonymous-guest`, `en`, `blog-posts-index` | `partially-verified` |
| 6881 | `vorlage-fur-blog-beitragsindex` | dynamic | de | False（与 `de/blog_index.html` 一致） | `GET /de/blog/` (200) → `LC DT ID: 6881`（`/de/blog/seite/2/` 重定向至 `/de/blog/`） | `anonymous-guest`, `de`, `blog-posts-index` | `partially-verified` |
| 234 | `template-for-single-product` | dynamic | en | False（与 `single_product.html` 一致） | `GET /product/saj-ats1-t63-a/` (200) → `LC DT ID: 234` | `anonymous-guest`, `en`, `single-product` | `partially-verified` |
| 6903 | `vorlage-fur-einzelnes-produkt` | dynamic | de | False（与 `de/single_product.html` 一致） | `GET /de/produkt/goodwe-gw60k-sts-g10/` (200) → `LC DT ID: 6903` | `anonymous-guest`, `de`, `single-product` | `partially-verified` |
| 231 | `template-for-archive-for-post-type-product` | dynamic | en | False（与 `archive_product.html` 一致） | `GET /product-category/{accessories,home-storage,inverters}/`, `/brand/{goodwe,ecoflow,chint}/`, `/series/.../`, `/phase/single-phase/`, `/battery-voltage/{high,low}-voltage/` (200) → `LC DT ID: 231` | `anonymous-guest`, `en`, `taxonomy-archive-product_cat`, `taxonomy-archive-brand`, `taxonomy-archive-pa_series`, `taxonomy-archive-pa_phase`, `taxonomy-archive-pa_battery-voltage`, `empty-archive` | `partially-verified` |
| 6905 | `vorlage-fur-archiv-fur-beitragstyp-produkt` | dynamic | de | False（与 `de/archive_product.html` 一致） | `GET /de/produkt-kategorie/.../`, `/de/brand/{goodwe,ecoflow,chint}/`, `/de/series/.../`, `/de/phase/dreiphasig/`, `/de/battery-voltage/hochvolt/`, **`/de/produkte/` (意外承接)** (200) → `LC DT ID: 6905` | `anonymous-guest`, `de`, `taxonomy-archive-product_cat`, `taxonomy-archive-brand`, `taxonomy-archive-pa_series`, `taxonomy-archive-pa_phase`, `taxonomy-archive-pa_battery-voltage`, `empty-archive`, `shop-page-de-fallback-collision` | `partially-verified` |
| 30 | `global-javascript-code` | partial | en, de | True（空串 `len=0`） | 所有 EN/DE 页面 `wp_footer` 均输出 `<script id="lc_script_tag" type="module"></script>`（空） | `not-applicable`, `empty-stock-slot`, `en`, `de`, `anonymous-guest` | `not-applicable` |
| 17 | `header` | partial | en | False（与 `partials/header.html` 一致） | Playwright EN 长短页及 404 → `<header id='lc-header'>` + `aria-label="Primary navigation"` | `anonymous-guest`, `en`, `long-page`, `short-page`, `404`, `desktop-1440`, `mobile-390`, `dropdown-open-close-esc`, `mobile-drawer-open-esc`, `language-switch` | `partially-verified` |
| 18 | `footer` | partial | en | True (`partials/footer.html`) | Playwright EN 长短页及 404 → `<footer id='lc-footer'>` + `aria-label="Footer navigation"` | `anonymous-guest`, `en`, `long-page`, `short-page`, `404`, `desktop-1440`, `mobile-390`, `footer-tabs`, `language-switch` | `partially-verified` |
| 6909 | `kopfzeile` | partial | de | False（与 `partials/de/header.html` 一致） | Playwright DE 长短页及 404 → `<header id='lc-header'>` + `aria-label="Primäre Navigation"` | `anonymous-guest`, `de`, `long-page`, `short-page`, `404`, `desktop-1440`, `mobile-390`, `dropdown-open-close-esc`, `mobile-drawer-open-esc`, `language-switch` | `partially-verified` |
| 6911 | `fuszeile` | partial | de | True (`partials/de/footer.html`) | Playwright DE 长短页及 404 → `<footer id='lc-footer'>` + `aria-label="Fußzeilen-Navigation"` | `anonymous-guest`, `de`, `long-page`, `short-page`, `404`, `desktop-1440`, `mobile-390`, `footer-tabs`, `language-switch` | `partially-verified` |

---

## 三、5 个 `lc_partial` 的 Playwright 只读交互实证

使用 Playwright Chromium 对生产站点执行只读页面访问与非破坏性交互，全程 `pageerror` 为 0：

1. **长短页与 404 覆盖（`1440×900`）**：
   - 长页：`https://de-linker.com/`（`docHeight=8388`, `en-US`）与 `/de/`（`8613`, `de-DE`）；`/privacy-policy/`（`6034`）与 `/de/datenschutz/`（`6380`）。
   - 短页：`https://de-linker.com/cart/`（`1300`, `en-US`）与 `/de/loesungsentwurf/`（`1300`, `de-DE`）。
   - 404 页：`https://de-linker.com/_coverage-review-missing-route/`（`2792`, HTTP 404）与 `/de/_coverage-review-missing-route/`（`2872`, HTTP 404）。
   - 所有页面均正确注入对应语言的页头（EN `Primary navigation` / DE `Primäre Navigation`）、页脚（EN `Footer navigation` / DE `Fußzeilen-Navigation`）、`linker-header-menu.js` 动态绑定的 `aria-controls="linker-menu-products"`、以及页脚脚本激活的 `.footer-ready`。
2. **Header 交互（`17` / `6909`）**：
   - 桌面 `1440`：EN 点击 `Products`、DE 点击 `Produkte` 均将 `aria-expanded` 由 `false` 切为 `true` 且 `.tv-mega-menu` 可见；按 `Escape` 后恢复 `aria-expanded="false"`。
   - 手机 `390`：EN 点击 `#tv-mobile-toggle` 后 `#tv-mobile-panel` `data-open="true"` 且可见，首个手风琴 `<details>` 展开，按 `Escape` 关闭并复位；DE 点击 `#tv-mobile-toggle` 后原生 `<details class="tv-mobile-navigation">` `open=true`、`toggle` 事件同步将 `#tv-mobile-panel[data-open]` 设为 `"true"`、按钮 `aria-label` 切为 `"Menü schließen"`，按 `Escape` 后恢复 `open=false`、`data-open="false"`、`aria-label="Menü öffnen"`。
3. **Footer 交互与语言切换（`18` / `6911`）**：
   - 桌面 `1440` 与手机 `390`（关闭 CookieYes 底部横幅防遮挡后）：点击 `Plan with Linker` / `Planen mit Linker`（或手机 `Contact`）选项卡，`aria-selected` 从 `false` 切为 `true`，对应 panel `hidden` 变为 `false`，原激活 panel 隐藏。
   - 语言切换链接实点跳转：
     - 首页页脚切换：`https://de-linker.com/` → 点击 `Deutsch` 跳转至 `https://de-linker.com/de/`（`de-DE`）→ 点击 `Englisch` 跳回 `https://de-linker.com/`（`en-US`）。
     - 短页（草稿页）页脚切换：`/cart/` → 点击 `Deutsch` 跳转至 `/de/loesungsentwurf/`（`de-DE`）。
     - 页头切换：`/privacy-policy/` → 点击页头 `DE` 链接跳转至 `/de/datenschutz/`（`de-DE`）。
4. **Global JavaScript Code（`30`）**：
   - 全部 8 个访问场景的 DOM 均存在 `<script id="lc_script_tag" type="module">` 且 `textContent.length === 0`，符合 `docs/audit/2026-11-04-lc-global-js-partial.md` 的空槽位结论；全站 JS 行为由 `linker-header-menu`、页脚内联 `footer-app.js` 等独立资源完成，无任何运行时错误。

---

## 四、发现的问题与源码根因

### 缺陷 1（功能/路由绑定偏差）：德语商城首页 `/de/produkte/` 渲染 `6905` 而非 `6961` (`shop-page`)

- **实证现象**：
  - `https://de-linker.com/products/`（及其 `?orderby=title`、`?product-page=2`）返回 `<!-- LC DT ID: 6961 -->`（`shop-page`）。
  - `https://de-linker.com/de/produkte/`（及其 `?orderby=title`、`?product-page=2`）返回 **`<!-- LC DT ID: 6905 -->`**（`vorlage-fur-archiv-fur-beitragstyp-produkt`），**未命中 `6961`**。
  - 这与 `template-matrix.json` 中 `6961` 的 `effective_languages: ["en", "de"]` 预期及 `plugins/linker-i18n/includes/DynamicTemplates.php:20-25`（“The shop, cart, checkout and account templates are structural… an instance can hold them in English only”）的设计意图不符。
- **源码根因**：
  1. WooCommerce 的 Shop 页面同时满足 `is_archive()`（`is_post_type_archive('product')`）与 `is_shop()`。
  2. 在 `livecanvas/modules/templating.php:51-72` 中，`is_archive()` 分支先运行并调用 `lc_get_template_id('is_archive_for_post_type_product')`；在 `/de/produkte/` 请求下，Polylang 将该查询限定为 `de`，因此命中了德语产品归档模板 **`6905`**。
  3. 随后 `templating.php:89-99` 运行 `if (is_shop()) $wc_specific_template_id = lc_get_template_id('is_shop_page');`。由于 `6961`（`shop-page`）在数据库中 `pll_lang = "en"` 且没有德语孪生（`pll_translations = {"en": 6961}`），`lc_get_template_id('is_shop_page')` 在 `/de/` 下返回 `false`，于是第 98 行 `if (isset($wc_specific_template_id) && $wc_specific_template_id)` 不执行，`$template_id` 保持为 **`6905`**。
  4. 最后 `templating.php:109` 触发 `lc_modify_template_id` 过滤器，调用 `Linker\I18n\DynamicTemplates::template(6905)`（`plugins/linker-i18n/includes/DynamicTemplates.php:90-93`）：
     ```php
     if ( $template_id || Languages::SOURCE === $this->languages->current() || ! $this->languages->ready() ) {
         return $template_id;
     }
     ```
     由于传入的 `$template_id` 是 `6905`（非假值），`DynamicTemplates::template()` 直接早退返回 `6905`，永远不会回退到 `6961`（`is_shop_page`）。
- **影响说明**：当前 `6961`（`shop_page.html`）与 `6905`（`de/archive_product.html`）页面结构相同，但 `6961` 使用 `[lc_label]` 动态翻译而 `6905` 含德语硬编码标签（且二者模板身份不同、后续若仅改 `shop_page.html` 将不会反映到 `/de/produkte/`）。修复方向（供后续单独立票处理，本批不改代码）：在 `DynamicTemplates::template()` 中当 `is_shop()` 为真时优先检查是否需要覆盖归档模板回到英文 `is_shop_page`，或为 `shop_page.html` 建立并同步 Polylang 德语孪生。

### 说明 2（非缺陷但须登记的台账现象）

1. **8 个 `lc_use_template_of_slug` 模板的 `pll_lang` 均为 `"en"`**：`6967/6968`、`6969/6970`、`6971/6972`、`6973/6974` 在 DB 中均为 `pll_lang="en"`（由 `Templates::sync_page_template()` 的 `assign_source_language()` 写入），但生产实测 `-de` 模板均正常渲染于 `/de/` 页面，原因是 LiveCanvas `lc_get_template_id_by_slug()` 按 `name` 查询单篇而绕过了 Polylang 语言过滤。
2. **20 行基线 `sha256` 漂移**：`template-matrix.json` 保留的是 2026-10-22 基线哈希；2026-11-13 WP-CLI 实测这 20 行的生产最新 `post_content` 除 `6861`（DB 404 DE 模板）外，其余 19 行均与当前仓库 `plugins/linker-commerce/content/livecanvas/**/*.html` 逐字节一致。
3. **无未命中路由的孤立模板**：全部 31 个已发布模板/partial 中，除 `30`（刻意为空的 Global JS 槽位）与 `6961`（DE Shop 被 `6905` 抢占）外，其余均已在生产实测命中对应真实 URL。
