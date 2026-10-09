# linker-i18n 审计 + EN/DE WooCommerce 方案调研

日期：2026-10-09。只读审计，未写任何站点、未改仓库文件。
代码：`refs/landed/chain-tip` = `f007a9dd`（2026-10-09 13:18 +0800），插件 `plugins/linker-i18n/` 版本 0.5.78（`linker-i18n.php:5`）。下文 `文件:行` 均指该提交。
线上：https://de-linker.com 与 /de/，cache-busted GET（`?cbq=<ts>`），2026-10-09 约 13:30–13:55 CST。
外部调研：全部经 Apify `apify/rag-web-browser`（第一次走 Apify MCP；因两个 Apify 连接器的数据集权限不互通，之后用 Apify REST + `~/.config/terravolt-builder/apify.env` 的 token 跑同一 actor，token 未打印、未落盘）。每条来源附 URL 与抓取时间（UTC）。

---

## 0. 结论速览

- **它不是"运行时 DOM 翻译"**。德语是服务端生成的：发布时 DeepSeek 按字符串翻译 → 校验 → 存进 postmeta / 自建字典表；渲染时用过滤器把英文对象换成德语，再对整页 HTML 做一次字典替换（chrome map）和链接改写。浏览器端 JS 只做链接、语言切换、REST 带 locale、3 条应急文案、以及按浏览器语言自动跳转。
- **内容主链路是健全的**：/de/ 页面的德语、`<title>`、description、JSON-LD 都在原始 HTML 里；hreflang 双向 + x-default、按语言 canonical、德语 sitemap 与英语 sitemap 一一对应（150/150）、404 正确。20 个随机商品 EN/DE 数字比对：1 个有实质遗漏（一句话后半句没译出），其余一致。
- **不健全的是外围**：①整页 HTML `strtr` 字典替换（chrome map）是事故源头（德语复合词被啃坏连续 5 个版本打补丁，代码里有 25 轮审查的痕迹）；②没有任何后台界面——开关、种子、强制重译都靠开临时 Code Snippet 桥；③UI 文案德语分散在约 7 套机制；④死代码与死数据（`discovery-surfaces/` 384 KB 无人读取，却占插件 121 次提交中的 68 次）；⑤若干 SEO 风险（整站 noindex 一票否决、按浏览器语言自动跳转、/de/ 下英文 slug 200 重复页、/de/ 首字节慢 0.3–0.9 s）。
- **外部现实（2026-10）**：不花钱就没有能管 WooCommerce 商品的"存储式"多语言插件——Polylang 免费版明确要付费的 Polylang for WooCommerce（99 €/年），唯一的免费桥接插件 2026-10-05 已被下架且 6 年未更新；TranslatePress 免费版本身就是"整页输出缓冲 + 字典替换"，而且 slug 和 SEO meta 翻译要付费；MultilingualPress 付费（149 €/年起）；WordPress 核心多语言（Gutenberg Phase 4）还停在路线图上。
- **建议：hybrid（保留并瘦身）**——保留 linker-i18n 的"单对象 + 德语存 meta + /de/ 路由 + 词表校验翻译任务"这一核心；把 UI 文案收拢到 WordPress 原生 gettext（含 Loco Translate、WooCommerce 正式德语包 de_DE_formal）；把德语审校搬进 WP 后台；删掉死代码，逐步缩小整页字符串替换层。理由见 §B6。

---

## A. linker-i18n 0.5.78 实际做了什么、是否健全

### A1 架构

**请求与语言**
- MU 加载器在插件加载前解析语言（`mu-loader/linker-i18n-mu-loader.php:7-53`，连 REST JSON 原始 body 也读，:31-40），保证 `.mo` 用德语加载。
- 单一 `locale` 过滤器：/de/ 请求返回 `de_DE`（`linker-i18n.php:121`，`includes/class-linker-i18n-lang.php:70-72`）。WP/Woo/b2b-core 的 gettext 由此切德语。
- 普通页面只按 URL 路径判语言；REST/AJAX/Woo 端点按 `X-Linker-Locale` 头或 `locale` 参数，矛盾则 400（`linker-i18n.php:260-334`，`class-linker-i18n-lang.php:110-140`）。

**/de/ 是怎么服务的——不是独立的德语文章，而是改写英文请求**
- `plugins_loaded` 优先级 1：把 `/de/<德语路径>` 反查成英文路径并**改写 `$_SERVER['REQUEST_URI']`**，让 WordPress 解析到同一个英文对象（`linker-i18n.php:630-675`，纯路径计算在 `includes/class-linker-i18n-router.php:51-149`）。
- slug 三张表：12 个固定基础段（`data/slug-bases-de.json`），商品分类专用表（`data/shelf-slugs-de.json`），页面/文章 slug 映射存 option（`linker_i18n_slug_map/_rmap`，`linker-i18n.php:432-445`）。新页面发布后 5 秒用模型翻译标题生成德语 slug（`linker-i18n.php:457-519`）；商品 slug 故意不译（型号）。
- 改名的德语 slug 301 到新址（`linker-i18n.php:683-693`）；分类 `/de/product-category/` 与英文分类 slug 301 到德语地址（`linker-i18n.php:702-714`）；关闭 WP 的 404 猜测与 canonical 跳转（`linker-i18n.php:724-746`）；服务端 `wp_redirect` 本地化（:750-758）；`<html lang="de-DE">`（:760-768）。

