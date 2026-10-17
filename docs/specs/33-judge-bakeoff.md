# #33 评审模型对比（Jev vs LLM 评审 vs 人工裁定）

业主 2026-10-09：先对比、通过评测再落地。本票只评测，不改任何运行时代码。

## 候选
- **Jev**：TypeSafe `typesafe/jev-1.13`，**仅经 OpenRouter 原生 `POST https://openrouter.ai/api/v1/systemone`**（模型路由铁律，AGENTS.md §5；本规格原写的 aihubmix 通道已被铁律取代，#258 改正；chat 接口的 jev-router 是逐调用转包他人的元路由，禁用）。Bearer，密钥来自环境 `OPENROUTER_API_KEY` 或 `~/.config/terravolt-builder/openrouter.env`，永不进仓库。请求：`{"model":"typesafe/jev-1.13","state":<文本或 JSON>,"questions":{<name>:{"type":"noul|choice|score","instructions":"…","criteria":{…}|[…]}}}`；返回每问的概率与 confidence（已实测 EN/DE 均可，延迟 3–6 s，652 输入 token 一次）。调用失败重试后显式报错，不换模型（同铁律）。
- **开源评审模型（业主 2026-10-09：Jev 只是让我们认识这一类；能用开源解决就用开源）**：用 Apify 调研 2026 年开源权重、许可可商用、能在 Apple Silicon Mac 上量化运行（≤8–14B）的专用评审/判断/奖励模型（Prometheus 系列、Flow-Judge、Atla Selene、Skywork-Reward、`openjev-qwen35-4b` 及 2026 年新出的同类，以调研为准），选 2–3 个纳入；另加一个通用开源 LLM（如 Qwen3 8B/14B 量化）作评审对照。调研结论：`docs/research/2026-10-09/judge-models.md`。
- **LLM 评审**：升级判定直连 DeepSeek 官方 API（`deepseek-flash`，密钥 `~/.config/terravolt-builder/deepseek.env`，业主裁定 2026-10-11）；（原对照评审 `claude-haiku-5-5` 经 aihubmix：模型路由铁律只许四条通道，已撤出；对比历史在 git。）各用同一评审提示词，输出 JSON 判定与理由。`gemini-3.8-flash` 是被封会话自拟的候选、业主从未认可，已从本规格与工具链整个清除。
- **人工裁定**：本线逐条裁定（盲审，不看模型结果），作为真值。

## 数据集（≥300 对，EN/DE 各半）
由 `docs/research/2026-10-09/old-repo-live-catalogue-facts.csv` 与我们托管的数据手册页构造 (问题, 候选答案, 参考) 三元组：正确答案、换型号的错误答案、数值篡改的错误答案、范围外却作答的答案、措辞不同但正确的答案（风格对抗）。每对三类问题：`grounded`（score 3 档）、`appropriate`（noul）、`better_pick`（choice）。另加 50 对 FAQ 文案质量判断（有无 AI 句式、营销感），专门验证论文所说的"无参考散文上失效"。

## 部署目标（业主 2026-10-09：最终要在线上运行，不停在 Mac）
评审模型部署在现有 VPS（1 vCPU、3.9 GB、无 GPU、不升级）上，形态为**队列驱动的后台工作进程**：持续评估线上 Genie 的每轮回答、执行 #8 的引用核验、运行 #13 的面板；不进入回答的请求路径。评测硬指标：每个开源候选在 VPS 上以量化（GGUF Q4/Q5 或 ONNX int8）实测单次判定延迟 p50/p95 与 RSS；与引擎、Genie 共存时空闲内存 ≥ 500 MB；报告给出每日可处理的判定量。候选偏向小模型（≤4B，优先 ≤1.5B）。

## 部署（#258，业主 2026-10-17：只做事后质检）

上面的"部署目标"按对比结论落地为 Jev API（`docs/research/2026-10-09/judge-bakeoff.md` §采用结论：没有达标的开源候选），形态不变：

