# de-linker.com 邮件停发根因调查（只读，2026-10-09）

调查时间：2026-10-09 06:40–07:15 UTC（14:40–15:15 北京时间）。全部为只读操作：SSH 上 `cat/grep/ls/strings`、`wp db query`（仅 SELECT）、`wp option get`、`wp plugin list`；本机 `dig`；外部资料只经 Apify。另做了一次**仅 TCP 建连、不进行 SMTP 对话**的端口可达性检查（见 §9）。没有发信、没有改设置、没有写站点或服务器。未读取/打印任何口令、令牌（`wp-config` 密钥行、`~/.api_token`、Apify token 均未输出）。

下文时间默认 **UTC**（站点 `gmt_offset=8`，北京时间 = UTC+8）。

---

## 0. 结论

1. **停发的直接原因：Hostinger 共享主机对“服务器内置发信”（PHP `mail()`/PHPMailer → sendmail）的硬性配额——每分钟 10 封、滚动 24 小时 100 封——在 2026-10-08 被用尽。**
   - 账号自 5 月以来的完整 `mail()` 记录（`~/.logs/mail.log`）显示：10-08 之前，任意 24 小时最多 **36** 次调用、任意 60 秒最多 **6** 次，从未接近配额，所以“以前都能发”。
   - 10-08 当天 **197** 次 `mail()`（大部分是 184–194 票的线上测试）；15:32–15:50 有 6 次“同一两秒内 13–20 封”的突发，超出 10/分钟，这就是当时“间歇性” `Could not instantiate mail function` 的来源；**18:07:37 起，累计接受量到达 24 小时上限，此后每一次 `mail()` 都被拒**——到 10-09 04:03:12 为止连续 68 次尝试 0 成功，并且跨过了午夜（说明是滚动 24 小时窗口，不是自然日）。
   - 按文档上限回放日志（§4.3），能复现 18:07:37 这一秒内“VAT 副本被接受、紧随其后的 New-customer 副本被拒”的分界。
2. **“现在的处理方式是错的”这一判断成立，但错在下面几处，而不是“请求上下文”或 From：**
   - 2026-09-30 起每封业务通知拆成 **4 封独立邮件**（主信 + 3 个副本），每次通知消耗 4 份配额；
   - 失败后的重试梯（主信 6 次 + 副本 5 轮×3 封）会把一封通知放大到最多 **21 次** `mail()`。它们在约 2.6 小时内全部用完就放弃，而配额窗口是 24 小时，所以在配额耗尽期间的邮件**全部永久丢失**，没有一封等到窗口重新放开；
   - 194 票新上的副本任务把整封邮件正文塞进 Action Scheduler 参数，而 AS 参数上限是 8000 字符，所以 **Woo 的 HTML 业务邮件（new_order 等）的副本根本排不进队列**（服务器 error_log 4 次 `ActionScheduler_Action::$args too long`）。也就是说，即使传输层完全正常，新订单通知也永远到不了 chester@、857@、sunriver 这三个副本箱；
   - 同一个无效税号，每下一单都重新发一遍 “VAT check needs review”（还会连带 3 个副本和重试）；
   - 线上测试大量发往 `@example.test`（7 个注册、5 张订单都是测试数据），白白消耗配额。另外，这份配额是 **同一 Hostinger 账号下 4 个站点共用的**（de-linker.com、sunriver-inverter.com 及其 stg、tvolt-energie.*）。
