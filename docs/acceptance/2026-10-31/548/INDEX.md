# #548 安装事实线 · 验收索引（2026-10-31）

## 2026-10-31 接管：当前结论与首批资源修复

本索引合并了同目录 `INDEX.md` 与 `index.md`；两个仅大小写不同的路径会在 macOS 上相互覆盖。下方较新的具名验收取代旧节相同项目的未验证状态，未扩展到未经验证的范围。生产验收提交不等同自然客户询盘，局部材料清单不等同完整安装 BOS。

本次统一工作树为 `/Users/chesterjohn/.codex/worktrees/installation-facts-548/de-linker`，分支 `codex/runtime-lifecycle-ci`；负责人当前总 goal 会话。复用既有干净工作树，不新增实例或整站副本。新增/修改的源码随能力保留；测试临时 SQLite、发布目录与子进程仅保留测试期，由执行者在退出路径回收。分支在合并及本批验收完成后删除，未提交实现和唯一证据保留。

### 当前只读生产采样（2026-10-31 02:58–03:06 UTC）

- VPS：1 CPU，load 0.07/0.02/0.00，短采样 CPU idle 97–99%，内存可用约 2717 MiB；磁盘 48 GiB 中用 5.1 GiB，可用 43 GiB。四项 Engine/Genie/Planner HTTP/worker 服务 active，NRestarts=0。本次采样未复现即时过载，不证明峰值负载或长期无泄漏。
- Hostinger：64 CPU，共享主机 load 47.34/60.25/53.68；账户可见主要为少量 lsphp，未运行压力测试。挂载卷61%使用不等同本账户配额；不可凭共享load数值归因为本项目过载。观察到CPU/IO压力，具体归属仍需分层测量。
- Planner：18项目、56修订、55任务（53成功、2失败，采样时无queued/running/retry_wait）；数据库294,912 bytes，629个blob合计201,315,654 bytes，无 `.incoming`。只读引用遍历得到6个候选未引用文件、5,203,227 bytes，但1个较大JSON未展开且外部快照引用未排除，**不得按该结果删除**。
- Genie：API和judge均active/enabled，使用默认同目录日志库；706条turn，最早2026-10-13，680条judgment，turn_starts=0。当前无超90天数据积压证据；独立夹具确认清理依赖可选judge以及失败start记录无清理的机制缺口。
- 知识索引三代，各约290.5MB；另有旧incoming目录。存在目录不证明可删除，须按运行/恢复引用和所有权判断。
- WordPress Cron确有 `linker_tools_planner_claim_sweep`，下一时间戳1793417530；AS无同名动作不表示WP Cron未注册。跨attempt重复排队则已有独立失败夹具。

### 本批实现状态

代码候选 `de463f4e` 及自定义日志路径修复 `d6d4f32f` 已完成独立 Spec/Standards 双评审；Spec发现的自定义 `--db` 清理回归已由原CLI失败夹具复现、修复并通过增量复审。尚未部署。

| 有界行为 | 当前验证 |
| --- | --- |
| 本地/CI按模块分流、presentation flags、超时/取消孙代回收、部分up/down失败 | Python3.12定向合同26项通过；recipes dry-run、YAML和Ruff通过；未运行真实站点 |
| Genie 90天清理、失败start、空闲API生命周期、并发写入、ID高水位 | 相关回归79项通过；最终13项retention夹具通过，含旧CLI自定义路径和实际锁库；使用本树PYTHONPATH |
| WordPress资料准备同锁内只组装一次manifest | 17项/118断言通过；PHPStan/PHPCS通过；保留fresh来源读取 |
| 认领扫描/foreground不绕开既有退避任务 | 2项/40断言通过；旧源码失败夹具已复现；PHPStan/PHPCS通过 |
| 服务复制失败保留current且清理半成品 | 4项实际shell发布用例通过；原源码失败留下额外版本目录；bash-n/Ruff通过 |

本批不代表Planner CAS完整引用回收、异常终止残留、服务激活失败全链恢复、Hostinger高峰负载归因、账号认领界面故障或全站完整goal已经完成。主线新增CI检查仍需对最终候选运行；正式生产结论待发布和实际消费者读回。

当前文档中的认证哈希已移除，但旧Git提交仍包含该材料，历史暴露与后续处置未关闭。未执行历史改写或修改生产账号。

### CI 首轮失败与已验证修复（PR #817）

首轮 `41164122644` 的 Python static 在约40秒报新增测试的三处mypy错误；此前本地仅检查受影响src，未执行覆盖测试目录的`mypy .`。已在本地整包精确复现并修复，225文件mypy、整包Ruff/format通过。JS unit的两个既有浏览器用例缺headless shell，根因是去重后下载排在unit之后；本机缓存掩盖此顺序问题。真实`just js-test`空浏览器状态夹具旧红新绿，唯一下载已提前，27项CI合同通过。失败保留，不把局部验证描述为CI全绿。

提交`7926adbc`另补生产现存带source后缀版本的回滚兼容；原脚本夹具失败`no older release`，修后5个实际发布shell用例通过。两轴增量评审均PASS。新版CI与生产结果待实际读回。Planner CAS下一批独立复用`unified-planner-548`工作树（旧已合入补丁分支保留），无新实例或整站副本。

### PR817 发布与第二批资源合同

PR817最终CI `41165087787` 21项成功；已合并为 `f93d026a52a5705a08ce44f7c75a95990395853e`。生产WordPress相对现部署c1fbac217只有PreparationJobs与ClaimOutbox运行源码变化，无模板/样式变化。发布工作树临时选择该合并提交，复用 `/Users/chesterjohn/de-linker-data/cutover-workspace/staging`；本批唯一用途为原子部署的运行依赖暂存，负责人父代理，最多一套，生产读回成功后删除可重建暂存。部署自动流式生成一份 `/Users/chesterjohn/de-linker-data/snapshots/db-<UTC>.sql.gz`，负责人父代理，合并同类计数最多3份，验证保留gzip后删除超限旧文件；主机只保留原子回滚上一版。

首次WP部署在数据库快照和暂存完成后、第一条远端路径查询处SSH断连，尚未上传或切换。独立连接随后恢复；本次重试创建一个任务私有SSH复用socket与临时配置/包装器（系统临时目录linker817-ssh-*，负责人父，最多1套，部署退出finally关闭连接并删除；不修改用户全局SSH设置）。统一复用同一连接减少每个artifact多次握手。

资源回收读回：验证保留3份数据库gzip完整可读后，在`.retention.lock`下删除超限3份（20261030T162636Z、162921Z、164801Z），普通文件合计22,490,016 bytes，分配块合计22,499,328 bytes。保留20261031T035705Z、035505Z和20261030T184016Z，前两份分别为成功重试和首次连接失败前的恢复点；待本批验收后再判断失败尝试重复点是否仍需保留。

第二批复用 `/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548`，分支codex/planner-storage-lifecycle；源码/必要回归随功能保留，无新增实例或整站副本。Planner GC与本地退役仍在交叉评审；不按旧的不完整候选列表删除生产CAS，不删除56个未知用途实例。cutover快照代码由20改3并修正protect重复/不存在/超过上限的计数边界，18项定向验证通过。临时测试目录仅生命周期内保留，执行者负责退出回收。

### 第二批跨平台 fixture 重导资源合同

最终 engine 源码完成增量复审并冻结后，Darwin 复用本树 `services/engine/.venv`，Linux 仅复用 VPS 已有 `/opt/linker-engine/current/.venv/bin/python` 的依赖，实际导出代码来自本批源码。负责人父代理与 `sol_local_retire_implementation`。VPS 仅允许 1 个 `/tmp/linker-planner-fixture-548-storage-lifecycle` 临时目录，装入 engine 源码、tests、schemas、锁文件和必要 fixture 原件，不复制 venv，不读取真实工作区，不监听端口、不启停生产服务。导出通常约 10 秒，执行 `nice -n 19` 并将 BLAS/OpenMP 线程限制为 1，最长 60 秒；成功、失败、超时均由远端 trap 与调用方 finally 精确回收该目录，结束读回目录不存在。本地 exporter 的单份合成 SQLite/CAS 由既有 TemporaryDirectory 退出回收。结果仅覆盖现有两平台 fixture 和 manifest，不新增副本；这些小型合同证据随对应源码保留，后续源码变更时原位重导替换。磁盘本轮读回可用 841 GiB。

跨平台重导结果：engine 增量独立复审无阻塞后，Darwin 与真实 Linux exporter 完成；相对各自上一版均仅 100 个 64hex 身份/派生哈希叶变化，非身份字段变化 0。canonical sorted JSON SHA-256：Darwin `6c2086a3cd75906c49b60851261ef00c6ff9e85bb82840947060365151fb1985`；Linux `050f264a951b9f69c3ec572781c02c6c2c4ae4bed021449dfebcda1372d36529`。只执行完整 Darwin exporter 复现、两平台 manifest、跨平台显式差异 mask 三项合同，3 项通过（10.99 秒）；未重跑未变化单元。Linux 传输包为 442 个源码/必要夹具文件、压缩 1,666,056 bytes，未复制 venv；远端目录与 exporter 临时合成 workspace 均已回收，读回确认远端目录不存在。初次直接调用因缺 tests 导入路径失败；初次 Linux 合成任务因缺间接使用的 PVGIS 原件失败，均在补齐原有导入路径/只读夹具后解决，未修改产品源码或依赖。

CAS 校验的明确边界：计划和恢复点校验拒绝非空 WAL，要求先安全停写并 checkpoint；不会使用 immutable 忽略已提交 WAL 事务。无 WAL 的静态数据库通过 immutable 连接真正只读，回归核验未新增辅助文件、已有文件内容和 mtime 不变。GC apply 由配对服务维护窗口停写后重算。

### 第二批候选与交叉评审结论

Planner CAS回收和本地实例退役已完成Sol/high互补实现及交叉Spec/Standards评审。增量评审发现并修复：恢复点DB/manifest符号链接及硬链接不独立；SQLite只读连接仍写WAL/SHM；显式递归CAS子引用缺失；超时后GC子进程存活；先停PHP阻塞依赖Woo的drain；失败marker使退役无法追加新证据决策；preserve父子路径重叠；WordPress实际代码未列证据；cutover与pull load官方入口绕过实例生命周期锁。有效证据和共享symlink目标保持保护。无真实实例或生产CAS删除。

验证复用：Planner相关archive/operator回归及最后3条进程组回归通过，原实现整包mypy356文件及最终增量mypy/Ruff通过；local最终整包mypy42、cutover24、pull22（均含tests）及Ruff通过；local/cutover/pull新增有效回归24项，snapshot18项。两平台真实exporter仅100个身份hash字段变化、非身份字段0，完整复现/manifest/mask三合同通过。最终交叉评审无未处理阻塞；这些是候选验证，不冒称已部署。

WP批817已切换为20261031T035727515212Z-f93d026a5，原子切换0.021秒。后续verify曾被SSH断开、本机127.0.0.1:1082系统代理Tunnel503和直连失败打断；保持pending恢复点，未重复上传。续读使用VPS内一个stdin驱动的临时HTTPS读取进程（不落文件/不访问生产DB，负责人父，最多1个，resume-deploy退出关闭stdin并wait/必要kill），同一套URL/语言/脚本转义/JSON-LD/同意门验收，归档成功才算该批WP发布收口。

### classic 测试实例实际退役资源合同

总 goal 授权使用已审 PR818 head `93666e477a325231240f25af389e5a024ccff0ac`（CI `41167264856`，21 jobs 成功）顺序退役 `g516classic`、`g520c`。负责人总 goal 与 `sol_local_retire_implementation`。唯一原字节只原子移交至 `/Users/chesterjohn/de-linker-data/retired-instance-evidence/g516classic` 与 `/Users/chesterjohn/de-linker-data/retired-instance-evidence/g520c`，每任务最多 1 份，预期总 584,911 bytes，不复制整站；目录权限 0700，不入 Git。移交范围仅各实例 logs、uploads/wc-logs，另含 g520c 的 mail；待与原任务证据比对确认重复后回收，当前保护这些唯一原字节。工具原生退役锁、停止/移交/精确删 DB/目录/登记/分批 Redis 回收负责执行；不删除共享下载缓存、工作树及其他实例。执行前只读计划须无未决项，保留与丢弃 sibling 范围不重叠；异常停止诊断。前后记录磁盘、登记、DB、Redis 与保留实例连接，不发信、不启动 UI 测试。

