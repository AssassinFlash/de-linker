# `state-matrix.json` 114 条 `partially-verified` 收口与 `findings.md` 核查报告

- **日期**：2026-11-13
- **核查范围**：
  1. `docs/acceptance/2026-10-22/full-site/state-matrix.json`（全表 1,044 行）中全部 **114 条 `status == "partially-verified"`** 状态行（覆盖 11 个 family、45 个 `(family, state)` 组合）；
  2. `docs/acceptance/2026-10-22/full-site/findings.md` 全文（588 行）中所有曾标记 `OPEN` / 待修 / 待发布的条目及今日最新合入修复的生产实效复核。
- **边界与生产纪律**：
  - 未修改 `docs/acceptance/2026-10-22/full-site/` 下任何已跟踪基线文件（仅输出提案文件供父代理统一合并）；
  - 生产探针严格执行匿名只读 HTTP `GET`/`HEAD` 与 Playwright Headless Chromium DOM/键盘/客户端校验检查（**0 次表单提交、0 个测试账号或询盘创建、0 封邮件触发、0 次 `/genie/turn` 模型调用**）；
  - 未启动或新增任何本地 WordPress 实例。
- **交付产物**：
  - `docs/acceptance/2026-11-13/matrix-batch-updates/state-pv-rows.json`（114 条结构化更新记录，376,512 bytes）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/state-pv-report.md`（本报告）

---

## 一、11 族 114 行收口总览

| Family | 原 `partially-verified` 行数 | 升级 `verified-production-20261113` | 升级 `pass` | 诚实保留 `partially-verified` | 同步清空残留 `findings[]` | 核心闭环依据摘要 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `blog` | 17 | 17 | 0 | 0 | 3 | 补齐全部 `390` 视口生产实测（索引/分类/越界分页/检索保留/折叠目录/44px 分享与 CTA/封面 `alt`） |
| `legal` | 14 | 14 | 0 | 0 | 0 | 补齐全部 8 篇法务页 `390` 视口生产实测（含 `7d8ebe52e` 修复 Refund/Rückgabe `✓` 伪元素与 29 反斜杠读回） |
| `taxonomy-routing` | 16 | 16 | 0 | 0 | 0 | `#548` 68 路由基线 + 2026-11-13 补验 `ecoflow-ocean2-plus-hd-p1-s2` 200、`?phase=3` 22 卡切语言保留与越界分页 `301` |
| `product-archive` | 5 | 5 | 0 | 0 | 0 | `12150da77` 修复 `/de/produkte/` LC DT `6961` + PR #1069 参数对齐已上线；`390/1440` 多重筛选、跨页去重（24+9=33）与 `Clear all` 保留 `q` 通过 |
| `global-navigation` | 11 | 9 | 0 | **2** | 2 | 顶栏键盘遍历/Esc 归还焦点、全站搜索、无结果空态、四类路由切语言保留参数共 9 行通过；账户子端点 `en:390`/`de:390` 因客户端 `#fragment` 未跨语言携带保留 2 行 |
| `contact` | 4 | 4 | 0 | 0 | 0 | 补齐无 `?source=` 的纯净 `/contact/`、`/de/kontakt/` `1440/390` 初始空态生产实测（无来源卡、吸顶白底不透字） |
| `authentication` | 2 | 2 | 0 | 0 | 0 | 补齐 `en:390`/`de:390` 登录空提交聚焦、44px Remember me 与两步注册客户端必填/网站或 VAT 二选一拦截实测 + `account.spec.ts` |
| `inquiry` | 12 | 0 | 12 | 0 | 0 | `inquiry-draft-actions.spec.ts`、`public-inquiry.spec.ts`、`draft-visual-states.spec.ts` 已在 `en/de × 1440/390` 全 4 组合跑绿 |
| `account` | 10 | 3 | 3 | **4** | 0 | `company` (3) 与 `inquiry-details-and-statuses` (3) 凭生产实测 + PR #874/#1003/#1067 闭环；`saved-solutions-populated` (4) 因缺 `planning-projects` 浏览器列表行 e2e 保留 |
| `files-and-feedback` | 7 | 4 | 3 | 0 | 0 | `private-document-*` (3) 凭 PR #1067/#1089 + 生产匿名 403/404 零字节探针闭环；`design-report-pdf` (4) 凭 PR #1070/#1089/#1102/#1110 生产四视口 A4 PDF 读回闭环 |
| `genie` | 16 | 4 | 12 | 0 | 4 | `lazy-bundle-failure-retry-close-focus` (4) 生产拦截 `genie.js` 实测全部 6 项契约通过；`document-card`/`citations`/`signed-facts-and-units` (12) 凭生产真问读回 + `genie-history-artifacts.spec.ts` 全表面 12 用例闭环 |
| **合计** | **114** | **78** | **30** | **6** | **9** | **108 / 114 行（94.7%）实证升级收口；6 行（5.3%）定位精确缺口诚实保留** |

