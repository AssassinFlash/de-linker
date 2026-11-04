# #533 D 域 remainder：contact / VAT 通知链生产证据（收口记录）

日期：2026-11-04（UTC）执行、2026-11-05 入库。执行线：通知/回执验证线（父线授权生产写入；测试邮件纪律＝AGENTS.md §5）。
关联：`docs/research/2026-11-04-notification-receipt-audit.md`（同一通知面的只读审计）。
恢复点：`.scratch/notification-e2e-533/backup-pre-e2e-2026-11-04.sql.gz`（本机，纯 PHP 只读转储，80,085 行 INSERT，含 `-- DONE` 尾标；父线已验证，保留至父线复核后回收）。

---

## 1. VAT 复核通知（VatReviewEmail）——生产端到端完成

**触发路径（全部真实客户路径，无状态直写）**：My Account → Company → Edit Company details → 保存 billing
（`woocommerce_customer_save_address` → `BillingVatField::after_address_saved` → `VatProfile::update(…, notify: true)` →
裁决变化 → `linker_commerce_vat_status_changed` → `VatReviewEmail::trigger` → `VatNotice::deliver`：
`Prepared::capture` 在 `pre_wp_mail` 边界捕获完整原始报文（不发送的边界）→ `JobStore::create`（原始收件人入队）→
`Outbox::HOOK` 即时尝试 → TestMode 投递时重写）。

**对象**：自有测试账号 user 49 `audit-vat-533`（`audit-533@de-linker.com`，公司 `Linker Notification Audit 533`；
wp-cli 创建，创建零邮件）。真实客户账号未触碰。

**步骤与证据**：

| 步 | 动作（真实 UI） | 结果 | 证据 |
|---|---|---|---|
| 1 | Company 表单保存，VAT=CN1234567890（非欧盟号） | 首次裁决 `unverified`（not an EU VAT ID，无 VIES 外呼）；**按设计零通知**（`VatNotice::persist`：previous 为空不 pending） | user meta `linker_vat_status=unverified`（后续被步骤 2 覆盖）；当日日志 15:51:44 前无任何 VAT 邮件 |
| 2 | 同一表单清空 VAT 再保存 | 裁决变化 `unverified→none` → 唯一一封 VAT 通知；test-mail on → 投递重写到 tester 单地址 | user meta `_linker_vat_notice_source = {"previous":"unverified","current":"none","job":8599,…,"pending":"no"}`；日志 `2026-11-04T15:51:44+00:00 INFO Email "VAT check changed: Linker Notification Audit 533" sent to chester@de-linker.com`；job 8599 投递成功后删除（`get_post_status(8599)=false`） |

**发送计数**：VAT 场景实发 **1 封**，仅 tester（chester@de-linker.com）。开关用后即关（`test-mail status` 读回 off）。

**原始路由证明（诚实边界）**：队列原始数据抓取未取得——`VatNotice::deliver` 在同一请求内创建 job 并即时尝试，
job 生存期毫秒级；首个 watcher 的输出因会话中断丢失（本地 `watcher.jsonl` 0 行）。原始路由由以下三层佐证：
① `TeamEmail::get_headers` 是全部内部通知唯一收件人来源（与 #8535 团队邮件同一接缝，后者在 **test mode off** 期间投递，
其日志行即原始路由实证：`sent to sales@sunriverinverter.com, bcc chester@de-linker.com`）；
② `Prepared::capture` 捕获的即 `wp_mail` 原始参数（重写只发生在 `Outbox::attempt` 内 `TestMode::redirect`）；
③ 集成测试 `NotificationRoutingTest`。传输通道：该邮件不在 web-PHP `mail.log`（当日 0 条）→ 走内部 SMTP 或 CLI/cron
PHP 通道（两者均不写该日志）；`linker-mail` 日志行为投递权威记录。

## 2. Contact 表单（NewInquiryEmail，contact 门）——既有端到端证据 + 今日自动化受阻取证

**既有生产端到端证据（无需新发邮件）**：**order 8535 就是 contact 门创建**（`_linker_inquiry_source=contact`、
`created_via=linker_contact`、2026-11-03T16:25:03Z）。当日链路：真实公开表单 → HPOS 记录 → 评估授权（normal）→
团队+访客回执两封投递（16:26:05）。**当时 test mode off，日志行即原始路由**：
`New inquiry #8535 from Linker Technology GmbH (Acceptance #533) sent to sales@sunriverinverter.com, bcc chester@de-linker.com`、
`Your inquiry #8535 has been received sent to chester@de-linker.com`（提交者即 tester）。

