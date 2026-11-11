# 能量时序域生产执行证据（Y 线，2026-11-11）

只读评估。生产侧未做任何写入、重启或配置变更：全部读回走只读 SQLite
（`?mode=ro`）与 blob 文件读取，临时脚本写在 `/tmp` 并在收尾删除。

评估对象：`548-energy-job.md`、`548-energy-workspace.md`、`548-energy-replay.md`、
`548-time-series.md`、`548-managed-energy-worker.md` 规格族，以及
`548-domain-gap-matrix.md` 第 3 行"PV 发电与能量时序 / 可发布（能力层）"这一评级。

## 结论先行

**该域在生产上真实执行过 10 次，全部成功；规格的关键承诺在真实 witness 上逐项成立。
但"可发布"这个评级要加限定：证据是执行器级的，不是客户数据级的。**

| 判据 | 结果 |
| --- | --- |
| 生产执行次数 | **10**（`single_ac_energy_replay_v1`） |
| succeeded / failed | **10 / 0**，`attempt=1`（上限 2），无 `error_sha256` |
| 每 run verification 检查 | **92 项，全部 passed**；最大 `worst_violation` 3.37e-13，allowance 1.01e-07 |
| 时序轴不变量 | 10/10 通过：0 gap、0 overlap、0 非正时长、0 naive 时间戳、0 非 ISO |
| 能量守恒闭合 | 10/10 闭合到 ≤2.4e-12 kWh |
| 预算使用 | `max_intervals=100000`，**实际最高 8.76%** |
| 2026-11-05 之后的执行 | **1/10**（`fc3304d4b6`，11-06 15:23 UTC） |
| 真实客户电表负载 | **0 例**——输入全是 Linker 自有的合成验收夹具 |

因此：**能力层"可发布"维持，但它证明的是执行器能正确算，不证明真实客户负载下算过。**
详见 §6 判定与 §7 建议。

---

## 1. 统计口径：为什么 D 线和 W 线都看不见这个域

这是本次最重要的方法发现，也是两个线共同盲区的根因。

`548-domain-gap-matrix.md` 第 3 行写"direct-beam/geometric-pv 无生产执行"，W 线已在
`direct-beam-production-assessment.md` §2 用 `manifest.context.models.task` 推翻。
但**能量域的那张表里一个都没有**——W 线列的 8 个 task 中不存在能量任务。

原因不是"没跑过"，是**键名不同**：

| 内核 | 标识位置 | 值 | 生产 run 数 |
| --- | --- | --- | ---: |
| `energy_kernel.py:41-50` | `models["replay"]` | `single_ac_energy_replay_v1` | **10** |
| `plant_energy_kernel.py:124-132` | `models["replay"]` | `plant_ac_energy_replay_v1` | 0 |
| `dc_energy_kernel.py:28-37` | `models["replay"]` | `shared_dc_energy_replay_v1` | 0 |

这三个内核都**没有** `models["task"]` 键。按 `models.task` 分组时，它们整类落到
`None`。生产 143 个 run 的实测分布：

| `models.task` | run 数 |
| --- | ---: |
| `planning_report_v1` | 50 |
| `qualify_woo_equipment_v1` | 35 |
| `search_woo_equipment_v1` | 28 |
| **`None`（全部是能量域，`models.replay` 有值）** | **10** |
| `acquire_pvgis_tmy_weather_v1` | 9 |
| `prepare_geometric_pv_reference_v1` | 7 |
| `prepare_roof_pv_reference_v1` | 2 |
| `prepare_direct_beam_visibility_v1` | 1 |
| `prepare_pvgis_roof_ac_reference_v1` | 1 |

存在 `replay` 键的 run = 10，存在 `task` 键的 run = 133，两者互斥，无一例外。

**统计口径结论**：任何"本域有无生产执行"的判断必须解 `manifest.context.models`
的**全字段**，不能只看 `models.task`，也不看 `jobs.kind`（生产该列只有 `evaluate`、
`render_report` 等执行类型，与任务身份无关）。这一条同时更正 D 线与 W 线的口径。

---

## 2. 生产执行史（10 个 run 全量）

按 `jobs` 表 `created_at` 排序。全部 `worker=production-linker-planner`。

