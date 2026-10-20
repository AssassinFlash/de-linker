# #335 阅读记录

本地实例 `c335`，快照 `20261019-1715`，Genie `http://127.0.0.1:9192`，文档索引 `20261018T173840Z`。直连 `POST /turn`。没有发询盘、联系或邮件。`~/de-linker-local/c335/mail/` 跑前跑后都是空的。

证据在 `~/de-linker-data/campaign-335/`。`home-de/` 是德语首页补测（hreflang 属性顺序）。`address/` 是法律页补测（`impressum` 这个 slug 找到的是德语页，英文页在 `/imprint/`）。

计数：**15 通过 / 5 缺陷 / 2 备注**。主跑 `language.jsonl` 是 3 条，都是英语首页（L-mixed-en、L-switch-en、L-bare-en），只报告，都通过。德语首页的语言行在 `home-de/language.jsonl`，不在这 3 条里。home-de 补测的 L-switch-en 是兜底句，按门 5 另记一条只报告的缺陷，不进入这 5 条。37 轮最近秩 p95 25.4 秒，最大 34.2 秒（T-sie 德语）。

`~/de-linker-data/campaign-335/` 里 2026-10-19 的 `summary.json` 保持原样。下面几处和那份文件不一致：T-mppt、T-pair 的机械结果，产品标题的漂移归因，T-address 里的邮箱和 33824，discover.json 的 `plz` 把 HRB 33824 算进邮编，补测 L-switch-en 的通过，T-sie 的通过。T-sie 德语轮 `fallback` 为真，那份文件仍写通过。装具现在把兜底记成缺陷。装具按这次重判来跑，不回写那批证据。

## 通过

12 条本页建议与已审文案逐字一致：产品、分类、方案草稿、账户、博客、FAQ，英德各一。德语是 Sie，没有禁用词。

| 用例 | 结果 |
| --- | --- |
| T-cost | 通过。两边卡片都是 4107。客人价格句是 Net price after partner sign-in / Nettopreis nach Partner-Anmeldung，没有金额 |
| T-mail | 通过（补测）。两边都是交接原句，邮箱都是 sales@de-linker.com。`Handoff.tsx` 只渲染 `block.summary`，顾客看到的是这两句，没有 mailto 链接。工具结果里的 mailto 不是这个链接。两边都有 contact 块，邮件目录没有新文件 |
| T-ban | 通过。问句里的 basket、catalogue、article、Warenkorb、Katalog-Artikel 没有进入回答。两边都说 solution draft / Lösungsentwurf，卡片 4107，带 action |

Store API 上 SKU `DLK-SAJ-H210KT3`、型号 `H2-10K-T3`、标题里的 10，英德一致。德语相位词是 Dreiphasig。

## 备注

T-mppt。问的数字两边都是 3 个 MPPT、每路 2 串。德语多写了 180 V 到 900 V。document 块英语 3 份、德语 1 份。机械结果是 `note`：共用的 3 和 2 一致，多出来的电压和文档份数写在 `notes` 里。

T-pair。卡片都是 4107、1832、2067、2068、2069、2070、2090、2092。块都是 text、cards、四份 document。`expect_numbers` 为真。英语散文列出 5、10、15、20、25 kWh，德语散文只写了 5。共用的 5 两边都有，英语多出的档位记为 `note`，离开通过列。

## 缺陷

### 1. 英文法律页的地址被语言门丢掉

页 `http://127.0.0.1:9190/imprint/`，h1 Imprint。问 "What postal address does this page print?"

`linker/read-page` 已经读到 Linker Technology GmbH、Steinfeldstraße 3、39179 Barleben。`page_error` 为空。`fallback` 为真。失败原文：`answer in English (language=en): follow the customer's last message when it is clearly one language, otherwise the page locale`。

顾客看到的是：I could not answer this time. Please try again in a moment, or write to our team.