---

## 二、逐族实证核查明细

### 1. `blog`（17 行 → 17 行 `verified-production-20261113`）

- **历史停留原因**：`blog-legal-states-20261108.json` 仅执行了 `1440` 桌面视口，导致 `en:390`（8 行）与 `de:390`（9 行）停留在 `partially-verified`；其中 `blog:article-related:de:390`、`blog:search-results:de:390`、`blog:search-pagination-query-preserved:de:390` 还残留着 PR #746 修复前的旧 `findings[]`。
- **2026-11-13 生产 `390×844` 实测数据**：
  - `index`（`/blog/`、`/de/blog/`）：HTTP 200，各渲染 10 张文章卡、6 个分类胶囊，整卡链接内图片 `alt=""`（`nonEmptyCardImgAlts=0`，无英文 `alt` 泄露），`scrollWidth=390`。
  - `category`（`/category/battery-storage/`、`/de/kategorie/batteriespeicher/`）：HTTP 200，各 2 张文章卡，`hasPagination=false`，`scrollWidth=390`。
  - `pagination` & `pagination-out-of-range`：当前 10 篇文章单页容纳无多余分页；`/blog/page/2/`、`/blog/page/99/` 稳定 `301` 回 `/blog/`，`/de/blog/seite/2/`、`/de/blog/seite/99/` 稳定 `301` 回 `/de/blog/`；带检索词越界 `/page/99/?s=Notstrom&post_type=post` 与 `/de/seite/99/?s=Notstrom&post_type=post` 返回本地化 HTTP 404 恢复模板且 `scrollWidth=390`。
  - `search-results` / `search-empty` / `search-pagination-query-preserved`：`/?post_type=post&s=storage`（9 篇，保留 `storage`）、`/de/?post_type=post&s=Notstrom`（4 篇，切 EN 链接为 `https://de-linker.com/?s=Notstrom&post_type=post`，无 `lang=de` 残留）、特殊字符 `Speicher "Backup" & Netz` 原样保留、清空词 `/de/?s=&post_type=post` H1=`"Alle Beiträge"`、无结果 `/de/?post_type=post&s=xyzzy-nonexistent-20261113` 0 卡无分页保留原词；`/blog/page/2/?s=storage` `301` 至 `/blog/?s=storage` 保留查询串。
  - `article-contents` & `article-related`：`390` 下 `.reader-toc` 默认折叠（`summary` 高度 `51.5px >= 44px`），点击展开并点选 `#article-hybrid-inverter` 滚至吸顶栏下方（`targetTop > headerBottom=81px`）；4 个分享按钮 `minHeight=44px`，正文 CTA 高度 `44.2px`；3 张相关文章卡图片 `alt=""` 且点击整卡准确跳转目标文章；4 篇独立封面图博文（含今日 `7d8ebe52e` 补齐的 `residential-storage-backup-self-consumption` 与 `ci-storage-peak-shaving-backup-scalability` 英德配对）`alt` 全部为非空对应语言描述。

### 2. `legal`（14 行 → 14 行 `verified-production-20261113`）

- **覆盖行**：`icons`、`section-anchor`、`copy-anchor-feedback`、`back-to-top`、`cross-document-navigation`、`language-switch`、`repeat-save-backslashes` 的全部 `en:390` 与 `de:390`（共 14 行）。
- **2026-11-13 生产 `390×844` 全 8 篇法务文档实测**：
  - `icons` & `repeat-save-backslashes`：`/imprint/`、`/privacy-policy/`、`/terms-of-sale/`、`/refund-returns/` 及其 4 篇德语配对页 `scrollWidth=390`；正文 `u003c` 泄露 `false`；今日提交 `7d8ebe52e` 已在线上修复 `/refund-returns/` 与 `/de/rueckgabe-erstattung/` 第 4 节列表伪元素（`getComputedStyle(li, '::before').content == '"✓"'`，`raw2713Leak=false`）；可见 SVG 图标包围盒全部大于 0；8 页 `#tv-legal-js` 反斜杠计数恒为精确 `29` 个且重复读取一致。
  - `section-anchor`：点击移动端折叠目录按钮展开后跳转 `#section-4`，章节落点 `y≈141px > headerBottom(81px)` 且当前项高亮。
  - `copy-anchor-feedback`：点击第 1 节复制链接按钮，URL 更新为 `#section-1`，`.lg-tip[data-state="ok"]` 显示 `"Link copied"` / `"Link kopiert"`。
  - `back-to-top`：深滚至页面底部后激活回到顶部控件，`window.scrollY` 归 `0` 且清空 hash。
  - `cross-document-navigation` & `language-switch`：底部关联法务卡片点击直达对应语言目标页（HTTP 200）；从 `/privacy-policy/#section-2` 切 DE 落至 `/de/datenschutz/#section-2`，再切回 EN 落至 `/privacy-policy/#section-2`，双向完整保留 `#section-2`。

