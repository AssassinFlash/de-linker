# 官方负载画像证据：BDEW/VDEW Standardlastprofile Strom

2026-11-11 采集、2026-11-12 记录。本文件只记录实现实际引用的原文、身份、换算与边界，不改变任何产品、项目或并网结论。

## 1. 为什么是这两个版本

能量域（#1107）此前的 10 次生产证据输入全为自有合成夹具，`rights_basis` 写的是「not measured consumption；只有 PV 是真实 PVGIS」。业主 2026-11-11 晚间裁定：这类数据自己去搜，不存在等业主提供的等待态。

德国客户是我们账号分布的第一大群（生产 23 个账号中 DE = 11），德国电力行业用于计量与结算的标准合成负载画像就是 BDEW（其前身 VDEW）的 Standardlastprofile。存在两个版本，**必须分别入库、绝不混用**：

| 版本 | 发布者 | 季节维度 | 日型 | 归一化基数 | 表内单位 |
| --- | --- | --- | --- | --- | --- |
| 1999 | VDEW（BDEW 前身），BTU Cottbus 编制，Materialien M-32/99 | 3 季（Winter / Sommer / Übergangszeit） | Werktag / Samstag / Sonntag | **1.000 kWh/a** | `[W]`（刻钟平均功率） |
| 2025 | BDEW，BTU EVU Beratung GmbH 受委托编制 | **12 个月** | **WT / SA / FT** | **1 Mio. kWh/a** | `[kWh]`（刻钟电量） |

## 2. 采用的原文（六份，均为一手，`bdew.de` 直取）

| # | 文件 | 官方 URL（`https://www.bdew.de/media/documents/` 后接） | 字节 | SHA-256 |
| --- | --- | --- | --- | --- |
| 1 | 1999 主报告 PDF | `1999_Repraesentative-VDEW-Lastprofile.pdf` | 3,021,528 | `b8392ad71eb5efbfc74e243abc92a4caebc0ffbe50d54d1abf256c7385d06ae9` |
| 2 | 1999 系数表压缩包 | `Profile.zip` | 913,965 | `8889fcd419d567861ac1a5b9e07960ae8e98215137fca09acf5c57a467d2fa91` |
| 3 | 2000 方法论 step-by-step PDF | `2000131_Anwendung-repraesentativen_Lastprofile-Step-by-step.pdf` | 302,186 | `631e6bad47ab41c355b7a45c1602ac2b27268543d8768e6a726982e7085a85bb` |
| 4 | 2025 应用说明 PDF | `2025-03-17_AWH_Aktualisierte_SLP_Strom_2025_Ver%C3%B6ffentlichung.pdf` | 208,380 | `724d72f2c3f98e11538b78417eecb08cbfbc3de07c3abf5ed034777d6beecf37` |
| 5 | 2025 系数表 xlsx | `Kopie_von_Repr%C3%A4sentative_Profile_BDEW_H25_G25_L25_P25_S25_Ver%C3%B6ffentlichung.xlsx` | 482,258 | `1803d4c612693563a784eb61001e7c58ffd6bd18a6bca3780f774f3c3459b845` |
| 6 | 客户分组键映射 PDF | `Zuordnung_der_VDEW-Lastprofile_zum_Kundengruppenschluessel.pdf` | 270,369 | `627db7cb84e8bd602121e67d6ef624a1a0d707bca135e806777d9e7efe364e03` |

入口页：`https://www.bdew.de/energie/standardlastprofile-strom/`（HTTP 200；上表六条链接均出现在该页的下载清单中）。

`Profile.zip` 内含三个成员；因 zip 文件名是 cp437 编码，解压后哈希须针对成员本身：

| 成员 | 字节 | SHA-256 |
| --- | --- | --- |
| `Repräsentative Profile VDEW.xls`（H0/G0–G6/L0–L2 系数） | 162,816 | `5bdcfd169c298f04cf538178e97e171376b26ed07c444b5c2068c7a52a27299d` |
| `Haushalt-Lastprofil.xls`（家用的静态与动态化年历程） | 2,696,192 | `9e8e989b2b3bc4e52e20a5a500a1a1f093e2ca66e616e02f85a07e7e3bc4336f` |
| `Anhang.doc`（同一系数表的排版版） | 642,048 | — |

`Anhang.doc` 与 `Repräsentative Profile VDEW.xls` 数值逐位一致（抽查 G0「Winter/Samstag」前六值 `70,0 / 73,0 / 75,9 / 77,6 / 77,1 / 75,0`），是同一版的两处发布，可互证。

## 3. 2025 版：官方规格原文

`2025-specifications.txt` 逐字摘录（PDF 第 3 页）：

