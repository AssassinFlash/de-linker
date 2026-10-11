# #68 文案对抗评审记录（搜索框芯片 / 联系表单 / 文档维护入口）

规则（AGENTS.md）：客户可见文案含 UI 字符串一律初稿 → 评审意见 → 定稿；EN 先行，DE
独立撰写不翻译；基准 = linker-copywriting Hard Stops + 线上既有措辞与 .po 术语。
德国 Sie 体（`de_DE_formal`）；禁 "不是…而是…"、三连排比等 AI 句式；不发明承诺
（一事一判：本次没有把 Proforma 链的 "one business day" 承诺搬到联系表单）。
定稿即 `.po` 的 msgstr 与代码里的 msgid（`plugins/linker-commerce`）。

评审为对抗式自查：先写 EN 初稿，再以 Hard Stops 与线上措辞逐条反驳，最后定稿；
DE 从语义重写（非逐词翻译）后同样反驳一遍。每条给"评审意见"的原话或要点。

## 1. 搜索框芯片 · 标签

- EN：复用既有定名 `Ask Genie`（#13 已评审、已在 .po）。无新串。
  评审：不改；与 dock 按钮同串，词典同源。
- DE：复用既有 `Genie fragen`（#13，已评审）。无新串。
  评审：不改；"Genie" 不连写（AGENTS §1）。

## 2. 联系表单 · 字段与按钮

| 位置 | EN 定稿 | DE 定稿 | 评审 |
|---|---|---|---|
| 问题区标签 | `Your question` | `Ihre Frage` | 与线上表单同词（`fieldLabels`/`lkc-question`），照用；DE "Ihre Frage" 与 .po 既有串一致。 |
| 姓名 | `Name` | `Name` | 线上同词。 |
| 公司（选填） | `Company` | `Unternehmen` | 线上同词；`optional` 小字 DE 用 `optional`（线上同词，德语商务惯用）。 |
| 回复邮箱 | `Reply email` | `E-Mail für die Antwort` | 线上同词（"E-Mail für die Antwort"），照用；不写 "E-Mail" 但明说用途。 |
| 同意勾选 | `I agree that my details may be used to respond to this message.` | `Ich bin damit einverstanden, dass meine Angaben zur Beantwortung dieser Nachricht verwendet werden.` | 线上句（"…zur Beantwortung dieser Anfrage…"）改一词 Anfrage→Nachricht，与本题"message"口径一致；DSGVO 语境保留 "verwendet werden"（不写 "verarbeitet"，避免超出实际处理范围）。 |
| 隐私链接 | `Privacy` | `Datenschutz` | 线上同词。 |
| 提交按钮 | `Send message` | `Nachricht senden` | 线上按钮是 `Send enquiry`/`Anfrage senden`；本表单不是询盘（询盘 = Proforma 链），评审意见：按钮沿用 "enquiry" 会让客户以为进了询盘流程，改 message/Nachricht；动词命令式 + Sie 体语境，DE "Nachricht senden" 直接。定稿：`Send message` / `Nachricht senden`。 |
| 按钮下小字 | `Your message goes to the Linker team. We reply to the address you give here.` | `Ihre Nachricht geht an das Linker-Team. Wir antworten an die Adresse, die Sie hier angeben.` | 初稿曾含 "We reply within one business day"——评审否：这是 Proforma 询盘的业主承诺（spec 11），联系表单未获此承诺裁定，删除。定稿只陈述路由与回复去向（谁答、答到哪个地址）。 |
| 蜜罐字段（屏读隐） | `Website` | `Website` | 线上同词；`aria-hidden` + `hidden` 属性，不影响客户。 |

## 3. 联系表单 · 状态消息

- EN 初稿（发送成功）：`Thank you. Your message is with the Linker team.`
  评审：不承诺时限（见上）；"is with …" 比 "has been sent" 少一层被动；与站上 §6 一句话转团队邮箱的口径一致。**定稿**同初稿。
- DE 初稿：`Vielen Dank. Ihre Nachricht liegt beim Linker-Team.`
  评审："liegt bei" 是常用商务表达（"liegt bei uns gut aufgehoben" 的短形），无被动堆叠；Sie 体。**定稿**同初稿。
- EN 校验失败：`Please check your entries and send the form again.`
  评审：与重定向回填状态一致（表单自身不保留字段输入，句里不声称"输入还在"——线上旧句 "Your draft is still here" 在本实现不成立，删）。**定稿**同初稿。
- DE 校验失败：`Bitte prüfen Sie Ihre Angaben und senden Sie das Formular erneut.`
  评审："Angaben" 是表单语境惯用词；两句祈使并列在德语表单里自然，非排比腔。**定稿**同初稿。
- EN 限流：`We received several messages from this connection. Please try again later or write to sales@de-linker.com.`
  评审：与线上旧限流句同义；给出邮箱出路（§2 允许的公司自有邮箱）；不暴露技术细节（IP、计数器）。**定稿**同初稿。
- DE 限流：`Von dieser Verbindung sind mehrere Nachrichten eingegangen. Bitte versuchen Sie es später erneut oder schreiben Sie an sales@de-linker.com.`
  评审："Verbindung" 在德语里可指网络连接，也指往来关系，均为中性；"eingegangen" 与收件动词一致。**定稿**同初稿。
