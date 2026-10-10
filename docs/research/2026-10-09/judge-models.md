# 评审/判断模型调研（#33，2026-10-09）

业主 2026-10-09：Jev 只是让我们认识"判断/评审模型"这一类，不是指定它；能用开源解决就用开源。评审模型最终在现有 VPS（1 vCPU、3.9 GB、无 GPU、不升级）上作为后台工作进程运行（队列驱动，不进回答路径），所以候选按"能否在这台机器上以量化方式跑"筛。外部来源全部经 Apify `apify/rag-web-browser` 于 2026-10-09 取得（会话里的 Apify MCP 连接器账户已到月度上限，改用 `~/.config/terravolt-builder/apify.env` 的项目令牌走 REST）；模型文件与 llama.cpp 发行包的下载用 curl/gh，按固定修订号和 sha256 校验。

## 结论

1. **`system.ai.openjev-qwen35-4b`（Databricks）：权重不可得。** Databricks 只把它列为 Unity Gateway 上按 token 计费的托管模型服务，走 TypeSafe 的 System One API；适用条款一栏写的是 Qwen3.5-4B 的 Apache 2.0。Hugging Face 上 `author=databricks` 没有模型，按 "typesafe" 搜索只有无关项目，TypeSafe 也没有发布权重。叫 OpenJev 的开源项目有三个，都没有文档说明它就是 Databricks 那份：TheoLeeCJ 的 OpenJev（已改名 SemIf，是在未改动的 Qwen3.5-4B 上做读出的方法，代码 MIT，JevBench Intelligence 27.1）、`AlexWortega/openjev`（MIT，只声明英语，4B v5 为 9.1 GB 的 bf16 交叉编码器）、`openjev/openjev`（27B，CC BY-NC 4.0，不可商用）。
2. **这一类的开源模型可以直接替换 Jev。** llama.cpp 从 2026-10-02 起在服务器里原生提供 `/v1/systemone`（PR #29818），请求与响应和 Jev API 相同，换 base URL 即可；ggml-org 把可用的决策模型整理成 GGUF 合集。我们的评测脚本因此用同一个客户端调 Jev 和本地开源决策模型。
3. **VPS 的硬约束决定了能纳入谁。** 业主的门槛是单次判定 p95 ≤ 30 s、RSS ≤ 2 GB、与引擎和 Genie 共存时内存余量 ≥ 500 MB。4B 级决策模型的 Q4_K_M 文件本身已超 3 GB；生成式评审模型（3.8B–8B）在 1 个 vCPU 上逐 token 写评语，Q4 文件也多在 2.4 GB 以上。能上 VPS 的只有 ≤ 2B 的模型。
4. **纳入评测**：Julia-1（144M，多语，决策模型）、Laya（0.4B，英语，决策模型）、lev（4B，决策模型；JevBench 上能用 llama.cpp 跑的 ≤ 4B 开源决策模型里分数最高，只在 Mac 上作质量上限参照，不上 VPS）；通用开源 LLM 对照 Qwen3-1.7B（Q4_K_M，按同一评审提示词输出 JSON）。另有 Jev API 与三个闭源 LLM 评审（deepseek-v4.1-flash、claude-haiku-5-5、gemini-3.8-flash）。

## 候选清单

"JevBench" 指 Benchmark Heaven 的 JevBench v1.6.1 开源权重榜（2026-10-06 发布，board v1.7.28，2026-10-09 读取），Intelligence 是按机会校正的准确率，Jev 1.13.0 为 63.6。表中"VPS"一栏按上面的三条门槛判断；实测见 `judge-bakeoff.md`。

