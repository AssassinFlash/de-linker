# 带条件设备 compiler：真实事实入口核实

2026-10-23（北京时间）。这是下一步设备能力编译的输入研究；没有修改商品、运行 feed、兼容合同、业务代码或设置，没有提交或部署。住宅/工商业、全 SKU 与全欧洲的总目标不变；下列代表案例用于建立可以泛化的事实合同，不能当作其余型号已通过。

**结论：原厂原件与相当一部分已录入事实真实存在，当前主要障碍是引用、条件和物理边界没有完整穿过投影。** 不能直接把现有顶层数字或 `released` 转成新 Kernel 的设备放行。也不能把“feed 没给”解释为厂商“不支持”。

## 1. 本次真正读取的状态

- 实例：p548，`GET http://127.0.0.1:9347/wp-json/linker/v1/engineering-feed` 实际 HTTP 200；保留的代表数据采集于 `2026-10-22T17:39:43Z`。该次 feed 为 106 个已发布产品，`schema_version=1`，兼容版本 `5d2a85676432d1501620997a21359782defcd8aa64b644c7799eb32d054a23b8`。这不是全站产品/语言总数，也不是本轮重新读取生产站的结果。
- 使用 `just wp p548 eval` **只读** 9 件产品的 `_tv_b2b_figures` 与 `_linker_documents`；没有读取账号、价格、库存数量、密钥或通知队列。
- p548 实际加载的 `EngineeringFeed.php`、`SelectionFacts.php` 解析到当前工作树；字节与本次读到的源码一致，SHA 分别为 `320ac163dac1d84531761fc9dcc6dcffd746268368d2f35c6048fd88a70bd78e`、`87069e6c785425fc37a01f003f96bb1b5bf4f2220b6ab587718bfcefabfbdd75`。收尾时工作树 HEAD 为 `d5f2c0dfb094cd02770b696e9f91d50288a728cb`；父线可能继续实施，本文按证据文件固定所读状态。
- p548 托管的既有 17 份 PDF **逐份重新计算 SHA，全部匹配** [hardware-study 固定研究](https://github.com/AssassinFlash/de-linker/blob/74aa66b921dfad70af92fe909663dfcf62978f92/docs/research/2026-10-22-roof-experience/hardware-study/README.md)。原表条件继承该研究已核的型号列、物理页与整页图；本轮读取相关文本，并额外直接提取了当前 feed 所引 AU B2 数据表 p2。未重新做现场测试、欧洲证书验证或厂商最新版本搜索。
- 全部材料来自本机已授权快照和第一方应用源码，本次没有新外网抓取；无需重复 Apify 已完成的原件获取。

取证文件均仅含公开产品数据：

| 文件 | 内容与界限 |
| --- | --- |
| [p548-public-cases.json](p548-public-cases.json) | 当次实际响应的 9 件代表产品、精确匹配的 8 条配对与 2 条要求；记录整个响应的 hash/字节数/生成时间。未把 tests fixture 当运行事实 |
| [p548-source-meta.json](p548-source-meta.json) | 对应 9 件产品的真实 Woo 图值与文档原记录，保留 `citation.doc`、`qualifier`、`evidence_refs` |
| [p548-document-manifest.json](p548-document-manifest.json) | 原 17 份 PDF 的 p548 路径、托管 URL、完整 SHA、页码与前次相同结果，另列本轮实际读取的 AU 表 S18 |
| [case-facts.json](case-facts.json) | 29 项有边界、条件、物理页和完整原件 SHA 的研究事实；`proposed_typed_field` 是建议合同名，**不是已经新增的生产字段**；每项明确 `equipment_release=not_established_by_this_fact` |

## 2. 已复现的真实数据链缺口

数据链为 Woo 原图值 → `SelectionFacts` 顶层选品数字，同时经另一条路径 → `EngineeringFeed::figures` 引用过滤 → Python `Product` 字符串解释。它们的证据要求不同。

| 实际产品 | Woo 图值数 | 实际 feed 图值数 | 典型结果 |
| --- | ---: | ---: | --- |
| 4107 H2-10K-T3 | 39 | 10 | 电池电压/PV/MPPT 在；电池电流、温度、效率、备电额定/峰值不在 |
| 2090 BU2-5.0-HV1 | 18 | 4 | 容量、模块数在；模块电压、30A、充放温度不在 |
| 2092 BC2-HV1 | 11 | 3 | 多个串数对应的电压以一条拼接字符串出现；不是已建好的拓扑模型 |
| 1946 GW80K-ET-G10 | 31 | 10 | PV/MPPT/电池电压在；双端口连续电流、充放功率、备电条件不在 |
| 1954 GW61.4-BAT-AC-G10 | 27 | 5 | 顶层仍有 61.4/60kWh；对应整柜容量引用和条件未随该数字输出 |
| 6321 GW125/261-ESA-LCN-G10 | 15 | 0 | 顶层仍有 125kW、261.25/261.25kWh；所有带 `doc` 的原图值均被过滤 |

这不是“原厂没有提供这些值”。直接原因与精确代码定位：

1. [`EngineeringFeed.php`](../../../plugins/linker-commerce/includes/Products/EngineeringFeed.php) `figures()` **132–153 行**，调用 `is_hosted_citation()` **167–171 行**，后者依赖 `citation_url()` **178–183 行**。只有 `citation.url` 合法才输出；实际原数据大量仍是 `{doc, page}`。例如 ESA261 全部 15 项是该形状，故得到 `{}`。本次没有把它解释成应该放宽任意外链；正确修复应先将精确原件解析到本站托管且 hash 固定的来源。
2. 同文件 **146–150 行**仅输出 `value/unit/citation`。即使补全 URL，原记录的 `qualifier`、来源条件、区域、端口和时限仍不会自然贯通。`services/engine/schemas/feed.schema.json` 的 `figure`/`citation` 也没有这些字段，且 `additionalProperties=false`；不能只改一条 PHP 输出而绕过合同。
3. [`SelectionFacts.php`](../../../plugins/linker-commerce/includes/Products/SelectionFacts.php) `for_product()` **118–145 行**从全部原图值计算数字；`ac_power()` **277–290 行**、`energy()` **314–327 行**及 `entry()` **349–362 行**只读取值和单位，不要求来源 URL、hash 或条件。于是“有顶层数字、无该数字的可消费证据”可以同时发生。它适合现有筛选合同的用途，不能自动升级为工程能力事实。
4. [`products.py`](../../../services/engine/src/linker_engine/products.py) `from_feed()` **102–120 行**直接接收顶层数字；没有反向关联到产生该值的具体 Figure。新设备 compiler 必须能携带推导路径与来源闭包，而非用类型合法代替设备证据成立。

实际例子：GW61.4 原 `system_usable_energy_kwh=60` 带 qualifier，明确寿命初期、100% DOD、0.2C、25±2°C，且实际可用量随系统配置变化。其 `citation` 为 doc-only，整条图值未进 feed，但顶层 `usable_kwh=60` 仍在。[原厂 S03 p2](https://de-linker.com/wp-content/uploads/2026/07/delinker-goodwe_batc60-datasheet.pdf#page=2)支持这个**带条件的** 60；没有支持不带边界的保证交流输出 60。

## 3. 住宅代表：H2-10K-T3 + BU2-5.0-HV1 + BC2-HV1

实际商品为 4107 / 2090 / 2092。B2-5/10/15 套装 1832 / 2067 / 2068 同时保留作模块与整套计量基准对照。来源 S13–S17 的每份完整 SHA 和 p548 原件路径见 manifest；下表各事实也已逐项写入 `case-facts.json` R01–R14。

| 建议可消费语义 | 原表值、单位与来源 | 当前实际链路 / 事实状态 |
| --- | --- | --- |
| BU2 单模块名义/可用能量 | 5.0 / 4.5kWh，[S15 p2](https://de-linker.com/wp-content/uploads/2026/09/B2-5-25K-HV1HV5-datasheet-EN-BEU.pdf#page=2) | 2090 图值与顶层都在；**已核 BEU 表述**。不得重复扣同一 90% DOD，不是交流交付承诺 |
| 串栈模块数与部件组成 | 一栈 1–5 个 BU2，控制器 BC2；[S15 p2](https://de-linker.com/wp-content/uploads/2026/09/B2-5-25K-HV1HV5-datasheet-EN-BEU.pdf#page=2)、[S17 p8](https://de-linker.com/wp-content/uploads/2026/09/H2_HS2_HS3_AS2_AS3_Configuration_Instructions_V1.0_en.pdf#page=8) | 基本 1–5 在 feed；H2 配对实际另有 2–5 与 BC2 每 system 1 的合同。**单栈可建条件候选**，多栈/双端口控制器数仍需接线合同，不能套用默认 1 |
| 串数条件下电压 | n=1…5：标称 102.4/204.8/307.2/409.6/512V；范围分别 89.6–115.2 / 179.2–230.4 / 268.8–345.6 / 358.4–460.8 / 448–576V；S15 p2 | 原件已核；BU2 原 meta 电压被过滤；BC2 feed 是整条列表字符串。需要 lookup 和 n，不能取第一范围代表整个系统 |
| 栈 DC 电流与功率 | 最大充/放各 30A；额定 3072W×n；S15 p2 | 原 meta 的 B2 电流/额定功率是 doc-only，feed 缺。**额定与最大按原词保留**；串联不乘电流，且这些不是 AC 放电功率 |
| H2 电池端口 | 电压 180–800V；No. of BAT=2；S13 p2。S14 p37 写 `2*50A`，p43 标 BAT1/BAT2；S13 充放行写 `50/50A` | 电压在；端口/电流缺。须保留资料粒度，先建立实际接法，不断言总 50A 或任意接法有 100A |
| H2 AC 与备电 | 并网额定 10kW；备电最大 10kVA，峰值 15kVA/3s；[S13 p2](https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf#page=2) | 并网额定已贯通；备电在 doc-only 原 meta，字段名 `backup_power_kw` 实际 unit=VA。必须保持量纲、时限与负载 PF/相别，不得变成 15kW 持续能力 |
| 温度与效率 | BU2 充电 0–50°C、放电 −10–50°C；H2 −40–60°C、45°C 起降额；H2 最大效率 98%、欧洲效率 97.6%；S15/S13 p2 | 原件已核、raw 可见，feed 缺；不是完整温度/SOC曲线，也不等于充放双向效率各 .98 |

可消费的**正向案例**是三模块单栈：5×3=15kWh 名义、4.5×3=13.5kWh BEU 可用；原表 268.8–345.6V 全部落在 H2 的 180–800V 运行窗内。可据此给出“所查电压窗口符合”和完整部件候选，不能据此直接给出任意 SOC/温度下电池独供 10kW 保证；30A、DC/AC 转换、共享 AC 输出、设备/BMS 状态仍需约束。

反向/未完成边界也必须保留：一模块最高 115.2V 仍低于 H2 最低 180V，所查窗口不相交；两模块最低 179.2V 低于 180V，但大部分窗口重叠。没有 V–SOC 曲线，不能把相差 0.8V 换算成准确丢失 kWh，更不能把两模块整个 9kWh 当作已保证可交付。

**本次新增地域版本证据：** B2 套装名义容量和模块数的当前 URL 引用的是 AU 表 S18，页脚 V1.1-20250609，SHA `99c1d10fae6486e314e4aa6a3767b664aa5637ce88eb2bfddbf8e11cbb85367b`。其 p2 可用能量为 **4.8/9.6/14.4/19.2/24kWh**；BEU 表为 **4.5/9/13.5/18/22.5kWh**，当前 usable 字段引用后者。BEU 4.5 不是无来源错误；需要确定实际欧洲 SKU/文档变体，禁止把两表条件拼成一套“已核能力”，本研究未改任何数值。

## 4. 工商业代表：GW125/261-ESA-LCN-G10

实际商品 6321 是**含 PCS 的整体柜**，不是需要再与同功率逆变器相加的裸电池。当前顶层 125kW、261.25/261.25kWh 在，15 项原图值全部因 doc-only 被过滤。下列事实见 `case-facts.json` C01–C11。

| 建议可消费语义 | 原厂事实 | 当前缺口与使用边界 |
| --- | --- | --- |
| 整柜功率/能量 | [S09 p2](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_Datasheet_EMEA-EN_V1.1.pdf#page=2)：AC 标称 125kW；Rack Nominal/Usable 均 261.25kWh | 原件明确相等，不以经验判抄错；需把来源、计量边界和运行 SOC 窗分别带入，不能重复扣相同 DOD |
| DC 电流与电压 | 188A **maximum continuous**；198.5A **maximum**；832V 标称、676–936V；S09 p2，连续值另见 S10 p94 | raw 只有最大 198.5，feed 都缺；最大值没有在此给时限，不能冒充持续值。无完整 V–SOC/温度/BMS 曲线 |
| AC 条件最大值 | 137.5kW@400VAC；130.6kW@380VAC，on/off-grid 行分别列；S09 p2 | raw/feed 缺；必须保留电压、模式、视在与有功差别，不能用一个 maxPower 覆盖 |
| 效率 | Max PCS 98.6%；Max System 92.0%；S09 p2 | raw 仅 98.6 且 unit=`% (PCS)`，feed 缺；不能将 PCS 最大值当全年效率，也没有依据把 System 最大效率自动定义为 RTE 或取平方根生成双向效率 |
| 环境与运行建议 | −25–55°C；45°C 降额；2000m 起海拔降额、4000m 最高；DOD 90–100%、推荐90%；S09 p2 | raw 只有温度范围；其他缺。推荐值不是不可更改的硬阈值，能力曲线与设置须另冻结 |
| 并网多柜 | [S11 p25/29](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_On-grid_User-Manual-EN_V1.0.pdf#page=25)：SEC3000C、LAN 菊链/混合≤20，星形≤15 | 不是一个 SKU 的无条件 parallel_max。监控平台列为合并单元格，不把海外错误绑定为“仅星形” |
| 特定无外部 EMS 主从 | S11 p20：≤8、不能接 PV 逆变器、**仅中国支持** | 不可复制为欧洲方案，也不代表别的欧洲拓扑禁止；第三方 EMS 的数量须其合同，不能借 SEC3000C 上限 |
| 离网与 STS | [S12 p24/58](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_Microgrid-User-Manual-EN_V1.1.pdf#page=24)：离网 ESA≤10；500K STS≤5柜；250K STS≤2柜 | 这些约束须同时成立；不能给一台 STS 接10柜并直接乘125kW |
| 远程黑启动 | S12 p21：STS 与 SEC3000C 间建议 UPS；无 UPS 不能实现本拓扑的远程黑启动 | 按**用户要求的功能**与具体拓扑绑定必要附件，不能给所有方案默认 UPS，也不把未知的其他启动模式默认 false |

整体柜内部辅耗、待机损耗、转换路径的方向效率、状态曲线、峰值持续/恢复条件与实际控制器固件仍未足以从该数据表生成完整真实设备时序模型。可以保留可验证的限制/条件与具名场景假设；不能把当前固定窗口 Kernel 的显式场景参数填成 0 辅耗和通用效率后改名为“该 SKU 已验证”。

## 5. 交叉电气边界：ET80 + GW61.4 不等于 80kW 电池系统

这是对 compiler 必须支持分端口和应用条件的补充代表链，实际商品 1946 / 1954，事实 X01–X04：

- [S01 p2](https://de-linker.com/wp-content/uploads/2026/09/GW_ET-75-100kW_Datasheet-EN-20260708-V2.1.pdf#page=2)：ET 电池端口 2、各连续充/放 100A、最大充/放88kW；电池口 300–800V、启动300V。这不是 PV 口200V启动值。
- [S03 p2](https://de-linker.com/wp-content/uploads/2026/07/delinker-goodwe_batc60-datasheet.pdf#page=2)：GW61.4 的最大充/放55.2/67.5kW、180/220A，电压275.52–346.56V，SOC/温度影响电流、功率及最大 C-rate 的持续时间；RTE96%仅在100%DOD、.2C、25±2°C测试点。不能从 RTE 唯一解出两个方向效率。
- 实际 feed 的配对合同确有 `released`，以及“不能达到逆变器满功率”的文字条件；[S05 p6](https://de-linker.com/wp-content/uploads/2026/09/GW_Battery-Compatibility-Overview_EMEA-EN_20260910.pdf#page=6)有该说明。文字并未变成当前可执行的端口/功率守卫。
- 在资料允许且实际双端口分配成立的前提下，`346.56V × (100+100)A /1000=69.312kW` 只是**不计转换损失的 DC 上包络**。它不证明实际可持续交付此值，不能将它用作新保守推荐功率。实际还受柜/BMS、接法、状态与共享 AC 口限制。
- [S02 并网清单 p12](https://de-linker.com/wp-content/uploads/2026/09/GW_ET-50-100kW_User-Manual-EN_V1.3.pdf#page=12)列61.4；on/off-grid 清单p17只列92.1/102.4/112.6。当前证据不足以将总体 compatible 升级为61.4的备电应用放行；缺列不等于已证明禁止。

## 6. 字符串解析结果与默认值的信任边界

下列结论来自实际 p548 代表 feed 经当前 `Product.from_feed()` 的只读解释；不是自造 fixtures，也没有执行候选选型或修改默认值。

| 当前实现位置 | 实际行为 | 新 compiler 必须改用的事实合同 |
| --- | --- | --- |
| `products.py:164–169 modules_per_stack` | low 缺失/为0时 `low or 1`；这不是厂商最小模块数证据 | min/max 都必须有来源，缺一项保留 unknown；0与缺失也应分开 |
| `stacking.py:31`、`:48` | 允许 `(1,1)`、`stacks_parallel_max or 1` | 单柜是明确选择/拓扑，不能把“未知可并数量”变成“厂家最多1”；也不推断多柜被禁止 |
| `products.py:182–183` + `units.number_range()` | 对 BC2 当前列表只返回 `(89.6,115.2)` | 电压列表按串数的条件表，保留所有分支；控制器不凭这条字符串生成储能容量 |
| `units.number()`、`kilo()` | `55.2 / 67.5` 只取55.2；80kVA在通用 kilo 函数得到80 | 方向与量纲必须先识别；分别 typed charge/discharge、active/apparent。此处不宣称原引擎已用该字符串算错了真实设备功率 |
| `units.per_input()` | H2当前40按3个MPPT重复为40/40/40，与本次 S13 原表相符；ET42×8也相符 | 此两例可用，但广播依据要绑定原表；不能把所有 `a/b` 当同一类端口列表 |
| B2套装与BU2模块共用 `module_energy_*` 名称 | 2067 B2-10 的该字段是整套10/9kWh、模块数固定2；2090 BU2是单块5/4.5、可组合1–5 | 需明确采购单位、内含模块BOM、能量基准和拓扑基数。这里未发现旧 `stacking` 把B2整套再乘模块数：其现有代码区分固定整套与可叠模块；新模型应保留事实而不依赖此命名推断 |

## 7. 可直接实施的事实合同与成熟模式映射

以下是本次事实取证导出的实施建议，不是设备方法已经验证的声明。已有 [NUMERICAL-MODELS §5–8](../2026-10-22-planning-implementation/NUMERICAL-MODELS.md)及其继承的 [SAM 物理输入](https://samrepo.nlr.gov/help/battery_storage_btm.html)、[SAM 停电](https://samrepo.nlr.gov/help/grid_outage.html)、[SMA multiuse](https://manuals.sma.de/SDesign/en-US/14444632075.html) 已区分物理参数、状态与控制，本轮没有重新抓取或扩大其验证范围。

| 成熟模式 / 本次原厂资料的结构 | 对本站的具体映射 | 当前实际 gap |
| --- | --- | --- |
| 名义/可用容量与运行窗口分别记录 | `quantity_basis=single_module/assembled_set/cabinet`；容量→可用窗转换只做一次；运行 reserve 另存 | 顶层量无推导来源，模块字段承载整套值，区域版本未绑定 |
| 实际端口、转换方向与限时能力 | `boundary/port_id/direction/limit_kind/duration_s`；DC电池与PV、AC并网/备电分别约束；共享AC预算单独施加 | 原字符串和通用 `power`/`backup_power_kw` 不具备这些语义 |
| 厂商条件配置表 | `application + mode + topology + region + controller + firmware + required_components` 的条件集合；候选由实际项目条件匹配 | 当前配对 regex + released +自然语言条件没有足够机器守卫；controller数量/并机限制并非统一整数 |
| 输入与证据版本冻结 | 每条事实连 `product_id/SKU/model/variant → raw_meta_sha → typed_fact → source_document_sha/page/locator`，保留转换/推导与不确定性 | feed只有URL/page，文件可替换，topscalar无法反查具体原字段，条件/qualifier丢失 |
| 不知道与不适用分别返回 | `verified_statement / conditional / conflicting_variant / unresolved_source / unverified / not_applicable`；约束判断独立为 satisfied/violated/unresolved | 不能把缺来源、没有性能曲线、未检查模式分别自动变成0、false或released |

最低可实施顺序：

1. **先修真实引用解析和条件保留。** 本次已匹配 SHA 的托管原件可形成明确源绑定；doc alias 只能经过已核型号/版本/页绑定转为托管 URL/hash，不能靠模糊文件名批量猜。保留 qualifier、区域、原值及未解决状态，不改成全字段默认可信。
2. **用上述两个主案例生成 typed facts 与条件候选。** 住宅先限定有证据的单栈三模块；ESA先选择具名模式/控制器/拓扑。这样能真实测试约束，不将代表案例当未来产品范围边界。
3. **能力 compiler 只编译有证据的条件。** 区分参数缺失和约束违反；例如缺双向效率、辅耗或状态曲线时可说明场景模型假设，但不得发布“实际SKU全年通过”。电气不相交、计数超过所选拓扑上限等则给明确违反及原件定位。
4. **由所有 SKU 的真实来源清单继续泛化。** 本轮9件不是全SKU验收。欧洲国家包、固件/地区适用、保护/接地/中性线、电气接线与实际控制均继续在全目标，不能因为当前研究未验证而删掉功能承诺。

## 8. 现有 fixture 覆盖与下一批真实验收

本轮只读调查测试源码，没有修改或重跑 PHP 测试。现有覆盖的实际含义如下：

- [`EngineeringFeedTest.php:90–157`](../../../plugins/linker-commerce/tests/php/Unit/Products/EngineeringFeedTest.php) 是 WP_Mock：明确测试顶层未引用10kW仍存在、该未引用 Figure 不输出、托管 URL 的 MPPT 值输出；这验证了**当前合同**，没有证明当前原 meta 的 doc-only 引用已解析。`:166`测本地 URL→规范域，`:271`测空图值 `{}`，`:298`测兼容合同同行。未见 qualifier/区域变体/原件hash/连续与最大语义贯通断言。
- [`SelectionFactsLiveProductsTest.php:187–190`](../../../plugins/linker-commerce/tests/php/Unit/Products/SelectionFactsLiveProductsTest.php) 的“live”来自 `tests/fixtures/live-products-2026-10-09.json` + 预期 CSV，经 mock 读取；6321的125/261.25行也只是该既有夹具，不是今天对p548源到feed的验收。
- Python `services/engine/tests/fixtures/feed.json` 比本次实际 feed 丰富：ET80 **31 vs10**、GW61.4 **27 vs5**、BU2 **18 vs4**、H2 **38 vs10**、ESA261 **15 vs0**。fixture有电流/效率/容量引用，实际投影缺；两者都没有完整 qualifier 合同。测试能证明解释已有 Figure 的行为，不能证明真实 WordPress 已提供它。
- 当前 PHP 测试树未见独立 EngineeringFeed REST 集成测试文件；其他 route/产品搜索测试可能请求 feed，本文不把它们等同原件→能力事实的逐字段验收。

下一批应在只读真实夹具与可控写入实例中逐项证明：

1. p548三条代表链的原件hash、型号列/物理页、raw字段、typed单位与条件、最终feed/冻结能力快照一一相同；故意缺引用/更换原件/地域冲突均给明确状态。
2. 三BU2 + BC2的采购单位/能量/电压与电流分别正确；单模块明确电压不满足；两模块不臆测低压对应能量；多栈未给接线时保持未决；BC2的100A故障电流永不成为工作电流。
3. ESA188A与198.5A不可互换；380/400V输出条件、20/15并网拓扑、10离网及5/2 STS限值同时可查询与执行；中国专用主从不能授予欧洲放行；要求远程黑启动时检查UPS证据。
4. ET80+61.4总体配对成立但不能授予80kW电池供电；备电专项证据不足须独立未决。可用60kWh测试条件及96%RTE条件不因投影丢失。
5. 修改/补充商品事实后，旧 revision/run 保留旧源与能力hash；unknown不默认为false；设备数据完整、数值可执行、项目模式符合、国家规则通过分别记录，不以一次计算任务成功代替工程放行。

上述是应同步补足的实际数据与验证合同，不是本研究已经完成产品修复或全SKU放行的声明。

### Joint-AC charging evidence readback — 2026-10-26

The current Woo H2 records already have the named BAT1/BAT2 port count and
per-port current evidence; no duplicate port-count maintenance is needed.
A local source-bound H2/B2/BMS preparation succeeds when BAT1 is selected.
The current source does not bind the AC reverse charging capability/power
needed by the separate-AC plant equivalent. AC inlet current/apparent input
cannot be relabelled as battery charging active power.

Apify search run `TTMcVNi3bmPtxOtPC` / dataset `mGiPcDKLP0PfYYysv` found the
manufacturer [H2/HS2/HS3/AS2/AS3 configuration instructions](https://www.saj-electric.com/hubfs/Guides%20and%20Manuals/HS3/H2_HS2_HS3_AS2_AS3_Configuration_Instructions_V1.0_en.pdf).
Crawler run `5WyJiPc1kdbrZWijj` / dataset `b1GvzMkq5nKGCtLem` retrieved the
200 PDF binary; its HTML/text extraction failed, so the saved Apify binary was
parsed locally with pdftotext. The 91-page document describes AC-coupled
three-phase arrangements and configurable battery charging operation
(printed pages20,42,57). This supports the technology direction, but does not
supply a model-specific H2-10K-T3 AC battery charge power rating. Manuals for
LS2/LT2/Africa models returned by the search are not transferred to the EU T3.
No new product facts or runtime source pack were invented from these searches;
verified future maintenance must go through the native Woo product record.
