# #66 旧工具页处置：对比页重建、Advisor 跳转、文档库页

依据：`docs/audit/2026-10-11-surface-inventory.md` GAP-3/4/5 与业主 2026-10-11 改裁定（compare 独立页由 301 改为重建）。本规格随实现写，是本票交付的一部分：三件套的原生优先穷尽证明（AGENTS 2026-10-11）、目录卡与浮动芯片的集成点。

## 1. /compare-products/（en / de）——重建

**照旧逻辑**（线上实测 2026-10-11，`https://de-linker.com/compare-products/?ids=6521,6522,6523`）：目录卡上的勾选按钮 → 浮动芯片显示已选数量 → 独立页表格；上限 4 个型号；选择态存 sessionStorage（有序商品 ID，只有 ID）；对比页的地址（`?ids=1,2,3`）是这条选择的权威——打开页面即把服务端规范化后的列表写回标签页，所以刷新、收藏与分享都成立。

**数据 = SelectionFacts 图值 + 产品的技术表，一个装配、两个入口。** `Linker\Commerce\Products\Comparison::of()` 是唯一的装配：

- 列：按地址给定的顺序，已发布商品，取标题/链接（按页面语言，#9 的翻译对象）、SKU、图、价格（#11 的 `CommerceState` 规则，看不到价时说同一句话）、有货与否。
- `rows`：**#7 的选择事实**，按设备类取行（逆变器侧 4 行、电池侧 3 行，互不混合；与 `linker/compare-products` ability 的行集、标签逐字一致）。unknown 是一等值，页面印破折号。
- `specs`：各商品**自己的技术表**（`ProductView::spec_groups()`，即 `linker_specs` 或当前语言的产品技术数据）。以原规格组标题和原标签的精确组合判断跨商品是否同一行；不同组的同名标签不合并，在行标题显示原组名区分，未冲突标签仍按原样显示。某商品在同一组重复相同标签时，来源不足以判断各次出现如何跨商品对应，逐条保留、不按位置猜配；无标题的组不补造名称。首个商品给出的行先显示，其他商品首次引入的行依来源顺序追加；数值、单位、注记均沿用来源。每行按当前商品 ID 顺序给出单元格，未声明的值留空并在页面显示破折号。

`linker/compare-products` ability 的 `products` / `rows` 现在由同一个 `Comparison::of()` 投影出来（输入输出 schema 不变，测试锁定），所以 Genie 与页面不可能各算一套。

**LC 承载**：对比页是普通页面，模板用 LiveCanvas 自己的"每页选择"机制——页面的 `lc_use_template_of_slug` 元值（`modules/templating.php` 的 singular 分支）指向模板文章的 slug。模板文章由 `present` 从 `content/livecanvas/compare_page.html`（en）与 `content/livecanvas/de/compare_page.html`（de）建立，slug 分别是 `linker-compare` / `linker-compare-de`；`Templates::assign_pages()` 把两个页面分别指派到各自语言的模板。这两页不是 Woo 页型，所以不用 `is_*` 元值（那会命中所有页面）。

**三件套原生优先——穷尽证明**（每一条都试过，才落到自定义代码）：

1. **LC 原生 tag**：表格的行列来自访客给定的有序 ID 列表（`?ids=`）而不是文章查询，`lc_loop` 只迭代主查询；`lc_the_cf` 读当前文章的自定义字段；`lc_wp_func` 只调无参函数；`lc_if` 只能判断已存在的函数——没有任何 LC tag 能按访客给的 ID 顺序建出"一列一商品"的表，也没有 tag 能读 sessionStorage。芯片的显示/计数/地址是浏览器状态，LC 侧没有对应物。
2. **Woo 原生**：WooCommerce 没有对比功能（不是核心能力，也不装付费插件）；`[products]` 短代码按查询出卡片，不按 ID 顺序出列。价格、有货与否、SKU、图仍走 Woo 自己的取值（`get_price_html`/`is_in_stock`/`get_sku`/`get_the_post_thumbnail_url`）与 #11 的价格门。
3. **WindPress**：样式词汇仍是 Tailwind 类；本票的新类经同一个 provider 进扫描面（见 §4），没有第二条构建。

