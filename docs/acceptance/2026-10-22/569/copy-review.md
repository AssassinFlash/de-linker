# 注册容量与恢复文案评审

本票沿用现有注册邮件的正式主题、正文和视觉；新增的是容量拒收、未知结果、员工处置和隐私状态。EN 为源文案，DE 以正式 Sie 体独立核对。评审依据为项目 AGENTS.md、现有账户/隐私词汇和 linker-copywriting Hard Stops 1–9。以下是已完成的独立文案审查记录，不代替 Spec、Standards 或运行时验收。

## 初稿与对抗意见

2026-10-22，incident_forensics 独立核对四组客户消息：

- 注册暂不可用且未创建账户：EN “Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.” / DE “Eine Registrierung ist derzeit nicht möglich. Ihr Konto wurde nicht angelegt. Bitte versuchen Sie es später erneut oder schreiben Sie an sales@de-linker.com.” 原文通过；只用于真正未创建的结果。
- 合并姓名最多250字符：EN “Please use no more than 250 characters for your first and last name together. Your account has not been created; your entries are still here.” / DE “Bitte verwenden Sie für Vor- und Nachnamen zusammen höchstens 250 Zeichen. Ihr Konto wurde nicht angelegt; Ihre Eingaben bleiben erhalten.” 语言通过；250来自本机 WordPress 原生 users.display_name schema，评审没有把文案当成技术上限的证据。
- 注册结果未知：EN “The registration status could not be confirmed. Please try signing in before registering again, or email sales@de-linker.com. You can send inquiries without an account.” / DE “Der Status Ihrer Registrierung konnte nicht bestätigt werden. Versuchen Sie bitte, sich anzumelden, bevor Sie sich erneut registrieren, oder schreiben Sie an sales@de-linker.com. Anfragen können Sie auch ohne Konto senden.” 原文通过；不得改成“账户未创建”。
- 确认拒绝资料保存：EN “Your changes could not be saved. Your entries are still here. Please try again later or email sales@de-linker.com.” / DE “Ihre Änderungen konnten nicht gespeichert werden. Ihre Eingaben bleiben erhalten. Bitte versuchen Sie es später erneut oder schreiben Sie an sales@de-linker.com.” 语言通过；输入保留须由实际表单证明。

对抗意见指出“entries / Eingaben”可能被理解为包括密码。定稿保留原句，在清空密码的注册情境补 “Please re-enter your password.” / “Bitte geben Sie Ihr Passwort erneut ein.”；多密码框的资料表单在有密码输入时补复数 “Please re-enter your passwords.” / “Bitte geben Sie Ihre Passwörter erneut ein.”。普通 billing 保存不加无关的密码句。密码不得为满足文案而回填、持久化或进入指纹。

root 后续独立审查完整29组 EN/DE：27组保留，两组员工措辞收窄为普通词汇：

| 初稿 | 审查意见 | 定稿 EN | 定稿 DE |
|---|---|---|---|
| Recent staff dispositions | disposition 太抽象 | Recent staff decisions | Letzte Entscheidungen des Teams |
| Reason for this disposition | 同上 | Reason for this decision | Grund für diese Entscheidung |
| Recover pending notifications / Ausstehende Benachrichtigungen wieder aufnehmen | 390视口中按钮溢出，沿原生按钮缩短；不承诺投递 | Recover notifications | Benachrichtigungen wieder aufnehmen |
| Resolve interrupted registration；缩写候选 Resolve registration / Registrierung abschließen | 会被理解为完成建户，实际仅标记无账户的中断占位已处理 | Mark as resolved | Als erledigt markieren |

未知资料提交的追加消息经 root 的独立 Spec 审查原文通过：EN “The status of your changes could not be confirmed. Please check your account before saving again, or email sales@de-linker.com.” / DE “Der Status Ihrer Änderungen konnte nicht bestätigt werden. Bitte prüfen Sie Ihr Konto, bevor Sie erneut speichern, oder schreiben Sie an sales@de-linker.com.”。仅在原生 COMMIT/ROLLBACK 无法确认时使用，不承诺未保存或自动重试；重新打开账户读取原生已确认状态。

## 定稿的事实门

所有新增 EN/DE 定稿在同一次插件交付中发布，PO/MO 的29组新译文没有覆盖既有人工词项。账户资料的真实 Woo handler + 实际项目模板先出现“数据库未写但输入丢失”的红门，本票为本次已验证提交增加四个非密码值的 request-local 回填；跨用户、重新读取页面和任意后续 POST 不借用该值。注册和 billing 的原生表单亦按两语言两宽度实测。

“Accepted by the notification queue / In die Benachrichtigungswarteschlange aufgenommen”只表示持久 Outbox 接收，不能说 SMTP 或收件箱已收到。“Account created; notification pending / Konto angelegt; Benachrichtigung ausstehend”必须保留真实已创建账户；恢复不重复创建。“Notification skipped by policy / Benachrichtigung gemäß Versandregel übersprungen”是已持久确认的单个 notice 决策。“Notification data erased / Benachrichtigungsdaten gelöscht”只覆盖本轮准确归属的 source/job 数据，不声称删除账户或所有历史邮件。

容量标签指公开待处理业务资料的逻辑字节，不代表 MySQL 物理磁盘。员工处置只在既有权限、nonce、审计和原生读回之后表示完成；未知结果不得称已释放。没有新增营销承诺、模型判断权限或客户 MFA 要求。完整私密审查原稿保留在本机 incident 目录，未把客户数据、令牌或原始 Message 放入仓库。


## 评审修复：隐私原始owner读取失败

初稿EN：**Registration notification data could not be read. Please try again.**

初稿DE：**Die Registrierungsbenachrichtigungsdaten konnten nicht gelesen werden. Bitte versuchen Sie es erneut.**

root独立对抗意见：EN原句通过；DE拆开长复合词，保留“读取失败、请重试”的事实，不改成空集、成功、已擦除或已向当前邮箱转移。

定稿EN：**Registration notification data could not be read. Please try again.**

定稿DE：**Die Daten zu den Registrierungsbenachrichtigungen konnten nicht gelesen werden. Bitte versuchen Sie es erneut.**

只在verified-email回调的实际原始owner/原生读取失败时返回：export为原生WP_Error，erase为retained且done=false。原生测试证明原地址A改为B后，故障不掩盖A的数据；健康重试仍能读取并擦除。PO/MO同批交付，原生gettext分别读回EN源文和DE定稿正确；没有把该错误分支冒充成已拍摄的新浏览器状态。
