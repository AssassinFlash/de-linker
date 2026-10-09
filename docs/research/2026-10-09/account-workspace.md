# 客户账户「工作台」：竞品映射、术语、WooCommerce 11 可行性与建议

- 日期：2026-10-09（AFK 研究，只读；未改代码、未动生产）
- 现状背景：链尖 `refs/landed/chain-tip` = `f007a9dd` 的账户门户，仅作背景，不作为"正确"的依据
- 外部检索：全部经 Apify（见 §1）；每条外部断言附 URL 与日期（页面自带的发布/更新日期；没有则写抓取日 2026-10-09）

---

## 0 结论（先读这一节）

业主的描述是：「账户是工作台：资料、产品文件、选型输出、Proforma；没有订单/支付概念；网站是询价站、以 Proforma 呈现；Woo 后台生成 Proforma/发票，之后什么都没有。」

**判定：方向成立，但有四处要改。**

1. **"没有在线支付"成立；"PI 之后没有任何状态"不成立。**
   - 在线支付不是 PV 批发的标配。Krannich 的 ALB 写明发货原则上只凭预付款转账；Memodo 只有两种付款方式：Vorkasse 和带信用额度的账期发票（§2.1）。
   - 但 9 家对标里有 8 家（其中 3 家是间接证据）在账户里提供「订单/Auftrag 总览 + 状态」，其中 6 家还能在账户里直接下载交易单据。这是最普遍的一组功能。
   - 换到询价模式，对应物就是「我的询价 + 3–4 个状态 + Proforma PDF」。WooCommerce 的 My Account → Orders 原生就有这个列表。不做它，反而要额外写代码把它关掉。
2. **客户必须能在登录后的账户里重新取到 Proforma。**
   - PI 上印着银行账户。行业资料明确提醒：有人截获 PI 邮件并篡改收款账户（newbuyingagent，2026-03-09）。账户里那份 PDF 是客户核对银行信息的可信来源。
   - Krannich 在官方教程里讲得很直接：单据放进门户之后，客户不必再找销售要文件，省掉了等待（§2.1）。
3. **"产品文件"不要做成账户里的独立文件库。**
   - 9 家里有 7 家提供数据表，但多数放在公开产品页或下载中心。账户内的"个人文件库"只在 IBC 见到（Merkliste 打包 ZIP）。
   - 建议：数据表继续公开（ADR-0023 的自托管文件），账户里每条询价按行附上该产品的数据表链接。
4. **Woo 只出 Proforma，不出正式发票。**
   - 正式发票（§14 UStG）要求编号唯一。同一笔交付若开出两张都没标成"副本"的发票，会触发 §14c 的税额风险。
   - 国内 B2B 电子发票义务：2027-01-01 起适用于上年营业额超过 80 万欧的企业，2028 年起适用于所有企业（§4.4）。
   - 正式发票应由 Linker 的会计/ERP 系统开具。因此网站侧的发票、贷记单、价格锁引擎、"接受报价→付款"流程都不需要（§5.5）。

**映射支持的部分：**

| 业主提到的要素 | 映射结论 | 依据 |
| --- | --- | --- |
| 资料 | 支持 | 公司资料/地址普遍存在（多用户只是"常见"，见 §2.3） |
| 选型输出 | 支持 | 9 家里有 7 家（另有 1 家间接证据）把规划工具产出的 BOM、购物清单或项目存进账户（BayWa Solar-Planit、IBC PV Manager、Memodo K2 导入、Krannich 多购物车、Segen Quick Quote 等） |
| Proforma | 支持 | 对应普遍存在的"订单 + 单据" |
| 个人对接人 | 业主没提，但映射显示 9/9 都有（其中 3 家是间接证据） | 应补上 |

**需要业主回答的只有事实（§5.6）：** Linker 现在用什么系统开正式发票；PI 有效期多少天；是否对询价回复时限做承诺。

---

## 1 方法与证据规则

**Apify 运行**：共 12 次，合计约 1.05 USD。
- `apify/google-search-scraper`：3 轮，约 130 个德语/英语查询。
- `apify/website-content-crawler`：5 批，约 150 个页面。
- `karamelo/youtube-transcripts`：8 个官方教程视频的字幕。

**证据的边界：**
- 竞品门户都需要登录，我们看不到。证据只来自公开材料：注册页列出的权益、FAQ/帮助中心、官方教程视频字幕、App Store 描述、AGB/ALB。
- 矩阵里的「–」表示公开资料没提到，**不等于"没有"**；「✗」表示有证据说明没有门户，或明确说明该事项在线下处理。

**本地核验**：Woo 内部行为在本机 QA 站的 WooCommerce 11.1.0 源码上核对（`output/system-delivery/local-site/.../woocommerce`）。这是读本地代码，不是网络检索。

**排除和纠错：**
- `ews-tools.de`（"my.EWS"）是另一家做机床刀具系统的 EWS，不是 PV 批发商 EWS GmbH & Co. KG（pv.de），已排除。
- Sonepar 是电气批发商（PV 只是其中一块）。它的证据来自德国、瑞士和意大利站点（意大利站有德语 FAQ），表中标为集团层面的证据。
- 厂商/咨询公司博客（Virto、ChatSKU、Toimi、DuoByte）只作旁证。一手调查用 Gartner、McKinsey 和 ECC KÖLN（后者经 DuoByte 转引，注明出处）。

---

## 2 Part A — 竞品账户区映射

### 2.1 逐家证据

**Memodo（DE，Shopware）**
- 付款方式只有 Vorkasse 和"Rechnung（Kreditlimit mit Zahlungsziel）"。正式发票在货物出库时以 PDF + E-Rechnung 发送；"所有发票都在客户账户的'Bestellungen'下"。出库时用邮件发送 Lieferschein 和物流跟踪链接。价格以发票开具日为准，原文："Das Rechnungsausgangsdatum ist entscheidend für den finalen Preis"——**没有价格锁**。来源：https://www.memodo.de/m/support/hilfe/ （抓取 2026-10-09）
- 在"Mein Konto"里能看到信用额度和个人付款条件；预付时开"Vorauskasse-Rechnung"，并已扣除 3% Skonto。来源：https://www.memodo.de/zahlung/ （2026-10-09）
- 网店功能：Stücklisten-Import、Favoriten-Speicher、Warenkörbe speichern、Mehrere Logins anlegen、Benachrichtigungen；"Persönliche Ansprechperson"。来源：https://www.memodo.de/m/willkommen-bei-memodo/ （2026-10-09）
- 可从 K2 规划工具导入 BOM。来源：https://www.memodo.at/partlistimport ；视频"Den Memodo Solarshop mit dem K2 Base Tool verknüpfen"（2024-04-11）https://www.youtube.com/watch?v=wbf6VPe4YPU
- 独立的 Service & Support 门户：可新建服务请求，可查看未结请求的状态。来源：https://service.memodo-shop.com/s/?language=de （2026-10-09）
- AGB §2：Memodo 的 Angebote 是 freibleibend；客户的 Bestellung 是有约束力的要约；Memodo 在 10 个工作日内以 Auftragsbestätigung 接受，接受后合同才成立。来源：https://www.memodo.de/agb/ （2026-10-09）

**Krannich Solar（DE，Shopware 6，35 家子公司）**
- 官方教程"Kundenportal 2023"（2023-10-25）https://www.youtube.com/watch?v=9lr14132Ui8 ，字幕要点：
  - Auftragsübersicht：近 12 个月已交付的订单 + 全部待交付订单，显示计划发货日。
  - 可筛选；快速搜索支持 Kommissionsname 和单据号。
  - 订单详情里可下载 PDF：Auftragsbestätigungen、Lieferscheine、Packlisten、Rechnungen，组件还有 Flash Reports。原话：这样"erspart Ihnen Wartezeit, da Sie diese Dokumente früher bei Ihren persönlichen Ansprechpartnern im Vertrieb anfordern mussten"。
  - 订单可导出 PDF/Excel。
  - Offene Posten：未结发票、贷记单、**Vorkassenrechnungen**；显示信用额度；可下载发票副本。
