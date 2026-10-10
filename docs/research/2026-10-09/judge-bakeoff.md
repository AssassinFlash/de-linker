# #33 评审模型对比：结果表

规格：`docs/specs/33-judge-bakeoff.md`；候选调研：`judge-models.md`；脚本：`services/genie/eval/judges/`。只评测，不改运行时代码。

**状态（2026-10-10）**：管线、数据集（348 对问答 + 50 条文案）、VPS 实测、398 条人工盲审真值与 8 个评审 × 3 次 × 398 条的正式轮全部完成。**结论：采用 Jev→gemini 置信度级联**（§正式轮）。本页的试跑数字是执行者自裁定的 10 对，只证明管线跑通，不作决策。

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
- **盲审（2026-10-10 完成）**：`pairs.jsonl` 不含答案类别与预期标签；构造信息在 `construction.jsonl`，裁定时不要打开它与 `runs/`。拆分按基础问题做（同一问题的 5 类答案与两种语言同在一侧），校准集约三分之一。裁定方法：去重后的 52 份参考全文先读一遍建立行–列对照，再分 15 批逐条裁定（不看 `construction.jsonl` 与任何 `runs/`）；过程中发现并修正了一次列对齐错误（GW25K 充电电流在 9 列德语表按 11 列英语表对齐，p049/p063 两条随之更正）。`uv run judges labels` 0 问题。有效性信号：盲审标签的落点分布（grounded 2/0/1 = 152/120/76，appropriate no=76，better_pick equal/A/B = 152/92/104，EN/DE 逐类完全均衡；文案四格 14/12/12/12）与构造设计的比例一致，且无一条 grounded=1 而 appropriate=yes、grounded=0 而 better_pick=equal 的自相矛盾。

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

## VPS 实测（开源候选，生产机 1 vCPU / 3.9 GB，2026-10-09，**实测**）

`bench.sh` 在 `/tmp/bench-20261009` 起各自的 llama.cpp 服务器（`nice -n 19`，一个槽、4,096 上下文，与后台工作进程同形），对 20 个真实条目逐次调用；RSS/VmHWM 与 MemAvailable 读 `/proc`。门槛（规格）：p95 ≤ 30 s、RSS ≤ 2 GB、与引擎和 Genie 共存时内存余量 ≥ 500 MB。

| judge | 量化 | p50 | p95 | max | RSS 峰值 | 主机内存余量最低 | 错误 | 判定 |
|---|---|---|---|---|---|---|---|---|
| julia1 | Q8_0（168 MB） | 3.83 s | 8.91 s | 9.85 s | 1 598.7 MiB | 1 955.1 MiB | 0 | **过三条门槛**（RSS 高是 4,096 token 的整批计算缓冲） |
| laya | Q8_0（449 MB） | 20.04 s | 37.14 s | 37.22 s | 797.9 MiB | 3 026.4 MiB | 0 | p95 超 30 s，**不达标** |
| qwen3-1.7b | Q4_K_M（1.28 GB） | 28.92 s | 135.11 s | 135.11 s | 3 462.7 MiB | 0.1 MiB | 2 | 三条全不过（服务器最终被 OOM killer 杀掉；2 次连接错误） |
| lev | Q4_K_M（3.01 GB） | — | — | — | — | — | — | 权重文件已超 2 GB，不上 VPS（只在 Mac 上作质量上限参照） |

产物：`runs/bench-vps/<judge>.jsonl` 与 `.summary.json`；服务器日志在 VPS `/tmp/bench-20261009/out/`。

## openjev-qwen35-4b

Databricks 文档里的 `system.ai.openjev-qwen35-4b` 只以按 token 计费的托管服务提供，Databricks 与 TypeSafe 都没有公开权重，结论为**不可得**；同名的三个开源项目及其许可见 `judge-models.md`。业主"开源优先"的意图由同类开源决策模型（Julia-1、Laya、lev）与通用小模型 Qwen3-1.7B 承接。

## 正式轮（2026-10-10，398 条 × 3 次 × 8 个评审）

- 运行：`uv run judges run --judges jev,deepseek,haiku,gemini --runs 3 --out runs/formal-20261010`（API，6 并发）与逐个 llama.cpp 服务器上的 `julia1`、`laya`、`lev`、`qwen3-1.7b`（每次一个请求）。8 个评审全部 1 194/1 194 次判定成功，`metrics.latest` 按 (条目, 次) 取末次。
- **中断记录**：deepseek 在 04:00–04:07 UTC 跑了 210 次后 aihubmix 余额耗尽（HTTP 403）；余额恢复后 05:36–05:54 续完其余 984 次。两次窗口都在 DeepSeek 双倍计费时段（01–04、06–10 UTC）之外；jev/haiku/gemini 在 01:15–02:10 UTC。API 实付合计约 $3.9。
- lev 与 qwen3-1.7b 的本地延迟是两服务器并行时测得的（竞争 Metal），只作参考；延迟判定以 VPS 实测为准。