3. **已排除的原因**：From 从 sunriver 改成 de-linker 并不是停发原因——改完后头 6 封新 From 的邮件都被接受了，随后才因配额触顶开始失败；“请求内（POST）发信会坏、独立请求就好”的说法也不成立——AS 请求、REST 桥请求同样失败，失败只跟发送量有关；WP-Cron/AS 一直在正常运行（逾期待执行 0 条）；去重 transient 也没有造成丢信。
4. **身份与 DNS（另一个层面，不是停发原因）**：de-linker.com 的 MX 在腾讯企业邮，SPF 是 `include:spf.mail.qq.com ~all`，**没有授权 Hostinger 发信**，也没有 DMARC 记录，Hostinger 也不会替 de-linker.com 做 DKIM 签名。所以从 Hostinger 发出、From 为 @de-linker.com 的邮件，在 SPF/DMARC 上都对不齐。sunriverinverter.com 的情况恰恰相反：它的 SPF 包含 Hostinger 中继（`_spf.mail.hostinger.com`），DKIM 也指向 Hostinger，DMARC 是 `p=none`。194 票的说法“改成 de-linker 是对齐发送主机”在 DNS 上不成立：网站托管在哪里，与哪个域名被授权发信是两回事。
5. **当前状态**：系统不会自愈，只会等配额窗口滑过去。按“只计已接受邮件”估算：05:48 UTC 起放出约 4 个名额，约 15:52 UTC（北京 23:52）起大部分恢复，约 18:08 UTC（北京 10-10 02:08）完全恢复。如果被拒的尝试也计入，则要到约 15:52 UTC 之后才开始恢复。10-10 01:00 UTC（北京 09:00）的 daily digest 是一个天然的观察点，不需要我们主动发信（§8）。10-07 之后的订单和注册全部是 `@example.test` 测试数据，**目前没有真实客户的邮件丢失**。

---

## 1. 时间线

| 时间 (UTC) | 事件 | 证据 |
|---|---|---|
| 2026-05-18 → 10-07 | 账号所有站点经 PHP `mail()` 发信。de-linker.com 从 07-03 开始；From 依次为 857@qq、wordpress@de-linker.com，07-26 起为 `Linker <sales@sunriverinverter.com>`（共 404 封，最后一封在 10-08 17:09:32） | `~/.logs/mail.log`（632 行，PHP `mail.log` 记录每一次 `mail()` 调用） |
| 09-29 16:26:44 | 单封邮件 + `Bcc:` 3 个副本 = **1 次 `mail()`** | mail.log |
| 09-30 03:12–03:15 | b2b-core 0.12.368 上线：副本改为 `phpmailer_init` 克隆，每封业务通知 = **4 次 `mail()`** | `.scratch/mail-sunriver-20260930/deploy-log.md`；mail.log |
| 10-08 之前 | 峰值：任意 24 小时最多 36 次（全账号单日最多 34 次），任意 60 秒最多 6 次 | mail.log 统计 |
| 10-08 05:48:40 | bulk order 通知，4 次 | mail.log |
| 10-08 13:58:46–47 | 测试注册 live-verify-184，同 1–2 秒内 13 次 | mail.log |
| 10-08 15:32–15:51 | 测试注册 live-185 / live-de-185 / diag-185 / curl4-185 / final-185，以及多次 probe 和旧的注册重试：本小时 **103 次**；突发 17/13/17/17/20 次（每段 ≤20 秒） | mail.log |
| 10-08 15:37:25 起 | 首批可见失败 `wp_mail_failed: Could not instantiate mail function`（15:37:25/26、15:40:07/08、15:50:07），**全部出现在突发的尾部**；同一时期孤立的 4 封组都成功 | `wc-logs/tv-b2b-admin-mail-2026-10-08-*.log`、`transactional-emails-2026-10-08-*.log`（curl4-185 欢迎信 15:40:07 failed） |
| 10-08 17:09:31–32 | 测试订单 #6556：VAT 主信 + new_order + customer_on_hold，Woo 日志均记为 sent | transactional-emails log |
| 10-08 ~18:06 | 194 上线（From→`sales@de-linker.com`、副本改为 AS 任务、Woo 事务邮件全站 defer） | 提交 12e81a09/8a5c4dd0/50b2fc25；线上文件与链尖字节一致 |
| 10-08 18:07:03 | 新 From 首两封（VAT + New customer 主信）**成功** | mail.log + 该秒无失败日志 |
| 10-08 18:07:37 | mailprobe-194 欢迎信 sent；VAT 副本 ×3 **成功**（即 194 验收时业主收到的那三封）；同一秒 New-customer 副本 ×3 **失败**（attempt 1） | transactional-emails / tv-b2b-admin-mail log |
| 10-08 18:07:37 → 10-09 04:03:12 | **68 次尝试，0 成功**：副本梯 attempt 2–5；“Mailbox receipt probe (194)”；测试订单 #6559/#6560/#6562/#6563 的 new_order 与 customer_on_hold（Woo 记为 failed，无重试）；VAT DE1 主信重试梯（20:01→23:00 共 6 次）；10-09 daily digest（01:06→04:03 主信 6 次 + 副本 5 轮 = 21 次） | 三份日志一一对应 |
| 10-08 20:01:46 / 20:14:41 / 22:24:44 / 22:26:27 | `Caught exception while enqueuing action "tv_b2b_business_mail_copy_job": ... $args too long ... not be more than 8000 characters` —— 恰好对应 4 张测试订单的 new_order | `~/.logs/error_log_de-linker_com` 371–374 行 |
| 10-09 07:00 | 已无任何待执行的邮件任务（重试全部耗尽）；下一个会发信的计划任务：`tv_b2b_daily_digest`，10-10 01:00 UTC | `wp_actionscheduler_actions`、`cron` option |