| # | run | 项目 | rev | 时间 (UTC) | 区间数 | 墙钟 | 检查 | runtime |
| ---: | --- | --- | ---: | --- | ---: | ---: | --- | --- |
| 1 | `8b366d7cbe` | `181228648034` | 7 | 10-27 08:23 | 2 | 0.47 s | 92 ✓ | `7a52e12c133c` |
| 2 | `f32e226aa7` | `181228648034` | 12 | 10-27 20:11 | 2 | 20.11 s | 92 ✓ | `8beaa6186e0c` |
| 3 | `553b1fbb4f` | `181228648034` | 15 | 10-29 06:59 | 2 | 22.43 s | 92 ✓ | `7c91bc9a2295` |
| 4 | `a796be35b9` | `51d074af0cee` | 3 | 10-29 07:34 | 2 | 6.57 s | 92 ✓ | `7c91bc9a2295` |
| 5 | `7f04efe981` | `88e747ebda38` | 11 | 10-30 12:59 | 8760 | 17.58 s | 92 ✓ | `35ea87dab72d` |
| 6 | `6576e35848` | `88e747ebda38` | 12 | 10-30 13:22 | 8760 | 14.93 s | 92 ✓ | `35ea87dab72d` |
| 7 | `e768842d86` | `acb2ee16d1b2` | 11 | 11-01 22:32 | 8760 | 27.97 s | 92 ✓ | `d537a203dc76` |
| 8 | `ecb5b44ead` | `acb2ee16d1b2` | 14 | 11-01 22:42 | 8760 | 26.69 s | 92 ✓ | `d537a203dc76` |
| 9 | `52796585d1` | `acb2ee16d1b2` | 17 | 11-02 02:59 | 8760 | 25.36 s | 92 ✓ | `3388306032b0` |
| 10 | `fc3304d4b6` | `517eb7457dcd` | 14 | **11-06 15:23** | 8760 | 18.88 s | 92 ✓ | `0662df45b37d` |

- 墙钟：n=10，min 0.47 s，max 27.97 s，**均值 18.10 s**。
- 7 个不同 `code_sha256`（`context.code_sha256` 与 `assets.runtime_bundle` 同值），
  全部 `python 3.12.3` / `Linux-6.8.0-147-generic-x86_64-with-glibc2.39` / `sqlite 3.45.1`。
- `parameters` 每次都真实存在且完整：`{"kind": "single_ac_energy_replay_v1",
  "max_intervals": 100000, "product_policy": "current_woo_profile_and_selected_equipment_v2",
  "tolerance": {"absolute_kw": 1e-07, "absolute_kwh": 1e-07, "relative": 1e-09}}`。
- 预算使用：2 区间的 run 用 0.002%，8760 区间的 run 用 **8.76%**。
  与 direct-beam/geometric 那条"`module_steps` 已用 95.6%"的通道对比，本域预算**从未被逼近**。

### 2.1 失败复核（独立于 W 线结论）

生产共 6 个 `failed` job，`attempt` 全为 1。逐个解 `models` 确认任务身份：

| job | run | 任务 | 本域？ |
| --- | --- | --- | --- |
| `312279488f` | `128017d6b0` | `acquire_pvgis_tmy_weather_v1` | 否 |
| `889496b794` | `4f98d0db20` | `acquire_pvgis_tmy_weather_v1` | 否 |
| `d9e832ded9` | `42fe518196` | `acquire_pvgis_tmy_weather_v1` | 否 |
| `4ae5341f09` | `d41eb193eb` | `planning_report_v1` | 否 |
| `fa8581f38b` | `828c288e03` | `planning_report_v1` | 否 |
| `e227ca32cd` | `19482b07d6` | `planning_report_v1` | 否 |

**本域 0 失败**，与 W 线记录一致，本次独立复核通过。

### 2.2 项目归属

5 个不同项目承载这 10 个 run：

