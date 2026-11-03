# 厂商证据采集：储能、端子、组网上限（2026-11-03）

本文件把 2026-11-03 从**我们自托管的知识索引**（142 份文档 / 19,107 个分块，按页切片）里查到的厂商事实固定下来，供引擎证据补齐直接取用。

采集方式：VPS 上只读 FTS5 检索 `python3 /tmp/kbq.py "<query>"`，返回文档标题、页码、原文片段。每条数值都必须能回溯到「文档 + 页码 + 原文」。查不到的一律记 `not found`，不补常识、不推公式。

> 说明：四路并行采集的原始 JSON 在导出时被截断（约 50 KB 上限），本文件是已核对到页码的部分；未收录的条目按「未采集」处理，不视为已证。
> Apify 未参与本次采集，也没有任何集成进产品的路径（AGENTS.md §6：仅研发取证）。

## 1. 储能：每销售单元的模块数与能量

| 型号 | 模块型号 | 模块数/单元 | 标称 kWh | 可用 kWh | 来源（文档 / 页） |
| --- | --- | --- | --- | --- | --- |
| GoodWe GW61.4-BAT-AC-G10 | GW10.2-PACK-ACI-G10 | 6 | 61.4 | 60 | BAT-C 60–112.6 kWh User Manual (EN V1.0) p.80；BAT-C Datasheet (EMEA, EN) p.2 |
| GoodWe GW92.1-BAT-AC-G10 | GW10.2-PACK-ACI-G10 | 9 | 92.1 | 90 | 同上 p.80；ET 50–100 kW user manual (EN) p.55 |
| GoodWe GW102.4-BAT-AC-G10 | GW10.2-PACK-ACI-G10 | 10 | 102.4 | 100 | 同上 p.80；ET 50–100 kW p.55 |
| GoodWe GW112.6-BAT-AC-G10 | GW10.2-PACK-ACI-G10 | 11 | 112.6 | 110 | 同上 p.80；BAT-C Datasheet p.2 |
| GoodWe GW208.9-BAT-LC-G10 | GW52.2-PACK-LC-G10 | 4 | 208.9 | 未载明 | BAT-C 208.9–261.2 Datasheet (EMEA, EN V1.1) p.2 |
| GoodWe GW208.9-BAT-LCD-G10 | GW52.2-PACK-LC-G10 | 4 | 208.9 | 未载明 | 同上（V1.0 版）p.2 |
| GoodWe GW261.2-BAT-LCD-G10 | GW52.2-PACK-LC-G10 | 5 | 261.2 | 未载明 | 同上 p.2；BAT-C 208.9–261.2 User Manual p.76 |
| GoodWe GW35.8/40.9/46.0/51.2/56.3-BAT-I-G10 | — | 7 / 8 / 9 / 10 / 11 | 35.8–56.3 | 同标称 | GoodWe ET 50–100 kW user manual (EN) p.52 |
| SAJ B2-5.0..25.0-HV1/HV5、BU2-5.0..25.0-HV1/HV5 | 单个电池模块 5.0 kWh | 1 / 2 / 3 / 4 / 5 | 5.0–25.0 | 4.5–22.5 | SAJ B2 Series HV User Manual (EN) p.10 |
| SAJ CB2-57.3 / 71.6 / 85.9 / 100.3-HV5 | — | 4 / 5 / 6 / 7 | 57.3–100.3 | 51.5–90.2 | SAJ CHS2 Datasheet (EN, BEU) p.4；SAJ CB2 User Manual (EN) p.12 |
| GoodWe GW125/261-ESA-LCN-G10/G11 | 52.25 kWh/模块 | 5 | 261.25 | 261.25 | GW ESA 261kWh User Manual EN V1.6 p.94 |
| Pylontech L260-OMNI (M7-1000V-125kW/260kWh) | — | 未载明 | 260 | 254.8（DoD 98%） | Pylontech OPTIM US L260-OMNI Datasheet p.2 |

关键比例：BAT-C 系列 `可用/标称 = 0.98`（GoodWe BAT-C Limited Warranty, Europe p.1 原文：`The usable energy per kilowatt-hour (kWh) of nominal capacity is 0.98 kWh.`）。

