# #16 段：知识索引入站、阈值收口与 Jev 重校准（2026-10-11）

依据：#10 评审线裁定迁移项（#10 issue 评论：阈值目标迁移 + 57/203 可修数据贡献 + 两阶段重排）、本日工单三项。

## ① 索引导入实例（位置 A 本地形态）与 ability 实测

- 源：`~/de-linker-data/index/builds/20261010T082155Z`（#10 最新构建，gemini-embedding-2，383 文档 380 索引 3 截断失败、32,852 块）。
- 本地栈是 Homebrew MySQL 9.6，无 MariaDB 向量机制（实测：`VECTOR INDEX (e) DISTANCE=cosine` → 1064 语法错；`VEC_DISTANCE_COSINE`/`VEC_DISTANCE`/`COSINE_DISTANCE`/`DISTANCE` → function does not exist），故按 `KnowledgeIndex` 自己设计的回退路径接入：用 #10 管线导出器（`index.mariadb.export`，corpus meta dimensions=0）产出无向量版 `index-mariadb-fulltext.sql`（28.9MB），导入实例库 `linker_t16`：`wp_genie_chunks` 32,852、documents 383、products 264、document_models 881，FULLTEXT 实测可查（'battery module' 10,464 命中）。dense 路径留在生产共享主机（MariaDB 11.8.9，#10 只读实测支持）。
- **search-knowledge 实测**（`wp eval-file`，走 ability 同一 `SearchKnowledge::execute`）：三条黄金问题（00506d0f0c-en、0065e3e240-en、00cc9d826a-en，bake-off 黄金集）各返回 8 条真实 chunk；FULLTEXT 路径的金块名次：Q1 第 10、Q2 >30、Q3 第 22——真实命中、排序深，与 bake-off 对关键词路径的测量一致（dense 路径是 bake-off 采信的出厂路径，本地无向量函数跑不了）。

## ② 57/203 数据回收与阈值数字

**修复（实例 t16 的 WP 数据，`source_tier: index-repair-2026-10-11` 可追溯）**：无映射型号 13 个建草稿商品（`_delinker_brand`/`_delinker_model` + downloads 挂金文档；含 3 个事实卡无型号项用字面 designation）；金文档未挂商品的 19 处补挂既有商品 downloads。评估链路完整走通：修复后 WP → `inventory.run` 对 t16 REST 重跑（`/tmp/t16-inventory-t16.json`，不覆盖共享产物）→ #10 corpus 只换 documents/products 挂接、chunks 与向量逐字节复用 → `store.export` 新索引 `builds/20261011T000000Z-repair/index.sqlite`。

**`just eval`（984 问，同一 harness）前 → 后**：

| Setting | Recall@5 前 | 后 | Page acc 前 | 后 |
|---|---|---|---|---|
| vectors, by product（出厂路径） | 52.8% | **56.2%** | 83.1% | 82.8% |
| keywords, by product | 26.9% | **30.8%** | 82.6% | 83.1% |
| vectors, whole library | 42.8% | 42.8% | 82.9% | 82.9% |

有商品映射的问题 878/984 → **984/984**（此前 106 问走全库）；EN 55.1→57.5、DE 50.6→54.9。页码正确率 −0.3pp（噪声级）。

**两阶段重排（`index/eval/rerank.py`，进仓库）**：一级 dense 按商品圈定折页成候选池，二级可选 DeepSeek 列表式重排进前 5。候选池页级上限（200 问 EN/DE 样本）：depth 50 = 84.5%、**depth 100 = 98.0%**、depth 200 = 99.0%——top-50 达不到 90% 门槛，**depth 100 是过线的最小池深**（与 #10 裁定的 @100=92.1% 全库口径相比，修复后的按商品圈定把池上限抬高了）。

## ③ Jev 两项

- **R5 根因（卡片角色）已修**：`pilot.py` 条目构造区分 `This page's product` 与 `Recommended products` 两行（页面本体来自 `PAGE_PRODUCT` 表，依据面板页面事实）；错误变体只在推荐行替换。v4 跑：R5 全问与确定性一致（v1 的 grounded=0 分歧消失）。已知残留：r3spell 的 better_pick 变体（页面本体换成 4107）被评为 equal——变体本身弱（推荐行相同、正文主导），该行 grounded 升级判分仍正确。
- **grounded 阈值重校准**：v4 实测（角色分离 + 双道完整 reference）一道 grounded 置信 0.0–0.95、≥0.6 的标签 11/11 全对、唯一错标签在 0.0；离线级联复算：0.85 → 升级 9/11、agreement 11/11；**0.6 → 升级 3/11、agreement 11/11**。`TURN_THRESHOLDS["grounded"] 0.85 → 0.6` 落仓库（turns.py 注释带证据），测试同步。
- **切片方案被证据否决**（记录留档）：先试验了"缩小 reference 切片"（`slice_reference`，只喂一道），实测一道 grounded 标签退化为 Not-verifiable（r1/r2/r5 的答案事实在被裁掉的字段里），会随低阈值出错的正是标签而非置信——删除，升级道与一道都读完整 replay。
- **运行发现（归数据，不归评审）**：r4spell 在本实例升级判 grounded=0：归档回合把 6483（EcoFlow OCEAN 2 HD-P1-3K-S2）列为 home hybrid，而当前库 `pa_application` 为空（wp-cli 实证）——评审抓到的是真实的数据断言缺口。#13 试点判 2 系当时实例 replay 数据不同。

## 运行记录

- 试点 v4（采用）：`docs/acceptance/2026-10-11/16/jev-recal-run/`（jev/deepseek/cascade/summary）。
- 重排与池上限：`services/genie/index/eval/rerank.py`（`python -m index.eval.rerank --index … --depth N --judge none|deepseek`）。
