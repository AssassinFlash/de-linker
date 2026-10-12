# C15 五台相位与功率（2026-10-13）

登记册 C15（原 A5）。只核 #1178、#2409、#6482、#6529、#6530 的相位和功率。产品事实冲突以我们托管的数据手册为准；手册取不到的记「无法核实」并保持现值。

## 怎么核的

- Woo 现值：本地实例 t110，`http://127.0.0.1:8975`，只读。命令是 `~/de-linker-local/t110/wp.sh post list`、`post term list`、`post meta get _tv_b2b_figures`，以及 `GET /wp-json/linker/v1/selection-facts?ids=1178,2409,6482,6529,6530`。读的是英文商品（选品事实的源语言）；德语孪生不另存事实。
- 手册：各商品 `_delinker_datasheet_url` 指向的 t110 媒体库 PDF，用 `pdftotext -layout` 读。注册表 `plugins/linker-commerce/data/material-registry.json` 只作对照，不代替手册。
- 消费方：`SelectionFacts::phase()` 先读 `pa_phase`，没有再读图值 `phase` / `phases`。`ac_power_kw` 按 `ac_output_kw_nominal`、`ac_output_w_nominal`、`rated_ac_power_kw`、`nominal_ac_power_kw`、`rated_power_kw`、`power_kw` 取第一个。工程 feed 的 `phase` 与 `ac_power_kw` 读同一处；图值要带 `citation.url` 为 de-linker.com 才进入 feed 的 `figures`。

读数日：2026-10-13。五台当时都是 `publish`，都没有 `pa_phase`。

## 对照

| ID | 商品 | Woo 现值（t110） | 托管手册 | 结论 |
|---|---|---|---|---|
| 1178 | SAJ ATS1-T63-A | `pa_phase` 空。图值无 `phase`/`phases`。`grid_connection` / `inverter_connection` / `backup_connection` = `Three-phase`（引用 `saj_ats1_datasheet_es.pdf` p.2，不进选品相位）。无额定 kW。选品：`phase=unknown`，`ac_power_kw=unknown` | `SAJ_ATS1_Datasheet_EN-BEU.pdf` p.2，ATS1-T63-A 列：Grid / Inverter / Backup 的 Connection 都是 Three Phase。电流是 Max. Input Current 63 A，不是 kW。本页不给额定输出功率 | 相位可核，不一致（缺）。补 `pa_phase=three-phase` 与 `phases=Three-phase`。功率无法核实，不新增功率键 |
| 2409 | GoodWe SEC3000C | `pa_phase` 空。无相位图值。`power_consumption` ≤25 W；`power_supply` `100 ~ 240 V, 50/60 Hz`。选品：`phase=unknown`，`ac_power_kw=unknown` | `GW_SEC3000C_Datasheet_EMEA-EN.pdf` p.1：电压量程写 `3L / N / PE` 与 `3L / PE`。Power Consumption ≤25 W 是控制器自身功耗。Power Supply 不写相数，也不是输出功率 | 相位可核，不一致（缺）。补 `pa_phase=three-phase` 与 `phases=Three-phase`。额定输出功率无法核实，保持无功率键 |
| 6482 | EcoFlow OCEAN 2 HD-P3-15K-G2F | `pa_phase` 空，`pa_application` 空。无 `phases`。`ac_output_kw_nominal` 15000 W，`max_pv_input_power_w` 24000 W，无 citation。选品：`phase=unknown`，`application=unknown`，`ac_power_kw=15`，`pv_input_kw=24` | `ecoflow-ocean2-three-phase-datasheet-de.pdf` p.2，列 EF HD-P3-15K-G2F：Nominale Ausgangsleistung 15000 W；Nennspannung `3L + N + PE`。同页 Gesamt-Eingangsleistung 24000 W | 相位可核，不一致（缺）。`pa_phase=three-phase` 与 `pa_application=home` 已在 `tools/migrate/7-facts.json`（票 #7），t110 尚未写入。补 `phases=Three-phase`。功率 15 kW 与手册一致，销账，不改数值 |
| 6529 | GoodWe GW30K-STS-G10 | `pa_phase` 空。`rated_power_kw` 30 kW。`rated_current_a` 63 A。无 `phases`。选品：`phase=unknown`，`ac_power_kw=30` | `GW_STS-30-60kW_Datasheet_EMEA-EN_V1.1.pdf` p.2。Grid / Back-up / Smart Port：额定电压 `3L / N / PE`；额定电流 43.5 A @ 400 V（45.5 A @ 380 V，41.6 A @ 415 V）；Max. Current 63 A；Rated Power 30 kW。Inverter side 只有一列，30 kW / 最大 63 A，横坐标落在 GW30K 列下 | 相位可核，不一致（缺），补三相。功率 30 kW 与手册一致，销账。电流不一致：63 A 是最大电流，不是额定电流。`rated_current_a` 改为 43.5 A（400 V），另记 `max_current_a` 63 A。`rated_power_kw` 30 与手册一致，只补 citation，数值不改 |
| 6530 | GoodWe GW60K-STS-G10 | `pa_phase` 空。`rated_power_kw` 60 kW。`rated_current_a` 100 A。`inverter_side_rated_power_kw` 30 kW。选品：`phase=unknown`，`ac_power_kw=60`（读的是 `rated_power_kw`，不是逆变器侧那一键） | 同一份 STS 手册 p.2。Grid / Back-up / Smart Port：`3L / N / PE`；额定电流 87.0 A @ 400 V（91.0 A @ 380 V，83.4 A @ 415 V）；Max. Current 100 A；Rated Power 60 kW。Inverter side 不印 GW60K 列 | 相位可核，不一致（缺），补三相。Grid/Back-up/Smart Port 的 60 kW 与手册一致，选品功率销账。电流不一致：100 A 是最大电流，`rated_current_a` 改为 87.0 A（400 V），另记 `max_current_a` 100 A。`rated_power_kw` 60 与手册一致，只补 citation。逆变器侧 30 kW 是 GW30K 那一列，不是本品；改为 60 kW，与本品另外三侧一致。逆变器侧额定电流手册未单列，不新造电流键 |

