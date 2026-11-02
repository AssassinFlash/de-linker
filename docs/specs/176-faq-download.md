# #176 FAQ + Download 页重做：Tab 框架 + 分区目录 + 毛玻璃卡片

依据：票 #176（业主 2026-10-15 裁定重做为 dashboard 式信息组织 + 原型变体 5 验收）；
`docs/design/2026-10-15-faq-download-prototype`（分支 `prototype/faq-download-redesign`，永不合并）；
本规格随实现写，是本票交付的一部分：原型态 → 实现态的逐项映射、缩略图通道决策、
三件套原生优先的穷尽证明、变更台账。

## 1. 页面与组成

页面仍是 `/faq-download/`（EN）与 `/de/faq-download/`（DE），页面对象与地址不动。
组成（自上而下）：

| 区块 | 承载 | 内容来源 |
|---|---|---|
| 紧凑居中页头（✦ + H1 + 副标题 + 联系行 + 居中大搜索框 + 浅网格底纹） | LC 模板 `content/livecanvas/faq_page.html` / `de/faq_page.html` | 模板字面量（EN/DE 各自成文，见 `docs/acceptance/2026-10-15/176/copy-review.md`） |
| 下划线 tab 栏（FAQ 288 / Documents 159，记入 URL） | 同上 | 计数 `[linker_library_count of="faq|documents"]` |
| 左吸附目录 / 右列内容 | 同上；目录与芯片条 `[linker_library_rail]` / `[linker_library_chips]` | `LibraryPage::rail()` / `chips()` |
| FAQ tab：`Before you order` 5 张分类卡 + `Product answers` 5 张品牌卡 | `[linker_library_faq]` | `data/faq-trade.json`（16 条冻结商务规则）+ `DocumentLibrary::answers()`（272 条产品问答） |
| Documents tab：类型芯片行 + `Brands` 5 张品牌卡（每行一份文档） | `[linker_library_documents]` | `DocumentLibrary::documents()`（159/160 份）+ `DocumentThumbnails`（147 张首页缩略图） |
| 交互层（搜索建议、分页、类型筛选、目录跟随、URL tab） | `assets/library-ui.js`（defer，enqueue 由 `[linker_library_config]` 完成） | 只隐藏/克隆服务端已印的行；自绘字全部来自 config 的 `.po` 翻译 |

**无 JS 即完整**：两 tab 的面板都在 HTML 里（缺 JS 时顺次展开，即目录式长页），搜索框与
类型芯片行默认 `hidden`（无 JS 不出现），不加 JS 就没有 pagination（全部行可见）。这是
本票相对原型的一处**有依据的差异**：原型的骨架屏、JSON 失败重试、失败态都是它运行时
取数的产物，本页数据在服务端装配，不存在取数失败这条路径，故不移植（唯一真实异步对象
是缩略图图片本身，见 §3）。

## 2. 原型态 → 实现态映射（变体 5，逐项）