## 最新客户链路验收记录


本轮在生产 `de-linker.com` 上完成的读回。每条都附执行方式与实际返回，不写推测。

### 1. 已保存方案 8207 的界面读回

**结论：通过。**

以 user 1（`857558227@qq.com`）会话打开 `https://de-linker.com/solution-configurator/?saved_solution=8207`，页面进入「Start a new project from a saved solution」：

- 标题 `SAJ BU2-5.0-HV1`，`Original inputs` 折叠区存在。
- 已带出 `Grid connection Three-phase`、`Backup supply Not needed`。
- 提示 `Some saved inputs cannot be carried over automatically. They are kept for reference and need review in the new project.` —— 这是设计意图（不能自动搬的保留参考），不是缺陷。

**下载读回**：展开 `Original inputs` 后点 `Download original inputs (JSON)`，得 498 字节文件：

```json
{
  "schema_version": 1,
  "authority": "historical_user_input",
  "solution_id": 8207,
  "title": "SAJ BU2-5.0-HV1",
  "kind": "residential",
  "input": { "locale": "en", "plz": "", "annual_kwh": 0, "pv_kwp": 0, "phase": 3, "backup": "none", "heat_pump": false, "electric_vehicle": false },
  "recorded_items": [ { "product_id": 2090, "quantity": 1 } ],
  "source_sha256": "6dfee710c8f17869436d9cf79ba7625d241b16aee45d535b24062f00b91e7859"
}
```

该链接是客户端 `data:` URL，由 `apps/planner/src/components/SavedSolutionReference.tsx` 从已加载的 `historical_user_input` 生成，不经过服务端。

**归属验证**：同一 URL 在临时管理员会话下报 `Your workspace could not be opened.`，在访客会话下报 `The saved inputs could not be loaded in this session.` —— 8207 属于 user 1，两者无权读取，行为正确。

### 2. 真实询盘提交（含人机验证）

**结论：通过。**

生产 `mode=enforce`、`configured=1`、`ready=1`、`test_keys=false`。Turnstile 为非交互 managed 模式（不显示勾选框，直接进入 `checking → ready`）。

在 `https://de-linker.com/proforma-request/` 填写并提交，生产读回：

| 字段 | 值 |
| --- | --- |
| 订单 ID | `8457` |
| 状态 | `wc-inquiry-received` |
| 邮箱 | `chester@de-linker.com` |
| 创建时间（GMT） | `2026-10-31 02:10:57` |
| 订单总数 | `252 → 253` |

订单行项：

```
GoodWe GW80K-ET-G10      line_item
GoodWe GW61.4-BAT-AC-G10 line_item
DE-MWST. 19%-1           tax
```

草稿里的两个产品都随询盘进入订单，验证了「Solution draft 一并带上」。

关键 meta：

- `_linker_inquiry_source = proforma`
- `_linker_i18n_language = en`
- `_linker_inquiry_topic = general`
- `_linker_inquiry_send_policy = inquiry-mail-v1`
- `_linker_planning_projects` = 一条 `planning_inquiry_reference_v1`，见下节

**邮件**：业主已在原会话确认收到邮件。队列中没有 8457 的记录不能单独证明 transport ACK、Message-ID 或首次发送成功；安全地图要求的自然客户询盘证据仍分别核实。

### 3. 客户下载报告 PDF

**结论：通过，且下载的是冻结报告。**

读取订单 `8457` 的 `_linker_planning_projects` 得到：

| 字段 | 值 |
| --- | --- |
| `handoff_id` | `c7ae5024b3014942bf1c6b7a4ca8fa57` |
| `project_id` | `0bbbb0cce41744aea47d57fc1fabbcb2` |
| `revision` | `4` |
| `title` | `Installation facts acceptance 2026-10-31` |
| `input_sha256` | `ab6534e3a76de858b0ddc8f015715f…` |
| `pdf.sha256` | `b70d599dcfd74eb95e6d66b5cb58d16753106c6830bbf3ab09cde4cc858246e8` |

路由 `GET /wp-json/linker/v1/inquiries/{id}/planning-report/{handoff}?key={order_key}`：

| 场景 | 结果 |
| --- | --- |
| 无 `key`、无会话 | `404` `planning_report_not_found` —— 不泄露报告是否存在 |
| 持有效 `order_key` | `200` `application/pdf`，60322 字节 |

文件本身：

```
PDF document, version 1.4, 6 pages
Title: Project planning report
Producer: ReportLab PDF Library
sha256: b70d599dcfd74eb95e6d66b5cb58d16753106c6830bbf3ab09cde4cc858246e8
```

**该 sha256 与订单里冻结的 `pdf.sha256` 逐字节一致**，证明客户拿到的是询盘时冻结的那份报告，不是重新生成的。

### 4. 生产改动与回滚

本轮为取得 user 1 读回，曾短暂改动生产账号，全部已按原字节回滚：

| 动作 | 状态 |
| --- | --- |
| 建临时管理员 `ss-verify-548`（ID 46） | 已删除 |
| user 1 认证字段临时改写 | 原会话记录称已恢复；凭证材料不应写入验收文档，当前正文已移除，历史暴露仍需处理 |
| 测试邮件重写开关 | 询盘前开、提交后立即关；当前 `off` |
| 前缀残留查询（`ss-verify%`/`ss-probe%`/`example.invalid`） | 空 |
| 生产用户数 | `17 → 16` |

### 5. 本轮发现、尚未修复

**历史邮件记录待分类**：原会话发现 38 条 `private` 邮件记录。安全工作线曾明确保留 38 条 held 攻击相关记录；仅凭数量、日期或 private 状态不能判定投递故障。必须核对实际隔离与派发状态，禁止据此批量重发或删除。

**`Send password reset` 误触**：操作管理列表时误点该链接。WordPress 的该动作在 GET 时发信，但返回 `reset_count=0`（自报未发出任何一封）；当时 `test-mail` 为 `off`，本次会话未更改其状态。业主未报告收到该邮件。

### 6. 环境与资源

| 项 | 值 |
| --- | --- |
| 磁盘可用 | 834 GiB |
| 本轮临时文件 `/tmp/548-*` | 已全部删除 |
| 生产备份 | 未新增（本轮仅账号与开关改动，均即时回滚） |
| 本地实例 | 未启动 |
| 浏览器 | 仅复用既有一个 tab，未新建 |

证据文件保存在仓库忽略目录 `.scratch/`：`548-withkey.pdf`、`548-nokey.json`。


## 先前有限范围验收与排障记录（历史）

以下记录保留过程与边界；与上方较新具名验收冲突时以上方为准。


这份索引只做一件事：让人一眼看出每项**验证到什么程度**、证据在哪、还有什么没验证。
详细记录在两份文档里，这里不重复内容，只给判断。

状态用词是固定的：

- **已读回** —— 在生产上取到了实际数据或报告内容，不是推断。
- **已隔离** —— 失败被定位到具体代码路径，且证明了这是正确行为或已知缺口。
- **未验证** —— 没有证据，附解除条件。

## 生产状态

| 项 | 值 | 状态 |
| --- | --- | --- |
| `knowledge` / `engineering` 消费者 | 均 `ready` | 已读回 |
| 带 `_linker_installation_facts` 的商品 | 534 中 9 个，79 条 | 已读回 |
| `source_revision` | `dc2b9fa7d994…` | 已读回 |
| `preview --production` | `{"changes": 0}` | 已读回 |

## 功能项

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 事实写入商品元数据 | 9 商品 79 条，`verify` 无待办 | `installation-facts-apply.md` |
| 工程 feed 携带事实 | `EngineeringFeed::item()` 含 `installation_facts` | 同上 |
| 引擎物料投影 | `status: documented`，字段与计划一致 | 同上 |
| `project_materials` 消费 | 真实 feed 产 17 条带页码行 | 同上 |
| 报告 BOM（德文，生产读回） | 13 行，德语标签与 `p.152–155` | `installation-facts-apply.md` 德文报告读回 |
| 报告 BOM（英文，生产读回） | 13 行，英文标签与 `p.153–155` | `installation-facts-apply.md` 英文报告读回 |
| 设备检查 | `succeeded`，5 项检查 3 satisfied | 同上 |
| **多台逆变器 + 线缆 + 安装事实** | ✅ 生产读回：项目 `260a61d2…` 报告 25 章节，BOM 16 行含 2 台逆变器与 12 条事实，路由 3 行 | `installation-facts-apply.md` 末节 |
| 路由报告 | `succeeded`，含 `installation-routing` 与免责声明 | 同上 |
| 已保存方案读取（作者） | 返回原始输入，不含旧价格 | `saved-solution-readback.md` |
| 已保存方案权限边界 | 他人读取得 404，不泄露 | 同上 |
| 3D 视图 | 生产渲染出带透视的屋顶平面，无降级提示 | 本文「3D 视图」节 |
| 德语界面 | 导航与屋顶工作区全部德语，无残留英文标签 | 本文「德语界面」节 |
| 同意与统计 | GA 以 `type="text/plain"` 输出，同意前不执行；默认全 `denied` | 本文「同意与统计」节 |
| 旧链接迁移 | 六条旧路径单次 301 落 200 | 本文「旧链接迁移」节 |
| 历史 | 项目可回读旧 revision（16 → 1）；计算历史 5 条跨 revision | 本文「历史」节 |
| 全站可用性 | 14 个关键页面（EN/DE 各 7）全部 200 | 本文首节 |
| 测试 | 引擎 971、PHP 2189 全过 | 本轮执行记录 |

## 已隔离的两处"看起来像缺陷"

| 现象 | 结论 | 依据 |
| --- | --- | --- |
| `Installation routing` 显示 0 | 正确行为 | 该字段来自兼容合同的 `meter`/`backup`，不读安装事实；路由报告另需 `installation.cable_runs` |
| `product_evidence_changed` 拒绝设备检查 | 准备状态的时间差，非数据不一致 | `engineering` 未 `ready` 时 `prepared_view` 不含该商品；恢复后同一项目成功 |

## 未验证（附解除条件）

| 项 | 缺什么 | 解除条件 |
| --- | --- | --- |
| 界面读回 `?saved_solution=8207` | 一个能登录 user 1 的浏览器会话 | 提供凭据，或授权临时启用一次性登录后移除 |
| 真实询盘与 Genie 提交 | 保护**正常工作**；自动化客户端不触发交互，拿不到 token | 人工在浏览器中打开询盘页或 Genie，聚焦表单产生 token 后提交。见下方「Turnstile 的准确状态」 |

## 已合并的修复

| PR | 内容 |
| --- | --- |
| #794 | 引擎拒因码在网关原样透传；文档哈希请求内复用；计划重冻 |
| #795 | 主线计划重冻（原计划 `preview` 直接拒绝） |
| #796 | `refresh` 命令，重 pin 不再靠手改 |

拒因码透传已验证在生产生效：错误码从 `linker_planner_upstream` 变为
`linker_planner_not_found`。哈希复用实测同请求第二次 `manifest()`
从 4.8 s 降到 0.67 s，内容一致。

## 方法注记

`ProductEvidenceChanged` 的 12 个 raise 点共用一个错误码，引擎又丢弃 message。
本轮据此连续做出 6 个错误推断（主机负载 → manifest 重建 → 旧 manifest →
LiteSpeed 缓存 → 兼容合同 → 平台夹具）。正确顺序是**先复现、再读代码**。

