# #246 询盘文案记录

依据：AGENTS.md §2（2026-10-17 询盘开放裁定）、§3 术语、已选原型 B/C，以及线上商务表单。新增客户文案的 EN 初稿先确定语义，DE 独立以 Sie 体撰写；既有的姓名、回复邮箱、隐私同意与一个工作日回复承诺沿用已评审词条。

## 初稿与修订

| 位置 | EN 初稿 | 评审意见 | EN 定稿 | DE 定稿 |
|---|---|---|---|---|
| 标题、按钮 | Request Proforma | 访客也可以只留言；按钮应准确说明当前动作 | Send an inquiry / Send inquiry | Anfrage senden |
| 说明 | Tell us what you need. The products in your solution draft will be included. | 说明产品随信附上，不引导客户填写地址 | 同初稿 | Teilen Sie uns Ihr Anliegen mit. Die Produkte aus Ihrem Lösungsentwurf werden mitgesendet. |
| 开放留言 | Notes | 业主明确叫留言，且可选 | Message (optional) | Nachricht (optional) |
| 资料摘要 | Company details | 此步只需回复资料，公司非必填 | Your reply details / Change | Ihre Kontaktdaten / Ändern |
| 公司 | Company | 选填必须直接标出 | Company (optional) | Unternehmen (optional) |
| 访客说明 | No account needed. | 符合业主裁定，不顺带注册 | 同初稿 | Kein Konto erforderlich. |
| 登录提示 | Already a partner? Log in for net prices and saved details. | 待审和限制账号看不到净价，不能把登录当成价格解锁条件 | Have an approved account? Log in for net prices and saved details. | Sie haben bereits ein freigegebenes Partnerkonto? Melden Sie sich an, um Nettopreise zu sehen und Ihre gespeicherten Angaben zu verwenden. |
| 草稿 | Solution draft / Edit solution draft / Update solution draft | 沿用站内术语；数量 0 按 Woo 原生规则移除该行 | 同初稿 | Lösungsentwurf / Lösungsentwurf bearbeiten / Lösungsentwurf aktualisieren |
| 空草稿 | You can send a message without products. | 不把没有产品当成错误，留言仍能提交 | 同初稿 | Sie können uns auch ohne Produkte eine Nachricht senden. |
| 空提交错误 | Please add a product or write a message. | 只有产品和留言都没有才拦，保留其余输入 | 同初稿 | Bitte fügen Sie ein Produkt hinzu oder schreiben Sie eine Nachricht. |
| 发送失败 | Please try sending your inquiry again. | 不假称发送成功 | 同初稿 | Bitte senden Sie Ihre Anfrage erneut. |
| 无价草稿引导 | Log in and request a Proforma | 登录不再是发送的前提，价格审批条件单独写清楚 | You can send this solution draft without an account. Net prices are available after account approval. | Sie können diesen Lösungsentwurf ohne Konto senden. Nettopreise sehen Sie nach der Freigabe Ihres Kontos. |
| 草稿空态说明 | Browse the products now. Adding to the solution draft is possible only after your account has been reviewed. | 后一句已不符合实际机制 | Browse products and add them to your solution draft. You can send an inquiry without an account. | Wählen Sie Produkte für Ihren Lösungsentwurf aus. Sie können Ihre Anfrage ohne Konto senden. |
| 感谢页和回执 | Your Proforma invoice will be in your account… | 联系留言与访客询盘没有必然账号或必然 PI；只承诺本次实际会发生的回复 | The Linker team will reply to the email address you provided. | Das Linker-Team antwortet Ihnen an die angegebene E-Mail-Adresse. |
| 可选注册入口 | Create an account | 说明沿用本次邮箱，不暗示账号已批准或自动创建 | Create an account with this email | Konto mit dieser E-Mail-Adresse erstellen |
| 访客回执中的注册说明 | Create an account to see net prices and track your inquiry. | 必须补批准条件，避免误导价格可见性 | Create an account with this email to see net prices after approval and track your inquiry. | Erstellen Sie mit dieser E-Mail-Adresse ein Konto. Nach der Freigabe sehen Sie Nettopreise und können Ihre Anfrage verfolgen. |

