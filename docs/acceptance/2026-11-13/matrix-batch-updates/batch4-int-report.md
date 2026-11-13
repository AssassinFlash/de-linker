# Batch 4 剩余 368 行产品/分类只读交互验证与生产修复复核报告

- **执行日期**：2026-11-13
- **验收环境**：生产站 `https://de-linker.com`（全程匿名只读；严禁加购提交、询盘提交或任何生产写入；Playwright 路由层硬拦截 `add-to-cart=` 与写接口 POST）
- **浏览器资源预算**：单实例无头 Chromium（4 并发页面复用工作池），任务结束已全部关闭并清理全部 `tests/e2e/b4int-*.tmp.mjs` 临时脚本。
- **产出文件**：
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch4-int-rows.json`（415 条行级更新提案：368 行 `interaction` 升级 + 222 行生产修复复核归档，交集 175 行）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/postfix-verified.json`（12 组共 67 次带 `?v=<random>` 边缘缓存穿透探针原始数据）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch4-captures/interactions-remaining-368.json`（368 行只读交互逐行探针原始回执）

---

## 一、368 行 `product` + `term` 只读交互全量扫描统计

从 `docs/acceptance/2026-10-22/full-site/page-matrix.json` 提取全部 `kind in ("product", "term") && interaction === "pending"` 行（共 **368 行 = 184 个独立 URL × 1440×900 / 390×844**）：

| 类别 | 独立 URL 数 | 矩阵行数 | HTTP 200 | `0` `pageerror` | 只读交互通过 | 提案目标状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `product`（在售商品详情页） | 158 | 316 | **316 / 316** | **316 / 316** | **316 / 316** | `interaction: "partially-verified"` |
| `term` · Woo 产品归档（`product_cat` 16 + `pa_phase` 2） | 18 | 36 | **36 / 36** | **36 / 36** | **36 / 36** | `interaction: "partially-verified"` |
| `term` · 博客分类归档（`category` 8） | 8 | 16 | **16 / 16** | **16 / 16** | **16 / 16** | `interaction: "partially-verified"` |
| **合计** | **184** | **368** | **368 / 368** | **368 / 368** | **368 / 368（0 失败）** | **`368` 行升级 `partially-verified`** |

### 验证覆盖与边界说明
- **Product 页（316 行）**：HTTP 200、`0` `pageerror`；存在多组规格 Tab（`[role="tab"]` ≥ 2）时实点第 2 个 Tab 并断言 `aria-selected === "true"`；存在 `.pdp-faqs details` 时点击展开并断言 `open === true`；`#downloads` 文档链接数量 `>0` 且全部 `href` 有效；加入草稿按钮（`a.pdp-btn-dark[href*="add-to-cart="]`）经 `click({ trial: true })` 实测可见可点（不触发加购写入，加购留本地 e2e 覆盖）；Compare 按钮（`[data-compare-product]`）实点切换 `aria-pressed="true"` 并二次点击还原 `"false"`；页头配对语言切换链接可见且指向对应 EN/DE 商品 URL。
- **Term 产品归档页（36 行）**：HTTP 200、`0` `pageerror`；390px 先点开 `#product-filter-open` 抽屉（`aria-expanded="true"`），再对 `#sidebar-filters details > summary.filter-title` 执行展开/收起双向切换断言；`#sort-select` 存在、选项完整且 `focus()` 聚焦成功；首张产品卡链接有效；页头配对语言切换链接有效。
- **Term 博客分类归档页（16 行）**：HTTP 200、`0` `pageerror`；390px 页头菜单 `<details class="tv-mobile-navigation">` 展开/收起正常；`#journal-search` 搜索框聚焦正常（不提交）；主题链接与首篇文章卡链接有效；页头配对语言切换链接有效。

---

## 二、今日已部署修复的生产逐项复核结果（`?v=<random>` 绕过缓存）

