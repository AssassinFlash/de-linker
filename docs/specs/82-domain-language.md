# #82 域语言净化：Article / Catalog 概念清出

依据（只用本仓库当期裁定）：issue #82（业主 2026-10-11：域语言必须是商城与产品的身份，Article/Catalog 类概念不得存活）、`docs/audit/2026-10-11-surface-inventory.md:62`（命名沿用裁定被推翻的那条）、`AGENTS.md` §3（产品、产品分类；不说目录 catalogue / 文章 article / 篮子 basket）、`plugins/linker-i18n/data/banned-de.json`（德语禁词表既有口径）。

范围：`plugins/linker-commerce`、`services/engine`、`plugins/linker-tools` 逐文件扫描 `catalog|article`（大小写不敏感），外加注释散文、模板、CSS、`.po/.pot`。`services/genie`、`plugins/linker-i18n`、`docs/`、`tools/` 的命中列在第 6 节（不在本票范围内，防漏记）。

## 0. 两段执行

- **A 段（本票，零碰撞）**：本名录 + 引擎改名（`services/engine` 无在途线，见第 1 节）。引擎改动已在本票内执行，见第 2.7 节。
- **B 段（等在途线全部合并后触发）**：`Linker\Commerce\Catalog` 命名空间 → `Products`、CSS 类族与 DOM 锚点重映射。**本票不碰**：`includes/Catalog/` 目录此刻正被 4 条在途线（t16/t66/t68/t69）同时写入（第 1 节），改名即全面碰撞。

## 1. 在途线现状（B 段为什么必须等）——开工时实测

| 在途线 | 状态 | 与 #82 重叠的触碰面（实测） |
|---|---|---|
| t16 `t16/review-acceptance`（37b257c，已提交） | Storefront 复刻接管 | **删除** `assets/storefront.css`、`assets/storefront.js`、`templates/storefront-archive-product.php`、`templates/storefront-single-product.php`；**新建** `content/windpress/catalogue.css`、`pdp.css`、`storefront.css`、`includes/Presentation/CatalogShortcodes.php`、`template-functions.php`、`includes/Catalog/Materials.php`；改 `CatalogFilters.php`、`Templates.php`、`WindPress*.php`；像素对照按页型跑（`docs/acceptance/2026-10-11/16/`）。新 CSS 保留全部线上锚点类（其注释自陈 "the same anchor classes (`tv-woo-b2b-catalog`, `sf-card`, `pdp-*`)"）：`catalogue.css` 228 行（`sf-catalog` 124 行、`tv-woo-b2b-catalog` 126 行）、`windpress/storefront.css` 4352 行（`tv-woo-b2b-catalog` 196 行）、`pdp.css` 0 行 |
| t68 `t68/surface-close`（未提交） | /products/ 搜索框 + contact + 文档入口 | 改 `includes/Storefront/CatalogFilters.php`、`includes/Plugin.php`、`linker-commerce.php`、`languages/*.po|.pot|.mo`、`tests/php/Unit/Catalog/EngineeringFeedTest.php`、`linker-tools/includes/Genie/Entries.php`；**新建 3 个 `includes/Catalog/` 文件**：`CatalogSearch.php`、`CatalogSearchController.php`、`SearchScope.php` + `tests/php/Unit/Catalog/*` 3 个 |
| t66 `t66/compare-pages`（未提交） | /compare-products/ 重建 | 改 `includes/Presentation/Templates.php`（`Templates::catalog()` 宿主）、`Abilities/CompareProducts.php`、`tests/php/Unit/Catalog/EngineeringFeedTest.php`；**新建 `includes/Catalog/Comparison.php`、`includes/Catalog/DocumentLibrary.php`** + `tests/php/Unit/Catalog/{Comparison,DocumentLibrary}Test.php` + `content/livecanvas/{compare,faq}_page.html` |
| t69 `t69/erp-stock`（未提交） | ERP 库存通道 | 改 `includes/Storefront/CatalogFilters.php`（库存徽标/筛选）、`includes/Plugin.php`、`tests/php/Support/MocksCatalogue.php` |
| t67 `t67/observability`（未提交） | 健康告警 + 会话保留 | 改 `includes/Plugin.php`、`tests/php/Unit/PluginTest.php`（`CatalogFilters` 注册断言宿主） |
| t81 `t81/cutover-drills`（未提交） | JSON-LD + cutover | 改 `includes/Plugin.php`、`tests/php/Unit/PluginTest.php`；新建 `includes/Storefront/ProductSchema.php` |
| t80 `t80/cutover-artifacts`（未提交） | 重定向数据 + mu + 迁移 | `plugins/linker-tools/includes/Redirects.php`、`tests/php/Unit/RedirectsTest.php`（不在 #82 面内，列出以说明 linker-tools 侧也热） |
| t73 `t73/approval` | 未开工（工作树干净） | — |

