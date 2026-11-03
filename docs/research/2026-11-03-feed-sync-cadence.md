# `linker-engine-feed-sync.timer` 空转治理与触发频率调研

日期：2026-11-03
范围：只读排查仓库定义、执行链路、VPS 实测运行数据与消费方影响（未修改生产任何配置或文件）。

---

## 1. Timer / Service 单位定义与触发间隔依据注释

### 1.1 仓库定义位置与原文

仓库内单位定义位于 `services/engine/ops/`，与 VPS 生产环境 `/etc/systemd/system/` 下的安装副本逐字节一致：

- **Timer 定义**：`services/engine/ops/linker-engine-feed-sync.timer:1-12`（生产路径 `/etc/systemd/system/linker-engine-feed-sync.timer`）
  ```ini
  # Woo pending jobs reconcile automatically; withdrawal never waits for this timer.
  [Unit]
  Description=Prepare changed Woo engineering data automatically

  [Timer]
  OnBootSec=1m
  OnUnitInactiveSec=1m
  Persistent=true
  Unit=linker-engine-feed-sync.service

  [Install]
  WantedBy=timers.target
  ```

- **Service 定义**：`services/engine/ops/linker-engine-feed-sync.service:1-19`（生产路径 `/etc/systemd/system/linker-engine-feed-sync.service`）
  ```ini
  # Publish a complete immutable generation and acknowledge actual loaded data.
  [Unit]
  Description=Refresh the Linker design engine's product feed and compatibility contract
  After=network-online.target
  Wants=network-online.target

  [Service]
  Type=oneshot
  Environment=LINKER_ENGINE_CACHE=/opt/linker-engine/state/cache
  EnvironmentFile=/etc/linker-engine.env
  # main records GC errors, still prepares Woo jobs and returns failure visibly.
  ExecStart=/usr/bin/python3 /opt/linker-engine/ops/sync-feed.py
  StandardOutput=journal
  StandardError=journal
  NoNewPrivileges=true
  PrivateTmp=true
  ProtectHome=true
  ProtectSystem=strict
  ReadWritePaths=/opt/linker-engine/state /run/systemd
  ```

### 1.2 当前触发间隔（`1m`）的依据注释核查

- **Timer 文件内无间隔依据注释**：`services/engine/ops/linker-engine-feed-sync.timer:1-12` 使用的是 `OnBootSec=1m`（第 6 行）和 `OnUnitInactiveSec=1m`（第 7 行，而非 `OnUnitActiveSec`）。文件头注释仅写 `# Woo pending jobs reconcile automatically; withdrawal never waits for this timer.`（第 1 行），**没有任何注释说明为什么间隔设为 `1m`（60 秒）**。
- **配套代码与运维文档中的相关说明**：
  - `services/engine/ops/sync-feed.py:4-5`：`The existing timer is an automatic retry/reconciliation path. Revocation is independent: requests read current Woo permission before and after work.`
  - `services/engine/ops/sync-feed.py:484`：`# One second yields to the minute retry instead of holding up work.`
  - `services/engine/ops/PUBLICATION.md:85-89`：`The one-minute timer runs cleanup even when there is no pending Woo job. This gives receipts their existing 24-hour usable lifetime and removes expired rows on the next healthy timer pass. ... A one-second SQLite lock wait yields to the next minute's retry.`
- **Git 历史溯源**：
  - `515ac6cf4`（2026-10-19，#354）与 `62452c4ab`（2026-10-21，#493）最初将该 timer 设为每晚定时执行一次：`OnCalendar=*-*-* 03:40:00 UTC` + `RandomizedDelaySec=10m`。
  - `50ae18139`（2026-10-23，`fix: bind engineering selections and reports to current Woo publication`）在接入 Woo 发布队列（`PreparationJobs`）与收据清理时，直接将 `OnCalendar=*-*-* 03:40:00 UTC` 改为 `OnBootSec=1m` + `OnUnitInactiveSec=1m`，未给出任何容量或业务频率测算依据。

