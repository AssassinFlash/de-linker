# #251 零件清单文案对抗评审记录

规则：AGENTS.md §3（产品、产品分类；不说 catalogue / article / cart；德语 Sie 体；禁"不是…而是…"与三连排比）、
linker-copywriting Hard Stops；EN 先定稿，DE 独立撰写（不逐字翻译）；基准为线上既有措辞与
`plugins/linker-tools/languages/linker-tools-de_DE_formal.po` 的术语。

范围：
1. 服务编写的整轮句子（`services/genie/src/linker_genie/parts.py` 的 `SUMMARY`）——数学由代码写，模型不参与；
2. `PartsCard` 的界面文字（`.po` 的 msgid / msgstr）；
3. 附件拒绝文案（新增 CSV / Excel 后）；
4. 首页预览卡的"上传清单"建议与清单选择提示（`Preview.php`、`App.tsx`）。

评审方式：初稿由实现会话写；独立评审代理（只读）对照规则逐条审，意见采纳与否记在下表；定稿即代码与 `.po` 的现状。

## 英文（先定稿）

**服务句子**（`parts.SUMMARY["en"]`）：

- `I checked your list: {matched} of {total} lines match our products.`
- `I checked your list: one of {total} lines matches our products.`（恰一行命中）
- `I checked your list: the line matches our products.`（只有一行）
- `I checked the first part of your list: {matched} match our products.` / `…: one matches our products.`（清单被截断：行数或字符）
- `I could not match any line of your list to our products.`
- `I could not match any of the rows I read of your list to our products.`（截断）
- `One line needs your confirmation.`
- `{count} lines need your confirmation: one at a time.`
- `One line is not in our product range.`
- `{count} lines are not in our product range.`
- `You can add the confirmed product to your solution draft.`（只一个商品）
- `You can add the confirmed products to your solution draft.`

**卡**：

- `Your parts list`
- `In our range: %s`
- `Not in our range.`
- `Skipped.`
- `Which model does this line mean?`
- `This line needs your confirmation.`
- `%d ×`
- `Row %1$d: %2$s`（候选芯片发回的消息）
- `Type the model`
- `Row %d: skip`
- `Skip this line`
- `Add the product to the solution draft` / `Add %d products to the solution draft`
- `Adding…` / `In your solution draft.` / `Sent, but the solution draft does not show the change yet.` / `Not everything was added. Try again.`

**附件与入口**：

- `This file type cannot be sent. Genie reads photos (JPEG, PNG, WebP or HEIC), PDFs and parts lists (CSV or .xlsx).`
- `This file is too large. A PDF can be up to %1$d MB, a photo up to %2$d MB, an Excel list up to %3$d MB and a CSV list up to %4$d MB.`
- `The files are too large in total. Use fewer or smaller files.`
- `Turn a parts list into products`
- `Genie checks every line of a parts list against our products. You can use a CSV or Excel (.xlsx) file, or a photo of the list.`
- `Choose a file`

## 德语（独立撰写，Sie 体）

- `Ich habe Ihre Liste geprüft: {matched} von {total} Zeilen passen zu unseren Produkten.`
- `Ich habe Ihre Liste geprüft: Eine von {total} Zeilen passt zu unseren Produkten.` / `…: Die Zeile passt zu unseren Produkten.`
- `Ich habe den ersten Teil Ihrer Liste geprüft: {matched} passen zu unseren Produkten.` / `…: Eine passt zu unseren Produkten.`
- `Ich konnte keine Zeile Ihrer Liste einem unserer Produkte zuordnen.`
- `Ich konnte keine der gelesenen Zeilen Ihrer Liste unseren Produkten zuordnen.`（截断）
- `Eine Zeile braucht Ihre Bestätigung.`
- `{count} Zeilen brauchen Ihre Bestätigung: eine nach der anderen.`
- `Eine Zeile ist nicht in unserem Sortiment.`
- `{count} Zeilen sind nicht in unserem Sortiment.`
- `Sie können das bestätigte Produkt Ihrem Lösungsentwurf hinzufügen.`（只一个商品）
- `Sie können die bestätigten Produkte Ihrem Lösungsentwurf hinzufügen.`
- `Ihre Teileliste`
- `In unserem Sortiment: %s`
- `Nicht in unserem Sortiment.`
- `Übersprungen.`
- `Welches Modell ist mit dieser Zeile gemeint?`
- `Diese Zeile braucht Ihre Bestätigung.`
- `%d ×`
- `Zeile %1$d: %2$s`
- `Modell eingeben`
- `Zeile %d: überspringen`
- `Diese Zeile überspringen`
- `Das Produkt dem Lösungsentwurf hinzufügen` / `%d Produkte dem Lösungsentwurf hinzufügen`
- `Wird hinzugefügt …` / `Im Lösungsentwurf.` / `Gesendet, aber der Lösungsentwurf zeigt die Änderung noch nicht.` / `Nicht alles wurde hinzugefügt. Bitte erneut versuchen.`
- `Dieser Dateityp kann nicht gesendet werden. Genie liest Fotos (JPEG, PNG, WebP oder HEIC), PDFs und Teilelisten (CSV oder .xlsx).`
- `Diese Datei ist zu groß. Ein PDF darf bis zu %1$d MB haben, ein Foto bis zu %2$d MB, eine Excel-Liste bis zu %3$d MB und eine CSV-Liste bis zu %4$d MB.`
- `Die Dateien sind insgesamt zu groß. Verwenden Sie weniger oder kleinere Dateien.`
- `Teileliste in Produkte umwandeln`
- `Genie gleicht jede Zeile einer Teileliste mit unseren Produkten ab. Sie können eine CSV- oder Excel-Datei (.xlsx) oder ein Foto der Liste verwenden.`
- `Datei auswählen`