| 原型行为 | 实现 | 备注 |
|---|---|---|
| `?variant=5&lang=en\|de&tab=faq\|documents` | 真实页面：EN/DE 各一个模板（页面语言即 data 语言），`?tab=documents` 记入 URL（`tabUrl()`，faq 为默认不带参数） | `variant`/`lang` 参数不存在 |
| 页头 ✦ 图标、浅网格底纹、居中大搜索 | LC 模板 markup + `faq.css` 的 `#linker-faq-page .linker-library-hero::before`（mask 网格） | 1:1 |
| 搜索建议下拉：问答/文档各 ≤6、命中 `<mark>`、↑↓、Enter、Esc、点外部关闭、"渲染函数不得因残留查询自动重开" | `renderSuggestions()` 只在 `state.suggestOpen` 为真时展开；`suggestOpen` 只由 input/focus/ArrowDown 置位；`applySearch()` 末尾调用的 `renderSuggestions()` 不置位 | 原型那条坑以状态机形式保持 |
| Enter 打开建议项 | 文档项：新标签打开该 PDF（原型的 `window.open`）；问答项：切到 FAQ tab、清搜索、定位到卡、翻到该行所在页、展开并按 sticky 偏移滚动 | 定位用 `visibleRows()` 下标算页 |
| tab 计数联动（搜索时显示分流数） | `renderSearch()` 更新两 tab 的 `.linker-library-n`；清空恢复 `totals`。**列表本身也按 tab 分流**：搜索中切 tab 重画该 tab 的那一半（`hitsOfTab()`），字段计数仍是命中总数 | FAQ 计数 = 商务规则 + 产品问答（288），与原型 `faqN` 同义；分流是原型 `renderV5` 搜索分支的规则（`split.faq` / `split.documents`），评审轮的 e2e 抓到本实现漏了它 |
| 结果扁平列表带分组 eyebrow | `.linker-library-hit` + `.linker-library-hit-eye`（`<组名> · <Trade rule｜Answer｜Document>`），行由原始 DOM **克隆**而来（保留链接、details、缩略图、类名） | 克隆而非重绘：内容永不两份 |
| 全列表 20 条/页分页器 | `PAGE_SIZE = 20`（`LibraryPage::PAGE_SIZE`，经 config 传给脚本）；每卡一个 pager，搜索结果一个 pager；窗口 `1 … n-1 n n+1 … last` | 行用 `hidden` 收放，DOM 不重建 |
| 类型筛选芯片（带计数） | `[data-library-filters]`（服务端渲染，含 `All` 与各类型计数）；点击置 `aria-pressed`、按 `data-library-type` 过滤行、更新卡计数与 rail/芯片条的品牌计数、重置分页、空品牌显示 soft empty | 芯片顺序取设计序（datasheet→manual→warranty→certificate→compatibility→brochure→document） |
| 骨架屏 / JSON 失败内联报错 + 重试 | 不移植（见 §1） | 有依据的差异 |
| 空态：搜索无命中（+Ask Genie）、类型筛选后无文档 | `.linker-library-empty`（`empty` + `genieUrl`）与 `.linker-library-empty-soft`（`emptySoft`），字来自 config | 无 JS 时不会出现空态（也无筛选） |
| focus-visible、aria（tablist/combobox/listbox/tabpanel）、reduced-motion | `:focus-visible` 全局；tab 是 `<a role="tab">`（无 JS 也能跳锚，键盘 ←→ 切换）；输入框 `role=combobox` + `aria-expanded` + `aria-activedescendant`；`prefers-reduced-motion` 关过渡/动画并让缩略图直接显示 | 无 JS 时 tab 作为锚链接工作 |
| 锚点 scroll-margin = 页头 + tab 栏 + 芯片条 | CSS `scroll-margin-top: calc(var(--ll-header-h) + var(--ll-sticky) + 12px)`；脚本 `measureSticky()` 实测 header 底边 + tab 栏高 +（可见时）芯片条高写入 `--ll-sticky`；点击目录/芯片条链接走 JS 精确滚动 | 无 JS 时回落到 CSS 值（`--ll-tab-h` + 窄屏芯片条估算） |
| 品牌 logo 锁定 34px（mono-light 实为深色字标，直接放浅底） | `card()` 印 `<img height="34">`；取件用 PDP 的同一读取（`get_posts` + `_wp_attached_file LIKE our-brand-<slug>-mono-light`）；媒体库没有则退回头字缩写 `.linker-library-mark` | 无 JS 时 img 直接显示 |
| 缩略图 52×72、失败退类型图标块 | 服务端印 `<span class="linker-library-thumb has-src"><img …><图标></span>`；`has-src` 隐藏图标；脚本 load 后加 `has-img`（淡入）、error 时移除 `has-src`/`has-img` 让图标回来 | 与原型 `has-src`/`has-img` 同名同义 |
| 每行都有 52×72 槽位（无图时类型块在槽内） | **行类恒定**：片段给每一行印 `linker-library-doc has-tile`（不是"有图才带行类"），网格与 `grid-template-areas` 挂 `.has-tile`，有无图只由 tile 上的 `has-src` 区分 | 评审抓到第一版把行类绑在 manifest 命中上：12 行无图行退回两列网格、tile 排到行尾下方（实测 row h=155 vs 有图 102）。现在实测两行同网格同高（1440：有图 101~102、类型块 102） |
| 移动端目录变芯片横条钉页头下 | `@media (max-width:1023px)`：rail 隐藏、`[data-library-nav]` 分组芯片横条 `position:sticky`（top = header + tab 栏），横向滚动 + snap | 两 tab 各一组芯片，`setTab()` 切组 |
| 原型顶栏/页脚/原型切换条 | 不移植：本站已有 LC 页头页脚 partial | 页面本体只有 `#linker-faq-page` |

