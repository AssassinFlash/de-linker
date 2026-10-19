# #332 对抗测试矩阵 · 系统失败批 — 执行记录

- 日期：2026-10-20。票 #332（地图 #329）。本目录是装具和手判，服务与插件代码不改。`justfile` 的 `py_projects` 加上本装具，`just check` / `just test` 才会跑这里的 ruff、mypy、pytest。
- 环境：本地实例 `c332`（快照 `20261019-1715`，WP `127.0.0.1:9187`，Genie `127.0.0.1:9189`，文档索引 build `20261018T173840Z`）。故障只打在这台实例上：聊天模型指向本机桩，Jev 指向本机 502，索引换成临时文件，能力路由用实例 mu-plugin，SSE 用本机截断代理，VPS 宕机用停本地服务，Redis 用本机 `brew services`。跑完已恢复：Genie 健康、`linker_genie_url` 为 `http://127.0.0.1:9189`、无 `GENIE_BASE_URL`、Redis `PONG`、mu-plugin 与故障旗标已删除。
- 场景 23 个。手判 pass 12，defect 11。11 条缺陷场景归成 4 个顾客痛点（D1–D4）。发布结论是手判。`RATE-BURST` 的 jsonl 仍写着 defect，手判是 pass。
- 证据在 `~/de-linker-data/campaign-332/`。仓库里的 `verdicts.jsonl` 是红acted 摘要（无原始 SSE、无令牌）。`cases.md` 是场景索引。
- 生产只做了 3 次正常问答，没有注入故障。见 `NOTES.md` §4。

## 装具

- `harness/run_faults.py` — 本地故障批次。`--only A,B` 追加 `cases.jsonl`，全量跑才会截断该文件。
- `harness/faults.py` — 本机聊天桩（500 / 429 / 空流 / 慢响应）、OpenRouter 502 桩、SSE 截断与重置代理。
- `harness/stack.py` — `c332` 的服务、索引、能力旗标、`linker_genie_url`、Redis。`restore()` 在干净环境里 `just serve c332`。
- `harness/grade.py` — 自动评分。发布用的是 `NOTES.md` 的手判。
- `harness/prod_smoke.py` — 生产探针。`de-linker.com` / `www.de-linker.com` 没有 `--confirm-production` 就拒绝。询盘与联系发送不调用。
- 本目录是独立 uv 工程（`package = false`）。

复跑本地批次：

```bash
just up c332 && just pull load c332 latest && just serve c332
cd docs/research/2026-10-20-campaign-332/harness
uv run --locked python run_faults.py "$HOME/de-linker-data/campaign-332/evidence"
```

生产冒烟（会写对话，跑完按 cookie 删除；本批已跑 3 次，不要再加）：

```bash
uv run --locked python prod_smoke.py --site https://de-linker.com --confirm-production \
  --evidence "$HOME/de-linker-data/campaign-332/evidence/prod-smoke.jsonl"
```

## 判定

- 失败要对顾客可见：明确错误，或降级句。有可引用产品时只出产品句、meta 里才有 `fallback`，记缺陷。
- 壳上的 502 / 无 `done` 的 200，当场应出现 “Genie did not answer. Please try again.” 空白停住记缺陷。
- 刷新后的状态单独记。问题还在但错误消失，或问题与错误一起消失，都记缺陷。
- 重试在故障撤掉后应回到 `deepseek` / `deepseek-flash` 的扎实回答。
- 静默换模型记缺陷。Jev 失败后仍由 deepseek-flash 作答，且 SSE meta 带 `jev_error`，按规格放行。
- 失败回合里写成事实的测量值（kW、kWh、W、V、A、€、mm）记缺陷。目录卡上的真实价格、以及有 `done` 的健康回合里的目录功率，不记。无 `done` 的块不渲染，里面的数字不算已发布事实。

## 结论

见 `NOTES.md` 与 `cases.md`。场景 pass 12 / defect 11。痛点 4 条，按顾客痛苦排序：停机时仍像一次成功推荐、目录工具故障被说成去信销售、SSE 截断刷新后错误消失、502 刷新后问题也不见。
