# #257 Genie 文档检索：验收记录（2026-10-17）

分支 `feat/257-knowledge-retrieval`；本地实例 g257（快照 latest = 10-15，只用于提供 Woo 侧的 abilities）；索引 `~/de-linker-data/index/builds/20261016T072222Z/index.sqlite`，与 VPS `current` 是同一版本、同一 sha256。

## 1. 文档评测集（强制调用 search-knowledge）

本节的结果是 rebase 到含 #233（理解层）的 main 之后**重跑**的。rebase 之前的两次运行（34 ✓ / 2 ◐，走的是已删除的 prefetch 入口和文本来源行）保留在 PR #282 早先推送的提交 `9d16c0df` 的 `docs/acceptance/2026-10-17/257/eval/` 里，这里不再引用。

- 题目：`services/genie/eval/knowledge/questions.json`，Knocket 对照题集第 2、3、5、6、7、8、9、10、19 题，EN 与 DE 各一，共 18 轮。
- 跑法：`services/genie/eval/knowledge/documents.py`，走的就是服务的路径：理解层（实例的 Store API 提供产品词，接着定路由、执行路由的调用）→ deepseek-flash（官方 API）→ 落地检查与水合。查询编码是经 OpenRouter 的 gemini-embedding-2。**只有 Jev 被钉死为 `documents_specs`**，所以每一轮都由路由在模型之前调用 search-knowledge，并圈定到问题里点名的产品。Jev 会不会把问题判成文档问题，由 #233 的评测衡量。
- 原始结果：`eval/run-20261017T224855.json`（A）、`eval/run-20261017T225306.json`（B），两次完整运行。自动判 A 16/18、B 17/18。
- 36 轮里每一次文档检索都是 `ranking: vector`、`encoder: google/gemini-embedding-2`；引用以 #233 的文档链接出现在答案后面（"标题 · p. N"，同一文件只出一个链接、页码合并）。

**判分**（TRIAL.md §1，逐条读答案，对照我们托管的文档）：

| # | 要求 | EN A | EN B | DE A | DE B |
|---|---|---|---|---|---|
| 2 | 最大 PV 输入 | ✓ 20000 Wp | ✓ | ✓ | ✓ |
| 3 | **3 个 MPPT** | ✓ | ✓ | ✓ 3 个，每路 2 串 | ✓ |
| 5 | ESA 10 kW 配哪些电池 | ✓ GW5.1/8.3（含 G21）/6.0/9.0-BAT-D-G20，带各自能量 | ✓ | ◐ 说明是一体式系统、模块有 5/6/8/9 kWh、最多 12 块，但没有点出电池型号 | ◐ 同左（模块数与总容量 108 kWh 正确） |
| 6 | L260 Omni 可用容量 | ✓ 标称 260 kWh、DoD 98%（单串），没有单列可用值 | ✓ | ◐ 核心对；但末句"Produktverbund reicht … von 400Vac"把电压用成了容量范围 | ✓ |
| 7 | **2026 年起户用 10 年** | ✓ 2026-01-01 前 5 年；之后户用并网与混合机 10 年，C&I 5 年 | ✓ | ✓（开头仍有一句"standardmäßig 5 Jahren"，随后分档正确） | ✓（同左） |
| 8 | OCEAN 2 相数与功率（按 TRIAL 10-17 更正判） | ◐ 两种相数都有，按型号给出功率（3/3.68/4.6 kW、5/6/8 kW），但数字来自商品数据、没有文档链接 | ✓ HD-P1 单相、HD-P3 三相，逐型号给功率 | ✓ | ✓ |
| 9 | **SAJ 出口限制步骤** | ✓ Export/Generation Limitation Settings → Enable → 类型 → 数值 → Save | ✓ | ✓（另写出 App 里的进入步骤） | ✓ |
| 10 | **快速安装指南里的间距** | ✓ 1500 / 400 / 500 / 1000 / 500 mm，与手册版本并列；承重 1.5 tons | ✓ | ✓ 承重 1.5 Tonnen | ✓ |
| 19 | §14a：**明说文档里没有** | ✓ 明说没写；Peak Shaving 等只作为相关内容提到 | ✓ | ✓ | ✓ |

合计 36 个答案：**✓ 32，◐ 4，✗ 0**。第 19 题四个答案都明说文档里没有。

**◐ 的来源**（记录给评审与 #233）：

- 第 5 题 DE：路由把 "ESA" 匹配到了 `goodwe-esa-lcn`（工商业 125/261 kWh）和 `goodwe-esa-5-30kw-eta-g20` 两个系列（`route.matches`），**单相 ESA 3–10 kW（EHA）系列不在 #233 的产品词表里**，检索因此被圈定到 GW10K/8K/12K-ETA 与 GW125/261，列出 GW5.1/8.3/6.0/9.0-BAT-D-G20 的 3–10 kW 数据手册第 3 页落在圈定之外。属于 #233 的词表数据，本分支不改，已写进 PR。
- 第 6 题 DE A：数字占位用错了地方（一个电压值被放进容量范围的句子里）。落地检查只能保证数字出自被引块，管不到语义。
- 第 8 题 EN A：模型用了路由取到的商品数据回答，没有引文档。内容正确。
- 德语的"standardmäßig 5 Jahren"开头、"von 10 Jahre"（主格单位，见 `copy-review.md` §3）这两处仍在，都不影响判分。

## 2. 网页检索确实走 gemini-embedding-2

- 线上（本票之前的步骤，见票评论）：wp-config `HOME` 修复后，20 次网页检索的 OpenRouter 用量 +0.0000816。
- 本分支：用同一把密钥连续 20 次 `KnowledgeSearch`，OpenRouter 用量 **+0.0000887**；每次都是 `ranking=vector encoder=google/gemini-embedding-2`。
- 编码耗时（各 12 次）：VPS 中位 0.46 s、最大 0.83 s；本机中位 3.8 s、最大 5.35 s。
- 失败要显式：三种状态的实测记录见 `failure-modes.md`（401 → 报错并兜底；不可达 → 2 次尝试共 20.5 s 后报错；没有编码器 → BM25，并写 WARNING 日志）。rebase 之后，路由里的文档检索失败时，记 `knowledge_error` 并让这一轮进兜底（`test_agent.py::test_a_failed_routed_document_search_ends_the_generation`、`test_the_route_runs_the_document_search_in_process`）。

## 3. 两份索引择一

结论与理由写在规格 10「唯一检索源」：VPS 的 SQLite 是唯一检索源，MariaDB 那份退役（ability 与 PHP 类已在本分支删除；五张表与共享主机的密钥文件在上线时先证后删，需业主同意）。用于比较的实测：线上 MariaDB 向量查询 30–80 ms，用到了向量索引，但经 WordPress 的整次检索约 3.5 s；VPS 上 sqlite-vec 热查询 240 ms，带商品圈定 150 ms；本机 MySQL 9.6 跑不了 MariaDB 的向量函数。

## 4. 黄金集回归（`just eval`，984 问）

见 `golden-eval.md`。
