# 16i：索引入站、阈值收口与 Jev 重校准（2026-10-11）

#16 主线外移的独立段：与视觉移植零耦合的知识索引与判分收口。依据：本段工单；#10 评审线裁定（issue #10 评论 2026-10-10：两阶段重排上限 **@100=92.1%、@200=95.5%** 独立复证；57/203 可修数据贡献先补挂金文档/补型号映射）。

## 装配

- `just up t16i`（http://127.0.0.1:8948，库 `linker_t16i`；PHP 8.3、WordPress 7.1.3、WooCommerce 11.2.0）→ 摘掉三个检出软链 → `just pull load t16i 20261010-0033 --live-code`：`ok:true`（发布品 106、附件 2,755、缺失 0、线上地址残留 0、德文指纹重算 61 篇、德语抽验 /de/ 三页 ok）→ 插件换装（`linker-commerce`/`linker-i18n`/`linker-tools` 指向本检出；`terravolt-b2b-core`、`linker-ai-assistant` inactive 留盘；`polylang`、`redis-cache` 激活）→ `wp linker-i18n setup --assign` → `just serve t16i`（engine `:8949`、genie `:8950`）。

`setup --assign` 不是可选步骤：不配 Polylang 语言时 REST 请求里 `get_posts(post_type=product)` 返回空表，`linker/search-products` 的 `qualified` 与 `excluded.by_reason` 全空——① 的 ability 与 ③ 的 reference 回放都会读到空数据。装配时必须先跑它。

## ① 索引入站（位置 A 的本地形态）与 ability 实测

源：`~/de-linker-data/index/builds/20261010T070946Z/index-mariadb.sql`（1,239,285,379 B，#10 位置 A 的产物，`index.mariadb.export` 写出）。

- **原样导入失败，失败点固定**：`ERROR 1064 (42000) at line 23: ... near 'INDEX (`embedding`) DISTANCE=cosine'`。逐项探针（MySQL 9.6.0）：`VECTOR(3072)` 列可以建；`VEC_FromText`、`VEC_DISTANCE_COSINE`、`COSINE_DISTANCE`、`DISTANCE` 一律 `ERROR 1305 ... does not exist`。本机实例是 Homebrew MySQL，线上共享主机是 MariaDB 11.8.9（`docs/local-stack.md` 的既知差异），`VECTOR INDEX ... DISTANCE=cosine` 是 MariaDB 11.7+ 的语法。
- **本地适配**（`adapt-index-sql-for-local-mysql.py`，两处改写，别的字节不动）：删掉 1 处向量索引子句（连带的逗号一起删，FULLTEXT 保留）、32,852 处 `VEC_FromText(` → `STRING_TO_VECTOR(`。
- **导入结果**（`linker_t16i`：manifest 只有 chunks 与 documents 两个计数，两数与它一致——32,852 / 383；其余三数为本库实读）：`wp_genie_chunks` 32,852、`wp_genie_documents` 383、`wp_genie_document_models` 881、`wp_genie_products` 264、`wp_genie_meta` 6。向量随行入库（`VECTOR(3072)` 列非空），但本机没有向量距离函数，`KnowledgeIndex::vector_ranking` 落到 `keyword_ranking`。
- **FULLTEXT 实测**：`MATCH(header,text) AGAINST('"battery" "module"' IN BOOLEAN MODE)` = 10,464 行。
- **ability 实测**（`just wp t16i eval-file <abs>/docs/acceptance/2026-10-11/16i/probe-search-knowledge.php`，走 `SearchKnowledge::execute` 本身，即 ability 的同一条路径）：

| 黄金问题 | hits | 金块在候选序里的名次（30 个候选） |
|---|---|---|
| `00506d0f0c-en`（DTSU666 与 CHS2-29.9K-T4-X 是否列为兼容） | 8 | 第 10 |
| `0065e3e240-en`（GW261.2-BAT-LCD-G10 的额定/最大电流） | 8 | 超出候选深度 |
| `00cc9d826a-en`（GW125/261-ESA-LCN-G10 的最大交流输出电流） | 8 | 第 27 |

三条都返回 8 条真实 chunk（标题、页码、正文、托管 URL 齐备），金页排序深——与 bake-off 对 BM25 路径的测量（28.8%）以及它"先按商品圈定再做 dense"的出厂形态一致：关键词路径不是出厂路径，它的作用是没有查询编码器时的回退。