### 3. `taxonomy-routing`（16 行 → 16 行 `verified-production-20261113`）

- **证据闭环**：复用 `#548` 68 个共享品牌/系列归档路由基线（`docs/acceptance/2026-10-31/548/INDEX.md:1229-1242`），并由 2026-11-13 生产 HTTP + `1440/390` 浏览器探针补齐全部遗留细项：
  - 10-31 唯一出现瞬时连接中断的 `/series/ecoflow-ocean2-plus-hd-p1-s2/` 与 `/de/series/ecoflow-ocean2-plus-hd-p1-s2/` 实测均为 **HTTP 200**（分别命中 `LC DT ID: 231` `en-US` 与 `LC DT ID: 6905` `de-DE`）。
  - 5 对 `product_brand` / `pa_brand` 同 slug 别名（`goodwe`、`saj`、`chint`、`pylontech`、`ecoflow`）统一收敛至规范品牌归档路由，EN/DE 产品家族数完全一致：GoodWe `24 + 14 = 38`、SAJ `13`、Chint `1`、Pylontech `1`、EcoFlow `0`（空态隐藏排序下拉并保留浏览出口）、BAT-C `3`、ETA-G20 `8`、SAJ HS3 `1`。
  - `/brand/goodwe/?phase=3` 与 `/de/brand/goodwe/?phase=3` 在 `1440/390` 下精确渲染 `22` 张三相产品族卡片，页头语言切换链接双向保留 `?phase=3`；越界第 3 页 `?product-page=3` 在 EN/DE 下均 `301` 跳回 `?product-page=2`。

### 4. `product-archive`（5 行 → 5 行 `verified-production-20261113`）

- **前置线上修复验证**：
  - 提交 `12150da77` 已在生产生效：`https://de-linker.com/de/produkte/` 现稳定输出 `<!-- LC DT ID: 6961 -->`（结构化 `shop-page` 模板，修复了此前落入 `6905` 的路由缺陷）；
  - PR #1069（`723030766`）已在生产生效：`/de/produkte/?anwendung=home` 与 `/de/produkte/?application=home` 返回一致产品集。
- **逐状态实测**：
  - `multiple-filters:de:390`：手机筛选抽屉触发器 `aria-expanded` `false -> true`，叠加 `brand=goodwe`（24 卡）+ `application=home` 后精确收敛为 `23` 张 GoodWe 户储家族卡片，`scrollWidth=390`。
  - `filtered-pagination-count-consistency:de:390`：`/de/produkte/?application=home` 第 1 页 24 卡 + 第 2 页 9 卡 = **33 个唯一产品族 ID（跨页交集为 0）**，越界 `?product-page=3` `301` 回 `?product-page=2`。
  - `clear-filters` (`en:390`, `de:1440`, `de:390`)：在 `?brand=goodwe&application=home&q=GW`（22 卡）点击 `Clear all` / `Alle zurücksetzen`，跳转 `/products/?q=GW` 与 `/de/produkte/?q=GW`（清除全部筛选项且完整保留搜索词 `q=GW`，恢复 24 卡，`scrollWidth=390/1440`）。

### 5. `global-navigation`（11 行 → 9 行 `verified-production-20261113`，2 行保留 `partially-verified`）

