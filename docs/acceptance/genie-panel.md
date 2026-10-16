# #13 Genie 行为面板（`docs/acceptance/genie-panel.md`）

≥30 问，EN/DE 各一遍。期望集合从 `docs/research/2026-10-09/old-repo-live-catalogue-facts.md` 推导。通过标准（docs/specs/13-genie.md §验收）：期望集合一致率 100%、追问不超过一个、披露句出现一次、范围外只有邮箱句。

记号：
- **HOME-3φ**：住宅三相混逆 28 台（6512 6514 3555 3556 4107 1182 2199 6513 3574 1183 1186 3575 3583 1184 1187 3576 3584 4108 1185 3585 2063 6515 2064 6516 6517 6518 2198 4109）。
- **ETR**：GW80K 6507、GW99.99K 6508、GW100K 6509、GW110K 6510、GW124.99K 6511、GW125K 3595（全部 commercial，不进住宅答案）。
- **ESA**：电池模块 6519 6521 3611 6520 6522 3612（无 pa_phase，unknown 保留）。
- 运行环境：本地实例 + `just serve`（engine + genie），真模型（deepseek-flash 直连 DeepSeek 官方 API，唯一对话模型，无供应商开关——业主裁定 2026-10-11）。结果存 `docs/acceptance/<date>/13/`。

## A. 按分类（每类 ≥2 问）

| # | 入口 | EN | DE | 期望 |
|---|---|---|---|---|
| A1 | 商城 | Which hybrid inverters do you carry for homes? | Welche Hybridwechselrichter haben Sie für Wohngebäude? | ⊆ HOME-3φ ∪ 单相机（6523–6528 有相值则含单相）；无 ETR；卡片 ⊆ refs |
| A2 | 商城 | And for commercial projects? | Und für Gewerbeprojekte? | ⊆ commercial 集合（含 ETR 六台）；无住宅单相机；一个追问或直接卡 |
| A3 | 商城 | What home-storage batteries are there? | Welche Heimspeicher-Batterien gibt es? | ⊆ 30 电池（ESA 六件 ⊆）；phase unknown 不剔除 |
| A4 | 商城 | All-in-one systems for a home? | All-in-one-Systeme für ein Wohngebäude? | ⊆ all-in-one 5 件 + CHS2 系；相数齐 |
| A5 | 商城 | Do you have an energy management system for the home? | Haben Sie ein Energiemanagementsystem für das Wohngebäude? | ⊆ ems-monitoring 5 件（3573 2415 3618 2409 1973）；无逆变器/电池混入 |
| A6 | 商城 | And a monitoring device for the electricity meter? | Und ein Monitoring-Gerät für den Stromzähler? | ⊆ ems-monitoring 的计量件（Chint DTSU666 2281、GoodWe GM330 2394、GMK330 2397）；无价格（未登录） |
| A7 | 商城 | Which wallboxes do you have for a home? | Welche Wallboxen haben Sie für ein Wohngebäude? | ⊆ ev-chargers 3 件（3586 3557 3587）；一个追问或直接卡 |
| A8 | 商城 | A three-phase EV charger for the garage. | Eine dreiphasige Wallbox für die Garage. | ⊆ 三相两件（11 kW 3557、22 kW 3587）；单相 7 kW（3586）不冒充三相 |
| A9 | 商城 | Which energy meters do you carry? | Welche Energiemessgeräte führen Sie? | ⊆ accessories 的计量件（2281 2394 2397）；长列表时问句不写数字 |
| A10 | 商城 | Do you have a battery base or a stack bridge for the OCEAN 2? | Haben Sie einen Batterie-Sockel oder eine Stack-Bridge für den OCEAN 2? | ⊆ {3608 EcoFlow Base, 3609 EcoFlow Bridge}；附 get-product 文档 |

## B. 四入口（各 ≥2 问）

入口形态按 2026-10-16 的实例取证（docs/specs/13-genie.md §C Entries）：产品页的条目是工具行的 "Ask Genie"（`[data-pdp-ask]`）与 dock 的开场提示；账户页的条目是常驻 dock（账户面不渲染自己的芯片组）；购物车是 `draft_chips` 的两枚芯片。

| # | 入口 | EN | DE | 期望 |
|---|---|---|---|---|
| B1 | 商品页 H2-10K-T3（4107）工具行点 "Ask Genie"（问句经 `linker-genie-ask` 交给 dock） | Which batteries have documented pairing with this model? | Welche Batterien haben ein dokumentiertes Pairing mit diesem Modell? | 只列 check-compatibility 对 4107 放行（released / released_with_accessory）的电池；附文件 |
| B2 | 商品页 4107，dock 开场提示 "Compare with…"（或同面直接问） | Compare this with the GW10K-ETA and the HS3-10K. | Vergleichen Sie dies mit GW10K-ETA und HS3-10K. | compare 块 3 ids ⊆ {4107, 3556, 2199}；正文无数字 |
| B3 | 商品页 4107，dock 开场提示 "Documents"（或同面直接问） | Where are the datasheets for this model? | Wo finde ich das Datenblatt zu diesem Modell? | 列 get-product(4107) documents，全部托管 URL |
| B4 | 购物车（Lösungsentwurf）点 "Check my draft" | Can the items in my solution draft work together? | Passen die Positionen in meinem Lösungsentwurf zusammen? | 读购物车 lines，逐对 compatibility；未放行对明确说 |
| B5 | 购物车点 "What happens next?" | What happens after I submit my inquiry? | Was passiert nach dem Absenden meiner Anfrage? | 流程句（询盘 → Proforma → 线下）；不带价格/日期承诺；无数字违规 |
| B6 | 账户页（登录）在常驻 dock 里问 "Where is my Proforma?"（dock 的开场提示即此句） | Where does my Proforma stand? | Wo steht meine Proforma? | inquiry-status 阶段条；未登录 → 要求登录句 |
| B7 | 账户页（未登录）同一 dock 入口 | Where does my Proforma stand? | Wo steht meine Proforma? | 登录请求；不泄露任何询盘数据 |

