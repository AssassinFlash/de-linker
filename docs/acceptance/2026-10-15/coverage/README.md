# 未拍面补拍清零（台账未拍清单 B–H 段，2026-10-15）

本泳道把 `docs/debt/ADJUDICATION-2026-10-14.md` 的「未拍 / 无证据清单」B–H 段逐行补拍/补验并关闭。
逐行结论在下文；每行的结论只有三种形态：**captured+功能核验**（矩阵基准 live/functional 的行）、
**captured+结构对照**、或**拍不到 → 阻塞原因 + 替代证据**。第三种形态本包 **1 行**：D6 的屋顶轮廓
（影像瓦片取不到；该行仍在 §3 逐条写明阻塞原因与替代证据）——其余 33 行都是前两种。

## 1. 环境与代码基线（结论只在基线内成立）

| 项 | 值 | 证据 |
|---|---|---|
| 实例 | t110，`http://127.0.0.1:8975` | `just status`；本文全部 URL 以该端口拍摄 |
| 插件代码 | `~/de-linker-local/t110/wordpress/wp-content/plugins/linker-{commerce,i18n,tools}` 软链到 `de-linker-worktrees/de-linker-nits`（会话开始时该线为 `cfd8ffb` + 未提交改动；会话期间该线提交为 `8d318f3`） | `ls -l …/plugins/linker-*`；`git -C …/de-linker-nits log --oneline -1` |
| 引擎 / Genie 服务 | 均起于 `de-linker-worktrees/de-linker-fix-blog-relations/services/{engine,genie}`（端口 8976 / 8977，`/health` 200） | `ps aux \| grep services/genie`；`curl :8977/health` → `{"status":"ok"}` |
| 拍摄协议 | `.scratch/live-recheck/shoot.mjs` 的同一套：禁动画、等字体、600px 步进懒加载滚动、图片 decode（15s 预算）、全页 PNG；同机同浏览器同视口 | 采集脚本 `.scratch/coverage/lib.mjs` 的 `settle()` 逐条照搬 |
| 线上侧 | 仅公开可达状态 GET（无登录、无提交），`https://de-linker.com` | `capture-H.mjs` 的 live 分支 |
| 测试邮件纪律 | 拍摄期间 t110 `linker-commerce test-mail on --to=tester@example.test`（注册/询盘/联系各态只落一封，收件人单一；实例邮件本就落 `~/de-linker-local/t110/mail/`，不发外网）。**拍摄结束后已关**：`just wp t110 linker-commerce test-mail off` → 「Success: Test mode is off: emails go to their recipients again.」，`test-mail status` → 「Test mode is off: emails go to their recipients.」（2026-10-15 实测输出） | `just wp t110 linker-commerce test-mail status`（关后输出见左） |
| 实例写入 | 仅测试数据：`coverage-*` 客户、其询盘/方案/Proforma（经插件自身 `Issuer`/`SavedSolutions::save()`）、审批三态用的三个一次性账号；联系表单限流用 `wp cache flush` 在四格之间复位 | §4 逐条命令 |

实例里为本次补拍准备的数据（可复核）：

```
coverage-full（approved）= 五个询盘 #7147 inquiry-received / #7148 proforma-issued（PI DLK-PF-2026-0025）/
#7149 completed / #7150 cancelled / #7151 de inquiry-received；一个含设计报告 PDF 的保存方案；公司地址 + 账号名
coverage-empty（approved）= 无询盘、无方案、无文档（空态）
coverage-pending / coverage-restricted / coverage-rejected = 价格门与登录拦截三态
```

复现命令（WP-CLI，实例允许）：

```bash
just wp t110 eval-file /Users/chesterjohn/Documents/de-linker/.scratch/coverage/prep.php
just wp t110 eval-file /Users/chesterjohn/Documents/de-linker/.scratch/coverage/prep2.php
```

## 2. 截图与采集脚本位置

- 截图：`.scratch/coverage/shots/`（260+ 张，不进仓库）；H 段的成对图：`.scratch/coverage/h-pairs/`（18 张：9 面 × local/live，另加实例恢复 Inverter side 后的 `pdp-en-{1440,390}-local-after-restore.png` 两张），像素指标 `.scratch/coverage/h-pairs-metrics.json`。
- 采集脚本：`.scratch/coverage/lib.mjs`（登录/协议/探针）、`capture-B.mjs`、`capture-C1.mjs`、`capture-C2.mjs`（`FILTER=` 分组）、`capture-D.mjs`、`capture-D2.mjs`、`capture-EG.mjs`、`capture-F.mjs`、`capture-F2.mjs`、`capture-F3.mjs`、`capture-H.mjs`、`analyse-pairs.py`。
- 每次运行的 DOM 探针原样落 `.scratch/coverage/probe-*.json`（本文每个数字都能在对应文件里找到）。

---

## 3. 逐行结论

### B. 登录后账号（9 行，登记关联 C10）

登录态：`coverage-full`（有数据）/`coverage-empty`（空态），口令 → 会话由 `just login t110 --user=<login>` 的一次性链接建立。
URL 实况（实测，非推断）：询盘列表是 `/my-account/inquiries/`、详情 `/my-account/inquiry/<id>/`（德语 `/de/mein-konto/…` 同构）；
Woo 默认的 `orders`/`view-order` 端点在本站 404（`/my-account/orders/` → 404，探针 `probe-B.json`）。截图 60 张。

