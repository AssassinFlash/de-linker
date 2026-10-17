# #235 会话保留文案对抗评审记录

规则：AGENTS.md §1 命名（"Genie, Linker's AI assistant" / "Genie, dem KI-Assistenten von Linker"，不写 "Linker Genie"）、
§3 用词与 Sie 体、禁 "不是…而是…" 与三连排比；linker-copywriting Hard Stops 1–9（邮件主题属公开面）；
目标 9 的 AI 标识与"可能出错"一句；现有 `.po` / JSON 术语（顾客面用 "Gespräch"、"Konto"、"Abbrechen"；
员工面用 "Unterhaltung"）。EN 先定稿，DE 独立撰写。

评审方式：初稿由实现会话写；评审由一个独立的评审代理执行（只读，不改文件），对照上面的规则、
`docs/specs/13-genie.md` 目标 7 与 9、联系表单回执邮件的先例（`linker-contact-receipt.php`），以及事实：
访客会话开始后 90 天清理、cookie 自最新会话起 90 天、登录全部并入账户、删除不可恢复、每连接每小时 3 封、
客户邮件的回复进团队邮箱。定稿即 `plugins/linker-tools/src/genie/**` 与
`plugins/linker-commerce/templates/emails/linker-genie-conversation.php` 的 msgid，
以及 `linker-tools-de_DE_formal-linker-tools-genie.json`、`linker-commerce-de_DE_formal.po` 的译文。

## 贯穿全稿的意见

1. **保留期措辞要按单个会话说**：服务端每个会话开始后 90 天清理，"Saved … for 90 days" 读成"从现在起全部 90 天"。
   天数用 `_n()` 并取自同一个常量（`Retention::RETENTION_DAYS`，经 `data-retention-days`）。**采纳**。
2. **"Sent" 说多了**：邮件经 Outbox，配额满时排队重试，200 只代表已交给发信链。→ "on its way / unterwegs"。**采纳**。
3. **限额数字不手写**：429 回执带回 `ConversationMail::LIMIT`，文案用 `%d`；"in an hour" 不准（滑动窗口）。**采纳**。
4. **访客可以填任何地址**：邮件第一句要说明它为什么到来（在哪个网站上请求的）。**采纳**；域名取 `home_url()` 的主机名
   （线上即 de-linker.com，本地截图显示 127.0.0.1）。是否允许发给任意地址属实现决定：与联系表单回执同一风险面、
   同一限额（每连接每小时 3 封），内容只是访客自己的对话。
5. **状态句式跟最近的兄弟句**：dock 里短状态是 "Not saved. Try again." → 删除失败用同一句式。**采纳**。

## 逐条

