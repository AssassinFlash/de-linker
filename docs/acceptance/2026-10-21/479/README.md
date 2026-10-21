# #479 配置器交互六项走查（C08 / C22 / C28 / C30 / C31 / C57）

2026-10-21。只在本地快照实例上走查并记录；不合并、不部署、不写生产、不发邮件、不发询盘、不走注册表单。
本票的产物是验收记录与缺陷票；产品代码未改。

## 1. 环境与基线

| 项 | 值 | 来源 |
|---|---|---|
| 实例 | `walk479`（`just up walk479` → `just pull load walk479 latest` → `just windpress-compile walk479` → `just present walk479` → `just serve walk479`） | `just status` |
| 地址 | `http://127.0.0.1:9258`；engine `:9259`；Genie `:9260`（两者 `/health` 200） | `curl` |
| 快照 | `20261021-1023`（2026-10-21T02:26:29Z 取自线上） | `just pull load` 输出 |
| 配置器构建 | `configurator.js?ver=bacae88a042528100047`，sha256 `7ac9d249d7afd305f1ec0d63c7f1475aecc8d9f3efb48a29072c8ec5af5eaee5`，209 422 B | `record.json` `build`（脚本从页面取脚本地址、下载后算哈希） |
| 页面 | EN `/solution-configurator/`、DE `/de/loesungskonfigurator/`，均 200（`environment.pages.{en,de}.status`） | `record.json` `environment.pages` |
| 拍摄 | 同一 Chromium（Playwright，1440×900 与 390×844），`reducedMotion: reduce`，禁动画/过渡，同一上下文内切换视口；目标状态居中后再截 | `walk.mjs` `shoot()` |
| 邮件 / 询盘 / 注册 | 走查前后：实例 mail 目录 `.eml` 0→0（本地 mu-plugin 对每次 wp_mail 落一封）、HPOS `wp_wc_orders` 66→66、solutions 0→0、customers 13→13；所有 POST 记录里没有 checkout / contact-form / register / 登录表单；脚本末尾断言全 true（含 `countersNumeric`、`mailReadable`、计数逐项不变与引擎选项还原） | `record.json` `instance`、`assertions`、`posts`、`forbiddenPosts: []` |

`walk.mjs` 用一次性登录链接（`just login walk479 --user=walk479`，无邮件）建立会话；测试用户由 WP-CLI 创建，走查后连同 claim 产生的两条方案一起删除。草稿在走查中清空（`remove-item` 200 ×2，读回 0）。没有使用业主邮箱或任何真实客户账号。

## 2. 逐行结论

| 行 | 结论 | 一句话证据 | 截图 |
|---|---|---|---|
| C08 方向键 | **验收记录缺口-verified** | 左右键逐项移动焦点并切换选中与面板，双向环绕；EN/DE 都成立 | 见 §2.1 索引 |
| C22 未知邮编 | **验收记录缺口-verified** | 真实邮编 26124（Oldenburg，不在引擎地名表）→ 引擎 422 `field=plz` → 专用文案；EN/DE | 见 §2.1 索引 |
| C22 产量服务 503 | **验收记录缺口-verified** | WP 代理后面换成本地 stub 引擎回真 503 → 服务文案；EN/DE；取证后选项已还原 | 见 §2.1 索引 |
| C28 加入未确认/重试/部分成功 | **验收记录缺口-verified** | Store API 500 → 两张卡 `retry` + 整单 partial；只写一部分 → 一张 `retry` 一张 `added` + partial；短读 → `unverified` + partial；短读在 `SETTLE_READS` 内恢复 → `added` + complete | 见 §2.1 索引 |
| C30 访客 claim cookie 保存 | **验收记录缺口-verified** | 未登录保存 202 `id:0`；`?lang=en` → 英文账户 URL，`?lang=de` → 德文账户 URL；两条都留在 WooCommerce 会话里，登录后被 claim 到同一账号，EN/DE 账户页各列两条 | 见 §2.1 索引 |
| C31 保存失败 | **验收记录缺口-verified** | `linker/v1/solutions` 500 → 失败句可见（EN/DE）；实际文案见 §3.5 | 见 §2.1 索引 |
| C57 手填 kWp 的 35° 朝南披露 | **验收记录缺口-verified** | 请求不带 `planes`；报告“假设与限制”含 `limit.default_orientation` 整句，EN/DE 逐字命中 | 见 §2.1 索引 |

