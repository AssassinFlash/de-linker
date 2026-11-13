# 全站验收三矩阵台账清洗批次（Batch 1）核查报告

- 日期：2026-11-13
- 范围：只读核查 `docs/acceptance/2026-10-22/full-site/` 下 `page-matrix.json`（708 行）、`state-matrix.json`（1044 行）、`template-matrix.json`（31 行）、`findings.md` 与 `docs/acceptance/2026-11-10/goal-state-ledger.md`；未修改任何仓库已跟踪文件。
- 生产访问与资源纪律：仅执行只读 `curl -I` 与无表单提交的 Playwright Headless Chromium 探针；临时脚本 `tests/e2e/audit-batch1.tmp.mjs` 已在运行结束后删除，零账号/询盘/邮件副作用。
- 提案文件：`docs/acceptance/2026-11-13/matrix-batch-updates/batch1-rows.json`（共 74 条行更新提案）。

---

## 一、核查过程

1. **基线解析**：用 Python 遍历 `page-matrix.json`、`state-matrix.json`、`template-matrix.json`，统计 `not-applicable`、`findings[]` 非空行、`partial-with-finding` 行及 `status != pending` 但 `evidence == []` 的行。
2. **仓库与证据交叉核对**：对照 `git log`（2026-10-22 至 2026-11-13）、`tests/e2e/artifacts/`、`tests/e2e/specs/`、`docs/acceptance/` 历史目录与 `/Users/chesterjohn/de-linker-data/` 收据 JSON，定位每条遗留 finding 的修复提交与版本边界。
3. **生产只读探针实测（2026-11-13）**：
   - `curl -sS -o /dev/null -w "%{http_code} %{redirect_url}" -I` 探测 Trina 8349/8350 EN/DE URL（2 条）与全部 EcoFlow EN URL（21 条）。
   - Playwright（`tests/e2e/node_modules/@playwright/test` Chromium）只读访问 `de/produkte/@390`（点击 2 项 client-side compare 控件检测固定栏几何与重叠）、`de/kundendienst/@390`、`GoodWe ETR EN/DE`、`GoodWe ESA 6321 EN`、`SAJ ATS1-T63-A 6839 DE`、`de/blog/` 与两篇 DE 博文、`de/?s=&post_type=post`、`de/?s=Notstrom&post_type=post` 切 EN、`products/?q=xyzzy-nonexistent` / `de/produkte/?q=xyzzy-nonexistent`、`de/loesung/heimspeicher/`（1440/390）。

---

## 二、四项重点任务结论

### 1. Trina 参考件 8349 / 8350（`page-matrix.json` 共 4 行）

- **现状**：`8349@1440`、`8349@390`、`8350@1440`、`8350@390` 的 `render` 与 `visual_review` 均为 `"not-applicable"`，但 **`interaction` 仍残留 `"pending"`**；此外缺少 EcoFlow 84 条不适用行具备的 `product_detail_applicability` 字段。
- **对比同类型行**：`page-matrix.json` 其余 84 条 `render: "not-applicable"` 行（EcoFlow 下架产品）均严格满足 `render == interaction == visual_review == "not-applicable"`。
- **生产核实**：`curl -I` 实测 `https://de-linker.com/product/trina-solar-tsm-460neg9r-28/` 与 `https://de-linker.com/de/produkt/trina-solar-tsm-460neg9r-28/` 均返回 **HTTP 404**（无重定向），`inventory-baseline.json` 确认 `engineering_role: "reference_pv_module"`，Publication 设计上不向客户公开渲染 PDP。
- **提案**（`batch1-rows.json` 4 条）：将 4 行的 `interaction` 补齐为 `"not-applicable"`，并补全 `product_detail_applicability`（`status: "not-applicable"`）。

### 2. 未核销的 PR #664 与 PR #734 finding

