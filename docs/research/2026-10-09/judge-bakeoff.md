# #33 评审模型对比：结果表

规格：`docs/specs/33-judge-bakeoff.md`；候选调研：`judge-models.md`；脚本：`services/genie/eval/judges/`。只评测，不改运行时代码。

**状态（2026-10-09）**：管线、数据集（348 对问答 + 50 条文案）、10 对试跑与 VPS 实测已完成。`pairs.jsonl` 待评审线盲审写回 `human_label`；正式数字和采用结论在裁定之后按下面写定的规则产出。本页的试跑数字是执行者自裁定的 10 对，只证明管线跑通，不作决策。

## 决策规则（在任何结果之前写定）

判定 = 对一个条目的一次评审（一次调用，问答条目同时回答 3 个问题，文案条目 2 个）。"事实类一致率" = grounded、appropriate、better_pick 三个问题与人工标签一致的比例，在测试集上、对 3 次运行取平均；无效输出算不一致。

1. **开源优先**（业主 2026-10-09）：开源候选在 VPS 上可跑（每次判定 p95 ≤ 30 s、常驻内存 RSS ≤ 2 GB、与引擎和 Genie 共存时内存余量 ≥ 500 MB），且事实类一致率与最佳闭源评审的差距 ≤ 3 个百分点 → 采用；多个达标取最小者。
2. 否则 **Jev API**：Jev 与最佳 LLM 评审的差距 ≤ 3 个百分点 → 采用，用于 #13 行为面板的第一道与 #8 的引用核验（规格原规则）。
3. 都不达标 → 用 LLM 评审；Jev 置信度级联若在测试集上与该 LLM 的差距 ≤ 3 个百分点且更便宜，可替代单独的 LLM。
4. 采用者的德语一致率落后英语 > 5 个百分点 → 只用于英语子集。
5. 文案质量（无参考）：按结果决定；预期不用（JEV-as-a-Judge，arXiv:2609.26550：无参考散文上所有评审接近随机）。
6. 任何情况下不进入回答的请求路径（AGENTS.md：运行时只有结构化输出与填数）；VPS 上是队列驱动的后台进程。

**Jev 级联阈值**：每个问题单独定，只用校准集。候选阈值取论文的冻结网格 {0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0}，选覆盖最多、且校准集一致率不低于回退评审 2 个百分点以内的那个；没有就全部升级。回退评审 = 校准集上一致率最高的 LLM（并列取便宜者）。阈值定下后原样用于测试集，不再调整（`metrics.py`：`THRESHOLD_GRID`、`MAX_CALIBRATION_LOSS`）。置信度：score 与 choice 用 TypeSafe 返回的 `confidence`，noul 用 |2p − 1|（docs.typesafe.ai/confidence）。

## 数据集

| | 问答对 | 英 | 德 | 校准集 | 测试集 |
|---|---|---|---|---|---|
| 数据手册（我们托管的 PDF 页，22 个基础问题 × 5 类答案 × 2 语言） | 220 | 110 | 110 | 70 | 150 |
| 产品目录事实（工具结果 JSON，8 × 5 × 2） | 80 | 40 | 40 | 30 | 50 |
| 范围外问题（公司、物流、服务，8 × 3 × 2） | 48 | 24 | 24 | 18 | 30 |
| 合计 | 348 | 174 | 174 | 118 | 230 |

