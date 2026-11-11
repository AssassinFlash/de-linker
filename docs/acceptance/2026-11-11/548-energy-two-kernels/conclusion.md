# plant_ac / shared_dc 能量重放：生产执行阻塞取证（2026-11-11）

承接 `#1107`（`docs/acceptance/2026-11-11/energy-production-evidence.md`）与
`#1119`（BDEW/VDEW 官方负载画像入库）。目标是给 `plant_ac_energy_replay_v1` 与
`shared_dc_energy_replay_v1` 补上生产执行证据，用官方画像作负载输入。

**结果：两个内核在生产上无法执行，本次没有产生任何生产 run。** 原因不是"没人调用"，
也不是内核数值缺陷，而是**设备事实门**：两内核的电池参数都必须经
`prepare_dc_parameters()` 从当前 Woo 设备事实派生，而当前 86 个工程就绪产品里
**没有任何一组逆变器+电池**能同时满足"完整电压窗口"与"可用能量"两条判据。
本次不写生产（run / 项目 / 资产均为 0），因此 CAS 增量实测为 **0 字节**。

---

## 1. 内核选择逻辑（读码结论，非推断）

唯一分派点是 `EnergyService.kernel_for()`（`services/engine/src/linker_engine/planning/energy_service.py:41-70`），
按项目 `inputs` 的键决定，四者互斥：

| 项目 inputs | 内核 | `models["replay"]` |
| --- | --- | --- |
| 有 `equipment_plant`／`equipment_plant_setup`，且 `energy_plant.coupling == "plant_shared_dc"` | `DcPlantEnergyKernel` | `plant_shared_dc_energy_replay_v1` |
| 有 `equipment_plant`／`equipment_plant_setup`（AC） | `PlantEnergyKernel` | **`plant_ac_energy_replay_v1`** |
| 无 plant，`EnergyInputs.coupling == "independent_ac"` | `EnergyKernel` | `single_ac_energy_replay_v1` |
| 无 plant，`EnergyInputs.coupling == "shared_dc"` | `DcEnergyKernel` | **`shared_dc_energy_replay_v1`** |

三个能量内核（外加 joint DC 第四个）都把身份写在 `models["replay"]`，
不写 `models["task"]`——`#1107` 的方法结论（必须解 `manifest.context.models` 全字段）
本次独立复核成立：生产 143 个 run 中 `models.replay` 有值者 10 个、`models.task` 有值者 133 个，无一重叠。

`plant_ac` 与 `single_ac` 的差异不止分派：`PlantEnergyKernel.parameter_dependencies()`
（`plant_energy_kernel.py:199-235`）要求每个单元一个 `battery_parameters_v1` 资产，
且该资产 metadata 必须同时带 `equipment_unit_id == unit_id` 与
`dependencies == {dc_prepared_parameters, dc_woo_inputs}`；
`DcEnergyKernel.context()`（`dc_energy_kernel.py:41-66`）对 `shared_dc` 要求同样的 DC 派生依赖。
**这两个内核的电池参数只能由服务端 `/battery/scenario` 从现行 Woo 设备事实派生**
（`http_asset_intake.py:104-158`，走 `prepare_dc_parameters`），手写的 AC 场景参数资产不被接受。

## 2. 官方画像如何进入能量重放（已验证可用）

`planning/load_profile.py` 的 `expand()` 产出真实一年 15 分钟序列，`to_csv()` 直接输出引擎自己的
`csv_profile_v1`（`time,power`，带显式 UTC 偏移）。本次实测（本地，未写生产）：

| 画像 | 输入年用量 | 区间数 | 年度积分 kWh | `normalisation_gap` |
| --- | ---: | ---: | ---: | ---: |
| BDEW H25（2025 版） | 60 000 | 35 040 | 59 952.142 | 0.059 952 |
| BDEW G25（2025 版） | 1 200 | 35 040 | 1 203.510 | 0.001 204 |

