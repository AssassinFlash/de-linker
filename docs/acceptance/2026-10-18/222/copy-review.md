# 待审账号保持登录 · 文案对抗评审

依据：当前票的业主裁定、AGENTS.md 的英德用词与文案评审要求，以及已交付账户卡的措辞。英文先行，德语独立撰写，使用 Sie 体。以下只改变价格位置的短提示；注册已收到、已批准邮件的主题与正文不变。

| 位置 | 初稿 | 评审意见 | 定稿 |
| --- | --- | --- | --- |
| EN 价格位 | Prices after approval | 仅说明条件，没有明确当前账号正在审核。直接补足状态；不要求再次登录，不承诺审核时间。 | Account under review. Prices after approval. |
| DE 价格位 | Konto in Prüfung. Nettopreise nach Genehmigung. | 使用面向客户的完整状态句；价格条件沿用既有 .po 的 Freigabe，避免新造 Genehmigung 术语。 | Ihr Konto wird geprüft. Preise nach Freigabe. |

账户内的卡片沿用已经评审的英文标题 `Your account is under review`、徽标 `Under review`、审核与询盘说明和产品链接。改变的是卡片的位置和标题层级：它是工作台内的 h2，不再替代整个账户页。既有正文已明确可以发送询盘，且获批后通过邮件通知；不新增审批时限或额外服务承诺。

复核：价格短提示无登录指令；restricted 的原因与提示不被 pending 替代；无 catalogue/article/cart，无否定对比、三连排比或无依据的强化词。客户可见邮箱继续为 sales@de-linker.com。

独立 Spec 评审认可两种语言的短提示，指出它只能描述真正待审的账号：待审询盘保存的 approval 原因在批准后仍可能被重放。已修正为批准后对尚未定价的历史询盘行显示既有中性文案 `Price on request` / `Preis auf Anfrage`，并增加回归验证。注册与批准邮件不变。

## 第一轮：restricted 账户页状态卡

复用 #246 已交付的状态和原因文案，在账户页同一 LC 卡片中呈现。原因由员工保存，按纯文本转义，账户和询盘表单共用原因片段。

| 位置 | 初稿 | 对抗评审意见 | 定稿 |
| --- | --- | --- | --- |
| EN 状态 | Access currently limited / Restricted | 保留既有状态术语；不说审核中，也不暗示询盘不可用。正文明确仍可发询盘，原因紧跟说明。 | Access currently limited / Restricted; You can send inquiries. Net prices are unavailable while your account is limited. |
| DE 独立撰写 | Zugriff derzeit eingeschränkt / Eingeschränkt | Sie 体；以“eingeschränkt”描述访问状态，保留既有德语 .po 用词和 Nettopreise，不承诺自动解除限制。 | Zugriff derzeit eingeschränkt / Eingeschränkt; Sie können Anfragen senden. Solange Ihr Konto eingeschränkt ist, werden keine Nettopreise angezeigt. |
| EN/DE 原因 | Our reason: / Unser Grund: | 不把员工原因改写为猜测；提示顺序为状态 → 说明 → 保存原因 → 联系方式，与询盘页一致。 | 原有原因标签与原文，HTML 转义。 |

价格提示仍只有 `PriceDisplay::reason_text` 一处映射；账户状态不重复决定价格可见性。