> Für alle neuen Profile gelten die folgenden Spezifikationen:
> › Alle neuen Profile arbeiten nun mit zwölf Monaten (Saisons). Die bisherigen Profile arbeiteten lediglich mit drei Saisons.
> › Alle neuen Profile arbeiten mit drei Typtagen: Werktage (WT), Samstage (SA) sowie Sonn- und Feiertage (FT).
> › Es gilt der bundeslandspezifische Feiertagskalender nach Definition des BDEW.
> › Alle Profile sind auf 1 Mio. kWh Jahresverbrauchsmenge normiert.

**「bundeslandspezifisch」是关键边界**：BDEW 的节日日历按 Bundesland 定义，本仓库没有任何州级节日法的一手文本，因此实现只应用九个全国统一节日（见 §6），州级节日由调用方显式声明。

版本间的可用性差异（同 PDF 第 3 页）：

> Jedem Netzbetreiber steht es weiterhin frei, bei der Bilanzierung auf die aktualisierten Profile aus dem Jahr 2025, die alten Profile aus dem Jahr 1999, eigene Profile oder eine Mischung der verschiedenen Optionen zurückzugreifen.

即两版在法律上并列可选，不存在「新版自动取代旧版」；这也支持两版并存入库。

各画像的编制样本量（同 PDF §2.1–§2.5）：H25 来自 62 家配电网 2018/2019 的结算数据（含中等 Prosumer 影响）；G25 来自十家分布全德的配电网约 2,000 条 iMSys 时序（2022/2023）；L25 沿用旧 L0 扩成 12 个月；P25 来自 400 条 iMSys、S25 来自 200 条 iMSys。

**动态化适用性由表头明示**：H25 表头「Bei Ausrollen der Profile ist die Dynamisierungsfunktion anzuwenden!」，G25/L25 表头「…ist die Dynamisierungsfunktion **nicht** anzuwenden!」。

## 4. 1999 版：季节、日型与归一化原文

`1999-seasons-and-daytypes.txt` 逐字摘录：

> Winter           01.11. bis 20.03.
> Sommer           15.05. bis 14.09.
> Übergang         21.03. bis 14.05. und 15.09. bis 31.10.
>
> Alle in dem betreffenden Versorgungsgebiet geltenden Feiertage erhalten das Sonntagsprofil; der 24. 12. und 31. 12. erhalten das Samstagsprofil, sofern sie nicht auf einen Sonntag fallen.

`1999-normalisation.txt`（§8.3）逐字摘录：

> …wurden im nächsten Schritt die Lastprofile auf einen spezifischen Jahresverbrauch von 1.000 kWh/Jahr normiert…

同一节还说明矩阵值「einen Viertelstunden-Verbrauch in Wh (Wattstunden; =1/1000 kWh) darstellen」——但**系数表 `.xls` 的表头写的是 `[W]`**（刻钟平均功率），两者只有在乘 0.25 h 后才等价。这是本实现把 1999 表按功率处理、2025 表按电量处理的依据；实测校验见 §7。

## 5. 动态化多项式：两处官方来源逐位一致

xlsx 的 `Dynamisierung` sheet 里该函数是一个嵌入图片（`xl/media/image1.png`，1534×370，243,245 B），xlsx 无公式文本。同一函数在 2000 方法论 PDF 第 19 页有正文版（`1999-dynamisation.txt`）：

> Ft = -3,92\*10⁻¹⁰ \* t⁴ + 3,2\*10⁻⁷ \* t³ – 7,02\*10⁻⁵\* t² + 2,1\*10⁻³\* t + 1,24
> mit t = Tagesnummer des jeweiligen Tages der gewählten Periode (orientiert am Jahreskalender; 1 ≡ 1.Jan, 365(366) ≡ 31.Dez.)

两者系数逐位相同。PDF 另给出三个检查点，已在测试里逐位断言：

> Das Minimum liegt mit F202= 0,7847 am Tag Nr. 202 … Das Maximum liegt mit F366= 1,2597 … Im Normaljahr liegt das Maximum mit F365= 1,2572.

实现的 `dynamisation_factor()` 复现：F(202)=0.7847、F(365)=1.2572、F(366)=1.2597。

## 6. 节日口径：九个全国节日，州级不代猜

Bundesministerium des Innern（BMI）官方页 `https://www.bmi.bund.de/DE/themen/verfassung/staatliche-symbole/nationale-feiertage/nationale-feiertage-node.html`（HTTP 200）：

