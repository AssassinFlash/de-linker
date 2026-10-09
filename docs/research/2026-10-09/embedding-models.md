# 嵌入模型选型：Mac 离线建索引 + 1 vCPU VPS 实时查询编码（含多模态可行性）

日期：2026-10-09 ｜ 语料：约 383 份 PDF（EN+DE 数据表、手册，含表格与接线/尺寸图）
证据规则：外部事实全部经 Apify（`apify/rag-web-browser`）抓取，抓取日期均为 2026-10-09（下文记「抓 10-09」），来源 URL 见 §7。VPS 数据是我在 2026-10-09 13:29 UTC 用只读 SSH 实测的，属于我方设施，不是外部事实。
标记：**实测** = 我方测得；**报告** = 来源公布；**估** = 我按 §2.3 方法推算，上线时必须在机器上复测。

---

## 0. 结论速览

- **约束（业主 2026-10-09 裁定，协调者转达）**：不升级任何主机。只推荐能在现有 VPS（1 vCPU、3.9 GB、无 GPU）上实时编码查询的模型；许可须为 Apache/MIT。
- **文本模型首选：`Snowflake/snowflake-arctic-embed-m-v2.0`**，使用官方 ONNX int8（`onnx/model_int8.onnx`，311 MB），Apache-2.0。
  - 在三套同时有两者数据的德语证据里，与 bge-m3 持平或更好（RTEB +3.7，CLEF +0.12，MIRACL-de −0.2），计算量却只有 bge-m3 的约 37%（非嵌入参数 113M 对 303M）。
  - 单 vCPU 查询延迟估 20–40 ms，genie 进程估 0.55–0.75 GB。
- **回退（资源往下）：`intfloat/multilingual-e5-small`** 官方 qint8 ONNX（118 MB，MIT）。估 5–10 ms，但德语明显更弱。
- **同族往上（只在黄金集证明 M 版不够时）：`snowflake-arctic-embed-l-v2.0`** int8（约 570 MB），估 50–100 ms。
- **多模态：现在不加页面图像检索。** 满足「图像塔在 Mac 离线建索引、文本塔小到 1 核实时」的模型确实存在（SigLIP/CLIP 类、ColSmol、ColModernVBERT），但多语言页面检索分全部低于纯文本管线。比纯文本强的视觉检索器，查询端都是 ≥1.5B（1.5–7B）的语言模型，3B 档多数是非商用许可。替代做法和重新评估的触发条件见 §6.3。
- **升级方案**：业主已排除。
- **混合检索不可省**：德语 RTEB 上 BM25 的 LegalQuAD 分数高于所有 dense 候选；跨语言查询时 BM25 又会崩溃。因此保持 SQLite FTS5（BM25）+ dense，用 RRF 融合。

---

## 1. 约束与实测基线（VPS 只读 SSH，2026-10-09 13:29 UTC，**实测**）

| 项 | 值 |
|---|---|
| CPU | 1 vCPU，AMD EPYC 9354P（Zen 4）；flags 含 `avx512f avx512_vnni avx512bw avx512vl avx2 fma`，ONNX Runtime 的 int8 可走 VNNI 内核 |
| 内存 | total 3915 MB，used 653 MB，available 3261 MB，**swap 0** |
| 常驻进程 RSS | `linker-design-engine`（uvicorn）149 MB；xray 47 MB 与 hysteria 29 MB（业主私人代理，不碰）；monarx-agent 37 MB；fwupd 45 MB；journald 35 MB |
| genie | VPS 上**没有**这个名字的进程，下文按「规划中的查询服务」计入预算 |
| 磁盘/系统 | 剩余 43 GB；Ubuntu 24.04.4 LTS |
| 语料页数 | 本地能取到的 127 份 PDF 共 2,784 页（均值 21.9，中位数 2，p90 67，最大 355）。383 份按均值外推约 **8,400 页（估）** |

---

## 2. 文本模型（第 1 项）

### 2.1 规格、许可与可下载格式（各模型卡与 HF 文件树，抓 10-09）

