# #67 健康告警邮件文案对抗评审记录

对象：服务健康告警邮件（主题 + 正文 + 失败原因行 + 服务名），发团队
（To 对接人 + Bcc，出 #11 的 Outbox 队列）。基准：linker-copywriting Hard
Stops（email subjects 属公开面）+ 既有邮件主题语料（"New inquiry #59 from
Solarbau Beispiel GmbH"、"New customer: Example Solar Installations Ltd"）
+ `linker-commerce-de_DE_formal.po` 术语。EN 先行；DE 独立撰写非翻译。
定稿即 `plugins/linker-commerce/includes/Health/Monitor.php` 里的字符串。

## 1. 主题 · EN

- 初稿：`Alert: the genie service failed its health check`
  评审：① "Alert:" 前缀不携带信息，只有 Alarmstimmung——既有主题语料全是
  直陈句（事件本身即告警）；② "genie" 处于句首位置小写，读作排版错误——
  助手定名是 Genie（AGENTS.md §1）；③ 备选 "The Genie service is not
  answering" 被否：失败不止"不应答"（还有 HTTP 非 200 与地址未配置两种，
  "failed its health check" 对三种都为真）。**定稿**：
  `The Genie service failed its health check`。

## 2. 正文 · EN

- 初稿：
  `The daily health check could not reach the genie service.` +
  `Address: … / Reason: … / Checked: … UTC` +
  `Genie uses this service. The check runs once a day and sends this message every time it fails.`
  评审：① "every time it fails" 的 it 指代不明——失败的是服务，不是检查；
  改 "on every failure"；② 服务名同主题改 Genie；③ "once a day" 是实现的
  真实事实（每日一次），不是编造时限，保留；④ Reason 行刻意携带原始传输
  错误（cURL error 7: …）：这是排障事实，运维语域，不润色；⑤ Hard Stops
  过线：无破折号、无强化词、无 homework、无排比。**定稿**（定稿字符串见
  Monitor.php `alert()`，运行样例 `docs/acceptance/2026-10-11/67/alert-en.eml`）：

  ```text
  The daily health check could not reach the Genie service.

  Address: {url}
  Reason: {reason}
  Checked: {Y-m-d H:i} UTC

  Genie uses this service. The check runs once a day and repeats this message on every failure.
  ```

## 3. 主题 · DE（独立撰写）

- 初稿：`Der Dienst Genie hat die Gesundheitsprüfung nicht bestanden`
  评审：① 德语运维邮件把事件放在最前；完整句把"失败"压到句尾，扫一眼
  抓不到；改事件前置的冒号形；② "Gesundheitsprüfung" 保留（不用英语借词
  "Health Check"，与 Woo 德语界面用德语复合词的口径一致）；③ "Dienst
  Genie" 同位无冠词，是德语运维头部的惯用形。**定稿**：
  `Gesundheitsprüfung fehlgeschlagen: Dienst Genie`（engine 同形）。

## 4. 正文 · DE（独立撰写）

- 初稿：
  `Die tägliche Gesundheitsprüfung hat den Dienst Genie nicht erreicht.` +
  `Adresse: … / Grund: … / Geprüft: … UTC` +
  `Genie nutzt diesen Dienst. Die Prüfung läuft einmal am Tag und wiederholt diese Nachricht bei jedem Fehlschlag.`
  评审：① "hat … nicht erreicht" 现在完成时自然，保留；② 收尾选
  "bei jedem Fehlschlag" 而非 "wenn der Dienst nicht antwortet"——Fehlschlag
  同样覆盖"地址未配置"这种服务谈不上"应答"的失败；③ "Engine" 按德语名词
  大写（EN 保留泛指小写 engine——两语各自成立，非逐词翻译）；④ 无 Sie 体
  诉求（邮件不直呼收件人），无 "nicht…sondern"、无三连排比；⑤ "Dienst"
  全文一致，不与 "Service" 混用。**定稿**（字符串见 Monitor.php）：

  ```text
  Die tägliche Gesundheitsprüfung hat den Dienst Genie nicht erreicht.

  Adresse: {url}
  Grund: {grund}
  Geprüft: {Y-m-d H:i} UTC

  Genie nutzt diesen Dienst. Die Prüfung läuft einmal am Tag und wiederholt diese Nachricht bei jedem Fehlschlag.
  ```

## 5. 服务名与原因行（两语）

- 服务名：EN `Genie` / `engine`；DE `Genie` / `Engine`（德语名词大写）。
- 用途行：EN `The Solution Configurator` / DE `Der Lösungskonfigurator`
  （AGENTS 定名，句首大写位）。
- 原因行：EN `the address option {option} is empty` /
  DE `die Adressoption {option} ist leer`；EN `the service answered HTTP {code}
  instead of 200` / DE `der Dienst antwortete mit HTTP {code} statt 200`。
  传输层错误（WP_Error 原文，如 cURL error 7）不翻译：那是栈的原始输出，
  保留原样才可对照排障。
- DE 全部进 `linker-commerce-de_DE_formal.po`（msgfmt 重建 .mo，过
  `msgfmt --check-format`）。

## 收尾

定稿字符串已回写 `Monitor.php` 并与本文一致；EN 实发样例
`alert-en.eml`（本地隔离截获，Outbox 队列路径），DE 渲染验证见本目录
`checks.json` 的 locale 一行。
