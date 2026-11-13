# 产品页与分类归档验收批次（Batch 4）报告

- **日期**：2026-11-13
- **范围**：`docs/acceptance/2026-10-22/full-site/page-matrix.json` 中全部 `render=preliminary-pass` 且 `interaction=pending` 的 `product`（340 行 = 170 在售 EN/DE SKU URL × 1440/390；Trina 8349/8350 参考件 4 行已 `not-applicable` 跳过）与 `term` 非品牌入口（72 行 = 36 EN/DE URL × 1440/390，含 `product-category` 20、`category` 10、`phase` 4、`battery-voltage` 2 URL），**合计 412 行（206 个独立 URL）**。
- **操作边界**：全程生产只读（无表单提交、无加购写入、无仓库已跟踪文件修改），仅通过 Playwright 浏览、只读 HTTP GET/HEAD、只读 WP-CLI 元数据核查与视觉 API 完成验收；所有临时脚本均已清理。
- **产出文件**：
  - 行更新提案：`docs/acceptance/2026-11-13/matrix-batch-updates/batch4-rows.json`（412 条）
  - 证据目录：`docs/acceptance/2026-11-13/matrix-batch-updates/batch4-captures/`（`layout-selfcheck-all-412.json`、`interactions.json`、`vision-review.json`、`dom-verify.json`、`dom-verify2.json`、`dom-audit-verify.json`、`visual-reps.json`、`screenshots-manifest.json`、`screenshots/` 120 张全页截图）

---

## 一、覆盖统计总览

| 验收维度 | 覆盖范围 | 执行结果 | 核心结论 |
| --- | --- | --- | --- |
| **机械布局全量** (`tests/visual/layout-selfcheck.mjs`) | **412/412 行**（206 URL × 1440×900 & 390×844，0 缺口，无需补跑） | **412/412 HTTP 200**、`0` failedLoads、`0` consoleErrors、**`0` defect**、`968` review | 全部 412 行 `render` 升级为 `verified-basic-production`；review 中 `966` 为 `<24px` 文本链接/折叠标题，`2` 为 390px 德语 `<dt>` 溢出 `9px` |
| **视觉轴分组抽样** (`deepseek-flash` + DOM/像素探针) | 60 URL × 2 视口 = **120 张全页截图**（`visual-reps.json`：85 EN 商品的全部 42 组结构签名 + 10 DE 代表页 + 8 分类归档代表页） | `119/120` 有效 JSON（**`66 PASS`、`53 ISSUE`、1 `PARSE_ERR`**），经 `dom-verify*.json` 与 `dom-audit-verify.json` 复核过滤误报，实锤 **4 类视觉/CSS 缺陷** | 实锤：`1440px` `.pdp-related` `::before` 网格错位（170 `@1440` 产品行）、`2092`/`2093`/`6735`/`6736` `.pdp-feature` 白字叠白底图、`de-6689@1440/390` 与 `de-6720@390` 无连字符断词、`term-625/632@390` `<dt>` 溢出 `9px` |
| **只读交互轴** (`Playwright`) | 12 个代表 PDP（EN/DE）× 2 视口 = 24 行；10 个代表 Term（4 种 taxonomy EN/DE）× 2 视口 = 20 行（**共 44/412 行直接实测**） | **44/44 上下文 HTTP 200**、`0` console/page errors；已渲染控件全部交互通过（其中 `390x844` `Ask`/`Ask Genie` 按钮在 `interactions.json` 同步 `scrollIntoView` 时因落于视口下方返回 `clickable: false`，经 `locator.click({trial:true})` 复核确认可正常滚动点击）；同时发现 **9 个商品（18 页）生产静默丢失 FAQ** | **仅 44 条实测行 `interaction` 升级为 `partially-verified`**，其余 **368 条未实测行严格保持 `pending`** |
| **全量 HTTP 复核** (`170` 在售商品页) | 全部 170 个 EN/DE 商品页 | `170/170` HTTP 200；144 页有 FAQ、26 页 0 FAQ（含 16 页库内有 FAQ 但前端静默丢失，另有 `2397/6716` 丢 1/2 条）；仅 `2003/6769` 仍含 `Document/Dokument` 元信息；`0` 处客户可见 `this article`/`dieser artikel` | 与 WP-CLI 根因排查完全吻合 |
| **矩阵提案分布** (`batch4-rows.json`) | 412 行 | `render`：412 `verified-basic-production`；`interaction`：44 `partially-verified` / 368 `pending` | `visual_review`：**216** `partially-verified`，**196** `partial-with-finding` |

