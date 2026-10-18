# #250 "对话内询盘确认卡" · 文案对抗评审记录

规则：AGENTS.md §3 用词（Product / 产品分类 / Solution draft = Lösungsentwurf；不说 catalogue / article / cart；德语 Sie 体）；
禁"不是…而是…"、三连排比与"像真人的 AI"填充词；linker-copywriting Hard Stops；两个插件的 `de_DE_formal.po` 既有术语；
EN 先定稿，DE 独立撰写（不逐字翻译）。Statuses 的四个客户可见状态词按 AGENTS.md §3 固定：
Inquiry received / Anfrage eingegangen · Proforma invoice issued / Proformarechnung ausgestellt · Completed / Abgeschlossen · Cancelled / Storniert。

评审方式：初稿由实现会话写（EN 先、DE 独立）；随后由同一会话做一遍只读的对抗复核（没有独立评审代理可用——见文末"未做到的"），
对照上面的规则、#243 / #246 / #244 的评审先例与三个 `.po` 的既有译文，并读了显示这些文案的代码
（`InquiryCard.tsx`、`genie.css`、`InquiryRequest.php`、`InquirySummary.php`、`Sender.php`、`Genie/Module.php`）。
定稿即代码里的 msgid，两个 `.po` 的 msgstr 与 `just i18n-tools` 生成的 JED。

## 复核从代码与规则里找出的三处（本轮已改）

1. **限额句里的 "another" 是错的**（#243 评审 B12 的同一个问题）：`InquiryRequest::LIMIT` 是每条连接每小时 3 次，
   `DAILY` 是全站每天 10 次；撞上全站上限的客户可能一封都没发过，"another inquiry" 不成立。→ 去掉 "another"。
2. **空解决方案时 "Edit on the inquiry page" 读不通**：那里没有可编辑的行，链接是把人带到询盘页去补。
   → 统一为 "Open the inquiry page" / "Anfrageseite öffnen"（两种状态都成立）。
3. **两条几乎相同的失败句**（限额、暂不可用）在同一个卡上各出现一次，差别客户看不见。
   → 合并成一个 msgid：两种情况都把客户带到询盘页。

另：`limited` 与 `unavailable` 在代码里保留两个失败类型（限额可以等一下再试，暂不可用是站点这一侧的问题），
但客户读到的是同一句；这与 #243 把 B12/B13 合并的做法一致。

## 逐条

