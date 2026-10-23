# 统一规划工作台：执行状态

2026-10-22，Codex负责。当前长期目标是完整实现、评审、迁移、发布与读回；用户已确认A版，并要求从头到尾无欠账。此文件是当前状态，不代表整体已交付。

## 已确认与已有资产

- [执行地图](https://github.com/AssassinFlash/de-linker/issues/548)已由规划阶段转为完整交付，早期“不实现/不部署”阶段限制已被本轮授权覆盖。
- 用户明确认可A·Journal统一项目工作台；[原型决定](https://github.com/AssassinFlash/de-linker/issues/553)已记录真实反馈并关闭。新材质/按钮细化按用户补充执行，没有冒称另获逐像素确认。
- 最新原型分支research/roof-workflow-prototype-553，提交9b361643；目录docs/prototypes/2026-10-22-planning-dashboard。localhost8794继续运行，行为JS未变（SHA256 9ea451c355df6f120623aabf26c65addb9b92bf02474b1008368798e4f24444d）。
- 视觉现采用站点40项既有token、Plus Jakarta Sans、teal-600、44px主控制、4/8px控制圆角、通栏侧栏和无卡片框指标。EN/DE手机、键盘焦点与德文长标签等高已核。材质效果和截图限制在原型VISUAL-REFINEMENT.md。
- 研究资产继续保留原研究分支，整体架构/范围/全站同步修复合同基于研究固定提交e1bfc71801e2a4a6f89fb95a5141264f348dd068。
- 本实施基线为origin/main 3bb955569eecc972b71df7cf4d5df69eb6aac41c。主工作树及其他任务未修改。
- 实施工作树：/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548；分支codex/unified-planner-548。
- 已完成just up p548，独立实例http://127.0.0.1:9347，邮件截获隔离。现已装入线上只读快照20261022-2309；212件已发布商品、2756个附件对齐，附件文件缺失0，线上地址残留0，主题/uploads/LC/WindPress及既有许可已带入。新应用的项目/brief页面已进行下文所述浏览器验收，完整路径仍在实施。
- [数值实施合同](../../../research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md)由独立研究代理完成；Apify新核6个官方页面，继承17条数值与4项物理参考，不重复研究。
- Apify三组现有凭证均HTTP200认证；已备份原配置并提供APIFY_TOKEN/ALT/PREV环境变量别名，受限配置在用户目录，Token未入库。真实Google-search-scraper已SUCCEEDED，dataset有1项且含SQLite官方结果，原始公共搜索证据在external目录。所有后续外部研究继续强制Apify，失败修复，不普通搜索fallback。

## 当前正在承担的工作

站点入口决定由本线认领；整体实施尚未完成。正式产品代码已写入services/engine/src/linker_engine/planning及apps/planner。新应用仅在p548的独立英德审查页挂载；正式工具入口仍由既有实现承接，生产尚未更新。

已实现并验证独立项目/修订/运行权威、幂等回执、每次读写归属检查、访客认领、不可变内容hash、持久租约队列、代次fencing、取消/重试/重启恢复、注册handler的独立worker与heartbeat、SQLite在线备份及完整资产恢复。合同在docs/specs/548-project-workspace.md，架构决定在docs/adr/0001-unified-project-authority.md。

基础项目/执行31项、时间/CSV/TZif/重采样27项已分别通过Spec与Standards独立固定提交复核。连续单AC能流及来源/命令/模式/独立合理算术与硬库存见证实现后，固定3c533482的planning组件110项通过，两个独立评审轴通过。记录分别在WORKSPACE-REVIEW.md、TIME-SERIES-REVIEW.md、ENERGY-REVIEW.md；不是设备/气象/全产品放行。

2026-10-23新增真实永久资产/CSV导入→项目运行→注册EnergyKernel Worker→轨迹/指标/独立验证链。客户端不能选运行时或拿另一个hash替换项目选定的asset ID；原文件、映射、TZif、runtime源文件/lock/平台身份固定。变更后的项目不覆盖旧run；server设置变更后的重复意图复用原回执。永久CAS拒绝有时限provider原数据；asset/result子依赖也进入备份校验。19项新真实链路夹具与既有组件合计129项通过后，独立评审找到并修复严格schema版本类型缺口，增加12项回归。固定685773a1的planning141项、两个独立评审轴均通过；整引擎298项通过（19.49s），mypy/ruff/format通过。记录在ENERGY-JOB-REVIEW.md。尚未公开挂载、未部署。

地图接入研究已形成MAP-ADAPTER.md，经Apify七组成功run核28个官方页面。Google地图/地点与Solar自动数据分别对待；成熟绘图层、来源权利、留存与米制领域边界须落实到实际适配器，不借第三方key、不把原型没画地图当取消技术路线。受时限数据的缓存/备份生命周期仍需实际实现，永久资产路径不能冒充已覆盖它。

2026-10-23已接通真实PVGIS原件→owned asset→冻结run→EnergyKernel Worker→连续能流与指标。Apify取回ERA5/SARAH3各8784行完整2020原文，保存精确URL/HTTP/MIME/UTC/原文hash；ERA5中心均值与SARAH瞬时时点显式重建分开，不重复扣loss。真实Unknown技术响应整年无P、北向-180被返回-179的错配均拒绝。独立评审找到超范围JSON整数裸OverflowError并修复，新增两个回归；最终37198e86的183项planning、340项整引擎独立通过，Spec/Standards均通过。固定记录在PVGIS-REVIEW.md；没有将小时天气当实际15分钟峰值，也没有公开挂载、部署或授予设备放行。

真实产品输入与原生身份研究已入库：2026-10-23-capability-inputs/FACT-INTAKE.md确认大量原值/条件没有穿过现有feed，并记录AU/BEU版本冲突；2026-10-23-planning-gateway/NATIVE-IDENTITY.md核本机WP/Woo签名session、guest→user专门hook、CartToken克隆与nonce/Origin边界。它们不是已经修好或真实HTTP已验收的声明。全106件源产品现已补齐原字段/引用库存，见2026-10-23-fact-sources/SOURCE-BINDINGS.md：2482项原图值、80个文档字节版本，分开精确文件身份、已核目标和未决候选；条件/多源引用不再被研究清单丢弃。新feed/capability编译器及逐字段工程放行仍待实现，不能把来源绑定数量当作已核产品能力。

2026-10-23私有RPC工厂通过独立双轴复核，最终bc68b112，见PRIVATE-GATEWAY-REVIEW.md。每种方法先服务鉴权，再接受WP私有主体；真实资产/项目/运行/轨迹路径均检查归属。独立反例推动同批修复错误协议、递归验证放大、UTF16/32深度绕过及框架外异常。尚未公开挂载，不是WP原生身份验收。

整访客接管与退役最终726557ac通过双轴复核，见SESSION-CLAIM-REVIEW.md。所有项目/历史原子转移，数据库约束同时阻止已启动旧进程重新创建退役访客项目；schema1→2、回滚、旧备份恢复、跨进程竞争均有实际证据。整engine395项通过，mypy/ruff通过。WP原生会话/登录hook/耐久outbox和真实浏览器仍未接通，不能把私有双主体夹具当作用户登录路径已完成。

业主补充：允许现代架构与新库，先正确使用，再采用当前稳定现代技术；并明确不能只考虑3D。新局部前端决定见docs/adr/0002-isolated-planner-runtime.md，整套应用合同见docs/specs/548-workbench-application.md。能力映射2026-10-23-modern-workbench/CAPABILITY-MAP.md覆盖W01–W22及A–D真实路径，区分实操、源码、官方描述与本站推导。React19/Fiber9/Drei10/Three/Vite与Query/ECharts/Ajv官方证据均经Apify取得；旧站wp.element保持隔离，WindPress仍是唯一样式编译管线。

apps/planner已进入真实本地应用实现：独立React19构建、原生WP module/gettext挂载、同一WindPress编译管线、项目列表/创建、brief编辑、不可变保存意图、修订确认与IndexedDB恢复。24项前端/协议/几何/历史/恢复夹具与严格类型通过。p548的独立EN/DE审查页已建立，未替换正式工具入口；真实浏览器已完成挪威工商业项目输入、保存到修订3、刷新恢复、未保存内容离开再重开及撤销到已存版本。实测页头遮挡保存栏和语言切换丢项目引用已修；新版恢复、冲突比较和手机/德语仍继续验收。实际地图/3D renderer、CSV intake UI、计算/设备资格与全站交接尚在同次实施中。8794原型保持独立。

项目/brief增量的逐轮独立问题与修复见APP-REVIEW.md，文案见APP-COPY-REVIEW.md。当前25项Node与15项React/DOM夹具通过，原生IndexedDB的七条升级/并发/隔离/保留夹具已在浏览器执行。英德1440/390项目编辑、索引、手机保存到修订4并刷新读回、德语非法数字、锚点与原生Genie共存已实测。两标签页在可控本地服务失败后，各自的创建意图均保留并能明确选择重试；原页面再次重试取得相同项目ID，没有重复创建。临时故障夹具已移除。最新关闭恢复和创建队列增量仍待独立固定提交复核；完整A、访客登录浏览器路径与跨身份未知创建恢复、CSV和后续路径继续实施。

原生网关、永久回执与brief输入边界最终ca4918ef通过两轮独立评审，planning294项通过。前序失败、修复及限制见NATIVE-GATEWAY-REVIEW.md。WP/Woo原生会话、登录hook、耐久认领outbox、Origin/nonce与实际服务已接通；原生夹具与浏览器工作分别记录，不能把后端组件通过当完整工具或生产验收。

继续落实几何/详细PV链/设备条件/国家包与报告、统一React工作台、WP身份/上传网关、Genie与Woo交接及全站入口/旧资料迁移。输入修改不能覆盖旧结果，任务成功不能等同工程放行，所有消费者读取同一冻结运行。每部分纳入同次验收，不以组件完成结案。

## 最终过关条件

- 面向住宅、工商业、全欧洲的项目输入与适用域真实实现；未知资料有明确证据状态，不伪造通过，不通过删能力缩减目标。
- 正式计算以独立参考、量纲/时间轴/能量与功率守恒及厂商条件证明；不是原型矩形示例算术。
- 屏幕/账户/Genie/PDF/草稿/询盘/团队保留同一project/revision/run/BOM与依据；真实保存刷新重开及跨账号隔离。
- 首页/导航/产品/相关内容/语言/SEO/LC-WindPress/同意/统计/服务发布等消费者同步修复，旧URL与记录保留事实和恢复路径。
- 相应真实夹具、Spec与Standards独立评审、EN/DE × 1440/390关键状态、隔离站完整路径、评审站与生产备份/迁移/发布/读回均完成。
- 本轮发现和本次重构引发的问题在同批修复；未过关则整体目标保持active，不留下正式交付后的TODO或另开欠账。

生产模型路由、测试邮件与备份纪律继续按AGENTS执行。原型不直接晋升生产，不把此执行状态当发布完成。

最新项目/brief/恢复组件在固定aefd6f26通过Spec与Standards双轴独立复核，新增恢复文案同步定稿；前序失败没有抹除，完整记录见APP-REVIEW.md。此门只关闭已实现组件，不关闭A或整体交付。接下来继续原始CSV/映射/质量预览、跨身份未知创建协调与访客登录浏览器路径，再接设计和计算链。

资料解释服务已接入真实私有/原生网关：结构化CSV错误保留安全的issue、物理起始行和字段角色；只读preview固定原件/metadata/TZif与PVGIS解释，返回全量覆盖、缺口、能量和区间均值范围，分页不改变指标。314项planning夹具通过，mypy/ruff、PHP289项及原生新HTTP夹具通过；两个真实JRC原件继续保留模型均值与重建的差别。固定提交双轴复核尚未完成，CSV前端上传/列预览/映射/错误本地化/待确认上传恢复仍在同一次实现中，不把服务存在当作UI已可用。

原件解释服务最终220c824e通过双轴独立复核；随后完整CSV前端导入增量最终432d8629通过双轴，失败轮次与修复保留在PROFILE-INTAKE-REVIEW.md及PROFILE-WORKFLOW-REVIEW.md。真实文件选择→私有列预览→单位/计量点/时区/DST显式映射→质量与来源→选入草稿→服务器保存→刷新/英德读回已在p548完成。323项planning、25项Node/32项真实React及原生IndexedDB升级/隔离/容量夹具通过；独立轴另重放其原失败探针。原生测试发现的隐藏错误、成功后滚到页脚、验证交错抢焦点和撤销后过期提示均已同轮修正。EN/DE×1440/390截图、原文件、visible readback及source/build哈希在profile-native/acceptance.json；本增量英德文案已对抗评审、选择应用并实际核验。未切换正式工具URL、未写生产、未发真实邮件。

整体目标继续active。下一步在同一项目权威上验实访客登录和跨身份未知意图接续，再推进同ID的地图/2D/3D/树/属性、约束与方案分支；计算图/设备国家证据及全部站点消费者仍须完成，不能用已接受的导入组件或已安装的3D包提前结案。

2026-10-23跨身份未知回执与恢复组件最终01ac29ea、可读原始设置ef30778d均通过独立Spec/Standards复核；逐轮失败及同轮修复在HANDOVER-REVIEW.md。真实原生登录前后，未知创建明确重试仍回到同一项目；未知CSV经英德桌面/手机保留原文件/映射，实际账户接管后明确重试仍回到同一asset。选入并保存revision2、刷新及英德读回完成。额外原生discovery503时，创建入口暂停，但已有项目仍保存到revision3；移除故障后主动检查会话，查询与创建恢复，revision3及原source/hash不变。两份故障夹具与状态均已移除。来源/截图方法/各阶段与最终只读CAS证据在handover-native/acceptance.json。此门只接受恢复与设置，不关闭A或整体目标；继续统一编辑以及文件/账户入口义务。

已接收业主最新磁盘边界（主工作树AGENTS.md §0及docs/agents/local-storage.md），本任务沿用p548一个实例、unified-planner-548一个实施工作树；prototype-roof-workflow-553仅作已批准设计基准对照，完整工具视觉验收取代它后回收运行依赖。无新全量备份/实例。四份本任务已完成评审档案中，已按固定提交Git blob逐文件核对并删除11,206,159,877字节可重建副本；唯一探针、证据、未提交内容及符号链接保留。后续评审仅最小源码材料和依赖链接，不再复制全库证据/快照。当前实例及实施工作树保留至整体生产读回与交付结束；完成评审临时副本当轮回收，独立证据归入同一验收目录。

同轮又回收32份已完成且固定提交可唯一识别的本任务评审源码档案，共38,077个逐blob核对的文件、857,304,678字节。未匹配内容、独立探针及依赖符号链接不删；两份并发/真实存储失败独立探针已另收入handover-probes。详细回收清单留在当前任务artifacts，不新建一套存储规则。