| # | 行 | 结论 | 证据（面 × 视口 × 语言） |
|---|---|---|---|
| B1 | Overview 仪表盘 | captured+功能核验：四态计数砖 2/1/1/1（收到/已开 PI/完成/取消）、Recent inquiries 5 行、Documents 2 行（PI + Design report）、联系人卡 | `account-overview-{1440,390}-{en,de}`；`probe-B.json` `tr=3`、bodyHead 含四态标签 |
| B2 | Inquiries 列表有行态 | captured+功能核验：表 6 行（状态/日期/金额/动作四列），行内 `Request again` 在 | `account-inquiries-rows-*`；`tr=6` |
| B3 | Inquiries 空态 | captured：`coverage-empty` 的表体空、仅表头 | `account-inquiries-empty-*`；`tr=2` |
| B4 | Inquiry detail 四态 + PI 下载 | captured+功能核验：四态各一（#7147/#7148/#7149/#7150）；**PI 下载实测** `http://127.0.0.1:8975/?linker-document=proforma&id=7148` → 200、`application/pdf`、26 603 B、头 `%PDF-1.7` | `account-inquiry-{received,proforma,completed,cancelled}-*`；下载断言见 §4 命令 1 |
| B5 | Saved solutions 空态 / 有数据态 | captured（两态）：有数据态列出 `Coverage roof 9.8 kWp`（2×Chint + 1×Chint，Saved on · 15 October 2026）；空态列出空列表 | `account-saved-with-data-*`、`account-saved-empty-*` |
| B6 | Documents 空态 / 有行态 | captured（两态）：有行态 3 行（Proforma DLK-PF-2026-0025 + Design report）；空态仅表头 + 说明 | `account-documents-rows-*`、`account-documents-empty-*` |
| B7 | Company 地址表单 | captured：表单带公司名/VAT/地址字段，预填 `Coverage Installer GmbH`（页首说明「These details are pre-filled on the Proforma request page」） | `account-company-*` |
| B8 | Account details 登录后表单 | captured：名/姓/显示名/邮箱/密码字段 | `account-details-*`；`form=1` |
| B9 | Lost password 请求 / 校验错误 | captured+功能核验：请求 → 「Password reset email has been sent.」（DE「Es wurde eine E-Mail zum Zurücksetzen des Passworts versandt.」）；错误 → 「Invalid username or email.」（DE「Benutzername oder E-Mail sind ungültig.」） | `account-lost-password-*`、`account-lost-password-error-*` |

### C. 商务功能态（7 行）

| # | 行 | 结论 | 证据 |
|---|---|---|---|
| C1 | Registration 五态 | captured+功能核验：本构建的注册是三段式表单（`ol.linker-auth-steps`：1 Company / 2 Contact and address / 3 Sign-in details，全部同屏可填），五态按此拍：①step1 空 ②公司已填 ③联系/地址已填 ④提交待审（页转「Your account is under review」/「Ihr Konto wird geprüft」，且 WP-CLI 读回 `linker_approval_status=pending`）⑤校验错误（`x@y` → 「Error: Please provide a valid email address.」/「Fehler: Bitte geben Sie eine gültige E-Mail-Adresse an.」） | `registration-step1-empty-*`、`-step2-company-*`、`-step3-account-*`、`-submitted-pending-*`、`-validation-error-*`（EN/DE × 1440/390，20 张）；`probe-C1.json` |
| C2 | Commerce approval admin 三态 | **captured+功能核验失败 → 本轮修复**：后台档案页 `wp-admin/user-edit.php` 的三个按钮（approve/restrict/reject）在本构建里点不动（POST 落到 WordPress 错误页，状态保持 pending）；根因 = 插件块的 `action=linker_approval` 之后还有核心自己的隐藏 `action=update`，PHP 重复键取末值 → 请求路由到 `admin_post_update`。**captured+功能核验（修复后实机复验，见 §5bis）**。证据链：①修复前三个按钮的 POST 体实测 `action=["linker_approval","update"]`、响应 400、状态保持 `pending`（截图 after 均为 WordPress 错误页）②同字段、只留 `action=linker_approval` 发一次 → 302 且状态 `restricted` + 原因落库（WP-CLI 读回，根因成立）③**修复后在 t110 上实点复验**（软链临时指向本分支）：`node .scratch/coverage/verify-approval-live.mjs` → `approve … status=approved` / `restrict … status=restricted reason=Coverage verification: r…` / `reject … status=rejected reason=…`，页面回 `user-edit.php`；④单测覆盖（§5-2） | `approval-admin-{approve,restrict,reject}-1440-en-{before,after}.png`（修复前）、`approval-admin-{approve,restrict,reject}-1440-en-after-fixed.png`（修复后实机）、`node .scratch/coverage/verify-approval-live.mjs` 三行输出；§4 命令 2、§5bis |
| C3 | Commerce price gate 三态 | captured+功能核验（商品页 `/product/chint-dtsu666/`，DE `/de/produkt/chint-dtsu666/`，EN/DE × 1440/390）：价格位被替换为设计化 CTA，**三态三种文案**——guest「Sign in for partner pricing」/ DE 登录入口；pending「Prices after approval」/「Preise nach Freigabe」；restricted「Not available for your account」/「Für Ihr Konto nicht verfügbar」（pending 与 restricted 文案不同，实测三态三样）；rejected 登录拦截：EN「This account is not approved for sign-in. We have emailed you the reason.」/ DE「Dieses Konto ist nicht zur Anmeldung freigegeben. …」 | `price-gate-{guest,pending,restricted}-*`（12 张）、`price-gate-rejected-login-*`（4 张）；`probe-C2-price.json` + 复核命令：`node .scratch/coverage/verify-price-gate.mjs`（输出即三态文本） |
| C4 | Proforma request approved filled / 校验错误 | captured+功能核验：已批准账户草稿 2 件时表单按公司数据预填（`#billing_company=Coverage Installer GmbH`、`#billing_first_name=Carla`、`#billing_city=Muenchen`）；未勾条款提交 → 「Please read and accept the terms and conditions to send your inquiry.」（四格同文本） | `proforma-request-filled-*`、`proforma-request-validation-error-*`；`probe-C2-funnel.json` |
| C5 | Thank-you order-received with key | captured+功能核验：本站端点被词汇表改名，收讫 URL = `<checkout>/inquiry-received/<id>/?key=…`（`wc_get_order()->get_checkout_order_received_url()` 实测输出）；EN `/proforma-request/inquiry-received/7147/?key=…`、DE `/de/proforma-anfrage/inquiry-received/7151/?key=…`，四格均 200 且渲染「Inquiry details / Details der Anfrage + 明细」 | `thankyou-order-received-*`；`probe-C2-thankyou.json` |
| C6 | Solution draft 有行态 | captured+功能核验：加购后草稿页 `/cart/`（DE `/de/warenkorb/`）显示「2 × “Chint DTSU666” have been added to your solution draft.」+ What happens next 流程 | `solution-draft-lines-*` |
| C7 | Contact 发送后 / 限流 / 校验错误 | captured+功能核验：三态齐（`?contact=sent|invalid|throttled`）：sent = 成功卡（表单被替换）；invalid = 「Please check your entries and send the form again.」/「Bitte prüfen Sie Ihre Angaben…」；throttled = 「We received several messages from this connection…」/「Von dieser Verbindung sind mehrere Nachrichten eingegangen…」（窗口 3 封，四格之间用 `wp cache flush` 复位，逐格实测） | `contact-{sent,validation-error,throttled}-*`；`probe-C2-contact.json` |