| 模型 | 参数（非嵌入） | 许可 | 最大长度 | 维度（MRL） | ONNX / int8 / GGUF 可得性 |
|---|---|---|---|---|---|
| `BAAI/bge-m3` | 568M（303M） | MIT | 8192 | 1024 dense + sparse + ColBERT | 官方 ONNX 只有 fp32（2.27 GB）；社区 int8 ONNX `gpahal/bge-m3-onnx-int8`（三种表示一起输出）；GGUF `gpustack/bge-m3-GGUF` Q8_0 635 MB / F16 1.16 GB；Ollama 1.2 GB |
| `intfloat/multilingual-e5-small` | 118M（≈21M，12 层×384） | MIT | 512 | 384 | 官方 `onnx/model.onnx` 470 MB、`model_O4` 235 MB、`model_qint8_avx512_vnni` 118 MB |
| `intfloat/multilingual-e5-base` | 278M（86M） | MIT | 512 | 768 | 官方 fp32 1.11 GB / O4 555 MB / qint8 279 MB |
| `intfloat/multilingual-e5-large` | 560M（303M） | MIT | 512 | 1024 | fastembed 内置（2.24 GB） |
| `jinaai/jina-embeddings-v3` | 572M | **CC-BY-NC-4.0 ✗** | 8192 | 1024 | 卡内有 ONNX 示例 |
| `nomic-ai/nomic-embed-text-v2-moe` | 475M 总 / 305M 激活（8 专家选 2） | Apache-2.0 | **512** | 768（→256） | 官方仓库只有 safetensors 1.9 GB；需 `trust_remote_code`；TEI 支持 |
| `Qwen/Qwen3-Embedding-0.6B` | 0.6B（≈440M，估） | Apache-2.0 | 32k | 1024（32–1024） | 官方 GGUF Q8_0 639 MB / f16 1.2 GB；`onnx-community` int8 614 MB；fastembed ≥0.8.1 内置（`-Q` 量化版要求 onnxruntime ≥1.23）；查询需加 `Instruct:` 前缀 |
| `Snowflake/snowflake-arctic-embed-l-v2.0` | 568M（303M） | Apache-2.0 | 8192 | 1024（→256） | 官方 ONNX fp32 2.27 GB / fp16 ≈1.13 GB / int8·uint8·quantized ≈570 MB；Ollama `snowflake-arctic-embed2` 1.2 GB |
| **`Snowflake/snowflake-arctic-embed-m-v2.0`** | 305M（**113M**） | Apache-2.0 | 8192 | 768（→256） | **官方 ONNX：fp32 1.23 GB / fp16 613 MB / `model_int8`·`model_uint8`·`model_quantized` 各 311 MB**（Transformers.js 导出）；TEI 支持；CLS 池化，查询加前缀 `query: ` |
| `Alibaba-NLP/gte-multilingual-base` | 305M（113M） | Apache-2.0 | 8192 | 768（128–768） | 官方仓库未见 `onnx/` 目录；需 `trust_remote_code`（arctic-m-v2 就是在它上面微调的） |

参考（不在原清单，但与本场景相关）：
- `google/embeddinggemma-300m`：308M，**Gemma Terms**（允许商用但不是 Apache/MIT）。2048 长度；MMTEB 61.15（Q8_0 60.93、Q4_0 60.62）；fastembed 内置。
- `jinaai/jina-embeddings-v5-text-nano`：212–239M，**CC-BY-NC ✗**，德语检索很强（见 2.2）。
- `ibm-granite/granite-embedding-311m/97m-multilingual-r2`：Apache，32k，有 ONNX，但德语偏弱。
- `jinaai/jina-embeddings-v2-base-de`：161M，Apache，德英双语，fastembed 内置。
- `mixedbread-ai/deepset-mxbai-embed-de-large-v1`：487M，Apache。

### 2.2 德语质量证据（全部为报告值；我只做了取均值的算术）

| 模型 | MTEB(deu, v1) 检索 4 任务均值 ① | RTEB(deu, beta) 4 任务均值 ② | MIRACL-de（HardNeg，nDCG@10）③ | CLEF（含德，nDCG@10）④ | MMTEB v2：Mean(Task) / Retr. ⑤ |
|---|---|---|---|---|---|
| arctic-embed-l-v2.0 | **57.09** | **76.77** | **58.95** | **0.541** | 57.03 / 58.36 |
| **arctic-embed-m-v2.0** | **55.24** | **72.70** | 57.37 | 0.534 | — / 54.83（缺任务） |
| bge-m3 | 无德语检索分 | 69.05 | 57.59 | 0.410 | 59.56 / 54.59 |
| nomic-embed-text-v2-moe | 无 | 70.11 | **58.17** | — | 57.64 / 57.21 |
| Qwen3-Embedding-0.6B | 无 | 无 | 54.21 | — | **64.34 / 64.65** |
| gte-multilingual-base | 不完整（GermanQuAD 88.38，GerDaLIR 11.56，XMarket 15.97） | 67.36 | 51.22 | 0.479 | — |
| multilingual-e5-large | 50.03 | — | MIRACL dev de 56.4（BGE-M3 论文） | 0.431 | — |
| multilingual-e5-large-instruct | 51.94 | 71.34 | 43.37（wz-it 引 MTEB results） | — | 63.22 / 57.12 |
| multilingual-e5-base | 48.75 | — | 52.96 | 0.432 | 57.02 / 52.72 |
| **multilingual-e5-small** | 48.18 | 60.87 | 50.83 | — | — |
| embeddinggemma-300m（Gemma 许可） | 无 | 无 | 56.60 | — | 61.15 / 62.49 |
| granite-311m-multilingual-r2 | — | 62.94 | 50.97 | — | 55.96 / 65.21 |
| 参照：jina-v5-text-nano（NC） | 57.62 | — | — | — | 65.52 / 63.26 |
| 参照：BM25（`mteb/baseline-bm25s`） | — | 66.84（其中 LegalQuAD **76.75**） | — | — | — |
| 参照：静态模型 potion-multilingual-128M / static-similarity-mrl-multilingual-v1 | — | 44.23 / 45.95 | — | — | — |

