# 现代方案工作台：从成熟软件到完整实施清单

2026-10-23，Codex 后台研究。范围是整套项目工作软件，不限三维。不重启已解决的数值/地图/硬件审计，不执行下载源码，不输出其内嵌配置，不改业务、设置或提交。

**应复刻的核心是“一个可持续编辑、可复算、可比较、可交付的工程项目”。** 3D 是其中一个编辑视图；现代前端包和可靠计算后端都必须接入资料、修订、任务、方案与商务链。用户最新允许独立现代工具 runtime；已选 React 19/R3F/Drei/Three/Vite 的版本依据见[既有 3D 栈研究](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/research/2026-10-23-3d-workspace/STACK-EVIDENCE.md)，这里不重复版本调查。

## 1. 证据级别与真正观察到的完整软件模式

- **O = 真实操作记录**：继承既有浏览器实走和原始导出，本研究没有重新操作。Aladdin 线上 2.0.7 的 584 片 Garage 项目，两次分析、`.ala`/CSV 导出以及重新导入后重复计算已有证据；PV*SOL 实际完成组件/逆变器/组串求解，年模拟停在验证码前。不能把 Trace/K2 官方资料算成已进入其设计器。[实操记录](/Users/chesterjohn/Documents/de-linker-worktrees/research-trace-software-access/docs/research/2026-10-22-trace-software-access/README.md:7)。
- **S = 源码证据**：本轮只在内存阅读固定 Aladdin `7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa` ZIP，SHA-256 `1441ac0f978a12d2930d390e22c195b338f35cb64bb8005e3aacd6f437bfb40a`；未运行它。该源码 UI 版本 2.0.6，与上述线上版本不同。[已核源码与版本边界](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-calculation-550/docs/research/2026-10-22-trace-software-access/reusable/README.md:25)。
- **P = 官方描述/手册**：Trace 的 PRO → elec calc SOLAR、K2 的结构与报告/数据交接、SAM 的 UI/计算内核分工，属于已取得的一手资料；没有据此宣称其商业流程被我们实跑。[Trace 资料](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-experience-549/docs/research/2026-10-22-trace-software-access/trace/README.md)、[软件与 SDK 研究](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-calculation-550/docs/research/2026-10-22-trace-software-access/reusable/README.md)。
- **I = 本站设计推导**：下表的接口、任务依赖、保存和验收要求，是把上述模式接到本站目标与现有架构的设计，不伪称竞争软件已证明这些本站能力。

Aladdin 不只提供画布。固定源码中已经能追到：

| 成熟模式（均 S，非本轮实走） | 固定源码定位 | 能复刻什么；不能照搬什么 |
| --- | --- | --- |
| 原生文件、导入迁移、展开默认值 | `localFileManager.tsx:128–162`；`stores/common.ts:798–905` | 文件读入/保存、版本迁移与有效输入展开。本站增加严格合同、原件来源和校准；不能直接导入任意 JSON，或依赖以后会变的默认值重算旧方案 |
| 2D/3D 与对象/属性视图 | `stores/common.ts:772–779`；`modeltree/modelTree.tsx:62–82` | 同场景改变观察方式，树与属性对应对象。本站用统一领域 ID/修订驱动多个视图，不能把渲染对象当项目权威 |
| 批量修改、撤销与分组 | `undo/UndoManager.ts:21–59`；`keyboardListener.tsx:63–105`；`solarPanelTiltAngleInput.tsx:59` | 命令栈、撤销后剪 redo、组合删除/修改。本站提交类型化命令与不可变修订；不要照搬捕获全局 mutable store 的闭包作为持久历史 |
| 刷新恢复与浏览器持久化 | `stores/common.ts:5424–5482` | 场景/视图参数选择性持久化，view-only 用 sessionStorage，否则 localStorage。本站增加身份隔离、草稿基准和服务器确认；源码还持久化 user，不能照搬为 WP 权限事实 |
| 过程控制与结果分离 | `panels/simulationControlPanel.tsx:34–199`；`stores/commonData.ts:22–34` | 计算的取消/暂停/恢复和派生结果单独保存。本站由耐久 worker 持有工作；浏览器 flags 不具备崩溃恢复、租约或 checkpoint 语义 |
| 多设计比较、变量与单位 | `panels/projectGallery.tsx:193,402`；`panels/ProjectUtil.ts:25–43,338–403`；`components/parallelCoordinates.tsx:29–47` | 多设计、选择/过滤、统一变量/单位的比较。本站比较冻结候选与同条件 run，不用一张图掩盖模型/输入不一致 |
| 排布约束和设备关联 | `stores/SolarPanelArrayLayoutConstraints.ts:7–19`；`models/SolarPanelModel.ts:9–22` | 间距、排宽、倾角、方向、设备引用的显式数据。其 `BatteryStorageModel.ts:7–12` 只有若干简化字段，不能替代本站端口/工作模式/峰值时长/温度/SOC/附件/国家放行图 |