### D. 配置器（6 行，登记关联 B1；工具页免像素门）

页面实况：EN `/solution-configurator/`、DE `/de/loesungskonfigurator/`（`/linker-planner/` 301 到 EN 页）。
三段式（Residential / Commercial & industrial / Utility），左栏 01 Inputs → 02 Solution → 03 Design report。

| # | 行 | 结论 | 证据 |
|---|---|---|---|
| D1 | utility submitted | captured+功能核验：Utility 段的「Write to our team」把六项工程事实编成 `mailto:sales@de-linker.com?subject=Utility-scale storage inquiry…`（实测 href 含 site/power/energy/grid/timeline/message 序列化后的正文）。该段不发引擎请求（`UtilityForm.tsx:21-30` 只做链接），「提交」即该链接的成形 | `cfg-utility-submitted-*`；`probe-D-en.json` 的 `teamLink` |
| D2 | design report PDF 下载 EN/DE | **captured+功能核验失败 → 本轮修复**：Solution 屏的 Download PDF 走站点同源代理 `/wp-json/linker-ai/v1/engine/report/pdf`，本构建下代理把引擎的 `application/pdf` 答成了 `{"detail":"%PDF-1.4…"}`（JSON 包着整个 PDF 文本），下载得到的是 JSON。根因 = `EngineProxy::call()` 用 `(array)` 读 `wp_remote_retrieve_headers()`，真实返回的是 `Requests_Utility_CaseInsensitiveDictionary`（私属性被 mangle 成单个 `\0*\0data` 键），`content-type` 永远读不到 → 走 JSON 分支。修复见 §5-1；引擎直连 `/report/pdf` 在同一输入下回 200 `application/pdf` 44–48 KB（非缺陷侧佐证） | 修复前：下载落盘 73 237 B、头 `{"det…`；直连命令见 §4 命令 3。修后单测覆盖（§5-1） |
| D3 | residential 四态 | captured：①calculating（引擎答复被延时 5s 顶住，请求体未改，`linker-empty--busy` 可见）②no qualified candidate（单相 + 30 kWp → 「No system in our range meets every rule」+ 逐条被拒规则，EN/DE 四格）③solution + 替代（选定系统块 + 「Add all to solution draft」/「Save solution」控件在）④validation error（邮编 `12` → 「Enter a German postcode with five digits.」逐字段提示） | `cfg-residential-{calculating,no-candidate,solution,validation-error}-*`；`probe-D-en.json`、`probe-D2.json` |
| D4 | commercial 五态 | captured：①calculating（同延时法，`[aria-busy=true]`）②no candidate/空结果（超配报错输入：grid 1 kVA、peak 5 000 kW）③solution with CSV（上传 30 天 × 96 点负荷曲线 → `sized` + 系统列表）④without CSV → 区间 + 询盘链接（`indicative` + `mailto:` inquiry）⑤validation error（邮编 `12` 拒绝） | `cfg-commercial-{calculating,no-candidate,with-csv,without-csv,validation-error}-*`；`probe-D-en.json`（`inquiry.href` 实测） |
| D5 | utility validation error | captured+结构对照：Utility 段**没有**引擎调用与提交校验（源码 `UtilityForm.tsx`：六个自由文本字段 + `mailto:` 链接，无 schema、无 422 面），故「utility 校验错误」在本构建里不存在可拍态；本行的替代证据 = 同屏的字段级校验面（residential/commercial 的 validation error，D3/D4 已拍）+ 源码位置。**结论按证据收窄：该行在本构建不适用（无该状态）** | `cfg-utility-submitted-*` + `plugins/linker-tools/src/configurator/utility/UtilityForm.tsx:21-30`、`105-120` |
| D6 | roof step（map + outline） | captured（map）+ 阻塞说明：屋顶步可开（面板 + MapLibre 画布 + 比例尺 + 「Click the roof of the building in the aerial image.」+ 手工画平面入口 + 归属行「© Bayerische Vermessungsverwaltung …CC BY 4.0」）。**影像瓦片在本环境取不到**（外部 WMS `geoservices.bayern.de`，画布为底层灰底），点击屋面无法定位到建筑，官方轮廓（LoD2）叠加因此拍不到。替代证据：引擎 `/roof/outline` 在同坐标（48.140278, 11.588411）实测 200 且 `found:true`、`building_id=DEBY_LOD2_5006493`、`address=Triftstraße 5`（§4 命令 4）——即缺陷不在引擎而在本环境的影像源可达性 | `cfg-roof-step-map-*`、`cfg-roof-step-outline-*`（轮廓态留空）；引擎探针见 §4 命令 4 |

