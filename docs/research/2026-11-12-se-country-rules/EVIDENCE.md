# 瑞典（SE）国家规则包证据：#548 域 8 扩国第二国

本文件只记录实现实际引用的原文、身份与边界。它不改变产品、证书或项目状态，也不构成任何并网放行。

> 目录按任务指定的 `2026-11-12` 命名；原文的读取、字节校验与哈希计算全部在 **2026-11-11**（UTC 09:55–10:35）完成。实现中的 `evidence_snapshot_date` 用实际核对日 `2026-11-11`，不用目录名。

## 1. 为什么是 SE

生产 23 个账号的国家分布：DE=11、US=3、**SE=1**、AT=1（已入包）、NL=1（已覆盖）。AT 入包后，SE 是最后一个有真实账号背书的扩国目标；此后扩国按新证据重新排序。

## 2. 先纠正两条会写错的前提

### 2.1 瑞典的国家技术规则是 **EIFS 2018:2**，不是 SvKFS

欧盟 RfG（Commission Regulation (EU) 2016/631）第 7.1 与 5.3 条要求成员国就「一般适用的要求」与「Type B/C/D 门槛」作出国家规定。瑞典指定的是 **Energimarknadsinspektionen（Ei）** 的 föreskrifter，编号 **EIFS 2018:2**。Svenska kraftnät 自己的页面写明：

> «Regelverket ger medlemsstaterna möjlighet att komplettera kraven med nationella föreskrifter. I Sverige har Energimarknadsinspektionen tagit fram föreskriften EIFS 2018:2, vilket innebär att den tekniska kravbilden finns på plats.»
> —— `https://www.svk.se/om-kraftsystemet/legalt-ramverk/eu-lagstiftning-/natanslutning-av-generatorer-rfg/`（页面标注 Granskad 16 maj 2025）

Svenska kraftnäts egen författningssamling（**SvKFS**）在同一站点的「Svenska kraftnäts föreskrifter」页只列 4 份文件（页面过滤结果原文：「Filtreringen resulterar i **4 dokument**」），覆盖对象是系统安全、计量、消费侧断开等，**不是**发电机并网的类型门槛与技术能力。本包因此以 EIFS 2018:2 为瑞典国家层主源，SvKFS 不作为规则来源。

### 2.2 「43,5 kW 以下免接入义务」是误读

业界（安装商页面、指南）普遍把 43,5 kW 讲成「小于该值不强制接入」。ellagen (1997:857) 4 kap. 2 § 的原文是**相反方向的约束**：它限制的是**电网公司**偏离接入义务时的程序。

> «Trots första stycket får ett distributionsnätsföretag, i fråga om en anläggning för produktion av förnybar el vars inmatning kan ske med en effekt om högst 43,5 kilowatt, göra avsteg från anslutningsskyldigheten **endast om** 1. företaget underrättar den som begär anslutning om detta, och 2. underrättelsen lämnas **inom en månad** från det att företaget har tagit emot begäran.»

即：≤43,5 kW 的可再生能源装置，电网公司**仍可**依 4 kap. 2 § 第一段（容量不足/其他特别理由）偏离，但**必须**在一个月内通知申请人。主规则仍是 4 kap. 1 §：「Den som har en nätkoncession **ska** på objektiva, icke-diskriminerande och i övrigt skäliga villkor ansluta en elektrisk anläggning …」。实现按原文含义表达，不写成「43,5 kW 以下无需接入」。

## 3. 采用的原文（三份，均为一手）