① 来源：mteb-leaderboard.hf.space/benchmark/MTEB(deu, v1) 的逐任务表。四项是 GermanQuAD-Retrieval（MRR@5）、GermanDPR、XMarket-de、GerDaLIR（nDCG@10），定义取自 most-embed-de 博客（2026-09-25）。bge-m3、Qwen3、EmbeddingGemma 在该基准缺德语检索任务。
② 来源：RTEB(deu, beta) 的逐任务表，四项是 German1Retrieval、GermanHealthcare1Retrieval、GermanLegal1Retrieval、LegalQuAD，其中三项为私有测试集。均值是我算的；页面摘要列只显示 LegalQuAD，那篇博客也指出了这一点。
③ 来源：`embeddings-benchmark/results` 仓库的原始 JSON `MIRACLRetrievalHardNegatives`（dev，de 子集）。wz-it 的 2026 文章引用了同一来源的数，我抽查 bge-m3、Qwen3、EmbeddingGemma 三个，都能对上。
④ 来源：Arctic-Embed 2.0 论文表 1。CLEF 覆盖 en/fr/it/de/es，论文用它衡量领域外检索。
⑤ 来源：MMTEB(Multilingual, v2) 排行榜；Qwen3 卡与之一致（取自 2025-05-24 的榜单）。

从这张表得出的结论：
1. **arctic-m-v2 是德语「质量/算力」比最优的可商用模型**：MTEB-deu 检索只比 L 版低 1.85（bge-m3 在该基准没有德语检索分），RTEB 比 bge-m3 高 3.7，MIRACL-de 与 bge-m3 基本打平（−0.2），CLEF 远高于 bge-m3（0.534 对 0.410）。Arctic 2.0 论文写明训练聚焦 en/fr/es/de/it/pt/pl。
2. **Qwen3-0.6B 的 MMTEB 总分高，但德语 MIRACL 反而更低**（54.21，bge-m3 57.59，arctic-m 57.37）。wz-it（2026）也指出总分排序和德语检索排序不一致。
3. **dense 和 BM25 各有不可替代的场景**：德语法律类任务上 BM25 很强，e5-small 的 RTEB 均值甚至低于 BM25；Vespa（2026-01-14）报告每个模型做混合都比纯语义高 3–5 个百分点。反过来，ViDoRe V3 在跨 6 种语言查询时 BM25S 只有 20.3，Qwen3-0.6B 43.8，BGE-M3 41.3。所以德语问题检索英文数据表必须依赖 dense。
4. 静态模型（Model2Vec 等）在德语上低于 BM25，没有价值。

### 2.3 CPU 延迟（短查询）

**公开实测锚点**（都不是 1 vCPU）：

| 来源 | 硬件 | 结果 |
|---|---|---|
| Vespa NanoBEIR 排行榜 + 博客（2026-01-14） | AWS c7g.2xlarge（多 vCPU 的 Graviton3）；纯 ONNX 推理；8 个词的查询 | **arctic-m-v2：fp32 27.1 ms，int8 8.6 ms**（NanoBEIR 0.662 → 0.652）；multilingual-e5-base fp32 20.9 ms；EmbeddingGemma 32.0 ms；e5-small-v2 int8 2.5 ms。博客总结：CPU 上 INT8 快 2.7–3.4×，保留 94–98% 质量 |
| `Soju06/bge-m3.c` BENCHMARKS | Ryzen 9 5900X（约 11 个物理核，AVX2，无 VNNI） | bge-m3 16 token：torch fp32 110–132 ms；int8 默认 31 ms；int8 fast 15 ms（nDCG −0.7%）。指出 XLM-R 隐层有离群通道（dim 386），朴素 W8A8 量化没过质量门 |
| Manticore 博客 | 16 核，ORT | all-MiniLM-L12-v2：单客户端线程单行插入约 14 ms，单线程 72 docs/s |
| HF 讨论 Qwen3-Embedding-0.6B #48 | i9-13900HK，12 线程，TEI `cpu-ipex` | 最小请求约 30 ms |
| llama.cpp issue #19933（2026-02-26） | 同一台机，硬件未注明 | Qwen3-0.6B GGUF 6,878 tok/s，bge-m3/arctic-l GGUF 31,383 tok/s，**每 token 慢约 4.6 倍** |
| sbert 官方效率文档 | — | i7-13700K 上 OpenVINO INT8 最快；HF 云 CPU 实例上 llama.cpp 最快；BGE-M3 Q4 GGUF 没通过与 fp32 的一致性检查。结论是要在部署硬件上实测 |

我共做了 9 次 Apify 检索，没有找到这些模型在 1–2 vCPU 上的公开实测，所以下面是**估算**。

