# direct-beam 与 geometric-pv 生产启用评估（W 线，2026-11-11）

只读评估。生产侧未做任何写入、重启或配置变更；启用本身留给业主或主控决定。
本地受控测量在仓库 `services/engine` 内用现有 `.venv` 运行，临时脚本与输出已回收。

## 结论先行

**两条链在生产上早已启用并已成功执行过。** `548-domain-gap-matrix.md` 第 3 行
"direct-beam/geometric-pv 无生产执行"**不成立**：D 线用的是 job 状态表
（生产 `jobs.kind` 只有 `evaluate` 一个值），没有解 run 的 manifest，因此看不见任务类型。

| 项 | 事实 | 证据 |
| --- | --- | --- |
| 执行器注册 | 两个都已注册 | 生产 `POST /planning/version` 返回 `models.direct_beam_visibility=prepare_direct_beam_visibility_v1`、`models.geometric_pv_generation=prepare_geometric_pv_reference_v1` |
| 真实执行 | direct-beam **1 次**、geometric **7 次**，全部 `succeeded`、`attempt=1` | 143 个 run 的 manifest `context.models.task` 统计 |
| expanded 隔离 | **已在生产生效并跑过** | 1 次 `clear_pitched_roof_v1`（2026-11-02），worker 单元含 `Delegate=cpu memory pids` + `DelegateSubgroup=supervisor` |
| 普通 geometric 配额 | **已用掉 95.6%**（module_steps 210,240 / 220,000） | §2、§5 R5 |
| direct-beam 配额 | 只跑过上限的 0.03% | §2、§3.2 |

因此本评估的交付不是"如何启用"，而是**"既然已启用，当前配置是否安全、缺什么证据"**。
建议见 §6。

---

## 1. 加载机制：改什么，不用改什么

`RuntimeConfig.from_environment()` 只读一个环境变量 `LINKER_PLANNER_CONFIG`，其值是
**JSON 文件路径**，不是 env 段。生产实际文件是
`/opt/linker-planner/releases/<sha>/.deploy/runtime.json`，由 `planner_release.py`
的 `prepare()` 生成（`services/engine/ops/planner_release.py:413-450`）。

生产当前 `runtime.json` **已包含全部相关段**（只读 cat 实取）：

```json
{
  "pv_preparation":            {"max_array_steps": 2000000, "max_weather_bytes": 8388608, "max_weather_rows": 9000},
  "direct_beam_visibility":    {"max_selected_rows": 24, "max_samples": 2000000, "max_ray_face_checks": 20000000, "max_bounds_checks": 50000000, "index_leaf_size": 8},
  "geometric_pv_generation":   {"max_module_steps": 220000, "max_samples": 2000000, "max_ray_face_checks": 20000000, "max_bounds_checks": 50000000, "index_leaf_size": 8},
  "geometric_pv_clear_flat_roof":    {"max_module_steps": 841000, "max_samples": 4300000, "max_modules": 96, "max_strings": 6, "max_weather_rows": 8760},
  "geometric_pv_clear_pitched_roof": {"max_module_steps": 841000, "max_samples": 4300000, "max_modules": 96, "max_strings": 6, "max_weather_rows": 8760}
}
```

配套 `worker.json` 已有 `expanded_job`：

```json
{"cpu_quota_percent": 20, "memory_max_bytes": 1258291200, "minimum_available_bytes": 1610612736,
 "timeout_seconds": 600, "health_ports": [8901, 8911]}
```

**要改的东西：无。** 生产配置与当前 `main` 的 `RuntimeConfig`、`WorkerPolicy`、
`expanded_job` 契约完全吻合（逐一比对 `runtime_config.py:51-95` 的 validator 与
`worker_policy.py:14-40` 的字段上界，全部满足）。本地 review 实例 503 的原因是
`tools/local/src/linker_local/services.py:485-508` 的 `planner_environment()`
只写最小段（无 direct-beam/geometric/weather），**那是本地模板缺口，不是生产缺口**。

