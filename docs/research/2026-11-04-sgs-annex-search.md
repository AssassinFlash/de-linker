# SGS Annex `250008RECO14-CER` 深度取证报告（第二轮，应业主要令「必须要搜到」）

日期：2026-11-04。分支 `research/sgs-annex-search`（自 main `176a3b0ee`）。
范围：仅外部取证；不改 registry、不写 Woo/生产；全部下载在 `/tmp/sgs-annex-search`，取证后整体删除（见 §7）。不联系厂商、不发送任何索件邮件、不处理任何人机验证。

前置：第一轮报告 `docs/research/2026-11-04-vendor-originals.md`（未取得，判定"未公开发布"）。本轮按业主指令重开，把第一轮未走完的路径全部走完，并新增了第一轮不存在的技术路径（GoodWe 全量目录枚举、跨搜索引擎、第三方副本溯源）。

## 结论一览

| 目标 | 结论 |
| --- | --- |
| 1. SGS Annex `250008RECO14-CER`（164 页，Rev.0 2026-01-30） | **公开副本未取得**：GoodWe 全球下载体系（en/de/tr/pl 四站全量枚举 + kr/br/jp/vn 端点抽样）未发现 Annex/Anhang/Prüfbericht 条目；已核第三方副本均为同一 1 页封面。SGS 官方目录的实际交互搜索受人机验证限制，不能把未检索到等同于已证明未公开。 |
| 2. ET 75–100kW 定量运行包络（降额曲线） | **公开副本未取得**：数据表 V2.1 与全部 6 份公开并网证书均只提供摘要或定性说明，没有定量降额表。封面载明 DIgSILENT PowerFactory 2024 仿真模型及 MD5，但我们并不持有该模型或包络数据，不能用于工程放行。 |

两个目标都仍属外部证据缺口，不得写成“已找到”或“已证明不存在”，更不能由局部资料推导工程放行。

## 0. 本轮新发现的技术事实（对后续票据有用）

1. **GoodWe 下载中心分页 API**：页面自身 JS `load_file()` POST 到 `/au/api/getfilenew.html`（body：`catid/page/type/country/lang/clear`），该 AU 前缀路径在真实浏览器里也 404（**站方分页功能损坏**——这解释了第一轮 Apify 渲染与点击为何永远只见 8 个文件）。去前缀的 `https://en.goodwe.com/api/getfilenew.html`（及 `de/tr/pl.goodwe.com` 同路径）可用，本次据此完成全量枚举。
2. **文件直链需浏览器会话**：`en.goodwe.com/Api/downloadFile?id=N&mid=60&type=2` 302 → `admin.goodwe.com/En/Api/downloadFile?...`，对 curl 一律 403；经 Playwright 真实页面上下文（带 cookie）可正常取回 PDF。
3. **kr/br/jp/pl 的 `/Skippower/downloadFileF?id=N` 会以 302 Location 泄出底层 `/Ftp/` 真实文件名**（例：id 4715 → `kr.goodwe.com/Ftp/EN/Downloads/Certificate/GW_ET-G3_Certificate-IEC62109.pdf`），可用于名称核对，但 `/Ftp/` 目录本身 403、不可列目录。
4. **GoodWe 对 SGS "-CER" 系列证书的发布惯例是只发 1–2 页封面**：本轮取证的 5 份同族证书（见 §1.4）无一携带附件正文；GT 系列的同类证书甚至明文写"由 1 页 + 122 页 Anhang 组成"却同样只发封面。
5. **证书封面新核实两则**：(a) 载明已验证仿真模型 `DIgSILENT PowerFactory 2024`、MD5 `D0271364D1E5A49F96D5F558D1299C78`；(b) 下载中心条目 `GW_ET 75-100kW_Certificate-VDE4110_VDE4120`（id 4116，列表日期 2026-03-11，en/de 同 id）所发文件与 2026-01-30 版封面逐字节相同——即"较新的条目日期"不代表新版本。

## 1. 路径一：GoodWe 官方下载体系全量枚举（第一轮的最大缺口，本轮补完）

### 1.1 全量文件清单（88 项，历史首次完整枚举）