10-07 之后的全部订单（#6556–#6563，customer 33）和注册（user 30–36）都是 `@example.test`。

## 2. 服务器上的实际发信链路

- `wp_mail()` → PHPMailer 7.1.1，`Mailer='mail'`（默认），`PHPMailer.php:894` 调 `@mail($to,$subject,$body,$header)`，**不带 `-f`**（WordPress 未设置 Sender）。
- `mail()` → `sendmail_path = /usr/sbin/hsendmail -t`（`/opt/alt/php83/etc/php.ini` 与 `/etc/php.ini` 都是这个值；Web 和 CLI 相同；`mail.add_x_header=On`）。
- `/usr/sbin/hsendmail`：Hostinger 自研的 Go 程序（`github.com/hostinger/hsendmail`，版本 1cf0aa2981，2026-06-08）。它用**本主机账号身份**（`unixPeerUsername` + `/run/hsendmail/auth.sock` 取 SMTP AUTH 口令）把邮件以 SMTP 交给 Hostinger 的 MTA。所以限额是**按主机账号 u388076051 计**的——同账号下 4 个站点共享一份（这一点是推断：依据是 mail.log 为账号级、hsendmail 按 Unix 用户认证）。`/usr/sbin/sendmail` 与 hsendmail 是同一个二进制（md5 相同）。
- MTA 拒收 → hsendmail 非 0 退出 → `mail()` 返回 false → PHPMailer 抛出 `Could not instantiate mail function.`（`PHPMailer.php:2150/2527`）。PHP 8.3 不会记录 sendmail 的具体错误文本；PHP 8.5 起才会把 sendmail 的错误作为 E_WARNING 报出（php.net changelog）。所以服务器上看不到拒收原文。
- 没有 SMTP 插件；`wp-config.php` 里没有任何邮件常量；mu-plugins 和两条活动 Code Snippet（#351、#372）都没有挂 `phpmailer_init`/`wp_mail`。站点上与邮件相关的钩子只有：b2b-core 的 `wp_mail_from`/`wp_mail_from_name`/`wp_mail`（priority 100）、`woocommerce_defer_transactional_emails`→true、`wp_mail_failed` 日志；LiveCanvas 表单的 `wp_mail_failed`；SEOPress Pro 的 `wp_mail_content_type`。
- Woo 设置：`woocommerce_email_from_address=sales@de-linker.com`，new/cancelled/failed order 的收件人都是 `sales@de-linker.com`；`admin_email=857558227@qq.com`。
- 出站端口：从主机到 `smtp.exmail.qq.com:465`、`smtp.hostinger.com:465/587` 都能建立 TCP 连接（只建连，未进行任何 SMTP 对话）。

## 3. Hostinger 的公开限额（经 Apify 抓取）