- **参考**：数据手册对的参考是 `pdftotext -layout` 从我们托管的 PDF（`~/de-linker-data/pdf/<sha256>.pdf`，#6 拉取）切出的表格片段，带表头与目标行，约 300–1 800 字符；德语问题用德语数据手册（11 个系列有德语版），只有 H2-12K-T3 一个系列用英语数据手册（跨语言）。目录对的参考是 `linker/search-products` 形状的 JSON，数据取自 `old-repo-live-catalogue-facts.md` 的表（规格提到的 `old-repo-live-catalogue-facts.csv` 不在 main 上，它的 16 列版本是 #7 分支的测试夹具）。范围外问题的参考是该产品的数据手册片段，库存问题用带 `in_stock` 的产品记录。
- **五类答案**：correct（照抄参考）、paraphrase_correct（换单位、德式数字格式、极简、寒暄式、带出处四种风格）、numeric_tamper（数值按固定倍数改动，且避开表中任何一格的值）、wrong_model（同一行里另一个型号的值，最常见的"串列"错误）、out_of_scope_answered（正确数值加一句库存数量/交期/Incoterms/安装/送达日期，或直接回答范围外问题）。错误答案一半套上寒暄式外壳，用来测"写得更周到的错误答案"（论文中 Jev 差距最大的一类）。
- **三类问题**：grounded（score，0 矛盾 / 1 无法核实 / 2 有依据）、appropriate（noul，是否在 Genie 的职责范围内）、better_pick（choice，A / B / equal；候选答案与一个正确答案配对，位置随机，正确对正确为 equal）。原文在 `rubric.py`，所有评审收到同一文字。
- **文案质量 50 条**（英德各 25）：plain 14、只有 AI 句式 12、只有营销腔 12、两者都有 12；问题为 ai_phrasing 与 marketing（noul），无参考。
- **盲审**：`pairs.jsonl` 不含答案类别与预期标签；构造信息在 `construction.jsonl`，裁定时不要打开它与 `runs/`。拆分按基础问题做（同一问题的 5 类答案与两种语言同在一侧），校准集约三分之一。

## 评测对象

| 评审 | 运行方式 | 设置 |
|---|---|---|
| jev | aihubmix `/v1/systemone`，`jev-1.13` | 三个问题一次请求 |
| deepseek | aihubmix `deepseek-v4.1-flash` | temperature 0，JSON 模式，默认推理 |
| haiku | aihubmix `claude-haiku-5-5` | 模型不接受 temperature，aihubmix 对它的 JSON 模式降级，因此两者都不传，按提示词输出 JSON |
| gemini | aihubmix `gemini-3.8-flash` | temperature 0，JSON 模式，默认推理 |
| julia1 | llama.cpp b11429 `/v1/systemone`，`Julia-1-Q8_0.gguf` | 开源，144M |
| laya | 同上，`Laya-Q8_0.gguf` | 开源，0.4B |
| lev | 同上，`lev-Q4_K_M.gguf` | 开源，4B，只在 Mac 上跑 |
| qwen3-1.7b | llama.cpp `/v1/chat/completions`，`Qwen3-1.7B-Q4_K_M.gguf` | 开源通用 LLM，temperature 0，JSON 模式，关闭思考 |

费用按 aihubmix 计费配置（`GET https://aihubmix.com/api/v1/models` 的 `pricing_lines` 默认档，2026-10-09 读取）与每次调用实际返回的 token 计算：jev 输入 $0.0462/百万、输出免费；deepseek $0.155/$0.62；haiku $0.1/$0.5；gemini $0.75/$3.75（推理 token 计入输出）。DeepSeek 在 UTC 01–04 与 06–10 点按两倍计费，试跑在 15:04–15:06 UTC，不在此列。开源模型按 0 计。API 的延迟是**经 aihubmix 代理**在这台 Mac 上测得的往返时间（6 个并发），本地模型一次一个请求。

## 试跑（10 对问答 + 2 条文案，自裁定，非正式）

自裁定标签在 `trial-labels.jsonl`（执行者按评审细则逐条核对参考给出，不是盲审），运行记录在 `runs/trial-20261009/`。每个评审跑 3 次。样本只有 10 对，一题之差就是 3.3 个百分点，下表不支持任何结论。

命令：`uv run judges report --runs runs/trial-20261009 --labels trial-labels.jsonl --split all`（10 对里 2 对在校准集，所以级联一栏只演示代码路径）。

| judge | weights | runs | factual (3 questions) | EN | DE | grounded | appropriate | better_pick | stable across runs | grounded variance | invalid | USD per 1,000 judgments | p50 / p95 s per judgment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | closed | 3 | 96.7% | 100.0% | 93.3% | 90.0% | 100.0% | 100.0% | 100.0% | 0.000 | 0.0% | $0.4304 | 4.64 / 7.40 |
| gemini | closed | 3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.000 | 0.0% | $2.3991 | 8.56 / 64.54 |
| haiku | closed | 3 | 98.9% | 100.0% | 97.8% | 96.7% | 100.0% | 100.0% | 96.7% | 0.022 | 0.0% | $0.3080 | 3.39 / 5.57 |
| jev | closed | 3 | 90.0% | 93.3% | 86.7% | 90.0% | 100.0% | 80.0% | 100.0% | 0.000 | 0.0% | $0.0671 | 1.54 / 2.12 |
| julia1 | Julia-1 (144M) Q8_0 | 3 | 26.7% | 26.7% | 26.7% | 50.0% | 20.0% | 10.0% | 100.0% | 0.000 | 0.0% | $0.0000 | 0.19 / 0.89 |
| laya | Laya (0.4B) Q8_0 | 3 | 46.7% | 66.7% | 26.7% | 50.0% | 50.0% | 40.0% | 100.0% | 0.000 | 0.0% | $0.0000 | 0.70 / 1.09 |
| lev | lev (4B) Q4_K_M | 3 | 56.7% | 66.7% | 46.7% | 50.0% | 90.0% | 30.0% | 100.0% | 0.000 | 0.0% | $0.0000 | 3.61 / 4.84 |
| qwen3-1.7b | Qwen3-1.7B Q4_K_M | 3 | 56.7% | 66.7% | 46.7% | 50.0% | 80.0% | 40.0% | 100.0% | 0.000 | 0.0% | $0.0000 | 0.65 / 2.01 |

