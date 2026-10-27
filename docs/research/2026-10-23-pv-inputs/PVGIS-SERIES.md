# PVGIS seriescalc：真实原件与纯适配器合同

2026-10-23。范围仅为具名 PVGIS 场景输入、原始响应、时间及计量转换；不证明具体设备、屋顶遮挡、全欧洲工程精度或电气合规。承接 `2026-10-22-planning-implementation/NUMERICAL-MODELS.md` §4、§11，不替代后续 pvlib 详细链。

**已取得两份官方 `api/v5_3/seriescalc` 完整原件**：公开 Berlin 市中心坐标、2020 闰年、同一固定阵列，分别使用 ERA5 与 SARAH3。原件来自成功的 Apify 文件记录，按字节保存，没有反序列化再输出；浏览器只读可见 JSON 另行核对了相同配置及首末时戳。此前的 robots 跳过、HTTP 200 拒绝页、Actor 权限/输入限制均如实保留，没有扩大账户权限。

## 1. 直接可用于适配器的两个样本

| 项目 | ERA5 | SARAH3 |
|---|---|---|
| 原件 | [era5-berlin-2020.seriescalc.json](raw/era5-berlin-2020.seriescalc.json) | [sarah3-berlin-2020.seriescalc.json](raw/sarah3-berlin-2020.seriescalc.json) |
| 字节数 | 1,057,449 | 1,054,883 |
| SHA-256 | `9c0b24cf9828cac4c118c4695922fcbbb7aa7213ae80350019f67e00e5eaf6ca` | `bfaeeebf8257067e90e9571551d8b31063ce8d5e6277f1ab81e6ab953369af39` |
| 实测行数 / 唯一时戳 | 8,784 / 8,784 | 8,784 / 8,784 |
| 第一 / 最后原始时戳 | `20200101:0030` / `20201231:2330` | `20200101:0011` / `20201231:2311` |
| 所有相邻差 / 闰日 | 3,600 秒 / 24 行 | 3,600 秒 / 24 行 |
| 所有分钟字段 | `30` | `11`，仅是此地点此请求的观察 |
| `Int` 实测分布 | 8,784 个 `0.0` | 8,784 个 `0.0` |
| `P` 最小 / 最大 | 0 / 727.73 W | 0 / 779.24 W |

以上是对两份原件的本地确定性核验；完整统计和输入/单位元数据见 [sample-validation.json](raw/sample-validation.json)。成功 Apify run 为 `1hHNy9TJqSLGv9hq4`，dataset `nxhnqERgOKXBC80f5`，key-value store `WRudj2UjhIKNA4f6D`；原始 provider URL、实际 loaded URL、抓取 UTC 时间、record 路径、长度和 hash 见 [sample-provenance.json](raw/sample-provenance.json)。该 run 明确使用 API 客户端 User-Agent，保存 `application/json`；不能由此断言 User-Agent 是排除拒绝的唯一原因，因为没有控制代理出口 IP。

两个响应均回显：`latitude=52.52`、`longitude=13.405`、`elevation=37 m`、`meteo_db=ERA5`、`year_min=year_max=2020`、`use_horizon=true`、`horizon_data=DEM-calculated`、固定 `slope.value=10`、`azimuth.value=0`、两个 optimal 标志为 false、`type=free-standing`、`technology=c-Si`、`peak_power=1 kW`、`system_loss=14 %`。其区别是 `radiation_db` 分别为 `PVGIS-ERA5` 和 `PVGIS-SARAH3`。这些是响应中实际值，不是从请求补出来的元数据。

**危险的真实兼容点：两个响应的 `meta.outputs.hourly.timestamp` 都写 `hourly averages`。** SARAH3 实际为 `HH:11`。因此，不能仅凭这个泛化字符串把 SARAH3 导入为有保证的小时均值；必须结合明确数据库和该数据库的方法证据。JRC 手册 §9.3 区分 SARAH 影像时点采样与 ERA5 小时平均；虽然首段点名 SARAH1/2，后文讨论 SARAH 数据库的影像时刻随位置变化。本适配器对 SARAH3 保守保留时点语义，不凭响应模板升级为均值。[JRC 手册 §9.3](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)

