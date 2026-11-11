# 奥地利（AT）国家规则包证据：#548 域 8 扩国第一国

2026-11-11。本文件只记录实现实际引用的原文、身份与边界。它不改变产品、证书或项目状态，也不构成任何并网放行。

## 1. 为什么是 AT

- 生产 23 个账号的国家分布：DE=11、US=3、SE=1、**AT=1**、NL=1。AT 有真实账号，德语区毗邻 DE，是规则包（现有 DE / NL / FR）之后证据最充分的扩国目标。
- 沿用 [#562](https://github.com/AssassinFlash/de-linker/issues/562) 的方法论：每国规则包必须有原始依据（原文 + 哈希 + 生效日期），分别表达功率语义、连接/安装/净注入门槛、日期/电压域/DSO 区分、新建 vs 改造、证书要求。

## 2. 采用的原文（三份，均为一手）

| # | 文件 | 官方入口 | 生效 | 取得时间 |
| --- | --- | --- | --- | --- |
| 1 | TOR Stromerzeugungsanlagen Typ A, **Version 1.4** | `https://ogd.ris.bka.gv.at/Dokumente/BgblAuth/BGBLA_2026_II_301/Anlagen_0001_1C9138FC_241E_4C87_9C70_B47AC7600383.pdf`（BGBl. II Nr. 301/2026, 2026-10-14 公布） | **2026-06-01** | 2026-11-11 |
| 2 | Elektrizitätswirtschaftsgesetz (**ElWG**), RIS 合并版 | `https://www.e-netze.at/downloads-data/pdf.aspx?pdf=ElWG_Fassung%20vom%2007012026.pdf`（RIS `Fassung vom 07.01.2026`） | 合并版基准日 **2026-01-07**；法源 BGBl. I Nr. 91/2025 | 2026-11-11 |
| 3 | E-Control：Anschluss von Kleinsterzeugungsanlagen (Mini-PV-Anlagen) | `https://www.e-control.at/mini-pv-anlagen` | 页面无生效日期声明 | 2026-11-11 |

> E-Control 官网另有同一 TOR Typ A v1.4 的镜像：`https://www.e-control.at/documents/1785851/1811582/TOR+Stromerzeugungsanlagen+Typ+A+Version+1.4+(7).pdf/093752f5-e220-0731-b8a8-bfa85ccb7287?t=1780897058735`。文档正文声明「Die sich auf der Website der E-Control befindliche Version gilt als authentische Fassung der TOR」，因此法定公告版（`ogd.ris.bka.gv.at`）与 E-Control 站内版互为同一版次的两处发布；本实现引用前者（公报版，作为生效依据）。

### 2.1 身份哈希

| 文件 | 字节数 | 页数 | PDF SHA-256 | 提取文本 SHA-256 |
| --- | --- | --- | --- | --- |
| TOR Typ A v1.4（公报版 PDF） | 2,559,500 | 63 | `3bfa1a11d770c0ee933498752d875fee0f01f2b4a876b06f29b25fb7fe0ae18e` | `5be42c6431cfbe670c70e3fb64827c7f97a72cab1b8a6741e9a3955432399820` |
| ElWG 合并版 PDF | 999,662 | 115 | `a5b2968808ca52d78d28dbc6aa2af7fa0530968f35b3ef41fcf58bba27275c07` | `c933a15dc7c3802fda69e2d04ab144d1a5143a056c7bfad0318ddfc5555ac641` |

**实现中 `text_sha256` 用的是「提取文本的哈希」，不是 PDF 字节哈希**，与 DE / NL / FR 的既有约定一致（见 §6）。PDF 字节哈希在此单独记录，用于重新取得同一份原件。逐字摘录见同目录：

- `tor-typa-v14-excerpts.txt`（TOR 关键条款，含行内 PDF 页码）
- `elwg-2026-excerpts.txt`（ElWG §6 Z 78、§77、§96）

## 3. 功率语义（有功 / 视在 / 峰值）

TOR §4.1 把三个量分开：

- **Maximalkapazität Pmax**：「Diese entspricht im Normalfall der Netto-Engpassleistung bzw. der Bemessungsleistung (Nennleistung)」。本规则包的分档键。
- **聚合**：「Mehrere verteilte Stromerzeugungseinheiten eines Netzbenutzers, die über einen gemeinsamen Netzanschlusspunkt an das Netz angeschlossen werden, gelten als eine Stromerzeugungsanlage.」含储能时按「Gesamtwirkung」取整体最大净 Engpassleistung。
- **netzwirksame Leistung**：合同约定的最大馈入/取用功率。脚注 8 原文：「Die netzwirksame Leistung ist für die Einordnung der Größenklasse irrelevant.」——**所以它不能顶替 Pmax，反之亦然**。

实现据此分成两个独立声明字段：`power_kw`（Pmax）与 `net_active_power_kw`（netzwirksame Leistung）。视在功率则是第三个量：§6.3.1 的解列保护门槛写的是 kVA，故另设 `apparent_power_kva`。

**未实现**：Pmax 的聚合需要项目侧提供同一接网点上的全部机组清单，本包只接收已聚合后的声明值，聚合本身由项目方按 §4.1 计算（界面文案已明示，不代算）。

## 4. 判定与出处

### 4.1 `at_tor_scope` — 适用范围

- 原文（§2.1）：「Dieser Teil der TOR gilt für den Anschluss und Parallelbetrieb von neuen oder wesentlich geänderten bestehenden Stromerzeugungsanlagen mit einer Maximalkapazität Pmax **kleiner als 250 kW** und einem Netzanschlusspunkt am Verteilernetz mit einer Nennspannung **unter 110 kV**.」
- 判定：`Pmax < 250 kW` 且接网电压 `< 110 kV` → `in_scope_below_250_kw_and_110_kv`；否则 `outside_scope`（`unresolved`，不提供条件性结论）。
- 两个上限都是**排他**边界（原文 "kleiner als"、"unter"），因此 250.0 kW 与 110.0 kV 均判为范围外。

### 4.2 `at_kleinsterzeugungsanlage` — ≤ 0,8 kW

- 原文（§2.1）：「Stromerzeugungsanlagen, deren Maximalkapazität Pmax **in Summe höchstens 0,8 kW** ist („Kleinsterzeugungsanlagen").」
- 法律定义（ElWG §6 Abs. 1 Z 78）：「„Kleinsterzeugungsanlagen" eine oder mehrere Stromerzeugungseinheiten, deren Maximalkapazität in Summe höchstens **0,8 kW pro Anlage an der Übergabestelle** eines Netzbenutzers beträgt」。
- 义务（§2.1）：Kleinsterzeugungsanlagen 豁除本 TOR 其余条款，但**仍须**满足 §5.1.3（LFSM-O）、OVE EN 61000-3-2、OVE EN 61000-3-3+A1+A2，并以固定 `cos φ = 1` 运行；且「spätestens **zwei Wochen** vor Inbetriebnahme der Netzbetreiber schriftlich zu verständigen」。
- 判定：`Pmax ≤ 0,8 kW` → `kleinsterzeugungsanlage_two_weeks_notice`；否则 `not_kleinsterzeugungsanlage`。
- **边界用十进制精确比较**：`0.8` 的二进制浮点值是 0.80000000000000004…，若用浮点或 `Fraction(float)` 会把正好 0,8 kW 的合法微型装置误判为「非微型」。实现改用 `Decimal(str(value))`，与声明值本身是十进制数的语义一致。

### 4.3 `at_network_disconnection_protection` — 30 kVA

- 原文（§6.3.1）：「Ein externer Netzentkupplungsschutz ist ab **> 30 kVA** der Engpassleistung der Stromerzeugungsanlagen, die an einem Netzanschlusspunkt eines Netzbenutzers im Niederspannungsnetz betrieben werden können, erforderlich. Bis zu einer gesamten Engpassleistung von maximal **30 kVA** je Netzanschlusspunkt … können auch selbsttätig wirkende Freischaltstellen gemäß **OVE-Richtlinie R 25** verwendet werden.」
- 脚注 30（与 §6.1.2 脚注 26 同文）：「Die Nennscheinleistungen von AC-gekoppelten elektrischen Energiespeichern, die **nicht in das Netz zurückspeisen**, werden für diese Bewertung nicht herangezogen.」
- 判定：`apparent_power_kva > 30` → `external_network_disconnection_protection`；`≤ 30` → `automatic_disconnection_device_r25`。
- 该门槛是**视在功率**，与 `power_kw` 不可互换；缺 `apparent_power_kva` 时返回 `missing_inputs` 并点名该字段。
- **注意**：脚注把不回馈电网的 AC 侧储能排除在「Engpassleistung」之外。本包只按声明值判定，**不自动**替用户扣减储能容量；界面与报告都要求项目方按该脚注计算后再填。

### 4.4 `at_substantial_change` — 新建 vs 改造

- 原文（§2.2）：「Eine Änderung … ist … dann wesentlich, wenn durch die Änderung die elektrischen Eigenschaften … vom im Netzanschlussvertrag vereinbarten Stand abweichen und diese Änderung den Netzbetrieb maßgeblich beeinflussen kann. Wesentliche Änderungen **können z.B. sein**: Erhöhung der Maximalkapazität Pmax einer Stromerzeugungseinheit um **mehr als 15 %** …」
- 判定：
  - 新建 → `new_installation`
  - 改造且 `Pmax > 1.15 × 改造前 Pmax` → `substantial_change_power_increase_above_15_percent`
  - 改造但未超 15% → `power_criterion_not_exceeded_other_criteria_open`（**unresolved**）
- 「未超 15%」**不**给否定结论：原文用「können z.B. sein」，15% 只是举例之一，其余情形（更换更高电气特性的逆变器、新增机组、变更电压等级）并列在同一列表里。把它写成「不构成实质变更」会超出原文。

### 4.5 `at_connection_route` — 连接/申报门槛

- 原文（ElWG §96 Abs. 1）：「Stromerzeugungsanlagen auf Basis erneuerbarer Energieträger … mit einer **netzwirksamen Leistung bis 20 kW** … sind auf entsprechende **Anzeige** an den Verteilernetzbetreiber hin an das Verteilernetz anzuschließen.」
- Abs. 2：运营商书面确认，或「nach Ablauf von **vier Wochen** ab vollständiger Anzeige … keine Entscheidung」即应接入。
- 判定：`net_active_power_kw ≤ 20` → `notification_route_up_to_20_kw_net_active_power`；`> 20` → `network_access_contract_required_above_20_kw`。
- 独立来源（`at_elwg_2025`），不与 TOR 共用生效日。

### 4.6 `at_conformity_evidence` — 证书/合格证明路径

- 原文（§8.1）：运行许可（Betriebserlaubnis）程序内提交「Prüfbericht des Netzentkupplungsschutzes … (ausgenommen Anlagen mit selbsttätig wirkender Freischaltstelle und entsprechendem Prüfbericht)」与「Bestätigung der vertragskonformen Errichtung」；应运营商要求另可要求：
  - 脚注 37：「Bei Wechselrichtern von PV-Anlagen, die in der **Wechselrichterliste von Oesterreichs Energie** als zulässig gelistet sind, gilt der Konformitätsnachweis als gegeben」。
  - 脚注 38：「Es werden auch Prüfberichte auf Basis **VDE-AR-N 4105** bzw. DIN VDE V 0124-100 anerkannt, sofern zusätzlich zu prüfende Eigenschaften gemäß **OVE-Richtlinie R 25**, insbesondere die **Q(U)- und P(U)-Regelung**, erfolgreich geprüft wurden und auch eine Dokumentation der oder eine Herstellerparametrieranleitung mit den Ländereinstellungen **„Österreich"** gemäß Anhang A3 bestätigt wurde。」
- 判定：三条路径各自给出 `declared_*`，**一律 `conditional`**。本包不读回清单/报告登记状态，因此不把「声明了路径」当作「已证实覆盖该设备与软件版本」。

## 5. 未验证、因而未实现的条款

以下均**未取得可引用原文**，实现里没有对应判定，也不做默认推断：

1. **DSO 具体补充要求。** TOR 多处把门槛、整定值、`cos φ` 程序、P(U)/Q(U) 参数交给「der relevante Netzbetreiber」在 Netzanschlussvertrag 中确定。奥地利有多个 Verteilernetzbetreiber，各自 Allgemeine Bedingungen/TAB 正文未取得，因此没有任何 DSO 级数值。
2. **Anhang A3 的「Ländereinstellungen Österreich」具体整定值。** 该附录在已取 PDF 内（第 58–60 页），但本次未逐条转录为实现中的固定值——保护整定值属于 DSO 合同中可被改写的内容，做成常量会与 §6.3.3「Der Netzbetreiber legt … die Einstellwerte fest」冲突。
3. **`§14a` 类储能并网专项。** TOR §2.4 只说储能「grundsätzlich wie Stromerzeugungsanlagen oder Verbraucheranlagen zu werten」并指向 TOR Verteilernetzanschluss；**该文件本轮未取得**，故储能的专项条款未实现。
4. **TOR Typ B/C/D 的门槛值。** 只取得 Typ A v1.4。第三方页面流传「Typ B ab 250 kW / C ab 35 MW / D ab 50 MW」，**未核原文，不采用**。
5. **`Pmax` 聚合的项目级计算。** 见 §3 末。
6. **过渡条款。** §2.1 说本 TOR 适用于「nach dem Inkrafttreten … abgeschlossenen」Netzanschlussverträge，并对已收到 Anschlusskonzept / Angebot 的申请除外。本包只按 `rule_date` 落在 `[2026-06-01, 2026-11-11]` 内给条件性结论，**不判断**某项目属于新旧哪一侧——那需要合同日期与运营商受理记录。
7. **E-Control Mini-PV 页面无生效日期。** 该页仅用于交叉印证 0,8 kW 与两周申报（与 §2.1、ElWG §6 Z 78 一致），未作为独立规则来源写入 `_SOURCES`。

## 6. 与既有三国包的约定一致性

- `text_sha256` 记录的是**采集器提取文本**的 SHA-256，而非官方签名或 PDF 字节哈希——与 `COUNTRY-EVIDENCE.md` §12 对 DE/FR/NL 的说明同一约定。PDF 字节哈希见 §2.1。
- 评价窗口 = `[effective_from, evidence_snapshot_date]`；窗口外一律 `outside_version`，不继承。AT 的 `evidence_snapshot_date = 2026-11-11`。
- AT 的六条检查共享**一个**评价窗口：一次读取是一个按日期包装的整体，不产生「部分已评估、部分过期」的混合结果。ElWG 与 §8.1 各自作为独立来源出现在报告里（各自带生效日），但窗口仍以 TOR 的 `[2026-06-01, 2026-11-11]` 为准。

## 7. 取证通道与故障

- 检索与抓取全部经 **Apify**：`apify/google-search-scraper`（AT 本地化检索）、`apify/website-content-crawler`（E-Control 页面）、`automation-lab/pdf-text-extractor`（公报 PDF 与 ElWG 合并版 PDF 文本）。
- 取得的 TOR PDF 直接来自 `ogd.ris.bka.gv.at`（`curl`，HTTP 200，2,559,500 B）。
- **`www.ris.bka.gv.at` 的 `NormDokument.wxe` 逐条页面返回 "Security Check" 人机验证**，未尝试绕过；改由 E-Control 引用的 RIS 合并版 PDF（`e-netze.at` 转发的 `ElWG_Fassung vom 07012026.pdf`）取得同一法律的完整正文。
- **`apify/website-content-crawler` 不能以 PDF 直链作为 startUrl**（`saveContentTypes` 只作用于页面内链接文件；直链会触发 `Download is starting` 或 Content-Type 拒绝），故 PDF 改由 `automation-lab/pdf-text-extractor` 处理。
- **E-Control 站内 PDF 链表页在 Playwright 渲染下超时**；改为在已取得的 HTML 页文本中定位 PDF 链接后，经检索结果与公报入口取得原件。
- 一次 run 的 E-Control 页面在 cheerio 下返回 503 Security Check，换种抓取方式后成功；未变更账户设置、未使用普通网络搜索替代。

## 8. 本轮不改变的事

- 没有为任何型号或项目建立并网资格结论；`numeric_rules` 只在这一批 AT 检查算出条件性结论时标为 `partially_assessed`。
- 没有写 Woo、没有改产品资料、没有对外联系。
- 生产账号中的 AT 客户（1 个）不因此获得任何自动放行。
