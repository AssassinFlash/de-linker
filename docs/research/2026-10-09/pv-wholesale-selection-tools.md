# 德国与欧洲 PV / 储能批发商如何在线帮安装商选型（2026-10-09）

**问题：** 2026 年，德国和欧洲的 PV 与储能批发商、分销商用哪些在线手段帮安装商**选设备**？de-linker.com（德国 B2B 光储贸易，约 100 个商品，买家是安装商、EPC 和经销商）的导购助手应当照搬行业做法，而不是照搬消费类 App。

**方法：** 所有外部检索和页面读取都经过 Apify REST：检索用 `apify/google-search-scraper`（地区 de，语言 de，5 批约 80 个德英关键词）；页面用 `apify/website-content-crawler`（Playwright Firefox）。筛选维度是用 `keepElementsCssSelector` 只保留各店铺列表页的 filter/facet 节点后读出的。全部数据取于 **2026-10-09**。

几处读取受阻，均已换路补齐：`apify/cheerio-scraper` 要求账号授予完全权限而被拒，改用 content-crawler；IBC 的 Intersolar 新闻稿和 pv-magazine 的 SAJ 文章返回 404；GoodWe Designer 页面只渲染出国家列表；Memodo 列表页需等 12–15 s 的 JS 才出现筛选面板；LinkedIn 文章只能读到公开部分。

**标注：** 【事实】有来源原文支撑，附 URL 和日期（未注明日期的，即为 2026-10-09 读取时的页面状态）。【推断】是从事实推出的判断，供决策参考。【未找到】表示多关键词、多来源检索后没有发现，不等于不存在。

**截图：** 本次没有在本地截图。下文给出各工具官方页面上公开的截图 URL，可以直接打开查看。

---

## 0. 结论速览

1. **行业主流不是“对话式导购”，而是三件套：** ① 店铺列表页的**技术参数筛选**（相数、AC 功率、MPPT、可用容量、HV/48 V、是否支持备用电源）；② **预先配好的“逆变器 + 电池”套装 SKU**，再配一份**兼容/放行清单**（Freigabeliste、Speicher-Matrix、Übersichtsblatt）；③ 一个**设计工具**，产出**物料清单（Stückliste）**，一键转入购物车或报价。设计工具有两种来源：批发商自研的 Solar-Planit、PV Manager、QuickPlan/QuickCalc、pvXpert；或者批发商汇总的厂商工具页。
2. **准入方式：** 价格、库存和下单普遍要登录，或者需要人工审核开户（Segen、BayWa、IBC、Sonepar、Rexel）。说明内容和兼容清单 PDF 多数公开。设计工具有免费的（Solar-Planit、Sunny Design、SmartDesign），也有付费的（pvXpert 每年 890 €，另加 190 € 必修培训；IBC PV Manager 按许可证出售）。
3. **工具最后都交回给人：** 几乎每个工具的终点都写着“交给你的销售对接人 / 报价部门 / Projektanfrage”。EWS 明说它的组合总表“不替代专业项目设计”，并指向报价部门；Krannich 的商用储能走 Projektanfrage PDF 表单；PVSelected 用聊天收需求，24 小时内由人工给报价。
4. **AI 助手：** 本次调查的目标批发商（Memodo、Krannich、BayWa、Segen、IBC、EWS、Wattkraft、Sonepar DE、Rexel DE 等）**都没有找到公开的选型 AI 聊天【未找到】**。目前唯一有一手证据的“批发商级 AI 选品助手”是北欧电气批发商 **Solar Group 的 Solar Assistant**（2024-12）。它只基于自家封闭的产品目录，结果直接写进购物车，支持 5 种语言。厂商一侧的“AI”几乎全是**终端用户的能源管理（EMS）**，例如 Fronius ECA、Huawei Smart Assistant、SolarEdge Sera、SAJ elekeeper；另一类是**设计软件里的 AI 屋顶建模**（SolarEdge Designer），都不是选型顾问。
5. **对 de-linker 的含义【推断】：** 助手应说安装商的行话，按“相数 → 功率 → 电池电压等级 → 容量 → 备用电源 → 通讯/接口”的顺序收窄。兼容判断必须来自“双方厂商的放行（Freigabe）”这一类事实来源。产出应当是**带数量的物料清单**，交给购物车、Proforma 或项目询价，并留一个找人的出口。屋顶 3D、静力计算、收益率营销、个性化推荐这些消费类做法都不适用。

---

## 1. 逐家：在线选型 / 配置工具

### 1.1 Memodo（慕尼黑）

- 【事实】“Werkzeuge”工具箱页面汇总了独立性计算器（Unabhängigkeitsrechner，算自用比例和自给率）、厂商 **PV-Auslegungstools** 合集，以及用于支架、**商用储能**和供暖的 **Erfassungsbögen（项目采集表）**，配有“Vertraue bei der Planung auf unsere Experten”一句。— https://www.memodo.de/m/werkzeuge/
- 【事实】PV-Auslegungstools 页按逆变器、家用储能、供暖、支架、通用规划分组，**链接各厂商的免费工具**，例如 Optisizer（商用 PV+储能的仿真与经济性分析）和 PVsyst。— https://www.memodo.de/m/werkzeuge/pv-auslegungstools/
- 【事实】**Vergleiche & Freigabelisten：** 提供家用储能 HV、家用储能 NV（48 V）、商用储能、商用逆变器的对比 PDF，以及**HV 和 48 V 储能放行清单**。原文：“welche Speicher- und Wechselrichter-Kombinationen kompatibel sind und welche Voraussetzungen für Notstrom- oder Ersatzstrombetrieb gelten”。页面上的“Stand”日期为 2025-01-01 / 2026-01-01。— https://www.memodo.de/m/werkzeuge/memodo-vergleiche-freigabelisten/
- 【事实】放行清单页的关键说明有三条：
  - 一个组合要成立，**逆变器厂商和电池厂商的放行必须同时存在**。
  - HV 组合常因逆变器的充放电电流小于电池而出现**直流功率降额**，清单会逐个组合标出。
  - HV 系统的备用/应急电源功能“meistens nur vom Wechselrichter abhängig”；48 V 系统要做备用电源，必须保证充放电功率足够。48 V 清单写明**每台逆变器需要哪种电池、需要几块**。
  - 来源：https://www.memodo.de/m/werkzeuge/stromspeicher-freigabeliste/ （PDF：https://www.memodo.de/m/fileadmin/dach/werkzeuge/freigabeliste/2025/q1/stromspeicher-freiagbeliste-hv.pdf ）