---

## 2. 每次 Tick 的实际执行逻辑（代码路径 `file:line`）

每次 `linker-engine-feed-sync.timer` 触发 `linker-engine-feed-sync.service` 时，都会拉起一个全新的 `/usr/bin/python3 /opt/linker-engine/ops/sync-feed.py` 进程（入口 `services/engine/ops/sync-feed.py:531-547`），依次执行两个阶段：

### 2.1 第一阶段：私有确认结果收据（Receipt）过期清理

- **代码路径**：`services/engine/ops/sync-feed.py:539` 调用 `cleanup_receipts()`（`sync-feed.py:505-529`）→ `receipt_path()`（`sync-feed.py:457-472`）。
- **每 tick 行为**：
  1. 解析 `/opt/linker-engine/state/cache/private/selections.sqlite`（`sync-feed.py:469`）。
  2. 若数据库文件存在，以读写模式打开 SQLite（`timeout=1`，`sync-feed.py:514-516`），执行：
     ```sql
     DELETE FROM selections WHERE expires < ?
     ```
     （`sync-feed.py:517-519`）。
  3. 打印第一行固定日志：`receipt retention: deleted <deleted> expired confirmed-result receipts at /opt/linker-engine/state/cache/private/selections.sqlite`（`sync-feed.py:520-522`）。
- **关键事实**：引擎运行时 `Selections` 类（`services/engine/src/linker_engine/selections.py:35-70`）在每次写入 `remember()` 时已经先执行 `DELETE FROM selections WHERE expires < ?`（`selections.py:39-40`），且在每次读取 `read()` 时严格按 `AND expires>=?` 过滤（`selections.py:60`）。因此过期行在读路径上秒级失效，无需靠每分钟外部进程轮询保证正确性。

### 2.2 第二阶段：向 WordPress 轮询认领工程准备任务（Feed 同步条件）

- **代码路径**：`services/engine/ops/sync-feed.py:542` 调用 `sync(jobs=job_request)`（`sync-feed.py:267-455`）。
- **每 tick 必做的远程调用**：
  1. 获取本地排他锁 `/opt/linker-engine/state/.publication-sync.lock`（`sync-feed.py:285-286`）。
  2. 调用 `job_request("claim", {"consumer": "engineering", "worker_id": f"engine-{socket.gethostname()}", "lease_seconds": 300})`（`sync-feed.py:161-180, 293-300`），通过公网向 `https://de-linker.com/wp-json/linker/v1/publication/jobs/claim` 发起带 Basic Auth 的 HTTPS POST 请求。
  3. **WordPress 端每次被 `/jobs/claim` 命中时做的重活**：
     - 路由入口：`plugins/linker-commerce/includes/Products/Publication/Controller.php:79-93` → `PreparationJobs::claim()`（`plugins/linker-commerce/includes/Products/Publication/PreparationJobs.php:92-162`）。
     - 在 `Lock::run('publication-jobs', ...)` 锁内（`PreparationJobs.php:100-105`），**每次都会实时调用 `Publication::manifest()`**（扫描全部已发布商品、工程参考件与技术文档附件并计算哈希），随后执行 `self::reconciled_state($manifest)`（`PreparationJobs.php:66-77`），对比 `$state['engineering']['source_revision']` 与 `$manifest['source_revision']` 并调用 `update_option('linker_publication_jobs', $state, false)`（及 `delete_option('linker_publication_pending')`）。
     - **空转判定条件**（`PreparationJobs.php:142-144`）：当 `$job['status'] === 'ready'`（或存在未过期的活动租约 `lease_expires_at > time()`）且 `$job['source_revision'] === $manifest['source_revision']` 时，WordPress 返回 `{"job": null}`。
  4. `sync-feed.py:301-303` 收到 `job is None`，打印第二行固定日志 `no pending engineering preparation` 并返回 `0`。

### 2.3 什么时候会“真的干活”？

