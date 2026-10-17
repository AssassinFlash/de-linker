# #257 文档引用文案对抗评审记录

范围：文档数字在回答里的写法（`figures.py` 的 `localize`）。§1、§2 记录的来源行已经不存在：#233 合并后，引用改由服务端加成文档链接（#233 的文档块），链接标签“标题 · p. N”的用词评审在 `docs/acceptance/2026-10-17/233/copy-review.md`；两份的结论一致（多页英文用 pp.，德文统一用 S.）。§1、§2 留作记录。模型自己写的句子不在本记录内。规则：AGENTS.md §3（不说 article / catalogue / cart；德语 Sie 体、de_DE_formal）；基准是线上已有的引用写法与 `.po` 术语。EN 先定稿，DE 独立撰写。每处：初稿 → 评审意见 → 定稿。

## 1. 来源行的标签（已被 #233 的文档链接取代）

- EN 初稿：`Source: SAJ H2 10-30K user manual, German and English (covers the H2-10K-T3), p. 37`；多份文档 `Sources: …; …`。
  评审：考虑过 `Reference`、`See`、`Documents`。`See` 是指令，客户读成"去看"，但这一行是在交代出处；`Documents` 和产品页的"Documents"标签页撞名，读者会以为是一组下载链接。`Source` 是技术文档引用的惯用词；一份用单数，多份用复数，不写 `Source(s)`。前面空一行，让它读作脚注、不读作正文。分号分隔文档，因为文档标题里本身就有逗号。**定稿**：`Source: <标题>, p. N` / `Sources: <标题 A>, p. N; <标题 B>, pp. N, M`。
- DE 初稿：`Quelle: SAJ H2 10-30K Handbuch, Deutsch und Englisch (gilt für den H2-10K-T3), S. 37`；多份 `Quellen: …; …`。
  评审：德语独立写，不从英语翻：`Quelle` / `Quellen` 是德语技术文本标出处的通用写法，没有 `Fundstelle` 那么生硬，也没有 `Siehe` 的指令口气。标题用 `title_de`（规格 10 的双语标题），这一行就不会出现英文标题。**定稿**：`Quelle: <Titel>, S. N` / `Quellen: <Titel A>, S. N; <Titel B>, S. N, M`。

## 2. 页码缩写（已被 #233 的文档链接取代）

- EN 初稿：单页、多页都写 `p.`。
  评审：英文惯例里多页写 `pp.`（`pp. 37, 38`）；trial run 里出现过 `p. 1, 4`，读起来像笔误。改成按页数取单复数。**定稿**：`p. 37` / `pp. 37, 38`。
- DE 初稿：`S.`
  评审：德语单页、多页都写 `S.`（`S. 37, 38`），没有复数缩写；不用 `Seite` 全拼，这一行要短。**定稿**：`S. 37` / `S. 37, 38`。

## 3. 回答里的文档数字：单位与日期

数字的值照文档原样写（规格 10「引用与核验」）。只有词单位和日期跟着回答的语言走，因为英文文档的数字也会出现在德语回答里（trial run：`10 years` 出现在德语句子中）。

- EN 初稿：照文档原样（`10 years`、`1 st January 2026`）。
  评审：`1 st January 2026` 是 PDF 抽取出来的样子（上标被拆开），放在英文回答里就是错字。日期统一写成 `1 January 2026`（英式日期，与站点的欧洲客户群和德国卖方一致）；词单位英文照原样。**定稿**：`10 years`、`12 months`、`1 January 2026`；德文来源的 `Jahre` / `Monate` / `Zyklen` 在英文回答里写成 `years` / `months` / `cycles`。
- DE 初稿：`10 Jahre`、`12 Monate`、`1. Januar 2026`。
  评审：数字之后要不要用与格（`10 Jahren`），取决于句子，服务端看不到语法位置；用主格复数，模型自己会围绕它造句（试题第 7 题：`eine beschränkte Garantie von 10 Jahre` 是这条规则带来的不自然处）。另一个办法是让模型把单位写在占位符外面，但这样就丢了"值原样来自文档"这个保证。接受主格，代价记在这里。日期写 `1. Januar 2026`（德语惯例：日后加句点、月份全拼）。**定稿**：`10 Jahre`、`12 Monate`、`1. Januar 2026`、`Zyklen`。

## 4. 不在本记录的

- 模型写的说明句（"Our documents do not state …" / "unsere Dokumente nennen … nicht"）的措辞由提示词约束（`prompts/{en,de}/system.md` 的"Documents / Dokumente"一段），不是固定文案。
- 文档链接怎么呈现（卡片或链接，不出长 URL）归 #233。