## 3. 缩略图通道决策（票里把决策权给实现方）

**决策：构建期生成、随插件资源入库发布**（`plugins/linker-commerce/assets/faq-thumbs/`）。

- 生成：`tools/faq/thumbs.py`（本票新增）——WP-CLI 读实例上**本插件自己的寄存器**
  （新 action `documents`，走 `DocumentLibrary`）→ HEAD 探大小 → 缓存下载 →
  `pdftoppm` 渲染第 1 页 → `magick` 缩到高 216px、quality 80 编 **WebP** →
  `<sha1(URL path)>.webp` + `manifest.json`（URL path → file/width/height）。
- 尺寸与格式依据：行内显示 52×72 CSS px，216px 高 = 3×（Retina 与 200% 缩放都够）。
  实测全量 **147 张、总量 984 KB**（PNG 原样为 12 MB，约为其 1/12）；WebP 的浏览器门槛
  （Safari 14+）低于本页已依赖的 `:has()`／`backdrop-filter`（Safari 15.4+），故不设
  PNG 兜底。张数以 `manifest.json` 为准（147 条）：脚本结尾按品牌打印的覆盖率会把同一份
  被多个品牌共用的文件各算一次，逐品牌相加会多出一张（首次记录写成 148 即此因）。
- 键是 **URL 的 path**（不是整条 URL）：同一份文件在线上与本地实例由不同 host 提供，
  缩略图属于文件而不属于 host —— 因此一次构建同时服务线上与本地、EN 与 DE。
- 上限与失败回退：`--max-file-mb 15` 默认跳过大手册（实测 12 份、450 MB），
  下载或渲染失败的记入输出、不入 manifest；缺 manifest 条目的行显示类型图标块
  （原型对无缩略图的文档就是这个样子）。当前覆盖率 147/159（EN）与 147/160（DE）。
- 服务端读取：`Products\DocumentThumbnails::of()`（`manifest.json` 一次读入，
  文件名必须匹配 `^[a-f0-9]{40}\.webp$` 才进 URL）；页面只印 `<img loading="lazy">`，
  不做任何请求期取件。
- 为什么不是 uploads/请求期生成：请求期意味着每次访问都去抓/解析线上 PDF（351 MB 量级），
  且本地实例与线上得各生成一遍；uploads 则是实例状态，不在版本控制里、切换时无法验证。
  随插件发布让"文档行有没有缩略图"成为可 diff、可审计的仓库事实。

## 4. 三件套原生优先（AGENTS 2026-10-11）——穷尽证明

1. **LC 原生 tag**：页面的区块划分、卡片结构、两 tab 的面板与 id 都在模板里（`[lc_home_url]`
   等原生 tag 可用）。但**行的内容**不是文章查询：`lc_loop` 迭代主查询，而本页要的是
   「每份文档一行、按品牌分卡、问答应带产品链接与引用页」——这是产品数据的
   `_linker_documents`/`_linker_faqs` 字段（#8/#15），LC 没有按字段聚合去重的 tag；
   `lc_get_cf` 只能读**当前文章**的字段，本页是 singular page。计数（tab 数、类型芯片数、
   卡计数）同理：LC 不提供聚合。