- **本机跑不了的那一半**：dense 路径依赖 `VEC_DISTANCE_COSINE`/`VEC_FromText`，两者在 MySQL 上都不存在；`QueryEmbedding` 的查询向量经 `wp_remote_post` 出网取（**集成点已消除**：main #99 起默认走 OpenRouter 的 `google/gemini-embedding-2`，3 次重试、失败大声记日志，aihubmix 仅 `LINKER_EMBEDDING_PROVIDER=aihubmix` 显式开关——本段当时记的"aihubmix"是迁移前的默认值，rebase 到 main 后代码里已无此默认），本地隔离只放行 127.0.0.1，所以它本地恒返回 null。两者都让本地实例落到关键词路径——这不是缺陷，是本地栈与隔离层的既定边界；dense 的验收面在共享主机（MariaDB 11.8.9）与 `just eval`（SQLite + sqlite-vec）。

## ② 57/203 数据修复的回收

修复内容与来源：`docs/acceptance/2026-10-11/16/knowledge-index-recal.md` ② 节（实例端 13 个无映射型号建草稿商品 + 19 处金文档补挂既有商品 downloads，`source_tier: index-repair-2026-10-11`）。修复后的索引是 `~/de-linker-data/index/builds/20261011T000000Z-repair/`（chunks 与向量逐字节复用 #10 的 082155Z 构建，只换 documents/products 挂接）。

**`just eval` 一次（不带重排），984 问同一 harness**：

| Setting | Recall@5 修复前 | 修复后 | Δ | 页码正确率 前 → 后 |
|---|---|---|---|---|
| vectors, by product（出厂路径） | 52.8% | **56.2%** | **+3.35pp** | 83.1% → 82.8% |
| keywords, by product | 26.9% | **30.8%** | **+3.86pp** | 82.6% → 83.1% |
| vectors, whole library | 42.8% | 42.8% | 0 | 82.9% → 82.9% |
| keywords, whole library | 13.6% | 13.6% | 0 | 77.0% → 77.0% |

有商品映射的问题 878/984 → **984/984**（修复前 106 问只能走全库）；出厂路径 EN 55.1→57.5、DE 50.6→54.9。页码正确率 −0.3pp，噪声级。修复回收了 57/203 里"可修的数据贡献"那一半的量级：这一轮把走全库的那批拉回圈定内，让出厂路径拿到分。

**本次复跑与早先记录逐字节一致**：`eval.json`（新跑）与 `eval.json.bak-20261011`（12:21 的记录）JSON 全等——同一索引、同一黄金集、同一 harness 下评测是确定性的，这一条把"数字会不会随跑随变"的问号去掉。

**上限数字引 #10 裁定**：两阶段重排的页级上限 **@100=92.1%、@200=95.5%**（#10 评审线 2026-10-10 独立复证；bake-off §5.2 的单阶段暴力上限是 @50 79.6%、@200 94.5%，两项不是同一次测量，本段以裁定里的两阶段数字为准）。一阶段排序到不了 90%@5 是结构结论，不是本段的待修项。

**小样本重排实测（一次性，`--sample 20 --depth 50 --judge deepseek --batch 20`）**：**到 10 分钟上限未返回，`timeout` 以 exit 124 结束**（40 问、每问一次列表式重排调用；日志只到 `encoding 40 queries…`，没有任何一题落盘）。按工单的边界——重排 live 评测不许第三次整跑——**放弃 live 重排实测，不再重跑**。可核验的候选池上限另测（不需要判分模型，只跑一级）：

| 深度 | 修复前索引 `20261010T082155Z` | 修复后索引 `20261011T000000Z-repair` |
|---|---|---|
| 50 | 85.0% | **93.5%** |
| 100 | 90.0% | **98.0%** |
| 200 | — | **99.0%** |

（`--sample 100`＝每语言 100 问＝200 问，与 #10 裁决口径同；每次 21–26 s，无判分模型调用。**五组数字的原始 stdout 已归档**：本目录 `runs/pool-ceiling/<索引>-depth<N>.txt`——修复前 `20261010T082155Z` 的 depth 50/100、修复后 `20261011T000000Z-repair` 的 depth 50/100/200；修复轮重跑复核，五组数值逐一复现，命令见"运行记录"。）

