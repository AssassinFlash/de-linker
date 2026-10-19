# #339 可导入的回归用例（#363 / #364 / #367 第二轮）

本文件不改 #339 的夹具。每条给出复现句和期望行为，供那套回归原样导入。实现落在 `services/genie/tests/test_product_words.py`。

1. 复现：产品页上问一个目录里没有的型号，文档意图，页面上已经有三个商品占满四次调用的预算。英文 `Do you have the GW50K-ETA-G20 in stock?`，德语 `Haben Sie den GW50K-ETA-G20 auf Lager?`。期望：该型号 `searched=False`，回答说这轮没有搜（英文 “was not searched”，德语 “nicht gesucht”），不说缺货或不在产品范围内。调用数 ≤ 4。
2. 复现：同上，但页面只有一个商品，预算装得下。期望：调用里有对 `GW50K-ETA-G20` 的 search-products，`searched=True`。
3. 复现：三个已知名型号的文档问题 `Do you have HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX and HS3-12K-T2-W/G-PX in stock?`。期望：四个调用以内，每个型号要么被 get-product 或 search-products 查过并记 `searched=True`，要么记 `searched=False` 并在回答里说没搜。
4. 复现：文档意图加上四个目录形状的未知型号 `GW51K-ETA-G20` `GW52K-ETA-G20` `GW53K-ETA-G20` `GW54K-ETA-G20`。期望：调用数 ≤ 4；没进调用的型号 `searched=False`。
5. 复现：`Order ABC-123-456 status?`，Jev 意图 other、置信度 0.95。期望：不进入产品路由，不产生型号笔记，不说 “not in our product range”。
6. 复现句：`HS3-5K-T2-W/G-PX and HS3-8K-T2-W/G-PX are both listed. These two model codes return no entry in our product data.` 两个型号的搜索都返回了商品。期望：接地失败。
7. 复现句：`GW50K-ETA-G20 is on the label. It is not in our product range.` 该型号本轮没有搜。德语：`GW50K-ETA-G20 steht auf dem Typenschild. Es ist nicht in unserem Sortiment.` 期望：接地失败，失败原因是把它说成了缺失。
8. 复现句：`GW10K-ETA-G20 is not in our product range. GoodWe may help.` 客户写的是 SAJ，卡片上有该商品。期望：接地失败。同一句通过的形状是 `You wrote SAJ; GW10K-ETA-G20 is a GoodWe product.`
9. 复现：search-products 返回 `ok: false`，或本轮没有任何工具结果，笔记却标了已搜。期望：兜底是降级句（`DEGRADED`）或邮箱句，不说 “not in our product range”，也不说 “The search did not return …”。搜索成功但没有商品时，才可以说没有匹配。
