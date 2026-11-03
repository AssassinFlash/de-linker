# 548 · 2026-11-03 生产验收记录

本目录记录 #548 在本日落到生产、并从生产读回的改动。证据以生产响应为准，本地测试只作为前置。

## 1. ETR 50–125 kW 安装事实落库（4 个产品）

**来源文档**：`GW ETR-50-125kW User-Manual-EN V1.0`（215 页），`document_id`
`doc-e135c80bd4befdcd3c7e807944036da9a13c966b4c61ad40e6ff7886cf10b42f`，
`document_revision` `f802c3c76d87d6e4dc6b724b400a1ce6fe9ebcb38a3475f3e4d5dcfaffc2ba63`。
事实与页码见 `manufacturer-evidence.md` 第 9 节。

**写入前备份**（生产主机 `disable_functions` 禁了 `exec`，`wp db export` 静默失败，
必须走 mysqldump 直连，见 `tools/cutover/src/linker_cutover/backup.py:13`）：

```
cd tools/cutover && .venv/bin/python -m linker_cutover.cli snapshot --write
→ ~/de-linker-data/snapshots/db-20261103T070621Z.sql.gz
  8,104,894 B, sha256 71f00f4a2504f1f7…
```

**preview**（作用域收窄到 4 个 ETR，绕开 9 个老产品的 revision 漂移）：

```json
{"action":"preview","site":"https://de-linker.com","changes":4,
 "source_revision":"cd9e9a990e1801afee18354379e7f87831fa1f56fafe78a05411dbd6fe11fdf6"}
```

**apply**（apply 只认 receipt，不接受 `--plan`）：

```json
{"action":"apply","site":"https://de-linker.com","changes":4,
 "source_revision":"113e8ad236d47e61d7b8af920fe6e0610d146b93bb4c4e0d4de477a0b9097534"}
```

**verify**（幂等复跑）：`changes: 0`，`source_revision` 不变。

**生产读回**：`GET https://de-linker.com/wp-json/linker/v1/engineering-feed`

| id | 新 product_revision | `installation_facts.status` | 条数 |
|---|---|---|---|
| 6508 | `6d219f809af9…` | documented | 3 |
| 6509 | `3b7f8c0e00af…` | documented | 3 |
| 6510 | `5a0d03c3019d…` | documented | 3 |
| 6511 | `e06d299cdcdd…` | documented | 3 |

6508 的事实形状（其余三个同构）：

| id | basis | 页 |
|---|---|---|
| `ac-conductor` | `manufacturer_recommended_ac_conductor` | 61 |
| `protective-earth-conductor` | `manufacturer_recommended_pe_conductor` | 60 |
| `battery-cluster-conductor` | `manufacturer_model_specific_conductor` | 60 |

三个 `basis` 与 item id 正好命中引擎契约
（`services/engine/src/linker_engine/planning/installation_conductor_comparison.py:100-108`），
`conditions: []` 满足 `_source_is_current` 之外的条件项。

**影响面**：4 个产品 revision 已变，计划/报价按新 revision 取数。

**回滚**：同一 receipt `rollback`；整库可用上面的快照 `restore-snapshot`。

## 2. 未完成项（本日不宣称完成）

- 引擎对外层仍保留刻意 unresolved 的工程边界项（scenario 参数基准、模型域、DSO/TAB 签核等，
  见 #548 与 `manufacturer-evidence.md` 第 5、6 节），这些**不因本条写入而变绿**。
- 剩余 9 个已漂移产品的计划需要重新 binding，不在本条范围。

## 3. 配置器真实运行：搜索成功，前端状态门与 API 契约不一致（2026-11-03 15:5x–16:2x CST）

用真实管理员账号在生产上走了一次完整配置器流程，项目
`ETR conductor walk 2026-11-03`（`1c62e4591c1549f3b5c7dbbf2a3f22cf`）：

- 需求 200 kWp / 61.4 kWh 可用 / 100 kW 连续放电，`grid_connected`、三相；
  先 `Prepare equipment search`，再 `Save project`（revision 2），
  `Find equipment combinations` 才从 disabled 变 enabled——这个顺序是实测出来的。
- 搜索任务 `71d9d923cf374f6dab59cd4b93190fae` 在生产 **`state: succeeded`**，
  `result.search.candidates` 有内容（首个候选 1946 + 1956，4 模块 1 簇）。
  判定：**设备搜索在生产可用**。
- 但 UI 停留在 `Searching for equipment combinations…`，直到手动刷新才消失；
  刷新后 Equipment 表单不回填已保存的需求。