### 1.1 部署拓扑（评估"双 namespace"时容易搞错的地方）

生产有**两个独立部署共享同一个 SQLite store**，不是同一份代码发两次：

| 部署 | 单元 | 用户 | 端口 | 谁在调 |
| --- | --- | --- | --- | --- |
| `/opt/linker-planner` | `linker-planner-http` + `linker-planner-worker` | `linker-planner` | 8911 | **WordPress**：`wp option linker_planner_url` = `https://72.62.97.95:8443/planning` → nginx `location ~ ^/planning` → `127.0.0.1:8911` |
| `/opt/linker-engine` | `linker-engine` | root | 8901 | 存量 sizing/health，不承接 `/planning` |

两者 `src/linker_engine/planning/` 各 259/260 个 `.py`，**16 个文件不同**
（`report_model.py`、`product_sources.py`、`pv_string_assessment.py` 等）。
但本域全部相关文件（`runtime_config.py`、`direct_beam_*.py`、`geometric_pv_*.py`、
`worker_host.py`、`worker_policy.py`、`expanded_job.py`、`schema.py`）**逐字节相同**。

对启用而言这意味着：**改 `planning/**` 需要两个 release 都重新发布**，否则客户
请求走的 8911 与另一条 8901 会在同一 store 上出现两套执行器身份。当前两边本域
代码一致，所以**现状没有这个风险**；一旦要改 direct-beam/geometric 的逻辑，
必须同批发布两个 namespace。

---

## 2. 生产实际执行史（这是"无生产执行"被推翻的直接证据）

按 manifest `context.models.task` 统计 143 个 run：

| task | run 数 |
| --- | ---: |
| `planning_report_v1` | 50 |
| `qualify_woo_equipment_v1` | 35 |
| `search_woo_equipment_v1` | 28 |
| `acquire_pvgis_tmy_weather_v1` | 9 |
| **`prepare_geometric_pv_reference_v1`** | **7** |
| `prepare_roof_pv_reference_v1` | 2 |
| `prepare_pvgis_roof_ac_reference_v1` | 1 |
| **`prepare_direct_beam_visibility_v1`** | **1** |

八个本域 run 逐个查 `jobs` 表，全部 `succeeded`、`attempt=1`，无重试、无 error。
witness 里记录了**实际消耗**（`inputs.work`），这是判断配额是否被验证过的关键：

| task | 时间 (UTC) | 执行类 | 墙钟 | 实际 samples | 预算上限 | 实际 module_steps | 上限 | 用量 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| direct-beam | 10-28 09:10 | — | 20.3 s | **680** | 2,000,000 | — | — | **0.03%** |
| geometric | 10-29 06:52 | 普通 | 71.5 s | 421,700 | 2,000,000 | 175,200 | 220,000 | 21% / 80% |
| geometric | 10-29 07:26 | 普通 | 61.2 s | 421,700 | 2,000,000 | 175,200 | 220,000 | 21% / 80% |
| geometric | 10-30 10:41 | 普通 | 94.6 s | 490,680 | 2,000,000 | 210,240 | 220,000 | 25% / **95.6%** |
| geometric | 11-01 22:25 | 普通 | 26.5 s | 134,304 | 2,000,000 | 52,560 | 220,000 | 7% / 24% |
| geometric | 11-01 22:41 | 普通 | 26.1 s | 134,304 | 2,000,000 | 52,560 | 220,000 | 7% / 24% |
| geometric | 11-02 02:56 | 普通 | 20.5 s | 122,670 | 2,000,000 | 52,560 | 220,000 | 6% / 24% |
| geometric | 11-02 04:53 | **`clear_pitched_roof_v1`** | **149.0 s** | 552,015 | 4,300,000 | 236,520 | 841,000 | 13% / 28% |

