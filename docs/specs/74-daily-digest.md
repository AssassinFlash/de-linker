# #74 每日摘要（四块业务仪表，空摘要照发）

## 是什么
每日 09:00（Europe/Berlin）给公司团队发一封 HTML 邮件（经 Outbox 队列，与业务邮件同重试语义）：当天待办的四块仪表。没有任何待办时照发（收不到摘要 = 管道故障信号）。第①块由 `Registration\PendingApprovals` 注册：只列 pending 的纯 customer（未显式记录状态也按 pending），标题显示数量；限制与拒绝不纳入新申请计数。第①块另有一行“Restricted, awaiting customer information: N”及 Accounts 页 status=restricted 链接，零也显示；限制账户的后续处理因此不被遗忘。逐项深链为 `admin.php?page=linker-accounts&focus=<用户ID>`，与后台队列及账号通知一致。

## 数字口径（写死，改动需改本节并同步测试）
全部窗口比较在 Unix 秒上进行（存储值本就是 UTC 纪元秒；时长比较与时区无关）。时区只出现在两处：发送时刻（09:00 Europe/Berlin，随夏令时 07:00/08:00 UTC）与邮件正文里的时间显示（Europe/Berlin，显式 `DateTimeZone('Europe/Berlin')`，不随站点"常规设置"里的时区走）。"超"一律是严格大于：恰好等于窗口边界（距今整 24 小时 / 整 72 小时）的**不**计入。

| 块 | 内容 | 窗口 | 起算点 |
|---|---|---|---|
| ① 待审批新账号 | 标题数量 + 公司名 + 注册时间 + 审核卡片深链 | pending 的纯 customer，注册时间从早到晚，无时间窗 | 注册时间仅作展示；无条目时显示 No account is waiting for approval. / Kein Konto wartet auf die Freigabe. |
| ② 未处理询盘 | 单号列表（编号、公司、创建时间、后台链接） | 创建时刻早于 发送时刻 − 86400 秒，且状态仍为 `wc-inquiry-received`，排除 `Protection\BusinessDisposition::processed()` 已验证的员工处置记录 | 询盘创建时刻（订单 `date_created`，进状态前的时间不算） |
| ③ PI 未响应 | 单号列表（编号、公司、签发时间、后台链接） | PI 签发时刻早于 发送时刻 − 259200 秒（3 天 = 72 小时，固定时长，非自然日），且状态仍为 `wc-proforma-issued` | PI 签发时刻（订单 meta `_linker_proforma_issued`，`Proforma/Issuer` 签发时写入的 Unix 秒）。处于 `wc-proforma-issued` 但没有该 meta 的（后台手工改状态绕过签发流程的）不计入：签发时刻未知 |
| ④ 邮件队列失败 | 封数 + 每封的收件人（Outbox 重试耗尽的消息） | 无时间窗：当前所有 `linker_mail_job` 草稿（`JobStore::FAILED_STATUS`）都算，直到有人处理 | 最近一次重试耗尽的时刻（消息保持草稿状态即视为未解决） |

待审账号的主题摘要、区块标题和正文数字统一读取 `PendingApprovals::pending_count()`；空提示和受限账号汇总仍显示，但不计入待审数。待开 PI 的处置排除必须通过现有原生读取器验证员工权限、私有订单审计、HMAC、订单归属和原始正文；标记存在本身、模型分类、未知或损坏证据均不足以排除，读取失败继续显示。原询盘状态、正文、审计、队列和容量不因摘要读取而改变。

发送时刻 = 本次 cron 触发的时刻。同一条数据在边界附近的两封摘要之间移动是预期行为。

## 内部认证健康（#297）

在原有四块之后固定加入 `Health\InternalMail`：读取最近 SMTP 结果，报告失败时间与固定分类，或最近一次成功时间；只配置而无发送记录时明确“尚无尝试”。缺配置仍显示未认证。SMTP 失败（含认证、连接和身份）时该封摘要立即走 PHP `mail()`；fallback 不覆盖 SMTP 失败，只有后续 SMTP 成功才更新最近结果。两通道都失败才排队重试，并在耗尽时进入失败邮件块。健康块只读、每封摘要只一个健康项、不另发邮件、不展示配置值；数据权威为 `Mail\SmtpOutcome`，传输、slot 与凭据契约见 spec 11。

## 发送与调度
- WP 原生 cron：`wp_schedule_single_event` 单次事件链——每次发送完成后把下一次排在"现在之后最近的 09:00 Europe/Berlin"；初始化时（init）无事件才补排。夏令时切换后的一次发送会按旧偏移落在 08:00 或 10:00，该次发送随即自校正；规则就是"每次发送重算下一次"。
- 收件人 = 内部通知收件人（To，`Options::notify_to()`，WooCommerce → Settings → Inquiries 的 Internal notifications → Recipient，缺省 `sales@sunriverinverter.com`）+ 抄送列表（Bcc，`notify_bcc()`，同节 Blind copies），与全部内部通知同源（`docs/specs/11-commerce.md` “内部通知收件人”，#221）。空摘要也发。
- 发送走 `wp_mail()`，由 Outbox 接管：当时可发就发，配额满或失败进队列，重试 1、5、30 分钟、2、6、12、24 小时，耗尽后消息留在队列标记失败——失败的摘要邮件自身会出现在下一封摘要的第④块里。同一柏林日的重叠 cron 消费者只准入一封普通摘要任务；原任务继续重试，不另建任务，也不占用关键通知预留。
- 手动触发：`wp cron event run linker_commerce_digest`。当天还没有摘要任务时会真发一封；已有任务只走原任务重试。生产上只在验收需要时用。
- 线上由 hPanel 每分钟 `wp cron event run --due-now` 跑（`DISABLE_WP_CRON`，spec 17），即 CLI PHP；主机的 `~/.logs/mail.log` 只记 Web PHP 的 `mail()`，CLI 的 `mail.log` 未设。所以摘要发没发**看 WooCommerce → Status → Logs 的 `linker-mail`**（Outbox 每次投递一行 info：主题、收件人、Bcc），不看 mail.log。
- 2026-10-17 查证（#221）：切换后摘要每天 07:00 UTC 都发了——Outbox 限速记录里有 2026-10-16 07:00:04 UTC 一次投递，cron 事件每天顺延；只是收件人是 `sales@de-linker.com`（老板的腾讯企业邮，Hostinger 发出的 `@de-linker.com` 邮件 SPF 不对齐，`docs/research/2026-10-09/mail-root-cause.md` §7），且 mail.log 不记。10-17 那次因临时止血（10-16 17:20 UTC 关掉）未发，符合预期。修法：改投内部通知收件人 + 投递日志。

