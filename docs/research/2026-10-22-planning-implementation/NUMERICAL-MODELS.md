# 新规划Kernel的数值模型与验证合同

2026-10-22，Codex后台方法核实。服务于已选定的统一Journal工作台实施；本文不修改产品代码、不安装依赖、不提交代码、不部署。既有17条独立参考运行和4项官方物理模块检查直接继承，未重复执行。新外部读取全部经Apify。

**可直接开始实现的共同核心是：明确时间与计量边界的PV/负荷序列、逐设备连续储能状态、共享库存的任务约束、来源账本，以及与求解器独立的结果复核。** 住宅/商业使用同一物理核心，模板只提供输入便利和目标，不持有第二套年量选型公式。数据和方法缺口是有类型结果，不能变成false、0损失或已放行。

## 1. 固定方法身份与纯计算边界

实施基线`origin/main=3bb95556`；`services/engine/uv.lock`已锁pvlib **0.16.1**。所有新增pvlib API原文均显示0.16.1，见§11。不能仅以pyproject的`pvlib>=0.13`作为可复算模型版本。

```text
normalize(raw_assets, explicit_import_contract) -> NormalizedInputs | InputInvalid
build_pv(normalized_weather, array_geometry, topology, pv_model_spec) -> ArrayPowerSeries
replay(series, device_configuration, policy, task_scenarios) -> SimulationWitness
verify(inputs, witness) -> CheckResults
compare(verified_candidates, declared_goals) -> CandidateComparison
```

以上函数不读网络、Woo、当前时钟、可变文件或浏览器状态。获取PVGIS/气候/设备事实属于适配层；Kernel只消费已固定字节及展开后的参数。每次run固定资产hash、有效默认参数、实际库/模型版本、PVGIS版本/库/年份和请求、拓扑/能力包、policy、TaskSpec、初末状态、数值容差和求解设置。没有对应旧版本字节时返回`VersionUnavailable`，不能读最新数据补算旧run。

结果至少区分：`execution_state`、`model_feasibility`、`hardware_and_evidence_state`、`applicability`。`calculated + ideal_schedule_feasible + backup_evidence_missing`是有效结果，不能转换成该SKU备电已验证。下面的公式编号只是本文定位，不是外部标准编号。

## 2. 必要领域输入：先把量纲与来源建实

| 输入 | 必需字段/单位/边界 | 缺少时的行为 |
| --- | --- | --- |
| TimeAxis | 每段UTC start/end、duration_h；原始时区/IANA区域、时间戳起点/末点/瞬时/区间平均语义、缺测和变换记录 | 无法判断DST或采样语义时`InputInvalid`，不得按条数猜15分钟 |
| LoadSeries | 总AC负荷kW区间平均或区间kWh；计量点、总负荷/净购电/已有PV后净值、原始列和单位 | 净购电不能直接当总负荷再扣PV；负值可能是净外送，不能静默归零 |
| WeatherSeries | UTC、辐照W/m²、temp_air°C、wind_speed m/s及测量高度、数据源/年/采样语义、地平线和标记 | 只有月/年总量不生成虚构小时过程；来源中断返回`SourceUnavailable` |
| ArrayGeometry | 不变组件ID、实际片数、STC W/片、安装倾角/真北顺时针方位、对应屋面和遮挡模型 | `kWp=N×P_STC_W/1000`；组件数不得为组串凑整而增加，坡度与安装倾角分开 |
| Topology/Capabilities | PV/DC/AC/负荷/电网端口图；每输入/MPPT/相、转换器、柜/串栈、附件、模式；有来源的状态条件能力 | `unknown`保留；不能用逆变器PV铭牌代替电池输出或用一个released放行所有模式 |
| BatteryState | 内部可用窗口电量kWh、容量表示/基准、初始来源份额、温度/退化条件；或详细物理模型的Q/V/SOC状态 | 初态须声明，不能午夜或任务边界重置；名义/可用容量不得重复扣DOD |
| Policy/TaskSpec | policy_id/version、可充来源、reserve、预测角色、控制周期、目标优先级、停电/削峰计量窗、终态要求 | 无目标不称最佳；无真实控制证据不称厂商EMS可执行 |