- 《Parameters and limits of hosting plans in Hostinger》 https://www.hostinger.com/support/6976044-parameters-and-limits-of-hosting-plans-in-hostinger/ （抓取 2026-10-09 06:53 UTC，页面显示“Updated 3 hours ago”）：Web/Cloud/Agency 全部套餐的 “Server-based email sending: **10/minute and max 100/day**”。“When sending emails through your hosting server’s built-in mail system using scripts (such as PHP mail(), PHPMailer…) there is a fixed limit of 10 emails per minute and up to 100 emails per day… the ability to send emails using this method will be temporarily disabled. The limit resets on a **rolling 24-hour basis**… we recommend… switching to SMTP.”
- Hostinger 教程 https://www.hostinger.com/in/tutorials/send-emails-using-php-mail/ （抓取 2026-10-09 06:57 UTC）：“limits for emails sent via PHP mail() are 100/day and 10/minute… **will be consumed immediately if there are queued emails**.”
- 《Parameters and limits of Hostinger Mail》 https://www.hostinger.com/support/4625828-parameters-and-limits-of-hostinger-email/ （抓取 2026-10-09 06:53 UTC）：Hostinger 邮箱经 SMTP 发信按**每个邮箱**单独计额：Business Starter 1000/天，Standard/Premium 3000/天；主机套餐附带的 1 年免费试用邮箱 100/天；均为滚动 24 小时。
- 文档没有说明“封”是按邮件计还是按收件人计。这一点会影响下面方案 A 的容量估算，属于未知项。

## 4. 根因一：配额耗尽（证据）

### 4.1 量
- 10-08 之前：任意 60 秒最多 6 次（08-17）；任意 24 小时最多 36 次。
- 10-08：197 次（15 点一个小时 103 次）；10-09：21 次（全是 digest 的重试）。
- 截至 18:07:37 的 24 小时窗口内：150 次尝试。

### 4.2 失败的形态与配额规则吻合
- 每分钟上限：所有 18:07 之前的可见失败都出现在 13–20 封/秒的突发尾部；之后孤立的 4 封组（15:38:49、15:41:05、15:44:19、15:46:11、15:47:28、16:13:41、16:20:00、17:09:31）全部成功。
- 24 小时上限：18:07:37 起失败率 100%（68/68），且跨过午夜依然失败，说明是滚动窗口而不是按自然日清零。
- 因此，185/187/194 票先后给出的“注册 POST 内 100% 失败”“请求内间歇性连接故障”“请求内不可靠、AS 内可靠”等解释，全部是**取样时恰好处在突发内或配额窗口内**造成的错觉。例如 18:19:07 的 REST 桥独立请求和 AS 请求同样失败。

### 4.3 回放验证
脚本 `scratchpad/simulate_limits.py`、`scratchpad/fit_limits.py` 用 mail.log 回放“每分钟 N 封 + 滚动 24 小时 M 封（只计已接受）”的规则，并与 16 个独立记录的结果（Woo 的 sent/failed、wp_mail_failed）比对：
- 9/分钟 + 105/24 小时：15/16 吻合，**准确复现 18:07:37 的分界**（VAT 副本被接受，New-customer 副本被拒）；
- 文档值 10/100 及其邻近取值：14/16。
- 剩下的偏差来自两点：克隆副本在 09-30 设计下失败是静默的，无法观测；每分钟计数的精确算法不公开。结论是：观测数据与文档限额在几封的误差内一致。

## 5. 当前机制本身造成的放大与丢失

