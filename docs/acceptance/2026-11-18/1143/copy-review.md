# #1143 英德客户文案审校

原句以 `c2616abfe` 为准。页头、询盘、审批邮件以 `7892336de` 的差异为准，联系表单接续 `74f81b93d`。每处记录初稿、评审意见与定稿。评审由执行代理按 STSS 与 Linker 商业文案规则完成。

## 页头配置器

- **原句。** 英文桌面 `The Roof detail step adds the building's layout.`，移动 `The Roof detail step adds the layout.`。德文两处均为 `Der Schritt Dachdetails nimmt die Dachfläche auf.`
- **初稿。** EN `You can add a roof layout if needed.` / DE `Bei Bedarf können Sie die Dachfläche einzeichnen.`
- **评审。** 只说这个步骤做什么，客户仍不能判断没有屋顶图能否继续。配置器规格明确屋顶设计可选，桌面和移动入口都要给出同一事实。保留原来对整套方案和 Stückliste 的说明。
- **定稿。** 桌面和移动均采用初稿。

## 询盘确认页与客户回执邮件

- **原句。** EN `We reply within one business day.` + `The Linker team will reply to the email address you provided.` / DE `Wir antworten innerhalb eines Arbeitstags.` + `Das Linker-Team antwortet Ihnen an die angegebene E-Mail-Adresse.`
- **初稿。** EN `We reply within one business day to the address you entered.` / DE `Sie erhalten innerhalb eines Arbeitstags eine Antwort an die von Ihnen angegebene Adresse.`
- **评审。** `address` 和 `Adresse` 在商务链可指邮寄地址，应明确是电子邮箱。旧页面第二句在窄屏被隐藏。把时限和回复渠道放在同一条可见提示中，保留待审核和未寄回执时的专用提示。邮件也只说一次。
- **定稿。** EN `We reply within one business day to the email address you provided.` / DE `Sie erhalten innerhalb eines Arbeitstags eine Antwort an die angegebene E-Mail-Adresse.`

## 账户审批邮件

- **通过原句。** EN `Net prices are now shown with every product. Add the systems you need to your solution draft, and request the Proforma when the draft is ready.` / DE `Die Nettopreise werden jetzt zu jedem Produkt angezeigt. Legen Sie die benötigten Systeme in Ihren Lösungsentwurf und fordern Sie die Proformarechnung an, wenn er fertig ist.`
- **通过初稿。** EN `You can now see net prices where available. You can send your solution draft as an inquiry.` / DE `Sie sehen jetzt die verfügbaren Nettopreise. Ihren Lösungsentwurf können Sie als Anfrage senden.`
- **通过评审与定稿。** 按 `CommerceState::shows_price()` 保留价格可用范围。按 2026-11-08 报价裁定与询盘提交按钮说明客户下一步。初稿通过。
- **拒绝原句。** EN `We cannot approve your Linker partner account. Signing in therefore stays closed.` / DE `Wir können Ihr Partner-Konto bei Linker nicht freigeben. Die Anmeldung bleibt deshalb geschlossen.`
- **拒绝初稿。** EN `Your Linker partner account was not approved. You cannot sign in with this account.` / DE `Ihr Partner-Konto bei Linker wurde abgelehnt. Sie können sich mit diesem Konto nicht anmelden.`
- **拒绝评审与定稿。** 写清这次账户决定，以及该账户无法登录。保留审批人员给出的原因和 `sales@de-linker.com`。初稿通过。

## 联系表单

| 位置 | 原句 EN / DE | 初稿 EN / DE | 具体评审 | 定稿 EN / DE |
|---|---|---|---|---|
| 引言 | `Tell us what you need. We’ll use the email below for your reply.` / `Beschreiben Sie Ihr Anliegen. Für die Antwort verwenden wir die unten angegebene E-Mail-Adresse.` | `Tell us what you need.` / `Beschreiben Sie Ihr Anliegen.` | 引言引导客户填写问题。邮箱字段本身已说明输入内容。 | 同初稿 |
| 联系资料标题与邮箱字段 | `Where can we reply?`、`Reply email` / `Wohin dürfen wir antworten?`、`E-Mail für die Antwort` | `Your contact details`、`Email address` / `Ihre Kontaktdaten`、`E-Mail-Adresse` | 这一组还包含姓名和可选公司名。标题概括字段，标签说明格式。邮箱仍必填，关联标签与自动填充沿用原实现。 | 同初稿 |
| 按钮下方 | `Your message goes to the Linker team. We reply to the address you give here.` / `Ihre Nachricht geht an das Linker-Team. Wir antworten an die Adresse, die Sie hier angeben.` | `The Linker team replies within one business day.` / `Das Linker-Team antwortet innerhalb eines Arbeitstags.` | 客户在发送前需要知道由谁回复、何时回复。时限取现行业主约定，也已在 `includes/Contact/Form.php` 的 `sent_no_receipt` 和 `templates/emails/linker-inquiry-received.php` 的共用回执中可见。移除重复的回复地址说明，保留同意条款、免账号与免项目说明、失败后恢复提示。 | 同初稿 |

`FormTest`、`CheckoutTest`、`ApprovalTest` 与 `inquiry-states.spec.ts` 分别覆盖联系表单、询盘确认、审批邮件与客户确认页的文案。德语来自 `linker-commerce-de_DE_formal` 字典，页头两语直接来自对应 LiveCanvas 局部模板。