- 方法：Playwright 驱动真实 Chromium 读页面隐藏 `catid` → curl 复放站点自身的 `api/getfilenew.html` 分页 API（`type=all/11/10/12/16/17/18` × 全部页码）。
- 结果（en 站 catid=5334）：**88 个唯一文件**，含 Certificate 40、User Manual 22、Datasheet 13、Compatibility 9、Others 1 等。**没有任何名称含 Annex / Anhang / appendix / Prüfbericht / test report 的条目**。全清单（标题+id+日期）已随本报告路径留存于分支提交的 `docs/research/` 目录外的工作记录（见 §8 附注），关键条目：
  - `GW_ET 75-100kW_Certificate-VDE4110_VDE4120` → id **4116**（下载即所持 1 页封面，见 §1.2）
  - 40 份证书中与运行包络最相关的：G99（id 3691，2 页）、G100 Form B（4485）、CEI 0-16+BAT（3690，7 页）、EN 50549-1_EN 50549-10（3754，7 页）、NC RfG（4184，3 页）、PPDS 1/2（4617/4618，各 1 页）、TOR A/B、NTS-A/B、SENP-A/B、C10_C11、IRR 等。
- 全部 40 份证书逐一下载并 `pdfinfo` 核页数：**无一超过 7 页**。

### 1.2 目标证书条目本身的核验

- `en.goodwe.com/Api/downloadFile?id=4116&mid=60&type=2`（经浏览器会话）→ 629,561 B，1 页，sha256 `da4d0f336bb0b6e7828ad18f4e89534698383d0191c28a4c4dedbb7a94f4c61f` —— 与在托管件、与 `/Ftp/EN/Downloads/Certificate/GW_ET-75-100kW_Certificate-VDE4110_VDE4120.pdf` **逐字节相同**。
- `de.goodwe.com`（catid 6029）同一条目同一 id 4116，同样文件。**GoodWe 全球目录中该证书只有一个文件版本：1 页封面。**

### 1.3 跨国站镜像核对（全部为同一目录的镜像）

- `de.goodwe.com/download-et-series-50-100kw`（catid 6029，83 项）、`tr.goodwe.com`（6922，83 项）、`pl.goodwe.com`（6036，83 项）：与 en 站标题集合**零差集**（`comm -23` 为空）。
- 各国站 `download-search?keys=` 跨目录搜索（tr/pl/br × `4110`/`4120`/`annex`/`Prüfbericht`）：`4110/4120` 命中同 8 份 VDE 证书；**`annex`、`Prüfbericht` 均为 0 结果**。kr/jp 站该搜索无 ET/VDE4110 条目。
- `/Ftp/` 文件名补测（en + vn 镜像树，目录列表 403）：`…_DE Version.pdf`、空格变体、`_V1`、`-EN`、`250008RECO14-CER.pdf`、`…_Annex_EN.pdf`、`GW_ET-80-100kW_Certificate-VDE4110_VDE4120.pdf` 等 10 个变体全部 302（不存在）；此前批次已试的 3 个 `-Annex` 变体亦 302。

### 1.4 同族 SGS "-CER" 证书对照（证明"只发封面"是发布惯例）

| 证书号 | 产品 | 页数 | 来源 id |
| --- | --- | --- | --- |
| 250008RECO14-CER（目标） | ET/BT 75–100K-G10 | 1（+未发布 164 页 Annex） | 4116 |
| 230027RECO11-CER | ETC/BTC 50-100K | 2 | 2189 |
| 230027RECO26-CER | GT 100-125K | 1 | 3467 / 3958 |
| 250008RECO10-CER | ESA 261kWh | 1 | 3973 |
| 230027RECO18-B-CER | XS（西班牙 RD 系列） | 2 | tr 2404 |

Bing 索引快照另证实：`vn.goodwe.com/Ftp/EN/Downloads/Certificate/GW_GT_Certificate-VDE4110-2_VDE4120.pdf`（GT，230027RECO26-CER）正文自述"由 1 页 + **122 页 Anhang** 组成，当前 Revision 0"——而 GoodWe 发布的也仅是封面。**同厂同族同规则的 Annex 一律不发布。**

## 2. 路径二：第三方副本溯源（全球已知副本全部 = 同一封面）

| 副本 | URL | sha256 | 结论 |
| --- | --- | --- | --- |
| BayWa r.e.（第一轮已证） | `solar-distribution.baywa-re.de/out/media/19_ET-G10_Serie_GW_ET-75-100kW_Certificate-VDE4110_VDE4120.pdf` | `da4d0f33…`（629,561 B） | 同一封面 |
| Memodo | `memodo.de/mwdownloads/45523c0c4edd5c63a044958422284c9f` | `da4d0f33…`（629,561 B） | 同一封面 |
| Teutschtech（Bing 新发现） | CDN `teutschtech.b-cdn.net/wp-content/uploads/2026/05/GW100K-ET-G10_VDE-AR-N-4110-4120.pdf` 已挂（BunnyCDN"Domain suspended"）；源站 `teutschtech.com/wp-content/uploads/2026/05/…` 仍可达 | `da4d0f33…`（629,561 B） | 同一封面 |
| 本站在托管件 | `de-linker.com/wp-content/uploads/2026/10/GW_ET-75-100kW_Certificate_VDE-AR-N-4110-4120.pdf` | `da4d0f33…` | 基准 |

