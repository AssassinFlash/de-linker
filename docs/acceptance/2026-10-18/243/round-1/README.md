# #243 · 评审第 1 轮（PR #303）· 本轮修改与证据

实例 g243（`just serve g243`：真实 Jev 经 OpenRouter、deepseek-flash 经官方 API）。分支已重放到含 #297、#302 的 origin/main。
第 1–3、5 条（经 #246 的 `Sender::message()` 写记录、发回执）等 PR #290 合并后在本 PR 里接入，本轮未做。

| 条 | 处理 | 证据 |
|---|---|---|
| 4 已发出的卡留在对话里 | 发出后卡进历史，紧跟提供它的回答（`ContactSent`）；下一轮、重载后都在且只一张；会话读取路由返回 `contacts: [{after, email}]` | `App.test.tsx`（下一轮与重载两例，含"卡在下一轮重新挂载并再报一次已发出"的回归），`api/turn.test.ts`，`ProxyTest`，`GenieContactTest::test_the_sent_card_stays_in_the_conversation`；e2e 8/8，截图 `screens/*-after.png`、`*-reload.png` |
| 6 短语表收窄 | 去掉单独的 team / expert / engineer / Techniker；team 只在 your team、the Linker team、Ihrem Team 时算，agent 只带冠词时算 | `test_contact.py` 正反例（含 team portal、expert mode、engineer's guide，EN/DE）；评测 `portal-*`、`expert-*`、`engineer-*` 均无卡 |
| 7 公司类卡不连续两轮 | 邮箱句每轮都有，卡在上一轮已提供时不附；附卡后 `ground.shipped` 检查整份出货回答（一张卡、在最后、正是决定的那种、公司类只有邮箱句 + 卡）；规格"结构保证"与 R8 已改 | `test_contact.py::test_the_service_card_is_not_offered_twice_in_a_row`，`test_ground_understanding.py` 两例；评测 `service-en#1–3`：卡、无、卡，三轮都有邮箱句 |
| 8 重复判定 | 后一句不加实词、带数字的词（型号、数量）不变、共有词 Jaccard ≥ 0.5；`repeats.json` 39 对（含 8 对真实追问反例：加 backup / Notstrom、加 15 kWh、换同系列型号）0 到 0.75 之间任何切线全对，取 0.5 | `test_contact.py`（39 对参数化）；评测 `followup-en#1–3` 无卡 |
| 9 不满覆盖 | 每种语言 5 句不满 + 2 句中性 | 评测 `unhappy-{en,de}-1..5` 均 `dissatisfied`，`neutral-*` 均无卡 |
| 10 重放与 i18n | 重放到 origin/main；`just i18n-commerce g243`、`just i18n-tools` 重新生成，覆盖门 clean；与 main 的 `.mo` 对比：两个插件 **0 丢失、0 改动** | `mo-compare.txt`（`mo-compare.py`） |
| 11 过期类名 | `ContactRequest` 文档注释改为 `Genie\ContactEmail` | diff |
| 12 一个防护类 | `Linker\Tools\Genie\FormGuard`：HMAC 戳（门名在签名里）+ `STAMP_LIFETIME` + `MIN_SECONDS` + `address()` + 每小时 / 每天两个 `RateLimit`；`ConversationMail` 与 `ContactRequest` 都用它，各带有出处的上限；`ContactGuard` 删除；卡改用 `started` + `started_nonce` | `FormGuardTest`（8 例，含超过寿命、另一扇门的戳）；`ConversationRoutesTest`、`GenieContactTest`（含十进程并发恰好 3 个名额） |
| 13 原因标签一处 | 代码与 TS 只有原因代码；标签只在 `ContactRequest::reason_label()`，以站点语言写进交接（`reason_label`）与记录（`label`），团队邮件与后台会话页显示它；commerce 的标签副本删除 | `GenieContactTest::test_the_reason_reaches_the_team_in_the_site_language`（德语请求，团队邮件与记录仍是英文标签） |
| 14 `log.py` 不依赖 `contact` | 日志加 `contact` 列存 `decide` 的原因；`offers()` 只读这一列 | `test_turn.py::test_the_log_keeps_the_offer_as_a_plain_field`，旧库自动补列 |
| 15 `model` | 不经模型的轮次记 `provider=service`、`model=none` | `test_turn.py` |
| 16 启动脚本 | `QualityPage` 用同一个 `$thread`；"used N times"注释改对 | diff |
| 17 phpstan 跨扫 | 注释写明：两插件之间的过滤器与动作契约，集成测试从 commerce 驱动 tools 一侧 | `phpstan.neon.dist` |

触发评测（真实服务）：**44/44**，`triggers.json`（`services/genie/eval/contact/triggers.py`）。
