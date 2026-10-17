# #302 文案保留检查

范围是现有配置器译文的载体迁移，依据票据要求保留全部既有 msgstr。
初稿为 `configurator-before.json`，取自 `translation-comparison.json` 记录的基线提交，
包含配置器原有的全部英文消息及德语单复数形式。

| 检查意见 | 定稿处理 |
| --- | --- |
| 共用英文消息的德语不能被另一工具覆盖。`Sent, but the draft does not show it yet. Please check.` 在配置器中以“Bitte prüfen Sie den Entwurf.”收尾，Genie 以“Bitte prüfen.”收尾。 | 配置器使用 `configurator` context；两边原文各自保留。 |
| `Not added. Try again.` 的配置器措辞是“Nicht hinzugefügt. Versuchen Sie es erneut.”，Genie 使用“Bitte erneut versuchen.”。 | 同上；不合并两种措辞。 |
| `Saved to your account.` 的配置器措辞是“In Ihrem Konto gespeichert.”，Genie 使用“Im Konto gespeichert.”。 | 同上；不合并两种措辞。 |
| Sie 体、Lösungsentwurf 与 Stückliste 术语以及复数形式须保持。 | 全量 msgid → msgstr 对照：无丢失、无新增、无改动；原有术语测试继续通过。 |

本轮实现者完成上述保留检查；PR 中的独立 Spec / Standards 评审由 Claude 执行。
`App.test.tsx` 在同时载入两工具译文的情况下检查配置器的未确认、重试与保存状态。
