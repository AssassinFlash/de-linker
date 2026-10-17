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

## 第一轮修改：保留既有德语

原表 Retranslate 动作改为 Sync German，避免暗示整页重译；待结构异常的处理是显性异常处理，不是审批。

| EN 初稿 | DE 独立措辞 | 使用处 |
|---|---|---|
| German out of date: structure differs | Deutsch nicht aktuell: abweichende Struktur | 状态列及摘要异常原因 |
| Sync German | Deutsch synchronisieren | 行动作，遵守原样保留及增量规则 |
| German sync has been queued. | Die Synchronisierung der deutschen Fassung wurde eingeplant. | 排队成功提示，允许零调用的基线收养 |

独立 Spec 评审：结构异常与同步动作可原样定稿；排队提示的 DE 初稿“Die deutsche Synchronisierung”略生硬，建议明确为“Die Synchronisierung der deutschen Fassung”。已采纳，表中为定稿。EN 不变；三组定稿已同步 .pot/.po/.mo。

## 第二轮补齐：每日摘要异常块

在已合并的每日摘要 Block/filter 上接入，文案只用于内部摘要。

| EN 初稿 | DE 独立初稿 | 用途 |
|---|---|---|
| German translation exceptions (%d) | Probleme bei deutschen Übersetzungen (%d) | 已记录异常的数量 |
| Open English source | Englischen Inhalt öffnen | 英文源后台入口 |
| No German translation exceptions. | Keine Probleme bei deutschen Übersetzungen. | 空态 |

独立 Spec 对抗评审：标题及链接可定稿；德语空态应加 `gemeldet`，因为查询仅覆盖已记录的失败和结构异常，不能保证全部译文质量。采纳：**Keine Probleme bei deutschen Übersetzungen gemeldet.** EN 原文保留；三组定稿进入 .pot/.po/.mo。真实 DigestEmail/Outbox 的 EN/DE 正文与路由断言通过，无邮件实发。