所有探针均附带随机查询参数 `?v=<random>` 穿透边缘/页面缓存直接验证生产当前状态，详见 `postfix-verified.json`：

| 检查项 / Finding ID | 抽样/全量探针规模 | 生产实测核心数据 | 结论 | 影响矩阵行数 |
| --- | --- | --- | :---: | ---: |
| `pdp-related-grid-before-pseudo` | 8 个 EN/DE `@1440` PDP（6 个四卡页 + 2 个三卡页） | `.pdp-related ul.products::before` `content: "none"`, `display: "none"`；首卡 `x = 80`，4 卡同排（`x = 80, 405, 730, 1055`，`sameRow: true`） | **PASS (8/8)** | 170 |
| `pdp-faqs-silently-dropped` & `saj-ats-de-faq-grammar` | 全部 9 对 = **18 个 EN/DE URL**（`1178/6839`、`1179/6838`、`1181/6837`、`1182/6836`、`1183/6835`、`1184/6834`、`2003/6769`、`2394/6717`、`2397/6716`） | 18/18 页 `.pdp-faqs` 均渲染出有效 `<details>`（1–3 条）；`/de/produkt/saj-ats1-t63-a/` 含 `"in der ATS-Box"` 且 0 处 `"im ATS Box"` | **PASS (18/18)** | 36（含 `6839` 2 行语法项） |
| `pdp-feature-white-bg-contrast` | 4 个 EN/DE `@1440` URL（`2092/6736`, `2093/6735`） | `.pdp-feature-media::after` 均渲染 `linear-gradient(90deg, rgba(16, 44, 48, 0.96) 0%, rgba(16, 44, 48, 0.85) 48%, rgba(16, 44, 48, 0) 76%)` 衬底遮罩 | **PASS (4/4)** | 4 |
| `pdp-de-feature-h3-unhyphenated-wrap` | `6689` (`@1440`, `@390`) + `6720` (`@390`) | 全部 `.pdp-section-title` 计算样式 `hyphens === "auto"`、`scrollWidth <= clientWidth`，按音节断词（`Netzbezugsbeg- / renzung`、`Nulleinspeisungsr- / egelung`），0 处孤立单双字母硬拆 | **PASS (3/3)** | 3 |
| `archive-de-card-facts-dt-overflow` | `625@390` + `632@390` | 全部 40 个 `.card-facts dt` 计算样式 `overflowWrap === "anywhere"`，`0` 处 `scrollWidth > clientWidth` | **PASS (2/2)** | 2 |
| `services-hero-display-overflow-x`（含 `6700@390` `services-audience-tabs-small` 清理） | `2748@1440`、`6700@1440`、`6700@390` | `@1440` `.service-hero-display` 字号上限 `96px`，宽 `855.8px / 880.7px <= h1ClientWidth`，`overflowPx = 0`；`@390` 受众 Tab `14px / 44px` | **PASS (3/3)** | 3 |
| `de-solution-scale-tab-label-overflow` | `/de/loesung/@390` (`6871`) | 3 个 `.sol-tab-label` 均 `maxWidth === "none"`，`scrollWidth === clientWidth`（`104 / 183 / 120px`） | **PASS (1/1)** | 1 |
| `de-installer-mobile-desktop-input-exposed-placeholder-clipped` | `/de/fuer-installateur/@390` (`6869`) | 桌面 `.lk-console-input-row` `display === "none"`，`#installer-mobile-query` 可见（`312×68px`）且占位符完整无裁切；本行 `interaction` 从 `partial-with-finding` 恢复为 `partially-verified`（注：`#tools` 阶段 03 英文演示视频 `de-installer-english-genie-preview-media` 仍如实保留） | **PASS (1/1)** | 1 |
| `de-heimspeicher-hero-hyphens-auto-omission` | `/de/loesung/heimspeicher/` (`@1440`, `@390`) | `#tv-rs-page-v1 .lk-hero-title` 计算样式 `hyphens === "manual"`，0 溢出；`#tool-pane-0` 为 `planner-de.jpg`（注：`#tool-pane-2` 英文演示视频 `de-heimspeicher-toolpane2-english-media` 仍如实保留） | **PASS (2/2)** | 2 |
| `legal-refund-returns-2713-backslash-stripped` & `legal-privacy-latent-2713-css-backslash-stripped` | 4 个法务页 × `1440/390` = 8 视图（`1038`, `6698`, `1673`, `6827`） | 内联 `<style>` 无 `content:"2713"`；退货页 `#section-4` 全部 3 个 `li::before` 渲染 `"\"✓\" / \"\""` | **PASS (8/8)** | 8 |
| `blog-cover-attachment-alt-empty` & `blog-de-independent-cover-alt-english` | 6 篇博客共 10 视图（`559`, `560`, `6899`, `6901` × 2 + `6887@390`, `6889@390`） | 全部 `.reader-cover img` `alt` 非空，4 篇德语博客均为地道德语描述 | **PASS (10/10)** | 10 |
| `document-generic-source-labels` | `2003`、`6769` PDP + `/faq-download/?tab=documents` + `/de/faq-dokumente/?tab=documents` | `pylontech-l260-pp20-21.pdf` 显示 `Brochure · PDF · EN` / `Broschüre · PDF · EN`；文档库筛选栏 `0` 处 `Document 1` / `Dokument 1` | **PASS (4/4)** | 4 |
| `pdp-6321-article-product-terminology` | `6321/6599`、`3573/6676` | 正文与规格 `0` 处产品指代意义的 `article`/`Artikel`（仅保留欧盟法规条文引用 `Articles 10, 12 and 14` / `Artikel 10, 12 und 14`） | **PASS (4/4)** | 8 |
| `etr-manual-only-pairing-labelled-compatibility-list` | `3595` (EN)、`6654` (DE) | `GW208.9-BAT-LCD-G10` 均显示 `Partially documented` / `Teilweise dokumentiert`，无兼容列表误标 | **PASS (2/2)** | 2 |

