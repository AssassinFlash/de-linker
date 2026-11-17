# 配置器：当前输入操作与工作台重排

目标：[全欧洲系统方案配置器正式落地并接入 Linker 客户链路](https://github.com/AssassinFlash/de-linker/issues/1132)。基线 `a92cda3a8`；候选分支 `codex/demand-to-system`。本记录随候选验收更新，不代表已发布。

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

资源回收：`agent-a59bc662892acd775`、`agent-a7a87623acf00ba39` 的源码格式化后与已提交版本相同，`agent-a98f3423e89850493` 的三份测试与已提交版本字节相同；确认没有进程占用及额外文件后删除这三份工作树。删除前后可用空间为 1,264,356,139,008／1,274,564,382,720 字节，实际增加 10,208,243,712 字节。其余四份实现树仍在核对整合差异。

当前仍待：验收记录提交后的最终 CI；合并、成对 Planner 与站点发布、生产入口读回；剩余资源回收。[PR 1134](https://github.com/AssassinFlash/de-linker/pull/1134) 保持草稿，完整目标保持开放。
