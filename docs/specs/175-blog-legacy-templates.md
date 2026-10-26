# #175 德语博客面死链与旧模板收编

依据：票 #175（线上症状 2026-10-15 复核：5 个德语归档 10 个文章卡链接 404）；
本票把**实例数据库里渲染这四个面的旧 LiveCanvas 动态模板收编进仓库**（单一实现），
并修掉它们生成文章卡链接的方式。复刻面（营销/产品/商城/分类/博客）的像素门口径见 §6。

四个面：**博客首页**、**搜索**、**分类归档**（本票收编）+ **博客单篇**（#166 已收编，仅列作对照）。

## 1. 现状 → 收编映射

实例（`blogs`，http://127.0.0.1:9027）上这四个面的渲染来源实测（`curl` 读页内
`<!-- LC DT ID: <n> -->` 戳，2026-10-16）：

| 面 | URL | LiveCanvas 赋值键 | 实例上的旧模板 id | 仓库文件（EN） | 仓库文件（DE） | 样式卷文件 |
|---|---|---|---|---|---|---|
| 博客首页 | `/blog/` · `/de/blog/` | `is_blog_posts_index` | 574 · 6881 | `content/livecanvas/blog_index.html` | `content/livecanvas/de/blog_index.html` | `content/windpress/blog-index.css` |
| 搜索 | `/?s=` · `/de/?s=` | `is_search` | 619 · 6875 | `content/livecanvas/search.html` | `content/livecanvas/de/search.html` | `content/windpress/blog-search.css` |
| 分类归档 | `/category/<slug>/` · `/de/category/<slug>/` | `is_archive_for_tax_category` | 607 · 6879 | `content/livecanvas/category_archive.html` | `content/livecanvas/de/category_archive.html` | `content/windpress/blog-category.css` |
| （对照）博客单篇 | `/hybrid-…/` · `/de/hybrid…/` | `is_single_post` | 613 · 6877 | `content/livecanvas/blog_single.html` | `content/livecanvas/de/blog_single.html` | `content/windpress/blog.css` |

收编方式：把六个模板的 `post_content` 原文（只读 WP-CLI 取出）逐字搬成仓库文件，
**只做五类机械变换**（生成脚本与逐文件比对留在 `.scratch/175/`——它们是证据，不进插件、
不随插件发布；仓库提交的 52 MB 全页图同此属性）：

1. 旧作者注释（含 "Deploy: LiveCanvas …" 与 `Target URL:`）换成仓库注释；
2. `<style>` 块搬进卷文件、`style="…"` 行内声明变成卷里的规则（树的规矩：模板管组成、卷管样式）；
3. 文章卡链接 `href="/{Field name}/"` → `href="{Field url}"`（§2）；
4. 实例主机名出仓库：uploads 绝对地址改根相对（`/wp-content/…`），JSON-LD 的站点地址改
   `[linker_site_url]`（§5）；
5. 卷文件里的注释按仓库措辞改写：旧的家族横幅（`… Dynamic Template v1 (DS v1)`）整段去掉，
   两处注释串替换——`--- shared typography (DS v1 eyebrow pattern; JetBrains Mono retired) ---`
   → `--- shared typography ---`，`Linker DS v1 CTA band: …` → `The final CTA band: …`；
   同时去掉 `<style>` 块自己的缩进（`generate.py` 的 `dedent()`；注释与空白不进像素）。

文案、类名、DOM 结构、section id、注释里的英文措辞**一律照线上**（复刻面，文案零改动），
**除一处经裁定的变更**：博客首页两张配置器卡片的 CTA —— 英文 href、德语 href 与德语标签
（§7）。这是全票唯一的客户可见文案改动，其余差异都是上面五类机械变换。

## 2. 死链根因（逐面）

四个面的文章卡都写成 `href="/{Field name}/"`：

- Tangible 的 `post` 循环里 `{Field name}` 是 `$post->post_name`（slug），
  拼上前导 `/` 就是**站点根下的 slug**，与语言无关。
- 英文面：文章地址本来就是 `/<slug>/` → 链接正确（票里也记了「英文归档正常」）。
- 德语面：德语文章地址是 `/de/<slug>/`，`/<slug>/` 是**另一个语言树里的地址**，
  它在线上不存在 → 404。票里的 5 个归档 × 2 卡 = 10 条全部如此。