| 项目 | owner | 标题 | run 数 |
| --- | --- | --- | ---: |
| `181228648034` | `user:wp:1:user:1` | Linker production acceptance · owned synthetic project | 3 |
| `acb2ee16d1b2` | `guest:wp:1:guest:201fc6a5…` | Linker acceptance 844 · PV and grid report | 3 |
| `88e747ebda38` | `user:wp:1:user:46` | Production Roof Acceptance 1946 | 2 |
| `517eb7457dcd` | `user:wp:1:user:53` | Residential · 10 kWp · 80331 | 1 |
| `51d074af0cee` | `user:wp:1:user:1` | Production geometric report · owned synthetic export | 1 |

4 个是**已认证账号**（`user:1`/`user:46`/`user:53`），1 个是前端访客匿名身份。
从标题可读：这些是**我们自己的验收项目**，不是外部客户项目。走的是真实客户链路
（WordPress → planner HTTP → durable worker → CAS），但数据不是客户的。

---

## 3. 抽样逐项核对（3 个 run × 规格条款）

抽 3 个覆盖面最不同的 run：最小合成例、整年含储能、**唯一落在 11-05 之后的那次**。

### 3.1 样本 A：`8b366d7cbe` — 全库唯一跨 DST 的 run

2026-10-27 08:23 UTC，项目 `181228648034` rev 7，2 区间，0.47 s。
输入全为 `origin=synthetic`（明确声明），PV 也是合成的（`pv_available_ac.synthetic`）。

| 规格条款 | 承诺 | 生产 witness 实测 | 判定 |
| --- | --- | --- | --- |
| `548-time-series.md` §1 | 区间显式、半开、UTC-aware、正时长、有序不重叠 | `2024-03-30T23:00Z` → `2024-03-31T00:00Z` → `2024-03-31T01:00Z`；0 gap / 0 overlap / 0 非正 / 0 naive | **成立** |
| §4 | 春季不存在的本地时刻必须拒绝；显式偏移决定真实瞬时 | 时区 `Europe/Paris`。区间 2 的 UTC 跨度 1 h，本地映射 `01:00+01:00 → 03:00+02:00`（本地 2 h）。DST 跳变点 UTC `01:00`，正好切在区间边界 | **成立**（这是全库唯一能证明该条的 run） |
| §2 | 区间平均 kW 与区间能量 kWh 必须显式区分 | `value_kind: interval_average_kw`，`within_interval_assumption: constant_mean_no_new_observations` | **成立** |
| `548-energy-job.md` §11 | 执行成功与场景约束分离 | `scenario_constraint_status: satisfied` 与 `verification.passed: true` 是两个独立字段 | **成立** |
| §5 | 电池参数是显式场景值，无隐藏默认 | `model.usable_window_kwh: 0.0`、`charge_ac_kw: 0.0`、`eta 1.0`——零值被**显式声明**，不是缺省 | **成立** |
| `548-energy-replay.md` §12 | 自给率 = (PV 直供负载 + PV 来源电池供负载)/总负载 | PV 直供 2.0 / 总负载 4.0 → 0.5；上报 `solar_autarky.value = 0.5`，**delta = 0** | **成立** |

### 3.2 样本 B：`7f04efe981` — 整年 8760 区间 + 储能双向转换

2026-10-30 12:59 UTC，项目 `88e747ebda38` rev 11，8760 区间，17.58 s，
trace 10 463.7 KB。2025 全年（非闰年，8760 小时），负载与辅助全合成，
PV 为 JRC PVGIS TMY（`origin=modelled`，真实模型数据）。

