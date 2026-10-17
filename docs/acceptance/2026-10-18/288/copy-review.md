# #288 文案评审

范围：本票不改客户邮件的主题、正文、From 名称、Reply-To 或客户页面；新增三条后台邮件设置文案，EN 先定稿，DE 独立撰写，Sie 体。既有 Sender email / Absenderadresse 保留。

## 初稿

- EN section: Mail delivery
- EN field: Return-Path
- EN help: Use a Hostinger-authorized address to keep emails out of spam.
- DE section: E-Mail-Zustellung
- DE field: Rücksendeadresse
- DE help: Wählen Sie eine von Hostinger autorisierte Adresse für die Zustellung Ihrer E-Mails.

## 对抗评审意见

1. “keep emails out of spam” 承诺超过代码能证明的结果：SPF 授权只是投递条件，最终归类需要 #288 生产实投。
2. Return-Path 是收件服务器写入的头，设置实际控制 PHPMailer Sender；标签用 Envelope sender，帮助文字说明投递与退信。
3. 新设置作用于全站，必须与 Internal notifications → Sender email 区分，也要说明不改变客户可见 From 与 Reply-To。
4. 德语“von Hostinger autorisiert”颠倒 SPF 授权关系；应是域的 SPF 授权 Hostinger。使用 Sie 指令，保留技术字段可辨认性。

## 定稿

| 项 | EN | DE |
|---|---|---|
| Section | Mail delivery | E-Mail-Zustellung |
| Field | Envelope sender | Envelope-Absender |
| Help | Used for delivery and bounces for all site emails. Choose an address whose domain authorizes Hostinger in its SPF record. The visible From and Reply-To stay unchanged. | Gilt für die Zustellung und Rückläufer aller Website-E-Mails. Wählen Sie eine Adresse, deren Domain Hostinger im SPF-Eintrag autorisiert. Die sichtbare Absenderadresse und die Antwortadresse bleiben unverändert. |

术语与事实核对：AGENTS.md §2/§3、#288 的 SPF 证据、现有 Woo 设置用词；无收件箱保证、无营销改写。POT 条目由 `wp i18n make-pot` 提取，PO 经 `msgmerge --no-fuzzy-matching` 更新后填写译文，`msgfmt --check` 编译。客户邮件不需要新文案或模板。
