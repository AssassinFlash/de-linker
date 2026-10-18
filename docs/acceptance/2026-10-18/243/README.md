# #243 Genie · 让 Linker 联系我 · 验收记录（2026-10-18）

实例 g243（`just sync g243`，快照 2026-10-17 20:57 UTC；`just serve g243`：真实 Jev 经 OpenRouter `/api/v1/systemone`、deepseek-flash 经官方 API）。
规格：`docs/specs/13-genie.md` "转人工"一节。文案评审：`copy-review.md`。

## 1. 触发（EN/DE，真实服务）

`uv run python eval/contact/triggers.py http://127.0.0.1:9113 …` → **20/20**，原始记录 `eval/triggers-20261018.json`：

| 用例 | 结果 |
|---|---|
| "Can I talk to a person?"、"Ich möchte mit einem Mitarbeiter sprechen" | 短语表命中，`person` 路由，**不调 Jev、不调模型**（0.0 s），回答 = 服务的一句 + 联系卡 `asked` |
| "Could somebody from your sales team give me a ring tomorrow?"、"Gibt es bei Ihnen einen Ansprechpartner, der sich mit Gewerbespeichern auskennt?" | 短语表不中，Jev `talk_to_person` → `asked` |
| 不满一句 EN/DE（"This is useless, you keep giving me the wrong products." / "Das hilft mir überhaupt nicht weiter, Ihre Antworten sind falsch."） | Jev `wants_person` → 照常回答 + 联系卡 `dissatisfied` |
| 物流 EN/DE | 团队邮箱句 + 联系卡 `service` |
| 普通产品问题、"Can the SAJ inverter talk to a Pylontech battery?" / "Kann der Wechselrichter mit dem Speicher sprechen?" | 无卡 |
| 同一问题连问四轮（EN/DE，大小写、标点、连字符各不同） | 第 1、2 轮无卡，**第 3 轮 `repeat`**，第 4 轮无卡（不连续两次） |

单元与集成：`services/genie/tests/test_contact.py`（短语表正反例含否定句与跨句否定、31 对同问测定集、四种原因、"不连续两次 / 一个问题一次"、Jev 不可用时重复规则照常）、
`test_turn.py`（找人不跑模型、日志判连续、第三轮一次、另一会话不串）、`test_understand.py`（短语命中时 Jev 与 ability 都没被调用）。

## 2. 团队收到什么（Outbox 队列断言，真实实例）

`plugins/linker-commerce/tests/php/Integration/GenieContactTest.php` + `NotificationRoutingTest.php`，对 g243 连跑多次结果一致（各自保存并还原选项、计数行、会话、购物车与队列）：

- 访客请求 → **恰好一行**队列：To = `sales@sunriverinverter.com`（`notify_to()`）、Bcc = 设置的抄送、From = `Linker <sales@sunriverinverter.com>`、Reply-to = 访客地址；
  正文含后台整段对话链接（`admin.php?page=linker-genie-quality&conversation=<ID>`）、原因、最近消息（最新在前）、页面地址与标题、语言、
  Lösungsentwurf 的产品名、Item number 与数量、"within one business day"；**没有任何一封发往访客地址**；会话上写了一条交接记录。
- 已登录客户：GET 已返回账户地址（不问联系方式），发送不带地址，Reply-to = 账户姓名与账单地址，正文有"Open the customer"；GET 的 `mailbox` 是客户可见的团队邮箱，不是内部地址。
- 蜜罐 → 按已发送回答、零行；伪造或过早的起始时间 → 400、零行；同一连接第 4 次 → 429、只有 3 行；全站日上限已满 → 429、零行；
  同一请求两次 → 一行，GET 显示已发出；**十个进程同时抢一个连接的名额，恰好 3 个拿到**（原子计数，#235 的 `RateLimit`）。
- 路由表新增一行（默认与自定义内部发件人两种）。

本地 spool 实例（e2e 发出的四封）：`team-mail-guest.html`（To sunriver、Bcc chester@、From 内部、Reply-To 访客）。实例邮件只写本地 spool，不出本机。

## 3. 截图（`screens/`，`LINKER_E2E_SHOTS=… just e2e g243 specs/genie-contact.spec.ts`，8/8 通过）

产品页 SAJ H2-10K-T3（EN `/product/saj-h2-10k-t3/`，DE `/de/produkt/saj-h2-10k-t3/`），每例：问找人 → 卡 → 发送 → 发出态；1440 再问一个产品问题证明 Genie 照常回答。

| 状态 | 访客 | 已登录（857558227@qq.com） |
|---|---|---|
| 卡（EN/DE × 1440/390） | `{en,de}-{1440,390}-guest-offer.png`（只留邮箱） | `{en,de}-{1440,390}-signed-in-offer.png`（点名账户地址、无输入框） |
| 发出后 | `{en,de}-{1440,390}-guest-sent.png` | `{en,de}-{1440,390}-signed-in-sent.png` |
| 之后照常回答（1440） | `{en,de}-1440-guest-after.png` | `{en,de}-1440-signed-in-after.png` |

已登录截图顶部是 WordPress 管理条：测试账号在快照里是员工账号（ID 1）。卡与样式只在对话里出现，静止页面不变（mount 只多一个 `data-contact-url` 属性）。
