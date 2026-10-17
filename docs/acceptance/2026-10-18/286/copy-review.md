# #286 内部通知发件人 · 文案评审

范围：WooCommerce → Settings → Inquiries → Internal notifications 中新增字段的标题与说明。邮件主题、正文及客户页面没有新增文案。

依据：#286 的发件人决定、AGENTS.md §3 用词、既有 `.po` 的 Interne Benachrichtigungen / Absender / E-Mails 术语，以及 #221 文案记录。EN 先定稿；DE 根据字段用途独立撰写。评审检查：员工能否区分收件人与发件人、是否准确说明客户邮件的设置来源、是否虚构送达承诺、是否出现禁用措辞。

| 位置 | EN 初稿 | 对抗评审意见 | EN 定稿 |
|---|---|---|---|
| 字段标题 | Internal sender | 与节标题重复，也没有说明这里填邮箱地址。使用明确的地址字段名。 | Sender email |
| 字段说明 | Use this sender to keep team notifications out of spam. Customer emails are unchanged. | 不能保证垃圾邮件分类；应说明确切行为。写清固定名称 Linker 和客户邮件的设置来源，让员工能找到另一处设置。 | Internal notifications use this address with the sender name Linker. Customer emails use the WooCommerce sender settings. |

EN 定稿后，DE 独立稿：

| 位置 | DE 初稿 | 对抗评审意见 | DE 定稿 |
|---|---|---|---|
| 字段标题 | E-Mail-Absender | 可能被理解成显示名称。此处输入地址，使用 Absenderadresse。 | Absenderadresse |
| 字段说明 | Diese Adresse ist für interne Benachrichtigungen. E-Mails an Kunden werden wie bisher gesendet. | 明确表达发送用途；不要用“wie bisher”要求员工记得历史。说清发件人名和 WooCommerce 设置，避免宣称进入收件箱。 | Interne Benachrichtigungen werden mit dieser Adresse und dem Absendernamen Linker gesendet. Für E-Mails an Kunden gelten die Absendereinstellungen von WooCommerce. |

两种语言均无虚构送达承诺、禁用产品用词、三连排比或“不是…而是…”句式。DE 不需要直接称呼员工；没有 du 体。默认值 `sales@sunriverinverter.com` 来自 #286，不是文案推断。

定稿写入 `SettingsTab.php`、POT、`de_DE_formal.po` 和编译后的 MO。此记录为实现会话自评；Claude 的独立实现评审在 PR 进行。