上表的 ZIP 条目 SHA、行范围、固定 GitHub URL 与研究来源在 [EVIDENCE.json](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/research/2026-10-23-modern-workbench/EVIDENCE.json)；只保存必要索引与摘要，没有复制整 app。

## 2. 完整能力 → 可执行工作包

表中“模式依据”只说明证据等级；“本站合同/完成门”全部是 **I，待实现或继续集成验收**。已存在的内核能力应复用，不要求推倒重写。

### 进入项目与形成可靠资料

| ID / 客户能力 | 模式依据与复用 | 本站合同与完成门 |
| --- | --- | --- |
| W01 同一个项目入口、任务概览 | O：Aladdin 原生项目；S：场景/项目图库；I：Journal 工作台 | 项目概览显示资料、设计、计算、设备、报告和交接各自状态。首页屋顶、产品、商业内容入口都进入同一项目；用户按已有资料开始，住宅/商业不分裂所有权或屋顶能力 |
| W02 导入资料并确认质量 | O：`.ala` 重开；S：导入版本展开；现有 Assets/ProfileImport/PVGIS 接入 | 文件原件私有保存 hash；几何确认比例/轴/CRS/来源，CSV 预览列映射、单位、计量点、时区/DST、缺测和有效范围。成功上传、成功解析、可用于哪种计算分开；错误定位到字段/行，不能把未知填 0 |
| W03 地点、测量、底图与来源 | P/I：既有 Map Adapter 与欧洲来源研究；复用 MapLibre/Terra Draw 的现站经验 | 地图显示、搜索、绘制、自动屋面、工程几何是窄 adapter。只把可保存、可衍生的资料编入项目；手工尺寸/图纸是完整路径。无自动数据时保留项目并能继续，不编造全欧洲同等覆盖或精度 |
| W04 目标、计量与任务条件 | P：成熟方案工具的任务输入；现有时间/能流内核 | 输入自用、削峰、备电等真实目标，展示所需负荷范围、峰窗、时序分辨率、初末库存及控制条件。年耗输入可以形成有来源模板场景，不能由此生成虚假的精确全年/15 分钟保证 |

### 编辑、修订、恢复与计算执行

| ID / 客户能力 | 模式依据与复用 | 本站合同与完成门 |
| --- | --- | --- |
| W05 地图/2D/3D/对象树/属性同步 | S：common 的 2D 切换、modelTree；已选 Three/R3F/Drei | 同一屋面/阵列/障碍 ID 与本地米制数据驱动所有视图；任一视图修改，其他视图同步。住宅坡顶/开孔、商业平顶/排距/障碍都能进入同一工具；树选择和数值编辑是画布外的完整路径 |
| W06 编辑约束与批量操作 | S：排布约束、对象属性批量修改；现有 Shapely/pyproj 可复用 | 手工/自动排布先给可检查建议；组件数量/ID、越界、孔洞、重叠、屋面约束在提交前后验证。批量旋转、排除、复制、删除均为可撤销命令；来源精度和工程规则不由 UI 默认数值决定 |
| W07 修订、撤销与自动恢复 | S：UndoManager/persist；O：本地文件重开 | 三层状态：交互临时态、未确认草稿、服务器确认 revision。显示“未保存/保存中/已确认/离线/冲突”；undo 产生新有效状态，历史 run 不改写。刷新/切语言/撤回统计同意/关闭再开后可恢复；账号改变不能读到前一身份草稿 |
| W08 长任务、进度、取消与重试 | S：simulation controls；现有 Jobs/Worker/receipt/fencing | UI 拿 run 引用后可离开并重新连接；区分排队、执行、失败、取消、结果发布。取消 fetch 不是取消服务器计算；只有 worker 实现 checkpoint 才展示可恢复暂停。重复点击和网络重试复用同一意图 key，不重复建工作 |
| W09 局部失效与有依据的重算 | S：导入时清派生数据；I：现有 manifest/依赖应扩展为任务图 | 改屋面→布局/近场遮挡/PV/电气/能流/报告相应过期；改负荷→能流/储能与报告过期；改项目标题只影响相应呈现。每个 artifact 声明输入/模型依赖 hash，只有匹配才复用；UI 不靠组件是否重新 mount 判断有效性 |
| W10 场景分支与方案比较 | S：projectGallery/ProjectUtil/parallelCoordinates；O：同几何两采样结果 | 方案引用固定 revision、候选拓扑与 run；对齐气象/负荷/模型/初末条件，突出真正差异。改几何得到新方案，旧图表/报告保留其依据；不能把旧 run 混在当前卡片中 |

