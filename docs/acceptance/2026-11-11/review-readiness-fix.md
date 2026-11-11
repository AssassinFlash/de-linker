# Review 实例出询价就绪修复 2026-11-11（`ready.engineering` 全 false → 88/88）

## 现象

L 线在 review 实例（WP 8889 / engine 8890 / genie 8891）跑 `planner-country-rules`
e2e 时，`POST /planning/runs/equipment` 对任何真实当前设备选择都返回 **409
`product_evidence_changed`**，规则结果页因此不可达。

读回确认：

```
GET http://127.0.0.1:8889/wp-json/linker/v1/publication/manifest
  products 88 · documents 147 · source_revision 4a3abcd6…
  ready.engineering 0 / 88
  ready.knowledge   0 / 88
```

引擎侧 `Publication::prepared_view()` 只保留 `ready.engineering is True` 的商品，
于是 prepared 商品集为空；`equipment_assessment.selection_products()` 在当前
prepared 集里找不到选中的逆变器，抛 `ProductEvidenceChanged`。

生产不受影响：生产 engine prepared 88，同一份代码返回 200。

## 根因（实例状态，不是代码缺陷）

`ready` 的唯一来源是 `linker_publication_jobs` 里每个 consumer 的
`loaded_products[product_id]`，即准备 worker 上次 ACK 时报告的**实际加载**的
`product_revision`：

```php
// plugins/linker-commerce/includes/Products/Publication/PreparationJobs.php:30
foreach ( self::CONSUMERS as $consumer ) {
    $result[ $consumer ] = is_array( $state )
        && ( $state[ $consumer ]['loaded_products'][ $id ] ?? '' ) === $revision;
```

读回该 option，`engineering` 消费者的 receipts **存在但已过期**：

```
engineering  source_revision = 4a3abcd6… (当前值，reconcile 已同步)
             status         = pending
             loaded_products = 88 条，revision 与当前 product_revision 全部不同
             例：1178 receipt ffb8ecb3…  vs  当前 5e00b3cb…
```

`knowledge` 消费者同样 `pending`，并带 116 条 `table_without_scope` 诊断。

成因链路（同一病灶第四次出现，前三次是 feed figures 与 compatibility pairs）：

1. 该实例自线上快照拉取；拉取流程按地址改写重写 uploads URL
   （`tools/pull/src/linker_pull/load.py` `_bind_publication`）。
2. 今日早先跑过 `wp linker-commerce publication repair-bindings`，把 figures /
   兼容引用续期到本副本的文档身份，feed 因此从 405 恢复到 982 条事实、
   compatibility 377 对。
3. 续期改变的是 `product_revision` 的输入，整份 manifest 的
   `source_revision` 随之改变；生产带过来的 `loaded_products` 回执全部失配。
4. 本机**没有**自动准备 worker。`sync-feed.py` 的 claim→load→ack 循环是生产
   systemd 单元（`linker-engine-feed-sync.service`），需要
   `LINKER_PUBLICATION_USER` / `LINKER_PUBLICATION_PASSWORD` 专用
   Application Password；本地实例没有这对凭据，`linker-local serve` 只负责把
   feed 交给引擎，从不 ACK。

所以引擎加载得完全正确（见下），WP 侧却没有任何人上报这份加载——readiness 停在
上一次次拉取的回执上。

## 修复

不改代码、不改协议、不手写 option。走既有 claim→ack 协议，ACK 的内容取自
**引擎自己认证后的实际加载态**，与生产 worker 的信任模型一致。

`acknowledge()` 本身会拒绝伪造（`PreparationJobs::acknowledge()`）：

- `loaded_revision` 必须等于当前 `manifest.source_revision`；
- `prepared_products` 每个 `product_revision` 必须等于当前源；
- `job_id` / `lease_token` / 租约未过期 / `source_revision` 全都要对上。

执行步骤（review 实例）：

```bash
# 1. 引擎实际加载态（服务令牌来自运行中引擎进程环境）
TOK=…   # 该实例启动时注入的 GENIE_SERVICE_TOKEN
curl -s -H "x-linker-service-token: $TOK" \
  "http://127.0.0.1:8890/resource/version?ready=1"
```

读回：

```
source_revision        4a3abcd6…  ← 与 manifest 相同
compatibility_revision 932e2ff6…
prepared_products      88 条
```

