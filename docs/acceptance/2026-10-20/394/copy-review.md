# #394 下一步文案 — 协调者对抗评审（2026-10-20 通过）

规则：AGENTS.md §2（业主 2026-10-09 / 2026-10-11：客户可见文案走对抗评审；EN 先定稿，DE 独立撰写，Sie 体，不是翻译）、§3 用词（产品 / Produkt、产品分类 / Produktkategorie；不说 catalogue、article、cart；禁止「不是…而是…」与 AI 句式）、linker-copywriting Hard Stops 1–9。这四句是对话里的下一步，不是邮件主题。

范围：`services/genie/src/linker_genie/template.py` 的 `TALK`、`PROMISE`、`REPLY_PROMISE`、`PARTNER`。同一组词也写进 `prompts/{en,de}/system.md`、`route.py` 的形状提示和 `agent.py` 的每轮提醒，避免模型对客户另说一套。页面段里「Lösungsentwurf 之后」那句德语时间短语按同一决定改过，不是新的一句客户文案。

状态：下面的英文和德文是本轮写进代码的句子。协调者的对抗评审已完成并签收（2026-10-20，逐句结论与结论见文末），以本轮文本为定稿；后续改动任一句须重新走对抗评审。

Coordinator sign-off: approved (2026-10-20)

## 英文定稿

问候或身份。范围用站点文档库的 Compatibility，不用工具参数名 pairings。不重复坞里的 EU AI Act 句 "You're chatting with an AI system."

- `I am Linker's AI assistant. I can help with products, compatibility, documents and sizing. Which product category do you want to look at?`

询盘之后。英文保持业主承诺的 "one working day"（AGENTS.md 2026-10-09，基线 b28-en）。不改成工具表单的 "one business day"。

- `After you send an inquiry, the Linker team replies within one working day.`

公司类转接后面追加的短句。

- `The Linker team replies within one working day.`

伙伴净价，没有点名产品。两段价格位照产品页 / 产品卡的现行句原样引用，不把访客和待审合成 "the sign-in line"。

- `Approved partner accounts see net prices. A guest sees "Net price after partner sign-in" on the product card. An account under review sees "Account under review. Prices after approval."`

## 德文

独立撰写，Sie 体，不是上面英文的逐句对译。

问候或身份。点出 Genie 这个名字（AGENTS.md：德语作 "Genie – der KI-Assistent von Linker"，不写 "Linker Genie"）。不重复首条消息里的 "Sie chatten mit einem KI-System."

- `Ich bin Genie, der KI-Assistent von Linker. Ich unterstütze Sie bei Produkten, Kompatibilität, Dokumenten und der Auslegung. Welche Produktkategorie möchten Sie ansehen?`

询盘之后。时间短语用站点既有的 "innerhalb eines Werktags"，不用 "in einem Werktag"。

- `Nach dem Absenden Ihrer Anfrage antwortet das Linker-Team innerhalb eines Werktags.`

转接后面追加的短句。主语换成 Linker-Team，时间短语与 linker-tools 的 "unser Team antwortet innerhalb eines Werktags" 相同。

- `Das Linker-Team antwortet innerhalb eines Werktags.`

伙伴净价。句法是「产品卡上写着什么」，两段价格位用现行德语原句，不用 "Anmeldesatz"。

- `Freigegebene Partnerkonten sehen die Nettopreise. Auf der Produktkarte steht für einen Gast „Nettopreis nach Partner-Anmeldung“ und für ein Konto in Prüfung „Ihr Konto wird geprüft. Preise nach Freigabe.“`

## 核对清单

这一轮的判断写在每条后面；文末协调者对抗评审（2026-10-20）已签收这组句子。

- Hard Stop 1：这一轮未看到 `proven`、`tier-1`、`leading`。
- Hard Stop 2：这一轮未看到把证书、协议、RMA 堆成卖点。
- Hard Stop 3：这一轮未看到「我们不是中间商」。
- Hard Stop 4：这一轮未看到 `direct` / `official` / `guaranteed`。`I can help with` 留着，因为禁的是 `Get help…`；德文用 `unterstütze`，不是那句英文的对译。
- Hard Stop 5：这一轮没有新编时效。`one working day` / `innerhalb eines Werktags` 是业主 2026-10-09 已承诺的回复时限。
- Hard Stop 6：这一轮未看到 `Get help…`，也未看到 `Tell us` / `Send us`。产品分类那句是问句，配 `ask`，不是派给客户的作业。
- Hard Stop 7：这四句是对话下一步，不是邮件主题。公开面用词按 §3 核过：没有 catalogue、article、cart。
- Hard Stop 8：这一轮未看到把接线或实验室验证写成卖点。
- Hard Stop 9：这一轮未看到 Future、Weight、Duration 的写法。问候句的四项是这条路由要求列出的范围，不是口号排比。
- AGENTS.md §3：这一轮未看到 catalogue、article、cart、Artikel、Katalog、Warenkorb。德文用 Produkt、Produktkategorie、Sie。
- 句式：这一轮未看到「不是…而是…」，新句子里没有 em dash，没有收束句。
- 德语：这一轮按独立成文写的。问候句点出 Genie、用 `unterstütze` 和 `Kompatibilität`；询盘句用 `Nach dem Absenden`；价格句用「产品卡上写着」。都不是英文的逐句对译。
- EU AI Act：披露句仍只在首条消息（`Entries.php`：`You're chatting with an AI system.` / `Sie chatten mit einem KI-System.`）。这四句不再写那一句。问候句只说明助手是谁，因为这条路由就是问候或身份问题。
- 与既有文案：见下面三条决定。价格位两句是产品页现行句的原样引用。