**估算方法**：FLOPs ≈ 2 × 非嵌入参数 × token 数。单个 Zen 4 vCPU 的有效吞吐取 fp32 40–60 GFLOPS、int8（VNNI）150–300 GOPS，再加约 2 ms 固定开销（分词、session 调用）。结果用上表 Vespa 和 bge-m3.c 的比例做了交叉校验。查询按 24 token 计（`query: ` 加约 12 个德语词）；Qwen3 因指令前缀按 40 token 计。

| 模型 | GFLOP/查询 | fp32（估） | int8（估） |
|---|---|---|---|
| multilingual-e5-small | 1.0 | 20–30 ms | **5–10 ms** |
| **arctic-embed-m-v2.0** | 5.4 | 90–140 ms | **20–40 ms** |
| multilingual-e5-base | 4.1 | 70–105 ms | 15–30 ms |
| bge-m3 / arctic-l-v2 / me5-large | 14.5 | 240–360 ms | 50–100 ms |
| Qwen3-Embedding-0.6B | 35 | 0.6–0.9 s | 120–240 ms |
| 2B 级 VLM 查询端（ColQwen2、Qwen3-VL-Embedding-2B、vdr-2b） | 90–120 | 1.5–3 s | 0.3–0.8 s，且 int8 权重约 +1.7–2.2 GB 内存 |

向量检索本身：约 2.5 万条 × 768 维 fp32（77 MB），numpy 暴力点积估 5–20 ms（受内存带宽限制）；用 MRL 截到 256 维估 2–6 ms。这个规模不需要 ANN 索引。

### 2.4 排除项与原因

| 模型 | 排除原因 |
|---|---|
| jina-v3、jina-v5 | 许可 NC |
| EmbeddingGemma | Gemma Terms，不是 Apache/MIT。技术上很适合 CPU；业主若接受该许可可重新考虑 |
| LFM2-ColBERT-350M | LFM Open License v1.0（不是 Apache/MIT），且多向量索引更大 |
| Qwen3-0.6B | 许可可用，但每次查询 CPU 开销约为 arctic-m 的 4–6 倍，德语 MIRACL 没有更好 |
| bge-m3 | 许可可用，但算力是 arctic-m 的 2.7 倍；官方 ONNX 只有 fp32 2.27 GB；XLM-R 量化有离群通道风险（Q4 GGUF 一致性检查失败）。德语质量不比 arctic-m 高 |
| nomic-v2-moe | Apache，MIRACL-de 最高（58.17），但只支持 512 token、没有官方 ONNX、是自定义 MoE 代码，工程风险高。只有在自己导出 ONNX 很顺利时，才值得作为黄金集对比的挑战者 |
| gte-multilingual-base | 被它的微调版 arctic-m-v2 全面压过 |
| granite r2 | 德语偏弱 |
| 静态模型 | 德语上低于 BM25 |

---

## 3. 多模态（第 2 项）

### 3.1 (a) 后交互 / VLM 文档检索器：查询端都是大语言模型

ViDoRe v1/v2 指标为 nDCG@5，v3 为 nDCG@10；数据来自 MTEB 排行榜与 ViDoRe V3 论文（arXiv 2601.08620），抓 10-09。

| 模型 | 参数 | 许可 | 查询编码器 | ViDoRe v1 | v2 | v3（多语言查询） |
|---|---|---|---|---|---|---|
| `vidore/colpali-v1.3` | 2.9B | 适配器 MIT + PaliGemma 的 **Gemma 许可** | PaliGemma 语言模型 | 84.75 | 54.72 | 43.05 |
| `vidore/colqwen2-v1.0` | 2.2B | Apache-2.0 | Qwen2-VL-2B 语言模型（约 1.5B）；每页最多 768 个 patch × 128 维 | 89.23 | 56.04 | 44.65 |
| `vidore/colqwen2.5-v0.2` | 3.0B | 适配器 MIT，但骨干是 **Qwen RESEARCH LICENSE（仅研究/评估）✗** | Qwen2.5-VL-3B | 89.54 | 60.06 | 51.90 |
| `nomic-ai/colnomic-embed-multimodal-3b` | 3.0B | Qwen2.5-VL-3B 衍生，卡上写「weights for research use」✗ | 同上 | 89.86 | 55.68 | 55.78 |
| `nomic-ai/colnomic-embed-multimodal-7b` | 7.0B | Apache-2.0 | Qwen2.5-VL-7B | 89.72 | 60.25 | 57.33 |
| `jinaai/jina-embeddings-v4` | 3.8B | **Qwen Research License ✗**（卡上说明最初误标为 CC-BY-NC） | Qwen2.5-VL-3B | 90.35 | 58.23 | 56.34 |
| `Qwen/Qwen3-VL-Embedding-2B`（单向量） | 2.1B | Apache-2.0，支持 30+ 语言 | Qwen3-VL-2B | — | — | 52.64 |
| `llamaindex/vdr-2b-multi-v1`（单向量，1536 维可 MRL） | 2B | Apache-2.0；训练语料含德语（共 50 万样本） | Qwen2-VL-2B，查询时还要带一张 56×56 的空白图 | 卡上报告 84.0 | — | — |
| `DataScience-UIBK/Argus-Colqwen3.5-2b-v0` | 2.3B | Apache-2.0 | 2B 级语言模型 | 91.49 | 61.84 | 60.09（公开子集） |
| `VAGOsolutions/SauerkrautLM-ColQwen3-2b-v0.1`（德国团队） | 2.1B | Apache-2.0 | 2B 级语言模型 | 90.24 | 57.95 | 54.32（公开子集） |
| `nvidia/llama-nemoretriever-colembed-1b-v1` | 2.4B | **NVIDIA Non-Commercial ✗** | Llama 1B | 90.50 | 62.96 | 55.59 |
| **`vidore/colSmol-256M`** | 256M | MIT | SmolLM2-135M（SmolVLM-256M = 93M SigLIP + SmolLM2-135M），**1 核可跑** | 79.74 | 34.82 | **21.40** |
| `vidore/colSmol-500M` | 500M | MIT | 小型语言模型 | 82.49 | 42.89 | — |
| **`ModernVBERT/colmodernvbert`** | 252M | MIT，**仅英语** | 小型编码器，**1 核可跑** | — | — | **26.07** |