| # | 位置 | 初稿 | 评审意见 | 定稿 EN | 定稿 DE |
|---|---|---|---|---|---|
| 1 | 行删除标记 aria-label | Delete conversation: %s / Gespräch löschen: %s | 保留 | Delete conversation: %s | Gespräch löschen: %s |
| 2 | 行内确认 | Delete this conversation? / Dieses Gespräch löschen? | 删除不可恢复，登录客户是所有设备上都没了，用一个词说明 | **Delete this conversation permanently?** | **Dieses Gespräch endgültig löschen?** |
| 3 | 确认按钮 | Delete / Löschen | 保留 | Delete | Löschen |
| 4 | 取消 | Cancel / Abbrechen | 保留（目录术语） | Cancel | Abbrechen |
| 5 | 删除失败 | Not deleted. Please try again. / Nicht gelöscht. Bitte versuchen Sie es erneut. | 与 "Not saved. Try again." 同句式 | **Not deleted. Try again.** | **Nicht gelöscht. Bitte erneut versuchen.** |
| 6 | 访客列表下的说明 | Saved in this browser for %d days. When you sign in, they move to your account. / In diesem Browser %d Tage lang gespeichert. Sobald Sie sich anmelden, gehen sie in Ihr Konto über. | 不准（按会话开始计）；"they" 无先行词；"gehen … über" 别扭，目录用 "übernommen" | **Each conversation stays in this browser for %d days from its start. Signing in moves all of them to your account.**（`_n`，单数 "%d day"） | **Jedes Gespräch bleibt ab Beginn %d Tage in diesem Browser gespeichert. Wenn Sie sich anmelden, werden alle in Ihr Konto übernommen.**（单数 "%d Tag"） |
| 7 | 对话下的按钮 | Email this conversation / Gespräch per E-Mail senden | 登录客户一点就发，按钮要说明是发给自己；"senden" 读像发给别人 | **Email me this conversation** | **Gespräch per E-Mail erhalten** |
| 8 | 访客地址标签 | Your email address / Ihre E-Mail-Adresse | 保留 | Your email address | Ihre E-Mail-Adresse |
| 9 | 访客发送按钮 | Send email / E-Mail senden | 保留 | Send email | E-Mail senden |
| 10 | 发送中 | Sending… / Wird gesendet … | 保留（同 "Wird gespeichert …"） | Sending… | Wird gesendet … |
| 11 | 登录客户已发 | Sent to the email address of your account. | 冗长，客户无从核对是哪个地址；服务端知道地址，回执带回，与 12 合一 | （并入 12，显示账户地址） | （并入 12） |
| 12 | 已发 | Sent to %s. / An %s gesendet. | 200 只代表交给 Outbox | **Your email to %s is on its way.** | **Die E-Mail an %s ist unterwegs.** |
| 13 | 地址无效 | Please enter a valid email address. / Bitte geben Sie eine gültige E-Mail-Adresse ein. | 保留 | 同初稿 | 同初稿 |
| 14 | 超限 | Too many emails from this connection. Please try again in an hour. / Von dieser Verbindung wurden zu viele E-Mails gesendet. … | "in an hour" 不准；数字要来自常量；DE 在 400 px 折三行 | **This connection has reached the limit of %d emails per hour. Please try again later.** | **Über diese Verbindung wurde das Limit von %d E-Mails pro Stunde erreicht. Bitte versuchen Sie es später erneut.** |
| 15 | 其它失败 | The email could not be sent. Please try again. / Die E-Mail konnte nicht gesendet werden. Bitte versuchen Sie es erneut. | 保留（同询盘失败句） | 同初稿 | 同初稿 |
| 16 | 邮件主题与标题 | Your conversation with Genie / Ihr Gespräch mit Genie | 保留；不要把首条消息放进主题（访客写的字会进发往任意地址的主题） | Your conversation with Genie | Ihr Gespräch mit Genie |
| 17 | 邮件首句 | Here is your conversation with Genie, Linker's AI assistant. / Hier ist Ihr Gespräch mit Genie, dem KI-Assistenten von Linker. | 访客可填任意地址，邮件要说明来由 | **As requested on %s, here is your conversation with Genie, Linker's AI assistant.** | **Wie auf %s angefordert, erhalten Sie hier Ihr Gespräch mit Genie, dem KI-Assistenten von Linker.** |
| 18 | 说话人 | You / Genie · Sie / Genie | 保留 | You / Genie | Sie / Genie |
| 19 | AI 提示 | Genie is an AI system and its answers can contain mistakes. The datasheets on the product pages are the reference. / Genie ist ein KI-System, seine Antworten … | EN 第二句含糊，写明业主规则（与数据手册不一致时以手册为准）；DE 用 "und" 连接 | **Genie is an AI system, and its answers can contain mistakes. Where an answer differs from the product's datasheet, the datasheet applies.** | **Genie ist ein KI-System und seine Antworten können Fehler enthalten. Maßgeblich sind die Datenblätter auf den Produktseiten.** |
| 20 | 末句 | A reply to this email reaches the Linker team. / Eine Antwort auf diese E-Mail erreicht das Linker-Team. | EN 改得更自然；DE 同回执先例 | **Replies to this email go to the Linker team.** | Eine Antwort auf diese E-Mail erreicht das Linker-Team. |
| 21 | 员工面（Woo → 设置 → 电子邮件） | Genie conversation / Sent to a visitor who asks Genie to email them a conversation. · Genie-Gespräch / … | 访客不是"问 Genie"，是点按钮；登录客户也会收；员工面用 "Unterhaltung"，描述句式照目录 "Geht an …" | **Genie conversation / Sent when someone asks for a copy of a Genie conversation by email.** | **Genie-Unterhaltung / Geht an die Person, die eine Genie-Unterhaltung per E-Mail anfordert.** |

无其它违规：无光环词、无 "不是…而是…"、无三连排比、无 catalogue / article / cart、无 "Linker Genie"。

## 实测

定稿文案在 g235（快照 20261018-0252）上逐状态截图，见 `screens/`（`*-4-email-form`、`*-5-email-sent`、
`*-6-email-message`（EN/DE 邮件正文）、`*-9-delete-confirm`、`*-2-guest-three` 的说明句）。

## 第 2 轮（PR #296 评审第 1 轮之后：访客先确认地址、每日上限、确认链接结果）

新增文案同一流程：EN 先定，DE 独立撰写，独立评审代理（只读）对照同一套规则与第 1 轮记录。事实：访客的确认邮件
只含固定文案与一次性链接（不含对话），链接 24 小时内用一次；全站每天 10 封 Genie 邮件（确认与对话合计），超出拒绝、
不排队，次日（UTC 日窗口）恢复；点链接时超限则链接保留到过期。

贯穿意见（均**采纳**）：

1. 用 "email address / E-Mail-Adresse"，不用单独的 "address / Adresse"（本站 "Adresse" 也指 Proforma 的邮寄地址）。
2. 确认邮件保持最少：不放第 1 轮的 "Replies to this email go to the Linker team"（会招来不知情收件人的回复）、
   不放 AI 提示、不放任何对话文字；主题是固定字符串，不含访客输入。（实现即如此。）
3. 点链接时被每日上限拒绝，链接不作废（`ConversationMail::confirm()` 在上限检查通过后才删除待确认记录），
   所以 "Please try again tomorrow" 指向的链接次日仍可用（24 小时内）。
