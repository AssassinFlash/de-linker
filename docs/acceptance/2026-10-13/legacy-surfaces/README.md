# 旧实现清零：LiveCanvas 旧模板族逐面处置（t110，2026-10-13)

范围:旧项目(terravolt)遗留 LiveCanvas 动态模板族在 t110(127.0.0.1:8975)的归属实测与处置。
授权边界:只读抓取 + 把仍由旧模板服务的模板草稿化(`wp post update --post_status=draft`);
未做 present、未碰 WindPress 编译、未改插件与页面内容、未碰其它实例。

## 1. 模板族盘点与归属判据

t110 上 `lc_dynamic_template` 全量(改前):

| ID | 面 | 改前状态 | 判据 | 归属 |
|---|---|---|---|---|
| 231 / 6915 | product archive EN/DE | publish | 1097 字节,`[linker_products_head]`/`[linker_products_filters]`/`[linker_genie_chips]` 短代码组装 | **我方导出,保持** |
| 234 / 6913 | single product EN/DE | publish | 同上族 | 我方,不在本线范围 |
| 6564–6567, 6570/6571 | shop/draft/proforma/account/compare | publish | 同上族 | 我方,不在本线范围 |
| 940 / 6871 | 404 EN/DE | draft | — | 此前已草稿,保持 |
| 574 / 6891 | blog posts index EN/DE | publish | 55 KB 自含内联 CSS,`id="tv-blog-index-v1"` 作用域,**0 个 linker_ 短代码**;注释头被改写成 "de-linker/Linker" 但结构仍是旧版 | **旧实现** |
| 613 / 6887 | single post EN/DE | publish | "TerraVolt Blog Single Post Dynamic Template v1" 注释 + `tv-blog-single-v1`;仅嵌 `linker_contact_*` CTA 短代码 | **旧实现** |
| 619 / 6885 | search EN/DE | publish | "TerraVolt Blog Search Results …" + `tv-blog-search-v1` | **旧实现** |
| 607 / 6889 | category archive EN/DE | publish | "TerraVolt Blog Category Archive …" + `tv-blog-category-v1` | **旧实现** |

判别标准(与简报一致):旧模板含 "TerraVolt" 注释或 terravolt 系资产/作用域引用(`tv-*-v1`);
我方导出是 LC 模板组装 `linker_` 前缀短代码的渲染结果。574/6891 虽然注释里写了 "de-linker",
但整页是 55 KB 自含旧式构建、零 `linker_` 短代码,判旧。