两条结论：
1. **数据修复把候选池抬过线**：depth 50 从 85.0% 升到 93.5%（+8.5pp）、depth 100 从 90.0% 升到 98.0%（+8.0pp）。修复前 top-50 池过不了 90% 门槛，修复后过得了；#10 裁决的 @100=92.1% 是修复前语料的下限，本段的 98.0% 是修复后的同深度值。
2. **移交文档里 depth 50 = 84.5% 的标注要更正**：同一个 200 问样本、同一个深度，修复前索引实测 85.0%、修复后 93.5%——84.5% 最合理的归类是**修复前**的值（**推断**：与修复前的 85.0% 同一量级、与修复后的 93.5% 差 9pp；移交文档当时的索引构建与其命令没有留档，84.5% 这个数无法逐字节复现，故这是归类不是复算），不是该文档写的"修复后索引"的值。depth 100/200 两栏与移交文档一致（98.0%、99.0%），所以那份文档是三个数字里混了一次修复前的测量。

## ③ Jev 两项

### R5 分歧的根因（卡片角色）——已修并复验

`pilot.py` 的条目构造把页面的"本体"与"推荐"两种角色拍平成一个 `Products offered` 列表，判分模型于是把"对下列每块电池有 documented pairing"读成对列表全员成立的断言（R5 的卡片集含页面本体 4107）。修复：`PAGE_PRODUCT` 表给出每一轮的产品页面本体，渲染成两行——`This page's product: <id>` 与 `Recommended products: <…>`；错误变体只换推荐行（r3spell 换的是本体，变体因此把本体张冠李戴，这正是要判的错）。

**本段实测**（`runs/pilot-20261011-t16i2`，活调用 11 轮）：**agreement 9/11**，两处不一致与早先记录完全相同（`panel-r3spell` 判 equal、`panel-r4spell` grounded=0），**R5 不再是分歧**（grounded=2、appropriate=yes、better_pick=A）。R5 的分歧确实来自构造，修复后消失。

### grounded 阈值：0.85 → 0.6 的复算与"活调用复现不了"的实测

阈值改动随本段入库（`turns.py` `TURN_THRESHOLDS["grounded"] = 0.6`）。三条可选核实：

1. **切片方案经实测否决**（记录留档）：先试"缩小 reference 切片"，第一道 grounded 标签在 r1/r2/r5 退化为 not-verifiable——答案的事实恰在被裁掉的字段里，低阈值会直接把错标签放行。删除。
2. **阈值复算（用历史记录，离线可复算）**：把已归档的 jev 记录按阈重算**升级数**——任一问置信度低于其阈值即该条升级（appropriate/better_pick 阈值固定 0.5/0.6，两列只差 grounded 阈值取 0.85 还是 0.6）：

   | 记录目录 | 升级@0.85 | 升级@0.6 |
   |---|---|---|
   | `runs/pilot-20261011`（角色未分离的 v1） | 10/11 | 5/11 |
   | `runs/pilot-20261011-v4` | 9/11 | 3/11 |
   | `runs/pilot-20261011-recal` | 8/11 | 2/11 |
   | `runs/pilot-20261011-t16i2`（本段活调用，旧 chat 路由） | 7/11 | 7/11 |

   前三份记录都在 jev-1.13 的回答上得出"0.6 把升级压到 2–5/11"，agreement 不变——**阈值这一项在 jev 真身上成立**。t16i2 那份两列相同（7/11）：该轮 7 条记录的置信度是 null（见下条），任何阈下都升级；它既不是新阈的证据，也不是反证。
3. **本段活调用复现不了这一项，原因是上游换了后端**：11 次"jev"调用里 0 次由 jev-1.13 回答。响应自报的 `model` 是 `deepseek/deepseek-v4.1-flash`（9 次）与 `google/gemini-3.8-flash`（2 次）；其中 7 次的回复根本没有校准概率，`confidence` 为 null，一律低于任何阈——**0.6 与 0.85 在本段这 11 轮里都是 7/11 升级**。一次直接探针（同 `typesafe/jev-router`、同一 body）回的是 `model: anthropic/claude-sonnet-5.5`、`provider: Google`，并且对"请回概率 JSON"的请求给出退化的 `{"yes":0.5,"no":0.5}`。结论：`typesafe/jev-router` 现在按请求把流量分给第三方后端，不再稳定落在 Jev 上；**阈值重校准的前提（jev 的校准概率）本段无法在活调用里执行**。这不是本段能改的（路由池在供应商侧，且 `typesafe/jev-router` 就是业主裁定的形态），登记为集成点。