另需注意：`sources/saved-solution` 是**网关层路径**（`Gateway.php:302`），
经 `Transport` 直连引擎会得到 `not_found`，看起来像功能坏了，实际不是。

## Turnstile 的准确状态（更正早前的描述）

早前记录写作「Turnstile 拦截询盘」，这个说法**不准确**。实测后的事实：

| 项 | 实测值 |
| --- | --- |
| `Configuration::active_mode()` | `enforce` |
| `ready()` / `configured()` | `true` / `true` |
| `test_keys` | `false`（真实密钥，非测试密钥） |
| `/proforma-request/` 页面 | `200`，**页面内没有 Turnstile 脚本** |
| 验证发生的位置 | 提交时，服务端调 `Protection/Turnstile.php` 的 siteverify |

也就是说：

- **页面不被拦截**。询盘页正常渲染。
- **保护在提交时生效**，且配置正确、使用真实密钥。
- 我的自动化验收拿不到有效客户端 token，因此**提交被正确拒绝**。

这属于「保护按设计工作，自动化客户端不被允许」，不是功能缺陷，也不是「外部条件导致功能未完成」。

真实询盘与 Genie 提交需要**人工在浏览器中完成**——这正是该保护的用途。用自动化绕过它去换取验收通过，是错误的做法，本线没有这样做。

### 一处自我更正

排查过程中我 grep 到两个 `pow`，一度认为存在 proof-of-work 机制。实际是
`/product-category/accessories/backup-power/` 里的子串，属误匹配，已推翻。

### 完整机制（从 `protection.js` 与生产页面读出）

我早先 grep「`/proforma-request/` 页面里没有 Turnstile 脚本」，这句本身没错，
但据此得出的「被拦截」结论是错的。真实设计是**交互触发、异步加载**：

1. 页面加载时**不**注入 `challenges.cloudflare.com/turnstile/v0/api.js`；
2. 用户第一次 `focusin` 或 `pointerdown` 表单时，`warm()` 才异步加载脚本并渲染 widget；
3. 提交时走两步：服务端 `POST /wp-json/linker/v1/protection/prepare` 换取 sitekey，
   客户端取得 token，再 `POST …/verify` 换取有时效的 proof；
4. `linker_proof` 隐藏字段由此填充，服务端再调 Cloudflare siteverify。

生产实测确认这套链路已注入：

```
linkerPublicProtectionConfig = {
  "api": "https://de-linker.com/wp-json/linker/v1/protection",
  "nonce": "754057849d",
  "mode": "enforce",
  "businessVerification": "required",
  "language": "en"
}
```

`protection.js` 在页面中出现 3 次（不同区块各挂一次）。

因此：**自动化客户端不触发交互、拿不到 token，提交被正确拒绝。**
这不是缺陷，也不需要「修复」。人工在浏览器中打开询盘页、聚焦表单，widget 会正常出现。

### 受保护动作清单与两种挂载方式

服务端 `Configuration::verification_required()` 对以下动作全部返回 `true`：

```
inquiry      required=yes
contact      required=yes
draft_write  required=yes
genie        required=yes
```

`Protection/Actions.php` 另列 `genie_contact`、`genie_inquiry`；
`Protection/BusinessPolicy.php` 把 `contact`、`inquiry`、`genie_contact`、
`genie_inquiry`、`conversation_mail` 归为业务验证类。

**两种挂载方式，同一套 proof 机制：**

| 入口 | 取 proof 的方式 |
| --- | --- |
| 询盘、联系、草稿写 | `FormFields.php:33` 渲染 `linker_proof` 隐藏字段，`protection.js` 提交前填充 |
| Genie | React 组件调 `window.linkerPublicProtection.proof('genie', widget)`，不走表单字段 |

实测：`/genie/` 与 `/de/genie/` 均注入 `linkerPublicProtectionConfig`（`mode: enforce`），
但页面中**没有** `data-linker-protected-action` 属性——这是 React 挂载方式的正常表现，
不是保护缺失。

因此「Genie 与询盘的失败提示不同」不表示两套机制，只是同一个 proof 在两种界面上
的呈现差异；根因一致：都需要真人交互产生 token。

## 客户侧报告 PDF 下载：生产上无样本，未验证

报告的 **API 内容**已逐行读回（英德各 13 行，见前文）。但**客户拿到的 PDF 文件**
走的是另一条路径，本轮未能验证。

### 机制

`Planning/ReportDownload.php` 注册：

```
GET /wp-json/linker/v1/inquiries/{id}/planning-report/{handoff}?key=...
```

- `{handoff}` 是 32 位十六进制 id，存在订单元数据 `_linker_planning_projects` 里
  （`Context::META`），由 `Context::stored()` 按 `valid_reference()` 过滤后返回。
- 权限三重之一：`manage_woocommerce`、订单客户本人、或持订单 `order_key`。
- 内容由 `linker_tools_planning_report_content` 过滤器供给，默认返回 503。

### 生产实测

扫描全部订单的 `Context::stored()`：

```
orders with report contexts: 0
```

**没有任何订单持有可下载的报告 handoff。** 因此该下载路径在生产上从未被真实使用过，
本轮无法读回一个真实的客户 PDF。

### 一处差点误判（记录下来避免重犯）

我先查了 `_linker_planning_handoff`，发现 10 个询盘全无，一度准备据此写
「客户报告从未交付」。但那实际是 `DraftTransfer::LINE_META`——**购物车行**上的
方案草稿转移标记，与报告 handoff 是完全不同的东西。元数据键相似不等于语义相同。

正确的键是 `_linker_planning_projects`；用它查出的结论才是上面那个。

### 解除条件

需要一个持有报告 handoff 的询盘。产生方式：客户在配置器里生成报告后
把方案发成询盘，`Context` 才会写入 contexts。本轮已有的询盘都早于该能力，
或未走这条路径。

### 权限层已实测（2026-10-31）

下载路径的权限与拒绝行为已在生产验证，均为只读探测：

| 请求 | 结果 |
| --- | --- |
| 无 `key`、无登录会话 | `404 planning_report_not_found` |
| 持该订单有效 `order_key`、但无对应 handoff | `404 planning_report_not_found` |

两次返回**同一个** 404，不区分「你没权限」与「报告不存在」——报告的存在性因此不会
通过该端点泄露，这是正确行为。

### 仍未验证的部分

**一次成功的 PDF 下载。** 需要一份真实持有 handoff 的询盘；生产上 `Context::stored()`
对所有订单均为空。

生产上要产生 handoff，只能由 `DraftTransfer::apply()` 在真实会话中写入，
而它需要引擎签发的完整回执。**我不会伪造这个回执**——伪造出来的「验收通过」
不是客户路径，等于自欺。

解除条件：客户在配置器里生成报告后把方案发成询盘，`Context::capture()` 才会写入
contexts；届时可用该询盘读回一次真实 PDF。

## 3D 视图：生产实测渲染成功

地图 #548 的一条旧记录写作「Chrome 3D context availability remains unproven」。
现已在生产环境实际验证。

### 实测

项目 `88e747eb…`（`Production Roof Acceptance 1946`，revision 12，24 块组件）：

1. 打开 Roof design 工作区（`#lp-design`）；
2. 视图切换 `Plan / Map / 3D` 中点击 **3D**；
3. 视口渲染出**带透视的屋顶平面**（梯形几何），3D 按钮进入激活态；
4. 页面无报错，未出现降级提示。

代码侧对应实现：`apps/planner/src/components/design/SceneViewport.tsx`
（Three.js / React Three Fiber），并在 `webglcontextlost` 时监听恢复，
失败时渲染「3D rendering is unavailable. The design remains available in the plan
view and numeric properties.」——**降级路径也有文案出口**，不会白屏。

### 边界（不要过度解读）

这次验证的是**渲染可用**，不是：

- 3D 视图的交互完整性（旋转、缩放、选中已在 Plan 与 Map 下验证，3D 下未逐一操作）；
- 像素级视觉验收（工具页不受像素门约束，但也没有做 1440/390 × EN/DE 全矩阵）；
- 在不同 GPU / 浏览器下的兼容性——只在当前环境验证。

### 结论

「3D 不可用」这条旧记录**可以关闭**。地图上应改为：3D 渲染在生产可用，
失败时的降级提示存在；交互与跨环境兼容性未做全矩阵。

## 德语界面：生产实测完整

英文界面此前已多处读回；德文界面这次在浏览器里实际走了一遍。

打开 `/de/loesungskonfigurator/?project=88e747eb…`：

- 页面标题 **`Lösungskonfigurator | Linker`**
- 导航：`Aktuelles Projekt` · `Projektübersicht` · `Standort und Projekt` ·
  `Dachplanung` · `Energiedaten` · `Energieberechnung` · `Geräte` ·
  `Leitungswege der Installation`
- 屋顶工作区：`Dachplanung` · `Draufsicht` / `Karte` / `3D` ·
  `Dachfläche hinzufügen` · `Modulspezifikation hinzufügen` ·
  `Dachgeometrie importieren` · `Aktive Dachfläche` · `Nordbezug erfasst` ·
  `Planungsobjekte`
- 顶部动作：`Genie fragen` · `Gespeichert · Version 12` · `Projekt speichern`

界面文案完整德语，无残留英文标签。

### 一处看似漏译，实际不是

设计对象面板显示 `Owned synthetic roof for release acceptance`（英文）。
核对 `DesignEditor.tsx:528`：该名称直接渲染 `{face.name}`，**不经过 `__()`**。

这是正确设计——`face.name` 是用户在项目里给屋顶起的名字，属用户数据。
德语用户自己起的名字，界面不应替他翻译。

### 边界

验证的是**文案与布局**，未做 1440/390 全矩阵截图比对，
也未在两语种下逐一操作每个控件。

## 同意与统计：生产实测，统计在同意前不加载

目标完成标准里点名「同意、统计」。此前没有验收证据，现有生产实测。

### 实测（生产首页 HTML）

**GA 脚本被真正扣住**，不是「先加载后 gating」：

```html
<script type="text/plain" data-cookieyes="cookieyes-analytics"
        id="google_gtagjs-js"
        src="https://www.googletagmanager.com/gtag/js?id=GT-PLVVHJ2K" async>
```

`type="text/plain"` 的脚本浏览器**不执行**。在 CookieYes 授予分析类同意之前，
GA 连脚本都不会运行。

**默认全部拒绝**：

```js
gtag('consent','default',{"ad_personalization":"denied","ad_storage":"denied",
"ad_user_data":"denied","analytics_storage":"denied",
"functionality_storage":"denied","security_storage": ...})
```

### 实现

`plugins/linker-commerce/includes/Consent/BasicMode.php`：

- `script_loader_tag`（优先级 30）扣住 Google tag，改为 `text/plain`；
- `googlesitekit_consent_defaults` 全部 `denied`；
- `googlesitekit_consent_category_map` 去掉 ads 类目；
- `wp_get_consent_type` 在 CLI 下返回 `optin`；
- 另入队 `assets/consent.js` 处理撤回。

CMP 是 **CookieYes**（`cky-*`），统计是 **GA4 `G-N2TGDM3193`**（容器 `GT-PLVVHJ2K`）。

### 边界

验证的是**页面输出与默认状态**。没有在浏览器里实际点击「接受」后确认 GA 开始采集，
也没有验证撤回后是否停止——那需要人工交互，与界面读回同属一类缺口。
## 旧链接迁移：生产实测全部 301 到新地址

目标完成标准点名「旧数据/链接迁移」。此前无独立证据，现补上。

### 旧路径重定向（生产实测）

| 旧路径 | 301 目标 | 最终状态 |
| --- | --- | --- |
| `/design-canvas/` | `/solution-configurator/?step=roof` | 200 |
| `/quote-configurator/` | `/solution-configurator/` | 200 |
| `/de/design-canvas/` | `/de/loesungskonfigurator/?step=roof` | 200 |
| `/de/entwurfsflache/` | `/de/loesungskonfigurator/?step=roof` | 200 |
| `/de/angebots-konfigurator/` | `/de/loesungskonfigurator/` | 200 |
| `/de/solution-configurator/` | `/de/loesungskonfigurator/` | 200 |

