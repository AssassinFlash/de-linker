# 生产 knowledge 消费者就绪 2026-11-11（`ready.knowledge` 0/88 → 85/85）

## 现象

生产 `GET https://de-linker.com/wp-json/linker/v1/publication/manifest` 的
`ready.knowledge` 恒为 **0 / 88**（`ready.engineering` 88/88 正常）。对生产跑
`ack-knowledge --genie=…` 被诚实拒绝：

```
genie_source_mismatch: Genie loaded 094db8ad…, this site publishes 6f07a2c7…
```

Genie 服务进程打开的索引代 `20261108T205220Z-672808000` 是用**线上旧快照**
（`source_revision 094db8ad…`）构建的；生产站点此后已推进到 `6f07a2c7…`。
这个旧代与 review 实例当初那份旧索引是同一代。

## 根因

### 1. 索引代比站点源落后

`ready` 的唯一来源是 `linker_publication_jobs` 里 knowledge 消费者的
`loaded_products[product_id] === product_revision`。站点源变了，旧索引里的
85 条 `publication_ready_products` 与当前 88 个商品的 revision 全部失配，一条都
给不出就绪（与 review 实例的机理完全相同，
`docs/acceptance/2026-11-11/review-knowledge-readiness.md`）。

### 2. 唯一会重新 ACK 的进程已经损坏（这才是生产停摆的直接原因）

生产知识代只由 Mac 上的受管 worker 准备并 ACK（`services/genie/ops/PUBLICATION.md`
"Mac worker installation"）。本机那份 launchd 定义
`com.linker.knowledge-publication` 指向：

```
ProgramArguments[0] = …/releases/1418dc26e14c/.venv/bin/python      ← 目录不存在
ProgramArguments[1] = …/releases/06e2b8549a93/ops/install_publication_worker.py  ← 目录不存在
PYTHONPATH          = …/releases/06e2b8549a93/…
```

两个 release 目录都已被删除，`current` 软链也断了。`launchctl` 读回
`state = not running`、**`last exit code = 78: EX_CONFIG`**。此后每 900 秒的
定时触发都直接失败，没有任何进程再领取知识租约——于是索引停在 11-08 那一代，
ACK 停在更早的回执上。

`worker.env`（凭据、jobs URL、Genie token）本身仍然有效：用它探测
`jobs/claim` 得到的是业务校验 `400`（而非 `403`），说明凭据与
`manage_woocommerce` 权限都在。

## 修复

### 关键前提：必须用**生产运行时自己的源码树**构建

`index.sqlite` 的 `serving_revision` 必须等于运行进程启动时测得的
`RUNTIME_SERVING_REVISION`，否则 `_require_serving()` 会让**所有检索直接失败**。
生产运行时是 `/opt/linker-genie/current`（→ `20261108T204817031587Z`），实测：

| 身份 | 生产运行时 | main 分支 |
| --- | --- | --- |
| `serving_revision` | `a4bde371…` | `e24270a4…` |
| `recipe_revision` | `67a500b5…` | `1403ff63…` |

所以取生产运行时源码树构建，而不是用仓库 HEAD：

```bash
rsync -a --exclude .venv --exclude __pycache__ \
  linker-services:/opt/linker-genie/current/ /tmp/prod-genie/
# 本地实测该树：serving a4bde371… · recipe 67a500b5…  ← 与 VPS 进程自报一致
```

### 走既有受管路径，不手工切换

发布协议要求候选索引的 `meta.activation_epoch` 必须**等于当前原生租约的纪元**
（`index_release._validate_candidate`），因此不能只跑 `publish_index.py`，
也不能 rsync 后改软链。使用仓库既有的受管 worker：

```bash
# 生产运行时源码树 + 隔离 data root（PDF/parse/embedding 缓存以符号链接复用）
export LINKER_DATA=/tmp/prod-data
export PYTHONPATH=/tmp/prod-genie:/tmp/prod-genie/src:/tmp/prod-genie/ops
. ~/de-linker-ops/knowledge-worker/worker.env
cd /tmp/prod-genie
.venv/bin/python ops/publication_worker.py \
  --rest-config ~/.config/terravolt-builder/rest-de.json \
  --worker-id manual-prod-knowledge-$(date +%s) \
  --lease-seconds 7200 \
  --loaded-url http://127.0.0.1:8902/knowledge/loaded \
  --host linker-services
```