结论：`includes/Catalog/` 在四条在途线上同时被改/新建（t16 删旧面、t68/t66 各加文件、t69 改 `CatalogFilters`）。命名空间改名必须等这些合并完，否则每一处都是冲突。

## 2. 现名 → 新名 全量映射表

列：**现名** / **新名** / **出现处**（当前 main `c043984` 的 `file:line`，`file` 省略前缀 `plugins/linker-commerce/` 或 `services/engine/`）/ **触碰它的在途票** / **阶段**。

### 2.1 PHP 命名空间 `Linker\Commerce\Catalog` → `Linker\Commerce\Products`

| 现名 | 新名 | 出现处 | 在途票 | 阶段 |
|---|---|---|---|---|
| `includes/Catalog/`（目录，9 类，`namespace Linker\Commerce\Catalog;`） | `includes/Products/` | `includes/Catalog/Compatibility.php:10`、`EngineeringData.php:10`、`EngineeringFeed.php:10`、`EngineeringFeedController.php:10`、`Faqs.php:10`、`SelectionFactSet.php:10`、`SelectionFacts.php:10`、`SelectionFactsController.php:10`、`Units.php:10` | t66/t68 各在本目录新建文件 | B |
| `use Linker\Commerce\Catalog\…`（消费方） | `…\Products\…` | `includes/Plugin.php:15,16`、`Storefront/CatalogFilters.php:12,13`、`Storefront/ProductView.php:14,15`、`Admin/FiguresMetaBox.php:12,13`、`Admin/FaqsMetaBox.php:12,13`、`Abilities/CheckCompatibility.php:12,13,14`、`Abilities/GetProduct.php:12,13`、`Abilities/SearchProducts.php:12,13,14`、`Abilities/CompareProducts.php:12,13`、`Presentation/Shortcodes.php:12` | t68/t69/t81 改 `Plugin.php`；t68 改 `FaqsMetaBox` | B |
| `Catalog\SelectionFactsController`（命名空间相对引用） | `Products\SelectionFactsController` | `linker-commerce.php:29` | t68 改本文件 | B |
| `Catalog\EngineeringFeedController`（同上） | `Products\EngineeringFeedController` | `linker-commerce.php:30` | t68 | B |
| `Linker\Commerce\Catalog\SelectionFacts`（内联 FQN，非 `use`） | `…\Products\SelectionFacts` | `templates/storefront-archive-product.php:189` | t16 删除本文件；新宿主 = t16 的 `CatalogShortcodes.php` | B |

### 2.2 PHP 类与测试命名空间

