# #332 系统失败批 — 结果与缺陷清单

- 日期：2026-10-20。票 #332（地图 #329）。只测试，不改产品。装具与笔记在本目录，`justfile` 只把装具接进 `py_projects`。
- 本地：`c332`，快照 `20261019-1715`（2026-10-19T09:18:02Z；212 个产品）。WP `127.0.0.1:9187`，Genie `127.0.0.1:9189`，索引 `/Users/chesterjohn/de-linker-data/index/builds/20261018T173840Z/index.sqlite`。插件链到本 worktree。
- 场景 23。手判 pass 12，defect 11。归并后的顾客痛点 4 条。
- 证据：`~/de-linker-data/campaign-332/evidence/cases.jsonl`（26 行，23 个 id；同一 id 取最后一行）。`summary.json` 只覆盖第二轮 `--only` 的自动分（pass 5 / defect 9），不发布。界面截图在 `~/de-linker-data/campaign-332/ui/`。生产冒烟在 `evidence/prod-smoke.jsonl`。
- 第一轮在 `stop_genie` 上中断，能力桩也没打中（`rest_pre_dispatch` 优先级被 ACF 清掉）。能力两例以第二轮为准。`RATE-BURST` 的存档 verdict 仍是第一轮评分器的 defect，手判改为 pass。
- 跑完栈是健康的。`c332/mail` 在 2026-10-19 23:00 之后没有新文件。没有发询盘或联系邮件。

## 1. 场景结论

pass：BASE-EN、BASE-DOC、RATE-BURST、ATT-LIMIT、SSE-RESET、REDIS-FLAP、REDIS-DOWN、AB-TIMEOUT、M-SLOW、M500-RETRY、JEV-502、IDX-RETRY。

defect：M500-EN、M500-DE、M500-DOC、M-EMPTY、M-429、IDX-MISS、IDX-BAD、AB-500、SSE-CUT、VPS-DOWN、VPS-KILL。

12 + 11 = 23。

## 2. 缺陷清单

按顾客痛苦排序。最小复现都在 `c332`，问句除注明外为 “Do you stock the SAJ H2-10K-T2?”。

### D1 · 停机时仍像一次成功推荐（7 个场景）

层：提示词（`template.fallback`）。IDX 两例再加一层检索。

dossier §1.15：**部分复刻**。可复刻的是 uxpatterns.dev 的 “explain why an AI response failed and offer a recovery path that matches the real failure mode”。#103 的 `DEGRADED` 只在没有任何可引用 id 时出现（`template.py` 的 `fallback`：`qualified_ids` 与 `product_ids` 都空才走 handoff / DEGRADED）。一旦搜到过产品，句子是 “Here are matching products from our range.”，卡照出，顾客句里没有停机说明。`meta.fallback` 与 `failures[]` 里有真正的错误。

turn log 的 provider/model 仍是 `deepseek` / `deepseek-flash`。顾客句来自 `template.fallback`。卡和 “Net price after partner sign-in” 来自目录。

| 场景 | 秒 | 顾客句 | `failures` |
|---|---|---|---|
| M500-EN | 8.144 | Here are matching products from our range. | 聊天 500，`injected chat 500`，model_name deepseek-flash |
| M500-DE | 3.664 | Hier sind passende Produkte aus unserem Sortiment. | 同上 |
| M-EMPTY | 3.019 | 与 M500-EN 相同 | 空流：ChatCompletion `model` 为 None 的校验错误 |
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

层：工具，加上提示词。

第二轮能力桩打中了 `linker/search-products`（实例 mu-plugin，`rest_pre_dispatch` 优先级 100，匹配 `REQUEST_URI`）。18.824s，HTTP 200，`done`，`fallback` true，`grounded` false。唯一块是 handoff：`Our team will answer that at sales@de-linker.com.` meta.failures 为 “a products turn is not a question for the team”。没有 DEGRADED 句。模型仍是 deepseek-flash。

`template.fallback` 在没有可引用产品时：本轮若已有 handoff 句，就用那句；否则才用 DEGRADED。目录工具失败因此变成销售邮箱。handoff 块渲染成段落，不发信。`c332/mail` 无新文件。旗标删除后的重试是正常的扎实产品回答。

第一轮的 AB-500 自动 defect 作废（桩未触发）。

### D3 · SSE 截断：当场有错，刷新后错误消失（SSE-CUT）

层：UI 状态。

dossier §1.15：**须自行设计**。SSE 中途断流的界面状态与重试，没有竞品材料。

代理放在 Genie 与 WP 之间，保留到第一条 `block` 为止，去掉 `done`。HTTP 200，事件只有 `meta` + `block`，11.677s，route products，fallback false，failures 空。日志 grounded，deepseek-flash。截断块里有 “10 kW”，因为没有 `done`，`Thread::answer` 不渲染，`partial_shown` false。这 10 kW 没有变成已发布事实。

当场：壳 `parseStream` 抛 “stream without done”，停靠条出现 “Genie did not answer. Please try again.” 输入框被清空，问题没有回到输入框。截图 `ui/sse-cut-live-error.png`。

刷新后再打开：用户句 “Do you stock the SAJ H2-10K-T2?” 还在，错误没有，答案没有，卡 0。`reload_hides_error` true。截图 `ui/sse-cut-reload.png`。