2. **Woo 原生机制**：WooCommerce 没有"文档库/FAQ 寄存器"能力；`[products]` 短代码按查询
   出商品卡，与「跨商品去重的文档行」正交。产品的下载与 FAQ 读取仍走 Woo/站点自己的读法
   （`get_post_meta`、`wc_get_product`），本票没有另建数据源。
3. **WindPress 管线**：页面样式 100% 在 `content/windpress/faq.css`（既有卷文件，`present`
   安装进卷、随编译进缓存），模板与片段只印语义标签与类名；插件对站点页面零 CSS 的纪律保持。
4. **自定义代码只剩两处，都是数据装配**：
   - `Presentation\LibraryPage`：把一次读取装配成 rail/chips/两个面板/config（输出零内联样式、
     零设计决策；唯一的 `<svg>` 是图标字面量，位置由 CSS 决定）。
   - `Products\TradeRules` + `data/faq-trade.json`：把冻结的 16 条商务规则从模板搬进数据文件
     （原先它们硬编码在两个模板里，计数还是手写的；现在 rail/芯片/卡标题/行读同一份，计数不可能
     对不上）。`Products\DocumentThumbnails`：读构建期 manifest（装配层薄读取）。

## 5. 数据与读取

- `data/faq-trade.json`：5 分类 16 问答，`{en, de}` 成对；内容是本票改版前两个模板里
  那 16 条的逐字搬运（`html.unescape` 后），可核验方式：与 `git show <本票父提交>:
  plugins/linker-commerce/content/livecanvas/faq_page.html` 的同名问答逐字对照。
- `DocumentLibrary::answers()` 新增 `brand` 字段（行所属品牌 = 该产品 `pa_brand` 或名字首词），
  register 因此能把问答案按品牌归档；这是读取层的加法，不改任何既有消费方（产品页、Genie）。
- `LibraryPage::model()` 每请求一次装配，五个片段共享。`DocumentLibrary::entries()` 为两个面板
  共用本次新读取的发布权限、资料字节核验及产品列表；再次装配仍重新读取，独立的
  `answers()` / `documents()` 调用也仍然各自读取当前状态。计数夹具断言一次权限装配、
  一次产品列表查询和一次品牌 logo 查询，其余片段零查询；没有跨请求缓存。

## 6. 扫描面与锚类

`WindPress::scan()` 已经扫 `content/livecanvas/**` 与本插件 `includes/Presentation/*.php`，
新模板与片段自动进扫描面。`WindPressCache::ANCHOR_CLASSES` 增补本页三个锚类
（`.linker-library-tabbar`、`.linker-library-card`、`.linker-library-thumb`：分别由模板、
片段、faq.css 提供，缺一个即本次编译没看见本页），并移除 `lg:grid-cols-3` 与 `gap-8`
——这两个类在本票改版后再没有任何模板/片段使用（它们原先只出现在本页），留着会让
`just windpress-compile` 永远失败。测试同步更新。

**锚点落点**：`scroll-margin-top` 是三处（区标题、卡、问题行）= 页头 + sticky 栈 + 12px；
脚本 `measureSticky()` 把实测量的页头底边、tab 栏高、（窄屏可见时）芯片条高写进
`--ll-header-h` / `--ll-sticky`，并在链接点击与分页时用它算落点。实测（a176，
`tests/e2e/specs/faq-download.spec.ts` 也逐宽度断言 `目标 top ≥ sticky 栈底`）：
1440 落点余量 +13px，390 +15~24px（芯片条是否已钉住而异）。

## 7. 变更台账（允许的像素差异）

本页属**工具页重设计**裁定（2026-10-10：Genie / Solution Configurator 等工具页可有自己的
设计；2026-10-15 业主验收变体 5），不进复刻面像素门。相对线上旧页的客户可见变更：