**德语怎么产生（发布时，不在访客请求里）**
- 触发：`wp_after_insert_post`、`save_post_lc_partial`、`save_post_lc_dynamic_template`、`woocommerce_update_product/new_product`（`includes/jobs.php:1022-1039`）→ `linker_i18n_enqueue()` 写待办 option（上限 2000，`jobs.php:72-91`）+ 5 秒单次事件 + **在保存请求自身的 `shutdown` 上直接跑**（`jobs.php:103-129`）。兜底：每 15 分钟 sweep 3 个（`jobs.php:955-1005`）。
- `Translator::translate_post()`（`includes/translator.php:507-807`）：按块切分句子（行内标签随句走，短代码/script/style 先摘出再放回，`translator.php:25-45`）；先查字典，再把缺的批量发给模型（≤25 条/≤1800 字符一批，≤12 次调用/次运行，`translator.php:65-92`）。
- 模型：`Linker_AI_Model('i18n')->chat_raw()`，独立熔断域（`translator.php:1177-1193`）；提供方 DeepSeek，默认 `deepseek-flash`，temperature 0.1，关闭 thinking（`plugins/linker-ai-assistant/includes/class-linker-ai-model.php:257-265, 542-556`；`class-linker-ai-settings.php:136-146`）。
- 系统提示词把词表拼进去（`translator.php:1402-1447`），要求只回 JSON 数组、保留 `<0>` 标记、不写 AI/KI、型号与单位原样、Sie 称呼。
- 校验（`translator.php:110-146`）：空、占位符、结构（标签/URL）、禁用词（`data/banned-vocabulary.json`）、词表禁译词（`data/glossary-de.json` 的 `never/unless/sense/allow`，`translator.php:1265-1400`）、型号完整性。后处理：品牌小写、`controller`→`Controller`、英文千分位→德式（`translator.php:153-313`）。**没有数字/事实对等与完整性校验。**
- 存储：页面/文章 `_linker_de_content/_title/_excerpt(+_sha)/_source_sha/_copy_sha/_status/_marked_at`；商品额外 `_linker_de_acf_json`（整个 `_tv_legacy_acf_json` 的德语孪生）与 `_linker_de_source_acf_json`（`translator.php:48-63`，`includes/product.php:37-40`）。字符串字典是自建表 `wp_linker_string`（sha1 键 + context，状态 1=机器、2=审校，`includes/store.php:42-59, 113-132`）。
- 商品载荷里哪些字段算"文案"是一份写死的键名清单 + 句子判定启发式（`product.php:71-138, 152-415`），与 b2b-core 的载荷结构直接耦合。

**渲染时怎么换成德语（`includes/render.php`）**
- 正文：`the_content` 优先级 5 换成 `_linker_de_content`，带新鲜度门（源 sha 不符就回英文，`render.php:46-67, 750-799`）。
- 标题/摘要/商品短描述/SEOPress 标题：`render.php:429-748`。
- 商品载荷：在 `get_post_metadata` 与 `woocommerce_data_store_wp_post_read_meta` 两个入口把英文 ACF JSON 换成德语孪生（`render.php:109-185`）。**这里没有新鲜度门**：只要德语载荷非空就照发。
- 整页输出缓冲（`render.php:191-245`）：对整页 HTML 依次做 chrome map 字典替换（`includes/chrome.php:416-427`，只碰文本节点、4 个可读属性、白名单 meta content，`chrome.php:442-675`）、日期改德式（`includes/dates.php:53`）、JSON-LD 里的链接本地化（`chrome.php:704+`）、`<a>/<form>` 链接本地化（`render.php:290-404`）。
- chrome map 是一个 option（上限 4000 条），在翻译时重建：LiveCanvas 页眉页脚和 7 个动态模板的英/德配对 + 所有文章/页面/商品标题 + SEOPress 全部文案 + 分类描述 + `data/commerce-strings-en.json` 的界面句子 + 媒体库全部 alt + 其他插件经 `linker_i18n_chrome_strings` 交来的句子（`jobs.php:622-808`）；分类名另从 `data/taxonomy-de.json` 在服务时并入（`includes/taxonomy.php:51-77`，`render.php:218-221`）。
- 为防 `strtr` 啃坏德语复合词，有两条稳定性规则 + 每请求按当页词汇动态"护盾"（`chrome.php:44-146, 251-325`）与专有名词护盾（`chrome.php:398-414`）。
- 交易邮件：德语订单邮件的整个 HTML 也过一遍 chrome map（`linker-i18n.php:781-806`）；邮件语言存在订单/用户 meta 上（`linker-i18n.php:809-880`）。

