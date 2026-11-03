# 生产负载治理只读读回与受控验证报告（Load Governance Readback）

日期：2026-11-04（采样窗口覆盖 2026-10-28 至 2026-11-04 00:12 CST / 2026-11-03 16:12 UTC）
范围：只读排查与受控验证，未直接修改任何生产环境配置或数据库记录；所有需修复项均给出精确改动方案与建议部署顺序，由父线单写入者统一执行。

---

## 1. Hostinger 共享主机四站 CPU 100%/90%+ 与 IOPS 512 触顶归因

### 1.1 套餐配额与同账号实际托管拓扑

hPanel 生产面板（`https://hpanel.hostinger.com/websites/de-linker.com/order/order-usage`）确认当前账号（`u388076051`，节点 `de-fra-web1798.main-hosting.eu`，套餐 `Business Web Hosting` / `hostinger_business_v3`）由 **4 个域名（实际含 5 套 WordPress 实例 + 2 套独立 Live Helper Chat 实例 + 5 个 MySQL 数据库）** 共享全部 LVE 资源上限：

| 资源维度 | 套餐硬上限（LVE） | 2026-11-04 00:12 CST 实测当前值 | 说明 |
| --- | ---: | ---: | --- |
| CPU | 100% | 实时 1h 均值 **8%**（24h 均值 **16%**，7d 均值 **39%**） | 峰值达 100% 时触发 LVE 限流与 `CPU 限制100 故障` 标记 |
| IOPS | 512 | 实时 1h 均值 **17**（24h 均值 **94**，7d 均值 **288**） | 触顶 512 时磁盘读写排队，导致 PHP worker 与 MySQL 响应延迟陡增 |
| 吞吐量（I/O） | 20,480 KB/s | 实时 < 1,200 KB/s（7d 仅 `10-28 06:00–08:00` 触顶） | 整站备份/迁移期间偶发接近上限 |
| 内存（Memory） | 3,072 MB | 实时 1h 均值 **293 MB**（峰值 < 850 MB） | 远低于 3,072 MB 上限 |
| PHP 工作者 | 60 | 实时 1h 均值 **3**（峰值 6） | 远低于 60 上限 |
| 最大进程数（NPROC） | 120 | 实时 1h 均值 **4**（峰值 11） | 远低于 120 上限 |
| 磁盘空间 | 50 GB | **10.47 GB（21%）** | 剩余 39.53 GB（79%） |
| Inodes（文件与目录数） | 600,000 | **282,083（47%）** | **hPanel 顶栏「过去 24 小时内使用的资源 47%」实为 Inodes 占比，而非 CPU** |

同账号下 5 套 WordPress 实例与数据库规模实测盘点（SSH `wp eval` 只读查询）：

| 实例路径 | 站点域名 | 数据库 | DB 总规模（Top 表合计） | `DISABLE_WP_CRON` | 独立组件 / 异常高频写库插件 |
| --- | --- | --- | ---: | --- | --- |
| `~/domains/de-linker.com/public_html` | `de-linker.com` | `u388076051_D5YLd` | ~121.9 MB | `true`（hPanel 每分钟 CLI cron） | `linker-commerce` / `linker-tools` / `linker-i18n` / `litespeed-cache` |
| `~/domains/metal-divider.com/public_html` | `metal-divider.com` | `u388076051_CZylP` | ~60.8 MB | **`false`**（访客触发 `wp-cron.php`） | 独立 `/chat/index.php`（Live Helper Chat）+ `md-kb-endpoint` + `md-wecom-notify` + `md-inquiry` |
| `~/domains/staging.metal-divider.com/public_html` | `staging.metal-divider.com` | `u388076051_YZcj0` | ~10.6 MB | `true`（无外部 cron，19 项任务滞留 `now`） | 独立 `/chat/index.php`（Live Helper Chat）+ `rapls-ai-chatbot` + `hostinger-reach` |
| `~/domains/sunriver-inverter.com/public_html` | `sunriver-inverter.com` | `u388076051_9SZnb` | **~268.8 MB** | **`false`**（访客触发 `wp-cron.php`） | `download-monitor`（`xqs_download_log` **387,214 行 / 125.17 MB**）+ `sg-security`（日写 623–1,752 条）+ `translatepress-multilingual`（10 语种词典表 **~106 MB**）+ `W3TC` |
| `~/domains/sunriver-inverter.com/public_html/stg` | `stg.sunriver-inverter.com` | `u388076051_oLeGH` | **~208.8 MB** | **`false`**（访客触发 `wp-cron.php`） | `download-monitor`（`xqs_download_log` **255,024 行 / 90.14 MB**）+ `sg-security` + `translatepress-multilingual`（10 语种词典表 **~100 MB**） |

---

### 1.2 历史 CPU 100%（7d 共 5 次）与 IOPS 512 触顶（7d 共 28 次）的三层根因归属

