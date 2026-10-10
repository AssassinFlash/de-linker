# #10 文档与知识索引

依据：`docs/research/2026-10-09/knowledge-audit.md`。

## 来源
媒体库里 mime 为 `application/pdf` 的全部附件（按 sha256 去重，预计 383 份），经 #6 的快照在本地取得；每份记录 `{sha256, url(我们托管), title, brand, models[], doc_type(datasheet|manual|compatibility|certificate|other), lang(en|de), pages}`，品牌与型号由商品的 documents 字段反查。不索引营销页、FAQ、AI 写的概念说明。

## 构建（`services/genie/index/`，`just index`，在 Mac 上离线）
1. 解析：Docling → 带页码的 Markdown；表格保留为整块。
2. 分块：≤512 token；表格整块（超长则按行切并重复表头）；每块前加上下文头 `brand | model(s) | doc_type | title | section | page`。
3. 向量：由 bake-off 决定；开源首选 snowflake-arctic-embed-m-v2.0 int8 ONNX（ONNX Runtime 单线程、关闭线程自旋、单 worker、运行时不装 torch），回退 multilingual-e5-small；API 候选为 gemini-embedding-2；索引记录所用模型。排除非商用许可模型（jina-v3/v5）与 Gemma 条款模型。
4. 存储：单个 SQLite：`documents`、`chunks(id, doc_sha, page, section, text, lang, model_tags)`、`chunks_fts`（FTS5，unicode61 + 德语复合词不拆）、`chunks_vec`（sqlite-vec）。
5. 发布：`index-<version>.sqlite` + manifest → VPS `/opt/linker-genie/index/<version>/`，`current` 软链，回滚即切软链。

## 索引放在哪里：由 bake-off 决定（业主 2026-10-09）
线上事实（2026-10-09 只读实测）：共享主机的 MariaDB 支持向量函数与向量索引（`VEC_DISTANCE_*` 可用，11.7+），InnoDB 全文索引可用，PHP 自带 SQLite 3.45 开了 FTS5；主机上没有 Python，不能跑任何本地模型。因此：
- **A. API 向量胜出**（gemini-embedding-2 等）：索引搬到共享主机——块与向量存进 WordPress 的 MariaDB（VECTOR 列 + 向量索引 + FULLTEXT），`search-knowledge` 成为 `linker-commerce` 里的纯 PHP + SQL，查询向量经 API 取得；VPS 只保留 Genie 代理循环与引擎。
- **B. 开源文本向量胜出**：查询编码需要进程跑模型 → 索引与编码器留在 VPS（SQLite FTS5 + sqlite-vec），按下文运行时约束。
- **C. 纯 BM25 与混合检索差距 < 5 个百分点**：不用向量，索引（全文）放共享主机，无 API、无模型。
构建管线与存储无关：Docling 解析与分块的产物以 JSONL（块、页码、上下文头、可选向量）为中间格式，提供导出到 MariaDB（SQL）与 SQLite 两个目标；bake-off 报告里必须单列"BM25 单独 vs 混合"的差距，供 C 判断。

## 运行时约束（业主 2026-10-09：不升级任何主机）
VPS 为 1 vCPU、3.9 GB、无 GPU。查询时的向量编码只能是：① 在 1 核上实时可跑的文本模型（int8 后约 300M 参数以内，如 multilingual-e5-base；BGE-M3 int8 以实测延迟 ≤1.5 s 为准），或 ② API（aihubmix 的 gemini-embedding-2 等，由 bake-off 决定）。自托管重排器在 1 核上不可行：重排只用 API 或不做。内存预算：引擎 + Genie 服务 + 索引 + 模型合计 ≤ 3 GB，索引以 SQLite 文件按需读取。多模态页面向量：图像侧只在 Mac 离线构建；查询侧要么走 API，要么文本塔满足 ① 的约束。

## 检索（`services/genie/retrieval.py`）
`search_documents(query, lang, product_ids=None, doc_types=None, k=8)`：先按 product_ids 对应的型号标签圈定文档（无则全库，圈定无果亦回全库）；FTS5 与向量各取 top-30，RRF 融合；可选重排（bge-reranker，CPU）；返回 `[{chunk_id, doc_url, page, section, text, score}]`。向量不可用时退回纯 FTS。
> 2026-10-10 bake-off 实测修订（`embedding-bakeoff.md` §2）：本语料上等权 RRF 融合比向量单路低 11.6pp 召回@5、加权 2:1/3:1 更差，出厂检索改为**向量独立成序**，BM25 降为本机没有该索引模型查询编码器时的回退；按商品圈定、圈定空回全库的行为不变。

## 引用与核验（供 #13）
模型只能引用 `chunk_id`；服务端渲染为"文档标题 · 第 N 页"并链接 `url#page=N`；答案里的数字必须出现在被引块文本中（确定性检查）。

## 模型对比（bake-off，业主 2026-10-09 要求：用证据定模型，差距不大就用无成本的）
同一黄金集、同一分块、同一融合下比较：BM25 基线；开源文本 **snowflake-arctic-embed-m-v2.0**（Apache-2.0，官方 int8 ONNX；德语检索分高于 bge-m3 且算力只有其 37%，见 `docs/research/2026-10-09/embedding-models.md`）；开源文本 multilingual-e5-small（MIT，轻量回退）；BGE-M3 作对照；付费 API `gemini-embedding-2` 文本（aihubmix，OpenAI 兼容 `/v1/embeddings`，3072 维）；`gemini-embedding-2` 多模态（aihubmix 的 Gemini 原生 `embedContent`，页面渲染为 PNG 做页面向量）。指标：召回@5、页码正确率、查询延迟、构建成本、索引体积；黄金集 ≥200 问且含 ≥30 个图类问题（接线图、尺寸图、图表）。决策规则：API 相对开源在召回@5 与页码正确率上的提升都 < 5 个百分点 → 用开源；否则用 API 并记录月成本；多模态只看图类子集的提升。密钥在 `~/.config/terravolt-builder/aihubmix.env`，永不进仓库。结果表：`docs/research/2026-10-09/embedding-bakeoff.md`。

## 评测（`services/genie/index/eval/`）
黄金集：从旧仓库的事实卡（ADR-0030，路径用 `git ls-tree` 查找）抽逐字引文生成 EN/DE 问答 ≥ 200 条；指标：召回@5、引用页码正确率；`just eval` 输出表格进 PR。

## 不做
不在 VPS 上解析或跑模型；不索引外部网页。

## 验收
- [ ] 全部 PDF 进索引，失败清单为空或逐条说明；索引大小与构建时间写入 PR。
- [ ] 召回@5 ≥ 90%，引用页码正确率 ≥ 95%，低于阈值不合并。
- [ ] 发布与回滚各演练一次（本地 VPS 模拟目录即可，真 VPS 在 #13）。
