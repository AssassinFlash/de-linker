# 系统选型的当前发布依赖

依据：[统一发布规则](https://github.com/AssassinFlash/de-linker/issues/609)、[系统选型实现](https://github.com/AssassinFlash/de-linker/issues/617)、既有 [Solution Configurator 规格](14-solution-configurator.md) 与 `docs/research/2026-10-09/pv-wholesale-selection-tools.md` 的封闭产品范围、厂商放行与整套物料清单模式。保留工程算法、三屏与既有 EN/DE 失败文案；Woo 原生发布本身不能撤销外部进程内的已加载工程对象，因此在现有服务边界增加当前许可验证。

## 当前对象与已加载代

`services/engine` 每个计算读取 Woo `/linker/v1/publication/manifest`。只保留当前 canonical 产品版本、资料身份/内容版本和产品关联均与已加载 feed 一致的交集。候选、被排除项、配件和备选都从该视图计算。未准备的新产品不进入交集；空集正常返回 `no_candidate`。兼容合同与工程 overlay 采用 Woo 同一 `compatibility_revision`。没有有效 Woo 文档关联的兼容依据不使用，也不以 JSON 中存在 URL 代替发布许可。

结果返回前再次检查全部使用的候选与资料依赖。下架/内容更新发生在途中则返回 409；Woo 当前权威不可读时返回 503。Python 的发布判断和 PHP 的最后验证均独立于 `off` / `observe` / `enforce` 的反滥用模式。显式给出的旧逆变器或电池 ID 返回 422，保持原输入，不替换为首候选。

## 已确认结果与下一步

成功结果增加 `publication`（产品、资料关联依赖、兼容修订与源修订）和 `selection_fingerprint`。指纹覆盖规范化输入、完整候选与选中结果、数量及依据版本；报告生成时间不参与。私有 SQLite selection receipt 保存服务端完整结果，保留 24 小时，与既有 native reply receipt 的保留边界一致；无匿名读取接口，文件权限 0600，不保存 Logo。过期后明确要求重新选型。

`POST /selection/validate` 是可信服务端接口：既有 `X-Linker-Service-Token`，body `{kind:'residential'|'commercial',input,selection_fingerprint}`。取已确认结果并重新验证全部发布依赖；返回直接的完整结果。它不重新计算，不另消耗一次 design 配额。PHP `linker_tools_engine_request` 的 `NativeEngine` 允许这个固定服务路径；保存和整套加入不得改用浏览器自报物料行。工商业多个 systems 需由消费者显式选择可信结果中的索引，禁止默认第一套。

`POST /report/pdf` 必须携带 `{input,selection_fingerprint,logo?}`。使用当时已确认的 `result.report`，在渲染前后检查依赖，不按相同输入重新选一套。PHP Proxy 也验证同一个已确认结果，并把其依赖作为服务器内存元数据交给 native receipt；二进制 PDF 不用大型 HTTP header 携带依赖。旧 receipt 无证明或依赖失效即拒绝。客户已经生成的历史 PDF 由账户所有权路径读取，本接口只负责生成新 PDF。

## 自动准备与版本读回

现有 feed sync 改为持久准备队列消费者。每分钟 claim `engineering` 作业，从 Woo 取一次完整 feed；feed、兼容合同与 manifest 全部验证后作为不可变代发布，再切同一个 `current` 软链。加载进程固定解析后的 feed 所在代，校验两文件 SHA，不能读混代。空 `products` 合法；任一输入校验失败不更换任一文件。最多保留当前与前一成功代。

重启后通过带服务令牌的 `/resource/version?ready=1` 核实际加载的源修订、兼容修订和可用产品交集，再 ack `prepared_products`。磁盘新文件不能为旧进程改标签；部分产品准备失败继续保留待办。作业、源修订或租约已过期时不恢复权限。自动工作器需要既有 `/etc/linker-engine.env` 中的 `GENIE_SERVICE_TOKEN` 与专用 `LINKER_PUBLICATION_USER` / `LINKER_PUBLICATION_PASSWORD`（Woo Application Password，服务器秘密，不进仓库）；可选 `LINKER_PUBLICATION_JOBS_URL` 与 `LINKER_PUBLICATION_URL` 指向对应站点。

首次迁移和部署需由集成任务先保留可恢复的旧数据/代码，按项目生产备份与读回纪律执行；部署前读回服务版本、启动定义、环境和数据位置。第一阶段 EcoFlow 草稿与资料 410 保留，不能由本票恢复。

## 验证边界

真实工程夹具包含 106 个产品、厂商合同、慕尼黑 PVGIS 与 LoD2 数据。专项验证覆盖同步未运行前撤权、在途撤权（非最终选中候选也检查）、同 URL 新资料版本、未准备新品、空集、来源不可读、显式旧 ID、PDF 指纹、可信验证通道和 enforce 下后续动作不重算。sync 以实际本地 HTTP feed 和引擎原生 schema loader 覆盖全代发布、输入失败、进程未加载回滚、保留边界与准备确认。

本文件描述代码合同；生产部署、最终 Spec/Standards 双评审和组合后的真实 WordPress / EN-DE 390/1440 验收由同一地图的集成记录给出，不能由本地单元测试代替。