自定义代码因此只有两处，都是数据装配：`Comparison`（装配）与 `ComparePage`（表片段、芯片、地址规范化、选择态脚本）。**零内联样式、零设计决策**（表片段只输出语义标记与类名）。

## 2. /genie/（de /de/genie/）——Genie 工作区

业主 2026-10-12 选定方案 A 后，这一页是 Genie 的全页工作区，不再 301 到目录。LiveCanvas 每页模板（`linker-advisor` / `linker-advisor-de`）只印 `[linker_genie_workspace]`；会话、历史和投票仍由 `linker-tools` 的 Genie 应用与 `linker-ai/v1/genie/conversations` 承担。右下助手与这一页读写同一条 cookie 会话。页面地址 2026-10-13 业主裁定改为 `/genie/`（德语 `/de/genie/`，不保留旧 slug）；旧 `/linker-advisor/`、`/de/linker-berater/`、`/de/linker-advisor/` 一律 301。

## 3. /faq-download/（en / de）——静态目录化

> **2026-10-15：本节的三段式组成已被票 #176 重做取代**（页头 + tab + 左目录右内容 +
> 毛玻璃卡；短代码换成 `[linker_library_*]` 七枚，16 条商务规则移入
> `data/faq-trade.json`）。当前实现与逐项映射见 `docs/specs/176-faq-download.md`；
> 本节余下文字只作为 #66 当时那一步的记录。

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
  - 手机与折叠导航宽度（小于 1280px）已有选择时，这个单一入口显示在导航下方的独立 52px 实底栏；页头同时预留该行，章节锚点和产品页吸顶导航使用合计 133px 的高度（81px 导航含边框，加 52px 比较栏）。依据是实际 390px 页面中原浮动胶囊遮住创建账户链接；只挪链接不能解除其他滚动位置的遮挡。空选择不留空栏，桌面保留原位置。仅由 WindPress 的 `storefront.css` 表达，不复制入口、不加滚动监听、不改变选择数据或产品权限。
- 页面：`/compare-products/` 已由页面的 `lc_use_template_of_slug` 接好，卡模板不需要知道它。

## 6. 附带修复（本轮发现，本轮修）

**WindPress 编译停在 LiveCanvas provider 的扫描响应上。** 现象：`just windpress-compile` 300 秒无 `cache/store`，浏览器 worker 报 `o.contents is not iterable`；源码定位（`windpress/assets/dist/assets/worker-1JLIzxvG.js` 第 41 行 8440 列）是它把某个 provider 的响应当 JSON 解析后取 `contents`。逐 provider 复跑（临时用管理员会话按 worker 的同一顺序请求 `admin/settings/cache/providers/scan`）证实：**livecanvas 的第 5 批响应不是 JSON**，正文以 `\n\t<h2>Additional information</h2>\n\n{...}` 开头——即 LiveCanvas provider 对单品模板执行 `do_shortcode()` 渲染时，`[lc_wc_product_tab_*]` 在没有商品上下文的情况下把标记泄漏到 JSON 之前，worker 解析失败。修复走官方过滤器：`WindPress::render_raw()` 挂在 `f!windpress/integration/livecanvas/compile:get_contents.render`，对 `lc_dynamic_template` 一律返回 false——模板按原文扫描（类名本来就在原文里），运行期由短代码打印的类由本插件自己的 provider 覆盖。修复后 `just windpress-compile t66` 通过：`cache recompiled (1783954645 -> 1791717446), anchor classes present`，编译产物 205 KB → 350 KB。这是 #54/#59 那条链路上的既有缺陷（线上编译缓存停在 2026-07-13，即编译一直是坏的），本票撞上并修掉，不是本票引入。

## 7. 发现但不在本票范围（留档）