再用引擎自己的读取链复核（`CsvMapping` + `profiles.read_profile` + `timezone_rules.load_timezone`）：
35 040 区间全tile、`native_max_interval_seconds = 900`、`reconstructed_means = False`（不是重建均值），
春季跳变日无缺口，首个区间为 `2024-12-31T23:00:00+00:00`。
**即：官方画像可以原样作为 `gross_load` 注入，无需改造，也不需要重采样。**

## 3. 生产侧实测（只读，零写入）

### 3.1 四个内核都在生产进程里注册

`POST /planning/version`（team 身份，只读）返回
`runtime_sha256 = 3f2b58893434f25a04a4c9f4f45061d76b099fdf9574914d5478bbf1dfdaf7c3`，其中：

```
"replay": "single_ac_energy_replay_v1",  "dc_replay": "shared_dc_energy_replay_v1",
"plant_replay": "plant_ac_energy_replay_v1", "plant_dc_replay": "plant_shared_dc_energy_replay_v1"
```

**注册齐全，缺的只是调用方**——这一条排除了"运行时未部署执行器"这类可能原因。

### 3.2 生产 run 分布（独立复核 `#1107`）

`runs` 143 / `revisions` 178 / `project_assets` 138 / `projects` 70；
`jobs`：succeeded 137、failed 6；`models.replay` 计数仅
`single_ac_energy_replay_v1 = 10`。`plant_ac` / `shared_dc` / `plant_shared_dc` 均为 **0**。

### 3.3 从来没有过 plant / shared_dc 场景（比"没执行"更强）

逐条解全部 178 个 revision 的 inputs：

- 带 `energy_plant` 且含 `coupling` 者 **0**；
- 带 `energy_replay.coupling == "shared_dc"` 者 **0**。

生产有 4 个项目准备了 `equipment_plant`（3 个 `user:wp:1:user:1` 自有验收 + 1 个 guest 的
PR828 合成验收），但它们的单元全是纯逆变器或从未备过场景参数；**没有任何单元备过
`battery_parameters_v1`**（下表）。所以两个内核在生产上连"可执行场景"都没出现过。

### 3.4 生产 5 个电池参数资产全部是"用户显式场景"，不可用于这两个内核

| 项目 | `dependencies` | `equipment_unit_id` | provenance basis |
| --- | --- | --- | --- |
| `1812286480` | `[]` | 无 | `user_explicit_scenario_not_equipment_release` |
| `51d074af0c` | `[]` | 无 | 同上 |
| `88e747ebda` | `[]` | 无 | 同上 |
| `acb2ee16d1` | `[]` | 无 | 同上 |
| `517eb7457d` | `[]` | 无 | 同上 |

`single_ac` 用这 5 个就够（`#1107` 的 10 次执行全部如此），但 `plant_ac` / `shared_dc`
要求 `dc_prepared_parameters` 依赖，一个都不满足。

## 4. 设备事实门：签名固定的池上 0 / 1763

`prepare_dc_parameters()`（`dc_parameter_source.py:170-333`）是 `/battery/scenario` 的唯一派生入口。
它串联多道事实门，任何一道不过就拒绝：

1. `woo_dc_fact:usable_energy_and_complete_voltage_window` — 先要 `battery_voltage` 判据
   （电池 `system_operating_voltage_range_v` / `operating_voltage_range_v` / `voltage_range`
   之一，与逆变器 `battery_voltage_range_v` **完整包含**），再要 `usable_energy`（只在电压
   `satisfied` 时才给数）；
2. `woo_dc_fact:battery_port_count` — 逆变器必须给出端口数或声明端口名，场景的
   `battery_port_id` 要落在其中；
3. `woo_dc_condition:<pid>:max_charge_current_a` — 电池的充电电流事实必须带可解释的
   qualifier（模块数范围、温度条件等）。

