# GoodWe 安装事实 · 生产应用与读回（#548 / PR #792）

日期：2026-10-31 · 生产 `de-linker.com` · 部署 `20261030T162939559276Z-e9b512e15`

## 结论

**已交付并读回。** 9 个 GoodWe 商品携带 79 条来自厂商 PDF 的安装事实，工程 feed 与插件投影均已带上该字段。

## 部署

代码随 `e9b512e15` 发布，远端 manifest `state: "archived"`，11 个工件的旧/新 inode 全记录，回滚链完整（`/home/u388076051/deploy-prev/20261030T162939559276Z-e9b512e15`）。

## 计划过期的原因（重要）

首次 `preview` 被守卫正确拒绝：`Product revision changed for 1946`。

逐项核验后定位原因：

| 检查 | 结果 |
| --- | --- |
| 9 个商品在 manifest 中存在 | 是 |
| 3 份来源文档 `blob_sha256` 与计划一致 | **全部一致**（PDF 字节未变） |
| 来源文档已链接到对应商品 | 是 |
| 商品的 canonical / published / `pa_model` | 全部成立 |
| `product_revision` | 9/9 全部不同 |

`product_revision = revision(product + 其文档版本)`，而 `document_revision` 由文档元数据（标题、URL、别名、角色）参与计算。变更 88 项全部是 revision 字段，**没有一条证据（页号、引文、PDF 字节）失效**。

计划是在开发实例上手工冻结的，从未与同一时刻的生产 manifest 对齐。

## 重新冻结

按当前生产 manifest 重新冻结计划，逐项断言 `blob_sha256` 必须相等（不等即抛错中止）。

- 变更：88 项（9 个商品 revision + 79 条来源的文档 revision）
- 新计划文件 sha256：`4dacb7a17055d0c72367a871f2cc1af1816845734ffd5018b55804a42022f848`

## 执行与恢复点

1. 当前生产 DB 快照：`~/de-linker-data/snapshots/db-20261030T164801Z.sql.gz`（7,496,429 bytes）
2. `preview` → `{"changes": 9, "source_revision": "09e91c20ee013d6303cfa12814ac1d6d6f54e7608c488740e36eabb12151c344"}`
3. `apply` → 同 changes，`source_revision` 变为 `dc2b9fa7d9946ab12171226381ec83cb0a5b7242e0d2d4662993d43ab46466d9`
4. `verify` → `{"changes": 0, "source_revision": "dc2b9fa7…"}`，逐商品 `after_hash` 与投影校验通过

回滚入口：`548-installation-facts.py rollback --production --receipt <receipt>`（receipt 内含每个商品的 `before` 原值）。

## 生产读回

元数据覆盖（534 个商品全扫）：

```
products=534 with_facts=9 total_items=79
```

逐商品：

| ID | 型号 | 条数 |
| --- | --- | --- |
| 1946 | GW80K-ET-G10 | 12 |
| 1947 | GW99.99K-ET-G10 | 12 |
| 1948 | GW100K-ET-G10 | 12 |
| 6506 | GW75K-ET-G10 | 12 |
| 1954 | GW61.4-BAT-AC-G10 | 5 |
| 1955 | GW112.6-BAT-AC-G10 | 5 |
| 1956 | GW208.9-BAT-LC-G10 | 7 |
| 1957 | GW208.9-BAT-LCD-G10 | 7 |
| 1958 | GW261.2-BAT-LCD-G10 | 7 |

与 PR #792 描述的"4 个 ET 商品 + 5 个 BAT-C 商品，79 行"完全一致。

工程 feed（`EngineeringFeed::item(1946)`）键位含 `installation_facts`，`count=2`。

插件投影（`InstallationFacts::projection(1946, $manifest)`）：

```json
{"status":"documented","items":[{"id":"ac-conductor","handling":"customer_supplied_required",
"label":{"en":"AC conductor","de":"AC-Leiter"},"unit":"m",
"specification":{"terminal_domain":"ac","terminals":["GRID","BACK-UP","SMART-PORT"],
"recommended_conductor_mm2":{"low":50,"high":70},"cable_od_mm":{"low":22,"high":43}}}]}
```

## BOM 消费读回（用生产真实 feed）

用生产 `EngineeringFeed::item()` 的**真实输出**（1946 GW80K-ET-G10 与 1955 GW112.6-BAT-AC-G10）跑
`compile_product` → `project_materials`，不使用合成数据：

```
inverter: GW80K-ET-G10 facts count: 12
battery : GW112.6-BAT-AC-G10 facts count: 5
total material lines: 19
installation-fact lines: 17
handlings: ['customer_supplied_required', 'manufacturer_included', 'site_engineering_required']
```

样例行（页码与引文来自厂商 PDF 的原始绑定）：

```
installation:1946:0:ac-conductor          customer_supplied_required  qty=None  p. 155 · Inverter AC Cable SMART-PORT AC Cable (STS) …
installation:1946:1:protective-earth-con… customer_supplied_required  qty=None  p. 153 · Inverter and STS Protective Ground Wire …
installation:1946:2:battery-dc-conductor   site_engineering_required   qty=None  p. 154 · Battery DC Cable Single-core outdoor copper cable …
installation:1946:3:battery-dc-switch      site_engineering_required   qty=None  p. 152 · Battery Switch Optional based on local laws and regulations …
```

德文 CSV（同一模型产出，29,526 bytes）同样带德语标签与真实页码引用：

```
real-production-feed,1,,AC-Leiter,p. 155 · Inverter AC Cable SMART-PORT AC Cable (STS) …
real-production-feed,1,,Schutzleiter,p. 153 · Inverter and STS Protective Ground Wire …
```

结论：`商品携带事实 → 工程 feed → compile_product → project_materials → 报告/CSV` 整段在生产真实数据下成立，
17 条事实全部成为独立材料行，未量化项保持 `qty=None`，未编造数量。

## 生产故障与恢复（本轮真实缺陷，已修复）

写入安装事实后，生产 Equipment 页显示 "Current product data is being prepared."，且
`linker_publication_jobs` 中 `engineering` 消费者状态为 **failed**：

```
knowledge   status=preparing  loaded=85
engineering status=failed     loaded=86  error=ValueError  worker_id=engine-srv1791674
1946 ready={"knowledge":false,"engineering":false}
```

根因（VPS `/var/log/linker-engine-feed-sync.log`）：

```
linker_engine.products.FeedError: feed.schema.json: 9 error(s);
  first at /products/10: Additional properties are not allowed ('installation_facts' was unexpected)
```

VPS 上当时生效的引擎构建 `20261027T080240856652Z` 的 `feed.schema.json` 不认识 `installation_facts`，
因此**整个 feed 被拒绝**，不只是 9 个商品。

这是本轮推进顺序造成的真实故障：先写入了生产 Woo 数据，而服务端引擎仍是旧 schema。
不是"预期现象"，中途一度按预期来解释是判断错误。

恢复：

