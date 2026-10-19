# #335 阅读记录

本地实例 `c335`，快照 `20261019-1715`，Genie `http://127.0.0.1:9192`，文档索引 `20261018T173840Z`。直连 `POST /turn`。没有发询盘、联系或邮件。`~/de-linker-local/c335/mail/` 跑前跑后都是空的。

证据在 `~/de-linker-data/campaign-335/`。`home-de/` 是德语首页补测（hreflang 属性顺序）。`address/` 是法律页补测（`impressum` 这个 slug 找到的是德语页，英文页在 `/imprint/`）。

计数：**16 通过 / 4 缺陷 / 1 备注 / 6 条只报告**。37 轮最近秩 p95 25.4 秒，最大 34.2 秒（T-sie 德语）。

## 通过

12 条本页建议与已审文案逐字一致：产品、分类、方案草稿、账户、博客、FAQ，英德各一。德语是 Sie，没有禁用词。

| 用例 | 结果 |
| --- | --- |
| T-pair | 通过。卡片都是 4107、1832、2067、2068、2069、2070、2090、2092。块都是 text、cards、四份 document |
| T-cost | 通过。两边卡片都是 4107。客人价格句是 Net price after partner sign-in / Nettopreis nach Partner-Anmeldung，没有金额 |
| T-mail | 通过（补测）。两边都是交接原句，邮箱都是 sales@de-linker.com，工具结果带 mailto:。两边都有 contact 块，邮件目录没有新文件 |
| T-ban | 通过。问句里的 basket、catalogue、article、Warenkorb、Katalog-Artikel 没有进入回答。两边都说 solution draft / Lösungsentwurf，卡片 4107，带 action |

Store API 上 SKU `DLK-SAJ-H210KT3`、型号 `H2-10K-T3`、标题里的 10，英德一致。德语相位词是 Dreiphasig。

## 备注

T-mppt。问的数字两边都是 3 个 MPPT、每路 2 串。德语多写了 180 V 到 900 V。document 块英语 3 份、德语 1 份。机械检查标了缺陷。按已问事实记备注。

T-pair 的英语散文列出 5、10、15、20、25 kWh，德语散文只写了 5。卡片集合相同。

## 缺陷

### 1. 英文法律页的地址被语言门丢掉

页 `http://127.0.0.1:9190/imprint/`，h1 Imprint。问 "What postal address does this page print?"

`linker/read-page` 已经读到 Linker Technology GmbH、Steinfeldstraße 3、39179 Barleben。`page_error` 为空。`fallback` 为真。失败原文：`answer in English (language=en): follow the customer's last message when it is clearly one language, otherwise the page locale`。

顾客看到的是：I could not answer this time. Please try again in a moment, or write to our team.

德语孪生 `http://127.0.0.1:9190/de/impressum/`，问 "Welche Postadresse steht auf dieser Seite?"，答出 Steinfeldstraße 3, 39179 Barleben, Deutschland。页上的 33824 是 HRB 33824，不是第二个邮编。

分层：读页成功；回答被语言门整段丢掉；兜底句没有地址。页文里的街道和 Geschäftsführer 是德语。

须自行设计。问句语言门是 #374 已经落地的规则。引用德语地址时回答怎样仍算英语，没有公开先例。

第一轮 `get_page_by_path('impressum')` 拿到的是德语页，英语问句打在 `/de/impressum/` 上，现象相同。上面这条是更正到 `/imprint/` 之后的复现。

### 2. 德语 du 诱饵被答成英语，兜底句没有事实

德语产品页。问 "Du, sag mir mal was zum SAJ H2-10K-T3."

route `products`。工具 `linker/search-products`、`linker/read-page`、`linker/get-product`。`fallback` 为真。失败原文：`answer in German (language=de): follow the customer's last message when it is clearly one language, otherwise the page locale`。

顾客看到的是：Hier sind passende Produkte aus unserem Sortiment. 加上 Nettopreis nach Partner-Anmeldung。卡片仍是 4107。回答里没有 du。

英语孪生 "Tell me about the SAJ H2-10K-T3." 写出 10 kW、3 路 MPPT、98.0%，以及随附的 eSolar AIO3、电表和说明书。

分层：模型把这句德语答成了英语；语言门丢掉整段；兜底句没有页面事实。Sie 守住了。这一轮 34.2 秒。

须自行设计。门是 #374。丢掉之后用空兜底，而不是用已经读到的页面重写一句德语，没有公开先例。

### 3. 产品标题改完，read-page 正文仍是旧的

编辑产品 4107。

改前：`SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)`

改后：`SAJ H2-10K-T3 C335DRIFT (10 kW three-phase hybrid inverter)`