### 结果（测试集 230 对问答；`uv run judges report --runs runs/formal-20261010 --split test`）

| judge | weights | runs | factual (3 questions) | EN | DE | grounded | appropriate | better_pick | stable across runs | grounded variance | invalid | USD per 1,000 judgments | p50 / p95 s per judgment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | closed | 3 | 97.8% | 97.9% | 97.7% | 93.6% | 100.0% | 99.7% | 97.5% | 0.014 | 0.0% | $0.4533 | 4.48 / 8.63 |
| gemini | closed | 3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.000 | 0.0% | $2.2973 | 7.11 / 27.15 |
| haiku | closed | 3 | 98.8% | 98.1% | 99.5% | 97.8% | 99.9% | 98.7% | 97.8% | 0.008 | 0.1% | $0.2967 | 3.15 / 4.26 |
| jev | closed | 3 | 94.4% | 94.2% | 94.7% | 92.6% | 100.0% | 90.7% | 98.7% | 0.003 | 0.0% | $0.0628 | 1.54 / 1.76 |
| julia1 | Julia-1 (144M) Q8_0 | 3 | 30.6% | 31.6% | 29.6% | 40.9% | 24.3% | 26.5% | 100.0% | 0.000 | 0.0% | $0.0000 | 0.18 / 0.35 |
| laya | Laya (0.4B) Q8_0 | 3 | 43.6% | 44.1% | 43.2% | 43.0% | 54.8% | 33.0% | 100.0% | 0.000 | 0.0% | $0.0000 | 0.58 / 0.92 |
| lev | lev (4B) Q4_K_M | 3 | 65.2% | 64.3% | 66.1% | 69.1% | 86.5% | 40.0% | 100.0% | 0.000 | 0.0% | $0.0000 | 12.83 / 22.68 |
| qwen3-1.7b | Qwen3-1.7B Q4_K_M | 3 | 43.6% | 42.9% | 44.3% | 29.6% | 78.3% | 23.0% | 100.0% | 0.000 | 0.0% | $0.0000 | 5.20 / 9.85 |

事实类一致率按答案类别（测试集）：

| judge | correct | paraphrase_correct | numeric_tamper | wrong_model | out_of_scope_answered |
|---|---|---|---|---|---|
| deepseek | 95.6% | 95.1% | 100.0% | 99.7% | 99.3% |
| gemini | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| haiku | 98.7% | 98.7% | 100.0% | 100.0% | 97.1% |
| jev | 87.6% | 86.9% | 100.0% | 100.0% | 100.0% |
| julia1 | 32.0% | 33.3% | 21.7% | 21.7% | 40.7% |
| laya | 40.0% | 38.0% | 45.0% | 43.3% | 52.0% |
| lev | 81.3% | 81.3% | 65.0% | 47.5% | 47.3% |
| qwen3-1.7b | 42.7% | 40.0% | 46.7% | 40.8% | 48.0% |

校准集（118 对）排序：gemini 99.7% > haiku 98.0% > deepseek 96.4% > jev 92.8%；开源 julia1 31.9%、laya 45.8%、lev 69.8%、qwen3-1.7b 45.2%（完整表 `uv run judges report --runs runs/formal-20261010 --split calibration`）。

### 决策规则应用（规则在结果之前写定）

1. **开源优先**：唯一过 VPS 三条门槛的 julia1 事实类一致率 30.6%，与最佳闭源评审（gemini 100.0%）差 69.4 个百分点 ≫ 3 个百分点；laya、qwen3-1.7b 一致率与 VPS 门槛双败；lev（一致率最高的开源，65.2%）权重 3.01 GB 无法上 VPS。**无开源候选达标。**
2. **Jev API**：Jev 单独 94.4%，与最佳 LLM 评审差 5.6 个百分点 > 3 个百分点。**不单独采用。**
3. **级联**（规则原文：级联在测试集上与回退 LLM 差距 ≤ 3 个百分点且更便宜即可替代单独的 LLM）：回退评审按校准集定为 **gemini**。**采用。**
4. 德语落后英语 > 5 个百分点才限英语：Jev EN 94.2 / DE 94.7，无落后；级联测试集 EN/DE 均 100%。**英德都可用。**
5. 文案质量（无参考，50 条全量）：闭源评审全部 98.0–100.0%（jev 99.0%、gemini 100.0%、haiku 98.0%、deepseek 99.7%）；开源全部 ≤ 89%（lev 89.0%、qwen3-1.7b 72.0%、laya 51.0%、julia1 47.0%）。本集按构造模式明显（"nahtlos"、三连排比、"完美之选"），高一致率不代表论文里无参考散文的一般情形；**不单独为文案采用评审**——#15 若需要，同一采用者在此类模式明显的条目上已够用。
6. 不进回答路径：级联部署为 VPS 上队列驱动的后台工作进程（网络出站调用，不驻留模型），引擎与 Genie 的内存不受影响。

