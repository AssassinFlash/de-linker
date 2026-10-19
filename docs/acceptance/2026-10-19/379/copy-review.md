# #379 产品词澄清文案 — 初稿（对抗评审未做）

规则：AGENTS.md §2（业主 2026-10-09 / 2026-10-11：客户可见文案走对抗评审；EN 先定稿，DE 独立撰写，Sie 体，不是翻译）、§3 用词（产品 / Produkt、型号 / Modell、系列 / Serie；不说 catalogue、article、cart；禁止「不是…而是…」与 AI 句式）、linker-copywriting Hard Stops 1–9。邮件主题属公开面；本组句子是对话兜底，不是邮件主题。

范围：`services/genie/src/linker_genie/template.py` 里本轮新增或改写的客户可见句（`_conflict_sentence`、`_range_sentence`、`_closest_sentence`、`_not_returned`、`_missed_sentences`、空搜索句、多型号引导句）。`DEGRADED` 已在 `docs/acceptance/2026-10-12/103/copy-review.md` 定稿，本轮不改。零件清单的 “not in our product range.” / “nicht in unserem Sortiment.” 属于 #251，本轮不改。

评审状态：**初稿而已。协调者的对抗评审还没有做。** 下文的清单是给那一轮用的，不是通过记录。定稿以协调者写回的意见为准，在那之前代码里的句子只是实现会话的草稿。

设计理由：dossier `docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md` §1.1、§1.11、§2 第 10 条——零结果澄清和品牌冲突没有竞品成句可抄，句子是本票自己写的。

## 英文初稿

冲突（一句里同时有客户写的品牌、型号、目录品牌和卡片）：

- `You wrote {written}; {code} is a {catalog} product, and the card shows it.`

不在产品数据里：

- `{code} is not in our product range.`
- `{code}, {code} are not in our product range.`

最近的产品、这次搜索没带回、这轮没搜、空搜索、多型号引导：

- `The closest products in our product data are on the cards.`
- `The search did not return {code}.`
- `{code} was not searched in this turn.`
- `No product matched that search.`
- `These are the products for the models in your message.`

## 德语初稿（独立撰写，Sie 体，不是上面英文的翻译）

- `Sie haben {written} genannt, {code} ist bei uns ein {catalog}-Produkt und steht auf der Karte.`
- `Für {code} haben wir kein Produkt.`（一个或多个型号共用这一句）
- `Auf den Karten liegen die nächsten Produkte derselben Reihe.`
- `Zu {code} lieferte die Suche kein Ergebnis.`
- `Nach {code} habe ich in dieser Runde nicht gesucht.`
- `In unseren Produkten gibt es dazu keinen Treffer.`
- `Die Karten gehören zu den Modellen, die Sie genannt haben.`

德语不沿用 #251 零件清单的 “nicht in unserem Sortiment.”。那句仍留在零件清单和接地检查的活动用语里，不是这组兜底句。

## 给协调者的核对清单

对抗评审逐句打勾。未打勾不等于初稿已通过。

- [ ] Hard Stop 1：没有借厂商声誉撑 Linker（`proven`、`tier-1`、`leading`）
- [ ] Hard Stop 2：没有把证书、协议、RMA 堆成卖点
- [ ] Hard Stop 3：没有「我们不是中间商」这类自我辩白
- [ ] Hard Stop 4：没有 `direct` / `official` / `guaranteed` 这类安抚词
- [ ] Hard Stop 5：没有编造的时效（24 小时、15 分钟）
- [ ] Hard Stop 6：没有 `Get help…`，也没有把活派给客户（`Tell us` / `Send us`）
- [ ] Hard Stop 7：公开面用词。邮件主题同样算公开面；确认这些句子不会被拿去当邮件主题
- [ ] Hard Stop 8：没有把接线、实验室验证写成卖点
- [ ] Hard Stop 9：Actor / Future / Weight / Duration 四项都过
- [ ] AGENTS.md §3：没有 catalogue、article、cart、Artikel、Katalog、Warenkorb
- [ ] 没有「不是…而是…」、没有 em dash、没有三连排比、没有 AI 收束句
- [ ] 德语是 Sie 体，并且不是英文的逐句翻译
- [ ] 一句冲突同时点出客户写的品牌和产品数据里的品牌（接地只认同一句）

## 留给协调者的问题

1. 英文冲突句用分号把两个品牌留在同一句里（接地只在 `.!?` 上断句）。分号是否要改成逗号？
2. `Für {codes} haben wir kein Produkt.` 在多个型号时仍用单数 “kein Produkt”。要不要改成复数？
3. `Nach {code} habe ich in dieser Runde nicht gesucht.` 用了第一人称。兜底的降级句也是第一人称；这里是否要改成不出现 “ich”？
4. `Auf den Karten liegen die nächsten Produkte derselben Reihe.` 里的 “derselben Reihe” 把后缀搜索说成同一系列。后缀不等于系列时，这句是否说重了？
5. `The closest products in our product data are on the cards.` 里的 “product data” 对客户是否太内部？
6. `No product matched that search.` / `In unseren Produkten gibt es dazu keinen Treffer.` 里的 “search” / “Treffer” 是否要改成只谈产品、不谈搜索？
7. 这组句子是对话兜底，不是邮件主题。若协调者把对话也视为 Hard Stop 7 的公开面，哪些词要再降一层？