匿名 GET：h1 仍是 `H2-10K-T3`。`data-page` 标题和三条开场建议都带 `C335DRIFT`。

立即问 "Quote this page's heading exactly." `linker/read-page` 正文前 800 字仍是旧副标题 `10 kW three-phase hybrid inverter`，没有 `C335DRIFT`。工具结果里的 `title` 是壳子刚传来的新标题，机械标签因此写成 `model-ignored-fresh-page`。按正文重判为 `stale-cache`。回答只引用了 h1：`H2-10K-T3`。

`just serve c335` 重启进程之后，正文变成 `C335DRIFT (10 kW three-phase hybrid inverter)`，回答引用了 `H2-10K-T3 C335DRIFT (10 kW three-phase hybrid inverter)`。

分层：`page.py` 的 `PageReader`，进程内缓存，键 `page:{path}`，TTL 600 秒。保存后没有失效。重启后下一次读取是新正文。本地没有 LiteSpeed。

须自行设计（dossier §1.2）。

### 4. 博客文末的新句子，同一缓存

博客 551，原文末尾加上：

```html
<p>C335DRIFT beacon sentence for the page drift test.</p>
```

匿名 GET 的 `<main>` 里有这句。问 "Quote the unusual token at the end of this post." 问句不含 `C335DRIFT`。

立即的 `linker/read-page` 没有这句。回答说文末没有异常记号。`stale-cache`。

重启后读到了这句。回答说 "What installers should verify" 末尾有一行测试句，并复述了 "beacon sentence for the page drift test"，把记号说成 label-like token，没有打出 `C335DRIFT`。新内容已经被读到。

同一层缓存。须自行设计（§1.2）。

`D-blog-warm` 在改文之前，`edit-not-rendered` 是预期读数。

## 翻译

`wp linker-i18n translate 4107 --now` 退出码 1。原文：`1 of 1 objects failed; previous German retained.`

德语产品 6628 的标题，命令前后都是 `SAJ H2-10K-T3 (10-kW-Dreiphasen-Hybrid-Wechselrichter)`。型号和 10 都在。`C335DRIFT` 没有进入德语页。两次德语提问都逐字引用了这条标题。

状态行在 WP-CLI 的 stdout。装具在失败时保留了 stderr，`structure_mismatch` 还是接口错误没有留下。恢复英文标题的那次保存把 meta 写成 `pending` / `queued`，失败状态被盖掉。

这条不记成 Genie 缓存缺陷。译后标题、参数、价格的核对，只覆盖了失败之后的保留，没有覆盖一次成功的重译。

## 语言（只报告，不开票）

规则按 #374：问句语言清楚时跟问句；混合或光一个型号时跟页面。

| 用例 | 回答语言 | 读到的内容 |
| --- | --- | --- |
| L-mixed，英语首页 | 英语 | 配对条件，B2 作为套装 |
| L-mixed，德语首页 | 德语 | 同一套配对条件 |
| L-switch-en，第二句改德语 | 德语 | 主跑：3 个 MPP-Tracker，每路 2 串。补测又跑了一次，只有 "Zu Ihrer Frage habe ich Folgendes gefunden." |
| L-switch-de，第二句改英语 | 英语 | 3 路 MPP，每路 2 串 |
| L-bare，英语首页，只发 H2-10K-T3 | 英语 | 10 kW，PV 20 kW |
| L-bare，德语首页 | 德语 | 10 kW，PV 20 kW，Lösungsentwurf |

混合问句没有单一语言。两边都按所在页面的语言回答。

## 编辑已经收回

英文标题收回为 `SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)`。德语标题仍是上面那条。博客 551 文末没有 `C335DRIFT`。

## 线上冒烟

只问句，然后删除对话。

| 探针 | HTTP | 秒 | 对话 | turn | 删除 | 最终 URL |
| --- | --- | --- | --- | --- | --- | --- |
| P-EN Which batteries pair with the SAJ H2-10K-T3? | 200 | 17.6 | 7566 | 217 | 200 | https://de-linker.com/wp-json/linker-ai/v1/genie/turn |
| P-DE Welche Batterien passen zum SAJ H2-10K-T3? | 200 | 20.0 | 7567 | 218 | 200 | 同上 |

响应头（两条都有，没有 `X-LiteSpeed-Cache`）：`Date` 分别为 Mon, 19 Oct 2026 15:45:35 GMT 和 15:45:58 GMT；`Server: LiteSpeed`；`X-Powered-By: PHP/8.3.35`；`Content-Type: application/json; charset=UTF-8`；`X-Robots-Tag: noindex`；`Link` 指向 `https://de-linker.com/wp-json/`。没有重定向。没有清生产缓存。

route 都是 `pairing`。块都是 text、cards、三份 document。客人价格句语言与问句一致。
