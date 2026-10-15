# /faq-download/ 重做文案对抗评审记录（票 #176，2026-10-15）

规则（AGENTS.md §2、§5）：客户可见文案一律初稿 → 评审意见 → 定稿记录在案；EN 先行、
DE 独立撰写非翻译（Sie 体、`de_DE_formal`）；基准 = linker-copywriting Hard Stops +
线上既有措辞与 `.po` 术语。定稿即模板里的字面量与 `.po` 的 msgstr
（`plugins/linker-commerce`）。

本票重做 `/faq-download/` 的框架层：页头（✦ + 标题 + 副标题 + 联系行 + 搜索框）、tab
栏、分区目录、类型芯片、分页器、搜索建议与各空态。**FAQ 问答内容本身不动**：16 条商务
规则是冻结内容（逐字搬进 `data/faq-trade.json`），产品问答来自已评审的 `_linker_faqs`
数据。原型（`docs/design/2026-10-15-faq-download-prototype`，变体 5，业主 2026-10-15
验收）的 EN 文案即本票的 EN 初稿来源——它是本轮设计讨论的可见成果；DE 逐条独立撰写，
与原型 DE 的差异逐条给出理由。

## 1. 页头（hero）

| 位置 | 初稿（原型 EN） | 评审意见 | 定稿 |
|---|---|---|---|
| H1 | `Answers and documents.` | 原型已验收；两句并列名词、句号收尾，无排比腔、无 slogan 公式（Hard Stop 9 清单无 `One X. One Y.` 之类结构，此项是「Answers and documents」一个并列短语）。工具页重设计范围，标题可自定。 | `Answers and documents.` |
| 副标题 | `Datasheets, manuals and trade rules for the equipment on file.` | 「on file」是站点既有口径（文档目录与 FAQ 一直说 on file / im Bestand），保留；三名词并列是内容清单不是排比修辞。 | 同初稿 |
| 联系行 | `Can't find what you're looking for?` + `Contact the Linker team` | 疑问句把主动方留给客户（Hard Stop 6 禁的是 `Get help checking…` 这类"乞求许可"；这里是陈述出路，不是让客户做作业）；链接名与页脚/页头联系入口的既有措辞一致。**定稿**：`Can't find what you're looking for? Contact the Linker team.` | 同初稿 |
| 搜索框 label（仅读屏） | `Search` | 与 aria 名一致，`Search questions and documents` 作 placeholder。 | `Search` |
| 搜索框 placeholder | `Search questions and documents` | 旧页是 `Search questions or models`——「models」在本页不成立（本页不按型号搜，型号搜索是目录页与 Genie 的事），改为本页真实对象：问题与文档。 | `Search questions and documents` |

## 2. tab 栏

| 位置 | 初稿 | 评审意见 | 定稿（EN / DE） |
|---|---|---|---|
| 两个 tab 名 | `FAQ` / `Documents` | AGENTS §3 用词：产品/分类不说 catalogue，文档说 documents；`FAQ` 是站点既有词（页脚、SEO 标题、旧页导航都是 FAQ）。DE 用站点既有 `FAQ` / `Dokumente`。 | `FAQ` / `Documents` · `FAQ` / `Dokumente` |
| tablist aria-label | `FAQ & documents` | 页面名；DE `FAQ & Dokumente`（与 `Templates::PAGES` 里的德语模板标题一致）。 | 同初稿 |

## 3. 目录、分区与卡片（区标题）

| 位置 | 初稿 | 评审意见 | 定稿（EN / DE） |
|---|---|---|---|
| 第一区（16 条商务规则） | `Before you order` | 旧页与冻结内容的既有说法（旧模板 heading `Before you order` / `Bevor Sie bestellen`），逐字保留——这是内容分区名，不是新文案。 | `Before you order` / `Vor der Bestellung` |
| 第二区（产品问答） | `Product answers` | 旧页 `Product answers` / `Produktantworten`，逐字保留。 | `Product answers` / `Produktantworten` |
| 文档区 | `Brands` | 文档按品牌分卡，区标题就是 `Brands` / `Marken`；原型同词。 | `Brands` / `Marken` |
| 空态（搜索无命中） | `Nothing on file matches that search.` + `Ask Genie` | 原型 EN 已验收；`Ask Genie` 是站点既有按钮词（`.po` 既有 msgstr `Genie fragen`）。不写"请换个词"（把作业推回客户）。 | 同初稿 / `Zu dieser Suche liegt nichts vor.` + `Genie fragen` |
| 空态（类型筛选后某品牌无文档） | `No documents of this type.` | 原型 EN 已验收。 | 同初稿 / `Keine Dokumente dieses Typs.` |
| 问题命中在答案里 | `In the answer` | 提示"命中在答案正文"的小字；原型同词。 | 同初稿 / `In der Antwort` |
| 搜索结果分组眉题 | `<品牌/分类> · <Trade rule｜Answer｜Document>` | 三个类别词都是既有词（`.po`：`Handelsregel`、`Antwort`、`Dokument`）。 | 同初稿 |
| 文档行类型徽章 | `Datasheet｜Manual｜Certificate｜Compatibility｜Warranty｜Brochure｜Document` | 全部沿用 `.po` 既有 msgstr（`Datenblatt｜Handbuch｜Zertifikat｜Kompatibilität｜Garantie｜Broschüre｜Dokument`），不新增词。 | 同既有 |
| 下载按钮 | `Download` | `.po` 既有 msgstr `Herunterladen`。 | 同既有 |
| 语言胶囊 | `EN｜DE｜MUL`（视觉）＋读屏全称 `English｜German｜Multilingual` | 视觉用代码、读屏用全称；全称沿用 `.po` 既有 msgstr（`Englisch｜Deutsch｜Mehrsprachig`）。 | 同既有 |

