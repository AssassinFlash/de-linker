# 配置器：当前输入操作与工作台重排

目标：[全欧洲系统方案配置器正式落地并接入 Linker 客户链路](https://github.com/AssassinFlash/de-linker/issues/1132)。基线 `a92cda3a8`；主候选经 PR 1134 合并并发布为 `21d9375d5`。生产验收发现的日期失败恢复增量经 PR 1135 合并并发布为 `4bc3d3b82`，生产更正计算与临时项目回收完成。

## 模板改版重新执行（业主校正）

业主再次指出现有界面未达到指定 Preline productivity 模板的改版要求。此前侧栏、面板与表单整理不能作为该设计目标完成的证据。新分支 `codex/planner-preline-workspace` 继续这一目标，先实看模板与现状再按页面结构实现。

资源由主线负责：复用现有工作树与 review 数据；模板预览 `127.0.0.1:8897` 只读服务指定模板根目录，最多一个进程，实看后停止；一个浏览器任务空间内复用两页用于模板／产品对照；工作截图 `/tmp/linker-template-current.png` 与 `/tmp/linker-product-current.png` 各一份，最终对照归档后删除。独立实现线各最多一个隔离树，无独立站点，明确文件归属后启动；整合验证后回收。当前磁盘可用约 1.29 TB。

实际参照 `productivity/project-management/project-details.html` 与 `setup.html`：项目标题和横向章节导航进入深色 masthead，目录与编辑内容居中；概览先列真实项目属性，下接屋顶预览与继续操作列表；能量设置由重复的简版／Advanced 编辑器改为单一章节编辑器；报告下载与正文分栏，比较结果与计算依据分栏。颜色使用现有 Linker teal900 与中性色 tokens。模板里的演示预算、进度、任务状态未引入。

集成首轮验证发现未知储能规模的新项目默认展示参数章，遮住原有运行目标到设备选择入口；已改为默认打开 Operation，仅初始化一次，后续章节选择保留。报告下载相关五项旧测试绑定了已移走的标题区按钮；改为按可见按钮文字查找后通过，下载、取消与旧报告标记断言保留。设备采用和德语百分比测试明确打开 Storage 后原业务断言通过，设备生命周期 15 项、PV 设置 5 项集成通过。全套域／数据 273 项通过；组件首轮通过结果与受影响文件补测共同覆盖最终逻辑，后续 CSS 调整不改变这些输入输出。

主线已实看 EN 桌面／手机概览与光伏空工作区、桌面设置与比较、EN 手机报告，DE 桌面／手机项目、用能、设备、安装布线与报告。EN／DE 新建入口在 390 宽操作打开和取消，DE 1440 表单、EN 1440 目录完成实看。DE 390 空日期提交后，Operation 自动展开并定位可见日期框，显示完整修正提示；Undo 恢复 Oslo 保存版本 8。报告历史改为可横向滚动的选择条，实际从报告切换到版本 8 能量结果，再从手机历史打开报告；PDF、CSV 和草稿操作位于正文之前。Oslo 光伏空布局的地图切换显示缺少地理原点／真北依据，未把这一状态计为影像加载成功，恢复纯储能版本 8。

候选 `2ca563224` 的 CI run `44112405544` 全部适用检查通过。Spec 独立评审无发现；Standards 发现比较依据侧栏单列规则被后面的双列规则覆盖，已修正选择器并在 DE 1440 读回单列 230px 和实看确认。入口实看另发现目录品牌深字、白色新建表单被标题浅色规则污染，分别继承白色和收窄标题简介选择器；EN／DE 390 与 DE 1440 表单复看通过。最终三处 CSS 增量经 Standards 复审无新发现；最终候选 `e57711f2be5856283f069511ca5266e24fc77429` 的 CI run `44116361956` 全绿，Planner 域／数据 273 项、组件 402 项与构建模块 1 项全部通过，检查、两层构建校验及 Planner PHP 通过；PR [1137](https://github.com/AssassinFlash/de-linker/pull/1137) 于 2026-11-17 15:43:54 UTC 合并为 `8f0ef09b41f1479c328b4c21f7d7a713c1d7e93e`，合并树与最终候选相同。补看 EN 1440／390 项目、用能、设备、安装，EN 390 章节编辑器与比较；均保持保存版本 8。模板服务与 review 服务已停止，保留 review 数据以保护 Utrecht 草稿。生产批次 `20261117T154436386272Z-8f0ef09b4` 已原子切换；首次停于 WindPress 缓存检查，随后运行生产编译并续同一批次，站点验证、Search Console／consent 读回和备份归档全部成功（退出 0）。上一版代码保留于 `/home/u388076051/deploy-prev/20261117T154436386272Z-8f0ef09b4`，旧发布备份由工具回收。数据库恢复点 `/Users/chesterjohn/de-linker-data/snapshots/db-20261117T154447Z.sql.gz` 为 8,190,426 字节，压缩流读通；沿用原子上一版代码回滚，不更新 Planner 后端。生产 `planner.js`、`ProjectEditor-DNj4Witw.js` 和 `source-manifest.json` 与已审候选逐字节相同。浏览器实际加载 CSS `1794930631`，masthead 计算颜色为 `rgb(5,53,48)`。线上 EN 1440／390 概览、DE 390 概览与新建表单、DE 1440 章节编辑器及 EN 1440 目录实看通过；Amsterdam 屋顶预览为原有 8 块组件、3.6 kWp，保存版本保持 3。没有创建生产测试项目、提交询盘或发信。浏览器空间 15 已关闭；本地保留主工作树约 6.33 GB、停用的 review 文件约 4.94 GB，以保留后续完整目标工作与 Utrecht 草稿。

截图：[模板 setup](demand-to-system/preline-template-setup.png)、[德语桌面章节编辑器](demand-to-system/preline-setup-de-desktop.png)、[英文桌面概览](demand-to-system/preline-overview-en-desktop.png)、[德语手机报告操作](demand-to-system/preline-report-de-mobile.png)。两份实现工作树的 13 份改动与集成版本逐字节相同，无额外未跟踪文件、无活跃进程，已回收；可用空间从 1,279,374,786,560 增至 1,286,611,808,256 字节，实际增加 7,237,021,696 字节。两份只读评审树由工具回收。

最终 Spec／Standards 各一份只读隔离工作树已由工具回收。四张最终模板／产品对照图保留在本任务目录 `preline-*.png`；两张临时截图与 `/tmp/linker-template-pr.md` 已删除。模板服务、review 服务与浏览器空间均已关闭；发布 SSH 会话及 staging checkpoint 已由发布工具回收。收尾磁盘实读：已用 2,709,762,473,984 字节，可用 1,286,566,854,656 字节。主树和 review 数据按上述用途保留；完整配置器目标 #1132 继续开放。

## 2026-11-18 完整目标续作

主线从未知容量客户的真实需求入口继续 #1132，沿用已验证的计算、报告和发布证据。资源预算：复用当前主工作树与 `/Users/chesterjohn/de-linker-local/review`，只启动 PHP／Engine／Planner；保护 Utrecht 草稿与 Oslo 保存版本 8。浏览器使用一个任务空间、一页；工作截图复用 `/tmp/linker-demand-current.png`。最多一个本轮临时 review 项目，通过正常入口创建，记录 ID 后在验收结束删除。两条只读核对线各占一个自动隔离 worktree：需求到选型、改造到采购清单，不装依赖、不启动实例，核对结束回收；实际树为 `/Users/chesterjohn/Documents/de-linker/.claude/worktrees/agent-abcb48342a95df782`（保留设备）与 `/Users/chesterjohn/Documents/de-linker/.claude/worktrees/agent-a66ae8c2b6c838d0e`（需求选型）。浏览器空间 16，页面 p1。临时 review 项目 `26816d8c962c4ef9925060f4472e4214`，标题 `Goal 1132 — demand journey 2026-11-18`，Germany／Storage only，经正常入口创建。主线负责回收，期限为本轮结束或暂停。开始可用空间 1,287,423,975,424 字节。

两份调查已完成，复用上述工作树进行独立修复：`agent-abcb48342a95df782` 负责商业储能欧洲邮编输入，`agent-a66ae8c2b6c838d0e` 负责移除无厂商依据的通用 DC/AC 硬限制及其排名影响。每树只使用自身依赖，最多保留本轮所需一份；不另开站点、浏览器或工作树。主线负责整合后回收，截止本轮结束或暂停。

本轮核对：未知容量搜索可正常枚举 690 个组合，但 `_requirements()` 只读取手填 kW/kWh，不消费负载、备电时段或削峰目标。商业模块 `commercial.py:125–147` 按每日超峰总量与固定 `HTW_DISCHARGE_EFFICIENCY` 计算，不能作为项目连续仿真的定容依据直接回填。需求选型必须复用项目时序、明确损耗与初始储能条件，并由实际配置的能量回放报告未满足负载；年耗不生成任意容量倍率。

真实入口验收另使用 `/tmp/linker-demand-profile.csv`：主线负责，单份三小时合成负载（2／4／2 kW，明确为测试输入），仅导入本轮项目以验证备电／削峰回放，验收或暂停后删除；不把测试数值作为产品规则。

需求回放前端在现有公开 seam 增补 `apps/planner/tests/equipment-demand-result.test.tsx`（父线拥有，永久行为回归，无临时报告）；输入与候选结果继续保存在项目及现有 run 中，不建第二份状态存储。

### 需求比较集成进度（2026-11-18）

已集成可选需求声明、逐候选能量回放、容量相同的运行内复用、独立设备证据、需求结果筛选、冻结初始储能采纳与输入变更拒绝。全停电时段只要求关键负载；单系统和 AC 多系统保持同一规则，连接时段仍要求全站负载。集成后 Python dispatch／plant／equipment 共 157 项通过（124.66 s）；前端类型检查及本批五组测试通过。尚未发布，Shared DC／多系统需求搜索及完整目标验收仍待完成。

性能依据：35,040 个时段单容量原完整回放约 6.6 s，verify 原约 5.5 s。只在最坏检查更新时分配 Check，保留全部有限值／容差／约束判定；代理测得 verify 5.482→3.803 s，主线已检查实际差异并通过 157 项集成测试。中断的 InventoryWitness Fraction 优化未纳入。真实 review 保存搜索 `5d6066f213b7404ba21ca86a69dee884` 有 690 个组合、41 个不同已知容量；因此不能把六容量夹具的耗时冒充真实搜索耗时。

本地需求回放预算拟设 210,240 intervals（6 × 35,040）：按当前约 4.9 s／全年容量给物理回放约 30 s 的交互等待目标；设备枚举／证据仍需另外实测，不声称硬时限。三小时验收只需 41 × 3 = 123 intervals，预算足以覆盖该保存搜索全部容量；全年全目录会明确报告未回放组合，性能问题仍未闭环。临时恢复点 `/Users/chesterjohn/de-linker-local/review/planner/runtime.before-demand.json` 与 `workspace.before-demand.sqlite` 各一份，主线负责，配置与服务读回成功且无需恢复后删除；现有 blobs 不改写。

主线同进程对照全年 35,040 时段：HEAD verify 5.101 s、候选 3.293 s，93 项检查完整 document 相同；另两份篡改能量轨迹同样逐字段相同。缓存不变量：本次运行仅候选可用容量变化，充放电功率、效率及损耗来自同一明确情景；将来设备功率参与模拟时必须相应改变缓存依据。

真实 review 客户入口：原关键负载 2／4／2 kW 的三小时停电场景直接计算完成，版本 3、run `83c3d72b3de446e9a70064df61f9007b`，8 kWh 负载、0 kWh 缺供、0 kWh 网格进口。随后设备页勾选需求比较，100% 初始可用窗口、0 kWh 允许缺供、明确测试来源，直接搜索为版本 4、run `fad37dd919a34a16b4329950e7570253`。690 组合：455 满足声明情景、59 缺供、176 资料不足未评估；41 种容量仅回放 123 interval work，completion=complete。筛选缺供实际显示 4.8 kWh 候选缺供 3.2 kWh；筛选满足后采用 13.5 kWh 候选，Storage 容量与 Starting state 未知来源库存均为 13.5，来源说明来自冻结声明，保存版本 5。设备适用性仍独立标为证据未解。EN 桌面与 DE 390 页面实看，未提交询盘或发信。

最终本批检查：planner 域／数据 275 项、组件 408 项、构建模块 1 项通过；首轮格式检查仅命中 energyScenario.ts，格式化后重建，逻辑未变。Spec／Standards 评审各允许一个只读临时隔离树，不安装依赖、不启动站点，由主线在评审结束回收；唯一用途是本批候选，保留至发现修正完成。原前端代理树继续已知 PV 纵切，原后端树保留中断优化片段至主线确认取舍。

完整目标尚有四项核心缺口：设备功率／损耗依据进入需求定容；备电负载／时长直接输入；已知 PV 资料无需屋顶生成时序；多系统／shared DC 从项目总需求比较整套配置。现有 CSV 备电模拟、已选多系统模拟和采购链仍有效；不据本批关闭 #1132。

正式德语新增 21 条，复用原生 PO→MO／JSON 管线。文案对抗审阅：百分比字段使用“Anfangs nutzbarer Anteil der Speicherkapazität”；kWh 缺供指标使用“Ungedeckter Energiebedarf”；空筛选使用“Keine Kombination entspricht diesem Bedarfsfilter.”，避免把未评估筛选描述成满足需求。已有译文保留。

需求候选 `336671c37` 的 Spec 评审发现三项：冻结采用漏查影响 PV 时段的纯储能范围；切换多系统后保留隐藏需求声明；策略回放失败被描述成硬件不可满足。主线核实后修正，采用检查复用同一函数；多系统／shared DC／纯光伏切换移除不适用声明，现有 Undo 可恢复。结果提示改为 “This simulation did not meet the declared storage, reserve or end-state constraints.”／“Diese Simulation erfüllte die angegebenen Vorgaben für Speicher, Reserve oder Endzustand nicht.”，文案审阅保留本次模拟的证据范围，不断言所有策略均失败。新增回归先红后绿，最终相关域测试 23 项、组件测试 20 项、类型检查、翻译编译、两层构建校验通过。Standards 无硬规则违反；重复检查建议随同修复。增量复审复用原评审代理，每轴只查修复及受影响上下文。

业主 2026-11-18 再次要求界面简单、逻辑清晰，反复脚本与补丁不能替代底层修复。本批发布暂停。主线负责合并重复客户需求入口；独立后端修复线最多一份隔离工作树、独立 uv 环境、不建站点，统一需求编译与一致性校验，集成后由主线回收。路径由 Agent 返回后补记，保留至本轮集成完成。实际客户入口发现纯储能多系统的有效 PV=0 与原始空值被不同模块重复解释，返回无字段的 422；不计为客户路径通过。

## 2026-11-18 客户操作链重建（进行中）

业主否定当前配置器的整体可用性：客户仍需理解内部任务并反复保存多个版本，才能尝试得到方案。前面的布局、表单和接口修正不构成这次要求的重构；已有通过记录仅证明各自列出的行为。本候选暂停发布，完整目标仍为 #1132。

客户入口收集地点、建设／改造／纯储能范围、用能目标及已有资料；不知道的事实允许留空。进入同一方案页后，客户看推荐设备与数量、满足目标的依据、保留／新购范围，以及具体缺项。补资料、改目标、替换设备后更新同一方案；比较、报告、草稿和询盘消费选定的同一冻结方案。屋顶、曲线、接线与专业参数按需要展开，不成为所有客户必经步骤。

| 责任 | 客户提供 | 工具承担 | 缺项处理 |
| --- | --- | --- | --- |
| 项目 | 地点、项目范围、目标；已有设备及保留／替换意图 | 复用同一项目与位置，按目标问相关问题 | 保留未知；只询问影响当前结论的事实 |
| 需求 | 备电负载与时长，或实际用电资料、削峰目标；已有 PV 信息 | 将声明编译为有单位、时段和来源的计算输入 | 年耗不能伪造逐时负荷；不能从任意倍率推荐容量 |
| 方案 | 提交需求；按需确认设备偏好 | 持久执行所需计算与产品资格检查，选型、数量、附件、解释和来源 | 区分可推荐、资料不足、需求未满足和搜索未完成 |
| 修改与交付 | 修改事实／目标，选择方案，下载或询盘 | 更新受影响计算；报告、BOM 和交接绑定同一方案 | 旧方案保留历史身份，不冒充当前结果 |

实现责任：一次“生成／更新方案”提交当前输入；服务端负责内部计算顺序和结果衔接。保存版本、准备资产、采用曲线、启动设备检查不再是客户必须安排的步骤。现有 Workspace 原子输入操作、持久任务、冻结结果、Woo 证据和报告消费者作为基础复用；当前代码尚无完整的方案生成操作。不得以自动点击旧按钮或仅隐藏表单代替该责任。

第一条验收从首次使用者的“给店铺配备电储能”开始，直接填写实际负载／时长与所需事实，通过真实 Planner RPC 获得可解释的方案或准确缺项，并从同一方案下载报告、继续询盘；随后覆盖新建、已知 PV、改造、已选设备、纯光伏及大型多系统。已确认的客户组件、Planner RPC、报告与交接为测试 seam。

资源：主线复用当前工作树和 review 数据；原型只读预览恢复到业主指定的 `127.0.0.1:8765`，根目录为当前树的 `docs/prototypes/2026-11-17-system-configurator`，最多一个进程，主线实看后停止，原型文件保留；独立后端责任核对最多一份只读隔离工作树，不安装依赖、不启动实例，只核对方案提交可复用的持久执行路径及缺口，主线采纳后回收。代码与产品文案在当前任务文件内迭代，不新增中间报告。后端实现由独立代理负责，一份隔离树和独立 uv 环境，无站点；主线负责整合后回收。主线新增 `apps/planner/src/components/energy/ProjectEnergyDemand.tsx` 作为正式用能入口，复用当前项目草稿与设备搜索，长期保留为产品源码。视觉实现线最多一份隔离树，不装依赖、不启实例，限改 planner.css，直接参照原型页面的浅色背景、内容卡片、导航和双栏比例；主线整合实看后回收。

2026-11-18 业主追加裁定：废弃旧配置器全部界面、页面划分和操作顺序，只复用或修改功能实现与接口。正式前端以已批准 `system-configurator.prototype.html` 的五个页面重新实现于 `apps/planner/src/components/configurator/`，不包装旧 Workspace。主线负责入口、项目和交付；复用 `agent-a1b59c0e7567ab235` 做新作用域样式、`agent-abcb48342a95df782` 做系统选择、`agent-a4edf90861e1fa0c6` 做用能输入、`agent-ac5bb4958d2719b9c` 验证冻结候选到报告，均沿用现有隔离树及预算，不新增实例；源码与对应行为测试长期保留，主线整合后回收子树。当前磁盘已用 2,626,406,476 KiB，可用 1,240,807,044 KiB。

### 本地评审读回（2026-11-18）

Rotterdam 的 Project 选定自用后，Energy use 直接显示同一用途。在 EN／正式 DE 的 1440 和 390 宽度实看该页。桌面滚动时右侧项目名停在固定页头下方 16 px；手机上的步骤按完整名称换行，`Photovoltaik`、`Strombedarf` 和 `Prüfen und weitergeben` 均可完整阅读。并网类型为空时，比较按钮旁显示选择单相或三相的提示，两种语言的下拉箭头均可见。

多系统原生报告夹具覆盖 7 kW × 6 h。报告列出损耗前负荷需求 42 kWh、备电功率上限 8 kW，共享转供和起始可用电量仍需核实。前端采用方案后，未单独填写的子系统放电功率保持为空。

Leipzig 访客询盘 8803 已收到。Woo 保存 H2-25K-T3 × 1、BU2-5.0-HV1 × 5、BC2-HV1 × 1。德语确认页显示输入版本 3，附带的原英文报告返回 HTTP 200、114705 字节。另在报告页上传 Linker Logo 后生成德语版。390 宽度下清单按设备显示数量、型号、货号和供货范围，1440 宽度使用四列表格。Rotterdam 评审项目已从航拍地图用指针绘制四角示例屋面，撤销后屋面列表恢复为空，关闭航拍后显示项目几何底图。

另一位首次访客在改造项目中选择保留既有逆变器。评审询盘 8804 已收到，Woo 记录为访客、零件商品，询盘附带该项目报告，确认页的下载返回 PDF。

Rotterdam 项目的 9 × 6 m 示例屋面已在英语和正式德语的 1440、390 宽度实看。初版斜视的浅灰屋面与背景难以区分，加深屋面后两种宽度都能辨认轮廓。切回平面仍为原四个顶点，切换语言仍打开同一项目。另在该项目预选 SAJ B2-5.0-HV1 后切换纯光伏，取消时电池和光储范围保留，确认时范围改为 Solar 并移除电池字段。

主线负责本次 review 引擎切换。`/Users/chesterjohn/de-linker-local/review/planner/runtime-releases/f753aae40c4491641aeaea29af535270045b026806ec8881dfba36d696c3f861` 保留一份切换前的可执行版本，同目录上级的 `workspace.before-retained.sqlite` 保留一份当时的数据库，至新版本访客报告交接与既有项目读回完成后回收。复用 review 及原隔离树，生命周期、引擎和零商品询盘各由原负责人推进。

## 本轮裁定与实现

业主要求从根因修复准备／保存／计算的责任分裂，并明确授权参照本地 Preline productivity 模板大改工具界面。项目列表、项目标题与操作区、桌面章节侧栏和手机章节选择器重新组织；保留现有 React/Vite 与 WindPress。

计算、设备搜索、手选设备检查直接接收当前编辑输入。服务端生成执行输入，并将项目版本、任务和回执原子提交。结果、比较与报告读取该次运行的固定依据。普通未保存输入可直接提交；冲突和未确认请求仍有明确恢复路径。

未知容量保留为空；零容量下限不决定有无储能。项目用途决定拓扑，保留／替换意图决定采购范围。纯光伏多系统保存真实逆变器和电气依据，执行时储能单元为空；不创建虚构电池。切换到纯光伏后，旧的储能连接选项不会改变实际 AC 光伏数据的含义，也不会删掉其选择。

## 已核验的真实客户路径

评审实例 `http://127.0.0.1:8889` 使用现有线上主题、上传文件和 2026-11-16 快照。

- Oslo 本地项目：更改用途筛选后直接查找设备，版本 6→7；未先保存，返回 644 个已评估组合。采用实际组合后，保留项目已有的手工能量情景。
- 更改情景来源说明和 1.2 kW 进口上限后直接计算，版本 7→8。完成结果可展开原始负载与模型来源；不再读取已删除的浏览器执行投影。
- 切换 DE 后生成版本 8 的报告；PDF 与 CSV 实际下载，PDF 前两页实看。SAJ H2-25K-T3、BC2-HV1、B2-15.0-HV1 各 1 件；系统内部 3 个电池模块没有变成 3 套采购。
- 正常点击确认后，三个产品进入同一 Lösungsentwurf，均显示规划项目与输入版本。访客短表单提交得到本地询盘 8786。确认页保留规划报告；其下载字节与原报告相同。
- 询盘邮件走本地隔离捕获；未向生产发信。测试邮箱使用保留域名 `example.test`。

## 行为验证与评审

- 合并后的后端组合检查：304 项通过，覆盖原子回滚、历史读取、三种当前输入操作的访客认领回执、设备搜索／检查、实际接线报告和 AC/DC 计算。
- 内部呈现改版集成后：273 项域／数据检查和 388 项组件检查通过（共 661 项），TypeScript、Prettier、Vite 构建与两层 build:check 通过；纯光伏隐藏连接状态的增量补测通过。另用原生两逆变器、零储能结果验证公开解码器、参数说明、来源读取和结果展示，避免把所有硬件单元误当储能单元。
- EN/DE 项目入口、语言切换、并发保存和登录认领用例通过；两条完整报告链已通过正常界面操作走完生成 PV → 选用该数据 → 能量计算／失败重试 → 设备检查 → PDF／CSV → 草稿 → 询盘和项目备注保护。测试中的 PV 与负载统一为 2026 时间轴，未放宽不同发电来源的拒绝规则。
- PHP 网关：11 项测试、107 个断言通过；PHPStan 通过。前端构建与两个产物清单检查通过。
- Standards 评审发现并修复：旧编辑器的迟到回执覆盖新草稿；登录后不能继承新操作的访客回执。真实存储／重新打开测试与原生认领测试分别复现并验证。
- Spec 评审发现并修复：手选设备的接线检查入口丢失；多系统纯光伏要求电池；缺失字段错误未关联控件；德语导航／语法错误；纯光伏继承不可见的 DC 模式并丢失 AC 数据。最后一项的窄复审已确认解决。

## 文案：初稿 → 对抗审阅 → 定稿

| 命中初稿 | 审阅发现 | 定稿 |
| --- | --- | --- |
| 选运行目标时自动填零，并写“User-declared … explicitly set to zero” | 用户没有声明这些损耗、初始电量和限制 | 目标选择只改变相关运行方式；未知物理值保持为空，沿用可编辑的来源、初始状态与运行期表单 |
| 德语提示 “unter Energieverbrauch” | 实际导航为 Strombedarf | “unter Strombedarf” |
| “Gewerblicher Speicher auslegen” | 格不正确 | “Gewerbespeicher auslegen” |
| “Save the project, then check the equipment selection” | 新设备检查直接接收当前输入，旧提示错误要求先保存 | “Check equipment to assess this wiring plan.”；德语使用实际按钮名 „Geräte prüfen“ |
| 多系统报告默认描述独立储能单元 | 纯光伏没有储能单元 | EN: “This calculation uses available AC PV generation and load at the common metering point. The declared scenario contains no battery storage.” DE: “Die Berechnung verwendet die verfügbare AC-PV-Erzeugung und die Last am gemeinsamen Messpunkt. Das angegebene Szenario enthält keinen Batteriespeicher.” |
| 日期缺项初稿仅说明日期、时间和时区 | 对相同／倒置的起止时刻没有可执行指导 | EN: “Enter a date and time with Z or a UTC offset. The end must be after the start.” DE: “Geben Sie Datum und Uhrzeit mit Z oder einem UTC-Zeitversatz an. Das Ende muss nach dem Beginn liegen.” |

字段错误使用实际字段名称和更正动作；不向客户显示内部路径。新文案维持 EN／正式 DE，译文编译及覆盖检查通过。

## 资源与交付阶段

主线复用 `system-configurator-prototype` 工作树与 review 实例。各实现线只使用自己的工作树；未增加站点实例。模板预览的 8897 静态服务已停止。

浏览器任务空间 14 曾返回 “This task space is no longer assigned to the agent”，当时停止操作。业主随后明确选择恢复空间 14，现已重新认领原页，继续 EN/DE、1440/390 验收。Utrecht 的未保存草稿保留。

2026-11-17 业主再次指出前端大改尚未完整呈现。实看确认工作台外框已改，设备、计算和结果内部仍需统一组织。本轮继续该既定范围：设备检索与手选分区、计算设置与依据分区、结果与报告组织；复用当前输入命令和草稿状态，不另建选择状态或构建管线。

资源预算：主线沿用现有工作树和 review；独立设备与能量呈现线各最多一个隔离工作树，无新增站点，源码集成和有效验证后由主线回收；各线不安装依赖，集成检查使用主线已有依赖。呈现增量的 Spec／Standards 各使用一个只读隔离工作树，评审结束即回收，不安装依赖；复用 `/tmp/linker-configurator-review-final.patch` 保存当前增量供两轴读取，主线负责回收。截图复用 `/tmp/linker-project-new-en.png`、`/tmp/linker-demand-current.png` 等已登记路径逐屏查看，最终选择证据归档后回收。

本地升级恢复点 `/tmp/linker-review-command-upgrade.sqlite` 只保留一份，按当前 review 数据滚动更新，数据库检查后才替换；本轮验收完成后删除。评审补丁只保留初次与最终候选两份，供隔离评审读取，结束后删除。临时截图、PDF 和 CSV 用于本轮实看与消费者核对，最终证据归档后回收其余副本。

2026-11-17 内部呈现增量已在 review 发布并编译 WindPress。设备需求／手选、单系统／多系统、计算设置、保存结果、比较和报告采用统一面板。EN／DE 的设备、情景、比较和报告在 1440／390 实看；手机正常切换系统、展开手选、切换计算历史、切换报告选项及语言。比较使用 Oslo 的版本 4 与 8，条件不同时保留各自数值并说明不显示差值。多系统测试后通过 Undo 恢复 Oslo 保存版本 8，未触碰 Utrecht 草稿。

实看发现多系统需求 fieldset 的旧 reset 覆盖新面板间距；将 reset 限定到非面板 fieldset，保留 legend 语义并将窄侧栏字段排为单列，英德文复看确认。Spec 与 Standards 独立评审及该 fieldset 增量复审无发现。更新后的 EN／DE 完整报告链均通过（2 项，3 分钟），覆盖 PDF／CSV、草稿和隔离本地询盘；本次命令中的 `planner-projects.spec.ts` 未匹配文件，未将其计为已重跑的项目测试。

发布恢复资源：主线复用 `/Users/chesterjohn/de-linker-data/planner-production/` 的既有 Archives／Remote 增量备份接口，创建一次当前生产 Planner 数据库与 CAS 独立归档；沿用既有 owner、登记表和 N=3 轮换，禁止新增服务端整站备份。新 release 通过 `tools/planner/publish/cli.sh` 创建，保留 current 与 previous；站点发布自动流式保存数据库快照并保留上一批代码。主线负责发布后读回和回收。

纯光伏和多系统计算设置的 EN／DE、1440／390 呈现实看完成；手机切换系统、初始状态和运行设置可操作。验收后 Oslo 恢复为 Saved · revision 8。生产 Planner 恢复点为 `/Users/chesterjohn/de-linker-data/planner-production/archive-20261117T124728Z-f1b360b4`，原生校验通过，轮换后保留 3 份；该操作前后可用空间为 1,267,013,607,424／1,266,483,744,768 字节。

候选 `121f0589e` 的首次 CI 在 `workspace-lifecycle.test.mjs` 首次加载编辑器时未在夹具的 2 秒期限内出现 textarea，其余 387 项组件检查通过。相同候选本地单文件 23 项及完整组件集 388 项通过；仅重跑失败 CI 作业一次后，run 44085565970 attempt 2 全绿，headSha 确认为 `121f0589ef11a98e97e9168c697f8e98271665ac`。测试超时与产品代码均未为此次重跑修改。临时日志 `/tmp/linker-planner-current-tests.log`、`/tmp/linker-ci-rerun.log` 各保留一份，由主线在 CI 原因与结果登记后回收。

资源回收：`agent-a59bc662892acd775`、`agent-a7a87623acf00ba39` 的源码格式化后与已提交版本相同，`agent-a98f3423e89850493` 的三份测试与已提交版本字节相同；确认没有进程占用及额外文件后删除这三份工作树。删除前后可用空间为 1,264,356,139,008／1,274,564,382,720 字节，实际增加 10,208,243,712 字节。其余四份实现树核对后确认差异均为已整合的界面改版、当前输入命令及后续缺陷修正；无活跃进程，现已删除，实际可用空间再增加 13,615,927,296 字节。七份工作树合计释放 23,824,171,008 字节。review 的 PHP、Planner worker、Engine 与 Genie 已通过 `just down review` 停止，保留实例数据以保护 Utrecht 草稿。两份评审补丁、本地升级恢复副本和组件测试临时日志共 4 份已回收，实际可用空间增加 2,138,112 字节。

生产读回预算：主线沿用浏览器空间 14 和 Amsterdam 保存项目，仅只读核对该项目。当前输入操作如需生产写入，最多创建 1 个明确标为 `Goal 1132 release acceptance` 的临时项目，只用于新网关／worker／结果和报告读回；不提交询盘、不发信，完成后通过项目删除入口回收。发布日志复用本机会话任务输出；最终发布批次与实际结果补入本记录。保留四份最终评审证据至 `docs/acceptance/2026-11-17/demand-to-system/`：多系统桌面、手机运行设置截图和德语报告 PDF／CSV，各一份，供本记录引用；归档后删除对应临时原件。

最终证据：[多系统桌面](demand-to-system/multi-system-en-1440.png) · [手机运行设置](demand-to-system/operation-en-390.png) · [德语报告 PDF](demand-to-system/planning-report-de.pdf) · [物料 CSV](demand-to-system/bill-of-materials-de.csv)。四份均核对归档字节，临时原件已删除。

最终提交 `c3a18f7be` 的 CI run 44088194030 全绿；PR 1134 于 2026-11-17 13:11 UTC 合并为 `21d9375d5a199082c7586e91913be28074d9cd89`。Planner 成对发布完成：release `/opt/linker-planner/releases/964ca6cb5c31270c7bd62fa482adf1c16fc9aeef59874853d73ccd7570e69645`，runtime `3164f7458367d8cbe17cde27aeaa25a99c5bd46e08a079aeb8de640d9766a16b`。HTTP PID 48644、worker PID 48892 均 active，原生 status 证实监听 8911、运行时与 worker 身份一致、draining=false、pending=0。切换中的一次提前 status 读取发生在监听启动前；13:14:50 HTTP 启动、13:14:53 worker ready 后读回通过。保留 current／previous 两个 release。站点原子发布批次 `20261117T131550502102Z-21d9375d5` 已启动；数据库恢复快照 `/Users/chesterjohn/de-linker-data/snapshots/db-20261117T131558Z.sql.gz`，8,154,047 字节，原生快照校验通过。

站点批次 `20261117T131550502102Z-21d9375d5` 已在原批续完：WindPress 编译更新实际 CSS，verify 与 archive 成功，任务退出 0。生产临时项目当前输入直接提交为版本 2；第一次运行因日期为空失败（job `invalid_input`）。采用共同时间范围请求期间继续修改其他运行字段，触发 `scenario_changed`，日期没有写入；界面未在提交时指出日期缺项。等待范围选用完成后，直接计算生成版本 3，运行 `9c1cb9faf8a24e858a9d16e2b6de383a` 成功：35,040 区间、负载与购电 4,990.56 kWh、光伏及未供电量均为零，符合明确声明的纯储能空初始电量测试情景。

新增缺陷工作预算：一名后端代理复用其隔离 worktree，已定位空日期仅在 worker 解析；在共享 authored schedule 编译处修复并补 HTTP 拒绝／回滚测试。依赖独立 uv 安装、不建实例，主线整合后回收该树。前端修复线另占一份隔离 worktree，负责共同时间范围异步更新与提交校验，依赖独立安装；主线负责集成、评审和回收。主线继续生产报告及界面读回。继续复用主线、review 数据和临时生产项目，不新增生产测试项目。完整目标保持开放，尚需报告读回、失败恢复修复和临时资源回收。生产 PDF 下载限一份，保存到新目录 `/tmp/linker-production-report-1132/`，主线实看后回收；生产截图复用已登记 `/tmp/linker-demand-current.png`，每次查看后覆盖，不累积副本。

生产后续读回：版本 3 报告 `6efdd3323b5747ca95617db555cc3814` 已生成并下载，两页 PDF 实看，包含原始运行引用、4,990.565 kWh 负载／购电和明确的合成情景来源。EN／DE、1440／390 的新情景与报告布局已刷新实看；DE 页面明确标注既有英文报告语言。当前输入设备搜索直接保存版本 4，评估 644 组；采用 SAJ H2-25K-T3 + BU2-5.0-HV1、3 模块、1 并联组及 BC2-HV1 后直接检查，保存版本 5，显示 Equipment check complete 与逐项证据。未提交生产询盘或发信。Amsterdam 只读重开仍为 Saved · revision 3；真实荷兰航拍、已存屋面与 8 块／3.6 kWp 组件均实际显示。

后端原只读代理工作树由工具在完成时自动回收，后续修复使用 `/Users/chesterjohn/Documents/de-linker/.claude/worktrees/engine-schedule-admission`（独立 .venv）；前端为 `/Users/chesterjohn/Documents/de-linker/.claude/worktrees/agent-ad08ef02046093a37`。后端增量已整合，主线逐文件字节核对并通过 16 项 HTTP／plant 针对性测试、Ruff 与类型检查。该隔离树无进程引用，只有已整合文件和可重建缓存，现已回收，实际释放 3,477,172,224 字节。前端树集成后同样由主线回收。生产 PDF 实看后删除，实际释放 126,976 字节。review 已重启 PHP、Engine 与 Planner worker，供失败恢复增量验收；Genie 未启动。真实 Oslo 界面清空开始日期后提交被拒绝，Undo 恢复 Saved · revision 8；缺少日期字段提示的前端增量仍待集成。联调发现前端只接收 `schedule[0]` 索引路径，主线修正后端原点号索引输出，16 项边界测试再次通过。

增量评审预算：Spec 与 Standards 各一份只读隔离工作树、不安装依赖、不创建站点；主线提交完整候选后并行评审，收到结果即由工具回收。复用 `/tmp/linker-demand-pr.md` 作为本次后续 PR 正文，发布后删除。发布前沿用既有 Archives/Remote 再取一次当前生产增量恢复点，仍按同源 N=3 轮换；不建立新的备份根目录。恢复点 `/Users/chesterjohn/de-linker-data/planner-production/archive-20261117T134931Z-f1b360b4` 已校验，保留 3 份；操作前后可用空间 1,284,099,723,264／1,284,012,273,664 字节。

日期恢复增量集成后，前端 273 项域／数据测试与 399 项组件测试通过（672 项），TypeScript、Prettier、Vite 及两层产物校验通过。翻译覆盖无缺口、9 份目录校验通过；Planner PHP 入口 3 项／37 断言通过。后端针对性 16 项通过；原独立后端完整受影响集为 182 项通过。候选 `cbebe6d0d` 的 Spec 与 Standards 独立评审均无发现，PR 为 [1135](https://github.com/AssassinFlash/de-linker/pull/1135)。评审站日期错误已在 EN／DE、1440／390 实看：开始日期缺项时聚焦实际字段并显示更正指导；英文桌面可在错误存在时切换报告再返回，德语修改日期后字段错误清除。验收结束用 Undo 恢复 Oslo 保存版本 8。截图等待实际滚动完成后查看，沿用临时工作图，不增加重复归档。最终提交 `ae3c8fbb9` 的 CI run `44099816089` 全绿；首轮 `cbebe6d0d` 在生命周期夹具首次加载编辑器时超过两秒等待，本地对应文件通过，最终提交 CI 通过，未修改超时。PR 1135 于 14:21:11 UTC 合并为 `4bc3d3b82ad321f16f34f7a1e7e2d56ebebc7571`。

前端隔离树 `agent-ad08ef02046093a37` 的 8 份改动与集成候选逐字节相同，未跟踪文件为空、忽略文件仅可重建 node_modules，无进程占用；已回收，实际可用空间增加 3,823,177,728 字节（1,284,015,484,928 → 1,287,838,662,656）。两份只读评审树已由工具自动回收。review 的 PHP、Planner worker 和 Engine 已停止，保留实例数据及 Utrecht 草稿。13:49 已验证恢复归档包含生产临时项目版本 5，与此次发布前项目状态一致；沿用该恢复点。

增量生产发布完成：Planner release `/opt/linker-planner/releases/c307fb2e74287aa72d3d2aa6049be9979652549ad30a60af8a6c768c775cad35`，runtime `c325bcfb1db5d5778972cee85598e2f2105cc109f3d428fbec34d6a19f7a3aaf`；HTTP PID 51959、worker PID 52063，原生 status 读回身份一致、draining=false、pending=0，保留 current／previous 两版。站点批次 `20261117T142546527553Z-4bc3d3b82` 的 verify／archive 成功，发布恢复记录已清除；数据库快照 `db-20261117T142613Z.sql.gz` 为 8,191,395 字节，快照仍保留 3 份。实际服务的 planner.js（1,370 字节）、ProjectEditor-CvCTPtTi.js（995,252 字节）、planner-core-BO9Dzslw.js（491,698 字节）与合并候选逐字节相同。

生产临时项目清空开始日期后，实际计算入口返回 HTTP 422，字段得到焦点及可读更正提示；Undo 后仍为保存版本 5。重新采用共同时间范围并直接计算，新运行 `5dc79351be424c5eaae0ca5ac4474f5f` 完成，输入版本 5、购电量 4,990.56 kWh。该项目 `40242003c8864b88bc21bb357ff993e9` 随后通过 Projects 的删除确认入口移除，列表只余受保护的 Amsterdam 项目。无生产询盘或发信。

收尾：浏览器空间 14 已关闭；临时截图与 PR 正文已删除，实际释放 110,592 字节。末次磁盘已用 2,707,456,335,872 字节，可用 1,288,872,992,768 字节。主工作树约 6.33 GB 保留源码及当前交付记录；review 数据保留 Utrecht 草稿，服务已停；Planner 三份独立恢复归档与明确基线、站点三份数据库快照及服务 current／previous 按既有保留规则继续保存。

## 2026-11-18 · Rotterdam 报告与历史下载

评审站的 Rotterdam solar workshop 在两项合成图纸的导出许可为未知时拒绝生成含屋面清单的新报告。在 Solar 的 Source properties 明确登记两项许可后，提交比较并采用同一逆变器。输入修订 5 的客户预览、PDF 和 CSV 均列出 Trina Solar TSM-460NEG9R.28 × 2，归属项目报价。PDF 的组件表列出每块 460 W、总计 0.92 kWp。系统页的三项均显示已检查条件满足，25 kW 逆变器在同等状态下按商品顺序列在首位。

从 Calculation history 实际下载修订 3 的 PDF 与 CSV。旧 PDF 标记输入修订 3，CSV 包含当时的逆变器与配套电表。保持历史版本展开，执行当前方案的 Add selected products、Confirm changes、View solution draft。Woo 草稿显示 Rotterdam solar workshop · input revision 5、SAJ H2-25K-T3 × 1，并能进入访客询盘。关闭项目页面后，经正式德语入口重开同一项目，仍能读取修订 5 的报告及其语言，390 px 可操作两项合成图纸的导出许可。

## 2026-11-18 · 生产发布与客户验收

PR [1139](https://github.com/AssassinFlash/de-linker/pull/1139) 的 [CI](https://github.com/AssassinFlash/de-linker/actions/runs/44224151926) 通过，合并提交 `0c5a9909a` 与候选 `cb4330bd6` 的树相同。Planner 恢复点为 `~/de-linker-data/planner-production/archive-20261118T025419Z-f1b360b4`，轮换后保留三份。HTTP 与 worker 已切换到 `fc0b7473562f362336d8fc06cb42f04866b1b5ed3d63f4f520d64c81b3b1ec50`。原生 status 返回 ready、draining=false、pending=0，HTTP 监听 8911。站点批次 `20261118T030056975036Z-0c5a9909a` 的数据库快照 `db-20261118T030103Z.sql.gz` 为 8,188,967 字节。首次 present 因生产 CSS 仍旧而停止。WindPress 重编后同批 resume 的 verify 与 archive 通过，发布记录已清除。公网实际提供的 planner.js、Configurator 和 planner-core 与合并提交逐字节一致。

临时访客项目 `Goal 1132 release acceptance`（`acd2ca3897f543d1be9d1c93cb73e23f`）以 Rotterdam、10 kWp、三相输入直接比较，保存修订 2。采用 SAJ HS2-10K-T2-X 后生成修订 3 报告，实际下载的 PDF、Woo 草稿和询盘表单均列出逆变器与 Chint DTSU666 各一件。客户可从正式德语入口重开，手机显示冻结报告的语言为英语。Amsterdam 只读打开时仍为修订 3。未提交生产询盘或发信。批准的生产测试账户 53 现有规划询盘报告与已保存方案报告数均为零，登录后下载冻结报告仍缺该账户的测试文件。

访客通过商品行 Remove 清空测试草稿，表单显示可无产品留言。此后临时项目删除入口仍提示已交接询盘并拒绝删除。正常比较请求在等待回执时短暂要求客户确认上一请求；刚重开已选方案时，System 在历史结果加载完成前提示先填需求。两项按本次操作复现处理。主线保留上述唯一生产临时项目供修复读回。两条修复线各使用一份隔离工作树（`agent-a5865b673a3c2a637` 和 `agent-a27c1cf90d7b85960`），各自独立依赖，整合后由主线回收。

## 2026-11-18 · 询盘恢复提示与评审站复验（#1140）

初稿将项目状态写作 `was deleted` / `wurde gelöscht`。评审确认，项目删除和访客失去原项目访问权会得到同一结果。商品分支定稿说明该项目已无法访问，要求移除该项目商品后重新发送。EN 使用 `Remove its products from your solution draft`，DE 使用 `Entfernen Sie die zugehörigen Produkte aus Ihrem Lösungsentwurf`，对应商品行 Remove / Entfernen。

仅报告分支的初稿 `Deselect the planning report` / `Wählen Sie den Planungsbericht ab` 暗示可逐份取消。表单只有一个复选框，定稿在消息中引用其完整标签 `Include planning reports and project notes with this inquiry` / `Planungsberichte und Projektnotizen mit dieser Anfrage senden`，然后请客户重发询盘。

评审站两种语言的访客询盘页和德语无产品留言回执均通过。历史完整快照能在所属账户 Documents 中列出，原订单链接可下载冻结 PDF。其他账户和遭修改的快照均无法下载。生产验收仍沿用原 Rotterdam 项目。