| # | 问题 | 位置 | 证据 / 影响 |
|---|---|---|---|
| M1 | 每封业务通知拆成 4 封独立邮件（09-30 起是 phpmailer_init 克隆，10-08 起是 AS 任务） | `mail-identity.php` `tv_b2b_queue_business_mail_copies` / `tv_b2b_business_mail_copy_job` | 配额消耗 ×4；09-29 的 Bcc 形态只需 1 次 `mail()` |
| M2 | 副本载荷（含整封正文）写进 AS args，超过 8000 字符直接异常，AS 吞掉异常，只在 error_log 留一行 | 同上 | 4 张订单的 new_order 副本**从未入队**；所有 HTML 业务邮件的副本在结构上都无法送达；WC 日志里也没有这条记录 |
| M3 | 重试梯：主信最多 5 次重试（5/10/20/40/80 分钟，约 2.6 小时），副本 5 轮（约 1.3 小时）；之后只留一行日志 | `notifications.php` `tv_b2b_admin_mail_*`；`mail-identity.php` | 配额窗口是 24 小时，所以重试必然先耗尽；每次通知最多 21 次 `mail()`，并且会抢占刚释放的名额（Hostinger 原话 “consumed immediately if there are queued emails”）；AS 状态仍显示 complete，管理员看不到哪些邮件没送达 |
| M4 | Woo 事务邮件全站 defer 到 AS，但 Woo 自身失败不重试 | `notifications.php:169-181` | #6559/#6560/#6562/#6563 的 new_order + customer_on_hold 只尝试一次就丢了；defer 的前提（“请求内会坏”）已被证伪，它既不修复也不加重问题 |
| M5 | 每次下单都重新跑 VIES 并重发同一结论的 VAT 审核信 | `vat-service.php` `tv_b2b_order_vat_snapshot` → `tv_b2b_save_user_vat_state` → `tv_b2b_notify_admin_vat_failure` | 10-08 共 5 次 “VAT check needs review: DE1”，每次 4 封外加重试 |
| M6 | 在生产环境测试，收件人多为 `@example.test` | 184–194 票的验收流程 | 10-08 约 45 个逻辑通知 → 197 次 `mail()`；同时把同账号 sunriver 站点的发信也一起锁死 |
| M7 | 代码注释里写着已被证伪的因果（“in-request wp_mail fails while separate request succeeds”） | `notifications.php:36-42,162-178`；`mail-identity.php` 文件头 | 会把后续的修改引向错误方向 |

## 6. 已排除

- **From 变更**：18:07:03–18:07:37 有 6 封新 From 邮件被接受，随后失败；失败与 From 无关，只与累计量有关。
- **请求上下文**：Web POST、AS、REST 桥三种上下文的成败都只取决于当时的发送量。
- **WP-Cron / 缓存**：AS 逾期待执行为 0；副本任务比计划晚 4–8 分钟执行（流量驱动，正常）；页面缓存是关闭的。
- **去重 transient**：只合并完全相同的重复通知，没有吞掉不同的邮件。

## 7. DNS 与送达（对齐）

| 域名 | MX | SPF | DMARC | DKIM |
|---|---|---|---|---|
| de-linker.com（NS：hichina/阿里云） | mxbiz1/2.qq.com（腾讯企业邮） | `v=spf1 include:spf.mail.qq.com ~all` | 无记录 | 不知道 Exmail 的 selector；`hostingermail-a._domainkey` 没有记录 |
| sunriverinverter.com（NS：dns-parking=Hostinger） | mx1/mx2.hostinger.com | `v=spf1 include:_spf.mlsend.com include:_spf.mail.hostinger.com ~all`（→ relay.mail.hostinger.com 148.222.54.0/23、189.12.192.0/22；relay.mailchannels.net 23.83.208.0/20） | `v=DMARC1; p=none` | hostingermail-a/b/c CNAME 到 Hostinger |

（查询方式：`dig @1.1.1.1`，2026-10-09 06:47 UTC；本机默认 DNS 是代理的 198.18.0.2，不支持 TXT 查询，所以 187 票当时 dig 超时。）

