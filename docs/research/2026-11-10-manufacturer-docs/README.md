# 原厂原件获取与核实：四项缺口（#548 工程放行原件）

日期：2026-11-10 / 11（北京时间）。独立 worktree `/tmp/docs-work`，基于 main `480fe0628`。
范围：只做外部取证、原件下载与版本核实；**不改 registry、不改 Woo、不写生产、不改产品代码**。

承接：`docs/research/2026-11-04-vendor-originals.md`、`docs/research/2026-11-04-sgs-annex-search.md`、
`docs/acceptance/2026-10-31/548/installation-facts-apply.md`（SGS/端子各节）、
`docs/acceptance/2026-11-10/goal-state-ledger.md` §3。本报告不重复其结论，只补本票要求的型号口径与新证据。

## 0. 一句话结论

| # | 目标 | 结论 | 是否为新原件 |
| --- | --- | --- | --- |
| 1 | SGS Annex（Pylontech US3000C/US5000 优先） | **前提需纠正**：Pylontech 的电池安全认证全部走 TÜV Rheinland / TÜV SÜD PSB / UL，官方目录 321 件里**零个 SGS 文件**。SGS 对 Pylontech 的存在形式是 2024-11-07「欧盟电池法规 Module A 合规认证」（工商业储能，非 US 系列），不是可下载的 Annex。SGS 证书目录的公开查询仍被 Akamai/Turnstile 拦。**四项中唯一无法以"下载到的原件"闭合的一项。** | 否（负结果 + 6 份 TÜV/UL 替代原件，覆盖 5 个独立证书号） |
| 2 | BAT-C 定量充放电曲线 | **定量曲线不存在于任何公开件**。官方 87 页手册 V1.0（2026-10-14）在手且与既往记录同哈希；全文只有一条降额脚注，无任何绘制曲线或坐标表。GoodWe BAT 目录全量 16 项枚举亦无专项曲线文件。 | 否（原件已在库，本次仅复核） |
| 3 | ET 运行包络 | **定量包络未公开**。GoodWe ET 目录 40 项全量枚举，无 Annex/Anhang/Prüfbericht 条目；数据表 V2.1 与 307 页用户手册均与既往记录**逐字节相同**；手册中三处降额表述均为定性。 | 否（原件已在库，本次仅复核） |
| 4 | terminal map（SAJ H2 / Pylontech US） | **已闭合**。两家当前官方手册本身即含完整端子定义，且 SAJ H2 手册与我们托管件**逐字节相同**。不存在"更全的独立端子图"这种东西。 | 是（SAJ H2 已验证；Pylontech 端子页首次定位到页） |

另有一项本票未列但实测发现的**真实版本缺口**（§6.1）：US5000 官方手册已到 **V1.3（2026-01-12，44 页）**，我们托管并入库的是 **V1.0（36 页，2023-08-17）**，跨两代，且新版改了推荐电流与电压窗口。

---

## 1. 口径确认：四个目标各指什么（先查后做）

任务书要求先搞清 "ET" 与"terminal map"确切所指。核查结果：

- **ET = GoodWe ET 系列三相混合逆变器**，不是任何缩写歧义。依据 `docs/research/2026-10-23-capability-inputs/FACT-INTAKE.md` §5「交叉电气边界：ET80 + GW61.4」、`docs/specs/548-workbench-application.md` §"Documented reverse input and battery-terminal ceilings"、`docs/acceptance/2026-11-05/vendor-originals-integration.md` 表第 2 行。具体型号 **GW75K / GW80K / GW99.99K / GW100K-ET-G10**（Woo 1946 GW80K-ET-G10 等）。
- **BAT-C = GoodWe BAT-C 60–112.6 kWh 电池系统**（GW61.4 / GW92.1 / GW102.4 / GW112.6-BAT-AC-G10）。"定量充放电曲线"指 SOC × 电芯温度 × 倍率/持续时间的量化降额曲线。
- **terminal map = 设备的端子/针脚级连接定义**（端子代码表 + RJ45 逐针 + Console/Contact 针定义），供工作台判断电池端口与通信接线，不是"接线示意照片"。
- **SGS Annex** 在本票中给定为"电池认证附件，Pylontech US3000C/US5000 优先"。这与既往两轮报告的对象（GoodWe ET VDE4110 证书的 164 页 Annex）**不是同一件东西**——见 §2，这个给定前提本身不成立。

`docs/specs/548-*.md` 全部 27 份中，只有 `548-workbench-application.md` 与 `548-design-geometry.md` 提到 terminal/envelope，且都指向 GoodWe 电池（1956–1958 的 COM1/2/3/4）。没有一份 spec 把 SGS 与 Pylontech 关联。即：**本票的 SGS 目标无法从仓库内任何 spec 推出，只能从外部事实核对**。

---

## 2. 目标 1：SGS Annex —— 前提不成立，负结果可证

### 2.1 Pylontech 官方目录全量枚举（321 件，第一次做完）

发现并打通 Pylontech 官方下载中心的真实接口（页面是 Nuxt SSR 空壳，
`/service/downloads` 返回 "No content available at the moment"）：

```
GET https://en.pylontech.com.cn/prod-api/api/service/downloadInfo?pageNum=N&pageSize=100
```

分类树（`/prod-api/api/service/buildDownloadTypeTree`）：

| id | 分类 | 件数 |
| --- | --- | --- |
| 128 | Operation Manual | 57 |
| 134 | Product Portfolio（数据表） | 34 |
| 135 | **Safety Certification** | 203 |
| 136 | Compatible Product | 2 |
| 137 | Product warranty | 25 |

分页 1–6 页抓完，去重 **321 个唯一文件**（原始清单见 `raw/pylontech-download-catalogue-2026-11-11.json`）。

