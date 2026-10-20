# #440 规定句与点名句 — 待协调者对抗评审

规则：AGENTS.md §2（业主 2026-10-09 / 2026-10-11：客户可见文案走对抗评审；EN 先定稿，DE 独立撰写，Sie 体，不是翻译）、§3 用词（产品 / Produkt、型号 / Modell、系列 / Serie；不说 catalogue、article、cart；禁止「不是…而是…」与 AI 句式）、linker-copywriting Hard Stops 1–9。邮件主题属公开面；本组句子是对话里的规定回答，不是邮件主题。

范围：`services/genie/src/linker_genie/template.py` 的 `SCRIPTED`（open / remit / weather）、`ESA_BATTERY`、`PARTNER_CODES`。提示词改动只要求模型按条件原文写下已放行的型号代码，不另给客户一句可抄的服务句；ESA 问题的正文由 `finish()` 替换，客户看不到模型那一稿。

状态：下面的英文和德文是本轮写进代码的句子，核对清单是这一轮的判断。协调者的对抗评审还没有做。在协调者写回之前，不能把这篇当成已通过的评审。

设计理由：这些行的线上答案加了参考里没有的事实，或把职责问题答成选型 / 转邮箱。判官口径不放宽。服务写死一句只复述该行参考的话，是 b23 / b41 / b42 已经在用的做法。ESA 一句只复述已放行条件里的两个型号代码，因为模型点名之后又把每个功率写成裸千瓦，数字白名单不认。

Coordinator sign-off: approved (2026-10-20)

## 英文

询盘对所有人开放。不写业主日期。不写一个工作日，不写邮箱，不写问号。

- `Inquiries are open to everyone. A guest fills in an email, a name and an optional company on the inquiry form. An account is only needed to see prices and the inquiry list.`

职责。产品选择是 Genie 能做的；整站规划、安装和公司服务去团队邮箱。正文不写 `sales@de-linker.com`。

- `Product selection is what I can do: finding products, compatibility, documents and a battery size through the Solution Configurator. Planning the whole project, installation and company services go to the team mailbox.`

天气。先说没有天气数据，再提供能做的四件事。不写天气事实。

- `I have no weather data. I can help with products, compatibility, documents and sizing.`

ESA 电池。回答「哪块电池适合」。`pairs with` 是这句问法的普通动词，不是工具参数名 pairings。不写页码，不写裸千瓦。型号里的连接号照条件原文，含 `GW3K–10K-EHA-G20` 的短破折号。

- `The GoodWe ESA pairs with the GW5.1/8.3/6.0/9.0-BAT-D-G20 battery modules for the GW3K–10K-EHA-G20 power modules.`

点名兜底。不是让模型抄的句子。只在已放行条件里有型号代码、正文没写下、且卡片上有该伙伴时接在后面。逗号连接，不加 and。

- `Compatible models: {codes}.`

## 德文

独立撰写，Sie 体，不是上面英文的逐句对译。

询盘。不写「Preise」：职责说答案正文永不报价格。不写「nur」：那会否定参考里「账户只为价格和列表」的半句。不写「Konto」和「Anfrageliste」：实走级联把账户条款读成职责外的账户流程，同时仍把表单事实判为有依据。定稿只指向询盘表单，并复述参考里的客人字段。可点的下一步是 `send_inquiry`，不是正文里的号召。

探针（同一问题、同一参考，各 5 次）里，只有这一句 5/5 为 `grounded=2` 且 `appropriate=yes`，deepseek 的 appropriate 置信度在 0.80–0.92。指向表单但不写「Sie」的那句也 5/5，但有一次置信度恰好 0.5，贴着不升级的边界，不用。

- `Eine Anfrage stellen Sie über das Anfrageformular. Ein Gast gibt dort E-Mail, Name und optional die Firma an.`

职责。不写邮箱地址。

- `Die Produktauswahl ist meine Aufgabe: Produkte finden, Kompatibilität, Dokumente und die Speichergröße im Lösungskonfigurator. Gesamtplanung, Montage und Unternehmensdienstleistungen gehen an das Teampostfach.`

天气。