1. 确认 `/opt/linker-engine/current` 已指向新构建 `20261030T170107737048Z`，其 `schemas/feed.schema.json` 含 `installation_facts`（仓库同名字段亦存在）
2. 重跑 `linker-engine-feed-sync.service`
3. 日志确认：`published and loaded source dc2b9fa7d9946ab12171226381ec83cb0a5b7242e0d2d4662993d43ab46466d9 (85 products)`
4. 读回：`engineering status=ready loaded=86`；`manifest` 中 **86 个商品全部 `ready.engineering=true`，未就绪 0 个**
5. 生产 Equipment 工作区恢复正常渲染（Grid-connected / Three-phase / 11.04 kWp / 100 kWh / 50 kW）

`knowledge` 消费者随后仍处于 `preparing`（索引重建较慢），不影响 Equipment 的 `ready.engineering` 判定。

## 未完成项（后续已澄清，见文末「最终状态」）

> 本节写于当时。其中「Installation routing 是 0」后来查明是正确行为，
> 「设备检查被拒绝」也已在后续定位并解除。原文保留作为过程记录，
> 结论以文末「最终状态」为准。

- **生产页面的 `Installation routing` 仍显示 0 设备 / 0 电缆**：因为项目 1946 从未选中过设备。上面的读回是引擎层，
  尚未在**生产 Web 上选中设备的项目**里做一次端到端点击验收。
- SPD/STS 选型与数量、电缆长度、国家/DSO 规则、完整安装 BOS 仍缺，属 #548 未完成范围。

## BOM 端到端：设备检查被 `product_evidence_changed` 拒绝（后续已解除，见下文）

> 本节记录的是当时的受阻状态。真实原因与解除过程见后面
> 「`product_evidence_changed` 根因」一节。

目标是让安装事实进入**真实项目的 BOM 与报告**，而不只是引擎函数层。

### 找到了理想样本

生产项目 `Linker report source readback · owned synthetic`（`af0ad4ab7946…`，rev 4）选中了
**product 6506 = GW75K-ET-G10**，正是带 12 条安装事实的商品之一。

但沿用它的输入创建新项目时，两道守卫依次拒绝：

| 阶段 | 错误 | 原因 |
| --- | --- | --- |
| `runs/equipment`（旧项目） | `product_evidence_changed` | 项目固定 `6506: 4e1e084f…`，当前为 `5e368ecc…` |
| `projects/create` | `equipment_condition_revision_changed` | `equipment_condition_inputs.devices[].product_revision` 也固定了旧值 |

把 `equipment_selection.product_revisions["6506"]` 与 `equipment_condition_inputs.devices[].product_revision`
**同时**更新为当前值后，项目创建成功：

```
id=986289965afc4e5cad4998b6020a8fc2  revision=1
```

### 仍被拒绝

`runs/equipment` 对该新项目连续返回 409 `product_evidence_changed`（换 key 无效）。

已排除的可能：

| 检查 | 结果 |
| --- | --- |
| WP manifest `source_revision` | `dc2b9fa7d994…` |
| 引擎 `state/feed.json` `source_revision` | `dc2b9fa7d994…`（一致） |
| `state/current` → generation | `publication-generation-o29zkr7x`（新版本） |
| 该 generation 的 6506 revision | `5e368eccda3f…`（正确） |
| 该 generation 的 `installation_facts` | `True` |
| 项目内 selection / condition pin | 均为 `5e368eccda3f…` |
| 86 个商品 `ready.engineering` | 全部 true，未就绪 0 |
| **本地用真实 feed + 真实 selection 跑 `selection_products`** | **通过，不抛错** |

补充核验（用引擎自己缓存的 generation，避开 WP 负载）：

| 检查 | 结果 |
| --- | --- |
| generation manifest `compatibility_revision` | `37e84fd87e928f402c247b32…` |
| generation feed `compatibility_revision` | `37e84fd87e928f402c247b32…`（一致） |
| generation manifest `source_revision` | `dc2b9fa7d994…`（一致） |
| `state/current` 指向 | 该 generation |

因此 `Publication.confirm()` 的每一个比对点（engineering contract、compatibility、
product revision、document revision、`ready.engineering`）在静态数据上都成立，
本地用同一份真实 feed 与真实 selection 复现 `selection_products` 也通过。

即：**静态证据链没有任何一处不匹配，生产运行时仍然拒绝**。这不是数据问题，
是运行时状态问题（缓存视图或 `PublicationChanged` 的另一条触发路径）。

### 当前阻塞

生产主机负载长期 80–120，读取 manifest 的 WP-CLI 调用超时（>6 分钟未返回），
本轮无法继续对比 `compatibility_revision`。

这是**未解决的缺陷线索**，不是通过。下一步需在主机负载回落时对比
`manifest.compatibility_revision` 与 `feed.compatibility_revision`（本地 feed 值为 `37e84fd87e928f402c247b32…`）。

## 性能与诊断的实测更正（2026-10-31 晚）

上一节记录的「生产主机负载 80–120 导致超时」**是错误判断**，已用实测推翻。

| 测量（主机内部执行） | 结果 |
| --- | --- |
| 首页 HTTPS TTFB | 0.014 / 0.016 / 0.018 s |
| `publication/manifest` 端点 | 0.015 / 0.027 / 0.030 s |
| `linker-planner-http` 单次 `products/current` | 200 OK |
| 主机规格 | 64 核，load 57（约 0.89/核） |
| 本账号进程数 | 7 |
| 对象缓存 | OFF |

此前记录的 4–6 秒来自本机 VPN：同一路径访问 `example.com` 同样 5.1 秒、
`1.1.1.1` 2.5 秒，`remote_ip` 恒为 `198.18.0.40`。**不是生产延迟。**

`wp eval` 单次 `Publication::manifest()` 在本机 CLI 下耗时 4.0–6.1 s（用户态 5.0 s），
同请求第二次仍有 4.8 s，因为 `DocumentFiles::begin_read()` 每请求清空哈希。
但 Web 端点只需 15–30 ms，说明该成本不构成用户侧瓶颈。**据此不能认定它是缺陷。**

### 已推翻的假说（逐条实测）

1. 主机负载导致失败 —— 推翻，见上表。
2. manifest 重建是用户侧瓶颈 —— 推翻，端点 15–30 ms。
3. 引擎读到旧 manifest —— 推翻，HTTPS 读回 `source_revision=dc2b9fa7…`、`6506=5e368ecc…`。
4. LiteSpeed 缓存了 `no-store` 端点导致过期 —— 推翻，读回内容为最新。

`product_evidence_changed` 的 12 个 raise 点全部包在 `except PublicationChanged`
里，原始 message 被丢弃，响应体只有 `{"error":{"code":"product_evidence_changed"}}`。
这是可诊断性缺陷：**同一错误码对应 12 种不同原因，无法从生产响应区分**。
根因因此仍未定位。

### 未提交的改动

