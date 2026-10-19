# #332 场景索引

手判，写在 `verdicts.jsonl` 的 `verdict` 和 `reasons`。第一轮自动分里 `RATE-BURST` 的 defect 已撤回。第一轮 `AB-500` / `AB-TIMEOUT` 的桩没有打中，不采用；下表是第二轮，外加后来在 c332 上补跑的四条。原始行在 `~/de-linker-data/campaign-332/evidence/cases.jsonl`（同一 id 取最后一行）。AB-500 的注入 500 在摘要的 `injected_error`。

| 场景 | 故障 | 手判 | 顾客看见 | 重试 | 模型 |
|---|---|---|---|---|---|
| BASE-EN | 无 | pass | T2 不在产品数据里，最近是 H2-10K-T3 | — | deepseek-flash |
| BASE-DOC | 无 | pass | 手册/数据表覆盖 T3；点名表内型号，T2 没有 | — | deepseek-flash |
| RATE-BURST | 连续 6 问，无聊天限额 | pass | 六问都 done，目录功率 | — | deepseek-flash |
| ATT-LIMIT | 附件小时额度顶满后再传 JPEG | pass | 429，`The attachment was not accepted.` | 同额度下打字提问 200 | — |
| SSE-CUT | 代理截掉 `done` | defect | 当场 “Genie did not answer.”；刷新后问题还在，错误和答案都没有 | 代理撤掉后健康 | 日志 deepseek-flash；块未渲染 |
| SSE-PARTIAL | 代理截在第一条 block 的 JSON 中间 | defect | 200，块解析不成，没有 `done`；刷新后问题还在，没有答案。没有截图 | 代理撤掉后健康 | deepseek-flash；`partial_shown` false |
| SSE-ATTACHMENT | 代理截在 attachment 事件中间；本轮上传 `h2.csv` | defect | 200，没有 reading / block / `done`；刷新后问题还在，没有答案。没有截图 | 代理撤掉后健康 | 零件清单，provider `service`，model `none` |
| SSE-READING | 代理截在 reading 事件中间；本轮上传 `h2.csv` | defect | 顾客正文是完整 attachment，没有 block；刷新后问题还在，没有答案。没有截图 | 代理撤掉后健康 | 零件清单，provider `service`，model `none` |
| SSE-RESET | 代理在正文前重置 | pass | 502，`Genie did not answer.` | 健康 | 服务侧 deepseek-flash，顾客没收到正文 |
| VPS-DOWN | 停本地 Genie | defect | 当场同一句 502；刷新后问题、错误、输入框都空 | 服务恢复后重打健康 | 故障时无日志行 |
| VPS-KILL | 杀掉本地 Genie | defect | 同一 502。没有单独看屏，界面从 VPS-DOWN 推得 | API 重试健康 | 故障时无日志行 |
| REDIS-FLAP | 重启本机 Redis | pass | 正常产品回答 | — | deepseek-flash |
| REDIS-DOWN | Redis 停一阵再拉起 | pass | 正常产品回答 | — | deepseek-flash |
| AB-500 | `linker/search-products` 返回 500 | defect | `Our team will answer that at sales@de-linker.com.` | 旗标撤掉后健康 | deepseek-flash |
| AB-TIMEOUT | 同一能力睡 25s | pass | 代理 60.2s 返回 502 | 旗标撤掉后健康 | 无完整流 |
| M500-EN | 聊天补全 500 | defect | “Here are matching products from our range.” + 六张卡 | 见 M500-RETRY | deepseek-flash（日志；模型调用失败） |
| M500-DE | 聊天补全 500，德语 | defect | “Hier sind passende Produkte aus unserem Sortiment.” + 卡 | 见 M500-RETRY | deepseek-flash |
| M500-DOC | 聊天补全 500，文档问句 | defect | “Here is what I found for your question.” + 手册块 | 见 M500-RETRY | deepseek-flash |
| M-EMPTY | 非流式补全缺 `model`（不是空 SSE） | defect | 与 M500-EN 相同的产品句和卡 | 见 M500-RETRY | 日志列 deepseek-flash |
| M-EMPTY-STREAM | 空 SSE：HTTP 200，正文没有事件 | defect | 与 M500-EN 相同的产品句和卡（1179、1181、2063、2064、4107、4108） | 这一轮没有重跑 | 日志列 deepseek-flash；failures 为 `expected JSON data` |
| M-429 | 聊天补全 429 | defect | 与 M500-EN 相同的产品句和卡 | 见 M500-RETRY | deepseek-flash |
| M-SLOW | 聊天桩先睡 65s | pass | 代理 60.3s 返回 502 | 桩撤掉后的 M500-RETRY 健康 | 无完整流 |
| M500-RETRY | 桩已撤 | pass | T2 不在目录，列出 T3 | — | deepseek-flash |
| JEV-502 | 本机 OpenRouter 502 | pass | 扎实的 T3 回答；meta `jev_error` | — | deepseek-flash |
| IDX-MISS | 索引路径不存在 | defect | 文档问句，顾客看到产品推荐句和卡 | 见 IDX-RETRY | deepseek-flash |
| IDX-BAD | 索引文件损坏（`file is not a database`） | defect | 同上 | 见 IDX-RETRY | deepseek-flash |
| IDX-RETRY | 真索引恢复 | pass | 手册覆盖 T3，T2 无最大 PV 输入数字 | — | deepseek-flash |

浏览器看过的只有英语、桌面宽度：`~/de-linker-data/campaign-332/ui/` 里 `model-500-cards.png`、`model-500-cards-scrolled.png`、`sse-cut-live-error.png`、`sse-cut-reload.png`、`sse-cut-retry.png`、`vps-down-error.png`。没有 390 宽，没有德语界面，没有 VPS-KILL 的截图，没有 VPS-DOWN 刷新后的截图。这三处跟在 #433，这轮没有补拍。

原来的 23 条手判不变。SSE-PARTIAL、SSE-ATTACHMENT、SSE-READING、M-EMPTY-STREAM 是后来对 c332 的补跑，四条都是 defect。`M-EMPTY` 仍是非流式校验错误；`M-EMPTY-STREAM` 才是零事件的 SSE，failures 为 `expected JSON data`。半条 block 和 attachment / reading 的截断没有截图。