#### (a) `mobile-compare-chip-covers-account`（`https://de-linker.com/de/produkte/@390`）
- **原问题**（`findings.md:206-210`）：390 视口下浮动 `Vergleichen` 胶囊 `(20, 700, 151.75, 48)` 遮挡卡片 `Konto erstellen` `(33, 705.08, 102.66, 44)`。
- **修复与生产实测**：PR #664（`096cc3bef`）将移动端比较入口改为页头下方 52px 固定顶栏（收据 `production-mobile-compare-header.json`）。2026-11-13 Playwright `390x844` 实测 `https://de-linker.com/de/produkte/` 勾选 2 款产品后：`[data-compare-chip]` 位于 `x:0, y:81, w:390, h:52, bottom:133`（紧贴 `#lc-header` 下缘 `bottom:81`）；卡片 `.linker-create-account`（`Konto erstellen`）在首屏下方 `x:33, y:842, w:103, h:44`，`overlaps: false`；左下角 `(40, 720)` 已无任何比较胶囊（`elementFromPoint` 命中页面 Cookie 横幅而非比较控件）。
- **提案**（`batch1-rows.json` 1 条）：清空 `findings: []`，在 `resolved_findings` 与 `verified_checks.account_cta_under_compare_chip`（`status: "pass"`）记录 PR #664 与 2026-11-13 探针证据。

#### (b) `withdrawn-english-old-slug-redirects-to-german-draft`（实为 **42 行**）
- **数量勘误**：任务说明提及“20 行 EcoFlow EN 产品”，经精确统计 `page-matrix.json` 中携带该 finding 的行实际为 **21 个唯一 EN URL × 2 视口（`@1440` / `@390`）= 42 行**（产品 ID：`3555, 3574–3582, 3608–3609, 6480–6488`，与 `findings.md:523` 及 `public-product-verification.json#production_readback_20261028` 记载的 21 个 EN URL 完全吻合）。
- **修复与生产实测**：PR #734（`fe7550a9e`）在 `GermanUrlMigration::old_post` 要求同语言已发布目标。2026-11-13 `curl -I` 逐一探测全部 21 个 EN URL：**21/21 直接返回 HTTP 404，且 `redirect_url` 均为空**（不再 301 跳转 DE 草稿 query）。
- **提案**（`batch1-rows.json` 42 条）：全部 42 行清空 `findings: []`，迁入 `resolved_findings`，并将 `verified_checks.withdrawn_product_current_public_route_20261028.status` 置为 `"pass"`。

### 3. `state-matrix.json` `authentication` 三行 `status=pass` 但 `evidence=[]`

核查目标行：
- `authentication:pending-submit:de:1440`
- `authentication:registration-success:de:1440`
- `authentication:password-email-confirmation:de:1440`

**证据排查结果**：
1. **`tests/e2e/artifacts/`**：
   - `tests/e2e/artifacts/report.json` 仅保留最近一次运行记录（2026-11-11 `planner-country-rules.spec.ts` 3 条用例），无任何 `account.spec.ts` 或 `pending-account.spec.ts` 记录。
   - `tests/e2e/artifacts/pending-out*/` 仅含历史失败重试目录（`.last-run.json` + `error-context.md`），无测试名、时间或断言记录。
2. **`docs/acceptance/`**：
   - `docs/acceptance/2026-10-18/222/`（`verification.md`、`matrix.json`、`screens/de-1440-register.png`、`de-1440-registered.png`、`de-1440-pending-inquiry.png`、`de-1440-pending-account.png`）记录了 `c222` 上 `de:1440` 注册与待审工作台，但日期为 **2026-10-18**，早于 PR #589（两步注册控件）、PR #678（登录校验）、PR #1003（Proforma→Quotation 改名）、PR #1015（重写 `pending-account.spec.ts`）与 PR #1061/#1067。
   - `docs/acceptance/2026-10-13/account-auth/`（`README.md`、`shots/de-lost-password.png`）日期为 **2026-10-13**（`t110`），早于账号重设计 PR #187 与 PR #678/#751/#1055。
   - `docs/acceptance/2026-11-09/de-1440-remaining-surface-release.json:19` 虽口头汇总 `"pending_account": "de 1440 passes on c222 in 30.5s"`，但无独立可追溯单用例输出文件。
   - **`docs/acceptance/2026-11-10/goal-state-ledger.md:154-159`**：明确判定这些行来自 `42feb9a637`（2026-11-08）的批量改状态，且“an earlier attempt to backfill them with run-family evidence was rejected as unverifiable and reverted; the rows stay flagged here for dedicated re-verification instead”。