在**签名固定**的工程就绪池上穷举，扫描前后各算一次 `ready.engineering` 产品集合的 SHA-256：

```
pool signature at start: 008fcf36a56d8a31   engineering-ready: 86
pool signature at end:   008fcf36a56d8a31   engineering-ready: 86   drifted: False
basis products: 83
tried: 1763   ok: 0
```

即 42 台逆变器 × 26 块电池 × 每块电池全部合法 `modules_per_stack` × 每个声明端口
（无声明时用 `battery-1`），**1763 次派生尝试，0 次通过**，且扫描期间池未漂移。

另一次同会话但**更宽的端口回退**（无声明端口时同时试 `battery-1` 与 `BAT1`，共 3444 次）
给出的失败分布，用于看清阻塞是**多道门串联**而非单一判据：

| 失败类别 | 次数 |
| --- | ---: |
| `woo_dc_fact:usable_energy_and_complete_voltage_window` | 2 708 |
| `woo_dc_fact:battery_port_count` | 712 |
| `woo_dc_condition:<pid>:max_charge_current_a` | 6 |

那次扫描同时报告了 18 次"通过"，但它**没有记录池签名**，且同一时段的后续复扫均无法重现。
按本仓库对证据的要求，这个 18 被**丢弃**，不作为任何结论依据；上表的 0 / 1763 才是
可复现、可核验的判定。

### 4.0 为什么当前池一块电池都过不去（逐项）

| 电池 | 模块数 | 可用能量事实 | 门控电压事实 |
| --- | --- | --- | --- |
| 1832 / 2067-2070 / 2090 / 2093 | 1-5 | 有 | **无** |
| 1956-1958 / 1959-1961 / 2003 / 4103-4106 | 4-5 或未声明 | **无** | **无** |
| 2092 | 1-5 | **无** | 有（列按模块数） |
| 3611 / 3612 / 6519-6522 | 未声明下界，上界 6 | 有 | 有（但 `qualifier: null`，且 700~950 V 与在售逆变器的 180~800 V 不相交） |
| 6321 | 未声明 | 有 | **无** |

43 台逆变器里**只有 `4107`（H2-10K-T3）声明了电池端口**（`BAT1`/`BAT2`）与端口电流，
其余逆变器连 `battery_port_count` 都没有——这是 `battery_port_count` 那 712 次失败的来源。
而声明了端口的 `4107` 电压窗口是 180~800 V，能与之完整包含的电池（1954/2093 一类）当前
要么不在就绪池、要么缺可用能量事实。

### 4.1 关键反例：可行组合存在过，但被就绪状态撤下

本次会话前段，`4107`（H2-10K-T3）+ `1954`（GOODWE BAT-C）+ `modules_per_stack = 6` +
`battery_port_id = BAT1` **完整通过**，产出：

```
usable_window_kwh = 60.0
source_facts.usable_energy_derivation.actual = 60.0  (60.0 × 1, 带双语条件原文)
```

这一步与 `pv_dc_kw` 无关：`pv_dc_kw = 0`（`plant_ac` 需显式无 DC PV）与 `pv_dc_kw = 6`
（`shared_dc` 走 PV 组）两种取值的派生都成功，说明**电池侧的门一旦通过，两内核共用同一条链**。

会话末段复测，同一组合已不在派生产物视野内（`product_revisions` 查表已取不到 1954）。
原因在发布层而非代码：

| 产品 | `ready.knowledge` | `ready.engineering` |
| --- | --- | --- |
| 1954 | false | **false** |
| 1955 | false | **false** |
| 2093 | true | true |
| 4107 | true | true |
| 2092 | true | true |

`Publication.prepared_view()` 只保留 `ready.engineering is true` 的产品，1954/1955 因此被剔除，
`4107 + 1954` 这条实证可行的链随之中断。