| 现名 | 新名 | 出现处 | 在途票 | 阶段 |
|---|---|---|---|---|
| `CatalogFilters` | `ProductFilters` | 定义 `includes/Storefront/CatalogFilters.php:26`；用 `includes/Plugin.php:17,65`；`templates/storefront-archive-product.php:17`；测试 `tests/php/Unit/PluginTest.php:18,62` | **t68/t69 改 `CatalogFilters.php` 本体**；t16 改 `Plugin.php`+`Templates`；t67/t81 改 `PluginTest.php` | B |
| `CatalogSorting` | `ProductSorting` | 定义 `includes/Gating/CatalogSorting.php:17`；用 `includes/Gating/Module.php:35,41`、`includes/Plugin.php:121`；测试 `tests/php/Unit/Gating/CatalogSortingTest.php:12,18,20,22,49,65`、`tests/php/Unit/Gating/ModuleTest.php:12,36` | 无在途线触碰 | B |
| `CatalogSortingTest`（文件名+类名） | `ProductSortingTest` | `tests/php/Unit/Gating/CatalogSortingTest.php:22`（另见 2.2 上行） | 无 | B |
| `CatalogText` | `ProductText` | 定义 `includes/Abilities/CatalogText.php:17`；用 `Abilities/GetProduct.php:126,135,136,138,139,140,174`、`Abilities/SearchKnowledge.php:122`、`Abilities/SearchProducts.php:217,403,404,430,545,546`、`Abilities/CompareProducts.php:134,149,150`；测试 `tests/php/Unit/Abilities/SearchProductsTest.php:23`（`@covers`）；跨树注释 `plugins/linker-tools/src/genie/api/product.ts:3` | t66 改 `CompareProducts.php`；t68 改 `SearchProducts` 相邻面 | B |
| `Linker\Commerce\Tests\Unit\Catalog`（测试命名空间，8 文件） | `…\Tests\Unit\Products` | `tests/php/Unit/Catalog/{Compatibility,EngineeringData,EngineeringFeed,Faqs,SelectionFacts,SelectionFactsController,SelectionFactsLiveCatalogue,Units}Test.php:10` | t66/t68 各在本目录新建测试 | B |
| `LiveCatalogue` | `LiveProducts` | 定义 `tests/php/Support/LiveCatalogue.php:20`；用 `tests/php/Unit/Catalog/SelectionFactsLiveCatalogueTest.php:14,200,214,261,272,275,380,455,477`、`tests/php/Unit/Abilities/SearchProductsTest.php:13,81`、`tests/php/Integration/SelectionFactsRestTest.php:14,68,79` | t68 改 `tests/php/Unit/Catalog/*` 相邻面 | B |
| `LiveCatalogueTest`（文件名+类名） | `LiveProductsTest` | `tests/php/Unit/Catalog/SelectionFactsLiveCatalogueTest.php:20,32` | t68 | B |
| `MocksCatalogue`（trait） | `MocksProducts` | 定义 `tests/php/Support/MocksCatalogue.php:3,12,24`；用 `tests/php/Unit/Abilities/{SearchProductsTest:14,27,CheckCompatibilityTest:13,24,CompareProductsTest:13,24,GetProductTest:13,24}` | t66/t69 改本文件 | B |
| `mock_catalogue()` | `mock_products()` | `tests/php/Support/MocksCatalogue.php:51`；调用 `SearchProductsTest.php:82,133,156,178,200`、`CheckCompatibilityTest.php:57,94`、`CompareProductsTest.php:38,58`、`GetProductTest.php:38,63` | t66/t69 | B |
| `Templates::catalog()` | `Templates::paths()` | 定义 `includes/Presentation/Templates.php:59`；用同文件 `:81`、`includes/Presentation/WindPress.php:51`、`includes/Presentation/WindPressCache.php:76`、`includes/Cli/PresentCommand.php:271`；测试 `tests/php/Unit/Presentation/TemplatesTest.php:28,29,33,35,169,176,178,179,186,187,188`、`tests/php/Unit/Presentation/WindPressCacheTest.php:80` | **t16/t66 改 `Templates.php`**；t16 改 `WindPress*.php`、`PresentCommand` | B |

### 2.3 CSS 类族、DOM 锚点与 data 属性（宿主 `assets/storefront.css`；B 段宿主改为 t16 的 `content/windpress/{catalogue,pdp,storefront}.css`）

`catalog-*` → `product-*` 一律 1:1 字母替换（issue 表）。

