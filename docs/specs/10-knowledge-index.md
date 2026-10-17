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

## 唯一检索源（#257，2026-10-17）
**Genie 只读一份索引：VPS 上发布的 SQLite（`/opt/linker-genie/index/current/index.sqlite`），由服务进程内的 `linker/search-knowledge` 工具（`services/genie/src/linker_genie/knowledge.py` → `retrieval.py`）检索。** 共享主机 MariaDB 里的 `wp_genie_*` 表与读它的 WordPress ability（`SearchKnowledge` / `KnowledgeIndex` / `QueryEmbedding`）退役。

理由（全部为 2026-10-17 实测，证据见 #257 评论）：
1. **本地能验，线上不是第一次被看到**：本地实例是 Homebrew MySQL 9.6，没有 `VEC_DISTANCE_COSINE` / `VEC_FromText`（2026-10-11 已记录于 `docs/acceptance/2026-10-11/16i/`），MariaDB 的向量路径只能在生产上跑；SQLite + sqlite-vec 在 Mac 与 VPS 上是同一段代码、同一个文件。
2. **评测数字就是这段代码的**：bake-off 与 `just eval` 的召回、页码正确率都是对 `retrieval.py` 量的；PHP 那份是另写的一套（每个圈定范围各自退回关键词），没有评测覆盖。
3. **快**：一次检索 VPS 约 0.7–0.9 s（OpenRouter 编码中位 0.46 s、最大 0.83 s + sqlite-vec 240 ms 热、带商品圈定 150 ms）；经 WordPress 的同一检索 3.5 s（WP 启动 + 共享主机出网编码，MariaDB 查询本身 30–80 ms）。
4. **密钥少一处**：OpenRouter 密钥本就在 VPS 的 `/etc/linker-genie.env`；共享主机上为网页检索临时放的 `~/.config/terravolt-builder/openrouter.env` 与 `wp-config.php` 的 `HOME` 补丁不再需要。
5. AGENTS.md §4 早已写明"构建产物是随 Genie 发布到 VPS 的 SQLite 索引……服务读 `current/index.sqlite`"；本节把运行时对齐到这句。上文"A. API 向量胜出 → 索引搬到共享主机"的推断被以上 1–3 推翻。

**另一份的去留**（上线顺序，先证后删）：
1. `just cutover services --run` 发布本服务后，线上 Genie 的文档题按"验收"的评测集复跑，`turns.sqlite` 的工具调用记录里 `ranking=vector`、`encoder=google/gemini-embedding-2`；
2. 之后 `just cutover deploy` 发布插件，`linker/search-knowledge` ability 从 WordPress 消失（服务已不调用它）；
3. 业主同意后、先备份：删除 `wp_genie_chunks`、`wp_genie_documents`、`wp_genie_document_models`、`wp_genie_products`、`wp_genie_meta` 五张表，删除共享主机的 `~/.config/terravolt-builder/openrouter.env`，撤回 `wp-config.php` 的 `HOME` 补丁；读回确认。
`index.build --mariadb` 的离线导出保留为构建选项（AGENTS.md §4），不再部署。

## 失败显式（#257）
- 有查询编码器（`gemini-embedding-2` 的索引 + OpenRouter 密钥）时只走向量：编码失败（超时、连接错误、429/5xx 在 2 次尝试后，其余 HTTP 错误与坏响应立即）抛 `EmbeddingError`，`knowledge.py` 记 `document search failed` 后上抛，这一轮进 `cycle` 的兜底，失败写进轮次日志的 `failures`。**不退回关键词。** 查询超时 10 s/次、2 次、间隔 0.5 s，最坏 20.5 s；失败的一轮检索两次（`cycle` 重答一次）共 41 s，在壳代理 60 s 内。依据：OpenRouter 编码 VPS 中位 0.46 s、最大 0.83 s，Mac 中位 3.8 s、最大 5.35 s（各 12 次，2026-10-17）。
- 主机上根本没有该模型的查询编码器（无密钥；或关键词索引）时，BM25 排序，每次检索记一条 `WARNING document search by BM25: no query encoder for …`（AGENTS.md §4 的回退）。
- 索引读不了（文件缺失、损坏）抛 `KnowledgeUnavailable`，同样进兜底并记日志。
- 每次检索记 `document search ranking=… encoder=… index=… hits=…`，轮次日志的工具调用也带 `ranking`、`encoder`、`index_version`：线上"确实走了 gemini-embedding-2"以此为证。