**`assets/linker-i18n-runtime.js` 在浏览器里做什么**
- 猴子补丁 `fetch` 和 `XMLHttpRequest`，给同源 REST/AJAX/Woo 请求加 `X-Linker-Locale`（`runtime.js:50-87`）。
- 在浏览器里再算一遍 EN→DE 路径并改写 `a[href]/form[action]`，MutationObserver 持续监听（`runtime.js:89-170, 349-361`）。
- 文本替换只有一个 3 条的应急字典（`runtime.js:172-184`；字典在 `linker-i18n.php:956-960`）——**不是 DOM 级翻译**。
- 注入/改写语言切换控件，写 `linker_lang` cookie（`runtime.js:186-300`）。
- **首次访问自动跳转**：英文页 + 浏览器偏好德语 + 无 cookie → `location.replace(dePath)`（`runtime.js:369-377`）。线上配置 `public: true`，即已生效。

**`discovery-surfaces/` 与 `data/*.json`**
- `discovery-surfaces/`：8 个 HTML（页眉页脚 + 6 个模板的英文源码字节拷贝，共 383,581 字节）+ manifest。生成器文档仍写"运行时 discovery 通过 PHP 分段器和 occurrence registry 消费这些文件"（`scripts/rest/build_linker_i18n_package.py:120-126`），但 occurrence registry 在 2026-08-03 重建时已删除；插件 PHP/JS 中没有任何代码读取该目录（grep 为零），`config/runtime-components.json` 的发布记录也明写 "no runtime code reads the discovery bundle"。它仍在每次页眉/页脚/模板变更时被重新生成和部署：本仓库里触及 linker-i18n 的 121 次提交中有 68 次碰了它。且该目录对公网可读（`/wp-content/plugins/linker-i18n/discovery-surfaces/partial-header.html` 返回 200）。
- `glossary-de.json`：词表，同时喂给提示词和校验器（65 条，其中 20 条带 `never/unless/sense/allow` 规则；`commercial` 条目的 `de` 值是一段说明文字而非译名）。
- `banned-vocabulary.json`：品牌不说 AI/KI 的禁用词 + 厂商功能名白名单（"AI Saving 3.0"、"SAJ AI Care"、"1 × AI"…）。
- `commerce-strings-en.json`：渲染器（b2b-core）打印的英文界面句子清单（70 条），交给模型翻进 chrome map。
- `taxonomy-de.json`：27 个分类名的人工德语。`slug-bases-de.json` / `shelf-slugs-de.json`：URL 段。

### A2 SEO 与正确性（线上实测 2026-10-09）

| 项目 | 结果 | 证据 |
|---|---|---|
| 德语是否服务端渲染 | 是。DE 商品页原始 HTML：德语虚词 159、英语虚词 5（均为 "All-in-One" 类误报）；首页 276 vs 5 | `/de/produkt/goodwe-esa-gw10k-eha-g20-10-kw-single-phase-power-module/` 与 `/de/` 的原始 HTML |
| `<html lang>`、Content-Language | `de-DE` / `de` | 响应头与 HTML |
| hreflang | en/de/x-default 双向，x-default=英文 | 首页、商品页 head；`class-linker-i18n-router.php:550-566` |
| canonical | 每语言自指，全站仅一个（整段 head 缓冲去重） | `linker-i18n.php:1170-1232` |
| 德语 sitemap | `/de-sitemap.xml` 150 条，与英文 4 个子 sitemap 的 URL 集合完全一致；robots.txt 已声明 | 实测比对；`linker-i18n.php:1040-1162` |
| 结构化数据 | DE 页 Product JSON-LD 的 name/description 为德语，url 为 /de/ 地址；无 `inLanguage`（中性） | DE 商品页、DE 博文 |
| 404 | `/de/gibt-es-nicht-xyz/` → 404 + noindex | 实测 |
| /de/ 下英文 slug | `/de/about/`、`/de/product/<slug>/`、`/de/products/`、`/de/contact/`、`/de/cart/`、`/de/my-account/` 均 **200**（靠 canonical 指向德语地址）；只有分类做了 301 | 实测；路由器"两种 slug 都接受"`linker-i18n.php:453-455` |
| 404/noindex 页上的 hreflang | 404 页与站内搜索页也输出指向不存在/noindex URL 的 hreflang | `/de/gibt-es-nicht-xyz/`、`/de/?s=Wechselrichter` |
| 自动语言跳转 | 已启用（见 A1），与 Google 指引"不要按你认为的用户语言自动跳转"相反 | Google 文档见 §B 来源 17 |
| 整站 noindex 一票否决 | 只要任一页面/文章/模板德语为空或 `partial` 超过 1 小时，**全部** /de/ 加 `noindex`、德语 sitemap 变 404、robots 里去掉、切换器隐藏 | `linker-i18n.php:418-424, 1129-1133, 1154-1162`；`router.php:561-563`；`jobs.php:880-953`。当前线上为 index（未触发），属设计风险 |
| 就绪度量范围 | 度量**不含商品**（只算 lc_partial、lc_dynamic_template、page、post），而商品占德语 sitemap 150 条中的 104 条 | `jobs.php:915` |
| 商品新鲜度 | 正文过新鲜度门，商品载荷不过；英文商品改了之后，任务写入前德语页继续发旧载荷（含旧的非翻译事实字段） | `render.php:62-65` 对比 `render.php:109-128` |
| 页面缓存 | HTML 响应无任何 `x-litespeed-cache` 头，重复请求首字节仍为 2.2–6.6 s，说明页面缓存实际没生效；翻译写入时清缓存用的是整站 `X-LiteSpeed-Purge: *`，且在 shutdown 时多半已发完头 | `class-linker-i18n-cache.php:97-110`；实测 |
| DE 比 EN 慢 | 同页 3 次中位数：首页 +0.33 s，商品列表 +0.91 s，商品页 +0.57 s，关于页 +0.36 s（整页 strtr/链接扫描的代价；从本机网络测，仅作指示） | 实测 TTFB |
| 内容质量抽查 | 20 个随机商品 EN/DE 数值比对，18 个一致，1 个误报（德语"6- und 10-kW"省略式），1 个实质遗漏：GW124.99K-ETR-G10 简介英文 "...hybrid inverter: 124.99 kW continuous AC with high-voltage multi-MPPT solar intake." 德语只剩前半句。校验器无完整性/数字对等规则，这类遗漏不会被拦 | 实测；`translator.php:110-146` |
| 其它小项 | DE 页 HTTP `Link` 头的 shortlink、`?format=md` alternate 指向英文；JS 端路径映射不认识分类 slug 表，JS 生成的分类链接会多一跳 301（服务端渲染的链接正确） | 响应头；`runtime.js:101-116` vs `router.php:135-141` |