- 【事实】家用储能列表页的筛选面板（JS 渲染后读出）：**Ab Lager verfügbar**、**Nur Angebote anzeigen**、**Batteriekopplung**、**MPP-Tracker**、**Modellreihe**、**Nettokapazität (kWh, Min–Max)**、**Speicher-Typ**（选项为 1-phasig / 3-phasig / 48 V Batterie / Hochvolt Batterie / **Speicher-Nachrüstung**）、**Garantie**。— https://www.memodo.de/photovoltaik/heimspeicher/
- 【事实】据 Google 摘要：组件页可按“Technologie, Bauweise, Leistung, Steckertyp oder Schnee- und Windlast”筛选；逆变器页写着“Module, Speicher, Wallboxen und Zubehör legst du im selben Warenkorb dazu”，并为商用项目给出商用逆变器对比。— https://www.memodo.de/photovoltaik/solarmodule/ ，https://www.memodo.de/photovoltaik/wechselrichter/ （Google 摘要，2026-10-09）
- 【事实】商品页（PDP）示例 Sigenergy Hybrid 8.0 kW TP2：
  - 规格列表包括 Nennleistung、MPPT 数量、IP 等级、MPPT 电压范围和通讯接口（WLAN、Ethernet、RS485、选配 4G）。
  - **“配套关系”写在正文里：** 要配 Sigen Gateway 才能实现备用电源；电池塔所需部件都包含在 SigenStor BC 里，并链接到该 SKU。
  - 页面标明渠道限制“Kein Verkauf an gewerbliche Wiederverkäufer”。
  - 来源：https://www.memodo.de/sigenergy-sigen-hybrid-wechselrichter-8.0-kw-tp-2-dreiphasig/14409
- 【事实】早期上线稿（未注明日期，文中引用了 2015 年数据）提到：只对安装商和经销商开放，可查交期，可下载资料，有“Chatfunktion – der direkte Draht zu unseren Mitarbeitern”（人工聊天）。— https://www.photovoltaik.eu/solarspeicher/neu-memodo-b2b-onlineshop-fuer-speicher-pv
- AI：【未找到】Memodo 自营的 AI 选型助手。Memodo 2026 年的网络研讨会议程里出现的 AI，是 SolarEdge 面向终端用户的“KI-Energie-Assistent Sera”（https://app1.edoobox.com/en/memo/Events%20DE/Webinare/2026/ ，Google 摘要）。

### 1.2 Krannich Solar

- 【事实】**WR-Speicher-Sets** 类目：共 446 个套装 SKU，每个是“储能 + 兼容逆变器”的组合，例如“B-Box HVS+ 5.1 + PLENTICORE MP S G3”“LUNA2000-7-S1 + SUN2000-3K-LB0”。类目文案为“Speicher bis 30 kWh und kompatible Wechselrichter im Set, sorgsam zusammengestellt von Ihrem Großhändler”。— https://shop.krannich-solar.com/de-de/ ，https://shop.krannich-solar.com/de-de/WR-Speicher-Sets
- 【事实】套装列表的筛选：**Hersteller Kombination**（例如“BYD + SMA (26)”“Pylontech + Goodwe (4)”）、**AC Nennleistung (kW)**、**Nutzbare Kapazität (kWh)**、**Max. AC Leistung (kVA)**、**Max. Eingangsstrom gesamt DC (A)**、**Ersatzstromfähig**（ja / **ja mit Zubehör** / nein）、**Anzahl der MPP-Tracker**、环境温度上下限。— 同上
- 【事实】混合逆变器列表（243 件）的筛选：**Hersteller**、**AC Nennleistung (kW)**、**Einspeisephasen**（3 / 1）、**Max. AC Leistung (kVA)**、**Max. Eingangsstrom gesamt DC (A)**、**Produktgarantie (Jahre)**、**Ersatzstrom light**（ja / ja mit Zubehör / nein）、**MPPT 数量**、**Schnittstelle 1/2**（RS485 / W-Lan / Ethernet / Bluetooth / USB）、温度、**Anschluss Rundsteuerempfänger**（ja / ja mit Zubehör / nein）。商品卡片的短描述写法是“Hybrid-WR, 2 MPPT, SPD, AFCI, 1-phasig”，下方再列 AC 额定功率、MPPT 数和并网相数三项。— https://shop.krannich-solar.com/de-de/Wechselrichter/Hybridwechselrichter
- 【事实】类目文案直接写出兼容问题：“Nicht jeder Speicher ist mit jedem Wechselrichter kompatibel. Daher bieten wir Sets und eine Übersicht kompatibler Geräte an.”；同时区分 DC-/AC-Speicher（AC 型“beliebt bei Nachrüstungen”）。— https://shop.krannich-solar.com/de-de/Heimspeicher
- 【事实】逆变器选型标准原文：Stranglänge/Eingangsspannung/MPPT、**Batteriekompatibilität**、Netzanschluss（70 %-Regel、VDE-AR-N 4105/4110）、Kommunikation（WLAN、LAN、Modbus、RS485、Smart Meter Gateway）。逆变器分为 PV-WR、Speicher-WR（AC 耦合加装）、Hybrid-WR、Mikro-WR 四类。— https://shop.krannich-solar.com/de-de/Wechselrichter
- 【事实】“Auslegungstools für Profis”页面汇总厂商工具：SOLIVIA、Enphase（含**模块兼容性计算器**和 Solargraf，后者可生成物料清单）、GoodWe Designer、Huawei SmartDesign 2.0、KACO String Sizing、KOSTAL Solar Plan（要求在 Solar Terminal 登录并具备“Planung”角色）、SigenStack Calculator、Sunny Design Pro、Sofar String Sizer (Excel)、SolarEdge Designer、SolarLog Configurator、SolaX Design、iSolarDesign、K2 Base 等。页面写明需要更多咨询时找“persönlicher Ansprechpartner”。— https://shop.krannich-solar.com/de-de/Services/Auslegungstools
- 【事实】商用储能走 **Projektanfrage（PDF 表单）**，“Krannich Solar unterstützt Sie bei Planung, Auslegung …”。— https://krannich-solar.com/de-de/blog/gewerbespeicher-notstrom/ ，下载页：https://shop.krannich-solar.com/de-de/Services/Downloads
- 【事实】商品页另有“Fragen zum Produkt”人工询问入口；站内有“Angebote für Profis: Palettenpreise & Projektkonditionen”。— https://shop.krannich-solar.com/de-de/Fragen-zum-Produkt?productId=53844a93401b5dee5e08526ea4d209dc （Google 摘要）
- 【事实，历史】2020 年曾有 WebPortal 内的 **Trinity-Konfigurator**：输入目标 PV 功率和年用电量，按**自给率升序**列出可选套装，一键加入购物车。— https://www.si-shk.de/online-konfigurator-von-krannich-81350/ （2020-12）。2026 年是否仍在使用：【未核实】。
- AI：【未找到】自营选型 AI。网络研讨会主题里有“AI-powered energy management systems”（厂商 EMS）。— https://shop.krannich-solar.com/en-de/intersolar