> Die Festlegung von Feiertagen ist in der Bundesrepublik Deutschland grundsätzlich Sache der Länder. Die Ausnahme hierzu ist der Tag der Deutschen Einheit.
>
> Durch die Sonn- und Feiertagsgesetze der Länder sind jedoch neun Feiertage bundeseinheitlich gesetzlich geschützt: Neujahr, Karfreitag, Ostermontag, Christi Himmelfahrt, Pfingstmontag, 1. Mai, Tag der Deutschen Einheit, erster Weihnachtstag, zweiter Weihnachtstag.

实现据此：`nationwide_holidays(year)` 只返回这九个；`extra_holidays` 供调用方按 Bundesland 补充（测试用 Bayern 的 Fronleichnam 与 Allerheiligen 演示）。**不内置任何州级节日**，因为本仓库没有州节日法原文。

## 7. 实测校验：表结构与归一化基数都对得上

用官方自己发布的年历口径（九个全国节日 + 周六/周日）重算年积分，与各版声明的基数比较：

| 画像 | 版本 | 展开后年积分 | 官方基数 | 比值 |
| --- | --- | --- | --- | --- |
| H0 | 1999 | 998.8 kWh | 1,000 | 0.9988 |
| G0 | 1999 | 1,013.6 | 1,000 | 1.0136 |
| G1 | 1999 | 1,034.4 | 1,000 | 1.0344 |
| G2 | 1999 | 1,023.7 | 1,000 | 1.0237 |
| G3 | 1999 | 1,006.1 | 1,000 | 1.0061 |
| G4 | 1999 | 1,011.8 | 1,000 | 1.0118 |
| G5 | 1999 | 1,011.4 | 1,000 | 1.0114 |
| G6 | 1999 | 1,012.7 | 1,000 | 1.0127 |
| H25 | 2025 | 999,202 | 1,000,000 | 0.9992 |
| G25 | 2025 | 1,002,925 | 1,000,000 | 1.0029 |
| L25 | 2025 | 1,000,454 | 1,000,000 | 1.0005 |
| P25 | 2025 | 999,703 | 1,000,000 | 0.9997 |
| S25 | 2025 | 999,197 | 1,000,000 | 0.9992 |

1999 版的 G 系列偏差在 ±3.5% 内，来源是三季 × 三类日对真实 365 天的离散化——官方自己在 `Haushalt-Lastprofil.xls` 的「Dynamischer Jahresverlauf」里算出 **1000.20 kWh/a**（`Statischer Jahresverlauf` 为 999.98），同样落在基数附近，因此这不是实现缺陷。

**独立交叉验证**：用官方 `Haushalt-Lastprofil.xls` 的「Statischer Jahresverlauf」365 行反查实现的日历规则（季节边界 + 节日→周日 + 12-24/12-31→周六），**361/365 天逐位一致**。4 天偏差的构成：3 天是 1996/1997 年的地区性节日（Fronleichnam、Allerheiligen、Christi Himmelfahrt）在官方表里仍按 Werktag 处理——这正是 BDEW 说的「按 Versorgungsgebiet 的节日」；1 天（1997-05-31）是官方表把周六写成 Werktag 的孤立瑕疵。

## 8. 数据文件（入库形态）

`services/engine/data/load-profiles/`：

| 文件 | 字节 | SHA-256 | 内容 |
| --- | --- | --- | --- |
| `coefficients-1999-vdew.json` | 89,157 | `e0e106cadf486dc87107901565025e9605f101f8e70f1f10cf891009034f53ea` | H0、G0–G6 共 8 画像 × 3 季 × 3 类日 × 96 刻钟 |
| `coefficients-2025-bdew.json` | 241,778 | `b448dddd8209394ada5ba7cc20fb49ae9d8862885fbd393594570ba2ae1b9a8b` | H25/G25/L25/P25/S25 × 12 月 × WT/SA/FT × 96 刻钟 |
| `sources.json` | — | — | 每版的发布者、原始 URL、字节、SHA-256、归一化基数、季节/日型规则、动态化适用性、节日口径、适用边界 |

生成方式：从原件直接解析（xlsx 走 `openpyxl`，xls 走 `xlrd`），**没有任何系数是手工转录的**。测试 `test_published_tables_are_the_hashed_companions_of_their_documents` 校验两个数据文件的字节数与 SHA-256 与 `sources.json` 一致。

## 9. 哪些画像属于哪个能量域角色（关键边界）

| 画像 | 语义 | 引擎角色 |
| --- | --- | --- |
| H0、G0–G6 | 客户侧总负荷 | `gross_load` |
| H25 | 客户侧总负荷（含中等 Prosumer 影响） | `gross_load` |
| G25、L25 | 客户侧总负荷 | `gross_load` |
| **P25** | **含 PV 后的净购电**（自用已从画像扣除） | **`net_import`** |
| **S25** | **含 PV + 电池后的净购电** | **`net_import`** |