修法：`{Field url}`。它在同一个 post 循环里解析成 `get_permalink( $id )`
（`vendor/tangible/template-system/loop/types/post/field.php` 的 `case 'url'`），
而 Polylang 过滤 permalink，**按文章自己的语言**给德语文章返回 `/de/…`。
实例实测（WP-CLI，2026-10-16）：

```
$ just wp blogs eval 'echo tangible_template( "<Loop type=\"post\" include=\"6883\"><a href=\"<Field name>\">…'  # 略
de 文章 6883：{Field url} -> http://127.0.0.1:9027/de/hybridwechselrichter-vs-ac-speicher/ ；
              /{Field name}/ -> http://127.0.0.1:9027/hybridwechselrichter-vs-ac-speicher/
```

即：**根因在模板里**（卡片链接的拼法），不在任何 PHP 装配处；修法是模板层的字段选择，
不新增 PHP。（模板的其它链接本来就正确：分类/导航用的分类术语循环 `{Field url}` 走
`get_term_link`，德语文件里写死的地址本来就是 `/de/…`。）

## 3. 接管机制：`present` 按 LiveCanvas 的赋值键就地收编

`Templates::sync()`（`includes/Presentation/Templates.php`）对每个面：

1. `existing_id( $meta )` 按 **LiveCanvas 自己的赋值 meta 键**（`is_blog_posts_index` /
   `is_search` / `is_archive_for_tax_category`）查**published** 的 `lc_dynamic_template`，
   取最小 id（`orderby ID ASC`）——实例上就是旧模板那一行；
2. 命中即 `wp_update_post` 写 `post_content`（+ 旧模板的出版状态保持 publish），
   **不新建第二份模板**；未命中才 `wp_insert_post` 并按老规矩登记备份；
3. 德语面：`sync_page_type_twins()` 用 `pll_get_post()` 找英文锚模板的德语孪生，
   把 `de/*.html` 写进孪生的 `post_content`（键与配对都由 LiveCanvas/Polylang 提供）。

实测（2026-10-16，`just present blogs`）：`created 0, updated 6, unchanged 15`，
六个面（574/619/607/6881/6875/6879）id、slug、状态与语言不变，`post_content`
逐字节等于仓库文件（`content_matches=yes`，见 §6 命令）。**旧模板不是被草稿化，而是被替换**：
LiveCanvas 的模板查找是「按 meta 键取第一条 published」，就地替换后旧内容不再可达。

**旧内容的备份范围**：替换前的内容留在 `linker_commerce_present_backup` 选项里，
`wp linker-commerce rollback --user=<admin>` 可还原——但 `PresentCommand::backup()`
（`includes/Cli/PresentCommand.php:318`）**每次运行都在写入前无条件覆盖**该选项，
取的是「那一刻」的 `post_content`。所以备份保证的是**自旧模板状态起第一次 `present`
之前**的内容；第二次 `present` 之后备份里已经是收编后的内容，`rollback` 只会把收编内容
再写一遍。旧模板全文另有仓库留档（`.scratch/175/dt-<id>.html` 六份），与实例备份无关。

**重复键的边界（上线前检查，本票不执行线上动作）**：`existing_id()` 取 id 最小的一条
（`Templates.php:817-818` 的 `orderby ID ASC`），而 LiveCanvas 自己的查找按
`menu_order` 取第一条（`livecanvas/modules/templating.php:149` 的
`'orderby' => 'menu_order'`）——实例上所有行 `menu_order` 都是 0，同语言真出现两行时
LiveCanvas 的取舍是 DB 未定义行为，这就是这条检查存在的理由。检查必须**逐语言**做：
Polylang 下每个键恒有 EN 行 + DE 孪生两行，不按语言收窄的查询会把健康的配对报成"多余行"，
照它处置就是草稿掉德语面：

```sh
just wp <instance> eval 'foreach ( array("is_blog_posts_index","is_search","is_archive_for_tax_category") as $k ) { foreach ( array("en","de") as $l ) { $n = get_posts( array( "post_type" => "lc_dynamic_template", "post_status" => "publish", "meta_key" => $k, "meta_value" => "1", "posts_per_page" => -1, "fields" => "ids", "lang" => $l ) ); printf("%s/%s: %d row(s) [%s]\n", $k, $l, count($n), implode(",", $n)); } }'
```