| 规格条款 | 承诺 | 生产 witness 实测 | 判定 |
| --- | --- | --- | --- |
| `548-time-series.md` §6 | 不用硬编码 24/8760，真实日历边界 | 8760 区间，总跨度**正好 8760.0 h**，起始 `2025-01-01T00:00Z` | **成立** |
| §7 | 重采样按区间均值实际重叠积分，覆盖缺失显式失败 | `transformations[0].method = energy_preserving_overlap_of_interval_means`，`input/output_max_interval_seconds` 均 3600 | **成立** |
| §8 | 细化是分段常数重建，非新观测；必须保留重建标记 | `pv_available_ac.reconstructed_means: true`，`effective_max_interval_seconds: 3600`，且 `temporal_policy.energy_preservation_claim: false`（**不虚报能量守恒**） | **成立** |
| `548-energy-job.md` §7 | 运行身份冻结，历史结果不重算 | result 内 `runtime_sha256` / `manifest_sha256` / `input_sha256` / `project_id` / `revision` 与 manifest 逐项相等（10/10 run）；trace 内 `manifest_sha256` 与 run manifest 相等（10/10） | **成立** |
| `548-energy-replay.md` §11 | 充电损耗 = 输入 × (1−η) | PV 充电 5572.848 × (1−0.95) = 278.642411617；上报 `charge_conversion_loss_kwh` 同值，**delta = 0** | **成立** |
| §5 | 静置损耗 `E·(1−e^(−rate·dt))` 先于内部辅助 | 该 run `standing_loss_rate_per_hour = 0.0`（显式零），`standing_loss_kwh = 0.0` | **成立**（零值场景） |
| §12 | 输入侧 PV 自用率 = (直供 + 直供辅助 + 充电输入)/限电后发电 | (8225.418 + 0 + 5572.848)/13803.275 = 0.999637149530；上报同值，**delta = 0** | **成立** |

### 3.3 样本 C：`fc3304d4b6` — 唯一 11-05 之后，且功能面最全

2026-11-06 15:23 UTC，项目 `517eb7457dcd` rev 14（`Residential · 10 kWp · 80331`，
认证用户 `user:53`），8760 区间，18.88 s，trace 10 851.6 KB。
这是 10 个 run 中唯一同时具备：非零辅助负载、非零静置损耗、双向转换损耗、
真实出口电量、非零储能余量的样本。

| 指标 | 值 |
| --- | ---: |
| 可用 PV / 总负载 / 系统辅助 | 9 515.578 / 3 777.385 / 175.200 kWh |
| 电网进口 / 出口 | 239.631 / 5 581.351 kWh |
| 自给率 `solar_autarky` | 0.940126471422 |
| PV 输入侧自用率 | 0.413451181992 |
| 充电 / 放电 / 静置损耗 | 83.358 / 77.612 / 55.057 kWh |
| 储能参数 | 10 kWh / 5 kW / η 0.96 双向 / 静置 0.001 h⁻¹ |

| 规格条款 | 承诺 | 实测 | 判定 |
| --- | --- | --- | --- |
| `548-energy-replay.md` §7 | 无电池对外出口路径 | trace 全部 flow 无 battery→export 字段；`model.battery_export: excluded_from_this_model` | **成立** |
| §7 | 分配优先级：PV 先负载再辅助 | 系统辅助 175.200 kWh 分三源记账：PV 68.752 + 电网 13.465 + 电池放电 92.982，`unserved_aux_kw` 全程 0；`internal_aux_supplied_kwh = 0` 是**电池内部**辅助（该场景显式 0），两者是不同身份 | **成立** |
| §9 | 自耗控制器是本地可执行基线，不承诺未来峰值可行 | `controller: self_consumption_with_reserve_v1`；无未来可行性声明字段 | **成立** |
| §12 | 零分母返回具名原因，不返回 NaN/虚假 0 | 全部比值字段为 `{"value": …, "undefined_reason": null}` 结构；`gross_load_undefined_reason: null` 且 `load_measurement_scope: gross_load` | **成立** |
| `548-energy-job.md` §11 | 设备与国家评估显式未评估 | `equipment_release.status: not_assessed`、`country_assessment.status: not_assessed`，各带具名 reason | **成立** |
| `548-managed-energy-worker.md` | 执行身份与限额随版本响应发布 | manifest `context` 含 `code_sha256` + `models` + `parameters(max_intervals, tolerance)` 全量 | **成立** |

### 3.4 能量守恒闭合（10/10 run）

独立于 `verification.checks` 的一次算术复核。对每个 run 取 trace 逐区间求和：

```
余量 = 可用PV + 进口 − 出口 − 总负载 − 系统辅助
闭合 = 余量 − (充电损耗 + 放电损耗) − 静置损耗 − 储能净增量
```