- 注册权益：价格与可用性、个人对接人、Online-Kundenportal zur Verwaltung Ihrer Bestellungen、Schnellbestellung、技术支持工单系统。来源：https://shop.krannich-solar.com/de-de/account/request-registration （2026-10-09）
- FAQ：客户门户从账户菜单进入；Quick Order 支持上传 CSV/XLSX；可保存购物车；可按项目建多个命名购物车；有产品对比。来源：https://shop.krannich-solar.com/en-de/Footer/Information/FAQ （2026-10-09）
- ≥400 kWp 的项目走询价表单，原文："Ihre persönlichen Ansprechpartner/innen im Vertrieb werden sich zeitnah mit Ihnen in Verbindung setzen"——**线下跟进，账户里看不到这条询价**。来源：https://shop.krannich-solar.com/en-de/anfrage-pv-projekt-ab-400-kwp （2026-10-09）
- ALB §3（合同成立）：Angebote freibleibend；webshop 里点"Bestellung abschicken"即为有约束力的要约；Bestelleingangsbestätigung ≠ 接受；合同经书面或电邮的 Auftragsbestätigung 成立。ALB 的付款条款另写明："Der Versand unserer Ware erfolgt grundsätzlich nur gegen Vorausüberweisung"。来源：https://krannich-solar.com/de-de/alb/ （2026-10-09）
- 客户专属价格与权限。来源：Shopware 案例 https://www.linkedin.com/posts/shopware-ag_case-study-krannich-activity-7449781407683407872-YF9g （2026-10-09）

**Segen（UK/EU，含德国 SegenSolar GmbH）**
- 门户内容："von Broschüren und Datenblättern über Installationsanleitungen bis hin zu Lagerbeständen, Angeboten und Ihre Rechnungen"，另有设计工具和配置器。来源：https://segensolar.de/portal/ 、https://segensolar.eu/portal/ （2026-10-09）
- 每个客户配一名专属销售、一名订单处理员、一名技术对接人。来源：同上，以及 https://segensolar.tz/about-us/ （2026-10-09）
- 英国门户权益里有"30-day price lock"。来源：https://portal.segen.co.uk/ 。南非站写的是"7-day price lock on quotes"。来源：https://segensolar.co.za/products/ （2026-10-09）
- Quick Quote 生成报价号，之后可在账户里取回（视频 2015-03-23）。来源：https://www.youtube.com/watch?v=uXGwjFrGBAg
- 南非门户指南（PDF，2017-03；正文未能抓取，以下来自 Apify SERP 摘要）："Make a Payment" 页面在 "My Account" 菜单下，可在线付款。来源：https://portal.segensolar.co.za/reseller/docs/MakingAPaymentSA_March2017.pdf

**BayWa r.e.（DE PV-Webshop）**
- 官方教程（2020-05-28）https://www.youtube.com/watch?v=_Ez3MH0F3-M ：
  - 产品页的文件可单个或打包下载。
  - Solar-Planit 规划工具的 Stückliste 可一键传进 webshop 账户（账户需经销售团队验证），再放进购物车。
  - Schnellbestellung（输入货号）。
  - Favoriten。
  - Einkaufslisten：可存当前购物车，也可把"bereits bestellte Warenkörbe"存成清单，一键回购物车。
- Solar Planit 打通"设计→下单→安装"；新功能让安装商快速出报价，报价可转为完整项目方案。注意：这是安装商给终端客户的报价，不是批发商给安装商的报价。来源：https://www.pveurope.eu/specialized-trade/baywa-re-steps-smarter-tools-and-bigger-goals （2025-06-20）
- AGB（LU）：除非标明不具约束力，BayWa r.e. 的 Angebote 在 30 天内有约束力；交付范围与付款以书面 Auftragsbestätigung 为准。来源：https://solar-distribution.baywa-re.lu/de/agb （2026-10-09）

**IBC SOLAR（DE）**
- 门户权益："Online-Shop … mit Preisen und Verfügbarkeiten · Auftragsübersicht mit allen Dokumenten, Informationen zu Lieferstatus · PV Manager · alle IBC-Ansprechpartner auf einen Blick"。来源：https://portal.ibc-solar.com/de/ （2026-10-09）
- 德国门户写的是"Zugriff auf alle Ihre Dokumente"和"Kontaktdaten Ihrer Ansprechpartner"。来源：https://portal.ibc-solar.de/ （2026-10-09）
- 门户 FAQ（https://portal.ibc-solar.de/faq ，2026-10-09）：
  - 当前数据表在产品店；旧数据表在 Downloads；多份文件可加进 Merkliste 后打包 ZIP 下载。
  - Mein IBC > Benutzerverwaltung：可建子用户并分配权限。
  - Finanzbereich > Rechnungsübersicht。
  - 每月更新的 Datanorm 文件。
  - PV Manager 需付费授权。
- PV Manager 从客户接触、计算、规划，一直到订货，生成的 Stückliste 可直接在 IBC 网店下单；项目可与 IBC 专家共享。来源：视频 https://www.youtube.com/watch?v=7im7OrQ5w2c （2022-01-20）

**Sonepar（电气批发，DE/CH/IT）**
- 德国站：账户区有 Kundenkonto、Merklisten、Warenkorb，并提供 Retourenportal。来源：https://www.sonepar.de/c/services-loesungen/beschaffung-lager/onlineshop （2026-10-09）
- 瑞士站："Einfache Benutzerverwaltung · Digitales Archiv aller Bestellungen (inkl. Lieferschein, Rechnungen, Retouren)"。来源：https://www.sonepar.ch/de/so/startseite/services/bestellservice/webshop （2026-10-09）
- 意大利站（德语 FAQ）：
  - 「Meine Angebote」：客户可从购物车生成报价；销售开出的报价可转成订单，生成时会发邮件通知。
  - 「Meine Bestellungen」「Gekaufte Produkte」「Zu liefern」「Meine Rechnungen」「Meine Lieferscheine」。
  - 用户与权限管理。
  - 来源：https://www.sonepar.it/de-it/static/faq （2026-10-09）
- 德国 App 评论原话："Wenn ich ein Angebot wandle und bestelle …"，说明 App 里能看到报价并转成订单。来源：https://apps.apple.com/de/app/sonepar-shop/id6451204403 （2026-10-09）
- UGL 接口的单据链：客户发出 Anfragen、Bestellungen；Sonepar 回传 Auftragsbestätigungen、Lieferscheine、Rechnungen、Gutschriften。来源：https://www.sonepar.de/c/services-loesungen/beschaffung-lager/e-procurement/schnittstellen/ugl-schnittstelle （2026-10-09）

**EWS GmbH & Co. KG（pv.de，DE/Nordics）**
- 合作伙伴区（登录）：News、"200 teamplayers und 1 direct contact"、可下载厂家文件、订单处理所需的文件与表单、销售支持。来源：https://pv.de/en/login/ （2026-10-09）
- 注册后可看价格和订单。来源：https://pv.de/registrierung/ （SERP 摘要，2026-10-09）
- QuickShop（在登录区）：未来几个月的可用性、按项目偏好加权的产品推荐、购物车内比较组件、自动计算运费。来源：https://pv.de/news/quickshop-der-online-fachberater-fuer-pv-profis/ （2022-04-06）
- 单独计算的整套系统，以及含文件的施工规划。来源：https://pv.de/produkte-preise/ （2026-10-09）

**Wattkraft（DE，Huawei/AIKO/Phono/Canadian Solar 分销）**
- 官网没有客户登录或下单门户。有按品牌分类的公开 Downloadcenter，有"Unsere Handelspartner"页面，有按事项分流的询价表单。来源：https://www.wattkraft.com/ 、https://www.wattkraft.com/kontakt/ （2026-10-09）
- Zendesk 帮助中心：技术资料、"Unterlagen für RMA Anfrage"、固件。来源：https://wattkraft-de.zendesk.com/hc/de-de （2026-10-09）
- 另有 Huawei 安装积分的 Prämienshop（忠诚计划，不用于下单）。来源：https://de.linkedin.com/posts/wattkraft_huaweifusionsolar-smartpvcommunity-solarenergie-activity-7470414515004739584-vj1n （SERP，2026-10-09）
- **它是"无门户、靠销售 + 表单 + 帮助中心"的分销商反例。**