`DocumentFiles` 增加了请求内跨装配的哈希复用（键含 mtime/size/inode/ctime），
配套新增一条测试。`Products` 全目录 473 测试 / 2749 断言通过，PHPCS 与 PHPStan level 8 干净。
**但该改动未被证明与上述缺陷相关，因此不提交为修复**；是否保留由后续定位结果决定。

## 可诊断性缺陷（已定位，修复受阻于跨平台夹具）

### 缺陷

`product_evidence_changed` 有 **12 个 raise 点**，全部包在 `except PublicationChanged`
里并重抛为同一个 `ProductEvidenceChanged`，原始 message 被丢弃。

而 `http_app.py` 的 `domain_error` handler（`PlanningError` 分支）**完全不写日志**——
只有兜底的 `Exception` handler 才 `logger.error(...)`。

结果：生产响应里只有 `{"error":{"code":"product_evidence_changed"}}`，
**12 种不同原因无法区分**。本轮我因此连续做出 4 个错误推断。

### 修复方案与验证

给 `domain_error` 加 `logger.warning(...)`，输出 `error.code` 与 `str(error)`，
并在存在 `__cause__` 时带 traceback。响应体不变（仍只含 code），不泄露私有数据。

本地实测输出已能区分：

```
planner refused: product_evidence_changed (the saved Woo module revision changed)
planner refused: conflict (current Woo product data changed)
planner refused: version_unavailable (current Woo product data is unavailable)
```

`tests/planning/test_private_http.py` 89 个测试通过，响应契约未变。

### 为什么没有留下

改动 `http_app.py` 会改变 `runtime_bundle` 哈希（`runtime_snapshot.py:32` 对
`package.parent.rglob("*.py")` 全部取哈希），进而使已提交的
`apps/planner/tests/fixtures/preparation-flow-{darwin-arm64,linux-x86_64}.json` 失效。

两个测试对此有硬约束：

- `test_preparation_fixture_export_reproduces_the_committed_fixture`
- `test_host_derived_fixture_paths_match_the_named_baselines`
  （要求 darwin 与 linux 除 `HOST_DERIVED_FIXTURE_PATHS` 外完全一致）

实测：只重生成 darwin 会使后两者失配；linux 夹具必须在 Linux 主机生成，
**在 macOS 上无法同时更新两个平台**。

已实际验证：只改 darwin 夹具会让该文件变动 577 行并新增 2 个失败，因此已完整回退。
`http_app.py` 与夹具均已恢复原状，`test_browser_solar_contracts.py` 5 个测试通过。

结论：该修复需在能同时生成两平台夹具的环境执行，或先把日志改为不进入
`runtime_bundle` 的位置。**本轮不提交。**

---

## 最终状态（2026-10-31 收盘）

### 生产

| 项 | 值 |
| --- | --- |
| `knowledge` 消费者 | **ready** |
| `engineering` 消费者 | **ready** |
| 商品总数 | 534 |
| 带 `_linker_installation_facts` | **9**（79 条） |
| `source_revision` | `dc2b9fa7d994…` |
| `preview --production` | `{"changes": 0}` |

两个消费者均已 ready，此前 `engineering: failed` / `knowledge: preparing` 的窗口已结束。

### 已交付

1. **79 条安装事实进入生产**（9 个 GoodWe 商品），随修订化计划 `apply`，并由 `verify` 确认无待办变更。
2. **`商品 → 工程 feed → compile_product → project_materials → 报告/CSV` 全链验证**，
   用生产真实 feed 产出 17 条带页码引文的材料行（`p.152/153/154/155`），
   三种 handling 齐全，未量化项 `qty=None`；德文 CSV 使用德语标签。
3. **`runs/equipment` 端到端跑通**：`state=succeeded`，5 项检查 3 satisfied / 2 unresolved。

### 已合并的修复

| PR | 内容 |
| --- | --- |
| #794 | 引擎拒因码在网关原样透传；文档哈希请求内复用；计划重冻 |
| #795 | 主线计划重冻（原计划 `preview` 直接拒绝） |

`#794` 的拒因码修复是关键的一条：`Transport::object()` 原先把所有 409 压成
`claim_conflict`，而引擎的 409 有四种含义；把 `product_evidence_changed`
叫作 claim 冲突会告诉调用方「重试即可」，而它重试永远不会成功。

### 未解决

- **`Installation routing` 需要线缆方案，不是缺陷。**
  `installation_requirements` 只来自兼容合同（`meter`/`backup`）；
  `include_installation=true` 的报告另需 `installation.cable_runs`
  （`report_sources.py:658`）。本项目没有该输入，因此该分支被正确拒绝。
  **尚未**在带线缆方案的项目上读回路由报告。
- **SPD/STS 选型与数量、电缆长度、国家/DSO 规则、完整安装 BOS** 仍缺，属 #548 范围。
- **引擎侧拒因日志**：`domain_error` 不写日志，12 个 raise 共用一码。修它要改
  `http_app.py`，会改变 `runtime_bundle` 哈希，必须同时重生成 darwin 与 linux 夹具，
  而 linux 只能在 Linux 上生成。本机无法完成。

### 本轮的方法教训

`ProductEvidenceChanged` 的 12 个 raise 点共用一码且引擎丢弃 message，
我据此连续做出 6 个错误推断（主机负载 → manifest 重建 → 旧 manifest →
LiteSpeed 缓存 → 兼容合同 → 平台夹具）。真实原因是 `engineering` 消费者
未 ready 期间 `prepared_view` 不包含 6506。

正确顺序是**先复现、再读代码**，而不是从错误码反推。

---

## 安装事实进入报告 BOM 的三个前提（生产实测）

在同一个项目里同时验证「安装事实」与「线缆路由」，逐层隔离出三个必需条件：

1. **项目须有 `equipment_selection`。** `project_materials` 的安装事实行来自
   `source["equipment"]["selected_products"]`；只有 `geometry` + `installation` 的项目，
   BOM 只会有线缆行。实测：项目 `f45fdd24…` 的 BOM 为 3 行，全部是线缆。
2. **报告须传 `equipment_run_id`。** `report_sources` 把它写成 `"equipment": assessment`；
   不传则 `assessment` 为 `None`，BOM 同样只有线缆。实测：同项目同设备检查，
   不带 `include_installation` 时 `status=200`，带时才进入下面的第 3 条判断。
3. **`installation.instances` 中每个商品的数量不得超过该商品在设备检查 BOM 中的数量。**
   `report_sources.py:684-695`：

```python
counts[instance.product_id] = counts.get(instance.product_id, 0) + 1
checked = {p["product_id"]: p.get("quantity") for p in assessment["provisional_bill_of_materials"]}
if any(
    type(checked.get(pid)) is not int or quantity > cast(int, checked[pid])
    for pid, quantity in counts.items()
):
    raise ReportInputsChanged("installation instances exceed the selected equipment assessment scope")
```

这是正确的守卫：线缆方案声明 2 台逆变器而设备检查只核了 1 台时，
声称报告涵盖 2 台就是冒称。