| run | 余量 kWh | 转换损耗 | 静置 | 储能净增 | **闭合残差** |
| --- | ---: | ---: | ---: | ---: | ---: |
| `8b366d7cbe` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0 |
| `f32e226aa7` | −0.000000 | 0.000000 | 0.000000 | 0.000000 | −8.9e-16 |
| `553b1fbb4f` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 8.9e-16 |
| `a796be35b9` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 8.9e-16 |
| `7f04efe981` | 543.352703 | 543.352703 | 0.000000 | 0.000000 | 1.1e-12 |
| `6576e35848` | 543.352703 | 543.352703 | 0.000000 | 0.000000 | 1.1e-12 |
| `e768842d86` | 0.619801 | 0.619801 | 0.000000 | 0.000000 | 2.4e-12 |
| `ecb5b44ead` | 0.619801 | 0.619801 | 0.000000 | 0.000000 | 2.4e-12 |
| `52796585d1` | 10.245515 | 10.245515 | 0.000000 | 0.000000 | −1.7e-12 |
| `fc3304d4b6` | 221.272511 | 160.970342 | 55.056975 | 5.245194 | 1.2e-12 |

10/10 闭合到 **≤2.4e-12 kWh**。注意 `fc3304d4b6` 那一行：只有把静置损耗与储能净增
一并计入才闭合，说明这三项在 witness 里是**分别记账**而不是被折叠掉。

### 3.5 时序轴不变量（10/10 run）

| run | 区间数 | gap | overlap | 非正时长 | naive | 非 ISO | 总跨度 h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `52796585d1` | 8760 | 0 | 0 | 0 | 0 | 0 | 8760.0 |
| `553b1fbb4f` | 2 | 0 | 0 | 0 | 0 | 0 | 2.0 |
| `6576e35848` | 8760 | 0 | 0 | 0 | 0 | 0 | 8760.0 |
| `7f04efe981` | 8760 | 0 | 0 | 0 | 0 | 0 | 8760.0 |
| `8b366d7cbe` | 2 | 0 | 0 | 0 | 0 | 0 | 2.0 |
| `a796be35b9` | 2 | 0 | 0 | 0 | 0 | 0 | 2.0 |
| `e768842d86` | 8760 | 0 | 0 | 0 | 0 | 0 | 8760.0 |
| `ecb5b44ead` | 8760 | 0 | 0 | 0 | 0 | 0 | 8760.0 |
| `f32e226aa7` | 2 | 0 | 0 | 0 | 0 | 0 | 2.0 |
| `fc3304d4b6` | 8760 | 0 | 0 | 0 | 0 | 0 | 8760.0 |

---

## 4. 未发现合同偏离

逐项核对下来**没有一条规格承诺在生产 witness 上不成立**，因此本次不报产品缺陷。
`solar_autarky`、`pv_input_self_use`、充电损耗、放电损耗、静置损耗五个可独立重算的量
在抽样 run 上全部 **delta = 0**；能量守恒闭合到 1e-12 量级；时序轴 0 违例。

唯一"看起来像偏差"的一处已排除：`internal_aux_supplied_kwh = 0` 而 trace 里
`frame.aux_ac_kw` 求和为 175.2 kWh。这不是矛盾——`internal_aux_kw` 是**电池内部**
辅助（该 run 显式 0.0），`frame.aux_ac_kw` 是**客户系统外部**交流辅助，正是
`548-energy-job.md` 第 9 条要求的"PV availability and AC auxiliaries retain their
distinct identities"。两个字段各有其位。

---

## 5. 证据边界（这是本次最重要的限定）

### 5.1 输入全部是合成夹具

每个 run 的 profile 资产都带 provenance，逐条读回：

| run | `gross_load` label | `origin` |
| --- | --- | --- |
| `52796585d1` | `Synthetic annual 2 kW site load` | `synthetic` |
| `553b1fbb4f` | `Synthetic 2023 gross load · Paris reference scenario` | `synthetic` |
| `6576e35848` / `7f04efe981` | `Owned synthetic 2025 hourly site load and zero auxiliary` | `synthetic` |
| `8b366d7cbe` | `Owned synthetic · two-hour acceptance` | `synthetic` |
| `fc3304d4b6` | `Synthetic household load 2023` / `Synthetic auxiliary load 2023` | `synthetic` |

`rights_basis` 原文（`6576e35848`）：
> "Owned synthetic test data generated for release acceptance; **not measured
> consumption**. Permanent private storage with this project is permitted."