| 现名 | 新名 | 出现处（`assets/storefront.css` 行号） | 标记方 | 在途票 |
|---|---|---|---|---|
| `#tv-woo-b2b-catalog`（DOM id，**概念词最大聚集点：CSS 133 处**） | `#linker-products` | `31, 32, 40, 43, 50, 57, 58, 63, 69, 70, 77, 84, 91, 98, 108–127, 137–141, 143–146, 153–173, 176–191, 197, 203–230, 234–245, 249, 1586, 1595, 1598, 1601, 1605, 1619`；标记方 `templates/storefront-archive-product.php:56`、`assets/storefront.js:49` | t16 删两文件并重写为 windpress CSS + `CatalogShortcodes.php`；模板/JS 由 t16 的重写承接 |
| `.sf-catalog`（130 处） | `.sf-products` | `32, 40, 43, 50, 57, 58, 63, 69, 70, 77, 84, 91, 98, 108–127, 137–141, 143–146, 153–173, 176–191, 197, 204–230, 234–245, 1586, 1595, 1598, 1601, 1605, 1619`；标记方 `templates/storefront-archive-product.php:56` | 同上 |
| `.catalog-section` | `.product-section` | 标记方 `templates/storefront-archive-product.php:57`（CSS 无规则） | t16 |
| `.catalog-layout` | `.product-layout` | CSS `110, 197, 217`；标记方 `templates/storefront-archive-product.php:58` | t16 |
| `.catalog-results` | `.product-results` | 标记方 `templates/storefront-archive-product.php:168`（CSS 无规则） | t16 |
| `.catalog-grid` / `#catalog-grid` | `.product-grid` / `#product-grid` | CSS `126, 225, 238`；标记方 `templates/storefront-archive-product.php:185, 254` | t16 |
| `.catalog-filter-close` / `#catalog-filter-close` | `.product-filter-close` / `#product-filter-close` | CSS `1598, 1619`；标记方 `templates/storefront-archive-product.php:60`；JS `assets/storefront.js:54` | t16 |
| `#catalog-filter-open` / `.catalog-filter-open-btn` | `#product-filter-open` / `.product-filter-open-btn` | CSS `216, 1601, 1605`；JS `assets/storefront.js:71` | t16 |
| `#catalog-filter-apply` | `#product-filter-apply` | CSS `223`；标记方 `templates/storefront-archive-product.php:164`；JS `assets/storefront.js:55` | t16 |
| `.catalog-filter-actions` | `.product-filter-actions` | CSS `221, 222`；标记方 `templates/storefront-archive-product.php:162` | t16 |
| `.catalog-filter-open`（body 状态类，注意与上面 `#catalog-filter-open` 同名不同用法） | `.product-filter-open` | JS `assets/storefront.js:62, 66` | t16 |
| `.catalog-mobile-actions` | `.product-mobile-actions` | CSS `214, 215` | t16 |
| `.catalog-article-dialog` | `.product-dialog` | CSS `228`（标记方 0 处，见 2.9） | t16 |
| `.catalog-article-heading` | `.product-dialog-heading` | CSS `229`（标记方 0 处） | t16 |
| `.catalog-article-close` | `.product-dialog-close` | CSS `230`（标记方 0 处） | t16 |
| `.card-exact-article` | `.card-product` | CSS `153, 154, 180, 185, 186, 245`（标记方 0 处） | t16 |
| `.card-article-picker` | `.card-product-picker` | CSS `146, 147, 180, 181, 245`（标记方 0 处） | t16 |
| `[data-compare-article]` | `[data-compare-product]` | CSS `249, 250`（标记方 0 处） | t16 / t66（对比页重建） |
| `[data-linker-catalog-filter]` | `[data-linker-product-filter]` | 标记方 `templates/storefront-archive-product.php:59` | t16 |
| 注释 `/* ===== Catalogue (archive) ===== */` | `/* ===== Products (archive) ===== */` | CSS `28` | t16 |

CSS 同步要求（issue 原文）：改名后**必须重跑像素门**，选择器重映射 1:1，像素应零变化；变即漏改。

### 2.4 模板 / 短代码 / 脚本散文

| 现名 | 新名 | 出现处 | 在途票 | 阶段 |
|---|---|---|---|---|
| `templates/storefront-archive-product.php:6` "catalogue the site serves today" | "product pages the site serves today" | 同上 | t16 删除该文件（新宿主 `CatalogShortcodes.php`） | B |
| `assets/storefront.js:43` "the catalogue the site serves today opens" | "the product page …" | 同上 | t16 删除该文件（新宿主 `catalog-ui`/`pdp-ui.js`） | B |
| `includes/Admin/FaqsMetaBox.php:106,108,138` 局部变量 `$catalogue`（= 文档列表） | `$documents` | 同上 | t68 改本文件 | B |
| `includes/Gating/CommerceState.php:23,24` "the live catalogue's data" | "the live product data" | 同上 | 无 | B |
| `includes/Account/InquiryList.php:27` "live catalogue data" | "live product data" | 同上 | 无 | B |
| `includes/Abilities/SearchProducts.php:210` "the published catalogue"、`:663` `@param int[] $ids Catalogue.` | "the published products" / `$ids Products.` | 同上 | 无（t68 改相邻面） | B |
| `tests/php/Unit/Gating/CommerceStateTest.php:42` "live catalogue data" | "live product data" | 同上 | 无 | B |
| `tests/php/Unit/Abilities/SearchProductsTest.php:31` 引用研究文档路径 | 见 3.6（证据文档改名另议，注释保持字面路径） | 同上 | 无 | — |
| `tests/php/Unit/Catalog/SelectionFactsLiveCatalogueTest.php:22,23` | 同上 | 同上 | t68 改相邻面 | — |
| `tests/fixtures/load-live-products.php:7` "reproduces the catalogue" | "reproduces the products" | 同上 | 无 | B |
| `tests/php/Support/MocksCatalogue.php:3` "Live-catalogue products" | "Live-product products" → "The live products" | 同上 | t66/t69 改本文件 | B |
| `tests/php/Unit/Catalog/CompatibilityTest.php:68` "every tower takes the battery base article" | "…the battery base module…"（英文散文里的 article ≠ 商品，见 3.5/3.8） | 同上 | 无 | B |

