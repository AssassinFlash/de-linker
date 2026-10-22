# 架构挑战：完整规划能力应由哪个 Module 承担？

日期：2026-10-22。状态：独立研究建议，供整体重设计决策；不是已批准的架构裁定，也没有实施改动。

**推荐方案②：独立规划应用及领域内核的模块化单体，HTTP与持久worker两个运行进程，共用一个版本化项目模型和同一份领域实现；WordPress/WooCommerce通过Adapter承担身份与商务。** 几何、PV、储能运行、设备选型和报告作为同一规划Module内部的协作Module，通过进程内调用完成计算。前端可独立表达完整规划工作流，部署初期用静态React/TypeScript资产，不因“现代化”增加Node SSR或拆微服务。

推荐的原因是已核实的物理与业务关系：GW80K+GW61.4需要同时考虑端口、电压、整柜电流及模式；ETA备电需要联立电池峰值、逆变器峰值及持续时间；ESA并机需要控制/拓扑/地域与STS条件；H2需要逐串电压与BC2身份。它们不能靠单个“计算器”依次返回几个数字拼成可信系统。[原始手册研究及证据](README.md)

## 1. 判断尺度与已知事实

采用本次已读的 [codebase-design SKILL.md](/Users/chesterjohn/.agents/skills/codebase-design/SKILL.md) 与 [DEEPENING.md](/Users/chesterjohn/.agents/skills/codebase-design/DEEPENING.md) 词汇：

- **Module** 有一个 **Interface** 和其 **Implementation**。Interface包括类型、前置条件、不变量、顺序、错误、配置与性能；不是只列几个HTTP路径。
- **Depth** 看调用者学会少量Interface后能获得多少完整行为。复杂计算可由多个内部Module组成，不必把内部细节全部暴露给调用者。
- **Seam** 是Interface所在的位置；**Adapter** 是在该处满足Interface的具体实现。只有真实差异才建立可替换Seam，不为每个计算函数建立空接口。
- 以 **Leverage** 检查浏览器、Genie、PDF和商务是否能消费同一可信结果；以 **Locality** 检查设备事实与约束修正能否集中修改、集中验证。

本次只读源码基线为 `123aea57`，硬件证据固定在 `74aa66b921dfad70af92fe909663dfcf62978f92`。相关现状证据：