PV 侧是真数据：`source: official_jrc_https_original`，`origin: modelled`，
`JRC PVGIS typical meteorological year`，带完整捕获 URL、`received_at_utc`、
原始/解析后双哈希。**也就是说：PV 是实测模型产物，负载是合成数据。**

结论：**这个域在生产上没有一例真实客户的电表负载数据。**
生产链路（WordPress → HTTP → worker → CAS → 结果读回）是真实的，负载数值不是。

### 5.2 按 D 线自己的截止线，只有 1 次在窗口内

`548-domain-gap-matrix.md:3` 把"可发布"定义为"有实现且有 **2026-11-05 之后**的生产证据"。
本域 10 次执行里：

- **9 次在 10-27 至 11-02**（截止线之前）
- **1 次在 11-06 15:23 UTC**（`fc3304d4b6`，截止线之后）

按该线自己的定义，支撑"可发布"的窗口内证据是 **1 次**，不是 10 次。
D 线给出该评级时并没有这 10 次的数据，所以这个评级当时没有依据；现在有依据了，
但依据的**时间分布**必须写明。

### 5.3 本域没有 witness 文档

geometric/direct-beam 的 result 里有 `dependencies["model.witness"]`，可以读出
`samples`/`module_steps` 等实际消耗。**能量域没有这个结构**：result 的
`dependencies` 只有 `{"energy_trace": <sha>}`。

等价证据由四段组成，本次按此核对：

| 角色 | 载体 |
| --- | --- |
| 输入解释（单位/时区/映射/变换） | `result.profile_interpretation` |
| 逐区间实际流与状态 | `trace` blob（`flows[].frame` + 27 个流量字段） |
| 输出指标 | `result.metrics`（含 `definitions` 自述口径） |
| 独立验证 | `result.verification.checks`（92 项，带 allowance 与 worst_violation） |

这不是缺陷，但**统计"实际消耗"时不能照搬 geometric 的 `inputs.work` 路径**——
能量域的预算是 `max_intervals`，实际用量只能从 `interval_count` 读。

### 5.4 verification 的区间覆盖分布

92 项检查中大部分落在 `at_interval = 0`（初始条件与建模恒等式），
平衡类检查落在真实后续区间：

| run | `at_interval` 分布 |
| --- | --- |
| `7f04efe981` | `{0: 82, 1: 3, 952: 1, 1963: 1, 1971: 2, 4459: 2, 5927: 1}` |
| `fc3304d4b6` | `{0: 76, 1: 3, 141: 1, 159: 2, 165: 1, 228: 1, 284: 1, 295: 1, 409: 2, 1299: 1, 3413: 2, 6602: 1}` |
| `8b366d7cbe` | `{0: 44, 1: 48}` |

即：`ac_energy_balance`、`stored_energy_balance`、`reference_discharge_delivery` 这类
真正的物理平衡检查，是在整年数据里的**具体区间**上取最坏值，不是只在第 0 区间过一遍。
但 `at_interval=0` 占 76–89% 这一事实要记录：**它们证明初始条件与恒等式，不证明全年每区间。**

---

## 6. 判定

### 6.1 "可发布（能力层）"——**维持，但按下列限定表述**

| 维度 | 结论 |
| --- | --- |
| 生产可执行 | **成立**。10 次真实执行，`production-linker-planner` 身份，0 失败，0 重试 |
| 规格合同 | **成立**。时序轴、单位、变换历史、守恒、指标定义、评估边界逐项通过 |
| 预算 | **成立且宽松**。`max_intervals` 最高用到 8.76%，不是"跑到上限才通过" |
| 规模覆盖 | **成立**。2 区间与 8760 整年都跑过；DST 跳变、春季缺时、整年非闰年都覆盖 |
| 客户数据 | **不成立**。0 例真实电表负载，全部 Linker 自有合成夹具 |
| 时间窗口 | **弱**。仅 1 次在 11-05 之后 |

**所以："可发布（能力层）"这个评级本身是准确的——它本来就限定在"能力层"。
但它不能外推成"该域已被真实客户数据验证"。**

### 6.2 两条必须更正的统计口径

