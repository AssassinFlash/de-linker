# #332 系统失败批 — 结果与缺陷清单

- 日期：2026-10-20。票 #332（地图 #329）。只测试，不改产品。装具与笔记在本目录，`justfile` 只把装具接进 `py_projects`。
- 本地：`c332`，快照 `20261019-1715`（2026-10-19T09:18:02Z；212 个产品）。WP `127.0.0.1:9187`，Genie `127.0.0.1:9189`，索引 `/Users/chesterjohn/de-linker-data/index/builds/20261018T173840Z/index.sqlite`。插件链到本 worktree。
- 原先 23 个场景的手判不变：pass 12，defect 11。补跑 4 条都是 defect。合计记录 27 条，pass 12 / defect 15。归并后的顾客痛点仍是 4 条。
- 证据：`~/de-linker-data/campaign-332/evidence/cases.jsonl`（30 行，27 个 id；同一 id 取最后一行）。`summary.json` 现在只覆盖这次补跑的自动分（pass 0 / defect 4），不发布。第二轮 `--only` 的自动分是 pass 5 / defect 9，文件已被这次运行覆盖，数字留在这里。界面截图在 `~/de-linker-data/campaign-332/ui/`。生产冒烟在 `evidence/prod-smoke.jsonl`。
- `8456cd2c` 的说明写成已经记录半条 block、attachment / reading 截断和空 SSE。那时只有装具单测，没有 c332 的行。这一轮补跑了这四条，行在 `verdicts.jsonl`。
- 第一轮在 `stop_genie` 上中断，能力桩也没打中（`rest_pre_dispatch` 优先级被 ACF 清掉）。能力两例以第二轮为准。`RATE-BURST` 的第一轮自动分把目录 kW 算成编造，已撤回；发布的 `verdict` 是 pass。
- 跑完栈是健康的。`c332/mail` 在 2026-10-19 23:00 之后没有新文件。没有发询盘或联系邮件。

## 1. 场景结论

pass：BASE-EN、BASE-DOC、RATE-BURST、ATT-LIMIT、SSE-RESET、REDIS-FLAP、REDIS-DOWN、AB-TIMEOUT、M-SLOW、M500-RETRY、JEV-502、IDX-RETRY。

defect：M500-EN、M500-DE、M500-DOC、M-EMPTY、M-429、IDX-MISS、IDX-BAD、AB-500、SSE-CUT、VPS-DOWN、VPS-KILL，加上补跑的 SSE-PARTIAL、SSE-ATTACHMENT、SSE-READING、M-EMPTY-STREAM。

原先 12 + 11 = 23。补跑 4 条 defect 之后，12 + 15 = 27。

## 2. 缺陷清单

按顾客痛苦排序。最小复现都在 `c332`，问句除注明外为 “Do you stock the SAJ H2-10K-T2?”。

### D1 · 停机时仍像一次成功推荐（8 个场景）

层：`template.fallback`（`services/genie/src/linker_genie/template.py` 里的函数，不是提示词）。有可引用 id 时句子是目录推荐；没有 id 时才是 handoff 或 DEGRADED。IDX 两例的错误在 `failures[]`（检索），顾客句仍是这个函数。修复票 #410。

dossier §1.15：**部分复刻**。可复刻的是 uxpatterns.dev 的 “explain why an AI response failed and offer a recovery path that matches the real failure mode”。#103 的 `DEGRADED` 只在没有任何可引用 id 时出现（`template.py` 的 `fallback`：`qualified_ids` 与 `product_ids` 都空才走 handoff / DEGRADED）。一旦搜到过产品，句子是 “Here are matching products from our range.”，卡照出，顾客句里没有停机说明。`meta.fallback` 与 `failures[]` 里有真正的错误。

turn log 的 provider/model 列仍是配置名 `deepseek` / `deepseek-flash`（见 §3，不是作答模型）。顾客句来自 `template.fallback`。卡和 “Net price after partner sign-in” 来自目录。