| # | 位置 | 初稿 EN / DE | 复核意见 | 定稿 EN / DE |
|---|---|---|---|---|
| A1 | 卡标题（可编辑态） | Your inquiry / Ihre Anfrage | 无；与状态词 "Inquiry received / Anfrage eingegangen" 同词根 | 不变 |
| A2 | 卡引言 | Check the details and send the inquiry to the Linker team. / Prüfen Sie die Angaben und senden Sie die Anfrage an das Linker-Team. | 无；"Angaben" 比 "Positionen" 覆盖商品、数量与留言 | 不变（复核前 DE 用 "Positionen"） |
| A3 | 行标题 | Products and quantities / Produkte und Mengen | 与询盘页右栏同义；客户核对的是"发什么、几件" | 不变 |
| A4 | 空解决方案 | No products in your solution draft. / Keine Produkte im Lösungsentwurf. | 既有 `No products in the solution draft.` 是团队邮件用语；对客户说 "your" 更直接。DE 与既有译一致 | 不变 |
| A5 | 留言框标签 | Message / Nachricht | 与询盘页的 `Message (optional)` 同词；卡上不写 "(optional)"，因为没有商品时留言是必需的 | 不变 |
| A6 | 摘要开关 | Attach the conversation summary / Zusammenfassung des Gesprächs anhängen | 无；"Gespräch" 与 #244 的团队邮件标题 "Conversation with Genie / Gespräch mit Genie" 一致 | 不变 |
| A7 | 摘要展开 | Read the summary / Zusammenfassung lesen | 无 | 不变 |
| A8 | 访客字段 | Name / Reply email / Company (optional) — Name / E-Mail für die Antwort / Unternehmen (optional) | 三处全部沿用询盘页（#246）已评审的标签，不另写 | 不变 |
| A9 | 同意句 | I agree that my details may be used to respond to this message. / Ich bin damit einverstanden, dass meine Angaben zur Beantwortung dieser Nachricht verwendet werden. | #246 既有句（#243 卡上也用）；已登录客户注册时已同意，卡上不显示 | 不变 |
| A10 | 发送按钮 | Send inquiry / Anfrage senden | 询盘页既有按钮；DE 不定式（`.po` 按钮惯例） | 不变 |
| A11 | 发送中 | Sending… / Wird gesendet … | linker-tools 的省略号前空格（#243 B7） | 不变 |
| A12 | 回复承诺 | We reply within one business day. / Wir antworten innerhalb eines Arbeitstags. | 既有句（#234 评审定 Arbeitstag） | 不变 |
| A13 | 去询盘页 | Edit on the inquiry page / Auf der Anfrageseite bearbeiten | 空解决方案时无可编辑；两种状态统一 | **Open the inquiry page / Anfrageseite öffnen** |
| A14 | 无内容提示 | Add a product to your solution draft or write a message. / Fügen Sie Ihrem Lösungsentwurf ein Produkt hinzu oder schreiben Sie eine Nachricht. | 无；两条路都存在（询盘页可只发留言） | 不变 |
| A15 | 数量 | × %d | 与询盘页、团队邮件 "× 2" 同一写法 | 不变 |
| B1 | 已发出标题 | Your inquiry is with the Linker team / Ihre Anfrage liegt beim Linker-Team | #243 B8 的句式；那里是 Kontaktanfrage，这里是询盘本身 | 不变 |
| B2 | 已发出状态行 | Inquiry #%1$s · %2$s / Anfrage Nr. %1$s · %2$s | 询盘号与状态都来自记录本身；DE 重复 "Anfrage" 是状态词固定用语的代价，接受 | 不变 |
| B3 | 已发出承诺 | The team replies within one business day. / Das Team schreibt Ihnen innerhalb eines Arbeitstags. | #243 B4 的定稿句（去掉地址）；DE 用 "schreibt … ", 不用 "antwortet" | 不变 |
| B4 | 无编号时 | Inquiry #%s / Anfrage Nr. %s | 兜底（订单号读不到时只显示编号）；正常不出现 | 不变 |
| B5 | 查看链接 | View your inquiry / Anfrage ansehen | linker-tools `.po` 既有 `ActionView` 句 | 不变 |
| B6 | 无回执 | We have not sent a confirmation email. / Es wurde keine Bestätigungs-E-Mail versendet. | #246 / #243 既有句（回执上限） | 不变 |
| B7 | Genie 照常 | Genie keeps answering your questions in the meantime. / Genie beantwortet Ihre Fragen in der Zwischenzeit weiter. | #243 既有句；不说 "is here for"（像真人） | 不变 |
| C1 | 缺姓名 | Please add your name. / Bitte geben Sie Ihren Namen an. | 询盘页 `Submission` 既有句 | 不变 |
| C2 | 缺地址 | Please add an email address we can reply to. / Bitte geben Sie eine E-Mail-Adresse an, an die wir antworten können. | 询盘页既有句 | 不变 |
| C3 | 未同意 | Please agree to the use of your details for the reply. / Bitte stimmen Sie der Verwendung Ihrer Angaben für die Antwort zu. | #246 / #243 既有句 | 不变 |
| C4 | 草稿变了 | Your solution draft changed. Check the lines and send the inquiry again. / Ihr Lösungsentwurf hat sich geändert. Prüfen Sie die Angaben und senden Sie die Anfrage erneut. | "lines" 与 A3 的 "Products and quantities" 对齐；不把变化说成错误 | 不变 |
| C5 | 空内容 | Add a product to your solution draft or write a message. / … | 与 A14 同一句（不另写） | 不变 |
| C6 | 限额 | Genie cannot send another inquiry right now. Please use the inquiry page. / Genie kann gerade keine weitere Anfrage senden. Bitte nutzen Sie die Anfrageseite. | "another" 在全站上限时错（复核发现 1）；给出去处，不做死胡同 | **Genie cannot send an inquiry right now. Please use the inquiry page. / Genie kann gerade keine Anfrage senden. Bitte nutzen Sie die Anfrageseite.** |
| C7 | 不可用 | Genie cannot send the inquiry right now. Please use the inquiry page. / Genie kann die Anfrage gerade nicht senden. Bitte nutzen Sie die Anfrageseite. | 与 C6 客户读不出区别，合并（复核发现 3） | **同 C6** |
| C8 | Woo 拒绝 | The inquiry could not be sent. Please check your solution draft on the inquiry page. / Die Anfrage konnte nicht gesendet werden. Prüfen Sie Ihren Lösungsentwurf auf der Anfrageseite. | 不说 "error"；指向能检查与补发的地方 | 不变 |
| C9 | 发送失败 | Sending did not work. Please try again, or use the inquiry page. / Das Senden ist fehlgeschlagen. Bitte versuchen Sie es erneut oder nutzen Sie die Anfrageseite. | #243 B11 的定稿句 + 去处；拿不到询盘页地址时退回 B11 原句（既有 msgid） | 不变 |
| D1 | 状态：已收到 | Inquiry received / Anfrage eingegangen | AGENTS.md §3 固定词；与团队邮件、账户页一致 | 不变 |
| D2 | 状态：Proforma | Proforma invoice issued / Proformarechnung ausgestellt | 同上 | 不变 |
| D3 | 状态：完成 | Completed / Abgeschlossen | 同上 | 不变 |
| D4 | 状态：取消 | Cancelled / Storniert | 同上 | 不变 |
| D5 | 状态：未发出 | Not sent / Nicht gesendet | Woo 的 pending 兜底（记录没有发出去）；照实说 | 不变 |

## 沿用（不在本票重写）

A8、A9、A10、A12、B5、B6、B7、C1、C2、C3 与 C9 的第二句是 #246 / #243 / #234 已评审的定稿 msgid；
本票只引用，不新增译文。状态的四词 D1–D4 取自 AGENTS.md §3 的固定表，DE 与 linker-commerce 的 `Statuses` 逐字一致
（linker-tools 的 JS 目录不能读 commerce 的 `.po`，所以这四句在 linker-tools `.po` 里各有一份同文译文——这是本票唯一的重复，
已在代码注释与这里写明原因）。

## 不属文案评审的部分

- 卡片里的留言与摘要正文是 #244 的模型输出（deepseek-flash，经服务 `/summary` 校验），不是本票写的文案；客户可改留言、可关摘要。
- 价格行是 WooCommerce 的 `get_price_html()`：已登录的合作伙伴看到净价，其余看到登录句（价格门 `Gating\PriceDisplay`），
  文案与产品页、询盘页同一实现；卡片只负责在卡的语言下取这一行（`InquiryRequest::draft()` 切到卡片语言）。
- 询盘号、状态来自订单记录，不写死。

## 未做到的

- **没有独立评审代理**：本会话内做了第二遍只读复核，但评审者与作者是同一会话。若业主/协调方要求独立代理的对抗评审，
  合并前应补一轮（只读，不改文件，对照本表与代码）。
- 卡片没有经过浏览器读屏实测；`aria-live="polite"` 的整卡结构沿用 #243 的做法，状态变化预期会被播报，但没有屏幕阅读器证据。