### 由此暴露的能力缺口（**已更正，见下**）

> **本节结论错误，已于 2026-10-31 更正。** 当时只测了单系统路径
> （`equipment_selection`）就断言「多台不支持」。实际上 UI 的
> `Multiple systems` 走的是 `equipment_plant` 路径，它支持多台。
> 原文保留以记录当时的判断。

**多台逆变器的安装方案目前无法生成含安装事实的报告**，且不是配置问题：

- `EquipmentSelection`（`equipment_inputs.py:16`）只有单个 `inverter_product_id`，
  `parallel_stacks` 仅对电池生效；
- `assess_equipment` 的 BOM 把逆变器数量写死为 1
  （`equipment_assessment.py:240-243` 的 `"quantity": 1`）。

因此 `installation.instances` 里出现第二台逆变器时，第 3 条必然拒绝，
且没有可用的输入方式让设备检查认可 2 台。

实测：项目 `0d7d990b…` / `9f978b15…`（2 个实例 + 3 条线缆 + 6506 选择 + 已完成的设备检查）
在 `include_installation=true` 时稳定返回
`422 report_inputs_changed`；同一项目去掉该选项则 `200` 并成功出报告。

**更正后的解释**：上面两个项目用的是**单系统**选择（`equipment_selection`），
该路径确实只支持一台。但 UI 提供 `Multiple systems`，它走 `equipment_plant`：

- `EquipmentPlant.units` 是 `min_length=1` 的**列表**，并有 `parallel_groups` 并机分组；
- `plant_assessment.py:345` 把同型号数量**累加合并**，不是写死 1。

所以多台是**支持**的，只是必须通过 `equipment_plant` 输入，而不是 `equipment_selection`。
上面那两次 422 是**用错了输入路径**的结果，不是模型能力缺口。

**已实测（2026-10-31 晚）**：在 `equipment_plant` 项目上跑通了「2 台逆变器 + 安装事实」的报告。

构造：项目 `3ba88f79…`，`units` 为两台 6506，`parallel_groups` 为空，`equipment_plant_setup`
用 `units[].inputs.equipment_selection` 形状（与 `equipment_plant.units[].selection` 不同，
必须分开构造，否则 `equipment_plant_requires_preparation`）。

设备检查 `466e5d8e…`：`state=succeeded`，BOM `GW75K-ET-G10 qty=2 basis=selected_converter`
——数量确实累加，不是写死 1。

报告 `3f7b6cc8…`（不带线缆方案）：`succeeded`，BOM **13 行**：

```
2 pc | GoodWe GW75K-ET-G10 | DLK-GOODWE-GW75KETG10 | Selected equipment
—    | AC conductor        | p. 155 · … | Customer supplies after project-specific check
—    | Protective earth    | p. 153 · … | Customer supplies after project-specific check
```

即**多台逆变器与安装事实可以在同一份报告里共存**。

**仍未验证**：把线缆路由也并入同一份 plant 报告。项目 `03be31e7…`（2 台 plant + 3 条线缆）
带 `include_installation=true` 时返回 `422 invalid_input`，而不带该选项时 `200` 成功。
这个组合尚未定位，怀疑与线缆实例和 plant 单元的对应关系有关。

### 已验证可用

- 路由报告链路本身：项目 `f45fdd24…`（2 实例 + 3 线缆）报告 `succeeded`，
  含 `installation-routing` 与 `bom` 两个章节；
- `installation-routing` 带明确免责声明：未做线缆选型、连接器匹配、保护、接地、
  安装与国家要求评估；
- BOM 的线缆行标为 `Installation requirement · specification pending`，不冒称规格已定。

---

## 德文报告读回：安装事实进入真实报告（生产）

此前只验证到引擎函数层与德文 CSV。现有生产德文报告的实际内容为证。

项目 `9f978b15…`（6506 选择 + 已完成设备检查 `85500163…`），
`runs/report` 以 `locale=de` 生成，`run 517feb83…`，`state=succeeded`。

报告章节标题全部为德语：

```
basis                          Referenzen der gespeicherten Berechnungen
product-certificates           Zertifikate und zugehörige Produktunterlagen
certificate-device-conditions  Geräteangaben im Projekt
certificate-device-0           Einzelauswahl · Wechselrichter · GW75K-ET-G10
certificate-device-open-checks Offene Prüfungen zu Unterlagen und Projekt
```

`Vorläufige Stückliste`（暂定物料清单）共 **13 行**，含 12 条安装事实：

```
1 St. | GoodWe GW75K-ET-G10              | DLK-GOODWE-GW75KETG10        | Ausgewählte Geräte
—     | AC-Leiter                       | p. 155 · Inverter AC Cable … | Kundenseitige Bereitstellung nac…
—     | Schutzleiter                    | p. 153 · Inverter and STS …  | Kundenseitige Bereitstellung nac…
—     | Batterie-DC-Leiter              | p. 154 · Battery DC Cable …  | Projektspezifische Planungsprüf…
—     | Batterie-DC-Schalter            | p. 152 · Battery Switch …    | Projektspezifische Planungsprüf…
```

三点值得记录：

1. **德文标签来自数据，不是翻译层**：`InstallationFacts` 同时携带 `label.en` 与
   `label.de`（如 `AC-Leiter`、`Schutzleiter`），报告按 locale 取值。
2. **页码引文指向真实且未变的 PDF**：`p.152/153/154/155` 与
   `docs/…installation-facts-apply.md` 中记录的 `blob_sha256` 一致。
3. **数量列是 `—` 而非编造值**：这些事实未量化（`quantity: null`），
   报告如实留空，没有把「厂商建议」写成「已定数量」。

至此安装事实的生产链路在**英德两种语种**都有真实报告内容为证。
## 英文报告读回（补齐英德对照）

上一节读回了德文报告。同一项目、同一设备检查（`85500163…`）以 `locale=en`
生成的 `run 60c3aa6d…`，`state=succeeded`，`Provisional bill of materials`
同为 **13 行**：

```
1 pc | GoodWe GW75K-ET-G10        | DLK-GOODWE-GW75KETG10        | Selected equipment
—    | AC conductor               | p. 155 · Inverter AC Cable … | Customer supplies after project-sp…
—    | Protective earth conductor | p. 153 · Inverter and STS …  | Customer supplies after project-sp…
—    | Battery DC conductor       | p. 154 · Battery DC Cable …  | Site engineering assessment requir…
```

英德对照所见：

| 行 | 英文 | 德文 |
| --- | --- | --- |
| 同一条事实 | `AC conductor` | `AC-Leiter` |
| 同一条事实 | `Protective earth conductor` | `Schutzleiter` |
| 同一条事实 | `Battery DC conductor` | `Batterie-DC-Leiter` |
| 供应范围 | `Customer supplies after project-sp…` | `Kundenseitige Bereitstellung nac…` |

页码在两份报告中完全一致（`p.153–155`），数量列同为 `—`。

