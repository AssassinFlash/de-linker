# #66 旧工具页处置：对比页重建、Advisor 跳转、文档库页

依据：`docs/audit/2026-10-11-surface-inventory.md` GAP-3/4/5 与业主 2026-10-11 改裁定（compare 独立页由 301 改为重建）。本规格随实现写，是本票交付的一部分：三件套的原生优先穷尽证明（AGENTS 2026-10-11）、目录卡与浮动芯片的集成点。

## 1. /compare-products/（en / de）——重建

**照旧逻辑**（线上实测 2026-10-11，`https://de-linker.com/compare-products/?ids=6521,6522,6523`）：目录卡上的勾选按钮 → 浮动芯片显示已选数量 → 独立页表格；上限 4 个型号；选择态存 sessionStorage（有序商品 ID，只有 ID）；对比页的地址（`?ids=1,2,3`）是这条选择的权威——打开页面即把服务端规范化后的列表写回标签页，所以刷新、收藏与分享都成立。

**数据 = SelectionFacts 图值 + 产品的技术表，一个装配、两个入口。** `Linker\Commerce\Catalog\Comparison::of()` 是唯一的装配：

- 列：按地址给定的顺序，已发布商品，取标题/链接（按页面语言，#9 的翻译对象）、SKU、图、价格（#11 的 `CommerceState` 规则，看不到价时说同一句话）、有货与否。
- `rows`：**#7 的选择事实**，按设备类取行（逆变器侧 4 行、电池侧 3 行，互不混合；与 `linker/compare-products` ability 的行集、标签逐字一致）。unknown 是一等值，页面印破折号。
- `specs`：各商品**自己的技术表**（`ProductView::spec_groups()`，即 `linker_specs` 一旦 #8 写入、之前读旧数据的那一个读取方）按标签取并集，某商品没写该行就空着。

`linker/compare-products` ability 的 `products` / `rows` 现在由同一个 `Comparison::of()` 投影出来（输入输出 schema 不变，测试锁定），所以 Genie 与页面不可能各算一套。

**LC 承载**：对比页是普通页面，模板用 LiveCanvas 自己的"每页选择"机制——页面的 `lc_use_template_of_slug` 元值（`modules/templating.php` 的 singular 分支）指向模板文章的 slug。模板文章由 `present` 从 `content/livecanvas/compare_page.html`（en）与 `content/livecanvas/de/compare_page.html`（de）建立，slug 分别是 `linker-compare` / `linker-compare-de`；`Templates::assign_pages()` 把两个页面分别指派到各自语言的模板。这两页不是 Woo 页型，所以不用 `is_*` 元值（那会命中所有页面）。

**三件套原生优先——穷尽证明**（每一条都试过，才落到自定义代码）：

1. **LC 原生 tag**：表格的行列来自访客给定的有序 ID 列表（`?ids=`）而不是文章查询，`lc_loop` 只迭代主查询；`lc_the_cf` 读当前文章的自定义字段；`lc_wp_func` 只调无参函数；`lc_if` 只能判断已存在的函数——没有任何 LC tag 能按访客给的 ID 顺序建出"一列一商品"的表，也没有 tag 能读 sessionStorage。芯片的显示/计数/地址是浏览器状态，LC 侧没有对应物。
2. **Woo 原生**：WooCommerce 没有对比功能（不是核心能力，也不装付费插件）；`[products]` 短代码按查询出卡片，不按 ID 顺序出列。价格、有货与否、SKU、图仍走 Woo 自己的取值（`get_price_html`/`is_in_stock`/`get_sku`/`get_the_post_thumbnail_url`）与 #11 的价格门。
3. **WindPress**：样式词汇仍是 Tailwind 类；本票的新类经同一个 provider 进扫描面（见 §4），没有第二条构建。

自定义代码因此只有两处，都是数据装配：`Comparison`（装配）与 `ComparePage`（表片段、芯片、地址规范化、选择态脚本）。**零内联样式、零设计决策**（表片段只输出语义标记与类名）。

## 2. /linker-advisor/（de /linker-berater/、/de/linker-advisor/）——301 → 目录

