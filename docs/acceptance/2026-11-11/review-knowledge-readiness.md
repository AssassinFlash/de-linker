# Review 实例 knowledge 消费者就绪 2026-11-11（`ready.knowledge` 0/88 → 85/85）

## 现象

review 实例（WP 8889 / engine 8890 / genie 8891）的 manifest 里
`ready.knowledge` 恒为 **0 / 88**：`linker_publication_jobs` 的 knowledge 消费者
`status=pending`、85 条 `loaded_products` 全是生产 worker 留下的过期回执，并带
112 条 `table_without_scope` 诊断。

engineering 同一病灶已由 `publication ack-engineering --engine=<url>` 修好（88/88，
`docs/acceptance/2026-11-11/review-readiness-fix.md`）；knowledge 被那条命令显式拒绝，
因为它需要 recipe-aware 回执。N 线与 O 线（PR #1097）都把它记为未做。

## 根因（两条，都必须解决）

### 1. 索引名的是另一代源

`acknowledge()` 的 recipe-aware 分支要求回执带
`recipe_revision` / `loaded_recipe_revision` / `index_version` /
`expected_serving_revision` / `serving_revision` / `loaded_model_identity_revision`，
并逐条比对 `prepared_products` 的 `product_revision`。engine 的
`/resource/version?ready=1` 一个都不给，只有 Genie 自己的
`POST /knowledge/loaded`（`retrieval.DocumentIndex.loaded()`）给出全集——
生产 worker（`services/genie/ops/publication_worker.py`）也是从这个端点 ACK 的。

实测本机索引与实例的差距：

| 项 | 本机旧索引 `20261108T205220Z-672808000` | review 实例 manifest |
| --- | --- | --- |
| `source_revision` | `094db8ad…`（线上快照构建） | `4a3abcd6…`（pull + repair-bindings 之后） |
| `serving_revision` | `a4bde371…` | 运行进程报 `e24270a4…` |
| 商品 revision 逐条匹配 | **0 / 85** | 88 个商品 |

`ready` 的唯一来源是 `loaded_products[product_id] === product_revision`，
所以旧索引一条都给不出就绪。

### 2. 没有任何本机进程会 ACK knowledge

`serve` 只把索引交给 Genie，`sync-feed.py` 的 claim→load→ack 循环是 VPS/Mac 的
systemd/launchd 单元，本地没有。于是即使索引对得上，也没有人上报。

## 修复

### 代码（PR #1101，未合并）

- **`GenieLoadedState`**（`plugins/linker-commerce/includes/Products/Publication/GenieLoadedState.php`）
  读 Genie 认证后的 `POST /knowledge/loaded` 并校验形状：五个 64-hex 身份、
  `index_version` 命名、`serving_revision === expected_serving_revision`
  （为别的 serving 规则构建的索引本进程也服务不了）、`activation_epoch` 非负整数、
  products 唯一且 revision 合法、诊断行 `reason` 在
  `no_proven_passage / document_unparsed / table_without_scope` 之内。
- **`publication ack-knowledge --genie=<url>`**（`PublicationCommand::ack_knowledge`）
  claim 前先拒绝三种索引：`genie_source_mismatch`、`genie_identity_mismatch`、
  `genie_products_stale`（stale / unknown 商品）；随后走既有
  `PreparationJobs::claim( 'knowledge', …, recipe )` → `acknowledge()`。
  `acknowledge()` 的校验一条没改（源、租约、recipe、索引代、serving、模型身份、
  逐条 product revision），命令只是把**实际加载态**送进协议。幂等：同一代已 ready
  时只报告，不再 claim。
- **`serve` 接线**（`tools/local/src/linker_local/services.py`）
  Genie 就绪后调用 `_acknowledge_knowledge()`，与 engineering 同模式（失败只报告，
  不让本来能起的 `serve` 失败）。
