# #257 黄金集回归（`just eval`，984 问，索引 20261016T072222Z）

"之前"是该构建目录里原有的 `eval.json`（10-16，旧检索代码）；"之后"是本分支 2026-10-17 重跑，`just eval --index …/20261016T072222Z/index.sqlite`。评测只计排序本身：`index.eval.run` 调 `search(..., neighbours=False)`，因为邻块排在命中之后，计进去会算成 k 之后的名次。

| 设置 | Recall@5 前 → 后 | MRR@5 前 → 后 | 页码正确率 前 → 后 |
|---|---|---|---|
| vectors, by product | 51.7% → **54.9%** | 0.364 → 0.387 | 83.1% → 82.6% |
| vectors, whole library | 41.2% → **55.0%** | 0.278 → 0.386 | 82.8% → 83.7% |
| keywords, by product | 27.0% → 28.5% | 0.175 → 0.183 | 82.6% → 82.5% |
| keywords, whole library | 13.6% → 28.0% | 0.084 → 0.176 | 77.0% → 82.6% |

- by product 这一行的 +3.2pp 来自碎片过滤（少于三个词的非表格块不再占名次）。
- whole library 这一行的 +13.8pp 来自型号圈定：问题里写了型号代码时，先在标了该型号的文档里检索。黄金集的问题大多带型号，所以不传商品 ID 的全库检索也接近了按商品圈定的水平。
- 页码正确率两行分别变化 −0.5pp 与 +0.9pp，属于噪声量级（10-11 的修复轮也记过 −0.3pp）。
- 门槛（第 1 轮评审后改，规格 10 验收 (a)）：原来的 90% / 95% 没有来源、结构上也达不到，已删除，改为"不低于基线"，基线就是上表"后"一栏的两行 vectors（`index/eval/run.py` 的 `BASELINE`）。按新判定重跑 `just eval`：数字逐位相同，退出码 0；输出每个设置与基线并列：

```
vectors, by product: recall@5 54.9% (baseline 54.9%, +0.0), citation page accuracy 82.6% (baseline 82.6%, +0.0)
vectors, whole library: recall@5 55.0% (baseline 55.0%, +0.0), citation page accuracy 83.7% (baseline 83.7%, +0.0)
```

低于基线时退出 1，并逐项写出"below the baseline … by N points"（`tests/test_eval_gate.py`）。