| # | 文件 | 官方入口 | 生效 | 读取 |
| --- | --- | --- | --- | --- |
| 1 | **EIFS 2018:2** — Energimarknadsinspektionens föreskrifter om fastställande av generellt tillämpliga krav för nätanslutning av generatorer | `https://ei.se/download/18.5b0e2a2a176843ef8f5b74/1608639227153/EIFS-2018-2-om-fastst%C3%A4llande-av-generellt-till%C3%A4mpliga-krav-f%C3%B6r-n%C3%A4tanslutning-av-generatorer.pdf` | 决定 2018-11-08，公布 2018-12-05，**生效 2019-04-27**（原文末句：「Dessa föreskrifter träder i kraft den 27 april 2019.」） | 2026-11-11 |
| 2 | **RfG** — Commission Regulation (EU) 2016/631（Art. 5.2 + Table 1、Art. 13、13.2、13.7、14.1、15.1、Art. 4.1(a)） | `https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0631&from=EN`（OJ L 112, 27.4.2016, pp. 1–68；EUR-Lex 状态 “In force”） | 2016-05-17 生效；2019-04-27 起适用（Ei 页面：「Förordningen tillämpas först från och med 3 år efter offentliggörande (april 2019)」） | 2026-11-11 |
| 3 | **Ellagen (1997:857) 4 kap.**（4 kap. 1、2、5、6、8 a、9 §） | `https://rkrattsbaser.gov.se/sfst?bet=1997:857`（官方合并本，页头「Ändring införd: t.o.m. SFS 2026:1298」） | 4 kap. 1–2 与 5 § 的现行文字来自 **Lag (2022:596)**：「Denna lag träder i kraft den **1 juli 2022**」 | 2026-11-11 |

### 3.1 身份哈希

| 文件 | 字节数 | 页数 | PDF SHA-256 | 提取文本 SHA-256 |
| --- | --- | --- | --- | --- |
| EIFS 2018:2（Ei 官方 PDF） | 180,749 | 11 | `89a1011a371f0f9ee8951f476e51621f07119869628afd6eb611082ff25b8eec` | `d87936b2aa55393ea10945560ce244e624adc0e9e2ae2b7940b2a9175f009780` |
| SFS 2022:596（ellagen 修订法 PDF） | 1,282,110 | 20 | `e827148e2748f5d75bd0f426fc92776418dfbdbaa1e3ece7ab4d2c295de6cdca` | `09861a39d4eea681621d961cbe0d1cf11fa0f00ee7c40848e3f6bbee6a384e3e` |

**实现中 `text_sha256` 用「提取文本的哈希」，不是 PDF 字节哈希**，与 DE / NL / FR / AT 的既有约定一致（见 §7）。本包三个来源的取值：

| 来源 | `text_sha256` 的对象 | 值 |
| --- | --- | --- |
| `se_eifs_2018_2` | `automation-lab/pdf-text-extractor` 的 `fullText`（EIFS PDF，20,763 字符） | `d87936b2aa55393ea10945560ce244e624adc0e9e2ae2b7940b2a9175f009780` |
| `se_rfg_2016_631` | `apify/website-content-crawler` 的 `text`（EUR-Lex HTML，210,737 字符） | `e88982d1cf6d0d4ef8870a88cff02b5bf3387b5a23196121543d156ec374f572` |
| `se_ellagen_1997_857` | 同一采集器的 `text`（rkrattsbaser 官方合并本，162,121 字符） | `e06739af5c38995d827d263f77fd17e963f6cf8a49f15f409445ef14dbaa6150` |

逐字摘录见同目录：`eifs-2018-2-excerpts.txt`、`rfg-2016-631-excerpts.txt`、`ellagen-1997-857-excerpts.txt`。原件不入库（与 AT 目录同一约定）：按上表的官方 URL 与 PDF SHA-256 可重新取得并校验同一份文件。

## 4. 功率语义与分档键

RfG Art. 5.1：Type 由「接网点电压电平」+「最大容量（maximum capacity）」共同决定。Art. 5.2(a) 写 `0,8 kW or more`（含 0,8 kW）；(b)(c)(d) 写 `at or above a threshold`（含门槛值）。因此：

- **分档键** = 申报的 **Pmax（最大连续容量）** + **接网点电压**。
- **聚合**：RfG 的 `power-generating module` 是设备单元级概念；多个 module 在同一接网点构成 `power-generating facility`。本包只接收**已按项目口径聚合后的 Pmax**，聚合本身由项目方计算（界面文案明示，不代算）。这与 AT 线「不代算聚合」的处理一致。
- **43,5 kW 是另一条量**：ellagen 4 kap. 2 § 讲的是「inmatning kan ske med en effekt om högst 43,5 kilowatt」，即**可馈入功率**，不是 Pmax，也不是设备的视在功率。故单设声明字段 `se_export_power_kw`，不与 `power_kw` 互换。