结合 hPanel 7 天（`10-28 00:00` 至 `11-04 00:00 CST`，85 个 2 小时聚合点）、24 小时（`11-03 00:00` 至 `11-04 00:00 CST`，73 个 20 分钟聚合点）、四站分时请求矩阵及 SSH 磁盘/数据库日志时间戳，历史负载触顶由以下三类具体源头共同构成：

#### 根因 A（已治理 90%+）：`de-linker.com` 工程/知识清单无缓存全量 PDF 磁盘哈希 × 1 分钟高频轮询

1. **机制与实测证据**：
   - 在 PR `#843`（`2026-11-01 20:56 UTC` / `11-02 04:56 CST` 上线）之前，`Publication::manifest()` 仅做单次请求内去重，不持久化文件哈希。每次调用都会遍历全部 85–88 款已发布商品及工程参考件，并对 **144–146 份托管 PDF 原件（数千页、数百 MB）逐一执行磁盘 `hash_file('sha256')`**。
   - 生产实测单次冷 `Publication::manifest()` 耗时 **wall 3,772.1 ms / CPU 3,493.5 ms**（其中 146 次 `hash_file` 占 **3,152.9 ms CPU / 3,175.2 ms wall**，外加 909 次 SQL 查询）。
   - 与此同时，VPS 上的 `linker-engine-feed-sync.timer` 自 `2026-10-23` 起被设为 **每 1 分钟** 触发一次 `POST /wp-json/linker/v1/publication/jobs/claim`（日均 **~1,200 次**，98.16% 空转），每次空转都在 `Lock::run('publication-jobs')` 锁内强制组装完整 `Publication::manifest()`。
   - 当 1 分钟一次的 `/jobs/claim` 与本机知识构建 worker（`POST /wp-json/linker/v1/publication/identify` 批量正则匹配 374 个文本窗口）、前台配置器请求（每次计算前/后请求 `GET /wp-json/linker/v1/publication/manifest`）或全站多视口验收并发重叠时，直接把 512 IOPS 与 100% CPU 打满。
2. **对应的历史峰值窗口**：
   - `10-28 04:00 CST`（CPU 100%，IOPS 512）：四站请求 `927 (de-linker) / 330 (metal-divider) / 587 (staging.metal-divider) / 145 (sunriver)`，对应 `de-linker` 与 `staging.metal-divider` 密集部署及验收。
   - `10-29 14:00 CST`（CPU 100%，IOPS 512）：四站请求 `610 / 64 / 0 / 118`。
   - `10-30 00:00 CST`（CPU 100%，IOPS 512）：四站请求 `6,635 / 109 / 0 / 159`（`de-linker` 全站扫描与知识库密集批次）。
   - `10-30 14:00–15:40 CST`（CPU 100%，IOPS 512）：四站请求 `845–1,566 / 16–345 / 16–20 / 144–158`。
3. **残余点（本次新定位）**：
   - `Publication::manifest()` 已传入 `DocumentFiles::begin_read(true)`（启用 `linker_publication_document_hashes_v1`），但 `Publication::library_read()`（`/downloads/` 资料库页面）、`Publication::product_library_read()`（产品详情页 FAQ 引用校验）与 `Publication::allows_document()`（PDF 原件下载门禁）仍调用 `DocumentFiles::begin_read(false)`（见 `plugins/linker-commerce/includes/Products/Publication.php:276,296,317` 与单元测试 `DocumentFilesTest.php:114-117` 对直接下载不读缓存的显式约束）。
   - 生产实测对比：`Publication::manifest()`（命中 stat 缓存）耗时 **`wall=0.513s, user=0.276s, sys=0.054s, inblock=0`**；而 `Publication::library_read()`（未用跨请求哈希缓存）耗时 **`wall=1.721s, user=1.514s, sys=0.114s, inblock=16`**。因公开页面有 LiteSpeed 整页缓存保护，正常访客命中缓存；仅在整站 `litespeed-purge` 后的首次冷访问 `/downloads/` 时会产生约 1.7 秒 CPU 开销。

#### 根因 B（11-03 唯一 CPU 100% 与两次 IOPS 512 的直接来源）：`metal-divider.com` 密集部署、WindPress 编译与 Live Helper Chat 轮询

hPanel 24 小时视图（`11-03 00:00` 至 `11-04 00:00 CST`）显示，在 `de-linker.com` 上线 `#843` 文件哈希缓存后，全天 **唯一一次 CPU 100%（`11-03 14:00 CST`）** 与 **仅有的两次自然 IOPS 512（`11-03 13:20 CST`、`11-03 18:20 CST`）** 均与 `metal-divider.com` 的生产写入及聊天压测精确吻合：