德语孪生 `http://127.0.0.1:9190/de/impressum/`，问 "Welche Postadresse steht auf dieser Seite?"，答出 Steinfeldstraße 3, 39179 Barleben, Deutschland。页上的 33824 是 HRB 33824。问的是邮寄地址，装具核对邮编和紧随其后的地名，两样都要在答句里。`39179 Atlantis` 对不上 `39179 Barleben`。页上的邮箱和 HRB 33824 不在核对里。英语这边的缺陷是语言门把整段丢掉，答句里没有 39179。

分层：读页成功；回答被语言门整段丢掉；兜底句没有地址。页文里的街道和 Geschäftsführer 是德语。

须自行设计。问句语言门是 #374 已经落地的规则。引用德语地址时回答怎样仍算英语，没有公开先例。

第一轮 `get_page_by_path('impressum')` 拿到的是德语页，英语问句打在 `/de/impressum/` 上，现象相同。上面这条是更正到 `/imprint/` 之后的复现。

### 2. 德语 du 诱饵被答成英语，兜底句没有事实

德语产品页。问 "Du, sag mir mal was zum SAJ H2-10K-T3."

route `products`。工具 `linker/search-products`、`linker/read-page`、`linker/get-product`。`fallback` 为真。失败原文：`answer in German (language=de): follow the customer's last message when it is clearly one language, otherwise the page locale`。

顾客看到的是：Hier sind passende Produkte aus unserem Sortiment. 加上 Nettopreis nach Partner-Anmeldung。卡片仍是 4107。回答里没有 du。

英语孪生 "Tell me about the SAJ H2-10K-T3." 写出 10 kW、3 路 MPPT、98.0%，以及随附的 eSolar AIO3、电表和说明书。

分层：模型把这句德语答成了英语；语言门丢掉整段；兜底句没有页面事实。Sie 守住了。这一轮 34.2 秒。2026-10-19 的 summary.json 把 T-sie 写成通过，因为当时的机械结果不读 `meta.fallback`。装具现在把这一侧的兜底记成缺陷。

须自行设计。门是 #374。丢掉之后用空兜底，而不是用已经读到的页面重写一句德语，没有公开先例。

### 3. 产品标题改完，read-page 正文仍是旧的

编辑产品 4107。

改前：`SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)`

改后：`SAJ H2-10K-T3 C335DRIFT (10 kW three-phase hybrid inverter)`

匿名 GET：h1 仍是 `H2-10K-T3`。`data-page` 标题和三条开场建议都带 `C335DRIFT`。

立即问 "Quote this page's heading exactly." `linker/read-page` 正文前 800 字仍是旧副标题 `10 kW three-phase hybrid inverter`，没有 `C335DRIFT`。工具结果里的 `title` 是壳子刚传来的新标题。当时的机械标签把这个 `title` 也算进正文，写成 `model-ignored-fresh-page`，`title-fresh-body-stale` 因此到不了。装具现在只看 `result.text`。按正文重判，这一轮是 `stale-cache`：正文没有记号，回答也没有。回答只引用了 h1：`H2-10K-T3`。

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

重启后读到了这句。记号在正文里，过了前 800 字。回答说 "What installers should verify" 末尾有一行测试句，并复述了 "beacon sentence for the page drift test"，把记号说成 label-like token，没有打出 `C335DRIFT`。按正文归因仍是 `model-ignored-fresh-page`。新内容已经被读到。

同一层缓存。须自行设计（§1.2）。

`D-blog-warm` 在改文之前，`edit-not-rendered` 是预期读数。

## 翻译

`wp linker-i18n translate 4107 --now` 退出码 1。原文：`1 of 1 objects failed; previous German retained.`

德语产品 6628 的标题，命令前后都是 `SAJ H2-10K-T3 (10-kW-Dreiphasen-Hybrid-Wechselrichter)`。型号和 10 都在。`C335DRIFT` 没有进入德语页。两次德语提问都逐字引用了这条标题。

状态行在 WP-CLI 的 stdout。装具在失败时保留了 stderr，`structure_mismatch` 还是接口错误没有留下。恢复英文标题的那次保存把 meta 写成 `pending` / `queued`，失败状态被盖掉。