（普通 geometric 的 `sample_upper_bound` 分别是 876,000 / 1,053,504 / 263,376，
实际量是上界的约 48%；expanded 那次 upper 1,185,192、实际 552,015，约 47%。）

**"跑过"≠"按工作量验证过"**：

- direct-beam 那一次只有 **680 样本**（10 模块 × 2 行 × (3²+5²)），且
  `ray_face_checks: 0`（无遮挡面相交）。生产上限 **2,000,000 样本**，
  实际用量是上限的 **0.034%**。这是"能跑通"的证据，不是工作量证据。
- **普通 geometric 的 `module_steps` 已用到 95.6%**（210,240 / 220,000）。
  也就是说该通道的常规上限**已经被一次真实任务逼近**，几乎没余量；
  再大一点的屋顶会直接落进 `GeometricPvExpandedScopeRequired` 分支，
  而 expanded 只接受「单屋顶、单阵列、无遮挡、无 keepout、1×1 与 2×2 网格」
  的严格受限场景（`geometric_pv_admission.py:44-70`），否则整任务拒绝。
- expanded 只跑过 1 次，27 模块，远低于 96 模块上限。

**关于 6 个 `failed` job**：逐个解 manifest，3 个是 `planning_report_v1`、
3 个是 `acquire_pvgis_tmy_weather_v1`（PVGIS 取源），**没有一个是本域任务**。
其中 `e227ca32cd9e`（2026-11-07 18:08 UTC）的 traceback 落在 `report_pvlib.py:352`
的 `KeyError: 'nameplate_kwp'`，属于报告模板缺陷，**与本域执行器注册无关**。
D 线把这类失败当作"本域无生产执行"的旁证是误读。

---

## 3. 资源预算

### 3.1 主机现状（`linker-services`，2026-11-11 05:01 UTC，只读）

| 项 | 值 |
| --- | --- |
| vCPU | **1**（AMD EPYC 9354P） |
| 内存总量 | 3,915 MiB |
| `MemAvailable` | 2,731–2,797 MiB |
| **`CommitLimit`** | **2,004,596 kB（≈1.91 GiB）** |
| **`Committed_AS`** | **1,565,344 kB（≈1.49 GiB）** |
| Swap | **0** |
| `vm.overcommit_memory` | 0（启发式），`overcommit_ratio` 50 |
| 磁盘 | 48 GB，用 5.4 GB，可用 42 GB |
| 系统 load | 0.16 / 0.06 / 0.01 |

各单元实测（`MemoryCurrent` / `MemoryPeak`，MiB）：

| 单元 | Current | Peak | `MemoryMax` | `OOMPolicy` |
| --- | ---: | ---: | --- | --- |
| `linker-engine` | 145.1 | 146.1 | infinity | stop |
| `linker-genie` | 156.6 | 206.3 | infinity | stop |
| `linker-genie-judge` | 34.9 | — | infinity | stop |
| `linker-planner-http` | 187.9 | 189.5 | infinity | stop |
| `linker-planner-worker` | 204.3 | 207.4 | infinity | **continue** |
| `linker-engine-tls` | 2.5 | — | infinity | stop |

磁盘上 planner workspace 500 MB，其中 CAS blobs 499 MB / 6,257 个文件，最大单 blob 40.5 MB。

**最硬的约束不是 `MemAvailable` 而是 commit 额度**：`CommitLimit` 1.91 GiB，
已提交 1.49 GiB，**剩余可提交 ≈ 0.42 GiB**，且无 swap 兜底。expanded 子进程
`memory.max = 1.2 GiB` 是 cgroup 上限而非预先提交的额度，所以 runtime 不会立即
被拒，但一旦匿名内存真的增长，唯一结局是 OOM killer 而不是换页。
这也是 `expanded_job` 必须先检查 `MemAvailable >= 1.5 GiB` 才准入的原因
（`expanded_job.py:178`），该检查在生产上有效。