---

## 二、Self-check Defect 与 Review 明细

`docs/acceptance/2026-11-13/matrix-batch-updates/batch4-captures/layout-selfcheck-all-412.json` 已全量覆盖 340 个在售产品行与 72 个非品牌分类归档行（**无任何剩余缺口**），汇总 **0 个 `defect` 级别问题**，共 **968 条 `review` 级别条目**：

1. **`overflow-x-visible`（2 条，确认缺陷）**：
   - `390x844` `/de/produkt-kategorie/zubehoer/`（`term-625`）第 6 张产品卡 `dl.card-facts > div:nth-of-type(4) > dt`：`"Kommunikationsadressbereich"` `scrollWidth=163 > clientWidth=154`（溢出 `9px`）。
   - `390x844` `/de/produkt-kategorie/zubehoer/energiezaehler-stromwandler/`（`term-632`）第 3 张产品卡同位置 `dt`：`"Kommunikationsadressbereich"` 溢出 `9px`。
2. **`small-target`（966 条，既有行内文本链接/折叠控件复核）**：
   - `.pdp-stats-context > summary`：224 条（`20.1px` 高，全宽行）
   - `nav.pdp-crumbs > a`：170 条（面包屑返回链接）
   - `.pdp-price > a.pdp-price-login` / `a.linker-create-account`：各 170 条（未登录价签内联链接）
   - `#sidebar-filters summary.filter-title`：100 条（桌面侧栏折叠标题）
   - `article.sf-card a.sf-card-title`：78 条（单行产品卡标题）
   - `.linker-contact-invitation a.linker-contact-email`：52 条（底部邮箱链接）
   - `#linker-products .wb-metarow a`：2 条

---

## 三、重点缺陷根因诊断与修复提案（未实施）

### A. 本次重点排查的 4 项已知缺陷

#### 1. `pdp-6321` 正文用 `"article"` 指代产品（`goodwe-esa-gw125-261-esa-lcn-g10`）
- **生产实测状态**：EN 页面（`6321`）与 DE 页面（`6599`）当前 HTML 均已正确输出 `"This product is one cabinet..."`、`"(separate device, not part of this product)"` 与 `"Dieses Produkt ist ein Schrank"`、`"nicht Teil dieses Produkts"`；170 个商品页全量扫描亦为 0 处产品语义的 `this article`/`dieser artikel` 漏网，仅保留欧盟法规 `"Regulation (EU) 2023/1542 Articles 10, 12 and 14"` / `"Artikel 10, 12 und 14"`。
- **底层数据根因**：虽然 `6321` 的 `post_excerpt` 与 `_tv_legacy_acf_json` 已修正，但源商品 **`6321`** 与 **`3573`** (`saj-esolar-aio3`) 的 **`_linker_de_acf_json`** 原始 meta 仍残留 `"Artikel"` / `"Artikels"` 字样，目前依赖 `plugins/linker-commerce/includes/Products/Materials.php:934-982` 的 `terms_in()` / `GERMAN_TERMS` 运行时字符串替换掩盖。
- **修复提案**：备份后通过 WP-CLI 清理 Post `6321` 与 Post `3573` 的 `_linker_de_acf_json` meta 中的 `"Artikel"` 旧词（`Dieser Artikel` → `Dieses Produkt`、`dieses Artikels` → `dieses Produkts`、`diesen Artikel` → `dieses Produkt`），消除对运行时替换的隐性依赖。

#### 2. `ETR/GW208.9` 手册配对被误标 `"On GoodWe compatibility list"`（`3595` / `6654`）
- **生产实测状态**：**已修复，可核销**。`plugins/linker-commerce/includes/Presentation/ProductShortcodes.php:1586-1598` 的 `pairing_status()` 对 `status === 'one_way'` 输出 `"Partially documented"`（DE `"Teilweise dokumentiert"`），原 `"On %s's compatibility list"` 在 `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po:6969-6973` 已废弃为注释条目。
- **验证证据**：生产 GET 实测 `https://de-linker.com/product/goodwe-etr-125-kw-ci-three-phase-hybrid-inverter-1000v/` 与 `/de/produkt/goodwe-etr-125-kw-ci-dreiphasiger-hybridwechselrichter-1000v/`，`GW208.9-BAT-LCD-G10` 均显示 `Partially documented` / `Teilweise dokumentiert`，`GW261.2-BAT-LCD-G10` 显示 `Documented by GoodWe` / `Von GoodWe dokumentiert`。