### 数值、设备、结果与工程交付

| ID / 客户能力 | 模式依据与复用 | 本站合同与完成门 |
| --- | --- | --- |
| W11 可追溯 PV 与时序 | O：Aladdin 原件与采样敏感性；P/I：既有 PVGIS/pvlib 方法；现有 TimeAxis/PVGIS profile | 展开全部有效参数、固定原件/模型/损失边界。PVGIS modeled AC 与显式辐照→DC→AC 路线具名；损失一次应用，图表标明真实/模型/重建分辨率。Aladdin 代表日 CSV 不能直接喂全年储能 |
| W12 遮挡与电气影响 | S：Aladdin 遮挡/模拟源码；P/I：方法研究 | 太阳/阴影显示、几何遮挡采样、辐照处理、组串/旁路/MPPT 电损分别出具方法与验证；按场景对近场、排间、散射适用性校验。渲染 shadow map 不参与正式能量账本；采样精度可解释并有收敛/独立夹具 |
| W13 端口、组串、设备/附件与条件选型 | O：PV*SOL 真实组串方案；P：厂商原件/Trace 电气分工 | Woo 产品身份+手册字段/条件→版本化 capability graph；温度电压、电流、串并联、连续/峰值/时长、控制器、STS/附件、国家/模式放行逐项表达。先资格/可行性，再排序；缺证据、越域与搜索未完不等于失败或已放行 |
| W14 连续储能、多目标与真实控制 | P/I：数值研究；现有 EnergyKernel/replay/独立 verify | 共用连续库存和来源账本，不在午夜重置；功率/能量/备用库存/计量窗/初末边界全部执行。场景 replay、理想可达域、真实 EMS 控制能力独立标记；替换电池后用实际能力重新验证，不能只按 kWh 比例换名 |
| W15 图表、比较、诊断与结果解释 | S：日/年面板及比较变量；现有冻结 artifact/metrics | 先读摘要，再按需读同 run 的时序窗口；功率/能量/比例各有口径、单位和 undefined 原因。可缩放/选时段/多方案叠加，同时提供可键盘阅读的表格与原始导出。显示抽稀不能修改正式时序或隐藏峰值失败 |
| W16 报告、BOM 与工程交接 | P：Trace PRO→elec calc、K2 报告与转接；现有 reportlab 经验 | 屏幕、PDF、CSV、单线/工程资料与 BOM 引用同一 run。组件数量、设备/附件、假设、失败/未知、来源页与条件、国家适用域、初末状态均可追溯。结构/消防/电气未计算的事项保留为具体待核输入与交付责任，不能给整套“通过” |
| W17 采购与询盘转换 | I：既定 Report/Commerce Adapter + Woo 原生 | 工程 BOM 不伪装全部可销售 SKU；区分组件/附件/安装用项与 Woo 可询盘产品。交接前重核当前账号/价格可见性/商品与库存状态，差异可见；原 run 不因实时商品变化被重写。一次意图只写一次 draft/inquiry，并返回真实回执 |

### 面向欧洲安装商的全站产品与运行