### 3.2 本地受控测量（本次实测，本机 Apple M3 Pro，Python 3.12.15）

单核基准（同一段纯 Python 循环，6,000,000 次取模）：

| 主机 | 耗时 |
| --- | ---: |
| 本机 | 0.515 s |
| VPS（`nice 19`，两次） | 0.656 / 0.704 s |

→ **VPS 单核比本机慢约 1.30 倍**。所有本机 CPU 数字按 1.3× 换算到 VPS。

**geometric PV expanded（96 模块路径，`clear-flat-roof` 用例）**

```
1 passed in 94.61s
96.83 real   84.68 user   3.36 sys
644,464,640  maximum resident set size
959,006,016  peak memory footprint
```

| 指标 | 本机 | VPS 换算（×1.3） | 生产 `memory.max` 余量 |
| --- | ---: | ---: | --- |
| 峰值 RSS | **644 MB** | 内存不随 CPU 缩放，仍 644 MB | 1.2 GiB 上限的 **53%** |
| CPU | 84.7 s | **≈110 s** | 600 s 超时的 18% |
| 墙钟 | 96.8 s | ≈126 s | |

与历史生产读数一致：`docs/research/2026-11-04-load-governance-readback.md`（§3.3）记录的
**VPS 上**96 模块 8,760 小时测试（2026-11-02 01:20 UTC）子 cgroup 峰值
**815–894 MiB**，期间主机 `kbavail` 最低降至 **1,818 MiB**。548 INDEX 的
334.99 s / 59.62 s CPU / 855,224,320 B 是同一路径的更早一次合成验证。

本次本机 644 MB 低于该生产读数，因为测试用例的 witness 规模小于 96 模块全年。
**该路径的真实上界应按 894 MiB 算**，距 1.2 GiB cgroup 上限只剩 **≈25%**，
且届时主机可用内存会掉到 1.8 GiB 附近——正好压在 `minimum_available_bytes`
（1.5 GiB）的准入线之上，余量约 300 MiB。

**direct-beam（生产 sample 上限下实测）**

用 `fixtures/planning/geometry-flat.json` 扩到 24 模块（4×6）+ 一面 7 m 长、0.5 m 厚、
3 m 高的实体墙，太阳方向 (-1/√2, 0, 1/√2)（45° 高度角，墙体挡在西侧），逐档加大网格：

| 网格 | 样本 | `ray_face_checks` | `bounds_checks` | CPU | 单样本 | 峰值 RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 30×30 / 60×60 | 108,000 | 140,400 | 2,220,120 | 5.64 s | 52.2 µs | 47.5 MB |
| 60×60 / 120×120 | 432,000 | 561,600 | 8,878,608 | 23.04 s | 53.3 µs | 47.6 MB |
| 120×120 / 240×240 | 1,728,000 | 2,246,400 | 35,512,560 | 99.21 s | 57.4 µs | 47.8 MB |

线性度在样本数上良好（52.2–57.4 µs/样本，末档偏慢是因为墙的阴影覆盖更多模块），
**内存恒在 47 MB 量级，与样本数无关**。直接按末档比率外推生产上限
**2,000,000 样本**（只外推 16%，不是长距外推）：

| 指标 | 1.728 M 实测 | 2.0 M 外推 | 生产上限 | 占用 |
| --- | ---: | ---: | ---: | ---: |
| CPU（本机） | 99.2 s | ≈ **115 s** | — | — |
| CPU（VPS ×1.3） | ≈ 129 s | ≈ **149 s** | — | — |
| 峰值 RSS | 47.8 MB | ≈ 48 MB | — | — |
| `ray_face_checks` | 2.25 M | ≈ 2.6 M | 20 M | **13%** |
| `bounds_checks` | 35.5 M | ≈ **41.1 M** | 50 M | **82%** |

