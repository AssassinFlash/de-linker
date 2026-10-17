# 后台德语同步文案

依据：业主本票会话确认所有内容自动翻译、自动生效，无人工审阅与营销冻结；AGENTS.md 的用词与 Sie 体仍适用。

## 初稿（EN 先行；DE 独立措辞）

| EN | DE | 使用处 |
|---|---|---|
| German | Deutsch | 状态列标题，沿用 |
| Synced | Synchronisiert | 自动同步成功，沿用 |
| Translation pending | Übersetzung ausstehend | 正常排队或重试，沿用 |
| Translation failed | Übersetzung fehlgeschlagen | 缺凭据、不可重试或耗尽重试 |
| Missing | Fehlt | 没有德语孪生，沿用 |
| Missing, translation pending | Fehlt, Übersetzung ausstehend | 首次翻译排队，沿用 |
| Retranslate | Neu übersetzen | 重试或主动重译，沿用 |
| This content is managed by the repository. | Diese Inhalte werden über das Repository verwaltet. | 拒绝对仓库模板的手工构造请求，仅后台 |

## 评审与定稿

独立 Spec 代理对 8 行逐项对抗评审（固定差异 00363e69...b968d83a）：全部可接受。

- 等待翻译只用于正常排队/重试，失败用于最终失败，语义明确。
- Synced / Synchronisiert 准确表达自动生效；没有人工批准暗示。
- Neu übersetzen 动作明确；模板归属提示仅用于后台，没有营销承诺或禁用词。
- 无须改词；初稿表原样定稿。新增字符串已写入 .pot/.po/.mo，并通过覆盖及编译检查。

本记录是后台措辞评审。产品与页面机器翻译按业主裁定自动生效，不设人工审阅门。