#### 3. `SAJ ATS1 DE FAQ "im ATS Box"` 语法（`6839` / `1178`）→ **牵出 P1 缺陷：9 个商品（18 页）FAQ 静默丢失**
- **生产实测状态**：
  1. 文案自身已在 Post `1178` / `6839` 的 `_linker_faqs` 中修正，生产全页 `"im ATS Box"` 为 0 命中。
  2. **但生产页面 `/product/saj-ats1-t63-a/` 与 `/de/produkt/saj-ats1-t63-a/`（及另外 8 个商品 EN/DE 页）FAQ 区块静默丢失！** 全量 170 页 HTTP 扫描实锤 **26 页**渲染 0 条 FAQ：其中 **16 页（8 个商品）** 与 `2397/6716`（丢 1/2 条）合计 **9 个商品（18 个 EN/DE 产品页 = 36 矩阵行）** 库内存在有效 FAQ 却被静默过滤（其余 5 个商品 `2281/1955/1957/6529/1946` 共 10 页自身无 FAQ）：
     - **6 个 SAJ 商品（`1178`、`1179`、`1181`、`1182`、`1183`、`1184`）**：`Faqs::of($id)` 共有 15 条有效 FAQ，但直接改写 `_linker_faqs` 后 `Publication::figure_revision($entry)` 哈希变化，而 `_linker_publication_faqs` 仍保存旧哈希键，导致 `EvidenceBindings::matches_faq()`（`plugins/linker-commerce/includes/Products/Publication/EvidenceBindings.php:320-337`）返回 `false`。同时，`EvidenceBindings::repair_unchanged()`（`EvidenceBindings.php:170-220`）仅处理 `self::META_KEY`（`_linker_publication_figures`），未处理 `self::FAQ_META_KEY`。
     - **3 个商品（`2003` 1/1 丢失、`2394` 2/2 丢失、`2397` 1/2 丢失）**：`_linker_faqs` 中的 `citation.url` 仍指向已下线/返回 `HTTP 410` 的旧版 PDF URL（`optim_us_l260_omni.pdf` 与 `GW_Smart-Meter-EU_User-Manual-EN_V1.5.pdf`），不在当前 `document_rows($id)` 允许集合内。
- **修复提案**：
  1. **代码修复**（`plugins/linker-commerce/includes/Products/Publication/EvidenceBindings.php:170`）：在 `repair_unchanged()` 中补充 `self::FAQ_META_KEY` 的同文件未变续绑逻辑（仅在 `document_id` 与 `blob_sha256` 不变时刷新 `figure_revision` 键）；批量修正 FAQ 的工具链路同步调用 `EvidenceBindings::capture_faqs($id)`。
  2. **数据修复（先完整备份）**：对 `1178, 1179, 1181, 1182, 1183, 1184` 刷新 `_linker_publication_faqs`；核对新 PDF 页码后更新 `2003`、`2394`、`2397` 的 FAQ `citation.url` 为现行托管 datasheet/manual URL 并重新绑定 `capture_faqs()`。

#### 4. `6 份公开 PDF 源元数据泛名 "Document"`（`findings.md:402`）
- **生产实测状态**：原 6 份泛名 PDF 已在 PR #693 中修复，但全量 170 页扫描与 `/faq-download/?tab=documents` 实测仍残留 **1 份**泛名类别条目：`2003` / `6769`（`Pylontech OPTIM US L260-OMNI`）下的 `pylontech-l260-pp20-21.pdf`（标题 `Pylontech Utility, C&I ESS product portfolio PY2412EN-SD - L260-OMNI: PDF pp. 20-21 (EN)`），在 PDP 渲染为 `Document · PDF · EN` / `Dokument · PDF · EN`，在 `/faq-download/` 类型芯片栏渲染为 `Document 1`。
- **修复提案**：将 Post `2003` 上 `pylontech-l260-pp20-21.pdf` 的元数据由 `document`/`Document`/`Dokument` 改为 `DocumentLibrary::TYPE_ORDER` 中已有的 `brochure` 类别（`_linker_documents[].type = "brochure"`、`download_role = "brochure"`、EN `download_type = "Brochure"`、DE `download_type = "Broschüre"`）。

---

### B. 本轮新发现的代码与视觉缺陷及修复提案

