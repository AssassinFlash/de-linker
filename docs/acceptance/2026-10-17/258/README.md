# #258 Genie · Jev 质检上线：本地验收记录（2026-10-17）

实例 g258（`just up g258` + `just pull load g258 latest`，快照 10-15），本分支 `feat/258-jev-quality`。
本地 Genie 用 `GENIE_LOG=<scratch>/g258-turns.sqlite just serve g258`：单独的对话日志，不与其他会话的实例混用（本地默认日志 `~/.cache/linker-genie/turns.sqlite` 是各实例共用的）。
评审进程：`python -m linker_genie.quality.worker`。模型都走真实通道：Jev = typesafe/jev-1.13，经 OpenRouter `/api/v1/systemone`；升级 = deepseek-flash，经 api.deepseek.com。

## 1. 真实对话 → 判定（22 轮，EN 13 / DE 9）

先起评审进程，再把 `docs/research/2026-10-17-knocket/raw/trial/questions.json` 的 20 题，加两道产品页题（4107 EN / 6628 DE），逐题经站点代理 `linker-ai/v1/genie/turn` 发出，每题一个新对话（7071–7092）。

| 指标 | 结果 |
|---|---|
| 判定完成 | 22 / 22，全部交给站点（`stored` 22） |
| 从回答发出到判定 | 中位 32 s，最长 100 s（题目连发，后几轮在队列里排队） |
| 升级给 deepseek-flash | 11 / 22（50%），每次一行 INFO 日志，写明哪一问、置信度多少、阈值多少 |
| 问到 better_pick（有可替换的产品） | 6 轮，全部判 A（真实回答胜出） |
| 标记 | 1 轮：第 9 题（SAJ H2 export limit），grounded = 1（无法核实）。回答提到菜单路径和监控 App，本轮检索结果里没有这两项。这道题正是 #257 要修的失分题 |
| 引用核验不过 | 0 |
| 成本 | 全部 $0.0478，每轮 $0.00217 |

逐轮结果：`e2e/verdicts.json`；对话与 turn 编号：`e2e/turns.json`；评审日志：`e2e/judge-worker.txt`。

日志样例（升级）：

```
INFO linker_genie.quality: turn 15 escalated to deepseek-flash: grounded 0.31 < 0.6; appropriate 0.16 < 0.5
INFO linker_genie.quality: turn 15 judged {'grounded': '2', 'appropriate': 'yes'}
```

## 2. OpenRouter 失败显式报错（真实端点）

新发一题（对话 7093），然后用故意写错的 `OPENROUTER_API_KEY` 跑一轮（`e2e/openrouter-failure.txt`）：

```
ERROR linker_genie.quality: turn 23 (conversation 7093) not judged, attempt 1 of 3: OpenRouter: first judge: https://openrouter.ai/api/v1/systemone: HTTP 401: {"error":{"message":"User not found.","code":401}}
```

- deepseek-flash 没有被调用来顶替 Jev：失败不算"不确定"，不升级，也不换模型。
- 站点收到状态上报。后台列表页首出现"最近一次评审错误"提示，"未能评判"筛选列出这一轮（截图 `*-not-judged.png`、`*-conversation-failed.png`）。
- 评审进程重启后，提示仍在：错误从已存的失败记录读出，进程内存不保留（测试 `test_a_restarted_worker_still_reports_an_unresolved_failure`）。
- 换回真实密钥后，10 分钟后自动重试并判定成功（`e2e/judge-worker-3.txt`）。提示随之消失（截图 `*-recovered-*.png`）。

## 3. 站点侧

- 路由 `POST linker-ai/v1/genie/quality` 的令牌放在请求头 `X-Linker-Judge-Token`。实测：不带令牌 401；令牌错误 401；令牌正确 200 `{"stored":[]}`。
- **发现**：LiveCanvas 自带的 template-system 在 `rest_pre_dispatch` 上把任何 REST 请求的 `Authorization: Bearer <令牌>` 当 JWT 解码，令牌不是 JWT 就直接 500（"Wrong number of segments"）。所以令牌不能走 `Authorization`。线上装着同一个 LiveCanvas，会遇到同样的问题。
- 每日摘要接口 `apply_filters( 'linker_tools_genie_quality_summary', null )` 在 g258 上的返回：

```
judged 22, flagged 1, escalated 11, failed 0, skipped 0, worker_stale false
line: "Genie quality check, last 24 hours: 22 answers judged, 1 flagged, 11 decided by the second judge, 0 could not be judged."
```

## 4. 截图（1440 / 390 × EN / DE）

状态：`list` 全部、`flagged` 标记、`not-judged` 未能评判（有错误提示）、`conversation-flagged` 被标记的对话、`conversation-escalated` 升级过的对话、`conversation-failed` 未能评判的对话、`recovered-list` 与 `recovered-conversation` 重试成功之后。

- 后台页面只用 WordPress 核心的后台样式（widefat 表格、notice、subsubsub），没有插件 CSS。390 宽度下表格用核心的 `fixed` 布局，长网址会折行，页面不出现横向滚动。
- 截图里的 LiveCanvas 授权横幅和 SEOPress 重定向提示是本地快照的现状，归 #252 处理，与本票无关。
- 日期格式 `2026年10月17日 pm7:50` 来自站点自身的 `date_format` / `time_format` 设置（快照照搬线上）。
- 快照里员工账号的界面语言是 `zh_CN`。截图时临时改成 `en_US` 和 `de_DE_formal`，拍完已改回 `zh_CN`。

## 5. 文案

本票没有改动客户可见的文案。新增的都是员工后台字符串，加上团队每日摘要里的一句；EN/DE 都在 `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`，德语用 Sie 体，`i18n-coverage` 检查通过。所以不走客户文案对抗评审。
