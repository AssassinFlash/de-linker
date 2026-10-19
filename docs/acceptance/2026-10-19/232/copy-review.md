# #232 首页 hero 文案对抗评审记录

规则：AGENTS.md §3（产品 / Produkt；不说 catalogue / article / cart；德语 Sie 体；禁
"不是…而是…" 与三连排比）、linker-copywriting Hard Stops（按钮是动作、正文不给读者布置任务）、
`docs/specs/13-genie.md` 目标 9（首次接触即见 AI 标识与"可能出错"一句，EU AI Act 第 50 条）。
EN 先定稿，DE 独立撰写（不逐字翻译），沿用现有 `.po` 术语（"Unterhaltung"、"Seitenleiste"、
"KI-Assistent von Linker"）。定稿即 `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`
的 msgid / msgstr；新增条目只有六条，其余复用已评审过的 dock 与 #236 文案。

评审方式：实现会话写初稿；对抗评审批次逐条对照上面的规则、线上既有措辞与 `.po` 术语，
指出填充词、过度承诺、冠词与格、英文句法搬进德语的问题；下表"定稿"列为准。

## 逐条

| 位置 | 初稿 | 评审意见 | 定稿 |
|---|---|---|---|
| AI 首句 EN | Genie is Linker's AI assistant. Answers may contain errors. | "may contain errors" 是法务句，不像工具说的话；目标 9 要求说明答案的来源，现稿没说。改说来源与仍可能出错，一句完成 AI 标识 + 依据 + 限度。 | **Genie is Linker's AI assistant. Answers come from our product data and documents, and can still be wrong.** |
| AI 首句 DE | Genie ist der KI-Assistent von Linker. Antworten können Fehler enthalten. | 逐字翻译英文法务句，德语里生硬；"von Linker" 是既有品牌句式，保留；补出来源，并用 "trotzdem" 承担 "still"。 | **Genie ist der KI-Assistent von Linker. Antworten stammen aus unseren Produktdaten und Dokumenten und können trotzdem falsch sein.** |
| 对话区标题 | Genie - Linker's AI assistant / Genie – der KI-Assistent von Linker | 复用 dock 的既有标题；AGENTS 规定德语不写 "Linker Genie" 连写，现有 `.po` 已是 en dash 形式。 | 同初稿（复用，不新增条目） |
| 顶部入口 EN | Continue in the side panel | 是按钮（动作），不是正文；"side panel" 与站内对 dock 的说法一致，不引入 "dock" 术语。 | **Continue in the side panel** |
| 顶部入口 DE | Im Seitenbereich fortsetzen | "Seitenbereich" 与现有 `.po` 的 "Seitenleiste"（如 "Seitenleiste schließen"）不一致，同一 UI 两个词会让读屏与用户困惑。 | **In der Seitenleiste fortsetzen** |
| 右下角返回入口 EN | Your Genie conversation · continue | 原型与票的原文；不加 "(2)" 计数（票没有要求，计数还会随会话变化）。"·" 是原型的视觉分隔，保留在可见文字里。 | **Your Genie conversation · continue** |
| 右下角返回入口 DE | Ihre Genie-Konversation · fortsetzen | "Konversation" 不是本仓库的访客用词；现有 `.po` 用 "Unterhaltung"（"Alle Unterhaltungen"、"Unterhaltung öffnen"）。 | **Ihre Genie-Unterhaltung · fortsetzen** |
| dock 来源行 EN | Asked from the homepage | 票的原文；它是标签不是问句，句末不加问号。 | **Asked from the homepage** |
| dock 来源行 DE | Von der Startseite gefragt | "gefragt" 直译英文被动，德语读起来像没说完；德语说"在首页开始"更自然，也与"同一会话"的含义一致。 | **Auf der Startseite begonnen** |
| 追问框 placeholder EN | Ask a follow-up… | 票要求输入框变成追问框；"follow-up" 是对话里的常用词，不布置任务（placeholder 不是正文）。 | **Ask a follow-up…** |
| 追问框 placeholder DE | Stellen Sie eine Rückfrage... | Sie 体；德语省略号的排版与现有 `.po` 一致（"Genie denkt nach …"，省略号前有空格）。 | **Stellen Sie eine Rückfrage …** |

无其它违规：无 "不是…而是…"、无三连排比、无光环词、无 catalogue / article / cart；
复用文案（Close / Schließen、Genie is thinking… / Genie denkt nach …、附件与产品卡）均已在
#235、#236、#243、#249、#250 评审过，不在本票重开。

## 实测（2026-10-19，g232，真实 Genie：deepseek-flash 官方通道）

`tests/e2e/specs/genie-hero.spec.ts` 在 EN/DE × 1440/390 上实走；截图在 `shots/`：

| 场景 | 结果 |
|---|---|
| EN "saj" | 真实回答 + 6 张 SAJ 产品卡，桌面四列、手机两列 |
| DE "saj" | 德语回答；卡面 "Produkt"、"Auf Lager"、"Zum Lösungsentwurf hinzufügen"、"Lösung speichern" |
| 标题栏 DE | "Genie – der KI-Assistent von Linker" / "In der Seitenleiste fortsetzen" / × |
| dock 来源行 DE | "Auf der Startseite begonnen"，会话正文与 hero 相同 |
| 精确铭牌 / 看不清 / PDF / 被拒 | #236 四种状态都在 hero 内渲染（截图 `*-nameplate-exact`、`*-nameplate-unreadable`、`*-datasheet`、`*-refused`） |
