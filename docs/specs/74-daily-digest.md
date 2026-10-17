# #74 每日摘要（四块业务仪表，空摘要照发）

## 是什么
每日 09:00（Europe/Berlin）给公司团队发一封 HTML 邮件（经 Outbox 队列，与业务邮件同重试语义）：当天待办的四块仪表。没有任何待办时照发（收不到摘要 = 管道故障信号）。第①块（待审批账号）的数据源在审批票（#73），本票交付可插拔接口，#73 落地后注册自己的块。

## 数字口径（写死，改动需改本节并同步测试）
全部窗口比较在 Unix 秒上进行（存储值本就是 UTC 纪元秒；时长比较与时区无关）。时区只出现在两处：发送时刻（09:00 Europe/Berlin，随夏令时 07:00/08:00 UTC）与邮件正文里的时间显示（Europe/Berlin，显式 `DateTimeZone('Europe/Berlin')`，不随站点"常规设置"里的时区走）。"超"一律是严格大于：恰好等于窗口边界（距今整 24 小时 / 整 72 小时）的**不**计入。

| 块 | 内容 | 窗口 | 起算点 |
|---|---|---|---|
| ① 待审批新账号 | 数量 + 公司名 + 注册时间 + 后台直达链接 | 审批票定义 | 审批票定义 |
| ② 未处理询盘 | 单号列表（编号、公司、创建时间、后台链接） | 创建时刻早于 发送时刻 − 86400 秒，且状态仍为 `wc-inquiry-received` | 询盘创建时刻（订单 `date_created`，进状态前的时间不算） |
| ③ PI 未响应 | 单号列表（编号、公司、签发时间、后台链接） | PI 签发时刻早于 发送时刻 − 259200 秒（3 天 = 72 小时，固定时长，非自然日），且状态仍为 `wc-proforma-issued` | PI 签发时刻（订单 meta `_linker_proforma_issued`，`Proforma/Issuer` 签发时写入的 Unix 秒）。处于 `wc-proforma-issued` 但没有该 meta 的（后台手工改状态绕过签发流程的）不计入：签发时刻未知 |
| ④ 邮件队列失败 | 封数 + 每封的收件人（Outbox 重试耗尽的消息） | 无时间窗：当前所有 `linker_mail_job` 草稿（`JobStore::FAILED_STATUS`）都算，直到有人处理 | 最近一次重试耗尽的时刻（消息保持草稿状态即视为未解决） |

发送时刻 = 本次 cron 触发的时刻。同一条数据在边界附近的两封摘要之间移动是预期行为。

## 发送与调度
- WP 原生 cron：`wp_schedule_single_event` 单次事件链——每次发送完成后把下一次排在"现在之后最近的 09:00 Europe/Berlin"；初始化时（init）无事件才补排。夏令时切换后的一次发送会按旧偏移落在 08:00 或 10:00，该次发送随即自校正；规则就是"每次发送重算下一次"。
- 收件人 = 内部通知收件人（To，`Options::notify_to()`，WooCommerce → Settings → Inquiries 的 Internal notifications → Recipient，缺省 `sales@sunriverinverter.com`）+ 抄送列表（Bcc，`notify_bcc()`，同节 Blind copies），与全部内部通知同源（`docs/specs/11-commerce.md` “内部通知收件人”，#221）。空摘要也发。
- 发送走 `wp_mail()`，由 Outbox 接管：当时可发就发，配额满或失败进队列，重试 1、5、30 分钟、2、6、12、24 小时，耗尽后消息留在队列标记失败——失败的摘要邮件自身会出现在下一封摘要的第④块里。
- 手动触发：`wp cron event run linker_commerce_digest`（会真发一封，生产上只在验收需要时用）。
- 线上由 hPanel 每分钟 `wp cron event run --due-now` 跑（`DISABLE_WP_CRON`，spec 17），即 CLI PHP；主机的 `~/.logs/mail.log` 只记 Web PHP 的 `mail()`，CLI 的 `mail.log` 未设。所以摘要发没发**看 WooCommerce → Status → Logs 的 `linker-mail`**（Outbox 每次投递一行 info：主题、收件人、Bcc），不看 mail.log。
- 2026-10-17 查证（#221）：切换后摘要每天 07:00 UTC 都发了——Outbox 限速记录里有 2026-10-16 07:00:04 UTC 一次投递，cron 事件每天顺延；只是收件人是 `sales@de-linker.com`（老板的腾讯企业邮，Hostinger 发出的 `@de-linker.com` 邮件 SPF 不对齐，`docs/research/2026-10-09/mail-root-cause.md` §7），且 mail.log 不记。10-17 那次因临时止血（10-16 17:20 UTC 关掉）未发，符合预期。修法：改投内部通知收件人 + 投递日志。