Advisor 整页是旧助手的整页形态；助手现在是 Genie（每页常驻 dock，产品页与目录页有芯片），所以该页没有自己的后继页，301 到商品目录（en → `/products/`，de → `/de/produkte/`）。`Redirects::RETIRED` 增加三条。`/de/linker-berater/` 是线上德语 sitemap 的地址，`/de/linker-advisor/` 是旧插件同样解析的"英语 slug 加 /de/"别名（与 `/de/design-canvas/` 同一先例）。

## 3. /faq-download/（en / de）——静态目录化

**保 URL**（en `/faq-download/`、de `/de/faq-download/`，页面对象不动）；**内容冻结用现有内容**；工作台 JS 随旧插件死亡，页面必须自己成立（无脚本即完整）。同样是 LC 每页模板（slug `linker-faq` / `linker-faq-de`）。

页面由三段组成：

- **文档目录**：`[linker_document_register]`（`Catalog\DocumentLibrary` 的读取）。一行一个文件，跨商品去重（同一文件被多个商品引用只出现一次并列出覆盖的商品），带类型、语言、"覆盖 N 个商品"与下载链接。文档来自**产品页自己的文档读取方**（`ProductView::downloads()`，即 `_linker_documents` 一旦 #8 写入、之前读旧数据的那一个），所以目录与产品页不可能互相矛盾。
- **产品问答**：`[linker_product_answers]`。答案来自 #15 的字段（`Faqs::of()`，德语页读 `question_de`/`answer_de`），字段空时回落产品页的旧问答列表；每条带产品链接与其引用的文档页。
- **下单前规则**：现有页面的 16 条 B2B 问答（5 类）逐字带进模板（冻结内容），`<details>` 静态展开，无脚本。

**去掉的**：hero 的六个筛选快捷片（`data-rd-quick`，工作台的一部分，无 JS 即死）与工作台搜索；其工作由 Genie（常驻 dock，`search-knowledge`）承接（GAP-4 的裁定）。**产品数据在源语言商品上**：文档与 FAQ 字段只在英文商品上，德语商品是翻译孪生——目录读数走 #7 事实使用的同一个孪生交换（`linker_commerce_facts_product_id`），标题与链接按页面语言取。

## 4. 扫描面与锚类

`Templates::catalog()` 现在也列出两个页型的四个模板文件，所以 WindPress 的 compile provider（`include/Presentation/*.php` + `content/livecanvas/**`）把它们和表片段一起扫描，`present` 的备份/回滚与 `WindPressCache` 的新鲜度检查也覆盖它们。锚类增加 `overflow-x-auto`、`object-contain`、`gap-8`——三个都只出现在新的片段/模板里，缺一个就说明这次编译没看见新页（硬门）。

## 5. 目录卡与浮动芯片：集成点（留给 #16 模板 PR）

本票交付**选择态脚本、芯片、页面全部**；卡上的挂载方式如下，卡模板（`shop_page.html` / `archive_product.html` / `single_product.html`，归 #16 重建）落地时照此接：

- 卡上的勾选控件（每个商品一个）：

  ```html
  <button type="button" data-compare-article="123">
    <span data-compare-label>Compare</span>
  </button>
  ```

  `data-compare-article` 的值是商品 ID；标签文字归卡模板（线上是 `+`，德语 `Vergleichen`）。脚本只写状态，不写样式也不写文字：选中即 `data-compare-selected="true"` 与 `aria-pressed="true"`，选满 4 个后未选中的控件 `disabled` 且带 `data-compare-limit="reached"`。选中态的样式由卡模板的类 + WindPress 规则决定（选择器挂 `[data-compare-selected="true"]`）。
- 浮动芯片：`[linker_compare_chip]`。它在目录页与产品页**已经**经 `wp_footer` 自行出现（与 Genie dock 同一路数，隐藏到标签页有选择为止），所以模板不改也生效；模板若要自己放，就用这个短代码，别抄标记。
- 页面：`/compare-products/` 已由页面的 `lc_use_template_of_slug` 接好，卡模板不需要知道它。

## 6. 附带修复（本轮发现，本轮修）

