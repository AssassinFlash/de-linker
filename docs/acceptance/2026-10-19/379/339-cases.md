# #339 产品词回归（#363 / #364 / #367）

用例在 `services/genie/eval/regression/339-product-words.jsonl`。`services/genie/tests/test_regression_339.py` 读取该文件并执行。本文件是索引。

这组只覆盖这三张票的产品词行为。#339 里其余夹具（账户、价格、附件、基线 100 题）不在这个文件里。

1. 文档意图，页面上已有三个商品，问目录里没有的 `GW50K-ETA-G20`（英、德）。期望：`searched=false`，回答说这轮没有搜，不说缺货或不在范围内。文档路由的调用数 ≤ 3（给模型留一次）。
2. 同上，页面只有一个商品。期望：调用里有对 `GW50K-ETA-G20` 的 search-products，`searched=true`。
3. 三个已知型号的文档问题。期望：调用数 ≤ 3；每个型号要么被 get-product 或 search-products 查过，要么 `searched=false`。
4. 文档意图加四个目录形状的未知型号。期望：调用数 ≤ 3；没进调用的型号 `searched=false`。
5. `Order ABC-123-456 status?`、`DLK-2026-001 status?`、`ORDER-2026-G20 status?`。期望：不产生型号笔记，不说 “not in our product range”。
6. 两个型号的搜索都返回了商品，回答却说 “no entry”。期望：接地失败。
7. 没搜过的型号被说成不在范围内（英、德）。期望：接地失败。
8. 品牌被拆到两句，或只说了目录品牌。期望：接地失败。同一句里两个品牌、卡片上有产品，型号可以不在这一句里：`You wrote SAJ; it is a GoodWe product.` 通过。带型号的那句也通过。
9. 已搜的型号没有成功的 search-products（调用未记入，AbilityError 的形状）。期望：兜底是降级句，不说不在范围内，也不说 “did not return”。一次成功、一次失败的混合同样：失败的型号用降级句。
10. 计划之后再 `with_page`：文档路由先留下空位，页面读得进，调用数仍 ≤ 3。