**Alibaba.com 买家工作台 / Accio（B2B 平台对照）**
- Inquiry 就是发给卖家的消息，在"My Alibaba"下的 Message Center 里跟踪。来源：https://activity.alibaba.com/page/resources/how-to-send-an-effective-inquiry.html （2021-02-03）
- RFQ 帮助页原话："You can track the status on your RFQ page"。来源：https://helpcenter.alibaba.com/s/buyer/knowledge?categoryId=275875456&questionId=ff589db60ef341ec837e5f33fe6ecddbsgvpc278077001 （2026-10-09）。另见 https://rfq.alibaba.com/rfq.html 的"Manage RFQ"。
- 增值税发票下载路径："My Alibaba > My Orders > Order details > Payment records"。来源：https://helpcenter.alibaba.com/s/buyer/knowledge?questionId=86528c6cefdb49ff8aefe600a812495bsgvpc278077001&categoryId=1000088 （2026-10-09）
- 流程原话："you will likely send an inquiry … your seller will probably then send you a document with all this information included, as well as the price. This is known as a pro-forma invoice. It is simply a quote before the sale takes place. A purchase order is usually created after receiving a pro-forma invoice."——**和 de-linker 的模式一样：询价 → PI。**来源：https://activity.alibaba.com/page/resources/What_goes_into_an_effective_purchase_order.html （2021-02-03）
- Accio：Favorites、Messenger（所有消息与询价跟进）、报价对标、订单跟踪；定位为"work-layer … lifecycle of a sourcing project"。来源：https://static.accio.com/accio-user-guide.html 、https://www.accio.com/wow/guide-accio-vs-alibaba.html （2026-10-09）
- **注意："workspace"是 Accio/SaaS 用语；PV 行业叫 Kundenportal / Mein Konto / Partnerbereich。**

### 2.2 功能矩阵

图例：✓ 有直接证据；◐ 间接或部分；✗ 有证据表明没有，或在线下处理；– 公开资料没提到

| 功能 | Memodo | Krannich | Segen | BayWa r.e. | IBC | Sonepar | EWS | Wattkraft | Alibaba/Accio |
|---|---|---|---|---|---|---|---|---|---|
| ① 询价/报价列表 + 状态 | – | ✗（项目询价线下跟进） | ✓ 报价 + 价格锁 | ◐（规划工具里的终端报价） | – | ✓ Meine Angebote | – | ✗ | ✓ RFQ 状态、Message Center |
| ② 订单/Auftrag 总览 + 状态 | ✓ | ✓ | ◐ account info | ◐（"已订购物车"可存清单） | ✓ 含 Lieferstatus | ✓ | ◐ | ✗ | ✓ My Orders |
| ③ 交易单据下载（AB/LS/RE/预付发票） | ✓ | ✓ | ✓ 发票 | – | ✓ | ✓ | – | ✗ | ✓ 税票 |
| ④ 产品文件（数据表/手册） | ✓ 公开产品页 | ✓ Downloads | ✓ 门户 | ✓ 产品页可打包 | ✓ 门户 + Merkliste ZIP | – | ✓ 伙伴区 | ✓ 公开下载中心 | ✗ |
| ⑤ 保存购物车/清单/BOM/项目 | ✓ | ✓ | ✓ Quick Quote | ✓ | ✓ PV Manager | ✓ Merklisten | ◐ | ✗ | ✓ Favorites/Accio |
| ⑥ 客户专属价格/价目表 | ✓ | ✓ | ✓ | ✓ | ✓ + Datanorm | ✓ | ✓ | ✗ | ◐ |
| ⑦ RMA/保修/工单 | ✓ 服务门户 | ✓ 工单 | ◐ 保修文件 | ✗ 线下客服 | ◐ After-Sales 下载 | ✓ Retourenportal | – | ✓ 帮助中心 RMA | – |
| ⑧ 公司资料/多用户 | ✓ 多个登录 | ◐ 会计联系人/权限 | – | – | ✓ 子用户 + 权限 | ✓ | – | ✗ | – |
| ⑨ 再订购/快速下单 | ◐ | ✓ CSV/XLSX | – | ✓ Schnellbestellung | – | ✓ | – | ✗ | – |
| ⑩ 具名个人对接人 | ✓ | ✓ | ✓ 三人小组 | ◐ | ✓ | ◐ | ✓ | ◐ | ✓ 卖家聊天 |
| ⑪ 规划工具 → BOM/购物车 | ✓ K2 | ✓ K2/Design Tools | ✓ | ✓ Solar-Planit | ✓ PV Manager | ◐ HERO | ✓ | ✗ | ◐ Accio |
| ⑫ 门户内在线支付 | ✗ Vorkasse/账期 | ✗ 预付转账 | ◐ ZA "Make a payment" | – | – | – | – | ✗ | ✓ Trade Assurance |
| ⑬ 信用额度/未结项 | ✓ | ✓ | ◐ | – | – | – | – | ✗ | – |

### 2.3 频率（9 家；通用 ≥7，常见 4–6，少见 ≤3）

| 等级 | 功能 |
| --- | --- |
| 通用 | ⑩ 具名对接人 9/9（3 个 ◐）；② 订单总览 8/9（3 个 ◐）；⑪ 规划 → BOM 8/9（2 个 ◐）；⑤ 保存清单/BOM/项目 8/9（1 个 ◐）；⑥ 客户价格 7/9（+1 ◐）；④ 产品文件 7/9（多为公开，账户内个人文件库只有 IBC） |
| 常见 | ③ 交易单据下载 6/9；⑦ RMA/工单 4/9（+2 ◐） |
| 少见 | ① 账户内询价/报价列表 3/9（+1 ◐）——PV 批发里只有 Segen 和 Sonepar；⑧ 多用户 3/9（+1 ◐）；⑨ 快速下单 3/9（+1 ◐）；⑬ 信用额度 2/9（+1 ◐）；⑫ 门户在线支付 1/9（Alibaba；PV 批发 8 家里没有直接证据，只有 Segen 南非站的 "Make a Payment" 算 ◐）；价目表文件（Datanorm）1/9 |

**解读：**
- PV 批发商是**先有网店**的模式：登录后见价，直接下单。所以它们的核心对象是 Bestellung/Auftrag，所有单据都挂在订单上。账户里的"报价列表"之所以少见，是因为报价在这种模式下只是"转成网上订单"的中间物（Segen、Sonepar 都是这样）。
- de-linker 是**先有询价**的模式：没有网上订单，询价本身就是核心对象。把通用的「Auftragsübersicht mit allen Dokumenten」（IBC 原话）翻译过来，就是「Anfragen mit Proformarechnung」。
- **不该搬过来的**：多用户、信用额度、RMA 门户、价目表文件、快速下单、在线支付。这些都依赖 ERP，或服务高频复购，频率也只有少见到常见。Toimi（2026-10-01）也说门户的回报主要来自高频复购，"a large firm selling one-off projects"受益较小。来源：https://toimi.pro/blog/b2b-customer-portal-features/

---

## 3 Part B — 行业术语与买家预期

### 3.1 德语单据链（PV 批发的实际用法）

| 步骤 | 发出方 | DE | EN | 证据 |
|---|---|---|---|---|
| 1 | 买方 | **Anfrage**（Angebotsanfrage） | **Inquiry**（英式 enquiry）/ RFQ | Sonepar UGL 把"Anfragen"列为客户发出的单据；Krannich 表单标题"Anfrage: PV-Projekt >400kWP"；Alibaba 的 inquiry / RFQ |
| 2 | 卖方 | **Angebot**（瑞士叫 Offerte）。Memodo、Krannich 是 freibleibend；BayWa r.e. 30 天内有约束力 | Quotation / Quote | 三家 AGB/ALB（§2.1） |
| 3 | 买方 | **Bestellung**：有约束力的 Vertragsangebot | Purchase order (PO) | Memodo AGB §2(2)；Krannich ALB §3(3) |
| 4 | 卖方 | Bestelleingangs- / Zugangsbestätigung：**不等于接受** | Order acknowledgement | Krannich ALB §3(4)；Memodo AGB §2(2) |
| 5 | 卖方 | **Auftragsbestätigung (AB)**：合同由此成立 | Order confirmation / Sales order | 三家 AGB；Sonepar UGL |
| 6 | 卖方 | **Vorkassenrechnung**（Krannich）/ **Vorauskasse-Rechnung**（Memodo）/ **Proformarechnung**：发货前的付款请求 | **Proforma invoice (PI)** / prepayment request | Krannich 门户字幕；memodo.de/zahlung；Lexware |
| 7 | 卖方 | Lieferschein | Delivery note | Sonepar UGL；Krannich |
| 8 | 卖方 | **Rechnung**（§14 UStG；2027/28 起为 E-Rechnung） | Invoice | §4.4 |
| 9 | 卖方 | Gutschrift | Credit note | Sonepar UGL |

补充两个词：
- **Auftrag**：卖方视角的"订单"，例如 Krannich 和 IBC 的"Auftragsübersicht"；**Bestellung** 是买方视角。两者指同一笔交易。
- **Lieferung**：交付本身，相关词有 Lieferschein、Liefertermin、Lieferstatus。在 de-linker 的模式里，交付全部在线下，网站上只会出现在 PI 的交货条件里。

