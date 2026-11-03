# 生产站客户全链路只读验收 · 2026-11-03（EN/DE × 1440/390）

- 执行代理：customer-chain-walk（opencli 会话 `chain`，真实 Chrome，真实管理员账号 857558227@qq.com，登录后身份显示 "de-linker Editorial Team"，已核实）。
- 站点：https://de-linker.com（生产）。时间：2026-11-03 17:08–17:40 Asia/Shanghai。
- 视口：1440×755（真实窗口）与 390×804（popup 窗口，真实视口，非模拟）；每页滚动置顶后 viewport 截图。
- 证据：截图 65 张拍摄于 /tmp/chain/。按 lead 指示裁剪后，本目录 `evidence/{en-1440,en-390,de-1440,de-390}/` 保留 10 张进 commit：每语言/视口各 2 张代表页（home + 产品详情，覆盖导航/hero 与价格/Add-to-draft 证据）+ D1 溢出 2 张（konto-unternehmen-overflow-a/b）；其余 55 张已移至 `/tmp/chain-evidence-backup/`（磁盘保留，不进 git；/tmp/chain/ 原件仍在）。下文引用的其余文件名均在 backup 目录。
- 红线遵守：未提交任何询盘/Proforma/联系表单（Proforma 页两语言均只填 Message 未提交，见截图）；未注册新账号；未修改生产数据（configurator 只打开既有项目查看，未点 Save/Find/New project；购物车数量未动；项目 1c62e459… 未改）。
- 每页统一检查：`document.documentElement.lang`、`scrollWidth` vs `innerWidth` 溢出、可见 mojibake（ä/ö/ü/ß/€ 乱码）、H1 存在且正确、`opencli console` 错误、关键交互。全站 4 组合 × 全部页面 console 错误数均为 0（无一条 error/warn）。

## 结论

**1 个缺陷（低危）+ 2 项观察项待 lead 裁定；其余全部通过。**

---

## 缺陷清单

### D1（低危）DE 390 `/de/mein-konto/unternehmen/` 水平溢出约 33px（隐藏 CookieYes 面板撑出）

- 现象：`document.documentElement.scrollWidth=408` vs `clientWidth=375`，页面可向右横向滚动约 33px，露出空白。
- 根因（DOM 诊断）：CookieYes 隐藏面板 `.cky-preference-center`（845px 宽，`visibility:hidden`，德语文案 "Ihre Cookie-Auswahl…"）位于 `position:fixed` 的 `.cky-modal` 内，而该 modal `overflow:visible`，面板右缘 658px 伸出视口（390px），撑大 scrollWidth。
- 复现步骤：390 视口打开 https://de-linker.com/de/mein-konto/unternehmen/ → eval `document.documentElement.scrollWidth`（408）→ `window.scrollTo({left:60})` 可滚动（scrollLeft 最大 33）。3 次重新加载均复现（408/408/408，确定性）。
- 影响范围：仅此一页此视口此语言。EN 390 `/my-account/company/` scrollWidth=375 无溢出；DE 1440 同页 1425<1440 无溢出；DE 390 其余各页（含 mein-konto/anfragen、kontodaten、gespeicherte-loesungen、dokumente）均 375 无溢出；/de/ 首页同款 cky 面板存在但不撑宽。
- 截图：`de-390/konto-unternehmen-overflow-a.png`（常态）、`de-390/konto-unternehmen-overflow-b-scrolled.png`（右滚后）。
- console：无错误。
- 视口/语言：390 / DE。

## 观察项（非缺陷，建议 lead 确认是否符合设计）

### O1 配置器"打开既有项目"落地在 solution 家族营销页
- 在 /solution-configurator/（及 /de/loesungskonfigurator/）点击既有项目卡 "Linker production acceptance · owned synthetic project（Revision 16）"，当前标签页导航至 `/solution/utility-storage/`（DE: `/de/loesung/grossspeicher/`，H1 "Wenn Speicher zur Infrastruktur werden."），页面含 "Save choices" 按钮（未点击）。若"打开项目=回到项目所属 solution 家族页"是设计行为则无问题；若应进入配置器输入屏则需修正。截图：`en-1440/configurator-project-open.png`、`de-1440/konfigurator-projekt-offen.png`。
### O2 产品页 tab 面板切换正常但 `aria-selected` 恒为 false
- EN 1440 产品页点击 "Checks" tab：面板内容正确切换显示（"Limits for the configuration…"，面板高 109px），但该 `role=tab` 按钮的 `aria-selected` 点击后仍为 "false"（11 个 tab 均如此）。功能可用，仅 tablist ARIA 模式语义不完整。截图：`en-1440/product-detail-checks-tab.png`。

