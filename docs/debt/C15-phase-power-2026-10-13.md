# C15 五台相位与功率（2026-10-13）

登记册 C15（原 A5）。只核 #1178、#2409、#6482、#6529、#6530 的相位和功率。产品事实冲突以我们托管的数据手册为准；手册取不到的记「无法核实」并保持现值。

同日二次更正（本文件的最终结论）：#6530 的逆变器侧额定功率**不是**无法核实。初版只读了 STS 数据表，把它的 Inverter side 通栏单元格读成「不属于本品」；ESA 5–30 kW 用户手册 §9.3 按型号分列，GW60K-STS-G10 列在该行同样印 30 kW，两处独立印证。`inverter_side_rated_power_kw`=30 kW 连同引用恢复，产品页文案与 FAQ 同步。初版的删键已撤回。

## 怎么核的

- Woo 现值：本地实例 t110，`http://127.0.0.1:8975`，只读。命令是 `~/de-linker-local/t110/wp.sh post list`、`post term list`、`post meta get _tv_b2b_figures`，以及 `GET /wp-json/linker/v1/selection-facts?ids=1178,2409,6482,6529,6530`。读的是英文商品（选品事实的源语言）；德语孪生不另存事实。
- 手册：各商品 `_delinker_datasheet_url` 指向的 t110 媒体库 PDF，用 `pdftotext -layout` 读；列位置用 `pdftotext -bbox` 复核（词框 x 与列的 x 原点）。注册表 `plugins/linker-commerce/data/material-registry.json` 只作对照，不代替手册。
- 第二份托管文档（二次更正）：ESA 5–30 kW 用户手册，EN V1.5（`GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf`，§9.3 STS Technical Data，PDF p.339–340）与 DE V1.4（`GW_ESA-5-30kW_User-Manual-DE_V1.4.pdf`，§9.3，PDF p.372）。它是我们自己的媒体库文档：ESA 模块页（3556、3583–3585、3611、3612）以 `_delinker_manual_url` 链接它，线上 `de-linker.com/wp-content/uploads/2026/10/GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf` 返回 200。
- 消费方：`SelectionFacts::phase()` 先读 `pa_phase`，没有再读图值 `phase` / `phases`。`ac_power_kw` 按 `ac_output_kw_nominal`、`ac_output_w_nominal`、`rated_ac_power_kw`、`nominal_ac_power_kw`、`rated_power_kw`、`power_kw` 取第一个。工程 feed 的 `phase` 与 `ac_power_kw` 读同一处；图值要带 `citation.url` 为 de-linker.com 才进入 feed 的 `figures`。

读数日：2026-10-13。五台当时都是 `publish`，都没有 `pa_phase`。

## 对照

