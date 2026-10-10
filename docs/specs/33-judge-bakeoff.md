# #33 评审模型对比（Jev vs LLM 评审 vs 人工裁定）

业主 2026-10-09：先对比、通过评测再落地。本票只评测，不改任何运行时代码。

## 候选
- **Jev**：TypeSafe `jev-1.13`，经 aihubmix `POST {AIHUBMIX_BASE_URL}/v1/systemone`（Bearer，密钥在 `~/.config/terravolt-builder/aihubmix.env`，永不进仓库）。请求：`{"model":"jev-1.13","state":<文本或 JSON>,"questions":{<name>:{"type":"noul|choice|score","instructions":"…","criteria":{…}|[…]}}}`；返回每问的概率与 confidence（已实测 EN/DE 均可，代理延迟 3–6 s，652 输入 token 一次）。
- **开源评审模型（业主 2026-10-09：Jev 只是让我们认识这一类；能用开源解决就用开源）**：用 Apify 调研 2026 年开源权重、许可可商用、能在 Apple Silicon Mac 上量化运行（≤8–14B）的专用评审/判断/奖励模型（Prometheus 系列、Flow-Judge、Atla Selene、Skywork-Reward、`openjev-qwen35-4b` 及 2026 年新出的同类，以调研为准），选 2–3 个纳入；另加一个通用开源 LLM（如 Qwen3 8B/14B 量化）作评审对照。调研结论：`docs/research/2026-10-09/judge-models.md`。
- **LLM 评审**：升级判定直连 DeepSeek 官方 API（`deepseek-flash`，密钥 `~/.config/terravolt-builder/deepseek.env`，业主裁定 2026-10-11）；对照评审 `claude-haiku-5-5` 经 aihubmix。各用同一评审提示词，输出 JSON 判定与理由。`gemini-3.8-flash` 是被封会话自拟的候选、业主从未认可，已从本规格与工具链整个清除。
- **人工裁定**：本线逐条裁定（盲审，不看模型结果），作为真值。

## 数据集（≥300 对，EN/DE 各半）
由 `docs/research/2026-10-09/old-repo-live-catalogue-facts.csv` 与我们托管的数据手册页构造 (问题, 候选答案, 参考) 三元组：正确答案、换型号的错误答案、数值篡改的错误答案、范围外却作答的答案、措辞不同但正确的答案（风格对抗）。每对三类问题：`grounded`（score 3 档）、`appropriate`（noul）、`better_pick`（choice）。另加 50 对 FAQ 文案质量判断（有无 AI 句式、营销感），专门验证论文所说的"无参考散文上失效"。

## 部署目标（业主 2026-10-09：最终要在线上运行，不停在 Mac）
评审模型部署在现有 VPS（1 vCPU、3.9 GB、无 GPU、不升级）上，形态为**队列驱动的后台工作进程**：持续评估线上 Genie 的每轮回答、执行 #8 的引用核验、运行 #13 的面板；不进入回答的请求路径。评测硬指标：每个开源候选在 VPS 上以量化（GGUF Q4/Q5 或 ONNX int8）实测单次判定延迟 p50/p95 与 RSS；与引擎、Genie 共存时空闲内存 ≥ 500 MB；报告给出每日可处理的判定量。候选偏向小模型（≤4B，优先 ≤1.5B）。

## 指标
与人工裁定的一致率（总体、EN、DE、按错误类型）、重复性（同一输入跑 3 次的方差）、每次判定成本、延迟（经代理实测）；Jev 的置信度级联：置信度 ≥ 阈值采纳、否则升级给 LLM 评审，报告级联的一致率与成本。

## 决策规则（写进 PR）
- 事实类判定（grounded / appropriate / better_pick）：与 embedding 同一原则（业主 2026-10-09）——先比，差距不大就用免费的。在 VPS 上可跑（p95 ≤ 30 s/次、RSS ≤ 2 GB）且与最佳闭源评审（Jev API 或闭源 LLM）的一致率差距 ≤ 3 个百分点的开源候选 → 采用（多个达标取最小者；注明量化、权重来源与许可）；没有达标的开源候选 → Jev API；文案质量判定另议。采用者用于 #13 的行为面板评测第一道与 #8 的引用核验。结果表加"每千次判定成本"列（API 按实际 token，开源按 0）。
- 文案质量判定：按结果决定；预期不用（论文已指出其弱点）。
- 德语一致率落后英语 > 5 个百分点 → 只用于英语子集。
- 任何情况下不进入运行时回答路径（AGENTS.md：运行时只有结构化输出与填数）。

## 产物
`docs/research/2026-10-09/judge-bakeoff.md`（结果表、阈值、每类错误的样例）；评测脚本 `services/genie/eval/judges/`（uv），黄金对 `services/genie/eval/judges/pairs.jsonl`。