依据（`2025-p25.txt` 逐字）：

> Bei Anwendung des Profils P25 muss auf der SOT-Seite … die Eigenversorgung der entsprechenden Haushalte geeignet berücksichtigt werden.

即自用要在供应商侧另行结清；把 P25/S25 塞进 `gross_load` 角色会把 PV 自用算两遍。实现的 `role()` 返回该归属，调用方必须匹配。

未动态化时 P25/S25 的年积分分别为基数的 **94.9% / 88.7%**（自用净额的直接体现）；动态化后回到 99.97% / 99.92%，因为 BDEW 把成品的年历程归一化到同一基数。两者都记录在测试里，避免以后被误判为缩放缺陷。

## 10. 未取得项与替代

1. **州级节日日历原文本**（16 个 Bundesland 的 Feiertagsgesetze）未取得。替代：只应用九个全国节日，州级节日走 `extra_holidays` 由调用方声明；`sources.json` 的 `usage_boundaries` 明示这一点。
2. **BDEW 官方 xlsx 内嵌的动态化函数**只有图片（`image1.png`），公式文本取自 2000 方法论 PDF 第 19 页。两处系数逐位一致，故以 PDF 正文为实现依据，并记录图片哈希以便复核。
3. **不含节日判定的纯系数**才是入库形态：数据文件不带任何日历，日历规则在代码里且按上表可替换。BDEW 未发布「带节日的成品年序列」，所以没有「官方年序列」可与实现逐点比对；可用的是官方自己算的 `Haushalt-Lastprofil.xls` 动态化年历程（见 §7 的 361/365 校验）。
4. **未采用第三方二次发布的系数**：检索中见到多个 Netzbetreiber 与其顾问站点转载的表格，均未采用；只用 `bdew.de` 的一手件。

## 11. 取证通道与故障

- 检索全部经 **Apify**（`apify/google-search-scraper`，德语本地化，`countryCode: de`）。四次查询定位到 BDEW 官方入口页与四份原件。
- **`www.bmi.bund.de` 在本机 TLS 握手被拒**（`LibreSSL SSL_connect: SSL_ERROR_SYSCALL`，curl 与 --tlsv1.2 均失败）。改为 Firecrawl（stealth 代理）取得同一页面全文，HTTP 200，正文逐字摘录于 §6。
- 一次经 Apify 的 `website-content-crawler` 抓 BMI 页与 Firecrawl 并行启动；Firecrawl 先返回后，按资源纪律 `TaskStop` 终止了重复的 Apify run。
- **`Profile.zip` 解压陷阱**：zip 内文件名是 cp437 编码，系统 `unzip` 会以 `(y/n)` 交互式提问并写坏文件（实测 `write error`）；改用 Python `zipfile` 逐成员读取后正常，成员 SHA-256 见 §2。

## 12. 本轮不改变的事

- 没有部署、没有合并、没有写生产；没有触碰 `country_rules.py`、`grid_connection*.py`、`report_copy.py`（SE 线）。
- 没有把任何画像当作「客户实测用电」；`basis` 字段写的是 `published_load_profile`，`origin` 写的是 `modelled`（引擎的四个 Origin 之一），与 #1107 合成夹具的 `synthetic` 明确区分。
- 没有为任何产品、项目或客户生成结论。

## 13. 引擎实跑记录（可复现）

命令（worktree 内，`services/engine`）：

```
uv run --locked pytest tests/planning/test_load_profile.py -q
uv run --locked python ../../tools/checks/ci_engine_tests.py
```

`test_official_bdew_profiles_run_through_the_real_energy_kernel` 的实际读数：

| 量 | 值 |
| --- | --- |
| 画像 | BDEW G25（2025 edition 系数，展开到 2020 闰年） |
| 申报年用电 | 400,000 kWh |
| 时间轴 | 35,132 个刻钟（= 与 PVGIS 轴的交集） |
| 引擎 `gross_load_kwh` | **403,556.6944** |
| 独立展开器同年全量 | 403,579.8680 |
| 差额 | 23.17 kWh = 被裁掉的边界小时 |
| 运行状态 | `succeeded` |

引擎与展开器是两条独立代码路径（前者走 `ProfileImport` → `FrozenProfile` → `regrid` → `scenario_frames` → `replay`，后者直接读系数表），两者对同一份数据的年积分一致，属于互证而非重复断言。

`ci_engine_tests.py` 结果：`1421 passed, 2 deselected in 274.09s`，exit 0（`ci_expensive` 组在其后单独跑）。本条记录的 2 个 deselected 是 `ci_expensive` 标记的几何 PV 用例，与本改动无关。