每条都是一次 301、落到 200，无重定向链、无断链。`?step=roof` 保留：旧画布入口
本就指向屋顶步骤，迁移后仍直接进入同一步。

### 历史方案恢复入口

```
/solution-configurator/?saved_solution=8207       → 200
/de/loesungskonfigurator/?saved_solution=8207     → 200
```

语种各自落在对应地址，不跨语言跳转。

### 边界

验证的是**状态码与落点**。未验证：301 是否被搜索引擎正确收录（需要 Search Console 数据）、
旧链接带查询参数时的行为、以及外部站点指向旧地址的入站链接。

`/solution-draft/` 返回 404——但该路径从未存在过；Solution draft 的真实地址是
`/cart/`（标题 `Solution draft | Linker`），前面已记录。

## 历史：项目修订与计算记录可读

目标完成标准点名「历史」。此前只有零散提及，现补上实测。

### 项目修订历史

项目 `181228648034…` 当前 revision 16，指定读取历史版本时：

```
current revision=16
rev1 readable, sha=58023034feb9
```

`projects/read` 接受 `revision` 参数，早期版本的输入哈希与当前不同，
说明每个 revision 保留独立的输入快照。

### 计算历史（浏览器实测）

Energy calculation → `Saved calculations`（URL 变为 `&energy_view=runs`），
`Calculation history` 列出跨 revision 的记录：

```
Revision 12  Planning report        Report ready            10/30/26, 9:34 PM
Revision 12  Planning report        Report ready            10/30/26, 9:27 PM
Revision 12  Energy calculation     Calculation complete    10/30/26, 9:22 PM
Revision 12  Equipment checks       Equipment check complete 10/30/26, 9:09 PM
Revision 11  Energy calculation     …
```

选中的那条展开为报告预览，含 `Download PDF`、`Download bill of materials (CSV)`
与 `Add selected products to solution draft`。

### 一处看起来不一致，实际是设计

界面语言是英文，历史列表也是英文（`Report ready`），但预览正文是德语
（`Projektplanungsbericht`），且标注 `Report language: German`。

核对 `PlanningReportResult.tsx:170-176`：正文语言由 `report.locale` 决定，
并在与界面语言不同时显示该提示（`reportLanguageDiffers`）。选中的报告本身
生成于德语环境，因此正文是德语——**这是正确行为**，不是语言串台。

### 边界

未验证：删除或重命名历史记录、超过一页时的分页、以及跨项目的记录隔离。

### PR817 WordPress 最终读回与本地回收

`resume-deploy`最终退出0；正式版本`20261031T035727515212Z-f93d026a5`。从VPS公开HTTPS完成同一套既有验收：英德首页/产品入口/询盘/账户/产品/8个法律页均200且德语lang正确；两个产品页各唯一Product JSON-LD；法律脚本反斜杠完整；旧屋顶入口301；Search Console属性及验证文件、CMP原生插件/统计同意门均通过。已把上一版原子回滚集归档到`/home/u388076051/deploy-prev/20261031T035727515212Z-f93d026a5`，只保留这一套。未执行营销文案改写或真实测试邮件。原本机网络失败记录仍保留，不将代理Tunnel503归因网站。

验收后删除本批可重建暂存`/Users/chesterjohn/de-linker-data/cutover-workspace/staging`：1400个普通文件，30,834,160逻辑bytes，34,037,760分配bytes。验证成功部署快照完整后删除已替代的失败尝试快照`db-20261031T035505Z.sql.gz`，7,471,537bytes。连同此前3份超限快照，本轮WP相关已删除文件逻辑量60,795,713bytes；尚保留2份快照（20261030T184016Z、20261031T035705Z），均在N=3内。自有pytest-24合成文件988bytes及SSH临时配置/socket、VPS HTTPS读取进程均已回收。Data卷仍约2.8TiB使用、841GiB可用，APFS及并发写入下不把文件逻辑字节当作净磁盘可用量增长。

两处实际部署PHP文件（PreparationJobs.php、ClaimOutbox.php）经WP-CLI读取SHA-256，与f93合并树逐一相等，文件身份读回通过。

classic 实例逐项实际退役读回：`{"name":"g516classic","status":"retired","preserved_files":9,"preserved_bytes":41824,"evidence_sha256_manifest":"7e3a6df2971714e3aa9d0d7d50f9ed02b504f2af4931b618e739f405ac6a3073","redis_keys_before_scan":2303,"redis_keys_removed":2303,"redis_keys_after":0,"directory_absent":true,"database_absent":true,"registration_absent":true,"marker_absent":true}`。移交目录 `/Users/chesterjohn/de-linker-data/retired-instance-evidence/g516classic`，文件 SHA-256 与迁移前逐一一致；该目录及其子目录权限 0700。

classic 实例逐项实际退役读回：`{"name":"g520c","status":"retired","preserved_files":73,"preserved_bytes":543087,"evidence_sha256_manifest":"f5e7ad81009b12932dbeb33397a45afc2a6f452b687f6218f463de0eefffdebb","redis_keys_before_scan":3878,"redis_keys_removed":3878,"redis_keys_after":0,"directory_absent":true,"database_absent":true,"registration_absent":true,"marker_absent":true}`。移交目录 `/Users/chesterjohn/de-linker-data/retired-instance-evidence/g520c`，文件 SHA-256 与迁移前逐一一致；该目录及其子目录权限 0700。

classic 退役批次资源/保护读回：`{"registered_before":56,"registered_after":54,"preserved_total_files":82,"preserved_total_bytes":584911,"redis_removed_total":6181,"free_bytes_before":903005908992,"free_bytes_after":903451406336,"free_bytes_delta":445497344,"protected_p548_database_query":"ok","other_54_registry_entries":"unchanged","shared_cache_and_worktree_inodes":"unchanged"}`。文件系统可用空间差值受并发会话影响，不等于本批独占物理释放量；未启动服务/浏览器、未发信。

classic 退役末次进程/权限读回：`{"retired_path_process_pids":[],"retired_ports_listening":[],"evidence_permissions":{"g516classic":"0o700","g520c":"0o700"},"intentional_shared_root_lock_bytes":{"g516classic":0,"g520c":0}}`。保留两个零字节共享根锁文件以保持同名生命周期锁 inode 稳定；无退役 marker 或临时文件，保留证据原字节共 82 文件/584,911 bytes，未提交。


### PR815 同批修复资源合同（manifest 与 BOM 来源绑定）

复用 `/Users/chesterjohn/.codex/worktrees/installation-facts-548-2697/de-linker` 和本树已有 engine 依赖，负责人总 goal / `sol_local_retire_implementation`，不新增实例、工作树或依赖环境。原 PR head `2238ac0f8921a0f3b5d4716f3f421a80043f45a0` 由现有 `origin/codex/548-genie-bom-context` 原样保护；fetch main 后如需 rebase，只使用最多一份 Git 自动 stash 暂存本记录，完成即自动应用/回收。只修改 engine assistant_context 与相关回归，修复 selected run manifest 固定的 report.source 未参与材料来源验证问题；legacy 无 materials model 的兼容与 provisional_not_complete_bos 边界保留。合成 SQLite/CAS 测试只使用 `/tmp/pr815-materials-binding-tests` 一份临时根，由本代理在命令 finally 精确删除；源码与有效回归随能力保留。不改生产 Genie、不 push/merge/deploy；跨平台 exporter 等最终源码复审后统一真实重导，不手改身份 hash。

PR815 绑定修复红绿：同 revision、相同 project/input 的自洽 sourceB/materialsB 曾可冒认 run manifest 固定的 sourceA，新增夹具在旧实现明确失败 `DID NOT RAISE InvalidInput`；修复后 selected materials 必须来自 `manifest.context.assets["report.source"]`。8 项 assistant_context 回归通过（1.09 秒），两修改文件 mypy/Ruff/format 和 diff-check 通过；旧报告无 materials_sha256 的早返回及 `provisional_not_complete_bos` 边界保留。原内部 schema/handling 负例同步固定各自 source，避免由新增外层检查遮盖原验证。rebase 到 main `b743878e5` 已完成；原 PR 实现字节保留，旧 fixture-only 提交被当前 main 的已验证基线替代，后续统一真实 exporter 重导，不手改 hash；原 remote PR head 未变，Git 自动 stash 已应用回收。Linux exporter 等生产 Genie817 切换和 ACK 完成后由总 goal 通知窗口。

PR815 增量独立 Spec/Standards 复审已通过，engine 来源绑定修复冻结。Darwin 真实 exporter 已完成并格式化，canonical sorted JSON SHA-256 `be07bf1bf49e78058b2067c1cef46025408cfa4033976d8939b0b64ab6bf3449`；相对已审原 PR815 fixture 的非身份差异为 0，相对当前 main 基线仅 100 个派生 hash 与原 PR 已有的 geometric report assistant materials 字段。Linux 仍待总 goal 确认生产 Genie817 切换和 ACK 窗口，不提前导出，不重复 Darwin；跨平台 mask/manifest 最终合同在两平台均就绪后统一检查。

PR815 Linux exporter 短窗口资源合同：总 goal 已确认无 pr817_migrate 进程，发布代理在本短窗口不执行 stop/publish。仅复用 `/opt/linker-engine/current/.venv/bin/python` 既有依赖，实际源码来自已复审冻结的本 PR 工作树；负责人总 goal / `sol_local_retire_implementation`。VPS 最多一个 `/tmp/linker-planner-fixture-815-source-binding` 专属临时目录，传入源码/tests/schemas/锁文件与必需 fixture 原件，不复制 venv，不访问真实 workspace 或生产服务。使用 nice19、BLAS/OpenMP 单线程、60 秒导出上限，trap 与 finally 精确删除目录并读回；远端完成先释放窗口，再本地验证两平台 manifest/mask 和 Darwin 复现。结果原位更新现有 Linux fixture/manifest，不新增持久副本、不提交/push。

PR815 最终跨平台合同：真实 Linux exporter已在独占短窗口完成，canonical SHA-256 `72ce66e6386cc6db3f8d012b584269e0bd053b9654e1e8e7580a73dec6d7af4f`；Darwin沿用上述一次导出。两平台相对已审原PR非身份差异0。Darwin完整复现、两平台manifest与精确平台mask三项通过（11.21秒），不重跑未变单元。Linux包442文件/1,663,514压缩bytes，不含venv；/tmp/linker-planner-fixture-815-source-binding已finally删除并读回，未操作生产workspace/服务。最终assistant_context源码SHA-256为`618c85067f3508830eedea6def7340f987e281b29f1f21c9fab27e20b9425385`，两轴增量评审通过；候选基于已合并PR818，不把本地通过写成已部署。

PR818最终CI41167264856精确验证93666e477：21项success、5项按plan跳过，已合并为b743878e581b12017c2069d73780f847545751b1。本地退役的真实执行结果见上文；生产Planner尚待与报告来源修复共用配对发布窗口。


### PR817 Genie-only 生产发布与回收（2026-10-31 UTC）

发布源码固定为 squash merge `f93d026a52a5705a08ce44f7c75a95990395853e`，未改生产 engine/Planner、模型通道、全局代理或密钥配置。新 runtime 为 `20261031T045723868974Z`，Genie PID `351302`、judge PID `351303`，两者实际 cwd 均为 `/opt/linker-genie/20261031T045723868974Z`；engine 保持原 PID `318406` 与 `/opt/linker-engine/20261030T170107737048Z`。