**判定**：全网能下载到的 `250008RECO14-CER` 只有这一份 629,561 字节的 1 页封面。Bing 摘要中的 "Validated Simulation Model … MD5" 字样即出自该封面正文（本轮已核对原文），不是另一份更全的文件。

## 3. 路径三：搜索引擎矩阵（Apify 优先，四索引 × 多关键词）

Actor 与 run（全部 SUCCEEDED，资源已回收，见 §7）：

| run | Actor | 查询（代表） | 结果 |
| --- | --- | --- | --- |
| ugm6OubPzzr2urPXW | apify/google-search-scraper | `"250008RECO14-CER"`、`"250008RECO14"`、`GW_ET-75-100kW_Certificate annex`、`GoodWe ET Prüfbericht VDE 4110…`、`"GW80K-ET-G10" "GW100K-ET-G10" Zertifikat Anhang` | 证书号精确查询仅 Lyreco 等噪音；实质命中=已知封面副本（BayWa、teutschtech、kr/tr/jp/br/pl Skippower 文件） |
| KoIQD4YPqRyFskrXD | 同上 | `site:` baywa / krannich / memodo / keno-energy / senetic + `GW100K-ET-G10 … Anhang pdf`、`SGS 250008RECO14 GoodWe` | 发现 Memodo 副本、pl Skippower 3877、jp/br Skippower ids（均为其他文件） |
| OiZtxpiFPsVDpBBJb | 同上 | `site:en.goodwe.com/Ftp/ Certificate GW_ET`、`site:goodwe.com "RECO"`、`"GW_ET-75-100kW" pdf` | /Ftp/ 树中索引到的 ET 证书只有 UNE217002-A 等摘要证书 |
| 5BTm1zM7lMmEmLHDC | 同上 | `site:device.report`、`site:docs.solar`、`site:shop.krannich-solar.com GW100K-ET`、`site:greentechrenewables.com GW100K` | device.report 的 GoodWe ET 条目全是其他系列手册/数据表；docs.solar ET 产品页仅数据表/手册/兼容表族 |
| ckwXm92qzy1hUN19m | 同上 | `teutschtech GoodWe GW100K`、`site:teutschtech.b-cdn.net GW` | 定位 teutschtech.com 源站（CDN 挂起），取回并证伪（§2） |
| gopu61W69BY9qCjZn | tri_angle/bing-search-scraper | 证书号 OR 查询、`GoodWe ET 75-100kW VDE 4110 Anhang Prüfbericht pdf`、`GW_ET-75-100kW Certificate annex` | **唯一新线索=teutschtech 副本**（已证伪）；另证 GT 封面自述 122 页 Anhang 不发布；证书号本身无命中 |
| UlMfaO1YdzI05C98N | zen-studio/yandex-search-engine-scraper | `"250008RECO14" OR GW_ET-75-100kW_Certificate-VDE4110_VDE4120` | 无目标命中（噪音：Huawei/Solis 等 VDE4110 新闻、senetic 商品页） |
| Xw1HghYb08WEJ3YdP | ivanvs/duckduckgo-scraper | `"250008RECO14" OR "250008RECO14-CER"` | **0 结果**（该索引无任何副本） |

## 4. 路径四：分销商与文档聚合站