### 1.3 BayWa r.e. Solar Trade（含 Solar-Planit；瑞士 Solarmarkt）

- 【事实】网店需要开户（“Sie haben noch keinen PV-Webshop-Zugang bei uns?”），提供 **DATANORM** 接口下载商品和价格数据，可**通过 Solar-Planit 导入物料清单**。— https://solar-distribution.baywa-re.de/de/
- 【事实】**Solar-Planit**：免费（“No licence or subscription fees”），15 个国家可用。流程依次是：
  1. 选地点（风荷载、雪荷载分区）；
  2. 屋顶类型和尺寸（3D 或上传图纸、卫星图、无人机图）、屋面材料；
  3. novotegra 支架和静力/配重计算；
  4. 排布组件、标出禁用区；
  5. **选择匹配的逆变器和储能**；
  6. 用电曲线、经济性、CO₂ 计算；
  7. 补充附加商品（如充电桩）；
  8. 已注册的网店用户可把**完整物料清单转入 BayWa 网店**。
  - 规划可以分享给 BayWa 销售。
  - 来源：https://solar-planit.com/ ；英文服务页：https://solar-distribution.baywa-re.lu/en/services/free-engineering-tool-solar-planit （“recommending the most suitable inverters and storage systems”）
- 【事实】2026 年更新：
  - 上传建筑图纸、卫星图、无人机图；平屋顶自由形状排布；自动识别禁用区；按所选组件生成可导出的**电气单线图**，方便电网报装。— https://www.photovoltaik.eu/planung/solar-planit-neue-funktionen-fuer-eine-effizientere-planung （2026-01-19）
  - 新项目总览，支持 Kanban、自定义状态、组内共享和修改记录；屋顶类型、组件、逆变器、系统和储能容量“at a glance”。— https://www.pveurope.eu/planning/solar-planit-puts-project-overview-front-and-centre （2026-08-06）
- 【事实】逆变器列表筛选：**Hersteller**、**MPP-Spannung min/max**、**Stromstärke in A**、**Anzahl MPPT**、**Netzanschluss**（1-phasig / 3-phasig）、**Max. Leerlaufspannung**、**System**（Hybrid-Wechselrichter / PV-Wechselrichter）、Leistungs-/Produktgarantie、**Preis (netto)**、尺寸。— https://solar-distribution.baywa-re.de/wechselrichter/
- 【事实】**Speicher-Sets** 类目：每个套装有独立货号，例如“BYD HVM 11.0 (BCU 2.0) + SMA STP 10.0-3SE, inkl. SunnyHomeManager”，货号 SET-12SE100110；页面有“**Artikel vergleichen**”对比功能，并显示“Derzeit nicht bestellbar”这类状态。— https://solar-distribution.baywa-re.de/speicher-sets/
- 【事实】储能类目页在“Planung”一项写着“Online-Planungstool Solar-Planit und PV-Systemkonfigurator”，在“Kompatibilität”一项写着“Als Anbieter von Komplettsystemen”；并给出按 PV 功率和年用电量推荐储能容量上限的图表（引用 HTW Berlin 独立性计算器）。— https://solar-distribution.baywa-re.de/speicherkomponenten/
- 【事实】博客教安装商使用厂商配置器，例如 Enphase System Builder，四步得出可导出的物料清单。第一步问国家、配置（仅 PV / PV+电池 / **IQ 电池加装**）、**相数**；后面依次问组件功率、数量、朝向，微逆型号，**相数和 kWh**，电池，以及选项（调制解调器、Wallbox、SG-Ready 热泵）。页面有截图，例如 https://toxid-solar-distribution.baywa-re.de/fileadmin/_processed_/2/5/csm_System-builder-Enphase-Energy-Schritt1_System_c51692443b.png 。— https://solar-distribution.baywa-re.de/blog/der-system-builder-von-enphase-energy/ ；工具本身：https://enphase.com/de-de/installers/systems
- 【事实】奥地利站托管 BYD HVB/HVM/HVS **Compatible Inverter List**。— https://solar-distribution.baywa-re.at/out/media/19-Battery-Box_HVSplus_Compatible_Inverter_List_Battery_Box_HVB_HVS__HVM__V1.0_25... （Google 摘要）
- 【事实】**Solarmarkt GmbH（瑞士 Aarau，批发商）：** 首页面向业主（Bauherrschaften）提供 Solarrechner、Eigenverbrauchsrechner、Carportkonfigurator、补贴信息，并声明“Als Grosshandelsunternehmen … planen und bauen wir Anlagen nicht selber”。— https://www.solarmarkt.ch/de 。BayWa r.e. Solar Trade 的 LinkedIn 帖子把 Solarmarkt 称为“Our colleagues at SOLARMARKT”。— https://www.linkedin.com/posts/bwre-solartrade-global_solarmarkt-... （Google 摘要）
- AI：【未找到】BayWa Solar Trade 的 AI 选型助手。

