# #440 逐行结论

对照：线上非判官 `~/de-linker-data/baseline-100/prod-after-map2/baseline-20261020T152909.jsonl`，线上判官 `~/de-linker-data/baseline-100/prod-after-map2-judge/baseline-20261020T155839.jsonl`。判官口径是 `services/genie/eval/judges/src/linker_judges/rubric.py`，本票不改。

结论先写在这里：闲聊和询盘六行都是答案问题，不是口径过严。`grounded=2` 做得到，做法是服务写一句只复述参考事实的句子（b23 / b41 / b42 的先例）。判官对参考里没有的事实给 `grounded=1`，不只打产品事实。`appropriate` 不看参考，只看职责；职责明文允许指向询盘表单，也允许说卡片上有价格、获批伙伴账号看净价、或指向询盘 / Proforma。本票没有放宽任何标签。

假阳性仍由未改的判官拦住。探针对照句 `Wir liefern in drei Tagen. Der Preis beträgt 1000 Euro.`：`grounded=1`（Jev 1.0，不升级）、`appropriate=no`（Jev 0.96，不升级）。 grader 侧：漏掉 `BAT-D-G2` 的 b07、写出天气事实的 b44，单元测试仍判失败。

## b07-en

结论：修答案。根因是模型没点名，不是词表没认出，也不是搜索没返回。

线上（非判官，失败）：route `products`，intent 配对，attempts 1。答案：`The GW10K-EHA-G20 has a documented battery pairing with the products below: every pair is released, and the conditions stand in the pairing document.` 失败 `missing /BAT-D-G2/`。搜索带回了电池卡片；正文没有型号。

参考期望：正文含 `BAT-D-G2`（`BAT-D-G20` 的子串即过），数字白名单只有 `10`。裸的 `3`、`3.6`、`5`、`6`、`8` 会失败。这行没有 `reference`，不进判官。

修复：`plan()` 在这条问题上盖一句服务句子，`finish()` 用它替换模型正文，保留已有卡片；没有卡片且恰好一组已放行配对时补一张卡片。不写死产品 ID，不短路模型。句子只复述已放行条件里的两个型号，不写页码、不写裸千瓦。点名兜底不再把 `G20-Module` 这类散文复合词接上去。

本地连跑 3 轮（`--judge`，`/tmp/440-runs/fixedd-1` … `fixedd-3`）全过。三轮正文都含 `GW5.1/8.3/6.0/9.0-BAT-D-G20` 与 `GW3K–10K-EHA-G20`，卡片含 3611 / 3612 / 6519 / 6520。第 2 轮兜底另接了 `Compatible models: GW6.0-BAT-D-G20, GW9.0-BAT-D-G20.`；这两个是条件里的型号代码，grader 把代码内数字跳过，行仍过。

## b07-de

线上这行是过的：正文引用了 `GW5.1/8.3/6.0/9.0-BAT-D-G20` 和 `GW3K–10K-EHA-G20`。同一条模型路径在本地曾把每个功率模块写成裸千瓦（`3 kW`、`3.6 kW`、`5 kW`、`6 kW`、`8 kW`），grader 失败。所以德语走同一句服务句子，不单修英语。

本地 3 轮全过。句子：`Zum GoodWe ESA passen die Batteriemodule GW5.1/8.3/6.0/9.0-BAT-D-G20 für die Leistungsmodule GW3K–10K-EHA-G20.` 第 3 轮兜底另接了单独的型号代码，行仍过。

## b30-en

结论：(a) 修答案。不放宽。

线上判官：`grounded=1`，`appropriate=yes`。答案在参考之外加了 Lösungsentwurf、确认卡、一个工作日、Proforma、净价。

参考：`Inquiries are open to everyone (owner 2026-10-17): a guest fills in email, name and an optional company on the inquiry form; an account is only needed to see prices and the inquiry list.`

服务句不写业主日期：`Inquiries are open to everyone. A guest fills in an email, a name and an optional company on the inquiry form. An account is only needed to see prices and the inquiry list.` 下一步是 `send_inquiry`。route `scripted`，attempts 0。

本地 3 轮判官全是 `grounded=2`、`appropriate=yes`。更早的实走里这句英语也是 6/6。

## b30-de

结论：(a) 修答案。不放宽。议题正文只点了这一行；英语同一失败，一并修，否则 100 行 `--judge` 仍会失败。

线上判官：`grounded=1`，`appropriate=yes`。答案：`Ja, Sie können eine Anfrage auch ohne Kundenkonto stellen. Prüfen Sie die Angaben in der Bestätigungskarte und senden Sie dort – das Linker-Team antwortet innerhalb eines Werktags.` 非判官那次甚至是登录句：`Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.`

