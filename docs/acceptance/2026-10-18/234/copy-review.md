# #234 开场建议与"Lösungsentwurf 之后"一句 · 文案对抗评审记录

规则：AGENTS.md §3 用词（产品、产品分类、Lösungsentwurf；不说 catalogue / article / cart；Sie 体）、禁 "不是…而是…" 与三连排比；
linker-copywriting Hard Stops（按 #249 的用法：建议按钮是访客发给 Genie 的原话，可以是对 Genie 的祈使句或问句）；
`.po` 既有术语；EN 先定稿，DE 独立撰写。

评审方式：初稿由实现会话写；评审由一个独立的评审代理执行（只读，不改文件），对照上面的规则、
`docs/acceptance/2026-10-18/249/copy-review.md` 的先例、`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po`
的术语（"We reply within one business day." → "Wir antworten innerhalb eines Arbeitstags."），并读了服务端代码
（`route.with_page`、`page.PAGE_CHARS`、`jev.about_this_page`），核对每条建议 Genie 是否真有材料可答。
定稿即 `includes/Genie/Entries.php::prompts()` 的 msgid、`languages/linker-tools-de_DE_formal.po` 的 msgstr、
`services/genie/prompts/{en,de}/system.md` 的"The page / Die Seite"一段。

首页、产品、产品分类、解决方案四类页面的开场建议沿用预览卡那一组（#249 已评审定稿），本记录只覆盖其余页面。

## 贯穿全稿的意见

1. **依赖本页的建议必须点名本页**（this post / these posts / this page / diese Seite）：只有 Jev 判为"问本页"才读页面
   （`about_this_page`）。→ 博客首页那条改成 "Which of these posts …"。**采纳**。
2. **FAQ 页的答案是编造的站点文案**（AGENTS.md 2026-10-09）：建议不应把 Genie 引向它当事实来源；公司、物流类问题照旧一句话转团队。
   → FAQ 页第 2 条换成有兼容数据支撑的配对问题。**采纳**。
3. **"其余页"的摘要建议不合适**：对 Impressum、Datenschutz、条款做 AI 摘要会改写法律文本，联系页与 Proforma 请求页的摘要没有用。
   → 只在博客首页与营销页保留 "Summarize this page"。**采纳**。
4. **DE 用问句**（#249 第 2 轮同样把 "Zeigen Sie mir …" 判为生硬）。**采纳**。
5. Proforma 请求页（`other`）显示着 Lösungsentwurf，建议放 "Check my draft"。**不采纳**：页面类型按票的八类划分，
   Proforma 请求是表单页；草稿的商品只在 `draft` 类型由代理读取，在表单页放这条建议会读不到草稿。

## 逐条

| # | 位置 | 初稿 EN / DE | 评审意见 | 定稿 EN / DE |
|---|---|---|---|---|
| 1 | 商城 /products/ · 1 | Which model fits my project? / Welches Modell passt zu meinem Projekt? | 无；是分类建议去掉前缀，#249 实测它引向配置器 | 同初稿 |
| 2 | 博文 · 1 | Summarize this post / Fassen Sie diesen Beitrag zusammen | DE 祈使句生硬 | **Summarize this post** / **Worum geht es in diesem Beitrag?** |
| 3 | 博文 · 2 | Which products does this post apply to? / Für welche Produkte gilt dieser Beitrag? | "gilt" 像法律适用范围 | **Which products does this post apply to?** / **Welche Produkte betrifft dieser Beitrag?** |
| 4 | 博客首页 · 1 | Which posts help me choose a hybrid inverter? / Welche Beiträge helfen bei der Wahl eines Hybrid-Wechselrichters? | 没点名本页，Jev 可能不判"问本页"，Genie 便没有文章列表；DE 64 字符 | **Which of these posts cover hybrid inverters?** / **Welche dieser Beiträge behandeln Hybrid-Wechselrichter?** |
| 5 | 博客首页 · 2、营销页 · 1 | Summarize this page / Fassen Sie diese Seite zusammen | DE 祈使；"其余页"不该有（贯穿意见 3） | **Summarize this page** / **Worum geht es auf dieser Seite?**（只用于博客首页与营销页） |
| 6 | FAQ 与文档页 · 1 | Find the datasheet for my model / Zeigen Sie mir das Datenblatt zu meinem Modell | "Find …" 像对搜索框下命令；风险：文档路由在没有型号时可能乱给数据手册——必须实测 Genie 会先问型号 | **Is there a datasheet for my model?** / **Gibt es ein Datenblatt zu meinem Modell?**（实测见下：先问品牌与型号） |
| 7 | FAQ 与文档页 · 2 | What does this page say about compatibility lists? / Was sagt diese Seite über Kompatibilitätslisten? | 没人这样问；内容来自一条编造的 FAQ（贯穿意见 2） | 沿用已评审的 **Which batteries work with my inverter?** / **Welche Batterien passen zu meinem Wechselrichter?** |
| 8 | 营销页 · 2 | Which products suit my project? / Welche Produkte passen zu meinem Projekt? | 动词与 #1 和分类建议的 "fit" 不一致 | **Which products fit my project?** / **Welche Produkte passen zu meinem Projekt?** |
| 9 | 其余页 · 1 | Summarize this page | 见贯穿意见 3 | **Which model fits my project?** / **Welches Modell passt zu meinem Projekt?**（第 2 条沿用 "Which batteries work with my inverter?"） |