## 决定

1. **回复时限。** linker-tools `.po`（`UtilityForm`：`our team replies within one business day`）的德语是 `unser Team antwortet innerhalb eines Werktags`。引擎 `texts.py` 另有 `wir antworten innerhalb eines Werktags`。本轮因此不用初稿的 `in einem Werktag`。英文仍是 `within one working day`：这是业主承诺和基线 b28-en 的字，工具表单的 `one business day` 是另一处表面，不拿来改这句。确认卡提示里的 `innerhalb eines Arbeitstags` 仍是那张卡自己的说法，这组句子不跟着改。基线 b28-de 的 `expect.all` 仍匹配 `eines Werktags`、`einem Werktag` 或 `einem Arbeitstag`（答案里出现其中一句，这一行的正则就过）。带 shape 的轮次（talk / promise / partner）把模型原话整段替换为签定句，签定句只出现一次；模型写 `einem Werktag` 或 `einem Arbeitstag` 不算已经说过。服务转接的 handoff 摘要只在缺少承诺内容时追加 `REPLY_PROMISE`，检测 `_has_promise` 只认规范句 `innerhalb eines Werktags`。
2. **Kompatibilität，不用 Passungen。** linker-commerce `.po` 里 `Kompatibilität` 有 6 处，其中标签是 msgid `Compatibility`。初稿的 `Passungen` 站点上没有。英文客户句从初稿的 `pairings` 改为 `compatibility`，与这条 msgid 一致。`with_pairings` 仍是工具参数名，范围段里对模型说的 pairings 不改成客户句。德文问候不用 `Passungen`，用 `Kompatibilität`。`Auslegung` 沿用配置器的 `Welches Projekt legen Sie aus?` 和 `Auslegungsbericht`。
3. **价格门原句。** 访客在产品页和 Genie 产品卡上读到的是 `Net price after partner sign-in` / `Nettopreis nach Partner-Anmeldung`（#242，`ProductView::price_html`）。待审账号读到的是 `Account under review. Prices after approval.` / `Ihr Konto wird geprüft. Preise nach Freigabe.`（#222，`PriceDisplay::reason_text`；#242 表里较短的 `Prices after approval` / `Preise nach Freigabe` 已经退役）。初稿把两种账号都说成 `the sign-in line` / `Anmeldesatz`，和产品页不符。定稿分别引用这两句现行文案。已批准账号仍是 `Approved partner accounts see net prices`；德文独立写成 `Freigegebene Partnerkonten sehen die Nettopreise`。

协调者若要改字，改 `template.py` 里的这四句，并改这篇记录。提示词里让模型对客户说的同一组词要一起改。

## 协调者对抗评审（2026-10-20）

逐句结论：
- EN 问候/身份：通过。"I can help with products, compatibility, documents and sizing." + 一个问句；不重复 AI 披露；无禁用词、无 AI 句式。
- EN 询盘承诺：通过。"within one working day"，与业主 2026-10-09 承诺一致。
- EN 转接短句：通过。
- EN 伙伴净价：通过。两段价格位逐字引用产品页/产品卡现行句。
- DE 问候/身份：通过。Sie 体；"Genie, der KI-Assistent von Linker" 与站内德语命名一致；"Kompatibilität" 与 .po 一致；"Auslegung" 与规格 13 一致。
- DE 询盘承诺：通过。"innerhalb eines Werktags" 与 linker-tools .po 一致。
- DE 转接短句：通过。
- DE 伙伴净价：通过。两段德语价格位逐字引用现行句（"Nettopreis nach Partner-Anmeldung"、"Ihr Konto wird geprüft. Preise nach Freigabe."）。
- 英德同义、Sie 体、无「不是…而是…」、无三连排比：通过。
- 备注：EN 未重复 Genie 名字、DE 重复，属可接受的不对称（首条消息已披露名字）。

结论：**通过**。以本轮文本为定稿；后续如需改动任一句，重新走对抗评审。

Coordinator sign-off: approved (2026-10-20)