## 5. 判定与出处

### 5.1 `se_module_type` — RfG 类型分档

- 国家桥接原文（EIFS 2018:2 **3 kap. 17 §**）：「De maximala tröskelvärdena för kraftproduktionsmodul av typ B, C och D som anges i **artikel 5.2 tabell 1 för synkronområde Norden** i kommissionens förordning (EU) nr 2016/631 ska gälla för Sverige.」
- 表值原文（RfG **Table 1**，Nordic 行）：`1,5 MW`（B 门槛上限）/ `10 MW`（C 门槛上限）/ `30 MW`（D 门槛上限）。
- Type A 下界（RfG Art. 5.2(a)）：`connection point below 110 kV and maximum capacity of 0,8 kW or more (type A)`。
- Type D 另一入口（Art. 5.2(d)）：`connection point at 110 kV or above (type D)`。

判定：

| 条件（按序） | 结果 |
| --- | --- |
| 接网点电压 ≥ 110 kV | `type_d` |
| Pmax ≥ 30 MW | `type_d` |
| Pmax ≥ 10 MW | `type_c` |
| Pmax ≥ 1,5 MW | `type_b` |
| Pmax ≥ 0,8 kW | `type_a` |
| Pmax < 0,8 kW | `below_range`（unresolved：不属 RfG 的 significant 类别） |

**注意口径**：Art. 5.2(b)(c)(d) 说的是「不得超过 Table 1 的上限」，即 Table 1 给的是**门槛上限**；EIFS 17 § 让这些上限值「适用于瑞典」，因此瑞典的门槛取到上限值本身。此读法已在实现注释与本节同时写明，避免把「上限」当成「瑞典自定的更低门槛」。
**边界用十进制精确比较**：`1.5` 与 `0.8` 的二进制浮点表示不是精确值，实现用 `Decimal(str(v))`，与声明值本身是十进制数的语义一致（AT 线同类陷阱）。

### 5.2 `se_frequency_range` — 频率范围（Type A–D）

- 原文（EIFS 2018:2 **3 kap. 1 §**）：「Den kortaste tidsperiod som en kraftproduktionsmodul av typ A, B, C och D ska kunna fungera inom frekvenser som avviker från nominellt värde utan att kopplas bort från nätet är: 30 minuter inom frekvensområde 47,5–48,5 Hz · 30 minuter inom frekvensområde 48,5–49,0 Hz · obegränsad inom frekvensområde 49,0–51,0 Hz · 30 minuter inom frekvensområde 51,0–51,5 Hz」
- 判定：落在 `type_a`…`type_d` 时给 `four_band_frequency_range_47_5_to_51_5_hz`；`below_range` 时为 `below_range`。
- 兼核 RfG Table 2 的 Nordic 行与该条文一致（47,5–48,5 Hz = 30 min；49,0–51,0 Hz = Unlimited；51,0–51,5 Hz = 30 min），48,5–49,0 Hz 在 RfG 是「不少于 30 分钟」，EIFS 直接写 30 分钟——**取 EIFS 的瑞典值**。

### 5.3 `se_lfsm_o` — 过频有功响应（Type A–D）

- 原文（EIFS **3 kap. 3 §**）：「Kraftproduktionsmodul av typ A, B, C och D ska tillhandahålla reduktion av aktiv effekt som frekvenssvar vid begränsat frekvenskänslighetsläge – överfrekvens (LFSM-O), vid en frekvenströskel på **50,5 Hz**. Automatisk bortkoppling av kraftproduktionsmodulen får inte användas som alternativ till en reduktion av aktiv effekt vid överfrekvens.」
- 斜率（**3 kap. 4 §**）：「Statikfaktorn för kraftproduktionsmoduler av typ A, B, C och D ska ha det primära inställningsvärdet **8 procent**.」
- 判定：`lfsm_o_50_5_hz_droop_8_percent`。
- RfG Art. 13.2(c)(d) 给的是**允许区间**（阈值 50,2–50,5 Hz、droop 2–12 %）；EIFS 把瑞典值定在区间上端 50,5 Hz / 8 %。实现只用 EIFS 的瑞典值。

