# 通知/回执链路生产只读审计（#533 D 域 remainder）

日期：2026-11-04（证据采样窗口： WooCommerce `linker-mail` 日志 2026-10-17 起、`~/.logs/mail.log`、队列 post 状态、Action Scheduler 表、相关 options）
范围：**生产只读**。未向生产写入任何数据、未发送任何测试邮件、未改动任何配置。所有结论来自 SSH + WP-CLI / SQL 只读查询与仓库源码比对。

依据：业主 2026-10-17 裁定（AGENTS.md §2）——内部通知（新注册、VAT 复核、新询盘、联系表单、每日摘要）只发 `sales@sunriverinverter.com`，不发 `sales@de-linker.com`；`chester@de-linker.com` 经确认能收到才保留作抄送；客户可见发件人/地址仍是 `sales@de-linker.com`。

---

## 1. 链路现状（实现地图）

### 1.1 Outbox 实现（唯一实现，无 mu-plugins 参与）

- 实现：`plugins/linker-commerce/includes/Mail/Outbox.php`，挂在 `pre_wp_mail` 上接管全站每一次 `wp_mail()`（含 WooCommerce 邮件）。
- 队列存储：私有文章类型 `linker_mail_job`（`JobStore.php`）；完整报文 JSON 存于 `_linker_mail_message` post meta，`_linker_mail_attempts` 计数，`_linker_mail_error` 存最后一次错误。
- 重试：Action Scheduler 钩子 `linker_commerce_mail_attempt`（组 `linker-commerce`）；退避梯度 60s/300s/1800s/7200s/21600s/43200s/86400s（共 8 次尝试，跨度 > 24h 配额窗口），之后 **dead-letter**：`post_status=draft`，计入摘要第四块 `FailedEmails`。
- 日志：`wc_get_logger` source `linker-mail`（WooCommerce → 状态 → 日志），线上每天一个文件，自 2026-10-17 起连续 19 天无缺口。
- 测试模式：选项 `linker_commerce_test_mail_to` **不存在 = 关闭**（符合测试邮件纪律：测试收件人重写开关平时必须撤除）。
- 生产 mu-plugins 逐一核对（`linker-deploy-reset`、`linker-engine-pin`、`linker-error-recorder`、`linker-inventory-access`、`linker-publication-worker-access`、`linker-site-guards`、hostinger/livecanvas 自带）：**均不处理邮件**，不存在第二条 outbox/收件人改写通道。

### 1.2 收件人与发件人的配置来源

`Settings\Options`（选项级单点）：

| 选项 | 线上值 | 生效值（含默认） | 判定 |
|---|---|---|---|
| `linker_commerce_notify_to` | 未设置 | 默认 `sales@sunriverinverter.com` | ✅ 符合裁定 |
| `linker_commerce_notify_from` | 未设置 | 默认 `sales@sunriverinverter.com`（内部发件地址，须与 SMTP 用户一致） | ✅ |
| `linker_commerce_team_bcc` | `chester@de-linker.com` | 每封内部通知密送 | ✅ 抄送持续在日志中证实送达链路 |
| `linker_commerce_team_to` | 未设置 | 默认 `sales@de-linker.com`（仅客户可见邮箱） | ✅ 未被内部通知使用 |
| `woocommerce_email_from_address` / `from_name` | `sales@de-linker.com` / `Linker` | 客户邮件发件人 | ✅ 客户面保持不变 |

`TeamEmail` 基类是全部内部通知的唯一收件人来源（`notify_to()` + `notify_bcc()`），新种类继承即同规则；`Health\Monitor` 的直发 `wp_mail()` 同样直接读同一选项。

### 1.3 传输通道证据

- **内部邮件**：`Mail\InternalSmtp`（#297）经认证 SMTP，凭据在 `PrivateConfigDirectory::path('sunriver-smtp.env')`（网站根目录之外的私有配置文件，不在数据库）；PHP `mail()` 作预算可用时的回退。线上 `linker_commerce_internal_smtp_outcome` = `{"status":"success","reason":""}`（at=1793779210 ≈ 2026-11-03，对应询盘 #8535 的内部通知）。
- **客户邮件**：PHP `mail()`（web PHP）。Hostinger web-PHP `mail.log` 在 `/home/u388076051/.logs/mail.log`（420 KB，mtime 2026-11-03），其中 de-linker.com 条目可逐一与 `linker-mail` 日志互证（例：2026-10-28 `Registrierung eingegangen` → `info@notstrom1.at`，From `Linker <sales@de-linker.com>`；2026-10-31 #8457 客户回执）。**cron（CLI PHP）的 mail.log 未设置**——摘要与重试只留 `linker-mail` 日志痕迹，与代码注释记录的 2026-10-17 主机实测一致。

