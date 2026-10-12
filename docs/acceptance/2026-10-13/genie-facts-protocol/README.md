# Genie 事实与协议（登记册 C2 / C12 / C18，2026-10-13）

来源：`docs/debt/REGISTRY-2026-10-12.md` 的 C2、C12、C18，以及 PR #96 交回的 pending-main（R7 未登录德语、grounding 拒答后的兜底）。

## C2 未登录德语与兜底

- 未登录问「Wo steht meine Proforma?」时，`inquiry-status` 回 401，`facts.py` 记成 `inquiry.login_required`。提示词要求这一事实只回答登录句，不得调用 handoff-team。grounding 拒掉邮箱句；兜底模板出登录句，不出团队邮箱句。
- grounding 拒答后的兜底：有合格商品时只出合格卡片，正文引用它们，德语行不混英文功能词；没有可引用事实时出降级声明，不借用邮箱句。
- 判分测试：`services/genie/tests/test_cycle.py`、`test_ground.py`、`test_agent.py`。

## C12 检索探针（单轮，不是 11 轮一致率）

命令（在 `services/genie/eval/judges` 下）：

```
uv run --locked python ../../../../docs/acceptance/2026-10-13/genie-facts-protocol/probe-systemone-set.py
```

结果：`systemone-probe.json`。11 条归档评测题各问一次，走 `JUDGES["jev"]` → OpenRouter `/v1/systemone`，模型自报 `typesafe/jev-1.13-20260917`，合计 29.8 秒，无错误。**这是单趟活调用，不是切换后的一致率。** 试点的 agreement 9/11（`runs/pilot-20261011-t16i2/summary.json`，`pilot.py` 每题只调一次 jev）也是单趟，不是三次平均。本探针不能当作切换后的一致率，是因为它只跑了 jev 一道：`probe-systemone-set.py` 对每题算了 `would_escalate_at_0_6`（置信度低于 `TURN_THRESHOLDS` 即为真），11 题里 7 题的 grounded 会升级，却没有调用 deepseek 级联。9/11 比的是级联终标签和面板确定性结果；这里没有级联终标签。

参考取自轮次日志里该轮自己的 `tool_calls`，不是对一个活着的 WordPress 实例重放。重放需要当时服务这些轮次的实例；日志是还在的记录，也是探针可复现的条件。

## C18 检索重排复测

被 10 分钟超时中断的路径是 `index.eval.rerank --judge deepseek`（`docs/acceptance/2026-10-11/16i/knowledge-index-and-jev.md`：`--sample 20 --depth 50 --judge deepseek --batch 20`，exit 124，日志停在 `encoding 40 queries…`）。密钥在：`~/.config/terravolt-builder/openrouter.env` 与 `deepseek.env` 都有键，不是缺 KEY。

原命令本次复跑四次，每次都停在同一行 `encoding 40 queries…`，进程卡在对端点的 SSL 读上（系统代理 `127.0.0.1:1082` 转到 `72.62.97.95:443`；绕过系统代理后仍走 `198.18.0.1` 的 VPN 网段，一样卡住）。四次都是手动停下的，不是再等满 10 分钟。同一批 40 条查询单独调用 `embed_queries` 用 5.5 秒返回，所以端点本身是通的，挂住的是这条命令进程里的那一次批量编码。

能跑完的复测把同一批查询逐条编码（40 条，136.6 秒），然后调用同一条 `deepseek_rerank` 逐题重排。数字在 `rerank-retest.json`：40 题，候选池上限 0.95，重排后 recall@5 = 0.775，页码正确率 0.857（28 条有引用），重排本身 1667.6 秒，模型 `deepseek-flash`，输入 277221 / 输出 352403 token。这是那条路径的复测，不是原命令自己返回了。切换判断的输入：原命令在这台机器上仍会停在编码阶段；逐条编码后的重排可以跑完，但 40 题要 1667.6 秒，单题最慢 106.5 秒。
