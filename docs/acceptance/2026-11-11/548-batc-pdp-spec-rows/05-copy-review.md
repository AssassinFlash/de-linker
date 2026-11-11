# BAT-C PDP 规格行文案对抗评审

日期：2026-11-11。范围：生产产品 1954（GW61.4）/1955（GW112.6）产品页 Technical data 表新增的三类行
——认证（两条）、额定充放电电流、额定充放电功率。英德同批。

事实来源（逐字核过原件）：

| 事实 | 原件 | 页 |
| --- | --- | --- |
| 额定充/放电电流 100 / 100 A | `GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf`（sha256 `c29cbf25…7fcb7`） | 物理 p81（印刷 80） |
| 额定充/放电功率 30.7 kW / 56.3 kW | 同上 | 物理 p81 |
| 额定值仅澳洲（Note 2） | 同上 | 物理 p83（印刷 82） |
| 认证块两行：Safety Regulation + EMC | 同上 | 物理 p82（印刷 81） |
| 认证清单不全（Note 5） | 同上 | 物理 p83 |
| 德语对照 | `GW_BAT-C-60-112kWh_Datasheet_EMEA-DE_V1.1.pdf`（媒体 6393，厂商德语原件） | p2 |

术语基准：`linker-copywriting` Hard Stops（spec 表属 Deep 面，技术词可用）；站点既有 spec 表德语术语
（`Max. Lade- / Entladestrom` 24 处、`Zertifizierung` 10 处、`EMV` 见 6321/2003、`Sicherheit` 见 6321）。

## 1. 初稿

**EN**

| label | value | note |
| --- | --- | --- |
| Safety regulation | IEC62619 / … / UN38.3 | GoodWe states that not all certifications and standards are listed and refers to its website for the full set. |
| EMC | IEC/EN 61000-6-1/2/3/4 | — |
| Rated charge / discharge current | 100 / 100 A | GoodWe rates these values for Australia only; actual charge/discharge current and power derate with cell temperature and state of charge. The maximum ratings are stated separately. |
| Rated charge / discharge power | 30.7 kW | 同上 |

**DE**

| label | value | note |
| --- | --- | --- |
| Sicherheitsbestimmung | IEC62619 / … / UN38.3 | GoodWe weist darauf hin, dass nicht alle Zertifizierungen und Normen aufgeführt sind und verweist für die vollständige Liste auf die eigene Website. |
| EMV | IEC/EN 61000-6-1/2/3/4 | — |
| Nenn-Lade- / Entladestrom | 100 / 100 A | GoodWe weist diese Werte nur für Australien aus; tatsächlicher Lade-/Entladestrom und tatsächliche Leistung werden abhängig von Zelltemperatur und Ladezustand reduziert. Die Maximalwerte sind getrennt angegeben. |
| Nenn-Lade- / Entladeleistung | 30,7 kW / 56,3 kW | 同上 |

## 2. 评审意见（逐条，按站点规则攻击初稿）

**意见 1 — `Safety regulation` 不是站内的词，也不是买家的词。**
`Regulation` 在英语里指法规（欧盟条例），而这里列的是 IEC 标准。"Safety regulation" 会让德国安装商
联想到 EU 2014/35 这类法规，与 IEC62619 混在一行。站点既有先例（产品 6321）用的就是 `Safety` / `Sicherheit`。
**改：** EN `Safety`，DE `Sicherheit`。德文侧同时弃用厂商的 `Sicherheitsbestimmung`——`Bestimmung` 在
德语标准语境里生硬，站点无一处使用。

**意见 2 — 初稿的 note 把解释写给了内部读者。**
"refers to its website for the full set" 是复述手册 Note 5 的元叙述，客户需要知道的是「这张清单不全」，
不是知道厂商在哪里写的那句话。
**改：** `GoodWe states that not all certifications and standards are listed; the full set is on its website.`
（德：`GoodWe weist darauf hin, dass nicht alle Zertifizierungen und Normen aufgeführt sind; die vollständige Liste steht auf der GoodWe-Website.`）

**意见 3 — 澳规 note 里 "current and power" 与所在行重复。**
电流行讲电流、功率行讲功率，同一句长 note 复制两遍读起来像粘贴错误；而手册 Note 2 同时约束两者，
所以两行语义必须都覆盖到。
**处置：** 保留两行同文。理由：Note 2 是一句同时限定两者的原文，拆开改写成两版会各自丢一半（只看电流行
的人会以为功率不受限）。同文在这里是事实结构，不是复制错误。
**改（措辞收紧）：** 去掉 "GoodWe rates these values" 里的 "these values" 冗余 → 保持原样，因为
qualifier 必须同时指向电流与功率两个数，去掉指代后 "GoodWe rates for Australia only" 语法不通。
保留。

**意见 4 — 澳规 note 未说明「最大值在哪」。**
初稿写 "The maximum ratings are stated separately."。客户在表格里看得见上一行的 Max 行，但 note 不点名
就要求他自己去找。
**改：** `The maximum ratings are listed above in this table.` —— 明确指向，且与实际行序（Max 行在上）一致。
德：`Die Maximalwerte stehen oben in dieser Tabelle.`