本轮另开 **一个缺陷票**（不在本记录票修）：

- **#485** 加入后的状态行与保存结果连成一句（缺分隔）：`All products are in your solution draft.Saved to your account.` / `Alle Produkte sind in Ihrem Lösungsentwurf.In Ihrem Konto gespeichert.`，EN/DE 与 1440/390 都复现；证据见 C30 截图与 `record.json` `rows.C30.guest.*.action.text`。既有记录（#472、#473）也带同一串，不是本轮引入。

### 2.1 截图索引（全部 44 张）

每格：EN 1440 · EN 390 · DE 1440 · DE 390。

| 状态 | 截图 |
|---|---|
| C08 方向键（Utility 聚焦） | [en-1440](shots/c08-arrows-en-1440.png) · [en-390](shots/c08-arrows-en-390.png) · [de-1440](shots/c08-arrows-de-1440.png) · [de-390](shots/c08-arrows-de-390.png) |
| C22 未知邮编 422 | [en-1440](shots/c22-unknown-plz-en-1440.png) · [en-390](shots/c22-unknown-plz-en-390.png) · [de-1440](shots/c22-unknown-plz-de-1440.png) · [de-390](shots/c22-unknown-plz-de-390.png) |
| C22 产量服务 503 | [en-1440](shots/c22-yield-503-en-1440.png) · [en-390](shots/c22-yield-503-en-390.png) · [de-1440](shots/c22-yield-503-de-1440.png) · [de-390](shots/c22-yield-503-de-390.png) |
| C28 加入 retry（Store API 500） | [en-1440](shots/c28-add-retry-en-1440.png) · [en-390](shots/c28-add-retry-en-390.png) · [de-1440](shots/c28-add-retry-de-1440.png) · [de-390](shots/c28-add-retry-de-390.png) |
| C28 加入 mixed（只写一部分） | [en-1440](shots/c28-add-mixed-en-1440.png) · [en-390](shots/c28-add-mixed-en-390.png) · [de-1440](shots/c28-add-mixed-de-1440.png) · [de-390](shots/c28-add-mixed-de-390.png) |
| C28 加入 unverified（短读） | [en-1440](shots/c28-add-unverified-en-1440.png) · [en-390](shots/c28-add-unverified-en-390.png) · [de-1440](shots/c28-add-unverified-de-1440.png) · [de-390](shots/c28-add-unverified-de-390.png) |
| C28 加入 settled（短读恢复） | [en-1440](shots/c28-add-settled-en-1440.png) · [en-390](shots/c28-add-settled-en-390.png) · [de-1440](shots/c28-add-settled-de-1440.png) · [de-390](shots/c28-add-settled-de-390.png) |
| C30 访客保存成功 | [en-1440](shots/c30-guest-saved-en-1440.png) · [en-390](shots/c30-guest-saved-en-390.png) · [de-1440](shots/c30-guest-saved-de-1440.png) · [de-390](shots/c30-guest-saved-de-390.png) |
| C30 登录后 claim 列表 | [en-1440](shots/c30-claimed-en-1440.png) · [en-390](shots/c30-claimed-en-390.png) · [de-1440](shots/c30-claimed-de-1440.png) · [de-390](shots/c30-claimed-de-390.png) |
| C31 保存失败 | [en-1440](shots/c31-save-failed-en-1440.png) · [en-390](shots/c31-save-failed-en-390.png) · [de-1440](shots/c31-save-failed-de-1440.png) · [de-390](shots/c31-save-failed-de-390.png) |
| C57 35° 朝南披露 | [en-1440](shots/c57-report-orientation-en-1440.png) · [en-390](shots/c57-report-orientation-en-390.png) · [de-1440](shots/c57-report-orientation-de-1440.png) · [de-390](shots/c57-report-orientation-de-390.png) |

## 3. 逐行证据

### 3.1 C08 方向键在三个项目类型间移动

`App.tsx` `onTabKey` 的三种行为都实测：ArrowRight 前进、ArrowLeft 后退、两端环绕（`(index + step + 3) % 3`），并且焦点跟随选中项。