### 3.2 "Proforma"在德国是什么意思、边界在哪里

- **Lexware**（更新于 2026-08-05）https://www.lexware.de/wissen/unternehmerlexikon/proforma-rechnung/
  - 它不是正规的 Handelsrechnung，"In Deutschland ist sie eine Auftragsbestätigung"。
  - 作为 AB "rechtlich bindend"。
  - 预付场景下"erhält [der Empfänger] eine Proforma-Rechnung als Auftragsbestätigung"。
  - 不能抵扣进项税；文件上必须写明"Proforma-Rechnung"。
- **IHK Rhein-Neckar** https://www.ihk.de/rhein-neckar/international/export-import/ausfuhr-eu/basisinfo-export/exportrechnung-proformarechnung-950590 （抓取 2026-10-09）
  - 纯信息性质，不触发付款。
  - "Die Pro-Forma-Rechnung kann auch als Angebot eingesetzt werden"（例如用于开立信用证）。
- **rechnungskit**（发布 2026-09-24，更新 2026-10-03）https://rechnungskit.de/wissen/proforma-rechnung
  - 不是 §14 意义上的发票。
  - 最常见的用途是 Vorkasse：客户需要"Betrag, Bankverbindung und Verwendungszweck"。
  - 应写明标题，并加一句"这不是发票"。
  - 如果 PI 上印了"Rechnungsnummer"和税额，可能按 §14c 产生税款。
  - 税额只在后来的正式发票上出现。
- **Stripe DE** https://stripe.com/de/resources/more/pro-forma-invoices-germany （2026-10-09）
  - PI 用单独的编号区间，单独归档，不进发票簿。
- **datax** https://datax-gmbh.de/pro-forma-rechnung/
  - "In einigen Ländern wird die Pro Forma Rechnung als Angebot gewertet, in Deutschland eher als Auftragsbestätigung."
- **Skydo**（更新 2026-09-29）https://www.skydo.com/blog/proforma-invoice-vs-quotation
  - 流程：Quotation → 买方接受或发 PO → PI（条款定稿、准备付款）→ 预付 → 发货 → 正式发票。
- **Alibaba**（2021）
  - PI 是"a quote before the sale"。

**结论：** 对"德国 + 欧盟"的经销商和安装商，"Proformarechnung / Proforma invoice"不需要解释，两种读法都成立：
- 德国读法：AB/预付文件；
- 国际读法：成交前的报价。

这正好对应业主的模式：询价 → PI（含银行信息）→ 转账 → 线下交付 → 会计系统开正式发票。

**拼写：**
- 专业来源三种写法都用：Proforma-Rechnung（Lexware、rechnungskit）、Pro-Forma-Rechnung（IHK）、Proformarechnung（sevdesk、Sage、Teamleader）。
- 链尖插件里已经在用"Proformarechnung"，**保持这一写法**。
- 英文链尖 inquiry 出现 119 次、enquiry 40 次，**统一为 inquiry**。

### 3.3 提交询价后，B2B 买家期待什么

1. **马上收到带编号的确认。**
   - 这是行业标准步骤：Krannich 叫 Bestelleingangsbestätigung，Memodo 叫 Zugangsbestätigung，两家都明确说它不等于接受。
   - Woo/YITH 一类询价插件也会在提交后发确认邮件。
2. **卖方在明确期限内给出有约束力的文件。**
   - Memodo：10 个工作日内发 AB。
   - BayWa r.e.：报价 30 天内有约束力。
   - Segen：报价价格锁定 7 天（南非）或 30 天（英国）。
3. **有人跟进，涉及选型时尤其如此。**
   - Krannich：项目询价由个人对接人"zeitnah"联系。
   - Segen：三人对接小组。
   - Gartner（2025-06-25）：买家查一般信息时偏好自助，但判断"是否适合自己业务"时偏好听销售意见。https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-sales-survey-finds-61-percent-of-b2b-buyers-prefer-a-rep-free-buying-experience
   - Gartner（2026-05-20）：69% 的买家用销售来核实 AI 给出的结论；同时 70% 偏好完全数字化的自助购买。https://www.gartner.com/en/newsroom/press-releases/2026-05-20-gartner-survey-finds-sixty-nine-percent-of-b-two-b-buyers-turn-to-sales-reps-to-validate-ai-generated-insights
   - Gartner（2026-03-09）：67% 偏好不经销售的购买体验。https://www.gartner.com/en/newsroom/press-releases/2026-03-09-gartner-sales-survey-finds-67-percent-of-b2b-buyers-prefer-a-rep-free-experience
4. **能自助查到状态和文件，并且各渠道说法一致。**
   - ECC KÖLN B2BEST Barometer Vol. 23（2026 年 7 月调查 200 家批发商和制造商，2026-09-17 发布）：最大的潜力在产品信息与可用性（46%）、实时订单与交付状态（42%）、报价与价格（40%）。经 DuoByte 转引（2026-10-03）https://www.duobyte.dev/de/insights/b2b-self-service-studie-kundenportale
   - McKinsey 2026 B2B Pulse（2026-05-28）：换供应商的头号原因是各团队给出的信息不一致，其次是找不到懂行的人。https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights/the-surprising-economics-of-b2b-growth-the-new-survival-threshold-and-what-it-takes-to-thrive
   - Gartner（2025-06-25）：69% 的买家遇到过官网信息与销售说法不一致。
5. **速度。**
   - HBR 研究：平均 42 小时回复，23% 从不回复（myralum 转引，2026）。
   - 厂商基准：24–72 小时是常态，超过 24 小时赢单率下降（ChatSKU 2026-09-29；goautonomous 2026-07-13）。这些是厂商内容，只说明方向。
   - **回复时限是商业承诺，属于业主要定的事实**；没有承诺之前，文案里不写小时数。

### 3.4 判定："询价 → PI，之后全部线下、没有状态"够不够？

**付款、发货、正式发票放在线下：够。**
- PV 批发本来就以预付转账为主。
- 这些事件 Woo 根本不知道。
- 在没有 ERP 的情况下硬显示物流状态，反而容易和销售的说法不一致，而这正是 McKinsey 调查里换供应商的头号原因。

**"没有状态"：不够。最低应该有：**
- (a) 提交后马上发确认，带询价编号；
- (b) 账户里有"我的询价"列表：状态（已收到 / PI 已出 / 已完成 / 已取消）+ PI PDF；
- (c) 同一个编号贯穿邮件、PI 和账户；
- (d) 具名对接人。

这一最小集合在 Woo 里几乎是现成的（§4）。不做的话，客户只能翻邮件附件，这与行业常态相反：9/9 都有对接人，8/9 有订单总览，6/9 能在账户里下载交易单据。

---

## 4 Part C — WooCommerce 11 可行性

### 4.1 Woo 核心有没有"询价/报价"

- WooCommerce 11.0 发布说明（2026-08-04）https://developer.woocommerce.com/2026/08/04/woocommerce-11-0/
  - 亮点是性能、"Customers can claim previous guest checkout orders"、分析数据的可靠性，以及实验性的弃购邮件和块编辑器邮件。
  - **没有询价/报价功能。**
- 核心订单状态（官方文档，抓取 2026-10-09）https://woocommerce.com/document/managing-orders/order-statuses/
  - 共 8 个：Draft、Pending payment、Processing、Completed、On hold、Failed、Cancelled、Refunded。
  - 没有"报价"状态。
- 当前版本：WP Overnight 免费版 5.16.4（2026-10-08）写着"Tested: Compatibility confirmed with WooCommerce 11.2"；本地 QA 站是 11.1.0。
- **结论：** 2026 年 Woo 没有官方的核心询价功能。Woo.com 市场上的询价扩展都来自第三方（Addify、WebWizards、WPExperts，以及"Quotes for WooCommerce Pro"），本次检索没有发现 Woo 自己出的报价扩展（§4.3）。不过"订单 = 询价"是可行的：多家询价插件也是这么做的，例如 YITH 把询价存成"New quote request"状态的 Woo 订单。

### 4.2 建模方案比较

以下 Woo 内部行为已在本地 WooCommerce 11.1.0 源码中逐条核对：
- `WC_Gateway_BACS::process_payment()` 用 `apply_filters('woocommerce_bacs_process_payment_order_status', OrderStatus::ON_HOLD, $order)` 决定下单后的状态（3.4.0 起）。
- `woocommerce_valid_order_statuses_for_payment` 默认只有 `pending`、`failed`。
- `WC_Order::set_status()` 会调用 `maybe_set_date_paid()`：进入 processing 或 completed 时写入 `date_paid`。
- 扣库存挂在 `payment_complete`、`processing`、`completed`、`on-hold` 上。
- 管理员的 New Order 邮件只挂在 pending/failed/cancelled → processing/completed/on-hold 这些状态转换上。
- `woocommerce_valid_order_statuses_for_order_again` 默认只有 `completed`。
- `customer-invoice.php` 只有在 `needs_payment()` 为真时才显示"Pay for this order"。