**意见 5 — `Rated charge / discharge current` 与表内既有 `Max. charge / discharge current` 不平行。**
排版上 "Rated" 与 "Max." 都是限定词，斜杠两侧空格一致即可；但德文侧表内既有行是
`Max. Lade- / Entladestrom`（斜杠两侧有空格，与站内其他 24 处 `Max. Lade-/Entladestrom` 不同）。
**处置：** 同一张表内保持一致优先 → DE 用 `Nenn-Lade- / Entladestrom`、`Nenn-Lade- / Entladeleistung`
（与同表 `Max. Lade- / …` 同形，也与厂商德语原件 `Max. Lade- / Entladestrom` 同形）。

**意见 6 — 认证值里的分隔符混用。**
安全清单用 ` / ` 分隔标准，EMC 行内部用紧贴的 `IEC/EN` 和 `6-1/2/3/4`。读者可能把 `IEC/EN` 读成两项。
**处置：** 不改。这是厂商原件与行业通行写法本身的样子，改成别的分隔符反而偏离原件的标准编号。

**意见 7 — EMC 行单独成行是否多余。**
与安全清单合成一行会更短，但手册把认证块印成两行，德国数据表也印成两行（`Sicherheitsbestimmung` / `EMV`）；
合成一行会让 "IEC/EN 61000-6-1/2/3/4" 被读成安全标准的一部分。
**处置：** 分两行。

**意见 8 — 德文 `Nenn-Lade- / Entladeleistung` 是否为自然德语。**
`Nennleistung`、`Ladeleistung`、`Entladeleistung` 都是德语数据表标准词，`Nenn-Lade-/Entladeleistung`
是常见复合形式（与 `Max. Lade- / Entladeleistung` 直接对应）。通过。

**意见 10 — 德文正文里的斜杠空格（生产读回后补记）。**
首次写入的德文 note 沿用了表格标签的写法 `Lade- / Entladestrom`（斜杠两侧空格）。表内保持这个写法是对的
——同表 `Max. Lade- / Entladestrom` 就这样印，标签之间要彼此同形；但**连续正文里**德语惯例是
`Lade-/Entladestrom` 不带空格，带空格读起来像排版错误。
**改：** note 正文改 `tatsächlicher Lade-/Entladestrom`（与 registry 的德语 qualifier 同形），
标签保留 `Nenn-Lade- / Entladestrom`。已重写生产并读回。

**意见 9 — AI 句式与禁用语扫描。**
初稿与定稿均无「不是…而是…」、三连排比、`Artikel`/`Katalog`/`Versand`/`Bestell`/`Zahlung` 等
`commerce-terms.txt` 词项；无 Marktplatz/Shop 语。`derate` 属 Deep 面技术词，spec 表允许。

## 3. 定稿

**EN**

| label | value | note |
| --- | --- | --- |
| Safety | `IEC62619 / IEC63056 / IEC60730 / IEC62477 / VDE2510 / ISO13849; IEC62040 / N140 / EU 2023/1542 / UN38.3` | GoodWe states that not all certifications and standards are listed; the full set is on its website. |
| EMC | `IEC/EN 61000-6-1/2/3/4` | — |
| Rated charge / discharge current | `100 / 100 A` | GoodWe rates these for Australia only; actual charge/discharge current and power derate with cell temperature and state of charge. The maximum ratings are listed above in this table. |
| Rated charge / discharge power | `30.7 kW` / `56.3 kW` | 同上 |

**DE**

| label | value | note |
| --- | --- | --- |
| Sicherheit | `IEC62619 / IEC63056 / IEC60730 / IEC62477 / VDE2510 / ISO13849; IEC62040 / N140 / EU 2023/1542 / UN38.3` | GoodWe weist darauf hin, dass nicht alle Zertifizierungen und Normen aufgeführt sind; die vollständige Liste steht auf der GoodWe-Website. |
| EMV | `IEC/EN 61000-6-1/2/3/4` | — |
| Nenn-Lade- / Entladestrom | `100 / 100 A` | GoodWe weist diese Werte nur für Australien aus; tatsächlicher Lade- / Entladestrom und tatsächliche Leistung werden abhängig von Zelltemperatur und Ladezustand reduziert. Die Maximalwerte stehen oben in dieser Tabelle. |
| Nenn-Lade- / Entladeleistung | `30,7 kW` / `56,3 kW` | 同上 |

分组标题：新增第三组 EN `Certification` / DE `Zertifizierung`（站点既有：2394、4117；`.po` 已有
`Certification` → `Zertifizierung`）。

## 4. 与 registry 的对应

| 页面行 | registry key | registry value |
| --- | --- | --- |
| Safety | `certification` | 同值（`qualifier` 保留原「未列全」限定） |
| EMC | `emc`（本批新增） | 同值 |
| Rated current | `rated_charge_discharge_current_a` | `100 / 100` + A |
| Rated power | `rated_charge_discharge_power_kw` | `30.7` / `56.3` + kW |

页面 note 是 registry `qualifier` 的客户面改写（去掉内部页码引用），语义逐项对应：
澳规限定、随温度/SOC 降额、最大值分列。页码留在 registry 与本文档，不上页面。

## 5. 已核但不在本批的事实差

`cycle_life`：registry 记 `6000 (25 ± 2 °C, 0.5C, 90% DoD, 70% EOL)`（数据表 p2），手册物理 p81 印
`≥6000 times until 70% SOH under 25±2°C, 0.5C and 100% DOD`，Note 3 另写 `For Australian DOD is 98%`。
两份厂商文件对循环寿命的 DoD 条件不一致（90% / 100%）。该行不在本批范围（页面表也没有循环寿命行），
不改值，登记于验收记录待业主定口径。