#### 5. **P1 · `.pdp-related ul.products::before` 导致全部 1440px 产品页相关商品网格错位**
- **根因定位**（`dom-verify2.json#en6528_related_grid` + `plugins/linker-commerce/content/windpress/pdp.css:1353`）：`#tv-storefront-pdp .pdp-related ul.products` 为 4 列 Grid，但未清除 WooCommerce `ul.products::before { content: " "; display: table; }`，导致第 1 列被伪元素占位，卡片 1–3 右移至 `x=405/730/1055`，卡片 4 折行至 `x=80, y=5728`。全量扫描确认 170/170 EN/DE 商品页均含 `.pdp-related`，影响全部 170 条 `@1440` 产品行。
- **修复提案**：在 `plugins/linker-commerce/content/windpress/pdp.css:1360` 后补充：
  ```css
  #tv-storefront-pdp .pdp-related ul.products::before,
  #tv-storefront-pdp .pdp-related ul.products::after {
      content: none;
      display: none;
  }
  ```

#### 6. **P2 · `saj-bu3` (`2093/6735`) 与 `saj-bc2` (`2092/6736`) `.pdp-feature` 白字叠白底图低对比度**
- **根因定位**（`dom-verify.json#en-2093` + `dom-audit-verify.json#en2092_1440_feature` + `pdp.css:797-816`）：`.pdp-feature-media` 为 `position: absolute; inset: 0` 且无渐变遮罩（`mediaAfterBg: "none"`），而 `.pdp-feature-copy` 为白色 `#fff`（`x=80..720`）。当采用宽幅白底图（`delinker-saj-bu3.jpg` / `delinker-saj-bc2-768x335.jpg`）时，白色背景伸入左侧文本区导致文字可读性严重下降。
- **修复提案**：在 `plugins/linker-commerce/content/windpress/pdp.css:800` 为 `.pdp-feature-media::after` 添加左侧深色渐变遮罩（如 `linear-gradient(90deg, rgba(16, 44, 48, 0.96) 0%, rgba(16, 44, 48, 0.85) 48%, rgba(16, 44, 48, 0) 76%)`）或限制桌面端 `.pdp-feature-image` 仅占右侧区域。

#### 7. **P2 · 德语分类归档 390px 卡片 `dl.card-facts dt` 复合词溢出 9px**
- **根因定位**（`layout-selfcheck-all-412.json` + `plugins/linker-commerce/content/windpress/products.css:173-174`）：规则仅为 `.card-facts dd` 设置 `overflow-wrap: anywhere`，未设置 `.card-facts dt`，导致 `term-625@390` 与 `term-632@390` 上 `"Kommunikationsadressbereich"` 实宽 `163px > 154px`。
- **修复提案**：在 `plugins/linker-commerce/content/windpress/products.css:173` 的 `.card-facts dt` 规则中补充 `overflow-wrap: anywhere;`。

#### 8. **P2 · 德语 `.pdp-section-title` 无连字符任意断字（`de-6689@1440/390`, `de-6720@390`）**
- **根因定位**（`dom-verify2.json#de6689_1440`, `de6720_390` + `vision-review.json`）：`.pdp-section-title` 启用 `overflow-wrap: anywhere; hyphens: manual;` 时，`"Netzbezugsbegrenzung an Bord"` 与 `"Nulleinspeisungsregelung"` 因缺软连字符在字母间硬折（`Netzbezugsbegrenzu / ng`、`Nulleinspeisungsregelu / ng`）。建议在数据/文案中插入 `&shy;` 软连字符或微调手机端字号下限 `clamp`。
- **附注（`en-2064` 兼容脚注重复句）**：`dom-verify2.json#en2064_pairings` 显示 3 条脚注均拼接相同前 3 句说明，仅末句不同，导致 `ProductShortcodes.php:1564-1567` 字符串去重未合并；可在后续文案整理中提炼公共系列约束。

---

## 四、视觉模型误报复核记录（`deepseek-flash` vs DOM 探针）

对 `vision-review.json` 全部 **53 条 `ISSUE`** 及 **1 条 `PARSE_ERR`** 逐类执行 DOM 探针核实（`dom-verify.json`、`dom-verify2.json`、`dom-audit-verify.json`）：