### E. PDP（1 行，登记关联 A3）

面：`/product/goodwe-gw60k-sts-g10/`（DE `/de/produkt/…`，快照同款）。EN/DE × 1440/390。

| 态 | 结论 | 证据 |
|---|---|---|
| gallery thumb selected | captured+功能核验：点第 3 枚缩略图 → `aria-pressed` 由 `[false,false,true]` 反映选中位置，主图 src 随之切换 | `pdp-gallery-thumb-selected-*` |
| viewer open | captured：点主图 → 查看器打开（`.pdp-gallery-main-wrap` 的查看层） | `pdp-viewer-open-*` |
| spec tab | captured+功能核验：Technical data 的 tab 行点击后面板切换（`.pdp-info-tabs` + `.pdp-tab-disclosure`） | `pdp-spec-tab-*` |
| family picker | captured+功能核验（落点=目录家族卡，PDP 自身无选择器）：`details.card-product-picker` 打开显示 4 个型号按钮；选另一型号后卡片跟随（选中型号文本前后实测变化，`aria-current` 转移） | `pdp-family-picker-open-*`、`pdp-family-picker-switched-*`；PDP 无 picker 的实测：`document.querySelectorAll('details.card-product-picker')=0` |
| PDP × live 成对 | **见 §3 H·A3**：本行产出 PDP 四对 local/live 图，并量出两侧结构性差异（本地少一个规格组「Inverter side」） | `.scratch/coverage/h-pairs/pdp-*` |

### F. Genie（4 行，登记关联 D1）

| # | 行 | 结论 | 证据 |
|---|---|---|---|
| F1 | 工作区/对话面（欢迎语/快捷问题/composer/消息往返） | captured+功能核验：①坞内欢迎态（披露句「Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system.」+ 快捷问题 chip + composer）②**消息往返实测**：EN 21.8s、DE 16.9s 收到带合格产品卡的答复（EN「Model H2-10K-T3 In stock…Save solution」；DE 德语同构）③整页工作区 `/genie/`（Conversations 栏、Where should we begin?、Ask Genie composer、披露句、快捷问题）EN/DE × 1440/390 四格 | `genie-welcome-*`、`genie-roundtrip-*`、`genie-workspace-*`；`probe-F.json`（`ms`）、`probe-F3.json` |
| F2 | dock history failed / pending question | **captured（三态齐）**：①历史栏 ready（EN「Conversations」列表 + 本轮会话行，`genie-history-open-1440-en.png`）②pending question：提问后引擎未定夺期间的界面（`genie-pending-question-1440-{en,de}.png`）③**failed**：把历史读 `GET …/genie/conversations` 用路由 fulfill 成 503 后打开历史栏 → 界面实测「Conversations could not be loaded. Try again」（`role=alert`，源码 `App.tsx:1179-1186`），EN/DE 各一图 | `genie-history-failed-1440-{en,de}.png`；复核：`node .scratch/coverage/verify-genie-states.mjs` → `history 503 → {"alert":"Conversations could not be loaded. Try again"}` |
| F3 | product card 七态（pending/added/unverified/retry；saving/saved/failed） | **captured（七态齐，每态带造态触发）**：①pending「Adding…」（`GET …/wc/store/v1/cart` 路由延时 8s 顶住）②added「In your solution draft.」（常规）③unverified「Sent, but the draft does not show it yet. Please check.」（add 成功、回读被改写为加购前的购物车）④retry「Not added. Try again.」（`POST …/cart/add-item` fulfill 500）⑤saving「Saving…」（`POST …/linker/v1/solutions` 延时 8s）⑥saved「Saved to your account.」（常规）⑦failed「Not saved. Try again.」（solutions fulfill 500）。语言覆盖：**EN 与 DE 各七态全拍**（DE 卡片按钮的德语标签在 `languages/linker-tools-de_DE_formal-linker-tools-genie.json`：`Zum Lösungsentwurf hinzufügen` / `Lösung speichern`，脚本按两种标签找；早先 DE pending 缺图的那轮是该轮答复里没带卡，属答复抽样，重跑即成，`LANG=de` 单跑一次 0 错） | 截图 EN：`genie-card-{pending,added,unverified,retry,saving,saved,save-failed,failed}-1440-en.png`；DE：`genie-card-{pending,added,unverified,retry,saving,saved,save-failed,failed}-1440-de.png`；复态文本：`node .scratch/coverage/verify-genie-states.mjs`（造态脚本 `capture-F4.mjs`，`LANG=de` 可单跑一支） |
| F4 | page chips 四入口（account/draft/PDP/catalog search） | captured+功能核验：四个面都渲染入口 chip 且可见（EN/DE 各四格，`chipVisible=true`） | `genie-chip-{account,draft,pdp,category}-1440-{en,de}.png`；`probe-F.json` |
| 边界 | 390 视口 | 390 下导航里的 `[data-linker-genie-open]` **不可见**（`vis=false`，实测于首页；坞入口是桌面形态），390 的 Genie 面以整页工作区承载（`genie-workspace-390-{en,de}` 已拍） | `probe-F3.json` |

