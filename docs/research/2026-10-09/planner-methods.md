# Planner 选型方法底层复盘（只读代码评审 + 外部取证）

- 代码基线：`refs/landed/chain-tip` = `f007a9dd`（2026-10-09 13:18 +0800），全部经 `git show refs/landed/chain-tip:...` 读取；行号均指该版本。
- 外部证据：全部经 Apify（`apify/rag-web-browser`，REST 调用，token 从 `~/.config/terravolt-builder/apify.env` 读取、未打印），抓取日期 2026-10-09；德语+英语关键词；原始结果存于 scratchpad `research/*.json`。
- 复现实验：用 chain-tip 引擎代码（`git archive` 到 scratchpad）+ 仓库自带的 Munich PVGIS TMY fixture（`tests/fixtures/pvgis_tmy_munich.json.gz`），在 `services/design-engine/.venv` 下离线运行，逐行复刻 `design._size_storage` / `_knee_point` / `_storage_that_pays` 的逻辑。未改动仓库、未触碰线上。
- 所有代码里的数字、方法、注释都按"声明"处理（见 §3 核对表）。

---

## 0. 结论先读

**总裁定：住宅 = "methods need rework"；C&I = "fundamentally different tool needed"（在有 Lastgang 能力之前应降级为询价流程，和 utility 一样）。**

定位本身是对的：一个 B2B 分销商的 quick calc，终点是"可下单、带兼容性证据的 Linker 逆变器+储能套件"。引擎里真正有价值、应保留的是硬件层——页码可溯的组件库、逆变器↔电池兼容性闸门、组串电压/电流校验、精确物料 BOM 与 blocker 行。偏离行业标准的是"能量与金钱"层：负荷模型、储能定容规则、经济性与法规制度。这一层需要替换方法，不是调参数。

五个最重的发现：

1. **住宅储能推荐量系统性偏大。** 复现 8 个典型户型：引擎推荐的可用容量是 HTW Berlin 推荐上限（可用容量 ≤1.5 kWh/kWp 且 ≤1.5 kWh/MWh·a）的 1.13–2.0 倍；3,000–5,000 kWh 的典型家庭是 1.5–2.0 倍。20 年回本门槛在 8 个案例里一次都没拦住（引擎算出 10–18 年）。
2. **自给率偏乐观。** HTW 给出的实测锚点：年耗 5,000 kWh、10 kW PV、10 kWh 储能的真实家庭平均自给率 77%。引擎模型在同一点给 85–86%；把电池参数换成 HTW 的假设后仍有 83–84%。所以剩下的约 6 个百分点来自负荷模型本身：H25 标准负荷曲线（SLP），再加上小时分辨率。HTW 和 SMA 都明确说过，SLP 不适合用来设计单户的自用系统。
3. **经济性依赖的法规前提将在 2027 年失效，而且现在就已经不完整。**
   - BNetzA 页面已写明 EEG 2023 只适用到 2026-12-31，但 `tariffs.yaml` 里写的是 `valid_until: 2027-01-31`。
   - EEG 2027 政府草案（Drucksache 21/7867）对 2027 年起投运的新系统取消 20 年固定上网电价，小系统改为 5.2 ct、最长 36 个月的过渡支付；另外对 <100 kW 的新屋顶系统永久设 50% 上网功率上限。
   - 现行 Solarspitzengesetz 的 60% 上网上限和负电价时段零补贴，引擎也都没有建模。
   - 引擎对所有项目一律按 20 年固定 FIT 计算。
4. **C&I 没有采用行业方法。**
   - 不收 15 分钟 Lastgang，不做削峰（`peak_shaving` 目标会被拒），不计需量电费（Leistungspreis）。所有工商业项目一律套 G25。
   - Planner 收集的 `operating_profile`、`facility_type`、`load_profile_state`、`peak_load_kw`、`grid_connection_kw` 没有一个进入引擎；`target_power_kw` 一进引擎就被判 `unsupported_scope`。
   - 复现结果：100 MWh/100 kWp 时，G25/G1/G3/G0 四种完全不同的负荷形状都推荐同一个 90 kWh（恰好是扫描上限）；250 MWh/150 kWp 时四种都推荐 0。
5. **规则硬伤（会直接产出错误结果）：**
   - 单相 >4.6 kVA 的逆变器可以被选中。组件库里有 5–12 kW 的单相机型（EcoFlow、SAJ EK90、Pylontech），而 VDE-AR-N 4105 规定单相每相 ≤4.6 kVA。
   - 组串熔断器按"每台逆变器总串数 ≥3"触发，而规则文本本身写的是"并联串数 ≥3"，应按每个 MPPT 计。结果是 C&I 的 BOM 会多出成对的 gPV 熔断器和熔断器座。
   - 年耗 <30 MWh 的小型工商业被按含税家庭电价 37 ct 计价，比 25 ct 净价高 48%。`tariffs.yaml` 自己写着"家庭含税、企业不含税，不可混用"。

---

## 1. 范围与证据

- **读过的代码：** `design.py`、`storage.py`、`pv_yield.py`、`econ.py`、`strings.py`、`bom.py`、`components.py`、`inputs.py`、`l10n.py`，外加 `cables.py`、`weather.py`、`report.py`、`api.py`、`data/tariffs.yaml`、`data/cable-tables.json`、`knowledge/components-db/*.json`（页码可溯的 datasheet 数据）、`knowledge/materials/manual-decisions.json`（Trina 参考组件）。
- **Planner 前端：** `plugins/linker-ai-assistant/assets/quote-configurator.bundle.js`（chain tip 上只有打包后的产物，没有 `src/`）。
- **WP intake：** `plugins/terravolt-b2b-core/includes/project-intake.php`。
- **外部来源：** 约 40 次 Apify 抓取。有用的来源列在 §6；没找到的东西列在 §7。

---

## 2. 逐项评审

格式：(a) 引擎做什么（file:line）；(b) 德国/欧洲行业与厂商工具的做法；(c) 裁定；(d) 行业正确版本的输入与输出。

### 2.1 PV 产量

**(a) 引擎做什么**

- `pv_yield.simulate` 的物理链是：SPA → Perez → Martin-Ruiz IAM → Faiman → Huld cSi，运行在 PVGIS 5.3 TMY 上。
  - 代码位置：`pv_yield.py:171-302`；数据获取在 `weather.py:87,273-293`。
- AC 计算为 DC × 1.0 ×（1−0.14）。
  - 代码位置：`pv_yield.py:178-180,238`。
- P50/P90 来自一组自定义不确定度（3.5/2.5/3.0/1.5%）。
  - 代码位置：`pv_yield.py:76-95`；PDF 上印为"P90 (konservativ)"（`report.py:29,123`）。
- 储能调度用的是同一链的逐时序列。
  - 代码位置：`pv_yield.py:349-392`。
- 阵列尺寸变化时按线性 rescale。
  - 代码位置：`pv_yield.py:305-346`。
  - docstring 自己承认链中没有逆变器，因此不存在削顶。