- **升级的 9 行**：
  - `keyboard-traversal:de:390`：`/de/` 实测连续 `Tab` 依次聚焦 `Linker-Startseite` → `Produkte suchen` → `EN` → `DE` → `#tv-mobile-toggle`（均具 `2px solid` 焦点环）；`Enter` 打开 `#tv-mobile-panel[data-open="true"]`，`Escape` 关闭抽屉并将焦点精确归还 `#tv-mobile-toggle`。
  - `search-results` (`en:1440`, `de:390`)：`/?s=SAJ` 与 `/de/?s=SAJ` 均保留输入框 `SAJ`、H1=`SAJ`、渲染 10 条结果（商品缩略图装饰性 `alt=""`）、手机端分区位于分页之前、下一页链接保留 `?s=SAJ`。
  - `search-empty` (`en:1440`, `en:390`, `de:1440`, `de:390`)：全站 `/?s=xyzzy-nonexistent-20261113` 与商城 `/products/?q=xyzzy-nonexistent-20261113`（及德语对应路径）均保留原词、隐藏空分页、无误导“清除筛选”提示（清空 `en:390`/`de:390` 残留的 PR #751 旧 `findings[]`）。
  - `language-switch-query-filter-pagination` (`en:1440`, `de:390`)：全站搜索第 2 页、商城筛选第 2 页、博客检索、文档库型号+类型筛选 4 类路由双向语言链接 100% 保留查询、筛选与页码。
- **诚实保留的 2 行**：`language-switch-account-endpoint-and-fragment:en:390` 与 `de:390`（详见第三节）。

### 6. `contact`（4 行 → 4 行 `verified-production-20261113`）与 `authentication`（2 行 → 2 行 `verified-production-20261113`）

- `contact:empty` (`en/de × 1440/390`)：生产直接访问无 `?source=` 的 `/contact/` 与 `/de/kontakt/`，`sourceCardPresent=false`，`name`/`email`/`message` 全空，`consentChecked=false`，滚动时吸顶页头为不透明 `rgb(255, 255, 255)`，`scrollWidth == viewport`。
- `authentication:invalid-fields` (`en:390`, `de:390`)：生产 `390×844` 客户端校验拦截实测（0 提交）：登录空点聚焦 `#username`（0 错误横幅、无 busy 锁死），仅填账号聚焦 `#password`，Remember me 行高 `44px`、间距 `10px`；两步注册第 1 步空点与缺网站/VAT 均停留在 `data-active-step="1"`，填入裸域名 `example.com` 正常推进至第 2 步，第 2 步空点触发原生必填提示，`scrollWidth=390`；结合 `tests/e2e/specs/account.spec.ts` 服务端错密/非法邮箱用例闭环。

### 7. `inquiry`（12 行 → 12 行 `pass`）、`account`（10 行 → 6 行升级 / 4 行保留）、`files-and-feedback`（7 行 → 7 行升级）

- `inquiry` 全部 12 行（`remove:en:390`、`undo:en:390`、`zero-quantity:en:390` 及 `guest-populated`、`fields-retained-after-draft-edit`、`pending-draft-blocks-submit` 的 `en:390`/`de:1440`/`de:390`）：核对 `tests/e2e/specs/inquiry-draft-actions.spec.ts`、`public-inquiry.spec.ts`、`draft-visual-states.spec.ts` 源码与运行记录确认，`en/de × 1440/390` 全 4 组合均已跑绿（此前脚本仅把 `status=="pending"` 行置为 `pass`，漏更新原 `partially-verified` 行）。
- `account:company` (`en:390`, `de:1440`, `de:390`) 与 `account:inquiry-details-and-statuses` (`en:390`, `de:1440`, `de:390`)：由生产客户链路巡检、PR #874（修复 DE 390 `.cky-modal` 横溢）、PR #1003（报价单状态读回）与 PR #1067 `tests/e2e/specs/account-states.spec.ts`（`en/de × 1440/390` 账单地址 6 必填校验保留 + 客户自有询盘列表跳转详情页）完整覆盖。`account:saved-solutions-populated` 4 行保留 `partially-verified`（详见第三节）。
- `files-and-feedback:private-document-owner-other-guest-status-and-no-bytes` (`en:390`, `de:1440`, `de:390`)：PR #1067 `account-states.spec.ts:691-773`（`en/de × 1440/390` 本人 200 PDF、异客 403、访客 403 零 PDF 字节）+ PR #1089 `planning-report-download.spec.ts` + 2026-11-13 生产匿名探针（`?linker-document=quotation&id=8671` 与 `report&id=8207` 均返回 `403 text/html`、`hasPdfMagic=false`；无 key 冻结报告 REST 返回 `404`）闭环。
- `files-and-feedback:design-report-pdf` (`en/de × 1440/390`)：既有账户静态报告门禁 + PR #1070 住宅双语 PDF 逐页验收 + PR #1089 询盘冻结报告下载契约 + PR #1102/#1110 生产四组合真机下载 5 页 A4 设计报告读回（`docs/acceptance/2026-11-11/commercial-pdf-production-readback.json`）闭环。