### A3 运营

**店员怎么看/改德语**
- 只有商品有后台入口：b2b-core 商品编辑面板"Linker product data"中英并排；填写的德语被写成 linker-i18n 字典的审校行（全店共用一句一译），并把商品标成 `partial` 重新入队（`plugins/terravolt-b2b-core/includes/product-editor.php:385-410`；ADR-0033）。这是 b2b-core 直接写另一个插件的私有表。
- 页面、文章、SEO 标题/描述、页眉页脚：**没有后台界面**。审校德语写在仓库 `tests/fixtures/linker-i18n-reviewed.json`（1,455 行），由开发机跑 `scripts/i18n/rebuild_switch.py --seed` 再 `--translate <id> --force`；SEO 文案还要 `--chrome-map` 重建（`docs/agents/i18n-strings.md`）。这些脚本每次都开临时 Code Snippet 桥（`rebuild_switch.py:1-30`）。插件本身没有任何菜单页、元框、REST 路由或 WP-CLI 命令（grep 为零）。
- 分类名：改 `data/taxonomy-de.json` 并部署插件文件。
- 英文页面一改，存的德语正文整体作废、所有句子重新从字典/模型取，原地手改的德语会丢（`docs/agents/i18n-strings.md:55`，`translator.php:821-831`）；商品则有逐叶保留逻辑。结果是页面改版时常要写一次性脚本来保住德语：`.scratch` 里有 24 个 `german_*.py/php/sh`（140、141、143、130、legal-pages、contact-identity、mainline-health 等）以及 302 个 expected-de/baseline-de 快照文件。2026-09-29 一次强制重建曾把 37 个 GoodWe 页面上 1,322 处已修正的德语换回机器译文（`docs/agents/i18n-strings.md:50`）。
- "审校"状态不可信：字典里约 13,000 行 STATUS_HUMAN，多数是历史迁移而非人审（`translator.php:928-935`）；仓库 fixture 与线上表（含商品编辑器写入）是两处来源，`Store::put` 用 REPLACE 覆盖（`store.php:150-166`），种子可以覆盖店员在编辑器里写的同一英文句的德语。

**英文商品保存后德语何时出现、会怎么失败**
- 时序：保存 → 入队 → 同一请求 shutdown 上立即翻译（每次最多 12 次模型调用，每次单次 18 s、总 40 s 上限）→ 写 meta → 必要时 shutdown 再重建 chrome map（模型预算 60 s，`jobs.php:697-700`）。没有 `fastcgi_finish_request` 之类的提前结束响应（全仓 grep 为零），所以这些都算在店员点"更新"的那个请求里；代码注释自己写了主机网关约两分钟会断开。推断：大批量或模型慢时，后台保存会卡住甚至超时（但服务器端仍在写）。
- 失败形态：模型故障 → `partial`，下次 sweep 继续；被校验拒绝的句子永久保持英文且不再排队，只在 20 条的 job log option 里可见（`translator.php:796-803`，`jobs.php:135-158`）；锁冲突 → 留队；WP-Cron 靠访客请求驱动（`jobs.php:11-14`）；待办超 2000 丢最旧。

**UI 文案德语——不是一套机制，是大约七套**
1. WP/Woo 核心语言包（经 `locale` 过滤器）。站点用非正式 `de_DE`，正式包没装，于是 b2b-core 用 290 行的 `email-voice.php` 覆盖邮件里的 "du" 句子（`email-voice.php:15-31`）。
2. b2b-core gettext：`terravolt-b2b-core-de_DE.po` 986 条。
3. b2b-core PHP 字面量中德对照：`tv_b2b_portal_copy()`（`account-portal-render.php:36-965`）、`tv_woo_b2b_commerce_de()`（`commerce-pages.php:74-169`）、`tv_b2b_project_portal_text()`（`project-display-text.php`，509 行）。
4. linker-ai-assistant：`.po` 只有 3 条；实际靠 JS 字面量 `COPY2`（`linker-assistant.bundle.js:505`）和 `data/tool-frame-copy.json`。
5. linker-i18n chrome map：`commerce-strings-en.json` → 模型 → 整页 strtr；另有 `linker_i18n_chrome_lookup()` 供 b2b-core 自己打印规格标签（`chrome.php:234-249`）。
6. runtime JS 的 3 条应急字典。
7. 手写 JSON：`taxonomy-de.json`、两张 slug 表。
另外 Advisor 重构计划再引入 `packages/i18n`（`.scratch/advisor-rebuild/issues/022-engineering-baseline.md:19`），会是第八套。`docs/agents/i18n-strings.md` 自己也承认存在四种模式。