---

## 三、未通过项报警与合并注意事项

1. **未通过项报警**：**0 项**。本次 368 行只读交互扫描与 12 组共 67 次生产修复缓存穿透探针 **100% 通过**。
2. **如实保留的真实未关闭项（共 6 行 = 3 个德语营销页 × 2 视口，不属本次代码修复范围）**：
   - `/de/fuer-installateur/@1440` & `@390`：`de-installer-english-genie-preview-media`（需录制真实德语 Genie 演示视频）
   - `/de/loesung/gewerbespeicher/@1440` & `@390`：`de-commercial-toolpane2-english-media`
   - `/de/loesung/heimspeicher/@1440` & `@390`：`de-heimspeicher-toolpane2-english-media`
   模拟合并验证确认：应用 `batch4-int-rows.json` 后，全站 708 行矩阵中 `product`（340 在售行）、`term`（140 行）、`post`（40 行）的 `interaction` 与 `visual_review` 全部达到 `partially-verified`（`0` `pending`、`0` `partial-with-finding`），活跃页面仅剩上述 6 行保留真实视频素材待办。
3. **父代理合并脚本提示（重要）**：
   - `batch4-int-rows.json` 中凡 `findings_mode === "replace"` 的条目，`updates.findings` 已精确计算为剔除已解决项后的剩余数组（清空或仅留未关闭视频项），**合并时请直接赋值替换 `row.findings = entry.updates.findings`，切勿做数组拼接**（此前 `a48a16c47` 合并 `batch1-rows.json` 时因拼接保留了 `/de/produkte/@390` 与 42 条 EcoFlow `not-applicable` 行已移入 `resolved_findings` 的旧 `findings` 项，建议父代理合并时顺带按 `Object.keys(row.resolved_findings)` 过滤一次残留同名 `findings`）。
