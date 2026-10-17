# #249 预览卡文案对抗评审记录

规则：AGENTS.md §3 用词（产品、产品分类；不说 catalogue / article / cart；Produkt / Modell / Serie）、
禁 "不是…而是…" 与三连排比；linker-copywriting Hard Stops 1–9（Actor：正文不给读者布置任务）；
目标 9 的 AI 标识与"可能出错"一句（EU AI Act 第 50 条）。EN 先定稿，DE 独立撰写（Sie 体），
不逐字翻译。

评审方式：初稿由实现会话写；评审由一个独立的评审代理执行（只读，不改文件），对照上面的规则、
现有 `.po` 术语（"Was passt zu diesem Modell?"、"Unterlagen"）、`docs/specs/13-genie.md` 目标 4 与 9、
`plugins/linker-commerce/data/compatibility.json`，并用每个 `{name}` 的真实取值（全部产品、分类、
解决方案名，EN/DE）逐条代入找语法断点。定稿即 `includes/Genie/Preview.php` 的 msgid 与
`languages/linker-tools-de_DE_formal.po` 的 msgstr。

建议按钮的文字原样作为访客的第一条消息发给 Genie（目标 4："点建议 → 打开真实 Genie 并提问"）。
Genie 现在还不读页面（#234），所以每条建议自己点名产品 / 分类 / 解决方案。

## 贯穿全稿的三条意见

1. **分类名嵌进句子会断**。EN "models in Inverters / in Backup Power" 不自然；DE "aus Wechselrichter"、
   "in All-in-One-Systeme" 格错（标签不能变格）。→ 名字放冒号前（"{Name}: …"），或作同位语
   （"zur Kategorie {Name}"）。**采纳**。
2. **DE 产品建议 "zu {name}" 需要不可知的冠词**（"zu … Batterie 8,03 kWh"）。→ "{name}: Was passt dazu?"。
   **采纳**。
3. **解决方案页的 "Size a system for my project" 没点名解决方案**，Genie 不读页面就不知道是哪种。
   → 带上名字。**采纳**。

## 逐条

