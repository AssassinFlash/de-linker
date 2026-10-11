# #74 每日摘要文案对抗评审记录

规则：内部业务邮件同过对抗评审（客户可见面门槛，email subjects 属公开面）。
基准：linker-copywriting Hard Stops + 本插件既有 .po 术语（Anfrage、
Proformarechnung、Anfrage öffnen、Proformarechnung ausgestellt）+ 既有管理
界面措辞（设置页顶部通知 "%d emails could not be delivered"）。EN 先行；
DE 独立撰写非翻译（Sie 体适用于对读者说话处——本邮件无第二人称句）。每处：
初稿 → 评审意见 → 定稿。定稿即 `includes/Digest/` 与
`languages/linker-commerce-de_DE_formal.po` 里的字面量。

## 1. 邮件标题与主题（设置页 title、邮件 heading、subject）

- EN 初稿：title/heading `Daily digest`，subject `Daily digest, {date}`。
  评审：subject 属公开面，一秒可读 ✓；"Daily digest" 自报家门 + 日期供归档
  检索 ✓；无承诺、无 borrowed credibility ✓。备选 "Linker daily digest"
  否——既有公司通知（"New inquiry #…"）主题不带品牌前缀，保持一致；逗号
  同位语比 "for" 短。`{date}` 的格式随邮件语言取（EN "October 11, 2026"、
  DE "11. Oktober 2026"），不取站点 date_format 选项——实测快照站点该选项
  为中文格式（"2026年10月11日"），与邮件语言无关，属旧配置遗留。**定稿**：
  同初稿。
- DE 初稿（独立写）：`Tagesübersicht`，subject `Tagesübersicht, {date}`。
  评审：Tagesübersicht 是德语业务惯用语（否掉 Tägliche Zusammenfassung 的
  直译腔与 Tagesdigest 的英借词）；逗号同位语在德语主题里同样成立。**
  定稿**：同初稿。
- 描述（设置页）EN 初稿：`Sent to the team mailbox, with blind copies,
  every morning at 9:00 (Berlin time).`。评审：说清对象、副本、时刻、时区，
  无过诺（"every morning" 与每日 cron 一致）。**定稿**：同初稿。
- 描述 DE 初稿：`Wird jeden Morgen um 9:00 Uhr (Ortszeit Berlin) an das
  Postfach des Teams gesendet, mit Blindkopien.`。评审：Ortszeit Berlin 是
  标准说法；"Postfach des Teams" 与设置页既有措辞（team mailbox→团队
  邮箱）同义；句式为状态句非被动直译。**定稿**：同初稿。

## 2. 第②块：未处理询盘

- EN 初稿：title `Inquiries waiting for a Proforma invoice`。评审：块名
  说状态不说判断（否 "Overdue inquiries"——逾期与否由空态句的窗口说）；
  waiting 的主语是询盘不是人，无作业派发 ✓。备选 "without a Proforma
  invoice" 读作缺陷清单，弃。**定稿**：同初稿。
- EN 空态初稿：`No inquiry is waiting for more than 24 hours.`。评审：与
  窗口严格对应（超 24h 才列出）；备选 "All inquiries were handled within
  24 hours" 是过诺（23 小时龄的询盘并未 handled），弃。**定稿**：同初稿。
- EN 条目初稿：label `Inquiry #%1$s – %2$s`，detail `Received on %1$s at
  %2$s (%3$s)`，链接沿用既有串 `Open the inquiry`（与询盘通知邮件同串同译
  "Anfrage öffnen"）。评审：en dash 列表内扫描清晰；age 括号是扫描辅助。
  **定稿**：同初稿。
- DE 初稿（独立写）：title `Anfragen ohne Proformarechnung`；空态 `Keine
  Anfrage wartet länger als 24 Stunden.`；label `Anfrage #%1$s – %2$s`；
  detail `Eingegangen am %1$s um %2$s Uhr (%3$s)`。评审：块名用锁定术语
  Proformarechnung、结构直说"有/无"；德语空态用现在时 warten，无
  werden-Futur 冗余；detail 用 am…um…Uhr 的德语时间语序，非英译序。**
  定稿**：同初稿。

## 3. 第③块：PI 未响应