这个就绪状态在本会话内**反复变化**（同一产品先后读到 `true` 与 `false`，
`engineering-ready` 计数在 83/86/88 之间浮动），而 C 线此刻正在改 Woo 数据
（本任务的硬约束之一就是不碰 Woo 数据）。因此它更可能是**在途状态**而非产品决策。
这也是为什么 §4 的判定必须绑定池签名：不绑签名的扫描结果在这段时间里不可复现，
本次已按该标准丢弃了一个这类结果。

剩下的就绪电池里，`2092` 的电压列只在 `mps ∈ {3,4,5}` 内 `satisfied`，但缺
`system_usable_energy_kwh`（`usable_energy` 判为 `cited_usable_energy_and_sales_basis`）；
`2093` 可选容量基准下报 `capacity_reference:sales_unit` 与
`capacity_reference:uninterpreted_conditions`，同样不成立。
**结论：签名固定的当前池里，没有任何就绪产品能同时满足全部事实门。**

## 5. 为什么本次没有生产 run（如实记录）

任务要求两内核各 ≥2 次生产实跑。**这一项没有达成**，原因是数据而非代码：

1. 要跑 `plant_ac`，先要有每单元的 `battery_parameters_v1`（带 `dc_prepared_parameters` 依赖）；
   派生前置即 §4 的设备事实门，签名固定的池上 0/1763 通过。没有参数资产，
   `PlantEnergyInputs.from_project()` 连 `energy_plant` 场景都无法通过；
   `/runs/energy` 会在 `context()` 阶段拒绝。
2. `shared_dc` 同一道门（`battery.dc_prepared_parameters`），且额外要求
   `pv_available_dc` 是 retained PV producer 产物（`pvlib_reference_profile_v1` 或
   `geometric_pv_reference_profile_v1` 的 `project_dc` 投影），CSV 不能顶替。
   生产里确有可用 PV 产物（`181228648034` 项目的 `pvlib_reference_profile_v1`，
   `geometry_sha256` / `parameters_sha256` 与当前输入逐项相等，witness 含 8760 个
   `dc_available_w`），**但缺同一道门后的电池参数**。

因此本次**主动不写生产**：不建项目、不灌 CSV 资产、不发 `/runs/energy`。
理由是按 `#1107` 记录的 CAS 占用约束（单条整年 trace 约 10.5 MB、`retention: permanent`），
在明知第一步就会 422 的情况下写入只会留下永久占用与失败 job，不产生任何证据增量。

- CAS：`/opt/linker-planner/state/workspace/blobs` 起 **495 564 061 字节**，止 **495 564 061 字节**，
  **增量 0 字节**。
- 磁盘：`/dev/sda1` 剩余 45.06 GB → 45.08 GB（正常波动），占用 12%。
- 生产只读方式：`?mode=ro` SQLite、blob 读取、`/planning/version` 与 `/products/current` 的
  team 只读 RPC；未重启、未改配置、未动 `/opt/linker-planner` 任何文件。

## 6. 解除阻塞的条件（给主控／业主）

按成本从低到高，任一条成立即可让我把两内核的生产证据补齐：

1. **恢复 1954 的工程就绪**（`ready.engineering = true`）。`4107 + 1954 @ mps=6, BAT1`
   已实证可派生（`usable_window_kwh = 60.0`；`pv_dc_kw = 6` 与 `0` 都能过——`pv_dc_kw`
   不是这道门的变量），恢复后即可直接跑 `plant_ac`；`shared_dc` 可复用同一电池并配
   `181228648034` 的 `pvlib_reference_profile_v1`。
2. **给某块就绪电池补齐两条事实**：带正确 qualifier 的
   `system_operating_voltage_range_v`（列以模块数为键）与 `system_usable_energy_kwh`
   （或 `module_energy_kwh_usable` + 明确的 `sales_unit_kind`/固定模块数）。
3. 这两条都属于 **Woo 设备数据**（C 线范围），本线按硬约束不碰。

