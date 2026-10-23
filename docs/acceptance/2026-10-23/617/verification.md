# 系统选型发布依赖：执行检查

对应[系统选型实现](https://github.com/AssassinFlash/de-linker/issues/617)。分支 `codex/617-publication-engine`；源基线 `177e560a`，已合并历史/整套动作与 Woo 发布合同的接口，以及 `7ab7946f` 的正式德语 PO/MO/JSON。它们是其他执行者的实现，最终地图集成应包含各自后续修复。

## 已执行

- `services/engine`: 最终完整 pytest 175 通过，真实 106 产品工程/PVGIS/LoD2 夹具；Ruff lint/format 通过，mypy 全目录 55 个文件（包括测试）通过。准备与发布专项 25 通过。
- 新发布专项含：异步未运行前排除草稿 EcoFlow、在途任一候选撤权、资料新修订、未准备新品、空集、权威不可读、明确旧电池/逆变器、私有可信结果验证、PDF 精确匹配。
- enforce 真实工程路径先计算，之后把计算函数替换为“调用即失败”，连续两次确认验证和 PDF 均保持相同选型、成功且没有重算。
- 自动 sync 用本地 HTTP 与引擎真实 schema loader 验证整代发布、空 products、任一部分错误保留旧数据、旧进程读回失败整代回滚、最多两代与作业确认。
- linker-tools 五个前端测试文件 71 用例通过（engine transport/App/store/solutions/protection），变更的 11 个前端源/测试文件 ESLint 与 Prettier 通过。新增状态使用正式德语 JSON 验证，覆盖当前权威不可读、需重算、整套加入未确认及卡片短标签；PDF 请求携带屏幕指纹。新的发布/选型失效 409 与来源故障 503 分开，其他 nonce/operation 409 不冒充产品变化。最后一次全项目 `tsc --noEmit` 发现 Genie 的共享 `AddStatus.stale` 消费者尚未更新，交给同轮 Genie 执行者；聚合分支必须重新通过全量类型检查，本记录不将单项测试通过替代该门。
- linker-tools PHP 11 个针对性单元测试、54 断言通过；六个变更 PHP 运行类与变更 Unit/Integration 夹具的 PHPStan level 8 通过；变更 PHP 运行类和针对性单元/集成测试 WPCS 检查通过。当前 Woo 无法刷新请求内缓存时明确返回 503；私有 NativeEngine、已确认结果验证及 PDF 渲染前后均保留 409/503 区分。
- `Resources` 的 `solution_save` / `draft_write` 新成功和旧成功回执都要求当前发布证明。`ResourceAdmissionTest` 已增加当前成功回执在产品下架后拒绝，以及没有证明的旧回执不能再成功的两个真实 WP 用例；既有合成工程传输夹具明确携带空依赖合同，避免仅因返回同一个错误而误报去重通过。这组真实 WP 用例等待聚合实例运行，尚不计为通过。
- 按锁文件复用已存在的主仓 Python venv / PHP vendor，以及同轮历史任务的 node_modules；跨工作树 Python 运行设置 `PYTHONPATH=src`，PHP 临时 bootstrap 将本工作树 PSR-4 放在共享 vendor 之前。没有复制依赖、启动实例、新建整站备份、发信、改模型或写生产。临时 bootstrap 在本次检查结束时回收；本工作树的依赖软链待主会话接收实现后移除，共享原件由各拥有任务保留。

## 集成验收边界

以上不证明生产部署、最终全量 Spec/Standards 双评审、组合后真实 WordPress HTTP 路径或 EN/DE 390/1440 视觉验收已完成。由地图主会话在同轮集成环境执行；本票未将本地通过改称生产通过。

部署须带上 engine 的新原子 sync 与 timer/service 定义，既有 `/etc/linker-engine.env` 增加专用 Woo Application Password 环境变量（只保存在服务器秘密配置），配置站点相应 manifest/jobs URL，读回实际 loaded source/compatibility/prepared_products 并确认 ack。首次替换 regular feed/contract 时脚本保留旧数据对，恢复旧代码时配合旧数据；不得只切新软链后给旧进程贴新版本。

第一阶段 EcoFlow 的草稿与资料 410 保护未改动；这份执行记录没有声称已重建知识库或通过实际公开 HTTP 撤权验收。

## 与统一工作台的边界对齐

本轮后续裁定要求长期产品方向以统一工作台为准。只读核对 `/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548` 的固定提交 `bc714bc628f1555d2ddcbface216dabc7b9371d5`，依据该树的 `docs/specs/548-workbench-application.md`、`548-design-geometry.md`、`548-geographic-intake.md` 与 `548-roof-import-workflow.md`；没有修改、重置或重启该工作树或运行实例。

| 边界 | 已查明的 source 合同 | 本票处置 |
| --- | --- | --- |
| 项目修订与未知确认 | `planning/workspace.py` 的 revise 以 expected_revision + intent key 在同一事务保存修订和回执；`planning/commands.py` 校验同 key 的完整命令 hash。工作台合同要求未知响应复用原 key/字节，保护更新的本地编辑。 | 新工作台继续由既有项目/命令机制维护。617 只修旧 Save/Ask 的未知结果提示；不扩展旧保存机制，不将旧 24 小时 selection receipt 当成永久项目。 |
| 冻结计算 | `planning/workspace.py` evaluate 固定 project/revision/input hash/context；`planning/frozen_run.py` 验证 run 与已存来源资产；`runtime_snapshot.py` 固定实际代码/依赖。`Run.is_current` 当前只表达项目修订相同。 | 本票旧 `/selection/validate` 和 `/report/pdf` 的 receipt 封住既有入口的重算与草稿读取。新工作台复用自己的 run 身份及冻结结果，不建立第二份 selection-receipt 历史；不能把 is_current 当成当前 Woo 发布许可。 |
| 来源与资产 | `planning/assets.py` 在所有读写前核 owner，以内容 hash 与独立 metadata hash 保留不可变私有来源；导入、项目修订和计算是不同命令。几何/CSV/用户场景具有独立来源、许可及质量。 | 产品事实与公开厂商资料仍只在 Woo 维护；客户项目输入继续由工作台的 Assets/修订维护。公开托管资料的 DocumentAccess 不接管私有用户上传、私有报告或数据源。 |
| SKU 资格与交接 | `planning/energy_kernel.py` 的实际输出明确 equipment_release / country_assessment 为 not_assessed。`records.py` 与 `schema.py` 存在 Handoff 值记录/表结构，工作台合同 §13 要求同一 project/revision/run/candidate/evidence 交接；本次未查到已生效的交接命令/HTTP 路径。 | 不能把物理场景重放、表结构或旧配置器 receipt 称为已完成产品资格/交接。新消费者应在其既有 run / candidate / handoff 边界接共享 Woo 权威；本票不在旧 UI 增造长期交接架构。 |

共享 Woo 合同的可复用范围是 `Products\\Publication::manifest()`、`validate()`、生成工程 feed 与准备 jobs：canonical 产品身份、产品修订、资料身份/内容修订及产品关联、兼容修订、实际准备读回。当前许可每次新动作前后新读；完整候选及其证据都列入依赖，未准备新品不阻断其他已准备产品。过期产品/资料返回 409，当前权威不可核验返回 503；准备完成、历史 frozen hash 或客户端字段均不自行授予发布许可。

接入新工作台时，应在其产品资格/排名及新商务交接前后验证上述完整范围，并将验证过的 Woo 依赖与它自己的 project/revision/run/candidate/result hash 绑定。客户读取已拥有的历史修订/结果不触发重算，也不补读草稿产品；新计算、新报告或加入 Solution draft 则遵守当前许可。此段是对两个已核实合同的接口衔接结论，尚未声明新工作台已实现该消费者。