**检索结果**：对 321 个文件名做 `sgs|annex|anhang|regulation|2023/1542|1542` 全量正则匹配 —— **0 命中**。

US 系列的认证构成（全量列出，逐条可核）：

| 类别 | 文件（官方目录原名） |
| --- | --- |
| IEC 62619 | `US3000C-IEC62619-R 50485157 0004_extsigned`、`US3000C-IEC62619-R50485157 0003`、`US3000C-IEC62619-SSH-D02F-PV20111019570`、`US5000-IEC62619-Cert 211-282160090-000` |
| IEC 63056 | `US5000-IEC63056-Cert 085-282160384-000` |
| VDE 2510-50 | `US3000C-VDE2510-50-R_50487638_0003`、`US3000C-VDE-R50487638 0001-0002 P00010765`、`US5000-VDE2510-Cert 64.280.21.60301.01`、`US5000-VDE2510-64.280.21.60301.02 Cert B EN` |
| UL 1973 | `US3000C-UL1973-80045633_CofC`、`US 3000C-UL 1973 2022-80188113 _CofC`、`US5000-UL1973-CoFC_80075844_EN`、`US5000-UL1973-CoFC_80145578_EN`、`US 5000-UL 1973 2022-80188114_CofC` |
| EMC / IEC 62040 / IEC 62477 / UKCA | `US3000C-EMC-*`、`US3000C-IEC62040-*`、`US3000C-IEC62477-*`、`US3000C-UKCA_*`、`US5000-EMC-*`、`US5000-UKCA-*` |
| UL9540A / UL 系统 | `US3000C 5000_5011347-220700523SHA-001_ATM`、`US3000C,US5000_5kW 5011347-2308A0464SHA-001_ATM`、`US3000C,US5000_15kW …A0466`、`US3000C,US5000_15kW,30kW,45kW …A0465` |

签发机构全部是 **TÜV Rheinland（R 504x…）**、**TÜV SÜD PSB Singapore（CB，SG PSB-BT-xxxxx / CB 090762 xxxx）**、**UL**。**没有任何一份 SGS 文件。**

### 2.2 SGS 与 Pylontech 的真实关系（这解释了"为什么会有 SGS 这个说法"）

Pylontech 官网新闻（`en.pylontech.com.cn/newsroom/info/62`、`…/info/69`，德文镜像同文）载明两件事，均**不产生可下载的 Annex**：

1. **2024-11-07，CIIE**：SGS 向 Pylontech 颁发首个**欧盟电池法规（EU Battery Regulation）合规认证 Module A**，对象是"工业与商用储能产品"（industrial and commercial energy storage products），不是 US3000C/US5000 这类低压户用模组。
2. 更早：SGS 授予 Pylontech **Witness Laboratory Qualification**（目击实验室资格）——这是对实验室能力的认可，不是产品证书。

也就是说：**"Pylontech 有 SGS 认证"是真的，但那是 EU 2023/1542 的 Module A 合规评定，与"电池安全 Annex（IEC 62619 测试报告附件）"是两件事。** US 系列的电池安全 Annex 如果存在，只会在 TÜV Rheinland/SÜD 手里，不在 SGS。

### 2.3 SGS 官方目录仍不可匿名查询（沿用并复验既往结论）

- 目录页 `https://www.sgs.com/en/certified-clients-and-products/sgs-certified-components-and-products` HTTP 200，但页面含 `cf-turnstile-response`（Turnstile 人机验证）。
- 正式接口 `POST https://www.sgs.com/api/certified-components-and-products/search` 直连返回 **403 Access Denied**（Akamai 边缘，`errors.edgesuite.net` 引用号可见），即使带完整浏览器 UA / Referer / Origin / Accept 头也一样。
- 详情接口 `GET …/details?certno=…&sourceSystem=…` 对空、`SGS`、`CER`、`SGS-CER`、`SGS-PL`、`PL` 六种 sourceSystem 一律返回 `-` 填充占位对象（与既往记录的 4 种尝试一致）。

按纪律：**不处理人机验证、不猜接口、不向厂商索取**。因此本项的可交付结论是：

> 厂商公开渠道（321 件全量枚举）不含 SGS 文件；SGS 官方目录受 Akamai/Turnstile 限制无法匿名查询；Pylontech 与 SGS 的实际认证关系是 EU 2023/1542 Module A（工商业储能），不是 US 系列的电池安全 Annex。

**这证明"公开渠道未提供"，不证明"Annex 不存在"，也不证明"必须付费或厂商授权"。** 任何 Annex 内容都不得外推。

### 2.4 替代原件（已下载，可核 US 系列真实认证链）

既然 SGS 前提不成立，本项按下沉的"电池认证附件"实际需求，把 US 系列的权威认证原件全部取回并入库（见 §11 清单）：

| 原件 | 证书号 | 签发方 | 日期 | 覆盖型号 | 文本层 |
| --- | --- | --- | --- | --- | --- |
| `pylontech_US3000C_IEC62619-R50485157-0004.pdf` | R 50485157 0004 | TÜV Rheinland | 2022-07-11 | US3000C；IEC 62619:2017 + IEC 63056:2020 | 有 |
| `pylontech_US3000C_IEC62619_SSH-D02F-PV20111019570.pdf` | R 50485157 **0001**（同证书早期页） | TÜV Rheinland | 2020-11-09 | US3000C；IEC 62619:2017 + IEC 63056:2020；载明推荐充电器最大电流 90 A、额定容量 74 Ah、上限充电电压 54 V、放电终止 40.5 V | **无（扫描件，需 OCR）** |
| `pylontech_US3000C_VDE2510-50_R50487638-0003.pdf` | R 50487638 0003 | TÜV Rheinland | 2022-09-26 | US3000C；VDE-AR-E 2510-50:2017 + 2 PfG 2698/08.19 | 有 |
| `pylontech_US5000_IEC62619_CB_211-282160090-000.pdf` | CB 090762 0045 Rev.00 / 211-282160090-000 | TÜV SÜD PSB Pte Ltd（新加坡） | 2021-09-09 | US5000; US5000-B；IEC 62619:2017 | 有 |
| `pylontech_US5000_IEC63056_CB_085-282160384-000.pdf` | SG PSB-BT-03076 / 085-282160384-000 | TÜV SÜD PSB Pte Ltd | — | US5000; US5000-B；IEC 63056 | 有 |
| `pylontech_US5000_VDE2510-50_B090762-0051-Rev01.pdf` | B 090762 0051 Rev. 01 | TÜV SÜD Product Service GmbH（慕尼黑） | 2023-05-24，有效至 2028-05-23 | US5000; US5000-B；VDE 2510-50 | 有 |