### 8. `genie`（16 行 → 4 行 `verified-production-20261113` + 12 行 `pass`）

- `genie:lazy-bundle-failure-retry-close-focus` (`en/de × 1440/390` — 4 行)：生产客户端拦截 `genie.js`（同时拦截 `/genie/turn` 确保 `turnPosts=0`）逐项实测行内全部 6 项 `required_contexts`：
  1. React 挂载前真实脚本加载失败渲染 `[data-linker-genie-load-error]`；
  2. Helper（`/products/`、`/de/produkte/`：`1440` 非模态 `aria-modal=null`、`390` 模态 `aria-modal="true"` 且背景兄弟 `inert`）提供 `44px` Retry 与 `44px` Close，独立工作台 `/genie/`、`/de/genie/` 提供 `44px` Retry 且不渲染无意义 Close；
  3. Helper 按 `Escape` 隐藏面板、解除 `inert` 并将焦点精确归还触发按钮；解除 `genie.js` 拦截后点击 Retry 在 helper 与 workspace 双端均成功挂载 `.linker-genie-app__input`；
  4. `1440/390` 无横向溢出；
  5. 住宅页 `#system-search textarea` 输入 `"Test source preservation"` 触发懒加载失败及点 Close 后，源输入框文本 100% 保留且 `turnPosts=0`；
  6. 显式 `Escape` 关闭 helper 后派发迟到 `linker-genie-ready`，面板保持 `hidden=true` 不自动重弹。
  同步将 PR #717 遗留 `findings[]` 迁入 `resolved_findings`。
- `genie:document-card`、`genie:citations`、`genie:signed-facts-and-units`（各 4 行，共 12 行）：结合生产真问读回（`docs/acceptance/2026-11-03/genie/audit.md` Turns 723/725/727/729、`genie-live-turns-20261107.json`、`genie-live-turns-20261111.json` Turns 757–759 `29.999 kW`、PR #514 负温度符号、PR #704 原厂文档标题及今日 `c1e0cad87`/`621eff923` BAT-C 10 份新原厂文档索引同步）与 `tests/e2e/specs/genie-history-artifacts.spec.ts`（`workspace`/`hero`/`dock` × `en`/`de` × `1440`/`390` 12 个用例）全量闭环。

---

## 三、诚实保留 `partially-verified` 的 6 行与生产新发现警报

### A. 保留 `partially-verified` 的 6 行精确边界

| 矩阵 Key（共 6 行） | 已验证通过部分 | 尚未闭合的真实缺口（保留原因） |
| --- | --- | --- |
| `account:saved-solutions-populated:en:1440`<br>`account:saved-solutions-populated:en:390`<br>`account:saved-solutions-populated:de:1440`<br>`account:saved-solutions-populated:de:390` | 1. 历史保存方案卡片名称、缺凭据重算引导、移除/撤销（PR #672/#673）；<br>2. Genie 签名方案快照保存→账户列表读回→加入草稿（PR #1042 `tests/e2e/specs/genie-save-readback.spec.ts`，`en/de × 1440/390` 全绿）。 | 行契约 `required_contexts` 同时要求验证**工程规划项目账户行**（`[linker_account_rows type="planning-projects"]` 渲染并跳往 `/solution-configurator/?project=<id>#lp-overview`）。全仓检索确认该分支目前仅有 PHP 单元测试（`AccountTemplatesTest.php`），尚无 `1440/390` 浏览器 e2e 或生产客户账号实证，故不虚报 `pass`。 |
| `global-navigation:language-switch-account-endpoint-and-fragment:en:390`<br>`global-navigation:language-switch-account-endpoint-and-fragment:de:390` | 生产 `390×844` 实测 `/my-account/register/` ↔ `/de/mein-konto/registrieren/` 与 `/my-account/lost-password/` ↔ `/de/mein-konto/passwort-zuruecksetzen/` **服务端账户子端点映射双向 100% 正确**，无溢出。 | 客户端 URL `#fragment`（如 `#step-2`、`#reset-card`）不会随 HTTP 请求发往服务端，而全站页头/移动抽屉/页脚语言切换链接在非法律页上无客户端脚本同步追加 `location.hash`（对比法务页在 `tv-legal-js` 中专门把 `#section-*` 写进切语言 href），实测点击切语言后 hash 丢失。按实证原则保留 `partially-verified`。 |

### B. 顺带发现的生产数据未生效警报（请父代理关注）