**结论**：**无当前版可复用证据，全部标记“需本地实例补跑”**（`batch1-rows.json` 提案将 3 行暂时回退为 `status: "pending"` 并在 `findings` 中锁定精确补跑 spec）。

> **附带台账发现**：同次提交 `42feb9a637` 遗留的另外 **4 行** `status: "pass"` 且 `evidence: []` 的 `de:1440` 行同样存在相同问题（详见第四节补跑清单）：`account:overview-pending:de:1440`、`account:overview-approved:de:1440`、`account:account-details:de:1440`、`genie:thinking:de:1440`。另有 11 条 `status: "partially-verified"` 行 `evidence: []`（但均在 `verified_checks` 内带具体收据路径）。

---

## 三、疑似可核销清单（任务 4 全量扫描）

### A. `page-matrix.json` 非空 `findings` 全量排查

| 矩阵行 / 范围 | Finding ID / 内容 | 相关提交 / PR | 2026-11-13 核查方法与生产结果 | 结论 |
|---|---|---|---|---|
| `de/kundendienst/@390` (`6700`, 1 行) | `services-audience-tabs-small` (`partial-with-finding`) | PR #701 (`c8e5126c9`), PR #889 (`ed68d1c3f`) | Playwright `390x844`：两个受众 tab 实测 `fontSize: 14px`、`lineHeight: 19.6px`、`height: 44px`、`width: 174px`，`scrollWidth: 390` | **可核销**（`visual_review` → `partially-verified`） |
| GoodWe ETR `3595@1440`, `6654@390` (2 行) | `etr-manual-only-pairing-labelled-compatibility-list` | `a316a69ac` (`ProductShortcodes::pairing_status`) | Playwright EN/DE PDP：`GW208.9-BAT-LCD-G10` 实测显示 `Partially documented` / `Teilweise dokumentiert`，`GW261.2` 显示 `Documented by GoodWe` / `Von GoodWe dokumentiert` | **可核销** |
| GoodWe ESA `6321@1440` (1 行) | `pdp-6321-article-product-terminology` | 术语清洗（`commerce-terms` 系列） | Playwright EN PDP：实测文本为 `"This product is one cabinet..."` 与 `"(separate device, not part of this product)"`，`"This article"` / `"not part of this article"` 为 0 命中 | **可核销** |
| SAJ ATS1-T63-A `6839@1440`, `@390` (2 行) | `saj-ats-de-faq-grammar` (`im ATS Box`) | `66c31e373` + FAQ 同步 | Playwright DE PDP 全文 `textContent`：`im ATS Box` 0 命中，对应断路器 FAQ 已更新为 `"in der Einheit oder im externen Verteiler montiert"` | **可核销** |
| DE 博文 `6887@390`, `6889@390` (2 行) | `blog-de-independent-cover-alt-english` | PR #747 (`c89ca5a0c`, `CoverAlt.php`) | Playwright `390x844`：6887 封面 alt=`"GoodWe Lynx Home F Hochvolt-Batterie"`，6889 封面 alt=`"Eine GoodWe-Batterie und ein Hybrid-Wechselrichter sind an der Außenwand eines Hauses montiert."`，相关卡 img alt=`""` | **可核销** |
| DE Heimspeicher `6923@1440`, `@390` (2 行) | `DE heading auto-hyphenation and English default planner media remain OPEN` | PR #721 (`b74b9b18a`), PR #722 (`c7b82be46`) | Playwright `1440/390`：`.lk-h2`/`.lk-h3` 均已为 `hyphens: manual`，`tool-pane-0` 默认预览已是德语 `planner-de.jpg`（`pane-1` 为 `...-de-poster.webp`）；但 `H1.lk-hero-title` CSS 仍为 `hyphens: auto`（当前文本未断词），`tool-pane-2` 视频仍为英文 `linker-advisor-lookup-for-installers.mp4` | **部分解决，收窄保留余项**（不直接核销） |