注 1：`SSH-D02F-PV20111019570` 与 `R50485157 0004` 是**同一证书号 R 50485157 的两个页/版本**（0001 为 2020 年首发，0004 为 2022 年改版）。
两者都在官方目录，不是两份独立认证；引用时以 0004 为准，0001 可作沿革证据。
`SSH-…` 是扫描 PDF（Konica Minolta bizhub，可提取文本仅 2 字节），若要进入知识库需先 OCR。

注 2：`R 50487638` 有三个页段，本次全部取回：
- `…_R50487638-0001-0002.pdf`（3 页，扫描件）：**完整证书正文**。0001 页 2020-11-25，载明
  **US3000C / 3.552 kWh / 48 V / 额定电流 14.8 A / 最大充电电流 90 A / 最大放电电流 90 A / 74 Ah /
  Protection Class I / IP20 / PD2**，依据 `VDE-AR-E 2510-50:2017` + `2 PfG 2698/08.19`。
- `…_R50487638-0003.pdf`（1 页）：变更页，正文写 `as page 0003 continuation`、
  `Modification: Add one new type of MCU for BMS`。
引用 US3000C 的 VDE 合规时必须用 0001-0002 的完整页，0003 只能作为变更证据。

注 3：`B 090762 0051 Rev. 01` 的测试依据是 **VDE-AR-E 2510-50:2017 + PPP 51094A:2022** 两项，
不是只有 VDE-AR-E 2510-50。引用标准时不得只写前者。

匹配度：七份文件（六个独立证书号）全部逐型号点名 US3000C 或 US5000/US5000-B，与 Woo 1133/1134 一致。**没有一份是 SGS 的。**

---

## 3. 目标 2：BAT-C 定量充放电曲线 —— 结论不变，本次独立复核

**文件**：`GW_BAT-C 61.4-112.6kWh_User Manual-EN`，87 页，5,440,295 B，
sha256 `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7`
（与 `docs/research/2026-11-04-vendor-originals.md` §2 记录**逐字节相同**，本次重新下载独立复算）。
来源：`https://en.goodwe.com/Api/downloadFile?id=4626&mid=60&type=2`（HTTP 200，`application/octet-stream`，
PDF 创建 2026-10-14 09:43:51）。

**曲线核查**：全文 2,826 行文本，对 `derat|curve|SOC` 全量检索，唯一实质命中在印刷 p.82（物理 p.84）脚注 2：

> Actual Dis-/Charge Current and power derating will occur related to Cell Temperature and SOC.
> And, Max C-rate continuous time is affected by SOC, Cell Temperature, Atmosphere environment temperature.
> Rated Charge/Discharge Current & Rated Charge/Discharge power only for Australia.

**没有任何绘制的曲线、坐标表、降额矩阵或持续时间曲面。** 唯一带 SOC 的定量表是**存储维护表**（初始存储 SOC 范围 30%~40%、推荐存储温度 0~35 °C、-20~+35 °C 每 12 个月维护一次 / +35~+45 °C 更短间隔），属存放条件，与充放电降额无关。

**旁证**：同步全量枚举 GoodWe BAT 系列官方目录（`catid=4361`，3 页），共 **16 个去重条目**，BAT-C 60–112.6 相关的只有：手册（CZ/DE/ES/FI/HU/IT/NL/PL/PT/SV 共 10 个语种，均 2026-10-14）、两份证书（`IEC 62040`、`IEC62619_IEC63056_EN62477`，均 2026-01-21）、一份西语数据表。**没有"曲线""降额""测试报告"类文件。**

判定：**GoodWe 未公开出版 SOC × 电芯温度 × 倍率的定量曲线。** 现有数据表值 + 手册定量参数表（0.9C/1.1C、180/220 A、96% RTE、≥6000 循环）即全部可得公开事实；更细曲线属厂商内部测试数据。不得由脚注外推任何坐标。

---

## 4. 目标 3：ET 运行包络 —— 官方目录与原件双重确认未公开

### 4.1 官方 ET 目录全量枚举（40 项）

同一接口机制（`https://en.goodwe.com/api/getfilenew.html`，POST `catid=5334&page=N&type=all&clear=1&show=1`），
注意 `page` 必须配合 `show=1` 才返回 `html` 字段内容，否则为空 —— 这是既往轮次"分页永远只见 8 个文件"的另一半原因。5 页抓完，40 个唯一条目（清单见 `raw/goodwe-et-catalogue-2026-11-11.json`）。

**对 40 个标题做 `Annex|Anhang|Prüf|4110|4120|VDE|BAT-C|BAT ` 检索，只命中 1 条**：
`4116 GW_ET 75-100kW_Certificate-VDE4110_VDE4120`（列表日期 2026-03-11）—— 即已知的 1 页封面。

目录构成（40 = 19 证书 + 9 兼容性清单 + 6 手册/快装指南 + 3 数据表 + 3 其他（海岸安装声明、海岸适用产品、第三方 EMS MODBUS 协议））。

### 4.2 原件逐字节复核