本次探针顺带核查了今日刚合入主线的提交在生产站 `https://de-linker.com` 的实时落地情况：
1. **已在生产生效**：
   - `12150da77`：`/de/produkte/` 已输出 `<!-- LC DT ID: 6961 -->`；
   - `7d8ebe52e`（全部样式/法务正文/博客封面 `alt`/宣传册类型部分）：PDP 1440 `.pdp-related ul.products::before` `display: none`（首卡 `x=80`）、`/de/kundendienst/@1440` H1 无溢出、`/de/fuer-installateur/@390` 桌面输入框 `display: none`、`/de/loesung/heimspeicher/@390` H1 `hyphens: manual`、`/de/loesung/@390` `.sol-tab-label` 0 溢出、`/de/produkt-kategorie/zubehoer/@390` `dt` 0 溢出、`/refund-returns/` 与 `/de/rueckgabe-erstattung/` `#section-4` 显示 `"✓"` 无 `"2713"`、4 篇博客封面 `alt` 非空本地化、Pylontech `2003/6769` 显示 `Brochure`/`Broschüre`（0 处泛名 `Document`）。
2. **尚未在生产页面生效（需触发商品重绑/清缓存）**：
   - 生产匿名请求 `https://de-linker.com/product/saj-ats1-t63-a/`、`/de/produkt/saj-ats1-t63-a/`、`/product/pylontech-optim-us-l260-omni/`、`/de/produkt/pylontech-optim-us-l260-omni/` 实测 **PDP 页面上渲染的 FAQ 数量仍为 `0`**。说明 `7d8ebe52e` 虽然更新了 `EvidenceBindings.php` 的绑定规则，但生产库中上述商品的发布投影/LiteSpeed 页面缓存尚未重跑刷新出 FAQ。

---

## 四、`findings.md` 全文 OPEN / 未闭环条目核查对照表

对 `docs/acceptance/2026-10-22/full-site/findings.md`（第 1–588 行）全部曾标记开放/待修/待发布的事项逐一核对当前 `main` 与 2026-11-13 生产实况：