### A4 体量与气味

**体量**
- 插件：PHP 8,896 行（`translator.php` 1,448、`linker-i18n.php` 1,304、`jobs.php` 1,057、`chrome.php` 895、`render.php` 799…）；JS/CSS 555 行；数据 JSON 423 行；`discovery-surfaces/` 384 KB。
- 插件外为它服务的东西：测试 3,749 行、审校 fixture 9,204 行（1,455 行数据）、scripts/tools 6,964 行（`i18n_render_qa.py` 1,745、`i18n_live_form_qa.py` 1,032、`rebuild_switch.py` 749、`validate_german_site.py` 674、`audit_german_site.py` 588…）、文档约 750 行，外加 `.scratch` 的一次性德语脚本。
- 跨插件耦合：b2b-core 与 Advisor 共 38 个文件、167 处引用 linker-i18n 符号；b2b-core 直接读写 `\Linker\I18n\Store`（`product-editor.php:399`，`catalog-search.php:148-153, 331`）。
- 变动频率：本仓库 2026-08-28 至 2026-10-09 共 121 次提交触及该插件。

**死代码 / 过时内容**
- `linker_i18n_should_translate_source` 两个过滤器（自家邮箱白名单、法定身份不翻译）没有任何 `apply_filters` 调用，注释自己承认"inert"（`linker-i18n.php:529-604`）。也就是说注释声称的"法定地址不送模型"实际上不成立。
- `$GLOBALS['linker_i18n_render_path']` 每个请求都算、没人读（`linker-i18n.php:655-658`）；`Router::render_identity()`、`is_sensitive_render_context()` 无调用（`router.php:363-463`）。
- `linker_i18n_additional_sensitive_render_context`：linker-i18n 与 b2b-core（`projects.php:521`）都挂了过滤器，全仓没有触发点（旧 overlay 已删）。
- `Linker_I18n_Cache::flush()` 里关于 render-QA 证据、`coverage_complete`、`Linker_I18n_Admin::refresh_coverage_gate()` 的分支，类已不存在（`class-linker-i18n-cache.php:59-91`）。
- `linker_i18n_serve_post_ids` 分阶段开关（`render.php:80-94`）、`jobs.php:17-26` "旧系统仍在翻译"的注释——灰度早已结束。
- 过时注释：`store.php`/`vocabulary.php`/`translator.php` 开头说"旧类已声明同名全局类、在 linker-i18n.php:1577"——这些类和行号都不存在了；`store.php:29` 说"本插件唯一含 SQL 的文件"，但 `jobs.php:251-256` 有 SQL；`taxonomy.php:48` 说"故意不含 Uncategorized"，`taxonomy-de.json` 却有。
- `package-manifest.json` 与 8 个文件的 sha/大小不符（线上文件与 tip 一致，过时的是清单）。
- `linker-i18n.php:906-907` 同一个值起两个名字（`$available`、`$public`）。

**重复规则（违反 Law 4）**
- EN→DE 路径映射有两份：PHP `Router::to_de()` 与 JS `germanPath()`，JS 版已漂移（不认识分类 slug 表）。
- 链接本地化服务端做一遍（`render.php:290-404`），客户端再做一遍（`runtime.js:154-170`）。
- 德式数字：翻译器自带千分位规则作为 b2b-core `tv_woo_b2b_german_figures()` 缺席时的后备（`translator.php:235-313`）。
- 系统提示词说 "controller is Verantwortlicher"（`translator.php:1442-1443`），后处理再用正则在技术语境把 `Verantwortlicher` 改回 `Controller`（`translator.php:166-175`）——同一个词两条相反规则靠正则调和。
- 审校德语两处来源：仓库 fixture 与线上表。

**写死的词汇、正则表、产品知识**
- 型号识别启发式与例外表（`SUB|MAX|MIN|GEN|TOP`，`translator.php:320-342`）；技术邻词表（`translator.php:171`）；提示词里写死产品名与示例（"AI Saving 3.0"、"GW10K-ET"、"16.38 kWh"，`translator.php:1431-1433`）。
- 商品载荷字段白/黑名单、单位表、句子判定（`product.php:71-144, 227-417`）。
- 厂商功能名白名单（`banned-vocabulary.json`）、分类名与分类 slug（两个 JSON）——目录知识写在翻译插件里，新增分类必须发插件。
- 路由里的 Woo 路径与查询键表（`router.php:315-347, 411-463`）。
- 自家邮箱写死（`linker-i18n.php:537`）。