### 2.5 语言文件

| 现名 | 新名 | 出现处 | 阶段 |
|---|---|---|---|
| `languages/*.pot`、`languages/*-de_DE_formal.po` 的 `#:` 引用行（`includes/Catalog/*.php`、`includes/Storefront/CatalogFilters.php` 路径） | 随文件移动重新生成，非手改 | `.pot:274–364, 912, 919–931`；`.po:287–403, 1024, 1031–1043` | B |
| msgid/msgstr 本体 | **不动**（无一含 catalog/article 概念；德语 `Artikelnr./Artikelnummer:` 属豁免，见 3.2） | `.po:1822, 1848` | — |

### 2.6 PHP 文件名

| 现名 | 新名 | 触碰它的在途票 | 阶段 |
|---|---|---|---|
| `includes/Storefront/CatalogFilters.php` | `includes/Storefront/ProductFilters.php` | t68、t69（改本体） | B |
| `includes/Gating/CatalogSorting.php` | `includes/Gating/ProductSorting.php` | 无 | B |
| `includes/Abilities/CatalogText.php` | `includes/Abilities/ProductText.php` | 无 | B |
| `tests/php/Unit/Gating/CatalogSortingTest.php` | `…/ProductSortingTest.php` | 无 | B |
| `tests/php/Unit/Catalog/SelectionFactsLiveCatalogueTest.php` | `…/SelectionFactsLiveProductsTest.php` | t68（改相邻面） | B |
| `tests/fixtures/live-catalogue-facts.csv` | `tests/fixtures/live-products-facts.csv`（引用点 `tests/php/Support/LiveCatalogue.php:26`） | 无 | B |

### 2.7 引擎（`services/engine`）——**A 段，本票已执行**

引擎无在途线（第 1 节），故整条链在本票内改名。现名 → 新名：

| 现名 | 新名 | 出现处（改名前的行号） | 处置 |
|---|---|---|---|
| `src/linker_engine/catalog.py`（模块） | `src/linker_engine/products.py` | 文件本身 | 已改（`git rm` + 新 `products.py`） |
| `src/linker_engine/products.py`（原文件：`Engine`、`ref`、`docs`、`release`、`documents_of`） | `src/linker_engine/engine.py` | 文件本身；引用方 `app.py:40`、`commercial.py:33`、`residential.py:44`、`tests/{conftest.py:23,test_commercial.py:7,test_report.py:10,test_residential.py:7}` | 已改 |
| `class Catalog` | `class Products` | `src/linker_engine/catalog.py:253,262,275` | 已改 |
| `from .catalog import …` | `from .products import …` | `src/linker_engine/{app.py:26,products.py:13,compatibility.py:20,commercial.py:21,stacking.py:16,residential.py:17,strings.py:17,eligibility.py:17}`、`roof/service.py:19`、`roof/packing.py:20` | 已改 |
| `Engine.catalog`（字段） | `Engine.products` | `src/linker_engine/products.py:23`；调用 `app.py:80,88,176`、`commercial.py:173,208,225,281`、`residential.py:148,229,297,307,352,739,741,805` | 已改 |
| `catalog`（pytest fixture） | `products` | `tests/conftest.py:21,40,41,57,58`；消费 `tests/{test_catalog,test_roof,test_strings}.py` 全部 | 已改 |
| `tests/test_catalog.py` | `tests/test_products.py` | 文件本身 | 已改名 |
| `products.py` 散文 "the same catalogue"（`:4,21,53,54`） | "the same products" / "The loaded products" / "when the product data carries it" | `src/linker_engine/products.py`（新宿主为 `engine.py`） | 已改 |
| `tests/test_residential.py:1` "the real catalogue fixture" | "the real product fixture" | 同上 | 已改 |

