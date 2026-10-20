# #415 库存问句 · 视觉验收（2026-10-20）

实例 `c415`（本分支 `fix/415-stock-answer`，快照 `20261019-1715`，http://127.0.0.1:9208）。`just serve c415` 的 Genie 是本工作树（127.0.0.1:9211）。Playwright 用 `tests/e2e` 的 Chromium，问句经页面自己的 `linker-genie-ask` 发出。视口 1440×900 与 390×844。英语页是 `/`（`data-locale=en`），德语页是 `/de/`（`data-locale=de`）。拍照前点掉 Cookie 横幅的 Reject all / Alle ablehnen，横幅不是任何状态的一部分。

## 截图

| 文件 | 状态 |
|---|---|
| `stock-1440-en-in-stock.png` | EN 首页 1440。问句 “What is the stock status of the SAJ H2-10K-T3?”。卡片徽标 In stock（`linker-card__badge--ok`），商品 SAJ H2-10K-T3 |
| `stock-390-en-in-stock.png` | EN 首页 390。同一问句。徽标 In stock。状态句 “In stock” 与徽标同在画面里 |
| `stock-1440-de-in-stock.png` | DE 首页 1440。问句 “Wie ist der Lagerstatus des SAJ H2-10K-T3?”。徽标 Auf Lager。标题是德语商品名 |
| `stock-390-de-in-stock.png` | DE 首页 390。同一问句。徽标 Auf Lager。状态句 “Auf Lager” 与徽标同在画面里 |
| `stock-1440-en-unavailable.png` | EN 首页 1440。问句 “What is the stock status of the GoodWe GW60K-STS-G10?”。徽标 Currently unavailable（`linker-card__badge--warn`） |
| `stock-390-en-unavailable.png` | EN 首页 390。同一问句。徽标 Currently unavailable。状态句与徽标同在画面里 |
| `stock-1440-de-unavailable.png` | DE 首页 1440。问句 “Wie ist der Lagerstatus des GoodWe GW60K-STS-G10?”。徽标 Derzeit nicht verfügbar |
| `stock-390-de-unavailable.png` | DE 首页 390。同一问句。徽标 Derzeit nicht verfügbar。状态句与徽标同在画面里 |
| `which-product-1440-en.png` | EN 首页 1440。问句 “What do you have in stock?”。回答 “Which product should I check the stock for?”，无卡片 |
| `which-product-390-en.png` | EN 首页 390。同一问句。整句在画面里，无卡片 |
| `which-product-1440-de.png` | DE 首页 1440。问句 “Welche Produkte sind auf Lager?”。回答 “Für welches Produkt soll ich den Lagerstatus prüfen?”，无卡片 |
| `which-product-390-de.png` | DE 首页 390。同一问句。整句在画面里，无卡片 |
| `mixed-status-1440-en.png` | EN 首页 1440。问句 “Are the GoodWe STS 30-60K in stock?”。状态句 “Some of these products are in stock and some are currently unavailable.”，第一张卡徽标 In stock，第二张卡的 Currently unavailable 徽标在同一次答案里（拍后读回两张徽标：In stock、Currently unavailable） |
| `mixed-status-390-en.png` | EN 首页 390。同一问句。状态句、第一张卡与第二张卡开头同在画面里 |
| `mixed-status-1440-de.png` | DE 首页 1440。问句 “Sind die GoodWe STS 30-60K auf Lager?”。状态句 “Einige dieser Produkte sind auf Lager, andere derzeit nicht verfügbar.”；徽标 Auf Lager、Derzeit nicht verfügbar |
| `mixed-status-390-de.png` | DE 首页 390。同一问句。状态句、第一张卡与第二张卡开头同在画面里 |
| `degraded-1440-en.png` | EN 首页 1440。问句 “Are the SAJ HS3 accessories in stock?”。回答 degraded 句 “I could not answer this time. Please try again in a moment, or write to our team.”，无卡片 |
| `degraded-390-en.png` | EN 首页 390。同一问句。整句在画面里，无卡片 |
| `degraded-1440-de.png` | DE 首页 1440。问句 “Sind die SAJ HS3 Zubehör auf Lager?”。回答 “Ich konnte Ihre Frage diesmal nicht beantworten. Bitte versuchen Sie es gleich noch einmal, oder wenden Sie sich an unser Team.”，无卡片 |
| `degraded-390-de.png` | DE 首页 390。同一问句。整句在画面里，无卡片 |

1440 的停靠面板只滚到第一张卡徽标进画面，状态句留在画面里。390 的底栏同时容纳状态句和卡片。

## 无货与混合状态的数据来源

快照里抽到的已发布商品都是 instock，包括 SAJ H2-10K-T3（4107 / 德语 6628）。拍照前把 GoodWe GW60K-STS-G10（6530）设为 outofstock；德语商品 6565 由 `Linker\I18n\Woo\Projection` 在英文商品保存时同步。八张状态图与混合图拍完后设回 instock，`woocommerce_hide_out_of_stock_items` 读回 yes。

`WooOptions` 把 `woocommerce_hide_out_of_stock_items` 钉成 yes，Store API 商品集合因此排除 `stock_status = outofstock`。本轮无货与混合截图**没有替换任何响应**：拍照期间只在实例里加了 `zz-415-capture-unpin.php`（实例私有，不入仓库），以优先级 20 覆盖 `pre_option_woocommerce_hide_out_of_stock_items` 返回 `no`，让页面自己的 `wc/store/v1/products?include=…` 与搜索都取到真实商品；拍完删除该文件。截图里卡片的徽标与文案均来自应用自己的 Store API 响应。

混合状态用 GoodWe STS 30-60K 系列：6530 无货、GW30K-STS-G10（6529）有货，同一个搜索返回两张不同状态的卡。降级状态走真实可达路径：问 “SAJ HS3 accessories” 时 series + device_class 过滤没有命中任何商品，服务对空的成功搜索答 degraded 句（不答 “No product matched.”）。

文案定稿在同目录 `copy-review.md`。
