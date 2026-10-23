# Genie 与系统选型消费 Woo 发布许可：源码调查与修复路线

日期：2026-10-23。对应问题：[确定 Genie 与系统选型消费 Woo 发布许可及旧状态校验的路线](https://github.com/AssassinFlash/de-linker/issues/613)。

**状态：Codex 只读源码调查；Claude Opus 正式研究受路由限制，尚未完成。** 显式 `opus` 被本机活动配置映射到其他供应商；调用中止、未采纳输出，没有更换网站模型通道或全局配置。本笔记提出的技术选择需要按主会话确认后的执行分工继续，不冒充已修复或 Claude 评审结论。

固定基线 `5eabfffc70c01df3d2b76ec0823d64eaad39a8ef`。本轮未启动站点、未测试生产运行、未修改生产。业务规则只采用[业主确认的发布与历史边界](https://github.com/AssassinFlash/de-linker/issues/609#issuecomment-6363552168)。

## Genie 与知识库的实际缺口

| 源码现状 | 修复必须覆盖的边界 |
| --- | --- |
| [KnowledgeSearch](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/src/linker_genie/knowledge.py#L67-L109) 直接搜索本地已加载索引并返回 text、figures、URL、index_version | 索引版本不等于当前 Woo 公开许可；同一个工具入口必须先限制当前可用范围，输出引用也要再验。 |
| [retrieval.scope](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/src/linker_genie/retrieval.py#L208-L239) 产品找不到文档映射时可能没有过滤条件而返回全库 scope | 空许可集合必须是空结果或明确不可用，不能解释为“不加过滤”。 |
| [retrieval.search](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/src/linker_genie/retrieval.py#L362-L392) 产品/型号圈定后仍添加全库回退 | 回退只能扩大到当前许可全集，不能越过撤权；dense、BM25 与型号推断必须共用相同限制。 |
| [with_page_neighbours](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/src/linker_genie/retrieval.py#L395-L421) 可追加整页或短资料邻块 | 初始 hit 合法不代表追加块合法；邻块同样做适用产品与内容版本过滤。 |
| [corpus.DocumentRow](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/index/corpus.py#L26-L40)、[SQLite schema](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/index/store.py#L40-L60) 以 SHA/型号关联资料，chunk 没有产品适用关系 | 同一 PDF 服务 A/B 时，doc 级白名单不能阻止 B 的表格/参数进入回答；内容去重与授权身份必须分开。 |
| [default_index](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/src/linker_genie/retrieval.py#L450-L460) 只首次打开索引单例 | 切 `current` 软链不代表进程已加载新索引；须读回 loaded source/index revision 并受控重开。 |
| [ground](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/src/linker_genie/ground.py#L10-L31) 校验本轮工具事实，[hydrate](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/genie/src/linker_genie/hydrate.py#L11-L16) 自动补引用链接 | “来自本轮工具”只说明来源，不证明输出时仍有权公开；不能用 grounding 代替当前发布校验。 |

推荐把统一发布门接在工具准备与最终输出两端，而不是给 EcoFlow 加永久品牌例外。每轮从 Woo 认证接口读取当前许可与依赖修订，产品、检索、页面感知、兼容查询、历史上下文与附件都使用同一身份。chunk 需要显式的适用产品/资料版本依据，保守处理无法确定的共用手册内容：只允许能证明适用于仍上架产品的块，不能把“整份 PDF 仍可下载”推导为“其中任何型号可技术回答”。内容不能可靠映射时保持该部分 unready，不凭模型猜授权。

最终输出前重新验证本轮产品、chunk、资料、动作所用依赖，变化则丢弃失效输出并以当前状态重试/给出已有错误面；不要对已经混入失效技术结论的文本只删一张卡片。历史助手消息、摘要和页缓存不能作为当前产品事实重新注入。客户本人查看历史快照保留，新的轮次、重新计算和任何后续动作从当前门重新开始。用户上传资料若识别到已撤型号，允许识别并交团队，不能继续技术答疑、选型或借客户上传绕过撤下。

知识新增与更新继续使用 Mac 构建，自动 worker/持久队列路线见[发布权威调查](./2026-10-23-publication-authority-route.md)。VPS 不承担重解析。准备失败保留匹配旧依赖的可用部分，撤权独立生效。不能以“索引尚未重建”继续读取已撤文档。

## 系统选型的实际缺口

| 源码现状 | 必要修正 |
| --- | --- |
| [Services](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/engine/src/linker_engine/app.py#L75-L87) 启动时加载 feed/contract，计算进程 version；[版本接口](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/engine/src/linker_engine/app.py#L149-L160) 还依赖 gate enforce | 同时报告稳定 Woo source revision 与已加载依赖版本；发布规则不能随 antiabuse off/observe 关闭。 |
| [sync-feed](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/engine/ops/sync-feed.py#L203-L240) 拒绝空 products；先换 feed 再换 contract，即使 contract 失败也会 restart | 合法空集必须承载“全部下架”；feed+contract+manifest整代验证后原子切换，禁止混代。 |
| [EngineVersion](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-tools/includes/Protection/EngineVersion.php#L38-L62) 已读 `/resource/version`，但 [Resources](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-tools/includes/Protection/Resources.php#L177-L203)、[NativeEngine](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-tools/includes/Protection/NativeEngine.php#L55-L88) 仅 enforce 读版本且旧 receipt 早返 | 复用已有 HTTP/版本机制；强制发布校验在所有模式执行，覆盖 cached receipts、PDF 与原生 ability 调用，不能仅修前端 proxy。 |
| [battery 选择](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/services/engine/src/linker_engine/residential.py#L865-L875) 找不到指定 battery_id 时回退第一款 | 旧请求指定已撤/未知型号时明确拒绝，不能悄悄换型号。 |
| [SolutionsRoute](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Account/SolutionsRoute.php#L107-L147) 已验证 items publish，但保存设计主要是 kind/input | 复用已有 publish 验证，扩展到服务端可信的整套依赖与输出快照，不能信任浏览器删减后的 items。 |
| [ReadSolution](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Abilities/ReadSolution.php#L216-L245) 读历史时重新调用引擎 | 本人读取历史改用当时快照，旧记录没有完整快照时明确有限信息，不用当前或草稿事实填补。重算必须成为独立新动作。 |
| [SavedSolutions::add_to_draft](https://github.com/AssassinFlash/de-linker/blob/5eabfffc70c01df3d2b76ec0823d64eaad39a8ef/plugins/linker-commerce/includes/Account/SavedSolutions.php#L240-L263) 逐项 add，部分成功即提示已加入 | 整套服务端预验和原子行为；任何条目失效就整套拒绝，不能静默剩余项成功。 |

## 推荐的最小跨服务合同与算法（待实现）

采用**全局 revision 发现变化、依赖集合决定可用性**。仅用一个全局版本不等就拒绝所有产品，会使一个正在准备的新品拖停已完整产品；只检查最终 selected 又会让失效候选参与排序、替代项和报告，仍不正确。

1. Woo 统一装配器返回 canonical 产品、公开许可、产品/资料内容修订与有效准备状态。engine 只对“当前有发布许可且已加载数据修订与 Woo 匹配”的交集生成候选。新增未准备对象不进入交集；撤下立即移出。候选全集、备选、排除项、文档引用都从同一个受限视图计算。
2. 服务请求携带服务端取得的当前许可 revision/依赖集合，不接受浏览器自报权威版本。engine 的 loaded revision 与实际对象来自同一不可变加载代；读取磁盘 manifest 不能为旧进程改标签。
3. 请求入口与最终输出、保存/加入/新报告动作提交前再验候选集合和实际证据依赖。计算期间候选许可改变则作废本次输出；无关新品尚未 ready 不改变有效候选集合，不必使其他产品 503。
4. 当前兼容合同可以先作为整体 hash 依赖：合同变更时暂停依赖该合同且尚未匹配的计算，胜过仓促发明逐条合同版本体系。屋顶、辐照、用电和工程 overlay 继续作为工程输入，但它们不能越过 Woo 产品/资料许可。
5. 结果携带服务器生成的 selection fingerprint（源依赖、候选/选中产品、数量、输入、证据版本），PDF 重算验证它；变化则要求重新选型，不能利用同输入自动生成另一套方案。cached PDF/result/receipt 都保留依赖证据并先验后复用。
6. 历史快照记录当时 title/model/BOM/关键结果与已生成报告，按 owner 读取；新的活动产品卡和文件链接仍从当前门产生。缺快照的旧数据不读取草稿产品补全，也不伪造历史。

上面选择比永久禁品牌、每个工具维护一张撤下表、等待定时全量重建更贴近当前统一 Woo feed、EngineVersion、持久作业和加载代机制。其复杂度主要是共用身份、准备确认和依赖集合，必须以真实夹具验证；本调查尚未跑性能或竞态测量。

## 实现责任与依赖

- Woo 基座/资料 gate/自动任务先建立统一合同与原URL保护，作为两类消费者的共同依赖。
- Genie 负责人实现检索全路径许可、逐块适用性、进程重开/loaded读回、历史上下文及附件规则；保持既有模型路由。
- 系统选型负责人实现整代feed发布、受限候选视图、mandatory pre/post checks、receipt/PDF重验与显式旧ID拒绝。
- 保存/历史/整套加入负责人复用 Woo 原生机制实现快照与原子动作，与 Genie/engine 共用同一依赖证据，避免各自推断。

每一层需 Spec/Standards、真实夹具、EN/DE 状态验证；客户界面有变化时按项目规定做 390/1440 视觉验收与文案对抗评审。至少覆盖：空全集、共用A/B手册、全库回退/邻块、相同SHA不同授权、同URL新字节、进程旧代、在途撤下、旧receipt、antiabuse三模式、旧battery_id、PDF重算、旧历史本人读取、新保存与整套原子加入。EcoFlow草稿和49路径410作为持续回归边界。

## 证据边界与未验证项

以上源码定位已核；推荐合同、自动 worker、所有输出/动作重验与快照改造均待实现。生产的 Genie/engine 当前加载版本、本轮产品状态与静态服务器规则未在本调查读回，不用源码替代生产验收。正式 Claude Opus 研究仍因未核到可用路由而受限；主会话应公开该限制并按业主明确分工继续。