同一 Woo source `dc2b9fa7d9946ab12171226381ec83cb0a5b7242e0d2d4662993d43ab46466d9` 经真实 native lease epoch **45**、新代码正常 chunk/compile/materialize、原生 prepare/upload/fenced activate、实际 API loaded 和 native ACK 完成；不是 metadata 重标。index `20261031T045644Z-714391000`，SQLite `290537472` bytes，SHA-256 `4280be213a9eb8cdb4c836e935d3c6dfc79119c6ccee57969f0d1715ffa33980`。recipe `fa349dd54c249ba1dd4f08fb3cfea4b08387e90f8b563123d502522a7ecdcb9e`；expected/actual serving 同为 `92d0369d9724d06463e17562cc57025809447c20491febe724da40a9a084d939`。独立 API 与 WP `linker_publication_jobs` 读回均同 source/recipe/index/epoch，native **ready**、lease `0`、85 个 prepared products，`materialization_complete=true`。

142 份 PDF 全部解析缓存命中，0 重解析；18,567 chunks、3,984 model projections；18,567 向量缓存命中、0 新编码。`preparation_complete=false`：217 个 `no_proven_passage` 文档关联与旧 index 逐项相同，语义缺口继续保留，不能将 ready 解释为 PDF 全部事实已放行。旧 manifest 原件 `/Users/chesterjohn/de-linker-data/index/builds/20261031T021452Z-018710000/manifest.json` 保留（chunk/compile/embed/store = 48.0/634.2/3.1/37.1s）；本次原件 `/Users/chesterjohn/de-linker-data/index/builds/20261031T045644Z-714391000/manifest.json` 保留，对应 **48.2/513.1/2.1/24.7s**。identify 次数没有现成计数，记未知，没有为统计重跑。

实际发布窗口：systemd stop/ActiveExit 为 **04:57:18Z**，API shutdown complete `04:57:18.258319Z`；新进程 start **04:57:37Z**，API startup complete **04:57:40.808888Z**。索引上传 **04:57:54Z–05:11:32Z，818.175s**；fence journal `05:11:47.087387Z`，current index 原子切换 `05:11:47.089387Z`。所以新 runtime/旧 index 的知识拒绝窗口约 **14m10s**，不能称零中断；后续发布 seam 应把真实上传及 checksum/manifest 校验前置，runtime hook 之后只做短 activate，并保留 native owner/fence/inspect。此次三项控制动作均首试完成，未重放 publish/activate。

API startup 后真实 SQLite 已有 `turns_retention`、`turn_starts_retention`、`judgments_retention`；`turn_sequence=(1,706)`，706 turns/MAX(id)=706、680 judgments、unfinished=0 保留，90 天前记录均 0。没有 retention 错误；生产默认 INFO 未输出删除计数，因此仅用实际索引/序号/行数与 startup 日志证明已执行，不伪称有删除计数日志。

失败证据保留：epoch43 被操作员 SIGINT 后经已部署的 `abandon_interrupted_knowledge` privileged native CLI preview/apply 清理 lease，未写 queue option 或伪造 ACK。epoch44 已完整生成 `20261031T043441Z-727588000`（SHA `713d15bdb7aaad8c7771f631a0a0a4c2610bcaf1befe1e53cffabdf8f3a82088`，chunk/compile/embed/store=48.3/582.7/2.1/23.2s），随后 stop SSH 调用失败、原三个 PID 和旧 matched pair 未变；原 worker 正常 failed ACK 并按其契约回收该失败 candidate。原 stop 的 exit/stderr 被早期临时 runner 丢弃，根因未知；后来一次只读前置明确 SSH exit255，但当时没有留下 stderr 类别，不能补猜。早先“5 分钟 SSL 等待即挂死”的判断已撤回：旧成功 manifest 的 compile 为634.2s，单凭等待不足以诊断。最后一轮45成功；没有继续重复编译。

Mac 定时器已恢复：`com.linker.knowledge-publication`，source/current `/Users/chesterjohn/de-linker-ops/knowledge-worker/releases/f93d026a52a5`（只读），previous `02cedf1835a0`；保留 `1418dc26e14c/.venv/bin/python` 作为明确的共享依赖，900s interval/7200s lease，PYTHONPATH 指向新 source。初次自动 poll 退出1，系统公开日志 `run_job / HTTPStatusError /503`；随后独立 native queue 仍 ready/epoch45/lease0，serving 正常，不能把调度已登记说成每次网络轮询均成功。既有900s重试调度保留，未因此再发 build 或改全局网络。

资源：VPS runtime 仅 current `20261031T045723868974Z` 与 previous `20261029T024800000000Z-02cedf18`；本次临时 stage 已不存在，新 release 的32-byte task owner marker已删除。Mac 两个过时 source `8869767c8192`/`bcc88fea4fef` 全部源码已核为对应 git archive，唯一额外文件为可重建的 `.git-source-manifest.json`；无 symlink/venv/进程/launcher 引用，解开仅这些退役目录的 owner 只读权限后删除，共 **771文件，42,175,083逻辑bytes，43,786,240分配bytes**。两个 source manifest 文件 SHA 分别 `973b90c59661305440c630783b7692b16d3e474968909da56d3aef3a062c210c`、`10ad80a0b920ac34c76fdf944f17eac7327a9229a4b9d94f6a13993b8caf606c`，旧 commit 仍在 Git 中。native ledger 自动回收旧 owned build `20261030T125504Z-601038000`（8文件、668,261,823逻辑bytes、668,274,688分配bytes），只保留新 current 和 `20261031T021452Z-018710000` previous；共享 PDF/parse/vector cache 未复制或删除。

以下临时内容在本段成功追加并 fsync 后按原资源合同删除：journal、唯一 SQLite 在线日志恢复 zip、忽略且不参加 recipe 的无扩展名迁移脚本；合计 **1952206逻辑bytes／1957888分配bytes**。迁移进程与上传观察器均已退出，无新增本地站点或浏览器。VPS 最后 filesystem available **44,533,528 KiB**（此前44,329,300 KiB）；Mac Data 卷最终可用量以下收尾读回为准。文件分配回收量不等同 APFS/并发写入下的全卷净增长。

收尾本机 Data 卷：3,902,665,360 KiB 总量，2,991,395,644 KiB 使用，879,922,656 KiB 可用（约839 GiB），78%。本批上述已核删除合计712,389,112逻辑bytes／714,018,816分配bytes，另VPS owner marker32逻辑bytes／4096分配bytes；不把它们冒充全卷净释放量。临时journal/zip/script均已读回不存在，current+previous源码和共享venv仍在。


### Planner 815 + 818 production release and CAS maintenance resource contract

Owner: sol_planner_gc_implementation, coordinated by root as the sole Planner production writer. Reuse this worktree and its existing engine environment; preserve all existing INDEX evidence. Candidate source is merged PR815 (including 818), expected merge `dabd78f2e235191adf59cf140367d5eef080c2b6`, local PR head `33378924aed3be4ce9cfceb45268aed3720f47ad`; fetch only the existing origin object needed to prove the engine subtree equality. New immutable release: `/opt/linker-planner/releases/3a551ec59f009c2e83026b014d58b1b91d7e29ecfec313c6ec14536dc25937dc`; exactly one candidate, `.venv` built with locked uv at that final path. Stage only engine src/schemas/ops/pyproject.toml/uv.lock; retain final current + previous, and a third only if a retained execution actually needs it. Reuse runtime/worker policies and source-environment path, never print credentials or hand-build prepared receipts.

One necessary current consistent recovery archive may be added under `/Users/chesterjohn/de-linker-data/planner-production/archive-<UTC>`, replacing superseded/incomplete recovery material only after native verify and reference/ownership checks; complete archives obey same-source N=3, and the explicit Oct27 acceptance DB baseline is protected. No remote full backup file. One bounded SSH streaming process holds the shared CAS lock while SQLite mode=ro backup-to-memory and immutable CAS are streamed to the Mac, locally verified with this batch's archive.verify, then published and acknowledged before unlocking. If native apply has candidates, at most one temporary remote recovery root outside workspace contains independently copied DB/backup.json (single-link plain files) and immutable CAS hardlinks; native independent_snapshot verifies it without changing its rules. This remote root is removed after apply + restored readiness + local recovery verification, or on failure after reliable service restoration. No second full CAS copy is made for cleanup.

Execution sequence: inspect exact live selection/UID/listener/schema/jobs/ownership and old recovery artifacts; prove merged source equality; stage in-place candidate and native prepare; create/verify the single current streaming recovery if old archives do not cover current state; native activate/status and HTTP+worker+storage+saved-report readback; compute complete advisory CAS closure on a consistent DB; if deletion is justified, stage independent remote recovery, invoke native retention --apply --recovery (which owns drain/stop/recompute/restore), verify history/recovery/service and second plan; remove only proved superseded releases/recovery/temp roots and record actual bytes/space. No manual systemd/drain pair operations, production mail, workload generation or pressure tests. SSH/uv/operator processes are bounded to their active operation and reaped; abandoned partial candidate/recovery output is removed if not uniquely needed for diagnosis.

Exact new recovery destination (one): `/Users/chesterjohn/de-linker-data/planner-production/archive-20261031T053139Z`; one `.incoming-*` sibling exists only during streaming/verify and is removed in finally or published into this path. It uses the already staged release native CAS shared lock and archive verifier; local complete archive retention remains N=3.

Recovery stream first attempt failed before SSH banner exchange completed: `Connection timed out during banner exchange; Connection to 72.62.97.95 port 22 timed out`, before remote backup/lock code ran. The `.incoming-*` directory was removed in finally and the same exact archive destination remains absent. Native prepare/source results remain valid. Authorized maintenance-only SSH ControlMaster: `/tmp/p815818-3a551ec5.sock`, owner this agent, at most one, ConnectTimeout 20s, ServerAliveInterval 15s/CountMax 2, ControlPersist 120s idle, exact socket permission/owner checked; finally `-O exit` and confirm socket/process absence. No global SSH config change, no second candidate or recovery destination.

Native prepare passed at the declared candidate path; 289 tracked source files match merged engine subtree with SHA-256 `0e191aa353de6a3eea84c8fbaf97925d2e01f29d33172983b510b0f25edaa251`. Prepared runtime is `7fb0962e88add78ba5ddc76f338a184bc1738c953bb10b5ca22ef9241865487b`, storage schema 5; policies reused and service-UID source construction passed. Existing production before replacement: 18 projects / 56 revisions / 55 runs / 55 terminal jobs (53 succeeded, 2 failed), no pending executor.

Recovery stream completed at the one declared archive: 629 blobs, logical bytes 201652816, DB SHA-256 `de3daf95024d09c62da07a513802498025144cf5c5d4ce10746284b8bf1eab76`; native archive.verify passed while source CAS shared lock remained held through local publish and ACK. No remote full backup file. The transport reached an end-of-stream wait because tarfile requested a full 10 KiB block from Popen's buffered pipe while the remote waited for verified ACK; diagnosed remote owned PID 353033/UID994 at pipe_read. A single 10240-byte gzip zero-padding tail to that exact owned stream released the same reader, preserving all received bytes and the held lock; DB/CAS files were not modified. Future streaming uses an unbuffered pipe. Native verification and SSH exit 0 completed; no incoming directory remains.

Activation and actual consumer readback: current `3a551ec59f009c2e83026b014d58b1b91d7e29ecfec313c6ec14536dc25937dc`, previous `01ac2230e7ab4aa4cfc27f0e8ce9eb2eaa20ec984a40a7c1c89d0abaff5bc5fd`; native operator retired `ba154318a753ab04dd9d2d48046eb107b031e5ed8de838d6868fb79549ef375d`, leaving exactly two releases after its global drain. HTTP PID353299 / worker PID353377 active with NRestarts0; 8911 belongs to HTTP. Runtime `7fb0962e88add78ba5ddc76f338a184bc1738c953bb10b5ca22ef9241865487b`, execution `69759854dbc1069b6a36055a5dcdb0b22932c71f24052c83260f525998e1862e`, storage `f91b6338e5204a220d7163fde4277f900fc0c12ca913edec9d7c1560f0eb06d4`; worker generation/identity matches, draining=false, pending=0. Real read-only team requests for saved project/revision, report and assistant context succeed in EN/DE. Saved report `3694efb88a2544c7a334e9078be023b8` retains result SHA `c69a799be70455ed9da8af0bc2f9fded138628ec4663c78cd5fb771cda1c719d`; project_materials_v3 has verified provenance, 16 lines, 10 unresolved quantities, and scope `provisional_not_complete_bos`. No job/evaluation was created.