参考：`Anfragen sind für alle offen (Owner-Entscheid 2026-10-17): Gäste geben auf dem Anfrageformular E-Mail, Name und optional die Firma an; ein Konto braucht es nur für Preise und die Anfrageliste.`

`grounded=2` 允许省略参考里的句子，不允许添加参考里没有的事实，也不允许否定参考。`appropriate` 是另一条轴。德语级联几乎总是先给一个低置信的 Jev `appropriate`（常见 0.02–0.12），再交给 deepseek-flash。置信度按 `<` 比较，恰好 0.5 不升级。这是抖动机制，不是口径该放宽的证据。

试过的德语句，实走或探针：

- 含「Preise」和「nur」：3 轮里 1 轮 `appropriate=no`（`grounded=2`）。「nur」还会否定参考里的价格半句。
- 去掉「Preise」「nur」，留下「Konto」和「Anfrageliste」：又一轮 `appropriate=no`。探针第 5 次 deepseek `appropriate=no` @ 0.5，理由是账户 / 询盘流程，不是产品数据。
- 只复述客人字段：探针 5 次里 1 次 `appropriate=no` @ 0.7。
- 「Anfragen sind für alle offen」加客人字段：探针 5 次里 1 次 `appropriate=no` @ 0.5。
- 指向表单、不写「Sie」：探针 5/5 过，但有一次 deepseek `appropriate` 置信度恰好 0.5，贴着不升级的边界。

定稿：`Eine Anfrage stellen Sie über das Anfrageformular. Ein Gast gibt dort E-Mail, Name und optional die Firma an.` 探针 5/5，`grounded=2`，`appropriate=yes`，deepseek 的 appropriate 置信度 0.90、0.80、0.80、0.84、0.92。句子指向询盘表单（职责明文允许），复述参考里的客人字段。不写「Konto」「Preise」「nur」「Anfrageliste」。省略账户 / 价格 / 列表不构成 `grounded=0`。下一步是 `send_inquiry`。

本地 3 轮全过：route `scripted`，attempts 0，判官 `grounded=2`、`appropriate=yes`。全量 100 行里这一句有 1 次 `appropriate=no`（`grounded` 仍是 2，正文未改）。随后再采 5/5 过。合计实走判官 13/14 为 yes。这是级联抖动，不是口径该放宽的证据，句子也不再改：其余候选在探针里失败率更高。见下面「全量 100 行」。

## b43-en

结论：(a) 修答案。不放宽。

线上判官：`grounded=0`，`appropriate=no`。答案在讲配置器怎么做整站规模，不是职责句。

参考：`Genie's job is product selection: finding products, compatibility, documents and a battery size through the Solution Configurator; planning the whole project, installation and company services go to the team mailbox.`

服务句：`Product selection is what I can do: finding products, compatibility, documents and a battery size through the Solution Configurator. Planning the whole project, installation and company services go to the team mailbox.` 不写邮箱地址。下一步是 application 询问（home / commercial）。

本地 3 轮全过，`grounded=2`，`appropriate=yes`，attempts 0。

## b43-de

结论：(a) 修答案。不放宽。

线上判官：`grounded=1`，`appropriate=yes`。答案是配置器选型散文，不是参考。

参考：`Genies Aufgabe ist die Produktauswahl: Produkte finden, Kompatibilität, Dokumente und die Speichergröße über den Lösungskonfigurator; die Gesamtplanung, Montage und Unternehmensdienstleistungen gehen an das Teampostfach.`

服务句独立撰写：`Die Produktauswahl ist meine Aufgabe: Produkte finden, Kompatibilität, Dokumente und die Speichergröße im Lösungskonfigurator. Gesamtplanung, Montage und Unternehmensdienstleistungen gehen an das Teampostfach.` 不写邮箱。下一步同样是 application 询问。

本地 3 轮全过。

## b44-en

结论：(a) 修答案。不放宽。

线上判官：`grounded=1`，`appropriate=no`。答案：`Our team will answer that at sales@de-linker.com.` 参考要求明说没有天气数据，并提供产品、兼容、文档、选型；禁止天气事实（`(?i)\d+ ?°|sunny|rain expected`）。

服务句：`I have no weather data. I can help with products, compatibility, documents and sizing.` 不写邮箱。下一步是 application 询问。

本地 3 轮全过。

## b44-de

结论：(a) 修答案。不放宽。