| hPanel 24h 峰值窗口（CST / UTC+8） | 对应 UTC 时间 | CPU | IOPS | SSH 实测跨站活动证据（精确到秒） |
| --- | --- | ---: | ---: | --- |
| `11-03 13:00 CST` | `05:00 UTC` | 69% | 7 | `metal-divider.com` 于 `05:06:13–05:08:59 UTC` 连续写入 `md-site`（`inquiry.css`、`pattern-grid.css`、`custom-screens.html`、`md-chrome.js`）与 `md-inquiry`（`inquiry.js`、`Submission.php`、`Emails.php`） |
| `11-03 13:20 CST` | `05:20 UTC` | 35% | **512** | `metal-divider.com` 于 `05:33:32 UTC` 写入 `uploads/windpress/data/{inquiry,pattern-grid}.css`、批量更新 25 个 `lc_dynamic_template` 及 346 个 revision，并于 `05:36:08 UTC` 切换 `public_html` |
| `11-03 14:00 CST` | `06:00 UTC` | **100%** | 11 | `metal-divider.com` 于 `05:46:43–05:46:45 UTC` 再次更新 `md-inquiry`（`Pattern.php`、`Form.php`）并跑验收；同时 `sunriver-inverter.com` 在 `06:00 UTC` 小时段出现全天最高的 **61 次 `sgs_log_events` + 22 次 `download_log` 写库** |
| `11-03 18:20 CST` | `10:20 UTC` | 12% | **512** | `metal-divider.com` 于 `10:06:26–10:29:32 UTC` 部署 Live Helper Chat（`chat/extension/mdvisitor/...`、`settings.ini.php` 于 `10:20:36 UTC`）并密集触发 `md-kb-endpoint` 模型调用与 `chat/index.php`（`10:14:01 UTC` 报 `PDOException: 2006 MySQL server has gone away`），叠加 `de-linker` `feed-sync` 1m 轮询的最后阶段（`10:23:51 UTC` 切为 15m） |

此外，`metal-divider.com` 当前 `DISABLE_WP_CRON=false`，且注册了两个每分钟执行的钩子（`action_scheduler_run_queue`、`md_inquiry_mail_tick`），每次前台页面或聊天组件请求都会触发 WordPress 内部 cron 锁竞争。

#### 根因 C（长期背景 IOPS 与慢查询噪音源）：`sunriver-inverter.com`（含 `/stg`）爬虫写库风暴

1. **数据库膨胀与全天候写入**：
   - `sunriver-inverter.com` 与其子目录克隆站 `sunriver-inverter.com/stg` 占用了共享 MySQL 约 **477.6 MB**。
   - `xqs_download_log` 在主站已累积 **387,214 行（125.17 MB）**、在 `/stg` 累积 **255,024 行（90.14 MB）**；过去 14 天主站每天仍新增 **212–1,241 行**。
   - 主站启用了非 Hostinger 环境的 `SiteGround Security Optimizer`（`sg-security` 1.6.2），过去 14 天每天向 `xqs_sgs_log_events` 写入 **623–1,752 条**访客/爬虫记录（每小时 20–61 次），每次未知 IP 访问均执行 `SELECT ID FROM xqs_sgs_log_visitors`、`SHOW TABLES LIKE 'xqs_sgs_log_visitors'`、`SHOW FULL COLUMNS FROM xqs_sgs_log_events` 与 `INSERT`。
2. **`TranslatePress` × `sg-security` 错误回调死循环（`~/.logs/error_log_sunriver-inverter_com` 实证）**：
   - 主站与 `/stg` 均启用了 `translatepress-multilingual` 10 个目标语种，共有 11 张 `xqs_trp_*` 大表（主站约 **32 万行 / 106 MB**，`/stg` 约 **100 MB**）。
   - 当 `sg-security` 在 `log_visit` 中遇到数据库连接抖动触发 `__() / gettext('Could not retrieve table charset.')` 时，`TRP_Process_Gettext` 在错误处理路径中拦截该字符串并尝试对 `xqs_trp_gettext_original_strings` 执行 `SELECT ... IN (CAST(... AS BINARY))` 与 `INSERT`，引发成串的 `WordPress database error Commands out of sync; you can't run this command now` 错误日志与无效 I/O。
   - 主站与 `/stg` 均处于 `DISABLE_WP_CRON=false` 状态，且每周一凌晨各自通过 `mail()` 发送 SiteGround 周报邮件，占用四站共享的 Hostinger `mail()` 配额（100 封/24h）。

---

### 1.3 治理前后对比数据（hPanel 实测）