- 默认朝向 35°/180°（`design.py:36-39`）。
- 由屋顶面积推 kWp 时用 5.0 m²/kWp（`design.py:34,1284-1286`）。
- 远处地形地平线来自 PVGIS printhorizon，近处遮挡来自 LoD2（`design.py:1312-1332`）。
- 只支持一个屋面（单一 tilt/azimuth）。

**(b) 行业做法**

- **PVGIS 5 用户手册：** 网页版的总系统损失默认 14%，范围包括线缆、逆变器、污损，以及按寿命平均的组件衰减。
- **PVGIS API：** `PVcalc` 的 `loss` 是必填参数；TMY 工具的 `usehorizon` 默认为 1，也就是 TMY 数据本身已经计入地形遮挡。
- **PV*SOL premium：**
  - 逐时序仿真；
  - 可导入实测负荷曲线（例如 60 分钟分辨率时为 8760 行）；
  - 内置 BDEW H25/G25/L25 曲线。
- **SolarEdge Designer（2026-04 版）：**
  - 能建模优化器输入削顶；
  - 允许上传并编辑用户自己的用电曲线。
- **HTW 计算器：** 假设 35° 朝南、无遮挡、AC=DC，参考年发电 1,024 kWh/kW。

**(c) 裁定**

- **物理链：standard。** 本质上是 PVGIS PVcalc 的再实现，README 声称与 PVcalc 偏差在 ±5% 内（这次没有重跑验证）。
- **问题：**
  - P90 的不确定度预算是自定义的（invented），而且这不是住宅/安装商工具的标准输出。
  - `gamma_pdc_pct_per_c` 被声明，但在 `pv_yield.py:179,357` 中从未使用，是一个死参数，对应的说明也是空话。
  - 损失瀑布图（`pv_yield.py:284-290`）把 14% 标成"污损/接线/失配"、逆变器标成 0%，与 PVGIS 对 14% 的定义不符。
  - PVGIS 的 14% 已经含寿命平均衰减，而 `econ.cashflow` 又另外按每年 0.5% 衰减，属于轻度重复计算。
  - 没有削顶，也没有上网上限（60%/50%），所以 DC/AC 到 1.6 在产量上是"免费"的。HTW 估算 60% 上限在纯上网情形下损失 1.1%（东西向）到 9.0%（南向）的发电量。
  - 只支持单一屋面，而德国东西屋面很常见。
  - 5 m²/kWp 取的是 HTW 所说"每 kW 需 5–10 m²"的下限，因此由面积推 kWp 偏乐观。
  - TMY 已计入地形遮挡，引擎又再算一次。对直射分量的处理是幂等的（不会重复扣减），但瀑布图里的"远处遮挡"会接近 0，低估了地形损失（次要）。
- **是否需要逐时仿真？**
  - 年度/月度发电：不需要，直接调 PVGIS PVcalc API 就是同一套物理，也正是安装商自己会拿来核对的数字。
  - 储能 KPI：需要时序，但误差的大头在负荷侧，不在 PV 侧。HTW 的做法是预先算好分钟级仿真结果、查表输出，这是行业验证过的"又快又准"的方式。

**(d) 行业正确版**

- **输入：**
  - 邮编或坐标；
  - 1–n 个屋面，每个屋面的 kWp、倾角、方位；
  - 遮挡等级（可选）；
  - 安装商实际使用的组件（可选）；
  - 上网上限：60% / 50% / 0% / 无。
- **规则：**
  - 每个屋面调用 PVGIS PVcalc（loss=14%），或保留现有物理链；
  - 削顶与上网上限按逐时序列计算。
- **输出：**
  - 各屋面及合计的年/月发电量、比发电量；
  - 削顶/上网上限造成的损失 %；
  - 不输出 P90。

### 2.2 住宅储能定容

**(a) 引擎做什么**

- **负荷模型：** BDEW H25 SLP 按年用电量缩放（`storage.py:47-82`），然后 resample 成小时（`design.py:1342-1343`）。
- **调度：** 贪心调度，初始 SOC=0，充放电各乘 √0.92，可用容量 = 0.9 × 名义容量，功率 0.5C（`storage.py:149-266`，`design.py:1423-1429`）。
- **扫描：** 名义容量 0/5/7.5/10/12.5/15/20 kWh（`design.py:1228`）。
- **knee 点：** 达到"扫描范围内自给率增益 90%"的最小容量（`design.py:1009-1030`）。docstring 自己承认结果会随扫描上限移动。
- **按 use_case 取值：**
  - `self_consumption`：先取 knee，再过 `_storage_that_pays` 的 20 年简单回本门槛（37 ct 电价、基准 capex；`design.py:1061-1100,1442-1450`）；
  - `max_autarky`：直接取扫描最大值 20 kWh，且不过任何门槛（`design.py:1052-1053`）；
  - `backup`：取 max(knee, kW·h/(0.9·√0.92))（`design.py:1054-1057,1376-1379`）。
- **选定实物后：** 用该物料自己的功率重新调度一次，仍沿用 0.9/0.92（`design.py:1167-1215,1695-1704`），然后再做一次回本校验（`design.py:1730-1743`）。

**(b) 行业做法**

- **HTW Berlin（Orth/Weniger/Meissner，Sonnenenergie 02/2022；以及计算器 FAQ）** 给出三条规则：
  1. PV ≥0.5 kW / MWh·a，否则不建议配储能；
  2. 可用容量 ≤1.5 kWh / kW PV；
  3. 可用容量 ≤1.5 kWh / MWh·a（约等于夜间用电量）。
  - 只有在需要备电预留、或计划上热泵/电动车时，才适度放大。
  - 示例：10 kW、4,000 kWh 的家庭，可用容量不应超过 6 kWh；同样 PV 下用电量翻倍到 8,000 kWh，才可放到 12 kWh。
- **HTW 独立性计算器（Unabhängigkeitsrechner）的方法：**
  - 预先计算了 25,000 多种配置，查表输出；
  - 分钟级分辨率；VDI 4655 单户负荷；DWD 实测气象；
  - 电池：考虑老化后平均只有 90% 可用容量；电池效率 95%，充、放电各 94%，AC-AC 合计 83.9%；功率为每 kWh 可用容量 1 kW；
  - 输入：年用电量、kWp、可用容量；
  - 输出：自给率、自用率、能流；
  - 适用范围：2,000–10,000 kWh；不适用于有热泵或电动车的家庭；
  - FAQ 还明确说，在合理容量下不可能完全脱网。
- **HTW（Zoll/Weniger，40. PV-Symposium 03/2025）：**
  - 实测家庭（5,000 kWh/10 kW/10 kWh）平均自给率 77%；
  - 在线计算器对同一工况给出 76–100%。
- **HTW 牵头、DGS/SFV 支持的计算器质量标准**（nextpit，2025-07-01 报道）：
  - 用实测负荷曲线，不用 SLP；
  - 时间分辨率 ≤15 分钟；
  - 考虑电池老化；
  - 不假设不现实的电价涨幅。
