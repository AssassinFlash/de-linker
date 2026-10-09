# Advisor 知识库审计 + 文档 RAG 目标方案

- 日期：2026-10-09。只读任务：未改仓库文件，未写任何站点。
- 代码基线：`refs/landed/chain-tip` = `f007a9dd`（2026-10-09 13:18 +0800），Advisor 插件 `0.13.474`。下文所有 `path:line` 都指链尖版本（`git show refs/landed/chain-tip:<path>`）。
- 线上只读证据：2026-10-09 约 05:27 UTC，用 `rest-de.json` 凭据对 `GET /wp-json/linker-ai/v1/admin/status` 做了一次认证读取（GET，无写入）。
- 外部研究：Apify `apify/rag-web-browser`（REST 调用，令牌从 `~/.config/terravolt-builder/apify.env` 进程环境读取，未打印、未落盘），抓取时间 2026-10-09 05:29–05:42 UTC。来源清单见文末。

---

## 0. 一页结论

1. **今天的"知识库"不包含任何 PDF 正文。** `knowledge-index.json` 有 901 条记录：540 条站点页面分段（60%），148 条产品 FAQ，213 条"文档"记录。文档记录只有身份信息，长度 45–539 字符（形如"品牌. 标题. 简称."）。站点托管 383 份唯一 PDF，共 1.98 GB，估计约 1 万页，没有一页的文字在问答时能被检索到。问答时能用到的文档事实只有两类：一是预先抽取进 registry 的 5,739 个带 doc+page 的参数值，二是 74 条人工审核过的 FAQ。
2. **生产当前只做词法检索。** 线上 `admin/status` 显示 `generation_match=false`：当前包的 generation 是 `emb2-e920dd…`，生效中的向量是 `emb2-c5409df…`。按 `active_embeddings()` 的规则，此时向量整体作废，语义检索对所有任务都关闭；最近一次请求的 `retrieval_modes` 为 `[exact, lexical]`。原因是 knowledge-index 在 2026-10-09 04:55 +0800（`6d1ebbd6`）重建后没有重嵌。这是"全有或全无"的 generation 设计的固有后果。
3. **证据路径上的大部分内容是人工或 AI 制品，不是一手来源。** 主要有六类：
   - FAQ 是 LLM（grok 4.5 high）写的商品文案，被收割回仓库，Advisor 引用时指向自家商品页 `#faq`；FAQ 自带的 `support_refs` 运行时从不读取。
   - 参数值由 56-agent 工作流从 PDF 抽取，对抗校验只覆盖约 61%。
   - 兼容合同 228 格的 EN/DE 约束句是人工手写。
   - system prompt 里有一段 AI 写的物理"概念基础"，它的出处札记自己承认没有取得外部文献。
   - 检索靠手调的停用词、同义词、权重和阈值。
   - 质量最高的事实卡（逐字引文加物理页码，5.48 MB）被宣布为权威（ADR-0030），但没有任何运行时代码读取它。
4. **推荐目标**：
   - 来源：以我们自己托管、按 sha256 固定的 PDF 为文档正文来源。
   - 构建：在 Mac 上离线用 Docling（MIT）解析，HybridChunker 切块（表格整块保留并重复表头，每块带页码）。每块前加确定性上下文头（品牌、型号、文档、章节、页）。用多语言 embedding 编码（首选 Voyage `voyage-4`，或开源 BGE-M3）。
   - 存储：写成一个 SQLite 文件（FTS5 BM25 + trigram，加 sqlite-vec），沿用引擎的版本化发布和回滚上 VPS。
   - 检索：服务端先按商品或型号圈定文档，再做 BM25+向量的 RRF 融合，可选 rerank。
   - 引用：模型只输出 chunk_id，服务端渲染"文档 · 版次 · 第 N 页"并链接 `url#page=N`，同时做"数字必须出现在被引块中"的确定性核验。
   - 评测：用事实卡的逐字引文构造黄金集。
   - 最强三条理由见 §C.4。

---

## Part A — Advisor 的"知识库"现状

### A1. 清单

#### A1.1 `knowledge/`（35 个文件，13.28 MB）

| 路径 | 大小 | 内容 | 性质 | 运行时读者 |
|---|---|---|---|---|
| `knowledge/components-db/{goodwe,saj,pylontech,ecoflow,mbs,chint}.json` | 1.35 MB | 57 个 family；5,824 个带 `doc`+`page` 的参数值 | **AI 抽取**：README:5-10 写明由 workflow `wf_92802a03-020`（56 agents）抽取并对抗校验。各文件 `verify_checked_values` 合计 3,529 / 5,824（约 61%）；11 个 family 为 `verified:false`。`goodwe.json` 的 `source` 自述"a source reference is not a whole-product verification verdict" | 设计引擎直接读（`services/design-engine/linker_engine/components.py`、`design.py:468`）；经 `scripts/materials/build_registry.py` 进入 material registry，再进 Advisor |
| `knowledge/fact-cards/{goodwe,saj,ecoflow,pylontech}.md` + `README.md` | 5.48 MB | Model 卡 121、Article 卡 106；文档登记 251 份；每行事实带"文档 ID + 物理页 + 逐字引文" | 会话（AI）逐页阅读后手写 | **无**。ADR-0030 原文："No builder or deploy script reads the directory"。各 store 存的是这些值的手抄副本 |
| `knowledge/materials/manual-decisions.json` | 549 KB | 10 条 decisions（附 `why_it_maps_to_linker` 理由文字）、253 条 material_overrides、32 条 manual_materials、44 条 research_records（43 条带 `summary` 文字）、68 条 woo_bindings | 手写与 AI 写混合 | registry 构建器（运行时不直接读） |
| `knowledge/product-faqs.json` | 94 KB | 74 行 EN+DE FAQ，覆盖 37 个产品；`source_refs` 共 161 个 PDF 页引用、24 个 `repo:` 引文 | 从商品页收割回仓库的 LLM 文案，加上开发者的审核记录 | 构建器生成 knowledge-index；ADR-0033 之后运行时不再读它 |
| `knowledge/claim-phrases.json` | 63 KB | 498 个规格键的 EN/DE 标签、113 个单位、10 条 ruling 句（`rulings` 在 :2730） | 手写 | 投影为 `plugins/linker-ai-assistant/data/spec-labels.json`，validator 读（`class-linker-ai-answer-validator.php:2771-2780`） |
| `knowledge/claims.json` | 5.22 MB | 6,782 条 claim：5,764 spec、934 compatibility、74 faq、10 ruling | 生成的投影（`tools/build_claims.py`） | **无运行时读者**，只有 `build_claims.py` 和 `rebuild_projections.py` 引用 |
| `knowledge/evidence-manifest.json` | 191 KB | 257 条证据文件（sha256、`hosted_url`；115 条有页数；15 条证书带注册号） | 生成加人工 | 构建器、校验器 |
| `knowledge/document-host-map.json` | 125 KB | 417 个托管 PDF URL，其中 383 个唯一 sha256，34 个字节相同的副本，共 1.98 GB | 托管库存（ADR-0023） | 构建器、校验器 |
| `knowledge/raw-docs/{MANIFEST.md,_index.json,README.md}` | 25 KB | 早期 22 份原始 PDF 的索引；PDF 本体在仓库外档案 | 生成 | 无 |
| `knowledge/current-state.md` | 42 KB | 旧项目状态叙述（:46 记录"Worker model for catalog copy: grok 4.5 high"） | 手写 | 无 |
| `knowledge/product-model-map.md` | 26 KB | 型号映射（自称"唯一真值源"，ADR-0030 已让位于事实卡） | 手写 | 无 |
| 其余：`lod2-*.json`、`image-host-map.json`、`page-inventory.md`、`i18n-render-qa.md`、`seo/*.generated.php`、`terravolt/*.md`、`code-references/watte/*`、`materials/ecoflow-owner-confirmations-2026-09-27.md` | 约 0.2 MB | LoD2 屋顶、图片、SEO、旧字段矩阵、业主确认 | 混合 | 与 Advisor 检索无关 |