## 4. 脚本自绘的部分（`.po` 新串，15 条）

脚本自己印的字（计数、分页、空态、提示）全部来自 PHP 侧翻译，脚本不带任何客户可见串
（`tests/js/library-ui.test.mjs` 有一条断言守着这条）。EN 初稿照原型，DE 独立撰写：

| msgid（EN 定稿） | DE 初稿 | 评审意见 | DE 定稿 |
|---|---|---|---|
| `%d result` | `%d Ergebnis` | 单数计数。德语 Ergebnis/Ergebnisse 是站点既有复数对（原型 DE）。 | `%d Ergebnis` |
| `%d results` | `%d Ergebnisse` | 同上复数。 | `%d Ergebnisse` |
| `%d on file` | `%d im Bestand` | 「在库/在册」用 im Bestand，与 EN `on file`、旧页说明句 `im Bestand` 同一口径。 | `%d im Bestand` |
| `Nothing on file matches that search.` | `Zu dieser Suche liegt nichts vor.` | 不用 `Nichts gefunden`（生硬且像报错）；`liegt nichts vor` 是档案/在册语域，与 im Bestand 呼应。 | `Zu dieser Suche liegt nichts vor.` |
| `No documents of this type.` | `Keine Dokumente dieses Typs.` | 直陈，无感叹。 | `Keine Dokumente dieses Typs.` |
| `Ask Genie` | `Genie fragen` | `.po` 既有定稿，不重写。 | `Genie fragen` |
| `Clear search` | `Suche leeren` | 原型 DE；`leeren` 是站上搜索控件既有动词口径（对比原型 `Suche leeren`）。 | `Suche leeren` |
| `In the answer` | `In der Antwort` | 与眉题的类别词 `Antwort` 同词。 | `In der Antwort` |
| `Trade rule` | `Handelsregel` | AGENTS §3 与旧页 DE 均用 Handelsregeln（页头副标题 `Handelsregeln`）；单数 Handelsregel。 | `Handelsregel` |
| `Answer` | `Antwort` | `.po` 既有。 | `Antwort` |
| `Document` | `Dokument` | `.po` 既有。 | `Dokument` |
| `Previous` | `Zurück` | `.po` 既有分页词。 | `Zurück` |
| `Next` | `Weiter` | `.po` 既有分页词。 | `Weiter` |
| `Pages` | `Seiten` | 分页器 nav 的 aria-label；`Seiten` 是德语分页标准词。 | `Seiten` |
| `Questions` | `Fragen` | 建议下拉的分组名；与 tab 名 `FAQ` 并存不冲突（分组说的是"问题"这一类别）。 | `Fragen` |
| `Documents` | `Dokumente` | 建议下拉的分组名，与 tab 名同词（`.po` 既有）。 | `Dokumente` |
| `All` | `Alle` | 类型芯片的"全部"；`.po` 既有 `Alle`。 | `Alle` |
| `Document type` | `Dokumenttyp` | 类型芯片组的 aria-label；原型 DE 同词。 | `Dokumenttyp` |
| `Before you order` | `Vor der Bestellung` | 区标题的 `.po` 侧副本（rail / 芯片条 / 区标题三处同一串）。 | `Vor der Bestellung` |
| `Product answers` | `Produktantworten` | 同上。 | `Produktantworten` |
| `Brands` | `Marken` | 同上。 | `Marken` |

DE 与原型 DE 只有一处措辞不同：原型空态写 `Zu dieser Suche liegt nichts vor.`（本票照
抄）；其余原型 DE 串（`Suche leeren`、`Dokumenttyp`、`Alle`、`Seiten`、`Fragen`）逐条
核对后直接采用——原型 DE 是业主验收过的可见成果，且与 `.po` 既有术语一致。

## 5. 未改动的内容（不在本票文案范围内）

- 16 条商务规则的问题与答案：冻结内容，逐字搬进 `data/faq-trade.json`（含其中一条答案
  里的 `<a href="/contact/?intent=support">Open Warranty & Replacements</a>` 链接）。
- 272 条产品问答：`_linker_faqs` 字段，已经过 #15 的对抗评审。
- 文档标题与语言、`covers …` 句：来自产品数据与 `.po` 既有串（`gilt für %s`）。

## 6. 检查（本轮跑过的门）

- `python3 tools/checks/i18n-coverage.py` → `clean`（新 15 串全部有 DE 定稿）。
- `msgfmt --check-format -o …mo …po` → 通过，`.mo` 与 `.po` 同步重生成。
- `plugins/linker-commerce`：`phpcs -q`、`phpstan analyse`、`phpunit`（1027 tests）全绿。
- `node --test plugins/linker-commerce/tests/js/*.test.mjs`（含 `library-ui.test.mjs` 19 条）全绿。