判据是「每个（键, 语言）恰好一行」；只有**同一语言内**多于一行时才草稿化多余的
（`wp post update <id> --post_status=draft`），然后才跑 `present`。
实例实测（2026-10-16）：`is_blog_posts_index/en: 1 [574]`、`/de: 1 [6881]`，
`is_search` 为 `[619]` / `[6875]`，`is_archive_for_tax_category` 为 `[607]` / `[6879]`。

## 4. 编译陷阱：`-webkit-` 前缀对必须写在前

WindPress 用 Lightning CSS 编译卷文件。**同一对声明里标准属性写在 `-webkit-` 之前时，
编译器丢掉标准声明、只留前缀那条**，Chromium 于是算出 `backdrop-filter: none`：
毛玻璃面板的模糊消失。实测（blogs，2026-10-16，先按原文顺序搬运）：

```
# 编译缓存里只剩前缀那条
#tv-blog-index-v1 #tv-blog-masthead .tv-blog-masthead-grid { … -webkit-backdrop-filter: blur(18px); … }
# 页面实算样式（逐元素全属性转储的 290 个元素里唯一的差异）
DIV.tv-blog-masthead-grid  backdrop-filter: 'blur(18px)' -> 'none'
# 首尾同机同视口全页截图：blog-en-1440 有 188 804 个像素不同（最大通道差 12/255）
```

把每一对改写成 `-webkit-` 在前、标准在后，编译缓存两条都在，逐元素实算样式与旧渲染
**零差异**。博客单篇（#166）的 context card 早就踩过同一个坑，卷文件里它就是那个顺序；
本票把这个顺序写进 `blog.css` 之外的三个新卷文件，并加了一条单元测试守住**
（`TemplatesTest::test_volume_stylesheets_order_prefixed_pairs_the_way_the_compile_keeps_them`）
——它**逐行**判每个前缀声明（同一属性出现多次也逐次判，`blog-category.css` 的
`backdrop-filter` 写了两遍就查两遍），全卷 13 对带孪生的前缀声明都在判据内；
另有一条变异自测 `test_the_prefixed_pair_guard_catches_each_reversed_pair`
（把 `blog-category.css` 的四对逐对反向，要求每对都变红）。

## 5. 仓库文件里不能有的两样东西

- **实例主机名**：旧模板里有两张 uploads 图片的绝对地址、以及 JSON-LD 的站点地址
  （模板在哪台机器上写的就写哪台：实例上是 `http://127.0.0.1:9027/…`）。前者改根相对
  （`/wp-content/…`，引擎与浏览器都按本站解析），后者改 `[linker_site_url]`。
- **模板引擎标签在 `<script>` 里不解析**：JSON-LD 块里 Tangible 的 `<Site url />`
  会原样输出（实测：块外渲染成站点地址、块内原样）。`[linker_site_url]`
  （`Shortcodes::site_url()`，`home_url('/')` 的 `esc_url`）是数据装配，
  跑在 LC 的短代码通道上，块内也生效。渲染实测：EN 与 DE 的 `CollectionPage.url`
  都是本站自己的 `/blog/`（线上该块同样是 `/blog/`，德语面不指向 `/de/blog/`——照线上）。

## 6. 验收与像素口径

**e2e（`tests/e2e/specs/i18n.spec.ts`，在 blogs 实例跑）**：

- 德语分类归档：卡片链接逐条 `^/de/` 且 200、`lang="de"`；**整页**不得出现任何德语文章
  的英文树地址（`bareArticleLinks()` 对 REST 的德语文章 slug 逐条比对）；
- 德语博客首页：五类卡片（featured/compact/practical/guide/browse）逐条 `/de/` 且 200，
  整页同样无英文树文章地址；
- 德语搜索：结果卡逐条 `/de/` 且 200，整页同样无英文树文章地址；
- 英文归档：卡片仍是英文地址且 200（**英文面不变**）；
- 归档断言的范围从主题的 `#container-content-archive`（旧渲染的兜底壳）改为模板自己的
  section（`faceRegion(html, 'tv-blog-category-v1', 'tv-blog-resources')`）——
  收编后这四个面不再经过主题的 loop 容器。

**像素（复刻面口径：同机同视口、禁动画、等字体图片，全页逐像素，掩膜外差异=0）**：