`bounds_checks` 是最先触顶的预算：一次满上限任务会吃掉生产 bounds 上限的 **82%**。
超过即 `InvalidInput("direct-beam bounds resource budget exhausted")` 整任务失败，
不产生部分结果——这是正确的 fail-closed 行为，但意味着**接近上限的任务会失败而不是变慢**。
而且这是 24 模块 / 一座墙的情况；模块或遮挡物更多的场景会在更低样本数触顶。

### 3.3 已有实测数据的可信度

`docs/acceptance/2026-10-31/548/INDEX.md:2484-2492` 有 expanded 路径的完整生产级
读数（334.99 s / 59.62 s CPU / 855 MB cgroup 峰值 / 两次健康检查全 200 / 临时单元
与 cgroup 事后确认消失）。`docs/research/2026-11-04-load-governance-readback.md` §3
有常驻基线与多峰值叠加分析。本次测量与这两份记录量级一致，没有推翻它们的证据。

**本次未覆盖、也不声称覆盖的**：96 模块满规模（测试用例是 96 模块但 witness 规模
小于全年客户项目）；多遮挡物与被遮挡组合；direct-beam 与 geometric 同时在飞的叠加。

---

## 4. 是否触碰 schema

**启用本身不触碰 schema。** 理由：

- `RuntimeConfig` 的 `schema_version` 固定为 1（`energy_inputs.SchemaVersion`），
  增加可选段不改变它——`direct_beam_visibility` 等字段本来就是 `| None = None`。
- SQLite `SCHEMA_VERSION = 5`、`READABLE_SCHEMA_VERSIONS = (1,2,3,4,5)`
  （`planning/schema.py:3-4`），本域新增的 `project_assets.purpose` 值
  （`geometric_pv_reference_profile_v1`）是**行值不是列**，不需要迁移。
- `planner_release.py:318-342` 的 preflight 会比对
  `workspace.sqlite` 的 `user_version` 与 release 的 `storage_schema_version`，
  生产两者都是 5，匹配。

**真正需要留意的不是 schema 而是 execution key**：`execution_key` 把
`code_sha256 + models + parameters` 一起冻结（`direct_beam_job.py:60-70`、
`geometric_pv_job.py:139-158`）。改动 `planning/**` 里任何被执行路径导入的文件
都会改变 `runtime_sha256` → 改变全部 execution key → 队列里旧 key 的任务只能由
旧 release 执行。`planner_release.py:801-806` 的 `drain()` 就是为此存在的：
它等 `pending == 0` 才允许换版，否则拒绝替换。

**双 namespace 发布纪律**（§1.1）：若改动本域代码，`/opt/linker-planner`
（走 `planner_release.py`）与 `/opt/linker-engine`（走 engine release 路径）
必须**同批发布**，且两边 `runtime_sha256` 的差异要能被接受。当前两边本域文件
完全一致，所以现状无此风险。

### 4.1 回滚路径（已核实可用）

`/opt/linker-planner` 保留两代 release：

```
releases/09f80a35d2fe…  ← current
releases/ea9a504bf29a…  ← previous
```

- 回滚命令：`python ops/planner_release.py rollback <spec.json>`
  （`planner_release.py:1009-1013`），走与激活同一条 `activate()` 路径：
  drain → 停旧 → 起新 → 校验 identity → 失败自动恢复旧 release 与 `selection.json`。
- 自动恢复：`activate()` 的 `except BaseException` 分支（`:827-847`）会停掉新单元、
  写回 `before`、重启旧 release 并 `control resume`。
- 保留策略：`activate()` 结束时只保留 current + 一个 rollback（`:849-858`），
  第三代立即 `shutil.rmtree`。
- drain 本身：`drain()`（`:587-599`）轮询 `control status` 直到
  `quiescent is True and pending == 0`，超 `drain_timeout_seconds`（生产 30 s）
  或 worker 不再 active 即抛错并保留原状。