| 方案 | 做法 | 后果 | 判定 |
|---|---|---|---|
| **A（推荐）** | 结账页只留一个网关：核心 **BACS**，改名，清空账户信息；BACS 下单后的默认状态改为自定义 `wc-inquiry`；员工出 PI 后改为 `wc-proforma`；成交后 `completed`，放弃则 `cancelled` | 不出现"付款"按钮；不写 `date_paid`，报表不会把询价算成已付；不扣库存；邮件按状态发 | ✓ |
| B | `woocommerce_cart_needs_payment` 返回 false | 结账走 `process_order_without_payment()` → `payment_complete()` → 订单变 processing 并写入 `date_paid`。GitHub #68289（2026-09-02，Woo 11.0.1）记录了这条分支把未付的非零订单标成已付 https://github.com/woocommerce/woocommerce/issues/68289 ；Business Bloomer 也演示了这个过滤器把订单推进到 Processing（2025-06-09）https://www.businessbloomer.com/woocommerce-managing-initial-order-status/ | ✗（数据显示"已付"，实际没付） |
| C | 只用核心 on-hold，把标签改成"Anfrage eingegangen" | 零代码，New Order 邮件原生触发。但 on-hold 的语义是"等到账、已扣库存"；客户收到的默认 on-hold 邮件写的是在确认收款前暂停处理；出 PI 后状态也不会变化 | 过渡方案 |
| D | 询价插件（YITH / Addify / WP Overnight Order Proposal / B2B 套件） | 多出一个"报价"对象和一份报价 PDF，并附带"接受 → 结账 → 付款"流程 | ✗ 与"无在线支付、PI 即报价"冲突 |
| E | Invoice Gateway 或 COD 改名为"账期/发票" | 订单进 Processing（写入 `date_paid`）；发票在外部系统开。Wholesale Suite（2026-09-25）https://wholesalesuiteplugin.com/woocommerce-order-without-payment/ ；Invoice Gateway https://wordpress.org/plugins/invoice-gateway-for-woocommerce/ | ✗（同样会显示"已付"） |
| F | Place Order Without Payment（免费，3,000+ 安装，v2.7.8） | 把支付区整个移除；它内部怎么处理状态没有核实 | 未在 staging 验证前不用 |

**员工日常操作（方案 A）：**
1. 打开订单，改价格，用一条 shipping 行填运费；
2. 生成 Proforma；
3. 把状态改成"Proforma issued"，系统自动发出带 PI 附件的邮件；
4. 客户转账；
5. 会计系统开正式发票；
6. 员工把订单标为 completed（这时写入 `date_paid` 是真实的）。

**另外两项配置：**
- Woo Analytics 的设置里把 `wc-inquiry`、`wc-proforma` 排除，不计入营收。YITH 的文档对询价状态也是这么建议的。
- Woo 11.0 起访客下的单可以凭邮箱验证认领。如果将来放开访客询价，询价可以事后归到账户下。

### 4.3 询价/报价扩展（列出来比较，不推荐用）

| 扩展 | 供应商 / 2026 价格 | 模式 | My Account | 适配 |
|---|---|---|---|---|
| YITH Request a Quote | 免费版 10,000+ 安装，v2.55.0；Premium 每年 $79.99（首年 $69.99） | 询价存为"New quote request"状态的 Woo 订单；报价 PDF；接受/拒绝；过期；接受后进结账页付款 | "Quotes"栏：状态 + PDF | ✗ https://yithemes.com/themes/plugins/yith-woocommerce-request-a-quote/ |
| Request a Quote for WooCommerce | Addify，Woo.com，每年 $69，5K+ 安装，v2.9.4 | 状态：Pending / In process / Accepted / Converted to cart / Converted to order / Declined / Cancelled | 报价日志 + PDF；客户可自己转成订单并付款 | ✗ https://woocommerce.com/products/request-a-quote-plugin-for-woocommerce/ |
| WooCommerce Order Proposal | WP Overnight，每年 €45；2.4.1（2026-06-30）测到 Woo 10.9 | 订单进"order proposal"状态；有效期到期自动失效；客户可在结账时选择 Proposal | 在账户里接受/拒绝，然后付款 | ◐（最接近，但带付款步骤，且未列 11.x 测试）https://wpovernight.com/downloads/woocommerce-order-proposal/ |
| B2B & Wholesale Suite | WebWizards，Woo.com，每年 $149 | 询价 + 消息系统 | – | ✗（整套 B2B 方案）https://woocommerce.com/products/b2b-wholesale-suite/ |
| Wholesale for WooCommerce | WPExperts，Woo.com，每年 $129 | 询价、报价 PDF、转成订单 | – | ✗ https://woocommerce.com/products/wholesale-for-woocommerce/ |
| B2BKing | 免费核心 10,000+ 安装，v5.2.61 | 以对话方式询价 + Offers；自带账期网关 | – | ✗ https://wordpress.org/plugins/b2bking-wholesale-for-woocommerce/ |
| Wholesale Suite（Quotes 模块） | Wholesale Suite 团队 | "Buyers build and submit quote requests right from their My Account area" | ✓ | ✗ https://wholesalesuiteplugin.com/ |
| NP Quote Request | 免费，8,000+ 安装，v2.4.17 | 不付款也能结账；可把订单转成报价 | – | ◐ https://wordpress.org/plugins/woo-rfq-for-woocommerce/ |

### 4.4 Proforma PDF，以及要不要开发票

| 插件 | 免费/付费（2026） | Proforma | 编号 | 德/英 | 银行信息 | My Account 下载 | Woo 11 | 结论 |
|---|---|---|---|---|---|---|---|---|
| **WP Overnight PDF Invoices & Packing Slips** + **Professional** | 免费版 5.16.4，300,000+ 安装，支持 UBL/Peppol/CII/Factur-X/ZUGFeRD 电子发票；Pro 每年 €69（1 站）；Plus Bundle（含 Premium Templates）每年 €99 | ✓（Pro：Proforma / Credit Note / Receipt；文档标题可改） | 每类文档可用单独编号 | 支持 WPML/Polylang/Weglot/TranslatePress/GTranslate；模板可翻译 | 页脚/免责声明可自定义；HTML/CSS 模板；Premium Templates 有页脚的公司/银行信息栏 | Pro 2.25.0（2026-05-12）起客户可在 My Account 订单页下载 Pro 文档；可附加到任意 Woo 邮件 | Pro 2.27.2（2026-07-28）测过 11.0；免费版 5.16.4 测过 11.2 | **推荐** |
| YITH WooCommerce PDF Invoices & Packing Slips | Premium 每年 $79.99 | ✓ | 顺序号、按年重置、前后缀 | 可翻译 | 模板 | ✓ | – | 可替代 https://yithemes.com/themes/plugins/yith-woocommerce-pdf-invoice/ |
| Flexible Invoices（WP Desk） | 免费版 6,000+ 安装，v6.2.30，只能手工开票；PRO 每年 $59 | ✓（PRO） | 自定义 | 用 WPML 翻译 | – | – | – | 可替代（偏手工开票）https://wordpress.org/plugins/flexible-invoices/ 、https://flexibleinvoices.com/ |
| Invoices for WooCommerce（Bas Elbers） | 免费版 10,000+ 安装，v3.2.1，"hasn't been tested with the latest 3 major releases of WordPress"，2 年未更新；Premium 有贷记单和催款 | ✗ | – | – | – | ✓ | ✗ | ✗ https://wordpress.org/plugins/woocommerce-pdf-invoices/ |
| Germanized Pro（Vendidero） | Pro 85 €、Business 119 €（含税；续费 65/89 €） | 只有"Handels- bzw. Proformarechnungen zu internationalen Sendungen"（按发货单出的报关用 PI） | – | DE | – | – | – | ✗（不是订单级的预付 PI）https://vendidero.de/woocommerce-germanized/features |
| WebToffee Proforma Invoice | 价格未采集 | ✓（"for WooCommerce quotations"） | – | – | – | – | – | 未深入评估 https://www.webtoffee.com/product/woocommerce-proforma-invoice/ |