补充事实：
- ColPali、ColQwen、ColSmol 的训练集「fully English by design」（见各卡）。
- ViDoRe V3 博客：多语言查询会让最好的模型掉 3–5 分。
- ViDoRe V3 的多语言平均分：colsmol256 0.214、colmodernvbert 0.245、colqwen2 0.447、colqwen2.5 0.519、colnomic-3b 0.558、jina-v4 0.576。
- **同一基准上的纯文本管线**（文本检索器读 NeMo 抽取出的 Markdown）：Qwen3-0.6B **43.8**、BGE-M3 **41.3**、LFM2-ColBERT-350M 44.9、Qwen3-8B 51.0、BM25S 20.3。论文脚注说，按页再切块或加入图像描述都没有提升他们的结果。

### 3.2 (b) 双塔（CLIP 类）：文本塔小，但读不懂文档页

| 模型 | 文本塔 | 图像塔 | 许可 | 德语 | 文档页检索 |
|---|---|---|---|---|---|
| `jinaai/jina-clip-v2` | Jina-XLM-R 561M | EVA02-L 304M | **CC-BY-NC ✗** | 89 种语言 | ViDoRe v2 26.94 |
| `google/siglip2-base-patch16-224` | 约 0.28B（共 0.4B，256k 词表，估） | ViT-B/16 | Apache-2.0 | 多语 | SigLIP2 不在 ViDoRe 榜上。同族 SigLIP：base-multilingual 在 v3 为 6.17，so400m 在 v1/v2/v3 为 56.38/33.00/15.75 |
| `nomic-ai/nomic-embed-vision-v1.5` + `nomic-embed-text-v1.5` | 137M（仅英语） | 92.9M | Apache-2.0 | ✗ | ViDoRe v1 11.92（ColPali 论文 12.9） |
| `laion/CLIP-ViT-H-14-frozen-xlm-roberta-large…` | XLM-R large | ViT-H/14 | MIT | 多语 | 不在榜上。同族 LAION CLIP-bigG：v1 43.19，v2 19.35 |
| `sentence-transformers/clip-ViT-B-32-multilingual-v1` | 约 0.1B，蒸馏多语模型，50+ 语言 | OpenAI CLIP ViT-B/32 | Apache-2.0 | 多语 | 不在榜上。OpenAI CLIP ViT-B/32 在 v3 为 2.23 |
| `BAAI/bge-visualized`（m3 版） | bge-m3 | EVA-CLIP | 卡上未声明许可 | 多语 | ViDoRe v1 12.38 |

ColPali 论文的 ViDoRe v1 基线（2024）：SigLIP 51.4；Unstructured+OCR+BGE-M3 66.1；加图像描述 67.0；ColPali 81.3。这些数说明 CLIP 类模型在文档页上弱于「OCR + 文本嵌入」。

### 3.3 在业主约束下的判断

- **能做到「Mac 离线建图像索引、VPS 1 核实时编码文本查询」的**：SigLIP/SigLIP2、多语 CLIP、nomic-vision v1.5（仅英语）、bge-visualized-m3（文本端就是 bge-m3，int8 估 50–100 ms）、ColSmol-256M/500M、ColModernVBERT、jina-clip-v2（NC）。
- **但它们的质量都不可接受**：在有数据的文档页基准上全部低于纯文本管线（v3 多语言：CLIP/SigLIP 类 2–17，ColSmol 21.4，ColModernVBERT 26.1，而文本端 41–44；v1 上 nomic/bge-visual 约 12，jina-clip-v2 在 v2 为 26.9）。ColSmol 在英语为主的 v1 上有 79.7，但多语言 v3 掉到 21.4。没有证据表明把这么弱的视觉通道融合进来能带来增益。
- **比纯文本强的视觉检索器**（ColQwen2.5、ColNomic、jina-v4、Argus/Sauerkraut ColQwen3、Qwen3-VL-Embedding-2B、vdr-2b）的查询端都是 1.5–3B 的语言模型。在 1 vCPU 上 int8 估 0.3–0.8 s，权重约多占 2 GB 内存，而机器没有 swap；其中 3B 档又大多是非商用许可。
- 我抓取的模型卡里，没有一家为这些大模型提供官方的小型纯文本查询编码器。
- **结论：现在不加页面图像检索**。