### G. 页头交互（2 行，登记关联 A1）

| # | 行 | 结论 | 证据 |
|---|---|---|---|
| G1 | account menu guest / logged-in open | captured+功能核验（1440）：guest 点 `.tv-b2b-acct-btn` → `aria-expanded=true`、`#linker-header-account-menu` 面板可见；登录态同一入口 → 面板列出 Overview/Inquiries/Saved solutions/Documents/Company/Account details/Log out（DE 德语同构）。**390 实况**：页头无该下拉，账户入口是移动工具行里的 46×46 链接（`a.tv-mobile-utility.tv-b2b-mobile-port`，href=`/my-account/`）——390 侧以该入口态收口（`header-account-entry-mobile-*`） | `header-account-menu-guest-open-*`、`header-account-menu-logged-in-open-*`、`header-account-entry-mobile-*` |
| G2 | 外点 / Escape 关闭 | captured+功能核验（1440 × EN/DE）：Escape → `aria-expanded=false`、面板不可见；外点（视口中部点击）→ 同上 | `header-account-menu-escape-close-*`、`header-account-menu-outside-click-close-*`；`probe-EG.json` |

### H. 登记册无证据条目（5 行）

| 条目 | 结论 | 证据 |
|---|---|---|
| A2 · 页头/页脚 `[linker_contact_link]` 三处 placement | **已定性（current state）**：两侧都把短代码渲染成设计化链接，**未出现字面量**。实测（同一探针）：页头 2 个 + 页脚 1 个 contact 链接，形状一致（`/contact/?intent=…&kind=…&title=…&source_id=…&product_id=…&source=…`；DE `/de/kontakt/` 同构）；`shortcodes` 探针在两侧均为空数组 | `.scratch/coverage/probe-H-pairs.json` 各行的 `headerContactLinks`/`footerContactLinks`/`shortcodes` |
| A3 · 复刻像素门缺可复核终局包 | **本行产出 PDP 的成对包**（三套对拍此前不含 PDP）：`h-pairs/pdp-{en,de}-{1440,390}-{local,live}.png` + 指标。**量出的差异（结构对照）**：EN 1440 全页差 14.71%（802 506 px，页高 3977 vs 3789）、EN 390 14.13%、DE 1440 14.38%、DE 390 14.79%；差异不是整页位移（最优位移 0），集中在两带：y≈1744–1843（**本地面板少一个规格组**：本地 Technical data 两组「Grid, back-up and smart port / Switching and environment」，线上三组，中间多「Inverter side」；DE 同形 y≈1792–1848）与页尾（本地比线上高 188 px，尾部整体下移）。**定性（2026-10-15 复核，按实测定稿）**：缺组在**实例侧**，不在快照。①本机四份快照/切换转储（`~/de-linker-data/{20261010-0027,20261010-0033,20261011-1732,cutover-20261011-1157}`，另本线另扫 `cutover-20261013-1759`）里 6530 的 `_tv_legacy_acf_json` 行都**含三组**（逐行 gzip 扫描：`Grid, back-up and smart port` / `Inverter side` / `Switching and environment`，行 5 387 B）；仓库持有的线上副本同形（`plugins/linker-i18n/tests/fixtures/live/products.json` 的 6530 条目三组）。②实例是两组（`just wp t110 eval` 读 6530 `_tv_legacy_acf_json.spec_groups` = 2；`linker_specs` 为空，故确走 legacy 分支；渲染端逐组输出见 `plugins/linker-commerce/includes/Storefront/ProductView.php:371-402`）。③**落在实例上的恢复已做并复验**：从仓库的线上副本取出该组、按线上位置插回实例的 legacy JSON（只插该组，其余字节不动）——
```
$ just wp t110 eval-file .scratch/coverage/restore-inverter-side.php
instance before: 2 groups: Grid, back-up and smart port | Switching and environment
instance after:  3 groups: Grid, back-up and smart port | Inverter side | Switching and environment
inserted at index: 1; payload bytes: 5041
$ curl -s http://127.0.0.1:8975/product/goodwe-gw60k-sts-g10/ | grep -o 'id="pdp-spec-tab-[0-9]"' | sort -u
id="pdp-spec-tab-0" / -1 / -2                    # 三个 tab；Inverter side 行为「Rated power 30 kW + 双来源注」
```
复拍后同协议对照（`h-pairs/pdp-en-1440-local-after-restore.png` vs `-live.png`）：tab 带差异消失（首个差异行 1744 → 1836），同排一致到 y≈3214；余下差异=y3214 起的页尾整段位移（条带口径：位移 188 时残差 **0 px / 609 行**，即页尾内容逐像素相同、整体下移 188px，本地该段多出 FAQ「Product questions」块的高度）。**仍未决的一点**：组是在哪一步从实例掉的（转储与仓库副本都有、实例没有）——按缺陷候选挂，步骤与承担者见 §6.4。**结论**：终局包已建立且可重跑（§4 命令 5），结构差的主因已定性并已修复实例侧；掩膜与「允许差异」仍须业主裁定后才能给过门结论——本行不自行判 PASS | `h-pairs-metrics.json`；`pdp-en-1440-{local,live}.png` 的 1650–1900 / 3150–3600 裁片 |
| A4 · 列表页 390 终局判定待核（默认态 shop/archive 390） | **已判（像素零差异）**：390 默认态 `/products/`、`/de/produkte/`、`/product-category/inverters/`、`/de/produkt-kategorie/wechselrichter/` 四格 local vs live **差异像素 = 0（0.0000%）**、页高逐格相等（12252 / 12590 / 12270 / 12619） | `h-pairs-metrics.json` 的 `shop-*-390`、`archive-*-390`；`h-pairs/*.png` |
| A6 · 条带口径 vs 全页口径 | **两口径逐项呈报（本轮 9 面）**：见下表。口径定义：全页 = 整页逐像素（阈值 >2/255）；条带 = 先取最优整页垂直位移后的逐像素。9 面里 5 面两口径同为 0；PDP 四面最优位移均为 0（不是位移问题），两口径数值相同 | 下表（数字源 `h-pairs-metrics.json`） |
| C6 · 商城样式 fresh authoring（代码形态债） | **已定性（代码面）**：两份卷**已重写为新作者版**，旧出处字符串不再存在——`content/windpress/storefront.css`（4 627 行）在树，`catalogue.css` 已不在卷里（`git ls-files \| grep -c 'catalogue\.css'` = 0）；`grep 'terravolt-b2b-core\|0\.12\.413' content/windpress/` 无命中。作者记录见 `docs/audit/2026-10-13-storefront-fresh-author.md`（选择器与声明保持不变、注释按卷职责重写）。原条目「代码形态债、不直接证明用户视觉缺陷、无专属成对截图」由此收口为：**该条目不是视觉缺口**，视觉差异由分类/商城面族的行承载；本轮 A4 已给四个 390 默认态列表页 local vs live 差异像素 = 0 | `ls content/windpress/`；`wc -l content/windpress/storefront.css`；`git ls-files \| grep -c 'catalogue\.css'` → 0；`grep -rn 'terravolt-b2b-core' content/windpress/` → 空（§4 命令 6） |