**缺陷史（来自代码注释与工单，说明整页字符串替换的脆弱）**
"Markenchutz"、"Batterienpannung"（`chrome.php:88, 134, 209`）、"Allee Dokumente"（`chrome.php:24`）、"GoodWe Lynx Startseite F"（`chrome.php:333`）、"Kontakt the Partner and Engineering Desk"（`jobs.php:219`）、德语首页 83 个链接只有 1 个是德语（`render.php:254`）、222 个值 114 个商品带英文千分位（`translator.php:181`）、62 处型号被改坏（`translator.php:396`）、505 个规格值留英文（`product.php:92`）、118 处审校行用错词（`translator.php:1385`）、隐私页 "spezialisierte Prozessoren"（`translator.php:1438`）、同类补丁连续五个版本 0.5.14–0.5.22（`chrome.php:137-138`）。翻译器注释里的审查轮次一路到 "twenty-fifth round"。

**`.scratch` 工单**
在 tip 上提到 i18n/德语的 400 个 md：146 done/delivered、5 in-progress、7 open、1 prepared、1 wontfix。当前没有以 i18n 缺陷为主题的 open 工单；相关的未结事项：148（评审站"德语词典还没同步"，`.scratch/prototype-to-site/issues/147-map.md:54`）、Advisor 重构 014（设计画布的德语动态输出、locale 传递、PDF 本地化缺陷）与 022（新增 `packages/i18n`）、183（新字段沿用现有翻译队列与新鲜度规则）。

### A5 健全性判断

- **健全**：服务端渲染、单对象存储（德语挂在原对象上，商品只有一行，库存/价格/SKU/ERP/物料绑定都不需要同步）、翻译离线做、按字符串缓存、词表 + 校验、hreflang/canonical/sitemap 实现正确、失败时退回英文而不是坏页。
- **不健全**：整页 `strtr`（chrome map）把 gettext 该做的事改成事后字符串替换，事故率高、性能有代价；没有后台运营面；德语审校分散且英文改版会冲掉页面手改；SEO 有一票否决式 noindex、自动跳转、200 重复页等风险；死代码和无用的 discovery 镜像持续制造部署与审查成本；跨插件耦合深。

---

## B. 外部方案（Apify 取证）

### B5 2026 年不花钱做 EN+DE WooCommerce 的现实选项

| 方案 | 2026-10 状态 | 对本站的含义 | 来源 |
|---|---|---|---|
| Polylang（免费） | v3.8.10，80 万+安装，测试到 WP 7.1.3。翻译模型：每种语言一篇独立文章/术语互相关联。FAQ："Is Polylang compatible with WooCommerce? You need Polylang for WooCommerce, premium addon"。DeepL 机器翻译、slug 翻译只在 Pro | 免费版管不了商品 | 1 |
| Polylang for WooCommerce | 1 站 99 €/年（年度许可，续费半价）；卖点含"跨译本同步库存""同步价格/分类/属性/图片"；机器翻译要 Polylang Pro | 付费，违反 Law 3；也说明孪生商品必须同步库存价格 | 2 |
| Hyyan WooCommerce Polylang Integration（唯一免费桥） | "closed as of October 5, 2026… pending a full review"；6 年未更新，测试到 WP 5.6 | 不可用 | 3 |
| TranslatePress（免费） | v3.3.7，40 万+安装；免费版只能一种翻译语言（EN+DE 够用）；Woo "out of the box"；自动翻译可用自己的 Google API key，或 TP AI Free 2,000 词；SEO Pack（翻译 title、description、**URL slug**、alt、OG）与 DeepL 是付费附加 | 免费版德语 URL 与 meta 不译，SEO 比现状差 | 4、5 |
| TranslatePress 的架构 | 源码：`ob_start(array($this,'translate_page'))`，"@param string $output Entire HTML page as string"，用 `str_get_html` 解析整页，再 `get_existing_translations` 查字典替换 | 与 linker-i18n 的 chrome map 是同一种"整页输出缓冲 + 字符串字典"做法，换过去不是走向存储式翻译 | 6 |
| MultilingualPress | v5.3.0（2026-09-07），基于 multisite，starter 149 €/年（2 种语言）；wp.org 上的免费旧版 2.11.3 测试到 WP 5.2、50+ 安装 | 付费；免费版已死；还要改成 multisite | 7、8 |
| WPML | 按要求排除（付费） | — | — |
| WordPress 核心多语言（Gutenberg Phase 4） | 官方路线图：Phase 3（协作）进行中；Phase 4 "Multilingual — Core implementation for Multilingual sites" 仍是远期项；2026 大目标里没有多语言；下一个版本 7.2 计划 2026-12-10。Phase 4 是 2018 年宣布的 | 近期指望不上 | 9、10 |
| DeepL API Free | 官方文档：免费 API 计划走 `api-free.deepl.com`；第三方 2026-05-28 文章：免费 50 万字符/月，Pro 5.49 美元/月 + 25 美元/百万字符；API 支持 glossary 与 style rules | 可作为备选引擎，但它的 glossary 只是术语对照，表达不了本站词表的 `never/unless/sense` 规则 | 11、12、13 |
| AutoPoly – AI Translation for Polylang（免费） | v1.6.3（2026-10-08），5,000+ 安装；免费版用浏览器内置 AI（Chrome/Edge）或 Yandex，在编辑器里逐篇翻译后存成 Polylang 译文；OpenAI/Gemini/DeepL/批量是付费 | 存储式，但前提是 Polylang（商品又回到付费问题），且无自定义词表 | 14 |
| Loco Translate（免费） | v2.8.9，100 万+安装；后台直接编辑 `.po/.mo`，可接 DeepL、Google、Microsoft、OpenAI API（自备 key），有受保护的自定义翻译目录 | **UI 文案**的 WP 原生、免费、店员可用方案 | 15 |
| WooCommerce 正式德语（Sie）语言包 | translate.wordpress.org：German (Formal) stable 98%（14,336 条），已生成语言包 | 可替代 `email-voice.php` 这类覆盖层 | 16 |
| Google 指引 | 不同语言用不同 URL + hreflang；"Avoid automatically redirecting… don't redirect based on what you think the user's language may be"；hreflang 需互相回链；scaled content abuse 的例子包括"借助翻译等自动变换批量生成、几乎不给用户提供价值的页面"——自家内容的合格译本不在此列，但质量要把关 | 现有 URL 结构正确；JS 自动跳转应去掉；翻译质量仍要把关 | 17、18、19 |

