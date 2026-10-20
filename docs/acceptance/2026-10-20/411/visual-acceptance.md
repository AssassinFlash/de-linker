# #411 视觉验收（本地快照实例）

实例 `c411`（`http://127.0.0.1:9215`），快照 `20261019-1715`（2026-10-19 09:18 UTC），插件来自分支 `fix/411-failure-state` 的检出。截图由 `capture.mjs` 用 Playwright（`tests/e2e` 的依赖）拍摄，浏览器同机同视口：1440×900 与 390×844；EN（`/`）与 DE（`/de/`）。

四个状态都走线上代码：

| 状态 | 达到方式 |
| --- | --- |
| `upstream` | 真实 dock 提问；turn 路由回 502。问句回到输入框，显示失败句与 Try again。 |
| `truncated` | 真实 dock 附 PDF 后提问；turn 路由回没有 `done` 的流。问句与文件 chip 留在输入框上，部分回答不渲染。 |
| `omitted-single` | 预置一条 `linker-genie-turn-failure` 记录（kind `upstream`，`omitted: ["datasheet.pdf"]`），打开 dock；失败句后是单文件提醒。 |
| `omitted-plural` | 同上，`omitted` 两个文件；提醒是复数句，不列文件名。 |

`omitted-*` 用预置记录，因为配额耗尽无法在浏览器里按需制造；这正是刷新后读回记录的路径。cookie 横幅在截图前按访客操作接受。

文件名：`live-<state>-<width>-<lang>.png`。