### 1.4 Segen（UK / DE / EU）

- 【事实】DE 门户需要注册（填写联系表后开通账号）。门户提供：实时库存和未来到货、数据表和保修文件，以及两个自研工具：
  - **“Wechselrichter-Auslegung”**：为任意系统找到合适的逆变器，并给出**组串方案**；
  - **“Quick-Angebot”**：规划组件、逆变器和支架后**直接下单**。
  - 另有 Renusol Configurator 3.0 负责支架设计。
  - 来源：https://segensolar.de/portal/ ，https://segensolar.de/pv-produkte/batteriespeicher/
- 【事实】UK 门户：“live pricing 24/7 … current availability, the stock location, and future availability … design tools and configurators … quotes”；每个客户配有 **Sales Manager、Fulfilment Manager、Technical Support Engineer**。— https://www.segen.co.uk/portal/
- 【事实】南非站：“24/7 Online Portal with **Kit Builder** … custom system builds”。— https://segensolar.co.za/ （Google 摘要）
- AI：【未找到】。

### 1.5 IBC SOLAR

- 【事实】**PV Manager**：付费许可，在 IBC 网店购买；2026 年起改为 Web 版（https://www.ibc-blog.de/2026/06/pv-manager-jetzt-als-web-version/ ）。功能覆盖：
  - 建筑与屋顶规划（阴影、雪荷载）；支架与配重；按 EuroCode 出具可审查的静力计算；
  - **逆变器和储能规划**、自用分析、标准负荷曲线（住宅、商业、**热泵**、农业、**电动车**）；
  - 带公司 Logo 的**报价 PDF**，可加入自有条目，含经济性计算；
  - **完整物料清单，一键在 IBC 网店下单**，按“tagesaktuelle, persönliche Einkaufskonditionen”计价。
  - 页面截图：https://www.ibc-solar.de/fileadmin/redaktion/de/Installateure/Produkte/PV-Mananger-Bestellung.png 、https://www.ibc-solar.de/fileadmin/redaktion/de/Installateure/Produkte/PV-Manager-Angebot.png 。
  - 来源：https://www.ibc-solar.de/installateure/produkte/pv-manager/
- 【事实】**Speicherpakete** 类目让安装商对照可下载的 **Speichermatrix (PDF)** 自行组合储能套装；需要更大的套装时“kontaktieren Sie bitte Ihren Vertriebsmitarbeiter”。— https://shop.ibc-solar.de/products/de/shop/PV/Speicher/Speicherpakete/ ；矩阵说明：“In Form einer Matrix werden Kompatibilitäten …”。— https://kiosk.ibc-solar.de/ibc-solar-speicher-matrix/63188591 （Google 摘要）
- 【事实】网店只对已注册的商业客户开放；面向私人客户另设 **Stromrechner**，并把他们转介给当地合作安装商。— https://shop.ibc-solar.de/
- AI：【未找到】。

### 1.6 EWS（pv.de）

- 【事实】服务项目包括 **QuickPlan（系统规划）、QuickCalc（系统计算器）、QuickContent（安装商网站配置器）**、技术咨询和联系人转介。— https://pv.de/leistungen/
- 【事实】QuickCalc（丹麦语页面）：快速计算单个询价，**给出针对项目的产品推荐**，**显示产品随时间的可用性**，**推荐可替代的现货产品**，单独计算运费，可加入安装费等自有加价，生成带自家 Logo 的报价，**无许可费**。注册用户可使用价格计算、出报价和客户沟通功能。— https://pv.de/dk/ydelser/systemberegner/fordele-ved-installatoren-et-overblik-quickcalc/
- 【事实】QuickCalc 4.0 集成支架规划（含 K2）：安装商在 Quickcalc 输入地点和建筑数据、画屋顶、排组件，后台按项目自动算出所需材料并生成文件，**一键订购**。— https://www.solarserver.de/2024/12/20/ews-pv-montage-planen-komponenten-bestellen-in-einem-schritt/ （2024-12-20）
- 【事实】**Übersichtsblatt “Speicherportfolio – Systemkombinationen”**（PDF）回答这些问题：“Welcher Wechselrichter lässt sich mit welchem Speicher kombinieren? Welche Speicherkapazität ist nutzbar? Welches System ist notstromfähig, welches skalier- bzw. erweiterbar?”。原文同时说明“nicht die professionelle Projektierung ersetzt”，并指向 **Angebotsabteilung**；登录后在 Händler-Login 的“Projektabwicklung”栏可看到最新版。— https://pv.de/news/speicher-und-wechselrichter-richtig-kombinieren-ews-uebersichtsblatt/
- 【事实】网店：“Echtzeit-Verfügbarkeiten und ein Online-Kalkulationstool für komplette PV-Systeme”。— https://pv.de/produkte-preise/ （Google 摘要）
- AI：【未找到】。