### B. `state-matrix.json` 非空 `findings` 全量排查

| 矩阵行 / 范围 | 原 Finding 内容 | 相关提交 / PR | 2026-11-13 核查方法与结果 | 结论 |
|---|---|---|---|---|
| `global-navigation:search-empty:en:390`, `de:390` (2 行) | `product search with q only ... says to clear a filter` | PR #751 (`1ef69c11b`) | 行内 `verified_checks.751_product_q_only_empty` 已标 `resolved-by-751-production-readback`；Playwright 实测 `/products/?q=xyzzy-nonexistent` 与 `/de/produkte/?q=xyzzy-nonexistent` 均只提示换搜索词，无清除筛选提示 | **可核销** |
| `blog:index:de:1440`, `blog:article-related:de:390` (2 行) | `DE linked/related card image alts leak English` | PR #746 (`03a58911d`) | Playwright `/de/blog/`（前 12 卡）与 6887/6889 相关卡 `img` 全部实测为 `alt=""` | **可核销** |
| `blog:search-results:de:390` (1 行) | `cleared journal search has an empty H1` | PR #746 (`03a58911d`) | Playwright `/de/?s=&post_type=post` 实测 `h1="Alle Beiträge"`、`title="Alle Beiträge \| Linker"` | **可核销** |
| `blog:search-pagination-query-preserved:de:390` (1 行) | `DE-to-EN journal search retains lang=de` | PR #746 (`03a58911d`, `LanguageLinks.php`) | Playwright `/de/?s=Notstrom&post_type=post` 实测 EN 切语言 href 为 `https://de-linker.com/?s=Notstrom&post_type=post`（无 `lang=de`），落地页 `htmlLang="en-US"`、`h1="Notstrom"` | **可核销** |
| `genie:ordinary-draft-failure-owner-isolation` (4 行) | 发现期描述 `repair and final browser/production readback pending` | `ac5bfe319` (`genie-failure-ownership.spec.ts`) | 4 行 `status` 已为 `pass`（`goal-state-ledger.md:72-75` 2026-11-10 差分跑绿）；`findings[]` 为未同步清理的旧文 | **可核销**（迁入 `resolved_findings`） |
| `genie:dock-keyboard-focus-escape-and-return` (`en/de × 390/1440`, 4 行) | Batch A 手机端 Continue / 390 侧栏解锁待办 | PR #1050 (`9d17eb4e9`), PR #1082 (`157576b4b`), `fba99fdc2` | `390` 两行 `findings[]` 内已自带 `resolved 2026-11-11`；`1440` 两行挂着错位描述的手机 Continue 旧文，相关契约已全闭环 | **可核销**（迁入 `resolved_findings`） |
| `genie:lazy-bundle-failure-retry-close-focus` (4 行) | PR #717 修复描述 + 剩余入口边界 | PR #717 | 实为 PR #717 修复说明与边界备注（行 `status: partially-verified`） | **保留边界说明**（暂不核销） |

### C. `findings.md` 正文里已被后续 PR 解决的遗留描述（供文档收敛参考）

