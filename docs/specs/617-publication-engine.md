# 系统选型的当前发布依赖

依据：[统一发布规则](https://github.com/AssassinFlash/de-linker/issues/609)、[系统选型实现](https://github.com/AssassinFlash/de-linker/issues/617)、既有 [Solution Configurator 规格](14-solution-configurator.md) 与 `docs/research/2026-10-09/pv-wholesale-selection-tools.md` 的封闭产品范围、厂商放行与整套物料清单模式。保留工程算法、三屏与既有 EN/DE 失败文案；Woo 原生发布本身不能撤销外部进程内的已加载工程对象，因此在现有服务边界增加当前许可验证。

## 当前对象与已加载代

`services/engine` 每个计算读取 Woo `/linker/v1/publication/manifest`。只保留当前 canonical 产品版本、资料身份/内容版本和产品关联均与已加载 feed 一致的交集。候选、被排除项、配件和备选都从该视图计算。未准备的新产品不进入交集；空集正常返回 `no_candidate`。`compatibility_revision` 只标识兼容合同，不混入单一参考组件的修订。没有有效 Woo 文档关联的兼容依据不使用，也不以 JSON 中存在 URL 代替发布许可。

结果返回前再次检查全部使用的候选与资料依赖。下架/内容更新发生在途中则返回 409；Woo 当前权威不可读时返回 503。Python 的发布判断和 PHP 的最后验证均独立于 `off` / `observe` / `enforce` 的反滥用模式。显式给出的旧逆变器或电池 ID 返回 422，保持原输入，不替换为首候选。

## 参考组件仍由 Woo 维护

光伏组件不进入销售产品分类，保留业主批准的参考组件设计输入。既有 Trina 的事实及两份托管 PDF 一次迁入 Woo 原生参考记录：已发布、隐藏销售展示、virtual、无价格、无产品分类；`engineering_role=reference_pv_module` 与 `engineering_id=mat_trina_solar_tsm_460neg9r_28` 标识用途。后台仍用现有产品图值与 Documents 入口维护。它不能作为商品候选、推荐或加入 Solution draft 的产品；非销售角色不免除资料公开许可校验。

`feed.overlay` 从这一 Woo 记录及当前 EvidenceBindings 生成，不再运行时读取 `data/engineering-overlay.json`。文件仅作一次迁移输入。每项保留 `{id,kind,brand,model,figures,documents}`，增加 `canonical_product_id`、`product_revision`、`reference_revision`；后两者是同一 Woo 产品修订，不再构造另一份手工版本。文档携带当前 `document_id`、`document_revision`、`blob_sha256` 与 `product_ids`。manifest 中同一 source 还须具有匹配的参考角色与工程 ID。

使用参考组件的住宅完整候选评估与两条屋顶入口，计算前验证源记录仍发布、角色与 ID 一致、源修订一致、每份已加载资料的身份/修订/内容 SHA 及关联仍有效，全部图值引用属于这份获准资料集合。结果放行前再核相同范围。不能将旧图值临时绑定为刚读到的新 PDF hash，也不能以文件仍可访问、共享 SHA 或其他产品的关联授予参考组件许可。

线上 feed URL 与 manifest URL 一致。本地快照保留本地 uploads origin，而现有 feed producer 将当前站点 URL 归一为 `https://de-linker.com`；Python 只按 `LINKER_PUBLICATION_URL` 所指定的同一精确 origin 做对应归一，保持路径、query、fragment 不变，且身份/修订/SHA/关联仍须全通过。任意其他主机即使路径或内容相同也不能通过。

新结果 `publication.engineering_contract=2`，且显式携带 `reference_inputs`。每个参考项为 `{reference_input_id,reference_revision,product_id,product_revision}`；其 source 产品依赖与全部文档依赖同时列入普通 `products` / `documents`，文档额外携带 `blob_sha256`。参考信息因此参与选择指纹及 Woo 最后校验。屋顶结果只列实际使用的参考及资料，不再清空依赖，也不附带无关销售候选。

旧 receipt 没有这一版本标记、遗漏参考身份或不含其完整产品/文档证明时，后续保存、确认与新 PDF 拒绝为 409。资料或源在途撤回/更新同样拒绝 409；计算开始前参考未准备/不可用，返回 503 `publication_unavailable`，明确 `reason=reference_evidence_unavailable`。客户拥有的历史快照和已生成 PDF 原件仍保留。

不实际读取参考组件的工商业计算、既有逆变器 retrofit，以及没有任何逆变器可评估的正常空候选，不携带参考依赖。`reference_inputs=[]` 在这些路径合法。overlay 可为空并正常加载普通产品；参考未准备不会封住这些计算。`/resource/version?ready=1` 仅确认已验证参考源的当前产品修订，缺证时只遗漏该参考；普通已准备产品仍可确认。参考资料变化不改变全局兼容修订。

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