## 2. 请求及响应身份

生产适配器显式使用 `https://re.jrc.ec.europa.eu/api/v5_3/seriescalc`，不使用随默认版本变化的 `/api/seriescalc`。JRC 文档允许版本入口和 GET；该文档显示的 5.3 链接文字与实际 href 还存在 5.1 不一致，故应固定并保存真正请求的 URL，不能盲从 href。响应没有独立的服务构建号；URL 版本不能冒充已知后端构建或保证重新请求永远字节相同。[JRC API §1.1–1.2](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en)

本次两个完整请求的全部参数存在 [request-manifest.json](raw/request-manifest.json)，其共同值为：

```text
lat=52.52, lon=13.405, startyear=2020, endyear=2020
pvcalculation=1, peakpower=1, loss=14, pvtechchoice=crystSi
mountingplace=free, angle=10, aspect=0, trackingtype=0
usehorizon=1, components=1, optimalinclination=0, optimalangles=0
outputformat=json
raddatabase=PVGIS-ERA5 或 PVGIS-SARAH3
```

参数含义及转换必须固定如下，而非从站点类型猜测：[JRC API §2.5](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en)

| 字段 | 可编码合同 |
|---|---|
| `lat` / `lon` | 十进制度，北/东为正；本次使用公开城市坐标。原始请求与回显均保存。 |
| `startyear` / `endyear` | 包含首尾的明确日历年，不能省略而让提供者自动选择全部年份。 |
| `raddatabase` | 明确数据库；无覆盖/不支持时返回失败，不偷偷换库。 |
| `peakpower` / `pvcalculation` | `seriescalc` 的峰值输入为 kW；要 `P` 必须请求 `pvcalculation=1`。不要把同文档中离网工具的 W 套进这里。 |
| `loss` | 明确百分比，保存依据及响应值；本样本 14% 是具名通用场景假设，不是每个 SKU 的实测损耗。 |
| `angle` / `aspect` | 角度相对水平面；PVGIS 方位南=0、东=-90、西=90。域内北=0 顺时针方位用 `aspect=azimuth_north_clockwise−180`，保留请求与实际回显；北向不得静默作 1° clamp 或放宽容差，见下方真实边界探针。 |
| `trackingtype` / optimal 字段 | 此合同只支持 `0` 固定阵列，两个 optimal 字段明确为 0；不能把真实屋面姿态替换成最优姿态。 |
| `mountingplace` | `free` 是背面通风的独立支架，`building` 是建筑集成；不能只由 roof/commercial 标签自动选择。中间安装条件本身有模型边界。 |
| `usehorizon` / `userhorizon` | 本样本使用提供者 DEM horizon；自定义 horizon 一旦启用必须保存完整向量、角度顺序及 hash，不能只保留 true。 |
| `components` / `outputformat` | 本次为组件辐照字段和 JSON。保留请求；响应实际字段仍须检查，不假设参数成功。 |