## 评审意见与采纳

独立评审代理（只读，对照 AGENTS.md §3、既有 `.po` 与 249 评审）逐条审；上文的定稿已是采纳后的现状。

| # | 意见 | 结果 |
|---|---|---|
| 1 | 入口正文"matches every line"承诺了代码做不到的事（行还会是 uncertain / missing），且正文用祈使句布置任务 | **采纳**：改为 "checks every line … against our products. You can use …"；DE "gleicht … ab. Sie können … verwenden." |
| 2 | 服务主句在单数计数下不成立（"1 of 1 lines"、"1 von 5 Zeilen passen"） | **采纳**：`lead_single` / `lead_one` 两个单数分支，EN/DE 各一 |
| 3 | 加入句只写复数，且 `matched > 1` 但去重后只有一个商品时与按钮不一致 | **采纳**：按 `add.products` 分支 `add_one` / `add` |
| 4 | 客户可见新文案不用 em/en dash | **采纳**：两处改为冒号 |
| 5 | "This file is too large" 也用于整轮超限（`turn_size`），且单文件上限没提照片 | **采纳**：拆出 `turn_size` 一句（"The files are too large in total…"）；单文件句列出 PDF/照片/Excel/CSV 四个上限 |
| 6 | "does not show it yet. Please check." 对多个商品用 "it"，并把检查推给客户 | **采纳**："does not show the change yet."，去掉 "Please check" |
| 7 | "Not added." 在部分成功时是假话 | **采纳**："Not everything was added. Try again."；并让 retry 状态的按钮可再次点击 |
| 8 | 截断清单的主句与 none 句声称读了整份清单 | **采纳**：截断时用 "the first {rows} lines" 的主句与 none 句，删掉单独的最后一句 |
| 9 | "Which model is this?" 预设只有一个型号，而 uncertain 行可能是多个 | **采纳**："Which model does this line mean?" / "Welches Modell ist mit dieser Zeile gemeint?" |
| 10 | 卡上 "In our range" 与 "Not in our product range" 用词不一 | **采纳**：否定句改为 "Not in our range."（德语已一致，保留）；"In our range: %s" 与铭牌卡共用，不改 |
| 11 | "Excel" 比代码宽（只收 .xlsx，旧 .xls 拒绝） | **采纳**：类型句与入口正文写明 "(CSV or .xlsx)" / "(CSV oder .xlsx)" |
| 12 | `answer()` 在 matched=0 且 uncertain>0 时只说不匹配、不提问 | **采纳**：该分支先说确认句，再说缺失句 |
| 13 | 空清单（total=0）没有专门一句 | **不采纳**：CSV/Excel 解析不出行时 reading 直接 `unreadable_list`（附件卡说读不到），粘贴清单也过不了 `looks_like_list`；`total=0` 不可达。保留防御性 `none` 句 |
| 14 | "Teileliste" 是否正确（而非 Stückliste） | **保留 Teileliste**：AGENTS.md §3 的 Stückliste 指方案内的物料清单；客户上传的是 Teileliste。`.po` 的 Stückliste 只出现在配置器输出 |
| 15 | "In our solution draft" 与产品卡共用 | **保留**：同一状态、同一文案，不再分叉 |

## 裁定

以上定稿即 `services/genie/src/linker_genie/parts.py` 的 `SUMMARY`、`PartsCard.tsx` / `AttachmentChips.tsx` / `App.tsx` 的 msgid 与 `languages/linker-tools-de_DE_formal.po` 的 msgstr。评审第 13 条不采纳的理由已写入上表；其余全部采纳。德语为独立撰写（Sie 体），未逐字翻译英语。

## 评审第 1 轮（PR #345）

| 位置 | 初稿 | 评审意见 | 定稿 |
|---|---|---|---|
| 截断主句 | "I checked the first {rows} lines …" / „Ich habe die ersten {rows} Zeilen … geprüft" | 60 000 字符的上限可能在 200 行以内截断，写死 200 行会与事实不符；但必须让客户知道只读了清单的一部分 | **"I checked the first part of your list: …" / „Ich habe den ersten Teil Ihrer Liste geprüft: …"**；none 句同步改为 "the rows I read" / „der gelesenen Zeilen" |
| DE 截断单数 | „…: eine passt zu unseren Produkten." | 冒号后是完整句，首字母大写 | **„…: Eine passt zu unseren Produkten."** |
| 失败清单的卡 | — | 不可读的 CSV/Excel 之前以 document 到达壳，卡不给重新选择文件的动作；文案本身不变，动作与 kind 在服务端修正 | 文案保持；端到端见 e2e 的 broken.xlsx |
| 旧版 .xls | 类型句与入口正文写 "Excel (.xlsx)" | 代码只收 .xlsx；正文已明写 .xlsx，规格与 PR 再记录 .xls 不收（需业主裁定才加依赖） | 保留 |

其余第 1 轮意见是代码/测试/安全项，不改客户文案；见 PR。
