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

未登记其它视觉差异：首页静止状态与线上逐像素一致（`pixel/report.jsonl`，EN/DE × 1440/390，
掩膜外差异 0）；页头页脚、营销区、产品卡以外的站点面未改。