| 步骤 | EN 焦点 / 选中 / 面板 | DE 焦点 / 选中 / 面板 |
|---|---|---|
| 起始（Residential 聚焦） | `linker-tab-residential` / residential / `linker-panel-residential` | 同左（标签 Wohngebäude） |
| ArrowRight | `linker-tab-commercial` / commercial / `linker-panel-commercial` | 同左（Gewerbe und Industrie） |
| ArrowRight | `linker-tab-utility` / utility / `linker-panel-utility` | 同左（Großanlagen） |
| ArrowRight（环绕） | `linker-tab-residential` / residential / `linker-panel-residential` | 同左 |
| ArrowLeft（环绕） | `linker-tab-utility` / utility / `linker-panel-utility` | 同左 |

- 初始 `tabIndex` 为 roving：选中项 0，其余 -1（`record.json` 起始状态；与 `App.tsx` 的 `tabIndex` 分支一致）。
- 截图停在 Utility 聚焦态，焦点环可见（`c08-arrows-*-1440.png`）；390 下三张卡片纵排，同样可见。
- `record.json` → `rows.C08.{en,de}.states`（每一步的 `focus` / `checked` / `panel` / `labels`）。

### 3.2 C22 真实但未知的邮编（422）

邮编取 **26124（Oldenburg, Niedersachsen）**：

- 引擎地名表（`services/engine/data/plz_de.csv.gz`，10 813 行，GeoNames 2026-10-09 导出）**不含** 26124（`record.json` `gazetteer.containsUnknown: false`；脚本直接解压该表逐行比对）。
- 现实性：两个独立名录把 26124 列在 Oldenburg 的邮编里（kip.net 的市情页、schulpraktikumsfinder.de 的 IHK 列表），Wikipedia 的 Oldenburg 信息框给 26121–26135 区间；取证走 Apify（google-search-scraper 与 website-content-crawler），摘录存 `postcode-26124.apify.json`。
- 提交后引擎真实回答 `422 {"detail":{"error":"invalid_input","field":"plz"}}`（`record.json` `rows.C22.unknownPostcode.*.answer`），界面显示：
  - EN：`We do not know this postcode. Check it and try again.`
  - DE：`Diese Postleitzahl ist uns nicht bekannt. Prüfen Sie sie und versuchen Sie es erneut.`
  - 错误框内还有 `Try again` / `Erneut versuchen`。
- **没有伪造 422**：这一行全程用真引擎、真代理、真输入。

### 3.3 C22 产量服务不答（503）

真引擎在本机有 PVGIS 缓存（正常输入返回 200，见 §3.4 的 `designStatus`），正常请求产不出 503。方法（本文件与 `walk.mjs` 都写明，可复跑）：

1. `stub503.py` 在 `127.0.0.1:9333` 起一个只答 `POST /design/residential` 的 stub，回 `503 {"detail":{"error":"yield_unavailable",…}}`。
2. `just wp walk479 option update linker_engine_url http://127.0.0.1:9333`（记录值：`9259 → 9333`）。
3. 浏览器照常提交；请求路径仍是同源代理 `/wp-json/linker-ai/v1/engine/design/residential`，由 `EngineProxy` 服务端跳到 stub，**503 原样穿过代理**（stub 日志收到 2 次 POST，EN/DE 各一次）。
4. 取证后还原 `linker_engine_url = http://127.0.0.1:9259` 并读回（`record.json` `rows.C22.yield503.option{Before,During,After}`）。

界面文案（EN/DE 各一格）：

- EN：`The yield service did not answer. Try again in a minute.`（+ `Try again`）
- DE：`Der Ertragsdienst hat nicht geantwortet. Versuchen Sie es in einer Minute erneut.`（+ `Erneut versuchen`）
- 引擎体：`503 {"detail":{"error":"yield_unavailable","message":"stub: PVGIS did not answer"}}`。

边界：只有 **503** 在引擎端口用 stub 造；422 是真请求。浏览器侧没有改响应。

### 3.4 C28 加入未确认 / 重试 / 部分成功，以及 `SETTLE_MS` / `SETTLE_READS`

输入是已知邮编夹具（EN 80538 / DE 80331，4500 kWh，10 kWp，三相，备电无；同 §3.6 的输入），方案行是商品 3556 ×1 与 3611 ×1。四种造态都在浏览器网络层注入（`page.route`），**不写真实小车**；`Add all` 的判定逻辑、卡片状态与整单文案都是真代码在跑：