- 现在的 From `sales@de-linker.com` 由 Hostinger 发出：de-linker.com 的 SPF 只授权腾讯，Hostinger 不会替它做 DKIM 签名，域上也没有 DMARC——**这样的邮件拿不到对齐的认证**。对于发给客户的邮件（欢迎信、订单信、发往 Gmail/M365 等邮箱），Gmail 的规定是：所有发件人都必须通过 SPF 或 DKIM，否则可能进垃圾箱或被 5.7.26 退回（https://support.google.com/mail/answer/81126 ，抓取 2026-10-09 07:08 UTC）。这是 194 改 From 带来的**送达退化**，但不是停发的原因。
- 旧 From `sales@sunriverinverter.com`：SPF 包含 Hostinger 中继，DMARC 是 p=none。如果本主机的出站中继属于这些网段（很可能，但没有收件头无法证实），旧 From 在 SPF 上反而是能通过的。sunriver 收件箱把这些信放进垃圾箱、09-29 的 Bcc 副本整封消失，更可能是 Hostinger 收件端对“自己托管的域名从外部进来”的处理，而不是 SPF 伪造判定。无论如何，用另一家公司的域名身份发信本身就不应该恢复。
- 10-08 17:09:32 #6556 的克隆副本：按回放推断，这几封被 Hostinger 接受了，但 857@ 和 chester@ 都没收到（据业主核查），sunriver 收在垃圾箱。这属于收件端的过滤或丢弃，与配额无关，现在也无法再查证（没有收件头）。

## 8. 恢复预测与不发信的验证方法

- 假设只有被接受的邮件计入额度（文档措辞是 “messages sent”）：05:48 UTC 起有约 4 个名额；13:58 UTC 约 13 个；**约 15:52 UTC（北京 23:52）起约 80 个**；18:08 UTC 完全恢复。
- 假设被拒的尝试也计入：约 15:52 UTC 之前 0 个名额，18:08 UTC 约 30 个，10-10 01:00 UTC 约 80 个。
- 不发测试信也能验证：等 10-10 01:00 UTC（北京 09:00）的 `tv_b2b_daily_digest`，到时读 `~/.logs/mail.log` 和 `wc-logs/tv-b2b-admin-mail-2026-10-10-*.log`。主信不报 `wp_mail_failed` 即为恢复。**如果仍然失败，就不是配额问题**（例如账号发信被风控冻结），需要向 Hostinger 查证。
- 在那之前，任何发信测试都会继续消耗或延长窗口。

## 9. 修复方案（排序）与需要删除的部分

### 必做（不管选哪种传输方式都要做；只改代码，不需要任何凭据）
1. **删掉** AS 副本任务 `tv_b2b_queue_business_mail_copies` / `tv_b2b_business_mail_copy_job`（M1、M2）。副本改为同一封邮件的收件人：`To: sales@` + `Bcc:` 副本箱 = 1 次 `mail()`；或者完全交给邮箱端转发（Exmail 规则，由 Linker 自己的企业邮管理员设置）。sunriver 副本是否还需要，属于业务路由问题，由业主决定。注意：09-29 唯一一次 Bcc 试验丢了 sunriver 副本，但当时的 From 正好是 sunriver 自己的地址，换了 From 之后结果未知。
2. **重写重试**（M3、M4）：一旦遇到拒收就停止突发；重试要覆盖 ≥24 小时（例如每小时一次，持续到 26 小时），并且重试不再连带副本。Woo 延迟发送的邮件也要纳入同一套重试（Woo 自己不重试）。更彻底的做法是用一个统一的发件队列：节流到 ≤8/分钟、≤80/24 小时（给同账号其他站点留余量），邮件留在队列里直到发出，并让管理员能看到“未送达”列表。
3. **VAT 审核信只在结论变化时发送**（M5）：一个规则、一个实现。
4. **生产环境禁止发信测试**：改用本地 QA（它本来就拦截外发）和 Woo 邮件预览；线上验收只读取自然发生的邮件日志（M6）。
5. 修正 `notifications.php` 和 `mail-identity.php` 中已被证伪的注释（M7）。全站 defer 不是修复手段，保留或回退到 Woo 默认都可以，只要注释如实说明即可。