## C. 选品条件

| # | EN | DE | 期望 |
|---|---|---|---|
| C1 | I need a three-phase hybrid inverter for a home with 10 kWp PV and a future battery.（R1 原句） | Ich brauche einen dreiphasigen Hybridwechselrichter für ein Wohngebäude mit 10 kWp PV und späterer Batterie.（R2） | qualified ⊆ HOME-3φ 且 pv_input ≥ 10 kWp；排除 HS2-5K（7.5）/HS2-6K（9）；无 ETR/ESA；一个追问 |
| C2 | 12 kWp on a three-phase home, which SAJ fits? | 12 kWp auf drei Phasen im Wohnhaus, welcher SAJ passt? | ⊆ {3576 3584 4108}（24 kWp 机）∪ {1185 15 kWp?}→1185 不合格（15<12? 不，15≥12 合格）→ ⊆ {3576 3584 4108 1185}；HS3-12K PV 图值 12000 W 无引用 → 以手册/属性核，无引用记 unknown 并说明 |
| C3 | Only GoodWe, please. | Bitte nur GoodWe. | ⊆ HOME-3φ ∧ brand=GoodWe；一个追问不超 |
| C4 | Single-phase home with 5 kWp. | Einphasig, 5 kWp. | ⊆ 单相集；无三相；无 ETR |
| C5 | I have 8 kWp and want backup for the whole house. | 8 kWp, Notstrom fürs ganze Haus. | 只列 backup=yes 或 with accessory 的；条件写明（R12 同型） |
| C6 | 48 V battery for a single-phase home. | 48-V-Batterie fürs Einphasen-Haus. | 追问或按 48 V 筛；HV 机型不出现（R11） |
| C7 | Battery around 10 kWh usable. | Batterie mit rund 10 kWh nutzbar. | ⊆ 电池且 usable ≈ 10 kWh；ESA 8.3-G2x 8.0 可列并标值 |
| C8 | I already have a GoodWe GW10K-ET and want to add a battery. | Ich habe einen GoodWe GW10K-ET und will eine Batterie ergänzen. | 只列对 ET 有放行文件的电池；三值标注；附文件（R10） |
| C9 | What fits 12 kWp?（冲突追问） | Was passt zu 12 kWp?（冲突） | "12 kWp … HS3-5K?" → HS3-5K 不推荐（PV 上限 10 kWp），改推 24 kWp 级（R3） |
| C10 | A hybrid inverter for a home. | Ein Hybridwechselrichter für ein Wohngebäude. | 事实不足：追问相数或 kWp 一项；列单相+三相（R4） |

## D. 对比 / 文档 / 库存与价格

| # | EN | DE | 期望 |
|---|---|---|---|
| D1 | Compare GW10K-ETA, HD-P3-10K0 and H2-10K-T3. | Vergleichen Sie GW10K-ETA, HD-P3-10K0 und H2-10K-T3. | compare ⊆ {3556, 3555, 4107}；电池能量与逆变器输出不混行 |
| D2 | Which battery pairs with the GW10K-ETA? | Welche Batterie passt zum GW10K-ETA? | check-compatibility(3556, battery)；附文件 |
| D3 | Do you have the ESA datasheet? | Haben Sie das ESA-Datenblatt? | 搜索知识库；只给我们自己托管的 URL |
| D4 | Is the HS3-10K in stock? | Ist der HS3-10K auf Lager? | 有货（stock 一律 in stock for orderable）；不写数量/日期（R9） |
| D5 | What does the GW10K-ETA cost? | Was kostet der GW10K-ETA? | 登录+有价 → 卡内价格；未登录 → 登录句；无 Incoterms（R9） |
| D6 | GW208.9 battery — can I order it? | GW208.9-Batterie — bestellbar? | rfq_only（1957）→ 询价句，无价格 |

## E. 范围外（只有邮箱句）

| # | EN | DE | 期望 |
|---|---|---|---|
| E1 | Do you do installations? | Machen Sie Installationen? | 只有 team 邮箱句（R8） |
| E2 | When will my order ship? | Wann wird meine Bestellung versandt? | 邮箱句；不承诺日期 |
| E3 | Who is Linker Technology? | Wer ist Linker Technology? | 邮箱句 |
| E4 | Lieferzeit? | Lieferzeit? | 邮箱句（R14 同款） |

## F. 多轮与动作

| # | 步骤 | 期望 |
|---|---|---|
| F1 | "Three-phase for home" → 追问 kWp → "10" | 第二轮 qualified ⊆ HOME-3φ∧PV≥10；总追问 = 1 |
| F2 | C1 答案卡 → "Add to solution draft" | pending → added；Store API 读回数量 ≥1；状态在卡内，按钮高度不变 |
| F3 | C1 答案卡 → "Save solution" | saving → saved；/my-account/solutions 出现；失败 → failed 句 |
| F4 | "Size a system for 5000 kWh, 10 kWp, three-phase, 80538" | open_configurator → 预填 URL /solution-configurator/?…；打开配置器 |
| F5 | 每问首开 | 披露句恰一次；之后各轮不再出现 |

## 跑法

```
just up t13 --snapshot ~/de-linker-data/20261010-0033
just serve t13
python3 tools/magic_login.py …  # 登录用例
```

结果逐条记 `docs/acceptance/<date>/13/panel-results.md`；R1/R2 的模型原始响应存 `panel-r1.json` / `panel-r2.json`。核验失败率（meta.fallback 计数 / 总轮数）写入 PR。