代理指回 `http://127.0.0.1:9189` 后，在同一对话里再发同一问，约 20s 出扎实回答（T2 不在目录，T3 家族，含目录上的 29.999 kW）。截图 `ui/sse-cut-retry.png`。

### D4 · 502：当场有错，刷新后问题也不见（VPS-DOWN、VPS-KILL）

层：UI 状态。同一节 §1.15 的状态机，须自行设计。当场那句符合壳的协议；缺口是刷新和输入框。

两例都是 HTTP 502，`linker_genie_upstream`，`Genie did not answer.` 故障期间没有 turn 日志。API 重试在服务恢复后健康。VPS-DOWN 1.109s（连接被拒），VPS-KILL 11.123s。

浏览器做在 VPS-DOWN（停进程，`/health` 失败）：用户气泡在，红色 “Genie did not answer. Please try again.”，输入框空。截图 `ui/vps-down-error.png`。刷新后重新打开停靠条：气泡 0，错误 null，输入框空。服务拉起后把同一问重新打进输入框，约 25s 答出 T3。502 不会像 409 那样把问题放回输入框；这次请求没有 200 正文，刷新后什么都不留。

VPS-KILL 走同一代理错误码，浏览器复现记在 VPS-DOWN 上。

## 3. 放行与观察

- BASE-EN、BASE-DOC、M500-RETRY、IDX-RETRY、JEV-502、REDIS 两例：deepseek-flash，`done`，fallback false（Jev 除外见下）。BASE-EN 写明 H2-10K-T2 不在产品数据，最近是 H2-10K-T3。BASE-DOC 写明手册与数据表覆盖 T3，表内有 H2-10K-T3、H2-12K-T3、H2-15K-T2、H2-15K-T3、H2-20K-T2。
- JEV-502：16.346s，`jev_error` = “jev failed after 3 attempts: http 502”，provider/model 仍是 deepseek / deepseek-flash，grounded，fallback false。这是规格允许的降级，写在 SSE meta 里。第二轮日志里桩的 BrokenPipeError 出在该例打印 pass 之后，索引例随后通过。
- SSE-RESET：502，16.232s。服务侧那一轮已经记成 deepseek-flash，管道在正文前断开，顾客只看到 502。重试健康。`reload_hides_error` false。
- AB-TIMEOUT：能力睡 25s，代理在 60.217s（`Proxy::TURN_BUDGET` 60s）返回 502。旗标撤掉后重试健康。第一轮此例作废。
- M-SLOW：桩睡 65s，代理 60.254s 返回 502。恢复问句是 M500-RETRY。
- ATT-LIMIT：429，`linker_genie_attachment_throttled`，0.124s，文案 “The attachment was not accepted.” 额度还在时，打字提问 200。
- RATE-BURST：6 次连续服务回合全部 HTTP 200、done、deepseek-flash、grounded。没有按回合的聊天速率限制。附件限额是 `genie_upload` 每小时 20，与此无关。jsonl 的 defect 来自旧评分器把健康回合的目录 kW 算成编造。
- Redis 抖动和短时停止期间回答仍是 200。`WP_REDIS_GRACEFUL`。结束后 `PONG`。
- 扎实回答里的 29.999 kW 是产品 1181（SAJ H2-30K-T3-DE）的目录交流功率，`SelectionFactsLiveProductsTest` 期望 `1181 => … 29.999 …`。
- 全部有日志的回合都是 deepseek / deepseek-flash。没有静默换模型。

## 4. 生产冒烟

2026-10-20 00:08（响应头 Date 为 Mon, 19 Oct 2026 16:08 GMT）对 `https://de-linker.com` 打了 3 次正常 `POST /wp-json/linker-ai/v1/genie/turn`。没有注入故障，没有附件，没有询盘。三次都是最终 URL 与请求 URL 相同（无 Location），HTTP 200，`done` true，`fallback` false，`grounded` true，`failures` 空，`jev_error` null。对话 7572、7573、7574 的 DELETE 都是 200。

选出的响应头（三次同形，Date 不同）：

| 探针 | 问句 | Date | 秒 | 对话 |
|---|---|---|---|---|
| P1-EN | Do you stock the SAJ H2-10K-T2? | Mon, 19 Oct 2026 16:08:12 GMT | 23.085 | 7572 |
| P2-DE | Haben Sie den SAJ H2-10K-T2 auf Lager? | Mon, 19 Oct 2026 16:08:38 GMT | 23.280 | 7573 |
| P3-EN | Which three-phase hybrid inverters do you list for a home? | Mon, 19 Oct 2026 16:08:55 GMT | 12.869 | 7574 |

三次共有的头：`Server: LiteSpeed`，`Content-Type: application/json; charset=UTF-8`，`X-Powered-By: PHP/8.3.35`，`X-Robots-Tag: noindex`。记录里没有 `Location`。原文在 `~/de-linker-data/campaign-332/evidence/prod-smoke.jsonl`。进程退出码 0，`{"turns": 3, "failed": []}`。

P1 回答写明产品数据没有 SAJ H2-10K-T2，最近的是 H2-T3 家族，并给出目录卡（价格文案 “Net price after partner sign-in”）。生产 SSE meta 没有 provider/model 字段，本批不从生产 turn log 读模型名。