- **SMA（博客，2012）：** SLP 可能让自用率被高估最多 50%；Sunny Design 用的是基于实测、按年用电量缩放的典型曲线。注意这份材料较旧。
- **SolarEdge Designer：**
  - 2026-09 版：储能推荐会按站点实际日用电量，优先给出"合适尺寸"而不是偏大的选项；
  - 2026-04 版：新增住宅储能对比页。
- **HTW Stromspeicher-Inspektion 2026：**
  - 待机功耗 4–64 W；
  - 电池效率相差 9 个百分点以上；
  - SPI 在 89.3–97% 之间。
- 没找到 BayWa 的储能图表（见 §7）。

**(c) 裁定：invented/unsourced 的方法，叠加在行业明确否定的负荷模型上，结果是错误的。**

- "90% 增益 knee"不是 HTW 的方法，代码里标注"HTW-style"属于误标。
- 复现结果：推荐的可用容量是 HTW 上限的 1.13–2.0 倍；自给率高出 6–9 个百分点（§4）。
- 20 年简单回本门槛过宽：常见电池质保是 10 年，代码注释里自己也提到过一个"10 年质保的电池"；而且没有电池老化、没有更换成本。
- `max_autarky` 对任何家庭都固定给 20 kWh：错误。
- 备电是重复计数：
  - `backup_starts_full` 假设停电时电池是满的（`design.py:1779`），同时这部分容量也全额用于日常自用调度；
  - HTW 指出，有备电功能的系统通常会在正常运行中预留一部分容量不用。
- 热泵/电动车的用电量也被摊进 H25 曲线；HTW 明确说其计算器不适用于这类家庭。

**(d) 行业正确版：见 §5.1。**

### 2.3 逆变器定型

**(a) 引擎做什么**

- **住宅候选** `_inverter_candidates`（`design.py:281-314`）：
  - 只按相数过滤；
  - DC/AC 带宽 0.7–1.6（按用户要求的 kWp 计算）；
  - 按 |ratio − 1.15| 排序。
- **C&I 候选** `_ci_inverter_candidates`（`design.py:317-382`）：
  - 最多 N 台同型号并联，`MAX_CI_UNITS = 8`（`design.py:116`）；
  - 带宽 0.8–1.6，"舒适区" 0.95–1.35；
  - 优先台数少。
- **组串枚举**（`strings.py:247-300`）：
  - 低温 Voc 用 min(−10 °C, TMY 最低温 − 5)（`design.py:1492`）；
  - 高温 Vmpp 按电池片 70 °C；
  - Isc × 1.25（NEC 690.8(A)）≤ 每路 MPPT 的 Isc 上限；
  - Impp ≤ 最大输入电流；
  - 校验最大 PV 输入功率；
  - DC/AC 0.8–1.6，以 1.15 排序。
- **电池电压窗口**带 ±20% 容差（`design.py:849,884`），超出时会打 `voltage_edge` 标记。
- **备电功率**只在 use_case=backup 时校验（`design.py:1761-1774`）。
- **参考组件**固定为 Trina TSM-460NEG9R.28（Isc 10.81 A），而 Linker 不供应组件（`design.py:62`）。

**(b) 行业做法**

- **DC/AC 比：** 典型 1.1–1.4；东西向屋面要更大幅度地压小逆变器（AC 约为 DC 的 70–80%）。（energie-experten）
- **厂商允许的最大 PV 输入 ÷ AC 额定**（来自页码可溯组件库）：

  | 品牌 | 型号/系列 | 最大 PV 输入 ÷ AC |
  | --- | --- | --- |
  | GoodWe | ET Plus、ET 15–50 kW | 1.5× |
  | GoodWe | ET 80–100 kW、ESA | 2.0× |
  | GoodWe | ETC | 1.3× |
  | SAJ | H2 | 1.5–2.0× |
  | SAJ | HS2 | 1.5× |
  | SAJ | HS3、EK90、CHS2 | 2.0× |
  | EcoFlow | OCEAN2 | 2.0× |
  | EcoFlow | PowerOcean | 2.0–3.0× |
  | Pylontech | H3X | 1.6× |

- **VDE-AR-N 4105：**
  - 单相每相 ≤4.6 kVA（三相不平衡限制），超过须用三相，或多台单相通讯耦合；
  - >30 kVA 须集中式 NA-Schutz；
  - 4105 适用于 ≤135 kW；135–950 kW 须满足 VDE-AR-N 4110；
  - 新版 4105:2026-03 已生效。
  - 来源：energie-experten，solarzubau。
- **Solarspitzengesetz：**
  - 没有智能电表/控制装置的新系统，上网上限为 60%（≥7 kWp 必须装 iMSys 和控制装置）；
  - 负电价时段不补贴。
  - 来源：ista 2026-01-27；enyo 2026-10-01，法律状态截至 2026-09-24。
- **并联上限：**
  - GoodWe SEC3000 产品页：RS485 最多 60 台；
  - SAJ eManager-C1 Pro：2–10 台 CHS2（这是引擎代码里自己的注释）。

**(c) 裁定**

- **组串校验：standard / acceptable。** Isc×1.25 偏保守；未能找到厂商工具的依据来确认或否定。
- **DC/AC 带宽：acceptable approximation。** 但它不是按厂商分别设定的；混合逆变器允许 1.5–2×；在有上网上限时，真正的约束是上网 kW，而不是逆变器 AC。
- **相数规则：wrong/missing。**
  - `RESIDENTIAL_INVERTER_FAMILIES` 里包含 5–12 kW 的单相机型，引擎没有 4.6 kVA 上限；
  - 相数未知时，单相和三相都会进入候选；住宅 Planner 又不强制填相数。
- **`MAX_CI_UNITS = 8`：unsourced。**
- **电池电压 ±20% 容差：invented**（虽然会打标记）。
- **参考组件：** 只有在明确标注为"默认组件"时才可接受。组串方案不能直接搬到安装商的真实组件上：大尺寸组件 Isc 13–18 A，会在某些 MPPT 上超限，而 Trina 这款 10.81 A 的组件能通过。
- **C&I 缺少合规标记：** 没有 >135 kW 时的 4110 提示，也没有 >30 kVA 时的 NA-Schutz 提示。

**(d) 行业正确版：见 §5。**

### 2.4 C&I

**(a) 引擎做什么**

- **对用户问题前提的修正：** `operating_profile` 不是自由文本，而是枚举值（daytime / two_shift / three_shift / continuous / variable / unknown；`project-intake.php:39-42`），而且引擎完全没有用到它。引擎里也没有任何削峰定容。
- **负荷曲线：**
  - 所有 C&I 项目都用 G25（`design.py:1336-1341`）；
  - 用户界面会提示"使用标准负荷曲线"（`l10n.py:39`）。