Consistent verified-archive full recursive CAS plan: 623 retained, 6 candidates / 5203227 bytes, temporary count 0. Candidate hashes are re-derived by native maintain while stopped, never trusted from the earlier truncated audit. Exact temporary remote recovery root: `/opt/linker-planner/state/retention-recovery-3a551ec5`; owner linker-planner / this task, maximum one, outside workspace, DB+backup.json are independent single-link regular files, only immutable CAS inode hardlinks are shared. Native independent_snapshot must pass and cover every candidate before unlink. Remove this root after native maintenance restores actual readiness and Mac recovery is verified; failure keeps it only while required for diagnosed recovery, with no second full data copy.

First temporary recovery metadata attempt failed before verification: macOS BSD tar emitted AppleDouble regular entries `._workspace.sqlite` and `._backup.json` in addition to the two permitted files; the remote assertion at transfer line 11 refused them and finally removed the exact temporary root. An operator sequencing mistake dispatched maintain before that independent result was confirmed. That native invocation exited 1 at planner_release.py:846 → operator:231 → command:93 (`RuntimeError: operator command failed: runuser`); the command helper did not retain the inner stderr. No deletion result is inferred from that generic error. Actual post-failure verification reads and rehashes all six planned hashes: all remain present, total 5203227 bytes; source DB remains projects18/revisions56/runs55/jobs55. Native finally restored HTTP PID353762 and worker PID353822, active/running NRestarts0, listener8911 owned by HTTP, worker generation928c5a73555e4d389e7e5977e382af3d equals systemd invocation, original prepared runtime/execution/storage match, draining=false pending0. Active timestamps: HTTP2026-10-31 05:48:08UTC, worker05:48:14UTC. No second apply or replacement recovery upload has started at this checkpoint. Failure evidence is retained; subsequent metadata transfer must use explicit Python USTAR with exactly the two named files and await independent verify success in a separate tool turn before apply.

Production GC deletion is stopped for a confirmed owned-runtime root omission. The observed additional blob is the actual current runtime `7fb0962e88add78ba5ddc76f338a184bc1738c953bb10b5ca22ef9241865487b`, 3059504 bytes, published by startup with no new job. Last native advisory plan connection closed (SSH255) without a result; no seven-candidate CLI proof is claimed. No USTAR replacement upload or second apply occurred. Final actual readback still has ready HTTP/worker with matching current identities and generation, draining=false pending0; all six old candidate bytes remain checksum-valid. Exact remote temporary recovery root is absent and retention process inventory is empty. Private SSH master PID46898 and `/tmp/p815818-3a551ec5.sock` are now closed/absent. No new production operation will be issued for the local fix.

N=3 recovery retention completed after independent coverage/ownership checks: superseded raw `/Users/chesterjohn/de-linker-data/planner-recovery-20261030-0450` removed; no open handles, all historical rows preserved, only two project revision/updated_at heads advanced, complete307-root graph and all313 CAS names covered by new verified archive. Its selector/spec metadata and hashes remain in existing RECOVERY-POINTS.json. Removed logical120779216B / allocated file121716736B; observed local free-space increase121884672B. Three verified complete archives Oct28/Oct29/Oct31 remain, plus explicitly protected Oct27 DB baseline; baseline's full116-root closure was directly verified against the new archive. Registry atomic temporary is absent, as are streaming incoming trees. An attempted INDEX append used the engine cwd and failed on a relative docs path before this note; the already authorized registry/cleanup succeeded and its exact result is recorded here. Further commands use absolute record paths and explicit dependency boundaries.


知识身份/批次识别同批资源与归属补充：复用 `/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548`，分支 `codex/knowledge-identity-batches`，base main `b743878e5`。PHP publication/lease 入口由 `sol_planner_gc_implementation` 负责；`services/genie` 的 src/index/ops 与 Python 回归由 `sol_local_retire_implementation` 负责，父代理集成。当前发布源 f93/817 保持不动，本候选不 push/merge/deploy，后续 rebase 保留815原有Genie改动。既有依赖与夹具复用，不新建实例/环境；本代理只允许一份 `/tmp/genie-identity-batches-tests` 合成测试根（负责人本代理、仅测试期、命令 finally 精确删除），不新增日志副本、跨构建缓存或生产请求。源码/有效回归随能力保留，测试临时产物用完回收。


### Knowledge identity/bounded batch PHP resource contract

Owner: sol_planner_gc_implementation; branch `codex/knowledge-identity-batches`, reused tree `/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548`. Scope: native Woo identity authority, authenticated lease-bound batches, knowledge claim/receipt fencing and their PHP tests. Source/test files remain with the capability and are maintained there; no new worktree, site, dependency install, production request or source copy. One existing PHP test process at a time; synthetic fixture temporary trees use one enclosing task temporary directory and existing test teardown, then finally remove that directory on success or failure. No persistent test server/process or extra report. Existing INDEX evidence from other owners is preserved. Production epoch 44/source 817 remains immutable.

The API uses independent `model_identity_revision` and preserves published `source_revision`. Private `texts` on the existing identify endpoint is bounded to 20 original windows of 16,000 UTF-8 bytes, requires authenticated exact knowledge lease ownership, and returns only matched labels plus an opaque identity hash. Old knowledge clients/receipts without the new protocol/identity cannot establish verified readiness.


PHP identity/batch candidate validation (local only): `Publication` unit directory 61 tests / 556 assertions; existing `EngineeringFeedTest` 20 / 130; affected `EngineeringReferenceTest` 10 / 47. Full `linker-commerce` PHPStan (includes tests/fixtures) passes; WPCS passes all nine changed PHP source/support/test files. The native batch fixture executes the real dispatcher/queue lock with current Woo-shaped relationships, proves 20 independent windows share one fresh map with no PDF access, rejects cross-window phrases/auth/budget/lease mismatches, and keeps unknown legacy identities from readiness. The draft-only fixture changes an unavailable model label while published source and engineering feed stay byte-equivalent after removing generated time; knowledge validation/reconcile/ACK reject the previous identity. Existing engine `Publication.read` selects known fields; `EngineeringFeed::feed` explicitly projects its strict schema, so identity is absent from feed. No engine schema expansion is needed.

Upgrade boundary: an old HTTP knowledge worker missing `identity_protocol=native-model-identification-v1` receives 409 before leasing; old or mismatched loaded identity cannot grant current knowledge readiness. `/validate` keeps identity optional for unchanged engineering consumers, so a PHP-only rollout cannot retrofit the old Genie runtime's proof rules. This batch requires the new Genie runtime (legacy index remains diagnostic-readable but grants no passages), PHP authority and new worker/index in a coordinated release; new runtime first, then PHP authority, then the fresh build/activation/ACK. No production rollout/readback is claimed here.

PHP resource readback: reused tree is 7.2 GiB including pre-existing dependencies/evidence; filesystem available 840 GiB at check. This half creates no persistent runtime, dependency copy or production request. All PHPUnit enclosing task temporary trees and generated fixture uploads were removed by teardown/finally; no PHP check process remains after completion. Temporary released bytes were not separately measured; only persistent source/test and this existing INDEX addition remain.

知识 identity/batching/progress 当前源码已独立 Spec + Standards 通过；后续 release 上传先行 seam 不预先沿用本结论。Python 端恢复既有16k请求窗组装，再以最多20个独立原窗口一批传输；原窗口内语义不变、批次窗间不拼接。opaque model_identity_revision 贯穿 manifest/proof/index meta、fresh permission/validate、loaded、native verify/fence/ACK；draft-only变化拒旧scope，旧缺identity generation仅可诊断loaded、不grant/ready，新build要求刷新identity inventory。代表回归覆盖20+1批、503退避/attempt、409不重试、draft-only撤销scope/ACK、原smallparts packing和阶段sink；早期协议夹具失败均已定向修复，未重复全矩阵。
真实日志sink只发一次安全数字probe `1793424025890979000`：现有env的 knowledge_progress 经 syslog.LOG_INFO（并保留foreground flush输出）在 macOS unified log 精确读回1条，时间 `2026-10-31 13:20:25.893293+0800`，PID42595，sender为syslog.cpython-312-darwin.so；predicate为eventMessage BEGINSWITH "linker-knowledge-publication " 且CONTAINS该probe。内容仅固定phase/event和数字，无文本/凭据，未新建日志文件/脚本、未发第二probe。测试隔离真实syslog，mock系统sink与capsys逐事件相等；batch+build代表2项通过（1.23秒）。

知识批次原生凭据接线资源合同：父代理负责mu-plugins/linker-publication-worker-access.php及其既有unit/native smoke夹具，只扩大到认证lease-bound texts模式的精确identify路径，保留单HTTP根调用/方法别名/embed/内部转发限制。源码/有效回归随能力保留；单元PHP子进程串行退出回收，不建临时脚本或依赖。本地真实认证验证优先复用现有ci_preflight，启动前核归属与资源、仅本门必要夹具，结束finally停止本次启动的进程并清理合成身份/文件，不发邮件。

父代理原生凭据接线修复：现有purpose APP_ID原只允许claim/ack，真实调用批次identify会在MU层403；新增正向红测确认。现在仅精确identify路径的JSON texts数组模式获一次root HTTP dispatch，text/models混用、查询参数伪装、内部子请求、embed/方法别名仍拒，原Controller继续验证native capability、窗口预算与完整lease。35项scope单元/129断言通过，改正真实set_body边界后两增量/21断言通过；全MU PHPStan和六文件WPCS通过。复用ci_preflight原生WordPress，58条认证/权限检查实际通过（SmokeTest 1项11外层断言），无生产请求/真实邮件。最初误以python -m cli会执行console入口导致空输出JSON错误，诊断后使用pyproject既有linker-local console入口；未改工具配置。finally down=0，三端口空闲、pid文件0、fixture option0、合成user ownership meta0，无新实例或依赖。


### Current runtime CAS ownership fix resource contract

Owner sol_planner_gc_implementation. Production815+818 is already active and healthy; production GC deletion is stopped after confirming that startup publishes a current runtime bundle with no DB root and restore/start would recreate it. This local increment exclusively owns engine planning/retention.py, worker_host.py and their smallest existing regressions; PHP and Genie changes from other owners are preserved. No immutable production source, new release, snapshot, environment, instance or browser is created. Source/tests persist with the capability. Reuse existing engine .venv with explicit current src. One enclosing synthetic SQLite/CAS test root at a time, bounded to a real runtime bundle plus one orphan and the necessary verified recovery archive; existing tmp_path/finally cleanup removes it on pass/failure. First prove the actual captured-runtime counterexample red, then wire native worker_host's true RuntimeSnapshot hash as an explicit owned root, verify complete closure and orphan apply/zero replan, and get independent incremental review. No escape CLI flag, hard-coded production digest or directory-name exemption. Final parent integration with815 precedes a single real two-platform fixture export; no fixture export here.

Owned-runtime fix completed locally (production GC remains stopped): native worker_host captures its actual RuntimeSnapshot SHA and passes the internal owned root to collector; a present bundle receives the same checksum-verified full JSON closure as DB roots, an absent bundle is never published, and a DB-reachable runtime is not traversed twice. No CLI bypass, directory exemption or fixed production hash. The real RuntimeConfig/open + SQLite/CAS fixture first failed against the previous code (three candidates rather than only the genuine orphan), then proves runtime and its actual captured source-file child survive native offline apply, the independent archive still verifies, and reopening the kernels yields a zero-candidate plan. Three existing representative recursive-history/backup-lock/fail-closed/readonly-WAL cases also passed (four tests total1.82s); the final formatted/runtime case passes independently. Full engine mypy . including tests passes356 files; Ruff/check/format passes the three changed files. Independent Sol Spec+Standards review PASS; the only later delta was explicit list type narrowing in the test. All synthetic test roots are removed in finally, no worker/listener was launched, no dependency or recovery copy created for this local fix. RuntimeSnapshot captures both changed source modules, so fixtures intentionally await parent integration with815 and one real Darwin/Linux export; no fixture is relabeled or exported here.