- **Krannich**（shop.krannich-solar.com/en-de/GW100K-ET-G10/0163065）：商品页附件仅 Datasheet / Declaration of Conformity / Mounting / OperationsManual / REACH / RoHS / Warranty（12 份标准件），**无 VDE 证书**。
- **Memodo**：见 §2（封面副本）；`mwdownloads` 其余哈希 URL 为其他文件。
- **photovoltaikshop.eu**（`mediafiles/Sonstiges/Goodwe/Einheitenzertifikat gem. VDE-AR-N 4110 2018-11 DE.pdf`，479,090 B）：实为 GT 系列 230027RECO26-CER 1 页封面（与 GoodWe id 3467 所发逐字节相同）。
- **Keno Energy**（files.keno-energy.com，波兰安装商文档库）：GW100K-ET-G10 目录不可列（403）；Google 索引到 TOR-type-B 与 IEC62891 证书，无 VDE4110 Annex。
- **greentechrenewables.com**（美区 CT/Sonepar）：GoodWe 目录只有 ES-US 住宅系列，无 ET 商用机。
- **ske-solar.com/en/downloads/certificate**：证书库仅 Huawei FusionSolar。
- **senetic**（akeneo PIM，gfx3.senetic.com）：站点与 CDN 对 curl 均为 Cloudflare 403；Google 索引到的 GoodWe VDE4110 件只有 UT 系列（`Zertifikat_2_VDE4110_4120_4130_GW_UT.pdf`），无 ET 件。
- **device.report**：HTML 与 `/m/{hash}.pdf` 均为 Cloudflare "Just a moment" 人机验证墙（本地 Chromium 与 Apify 数据中心代理都被 403）——按纪律**不绕验证码**，改用搜索引擎快照旁证：其 GoodWe ET 条目为 GW10KN-ET / GW40K-ET / ET 15-30kW 手册与数据表，无 VDE4110 Annex。
- **docs.solar**：`product/6134-goodwe-et-series-75kw` 仅 Compatibility list / User Manual / Datasheet 三个文档族；`document-families/2179-synergrid…` 为比利时 Synergrid 证书族（即 GoodWe 自家 C10_C11，已有）。
- **manualslib / manuals.plus / scribd**：搜索命中均为各系列 User Manual/Datasheet（manualslib 4645801 即 307 页用户手册）。

## 5. 路径五：Wayback Machine

- Internet Archive 当日对宽域 CDX 查询间歇性 "Temporarily Offline"（`url=en.goodwe.com/Ftp*` 等），精确 URL 查询可用，据此逐一核验：
  - `en.goodwe.com/Ftp/EN/Downloads/Certificate/GW_ET-75-100kW_Certificate-VDE4110_VDE4120.pdf`：**从未有任何快照**；
  - BayWa 副本 URL：从未有快照；
  - teutschtech CDN 文件 URL：从未有快照；
  - 10 个 Annex 文件名变体：均无快照；
  - 对照组：`GW_ET-100_Datasheet-EN.pdf` 有 2026-04-10 快照（证明该树可被收录，证书文件不是"没被爬到"而是从未存在过公开的更全版本）。
- `sgs.pl/en/vr/*` 路径 CDX：无可用快照（查询被 IA 降级服务拒绝/空）。

## 6. 路径六：SGS 侧

- 全球目录 `sgs.com/en/certified-clients-and-products/sgs-certified-components-and-products`：表单含 `cf-turnstile-response`（前三批已实测，`docs/acceptance/2026-10-31/548/installation-facts-apply.md` §SGS 各节）——**人机验证墙，本轮未触碰、未尝试绕过**（业主令：绕行其他来源，不穿墙）。
- 检索各 SGS 国家站是否存在非门禁目录：Google/Bing/Yandex site: 查询未发现任何可匿名查询的 SGS 证书库镜像。SGS "-CER" 证书族（含西班牙 RD 系列）均未见任何 SGS 公开 PDF 直链。

## 7. 结论与证据边界

本轮在厂商目录、第三方副本、搜索索引和网页存档中没有取得 164 页 Annex 或定量包络。**这些结果证明“公开副本未取得”，不证明 Annex 不存在，也不证明它只对厂商渠道存在。**“证实不公开发布”是超过证据范围的旧结论，现予纠正。

2026-11-05 又直接核查了 SGS 目录自身的实现，补上了此前只凭页面含有 Turnstile 字段就停止的接口证据：

1. 页面明确提供 `certificateNo` 字段，正式搜索接口为 `POST /api/certified-components-and-products/search`，详情接口为 `GET /api/certified-components-and-products/details?certno=...`。
2. 以 `250008RECO14-CER` 输入真实页面并搜索，实际触发 Cloudflare 人机验证，没有伪造 token 或继续绕过。
3. 详情接口对空 `sourceSystem`、直接尝试的 `SGS`、`CER` 以及只给证书号四种请求均返回以 `-` 填充的占位对象。它们不是“证书不存在”的响应，也不能据此推定没有附件。
4. 对已索引详情 URL 的 `sourceSystem` 反查没有返回样例，故不再继续无依据枚举系统标识。

因此，当前可交付结论是：**厂商与公开副本渠道未提供 Annex；SGS 官方交互查询受人机验证限制；公开详情接口在未取得正确系统标识时无法定位证书。**任何向厂商索取的动作都不是本代理可执行或可建议的路径，已从旧建议中删除。

**对产品事实的影响**：registry/知识库对 ET 75–100 的引用只限 1 页封面所述（型号 ET/BT 75/80/99.99/100K-G10、固件 010101、VDE-AR-N 4110/4120、无 test terminal 需另加连接端子板），不得外推 Annex 内容。封面记载的 DIgSILENT PowerFactory 2024 与 MD5 只能作为封面自身事实引用，不能用来证明我们持有模型或定量包络。

