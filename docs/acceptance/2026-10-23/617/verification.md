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