| 变更 | 依据 |
|---|---|
| 页面结构：三长区块 + 折叠品牌卡 → 页头 + tab + 左目录右内容 + 毛玻璃卡 | 票 #176 裁定 |
| 新增：全局搜索（含建议下拉）、完整品牌问答行（不再两层折叠）、类型筛选、20 条/页分页、锚点目录、移动端芯片条 | 票 #176 裁定与原型验收 |
| 新增视觉：浅网格底纹、深色品牌 logo 锁定（原先文档/问答区只有文字品牌名）、52×72 PDF 首页缩略图 | 原型验收（logo 与缩略图都是原型的一部分） |
| 导航药丸顺序与内容顺序不一致（旧页问题） | 已消除：rail/芯片条的组与顺序 = 面板内容顺序 |
| 锚点跳转被页头吃掉（旧页问题） | 已消除：`scroll-margin` = 页头 + tab 栏 + 芯片条（模板与脚本双路径） |
| 新增文案：页头标题/副标题/联系行、tab 名、区名、15 条 `.po` 新串 | `docs/acceptance/2026-10-15/176/copy-review.md` |
| 德语第一区名 `Vor der Bestellung`（线上德文页写 `Bevor Sie bestellen`） | 原型（变体 5）的德语措辞，业主验收；EN 侧 `Before you order` 与线上逐字一致。评审指出记录曾误写"逐字保留"，已改正并列入本条 |
| 移除：旧 `[linker_faq_help]` 搜索卡与 `assets/faq-ui.js`、旧文档/问答/规则片段短代码 | 被新片段取代；无其他消费方（grep 确认） |
| 保留：16 条商务规则逐字、272 条产品问答与文档数据 | 冻结内容与已评审数据 |
| 2026-10-16 N3：目录类型解析改 role 先行——EN 侧 12 行移动（8 document→compatibility、4 manual→document）；DE 芯片德语化（修复前 159 Dokument + 1 Garantie → 修复后 16 Dokument / 2 Garantie / 其余 142 行分入 Datasheet·Manual·Certificate·Compatibility·Brochure 五类）；另 6506 德语证书行 `download_role` 数据修正（document→certificate，线上+实例） | N3 复核（§8）；EN 侧移动与 PDP 文档卡既显示一致，DE 侧为修复目标本身 |

## 8. 已知数据缺口（票里点名，本轮如实呈现不掩盖）

- **票里"德语商务规则 16 条目前是英文"的前提不成立，已核否**：`data/faq-trade.json` 的
  16 条 `de` 侧全部是德语，抽取源（我们自己的 `de/faq_page.html`，08997063）本来就是德语；
  线上德文页也逐字一致（2026-10-15 拉 `https://de-linker.com/de/faq-download/` 核对：
  16 条问题全部在页面文本里命中，无一英文起句）。故此项不是数据缺口。
- **德语文档类型字段几乎全为 `document`**（160 份里绝大多数）：类型芯片在德语下区分度低——
  本票记录时为「源数据类型字段的缺口」。**2026-10-16 复核推翻该归因**：德语表
  （`_linker_de_acf_json.downloads[]`）每行本来就带 `download_role`（英文规范词），`download_type`
  是德语词（`Datenblatt`/`Handbuch`/`Zertifikat`…），而目录的类型解析（`DocumentLibrary::type()`）
  只认英文词表，于是除个位数外全部落到 `document`——数据不缺，是解析缺一张德语别名表。
  修复＝解析改走产品页文档卡用的同一张映射（`Materials::document_kind()`，role 先、type 后；别名表
  落在 `plugins/linker-commerce/includes/Products/Materials.php` 的 `document_kind()` 内），
  再按目录自己的词表收口（PR #197）。
  修复后 DE 目录与 EN 同分布：两表共享 230 个文件（EN-only 1、DE-only 2），**逐文件类型 100% 一致**
  （914 对 (商品,文件) 全等，含把 6506 德语证书行的 `download_role` 由 `document` 修正为 `certificate`
  后；该数据修正已写入线上与实例）；EN 侧另有 12 行按 role 修正（8 document→compatibility、4 manual→document）。
  附录：`_linker_documents`（#8 字段）只在英文商品上（DE 是翻译孪生，经 `linker_commerce_facts_product_id` 取源），
  EN 106 商品 210 行（datasheet 103 / manual 91 / warranty 15 / document 1），DE 0 行——按设计如此。