**WindPress 编译停在 LiveCanvas provider 的扫描响应上。** 现象：`just windpress-compile` 300 秒无 `cache/store`，浏览器 worker 报 `o.contents is not iterable`；源码定位（`windpress/assets/dist/assets/worker-1JLIzxvG.js` 第 41 行 8440 列）是它把某个 provider 的响应当 JSON 解析后取 `contents`。逐 provider 复跑（临时用管理员会话按 worker 的同一顺序请求 `admin/settings/cache/providers/scan`）证实：**livecanvas 的第 5 批响应不是 JSON**，正文以 `\n\t<h2>Additional information</h2>\n\n{...}` 开头——即 LiveCanvas provider 对单品模板执行 `do_shortcode()` 渲染时，`[lc_wc_product_tab_*]` 在没有商品上下文的情况下把标记泄漏到 JSON 之前，worker 解析失败。修复走官方过滤器：`WindPress::render_raw()` 挂在 `f!windpress/integration/livecanvas/compile:get_contents.render`，对 `lc_dynamic_template` 一律返回 false——模板按原文扫描（类名本来就在原文里），运行期由短代码打印的类由本插件自己的 provider 覆盖。修复后 `just windpress-compile t66` 通过：`cache recompiled (1783954645 -> 1791717446), anchor classes present`，编译产物 205 KB → 350 KB。这是 #54/#59 那条链路上的既有缺陷（线上编译缓存停在 2026-07-13，即编译一直是坏的），本票撞上并修掉，不是本票引入。

## 7. 发现但不在本票范围（留档）

- **本地快照缺商品特色图**：装入后的库 `wp_postmeta` 里没有一行 `_thumbnail_id`（`SELECT COUNT(*) FROM wp_postmeta WHERE meta_key='_thumbnail_id'` = 0），而快照 dump 里有（例：`(45427,6528,'_thumbnail_id','6500')`，本机 meta_id 45427 不存在）。后果：对比表与目录卡的图片列在本机是空的（线上有图），代码路径与线上相同（`get_the_post_thumbnail_url`）。归 #6 的 load/anonymize 链路。
- **德语商品的文档与 FAQ 字段**：数据只在英文商品上（德语商品是翻译孪生），本票的目录读数按 #7 的孪生交换取源语言商品；产品的技术表标签/值是线上继承的产品数据，本机为英文（线上德语由被拆掉的运行时翻译提供）。要德语产品数据，#8 的 `_linker_documents`/`linker_specs` 与 #15 的 `_linker_faqs` 字段落库后自动成立。
- **页头页脚的 `[linker_contact_link]`**：线上 partial 里还有三处这个旧插件的短代码（hero 与页脚），旧插件退役后按原文输出。归 #12/#16 的页头页脚线。

## 8. 变更记录

- 2026-10-11：本规格随 #66 首次写入。证据与命令：
  - 线上对照（只读 GET）：`/compare-products/`、`/compare-products/?ids=6521,6522,6523`、`/de/compare-products/?ids=6521,6523`、`/faq-download/`、`/de/faq-download/`、`/linker-advisor/`（200）、`/de/linker-berater/`（200）、`/de/linker-advisor/`（200）——实施日期 2026-10-11。
  - LC 每页机制的来源：快照里的 LiveCanvas 4.9.3 `modules/templating.php`（singular 的 `lc_use_template_of_slug` 分支）与其 `post-specific-dynamic-template-choice-ux.php`（后台的同一选择）。
  - 旧对比页的行为来源：旧仓库当前交付版本的 `plugins/terravolt-b2b-core/assets/compare-selection.js` 与 `includes/compare-products.php`（只作为"线上现状"中性证据：芯片、上限、sessionStorage、地址回写四项照旧；其行数据路径不继承）。
- 2026-10-11（同日追加）：§6 的 WindPress 修复（`render_raw`）与 §7 的三条留档，均随本票一并交付。
- 2026-10-11（评审轮追加）：§1 的页面地址改为按请求语言解析（`ComparePage::page_url()` 经 `pll_get_post` 取页面孪生，德语访客的芯片、规范化跳转与 Remove 链接留在 `/de/` 页），模板引导句落地 §1.2 定稿（EN/DE 都不含 catalogue/Katalog）。