**为什么源模块也必须改、以及为什么是这两个名字**：issue 只列了 `test_catalog.py → test_products.py`，但文件内 `from linker_engine.catalog import Catalog`、`Catalog` 类型、`catalog` fixture 三个概念词都指向源头，只改文件名等于概念词原地留存，grep 断言守不住。改成 `products.py` 时两件事决定了落地形状：

1. **`src/linker_engine/products.py` 已存在**（承载 `Engine`、`ref`、`release`、`docs`、`documents_of`），`products` 这个名字已被占用；
2. **两文件不能合并**：`compatibility.py:20` 依赖 `catalog.py` 的 `validate`，而 `products.py` 依赖 `compatibility.py` —— 合并会成环（`products → compatibility → products`），`from` 在文件顶部，环在导入期直接炸；ruff 的 E402 也不许把导入挪到定义之后。

于是把被占用的那个名字让给产品数据：`catalog.py → products.py`（`Product`、`PvModule`、`Products`、`FeedError`、`validate`），原 `products.py → engine.py`（`Engine` 及其答案装配片段，模块名即它定义的类）。依赖方向不变、无环：`products ← compatibility ← engine`。这样做也让 `tests/test_products.py` 与自己的模块同名，且与 PHP 侧"命名空间 `Products` 收全部产品类"的形状一致。

### 2.8 数据与内容（自有代码外的概念词）

| 现名 | 新名 | 出现处 | 阶段 |
|---|---|---|---|
| `data/compatibility.json:871` 英文条件 "one battery base article" | "one battery base module"（英文散文用 item/module，不用 article） | 同上 | 属内容改动，走文案对抗评审；不是代码改名 |
| `data/compatibility.json:5131` 英文条件 "an article of its own" | "an item of its own" | 同上 | 同上 |
| `data/compatibility.json:872,5132` 德文条件 "als eigenen Artikel" / "ein eigener Artikel" | **不改**（德语商业用语，见 3.2） | 同上 | 豁免 |

### 2.9 生成产物与"零标记方"说明

- `plugins/linker-tools/build/*.js`（提交在案）含 `<article>` 编译结果；由 `just build` 重新生成，无手改点（3.4）。
- `.catalog-article-dialog`/`-heading`/`-close`、`.card-exact-article`、`.card-article-picker`、`[data-compare-article]` 在新树**没有任何标记方**（`grep -rn` 除 `assets/storefront.css` 与审计文档外 0 命中）——它们是线上 CSS 搬字节时带进来的死选择器。改名只动选择器，像素门不会因此变化；B 段可顺带核对是否随 t16 的新 CSS 一并留存。

## 3. 豁免清单（逐条核对）

### 3.1 Woo 原生 API 名——保留，改名即分叉 Woo

| 名字 | 出现处 |
|---|---|
| `woocommerce_catalog_orderby` | `includes/Gating/Module.php:65`；`includes/Gating/CatalogSorting.php:27`（docblock）；`tests/php/Unit/Gating/ModuleTest.php:55` |
| `woocommerce_get_catalog_ordering_args` | `includes/Gating/Module.php:66`；`includes/Gating/CatalogSorting.php:40`（docblock）；`tests/php/Unit/Gating/ModuleTest.php:56` |
| `get_catalog_visibility` | `plugins/linker-i18n/includes/Woo/Projection.php:85`（本票三树之外，列此证明该类 API 的口径） |
| `CatalogVisibility` | `plugins/linker-commerce/vendor/php-stubs/woocommerce-stubs/woocommerce-stubs.php:127169`（`Automattic\WooCommerce\Enums\CatalogVisibility`），`plugins/linker-i18n/vendor/php-stubs/…` 同；**只存在于 vendor 的 Woo 官方 stub 包，非自有代码**（issue 提到的这个名字确实在树里，但来源是第三方的） |

### 3.2 德语商业用语 `Artikelnr.` / `Artikel`——保留