## 9. 验收与验证

- 夹具/单测：`LibraryPageTest`（8）、`WindPressCacheTest`（9）、`DocumentLibraryTest`、
  `DocumentThumbnailsTest`（5）、`TradeRulesTest`（4）、`TemplatesTest`、`ModuleTest`；
  `tests/js/library-ui.test.mjs`（22 条：匹配/排序/高亮/
  分页窗口/tab URL、tab 切换与 URL、卡内分页、类型筛选联动计数（含"aria-pressed 只属于芯片"）、
  搜索结果与 tab 分流（含切 tab 重画那一半）、行槽位恒定（克隆后仍是 has-tile）、
  答案命中提示、空态与清空、建议下拉与点外部关闭、键盘 ↑↓+Enter、文档建议打开 PDF、
  开合态保留、脚本零客户串）。
- i18n：`tools/checks/i18n-coverage.py` clean；`msgfmt --check-format` 重生成 `.mo`。
- 本地实例 a176 真实夹具：EN/DE 页 200；tab 标记、卡、文档行带缩略图 img、
  147 张 webp 服务 200；`present` + `windpress-compile` 通过（锚类命中）。
- e2e（`tests/e2e/specs/faq-download.spec.ts`，EN+DE 共 10 条）：tab 往返与 URL、搜索与
  分流计数（含切 tab 后列表只剩该 tab 的一半）、20 条/页分页、类型芯片筛选与计数、
  1440/390 锚点落点 ≥ sticky 栈底。
- 缩略图管线：`tools/faq` 的 `test_thumbs.py`（11 条：key/file_name/webp_size/is_pdf、
  上限选择 `select()`、probe-only 不落盘、清理只留 manifest 命名的文件、提交的
  manifest 与提交的文件互相自洽）；`extract-trade.py --check` 证明 `data/faq-trade.json`
  就是 08997063 的抽取结果。
- 视觉验收（1440/390，EN/DE，逐状态）归主线会话，基准 = 本仓库原型变体 5。

### 9.1 单次装配内的媒体权限查询（2026-10-26）

前批已让 FAQ 和文档两栏共享一次 fresh manifest。继续沿该装配的原生查询归因，
本地 LibraryPage 的 610 条 SQL 中有 608 条来自 `attachment_url_to_postid()`：
同一份 PDF 被多个产品及别名引用时，媒体状态会被重复查询。分类和文件字节校验
不是这批修改的落点；原生媒体查找和 `_linker_document_public` 判定继续使用。

`Publication::assemble()` 为自己的这一次装配持有 URL→允许/拒绝的局部数组；
规范化后的每个 URL 只调用一次原生媒体查找。数组随本次调用释放，下一次
`manifest()` 重新刷新原生运行期缓存并建立新数组，没有对象级、静态或跨请求缓存。
真实 PDF 字节哈希、产品/文档关系、别名相同字节校验、FAQ/数值的证据绑定不变。

单个既有 RevisionTest 文件增加共享产品/别名的回归：两个产品共享一个公开 PDF，
等字节别名被拒绝，再撤回原 PDF，最后重新开放两个 URL。它同时验证本次装配的
查找去重、拒绝结果去重、URL 权限隔离，以及下次装配的撤回/恢复；不叠加页面矩阵。
修复前公开 URL 查找 2 次、被拒别名 3 次，回归明确失败。修复后通过。

相同本地原生数据的两个 fresh manifest 逐字一致，媒体查找 608→142、SQL 609→143；
单次配对装配 2720→2411 ms。当前快照有 85 个产品、142 份文档，不能代替线上完整数据。
线上实际 86 个产品/144 份文档对照虽逐字一致，装配只从 4305→4217 ms，约2%，因此
未单独发布该微优化。边界计时进一步确认，4159 ms 中约3087 ms用于解析/校验文件。
同一完整 manifest 原来还阻塞每一次原版 PDF 下载，本批继续修复该下载调用落点，
合同见 `609-product-publication.md` 的“原版 PDF 的按请求校验”。FAQ 本身的剩余耗时保持开放。
线上只读候选对照、CI、发布与读回结果沿用既有性能记录
`production-faq-copy-correction.json` 的 `attachment_permission_candidate` 字段及本批发布收据。
已有 FAQ 内容/英德呈现/交互证据在输出和样式不变时复用；不重跑全站扫描或截图矩阵。