1. **D 线第 3 行的"无生产执行"式推断**（本次未在其原文出现于能量域，但同一方法在
   direct-beam 上已经出过错）：本域 10 次执行确实存在，只看 `jobs.kind` 或
   `models.task` 都会漏掉。后续任何域级统计必须解 `manifest.context.models` 全字段。
2. **W 线 §2 的 task 计数表**漏了这 10 个 run（表中 8 行合计 133，不是 143）。
   该表结论"八个本域 run 全部 succeeded"不受影响，但作为全库分布表是不完整的。

### 6.3 三个内核的生产使用情况

| 内核 | 生产 run | 说明 |
| --- | ---: | --- |
| `single_ac_energy_replay_v1` | **10** | 本域唯一被真实执行过的 |
| `plant_ac_energy_replay_v1` | **0** | 多机并联储能。零生产执行 |
| `shared_dc_energy_replay_v1` | **0** | 共享直流母线。零生产执行 |

**这一条必须让评级收窄**：`548-energy-job.md`/`548-energy-replay.md` 的"能力层"覆盖三者，
但生产证据只覆盖其中**一个**。另两个内核的可发布性目前**只有单元测试**支撑。

---

## 7. 建议（留给主控/业主决定，本次未执行）

按成本从低到高：

1. **把矩阵第 3 行的表述改精确**：把"可发布（能力层）"限定为
   `single_ac_energy_replay_v1`，并把 plant / shared_dc 单列一行标"仅单测"。
   这是文档订正，零风险。
2. **补一例真实客户负载的整年 run**。现有 5 个项目里没有真实电表负载；
   要补需要真实客户投喂数据，属业主/主控决策，不是本线能自造的（自造只会重复
   当前证据的性质）。这一项才是把"能力层"抬到"客户级"的唯一途径。
3. **补一例 plant 或 shared_dc 的生产 run**。两者的执行器都在生产注册表里，
   但从未被调用；不补的话它们的"可发布"没有生产依据。

不建议的做法：为了凑"11-05 之后"而重复跑合成项目。合成夹具再跑 10 次也不改变
证据的性质，只会增加 CAS 永久占用（单个整年 trace 已 10.5 MB，`retention: permanent`，
见 `direct-beam-production-assessment.md` 风险 R6）。

---

## 8. 复现命令

生产只读，全程未写入：

```bash
# 1) 任务身份分布：必须按 models 全字段，不能只看 models.task
ssh linker-services 'python3 - <<"EOF"
import sqlite3, json, os
c = sqlite3.connect("file:/opt/linker-planner/state/workspace/workspace.sqlite?mode=ro", uri=True)
root = "/opt/linker-planner/state/workspace/blobs"
load = lambda s: json.load(open(os.path.join(root, s[:2], s)))
for rid, man, res in c.execute("select id,manifest_sha256,result_sha256 from runs"):
    models = (load(man).get("context") or {}).get("models") or {}
    if models.get("replay"):          # 能量域在这里，不在 models.task
        print(rid[:10], models["replay"], load(res)["interval_count"])
EOF'

# 2) 执行状态与耗时
ssh linker-services 'python3 -c "
import sqlite3
c=sqlite3.connect(\"file:/opt/linker-planner/state/workspace/workspace.sqlite?mode=ro\",uri=True)
for r in c.execute(\"select state,attempt,count(*) from jobs group by state,attempt\"): print(r)'"

# 3) 契约核对（时序轴 / 守恒 / 指标恒等式）见 §3.4、§3.5 的脚本逻辑，均为只读 trace 求和
```

本地无测量（本域本次不需要本地复跑：生产 witness 已含逐区间 frame，
外部重算即可判定，不必启动站点或 engine 实例）。

---

## 9. 资源与收尾

- 生产只读：只读 SQLite（`?mode=ro`）、blob 文件读取、`jobs`/`runs`/`projects` 查询。
  未写入、未重启、未改配置。
- 唯一生产写入：`/tmp/*.py` 临时脚本 6 个，运行后全部删除（见末尾核对）。
- 本机：`/tmp/y-energy-en.py` 等一次性脚本，任务结束回收。
- worktree：`/tmp/y-energy`（分支 `y-energy`），提交后保留供 PR 使用，合并后回收。