| 现状证据 | 对新设计的约束 |
| --- | --- |
| [app.py:184](../../../../services/engine/src/linker_engine/app.py#L184) 起分别提供住宅、工商业、屋顶描边、排布与PDF路径 | 路径现状不是将来Module划分的充分理由。屋顶应作为项目输入与结果的一部分，住宅/工商业是项目需求与适用方法的差异 |
| [app.py:217](../../../../services/engine/src/linker_engine/app.py#L217) 的PDF路径重新执行 `residential.design` | 读报告需要冻结的run结果，不能依赖下载时再抓气象/再读设备/再选型 |
| [models.py:154](../../../../services/engine/src/linker_engine/models.py#L154) 的兼容结果主要是verdict、文字条件与文档；[models.py:206](../../../../services/engine/src/linker_engine/models.py#L206) 的BatteryChoice主要是商品、数量、栈数、kWh与release | 新能力模型须能表达端口与拓扑、条件化功率及附件。不能将这些现有字段当新合同的上限 |
| [SolutionsRoute.php:107](../../../../plugins/linker-commerce/includes/Account/SolutionsRoute.php#L107) 接收浏览器提交的input、商品行和可选PDF，访客返回202、账号返回201 | 新项目/运行快照需要服务端权威；所有权与持久化结果也应为独立状态，不能以“HTTP成功”代替“已存账号” |
| [EngineProxy.php:55](../../../../plugins/linker-tools/includes/Configurator/EngineProxy.php#L55) 转发多个路径；[EngineProxy.php:221](../../../../plugins/linker-tools/includes/Configurator/EngineProxy.php#L221) 的上游请求可占用60秒 | 长工作不宜占用浏览器→PHP→计算的整条同步请求；应短提交后取得持久run引用 |
| [services/engine/pyproject.toml](../../../../services/engine/pyproject.toml) 已有Python科学/几何/PDF依赖；[pdf.py](../../../../services/engine/src/linker_engine/pdf.py) 使用ReportLab | 不需要为使用这些能力另起Node渲染进程；现有实现仍需按新合同验证，不因库存在就直接接受旧逻辑 |

运行资源前提由本轮协调者的只读调查提供：VPS为1CPU、约4GB，Python进程已在跑，当前没有Node、Redis、Postgres二进制。本文没有再次探测或修改VPS，也没有量测新架构吞吐。资源结论只支持“保持初期进程和依赖精简”，不能支持某个并发量或性能承诺。

## 2. 三种真实可行方案的比较

| 维度 | ① WP/Woo主导项目状态，调用多个计算HTTP Interface | ② 独立规划应用/领域内核的模块化单体，HTTP+worker | ③ 几何、PV、储能、选型各自独立部署 |
| --- | --- | --- | --- |
| 项目权威 | WP持有项目revision、run、附件/报告清单，PHP编排计算 | 规划持久库持有项目revision、run与artifact；WP保有身份和商务 | 仍需一个项目协调Module；拆四个计算部署不能消除它 |
| 物理迭代与一致性 | PHP需要理解依赖与版本：换组件影响排布/组串，换逆变器影响电池端口/备电；Python结果不能各自独立“成功” | 同一内核固定输入及依赖版本，进程内交替计算、统一约束判定和发布run | 多次传递大型几何、时序、候选拓扑与版本；要处理部分失败、重复任务、乱序及跨部署兼容 |
| Depth / Locality | 可以做成deep Module，但需要在WP内新建完整领域编排与持久模型；复杂度容易分散到PHP、Python、浏览器 | 项目Interface隐藏数据获取、几何/PV/储能/设备求解及证明链；调用者只认识revision/run/artifact | 每个内部Module可有Depth，但外部协调Interface往往变浅：调用者仍需理解顺序和失败补偿 |
| 状态与持久工作 | 可用WP自定义表与持久任务机制做正确实现，不能说WP“做不到”；需避免普通post meta和请求生命周期成为事实模型 | SQLite事务队列候选，worker断点/重试，run快照与结果统一提交 | 需要跨进程任务投递、幂等、可观测性与数据契约治理，通常还会增加协调基础设施 |
| 身份与商务 | 原生会话与账号入口最直接；与站点部署/故障同一运行面 | 需要明确身份声明与商务handoff，初期集成成本更高 | 同样需要身份/商务Adapter，并增加内部部署间认证与授权 |
| 1CPU/约4GB初期运行 | 不新增项目持久库可少一项运维；长请求和多跳仍占资源，科学计算仍在Python | 一个Python发行包、短HTTP进程+单重活worker；增加一个小型规划库及其备份责任 | 能在一台机器上跑，但进程、缓存和依赖内存重复；在同一CPU上不产生可用的独立扩容收益 |
| 适合条件 | 工具长期保持简单、WP团队主导全部领域状态、计算很少需联立迭代，且接受PHP承担规划事务 | 当前完整屋顶→发电→负载/储能→设备/附件→报告→询盘目标 | 已实证不同资源规模、独立发布团队/合规隔离或昂贵计算故障隔离需求 |

①并不天然错误。如果决定WP是规划权威，就应认真建立WP内deep Module，而不是继续让浏览器收集各路HTTP结果。与②相比，它把项目事务和科学计算分置PHP/Python两侧，对当前团队与能力目标没有明显收益。

③也并非永远不合适。当前没有独立扩容/团队的证据。提前把几何、PV、储能和选型变成部署划分，会先支付分布式协调代价；其后仍要解决设备功率、项目版本和报告一致性的核心问题。暂保留进程内Module，未来按实测热点及故障面决定提取哪一个Implementation。

## 3. 推荐的Module、Interface与事实权威

建议按以下职责组织Implementation，不按现有HTTP路径保留旧形状：

| Module | 职责与内部Interface | 事实权威 / 不应承担的事实 |
| --- | --- | --- |
| **Project Workspace** | 项目创建/修订、权限、run请求、结果读取、artifact及handoff引用；外部统一Interface | 用户已提交的需求、明确确认的假设、不可变revision、归属关系；不把浏览器UI状态当已提交事实 |
| **Planning Kernel** | 基于固定revision及证据包形成候选系统；联立几何、PV、负载、储能、端口与附件约束，输出证明/失败/未知 | 一次run的推导结果；不拥有商品价格、库存或厂商原始事实 |
| **Site & Geometry** | 坐标/CRS、屋面、障碍、手绘与自动来源、排布、面积/倾角/方位及精度说明 | 官方/用户来源记录与几何变换；不认证结构安全、消防通道或屋面承载 |
| **Energy Analysis** | 气象与发电时序、负载时序、储能调度与备电工况 | 版本化气象/负载与方法的计算结果；没有时序/方法适用性时保留估算或未知，不冒充仿真 |
| **Device Capabilities** | 精确型号、端口、模式化能力、时长/SOC/温度条件、串并联、控制/附件关系、厂家配对及证据 | 人工核实并版本化的工程事实与派生规则；原始厂商资料优先，冲突/无法映射不得自动批准 |
| **System Synthesis** | 产生拓扑、分配设备/端口/串栈、联立约束、排序并给排除原因；与Energy Analysis迭代 | 可解释的可行性证明；“厂家配对compatible”仅是其中一个约束 |
| **Project Store & Jobs** | revision/run/artifact/任务的原子持久化、幂等、lease、fencing、版本冲突处理 | 哪次提交已落盘、哪份结果属于哪次run；不改写物理/商务结果 |
| **Report Projection** | 固定run→结构化报告→屏幕/PDF，EN/DE与Logo的artifact版本 | 已冻结结果的呈现；不重算/重选，不因改措辞提升可行性结论 |
| **Identity Adapter** | 从WP取得并验证账号/访客主体声明，归属转移的证明与授权 | WP账号与审批三态；规划库保有project→subject关系，无第二套密码库 |
| **Commerce Adapter** | Woo商品映射、当前可售/库存/账号价权限、solution draft与询盘交接回执 | Woo商品发布、价格、库存与询盘记录；规划库保有工程版本和交接清单引用 |

typed capability graph是领域数据结构，不要求购买或安装图数据库。节点可以是设备、端口、储能模块、串栈、柜、控制器、附件；关系表达串联/并联/连接/控制/所需附件。能力记录保存物理量、模式、额定/连续/最大/峰值、秒数和条件表达式，并连接原件SHA、精确型号列、物理页、修订、原字段及核实记录。派生规则还记录推导及其输入证据。

Woo商品ID作为商务映射，不能成为设备物理身份。例如同一个模块可参与多种合法拓扑，完整柜产品含PCS，BC2是控制器且不增加能量。商品上架、缺货或价格变化不应改写历史工程事实；工程证据修订也不应改写已发出的询盘快照。

**internal seams**应按真实变化设立：

- 几何、时序和约束推导是进程内依赖，直接组合与测试，不为它们添加HTTP Adapter。
- 不同国家官方几何来源、手绘输入，以及外部PVGIS与录制响应是可证明的差异；源获取有注入的Adapter，数据转换和适用性判定集中在对应Module。
- WP身份/商务是真实远端依赖；生产HTTP Adapter与本地受控协议夹具共享同一个Interface。
- SQLite是初期唯一持久Implementation时，先给Project Store清晰Interface并用真实临时SQLite验证事务；没有第二个需求就不建立泛型多数据库框架。
- 屏幕与PDF为同一结构化报告的两个呈现Implementation，共用状态/数据；各自渲染测试不重新定义工程逻辑。

## 4. 外部核心Interface：调用者只需理解项目、revision、run和artifact

下面是语义草图，不是已有类型或冻结协议。actor由Identity Adapter验证，不能由浏览器正文指定账号。幂等键由请求者提供，服务器按主体、操作及载荷哈希约束其复用。

```text
PlanningWorkspace.create(seed, actor, idempotency_key) -> ProjectRef
PlanningWorkspace.revise(project_ref, expected_revision, changes, actor, key)
    -> RevisionRef
PlanningWorkspace.evaluate(revision_ref, actor, key) -> RunRef
PlanningWorkspace.read(project_ref | run_ref, actor) -> ProjectView | RunView
PlanningWorkspace.render_report(run_ref, format, locale, branding_ref, actor, key)
    -> ArtifactJobRef
PlanningWorkspace.prepare_handoff(run_ref, candidate_ref, intent, actor, key)
    -> HandoffRef
```

`seed/changes`是用户能理解的项目数据：位置/国家、屋面及来源、现有设备、负载/时序、备电负载及冲击/持续时间、设计目标、安装/并网条件、用户确认的假设。住宅/商业是需求模板和方法适用性的一部分，不能在数据模型上堵住商业屋面。

`evaluate`由服务器选取并固定可用证据/方法/代码版本，run与任务事务提交成功后才返回持久引用（HTTP适配可用202）；接受排队不表示计算成功。不要求浏览器知道先调几何、再PV、再储能、再选型。用户换候选硬件或确认一个新假设，需要形成有记录的revision/派生方案选择，再产生可追溯run，不通过客户端直接改已计算BOM。

内部Kernel的核心Interface可以更小：

```text
PlanningKernel.evaluate(frozen_project, planning_context)
    -> Assessment | NeedsEvidence
```

`planning_context`在Implementation内固定已验证的能力/证据、气象/规则/方法版本以及输入资产。生产与测试均跨此Seam取得候选、拓扑、BOM、指标、证明、失败与未知；纯计算不产生WP写入或邮件。真实外部获取在执行准备阶段完成，并以内容哈希资产交给Kernel。若需后续数据，Kernel返回有类型的NeedsEvidence（来源/请求参数/目的/所需版本），worker记录阶段、获取并固定资产后再次调用；外部调用顺序仍隐藏在Module内部，浏览器不编排它。不能在确定性内核里偷偷读“最新”。

### 调用者必须知道的不变量

1. **revision不可变且有乐观并发检查。** 修改使用expected_revision；旧标签页不得覆盖新修订。输入快照与资产哈希是run的精确对象。
2. **run固定依赖。** 代码/方法、能力图、兼容/国家规则、PV组件模型、气象与负载/几何资产、条件与假设均进入manifest。只固定digest然后执行时读当前文件不满足该不变量。
3. **结果原子发布。** 任务成功与完整Assessment引用在同一提交中可见；半写入BOM不能被读成完整系统。阶段性几何/发电预览可单独发布，必须有各自状态和版本。
4. **完成计算不等于可行。** 违反硬约束、缺证据、缺外部输入分别保留；数值有结果不能掩盖模式/附件尚未验证。
5. **读报告不重算。** 屏幕/PDF/Genie/handoff指向同一run；报告语言和Logo只改变artifact版本。重新计算创建新run，旧报告仍能说明其来源。
6. **新输入令旧结果脱离当前revision。** 系统可读取/下载明确标注的历史报告；不得继续把旧结果显示为当前输入的建议。新数据版本可提示可重算，不能静默改旧报告。
7. **工程与商务各有权威。** 计算出的附件和拓扑不能被WP按商品清单简化掉；Woo当前不可售/库存/价格变化只影响交接结果，不回写旧run。
8. **未知不能升格。** H2多串缺接线图、GW61.4备电缺专项证据等，在所有呈现和交接中保留。访客也可发询盘；待核项目可随询盘交给团队，但不能被称为完整已验证系统。
9. **国际化不改变物理语义。** 国家影响电网/认证/数据适用规则；locale影响呈现。EN/DE报告来自同一Assessment，不以翻译创造证据。
10. **可行性与推荐排序分开。** 每个候选先通过约束，再按项目明确目标和可追溯方法排序。搜索预算/剪枝和未覆盖组合需记录；没有完整性证明就不能宣称全局最优。相同输入与固定上下文需要稳定的候选与排除解释。

### 三组独立状态

| 状态轴 | 建议值与意义 |
| --- | --- |
| 任务执行 | `queued / running / retry_wait / succeeded / failed / cancelled`，包含阶段、重试原因与最后更新；succeeded仅表示计算正常完成 |
| 工程Assessment | `feasible_for_stated_scope / conditional / infeasible / insufficient_evidence`，附已检查scope、约束通过/失败/未知、未覆盖的结构/消防/并网认证等；不能只返回一个released |
| 结果与当前项目关系 | 当前revision对应、输入已变更、或存在新证据可重算；是从revision/run/evidence版本推导的关系 |

归属/持久化另有明确回执：`guest_private`、`account_owned`，以及保存的revision/run引用。商务交接也有独立的prepared/submitted/confirmed/rejected结果。这些不能折叠为一个“saved”布尔值。

### 错误与恢复

| 错误/结果 | Interface行为 |
| --- | --- |
| 字段或物理维度非法 | `invalid_input`，定位字段/资产/单位，提交不改变现有revision；不得将德语小数逗号悄悄读成0 |
| expected revision不一致 | `revision_conflict`，返回当前revision引用；由用户合并/确认，不能静默覆盖 |
| 同幂等键不同载荷 | `idempotency_conflict`；同载荷重试返回原引用 |
| 找不到合法系统 | 正常完成的`infeasible`及排除证据；不是网络错误，重试不能假装解决 |
| 缺少厂家字段/运行条件 | `insufficient_evidence`或conditional，列缺项；不能给0、默认C-rate或默认附件替代 |
| 外部图像/LoD2/PVGIS失败 | 任务记`source_unavailable`及可重试性；有边界的重试，保留已完成资产。可提供用户确认的手绘/其他数据路径，但不能把失败瓦片状态写成ready或静默编造气象 |
| 固定代码/数据版本不再可执行 | `version_unavailable`；不能用当前版本执行后仍标旧版本。选择恢复原发行包，或经明确重算创建新run |
| 权限、额度或资源超限 | 返回具体原因与恢复路径；既有项目和结果仍可读。单个重型项目不能耗尽所有交互请求 |
| 商务交接时商品停用/数量映射失效 | `commerce_conflict`及对应行；保留工程清单和差异，重新确认商务行，不悄悄删附件再成功 |

## 5. 数据版本、保存与报告/商务交接

建议的最小持久记录为 `projects`、不可变`project_revisions`、`runs`、`jobs`、内容寻址`assets`、`artifacts`和`handoffs`，并保存幂等/所有权关联。无需把用户每个鼠标移动都作为事件保存；几何编辑可本地暂存，明确提交的revision才是服务器权威。后端定期/离开页面时保存草稿的策略属于产品交互设计，必须有真实持久化回执。

run manifest至少固定以下内容：

- canonical项目输入、单位、坐标系/方位约定、时区/时步、资产内容哈希；负载间隔功率与区间电量、DST/缺测处理不能混用。
- 屋面/障碍/排布来源及精度，自动/手绘/假设身份；图像与几何的获取时间、提供者、许可/署名要求。
- 能力图与证据版本、国家/电网规则版本、方法适用性、solver代码发行包与配置；每项派生约束的证据输入。
- 气象响应及参数/年份、负载原件与清洗结果、系统候选/拓扑/运行工况、指标与限制。

重新计算可显式更新依赖，形成新run并展示变更原因；更正硬件事实时标记受影响历史run，保留原结论及纠正记录，不原地改旧数字。历史资料不满足新模型时，导入为有原出处的legacy artifact/旧方案，不能假装已通过新Kernel验证。

**保存**先在规划库持久化，再返回精确project/revision/run与owner状态。访客项目使用受控私有主体和可恢复期限；归属账号时验证WP登录主体及原访客占有证明，事务化转移owner，不能接受浏览器传入user_id。访客保留策略、上传资产大小和清理期限需在实施时按产品与容量决定，本研究没有擅定天数。

**报告**只消费冻结Assessment。PDF存储为有内容哈希的artifact，带run、模板版本、locale、Logo资产与生成时间。生成PDF失败不应回滚已成功的工程run；重试只重做报告。Genie读取同一个有权限的run/报告视图，不通过自然语言重新选型，也不把客户尚未确认的假设转成事实。

**商务交接**由Planning生成不可变manifest：project/revision/run、候选/拓扑、工程BOM与必需附件、缺项/条件、可售SKU映射及报告引用。必需工程约束尚为未知或失败时，handoff不得把该候选标作完整已验证方案；可以保留待核范围，以客户明确的询盘意图交给团队。WP通过可信服务器调用取manifest，再依据Woo当前事实生成solution draft或询盘。浏览器只提交引用和明确意图，不能自报一份已批准BOM。

跨规划库与WP不承诺分布式原子事务。以handoff_id作幂等键，记录发送/重试与WP回执；WP存该ID并对重复提交返回同一结果。超时后先查回执，不盲目创建第二份询盘。查询、准备交接与真正发送询盘是不同动作，准备方案/后台重试不能触发未经用户提交的真实询盘邮件。

商品映射、库存或价格在交接时变化，WP返回差异；工程run保持不变。若替换型号影响能力，需要新revision/run而非在商务层静默替换。“客户已批准方案”与“厂家兼容证据”也不是同一种身份或状态。

## 6. 在当前资源上如何运行，及不能回避的成本

初期建议一个Python发行包，两个由现有进程管理方式守护的进程：

1. **HTTP进程**：身份验证、短事务、项目读写、提交/查询任务、读artifact及handoff。重型计算不在请求中同步跑。
2. **持久worker进程**：初始同时执行一个重型任务，按阶段处理几何/气象/仿真/候选求解与PDF。并发数是待量测的运行配置，不是已证明容量；外部请求设置超时，工作量设置可解释预算，避免一个欧洲大项目长期占满队列。

单机持久化先评估SQLite与WAL，文件放本地持久磁盘，事务短，外部HTTP或长计算期间不持有写事务。任务入队与run创建在同一事务中；worker通过lease领取，领取代次/fencing防止旧worker晚回写覆盖新领取者。执行采用at-least-once并令发布幂等，不承诺无法证明的exactly-once。任务重启可继续/重试，阶段资产按内容哈希复用；不要把API进程内background task当持久队列。

这增加了规划数据库与资产备份、恢复、配额、迁移、访问控制及故障监控责任。SQLite单写者、单机可用性、磁盘容量与备份一致性都需要真实验证；如果队列等待、写锁竞争、数据量或高可用性需求超过已量测范围，再评估Postgres/独立队列或扩CPU。不能因“现在没有二进制”断言永远不用，也不能先安装三套基础设施再寻找需求。

部署HTTP与worker必须匹配同一发行包。已排队任务固定旧代码时，要保留执行该版本的能力或部署前有受控drain；若新进程无法执行旧manifest，就显式version_unavailable并创建重算流程。不能重启后用新代码偷偷续跑旧run。工程数据发布同样以不可变包切换，不能让每个进程各读到半个更新。

前端静态资产在构建环境生成；VPS无需Node SSR。通过正常TLS及反向代理提供规划Interface，同源身份交接可以避免把所有长工作继续串经PHP。WP登录依赖仍存在：验证新身份或商务操作时WP不可用会影响这些动作，短期凭据与已存工程结果并不等于完全解耦可用性。具体身份声明/路由需单独做威胁与会话验证，不能简单信任任意请求头或公开服务令牌。

现有Genie与其他Python进程也共享CPU/内存。新worker单并发并不自动保证聊天和页面响应，需要实测峰值内存、候选搜索时间、磁盘/外部依赖延迟、排队公平性和取消恢复。ReportLab可减少额外渲染运行时，但报告可读性仍需EN/DE真实渲染验收。

## 7. 用Interface验证架构，而不是用结构图证明成功

删除Project Workspace/Kernel后，如果同一份版本/约束逻辑重新出现在浏览器、WP、PDF和Genie中，说明它们提供了Depth。若删除一个新Module只少一层转发、调用者并未得到完整行为，应合并这个浅Module。不能靠目录数量或方法数量判定模块化。

新的主要验收跨外部Interface和Kernel Seam执行，不再叠一套只镜像旧字段与函数的测试：

- 手册反例从create/revise/evaluate进入：ET80+61.4的80kW电池独立供电、ETA6kVA持续备电、ESA星形16台、H2单模块均得到正确失败/未知及精确证据；附件与端口约束同时成立。
- 候选变化能联立影响几何/组串/发电/储能运行与BOM；没有从某一独立计算器复制未更新结果。
- 结果生成后更改输入或证据版本，旧报告保持原run且清晰为历史，新的当前结果需要新run；屏幕/PDF/Genie/handoff数值与scope一致。
- 创建run后杀掉本票独立worker并恢复，项目及任务可恢复；重复提交/重复交接不会生成第二份run或询盘。此处是实施验收设计，本轮没有操作任何进程。
- 地图/PVGIS失败、运行预算超限、无可行系统、缺厂家证据有不同恢复路径；不会全部变成“再试一次”或“完整系统”。
- 单机真实SQLite事务测试，外部使用录制源Adapter；另做有标识的真实源与WP商务协议验证。录制响应成功不代替当时外网成功。

实施顺序建议先完成证据合同与四组反例的Kernel纵向闭环，再加入项目/任务持久性和报告/商务Adapter，随后以真实项目及故障恢复验证整体Interface，最后基于这些状态制作用户原型。迁移时建立新的领域Interface与数据模型；现端点如需兼容，只做有退出条件的Adapter，上游迁移后移除。旧存量方案保留出处与旧结果，待验证后再转换。

最终切换需要独立的部署/回滚与客户路径验收，不在本研究执行范围。整体重设计允许替换现有结构，但保留的用户资产、URL、账号与询盘引用都要有明确映射；不能把重建架构当作丢失项目或重发询盘的理由。