| 场景 | 秒 | 顾客句 | `failures` |
|---|---|---|---|
| M500-EN | 8.144 | Here are matching products from our range. | 聊天 500，`injected chat 500`，model_name deepseek-flash |
| M500-DE | 3.664 | Hier sind passende Produkte aus unserem Sortiment. | 同上 |
| M-EMPTY | 3.019 | 与 M500-EN 相同 | 非流式校验错误：ChatCompletion `model` 为 None。请求没有走流式分支，不是空的 SSE |
| M-EMPTY-STREAM | 5.205 | 与 M500-EN 相同。卡 1179、1181、2063、2064、4107、4108。追问选项是模板值 `none` / `needed` / `needed_accessory_ok` | 空 SSE：HTTP 200，正文没有事件。failures 为 `expected JSON data`。这一轮没有重跑 M500-RETRY |
| M-429 | 3.655 | 与 M500-EN 相同 | 聊天 429，`injected chat 429` |
| M500-DOC | 7.176 | Here is what I found for your question. | 聊天 500。问的是 H2-10K-T2 的最大 PV 输入 |
| IDX-MISS | 4.784 | 产品推荐句 + 卡 | `linker/search-knowledge: document index unavailable: unable to open database file` |
| IDX-BAD | 4.498 | 产品推荐句 + 卡 | `file is not a database` |

M500-EN 的卡是 1179、1181、2063、2064、4107、4108。浏览器（新对话，同一问句）展开后的全文只有 “Here are matching products from our range.”，下面是 SAJ H2-25K-T3 等产品卡，没有 “I could not answer this time.” 截图：`ui/model-500-cards.png`、`ui/model-500-cards-scrolled.png`。

英语兜底还带一个 backup 追问，选项是模板里的内部值 `none` / `needed` / `needed_accessory_ok`（`template.py` `_ask_options`）。浏览器上这三个词原样出现。德语同一路径的选项是 “ohne / benötigt / benötigt, Zubehör akzeptiert”。

M500-DOC 的文档块标签是 “SAJ H2 10-30K user manual, German and English (covers the H2-10K-T3) · pp. 8, 37, 38”，URL 为站上该 PDF 的 `#page=8`。渲染文本里没有新编的 kW。缺陷是模型没有跑成，句子仍表示这份文档回答了问题，且没有 DEGRADED 句。

IDX 两例的路由是 `documents`，问句要求用数据表。规格写的是检索失败则整轮兜底、不做关键词回退。`fallback` 为真，顾客看到的是产品推荐。

故障撤掉后的 M500-RETRY（21.9s）与 IDX-RETRY（17.6s）都是 deepseek-flash、grounded、fallback false。

### D2 · 产品搜索 500 被说成去信销售（AB-500）

层：`template.fallback` 的 `_outage`。`linker/search-products` 返回 500 是触发（`understanding.call_failures`：`linker/search-products returned 500 for {'input[series]': 'saj-h2', 'input[lang]': 'en', 'input[limit]': 6}`，mu-plugin 的正文是 `injected ability 500`）。函数在本轮已有 handoff 句时用那句，否则才用 DEGRADED。不是提示词。修复票 #410。

第二轮能力桩打中了 `linker/search-products`（实例 mu-plugin，`rest_pre_dispatch` 优先级 100，匹配 `REQUEST_URI`）。18.824s，HTTP 200，`done`，`fallback` true，`grounded` false。唯一块是 handoff：`Our team will answer that at sales@de-linker.com.` meta.failures 为 “a products turn is not a question for the team”。没有 DEGRADED 句。模型仍是 deepseek-flash。

`template.fallback` 在没有可引用产品时：本轮若已有 handoff 句，就用那句；否则才用 DEGRADED。目录工具失败因此变成销售邮箱。handoff 块渲染成段落，不发信。`c332/mail` 无新文件。旗标删除后的重试是正常的扎实产品回答。