Factual agreement by answer class:

| judge | correct | paraphrase_correct | numeric_tamper | wrong_model | out_of_scope_answered |
|---|---|---|---|---|---|
| deepseek | 100.0% | 83.3% | 100.0% | 100.0% | 100.0% |
| gemini | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| haiku | 100.0% | 94.4% | 100.0% | 100.0% | 100.0% |
| jev | 66.7% | 83.3% | 100.0% | 100.0% | 100.0% |
| julia1 | 33.3% | 33.3% | 0.0% | 16.7% | 50.0% |
| laya | 33.3% | 50.0% | 33.3% | 33.3% | 83.3% |
| lev | 66.7% | 83.3% | 66.7% | 33.3% | 33.3% |
| qwen3-1.7b | 66.7% | 33.3% | 66.7% | 50.0% | 66.7% |

Copy quality without a reference (AI phrasing, marketing tone):

| judge | both questions | EN | DE | ai_phrasing | marketing |
|---|---|---|---|---|---|
| deepseek | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| gemini | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| haiku | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| jev | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| julia1 | 25.0% | 50.0% | 0.0% | 0.0% | 50.0% |
| laya | 50.0% | 0.0% | 100.0% | 50.0% | 50.0% |
| lev | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| qwen3-1.7b | 75.0% | 50.0% | 100.0% | 50.0% | 100.0% |

Jev confidence cascade (fallback = gemini, the best LLM on the calibration split; thresholds from calibration only: grounded ≥ 0.85, appropriate ≥ 0.5, better_pick ≥ 0.5):

| on the test split | factual agreement | items escalated | USD per 1,000 judgments |
|---|---|---|---|
| Jev alone | 91.7% | 0% | $0.0606 |
| gemini alone | 100.0% | 100% | $2.4010 |
| cascade | 95.8% | 12.5% | $0.3556 |

Accepted from Jev per question: grounded 100.0%, appropriate 100.0%, better_pick 87.5%

## VPS 实测（开源候选，生产机 1 vCPU / 3.9 GB）

VPS_TABLE

## openjev-qwen35-4b

Databricks 文档里的 `system.ai.openjev-qwen35-4b` 只以按 token 计费的托管服务提供，Databricks 与 TypeSafe 都没有公开权重，结论为**不可得**；同名的三个开源项目及其许可见 `judge-models.md`。业主"开源优先"的意图由同类开源决策模型（Julia-1、Laya、lev）与通用小模型 Qwen3-1.7B 承接。

## 正式轮

1. 评审线在 `pairs.jsonl` 每行写入 `human_label`：问答条目 `{"grounded": 0|1|2, "appropriate": "yes"|"no", "better_pick": "A"|"B"|"equal"}`，文案条目 `{"ai_phrasing": "yes"|"no", "marketing": "yes"|"no"}`。`uv run judges labels` 通过（0 个问题）才开跑。
2. `uv run judges run --judges jev,deepseek,haiku,gemini --runs 3 --out runs/formal-<日期>`；本地模型逐个起 llama.cpp 服务（命令见 `bench.sh`）后 `--judges julia1`、`laya`、`lev`、`qwen3-1.7b`。按试跑的每次调用费用，398 个条目 × 3 次，API 合计约 $3.6（gemini 约 $2.7）。
3. `uv run judges report --runs runs/formal-<日期>` 输出上面各表的正式版；按决策规则写结论，并补每类错误的样例。