回滚**不触碰数据**：workspace 与 blobs 在 `/opt/linker-planner/state/`，
两代 release 共用。降级到旧 release 时的风险只有一种——旧 release 不认识新 release
写入的 execution key，那些任务会被 drain 拦住而不是静默算错。

---

## 5. 风险清单

| # | 风险 | 严重度 | 现状 |
| --- | --- | --- | --- |
| R1 | **commit 额度**：`CommitLimit` 1.91 GiB，已提交 1.49 GiB，剩 ~0.42 GiB，无 swap | 高 | 已存在；expanded 准入检查 `MemAvailable ≥ 1.5 GiB` 提供了第一道闸，但它保护的是可用内存不是 commit |
| R2 | **`OOMPolicy=stop` 的四个单元**：`linker-engine`、`linker-genie`、`linker-genie-judge`、`linker-planner-http` 都是 `stop` + `Restart=on-failure`；只有 worker 是 `continue` | 中 | 已存在（`2026-11-04-load-governance-readback.md` 风险 2 已记录，未修） |
| R3 | **direct-beam 没有资源隔离**：它走普通 worker，不受 expanded cgroup 限制；2 M 样本任务在本机 ≈115 s CPU、VPS ≈149 s，单核期间与 HTTP/engine/genie 抢 CPU | 中 | 未隔离 |
| R4 | **direct-beam 的 `bounds_checks` 接近触顶**：1.728 M 样本实测已用 35.5 M / 50 M（71%），2 M 外推 82% | 中 | 未实测生产最大值 |
| R5 | **普通 geometric 的 `module_steps` 已被用到 95.6%**（210,240 / 220,000）。再大的屋顶会掉进 expanded 分支，而 expanded 只接受单屋顶/单阵列/无遮挡/无 keepout/1×1 与 2×2 网格的严格场景，否则**整任务拒绝**。多阵列或有遮挡的中等屋顶当前无通路 | **高** | 生产事实（2026-10-30 run） |
| R5b | **direct-beam 配额从未按工作量实测**：峰值 680 样本（上限 0.034%）；expanded 只跑过 27 模块（上限 96） | 中 | 本次读回 witness 证实 |
| R6 | **CAS 永久增长**：`retention: permanent`，单个 geometric witness 40.55 MB；blobs 已 499 MB | 低-中 | 有 `planner_maintenance.py` 维护 + launchd 每日 02:00 UTC 窗口，但它是 Mac 本地调用，且当前 `launchctl print` 显示路径指向 `.previous.plist` |
| R7 | 2026-11-04 记的 `planner_maintenance.py:79` 预算传递缺陷 | — | **已修复**：`action=='plan'` 现在是 `r.operator('retention', timeout=scan_budget)`，`scan_budget` 由 `work_deadline` 推导（`planner_maintenance.py:80-84`）。原记录已失效 |
| R8 | 本地 review 实例没有这两个段（503 的真实来源） | 低 | 文档/模板缺口，不影响生产 |

关于 R6 的补充：`launchctl print gui/501/com.linker.planner-maintenance` 当前
`path = …/com.linker.planner-maintenance.previous.plist`，即**正在跑的是"上一版"
plist**。这与 `2026-11-04` 记录里"替换当前残留的 `.previous.plist`"是同一现象，
说明那次替换没有真正生效。这会影响 CAS 回收是否按预期每天运行，**但本次未做
生产写操作，未进一步确认**。

---

## 6. 建议

### 6.1 判定

**可以维持启用，但不要按"已完成"结案。** 分四条：

1. **geometric-pv 普通通道 —— 有配额**阻塞**，不只是缺证据。**
   `module_steps` 已被用到 95.6%，说明 220,000 这个普通上限对"24 模块全年"
   就已经见底。更大的屋顶不会变慢，会直接掉进 expanded 分支；而 expanded 的
   准入条件极窄（单屋顶、单阵列、无遮挡、无 keepout、1×1 与 2×2 网格）。
   **结论：多阵列、有遮挡的中等规模屋顶目前没有可执行路径。** 要么抬高普通
   `max_module_steps`，要么放宽 expanded 的准入——两者都是配额决策，需要业主
   或主控按真实客户屋顶规模定，不是本次能自行决定的。