结论：2026 年不存在一个免费、成熟、能把 WooCommerce 商品德语"存成内容"并带 SEO slug 的插件。免费路径要么商品管不了（Polylang），要么本身就是整页字符串替换且 SEO 功能付费（TranslatePress），要么付费或已死（MLP、WPML、Hyyan）。核心多语言还没开工。WordPress 原生、免费、成熟的只有两块：gettext 体系（含 Loco Translate 与官方语言包，包括正式德语）和"每语言独立 URL + hreflang"的 SEO 规范。

### B6 三条路线对比（约束：Linker 无人读德语；德语由 AI 生成，按词表产出，由 AI 线按 Law 6 修正案审校）

**路线 K：原样保留 linker-i18n**
- SEO：正确但脆弱（一票否决式 noindex、自动跳转、200 重复页、DE 慢 0.3–0.9 s）。
- 店员运营：差。只有商品可在后台改德语；页面/SEO/分类/开关都要开发机脚本 + 临时 Snippet 桥；英文改版会冲掉页面手改德语。
- Woo-first：一半。内容翻译这块 Woo 生态确实没有免费答案，自研合理；但 UI 文案用整页 strtr 重造 gettext、用覆盖层代替正式德语包，不合 Law 3。
- 维护面：最大（插件近 9k 行 PHP + 插件外约 2 万行工具/测试/fixture + 每次改版的一次性脚本 + 384 KB 无用镜像）。

**路线 R：换成 Polylang 式存储翻译 + 带本站词表的 AI 翻译任务**
- 免费 Polylang 不支持 Woo，必须买 99 €/年的扩展（违反 Law 3）；免费桥已下架。
- 每种语言一个商品 = 每个物料两行商品，与 ADR-0032（商品是运行时台账）、ADR-0034（`mat_product_<id>`）、ADR-0031（ERP 按 SKU 推库存）直接冲突；SKU 唯一、库存/价格同步、订单里的商品 ID、物料绑定全要重写或靠付费同步。
- 若只把页面/文章交给 Polylang、商品留在自研，则 /de/ 有两个路由所有者，商品 URL 要迁移；LiveCanvas 页眉页脚/模板与 Polylang 的兼容性未知（未验证）。
- AI 翻译任务 + 词表 + 校验无论如何都得自研（没有免费插件能用自定义"禁译"规则驱动 LLM）。换掉的只是存储与路由，而这两块现在恰恰是好用的。
- 若换成 TranslatePress 免费版：架构上就是现在的 chrome map 的通用版，且德语 slug/meta 不译，SEO 倒退。
- 结论：成本最高、风险最大、与现有台账决策冲突，不推荐。

**路线 H：hybrid——保留核心、向 WordPress 原生收拢、瘦身**
保留：`/de/` 路由与 slug 表、`Linker_I18n_Lang`/locale、德语存在原对象 meta（这正是"存储式翻译"想要的性质，只是不复制对象）、翻译任务 + 词表 + 校验、hreflang/canonical/sitemap。
改变（按价值排序，不是工单清单）：
1. UI 文案只走 gettext：b2b-core `__()` + `.po`，店员可用 Loco Translate 在后台改（需定好 `.po` 的唯一权威位置）；装 Woo/WP 的 `de_DE_formal` 包，删 `email-voice.php` 覆盖；`commerce-strings-en.json`、字面量对照表、runtime 应急字典逐步退场；Advisor 重构的 React 应用用 WP 原生 JS 翻译（`wp_set_script_translations` / make-json），不再造第八套。
2. 缩小整页 strtr：分类名改为 term meta（后台可编辑），SEO 文案按对象存德语并由现有 SEOPress 过滤器读取；最终只剩 LiveCanvas 页眉页脚/模板仍依赖配对替换（能否改成渲染时换存储德语，需要先查 LiveCanvas 的渲染入口）。
3. 运营搬进后台：页面/文章与商品一样有中德并排面板；任务状态/待办/拒绝原因可见；页面英文改版按句保留德语（商品已有同类逻辑），不再需要一次性脚本和 Snippet 桥；审校德语只有一个权威来源。
4. SEO 修正：按页 noindex 取代整站一票否决，就绪度量纳入商品；删 JS 自动跳转（改成提示条）；/de/ 下英文 slug 一律 301；404/noindex 页不出 hreflang；商品载荷加与正文一致的新鲜度门；校验器加数字对等与完整性检查。
5. 删除：`discovery-surfaces/`、两个惰性 `should_translate_source` 过滤器、sensitive-context 过滤器（含 b2b-core 那个）、`render_identity`、缓存类里的旧门控分支、过时注释与清单。