#### A1.2 `contracts/`（31 个文件，0.49 MB）

| 路径 | 大小 | 内容 | 运行时读者 |
|---|---|---|---|
| `contracts/compatibility-lists.json` | 209 KB | 37 份兼容文件（SAJ 15、GoodWe 12、EcoFlow 6、Pylontech 4，全为 `first_party`）；25 个逆变器 family × 16 个电池 family；228 格（190 `not_listed`、31 `listed`、7 `one_way`）。**每格都有手写 EN+DE `constraint`，66 格有手写 `warranty`/`warranty_de`**；页码只出现在句子里（如"(p. 1)"），没有结构化页码字段 | b2b-core `includes/material-compatibility.php:64`；Advisor 兼容链路（`class-linker-ai-compatibility.php:542-557` 把约束句原样带入答案） |
| `contracts/delinker-truth.json` | 23 KB | 定位、品牌、禁用词、禁用 SKU | Advisor `class-linker-ai-products.php:2599`（`banned_brands`）；b2b-core `legacy-redirects.php` |
| 其余 29 个 `.md/.json`（design-*、livecanvas-*、page-*、section-pattern-library、site-architecture-lock、brand-voice、copywriting 等） | 约 0.26 MB | 设计与文案契约 | 与 Advisor 知识无关 |

#### A1.3 `plugins/linker-ai-assistant/data/`（5 个文件，3.01 MB）

| 文件 | 大小 | 内容 |
|---|---|---|
| `knowledge-index.json` | 1.35 MB | 检索语料（见 A1.4） |
| `components-db.json` | 1.62 MB | 组件目录投影，只服务 `linker/v1/components`（advisor-rebuild 005 盘点） |
| `spec-labels.json` | 44 KB | `claim-phrases.json` 的投影 |
| `tool-frame-copy.json`、`engine-ca.pem` | 小 | UI 文案、引擎证书固定 |

#### A1.4 `knowledge-index.json` 的结构

- 顶层：`schema_version=1`，`source=production`，`site_origin=https://de-linker.com`。`generated_from` 有 7 项：生产 wp/v2 页面、wp/v2 product 链接、`contracts/compatibility-lists.json`、`knowledge/product-faqs.json`、`plugins/terravolt-b2b-core/data/material-registry.json`、`knowledge/evidence-manifest.json`、`knowledge/document-host-map.json`。`source_manifest` 有 23 个页面面，`bundle_sha256=87befbde…`，与线上 `current_bundle_sha256` 一致，说明链尖这份已部署。

| kind | 语言 | 条数 | content 长度（最小/中位/最大） |
|---|---|---|---|
| `site_page` | en / de | 261 / 279 | 18 / 406 / 3,500 |
| `product_faq` | en / de | 74 / 74 | 170 / 353 / 1,047 |
| `material_document` | en | 149 | 54 / 93 / 333 |
| `specification_source` | en | 27 | 77 / 183 / 539 |
| `compatibility_document` | en | 37 | 45 / 81 / 122 |
| **合计** | | **901** | 全部 `status=published` |

- **构建方式**：`scripts/build_linker_ai_knowledge.py`，由 `tools/rebuild_projections.py` 的 `knowledge` stage 调用（`STAGE_ORDER` 在 :77；`stage_knowledge` 在 :1445-1489）。该 stage 需要 `--live-knowledge`，先在临时文件里重建，若会让记录变少就拒绝写入。另有三个按范围重建的子 stage：FAQ-only、compatibility-only、material-only（:1491-1647）。
- **切块方式**：页面按 h1–h3 切段。每段至少 80 字符、最多 3,500 字符，每页最多 40 段（`build_linker_ai_knowledge.py:295-306`）；页面 overview 截到 1,800 字符（:362、:461）。
- **文档记录只有身份信息**：兼容文件的 content 是 `f"{doc['brand']}. {doc['title']}. {doc['short']}."`（:854）；material 文档的 content 是"厂商. 类型 for 型号表. 标题"（:1233-1237）。
- **内置检索基准只有 4 个 case**（`RETRIEVAL_BENCHMARK_CASES`，:129-158）。
- **Embedding**：
  - 供应商是 NVIDIA 托管 NIM，地址 `https://integrate.api.nvidia.com/v1/embeddings`（`class-linker-ai-model.php:1742`）。
  - 模型默认 `nvidia/llama-nemotron-embed-vl-1b-v2`（`class-linker-ai-settings.php:94,176`）。2026-08-25 前一个模型 `llama-nemotron-embed-1b-v2` 返回 410 Gone 后改为这个（:155-168）。
  - 请求参数：`dimensions: 384`、`truncate: END`、`encoding_format: float`。`input_type` 按条数决定：1 条为 `query`，多于 1 条为 `passage`（:1730-1740）。
  - 编码的文本是 title + aliases + content 前 6,000 字符（`class-linker-ai-knowledge.php:902-909`）。
