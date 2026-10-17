# #233 Genie 兜底文案对抗评审记录

规则（AGENTS.md §1–§3）：工具名 Solution Configurator / Lösungskonfigurator；
德语 Sie 体（de_DE_formal）；禁 "不是…而是…"、三连排比与 AI 套话；不说
article / catalogue / cart / basket（Artikel / Katalog / Warenkorb）；承诺须
可执行（配置器的设计报告给储能容量区间与选定电池，不给回本期）。EN 先行，DE
独立撰写。语气基准：同文件 `template.py` 的 DEGRADED（第一人称 "I could not
answer…" / "Ich konnte Ihre Frage…"）与 LOGIN_REQUIRED；术语基准：
`linker-commerce` .po 的 `p. %d` → `S. %d`、`linker-tools` .po 的按钮
`Open the configurator` → `Konfigurator öffnen`。德语定稿须通过
`german_is_clean`（不含 ` the ` ` and ` ` with ` ` your ` ` this ` ` our `）。
每处：初稿 → 评审意见 → 定稿。定稿即 `services/genie/src/linker_genie/template.py`
与 `hydrate.py` 里的字面量。

## 1. SIZING（电池定容问题的模型回答两次未过 grounding 时的兜底句，下接 "Open the configurator" 按钮）

- EN 初稿：`The Solution Configurator sizes the battery from your PV system and
  your annual consumption.`
  评审：
  - 工具名逐字正确，主语位带 The，与 #12 记录 §10 的既有句式
    "The Solution Configurator sizes" 一致；"size the battery" 是安装商的行话，
    B2B 语域合适。
  - 承诺核对：规格 14 的住宅设计输出 `storage.usable_kwh_range` 与选定电池，
    "sizes the battery" 可执行；句子不提回本、不提价格，不越界。
  - 输入次序：配置器表单与 HTW 定容规则里年用电是必填输入，光伏 kWp 可以缺省
    （"还没有，按屋顶估" → 屋顶步）。先说必有的输入、后说可缺的输入，读起来与
    表单顺序一致，也与 DE 定稿同序。只对调两项，不加第三项（相数、备电、邮编
    也是输入，补进来就成了排比，且兜底句不必列全）。
  - "from" 在 "size X from Y" 里是惯用法，不改 "based on"。
  **定稿**：`The Solution Configurator sizes the battery from your annual
  consumption and your PV system.`
- DE 初稿：`Der Lösungskonfigurator ermittelt die passende Speichergröße aus
  Ihrer PV-Anlage und Ihrem Jahresverbrauch.`
  评审：
  - "ermittelt … aus Ihrer PV-Anlage" 字面是"从您的光伏系统里求出"，介词不准；
    依据数据求值的惯用介词是 "anhand"（支配属格）。
  - 配置器实际读的是光伏功率（kWp），"PV-Anlage" 指整套设备，换成
    "PV-Leistung" 更准，也是安装商的说法。
  - "Speichergröße" 与站内既有 "Speicherlösung""Speicheroptionen" 同族，德国
    市场对电池储能惯说 Speicher，保留；"passende" 对应报告里的选定电池与容量
    区间，不算过度承诺。
  - 次序同 EN 理由：年用电在前。Sie 体（Ihres / Ihrer），无英语功能词。
  **定稿**：`Der Lösungskonfigurator ermittelt die passende Speichergröße
  anhand Ihres Jahresverbrauchs und Ihrer PV-Leistung.`

## 2. DOCUMENTS（文档/规格问题的兜底句，下接最多三条文档链接）

- EN 初稿：`These documents cover your question.`
  评审：
  - **过度承诺**：此句只在模型回答未过 grounding 时出现，链接来自
    search-knowledge 的检索排序（dense 单路，无"已答"判定）。"cover your
    question" 断言文档回答了问题，服务端无从保证；检索块可能只是相关。
  - **单复数**：`refs[:FALLBACK_DOCUMENTS]` 可能只有一条（`facts.documents`
    非空即可进入此分支），"These documents" 在一条链接时出错。句子须不依赖
    数量。
  - 语气：DEGRADED 用第一人称陈述 Genie 做了什么（"I could not answer"）；
    此处同样只陈述做过的事——找到了这些——不替文档下结论。
  - 候选 "These documents may help with your question." 仍有复数问题且
    "may help" 是对冲腔；"These documents are relevant…" 仍断言相关性。
  **定稿**：`Here is what I found for your question.`