A6 两口径数字（同一批成对图，同协议）：

| 面 | 全页差异 px | 全页 % | 最优位移 | 条带差异 px | 条带 % | 页高 local / live |
|---|---|---|---|---|---|---|
| home-en-1440 | 0 | 0.0000 | 0 | 0 | 0.0000 | 8264 / 8264 |
| shop-en-390 | 0 | 0.0000 | 0 | 0 | 0.0000 | 12252 / 12252 |
| shop-de-390 | 0 | 0.0000 | 0 | 0 | 0.0000 | 12590 / 12590 |
| archive-en-390 | 0 | 0.0000 | 0 | 0 | 0.0000 | 12270 / 12270 |
| archive-de-390 | 0 | 0.0000 | 0 | 0 | 0.0000 | 12619 / 12619 |
| pdp-en-1440 | 802 506 | 14.7083 | 0 | 802 506 | 14.7083 | 3977 / 3789 |
| pdp-en-390 | 248 770 | 14.1341 | 0 | 248 770 | 14.1341 | 4675 / 4513 |
| pdp-de-1440 | 801 902 | 14.3821 | 0 | 801 902 | 14.3821 | 4060 / 3872 |
| pdp-de-390 | 268 997 | 14.7917 | 0 | 268 997 | 14.7917 | 4825 / 4663 |

---

## 4. 复跑命令（每一行都能重跑）

```bash
# 1 · PI 下载（B4）：下载是会话绑定的（无 cookie 的 curl 得到 403，实测），
#     所以走浏览器上下文取字节；命令即采集脚本里那一段
node - <<'JS'
import { chromium, BASE, loginLink } from '/Users/chesterjohn/Documents/de-linker/.scratch/coverage/lib.mjs';
const b = await chromium.launch(); const c = await b.newContext();
await (await c.newPage()).goto(loginLink('coverage-full'), { waitUntil: 'domcontentloaded' });
const r = await c.request.get(BASE + '/?linker-document=proforma&id=7148');
const buf = await r.body();
console.log('status', r.status(), r.headers()['content-type'], buf.length, 'B', buf.slice(0, 8).toString());
await b.close();
JS
# → status 200 application/pdf 26603 B %PDF-1.7
# 无会话对照（同一 URL）：curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:8975/?linker-document=proforma&id=7148" → 403

# 2 · 审批三态（C2）：实机复验（软链临时指向本分支，见 §5bis 的完整命令与还原）
node .scratch/coverage/verify-approval-live.mjs
# → approve   url=/wp-admin/user-edit.php?user_id=254 status=approved  reason=(unset)
#   restrict  url=/wp-admin/user-edit.php?user_id=255 status=restricted reason=Coverage verification: r…
#   reject    url=/wp-admin/user-edit.php?user_id=256 status=rejected   reason=Coverage verification: r…
#   修复前同一操作：POST 落 admin-post.php 400、状态不变（截图 approval-admin-<action>-1440-en-after.png）
#   修复后页面截图：approval-admin-<action>-1440-en-after-fixed.png

# 3 · 设计报告 PDF（D2）：引擎直连 vs 站点代理
curl -s -o /tmp/report.pdf -w "engine %{http_code} %{content_type} %{size_download}\n" \
  -X POST http://127.0.0.1:8976/report/pdf -H 'Content-Type: application/json' \
  -d '{"input":{"locale":"en","plz":"80538","annual_kwh":5000,"pv_kwp":10,"phase":3},"logo":null}'
curl -s -o /tmp/report-proxy.bin -w "proxy  %{http_code} %{content_type} %{size_download}\n" \
  -X POST http://127.0.0.1:8975/wp-json/linker-ai/v1/engine/report/pdf -H 'Content-Type: application/json' \
  -d '{"input":{"locale":"en","plz":"80538","annual_kwh":5000,"pv_kwp":10,"phase":3},"logo":null}'
head -c 40 /tmp/report-proxy.bin     # 修复前 → {"detail":"%PDF-1.4…   修复后 → %PDF-1.4

# 4 · 屋顶步（D6）替代证据：引擎的官方轮廓
curl -s -X POST http://127.0.0.1:8976/roof/outline -H 'Content-Type: application/json' \
  -d '{"plz":"80538","locale":"en","location":{"latitude":48.140278,"longitude":11.588411}}' | head -c 200

# 5 · H 段成对图与两口径指标
node .scratch/coverage/capture-H.mjs && python3 .scratch/coverage/analyse-pairs.py

# 6 · 价格门三态文本（C3 复核）
node .scratch/coverage/verify-price-gate.mjs

# 7 · Genie 的造态与状态文本（F2/F3 复核）：七态造态与逐态文本
node .scratch/coverage/verify-genie-states.mjs          # history 503 / Adding… / Sent, but… / Not added… / Saving… / Saved… / Not saved…
LANG=de node .scratch/coverage/capture-F4.mjs           # 只跑一支语言的造态拍摄（也可以不带 LANG 跑两语）

# 8 · C6 的代码面事实
git -C /Users/chesterjohn/Documents/de-linker ls-files | grep -c 'catalogue\.css'          # → 0
wc -l /Users/chesterjohn/Documents/de-linker/plugins/linker-commerce/content/windpress/storefront.css   # → 4627
grep -rn 'terravolt-b2b-core\|0\.12\.413' /Users/chesterjohn/Documents/de-linker/plugins/linker-commerce/content/windpress/   # → 空

# 9 · PDP 的 Inverter side 组（A3 落点）：把丢失的组写回实例，再读回渲染
just wp t110 eval-file /Users/chesterjohn/Documents/de-linker/.scratch/coverage/restore-inverter-side.php
curl -s http://127.0.0.1:8975/product/goodwe-gw60k-sts-g10/ | grep -o 'id="pdp-spec-tab-[0-9]"' | sort -u   # → 0/1/2 三枚
```

