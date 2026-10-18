# #243 "让 Linker 联系我" · 文案对抗评审记录

规则：AGENTS.md §3 用词（Product / Lösungsentwurf；不说 catalogue / article / cart；Sie 体）、禁"不是…而是…"与三连排比；
linker-copywriting Hard Stops（事务邮件主题属公开面）；`.po` 既有术语（"We reply within one business day." →
"Wir antworten innerhalb eines Arbeitstags."；#234 评审：Arbeitstag，不用 Werktag）；EN 先定稿，DE 独立撰写。

评审方式：初稿由实现会话写（EN 先、DE 独立）；评审由一个独立的评审代理执行（只读，不改文件），对照上面的规则、
#234 与 #249 的评审先例、两个插件的 `de_DE_formal.po`，并读了显示这些文案的代码（`ContactCard.tsx`、`genie.css`、
`contact.py`、`ContactRequest.php`、`ContactGuard.php`、`QualityPage.php`、`Genie/ContactEmail.php`、邮件模板）。
定稿即代码里的 msgid（`plugins/linker-tools/src/genie/components/ContactCard.tsx`、`includes/Genie/{ContactRequest,QualityPage}.php`、
`plugins/linker-commerce/includes/Genie/ContactEmail.php`、`templates/emails/linker-genie-contact.php`）、两个 `.po`/JED 的 msgstr，
以及服务的 `contact.ANSWER`。

## 评审从代码里找出的三处（不只是措辞，本轮已改）

1. **日上限是全站的**：`ContactGuard::DAILY` 对整站计数，没发过请求的客户也会碰到；"later" 可能是第二天。→ 拒绝时给出客户可见的团队邮箱
   （见 B12）。实现：路由的 GET 返回 `mailbox`，取自 `linker_genie_team_mailbox` 过滤器，由 commerce 的 `Options::team_mailbox()` 回答
   （sales@de-linker.com；集成测试断言它不是内部地址）。**采纳**。
2. **团队邮件里的"摘要"其实是客户最近 5 条原话**：标题改为照实说（C7）。**采纳**。
3. **后台会话页的原因是未翻译的键**（"(dissatisfied)"）：改为翻译后的原因标签（D2）。**采纳**。

另两处非文案意见：
- 发出后的状态是新挂上的 `aria-live` 区，屏幕阅读器多半不播报 → 卡片整个生命周期是同一个 `aria-live="polite"` 区。**采纳**。
- 访客填错地址、发出后改不了（也没有回执信可暴露错误）→ 发出态照旧显示地址，客户能当场看到；要改就再向 Genie 要人，换了地址的请求会再发
  （同一地址才算重复）。**不另加"修改地址"**：多一个可重复发送的入口，正是限额要防的。

## 逐条

