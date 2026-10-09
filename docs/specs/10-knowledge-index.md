# #10 文档与知识索引

依据：`docs/research/2026-10-09/knowledge-audit.md`。

## 来源
媒体库里 mime 为 `application/pdf` 的全部附件（按 sha256 去重，预计 383 份），经 #6 的快照在本地取得；每份记录 `{sha256, url(我们托管), title, brand, models[], doc_type(datasheet|manual|compatibility|certificate|other), lang(en|de), pages}`，品牌与型号由商品的 documents 字段反查。不索引营销页、FAQ、AI 写的概念说明。

## 构建（`services/genie/index/`，`just index`，在 Mac 上离线）
1. 解析：Docling → 带页码的 Markdown；表格保留为整块。
2. 分块：≤512 token；表格整块（超长则按行切并重复表头）；每块前加上下文头 `brand | model(s) | doc_type | title | section | page`。
3. 向量：voyage-4（环境变量 `VOYAGE_API_KEY`，多语）；无密钥时用本地 BGE-M3（`sentence-transformers`）作为备选，索引记录所用模型。
4. 存储：单个 SQLite：`documents`、`chunks(id, doc_sha, page, section, text, lang, model_tags)`、`chunks_fts`（FTS5，unicode61 + 德语复合词不拆）、`chunks_vec`（sqlite-vec）。
5. 发布：`index-<version>.sqlite` + manifest → VPS `/opt/linker-genie/index/<version>/`，`current` 软链，回滚即切软链。

## 检索（`services/genie/retrieval.py`）
`search_documents(query, lang, product_ids=None, doc_types=None, k=8)`：先按 product_ids 对应的型号标签圈定文档（无则全库）；FTS5 与向量各取 top-30，RRF 融合；可选重排（bge-reranker，CPU）；返回 `[{chunk_id, doc_url, page, section, text, score}]`。向量不可用时退回纯 FTS。

## 引用与核验（供 #13）
模型只能引用 `chunk_id`；服务端渲染为"文档标题 · 第 N 页"并链接 `url#page=N`；答案里的数字必须出现在被引块文本中（确定性检查）。

## 模型对比（bake-off，业主 2026-10-09 要求：用证据定模型，差距不大就用无成本的）
同一黄金集、同一分块、同一融合下比较：BM25 基线；开源文本 BGE-M3；开源文本 multilingual-e5-base（VPS 1 vCPU 可实时跑的量级）；付费 API `gemini-embedding-2` 文本（aihubmix，OpenAI 兼容 `/v1/embeddings`，3072 维）；`gemini-embedding-2` 多模态（aihubmix 的 Gemini 原生 `embedContent`，页面渲染为 PNG 做页面向量）。指标：召回@5、页码正确率、查询延迟、构建成本、索引体积；黄金集 ≥200 问且含 ≥30 个图类问题（接线图、尺寸图、图表）。决策规则：API 相对开源在召回@5 与页码正确率上的提升都 < 5 个百分点 → 用开源；否则用 API 并记录月成本；多模态只看图类子集的提升。密钥在 `~/.config/terravolt-builder/aihubmix.env`，永不进仓库。结果表：`docs/research/2026-10-09/embedding-bakeoff.md`。

## 评测（`services/genie/index/eval/`）
黄金集：从旧仓库的事实卡（ADR-0030，路径用 `git ls-tree` 查找）抽逐字引文生成 EN/DE 问答 ≥ 200 条；指标：召回@5、引用页码正确率；`just eval` 输出表格进 PR。

## 不做
不在 VPS 上解析或跑模型；不索引外部网页。

## 验收
- [ ] 全部 PDF 进索引，失败清单为空或逐条说明；索引大小与构建时间写入 PR。
- [ ] 召回@5 ≥ 90%，引用页码正确率 ≥ 95%，低于阈值不合并。
- [ ] 发布与回滚各演练一次（本地 VPS 模拟目录即可，真 VPS 在 #13）。