### 5.4 `se_voltage_range` — 90–105 % 电压区间（仅 Type B/C/D）

- 原文（EIFS **3 kap. 18 §**）：「Kraftproduktionsmodul av typ B, C och D ska kunna upprätthålla utmatning av aktiv effekt inom spänningsintervallet **90–105 procent** spänning i anslutningspunkten.」
- 判定：`type_b`/`type_c`/`type_d` → `voltage_range_90_to_105_percent`；`type_a` → `not_applicable_type_a`（unresolved）。Type A 没有对应条文——RfG Art. 13 全篇不含该电压区间要求，EIFS 也未对 Type A 补设，**不替 Type A 外推**。

### 5.5 `se_automatic_reconnection` — 自动并网条件（仅 Type A/B/C）

- 原文（EIFS **3 kap. 8 §**）：「Kraftproduktionsmoduler av typ A, B och C får anslutas automatiskt till nätet när nätfrekvensen i anslutningspunkten är inom intervallet **47,5–50,1 Hz**. Nätfrekvensen … ska ha befunnit sig inom detta frekvensintervall under minst **tre sammanhängande minuter** innan anslutning får ske.」
- 功率上升（**3 kap. 9 §**）：「< 49,9 Hz — Ingen begränsning … · 49,9–50,1 Hz — Ökning med maximalt **10 procent** av nominell aktiv uteffekt per minut · > 50,1 Hz — Ökning av uteffekten ej tillåten」
- 判定：`type_a`/`type_b`/`type_c` → `automatic_reconnection_47_5_to_50_1_hz_after_3_minutes`；`type_d` → `not_applicable_type_d`（unresolved）。条文只列 A/B/C，**不向 Type D 外推**。

### 5.6 `se_existing_change` — 既有装置的改造（RfG Art. 4.1(a)）

- 原文（RfG **Art. 4.1(a)**）：「a **type C or type D** power-generating module has been modified to such an extent that its connection agreement must be substantially revised in accordance with the following procedure: (i) … shall notify their plans to the relevant system operator in advance; (ii) if the relevant system operator considers that the extent … is such that a new connection agreement is required, the system operator shall notify the relevant regulatory authority …; (iii) the relevant regulatory authority … shall decide if the existing connection agreement needs to be revised or a new connection agreement is required and which requirements of this Regulation shall apply」
- 判定：
  - 新装置 → `new_installation`
  - 改造且类型为 C/D → `modification_notification_type_c_or_d`
  - 改造且类型为 A/B → `modification_outside_4_1_a_other_rules_open`（unresolved：Art. 4.1(a) 不覆盖 A/B，其余规则未在本包核到）
- 该条是**程序**义务，不判断改造是否「重大」；判断权在系统运营方与监管机构，本包不替代。

### 5.7 `se_connection_duty` — 接入义务与 43,5 kW 通知规则

- 主规则（ellagen **4 kap. 1 §**）：「Den som har en nätkoncession ska på objektiva, icke-diskriminerande och i övrigt skäliga villkor ansluta en elektrisk anläggning till ledningen eller ledningsnätet, om innehavaren av den elektriska anläggningen begär att den ska anslutas.」
- 例外与 43,5 kW（ellagen **4 kap. 2 §**）：见 §2.2 原文。
- 判定：
  - `se_export_power_kw ≤ 43,5` → `deviation_notice_within_one_month`
  - `> 43,5` → `deviation_on_general_grounds_no_notice_duty`
  - 缺该字段 → `missing_inputs` 并点名 `se_export_power_kw`
- 两者都**不是**「无需申请接入」：接入义务来自 4 kap. 1 §，2 § 只是偏离条件。报告文案明确写「接入义务仍然存在」。

## 6. 未验证、因而未实现的条款

以下均**未取得可引用原文**，实现里没有对应判定，也不做默认推断：

