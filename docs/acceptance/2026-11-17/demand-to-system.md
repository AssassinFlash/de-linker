# 配置器：当前输入操作与工作台重排

目标：[全欧洲系统方案配置器正式落地并接入 Linker 客户链路](https://github.com/AssassinFlash/de-linker/issues/1132)。基线 `a92cda3a8`；主候选经 PR 1134 合并并发布为 `21d9375d5`。生产验收发现的日期失败恢复增量经 PR 1135 合并并发布为 `4bc3d3b82`，生产更正计算与临时项目回收完成。

## 模板改版重新执行（业主校正）

业主再次指出现有界面未达到指定 Preline productivity 模板的改版要求。此前侧栏、面板与表单整理不能作为该设计目标完成的证据。新分支 `codex/planner-preline-workspace` 继续这一目标，先实看模板与现状再按页面结构实现。

资源由主线负责：复用现有工作树与 review 数据；模板预览 `127.0.0.1:8897` 只读服务指定模板根目录，最多一个进程，实看后停止；一个浏览器任务空间内复用两页用于模板／产品对照；工作截图 `/tmp/linker-template-current.png` 与 `/tmp/linker-product-current.png` 各一份，最终对照归档后删除。独立实现线各最多一个隔离树，无独立站点，明确文件归属后启动；整合验证后回收。当前磁盘可用约 1.29 TB。

实际参照 `productivity/project-management/project-details.html` 与 `setup.html`：项目标题和横向章节导航进入深色 masthead，目录与编辑内容居中；概览先列真实项目属性，下接屋顶预览与继续操作列表；能量设置由重复的简版／Advanced 编辑器改为单一章节编辑器；报告下载与正文分栏，比较结果与计算依据分栏。颜色使用现有 Linker teal900 与中性色 tokens。模板里的演示预算、进度、任务状态未引入。

集成首轮验证发现未知储能规模的新项目默认展示参数章，遮住原有运行目标到设备选择入口；已改为默认打开 Operation，仅初始化一次，后续章节选择保留。报告下载相关五项旧测试绑定了已移走的标题区按钮；改为按可见按钮文字查找后通过，下载、取消与旧报告标记断言保留。设备采用和德语百分比测试明确打开 Storage 后原业务断言通过，设备生命周期 15 项、PV 设置 5 项集成通过。全套域／数据 273 项通过；组件首轮通过结果与受影响文件补测共同覆盖最终逻辑，后续 CSS 调整不改变这些输入输出。

主线已实看 EN 桌面／手机概览、桌面设置与比较、EN 手机报告、DE 桌面报告与手机 Operation。DE 390 宽空日期提交后，Operation 自动展开并定位可见日期框，显示完整修正提示；Undo 恢复 Oslo 保存版本 8。报告历史改为可横向滚动的选择条，避免历史／正文／操作三列挤压。完整页型验收、双轴评审和发布仍待完成。

最终 Spec／Standards 各一份只读隔离工作树，不装依赖、不建站点；主线负责评审结束后回收。最终模板／产品对照证据最多四张，存入本任务目录 `preline-*.png`，其余工作截图覆盖复用后删除。

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