- `findings.md:26`（住宅页 `#system-search` 发送仅跳转、附件/语音 disabled）：已由 `entries.ts` 与 PR #1046 解决，`state-matrix` `marketing-genie-entry` 32/32 `verified-production-20261107`。
- `findings.md:54-55`（比较页裸加号/英文类别/切语言丢 ids）：已由 PR #661（`findings.md:184-192`）与 PR #753（`findings.md:560`）解决。
- `findings.md:75`（住宅与商用 hero textarea 无关联 label）：已由 PR #889（`ed68d1c3f`，`entries.ts:45-59` 以 placeholder 补齐 `aria-label`）解决。
- `findings.md:87, 109`（共享 sticky 页头透出底层文字）：`chrome.css` 已改为不透明白底；`known-defects-probe.json:165-220` 实测 5 页 `headerBg: "rgb(255, 255, 255)"`、`headerBackdrop: "none"`。
- `findings.md:109`（Contact DE hero 断词）：`findings.md:579` 已记录“德语标题溢出与确认页无效 key 两个真实缺陷全链修复并生产实证”。
- `findings.md:206`（`mobile-compare-chip-covers-account`）：PR #664 + 2026-11-13 实测已解决。
- `findings.md:523`（`withdrawn-english-old-slug-redirects-to-german-draft`）：PR #734 + 2026-11-13 `curl -I` 21/21 实测已解决。
- `findings.md:548`（Genie Turnstile Error 300030）：2026-11-11 生产真人家访实测通过（`goal-state-ledger.md:420-431`，单号 #8703/#8704）。
- `findings.md:581-587`（剩余 556 pending 执行地图）：已由 2026-11-10 至 2026-11-11 批次清空（`goal-state-ledger.md:587` 当前 `state-matrix` 0 pending）。

---

## 四、需后续本地实例补跑的清单

### 必跑（任务 3 指定）

| 矩阵 Key | 精确 Spec 文件 | 精确用例 / 断言范围 | 所需本地实例 |
|---|---|---|---|
| `authentication:pending-submit:de:1440` | `tests/e2e/specs/pending-account.spec.ts` | `de 1440: register → pending workspace and inquiry → approve in the same session`（提交两步注册、验证会话与 pending 工作台及询盘开放） | `c222`（spec 第 51 行硬校验 `instance().name === 'c222'`） |
| `authentication:registration-success:de:1440` | `tests/e2e/specs/pending-account.spec.ts` | `de 1440: register → pending workspace and inquiry → approve in the same session`（验证注册成功落地 `/de/mein-konto/`、session cookie 建立、Outbox 含注册邮件主题） | `c222` |
| `authentication:password-email-confirmation:de:1440` | `tests/e2e/specs/account.spec.ts` | `de-1440: the lost-password request answers and its link opens the new-password card`（注意：现有 spec 验证提交重置请求后出现 `.woocommerce-message` 及通过 WP-CLI reset key 重设密码；若需严格断言 Outbox 重置邮件正文/链接，建议同跑时校验 `linker-mail` spool） | `review` |

### 顺带发现的同源空 Evidence 行（来自 `42feb9a637`，建议一并归档报告 JSON）

| 矩阵 Key | 精确 Spec 文件 | 精确用例 | 所需本地实例 |
|---|---|---|---|
| `account:overview-pending:de:1440` | `tests/e2e/specs/pending-account.spec.ts` | `de 1440: register → pending workspace and inquiry → approve in the same session` | `c222` |
| `account:overview-approved:de:1440` | `tests/e2e/specs/pending-account.spec.ts` | `de 1440: register → pending workspace and inquiry → approve in the same session` | `c222` |
| `account:account-details:de:1440` | `tests/e2e/specs/account.spec.ts` | `de-1440: account details save names its error and keeps the typing` | `review` |
| `genie:thinking:de:1440` | `tests/e2e/specs/genie-reply-presentation.spec.ts` | `de 1440` 思考中状态（waiting state） | `review` |
