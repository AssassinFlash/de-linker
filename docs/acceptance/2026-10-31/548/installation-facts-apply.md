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