- **扫描范围：** 上限 = min(300, max(40, round(0.4 × 日用电 / 25) × 25)) kWh（`design.py:1368-1372`），unsourced。
- **use_case 限制：**
  - 只允许 self_consumption / backup（`inputs.py:69-71`）；
  - intake schema 里有的 `peak_shaving`、`dynamic_tariff`、`grid_feed_in`（`project-intake.php:27-29`）全部被拒；
  - `target_power_kw` 被判为 unsupported（`inputs.py:77-78`）。
- **Planner 的计算前置条件**（bundle `4564-4596`）：目标只能是这两种，必须已知相数，而且不能有 `target_power_kw`、约束、既有设备或耦合方式偏好，否则不发起计算。
- **收集了但没用：**
  - `operating_profile`、`load_profile_state`、`facility_type`、`peak_load_kw`（`project-intake.php:317`）、`grid_connection_kw` 都被收集（bundle `4488-4505`）；
  - 但它们不在发往引擎的 payload 里（bundle `4598-4635`；`tv_b2b_project_calculation_inputs` 的白名单在 `project-intake.php:1246-1300`）。
- **硬件与经济门槛：**
  - ≤8 台同型号并联，或 SAJ CHS2 一体柜；
  - 回本门槛只用净电价（25 / 16.7 ct），没有需量电费。

**(b) 行业做法**

- **Intilion（C&I 储能厂商）：**
  - 定容依据是上一整年的 15 分钟 Lastgang；
  - 年用电 >100,000 kWh 或 >30 kW 的 RLM 用户，可从配电网运营商（DSO）处拿到这份数据；
  - RLM 用户的电网费由 kWh 和年度峰值 kW 两部分组成。
- **Voltfang（2026-02-18）：** 用 15 分钟 Lastgang + 电费账单，重点识别峰值。
- **stromfee（2026）：** kW 由"高出基础负荷带的高度"决定，kWh 由"峰值以上的面积"决定。
- **furoenergy（2025-07-03）：** 削峰是一个在负荷/PV 时序上、同时考虑 €/kW 与 €/kWh 的优化问题。
- **akkusmart：** Lastgang 分析出的功率与容量是两个核心设计值。
- **SLP 的适用范围（Wikipedia）：**
  - SLP 只用于没有注册式功率计量的计量点，通常 ≤100 MWh/a；
  - G0 是 G1–G6（办公 / 晚间 / 连续 / 零售 / 烘焙 / 周末）的加权平均；
  - 2025 版只有一个笼统的 G25。
- **SolarEdge Designer 2026-09 版：** 新增按年计费的需量电费，明确面向德国商业项目。
- 没找到 Memodo / BayWa / Segen / GoodWe / SAJ 的 C&I 询价问卷（见 §7）。

**(c) 裁定：invented 且对 C&I 是错误的。**

- 结果对运营形态完全不敏感（见 §4）。
- knee 就是扫描上限，docstring 自己也承认。
- 缺了需量电费这一主要价值来源。
- 对 >100 MWh 的 RLM 用户来说，SLP 已经超出其适用范围，而这些用户手里本来就有实测数据。
- 缺少电网规范（4110）提示。

**(d) 行业正确版：见 §5.2。**

### 2.5 BOM

**(a) 引擎做什么**

- **核心件：** 逆变器、电池的精确物料行（`bom.py:226-313`）。
- **PV 组件：** 按组串方案的数量列出参考 Trina 组件，标为 `not_supplied`（`bom.py:316-340`）。
- **支架：** 一条阻断式的 resolution 行（`bom.py:342-372`）。
- **直流线缆：** 红黑两色 × 串数 × 15 m（`bom.py:29,374-405`）。
- **连接器：** 每串配 TS4 现场端 + Stäubli MC4 逆变器端（`bom.py:407-449`）。
- **gPV 熔断器 + 熔断器座：** 每串各 2 个（`bom.py:451-489`），但触发条件有 bug，见下。
- **电表 / CT / EMS：** 按品牌规则配（`bom.py:492-658`）。
- **配电盘工程服务：** 一条（`bom.py:664-680`）。
- **直流 SPD：** 可选（`bom.py:686-700`）。

**(b) 行业做法**

- **BayWa r.e. Solar-Planit**（批发商的免费规划工具）：
  - 覆盖整套 PV：支架（含结构计算）、组件、逆变器、储能、发电量、经济性、PDF 文档；
  - 2026-01 起还能导出单线图，用于电网报装。
- **对一家只做"储能+逆变器"的分销商来说，quick BOM 应当：**
  - 把自己范围内的东西列完整：电池模块/BMS/底座、逆变器、电表+CT、EMS/并联控制器、全屋备电时的切换盒、通讯；
  - 把组件、支架、AC 开关柜列为安装商负责的范围。
- 用户提到的"QuickCalc"：两次 Apify 检索都没找到同名的批发商工具（见 §7）。

**(c) 裁定**

- **结构：acceptable / 良好。** "精确物料 + 显式 blocker"的做法比通用套件更好。
- **熔断器 bug：wrong。**
  - `design.py:1798` 传的是 `n_parallel_strings=string_payload["strings_total"]`；
  - 但 `cables.py:129` 和 `cable-tables.json` 的规则是按"并联串数 ≥3"判断，应当按每个 MPPT 计；
  - 后果：每台超过 3 串的方案（例如 ET 15–30 kW 的 2×2、ET 80–100 kW 的 8×2、CHS2 的 4–6×2）都会多出熔断器和熔断器座；
  - 对比：Trina 组件允许的最大串联熔断器电流是 25 A，每个 MPPT 2 串时并不需要熔断器。
- **组件/支架行：** 不在 Linker 的供货范围内，应改为"由安装商负责"的信息行。
- **15 m / 20 m 线缆长度：** 是占位值，可以接受，但应作为输入或明示为假设。
- **`bom.py:191`：** 用 kWp ≥4.6 来推断相数，把直流 kWp 和交流 kVA 规则混在了一起（次要）。
- **备电接口：** 没有根据备电类型推导出相应的设备。

**(d) 行业正确版：见 §5 的输出部分。**

### 2.6 经济性

**(a) 引擎做什么**

- **储能价值：** `storage_value`（`econ.py:20-23`）。
- **现金流 `cashflow`**（`econ.py:41-181`），参数：
  - 期限 20 年，FIT 固定不变；
  - 零售电价每年 +2%；
  - 运维费 = 1% capex，并随通胀上调；
  - 发电量每年衰减 0.5%；
  - 折现率 4%；
  - 回本年限不折现；另算 LCOE。
- **基准 capex**（`econ.py:228-290`），按边际分档：
  - PV：1,500 / 1,250 / 1,050 / 850 €/kWp；
  - 电池：700 / 550 / 450 €/kWh。
- **零售电价只按年用电量选档**（`econ.py:309-324`；`tariffs.yaml:63-72`）：
  - <30 MWh：37 ct（家庭，含税）；
  - <160 MWh：25 ct（净价）；
  - 以上：16.7 ct（净价）。
- **FIT：** 按 7.70 / 6.66 / 5.44 分档混合；>100 kWp 时沿用最后一档（`econ.py:349-378`，`376-377`）。
- **"已验证"判断：** `valid_until: 2027-01-31`（`tariffs.yaml:19-24`；`econ.py:327-346`）。
- **PDF 输出：** 印出 payback、NPV20、LCOE（`report.py:36,192-194`）。