第一轮的 AB-500 自动 defect 作废（桩未触发）。

### D3 · SSE 截断：当场有错，刷新后错误消失（SSE-CUT、SSE-PARTIAL、SSE-ATTACHMENT、SSE-READING）

层：UI 状态。修复票 #411。

dossier §1.15：**须自行设计**。SSE 中途断流的界面状态与重试，没有竞品材料。先记录的一刀是第一条完整 `block` 之后。半条 block、attachment 事件、reading 事件后来在 c332 上重放，四刀的刷新结论相同，后三刀没有截图。

代理放在 Genie 与 WP 之间，保留到第一条 `block` 为止，去掉 `done`。HTTP 200，事件只有 `meta` + `block`，11.677s，route products，fallback false，failures 空。日志 grounded，deepseek-flash。截断块里有 “10 kW”，因为没有 `done`，`Thread::answer` 不渲染，`partial_shown` false。这 10 kW 没有变成已发布事实。

当场：壳 `parseStream` 抛 “stream without done”，停靠条出现 “Genie did not answer. Please try again.” 输入框被清空，问题没有回到输入框。截图 `ui/sse-cut-live-error.png`。

刷新后再打开：用户句 “Do you stock the SAJ H2-10K-T2?” 还在，错误没有，答案没有，卡 0。`reload_hides_error` true。截图 `ui/sse-cut-reload.png`。

代理指回 `http://127.0.0.1:9189` 后，在同一对话里再发同一问，约 20s 出扎实回答（T2 不在目录，T3 家族，含目录上的 29.999 kW）。截图 `ui/sse-cut-retry.png`。

补跑的三刀走同一个代理，问句仍是 “Do you stock the SAJ H2-10K-T2?”。判定都是 defect：HTTP 200，没有 `done`，`partial_shown` false，GET 线程里问题还在、没有答案。代理撤掉后的重试是健康的产品回答。没有截图，当场那句 “Genie did not answer.” 是壳对无 `done` 的 200 的路径，不是另一次看屏。

| 场景 | 秒 | 截在哪里 | 顾客正文 | 日志 |
|---|---|---|---|---|
| SSE-PARTIAL | 25.145 | 第一条 `block` 的 JSON 中间。正文不以空行结束，块解析不成，`done` 不在缩短后的正文里 | 事件名 `meta`、`block`。块里的目录 kW 没有渲染 | deepseek-flash，route products |
| SSE-ATTACHMENT | 0.461 | `attachment` 的 JSON 中间。没有 `reading`，没有 `block`，没有 `done` | 事件名 `meta`、`attachment` | 零件清单路径，provider `service`，model `none`。上传 `h2.csv`（一行 `SAJ H2-10K-T3`） |
| SSE-READING | 0.25 | `reading` 的中间。缩短后的上游含 `reading` 且没有 `done` | WordPress 剥掉 `reading`，顾客正文是 `meta` 加一条完整的 attachment，没有 block | 同上，零件清单路径 |

`cut_observed.marker_present` 三刀都是 true，`done_in_shortened` 都是 false。

### D4 · 502：当场有错，刷新后问题也不见（VPS-DOWN、VPS-KILL）

层：UI 状态。同一节 §1.15 的状态机，须自行设计。修复票 #411。当场那句符合壳的协议；缺口是刷新和输入框。

两例都是 HTTP 502，`linker_genie_upstream`，`Genie did not answer.` 故障期间没有 turn 日志。API 重试在服务恢复后健康。VPS-DOWN 1.109s（连接被拒），VPS-KILL 11.123s。

浏览器做在 VPS-DOWN（停进程，`/health` 失败）：用户气泡在，红色 “Genie did not answer. Please try again.”，输入框空。文件名是 `ui/vps-down-error.png`。刷新后重新打开停靠条：气泡 0，错误 null，输入框空。服务拉起后把同一问重新打进输入框，约 25s 答出 T3。502 不会像 409 那样把问题放回输入框；这次请求没有 200 正文，刷新后什么都不留。

