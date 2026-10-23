# Woo 发布权威、资料访问与自动更新：源码调查与推荐接口

日期：2026-10-23。对应问题：[确定 Woo 发布权威、资料访问与自动更新的统一接口](https://github.com/AssassinFlash/de-linker/issues/612)。

**状态：Codex 只读源码调查；不是已完成的 Claude Opus 正式研究，也不是已实施修复。** 原计划调用 Claude Code `--model opus`，但实际活动配置把别名映射到另一供应商模型；未发现可核实的既有 Opus 路由，调用已中止，未采纳任何模型输出，未修改全局配置或网站模型通道。是否调整执行分工由主会话与业主另行确认。

源码基线固定为 `5eabfffc70c01df3d2b76ec0823d64eaad39a8ef`。下列“现状”来自该提交，不能据此推断生产进程已加载它；本次没有生产写入或运行验收。

## 已确认的业务边界

[业主的正式答复与规则]( https://github.com/AssassinFlash/de-linker/issues/609#issuecomment-6363552168 )明确：产品、发布状态、资料关联和公开决定只在 WooCommerce 维护；工具只消费可重建的派生数据。撤下应立即阻止后续读取与操作，不能等待重建；上架可先展示，资料解析与工程准备完成后自动进入工具。共用 PDF 仍有有效上架产品关联时可公开，但不能把已撤产品作为当前型号返回；历史私有快照保留，新操作整套重验；资料去重不转授其他关联的权限。第一阶段的 EcoFlow 草稿与资料 410 保护继续保留到新通道证明对等。

## 现有拥有源与缺口

| 已核能力 | 证据及含义 |
| --- | --- |
| 产品后台已有资料维护位置 | [DocumentsMetaBox::save](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Admin/DocumentsMetaBox.php#L146-L200) 在 `save_post_product` 保存资料列表；[hosted_url](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Admin/DocumentsMetaBox.php#L243-L256) 只验证同站 host，未验证该 URL 对应文件的当前公开许可。继续复用该入口，不另建手工资料库。 |
| 工程 feed 已从发布产品装配 | [EngineeringFeed::feed/item](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Products/EngineeringFeed.php#L52-L121) 只返回 `publish` 产品，并带产品资料与兼容合同；包络含每次变化的 `generated_at`，没有稳定的源内容版本。不能拿整个原始 JSON 字节直接当业务 revision。 |
| 英德事实已有源身份入口 | [SelectionFacts::for_product](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Products/SelectionFacts.php#L109-L130) 经语言层 filter 解析事实源产品。应复用 canonical identity，同时显式记录各语言公开许可，不能把翻译 ID 当第二套工程产品。 |
| Woo 已有持久任务与防并发先例 | [Assessment Queue](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Inquiry/Assessment/Queue.php#L103-L108) 使用 Action Scheduler；[process](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Inquiry/Assessment/Queue.php#L123-L140) 复用 Lock。适合承接变更通知与重试；不表示目前已有产品发布同步作业。 |
| 私有文件可先封静态读取，再动态流 | [PrivateFiles](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Account/PrivateFiles.php#L85-L104) 写 deny-all；[DocumentDownload](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Account/DocumentDownload.php#L92-L131) 检查 owner 后直接输出文件字节。可复用存储保护与流式机制，技术资料的公开许可应单独判断。 |
| 知识构建与发布已有可复用 CLI | [build](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/index/build.py#L1-L11) 定义 Mac 构建；[publish_index](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/ops/publish_index.py#L46-L71) 校 SHA、上传和读回；[index_release](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/ops/index_release.py#L51-L60) 原子切换 current。尚不能据此声称有自动 worker。 |
| 运行资源约束 | [知识规格](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/docs/specs/10-knowledge-index.md#L44-L45)、[不做](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/docs/specs/10-knowledge-index.md#L71-L72) 约束重解析在构建机，VPS 不跑 Docling/OCR/知识构建模型。此处只援引现行运行约束，不采用文档较早、已被后续章节修正的存储推断。 |

## 推荐的最小统一接口合同（待实现）

Woo 内增加一个发布装配器，所有入口与任务共享它；不要让各工具分别查询和解释产品状态。使用现有产品/资料字段，补齐资料关联的稳定身份、主动撤下状态与内容版本。派生的查询表/索引属于自动缓存，不成为新手工源。

建议合同字段：

- `source_revision`：规范化产品、发布许可、资料关联、资料内容 hash 与工程合同的稳定 hash；排序固定，排除 `generated_at`、任务时间、构建时间。
- 产品：`canonical_product_id`、`locale_product_ids`、各语言公开状态、`product_revision`、工具准备状态。事实共享不意味着各语言状态可以被忽略；许可必须由服务端解析，不能信任浏览器报来的 ID。
- 资料：稳定 `document_id`、`document_revision`、`blob_sha256`、规范 URL 与各别名、`active`，以及稳定的产品关联及其修订。相同 SHA 只复用解析缓存；URL/产品关联/公开权分开。相同 URL 换内容必须产生新内容修订，撤销旧块使用许可。
- 每个工具所用的 product/document/dependency revisions 与 loaded generation；`ready` 必须代表服务进程实际加载并核验了匹配版本，不是文件传完或命令退出。
- 公共读取接口只返回有效许可对象；服务认证接口供工作机领取准备任务、校验依赖与确认实际加载。具体 route 名由实现保持最小，合同语义保持一致。

**即时的边界**：Woo 变更提交后，新请求按当前权威判断；在途请求在输出及写操作提交前重新读取当前许可。已下载到客户设备的历史字节不能远程收回。资料静态缓存必须退出可绕过门控的路径，不能靠有过期窗口的 allowlist 保证撤下。

## 原文件与上传的公开门

推荐保持原公开 URL，通过 Web 服务器重写至 WordPress 授权流；规则必须在“现有文件直接返回”的 shortcut 之前生效。授权流解析实际注册路径与别名，从当前 Woo 关联计算：资料 active 且至少有一个有效上架关联，才输出字节；未知技术资料/无关联资料默认不可公开。严禁 302 回原静态文件，否则门被绕过。路径要规范化并验证在受管目录内，不能由查询参数任意读本机文件。

控制范围是产品技术资料及其别名。私有询盘/历史报告继续走原 owner gate，不能被公开资料许可放行，也不能以“全部 PDF 禁止”为名破坏历史快照下载。新上传从 Woo 资料入口写入受保护的暂存位置，在有效关联和内容登记提交前不得出现静态可公开窗口。通用媒体库、旧目录与未知 PDF 的归属需要迁移清单核实，不可按扩展名猜测其业务用途。

共用手册保留原件；关联许可是当前有效集合的交集，B 的资料关联撤下不能被 A 的相同 SHA 或别名重新授权。内部解析或构建取源走认证下载，不依赖公开链接仍可读。原 EcoFlow 49 路径的临时 410 逐条读回证明新门等效后才能移除。

## 自动准备与失败路线

推荐以 Woo 变更 hook（状态、删除、相关 meta/资料关联、文件内容、语言配对与工程合同）为触发，写持久的幂等任务，提交后立即更新发布许可。hook 只登记作业，不在后台保存操作中做重解析。撤权直接由当前 Woo 门生效，作业失败不恢复旧许可。

知识准备复用 Mac 构建与现有发布 CLI：新增受控的构建机 worker，以系统调度自动拉取/认领 Woo 作业，按源修订去重、租约防重复，复用 SHA 解析/向量缓存，构建后上传、原子发布，读回运行服务实际 loaded revision，再 ack 准备完成。**这是待实现的新自动化，不是已存在能力。** Mac 离线时作业持久保留，新增或修改资料保持 unready；已有且依赖未变的产品继续可用，撤权即时独立生效。失败状态、重试原因与最后成功版本在现有后台/摘要入口可见，不要求业主另按“同步”。重试策略和资源限额应依据实际调度环境与既有约束配置，不能凭空加无来源阈值。

源读取、构建、上传与 ack 全程携带原 source/dependency revision；若准备过程中发生第二次编辑，旧作业不得把新状态标 ready。回滚代码或索引也不能把已撤许可恢复。每次换代保留当前与可恢复上一代，依项目本地存储规则滚动回收。

## 实现切分与验收

1. Woo 发布装配器/合同与持久作业：先可供测试夹具使用，覆盖产品与资料的全部变更，不把前端状态当权威。
2. 文件门与受保护上传：先在本地/评审站验证原 URL、别名、共用 PDF、同 SHA 不同授权、同 URL 换内容、未知/未关联资料和私有报告，再迁移临时 410。
3. 自动准备 worker 与加载确认：复用现有 build/publish，覆盖离线、并发租约、失败重试、过时 ack、进程未重开但磁盘已新等真实状态。
4. Genie 与选型消费合同：独立源核与实现，不能仅加产品列表过滤就宣称完整修复。

必要验收包括：一次 Woo 上下架无需手动同步；全部产品撤下的空候选集；在途撤下；资料撤下但产品仍上架；共用 A/B；不同 URL 相同 SHA；同 URL 内容替换；构建机离线；服务加载旧代；原文件访问与私有历史 owner 规则；第一阶段所有 EcoFlow 保护持续成立。工具客户文案需遵循项目双语与对抗评审要求。

## 证据边界

已核：上述固定提交的源码与规格、CLI 真实别名路由不可证明 Opus 可用。待实现：统一合同、资料门、自动 worker 与消费者校验。未验证：生产现有 rewrite/CDN 缓存路径、Mac 自动作业安装和可用时段、真实跨服务竞态；不得把本笔记当部署或验收完成。
