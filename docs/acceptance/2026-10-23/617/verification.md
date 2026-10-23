# 系统选型发布依赖：执行检查

对应[系统选型实现](https://github.com/AssassinFlash/de-linker/issues/617)。分支 `codex/617-publication-engine`；源基线 `177e560a`，合并受信上游接口提交 `0a10f2ee`（历史/整套动作）与 `f0789a57`（Woo 发布合同）进行本地类型检查。它们是其他执行者的实现，最终地图集成应包含各自后续修复。

## 已执行

- `services/engine`: 完整 pytest 172 通过，真实 106 产品工程/PVGIS/LoD2 夹具；ruff 通过，mypy 31 个源码模块通过。后续屋顶依赖缩窄后补跑 API/UI 夹具；准备与发布专项 22 通过。
- 新发布专项含：异步未运行前排除草稿 EcoFlow、在途任一候选撤权、资料新修订、未准备新品、空集、权威不可读、明确旧电池/逆变器、私有可信结果验证、PDF 精确匹配。
- enforce 真实工程路径先计算，之后把计算函数替换为“调用即失败”，连续两次确认验证和 PDF 均保持相同选型、成功且没有重算。
- 自动 sync 用本地 HTTP 与引擎真实 schema loader 验证整代发布、空 products、任一部分错误保留旧数据、旧进程读回失败整代回滚、最多两代与作业确认。
- linker-tools TypeScript 全项目 `tsc --noEmit` 通过；五个前端测试文件 58 用例通过（engine transport/App/store/solutions/protection）。409 沿用已翻译 unavailable 状态；PDF 请求携带屏幕指纹。
- linker-tools PHP 10 个针对性单元测试、51 断言通过；六个变更 PHP 运行类的 PHPStan level 8 通过；变更 PHP 运行类和针对性单元测试 WPCS 检查通过。
- 按锁文件复用已存在的主仓 Python venv / PHP vendor，以及同轮历史任务的 node_modules；没有复制依赖、启动实例、新建整站备份、发信、改模型或写生产。最终移除本工作树的依赖软链及临时测试 bootstrap；共享原件由各拥有任务保留。

## 集成验收边界

以上不证明生产部署、最终全量 Spec/Standards 双评审、组合后真实 WordPress HTTP 路径或 EN/DE 390/1440 视觉验收已完成。由地图主会话在同轮集成环境执行；本票未将本地通过改称生产通过。

部署须带上 engine 的新原子 sync 与 timer/service 定义，既有 `/etc/linker-engine.env` 增加专用 Woo Application Password 环境变量（只保存在服务器秘密配置），配置站点相应 manifest/jobs URL，读回实际 loaded source/compatibility/prepared_products 并确认 ack。首次替换 regular feed/contract 时脚本保留旧数据对，恢复旧代码时配合旧数据；不得只切新软链后给旧进程贴新版本。

第一阶段 EcoFlow 的草稿与资料 410 保护未改动；这份执行记录没有声称已重建知识库或通过实际公开 HTTP 撤权验收。