这条不记成 Genie 缓存缺陷。它是本批第 5 条缺陷，归到 #406。#406 仍开着，没有合进 main，这次没有重跑 `wp linker-i18n translate`。失败时 `grade_translation` 记 `measured: false`，并写明成功重译后的德语标题、属性数字和价格没有测到。成功路径（记号留在德语标题、标题数字与英语一致、属性数字、商店价格字段）由装具单测覆盖。商店价格要有非空金额才算测到；客人价为 null，或商店接口返回的带 `error` 的对象，都不算测到价格。2026-10-19 这次只测到失败之后保留的德语标题。

## 语言（只报告，不开票）

规则按 #374：问句语言清楚时跟问句；混合或光一个型号时跟页面。主跑 `language.jsonl` 只有英语首页 3 条。下表德语首页各行来自 `home-de/language.jsonl`。

| 用例 | 回答语言 | 读到的内容 |
| --- | --- | --- |
| L-mixed，英语首页（主跑） | 英语 | 配对条件，B2 作为套装 |
| L-mixed，德语首页（home-de） | 德语 | 同一套配对条件 |
| L-switch-en，第二句改德语 | 德语 | 主跑：3 个 MPP-Tracker，每路 2 串，通过。补测（home-de）`fallback` 为真，答句是 "Zu Ihrer Frage habe ich Folgendes gefunden."，模型原文含数字。门 5（`docs/specs/13-genie.md`）下兜底不算通过。机械结果是缺陷，`report_only` 仍为真 |
| L-switch-de，第二句改英语（home-de） | 英语 | 3 路 MPP，每路 2 串 |
| L-bare，英语首页，只发 H2-10K-T3（主跑） | 英语 | 10 kW，PV 20 kW |
| L-bare，德语首页（home-de） | 德语 | 10 kW，PV 20 kW，Lösungsentwurf |

混合问句没有单一语言。两边都按所在页面的语言回答。

## 编辑已经收回

英文标题收回为 `SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)`。德语标题仍是上面那条。博客 551 文末没有 `C335DRIFT`。

装具在改标题之前把原文写入 `title-original-<id>.txt`，博客正文写入 `blog-original.html`，恢复读这些文件。写回用 `wp_update_post` 的 WP_Error：返回错误，或没有写回这篇，eval 以 1 退出。一个字段写回失败时，后面的字段继续写回，每条失败都写入 `restore_error`。恢复之后再读标题、德语标题和博客正文，和快照不一致时 `restored` 不是真。邮件目录有新增，漂移阶段跑过而标题和快照不一致，或没有英语产品可改，进程退出码为 1。没有英语产品时没有编辑，也没有恢复。

## 线上冒烟

只问句，然后删除对话。

| 探针 | HTTP | 秒 | 对话 | turn | 删除 | 最终 URL |
| --- | --- | --- | --- | --- | --- | --- |
| P-EN Which batteries pair with the SAJ H2-10K-T3? | 200 | 17.6 | 7566 | 217 | 200 | https://de-linker.com/wp-json/linker-ai/v1/genie/turn |
| P-DE Welche Batterien passen zum SAJ H2-10K-T3? | 200 | 20.0 | 7567 | 218 | 200 | 同上 |

响应头（两条都有，没有 `X-LiteSpeed-Cache`）：`Date` 分别为 Mon, 19 Oct 2026 15:45:35 GMT 和 15:45:58 GMT；`Server: LiteSpeed`；`X-Powered-By: PHP/8.3.35`；`Content-Type: application/json; charset=UTF-8`；`X-Robots-Tag: noindex`；`Link` 指向 `https://de-linker.com/wp-json/`。没有重定向。没有清生产缓存。

route 都是 `pairing`。块都是 text、cards、三份 document。客人价格句语言与问句一致。

装具在每个跳转之后再看主机。307 和 308 会把 POST 原样带过去。目标主机是 `de-linker.com` 或 `www.de-linker.com` 时，没有 `--confirm-production` 就不跟随。最终 URL 的主机再查一次。这次记录的两条没有重定向。