同一路径上发现一个真实的接口契约缺口：

- 配置器四个表单都以 `catalog.data.prepared` 作为准入门
  （`apps/planner/src/components/equipment/EquipmentSetup.tsx:309`、
  `energy/DcStorageForm.tsx:71,120`、`equipment/PlantSetup.tsx:234`、
  `NewProject.tsx:466`），
  而 `products/current` 的响应从来没有这个字段——顶层键只有
  `battery_assemblies, cable_references, compatibility_origin, dc_battery_ports,
  figure_projection_version, loaded_engine_version, loaded_source_revision,
  module_diagnostics, parallel_controller_product_ids, products, provider, publication`，
  `publication` 里也没有，所以每个客户都会看到
  `Current product data is being prepared.`，即使目录完整（85 个产品、614 份发布文档）。
- 修复：`services/engine/src/linker_engine/planning/product_sources.py` 在响应中补
  `prepared: True`（该响应只在 `publication.prepared_view(...)` 成功后才构造），
  测试断言该契约。PR #868 → main `ab368fd0b`，CI `engine` pass 5m10s。
- **部署边界（重要）**：Engine 服务已用
  `services/engine/ops/legacy_release.py prepare/activate` 发布为
  `20261103T083700000000Z-ab368fd0`；但 `planner/rpc/products/current` 由 **planner**
  服务提供，而 planner 的每个 release 里 **vendored** 了一份
  `src/linker_engine/...`（`/opt/linker-planner/releases/<sha>/src/linker_engine/planning/product_sources.py`）。
  因此生产读回仍是 `prepared: null`——必须为 planner 出一个新 release
  （`planner_source.py prepare` + `planner_release.py prepare/activate`，
  spec 形如 `{"port":8911,"prefix":"linker-planner","release":"<新路径>",
  "root":"/opt/linker-planner","schema_version":1,"start_seconds":30,
  "stop_seconds":30,"user":"linker-planner"}`，并在该不可变路径下建 `.venv`）。
  本条不宣称这一项已完成。

## 4. `prepared` 契约修复已通过 planner release 上线（2026-11-03 17:0x CST）

第 3 节的根因（引擎从不返回 `prepared`）已修复并部署，执行记录见
[planner-release.md](planner-release.md)：

- 修复 `ab368fd0b`（PR #868）经新 planner release
  `08256b932b3bec053a221c95d328152fe318859c86b5872600f518ec1c3946e6` 上线
  （activate 一次通过，current+previous 保留，health 全绿，写前已备份
  workspace.sqlite 到本机）。
- 生产读回：`POST /wp-json/linker/v1/planner/rpc/products/current` → 200，
  顶层 `"prepared": true`（发布前为 `null`）。
- UI 层（Equipment 面板不再显示 "being prepared"）待浏览器实走确认。

## 5. ETR 机型已进入生产候选；搜索评估明细与电池准入门（17:1x CST）

对第 3 节同一次搜索 run（`71d9d923…`）的深入读回：

- 10 个候选中 **6508/6509/6510/6511 全部在列**（第 6–9 名，均配电池 1958，
  5 模块 1 簇，`status: unresolved`，0 violated / 8 unresolved）——ETR 四机型
  已被生产搜索真实覆盖。
- 候选评估明细存在 planner workspace blobs（按 sha256 分片）：
  `6508+1958` 的 8 项 unresolved 为 `pv_dc_input`、`pv_electrical_topology`、
  `manufacturer_pair`、`modules_per_stack`、`battery_voltage`、`usable_energy`、
  `continuous_battery_ac_output`、`battery_discharge_path`——全部是
  已知缺证类（`manufacturer_pair` 要求 released 且无条件，51/51 都带条件；
  `continuous_battery_ac_output` feed 0/106），与本轮落库的安装事实无关，
  属 `manufacturer-evidence.md` 的 (a)/(b) 类补证范围。
- **电池准入门**：`equipment_search_space.py:49-60` 要求
  `evidence.sales_unit(pid) ∈ {battery_module, battery_system}` 才入池；
  本次 18 个电池产品全部因 `sales_unit_evidence_missing` 被排除
  （1832、2067–2070、2090、2092、2093、3611、3612、4103–4106、6519–6522）。
  注意 615-dc-figures 线给过 2090/2092 的 sales_unit，但引擎侧仍判缺证
  ——补 sales_unit 证据（文档绑定）可直接扩大候选池。
- 导体/端子结论（`ConductorManufacturerResults`）在安装阶段渲染，需在
  配置器里选中候选并确认条件后才出现；本日未走到该步，不宣称。