| 文件 | 官方直链 | 页数/字节 | sha256 | 与既往记录 |
| --- | --- | --- | --- | --- |
| ET 75-100kW Datasheet EN | `https://en.goodwe.com/Api/downloadFile?id=3685&mid=60&type=2` | 2 p / 684,740 B | `4f7178042e8faf03bd926dc33a5ff0b85ffcd4f46e12f1dcf86d6db10befee4d` | **相同** |
| ET 50-100kW User Manual EN | `https://en.goodwe.com/Api/downloadFile?id=4387&mid=60&type=2` | 307 p / 41,900,846 B | `0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615` | **相同** |

数据表 PDF 创建 2026-07-08（V2.1），型号行明确覆盖 GW75K/GW80K/GW99.99K/GW100K-ET-G10。

### 4.3 包络内容核查

对 307 页手册全文 10,452 行做 `derat|power limit|curve|P-Q|Q(U)|temperature.*derat` 检索，实质命中 3 处，全部定性：

- 物理 p.16 区："When the PV string input voltage is high or the input current is high, the inverter output power may be derated."
- 同章："When the grid voltage and frequency change, it may cause derating of the inverter output power."
- 物理 p.108 区："Adverse environmental conditions such as direct sunlight and high temperatures may cause derating of the inverter output power."

**跨 DC 输入 / 温度 / 网压 / 频率 / P-Q 的定量包络在三份当前文档中均不存在。** 它与 SGS Annex 是同一份未公开测试报告的内容（见 §2.3 对 SGS 查询限制的说明）。

判定：#548 对 ET 的引用只能停在"存在降额、条件未量化"，**不得构造任何降额坐标**。工作台若需要定量包络，只能标为未获证据。

---

## 5. 目标 4：terminal map —— 已闭合（SAJ H2 + Pylontech US）

### 5.1 SAJ H2：官方手册 = 我们的托管件（逐字节相同）

- 官方直链：`https://www.saj-electric.com/hubfs/crm-properties-file-values/H2-(10K-30K)-(T2%2cT3)_User_Manual_de_en_EU-1.pdf`
  （HTTP 200，`application/pdf`，9,782,323 B，59 页）
- sha256 `770ccafa080cb6f4484453c976e48a44df71d7fe63bc220506c1f3e9191a75b3`
- 我方托管件 `https://de-linker.com/wp-content/uploads/2026/10/SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf`
  同字节数、**同 sha256**，与 `docs/research/2026-10-23-fact-sources/document-inventory.json` 记录一致。

→ **不存在更新版本、也不存在"更全的独立端子图"；手册本身即最全公开粒度。**

端子内容（首次逐页定位）：

| 位置（印刷页 / 物理页） | 内容 |
| --- | --- |
| 印刷 p.21（物理 p.14 左半） | 端子代码表 A–K：A `DC-SCHALTER`、B/C/D `MPPT1/2/3`（PV 输入）、E `BAT1+, BAT1-`、F `BAT2+, BAT2-`、G 接地、H `4G/WLAN-Anschluss`（WLAN/4G/Ethernet）、I `LAN/CAN/PART/EMS/RS485/MESSUHR/DRMs`（通信）、J `SICHERUNG`（备电负载）、K `STROMNETZ`（电网） |
| 印刷 p.25（物理 p.16 左半） | 六组 RJ45 逐针：**EMS/MESSUHR**（7=RS485-A、8=RS485-B，1–6=NC）、**RS485_PC1/PC2**（7=RS485-A、8=RS485-B）、**DRM**（1=DRM1/5、2=DRM2/6、3=DRM3/7、4=DRM4/8、5=RefGen、6=Com/DRM0、7=V+、8=V−）、**CAN1/CAN2**（4=CANH、5=CANL，余 NC）、**TEIL1/TEIL2**（1=CANH PAR、2=CANL PAR、4=SYN-BUS、6=HOST-BUS+、8=TRF-BUS）、**LAN**（1=TX+、2=TX−、3=RX+、6=RX−） |
| 印刷 p.22（物理 p.14 右半） | AC 保护开关选型：H2-(10K-20K)-(T2,T3) → 50 A；H2-(25K-30K)-T3 → 63 A；AC 电缆 10–16 mm²（推荐 16），接地附加 8 mm² |
| 印刷 p.26（物理 p.16 右半） | BMS 电缆 8–10 mm²（推荐 8）；`BAT+`/`BAT-` 接电池控制单元 |

该 PDF 是**一物理页排两印刷页**（左右并排、德英对照），引用时务必区分两者：物理 p.14 的页脚同时印着 `21` 与 `22`。

型号覆盖：手册点名 `H2-10K-T3`、`H2-12K-T3`、`H2-15K-T2`、`H2-15K-T3`、`H2-20K-T2`、`H2-20K-T3`、`H2-25K-T3`、`H2-30K-T3`。与我方 Woo 产品 **4107（H2-10K-T3）、4108（H2-12K-T3）、2063（H2-15K-T3）、2064（H2-20K-T3）、1179（H2-25K-T3）、1181（H2-30K-T3-DE）** 全部对上，无缺口。

### 5.2 Pylontech US3000C / US5000：端子定义在手册内（首次定位到页）

| 型号 | 手册 | 端子页（物理页 / 印刷页） |
| --- | --- | --- |
| US3000C | `RESS-Installation Manual-US3000C 5PMPA08-00222 V1.0`（36 p） | **物理 p.13**（印刷 10）：`Definition of RJ45 Port Pin` 表 + `Power Terminals`；Console/Contact 8 针在**物理 p.12**（印刷 9） |
| US5000 | `RESS-Installation Manual-US5000 US5000-B 5PMPA08-00219 V1.0`（36 p） | **物理 p.15**（印刷 12）：`Definitions of RJ45 Port Pin` 表 + `Power Terminals`；Console/Contact 8 针在**物理 p.14**（印刷 11） |
| US5000（V1.3） | `5PMPA08-20078 V1.3`（44 p） | **物理 p.17**（印刷 11）：RJ45 表 + Power Terminals + Breaker 段 |