沿用词条：Name / Name；Reply email / E-Mail für die Antwort；Privacy / Datenschutz；We reply within one business day. / Wir antworten innerhalb eines Arbeitstags.；隐私同意词条与联系表单完全相同。数量输入的无障碍名称为 Quantity for %s / Menge für %s。

邮件主题沿用已存在的 Your inquiry #{order_number} has been received / Ihre Anfrage #{order_number} ist eingegangen；新询盘团队信仍用 New inquiry #{order_number} from {company}，公司未填时以姓名填入占位符。通知的对外发件人与客户可见邮箱仍是 sales@de-linker.com。

## 对抗评审

独立 Spec/文案评审由 `review_spec_copy` 完成，全量 diff 初审发现一组 P2：待审页、注册回执、限制邮件与登录说明仍暗示账号获批后才能询盘。修订后再次逐条核对，结论 PASS；新表单、空态、回执和可选注册文案也通过。团队邮件在公司为空时改用姓名，避免空括号。

| 位置 | 初稿问题 | EN 定稿 | DE 定稿 |
|---|---|---|---|
| 待审页、注册回执 | 旧文案把询盘权限与审批绑定 | We are reviewing your partner account and will email you when it is approved. You can send inquiries now; approval opens net prices. | Wir prüfen Ihr Partnerkonto und informieren Sie per E-Mail über die Freigabe. Anfragen können Sie bereits senden; Nettopreise sehen Sie nach der Freigabe. |
| 限制邮件 | 旧文案说 Proforma 请求暂停 | You can browse products and send inquiries. Net prices remain unavailable while your account is limited. You can also reach us at sales@de-linker.com. | Sie können Produkte ansehen und Anfragen senden. Solange Ihr Konto eingeschränkt ist, werden keine Nettopreise angezeigt. Sie erreichen uns auch unter sales@de-linker.com. |
| 登录说明 | 登录即展示价格的含义不准确 | Net prices after account approval | Nettopreise nach Freigabe Ihres Kontos |
| 退役的原生结账入口 | 绕过新表单不能静默创建询盘 | Please use the inquiry form to send your inquiry. | Bitte senden Sie Ihre Anfrage über das Anfrageformular. |

评审基准：AGENTS.md、本票、已选原型、既有 .po 术语和线上商务文案。`linker-copywriting` 的 Hard Stops 文件在本机列出的技能目录及项目内均未找到，未声称执行该缺失文件；本记录提供可检查的独立初审意见、修订与通过结论。英德词条已随插件发布，审批邮件的真实夹具断言同步更新。

## PR #290 round 1: restricted account notice

Draft EN: **Access currently limited** — “You can send inquiries. Net prices are unavailable while your account is limited.”

Independent DE draft: **Zugang derzeit eingeschränkt** — “Sie können Anfragen senden. Solange Ihr Konto eingeschränkt ist, werden keine Nettopreise angezeigt.”

Adversarial review (`review_spec_copy`, 2026-10-18): body passes. It states that inquiries remain open, limits only prices, makes no new response/approval promise, uses Sie, and leaves the actual team's saved reason visible. Terminology objection: the established gettext title is **Zugriff derzeit eingeschränkt**, not Zugang. Keep the established title and reason label **Unser Grund:**.

Final EN: **Access currently limited** — “You can send inquiries. Net prices are unavailable while your account is limited.” **Our reason:** followed by the escaped, stored reason.

Final DE: **Zugriff derzeit eingeschränkt** — “Sie können Anfragen senden. Solange Ihr Konto eingeschränkt ist, werden keine Nettopreise angezeigt.” **Unser Grund:** followed by the escaped, stored reason. The team's free-text reason is not machine translated by this form.

Honeypot accessible label uses the existing reviewed gettext pair **Website / Website** from the contact form; the shared guard now emits it for both doors. No visible contact wording changes.