- **向量存储**：放在 WordPress options 里，`linker_ai_embeddings_active_v2` / `_staging_v2` / 旧 `linker_ai_embeddings_v1`，`autoload=false`（`class-linker-ai-knowledge.php:9-12, 1229, 1306, 1368`）。重建由管理员调用 `POST /linker-ai/v1/admin/reindex`，每批不超过 16 条（:1188-1192）。
- **Generation**：对全部打包记录的 (id, title, aliases, content) 加模型、维度和 id 集合做 sha256（:917-997）。只有整代都匹配时才提供向量（`payload_matches_bundle`，:1021-1031）；查询时在 PHP 里对全部记录逐条算余弦（:438-449）。
- **线上读数（05:27 UTC）**：`knowledge_records=1297`（打包的非 FAQ 记录 753 条 + 线上实时读取的 FAQ 约 544 条）；`embedded_records=901`；`generation_match=false`；旧 v1 option 仍存 197 个向量；`last_request.retrieval_modes=[exact, lexical]`。

### A2. 检索是怎么做的

1. **运行时语料** = 打包记录中的非 FAQ 部分 + 从已发布商品实时读取的 FAQ（EN 来自 `_tv_legacy_acf_json`，DE 来自 `_linker_de_acf_json`）（`class-linker-ai-knowledge.php:40-61, 94-162`）。
   - FAQ 存在 transient `linker_ai_product_faq_records` 里，保留 1 天或直到商品被保存（:143；入口文件挂了 `save_post_product` 钩子）。
   - 与打包版逐字相同的 FAQ 沿用旧向量；改过的 FAQ 的 id 会加 `~hash` 后缀，没有向量，只能靠词法命中（ADR-0033 明写此代价）。
2. **分词**（`tokens()`，:180-236）：
   - 先转小写，再用正则切词。
   - 停用词表 EN+DE（:18-28），其中多条是线上探针暴露问题后补上的。
   - 手写同义词（:187-196），例如 `moq→mindestbestellmenge`、`geschäftskonto→partnerkonto`、`erfahren→erfahrung`、`*zertifikat*→zertifikate`。
   - 型号码会额外生成前缀，如 `hs3-10k-t2-w-p→hs3`。
3. **词法分**（`lexical_score`，:408-436）：用子串匹配（`mb_strpos`），不是按词匹配，也不是 BM25（没有 IDF，没有长度归一化）。
   - 标题命中 +6；aliases、subject_ids、applicable_models 命中 +7；正文命中次数取 min(4,n)×1.25；相邻词对命中 +5；上下文命中 +1.5。
4. **语义分**：只有任务的 `allow_vector` 为真、且向量可用时才计算（:649-662）。`allow_vector` 只对 `document_lookup`、`navigation_service`、`general` 开放（ADR-0012；`Linker_AI_Contracts::task_plan`）。
   - 公式：`score = lexical + max(0, cos-0.45)*18`；词法分 ≤0 且余弦 <0.56 的记录直接丢弃（:542-543）。阈值都是手调常数。
5. **过滤**：
   - 只要 `status=published` 的记录（:244-252）。
   - 语言：英文读者看不到德文记录；德文读者先找德文，一条都没命中时才回退到英文（:507-566）。
   - FAQ 和文档类记录要求与问题里的型号匹配（`record_applies_to_models`，:341-406）。
   - 每次最多返回 10 条。
6. **按任务类型路由**（`search_for_task`，:568-625；`Linker_AI_Contracts::AUTHORITY_MAP` 在 `class-linker-ai-contracts.php:73-106`）：
   - `product_lookup` 和 `project_direction`：只查 `product_faq`，只用词法。
   - `document_lookup`：查三类文档身份记录；结果少于 3 条或问题里有证书类词时，追加站点页面一层。证书类走一条专门的正则通道，在页面里扫"zertifikat/certificate…"再按词重叠排序（:676-760）。
   - `navigation_service` / `general`：查页面，`general` 也查 FAQ。
   - `compatibility_check`、`commercial_fact`、`project_*`、`order_document_help`、`spatial_help`：**不进语料**，走结构化权威（registry、兼容合同、Woo、Project）。
   - 法律身份等固定路由走 `site_page_evidence($path)`（:801-842）。
7. **记录变成证据、再变成引用**：
   - `Linker_AI_Authority_Resolver::knowledge_evidence()`（`class-linker-ai-authority-resolver.php:2503-2551`）把每条记录包装成 evidence：`source_id` = 记录 id，`scope.source_ids` = 记录的 `source_ids`。
   - validator 的 `citations()`（`class-linker-ai-answer-validator.php:1990-…`）生成引用卡：标题由 `citation_title` 决定（:1702-1760，含德文标题），附 URL、日期和版本；兼容文件追加"verified <date>"戳；同一 URL 只出一张卡。
   - 正文里的标记写成 `[[cite:N]]`；只有当证据 id 以 `:pNN` 结尾时，才写成 `[[cite:N:页]]`（`inline_citations`，:4268-4282）。
   - **所以页级引用只来自 registry/components-db 预抽取的参数值**，不来自检索到的文本。
   - FAQ 的引用指向自家商品页 `…/product/<slug>/#faq`（`source_ids=wordpress-product:<slug>`）。FAQ 的 `support_refs`（数据手册页）**在 `includes/` 下零引用**，不进证据，也不进引用卡。
   - `document_lookup` 返回的文件只作为链接（`resolve_document`，:3152-…）。README 也写明："Product documents are offered as links; they do not become compatibility evidence"。

