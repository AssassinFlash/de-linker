# #232 Genie · hero 接线实现 · 验收记录

实例：`g232`（`http://127.0.0.1:9144/`），快照 `20261019-0016`（2026-10-18T16:23:43+00:00 拉取），
`just serve g232`（engine 9145、genie 9146）。所有验证在本地实例完成；未部署、未合并、未写生产。

## 交付

首页 hero（LiveCanvas 的 `section.hero-cinematic`）的每个控件原地展开真实 Genie 会话，
变体 B：未交互时页面不动（像素门），展开后对话与 #236 附件、dock 共用同一个会话。

- PHP：`plugins/linker-tools/includes/Genie/Hero.php`（只在 `is_front_page()` 加载构建入口）。
- 前端：`plugins/linker-tools/src/hero/`（`state.ts` 状态机、`session.ts` 共享会话、`Hero.tsx`
  对话、`controller.tsx` 页面控件、`hero.css`、`index.tsx`）。
- dock 交接：`includes/Genie/Entries.php` 的加载器转发 `refresh` / `fromHome`；
  `src/genie/App.tsx` 用 `showStored()` 重读 hero 写的线程并显示 "Asked from the homepage"。
- 规格：`docs/specs/13-genie.md` 的"首页 hero"一节与 Entries 条目。
- 文案：`docs/acceptance/2026-10-19/232/copy-review.md`（六条新文案，EN 先定稿、DE 独立撰写）。
- 裁定变更：`docs/acceptance/2026-10-19/232/change-ledger.md`。

## 完成标准与证据

| 完成标准 | 证据 |
|---|---|
| 每个控件原地开聊、不跳页（输入回车、发送、胶囊、拍照、附件、语音） | `tests/e2e/specs/genie-hero.spec.ts` → "every control opens the conversation in place and never navigates"（EN/DE × 1440/390，共 28/28 通过）；每条断言 URL 不变、`.linker-genie-hero--open` 与 `.linker-genie-hero__surface` 出现。截图 `shots/hero-{en,de}-{1440,390}-{enter,send,capsule,voice,photo-open,attach-open}.png` |
| 展开后真实 Genie 回答与产品卡在 hero 内（桌面四列、手机两列） | e2e "the answer and its product cards appear in the hero"：断言 `.linker-genie-reply` 与 `.linker-card`，并断言 `grid-template-columns` 为 4（1440）或 2（390）。截图 `*-answer.png`、`*-cards.png` |
| 滚出 hero 后出现 "Your Genie conversation · continue"，点开在 dock 继续同一会话 | e2e "out of sight, the way back continues the same conversation in the dock"：断言 pill 可见、dock 打开、来源行与 `saj` 同线、URL 不变。截图 `*-continue-entry.png`、`*-dock-continued.png` |
| 关闭对话区复原 hero，且追问仍是同一会话 | e2e "closing restores the hero and the same conversation continues"：关闭后 surface/类清空、标题可见；下一次 POST 的 `messages[0]` 是第一次的 `saj`（整条线程被带回）。截图 `*-restored.png` |
| 对话区顶部 "Genie - Linker's AI assistant" + "Continue in the side panel" + 关闭 | e2e "Continue in the side panel hands the same conversation to the dock"：hero 折叠、dock 打开、来源行与同线断言。截图 `*-side-panel.png` |
| #236 附件：精确匹配、看不清、PDF、被拒 | e2e "the #236 attachment states render in the hero"：四种状态各断言文案并截图 `*-nameplate-exact.png`、`*-nameplate-unreadable.png`、`*-datasheet.png`、`*-refused.png`；同一条测试在"看不清"卡上点 "Type the model" / "Modell eingeben"，断言 `.hero-prompt` 的值与焦点（手动输入型号出口） |
| #243 联系卡与 #250 询盘确认卡在 hero 内 | e2e "the #243 contact and #250 inquiry cards send from the hero"：联系卡（访客邮箱+同意）发送后显示 "Your request is with the Linker team"；询盘卡（产品与数量、留言、摘要、访客姓名/邮箱/公司/同意）发送后显示询盘号与 "Inquiry received" 状态。截图 `*-contact.png`、`*-inquiry.png`。测试邮件只到 tester（`linker_commerce_test_mail_to` 在 beforeAll 设置、afterAll 还原；发送计数每次清空） |
| 头部文字与五个收起元素（评审第 1 轮第 7 项） | e2e "the answer and its product cards appear in the hero" 用 `header()` 断言中/英标题与 "Continue in the side panel"、关闭按钮存在，并断言 `.hero-badge`、`.hero-title`、`.hero-subtitle`、`.hero-capsules`、`.hero-footnote` 全部隐藏（`toBeHidden`） |
| 可访问性（评审第 1 轮第 3 项） | 六个触发控件 `aria-expanded`/`aria-controls`；展开时焦点到关闭按钮、关闭时回到触发器；新答案 live region。`controller.test.tsx` 与 `Hero.test.tsx` 断言。dock 的既有回答没有 live region，是先前缺口，本票未改 dock |
| 共享领域逻辑，无两份实现（评审第 1 轮第 4 项） | `src/genie/shared/conversation.ts`（提问/附件名/拒绝码/手动型号）、`blocks.ts`（卡/对比 id 与价格）、`cardActions.ts`（加入草稿/保存方案与卡状态）、`dictation.ts`（听写）；App 与 Hero 都改用，测试 `src/genie/shared/*.test.*`（20） |
| 未交互时与线上像素一致 | `pixel/`：`tests/visual/pixel-parity.mjs`，首页 EN/DE × 1440/390，`unmasked_different_pixels` 全为 0（见 `pixel/report.jsonl` 与 `pixel/results.json`；390 的 live/local 对照图入库，1440 的 22 MB 对照图未入库，命令见下，可复跑） |
| 真实夹具测试（状态机 + 共享会话） | `src/hero/state.test.ts`（8）、`src/hero/session.test.ts`（8，含"每次发送前重读"）、`src/hero/controller.test.tsx`（12）、`src/hero/Hero.test.tsx`（10）、`src/genie/shared/*.test.*`（20）、`tests/php/Unit/HeroTest.php`（4）；`src/genie/App.test.tsx` 新增 dock 重读测试 |
| 首页 hero 写进 13-genie.md | `docs/specs/13-genie.md` §"首页 hero（#232…）" 与 Entries 条目、变更记录 |