| # | 位置 | 初稿 EN / DE | 评审意见 | 定稿 EN / DE |
|---|---|---|---|---|
| A1 | 服务的一句（找人的整轮回答） | Yes, someone from the Linker team can get in touch with you. / Gern meldet sich jemand aus dem Linker-Team bei Ihnen. | "Yes" 对"call me back""Rückruf"这类命令句别扭；没说渠道，"meldet sich"读成电话；DE "Gern … meldet sich" 在客户发出之前就当事实许诺，"Gern" 像真人在说 | **Someone from the Linker team can get in touch with you by email.** / **Jemand aus dem Linker-Team kann sich per E-Mail bei Ihnen melden.** |
| B1 | 卡标题（找人、公司类） | Let the Linker team contact you / Lassen Sie sich vom Linker-Team kontaktieren | DE 被动生硬、45 字符，按钮里又一个 kontaktieren | EN 不变 / **Rückmeldung vom Linker-Team** |
| B2 | 卡标题（不满、重复） | Would you rather talk to a person? / Möchten Sie lieber mit einem Menschen sprechen? | "talk/sprechen" 许诺通话，实际是邮件；"rather/lieber" 像替换 Genie，与"Genie 照常回答"矛盾 | **Should someone from the Linker team get in touch?** / **Soll sich jemand aus dem Linker-Team bei Ihnen melden?** |
| B3 | 访客说明 | Leave your email address and the team replies within one business day. / Hinterlassen Sie …, und das Team antwortet innerhalb eines Arbeitstags. | DE "antwortet" 预设已有问题；三处统一一个动词 | EN 不变 / **Hinterlassen Sie Ihre E-Mail-Adresse, und das Team schreibt Ihnen innerhalb eines Arbeitstags.** |
| B4 | 已登录说明 | The team replies to %s within one business day. / Das Team antwortet innerhalb eines Arbeitstags an %s. | DE "antwortet an <地址>" 别扭，`.po` 用 "schreiben … an %s"；地址放句末便于 360px 折行 | EN 不变 / **Das Team schreibt Ihnen innerhalb eines Arbeitstags an %s.** |
| B5 | 地址字段（读屏标签） | Your email address / Ihre E-Mail-Adresse | 无（字段无占位，B3 必须紧贴其上——现状如此） | 不变 |
| B6 | 按钮 | Contact me / Kontaktieren Sie mich | DE 违反 `.po` 按钮用不定式的惯例（"Nachricht senden"、"Produkt anfragen"）；对公司用 Sie 祈使句怪 | EN 不变 / **Kontakt anfordern** |
| B7 | 发送中 | Sending… / Wird gesendet… | linker-tools `.po` 省略号前空格 | Sending… / **Wird gesendet …** |
| B8 | 发出后标题 | The Linker team has your request / Ihre Anfrage liegt beim Linker-Team | DE "Anfrage" 是询盘的保留词（"Anfrage eingegangen"、账户的"Anfragen"）；EN 对齐联系表单先例 | **Your request is with the Linker team** / **Ihre Kontaktanfrage liegt beim Linker-Team** |
| B9 | 发出后说明 | You will get a reply at %s within one business day. In the meantime, Genie is here for your other questions. / Sie erhalten … eine Antwort an %s. Bis dahin beantwortet Genie gern … | DE 主语与地址混；"is here for""gern"是安抚填充、让 AI 像人；"Bis dahin"暗示团队回复后 Genie 就停；重载数天后仍显示，现在时规则（与 B4 同句）更久为真；保留地址可见是对的（没有回执信） | **The team replies to %s within one business day.** + **Genie keeps answering your questions in the meantime.** / **Das Team schreibt Ihnen innerhalb eines Arbeitstags an %s.** + **Genie beantwortet Ihre Fragen in der Zwischenzeit weiter.** |
| B10 | 地址无效 | Please enter a valid email address. / Bitte geben Sie eine gültige E-Mail-Adresse ein. | 无 | 不变 |
| B11 | 起始时间无效 / 太快 | That did not work. Please try again. / Das hat nicht geklappt. … | "That"含糊；"geklappt"对正式 B2B 太口语；先例 "Die Anfrage ist fehlgeschlagen." | **Sending did not work. Please try again.** / **Das Senden ist fehlgeschlagen. Bitte versuchen Sie es erneut.** |
| B12 | 限额 | Genie cannot pass on more requests right now. Please try again later. / … keine weiteren Anfragen … | 死胡同（客户要的就是人）；全站上限时"more"是错的；联系表单的限额句给出邮箱；DE "Anfragen" 同 B8 | **Genie cannot pass on your request right now. Please try again later or write to %s.** / **Genie kann Ihre Kontaktanfrage gerade nicht weitergeben. Bitte versuchen Sie es später erneut oder schreiben Sie an %s.**（%s = 团队邮箱设置，不写死在 msgid 里；拿不到邮箱时用去掉"or write to"的同一句） |
| B13 | 暂不可用 | Genie cannot pass on your request just now. … | 与 B12 定稿逐字相同，合并成一个 msgid | 同 B12 |
| C1 | 团队邮件主题 | Genie: {customer} asks the team to get in touch / Genie: {customer} bittet das Team um Kontakt | 既有主题模式 "New inquiry #{n} from {company}"、"New customer: {company}"；"get in touch" 谁联系谁不清；与 C13、D1 同词 | **Contact request from {customer} via Genie** / **Kontaktanfrage von {customer} über Genie** |
| C2 | 邮件标题 | A customer asks the team to get in touch / Eine Kundin oder ein Kunde bittet … | 既有员工邮件用通称"Kunde"，初稿内部混用；标题模式 "New message from the contact form" | **New contact request via Genie** / **Neue Kontaktanfrage über Genie** |
| C3 | 邮件首句 | A customer asked Genie to pass the conversation to the team. Genie told them … | 不满与重复两种原因是 Genie 提议、客户接受，"asked Genie"不对；"pass the conversation"像实时转接 | **A contact request came in through Genie. Genie promised a reply within one business day.** / **Über Genie ist eine Kontaktanfrage eingegangen. Genie hat eine Antwort innerhalb eines Arbeitstags zugesagt.** |
| C4 | 行标签 | Why / Customer / Language / Page — Anlass / Kunde / Sprache / Seite | "Why" 作标签太口语，`.po` 已有 "Reason" → "Grund" | **Reason** / Customer / Language / Page — **Grund** / Kunde / Sprache / Seite |
| C5 | 原因 | Asked to talk to a person / A company, delivery or service question / Seemed unhappy with Genie's answers / Asked the same question three times | 不平行；"dissatisfied" 来自 Jev 的"找人或不满"，只说不满是夸大；重复只算连续 | Asked to talk to a person / **Asked about the company, delivery or service** / **Seemed frustrated or wanted a person** / **Asked the same question three times in a row** — Wollte mit einem Menschen sprechen / **Fragte nach Unternehmen, Lieferung oder Service** / **Wirkte unzufrieden oder wollte einen Menschen** / **Stellte dieselbe Frage dreimal hintereinander** |
| C6 | 访客 | Guest, no account / Gast, kein Konto | 无 | 不变 |
| C7 | 摘要标题 | Summary: what the customer wrote, latest first | 不是摘要，是最近 5 条原话；性别写法同 C2 | **The customer's last messages, newest first** / **Letzte Nachrichten des Kunden, neueste zuerst** |
| C8 | 全文链接 | Read the whole conversation / Ganzes Gespräch lesen | 后台用 "Unterhaltung"；员工链接模式 "Open the …" | **Open the conversation** / **Unterhaltung öffnen** |
| C9 | 草稿标题 | Solution draft / Lösungsentwurf | 无 | 不变 |
| C10 | 空草稿 | The solution draft is empty. | 复用既有 msgid | **No products in the solution draft.** / **Keine Produkte im Lösungsentwurf.**（既有） |
| C11 | 表头 | Product / SKU / Quantity | 站内用 "Item number" | Product / **Item number** / Quantity（既有译文） |
| C12 | 结尾 | Answer this email to reply to the customer directly. | DE "Antworten … antworten" 重复；陈述事实更干净（Reply-To 就是客户） | **A reply to this email goes straight to the customer.** / **Eine Antwort auf diese E-Mail geht direkt an den Kunden.** |
| C13 | Woo 邮件设置标题与说明 | Genie contact request / … when a customer asks Genie for the team's contact. | "the team's contact" 含糊；DE 先例把"(mit Blindkopien)"放括号 | Genie contact request / **… when a customer sends a contact request from Genie.** — Genie-Kontaktanfrage / **Geht an die Adresse für interne Benachrichtigungen (mit Blindkopien), wenn über Genie eine Kontaktanfrage eingeht.** |
| D1 | 后台会话页小节 | Contact requests / Kontaktanfragen | 无 | 不变 |
| D2 | 后台每条记录 | %1$s: reply to %2$s (%3$s) | **阻断**：%3$s 是原始键；"reply to"读作指令；既有术语 "Reply address"、"Reason" | **%1$s · Reply address: %2$s · Reason: %3$s** / **%1$s · Antwortadresse: %2$s · Grund: %3$s**（%3$s = 翻译后的 C5 标签，`ContactRequest::reason_label()`） |