## 无法核实（保持现值）

- #1178：手册给的是相数和最大电流，不给额定 kW。不写 `rated_power_kw`。
- #2409：≤25 W 是功耗，不是额定输出。100–240 V 不判定相数；相数只根据 `3L/N/PE`。不写输出功率。
- #6530 逆变器侧额定电流：手册该块只有 GW30K 一列（43.5 A @ 400 V / 最大 63 A）。不把这一列抄到 6530，也不用 87.0 A 去填一个手册没印的键。

## 写入

写入数据在 `tools/migrate/c15-facts.json`（与 `7-facts.json` 同一 from/to 形状）。不放进 `7-facts.json`：`LiveCatalogue` 会把那份计划整份套到 2026-10-09 夹具上，而 #1178/#2409/#6529/#6530 不在那份夹具里。#6482 的 `pa_phase=three-phase` 与 `pa_application=home` 仍是 #7 计划里已有的项，t110 上本轮一并写入。`plugins/linker-commerce/data/material-registry.json` 里 `mat_goodwe_gw30k_sts_g10` / `mat_goodwe_gw60k_sts_g10` 的额定电流、最大电流和 GW60K 逆变器侧功率改成与手册同一读数。GW60K 逆变器侧额定电流手册未印，注册表不加这个键。

t110 已按 `c15-facts.json` 写入并读回（备份 `~/de-linker-local/t110/backups/7-facts-c15-backup-127.0.0.1_8975-20261013-014112.json`）。写完后 `selection-facts` 与 `engineering-feed` 对五台的相位为 3；#1178/#2409 的 `ac_power_kw` 仍是 `unknown`；#6482/#6529/#6530 为 15/30/60。未对 https://de-linker.com 写。切换前线上仍是改前的值。