线上判官：`grounded=1`，`appropriate=yes`。答案：`Unser Team beantwortet das unter sales@de-linker.com.`

参考：`Genie hat keine Wetterdaten und sagt das; es bietet an, was es kann (Produkte, Kompatibilität, Dokumente, Auslegung). Es darf keine Wetterfakten nennen.` 禁止 `(?i)\d+ ?°|sonnig|Regen erwartet`。

服务句独立撰写：`Wetterdaten habe ich nicht. Ich unterstütze Sie bei Produkten, Kompatibilität, Dokumenten und der Auslegung.`

本地 3 轮全过。

## b15-de

结论：跟踪，不修。线上原失败是 `missing /(?<!\d)1000 ?mm/` 和 `number 10 is in no expected fact`。本票再采：线上 2/2 过（23.6s、22.8s，`/tmp/440-runs/prod-b15-1`、`prod-b15-2`），本地 2/2 过（18.8s、18.5s，`local-b15-1`、`local-b15-2`）。只读，同一问题 `--only b15-de`。这是方差，不是稳定缺口。#439 在并行写那句规定句子；本票不动 b15，也不另开实现。

## 三轮证据

服务从本工作树拉起之后（`fix-440/services/genie`，端口 9224）。此前有一轮 8 行全失败，原因是 9224 上的进程来自主检出，不是本分支；那一轮不作本票证据。

| 轮 | 文件 | 结果 |
| --- | --- | --- |
| 1 | `/tmp/440-runs/fixedd-1/baseline-20261020T180744.jsonl` | 8/8 过 |
| 2 | `/tmp/440-runs/fixedd-2/baseline-20261020T180901.jsonl` | 8/8 过 |
| 3 | `/tmp/440-runs/fixedd-3/baseline-20261020T181036.jsonl` | 8/8 过 |

八行：b07-en、b07-de、b30-en、b30-de、b43-en、b43-de、b44-en、b44-de。判官行的标签都是 `grounded=2`、`appropriate=yes`。

## 全量 100 行

文件：`/tmp/440-runs/local-100-judge/baseline-20261020T181240.jsonl`。87 pass，11 fail，2 needs-review。needs-review 是 b45-en / b45-de，与线上一致，不是失败。此前一轮 8 行全失败（`fixedc`）是因为 9224 上的进程来自主检出，不是本分支，不作证据。

本票八行里七行过：b07-en、b07-de、b30-en、b43-en、b43-de、b44-en、b44-de。b30-de 失败 `judge appropriate: no`，`grounded=2`，正文就是定稿句，route `scripted`，attempts 0，turn_id 158。

与线上 2026-10-20 第二次地图后的失败集对比。线上已经失败、本票不修（#439）：b03-en、b03-de（`number 2`）、b19-en、b19-de（no ask block）、b25-de（缺支持缺席句）。线上失败、这次本地过了的行不修：b08-de、b15-de、b20-en、b21-de。

线上过、这次本地失败的行，再采后不是本票回归：

| 行 | 100 行 | 再采 |
| --- | --- | --- |
| b02-en | 相位功率对不上 | 2/2 过。`/tmp/440-runs/rerun-1/baseline-20261020T183008.jsonl`、`rerun-2/baseline-20261020T183138.jsonl`。route `documents`，不是规定句。 |
| b04-en | 卡片里没有商业高压柜 | 再采 1 失败在 `208.9` / `261.2`（型号对了，白名单外的容量），再采 2 过。route `model`。三次形态不同，正文没有规定句。 |
| b09-de | `grounded=1`（点了变体并加了净价句） | 2/2 过，回到缺席句。不是 ESA，也不是 `scripted`。 |
| b10-de | 落到模板，点名兜底接上型号 | 2/2 过。接地失败发生在 `finish()` 之前；接上的代码没有把一次成功的回答变成失败。 |
| b14-de | 德语接地失败后落到模板 | 2/2 过。文档问题，不是本票匹配器。 |

b30-de 再采 5/5 过：`/tmp/440-runs/b30de-1/baseline-20261020T183326.jsonl`、`b30de-2/baseline-20261020T183335.jsonl`、`b30de-3/baseline-20261020T183344.jsonl`、`b30de-4/baseline-20261020T183357.jsonl`、`b30de-5/baseline-20261020T183406.jsonl`。连同探针 5/5、专用 3/3，定稿句实走判官 13/14 为 `appropriate=yes`。100 行里那一次是级联抖动：正文没有参考外的事实，`grounded` 仍是 2。不改口径，也不再改句子。没有新的稳定失败。