**关于 1954/1955 就绪状态的时间性**：本次是在同一会话内先后观察到 `true` 与 `false` 两种
状态，而 C 线此刻正在改 Woo 数据（本任务的硬约束之一就是"不碰 Woo 数据"）。因此
`ready.engineering = false` **很可能不是一次产品决策，而是另一条线的在途状态**。
这也意味着：解除条件 1 可能不需要任何人工裁定，等 C 线那批写入落定后重测即可；
重测的第一件事应是重新读 `ready` 两名值并记录池签名，而不是直接重跑穷举。

## 7. 评级影响

`docs/acceptance/2026-11-11/548-domain-gap-matrix.md` 第 3 行：

- **改前**：`可发布（能力层）`，缺口栏写"另两内核零生产执行——评级限单内核"。
- **改后**：`需补验`，缺口栏写明两内核受阻于设备事实门（签名固定池上 0/1763、且阻塞是
  电压窗口/端口声明/电流条件三道门串联）、唯一实证可行的链 `4107+1954` 因
  `ready.engineering=false` 被撤下、以及解除条件。
  单内核 `single_ac` 的能力层评级不变（`#1107` 的 10 次执行仍然成立）。

换句话说：`#1107` 提出的"给两内核补生产 run"这条建议，本次给出了**可执行性判定**——
不是"再跑一次就有证据"，而是"当前设备数据下跑不起来"。这比补两次 run 更能解释矩阵里
那半格的真实状态。

## 8. 复现命令

```bash
# 1) 内核注册（只读）
REL=/opt/linker-planner/releases/<current>
TOK=$(sudo cat $REL/.deploy/http.env | grep '^GENIE_SERVICE_TOKEN=' | cut -d= -f2- | tr -d '"')
curl -s -X POST -H "X-Linker-Service-Token: $TOK" -H "X-Linker-Planner-Principal-Kind: team" \
  -H "X-Linker-Planner-Principal-Subject: read-only" -d '{"schema_version":1}' \
  http://127.0.0.1:8911/planning/version

# 2) 就绪标志（worker 环境内执行；只读）
sudo -u linker-planner env $(grep -v '^#' $REL/.deploy/worker.env | xargs) \
  $REL/.venv/bin/python - <<'PY'
from linker_engine.app import SOURCE, Services, Settings
s = Services(Settings.from_environment(), SOURCE)
cur = s.publication.read()
ready = {i["product_id"]: (i.get("ready") or {}) for i in cur["products"]}
print("engineering-ready:", sum(1 for v in ready.values() if v.get("engineering") is True))
for pid in (1954, 1955, 4107, 2092, 2093):
    print(" ", pid, ready.get(pid))
PY

# 3) 事实门穷举，必须绑定池签名（下面脚本前后各打一次签名，drifted 必须是 False）
#    脚本主体见 §4 的 tried/ok 口径：42 inverters x 26 batteries x legal module counts x declared ports
```

§4 的两次扫描都用同一份脚本骨架，唯一的差别是端口回退策略
（只在声明端口上试 vs 无声明时同时试 `battery-1` 与 `BAT1`）。
判定用的是绑签名那次；不绑签名那次只用来读失败分布，其"通过"计数已丢弃。

```bash
# 4) 官方画像 → 引擎读取链（本地，零生产写入）
cd services/engine && .venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "src")
from linker_engine.planning import load_profile as lp
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.profiles import read_profile
from linker_engine.planning.timezone_rules import load_timezone
p = lp.expand(2025, "H25", year=2025, annual_kwh=60000)
csv = lp.to_csv(p)
m = CsvMapping("time","power","gross_load","interval_average_kw","start","Europe/Berlin",
               "template",900.0,",",".",None,None,None)
s = read_profile(csv, m, load_timezone("Europe/Berlin"))
print(len(s.intervals), round(s.total_kwh,3), s.source.native_max_interval_seconds)
PY
```
