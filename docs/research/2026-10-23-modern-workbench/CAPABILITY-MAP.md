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


## 6. 安装设计与完整物料的实施合同（2026-10-26）

**下一步应建立有物理设备实例、端口、回路和实际路由的安装设计，再由分域校核结果生成物料需求。** 只添一张可填数量的清单，不能完成 W13/W16。以下“本站合同”是设计推导 I，不冒称已经实现、已实走竞品或已取得标准全文。

### 6.1 已核现状和成熟模式

- 本机当前 Woo 派生源 `ae4a0a7920abea212908786f8b08141e4432e6631af699d79c99429c27a1257f` 有 85 个销售设备、1 个组件参考输入、377 条兼容 pair，以及 29 条 meter / 6 条 parallel-controller requirement。4107 的 17 类包装件已按手册 PDF36 维护。它没有完整支架体系、场地电缆/保护器件或接地设计合同；这是一项已读回的数据边界，不能由文字条件推断成已有能力。
- **P：K2 的专业范围是所选 K2 安装体系。** 当前官网将风雪作用、安装布置报告、分屋顶组件分配和物料清单放在同一规划流程中。可复刻“系统/屋顶/布局及作用条件决定安装方案，再生成物料”；公开页面没有给本站一个已获授权、可直接调用的通用结构/BOM API。[K2 Base 官方页](https://k2-systems.com/en/digital-services/k2-base/)
- **P：Trace 将光伏 DC、AC 到接入点作为同一电气项目。** 当前 SOLAR 页把导线截面、保护器件、维护中的厂家设备资料、计算书、单线图和 BOM 连在一起；既有 F02 2026.0 原件 PDF5 明确 PRO 导入恢复设备引用与总体结构后继续电气设计。可复刻项目连续和工程任务边界，不能把其产品宣称当本站准确度证明，也未取得其嵌入内核或接口许可。[SOLAR 官方页](https://www.trace-software.com/en/our-solutions/elec-calc-solar-complete-pv-design-software-from-panel-to-ev-charging-point/)、[F02 原文 PDF5](https://dl.trace-software.com/dl//frk/docs/Changelog/01_FR_Note_de_mise_a_jour_2026.0.pdf#page=5)
- **已有 P/M 证据沿用。** 具体电缆/保护/接地与国家采纳版仍须相应条款及器件依据；现有[欧洲工程研究](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-europe-precedents-551/docs/research/2026-10-22-roof-europe-precedents/engineering-study/REPORT.md)中的物理/国家分域、标准范围与未获全文边界继续有效，不重做一遍国家扫描。

本次两页仅作上述范围/流程依据。经 Apify `website-content-crawler` 回读：K2 在 run `cOMgXHffB7VLEAYxU` / dataset `3wiNH8bUYpRAFqdhX`，2026-10-25 22:22:57Z HTTP200，正文 SHA-256 `b5d3717b7b39b28431fa8f83ef8bd0c31c89497141184c16c3b2569cb517520f`；Trace 的 cheerio 仅得短壳，改为 `playwright:adaptive` + `htmlTransformer:none` 后，run `DOIh9RZBU8JiDRUvl` / dataset `rSrkyhZde9mziADcn`，22:24:32Z HTTP200、20,519 字符，正文 SHA-256 `da1eca3740ec413b34cb63c22566321c6cbed70bf1f262b09e5c3e2b5051557d`。没有普通搜索、注册/付费/发信或产品运行时研究依赖；未新增本地资料副本。

### 6.2 项目事实和 Woo 厂商事实分别承载什么

| 设计域 | 项目必须提供/保存的输入（允许未知，具来源） | 只由当前 Woo 商品/参考输入及关联资料提供的厂商事实 | 可计算的量和仍须工程依据的判断 |
| --- | --- | --- | --- |
| 支架与固定/配重 | 屋面与阵列 ID/修订、屋面结构/覆盖层/固定基底、实际支承位置、建筑高度和相应作用/区段、所选安装体系及现场调查 | 具体安装体系、组件允许夹持区/夹具与导轨组合、支点/连接/压载规则、适用结构与文件版本 | 几何可给排长/位置，不能单凭模块个数给夹具、屋顶钩、锚栓或配重。须有采用体系的计算方法/厂商设计输出和项目适用性 |
| DC/AC/电池电缆 | 设备实例和接线端点、每根电缆或单导体的实际路径、垂直段、回路/运行方式、敷设/环境温度/成组条件及工程设计边界 | 电缆型号/芯数/材料/绝缘/额定值、端子接受范围、设备端口额定值及相关条件 | 明确路径可给长度；截面、载流、压降、故障承受与保护配合依赖完整条件和适用方法，不能由 kWp 直接给截面 |
| 连接器/端接 | 实际串和端点图、接线方式、已随设备/组件提供而可用的端接、需现场制作的端点 | 精确厂家/系列/变体/极性、允许配对、导体范围、组装/工具要求及随附数量 | 可数有身份且未满足的端点；是否可配对须厂商证据。不能以“MC4 compatible”或接口外形批准混插 |
| 保护、隔离和接入 | 国家/地区/DSO、电压层级与接地系统、供电/并网/备电状态、短路条件、回路拓扑和线缆设计 | 器件额定值/分断能力/特性及使用条件、设备内建保护的准确位置和作用范围 | 保护需要及器件/整定由适用规则和配合校核决定；内建 SPD 或一个最大熔断值不自动替代整厂方案 |
| PE/等电位/接地及防雷接口 | 要连接的可导电部件/位置、连接路径、现场接地及已有防雷系统、设计/测量依据 | 支架/夹具的导电连接许可、端子和导体要求、相关器件特性 | 路由可给已定义连接的长度/端点，连续性、截面和防雷/接地适用性须相应工程依据，不生成泛化“一套接地包” |

输入不得把未知设为 0 或用德国默认值填全欧洲。坡顶/平顶、住宅/工商业复用这些域；项目类型用于引导所需资料，不能绕过某域的校核。商业多设备须用 **物理实例 ID + 端口 ID** 区分同型号多台设备；现有单 `inverter_product_id` 的 `PvStringPlan` 只能经显式适配进入网络，不能冒充整厂多机拓扑。

**当前源的三个具体禁推例：** Trina 参考组件的 `cable_mm2=4.0` 是该组件资料中的线缆规格，不能据此给现场延长线选截面；`max_series_fuse_a=25` 是上限事实，不能直接选 25 A 熔断器；其 `dc_connector` 列出多个变体而未唯一选定，H2 包装又只给接头数量，因此目前不能据“有6对”扣减所有串的安装接头需求。组件资料的风雪试验荷载也不是现场屋面承载或建筑作用值。这些规则来自数值语义和产品证据边界，未冒用未获标准条文。

### 6.3 可以立即实现的深模块与数据合同（I）

1. **`InstallationInputs` 与项目修订。** 新的版本化项目字段保存 `device_instances`、`circuits`、`routes`、`mounting_selection`、`site_conditions`、`evidence`。设备实例只引用当前 Woo ID/修订；组件、阵列和串引用既有对象 ID；端点引用实例/端口而非自由型号文字。现场输入允许保留未确定值。厂家额定值/规格不出现在客户可编辑 DTO 中；后端从同一已准备 Woo 投影解析。沿用 `Workspace`/资产/幂等/永久修订，不建新队列或第二设备库。
2. **`RouteTakeoff` 先提供真正可用的几何产出。** 路径声明本地米制坐标框架及来源，按 `Σ‖p[i+1]−p[i]‖` 求分段中心线路长。实际高程/上下行须在路径中，二维投影只能名为平面长度，不能变成完整敷设长度。每一电缆组件或单导体显式分配路径；有来源的端接/服务环余长分别记录后相加，不塞统一15m或损耗率。多芯电缆是一根组件的路径，不能按芯数购买多倍米数；两根独立 DC 导体只有被明确分配时才各计长度。截面/安全状态独立于这个几何量，来源精度随结果保留。
3. **`InstallationEvidence` 编译与分域内核。** 从 Woo 的维护字段和关联手册编译具类型的安装能力；缺少真实 BOS/安装体系资料时给具名需求，不自动生成参考产品来填格。支架、线缆、连接器、保护、接地分别返回适用域、已满足/违反/缺输入/缺厂家证据/未支持方法/待国家规则；一个任务成功不表示这五域全部合格。新增规则逐条带方法/版本/所用条款或厂商页；本研究不建议现在硬编码未获正文中的系数。
4. **`InstallationDesignResult` → `MaterialDemand`。** 输出按实例/屋顶/回路分组的需要量、单位、数量来源（几何/规则/厂家项目报告）、使用的全部依赖与每域状态。数量可以已确定而规格待核。外部厂商项目文件作为私有工程证据保存原件/hash/适用屋顶与布局修订；其中产品行必须对照 Woo，未映射行保留为未映射需求，不注册新商品、不导入额定值或把手填行当自动设计结果。未取得的外部 API/schema 不先造 adapter 的成功合同。
5. **`MaterialReconciliation` 才把需求与随附清单合并。** 保留 `required` / `included_available` / `allocated` / `additional_required` 四个量及单位，只有同一种且已证明可配对的物件才允许分配、扣减；同一随附件不能分配给两个端点，额外提供的包装件不成为额外采购量。规格未知时不以负数截零掩盖差异。`project_materials.py` 消费这份冻结结果，现有屏幕/PDF/CSV和 Woo-only 销售交接继续共用；不从报告层反推数量或做选型。
6. **完成度与局部失效。** `quantities_recorded`、`design_calculated`、`required_domains_qualified`、`BOM_complete_for_scope` 分开；客户填写“已完成”不产生工程资格。不适用必须由声明的设计范围/规则适用性决定并保留依据。几何/阵列/设备位置变动使受影响的支架/路径/电气结果过期；只改路由不重跑不相关年度能流。国家/规则版本改变仅使相关资格和报告过期；EN/DE 切换不改变规则地区。

现有代码落点：后端在 `services/engine/src/linker_engine/planning/` 增加具名输入/路由计算/安装校核模块，复用 `geometry_documents.py`、`pv_string_inputs.py`、`equipment_inputs.py`、`report_sources.py`、`project_materials.py` 与现有 `Workspace`；合同由 `services/engine/scripts/export_planner_schemas.py` 导出。前端通过 `ProjectEditor.tsx` / `DesignEditor.tsx` 及 `useProjectDraft.ts` 让路由与同一几何可视/可数值编辑，并在 `ProjectOverview.tsx` 给每域就绪/缺项；不让 UI 计算器决定工程资格。首次竖向交付应是 **设备实例/真实串 → 画出或确认实际路径 → 保存 → 后端几何取量 → 同一报告材料需求与缺项**，随后接所选安装体系和电气校核。它是必要的首段功能，不等于完整安装设计结束。

### 6.4 最小而有辨别力的完成门（I，待执行）

- 一个含水平和垂直分段的可解析路径，证明路长、单导体/多芯电缆购买量和来源单位正确；缺高程、缺路径或缺绑定保留明确未知。一个“同型号两台逆变器”项目证明实例端口及需求不混淆。
- 同一已知端点需求分别遇到匹配随附件、错系列/未知变体、重复分配，证明只扣可用件；使用当前 Trina 变体/H2 包装件作为拒绝伪成功的真实来源条件，无须排列所有数量组合。
- 厂家认可的一个支架项目及一个有依据的回路设计，逐项对照物料、适用域和失败/缺项；拿不到该独立设计时不能把自算结果标合格。先选有事实的体系完成，不用一套通用常量声称全欧洲全部体系。
- 同一修订/结果的屏幕、PDF、CSV和草稿候选保持一致，安装需求不增加虚假销售 SKU；变路由只失效相关任务，原文件仍是历史原件。复用已通过的报告/权限/历史与未变年度能流证据，只补安装新增风险。

此合同没有降低“统一工具、住宅/工商业、欧洲、完整 BOM/工程交接”的目标。它明确了当前缺少的事实和真实实现顺序；在安装体系、相应产品/现场资料与方法尚未取得时，完整安装资格及完整 BOM 均不可宣称已经交付。


## 7. 首个商用协调多机拓扑的厂商事实（2026-10-26）

**首段采用“共用 AC 并网点、每台 ET 自有 DC 电池组、一个 SEC3000C 协调”的两台同型号方案。** 当前 Woo 有可引用的 ET80/99.99/100（1946/1947/1948）、BAT C 61.4/112.6（1954/1955）与 SEC3000C（2409）；首段选择 1955，以免把 61.4 的总体兼容误升级为未证明的备电放行。两台是本次首段的明确项目选择，不是伪造的厂商最多台数。本节是原件证据与待维护合同，未改 Woo、未运行产品、未证明现场调试或完整工程放行。

### 7.1 本轮实际读过的维护源与原件

读取当前 `/Users/chesterjohn/de-linker-local/p548/engine/feed.json`，生成于 `2026-10-25T21:58:02+00:00`，`source_revision=ae4a0a7920abea212908786f8b08141e4432e6631af699d79c99429c27a1257f`、`compatibility_revision=a939cdb8036477d94f534dee354de58f93a48521c8de9bc6d8593cc045f8dc55`。以下均是该源已关联、实际存在于 p548 uploads 的厂商 PDF；**PDF 页码是从封面起的 1 基序号**，通常比页脚页码大 1。ET/SEC 接线图及关键表格已看渲染页，不能只按抽取文本拼接表格。

| 原件代号 / 版本 | 当前托管原件与所用页 | 已绑定字节 SHA-256 |
| --- | --- | --- |
| ET-S / Solution Manual V1.3，2026-06-30 | [ET 50–100，PDF9–12 并网、PDF15–19 并离网、PDF33 线缆](https://de-linker.com/wp-content/uploads/2026/09/GW_ET-50-100kW_User-Manual-EN_V1.3.pdf#page=9) | `f66efb70d0d8927a92355980e0a0bd09359f580664976e082c4e510320e6d5a0` |
| ET-U / User Manual V1.2，2026-07-02 | [ET 50–100，PDF19 电池归属、PDF30–32 并网、PDF36–38 并离网、PDF52 扩容、PDF168 电池接线、PDF178 cloud board](https://de-linker.com/wp-content/uploads/2026/10/GW_ET-100kW_User-Manual-EN_V1.2.pdf#page=19) | `0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615` |
| SEC-U / User Manual V1.3，2026-07-31 | [SEC3000C，PDF18–19 内含设备、PDF40–43 ET 拓扑、PDF51–54 CT/LAN、PDF155 数量表](https://de-linker.com/wp-content/uploads/2026/09/GW_SEC3000C_User-Manual-EN.pdf#page=40) | `98bbe6f74e4d4d0e2437c3917e1fb2365c352ad01b5c46d26ad82876cb18850d` |
| SEC-D / EMEA Datasheet V1.1，2026-05-15 | [SEC3000C，PDF1](https://de-linker.com/wp-content/uploads/2026/09/GW_SEC3000C_Datasheet_EMEA-EN.pdf#page=1) | `143fb6026284ffdb499ceb2efc5f46023a3bc84de4c215460fbe0d466b19ba54` |
| BAT-D / BAT C EMEA Datasheet V1.1，2026-01-12 | [BAT C 61.4/112.6，PDF1–2](https://de-linker.com/wp-content/uploads/2026/07/delinker-goodwe_batc60-datasheet.pdf#page=1) | `845e51ffb2801f48971c8b53941629dde1e8bc114b9b45dbc4f08c49c5ef815c` |

原有 [FACT-INTAKE §5](../2026-10-23-capability-inputs/FACT-INTAKE.md#5-交叉电气边界et80--gw614-不等于-80kw-电池系统)已经正确区分 1946/1954 的电压/功率和模式边界，本节沿用，不重复构造一份规格库。当前六条 `parallel_controller` requirement 全属于 **ETR**，只声明 SEC≥V7.8.19；ET 三个商品只有 `parallel_operation` 文字。ETR 的版本条件不能挪给 ET。ETR 现有手册的表列也未在所读页给出通用多机数量，本轮没有把它替代成无证据的上限。

### 7.2 模式、数量、关联与必要件的明确边界

| 域 | 厂商原件实际支持的内容 | 对首段及后续搜索的约束 |
| --- | --- | --- |
| 纯并网多机 | ET-S PDF10–11 已再次目视核实：ET 行的说明格为空，**15 台 / ARM≥2.184 / DSP≥2.212 明确印在下一页 BT 行内**，不能据此作为 ET 数字要求。ET 的 LAN 并网拓扑图明确有一组 SEC。SEC 自身表的版本说明保留其原适用范围。ET-S PDF7 明确此模式停电即停输出 | 保留 `mode=grid_connected`。15 是该系统表的数值；其中 hybrid 行的说明在分页处空白、15/固件印在 BT 行旁，不能隐藏这个表格归属疑点。首段两台同型号不引入型号混用规则；未获明示的异型号混用继续未知 |
| 并网/备电切换多机 | ET-S PDF16 / ET-U PDF36 的共同说明格明确 ET+BT 最大 **6 台**；ARM≥**3.193**、DSP≥**3.306**。ET-S PDF18 / ET-U PDF38：SEC≥**7.18**、STS≥**3.304** | 必须独立于纯并网计数和固件。备电不是“几台功率相加”即可放行；须有实际 STS 及负荷/电池约束。上述版本按原文保留，不能擅自补位或将 7.18 与 7.5.32 当小数比较 |
| STS 承载台数 | ET-S PDF18：GW125K-STS-G10 接 **1 台**；GW375K-STS-A-G10 接 **3 台**；GW750K-STS-A-G10 接 **6 台**。400V 额定功率依次125/375/750kW；375/750 在220V时为200/400kW | 当前 feed 的此类产品只有125K（2403），另有30K/60K。**375K/750K 均没有当前 Woo 身份**。因此125K不能给两台提供一个公共备电出口；首段采用纯并网，后续共享备电保留具名缺件，不能创建参考销售 SKU 顶替 |
| SEC 接口数量 | SEC-D PDF1、SEC-U PDF155：**RS485 60 / LAN 10**；SEC-U PDF53：每条可用 RS485 总线最多 **20 台并网逆变器**，3条可用总线，另一条默认接内含GM330；15是交换机端口数 | LAN10、交换机15口、ET系统15台和RS48560不是同一物理/语义上限。不能用RS48560批准60台ET储能协调，也不能以15口推出15台LAN控制。两台首段处于这些已知数量内；超过10的LAN方案仍须消除文件/接法差异后才放行 |
| 每台逆变器的电池关联 | ET-S PDF11/16、ET-U PDF31/36：**2对电池口**可接本台的同一电池系统或独立的两个电池系统；ET-U PDF19明确**每个电池只能接一台储能逆变器** | 采用 converter instance → battery bank instance 的明确归属；同一电池/并联柜组不得横跨两台逆变器。多台的AC并联不是共享DC母排的许可。首段可选每台一个自有柜组，实际双口接线仍须按原图/电流约束 |
| BAT C 并联结构 | BAT-D PDF1、ET-S PDF12/17、ET-U PDF31/37/168：同一电池并联组最多 **4柜**，不同型号不能在一个组内混并。1954为6 PACK，1955为11 PACK，不是让客户逐块自由叠到任意电压 | 实例按“整柜/组/端口”建模。允许的4柜只作用于它所属的battery bank；不能把两台各4柜解释为同一跨逆变器8柜组。ET-U PDF52又规定安装后不支持柜内添PACK；加柜扩容为安装一年内、同型号同料号，需售后细则 |
| 61.4 的模式与功率 | 签署的[兼容声明 PDF1](https://de-linker.com/wp-content/uploads/2026/09/BAT100KWHInverterCompatibilitystatement.pdf#page=1)列1946/47/48与61.4–112.6；[EMEA兼容表 PDF6](https://de-linker.com/wp-content/uploads/2026/09/GW_Battery-Compatibility-Overview_EMEA-EN_20260910.pdf#page=6)注明61.4不能达到ET80–100满功率。ET-S EN PDF12列61.4，备电PDF17及较后的ET-U对应表未列61.4；ET-S DE对应表亦未列61.4 | 总体 `released` 不等于61.4备电批准。保留1954的原有条件及文件差异；第一组用1955。缺列不能反写为厂商明确禁止61.4备电 |
| 计量和CT | SEC-D PDF1、SEC-U PDF19：SEC内含 **GM330×1**；SEC-U PDF51–52：要使用该表需对应三相取样与CT，CT自购/向GoodWe采购，**nA/5A，200≤n≤5000**；方向/相序须正确，线径须能穿CT | 公共并网点由同一SEC的GM330计量，不能另加“每台一个必须另购GM330”。CT比率/孔径由现场数据决定，未知不能给任意型号或数量已齐结论。SEC内含表的 `included` 归属是SEC产品，与逆变器随附表分别记账 |
| 通信与具体连接 | ET-S PDF9/15说明112.6类柜有内置Ezlink，逆变器通过smart stick接本地电池系统，再经LAN把并联信息交SEC；SEC-U PDF54要求储能逆变器经stick接入时使用 **WiFi/LAN Kit-20≥V2.5.49**。ET-S PDF33要求电池并柜/cloud-board线为 **CAT5E及以上屏蔽网线、RJ45、EIA/TIA568B**，客户准备 | 首段要声明每台转换器的stick/本地CAN和柜组间LAN路径，再接同一个SEC。不能将图上CAN和LAN混作同一边。Kit/线缆的随附量未由当前feed证明，先保留安装需求；未映射件不进入Woo销售行 |
| 电池监控数量 | ET-U PDF178 的cloud-board通信写可连接 **60个电池系统**，并规定配对路由器及标准屏蔽网线；联网与否影响CELL/PACK信息可见性 | 这是监控通信层，不修改同一DC电池组最多4柜或一个电池只能接一台逆变器的规则。严禁把60当能量拓扑/并联柜上限 |

上表各数字必须跟随适用模式/端口/网络/文件，不得在UI或engine只剩一个 `parallel_max`。三相事实已在现维护ET资料内，首段为 `phase=3`；不能从“3相”推断任意国家、接地系统或并网证书全部适用。设备/控制器/电池BMS的实际固件与调试状态尚未取得，属于项目需要核实的条件。

### 7.3 最少的 Woo 维护增量及现有 schema 的实际能力

以下是待实施合同 I，不是已写入的产品事实。身份、文件和原文条件仍只维护在 Woo；运行侧编译同一维护源，不另建外部事实包。

1. **已能容纳的字段先复用。** `CompatibilityClaims.php:150–168` / `CompatibilityEditor.php:117–121` 已接受正整数 `phase` 和 `max_units`；`accessories` 能记录 `product_id=2409, quantity=1, per=system`，文件可绑定 `document_id/blob_sha256/document_revision/product_id/page`。现有 `Requirement` 投影也保留这两个整数。因此不需要发明另一套产品身份或纯数值并机上限字段。
2. **一个未分域的 `max_units` 尚不够。** 当前 requirement 只有kind、included、phase、max_units、accessories、EN/DE文字条件和来源，没有可执行的 mode、通信方式、固件目标或电池归属条件；`requirements(inverter_model, kind, inverter_id)` 也不接 mode。并列写两条15/6却不扩条件匹配会被同时读出，不能据此选择正确限制。最小增量是在同一Woo claim中增加具类型的适用域（至少 `operating_mode`、`control_network`、实际部件/firmware条件）及明确条件状态，再分别维护grid与backup声明。不能从EN/DE句子解析“备电/15台”替代结构。
3. **组合同样在 Woo 事实编译层。** ET三型号：phase3、两电池口、模式数量/固件、1 SEC/组；2409：内含GM330×1、LAN/RS485的各自上限、Kit固件；1954/1955：整柜、4柜/组、组内同型号、单逆变器归属。非商品安装件（CT/线缆/Kit未映射）是有规格/证据但缺当前销售身份的需求，不伪造accessory产品ID。BMS/CAN与LAN是明确端口类型，不能由品牌相同推断兼容。
4. **首段可执行范围。** 先提供两台同型号1946（也可随后逐型号开放1947/1948）、各一自有1955柜组、一个2409、三相并网公共计量点的候选。每台的电池组和PV串独立归属，能流按每台设备实际功率/电池窗口计算后汇总到公共点；削峰调度需受整个并网点计量约束。控制器协调权、现场固件、CT和安装设计仍是具名条件。报告/BOM应数2台转换器、实际每台柜数、1个SEC及其内含GM330，不能把两台单机结果仅相加后称为完整多机拓扑。
5. **后续尚未解决。** 网联ET表格分页说明的精确适用范围；ET15与SEC LAN10之间的可用网络/版本；异型号converter混用；61.4的备电；375K/750K的Woo维护身份；Kit/CT/线缆实际随附/采购身份；现场固件、额定条件与调试。它们各自限制对应范围，不阻止实现两台112.6独立电池组的纯并网建模，也不能被已有pair=`released`或计算成功吞掉。

本节没有新增测试矩阵。后续只须围绕上述首段验证实例/归属、模式和数量守卫、SEC/内含表数量以及当前Woo来源读回；未变化的功率/电压原件与既有数值证据沿用。


### 7.4 本轮新增的外部核实与边界

新增外部动作只有 Apify。`apify/google-search-scraper` run `O52xHxCB3qBjTpfb2` / dataset `qWbiqBnihRggMzZB9` 于 `2026-10-26T01:58:26Z` 成功，重新定位两个厂商原域链接：[GoodWe Solution Manual](https://fr.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_Commercial-Smart-Inverter-Solutions_User-Manual-ET100kW-EN.pdf)、[GoodWe User Manual](https://en.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_ET-100kW_User-Manual-EN.pdf)。此步只证明官方定位仍可被检索；不把搜索摘要当新的参数依据。

随后 `apify/website-content-crawler` run `oDbT3dcJYxMhHZFdI` / dataset `wBwUyjrHt8ggiPBlq` 取这两份原域PDF，日志显示目标响应流连续超时、0份正文取回。已停止相同重试；没有改用普通搜索或绕过Apify下载。Apify检索本身成功，失败落在GoodWe大PDF响应流，不能将它声称为完成最新版/字节同一性核验。本节的技术结论全部依赖7.1中已有Woo关联、本地已持有并核过字节和页码的原件；官方原域最新字节仍为未核实。五张仅供读图的临时PNG共1,225,875字节已删除，没有另建报告、源文件副本、测试脚本或运行实例。


## 8. 近场遮挡：已有竞品源码复核与下一实现边界

2026-10-28 直接读取 EVIDENCE.json 已登记、现仍保留的 Aladdin 固定源码包，没有再次下载、解包副本或外部搜索。`src/analysis/solarPanelSimulation.tsx` 实际 SHA-256 为 `d734be994a8eb4b36484abf660eb5d015de7dcc5c678e9661e3261bb951407e9`，版本仍为 `7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa`。

- **S：可复用的方法边界。** 该路径第 791–818 行在面板采样位置逐点判断直射光；第 1231–1239 行用 Three.js Raycaster 与场景对象求交，并排除当前面板。它提供几何遮挡采样的成熟参考，不能把视觉 shadow map 当作计算结果。
- **S：不能直接当作真实组件电损合同。** 第 826–855 行根据 shadeTolerance 分支聚合采样，其中 PARTIAL 明写每两列电池片共用旁路二极管的假设；第 772–807 行的间接辐照先由独立函数给出，所检视的逐点遮挡判断只限制后续直射项。这些固定假设不能据此批准当前 Woo 组件的实际半片/旁路拓扑，也不证明近障碍物对散射辐照或整串 MPPT 的影响已被解决。结论仅限本次检视路径。
- **I：下一实现须拆清计算证据。** 在当前 ENU 几何和太阳时序上生成有输入 hash、采样分辨率、时间语义及收敛依据的逐组件直射透过率；保留障碍物、相邻排与自相交排除的可追溯身份。其后分别处理散射遮蔽和电气响应。电损层必须读取 Woo 维护的组件/组串/旁路/转换器证据，缺少拓扑时保留具名缺项，不能用遮挡面积比例冒充功率损失。

当前已验收的 uniform_unshaded_pvlib_reference_v1 保留为独立未遮挡基线；本节没有把它升级为遮挡模型。几何、散射、电气遮挡与完整年能量集成仍属于完整目标，均未因本节复核而完成。本次只复用现有源码证据，没有新增测试、计算任务或运行副本。