- **不进回答路径**：回答照常立刻发出；评审是 VPS 上独立的 systemd 单元 `linker-genie-judge`（`services/genie/ops/linker-genie-judge.service`，与 `linker-genie` 同一发布目录 `/opt/linker-genie/current`、同一环境文件）。
- **队列**：服务自己的对话日志 `turns.sqlite`（`GENIE_LOG`）。日志每轮另记客户问句、页面上下文和各工具当时的返回（`services/genie/src/linker_genie/log.py`、`abilities.py`）；评审只读日志，不重放（库存、价格、客户询盘会变）。工作进程自己的 `judgments.sqlite` 记队列位置、每轮结论与是否已交给站点。首次启动从当时最新一轮之后开始，只评新对话。
- **级联**（`services/genie/src/linker_genie/quality/worker.py`，复用 `eval/judges` 的 `run_cascade`）：Jev 答 grounded / appropriate / better_pick（有可换的产品时才问第三问；换品取本轮工具返回过、回答没给的产品）；任一问置信度低于 `TURN_THRESHOLDS`（grounded 0.6、appropriate 0.5、better_pick 0.6）→ 整条交 deepseek-flash（仅官方 API）判，日志 INFO 记 "turn N escalated to deepseek-flash: grounded 0.42 < 0.6"。**Jev 调用失败不是"不确定"**：不升级、不换模型，该轮记 `failed`、日志 ERROR，10 分钟后重试，共 3 次。
- **引用核验**（`quality/citations.py`）：发出的回答里每个引用 ID、每张卡片都必须是本轮工具返回过的，每个数字都必须出现在本轮工具返回的值里（与 `ground.py` 第 5 条同一判定）。
- **标记**：grounded 0（矛盾）或 1（无法核实）、appropriate no、better_pick B、引用核验不过、判不出 → 标记，后台列表可筛。
- **交给站点**：`POST /wp-json/linker-ai/v1/genie/quality`，共享令牌放在请求头 `X-Linker-Judge-Token`（不用 `Authorization: Bearer`：LiveCanvas 自带的模板系统把每个 REST 请求的 Bearer 当 JWT 解码，非 JWT 令牌直接 500；VPS `GENIE_JUDGE_TOKEN` = 站点 wp-config.php 常量 `LINKER_GENIE_JUDGE_TOKEN`；没有常量时路由关闭）。站点把每轮结论存为对话帖的 post meta（`linker_genie_quality`），无自定义表；没被站点收下的结论下一轮再交。工作进程每 10 分钟报一次状态，站点 30 分钟没收到即视为停止。
- **后台**：Genie quality（`linker-tools` `QualityPage`）列出有结论的对话，可筛"标记"与"未能评判"；点进对话看逐轮问句、回答、结论、升级原因、评审理由与对话全文。页首显示工作进程停止或最近一次评审错误。
- **保留期限**：VPS 上的对话日志（顾客原话、页面、工具返回）和结论库保留 90 天，与站点删除访客对话的期限相同（`plugins/linker-tools/includes/Genie/Retention.php` 的 `RETENTION_DAYS`；有测试把两边的数字钉在一起）。注册客户的对话站点会继续保留，但 VPS 上的副本只供评判使用，同样 90 天后删除；结论本身随对话存在站点上。评审进程每天清理一次两个库里的过期行，失败记 ERROR 并在下一轮重试。
- **部署**：`just cutover services --run` 一条命令完成发布与启用：两份 release 之后在 VPS 上跑 `services/genie/ops/activate.sh`（两个服务各自 `uv sync --locked`、安装/更新 `linker-genie-judge.service`、`daemon-reload`、重启 engine / genie / judge、逐个确认 active，有一个没起来即失败）。唯一的手工步骤是放令牌：站点 wp-config.php 的 `LINKER_GENIE_JUDGE_TOKEN` 与 `/etc/linker-genie.env` 的 `GENIE_JUDGE_TOKEN`；没有令牌时评审单元只安装不启动，该步骤以提示结束。
- **本地**：`just serve <实例>` 把 Genie 日志写到该实例自己的 `~/de-linker-local/<实例>/genie/turns.sqlite`，评审进程的 `judgments.sqlite` 默认在它旁边；各实例互不串号。本地跑评审：`GENIE_JUDGE_TOKEN=<实例 wp-config 里的值> GENIE_WP_URL=<实例地址> uv run --project services/genie python -m linker_genie.quality.worker --log ~/de-linker-local/<实例>/genie/turns.sqlite`。
- **每日摘要**：`apply_filters( 'linker_tools_genie_quality_summary', null, $since )` 返回过去 24 小时的计数（judged / flagged / escalated / failed / skipped）、工作进程状态、后台链接和一句现成的 `line`；摘要一节由 #221 按 `Digest\Block` 接入。

## 指标
与人工裁定的一致率（总体、EN、DE、按错误类型）、重复性（同一输入跑 3 次的方差）、每次判定成本、延迟（经代理实测）；Jev 的置信度级联：置信度 ≥ 阈值采纳、否则升级给 LLM 评审，报告级联的一致率与成本。

## 决策规则（写进 PR）
- 事实类判定（grounded / appropriate / better_pick）：与 embedding 同一原则（业主 2026-10-09）——先比，差距不大就用免费的。在 VPS 上可跑（p95 ≤ 30 s/次、RSS ≤ 2 GB）且与最佳闭源评审（Jev API 或闭源 LLM）的一致率差距 ≤ 3 个百分点的开源候选 → 采用（多个达标取最小者；注明量化、权重来源与许可）；没有达标的开源候选 → Jev API；文案质量判定另议。采用者用于 #13 的行为面板评测第一道与 #8 的引用核验。结果表加"每千次判定成本"列（API 按实际 token，开源按 0）。
- 文案质量判定：按结果决定；预期不用（论文已指出其弱点）。
- 德语一致率落后英语 > 5 个百分点 → 只用于英语子集。
- 任何情况下不进入运行时回答路径（AGENTS.md：运行时只有结构化输出与填数）。

## 产物
`docs/research/2026-10-09/judge-bakeoff.md`（结果表、阈值、每类错误的样例）；评测脚本 `services/genie/eval/judges/`（uv），黄金对 `services/genie/eval/judges/pairs.jsonl`。
