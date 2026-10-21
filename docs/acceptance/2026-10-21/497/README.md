# #497 屋顶步的作用与跳过它的代价 — 本地 Genie 访客走查

2026-10-21。真实本地 Genie（快照实例），访客，无账号；只在本地实例上走查并记录。不合并、不部署、不写生产、不发邮件、不发询盘、不走注册表单。

## 1. 环境

| 项 | 值 | 来源 |
|---|---|---|
| 实例 | `w497`（`just up w497` → `just pull load w497 latest` → 编译 WindPress 缓存 → `just present w497` → `just serve w497`） | `just status` |
| 地址 | `http://127.0.0.1:9264`；Genie `http://127.0.0.1:9266`（`/health` 200） | `curl` |
| 快照 | `20261021-1023`（2026-10-21T02:26:29Z 取自线上） | `~/de-linker-local/w497/snapshot.json`；`record.json` `snapshot` |
| Genie 资产 | `linker-tools/build/genie.js?ver=a31c26fb2c739e595898` | 页面 HTML |
| 页面 | EN `/genie/`、DE `/de/genie/`，均 200；`data-signed-in="0"` | `record.json` `cases[].htmlLang`、`title` |
| 拍摄 | 同一 Chromium（Playwright），1440×900 与 390×844，`reducedMotion: reduce`；每次一个全新 guest context；答案展开（Show full response）并滚入视野后截 | `walk.mjs` |
| 邮件 / 账号 / 询盘 | 无；脚本不触碰注册、账户、邮件与询盘 | `record.json` `mailSent: false`、`accountUsed: false` |

`docs/acceptance/2026-10-21/497/walk.mjs` 可重跑：`node walk.mjs`。脚本从实例自己的 Genie 回合日志（`~/de-linker-local/w497/genie/turns.sqlite`）读回同样的 8 个回合，断言路由、提供者、模型、块结构与工具调用。

## 2. 两个问题与签定回答

复刻来源：作用句逐字复用 #12 站点文案；末句逐字复用引擎 `limit.default_orientation`（#479 C57）。文案对抗评审见 [copy-review.md](copy-review.md)，**Coordinator sign-off: approved (2026-10-21)**。

| 语言 | 问题 | 解释 |
|---|---|---|
| EN | `What does the Roof detail step do?` | 步骤作用 |
| EN | `What happens if I skip the roof?` | 跳过后的代价 |
| DE | `Was macht der Schritt Dachdetails?` | 步骤作用 |
| DE | `Was passiert, wenn ich das Dach weglasse?` | 跳过后的代价 |

EN（逐字）：

> The Roof detail step adds the building's layout. It is optional and maps the roof surface and module placement. Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).

DE（逐字）：

> Der Schritt Dachdetails nimmt die Dachfläche auf. Er ist optional und zeichnet die Lage der Module ein. Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).

两个问题、两种语言得到同一句签定回答；动作是 `open_configurator`，链接 `http://127.0.0.1:9264/solution-configurator/`（size-hint 的返回值，#393/#458：德语回合也走英文配置器路径，不加 `lang`）。

## 3. 截图索引（8 张）

每格：1440 · 390。

| 问题 | EN | DE |
|---|---|---|
| 步骤作用 | [en-1440](shots/roof-role-en-1440.png) · [en-390](shots/roof-role-en-390.png) | [de-1440](shots/roof-role-de-1440.png) · [de-390](shots/roof-role-de-390.png) |
| 跳过屋顶 | [en-1440](shots/roof-skip-en-1440.png) · [en-390](shots/roof-skip-en-390.png) | [de-1440](shots/roof-skip-de-1440.png) · [de-390](shots/roof-skip-de-390.png) |

## 4. 断言

`record.json` `assertions` 全为 true；`cases[].*` 是 DOM 证据，`turnLog[]` 是服务端回合日志证据。

- 精确 35° 句：EN `Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).`、DE `Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).` 在每张截图与每个回合里逐字命中（`orientationExact` 8/8）。
- 动作在：每回合恰好一个 `action` 块，`name=open_configurator`，`args.url=http://127.0.0.1:9264/solution-configurator/`；截图里链接可见（EN “Open the configurator” / DE “Konfigurator öffnen”）（`actionUrlExact` 8/8）。
- 无卡片：DOM `.linker-card` 计数 0/8；回合块类型只有 `text` + `action`（`noCards: true`）。
- 无转人工：DOM `.linker-genie-app__handoff` 计数 0/8（`noHandoff: true`）。
- 无编造数字：回合由服务写出，`provider=service`、`model=none`、`grounded=1`、`fallback=0`、`failures=[]`；回答里的数字只有签定句里的 35°（`serviceWroteEveryTurn: true`）。
- 路由：8 个回合的 `understanding.route` 都是 `roof`；唯一工具调用 `linker/size-hint`，参数 `{}`，`ok=true`，返回 `configurator_url`（`turnLogPass: true`）。
- 无询问块：DOM `.linker-genie-app__ask` 计数 0/8（`noAsk: true`）；签定句之外没有模型问题。

## 5. 边界

- `?step=roof` 未动：#462 方案 (a) 保持不变（跳转仍是稳定落点，画布仍只从按钮打开）。本票不读地址栏，也不改配置器的挂载属性。
- 未改模型通道：本路由不调用模型；`provider=service`、`model=none` 是回合日志的读回，不是配置。
- 未改其它签定句、未改 UI 文案（动作标签是既有 `.po` 的 “Open the configurator” / “Konfigurator öffnen”）。
- `size-hint` 失败：客户看到降级句，回合 `grounded=false`、`fallback=true`、`failures` 带工具句，不画没有 URL 的动作。测试是 `tests/test_next_step.py::test_a_failed_size_hint_is_a_degraded_roof_turn_in_the_question_language` 与 `test_a_roof_answer_without_the_size_hint_fact_has_no_action`；正常路径的上表不受影响。
- 路由边界（外审四条探针，修复后）：`Wie viel kWp kann ich auf meiner Dachfläche aufnehmen?` → `sizing`；`Ich möchte 12 kWp, aber ohne Dachdurchdringung planen.` → `sizing`；`Bieten Sie Anlagen ohne Dachmontage an?` → `service`；`Gibt es den SAJ H2-10K-T3 auch ohne Dachmontage?` → `products`（型号词）。步骤名的问题仍是 `roof`；`Dachmontage` / `Dachdurchdringung` / `Dachneigung` 是屋面构件，不触发弱标记。测试是 `tests/test_route.py::test_a_roof_measurement_product_or_company_question_keeps_its_route` 与 `test_every_roof_marker_is_its_sources_normalized_form`。