---

## 4. 服务方式（第 3 项）

| 方式 | 运行时依赖 | 对 arctic-m-v2 | 内存 | 延迟证据 | 判断 |
|---|---|---|---|---|---|
| **onnxruntime + `tokenizers` 直接调用** | onnxruntime、tokenizers、numpy，**不需要 torch** | 官方 `onnx/model_int8.onnx` 311 MB | 约等于文件大小 + 50–150 MB（估） | Vespa：int8 8.6 ms（多 vCPU），本机估 20–40 ms | **推荐** |
| fastembed（Qdrant） | 底层同样是 ORT + tokenizers，不需要 torch | 用 `TextEmbedding.add_custom_model(...)` 注册，指定 CLS 池化、`model_file="onnx/model_int8.onnx"`（README 示例用的正是 me5-small） | 同上 | — | 可选，省样板代码。v0.8.1 起内置 embeddinggemma、Qwen3-0.6B/-Q、siglip2-base、potion-multilingual；早已内置 me5-large、jina-v2-base-de、paraphrase-multilingual-* |
| sentence-transformers `backend="onnx"` | torch + transformers（+ optimum） | GTE 架构需 `trust_remote_code` | torch 本身占内存大（估数百 MB） | 文档基准是多核数据 | **只在 Mac 上用来导出/量化**（`export_dynamic_quantized_onnx_model(..., "avx512_vnni")`，文档说几种量化配置提速相近），VPS 运行时不用 |
| llama.cpp GGUF（`llama-server --embedding`） | 一个二进制文件 | 没有找到 arctic-m-v2 的 GGUF；bge-m3 Q8_0 635 MB，Qwen3-0.6B Q8_0 639 MB | 约等于 GGUF 文件 + 上下文缓冲 | Qwen 每 token 比 XLM-R 类慢约 4.6 倍（#19933）；BGE-M3 Q4 一致性检查失败 | 只在改用 bge-m3/Qwen3 时考虑 |
| TEI CPU（`ghcr.io/huggingface/text-embeddings-inference:cpu-1.9`，x86 用 MKL） | Docker / Rust 服务 | 支持 GTE、XLM-R、NomicBERT、Qwen3、Gemma3 | 文档里没有 int8 路径，按 fp32/bf16 权重估 arctic-m 0.6–1.2 GB | Qwen3-0.6B 在 12 线程 cpu-ipex 上约 30 ms | 对这台机器太重，不推荐 |

---

## 5. 升级方案（第 4 项）

业主已排除（2026-10-09 裁定：共享主机与 VPS 都不升级）。

---

## 6. 推荐（第 5 项）

### 6.1 文本模型

1. **首选**：`snowflake-arctic-embed-m-v2.0`，官方 int8 ONNX，768 维。
   - 查询前缀 `query: `，文档不加前缀，CLS 池化后做 L2 归一化。
   - 如果内存或速度吃紧，可用 MRL 截到 256 维。arctic-m-v2 卡上报告：BEIR 55.4→54.4（−1.81%），MIRACL 55.2→54.0（−2.17%），CLEF 51.7→50.6（−2.13%），CLEF-Full 53.9→52.3（−3.06%）。
   - 文档切块 ≤512 token。
2. **回退（往下）**：`multilingual-e5-small`，官方 `model_qint8_avx512_vnni.onnx`，384 维。查询与文档分别加 `query: ` / `passage: ` 前缀。
3. **同族往上（只在黄金集证明 M 版不够时）**：`snowflake-arctic-embed-l-v2.0` int8。查询协议相同，但向量空间不同，换模型必须重建索引。
4. **索引与查询必须一致**：Mac 端用**同一个 ONNX 文件**嵌入文档。在 SQLite 里记录模型 revision 和 sha256、tokenizer sha、前缀、池化方式、维度，VPS 加载时比对，不一致就拒绝服务，避免同一规则有两份实现。

### 6.2 内存预算（现有 VPS：已用 653 MB，**实测**，无 swap）