只有当 WordPress 的 `Publication::manifest()['source_revision']` 发生变化（触发源见 `plugins/linker-commerce/includes/Products/Publication/Module.php:25-37`：商品保存/状态变更、`pa_*`/`product_*` 词项修改、PDF 附件或 `_linker_document_public` 变更、兼容合同或安装事实 `InstallationFacts` 写入等），导致 `$state['engineering']['source_revision'] !== $manifest['source_revision']` 被置为 `status = 'pending'`，或上一次准备任务失败/租约超时（`lease_expires_at <= time()`）时，`/jobs/claim` 才会返回非空 `job` 对象（`PreparationJobs.php:145-158`）。此时 `sync-feed.py` 执行完整同步：

1. **拉取完整 Feed**：`fetch_feed()` 请求 `GET https://de-linker.com/wp-json/linker/v1/engineering-feed`（`sync-feed.py:58-67, 304`），校验 `document["source_revision"] == job["source_revision"]` 及 `compatibility` 结构（`sync-feed.py:305-319`）。
2. **已加载代复用短路**：`reusable_generation()`（`sync-feed.py:183-241, 321-331`）检查 `/opt/linker-engine/state/current` 的 `feed.json` / `compatibility.json`（忽略每次请求动态生成的 `generated_at`）及引擎进程 `http://127.0.0.1:8901/resource/version?ready=1` 是否已匹配目标版本；若已匹配则直接调用 `acknowledge()`（`POST /wp-json/linker/v1/publication/jobs/ack`，`sync-feed.py:244-264`）并记录 `confirmed already loaded source <rev>`。
3. **落盘新代并原子切换 + 重启 `linker-engine`**：
   - 在 `/opt/linker-engine/state/` 下创建 `publication-generation-<random>` 目录，写入 `feed.json` 与 `compatibility.json`（`sync-feed.py:335-341`）。
   - 用 `/opt/linker-engine/current/.venv/bin/python` 运行 `GENERATION_PROBE`（`Products.load` + `Compatibility.load` + 计算版本摘要，`sync-feed.py:37-49, 92-106, 342-344`）。
   - 写入 `manifest.json`、设置 `0755/0644` 权限（供非 root 的 `linker-planner` 读取），原子替换 `state/current`、`state/feed.json`、`state/compatibility.json` 软链（`sync-feed.py:109-121, 345-382`）。
   - 执行 `systemctl restart linker-engine`（`sync-feed.py:70-76, 384`），轮询 `http://127.0.0.1:8901/resource/version?ready=1` 验证进程已加载新代（失败则回滚 `current` 软链并重启，`sync-feed.py:387-408`）。
   - 调用 `POST /wp-json/linker/v1/publication/jobs/ack` 向 WordPress 确认 `status="ready"` 与 `prepared_products`（`sync-feed.py:410-412`），清理旧 `publication-generation-*` 目录（仅保留 `current` 与 `previous` 两代，`sync-feed.py:124-148, 413`），输出 `published and loaded source <rev> (<N> products)`（`sync-feed.py:416-418`）。

---

## 3. VPS 实测频率数据（`ssh linker-services` 只读取证）

### 3.1 `/opt/linker-engine/state/` 目录与 `feed.json` mtime 历史

`sync-feed.py` 每次发布新代都会调用 `prune_generations()` 只保留 `current` 和 `previous` 两个代目录。当前 VPS `/opt/linker-engine/state/` 实测状态：

| 路径 | 类型 / 目标 | mtime (UTC) | `source_revision` |
| --- | --- | --- | --- |
| `/opt/linker-engine/state/feed.json` | symlink → `current/feed.json` | `2026-11-03 07:09:11Z` | `113e8ad2...9097534` |
| `/opt/linker-engine/state/current` | symlink → `publication-generation-jusa86bz` | `2026-11-03 07:09:11Z` | `113e8ad2...9097534` |
| `publication-generation-jusa86bz/feed.json` | regular file (1,340,371 B) | `2026-11-03 07:09:11Z` | `113e8ad2...9097534` |
| `publication-generation-xo1h9eod/feed.json` | regular file (1,327,607 B) | `2026-11-03 03:38:11Z` | `cd9e9a99...e11fdf6` |
| `compatibility.json.bak-20261021` | regular file (310,506 B) | `2026-10-21 08:24:40Z` | 初始切换前备份 |