| 指标 / 阶段 | 治理前基线（10-24 至 10-31，7d） | `#843` PDF 哈希缓存上线后、`feed-sync` 仍为 1m（11-03 00:00–18:20 CST，56 个 20m 桶） | `#872` `feed-sync` 改为 15m 后（11-03 18:40–23:40 CST，16 个 20m 桶） | 实时静默窗口（11-03 23:12–23:54 CST，43 个 1m 桶） | 变化幅度（较治理前） |
| --- | ---: | ---: | ---: | ---: | --- |
| `Publication::manifest()` 单次 CPU | 3,493.5 ms（146 次 `hash_file`） | 321.8 ms（0 次 `hash_file`） | 276.0 ms user + 54.0 ms sys | 276.0 ms user | **-90.8%** |
| `linker-engine-feed-sync` 触发频率 | ~55 次/小时（~1,200 次/天） | ~55 次/小时 | **3.8 次/小时（21 次 / 5.5h）** | 4 次/小时 | **-92.9%** |
| Hostinger 账号 CPU 均值 | **41.0%** | 16.5% | **14.6%**（含 2 次跨站部署） | **5.1%**（全 1h 含 SSH 探针为 8%） | **-64.4% ~ -87.6%** |
| Hostinger 账号 CPU 100% 次数 | 5 次 / 7d | 1 次（`14:00` `metal-divider` 部署） | **0 次** | **0 次**（最高 12%） | **消除常驻冲顶** |
| Hostinger 账号 IOPS 均值（上限 512） | **271.0** | **113.8**（基准常驻 110–187） | **29.8**（区间 1–114） | **2.1**（全 1h 含探针为 17） | **较 1m 阶段再降 73.8%（较 7d 基线降 89.0%）** |
| Hostinger 账号 IOPS 512 触顶次数 | 24 次 / 85 点（28.2%） | 2 次 / 56 点（`13:20`、`18:20`） | **0 次 / 16 点（0%）** | **0 次** | **自然触顶归零** |

---

## 2. VPS 定时维护与回收结果读回（`cache-clean`、`feed-sync`、`#850` Planner 维护）

### 2.1 `linker-engine-feed-sync.timer`（15m 周期生效验证）

- **VPS 生产定义读回**：`/etc/systemd/system/linker-engine-feed-sync.timer` 已与仓库 `services/engine/ops/linker-engine-feed-sync.timer` 一致（`OnBootSec=1m`、`OnUnitInactiveSec=15m`、`Persistent=true`），于 `2026-11-03 10:23:51 UTC` 重启生效。
- **运行与真实同步读回（`10:23:51 UTC` 至 `15:54:00 UTC`，共 5.5 小时）**：
  - 共触发 **21 次**（间隔严格为 15 分钟：`10:38:08`、`10:53:26`、`11:08:58`、`11:24:01`、`11:39:13`、`11:54:21`、`12:09:26`、`12:25:06`、`12:40:09`、`12:55:26`、`13:10:47`、`13:26:26`、`13:41:46`、`13:56:51`、`14:11:59`、`14:27:02`、`14:42:16`、`14:57:18`、`15:12:26`、`15:27:56`、`15:43:04 UTC`）。
  - 其中 **18 次** 为正常空转（`deleted 0 expired confirmed-result receipts` + `no pending engineering preparation`，单次 CPU `128ms`），**1 次** 在 `12:55:26 UTC` 真实认领并发布 `#878` 电池销售单元新数据（`published and loaded source d47df3a3da4cb4f0f88dc254bcfbb3203285372c604586d0175f48ad6d9a1177 (85 products)`，耗时 12 秒完成原子切换与 `linker-engine.service` 重启），**2 次**（`10:53:26`、`12:40:09 UTC`）因远端瞬时连接超时退出并在下一个 15 分钟周期自动恢复。

### 2.2 `linker-engine-cache-clean.timer` 自然触发与路径漂移发现

- **自然触发读回**：
  - `systemctl status linker-engine-cache-clean.timer`：`active (waiting)`，上次触发时间为 **`Mon 2026-11-02 00:00:00 UTC`**，下次触发时间为 `Mon 2026-11-09 00:00:00 UTC`。
  - `journalctl -u linker-engine-cache-clean.service`：`Nov 02 00:00:00` 启动并成功退出（`Main PID: 434324 (code=exited, status=0/SUCCESS)`，`CPU: 8ms`）。
