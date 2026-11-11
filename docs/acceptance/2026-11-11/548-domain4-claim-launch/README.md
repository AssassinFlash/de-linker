# 域 4「项目工作台与修订」两处维持记录的解除证据（2026-11-11）

`548-domain-gap-matrix.md` 第 4 行把该域判为**可发布**，但保留两条记录：
「recovery outbox 仍仅单测」与「launch protection 无独立验收」。本文件是这两处
补上真实层证据的结果。

**结论：两处都补上了真实层验收证据，全部通过。未发现规格与实现不一致。**

真实层在此处的定义：真 WordPress（快照实例）、真 Action Scheduler
（`wp action-scheduler run`）、真 `services/engine` 可执行与其保留环境；
不含任何替身 transport、替身调度器或替身存储。

## 一次性栈

| 项 | 值 |
|---|---|
| worktree | `/tmp/domain4-accept`（分支 `domain4-accept`，基于 `origin/main` @ `1c2f86cbb`） |
| 实例 | `d4accept`，WP `http://127.0.0.1:8894`、engine `8895`、Genie `8896` |
| 端口隔离 | 未使用共享 review 实例的 8889/8890/8891，也未用 8888/8892/8893 |
| 快照 | `~/de-linker-data/20261105-1208`（`snapshot.json` 记录 `loaded`） |
| 引擎运行时 | `runtime_sha256 = cfd3437e3d8d1e4397b2cdb88d3d68ff69276e708f3f7add43d4a37d368e0448`，`storage_schema_version = 5` |
| 资源周期 | 任务内唯一实例，验收完成后 `just retire --write` 回收 |

## 缺口 1：recovery outbox（真实层）

**层**：`tools/local/tests/integration/test_planner_native.py`
（真实实例 + 真实 Action Scheduler + 真实引擎），新增
`test_native_claim_outbox_persists_replays_and_only_a_receipt_removes_it`，
复用既有 `claim_runtime` 夹具：独立私有 workspace、独立 0600 MU 探针、退出时恢复
`runtime.json`/`wp-config.php`/option 并核对原 workspace 未被改写。

### 证明了什么

1. **持久化**：访客建项目后登录，确有一次原生
   `woocommerce_guest_session_to_user_id` 过渡，落成**一个**私有
   `linker_planner_claim` post：`post_status=private`、`post_author` = 该账号、
   内容是完整事件 `{schema_version:2, guest, user, key, recovery_scope}`（guest 为
   `wp:1:guest:<64 hex>`，key 与 scope 各 64 hex）。
2. **调度重放**：该事件恰好有一条 `linker_tools_planner_claim` / 组
   `linker-planner` 的投递，参数为 `[event_id, attempt]`。
3. **退避**：把 `linker_planner_url` 指向 `http://127.0.0.1:1/planning`
   （真实拒绝），连续 6 次让到期投递由真实 `wp action-scheduler run --force`
   执行，实测每次重试的到期偏移：

   ```
   attempt 1 → 59 s
   attempt 2 → 120 s
   attempt 3 → 240 s
   attempt 4 → 479 s
   attempt 5 → 899 s
   attempt 6 → 899 s
   ```

   与 `ClaimOutbox::queue()` 的 `min(15 min, 1 min × 2^(attempt-1))` 一致
   （读数是预定时刻前整秒，故 ±1–2 s）。规格里「无事件过期、失败保留事件重试」
   在真实调度上成立：6 次失败后事件仍在。
4. **投递失败不影响引擎**：整段失败期间引擎侧 `principal_closures` 与
   `ownership_transfers` 均为空，项目 owner 仍是 guest——即「没有确认回执就不算认领」。
5. **RPC 真实送达 + 确认后删除**：恢复真实 `linker_planner_url` 后，下一次真实
   `wp action-scheduler run` 使事件被删除（post 消失、无剩余投递），引擎三处同时读回：

   ```
   principal_closures   guest:wp:1:guest:<hex> | user:wp:1:user:<id>
   ownership_transfers  <project> | guest:wp:1:guest:<hex> | user:wp:1:user:<id>
   projects.owner       <project> | user:wp:1:user:<id>
   ```

   并且该账号读取原访客项目返回同一份对象，`bootstrap().claim_pending` 变为 `false`。

### 与既有覆盖的区别

- `plugins/linker-tools/tests/php/Unit/PlannerClaimOutboxTest.php`：替身 transport 与
  替身调度器，只验证分支与载荷形状。
- 既有 `test_native_login_claim_survives_upstream_outage_and_logout`（2026-10-23）：
  只断言「存在一条未来的重试」，不验证退避值、不读引擎回执、也不验证删除与
  `principal_closures`/`ownership_transfers`。
- 本用例：真实调度器推进真实退避序列，并直接读引擎 SQLite 的认领回执。

## 缺口 2：launch protection（真实可执行对）

