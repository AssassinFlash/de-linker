# #379 产品词澄清文案 — 待协调者对抗评审

规则：AGENTS.md §2（业主 2026-10-09 / 2026-10-11：客户可见文案走对抗评审；EN 先定稿，DE 独立撰写，Sie 体，不是翻译）、§3 用词（产品 / Produkt、型号 / Modell、系列 / Serie；不说 catalogue、article、cart；禁止「不是…而是…」与 AI 句式）、linker-copywriting Hard Stops 1–9。邮件主题属公开面；本组句子是对话兜底，不是邮件主题。

范围：`services/genie/src/linker_genie/template.py` 的七组句子（冲突、不在范围内、最近的产品、搜索没有带回、这轮没搜、没有匹配、多型号引导）。`DEGRADED` 已在 `docs/acceptance/2026-10-12/103/copy-review.md` 定稿，本轮不改。零件清单的 “not in our product range.” / “nicht in unserem Sortiment.” 属于 #251，本轮不改写零件清单；这两句仍是接地检查里的活动用语。

状态：下面的英文和德文是本轮写进代码的句子，核对清单是这一轮的判断。协调者的对抗评审还没有做。在协调者写回之前，不能把这篇当成已通过的评审。

设计理由：dossier `docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md` §1.1、§1.11、§2 第 10 条——零结果澄清和品牌冲突没有竞品成句可抄，句子是本票自己写的。

Coordinator sign-off: pending

## 英文

冲突。一句里同时有客户写的品牌和产品数据里的品牌，卡片上有该产品。型号可以出现在这一句里，也可以出现在别的句子里。分号不断句（接地在 `.!?` 上断句），所以两个品牌留在同一句。

- `You wrote {written}; {code} is a {catalog} product, and the card shows it.`

不在产品范围内。一个型号用 is，多个型号用 are。沿用 #251 的 “not in our product range”，不另造一套说法。

- `{code} is not in our product range.`
- `{code}, {code} are not in our product range.`

最近的产品。只说这次搜索带回的下一批产品，不说它们属于同一系列。

- `The closest products are on the cards.`

这次搜索没有带回该型号。只在这次搜索成功、并且没有带回该型号时使用。搜索失败时用已定稿的降级句或邮箱句，不用这一句。

- `The search did not return {code}.`

这轮没有搜。

- `{code} was not searched in this turn.`

没有匹配。谈产品，不谈 “search”。

- `No product matched.`

多型号引导。

- `These are the products for the models in your message.`

## 德文

独立撰写，Sie 体，不是上面英文的逐句对译。系列只在搜索本身确立了系列时才用 “Serie”；这七句里没有一处用 “Reihe”，也没有一处声称同一系列。

冲突。一个句子里同时有客户写的品牌、卡片和产品数据里的品牌。不用 “führen wir nicht”（那是缺失用语）。

- `Sie haben {written} angegeben; die Karte zeigt {code} als {catalog}-Produkt.`

不在产品范围内。一个型号用单数，多个型号用复数。

- `Für {code} haben wir kein Produkt.`
- `Für {code}, {code} haben wir keine Produkte.`

最近的产品。说的是这次搜索带回的下一批产品。

- `Die Karten zeigen die nächsten Produkte dieser Suche.`

这次搜索没有带回该型号。

- `Die Suche hat zu {code} kein Produkt geliefert.`

这轮没有搜。不出现 “ich”。降级句仍是已定稿的第一人称，这里不跟着改。

- `{code} wurde in dieser Runde nicht gesucht.`

没有匹配。

- `Dazu haben wir kein passendes Produkt.`

多型号引导。

- `Die Karten gehören zu den Modellen, die Sie genannt haben.`

德语不沿用 #251 零件清单的 “nicht in unserem Sortiment.”。那句仍留在零件清单和接地检查的活动用语里，不是这组兜底句。

## 核对清单

这一轮的判断写在每条后面。未签收不等于这些句子已通过对抗评审。

- Hard Stop 1：通过。没有 `proven`、`tier-1`、`leading`。
- Hard Stop 2：通过。没有把证书、协议、RMA 堆成卖点。
- Hard Stop 3：通过。没有「我们不是中间商」。
- Hard Stop 4：通过。没有 `direct` / `official` / `guaranteed`。
- Hard Stop 5：通过。没有编造的时效。
- Hard Stop 6：通过。没有 `Get help…`，也没有 `Tell us` / `Send us`。
- Hard Stop 7：这七句是对话兜底，不是邮件主题。本轮不把它们放进邮件主题。公开面用词按 §3 核过：没有 catalogue、article、cart。
- Hard Stop 8：通过。没有把接线或实验室验证写成卖点。
- Hard Stop 9：通过。没有 Actor、Future、Weight、Duration 的写法。
- AGENTS.md §3：通过。没有 catalogue、article、cart、Artikel、Katalog、Warenkorb。德文用 Produkt、Modell；系列一词没有出现，因为这组句子并不确立系列。
- 句式：通过。没有「不是…而是…」，没有 em dash，没有三连排比，没有收束句。
- 德语：通过这一轮的自查。Sie 体，冲突句、范围句、最近产品句、没搜句都不是英文的逐句对译。
- 冲突句：通过这一轮的自查。同一句里有客户写的品牌和产品数据里的品牌，卡片上有该产品。型号可以不在这一句里；兜底句仍把型号写在这一句里。

## 本轮对原先问题的处理

1. 英文冲突句保留分号。逗号同样不会被 `.!?` 断开；分号把两个品牌留在顾客读得开的一句里。接地认的是同一句里的两个品牌和卡片上的产品，不再要求型号也在这一句里。
2. 德语范围句按个数分开：一个型号 “kein Produkt”，多个型号 “keine Produkte”。
3. 没搜的德语句去掉 “ich”。降级句的第一人称是已定稿的，不改。
4. 最近产品的德语句去掉 “Reihe”，也不说同一系列。英文去掉 “product data”。两边都只说这次搜索带回的下一批产品。
5. “product data” 不再出现在最近产品这句里。冲突的提示仍对模型说 product data；那句是给模型的英文提示，不是这七句。
6. 没有匹配改为只谈产品：`No product matched.` / `Dazu haben wir kein passendes Produkt.`
7. 这七句留在对话兜底里，不作为邮件主题。

协调者若要改字，改 `template.py` 里的这七句，并改这篇记录。`DEGRADED` 不在此列。