- `languages/linker-commerce-de_DE_formal.po:1822` `msgid "Item no."` → `msgstr "Artikelnr."`；`:1848` `msgid "Item number:"` → `msgstr "Artikelnummer:"`。**线上冻结文案**（`templates/storefront-archive-product.php:229` 的 `Item no.`、`storefront-single-product.php:108` 的 `Item number:` 走这两个 msgid），Artikelnummer = 货号，德语电商标准用语。
- `languages/linker-commerce-de_DE_formal.mo` 为编译产物，与 `.po` 同步。
- `data/compatibility.json:872,5132` 德文条件里的 "Artikel"（"ein eigener Artikel" = 单独的货件）同属市场语言，非旧代码概念。
- `tests/php/Unit/Vocabulary/OverridesTest.php:83` 的德语复数形 `'%1$s für %2$s Artikel'`（测 `Vocabulary\Overrides::ngettext`）同上。
- `plugins/linker-i18n/data/banned-de.json:2` 已写明："'Artikel' is not listed: German legal texts cite 'Artikel 6 DSGVO'." —— 既有口径与本豁免一致。
- `plugins/linker-tools/src/configurator/i18n.test.ts:94` 的门 `expect( text ).not.toMatch( /Warenkorb|Kasse|Artikel|Katalog/ )` 是**工具应用内文案**的护栏（比站点更严），保留不动；它不覆盖站点 `.po`。
- 若业主要求连线上德语文案（Artikelnr.）一起换，属内容变更，另走裁定与文案评审——不在本票。

### 3.3 德语语法冠词 `de_article`——保留（同形异义）

`services/genie/eval/judges/src/linker_judges/templates.py:20,92,104,105,129` 的 `de_article` 是德语**语法冠词** der/die/das（"Wie hoch ist {de_article} {de} …"），与"产品=Article"的概念无关。位置在三树之外，列出以防下一轮误伤。

### 3.4 HTML `<article>` 元素与 ARIA role `article`——保留

`<article>` 是 HTML 标准元素、`role="article"` 是 ARIA 标准角色；这是平台词汇，不表"产品=文章"。改名会破坏语义标签与可访问性。

| 位置 | 出现处 |
|---|---|
| 归档模板 / 产品卡 | `templates/storefront-archive-product.php:202, 250` |
| LiveCanvas 模板 | `content/livecanvas/archive_product.html:34, 55`；`shop_page.html:24, 45` |
| React 产品卡 | `src/shared/ProductCard.tsx:65, 124` |
| 测试（ARIA 选择器，三树内） | `src/shared/ProductCard.test.tsx:32`；`src/genie/CardStates.test.tsx:88,119,140`；`src/configurator/App.test.tsx:81,117`；`src/configurator/App.stories.tsx:153`；`tests/e2e/configurator.spec.ts:27,45,126,145`；`bin/capture-configurator.mjs:153` |
| 构建产物（生成） | `build/genie.js`、`build/configurator.js`（各 1 行，`<article>` 编译结果） |

### 3.5 外部文献 URL——保留

`src/linker_engine/rules.py:217` `https://journals.riverpublishers.com/index.php/DGAEJ/article/download/30737/22483/121041`、`:238` `…/article/view/30737/22485` —— 期刊站点自身的 `/article/` 路径，改了链接就断。规则来源引用不改。

### 3.6 证据文档路径与托管文档文件名——保留

| 名字 | 为什么不改 |
|---|---|
| `docs/research/2026-10-09/old-repo-live-catalogue-facts.md`（被注释引用：`tests/php/Unit/Catalog/SelectionFactsLiveCatalogueTest.php:23`、`tests/php/Unit/Abilities/SearchProductsTest.php:31`、`includes/Gating/CommerceState.php:24`、`includes/Account/InquiryList.php:27`、`src/linker_engine/...` 无） | 证据文档的**标题即文件名**，是线上现状/旧系统行为的记录，不是代码概念；改文件名会断掉跨文件引用。全树 grep 断言只覆盖自有代码/模板/样式（第 4 节），文档不在此列 |
| `chint_dtsu666_catalog_en.pdf`（托管厂商文档） | `services/engine/tests/fixtures/feed.json:8345,8354,8363,8380,8396,8405,8414,8422,8430,8439,8447,8456,8464,8472,8480,8488,8496,8504,8512,8520,8521`（21 行）；三树外 `tools/migrate/8-engineering.json:4164,4167,7781,7782` | 是我们自己托管的厂商文档原文件名，是**文件事实**（citations 指向它），不是代码概念；改名要连带改媒体 URL 与所有引用，属另一件事 |
| `tests/fixtures/live-products-2026-10-09.json` | 文件名已无概念词（正面例子，无需处理） |

