# 2026-10-31 · 统一方案工作台与客户链路读回（#548）

本轮在生产 `de-linker.com` 上完成的读回。每条都附执行方式与实际返回，不写推测。

## 1. 已保存方案 8207 的界面读回

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

## 2. 真实询盘提交（含人机验证）

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

**邮件**：`linker_mail_job` 中没有 8457 的记录。`JobStore` 只在发送失败时保留消息，因此「无记录」即「首次发送成功」。业主确认已收到邮件。

## 3. 客户下载报告 PDF

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

## 4. 生产改动与回滚

本轮为取得 user 1 读回，曾短暂改动生产账号，全部已按原字节回滚：

| 动作 | 状态 |
| --- | --- |
| 建临时管理员 `ss-verify-548`（ID 46） | 已删除 |
| user 1 `user_pass` 临时改写 | 已按原字节写回并核对：`$wp$2y$10$Zaf2kyXdBrU7eksFQM.uEe/nc081nCl0bwUust5YnX4uneohi/gSC` |
| 测试邮件重写开关 | 询盘前开、提交后立即关；当前 `off` |
| 前缀残留查询（`ss-verify%`/`ss-probe%`/`example.invalid`） | 空 |
| 生产用户数 | `17 → 16` |

## 5. 本轮发现、尚未修复

**邮件队列积压**：生产 `linker_mail_job` 有 **38 条** `private` 状态的失败记录，创建时间集中在 `2026-10-22 14:3x`，标题形如 `New inquiry #8204 from google`。这些是未送达的团队通知。本条属独立缺陷，未在本轮修复。

**`Send password reset` 误触**：操作管理列表时误点该链接。WordPress 的该动作在 GET 时发信，但返回 `reset_count=0`（自报未发出任何一封）；当时 `test-mail` 为 `off`，本次会话未更改其状态。业主未报告收到该邮件。

## 6. 环境与资源

| 项 | 值 |
| --- | --- |
| 磁盘可用 | 834 GiB |
| 本轮临时文件 `/tmp/548-*` | 已全部删除 |
| 生产备份 | 未新增（本轮仅账号与开关改动，均即时回滚） |
| 本地实例 | 未启动 |
| 浏览器 | 仅复用既有一个 tab，未新建 |

证据文件保存在仓库忽略目录 `.scratch/`：`548-withkey.pdf`、`548-nokey.json`。