**(b) 行业与法规**

- **BNetzA（2026-10-09 抓取）：**
  - 2026-08-01 至 2026-12-31 投运的部分上网系统：7.70 / 6.66 / 5.44 ct；
  - 页面写明 EEG 2023 只适用到 2026-12-31，后续规则在议会审议中；
  - 100–1,000 kW 屋顶系统只有市场溢价（Marktprämie）路径，anzulegender Wert 为 5.84 ct，即必须直接售电，没有固定 FIT。
- **EEG 2027：**
  - 2026-07-29 内阁通过（enerix）；
  - 2026-09-07 形成 Drucksache 21/7867，计划 2027-01-01 生效。新系统默认直接售电；小系统可领过渡支付，门槛为：2027 年投运 <50 kW，2028 年 <25 kW，2029–30 年 <7 kW。过渡支付 = 6.2 ct − 1 ct = 5.2 ct，付到投运后第 36 个月末。<25 kW 直接售电有 1.5 ct 奖励，最长 48 个月；<100 kW 可选择无偿上网；存量系统继续适用 EEG 2023。（klamm/PresseBox，2026-10-04）
  - <100 kW 的新屋顶系统永久 50% 上网上限；
  - 2026-10-05 议会委员会听证会上，行业要求修改（solaranlage-ratgeber，2026-10-06）。
- **零售电价：** BDEW 家庭均价 2025 年为 39.6 ct（ee-news，2025-10）。
- **储能价格：**
  - ADAC（2026-08-21）：不含安装 250–450 €/kWh；10 kWh 一般 2,500–4,500 €（不含安装）；
  - energie-experten（2026）：5–10 kWh 约 440 €/kWh（含电力电子），>15 kWh <390 €/kWh。
- **PV 价格：** 1,200–1,800 €/kWp（pv-anlagen24，2026）。
- **安装商工具的做法：** 都显示经济性，但价格由用户自己设定。SolarEdge Designer 2026-09 版可在报告里分别看"仅电池 / 仅 PV / 整套"的财务数据，并支持需量电费。
- **HTW 质量标准：** 不得假设过高的电价涨幅，必须计入电池老化。

**(c) 裁定**

- **现金流 / NPV / LCOE 框架：standard。**
- **法规制度：**
  - 2027 年及以后投运的系统，如果草案通过：wrong；
  - 2026 年的系统现在就不完整：缺 60% 上限和 § 51 负电价规则；
  - `valid_until` 与 BNetzA 公布的窗口不一致。
- **>100 kWp 沿用 FIT：** 标注不正确。法律上应是 Marktprämie/直接售电；数值上接近（5.44 vs 5.84 减去直接售电服务费）只是巧合。
- **零售电价不分客户类型：wrong。** 小型 C&I 按 37 ct 含税价计算，比 25 ct 净价高 48%。
- **capex：** 没有来源，储能价格是 2023 年的水平，而且不是 Linker 自己的物料价格。
- **其他缺口：**
  - 没有电池老化或更换；
  - 14% 损失与每年 0.5% 衰减轻度重复；
  - P90 是自定义的。
- **对 B2B 分销商的定位问题：** 用分销商控制不了的基准 capex 去给终端客户算回本，碰到的是 Law 6（价格与承诺必须由 owner 决定）。这部分应改成可选模块，由安装商自己填参数。

**(d) 行业正确版：见 §5。**

### 2.7 输入

**行业会问、我们不问（或问了却丢弃）：**

- **改造类项目：** 既有逆变器的品牌/型号/AC kW、既有 PV kWp、投运年份/EEG 状态；据此决定 AC 耦合还是 DC 耦合（Solarwatt）。
  - 现状：引擎拒绝 `project_intent ≠ new_system` 和任何 `existing_equipment`（`inputs.py:67-74`）。
- **电池电压等级（HV/LV）：** 新装时可由逆变器推出；改造时是关键信息。
- **备电类型：**
  - Notstrom：常见为单相、手动、专用插座；
  - Ersatzstrom：全屋供电、自动切换，可做三相；
  - 另需关键负荷的 kW 与相数（strombauer）。
- **智能电表 / iMSys 与上网上限（60/50/0%）。**
- **电网接入：** 户内总保险容量或 Netzanschlussleistung（kVA）、相数（住宅 Planner 不强制填）。
- **多屋面**（例如东西向）。
- **热泵 / 电动车 / Wallbox 的用电量**（HTW FAQ）。
- **动态电价**（可选；HTW SPI 2026 有专门分析）。
- **C&I 专项：**
  - 15 分钟 Lastgang；
  - Leistungspreis（€/kW·a）、Arbeitspreis；
  - 年利用小时（2,500 h 两档）；
  - 峰值 kW、班次；
  - 变压器 / 接入容量；
  - 安装位置 / 空间 / 消防；
  - 关键负荷。

**我们问了、行业 quick calc 却用不上（因为我们没用）：**

- 已收集但从未进入计算：`operating_profile`、`facility_type`、`load_profile_state`、`peak_load_kw`、`grid_connection_kw`。
- 问了以后会把计算挡掉的：`target_power_kw`、`coupling_preference`（只要不是 unknown）、`constraints` 文本。
- 屋顶面积可以保留，作为 kWp 未知时的后备。
- `operating_profile` 枚举其实很有用：在没有 Lastgang 时，可以映射到 G1–G6 形状作为后备。前提是真的被使用。

---

## 3. 代码"声明"核对表