`inputs` 与 `meta` 是两种不同内容：前者是计算实际输入回显，后者主要是字段说明。必须保留完整根对象，避免只保存 `outputs.hourly` 而丢掉身份、单位及数据来源。响应归一化要采用具名版本映射：本次 `crystSi → c-Si`，`free → free-standing`；不能用请求字符串与响应字符串直接相等，也不能任意模糊匹配。pvlib 0.16.1 的 JSON 解析器同样把实际 `inputs` 放进 metadata，并单独保留描述。[pvlib 0.16.1 原始解析器](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/iotools/pvgis.py#L247-L259)

为避免猜测其余映射，补做同一 Berlin/2020 ERA5 的 4 个实际 `seriescalc` 请求（run `HFCHIVy161ErUxfkV` / dataset `2Gu9QL16ONyztUcNE`）。均收到正常 JSON 和 8,784 行 hourly，但 **Unknown 没有返回 P，不能称全部技术都已产出系统功率**。本地只保存元数据及完整原文 hash，未复制另一批全年文件。精确请求、所有实际 inputs/meta、原文长度/hash、Apify record 和后续逐字段能力复核见 [technology-mapping-probes.json](raw/technology-mapping-probes.json)。可验证的标签映射如下：

| 请求 | 实际响应 |
|---|---|
| `pvtechchoice=crystSi` | `inputs.pv_module.technology=c-Si`（完整 ERA5/SARAH3 原件） |
| `pvtechchoice=crystSi2025` | `technology=c-Si2025` |
| `pvtechchoice=CIS` | `technology=CIS` |
| `pvtechchoice=CdTe` | `technology=CdTe` |
| `pvtechchoice=Unknown` | `technology=Unknown type`；仅确认标签，本次无 `P`，不得用于系统输出 |
| `mountingplace=free` | `inputs.mounting_system.fixed.type=free-standing` |
| `mountingplace=building` | `fixed.type=building-integrated`（与 crystSi2025 同一探针） |

**映射不等于输出能力。** 先前标签探针只确认标签和行数，未充分验证 P 能力；补充核验重新读取同一个 Unknown Apify 原件，SHA 仍为 `c38933f99d34b4f723f3879cd6544d26fbd8e1ce4135aadc149a9bad45ff9c08`，长度 956,061 字节：请求确实含 `pvcalculation=1`，实际 HTTP 200 / application/json，根对象只有 `inputs/outputs/meta`，没有 `error/message/status` 解释；但 8,784 行全部没有 `P`，meta 也没有 `P` 或其 W 单位。`inputs.pv_module` 虽回显 `Unknown type / peak_power=1 / system_loss=14`，不能证明执行过 PV 计算。事实上四个补充技术响应都没有回显 `pvcalculation` flag，必须用请求加实际输出共同验证。[Unknown 原件复核摘要](raw/unknown-output-capability.json)

Unknown 的 `T2m` 和 `WS10m` 还各有 8,784 个零，全年最小值和最大值均为 0；辐照/太阳高度字段存在。这些零不能因 `meteo_db=ERA5` 就当作已验证的气象量导入详细 pvlib。其余三个补充技术原件重新匹配各自原始 hash 后，均有 8,784 个有限 `P` 且 meta 单位为 W，`T2m` 为 −4.54 至 35.09°C，`WS10m` 为 0.07 至 10.21m/s。逐字段统计已写入 `capabilityAudit`；这里的可用性仅指对应响应具备 P/单位，仍须经过完整适配器身份及时间校验。[逐字段能力证据](raw/technology-mapping-probes.json)

JRC API §2.5 虽把 `Unknown` 列为可选参数，本次原件没有说明缺 P 的内部原因，现有证据不足以断言具体 provider bug 或替它设计修复。适配器应显式拒绝这份无 P 响应进入系统输出，不补零、不借别的技术的 P/单位，也不把其气象零值转入详细链。该标签白名单只处理回显规范化，不授予系统输出能力，更不证明某技术模型适合任意实售组件。[JRC API §2.5](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en)

建议冻结的最小依赖为：`request/providerURL+parameters`、`responseBodySHA256`、原始响应 artifact、提供者版本 URL、radiation/meteo 数据库、年份、实际几何/峰值/损耗/技术/安装/地平线策略、单位、时间语义版本及其依据、adapter 版本。运行重现读取冻结响应，不重新访问当前 API 再冒充原运行；换库、换年份或重抓是新的输入版本。

接受前逐项比较请求与实际回显；地点、数据库、年份、倾角/方位、optimal 标志、固定安装类型、技术、峰值、loss、horizon 任一不匹配即拒绝。不存在的回显字段不能填成“已验证”：保存请求值并注明是否由响应证实；特别是完整自定义 horizon 或后端构建号，不能凭空补齐。响应允许额外字段，例如本次 `horizon_db=null` 但有 `horizon_data=DEM-calculated`；不要把该合法新字段组合当成未使用 horizon。

**北向与 horizon=false 的真实边界探针：** 同一 Berlin/2020 ERA5、crystSi/free，只将 `aspect=-180`、`usehorizon=0` 显式改动，run `CegW8eplqlh9xVMEf` / dataset `4cCfnhhlEuEnbwhVC`。请求返回 8,784 行且每行有 P、meta P 单位为 W，但 `inputs.mounting_system.fixed.azimuth.value=-179`、`optimal=false`，与请求有 1° 真实几何错配，**严格适配器必须拒绝它代表请求的精确北向场景**。不能把 −179 当作 −180 的同义标签、浮点误差或已证实支持的北向；本探针没有验证 `aspect=+180` 的行为，也未查明 provider 改值的内部原因。[north-nohorizon-probe.json](raw/north-nohorizon-probe.json)

同一响应 `inputs.meteo_data.use_horizon=false`、`horizon_db=null`，且 `horizon_data` 字段不存在；有 horizon 的两个核心原件则是 `use_horizon=true`、`horizon_db=null`、`horizon_data=DEM-calculated`。因此 `horizon_db=null` 单独无法判断是否使用地平线；应验证布尔值，并允许已关闭时不返回 `horizon_data`。该边界原文 1,056,353 字节、SHA `6007f9af37e15e3685c8f286e5f51d49ef22726af78a5ee7657b2f80abc41cd3`，本地保存完整 inputs/meta、请求、原文 hash 与 Apify record，未另存全年正文。[北向/无地平线原始回显](raw/north-nohorizon-probe.json)

## 3. 时间与计量的精确转换

原始 `time` 形如 `YYYYMMDD:HHMM`，**没有 `Z` 或偏移后缀**。pvlib 原始 JSON 解析明确用该格式并赋 UTC；本适配器应同样保存原字符串、解析为 UTC，然后才为显示转换地点时区。不得把它先当 Europe/Berlin 本地时间，因此不引入 DST 重复/缺失小时。[pvlib 0.16.1 解析器 L247–259](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/iotools/pvgis.py#L247-L259)

**ERA5：** JRC 规定其辐照和其他气象量为小时均值，时戳在 HH:30。适配器采用此具名 PVGIS 场景的小时输出合同：中心 `t` 对应半开 UTC 区间 `[t−1800s, t+1800s)`，源功率 `P_W` 转 `mean_kW=P_W/1000`，区间能量为 `mean_kW × 1h`。本原件的完整区间恰为 `[2020-01-01T00:00Z, 2021-01-01T00:00Z)`，8,784 小时；精确十进制相加为 946.43692 kWh。该数是这份 1 kWp、14% loss 场景模型的年积分，不能称客户计量或电气系统验收结果。[JRC 手册 §9.3、§4](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)；[本次验证](raw/sample-validation.json)

**SARAH3：** 保存 `HH:11` 原始 UTC 时点及全部 `P`、辐照、气象、`Int`；本合同不直接产出有来源保证的 `interval_mean` PowerSeries。JRC 说明 SARAH 来自所选影像时刻，确切分钟取决于位置，气象量则来自对应小时的再分析。**官方确实采用“把该瞬时辐照假设为该小时的代表平均值”的近似**，因此有可复用的小时场景估算先例；它仍不是测得的小时平均，也没有恢复小时内变化。[JRC 手册 §9.3](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)

实现可以选择显式、版本化的 `sample_value_over_containing_utc_hour_v1`：将采样功率作为包含其 UTC 时点的 `[floor_hour(t), floor_hour(t)+1h)` 的估算常值，保留原时点、估算依据、重建标记及有效一小时精度。本 Berlin `HH:11` 样本可在该定义下完整覆盖 2020；`sum(P)/1000 × 1h` 为 979.72921 kWh，只有采用此假设后才能称该重建场景的能量。**这个 floor/半开区间选择是产品的可审核建模策略，不是 JRC 明文指定的通用时间合同。** §9.2 仅说明输出格式，§9.3 没有给“对应小时”的数学端点，且提到 Meteosat Eastern 可在整点前约 20 分钟成像。因此不能声称所有地点的 `:40` 都经官方证明属于 floor 后的小时；未来其他时相/地区需要独立核对或明确标注该策略的适用假设，不能偷偷套 ERA5 ±30min。`Int=0` 不会取消这种时间重建。[JRC 手册 §9.2–9.3](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)

`Int` 是提供者的太阳辐射重建指示，响应说明 1 代表辐射值被重建；它与我们把小时值铺到 15 分钟的时间重建是两件事。本次 JSON 使用 `0.0`，不是必须写成整数 token；接受可精确归一化为 0/1 的有限数值，拒绝 0.5、布尔或缺失，保存原值及每行质量标志。不因列名猜成积分量、也不先丢掉再声称“全为原始观测”。[本次 response meta](raw/era5-berlin-2020.seriescalc.json)；[pvlib 0.16.1 对 Int 的定义及类型处理](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/iotools/pvgis.py#L169-L181)

更细轴只能作明确重建。ERA5 1h → 15min 分段常值可保持总能量，但必须记录源 3,600 秒分辨率、变换输入/轴 hash、重建标记及有效最粗分辨率；不得据此宣称有 15min 云影变化、峰值或保证削峰效果。它与已有时间模块的中间精度历史合同一致。

## 4. 输出系统边界

`meta.outputs.hourly.variables.P.units` 在两个原件中都是 `W`；峰值输入单位是 `kW`。JRC 把 PV 输出定义为系统最终输出，通常为 AC，并已计入系统损耗。故该路径命名为 **PVGIS 场景的系统输出估算**：不能把 `P` 当裸 DC 再跑一遍模块温度/逆变器效率/同一 loss；也不能用这个估算去证明已选逆变器、MPPT、电池或 PCS 的实际曲线和限值已经被建模。[JRC 手册 §4](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)；[响应单位](raw/sample-validation.json)

官方 FAQ 还明确不同损失依次乘在剩余量上，而不是把温度/入射/系统损耗百分比直接相加。14% 也不等于该模型总损失只有 14%；适配器展示应区分用户输入的 system loss 与提供者内部已经计算的温度、辐照和光学效应。[JRC FAQ：损失为何不相加](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/frequently-asked-questions_en)

倾角/方位来自实际阵列姿态；多姿态阵列需要独立具名场景并在共同时间合同下组合，不能把面积平均的倾角/方位伪装成实际阵列。DEM 地平线不等于烟囱、树、邻楼、行间遮挡或真实组件布局；通风安装的二分选择也不等于所有屋顶热条件。详细路线仍需 geometry/array/shading → irradiance → temperature → DC → selected inverter/AC，及设备原件和验证基准；与已含 loss 的 PVGIS `P` 路线保持可替换而清楚的边界。[JRC 手册 §2、§4、§9](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)

## 5. 失败必须明确，缺值不补成生产量

纯适配器应拒绝以下状态；运输层与模型层分开返回有上下文的领域错误：

1. HTTP 非成功；或 HTTP 200 但 Content-Type/正文是 HTML、拒绝页、截断文本、非法 JSON。不能只用状态码判成功。本次确有前两轮 200/text/html 拒绝页，见 [seriescalc-api-crawl-items.json](raw/seriescalc-api-crawl-items.json)、[seriescalc-de-proxy-items.json](raw/seriescalc-de-proxy-items.json)。
2. JSON 错误对象而非 `inputs/outputs.hourly/meta`；缺少 `P`/单位，或 P 单位非 W；未知数据库/未知时间语义；实际输入身份错配。只读 radiation 的请求没有 P 是另一类输入，不能填零冒充 PV。
3. 无效/重复/乱序时戳、不是完整连续小时、范围与明确年份不符；ERA5 中心非 `:30`；预期闰年 8,784 行却只有 8,760。除行数，还要核首末、每一步和闰日，避免等长错年、重复抵消缺行。不要靠行号从 Jan 1 重造时戳。
4. `P` 非有限数、负值或缺失，以及非法 Int。不得用 0、插值、截断负值掩盖输入异常。不要笼统加 `P ≤ peakpower×1000` 作为电气有效性证明：这个 PVGIS 路线没有所选逆变器合同，本样本最大值不能提供通用电气限幅规则。
5. 请求超出数据库覆盖/年份，或 API 版本不支持。禁止自行换 ERA5、最近城市、当前默认版本或别的年份；返回用户可辨识的来源失败并保留原文/hash，供显式重新选择来源。

官方支持服务端 GET 集成，不允许把浏览器 AJAX 当集成入口；429 与 529 分别表示限流和计算过载。运行时需要受限并发、超时、有限重试及显式失败，不把网页抓取或此研究用 Apify 当生产适配器架构。[JRC API §1.1–1.5](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en)

另已在当前 5.3 请求 `endyear=2030`、SARAH3 `lat=89`，并用不存在的 `v5_99` 作版本负例；run `zawK3MY4xD1ZWftLF` / dataset `DByU4U1Rm3D42CWT1`。此次通用 Actor 把三者都终止为 `navigation: Download is starting`，dataset 为空，KVS 没有 provider error body。因此这里只证明负例抓取未完成，**没有观察到可断言的 provider HTTP 状态或错误 JSON**；不得把 Actor 的统一错误写成 JRC 的 400/404/覆盖判定。[negative 输入](raw/seriescalc-negative-input.json) / [原始 Actor 日志](raw/seriescalc-negative-log.txt)

## 6. 许可、归属及长期原文保存

JRC 的 PVGIS 专属使用条件 §1 明确其提供的信息免费、用途不受限制；手册开头也明确结果用途不限且无需注册。因此可采用服务器获取并保存完整公开结果的方案，**无需把已下载结果在短 TTL 后丢弃**。本次检查的专属条件、手册与 API 文档没有规定缓存 TTL、强制重取或到期删除。[PVGIS Usage Conditions & Data Protection §1](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/usage-conditions-data-protection_en)；[手册简介](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en)

“以 content hash 长期冻结已返回原文供重现”是基于上述用途授权的工程采用方式；原文没有单列一个缓存服务条款或永久可用 SLA，不能虚构官方特别认证了我们的缓存架构。新请求/用户主动刷新另建新 artifact，既有运行继续指向原件。源响应自带的 location 信息仍受项目隐私和访问控制约束；本次可提交公开 fixture 的原因是坐标公开且不属于客户项目，不代表客户位置也应进入公开 feed。

欧委会官方通用版权说明另规定：除另有说明，属于 EU 的网站内容按 CC BY 4.0 重用，应注明来源和修改，第三方内容、软件及工业产权等有例外。应保留出处与变换记录，不把这段通用说明扩张成原始 ERA5/CM SAF 底层数据库、卫星图像、logo 或第三方材料的统一再许可。[European Commission legal notice：Copyright notice](https://commission.europa.eu/legal-notice_en)

报告/来源面板建议保存并显示 `European Commission, Joint Research Centre — PVGIS 5.3`、明确的 radiation/meteo 数据库、来源 URL、获取 UTC 日期、原请求及响应 SHA、adapter/时间策略版本和实际变更（如 W→kW、ERA5 中心→区间、SARAH 重建策略）。这是可溯源实施建议，不冒称专属条款强制使用这一固定句式。PVGIS 专属免责声明说明其输出不必代表欧委会立场、使用责任由使用者承担；界面不能宣称欧委会认可我们设备选型或项目工程。[PVGIS 使用条件 §3](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/usage-conditions-data-protection_en)

专属条件已由本次 Apify run `qWk6KyO25MLjsToZ9` / dataset `5293hgWSwijAUoFF0` 保存为 [official-pvgis-usage-conditions.md](raw/official-pvgis-usage-conditions.md)，SHA `067585a8c5f8460db25ff9d5277d8ba0beac4dc3dad2d6ca61e34b2ded90a408`；通用说明由 run `9r9hb3YVpi6U5hb8x` / dataset `Hauh42KS1qROt8cfo` 保存为 [official-commission-legal.md](raw/official-commission-legal.md)，SHA `889ce104d0f36ca205ebf857067d86a9000021e6a93cd798a0445a59ce82ca5a`。这些是网页正文抽取，精确来源/loaded URL/hash 见 raw `terms-provenance.json`、`license-provenance.json`。

## 7. 来源与验证状态

| 来源 | 实际获取和本地证据 |
|---|---|
| [JRC 用户手册](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en) | 复用此前 Apify dataset `fIWOSxRwJ0sVhgUVk` 原文抽取；本地 [official-user-manual.md](raw/official-user-manual.md)，SHA `30e1e48b6459b820d5e1bd93f65ddbf3e6f24734c694de4b59fd0b8e069e5d31`。这份是网页 markdown 抽取，不能冒充 provider 原始字节。 |
| [JRC API 文档](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en) | 复用此前 run `7MOtn1UhYhSXuaK5b` / dataset `Z44vSQlt8cWdoUnW5`；本地 [official-api-doc.md](raw/official-api-doc.md)，SHA `bad9781329a5b8534d112df7c6fd258f3d4a8d918fb41992be4498899682b561`。|
| [pvlib v0.16.1 原始解析代码](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/iotools/pvgis.py) | 本次 Apify run `lKsXFcOgWBdNett22` / dataset `ok1OASYOkvTHzMlhm` 原始文件记录，保存 [pvlib-pvgis.py](raw/pvlib-pvgis.py)，SHA `c00a047d2d2b16a100f7f0403260a4aeeb9feef9c33ca153c652553c3e689a0e`；UTC、方位、Int 依据均可查其原代码。其 Git tree/blob 身份另见 raw provenance。 |
| 两个完整 seriescalc JSON | 本次成功 run `1hHNy9TJqSLGv9hq4`，两个原件及 [sample-provenance.json](raw/sample-provenance.json)；此处是 exact Apify file record bytes，不是网页叙述或手写 fixture。 |
| 独立浏览器读回 | 自建 Chrome tab `329395485`，公开官方 API 可见 JSON，同样 8,784 行；完成后只关闭该研究 tab。[browser-observation.json](raw/browser-observation.json) 记录观察与未成功的附件事件；没有用隐藏状态、第三方 key 或扩大权限。 |

本次 [PVGIS 官方主页](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en) 仍将 5.3 标为生产版本，另列 6 为测试 beta、其数据至 2024；这进一步说明不能从“新版本”推断本次具名 5.3 请求应自动升级。网页文档仍有旧数据库名称/范围段落，手册展示 ERA5/SARAH3 至 2023，不能当“所有地点当前最新可用年”的自动权威。

两个 Berlin/2020 成功样本只证明这两个明确请求可达和格式/计量合同；不能证明所有欧洲地点、国家设备、安装方式、当期全部年份或所有异常响应已覆盖。实现的验收仍需对上述拒绝条件、源 artifact 冻结及与负荷轴对齐做产品层测试；本研究没有修改产品代码，也没有声称产品适配器已执行通过。核验已完成：原件 SHA/JSON 结构、8,784 个唯一时戳、全部相邻步长、首末范围、闰日、单位/场景回显及 4 个标签探针；所有本地 JSON 可解析，文档本地链接存在，记录中不保留凭证或签名查询。