- **真实回收结果与路径漂移缺陷**：
  - 生产 `/etc/systemd/system/linker-engine-cache-clean.service` 当前定义为：
    ```ini
    [Unit]
    Description=Prune old linker-design-engine PVGIS cache files
    [Service]
    Type=oneshot
    ExecStart=/usr/bin/find /var/cache/linker-engine -type f -mtime +30 -delete
    ```
  - `stat /var/cache/linker-engine` 与 `/var/cache/linker-engine/matplotlib` 读回：
    - 两个目录的 `Modify` 与 `Change` 时间戳均为 **`2026-11-02 00:00:00.196880784 +0000`**，且 `/var/cache/linker-engine` 目录项表大小达 `401,408 Bytes`（历史曾存放大量缓存文件），当前目录下普通文件数为 **0**。这证实 `2026-11-02 00:00:00 UTC` 的自然触发确实扫描并删空了 `/var/cache/linker-engine` 中最后一批满 30 天的历史遗留文件。
  - **但存在两项配置漂移风险**：
    1. 自 `2026-10-23` 缓存目录迁移（`services/engine/ops/PUBLICATION.md:62-66`）后，`linker-engine.service` 与 `linker-engine-feed-sync.service` 实际使用 `LINKER_ENGINE_CACHE=/opt/linker-engine/state/cache`（当前含 `pvgis/` 5 个文件 3,148 B、`lod2/` 3 个文件 999,033 B、`private/selections.sqlite` 638,976 B、`private/slots.sqlite` 16,384 B）；而 `/var/cache/linker-engine` 与 `/root/.cache/linker-engine`（残留 Oct 14–23 的 8 个文件）已不再被当前服务写入。
    2. **安全边界警告**：切勿将 `ExecStart` 简单改为 `find /opt/linker-engine/state/cache -type f -mtime +30 -delete`——否则当 `private/selections.sqlite` 或 `private/slots.sqlite` 超过 30 天无写入时（例如 `slots.sqlite` 当前 `mtime` 为 `Oct 23 23:28`，距满 30 天仅剩 19 天），会被 `find -delete` 误删！必须仅针对 `pvgis` 与 `lod2` 子目录清理（见第 4 节修复方案）。

### 2.3 `#850` Planner 维护（`com.linker.planner-maintenance`）自然触发结果与超时根因

- **自然触发读回**：
  - 本机状态文件 `/Users/chesterjohn/de-linker-data/planner-production/maintenance-f1b360b43ebcffaaacb556a4f624eb46.json` 与 macOS Unified Log（`syslog`）记录：
    - `2026-11-03` 自然窗口触发时间：**`2026-11-03T02:20:12.219785+00:00`**（北京时间 `10:20:12`）。
    - 执行结果：**`{"phase": "plan", "reason": "remote_plan_subprocess_timeout", "status": "error"}`**（后续每小时唤醒均按设计返回 `{"reason": "outside_UTC_window", "status": "skipped"}` 并保留 `last_failure`）。
  - VPS `sar`（`/var/log/sysstat/sa03`）在 `02:20:09 UTC` 同步印证：系统页缓存 `kbcached` 从 `1,844,964 kB` 跳升至 `2,174,716 kB`（**+330 MB**），`ldavg-1` 升至 `0.59`，证实远端 `plan` 阶段已启动并读取了工作区 CAS blobs，但在完成前被 30 秒子进程超时终止。
- **当前 VPS Planner 工作区只读 `retention` 计划实测**：
  - 在生产当前版本 `/opt/linker-planner/releases/08256b932b3bec053a221c95d328152fe318859c86b5872600f518ec1c3946e6` 上只读执行 `planner_release.py retention`：
    ```json
    {
      "advisory": true,
      "candidate_bytes": 10449376,
      "candidate_count": 3,
      "candidate_sha256": [
        "b56587b6f33d8499d78b9b77a21c0b20ecbeecaaa6ee0c8d310da623e317c0c1",
        "bbe8fc09a1ad56e84f5295197c181d1c03dc14ecf14793bb34c0333f5c44d86c",
        "f4e59fb2630664d2f39754f9f5d83a3d56f139351ce05bbabc3df103e8efbd7f"
      ],
      "deleted_bytes": 0,
      "deleted_count": 0,
      "mode": "plan",
      "retained_count": 1083,
      "schema_version": 1,
      "temporary_count": 0,
      "temporary_deleted_count": 0
    }
    ```
  - **实测耗时**：冷页缓存首次执行 **`real 27.289s`（`user 16.906s`, `sys 9.571s`）**；热页缓存二次执行 **`real 19.899s`（`user 17.062s`, `sys 2.380s`）**。当前有 **3 个未引用候选 blob（共 10,449,376 Bytes ≈ 9.97 MiB）** 待回收，1,083 个有效 blob 被保留。