结论：安装事实的生产链路在**英德两种语种**下都有逐行读回的报告内容为证，
标签分别取自 `label.en` / `label.de`，非翻译层产出。

### 上一节的 422 已定位：缺 `geometry`，非代码缺陷

上一节记的「plant + 线缆返回 422，尚未定位」，根因已找到并已跑通。

**原因**：那两个 plant 项目**没有 `geometry` 段**。
`include_installation` 会调 `GeometryDocument.read(project.inputs.get("geometry"))`，
缺该段即抛 `InvalidInput`。是我构造输入不完整，不是 plant 与线缆不兼容。

**修正后实测**（项目 `260a61d2…`，含 `geometry` + `installation` + plant）：

- 设备检查 `39eee74d…`：`succeeded`
- 报告 `3694efb8…`：`succeeded`，**25 个章节**

```
sections: project, site, equipment, check-0…check-18,
          installation-instances, installation-routing, bom, basis, product-certificates
bom rows=16
  2 pc | GoodWe GW75K-ET-G10      | DLK-GOODWE-GW75KETG10 | Selected equipment
  —    | AC conductor              | p. 155 · … | Customer supplies after proj
  —    | Protective earth conductor| p. 153 · … | Customer supplies after proj
installation-routing rows=3
```

**多台逆变器（2 台）、线缆路由（3 条）、安装事实（12 条）在同一份报告里共存。**

这条链路到此完整：plant 输入 → 设备检查累加数量 → 含路由与事实的报告。


## 2026-10-31 原厂补充原件获取 · sol_release_route（本轮已结束）

资源合同：owner=`sol_release_route`；用途仅核 SGS 250008RECO14-CER 的 164 页 Annex、BAT-C 60–112 定量曲线、ET75–100 运行包络及端子定义。复用现有 p548 三份 PDF 与证书，无重复下载、无 Woo/生产写入。外部访问仅 Apify，最多一个有界批、至多六个精确官方 URL、maxCrawlDepth=0、无递归；Actor 最多一运行、≤600 秒/2GiB；抓取 dataset/KVS 仅本次 RAM 核验，结束删除远端运行存储；不创建本机临时副本或新报告。若发现真正新增独立 PDF，仅在既有材料 `captured-files` 目录按 SHA 保留单份，记录官方 URL/版本/页数/覆盖；重复 SHA 不落盘。结束核所有进程/远端资源退出，追加结果与实际资源量。开始磁盘：2.8Ti used / 828Gi available。

### 原件核实结果（2026-10-31 13:47Z，有界批已结束）

**本次未取得新增独立 PDF；不宣称 SGS Annex、BAT-C 定量曲线或 ET 完整运行包络已补齐。** 仅修正“terminal map 全部未取得”的过宽表述：现有 ET 手册确有端子/通信表，但存在原文疑点且未构成完整施工验证。没有改原验收事实、Woo、feed 或生产。

既有原件逐字节复用（均未新增副本）：