## 给摘要加一块（#258 质检汇总等后续票的接入点）
实现 `Linker\Commerce\Digest\Block`（四个方法见下节），在自己的 Module 里 `add_filter( 'linker_commerce_digest_blocks', fn ( array $blocks ) => [ ...$blocks, new YourBlock() ] )`——**追加在末尾**（第①块待审账号由审批票放在最前，②③④的顺序不动）。`entries()` 每条一行：`label` 必填，`url` + `link_text` 给后台直达链接（可空），`detail` 给一句说明（可空）；没有条目时显示 `empty_text()`，块照样出现（空态也是信号）。块只读数据、不发信：收件人、语言、发送与重试都归 `DigestEmail`。测试照 `tests/php/Unit/Digest/BlocksTest.php` 断言顺序，照 `tests/php/Integration/DigestTest.php` 断言真实实例里那一块出现在摘要正文。

## 第①块插拔接口（审批票对接点）
`Linker\Commerce\Digest\Block` 接口（`id()/title()/entries()/empty_text()`，entry = `label + url + link_text + detail`），`Digest/Blocks` 按固定顺序装配内置的 ②③④，并应用过滤器 `linker_commerce_digest_blocks`（传 `list<Block>`，返回 `list<Block>`，非 Block 元素被剔除）。审批票在自己的 Module 里 unshift 第①块：`add_filter( 'linker_commerce_digest_blocks', … )`；每条 entry 的 `url` 放用户资料页后台直达链接（`admin_url( 'user-edit.php?user_id=…' )` 形态）、`link_text` 放链接名（满足票面"后台直达链接"）。审批票落地前摘要只有三块；`#73` 的状态契约（用户元键）不存在于本票——对接时以审批票定义的元键为准，不在此预写。

## 邮件
- WC_Email 子类（`Digest/DigestEmail`，继承团队通知基类），注册进 `woocommerce_email_classes`（后台 WooCommerce → Settings → Emails 可见可关）。语言 = 站点默认语言（团队邮件规则），HTML 单格式，正文模板 `templates/emails/linker-digest.php`（语义标记，零内联样式，外层沿用 WooCommerce 邮件头尾）。邮件内的时间显示一律 Europe/Berlin；日期格式随邮件语言取（EN "October 11, 2026" / DE "11. Oktober 2026"），不取站点的 date_format 选项（快照站点该选项是中文格式，与邮件语言无关）。
- 主题/标题/各块标题与空态句是客户可见面之外的内部业务邮件文案，同样过文案对抗评审（记录 `docs/acceptance/<日期>/74/copy-review.md`）：EN 先行，DE 独立撰写非翻译，基准 = linker-copywriting Hard Stops（email subjects 属公开面）+ 既有 .po 术语（Anfrage / Proformarechnung / Anfrage eingegangen / Proformarechnung ausgestellt）。

## 不做
不建后台页面（第④块的排查入口是既有设置页顶部提示与 WooCommerce → Status → Logs）；不重发/不清理失败消息；第①块查询与审批状态机不在本票；不碰 LiveCanvas 模板与任何站点页面呈现。

## 验收
- [ ] 单元：调度时刻计算（09:00 Berlin 跨夏令时、边界前后）；三个查询的窗口边界（含恰好 24h/72h 不计入）；过滤器注册块顺序；主题与模板参数。
- [ ] 真实实例（`phpunit.integration.xml.dist`）：真实夹具下三块数字断言（跨日边界的 23h/25h/整 24h 与 71h/73h/整 72h 各一份）；空摘要路径（无夹具仍发出一封、三块各带空态句）；Outbox 发送路径（To=团队邮箱、头含 Bcc）与失败重试路径（模拟投递失败→重试→耗尽→消息成草稿→第④块在下一封摘要中列出它）。
- [ ] DE 渲染截图归档 `docs/acceptance/<日期>/74/`；文案定稿记录同目录。