（WP Overnight 来源：https://wpovernight.com/downloads/woocommerce-pdf-invoices-packing-slips-professional/ 、https://wordpress.org/plugins/woocommerce-pdf-invoices-packing-slips/ 、https://docs.wpovernight.com/woocommerce-pdf-invoices-packing-slips/more-document-types/ ，均抓取于 2026-10-09）

**网站要不要开正式发票？不要。理由：**
1. **编号唯一。** §14 Abs. 4 Nr. 4 UStG 要求编号"einmalig vergeben"（https://www.gesetze-im-internet.de/ustg_1980/__14.html ）。可以有多个号段，但每个号只能用一次（fortlauf.de，2026-07-25）。网站和会计系统各开一套，就是两个出票源。
2. **重复开票的税款风险。** 同一笔交付出现多张没标"副本"的发票，财政局按 §14c 处理（rechnungskit 转引 UStAE 14c.1 Abs. 4）。
3. **电子发票义务。** 2026-12-31 之前的交易仍可开纸质/PDF 发票；2027 年起，上年营业额超过 80 万欧的企业必须开结构化电子发票，较小企业到 2027-12-31。来源：Görler & Partner，依据 §27 Abs. 38 UStG https://www.goerler-partner.de/de/service/e_rechnungspflicht_im_b2b_bereich_ab_2025/index.html （抓取 2026-10-09）
4. **触发事件不在网站上。** 正式发票由交付或收款触发，而这两件事都在线下发生，网站无从知道。

**所以网站只出 Proforma：**
- 单独号段 `PF-YYYY-NNNN`；
- 不用"Rechnungsnummer"这个词；
- 页面写明"keine Rechnung im Sinne des § 14 UStG; die Rechnung wird gesondert ausgestellt"。
- PI 上税额怎么呈现，请税务顾问确认。

**例外：** 如果 Linker 目前根本没有开票系统，WP Overnight 免费版能出 ZUGFeRD 2.0、Peppol BIS 3.0、CII、UBL 等结构化格式（BMF 认可 ZUGFeRD ≥2.0.1 和 Peppol-BIS，具体配置是否合规要逐项核对），Woo 可以成为**唯一**的开票系统。但那样所有销售（包括线下成交的）都要走它。这是业主层面的事实问题。

### 4.5 邮件

| 邮件 | 收件人 | 触发 | 实现方式 |
|---|---|---|---|
| 新询价（Woo New order 改标题为"Neue Anfrage / New inquiry"，即老板要的"有人下单就通知"） | 管理员（sales@） | pending → `wc-inquiry` | 需要把这个状态转换加进 `woocommerce_email_actions` 并挂上 trigger，或由状态插件处理 |
| 询价已收到 | 客户 | → `wc-inquiry` | 状态插件的状态邮件，或一个小的 `WC_Email` 子类 |
| Proformarechnung | 客户 | → `wc-proforma` | 状态邮件 + WP Overnight Pro 附加 PI。退路：Woo 原生"Order details"邮件（订单操作手动发送；自定义状态下不显示付款链接）+ 附件 |
| 已完成 / 已取消 | 客户 | → completed / cancelled | Woo 原生邮件（可选） |

---

## 5 Part D — 建议

### 5.1 账户功能集（"Mein Konto / My account"）

| 区块 | EN | DE | 内容 | 实现来源 |
|---|---|---|---|---|
| 概览 | Overview | Übersicht | 最近一条询价的状态；"Neue Anfrage / New inquiry"入口；**Ihre Ansprechperson / Your contact**（sales@ + 电话） | Woo dashboard + 一个小区块 |
| 询价 | Inquiries | Anfragen | 列表：Anfrage-Nr. · 日期 · 状态 · 金额 · 操作「Ansehen / View」「Proformarechnung (PDF)」。详情页：行项目，**每行附该产品的数据表链接**，PI 下载，「Erneut anfragen / Inquire again」 | Woo orders 端点改名 + view-order + WP Overnight Pro + order-again 过滤器 |
| 保存的选型 | Saved selections | Gespeicherte Auswahl | Advisor/工具的选型输出；「Als Anfrage senden / Send as inquiry」（放进购物车） | 现有选型存储，收缩后使用 |
| 公司资料 | Company details | Firmendaten | 公司名、USt-IdNr.（VIES 校验）、联系人、密码 | edit-account + 现有 B2B 字段 |
| 地址 | Addresses | Adressen | 账单地址 / 收货地址 | edit-address |
| 退出 | Log out | Abmelden | | |

**不放进账户：** Quotes、跨项目 Documents、Bulk order、Projects & Support、Payment methods、Woo Downloads、多用户、信用额度、RMA 门户、价目表。

**三条理由：**
1. **映射。** PV 批发门户的通用核心是「订单 + 单据 + 对接人 + 保存的清单/BOM」（§2.3），换成询价模式就是上表前三项。其余功能——多用户、信用额度、RMA、价目表、快速下单、在线支付——都属于先有网店、依赖 ERP 的模式，出现频率最多 4/9。
2. **风险与服务。** PI 上有银行信息，账户里那份可核对的 PDF 能降低改账户诈骗的风险（newbuyingagent，2026-03-09），也省掉"请再发一次文件"的来回。Krannich 的教程讲的就是这件事；Toimi 列出的四个日常问题里也有一条是"Can you resend the invoice?"。
3. **成本。** 列表、详情、再询价、邮件都是 Woo 原生功能，只多一个 PDF 扩展。这符合老板 2026-10-07 的裁定："普通网站、成本最低、不开发新功能"。

### 5.2 术语（EN / DE，作为功能性 UI 文字一并上线）

| 用途 | EN | DE |
|---|---|---|
| 账户区 | My account | Mein Konto |
| 导航项 | Inquiries | Anfragen |
| 单条 | Inquiry | Anfrage |
| 结账页标题 | Review and send inquiry | Anfrage prüfen und senden |
| 提交按钮 | Send inquiry | Anfrage senden |
| 唯一支付方式：标题 | Payment after proforma invoice | Zahlung nach Proformarechnung |
| 唯一支付方式：说明 | Nothing is charged now. After reviewing your inquiry we send you a proforma invoice with our bank details. | Sie zahlen jetzt nichts. Nach Prüfung Ihrer Anfrage erhalten Sie eine Proformarechnung mit unserer Bankverbindung. |
| 状态 1 | Inquiry received | Anfrage eingegangen |
| 状态 2 | Proforma invoice issued | Proformarechnung ausgestellt |
| 状态 3 | Completed | Abgeschlossen |
| 状态 4 | Cancelled | Storniert |
| 文件名称 | Proforma invoice | Proformarechnung |
| 下载 | Download proforma invoice (PDF) | Proformarechnung herunterladen (PDF) |
| 编号 | Inquiry no. / Proforma no. | Anfrage-Nr. / Proforma-Nr. |
| 有效期 | Valid until | Gültig bis |
| 付款条件 | Prepayment by bank transfer | Vorkasse per Überweisung |
| 再询价 | Inquire again | Erneut anfragen |
| 保存的选型 | Saved selections / Send as inquiry | Gespeicherte Auswahl / Als Anfrage senden |
| 对接人 | Your contact | Ihre Ansprechperson |
| 数据表 | Datasheet | Datenblatt |
| PI 声明 | This is not a tax invoice. The invoice will be issued separately. | Keine Rechnung im Sinne des § 14 UStG. Die Rechnung wird gesondert ausgestellt. |

**避免使用：**
- Bestellung / Order、Kasse / Checkout（不出现在可见标签里）、Bezahlen / Pay；
- Angebot annehmen / Accept quote；
- 用 Rechnung / Invoice 指代 PI；
- 把 Preisbindung / Price lock 当成功能来宣传；
- "Workspace / Arbeitsbereich"：这是 SaaS 用语，PV 行业说 Kundenportal / Mein Konto / Partnerbereich。

**三条理由：**
1. **符合行业用法。** 德国 PV 批发的合同链是 Angebot → Bestellung → Auftragsbestätigung；预付文件叫 Vorkassen- 或 Vorauskasse-Rechnung。Proformarechnung 在德国被读作 AB/预付文件，在国际贸易里被读作成交前的报价（§3.1–3.2）。对德国和欧盟的经销商都不需要解释。
2. **不做虚假承诺。** Memodo 和 Krannich 的 AGB 把"Bestellung"定义为有约束力的要约。de-linker 的询价没有约束力，也没有在线付款。用"Bestellung / Kasse / Bezahlen"会误导客户；"Anfrage + Proformarechnung"正好描述真实流程。
3. **前后一致。** 链尖已经在用"Proformarechnung"和"inquiry"。Gartner 和 McKinsey 都显示"信息不一致"是换供应商的头号原因，所以导航、状态、邮件、PDF 要用同一套词、同一个编号。