### A3. 文档：托管了多少，正文是否可检索

| 口径 | 数字 |
|---|---|
| 托管库存（`document-host-map.json`） | 417 个 PDF URL，其中 383 个唯一（34 个字节相同的副本），1.98 GB；单文件中位 1.0 MB，最大 108 MB |
| 估计页数 | 约 1.07 万页。估算方法：evidence-manifest 中有页数的 115 份共 2,303 页，平均 184 KB/页，按总字节外推。只是量级估计 |
| 按文件名推断类型（唯一文件；粗略） | datasheet 约 122，manual/guide 约 111，证书/声明约 80，按名字能认出的兼容清单约 12（合同里实有 37 份，很多文件名形如 `S9.pdf`），保修约 10，宣传册约 7，未知约 41 |
| registry `documents[]` | 410 条，指向 149 个不同 URL（按条目计：datasheet 238、manual 154、warranty 15，另有 catalogue、technical_guide、document 各 1）；**410 条中 408 条没有语言字段** |
| 事实卡文档登记（逐份读过的子集，251 份） | 语言：仅 EN 154，仅 DE 29，EN/DE 或多语约 54，其他少量。类别：证书 51，datasheet 50，手册与安装指南约 58，声明 20，兼容清单 7，保修 7 |
| 兼容合同文件 | 37 份 |
| evidence-manifest | 257 条（其中 15 条证书带注册号） |

**正文是否被索引：没有。**
- knowledge-index 里 213 条文档记录只有身份信息（`build_linker_ai_knowledge.py:854, 1233-1237`）。
- 运行时没有任何 PDF 文本抽取。
- 仓库里唯一抽取 PDF 文本的代码是离线核对工具 `tools/datasheet_evidence.py`（`pdftotext -layout`，:184）。它的 `value_present()` 只查数字是否出现在整份文档里，不核对被引的那一页。
- "带页码的事实"只有 registry 里 5,765 个参数中的 5,739 个（来自 components-db），而且只覆盖当初抽取过的字段。
- 手册里的接线、间距、错误码、参数设置、电网规则参数等长尾内容，问答时完全不可达。

### A4. 异味：AI 写的知识被当作证据（file:line）

| # | 位置 | 问题 |
|---|---|---|
| S1 | `plugins/linker-ai-assistant/includes/class-linker-ai-model.php:854-901` | **CONCEPT FOUNDATIONS**：按关键词正则把四段物理"基础知识"（能量/功率、V·I、I-V/P-V 与 MPPT、混合逆变器与电池端口）注入 system prompt。:898 注明出处是 `.scratch/advisor-answer-upgrade/evidence/mppt-foundation-20260923.md`。该札记末段自述：Apify 请求触顶，"遮阴多峰和具体 MPPT 方法的外部直接文献仍未取得"，依据只是本机 pvlib/SciPy 源码加第一性原理推导。这是 AI 写、没有外部来源的知识，以指令形式无引用地进入答案 |
| S2 | `class-linker-ai-knowledge.php:94-162`；`knowledge/current-state.md:46`；`docs/audit/2026-08-28-knowledge-chain-audit.md:28,81`；`docs/audit/2026-09-01-catalog-data-audit.md:64` | **产品 FAQ 是 LLM 文案**（"Worker model for catalog copy: grok 4.5 high"），运行时实时读取全部已发布 FAQ。线上约 544 条 FAQ 记录中，带审核过的支撑的至多 148 条，即至少 73% 没有经过审核的支撑。即使是审核过的，也引用到自家 PDP `#faq`，`support_refs` 不被读取，属于自证循环。历史上已出现 TS4-M2 FAQ 用 Tigo 硬件作答，并带着德语孪生进入 AI 语料（09-01 审计；该行现已移除） |
| S3 | `knowledge/components-db/README.md:5-10`；各 brand JSON 的 `verified`/`verify_checked_values` 字段 | 参数值由 AI agent 工作流抽取，对抗校验覆盖约 61%（3,529/5,824），11 个 family 为 `verified:false`。这是 Advisor 唯一带页码的规格证据；`tools/datasheet_evidence.py` 只做整份文档的数字存在性检查 |
| S4 | `contracts/compatibility-lists.json` cells（全部 228 格的 `constraint`/`constraint_de`，66 格的 `warranty`/`warranty_de`）；`class-linker-ai-compatibility.php:542-557` | 手写的 EN/DE 解释句原样进入答案。引用到文档级（`docs:["P1","G1"]`），页码只在句子里。构建器在 `build_linker_ai_knowledge.py:851-853` 刻意不让合同 notes 进入检索，但 cell 句子走兼容权威链路照样到达客户 |
| S5 | `knowledge/materials/manual-decisions.json:17,30,44,65,77,88,99`（`why_it_maps_to_linker`）；`research_records[*].summary`（43 条） | AI 写的理由和文档摘要。例如 `quote_validity_default`（14 天）只有竞品页面支撑（`memodo_faq_2026_07_28`、`segen_portal_2026_07_28`）。对应的 `plugins/terravolt-b2b-core/data/operating-policies.json` 里 `quote_validity` 是 `public:false, legal_review_required:true`，已被门控，这是正确做法；但理由文字仍是 AI 推理 |
| S6 | `knowledge/claim-phrases.json:3`（`spec_labels`，498 条）、`:2730`（`rulings`，10 条）；`knowledge/claims.json` | 手写的标签和 ruling 句；`claims.json` 有 5.2 MB、6,782 条 claim，没有运行时读者，属于"知识地基"的半成品投影 |
| S7 | `docs/adr/0030-fact-cards-are-the-product-authority.md`（Decision · Home）；`knowledge/fact-cards/*.md` | 质量最高的证据格式（物理页码加逐字引文、冲突表、R4 规则）被宣布为"权威"，但没有代码读它；store 存的是"手抄副本"，漂移只能靠逐品牌的人工比对票发现（ADR-0030 Consequences 自述） |
| S8 | `class-linker-ai-knowledge.php:18-28, 187-196, 408-436, 542-543, 676-760`；`class-linker-ai-answer-validator.php`（11,446 行） | 检索质量靠手调的停用词、同义词、权重、阈值和证书正则通道来补；评测只有 4 个 case。每次线上探针失败就加一条规则，这是补丁累积 |
| S9 | `class-linker-ai-knowledge.php:917-997, 1021-1031`；`class-linker-ai-settings.php:155-177`；`class-linker-ai-model.php:1730-1742` | 运维异味：①generation 全有或全无，任何一个字的内容变化都会让全站静默退回纯词法，直到有人手动 reindex（线上此刻正是这样）；②生产依赖 NVIDIA 免费托管端点，NVIDIA 自己把它定位为原型和测试用途，且已出过一次 410 改名；③模型卡记载输出 2048 维，请求的 384 维依赖 API 端截断，模型卡未说明；④`input_type` 由批大小决定，若最后一批只有 1 条会被编成 `query`；⑤向量存在 wp_options，旧 v1 的 197 个向量仍在 |
| S10 | `build_linker_ai_knowledge.py:854, 1233-1237` | 213 条"文档记录"只是身份信息，"文档检索"实际上是检索文件名和标题 |
| S11 | knowledge-index 的 kind 分布 | 60% 是营销和站点页面分段（540/901）。它们是 Linker 文案，不是工程证据，却与 FAQ、文档身份记录在同一个池子里竞争 6 个名额 |