| 位置 | 初稿 | 评审意见 | 定稿 |
|---|---|---|---|
| 首页 · 标题 EN | Ask Genie about any product we carry | "any … we carry" 是填充；导语已说范围 | **Ask Genie about our products** |
| 首页 · 标题 DE | Fragen Sie Genie zu jedem unserer Produkte | "jedem unserer Produkte" 生硬 | **Fragen Sie Genie zu unseren Produkten** |
| 首页 · 导语 EN | Genie knows our range: models, pairings and documents. | 冒号后三项并列＝三连排比；"knows" 与"可能出错"并排时过度承诺；与建议不对应 | **Genie finds any model in our range and checks what works with it.** |
| 首页 · 导语 DE | Genie kennt unser Sortiment: Modelle, passende Kombinationen und Unterlagen. | 同上 | **Genie findet jedes Modell aus unserem Sortiment und prüft, was dazu passt.** |
| 首页 · 建议 1 EN | Find the SAJ H2-10K-T3 | 保留 | **Find the SAJ H2-10K-T3** |
| 首页 · 建议 1 DE | Den SAJ H2-10K-T3 finden | 不定式进聊天读像待办；"den" 对 Wechselrichter（阳性）成立 | **Zeigen Sie mir den SAJ H2-10K-T3** |
| 首页 · 建议 2 EN | Which batteries work with the EcoFlow OCEAN 2? | OCEAN 2 是系列不是型号，且系列自带电池，问题循环；换兼容数据里有放行对的具体型号（GW3K–10K-EHA-G20 ↔ BAT-D-G20 released），也避免两条都点 SAJ | **Which batteries work with the GoodWe ESA GW10K-EHA-G20?** |
| 首页 · 建议 2 DE | — | "zum" 对 der Wechselrichter / das Leistungsmodul 都成立 | **Welche Batterien passen zum GoodWe ESA GW10K-EHA-G20?** |
| 首页 · 建议 3 | Compare SAJ and GoodWe hybrid inverters / Hybrid-Wechselrichter von SAJ und GoodWe vergleichen | 保留（目标 4 的"比较品牌"）；须实测品牌级比较 | 同初稿；实测见下 |
| 产品 · 标题 EN | Looking at the {name}? | 业主在 DECISION.md 认可的样例；最长 48 字符两行内 | **Looking at the {name}?** |
| 产品 · 标题 DE | Fragen zu {name}? | 标题省冠词是常规，任何性别都成立 | **Fragen zu {name}?** |
| 产品 · 导语 EN | Genie answers questions about this model right here. | "right here" 填充，没比标题多说什么；改说答案依据（AGENTS §4：检索我们托管的文档、服务端填数） | **Genie answers from our product data and the manufacturers' documents.** |
| 产品 · 导语 DE | … direkt hier. | "direkt" 属 Hard Stop 4 的安抚词 | **Genie antwortet auf Grundlage unserer Produktdaten und der Herstellerunterlagen.** |
| 产品 · 建议 1 EN | What pairs with the {name}? | 兼容数据里没有 HCA 充电桩、eManager、CB2 的对；建议只在有对时显示，否则换 "What is the {name} used for?" | **不采纳条件显示**，保留 **What pairs with the {name}?**。理由：实测 eManager（无兼容对）时 Genie 照实说"没有记录的兼容对"，并按手册列出它通信的设备——回答有用且不编造；按兼容数据决定建议会把 linker-commerce 的兼容规则复制进卡片（一条规则两处实现） |
| 产品 · 建议 1 DE | Was passt zu {name}? | 冠词问题 | **{name}: Was passt dazu?** |
| 产品 · 建议 2 | Show the documents for the {name} / Unterlagen zu {name} anzeigen | EN 保留；DE 冠词问题 | EN **Show the documents for the {name}**；DE **{name}: Unterlagen anzeigen** |
| 产品 · 建议 3 | Compare the {name} with similar models / {name} mit ähnlichen Modellen vergleichen | 保留；建议在同类只有一款时隐藏 | 保留；**不采纳条件显示**（理由同建议 1：Genie 的比较工具自己报告找不到同类） |
| 产品 · 短标签 | — | 卡上名字出现四次，建议按钮显示短标签、发送完整句 | **不采纳**：按钮上的字与发进对话的字不一致，访客在对话里看到的不是自己点的那句 |
| 分类 · 标题 EN | {Name}: which model fits your project? | 与建议 1 几乎重复；最长 61 字符 | **Looking at {Name}?** |
| 分类 · 标题 DE | {Name}: Welches Modell passt zu Ihrem Projekt? | 最长 68 字符；重复；"Fragen zu {Name}" 会格错 | **Fragen zur Kategorie {Name}?**（同位语不变格） |
| 分类 · 导语 EN | Genie narrows the list down to the models that fit your project. | "the list" 暗示过滤页面上的列表，Genie 不做 | **Genie compares the models in this category and checks which suit your project.** |
| 分类 · 导语 DE | Genie grenzt die Liste … ein. | 同上 | **Genie vergleicht die Modelle dieser Kategorie und prüft, welche zu Ihrem Projekt passen.** |
| 分类 · 建议 1 | Which models in {Name} fit my project? / Welche Modelle aus {Name} … | 语法与格 | EN **{Name}: which model fits my project?**；DE **{Name}: Welches Modell passt zu meinem Projekt?** |
| 分类 · 建议 2 | How do the models in {Name} differ? / Worin unterscheiden sich die Modelle in {Name}? | 语法；三十多款一次比较答不好；Serie 是定名用词 | EN **{Name}: how do the series differ?**；DE **{Name}: Worin unterscheiden sich die Serien?** |
| 解决方案 · 标题 EN | Planning {name}? | "Planning utility storage?" 不自然 | **Planning a {name} project?**（"a utility" 也对） |
| 解决方案 · 标题 DE | {Name} in Planung? | 稳健；"Sie planen einen …" 会在 "Gewerblicher Speicher" 断 | **{Name} in Planung?** |
| 解决方案 · 导语 EN | Genie sizes the system and picks the products with you. | 保留 | 同初稿 |
| 解决方案 · 导语 DE | Genie legt mit Ihnen die Anlage aus und wählt die passenden Produkte. | "mit Ihnen" 应同时管两个动词 | **Genie legt die Anlage mit Ihnen aus und wählt die passenden Produkte dazu.** |
| 解决方案 · 建议 1 | Which products fit {name}? / {Name}: Welche Produkte passen? | "fit residential storage" 不自然；DE "passen" 无宾语 | EN **What do I need for a {name} system?**；DE **{Name}: Welche Produkte brauche ich?** |
| 解决方案 · 建议 2 | Size a system for my project / Eine Anlage für mein Projekt auslegen | 没点名解决方案 | EN **Size a {name} system for my project**；DE **{Name}: Anlage für mein Projekt auslegen** |
| 关闭按钮 aria-label | Close. No more suggestions for 30 days. / Schließen. 30 Tage lang keine Vorschläge mehr. | 夸大：对话内的下一步建议照常出现，只有卡片隐藏；"Close" 放句首便于语音控制 | EN **Close. Suggestion cards stay hidden for 30 days.**；DE **Schließen. Vorschlagskarten bleiben 30 Tage lang ausgeblendet.** |
| AI 行 | AI assistant · answers can contain mistakes / KI-Assistent · Antworten können Fehler enthalten | 保留；"·" 设 aria-hidden，读屏不念"中点" | 保留；拆成两串，中点 `aria-hidden` |
| 时序 | — | 卡若 8 秒后自动消失会违反 WCAG 2.2.1 | 已确认：卡一直留着，直到关闭、点建议或打开 Genie；8 秒是出现前的停留 |