### Integrated815 owned-runtime fixture export resource contract

Owner sol_planner_gc_implementation; final parent integration HEAD `dabd78f2e235191adf59cf140367d5eef080c2b6`, preserving the three reviewed engine changes. Regenerate only the existing Darwin/Linux preparation-flow JSON and their platform manifest, using the real exporter on each host; source SHA at start: {"services/engine/src/linker_engine/planning/retention.py": "a5f020da7f5ae510f89df2f31049746a05e8e3c1d7f62b80063eb292b2f71aaf", "services/engine/src/linker_engine/planning/worker_host.py": "b38c1acf9eb25c37ac0c165579dcad97e6942cbfc3a94efffebc3ef3f8ec9e25"}. No engine unit rerun, production stage, service action, backup, dependency install or new worktree. Darwin reuses this engine .venv; one enclosing temporary root contains exporter/contract synthetic SQLite/CAS and is removed in finally. Linux reuses only `/opt/linker-engine/current/.venv/bin/python`; exactly one task directory `/tmp/linker-planner-fixture-548-owned-runtime` contains explicit source/tests/schema/lock/PVGIS fixture inputs plus a task owner marker. Use nice19 and all numerical thread limits1, exporter timeout60s with owned process-group kill/reap on failure; remote try/finally and caller exact-owner cleanup remove it, then read back absence. The small source package exists only in memory and the one remote directory. No live workspace or public API is read. Compare each complete generated document against merged815: every non-hash field, including all engineering numbers, must be identical. Existing fixture originals remain in Git; no backup copies are created. After existing Prettier formatting, run only full fixture reproducibility, platform manifest and exact host-mask three contracts.


815 integration Genie targeted compatibility contract: owner sol_local_retire_implementation; reuse the current Genie .venv and current src at integrated HEAD dabd78f2. Run existing test_planning.py plus two existing with_page dropped-search budget cases adjacent to the BOM priority branch, without other suites or external calls. Reuse the single authorized /tmp/genie-identity-batches-tests only while pytest runs; finally delete it on pass/failure. No new source, fixture, dependency, instance, service or production request. Results append here; no separate report.

815 integrated Genie compatibility: 16 existing cases passed in0.17s with explicit current src (entire test_planning.py including EN/DE BOM routing, provisional verified provenance/scope, full documents-call budget and sizing-history; two existing with_page dropped-search/family-suffix budget cases). No source/fixture changes were necessary. test_route.py has no separate BOM case; the actual route.with_page BOM priority consumer is exercised in test_planning.py. Current identity Snapshot additions coexist with the merged815 planning/route implementation. The single authorized test temporary root is absent after finally cleanup; cache provider/bytecode writes were disabled, no new environment/instance/listener/external request. Reused existing engine review after its test-only list narrowing; no source re-review or old test rerun.

Integrated export first results: Darwin actual exporter succeeded with100 identity-hash changes and0 non-identity changes versus merged815. Linux first isolated export failed at test_pv_generation.geometry() → FileNotFoundError `/tmp/linker-planner-fixture-548-owned-runtime/fixtures/planning/geometry-flat.json`; remote finally and caller cleanup confirmed task directory absent. No fixture value was written from that failed Linux run. The indirect original geometry fixture is added to the explicit source package; only Linux is retried, preserving the successful Darwin result and the failure evidence. No service/data/dependency changes.

Second isolated Linux export reached the real managed-reference worker and failed with FileNotFoundError at test_pvgis.raw(): missing original `docs/research/2026-10-23-pv-inputs/raw/era5-berlin-2020.seriescalc.json`. Synthetic job returned execution_failed; the original path/stack is retained in tool evidence. Remote/caller finally again removed the single task directory and no Linux fixture was written. Retries are stopped while the previous successful815 exporter owner supplies the complete known input list; no source/dependency fix or production operation is inferred from this packaging error.

Original exporter owner confirmed the full minimum non-engine input closure before another attempt: `fixtures/planning/geometry-flat.json`; `docs/research/2026-10-24-pv-generation/raw/berlin-2005-2023-nohorizon.tmy.json`; that directory's `weather-provenance.json`; `docs/research/2026-10-23-pv-inputs/raw/era5-berlin-2020.seriescalc.json`. Engine src/tests including test fixtures/schemas/pyproject/uv.lock are the rest of the package. No further dependency investigation or trial inputs are needed. Linux-only retry uses this complete original set and the same owned temporary path; Darwin remains reused.

Integrated815 owned-runtime export completed: actual Darwin canonical sorted JSON SHA `dd1be3e96d6ac104a11fe42421a2954a7997faa9233e18769eba57e39d3ed5fa`; actual Linux `61e75026e0a4dd02a2184d04b11e11984ebfc821fac565122f0d1a6a1dc72e21`. Each platform differs from its merged815 baseline at exactly100 lower-hex identity hash leaves, with zero other field/structure/engineering-number differences. Both source-pinned fixture runtime hashes are `69afa63db3eb7b2c9fa50e605d80bf5a562b1f8fd787b861eca602744bedbb26`. Linux successful isolated run took15.386s at nice19/thread1 using368 tracked source/fixture inputs and1634452 compressed bytes held only in memory; owned remote directory and processes were removed, caller readback confirms absence. Darwin successful export was reused throughout Linux input correction.

Only the three requested contracts ran: full same-host exporter reproducibility, platform manifest hashes and the exact pre-existing Darwin/Linux mask; all3 passed11.00s. The three existing JSON files pass Prettier, source modules retain their reviewed SHA values, and diff-check passes. Four verified external inputs plus the actual rendered() entry and cleanup duties are documented in existing engine/ops/planner-worker.md; this Markdown file remains outside RuntimeSnapshot.capture, with no source-hash scope change. No other engine unit, dependency install, new backup, production request/deploy or service lifecycle action ran. All local exporter/contract temp roots are absent. Mac available space is recorded by final readback; only the existing fixtures/manifest and this existing documentation remain.

Lease batch origin binding resource contract: owner sol_local_retire_implementation, exclusively Genie publication.py/test_publication.py. Bind credential-bearing identify batches to the existing lease claim URL scheme/host/effective port and claim path; preserve anonymous and local HTTP same-origin behavior. Reuse existing Genie env; only one /tmp/genie-identity-batches-tests during targeted red/green, finally remove. No real HTTP/credentials, new instance/dependency or production action. Source/tests persist with this capability; existing record only.

Credential-bearing batch origin correction: the old code failed all four negative MockTransport cases (different host, HTTPS-to-HTTP downgrade, different effective port, wrong native claim path). Before Basic credential assembly or any transport call, _request now binds actual client base origin to lease.verify_url scheme/host/effective port and its exact existing jobs/claim path, rejecting embedded userinfo/query/fragment. Three targeted test functions/seven cases pass0.67s: negative requests remain0, explicit HTTPS443 equals default, same-origin localHTTP remains valid, original20+1 windows remain distinct, anonymous single query sends no auth. Two changed files pass mypy with MYPYPATH=src:.:ops, Ruff/check/format and diff-check. The first narrow mypy invocation omitted ops and reported only publication_worker import-not-found; corrected existing source path passes without code changes. Test temp root absent after finally; no real HTTP, service, credential read or persistent runtime. Incremental independent review requested from release owner.

Origin guard incremental independent Spec+Standards review PASS by release owner; source unchanged after the seven-case green. Reciprocal read-only review of Worker.one/PHP claim unknown observation and exact native-ACK recovery also PASS: unknown transport/partial body does not revoke ready; bootstrap still claims, complete mismatch remains repairable, restoration requires same current source/recipe/model identity and exact acknowledged generation/products/coverage with no active lease or fence rollback. Existing42Python/27PHP222assert results reused; reviewed four-file diff-check passes, no repeated suite, source edit or production call for that review.


Unknown loaded-observation correction (candidate only; owner sol_release_route). A transport exception/SystemExit or incomplete/malformed loaded body is now explicitly reported as phase=loaded_observation and sent as an unknown observation. Native claim reconciles real source/recipe/model-identity changes first, but an unknown observation alone preserves an acknowledged ready generation. A complete valid different generation still uses the existing repair lease; an unprepared bootstrap still claims a real build. The deterministic old-code counterexample was red in both Worker MockTransport and real native ready state: the unknown poll incorrectly invoked preparation/new epoch. Both are green after this change. Production epoch46 naturally completed before this source repair: native/API full receipt fields and all85 product revisions match index20261031T053823Z-086121000, materialization_complete=true, preparation_complete=false with217 existing semantic gaps; launchd ended naturally with last_exit0. The prior literal repair cause is unknown because the later accepted ACK overwrote job.error. No current46 cancellation, replacement build, timer stop, production source edit or queue mutation was performed for this correction.

Native recovery is within the existing claim lock and does not rewrite version evidence: each accepted knowledge ACK now snapshots its materialization/preparation/diagnostics; pending preserves those acknowledged fields. Failed/pending/expired-preparing state can return to ready only without an active lease, with current source/recipe/model identity equal to that ACK, and a fresh complete receipt exactly matching acknowledged source/model/recipe/expected+actual serving/index/loaded epoch/products and revalidated current-manifest diagnostics. Status/coverage are restored from that native snapshot; activation_epoch remains monotonic and loaded epoch is unchanged. Missing legacy snapshot, changed input/identity/receipt, or an active lease cannot use this restoration. A legacy job lacking the snapshot remains conservative and requires a real native lease. No epoch rebinding or direct option-edit recovery is introduced.

Local validation: preparation_worker full file42passed0.65s; affected Worker consumers including adjacent publication tests54passed/65deselected1.55s; native PreparationJobs27tests/222assertions0.096s. Native failed-state recovery was also red before implementation. Coverage includes unknown/malformed ready, bootstrap, valid changed generation, exact partial-semantic recovery, live-lease preservation, and missing-snapshot/recipe/model-identity rejection. Ruff/check/format, Worker mypy, the two PHP files' WPCS and PHPStan, and four-file diff-check pass. Three leased-recognition fixtures gained their required same-origin native claim URL for the independently reviewed auth contract; original assertions remain. Genie author independent incremental Spec+Standards review PASS; PHP native author review requested separately. Frozen upload/runtime seam is unchanged. Source is local uncommitted next-pipeline work, not a claim of a production fix.

Observation-fix resource readback: reused candidate tree7.2GiB, filesystem available832GiB (78% used). Only these existing four source/test files and existing INDEX receive this increment; no new environment, worktree, service or persistent process. One enclosing /tmp/linker-knowledge-observation-548 was reused for bounded tests/static analysis and finally removed; readback confirms absence after every completed invocation. Temporary released bytes were not measured separately and are not claimed as a disk-space delta. Existing dependencies and unrelated WIP remain required and untouched.

Native PHP author independent incremental Spec+Standards review also PASS, no blocking findings; original ACK authority, current-input/version/product/coverage equality, no-active-lease guard and monotonic epoch were independently checked. Both independent reviews reuse the recorded targeted tests/static results and performed no source edits, repeated suite or production requests.

统一候选收口：知识分支已fast-forward到815 main merge dabd78f2e；36个当时已有WIP文件逐SHA确认整合未改，815/817/Planner实际交付记录及本候选证据无损汇总。后续批次origin绑定、unknown/可信ACK恢复、上传前置/delta、MU purpose接线和engine owned-runtime均分别获独立Spec/Standards增量PASS。最后完整Genie mypy .含225文件、完整commerce PHPStan含tests均通过；815集成的16个既有planning/route预算用例通过。final候选CI待统一执行，不能将本地与评审通过写成已生产发布。当前GC仍未成功删除生产CAS，生产保留旧6候选字节；后续必须用包含owned root修复的新release。当前自动Genie46已自然ACK/readback，具体导致此前repair的旧literal原因被ACK覆盖仍未知，不把代码反例当作该次网络故障的确定因果。