| ID / 客户能力 | 模式依据与复用 | 本站合同与完成门 |
| --- | --- | --- |
| W18 欧洲项目与 EN/DE | I：统一产品决定、欧洲研究；现有 Polylang/gettext | 国家/地点/时区/规则包与界面语言独立。法国、英国、瑞士等项目能在 EN/DE 同项目编辑；小数、日期、单位与导入语义不因翻译改变。安装商可复用模板、复制方案与整理资料，但模板的事实/默认有来源 |
| W19 站点入口、SEO 与分享 | I：已有全站影响研究；复用 WP/LC/原语言地址 | 首页屋顶重点入口、导航/手机、内容/产品/Journal/FAQ、旧深链都进入正确任务并保留已知上下文；返回/刷新有效。公共入口的双语 SEO 与私有项目/报告索引策略分开，不能把私有 run ID 当公共营销页 |
| W20 账户/访客恢复与 Genie | I：既定 WP 身份/规划私有 API 及 Genie 通道 | 客户不自选 owner。访客刷新可恢复，login 仅认领自己项目，logout 不继承账号权；保存文案基于真实确认。Genie 读用户有权访问的指定 run/当前选中历史方案，准确报告 stale/缺项，不另算另一套 BOM 或暗用最新数据 |
| W21 无障碍、性能与设备恢复 | S：源码键盘/属性机制；P：既有 3D 官方性能；I：本站验收 | 不以 gizmo/hover/颜色作为唯一入口；对象列表、数值表、键盘选择/撤销、错误聚焦、图表表格、读屏状态都可完成任务。静态场景按需渲染、实例化、视窗数据；GPU/地图失败仍可编辑同项目，不承诺未经测试的手机容量 |
| W22 隐私、同意与运行可观测 | I：全站影响/来源留存/存储合同；现有 consent、jobs、backup | 运营指标记录真实状态而不采地址/负荷/文件/私有链接；拒绝分析同意不阻断设计。源资产按权利留存与删除，不能为永久重放违约；任务资源限制/错误、备份恢复、版本升级和 schema 迁移都有真实演练与读回 |

依据范围：上述数值/选型沿用[NUMERICAL-MODELS](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md)、[硬件原件研究](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-experience-549/docs/research/2026-10-22-roof-experience/hardware-study/README.md)；地图消费沿用[MAP-ADAPTER](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/research/2026-10-22-planning-implementation/MAP-ADAPTER.md)的来源/几何边界，前端同 React 的旧建议已被本轮独立 runtime 裁定调整。站点链沿用[SITE-IMPACT](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-system-route-548/docs/research/2026-10-22-roof-system-rebuild/SITE-IMPACT.md)与[入口/语言/SEO/统计证据](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-experience-549/docs/research/2026-10-22-planning-site-impact/entry-content/README.md)；历史 r549 浏览器仅证明旧问题，不算新工作台验收。

## 3. 当前后端与 3D 包之外仍需明确的架构决定

本轮取证基线 HEAD 为 `6544c23bc0fc2b7f31ec420e130aa069a2af3564`；工作树另有根代理正在修改的 HTTP/身份边界及 `apps/planner`。本研究不评审或回滚它们，也不把文件存在当 runtime 验收。

已有项目修订、私有资产、幂等意图、冻结依赖、持久 worker、时间语义、连续能流与 PVGIS profile 是应接上的基础。它们的规格分别位于 [workspace](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/specs/548-project-workspace.md)、[energy job](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/specs/548-energy-job.md)、[PVGIS](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/specs/548-pvgis-inputs.md)、[private gateway](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/specs/548-private-gateway.md)。以下不是重新否定基础，而是“基础怎样成为完整工作软件”的决定与完成门：

1. **编辑器状态合同**：领域命令/不可变 revision、可撤销编辑、未保存本地草稿、相机/选择 UI 状态、服务器缓存分开。恢复策略必须指定基准 revision、身份作用域、冲突处理、确认点；不要照搬 Aladdin 整个全局 store/localStorage。
2. **项目文档与迁移合同**：几何对象图、资料资产、模板默认、地理参考和坐标、设备拓扑及派生数据分别版本化。保存的是展开有效参数；导入迁移不能悄悄改变历史 run。需要可移植项目包时明确包含什么、哪些受限源只能留来源证明。
3. **任务依赖与有效性合同**：把现有 run manifest 的依赖升级为客户可理解的任务/产物图；为每个工作种类声明输入、模型、结果、重用条件、失效范围、失败恢复和进度协议。不要由 React Query 的 cache freshness 或一个 `loading` 布尔值决定工程结果有效性。
4. **方案与比较合同**：一个方案是固定场景+设备候选+模型/任务条件+run 引用，不等于某次 UI 表单。比较先检查可比条件，保存基准/差异/缺项；需要独立的候选与比较投影，而不只是把两个年量卡片并排。
5. **设备与国家资格合同**：实际商品事实编译、原文证据、条件能力图、拓扑搜索/预算/验证和国家包仍须逐域完成；基础 replay 的 pass 不自动晋升为 SKU 或欧洲工程放行。此能力不能被“先做3D”取消。
6. **结果与交付合同**：同一冻结结果生成可访问的摘要、时序查询、报告、工程 BOM 与交接请求；消费端拿真实回执，区分已准备/已保存/已加入草稿/已发送询盘，不能由 UI toast 自行宣布。
7. **站点桥与运行合同**：现代 app 与 WP 的身份/产品/草稿/语言/Genie/SEO/同意通过窄接口联动，纯计算不写商务。实际 enqueue/lazy chunks/WindPress、备份恢复、资产到期、监控与低端设备仍需完整用户路径验证。

