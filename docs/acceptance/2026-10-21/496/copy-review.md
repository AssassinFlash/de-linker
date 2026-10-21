# #496 报告页“Ask Genie”·文案对抗评审记录

规则：AGENTS.md §3 用词（Product / 产品分类 / Solution draft = Lösungsentwurf；saved solution = 正确的客户对象，不写作 Solution draft；德语 Sie 体、de_DE_formal）；禁“不是…而是…”与三连排比；
linker-copywriting Hard Stops；两个插件的既有 `.po` 术语；EN 先定稿，DE 独立撰写（不逐字翻译）。
基准面：设计报告（`services/engine/src/linker_engine/texts.py`）与账户页的 “Saved solution / Gespeicherte Lösung”、
“Save solution / Lösung speichern”、“Open saved solution / Gespeicherte Lösung öffnen”。

评审方式：初稿由实现会话写入代码；随后由一个**独立只读评审代理**对照上述规则、`.po`、报告文案与实现代码做对抗复核。
评审意见按条目返回，本文的记录是评审后的定稿。定稿即代码里的 msgid / msgstr（`plugins/linker-tools/languages/linker-tools-de_DE_formal.po`，
`just i18n-tools` 生成 JSON），以及 `solution.py` 的 LABELS 与两份 `system.md` 的模型规则。

状态：**Coordinator sign-off: approved (2026-10-21)**（见文末）。

## 逐条

| # | 位置 | 初稿 EN / DE | 评审意见 | 定稿 EN / DE |
|---|---|---|---|---|
| A | 报告页按钮 | Ask Genie / Genie fragen | 既有 `.po` 字符串（dock 与报告共用），德语的不定式形式已是站点惯例 | 不变 |
| B | 保存中按钮 | Opening Genie… / Genie wird geöffnet… | 德语少了 `.po` 里所有忙碌句都有的省略号前空格（“PDF wird erstellt …”“Wird gespeichert …”） | **Opening Genie… / Genie öffnet sich …** |
| C | 保存失败（报告页） | The solution could not be saved. Try again. / Die Lösung konnte nicht gespeichert werden. Versuchen Sie es erneut. | 票面要求复用 C31 既有失败句；评审指出它对确定性失败（报告 PDF 超过上传上限）不是真实可重试路径。该句与 Save solution 按钮（#14 既有行为）共用，本票不改保存错误分类，原句保留并在此记明限制 | 不变（复用 C31） |
| D | 访客提示 | Your saved solution stays with this session. Sign in or create an account to keep it and ask Genie about its figures. / Ihre gespeicherte Lösung bleibt in dieser Sitzung. Melden Sie sich an oder legen Sie ein Konto an, um sie zu behalten und Genie zu ihren Kennzahlen zu fragen. | “登录后问 Genie”没有承载：账户页没有把 `solution_id` 交给 Genie 的入口，`linker/read-solution` 只从报告页的交接拿引用。访客的保存留在会话（48 小时）并在登录时 `claim()` 入账，因此只需承诺“留住”；德语 “Sitzung” 是技术词，`.po` 对访客会话用 “Browser” | **Your saved solution stays in this browser for now. Genie reads a saved solution only when it is in your account. Sign in or create an account to keep it. / Ihre gespeicherte Lösung bleibt vorerst in diesem Browser. Genie liest eine gespeicherte Lösung nur, wenn sie in Ihrem Konto liegt. Melden Sie sich an oder legen Sie ein Konto an, um sie zu behalten.** |
| E | 按钮发送的首问 | What does my saved solution say? / Was sagt meine gespeicherte Lösung? | 给方案安上“说话”的动作；德语是逐字直译。改为问“有哪些数字”，仍含 solution / Lösung（`route._SOLUTION_WORDS` 的确定性触发保留） | **What are the figures in my saved solution? / Welche Kennzahlen enthält meine gespeicherte Lösung?** |
| F | 系统提示词段落（EN/DE） | （初稿见 git 历史）含 “dock/Dock”、与报告不一致的标签（usable storage、self-sufficiency 不带 with storage）、对必须精确引用的数字说 “in your own words”；德语 “raten Sie ihre Kennzahlen nie” 有“建议”歧义 | 用报告的标签（annual yield / Jahresertrag、proposed usable capacity / vorgeschlagene nutzbare Kapazität、self-sufficiency with storage / Autarkiegrad mit Speicher），去掉 dock 与“用自己的话”，隐私句改为“只描述 read-solution 返回的这一份”，加上“不要为此调用 handoff-team” | **见 `services/genie/prompts/en/system.md` 的 “The saved solution:” 段与 `de/system.md` 的 “Die gespeicherte Lösung:” 段（定稿即文件内容）** |
| G | login_required 句 | “a saved solution can be read only for a signed-in customer” / “nur für angemeldete Kundinnen und Kunden lesbar … bitten Sie um die Anmeldung” | 原句读成“任何登录客户都能读”，而不是“本人”；德语 “bitten Sie um die Anmeldung” 可读成索要登录凭据；补 “handoff-team 不用于此” | **“signing in lets you read the saved solution from the customer's account, and ask them to sign in. Do not call handoff-team for this.” / “dass Sie die gespeicherte Lösung nach der Anmeldung aus dem Konto der Kundin oder des Kunden lesen können, und bitten Sie die Kundin oder den Kunden, sich anzumelden. Rufen Sie handoff-team dafür nicht auf.”** 同步在 `solution.py` 的 `RULE` 与 `route.py` 的 `SOLUTION_HINT` |
| H | 服务端标签（模型读取的数据） | EN: PV yield per year / PV yield mean；其余同报告 | EN 两个产量标签不是报告用语（报告是 “Annual yield, range over …” 与 “Mean annual yield”）；德语已与报告一致 | **EN: Annual yield / Mean annual yield / saved on；DE 不变（Jahresertrag / Mittlerer Jahresertrag / gespeichert am）** |
| I | 服务端状态句（模型读取的数据） | The stored inputs have no complete solution at the moment. / Für die gespeicherten Eingaben gibt es derzeit keine vollständige Lösung. | 模型读的数据句，不是客户可见文案；说法与报告的 no_candidate 一致，不承诺数字。评审确认它是数据、不是第二套客户句；保留在服务端 | 不变 |

