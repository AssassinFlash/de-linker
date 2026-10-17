# 后台账户审核文案 · EN / DE

依据：业主选定变体 C、本票正文与会话澄清。无 7 秒计时；状态随时可改。EN 初稿先定语义，DE 以 Sie 体独立撰写；既有状态用语沿用插件正式词表。

## 初稿

| EN | DE |
|---|---|
| Company website | Unternehmenswebsite |
| You do not have permission to switch to this customer. | Sie sind nicht berechtigt, zur Ansicht dieses Kunden zu wechseln. |
| User Switching is not active. | User Switching ist nicht aktiviert. |
| Accounts waiting for you | Konten zur Prüfung |
| All accounts → | Alle Konten → |
| Accounts | Konten |
| %s account to review | %s Konto zu prüfen / %s Konten zu prüfen |
| Search accounts | Konten suchen |
| You are not allowed to review accounts. | Sie sind nicht berechtigt, Konten zu prüfen. |
| This account is unavailable or you do not have permission to review it. | Dieses Konto ist nicht verfügbar oder Sie sind nicht berechtigt, es zu prüfen. |
| You are not allowed to change this account. | Sie sind nicht berechtigt, dieses Konto zu ändern. |
| Enter a reason for the customer before restricting or rejecting the account. | Geben Sie einen Grund für den Kunden an, bevor Sie das Konto einschränken oder ablehnen. |
| Free email provider: %s | Kostenloser E-Mail-Anbieter: %s |
| Email domain: %s (not verified) | E-Mail-Domain: %s (nicht geprüft) |
| Possible automated registration: company name contains "%s". | Möglicherweise automatisierte Registrierung: Der Unternehmensname enthält „%s“. |
| No suspicious company-name pattern found. Please verify the company. | Kein auffälliges Muster im Unternehmensnamen erkannt. Bitte prüfen Sie das Unternehmen. |
| Company | Unternehmen |
| Contact | Kontakt |
| Approval | Freigabe |
| Reason | Grund |
| Registered | Registriert am |
| No accounts match these filters. | Für diese Filter wurden keine Konten gefunden. |
| Review or change decision | Prüfen oder Entscheidung ändern |
| All accounts | Alle Konten |
| Login email | E-Mail-Adresse für die Anmeldung |
| The request failed. Please try again. | Die Anfrage ist fehlgeschlagen. Bitte versuchen Sie es erneut. |
| Automatic checks | Automatische Prüfungen |
| Details | Details |
| View the website as this customer | Website als dieser Kunde ansehen |
| Approve | Freigeben |
| Restrict | Einschränken |
| Reject | Ablehnen |
| Reason for the customer | Grund für den Kunden |
| The customer receives this reason by email. Explain what information is needed or why the account cannot be approved. | Der Kunde erhält diesen Grund per E-Mail. Erläutern Sie, welche Angaben fehlen oder warum das Konto nicht freigegeben werden kann. |
| Restrict and notify customer | Einschränken und Kunden informieren |
| Reject and notify customer | Ablehnen und Kunden informieren |
| Cancel | Abbrechen |
| Saving decision… | Entscheidung wird gespeichert… |
| Decision saved. You can change it at any time. | Die Entscheidung wurde gespeichert. Sie können sie jederzeit ändern. |
| Loading accounts… | Konten werden geladen… |
| Try again | Erneut versuchen |
| No accounts are waiting for review. New registrations will appear here and in the top bar. | Es warten keine Konten auf Prüfung. Neue Registrierungen erscheinen hier und in der oberen Leiste. |
| Review account | Konto prüfen |
| Close | Schließen |

## 对抗评审

2026-10-17，由独立 Spec 评审代理在全量 diff 评审中逐一核对 PHP、React、`.po` 和此表；Standards 评审另检查流程是否留下记录。

| 对抗检查 | 评审意见 | 定稿处理 |
|---|---|---|
| 批准、限制、拒绝会不会被误读为一次性决定？ | 操作成功明确说可随时修改；没有倒计时或 Undo 文案。 | 保留 `Decision saved. You can change it at any time.` / `Die Entscheidung wurde gespeichert. Sie können sie jederzeit ändern.` |
| 客户能否看到原因，员工是否会误填内部备注？ | 标签写明“for the customer”，提示直接说明邮件送达，并给出“缺哪些资料 / 为什么不能批准”两种用途；提交按钮写明通知客户。 | 保留原因标签、提示与两个通知按钮；原因不是内部备注。 |
| 自动线索会不会冒充查证结论，或直接把申请判为机器人？ | 未知邮箱域名明确 `not verified` / `nicht geprüft`；公司名只显示 `Possible` / `Möglicherweise` 和命中的短语；无命中仍要求核实公司。 | 保留初稿；禁止把这些提示自动转成账户决定。 |
| 德语是否只是逐字翻译，或改变已用术语？ | Sie 体、`Freigeben / Einschränken / Ablehnen` 与既有词表一致；空状态和原因提示是完整可操作句。没有禁止的对比句、三连口号或商务禁词。 | EN、DE 均定稿；不更改现有批准邮件文案。 |
| 记录与实际界面是否一致？ | 初稿“无权修改此账户”一行的德语与已有 `.po` 不同；实际为 `Sie dürfen dieses Konto nicht ändern.`，两句均可，但记录须准确。 | 采用实际 `.po`：`You are not allowed to change this account.` → `Sie dürfen dieses Konto nicht ändern.` |

## 定稿

初稿表除上一节记录的权限句以外全部接受，未要求修改运行时文案。权限句以 `.po` 的 `Sie dürfen dieses Konto nicht ändern.` 为最终稿。PHP MO 与 React JSON 均已构建；浏览器验证员工使用德语时，读取卡片及发出客户通知后的状态、国家、检查线索仍为德语。最终视觉门须等 #252 合并、重新导入最新快照后再签收。