注：registry 现有 `evidence_refs` 用的是**物理页**（US3000C `:p10`、US5000 `:p11` 对应各自规格表的物理页）。
上表两列并列，便于升级 V1.3 时重新对页。

**RJ45 逐针（两份手册表述一致）**：

| Pin | A/CAN | B/RS485 |
| --- | --- | --- |
| 1–3 | 必须为 NULL（否则可能影响 BMS 与逆变器通信） | 同左 |
| 4 | CAN-H | CAN-H |
| 5 | CAN-L（原文误印为 `CAH-L`，两份手册同） | CAN-L |
| 6 | CAN-GND | CAN-GND |
| 7 | 485A | 485A |
| 8 | 485B | 485B |

**Console（8 针，维护口）**：Pin3 = 232-TX、Pin4* = +5~+12 V wake up、Pin5* = GND wake up、Pin6 = 232-RX、Pin8 = 232-GND
（`*` wake up 信号须 ≥0.5 s、5–15 mA，发完后电压须消失才能正常工作）。

**Contact（8 针，干接点）**：Pin1/2 = 输入（On: 关机，Off: 正常）；Pin3/4 = Output1（On: 停止充电，+/−）；Pin5/6 = Output2（On: 停止放电）；Pin7/8 = Output3（On: BMS 故障）。BMS 内部供 5 VDC；外部请求信号 ≤25 V、<0.3 A。

**US5000-B 专属**：V1.3 手册新增 Breaker 端子说明（type C，60 V/DC，125 A，Icu 10 kA，UL1077 / IEC60947-2）—— V1.0 只在规格表里写 "Breaker: Yes/No"，没有操作说明。

---

## 6. 本票未列但实测发现的真实缺口

### 6.1 US5000 手册跨两代未更新（**可执行项**）

Pylontech 官方 PDF 路由 `/pdf?id=N&type=2` 实际 302 到
`https://en.pylontech.com.cn/prod-api/api/callback?uuid=N&type=2`，再跳阿里云 OSS 直链。
按 `id=44` 取得：

- **当前官方**：`5PMPA08-20078_US5000_User Manual_V1.3_20260112`，44 页，3,920,843 B，
  sha256 `43088b8060b082f3427913bfc0de471cc425474d9de7c1329c4d5d4eceeb4062`，
  PDF 创建 2026-01-12 14:02:19
- **我们托管并在 registry 引用的**：`5PMPA08-00219_V1.0`，36 页，PDF 创建 2023-08-17

规格差异（V1.0 → V1.3，均出自各自 `System Specifications` 表）：

| 项 | V1.0 | V1.3 | 影响 |
| --- | --- | --- | --- |
| Recommended Charge/Discharge Current | **80 A** | **100 A** | 推荐工况取值 |
| Max continuous Charge/Discharge Current | 100 A | 100 A | 不变 |
| Peak Charge/Discharge Current | 101–120@15 min；121~200@15 sec | 105~119@15 min；120~200@15 sec | 峰值口径 |
| 电压 | Discharge 43.5~53.5 V + Charge 52.5~53.5 V（分开两行） | **Operation Voltage Range 43.5~53.2 V**（合并一行） | **上界 53.5 → 53.2 V** |
| Shelf Temperature | −20~45 °C | −20~45 °C | 不变 |
| Short current / duration | <2000 A / 1 ms | <2000 A / 1 ms | 不变 |
| Breaker（US5000-B） | 仅规格表 "Yes" | 规格表 + 独立端子段（type C / 60 VDC / 125 A / Icu 10 kA） | 新增可施工信息 |
| 章节 | — | 新增 Legal Information / Disclaimer / Country of manufacturer | — |

**对 #548 的直接意义**：registry `mat_pylontech_us5000` 现有 `module_voltage_range_v = 43.5 ~ 53.5`，
在 V1.3 口径下应为 **43.5 ~ 53.2**；工作台的"每单元可用窗口"上界随之变化。
`max_charge_current_a = 100` 在 V1.3 仍成立（对应 max continuous），但 V1.3 的 **recommended** 已由 80 提到 100 —— 即旧手册的"推荐 80"约束已失效。

**本报告只登记事实，不改 registry**（任务边界）。执行建议见 §8。

### 6.2 US3000C 与 US5000 的电流字段语义不一致（**需确认**）

手册 `System Specifications` 表原文三行：

```
Recommend Charge/Discharge Current (A)        37
Max. Charge/Discharge Current (A)             74-89@60sec
Peak Charge/Discharge Current (A)             90~200@15sec
```

registry `mat_pylontech_us3000c` 的 `max_charge_current_a` / `max_discharge_current_a` 均为 **37**。

要点（比"取错字段"更精确）：**US3000C 手册没有 "max continuous" 这一行**。37 A 是唯一的稳态值（Recommend），
74–89 A 明标 `@60sec` 属限时能力，90–200 A 属 15 s 峰值。因此 registry 的 37 A 作为**稳态上限**是站得住的，

**第三方交叉证据**：TÜV Rheinland 证书 `R 50487638 0001`（2020-11-25）对同一 US3000C 载明
`Nominal current 14.8 A / Maximum charging current 90 A / Maximum discharging current 90 A`。
即证书口径的"最大"是 **90 A**，与手册的 15 s 峰值下限 90 A 对得上，而不是 37 A。
这进一步说明 37 A 只能是"推荐稳态"，不可作为"最大能力"引用。

