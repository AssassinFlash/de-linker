# 系统选型的当前发布依赖

依据：[统一发布规则](https://github.com/AssassinFlash/de-linker/issues/609)、[系统选型实现](https://github.com/AssassinFlash/de-linker/issues/617)、既有 [Solution Configurator 规格](14-solution-configurator.md) 与 `docs/research/2026-10-09/pv-wholesale-selection-tools.md` 的封闭产品范围、厂商放行与整套物料清单模式。保留工程算法、三屏与既有 EN/DE 失败文案；Woo 原生发布本身不能撤销外部进程内的已加载工程对象，因此在现有服务边界增加当前许可验证。

## 当前对象与已加载代

`services/engine` 每个计算读取 Woo `/linker/v1/publication/manifest`。只保留当前 canonical 产品版本、资料身份/内容版本和产品关联均与已加载 feed 一致的交集。候选、被排除项、配件和备选都从该视图计算。未准备的新产品不进入交集；空集正常返回 `no_candidate`。`compatibility_revision` 标识厂商兼容合同。没有有效 Woo 文档关联的兼容依据不使用，也不以 JSON 中存在 URL 代替发布许可。

结果返回前再次检查全部使用的候选与资料依赖。下架/内容更新发生在途中则返回 409；Woo 当前权威不可读时返回 503。Python 的发布判断和 PHP 的最后验证均独立于 `off` / `observe` / `enforce` 的反滥用模式。显式给出的旧逆变器或电池 ID 返回 422，保持原输入，不替换为首候选。

## Woo 商品、电缆参考与项目组件

Woo 发布在售商品的 SKU、型号、图值、资料和库存。`feed.products` 用于选品。已发布的电缆工程参考使用 `engineering_role=reference_cable`，通过 `feed.overlay` 提供来源已绑定的 `cable_facts`。电缆记录保留 canonical 产品、修订、工程 ID 和资料关联。Woo 编制商品候选、品牌目录和购物草稿时排除这些参考。

光伏组件在项目中使用通用功率、尺寸及客户提供的电气参数。品牌、型号、Woo ID 和厂商组件资料不进入配置器组件选择、Genie 产品推荐、报告或新导出。项目取用通用参数不依赖 Woo 参考记录或其发布修订。原有屋面、组件数量、项目/修订归属及私有文件的访问权限随项目保留。见[业主裁定与交付范围](https://github.com/AssassinFlash/de-linker/issues/1168)。

一次数据清理使用 `tools/migrate/1168-retire-pv-supply.php`。先用 `wp eval-file ... plan` 检查实际商品、订单行、词项归属和文件关联，再按备份规格运行 `apply`。订单引用的商品及其语言配对转为私有。未被订单引用的已核实废弃商品、独占品牌和型号词项、专属测试 PDF 被移除；原厂文件撤销公开权限。再次运行 `plan` 时应无待处理项。

线上 feed URL 与 manifest URL 一致。本地快照保留本地 uploads origin，而现有 feed producer 将当前站点 URL 归一为 `https://de-linker.com`；Python 只按 `LINKER_PUBLICATION_URL` 所指定的同一精确 origin 做对应归一，保持路径、query、fragment 不变，且身份/修订/SHA/关联仍须全通过。任意其他主机即使路径或内容相同也不能通过。

原生 Woo 文档可携带 `aliases`（明确托管 URL 列表），图值 `citation.doc` 保留原始来源文件名；schema 与 typed model 明确接收这两项，其他未声明键仍拒绝。文件名只作来源标签，不授予许可。引用允许使用当前同一文档的明确 URL 别名；所有已加载别名仍须属于新读到的许可 URL 集合，资料身份/修订/关联也须有效。producer 将历史语言标签派生为小写双字母、`mul`（明确多语言）或 `und`（未说明/未识别），不改 Woo 原值或其证明；资料类型复用现有产品资料的 EN/DE 映射。报告优先用匹配语言，缺少匹配时保留既有可用资料回退，不将未知语言假定为英文。

新计算记录实际使用的 Woo 产品、已授权资料与兼容合同。电缆输入以当前产品与所引用资料的版本为准。项目的通用组件不会生成销售行或厂商参考依赖。客户已生成的报告由账户文件入口按原有所有权读取，新报告与新导出按当前项目参数产生。

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