- `ack-engineering` 的 `unsupported_consumer` 文案改为指向新命令。

### `activation_epoch` 的语义裁定

本地预构建的索引不在准备租约里编译，`meta.activation_epoch = 0`（实测）。
`acknowledge()` 要求回执的 `activation_epoch` 等于当前 job 的 epoch，所以回执送的是
**本次 claim 的租约纪元**（94），索引自身的 0 只作为 `index_activation_epoch`
出现在输出里。没有为此放宽任何校验：epoch 是租约栅栏，不是索引代身份。

### `table_without_scope`：不修，也不该修

112 条诊断分布在 23 个文档（manual 71 行、compatibility 38 行、datasheet 3 行），
来自 `index.table_gate` 的规范性逐表判定（datasheet 任何 ≥4 行参数表、
compatibility 全部表、manual 仅表头型号轴已证明的表）。它是**诚实的覆盖报告**，
不是实例状态缺陷，改它就是伪造覆盖。

它不阻塞就绪：`acknowledge()` 里 `status` 由 `materialization_complete` 决定，
`preparation_complete=false` 只记录"仍有文档关联缺少已证段落"并保留原文诊断。

## 实例侧操作（可重放）

```bash
# 1. 用 review 实例的 manifest 重建索引（本机 PDF/parse/embedding 缓存命中）
cd services/genie
just wp review user application-password create 1 t-knowledge-index --porcelain   # 一次性凭据
uv run --locked --group index python -m index.build --rest-config /tmp/review-rest.json

# 2. 让 Genie 打开新构建（只重启 genie，WP 与 engine 不动）
just serve review --service genie

# 3. 走真实 claim → acknowledge
just wp review linker-commerce publication ack-knowledge --genie=http://127.0.0.1:8891
```

构建实测（143 文档全部命中 parse 缓存）：chunk 71.7 s · compile 318.4 s ·
embed 14.1 s（19 193 chunks 全部命中 embedding 缓存）· store 295.4 s，
合计约 12 分钟。产物 `20261111T032628Z-899307000/index.sqlite`，296 595 456 字节。

`ack-knowledge` 的读回：

```
source / loaded_source   4a3abcd6…（一致）
model identity           一致
recipe_revision          1403ff63…
index_version            20261111T032628Z-899307000
expected == serving      e24270a4…（一致）
products                 expected 85 · loaded 85 · matching 85 · stale [] · missing [] · unknown []
ack                      {"accepted":true,"complete":true}
```

## 验证

| 检查项 | 修复前 | 修复后 |
| --- | --- | --- |
| manifest `ready.knowledge` | 0 / 85 | **85 / 85** |
| manifest `ready.engineering` | 88 / 88 | 88 / 88（未受影响） |
| knowledge 消费者 | `pending`，85 条过期回执 | `ready`，`loaded_products` 85，`index_version` 指向新构建 |
| `preparation_complete` | false（112 条 `table_without_scope`） | false（同样 112 条，如实保留） |
| Genie `POST /knowledge/loaded` | 旧索引 `20261108T205220Z-672808000`，源 `094db8ad…` | 新索引 `20261111T032628Z-899307000`，源 `4a3abcd6…` |
| `publication reconcile` 之后 | — | 85/85 不变 |
| 再跑一次 `ack-knowledge` | — | `knowledge is already acknowledged for this generation: 85 of 85`（幂等） |
| `just serve review --service genie`（用 PR #1101 的代码） | — | `review: knowledge readiness: acknowledged`，索引行指向新构建 |

**88 个商品里 knowledge 只到 85**：另 3 个是 `reference_pv_module`（8349）与
`reference_cable`（8467、8468）。`acknowledge()` 的分母按
`EngineeringReference::ROLES` 排除它们（索引同样只有 85 条
`publication_ready_products`），与 engineering 的 88 分母不同是设计如此，不是缺口。

### Genie 检索实测（review 实例，真实浏览器走 WordPress 代理）