## 运行时约束（业主 2026-10-09：不升级任何主机）
VPS 为 1 vCPU、3.9 GB、无 GPU。查询时的向量编码只能是：① 在 1 核上实时可跑的文本模型（int8 后约 300M 参数以内，如 multilingual-e5-base；BGE-M3 int8 以实测延迟 ≤1.5 s 为准），或 ② API（aihubmix 的 gemini-embedding-2 等，由 bake-off 决定）。自托管重排器在 1 核上不可行：重排只用 API 或不做。内存预算：引擎 + Genie 服务 + 索引 + 模型合计 ≤ 3 GB，索引以 SQLite 文件按需读取。多模态页面向量：图像侧只在 Mac 离线构建；查询侧要么走 API，要么文本塔满足 ① 的约束。

## 检索（`services/genie/retrieval.py`）
`search_documents(query, lang, product_ids=None, doc_types=None, k=8)`：先按 product_ids 对应的型号标签圈定文档（无则全库，圈定无果亦回全库）；FTS5 与向量各取 top-30，RRF 融合；可选重排（bge-reranker，CPU）；返回 `[{chunk_id, doc_url, page, section, text, score}]`。向量不可用时退回纯 FTS。
> 2026-10-10 bake-off 实测修订（`embedding-bakeoff.md` §2）：本语料上等权 RRF 融合比向量单路低 11.6pp 召回@5、加权 2:1/3:1 更差，出厂检索改为**向量独立成序**，BM25 降为本机没有该索引模型查询编码器时的回退；按商品圈定、圈定空回全库的行为不变。
> 2026-10-17 修订（#257，Knocket 对照题集实测）：
> - **型号圈定**：调用方没给 `product_ids` 时，问题里的型号代码（字母与数字同在一个词：L260、H2-10K-T3、CB2-100.3-HV5）对 `document_models` 的型号做前缀匹配（去标点、小写；型号整体或其中一个词），先在这些文档里检索，无果回全库。调用方给了 `product_ids` 时以它为准。
> - **碎片不算命中**：少于三个词的非表格块（图标被读成文字的 "SAND"、"SAFI"、孤立的步骤号）不进结果；索引 20261016T072222Z 有 2,266 / 33,172 块属此类，曾占试题前 8 个命中里的最多 4 个。
> - **同页邻块**：表格按行切块、表头重复，同一页的答案行可能排在截断线下（GoodWe 保修表 2026 行德语题排第 12）；命中所在页的其他段落随之返回，**4 页以内的数据手册整份随之返回**（概览页之后是参数表；88 份数据手册里 79 份 ≤4 页）；总数上限 16（2×k）。
> - 数据问题（不在检索里修，记在 #257）：商品 2003 的文档里挂了 44 页的 Pylontech 产品组合手册，标题写明只有 PDF 第 20–21 页属于 L260-OMNI；`document_models` 没有页范围，圈定会带进整本手册的其他产品。

## 引用与核验（供 #13）
模型只能引用 `chunk_id`；答案里文档的数字只能是被引块的数字。实现（#257）：
- 工具把每块文本里的数字标成 `[nK=值]`（`figures.tag`：表格单元格、带单位的数、日期各为一个；型号代码整体不标；表格行的标签格写着单位时，无单位的数带上它，如 `Nominal Capacity (kWh) | 260` → `260 kWh`）。模型写 `{fact:块ID.nK}`，水合填入文档原样的值；德语回答里词单位与日期本地化（`10 years` → `10 Jahre`，`1 st January 2026` → `1. Januar 2026`）。模型读到的结果不含文档 URL 与数字表。
- 核验：模型文本不许有裸数字（型号代码里的数字段除外，`CB2-100.3-HV5` 是名字）；文档数字的值必须出现在本轮块文本中。商品事实（`pID.FIELD`）来自商品数据，不拿块文本核。
- 来源：答案依据的块（`refs` 里的块 ID 与取了数字的块）由服务端在答案后面加成文档链接：这就是 #233 的文档块（`DocumentBlock`），显示为“标题 · p. N”/“标题 · S. N”，同一个文件只出一个链接、页码合并，点开 PDF 直接到所引页（`hydrate.cited_documents`）。模型已经自己加了文档块的块不再重复。链接标签的用词评审在 #233 的 `docs/acceptance/2026-10-17/233/copy-review.md`；文档数字的单位与日期写法见 `docs/acceptance/2026-10-17/257/copy-review.md`。