这些决定的既有分工与事实权威见[统一架构研究](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-system-route-548/docs/research/2026-10-22-roof-system-rebuild/ARCHITECTURE.md)。不需要为此拆成几十个微服务或引入图数据库；库只应填真实职责缺口。

## 4. 实施顺序与可验收切片

| 切片 | 必须实际串起来的能力 | 放行证据 |
| --- | --- | --- |
| A 项目壳与资料 | W01–04、W07–09 的基础；WP 身份→创建/导入→质量预览→保存→刷新恢复 | 真实私有 API/身份；同一项目/修订/原件；冲突/断网/拒绝输入可恢复。不能用 localStorage 假存账户 |
| B 完整设计编辑 | W05–07、W10；2D/3D/树/属性→约束→撤销→方案分支 | 坡顶和平顶夹具，双向修改、批量操作、保存重开；所有视图同 ID/米制数据；键盘和手机可完成 |
| C 联立计算与比较 | W08–15、W18；真实资料→局部重算→设备/能流→候选比较 | 冻结依赖与有效性；独立数值/硬件/国家证据；失败/未知/越域有具体定位。仅得到图形或绿色计算状态不够 |
| D 报告与全站交付 | W16–22；报告/BOM→草稿/询盘/Genie，旧入口和双语迁移 | 同 run 数量/型号/来源；当前 Woo 差异确认、真实回执；EN/DE × 1440/390 状态验证；隐私/同意/恢复与共享页面回归 |

切片用于形成真实可用的竖向路径，不缩减完整目标；不能把 A/B 完成写成选型已经可信。研究完成、依赖安装、包能 build、一个场景能旋转都不是工作台交付。

## 5. 三个明确缺口的成熟模块候选

这次只为根代理点名的 server state、时序图表、跨语言合同三个职责补取官方资料。以下版本经 Apify 从发布者 registry 原件实际回读并哈希，不用 Context7 的历史版本列表判断“当前最新版”。当前 `apps/planner` 的采用和真实构建由根代理执行，本研究没有安装它们。

| 模块候选 | 本次 stable / 许可与直接依赖 | 对应能力及采用边界 |
| --- | --- | --- |
| `@tanstack/react-query` | **5.104.5**；MIT；React 与 @types/react peer `^18 \|\| ^19`；query-core 同版，无 Router 依赖 | W01/W08/W09/W10/W20 的服务端读取、缓存、轮询、失效和提交状态。浏览器编辑草稿、undo 栈与领域有效性不交给 Query cache；不因选用它额外引入 Router |
| `echarts` | **6.1.0**；Apache-2.0；zrender **6.1.0**，无 React peer | W10/W15/W21 的多方案/全年时序图、窗口 zoom 和结果解释；直接封装生命周期即可，不要求再加 React wrapper。只导入实际 line/dataZoom/legend/tooltip/ARIA/renderer 等所需模块，保留许可归属 |
| `ajv` | **8.20.0**；MIT；与现有 linker-tools 已锁版本相同 | W02/W04 与所有命令/响应的运行时 JSON Schema 验证。复用版本和“后端 schema→前端 resolver”模式；不为追新更换 schema draft、放宽严格性或复制一套 TS 业务规则 |

