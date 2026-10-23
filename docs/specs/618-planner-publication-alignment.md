# 统一发布规则与新项目工作台的交界

2026-10-23。依据业主本轮确认的[统一产品与资料发布规则](609-product-publication.md)，以及新工作台负责会话转达的当期协调。本文调整[迁移、全链验收与上线](https://github.com/AssassinFlash/de-linker/issues/618)的集成边界，不把旧配置器的界面或结果保存机制定为长期目标。

## 已核对的实际来源

只读核对 `/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548` 的 `bc714bc628f1555d2ddcbface216dabc7b9371d5`。未修改该工作树、其未跟踪证据或 p548 实例；未重启、重置或部署该工作线。

- `docs/specs/548-workbench-application.md`：项目版本、持久命令意图、冻结结果、资格判断和交接要求，尤其第 6、8、11、13、14 项。
- `docs/specs/548-design-geometry.md`、`548-geographic-intake.md`、`548-roof-import-workflow.md`：几何、用户原件与来源许可拥有独立的私有生命周期。
- `planning/workspace.py`、`commands.py`、`records.py`、`frozen_run.py`、`dependencies.py`、`schema.py`：已有 owner、expected_revision、持久 key、内容哈希及 run/context/asset 的冻结校验。只看到 Handoff 值对象及存储表，不将其称为已完成的 Woo 交接；设备资格和下游集成仍由新工作台工作线完成。

## 归属与复用

| 能力 | 唯一归属 | 本轮处理 |
| --- | --- | --- |
| 当前产品事实、发布许可、托管技术资料关系及文件版本 | Woo `Products\Publication` | 通用基础继续完成，供所有消费者使用 |
| 工程 feed、索引与自动准备 | Woo 权威的可重建派生输出 | 共享 manifest/validate/jobs，不增加另一份手工维护名单 |
| 新项目保存、修订、恢复、计算任务与历史 | 新 `planning` 与 `apps/planner` 合同 | 不用旧 saved-solution 或 24 小时 selection receipt 替代 |
| 屋顶、CSV、用户原件、几何与运行来源 | 新工作台私有 Assets/run/context | 不当作公开产品资料，不搬进 Woo，不被公开 PDF 门误伤 |
| 当前线上旧工具的新计算、报告、保存和整套加入 | 现有入口的必要撤权修复 | 保留最小闭环，待新入口对等承载后迁移；不增加旧工具功能 |
| Genie 普通产品卡与产品清单 | 签名完整 BOM、身份及当前 Woo 依赖 | 无伪造住宅输入，无第二套项目系统 |

共享的服务端界面在 `614-publication-contract.md`：当前读取 `manifest`，新操作前后 `validate`，正常 Woo 写入产生自动 jobs。`products` 与 `documents` 的空列表只代表空许可；哈希、旧索引和冻结原件不授予当前公开权限。真实撤权或依赖变化为 409；权威不可读为 503。

新工作台已有的冻结 context 可保存当时的 Woo 依赖文档与相应产品、资料版本，但该文档只是历史依据。设备资格判断需从当前 Woo 允许且已准备的集合取候选，记录全部候选和证据依赖；worker 输出、当前结果复用、新报告和交接都重新验证。历史 run、历史原件和已生成 PDF 依原 owner/权利读取，不重算、不补取草稿事实。

新交接应沿用 project/revision/run/candidate/evidence 及永久意图 key；在 Woo 写入边界核当前发布、账号和库存规则，并完成整套写入及实际回执。未知响应重试复用原意图。旧 `selection_fingerprint` 与 selection receipt 是当前旧入口的安全适配，不成为新工作台的项目权威。

## 验收与声明边界

本轮继续核 Woo、原 URL 文件门、Genie、知识库及当前已上线工具的撤权。旧工具截图只证明当前线上入口的必要修复，不证明新工作台已完成。新工作台自己的规格、原型、原生验收和整体上线由其负责工作线持有；它的公开产品资格及交接在接通共享发布合同前，不应宣称“全站所有未来入口都已自动同步”。

第一阶段的 EcoFlow 草稿状态和临时文件规则持续保留。其他安全任务的入口封锁保持；不因本轮产品权限修复解除。替换旧入口必须先证明新入口承载同等撤权、完整依赖、历史和整套动作约束。