- **本地快照缺商品特色图**：装入后的库 `wp_postmeta` 里没有一行 `_thumbnail_id`（`SELECT COUNT(*) FROM wp_postmeta WHERE meta_key='_thumbnail_id'` = 0），而快照 dump 里有（例：`(45427,6528,'_thumbnail_id','6500')`，本机 meta_id 45427 不存在）。后果：对比表与目录卡的图片列在本机是空的（线上有图），代码路径与线上相同（`get_the_post_thumbnail_url`）。归 #6 的 load/anonymize 链路。
- **德语商品的文档与 FAQ 字段**：数据只在英文商品上（德语商品是翻译孪生），本票的目录读数按 #7 的孪生交换取源语言商品；产品的技术表标签/值是线上继承的产品数据，本机为英文（线上德语由被拆掉的运行时翻译提供）。要德语产品数据，#8 的 `_linker_documents`/`linker_specs` 与 #15 的 `_linker_faqs` 字段落库后自动成立。
- **页头页脚的 `[linker_contact_link]`**：线上 partial 里还有三处这个旧插件的短代码（hero 与页脚），旧插件退役后按原文输出。归 #12/#16 的页头页脚线。

## 8. 变更记录

- 2026-10-13：§7 第一条（本地缺 `_thumbnail_id`）在本机 t110 上复现并修：实例修前 6 行、快照 273 行（t103/t108/t109 均为 273），用 `tools/migrate/13-media-meta.py --snapshot ~/de-linker-data/20261011-1732 plan|apply --write` 从快照写回；`Materials::gallery_ids()` 另修了 `_product_image_gallery` 的读法（Woo 存逗号分隔字符串，`(array)` 只取到第一个 id，导致商品页少一张图且两个 id 以下不出缩略图条）。商品页的德语孪生模板（`content/livecanvas/de/single_product.html`）此前没有任何安装路径，`Templates` 现在把它写进英文模板的 Polylang 孪生（德语页型由孪生渲染，LiveCanvas 按请求语言查指派）。
- 2026-10-13（同日追补，商品页三块与线上对齐）：线上商品页在情景带 checklist 时渲染 `<section class="pdp-block pdp-fit" id="fit">`（"Where this model fits." / "Wo dieses Modell passt."）并在段导航里给出 `Applications` / `Anwendungen` 链接——2026-10-13 逐页实测：GW60K-STS-G10、GW75K-ET-G10、EcoFlow OCEAN 带 checklist、无场景图，线上都渲染；ESA GW10K-EHA-G20 两者皆无，线上都不渲染。`linker_commerce_pdp_has_scenes()` 原先要求 `image > 0 && checklist`，把 checklist-only 的商品整体关死（GW60K 在内），现在只要求 checklist；两份模板（EN/DE）各加一条同条件的导航链接。只带场景图（无 checklist）的商品，线上渲染的是另一变体（"Product views and project settings." + `pdp-scene-reel` 场景卡），本树的 scenes 短代码尚未实现该变体，这类商品保持关闭——已知差异，记录在案。FAQ 块（`Product questions` / `Produktfragen`）由 `_linker_faqs` 数据开启：#16 装配时用 `tools/faq/import.py --from docs/faq --write` 写入（106 产品 221 项）；present 只装呈现层、不写产品数据，所以新起的实例要补跑该导入（本轮验证实例 sweep-8990 即如此）。画廊：`pdp.css` 里的桌面画廊规则（pair 单图、第二图 `display:none`、主图 640 高）此前被 WindPress 后编译进来的 storefront 卷副本压过（≥640px 把 pair 变成两栏并显示第二图，本机主图 400 宽、线上 813），线上是靠后加载的 `product-page.css` 分胜负；这些规则改用本文件自己的 `body:has(#tv-storefront-pdp)` 前缀后，1440 与 390 两处几何与线上逐项相同（813×640 / 72×72 三枚；190×245 / 60×60）。手机缩略图条同处对齐（单行 `overflow-x:auto`、tile `flex:0 0 60px`，线上 68 高对原先 136）。
- 2026-10-29：线上 6530 实测产品页同名额定功率分别属于电网组 60 kW 与逆变器组 30 kW（附原始注记），比较页原只显示后者。比较装配改为按来源组和标签区分；页面按商品 ID 对齐空值。能力仍只输出既有 `products` / `rows` 子集，发布与价格门不变。详见同一验收记录的补充，线上部署与浏览器验收按实际状态记录。
- 2026-10-11：本规格随 #66 首次写入。证据与命令：
  - 线上对照（只读 GET）：`/compare-products/`、`/compare-products/?ids=6521,6522,6523`、`/de/compare-products/?ids=6521,6523`、`/faq-download/`、`/de/faq-download/`、`/linker-advisor/`（200）、`/de/linker-berater/`（200）、`/de/linker-advisor/`（200）——实施日期 2026-10-11。
  - LC 每页机制的来源：快照里的 LiveCanvas 4.9.3 `modules/templating.php`（singular 的 `lc_use_template_of_slug` 分支）与其 `post-specific-dynamic-template-choice-ux.php`（后台的同一选择）。
  - 旧对比页的行为来源：旧仓库当前交付版本的 `plugins/terravolt-b2b-core/assets/compare-selection.js` 与 `includes/compare-products.php`（只作为"线上现状"中性证据：芯片、上限、sessionStorage、地址回写四项照旧；其行数据路径不继承）。