### 5.3 Woo 建模（状态、单据、邮件）

**状态：**

| slug | 客户看到（EN / DE） | 谁来设 | Woo 行为 |
|---|---|---|---|
| `wc-inquiry`（自定义） | Inquiry received / Anfrage eingegangen | 结账时自动设（BACS 的默认状态） | 不能付款；不扣库存；不写 `date_paid`；在 Analytics 中排除；触发"Neue Anfrage"（发给管理员）和客户确认邮件 |
| `wc-proforma`（自定义） | Proforma invoice issued / Proformarechnung ausgestellt | 员工，在生成 PI 之后 | 行为同上；触发附带 PI 的客户邮件；客户可在账户中下载 PI |
| `completed`（核心） | Completed / Abgeschlossen | 员工，收款并交付后（可选） | 写入 `date_paid`（此时数据是真实的）；计入报表；显示"Erneut anfragen" |
| `cancelled`（核心） | Cancelled / Storniert | 员工，询价不再继续或 PI 过期 | Woo 原生取消邮件（可选） |

不使用 `pending`、`on-hold`、`processing`、`failed`、`refunded`，也不再用 `dlk-quote`。

**单据：只有 PI**（WP Overnight Pro 的 Proforma Invoice 文档，改名为"Proformarechnung / Proforma invoice"）。
- 编号格式 `PF-{year}-{n}`，单独计数。
- 语言规则沿用现有的 `tv_b2b_document_lang()`：账单国家为 DE/AT/CH 时出德语，其余出英语。
- 内容：卖方身份、买方、行项目、运费行、合计、"Gültig bis"、Vorkasse、银行信息、Verwendungszweck（填 Proforma-Nr.）、交货条件（项目报价按项目条款）、§14 免责声明。
- 关闭 Invoice 和 Packing slip 两类文档。

**邮件：** 见 §4.5。

**三条理由：**
1. **Woo 订单是对的容器。** 行项目、价格、税、运费行、地址、备注、HPOS、后台列表、My Account 列表、邮件都现成，符合 Woo-first。连询价插件也是把询价存成 Woo 订单。
2. **自定义状态放在"已付 / 可付"集合之外。** 这样不会出现付款按钮，不写 `date_paid`，不扣库存，报表不失真。`needs_payment=false` 那条路会把没付的订单标成已付（#68289）。
3. **扩展点稳定，代码量为零或很少。** BACS 默认状态过滤器从 Woo 3.4.0 起就有；免费状态插件可以按支付方式设默认状态，也能发状态邮件。员工的整个流程都在 Woo 订单页里完成。

### 5.4 插件 vs 自定义代码

**使用：**

| 组件 | 选择 | 费用 | 作用 |
|---|---|---|---|
| PDF / Proforma | **WP Overnight 免费版 + Professional**（或 Plus Bundle，含 Premium Templates 的银行信息栏） | €69/年（或 €99/年） | 生成 PI；单独号段；附在邮件里；账户内下载 |
| 状态 + 状态邮件 | **Custom Order Status Manager for WooCommerce**（免费，30,000+ 安装，v2.1）。功能：自定义状态、按支付方式设默认状态、给客户/管理员发状态邮件。https://wordpress.org/plugins/bp-custom-order-status-for-woocommerce/ | 0 | `wc-inquiry`、`wc-proforma` |
| 结账网关 | Woo 核心 **BACS**：改名，清空账户信息 | 0 | 不付款就能提交询价 |
| 备选 | Addify Custom Order Status（Woo.com，$49/年，700+ 安装）https://woocommerce.com/products/custom-order-status/ | $49/年 | 仅在免费插件的双语表现不达标时使用 |

**小段自定义代码（复用现有权威，不另造）：**
- EN/DE 的标签和邮件文字走现有的 linker-i18n。
- PI 语言：按 `tv_b2b_document_lang()` 切换 WP Overnight 的渲染语言。本站不用 WPML/Polylang，所以需要一个 locale 切换钩子，先在 staging 验证。
- 账户：用 `woocommerce_account_menu_items` 改名并精简菜单；加对接人区块；订单行附数据表链接；把 `inquiry`、`proforma`、`cancelled` 加进 `woocommerce_valid_order_statuses_for_order_again`。
- 如果不用状态插件：自己注册两个状态，加上邮件动作。现有 `quotes.php` 里已经有注册状态的同类代码。

**不使用：** YITH 或 Addify 的询价插件、WP Overnight Order Proposal、各类 B2B 套件、B2BKing、Wholesale Suite、Germanized Pro、Bas Elbers 的插件、`needs_payment=false`、未经测试的 Place Order Without Payment。

**三条理由：**
1. **WP Overnight 是装机量最大的 Woo PDF 插件**（300,000+），一直在维护（2026-10-08 的版本测过 Woo 11.2）。Pro 正好提供 Proforma、单独号段、邮件附件和账户下载，可以替代整套自制的 ledger 和 renderer。
2. **询价插件和 B2B 套件都围绕"接受 → 结账 → 付款"设计**，还会多出一份报价文件。这与"无在线支付、PI 即报价"冲突，等于把一条规则拆成两份实现（Law 4）。
3. **剩下的自定义代码都是小而单一的胶水**：语言、标签、数据表链接、对接人，全部复用已有权威（i18n、`tv_b2b_document_lang()`、托管文档）。总费用约 €69–99/年（另有可选的 $49/年）。

### 5.5 现有定制门户（链尖 f007a9dd）逐项对照

**映射确认不需要的：**

| 组件 | 位置 | 结论 | 依据 |
|---|---|---|---|
| Quotes：`dlk-quote` 状态 + 默认 14 天的"Price lock"快照 + 接受→付款 | `quotes.php`、ADR-0004、工单 010/011 | **不需要** | PV 批发里只有 Segen 和 Sonepar 在账户里显示报价，而且两家都是把报价当作"转成网上订单"的中间物。de-linker 没有网上下单和付款。有效期改为 PI 上的"Gültig bis"即可：BayWa 报价 30 天有约束力，Segen 7/30 天，Memodo 价格以开票日为准，Krannich 报价 freibleibend |
| Proforma 讨论流：ready / in_discussion / updated / closed | `proforma-workflow.php` | **不需要** | 竞品都没有客户可见的谈判状态；谈判由具名对接人在线下完成 |
| 文件账本 v3（proformas[]、invoice、adjustments[]、quotes[]）+ 自制渲染器 + 网站发票号 | `order-document-lifecycle.php`、`documents.php` | **不需要** | PI 由 WP Overnight Pro 替代；发票和贷记单归会计系统（§4.4） |
| 保存的支付方式 / Stripe / 支付闸门 | `account-payment-methods.php`、`payment*.php` | **不需要** | 老板 2026-10-07 的裁定；PV 批发以预付转账或账期为主（Krannich、Memodo） |
| Order-next-action 引擎、运费确认流程 | `order-next-action.php`、`tv_b2b_confirm_order_freight()` | **不需要** | 只有 4 个状态时"下一步"不言自明；运费就是 PI 上的一条 shipping 行 |
| 跨项目的"Documents"页 | documents 端点（`account-portal.php`） | **不需要** | 竞品的单据都挂在订单上（Krannich、IBC、Sonepar）；产品文件放在公开产品页或下载中心 |
| Bulk order | `bulk-order.php` | **映射不要求，可删** | 快速下单只有 3/9（+1 个 ◐），服务的是高频复购；询价站用购物车里的数量就够了 |
| Projects & Support | `project-portal.php` 等 | **收缩** | 选型输出保留为 Gespeicherte Auswahl；Support 改为对接人区块 + 邮件。保存清单/BOM 有 8/9，属于通用；但竞品都没有逐项目的支持工作区。删除前要先核对 Advisor 对这块存储的依赖 |

**保留的：**

| 组件 | 位置 | 处理 | 依据 |
|---|---|---|---|
| "Proformas"（orders 端点改名后的列表） | `account-portal-render.php` | 思路保留，改用 Woo 原生列表 + 4 个状态 + PI 下载 | §3.4 |
| 公司资料、地址、VIES 校验 | `account-settings.php`、`vat-service.php` | 原样保留 | 普遍 |