问题在字段名 `max_charge_current_a`——它读起来像"最大能力"，实际承载的是"推荐/稳态"。
若工作台用该字段表达"电池端子最大充放电能力"，会把 US3000C 的短时可交付功率低估一半以上；
若用它表达"可持续充放电功率"，则取值正确、只是命名有歧义。

对照 US5000：其手册有独立的 `Maximum Continuous Charge/Discharge Current (A) = 100`，
而 registry 的 `max_charge_current_a` 也正好是 100 —— 两款的字段语义因此不一致（一款取 Recommend，一款取 Max continuous）。

这不是本次取证引入的问题，是对既有 registry 值的对照发现；按任务边界不在本轮修改，列入 §8。

### 6.3 registry 的 Pylontech 数据表链接已 410（**需确认**）

| registry 引用 URL | HTTP |
| --- | --- |
| `…/2026/07/Pylontech_US3000C_Datasheet.pdf`（US3000C） | **410 Gone** |
| `…/2026/07/pylontech-us-series.pdf`（US5000） | **410 Gone** |
| `…/2026/07/Pylontech_US2000C_US3000C_Datasheet_EN.pdf`（US2000C） | **410 Gone** |
| 对照组 `…/2026/10/SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf` | 200 |
| 对照组 `…/2026/10/GW_ET-100kW_User-Manual-EN_V1.2.pdf` | 200 |

三个 Pylontech 数据表的托管字节已不可取，而 registry 仍以它们为唯一 `technical.documents`。
Woo 产品 1133/1134 的 `?p=` 也已 404（`_note_featured_scope_2026_10_01` 记录其已退役、不再供货），
线上仅 2003 OPTIM US L260-OMNI 在售。

### 6.4 SGS 目标的可执行性判断

本票把"SGS Annex、电池认证附件、Pylontech 优先"三件事绑在一起，但事实链是：
Pylontech 的电池安全认证走 TÜV，SGS 只有 EU 2023/1542 Module A 合规评定（工商业储能）。
因此**这一项在当前给定条件下不可通过公开渠道闭合**。若业主真正需要的是"US 系列的电池安全测试报告正文"，
正确来源是 TÜV Rheinland / TÜV SÜD 的证书附件（与 GoodWe SGS Annex 同理，厂商通常只发证书封面）。
本报告已把 6 份可在官方目录直接下载的 TÜV/UL 证书文件全部入库（覆盖 5 个独立证书号）；
**这 6 份是"能拿到的最强认证原件"**。证书附件（测试报告正文）同样未公开——
`R 50485157 0004` 等封面上只写 `ANLAGE (Appendix): 1.0`，无附件正文。

---

## 7. Woo 产品匹配度

| 目标型号 | registry material | Woo product | 线上状态 | 匹配 |
| --- | --- | --- | --- | --- |
| Pylontech US3000C | `mat_pylontech_us3000c` | 1133 | **404**（已退役，`not_supplied`） | 型号一致；资料链接 410 |
| Pylontech US5000 | `mat_pylontech_us5000` | 1134 | **404**（已退役，`not_supplied`） | 型号一致；资料链接 410 + 手册版本落后 |
| SAJ H2-10K-T3 | `mat_saj_h2_10k_t3` | 4107 | 200 | 一致 |
| SAJ H2-12K-T3 | `mat_saj_h2_12k_t3` | 4108 | 200 | 一致 |
| SAJ H2-15K-T3 | `mat_saj_h2_15k_t3` | 2063 | 200 | 一致 |
| SAJ H2-20K-T3 | `mat_saj_h2_20k_t3` | 2064 | 200 | 一致 |
| SAJ H2-25K-T3 | `mat_saj_h2_25k_t3` | 1179 | 200 | 一致 |
| SAJ H2-30K-T3-DE | `mat_saj_h2_30k_t3_de` | 1181 | 200 | 一致 |
| GoodWe ET-G10 系列 | `mat_goodwe_gw75k_et_g10` / `…gw80k_et_g10` / `…gw99_99k_et_g10` / `…gw100k_et_g10` | **6506** GW75K、**1946** GW80K、**1947** GW99.99K、**1948** GW100K | 200 | 一致（数据表 V2.1 的型号行逐一点名这四个） |
| GoodWe BAT-C 61.4 / 112.6 | `mat_goodwe_gw61_4_bat_ac_g10` / `…gw112_6_bat_ac_g10` | 1954 / 1955 | 200 | 一致（手册覆盖 GW61.4/92.1/102.4/112.6） |

（Woo 线上在售商品按 `wc/store/products` 全量 88 件核对；Woo 产品 ID 由接口读出，非 registry 推断。）

注：Pylontech US 系列两款在 Woo 已退役且不再供货，但 registry 保留历史身份与规格。
**这意味着 SGS/端子两项的"客户实际可见"影响目前为零**（产品页 404），价值在于工作台的历史数据完整性与未来重新上架。

---

## 8. 建议的后续动作（本轮不执行，按任务边界）

1. **US5000 手册升级 V1.0 → V1.3**：按 609 原件托管流程入库新文件（sha `43088b80…`），
   更新 registry `module_voltage_range_v` 43.5~53.5 → 43.5~53.2，并在证据页改为 V1.3 的页码。
   注意 V1.3 页码与 V1.0 不同，现有 `evidence_refs` 的 `:p11` 需重新核对。
2. **US3000C 电流字段语义统一**：`max_charge_current_a`/`max_discharge_current_a` = 37 是手册唯一的稳态值
   （Recommend）；手册没有 "max continuous" 行，74–89 A 是 `@60sec` 限时值。两款产品的字段语义不一致
   （US3000C 取 Recommend、US5000 取 Max continuous），需规格线决定统一语义后再改，
   并在字段文档里写明"稳态"还是"最大"。
3. **三个 Pylontech 数据表 410**：重新托管当前官方数据表（`EN-SD-*` 系列在 Product Portfolio 分类），
   或移除失效 URL。当前 registry 的 `technical.documents` 指向死链。