### 传输方式（三选一）
- **A. 继续使用 Hostinger 内置 sendmail（完全在 Hostinger 内，不需要任何凭据）**：做完上面的“必做”就能恢复稳定发信。容量是滚动 24 小时 100 封、每分钟 10 封，**与同账号其他 3 个站点共享**：如果按邮件计数，约 80 次通知/天；如果按收件人计数（4 个收件人），约 20 次/天。缺点是 From @de-linker.com 的认证问题依旧存在；可在 de-linker.com 的 SPF 里加入 Hostinger 中继（需要阿里云 DNS 权限，也是 Linker 自己的；具体 include 要先用一封真实收件的邮件头核实出站 IP）。**这是“完全在 Hostinger 内、且不需要另一家公司凭据”的方案。**
- **B. Hostinger Email 邮箱 + SMTP（smtp.hostinger.com:465）**：在 hPanel 新建一个属于我们自己的邮箱，不需要 sunriver 的凭据。de-linker.com 的 MX 在腾讯，所以只能放在子域（例如 notify.de-linker.com），需要在阿里云 DNS 加 MX/SPF/DKIM；免费试用 100/天（按邮箱单独计，不占 sendmail 额度），Business Starter 为 1000/天（收费）。本套餐是否支持子域开通邮箱**尚未验证**。也在 Hostinger 内。
- **C. Linker 自有腾讯企业邮 SMTP（smtp.exmail.qq.com:465，SSL）**：SPF 已经授权腾讯，开启 Exmail DKIM 后 DMARC 对齐也能就绪；完全不占 Hostinger 的配额；不需要改 DNS。需要 Linker 的企业邮管理员在 WeCom 后台开通 SMTP，并生成客户端授权码（https://open.work.weixin.qq.com/help2/pc/19886 ，抓取 2026-10-09 07:04 UTC）。用的是 Linker 自己的凭据，不涉及另一家公司，但发信不在 Hostinger 内。从实现上看，WordPress 自带的 PHPMailer 加一个 `phpmailer_init` 设置就够了，不需要插件。
- 排除：用 `sales@sunriverinverter.com` 在 Hostinger 的邮箱走 SMTP——需要另一家公司的凭据，而且是借用别人的域名身份。

**结论**：认证 SMTP 是 Hostinger 官方针对这条限额给出的替代方案（C 或 B）。但它解决不了 M2、M3、M5：哪怕换成 SMTP，新订单副本照样排不进队列，重试照样会放弃。先做“必做”是最根本的。只用“必做 + A”就能恢复，代价是 100 封/天的共享上限和较弱的 From 认证。是否升级到 B 或 C，取决于谁能提供 DNS 权限（B）或 Exmail 授权码（C）。

## 10. 未知项及如何在不发信的前提下补齐

- 被拒的尝试是否计入 24 小时额度：看 §8 的 digest 观察点。
- 额度按邮件还是按收件人计：Hostinger 文档没写；可在 hPanel 的邮件/限额页面查看，或询问 Hostinger 支持。
- 本主机实际的出站中继 IP 和 envelope sender：从任何一封已收到的邮件的原始邮件头（Received/Return-Path）可以读到，例如 10-08 18:07:37 那封 VAT 副本。
- MTA 的拒收原文：PHP 8.3 不报告；切换到 PHP 8.5（主机上有 `/opt/alt/php85`）后会作为 E_WARNING 记录。这属于设置变更，本次没有做。
- 注意：如果 hsendmail 对 4xx 临时拒收返回 EX_TEMPFAIL(75)，PHP 会把它当作发送成功（真）。这种情况下“显示已发送、实际丢失”在日志里是看不到的。

## 11. 文件与数据位置

- 服务器：`~/.logs/mail.log`（PHP mail.log，账号级）、`~/.logs/error_log_de-linker_com`（371–374 行 args too long）、`public_html/wp-content/uploads/wc-logs/{transactional-emails-2026-10-08,tv-b2b-admin-mail-2026-10-08,tv-b2b-admin-mail-2026-10-09}-*.log`、`wp_actionscheduler_actions`（8689–8766）。
- 线上与链尖字节一致：`plugins/terravolt-b2b-core/includes/mail-identity.php`（11683 B）、`notifications.php`（39460 B）。
- 本地副本与脚本（scratchpad）：`live/mail.log`、`parse_maillog.py`、`simulate_limits.py`、`fit_limits.py`。
- 外部来源：上文各条链接，抓取日期均为 2026-10-09；另有 php.net `mail.configuration`、`function.mail`（抓取 2026-10-09 07:10 UTC），用于说明 mail.log 的含义、返回值语义以及 8.5 的 changelog。