| 模型 | 类型 | 参数 | 许可 | 语言 | 评审基准分（出处） | VPS（1 vCPU，≤ 2 GB） | 是否纳入 | 来源 |
|---|---|---|---|---|---|---|---|---|
| Jev 1.13（TypeSafe） | 决策模型，托管 API | 未公开 | 闭源；aihubmix 计价 $0.0462/百万输入 token，输出免费 | 实测英德可用 | JevBench Intelligence 63.6、Calibration 90.6；JEV-as-a-Judge（arXiv:2609.26550）：普通偏好与有证据的事实性上距最强 LLM 评审 ≤ 3 个百分点，无参考散文上所有评审都接近随机 | API | 纳入 | typesafe.ai/blog/introducing-system-one-models-and-jev；arxiv.org/html/2609.26550v1 |
| openjev-qwen35-4b（Databricks） | 决策模型托管服务 | 4B | 条款写 Apache 2.0（Qwen3.5-4B） | — | 无公开评测 | 权重不可得 | 不纳入：不可得 | docs.databricks.com/aws/en/machine-learning/foundation-model-apis/supported-models；learn.microsoft.com/en-us/azure/databricks/machine-learning/model-serving/query-systemone-models；docs.databricks.com/aws/en/machine-learning/model-serving/acceptable-use-models |
| Julia-1（SupersonicLabs） | 决策模型（mmBERT-small） | 144M | Apache-2.0 | 52 个语种（MASSIVE 宏平均 71.5%） | typed-decisions 73.15%，同集 Jev 参考 72.70%（Noul 80.67%、Choice 71.33%、Score 68.88%）；不在 JevBench | Q8_0 168 MB | **纳入** | huggingface.co/SupersonicLabs/Julia-1；huggingface.co/ggml-org/Julia-1-GGUF |
| Laya（convaiinnovations） | 决策模型（ModernBERT-large） | 0.4B | Apache-2.0 | 英语（多语版另为 mmBERT-base 检查点，JevBench Intelligence 0.3） | 卡片：微调版 typed-decisions 0.766 | Q8_0 449 MB | **纳入** | huggingface.co/convaiinnovations/laya；huggingface.co/ggml-org/Laya-GGUF |
| lev（Interfaze AI） | 决策模型（Qwen3.5-4B + LoRA） | 4B | Apache-2.0 | 英语为主（massive-de-DE 0.823，Jev 0.871） | JevBench Intelligence 41.1、Capability 61.7；S1Bench 13 个子集 68.9% | Q4_K_M 3.01 GB，超 2 GB | **纳入（仅 Mac 质量参照）** | huggingface.co/interfaze-ai/lev；huggingface.co/ggml-org/lev-GGUF |
| Qwen3-1.7B（Qwen） | 通用 LLM，作评审对照 | 1.7B | Apache-2.0 | 多语 | JevBench 只测过其原始 logits 读出（Intelligence 5.1），不是作为对话评审 | Q4_K_M 1.28 GB | **纳入（通用对照）** | huggingface.co/ggml-org/Qwen3-1.7B-GGUF |
| Kev-4B（jaredpalmer） | 决策模型 | 4B | Apache-2.0 | 英语 | JevBench（旧 Qwen3 版本）Intelligence 19.5 | Q4_K_M 3.03 GB | 不纳入：同尺寸 lev 更强 | huggingface.co/ggml-org/Kev-4B-GGUF |
| H2O-Lightning-4B v1.1 | 决策模型（Qwen3.5-4B） | 4B | Apache-2.0 | 英语 | JevBench 综合分第 1（72.5，Intelligence 60.0） | 只发布 vLLM + shim 运行方式，无 GGUF；4B 超 2 GB | 不纳入 | huggingface.co/h2oai/h2o-lightning-4b |
| Clef-Flash（Cloudflare） | 决策模型（Qwen3.5-9B） | 9B | Apache-2.0 | 英语 | JevBench Intelligence 42.2 | Q4_K_M 6.49 GB | 不纳入：体积 | huggingface.co/ggml-org/Clef-Flash-GGUF |
| Bespoke Nimble 9B v3 | 决策模型 | 9B | CC BY-NC 4.0 | — | JevBench Intelligence 56.5 | — | 不纳入：不可商用 | huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF |
| OpenJev 27B / OpenJev Flash 9B（openjev） | 决策模型 | 27B / 9B | CC BY-NC 4.0 | 27B 含德语 | 1 万道文本题 84.0% / 79.4%，同题 Jev 85.4% | — | 不纳入：不可商用 | huggingface.co/openjev/openjev；huggingface.co/openjev/OpenJev-Flash-9B |
| SemIf（原名 OpenJev，TheoLeeCJ） | 读出方法，权重即 Qwen3.5-4B | 4B | 代码 MIT，权重 Apache 2.0 | 英语 | JevBench Intelligence 27.1 | Q4 约 3 GB | 不纳入 | github.com/TheoLeeCJ/SemIf-OpenJev |
| openjev（AlexWortega） | 交叉编码器决策模型 | 4B | MIT | 英语 | JevBench 公开题 0.814（Jev 1.13 为 0.866），judge_hard 0.53 | 9.1 GB bf16，只有 transformers 路径 | 不纳入 | huggingface.co/AlexWortega/openjev |
| Imajev 2B / 4B | 决策模型（Qwen3.5 + LoRA，可读图） | 2–4B | Apache-2.0 | 英语 | JevBench v1.4.2.2 第 1（67.37） | 需作者的 torch 运行时，无 GGUF | 不纳入 | github.com/mohit67890/imajev |
| Open-Jev-9B（ZefanCai） | 决策模型（LoRA + 标量头） | 9B | Apache-2.0 | — | 自建测试集 hard 准确率 97.5% | 需 GPU 加载器 | 不纳入 | huggingface.co/ZefanCai/Open-Jev-9B |
| Prometheus 2 | 生成式评审 | 7B | Apache-2.0 | 英语 | 5 档 Likert 留出集 Pearson 0.910（Flow-Judge 卡片转引原论文） | Q4 约 4.4 GB，生成式 | 不纳入 | huggingface.co/prometheus-eval/prometheus-7b-v2.0 |
| M-Prometheus | 多语生成式评审 | 3B | other（见卡片） | 多语 | 卡片未给统一分数 | 生成式 | 不纳入 | huggingface.co/Unbabel/M-Prometheus-3B |
| Flow-Judge v0.1 | 生成式评审（Phi-3.5-mini） | 3.8B | Apache-2.0 | 英语 | 3 档 Likert 留出集 Pearson 0.940；Pass/Fail 留出集 F1 0.955 | Q4 约 2.4 GB，生成式 | 不纳入 | huggingface.co/flowaicom/Flow-Judge-v0.1 |
| Atla Selene 1 Mini | 生成式评审（Llama-3.1-8B） | 8B | Apache-2.0 | 英语为主，支持德语 | RewardBench 上最好的 8B 生成式模型（卡片） | Q4 约 4.9 GB | 不纳入 | huggingface.co/AtlaAI/Selene-1-Mini-Llama-3.1-8B |
| Skywork-Reward-V2-Qwen3 0.6B / 1.7B | 奖励模型 | 0.6B / 1.7B | Apache-2.0 | — | RewardBench v1 85.2 / 90.3，v2 61.3 / 68.3，JudgeBench 67.6 / 72.9 | 体积可以 | 不纳入：只给成对偏好分，覆盖不了 grounded 三档与 appropriate | huggingface.co/Skywork/Skywork-Reward-V2-Qwen3-0.6B |
| Granite Guardian 3.3 | 风险与事实性判定 | 8B | Apache-2.0 | 英语 | TRUE 平均 0.777（no_think） | Q4 约 5 GB | 不纳入 | huggingface.co/ibm-granite/granite-guardian-3.3-8b |
| HHEM-2.1-Open（Vectara） | 幻觉分类器 | 约 0.1B | Apache-2.0 | 英语（多语只在付费 HHEM-2.3） | AggreFact、RAGTruth（卡片） | CPU 可跑 | 不纳入：只覆盖 grounded | huggingface.co/vectara/hallucination_evaluation_model |

## 取舍依据

- 我们要判的三类问题（grounded 三档、appropriate 是非、better_pick 三选一）正好是 System One 的 score、noul、choice。决策模型原生覆盖三类；奖励模型和幻觉分类器各只覆盖一类，生成式评审虽能覆盖但在 1 vCPU 上逐 token 生成，延迟与体积两条门槛都过不去。
- "优先 ≤ 1.5B"（业主）落到 Julia-1 与 Laya 两个编码器决策模型；"≤ 4B"里能在 llama.cpp 上跑、JevBench 最高的是 lev，作为"开源决策模型在我们数据上的上限"参照；Qwen3-1.7B 代表"通用小模型直接当评审"。
- 不可商用（CC BY-NC）的 OpenJev 27B/Flash 9B、Nimble 9B 直接排除，无论分数。