| 对照 | 结果（2026-10-16，Playwright chromium 1.64，1440×1000 / 390×844） |
|---|---|
| 本地「旧模板」→ 本地「收编后」（工具改名之前，6 面 × 2 视口共 12 张全页图） | **差异像素 = 0**（每张页高逐格相等；同一状态重拍两次也逐像素相同） |
| live → 本地「收编后」（同上），6 面 × 1440 | 六面全部 **0** |
| live → 本地「收编后」（同上），6 面 × 390 | 两面对 0，四面有 **≤3/255** 的残差（`blog-de` 227 px、`blog-en` 154 px、`search-de` 65–134 px、`search-en` 134 px），落在缩略图边缘与文字像素上 |
| 工具改名后：`/de/blog/` 390 对「改名前的本地」 | **声明差异，非回归**（§7）：`Linker Planer öffnen` → `Lösungskonfigurator öffnen` 两处链接文字，见下 |

390 那几处残差**不是本票引入的**，也不是「本地画得不一样」：把本地还原成旧模板后与 live
对比，数字逐对相同（坐标相同）；**同一张 live 页面同协议重拍两次自己也不同**（实测
`/de/?s=wechselrichter` 390：69 px，≤3/255，行带一致）——是 390 上文字/图片缩放的
逐次栅格差异。故这四面 390 的 live|local 差异在当前口径下无法逐像素归零，
需要掩膜（登记为真实动态/栅格噪声区）才能给过门结论；本票不改它的性质，只报告。

**工具改名的像素证据（§7 的那处裁定变更）**：同机同协议、改名前后各拍一次
（`/de/blog/` 与 `/blog/`，1440/390）：

| 面 | 差异像素 | 落点（行带，x 簇） |
|---|---|---|
| `/blog/` 1440 与 390 | **0** | 英文面只有 href 变化，href 不进像素 |
| `/de/blog/` 390（页高 11598 不变） | **3 522** | y 2166–2181 x 91–296（inquiry strip 的 `tv-blog-btn-primary`，1 578 px）与 y 10753–10769 x 75–310（final CTA 的 `tv-blog-btn-primary-lg`，1 944 px） |
| `/de/blog/` 1440（页高 6353 不变） | **11 518** | y 1578–1670 x 121–239 与 x 1032–1221（inquiry strip：按钮 8 811 px + **同一 flex 行里那句德语引文的重排** 763 px——按钮变宽把同行的 `tv-blog-inquiry-text` 挤窄，句子换行位置随之变化）与 y 5513–5529 x 928–1163（final CTA 按钮，1 944 px） |

即：DE 的差异两处是那两条链接文字本身，1440 上还有一处是同一条 flex 行内被它挤动的
引文换行；英文面零差异。

自验命令（证据材料在 `.scratch/175/`——是证据，不进插件、不随插件发布）：

```sh
node .scratch/175/shots.mjs .scratch/175/shots-before     # 旧模板态
just present blogs && just windpress-compile blogs && just present blogs
node .scratch/175/shots.mjs .scratch/175/shots-after      # 收编后
uv run --with numpy --with pillow python .scratch/175/pixel-diff.py \
  .scratch/175/shots-before .scratch/175/shots-after .scratch/175/diff
# 工具改名那处：改名前后各拍一次 /de/blog/（1440/390）与 /blog/（1440/390），同法逐像素比
```

复跑注意：**第二个 `present` 会把 `linker_commerce_present_backup` 刷成收编后的内容**
（§3 的备份范围），要留旧模板的还原点必须在第一次 `present` 之后先做别的动作前取出。

**零旧实现门（`tools/checks/legacy-surfaces.py`）**：判据已随本票更新。
旧模板的 id 仍是 LiveCanvas 的行号，而 `present` **就地复用**这些行，
所以「页内戳号 ∈ 旧 id 集」不再是旧实现的证据；新判据是**旧实现真正印进页面的东西**——
行内 `<style data-name="tangible-template-inline-style">` 块（移植后样式归卷）与
模板家族横幅（`… Dynamic Template v1`）。戳号仍打印，且 `LEGACY_DT_IDS`
已按实例实际行刷新（`{940, 6861, 574, 6881, 613, 6877, 619, 6875, 607, 6879}`，
EN+DE 成对），八面**都**带 `(reclaimed old row […])` 注解。
双向实测：`docs/acceptance/2026-10-13/legacy-surfaces/before/*.html` 八个存档页
全部仍判旧（ok=False），当前八面全部判「我们的模板」（ok=True）；
blogs 实例整体 `== CLEAN ==`，exit 0。