4. 经链接到达的界面（B、I、J）用 "the conversation"，不用 "your conversation"：点链接的人不一定是聊天的人。
5. 产品行的型号用目录既有 msgid "Model" / "Modell"，不新增字符串。

| # | 位置 | 初稿 | 评审意见 | 定稿 EN | 定稿 DE |
|---|---|---|---|---|---|
| A | 访客提交地址后的状态 | A confirmation link is on its way to %s. The conversation follows once the link is opened. / Ein Bestätigungslink ist unterwegs an %s. … | DE 语序别扭，照先例 "Die E-Mail an %s ist unterwegs." | A confirmation link is on its way to %s. The conversation follows once the link is opened. | **Ein Bestätigungslink an %s ist unterwegs.** Das Gespräch folgt, sobald der Link geöffnet wird. |
| B | 链接打开、对话已交出后的页面提示 | Address confirmed. Your conversation is on its way. / Adresse bestätigt. Ihr Gespräch ist unterwegs. | 意见 1、4 | **Email address confirmed. The conversation is on its way.** | **E-Mail-Adresse bestätigt. Das Gespräch ist unterwegs.** |
| C | 每日上限（状态行与链接提示） | Conversations cannot be emailed again until tomorrow. / Gespräche können erst morgen wieder per E-Mail gesendet werden. | "again" 预设读者已经发过，也没说下一步；与小时上限句同式 | **Today's email limit has been reached. Please try again tomorrow.** | **Das E-Mail-Limit für heute ist erreicht. Bitte versuchen Sie es morgen erneut.** |
| D | 链接过期或已用 | This link has expired or was already used. | EN 时态混用；DE 保留 | **This link has expired or has already been used.** | Dieser Link ist abgelaufen oder wurde bereits verwendet. |
| E | 员工面标题 | Genie address confirmation / Genie-Adressbestätigung | 加前缀，与 "Genie conversation" 在 Woo 列表里排在一起；员工面用 "Unterhaltung" | **Genie conversation: address confirmation** | **Genie-Unterhaltung: Adressbestätigung** |
| F | 员工面说明 | Sent when a visitor without an account asks … | 邮件发往填入的地址（未必是访客自己的）；说明里只有链接 | **Sent to the address a visitor without an account enters to get a Genie conversation by email. It holds only a link that confirms the address; the conversation follows after the click.** | **Geht an die Adresse, die ein Besucher ohne Konto für eine Genie-Unterhaltung per E-Mail angibt. Die E-Mail enthält nur einen Link zur Bestätigung; die Unterhaltung folgt nach dem Klick.** |
| G | 主题（公开面） | Confirm your address for your Genie conversation / Bestätigen Sie Ihre Adresse für Ihr Gespräch mit Genie | "your … conversation" 对没请求的人声称归属；"Confirm your address" 是常见钓鱼主题；改为说明来由的中性主题 | **Conversation with Genie requested for this email address** | **Gespräch mit Genie für diese E-Mail-Adresse angefordert** |
| H | 标题 | Confirm your address / Bestätigen Sie Ihre Adresse | 保留祈使（地址确是收件人的）；意见 1 | **Confirm your email address** | **Bestätigen Sie Ihre E-Mail-Adresse** |
| I | 首句（%s = 站点域名） | On %s, this address was given for a copy of a conversation with Genie, Linker's AI assistant. / Auf %s wurde diese Adresse angegeben, um eine Kopie eines Gesprächs … | 句子笨重，DE 属格链太重；照第 1 轮 "As requested on %s" 以站点开头 | **On %s, a conversation with Genie, Linker's AI assistant, was requested for this email address.** | **Auf %s wurde angefordert, ein Gespräch mit Genie, dem KI-Assistenten von Linker, an diese E-Mail-Adresse zu senden.** |
| J | 链接文字 | Send me the conversation / Gespräch zusenden | 保留 | Send me the conversation | Gespräch zusenden |
| K | 有效期（复数，%d = 24） | The link works once, for %d hour(s). / Der Link funktioniert einmal und %d Stunde(n) lang. | DE 读成"一次并且 24 小时"；两种语言都用"到期" | **The link works once and expires after %d hour. / …after %d hours.** | **Der Link lässt sich einmal verwenden und läuft nach %d Stunde ab. / …nach %d Stunden ab.** |
| L | 末句 | Without a click on the link, nothing more is sent to this address. / Ohne Klick auf den Link wird nichts weiter an diese Adresse gesendet. | 不严格为真（新请求可再发确认，在限额内）；确定的事实是对话只在点击后发送；给没请求的人一句安心的话（许可，不是任务，过 Hard Stop 9 Actor） | **The conversation is sent only once the link is opened. If you did not ask for it, you can ignore this email.** | **Das Gespräch wird erst gesendet, wenn der Link geöffnet wird. Falls Sie es nicht angefordert haben, können Sie diese E-Mail ignorieren.** |

无其它违规：无 Hard Stop、无 "不是…而是…"、无三连排比、无 catalogue / article / cart、无 "Linker Genie"。
实测截图：`screens/*-5-confirm-requested.png`、`*-6-confirm-message.png`、`*-7-link-opened.png`、`*-8-conversation-message.png`。