> **2026-10-11 晚更正（rebase 到 main 之后）——Jev 的路径已切换，上条登记的集成点已消除**：业主裁定 Jev 走 OpenRouter 原生 `/v1/systemone` + `typesafe/jev-1.13`（本分支 b6fefe9 起，`registry.JUDGES["jev"]`），`typesafe/jev-router` chat 路由按元路由处理、不再使用。因此本文出现的 11 轮 agreement 数字（`runs/pilot-20261011-t16i2`：agreement 9/11、升级 7/11）**测自旧 chat 路由，切换后没有重跑 11 轮复验**；上表的阈值离线复算不受影响（那是旧记录上的复算），但它不是新路径上的活调用证据。新路径留有一次实测：`systemone-probe-20261011.json`（本目录；脚本 `probe-systemone-jev.py`，走 `pilot` 同一条 `linker_judges.judges.call` 路径重跑 panel-r10）——响应 `model` 自报 `typesafe/jev-1.13-20260917`，`usage.cost` = $0.0003654（8700 in / 71 out），解析后 grounded=2（置信 0.79）、appropriate=yes（0.90）、better_pick=A（1.00）；该条在 0.85 阈下会升级、在 0.6 阈下不升级（单条观察，不作阈值结论）。

### 运行发现（归数据，不归评审）

`panel-r4spell` 的 grounded 在本段仍判 0：归档回合把 6483（EcoFlow OCEAN 2 HD-P1-3K-S2）列为 home hybrid，而当前库 `pa_application` 为空。与早先记录的结论一致——评审抓到的是真实的数据断言缺口，不是判分缺陷。

## 重排（两阶段）

`index/eval/rerank.py`（评测级，进仓库）：一级 dense 按商品圈定折页成候选池（深度可配，评测时把 `retrieval.CANDIDATES` 抬到 `depth*4`），二级可选 DeepSeek 列表式重排进前 5；`--judge none` 只量池上限。

- 命令行补了凭据读取：原来只读 `os.environ`，没导出变量就 401；改成走 `linker_genie.embedding.credentials`（环境变量优先、否则业主的 `~/.config/terravolt-builder/deepseek.env`，与 `linker_judges.http` 同一读取规则）。rebase 到 main 后该函数保留在 `embedding.py` 里供本脚本读 DeepSeek 键；`gemini_from_env` 本身是 main #99 的铁律版（OpenRouter 默认、aihubmix 仅显式开关），本分支旧版的自动降级已丢弃。
- live 重排实测 10 分钟未返回、已放弃（②节末表）；候选池上限五组均实测在 ② 节。
- 一级排序本身很快：depth 200、200 问的池只要 21 s——重排的耗时全在二级模型调用上。

## 运行记录

- ability 探针、本地化脚本与 Jev 探针：本目录 `probe-search-knowledge.php`、`adapt-index-sql-for-local-mysql.py`、`probe-systemone-jev.py`（输出 `systemone-probe-20261011.json`）。
- 评测：`~/de-linker-data/index/builds/20261011T000000Z-repair/eval.json`（本次复跑；同目录 `eval.json.bak-20261011` 是早先记录，两份相等）。
- 重排：live 那一跑 exit 124（10 分钟上限）无产出；池上限五组的原始 stdout 在 `runs/pool-ceiling/`（`<索引>-depth<N>.txt`），命令（在 `services/genie` 下）：
  `uv run --locked python -m index.eval.rerank --index ~/de-linker-data/index/builds/<索引>/index.sqlite --depth <N> --judge none --sample 100`——修复轮重跑五组，数值与 ② 节表格逐一相同（修复前 85.0 / 90.0%，修复后 93.5 / 98.0 / 99.0%）。
- Jev 试点：`services/genie/eval/judges/runs/pilot-20261011-t16i2/`（jev / deepseek / cascade / items / summary；测自旧 chat 路由）；首跑 `runs/pilot-20261011-t16i/` 是 Polylang 未配时的空 reference 记录，只作对照。新路径的实测（`/v1/systemone`）见 §③ 更正段，探针命令（在 `services/genie/eval/judges` 下）：`uv run --locked python ../../../../docs/acceptance/2026-10-11/16i/probe-systemone-jev.py`。