| 声明 | 位置 | 核对结果 | 状态 |
|---|---|---|---|
| 14% 是 PVGIS PVcalc 自己的默认值 | `pv_yield.py:34-39` | PVGIS 手册：网页版默认 14%（含逆变器与寿命平均衰减）；API 中该参数必填 | ✓（但 14% 含衰减，与 `econ` 的 0.5%/年重复） |
| Huld 是 PVGIS 自用的功率模型 | `pv_yield.py:22-25` | PVGIS 手册引用 Huld et al. | ✓ |
| `gamma_pdc_pct_per_c` 是在用的默认值 | `pv_yield.py:40-43,179,357` | 从未使用 | ✗ 死参数 |
| P50/P90 采用"PVsyst 可融资方法" | `pv_yield.py:76-95` | 不确定度预算为自定义；未找到依据 | ✗ invented |
| 35°/180° 是德国住宅默认 | `design.py:36-39` | HTW 计算器同样假设 35° 朝南 | ✓ |
| 5.0 m²/kWp 是常用经验值 | `design.py:9-10,34` | HTW：每 kW 需 5–10 m² | △ 取下限，偏乐观 |
| DC/AC 目标 1.15 | `design.py:11,35` | 行业典型 1.1–1.4；厂商上限 1.3–3.0× | △ 可接受，但非按厂商设定 |
| knee 是"HTW 式边际递减"读法 | `design.py:12-13,1009-1030` | HTW 方法是三条上限规则；90% 增益规则随扫描上限漂移（docstring 自认） | ✗ 误标 + invented |
| "HTW-Berlin-style 曲线" | `storage.py:11-12,26-29` | HTW 用分钟级 VDI 4655 / 实测曲线，不用 SLP | ✗ |
| RTE 0.92 是披露的规划假设 | `design.py:41` | HTW 计算器取 AC-AC 83.9% | △ 偏乐观 |
| 可用容量 0.9（DoD） | `design.py:40` | 仅在 datasheet 缺数据时兜底；HTW 另扣 90% 老化可用率 | △ |
| 回本期限 20 年 = 展示期限 | `design.py:42-47` | 电池质保常见 10 年；没有更换成本 | ✗ 过宽 |
| `MAX_CI_UNITS = 8` | `design.py:116` | GoodWe SEC3000 最多 60 台；SAJ 为 2–10 台 | ✗ unsourced |
| C&I 扫描上限 0.4×日用电，封顶 300 kWh | `design.py:1368-1372` | 无来源 | ✗ invented |
| 电池电压 ±20% 容差 | `design.py:849,884` | datasheet 给的电压窗口是硬限 | ✗ invented（有标记） |
| 串熔断器"自第 3 个并联串起" | `cables.py:118-135`；`cable-tables.json` | 规则文本正确，但调用方传入的是总串数 | ✗ bug |
| NEC 1.25 系数用于逆变器 MPPT 的 Isc 上限 | `strings.py:31-34,219` | 这是美标线缆/保护器件的选型系数；用作逆变器限值偏保守 | △ 未证实 |
| FIT 固定 20 年（EEG 2023 § 48） | `econ.py:65-71` | 对 2026-12-31 及以前投运成立；对 2027+ 草案不成立；还有 § 51 负电价规则 | △ / ✗ |
| >100 kWp 沿用最后一档 FIT | `econ.py:376-377` | 法律上是 Marktprämie（AW 5.84 ct）+ 直接售电 | ✗ 误标 |
| `valid_until: 2027-01-31` | `tariffs.yaml:21` | BNetzA：窗口至 2026-12-31，EEG 2023 适用到当日 | ✗ |
| 零售电价分档（家庭含税 / 企业不含税，"不可混用"） | `tariffs.yaml:55-72`；`econ.py:309-324` | 选档只看用电量，不看客户类型 → 两者被混用 | ✗ |
| 家庭电价 37 ct（BDEW 2026） | `tariffs.yaml:66` | BDEW 2025 均价 39.6 ct；2026 值未核实 | △ |
| 电池 capex"参考 HTW Stromspeicher-Inspektion 价格序列" | `econ.py:226-227,234-238` | SPI 是效率测试，不是价格序列；2026 市价 250–450 €/kWh（不含安装） | ✗ unsourced / 过时 |
| 折现 4%"参考 HTW PV-Battery-Tool" | `econ.py:106-108` | 未找到依据 | ? |
| H25 正在取代 H0 | `storage.py:16-23` | BDEW 2025 版曲线确实存在 | ✓（但与是否适用无关） |
| 引擎声明使用 SLP | `l10n.py:39` | 有披露 | ✓ 披露良好；但披露不能修正方法 |

---

## 4. 复现实验（chain-tip 代码，Munich TMY fixture，比发电量 1,112 kWh/kWp，H25，小时分辨率，引擎原参数）

### 4.1 住宅：推荐量 vs HTW 上限

| kWp / 年用电 | 引擎推荐（名义 → 可用） | HTW 上限（可用） | 倍数 | 引擎回本年限 | 自给率 无储能 → 推荐储能 |
|---|---|---|---|---|---|
| 5 / 3,000 | 10 → 9.0 | 4.5 | 2.0× | 18.1 | 42% → 87% |
| 6 / 2,500 | 7.5 → 6.75 | 3.75 | 1.8× | 15.6 | 44% → 91% |
| 8 / 4,000 | 10 → 9.0 | 6.0 | 1.5× | 13.8 | 43% → 87% |
| 10 / 4,000 | 10 → 9.0 | 6.0 | 1.5× | 13.3 | 44% → 90% |
| 10 / 5,000 | 12.5 → 11.25 | 7.5 | 1.5× | 13.2 | 43% → 87% |
| 12 / 6,000 | 12.5 → 11.25 | 9.0 | 1.25× | 11.4 | 43% → 86% |
| 15 / 8,000 | 15 → 13.5 | 12.0 | 1.13× | 10.3 | 43% → 83% |
| 10 / 10,000 | 20 → 18.0 | 15.0 | 1.2× | 12.3 | 38% → 73% |

- 在 8 个案例里，20 年回本门槛没有一次生效。
- 实际设计还会把推荐量映射到一个在 0.6–1.8× 带宽内的真实物料，但驱动定容的目标值就是上表中的推荐量。

### 4.2 HTW 实测锚点（5,000 kWh / 10 kW / 可用 10 kWh；实测平均自给率 77%）

| PV 序列 | 引擎电池假设（0.9 / 0.92 / 0.5C） | HTW 电池假设（90% 可用 / 83.9% / 1C） | 无储能 |
|---|---|---|---|
| Munich TMY | 86.3% | 84.1% | 43.0% |
| 缩放到 HTW 的 1,024 kWh/kWp | 85.1% | 82.9% | 42.5% |

- 结论：剩余约 6 个百分点的偏差来自 SLP 负荷模型（外加小时分辨率），而不是电池参数。

### 4.3 C&I：结果对负荷形状不敏感

| 年用电 / PV | 负荷曲线 | 小时峰值 | 扫描上限 | knee | 推荐 |
|---|---|---|---|---|---|
| 100 MWh / 100 kWp | G25 / G1 / G3 / G0 | 27 / 47 / 15 / 23 kW | 100 | 90（=扫描上限） | 90 / 90 / 90 / 90 kWh |
| 250 MWh / 150 kWp | G25 / G1 / G3 / G0 | 67 / 116 / 38 / 59 kW | 275 | 200–250 | 0 / 0 / 0 / 0 |

- 峰值差了 3 倍，推荐结果完全一样。原因有三：
  - 方法里没有功率（kW）这个维度；
  - 没有需量电费；
  - knee 被扫描上限截断。

---

## 5. 总裁定与行业正确的 quick calc 规格

**总裁定：**
- 住宅："methods need rework"；
- C&I："fundamentally different tool needed"（在此之前降级为询价流程）。

**保留：**
- 页码可溯的组件库；
- 兼容性闸门（`_compatibility_decision` / contract）；
- 组串电压/电流校验；
- 精确物料 + blocker 的 BOM 结构；
- PV 物理链（或直接改调 PVGIS PVcalc）；
- 假设与未满足约束的披露机制。

**替换 / 修正（按优先级）：**