## 贯穿意见与处理

1. DE "Anfrage" 与询盘相撞 → 本功能面向客户的 DE 一律 "Kontaktanfrage"（B8、B12、C1、C2、C3、C13、D1）。**采纳**。
2. 渠道从未说明，"talk / sprechen / meldet sich"暗示电话或实时聊天 → A1 说 "by email / per E-Mail"，B2 不用 talk 动词；B4、B9 点名地址。**采纳**。
3. 员工邮件性别写法混用 → 跟随既有员工邮件的通称"Kunde"，或改写成不用名词（C2、C3、C13）。**采纳**。
4. 错误不能是死胡同 → B12/B13 合并并给出可见邮箱（`%s` 取团队邮箱设置）。**采纳**。
5. DE 回复动词统一 "schreibt Ihnen … an %s"，地址句末。**采纳**。
6. 填充词与"像真人的 AI"（"Gern"、"is here for"、"Yes,"）→ 说 Genie 做什么："Genie keeps answering …"。**采纳**。
7. 不发回执信：定稿无任何回执承诺，卡就是确认。**确认**（另两条非文案意见见上）。
8. 省略号按所在插件的写法（linker-tools 在 "…" 前加空格）。**采纳**。
9. 规则核对：无"不是…而是…"，无 catalogue / article / cart；"Arbeitstags" 与业主句一致；唯一的三项并列是 C5 的
   "company, delivery or service"，是路由类别的事实列举，接受。