**今日（2026-11-04 ~16:20–16:35 UTC）新提交取证**（目的：抓队列原始数据 + tester 单投递；未成功，原因如下）：

- 环境：真实访客路径、内嵌浏览器、protection=`enforce`、contact 验证 required（读回确认）。
- 原始状态序列（逐字）：
  1. `No request has been sent in this attempt. Please complete the verification.`（interactive）
  2. 首次提交等待令牌超时后：`Verification could not be completed. No request has been sent in this attempt. Please try again or email sales@de-linker.com.`
- 证据图：`contact-turnstile-failed-state-2026-11-04.png`（整页失败态）、`contact-turnstile-widget-crop-2026-11-04.png`（widget 区裁图）。
- 点击记录：widget 容器边界 y≈622–766（图像像素）；复选框坐标点击 6 次（含前台可见标签页重试）均未出令牌，状态保持 interactive。
- 服务器侧互证：`linker_public_admission_ledger` 当日 **0 条** `verification_contact` 条目＝客户端从未拿到令牌、从未调 verify；
  无 POST（URL 恒为 `/contact/`）、无新订单（最新订单仍 8535）、当日邮件日志除 08:00 摘要与 15:51:44 VAT 外 **0 新行**、
  队列 38 条隔离任务不变、watcher 全程 0 新 job。
- 服务端边界探测：无 proof 的合法表单 POST（nonce/蜜罐/时钟全合法）与浏览器 GET `admin-post.php?action=linker_contact`
  均得到边缘层主题化 404（LiteSpeed/边缘对非表单 POST 请求的行为；`linker-site-guards` 仅管 REST users）。
  WP 层结论**不成立也不必**：admin-post 表单 POST 通道由 #8535（11-03）证明可用。
- **根因（两项独立环境互证）**：Cloudflare Turnstile 交互挑战不向自动化受控浏览器放行令牌（本内嵌浏览器与父线 Playwright
  均停在 interactive）。**防护全程未关闭、未绕过**；真人影响既未证实也未证伪——#8535 证明该门在真实浏览器下 11-03 可完整通过。
- **发送计数**：contact 场景实发 **0 封**（从未产生可投递消息）。

## 3. 防滥用与隔离完整性

- 38 条 `public-inquiry-campaign-20261022` 隔离 job 全程未触碰（前后计数一致 private=38，draft=0）。
- 客户端不交、服务器 ledger 零 verify、`Outbox` 零新 job：三层互证当日无任何测试外邮件逃逸。
- 每日摘要 2026-11-04T08:00:10Z 正常发出（真实内部路由，非本场景）。

## 4. 生产对象与清理

| 对象 | 处置 |
|---|---|
| user 49 `audit-vat-533`（含 VAT/公司元数据） | **保留**（VAT 证据载体：`_linker_vat_notice_source` 即在其 user meta 上）；属必要测试对象，后续清退由父线决定 |
| contact 订单 | 今日无新增（未产生）；8535 为既有验收记录，保留 |
| `linker_commerce_test_mail_to` | **已删除并读回**（`Test mode is off`） |
| 主机 `/home/u388076051/dlk-tmp-watcher.php`、`dlk-tmp-dump.php` | 均已删除并验证不存在 |
| 本机 `.scratch/notification-e2e-533/` | 保留备份 gz 与账号口令文件（路径见文末）；空 watcher 产物与一次性脚本已删 |

## 5. 本机证据与资源报告

- `docs/acceptance/2026-11-04/notification-contact-vat/`（本文件 + 2 PNG）。
- `.scratch/notification-e2e-533/backup-pre-e2e-2026-11-04.sql.gz`（8.1 MB，恢复点，保留至父线复核）。
- `.scratch/notification-e2e-533/audit-account-pass.txt`（user 49 口令，仅本机，不入库）。
- 浏览器：本线自建生产标签已关闭；未触碰他线标签（本地 dummy 链）。
- 进程/临时文件：无遗留（watcher 任务已停、主机脚本已删、/tmp 抓取文件已清）。
- 生产写入合计：test-mail 开关 2 次（终态 off 并读回）、user 49 及其 meta、（VAT 场景）1 封 tester 邮件；无数据库结构或内容删除。