| 项 | arctic-m-v2 int8 | e5-small int8 | arctic-l-v2 int8 |
|---|---|---|---|
| genie 基础（FastAPI/uvicorn，**不装 torch**；参照引擎 149 MB） | 100–150 MB（估） | 同左 | 同左 |
| ORT 会话 + 模型 | 350–450 MB（估，文件 311 MB） | 150–200 MB（估） | 650–750 MB（估） |
| tokenizers | 20–40 MB | 20–40 MB | 20–40 MB |
| 向量（约 2.5 万块；8,400 页按每页 2–3 块估） | fp32 77 MB（int8 19 MB；256 维 fp32 26 MB） | 38 MB | 102 MB |
| SQLite FTS5 页缓存 | 可回收，小 | 同左 | 同左 |
| **genie 合计** | **约 0.55–0.75 GB** | 约 0.3–0.45 GB | 约 0.85–1.05 GB |
| **上线后剩余 available** | **约 2.5–2.7 GB** | 约 2.8 GB | 约 2.2–2.4 GB |

**不安全的组合**：bge-m3 fp32（单权重 2.27 GB）；任何 2B 级 VLM 的查询端（再多约 2 GB）。

### 6.3 多模态：现在不加；替代做法与触发条件

- **替代做法**：页面图像的信息在 Mac 离线阶段转成文字，然后用同一个文本模型嵌入，VPS 查询路径完全不变。
  1. 先用 PDF 文本层；扫描页走 OCR。
  2. 只有黄金集证明需要时，再对接线图和尺寸图用开源 VLM 生成描述（Mac 上运行）。注意 ViDoRe V3 发现加入图像描述没有带来提升，所以这一步不能默认开启。
  3. 页面截图可以作为结果展示附在答案里，但不参与检索。
- **重新评估视觉检索，须两个条件同时满足**（阈值是我的建议，可调）：
  - **需求侧**：黄金集里有 ≥30 个只能从图或表的图形中得到答案的问题，并且做完 Mac 端 OCR/描述增强后，纯文本管线在这个子集上的 Recall@10 仍 < 0.7。
  - **供给侧**：出现 Apache/MIT 许可的视觉检索器，查询端 ≤约 350M 参数（在这台 vCPU 上 int8 p95 < 150 ms），且 ViDoRe V3 多语言分 ≥ 纯文本管线（≥约 44）。
  - 业主不升级，所以缺了供给侧条件就不能做。只满足需求侧时，改进方向是 Mac 端的文字化，而不是 VPS 的查询端。

### 6.4 运行参数与上线验收（只保留会改变决定的检查）

**运行参数**：
- `intra_op_num_threads=1`、`inter_op_num_threads=1`。
- `session.intra_op.allow_spinning=0`：Manticore 指出 ORT 线程池默认自旋，在单 vCPU 上会和引擎抢核。
- uvicorn 只开 **1 个 worker**（每个 worker 会各加载一份模型）。
- 用 systemd 给 genie 设 `MemoryMax≈1.2G`，让 OOM 只杀 genie，不连累引擎和代理。
- `model_int8.onnx` 与 `model_quantized.onnx` 在机器上各测一次，取更快的那个。

**验收**（每一项都对应一个具体决定）：

| 检查 | 不合格时的决定 |
|---|---|
| 用 50 条黄金查询测 p50/p95 | int8 p95 > 150 ms → 降级到 e5-small |
| genie RSS | > 1.1 GB → 降级到 e5-small |
| Mac 与 VPS 对同一查询的向量余弦 ≥ 0.99 | 不满足说明模型或分词器不一致 → 修正后再上线 |
| 黄金集 Recall@10：混合检索 vs 仅 BM25，单列德语问英文文档的子集 | arctic-m 不达标 → 试 arctic-l |

---

## 7. 来源（均经 Apify `rag-web-browser` 抓取，2026-10-09）

**模型卡与文件树**：
- https://huggingface.co/BAAI/bge-m3 ；https://huggingface.co/BAAI/bge-m3/tree/main/onnx
- https://huggingface.co/intfloat/multilingual-e5-small（以及 -base、-large）；https://huggingface.co/intfloat/multilingual-e5-small/tree/main/onnx ；https://huggingface.co/intfloat/multilingual-e5-base/tree/main/onnx
- https://huggingface.co/jinaai/jina-embeddings-v3 ；https://huggingface.co/jinaai/jina-embeddings-v5-text-nano ；https://huggingface.co/jinaai/jina-embeddings-v5-text-small
- https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe ；…/tree/main
- https://huggingface.co/Qwen/Qwen3-Embedding-0.6B ；https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/tree/main ；https://huggingface.co/onnx-community/Qwen3-Embedding-0.6B-ONNX/tree/main/onnx
- https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0 ；https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0 ；两者的 …/tree/main/onnx
- https://huggingface.co/Alibaba-NLP/gte-multilingual-base ；https://huggingface.co/google/embeddinggemma-300m ；https://huggingface.co/onnx-community/embeddinggemma-300m-ONNX/tree/main/onnx
- https://huggingface.co/ibm-granite/granite-embedding-278m-multilingual ；…-107m-multilingual ；…-311m-multilingual-r2 ；…-97m-multilingual-r2
- https://huggingface.co/jinaai/jina-embeddings-v2-base-de ；https://huggingface.co/mixedbread-ai/deepset-mxbai-embed-de-large-v1
- https://huggingface.co/gpahal/bge-m3-onnx-int8 ；https://huggingface.co/gpustack/bge-m3-GGUF/tree/main ；https://huggingface.co/electroglyph/snowflake-arctic-embed-m-v2.0-ONNX-uint8
- https://ollama.com/library/bge-m3 ；https://ollama.com/library/snowflake-arctic-embed2