---

## 2. 各通知种类 × 实际路由 vs 裁定

`linker-mail` 日志（2026-10-17 起）中的全部真实发送均路由正确；`sales@de-linker.com` **从未出现在任何内部通知收件人里**：

| 种类 | 实现类 | 裁定路由 | 线上实际（最近真实证据） | 判定 |
|---|---|---|---|---|
| 新注册 | `Registration\Emails\NewCustomerEmail`（TeamEmail） | sunriverinverter + bcc chester | 2026-10-18 / 10-19 / 10-28（Notstrom1e.U.）均 `→ sales@sunriverinverter.com, bcc chester@de-linker.com` | ✅ |
| VAT 复核 | `Registration\Emails\VatReviewEmail`（TeamEmail） | 同上 | 窗口内**无真实触发**（无触发条件的注册发生）；代码级同源路由 + `NotificationRoutingTest` 覆盖 | ✅（代码级，无回执证据，见 §6） |
| 新询盘 | `Inquiry\Emails\NewInquiryEmail`（TeamEmail） | 同上 | 2026-10-22 约 60 封（hold 确认前）、2026-10-31 #8457、2026-11-03 #8535（验收 #533）均路由正确 | ✅ |
| 联系表单 | `Contact\Module`：同一询盘管道（"两扇门、一份记录"），团队通知即 `NewInquiryEmail` | 同上 | 窗口内无独立联系留言事件；路由同上 | ✅（代码级） |
| 每日摘要 | `Digest\DigestEmail`（TeamEmail） | 同上 | 每日一封，2026-10-21 起无中断（详见 §4） | ✅ |
| 复核催办 | `Message::REVIEW_REMINDER` 类目 | 同上 | 2026-10-22 曾发出 4 封（15:24–18:25 UTC），其后按业主停止政策由 `Outbox::hold_review_reminder` 永久扣留（`review_reminders_disabled`） | ✅ 停发符合裁定 |
| 健康告警 | `Health\Monitor` → notify_to | 同上 | 窗口内无告警触发（无失败） | ✅（无事件） |
| 客户回执/事务邮件 | `InquiryReceivedEmail` 等 `CustomerOrderEmail`/`WC_Email` | 发往客户，From `sales@de-linker.com` | mail.log 实证 From 为 `sales@de-linker.com` | ✅ |

---

## 3. 队列/重试健康

- **队列现状**：`linker_mail_job` 共 38 篇，全部 `private`（等待中），0 篇 dead-letter（`draft` 计数 0）。
- **38 篇滞留任务 = 有意隔离，不是丢失**：全部创建于 2026-10-22 14:17–14:38（主机本地时；06:17–06:38 UTC），标题均为 `New inquiry #81xx from google`（俄语 gmail 地址的机器人洪水）。根因（逐项核实）：每篇 job 及其订单都带 `_linker_incident_hold = {incident: "public-inquiry-campaign-20261022", reason: "confirmed_campaign_notification_hold", manifest_sha256: …}`；`attempts=0`、无 `_linker_mail_error`、`_linker_mail_inquiry` 为空；Action Scheduler 中该钩子 0 条 pending（102 complete / 1 canceled）。`SendAuthorization::allows()` 在订单被 hold 时拒绝放行且不重排——即这些任务被活动级扣留，等待员工释放/擦除（`NotificationHold::release` / `SendAuthorization::release` 管道存在）。
- **hold 确认前的发送**：洪水当日 00:06–06:16 UTC 约 60 封团队通知与客户回执**已经发出**——收件人全部正确（内部 → `sales@sunriverinverter.com` + bcc chester；回执 → 提交者邮箱），路由无违例。
- **重试行为**：退避梯度有限（8 次 ≈ 46h），随后 dead-letter 进摘要第四块；窗口内没有任何一封走到 dead-letter。
- **日志健康**：19 个 `linker-mail` 日志文件 **0 条 WARNING/ERROR**。
- 节流状态选项 `linker_commerce_mail_sends` 当前 0 条目（无 PHP 通道在途配额占用；内部通道走 SMTP 独立预算）。

## 4. 每日摘要