### 3.2 `journalctl -u linker-engine-feed-sync.service` 实测统计（2026-10-27 至 2026-11-03）

当前 systemd journal 保留窗口为 `2026-10-27T14:31:56Z` 至 `2026-11-03T09:30:12Z`（共 **6.79 天**），全量统计如下：

| UTC 日期 | 启动总次数 (`starts`) | 空转次数 (`no pending`) | 实际同步次数 (`published and loaded`) | 已加载直接确认 (`confirmed`) | 网络/超时/校验失败 (`errors`) | 清理过期收据 (`deleted > 0`) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-10-27 (14:31起) | 468 | 458 | 1 | 0 | 9 | 0 |
| 2026-10-28 | 1,173 | 1,161 | 2 | 0 | 10 | 0 |
| 2026-10-29 | 1,190 | 1,172 | 1 | 0 | 17 | 0 |
| 2026-10-30 | 1,168 | 1,137 | 2 | 0 | 29 | 0 |
| 2026-10-31 | 1,215 | 1,209 | 0 | 0 | 6 | 0 |
| 2026-11-01 | 1,201 | 1,172 | 9 | 1 | 18 | 0 |
| 2026-11-02 | 1,214 | 1,185 | 7 | 1 | 22 | 0 |
| 2026-11-03 (至09:30) | 483 | 469 | 2 | 0 | 12 | 0 |
| **合计（6.79 天）** | **8,112** | **7,963 (98.16%)** | **24 (0.30%)** | **2 (0.02%)** | **123 (1.52%)** | **0 (0.00%)** |

补充证据：
1. **真实 Feed 变化频率**：
   - 过去 6.79 天内，`published and loaded source` 共发生 **24 次**（去重后仅 **19 个不同的 `source_revision`**，日均 **3.5 次**；无后台改动的完整自然日如 2026-10-31 为 **0 次/天**）。
   - 最近 24 小时（北京时间 2026-11-02 20:00 至 2026-11-03 17:30，对应批量写入 `installation_facts` 期间）共发生 **4 次**：
     - `2026-11-02T12:56:42Z`（`726872bf...`）
     - `2026-11-02T14:42:39Z`（`bd2bbe2c...`）
     - `2026-11-03T03:38:16Z`（`cd9e9a99...`）
     - `2026-11-03T07:09:17Z`（`113e8ad2...`）
   - 更早的历史日志文件 `/var/log/linker-engine-feed-sync.log`（`2026-10-23T22:08:48Z` 切换至 1 分钟 timer 起，至 `2026-11-01T07:13:10Z` 停用文件日志止，共 8.38 天）共记录 **9,715 次 `no pending engineering preparation`**，而同期 `published and loaded source` 仅 **15 次**（日均 **1.8 次**）。
2. **Receipt GC 实际命中率**：
   - 在最近 6.79 天的 8,112 次启动中，`receipt retention: deleted <N>` 有 **0 次**删除了任何记录（全部为 `deleted 0`）；当前 `/opt/linker-engine/state/cache/private/selections.sqlite` 中 `SELECT count(*) FROM selections` 为 **`0` 行**。
   - 在 `2026-10-23` 至今的全部历史中，仅 `2026-10-24 23:17–23:28 UTC` 出现过 4 次 `deleted 1`。
3. **高频空转带来的副作用（Hostinger 抖动放大）**：
   - 因为每次空转都要向 Hostinger 共享主机发起 `POST /wp-json/linker/v1/publication/jobs/claim` 并触发全量 `Publication::manifest()` 计算 + `wp_options` 写锁，过去 6.79 天内因 Hostinger 瞬时 `HTTP 500/503`、TLS 握手超时（`_ssl.c:983`）或 30 秒读超时导致 `linker-engine-feed-sync.service` 报错退出（`status=1/FAILURE`）达 **123 次**（日均 **18 次**）。