**基准与论文**：
- https://mteb-leaderboard.hf.space/benchmark/MTEB(deu,%20v1) ；…/RTEB(deu,%20beta) ；…/MTEB(Multilingual,%20v2) ；…/ViDoRe(v1) ；…/ViDoRe(v2) ；…/ViDoRe(v3)
- https://github.com/embeddings-benchmark/results ：原始 JSON 在 https://raw.githubusercontent.com/embeddings-benchmark/results/main/results/<org>__<model>/<rev>/MIRACLRetrievalHardNegatives.json ，以及 GermanQuAD-Retrieval、GermanDPR、XMarket、GerDaLIR、MIRACLRetrieval
- https://huggingface.co/blog/malteos/most-embed-de-german-embedding-model（2026-09-25）；https://wz-it.com/en/blog/best-embedding-models-german/（2026）
- https://arxiv.org/html/2402.03216v4（BGE-M3）；https://arxiv.org/html/2412.04506（Arctic-Embed 2.0）；https://arxiv.org/html/2502.20204（Granite Embedding）；https://arxiv.org/html/2506.05176（Qwen3 Embedding）；https://arxiv.org/html/2509.20354（EmbeddingGemma）；https://arxiv.org/html/2502.07972（Nomic MoE）；https://arxiv.org/html/2407.19669（mGTE）

**服务与延迟**：
- https://sbert.net/docs/sentence_transformer/usage/efficiency.html
- https://qdrant.github.io/fastembed/examples/Supported_Models/ ；https://github.com/qdrant/fastembed ；https://github.com/qdrant/fastembed/releases ；https://github.com/qdrant/fastembed/blob/main/fastembed/text/pooled_embedding.py
- https://huggingface.co/docs/text-embeddings-inference/supported_models ；https://huggingface.co/docs/text-embeddings-inference/local_cpu
- https://github.com/Soju06/bge-m3.c/blob/main/docs/BENCHMARKS.md
- https://blog.vespa.ai/embedding-tradeoffs-quantified/（2026-01-14）；https://huggingface.co/spaces/vespa-engine/nanobeir-hybrid-evaluation
- https://manticoresearch.com/blog/onnx-embeddings-speedup/
- https://github.com/ggml-org/llama.cpp/issues/19933 ；https://huggingface.co/Qwen/Qwen3-Embedding-0.6B/discussions/48

**多模态**：
- https://huggingface.co/vidore/colpali-v1.3 ；…/colqwen2-v1.0 ；…/colqwen2.5-v0.2 ；…/colSmol-256M ；…/colSmol-500M
- https://huggingface.co/nomic-ai/colnomic-embed-multimodal-3b ；…-7b ；https://huggingface.co/nomic-ai/nomic-embed-multimodal-3b
- https://huggingface.co/jinaai/jina-embeddings-v4 ；https://huggingface.co/jinaai/jina-clip-v2 ；https://huggingface.co/jinaai/jina-embeddings-v5-omni-nano
- https://huggingface.co/google/siglip2-base-patch16-224 ；https://huggingface.co/nomic-ai/nomic-embed-vision-v1.5 ；https://huggingface.co/laion/CLIP-ViT-H-14-frozen-xlm-roberta-large-laion5B-s13B-b90k ；https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1 ；https://huggingface.co/BAAI/bge-visualized
- https://huggingface.co/llamaindex/vdr-2b-multi-v1 ；https://huggingface.co/marco/mcdse-2b-v1 ；https://huggingface.co/ModernVBERT/colmodernvbert ；https://huggingface.co/tsystems/colqwen2.5-3b-multilingual-v1.0（此卡称骨干为 Apache，与 vidore/Jina 的说明相矛盾，按研究许可处理）
- https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B ；https://huggingface.co/DataScience-UIBK/Argus-Colqwen3.5-2b-v0 ；https://huggingface.co/VAGOsolutions/SauerkrautLM-ColQwen3-2b-v0.1 ；https://huggingface.co/nvidia/llama-nemoretriever-colembed-1b-v1 ；https://huggingface.co/ibm-granite/granite-vision-3.3-2b-embedding ；https://huggingface.co/LiquidAI/LFM2-ColBERT-350M ；https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct
- https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/main/LICENSE（Qwen RESEARCH LICENSE：「Non-Commercial」指仅用于研究或评估）；https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct
- https://arxiv.org/html/2407.01449（ColPali）；https://arxiv.org/html/2412.08802（jina-clip-v2）；https://arxiv.org/html/2601.08620v1（ViDoRe V3）；https://huggingface.co/blog/QuentinJG/introducing-vidore-v3

原始抓取文件（未做清洗）保存在本 scratchpad 的 `raw/` 目录。