### 采用结论

**Jev（jev-1.13，经 aihubmix）为第一道，置信度不足时升级 gemini-3.8-flash**；阈值只用校准集选出、原样用于测试集：grounded ≥ 0.85、appropriate ≥ 0.5、better_pick ≥ 0.6（`metrics.py` THRESHOLD_GRID/MAX_CALIBRATION_LOSS）。用途：**#13 行为面板的每轮回答评测第一道与 #8 的引用核验第一道**；不进入 Genie 的回答请求路径。

| 测试集 | 事实类一致率 | 升级条目占比 | 每千次判定成本 |
|---|---|---|---|
| Jev 单独 | 94.4% | 0% | $0.0588 |
| gemini 单独 | 100.0% | 100% | $2.2973 |
| **级联（采用）** | **100.0%** | **37.8%** | **$0.9105** |

Jev 各问题被直接采纳的比例：grounded 87.2%、appropriate 100.0%、better_pick 68.0%。
重复性：Jev 跨 3 次运行标签稳定率 98.7%（grounded 方差 0.003）；级联中 gemini 稳定率 100%。
日处理量（1 vCPU 队列工作进程，网络型负载）：平均每判定 ≈ 0.622 × 1.54 s + 0.378 × (1.54 + 7.11) s ≈ 4.2 s → 单工作进程约 2 万次判定/天。
每千次判定成本对比：julia1 $0（但 30.6% 一致率，不可用）；Jev $0.059；级联 $0.91；haiku $0.30；deepseek $0.45；gemini $2.30。

**Post-hoc 观察（非预先登记的决策，供 #13/#8 实施时权衡）**：若回退换成 haiku（校准集第二），同样的冻结网格选出 grounded ≥ 0.6、appropriate ≥ 0.5、better_pick ≥ 0.6，测试集一致率 99.6%（−0.4 个百分点对 gemini 级联）、升级 35.9%、每千次 $0.1665（再省 82%）。差距来自 haiku 自身 98.8% 的上限。预登记规则按校准集最优选了 gemini，故本票采用 gemini 级联；若面板上线后成本成为主要考量，jev→haiku 是有实测支撑的降价选项，换回退不需重跑真值。

### 每类错误样例（测试集，评审与人工不一致）

- **jev 把正确的答案判成 better_pick 有高低**（better_pick 90.7% 的主要来源）：p004 两个答案都是"13200 VA"整句/寒暄式改写，人工 equal，jev 选了 B；p007 同值整句 vs 寒暄壳，人工 equal，jev 选 A——即 jev 仍受风格长度影响，正是规则要求"措辞不使答案更好"的地方。
- **jev 把转团队邮箱的正确处理判为 grounded=1**（不可核实）：p020 安装问题答" Fragen zur Installation klärt unser Team direkt unter sales@de-linker.com"，人工 2（无产品事实即有依据），jev 给 1——它把"邮箱/团队"当成了参考里没有的事实。
- **jev 对 correct/paraphrase 类 87–87.6%**：如上两类；对三类错误答案（篡改、串型号、越权作答）100% 抓住。
- **gemini 无不一致**；haiku 唯一失分是 p029 的一次无效输出（JSON 缺键，按规则计不一致）+ 少量 marketing 判断摇摆（文案 96.0%）。
- **julia1（开源最优 VPS 候选）把 132.0 kW 判成有依据**（p001，表中值 110.0）、把正确答案判出职责外——30.6% 的一致率说明该尺寸的决策模型不理解我们的表格任务。

## 产物与复现

- 黄金对与真值：`pairs.jsonl`（398 条，`human_label`）；构造密钥 `construction.jsonl`。
- 运行记录：`runs/formal-20261010/<judge>.jsonl`（含每次调用的时间、token、成本、延迟）；`runs/bench-vps/`、`runs/bench-mac/`；试跑 `runs/trial-20261009/`。
- 报表：`uv run judges report --runs runs/formal-20261010 --split test|calibration|all`；级联与阈值：`metrics.py`。
- 测试集是决策面；校准集只用于选回退评审与级联阈值，两条规则都先于结果写定。
