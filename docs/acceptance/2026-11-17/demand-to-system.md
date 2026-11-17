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
- 前端完整检查：261 项域／数据检查和 380 项组件检查通过；纯光伏隐藏连接状态的增量补测通过。另用原生两逆变器、零储能结果验证公开解码器、参数说明、来源读取和结果展示，避免把所有硬件单元误当储能单元。
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

浏览器任务空间 14 随后返回 “This task space is no longer assigned to the agent”。主线停止该空间的操作；未自行接管或换浏览器继续交互。剩余实看与生产交互读回须获得该空间恢复授权。独立的本地测试与代码检查继续。

本地升级恢复点 `/tmp/linker-review-command-upgrade.sqlite` 只保留一份，按当前 review 数据滚动更新，数据库检查后才替换；本轮验收完成后删除。评审补丁只保留初次与最终候选两份，供隔离评审读取，结束后删除。临时截图、PDF 和 CSV 用于本轮实看与消费者核对，最终证据归档后回收其余副本。

当前仍待：受影响页面 EN/DE、1440/390 实看收敛；最新候选 CI；合并、成对 Planner 与站点发布、生产入口读回；本轮资源回收。[PR 1134](https://github.com/AssassinFlash/de-linker/pull/1134) 保持草稿，完整目标保持开放。