### 3.7 引用被禁词的政策注释——保留

`includes/Vocabulary/Terms.php:66` `// Products (AGENTS.md §2, 2026-10-05: Product / Model / Series, never "article").` 是**记录禁令本身**的注释；它引用被禁的词以说明不许用。删除或改写会抹掉这条口径的出处，保留。

### 3.8 保留裁定明确点名的非概念携带物（不属 #82）

`#tv-storefront-pdp`（`assets/storefront.css:250`）、`--dlk-radius` 变量、`~/.config/terravolt-builder/` 凭据路径、REST 命名空间 `linker/v1`：`docs/audit/2026-10-11-surface-inventory.md:62` 明写"REST 命名空间与凭据路径保留不变"；其余三项不含 `article|catalog` 词根，不在 #82 面内——列出以免被当作已处理。

### 3.9 第三方与生成物

`vendor/`（含 Woo 官方 stub 包 `woocommerce-stubs/woocommerce-stubs.php:127169` 的 `Automattic\WooCommerce\Enums\CatalogVisibility`）、`node_modules/`、`build/`、`.venv/`、`__pycache__/`、`.mypy_cache/`、`.pytest_cache/` 不是自有代码。

## 4. 全树 grep 断言（B 段落地的判据）

本票 A 段落地的实测命令与结果（B 段用同一条命令收口）：

```
grep -rniE 'catalog|article' plugins/linker-commerce services/engine plugins/linker-tools \
  --exclude-dir=node_modules --exclude-dir=build --exclude-dir=vendor \
  --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=.mypy_cache \
  --exclude-dir=.pytest_cache
```

A 段执行后 `services/engine` 只剩 2 个文件命中，均为第 3 节豁免（`tests/fixtures/feed.json` 21 行 = 托管文档名；`src/linker_engine/rules.py:217,238` = 期刊 URL）。`plugins/linker-commerce` 与 `plugins/linker-tools` 的命中等待 B 段。

只允许出现第 3 节列举的豁免（Woo 钩子名、`Artikelnr./Artikelnummer/Artikel`、`<article>`/`role="article"`、期刊 URL、托管文档名、证据文档路径、禁令注释）。B 段把这个断言与豁免白名单落成可重跑的脚本，避免"人眼比对"。

## 5. 验收与顺序

1. B 段开工前提：t16/t66/t67/t68/t69/t80/t81/t73 全部合并，`git status` 干净。
2. B 段改名顺序：先 `includes/Catalog/` 目录与命名空间（含 `use` 与内联 FQN），再 PHP 类名与文件名，再测试命名空间/支持类/夹具，再 `Templates::catalog()`，最后 CSS 类族与 DOM 锚点（CSS + 模板 + JS 同一提交）。
3. CSS 改完必须重跑像素门（EN/DE × 1440/390，按页型逐一对照），掩膜外差异数必须为 0；任何差异即选择器漏改。
4. `just check && just test` 全绿。
5. 全树 grep 断言只剩豁免。

## 6. 三树外的命中（不在本票范围，防漏记）

| 位置 | 性质 |
|---|---|
| `services/genie/eval/judges/construction.jsonl`（80 行）、`.../src/linker_judges/build.py:121,132,142,291,292,372` | 评测用例的 `kind: "catalogue"`（= 取自线上目录的事实题）与对研究文档路径的引用 |
| `plugins/linker-i18n/data/banned-de.json:2,3` | 德语禁词表本体（`Katalog*` 是禁用词），护栏 |
| `plugins/linker-i18n/includes/Woo/Projection.php:85` | `get_catalog_visibility`（Woo 原生） |
| `plugins/linker-i18n/tests/fixtures/live/{pages,posts,products}.json` | 线上内容快照（数据） |
| `tools/migrate/8-engineering.json` | 迁移数据里的托管文档 URL |
| `docs/`（acceptance、faq、research、specs、audit） | 证据与裁定记录 |

## 变更记录

- 2026-10-11 首版（A 段）：全量名录 + 引擎改名执行。更正 issue #82 的量化：引擎侧泄漏不止 `test_catalog.py`，还有 `src/linker_engine/catalog.py` 与 `class Catalog`（A 段一并对齐）；CSS 侧最大聚集点 `#tv-woo-b2b-catalog`（133 处）也未被 issue 表列出，已补入 2.3。
