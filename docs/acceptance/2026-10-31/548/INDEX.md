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

CI预检分流/可见进度/取消清理、Genie日志生命周期、WordPress重复manifest与认领重试去重、失败服务复制清理正在同批实现和定向验证，尚未发布。正式结论以最终评审、CI和实际消费者读回更新，不能把此段候选状态当线上完成。

当前文档中的认证哈希已移除，但旧Git提交仍包含该材料，历史暴露与后续处置未关闭。未执行历史改写或修改生产账号。

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