1. **具体 DSO 的补充要求。** 瑞典有多个 elnätsföretag（Vattenfall Eldistribution、Ellevio、E.ON 等），各自的 anslutningsvillkor / teknisk anvisning 正文本轮未取得，因此没有任何 DSO 级数值。
2. **Elsäkerhetsverket 的装置规则（ELSÄK-FS）逐条要求。** 其「Installera solceller – vad gäller?」页只说明安装工作属电安装作业、须按 ELSÄK-FS 2017:2 / 2022:1 / 2017:3 与 SS 436 40 00 执行、逆变器须符合 SS-EN 62109-2；**具体条款号与整定值未逐条读取**，故未做成判定。
3. **EIFS 2018:2 正在被更新。** Ei 于 2026-02-23 发布 remiss（`På remiss: Föreskrifter om krav för nätanslutning av generatorer`），原文写明「Ei föreslår att nu gällande föreskrifter EIFS 2018:2 **upphävs och ersätts** av nya föreskrifter」。截至本次读取，Ei 的「Föreskrifter - el」列表仍以 **EIFS 2018:2** 为现行版本，未见新的 nätanslutning-av-generatorer 条目。**新规一旦决定并生效，本包的类型门槛与整定值须整体重读**；本包只覆盖 `[2019-04-27, 2026-11-11]` 窗口。
4. **Type B/C/D 的完整技术条款。** 本包只落实与「项目分档 + 频率/电压/LFSM-O/重合闸」直接相关的条款；EIFS 3 kap. 10–16（故障穿越曲线）、19–32（Type C/D 的有功设定、FSM、爬坡）、4–6 kap.（同步机、kraftparksmodul、海上模块）**未做成判定**，因为它们是设备型式试验层面的能力清单，不是本项目声明能判定的量。
5. **`Pmax` 聚合的项目级计算。** 见 §4 末。
6. **过渡条款。** RfG Art. 4.2 定义「既有装置」的两条判据（并网日 / 最终绑定采购合同 + 30 个月通知）需要合同日期与运营商记录，本包只按 `rule_date` 落在窗口内给条件性结论，**不判断**某项目属于新旧哪一侧。
7. **`kraftproduktionsmodul` 与 `kraftproduktionsanläggning` 的边界在项目层面的落法。** RfG Art. 2(5)(6) 有定义，但一个多机项目如何切分 module 取决于接网点与电气布局，本包不切分。

## 7. 与既有四国包的约定一致性

- `text_sha256` 记录的是**采集器提取文本**的 SHA-256，而非官方签名或 PDF 字节哈希——与 `COUNTRY-EVIDENCE.md` §12、§13 对 DE/FR/NL/AT 的说明同一约定。PDF 字节哈希见 §3.1。
- 评价窗口 = `[effective_from, evidence_snapshot_date]`；窗口外一律 `outside_version`，不继承。SE 的 `evidence_snapshot_date = 2026-11-11`，`effective_from = 2019-04-27`。
- SE 的七条检查分**两个**评价窗口，因为两条法源确实不同时生效：
  - 分档与网络码要求（`se_module_type`、`se_frequency_range`、`se_lfsm_o`、`se_voltage_range`、`se_automatic_reconnection`、`se_existing_change`）用 **`[2019-04-27, 2026-11-11]`**（EIFS 生效日到核对日）。
  - `se_connection_duty` 用 **`[2022-07-01, 2026-11-11]`**（Lag (2022:596) 的生效日到核对日）：43,5 kW 通知规则随该法进入 4 kap. 2 §，2019-04-27 到 2022-06-30 之间的日期有网络码但还没有这段条文，因此该条给 `outside_version` 而不是借用 EIFS 的窗口。
  - 这与 AT 的「一次读取一个按日期包装的整体」不同，是刻意的：AT 的两份来源覆盖同一段义务，SE 的 43,5 kW 规则是一项**后加的**条款，把它提前到 2022 年之前会给错答案。

## 8. 取证通道与故障

