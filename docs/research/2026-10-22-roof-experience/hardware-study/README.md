# 四组设备选型依据：型号 → 原表字段 → 条件 → 可执行约束

调查日期：2026-10-22（北京时间）。性质：原始设备资料核实与选型数据审计；没有修改业务代码、商品、兼容合同或运行 feed。本记录只回答指定四组硬件的约束，不代表全商品库、电气设计或国家并网认证已完成核实。

**已确认的问题是约束语义不完整：厂商列出某个兼容组合，并不能证明它满足客户要求的持续功率、停电备电、并机数量或完整附件。** 四组资料已经足以给出具体的反例和重构输入。

## 取证方法与文件

原件来自已授权载入的线上快照 `20261022-1653`，本地原件根目录为 `/Users/chesterjohn/de-linker-local/r549/wordpress/wp-content/uploads/`。以 r549 实际 feed 的 citation/document URL 映射原件，核对型号所在列，运行 `pdfinfo`、`pdftotext -layout`，并渲染关键完整页面核对表格列与脚注。没有发起外部网页抓取；下列托管 URL 是原件的来源标识，不表示本轮重新核验了公网文件或厂商最新版本。

- [source-manifest.json](source-manifest.json)：17 份原件的托管 URL、绝对本地路径、SHA-256、文件大小、PDF 元信息、实际读取的物理页码与提取文本哈希。
- [extracts/](extracts/)：按物理 PDF 页保留的相关原文；未保留整本 351 页手册的文本副本。
- [pages/](pages/)：关键原表完整页面渲染，已逐张看过。文件名中的 `pN` 均指物理 PDF 页，SAJ 双页展开文档的印刷页码另列。
- [product-input-evidence.json](product-input-evidence.json)：运行 feed 与仓库 fixture 中指定型号的字段快照；只用于检查投影与语义，不能作为设备数值的原始依据。

以下 S01–S17 对应 manifest 的 `source_id`。表内英文是原字段名，数值保持原单位。`kW`、`kVA`、`A`、`kWh` 不互相替代。额定、最大连续、最大、限时峰值分别记录。

## 1. GW80K-ET-G10 + GW61.4-BAT-AC-G10

### 原表与版本