**层**：`tools/local/tests/integration/test_engine_launch_protection.py`（新增，7 用例），
用真实 `services/engine` 源码与其保留 `.venv`，经 `PlannerWorker` 与真实
`services.serve()` 驱动，不使用替身 `release`/`require_input_compatibility`。

### 逐条对应规格声明

| 规格声明 | 用例 | 观测 |
|---|---|---|
| (a) 拒绝打开 schema 版本不同的既有存储 | `test_serve_refuses_a_store_the_executable_cannot_adopt[versioned-3]` | `ProcessError: planning storage/executable versions differ; a verified paired upgrade and recovery point are required`；DB 字节、mtime、文件集完全不变，且未产生 `-wal` |
| (c) 未标版本但已填充的存储不得当作新空库 | 同名 `[unversioned-0]` | 同上；`user_version=0` 但有表有行时仍被拒 |
| (b) 拒绝与不同可执行运行时并存的 worker | `test_serve_refuses_a_running_worker_from_another_executable` | 真实跑起「多一个模块」的可执行树的 worker（runtime `≠` checkout）后，`services.serve()` 抛 `running planning worker differs from this executable; preserve it for a verified paired upgrade`；PID 与 readiness 文件原样保留 |
| (b) 同上，HTTP 半 | `test_serve_refuses_a_running_http_from_another_executable` | 用该树真实启动 uvicorn，`/planning/version` 回报不同 `runtime_sha256`，serve 抛 `running planning HTTP differs …`；进程 PID 不变 |
| (d) 拒绝发生在 drain/stop/依赖同步/服务重启/WP option 更新之前 | 以上四例 + `recording_uv` | 每次拒绝时唯一执行的子进程是 `uv run … linker_engine.planning.worker_host release`；无 `sync`、无 `control`、无 `uvicorn`；`LINKER_ENGINE_RESOURCE_VERSION` 常量不变；`services.running()` 为空 |
| 顺序：存储拒绝先于执行器对 | `test_refusal_order_puts_the_store_before_the_executor_pair` | 同时让「运行中的不同 worker」与「不同版本存储」成立，报错是 `storage/executable versions differ`，不是 `worker differs`；该配对 worker 仍存活 |
| `worker_host release` 只报哈希与存储版本，不打开数据库 | `test_release_probe_needs_no_policy_store_or_migration` | 不存在的 `LINKER_PLANNER_CONFIG` 未被创建；对一个权限 `000`、内容为 `not a database` 的 `workspace.sqlite` 仍返回 `schema_version=1`、64-hex `runtime_sha256`、`storage_schema_version = schema.py 的 SCHEMA_VERSION`（实测 5） |
| 反向对照 | `test_routine_serve_accepts_the_store_its_own_executable_created` | 同一 `compatible_release()` 对自建存储放行，且仅做预检不启动 worker |

### 关键观察数据

```
release probe        runtime_sha256 = cfd3437e3d8d1e4397b2cdb88d3d68ff69276e708f3f7add43d4a37d368e0448
                     storage_schema_version = 5
                     耗时 2.1–3.0 s（冷启动首次约 12 s）
不同可执行树          runtime_sha256 = 749fd428…（同一份源码 + 一个额外模块）
不同可执行树 identity execution_key = 0304df9d…
共享存储              storage_binding 相同（同一 workspace 路径）
```

`storage_binding` 只看数据库路径，`execution_key` 只看代码/模型/参数——这解释了为什么
「同存储、不同可执行」能各自成立而被正确拒绝。

### 与既有覆盖的区别

`tools/local/tests/test_engine_release.py` 与 `test_planner_launch.py` 把
`release`、`require_input_compatibility`、`subprocess.run` 与存储全部替身化；
本文件跑的是真实可执行、真实 SQLite 与真实 uvicorn/worker 进程。

## 门禁

| 门禁 | 结果 |
|---|---|
| `tools/local`：`ruff check` / `ruff format --check` / `mypy`（strict） | 全绿（45 files，`Success: no issues found`） |
| `tools/local`：`pytest`（`just ci-python-package tools/local` 的单元层） | 见下节运行记录 |
| `plugins/linker-tools`：`vendor/bin/phpunit`（382 tests） | `OK (382 tests, 2945 assertions)` |
| 新用例：`test_engine_launch_protection.py` | `7 passed`（65.6 s） |
| 新用例：`test_native_claim_outbox_…` | `1 passed`（55.9 s） |

`composer install` 与 `npm ci` 均在本 worktree 内独立执行，未符号链接主树。

## 未改变的边界

- 本批次只新增真实层验收与记录，未修改 `ClaimOutbox.php`、
  `engine_release.py`、`planner_worker.py` 或引擎源码——两处实现经真实层观测
  与规格一致，没有需要修的差异。
- 未部署、未合并、未写入生产；未接触 `ssh hostinger-de-linker` 或
  `linker-services`；未使用共享 review 实例。