| 造态 | 注入 | 两张卡 | 整单状态行 | 加入 POST | 加后小车读 |
|---|---|---|---|---|---|
| Store API 500 | `POST cart/add-item` → 500 | `retry`：`Not added. Try again.` / `Nicht hinzugefügt. Versuchen Sie es erneut.` | partial：`Some products are not confirmed in your solution draft. See the cards above.` / `Einige Produkte sind in Ihrem Lösungsentwurf nicht bestätigt. Einzelheiten stehen in den Karten oben.` | 2 | 1（before + after；没有 sent 行，不进入 settle） |
| 只写一部分（混合） | 第一行 500、第二行 200；读回只有第二行 | 第一张 `retry`、第二张 `added` | partial（同上） | 2 | 1（before + after；发出的行已读全，不进入 settle） |
| 短读不恢复 | add-item → 200；`GET cart` 第 2–5 读不显示已发出的行（quantity 1，少 1 即 0） | `unverified`：`Sent, but the draft does not show it yet. Please check.` / `Gesendet, aber im Entwurf noch nicht sichtbar. Bitte prüfen Sie den Entwurf.` | partial（同上） | 2 | 4（after + 3 次 settle） |
| 短读在 `SETTLE_READS` 内恢复 | add-item → 200；第 2–4 读短，第 5 读回全量 | `added`：`In your solution draft` / `In Ihrem Lösungsentwurf` | complete：`All products are in your solution draft.` / `Alle Produkte sind in Ihrem Lösungsentwurf.` | 2 | 4（after + 3 次 settle） |

- 常量取自源码（`api/store.ts`）：`SETTLE_MS = 250`、`SETTLE_READS = 3`（`record.json` `settle`）。
- 实测读间隔（EN unverified）`255 / 254 / 254 ms`；（EN settled）`254 / 255 / 254 ms`；（DE unverified）`253 / 255 / 255 ms`；（DE settled）`253 / 256 / 255 ms`——都在 `253–256 ms`，即只在读短时等，每次等约 250 ms，最多再读 3 次；第 3 次仍短 → `unverified`；第 3 次读全 → `added`。
- 500 与 mixed 两格的加后读只有 1 次（没有进入 settle），证明 settle 只服务于“已发出的行读短”，不服务于整单失败或未发出。
- 证据：`record.json` `rows.C28.{en,de}.cases.{retry,mixed,unverified,settled}`（卡片状态、整单文案、读数、间隔）。

### 3.5 C31 保存失败

`POST /wp-json/linker/v1/solutions?lang=…` 用 `page.route` 回 500（真前端、真保存流程，报告 PDF 仍由真引擎生成）。界面显示：

- EN：`The solution could not be saved. Try again.`
- DE：`Die Lösung konnte nicht gespeichert werden. Versuchen Sie es erneut.`

**与清单措辞的差异（记录，不判缺陷）**：`inventory.md` C31 行把期望文案写成 `Not saved. Try again.`。这句是 Genie 卡片的 save-failed 文案（同清单 F3 行，`cardActions.ts:151`）；配置器的实际文案是上面两句（`Solution.tsx:371-376`，普通 `__`，无 `configurator` context）。规格 14 只规定“保存失败态”，没有钉死这句；实际文案清楚、EN/DE 同步，故按“实现与规格相符、清单引文来自另一条卡”记录。若要把配置器文案统一成 `Not saved. Try again.`，那是新的文案裁定，需走文案评审，不在本轮。

### 3.6 C30 访客用 claim cookie 保存（含 #477 的 `?lang=`）

未登录上下文里在同一会话完成两次保存（EN 用 80538，DE 用 80331）：

| | EN | DE |
|---|---|---|
| 保存请求 | `POST /wp-json/linker/v1/solutions?lang=en` | `POST /wp-json/linker/v1/solutions?lang=de` |
| 回答 | `202 {"id":0,"url":"http://127.0.0.1:9258/my-account/saved-solutions/"}` | `202 {"id":0,"url":"http://127.0.0.1:9258/de/mein-konto/gespeicherte-loesungen/"}` |
| 界面 | `Saved to your account.` + `Open saved solution` | `In Ihrem Konto gespeichert.` + `Gespeicherte Lösung öffnen` |

