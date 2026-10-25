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

## 12. 下一批实现决策：共享DC端口执行器与可替换电池状态核心

2026-10-25。问题限定为：已有PV/负荷时序与Woo设备事实后，怎样执行真实AC/DC耦合和连续储能状态。本节只补实施决策，继承§8已完成的参考检查；未重跑17条、全年、页面或SKU测试，也未修改运行环境。结论是：**立即实现具名的`constant_window_shared_dc_bus_v1`，共享DC端口执行器与电池状态核心分开；现有AC模型继续服务独立PCS拓扑；`PySAM.BatteryStateful`作为参数齐备时的可替换细物理核心。** 共享端口与能量账本采用下面的明确合同，其成熟依据是SSC的母线分流与共享逆变器结构；本节的固定窗口执行器属于本站实施选择，不宣称已经封装、执行或等价于完整SSC调度。

### 12.1 两个PySAM入口的实际能力与选择

| 入口 | 可接的输入、执行边界 | 本批采用方式 |
| --- | --- | --- |
| `import PySAM.Battery as Battery`；`Battery.default("CustomGenerationBatteryResidential")`或Commercial | `SystemOutput.gen`是已给定发电kW，`Load.load`是AC负荷kW；`BatterySystem.batt_ac_or_dc=1`为AC；`BatteryDispatch.batt_dispatch_choice=2`与`batt_custom_dispatch`可接每步电池命令（AC连接为kW AC，DC连接为kW DC）；一次`execute()`运行年度/多年。`gen`为INOUT，执行后已包含储能影响，必须另存原始输入。 | 仅适合将来对**规则完整年、独立AC PCS**作外部基准；不取代当前任意区间replay。通用发电模块明确拒绝DC连接。 |
| `import PySAM.BatteryStateful as BatteryStateful`；`BatteryStateful.new()` | 只含电池电压、容量、热和寿命状态；`Controls.control_mode=0`接A，`=1`接kW，均为**电池DC端子**；`setup()`一次，之后每步`execute()`。没有PV、负荷、PCS、共享逆变器、实际BMS功率/电流上限或本站policy。 | 参数和时间域合格才启用；外部端口执行器仍负责功率、电流、共享逆变器、计量和来源账本。其估计`P_chargeable/P_dischargeable`不能代替厂商连续功率。 |
| SAM详细PV Battery / `PySAM.Pvsamv1`的集成储能通道 | SAM在PV链内将PV DC与储能交给同一共享逆变器；官方说明它会假定该逆变器具有双向/混合能力，实际选中的逆变器可以并不支持。 | 作为端口结构依据；不通过换一个配置名给任意Woo逆变器补出双向、备电或共享端口能力，也不为接已给定PV时序重新运行一套PV模型。 |