**映射说必须新增或补齐的：**
1. 「Anfragen」列表的 4 个状态和 PI 下载（Woo 原生 + Pro）。
2. 概览页上的「Ihre Ansprechperson」（9/9 都有）。
3. 询价详情里每一行的数据表链接（复用托管文档）。
4. 同一个编号贯穿确认邮件、PI 和账户（McKinsey 和 Gartner 的一致性要求）。
5. 「Erneut anfragen」（扩展 order-again 的适用状态）。
6. Gespeicherte Auswahl → 「Als Anfrage senden」。

**删除前要做的事：** 先查生产环境里现有订单、报价和 PI 的真实数量。只有存在真实客户数据时，才需要决定旧 PI 怎么展示（例如作为 PDF 附件挂在原订单上）；没有真实读者就不做迁移。

### 5.6 需要业主回答的事实（只问事实）

1. **Linker 的正式发票现在由哪个系统开？**（会计软件、税务顾问或 ERP）这决定网站是否完全不出发票；默认答案是不出。
2. **PI 有效期多少天？** 参考：BayWa r.e. 报价 30 天内有约束力；Segen 报价价格锁定 7 天（南非）或 30 天（英国）；Memodo 价格以开票日为准。
3. **是否承诺询价回复时限？** 没有承诺就不在文案里写小时数。

另外，PI 上的税额怎么呈现，请税务顾问确认。这是税务问题，不是语言问题。

### 5.7 实施前在 staging 验证（技术事项，不问业主）

- WP Overnight Pro 在本站自制 i18n 下能否正确切换 DE/EN。
- 免费状态插件的标签和邮件能否走 linker-i18n；不行就改用小段自定义代码。
- 块结账里 BACS 的标题、说明，以及"Anfrage senden"按钮文字。
- 生产环境现有订单、报价、PI 的数量。
- Advisor 对 project 存储的依赖。

---

## 附录 A — 主要来源（抓取日 2026-10-09；括号内为页面自带日期）

**竞品**
- Memodo：https://www.memodo.de/m/support/hilfe/ ；https://www.memodo.de/zahlung/ ；https://www.memodo.de/m/willkommen-bei-memodo/ ；https://www.memodo.at/partlistimport ；https://service.memodo-shop.com/s/?language=de ；https://www.memodo.de/agb/ ；https://www.youtube.com/watch?v=wbf6VPe4YPU （2024-04-11）
- Krannich：https://www.youtube.com/watch?v=9lr14132Ui8 （2023-10-25）；https://www.youtube.com/watch?v=ZkJp4Ly17go （2022-11-24）；https://www.youtube.com/playlist?list=PLi05zH0uftYdAyTeLp_qTTq7l0R_d7kJ5 （更新于 2026-03-12）；https://shop.krannich-solar.com/de-de/account/request-registration ；https://shop.krannich-solar.com/en-de/Footer/Information/FAQ ；https://shop.krannich-solar.com/en-de/anfrage-pv-projekt-ab-400-kwp ；https://krannich-solar.com/de-de/alb/ ；https://www.linkedin.com/posts/shopware-ag_case-study-krannich-activity-7449781407683407872-YF9g
- Segen：https://segensolar.de/portal/ ；https://segensolar.eu/portal/ ；https://portal.segen.co.uk/ ；https://segensolar.co.za/products/ ；https://segensolar.tz/about-us/ ；https://www.youtube.com/watch?v=uXGwjFrGBAg （2015-03-23）
- BayWa r.e.：https://www.youtube.com/watch?v=_Ez3MH0F3-M 与 https://www.youtube.com/watch?v=hvmBz-Tdxp0 （2020-05-28）；https://www.pveurope.eu/specialized-trade/baywa-re-steps-smarter-tools-and-bigger-goals （2025-06-20）；https://solar-distribution.baywa-re.lu/de/agb ；https://solar-distribution.baywa-re.de/services/fuer-installateure/kundenservice-logistik/
- IBC SOLAR：https://portal.ibc-solar.com/de/ ；https://portal.ibc-solar.de/ ；https://portal.ibc-solar.de/faq ；https://www.ibc-solar.com/login/ ；https://www.youtube.com/watch?v=7im7OrQ5w2c （2022-01-20）；https://www.dc.ag/de/projekte/ibc-solar
- Sonepar：https://www.sonepar.de/c/services-loesungen/beschaffung-lager/onlineshop ；https://www.sonepar.ch/de/so/startseite/services/bestellservice/webshop ；https://www.sonepar.it/de-it/static/faq ；https://www.sonepar.de/c/services-loesungen/beschaffung-lager/e-procurement/schnittstellen/ugl-schnittstelle ；https://apps.apple.com/de/app/sonepar-shop/id6451204403 ；https://soneparsuisse.zendesk.com/hc/de-ch/articles/12662932366621-Wie-kann-ich-den-Warenkorb-als-Merkliste-speichern
- EWS：https://pv.de/en/login/ ；https://pv.de/registrierung/ ；https://pv.de/produkte-preise/ ；https://pv.de/news/quickshop-der-online-fachberater-fuer-pv-profis/ （2022-04-06）
- Wattkraft：https://www.wattkraft.com/ ；https://www.wattkraft.com/kontakt/ ；https://wattkraft-de.zendesk.com/hc/de-de
- Alibaba / Accio：https://activity.alibaba.com/page/resources/how-to-send-an-effective-inquiry.html （2021-02-03）；https://activity.alibaba.com/page/resources/What_goes_into_an_effective_purchase_order.html （2021-02-03）；https://rfq.alibaba.com/rfq.html ；Alibaba 帮助中心 RFQ 与税票两页（链接见 §2.1）；https://static.accio.com/accio-user-guide.html ；https://www.accio.com/wow/guide-accio-vs-alibaba.html

**术语与法规**
- https://www.lexware.de/wissen/unternehmerlexikon/proforma-rechnung/ （2026-08-05）
- https://www.ihk.de/rhein-neckar/international/export-import/ausfuhr-eu/basisinfo-export/exportrechnung-proformarechnung-950590
- https://rechnungskit.de/wissen/proforma-rechnung （2026-09-24 / 2026-10-03）
- https://stripe.com/de/resources/more/pro-forma-invoices-germany
- https://datax-gmbh.de/pro-forma-rechnung/
- https://www.skydo.com/blog/proforma-invoice-vs-quotation （2026-09-29）
- https://www.newbuyingagent.com/wiki/proforma-invoice-pi （2026-03-09）
- https://www.gesetze-im-internet.de/ustg_1980/__14.html
- https://fortlauf.de/wissen/fortlaufende-rechnungsnummer/ （2026-07-25）
- https://www.goerler-partner.de/de/service/e_rechnungspflicht_im_b2b_bereich_ab_2025/index.html

**买家预期**
- Gartner：2025-06-25、2026-03-09、2026-05-20 三篇新闻稿（链接见 §3.3）
- McKinsey 2026 B2B Pulse（2026-05-28）
- DuoByte 对 ECC KÖLN B2BEST Barometer Vol. 23 的转引（2026-10-03）
- https://toimi.pro/blog/b2b-customer-portal-features/ （2026-10-01）
- https://virtocommerce.com/blog/b2b-ecommerce-quote-management （2026-05-04，厂商）
- https://experienceleague.adobe.com/en/docs/commerce-admin/b2b/quotes/quotes （2026-05-14）
- https://chatsku.com/b2b-quote-response-time/ （2026-09-29，厂商）

**WooCommerce 与插件**
- https://developer.woocommerce.com/2026/08/04/woocommerce-11-0/
- https://woocommerce.com/document/managing-orders/order-statuses/
- https://woocommerce.com/document/bacs/
- https://github.com/woocommerce/woocommerce/issues/68289 （2026-09-02）
- https://www.businessbloomer.com/woocommerce-managing-initial-order-status/ （2025-06-09）
- https://wholesalesuiteplugin.com/woocommerce-order-without-payment/ （2026-09-25）
- https://wordpress.org/plugins/invoice-gateway-for-woocommerce/
- https://wordpress.org/plugins/wc-place-order-without-payment/
- WP Overnight 三个页面与 Order Proposal（链接见 §4.3–4.4）
- YITH 两个插件、Addify 两个扩展、B2BKing、Wholesale Suite、Flexible Invoices、Bas Elbers、Germanized、WebToffee（链接见 §4.3–4.4）
- 本地核验：`output/system-delivery/local-site/wp-content/plugins/woocommerce`（WooCommerce 11.1.0）中的 `includes/gateways/bacs/class-wc-gateway-bacs.php`、`includes/class-wc-order.php`、`includes/wc-stock-functions.php`、`includes/emails/class-wc-email-new-order.php`、`templates/emails/customer-invoice.php`、`templates/emails/customer-on-hold-order.php`