各数值既有单位也有语义。例如`module_stc_w`、`inverter_pvwatts_dc_limit_w`、`continuous_battery_ac_discharge_kw`分别存在；不使用一个无边界的`power`。SOC输入统一小数或百分数之一并验证，不能靠数值大小猜。W→kW、Wh→kWh仅在适配边界转换一次。

## 3. 时间、CSV与重采样的可编码规则

对区间平均功率，`e_t[kWh]=p_t[kW]×Δt[h]`；对区间能量，`p_t=e_t/Δt`。CSV导入合同显式选择timestamp列、value列、分隔符、小数点/逗号、单位、间隔和时间区。没有时间列的序列须用户确认start/interval/timezone和周期；不取“最后一个数字列”。SMA明确允许完整年或整周和多种间隔/单位，整周外推本身可用，但必须保存外推规则和源周。[SMA负荷原文](https://manuals.sma.de/SDesign/en-US/14318222475.html)。

- 转UTC后时间严格有序、不重复；end>start。DST回拨的同名本地时刻必须有offset/fold，不能去重丢一小时；缺失时刻按显式策略处理。不以固定8760/35040条证明正确，闰年和时区分别校验。
- 当原始值是区间平均时，重采样用区间交叠：目标区间能量`E_j=Σ_i p_i×overlap_hours(i,j)`，目标平均`P_j=E_j/duration_j`。不覆盖的时段标缺测，不能默认0。细化成四段可保持能量，却没有新增测量精度。
- 瞬时采样必须先采用具名的重建方法，才能积分；线性/保持/天气模型重建记录为模型假设。不得把SARAH瞬时卫星值伪装成小时平均。
- 所有PV、负荷、能力变化和任务切换映射到同一时间轴。必要时用全部边界的并集细分；SOC始终沿真实持续时间推进。报告保留原始分辨率和变换后的分辨率两项。
- 年能量可由完整时序积分；如果只有年用电，允许在客户确认的归一化profile下作场景估计，必须记录profile来源及`Σweights×Δt`归一值。年耗不能唯一决定15分钟峰值、储能任务或自给率。

**独立小例：** 4kW的半小时区间为2kWh；细分两个15分钟区间仍是4kW、各1kWh。1kWh/15min转换为4kW。UTC23:45–00:15跨午夜仍累计0.5h，不创建新日初态。以上是单位/区间定义的解析预期，不依赖业务实现。

## 4. PV两条具名模型路线及精确边界

### 4.1 PVGIS modeled system output：可声明假设的场景估计

pvlib0.16.1的`get_pvgis_hourly`和`get_pvgis_tmy`均返回`(data, metadata)`；0.13前的三/四返回值不能沿用。Hourly API用`pvcalculation=True`时peakpower单位为kW，`P`输出单位W；必须显式记录loss百分数、mountingplace、技术、实际倾角/方位、版本URL、辐射库及start/end，不接受API默认的全部可用年份或自动最优角偷偷替换实际布局。[Hourly API](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_pvgis_hourly.html)。

| 处理 | 必须执行的合同 |
| --- | --- |
| 方位 | Kernel用真北0°、东90°、南180°、西270°；pvlib当前输入相同。直接PVGIS REST的aspect为南0°、东-90°、西90°，转换`aspect=azimuth_north_clockwise−180`。返回metadata仍可能用PVGIS约定，不能再当北0°读取 |
| 姿态 | 每个实际阵列/姿态对应自身数量及kWp；不把东西向共用一个南向年量。共享逆变器/出口限制在共同端口处处理，不能把多坡各自满额AC输出直接相加当真实系统 |
| 时间 | SARAH类小时值有卫星成像时刻的瞬时语义；ERA5为小时平均，JRC手册解释其中心时刻。按响应时间戳、库和语义对齐，不统一强制整点 |
| TMY | TMY从不同原始年份选月，适合典型场景，不是实际某个历史年。当前函数默认coerce_year=1990、UTC；显式选定模拟年/是否roll、保存meta中months_selected和原始年份。虚拟年份不表示数据在1990测量，也不能忽略日期/DST后直接拼负荷 |
| 输出和损失 | `P/1000`作为该具名PVGIS模型的系统出力估计进入AC场景；它不证明真实型号输出曲线。其综合系统损失已经存在，不再走完整pvlib模块→逆变器损失链重复扣。限发、削顶、储能与计量边界另记，不能混入PVGIS loss后又重复扣 |

PVGIS地形horizon不等于近场树/楼/天窗/女儿墙和排间模型。缺近场证据时必须显示未建模项；不得默认为详细遮挡已算。小时气象重复四次可用于声明重建假设的15分钟场景，但**不能签发15分钟真实削峰保证**。[JRC API](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en)、[JRC用户手册第9节](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)、[pvlib TMY](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_pvgis_tmy.html)。

### 4.2 Explicit irradiance-to-AC：明确参数的pvlib链

阶段产物按顺序固定，不静默从PVGIS系统输出切进这条链：

```text
原始气象GHI/DNI/DHI + 明确时间/太阳位置
 → 实际阵列POA各分量
 → 已声明的horizon/近场/排间/IAM等传递
 → 安装条件对应的cell温度
 → DC功率或完整I-V
 → 实际端口/MPPT/逆变器限制及转换
 → 各AC节点出力、损失和限发
```

**POA：** `get_total_irradiance`返回`poa_direct/poa_sky_diffuse/poa_ground_diffuse/poa_global`，均W/m²；`POA_global=beam+sky+ground`。输入DNI是法向，GHI/DHI是水平量；不能把Gb(i)平面直射直接当DNI。模型必须具名：isotropic是简单各向同性场景，Hay-Davies等需dni_extra，Perez/Perez-Driesse还需相对airmass；不能缺参数便换模型且不留痕。albedo亦记录实际值和来源，不把库默认0.25当现场事实。[POA API](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_total_irradiance.html)。

**温度：** 优先使用能明确输出cell温度且与安装条件对应的模型，例如SAPM：

```text
T_module[°C] = POA[W/m²] × exp(a + b×wind_10m[m/s]) + T_air[°C]
T_cell[°C]   = T_module + (POA/1000) × deltaT[°C]
```

a/b/deltaT须固定到构造和安装条件，不能所有欧洲屋顶统一open-rack。Faiman默认参数来自特定开架实验，且module温度与cell温度不能直接混用。SAPM官方数值例：open_rack_glass_glass，POA1000、T_air10、wind0得到**44.11703066106086°C**；适合作库适配回归，不是现场校准。[SAPM cell](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.sapm_cell.html)、[Faiman既有原文](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.faiman.html)。

**DC简化模型：** pvlib PVWatts V5在未启用可选低照调整时为

```text
P_dc[W] = (G_effective[W/m²]/1000) × module_stc_w[W]
          × (1 + gamma_pdc[1/°C] × (T_cell−25)[°C])
```

gamma从型号事实取得，百分数/°C先除100；G_effective的IAM与污损等损失处于哪个阶段必须记录。当前API另有可选k/cap_adjustment，无来源不启用。此模型求Pmpp，不产生可靠Voc/Vmpp/Isc/Impp；电气端口检查不能由它假造。[PVWatts DC](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.pvwatts_dc.html)。

**详细I-V：** 若已有型号匹配、可追溯并验证的CEC参数，`calcparams_cec(G_effective,T_cell,...)`产生5个单二极管参数，`singlediode`分别求Voc/Isc/Vmpp/Impp/Pmpp；记录算法/参数来源及拟合误差。不用beta_Voc替代beta_Vmpp；冷态绝对电压、热态/低照MPPT、输入/MPPT电流和短路电流分别检查。不能因公共数据库有相似名称就认定是托管手册同一变体。[CEC API](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.calcparams_cec.html)、[singlediode](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.singlediode.html)。典型年温度不能替代有依据的设计极值。

**逆变器PVWatts场景模型：** 与组件STC字段分开：

```text
zeta = P_dc / inverter_pvwatts_dc_limit_w
eta  = (eta_nom/eta_ref)×(−0.0162×zeta − 0.0059/zeta + 0.9858)
P_ac0 = eta_nom × inverter_pvwatts_dc_limit_w
P_ac = min(eta×P_dc, P_ac0)；零输入单独处理，不能计算除零
```

同一函数名pdc0在DC模型代表组件STC W，在逆变器模型代表**逆变器DC输入limit W**。名义效率参数是场景模型/设备参数，库默认0.96/0.9637不是所有SKU事实。多MPPT/共享混合机、无功占用、温度/SOC降额、PCS和电池通路还须其真实能力模型；PVWatts曲线不放行这些。[逆变器API](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.inverter.pvwatts.html)。

**损失台账：** 每一损失记录`stage, port_boundary, model, parameters, source, applied_once`。可乘的独立百分比按`remaining=∏(1−loss_i)`而非直接求和；逐时遮挡/失配不能凭一个通用百分数替代。几何受阴比例与串/旁路二极管电损失分开，规则无限排模型不可直接覆盖不规则屋顶。[行阴影](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.shading.shaded_fraction1d.html)、[infinite_sheds](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.bifacial.infinite_sheds.get_irradiance.html)。

**独立解析预期，供实施验收，不声称本轮已经执行：**

- 10片400W→4kWp；G_effective800、T_cell45、gamma=-0.004、module_stc_w4000→**2944W DC**。
- 逆变器模型DC limit1000W、eta_nom0.96、eta_ref0.9637：DC1000→**AC960W**；DC2000的模型输出被截到960W。不得把4kWp阵列的4000W直接当这台逆变器的limit。
- 水平面、solar_zenith60°、DNI800、DHI100、GHI500，isotropic模型→beam400、sky100、ground0、POA500W/m²。
- 两项损失2%和3%→剩余**0.9506**；不是0.95。上述只证明量纲和接口组合，不能当SKU或真实天气精度证明。

## 5. 连续AC能流与储能状态的实现核心

本节是单AC母线、单储能、明确方向效率的起始实现合同；多柜/多母线按相同守恒扩展。其守恒式为本研究推导，不伪称逐字摘自SAM。SAM/OpenSolar支持分路径效率、功率、状态及控制分别建模，原始依据见§11。

对每个t，所有功率为kW区间平均、Δt为小时：

```text
S_available + G_import + D = L_gross + C + G_export + PV_curtail + Aux_AC
E_next = E + eta_charge×C×Δt − (D/eta_discharge)×Δt − E_aux_internal − E_standing_loss
0 ≤ E_next ≤ E_window_available
0 ≤ C ≤ ChargeCapability(state,mode,ports,T)
0 ≤ D ≤ DischargeCapability(state,mode,ports,T)
```

S_available是在已选PV模型及已声明设备转换后、限发前的AC潜在输出；实际发出`S_generated=S_available−PV_curtail`。削顶和限发分别记，不能当作电池损耗。Aux_AC在AC母线上，E_aux_internal/E_standing_loss是内部kWh，不得全量两边重复扣。

第一式是负荷全部满足时的式子。失败场景仍须保持物理账本：记录`L_served=L_gross−U_load`、`0≤U_load≤L_gross`，实际母线式用L_served，未供量单独输出；硬任务要求U_load=0。诊断求解可引入短缺变量，但它不是供能来源，不能计PV/电网/储能贡献，也不能通过放宽该变量给任务放行。自给率分母仍按所定义的总负荷需求，不能仅以较小的已供负荷掩盖停电缺供。

1. **E的基准固定。** 起始简化模型令E为物理可用SOC窗口内的内部电量，0对应该窗口下限；E_window_available已经是可用容量时不再乘同一DOD。若输入名义容量及SOC窗口，固定参考下`E_window=C_ref×(SOCmax−SOCmin)`、`E=(SOC−SOCmin)×C_ref`。这些转换不替代非线性Q/V/热模型；容量随状态变时不能简单clamp E销毁能量，须相应物理适配器和损失见证。
2. **方向效率固定来源。** 两向eta∈(0,1]；只有round-trip时，`sqrt(roundtrip)`仅可作为明确的对称化估计（OpenSolar采用此简化），不能声称有双向实测。电池端DC和PCS AC必须分别换算。
3. **每台储能模式互斥。** 起始模型不允许同台同时充放：`C×D=0`，优化可用binary约束。多柜一充一放的真实拓扑不能套一个全站互斥，必须逐设备建状态。导入/导出在瞬时端口的互斥也与区间内双向计量分开，不能伪称小时平均能判断所有瞬时行为。
4. **不裁掉物理失败。** policy命令超能力时，模型返回实际执行量和缺供/未达到目标；不能先减E再clamp并仍报负荷已满足。每段功率、母线和状态都由独立verify检查。
5. **没有日期重置。** Midnight、CSV拼接、月切换、控制任务切换均不改变E。连续运行按TaskSpec要求`E_end≥E_start`或周期边界；一次停电可允许消耗初态，但不得说成循环年年可持续。初末状态在结果显示。

恒效率无其他损耗、初末E相同时，`AC_recharge ≥ AC_discharge/(eta_charge×eta_discharge)`。这是补能下界，不是实际设备承诺；跨时间可用充电功率和电网余量还须同时满足。

## 6. 能量来源账本和指标定义

每台电池至少携带`E_pv/E_grid/E_initial_unknown`，已知初始PV库存另有明确来源和期初标记；总和必须等于E。PV/grid充入各乘eta_charge。内部放电消耗量为`D×Δt/eta_discharge`；按声明的比例混合记账从各bucket扣除，给负荷/外送的AC量和转换损失都按同一比例分配。比例混合是透明会计约定，不是可识别电子的物理事实；替换FIFO时模型版本和指标变更。自放电/内耗也必须分配，不能从总E扣了却留在PV bucket。

```text
gross_load_energy = Σ L_gross×Δt
solar_load_energy = PV_direct_to_load + battery_PV_origin_to_load
solar_autarky = solar_load_energy / gross_load_energy
```

grid充电和初始未知库存不计太阳能贡献；不简单使用`1−全年购电/负荷`，该式会被跨期库存、电网补能和计量边界破坏。总负荷为0则指标为undefined并有reason，不输出NaN、0或100%的伪意义。

在**无储能外送**、同一AC边界下，输入侧PV自用率为`(PV_direct_load+PV_charge_AC)/PV_generated_AC`；它计入充入后损耗/库存，与“实际太阳能给负荷比例”不同。另输出`PV_onsite_input_share`，分母为限发前可用潜力，不能与实际发电分母混用。无实际PV发电时自用率为undefined。储能外送或期初PV库存跨期时，应提供带周期来源的出口/库存账本并另定口径，不能继续套上述特殊式；未支持该指标域时返回该项`MethodDomainExceeded`而非编数。[HTW定义原文](https://solar.htw-berlin.de/faq-unabhaengigkeitsrechner/)、[既有公式与来源研究](https://github.com/AssassinFlash/de-linker/blob/0b37a330219645bd1701b4c2174784931e87e604/docs/research/2026-10-22-roof-calculation/method-study/README.md)。

独立解析预期：PV10kWh全部充入，eta_c=eta_d=.9，之后负荷10kWh、终态0，可交付PV来源8.1kWh，电网补1.9；输入侧自用率100%，太阳能供负荷比例81%，损耗1.9。无PV、先grid充5后给负荷5、效率1：太阳能自给率必须0，而不是100%。

## 7. 可执行policy、理想可行域和多任务约束分开

### 7.1 可立即实现的policy replay

首先实现一个具名的`self_consumption_with_reserve`基线，所有参数来自输入而非暗设：

```text
surplus = max(S_available − L_gross − Aux_AC, 0)
deficit = max(L_gross + Aux_AC − S_available, 0)
C = min(surplus, charge_cap, (E_max−E)/(eta_c×Δt))
D = min(deficit, discharge_cap, eta_d×max(E−E_guard,0)/Δt)
```

上述无站立/内部损耗的闭式步进仅适用对应简化物理模型；启用损耗时先由该模型计算本步可充/可放界限。余量按允许的电网收发/限发处理，得到真实未供量及目标违反。`E_guard`可含正常备电保留和有依据的削峰保留区；不能将一个合成例的4kWh设成默认。它是可重放控制规则，**不保证未来峰值一定被削掉**。

削峰+自用采用同一电池状态和明确优先级/SOC分区；grid补能必须由policy允许，受电网余量、充电功率和终态约束。若要保证未来峰值，须使用具名的预测/滚动策略并声明预测输入/时限，或先给理想可达域。SMA multiuse提供SOC分区成熟先例，不能从其网页推导任意控制器支持本站命令。[SMA multiuse](https://manuals.sma.de/SDesign/en-US/14444632075.html)。

### 7.2 理想调度存在性/边界求解

可将§5各段C/D/E及PV、grid流量作为变量，以binary限制同台充放和适用端口模式，加入reserve、grid窗、初末态等约束。binary上界取设备/连接物理能力，不任用巨大常数。先求硬任务可行性，再按明示目标减少grid能量/吞吐等；不同目标采用明确优先级或Pareto，不能以产品ID、最大电池或AC最接近kWp当最优。

必须输出求解状态、可行见证、未满足约束、上下界/最优性差距及搜索覆盖。`timeout/unknown/numerical_failure`不是infeasible；有可行解但未证最优，不能叫最优选型。此角色记为`perfect_foresight_feasibility`，另与policy replay比较；理想调度存在不等于该EMS/固件可执行。非线性状态能力、电气化学和多端口曲线未进入求解器时，其可行域也不能放行这些未建模能力。

### 7.3 削峰与备电的任务合同

- 削峰先指定计量点与窗：若为15分钟进口需量，`window_average_import = Σ(G_import×overlap_h)/window_h ≤ cap_kw`。瞬时上限、净计量、进口计量不是同一式；原始负荷分辨率不足或PV只有小时重建时，输出场景结果与证据限制，不签实际15分钟保证。
- 停电在明确start/end切换模式，`G_import=G_export=0`。负荷取critical_load，PV仅在该孤岛拓扑确实可用时保留；能力、最小SOC、切换/黑启动/STS/控制器另取相应模式。
- 停电初态从正常policy在该时点的E及来源继承，或明确为用户指定情景；不能每个停电都假设满电。扫描多个开始时刻时输出覆盖数、起点列表及失败见证；只测部分起点不声称全年任意时刻续航。
- 自用、削峰和备电共享库存。正常备电floor不应被自用或削峰“重复花掉”；停电时是否可下降到不同floor必须有设备/策略依据。容量足而功率不足仍失败。

[SAM BTM dispatch](https://samrepo.nlr.gov/help/battery_dispatch_btm.html)、[SAM grid outage](https://samrepo.nlr.gov/help/grid_outage.html)支持这些边界区分；SAM自身DC耦合可能假定双向混合逆变器，不能据此给真实型号补出功能。

## 8. 独立验收清单：继承已解决例，不重做研究

下表是实施必须通过的合同。既有结果来自固定研究提交，**本轮未重跑17条，也未跑新产品Kernel**。[原始输入、逐步流量与结果](https://github.com/AssassinFlash/de-linker/blob/0b37a330219645bd1701b4c2174784931e87e604/docs/research/2026-10-22-roof-calculation/method-study/reference-results.json)。测试应由解析下界/独立账本给答案，不从实现再计算expected。

| 场景 | 必须保留的独立预期 |
| --- | --- |
| 跨午夜20kW负荷20:00–04:00，grid cap10kW | 需80kWh AC，eta_d=.94时内部至少85.1063829787kWh；42.6不可行。还要验证低负荷补回初态的可用时间/功率 |
| 放电10kWh，两向.94、初末相同 | 至少11.3173381621kWh AC补能；10kWh充电余量不可行 |
| 初始PV0、PV总2.208kWh、总负荷4kWh | 无损太阳能自给上限55.2%；有效率/时序限制只会收紧 |
| 停电10kW×1h，容量20kWh | 连续输出cap5kW仍不能满足；容量不能掩盖功率缺口 |
| grid充5→放5、无PV | 太阳能贡献0；来源账本闭合 |
| 初态未知5kWh供5kWh停电负荷、无其他输入 | 一次性终态0可行；要求终态≥初态5则不可行，初始未知不计PV |
| PV存6kWh，后两段负荷3/8，各1h、grid cap4、eta1 | 前段放2留4、后段放4可行；贪心先放3导致后段购电5，不能由理想可行假称贪心policy也通过 |
| 上例另保留4kWh备电 | 同一库存不能重复分配；初态6不足，8可行（其余条件同研究夹具） |
| 时间/量纲/PV接口 | §3、§4解析值；DST回拨两段均保留，年能量重采样不变；组件/逆变器pdc0域不混淆 |
| 守恒与来源 | 每段AC残差、E残差、bucket和、充放互斥、能力、reserve和终态全核；禁止先clamp后只比年总量 |

数值误差容差是软件参数，不是现场准确率。建议对无噪声float64合成夹具使用并记录`abs_tol_energy=1e-7 kWh`及`rel_tol=1e-9×相关能量尺度`，功率另有kW容差；真实工程安全裕量与输入不确定性独立计算，不能以容差给硬边界放行。保留原始残差、约束余量和使用的阈值，返回有限JSON数值或有原因的undefined。

官方外部实现的既有有限对照：[BatteryStateful结果](https://github.com/AssassinFlash/de-linker/blob/0b37a330219645bd1701b4c2174784931e87e604/docs/research/2026-10-22-roof-calculation/method-study/official-crosscheck-results.json)，`nlr-pysam==8.0.0`单步Q积分/VI功率、25h连续状态、过大命令实际受限、参数/状态读回四项。它没有验证本站SKU，也没有证明MILP或新Kernel与完整SAM整年调度等价。

## 9. 不能诚实放行的条件及程序返回

| 条件 | 可返回的真实成果 | 不允许的结论 |
| --- | --- | --- |
| 没有有效时序，只有年耗/kWp | 有来源负荷模板下的场景估计或需求缺项 | 准确自给率、15分钟削峰、容量最优 |
| 只有小时天气却要求实际15分钟保证 | 具名重建的场景、分辨率/不确定性 | 把重采样当新增观测 |
| 只有PVWatts功率参数，没有I-V/设计温度/端口依据 | 产量场景和具体缺项 | 冷态安全、热态MPPT、全部组串通过 |
| 有容量/一般兼容，缺相应模式功率/STS/附件依据 | 条件模型可达值与EvidenceMissing | SKU备电/并机/切换已经放行 |
| 只通过perfect-foresight、无实际控制合同 | 理想可达见证，policy对照及差距 | EMS实际能实现或未来所有天气都保证 |
| 用AC单母线模型遇DC共享混合机/多相/多柜越域 | 已能计算的部分、MethodDomainExceeded及适配需求 | 将缺少的端口/状态默认为独立且无限能力 |
| 缺遮挡、温度/效率参数或国家规则 | 具名假设场景、未知及待补证 | 0损失/统一欧洲参数/工程通过 |
| 求解中断、数据缺测、终态耗尽 | SolverIncomplete/InputInvalid/不可重复边界说明 | 不可行证明、零值继续或年复一年续航 |

错误与不确定性同时是数据：`InputInvalid/SourceUnavailable/EvidenceMissing/MethodDomainExceeded/Infeasible/SolverIncomplete/VersionUnavailable`附字段、时段、设备/约束ID、来源、可复算见证；另列天气年际、输入测量、模型结构、设备参数、控制预测等不确定性。国家规则、结构/消防/并网审批由对应模块判断；数值守恒通过不代表这些事项已通过。

## 10. 实施顺序与合并门

1. **TimeAxis/计量/单位与不可变有效参数。** 先做解析、区间交叠和原始来源保留；用DST/跨午夜/能量积分解析例验证。没有这层不接PV-load联合。
2. **单母线状态replay+来源账本+独立verify。** 先消费明确的已给定PV/负荷序列；实现功率/容量/效率/初末/保留/停电。复用§8的已解决边界作新实现验收，不移植旧年量引擎。
3. **具名PV适配器。** 接PVGIS的固定请求/响应与时间语义；接pvlib显式链并逐公式验证。各自阶段和损失不混算，数据库/天气缺失显式失败。
4. **联合policy与存在性oracle。** 明确任务、meter窗及真实policy优先级；理想求解仅作可行域对照。生成设备图后重新按真实能力replay，返回失败时段与余量。
5. **逐设备/拓扑与精度证据扩展。** 接硬件方提供的模式/电压/电流/功率曲线、DC/多相/并联及国家合同；每个新适配域有独立夹具/原件/必要基准，未覆盖域准确返回缺项。
6. **同run投影。** 屏幕、指标、BOM、报告和商务引用同一结果身份；不得用最新设备/新输入重算某一块。计算成功、验证通过、硬件证据齐备分别保存。

第2步可立刻开展，不依赖天气网络或未到位设备资料；但它的结果角色是已明示模型的replay。进入具体SKU任务的已验证集合，还必须满足相应资料与控制/国家条件。以上顺序不是删减目标能力，也不是以future adapter代替完成。

## 11. 原始依据、版本及本轮Apify取证

继承的主要依据：

- [统一方法研究及公式台账，固定0b37a330](https://github.com/AssassinFlash/de-linker/blob/0b37a330219645bd1701b4c2174784931e87e604/docs/research/2026-10-22-roof-calculation/method-study/README.md)，含SMA/OpenSolar/SAM原始全文、17条参考运行、4项官方物理检查及模型限制。
- [工程方法研究，固定768cc73e](https://github.com/AssassinFlash/de-linker/blob/768cc73e921d3b07afd5548d51c43f47b2e5fc5c/docs/research/2026-10-22-roof-europe-precedents/engineering-study/REPORT.md)，含pvlib0.16.1 CEC/单二极管/Faiman/行阴影、JRC API与时间语义、设计温度和型号/地域边界。其Apify physics run为7MOtn1UhYhSXuaK5b、dataset Z44vSQlt8cWdoUnW5；本轮只读继承，不重复抓取。
- [SAM BTM物理输入](https://samrepo.nlr.gov/help/battery_storage_btm.html)、[BTM控制](https://samrepo.nlr.gov/help/battery_dispatch_btm.html)、[停电](https://samrepo.nlr.gov/help/grid_outage.html)、[BatteryStateful API](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html)：原件已于此前经Apify保存，模型/控制分工与限制按该次证据继承，没有宣称本轮新运行。

本轮新增取证仅6个实施需要的pvlib官方页，Actor为既有获准`apify/website-content-crawler`，memory2048MB、maxConcurrency2、Cheerio；run **hSwl9BZAT4I3m4nuF**、dataset **m05gZ6RvegRd7WhJs**，6/6页面成功。只在本文记录公开来源与正文SHA；未向其他目录写raw、未输出/保存令牌，未批准新Actor权限。SHA取Apify返回markdown正文UTF-8字节，便于从dataset独立核对：

| 官方页，正文版本均0.16.1 | 正文SHA256 |
| --- | --- |
| [get_pvgis_hourly](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_pvgis_hourly.html) | `42b998c47132c4d222fad854b95c6fa722d2ccaf4249a363ce0cc4edf44ac3b3` |
| [get_pvgis_tmy](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_pvgis_tmy.html) | `1b044309746e610f6b961a3f9e6688f4905344564a8638abd8d1203658c71813` |
| [pvwatts_dc](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.pvwatts_dc.html) | `f8218a7b9d20855777b1606abd451d6dcc7f404d4d057f6d516eecd9e615b7be` |
| [inverter.pvwatts](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.inverter.pvwatts.html) | `67b996de521663ab0525a30b628f8587017cd29cab5422140459c1599ea90e48` |
| [sapm_cell](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.sapm_cell.html) | `bc3aabbf5aa6e6b10f3fad52f09753eff9ae6ca1f78b16bb7e04ae0ca5bdcf15` |
| [get_total_irradiance](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_total_irradiance.html) | `03dc995832ff78050ed19fbc2cedce6c3f4f9daeb47a1e2338ea8e742c003a16` |

本文给出的是可实施/可验收合同与证据，不是新生产Kernel已经通过。官方公式、守恒推导、项目实现选择、既有执行结果和仍未知的SKU/现场证据在上文分别标明。