| ID | 商品 | Woo 现值（t110） | 托管手册 | 结论 |
|---|---|---|---|---|
| 1178 | SAJ ATS1-T63-A | `pa_phase` 空。图值无 `phase`/`phases`。`grid_connection` / `inverter_connection` / `backup_connection` = `Three-phase`（引用 `saj_ats1_datasheet_es.pdf` p.2，不进选品相位）。无额定 kW。选品：`phase=unknown`，`ac_power_kw=unknown` | `SAJ_ATS1_Datasheet_EN-BEU.pdf` p.2，ATS1-T63-A 列：Grid / Inverter / Backup 的 Connection 都是 Three Phase。电流是 Max. Input Current 63 A，不是 kW。本页不给额定输出功率 | 相位可核，不一致（缺）。补 `pa_phase=three-phase` 与 `phases=Three-phase`。功率无法核实，不新增功率键 |
| 2409 | GoodWe SEC3000C | `pa_phase` 空。无相位图值。`power_consumption` ≤25 W；`power_supply` `100 ~ 240 V, 50/60 Hz`。选品：`phase=unknown`，`ac_power_kw=unknown` | `GW_SEC3000C_Datasheet_EMEA-EN.pdf` p.1：电压量程写 `3L / N / PE` 与 `3L / PE`。Power Consumption ≤25 W 是控制器自身功耗。Power Supply 不写相数，也不是输出功率 | 相位可核，不一致（缺）。补 `pa_phase=three-phase` 与 `phases=Three-phase`。额定输出功率无法核实，保持无功率键 |
| 6482 | EcoFlow OCEAN 2 HD-P3-15K-G2F | `pa_phase` 空，`pa_application` 空。无 `phases`。`ac_output_kw_nominal` 15000 W，`max_pv_input_power_w` 24000 W，无 citation。选品：`phase=unknown`，`application=unknown`，`ac_power_kw=15`，`pv_input_kw=24` | `ecoflow-ocean2-three-phase-datasheet-de.pdf` p.2，列 EF HD-P3-15K-G2F：Nominale Ausgangsleistung 15000 W；Nennspannung `3L + N + PE`。同页 Gesamt-Eingangsleistung 24000 W | 相位可核，不一致（缺）。`pa_phase=three-phase` 与 `pa_application=home` 已在 `tools/migrate/7-facts.json`（票 #7），t110 尚未写入。补 `phases=Three-phase`。功率 15 kW 与手册一致，销账，不改数值 |
| 6529 | GoodWe GW30K-STS-G10 | `pa_phase` 空。`rated_power_kw` 30 kW。`rated_current_a` 63 A。无 `phases`。选品：`phase=unknown`，`ac_power_kw=30` | `GW_STS-30-60kW_Datasheet_EMEA-EN_V1.1.pdf` p.2。Grid / Back-up / Smart Port：额定电压 `3L / N / PE`；额定电流 43.5 A @ 400 V（45.5 A @ 380 V，41.6 A @ 415 V）；Max. Current 63 A；Rated Power 30 kW（落在 GW30K 列下）。Inverter side 的 Rated Power 是通栏单元格（词心 x=396.9，不在任一型号列下）；ESA 5–30 kW 用户手册 §9.3 的 GW30K-STS-G10 列在 Inverter side 块同样印 30 kW，且最大值 63 A 与通栏一致——通栏的 30 kW 就是 GW30K 的值 | 相位可核，不一致（缺），补三相。功率 30 kW 与手册 Grid/Back-up/Smart Port 一致，销账。电流不一致：63 A 是最大电流，不是额定电流。`rated_current_a` 改为 43.5 A（400 V），另记 `max_current_a` 63 A。`rated_power_kw` 30 与手册一致，只补 citation，数值不改。逆变器侧 30 kW 由两处印证，与 `rated_power_kw` 同值，不加新键 |
| 6530 | GoodWe GW60K-STS-G10 | `pa_phase` 空。`rated_power_kw` 60 kW。`rated_current_a` 100 A。`inverter_side_rated_power_kw` 30 kW（无 citation；`_tv_legacy_acf_json` 的 Inverter side 也是 30 kW）。选品：`phase=unknown`，`ac_power_kw=60`（读的是 `rated_power_kw`，不是逆变器侧那一键） | 同一份 STS 手册 p.2。Grid / Back-up / Smart Port：`3L / N / PE`；额定电流 87.0 A @ 400 V（91.0 A @ 380 V，83.4 A @ 415 V）；Max. Current 100 A；Rated Power 60 kW（落在 GW60K 列下）。Inverter side 的 Rated Power 是通栏单元格印 30（词心 x=396.9；GW30K 列值 x≈315、GW60K 列值 x≈469）。**ESA 5–30 kW 用户手册 §9.3（PDF p.339–340）：GW60K-STS-G10 列（x 原点 x=388.220）在 Inverter side 块印 Rated Power 30 kW，搭配 Max. Current 100.0、Rated. Current 43.5@400V；DE V1.4 p.372 同值** | 相位可核，不一致（缺），补三相。Grid/Back-up/Smart Port 的 60 kW 与手册一致，选品功率销账。电流不一致：100 A 是最大电流，`rated_current_a` 改为 87.0 A（400 V），另记 `max_current_a` 100 A。`rated_power_kw` 60 与手册一致，只补 citation。**逆变器侧额定功率 30 kW 两手册印证**（STS 数据表通栏行 + 用户手册 §9.3 型号列）：恢复 `inverter_side_rated_power_kw`=30 kW，citation 引 STS 数据表 p.2，evidence_refs 记两处，note 写明两处独立印证 |

## 无法核实（保持现值）

- #1178：手册给的是相数和最大电流，不给额定 kW。不写 `rated_power_kw`。
- #2409：≤25 W 是功耗，不是额定输出。100–240 V 不判定相数；相数只根据 `3L/N/PE`。不写输出功率。
- ~~#6530 逆变器侧额定功率：删键，无法核实。~~ **撤回**：ESA 5–30 kW 用户手册 §9.3 按型号分列，GW60K-STS-G10 列印 30 kW（p.340，值 xMin=388.220 = 该列 x 原点；EN V1.5 与 DE V1.4 一致）。通栏单元格与型号列两处独立印证，键恢复。
- #6530 逆变器侧额定电流：两处都在（额定 43.5 A @ 400 V 一致；最大电流不同——数据表通栏 63 A，手册 GW60K 列 100.0 A）。本轮不新增该键（本轮范围是功率键的恢复，且 `SelectionFacts` 与引擎都不读逆变器侧电流）；事实记在这里。

## 写入

写入数据在 `tools/migrate/c15-facts.json`（与 `7-facts.json` 同一 from/to 形状）。不放进 `7-facts.json`：`LiveCatalogue` 会把那份计划整份套到 2026-10-09 夹具上，而 #1178/#2409/#6529/#6530 不在那份夹具里。切换数据步在 `7-facts.json` 之后跑 `7-facts.py --plan tools/migrate/c15-facts.json`。#6482 的 `pa_phase=three-phase` 与 `pa_application=home` 仍是 #7 计划里已有的项，t110 上本轮一并写入。`plugins/linker-commerce/data/material-registry.json` 里 `mat_goodwe_gw30k_sts_g10` / `mat_goodwe_gw60k_sts_g10` 的额定电流和最大电流改成与手册同一读数；GW60K 的 `inverter_side_rated_power_kw`=30 kW 带 citation（STS p.2）与 evidence_refs（数据表 p.2 + EN 手册 p.339–340）与注记，两处独立印证。

