# #221 文案记录：内部通知收件人

本票没有改任何客户可见文案（页面、Genie 回答、客户邮件的主题与正文都不动；客户可见的地址仍是 sales@de-linker.com，由 `NotificationRoutingTest` 断言）。改的只有后台文字：WooCommerce → Settings → Inquiries 的设置说明，以及 WooCommerce → Settings → Emails 列表里五封内部邮件的说明。它们只给员工看，仍按 AGENTS.md "只要是文案就要好好做"走一遍：EN 先定，DE 独立写（Sie 体，沿用 .po 既有术语），记录在此。

基准：.po 既有术语（Team-Postfach、Blindkopien、Proformarechnung、Tagesübersicht、Nachricht über das Kontaktformular、USt-IdNr.-Prüfung、Gesundheitsprüfung）；AGENTS.md §3 用词（不说 catalogue / article / cart）；不用"不是…而是…"和三连排比。

## 为什么要改

拆分之前，"Team mailbox" 一词同时指客户看到的地址和内部通知收件箱。拆开以后，设置页如果继续写"每封公司通知都发到团队邮箱"，就会把员工引到错误的字段；五封邮件的说明"Sent to the team mailbox"也会变成错话。

## 条目

| # | 位置 | 初稿 EN | 评审意见 | 定稿 EN | 定稿 DE |
|---|---|---|---|---|---|
| 1 | 设置页 · Team mailbox 节说明 | The address customers see: on the Proforma, on the pages and in Genie's answers. Internal notifications do not go here. | "on the pages"含糊，员工会问是哪些页面；客户看到的是网站 | The address customers see: on the Proforma, on the website and in Genie's answers. Internal notifications do not go here. | Die Adresse, die Kunden sehen: auf der Proformarechnung, auf der Website und in den Antworten von Genie. Interne Benachrichtigungen gehen nicht an diese Adresse. |
| 2 | 设置页 · 新节标题 | Internal notifications | 与五封邮件说明里的 "internal notification address" 同根，可互相找到 | Internal notifications | Interne Benachrichtigungen |
| 3 | 设置页 · 新节说明 | Every internal notification (new customer, VAT check, new inquiry, contact form message, daily digest, health check) is one message to this address, with a blind copy to each address below. | 六类要与 Woo 邮件列表里的名称对得上（New customer / VAT check changed / New inquiry / Contact form message / Daily digest）；健康告警不在 Woo 列表里，用告警主题里的 "health check" | 同初稿 | Jede interne Benachrichtigung (neuer Kunde, USt-IdNr.-Prüfung, neue Anfrage, Nachricht über das Kontaktformular, Tagesübersicht, Gesundheitsprüfung) ist eine Nachricht an diese Adresse, mit einer Blindkopie an jede Adresse unten. |
| 4 | 设置页 · 新字段 | Recipient | 节标题已说明是内部通知，字段名不重复 | Recipient | Empfänger |
| 5–9 | Woo 邮件列表 · 五封说明 | Sent to the internal notification address, with blind copies, when …（联系表单 / 每天 9:00 / 询盘 / 注册 / VIES 结论变化） | 只把"team mailbox"换成新名称，其余句子不动，员工已认得 | 同初稿 | Geht an die Adresse für interne Benachrichtigungen (mit Blindkopien), wenn …；摘要句为 "Geht jeden Morgen um 9:00 Uhr (Ortszeit Berlin) an die Adresse für interne Benachrichtigungen, mit Blindkopien." |

DE 第 5–9 条顺手统一成 "Geht an …"：原先联系表单与摘要两句是 "Wird … gesendet"，另外三句是 "Geht an …"，一个列表里两种句式。

## 不改的

- 字段 "Team mailbox"（EN/DE 不变）：它仍是同一个设置、同一个地址，只是不再收内部通知。
- "Blind copies" / "One address per line."：意思没变，移到新节下。
- 内部邮件的主题与正文：收件人变了，内容不变。