- **P0 — 现在就会产出错误结果：**
  1. 住宅储能定容改用 HTW 三条规则作为硬上限；删除 90%-knee，删除 max_autarky = 20 kWh。
  2. 负荷模型改为实测曲线（HTW 免费的 74 户 1 秒分辨率数据集，或 VDI 4655），分辨率 ≤15 分钟；或改用 HTW 式预计算查表。输出给区间，不给单一的乐观值。
  3. 经济性改为按投运日期切换法规制度：
     - EEG 2023 至 2026-12-31；2027 起按草案（随立法进展更新）；
     - 现在就加上 60% 上限与负电价规则；
     - 零售电价区分客户类型（家庭含税 / 企业净价）；
     - >100 kWp 走 Marktprämie/直接售电；
     - 计入电池老化与更换；
     - 价格改由安装商输入，或使用 Linker 物料价 + 人工；
     - 删除 P90。
  4. 单相 ≤4.6 kVA；默认三相。
  5. 串熔断器改按"每个 MPPT 的并联串数"判断（修 bug）。
  6. C&I：在没有 Lastgang 前，停止把基于 G25 的定容当作设计输出。
- **P1：**
  7. 备电预留（不重复计数）；增加 Notstrom / Ersatzstrom 输入。
  8. 改造路径：既有逆变器信息、AC 耦合方案。
  9. 多屋面；使用安装商的实际组件；DC/AC 按厂商上限；产量里计入削顶与上网上限。
  10. C&I 提示：>30 kVA 须 NA-Schutz、>135 kW 适用 VDE-AR-N 4110；`MAX_CI_UNITS` 改为读控制器 datasheet。
- **P2 — 清理：**
  - 删除未使用的 `gamma` 参数；
  - 修正损失瀑布图的标签；
  - 修正 `valid_until`；
  - 处理 14% 与年衰减的重复；
  - 处理 TMY 与地形地平线的重复计入；
  - BOM 中 kWp ≥4.6 推相数的逻辑。

### 5.1 住宅 quick calc（德国 EFH/ZFH，≤30 kWp，≤约 15 MWh）

**输入**

- **必填：**
  - 邮编；
  - 年用电量（不知道时按人数用 BDEW 表：1 人 1,900 / 2 人 2,900 / 3 人 3,700 / 4 人 4,100 / 5 人 5,100 kWh）；
  - 项目类型：新建 PV+储能 / 存量 PV 加储能 / 换逆变器；
  - PV：新建时给各屋面的 kWp、倾角、方位；改造时给既有 kWp、既有逆变器型号与 AC kW、投运年份；
  - 电网：三相或单相（默认三相）。
- **可选：**
  - 热泵 kWh/a；电动车 kWh/a 或 km/a；
  - 备电：无 / Notstrom（单相插座）/ Ersatzstrom（全屋、自动、单相或三相），以及关键负荷 kW × h；
  - 智能电表与上网上限：60 / 50 / 0%；
  - 计划投运月份；
  - 15 分钟智能电表数据（上传）；
  - 安装商实际组件；
  - 安装商价格（如需经济性）。

**规则**

1. **发电量：** 每个屋面跑 PVGIS PVcalc（loss 14%），逐时序列用于削顶与上网上限计算。
2. **储能可用容量：**
   - PV < 0.5 kWp/MWh·a 时：不建议配储能；
   - 否则：上限 = min(1.5 × kWp, 1.5 × 家庭 MWh·a)；
   - 在此之上：加上备电预留（关键 kW × h ÷ η）；热泵/电动车的影响用仿真评估，不放大上限。
   - 选取 ≤ 上限的最近可下单物料；如果物料的容量档位太粗，取上一档并标注。
3. **KPI：** 用实测曲线集（≤15 分钟）仿真，或 HTW 式查表；电池参数用 HTW 默认值（90% 可用、83.9% RTE），有产品 SPI/待机数据时用产品数据。输出 P25–P75 区间。
4. **逆变器：**
   - AC ≥ max(备电 kW, 电池功率需求)；
   - DC/AC ≤ 厂商最大 PV 输入，常规 1.0–1.4；
   - 单相 ≤4.6 kVA；
   - 按屋面、按 MPPT 排组串。
5. **兼容性：** 沿用现有闸门；电压窗口不加容差。

**输出**

- **套件：** 逆变器 ×n、电池模块/BMS/底座、电表+CT、备电接口、通讯；每一项附兼容性引用。
- **能量：** 年/月发电量、比发电量；有/无储能的自给率与自用率区间；年循环次数；说明是哪条上限在起约束作用。
- **合规标记：** 4.6 kVA、上网上限、DC/AC、组串有效性。
- **经济性（可选，安装商填参数）：** 按投运日期所适用的补贴制度计算的年节省、回本区间，并分别给出"仅电池 / 整套"的数据。
- **安装商自担清单：** 组件、支架、线缆长度、AC 保护、NA-Schutz。

### 5.2 C&I quick calc（30 kW–约 1 MW，低压/中压接入）

**输入**

- **必填：**
  - 上一整年的 15 分钟 Lastgang（RLM 数据，CSV）；
  - 电价：Arbeitspreis（净价）、Leistungspreis（€/kW·a）、年利用小时档（<2,500 h / ≥2,500 h）；
  - 接入：Netzanschlussleistung（kVA），以及低压还是中压；
  - PV：既有或计划的 kWp 与屋面、补贴模式、上网上限；
  - 目标：削峰目标 kW / 自用 / 关键负荷备电（kW × h）/ 动态电价套利；
  - 安装条件：室内/室外、空间、消防。
- **没有 Lastgang 时（SLP 用户，<100 MWh）：**
  - 改填年 kWh + 运营形态（映射到 G1–G6 或班次模型）+ 账单上的峰值 kW；
  - 输出明确标注为"仅为指示性区间"，并要求补充 Lastgang；或转为询价。

**规则**

1. **削峰：**
   - 从净负荷（扣除同时刻的 PV）得到负荷持续曲线；
   - 对每个候选封顶值 P_cap：所需功率 = max(P − P_cap)；所需能量 = 单个峰事件在 P_cap 以上的最大面积 ÷（可用率 × η）；
   - 校验两次峰值之间的回充可行性；
   - 选择使"需量电费节省 − 成本"最大的 P_cap。
2. **自用 + 削峰联合调度：** 在 15 分钟序列上，用实际物料的 kW/kWh 进行调度。
3. **硬件：**
   - 按 kW 选 PCS 或混合逆变器，按 kWh 选电池柜；
   - 并联台数以控制器 datasheet 为上限；
   - 兼容性闸门；
   - 按接入点电流选 EMS 与 CT 变比；
   - 合规提示：>30 kVA 须 NA-Schutz；>135 kW 适用 4110。
4. **经济性：** 需量电费节省 + 电量节省 − 安装商 capex；给出对 Leistungspreis 和 P_cap 的敏感性。

**输出**

- 推荐的 kW/kWh 组合；
- 峰值下降多少 kW；
- 分项年节省（需量 / 电量）；
- 年循环次数；
- Linker 物料清单（电池柜、PCS/混合逆变器、EMS、CT）；
- 待办工程项：电网审批、消防、基础。