- **是否运行**：是。链式单事件 `linker_commerce_digest`，每天 09:00 Europe/Berlin；下一跳 2026-11-05 08:00 UTC。日志可证实自 **2026-10-21**（功能上线）起逐日送达，含夏令时切换（10-25 前 07:00 UTC / 后 08:00 UTC，墙钟 09:00 柏林时间两侧一致）。
- **最近一次**：2026-11-04 08:00:10 UTC，`【Linker 业务简报】2026年11月4日：2 个待审客户 · 106 条待开 PI` → `sales@sunriverinverter.com`, bcc `chester@de-linker.com`。
- **内容**：五块——待开 PI 询盘、待回复 Proforma、失败邮件（0）、内部邮箱健康、待复核项（`Digest\Blocks`）。
- **唯一异常**：2026-10-29 同日两封摘要（08:00:15 与 08:00:17，2 秒间隔）。根因：重叠的 cron 消费者各自入队一次普通投递；当日即由提交 `4ee218f34`（"admit one ordinary job when daily cron consumers overlap"，`NativeDailyDelivery` 普通投递回执去重）修复，10-30 至 11-04 每日单封，无复发。
- **观察（非路由缺陷）**：「106 条待开 PI」被隔离活动留在 `inquiry-received` 状态的约百条垃圾订单抬高——摘要按订单状态计数而非按已通知询盘计数；活动擦除/清退后自然回落。是否清退那批订单属业主决定，未在本只读审计内处理。

## 5. 凭据暴露检查（#533 goal）

只报告位置，本报告不含任何密钥内容：

- 队列/hold 报文：`wp_postmeta` 中 `_linker_mail_message` / `_linker_incident_hold` / `_linker_inquiry_queue` 对 `sk-`、`Bearer `、`PRIVATE KEY`、`Authorization:`、`api_key`、`password` 模式 LIKE 扫描——**0 命中**。
- options（`linker_%`、`woocommerce%`）同模式扫描——**0 命中**。
- `wp-content/uploads/wc-logs/` 全量正则扫描（sk-/Bearer/PRIVATE KEY/ghp_）——**0 命中**。
- SMTP 凭据在网站根外的 `sunriver-smtp.env` 文件（不入库、不入日志）；`Outbox::remember_error()` 对 SMTP 失败统一记录固定诊断串 `InternalSmtp::FAILURE_MESSAGE`，不回显服务器原文（#297 防回显设计在位）。
- **未发现任何凭据/令牌落入日志、options 或队列负载。**
- 邻近事实（不属本站缺陷）：`~/.logs/mail.log` 为共享账号级文件，混有同账号其他域名（metal-divider、sunriver）的邮件头；仅本站审计视角记录，未扩散。

## 6. 未能验证的事项（诚实边界）

只读约束下无法验证：

1. **物理送达**：`linker-mail` 的 INFO 行证明 `wp_mail()` 返回 true（PHPMailer 接受），不能证明对方邮箱实际收到。裁定要求的"业主路径线上实走"不在本审计内。
2. **VAT 复核与联系表单的真实回执**：窗口内（日志起点 2026-10-17）没有触发过这两种通知；其路由为代码级验证（同 `TeamEmail` 单源）+ 既有 `NotificationRoutingTest`，无生产回执证据。
3. **隔离任务释放后的送达**：38 篇 hold 任务若被员工释放能否正常投递，未（也不能在不发信的前提下）实测；放行管道与审计（`SendAuthorization::release`，nonce/capability 校验 + 事件记录）在代码层完整。
4. `linker_commerce_mail_sends` 选项 0 条目与其设计语义（是否只记 PHP 通道、是否随成功即清）未逐行核对 `Throttle` 写入路径，未作为任何结论的依据。

## 7. 结论

- **路由合规**：窗口内全部真实内部通知（注册、询盘、摘要、催办、验收 #533 测试询盘）一律 `sales@sunriverinverter.com` + bcc `chester@de-linker.com`；`sales@de-linker.com` 只作客户可见地址与客户邮件发件人。与 2026-10-17 裁定**零偏差**。
- **队列健康**：无积压（38 篇为有意隔离的活动扣留，非缺陷）、无 dead-letter、无失败重试循环、无日志错误；重试有界、dead-letter 进摘要可见。
- **摘要管道**：每日运行正常，历史上唯一一次重复投递已于当日修复并有连续 6 天单封证据。
- **凭据面**：未发现暴露。
- 无需修复项；遗留观察一项（§4 垃圾订单抬高待开 PI 计数）供业主/父线决定清退。

---

*资源报告：本审计未在生产创建/删除任何文件，未启动任何进程；SSH 会话即开即用即断，本机未新增临时文件；无待回收资源。*