它走完整条既有链：`claim`（原生租约）→ build → `publish_index.prepare/activate`
（rsync 增量 + owner token + 原子切换）→ SSH 回环读 `/knowledge/loaded` →
`jobs/ack`。全程身份由原生校验器复核，没有手工写 option、没有绕过 owner 与
epoch 检查。

### 恢复受管 worker 的 launchd 定义

本机 `releases/` 下还有三份 release，其中 **`db0fddffa-main` 的身份与生产运行时
完全一致**（serving `a4bde371…`、recipe `67a500b5…`）。用该 release 自带的
渲染器重新生成并安装定义（只改路径，其余参数与损坏前一致：worker-id
`publication-618-mac`、interval 900 s、lease 7200 s、loaded-url
`http://127.0.0.1:8902/knowledge/loaded`、host `linker-services`）：

```bash
cd ~/de-linker-ops/knowledge-worker/releases/db0fddffa-main
env -u PYTHONPATH .venv/bin/python ops/install_publication_worker.py \
  --env-file ~/de-linker-ops/knowledge-worker/worker.env \
  --interval-seconds 900 --lease-seconds 7200 \
  --worker-id publication-618-mac \
  --loaded-url http://127.0.0.1:8902/knowledge/loaded \
  --host linker-services --install
```

安装后读回：`state = running`、`program = …/db0fddffa-main/.venv/bin/python`、
`last exit code = (never exited)`（不再是 78）。损坏前的 plist 保留为
`com.linker.knowledge-publication.previous.plist`（安装器自带的行为）。

## 构建代

| 项 | 值 |
| --- | --- |
| 版本 | `20261111T042003Z-140562000` |
| `source_revision` | `6f07a2c72ea69cd538d1e7895e85bbcaa9e85b741a1f89224a318f811078c6fb` |
| `recipe_revision` | `67a500b57c5ea740ff175d33f16cbfbd8fdd09b93ccbfbed0f6b0bf5032ae483` |
| `serving_revision` | `a4bde371561adac8179bcaecaec4b7303f6293b34ed1801c2298bc5685b21306` |
| `activation_epoch` | 100（本次原生租约纪元） |
| 文档 | 143 / 143 索引成功，0 失败 |
| 页 / 片段 | 4700 页，4686 页有片段；19 195 片段（4425 条型号投影） |
| `permission_coverage` | 5314 / 19195 片段有证明 |
| datasheet 裸表 | 0（发布门禁 `refuse_bare_datasheet_tables` 放行） |
| `index.sqlite` | 296 648 704 字节，sha256 `41025c44bd8013d7ac3ec0e75b75e6ca5065a90119544812c64dcbeb197c4ac3` |
| 耗时 | chunk 98.7 s · compile 120.0 s · embed 2.9 s · store 60.1 s（parse 全部命中缓存） |

上传是增量的：`Matched data: 280396800 B`、实际只传 1 555 619 字节
（speedup 176.97）。

## 读回

原子切换后 `/opt/linker-genie/index/current` → `20261111T042003Z-140562000`，
`.activation.json` 记录 `epoch 100` 与该代的 source/recipe/serving。
Genie 进程在下一次读取时重开 `current`（`default_index()` 比较解析后的路径），
`/knowledge/loaded` 立刻报出新代：

```
index 20261111T042003Z-140562000 | source 6f07a2c7… | serving a4bde371… | products 85
```

生产队列（`wp option get linker_publication_jobs`）：

```
status          ready
loaded_revision 6f07a2c72ea69cd5…
index_version   20261111T042003Z-140562000
loaded_recipe   67a500b57c5ea740…
serving         a4bde371561adac8…
epoch/loaded    100 / 100
mat/prep        True / False
loaded_products 85   unprepared 113
error           'Some current document associations still lack proven passages.'
```

生产 manifest：

| 检查项 | 修复前 | 修复后 |
| --- | --- | --- |
| `ready.knowledge` | 0 / 88 | **85 / 85**（85 + 3 参考件） |
| `ready.engineering` | 88 / 88 | 88 / 88（未受影响） |
| `source_revision` | `6f07a2c7…` | `6f07a2c7…`（未变） |

**85 而不是 88**：`8349`（`reference_pv_module`）、`8467`/`8468`
（`reference_cable`）按 `EngineeringReference::ROLES` 不进 knowledge 分母，
索引自身也只有 85 条 `publication_ready_products`。与 review 实例同一口径。