| 视觉模型报告的问题类型 | 代表截图 | DOM 探针复核证据与实测值 | 判定 |
| --- | --- | --- | --- |
| 固定 Cookie 横幅遮挡正文 / 隐形折线文本 | `en-6530-1440`, `en-3557-390`, `en-4106-1440` | `dom-verify.json#intro_overlap`：实际文档流 `introRect.top=786.3` 无重叠；`position: fixed` 底栏在 `fullPage` 截图首屏折线处重绘 | **误报（视口折叠伪象）** |
| 粘性页头 `'DE'` 按钮与灰条重叠正文 | `en-3573-1440`, `de-6690-1440` | `dom-verify.json#en-3573`：`#lc-header` 为 `position: sticky`，分段滚动截图将其绘入页面中部 | **误报（粘性页头截图伪象）** |
| 390px 顶部锚点条 `'Documents'` 裁切为 `'Docu'` | `en-2394-390`, `en-2403-390`, `en-3557-390`, `en-6530-390` 等 9 张 | `dom-verify.json#section_nav`：`#product-sections .sf-container` `overflowX="auto"`, `scrollWidth=475 > clientWidth=390`，属设计横向滚动条；整页 `scrollWidth=390` 无溢出 | **误报（横向滚动条边缘裁切）** |
| 相关商品 / 兼容配对缩略图显示灰色占位块 | `en-1184`, `en-1948`, `en-1973`, `en-2093`, `en-2394`, `en-3556`, `en-6511`, `de-6752` 等 19 张 | `dom-audit-verify.json#imageAudit` 显式等待全页懒加载 `img.complete` 后，**19/19 页面 `relatedBroken: 0`**（唯一 `brokenCount=1` 为页面空 `src=""` 零宽高占位标签，非商品图）；原 `screenshots-manifest.json` 在 `complete` 未就绪时即截图导致灰块 | **误报（懒加载截图时序伪象）** |
| `de-6720-1440` 产品描述行重叠 | `de-6720-1440` | `dom-audit-verify.json#de6720_1440_desc` 与复核探针：4 个 `.pdp-benefit` 卡片为非重叠 2×2 网格（`y=1318..1440`, `1456..1602`），3 个 `details.pdp-disclose` 均处于 `open: false` 折叠态（`y=1634..1697`, `1697..1761`, `1761..1824`） | **误报（折叠内容盒子/首屏伪象）** |
| `en-2070-390` 页脚 Logo 裁切破损 | `en-2070-390` | `dom-audit-verify.json#en2070_390`：`footerLogo` 实测 `natW=717, natH=273, rect=91×34.6px, overflow=false` | **误报（视觉模型切片错觉）** |
| `term-1-product_cat-de-1440` 侧栏筛选项文字被截断 | `term-1-product_cat-de-1440` | `dom-audit-verify.json#term1_sidebar`：`#sidebar-filters` 共 70 个标签，`clipped: []`（0 处溢出/裁切） | **误报（视觉模型 OCR 幻觉）** |
| 页脚与正文拼写错字（`"Deutscher"`, `"Allrights"`, `"GoodWeBAT-C"`, `"Stromaribtrage"`, `"NETZGEEKOPPELT"`, `"Heimspieler"`）及 `en-2409` 图片错配 | `en-2199-390`, `en-3612-390`, `en-1958-1440`, `de-6769-1440`, `de-6836-1440`, `de-6798-390`, `en-2409-390` | `dom-verify.json#footer_text`、`dom-verify2.json#en1958_docs`、`dom-verify.json#emanager_img`：DOM 实测均为 `"Deutsch"`, `"All rights reserved."`, `"GoodWe BAT-C Series"`, `"Heimspeicher"`，且 `en-2409` 相关卡为 `our-saj-emanager-studio-300x300.jpg`（SAJ 原厂模块） | **误报（视觉模型 OCR/压缩幻觉）** |
| `term-5-battery_voltage-en-1440` 视觉模型返回空 JSON (`PARSE_ERR`) | `term-5-battery_voltage-en-1440` | `dom-audit-verify.json#term5_bv_en_1440`：`h1="High Voltage"`, `scrollW=1440/clientW=1440`, `cards=8`, `brokenImgs=0`；`layout-selfcheck-all-412.json` 0 defect | **已用 DOM 探针补验通过** |
| `.pdp-related` 首行右移留空第 1 列 | `en-6528-1440`, `en-1957-1440` | `dom-verify2.json#en6528_related_grid`：`ul.products::before` `content: " "; display: table` 占用网格第 1 列 | **实锤缺陷（提案 #5）** |
| `.pdp-feature` 白字与白底图重叠 | `en-2093-1440`, `en-2092-1440` | `dom-verify.json#en-2093` + `dom-audit-verify.json#en2092_1440_feature`：`mediaAfterBg="none"`, `copyColor="rgb(255, 255, 255)"` | **实锤缺陷（提案 #6）** |
| 德语 `.pdp-section-title` 无连字符硬折 | `de-6689-1440/390`, `de-6720-390` | `dom-verify2.json#de6689_1440/de6720_390`：`overflowWrap: "anywhere", hyphens: "manual"`，德语复合长词无 `&shy;` 时硬折 | **实锤排版缺陷（提案 #8）** |