### 9.2 按页面实际用途读取文档（2026-10-26）

完整资料清单的主要耗时在读取全部 PDF 字节。FAQ 页改用
`Publication::library_read()`，沿同一次原生候选、发布状态、资料关联、媒体许可和
托管路径校验装配两栏；跳过未引用 PDF 的全文和列表未消费的产品事实及准备状态。
没有增加缓存、TTL、表或第二份资料权威。

该读取只返回 `products` / `documents`，不冒充完整 manifest。未引用文档的
`blob_sha256` 为 `null`，不产生产品/资料版本，不授予 FAQ 或数值许可；实际下载
仍由原版 PDF 门重新核当前关联、权限与字节。`DocumentFiles::locate()` 与
`resolve()` 共用原有站点、路径、私有目录和可读文件边界；后者继续计算真实 SHA。
缺失、不可读或越界文件不进入列表。

装配前先收集所有当前发布源产品的原始 FAQ 引用路径，覆盖后面的产品对前面
共享资料的引用。命中主文件或声明别名的资料组仍校验真实字节、等字节别名和
媒体许可，保留首条有效记录的别名集合。答案继续由原有 URL、产品关联和持久
字节绑定裁决；引用路径仅选择校验范围，不能放行答案。主文件或别名替换、
资料撤权、关联移除后，下一次读取仍拒绝旧答案。

一次线上只读候选对照使用真实 86 个产品、144 份资料，37 份命中潜在 FAQ 引用。
装配从 3802 ms / 2714 SQL 降至 1768 ms / 943 SQL。完整 manifest、资料展示字段、
英德各七个原生片段均逐字不变，保留 202 个问答及 144 份资料。这是 CLI 边界计时，
客户端提速须在发布后配对读回。来源哈希和结果进入既有性能记录的
`focused_library_candidate`；未变的样式、搜索、分页及双视口证据复用。

### 9.3 以关联型号查找文档（2026-10-26）

公开页搜索 GW10K-EHA-G20 时有三个问答，却没有文档结果，尽管答案已引用本站手册。
原因是多个产品共用资料时，显示层只保留“关联几个产品”，DOM 搜索索引因此丢失型号。

文档行以转义 JSON 属性携带同一次当前读取已经公开的语言产品名称，不增加查询、
PDF 读取或资料源。列表仍用原来的数量摘要。索引同时读取这些名称；匹配来自关联
产品时，搜索结果和建议展示对应产品，复用既有 `covers %s` 及德语译文，保留原下载
URL。展示名称使用 textContent，畸形或非字符串属性不影响其余搜索。清空查询后
原摘要、目录、分页、筛选和计数恢复；未关联型号不能仅凭相似文档标题获得关联。

产品和文档撤权继续由下一次当前读取及原下载门裁决，前端索引不授予权限。
复用已有加载性能和未受影响状态，只验证真实型号检索、匹配解释、英德换行及下载入口。

### 9.4 搜索与文档类型共同生效（2026-11-02）

搜索时保留已选文档类型：文档结果、建议及文档标签计数只包含该类型，FAQ 命中不受
文档类型影响。文档标签的搜索结果中继续显示同一组类型控件；类型数字表示当前查询
分别匹配的文档数，便于切换或从空结果恢复。切回 FAQ 时隐藏文档类型控件，清除搜索后
将它放回原文档面板并恢复全库类型数字。语言切换与刷新保留已有查询、标签和类型；
原文件链接及服务端授权不变。未启用脚本时仍显示服务端原始文档与链接。