产品页读的是 `_tv_legacy_acf_json` / `_linker_de_acf_json`：benefit 首条与 feature 首卡按两手册恢复 30 kW 表述。文案行不在 `drop_legacy`（那是规格表行）的机制里，为此 `7-facts.py` / `7-facts.php` 增加 `legacy_copy` 组：按 `meta_key` + 路径替换一个字符串，同一 from/to 合同（`from` 记两个可接受现值：线上原句与 t110 本月改过的句子；两者都判 apply，其余判 drift）。`_linker_de_source_acf_json` 是翻译底稿，不渲染，不动。FAQ 发布源 `docs/faq/goodwe-gw60k-sts-g10.json` 第一条改成「两处手册都印证逆变器侧 30 kW」，经 `tools/faq/import.py --write` 写入 `_linker_faqs`（含德语孪生镜像）。

产品页的 legacy 规格表：上一轮把 Inverter side 组整组删了（被删的就是「Rated power 30 kW / Nennleistung 30 kW」行，行注原文「Printed for this Model on both the EMEA datasheet and the ESA 5–30 kW manual.」——行注与本次结论一致；行内容见备份 `c15-facts-backup-127.0.0.1_8975-20261013-032826.json`）。本轮范围是恢复 benefit/feature 四条文案与数据键，`legacy_copy` 只替换既有字符串、不插入行，规格表没有插行机制；该组当前仍不在规格表上。产品页的 30 kW 表述在 benefit、feature、FAQ 三处（EN/DE 同源），数值事实在 `_tv_b2b_figures` 与注册表两处。

t110 的写入历史（备份在 `~/de-linker-local/t110/backups/`）：

1. 第一写（备份 `7-facts-c15-backup-…-20261013-014112.json`）把 #6530 的 `inverter_side_rated_power_kw` 写成 60 kW 并挂 p.2 citation——数据表对不上，错。
2. 第二、三写（备份 `c15-facts-backup-…-032522.json` 与 `…-032826.json`）改成删键并删产品页 legacy 规格行——只读数据表，读漏了用户手册，过度更正。
3. 第四写（备份 `c15-facts-backup-127.0.0.1_8975-20261013-044057.json`）按二次更正恢复：`inverter_side_rated_power_kw`=30 kW 带双来源，产品页四条文案行恢复；写回后逐条读回 done（20/20，0 drift）。写完后 `selection-facts` 与 `engineering-feed` 对五台的相位为 3；#1178/#2409 的 `ac_power_kw` 仍是 `unknown`；#6482/#6529/#6530 为 15/30/60；工程 feed 重新带 `inverter_side_rated_power_kw`（citation 指向数据表 p.2）。FAQ 经 `tools/faq/import.py --write` 写入 `_linker_faqs`（6530 与德语孪生 6575 同文）。
4. 线上只做过一次只读 dry-run（`7-facts.py --plan tools/migrate/c15-facts.json --wp "ssh hostinger-de-linker /usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html"`，无 `--write`）：**20 to apply, 0 done, 0 drifted**——线上持无 citation 的 30 kW 与两语言原句，计划逐条判 apply，切换时由同一份计划落地。未对 https://de-linker.com 写。

## 组消失的定位与防线（2026-10-16 结案）

「Inverter side 组从实例上消失」的缺陷候选（未拍面补拍包 §6-4）到此定位：**消失点就是本页写入历史的第二、三写**——计划里 `to: null` 的那条变化带 `drop_legacy`（`titles: ["Inverter side", "Wechselrichterseite"], labels: ["Rated power", "Nennleistung"]`，见提交 `e85ee87c`），`7-facts.php` 的删除器把行删掉后**组随之消失**（组只剩这一行）。证据链：备份时间线里 `…-032826`（第二、三写之间）两个语言表都是三组，`…-044057`（第四写前）都是两组；`pull load` 无责——同快照（`20261015-1852`）装入全新实例后两张表逐字节等于快照（5041 / 5242 B，三组）。第四写恢复了数据键与四条文案，但 `legacy_copy` 不插行，规格组因此没有回来；实例侧的补回见未拍面补拍包（`restore-inverter-side.php`）。

防线（本轮加在迁移工具里，见 PR）：

- **`7-facts.php`**：删除器算完每个表的结果后，**先**检查有没有组会因删行而空掉；空的组必须在变化的 `drop_legacy.remove_groups` 里点名才删，否则**在任何 meta 被写之前**拒绝（理由打到 stderr，WP-CLI 以非零退出）。
- **`7-facts.py`**：写后读回增加「legacy 组完整性」断言——触碰过的商品、两张表，凡写前有、写后没的组，未在计划的 `remove_groups` 里点名就判失败（`The write removed spec groups the plan does not name`）。

即：**迁移（改行、改文案）不再能无声地删掉一个规格组**；要删，计划必须写出来。C15 的第三次写入在今天会被这两道中的第一道直接挡下。