### A5. 判定：真源与制品

| 真正的一手来源（应当成为检索对象） | 人工或 AI 制品（今天在证据路径上） |
|---|---|
| 383 份我们托管、按 sha256 固定的 PDF（datasheet、手册、证书、兼容清单） | LLM 写的产品 FAQ（运行时实时读取，引用自家 PDP） |
| Woo 商品当前状态（ADR-0032/0033 的商品自持数值、价格、库存） | AI 抽取的 components-db 参数值，再经 registry 进入（有页码，校验约 61%） |
| 已发布页面（作为 Linker 自己的陈述） | 兼容合同 228 格手写 EN/DE 约束句和保修句 |
| 业主带日期的裁定（rulings） | system prompt 里的"概念基础"物理段落（没有外部来源） |
| — | manual-decisions 的 AI 理由和摘要；claim-phrases 的手写 ruling 句 |
| — | 事实卡（AI 会话手写，但格式是逐字引文加页码，最接近真源，却没有运行时读者） |
| — | `claims.json`（无人读取的投影）；knowledge-index（60% 页面分段，文档部分只是身份信息） |

---

## Part B — 外部研究（Apify，2026-10-09）

### B1. PDF 解析

| 工具 | 许可 | 纯 CPU | 表格 | 页级出处 | 备注 |
|---|---|---|---|---|---|
| **Docling** | 代码 MIT。README："The Docling codebase is under MIT license. For individual model usage, please refer to the model licenses"。HF `docling-project/docling-models`（版面模型加 TableFormer）标注 CDLA-Permissive-2.0 和 Apache-2.0 | 可以。技术报告实测 4 线程：0.60–2.18 页/秒，峰值内存 2.4–6.2 GB（2024 年数据，arXiv 2408.09869） | TableFormer 恢复表格结构；`HybridChunker` 的 `repeat_table_header` 默认开启 | DoclingDocument 带 provenance（页、坐标） | 68.6k stars，LF AI & Data 项目；有 `docling-serve`（MIT）REST 封装 |
| **marker** | 代码 Apache-2.0；权重采用"modified AI Pubs Open Rail-M"，研究、个人使用以及融资或营收低于 500 万美元的初创免费，超出需付费 | 可以：`fast` 模式为 CPU 优化，surya VLM 通过 llama.cpp 运行 | 优先从文本层重建表格，置信度低时回落到 VLM | `--paginate_output`，输出 JSON/chunks | 40.3k stars；olmocr-bench 76.0% 是厂商自报 |
| **pymupdf4llm** | **AGPL-3.0**（商用许可需向 Artifex 购买） | 可以："No GPU, no cloud" | 检测表格，输出 Markdown 或 HTML | `page_chunks=True` 时每页带元数据 | 2.2k stars；最轻；OCR 只在需要的区域做 |
| **unstructured** | Apache-2.0 | 可以（PDF 需要 tesseract 和 poppler） | 厂商自述付费的 Transform API 表格准确率是开源版的 2 倍 | 元素级元数据 | README 写明默认开启遥测；15.6k stars |

结论：首选 Docling，因为许可干净、有表格结构、有页级出处、有现成切块器。它很重，在 1 vCPU / 3.9 GB 的 VPS 上跑不合适，应在 Mac 上离线构建。pymupdf4llm 必须先拿到商用许可才能用。marker 的权重许可要看公司营收，不宜默认采用。

### B2. 切块（数据手册表格）

- 按文档结构切：表格整块保留，跨块时重复表头（Docling `HybridChunker` 的 `repeat_table_header=True`；`merge_peers` 会合并同标题下的小块）。每块带页码区间和所在标题路径。
- 块长：arXiv 2605.27444（2026-05，技术文档 RAG 系统评测）结论是"the use of the reranker is strongly beneficial … preference for passages up to 512 tokens"，并且 BM25 在各指标上表现最稳定。
- 上下文前缀：Anthropic 的"Contextual Retrieval"测得，给块加上下文后做 embedding，top-20 召回失败率下降 35%；embedding 和 BM25 都加上下文后下降 49%；再加 rerank 下降 67%（5.7%→1.9%）。数据手册的上下文可以确定性生成：品牌、型号表、文档标题和版次、章节、页码。不需要调用 LLM。
- 同一篇文章指出，知识库小于 20 万 token（约 500 页）时可以整体放进 prompt。本语料约 1 万页，按 Claude 的 PDF 计价口径每页 1,500–3,000 token（Claude PDF 文档），不适用整体放入；但按单个商品圈定后，一份 2–4 页的数据手册可以整份放进上下文。

### B3. 混合检索与重排