### 1.7 Wattkraft（Huawei / AIKO / Phono / Canadian Solar 分销商）

- 【事实】Wattkraft 不直接面向安装商开店，而是列出“Bezugsquellen / Handelspartner”（EWS、Krannich、Segen、Rexel、Sonepar 等）。— https://www.wattkraft.com/
- 【事实】服务内容是**人工的**：为较大项目提供 Huawei 逆变器的“Planungsunterstützung & Layoutservice”；按 BDEW / VDE-AR-N 4105 计算谐波和干扰水平（要求提供逆变器数量和型号、并网规范、电网短路容量 SKV 等）；德语热线和工单系统。— https://www.wattkraft.com/unternehmen/service/
- 【推断】设计工具依赖厂商的 Huawei SmartDesign 2.0（见 §3）。

### 1.8 Sonepar / Rexel（电气综合批发商）

- 【事实】Sonepar Österreich 网店：逆变器列表对未登录用户显示“**Für Preisinformation und Bestellung bitte anmelden**”，卡片只显示厂商货号和“Bemessungsspannung MPP”。— https://www.sonepar.at/catalog/de-at/category/wechselrichter-17277
- 【事实】Sonepar Suisse **PV-Konfigurator**（登录后使用）输入：屋顶结构、安装方式、屋顶面积、屋面材料、**期望的逆变器类型**、组件产地。输出“**Grobkostenübersicht**”（粗略成本），之后由专家出“Detailofferte”。帮助页有截图。— https://soneparsuisse.zendesk.com/hc/de-ch/articles/12642094474013-Was-ist-der-PV-Konfigurator-und-wie-arbeite-ich-damit
- 【事实】Sonepar Deutschland **Digiplan**：电气和照明规划的云应用，支持 LiDAR 扫描户型、**KI-gestützte Symbolerkennung**；符号关联到货号，**自动生成物料清单并在 Sonepar 网店下单**。— https://www.sonepar.de/c/services-loesungen/planung-organisation/sonepar-digiplan 。据第三方说明，德、奥、瑞的 Sonepar PV 规划使用 Solarschmiede 软件。— https://www.solarschmiede.de/systemanbieter/sonepar/ （Google 摘要）
- 【事实】Rexel Germany **pvXpert**：只供 Rexel 客户使用，年费 890，另有一次性必修培训 190。可基于卫星图和 CAD 完成项目，包括静力报告、**逆变器设计**、物料清单、安装图；**不显示库存**，但物料清单可以快速转入 Rexel 网店；ERP 可通过 **IDS 接口**接收清单再出报价。— https://www.rexel.de/rexeleasy/pvxpert
- AI：Sonepar Digiplan 有 AI 符号识别（规划用途，不是选型对话）。【未找到】Rexel DE 或 Sonepar DE 的 AI 选型聊天。

### 1.9 Solartraders / sun.store（B2B 交易市场）

- 【事实】Solartraders：B2B 交易市场，需要注册（免费），把 100 多家分销商的报价放在一起比价，提供第三方托管支付（Treuhand）；大型项目可“direkt beim Hersteller”采购。— https://www.solartraders.com/de
- 【事实】储能报价卡片显示字段为“Speicher: 16 kWh. Spannung: Niedervolt. Zelltechnologie: LFP (LiFePO4). Produkt-Garantie: 8000 Zyklen … Preise vergleichen … ab Lager”。选型文案列出：容量与功率、循环寿命、**兼容与集成**、认证（VDE-AR-E 2510-50）。— https://www.solartraders.com/de/products/speicher （Google 摘要 + 页面正文）
- 【事实】sun.store：“Find, compare, and buy PV equipment … comparing multiple offers”，聚合数百家欧洲卖家的现货和价格。— https://sun.store/en 。AI：【未找到】。

### 1.10 PVO International

- 【事实】**已于 2026-07-01 停止营业**：“All remaining stock has been sold and we are no longer accepting new orders”。— https://www.pvo-int.com/de/ 。不再作为参照对象。

### 1.11 其他相关做法（补充样本）

- 【事实】PVSelected（Willich）：“**Smart Request** – Kein langweiliges Kontaktformular. Sagen Sie uns einfach im Chat, was Sie brauchen – wir melden uns innerhalb von 24h mit Ihrem individuellen Angebot”；另有“PVSelected Konfigurator”（在线规划，自动选组件）和带透明库存的 B2B 网店。— https://pvselected.com/
- 【事实】Densys pv5 储能列表筛选：Hersteller、Aktionen、**Kapazität netto (kWh)**、**Technologie**（Gewerbespeicher / **Hochvolt** / **Niedervolt**）、**Schnittstellen**（CAN、RJ45）、Produktgarantie、Schutzklasse（IP21–IP66）、**Richtlinienkonformität**（VDE 2510-50、VDE 4105、IEC 62619、IEC 62040-1 …）、重量和尺寸；另提供含逆变器和全部附件的“Speicherpakete”。— https://densys-pv5.de/stromspeicher?all

---

## 2. 共同的筛选维度和行话；“兼容”怎么呈现

### 2.1 逆变器筛选（交叉汇总 Krannich、BayWa、Memodo）