`ui/vps-down-error.png` 与 `ui/sse-cut-live-error.png` 字节相同（`cmp -s` 退出码 0，SHA-256 `44a412dd09ab236a60c613365902d5d6076ca19cec80e3d990d51a077c60ab85`，1938808 字节）。同一张渲染不能同时当两个场景的界面证据。VPS-DOWN 的主证据是 502 那一行：HTTP 502，`linker_genie_upstream`，1.109s，故障期间没有 turn 日志。这张 PNG 只记在 SSE-CUT 的当场错误上。

VPS-KILL 走同一代理错误码。浏览器只做了 VPS-DOWN 的当场错误，没有单独截 VPS-KILL，也没有截 VPS-DOWN 刷新后的空停靠条。VPS-KILL 的界面是从同一 502 推出来的，不是另一次看屏。

### 界面覆盖的界限

看过屏的只有英语、桌面宽度的停靠条，三态：

- 模型 500（M500-EN）：`ui/model-500-cards.png`、`ui/model-500-cards-scrolled.png`
- SSE 截断（完整 block 之后）：`ui/sse-cut-live-error.png`、`ui/sse-cut-reload.png`、`ui/sse-cut-retry.png`
- VPS 停机的当场 502：HTTP 行（见 D4）。`ui/vps-down-error.png` 与 `sse-cut-live-error.png` 是同一文件，不能另作此态的截图。

没有的：390 宽、德语界面、VPS-KILL、VPS-DOWN 刷新后的空状态。半条 block、attachment / reading 事件已经对 c332 重放，仍没有截图。也没有 Jev 502、AB-500 的 handoff 句的截图。M500-DE 的德语句子来自 API 正文，不是截图。VPS-DOWN 的当场画面没有独立截图，主证据是 502 行。“界面没有空白”只覆盖模型 500 和 SSE-CUT 当场这两张不同的图，不是一张状态表。390 宽、德语和 VPS-KILL 的截图跟在 #433，这轮没有补拍。

## 3. 放行与观察