| `findings.md` 位置 | 原开放/待修事项标识 | 修复 PR / Commit | 2026-11-13 核查结论 |
| --- | --- | --- | --- |
| L13 | 首页展开回答排版层次与手机顶部 32–36px 控件线上门 | PR #654/#655/#657, `genie-reply-presentation.spec.ts`, PR #1050/#1082 | **已闭环（RESOLVED）**：`home` 与 `genie` 相关排版/44px 动作已上线并由 `home`/`genie` 状态矩阵验收 |
| L14 | 首页 Continue → 手机侧栏焦点留在背景、Esc 不能关闭 | PR #1050 (`9d17eb4e9`), PR #1082 (`157576b4b`), `fba99fdc2` | **已闭环（RESOLVED）**：`genie-dock.spec.ts` 验证 390 Continue 入侧栏聚焦输入框、Tab 闭环、Esc 关闭并归还 `.hero-prompt` |
| L15 | `premount_load_error` 剩余入口/迟到 ready/线上访客边界 | PR #717 + 本次 2026-11-13 生产 6 上下文探针 | **已闭环（RESOLVED）**：helper/workspace/营销源保留/迟到 `linker-genie-ready` 在 EN/DE × 1440/390 全部通过 |
| L16, L26 | 营销/住宅 `#system-search` 发送丢问题、附件/语音 disabled、source 错误/移除按钮细节 | `entries.ts`, PR #889 (`ed68d1c3f`), PR #1046 | **已闭环（RESOLVED）**：`marketing-genie-entry` 32/32 行已于 `verified-production-20261107` 全绿 |
| L44–50 | FAQ 与下载中心缩略图克隆空白、折叠缺型号、手机 34px 按钮、键盘焦点（当时写“尚未合并发布”） | PR #528 (`a33a0bce`), PR #656/#659/#660 | **已闭环（RESOLVED）**：均已发布上线，`document-library` 全族已验收通过 |
| L55 | 产品比较裸加号、英文 `accessories` 类别、切语言丢 `ids` | PR #661 (`f9350430`), PR #662/#663/#664, PR #753 (`3cd8788e`) | **已闭环（RESOLVED）**：生产比较页双语类别、勾选态、44px 控件、跨语言保留与稀疏规格对齐均已上线通过 |
| L59 | 品牌归档 Chint 切 DE 404 及 34 个共享品牌/系列入口待测 | 共享归档修复 + `#548` + 本次 2026-11-13 探针 | **已闭环（RESOLVED）**：68 个 EN/DE 路由（含 `ecoflow-ocean2-plus-hd-p1-s2`）全部 HTTP 200 且产品集一致 |
| L67–69, L111 | 普通 Genie 失败草稿/附件跨账号隔离 & `pagehide` 语音保留 | PR #654 + `ac5bfe319` (`genie-failure-ownership.spec.ts`) | **已闭环（RESOLVED）**：4 组合差分测试全绿（Batch 1 已同步清理残留 finding 文本） |
| L75 | 住宅与商用 hero 源 textarea 无关联 `aria-label` | PR #889 (`ed68d1c3f`, `entries.ts:45-59`) | **已闭环（RESOLVED）**：按 placeholder 注入准确英德无障碍名称 |
| L76 | 商用页 1440 照片页头 EN/DE 文字对比度 | PR #544 + `chrome.css` 封面规则 | **已闭环（RESOLVED）**：封面态白字实底对比度达标，滚出封面后转为纯白底深字 |
| L77, L81 | 德语文档库加载早期点击“Dokumente”竞态 | PR #528 (`a33a0bce`, L91 已记线上归档) | **已闭环（RESOLVED）** |
| L83–85, L95–99 | 空归档模板丢失、空页 0–0/sort、商城切语言丢 `q`/`brand`/`product-page`、Contact 缺来源摘要 | 共享归档批次 + PR #650/#651 + PR #751 + PR #1069 | **已闭环（RESOLVED）**：2026-11-13 生产实测空归档无 sort、切语言与 `Clear all` 均保留上下文 |
| L87, L109 | 共享 sticky 页头 95% 白底透字 & Contact DE hero 大标题断词 | `chrome.css:26` (`background:#fff`) + `a052d6875` | **已闭环（RESOLVED）**：2026-11-13 生产实测滚动后 `header#lc-header` 纯白实底 `rgb(255,255,255)`，Contact DE 标题无断词溢出 |
| L107 | Contact 编辑未提交留言切语言清空、来源重勾选 | `LanguageDraft.php` + `contact-language/navigation.ts` | **已闭环（RESOLVED）**：Batch 3 生产实测 EN↔DE 切换完整保留未提交字段与勾选态 |
| L123, L135, L147 | `blog-mobile-touch`、`contact-source-only-legend`、`marketing-copy-source-misattribution` | PR #649, PR #651, `production-marketing-correction.json` | **已闭环（RESOLVED）**：均已在 `findings.md` 后续章节（L128, L140, L153）正式核销 |
| L175 | `library-document-model-search`（型号关联文档检索） | PR #660 (`d63318d3`, L179) | **已闭环（RESOLVED）** |
| L206 | `mobile-compare-chip-covers-account` | PR #664 (`096cc3bef`, L208) + Batch 1 2026-11-13 复测 | **已闭环（RESOLVED）** |
| L212, L377–380 | `pdp-navigation-delay` / cold 页面耗时观测 | PR #665/#666/#667/#674/#715 | **非阻断观测（BOUNDED）**：单商品 SQL 由 2,787 降至 292，服务端正文组装 0.63s，已完成数据库查询层收敛 |
| L309 | `blog-search-retained-query` | PR #676 (`f7a9c8c3`, L338) | **已闭环（RESOLVED）** |
| L393 | `legal-online-ordering-stale`（旧线上下单条款） | PR #682/684（L413，18 处条款按报价约定更正上线） | **已闭环（RESOLVED）** |
| L402, L409 | `document-generic-source-labels`（泛名 `Document` 标签） | PR #693 (`46172e73`) + PR #704 + 今日 `7d8ebe52e`（Pylontech `2003/6769` `Brochure`/`Broschüre`） | **已闭环（RESOLVED）**：2026-11-13 生产实测 Pylontech `2003/6769` 已显示 `Brochure`/`Broschüre`，0 处泛名 `Document` |
| L433, L438, L465, L471, L546, L560 | 知识索引 `no_proven_passage` 关联缺证（曾剩 376→365→339→324 条） | PR #752 + epoch 77 + PR #876 + 今日 `c1e0cad87`/`621eff923`（BAT-C 10 份新原厂文档入库同步） | **已大幅收敛并由 `audit.md` 闭环主链**：`findings.md:573` 确认历史缺证已补证放行，跨行表头由 PR #876 修复，今日 BAT-C 10 份证书/手册亦已同步进 Genie 索引 |
| L443 | `about-mobile-heading-auto-hyphenation` | PR #697 (`9f47424e`, L468) | **已闭环（RESOLVED）** |
| L448, L454, L460, L463 | `standalone-draft-unsaved-quantity-continue` & `standalone-draft-last-remove-blank`（线上视觉曾待验） | PR #690, PR #692, PR #695 + `empty-draft.spec.ts` / `draft-visual-states.spec.ts` | **已闭环（RESOLVED）**：独立草稿修改阻断、末件移除空态与 Undo 均已上线并通过四视口 e2e 套件 |
| L492, L497 | PR #709/#712 询盘成功确认页按钮对比度与纯留言空表头/Notes 对齐（缺生产存活确认 URL） | PR #709, PR #712 + `a052d6875` + `public-inquiry.spec.ts` / `goal-state-ledger.md` (#8703/#8704) | **已闭环（RESOLVED）**：本地四视口实图 + 2026-11-11 生产真实询盘单 #8703/#8704 确认页读回完成 |
| L504 | GoodWe ESA `6321` 两处 `article` 用词、ETR `3595/6654` 兼容来源标识 | `commerce-terms` 清洗 + `a316a69ac` (`ProductShortcodes::pairing_status`) | **已闭环（RESOLVED）**：Batch 1 2026-11-13 生产 PDP 实测 0 处 `"This article"`，ETR 准确显示 `Partially documented` / `Teilweise dokumentiert` |
| L523 | `withdrawn-english-old-slug-redirects-to-german-draft`（21 个 EcoFlow EN 旧地址 301 到 DE 草稿） | PR #734 (`72d1bcf1`, L528–530) + Batch 1 2026-11-13 `curl -I` 复测 | **已闭环（RESOLVED）**：21/21 直接返回 HTTP 404 且无跳转头 |
| L548 | Staff Chrome Genie 新对话 Cloudflare Turnstile `Error 300030` | Jev/验证链路收敛 + 2026-11-11 生产真人家访实测 | **已闭环（RESOLVED）**：真实客户链路正常通过（`goal-state-ledger.md:420-431`） |
| L581–587 | 2026-11-07 剩余 `556 pending` 执行地图 | 2026-11-08 至 2026-11-13 连续批次 + 本批 `state-pv-rows.json` | **已执行收口**：原 556 pending 此前已降至 3 条，本批再将 114 条 `partially-verified` 中的 **108 条**实证收口，仅余 **6 条**具名细粒度缺口与 Batch 1 标记的 `de:1440` 补跑项 |
| Batch 3 延伸跟踪 | 今日 Batch 3 报告登记的 D1–D5 项在 `7d8ebe52e` 部署后的最新状态 | Commit `7d8ebe52e` + `12150da77` | **D1（Refund `2713`）、D2（Kundendienst 1440 H1 溢出）、D3（Lösung 390 `.sol-tab-label` 溢出）、D4（Installer 390 桌面输入框复活）、D5a（Heimspeicher H1 `hyphens:manual` 与 4 篇博客空封面 `alt`）均已在生产修复生效！**<br>**仍开放细项（2 项）**：① 德语营销页 `#tool-pane-2`（Heimspeicher / Gewerbespeicher / Installer）仍嵌英文演示视频 `linker-advisor-lookup-for-installers.mp4`；② 生产 `saj-ats1-t63-a` 与 `pylontech-optim-us-l260-omni` PDP 的 `faqCount` 仍为 `0`（需在生产触发 FAQ 重绑与缓存刷新）。 |