2. **geometric-pv expanded —— 可以维持启用。**
   有生产成功执行、有隔离 cgroup、有实测上界（894 MiB vs 1.2 GiB）、有完整回滚。
   缺的是 96 模块满规模证据，那是**补验**不是**阻塞**。

3. **direct-beam —— 维持启用，但在补隔离或下调上限前不推广。**
   没有 cgroup 隔离，2 M 样本任务独占单核 ≈149 s（VPS 换算），期间 HTTP/engine/genie
   全排队；`bounds_checks` 会吃掉上限的 82%。当前只跑过 680 样本，风险未兑现，
   但真实客户用满 24 行 + 大网格就会碰到。

4. **"无生产执行"这条 D 线结论必须更正**，并且要更正**统计口径**：只查
   `jobs.kind` 会漏掉所有非 `evaluate` 任务类型（生产该列只有 `evaluate` 一个值），
   正确做法是解 run 的 `manifest.context.models.task`。

### 6.2 若要降低 direct-beam 风险，两个可选动作

按成本从低到高：

- **(a) 下调 `direct_beam_visibility.max_samples`**，例如 2,000,000 → 500,000
  （VPS ≈37 s CPU，`bounds_checks` ≈10 M / 50 M）。
  注意这**不是改个 JSON 再重启**：`DirectBeamLimits` 经 `parameters()` 进入
  execution key（`direct_beam_job.py:52-64`），而 `preflight()` 把 `runtime.json`
  的哈希冻结在 `prepared.json` 里，改了就会报
  `prepared executable or configuration changed`。所以要走**完整的一次 release**：
  新 release 目录（同一份代码 + 新 `runtime.json`）→ `prepare` → `activate`（含 drain）。
  代码零改动，`runtime_sha256` 不变，只变 `execution_key`。
  生产只有 1 个 direct-beam run 且已 succeeded，旧 key 失配不构成阻塞。
  **这是最小改动，推荐。**

- **(b) 把 direct-beam 也纳入 expanded 隔离机制**。需要改 `worker_host.py`
  （把 direct-beam key 并入 `expanded_execution_keys`）与 `direct_beam_job.py`
  （提供 `execution_keys()`），属于 `planning/**` 改动 → **必须双 namespace 发布**
  （`/opt/linker-planner` + `/opt/linker-engine` 同步），并按
  `planner_release.py` 的 drain 纪律换版。工作量明显大于 (a)。

不建议的做法：给 `linker-planner-worker` 顶层加 `MemoryMax`。worker 承载普通
作业与 expanded 父进程，加顶层上限会先杀掉父进程而不是子 cgroup，掩盖不了
commit 额度问题。

### 6.3 需要先补的证据（按优先级）

1. **direct-beam 在生产上限附近的实测**：一次 2 M 样本的任务，读回
   `sample_count` / `ray_face_checks` / `bounds_checks` 与 job 墙钟。
   现有 680 样本的数据不足以支撑"配额合理"的判断。
2. **96 模块满规模 expanded 的生产实测**：现有最大是 27 模块。
   548 INDEX 的 96 模块读数是**合成 host 验证**，不是客户项目。
3. **确认 R6（launchd 指向 `.previous.plist`）是否需要处理**——CAS 回收是否
   按预期每天运行，本次未做生产写操作去验证。
4. **R2**：把 `linker-planner-http` 的 `OOMPolicy` 从 `stop` 改为 `continue`
   是否需要（HTTP 进程 OOM 时停止整个单元会让所有客户请求失败）。

**"跑过"与"按工作量验证过"之间，最大的缺口不是 direct-beam，而是普通 geometric 的配额已见底。**

### 6.4 明确不做的