与 manifest 逐条比对：**88 对 88，无缺失、无多余、revision 0 处不匹配**。

```bash
# 2. 用引擎实测回执走真实 claim → ack
just wp review eval-file /tmp/ack-engineering.php
```

脚本要点（完整脚本见下方「可重放命令」）：先校验引擎
`source_revision === manifest.source_revision`，不等则拒绝；然后
`( new PreparationJobs() )->claim( 'engineering', … )`，用返回的 job_id /
lease_token 和引擎的 `prepared_products` 调 `acknowledge()`。

输出：

```
claimed job bfe47d41c97e
ack: {"accepted":true,"complete":true}
engineering status=ready loaded=88 error=
```

### 可重放命令

```bash
cat > /tmp/ack-engineering.php <<'PHP'
<?php
use Linker\Commerce\Products\Publication\PreparationJobs;
use Linker\Commerce\Products\Publication;

$manifest = Publication::manifest();
$token = getenv( 'LINKER_ENGINE_SERVICE_TOKEN' );
$ctx = stream_context_create( [ 'http' => [ 'header' => "x-linker-service-token: {$token}\r\n" ] ] );
$actual = json_decode( file_get_contents( 'http://127.0.0.1:8890/resource/version?ready=1', false, $ctx ), true );
if ( ! is_array( $actual ) || ( $actual['source_revision'] ?? '' ) !== $manifest['source_revision'] ) {
    WP_CLI::error( 'engine loaded source does not match the current manifest; refusing to acknowledge' );
}
$jobs  = new PreparationJobs();
$claim = $jobs->claim( 'engineering', 'review-repair-' . getmypid(), 120 );
if ( is_wp_error( $claim ) ) {
    WP_CLI::error( 'claim failed: ' . $claim->get_error_code() );
}
$job = $claim['job'] ?? null;
if ( null === $job ) {
    WP_CLI::log( 'no claimable job' );
} else {
    $ack = $jobs->acknowledge( [
        'job_id'            => $job['job_id'],
        'lease_token'       => $job['lease_token'],
        'source_revision'   => $job['source_revision'],
        'loaded_revision'   => $actual['source_revision'],
        'prepared_products' => $actual['prepared_products'],
        'status'            => 'ready',
    ] );
    if ( is_wp_error( $ack ) ) {
        WP_CLI::error( 'ack rejected: ' . $ack->get_error_code() );
    }
    WP_CLI::log( 'ack: ' . wp_json_encode( $ack ) );
}
PHP
```

回滚：修复前 option 原文已留存（`wp option get linker_publication_jobs` 的 JSON
副本），`wp option update linker_publication_jobs '<json>' --format=json` 即可还原。
还原后 manifest 立刻回到 0/88，不影响站点其余功能。

## 验证

| 检查项 | 修复前 | 修复后 |
| --- | --- | --- |
| manifest `ready.engineering` | 0 / 88 | **88 / 88** |
| `engineering` 消费者 | `pending`，88 条过期回执 | `ready`，`loaded=88`，`error=""` |
| `POST /planning/runs/equipment` | 409 `product_evidence_changed` | **200**，`state: succeeded` |
| `country_assessment.rule_review` | 不可达（运行先被拒） | 出现在运行结果里 |

manifest 连读两次，`source_revision` 与 88/88 均稳定（ack 不改变源，`reconcile`
不会回退）。

重放运行（真实逆变器 1184 / SAJ HS2-8K）：

```
POST /planning/projects/create  200  project c61f0074…
POST /planning/runs/equipment   200  run 8f99c0dd…  state=succeeded
  product_policy: current_woo_prepared_equipment_v1
  check converter_identity: ac_output_kw_nominal 8000 W
    evidence doc-14697ee4… p2 · blob 259793c5… · figure 6350e180…
    product_revision ad120ba7…  (与 manifest 一致)
```

带 `country_rule_inputs`（DE，`de_pv_installed`，8 kW，2020-01-01）再跑一次：

```
state succeeded
country_assessment.rule_review =
  { country_code DE, rule_date …, checks [de_eeg_control, de_eeg_export] }
```

这正是 `planner-country-rules.spec.ts` 头注释里记的那条「recorded gap」——规则结果
只能在 equipment 结果里出现，而 equipment 之前被 409 挡住。现在它出现了。
该 spec 的注释已同步改为现状。