## 按页型通过项（证据截图一行一条）

### 首页 `/` · `/de/`
- EN 1440：lang=en-US、无溢出(1440=1440)、H1 "Linking Value. Serving You."、无 mojibake、console 0 → `en-1440/home.png`；Products 桌面 mega menu 点击展开(1120×516)可关 → `en-1440/home-nav-dropdown.png`。
- EN 390：lang/溢出(375<390)/H1/无 mojibake/console 0，汉堡 `.tv-mobile-toggle` 真实点击展开 26 个链接、再点关闭 → `en-390/home.png`、`en-390/home-burger-open.png`。
- DE 1440：lang=de-DE、无溢出、H1 "Wert verbinden. Für Sie da."、无 mojibake（title "PV- & Speicherlösungen für Installateure und EPCs" 正确）、console 0 → `de-1440/home.png`。
- DE 390：同上全过，汉堡开(26 链接)合正常 → `de-390/home.png`、`de-390/home-burger-offen.png`（390 /de/ hero 背景图文案重叠为已裁定非缺陷，未报）。
- 语言切换：EN 首页头部 "DE" 链接点击 → `/de/` 加载、lang=de-DE、德语 H1（交互证据含于 `de-1440/home.png` 流程）。

### 产品列表 `/products/` · `/de/produkte/`
- EN 1440：lang/无溢出/H1 "Products"/无 mojibake/console 0，72 张产品卡、72 处可见 € 价格 → `en-1440/products.png`。
- EN 390：同规格全过 → `en-390/products.png`。
- DE 1440：H1 "Produkte"、de-DE、无溢出、无 mojibake → `de-1440/produkte.png`。
- DE 390：同上 → `de-390/produkte.png`。

### 产品详情 `/product/goodwe-gw60k-sts-g10/` · `/de/produkt/goodwe-gw60k-sts-g10/`
- EN 1440：H1 "GW60K-STS-G10"、价格 €635.00（登录管理员可见，3 处）、"Add to solution draft" 按钮存在、11 个 tab 可点击切换（见 O2）、console 0 → `en-1440/product-detail.png`、`en-1440/product-detail-checks-tab.png`。
- EN 390：价格 3 处可见、"Add to solution draft" 可见、无溢出 → `en-390/product-detail.png`。
- DE 1440：价格德式格式 "635,00 €"、"Zum Lösungsentwurf hinzufügen" 存在、无 mojibake → `de-1440/produkt-detail.png`。
- DE 390：价格 "635,00 €"、加草稿链接可见、无溢出 → `de-390/produkt-detail.png`。

### 配置器 `/solution-configurator/` · `/de/loesungskonfigurator/`
- EN 1440：H1 "Your projects"、项目列表正常渲染、既有项目可打开（落地行为见 O1）、未点 New project/Save → `en-1440/configurator.png`、`en-1440/configurator-project-open.png`。
- EN 390：H1、无溢出、console 0 → `en-390/configurator.png`。
- DE 1440：H1 "Ihre Projekte"、项目列表完整（18 行）、打开既有项目 → `/de/loesung/grossspeicher/`（de-DE、无溢出）→ `de-1440/konfigurator.png`、`de-1440/konfigurator-projekt-offen.png`。
- DE 390：H1、无溢出 → `de-390/konfigurator.png`（工具页三屏不受像素门，按 brief 只验基础项）。

### Lösungsentwurf `/cart/` · `/de/loesungsentwurf/`
- EN 1440：H1 "Solution draft"、4 项草稿行、3 个数量字段（未改动）、Proforma 链接存在、console 0 → `en-1440/solution-draft.png`。
- EN 390：同基础项全过 → `en-390/solution-draft.png`。
- DE 1440：H1 "Lösungsentwurf"（umlaut 正确）、de-DE、无溢出 → `de-1440/loesungsentwurf.png`。
- DE 390：同上 → `de-390/loesungsentwurf.png`。

