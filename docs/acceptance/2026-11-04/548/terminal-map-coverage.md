# #548 · 端子图落库覆盖表（2026-11-04）

本批把五个机型族的厂商端子图写进 `_linker_installation_facts`（`basis: manufacturer_terminal_map`），
每个端子组带 `document_id` / `blob_sha256` / `document_revision` / `page` / `quote`。
下表说明**写了什么**、**故意没写什么**，以及每条引用的位置。

## GoodWe ET（1946 / 1947 / 1948 / 6506）

引用文档：`GW_ET-100kW_User-Manual-EN_V1.2`（`doc-cbd6d3d2…`，307 页）。

| 事实 id | 域 | 端子 | 页 |
| --- | --- | --- | --- |
| `pv-dc-input-terminals` | pv_dc | PV+ / PV- | 49 |
| `battery-dc-input-terminals` | battery_dc | BAT+ / BAT- | 49 |
| `protective-earth-terminals` | pe | PE | 49 |
| `ac-wiring-terminals` | ac | AC | 49 |
| `ems-communication-terminal` | communication | COM1 | 191 |
| `meter-sts-communication-terminal` | communication | COM2 | 192 |
| `dongle-communication-terminal` | communication | COM3 | 192 |

**故意没有 BACK-UP 端子。** ET 50–100 kW 逆变器本体不提供 BACK-UP 端子：厂家要求备电经外部 STS
（`GW125K-STS-G10` / `GW375K-STS-A-G10` / `GW750K-STS-A-G10`），BACK-UP / SMART-PORT / GRID 端子属于 STS 本体
（同一手册 p.51 的 STS 部件表）。把 STS 的端子记到 ET 名下会让配置器接受一个厂商并未提供的接线点。

**注意**：`manufacturer-evidence.md` §3 给的页码（p.160 / p.190–192）指向的是 **ET 50–100 kW EN V1.3（65 页）**，
那份文档里没有 COM 端子表。COM1/COM2/COM3 只存在于 307 页的
`GW_ET-100kW_User-Manual-EN_V1.2`，本批按后者绑页。

## GoodWe ETR（6507 / 6508 / 6509 / 6510 / 6511）

引用文档：`GW_ETR-50-125kW_User-Manual-EN_V1.0`（`doc-e135c80b…`，215 页）。

| 事实 id | 域 | 端子 | 页 |
| --- | --- | --- | --- |
| `pv-dc-input-terminals` | pv_dc | MPPT | 24 |
| `sts-terminal` | ac | STS | 24 |
| `ac-terminals` | ac | AC | 24 |
| `inverter-communication-terminal` | communication | COM1 | 24 |
| `service-communication-terminal` | communication | COM2 | 24 |

ETR 的 BACK-UP 同样只经 STS 提供，本体只标 `STS Port`，因此备电一侧按 `sts-terminal` 记录。

## GoodWe ESA 5–30 kW（3556 / 3583–3585 / 6512–6518）

引用文档：`GW_ESA-5-30kW_User-Manual-EN_V1.5`（`doc-a7cfa5ad…`，351 页）。

| 事实 id | 域 | 端子 | 页 |
| --- | --- | --- | --- |
| `battery-connector` | battery_dc | Battery connector | 51 |
| `sts-communication-interface` | communication | STS | 51 |
| `pv-input-terminals` | pv_dc | PV input | 51 |
| `backup-port` | ac | BACK-UP | 51 |

这一族**本体带 BACK-UP 端口**（与 ET/ETR 不同），因此 `backup-port` 记在逆变器名下。

## GoodWe ESA 3–10 kW 单相（6523–6528）

引用文档：`GW_ESA-3-10kW_User-Manual-EN_V1.8`（`doc-c4fbcd95…`，324 页）。

| 事实 id | 域 | 端子 | 页 |
| --- | --- | --- | --- |
| `on-grid-port` | ac | ON-GRID | 49 |
| `backup-port` | ac | BACK-UP | 49 |
| `communication-port` | communication | COM | 49 |
| `pv-input-terminals` | pv_dc | PV input | 49 |

## SAJ H2 10–30K（1179 / 1181 / 2063 / 2064 / 4107 / 4108）

引用文档：`SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf`（`doc-71f7f3e6…`，59 页，双语，页 43 为英文版部件表）。

| 事实 id | 域 | 端子 | 页 |
| --- | --- | --- | --- |
| `mppt-pv-input-terminals` | pv_dc | MPPT1 / MPPT2 / MPPT3 | 43 |
| `battery-input-terminals` | battery_dc | BAT1+ / BAT1- / BAT2+ / BAT2- | 43 |
| `communication-terminal` | communication | LAN / CAN / PART / EMS / RS485 / METER / DRMs | 43 |
| `ac-terminals` | ac | GRID / BACK-UP | 43 |
| `grounding-terminal` | pe | Grounding | 43 |

## 为什么这些事实能进配置器

`services/engine/src/linker_engine/planning/installation_terminals.py:105-140` 要求：

- `basis == "manufacturer_terminal_map"`
- `specification.terminal_domain` 命中 `ac / pe / battery_dc / pv_dc / communication`
- `specification.terminals` 是非空字符串数组
- `source.document_id` 与 `document_revision` 等于当前绑定
- 端子名出现在 `terminals` 里

`plugins/linker-commerce/includes/Products/Publication/InstallationFacts.php:159-203` 的
`specification()` 是同一套 PHP 侧白名单；`terminal_use` 只允许 `communication` 域 + 非空端子。

本批 244 条事实已用**真实** `InstallationFacts::bind()` 逐条跑过（37 个产品、0 错误），
不是只靠 schema 检查。

## 未覆盖、也不该硬凑的

- **GoodWe ET / ETR 的 BACK-UP 端子**：厂商不在逆变器本体提供（见上）。
- **GoodWe BAT-C 208.9/261.2 的 AC 端子**：电池柜只有 P+/P- 与 COM1–COM4，其 AC 侧属于液冷与消防单元，
  不是客户接线点；本批未写。
- **SAJ HS3 / CB2 的端子图**：本批未纳入（任务范围只列到 H2）；HS3 手册 p.22 的端口表可作为下一批输入。
