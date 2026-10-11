# #66 文案对抗评审记录（对比页 + 文档库页）

规则（AGENTS.md 2026-10-11 文案门槛）：客户可见文案（含 UI 字符串）逐处对抗评审，
EN 先行、DE 独立撰写（不是翻译）；基准 = linker-copywriting Hard Stops + 线上既有
措辞与用词表（AGENTS §3：产品/产品分类，德语 Sie 体 de_DE_formal，禁 "不是…而是…"
与三连排比）。每处：初稿 → 评审意见 → 定稿。

**线上既有措辞优先**：本票两页的许多串在线上已有德语（同一页、同一工作台），这些
以线上原样为定稿（"内容冻结"），逐条注明"线上原样"。新写的串给初稿与评审。

## 1. 对比页 · 页面（模板 `content/livecanvas/compare_page.html` 与 `de/` 孪生）

### 1.1 页标题（h1，取自页面标题 `[lc_the_title]`）

- EN `Compare products` / DE `Produkte vergleichen`。线上原样（线上页标题）。**定稿**：
  同线上。

### 1.2 引导句

- EN 初稿：`Tick up to four products while you browse the catalogue, then open
  this page to see their figures and technical data side by side. The selection
  stays in this browser tab.`
  评审：AGENTS §3 禁"目录（catalogue）"这类词——`while you browse the catalogue`
  改 `while you browse the products`；后半句是会话存储的事实陈述（刷新后仍在、
  关标签页即失），"stays in this browser tab" 准确；"figures and technical data"
  对应页面的两块行（#7 图值 + 技术表），不改。**定稿**：`Tick up to four products
  while you browse, then open this page to see their figures and technical data
  side by side. Your selection stays in this browser tab.`
- DE 初稿（独立撰写，非译）：`Setzen Sie beim Durchsuchen der Produkte Häkchen
  bei bis zu vier Produkten und öffnen Sie diese Seite, um Kennzahlen und
  technische Daten nebeneinander zu sehen. Ihre Auswahl bleibt in diesem
  Browser-Tab.`
  评审："Häkchen setzen" 正是勾选控件的动作（德语安装商对复选框的常态说法，
  比 "auswählen" 更明确指向勾选态）；"Kennzahlen und technische Daten" 是两块行
  的德语说法（Kennzahlen = 关键数字，#7 图值在产品页德语也用这个词）；Sie 体；
  无 "nicht…sondern"、无三连排比。**定稿**：同初稿。

### 1.3 继续浏览按钮

- EN `Continue browsing` / DE `Weiter einkaufen`。线上原样（线上对比页与目录页的
  同一按钮）。**定稿**：同线上。

### 1.4 面包屑首项

- EN `Home` / DE `Startseite`。站内既有（页头、产品页模板同词）。**定稿**：同既有。

## 2. 对比页 · 表片段（`ComparePage`，插件文本域，德语进 .po/.mo）

### 2.1 空态

- EN `Choose products to compare their specifications.` / DE `Wählen Sie Produkte
  aus, um ihre technischen Daten zu vergleichen.`。线上原样（线上对比页空态德语
  逐字）。**定稿**：同线上。

### 2.2 上限提示

- EN 初稿：`Only the first %d products are shown.`（线上旧文案，沿用）
  评审：地址带了 5 个以上 ID 时才出现，说的是"只显示前 N 个"——与页面的实际
  行为一致（前 4 个按顺序保留）。不改。**定稿**：同初稿。
- DE 初稿：`Nur die ersten %d Produkte werden angezeigt.`
  评审：德语常态句式（"angezeigt werden" 的被动在德语界面里比 "sieht man" 自然）；
  与 EN 同为一句；Sie 体规则此处无主语，不受影响。**定稿**：同初稿。

### 2.3 行首列与操作

| EN（源串） | DE 定稿 | 依据 |
|---|---|---|
| `Products` | `Produkte` | 站内既有（.po 已有，线上目录/表头同词） |
| `Remove` | `Entfernen` | 线上原样（线上对比页每列的操作链接） |
| `Item number` | `Artikelnummer` | 线上德语用缩写 `Artikelnr.`；评审：缩写是线上窄列的权宜，页面是工具页（设计可现代化），完整词是德语贸易的常态写法（询盘、Proforma 里都是 Artikelnummer），列宽由样式解决。**定稿**：`Artikelnummer` |
| `Net price` | `Nettopreis` | 线上原样 |
| `Availability` | `Verfügbarkeit` | 线上原样 |
| `Product comparison table`（表格的 aria-label） | `Vergleichstabelle der Produkte` | 新写；评审：德语把限定语放后置属格是常态，不用连写 `Produktvergleichstabelle`（过长且德语装订词里少见）；读屏读出完整语义 |
| `Compare`（浮动芯片标签） | `Vergleichen` | 线上原样（线上芯片 aria-label 与卡按钮标签） |

### 2.4 行值与行标签

- 行标签（Anwendung / Phasen / Bemessungsleistung AC (kW) / Maximale PV-Eingangsleistung (kW) / Nutzbare Energie (kWh) / Nennenergie (kWh) / Energiebereich (kWh) / Produktkategorie）：**#13 已交付的 ability 标签逐字复用**（一个词表，两处入口），不在本票重写。
- 值 `home` / `commercial` → `Home` / `Commercial`（EN）、`Privat` / `Gewerblich`（DE）：站内既有（产品页关键数字、目录卡的同一词）。**定稿**：同既有。
- 技术表的行标签与值来自产品自己的数据（线上同源，德语随产品数据），不改。

## 3. 文档库页 · 页面（`faq_page.html` 与 `de/` 孪生）

### 3.1 冻结内容（线上原样，不逐条重评）

hero 的 kicker/标题/引导句、四个承诺、三个区锚点（Dokumente / Produktantworten /
Bevor Sie bestellen）、"Bevor Sie bestellen" 的 16 条问答与 5 个类目：逐字取自
线上页（EN 与 DE 各自已有成稿）。**定稿**：同线上。

- 一处还原：`Engineering desk` 承诺的 EN 句在初稿里被写成 "handled by the
  engineering desk in Germany."；评审：这是冻结句，线上是 "Missing documentation
  or custom inquiries handled by **Linker's technical desk**."（DE "…bearbeitet das
  technische Team von Linker."）——初稿把另一条的 "in Germany" 误带进来，改回线上
  逐字。**定稿**：线上原样。

### 3.2 工具改名（线上内容，裁定改名）

- 线上 gc4 末条问的是旧助手："What technical documentation is available through
  Linker Advisor?" / "Welche technische Dokumentation ist über den Linker Berater
  verfügbar?"。按 #12 的改名裁定（助手现在是 Genie），只换名、其余逐字。
  EN **定稿**：`What technical documentation is available through Genie?` /
  `Genie indexes the datasheets, manuals, and compatibility matrices in this
  library, retrieving specific technical parameters and wiring requirements
  directly.`
  DE **定稿**：`Welche technische Dokumentation ist über Genie verfügbar?` /
  `Genie indexiert die Datenblätter, Handbücher und Kompatibilitätsmatrizen in
  dieser Bibliothek und ruft technische Parameter und Verdrahtungsanforderungen
  direkt ab.`
  评审：德语不写 "Linker Genie" 连写（AGENTS §1）、不带冠词（Genie 是专名，
  "über Genie"、"Genie indexiert"）；其余词与线上德语逐字一致。

### 3.3 产品问答区（新写）

- EN 初稿：`What the products are asked about.` + `The questions answered on the
  product pages, gathered by brand. For a question this list does not answer, ask
  Genie.`
  评审：标题是"这一区是什么"的一句，不用名词堆（"Product Q&A"）；正文说明来源
  （产品页自己的答案）与去处（Genie），第二句给读者一条出路，不承诺"我们回答
  一切"（范围外问题本来就转人）；"ask Genie" 与站内 entry 措辞一致。**定稿**：
  同初稿。
- DE 初稿（独立撰写）：`Was zu den Produkten gefragt wird.` + `Die Fragen, die
  auf den Produktseiten beantwortet werden, nach Marke zusammengestellt. Für eine
  Frage, die diese Liste nicht beantwortet, fragen Sie Genie.`
  评审："Was zu den Produkten gefragt wird" 是德语里"被问到的事"的常态说法（比
  "Produktfragen" 更像人话，且不与 FAQ 缩写混用）；第二句用关系从句承接，Sie 体；
  末句直接请读者提问（fragen Sie Genie），不说 "kontaktieren Sie"。**定稿**：同初稿。

## 4. 文档库片段（`LibraryPage` / `DocumentLibrary`，德语进 .po/.mo）

| EN（源串） | DE 定稿 | 依据 |
|---|---|---|
| `Download` | `Herunterladen` | 线上原样（文档目录每条的链接） |
| `%d document` / `%d documents` | `%d Dokument` / `%d Dokumente` | 线上原样（"92 Dokumente" 的品牌计数） |
| `%d answer` / `%d answers` | `%d Antwort` / `%d Antworten` | 新写；线上这一格是脚本填的省略号。评审：与 `Dokument/Dokumente` 同一复数机制 |
| `covers %s` | `gilt für %s` | 线上原样 |
| `covers %d product(s)` | `gilt für %d Produkt(e)` | 线上原样 |
| `Datasheet` | `Datenblatt` | 线上原样（类型筛选与每条的类型） |
| `Manual` | `Handbuch` | 线上原样 |
| `Certificate` | `Zertifikat` | 线上原样 |
| `Compatibility` | `Kompatibilität` | 线上原样 |
| `Warranty` | `Garantie` | 线上"Garantie & Service"的同一词根；类型名新写 |
| `Brochure` | `Broschüre` | 新写（德语技术市场常态词） |
| `Document`（兜底类型） | `Dokument` | 线上原样（线上" Dokument" 类型） |
| `English` / `German` / `Multilingual` | `Englisch` / `Deutsch` / `Mehrsprachig` | 线上原样（语言筛选） |

## 5. 未改的既有串

产品页、目录卡、账户页与邮件里的字符串本票未动；`Net price after partner
sign-in` / `In stock` / `Currently unavailable` 走 #11 已有的 .po 翻译（对比页与
产品页同一句）。对比表的行标签与值见 §2.4。

## 6. 评审结论

- 每处 EN 先定、DE 独立写；德语无一处是 EN 的逐词搬运（§1.2、§3.3 的德语句式与
  EN 不同构）。
- 线上已有的德语串一律引用线上原样（"内容冻结"），只在工具改名（§3.2）与一处
  误带词（§3.1 还原）上偏离线上。
- 定稿落地位置：模板文件 `content/livecanvas/{compare_page,faq_page}.html` 与
  `content/livecanvas/de/{compare_page,faq_page}.html`；插件串在
  `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po`（msgfmt
  出的 .mo 随仓库）。
