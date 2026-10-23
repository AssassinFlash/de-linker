# 系统选型发布依赖：执行检查

对应[系统选型实现](https://github.com/AssassinFlash/de-linker/issues/617)。分支 `codex/617-publication-engine`；源基线 `177e560a`，已合并历史/整套动作与 Woo 发布合同的接口，以及 `7ab7946f` 的正式德语 PO/MO/JSON。它们是其他执行者的实现，最终地图集成应包含各自后续修复。

## 已执行

- `services/engine`: 工程/发布基线完整 pytest 175 通过，真实 106 产品工程/PVGIS/LoD2 夹具；后续独立 ops 修复专项 20 通过（含已有同步用例），没有把两组重叠数字相加。Ruff lint/format 全目录通过，mypy 全目录 56 个文件（包括测试）通过。
- 新发布专项含：异步未运行前排除草稿 EcoFlow、在途任一候选撤权、资料新修订、未准备新品、空集、权威不可读、明确旧电池/逆变器、私有可信结果验证、PDF 精确匹配。
- enforce 真实工程路径先计算，之后把计算函数替换为“调用即失败”，连续两次确认验证和 PDF 均保持相同选型、成功且没有重算。
- 自动 sync 用本地 HTTP 与引擎真实 schema loader 验证整代发布、空 products、任一部分错误保留旧数据、旧进程读回失败整代回滚、最多两代与作业确认。
- linker-tools 五个前端测试文件最终 80 用例通过（engine transport/App/store/solutions/protection），变更的 11 个前端源/测试文件 ESLint 与 Prettier 通过。新增状态使用正式德语 JSON 验证，覆盖当前权威不可读、需重算、整套加入未确认及卡片短标签；PDF 请求携带屏幕指纹。新的发布/选型失效 409 与来源故障 503 分开，其他 nonce/operation 409 不冒充产品变化。合入 `7f474b4c` 后新增 EN/DE × Save/Ask 四条未知保存回执断言：不宣称未保存、不自动重发、不打开未经确认的 Genie 记录、不清空输入或结果；PDF 生成失败尚未发保存 POST 的既有明确失败用例仍通过。最后一次全项目 `tsc --noEmit` 仅报 Genie 的共享 `AddStatus.stale` 消费者尚未更新，交给同轮 Genie 执行者；聚合分支必须重新通过全量类型检查，本记录不将单项测试通过替代该门。
- linker-tools PHP 11 个针对性单元测试、54 断言通过；六个变更 PHP 运行类与变更 Unit/Integration 夹具的 PHPStan level 8 通过；变更 PHP 运行类和针对性单元/集成测试 WPCS 检查通过。当前 Woo 无法刷新请求内缓存时明确返回 503；私有 NativeEngine、已确认结果验证及 PDF 渲染前后均保留 409/503 区分。
- `Resources` 的 `solution_save` / `draft_write` 新成功和旧成功回执都要求当前发布证明。`ResourceAdmissionTest` 已增加当前成功回执在产品下架后拒绝，以及没有证明的旧回执不能再成功的两个真实 WP 用例；既有合成工程传输夹具明确携带空依赖合同，避免仅因返回同一个错误而误报去重通过。这组真实 WP 用例等待聚合实例运行，尚不计为通过。
- 按锁文件复用已存在的主仓 Python venv / PHP vendor，以及同轮历史任务的 node_modules；跨工作树 Python 运行设置 `PYTHONPATH=src`，PHP 临时 bootstrap 将本工作树 PSR-4 放在共享 vendor 之前。没有复制依赖、启动实例、新建整站备份、发信、改模型或写生产。临时 bootstrap 在本次检查结束时回收；本工作树的依赖软链待主会话接收实现后移除，共享原件由各拥有任务保留。

## 集成验收边界

以上不证明生产部署、最终全量 Spec/Standards 双评审、组合后真实 WordPress HTTP 路径或 EN/DE 390/1440 视觉验收已完成。由地图主会话在同轮集成环境执行；本票未将本地通过改称生产通过。

部署须带上 engine 的新原子 sync 与 timer/service 定义，既有 `/etc/linker-engine.env` 增加专用 Woo Application Password 环境变量（只保存在服务器秘密配置），配置站点相应 manifest/jobs URL，读回实际 loaded source/compatibility/prepared_products 并确认 ack。首次替换 regular feed/contract 时脚本保留旧数据对，恢复旧代码时配合旧数据；不得只切新软链后给旧进程贴新版本。

第一阶段 EcoFlow 的草稿与资料 410 保护未改动；这份执行记录没有声称已重建知识库或通过实际公开 HTTP 撤权验收。

## 定时回执清理与受限文件系统

集成会话的生产只读检查发现，旧在用 cache 为 `/root/.cache/linker-engine`；新 sync unit 的 `ProtectHome=true` 隐藏该路径，且可写目录只有既有 state、日志与 systemd 目录。旧 `main()` 在 claim 前无保护地执行 GC：不可写 SQLite 会中断准备；未来数据库被隐藏时又会被误报成“没有文件，因此成功”。

修复将 GC 和准备分开：GC 明确失败、记录 journal、最终返回非零，但本轮仍完成独立的 Woo claim/build/loaded-readback/ack。两 unit 默认统一到 `/opt/linker-engine/state/cache`；环境文件中的旧值必须显式迁移，不能靠 unit 默认值覆盖。没有放开 `/root`、关闭 ProtectHome，或新增会因 GC 故障阻断 engine 重启/准备的 ExecStartPre。`--cache-preflight` 提供真实 SQLite 建库/事务/回滚写检查，部署必须在实际 unit namespace 内执行；`--cleanup-receipts` 可独立诊断，不代替定时证据。

本轮本地验证：9 个原生 SQLite/路径用例与 11 个原有同步用例共 20 通过，包括 readonly DELETE 失败时仍从本地 HTTP 取真实 feed、原生 loader 验证、发布并 ack 成功，最终返回 1；无 pending job 也清理；只删除到期行，保留边界/未到期行与原件；未来建库写检查及探针回收；拒绝缺省、相对、root 或逃逸 symlink 路径。CLI 对旧 root 路径的 preflight 实际返回 1 并打印原因，未访问/移动该目录。客户历史、Woo 草稿与托管资料原件不在本 GC 范围。

完整部署、迁移、回滚与实际定时验收步骤见 [ops/PUBLICATION.md](../../../../services/engine/ops/PUBLICATION.md)。该步骤要求先备份、停写并完整复制旧 cache，保留源作有界回滚，更新既有 env，安装 stable worker 与两 unit；在实际保护边界写检查，读回 engine 进程实际 cache，再观察两次真实 timer 触发及路径/删除数。当前 macOS 无 systemd，本轮没有执行该完整 unit/namespace/定时验收，也没有移动生产数据；这些通过前不得将 24 小时定期清理宣称已在生产生效。没有过期生产行时应记录零，不编造实际删除。

## 与统一工作台的边界对齐

本轮后续裁定要求长期产品方向以统一工作台为准。只读核对 `/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548` 的固定提交 `bc714bc628f1555d2ddcbface216dabc7b9371d5`，依据该树的 `docs/specs/548-workbench-application.md`、`548-design-geometry.md`、`548-geographic-intake.md` 与 `548-roof-import-workflow.md`；没有修改、重置或重启该工作树或运行实例。

| 边界 | 已查明的 source 合同 | 本票处置 |
| --- | --- | --- |
| 项目修订与未知确认 | `planning/workspace.py` 的 revise 以 expected_revision + intent key 在同一事务保存修订和回执；`planning/commands.py` 校验同 key 的完整命令 hash。工作台合同要求未知响应复用原 key/字节，保护更新的本地编辑。 | 新工作台继续由既有项目/命令机制维护。617 只修旧 Save/Ask 的未知结果提示；不扩展旧保存机制，不将旧 24 小时 selection receipt 当成永久项目。 |
| 冻结计算 | `planning/workspace.py` evaluate 固定 project/revision/input hash/context；`planning/frozen_run.py` 验证 run 与已存来源资产；`runtime_snapshot.py` 固定实际代码/依赖。`Run.is_current` 当前只表达项目修订相同。 | 本票旧 `/selection/validate` 和 `/report/pdf` 的 receipt 封住既有入口的重算与草稿读取。新工作台复用自己的 run 身份及冻结结果，不建立第二份 selection-receipt 历史；不能把 is_current 当成当前 Woo 发布许可。 |
| 来源与资产 | `planning/assets.py` 在所有读写前核 owner，以内容 hash 与独立 metadata hash 保留不可变私有来源；导入、项目修订和计算是不同命令。几何/CSV/用户场景具有独立来源、许可及质量。 | 产品事实与公开厂商资料仍只在 Woo 维护；客户项目输入继续由工作台的 Assets/修订维护。公开托管资料的 DocumentAccess 不接管私有用户上传、私有报告或数据源。 |
| SKU 资格与交接 | `planning/energy_kernel.py` 的实际输出明确 equipment_release / country_assessment 为 not_assessed。`records.py` 与 `schema.py` 存在 Handoff 值记录/表结构，工作台合同 §13 要求同一 project/revision/run/candidate/evidence 交接；本次未查到已生效的交接命令/HTTP 路径。 | 不能把物理场景重放、表结构或旧配置器 receipt 称为已完成产品资格/交接。新消费者应在其既有 run / candidate / handoff 边界接共享 Woo 权威；本票不在旧 UI 增造长期交接架构。 |

共享 Woo 合同的可复用范围是 `Products\Publication::manifest()`、`validate()`、生成工程 feed 与准备 jobs：canonical 产品身份、产品修订、资料身份/内容修订及产品关联、兼容修订、实际准备读回。当前许可每次新动作前后新读；完整候选及其证据都列入依赖，未准备新品不阻断其他已准备产品。过期产品/资料返回 409，当前权威不可核验返回 503；准备完成、历史 frozen hash 或客户端字段均不自行授予发布许可。

接入新工作台时，应在其产品资格/排名及新商务交接前后验证上述完整范围，并将验证过的 Woo 依赖与它自己的 project/revision/run/candidate/result hash 绑定。客户读取已拥有的历史修订/结果不触发重算，也不补读草稿产品；新计算、新报告或加入 Solution draft 则遵守当前许可。此段是对两个已核实合同的接口衔接结论，尚未声明新工作台已实现该消费者。

## 参考组件与技术资料的同轮修复

独立 Spec 复核发现：原 `Publication.view()` 仅验证 `feed.products`，原 Trina module 原样留在 engine；两条 roof 路径还主动将 `products/documents` 清空。这使组件 PDF 撤回、关联移除或同 URL 替换内容无法撤销依赖其电压、功率、尺寸的结果。原工程 JSON 的存在并非 Woo 许可，也不能把旧图值在请求时绑定为新读到的 PDF SHA。

按本轮确认合同，基础模块将既有 Trina 事实与 EN/DE 两份资料迁入一个 Woo 原生参考记录，后台仍使用现有图值和 Documents 维护；隐藏销售展示、virtual、无价格和产品分类，role 为 `reference_pv_module`。原 JSON 仅作一次迁移输入。feed.overlay 必须由当前 Woo 记录及有效 EvidenceBindings 生成，保留旧工程 ID，携带 canonical source、product/reference 同一修订以及文档 identity/revision/SHA/product association。此 PHP producer 与迁移由基础模块执行者拥有，本增量没有复制其 PHP 实现或写生产。

Python 消费者已落实：参考角色/工程 ID 与源修订一致，所有资料身份/内容 SHA/修订/源关联和图值引用集合均通过后，实际使用组件的住宅与两条 roof 才能计算。输出前再核完整依赖；roof 不再清空证明。`engineering_contract=2` 与显式 `reference_inputs` 参与结果指纹，source 产品和所有资料也列入普通依赖。旧 receipt 缺少标记、参考身份或完整资料证明，即使旧产品仍在上架，也不能保存/确认/生成新 PDF；不重算、不静默替换。新动作前未准备返回既有产品数据 503，明确内部 reason；在途撤证/变更与旧证明返回 409。客户历史原件保持不动。

全局 `compatibility_revision` 仅包含兼容合同。参考证据变化单独受其产品/文档依赖约束。overlay 为空可以正常加载；不读取 module 的 commercial、既有逆变器 retrofit 和无逆变器可评估的正常空候选不被封住。准备读回仅在参考实际可用时返回其 Woo 修订，缺证只遗漏该参考。当前 manifest 的明确参考角色或 overlay source 身份也不能混入销售候选。

真实本地快照的 producer 已有 URL 归一约定：feed 为 canonical de-linker URL，manifest 保留当前本地 uploads origin。消费者仅按 `LINKER_PUBLICATION_URL` 的精确 origin 归一映射并保留 path/query/fragment，仍须身份/版本/SHA/关联全通过；其他 host 同路径或同内容不能授权。此处与基础模块 owning source 已核一致。

本增量基于已合并的 `049a0beb` 聚合代码（本树 merge `ce53d946`），完成以下验证：

- `PYTHONPATH=src .../.venv/bin/python -m pytest -q`：**238 passed in 40.04s**。其中新 `test_reference_publication.py` **54** 个用例，覆盖真实 106 商品、Trina、慕尼黑 PVGIS/LoD2 输入下的三入口完整证明、七种事前失效、在途撤证、旧 SQLite receipt、已确认动作及渲染后换 bytes、空 overlay、未版本化旧输入、无关路径可用与准备确认、错误销售源及显式 origin 映射。其他 184 个已有工程/同步/GC/HTTP/报告/展示夹具测试同轮通过。
- Ruff 全目录 lint 与 format 通过（58 文件），mypy 全目录 **57 source files** 通过，`git diff --check` 通过。
- 配置器 App、engine/store/solutions API 四个前端文件 **66 tests / 4 files** 通过；整个 linker-tools `tsc --noEmit` 通过。八份 EN/DE 展示夹具只有 `selection_fingerprint` 各一行改变，真实选型、数字、报告、文案完全相同；指纹保持参与端到端夹具比较，没有从断言中剔除。
- 新 `reason` 不直接呈给客户，继续使用已审定 EN/DE 503/409 状态；文案准确性补记在同目录 copy-review。此次没有新增工具界面、长期保存机制、模型或商业按钮。

本地未启动新实例、复制依赖或全站备份；继续复用现有 venv 和两条共享依赖软链，未把软链加进 Git。工作树仍服务当前集成/复核，唯一代码和证据保留，依赖原件由原任务拥有；新增测试仅使用自动保留边界内的 pytest 临时目录。按已读本地存储规则，没有可独立认定过时的本任务运行副本可删除。

**集成仍需证明**：组合基础 producer、Python consumer 和 PHP 新 proof marker 检查；先备份并预览/执行一次 Woo 参考迁移，核真实记录、当前 30 项图值及两 PDF，而非采用测试用 synthetic ID；核其不进入商店/Genie/整套加入销售候选；在组合真实 WP 验证事前/在途/旧成功回执及 origin 对应；读回实际 engine 加载 source/compatibility/prepared reference，复核 EcoFlow 原有保护；完成全量双评审、EN/DE 390/1440 状态验收与此前记录的真实 systemd/定时清理证明。详见 ops/PUBLICATION.md。以上待办属于本地图同轮集成门，本增量不将其宣称完成，也没有部署、生产数据写入或改动另一工作台的 source/运行实例。

## 原生完整 feed 的资料格式回归

集成第一次实际 queue build 在原生 loader 处拒绝，未重启也未成功 ack。只读核本实例 `engine/validation-input.json`，1433 项 schema 错误分为：610 个文档的明确 `aliases`、378 个图值的 `citation.doc` 来源文件名、445 个历史语言标签。准确位置是 `citation.doc`，不是额外的 sources 数组。本增量不全局放开 additionalProperties，也没有将原始全量 owner 数据提交。

schema 与 typed `Document/Citation` 明确保留这两项；别名必须为托管 URL，候选的已加载别名在每次入口还须属于当前文档的许可 URL 集合。来源文件名和同 SHA 不授予新许可。基础模块 producer 独立提交 `a425071349a0b40c67cfa11889cc7142872a5f75` 将 EN/DE 大小写、MUL/MULTI/EN/DE/DE/EN 和空/未知标签派生为 canonical 语言；合法双字母保持对应小写，多语言 `mul`、未知 `und`，不猜测 en/de。资料 type 复用已有 `Materials::document_kind`，解决历史 German type 标签被报告精确匹配漏掉的问题；Woo 原值与 publication proof 保留。

本地互操作证明使用上述私有原始输入（SHA `a36f4146d8f0be26153f8c12d4d57f739113535439b861dd84bf9c81698d4f92`），仅 stdin/stdout 调用基础模块该精确提交的原生 PHP `document_language()` 与 `Materials::document_kind()`，不是 Python 另造转换表；接着本树 `Products.from_feed` 原生加载成功：**85 产品、1 Trina reference、610 项 aliases、378 项来源标签完整保留**，语言为 en 296 / de 138 / mul 155 / und 21。空 object 形状保持，原始输入 hash 前后相同，没有改写共享实例或重启进程。这是实际输入与两端 source 的本地互操作预验，未将其称为重新生成的 HTTP feed 或已经 loaded/ack 的运行证据；主线合入两端后须重跑真实队列。

新增小型匿名形状夹具 `woo-document-shape.json` 和 21 个针对性用例，覆盖字段保留、canonical 语言、拒绝未投影/未知原始标签、拒绝任意新键与外站别名、EN/DE 报告优先语言及 mul/und 回退，以及移除当前别名后该产品不再进入候选。完整 engine **259 passed in 43.29s**；Ruff lint/format（59 文件）、mypy（58 source files）和 diff 检查通过。既有 EN/DE 展示夹具原值仍通过，没有修改客户文案或报告结果。没有执行共享 WP mutation、claim/restart 或生产写入。