- BASE-EN、BASE-DOC、M500-RETRY、IDX-RETRY、JEV-502、REDIS 两例：deepseek-flash，`done`，fallback false（Jev 除外见下）。BASE-EN 写明 H2-10K-T2 不在产品数据，最近是 H2-10K-T3。BASE-DOC 写明手册与数据表覆盖 T3，表内有 H2-10K-T3、H2-12K-T3、H2-15K-T2、H2-15K-T3、H2-20K-T2。
- JEV-502：16.346s，`jev_error` = “jev failed after 3 attempts: http 502”，turn log 列仍是配置名 deepseek / deepseek-flash，grounded，fallback false。这是规格允许的降级，写在 SSE meta 里。第二轮日志里桩的 BrokenPipeError 出在该例打印 pass 之后，索引例随后通过。
- SSE-RESET：502，16.232s。服务侧那一轮已经记成 deepseek-flash，管道在正文前断开，顾客只看到 502。重试健康。`reload_hides_error` false。
- AB-TIMEOUT：能力睡 25s，代理在 60.217s（`Proxy::TURN_BUDGET` 60s）返回 502。旗标撤掉后重试健康。第一轮此例作废。
- M-SLOW：桩睡 65s，代理 60.254s 返回 502。恢复问句是 M500-RETRY。
- ATT-LIMIT：429，`linker_genie_attachment_throttled`，0.124s，文案 “The attachment was not accepted.” 额度还在时，打字提问 200。
- RATE-BURST：6 次连续服务回合全部 HTTP 200、done、日志列 deepseek-flash、grounded。没有按回合的聊天速率限制。附件限额是 `genie_upload` 每小时 20，与此无关。第一轮自动分把健康回合的目录 kW 算成编造，已撤回。
- Redis 抖动和短时停止期间回答仍是 200。`WP_REDIS_GRACEFUL`。结束后 `PONG`。
- 扎实回答里的 29.999 kW 是产品 1181（SAJ H2-30K-T3-DE）的目录交流功率，`SelectionFactsLiveProductsTest` 期望 `1181 => … 29.999 …`。
- 有日志的回合，turn log 的 `provider` / `model` 列是 `deepseek` / `deepseek-flash`。这两列是 `app.py` 用 `provider_name()` / `model_name()` 写进去的：前者是常量 `deepseek`，后者是 `GENIE_MODEL` 或默认 `deepseek-flash`（`agent.py` 的 `DEFAULT_MODEL`）。它们不是聊天补全请求里的模型 id。`8456cd2c` 拿掉的日志列检查因此留着缺口。替换在请求侧：聊天桩记下请求 JSON 的 `model`（慢响应在入睡前记下）。`faults.silent_switch_reasons` 要求每一笔都是 `deepseek-flash`，并且本机 OpenRouter 桩的命中次数是 0。没有记下任何 `model` 也算失败。聊天故障例同时拉起这个 OpenRouter 桩，但不把它写成 `OPENROUTER_BASE_URL`：Jev 仍走真实 OpenRouter，那是规格允许的通道，不进这个计数。计数增加只说明有请求打到了这个桩。`grade` 在行里有 `requested_models` 和 `openrouter_hits` 时才用这条。已经入库的 27 条手判没有这两个字段，不因此改判。下一次 `chat()` 会把它们写进行里。失败仍写在 `meta.failures` 或 `jev_error`，顾客句来自 `template.fallback` 或壳的错误句。Jev 502 的 `jev_error` 在 SSE meta 里，这是规格允许的降级。

## 4. 生产冒烟

2026-10-20 00:08（响应头 Date 为 Mon, 19 Oct 2026 16:08 GMT）对 `https://de-linker.com` 打了 3 次正常 `POST /wp-json/linker-ai/v1/genie/turn`。没有注入故障，没有附件，没有询盘。三次都是最终 URL 与请求 URL 相同（无 Location），HTTP 200，`done` true，`fallback` false，`grounded` true，`failures` 空，`jev_error` null。对话 7572、7573、7574 的 DELETE 都是 200。这一轮的装具在 `--confirm-production` 下还要求 `--evidence`，并在 DELETE 之后 GET `/genie/conversation`，对话 id 仍在就失败；`fallback` 为真或 `failures` 非空也失败。当时的三次记录满足这些条件，但那次进程还没有做 GET 复查。

选出的响应头（三次同形，Date 不同）：

| 探针 | 问句 | Date | 秒 | 对话 |
|---|---|---|---|---|
| P1-EN | Do you stock the SAJ H2-10K-T2? | Mon, 19 Oct 2026 16:08:12 GMT | 23.085 | 7572 |
| P2-DE | Haben Sie den SAJ H2-10K-T2 auf Lager? | Mon, 19 Oct 2026 16:08:38 GMT | 23.280 | 7573 |
| P3-EN | Which three-phase hybrid inverters do you list for a home? | Mon, 19 Oct 2026 16:08:55 GMT | 12.869 | 7574 |

三次共有的头：`Server: LiteSpeed`，`Content-Type: application/json; charset=UTF-8`，`X-Powered-By: PHP/8.3.35`，`X-Robots-Tag: noindex`。记录里没有 `Location`。原文在 `~/de-linker-data/campaign-332/evidence/prod-smoke.jsonl`。进程退出码 0，`{"turns": 3, "failed": []}`。

P1 回答写明产品数据没有 SAJ H2-10K-T2，最近的是 H2-T3 家族，并给出目录卡（价格文案 “Net price after partner sign-in”）。生产 SSE meta 没有 provider/model 字段，本批不从生产 turn log 读模型名。