- 2026-10-11（同日追加）：§6 的 WindPress 修复（`render_raw`）与 §7 的三条留档，均随本票一并交付。
- 2026-10-11（评审轮追加）：§1 的页面地址改为按请求语言解析（`ComparePage::page_url()` 经 `pll_get_post` 取页面孪生，德语访客的芯片、规范化跳转与 Remove 链接留在 `/de/` 页），模板引导句落地 §1.2 定稿（EN/DE 都不含 catalogue/Katalog）。

## 2026-10-26 · 比较选择与交互修复

线上实走已确认：德语比较页的英文语言链接丢掉 `ids`，且德语页面实际 slug 为 `produkte-vergleichen`，只检查英文 slug 会漏掉其规范化与选择脚本。共享页头/页脚经 Polylang 原生页面与公开商品配对保留顺序、去重、最多四项和 capped 提示；非比较页不继承任意 ids。目标页将规范化结果写回现有 sessionStorage，不改变存储协议、规格计算、价格门或库存权限。

比较入口显示既有 Compare/Vergleichen 文本，选中出现勾选并保留 aria-pressed，和加入方案动作区分。WindPress 承接既有比较表设计到实际原生类名，移除/清空至少44px；水平溢出时才显示英德滚动提示，行标题固定、数据列保留可读宽度。类别文字直接读 Woo 分类及 Polylang 译名，不改事实层的 slug。空选择直接输出原有空态，跳过完整商品/文档装配。

原生优先：LC 已负责页面组成；Woo/Polylang 提供维护数据与语言配对；WindPress 为唯一样式发布通道。本次只补现有短代码的数据装配、选择脚本和现有样式，未增加独立模板系统或产品权威。验收复用原有发布/资料/价格门结论，仅覆盖本次比较和入口差异。

## 2026-10-26 · 列表与产品页跨语言比较身份

线上确认同两款产品在英文列表已选，直接切德语后仍显示2/4，但两个控件均未选中。比较选择改用既有产品发布层的英文源ID，英德ID只作同一身份的别名；商品页面URL与标题继续使用原生当前语言。每个已渲染卡片/产品页/比较页只提供自身及型号家族的原生ID对应，不新增全站数据读取、网络端点或另一套产品来源。旧标签页ID和混合语言分享链接先合并同一产品，再套用既有四款上限；目标页面仍以当前发布权限重新装配结果。

型号家族切换使用对应源ID并立即重绘比较状态，读回既有译文的可访问名称。原sessionStorage键与有序ID数组协议保留；参数与浏览器存储不授予任何产品/价格/库存权限。复用661的外观与触摸/横向提示证据，只验新增身份、旧ID兼容与型号切换。