## 6. ETR 最后一公里：厂商导体对比在生产渲染（18:01 CST）

第 1 节落库的安装事实，已在生产配置器里走完整条消费链。操作序列来自
安装流代码审计（`installation-flow.md`），由真实管理员账号在生产 UI 逐步驱动：

1. 项目 `1c62e4591c1549f3b5c7dbbf2a3f22cf` 重新搜索
   （run `715970aa8aa4465eaeb4081745359a92`，2026-11-03 09:33:32Z），
   10 个候选含 6508–6511（第 6–9 名，配电池 1958、5 模块 1 簇）；
   采纳候选[6]（**6508 = GoodWe GW99.99K-ETR-G10**）并保存。
2. Installation routing 按审计序列补齐前置输入：
   测量源（Site measurement，精度 0.1）→ 设备实例 "GW99.99K-ETR inverter"
   （product=6508，连接点 AC grid side / Battery side）→ 回路
   "Inverter AC output"（type AC，两点都落该实例）→ 路由（经 circuit 自动带入两点）→
   导体 "AC feeder 50 mm2"（Declared cross-section 50，basis 文案）。
3. conductor instruction 下拉在 cross-section+basis 有效后出现
   **"GoodWe GW99.99K-ETR-G10 · AC conductor · p. 61"**，选中并勾确认框，
   Apply → Save project。
4. 点 `Review routes and circuit conditions`，**`Manufacturer conductor
   cross-section comparisons` 渲染**（截图 `evidence/etr-walk/etr-final-comparison.png`）：

   | 导体 | Declared | Manufacturer range | 结论 |
   |---|---|---|---|
   | AC feeder 50 mm2 | 50 mm² | **50–70 mm²** | Within the recommended cross-section range |

   展开 `Manufacturer source`：链接 `Document · page 61` →
   `https://de-linker.com/wp-content/uploads/2026/10/GW_ETR-50-125kW_User-Manual-EN_…`，
   原文引用 "Inverter AC Cable \| Multi-core outdoor copper cable Conductor
   cross-sectional area: 50mm²-70mm² • Cable outer diameter: …"。

**判定**：ETR 手册事实（p.61 AC 50–70 mm²）→ `installation_facts` 落库（§1）→
引擎 `installation_conductor_comparison` 校核 → 配置器结果卡片，全链在生产打通；
第 1–6 节构成本日 #548 的完整交付证据链。

已知未竟（输入完备性，非缺陷）：takeoff 表 `Calculated length —` +
`Extra length or its basis is missing`（导体长度需 extra length 输入，
不影响导体对比门）。UI 驱动细节与字段 id 见 `installation-flow.md`。

## §7 生产部署与三修复读回（2026-11-03 19:20 CST）

部署：`linker_cutover.cli deploy --write`（main 7e2f6502，含 PR #871 planner 资产 + PR #874 commerce 修复）；原子切换 0.018s，插件激活、present、litespeed purge 完成。**WindPress 缓存重建为后台手工步骤**（wp-admin → WindPress → Performance → Generate）：点击后缓存 mtime 1793646409（03:06）→ 1793704734（19:19），读回 `body .cky-modal{overflow:hidden}` 生效。

生产读回（有头 Playwright，视口 390×844 / 1440×900）：
- **PR #871 缺陷 2（表单回填）**：`/solution-configurator/?project=1c62e459…` Equipment 表单回填 200 kWp / 61.4 kWh / 100 kW，operating mode=grid_connected、grid phase=3 ✓（修复前全空）
- **D1（DE 390 溢出）**：`/de/mein-konto/unternehmen/` innerWidth=390、scrollWidth=390（修复前 402）、`.cky-modal` computed overflow=hidden、账户卡 grid 294px ✓
- **O2（PDP tab ARIA）**：`/product/goodwe-esa-gw3k-eha-g20-3-kw-single-phase-power-module/` 点击 "PV input" tab → aria-selected="true"、其余 tab 全 "false" ✓（5 tabs）
- PR #871 缺陷 1（stale spinner）：新 release 08256b93 实走 ETR 时 ~1 分钟无刷新出结果（b45 已记录），本次部署 planner.js ver=9397743b…（CI 构建）确认线上即该版。

已知部署管线缺口：cutover deploy 的 present 步骤只打印"去后台点 Generate"，不强制执行也不校验缓存新鲜度——违反 AGENTS §4"部署流程含缓存强制重建"。修复臂已派（见 #875 后续）。