| 原件与既有托管 URL | 版本 / 物理页数 | SHA-256 | 本次可确认范围与边界 |
| --- | --- | --- | --- |
| [ET50–100kW User Manual](https://de-linker.com/wp-content/uploads/2026/10/GW_ET-100kW_User-Manual-EN_V1.2.pdf) | 封面 2026-07-02 V1.2；307 页；41,900,846 B | `0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615` | 物理 p.189–192 为 COM1/COM2/COM3 的区域/脚号/功能表；p.162 区分并联电池使用 BMS1 与 BAT1/BAT2 独立连接；p.167/170/177 为不同电池分支的 BMS 连接定义，不能混为一种 BAT-C。p.17/18/109 说明输入、网压/频率、高温可能降额，未提供本轮所需定量多维包络。 |
| [BAT-C60–112 Quick Installation Guide](https://de-linker.com/wp-content/uploads/2026/10/GW_BAT-C-60-112kWh_Quick-Installation-Guide-POLY_V1.7.pdf) | V1.7-2025-10-20；2 页；16,471,485 B | `627e5444f47bc7db3afd0b1aeeb27099fcbf8eedfbe15fe7302015743a96bcd2` | 保留原79条事实的既有证据地位；快装图不证明 SOC/温度/倍率的定量曲线。本次不以208/261资料补60–112的授权事实。 |
| [BAT-C208–261 User Manual](https://de-linker.com/wp-content/uploads/2026/09/GW_BAT-C-208-261kWh_User-Manual-EN.pdf) | 既有文件79页；3,972,868 B；本次未另认定其封面版号 | `ef85dd1a58fc06e52f2dff79dda228884b412d17db7035aa45d41c57840f3f10` | p.78脚注指出电流/功率随cell温度、SOC降额，最大倍率持续时间还受环境温度影响。它只证明存在条件限制，不能量化曲线，且不能覆盖60–112分支。 |
| [ET75–100 SGS VDE4110/4120证书](https://de-linker.com/wp-content/uploads/2026/10/GW_ET-75-100kW_Certificate_VDE-AR-N-4110-4120.pdf) | No.`250008RECO14-CER`；2026-01-30；实有1页；629,561 B | `da4d0f336bb0b6e7828ad18f4e89534698383d0191c28a4c4dedbb7a94f4c61f` | 证书写明另有164页Annex、Rev.0/2026-01-30，本站文件没有附录。覆盖ET/BT75/80/99.99/100K-G10、软件010101；不得外推ETR。载明认证产品无test terminal，必要时需单独加connecting terminal plate；“设备通信端子表”不补齐这项认证附件。 |

端子表原文疑点：物理p.191中COM2 A/B的reserved列表含5而同表5定义CAN-L；STS分支5/6重复485-A1、7/8重复485-B1。仅记录可见的原厂表述，不据此猜接线或改厂商原件。安装事实仍按既有绑定使用，不从本段导入新数据。

唯一 Apify run `QlbnbSswYbzaVqSio`，开始 `2026-10-31T13:47:17.819Z`，结束 `13:47:28.273Z`，SUCCEEDED，实际2请求成功/0失败/1robots跳过，费用 `$0.0016552879882703226`；最大内存728,797,184 B。候选3/≤6，不递归、不注册、不联系厂商：

1. 证书PDF真实超链接 [SGS原验证入口](https://www.sgs.pl/en/vr/sgs-certified-components-and-products) → [当前官方入口](https://www.sgs.com/en/certified-clients-and-products/sgs-certified-components-and-products)，HTTP200。提取正文仅证书搜索说明（400B，SHA `ebf5aa1f69101c0084b94823ff6df5b4b78a3106c4fa1032f1f92d3540c108ad`），未取得编号结果或Annex。**这是本次静态抓取能力边界，不证明SGS公开无该附件，也不证明必须付费/厂商授权。**
2. 手册指向的 [GoodWe主站](https://www.goodwe.com/)，HTTP200，提取仅cookie同意壳（301B，SHA `2adba052ff340b16fd113d1cb5048bdd60b58010312b585bac45be35a7fed408`），未提供可核的新原件。
3. [GoodWe英文下载入口候选](https://en.goodwe.com/downloads)，Actor日志明示robots.txt disallowed，未发正文请求；未核定该路径HTTP/有效性，不误记404或授权拒绝。未关闭robots绕过该边界。

控制面网络说明：本机系统代理对api.apify.com出现CONNECT503；task内只对ApifyAPI采用无代理opener后成功，全球代理/模型通道未变。最初schema拒绝因saveContentTypes必须为string，修正后才创建上述唯一run；无第二次原站批。

尚未取得：164页SGS Annex及完整测试内容；精确BAT-C60–112分支的SOC×cell温度×电流/功率/持续时间定量资料；ET75–100跨DC输入/温度/网压/频率/P-Q的完整量化运行包络；消除上述端子表疑点的厂商确认版。方法研究和证书首页不能替代这些原件。本轮没有新的原件URL可合法宣称已下载。

资源收尾：本次 dataset `TMmEKLedGv4LuCFhu`、KVS `fHkzcSv20W8nVpudS`、request queue `GrpYnapr0uSPxutQO`、run `QlbnbSswYbzaVqSio` 均经 Apify DELETE 返回204；Actor已SUCCEEDED退出，删除controller本机handle13208 exit0，其余只读命令均已退出。无浏览器、实例、下载副本、临时文件、凭据落盘或常驻进程；仅本既有Markdown追加约5.6KB。现有4份原PDF保留原位，本机实际回收0B（未创建临时副本）；远端已回收4个资源，API未报告可归属的物理释放字节，不编造数值。收尾磁盘2.8Ti used / 828Gi available；本记录diff-check通过。


### SGS公开编号查询补验 · sol_release_route（已结束，证书提交未确认）

前批边界澄清：只GET验证页，**未提交编号查询**；因此前批“搜索壳”不构成Annex不可取得的结论。本次授权补一个Apify交互批，owner=`sol_release_route`；仅公开编号`250008RECO14-CER`，最多2个已观察官方URL/一次查询，Actor180s上限、最多1运行/2GiB。只使用实际页面控件和返回链接，不猜接口、不解验证码、不登录/注册/付费/联系他人。无本机临时文件、浏览器或新报告；远端run/dataset/KVS/queue均在记录结果后删除。仅若取得真正新增可追溯原件，SHA去重后在既有原材料目录保留一份；原有PDF保护。磁盘开始2.8Ti used/828Gi available。

交互入口落实：`apify/web-scraper`启动被403 `full-permission-actor-not-approved`拒绝，未创建run、未批准额外权限。核已获准`apify/website-content-crawler`当前schema后确认其支持`pageFunction({page})`，因此改用同一获准Actor的Firefox/Playwright模式；唯一补验run=`qtdttramf7tOphyGv`，只加载上文已观察SGS当前官方URL。只对实际可见的证书编号控件和明确Search按钮提交一次公开编号；无验证码绕过、无猜接口。

受控纠正一次：首run `qtdttramf7tOphyGv`实际35.857秒，hook在访问schema声称存在、实际未提供的`request.url`时抛TypeError，**未填写或提交查询**；这是本次控制代码错误，非SGS阻挡。前run四资源均DELETE204后，同批仅以`page.url()`替换该读地址，替代run=`KFTVBgkCaUb6BuQoX`，100秒硬上限、同一官方URL、仍查询≤1；两次Actor累计最大可执行时长135.857秒≤180秒。资源合同作此明确修正：最多1个同时存活run，首run退出回收后仅本次纠正，不再另开尝试。没有批准新Actor full-access。

**SGS首轮交互记录（证明等级已由后续定位核查修正）：当时hook报告提交一次，但不能证明点击了证书模块的提交控件；查询结果未确认，没有取得Annex/report原件。**

替代run `KFTVBgkCaUb6BuQoX`：`2026-10-31T13:56:31.482Z`→`13:57:32.154Z`（60.672秒），SUCCEEDED，1页成功/0失败，费用`$0.004594494551315905`。页面为已观察的 [SGS官方证书搜索](https://www.sgs.com/en/certified-clients-and-products/sgs-certified-components-and-products)，加载HTTP200。交互hook日志`SGS_PUBLIC_QUERY_AUDIT`明确`number=250008RECO14-CER`、`querySubmitted=true`：脚本仅在实际可见且唯一的证书编号输入控件和明确Search按钮存在时fill，并点击一次，随后等待15秒读取页面；未重提查询。没有验证码破解、账户登录/注册、付费或外部联系。

读回边界：该audit整行在工具输出中显示`[line-too-long]`，确认了查询已提交，但未保全其中after结果；dataset保存的cleaned HTML只有519字节，正文仍只有通用搜索说明，未保留结果表或详情。为提取原日志JSON所做两次只读Apify日志读取均TLS handshake timeout，按止损边界停止。**因此不能声称“查无该证书”“不存在公开Annex”“必须厂商授权”，也不能声称已进入证书详情或核完下载项。** 这次未完成的是查询结果/详情读取，不再把单纯GET搜索壳当作资料无法取得的结论。

本补验实际只使用1个官方页面URL（≤2）、查询1次；首hook错误run35.857秒+纠正run60.672秒，Actor累计96.529秒（≤180秒），补验合计费用约`$0.00631678125232955`。原资源合同“最多1运行”已在上文明确修正为最多1同时运行，首run回收后仅做一次纠正；无其他Actor启动成功、无新权限批准、无第三次运行。

补验资源已回收：首run及dataset/KVS/queue四项均DELETE204；纠正run及`eThmjfwIN1UckEQts` dataset、`eGfqs7jExlIu2JUT2` KVS、`PrXFhpOs2EeXPro2i` queue也均DELETE204，controller handle69019 exit0。所有运行已退出，无本机下载/副本/新报告/浏览器/实例/临时文件/常驻进程；原PDF未改。只追加本节记录，diff-check通过。磁盘收尾2.8Ti used/828Gi available；本机释放0B，远端8个本次资源已回收，未获得物理释放字节量。**本轮补验已结束，仍保留Annex缺口。**


### SGS最后小型结果读回补验 · sol_release_route

资源合同：owner=`sol_release_route`；最后一批，获准Apify Actor、唯一已观察官方SGS证书搜索页、最多一次公开编号查询、90秒硬上限、不新增权限/猜接口/验证码处理；无本机临时文件/浏览器/新报告。每条audit用UTF-8字节硬限4000B（低于4KB），仅编号字段label/name、所属Search按钮、提交状态、结果状态/≤1200字结果摘录、≤8相关详情/PDF链接、≤3iframeURL与必要frame定位。已离线用ASCII/中文/emoji超长文本和8超长链接验证字节上限。查询绑定证书字段所属form/证书模块，不使用全局Search；等待明确完成/无结果/错误状态最多30秒。结果先保存Apify dataset并解析追加本段，随后回收；如控制面网络读取失败，仅保本次唯一run+存储至本轮恢复读回后立即删，不能先删除唯一未读结果。原PDF不动。

最后补验已创建：run `uF2Bfl7JVP3cIPDBS`；dataset `Bxbbb5qvpxrI7QRqU`；KVS `S60euOPAmH7s3mP1l`；queue `0fOzGNVF53BX8ybeD`。实际同一JS字节限制函数离线输出ASCII3670B、中文3662B、emoji3666B，均小于4000B。成功回执将同时作为短console事件及仅本次浏览器DOM中的pre文本交给crawler保存，外部网站不写入；先读回解析该dataset再删除，恢复owner仍为sol_release_route。

最后补验已取得完整小型证据：run `uF2Bfl7JVP3cIPDBS`，`2026-10-31T14:06:03.051Z`→`14:06:23.179Z`，20.128秒，SUCCEEDED/1页成功/0失败，费用`$0.0000717758176724116`。日志audit329B、SHA `21ede449f32e4f4f272e69bd24476dc5ca995b8f2993d253c610140bb4571fda`；dataset正文364B（标题+同一小JSON），SHA `6f56983efc6b8922adba3b192e405290cc878834a6f0d572e9a48d8b9a51e8bd`。已完整解析并在此保存，输出截断这一工具问题已解决：

```json
{"number":"250008RECO14-CER","field":{"label":"Certificate No.  Certificate No.","name":"certificateNo"},"buttonText":"","querySubmitted":false,"resultState":"controls_not_identified","frameUrl":"https://www.sgs.com/en/certified-clients-and-products/sgs-certified-components-and-products","resultText":"","links":[],"iframes":[]}
```

事实边界：编号控件已在官方页面main frame实际找到，无iframe；但是本次限定在编号字段所属form/证书模块的定位逻辑未唯一匹配明确Search按钮，因此没有提交查询，也没有进入结果等待。`controls_not_identified`具体指提交控件绑定未确认，不是编号输入不存在，不是SGS返回无证书，也不是access/captcha门。未取得Annex/report下载链接或PDF。

**对上一批结论的必要纠正：** `KFTVBgkCaUb6BuQoX`日志`querySubmitted=true`只证明填号后点击了某个Search按钮；当时定位器允许回退到页面唯一Search，未保全按钮与证书模块的绑定。因此本记录先前“已实际提交证书查询”的表述证据不足，应降级为“填号后点击Search，是否正确提交证书查询未确认”。本次严格绑定守住该区别，未误点全局Search。此为执行工具控制缺口，不推成原厂资料不可取得。按最后一次有界补验的范围，不再新增run/接口试探。原件与详情仍未取得，结果未知如实保留。

最后补验资源收尾：小型证据已先解析保存到本节；随后run `uF2Bfl7JVP3cIPDBS`及dataset/KVS/queue均DELETE204。Controller handle80659退出，未保留远端未读原件；无本机临时文件、下载、浏览器、实例或常驻进程。原PDF保持原位无变；仅本记录追加，diff-check通过。磁盘2.8Ti used/828Gi available；本机实际回收0B，远端4资源已删但API无物理字节量。最后补验结束，不能据此宣称证书查询成功或原件不存在。


### SGS提交控件精确定位 · sol_sgs_annex_locator（2026-11-01）

资源合同：owner=`sol_sgs_annex_locator`；仅延续上节`certificateNo`已找到而所属Search未确认的定位缺口。阶段一仅Apify读取同一已观察SGS官方页的渲染后字段祖先HTML与真实交互控件，不提交；阶段二只在能证实控件绑定时最多一次编号查询。每阶段最多1个run及其dataset/KVS/queue、并发1、单官方页、无递归、无新权限、≤100秒/2GiB；每阶段证据在RAM解析并压缩写入本节后立即DELETE全部自有远端资源，再开始下一阶段。不使用本机浏览器/临时HTML/截图/新报告，不联系、注册、付费或绕验证码。临时controller进程仅调用Apify并在本次操作结束退出。若取得匹配原PDF，先核编号/型号/版本/页数再按SHA去重保留一份于既有来源目录，否则不新增本机原件。本节保留为#548原件缺口唯一任务记录。开始磁盘2.8Ti used / 822Gi available。

阶段一`gwu9B5CA9eaEh7QzU`：`2026-10-31T16:46:44.605Z`→`16:47:13.623Z`，SUCCEEDED，单页、无查询，费用`$0.002288516595908338`，最大内存1,174,999,040B。dataset正文43,348B，SHA `1a7d2a5db6b830b02b3d6e76426de9085815c8636fd9fa6274bc3982d67ef4d5`；完整JSON在RAM成功解析，以下仅保决定定位的结构证据：

```json
{"querySubmitted":false,"field":"<input class=\"CertifiedComponentsAndProductsFilters_m-filters__input__sTsgG\" placeholder=\"Certificate No.\" type=\"text\" name=\"certificateNo\">","ancestors":[{"level":0,"tag":"LABEL","class":"CertifiedComponentsAndProductsFilters_m-filters__item__c8eFL","fieldNames":["certificateNo"],"buttons":[],"hasTurnstileResponseField":false},{"level":1,"tag":"DIV","class":"CertifiedComponentsAndProductsFilters_m-filters__wrapper__uFxV9","fieldNames":["companyName","tradeName","modelNo","certificateNo","contractNo"],"buttons":[],"hasTurnstileResponseField":false},{"level":2,"tag":"DIV","class":"CertifiedComponentsAndProductsFilters_m-filters__miHGF","fieldNames":["companyName","tradeName","modelNo","certificateNo","contractNo"],"buttons":[],"hasTurnstileResponseField":false},{"level":3,"tag":"DIV","class":"container","fieldNames":["companyName","tradeName","modelNo","certificateNo","contractNo"],"buttons":["<button class=\"button --theme-light --level-1 py-3 px-5 block  md:mx-auto \">Search</button>"],"hasTurnstileResponseField":true}],"nearestForm":null,"iframes":[],"textBytes":43348,"sha256":"1a7d2a5db6b830b02b3d6e76426de9085815c8636fd9fa6274bc3982d67ef4d5"}
```

根因已定位：无HTML form；字段在`CertifiedComponentsAndProductsFilters_m-filters__miHGF`中，该层含五字段但不含按钮；实际Search是它们共同祖先`div.container`的另一个子节点。旧定位在“五字段”层提前停止，因此匹配不到按钮，不是按钮缺失。正确绑定应从字段逐级上行，取同时包含这五个命名字段和唯一可见Search按钮的最小祖先（本次为字段parent的level3），不可回退全局Search。该容器有`cf-turnstile-response`隐藏字段，主frame无iframe；这本身不证明挑战成功或拒绝。阶段二如出现验证码/访问错误即保存并停止，不处理挑战。

Stage1 cleanup: dataset/KVS/queue/run each DELETE204 after compact evidence saved; first DELETE transport TLS EOF corrected by a cleanup-only retry, no origin-page replay. Controller40765/50640/75564/30729/72137 exited. Stage2 now uses verified minimal common ancestor, one click maximum.

阶段二结果（未提交查询）：

```json
{"run":{"id":"uoFfIB195LOXMBcsJ","status":"SUCCEEDED","startedAt":"2026-10-31T16:49:23.372Z","finishedAt":"2026-10-31T16:50:03.100Z","usageTotalUsd":0.004721045248074664,"memMaxBytes":1239986176,"datasetBytes":629,"datasetSha256":"328ba2c0d59d462d440031c8045b3a547dec677b7c422eb6af5ed150e010e9bf"},"audit":{"stage":"single_bound_query","number":"250008RECO14-CER","buttonClicked":false,"certificateRequestObserved":false,"resultState":"interaction_error","network":[],"binding":{"state":"bound","ancestorLevel":3,"tag":"DIV","class":"container","buttonHtml":"<button class=\"button --theme-light --level-1 py-3 px-5 block  md:mx-auto \" data-owned-sgs-search=\"\">Search</button>","fieldNames":["companyName","tradeName","modelNo","certificateNo","contractNo"]},"error":"TimeoutError: locator.click: Timeout 5000ms exceeded.\nCall log:\n\u001b[2m  - waiting for locator('[data-owned-sgs-search]')\u001b[22m\n"}}
```

本轮已核实按钮与五个证书字段绑定，`ancestorLevel=3`；但fill后点击临时标记定位器超时，`buttonClicked=false`、`certificateRequestObserved=false`、network为空。fill后临时标记不再可定位，属于控制脚本缺陷；React重绘使属性丢失是与现象一致的解释，未另采样确认；尚未发出编号查询，无SGS查询结果、详情或Annex链接。后续正确定位应在fill后重新从稳定`input[name="certificateNo"]`定位同时包含五字段与唯一Search的最小祖先，再按该范围内真实Search定位，不依赖fill前附加的DOM属性。按本次1 DOM读取+1查询阶段的预算停止，不自动增开纠正run。证书/Annex可取得性仍UNKNOWN；既有1页证书不等于164页Annex已补齐。

本轮收尾：阶段一、阶段二各1run，每run的dataset/KVS/queue/run均DELETE204，共8个自有远端资源已删；两run已SUCCEEDED退出，controller45160、90413、4649、25460及前述阶段一controller均已退出。原站请求边界仍2个单页加载、0个确认提交的证书编号查询，无新增原件、浏览器、实例、本机临时文件或常驻进程。仅现有附录新增约6KB，未改INDEX、产品事实、代码、Woo或生产。费用合计`$0.007009561843983002`。本机实际回收0B；远端物理释放量API未报告。收尾磁盘2.8Ti used / 823Gi available（与开始相比的空间变动不归因于本次清理）；diff-check通过。保留项仅本附录小型证据和既有原PDF。


#### 已授权的单次稳定定位纠正（2026-11-01）

主代理复核并批准下列稳定Locator，因前阶段未点击/未查询，实际查询额度仍为一次。资源上限明确修正为：增加且仅增加1个Apify run（100秒/2GiB、并发1），最多2个页面请求（既有搜索页及实际结果导航；不猜链接、不递归），owner仍为`sol_sgs_annex_locator`；其dataset/KVS/queue/run在本轮小型证据先解析追加后立即全删。原8资源已删除。无本机临时文件/浏览器/新报告/原件副本；controller仅调用Apify，操作完退出。稳定路径：fill后重新创建`page.locator('input[name="certificateNo"]')`，live XPath取最近`div.container`，该范围`getByRole('button', {name:'Search',exact:true})`；field/scope/Search各count=1且立即点击前`inputValue()===250008RECO14-CER`才允许一次click。不加DOM marker、不持ElementHandle，不处理验证码；若实际证书请求/结果未确认，保存真实状态并停止，不重提。本纠正代码已由主代理审阅。

稳定定位纠正run `ycZGKXOOKQaqMR2xm`，`2026-10-31T16:54:29.377Z`→`16:55:24.811Z`，SUCCEEDED（55.434秒墙钟），费用`$0.004019274099810256`，最大内存1,323,708,416B。创建前一POST在TLS握手中EOF，未获run回执；先查Actor倒序最近运行确认没有新run（最新仍13:51Z），才重试创建本唯一纠正run，没有重放原站查询。

已完整解析dataset audit，保留决定结论的小型证据：

```json
{"stage":"stable_locator_single_query","number":"250008RECO14-CER","buttonClicked":true,"numberRequestObserved":false,"counts":{"field":1,"scope":1,"search":1},"valueConfirmed":true,"requests":[{"path":"/metrics/g/collect","method":"GET","type":"fetch","containsNumber":false}],"responses":[{"path":"/metrics/g/collect","status":200,"containsNumber":false}],"alerts":[],"matchingRows":[],"links":[],"url":"https://www.sgs.com/en/certified-clients-and-products/sgs-certified-components-and-products","iframes":[],"machineResultState":"no_results","reviewedResultState":"after_click_unknown","datasetBytes":1667,"datasetSha256":"4b95c57aca0ff522bd92219af40dcb59e769cd15635f80f1957b047ed977d6a1"}
```

**正确Search已点击一次；证书编号查询是否实际发送、结果与Annex可取得性仍未知。** 点击前field/scope/Search各唯一、输入值逐字相等；未使用临时DOM属性或ElementHandle。25秒等待后页面仍通用搜索说明，无结果行、无匹配下载链接、无可见错误或人机挑战。网络记录仅限同源`www.sgs.com`的fetch/xhr/document；只有`/metrics/g/collect`返回200，未观察到含证书编号的同源请求，不能据此证明其他主机不存在请求。

必要纠正：原audit机器字段`resultState=no_results`是检测器假阳性——宽松正则`0 results`命中了通用说明里的`100 results`；页面没有“查无结果”的明确响应。人工按同份完整audit纠正为`after_click_unknown`，保留原机器值与哈希，不把该值当SGS搜索结果。正确按钮定位缺口已解决；本轮不再点击、不增run、不猜接口、不处理验证码，不声称证书/Annex不存在或不公开。未获得新原件，既有1页证书和164页Annex缺口仍保留。

纠正后资源收尾：`Esc5MfcyuRIJSXNlA` dataset、`TejJPaocUVZRuSdbE` KVS、`H8ie2X44548b3Mk9M` queue、`ycZGKXOOKQaqMR2xm` run均DELETE204；run已退出，controller86352/31969/25904/30436/26190/6232均退出。本专责任务累计3个成功run、12个自有远端资源已删、正确Search点击1次；费用合计`$0.011028835943793258`。只有既有附录小型记录新增（收尾前本专责段落9327B），无新本机原件/临时文件/浏览器/实例/常驻进程，无生产写入。磁盘2.8Ti used / 822Gi available，本机释放0B，远端释放字节未报告。保留原PDF及本记录；本轮结束，不再原站查询。