## 5. 本轮修的两处（都由本泳道的补拍发现，含单测）

### 5-1 `EngineProxy` 读上游响应头的方式（`plugins/linker-tools/includes/Configurator/EngineProxy.php`）

- 症状：设计报告 PDF 经站点代理后变成 JSON（`{"detail":"%PDF…"}`），下载得到 73 KB 的 JSON。
- 根因：`call()` 用 `(array) wp_remote_retrieve_headers($response)` 遍历；真实返回是核心的
  `Requests_Utility_CaseInsensitiveDictionary`，对象转数组只暴露私属性 mangle 键 `"\0*\0data"`，
  于是 `content-type` 永远取不到 → 落进 JSON 分支。实测（`wp eval`，同一请求）：
  `headers: {"\u0000*\u0000data":""}`。
- 修法：新增 `EngineProxy::flatten_headers()`——对象且有 `getAll()` 就经它读，数组照旧；`call()` 改调它。
- 测试：`EngineProxyTest::test_the_upstream_headers_are_read_in_both_shapes`（先断言 `(array)` 里没有
  `content-type`，再断言两种形状都读出 `content-type => application/pdf`）。
- 验证：`php vendor/bin/phpunit --filter EngineProxyTest` → **OK (8 tests, 42 assertions)**。

### 5-2 审批三态在档案页的入口（`plugins/linker-commerce/includes/Registration/ApprovalAdmin.php`）

- 症状：`wp-admin/user-edit.php` 的 approve/restrict/reject 三个按钮点了没反应，请求落到 WordPress 错误页
  （HTTP 400），账号状态不变（实测三个账号全 `pending`）。
- 根因：三个按钮用 `formaction` 提交 WordPress 自己的档案表单；表单里插件块的隐藏字段
  `action=linker_approval` 之后还有核心自己的隐藏字段 `action=update`，PHP 对重复键取**末值**，
  请求被路由到 `admin_post_update`（实测 POST 体：`action=["linker_approval","update"]`，
  响应 400，状态不变；把同样的字段只留 `action=linker_approval` 发一次 → 302 且状态 `restricted` 落库）。
- 修法：`register()` 增开第二扇门 `admin_post_update → handle_profile_form()`；该方法先看请求里有没有
  插件自己的 `linker_approval_action`，没有就原样放行（WordPress 自己的 update 请求不受影响），有就走同一条 `handle()`。
- 测试：`ApprovalAdminTest::test_the_profile_forms_buttons_arrive_under_wordpresss_own_action`（带
  `action=update` 到达仍落 `restricted` + 原因）与 `…::test_the_update_door_stands_down_for_wordpresss_own_request`
  （无插件字段时不动状态、不 die）。
- 验证：`php vendor/bin/phpunit --filter ApprovalAdminTest` → **OK (9 tests, 38 assertions)**。

## 5bis. 两处修复的实例端到端复验（在查出缺陷的那个站上）

拍摄基线 t110 的插件软链原本指向并行泳道的 `de-linker-nits`；按评审意见把软链临时指向本分支并重启实例
（`cd <this worktree> && just up t110`，输出 `t110: plugins linker-commerce, linker-i18n, linker-tools -> …/de-linker-coverage`），
复验后已还原（`cd …/de-linker-nits && just up t110`，输出同形、目标回到 nits）：