## 2. 并联上限（可直接变成 `max_units` 类边界）

| 系统 | 上限 | 来源 |
| --- | --- | --- |
| BAT-C 92.1/102.4/112.6（单簇） | 4 台/簇；最大簇容量 368.4/409.6/450.4 kWh | ET 50–100 kW Systemhandbuch (DE) p.12；EN p.4 |
| BAT 35.8–56.3 kWh | 6 台并联 | ET 50–100 kW user manual (EN) p.37 |
| Lynx D G2（GW5.1/8.3-BAT-D-G2x） | 12 台并联 | Lynx D G2 datasheet (EN, EMEA) p.1 |
| SAJ B2/BU2 | 最多 5 个模块 | SAJ HS2 series datasheet (EN) p.2 |
| SAJ HS3 系统 | 单机最多 8 个电池；落地堆叠 ≤4，壁挂 ≤3 | SAJ HS3 T2 User Manual (EN V4) p.18、p.39 |
| SAJ CB2 × CH2 逆变器 | 1 台 CH2 最多接 4 个 CB2 | SAJ CB2 User Manual (EN) p.8；Quick Installation Guide p.5 |
| GoodWe ESA 261 kWh | 主从并联最多 8 台 | GW ESA 261kWh User Manual EN V1.6 p.46 |
| Pylontech L260-OMNI | 最多 6 台并联（260→1560 kWh） | L260-OMNI datasheet excerpt pp.17-18 |

`EzLogger / EzManager 每台可带多少台逆变器`：在已托管文档中**未查到明确上限**。fixtures 里的 `max_units: 10` 至今**没有任何原始出处**，因此不得恢复（AGENTS.md §2：项目里的数字不天然可信）。

## 3. 逆变器端子图（`manufacturer_terminal_map`）

### GoodWe ET 50–100 kW（对应产品 1946 / 1947 / 1948 / 6506 所在系列）

- DC 侧：8 路 MPPT、每路 2 串，共 16 个 PV 直流接线端子（`PV-CZM-61100`，Cu 4–6 mm²）；串联数 <9 时按 MPPT1→MPPT8 顺序接（ET 50–100 kW User Manual EN p.160）。
- 电池侧：2 路电池输入（正/负各 2），压接工具 YQK-70（p.49、p.95）。
- AC 侧：`3L/N/PE`，220/380、230/400、240/415 V；AC 接线模块 = 部件 4，接地端子 = 部件 5，PE 端子 ×2（25–35 mm² Cu）（p.49、p.182）。
- 备电：逆变器本体**没有** BACK-UP 端子，必须经外部 STS（GW125K-STS-G10 / GW375K-STS-A-G10 / GW750K-STS-A-G10）；STS 端口为 PE、INVERTER、BACK-UP(L1/L2/L3/N/PE)、SMART-PORT、GRID（p.51、p.185）。
- 通信：COM1（PAR1/PAR2、RSD-1/2、DI-1/2、DRM&RCR、EMS RS485-A1/B1、LOAD、GEN）、COM2（CAN-H1/L1、CAN-H2/L2、STS、Meter RS485）、COM3（Dongle）（p.190–192）。

### 其他已核对型号（同上文档集）

- **GoodWe ETR 50–125 kW**：8 或 10 路 MPPT、每路 2 串（8→16 串端子，10→20）；1 路电池输入（Cu 70 mm²）；`3L/N/PE` 或 `3L/N`；BACK-UP 仅经 STS；COM1/COM2 端口定义见 EN p.24、p.71。
- **GoodWe ESA 5–30 kW**：MPPT 3/4，串数 1/1/1 与 1/1/2/2；本体带 BACK-UP 端口；电池接口为单连接器（BAT+、BAT-、PE、BMS）；通信口含 PAR1/PAR2、CT、DRM/RCR、METER、DI、LOAD、GEN、EMS（EN V1.5 p.52、p.163–164）。
- **GoodWe ESA 3–10 kW（单相）**：MPPT 2 或 4，串数 1/1 与 1/1/1/1；`L/N/PE`；本体带 BACK-UP（EN V1.8 p.124、p.152–153）。
- **SAJ H2 (10–30K) T2/T3**：MPPT 2（T2）或 3（T3），串数 2/2 与 2/2/2；双电池输入 BAT1/BAT2；`3L+N+PE`；本体带 BACK-UP；通信含 LAN/CAN/PART/EMS/RS485/METER/DRM（User Manual DE/EN p.43、p.45）。

