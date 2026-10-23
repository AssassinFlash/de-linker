# EcoFlow 停止公开展示：影响与最小可逆路线

记录时间：2026-10-23 18:40（Asia/Shanghai）。

研究票：[核清 EcoFlow 下架对 Genie、技术资料与系统选型工具的完整影响](https://github.com/AssassinFlash/de-linker/issues/608)。所属地图：[地图：EcoFlow 停止公开展示与技术资料下架](https://github.com/AssassinFlash/de-linker/issues/607)。

## 结论与边界

只把商品设为草稿不足以完成本次要求。它会挡住商品查询和当前公开资料库里的商品条目，但独立知识库、已有对话文档、公开兼容合同、引擎静态 feed 和旧工具结果各自有生命周期，必须一起处理。

**紧急执行优先级补充：**业主随后要求立即先将全部 EcoFlow 商品设为草稿，明确将“草稿仍可读技术资料”作为后续修复的设计缺陷。主会话先完成必要完整增量备份、执行时待改发布记录的 draft 更新及发布数为零的读回；知识、技术资料和系统选型工具缺陷之后处理。本文完整退出路线用于后续修复交接，不阻塞本次紧急商品状态动作，也不把该动作等同于全链资料已撤下。执行结果以主会话的生产读回记录为准。

业主已明确：所有 EcoFlow 商品下架为草稿；停止展示包括本网站技术资料；solution 指系统选型工具 Solution Configurator / Lösungskonfigurator。原始产品、技术文件、兼容事实与历史记录保留。私有历史方案/询盘/已生成报告是否继续允许客户查看，以及客户自己上传手册/铭牌是否继续答疑，仍待业主决定。不能把本网站资料下架扩张为禁止一切用户上传内容。

## 证据口径

源码固定为 [8f3d8e3921dc0d71fb11d76d0576988736ca23a3](https://github.com/AssassinFlash/de-linker/tree/8f3d8e3921dc0d71fb11d76d0576988736ca23a3)，即本轮核查时的 origin/main。本文链接均固定到此提交，避免后续 main 变化改变证据。后台研究代理只读源码及已有测试；下述生产观测由同会话主代理只读取得。本研究代理没有生产变更、真实发信、模型调用或更改后实走；生产观测为本次紧急商品状态动作之前的快照；已有测试断言属于证据，本轮未重新运行测试。

### 当前生产只读观测

| 对象 | 本轮读回 | 含义与限制 |
| --- | --- | --- |
| WooCommerce | 11.2.0；EcoFlow 发布 EN 21、DE 21，草稿 EN 13、DE 13 | 按此快照待改发布记录 42；不能当作执行时锁定清单，执行前重新读回 |
| Genie 当前 SQLite | 384 份文档；48 份含 EcoFlow 标记；品牌匹配 chunks 4,182 | 这些是索引元数据匹配计数，不是完整文件撤下清单 |
| WP `_linker_documents` | JSON 解析后取得 12 个独立 URL | 仅此字段的当前枚举，不能推断全部技术资料只有 12 份 |
| 引擎 `state/feed.json` | 106 个产品，其中 21 个 EcoFlow | Woo 改状态不会直接改变这份进程使用的数据 |
| 已知托管 PDF | [EcoFlow OCEAN 2 P3 S2 user manual](https://de-linker.com/wp-content/uploads/2026/09/ecoflow-ocean2-p3-s2-user-manual-v1-1.pdf) 的 HEAD 为 200、`application/pdf` | 说明当前原文件 URL 公开可取；未对全部文件逐一验证 |
| 在用服务源码 | Genie knowledge/retrieval、engine residential/app 的 SHA 与固定源码一致；已核当前进程 cwd、current 指向、服务 active | 证明调查的四个拥有源在用；不等于已验证每个交互结果 |
| 已加载 WP 类 | DocumentLibrary、EngineeringFeed、SolutionsRoute、PriceDisplay、SavedSolutions 文件 SHA 与固定源码一致 | 生产类文件与所读源码对齐；没有做下架后的生产行为验证 |

以下影响由这些生产观测和固定源码共同支持；未发生下架，故不存在“下架后已验收”的结论。

## 影响矩阵

| 表面或链路 | 商品改草稿后会发生什么 | 必须补的动作 |
| --- | --- | --- |
| Genie 商品查找与详情 | search-products 只取 publish；get-product 对非 publish 返回空记录，无法当作真实商品。词表由 Store API 读取，内存最长保留 600 秒 | 清词表/等待实际过期并读回，验证新商品卡和关联操作已退出。[商品搜索](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Abilities/SearchProducts.php#L265-L287)、[详情门](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Abilities/GetProduct.php#L123-L147)、[词表缓存](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/src/linker_genie/storeapi.py#L25-L79) |
| 网站 FAQ / Downloads | 只遍历 publish 商品；独有文档和 FAQ 随之移出。共享文件若还由其他发布商品引用，仍会显示 | 核对共享文件及页面缓存；不能一概按文件名包含品牌就处理。[资料库查询与去重](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Products/DocumentLibrary.php#L83-L142)、[FAQ](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Products/DocumentLibrary.php#L167-L185) |
| Genie 知识与技术回答 | 不自动排除。SQLite 没有商品发布状态；按型号/产品缩窄失败后仍可回退全库，已有 EcoFlow 技术块仍可成为回答证据 | 从公共检索排除本次撤下资料，并使未来构建遵守同一范围。[索引表](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/index/store.py#L25-L49)、[检索过滤与回退](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/src/linker_genie/retrieval.py#L207-L241)、[搜索](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/src/linker_genie/retrieval.py#L362-L392) |
| Genie 新技术文档链接 | 知识命中进入本轮 facts 后，hydrate 自动生成原 PDF 的页码链接；商品不可见不阻止此路径 | 文档可见性必须在进入模型证据与输出前成立。[搜索结果](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/src/linker_genie/knowledge.py#L67-L110)、[引用补齐](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/src/linker_genie/hydrate.py#L142-L213) |
| Genie 旧对话 | 恢复时会刷新价格和文档标签，保留旧文字与原文档 URL；文档元数据不可读时仍保留链接 | 按业主确定的历史展示边界过滤可见副本，不删除底层历史。[恢复逻辑](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/src/genie/api/historyArtifacts.ts#L100-L113)、[返回保留 blocks](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/src/genie/api/historyArtifacts.ts#L185-L199)、[直接输出链接](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/src/genie/components/DocumentLink.tsx#L12-L23) |
| 托管 PDF 原网址 | 商品状态没有触及文件服务；已知原网址当前仍 200 | 可逆限制本次明确范围的文件公开访问，核对所有别名与缓存；原件保留。当前示例见生产观测 |
| 公开 engineering-feed | products 有 publish 门；compatibility 完整原样加入，不随 products 过滤，EcoFlow 型号与 PDF 引用仍可能公开 | 在公开输出层同步收窄兼容资料；内部完整合同保留。[完整合同加入](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Products/EngineeringFeed.php#L60-L85)、[商品门](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Products/EngineeringFeed.php#L90-L99) |
| 系统选型工具新结果 | 使用当前引擎 feed；刷新后会在剩余候选中选，可能选其他品牌；无合格候选返回 no_candidate。没有已核定的 EcoFlow 专用处理；Trina 参考组件与本次无关 | 用完整产品同步刷新并验证进程实际在用 feed，不能只确认磁盘新文件。[候选与选择](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/engine/src/linker_engine/residential.py#L807-L875)、[无解输出](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/engine/src/linker_engine/residential.py#L994-L1005) |
| 失效选择与已打开旧结果 | 已移除 inverter_id 会报 invalid_input（HTTP 422）；失效 battery_id 回退当前首电池候选。旧 React result 保留型号与文档；保存时 publish 门拒绝（400） | 明确失效结果的提示与刷新规则，防止屏幕和新计算混用。[失效 ID](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/engine/src/linker_engine/residential.py#L820-L875)、[旧结果显示](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/src/configurator/solution/Solution.tsx#L254-L320)、[保存门](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Account/SolutionsRoute.php#L107-L119) |
| 旧结果的即时报告下载 | PDF 端点用当前 feed 重算；可能下载另一套方案而屏幕保持旧结果，或因失效 inverter_id 返回 422。无 selected 时没有对应 BOM | 报告必须与客户确认的当前结果一致；失效时先重新计算并展示，不静默换方案。[PDF 重算](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/engine/src/linker_engine/app.py#L222-L233)、[报告选择分支](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/engine/src/linker_engine/report.py#L272-L343) |
| 私有保存方案与历史 PDF | 保存记录与 PDF 不随下架自动隐藏，账号仍可呈现历史型号；历史报告按权限读取原文件 | 待业主确定客户查看边界，再加显示/下载门，内部原始记录保留。[真实账号呈现](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Presentation/AccountTemplates.php#L559-L587)、[历史 PDF](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-commerce/includes/Account/DocumentDownload.php#L108-L153) |
| 全部加入 Lösungsentwurf | 客户端逐行加入，允许部分成功；不能视为一次事务或全部可加 | 验证混合品牌旧结果的逐行失败提示，避免只有一部分被带入却让客户误认为整套已加入。[逐行逻辑](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/src/configurator/api/store.ts#L113-L139)、[批量结果](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/src/configurator/api/store.ts#L172-L189) |

### 两条容易误判的证据

1. 直接重建现有知识库不会解决下架：inventory 从全部 PDF 媒体取文件，产品查询为 `status:any`；build 对所有有 model 的产品和全部文档构建，没有发布状态过滤。[媒体/产品清单](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/index/inventory.py#L354-L377)、[构建循环](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/index/build.py#L233-L268)。已有测试明确断言未知产品或空缩窄时查全库，故仅移除 product mapping 也不够。[检索测试](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/tests/test_retrieval.py#L177-L200)。
2. 旧对话的 PDF 保留是现有测试要求：当产品 authority 不可用，断言 URL 继续存在；知识块式旧引用无需查商品。[历史测试](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/src/genie/api/historyArtifacts.test.ts#L142-L220)。因此新查询通过发布门不代表历史文档已撤下。

## 最小可逆执行序列

本节为完整退出的后续实施方案，本研究代理没有执行；紧急先行的备份、商品改草稿和状态读回由主会话按业主最新指令处理。

1. **锁定范围与恢复点。**重新读回英德全部 EcoFlow 商品状态；保存本次待变更的发布记录原状态。对齐 WP 文档字段、旧文档字段、附件、当前索引的 SHA/URL、全部公开兼容引用，建立单份撤下清单，列明别名和跨品牌共享文件。按项目备份/保留规则建立并验证所需恢复点；不删除原文件或历史。
2. **准备一致退出。**在评审环境完成公开文档可见性、知识检索/构建排除、公开兼容输出收窄和旧结果失效行为。只清商品状态会留下资料；仅删当前索引会在下次构建回流。历史私有内容与客户上传内容依据业主下一项决定处理，避免无根据扩大范围。
3. **执行商品下架与数据刷新。**通过正常 WordPress 更新机制把执行时仍发布的英德记录改 draft，保留其他字段；立即触发完整引擎产品同步，确认 EcoFlow 从实际在用候选消失。替换公共知识索引并启用构建排除；对撤下文件设置可恢复的公开访问限制，清对应缓存。若不能在同一窗口完成，使用明确限时的受影响入口暂停措施，直到退出链验收完成。
4. **让实际进程生效。**先核运行版本、磁盘版本、启动定义与数据兼容，再重载/重启必要服务，读回当前监听/站点/实际索引和 feed。知识 `default_index` 连接只初始化一次；发布脚本仅 rsync 和切 current 链接，并不重开运行中连接。[一次打开](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/src/linker_genie/retrieval.py#L450-L460)、[发布](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/ops/publish_index.py#L46-L72)、[切换](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/ops/index_release.py#L96-L109)。正常保存虽会通知 Genie 清页面/草稿缓存，但不是知识库/词表失效机制。[通知 hook](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/plugins/linker-tools/includes/Genie/PageCache.php#L131-L167)、[失效端点](https://github.com/AssassinFlash/de-linker/blob/8f3d8e3921dc0d71fb11d76d0576988736ca23a3/services/genie/src/linker_genie/app.py#L365-L382)。
5. **验收并收尾。**逐层读回下述结果；记录真实改动、回滚指令和未通过项，完成滚动保留清理，通知协作会话恢复测试。

回滚按同一清单执行：只恢复本次由 publish 改成 draft 的记录；原来就是 draft 的记录继续为 draft。恢复公开文件策略、公共兼容视图、上一版知识索引及候选数据，确保进程实际读入对应版本。恢复原始档案不等于自动恢复公开展示，二者分别留记录。

## 后续实施验收

- 数据：执行时 EcoFlow 发布数为零；本次清单与变更数逐条匹配，EN/DE 同步；非 EcoFlow 商品与库存/价格未被批量改变。文档清单与实际来源集合对账，所有共享文件和别名都有结论。
- 匿名公开面：商品页/列表/搜索、FAQ 与 Downloads、公开商品 API、engineering-feed 的 products 和 compatibility、撤下 PDF 原 URL及附件发现入口均覆盖；对每个应撤下文件实际验证响应及缓存，不用删除媒体原件代替访问控制。
- Genie：EN/DE 新会话的品牌问法、具体型号、技术参数、手册和兼容性查询，不能返回被撤下托管资料或新推荐卡。覆盖知识全库回退、旧对话重开/继续追问、词表更新和实际进程索引版本；与业主确认的私有历史/用户上传策略一致。应在获准测试环境实走，不用源码推断冒充已通过。
- 系统选型工具：有替代候选、无候选、旧 inverter_id、旧 battery_id、旧打开结果保存/加全部/下载报告、账号保存方案及既有 PDF。报告必须与屏幕确认的结果同一套；无解和失效状态不能静默换型。EN/DE、390/1440 逐状态截图，运行改动所在层真实夹具与 Spec/Standards 全量双评审。
- 恢复：演练按清单恢复，确认原来 draft 的产品未误上架；核知识和 feed 在用版本，不仅核文件链接。按本地保留规则回收可重建运行副本，仅保留必要恢复点和证据。

已经下载到客户本机的文件无法撤回；已打开标签页里加载的旧内容不会因服务器商品状态变动自动消失。可控制的是后续读取、重开与操作，验收必须明确这个时点。

## 未验证与待决定

本研究代理未实施 draft；主会话紧急改状态的实际结果以其票据读回为准。本研究未重建/发布排除后的索引、未刷新生产 feed、未限制 PDF 访问、未调用模型、未实走下架后的 EN/DE 浏览器链，也未测试回滚。12 个 WP 文档 URL、48 个索引标记文档和 4,182 个品牌匹配 chunks 的集合尚未完整对账；不能据此宣布资料范围已全部核清。

待业主决定仅有业务边界：私有历史方案/询盘/已生成报告能否继续供本人查看；用户自己上传手册或铭牌能否继续答疑。其余公共检索、公开技术资料、产品候选的一致撤下属于已确定范围，应由实施补齐。