一手发布元数据：[Query](https://registry.npmjs.org/@tanstack%2freact-query/latest)、[ECharts](https://registry.npmjs.org/echarts/latest)、[Ajv](https://registry.npmjs.org/ajv/latest)。原件及文档来源摘要已一并存入本目录证据索引；包未声明 Node engines 不是对所有环境/浏览器的保证，实际沿既定 Node/Vite/TS 6.0.3 工具链验。

**Query 的正确边界。** 官方提供 queryFn 的 AbortSignal；必须传给实际 fetch 才能取消相应网络操作。默认 unmount 后尚未完成的 query 并不自动丢弃其结果，已完成响应可能进入缓存。mutation 默认并行，即使多次调用同一 `.mutate()`；可按 scope ID 串行，且默认不自动 retry。持久化离线 mutation 后还要恢复对应 mutationFn，不能因为状态已存就保证刷新后会自动继续。[官方取消语义](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation)、[官方 mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations)。

由此推导本站合同：query key 至少分开项目、revision、run、输出种类和已验证身份作用域；身份退出/切换后清理私有 cache。mutationFn 发送同一个业务意图的 idempotency key 与 expected_revision，lost acknowledgement 时先按回执读回，不能换 key 重发；409 冲突要用户可恢复地处理。**Query 取消、scope 串行和 retry 均不提供服务器端幂等、权限或持久 job 取消。** Cancel job 必须发独立业务命令并等服务器状态；Query staleTime 不能使旧工程结果重新有效。先使用现有 Jobs/Workspace 合同，不引入第二套工作队列。

**ECharts 的正确边界。** 官方有 slider/inside dataZoom 交互；ARIA 需显式引入 AriaComponent，并启用对应配置，纹理辅助可以减少只靠颜色区分。官方手册也说明把大量点逐条读出来并不易理解，应给合适的自定义描述。[官方 ARIA](https://echarts.apache.org/handbook/en/best-practices/aria/)、[官方 dataZoom 文档源](https://github.com/apache/echarts-doc/blob/master/en/tutorial/data-zoom.md)。手册同页混用旧 `aria.show` 与 `aria.enabled`；本次已取回[官方 option 源](https://github.com/apache/echarts-doc/blob/master/en/option/component/aria.md)，第 8–27 行明确 `aria.enabled: true`，且 `aria.label.enabled` 跟随开启。采用该 API 并以锁定 6.1.0 的类型及浏览器真实 `aria-label` 验证，不能只复制旧例子便宣称无障碍完成；本研究未把一个 404 的 AriaModel.ts 猜测路径冒称为当前版本源码。

本站图表投影应携带 run/单位/计量口径/时间区间/原生与重建分辨率，提供 EN/DE 摘要、键盘可操作的时段选择与数据表、原始数据下载；ARIA 自动文字不代替这些路径。8760 或多方案点数能否流畅是实测门，不是库的能力清单能证明的性能。显示采样/聚合只影响绘图，原始峰值、独立验证与正式指标来自冻结 artifact；不能用图中稀疏曲线重新算削峰或“看起来没有失败”。图表窗口 API/数据投影须有授权、边界与来源，不能一次把所有候选全年明细灌入页面。

**Ajv 的正确边界。** 官方默认 export 对应 draft-07；2020-12 与此前版本不能共用同一 Ajv instance，应选择对应 class/元 schema。`JSONSchemaType` 的 TS union 支持有限，TS 通过不能证明 schema 已包含所有 union 分支。[官方 draft 说明](https://ajv.js.org/json-schema.html)、[官方 TypeScript 限制](https://ajv.js.org/guide/typescript.html)。现有 [validation.ts](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/plugins/linker-tools/src/configurator/validation.ts:1) 已有后端导出 schema + React Hook Form resolver，但它的旧德国字段文案、旧模型范围和 `strict:false` 不构成新合同要求。

本站实施应从版本化 Pydantic 命令/结果模型导出具名 draft 的 schema 与 TS 类型，CI 比较已发布合同及兼容性；不手写一套会漂移的前端阈值。对新增 schema 独立选择正确 Ajv instance 与严格配置，避免 coercion/default/removal 在验证时悄悄改输入。前后端共用“真/假、整数/数值字符串、缺字段、额外字段、union 各分支、单位与未知状态”等反例夹具；服务器仍是授权、幂等与工程规则权威，浏览器校验只改善输入反馈。图表与 3D 也必须验证响应来源/版本，不能只给表单做校验。

**不再扩库的部分。** 现站已使用 React Hook Form 7.88.0、MapLibre 5.24.0、Terra Draw 1.35.0；优先把其表单/地图/绘制经验接入新 app，仍需验证 React 19 隔离、坐标、控件、样式和生产路径。undo/恢复采用小领域命令及浏览器原生持久层即可开始；只有实测需要才增加状态库、协作框架、空间加速或优化求解器。Aladdin 的 Zustand、Firebase、Ant Design、Recharts/d3 等说明其实现方式，不是本站必须全装的依赖清单。

本节采用门：现代包真实 build/运行；Query 错误/重试/取消/身份切换和 lost acknowledgement 不重复提交；ECharts 全年及多方案夹具、手机 zoom/表格/读屏且不改正式数据；Ajv/Pydantic 合同双向夹具及 schema diff。未完成这些证据前，只能称模块候选和实施方案。