## 4. 采集中发现的文档冲突（不得替业主择一）

| 型号 | 字段 | 值 A | 值 B |
| --- | --- | --- | --- |
| GoodWe GW6.0-BAT-D-G20 | 可用能量 | 5.8 kWh（Lynx D G2 datasheet p.2） | 5.9 kWh（ESA 5–30 kW Benutzerhandbuch DE V1.4 p.368） |
| GoodWe GW9.0-BAT-D-G20 | 可用能量 | 8.7 kWh（同上 p.2） | 8.85 kWh（同上 p.368） |
| SAJ BU3-5.0-TV2-PRO | 可用能量 | 4.8 kWh（HS3 T2 User Manual EN V4 p.114） | 4.5 kWh（同文档 p.121） |
| GoodWe GW25K/29.999K/30K-ETA-G20 | 每 MPPT 串数 | 1/1/2/2（Datasheet p.2；DE 手册 p.337） | 外观图 p.51–52 写 4 |

这四处保持冲突状态入库，需要业主或原厂更新版本文档裁决，不能按「取最新」或「取较大值」自行合并。

## 5. 本次未采到（知识库里没有对应文档）

BYD Battery-Box（HVS/HVM/HVB）、Huawei LUNA2000、Sungrow SBR/SBH/PowerStack/PowerTitan、Pylontech US/Force 系列、GoodWe Lynx Home F/U/A/C 系列——索引里只有型号名（出现在 GoodWe 兼容性总表与保修文件），**没有数据手册**。这些型号的模块数、可用能量、并联上限目前无证据，引擎只能保持 `unresolved`。

## 6. 这批证据能解锁什么

- BAT-C 与 SAJ/Pylontech 的**并联上限**可把 `plant_assessment` 的并行边界从"恒为空"变成可判定（前提是 `compatibility.json` 的对应 pair 记上 `max_units` 并带本条来源）。
- GoodWe ET 系列的**端子图**可让 1946/1947/1948/6506 的 AC/PE/电池/通信端点从 `not_assessed` 进入 `documented`，前提是按 `installation_facts` 的既有 schema（`basis: manufacturer_terminal_map` + `specification.terminal_domain` + `terminals[]` + `source`）落库，并绑定当前 `product_revision`。
- BAT-C 的 `0.98` 可用比例可用于校验报告里的可用能量，而不是重新推导。

**仍未解决、且不能靠本文件绕过的**：无条件连续充放电 AC 功率标量（0/106）、`manufacturer_pair` 要求"已发布且无 condition"而 51/51 已发布 pair 都带 condition、AC/多芯/>6 mm² 载流表（`cable-references.json` 仍只有 2 根单芯 DC 光伏电缆）。这三项照旧必须是 `unresolved`。

## 7. 组网上限：SEC3000C（本轮补）

`GoodWe SEC3000C Datasheet (EMEA, EN) p.1` 原文表格：

> `| Max. Inverters Supported | RS485: 60, LAN: 10 |`

结论：所谓「一台 EzLogger 带 10 台逆变器」只在 **LAN 模式**下成立；走 RS485 是 60。任何把它当通用上限的用法都是错的，必须绑定接入方式。
`EzLogger3000C` 本身在 143 份托管文档中**没有独立手册**，只作为 `Datalogger | EzLogger3000C × 1` 出现在 SEC3000C 的配置表里。

## 8. 生产载荷实测：德语配置器的翻译内联（2026-11-03 14:47 CST）

`/de/loesungskonfigurator/` 的 HTML 里有 `<script id="wp-script-module-translation-data-linker-planner">`，内容是 `build/planner/assets/planner.js` 的**整份**德语翻译目录，278,563 B，一个 `setLocaleData("linker-tools", …)` 调用。