4. **SGS 目标改判**：建议把 #548 的原件缺口表述从"SGS Annex（Pylontech）"改为
   "US 系列的 TÜV 电池安全测试报告附件"，与 GoodWe 的 SGS Annex 缺口分开记账——
   两者签发机构不同、公开政策相同（只发封面）。
5. **BAT-C / ET 定量包络**：维持"未获证据"状态。工作台不得由脚注外推坐标；
   若产品侧需要定量包络，只能作为已知不可得项显式呈现。

---

## 9. 检索轨迹（含负结果，便于复跑）

### 9.1 Apify（按 AGENTS.md §6 优先）

| run | Actor | 用途 | 结果 |
| --- | --- | --- | --- |
| `A9EgGaPp8B4kqkEfz` | `apify/google-search-scraper` | SGS/Pylontech 证书 5 组英文查询 | 定位 `pylontech.de/newsroom/info/62`、`en.pylontech.com.cn` 下载中心、第三方证书副本；无 SGS Annex |
| `XNEtAVhyFGgNKKO0k` | 同上 | SAJ H2 / Pylontech 端子 5 组查询 | 定位官方 hubfs H2 手册直链、`manual.aspx?id=44` US5000 V1.3、Pylontech 官方下载中心 |
| `kBGM8ktKeb5THbibB` | 同上 | `site:sgs.com Pylontech`、EU-Type Examination、IEC62619 UN38.3 | `site:sgs.com` 零结果；确认 Pylontech 侧无 SGS 产品证书索引 |
| `QniNHvhnfUNXiit8R` | `apify/website-content-crawler`（Playwright/Firefox） | 渲染 `en.pylontech.com.cn/service/downloads` + `pylontechhub.com` | 两者均为 JS 壳，`bodyText` 为空 → 改用直连接口（§2.1） |
| `kEOzA2KQqqhNdb0NY` | 同上 | 渲染 `manual.aspx?id=44` | 确认 302 到 `/pdf?id=44&type=2`（API 路由线索） |
| `RJhXG6lSLOuG3XTNr` | 同上 | 渲染 Pylontech 新闻 62/69（en/de） | **取得 SGS 关系原文**：2024-11-07 Module A + Witness Lab（§2.2） |

### 9.2 直连路径（Apify 之后的合法补充）

- **Pylontech 官方下载 API**：`/prod-api/api/service/downloadInfo`、`/buildDownloadTypeTree` —— 321 件全量（§2.1）。
- **Pylontech 官方 PDF 路由**：`/prod-api/api/callback?uuid=N&type=2` → 阿里云 OSS（§6.1）。
  实测 `id=44` = US5000 V1.3；`id=45–64` 抽样为旧式无意义文件名（如 `20211206204718_2364.pdf`）；
  `id=65` = `upload_file_qr`；`id=145–152` 全部回落到 callback 自身（已失效）。
  这说明该 id 空间是历史遗留的混合索引，**只有逐一探测才知道内容，无法按号段推断**。
- **Pylontech 合作伙伴证书库**：`pylontechhub.com/prod-api/market/site/memberCertificate/homeList?companyName=Pylontech`
  → 返回 4 条**合作伙伴/培训证书**（Fidus 培训、Official Sales Partner、Annual Partner、Peak Performance Award），
  **与产品认证无关**，记录为负结果，防止后续误把它当产品证书源。
- **GoodWe 目录 API**：`api/getfilenew.html`，`catid=5334`（ET）+ `catid=4361`（BAT），
  必须 `show=1` 才回 `html`（§4.1）。
- **SAJ 下载中心**：`saj-electric.com/en-de/services-support-download` 按 `product_model=H2_Series` 过滤，
  页面直出 hubfs PDF 链接（无需接口）。
- **SGS**：目录页 Turnstile；`/api/certified-components-and-products/search` 403（Akamai）；
  `details` 六种 sourceSystem 均返回占位对象（§2.3）。**未触碰人机验证。**
- **EUR-Lex**：`eli/reg/2023/1542/oj/eng` 与 `CELEX:32023R1542` 均返回 202 挑战页，
  未能取到 Module A 条文原文 → 报告只述"Module A 合规评定"这一 Pylontech 官方措辞，
  **不展开 Module A 的法律含义**（未取得原文，不推断）。
- **EU NANDO / SMCS**：`webgate.ec.europa.eu/single-market-compliance-space` 为 Angular 壳，
  `/api/nb/notified-bodies*` 各变体均返回同 152 KB HTML，未找到可用 JSON 端点 → 本项不用 NANDO 结论。

### 9.3 明确的负结果（避免下一轮重复）

- `site:sgs.com` 下无任何 Pylontech 条目（Apify google-scraper，0 结果）。
- Pylontech 321 件目录：`sgs|annex|anhang|2023/1542` 正则 **0 命中**。
- GoodWe ET 40 件目录：`Annex|Anhang|Prüf|4110|4120` 仅命中已知 1 页封面 `id=4116`。
- GoodWe BAT 16 件目录：无曲线/降额类文件。
- SAJ 下载中心 H2 系列：只有 5 个手册文件（ITA / de_en_EU / H2-3-6K-S2 / H2-5-10K-S3 / H2-6K-S2-IE），
  **de_en_EU 即我们的托管件**，无 V5 或更新版。
- `en.pylontech.com`（不带 `.cn`）在本机 TLS 握手持续失败（`SSL_ERROR_SYSCALL`）；
  `pylontech.com` / `www.pylontech.com.cn` / `en.pylontech.com.cn` 均 200。
  这是本机网络问题，不是站点下线，不足以推出"官方站不可用"。

---

## 10. 资源报告（AGENTS.md §0）