| 维度 | 各家写法 | 来源 |
|---|---|---|
| 相数 | Einspeisephasen 1/3（Krannich）；Netzanschluss 1-phasig/3-phasig（BayWa）；Phasen: 3（Memodo PDP） | Krannich 混合 WR；BayWa WR；Memodo PDP |
| 类型 | System：Hybrid-Wechselrichter / PV-Wechselrichter（BayWa）；PV-WR / Speicher-WR / Hybrid-WR / Mikro-WR（Krannich） | 同上 |
| 功率 | AC Nennleistung (kW)、Max. AC Leistung (kVA) | Krannich |
| DC 侧 | Anzahl MPPT、MPP-Spannung min/max、Max. Leerlaufspannung、Max. Eingangsstrom DC (A) | BayWa、Krannich |
| 备用电源 | Ersatzstrom light：ja / **ja mit Zubehör** / nein | Krannich |
| 并网与控制 | Anschluss Rundsteuerempfänger；文案中的 VDE-AR-N 4105/4110、70 %-Regel、Smart Meter Gateway | Krannich |
| 通讯 | Schnittstelle：RS485 / WLAN / Ethernet / Bluetooth / USB | Krannich |
| 商务 | Hersteller、Produkt-/Leistungsgarantie、Preis (netto)、Ab Lager verfügbar、Nur Angebote | BayWa、Memodo |

### 2.2 储能筛选

| 维度 | 写法 | 来源 |
|---|---|---|
| 电压等级 | Hochvolt Batterie / 48 V Batterie（Memodo）；Hochvolt / Niedervolt / Gewerbespeicher（Densys）；Spannung: Niedervolt（Solartraders） | Memodo、Densys、Solartraders |
| 相数 / 场景 | Speicher-Typ：1-phasig / 3-phasig / **Speicher-Nachrüstung**（加装） | Memodo |
| 容量 | Nettokapazität / **Nutzbare Kapazität (kWh)** / Kapazität netto | Memodo、Krannich、Densys |
| 耦合方式 | Batteriekopplung；DC- vs. AC-Speicher（AC“beliebt bei Nachrüstungen”） | Memodo、Krannich |
| 备用电源 | Ersatzstromfähig：ja / ja mit Zubehör / nein | Krannich 套装 |
| 套装品牌组合 | Hersteller Kombination（“BYD + SMA”） | Krannich 套装 |
| 化学体系与寿命 | Zelltechnologie LFP；Garantie (Jahre / Zyklen) | Solartraders、Memodo |
| 规范 | VDE-AR-E 2510-50、IEC 62619、VDE 4105 | Densys、Solartraders |
| 接口 | CAN、RJ45 | Densys |

### 2.3 “兼容”的五种呈现方式

1. **套装 SKU**（最主流）：有独立货号、名称写成“电池 + 逆变器（inkl. 配件）”。见 Krannich WR-Speicher-Sets（446 件）、BayWa Speicher-Sets（SET-…）、IBC Speicherpakete、Densys Speicherpakete。
2. **放行清单 / 矩阵 PDF**：Memodo Freigabelisten（要双方厂商都放行，标出 DC 降额和备用电源条件，写明 48 V 系统需要的电池数量）、EWS Übersichtsblatt（可用容量、能否备用电源、能否扩展）、IBC Speicher-Matrix。
3. **厂商原始清单**：例如 BYD **Minimum Configuration List / Compatible Inverter List**，按单相、三相、离网列出每种逆变器的最少电池模块数和**最低固件版本**。— https://bydbatterybox.com/uploads/downloads/240116_BYD_Battery-Box_Premium_LVS_Minimum_Configuration_List_V1.11-65a73c0df09bc.pdf ，https://docs.eft-systems.de/download/203046c195&_lang=en （Google 摘要）
4. **商品页正文里的“需要搭配”**：例如 Memodo 写“需要 Sigen Gateway 才有备用电源”“电池塔附件都在 BC 里”，BayWa 写“inkl. SunnyHomeManager”。筛选里的“ja **mit Zubehör**”也是同一个意思：兼容，但要加配件。
5. **厂商计算器**：Enphase 模块兼容性计算器、Fronius Solar.creator“Automatic suggestion of compatible Fronius components”、Fronius Repowering Tool（为旧系统推荐替换逆变器）。— https://shop.krannich-solar.com/de-de/Services/Auslegungstools ，https://www.fronius.com/en/solar-energy/solar-solutions/apps-software/solar-creator ，https://www.fronius.com/de-de/germany/solarenergie/installateure-partner/infocenter/blog/how-to-find-the-perfect-inverter-061221

【推断】兼容在行业里是**三值**的：可以 / 加配件可以 / 不可以。它还带**条件**：功率降额、备用电源要满足最少电池数、最低固件版本。它的**权威来源是厂商放行**，不是批发商自己的判断。

---

## 3. 本行业的 AI 助手和厂商工具

### 3.1 批发商侧

| 主体 | 功能 | 证据 |
|---|---|---|
| **Solar Group（北欧电气批发，solar.eu）— Solar Assistant** | 嵌在 Solar Mobile App 里的生成式 AI 聊天，2024-12 发布，自称“industry's first”；目录约 70 万个货号，**封闭数据集**，不使用目录外数据或互联网；回答规格问题（颜色、性能、EPD…），可用文字或语音；**结果直接进入购物车**，可以用一句话改颜色或数量；支持 DA/NL/EN/SV/NO 五种语言；动机来自客户调研：“difficult to find products you do not use very often”；官方定位为“A perfect supplement to your personal sales rep” | https://www.linkedin.com/pulse/ai-assistant-makes-everyday-life-easier-solars-customers-solar-as-cwtif （2024-12-26）；https://www.linkedin.com/posts/solar-as_solars-ai-assistant-has-a-close-eye-on-a-activity-7376888434361131008-esmI |
| Sonepar DE — Digiplan | AI 识别符号和房间 → 自动物料清单 → 网店下单（电气规划，不是光储选型） | https://www.sonepar.de/c/services-loesungen/planung-organisation/sonepar-digiplan |
| PVSelected — Smart Request | 用聊天收集需求，**人工** 24 小时内回复报价（是否用 AI 未说明） | https://pvselected.com/ |
| Memodo / Krannich / BayWa / Segen / IBC / EWS / Wattkraft / Rexel DE | 【未找到】AI 选型聊天。检索词包括“KI Assistent Photovoltaik Großhandel”“AI assistant solar distributor”“Memodo KI”“Krannich KI/Chatbot”“BayWa Solar Trade KI”“PV Großhandel KI-Assistent Shop Produktsuche” | §0 方法 |