- 标准做法：BM25 加向量检索，再用 RRF 融合。LanceDB 文档说明默认 `k=60`，"Experiments indicate that k = 60 was near-optimal, but that the choice is not critical"。
- SQLite FTS5 自带 `bm25()`。`trigram` 分词器支持子串匹配，适合型号码（GW10K-ET）和德语复合词。用 FTS5 加 sqlite-vec 在纯 SQL 里实现 RRF 的写法见 Alex Garcia 的博客。
- 重排选项：
  - Voyage `rerank-3` / `rerank-3-lite`：32k 上下文，多语，$0.05 / $0.02 每百万 token，每账户前 2 亿 token 免费。
  - 自托管 `bge-reranker-v2-m3`（Apache-2.0）或 `Qwen3-Reranker-0.6B`（Apache-2.0）：在 1 vCPU 上偏重。
  - `jina-reranker-v2-base-multilingual` 是 CC-BY-NC 4.0，商用不可。

### B4. 适合 1 vCPU VPS 的存储

| 方案 | 许可 | 运维 | 混合检索 | 评价 |
|---|---|---|---|---|
| SQLite + FTS5 + **sqlite-vec** | MIT 与 Apache-2.0 双许可 | 单文件，没有服务进程 | FTS5 的 bm25 加 vec0 KNN（支持 metadata 和 partition 列；float/int8/binary 向量） | README："pre-v1, so expect breaking changes"，需锁版本。规模在 1 万到 10 万块时暴力 KNN 足够 |
| **LanceDB** | Apache-2.0 | 嵌入式库，依赖 Arrow/Rust | 向量 + 全文 + SQL，内置 RRF reranker | 开箱即用的混合检索；依赖较重 |
| **pgvector** | PostgreSQL License | 需要常驻 Postgres | 默认精确检索，另有 HNSW/IVFFlat；全文检索靠 Postgres 自身 | 在 1 vCPU 上多一个常驻服务，对本规模没必要 |
| **Chroma** | Apache-2.0 | 嵌入式或服务式 | 开源版的全文检索只有 `$contains`/`$regex` 过滤（区分大小写），没有 BM25 排序；"hybrid, and full-text search"主推 Chroma Cloud | 不适合本需求 |

### B5. Embedding 供应商（与 DeepSeek / Anthropic 并用）

- DeepSeek 没有 embedding 模型：价格页只列 `deepseek-flash` 和 `deepseek-v4-pro`。
- Anthropic 没有 embedding 模型：官方文档原句 "Anthropic does not offer its own embedding model"，并以 Voyage 为示例。

| 供应商/模型 | 许可或条款 | 多语 | 维度 | 价格 | 备注 |
|---|---|---|---|---|---|
| **Voyage `voyage-4` / `-lite` / `-large`** | 商用 API | 支持（"general-purpose and multilingual"） | 256/512/1024/2048；可返回 int8 或 binary | $0.06 / $0.02 / $0.12 每百万 token；每账户前 2 亿 token 免费 | 4 系列共享同一嵌入空间，包括开源的 `voyage-4-nano`（Apache-2.0，约 3.4 亿参数），可本地兜底而不必重建索引 |
| OpenAI `text-embedding-3-small` / `-large` | 商用 API | 支持 | 1536 / 3072，可缩短 | 约 $0.02 / $0.13 每百万（按"62,500 / 9,615 页每美元、每页 800 token"折算） | MTEB 62.3 / 64.6 |
| Cohere `embed-v4.0` | 商用 API | 支持 | 256–1536 | — | 支持文本和图像（PDF），128k 上下文 |
| NVIDIA `llama-nemotron-embed-vl-1b-v2`（现用） | 权重用 NVIDIA Open Model License，"ready for commercial use"（指自托管，需 GPU） | 支持 | 卡上写输出最多 2048 维 | 托管端点"free … for unlimited prototyping … for development and testing"；上生产需购买 NVIDIA AI Enterprise | 1.7B 参数的视觉语言模型；我们只用了它的文本能力 |
| **BGE-M3** | MIT | 支持，100+ 语言 | 1024 | 自托管 | 5.68 亿参数，8k 上下文，同时输出 dense、sparse、colbert；MIRACL 德语 nDCG@10 为 57.59 |
| Qwen3-Embedding-0.6B / 4B | Apache-2.0 | 支持 | 32–1024 / 最高 2560 | 自托管 | MIRACL 德语 54.21 / 62.98 |
| multilingual-e5-large-instruct | MIT | 支持 | 1024 | 自托管 | MIRACL 德语 43.37（在 MMTEB 总分上领先 BGE-M3，在德语检索上落后） |
| jina-embeddings-v3 / v5 | 权重 CC BY-NC 4.0（商用需另购许可；通过 API 使用另算） | 支持 | MRL | — | 自托管商用受限 |

- EN/DE 结论：已读的 251 份文档里约 61% 只有英文，德文问题却占一半。这意味着检索必须能跨语言。BM25 只能靠型号码跨语言，其余要靠多语 embedding。
- 德语数据来源：WZ-IT 2026-09-16 的博客，数字来自各模型卡的 MIRACL-de。属二手来源，只用来缩小候选范围；作者自己也强调"The decision is made by a test set of real questions … from your own collection"。

### B6. 评测

- RAGAS（Apache-2.0，仓库现为 `vibrantlabsai/ragas`）提供 Context Precision/Recall、Faithfulness、Response Relevancy、Factual Correctness 等 LLM 评分指标，也有 Exact Match、String Presence 等非 LLM 指标。
- 更简单、更硬的做法是黄金集：用"问题 → 期望的文档和页码"衡量 recall@k 和 MRR，再加"被引块里确实出现了答案中的数值"这一确定性检查。本项目的事实卡天然提供"型号、字段、值、文档 ID、物理页、逐字引文"，可以直接生成 EN 和 DE 问题。
- arXiv 2605.27444 使用 60 组问答加 reranker 作为代理真值，并提醒样本小的局限。这说明小黄金集可行，但要把结论当作参考而非定论。

### B7. 引用机制（与 advisor-rebuild 006 的冲突）