Shared brand/series read-only coverage resource contract: owner sol_local_retire_implementation, integrated candidate22bc7ceb. Reuse existing full-site inventory/matrices and existing code; inspect exactly the34 shared brand/series URLs and5taxonomy aliases, starting with minimal representative origin/locale/product-set/filter/template mechanisms. At most one bounded read-only SSH/WP process and sequential bounded anonymous HTTP reads, no remote script/file/config/DB writes or service action. No new instance/environment/snapshot/report. HTTP bodies stay in memory; retain only compact unique findings in this INDEX. If browser is necessary, reuse at most one existing tab, never close user tabs; create none. Every task process exits/reaps after its operation; no persistent transport, screenshot or cache copy.


PR819 candidate checkpoint: commit22bc7ceb89eb11bb5c222cd6d6a7faf67f7b7de1, https://github.com/AssassinFlash/de-linker/pull/819, CI41177958428 running. Connector create failed authentication before creation; REST/gh list confirmed no duplicate, existing authenticated gh created819. One temporary PR body file was removed in finally, no config changed. Current resource readback831GiB available /2.8TiB used, no new worktree/environment.

CI remaining granularity finding: tools/checks/ci_scope.py classify() still falls back to FULL_LANES for general commerce PHP and MU paths outside the narrow commerce allowlist;819 therefore selects all PHP/JS/Python/content/build/native lanes despite no JS runtime diff. The visible lanes/cancellation improvements already delivered do not close this remaining scope issue. Preserve this candidate CI and its release gate; next CI increment should map actual package/dependency influence and test general PHP/MU/engine/Genie mixed changes, without skipping necessary native authority checks or relaunching unchanged validation. This is an identified implementation limit, not a claim that all selected checks are redundant.

CI819 native compatibility correction resource contract: owner sol_local_retire_implementation, parent coordinated exclusive reuse of stopped ci_preflight (8919/8920/8921). Own only two existing native integration files plus a necessary confirmed Publication model-term root-cause increment. First capture actual synthetic-product manifest exception without weakening guards; then run only ResourceAdmission failing method and PublicationPreparationRecipe integration range. Reuse current dependency env and retained instance/DB, no new instance/snapshot/browser/script/report. At most one PHP/local process sequence, no paid model or mail; local isolation and original queue/cart/user/options/actions must be restored by existing teardown. Start only needed PHP, finally native down and read back pid/listener absence. Source/regression persists; task-only synthetic products, terms/queue/AS rows and files are deleted/restored in teardown/finally, no blanket cleanup.


819 first CI failure retained: native runtime ResourceAdmissionTest::test_native_genie_list_writes_and_replays_keep_their_proof_contract line828 received publication_unavailable503 (19cases379assert); native cleanup succeeded and siblings cancelled. Genie full lane also exposes original table-axis/warranty SQLite consumer fixtures with no new model identity. Parent owns only tests/test_table_compiler_axis.py and test_warranty_terms.py identity metadata upgrade; do not change original PDF/Docling/manifest files, expected numbers, reference revocation or production authorization. Existing .venv reused; one /tmp/linker819-genie-fixture-check root for these two affected modules, owner parent, bounded to pytest lifetime, finally exact cleanup; no real HTTP, new instance/dependencies or persistent log files. Sol local owner separately handles native failure and legacy native protocol fixtures.

Genie CI fixture correction result: two affected original table-axis/warranty modules yielded61pass/1remaining captured-cohort identity failure; the additional current-policy fixture now explicitly upgrades only in-memory manifest and captured scopes to fixture-identity-1, preserving original files and all physical-anchor/number/revocation/tamper assertions. That one remaining case passes3.41s; prior61 results reused. Both changed test files pass Ruff/format/mypy. No production source or authorization fallback changed. /tmp/linker819-genie-fixture-check removed after both invocations; no new dependencies, servers or retained artifacts. First four-line independent Spec/StandardsPASS; final captured-cohort delta awaiting same reviewer.

Planner post819 read-only preparation resource contract: owner sol_planner_gc_implementation, parent remains the sole coordinated production writer. Candidate22bc is not deployed before final CI+merge authorization. Reuse current tree, existing Oct31 archive and RECOVERY-POINTS registry. At most one bounded SSH read process at a time (ConnectTimeout20, ServerAlive15/CountMax2, no ControlMaster/socket), no remote/local temporary file, backup, release directory, instance or production mutation. Read selection/process/readiness/load, immutable DB only when WAL is empty, and CAS metadata into memory; exit/reap transport after each bounded operation. Existing INDEX retains only compact facts and command sequence. No old engine tests or full backup repetition. New release/recovery/GC resources require the later approved execution contract and cannot be created in this read-only phase.

Final eight-line Genie fixture increment independently Spec+StandardsPASS, no repeated checks. Parent also wires the existing PublicationPreparationRecipeTest into ci-native runtime using that same already-running WordPress instance: prior CI filters omitted this native lease/ACK/observation protocol contract. No new suite/process/environment design; Sol owner makes its own tiny hosted fixture self-contained on bare CI and cleans it through existing teardown. Required runtime coverage is now explicit alongside ResourceAdmissionTest.

Planner post819 read-only checkpoint (2026-10-31T06:55:53Z): selected current3a551ec59f009c2e83026b014d58b1b91d7e29ecfec313c6ec14536dc25937dc, previous01ac2230e7ab4aa4cfc27f0e8ce9eb2eaa20ec984a40a7c1c89d0abaff5bc5fd, exactly2 retained releases. HTTP353762 / worker353822 active-running, NRestarts0; native probe verifies8911 ownership and ready worker generation928c5a73555e4d389e7e5977e382af3d and runtime7fb0962e88add78ba5ddc76f338a184bc1738c953bb10b5ca22ef9241865487b / execution69759854dbc1069b6a36055a5dcdb0b22932c71f24052c83260f525998e1862e / storagef91b6338e5204a220d7163fde4277f900fc0c12ca913edec9d7c1560f0eb06d4. DB schema5/294912B, WAL0 before+after with identical size/mtime; immutable transaction shows18projects/56revisions/55runs/55jobs (53succeeded,2failed), no queued/running or active execution route. Every table's complete sorted-row hash equals Oct31 archive, including execution_control draining=0. Live DB file SHA f8b22c67278d456705d740de1c0b639fc27a7b8842dcad3b85768b0fb90ccbb7 differs from archive bytes but no row difference is observed. CAS metadata630files/204375158B, old archive629 all present, only delta current runtime7fb/3059504B (actual current file checksum matches), hardlinked files0. Previous remote temporary recovery root absent. Load0.127/0.031/0.008; available RAM2978360kB/no swap; remote free45608337408B. No production mutation, new snapshot, stage or test occurred.

Prepared post-merge execution boundary: verify final merged engine subtree against reviewed candidate; create exactly one random64hex immutable release, transfer only src/schemas/ops/pyproject.toml/uv.lock by explicit Python USTAR (no AppleDouble), build locked no-dev venv at final path. Copy current runtime/worker policy and derive only spec.release; prepare uses current http.env as source-environment, with public authority URL read internally. Require independent source digest, service UID loading and native prepared receipt before service changes. Native commands, sequentially inspected: python3 NEW/ops/planner_release.py prepare NEW/.deploy/spec.json --source-environment CURRENT/.deploy/http.env --publication-url PUBLIC_URL; then activate NEW/.deploy/spec.json; then status NEW/.deploy/spec.json. If activation fails, inspect actual selector/pair first: recover the explicitly saved prior CURRENT spec using the new operator when needed, rather than blindly rollback to an older previous. After a successful switch, native rollback NEW/.deploy/spec.json is the retained paired rollback. No manual drain/systemctl sequence.

Archive reuse decision: archive.backup has no incremental API. Official independent_snapshot permits immutable blob hardlinks while requiring independent single-link DB/manifest. One new complete local archive may therefore reuse verified Oct31 CAS by hardlinks, receive a fresh SQLite backup-to-memory plus exact canonical official manifest and only missing CAS bytes under the new source's shared .cas.lock, then native verify/independent_snapshot, publish and ACK before source unlock. Existing archive is never edited. At this checkpoint transfer delta is only3059504B plus fresh DB/manifest. New complete verification and explicit baseline116-root coverage precede N3 rotation of the superseded Oct28 archive; Oct27 DB stays protected. Do not claim a built-in incremental backup command or skip full checksum/closure verification.

After new pair and saved-report readback, default native retention is advisory/read-only; use its newly computed candidates, never the old6list as authorization. Remote recovery is one outside-workspace temporary root with exact independent DB/manifest copies (Python USTAR2regular files) and source immutable CAS hardlinks. Separate upload result, native independent_snapshot/逐hash verify PASS, and apply calls. Apply command: python3 NEW/ops/planner_release.py retention NEW/.deploy/spec.json --recovery RECOVERY_ROOT --apply; native operator owns operator.lock, drain/queue exit, stopped HTTP/worker/listener proof, exclusive CAS lock and fresh full closure/candidate coverage, then finally paired start/readiness/resume. Current new runtime is an owned root; old7fb may become reclaimable only after actual new-runtime switch and fresh mark. Unknown/new uncovered bytes refuse before unlink and restore services; no ad-hoc archive mutation or fake DB reference. Verify deletion outcome, refs/history/saved report, ready PIDs/generation/draining=false/pending0 and zero replan, then remove remote hardlink root before measuring physical free-space change. Staging/recovery are online; only native activate and native retention have distinct stop windows. Policy30s drain/start/stop are per-step budgets, not a promised total outage. All production writes remain gated on parent final CI+merge authorization.

Read-only resource closeout: SSH process exited0/reaped, no ControlMaster/socket/temp/root was created. Existing three complete local archives and protected Oct27 baseline remain; Oct31 DB/manifest hashes still match registry. No incoming trees or prior private socket. Mac free892632768512B (~831GiB), no removal or released-space claim. Persistent change from this subtask is only this existing INDEX append; other owners' WIP is untouched. Further production sampling stops until the authorized execution window.

CI819 native root cause was reproduced on the existing bare ci_preflight: actual synthetic WC_Product, taxonomy_exists(pa_model)=false, native term error invalid_taxonomy, direct Publication::manifest RuntimeException Current model identity terms could not be read. A published Woo product does not require a registered model attribute; no model relationships form a legitimate empty identity map. Minimal Publication correction accepts only invalid_taxonomy with taxonomy_exists=false; an existing attribute or any other read error still fails503. Identity unit7tests67assertions passes, including absent-taxonomy identity and registered-taxonomy error distinction. Original ResourceAdmission failing method is unchanged except owned AS/pending cleanup and now passes1test16assertions0.722s. Recipe integration now supplies real native identity protocol/ACK/loaded fields and explicitly distinguishes unknown observation preservation from a complete mismatching generation; its6tests129assertions pass2.876s. Each case owns one small hosted original and product rather than requiring a production snapshot. Parent reviewed source/fixture increment Spec+Standards PASS and connected the existing Recipe filter into the same runtime CI instance.
Final fourPHP-file WPCS/PHPStan and diff-check pass. First native green revealed24 task-created translation/attribute-index AS rows; their exact IDs12986–13009 were inspected and deleted, plus three exact diagnostic actions12983–12985 for owned deleted product13861. The fixture cleanup now records/removes only its new actions. Final repeat preserves all12809 then-existing action IDs exactly and leaves0new rows; after separately reclaiming the three diagnostic rows,12806 pre-existing actions remain untouched. Products returnto0/users1; publication queue and pending hashes match before/after; all publication-recipe upload dirs absent. finally down0, run pid files0 and8919/8920/8921 listeners0. No production request, mail transport, new instance/environment/snapshot or retained temporary script.