- 检索与抓取全部经 **Apify**：`apify/google-search-scraper`（瑞典本地化检索，7 次）、`apify/website-content-crawler`（官方页面，12 次）、`automation-lab/pdf-text-extractor`（EIFS PDF 正文）。
- **`eur-lex.europa.eu` 的 PDF 直链在本机 curl 与 Apify 两端都拿不到字节**：`?uri=CELEX:32016R0631` 的 PDF 路由返回 HTTP 202 + 空 body（有 `Accept`/UA 变体亦同），`automation-lab/pdf-text-extractor` 报 `PDFDocument: stream must have data`。改由 EUR-Lex 的 **HTML** 路由（`legal-content/EN/TXT/HTML/?uri=CELEX:32016R0631&from=EN`）取到 210,737 字符正文，Table 1 与 Art. 5.2/13/14/15/4.1(a) 均在其中逐字核对。这是**取文方式**的变化，不是来源降级。
- **`ei.se` 的 PDF 直链在 LibreSSL 下首次 `SSL_ERROR_SYSCALL`**；改 `--http1.1` + 桌面 UA 后 HTTP 200、180,749 字节取得同一 URL。已用 PDF 字节哈希复核。
- **`lagen.nu` 的 EIFS 2018:2 页面**（`https://lagen.nu/eifs/2018:2`）作为交叉核对：条文文字与官方 PDF 一致，且给出 `Beslutad 2018-11-08 / Ikraftträdande 2019-04-27 / Källa ei.se`。实现以官方 PDF 为准（`_SOURCES` 指向 `ei.se` 的 PDF URL）。
- **`svk.se` 的 föreskrifter 列表页**在 Playwright 下只渲染出「Filtreringen resulterar i 4 dokument」，文档标题由 JS 延迟加载；该页仅用于证明 SvKFS 不含本包主题，未作为规则来源。
- **`svenskforfattningssamling.se/doc/2022596.html`** 只返回导航壳（114 字符），改由同一站的 PDF 直链取得 20 页原件。
- **`lagen.nu/2022:596`、`lagen.nu/2025:1330` 返回 404**（该站不收录这两份修订法的独立页），因此修订法身份改用 `svenskforfattningssamling.se` PDF + `rkrattsbaser` 合并本的条末「Lag (2022:596).」标记互证。

| 采用内容 | Actor / run | Dataset |
| --- | --- | --- |
| 瑞典本地化检索（法规名、门槛、Ei 状态） | `apify/google-search-scraper` · 7 次 | 见 §9 索引 |
| svk.se RfG 页、Ei RfG 页、lagen.nu EIFS 页、svk föreskrifter 页 | `apify/website-content-crawler` · `clBSUgwhEmNW7oxCz` | `2kXcX1Z5S6bGdTDHF` |
| Ei 页面（RfG Art. 7.1/5.3、foreskrifter-el 列表、2026-02-23 remiss） | `apify/website-content-crawler` · `FoRkonzxtF85dZqfB` | `hqusYhLccfxWEreGE` |
| EUR-Lex RfG HTML 全文（Table 1、Art. 5.2/13/14/15/4.1） | `apify/website-content-crawler` · `oTXcvwFRVNaQBklLj` | `DA94sSU00IOtpuiaW` |
| rkrattsbaser 官方 ellagen 合并本（4 kap. 全文） | `apify/website-content-crawler` · `Zk1L8rnOWz6dHD1Jh` | `duWP6z6gUuMdaVG6l` |
| EIFS 2018:2 PDF 正文 + 逐页文本 | `automation-lab/pdf-text-extractor` · `UrabSCWsi4AwEGwL2` | `QZAEGUVRJ1Zj0goXO` |

## 9. 本轮不改变的事

- 没有为任何型号或项目建立并网资格结论；`numeric_rules` 只在这一批 SE 检查算出条件性结论时标为 `partially_assessed`。
- 没有写 Woo、没有改产品资料、没有对外联系。
- 生产账号中的 SE 客户（1 个）不因此获得任何自动放行。
- 未声称任何设备满足 EIFS 的整定值；本包只把「规则要求什么」按日期与项目声明读出来。