| 维度 | K 保留 | R 替换 | H 混合 |
|---|---|---|---|
| SEO 正确性 | 正确但有结构性风险 | 免费路线会倒退（slug/meta 或 Woo 不可用） | 保留正确部分并去掉风险 |
| 店员运营 | 差 | 付费 Polylang 后台熟悉，但商品双份维护 | 好（后台面板 + Loco） |
| Woo-first | 部分 | 免费版做不到 Woo；付费违规 | 最好（gettext、正式语言包、单商品台账） |
| 维护面 | 最大 | 新增同步与迁移代码 | 明显缩小 |

**推荐：H（hybrid）。最有力的三条理由：**
1. **没有可替换的免费存储式方案**：Polylang 管商品要付费扩展，唯一免费桥已下架；TranslatePress 免费版本身就是整页字符串替换且不译 slug/meta；MLP 付费、核心 Phase 4 未启动。linker-i18n 的"单对象 + 德语 meta"是唯一同时满足 Law 3（不买插件）与 ADR-0031/0032/0034（一个商品一行）的做法，替换它买不到任何东西。
2. **问题集中在重造了 WordPress 原生能力的那几层**：整页 strtr 代替 gettext、覆盖层代替正式德语包、仓库 fixture + Snippet 桥代替后台编辑——事故史、7 套文案机制、24 个一次性脚本都出在这里。把它们换成 gettext/Loco/de_DE_formal/后台面板，正好是 Law 3 与 Law 4 要求的方向。
3. **实测核心是好的，风险是具体可修的**：德语服务端渲染、hreflang/canonical/sitemap 正确、20 个商品只有 1 处遗漏；要修的是一票否决 noindex、自动跳转、200 重复页、DE 首字节开销和 384 KB 无用镜像（占插件 68/121 次提交）——都是局部改动，不需要推倒重来。

---

## 来源（Apify `apify/rag-web-browser`，抓取时间 UTC 2026-10-09）

1. https://wordpress.org/plugins/polylang/ — 05:38:01Z
2. https://polylang.pro/pricing/polylang-for-woocommerce/ — 05:38:23Z
3. https://wordpress.org/plugins/woo-poly-integration/ — 05:38:51Z
4. https://wordpress.org/plugins/translatepress-multilingual/ — 05:38:45Z
5. https://translatepress.com/pricing/ — 05:39:17Z
6. https://plugins.svn.wordpress.org/translatepress-multilingual/trunk/includes/class-translation-render.php — 05:50:48Z
7. https://multilingualpress.org/ — 05:40:42Z
8. https://wordpress.org/plugins/multilingual-press/ — 05:40:53Z
9. https://en-nz.wordpress.org/about/roadmap/ — 05:40:14Z
10. https://wptavern.com/how-will-gutenberg-phase-4-impact-multilingual-solutions-for-wordpress（发表于 2019-03-26）— 05:40:13Z
11. https://developers.deepl.com/docs/getting-started/quickstart — 05:41:35Z
12. https://chatscontrol.com/blog/deepl-api-pricing-plans-limits-2026（第三方，2026-05-28）— 05:42:49Z
13. https://www.deepl.com/en/products/api — 05:43:35Z
14. https://wordpress.org/plugins/automatic-translations-for-polylang/ — 05:41:20Z
15. https://wordpress.org/plugins/loco-translate/ — 05:48:10Z
16. https://translate.wordpress.org/locale/de/formal/wp-plugins/woocommerce/ — 05:48:03Z
17. https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites — 05:44:11Z
18. https://developers.google.com/search/docs/specialty/international/localized-versions — 05:44:28Z
19. https://developers.google.com/search/docs/essentials/spam-policies — 05:44:21Z

未用作证据：第一次 Google 检索命中的 GPL 转售站（gplkit.com）。DeepL 官方 API 价格页为动态加载，未能抓到正文，故 50 万字符的数字只有第三方来源。

## 局限

- 未读线上数据库（字典表规模、job log、pending 列表），相关数字来自代码注释与文档。
- TTFB 是从本机网络测的 3 次中位数，只作相对比较。
- 20 个商品的数字比对是启发式，确认的遗漏只有 1 处，误报已逐条人工核对。
- LiveCanvas 与 Polylang 的兼容性、LiveCanvas 渲染入口能否直接换存储德语，未验证。