## 评审提出而本票不采用的两点

1. **新增“登录”动作以满足“每轮一个可点下一步”**：不动。访客没有 `solution_id`（会话保存 `id` 为 0，尚无文章），报告页在访客保存后只显示登录提示、不向 Genie 发轮次；`login_required` 只在令牌失效时出现，而令牌 TTL 120 秒、壳的整轮预算 60 秒，一轮内不会失效。为不可达分支新增 `schema.ActionName` 与服务端动作超出本票（模型路由与动作集合不变）。提示词明确“请对方登录”即可。
2. **`Werktag` → `Arbeitstag`**：既有句（`system.md`、`texts.py`、`template.py`）与本票无关；#234/#243/#250 已定 “business day / Arbeitstag”，但那是另一处修订，本票不改既有承诺句，避免把无关文案混进 #496。

## 未做到的

- 独立评审代理是只读的，未改文件；定稿由实现会话落盘，评审者与作者不是同一代理，但也不是业主本人。
- 没跑读屏实测；新按钮与提示沿用配置器既有的 `linker-button` / `role="status"` 结构。
- 访客提示的截图文案为定稿；C 的“确定性失败仍显示 Try again”是已知的既有保存行为，未在本票修。


## 协调者对抗评审（2026-10-21）

逐条复核定稿列：A 复用既有 .po；B 补德语省略号前空格（与站点忙碌句惯例一致）；C 复用 C31 并如实记录"确定性失败不可重试"的限制（本票不改保存错误分类，正确）；D 是本轮最重要的修正——删掉"登录后问 Genie"的无承载承诺，改为只承诺会话保存+claim 入账，并把 Genie 读取的前提（在账户里）说清，德语 Sitzung→Browser 与 .po 一致；E 问数字不问"方案说话"；F 提示词与报告标签逐一对齐、隐私句限定为 read-solution 返回的这一份；G 本人限定+登录请求+handoff-team 禁用；H 产量标签对齐报告用语。两处不采用的理由均成立（访客无可读分支、状态句是数据非客户句）。与 .po/solution.py/prompts 的实际字符串一致。Hard Stop 1–9 与 §3 复核通过。无改动，定稿。
