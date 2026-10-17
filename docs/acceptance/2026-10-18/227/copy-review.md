# 通知接线文案 · EN / DE 对抗复核

2026-10-18：邮件收件人和模板已在内部通知票合并并上线；本 PR 复用既有 `TeamEmail` 与 `Digest\Block`，没有新写客户事务邮件正文或改主题。

## 初稿

| 用途 | EN | DE |
|---|---|---|
| 摘要待审块，既有标题后附本次 pending 数量 | Accounts waiting for approval (N) | Konten, die auf die Freigabe warten (N) |
| 通知与摘要的逐申请链接，既有词表 | Open the customer | Kunden öffnen |

## 独立对抗意见

Spec 评审代理对全量 diff 和当前规格独立核对：数量只表示尚未决定的申请，限制与拒绝不再计入；集合标题用复数能承载 `(0)`、`(1)`，无需新增单复数文案。链接的英文略偏后台用语，但沿用正式 EN/DE 术语，目标是该客户的审核卡片，不误导操作、不增加承诺；保留即可。未发现禁词、AI 对比句式或德语 Sie 体偏离。

## 定稿

初稿全部接受。真实 Outbox 断言 EN/DE 标题、数量及 URL；后台卡片原有按钮、原因提示、检查说明、空态与错误反馈继续使用前次已对抗评审的[定稿](../../2026-10-17/227/copy-review.md)，本轮逐态截图重新核对其实际呈现。

## Claude 第 1 轮修订文案初稿（2026-10-18）

EN 先按待办语义定稿，DE 独立按员工工作语境撰写，不把限制误写成新申请。

| EN | DE | 目的 |
|---|---|---|
| Website (from email domain) | Website der E-Mail-Domain | 说明链接来自邮箱，不能宣称已核实公司网站。 |
| Restricted, awaiting customer information | Eingeschränkt, Angaben vom Kunden fehlen | 单列需要客户补资料的限制账户。 |
| Restricted, awaiting customer information: %s | Eingeschränkt, Angaben vom Kunden fehlen: %s | 摘要中的独立数量，不并入 pending。 |
| View restricted accounts | Eingeschränkte Konten ansehen | 直接进入限制账户区域。 |
| No restricted accounts are awaiting customer information. | Bei keinem eingeschränkten Konto fehlen derzeit Kundenangaben. | 零限制账户时清楚说明当前没有补资料待办。 |

### 独立对抗意见与定稿

2026-10-18，独立 Spec 代理在 `b7cbbf40...dc4eeff` 全量评审中核对五条新增文字、PHP/React、PO/MO、React 实际消费的编译 JSON，并抽查 EN/DE 限制区域与空态截图。意见与处理：

| 对抗问题 | 独立评审意见 | 定稿处理 |
|---|---|---|
| 邮箱域名链接是否冒充已核实官网？ | 两版都明确链接来自邮箱域名，没有声称已核实。 | 保留初稿。 |
| 限制是否混入新申请，或不清楚谁要补资料？ | 区域标题与带数量版本都写明等待客户补资料；与 pending 区分清楚。 | 保留初稿。 |
| 摘要链接动作是否与目标一致？ | View restricted accounts / Eingeschränkte Konten ansehen 直接对应限制区域。 | 保留初稿。 |
| 空态是否反转语义，德语是否生硬？ | 两版均说明当前没有这类补资料待办；德语自然，无语义反转。 | 保留初稿。 |
| 记录是否与交付资源一致？ | 五条原文及 PO/MO 一致；React 唯一消费的 restricted-empty 在编译 JSON 中一致，其余由 PHP/MO 渲染。 | 五条均定稿，无强制修改。 |

Standards 同时指出“待补录”不能当作闭环；此处已保存实际独立意见与定稿处置，替换此前的待评审占位。
