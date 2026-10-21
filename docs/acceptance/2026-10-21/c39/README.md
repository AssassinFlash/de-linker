# #470 · C39 后半：设计报告 PDF 的浏览器 Download 按钮

记录只此一次。没有改插件、没有改站点、没有合并、没有部署。

- **票**：#470（#437 波 2-1）。缺口是浏览器按钮，不是代理本身。`docs/acceptance/2026-10-15/coverage/README.md` §5bis 只记了实例 curl：`POST /wp-json/linker-ai/v1/engine/report/pdf` → 200 `application/pdf`，EN 48837 B / DE 49529 B，`%PDF-1.4`，3 页。
- **实例**：`c470` = `http://127.0.0.1:9243`，引擎 `http://127.0.0.1:9244`。快照 `20261019-1715`（`taken` `2026-10-19T09:18:02+00:00`），工作树 `w470` 上 `just pull load c470 latest`。
- **日期**：2026-10-21。Chromium headless（Playwright），视口 1440×900 与 390×844。登录态用 `just login c470 --user c470-walk` 的一次性链接，不发信。`~/de-linker-local/c470/mail` 在走查后仍为空。
- **输入**：住宅表单默认值，与 §5bis 同一组：PLZ `80538`，年用电 5000 kWh，10 kWp，三相。备用电源未选，热泵与电动车未勾。点 `Calculate system` / `System berechnen`，报告出现后再点 Download。

## 实例文件，不是站点改动

`just pull load` 把 `https://de-linker.com` 换成了 `http://127.0.0.1:9243`。两件事只发生在引擎读的那份实例文件 `~/de-linker-local/c470/engine/feed.json` 上。WordPress 数据库没有改，插件与站点代码没有改。

1. 文档 URL 不再满足引擎 schema `^https://de-linker\.com/`。这份文件里的文档 URL 写回 `https://de-linker.com/`。
2. 工程 feed 只收录引用主机为 `de-linker.com` / `www.de-linker.com` 的规格。替换之后，621 条托管引用的主机变成 `127.0.0.1`，端点把它们全部丢掉，逆变器 `figures` 为空。同一输入的 `/design/residential` 因此是 `no_candidate`，Download 按钮不会挂上。这是本地 search-replace 的副作用，不是按钮缺陷。

文件里按同一条规则补回这些引用（主机是 `127.0.0.1` 的才算被替换过的托管引用），URL 写回 `https://de-linker.com/`：83 个产品，610 条规格。引擎进程对着这份文件重启。没有跑 `just serve`，因为它会重新拉取被剥空的端点并覆盖这份文件。

补回之后，同一输入给出方案（GoodWe GW10K-ETA-G20 + GW6.0-BAT-D-G20），报告与 Download 按钮出现。

## 怎么比的字节

按钮的 `fetch` 得到代理响应，再用 `<a download>` 保存。响应头是 `Content-Disposition: attachment`。Playwright 的 `response.body()` 对这一响应是空的（`responseReceived` 时 `encodedDataLength` 只有头那么大；`loadingFinished` 之后才有正文）。所以字节对比不用那条空读数。

对比的是页面自己的 `fetch` 克隆（按钮客户端实际收到的那一份）和浏览器 `download` 事件落盘的文件。八个状态都逐字节相同。

同一请求体再 curl 一次代理，得到的仍是 `%PDF-1.4`、同样的页数和标题。两次调用的字节不保证相同：PDF 里写了 `CreationDate`。只观察到一次差 1 字节：`1440-de-logged-in` 的下载是 49529 B（`D:20261021080701+08'00'`），紧接着的重放是 49530 B（`D:20261021080702+08'00'`）。差在时间戳及其后的交叉引用偏移，不是会话，也不是按钮。

`URL.revokeObjectURL` 紧跟在 `link.click()` 之后。这八次点击里下载事件都发出了，落盘文件与当次响应一致，没有空文件。

## 结果：八态都通过

按钮标记不随登录变化。访客与已登录都点了，因为浏览器会带 cookie。`[data-linker-app="genie"]` 的 `data-signed-in`：访客 `0`，已登录 `1`。

点完之后状态段为空，按钮回到空闲文案，没有 “The PDF could not be created. Try again.” / “Das PDF konnte nicht erstellt werden. Versuchen Sie es erneut.”

| 状态 | 登录 | 按钮 | 文件 | 字节 | 头 | 页 | 标题 | 与当次代理响应 |
|---|---|---|---|---|---|---|---|---|
| 1440 EN 访客 | 0 | Download PDF | `linker-design-report-80538-en.pdf` | 48835 | `%PDF-1.4` | 3 | Design report | 相同 |
| 390 EN 访客 | 0 | Download PDF | 同上 | 48835 | `%PDF-1.4` | 3 | Design report | 相同 |
| 1440 EN 已登录 | 1 | Download PDF | 同上 | 48835 | `%PDF-1.4` | 3 | Design report | 相同 |
| 390 EN 已登录 | 1 | Download PDF | 同上 | 48835 | `%PDF-1.4` | 3 | Design report | 相同 |
| 1440 DE 访客 | 0 | PDF herunterladen | `linker-design-report-80538-de.pdf` | 49530 | `%PDF-1.4` | 3 | Auslegungsbericht | 相同 |
| 390 DE 访客 | 0 | PDF herunterladen | 同上 | 49530 | `%PDF-1.4` | 3 | Auslegungsbericht | 相同 |
| 1440 DE 已登录 | 1 | PDF herunterladen | 同上 | 49529 | `%PDF-1.4` | 3 | Auslegungsbericht | 相同 |
| 390 DE 已登录 | 1 | PDF herunterladen | 同上 | 49530 | `%PDF-1.4` | 3 | Auslegungsbericht | 相同 |

代理当次响应：八态都是 200 `application/pdf`。重放也是 200 `application/pdf`，页数与标题与下载文件相同。EN 重放 48835 B；DE 重放 49530 B（上面那一次时间戳差除外）。

相对 §5bis 的 48837 / 49529：版本、页数、标题一致。EN 少 2 字节，DE 落在 49529 或 49530。这是六天后的目录与时间戳，不是浏览器和代理各给一份。当次点击里，浏览器文件等于代理响应。

390 的视口截图把按钮滚进画面后，底部步骤条盖住报告更下面的行。按钮本身完整可见，点击成功。这是现有步骤条，不是这次下载的失败态。

## 文件

- `screenshots/<state>-{before,report,button,after,after-button}.png`
- `downloads/<state>.pdf`：浏览器下载事件落盘的文件
- `<state>.json`、`results.json`：每态读数。访客与已登录的按钮 HTML 相同：`<button type="button" class="linker-button linker-button--primary" aria-busy="false">…</button>`