页头页脚 partial(#17/#18/6919/6921)带 `tv-header-v2`/`tv-footer-v2` 作用域 id,但**这些 id 是本仓库
`plugins/linker-commerce/content/livecanvas/partials/{header,footer}.html` 自己发布的**
(移植时刻意保留的样式钩子),且已消费 `[linker_header_utilities]`。属我方现行 chrome,不在草稿范围。

## 2. 四个面的实测记录

实测方法:curl 抓 HTML,渲染归属直接读 LiveCanvas 自己盖进页面的 `<!-- LC DT ID: <n> -->` 戳。
改前 HTML 在 `before/`,改后在 `after/`。

| 面 | URL | 改前 | 改后 |
|---|---|---|---|
| 博客首页 EN | /blog/ | 200,LC DT **574**,`tv-blog-index-v1` + 9 个 `tv-blog-*` 区 | 200,无戳,主题回退,内容在(post 链接可达) |
| 博客首页 DE | /de/blog/ | 200,LC DT **6891** | 200,主题回退 |
| 单篇 EN | /hybrid-inverter-vs-ac-coupled-storage/ | 200,LC DT **613**,"TerraVolt" ×2 | 200,主题回退,标题/正文正常 |
| 单篇 DE | /de/hybridwechselrichter-vs-ac-speicher/ | 200,LC DT **6887** | 200,主题回退 |
| 搜索 EN | /?s=inverter | 200,LC DT **619**,"TerraVolt" ×2 | 200,主题回退,结果正常 |
| 搜索 DE | /de/?s=wechselrichter | 200,LC DT **6885** | 200,主题回退 |
| 分类归档 EN | /category/uncategorized/ | 200,LC DT **607**,"TerraVolt" ×3 | 200,主题回退,该分类文章(558)在 |
| 分类归档 DE | /de/category/uncategorized/ | 200,LC DT **607**(EN 模板兼着渲染) | 200,主题回退 |

注:分类归档只有 `uncategorized` 有文章(REST `categories?per_page=100` 里唯一 count>0),
命名分类(system-design 等)全部 count=0,不可达,不测。

处置执行(2026-10-13,逐个 `wp post update <ID> --post_status=draft`,每条返回 `Success: Updated post <ID>.`):

```
619, 6885, 613, 6887, 574, 6891, 607, 6889 → draft
```

改后读回:8 个全部 `draft`;231/6915 仍 `publish`;940/6871 仍 `draft`。

**四个面的终态:全部"主题回退 + 待设计"。** 新树没有博客/搜索/分类的新模板
(`plugins/linker-commerce/content/livecanvas/` 只有商城/商品/账户/工具页与 partials),
旧通道已断开,这些面由 picostrap5 主题默认渲染兜底,等新设计接管。

## 3. 检查门

`tools/checks/legacy-surfaces.py`(纯 stdlib,无认证,HTTP+REST 只读):

```
python3 tools/checks/legacy-surfaces.py [--base http://127.0.0.1:8975]
```

- 面归属:四个面 × EN/DE,状态码 + 渲染来源判据。判据:LC DT 戳命中旧 ID 集 → FAIL;
  出现本仓库未发布的 `tv-*` 区 id 或 "TerraVolt" 字样 → FAIL;无戳无旧标记 → 主题回退(过)。
  允许清单动态取自 `plugins/linker-commerce/content/**` 实际发布的 id。
- 资产抽查:首页 EN/DE、products EN/DE + 四个面共 12 个公开页,`terravolt-b2b-core`
  资产引用必须为 0;"TerraVolt" 字样只告警不 FAIL(见 §4 未决项)。
- 发现机制:单篇/分类 URL 经公开 REST 发现,换实例夹具为零。
- 退出码:0 干净,1 有问题,2 实例不应答。

2026-10-13 在 t110 实跑:`== CLEAN, 2 page(s) with TerraVolt-word warnings ==`,exit=0
(全文 `gate-run-t110.txt`)。反向证明:用 `before/` 存档 HTML 离线喂 `classify()`,
四个面全部判出 `legacy-template [574/613/619/607]` 且 ok=False;死实例返回 exit=2。

## 4. 仍开的项

1. **`/products/` 与 `/de/produkte/` 各带 3 处 "TerraVolt" 字样**(检查门 WARN)。
   出处:实例快照带进来的子主题 `picostrap5-child-base/functions.php` 输出的
   CollectionPage JSON-LD(`name:"TerraVolt Product Families"`、`"TerraVolt Energie GmbH"`)。
   旧插件 `terravolt-b2b-core` 在 t110 已是 inactive,这段字串来自主题,不在本线授权
   (只许草稿模板)之内。归主题/切换工作处置;本仓库内容树 grep 无任何 "TerraVolt"。
2. **页头页脚/商城模板的 `tv-*` id 是本仓库发布的样式钩子**(`tv-header-v2`、`tv-footer-v2`、
   `tv-mobile-*`、`tv-storefront-*`、`tv-woo-b2b-checkout`)。它们不是旧实现在渲染的证据,
   但是旧词汇;是否改名属样式体系决定,不在本线范围。检查门经允许清单豁免,
   仓库哪天不再发布某个 id,它立刻重新变成 FAIL 信号。
3. **博客首页/单篇/搜索/分类四个面当前是主题裸回退**(待设计)。视觉上是 picostrap5
   默认样式,不是交付态;需要新设计经 LC 模板 + WindPress 接管后,检查门的对应行
   会从 "theme fallback" 变成 "lc-template <新ID>",仍是过。