- **定位到的三项具体缺陷（解释为何 `#850` 后仍发生 `remote_plan_subprocess_timeout`）**：
  1. **缺陷 1（`#850` 预算传递遗漏，`services/engine/ops/planner_maintenance.py` & `planner_release.py`）**：
     - PR `#850`（`ebcd20484`）仅在 `planner_release.py:937` 的离线 `--apply --offline` 调用处传入了 `timeout=remaining`（来自 600 秒 `work_deadline`），却遗漏了其余 **4 处** 全量扫描 CAS 的子进程调用，导致它们仍然使用 `Release.operator()` 的默认超时 `self.spec["start_seconds"] = 30` 秒：
       - `services/engine/ops/planner_maintenance.py:79`：`action=='plan'` 中 `plan=r.operator('retention')` 未传 `timeout`，固定 30 秒超时；
       - `services/engine/ops/planner_release.py:878`：`maintain()` 在 `not apply` 时 `return release.operator(*arguments)` 未传 `timeout`，固定 30 秒超时；
       - `services/engine/ops/planner_release.py:888`：`maintain(apply=True)` 停服前预检 `plan = release.operator("retention", *arguments[1:])` 未传 `timeout`，固定 30 秒超时；
       - `services/engine/ops/planner_release.py:729-758, 893`：`release.recovery_covers()` 对恢复归档全量运行 `independent_snapshot()`（含 1,083+ 个 blob 校验），硬编码 `timeout=self.spec["start_seconds"]`（30 秒）。
     - 随着生产 CAS 从 629 个（10-31）→ 843 个（11-02）增长至 **1,086 个（11-03，约 330 MB）**，单核 VPS 冷缓存 `retention` 计划耗时已达 **27.3 秒**，凌晨 `02:20 UTC` 稍有磁盘抖动即突破 30 秒 `start_seconds` 硬阈值，在 `plan` 阶段直接报 `remote_plan_subprocess_timeout`。
  2. **缺陷 2（本机 `launchd` 加载状态漂移）**：
     - `launchctl print gui/501/com.linker.planner-maintenance` 实测显示，本机内存中的 launchd 任务仍绑定在 `/Users/chesterjohn/Library/LaunchAgents/com.linker.planner-maintenance.previous.plist`（执行路径指向 `releases/d90ff09dc271357141a417871aeaaadd3da97f9d`，即 `#849`），而磁盘上的 `com.linker.planner-maintenance.plist` 虽已更新为 `releases/a9c6a378e613776d75eb6e57d89f71fd94cbfc8c`（`#850`），但未完成 `bootout` + `bootstrap` 切换。
  3. **缺陷 3（VPS 当时尚未部署含 `#850` 的 Planner release）**：
     - `2026-11-03 02:20 UTC` 自然触发时，VPS 上的 Planner 还在运行旧 release；含 `#849/#850` 的新 Planner release `08256b93...` 于当日 `09:12 UTC`（`17:12 CST`）才激活上线。

---

## 3. VPS（1 vCPU / 3,915 MB / 0 Swap）负载评估与资源边界确认

### 3.1 硬件、内核与全天负载实测（`ssh linker-services`）

- **主机规格**：`srv1791674`，`AMD EPYC 9354P` **1 vCPU**，物理内存 **3,915 MiB（`4,009,192 kB`）**，**Swap = 0 B（`SwapTotal: 0 kB`, `Zswap: 0 kB`）**，根分区 **48 GiB**（已用 `5.1 GiB`，可用 `43 GiB`）。
- **内核 OOM 记录**：`dmesg -T | grep -i -E "oom|out of memory|killed process"` 输出为空（**历史 0 次内核 OOM kill**）。
- **当前内存水位（`2026-11-03 15:55 UTC`）**：
  - `MemTotal: 3,915 MiB` | `MemUsed: 1,062 MiB` | `MemFree: 530 MiB` | `Buff/Cache: 2,605 MiB` | **`MemAvailable: 2,853 MiB（可用率 72.9%）`**
  - `AnonPages: 669.2 MiB` | `Slab: 298.0 MiB`（其中 `KReclaimable: 227.1 MiB`）| `Committed_AS: ~1,425 MiB（36.4%）`
- **`sysstat`（`sar`）连续 48 小时运行统计**：
  - `2026-11-02` 全天平均：CPU `%user 7.39%`、`%nice 3.95%`、`%system 2.65%`、`%iowait 0.04%`、`%steal 0.79%`、**`%idle 85.18%`**；`ldavg-1` 均值 `0.13`；`kbavail` 均值 `2,695 MiB`（最低点 `01:20 UTC` 96 块组件测试期间 `kbavail = 1,818 MiB`，`%memused = 44.56%`）。
  - `2026-11-03`（`00:00–15:50 UTC`）：CPU **`%idle` 均值 > 96%**，`ldavg-1` 均值 **`0.06`**（最高 `09:40 UTC` `0.82`、次高 `02:20 UTC` `0.59`），`kbavail` 始终保持在 **`2,602–2,892 MiB`**。

### 3.2 常驻服务进程与 systemd 资源边界盘点