Lösungsentwurf（"Check my draft"、"What happens next?"）与账户（"Where is my Proforma?"、"What happens next?"）沿用既有定稿，不改。

## 系统提示词里"Lösungsentwurf 之后"一句

它是给模型的指令，但决定了客户看到的回答。业主事实：一个工作日内回复询盘（2026-10-09）；询盘对所有人开放（2026-10-17）；
四个状态名（AGENTS.md §3）。模型不得写任何形式的数字，所以写 "a business day"。

| 评审意见 | 处理 |
|---|---|
| 用词：`.po` 里是 "business day / Arbeitstag"；德语 **Werktag** 在法律上含周六，会把承诺放宽 | **采纳**：EN "business day"，DE "Arbeitstag" |
| 承诺范围：初稿读起来像 Proforma 也在一个工作日内出 | **采纳**：一个工作日只修饰"回复" |
| 访客也能发询盘：初稿会让模型叫访客去看他没有的账户 | **采纳**：状态只在"已登录客户的账户"里 |
| 状态名加引号，模型照抄，德语句子也通顺 | **采纳** |
| DE 三个动词 "und … und" 串在一起；"sendet" 与状态名"ausgestellt"不一致 | **采纳** |

定稿：
- EN：What happens after the solution draft: the customer sends it with the Proforma request; the Linker team replies within a business day and issues a Proforma invoice. A signed-in customer's account shows each inquiry as "Inquiry received", "Proforma invoice issued", "Completed" or "Cancelled".
- DE：Was nach dem Lösungsentwurf geschieht: Die Kundin oder der Kunde sendet ihn mit der Proforma-Anfrage; das Linker-Team antwortet innerhalb eines Arbeitstags und stellt eine Proformarechnung aus. Im Konto angemeldeter Kundinnen und Kunden erscheint jede Anfrage als „Anfrage eingegangen“, „Proformarechnung ausgestellt“, „Abgeschlossen“ oder „Storniert“.

无其它违规：无 "不是…而是…"、无三连排比、无 catalogue / article / cart；英语拼写统一为美式；定稿长度都在 50 字符内，DE #4 为 55 字符（德语更长，接受）。

## 实测（2026-10-18，g234，真实 Genie：Jev + deepseek-flash 官方通道，`just serve g234`）

每条新建议在它所在的页面发出一次（服务端 `/turn`，带该页的页面上下文），原始记录 `eval/chips-20261018.json`：

| 页面 | 建议 | 结果 |
|---|---|---|
| /faq-download/ | Is there a datasheet for my model? | 说明本页是文档库，按品牌分组、有德语版处另附德语，**先问品牌与型号**，没有乱给数据手册 |
| /de/faq-download/ | Gibt es ein Datenblatt zu meinem Modell? | 德语，同上，问"Von welcher Marke ist Ihr Modell?" |
| /blog/ | Which of these posts cover hybrid inverters? | 读了博客首页，点出 "How to Choose Between a Hybrid Inverter and an AC-Coupled Storage Setup"，另列相关的配对检查清单 |
| /de/blog/ | Welche dieser Beiträge behandeln Hybrid-Wechselrichter? | 德语，同上 |
| 博文（EN） | Summarize this post | 按博文结构概述两种架构与各自适用场景 |
| 博文（DE） | Welche Produkte betrifft dieser Beitrag? | 照实说博文不点名型号，按它比较的两类产品回答 |
| /for-installer/ | Summarize this page | 概述该页（住宅单/三相、商业电池柜、工具） |
| /de/fuer-installateur/ | Welche Produkte passen zu meinem Projekt? | 按本页说明产品范围，引向 Lösungskonfigurator |
| /contact/ | Which model fits my project? | 引向 Solution Configurator（带打开动作） |
| /de/produkte/ | Welches Modell passt zu meinem Projekt? | 引向 Lösungskonfigurator，并提到本页的筛选 |