- Anthropic Citations：PDF 返回 `page_location`（页码从 1 起），`cited_text` 不计输出 token；也支持预切块的"custom content"文档和 `search_result` 块。**但"Citations cannot be used together with structured outputs"。**
- `.scratch/advisor-rebuild/work/006-target-architecture.md:34` 写的是"Anthropic 作可切换供应商（strict + `search_result` 引用块）"，与官方文档矛盾。DeepSeek 没有引用功能。
- 结论：沿用 006 的 strict 输出，`refs` 只引用本轮工具返回的 chunk_id，由服务端渲染页级引用。这种做法与供应商无关，也与 006 的"Rufus hydration"思路一致。

---

## Part C — 推荐目标：来源 → 构建 → 存储 → 检索 → 引用 → 评测

### C.1 来源
1. **文档正文**：`knowledge/document-host-map.json` 中的 383 份唯一 PDF。只从我们自己的 URL 取字节，并校验 sha256，符合 ADR-0023。文档元数据（类别、品牌、型号、版次、日期、EN/DE 标题）来自 registry `documents[]`、兼容合同 `documents`、事实卡"Document register"和 chrome 标题映射。
2. **结构化权威不变**：规格值（ADR-0033 商品数值加 registry）、配对（兼容合同）、价格和库存（Woo）。它们仍通过 abilities 提供（006）。RAG 只补充文档段落，不覆盖结构化事实；两者冲突时记日志，按事实卡的冲突规则处理。
3. **Linker 自己的陈述**：FAQ（实时读取 Woo）和已发布页面单独成类，标注为"Linker FAQ / 页面"。有 `support_refs` 的 FAQ 同时给出数据手册页引用；没有的就不挂文档引用。

### C.2 构建（离线，在 Mac 上，按 020 的 uv/pyproject 工程）
1. 盘点：生成 docs 表，字段包括 sha256、url、class、brand、models、edition/date、lang（检测得出）、title_en/de。
2. 解析：Docling，只对没有文本层的页面做 OCR，产出 DoclingDocument JSON，按 sha256 缓存，只重新解析变化的文件。
3. 切块：`HybridChunker`，分词器与所选 embedder 一致，每块不超过约 512 token，开启 `repeat_table_header`。每块记录 `chunk_id`（文档 sha、页码区间和文本的哈希）、`page_start/end`、标题路径、是否表格、语言、正文。
4. 上下文头（确定性生成）：`{brand} {models} · {doc title} ({edition}) · {section} · p.{page}`，同时写入 BM25 文本和 embedding 文本。
5. Embedding：首选 `voyage-4`，`input_type=document`，512 或 1024 维，int8。语料约 500 万–1000 万 token，按标价不到 1 美元，且落在 2 亿免费额度内。如果坚持不用外部 API，就在 Mac 上用 BGE-M3（MIT）离线编码；但查询向量必须由同一模型生成，1 vCPU 上做查询编码会比较吃力。
6. 写入一个 SQLite 文件，包含：`docs`、`chunks`、`chunks_fts`（`unicode61 remove_diacritics 2`）、`chunks_tri`（`trigram`）、`vec_chunks`（vec0，以 brand、lang、doc_class 作 partition 或 metadata）、商品→文档映射。
7. 闸门：黄金集不得回退，并沿用"会缩小就拒绝写"的规则（ADR-0021）。
8. 发布：作为版本化 release 上传到 VPS（`/opt/linker-advisor/releases/<ver>/docs.sqlite`，照搬 `deploy_design_engine.sh` 的模式），原子切换，回滚就是切回上一个 release。

### C.3 检索与引用（`services/advisor` 的工具 `search_documents`）
- 输入：`query, locale, product_ids?, doc_classes?`。
- 步骤：
  1. 如果对话里已确定商品或型号，先圈定只属于它们的文档；圈定后结果为空，再退回全库。
  2. FTS5 取 top-50（型号码走 trigram 表），向量取 top-50（查询由 `voyage-4-lite` 编码；API 故障时只用 BM25；也可用共享嵌入空间的 `voyage-4-nano` 本地兜底）。
  3. RRF 融合（k=60），可选 `rerank-3-lite`，最终取 6–8 块。
- 返回：`chunk_id, text, url, page, title_en/de, edition, lang`。
- 输出约束：模型的 strict 输出只能 `refs:[chunk_id]`。
- 引用渲染：服务端生成"标题（版次）· S./p. N"，链接 `url#page=N`。
- 核验：答案正文里的数字要么来自 `{fact:ID}` 占位，要么逐字出现在被引块中，这是确定性检查，按页执行；`tools/datasheet_evidence.py` 的 `value_present` 是同一思路，但它查整份文档。
- 成本：每次 rerank 约 50 块 × 400 token，约 2.1 万 token，按 `rerank-3-lite` 计约 $0.0004；查询编码几乎为零。

### C.4 三条最强理由
1. **覆盖面**。今天 PDF 正文零可检索：文档记录只是身份信息，规格只限预抽取的 5,739 个值，审核过的 FAQ 只有 74 条。安装商的长尾问题（接线、设置、错误码、间距、电网规则参数、证书细节）都在我们已托管的约 1 万页手册里。页级混合检索把这些内容变成可引用的证据，而且引用的永远是我们自己的 URL 和页码（ADR-0023）。
2. **证据完整性**。用"文档原文 + 第 N 页"加确定性的"数字在被引块中"检查，取代证据路径上的三类东西：LLM 写的 FAQ 自证、AI 抽取或手写的转述、手调的停用词/同义词/阈值和正则补丁链。事实卡从"没人读的权威"变成可量化的黄金评测集，每次重建都测 recall@k 和引用正确率，不再靠线上探针一条条补规则。
3. **低运维且适配 1 vCPU / 3.9 GB**。全部组件采用宽松许可（MIT/Apache），离线构建，产出一个 SQLite 文件，沿用现有 release 和回滚流程。块级内容哈希避免了"一字变化导致全站静默失去语义检索"（线上此刻正是如此）。生产 embedding 换成有正式文档和定价、带 2 亿免费 token 的付费 API，替代 NVIDIA 定位为原型用途、且已经 410 过一次的免费端点。VPS 上不跑模型，也不解析 PDF。

### C.5 退役与保留
- 退役：
  - knowledge-index 里的文档身份记录；
  - wp_options 里的向量和 NVIDIA embedding 依赖（vision 另议）；
  - 停用词、同义词、权重调参和证书通道；
  - 全有或全无的 generation；
  - system prompt 里的"概念基础"：要么改为引用我们托管的教科书或标准文档，要么作为不带引用的一般知识明确标注；
  - `claims.json`，若始终没有读者。