### 3.2 厂商侧（设计工具与“AI”）

- **SMA Sunny Design / Pro**：免费；规划并网和离网系统，给出**自动设计方案**（6.10 版改进了逆变器方案生成算法）；导入负荷曲线（可从 Sunny Portal 导入，CSV 7 天自动补全为全年）；储能和动态电价；生成报价、项目状态和团队协作；设备清单可导出 CSV。— https://www.sma.de/produkte/apps-software/sunny-design 。【未找到】AI 聊天。
- **Fronius Solar.creator**：免费在线配置器，自动推荐**兼容的 Fronius 组件**，可选预设负荷曲线，报告含经济性和组件总表；**Repowering Tool** 为旧系统推荐替换机。Fronius 的“KI”是 **Energiekosten-Assistent (ECA)**，即终端用户的电价和储能调度。— https://www.fronius.com/en/solar-energy/solar-solutions/apps-software/solar-creator ，https://www.fronius.com/de/solarenergie/solarloesungen/apps-software/solar-web/energiekosten-assistent
- **Huawei FusionSolar SmartDesign 2.0**：帮助安装商完成整套 PV 设计，自动生成分析报告，注册免费，也可做大型储能的设计和经济性。2026-03，Huawei 把 EMMA 改名为 **Smart Assistant**，这是住宅和小型商业的 AI 能源管理和网关，不是选型工具。— https://solar.huawei.com/at/smart-design/ ，https://www.pveurope.eu/planning/huawei-fusionsolar-rebrands-emma-smart-assistant （2026-03-18）
- **GoodWe Designer**：免费在线设计和仿真平台（可用 SEMS 账号登录），支持加装电池的设计。— https://emea.goodwe.com/goodwe-launches-free-goodwe-designer-and-sems-plus-app-software-solutions-for-solar-energy-planning-and-ma... （Google 摘要），https://www.vpsolar.com/en/goodwe-ezdesigner/ 。【未找到】AI 选型。
- **SAJ elekeeper**：“AI-powered … energy e-management assistant”，面向业主、安装商和运营方的监控与 AI 调度（运维 / EMS）。— https://www.saj-electric.com/elekeeper
- **SolarEdge Designer**：免费；“KI-gestützte 3D-Modellierung und Dacherfassung”，自动电气设计，并按规则校验“100 %ige Einhaltung der Auslegungsregeln”。2026-09 版改进了**储能推荐**：按实际日用电量优先推荐合适容量，而不是过大的容量；报告可在“仅电池 / 仅 PV / 全系统”之间切换。**Sera** 是面向业主的 AI 能源助手。— https://www.solaredge.com/de/produkte/software-tools/designer ，https://marketing.solaredge.com/rn_designer （2026-09）
- **Enphase Solargraf — Sol**：嵌在设计软件里的 AI 助手，**只回答 Solargraf 产品用法**，常驻侧栏，**一键转人工客服**，每条回答都可评分。— https://www.solargraf.com/blog/meet-sol-your-solargraf-ai-assistant （2026-05）
- **EcoFlow PowerOcean**：面向**业主**的“Konfigurieren Sie Ihr Heimenergiesystem”问答（地点、用电量等），推荐 PowerOcean 配置（单相 3–6 kW，5–15 kWh 等）；安装商一侧是用于调试和监控的 **EcoFlow Pro** App。— https://energy.ecoflow.com/de/design ，https://apps.apple.com/de/app/ecoflow-pro-for-installers/id6450247344
- **K2 Systems**（支架厂商）：官网有“K2 Kai, dein KI-Assistent”，回答产品和服务问题。— https://k2-systems.com/kontakt/privatkunden/installateur-finden/ （Google 摘要）

【推断】厂商的“AI”有两大类：EMS（调度电价和储能）和设计软件里的建模、帮助助手。真正与 de-linker 场景同构的只有两个例子：Solar Assistant 的“封闭目录 + 写入购物车”，以及 Solargraf Sol 的“范围受限 + 一键转人工”。

---

## 4. 对 de-linker 的提炼

### 4.1 输入：按安装商的思路问，用他们的词

【推断，依据 §2 的筛选维度和各配置器的输入】建议的提问和收窄顺序，最多只追问缺失的部分：

1. **项目类型**：新建 PV+储能 / **储能加装（Nachrüstung，AC 或 DC 耦合）** / 只要逆变器 / 商用（Gewerbe）。依据：Enphase 第一步问配置类型；Memodo 有“Speicher-Nachrüstung”；Krannich 区分 AC/DC 加装。
2. **Netzanschluss / Phasen**：1-phasig 或 3-phasig。所有逆变器筛选都有这一项；Enphase 第一步也问相数。
3. **功率**：AC-Nennleistung (kW)，或 PV 发电机规模 (kWp)，以及 MPPT 数和组串约束。de-linker 只做初筛，不替代组串设计。
4. **储能**：电压等级 HV / 48 V (NV)，**可用容量 (kWh)**，是否要扩展。
5. **Ersatzstrom/Notstrom**：要不要、要到什么程度（ja / ja mit Zubehör）。
6. **接口与控制**：EMS、Smart Meter、Rundsteuerempfänger、通讯方式。
7. 可选：年用电量。只在推荐容量时使用；BayWa 和 SolarEdge 都用“PV 功率 + 年用电量”给容量上限。

