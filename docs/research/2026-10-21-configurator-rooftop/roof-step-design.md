# 设计理由：`?step=roof` 要不要打开屋顶画布（#462，地图 #437）

- 日期：2026-10-21。只写设计理由。没有改插件、服务、生产站，没有新的外部抓取。
- 问的是：`?step=roof` 要不要打开屋顶画布，邮编怎么处理。
- 判据：AGENTS.md 2026-10-19，地图 [#437](https://github.com/AssassinFlash/de-linker/issues/437) 的边界。逻辑或功能改动之前，先抄既有接口（规格、原型、实现、验收）或 `docs/research/` 里的成熟模式。没有接口才写设计理由，再改。不凭空发明。
- 本文件是那份理由。它不是缺陷修复，也不是实现票。建议在 §0。协调者已采纳 (a)（[#462 评论](https://github.com/AssassinFlash/de-linker/issues/462#issuecomment-6299368915)，2026-10-21 03:30）。该裁定不授权产品改动。

---

## 0. 建议（已裁定：采纳 (a)）

**Headline: keep `?step=roof` as a stable landing. Do not open the roof canvas from the query.**

**建议 (a)。** `?step=roof` 保持稳定落点。画布继续只从现有按钮打开。零改动。协调者已采纳（同上评论）。

理由，短的：能打开 `.linker-roof` 的既有接口只有「有效邮编之后的按钮」。规格 12 已接受的检查是退役地址一跳 301 到 `?step=roof` 然后 200，两边引擎都过了。现在发出 `step=roof` 的地址都没有邮编。没有邮编就没有画布可开——画布没有空邮编态。从查询打开画布，没有在跑的接口：清单 R02 是「规格有实现无」，并写明跳转通过不能算打开（`docs/research/2026-10-21-configurator-rooftop/inventory.md` 第 172 行）；门是 `config.openRoof && defaults?.plz`（`plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx` 第 126–130 行），`plugins/linker-tools/src/configurator/App.tsx` 第 176–181 行不传 `defaults`，`plugins/linker-tools/includes/Configurator/Mount.php` 第 54–71 行不印 `data-step`；本地在浏览器里注入 `data-step="roof"`（产品代码未改，线上未做）后画布仍关、邮编仍空（`docs/research/2026-10-21-configurator-rooftop/matrix/both-engines.json` 的 `data-step-injected`）。`docs/research/2026-10-21-configurator-rooftop/dossier-gap.md` §5.14 在这里只为它写下的这两件事被引用：其余查询参数没有竞品研究；不要把 `?calc=canvas-roof` 的参数表套到现行页上（同文件第 213、321 行）。它不是「从查询打开画布没有先例」的出处。§1.6 引它关于规格 12 的原文。(b) 复用的是按钮的空邮编动作，发明的是触发器，而且画布仍然不开。(c) 要等 [#457](https://github.com/AssassinFlash/de-linker/issues/457) 落地。该票写的是接上已有的查询键，并不点名 `step`；`step` 不在 SizeHint 写出的键里。今天没有一个写出方同时发出 `step` 和 `plz`，所以 (c) 对现有地址是空操作。

这是客户可见流程的裁定级选择。协调者已决定 (a)。本文件记录该裁定，不另作决定，也不授权产品改动。

---

## 1. 现状

每一条下面都写路径。测量日期与矩阵相同：本地实例 `m445`（`http://127.0.0.1:9231`），线上只读。两边同一构建：`configurator.js?ver=e90a705b79f5bc1bc010`，208659 字节，sha256 `277692b3f931595049f493c636feca4006a6b7978448384532892ae14c839143`。产物含 `openRoof`，不含 `URLSearchParams`（`docs/research/2026-10-21-configurator-rooftop/matrix/matrix.md` 第 15 行；`matrix/both-engines.json` 的 `step-roof` 行 `assets`）。

### 1.1 已接受的契约是 301，不是打开画布

规格 12 的验收条写的是跳转，不是画布出现：

- `docs/specs/12-site-chrome.md` 第 22 行：旧工具入口直达新址，「屋顶步带 `?step=roof`，一跳到 200」。
- 同文件第 5 行的散文把落点叫做「配置器页屋顶步」，并记欠账 N14：丢弃查询串时，`/de/solution-configurator/?step=roof` 的 301 落到了配置器第一步。散文描述的是意图。验收条量的是 Location 里有 `?step=roof`。

[#462](https://github.com/AssassinFlash/de-linker/issues/462) 与矩阵把已接受的检查收成：退役 URL 一跳 301 到 `?step=roof`，然后页面 200。这一条两边都过。不跟随跳转记下的状态与 Location（`docs/research/2026-10-21-configurator-rooftop/matrix/redirects-301.json`，同形也在 `matrix/both-engines.json` 的 `redirect-301`）：

| 引擎 | 来自 | 状态 | Location |
| --- | --- | ---: | --- |
| local | `/design-canvas/` | 301 | `http://127.0.0.1:9231/solution-configurator/?step=roof` |
| local | `/de/design-canvas/` | 301 | `http://127.0.0.1:9231/de/loesungskonfigurator/?step=roof` |
| local | `/de/entwurfsflache/` | 301 | `http://127.0.0.1:9231/de/loesungskonfigurator/?step=roof` |
| prod | `/design-canvas/` | 301 | `https://de-linker.com/solution-configurator/?step=roof` |
| prod | `/de/design-canvas/` | 301 | `https://de-linker.com/de/loesungskonfigurator/?step=roof` |
| prod | `/de/entwurfsflache/` | 301 | `https://de-linker.com/de/loesungskonfigurator/?step=roof` |

引擎名跟 `redirects-301.json` 的 `engine` 字段：`local` 与 `prod`。`prod` 是线上只读，不是另一个构建。

地图自己的目标就带查询，请求的查询串不替换它。落点 `plugins/linker-tools/data/legacy-redirects.json` 第 331–333 行；携带规则 `plugins/linker-tools/includes/Redirects.php` 第 101–120 行（`carrying_query`：目标已含 `?` 则原样返回）。`Redirects.php` 第 104–106 行把「丢掉查询就落到第一步，而不是访客要的屋顶步」写成 N14 的测量说明。那是注释里的意图，不是本矩阵量到的打开。

跳转之后查询还在，`.linker-roof` 不出现。EN 与 DE，1440 与 390，两边引擎。挂载点没有 `data-step`。`matrix/both-engines.json` 的 `step-roof` 行：`dataStep` 为 `null`，`roofPresent` 为 `false`，`plz` 为 `""`，`finalPath` 仍带 `?step=roof`。线上 HTML 同形：`docs/research/2026-10-21-configurator-rooftop/live-get-2026-10-20.md` 第 12 行，`GET /solution-configurator/?step=roof` 为 200，无 `data-step`。

这不是失败的跳转。矩阵把它从缺陷里拿出来，归 #462（`matrix/matrix.md` 第 24、122–141、172 行）。清单 R02 的类是「规格有实现无」，并写明跳转的通过记录不能算打开（`docs/research/2026-10-21-configurator-rooftop/inventory.md` R02，第 172 行）。两个读法都在：验收条量的是 301；散文与 R02 说的是打开。本文件按 #462 的框：打开不是那条已接受的契约。要把散文变成契约，得另有裁定。2026-10-21 03:30 采纳的是 (a)，不是这一条。这不是修 bug。

### 1.2 画布门是 `config.openRoof && defaults?.plz`，页面两边都不满足

`plugins/linker-tools/src/configurator/config.ts` 第 8–9 行注释写：`data-step="roof"` 可选，先打开屋顶步，并指向规格 12。第 39 行实现是 `openRoof: data.step === 'roof'`。它只读挂载点的 dataset，不读地址栏。构建产物不含 `URLSearchParams`（§1 开头的哈希行）。

`plugins/linker-tools/includes/Configurator/Mount.php` 第 54–71 行的短代码印出 `data-linker-app`、`data-engine-url`、`data-rest-url`、`data-rest-nonce`。不印 `data-step`。第 55 行 `unset( $atts )`，短代码属性也不读查询串。

`plugins/linker-tools/src/configurator/App.tsx` 第 176–181 行把 `ResidentialPanel` 渲成 `config`、`engine`、`store`。不传 `defaults`。`ResidentialPanel` 的 `defaults` 是可选的，注释写明给 stories 和测试（`plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx` 第 50–56 行）。

画布是否出现，看 `roofPlz` 是否非空（同文件第 234–253 行：`roofPlz ? <RoofStep plz={roofPlz} …>`）。`roofPlz` 的初值是 `null`（第 85 行）。把它设上的页面路径有两条：

1. 按钮：`onOpenRoof={ setRoofPlz }`（第 230 行），而按钮只在 `trigger('plz')` 成功后调用（见 §1.3）。
2. 效果：第 126–130 行。

```126:130:plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx
		useEffect( () => {
			if ( config.openRoof && defaults?.plz ) {
				setRoofPlz( defaults.plz );
			}
		}, [ config.openRoof, defaults?.plz ] );
```

两条在页面上都是死的。`openRoof` 要挂载点有 `data-step="roof"`，Mount 不印。`defaults?.plz` 要 App 传入，App 不传。

本地曾在浏览器里、脚本跑之前，把 `data-step="roof"` 注进挂载点。产品代码没改，线上没做。结果画布仍关，邮编仍空（`matrix/both-engines.json` 的 `data-step-injected`：`dataStep` 为 `"roof"`，`roofPresent` 为 `false`，`plz` 为 `""`，`note` 写明 browser-only）。这与第 126–130 行一致：只有 `openRoof`、没有 `defaults.plz`，效果不调用 `setRoofPlz`。

### 1.3 空邮编时，按钮聚焦字段，不开画布

既有打开路径是按钮，不是查询。清单 R01 把这一条标成已验：有效邮编之后，从住宅表单打开屋顶步（`inventory.md` 第 171 行）。

```147:152:plugins/linker-tools/src/configurator/residential/ResidentialForm.tsx
		async function openRoof() {
			if ( await trigger( 'plz' ) ) {
				onOpenRoof( getValues( 'plz' ).trim() );
			} else {
				setFocus( 'plz' );
			}
		}
```

两个按钮都走这个函数：已有屋顶时的「Change roof」（第 236 行），没有屋顶时的「No PV figure yet? Estimate from the roof」（第 255 行）。没有别的调用点。页面加载不调用它。

空值从 `EMPTY.plz = ''` 来（第 49–50 行）。`toInput` 始终带上 `plz: values.plz.trim()`（第 74 行），所以空字段是空字符串，不是缺属性。schema 要求 `plz`，模式是 `^\d{5}$`（`plugins/linker-tools/src/configurator/schema/residential-input.schema.json` 第 70–74 行与第 230–234 行）。空字符串过不了模式。`schemaResolver` 把 `pattern` 写成「Enter a German postcode with five digits.」（`plugins/linker-tools/src/configurator/validation.ts` 第 38–42 行）。德语已有译文「Geben Sie eine deutsche Postleitzahl mit fünf Ziffern ein.」（`plugins/linker-tools/languages/linker-tools-de_DE_formal.po` 第 1554–1556 行）。`required` 的句子是另一句（`validation.ts` 第 36–37 行，「Please fill in this field.」/ `po` 第 1550–1552 行）；空字符串已经带了 `plz` 键，走的是 pattern，不是 required。

`trigger('plz')` 会跑这个 resolver。失败则 `setFocus('plz')`，不调用 `onOpenRoof`，所以 `roofPlz` 保持 `null`，`.linker-roof` 不挂上。本票没有在浏览器里再点一次空邮编按钮，不去声称某张截图上已经画出那句错误。代码路径是：空则聚焦，并且 resolver 会为 `plz` 准备那句五位数字的句子。`trigger` 是否把这句画到字段上，是 react-hook-form 对 resolver 错误的保留，本票没有重测。实现 (b) 如果调用的就是这个函数，继承的是整条路径，不是单独一次 `setFocus`。只调用 `setFocus`、跳过 `trigger`，是一条新路径，不是按钮的空邮编路径。

邮编框是 `inputMode="numeric"`、`autoComplete="postal-code"`、`maxLength={5}`、`id="linker-plz"`（第 171–176 行）。标签 EN「Postcode of the site」，DE「Postleitzahl des Standorts」（`plugins/linker-tools/languages/linker-tools-de_DE_formal.po` 第 896–897 行；同一对也在 `plugins/linker-tools/languages/linker-tools-de_DE_formal-ff47dbd6ce1b77b210b406f2367c7ea7.json`）。

有邮编时这条路径开得了画布。本地、邮编 80538、点「No PV figure yet? Estimate from the roof」：`matrix/both-engines.json` 的 `roof-button` 行 `roofPresent` 与 `roofVisible` 为 `true`，`plz` 为 `"80538"`，`roofText` 含 `© Bayerische Vermessungsverwaltung – www.geodaten.bayern.de, CC BY 4.0`。截图在同意 cookie 之后重拍（`matrix/matrix.md` 第 143 行，`shots/both-local-roof-button-1440.png`，时间 2026-10-20T18:20:57Z）。线上没有点。线上是同一构建，德语按钮文案是「Noch keine PV-Leistung? Aus dem Dach abschätzen」（同文件 `step-roof` 德语行的 `roofButton`）。

### 1.4 今天带 `step=roof` 的地址，没有邮编

| 写出方 | 地址 | 有没有 `plz` | 出处 |
| --- | --- | --- | --- |
| 退役工具地图 | `/design-canvas/` → `/solution-configurator/?step=roof`；德语两条 → `/de/loesungskonfigurator/?step=roof` | 无 | `legacy-redirects.json` 第 331–333 行；§1.1 的六行 301 |
| 安装商页 CTA | EN `href="/solution-configurator/?step=roof"`，文案 “Open the Roof detail step →”。DE `href="/de/loesungskonfigurator/?step=roof"`，文案 “Dachdetail-Schritt öffnen →” | 无 | `inventory.md` C05；`docs/acceptance/2026-10-10/12/copy-review.md` 第 108–109 行；`docs/research/2026-10-21-configurator-rooftop/live-get-2026-10-20.md` 第 17–18 行 |
| 语言切换 | 保留访客实际带上的 `step`，不另造键 | 不添加 `plz` | `plugins/linker-commerce/includes/Presentation/LanguageLinks.php` 第 28 行 `LANGUAGE_QUERY_KEYS` 含 `step`，第 134–141 行只保留请求里已有的这些键 |

页脚与商城的配置器入口不带 `step=roof`，指向配置器根地址（`live-get-2026-10-20.md` 第 15–16、20–23 行）。那些入口不在本题里。

语言键不是另一套参数名。德语 301 的 Location 仍是 `?step=roof`，不是德语键名（§1.1 表）。`linker/size-hint` 接受 `lang` 并丢掉，URL 里不出现 `lang`（`plugins/linker-commerce/includes/Abilities/SizeHint.php` 第 109–118 行）。页面语言跟路径，不跟查询。

### 1.5 SizeHint 的键集，#457 没有落地

`SizeHint::execute` 写进 URL 的键只有这些（`SizeHint.php` 第 121–140 行）：

| 输入 | 查询键 | 写入条件 |
| --- | --- | --- |
| `pv_kwp` | `pv_kwp` | 数字且 `> 0` |
| `annual_load_kwh` | `annual_kwh` | 数字且 `> 0` |
| `phase` | `phase` | `1` 或 `3` |
| `backup` | `backup` | `none` / `needed` / `needed_accessory_ok` |
| `plz` | `plz` | 五位数字 |
| `lang` | （不写） | 接受后 `unset` |

没有 `step`。夹具同此：`services/genie/tests/fixtures/size-hint-urls.json` 里带 `plz=80538` 的 URL 没有 `step`；非法邮编（`8053`、`805381`、`ABCDE`）的 URL 连 `plz` 都不写。矩阵量到的 Genie 地址是 `?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`，EN 与 DE 相同，没有 `step`，没有 `lang`（[#457](https://github.com/AssassinFlash/de-linker/issues/457) 正文；`matrix/matrix.md` 第 36 行）。

#457 仍开着，类是集成接口断点，不是本票。它自己的修复边界是：接上已有的查询键和已有的表单默认值，不要新造一套字段（issue 正文「以后若修」；`matrix/matrix.md` 第 38 行）。配置器今天不读这些键。`readConfig` 只读 `data-step`。所以「#457 的先例」还不存在。本文件不假定它会落地，也不把 `step` 算进那五个键。

### 1.6 查询之外，没有可抄的深链

`docs/research/2026-10-21-configurator-rooftop/dossier-gap.md` 第 36 行（无成熟模式清单第 14 行）：深链查询在 `?step=roof` 之外接受哪些参数、未知参数、语言，无竞品深链研究。`?step=roof` 本身见规格 12。其余参数写契约。

同文件 §5.14（第 317–321 行）：`?step=roof` 打开屋顶步，写在规格 12，挂载点读 `data-step="roof"`（`config.ts`）。那一条有规格，#444 核对实现是否一致即可。核对的结果在清单 R02：规格有，实现无。旧的 `?calc=canvas-roof` 加项目引用与版本，是「打开已保存的屋顶计算」（同文件第 213 行）。不要把它的参数表套到现行页上。

所以：从查询打开画布，没有在跑的接口（§1.2 的死门，清单 R02）。上面 §5.14 的引文不把这件事写成「无先例」：它写的是 `?step=roof` 打开屋顶步已在规格 12，#444 只需核对实现；没有竞品研究的是其余参数，并且不要抄 `?calc=canvas-roof`。按钮路径是既有接口。301 是既有契约。两者都已经在跑。把查询接到 `openRoof` 上，是新接口。#437 的规则要求先写理由。这就是这份文件。

---

## 2. 设计问题

`?step=roof` 要不要打开屋顶画布？邮编空着、或查询里有 `plz` 时，各做什么？

约束，从 §1 来，不是新发明：

- 画布的 props 要 `plz`（`ResidentialPanel.tsx` 第 243 行 `plz={ roofPlz }`）。`roofPlz` 只有非空字符串才会挂上 `RoofStep`。
- 按钮在 `trigger('plz')` 失败时拒绝调用 `onOpenRoof`。
- 效果只在 `openRoof` 与 `defaults.plz` 同时为真时 `setRoofPlz`。
- 退役地址、安装商 CTA、语言切换保留下来的 `step=roof`，都没有 `plz`。
- size-hint 可以有 `plz`，从没有 `step`。#457 未落地，配置器也不读 `plz`。

因此「让 `?step=roof` 打开画布」在现有地址上做不到，除非新造一个没有邮编的画布态。那个态不存在。`RoofStep` 没有空 `plz` 的调用。

下面三选一。每条写：复刻哪条接口，发明什么，英德影响，风险。

---

## 3. 选项

### (a) 保持现状

深链是稳定落点。画布仍由现有按钮打开。零改动。

- **复刻：** 规格 12 第 22 行的 301 契约（§1.1，两边已过）。画布打开复刻 R01：访客在邮编有效之后点按钮（`ResidentialForm.tsx` 第 147–152 行 → `setRoofPlz`）。空邮编时按钮自己聚焦，查询不参与。
- **发明：** 无。
- **英德：** 无变化。EN/DE、1440/390、本地与线上，今天都是画布关闭、邮编为空、按钮在（`both-engines.json` 的 `step-roof` 行）。不新增字符串。安装商 CTA 仍说 “Open the Roof detail step →” / “Dachdetail-Schritt öffnen →”，页面仍不开画布。这个落差已经量到（清单 C05 与 R02），(a) 不扩大也不消除它。
- **风险：** 规格第 5 行、`config.ts` 第 8–9 行、`Redirects.php` 第 104–106 行、安装商 CTA，继续描述一个页面没有做的打开。后来的实现者可能把散文当成未修的 bug，不经本理由就接线。这是文档与文案的落差，不是回归：两边引擎今天就是这样。客户从 `/design-canvas/` 或安装商链接进来，看到的是配置器输入，不是地图。URL 里有 `step=roof`，屏幕上没有屋顶步。

### (b) `step` 调用按钮的 `openRoof`；邮编空则走现有空路径

到达 `?step=roof` 时调用 §1.3 的那个函数。邮编空：`trigger('plz')` 失败，`setFocus('plz')`，画布不开。邮编能过 schema：`onOpenRoof`，画布开。今天的 `?step=roof` 地址没有预填邮编，所以实际总是空路径。

- **复刻：** 按钮的空邮编动作（聚焦，且不调用 `onOpenRoof`）。不复刻「打开画布」，因为按钮在空邮编时拒绝打开，而这些 URL 就是空邮编。
- **发明：** 触发器。今天 `openRoof` 只是两个按钮的 `onClick`（第 236、255 行）。没有任何加载时调用。查询在挂载时调用它，不是既有接口。若实现只 `setFocus`、不 `trigger`，则连动作也不是按钮的，是第三条路径。
- **英德：** 不需要新文案，如果复用已有错误句。五位数字句英德都已在 `validation.ts` 与 `de_DE_formal.po` 第 1554–1556 行。聚焦本身不分语言。安装商 CTA 的承诺仍然落空：画布不开。要让 CTA 与屏幕一致，得改 CTA，那是另一次文案对抗评审，不是本选项的附赠。
- **风险：**
  - 调用现有函数会先 `trigger('plz')`。空字符串失败于 `^\d{5}$`。`validation.ts` 为这次 pattern 失败准备五位数字句（§1.3）。这句会不会画到字段上，本票没有测。不得把「未点击就出现字段错误」写成已测量的状态。矩阵的 1440/390 截图是画布关闭；那些截图也没有测过到达即 `trigger`。
  - 邮编框有 `inputMode="numeric"`（`ResidentialForm.tsx` 第 173 行）。本票没有在 390 上测量键盘是否唤起。只引用这个属性，不声称键盘打开。
  - 语言切换保留 `step`（`LanguageLinks.php` 第 28、134–141 行）。在 `?step=roof` 上切语言会再走一次。这是现有保留键的副作用，不是新的德语参数名。
  - 页面默认住宅段（`App.tsx` 第 41–43 行，`initialSegment ?? 'residential'`）。查询不选工商业或电站。聚焦会落在住宅邮编上。对退役地址和安装商链接，这与屋顶意图同向；它仍然不开地图。
  - 不产生 `.linker-roof`。想要地图的人得不到地图。成本是新的到达态，收益不是画布。

### (c) 仅当查询里有 `plz` 时，`step` 才打开画布

把 `openRoof` 从 `?step=roof` 接上，并且只在已有 `plz` 查询键时 `setRoofPlz`。这是把 #457 的键集延伸一格：配置器除了读 size-hint 的五个键，还读 `step`，并用已有效果 `config.openRoof && defaults?.plz` 打开。**只在 #457 的先例落地之后才谈得上复刻。** 今天不落地。

- **复刻：** 若 #457 先把 `plz` 写进 `defaults`，则第 126–130 行的条件本身是代码里已有的门。让这扇死门在「挂载点 `openRoof` 且 `defaults.plz`」时生效，是把已写的条件接到页面上，不是新造「无邮编也开画布」。
- **发明：**
  - 从地址栏读 `step`。`readConfig` 不读。Mount 不印 `data-step`。构建不含 `URLSearchParams`。#457 的键集没有 `step`（§1.5）。#457 写明不要新造字段。把 `step` 加进读取集，就是延伸，不是那五个键的复刻。
  - 组合 `?step=roof&plz=`。没有写出方。退役地图与安装商 href 只有 `step`。size-hint 可以有 `plz`，从没有 `step`。夹具与矩阵 URL 都没有这个组合。
  - 打开方式若是直接 `setRoofPlz`，就跳过按钮的 `trigger('plz')`。按钮从不这样开。五位数字但引擎不认识的邮编，与手填同界：按钮路径的 schema 也只查五位。不同的是没有点击就懒加载 `RoofStep`（`ResidentialPanel.tsx` 第 41–46 行：地图库只在屋顶步打开时加载）并请求地点。源码阅读，本票没有用未知邮编在浏览器里重测：`roofPlz` 一设上，`RoofStep` 就渲染 `<section className="linker-roof">`（`RoofStep.tsx` 第 428 行），其中有地图容器（第 440–448 行）。`place(plz)` 在第 95–109 行。404 是未知邮编（`plugins/linker-tools/src/configurator/api/engine.ts` 第 22、56–57 行，抛 `EngineError('not_found')`）。失败走第 105 行 `setStatus('error')`，不 `setPlace`。MapLibre 只在 `place` 有值之后构造（第 111–114 行，`!place` 则返回）。所以不是先建好 MapLibre 再失败。挂上的是屋顶步区块；未知邮编不构造 MapLibre。
- **英德：** `plz` 在两条语言路径上是同一个键（#457：`input[lang]=de` 的 GET 仍返回英语路径和 `plz=80538`，无 `lang`）。屋顶步的句子已有英德（`linker-tools-de_DE_formal.po` / json）。不新增文案，如果画布用的是表单已经接受的邮编。页面语言仍由路径决定。
- **风险：**
  - #457 未合并、无落地 PR（2026-10-21 `gh issue view 457` 为 OPEN）。该票写的是接上已有的查询键（`pv_kwp`、`annual_kwh`、`phase`、`backup`、`plz`），并不点名 `step`。先例不存在时实现 (c)，是在未落地的票之外再读一个它没有列出的键，不是实现一个它点名排除的键。
  - 对 `/design-canvas/`、安装商 CTA、以及今天每一条 size-hint URL，(c) 什么都不做。它不回答「点了 Open the Roof detail step 为什么没有地图」。
  - 若以后有人把 `step=roof` 加进已含 `plz` 的 size-hint URL，Genie 打开配置器的落地会从「预填表单」（#457 的范围）变成「打开地图」。那是另一条客户可见变化，不在 #457 的「接上已有键」里。
  - 矩阵的屋顶按钮截图是在接受同意之后重拍的，因为 cookie 条挡住了署名行（`matrix/matrix.md` 第 143 行）。这不是「地图等同意才加载」的证据——屋顶代码里没有 consent 门（`plugins/linker-tools/src/configurator/roof/` 无 consent/cookie 命中）。自动打开会把署名行放在同一条 cookie 条下面，直到访客接受。这是叠层事实，不是新的同意契约。

---

## 4. 为什么是 (a)，以及什么会推翻它

#437 的规则是复刻，不发明。本题里能复刻的只有两件事，而且都已经在线上：

1. 301 到 `?step=roof`，一跳，然后 200（规格 12 第 22 行，§1.1）。
2. 有效邮编之后，按钮打开画布；空邮编则聚焦，不开画布（R01，§1.3）。

(b) 复用了第 2 条的动作，发明了触发器，并在现有 URL 上仍然不开画布。到达即 `trigger('plz')` 会让 resolver 准备五位数字句；这句是否画到字段上，未测（§3(b)）。390 上只知道邮编框有 `inputMode="numeric"`，键盘是否唤起未测。语言切换会保留 `step` 再走一次，这是 `LanguageLinks.php` 的既有保留，不是新的德语参数名，也没有验收记录过「到达即聚焦」。CTA 的英德承诺都不因此变真。

(c) 复用的是一扇从未从页面触发的效果门，前提是另一个未落地的票。#457 说接上已有的查询键，并不点名 `step`。`step` 不在 SizeHint 写出的五个键里。把 `step` 加进读取集，是超出「接上已有键」，不是该票点名排除的键。现有地址上它是空操作。`dossier-gap.md` 第 213 行把 `?calc=canvas-roof` 写成「打开已保存的屋顶计算」，不是现行 `?step=roof` 的查询契约。§5.14 只禁止把那张参数表套到现行页上。

所以建议是 (a)。零改动。画布继续只从按钮开。

选择 (a) 意味着下面这些文字描述的是意图，不是已接受的、也不是本建议要去实现的行为：

- `docs/specs/12-site-chrome.md` 第 5 行「301 → 配置器页屋顶步」，以及 N14「落到了配置器第一步」。
- `config.ts` 第 8–9 行「opens the roof step first」。
- `Redirects.php` 第 104–106 行「instead of the roof step they asked for」。
- 安装商 CTA “Open the Roof detail step →” / “Dachdetail-Schritt öffnen →”（`copy-review.md` 第 108–109 行；`live-get-2026-10-20.md` 第 17–18 行）。
- `dossier-gap.md` §5.14 把「`?step=roof` 打开屋顶步」写成规格已有。清单 R02 已记下实现没有。#462 把这个落差收成设计项，不是 bug。

这些落差留在文档里，不构成接线的许可。

**会推翻已采纳的 (a) 的，只有协调者的后续裁定：** 规格散文和安装商 CTA 才是契约，301 复选框不是。2026-10-21 03:30 的裁定不是这一条；它采纳的是 (a)。即便日后改口，现有 URL 仍然没有邮编，画布仍然没有空邮编态。那个裁定也不能靠「打开 `.linker-roof`」来实现，因为没有在跑的接口可复刻（§1.2、R02）。届时最接近既有接口的是 (b)，而且必须调用现有 `openRoof`（含 `trigger`），不得另写一个只聚焦的函数；它仍然不会让 CTA 字面成立。要让 CTA 字面成立，只有两条，本文件都拒绝当作复刻：改 CTA 文案（另一次对抗评审，不在本票），或新造无邮编画布（`RoofStep` 要求 `plz`，按钮拒绝，没有在跑的空邮编态）。

(c) 不因推翻 (a) 而自动成立。它仍要等 #457 落地，并且仍要一份单独的理由说明为什么往键集里加 `step`。本文件不预写那份理由。

---

## 5. 采纳 (a) 之后仍然不要做的事

协调者已采纳 (a)（[#462 评论](https://github.com/AssassinFlash/de-linker/issues/462#issuecomment-6299368915)，2026-10-21 03:30）。该裁定不授权产品改动。设计记录经 PR #465 入库之后才关票；入库是合并的事，本修订不合并、不部署。

- 不要把接线写成 bugfix。#462 没有 bug 标签。规格 12 的 301 契约保持。按钮路径保持。
- 不要在 #457 落地之前读 `step` 或 `plz` 查询键。不要给 size-hint 的 URL 加上 `step`。#457 说接上已有的查询键，并不点名 `step`。
- 不要改安装商 CTA、规格 12 或 `config.ts` 的注释来「对齐」本建议。裁定没有要求改这些文字。客户可见文案改动走对抗评审（AGENTS.md 2026-10-09）。
- 不要把 `?calc=canvas-roof` 的参数抄到配置器页上（`dossier-gap.md` 第 213 行与 §5.14）。§5.14 禁止的是套用那张参数表，不是「从查询打开画布没有先例」这句。

产品代码不动。