- DE 初稿：`Diese Dokumente behandeln Ihre Frage.`
  评审：同样过度承诺且有单复数问题；另外 "behandeln Ihre Frage" 搭配不自然
  （文档 behandeln 一个 Thema，不 behandeln 一个 Frage）。独立撰写：第一人称、
  只陈述找到的结果，"Folgendes" 不论一条或三条都成立；Sie 体（Ihrer）；无英语
  功能词。
  **定稿**：`Zu Ihrer Frage habe ich Folgendes gefunden.`

## 3. 文档链接标签里的页码缩写（`<document title> · p. 42`）

- EN 初稿：`p.`；DE 初稿：`S.`
  评审：
  - 与站内已发布的 `linker-commerce` .po 一致（`p. %d` → `S. %d`、
    `%1$s, p. %2$d` → `%1$s, S. %2$d`），Seite 的德语标准缩写是 "S."，接受。
  - 排版：`hydrate.py` 第 61 行用普通空格连接缩写与数字，390px 宽的聊天卡片里
    "S." 可能落在行尾、"42" 换到下一行。缩写与页码之间应为不换行空格
    U+00A0（EN 与 DE 同）。
  - 分隔符：门店文档库用逗号（"Title, p. 42"），Genie 链接用居中点（"Title ·
    p. 42"）。两处是不同表面（列表行与对话卡片），居中点与 Genie 卡片既有的
    "·" 分隔一致，不强求统一，记录在此。
  **定稿**：EN `p.`，DE `S.`；标签拼接为 `<title> · p. 42` /
  `<title> · S. 42`。

## 附：评审中顺带发现（属本票，交实现方本轮修）

- `facts.py` 第 164、220、246 行把页码写成 `p.{page}`（无空格、不分语言）存入
  Fact 的 value。若这些 value 会经服务端填入回答而呈现给客户（AGENTS §4：
  "数字由服务端填入"），德语回答里会出现英文 "p.42"。实现方须核实这些 value
  是否对客户可见；可见则改用 `PAGE_WORD[language]` 加 U+00A0，与 §3 同形。

## 实现核对（执行会话）

- 定稿已写入 `services/genie/src/linker_genie/template.py`（SIZING、DOCUMENTS）与 `hydrate.py`（`PAGE_WORD` 与不换行空格）。
- 评审指出的 `facts.py` 里 `p.{page}` 英文值：这些值只作事实 ID 的内容，不再进入客户可见文本——`ground.py` 的 `_documents` 拒绝任何指向文档事实的 `{fact:…}` 占位符，文档只经文档块呈现，标签由 `hydrate.document_label` 按语言生成。测试：`tests/test_ground_understanding.py::test_no_url_stands_in_the_text`、`test_a_german_document_link_says_seite`。

## 第 1 轮评审补充：多页缩写（PR #279）

同一文件被引用多页时合成一个链接（评审意见 1）。
- 初稿：EN `pp. 3, 7`；DE `S. 3, 7`。
- 异议：DE 是否需要复数形式？不需要。德语出版惯例里一页、多页都写 "S."（如 "S. 3, 7"、"S. 3–7"），没有 "SS." 这种写法。EN 的 "pp." 是英文引文的标准多页缩写，和单页的 "p." 成对。缩写与页码之间沿用不换行空格。页码升序排列，逗号分隔；不合并成区间，因为引用的是互不相邻的单页。
- 定稿：EN `pp.`（`PAGES_WORD["en"]`）；DE `S.`（`PAGES_WORD["de"]`）。测试：`tests/test_ground_understanding.py::test_one_file_is_one_link_with_its_cited_pages`、`test_a_german_link_of_several_pages_keeps_s`。