- 保留：兼容合同和 registry（结构化权威）、Woo 商品和 FAQ、事实卡（转为评测集加更正台账）、站点页面（单独成类，作为 Linker 陈述）。
- 与 advisor-rebuild 的衔接：006:42 原计划让 `linker/search-knowledge` 读现有 knowledge-index。建议改为本方案的 `search_documents`，放在 `services/advisor` 一侧（Python，与 006 的 Pydantic AI 同进程），WP 侧只保留 FAQ 实时读取。

### C.6 风险与未决（技术层面，不需要问业主）
- 只有图像的 PDF 需要 OCR；接线图等图片内容无法变成文本，但页链接仍然有用。
- 同一文档的多版次或多语言版本（EN/DE、旧版/新版）全部入库，带版次和日期，引用时显示版次；同一事实以较新版次优先，与事实卡的 R2 规则一致。
- sqlite-vec 尚未到 v1，需锁版本，LanceDB 可作备选；Ubuntu 24.04 的 Python sqlite3 支持 FTS5，加载扩展需要 `enable_load_extension`（sqlite-vec 的 wheel 自带）。
- 选 Voyage 还是开源模型（BGE-M3 或 Qwen3-0.6B）、是否加 LLM 生成的上下文头：先用黄金集的基线数据决定，不预先拍板。

---

## 来源清单（全部经 Apify `apify/rag-web-browser` 抓取，日期 2026-10-09，括号内为 UTC 时间）

- Docling README — https://github.com/docling-project/docling (05:31)
- Docling 技术报告 arXiv 2408.09869 — https://arxiv.org/html/2408.09869 (05:35)
- Docling chunking — https://docling-project.github.io/docling/concepts/chunking/ (05:33)
- DoclingDocument — https://docling-project.github.io/docling/concepts/docling_document/ (05:41)
- docling-models（HF）— https://huggingface.co/docling-project/docling-models (05:33)
- docling-serve — https://github.com/docling-project/docling-serve (05:35)
- marker README — https://github.com/datalab-to/marker (05:31)
- pymupdf4llm README — https://github.com/pymupdf/pymupdf4llm (05:31)
- unstructured README — https://github.com/Unstructured-IO/unstructured (05:31)
- sqlite-vec README — https://github.com/asg017/sqlite-vec (05:31)
- SQLite FTS5 — https://www.sqlite.org/fts5.html (05:33)
- SQLite 混合检索（Alex Garcia）— https://alexgarcia.xyz/blog/2024/sqlite-vec-hybrid-search/index.html (05:33)
- LanceDB README — https://github.com/lancedb/lancedb (05:31)；RRF — https://docs.lancedb.com/reranking/rrf (05:37)；Hybrid — https://docs.lancedb.com/search/hybrid-search (05:37)
- pgvector README — https://github.com/pgvector/pgvector (05:31)
- Chroma README — https://github.com/chroma-core/chroma (05:31)；Full-text — https://docs.trychroma.com/docs/querying-collections/full-text-search (05:37)
- Anthropic embeddings — https://platform.claude.com/docs/en/build-with-claude/embeddings (05:32)
- Anthropic citations — https://platform.claude.com/docs/en/build-with-claude/citations (05:32)
- Anthropic search results — https://platform.claude.com/docs/en/build-with-claude/search-results (05:32)
- Anthropic PDF support — https://platform.claude.com/docs/en/build-with-claude/pdf-support (05:37)
- Anthropic Contextual Retrieval — https://www.anthropic.com/engineering/contextual-retrieval (05:32)
- Voyage embeddings — https://docs.voyageai.com/docs/embeddings (05:32)；pricing — https://docs.voyageai.com/docs/pricing (05:32)；reranker — https://docs.voyageai.com/docs/reranker (05:32)
- voyage-4-nano（HF）— https://huggingface.co/voyageai/voyage-4-nano (05:35)
- OpenAI embeddings — https://developers.openai.com/api/docs/guides/embeddings (05:32)
- Cohere embed — https://docs.cohere.com/docs/cohere-embed (05:33)
- DeepSeek API — https://api-docs.deepseek.com/ (05:32)；pricing — https://api-docs.deepseek.com/quick_start/pricing/ (05:37)
- NVIDIA NIM for Developers — https://developer.nvidia.com/nim (05:35)；https://build.nvidia.com/ (05:35)
- llama-nemotron-embed-vl-1b-v2（HF）— https://huggingface.co/nvidia/llama-nemotron-embed-vl-1b-v2 (05:32)
- BGE-M3 — https://huggingface.co/BAAI/bge-m3 (05:32)；bge-reranker-v2-m3 — https://huggingface.co/BAAI/bge-reranker-v2-m3 (05:32)
- Qwen3-Embedding-0.6B — https://huggingface.co/Qwen/Qwen3-Embedding-0.6B (05:32)；Qwen3-Reranker-0.6B — https://huggingface.co/Qwen/Qwen3-Reranker-0.6B (05:35)
- multilingual-e5-large-instruct — https://huggingface.co/intfloat/multilingual-e5-large-instruct (05:32)
- jina-embeddings-v3 — https://huggingface.co/jinaai/jina-embeddings-v3 (05:33)；jina-reranker-v2 — https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual (05:32)；Jina API — https://jina.ai/embeddings/ (05:35)
- 德语 embedding 比较（WZ-IT，2026-09-16，二手来源）— https://wz-it.com/en/blog/best-embedding-models-german/ (05:35)
- RAGAS — https://github.com/vibrantlabsai/ragas (05:33)；metrics — https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/ (05:35)
- 技术文档 RAG 评测 arXiv 2605.27444（2026-05）— https://arxiv.org/html/2605.27444v1 (05:35)
- 未采用（可信度低）：两条 LinkedIn 帖子（PDF 解析比较、RAG 评测）。marker 的 MODEL_LICENSE 页面抓取返回 500，许可条款改以其 README 的"Commercial usage"一节为准。
