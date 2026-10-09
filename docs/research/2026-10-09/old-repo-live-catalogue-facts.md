# 线上目录事实盘点（只读 GET，2026-10-09）

结论：筛"住宅三相"可依赖 Woo `pa_application`/`pa_phase`，但 9 台缺属性；交流功率与最大光伏输入每台都有，但单位与键名不统一；组件库和注册表都把 GoodWe ESA 功率模块分在"混合逆变器"之外。106 件已发布商品；明细表 `live-catalogue-facts.csv`（89 行 × 32 列，每值注明来源字段）。

## 数据从哪读
- 品类：`inverters` 59 件全为混合逆变器（EcoFlow OCEAN 2、GoodWe ESA ETA/EHA、ET-G10、ETR，SAJ H2/HS2/HS3）；电池 30 件（home-storage 16、battery-systems 9、all-in-one-systems 5）；`backup-power` 不在范围。
- 属性：`pa_application`（id 6）词条是 `home`（65）/`commercial`（32），不是 Residential；`commercial-industrial` 无商品。`pa_phase`（id 4）：`single-phase` 11、`three-phase` 46。
- `_tv_b2b_figures`：带认证的 `/wc/v3/products` 的 `meta_data` 里，106 件都有；JSON 字符串，每项 `{value, unit, evidence_refs?, value_de?}`。
- 供货：`/wp-json/linker/v1/materials` 公开投影无 `woo_product_ids`；`linker_supply_relation`/绑定读自链尖 `material-registry.json`（revision 与线上 `/tvb2b/v1/material-runtime` 一致，overrides 为空）。已绑定 79 件全部 normal/orderable、in_stock。10 件无打包绑定：9 台 2026-10-07 新建 EcoFlow + 6321 ESA-LCN（ADR-0034 运行时 `mat_product_<id>`）。
- 可购性/价格：仅 1957 GW208.9-BAT-LCD-G10 为 `rfq_only`；89 件全部有价。

## 交流功率与光伏输入
- 交流额定：53 件 `ac_output_kw_nominal`，其中 26 件存 W、27 件存 kW；6 件（新 EcoFlow P1）用 `ac_output_w_nominal`。
- 最大光伏输入 `max_pv_input_power_w`：59/59 有，单位 kW 27、W 17、Wp 15。

## 字段可靠性（混合逆变器 59）
| 字段 | 有值 | 缺 |
|---|---|---|
| `pa_application` | 50 | 9 台新 EcoFlow（6480–6488） |
| `pa_phase` | 50 | 同上 |
| figures `phases`/`phase` | 51 | 6523–6528（EHA 单相）、6506 GW75K-ET、6482 HD-P3-15K-G2F |
| 交流功率 | 59 | — |
| 最大光伏输入 | 59 | — |
- 相位写法：`Three-phase`、`Three Phase`、`3L+N+PE`、`Single-phase`，需归一化；属性、图值、名称三者无矛盾。
- Application 跨品牌不一致：SAJ H2-25K-T3（1179）、H2-30K-T3-DE（1181）Commercial，H2-20K Home；GoodWe ETA 20/25/29.999/30 kW 全部 Home。
- 类型标记误导：17 台 GoodWe ESA ETA/EHA 在 Woo `_delinker_type=system`、注册表 `fixed_system`、组件库 `all_in_one`，三处都不是 hybrid_inverter。
- 电池 30：`pa_application` 30/30；`pa_phase` 仅 4 件（3 台 SAJ CHS2 一体机 + 6321）；kWh 键名 7 种以上（`module_energy_kwh_nominal/_usable`、`system_*_energy_kwh`、`rated_energy`、`energy_kwh`、`battery_rated_energy`、`system_energy_kwh_range`）；GoodWe BAT-AC/LC/LCD 只有模块 kWh；BC2-HV1 只有范围值。

## 住宅三相混逆集合（`home` ∧ `three-phase`，28 台，全部 orderable、有价、in_stock、有绑定；AC kW 已统一）
| AC kW | 产品（id，最大光伏输入） |
|---|---|
| 5 | GW5K-ETA-G20（6512，10 kW）；HS2-5K（4109，7.5 kWp）；HS3-5K（2198，10 kWp） |
| 6 | HD-P3-6K0-S2（3574，12 kW）；GW6K-ETA（6513，12 kW）；HS2-6K（1183，9 kWp）；HS3-6K（1186，12 kWp） |
| 8 | HD-P3-8K0（3575，16 kW）；GW8K-ETA（3583，16 kW）；HS2-8K（1184，12 kWp）；HS3-8K（1187，12 kWp） |
| 9.999–10 | GW9.999K-ETA（6514，20 kW）；HD-P3-10K0（3555，20 kW）；GW10K-ETA（3556，20 kW）；H2-10K-T3（4107，20 kWp）；HS2-10K（1182，15 kWp）；HS3-10K（2199，15 kWp） |
| 12 | HD-P3-12K0（3576，24 kW）；GW12K-ETA（3584，24 kW）；H2-12K（4108，24 kWp）；HS3-12K（1185，15 kWp） |
| 15–30 | GW15K-ETA（3585）；H2-15K（2063）；GW20K-ETA（6515）；H2-20K（2064）；GW25K-ETA（6516）；GW29.999K-ETA（6517）；GW30K-ETA（6518） |
另：6480 HD-P3-5K0-S2、6481 HD-P3-15K-G2、6482 HD-P3-15K-G2F 按名称和图值也是三相住宅机，但缺属性；1185 HS3-12K 的 12000 W 无引用。

## ETR 与 ESA 电池
6 台 ETR 全部 `commercial` + `three-phase` + `_delinker_type=inverter`，注册表 hybrid_inverter/goodwe-etr：GW80K 6507（80 kW，PV 160 kW）、GW99.99K 6508（99.99，200）、GW100K 6509（100，200）、GW110K 6510（110，220）、GW124.99K 6511（124.99，250）、GW125K 3595（125，250）；相位图值键名是 `phase`。
6 件 ESA 电池模块：`home`，无 `pa_phase`，`home-storage`，`_delinker_type=system`，注册表 battery_system，组件库 `goodwe-esa-bat-d-g20`（含 G21）；标称/可用 kWh：5.1-G20 6519 5.12/5.0、5.1-G21 6521 5.12/5.0、6.0 3611 6.0/5.8、8.3-G20 6520 8.32/8.0、8.3-G21 6522 8.32/8.0、9.0 3612 9.0/8.7。

## 与链尖 `components-db.json` 对比
- 组件库无用途字段。相位两边有值者无矛盾。
- 交流功率不一致：1959 SAJ CHS2-29.9K-T4-X Woo 29 900 W（后台改过，无引用）vs 组件库 29 999 W（数据手册 p2）；1185 HS3-12K 组件库值 `"12000*"` 格式被污染。
- 组件库缺：9 台新 EcoFlow、6321；缺相位：6 台 EHA、6506。

## 对选品的直接含义
1. 用途、相位先读 Woo `pa_application`/`pa_phase`（住宅 = `home`）；2. 缺属性时用 figures 相位归一化补位；3. 功率按 `unit` 换算；4. 不能只靠注册表/组件库 kind 判"混合逆变器"。