| systemd 单元 | PID / 运行用户 | 当前 cgroup 内存 (`MemoryCurrent`) | 历史峰值 (`MemoryPeak`) | 进程 RSS | `OOMPolicy` | `MemoryMax` / `CPUQuota` | 委托隔离 (`Delegate`) |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `linker-planner-http.service` | `521902` (`linker-planner`) | 214.6 MiB | **366.0 MiB** | 273.5 MiB | `stop` | `infinity` / `infinity` | 无 |
| `linker-planner-worker.service` | `522001` (`linker-planner`) | 159.0 MiB | 159.3 MiB | 222.1 MiB | `continue` | `infinity` / `infinity`（扩展子任务限 **1,200 MiB / 20% CPU / 0 Swap / 16 pids**） | `cpu memory pids` (`supervisor`) |
| `linker-engine.service` | `537491` (`root`) | 138.4 MiB | 140.1 MiB | 201.9 MiB | `stop` | `infinity` / `infinity` | 无 |
| `linker-genie.service` | `538530` (`root`) | 48.6 MiB | 49.3 MiB | 64.5 MiB | `stop` | `infinity` / `infinity` | 无 |
| `linker-genie-judge.service` | `538531` (`root`) | 31.6 MiB | 32.0 MiB | 47.2 MiB | `stop` | `infinity` / `infinity` | 无 |
| `nginx.service` | `215279` (`root`/`www-data`) | 3.0 MiB | 5.1 MiB | 16.8 MiB | `stop` | `infinity` / `infinity` | 无 |
| 其他常驻（`monarx`/`xray`/`hysteria`/`journald`） | 各独立单元 | ~108 MiB 合计 | — | ~108 MiB | — | — | — |
| **常驻基线合计** | — | **~703 MiB** | **~860 MiB** | **~934 MiB** | — | — | — |

### 3.3 零 Swap 环境下的容量边界结论

1. **常规稳态与单次扩展计算安全**：
   - 常驻基线占用后主机仍余 **~2,850 MiB `MemAvailable`**。
   - 96 块组件全年 8,760 小时扩展任务（`expanded_job`）在 `linker-planner-worker` 下受双重保护：准入前强制检查主机 `MemAvailable >= 1,536 MiB`（`minimum_available_bytes = 1,610,612,736`），运行时放入独立子 cgroup（`memory.max = 1,200 MiB`、`swap.max = 0`、`cpu.max = 20%`、`nice = 19`），实测子 cgroup 峰值 `815–894 MiB`，单任务运行时主机仍余 `> 1,800 MiB` 可用内存。
2. **剩余边界风险（需关注的叠加场景）**：
   - **风险 1（多峰值叠加无 Swap 缓冲）**：若同一时刻发生「扩展任务子进程（`~894 MiB`）+ 普通 worker 报告/CSV 生成（`~250–400 MiB`）+ `planner-http` 大体积 CSV 流式响应（峰值 `366 MiB`）+ 外部部署 `uv sync` 或 `planner_maintenance` 全量 `backup.serialize()` 内存快照（`~300–500 MiB`）」，瞬时匿名内存需求可达 `2.5–2.9 GiB`，逼近 `3,915 MiB` 无 Swap 硬边界。
   - **风险 2（顶层服务无 `MemoryMax` 与 `OOMPolicy=stop` 语义）**：`linker-engine`、`linker-genie`、`linker-planner-http` 均未设置顶层 `MemoryHigh`/`MemoryMax`，且默认 `OOMPolicy=stop` 配合 `Restart=on-failure`——一旦子进程触发 cgroup OOM，systemd 将直接停止整个服务单元且可能不触发 `on-failure` 自动拉起（仅 `linker-planner-worker` 已正确设为 `OOMPolicy=continue`）。

---

## 4. 需修复项清单与建议改动（供父线统一执行）

### 修复项 1（P0）：补齐 `#850` Planner 维护在 `plan` 与 `recovery_covers` 阶段的剩余预算传递

- **目标文件**：
  - `services/engine/ops/planner_maintenance.py`
  - `services/engine/ops/planner_release.py`
  - `services/engine/tests/test_planner_release.py`
- **具体改动**：
  1. 在 `services/engine/ops/planner_maintenance.py:79`（`REMOTE` 的 `action=='plan'` 分支）：
     将 `plan=r.operator('retention')` 改为使用剩余维护预算：
     ```python
     else:
         remaining = work_deadline - time.monotonic()
         if remaining <= 0: raise TimeoutError('maintenance_budget_expired')
         result.update(status='idle', plan=r.operator('retention', timeout=remaining))
     ```
  2. 在 `services/engine/ops/planner_release.py`：
     - `Release.recovery_covers()`（第 729–758 行）增加可选 `timeout: float | None = None` 参数，传给 `command(..., timeout=self.spec["start_seconds"] if timeout is None else timeout)`；
     - `maintain()`（第 862–940 行）新增内部辅助函数 `_remaining_budget(work_deadline)`，并在第 878 行（`if not apply:`）、第 888 行（`plan = release.operator("retention", ...)`）及第 893 行（`release.recovery_covers(...)`）统一传入 `timeout=_remaining_budget(work_deadline)`；
     - `main()` 第 1023 行将 `work_deadline=time.monotonic() + args.work_seconds` 同时应用于只读 `retention` 与 `--apply`，使 CLI 默认 600 秒 `--work-seconds` 在 `plan` 阶段同样生效。
  3. **说明**：`services/engine/src/linker_engine/planning/runtime_snapshot.py` 仅哈希 `src/`、`schemas/`、`pyproject.toml`、`uv.lock`，不包含 `ops/`，因此该改动**不改变 `RuntimeSnapshot` 哈希，无需重导跨平台算例夹具**。