```
# 设计报告 PDF，经站点代理（同一 URL：修复前 200 application/json 73 242 B、正文 {"detail":"%PDF…）
$ curl -s -o /tmp/fix-report2.bin -w 'proxy %{http_code} %{content_type} %{size_download}\n' \
    -X POST http://127.0.0.1:8975/wp-json/linker-ai/v1/engine/report/pdf \
    -H 'Content-Type: application/json' \
    -d '{"input":{"locale":"en","plz":"80538","annual_kwh":5000,"pv_kwp":10,"phase":3},"logo":null}'
proxy 200 application/pdf 48837          # 头 %PDF-1.4；file → PDF document, version 1.4, 3 pages
proxy-de 200 application/pdf 49529       # DE 输入同形

$ node .scratch/coverage/verify-approval-live.mjs     # 档案页三个按钮，实点实拍
approve   url=/wp-admin/user-edit.php?user_id=254 status=approved  reason=(unset)
restrict  url=/wp-admin/user-edit.php?user_id=255 status=restricted reason=Coverage verification: r…
reject    url=/wp-admin/user-edit.php?user_id=256 status=rejected   reason=Coverage verification: r…
# 三态修复后的页面截图：.scratch/coverage/shots/approval-admin-<action>-1440-en-after-fixed.png
```

## 5ter. 复核工具的选择器与可运行性（决策 7）

决策记录第 7 条要求把复核工具 `.scratch/live-recheck/shoot.mjs` 的选择器更新到新树 id。实测两侧（线上与 t110 本地）
只发 `data-compare-product`（curl 各 24 个），`data-compare-article` 两侧都为 0；工具原本两处仍用旧属性，compare 动作恒报
`no compare control`。改动与验证：

```
$ grep -n "data-compare" .scratch/live-recheck/shoot.mjs
138:  products: q('li.product, .products .product, [data-compare-product], [data-compare-article]'),
225:  const control = page.locator('[data-compare-product], [data-compare-article]').first();

$ node .scratch/live-recheck/shoot.mjs compare-chip --force     # 线上 GET-only
shot compare-chip-en-1440 9237 h en-US Browse Inverters, Batteries and Systems | Linker
shot compare-chip-en-390 12251 h en-US Browse Inverters, Batteries and Systems | Linker
# dom-counts.json：compare-chip-en-1440/390 → products 24；action {ok:true, found:true, visible:true, text:'Compare 1/4'}
```

同时修了工具自己的启动致命项：它以 `plugins/linker-tools/package.json` 解析 playwright，而全新 checkout 里该目录没有
`node_modules`（工具在任何一次拍摄前就崩），现在回退到 `tests/e2e/package.json`；并加 `--force` 以便探针改过后重拍。

## 5quater. phpcs 结论的树与运行时口径（评审纠正）

§5 的两条修复各自以单测 + 实例复验收口；仓库级的 phpcs 结论按树与 PHP 运行时记：

```
$ php vendor/bin/phpcs -q                # PATH php = 8.5.5，CWD = 本分支的 plugins/linker-commerce
→ 2 ERROR：tests/php/Integration/ProductSearchRestTest.php:191 与 SelectionFactsRestTest.php:177
           （Generic.PHP.DeprecatedFunctions：curl_close() 已弃用）
$ /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpcs -q      # justfile 的 php（8.3）
→ 无输出
```

即：**本分支带 main 既有的两条 curl_close 弃用报告**（决策 13 归属 nits 泳道，那条泳道已在其树里把
`curl_close($handle)` 换成 `unset($handle)`），不是「本分支 clean」；两条命令只是运行时不同（8.5 vs 8.3）。
本分支自己改动的文件在上述两条命令下都干净。

## 6. 边界与未竟（逐项写明，不留 TODO 之外的模糊表述）

1. **F2 的 failed 与 F3 的七态已全部补齐**（2026-10-15 二次/三次补拍，触发、文本与语言覆盖见 §3 的 F 段表）：
   history read 503 → 「Conversations could not be loaded. Try again」；卡片 pending/unverified/retry/saving/saved/failed
   各由指定路由造态，EN/DE 两语言都有图。此前记的「未复现 / 需特定数据」说法已撤下。
2. 见上：本包不再有属于「未复现」的 F 行。
3. **D6 屋顶轮廓**（本包唯一的第三种形态行）：影像瓦片取不到（外部 WMS `geoservices.bayern.de`，画布灰底、点屋面无法定位），
   轮廓叠加拍不到；替代证据 = 引擎 `/roof/outline` 同坐标实测 `found:true`（§4 命令 4）。
4. **A3 的 PDP 差异**：实例侧缺组已恢复并复验（§3 H·A3，`restore-inverter-side.php`），余下差异=页尾整段 188px 位移
   （内容逐像素相同）。**缺陷候选（缺组发生在哪一步）**——挂给数据/切换泳道，可复核步骤：①`for d in ~/de-linker-data/*/; do gzip -dc $d/db.sql.gz |
   grep -c '6530' ; done` 扫各转储的 6530 legacy 行是否含 `Inverter side`（本机四份都含）②在实例上 `just wp t110 eval` 读
   6530 `_tv_legacy_acf_json.spec_groups` 的组数（本线实测 2）③比对 `plugins/linker-i18n/tests/fixtures/live/products.json` 的
   6530 条目（三组）④差异点定位后再决定是否需要一个「legacy 组完整性」判定进迁移检查。承担者：数据/切换泳道（本线只做实例侧恢复）。
   「过不过像素门」仍须业主掩膜/允许差异裁定，本行不自行判 PASS。
5. **test-mail 开关**：拍摄结束后已关（`off` 与 `status` 的实测输出见 §1 该行）；实例的插件软链也已还原到
   并行泳道的 `de-linker-nits`（§5bis 末尾），本次复验窗口之外未留改动。