- 字段级错误（服务端拒绝时映射到同一 `invalid` 状态，串用于日志/回执兜底）：
  - `Please add your name.` / `Bitte geben Sie Ihren Namen an.`
  - `Please add an email address we can reply to.` / `Bitte geben Sie eine E-Mail-Adresse an, an die wir antworten können.`
  - `Please write your message.` / `Bitte schreiben Sie Ihre Nachricht.`
  - `Please agree to the use of your details for the reply.` / `Bitte stimmen Sie der Verwendung Ihrer Angaben für die Antwort zu.`
  评审：均为请求 + 具体动作；DE 与线上 `errorCopy` 的句式（"Bitte geben Sie … an."）一致；不作 "invalid" 之类的断言。

## 4. 客户回执邮件（事务邮件；主题与正文同属公开面）

- EN 主题初稿：`We received your message`
  评审：线上回执主题是 "We received your inquiry"；本题口径为 message（第 2 节评审），主题随之。**定稿**同初稿。
- DE 主题初稿：`Wir haben Ihre Nachricht erhalten`
  评审：与线上 "Wir haben Ihre Anfrage erhalten" 同构，只换词；被动完成体是德语事务邮件惯例，非 AI 腔。**定稿**同初稿。
- EN 开头：`Hello {name},` — 与插件其他邮件共用串（`.po` 已审）。DE：`Hallo {name},`（.po 同串）。
- EN 正文：`Thank you for your message. The Linker team will reply to this address.`
  评审：与表单小字同一承诺口径；不用 "shortly"（时限）。**定稿**同初稿。
  DE：`Vielen Dank für Ihre Nachricht. Das Linker-Team antwortet an diese Adresse.`
- 回显：`Your message:` / `Ihre Nachricht:`（线上同词）。
- EN 结尾：`If anything is missing, reply to this email and it reaches the same team.`
  评审：给回信一个明确去处（回执的 Reply-to 是团队邮箱）；不用 "feel free to" 之类填充语。DE：`Falls etwas fehlt: Antworten Sie auf diese E-Mail, damit erreichen Sie dasselbe Team.`（冒号后命令句，德语邮件常见）。

## 5. 团队信（内部，同样逐条写）

- EN 主题：`New message from {name}` — 与 #11 `New inquiry #{order_number} from {company}` 同族；用 {name} 避免公司为空时出现 "from "（线上线的占位法）。DE：`Neue Nachricht von {name}`。
- EN 抬头（Heading）：`New message from the contact form` / DE：`Neue Nachricht über das Kontaktformular`。
- 正文首句 EN：`{name} ({company}) sent a message through the contact form.`（公司为空时占位 `no company given` / `kein Unternehmen angegeben`）
  评审：一句话给全身份 + 渠道；不用被动。DE：`{name} ({company}) hat eine Nachricht über das Kontaktformular gesendet.`
- 回复地址行：`Reply address: {email}` / `Antwortadresse: {email}`；语言行：`Written in: EN|DE` / `Geschrieben auf: EN|DE`
  评审：团队需要知道用哪种语言回复；"Written in"/"Geschrieben auf" 比 "Language:" 少一个名词堆叠。
- 结尾：`Answer this email to reply to the visitor directly.` / `Antworten Sie auf diese E-Mail, um dem Besucher direkt zu antworten.`
  评审：说明 Reply-to 已设为客户地址；德语 "dem Besucher"（表单访客）与站点口径一致。

## 6. 商品文档维护入口（后台 meta box，员工面）

- box 标题：`Documents` → `Unterlagen`（§3 定名：Documents / Unterlagen，账户端点同名）。
  评审：与产品页的附件区区分：产品页附件有 `msgctxt "product attachments"` 的 `Documents` = `Dokumente`（.po 既有），后台维护入口用无语境串 `Unterlagen`；两个德语词的分工记录在此。
- 说明句 1 EN：`The documents shown on the product page and used as citations: datasheets, manuals and warranty terms of our own media library.`
  评审：一句话说清三件事（前台可见、作为引用、来自我们自己的媒体库）；"warranty terms" 与数据里的 type `warranty` 对应。
  DE：`Die Unterlagen, die die Produktseite zeigt und die als Beleg dienen: Datenblätter, Handbücher und Garantiebedingungen aus unserer eigenen Mediathek.`（"Beleg" 对应 citation；"Mediathek" 是 WP 德语的媒体库词）。
- 说明句 2 EN：`The file itself is uploaded to the media library; the address here is the media file's URL. What a document may state is decided item by item — do not change a value or a claim without that confirmation.`
  评审：把业主裁定（我们托管、无来源链接）与"内容逐项确认"写成操作指令；破折号连接第二句，避免变成警告腔。
  DE：`Die Datei selbst liegt in der Mediathek; die Adresse hier ist die URL der Mediendatei. Was eine Unterlage aussagen darf, wird Punkt für Punkt entschieden – ändern Sie keinen Wert und keine Aussage ohne diese Bestätigung.`
- 列名：`Title`/`Titel`、`URL`/`URL`、`Type`/`Typ`、`Language`/`Sprache`、`Remove`/`Entfernen`。评审：与文档数据键（title/url/type/lang）一一对应；`Remove` 用动作词而非 `Delete`（删除发生在保存时，勾选只是标记）。

## 7. 数据集内文案（非客户可见，登记备查）

- Ability/端点描述（`A model or item number.`、`Item number.` 等）随 `wp i18n make-pot`
  进入目录；DE 译文按同样规则给出，但该面只服务 Genie 的工具 schema。
- 迁移脚本 `tools/migrate/68-contact-form.py` 的输出是工程日志，不进客户面。

## 未决（留给业主的事实问题，非本次交付）

- 无。第 2 节删掉的 "one business day" 是把已有承诺的适用范围收窄，不需要新裁定；
  若业主希望联系表单也承诺一个工作日回复，那是新事实，届时按单条文案走。
