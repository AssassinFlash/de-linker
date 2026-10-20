# #339 产品词回归（#363 / #364 / #367）

用例在 `services/genie/eval/regression/339-product-words.jsonl`。`services/genie/tests/test_regression_339.py` 读取该文件并执行。本文件是索引。

这组覆盖这三张票的产品词行为，以及 #384 把极端问法和型号码写在同一句里的复合路径。#339 里其余夹具（账户、价格、附件、基线 100 题）不在这个文件里。

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
11. #384 复合。类别极端旁边一个目录里没有的型号（英、德）：聚合调用在前，未知型号自己再搜一次。一个已知型号加一个未知型号：两个码都搜。两个已知型号再加一个目录里没有的型号，问最小：聚合仍在前，三个码都搜，兜底点名那个未知型号。两个已知型号问最便宜（英、德）：聚合仍带 `extreme=cheapest`，提示要求可见价格时只出赢家那一张卡。可见价格的兜底点名两个型号，卡片只有赢家。隐藏价格的兜底写出价格句和 “You named” / “Sie haben … genannt.”。只写价格句、不点名型号：接地失败。
12. #415 库存问句（`kind: stock`）。SAJ H2-10K-T3，有货/缺货 × 英/德 × 访客/已批准，以及一次查不到状态。期望：路由是 products 且 `stock`，不调 handoff-team；正文是商品页的状态句，卡片是 4107，价格行留在卡上；正文没有数量。失败时是降级句，没有卡片，也不说匹配商品。
13. 语言（#396，地址兼 #404）。`Im looking for a battery` 与 `the ins and outs` 判英语，不因 `im`/`ins` 变成混合。`Der Fehlerstromschutzschalter Typ A ist erforderlich.` 判德语。`Schutzart IP65, Typ A.` 不判英语。`The office is at Hauptstraße 3.` 仍是英语：街道名和专名不计票。
14. 引用（#396）。本轮没有的文档引用（`p3612.document.2`）和 chunk 引用算越界。产品 id 和占位符不算：它们走卡片和缺席规则，不把整轮换成降级句。
15. #440 规定句（`kind: signed`）。询盘开放、整站职责、天气，英德各一句：高置信误读仍走 `scripted`，正文是规定句，模型散文被换掉，没有邮箱。开放句的下一步是 `send_inquiry`；职责和天气是 application 询问。德语开放句不含 `Preis`、` nur `、`Konto`。ESA 电池问句盖上型号句，`3 kW` 不留下，正文含 `BAT-D-G2`。对照：比较 ESA、SAJ 的「哪个储能」、以及只有账户词没有询盘名词的句子，不走这两句。