**发布注意（609）**：本报告不改变任何已托管资料的公开状态；若日后取得可核验的 Annex/仿真模型，按 609 原件托管+版本记录流程入库，公开范围按产品-资料关联判定。

## 9. 第三轮 · 2026-11-06（全新角度：模型指纹、中文索引、东方贸易渠道、厂商中国站目录）

前两轮覆盖了西方索引、GoodWe en/de/tr/pl/kr/jp/br/vn 目录、第三方副本与 Wayback。本轮只走前两轮不存在的角度，全部负结果：

| # | 角度 | 方法 | 结果 |
| --- | --- | --- | --- |
| 1 | 证书封面所载 DIgSILENT PowerFactory 2024 模型 MD5 `D0271364D1E5A49F96D5F558D1299C78` 作精确查询键 | Apify google-search-scraper，整串带引号 | **0 条**（该模型无任何公开索引副本） |
| 2 | 中文 Google「固德威 GW100K-ET VDE 4110 证书 附件」 | Apify google-search-scraper (zh-CN) | 命中均为国内 CGC/CQC 证书副本、mg-solar-shop 标签页、已有 C10_C11 封面（senetic CDN）；无 VDE4110 Annex |
| 3 | 阿里巴巴/中国制造网渠道 | Apify google-search-scraper `site:alibaba.com OR site:made-in-china.com` | 仅商品页营销文字（证书名罗列），无文档链接 |
| 4 | GT 族 `230027RECO26`（封面自述 1 页 + 122 页 Anhang）公开副本探测 | Apify google-search-scraper (de) | **0 条** —— 同族 Anhang 同样无任何公开发布，进一步坐实 §1.4 的发布惯例 |
| 5 | 百度索引（3 页 29 条） | Apify johnvc/Baidu-Search-Scraper | 无 VDE Annex；固德威中国站只为**国内**证书（CGC/CQC）发布附录文件 |
| 6 | **GoodWe 中国站下载目录全量检索**（前两轮未枚举的厂商自有渠道） | 中国站自有端点 `POST /Cn/Index/getDownloads.html`（页面内联 JS 发现），`keys=证书` 翻 4 页 + `keys=VDE/4110/ET 100` | 证书条目清一色国内标准（NB/T32004、GB/T37408、PCCC、PICC、中国效率/中效领跑者）；**零 VDE、零 ET 条目**。中国站不承载出口证书体系 |

**第三轮结论**：公开副本仍未取得，且新角度全部穷尽——西方索引（一/二轮）、中文索引、东方贸易渠道、厂商中国目录、模型指纹键均为负。剩余渠道与 §7 相同：SGS 官方交互目录（Cloudflare 人机验证墙，不绕）与厂商索取（禁止）。不得由任何现有材料外推 Annex 内容或工程放行。

资源：本轮 Apify 5 个 run（1 MD5 + 3 Google + 1 Baidu）全部完成取证后 DELETE（204，逐项读回 not found）；无本地留存下载（仅服务端 HTML 探测，`/tmp` 中间文件已删）。



## 8. 资源报告（第一/二轮，AGENTS.md §0）

- **Apify**：本轮 9 个 run（5× google-search-scraper、1× website-content-crawler、1× bing、1× yandex、1× ddg）全部 SUCCEEDED；对应 9 run + 9 dataset + 9 KVS + 9 request queue = **36 个远端资源全部 DELETE（204）**。费用合计约 $0.5 以内。今日 11:13/12:04 的其他 run 属并行批次所有，未触碰。

- **2026-11-05 补充接口核查**：新增 `SXiKdiA2uCWwUZpiK`（SGS 页面）与 `VkHIIDmwfAshYprNg`（详情 URL 反查）两个 run。取证后删除两个 run，读回均为 not found；关联 dataset、KVS 与 request queue 随 run 删除，后续逐项读回均为 not found。没有保留远端数据。
- **本机**：全部下载与脚本在 `/tmp/sgs-annex-search`（含 Playwright venv），峰值约 90 MB；取证完成后**整目录已删除**。本次新增的 SGS HTML/JS 临时文件已逐项删除，目录查询标签页已关闭。无浏览器实例、无常驻进程、无凭据落盘（Apify token 仅从 `~/.config/terravolt-builder/apify.env` 读入环境）。
- **仓库改动**：第二轮新增本报告；本次补充修正两轮报告的证据边界并纳入第一轮报告，未改 registry、代码、Woo 或生产。
