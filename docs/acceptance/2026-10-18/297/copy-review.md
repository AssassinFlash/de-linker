# #297 内部认证健康文案

仅新增内部摘要区块，不修改客户邮件主题、正文、页面或客户可见邮箱。EN 先行；DE 独立撰写，使用 Sie 体。对抗检查依据 AGENTS.md 的文案裁定与既有 `.po` 用词。

| 项 | 初稿 | 评审意见 | 定稿 |
|---|---|---|---|
| EN 标题 | SMTP status | 对业务收件人说明检查对象，避免把协议名当标题。 | Internal mail authentication |
| EN 异常 | SMTP is not working. | 未连远端，不能断言不可用；本票检查的是配置与身份。 | Internal mail not authenticated. |
| EN 操作说明 | Contact the developer. | 给出当前通道和可操作的检查对象。 | Internal notifications use PHP mail(). Check the SMTP configuration on the server. |
| EN 正常空态 | Internal mail is authenticated. | 文件完整不证明真实认证或收件箱结果，只能说已配置。 | Authenticated SMTP is configured for internal notifications. |
| DE 标题 | SMTP-Status | 明确内部邮件与认证，和德语运维用词一致。 | Authentifizierung interner E-Mails |
| DE 异常 | Interner Mailversand fehlgeschlagen. | 配置异常不等于投递失败；投递失败由既有重试与失败邮件区块报告。 | Interne E-Mails sind nicht authentifiziert. |
| DE 操作说明 | Bitte prüfen. | 指明当前发送方式与服务器配置，正式 Sie。 | Interne Benachrichtigungen werden über PHP mail() versendet. Prüfen Sie die SMTP-Konfiguration auf dem Server. |
| DE 正常空态 | SMTP funktioniert. | 不声称已连接或已成功认证。 | Authentifiziertes SMTP ist für interne Benachrichtigungen konfiguriert. |

检查结果：没有发送成功、收件箱或可用性方面的额外承诺；异常项每封摘要仅一条，不追加告警邮件；不呈现主机、用户、密码或文件内容。EN/DE 由同一健康事实驱动；真实摘要模板的英德渲染由 `Integration\InternalSmtpTest::test_missing_configuration_falls_back_and_reports_once_per_digest` 验证。