## 给摘要加一块（#258 质检汇总等后续票的接入点）
实现 `Linker\Commerce\Digest\Block`（四个方法见下节），在自己的 Module 里 `add_filter( 'linker_commerce_digest_blocks', fn ( array $blocks ) => [ ...$blocks, new YourBlock() ] )`——**追加在末尾**（第①块待审账号由审批票放在最前，②③④的顺序不动）。`entries()` 每条一行：`label` 必填，`url` + `link_text` 给后台直达链接（可空），`detail` 给一句说明（可空）；没有条目时显示 `empty_text()`，块照样出现（空态也是信号）。块只读数据、不发信：收件人、语言、发送与重试都归 `DigestEmail`。测试照 `tests/php/Unit/Digest/BlocksTest.php` 断言顺序，照 `tests/php/Integration/DigestTest.php` 断言真实实例里那一块出现在摘要正文。

## 第①块插拔接口（账户审核接线）
`Linker\Commerce\Digest\Block` 接口（`id()/title()/entries()/empty_text()`，entry = `label + url + link_text + detail`），`Digest/Blocks` 按固定顺序装配内置的 ②③④与内部认证健康块，并应用过滤器 `linker_commerce_digest_blocks`（传 `list<Block>`，返回 `list<Block>`，非 Block 元素被剔除）。`Registration\Module` 将 `PendingApprovals` 放在最前；每条 entry 的 `url` 由 `Registration\AccountsAdmin::url( $user_id )` 生成，直达 `admin.php?page=linker-accounts&focus=<用户ID>` 审核卡片，`link_text` 沿用 Open the customer / Kunden öffnen。身份及状态口径由现有 `Registration\Approval` 负责；本块不另写审批状态机。已处理账户不计入待审；限制账户另列一行数量与后台独立区域链接，拒绝账户只在历史中保留。旧邮件里的深链仍可查看当前决定。

## 邮件
- WC_Email 子类（`Digest/DigestEmail`，继承团队通知基类），注册进 `woocommerce_email_classes`（后台 WooCommerce → Settings → Emails 可见可关）。语言 = 站点默认语言（团队邮件规则），HTML 单格式，正文模板 `templates/emails/linker-digest.php`。有条目的块各成一张卡片，条数在标题左边，打开链接用原文、不用按钮。没有条目的块收在最后一张安静的卡片里。样式类写在 `DigestEmail::presentation_css()`，经 `woocommerce_email_styles` 在发送时内联，模板本身不加 style 属性。外层仍沿用 WooCommerce 邮件头尾，只改这一封的底色和字号。已审过的标题、空态句和条目句子不改。邮件内的时间显示一律 Europe/Berlin；日期格式随邮件语言取（EN "October 11, 2026" / DE "11. Oktober 2026"），不取站点的 date_format 选项（快照站点该选项是中文格式，与邮件语言无关）。
- 主题/标题/各块标题与空态句是客户可见面之外的内部业务邮件文案，同样过文案对抗评审（记录 `docs/acceptance/<日期>/74/copy-review.md`）：EN 先行，DE 独立撰写非翻译，基准 = linker-copywriting Hard Stops（email subjects 属公开面）+ 既有 .po 术语（Anfrage / Proformarechnung / Anfrage eingegangen / Proformarechnung ausgestellt）。

## 不做
不建后台页面（第④块的排查入口是既有设置页顶部提示与 WooCommerce → Status → Logs）；不重发/不清理失败消息；第①块查询与审批状态机不在本票；不碰 LiveCanvas 模板与任何站点页面呈现。

## 验收
- [ ] 单元：调度时刻计算（09:00 Berlin 跨夏令时、边界前后）；三个查询的窗口边界（含恰好 24h/72h 不计入）；过滤器注册块顺序；主题与模板参数。
- [ ] 真实实例（`phpunit.integration.xml.dist`）：真实夹具下三块数字断言（跨日边界的 23h/25h/整 24h 与 71h/73h/整 72h 各一份）；空摘要路径（无夹具仍发出一封、三块各带空态句）；Outbox 发送路径（To=团队邮箱、头含 Bcc）与失败重试路径（模拟投递失败→重试→耗尽→消息成草稿→第④块在下一封摘要中列出它）。
- [ ] DE 渲染截图归档 `docs/acceptance/<日期>/74/`；文案定稿记录同目录。