- EN 初稿：title `Proforma invoices without a reply`；空态 `No Proforma
  invoice has waited more than 3 days for a reply.`；detail `Proforma
  invoice %1$s issued on %2$s at %3$s (%4$s)`。评审：块名与条目同构（条目
  就是一张无回复的 PI）；现在完成时读作"至今"，与窗口方向一致；备选
  "Every Proforma invoice was answered within 3 days" 过诺，弃。**定稿**：
  同初稿。
- DE 初稿（独立写）：title `Proformarechnungen ohne Antwort`；空态 `Keine
  Proformarechnung wartet länger als 3 Tage auf eine Antwort.`；detail
  `Proformarechnung %1$s ausgestellt am %2$s um %3$s Uhr (%4$s)`。评审：
  ausgestellt 与状态名 "Proformarechnung ausgestellt" 同词根（术语一致）；
  两块标题共享 "ohne X" 框架是刻意同构（便于扫读），非三连排比。**定稿**：
  同初稿。

## 4. 第④块：邮件队列失败

- EN 初稿：title `Emails that could not be delivered`。评审：与设置页既有
  通知 "%d email could not be delivered" 同源措辞（一个事实一处说法）；
  备选 "Undelivered emails" 更短但歧义（退信？垃圾箱？），弃。**定稿**：
  同初稿。
- EN 空态初稿：`No email failed to send.`。评审：重试中的消息尚未"失败"，
  本句只说重试耗尽者——准确；备选 "All emails were delivered" 过诺（
  队列里可有等待重试者），弃。**定稿**：同初稿。
- EN 条目初稿：label=失败消息的 subject；detail `To: %1$s – Error: %2$s`。
  评审：收件人是"谁没收到"，错误是 PHPMailer 诊断（机器输出，保持原文不
  翻）。**定稿**：同初稿。
- DE 初稿（独立写）：title `Nicht zugestellte E-Mails`；空态 `Es liegen
  keine fehlgeschlagenen E-Mails vor.`；detail `Empfänger: %1$s – Fehler:
  %2$s`。评审：title 用 zustellen（投递）非 senden（发送）——德语里投递
  才是结果；空态用状态句 "liegen vor"（在案），精确且正式。**定稿**：
  同初稿。

## 5. 年龄（age）串

- EN 初稿：`%d hour ago / %d hours ago`、`%d day ago / %d days ago`（_n）。
  规则：<48 小时以小时计，自此以整天计（47 小时 59 分 = "47 hours ago"，
  48 小时 = "2 days ago"）。评审：_n 覆盖单复数；无 "over/under" 修饰。**
  定稿**：同初稿。
- DE 初稿（独立写）：`vor %d Stunde / vor %d Stunden`、`vor %d Tag /
  vor %d Tagen`。评审：德语 vor + Dativ，复数形式 Tagen 由 _n 两个格给出；
  否掉直译 "hours ago" 式的 "vor %d Stunden her"（her 冗余）。**定稿**：
  同初稿。

## Hard Stops 检查单（公开面 = subject；全件核）

- [x] 无 borrowed credibility / proof-inventory
- [x] 无防御性否认、无 reassurance intensifiers
- [x] 无 invented logistics / 假计时器（age 数字来自真实窗口计算）
- [x] 无 helpdesk initiation、无作业派发（邮件无第二人称句）
- [x] 公开面（subject）一秒可读、纯 B2B 英语
- [x] 无 "From X to Y" / "One X. One Y." / "Instead of" 句式
- [x] 术语锁：Anfrage / Proformarechnung / Anfrage öffnen /
      Proformarechnung ausgestellt 与既有 .po 一致

## 验证

- msgid 提取：`wp i18n make-pot`（15 条新串入 pot，Daily digest 一串两用）；
  新串直接填入 de_DE_formal.po（首选拉取/合并通道会重排整库，实测弃用）；
  msgfmt --check 生成 .mo（369 条译串，新增 45 条 Abilities schema 串按
  既有状态留 EN——面向模型的后台描述，非客户面）。
- 渲染证据：EN/DE × 空/满 四张渲染邮件截图见同目录（digest-empty-en.png、
  digest-empty-de.png、digest-filled-en.png、digest-filled-de.png，1440 宽，
  chromium 实渲染；DE 满载图含"Anfragen ohne Proformarechnung /
  Proformarechnungen ohne Antwort / Nicht zugestellte E-Mails"三块与
  "vor 26 Stunden / vor 3 Tagen" 年龄句，PHPMailer 错误文本保持英文原样——
  机器输出非文案）。