- **Apify — 逐项已读回删除**：6 个 run 全部 SUCCEEDED，取证后逐个 `DELETE /v2/actor-runs/{id}` 均返回 **204**：

  | run | 用途 | 删除 | 读回 |
  | --- | --- | --- | --- |
  | `A9EgGaPp8B4kqkEfz` | SGS/Pylontech 5 组搜索 | 204 | 404 |
  | `XNEtAVhyFGgNKKO0k` | SAJ H2 / Pylontech 端子 5 组搜索 | 204 | 404 |
  | `kBGM8ktKeb5THbibB` | `site:sgs.com` / IEC62619 搜索 | 204 | 404 |
  | `QniNHvhnfUNXiit8R` | 渲染 Pylontech 下载页 + pylontechhub | 204 | 404 |
  | `kEOzA2KQqqhNdb0NY` | 渲染 `manual.aspx?id=44` | 204 | 404 |
  | `RJhXG6lSLOuG3XTNr` | 渲染 Pylontech 新闻 62/69 | 204 | 404 |

  6 个默认 dataset（`6NKw5BIOkhssWsCuj`、`I0WuHXdFnjn6vhX6P`、`V0xkIm36vNLuJRaPy`、
  `LNk7psbhhLahMGs2F`、`ExasJUYAgOinHOTlx`、`5wYxsYyjGzRRD2Y7c`）随 run 删除，逐个读回 **404**。
  首个 run 及首个 dataset 首次读回各遇一次 30 s 连接超时，重试后均为 404（未把超时当作已删除）。
  费用：6 个 run 合计 computeUnits 约 0.1，实际计费 $0.1 以内。
- **本机**：全部中间下载与解析产物（`/tmp/mfg`、`/tmp/pyl`、`/tmp/*.json`、`/tmp/*.html`、临时 JS/HTML）
  已在核对哈希后删除；`/tmp` 下无本任务遗留目录。仅保留 §11 的 **13 份**入库原件 + 2 份 raw 清单。
- **仓库改动**：仅新增 `docs/research/2026-11-10-manufacturer-docs/`
  （`README.md` + `originals/` 13 份 PDF + `raw/` 2 份 JSON，合计 30 MB）。
  `git status` 确认无其他改动；未改 registry、代码、Woo、生产，未创建本地实例、浏览器窗口或常驻进程。
- **凭据**：Apify token 只从 `~/.config/terravolt-builder/apify.env` 读入环境变量，未落盘、未写入仓库、
  未出现在任何提交或报告中。
- **磁盘**：任务开始与结束均为 2.5 Ti used / 1.1 Ti available；本机净增 30 MB（入库原件 + 报告），无其他增量。

## 11. 入库原件清单（`originals/`）

| 文件 | 页 | 字节 | sha256 |
| --- | --- | --- | --- |
| `goodwe_BAT-C_61.4-112.6kWh_User-Manual-EN_V1.0.pdf` | 87 | 5,440,295 | `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7` |
| `goodwe_ET75-100K-G10_Datasheet-EN_V2.1.pdf` | 2 | 684,740 | `4f7178042e8faf03bd926dc33a5ff0b85ffcd4f46e12f1dcf86d6db10befee4d` |
| `pylontech_US3000C_IEC62619-R50485157-0004.pdf` | 2 | 2,280,839 | `a6143a495cfcab034215b16a07105cc977eb5b2e4b220a9fcafe2316a1e54085` |
| `pylontech_US3000C_IEC62619_SSH-D02F-PV20111019570.pdf` | 2 | 840,208 | `53393f544e3ca24ecc2dd6d309447fa991dc0680d35dcd635ed76f5f0b83b08b` |
| `pylontech_US3000C_Installation-Manual_5PMPA08-00222_V1.0.pdf` | 36 | 2,117,803 | `6657a2db3083c6940eeed7b79fff73ceb6ee5c16773ec15d7368ddf865b04885` |
| `pylontech_US3000C_VDE2510-50_R50487638-0001-0002.pdf` | 3 | 1,153,639 | `76be793e1f917726d5f52000e72ee9928958ec84bd3ba2b18674f0671a4916ce` |
| `pylontech_US3000C_VDE2510-50_R50487638-0003.pdf` | 1 | 614,726 | `349daccd1e842c06d48d8271e4c86a8a0104e3ec1e6d64332ea1bf0c196b9781` |
| `pylontech_US5000_IEC62619_CB_211-282160090-000.pdf` | 2 | 257,884 | `65a201f42e7cb8c415a3b061006e382d517b4ea9d14f03100ac3b1da0ecd1708` |
| `pylontech_US5000_IEC63056_CB_085-282160384-000.pdf` | 2 | 257,680 | `ff5290a04268ea8a932dffb7d3c4283cdd1df9845304584a86ddf4d1cc24b524` |
| `pylontech_US5000_Installation-Manual_5PMPA08-00219_V1.0.pdf` | 36 | 2,430,453 | `70ae894fc6f22bed50c51417c1b35d825ef88c02badb5f31f7694ef11c04b134` |
| `pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf` | 44 | 3,920,843 | `43088b8060b082f3427913bfc0de471cc425474d9de7c1329c4d5d4eceeb4062` |
| `pylontech_US5000_VDE2510-50_B090762-0051-Rev01.pdf` | 2 | 341,631 | `ba488945dc5d09c93a917bf180b3025598824f9b6b882d75893bc87412611bdf` |
| `saj_H2-10-30K-T2T3_User-Manual_de_en_EU.pdf` | 59 | 9,782,323 | `770ccafa080cb6f4484453c976e48a44df71d7fe63bc220506c1f3e9191a75b3` |

`raw/` 内 2 份为可复跑的原始清单：
`pylontech-download-catalogue-2026-11-11.json`（321 条，含官方相对路径）、
`goodwe-et-catalogue-2026-11-11.json`（40 条，含 id / 列表日期 / 标题）。