`preparation_complete=false` + 113 条 `table_without_scope` 是**诚实的覆盖报告**，
不阻挡就绪：`acknowledge()` 的 `status` 由 `materialization_complete` 决定。

## 生产检索实测

生产站启用了 Turnstile，因此直接 curl `/linker-ai/v1/genie/turn` 会得到
`503 linker_admission_configuration`（保护层拒绝无浏览器凭证的请求），无头浏览器
也停在 "Checking verification…"——**我没有绕过生产的人机验证**。改用 VPS 本机回环
与 Genie 自己的服务令牌（WordPress 外壳调用它走的同一条认证路径）：

```
POST http://127.0.0.1:8902/assistant/turn   (x-linker-service-token + resource subject)
meta: grounded=true  fallback=false  route=documents  intent=documents_specs
      understand.call.linker/search-knowledge = 8.914 s   failures=[]
block: "The HS2-8K-T2-X is rated at 8000 W of rated AC output power."
       + HS2 family 5K/6K/8K/10K 分别为 5000/6000/8000/10000 W
refs:  0abea746ac33-p2-model-48c66ddb910103c5, …-bfb42d8e9aa29448, …-8da853b7567c034d, …
document: "SAJ HS2 Three-Phase All-in-One Datasheet (EN) · p. 2"
       https://de-linker.com/wp-content/uploads/2026/07/saj_hs2-10k-t2-x_datasheet.pdf#page=2
done: {"ok": true}
```

数值与页码来自新索引的真实证明片段，不是兜底话术；`grounded=true` 表示引用通过
发布校验。

## 回滚

旧代仍在 VPS 上按既有流程保留（`KEEP = 3`）：

```
/opt/linker-genie/index/20261108T205220Z-672808000   ← 上一代（当前仍保留）
/opt/linker-genie/index/20261108T183602Z-365393000
/opt/linker-genie/index/20261108T171459Z-434728000
```

按 `PUBLICATION.md` "Deliberate rollback"，受管索引**不能**直接把 `current` 指回
旧代（`.activation.lock`/FENCE 会拒绝）；恢复旧代要走
`PreparationJobs::reactivate_recipe($expected_current_recipe, $verified_retired_recipe)`
（已知退役 hash + CAS），再由 worker 以更高 epoch 重新准备。本次没有删除任何旧代。

## 未解决项

1. **`identify` 端点对 worker 凭据返回 403**。实测
   `POST /wp-json/linker/v1/publication/identify` 用 `worker.env` 的凭据得 403，
   而 `jobs/claim` 同一凭据得 400（业务校验，说明已通过鉴权）。本次构建没有触发
   该路径（`identify` 只在 leased batch 且需要模型识别时使用，日志显示
   `phase: identify` 实际走的是批量端点且成功），所以**不影响本次发布**；但这
   是一个独立的鉴权缺陷，若将来有构建需要单条 `identify` 会失败。
2. **worker 的自动发布依赖本机 release 目录存在**。这次我把它指回
   `db0fddffa-main`（身份与生产运行时一致）。一旦生产运行时升级（paired release），
   该 release 的 serving 身份就与新运行时不再匹配，worker 会按设计拒绝发布，
   需要同时准备匹配的新 worker release——这是既有流程，不是本次引入的问题。
3. 本次发布由我手动运行的受管 worker 完成（`worker-id manual-prod-knowledge-…`），
   **不是** launchd 那一份。launchd 那份已在发布后修复并读回运行中，下一次定时
   触发会走它（对已 ready 的同一代是幂等 no-op）。

## 资源报告

- 新增构建：`/tmp/prod-data/index/builds/20261111T042003Z-140562000/`
  （源码树 `/tmp/prod-genie` 23 MB + 构建目录约 700 MB）。
  **保留到本次验收结束**；生产已在服务该代（VPS 侧副本为正式留存的 release）。
- VPS 新增 release `20261111T042003Z-140562000`（296 MB），按 `KEEP = 3` 连同
  旧代保留；未手工删除任何旧代。
- 临时文件：`/tmp/prod-turn-payload.json`、`/tmp/prod-turn.sse`、
  `/tmp/broken-plist-backup.plist`、`/tmp/run-prod-worker.sh`（含凭据读取，
  收尾删除）。
- 未新增实例；未重启 VPS 上任何 unit（Genie 在读取时自行重开 `current`）；
  浏览器标签已关闭。