## 命令

```bash
just sync g232
just build
just serve g232
LINKER_E2E_SHOTS=$PWD/docs/acceptance/2026-10-19/232/shots just e2e g232 genie-hero
node tests/visual/pixel-parity.mjs docs/acceptance/2026-10-19/232/pixel \
  https://de-linker.com http://127.0.0.1:9144 --widths 1440,390 --paths /,/de/
```

e2e 结果：`28 passed (6.4m)`（Chromium，真实 deepseek-flash 官方通道）。全部截图在 `shots/`
（72 张：6 个控件 × 4 组、答案/卡片、继续入口/dock、复原、侧栏、四种附件状态、联系卡与询盘卡）。

"看不清"状态用 `tests/e2e/fixtures/hero-nameplate-unreadable.jpg`：一张型号栏留空的名牌标签。
真实的模糊铭牌照片（`services/genie/eval/attachments/`）在评测里记为 unreadable，但模型偶尔会猜出
一个型号；为了让截图状态可重复，e2e 用这张确定得到 "The model could not be read." 的夹具。
真实照片的读取质量归 #236 的评测，不在本票。

## 说明

- 手机（≤860 px）上对话区 transcript 限 36vh、hero 上下留白 24px，让追问框与发送行留在屏内；
  桌面 transcript 限 52vh（原型值）。
- 语音用浏览器自带听写；无听写的浏览器只展开并聚焦追问框，不显示死按钮以外的东西。
- "关闭对话区"只卸载 hero 的视图；会话留在服务端（同 cookie 的会话文章），再展开/dock 都接着同一会话。
- 像素门只覆盖未交互的首页；展开后的 hero 是工具面（业主 2026-10-10 裁定工具面可改），
  裁定变更见 `change-ledger.md`。
- hero 内渲染回答文字、产品卡、对比、文档、追问芯片、附件卡，以及 #250 询盘确认卡与 #243
  联系卡；发送后记录留在对话里，与 dock 的同一会话一致（目标 5、6）。
- 评审第 1 轮（PR #346）的 8 项已在本分支处理：对话内询盘/联系卡（P0）、每次发送前重读线程
  （P1-2）、焦点/ARIA/live region（P1-3）、共享领域逻辑（P1-4）、规格纠错（P1-5）、
  CSS 例外入台账（P1-6）、头部/收起元素断言（P1-7）、load 拒绝与共用 ACCEPT（P1-8）。
  dock 的既有回答没有 live region，本票只在规格里记下这一先前缺口。