术语统一用 **Hybrid-WR、Speicher-Nachrüstung、nutzbare Kapazität、Ersatzstrom / Notstrom、Hochvolt / 48 V、Einspeisephasen、MPPT、Freigabe**。不要用消费类说法，例如“家庭电池多大合适”“省多少钱”。

### 4.2 兼容：照搬“放行”语义

- 【推断】兼容判断**只能来自事实源**。de-linker 现有的兼容合同（`contracts/`）应当表达行业的三值写法：**freigegeben / mit Zubehör / nicht freigegeben**。每条结论要能附上条件：DC 降额、备用电源所需的最少模块数、固件下限。依据：Memodo 的“双方厂商放行”原则，以及 BYD Minimum Configuration List 的结构。
- 【推断】回答兼容问题时，先给结论和条件，再给“需要的配件”。这对应 Memodo 商品页的 Gateway / BC，以及 BayWa 套装的“inkl. …”。

### 4.3 输出：物料清单 → 购物车 / Proforma / 项目询价

- 【事实汇总】行业工具的终点都是**带数量的物料清单**，再转入购物车（Solar-Planit、PV Manager、QuickCalc、pvXpert、Segen Quick-Angebot、Enphase System Builder 可导出），或者生成**报价 PDF**（PV Manager、QuickCalc、Sunny Design），或者走**项目询价**和人工对接（EWS 报价部门、Krannich Projektanfrage、Sonepar 的 Detailofferte、IBC 的大套装找销售、PVSelected 24 小时报价）。
- 【推断】de-linker 助手的输出应当是：
  - **推荐组合**：SKU 加数量，每一项都有目录事实依据；
  - 一键写入 **Warenkorb**，或生成 **Proforma**。这是在线支付以外的 B2B 路径，符合 2026-10-07 的“无在线支付”范围；
  - 超出单套范围时（商用、大容量、需要组串或静力计算），转到**项目询价**，把已收集的参数预填进去；
  - 始终留一个**找人的出口**，同 Segen 的专属团队、Solargraf Sol 的一键转人工。
- 【推断】采用 Solar Assistant 的两条做法：**只用封闭目录**；结果与购物车联动，可以用一句话改数量。

### 4.4 准入与价格展示

- 【事实汇总】同行普遍需要登录才看价格（Sonepar、Segen、BayWa、IBC），说明内容和兼容清单公开。【推断】助手对未登录访客可以回答选型和兼容问题，价格、Proforma、下单按站点现有规则处理。助手不应另立一套价格可见规则（Law 4）。

### 4.5 不适用的消费类做法

【推断，依据 §1–3 的对照】

- **以屋顶为起点的 3D 设计、静力和配重计算**：这是 Solar-Planit、PV Manager、pvXpert 的核心。它要求支架和组件全品类以及地点数据，de-linker 只有约 100 个商品、不卖组件（2026-10-02 决定），不应复刻。需要时可学 Memodo / Krannich 的“厂商设计工具汇总页”。注意 ADR-0023 / 所有者规则“不放第三方文件链接”：外链设计工具不是文件，但是否允许，需要先按该规则判断。
- **自给率和收益率营销计算器**（IBC Stromrechner、Solarmarkt Solarrechner、EcoFlow 问答）：这些都**面向业主**，结果是把业主引给安装商。de-linker 的买家是安装商，只在推荐储能容量时用年用电量做辅助。
- **个性化推荐、评价、降价提醒、优惠券、即时支付**：同行 B2B 店铺里看不到这些。同行的“价格”是登录后的个人采购条件、托盘价或项目价，例如 IBC 的“tagesaktuelle, persönliche Einkaufskonditionen”和 Krannich 的“Palettenpreise & Projektkonditionen”。
- **开放式闲聊、借题发挥**：Solar Assistant 刻意保持封闭数据；Sol 只回答本产品范围内的问题。

### 4.6 待所有者决定的事实问题（不阻塞实现）

- 是否像同行一样为常见组合建**套装 SKU**（Krannich、BayWa 的做法）？这涉及目录数据，属于 Law 6 的事实问题。
- 兼容合同里的每条“freigegeben”是否都有厂商放行文件可追溯？没有文件的条目应先列出来，交所有者逐条确认，不能自行认定。

---

## 附：主要来源一览（全部取于 2026-10-09）

Memodo：/m/werkzeuge/，/m/werkzeuge/pv-auslegungstools/，/m/werkzeuge/memodo-vergleiche-freigabelisten/，/m/werkzeuge/stromspeicher-freigabeliste/，/photovoltaik/heimspeicher/，PDP 14409 · Krannich：shop 首页，/WR-Speicher-Sets，/Wechselrichter/Hybridwechselrichter，/Heimspeicher，/Wechselrichter，/Services/Auslegungstools，/Services/Downloads，blog gewerbespeicher-notstrom，si-shk 2020 · BayWa：solar-distribution.baywa-re.de（首页、/wechselrichter/、/speicher-sets/、/speicherkomponenten/、Enphase 博客），solar-planit.com，photovoltaik.eu 2026-01-19，pveurope 2026-08-06，solarmarkt.ch · Segen：segensolar.de/portal/，segen.co.uk/portal/，segensolar.co.za · IBC：PV Manager 页，ibc-blog 2026/06，shop.ibc-solar.de（首页、Speicherpakete） · EWS：pv.de/leistungen/，QuickCalc（DK），solarserver 2024-12-20，Übersichtsblatt 新闻 · Wattkraft：首页，/unternehmen/service/ · Sonepar：sonepar.at 逆变器列表，Sonepar Suisse 帮助中心，sonepar.de Digiplan · Rexel：rexel.de/rexeleasy/pvxpert · Solartraders，sun.store，PVO International，PVSelected，Densys pv5 · Solar Group（LinkedIn 2024-12-26） · SMA、Fronius、Huawei、GoodWe、SAJ、SolarEdge、Solargraf、EcoFlow、K2（链接见正文）。