上述API、单位及命令模式见继承的[Battery API](https://nrel-pysam.readthedocs.io/en/main/modules/Battery.html)、[BatteryStateful API](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html)。[SAM Cell and System](https://samrepo.nlr.gov/help/battery_storage_btm.html#powerconverters)明确区分固定效率的电池转换器与带负载效率曲线的PV逆变器，并说明DC模式的双向假设。新的官方源码证据固定为SSC提交`c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8`：[cmod_battery.cpp L2373–2386](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/ssc/cmod_battery.cpp#L2373-L2386)按`8760 / 每年gen条数`取得小时步长，[L2505–2507](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/ssc/cmod_battery.cpp#L2505-L2507)直接抛出`Generic system requires AC-connected battery.`。因此短周、不规则区间、闰年或明确UTC时轴不能靠填入任意长度数组进入该通用模块。

本机只读复用旧研究隔离安装/uv缓存，实际distribution为`nlr-pysam==8.0.0`、SSC **308**，native build信息为`OS X 64 bit GNU/C++ Aug 13 2026 01:34:50`。只做API/默认参数读回及native错误文本检查；没有安装到当前engine环境。该wheel包含上面的AC限制错误文本；本轮读取的固定SSC源码不是这份wheel构建提交的证明，不能据此声称二进制逐行同版。既有四项Stateful运行证据仍以§8的固定结果为准。

### 12.2 固定窗口DC模型的最小输入域

首个域是**一个PV DC母线、一台共享逆变器、一个电池栈连接一个已指明的电池端口、一个AC负荷/电网计量点**。同台逆变器未使用的第二电池端口不增加本配置的电流、功率或容量。多栈/多变流器、逐相不平衡、瞬态切换、无功和热降额曲线另经对应端口/模式模型承载；相关任务越过已实现域时准确返回`MethodDomainExceeded`。并网/停电可用性与功率分别由输入给出，拥有DC端口不证明孤岛、黑启动或PV在停电时仍可用。

| 参数组 | 必填内容及单位；缺项规则 |
| --- | --- |
| 时间与PV阶段 | 与AC负荷同一`TimeAxis`；PV输入是`pv_dc_available_kw_at_bus`，保留逐阵列未削顶DC、MPPT/DC线路后的DC母线产物及已施加损失。PVGIS系统AC或已削顶AC不能反除效率重建这项输入；缺失返回`EvidenceMissing(pv_dc_stage)`。 |
| 电池状态 | 明确的usable内部窗口`E_window_kwh`、初始`E`与来源分量、正常/停电reserve和terminal要求；`eta_store_charge/eta_store_discharge`定义**DC端子↔该内部库存**的方向效率，`internal_aux_kw`、standing-loss模型和顺序显式给定。若设备可用kWh已含DOD，不再扣第二次。参数来源可为厂商事实或明确场景；场景不能转成型号验收。 |
| 电池端口 | 选中`battery_port_id`，该栈与该端口各自充/放电连续kW、最大电流A、工作V范围、适用SOC/温度/模式及限值为逐口/总计的范围；同一配置逐项取交集。peak/fault电流不可变成连续电流，端口数不可乘成一口额定值。 |
| 电池DC/DC | `eta_bus_to_battery`、`eta_battery_to_bus`及各方向kW/A/V能力，边界为DC母线↔电池端子。设备事实若只提供一个双向固定效率，须保存该事实的适用声明；若只有系统最大效率/Euro加权效率，不能补出这两个值。 |
| 共享逆变器 | 每模式实际共享`forward_ac_kw`、适用的共享DC输入约束及单独PV输入约束；固定窗口首版使用具名`fixed_directional_efficiency`模型的`eta_inv_forward/eta_inv_reverse`。未来曲线可替换此函数，现版本不将最大效率当逐时效率。支持反向充电必须有明确true及反向AC/DC能力；unknown保留为unknown，相关命令返回`EvidenceMissing(reverse_conversion)`；明确false的路径不进入可执行图。 |
| 运行与控制 | `pv_charge_allowed/grid_charge_allowed/battery_export_allowed`、母线辅助负荷与供应端、import/export cap、正常/停电能力、policy优先级；每项皆有显式值或缺项状态。首版沿用禁止电池外送的指标域。逆变器支持反向与policy允许电网充电是两项条件。 |

简化模型不生成虚构的逐步电池电压。只有厂商工作电压范围与电流上限时，可选择显式`voltage_floor_current_cap`保守规划包络：每方向`P_dc_cap = min(适用连续DC kW, I_max_A × V_operating_min_V / 1000, 所选PCS端口能力)`，并保存使用的电压下界及适用条件。这是由`P=VI`推得的**电流安全上界约束**，不证明真实电池在所有SOC/温度都持续交付该功率；其余降额/连续能力证据仍单独判断。不能用名义电压把最大电流直接当全程恒功率，也不能用最大工作电压放宽该保守包络。缺少有效工作范围或持续能力时，计算保留具体缺项，不生成“通用电池”。

### 12.3 可直接编码的共享端口方程与步进

以下是本站的固定方向效率模型；所有功率kW、时间h、库存kWh。`C_b/D_b`是**电池DC端子**实际充/放电，非AC等效功率；`S_dc`是已声明DC路径损失后的可用PV母线功率；`K_dc`为未进入任何用电路径的PV削顶/限发。每个设备端口能力先按mode/state求出，再执行命令，最后才推进同一库存：

```text
C_bus = C_b / eta_bus_to_battery
D_bus = eta_battery_to_bus × D_b
x_inv_dc = S_dc + D_bus − C_bus − Aux_DC_served − K_dc

x_inv_dc >= 0:  P_inv_ac = eta_inv_forward × x_inv_dc
x_inv_dc <  0:  P_inv_ac = x_inv_dc / eta_inv_reverse

P_inv_ac + G_import = L_served + Aux_AC_served + G_export
E_next = E_after_explicit_internal_losses
         + eta_store_charge × C_b × dt
         − D_b × dt / eta_store_discharge

C_b >= 0; D_b >= 0; C_b × D_b = 0; 0 <= K_dc <= S_dc
−P_reverse_ac_cap <= P_inv_ac <= P_forward_ac_cap
```

负`x_inv_dc`需有真实反向路径、policy允许、模式可用、反向功率与电网余量全部满足。它是**同一桥的净反向**，不创建同时满功率正向/反向两个独立逆变器；客户负荷仍可在共享逆变器正向发电时由电网补足。若适用无功能力域，`P_forward_ac_cap`另受`P²+Q²≤S²`约束；首版没有Q模型时，不给要求该能力的任务放行。辅助负荷无源可供时记录未供量，不靠负库存满足守恒。

SSC的对应成熟结构为：[powerflow L689–701](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/shared/lib_battery_powerflow.cpp#L689-L701)将电池端DC按DC/DC方向换到母线，再与PV DC相加；[L719–769](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/shared/lib_battery_powerflow.cpp#L719-L769)分出PV充电、余下PV与允许的电网充电；[L781–813](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/shared/lib_battery_powerflow.cpp#L781-L813)只将净DC送给共享逆变器，并将电网补入的DC除以转换效率得到AC需求；[L876–896](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/shared/lib_battery_powerflow.cpp#L876-L896)对合并DC执行一次逆变器转换。这支持上述端口分工，不代表应继承SSC的通用效率/缺参补值。

实现按以下顺序落地，不等待完整电化学资料：

1. **PV适配层交出DC产物。** 保留现有PV计算的模块/阵列未削顶DC与每个损失阶段；独立PCS继续消费对应AC产物，DC共享机消费实际DC母线产物。两条入口用阶段类型校验，不能靠一个无单位`generation`字段混用。
2. **执行器先分DC充电，再执行共享转换。** policy先保留PV服务负荷/辅助需求所需的DC，再允许其余PV在削顶前充电；剩余出力在共享逆变器与电网出口约束下转换/限发。放电先受窗口、reserve、电池/所选端口DC能力限制，再受PV占用后的**同一逆变器余量**限制。单纯固定效率、无其他DC损失时，余量为`max(P_forward_ac_cap/eta_inv_forward − S_dc, 0)`；有DC辅助、PV限发或不同优先级时，用上面的实际母线式重新计算。不得先放掉电池再把合并AC截断而丢弃电池能量。
3. **所有命令只按实际量推进E。** 约束后的`C_b/D_b`进入窗口状态核心；缺供、未交付命令、PV削顶/出口限发和各方向转换损失分别输出。每次试算若需缩小命令，必须从同一前态重放，只提交最后可行步。SSC也以保存前态→运行电池→计算powerflow→核限→恢复前态迭代的方式协调物理状态与端口，见[dispatch L427–467](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/shared/lib_battery_dispatch.cpp#L427-L467)。本站固定窗口有解析界限时直接求该界限，不照搬SSC的迭代次数、误差阈值或缺参fallback。
4. **保持来源与损失阶段。** PV/grid在DC母线进入电池各自分账，依次通过实际DC/DC和库存充电效率；放电先从库存按§6混合扣除，再过电池端子→DC母线→共享逆变器。共享转换只施加一次；PV与电池的实际共享转换损失按声明分配约定归属，不能分别计算`F(PV)+F(battery)`。没有PV时的grid充放仍贡献0太阳能。PV已在DC充入电池的部分不再先过PV AC转换；其以后放电才经过共享逆变器。
5. **独立verify重建双母线与状态。** 返回并核对`PV_to_battery_bus_dc/PV_to_inverter_dc/battery_to_inverter_dc/grid_to_inverter_ac`、共享逆变器DC/AC净方向、逐路径损失、PV削顶与其他限发、AC供需、DC供需、窗口与来源前后态、端口和模式上限。不把SAM的AC等效`system_to_batt`当真实DC充电量。所有屏幕/报告继续引用同一run固定的阶段、事实hash和状态。

**只新增能区别这个域的解析验收，未在本轮执行：** ①PV DC12kW、共享AC10kW、效率1、battery有2kW充电余量时，应PV→load/export10、PV→battery2，不能先削到10而丢掉可充2；②PV8、battery请求放5、共享AC10、效率1时实际放电≤2，未交付≥3，E只扣实际2；③反向能力false时grid充电不执行，有能力且显式`eta_inv_reverse=.9`时电池母线需9kW对应10kW AC输入，不能按8.1或9计购电；④两个50A端口、只选一口与30A电池限流时不得得到100A能力。实际型号验收继续需要自己的事实与输入，合成例中的效率1/.9只属于夹具。

### 12.4 Stateful的精确启用条件和Python接法

`BatteryStateful`的Li-ion原件要求如下；这是模型必填合同，不要求把所有产品都强行拟合进它。[官方参数API](https://nrel-pysam.readthedocs.io/en/main/modules/BatteryStateful.html#paramscell-group)、[源码参数构造 L427–563](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/ssc/cmod_battery_stateful.cpp#L427-L563)。

| 组 | 显式输入、单位与条件 |
| --- | --- |
| `Controls` | `control_mode`；`dt_hr`小时；`input_power`kW DC或`input_current`A。正号放电、负号充电；两模式只选一个。 |
| `ParamsCell`基础 | `chem=1`、`initial_SOC/minimum_SOC/maximum_SOC`百分数；`Vnom_default`为**单电芯**额定V、`Qfull`单电芯Ah、`resistance`单电芯Ω；不能将系统电压/整柜电阻填进单电芯字段。 |
| 电压模型 | `voltage_choice=0`需`Qexp/Qnom` Ah、`Vfull/Vexp/Vnom/Vcut` V、放电曲线的`C_rate`；或`voltage_choice=1`并提供`voltage_matrix`两列`[DOD%, cell V]`。系统工作V范围不等于该DOD电压曲线。 |
| 寿命 | `life_model`明确选型；若`=0`需`cycling_matrix=[DOD%, cycle#, capacity%]`和`calendar_choice`；`calendar_choice=1`还需`calendar_q0/a/b/c`，`=2`需`calendar_matrix=[day#,capacity%]`。预设NMC/LMO-LTO寿命模型不能仅因产品写“锂电池”就套用。 |
| `ParamsPack` | `nominal_energy`kWh、`nominal_voltage`V、`mass`kg、`surface_area`m²、`Cp` J/(kg·K)、`h` W/(m²·K)、`T_room_init`°C；`life_model=0`还需`cap_vs_temp=[°C,capacity%]`。每段环境温度可通过`StatePack.T_room`更新。 |
| 附加选项 | `loss_choice`及匹配的charge/discharge/idle或schedule loss（kW）、拼写为`availabilty_loss`的百分比数组、`replacement_option`及对应条件字段，全部显式固定。关闭老化/更换、零附加损失或恒温都是具名模型/情景选择，不能静默当SKU事实。 |

```python
import PySAM.BatteryStateful as BatteryStateful

model = BatteryStateful.new()
model.assign({
    "Controls": {"control_mode": 1, "dt_hr": fixed_dt_hr, "input_power": 0.0},
    "ParamsCell": resolved_params_cell,
    "ParamsPack": resolved_params_pack,
})
model.setup()
for frame in regular_frames:
    model.StatePack.T_room = frame.battery_room_temperature_c
    model.Controls.input_power = frame.deliverable_battery_dc_kw
    model.execute()
    actual_dc_kw = model.StatePack.P
    pack_state = model.StatePack.export()
    cell_state = model.StateCell.export()
```

`resolved_*`由完整、固定来源参数编译；代码中的`input_power=0`只是setup控制初值，循环使用首个**真实**区间命令，不额外执行一段“初始化充放电”推进时间。实际交付读`StatePack.P`，并保存`I/V/Q/Q_max/SOC/T_batt/loss_kw/last_idx`及完整`StateCell`；请求值不等于交付值，不能仅按请求更新外部账本。`Q`的Ah、瞬时V×Q、名义kWh×SOC和可交付AC kWh各有边界；不能用其中一个强制覆盖另一个。读回状态/恢复前态的机制见[setup/exec L573–659](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/ssc/cmod_battery_stateful.cpp#L573-L659)。新Stateful执行器的checkpoint恢复、与本站来源账本耦合及端口再约束尚未执行验证，不能沿用旧四项检查声称这些能力已通过。

**启用还有两个硬边界。** 其setup按`ceil(pack V / cell V)`和`round(pack kWh / 每串电量)`推导串并数量，见[参数构造 L440–450](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/ssc/cmod_battery_stateful.cpp#L440-L450)；因此必须核对该派生结构与真实模块/串栈，保留有效模型参数与实际状态，不能把输入的pack值当精确实物结构。其次，exec虽支持修改步长，但仍用`last_idx`与整数`steps_per_hour=(size_t)(1/dt_hr)`换算日历，见[L630–645](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/ssc/cmod_battery_stateful.cpp#L630-L645)；大于1小时可使steps_per_hour为0，不规则步长也不能仅靠索引保全日历语义。本站初始适配域限定**固定`dt_hr=1/n`、n为正整数、显式日历起点及附加损失/更换映射**，长区间须按声明规则细分；不规则轴继续用固定窗口核心，或返回细物理模型越域，不做无记录的重采样。这个保守域是源码审查后的本站选择，不声称官方模型完全不支持其他用法。

### 12.5 Woo事实、场景与有效默认值

厂商事实仍只由Woo维护。编译器从同一Woo快照及其托管资料提取字段和来源，不新建手工SKU能力包；每项至少带`product_id/model_variant/document_hash/page/field_scope/unit/mode/conditions`，以及`verified/unknown/conflicting`状态。需要供给的字段就是§12.2中的端口图、逐口/总计限值、容量与工作V/SOC范围、模式能力、转换效率证据和设备组合/BMS兼容条件；若启用Stateful，再提供§12.4的型号匹配电芯与热/寿命数据。资料有`No. of BAT`或`2×50A`只证明其明确范围；没有来源不得变成单口100A、两个独立满功率PCS或任意并联栈。

本地`Battery.default("CustomGenerationBatteryResidential")`读回包含25年、AC/DC方向96%、DC/DC99%、通用电芯/热/寿命和自动更换；`BatteryStateful.default("LFPGraphite")`也带研究用电芯曲线、内阻、热及寿命值。这些是**库配置**，不属于Woo设备事实。SAM库的最大效率、`SharedInverter`对负功率沿用正向模型的处理也不能证明某型号有对应反向路径；该实现见[SharedInverter L248–290](https://github.com/NatLabRockies/ssc/blob/c92cbf05e3fc1411a91c0fb9b48827dd2104c7f8/shared/lib_shared_inverter.cpp#L248-L290)。原件只有最大效率或Euro加权效率时，保留这两个事实，固定方向模型需要的路径效率保持缺项；允许用户/研究明确提供的效率场景参与计算，但结果同时保留`hardware_and_evidence_state=EvidenceMissing`，不把场景折成产品事实或型号放行。

因此本批可完成的具体交付是：**接出PV未削顶DC阶段、实现并独立复核共享端口执行器、将现有连续窗口与来源核心接到电池DC边界、从Woo编译实际配置并逐项返回计算与硬件证据状态。** 缺少转换曲线不阻止这个执行器及其解析边界完成；它阻止把该设备的未证效率/模式写成已验证预测。此后资料补齐只替换对应有效参数或状态核心，不再重建拓扑/连续库存/来源账本。

### 12.6 本轮新增取证与已证边界

外部新增读取均走既有`apify/website-content-crawler`，只作研发。首次raw URL run `0sx9fqPCGpz32WXG8`虽报告6成功，日志实际说明`text/plain`不可解析、dataset为空；随后HTML run `x7QXHaEtmLSqYbx4b`仍只取得元数据。诊断并读取Actor输入schema后，将`htmlTransformer=none`、`removeElementsCssSelector=dummy_keep_everything`保留GitHub嵌入JSON，run **hnCi4zEJVbrch0N3y** / dataset **ht7eRZxfcgPj9dhLd**取得`cmod_battery.cpp`真实`rawLines`和提交ID；再用固定提交URL，run **C8OmjYTo6oPY5ZRgz** / dataset **3IvYZBOpFVd0wrlv1**取得其余5个官方源文件。全程未绕开Apify、未输出/保存令牌、未创建新raw目录；没有把抓取成功计数当源码已取得。

实际使用的新源码为`cmod_battery.cpp`、`cmod_battery_stateful.cpp`、`lib_battery_powerflow.cpp`、`lib_battery_dispatch.cpp`与`lib_shared_inverter.cpp`，固定提交均为上文`c92cbf05…`。可在上述dataset从保留的GitHub嵌入JSON提取`rawLines`复核；其中Stateful/powerflow/dispatch/shared-inverter按`"\n".join(rawLines)+"\n"`的UTF-8 SHA256依次为`6fff3319311f2846e4f25c9cd801f99ec71eedda2a241d621dabb4519d5648fa`、`e6e0b52a8eeb994be84c782588c2adbb64b3c62033582c2daace2dcc57a05c99`、`18bbdb9523b70e4b3bb614c3b01ef235e37d19b64edfae97640c42707a0093c6`、`439d1757242412fbf17301279303671d3e6a82053087ba794a99ed60a5333f64`。

本节已证：官方Python入口/参数/端口单位、通用Battery拒绝DC、Stateful分工与源码时间/结构边界、SSC共享逆变器母线结构、本地既有库实际版本与默认值。尚未声称完成：本站DC执行器、Stateful适配器、真实SKU效率拟合、年度一致性、厂商EMS可执行性或线上验收。主线可直接按§12.2–12.3实现，验收仅追加能区分新DC域的代表用例，其他既有有效覆盖继续复用。