### 修复项 2（P1）：VPS `linker-engine-cache-clean.service` 路径修正与入库 + 旧缓存清理

- **目标文件**：新增 `services/engine/ops/linker-engine-cache-clean.timer` 与 `services/engine/ops/linker-engine-cache-clean.service`，并在 VPS `/etc/systemd/system/` 同步更新。
- **建议单元内容（保护 `private/*.sqlite` 不被误删）**：
  ```ini
  # /etc/systemd/system/linker-engine-cache-clean.service
  [Unit]
  Description=Prune old linker-design-engine PVGIS and LOD2 cache files

  [Service]
  Type=oneshot
  ExecStart=/usr/bin/find /opt/linker-engine/state/cache/pvgis /opt/linker-engine/state/cache/lod2 -type f -mtime +30 -delete
  NoNewPrivileges=true
  PrivateTmp=true
  ProtectHome=true
  ProtectSystem=strict
  ReadWritePaths=/opt/linker-engine/state/cache/pvgis /opt/linker-engine/state/cache/lod2
  ```
- **一次性旧目录清理命令（VPS）**：
  核对无进程打开后，清理已废弃的 `/root/.cache/linker-engine`（8 个 10 月旧文件）与空的 `/var/cache/linker-engine`（401 KB 空目录项表）：
  ```sh
  ssh linker-services 'lsof +D /root/.cache/linker-engine /var/cache/linker-engine || true'
  ssh linker-services 'rm -rf /root/.cache/linker-engine /var/cache/linker-engine && systemctl daemon-reload'
  ```

### 修复项 3（P1）：Hostinger 同账号非 `de-linker` 站点的后台负载止血（需业主确认后由父线执行）

1. **`sunriver-inverter.com` 与 `sunriver-inverter.com/stg`**：
   - 在两站 `wp-config.php` 中开启 `define('DISABLE_WP_CRON', true);`（主站如仍需定时任务，可挂低频 CLI cron；`/stg` 克隆站建议完全停用 cron，消除每周重复发信与后台任务）。
   - 停用两站上的 `sg-security`（SiteGround 专用插件在 Hostinger 上无效且每天产生上千次访客表写库及 `TranslatePress` 错误回调死循环）。
   - 清理或截断两站膨胀的 `xqs_download_log`（主站 125.17 MB / 38.7 万行，`/stg` 90.14 MB / 25.5 万行，合计可释放 **215 MB** 数据库空间并消除爬虫下载日志写放大）。
2. **`metal-divider.com` 与 `staging.metal-divider.com`**：
   - `metal-divider.com`：在 `wp-config.php` 设置 `define('DISABLE_WP_CRON', true);` 并改由 hPanel CLI cron 驱动，避免前台访问触发 `wp-cron.php`。
   - `staging.metal-divider.com`：清理滞留在 `now` 的 19 个到期 cron 事件或按需仅在测试期手动触发。

---

## 5. 建议部署与执行顺序（供父线统一调度）

1. **第一步（本机与 VPS 维护链路修复，零停服）**：
   - 合入修复项 1（`planner_maintenance.py` + `planner_release.py` 预算传递修复）与修复项 2（`linker-engine-cache-clean.{timer,service}`）。
   - 在 VPS 当前 Planner release（或随下一 Planner release）更新 `ops/planner_release.py`，并在 VPS 安装新版 `/etc/systemd/system/linker-engine-cache-clean.service` 后执行 `systemctl daemon-reload`，清理 `/root/.cache/linker-engine` 与 `/var/cache/linker-engine`。
   - 在本机更新 `/Users/chesterjohn/de-linker-ops/planner-maintenance/releases/<merged-sha>`，通过 `install_planner_maintenance.py` 渲染并重新 `bootout` + `bootstrap` `com.linker.planner-maintenance.plist`，使 `launchctl print gui/501/com.linker.planner-maintenance` 指向最新 release（替换当前残留的 `.previous.plist`），在下一个 `02:00–03:00 UTC` 自然窗口回收当前 3 个候选 CAS blob（10.0 MiB）。
2. **第二步（Hostinger 兄弟站点止血，经业主确认后执行）**：
   - 先对 `sunriver-inverter.com` 与 `metal-divider.com` 数据库做本机快照备份。
   - 停用 `sunriver-inverter.com`（及 `/stg`）的 `sg-security`、设置 `DISABLE_WP_CRON=true`、截断 `xqs_download_log`。
   - 为 `metal-divider.com` 开启 `DISABLE_WP_CRON=true`。