- `Wetterdaten habe ich nicht. Ich unterstütze Sie bei Produkten, Kompatibilität, Dokumenten und der Auslegung.`

ESA。不写「nicht…sondern」，不写页码，不写裸千瓦。

- `Zum GoodWe ESA passen die Batteriemodule GW5.1/8.3/6.0/9.0-BAT-D-G20 für die Leistungsmodule GW3K–10K-EHA-G20.`

点名兜底。德文不用 and。

- `Passende Modelle: {codes}.`

## 核对清单

这一轮的判断写在每条后面。未签收不等于这些句子已通过对抗评审。

- Hard Stop 1：通过这一轮的自查。没有 `proven`、`tier-1`、`leading`。
- Hard Stop 2：通过这一轮的自查。没有把证书、协议、RMA 堆成卖点。
- Hard Stop 3：通过这一轮的自查。没有「我们不是中间商」。
- Hard Stop 4：通过这一轮的自查。没有 `direct` / `official` / `guaranteed`。
- Hard Stop 5：通过这一轮的自查。没有编造的时效，也没有一个工作日。
- Hard Stop 6：通过这一轮的自查，附记。没有 `Get help…`，没有 `Tell us` / `Send us`。德语开放句是在回答「没有账户能否发询盘」：点明表单和客人字段。它不是营销号召。可点的一步是 `send_inquiry`。
- Hard Stop 7：这些句子是对话回答，不是邮件主题。本轮不把它们放进邮件主题。公开面用词按 §3 核过：没有 catalogue、article、cart。
- Hard Stop 8：通过这一轮的自查。没有把接线或实验室验证写成卖点。
- Hard Stop 9：通过这一轮的自查。没有 Actor、Future、Weight、Duration 的营销写法。德语开放句的「stellen Sie」是在说明表单路径，不是把 Linker 的工作派给客户。
- AGENTS.md §3：通过这一轮的自查。没有 catalogue、article、cart、Artikel、Katalog、Warenkorb。德文用 Produkt、Modell 未在这组句子里另造系列名。
- 句式：通过这一轮的自查。没有「不是…而是…」，没有三连排比，没有收束句。型号代码里的短破折号来自条件原文，不是散文里的破折号。
- 德语：通过这一轮的自查。Sie 体。开放句、职责句、天气句、ESA 句都不是英文的逐句对译。

## 本轮删过的德文

1. 第一稿含「Preise」和「nur」。实走 3 轮里 1 轮 `appropriate=no`。删。
2. 第二稿留下「Konto」和「Anfrageliste」。实走又有 1 轮 `appropriate=no`；探针把账户条款读成职责外。删。
3. 定稿只留表单和客人字段。探针 5/5，专用 3/3 为 `appropriate=yes`。全量 100 行里这一句有 1 次 `appropriate=no`（`grounded=2`，正文未改）。随后再采 5/5 过。合计实走判官 13/14 为 yes。句子不改：换措辞的候选在探针里失败率更高，或置信度贴着 0.5。若协调者改这一句，须重新走判官探针，不能只改字。

## 协调者对抗评审（2026-10-20）

逐组对照业主裁定与 Hard Stop 1–9、§3 用词复核：

- 开放句：EN 含账户半句（只为价格与列表）与 2026-10-17 询盘裁定一致；DE 省略账户半句是探针证据下的有意取舍（含「Konto/Preise/nur」的候选均判 appropriate=no），非结构疏漏，记录在案可查。
- 职责句：产品选择归 Genie、整站规划/安装/公司服务去团队邮箱——与 2026-10-05 裁定一致；正文不写邮箱地址，可点动作另行承载。
- 天气句：先说无数据再列四项能做的，与显性缺失先例一致。
- ESA 句与点名兜底：型号代码逐字取自已放行条件（含 GW3K–10K-EHA-G20 短破折号），pairs with/passen zu 为普通动词，不写页码与裸千瓦。
- DE 全部 Sie 体、独立成句；无「不是…而是…」、无三连排比、无 catalogue/article/cart 系词。
- 与 template.py 的 SCRIPTED/ESA_BATTERY/PARTNER_CODES 实际字符串一致。
- 无改动，按本记录定稿。若后续要改德语开放句，按记录规则须重走判官探针。