### Proforma 请求 `/proforma-request/` · `/de/proforma-anfrage/`（只填不提交）
- EN 1440：H1 "Send an inquiry"；已登录资料折叠为单行 details "Your reply details · Chester john · 857558227@qq.com"，真实点击展开 11 个字段；表单字段（Name/Reply email/Company optional/Message optional + billing 选填组）齐全；填入 Message "Acceptance walk fill - do not submit" 后截图，**未点 "Send inquiry ↗"** → `en-1440/proforma.png`、`en-1440/proforma-filled-nosubmit.png`。
- EN 390：基础项全过 → `en-390/proforma.png`。
- DE 1440：H1 "Anfrage senden"；德语标签全部正确（Nachricht (optional)、E-Mail für die Antwort、Unternehmen (optional)、Straße und Hausnummer、Postleitzahl、USt-IdNr. 等无乱码）；账号预填姓名/邮箱/账单地址；填入 "Akzeptanzbegehung - nicht senden" 截图，**未点 "Anfrage senden ↗"** → `de-1440/proforma-anfrage.png`、`de-1440/proforma-anfrage-gefuellt.png`。
- DE 390：4 个询盘字段可见、"Anfrage senden ↗" 按钮存在、无溢出 → `de-390/proforma-anfrage.png`。

### 我的账户 `/my-account/`（6 子页）· `/de/mein-konto/`（6 子页）
- EN 1440：Overview/Inquiries/Saved solutions/Documents/Company/Account details 全部 H1 正确、en-US、无溢出、console 0 → `en-1440/my-account.png`、`acct-inquiries.png`、`acct-saved-solutions.png`、`acct-documents.png`、`acct-company.png`、`acct-edit-account.png`。
- EN 390：Overview/Inquiries/Edit account/Company 全过（375 无溢出）→ `en-390/my-account.png`、`acct-inquiries.png`、`acct-edit-account.png`、`acct-company.png`。
- DE 1440：Übersicht/Anfragen/Gespeicherte Lösungen/Dokumente/Unternehmen/Kontodetails 全部 de-DE、H1 正确（含变音符号）、无溢出 → `de-1440/mein-konto.png`、`konto-anfragen.png`、`konto-loesungen.png`、`konto-dokumente.png`、`konto-unternehmen.png`、`konto-kontodaten.png`。
- DE 390：除 Unternehmen 溢出（D1）外其余全过 → `de-390/mein-konto.png`、`konto-anfragen.png`、`konto-gespeicherte-loesungen.png`、`konto-dokumente.png`、`konto-kontodaten.png`、`konto-unternehmen.png`。
- 询盘四状态词（DE）与 AGENTS §3 完全一致：Anfrage eingegangen / Proformarechnung ausgestellt / Abgeschlossen / Storniert（konto-anfragen 页可见）。

### 联系 `/contact/` · `/de/kontakt/`（不提交）
- EN 1440：H1 "Let's work on what comes next."、表单 5 字段（message/name/email/company/consent）、sales@de-linker.com 显示 2 处、console 0 → `en-1440/contact.png`。
- EN 390：5 字段可见、无溢出 → `en-390/contact.png`。
- DE 1440：H1 "Sprechen wir über Ihr Projekt."、de-DE、无溢出 → `de-1440/kontakt.png`。
- DE 390：5 字段可见、无溢出 → `de-390/kontakt.png`。两语言均未提交。

### 隐私 `/privacy-policy/` · `/de/datenschutz/`
- EN 1440：H1 "Privacy Policy"、en-US、无溢出、console 0 → `en-1440/privacy.png`；EN 390 → `en-390/privacy.png`。
- DE 1440：H1 "Datenschutzerklärung"（ß 正确）、de-DE、无溢出 → `de-1440/datenschutz.png`；DE 390 → `de-390/datenschutz.png`。

## 测试环境备注（非站点缺陷）
- opencli 原生输入在 popup 窗口被遮挡（`visibilityState=hidden`）时会拒绝派发（"Native input requires a visible browser page"），期间个别 click 返回 clicked:true 但实际未派发事件——已用事件监听器甄别，误报的"汉堡无法打开"为工具/遮挡问题：窗口重新置前后真实点击开合全部正常（en/de 各 26 链接）。报告中的交互结论均为事件核实后的结果。
- 顶部 WP admin bar 为管理员登录态特有，客户不可见，不计入验收。
- 已知非缺陷未报：390 /de/ hero 背景图英文标语与德语副标题重叠（业主已裁定）；工具页不受像素门；懒加载图片 naturalWidth=0 假阳性（检测已排除）。

## 资源报告
- 新增：`evidence/` 截图 65 张（29MB，/tmp/chain 原件复制）+ /tmp/chain/pagecheck.sh（/tmp，系统自动回收）；本 README.md。
- 浏览器资源：验收用的 1440 窗口与 634px 误建窗口已在过程中关闭；390 popup 窗口与会话标签在报告落盘后关闭；最初会话遗留的未绑定 de-linker 标签一并关闭。共享窗口内他人会话（local dev 标签、另一代理标签）未触碰。
- 磁盘：仓库内新增约 29MB 截图证据（未 commit，留 lead 决定去留）；其余无新增。