无其它违规：无 "不是…而是…"、无光环词、正文无布置任务的祈使句、无 catalogue / article / cart。

## 实测（2026-10-18，g249，真实 Genie：deepseek-flash 官方通道，`just serve g249`）

每条首页建议与每类页面各一条建议，新页面里经 `linker-genie-ask` 发出，记录回答开头：

| 页面 | 建议 | 结果 |
|---|---|---|
| / | Find the SAJ H2-10K-T3 | 出 SAJ H2-10K-T3 产品卡，提示可查配对与文档 |
| / | Which batteries work with the GoodWe ESA GW10K-EHA-G20? | 按兼容数据答 released，引 ESA 3–10 kW 数据手册，出 BAT-D-G20 产品卡 |
| / | Compare SAJ and GoodWe hybrid inverters | 选同级 SAJ H2-10K-T3 对 GoodWe ESA GW10K-ETA-G20 出对比表，并概述两家系列 |
| （产品，无兼容对） | What pairs with the SAJ eManager? | 照实说没有记录的兼容对，按手册列出它通信的设备 |
| /product-category/inverters/ | Inverters: how do the series differ? | 按系列（GoodWe ESA、EcoFlow OCEAN、SAJ、GoodWe ET/ETR）分述并出代表型号对比 |
| /solution/utility-storage/ | Size a utility storage system for my project | 引向 Solution Configurator |
| /de/ | Zeigen Sie mir den SAJ H2-10K-T3 | 德语回答，出产品卡与两份文档 |
| /de/produkt-kategorie/wechselrichter/ | Wechselrichter: Welches Modell passt zu meinem Projekt? | 德语回答，出候选并引向 Lösungskonfigurator |
| /de/loesung/heimspeicher/ | Heimspeicher: Welche Produkte brauche ich? | 德语回答，出 Heimspeicher 产品并引向 Lösungskonfigurator |

产品页建议 1 的端到端截图：`screens/en-1440-product-suggestion-answered.png`、`screens/de-1440-product-suggestion-answered.png`。