| 页面 | 原始 HTML | 压缩传输 |
| --- | --- | --- |
| `/solution-configurator/` | 279,781 B | **45,253 B** |
| `/de/loesungskonfigurator/` | 587,690 B | **137,123 B** |
| `/proforma-request/` | — | 66,302 B |
| `/de/proforma-anfrage/` | — | 75,201 B |

判断：德语配置器比英语多传约 92 KB（gzip 后），来源就是这份内联翻译目录。137 KB 的压缩传输对一个工具页在可接受范围内，**不构成缺陷**；先前「2.1 倍体积」的比较是未压缩字节，不作为性能问题成立。若将来要压，唯一正路是拆分 `planner.js` 的翻译目录或按需加载，而不是绕开 WP 的脚本模块翻译机制。

## 9. ETR 50–125 kW：可直接落库的安装事实（2026-11-03 14:45 CST）

来源文档已在生产 `Publication::manifest()` 中绑定到产品 3595、6507–6511：

- `document_id` `doc-e135c80bd4befdcd3c7e807944036da9a13c966b4c61ad40e6ff7886cf10b42f`
- `blob_sha256` `50bdd49b7be0ef036cafec286994f33af79dab5fc54dfcebbf4549f7e429acf9`
- `document_revision` `f802c3c76d87d6e4dc6b724b400a1ce6fe9ebcb38a3475f3e4d5dcfaffc2ba63`
- 标题 `GW ETR-50-125kW User-Manual-EN V1.0`，215 页

原文表格（`No. | Cable | Recommended Specification | Acquisition Method`）：

| 页码 | 项目 | 原文规格 |
| --- | --- | --- |
| p.60 | Inverter Protective Grounding Cable | 单芯户外铜缆，导体截面 **25–35 mm²**，User-provided |
| p.60 | Battery DC Cable | 单芯户外铜缆，导体截面 **70 mm²**，外径 **14.5–15.5 mm**，Obtained from the battery system accessory kit |
| p.60 | PV DC Cable | 行业标准户外光伏电缆，导体截面 **4–6 mm²**，外径 **5.9–8.8 mm**，User-provided |
| p.61 | Inverter AC Cable（单芯） | 单芯户外铜缆，导体截面 **50–70 mm²**，外径 **14–34 mm**，**SPE ≥ 1/2×SAC** |
| p.61 | Inverter AC Cable（多芯） | 多芯户外铜缆，导体截面 **50–70 mm²**，外径 **22–43 mm**，**SPE ≥ 1/2×SAC** |
| p.62 | DO 并联通信线 | 长度 5 m，Shipped with the unit（仅离网并机场景） |
| p.62 | Meter Communication cable | 长度 10 m，Shipped with the unit |

生产工程 feed（`GET /wp-json/linker/v1/engineering-feed`，85 个产品）中四个 ETR 机型的当前版本与事实状态：

| 产品 | 型号 | `product_revision` | `installation_facts` |
| --- | --- | --- | --- |
| 6508 | GW99.99K-ETR-G10 | `2e375a64a64072206a19b9afb28f264b72b56d21e472dbff7a5ea88d47ac242d` | 无 |
| 6509 | GW100K-ETR-G10 | `36cee323c7b04dc13adcdc59f379216101f93ed1751301c9c8b692af4a0b8c3b` | 无 |
| 6510 | GW110K-ETR-G10 | `830ca6597193b83379895926bfc5ec499981c348e4a31fe801edd51d34862086` | 无 |
| 6511 | GW124.99K-ETR-G10 | `829a52e7504213453d56ba633038b947ecb1414aca55df6de589607eac10c52b` | 无 |

即：文档已绑定、页码与原文已核对，缺的只是把这四项 conductor 事实写进 `548-installation-facts.json` 并走一次 guarded 迁移。这是下一段工作的直接输入，不需要再查资料。

## 10. 全站 URL 状态（2026-11-03 14:43 CST）

sitemap 五张子图合计 **258** 条 URL，逐条请求：**249 条直接 200**；9 条首次并发超时，单独串行重试后全部 **200**。合计 **258/258 = 200**，没有断链、没有 404、没有 5xx。