---

## 五、资源报告（遵循 `AGENTS.md` §0 本地存储纪律）

- **当前磁盘占用与可用空间**（`df -h .`）：总容量 `3.6Ti`，已用 `2.4Ti`（`68%`），可用空间 **`1.2Ti`**。
- **本次新增保留内容（共 2 个目标交付文件）**：
  - `docs/acceptance/2026-11-13/matrix-batch-updates/state-pv-rows.json`（`368 KB` / `376,512 bytes`，供父代理合并 `state-matrix.json` 用）；
  - `docs/acceptance/2026-11-13/matrix-batch-updates/state-pv-report.md`（本核查报告，约 `22 KB`）。
- **本次已回收临时内容与进程**：
  - 临时只读探针脚本 `tests/e2e/spv-audit.tmp.mjs`（约 `28 KB`）已删除；
  - 探针派生残留进程（PID `69639`、`69640`、`68672`）已全部终止并经 `ps aux` 复核确认 **0 残留进程**；
  - 未生成任何中间截图目录、备份快照、数据库副本、git worktree 或本地站点容器。
- **基线保护核验**：`git status --short docs/acceptance/2026-10-22/full-site/` 输出为空，`state-matrix.json`、`page-matrix.json`、`template-matrix.json`、`findings.md` 均保持零改动。