`http://127.0.0.1:8889/genie/` 提问
*"What is the AC output power of the SAJ HS2-8K inverter?"*：

```
POST /wp-json/linker-ai/v1/genie/turn   200  27.8 s
meta: grounded=true  fallback=false  route=documents  intent=documents_specs
      understand.call.linker/search-knowledge = 8.017 s
block: "For the HS2-8K-T2-X, the datasheet gives its rated AC power (on-grid) as 8000 W."
       refs: 0abea746ac33-p2-model-…, 4109, 1183, 1184, 1182
block(document): "SAJ HS2 Three-Phase All-in-One Datasheet (EN) · p. 2"
       http://127.0.0.1:8889/wp-content/uploads/2026/07/saj_hs2-10k-t2-x_datasheet.pdf#page=2
done: ok=true
```

引用来自新索引的 chunk（`0abea746ac33…` 是文档内容哈希），接口给出真实 PDF 页码，
不是兜底话术。

## 未解决项与注意事项

- **实例上运行的是主线代码，不是 PR #1101 的代码**。本次 ACK 是临时把
  `plugins/linker-commerce` 符号链接指到 `/tmp/t-knowledge` 执行的，随后已还原
  主线链接（`ls -l` 已读回）。所以：**在 #1101 合并并部署前，`just serve review`
  不会自动补 ACK**；`serve` 现在也没有 `ack-knowledge` 子命令。
  knowledge 的 ready 状态本身会保留（存的是 option，不依赖代码）。
- **PR #1101 未合并**，CI 状态见该 PR。
- 实例的 `linker_publication_jobs` 回滚副本：`/tmp/jobs-rollback-t-knowledge.json`
  （修复前原文，33 094 字节）；还原用
  `wp option update linker_publication_jobs '<json>' --format=json`。
- 本次用 `wp user application-password create 1 t-knowledge-index` 建过一个
  Application Password 供重建索引用，**已撤销**（
  `WP_Application_Passwords::delete_application_password()` 返回 `true`，
  `application-password list` 现为空），`/tmp/review-rest.json` 已删除。
  重建时按上面第 1 步重新生成即可。
- 生产同样停在 0/88（`https://de-linker.com` 实测 `knowledge` 0 / 88，
  `linker_publication_jobs` knowledge `pending`、`loaded 85`、`index_version
  20261108T205220Z-672808000`、`unprepared 113`）。这不在本票范围（本票只修 review
  本地实例），但说明**同一个缺口在生产也存在**，修复路径相同（合并 #1101 后在
  生产跑一次 `ack-knowledge --genie=<VPS Genie>`，前提是 Genie 已打开与新源匹配的索引）。

## 资源报告

- 新增构建：`~/de-linker-data/index/builds/20261111T032628Z-899307000/`（616 MB，
  index.sqlite 296 MB + corpus 392 MB）。这是 review 实例当前服务的索引，**保留**。
- 上一版构建仍在（`20261108T…` 662 MB、`20261108T183602Z` 662 MB），本票未删；
  它们不再被任何实例引用，可回收。
- worktree：`/tmp/t-knowledge`（3.0 GB，PR 提交已完成；保留待合并）。
- 临时文件：`/tmp/jobs-rollback-t-knowledge.json`（回滚副本，保留到下一次
  `pull load` 覆盖实例为止）、`/tmp/turn.sse`、`/tmp/pr-body.md`、
  `/tmp/commit-msg.txt`、`/tmp/review-manifest.json`、`/tmp/jobs.json`。
  含凭据的 `/tmp/review-rest.json` 已随 Application Password 撤销一并删除。
- 未新增实例；只重启了 review 的 genie 一个服务（WP 与 engine 未重启）；
  浏览器标签已关闭；未留下运行中的后台进程。
- 磁盘：`/System/Volumes/Data` 3.6 TiB，可用 1.2 TiB。