---

## 6. 来源（均经 Apify 抓取，2026-10-09）

**HTW Berlin**
- Orth/Weniger/Meissner，《Empfehlungen zur Auslegung von Solarstromspeichern》，Sonnenenergie 02/2022 — https://solar.htw-berlin.de/publikationen/auslegung-von-solarstromspeichern/
- 独立性计算器 FAQ（方法、假设、适用范围）— https://solar.htw-berlin.de/faq-unabhaengigkeitsrechner/；计算器页 — https://solar.htw-berlin.de/rechner/unabhaengigkeitsrechner/
- Zoll/Weniger，在线计算器质量（实测 77% vs 计算器 76–100%），40. PV-Symposium 03/2025 — https://solar.htw-berlin.de/publikationen/qualitaet-von-online-solarrechnern/
- Stromspeicher-Inspektion 2026 — https://solar.htw-berlin.de/studien/stromspeicher-inspektion-2026/
- 74 户 1 秒分辨率负荷数据集 — https://solar.htw-berlin.de/elektrische-lastprofile-fuer-wohngebaeude/

**计算器质量与 SLP**
- nextpit，2025-07-01（HTW/DGS/SFV 质量标准）— https://www.nextpit.de/ratgeber/online-rechner-fuer-pv-anlagen-so-findest-du-serioese-vorhersagen
- SMA 博客《Eigenverbrauch richtig abschätzen》（2012）— https://www.sma-sunny.com/eigenverbrauch-richtig-abschatzen/
- Wikipedia《Standardlastprofil》（G0–G6、2025 版曲线、≤100 MWh）— https://de.wikipedia.org/wiki/Standardlastprofil

**规划工具**
- SolarEdge Designer release notes（2026-09 / 04 / 02）— https://marketing.solaredge.com/rn_designer
- BayWa r.e. Solar-Planit — https://solar-distribution.baywa-re.lu/de/services/kostenloses-auslegungstool-solar-planit；photovoltaik.eu 2026-01-19 — https://www.photovoltaik.eu/planung/solar-planit-neue-funktionen-fuer-eine-effizientere-planung
- PV*SOL premium — https://valentin-software.com/produkte/pvsol-premium/；论坛（负荷曲线导入）— https://forum.valentin-software.com/topic/7715-batteriespeicher-berechnen/

**PVGIS**
- 用户手册 — https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en
- API — https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en

**补贴与 EEG 2027**
- BNetzA EEG-Förderung und -Fördersätze — https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html
- ADAC 上网电价 2026/2027 — https://www.adac.de/rund-ums-haus/energie/spartipps/einspeiseverguetung-pv-anlagen/
- klamm.de / PresseBox 2026-10-04（Drucksache 21/7867 条文）— https://www.klamm.de/news/einspeiseverguetung-soll-fuer-neue-solaranlagen-ab-2027-enden-der-bundestag-beraet-einen-entwurf-mit-62-cent-4N1312288.html
- solaranlage-ratgeber 2026-10-06（10-05 听证会）— https://www.solaranlage-ratgeber.de/eeg-novelle-2027-anhoerung-kleine-pv-anlagen
- enerix 2026-07-29（内阁决定）— https://www.enerix.de/blog/kabinett-beschliesst-eeg-2027/

**Solarspitzengesetz**
- enyo 2026-10-01 — https://enyo-energy.de/magazin/solarspitzengesetz-60-prozent-regel
- ista 2026-01-27 — https://www.ista.com/de/blog/nachhaltigkeit/solarspitzengesetz-und-photovoltaik-anlagen-was-gilt-jetzt/

**电网规范与逆变器定型**
- VDE-AR-N 4105（4.6 kVA、30 kVA、135 kW、2026-03 版）— https://www.energie-experten.org/erneuerbare-energien/photovoltaik/planung/vde-ar-n-4105；https://solarzubau.de/wiki/vde-ar-n-4105/
- DC/AC 实践 — https://www.energie-experten.org/erneuerbare-energien/photovoltaik/wechselrichter/auslegung

**C&I**
- Intilion — https://intilion.com/blog/stromspeicher-fur-gewerbe-und-industrie/
- Voltfang 2026-02-18 — https://voltfang.de/2026/02/18/wie-gross-muss-eine-pv-anlage-fuer-einen-gewerbespeicher-sein/
- stromfee — https://www.stromfee.me/post/gewerbespeicher-lohnt-sich-2026
- furoenergy 2025-07-03 — https://www.furoenergy.com/blog/eigenverbrauchsoptimierung-lastspitzenkappung
- akkusmart — https://blog.akkusmart.de/lastspitzenkappung-im-betrieb-praxisleitfaden-mit-roi

**价格与电价**
- ADAC 储能 2026-08-21 — https://www.adac.de/rund-ums-haus/energie/versorgung/pv-stromspeicher/
- energie-experten 储能价格 2026 — https://www.energie-experten.org/erneuerbare-energien/photovoltaik/stromspeicher/preise
- pv-anlagen24 PV 成本 2026 — https://pv-anlagen24.com/magazin/pv-anlage-kosten-2026-preise
- BDEW 电价分析 2025-10（ee-news）— https://ee-news.ch/a/bdew-strompreisanalyse-oktober-2025-zeigt-aktuelle-entwicklung-der-strompreise-in-deutschland

**改造与备电**
- Solarwatt 改造 — https://www.solarwatt.de/ratgeber/stromspeicher-nachruesten
- strombauer 2024-11-29（Notstrom vs Ersatzstrom）— https://strombauer.com/blog/notstrom-vs-ersatzstrom/

**并联**
- GoodWe SEC3000 — https://en.goodwe.com/sec3000-smart-energy-controller

**内部证据**
- `knowledge/components-db/*.json`（厂商 datasheet，带页码）
- `knowledge/materials/manual-decisions.json`（Trina TSM-460NEG9R.28 datasheet 值）

---

## 7. 没找到 / 没验证（不当作结论使用）

- **BayWa 储能尺寸图：** 没找到。Solar-Planit 页面只说"推荐合适的逆变器和储能"，没有公开方法。
- **"QuickCalc"：** 两次 Apify 检索都没找到同名的批发商工具，只找到一个无关的通用计算器网站。
- **Memodo / BayWa / Segen / GoodWe / SAJ 的 C&I 询价问卷：** 没找到。C&I 的输入要求取自 Intilion、Voltfang 等储能厂商的说明。
- **Sunny Design 当前版本的储能推荐方法：** 只找到 SMA 2012 年的博客。
- **PVGIS PVcalc ±5% 验证：** 本次没有重跑（需要联网调用 PVGIS）。
- **econ 中 4% 折现率"来自 HTW 工具默认值"、37 ct 是"BDEW 2026"均价：** 未核实。
- **EEG 2027：** 仍是草案。门槛与费率以 Drucksache 21/7867 当前文本为准，听证会后可能修改；不同二手来源对"<25 kW"与"<50 kW（2027）"的说法不一致，本报告按引用条文的那一篇为准。