两轮重放用的项目随后都 `POST /planning/projects/delete` 删除（返回
`deleted: true`），不留测试项目在共享实例上。

## 未解决项（如实记录）

- **`ready.knowledge` 仍为 0/88**。它与本缺陷无关：knowledge 需要 recipe-aware
  的索引代（`recipe_revision` + `expected_serving_revision` +
  `index_version`），本地没有构建该索引的 worker，且既有回执里 116 条
  `table_without_scope` 诊断会强制 `preparation_complete=false`。它不阻塞
  Equipment（`prepared_view` 只看 `ready.engineering`），但 Genie 的知识检索
  在本实例上不是 ready 状态。修复它需要构建本机索引代，属于另一条链路。
- **成因会复发（已固化，见下节）**。凡是从线上快照拉取的实例，只要跑过
  `bind-figures` / `repair-bindings`，`product_revision` 就会整体改变，回执随即
  全部失配；而本机没有任何 worker 会重新 ACK。`tools/pull` 的
  `_bind_publication()` 只做绑定续期，明确不碰 readiness（它当时也没有已加载的
  引擎可读）。所以**每一个新拉的实例在有人手动 ACK 之前，planning 的 equipment
  链路都是 409**。

  本票按任务边界只修实例并留证据，未扩大改动范围；持久化解法由后续的 O 线
  落实，见下节。

## 已固化：`publication ack-engineering` + `just serve` 接线

主线裁定：本地引擎的加载态可以授予本地 WP 就绪，与生产 worker 同一信任模型。
据此把本票的手动步骤固化成正式命令，并接进 `just serve` 的收尾。

- `wp linker-commerce publication ack-engineering --engine=<base-url>`：读
  engine 认证后的 `/resource/version?ready=1`，校验 `source_revision` 等于本站
  manifest，再走 `PreparationJobs::claim()` → `acknowledge()`。`acknowledge()`
  原有的防伪造校验全部保留（`loaded_revision`、逐条 `product_revision`、
  `job_id`/`lease_token`/租约/source 全部要匹配），所以命令只是把**实际加载态**
  送进既有协议，没有新增信任面。实现见
  `plugins/linker-commerce/includes/Products/Publication/EngineLoadedState.php`
  与 `includes/Cli/PublicationCommand.php`。
- 只支持 `--consumer=engineering`；`--consumer=knowledge` 显式拒绝并说明原因
  （需要 recipe-aware 索引代）。knowledge 仍是本实例的未解决项。
- `tools/local` 的 `serve` 在 engine readiness 探测通过、`linker_engine_url`
  写好之后调用它（`tools/local/src/linker_local/services.py`
  `_acknowledge_engineering`）。幂等；失败只在输出里报告，不让本来能起的
  `serve` 失败。
- 测试：`plugins/linker-commerce/tests/php/Unit/Cli/PublicationCommandAckTest.php`
  （成功、source 不匹配拒绝、引擎不可达、非法读回形状、knowledge 显式不支持、
  已 ready 幂等）与 `tools/local/tests/test_engine_acknowledgement.py`
  （命令参数与 token、serve 的调用顺序与失败降级）。

review 实例上的实测对照（先把 88 条 engineering 回执 revision 全部置为失效，
复现 pull+repair 后的状态）：

| 检查项 | 修复前 | 命令执行后 |
| --- | --- | --- |
| manifest `ready.engineering` | 0 / 88 | **88 / 88** |
| engine 回执逐条比对 | — | `matching 88`, `stale []`, `missing []`, `unknown []` |
| ACK | — | `{"accepted":true,"complete":true}` |
| 再跑一次（幂等） | — | `engineering is already acknowledged for this source: 88 of 88` |

## 资源报告

- 新增文件：本文件；worktree `/tmp/n-ready`（3.0 GB，任务结束即回收）。
- 临时文件：`/tmp/jobs-rollback-101511.json`（回滚副本，验证已通过，随任务结束回收）、
  `/tmp/ack-engineering.php`、`/tmp/replay.py`、`/tmp/manifest*.json`、
  `/tmp/engver.json`。
- 未新增实例、未重启、未重建 review 实例；未新增浏览器进程。
- 磁盘：`/System/Volumes/Data` 3.6 TiB，可用 1.3 TiB。