| 来源 | 原件、版本与定位 | 核实状态 |
| --- | --- | --- |
| S01 | [ET 75–100kW 数据表](https://de-linker.com/wp-content/uploads/2026/09/GW_ET-75-100kW_Datasheet-EN-20260708-V2.1.pdf#page=2)，页边标识 `20260708-EN-V2.1`，PDF p2，GW80K 列 | 精确型号列，已看 [整页](pages/goodwe-et80-p2.png) |
| S02 | [ET 50–100kW Solution Manual](https://de-linker.com/wp-content/uploads/2026/09/GW_ET-50-100kW_User-Manual-EN_V1.3.pdf)，封面 V1.3 / 2026-06-30，PDF p10–12（印刷9–11）、p16–18（印刷15–17） | 精确型号出现在两类场景设备清单中；场景必须分别读取 |
| S03 | [BAT-C 托管数据表](https://de-linker.com/wp-content/uploads/2026/07/delinker-goodwe_batc60-datasheet.pdf#page=2)，页边 `20260112-EMEA-EN-V1.1`，PDF p2 | 精确 GW61.4 列，已看 [整页](pages/goodwe-batc-old-p2.png) |
| S04 | [另一份 BAT-C 数据表](https://de-linker.com/wp-content/uploads/2026/10/GW_BAT-C-60-112kWh_Datasheet-EN_V2.1.pdf#page=2)，页边 `20260313-EN-V2.1`，PDF p2 | 同型号主要电气数值与 S03 一致，已看 [整页](pages/goodwe-batc-v21-p2.png)；不把不同区域版本的全部配置视为相同 |
| S05 | [Battery Compatibility Overview](https://de-linker.com/wp-content/uploads/2026/09/GW_Battery-Compatibility-Overview_EMEA-EN_20260910.pdf#page=6)，`20260910-EMEA-EN-V029.1`，PDF p6 | ET(80–100kW) 列的 GW61.4 有兼容标记，并附不能满功率说明，已看 [整页](pages/goodwe-compat-p6.png) |
| S06 | [签署兼容声明](https://de-linker.com/wp-content/uploads/2026/09/BAT100KWHInverterCompatibilitystatement.pdf)，PDF p1–2，签署日期 2025-04-07 | 明列 GW80K-ET-G10 与 GW61.4-BAT-AC-G10；证明型号配对，未给系统交付功率 |

| 所属设备 | 原表字段 | 数值及条件 |
| --- | --- | --- |
| GW80K，电池侧 | `Voltage Range` / `Start-up Voltage` | 300–800 V / 300 V；不是 PV 侧的 200 V 启动电压 |
| GW80K，电池侧 | `Number of Battery Inputs` | 2 |
| GW80K，电池侧 | `Max. Continuous Charging Current` / `Max. Continuous Discharging Current` | 各 `100 × 2 A`；必须保留每端口与端口数 |
| GW80K，电池侧 | `Max. Charging Power` / `Max. Discharging Power` | 各 88 kW；是逆变器侧最大能力，不是任意电池组合可交付值 |
| GW80K，交流侧 | `Nominal Power` / `Max. Power` | 80 / 88 kW；地区脚注例如 Chile 另有限制，本轮不核欧洲各国证书 |
| GW80K，备电侧 | `Nominal Output Apparent Power` | 80 kVA；该侧脚注要求 STS Box 或 STS Cabinet |
| GW61.4，整柜 | `Nominal Energy` / `Usable Energy` | 61.4 / 60 kWh。60 的测试条件为寿命初期、100% DOD、0.2C、25±2°C；系统配置可影响可用能量 |
| GW61.4，整柜 | `Nominal Voltage` / `Operating Voltage Range` | 307.2 V / 275.52–346.56 V |
| GW61.4，整柜 | `Max. Charge / Discharge Current` | 180 / 220 A |
| GW61.4，整柜 | `Max. Charge / Discharge Power` | 55.2 / 67.5 kW。脚注明确电芯温度、SOC 导致电流与功率降额，最大 C-rate 的可持续时间也受 SOC、电芯与环境温度影响 |

S02 的并网清单 PDF p12（[整页](pages/goodwe-et-manual-grid-p12.png)）列 GW61.4，允许同型号整柜并联簇最多 4 柜，不允许不同型号混并；建议通过两个电池端口均衡连接，不推荐只接一个电池支路。**柜数增加通常增加电流/能量能力，并联本身不把电压翻倍。** 这是电路关系的推导，不是资料给出的某个完整接线方案。

S05 明确 GW61.4 与 ET80–100 配对不能达到逆变器满功率。其紧接的算式含 `100A`，脚注又明确该数为 ET50 最大连续电流，不能脱离 ET80 的双端口结构，直接当作 ET80 全系统唯一电流。

可审计的推导上限：若 GW61.4 按手册允许的并联配置接至 GW80K 两个端口，即使取电池最高公布电压和两个端口都到 100A，直流上包络也仅为 `346.56 × (100 + 100) / 1000 = 69.312 kW`。在标称 307.2V 时是 61.44kW。只接一个 100A 端口时标称上包络为 30.72kW。**这些只是未计转换损失的上限，不是保证输出；实际仍取整柜/BMS、接法、SOC、温度和逆变器各限制的较小者。** 因此不能以 `ac_power_kw=80` 给这组系统授予 80kW 的电池独立供电或削峰能力。

### 必须形成的约束

1. 配对兼容与性能达标分开：保留兼容声明，同时明确该配对的满功率能力为否；按实际工作电压和端口分配计算可用功率。
2. 电池电压低于 300V 的部分不能当作逆变器可工作的区间。没有电压–SOC 曲线时，不能自行把 275.52–300V 换成某个精确损失 kWh 或可用 SOC 比例。
3. 给每个电池端口建立 100A 连续约束；柜体共用 BMS 的总电流限制也须施加。不能将两个端口的上限重复给同一柜，或把柜并联数量直接乘到逆变器功率。
4. 备电场景另有 STS 与设备清单证据门槛。S02 的 on/off-grid 清单 PDF p17（[整页](pages/goodwe-et-manual-backup-p17.png)）列 GW92.1/102.4/112.6，未列 GW61.4。**清单缺列不等于已证明禁止，但本轮证据不足以把总体 compatible 自动升级成这组电池的备电场景放行。** 应保留待厂商确认状态。

当前 fixture 的 `55.2 / 67.5`、`100 × 2` 等原始字符串数值有原表支持，问题是单个字段含充/放两义、没有工作点与拓扑。兼容合同中的功率/低电压提醒也有原件支持，但文字条件不能替代上述算式和场景守卫。

## 2. GW5K-ETA-G20：备电持续值、峰值与供能条件

### 原表与版本

- S07：[ESA 5–30kW 数据表](https://de-linker.com/wp-content/uploads/2026/09/GW_ESA-5-30kW_Datasheet-EN.pdf)，页边标识 `20260616-EN-V2.1`，PDF p2 是功率模块、p3 是电池模块。PDF 元信息创建日期为 2026-08-17，与页边版本不是一回事。已核 [功率模块整页](pages/goodwe-eta-p2.png) 与 [电池模块整页](pages/goodwe-eta-bat-p3.png)。
- S08：[ESA 5–30kW 用户手册](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf)，封面 V1.5 / 2026-09-04；GW5K 精确型号在 PDF p280–283，脚注在 p311。PDF p283（印刷282，[整页](pages/goodwe-eta-manual-backup-p283.png)）与数据表的备电数值一致。

| 原表位置/字段 | GW5K-ETA-G20 数值 | 条件与意义 |
| --- | --- | --- |
| 电池侧连续充/放电流 | 6.7 / 7.4 A | 700–950 V，启动720V，单电池输入；此设备的高压系统不要与 ET80 或低压裸电池电压混读 |
| 电池侧最大充/放电功率 | 5.0 / 5.5 kW | 逆变器侧，仍受匹配电池供能限制 |
| 电网口额定/最大有功功率 | 5 / 5 kW | 不是停电时的整屋旁路容量 |
| 备电口 `Rated Apparent Power` | 5 kVA | 额定视在功率；需负载功率因数和相别条件才能对应负载有功 |
| 备电口 `Max. Apparent Power` | 离网5.5 kVA；10 kVA只持续10s | 额定、非10秒最大值、10秒峰值需分别建字段；不能把10当持续功率 |
| 备电口 `Max. Apparent Power` | 并网43.5 kVA | 脚注明确并网定义包含电网或发电机侧供能；与停电后仅PV/电池供电不同 |
| 旁路 | 63A | 数据表脚注指内部旁路穿越能力，不是5kW逆变器转换功率 |
| 备电切换 | <4ms | 切换时间不保证任何容量的负载可持续运行 |

S08 PDF p107（印刷106，[整页](pages/goodwe-eta-manual-load-p107.png)）明确：全屋备电接入总负载超过额定功率 1.1 倍，停电后会因过载停止输出。PDF p27 则要求使用手册列明的 GoodWe 电池；无电池只可并网运行。其 30% 离网 SOC 下限为厂家**建议值**，不能写成所有型号不可改变的硬阈值。PDF p60 说明备电预留 SOC 的补能逻辑；从电网补能还要遵守当地规定。

S07 p3 的模块功率会进一步约束整套系统：

| 精确电池模块 | 可用能量 | 最大输入/输出功率 | 限时峰值输出 |
| --- | --- | --- | --- |
| GW5.1-BAT-D-G20 / G21 | 5.0 kWh | 各5.0 kW | 7.5 kW / 10s |
| GW8.3-BAT-D-G20 / G21 | 8.0 kWh | 各8.0 kW | 12 kW / 10s |
| GW6.0-BAT-D-G20 | 5.8 kWh | 各3.0 kW | 4.5 kW / 10s |
| GW9.0-BAT-D-G20 | 8.7 kWh | 各4.5 kW | 6.75 kW / 10s |

这些模块的最大/峰值功率均有 SOC 与温度降额脚注；G20/G21 加热配置与充电温度也不同，例如 GW5.1 的 G20 为 -18–55°C，G21 为 2–55°C。可扩 12 pcs 的同一表又限定单列堆装最多6个并联单元，不能只存一个“12”。电池侧工作电压是系统级（三相700–950V），不能把这种带变换结构的模块当作串联裸电池，按模块数量线性叠加电压。

### 必须形成的约束

1. 备电能力至少分为额定 kVA、离网最大 kVA、限时峰值 kVA/秒、并网旁路 kVA/A；当前 `backup_power_kw=5` 配 `unit=kVA` 的 fixture 需保留正确物理量，不能因字段名把它当5kW已认证的负载能力。
2. 夜间停电、PV=0 的持续与冲击负载必须同时通过逆变器和**实际模块/数量/连接**的供能约束。单块 GW5.1 的7.5kW/10s 不能独立支持10kW/10s；单块GW6.0的3kW最大输出也不能因逆变器额定5kW而自动成为5kW系统。
3. 负载超过5.5kVA的持续备电需求不能由10kVA/10s的峰值行放行；即使小于5.5，还需要相别、不平衡、功率因数、BMS/温度/SOC、预留能量等条件。原表最大值不是全天候保证值。
4. 没有实证的峰值所需最低 SOC、具体温度、可重复间隔及每相限制保持未知。本轮没有找到可直接写成完整峰值包络的厂家曲线，不能自造常数。

## 3. GW125/261-ESA-LCN-G10：电流、并机与控制范围

### 原表与版本

| 来源 | 原件、版本与定位 |
| --- | --- |
| S09 | [ESA261 EMEA 数据表](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_Datasheet_EMEA-EN_V1.1.pdf#page=2)，`20260716-EN-EMEA-V1.1`，PDF p2，精确 G10/G11 分列，已看 [整页](pages/goodwe-261-p2.png) |
| S10 | [ESA261 用户手册](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_User-Manual-EN_V1.6.pdf)，V1.6 / 2026-04-20；PDF p3 精确型号、p46/48/49 并机、p94 电池技术表 |
| S11 | [ESA261 并网手册](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_On-grid_User-Manual-EN_V1.0.pdf)，V1.0 / 2026-08-26；PDF p20、24–29、31，包含比通用手册更具体的拓扑与地区条件 |
| S12 | [ESA261 微网手册](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_Microgrid-User-Manual-EN_V1.1.pdf)，V1.1 / 2026-08-26；PDF p21、24–25、30、58 |

| S09 原字段 | 数值 | 所需语义 |
| --- | --- | --- |
| `Rack Nominal Energy` / `Rack Usable Energy` | 原表均为261.25 kWh | 当前 `usable_kwh=261.25` 有原表支持，不能仅因两者相等就断言抄错。另有DOD90–100%、推荐90%的独立运行条件 |
| `Nominal Voltage` / `Operating Voltage Range` | 832V / 676–936V | 电池侧 |
| `Max. Continuous Charge / Discharge Current` | 188A | 连续电流；S10 p94亦相同 |
| `Max. Charge / Discharge Current` | 198.5A | 最大值，原表未在此处给持续时间，不能替换188A连续值 |
| `Max. Charge / Discharge Rate` | 0.5P | 不应改写成任意SOC/温度都可持续的恒功率承诺 |
| `Nominal Output Power` | 125kW | 交流标称功率 |
| `Max. Output Power` | 137.5kW@400VAC；130.6kW@380VAC | 电网/输出电压条件不可丢失 |
| `Derating Temperature` | 45°C | 另有最高海拔4000m、2000m开始降额条件 |
| `Max. PCS Efficiency` / `Max. System Efficiency` | 98.6% / 92.0% | 两者不同，不得用PCS最大效率替代全系统效率或年度效率 |

并机不是一个无条件的整数：

| 场景与控制 | 原件明确范围 | 选型应如何使用 |
| --- | --- | --- |
| 主从，无外部EMS | S11 PDF p20（[整页](pages/goodwe-261-grid-p20.png)）：最多8台；不支持接PV逆变器；**仅中国支持** | 不能把“8台主从”复制给欧洲工商业 |
| SEC3000C，并网LAN菊链/混合 | S11 PDF p25/29：≤20台ESA261 | 需要保存控制器、通信与拓扑；不能只引用章节前一句“20台” |
| SEC3000C，并网LAN星形 | S11 PDF p25/29：≤15台ESA261 | p25监控平台列为跨行合并单元格，国内WE3.0、海外SEMS+不分别绑定20/15；不能误读成海外仅可星形 |
| 并网PV逆变器 | S11 PDF p25/29：RS485菊链≤40；p25备注特定表计/接口配置可到60，要求联系售后支持 | 常规40与特殊60需要不同条件；且具体兼容PV逆变器型号仍须确认 |
| 第三方EMS | S11 PDF p31：并机数由第三方EMS决定 | 缺EMS合同/协议/设备清单时是未知，不能沿用SEC3000C限值 |
| STS微网 | S12 PDF p24/58：接500K STS≤5柜、250K STS≤2柜 | STS型号、吞吐/电流、柜数、并网点等均须另核，不可只乘柜体125kW |
| 离网并机 | S12 PDF p58（[整页](pages/goodwe-261-micro-p58.png)）：最多10台ESA261 | 不等于任意一台STS可接10柜；不能把离网上限当所有模式上限 |

S11 PDF p25（[整页](pages/goodwe-261-grid-p25.png)）与p29（[整页](pages/goodwe-261-grid-p29.png)）是上述关键拓扑证据。p25右侧监控平台列的合并单元格已通过完整渲染及矢量边线复核（[布局证据](table-cell-layout.json)）；不按文字纵向位置把国内/海外强配至某个拓扑。S11 p27与S12 p24要求项目内储能型号/规格保持一致，混用不被推荐。S11 p20要求为限功率在PCC配置CT/电表，并给GM330或DTSD1352方案；p28–29明确SEC3000C、表计、CT、独立采购断路器等。S12 p21建议为STS与SEC3000C之间增加UPS；没有UPS不能实现远程黑启动。这里的“建议UPS”只在要求远程黑启动时成为功能必要条件，不应对所有询盘一概加购。

### 必须形成的约束

1. `188A continuous` 与 `198.5A maximum` 分开。当前 fixture 的198.5并非没有来源，但缺少连续值/时间性质，不能让计算器把它作为持续放电许可。
2. 柜体是带PCS的完整产品，其125kW/261.25kWh不能再配一个“同功率逆变器”并把输出相加。并机方案必须绑定控制器、通信、模式、地区/平台、保护计量和附件。
3. `parallel_limit` 应成为按场景、地区、控制器、拓扑等选择的条件表，不是SKU一个数字。欧洲多柜项目缺控制方案时只给候选及缺项，不能出“整套已放行”结论。
4. 数据表对可用能量已有标值，运行SOC预留、推荐DOD、老化、温度和交流损耗仍是独立因素。不能把 `usable_kwh × 柜数` 当作整个寿命/环境内的可交付交流能量保证。

## 4. SAJ H2-10K-T3 + BU2-5.0-HV1 + BC2-HV1

### 原件、版本和证据边界

- S13：[H2 10–30K 数据表](https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf#page=2)，PDF p2（与p1内容重复），精确H2-10K-T3列，已看 [整页](pages/saj-h2-p2.png)。可见页面没有修订号，PDF创建日期2025-06-03仅作元信息。
- S14：[H2 DE+EN 用户手册](https://de-linker.com/wp-content/uploads/2026/10/SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf)，PDF p37=英文印刷9–10，p43=英文印刷21–22。封面渲染可见V0.3（[整页](pages/saj-h2-cover-p1.png)），文字层另残留V1.1；不据此断言英文部分的确切修订号，按SHA固定本次原件。
- S15：[B2 5–25kWh HV1/HV5 数据表](https://de-linker.com/wp-content/uploads/2026/09/B2-5-25K-HV1HV5-datasheet-EN-BEU.pdf#page=2)，PDF p2，HV1与HV5分表，已看 [整页](pages/saj-b2-p2.png)。无可见修订号；创建日期2025-06-03仅作元信息。
- S16：[B2 用户手册](https://de-linker.com/wp-content/uploads/2026/10/B2-5.0-HV1-HV5-user-manual-EN-EU.pdf)，封面V1.2；PDF p5限定与H2成套使用，p10规格，p11控制器独立包装，p19–21串联及控制器接线。
- S17：[Configuration Instructions](https://de-linker.com/wp-content/uploads/2026/09/H2_HS2_HS3_AS2_AS3_Configuration_Instructions_V1.0_en.pdf#page=8)，V1.0，PDF p8 `Required devices` 表明确为 **H2 + BC2 + BU2**，已看 [整页](pages/saj-config-p8.png)。同表将HS2/AS2与HS3/AS3另列，不能借用其附件结构。

| 型号/字段 | 原表数值 | 约束意义 |
| --- | --- | --- |
| H2-10K-T3电池电压 | 180–800V | 与PV 180V启动值不同；需要独立电池侧约束 |
| H2电池端口 | S13 `No. of BAT=2`；S14 p43列BAT1+/BAT1−与BAT2+/BAT2− | 需要连接拓扑，不能只有总模块数量 |
| H2充/放电流 | S13写`50/50A`；S14 p37写`2*50A` | 数据表充/放表示与手册双端口表示粒度不同；不可擅自压成单个“总50A”，也不可在任意接线下保证100A |
| H2-10K-T3备电 | 最大输出10000VA；峰值15000VA/3s | 不能把15kVA当持续、或自动当15kW；仍由电池供能与负载决定 |
| BU2-5.0-HV1单模块 | 标称102.4V，范围89.6–115.2V；标称5.0/可用4.5kWh | 模块不是完整可直接连接H2的系统 |
| B2串栈电流 | 最大充30A / 放30A | 串联加电压，电流不乘模块数；BC2的100A是`Max. Fault Current`，绝不能作可持续工作电流 |
| BC2-HV1 | `Control Module`，控制器单独包装 | 必要附件；不增加储能kWh |

S15 的整栈表精确给出：

| 模块数/系统名 | 标称电压 | 运行电压 | 可用能量 | 原表 `Rated Power` |
| --- | --- | --- | --- | --- |
| 1 / B2-5.0-HV1 | 102.4V | 89.6–115.2V | 4.5kWh | 3072W |
| 2 / B2-10.0-HV1 | 204.8V | 179.2–230.4V | 9.0kWh | 6144W |
| 3 / B2-15.0-HV1 | 307.2V | 268.8–345.6V | 13.5kWh | 9216W |
| 4 / B2-20.0-HV1 | 409.6V | 358.4–460.8V | 18.0kWh | 12288W |
| 5 / B2-25.0-HV1 | 512V | 448–576V | 22.5kWh | 15360W |

S16 PDF p20（印刷33–34，[接线整页](pages/saj-b2-wiring-p20.png)）显示模块逐个串联，经控制单元接逆变器；p19还有通信链与终端插头要求。它给出了“一组受控串栈”的构成，不能把图中多个模块误读成并联电池箱。

### 必须形成的约束

1. 单块BU2+H2应拒绝：其最高115.2V仍低于H2下限180V。当前兼容合同已经给BU2最少2、最多5模块，方向与原表相符；不能只看兼容 verdict 或4.5kWh容量就放行单模块。
2. 两模块的电压范围下沿179.2V略低于180V。可确认其可工作范围有交集，但不能推导全SOC都可用。没有厂商具体H2+B2低SOC停机/可用能量曲线时，不把179.2V四舍五入为180V，也不自行禁止全部两模块配置。
3. 模块数量必须按每串分配；每串工作电流受30A限制，并同时满足所接H2端口的限制。不能用H2允许50A把B2允许30A抬高；两串如何分接两个端口、是否允许不同栈配置，本轮未获得完整专用图，不作已验证放行。
4. 每个构成B2受控串栈的必要BC2进入BOM。现合同 `1 / system` 足以描述单串示例；若未来一个系统有多个独立串栈，需要依据厂商接线明确控制器数量，现粒度不能证明仍只需1个。不在缺图情况下直接发布新的多串附件数量规则。
5. H2+BU2+BC2只是基础构成。S17 p8还按单机/AC耦合/并机给表计、CT和EMS条件：三相单机示例为1表计、3个外部CT（集成CT的80A表计有例外）；多逆变器并联需要1个EMS。它们不能被一条“电池兼容”结论涵盖，实际BOM要选定一种接线/计量方案并避免重复加入已随设备供给的附件。

## 5. 数据结构与回归案例应从原表派生

以下是研究推导的实现要求，不是厂商的原句，也不表示本轮已经实现。当前 fixture 的字段仅用于诊断。新模型应从 typed capability graph 定义：设备、储能模块、控制器和附件各有身份；端口属于设备；串联/并联/控制/供能关系连接节点；能力随工作模式、持续时间和运行条件变化；每个事实及约束连接版本化原文证据。物理关系决定合同，不继承现有字段白名单或原始字符串的结构。

| 必要维度 | 原件为什么要求它 |
| --- | --- |
| 精确型号、区域/修订、原件SHA、物理页与字段名 | G20/G21、G10/G11、H2/HS2不能按相似名称串用；同一托管名不等于永不更新 |
| 物理量与单位 | kWh不能证明kW；kVA需要负载条件；故障A不能当工作A |
| 额定、连续、最大、峰值及秒数 | ETA10kVA/10s、H2 15kVA/3s、ESA188A连续与198.5A最大 |
| 每端口/每串/每柜及连接拓扑 | ET100A×2，H2双端口，B2串联模块，BAT-C同型号柜并联 |
| 电压工作点、温度、SOC与保留量 | GW61.4电压低段、BAT-C最大C-rate时间、ETA电池功率降额 |
| 工作模式与供能来源 | 并网旁路、离网电池供电、PV辅助、备电切换不是同一个结果 |
| 控制器/软件/区域/平台/通信条件 | ESA主从China only、菊链20/星形15台、海外监控平台SEMS+、不同STS与离网限值 |
| 完整组件与附件关系 | H2需要BC2，ESA多柜需要确认控制计量与保护，备电有STS条件 |
| 结果状态 | 已核配对、满足特定需求、待确认三者分别输出；缺条件不能变成“完整系统已放行” |

应加入后续选型引擎的具体回归场景：

- GW80K + GW61.4，客户要求80kW电池独立持续输出：不能因配对released而通过；保存不能满功率的证据，并输出工作点/端口限制。
- GW5K-ETA-G20，要求6kVA持续离网：不能使用10kVA/10s行通过；43.5kVA并网旁路也不得参与此计算。
- GW5K-ETA-G20 + 一块GW6.0，PV=0，要求5kW持续：不能仅以逆变器5kW或电池5.8kWh通过；原模块最大输出为3kW。
- 欧洲ESA261主从8台：不能引用中国主从方案放行；缺控制/拓扑时标待确认。
- ESA261 + SEC3000C + 星形16台：超过该原表15台；不能静默换成另一种拓扑再宣称原输入已获放行。
- ESA261离网10台要求接单个250K STS：离网10台上限不能覆盖该STS≤2柜限制。
- H2 + 一块BU2 + BC2：电池最高电压低于H2下限，应拒绝。
- H2 + 两块BU2：记录串栈和BC2，并明确180V下限；不能无证据承诺全部9kWh在任何运行状态都可交付。
- H2 + 多个串栈：若只有总模块数和每system一枚BC2而无接线方案，完整BOM与端口/控制器校验未完成；不授予整套放行。

## 6. 未核实项目与本轮结论的边界

已核的是本地托管原件内的型号列、字段、条件和可复核推导，置信度高；它们仍不能替代设备现场运行、设计图与厂商专项确认。尚缺：完整SOC/温度功率曲线及峰值恢复条件；GW61.4配ET80备电的专项放行；所选控制器/平台组合的实际固件适用与部署证明；各方案完整保护选型和实际供货包含项；SAJ多串多端口的专用接线与控制器数量；每个项目的欧洲国家并网证书、接地与中性线安排。

本轮没有将这些缺口解释成“不可能实现”，也没有用文案调整代替约束修复。正确顺序是：先使上述证据成为有类型、有条件、有作用域的设备合同，再让候选系统同时满足功率、能量、电压、端口、控制与附件；未能满足或无法核实的条件在结果中保留。原型和视觉表达应消费这个已明确的结果状态。

## 7. 仓库证据定位与复核

本报告比对基于本分支业务基线 `123aea57`，未更改以下文件：

- [`services/engine/tests/fixtures/feed.json`](../../../../services/engine/tests/fixtures/feed.json)：GW80K位于2755行、GW61.4位于3601行、BU2位于7432行、BC2位于7603行、H2-10K-T3位于13735行、ESA261位于14765行、GW5K-ETA位于17457行（均为本次读取的型号行）。
- [`plugins/linker-commerce/data/compatibility.json`](../../../../plugins/linker-commerce/data/compatibility.json)：ET80+BAT-C及61.4附加条件约2934行；H2+B2/BU2/BC2的放行、附件与2–5模块条件约5125–5259行。这些是当前实现事实，其正确性以本报告原件逐项核验为限。

manifest 中保存了源文件和提取文本的SHA。复核时先对原件重算SHA，再按所记物理PDF页读取；不要用PDF创建时间冒充修订日期，也不要只依赖文字层。例如S14文字层的版本与可见渲染并不完全一致。
