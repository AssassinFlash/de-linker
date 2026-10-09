# #33 评审模型对比（Jev vs LLM 评审 vs 人工裁定）

业主 2026-10-09：先对比、通过评测再落地。本票只评测，不改任何运行时代码。

## 候选
- **Jev**：TypeSafe `jev-1.13`，经 aihubmix `POST {AIHUBMIX_BASE_URL}/v1/systemone`（Bearer，密钥在 `~/.config/terravolt-builder/aihubmix.env`，永不进仓库）。请求：`{"model":"jev-1.13","state":<文本或 JSON>,"questions":{<name>:{"type":"noul|choice|score","instructions":"…","criteria":{…}|[…]}}}`；返回每问的概率与 confidence（已实测 EN/DE 均可，代理延迟 3–6 s，652 输入 token 一次）。
- **开源权重的同类**：`openjev-qwen35-4b`（Databricks 文档里的 System One 开源模型，基于 Qwen3.5-4B）——查明权重来源与许可，能在 Mac 上本地跑则纳入，作为"无成本"选项。
- **LLM 评审**（经 aihubmix，OpenAI 兼容）：`deepseek-v4.1-flash`、`claude-haiku-5-5`、`gemini-3.8-flash`；各用同一评审提示词，输出 JSON 判定与理由。
- **人工裁定**：本线逐条裁定（盲审，不看模型结果），作为真值。

## 数据集（≥300 对，EN/DE 各半）
由 `docs/research/2026-10-09/old-repo-live-catalogue-facts.csv` 与我们托管的数据手册页构造 (问题, 候选答案, 参考) 三元组：正确答案、换型号的错误答案、数值篡改的错误答案、范围外却作答的答案、措辞不同但正确的答案（风格对抗）。每对三类问题：`grounded`（score 3 档）、`appropriate`（noul）、`better_pick`（choice）。另加 50 对 FAQ 文案质量判断（有无 AI 句式、营销感），专门验证论文所说的"无参考散文上失效"。

## 指标
与人工裁定的一致率（总体、EN、DE、按错误类型）、重复性（同一输入跑 3 次的方差）、每次判定成本、延迟（经代理实测）；Jev 的置信度级联：置信度 ≥ 阈值采纳、否则升级给 LLM 评审，报告级联的一致率与成本。

## 决策规则（写进 PR）
- 事实类判定（grounded / appropriate / better_pick）：与 embedding 同一原则（业主 2026-10-09）——先比，差距不大就用免费的。开源权重的 openjev-qwen35-4b 若与 Jev API 及最佳 LLM 评审的一致率差距 ≤ 3 个百分点 → 首选 openjev（在 Mac 上作为构建时评审运行，实测延迟与内存、注明量化、查清权重来源与许可）；其次 Jev API；都不达标 → LLM 评审。采用者用于 #13 的行为面板评测第一道与 #8 的引用核验。结果表加"每千次判定成本"列（API 按实际 token，开源按 0）。
- 文案质量判定：按结果决定；预期不用（论文已指出其弱点）。
- 德语一致率落后英语 > 5 个百分点 → 只用于英语子集。
- 任何情况下不进入运行时回答路径（AGENTS.md：运行时只有结构化输出与填数）。

## 产物
`docs/research/2026-10-09/judge-bakeoff.md`（结果表、阈值、每类错误的样例）；评测脚本 `services/genie/eval/judges/`（uv），黄金对 `services/genie/eval/judges/pairs.jsonl`。