10. `contact.py` 注释里的 "one-working-day" 改为 "business day"。**采纳**。

另：评审指出短语表会对否定句（"I don't want to talk to a person"）误触发。**采纳**：`contact.asks_for_person` 只在短语所在分句里
没有否定词时命中（`_CLAUSE`、`_NEGATION`；正反例在 `tests/test_contact.py`），否定句照常交 Jev。

## 补记：#246 合并后（评审第 1 轮之二）

交接改走 #246 的联系记录，客户得到与联系表单一样的回执。新出现在 Genie 卡上的三句**全部沿用 #246 已评审的措辞与译文**，不另写：

| 位置 | EN / DE（沿用） | 来源 |
|---|---|---|
| 访客同意句（勾选框） | I agree that my details may be used to respond to this message. / Ich bin damit einverstanden, dass meine Angaben zur Beantwortung dieser Nachricht verwendet werden. | #246 询盘与联系表单 |
| 未勾选时的提示 | Please agree to the use of your details for the reply. / Bitte stimmen Sie der Verwendung Ihrer Angaben für die Antwort zu. | #246 `Submission` |
| 回执上限时（卡与历史里的卡） | We have not sent a confirmation email. / Es wurde keine Bestätigungs-E-Mail versendet. | #246 联系表单的 `sent_no_receipt` |

团队邮件改为 #246 的 `NewInquiryEmail`（主题"New inquiry #… from …"沿用），Genie 一节新增两句（内部邮件，按上文 C 组的定稿取词）：

| 位置 | EN / DE | 说明 |
|---|---|---|
| 小节标题 | Through Genie / Über Genie | 与 C 组"via Genie / über Genie"同一介词取向；作标题用名词短语 |
| 承诺句 | Genie promised a reply within one business day. / Genie hat eine Antwort innerhalb eines Arbeitstags zugesagt. | C3 定稿的第二句原样 |

C 组中随 `Genie\ContactEmail` 删除而不再使用的：C1、C2、C3 首句、C6、C12、C13（团队邮件的主题、标题、回复说明由 #246 的邮件给出）。其余（原因标签、"The customer's last messages, newest first"、"Open the conversation"、Lösungsentwurf 表头）沿用。