## 7. 已按裁定修改的一处 + 发现但**未改**的同类项

### 7.1 已改：博客首页的配置器 CTA（工具改名，业主已裁定）

业主裁定（文案对抗评审 2026-10-10 #12 + 工具改名台账 B4/B2）：旧工具名全站替换、
配置器页面搬到自己的地址（2026-10-12）。仓库其他面（页头页脚 partial、产品页、营销页）
早已是新名，线上旧模板的博客首页是漏网的一处；本票收编时顺手改到既定的对：

| 面 | 旧 | 新 |
|---|---|---|
| EN `blog_index.html`（2 处） | `href="/linker-planner/"`（301 → `/solution-configurator/`） | `href="/solution-configurator/"`（标签本来就是 `Open the Solution Configurator`） |
| DE `de/blog_index.html`（2 处） | `href="/linker-planner/"` + 标签 `Linker Planer öffnen` | `href="/de/loesungskonfigurator/"` + 标签 `Lösungskonfigurator öffnen` |

德语标签取的是站点既有的 msgid/msgstr 对（`linker-commerce-de_DE_formal.po:1612`：
`Open the Solution Configurator` → `Lösungskonfigurator öffnen`，产品页按钮同款），
德语地址是配置器自己的 German slug（线上 6693 的 slug 将在部署窗口改，属台账 B2；
本票未执行线上动作）。像素：EN 只换 href，**差异 = 0**；DE 是两处链接文字的**声明差异**
（§6 末的像素证据段）。

### 7.2 未改：德语面其余通到英文树的链接

德语面照线上复刻，这些非 `/de/` 链接一字不动带了过来；都不是 404（除第一项外），
是「德语面通到英文树」，与 #175 同族但不在本票授权范围内（票面只允许文章卡链接语言化
一处差异，且「英文归档不变」）：

| 位置 | 现状 | 行为 | 备注 |
|---|---|---|---|
| `de/category_archive.html` 资源卡「Unsere Produkte ansehen」 | `href="/product/"` | **404**（线上同样 404；英文模板同款 `href="/product/"`） | 同族死链；修法 = EN 指 `/products/`、DE 指 `/de/produkte/`（各一行）。英文面同改才算齐，故留给主线一并裁定 |
| 两个搜索表单（首页/分类/搜索面各一） | `action="/"` | 德语面提交到英文搜索页（200，英文结果） | 修法 = 德语模板 `action="/de/"`；只改德语模板 |
| 搜索面与分类归档的「Alle Artikel / Filter zurücksetzen」 | `href="/blog/"` | 德语面通到英文博客首页（200） | 线上同款 |

另：本票不改 `docs/acceptance/2026-10-13/legacy-surfaces/README.md`（当期验收记录，历史），
接管后的口径以 §3 与本文为准。


## 原生分页的呈现补全（2026-10-27，全站体验目标）

站内搜索的真实第二页确认：LiveCanvas输出当前项为`span.page-link.current`，原卷只给链接和`span.page-numbers`统一尺寸，因此当前数字仅约9.6×20px；原生`h2.visually-hidden`也未获得对应隐藏规则，直接露出默认英文标题。共享journal卷补齐原生span的既有44px外观，并仅在分页内保留标题的辅助阅读隐藏语义。三个页型的英德模板使用LiveCanvas原生`screen_reader_text`参数传入Page navigation／Seitennavigation，不改插件PHP、分页查询或链接机制。

站内搜索分支缺少其他journal页面已有的`journal-content`容器，手机flex顺序因此把搜索分区入口放到结果末尾，紧贴分页。英德分支补回同一容器，分区导航回到搜索框与结果之间；沿已有样式和值，不另造间距体系。

必要验收：真实多页搜索的当前项、相邻项、下一页、查询/语言保留和键盘焦点；EN/DE1440/390实际布局；同一原生标签在博客首页及分类的消费者核实。当前项保持非链接和aria-current，标题仍可被辅助阅读命名。无分页时不出现额外空导航。已有未受影响搜索、文章消费者与营销正文结果复用。