---

## 4. 消费方机制与三选一方案论证

### 4.1 消费方如何读取 `feed.json`？（决定延迟后果）

VPS 上有两个服务消费 `/opt/linker-engine/state/feed.json` 与 `/opt/linker-engine/state/compatibility.json`：

1. **Legacy Engine（`linker-engine.service`，端口 `8901`）**：
   - 进程启动时在 `Services.__init__()`（`services/engine/src/linker_engine/app.py:92-132, 175-181`）将 `feed.json` 读入内存缓存；当 `sync-feed.py` 发布新代时，会主动执行 `systemctl restart linker-engine`（`sync-feed.py:70-76, 384`）使其立即加载新代。
2. **Dedicated Planner（`linker-planner-http.service` 端口 `8911` + `linker-planner-worker.service`）**：
   - **既不是每 release 拷贝 `feed.json` 副本，也不是进程启动时一次性缓存，而是运行时按操作直接读取 `/opt/linker-engine/state/feed.json` 软链指向的当前代文件！**
   - 代码与生产环境证据：
     - `services/engine/ops/planner_release.py:31-35, 424, 443-454` 在 `prepare` 时仅将路径变量 `LINKER_ENGINE_FEED=/opt/linker-engine/state/feed.json` 与 `LINKER_ENGINE_COMPATIBILITY=/opt/linker-engine/state/compatibility.json` 写入 `/opt/linker-planner/releases/<hash>/.deploy/{http,worker}.env`（已在 VPS 实测核对），不拷贝 JSON 数据文件。
     - `services/engine/src/linker_engine/planning/http_host.py:47-48` 默认注入 `worker_product_provider`（`services/engine/src/linker_engine/planning/product_sources.py:40-45`），每次调用 `ProductSources.load()`（如 `module_basis()` 第 61 行、`equipment_basis()` 第 100 行、`confirm_basis()` 第 207 行、`current()` 第 471 行）都会实例化 `Services(Settings.from_environment(), SOURCE)`，实时 `resolve()` 并读取 `/opt/linker-engine/state/feed.json` 与同目录 `manifest.json`。因此 `sync-feed.py` 原子切换 `/opt/linker-engine/state/current` 后，**Planner 无需重启即可在下一次请求看到新 `feed.json`**。

### 4.2 同步延迟在三种业务场景下的真实后果

1. **产品或技术资料下架/撤权（零延迟，完全不依赖 timer）**：
   - `services/engine/src/linker_engine/publication.py:60-97, 333, 520` 在每次计算、选型、读取产品目录（`products/current`）和确认结果前/后都会实时请求 `GET https://de-linker.com/wp-json/linker/v1/publication/manifest`（`Cache-Control: no-cache`）。一旦商品转草稿或资料撤权，引擎和 Planner **0 秒立即拒绝**，绝不等待 `feed-sync`。
2. **未改动商品的正常选型与规划（零影响）**：
   - WordPress 的 `PreparationJobs::readiness()`（`PreparationJobs.php:30-40`）按单个商品维度比对 `($state['engineering']['loaded_products'][$id] ?? '') === $revision`。即使某个商品被编辑触发了新的 pending job，其余未改动商品的 `loaded_products[$id]` 依然匹配当前 `product_revision`，`ready.engineering` 保持 `true`，不受等待队列影响。
3. **新增商品或刚修改了工程事实/文档的商品（唯一受 timer 间隔影响的窗口）**：
   - 从商品在 Woo 中修改保存（`product_revision` 改变）到下一次 `sync-feed.py` 完成拉取并回调 `/jobs/ack` 之前，该被改商品在 `manifest` 中的 `ready.engineering` 为 `false`，Planner 将其视为“正在准备工程数据”（`docs/specs/609-product-publication.md:24` 明确规定：“新上架产品可以先在网站展示。所需资料与工程数据准备完整后，相关工具自动启用”）。
   - 若是工程人员通过 CLI/脚本批量写入商品事实（如 `#548` 写入 `installation_facts`）需要立即验收，运维规程本就支持直接执行 `systemctl start linker-engine-feed-sync.service` 立即触发一次同步（见 `docs/acceptance/2026-10-31/548/installation-facts-apply.md:141`）。

