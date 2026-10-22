# 可取得的真实光伏设计软件、项目格式与源码复用边界

2026-10-22，Codex。范围：取得真实软件和原始项目，核实公开源码、许可、接口与可运行条件。没有安装软件、运行下载源码、注册账号、授权新Actor、接受试用合同或修改业务实现；没有另造原型。外部取证均经Apify，实际软件操作由协调者另行执行。

**已经拿到可研究的软件，而不只是介绍页：Aladdin公开仓库的固定版本完整源码ZIP已下载到本机，1,168个跟踪文件与Git树逐一核对一致；完整MIT许可和四个官方JSON样例已入库。** 协调者已在官方浏览器应用打开真实项目、运行分析并导出`.ala`及CSV。它适合研究三维场景、屋面/阵列编辑和可视化计算；本轮核出的代表日外推方法不具备全年时序或欧洲设备选型的验收证明。

## 1. 已取得什么，实际做到哪一层

| 软件或材料 | 本轮实际证据 | 可用角色及边界 |
| --- | --- | --- |
| Aladdin官方浏览器应用 | [仓库README给出的应用](https://institute-for-future-intelligence.github.io/aladdin/)；协调者实际打开、分析、保存项目和CSV | 完整CAD/CAE界面参照。不是pvlib这类计算库，也不是本研究自写demo；它的模型、设备与工程适用性仍须验证 |
| Aladdin固定源码 | [公开提交7b939ab](https://github.com/Institute-for-Future-Intelligence/aladdin/commit/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa)，完整ZIP已回读到本机 | 可以阅读和依法修改；未构建或执行，不能称本地运行已通过 |
| Aladdin原生项目 | 四个仓库原始JSON；本地读写源码；协调者实际`.ala`和CSV | 可以核对状态、几何、参数与输出。旧样例会依赖默认展开和版本迁移，不能把字段缺失解释成0 |
| archelios PRO及其交接 | 官方产品矩阵明确导入/导出方向；实际账号与界面由协调者负责 | 成熟闭源流程参照。公开导出能力不等于有开放设计内核、通用API或白标许可 |
| SAM桌面应用/SDK | 官方下载、源码、许可证、文件菜单、SDK原文 | 完整桌面仿真及可编程接口参照；不是屋顶自动排布、全厂商配对和欧洲电气审查的等价物 |
| OpenSolar开发门户 | 官方门户明确API、SDK、MCP入口 | 公开集成线索；本轮未验证授权、端点运行、嵌入许可或取得其设计内核源码 |

Aladdin机构官网自称experimental CAD/CAE平台，展示屋顶、立面、地面PV等设计。其建筑BESTEST介绍不构成光伏产量、逆变器选型或储能调度已经校验的证据。[机构介绍](https://intofuture.org/aladdin.html)、[光伏示例](https://intofuture.org/aladdin-pv.html)。

## 2. Aladdin源码包、许可证及版本对应

- 固定源码提交：`7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa`，提交API记录时间`2026-04-28T16:27:36Z`，见[提交记录](raw/aladdin-commit-metadata.json)。
- [官方完整ZIP下载](https://codeload.github.com/Institute-for-Future-Intelligence/aladdin/zip/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa)。本机实物：[源码ZIP](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-calculation-550/docs/research/2026-10-22-trace-software-access/reusable/raw/aladdin-7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa.zip)。
- ZIP为25,329,681字节，SHA256：`1441ac0f978a12d2930d390e22c195b338f35cb64bb8005e3aacd6f437bfb40a`。解压后跟踪内容36,431,786字节、1,168个文件；缺失、额外和Git blob哈希不匹配均为0。只在内存读ZIP条目核对，没有解压或执行。ZIP留本机，不把25MB二进制重复提交；[归档核对记录](raw/aladdin-archive-manifest.json)与[完整公开树](raw/aladdin-tree.json)入库。
- [完整MIT许可](raw/aladdin-LICENSE.txt)已原样回读，1090字节，SHA256：`fce4189743362fb435286d656f72ea761d1b332517ddc53740a9074279772e38`。许可允许使用、修改与分发，要求保留版权及许可文本，也明确不提供软件适用性保证。这不自动覆盖外部地图、云服务、第三方依赖或厂商资料的独立条件。[固定许可原件](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/LICENSE)。

**不能称已经拿到线上同版源码。** 固定源码`src/constants.ts:26`为`VERSION='2.0.6'`，`package.json`却仍写1.7.5；协调者实际应用和实际导出的项目均为2.0.7。四个仓库样例内的文件版本又是1.8.9。包元数据、应用版本、文件版本是三个不同字段；本轮没有取得并运行2.0.7部署代码。[源码常量](raw/aladdin-source-src__constants.ts)、[包元数据](raw/aladdin-package.json)、[实际导出核对](raw/aladdin-live-export-check.json)。

源码包是完整**跟踪源码**，不含已安装依赖、Git历史、外部服务凭据或线上后端数据。包中明确存在React18、Three、Zustand、Vite、Firebase、地图和其他依赖，不能把下载ZIP说成完整离线运行环境。[固定package.json](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/package.json)。

本机为arm64/macOS26.6.2。浏览器应用无需本机安装这套依赖；源码本机构建尚未执行。已准备的隔离运行路线是：固定ZIP及许可→独立解压目录→先核锁文件和安装脚本→该目录独立依赖→以本机回环地址运行Vite；源码`start=vite`、`build=vite build`，有`yarn.lock`，并有`postinstall=husky install`，所以本次没有以“只是准备”为名执行安装脚本。Vite配置有`/aladdin`基路径；云保存/地图等外部功能须另核，不制造默认密钥或假数据。[Vite原件](raw/aladdin-source-vite.config.ts)。

## 3. 原生格式与可以直接研究的样例

`src/localFileManager.tsx:127–145`用FileReader读文字、JSON.parse后调用importContent；`:158–162`保存时加`.ala`扩展名，用JSON.stringify(exportContent())和application/json写出。**浏览器版`.ala`是JSON内容；机构网站`/jaladdin/models/*.ald`不应当成此版浏览器JSON格式。** 本轮没有声称`.ald`可导入。[固定读写实现](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/localFileManager.tsx)、[回读副本](raw/aladdin-source-src__localFileManager.tsx)。

| 官方仓库样例 | 已回读原件 | 内容用途 | SHA256 |
| --- | --- | --- | --- |
| [rooftop_solar_panels.json](https://raw.githubusercontent.com/Institute-for-Future-Intelligence/aladdin/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/examples/rooftop_solar_panels.json) | [JSON](raw/aladdin-example-rooftop_solar_panels.json) · [同字节.ala](raw/aladdin-example-rooftop_solar_panels.ala) | 同屋顶四朝向的官方例子 | `41cc3b8409231642eb8e3fbc13058a9494b6367ee64730b8f849904b073e4956` |
| [solar_panel_array_auto_layout.json](https://raw.githubusercontent.com/Institute-for-Future-Intelligence/aladdin/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/examples/solar_panel_array_auto_layout.json) | [JSON](raw/aladdin-example-solar_panel_array_auto_layout.json) · [同字节.ala](raw/aladdin-example-solar_panel_array_auto_layout.ala) | 区域与自动排布状态 | `f1692704d3193e0b0350de13d6dfeffe772c0e6a806617406b9a4c477c123f79` |
| [inter_row_spacing.json](https://raw.githubusercontent.com/Institute-for-Future-Intelligence/aladdin/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/examples/inter_row_spacing.json) | [JSON](raw/aladdin-example-inter_row_spacing.json) · [同字节.ala](raw/aladdin-example-inter_row_spacing.ala) | 排间距敏感性 | `92836bbf1b378614d6890945315caf7593dbbdb43da3efa447f40b3abb10cd62` |
| [home_solar_energy_storage.json](https://raw.githubusercontent.com/Institute-for-Future-Intelligence/aladdin/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/examples/home_solar_energy_storage.json) | [JSON](raw/aladdin-example-home_solar_energy_storage.json) · [同字节.ala](raw/aladdin-example-home_solar_energy_storage.ala) | 房屋/PV/储能的官方场景状态 | `1674d3da8fc9013a77f742af0551b7e1f6a8ffafc5da7b31408325884b804a51` |

四个原件都成功解析，且Git blob哈希与捕获树一致。[逐文件来源/哈希](raw/aladdin-native-manifest.json)。`.ala`别名只是同字节换扩展名，没有转换数据，也没有把它说成本研究者已实走导入通过；[别名记录](raw/aladdin-example-aliases.json)。官方例中原有dailyYield/yearlyYield属于保存的数据，不能冒作本轮新模拟结果。

项目包含world、elements、view、graphState、排布参数/约束、customPvModules等。elements是对象图，可能以一个Solar Panel对象代表一块面板组或阵列；不能把对象条数直接当实体组件片数。位置和normal/rotation/tilt等字段也有父对象关系，需要对应版本的模型和转换逻辑，不能仅凭字段名平移到新内核。

这提供了**可读写的原生项目实现和实际样例**，没有证明有稳定、公开支持的外部SDK、REST项目API或第三方嵌入合同。MIT允许研究和重构源码，不代表能把应用整体直接塞进WordPress。可优先研究仓库中的屋面/组件操作、参数检查器、撤销、排布向导和同场景可视化；具体目录已保存在完整树，模型正确性与第三方依赖另核。

## 4. 已深入核到的关键边界：年度PV结果是代表日外推

协调者在官方2.0.7界面真实操作Garage例子，并保存项目及结果；[4日结果截图](/Users/chesterjohn/Documents/de-linker-worktrees/research-trace-software-access/docs/research/2026-10-22-trace-software-access/coordinator/screens/aladdin-yearly-result.jpg)、[12日结果截图](/Users/chesterjohn/Documents/de-linker-worktrees/research-trace-software-access/docs/research/2026-10-22-trace-software-access/coordinator/screens/aladdin-yearly-result-12-days.jpg)。本研究对其导出文件做独立读回和算术核对，未执行下载的2.0.6源码。

### 4.1 实际输入和CSV/图的关系

| 同一官方例子的实际操作 | 导出证据与独立算核 | 能证明什么 |
| --- | --- | --- |
| 例子原有daysPerYear=4、timesPerHour=2 | CSV只有Jan/Apr/Jul/Oct四行，合计94,087.41243357198；图年总量282,262.24等于该合计×3后取两位 | 实际存在四个代表月及年外推，不是取得完整年时序 |
| 在界面改为12天并重算，timesPerHour仍2 | 已取得12行CSV，合计281,869.30259735853；约比4日外推低0.1392% | 此例对采样设置的敏感性；不是对真实电表、TMY或独立权威模型的精度验收 |

[4日导出核对](raw/aladdin-live-export-check.json)、[12日导出核对](raw/aladdin-live-twelve-day-check.json)固定了协调者文件路径和SHA；本研究不改这些原件。图和CSV采用不同的汇总层次，不能把四行CSV直接交给全年储能或15分钟削峰模型。

### 4.2 源码定位及公式

下述为已取得的**2.0.6固定源码**；它解释了2.0.7实际观察的×3关系，不证明两版全实现等价。

| 位置 | 实际逻辑及含义 |
| --- | --- |
| `constants.ts:250–251` | 全局fallback为timesPerHour=1、daysPerYear=12。**4天和每小时2次是此次厂商样例的显式设置，不是软件全局默认** |
| `solarPanelSimulation.tsx:89–92` | minuteInterval=60/timesPerHour；monthInterval=12/daysPerYear |
| `solarPanelSimulation.tsx:462–479` | 静态年度循环只取每个抽样月22日；4天时monthInterval=3，得到1/4/7/10月。动态路径`:439–450,571–575`同样跳到抽样月22日 |
| `solarPanelSimulation.tsx:118,588–598,618–655` | 代表日积分结合月日照权重，再乘daysInYear/12，形成CSV所见的代表月数据；并非逐实际月份天数逐日积分 |
| `yearlyPvYieldPanel.tsx:118–150,240–241` | 图年总量先对这些代表月求和，再乘yearScaleFactor=12/daysPerYear |
| `yearlyPvYieldPanel.tsx:538`及`helpers.tsx:200–213` | CSV直接写yearlyYield数组，没有把年总量外推权重一起写成额外字段 |
| `stores/commonData.ts:221–233` | 年汇总也采用相同12/daysPerYear权重 |

因此`Y_annual_estimate = (12 / n_sampled_days) × Σ representative_month_yield`。这是一条可核对的实现公式，**不宣称它是欧洲标准或经现场校准的公式**。[固定PV模拟源码](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/analysis/solarPanelSimulation.tsx)、[固定结果面板](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/panels/yearlyPvYieldPanel.tsx)、[已回读源码和哈希](raw/aladdin-sampling-source-manifest.json)。

12日重算后的`.ala`省略daysPerYear有明确源码原因：`common.ts:865–905`导出后压缩默认值；`contentUtil.ts:598–601`删除等于默认值的daysPerYear/timesPerHour等；`:668–671`导入时补回默认值。`common.ts:798–802`先展开再消费。所以缺字段不表示没有约定。做我们自己的不可变run时，必须保存**展开后的有效参数和该默认版本**，不能只有一个依赖软件未来默认值的短项目JSON。[固定压缩/展开实现](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/contentUtil.ts)。

### 4.3 天气从哪里进入，为什么不能称TMY全年时序

`hooks.tsx:17–18`按city取weather；`stores/common.ts:5167–5197`读取随软件发布的`resources/weather.csv`，解析城市坐标/海拔、12组最低/最高温和12个月日照小时。WeatherModel也是这些月数组，不是8760/35040记录。`solarPanelSimulation.tsx:1206–1208`使用`月日照小时 / (30 × 当日昼长小时 × timesPerHour)`权重；`:1217–1227`按月高低温构造日内温度；`sunTools.ts:108–140`另用太阳位置、气团与辐射模型。`:1211–1214`还乘面积、逆变器效率和月损失。

这些是已经追到源码和内置CSV的**实现输入**，不是已经追到每个气候数值的原始观测站、数据年份或可追溯TMY版本。该原始来源缺口保留。此次实际项目的dustLoss=0.05也不能直接认作唯一有效损失：2.0.6模拟用monthlyIrradianceLosses，缺失时为每月0.05，还另有逆变器效率；没有以一个旧字段推断整条2.0.7损失链。

[内置天气原件](raw/aladdin-source-src__resources__weather.csv)、[WeatherModel](raw/aladdin-source-src__models__WeatherModel.ts)、[天气读取](raw/aladdin-source-src__stores__common.ts)、[太阳辐射源码](raw/aladdin-source-src__analysis__sunTools.ts)均来自已核对ZIP。**可学习三维反馈与参数敏感性；该例及这种代表日结果不能直接作为全年连续SOC、15分钟峰值、备电续航或选型准确性的依据。**

## 5. archelios公开集成：已经有文件交接，尚未证明有可嵌入内核

[国际英文官方矩阵](https://www.trace-software.com/en/our-solutions/solar-pv-design-software/)本轮取得完整正文，明确列出：Sunny Design/K2 Base项目导入；Silver到elec calc/archelios CALC的partial项目导出；Gold的完整交接、PDF/CSV、3D DXF、GeoJSON、KML；Platinum的3E天气API导入。[本轮正文](raw/access-01.md)。这些是产品页对相应版本的声称，本研究没有取得账户中实际导出的所有格式或其schema。

- **可实际研究的接口方向**：中性几何格式可能帮助对照位置/轮廓，CSV/PDF帮助对照结果；PRO→电气工具是现成的交接模式。不能由“GeoJSON”三个字推导它包含电池、MPPT、全部假设或足够重建整套项目。
- **API方向要分清**：[3E官方合作公告](https://www.3e.eu/resources/news/trace-software-partnership-3e-solar-irradiation-data-compatible-with-archelios-pro)说的是3E天气服务被archelios调用，不是archelios给第三方提供通用设计API。
- **公开SDK/白标/embed**：本轮找到的公开材料不足以确认其授权、合同或接口规格；也没有取得设计内核源码。不能据此断言厂商没有合作接口；若要采用，应索取明确的集成授权及样例合同。
- **旧CALC与新elec calc SOLAR分开**：旧FAQ的`.arc_sol`只在搜索结果出现；本轮抓FAQ正文仅得到框架，未把搜索片段升格为已核格式。协调者另发现[当前中国站elec calc SOLAR](https://tracesoftware.cn/products-2/software-for-sizing-elec-calc-solar/)；不能把旧CALC的扩展名当作新产品公开规范。
- **地区/版本差异保留**：本轮国际英文矩阵Free写9kWp；协调者中国站[Free页面](https://tracesoftware.cn/archelios-pro/free-pv-design-software/#freeversion)观察为36kWp。两条不同页面声称不能合成一个全局免费额度；以实际地区、账户和功能实走核定。本研究没有购买或接受订阅。

archelios适合学习完整工作流和输出证据，尚无依据把其闭源内核当作可复用代码，或在未运行同输入对照前把其结果叫准确度基准。

## 6. 另外两条真实路线：SAM桌面和OpenSolar集成

[SAM官方开源说明](https://sam.nlr.gov/sam-open-source.html)与[完整仓库](https://github.com/NatLabRockies/SAM)明确区分完整桌面UI和SSC计算库：前者负责输入、模块顺序、结果和三维遮挡工具，后者是模型内核。主体BSD-3-Clause，仓库还列明Sandia的LGPL部分；复用时不能笼统说所有组件只有一种许可。[回读许可](raw/sam-LICENSE.txt)。

[官方当前下载页](https://sam.nlr.gov/download.html)提供2026.7.3/SSC308的Mac/Win/Linux版，首次运行需邮箱注册免费key；本研究没有替用户注册。[官方Mac构建说明](https://github.com/NatLabRockies/SAM/wiki/Mac-Build-Instructions)说明Apple Silicon/Intel路线及多仓库依赖，也区分SAMOS公开构建与含部分线上服务集成的official/private构建。本轮未安装SAM桌面。

[SAM文件菜单](https://samrepo.nlr.gov/help/file_menu.html)有原生`.sam`、案例导入和输入CSV；[官方SDK](https://sam.nlr.gov/software-development-kit-sdk.html)有SSC C接口、LK及按实际案例生成JSON/PySAM JSON/程序的路径。它是本地可编程库，不因有API一词就成为托管web设计服务。本轮仅核取得方式与接口，没有重复此前PySAM算例，也没有把它说成完整屋顶CAD/欧洲BOM放行工具。

[OpenSolar官方开发门户](https://developers.opensolar.com/)提供[API](https://developers.opensolar.com/api/)、[SDK](https://developers.opensolar.com/sdk/learn/)、[MCP](https://developers.opensolar.com/mcp/)文档入口。这是比揣测闭源API更直接的集成调查入口；本轮只取得门户正文，未申请权限、调用项目端点或核其SDK许可，不能声称已经拿到其完整设计内核或可直接白标嵌入。

## 7. 用同一项目学习和对照，而不另造界面原型

先把Aladdin官方rooftop/auto-layout/inter-row/storage四例作为软件自身操作样本，保留原件和运行后导出，区分原文件缓存结果与新计算。随后在Aladdin和archelios中人工建立一个共同受控项目，用于观察实际任务链：建议合成平屋顶20×12m、屋面高5m、4×3m且高出屋面1m的障碍、边缘保留1m；这些均为**比较夹具条件，不是国家工程阈值**。地点用52.52/13.405的测试坐标，先固定20块合成400W、2×1m组件共8kWp，安装倾角10°、真南方向，再分别比较自动排布建议；不把合成组件当可采购SKU。真实电气选型再换成双方都能输入、且有同一份原厂数据的实际型号。

每次拿到以下同一项目证据，才有可复刻结论：

| 环节 | 保存的真实证据 | 比较时必须控制 |
| --- | --- | --- |
| 输入与编辑 | 任务入口、操作录屏/截图、屋面/障碍尺寸、错误提示、原生项目 | 坐标/单位、屋面坡度和安装倾角分开；来源和默认值 |
| 排布 | 排布前后场景、组件位置/姿态/数量、障碍与边缘、可逆编辑 | 相同安装/间距条件；自动数目不等于已证明最优 |
| 发电 | 实际模型设置、天气/时间/采样、遮挡/损失、CSV与图 | 代表日与全年、DC/AC边界；天气不同不能作数值准确度竞赛 |
| 系统结果 | 组件/逆变器/电池及附件的具体型号数量、串/MPPT/模式、说明/报告 | 工具不支持的电气约束记缺项，不以三维场景代替厂商放行 |
| 保存和交接 | 原生文件、重开结果、报告、CSV、到电气工具的实际文件 | 文件版本与有效默认参数、是否重算、是否丢几何/模式/附件 |

本轮Garage的4→12代表日实走已经给出一个实际学习结论：**复制交互与可读项目状态有价值，复制“Yearly”标签下的采样外推不能替代我们的连续时序合同。** 应继续用成熟软件暴露方法和操作，而不是把某软件返回了结果当作新系统正确性。

## 8. 取证和交付状态

外部请求均由现有Apify凭据经安全helper发出，常用运行内存2048MB、并发1–2。尝试另一个官方Cheerio Actor时收到403 `full-permission-actor-not-approved`，未批准其full-account权限，失败记录保留；随后用原有获准website-content-crawler的文件保存能力取回原件。部分非HTML下载被Actor页面统计记为failed，实际HTTP200、KV文件字节、SHA和Git blob均已另核，未凭SUCCEEDED状态宣称取得正文。

原始README/许可/样例/源码/归档清单已在raw保存；[原始文件清单](raw/original-file-manifest.json)、[原生文件清单](raw/aladdin-native-manifest.json)、[采样方法来源](raw/aladdin-sampling-source-manifest.json)、[完整归档证明](raw/aladdin-archive-manifest.json)可查。所有KV下载签名从入库记录移除；API令牌没有输出或写入文件。完整ZIP在本机，公开固定下载可重新取得。

完成的是：真实软件取得、源码/许可/格式核实、原生样例、与协调者真实实走相连的关键采样方法核对。尚未完成的是：下载源码本地构建、线上2.0.7源码等价、全欧洲工程精度、具体设备选型及原始气候表数据校准。后者不能用本轮下载、开源许可或代表日结果代替。