## 模型对比（bake-off，业主 2026-10-09 要求：用证据定模型，差距不大就用无成本的）
同一黄金集、同一分块、同一融合下比较：BM25 基线；开源文本 **snowflake-arctic-embed-m-v2.0**（Apache-2.0，官方 int8 ONNX；德语检索分高于 bge-m3 且算力只有其 37%，见 `docs/research/2026-10-09/embedding-models.md`）；开源文本 multilingual-e5-small（MIT，轻量回退）；BGE-M3 作对照；付费 API `gemini-embedding-2` 文本（aihubmix，OpenAI 兼容 `/v1/embeddings`，3072 维）；`gemini-embedding-2` 多模态（aihubmix 的 Gemini 原生 `embedContent`，页面渲染为 PNG 做页面向量）。指标：召回@5、页码正确率、查询延迟、构建成本、索引体积；黄金集 ≥200 问且含 ≥30 个图类问题（接线图、尺寸图、图表）。决策规则：API 相对开源在召回@5 与页码正确率上的提升都 < 5 个百分点 → 用开源；否则用 API 并记录月成本；多模态只看图类子集的提升。密钥在 `~/.config/terravolt-builder/aihubmix.env`，永不进仓库。结果表：`docs/research/2026-10-09/embedding-bakeoff.md`。

## 文档问答评测（#257，`services/genie/eval/knowledge/`）
`questions.json`：Knocket 对照题集第 2、3、5、6、7、8、9、10、19 题，EN 与 DE 各一（18 轮）。`documents.py` 对本地实例逐题跑一轮 Genie，跟服务的路径一样：先过理解层（实例的 Store API 提供产品词，然后定路由、执行路由的调用），再由 deepseek-flash（官方 API）写回答，查询编码用经 OpenRouter 的 gemini-embedding-2，索引是指定的那一份。只有 Jev 的回答是钉死的：每个问题都当文档问题处理（`documents_specs`，置信度 1），所以路由会**在模型之前调用 `linker/search-knowledge`**，并圈定到问题里点名的产品。自动判：落地、非兜底、非转人工、至少链接一个检索块、正文命中期望。最终判分按 `docs/research/2026-10-17-knocket/TRIAL.md` §1 逐题读答案。Jev 是否把问题判为文档问题，由 #233 的评测衡量。

## 评测（`services/genie/index/eval/`）
黄金集：从旧仓库的事实卡（路径用 `git ls-tree` 查找）抽逐字引文生成 EN/DE 问答 ≥ 200 条；指标：召回@5、引用页码正确率；`just eval` 输出表格进 PR。

## 不做
不在 VPS 上解析或跑模型；不索引外部网页；不在 WordPress 里检索文档（#257）。

## 验收
- [ ] 全部 PDF 进索引，失败清单为空或逐条说明；索引大小与构建时间写入 PR。
- [ ] **(a) 检索不退步**：`just eval` 的黄金集（984 问）召回@5 与引用页码正确率不得低于记录在案的基线。基线：vectors, by product 54.9% / 82.6%（540/984、419/507）；vectors, whole library 55.0% / 83.7%（541/984、422/504）。来源：索引 20261016T072222Z，#257 的 `docs/acceptance/2026-10-17/257/golden-eval.md`。数值写在 `services/genie/index/eval/run.py` 的 `BASELINE`；`just eval` 低于基线退出 1，并打印差了多少，不低于则退出 0。某个版本做得更好时提高基线，降低基线需要裁定。
- [ ] **(b) 回答层 0 个答错**：`services/genie/eval/knowledge/` 的文档评测集，以及 `docs/specs/13-genie.md`「目标」里的 20 题对照集，按 `docs/research/2026-10-17-knocket/TRIAL.md` §1 判分，0 个答错。
- 原来的"召回@5 ≥ 90%、引用页码正确率 ≥ 95%，低于阈值不合并"于 2026-10-17（#257 评审）删除。理由：这两个数没有来源（不是业主裁定，没有行业证据，也不是 Woo 原生能力，AGENTS.md §6），而且结构上达不到：2026-10-11 的验收（`docs/acceptance/2026-10-11/16i/`）记录过一阶段排序到不了 90%@5，此后任何版本也都没有达到。是否答对由 (b) 在回答层直接衡量。
- [ ] 发布与回滚各演练一次（本地 VPS 模拟目录即可，真 VPS 在 #13）。