- **claim cookie**：访客的“认领”就是 WooCommerce 会话 cookie（`wp_woocommerce_session_*`，`keep_for_guest()` 里 `set_customer_session_cookie(true)`；`SavedSolutions.php` 文件头注释）。浏览器侧该 cookie 在 `Add all` 后已在（`cookiesAfter` 名：`wp_woocommerce_session_*`、`woocommerce_cart_hash`、`woocommerce_items_in_cart`）；服务端读回才是硬证据：
  - 登录前 `wp_woocommerce_sessions` 里含 `linker_saved_solutions` 的会话 = 1；含 `80538` = 1；含 `80331` = 1（同一行里两条方案）。
  - 用一次性链接登录后，同一上下文访问账户“Saved solutions” → **两条都在**：EN 页两行 `GoodWe GW10K-ETA-G20, 80538` 与 `…, 80331`，DE 页 `Gespeicherte Lösungen` 两行（`Gespeichert am · 21. Oktober 2026`）。
  - claim 之后再查会话：含 `linker_saved_solutions` = 0（`record.json` `rows.C30.session`）。
- 账户页截图：`c30-claimed-{en,de}-{1440,390}.png`。测试用户是“待审”账号（页面顶部 Under review 提示），按裁定待审账号可保存、可发询盘；claim 不依赖审批。
- 清理：草稿 remove-item 200 ×2，读回 0；claim 产生的方案 8014、8015 与用户 49 已删除；删后读回解决方案 0、用户不存在（`record.json` `rows.C30.cleanup`）。

**缺陷**：保存成功后同一状态行把加入句与保存句连成一句（缺空格），见 #485；本行机制本身 verified。

### 3.7 C57 手填 kWp、没有屋面的 35° 朝南披露

输入不含屋顶步（手填 10 kWp）。设计请求的键是 `locale, plz, annual_kwh, pv_kwp, phase, backup, heat_pump, electric_vehicle`——**没有 `planes`**（`rows.C57.*.requestHasPlanes: false`）。报告 §“假设与限制 / Annahmen und Grenzen”逐字命中：

- EN：`Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).`
- DE：`Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).`

来源链：`services/engine/src/linker_engine/report.py:360-361`（`if not request.planes`）→ `texts.py:517-519` 的 `limit.default_orientation`。截图把该段居中（390 下整句可读）。

## 4. 记录与方法

- `walk.mjs`：全部六行的采集脚本；同一实例、同一浏览器；每次造态记录请求状态、响应体、界面文本与截图路径。**不注入 422**；503 只换引擎端口；C28 的 500/短读是网络层造态，C30 的加购/保存是真 Store API。
- `stub503.py`：C22 503 的本地引擎 stub（自带说明；由 `walk.mjs` 起停，选项由脚本改回）。
- `postcode-26124.apify.json`：26124 现实性的 Apify 取证摘录。
- `record.json`：机器记录（环境、构建哈希、每一行的原始观测、清理结果、POST 清单）。
- 截图 44 张：`shots/`，命名 `<行>-<状态>-<语言>-<视口>.png`。

复跑：

```bash
just up walk479 && just pull load walk479 latest
just windpress-compile walk479 && just present walk479 && just serve walk479
just wp walk479 user create walk479 guest479@example.test --role=customer
node docs/acceptance/2026-10-21/479/walk.mjs "$(just login walk479 --user=walk479 | tail -1)"
```

（`just windpress-compile` 需要插件目录 `npm ci`；本次已装。Playwright 从主检出的 `tests/e2e` 解析，默认路径写死在脚本里，可用 `LINKER_E2E_PACKAGE` 覆盖。脚本末尾会删除测试用户与 claim 方案、清空草稿。）

## 5. 观察（不是本票缺陷）

- 账户页对“待审”测试用户显示 Under review 横幅——这是审批三态的既有设计，不影响保存与 claim；本次没有批准账号，以证明 claim 不依赖审批。
- 清单 C31 的引文 `Not saved. Try again.` 来自 Genie 卡片（F3），不是配置器；见 §3.5。
- 既有的 #472 / #473 记录里就有连句串（`record.json` 的 `status`），本轮把它落成 #485。

## 6. 清理与边界

- 无邮件、无询盘、无注册表单提交、无生产写入；`forbiddenPosts: []`。前后计数与断言：`record.json` `instance`（mail 文件 0→0、HPOS orders 66→66、solutions 0→0、customers 13→13）与 `assertions`（全 true，含 `countersNumeric`、`mailReadable`、计数逐项不变与 `engineOptionRestored`）。
- 走查只写本地实例的测试会话与两条测试方案，均已删除；草稿读回 0。
- `linker_engine_url` 已还原为 `http://127.0.0.1:9259` 并读回（`optionAfter.value`）。
- 本票不改产品代码、不部署；记录经 PR #487 合并。线上重走由协调者另行安排（部署后同两语言再走一次 26124 与访客保存）。
