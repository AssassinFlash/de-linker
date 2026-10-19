# #232 首页 hero · 裁定变更台账

依据：业主 2026-10-17 选定变体 B（就地展开，`docs/prototypes/2026-10-17-hero/DECISION.md`）；
AGENTS.md 2026-10-10 裁定：工具页（Genie、Solution Configurator，含屋顶步）的设计可以改动，
营销/产品/博客/商务页遵循线上现有设计。本票只改 Genie 工具面，不动首页静止外观。

| 表面 | 变更 | 依据 | 前 / 后 |
|---|---|---|---|
| 首页 hero · 交互后 | 眉题、标题、副标题、胶囊、脚注收起；对话区在 `.hero-dialog` 顶部展开；输入框变追问框 | 业主 2026-10-17 变体 B | `shots/hero-en-1440-restored.png`（复原） / `shots/hero-en-1440-answer.png`、`shots/hero-en-1440-cards.png`（展开） |
| 首页 hero · 对话区 | 顶部 "Genie - Linker's AI assistant" ＋ "Continue in the side panel" ＋ ×；首条 AI 标识与"可能出错"一句 | 目标 9、票面 | `shots/hero-en-1440-answer.png`、`shots/hero-de-1440-answer.png` |
| 首页 hero · 产品卡 | 桌面四列、手机两列；卡内图片在上、文字在下（dock 的两列行布局在 960 px 里放不下四张） | 票面变体 B、原型截图 | `shots/hero-en-1440-cards.png`、`shots/hero-en-390-cards.png` |
| 首页 hero · 返回入口 | hero 滚出视口后右下角（Genie 圆钮旁）"Your Genie conversation · continue"；手机在右下角 | 票面变体 B、原型 | `shots/hero-en-1440-continue-entry.png`、`shots/hero-en-390-continue-entry.png` |
| dock 顶部 | 从 hero 转来的会话标 "Asked from the homepage" / "Auf der Startseite begonnen"；开启时重读 hero 写的线程 | 票面（"dock 里标注 Asked from the homepage"） | `shots/hero-en-1440-side-panel.png`、`shots/hero-de-390-dock-continued.png` |
| 首页 hero · 对话内询盘/联系 | #250 询盘确认卡与 #243 联系卡在 hero 内渲染并可发送，发送后留下记录（目标 5、6 在 hero 入口成立） | 目标 5、6；评审第 1 轮 P0 | `shots/hero-en-1440-inquiry.png`、`shots/hero-de-390-inquiry.png`、`shots/hero-en-1440-contact.png`、`shots/hero-de-390-contact.png` |

## 站点页面 CSS 例外（评审第 1 轮第 6 项）

`src/hero/hero.css` 有少量规则直接指向 LC 页面自己的类（`.hero-cinematic`、`.hero-stage`、
`.hero-dialog`、`.hero-badge`、`.hero-title`、`.hero-subtitle`、`.hero-capsules`、`.hero-footnote`），
用于在展开时收起 hero 自己的文字并放宽对话区。它们全部以 `.linker-genie-hero--open` 为前缀，
只在插件加上这个类后生效；静止状态没有任何插件 CSS 命中页面标记。依据是业主 2026-10-10 的
工具面设计裁定（Genie 对话可改），这是 AGENTS §4"插件对站点页面零 CSS"经评审确认的唯一例外；
像素门（`pixel/report.jsonl`）证明静止页面与线上掩膜外 0 差异。其余插件规则只挂在
`.linker-genie-hero__*` 与 hero 自己注入的元素上。

未登记其它视觉差异：首页静止状态与线上逐像素一致（`pixel/report.jsonl`，EN/DE × 1440/390，
掩膜外差异 0）；页头页脚、营销区、产品卡以外的站点面未改。