- 不实际启用或变更生产配置（本轮任务边界）。
- 不动 `/opt/linker-engine` 与 `/opt/linker-planner` 的任何文件。
- 不改 `runtime.json` / `worker.json`。
- 不做 96 模块满规模的生产实跑（那需要真实客户项目或合成项目写入生产 store）。

---

## 7. 复现命令

生产只读：

```bash
# 执行器注册与限额
TOK=$(sudo grep '^GENIE_SERVICE_TOKEN=' <release>/.deploy/http.env | cut -d= -f2- | tr -d '"')
curl -s -X POST -H "X-Linker-Service-Token: $TOK" \
  -H "X-Linker-Planner-Principal-Kind: team" \
  -H "X-Linker-Planner-Principal-Subject: read-only" \
  -d '{"schema_version":1}' http://127.0.0.1:8911/planning/version

# 资源
free -m; grep -E 'MemAvailable|CommitLimit|Committed_AS' /proc/meminfo
systemctl show linker-planner-worker --property=MemoryCurrent,MemoryPeak,OOMPolicy

# 生产 run 类型分布（解 manifest，不看 jobs.kind）
sudo -u linker-planner python3 - <<'EOF'
import sqlite3, json, os
c=sqlite3.connect("file:/opt/linker-planner/state/workspace/workspace.sqlite?mode=ro",uri=True)
root="/opt/linker-planner/state/workspace/blobs"
load=lambda s: json.load(open(os.path.join(root,s[:2],s)))
counts={}
for rid, man, res in c.execute("select id,manifest_sha256,result_sha256 from runs"):
    m=load(man); t=((m.get("context",{}).get("models") or {}).get("task","?"))
    counts[t]=counts.get(t,0)+1
    # 本域真实工作量：witness 记的是实际消耗，不是估算
    if t=="prepare_geometric_pv_reference_v1":
        w=load(load(res)["dependencies"]["model.witness"])
        print(rid[:10], t, w["inputs"]["work"], len(w["modules"]))
    elif t=="prepare_direct_beam_visibility_v1":
        print(rid[:10], t, load(res)["visibility"]["sampling"])
print("--- task counts ---")
for k,v in sorted(counts.items(), key=lambda x:-x[1]): print(v,k)
EOF
```

本地测量（本次实际执行）：

```bash
cd services/engine
# 96 模块 expanded geometric
/usr/bin/time -l .venv/bin/python -m pytest \
  "tests/planning/test_geometric_pv_job.py::test_series_iv_complete_weather_worker_freezes_wiring_and_supports_energy_and_report[clear-flat-roof]" \
  -q -p no:cacheprovider
# direct-beam 全用例
/usr/bin/time -l .venv/bin/python -m pytest tests/planning/test_direct_beam_job.py -q -p no:cacheprovider
# direct-beam 上限外推（临时脚本，已回收）
PYTHONPATH=src .venv/bin/python <bench> <repo> 120
```

本域测试本轮实跑：`test_direct_beam_{index,job,visibility}.py` +
`test_geometric_pv{,_job,_witness}.py` = **38 passed in 221.60 s**（本机，含全部
`ci_expensive` expanded 用例）。

---

## 8. 证据边界

- 生产数据全部只读取得（`free`、`systemctl show`、`cat` 配置文件、只读 SQLite
  `?mode=ro`、带令牌的 `/planning/version`）。未写入、未重启、未改配置。
- 唯一一次在生产上创建文件：为测单核基准往 `/tmp` 写了一个 6 行脚本，
  运行后立即删除，本机侧同样删除。
- 本地测量只有单次采样，没有时间序列；96 模块的 644 MB 是**测试用例规模**，
  生产 894 MiB 才是该路径的真实上界。
- direct-beam 的 2 M 样本数字是**线性外推**，不是实测。实测到 1.728 M 样本。
- `launchctl print` 显示 launchd 指向 `.previous.plist`，本次只记录未处理。