### 4.3 三选一结论与对比

- **方案 (a)【推荐】：将 `linker-engine-feed-sync.timer` 的 `OnUnitInactiveSec=1m` 放大到 `15m`（15 分钟）**。
  - **收益**：每日 Python 启动、SQLite 写事务与跨公网请求 WordPress `/wp-json/linker/v1/publication/jobs/claim`（含全量 `Publication::manifest()` 计算）的次数从 **~1,200 次/天降至 ~96 次/天（减少 92%+）**；Hostinger 瞬时 500/503/TLS 超时导致的 systemd 假失败告警同步减少 92%+。
  - **安全性依据**：
    1. **下架/撤权 0 秒生效**：运行时每次请求直读 `/publication/manifest`，与 timer 间隔无关。
    2. **未修改商品 0 影响**：`loaded_products` 按商品粒度判定就绪，Planner 运行时直读 `/opt/linker-engine/state/feed.json` 软链。
    3. **低频后台编辑延迟可接受**：实测 Feed 真实变化仅 **0–9 次/天（日均 3.5 次）**；后台常规编辑最多等待 ≤15 分钟（平均 7.5 分钟）自动就绪，完全符合 `docs/specs/609-product-publication.md:24`；工程脚本批量写入或发布验收时可按既有规程 `systemctl start linker-engine-feed-sync.service` 即刻同步。
    4. **Receipt GC 零风险**：`selections.sqlite` 的 TTL 为 24 小时，读路径 `Selections.read()` 秒级校验 `expires >= now`，写路径 `Selections.remember()` 自动顺带清理过期行；GC 轮询从 1 分钟改为 15 分钟不影响任何业务行为。
- **方案 (b)【不推荐单独采用】：改为纯事件驱动（WP 发布时主动触发）**。
  - **不推荐理由**：
    1. **跨主机拓扑与权限边界**：WordPress 运行在 Hostinger 共享主机，而 `sync-feed.py` 运行在独立 VPS 且需要写 `/opt/linker-engine/state` 与执行 `systemctl restart linker-engine`（需 `/run/systemd` 权限）。在 VPS 暴露公网 webhook 供 Hostinger 触发重启会显著扩大攻击面与运维复杂度。
    2. **规格硬约束仍要求保留后台对账轮询**：`docs/specs/609-product-publication.md:25, 83, 103` 明确要求“准备失败要可见、可重试，构建机离线时保留待办；事件丢失、重启、任务积压与旧任务晚到均不得让撤权失效；自动对账恢复待办”。即便增加 WP 侧 webhook 推送，依然不能取消 VPS 侧的定时对账 timer，且 `selections.sqlite` 的周期性过期清理也依赖该 timer。
- **方案 (c)【不推荐】：维持现状（`1m`）**。
  - **不推荐理由**：实测 98.16% 的触发（约 1,200 次/天）是纯空转，且每次空转不仅在 VPS 上白白启动 Python，还跨公网触发 WordPress 全量构造 `Publication::manifest()` 与写库加锁，每天在 Hostinger 上制造约 18 次无意义的 500/503/超时失败日志。

---

## 5. 结论摘要

**推荐方案 (a)**：将 `services/engine/ops/linker-engine-feed-sync.timer:7`（及 VPS `/etc/systemd/system/linker-engine-feed-sync.timer`）的 `OnUnitInactiveSec=1m` 调整为 `OnUnitInactiveSec=15m`（同步更新 `services/engine/ops/PUBLICATION.md:85, 89` 中的文案描述），在零架构改动、零安全回退的前提下消除 92% 以上的无效 Python 启动与 WordPress 远端锁竞争。
