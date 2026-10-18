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
| 每个控件原地开聊、不跳页（输入回车、发送、胶囊、拍照、附件、语音） | `tests/e2e/specs/genie-hero.spec.ts` → "every control opens the conversation in place and never navigates"（EN/DE × 1440/390，24/24 通过）；每条断言 URL 不变、`.linker-genie-hero--open` 与 `.linker-genie-hero__surface` 出现。截图 `shots/hero-{en,de}-{1440,390}-{enter,send,capsule,voice,photo-open,attach-open}.png` |
| 展开后真实 Genie 回答与产品卡在 hero 内（桌面四列、手机两列） | e2e "the answer and its product cards appear in the hero"：断言 `.linker-genie-reply` 与 `.linker-card`，并断言 `grid-template-columns` 为 4（1440）或 2（390）。截图 `*-answer.png`、`*-cards.png` |
| 滚出 hero 后出现 "Your Genie conversation · continue"，点开在 dock 继续同一会话 | e2e "out of sight, the way back continues the same conversation in the dock"：断言 pill 可见、dock 打开、来源行与 `saj` 同线、URL 不变。截图 `*-continue-entry.png`、`*-dock-continued.png` |
| 关闭对话区复原 hero，且追问仍是同一会话 | e2e "closing restores the hero and the same conversation continues"：关闭后 surface/类清空、标题可见；下一次 POST 的 `messages[0]` 是第一次的 `saj`（整条线程被带回）。截图 `*-restored.png` |
| 对话区顶部 "Genie - Linker's AI assistant" + "Continue in the side panel" + 关闭 | e2e "Continue in the side panel hands the same conversation to the dock"：hero 折叠、dock 打开、来源行与同线断言。截图 `*-side-panel.png` |
| #236 附件：精确匹配、看不清、PDF、被拒 | e2e "the #236 attachment states render in the hero"：四种状态各断言文案并截图 `*-nameplate-exact.png`、`*-nameplate-unreadable.png`、`*-datasheet.png`、`*-refused.png`；同一条测试在"看不清"卡上点 "Type the model" / "Modell eingeben"，断言 `.hero-prompt` 的值与焦点（手动输入型号出口） |
| 未交互时与线上像素一致 | `pixel/`：`tests/visual/pixel-parity.mjs`，首页 EN/DE × 1440/390，`unmasked_different_pixels` 全为 0（见 `pixel/report.jsonl` 与 `pixel/results.json`；390 的 live/local 对照图入库，1440 的 22 MB 对照图未入库，命令见下，可复跑） |
| 真实夹具测试（状态机 + 共享会话） | `src/hero/state.test.ts`（8）、`src/hero/session.test.ts`（7）、`src/hero/controller.test.tsx`（12）、`src/hero/Hero.test.tsx`（7）、`tests/php/Unit/HeroTest.php`（4）；`src/genie/App.test.tsx` 新增 dock 重读测试 |
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

e2e 结果：`24 passed (4.2m)`（Chromium，真实 deepseek-flash 官方通道）。全部截图在 `shots/`
（64 张：6 个控件 × 4 组、答案/卡片、继续入口/dock、复原、侧栏、四种附件状态）。

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
- hero 内渲染回答文字、产品卡、对比、文档、追问芯片与附件卡；询盘确认卡与联系卡（#250 / #243）
  留在 dock 的完整工作面，经 "Continue in the side panel" 或继续入口接续（同一会话）。
