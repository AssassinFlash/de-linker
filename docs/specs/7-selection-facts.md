# #7 产品事实契约

## 目标
`linker-commerce` 里有且只有一个读取"选品事实"的实现，供配置器、Genie 的 `search-products`、产品分类页筛选共用；并落定三条已裁定的数据事实与 9 台 EcoFlow 的属性补缺。

## 契约（`Linker\Commerce\Catalog\SelectionFacts::for_product(int $product_id): SelectionFactSet`）
| 键 | 来源 | 规范值 | 缺失 |
|---|---|---|---|
| `device_class` | 商品的主产品分类 slug（inverters / home-storage / battery-systems / all-in-one-systems / ems-monitoring / ev-chargers / accessories） | slug | `unknown` |
| `application` | 属性 `pa_application` | `home` / `commercial` | `unknown` |
| `phase` | 属性 `pa_phase`；缺则图值 `phase`/`phases` 归一化（`three-phase`、`Three Phase`、`3L+N+PE`、`3/N/PE` → 3；`single-phase`、`1/N/PE`、`L+N+PE` → 1；"230 V" 不作判据） | `1` / `3` | `unknown` |
| `ac_power_kw` | 图值键 `ac_output_kw_nominal`、`ac_output_w_nominal`、`rated_ac_power_kw`、`nominal_ac_power_kw`、`rated_power_kw`、`power_kw`（按此优先级取第一个存在的） | kW，只按 `unit` 换算（W→/1000；kVA 另存 `ac_apparent_kva`） | `unknown` |
| `pv_input_kw` | `max_pv_input_power_w` | kW，按 `unit`（W、Wp、kW） | `unknown` |
| `usable_kwh` / `nominal_kwh` | `module_energy_kwh_usable`、`system_usable_energy_kwh`、`usable_energy_kwh` / `module_energy_kwh_nominal`、`system_capacity_kwh_nominal`、`system_nominal_energy_kwh`、`system_energy_kwh_nominal`、`rated_energy`、`energy_kwh`、`battery_rated_energy` | kWh，按 `unit`（Wh→/1000）；范围值放 `kwh_range` 不进标量 | `unknown` |
图值读自商品 meta `_tv_b2b_figures`（JSON：键 → `{value, unit, citation?, value_de?}`，形状不变）。单位换算是一个独立的纯函数类 `Units`，有表驱动测试。`unknown` 是一等值：筛选时既不匹配也不冲突。

## REST
`GET /wp-json/linker/v1/selection-facts?ids=1,2,3`（匿名，只返回已发布商品；最多 100 个；LiteSpeed 可缓存）→ `{ "<id>": SelectionFactSet }`。商品分类页的筛选 data-* 与配置器、Genie 都读这个契约（分类页在 #12 接入）。

## 数据改动（在本地实例做，脚本进 `tools/migrate/7-facts.py`，dry-run → write；切换时随 #17 应用）
1. 6480–6488（EcoFlow，2026-10-07 新建）：`pa_application=home`；`pa_phase`：P1 系列 `single-phase`，P3 系列 `three-phase`——依据各自的数据手册页（引用写入 PR）。
2. 1959 CHS2-29.9K-T4-X：`ac_output_kw_nominal` = 29 999 W，`citation` = 数据手册 p.2（我们托管的 URL）。
3. 1179 H2-25K-T3、1181 H2-30K-T3-DE、GoodWe ETA 20/25/29.999/30 kW：`pa_application` 按各自厂商系列页/数据手册的目标客群核定（厂商怎么说我们怎么说），结论与引用写入 PR；无厂商说法则保持现值。

## 不做
不改 SKU、名称、描述、价格、库存；不迁移存储形状；不删 `_tv_b2b_figures` 的任何键。

## 验收
- [ ] PHPUnit（真实夹具 = #6 快照里 89 件商品的 meta 与属性）：输出与 `docs/research/2026-10-09/old-repo-live-catalogue-facts.md` 的 CSV 人工换算值一致；6 台 ETR → `commercial`/`3`/80–125 kW/160–250 kW；28 台住宅三相集合 + 补缺后的 6480/6481/6482；6 件 ESA 电池 `phase=unknown`。
- [ ] 单位表测试：`10`+kW→10；`10000`+W→10；`7500`+Wp→7.5；`5120`+Wh→5.12；无 unit→unknown。
- [ ] 文本 "1/N/PE a.c. 230 V" → `phase=1`，不再判三相。
- [ ] REST 匿名返回 7 个键；未发布商品不出现；101 个 id 返回 400。

2026-10-09 #7 实施按证据修订（证据见 PR）：能量键"产品自身图值先于单个模块"并补 `rated_energy_kwh`（线上 1954–1958 的 `module_energy_kwh_nominal` 只是一个模块，产品值在 `system_nominal_energy_kwh`/`rated_energy_kwh`）；可用能量键补 `usable_energy`（4103–4106 的键名；`usable_energy_kwh` 只在草稿商品上）；`system_energy_kwh_range` 进 `kwh_range`；`kwh_range`、`ac_apparent_kva` 只在图值给出时出现，7 个键始终在；不在列表里的分类取最近的列表祖先（backup-power、meters-current-transformers → accessories）；1959 同源错误的另 6 个功率值（取自同一数据手册 p.3 的 CH2 列）一并按 p.2 改为 29 999 W/VA、59 998 Wp；1179/1181 按 SAJ H2 系列页核定为 `home`。

2026-10-09 评审补记：商品的分类经祖先归并后落在两个设备类（如同时在 inverters 与 home-storage）时，`device_class` 为 `unknown`。

2026-10-09 业主裁定（产品事实冲突以数据手册为准）：草稿 4124 Pylontech PowerCube-X2 的 `system_capacity_kwh_nominal` 24.9 kWh 与电压图值引自另一产品线的文档；按我们托管的 PowerCube-X1/X2-V2 手册 p.12（X2：3.552 kWh × n、48 V × n，本品 n = 5）改为 17.76 kWh、240 V、217.5~270 V，模块 43.5~54 V，随 `tools/migrate/7-facts.json` 写入；名称本就是 17.76 kWh，不改；仍为草稿。
