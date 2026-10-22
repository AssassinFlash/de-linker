# 统一规划工具重构对商务链的影响与同步修复范围

2026-10-22，Codex。本研究只读源码和现有夹具，定义工程BOM→Solution draft→询盘/Proforma→确认、团队通知和账户询盘查看的同步修复范围。没有改产品实现、运行写入/发信测试、访问浏览器或生产，也没有建票。本轮不承接Saved solutions、设计报告生成、入口或Genie本身的重构。

**结论：新规划内核不能只替换配置器页面和计算API。现有商务入口只接收SKU与数量，随后保存为Woo询盘；它没有新项目、revision、run或BOM行的身份合同。必须同时建立可信工程交接及其显示/保存合同，继续使用现有Woo原生询盘、接纳、去重和通知体系。** 不能把“计算成功”“草稿有同SKU”“询盘已保存”“通知已发出”当同一状态。

## 1. 研究基线、产品决定与证据等级

- 当期产品依据：[PRODUCT-STRUCTURE.md](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-system-route-548/docs/research/2026-10-22-roof-system-rebuild/PRODUCT-STRUCTURE.md)。一个统一项目工作台，屋顶/设备/储能/清单属于同一产品；WordPress/Woo继续负责商品与商务，用户可只完成一项成果。它不是实现或验收通过记录。
- 主源码引用固定到`origin/main=340a11a9cc3a33f687ca8092fcd6285cb9dcfc42`。研究工作树HEAD最初为`2c681c77e1433e2afcde8272250ef9d78c6640f4`；对本轮相关的Sender、Handler、确认、ContactSelection、Intake和通知变化使用`git show origin/main:...`核对，没有把工作树旧实现当当前主分支。以下GitHub链接均固定主基线。
- **已证代码事实**表示调用、字段或分支可从本版源码直接核对；**夹具已有断言**表示测试文件存在，未在本轮执行；**同步修复合同**是重构要求，尚未实现；**动态未验**包括当前部署、邮件送达、实际草稿会话、设备事实和视觉。
- 没有本轮商务浏览器运行证据，也不作线上现状宣称。此前屋顶/软件研究的浏览器旧基线不用于证明本版商务行为。

## 2. 当前实际调用、载荷与消费者

| 环节 | 已证调用与载荷/保存字段 | 当前消费者及重要含义 |
| --- | --- | --- |
| 住宅结果→待加入行 | `ResidentialPanel.draftLines()`从selected.lines仅取有product的行，映射为`{productId,quantity}`；无product行留在Installer's scope | [ResidentialPanel.tsx:229](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx#L229)、[Solution.tsx:193](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/solution/Solution.tsx#L193)。角色、单位、依据、附件依赖和未供货清单没有进入这次写入载荷 |
| 待加入行→Woo草稿 | GET `wc/store/v1/cart`取Nonce与按productId聚合数量；顺序POST`cart/add-item`，body只有id和缺少数量；最后GET并按数量读回 | [store.ts:40](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/api/store.ts#L40)。当前added证据是SKU数量，不是某run的完整BOM交接；已有足量便不再POST，部分失败可保留已写行 |
| 商业结果→询盘 | `CommercialResult`显示系统及lines，但主动作只是`href=result.inquiry` | [CommercialResult.tsx](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/commercial/CommercialResult.tsx)。此组件没有与住宅同样的整套加入动作，也不提交商业结果快照；不能把一个询盘链接称作完整方案交接 |
| 草稿/询盘页 | Form读取当前WC cart，逐行呈现商品名、数量、价格、删除链接；hidden有`linker_draft_hash`；数量可编辑 | [Form.php:116](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Form.php#L116)、[Form.php:179](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Form.php#L179)。页面没有工程项目/run分组和必需附件关系 |
| 发询盘 | admin-post Handler验证nonce、PublicGuard、Submission，payload含details/billing/draft hash，交给Business::run；Sender从Woo会话取商品/价格/客户，经native checkout create_order保存 | [Handler.php:43](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Handler.php#L43)、[Sender.php:51](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Sender.php#L51)。preflight检查商品存在和Woo库存，不读取工程run/模式/拓扑；本轮所核此路径未调用工程兼容检查 |
| 首次保存/提交后 | Sender写`_linker_locale`、`_linker_inquiry_source`、`_linker_inquiry_topic`和可选`_linker_genie_summary`，接Intake或Assessment，保存后转接收状态，正常request结束清空cart | [Sender.php:171](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Sender.php#L171)。没有当前规划project/revision/run/BOM hash或行分配字段 |
| 业务证据快照 | Assessment Snapshot取产品id、variation_id、当时行名/数量/total、当前商品SKU、客户和已授权对话上下文 | [Snapshot.php:24](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Assessment/Snapshot.php#L24)。这是业务判断快照，不是固定工程证据包；不能拿其products数组替代全部工程BOM |
| Proforma | 员工Issuer校验有商品、每行已有价格、银行资料，计算Woo税/金额，生成并存PDF、号码及签发时间；Document从订单行取名称/数量/金额、从当前商品取SKU | [Issuer.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Proforma/Issuer.php)、[Document.php:55](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Proforma/Document.php#L55)。元字段为`_linker_proforma_number/_issued/_file`。它是商务文件，当前不核工程BOM完整性 |
| 确认/邮件/账户 | 确认页看真实订单及通知hold；团队模板消费订单、Genie摘要和Woo详情；账户详情仍消费原生询盘，PI下载读已存文件，datasheet按当前商品读取 | [Checkout.php:114](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Checkout.php#L114)、[InquiryList.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Account/InquiryList.php)、[AccountTemplates.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Presentation/AccountTemplates.php)。现有阅读面没有规划版本/方案分配的显示合同 |

### 数量合并的真实语义

当前addAll的目标是“草稿至少已有方案数量”：已有1而方案要2就加1；已有5而方案要2则保留5并记added。同一方案再点不叠加数量。`store.test.ts:121,183,205`明确断言这一行为。[现有夹具](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/api/store.test.ts#L121)。本轮没有运行测试或把这段既有约定改判为已复现事故。

新项目模型不能沿用这条身份判断：例如A项目需要同SKU 2件、B项目需要3件，当前算法把总量补到3，无法表达两个项目分别分配的5件；方案从5改到2时，也不能用剩余5件宣称“新BOM完全一致”。这是源码可推出的**新合同失配**，不是本轮真实会话复现。必须先明确append某独立方案、更新同一handoff、保留手工商品等操作，再对分配账本与最终Woo总量一并读回。

## 3. 已合入的接纳、去重、通知及Contact链必须承接

1. **Business接纳和恢复已经是事实权威。** `BusinessRecord`在首次Woo保存时写`_linker_public_request/_input/_subject`，用request、输入指纹和主体恢复同一原生记录。新handoff_id应与这个逻辑请求建立稳定关联；超时先恢复回执，不另建订单，不因为规划run已完成而绕开Business。[BusinessRecord.php:16](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Protection/BusinessRecord.php#L16)。
2. **审查接纳不等于邮件已发。** Intake有`_linker_review_intake/_linker_review_lane`，可恢复已保存记录；NotificationHold和Assessment/Outbox管理延后、hold/release及发送。确认页已能显示“Inquiry saved for review”，或说明没有确认邮件。新工具返回必须承接原生记录和这些真实状态，不能用一个success布尔值盖过。[Intake.php:66](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Protection/Intake.php#L66)、[NotificationHold.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Mail/NotificationHold.php)、[NewInquiryEmail.php:55](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/Emails/NewInquiryEmail.php#L55)。
3. **完整BOM须适配现有边界。** Intake审查路径目前检查语义payload≤32768字节和cart行数≤20，超限明确保留输入/草稿并返回错误。这不是所有普通询盘路径的统一20行上限。新项目引用和精简业务快照须纳入原有接纳及大小校验；不得通过静默删附件、丢非SKU行或未经研究直接扩大阈值来宣称整套交接。安全机制由现有模块拥有，本研究不改其规则。[Intake.php:21](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Protection/Intake.php#L21)。
4. **Contact有自己的已落地上下文合同。** SelectionContext只接公开同源WP来源和选项白名单，服务端重新取标题；selection包含application/brand/phase/power、数值范围、q/sort，不含私有project/run。Contact Handler经Business::run保存`_linker_contact_selection`，走Sender.message且不消费cart。新私有工程项目不能塞进现有source或任意query参数假装已有支持，须增加受所有权验证的工程关联，沿现有Contact写入和Selection显示链传递。[SelectionContext.php:16](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Contact/SelectionContext.php#L16)、[Contact Handler.php:84](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Contact/Handler.php#L84)。
5. **后台继续是一份原生记录。** IntakeAdmin使用现有Woo列表显示held记录，而非第二份Inbox。新工具应给这份记录增加规划来源/版本和可授权查看的冻结依据；不能另开“工具询盘库”后再同步出第二封通知或第二个询盘。

以上只定义新工程关联要接入的点，没有接管或重新设计防护、Inbox、邮件预算、路由或hold/release实现。

## 4. 重构时必须同步修复的合同和落点

以下均为**待实现合同**，不是对现有版本的动态故障宣称。

| 同步范围 | 应落实的行为/数据 | 具体落点 |
| --- | --- | --- |
| 可信工程→商务交接 | 浏览器提交run/candidate引用及意图；服务端核主体/版本、读取不可变BOM、验证相关检查，再映射当前Woo事实。回执绑定handoff_id、project/revision/run、candidate及BOM hash | 新Planning↔Commerce Adapter；替代ResidentialPanel/StoreClient自行拼SKU写入；商业也使用同一入口 |
| 行身份与数量 | 工程行有bom_line_id、数量/单位、角色、供货方、必需关系/模式；商务SKU行保留对各handoff和BOM行的分配。相同SKU可汇总显示，但不能丢分配或把手工行冒充方案行；更新/重复/替换有明确语义 | Woo cart item data/session、Store API扩展/交接服务、cart→order line meta复制。具体字段命名由实现规格确定，本版并不存在 |
| 全部工程BOM与交易子集 | PV组件、现场材料、已有设备和安装商自备项保留工程数量与责任；Linker报价项映射SKU或明确项目报价行。没有公开组件分类，不为交接便利建套装SKU或公开组件分类；无product不能成为“无须跟踪”的理由 | 工程BOM→商业projection、草稿/询盘旁的工程范围片段、原生订单的冻结关联。采购/供货选择显式，与公开分类分开 |
| 必需附件与人工改动 | 删除、调量、换型号影响约束时，显示该方案已被改动并要求重核；不能只留“厂家已放行”徽章。缺附件/缺映射/停产不静默略过；可明确以待核询盘传给团队，不能标整套工程通过 | 交接验证器、草稿更新/删除/替换动作、Form预览、Sender提交前差异核对；使用新能力合同，不给旧引擎补丁 |
| 价格/库存/审批与版本 | 当前Woo商品、账号价格门和库存负责商务；工程历史不被最新价格重写。报价按当前商务事实，差异可见；不把“有货”当工程放行，不展示库存数，不因pending/restricted/rejected而关询盘 | CommerceState、PriceDisplay、StoreApiPrices、Woo native stock、审批三态及待审状态；保持现有purchasable/未定价记录行为 |
| 询盘冻结与恢复 | 原生order保存工程关联及足以还原报价范围的冻结快照；line meta保留SKU/版本及分配。项目后改不变旧询盘；同一请求超时重试恢复同order，购物草稿变化须客户重新确认 | Handler.payload/draft binding、Business请求语义、Sender/create_order hooks、Assessment Snapshot、BusinessRecord；复用接纳和隐私所有权，不复制大原始负荷资产到邮件 |
| Proforma | 员工看到工程商业范围差异、待核项和附件完整性；商务改量/换件不悄悄继承原工程通过。PI保留号码/有效期/税额等业务规则，引用其对应冻结工程范围；已签发PDF不因项目改动重算 | Proforma AdminBox/Issuer/Document、PI模板、原生订单行/报价快照。设计报告生成不在本任务；仅接其固定artifact引用 |
| 确认/通知/后台 | 显示真实原生询盘和接纳/审查/通知状态、工程关联；团队能看同一版本BOM/非SKU范围/待核项。继续既有Outbox及路由，不从规划worker再发一封。未验证收件地址的固定回执继续不带可控项目内容 | Checkout、LC inquiry/received、OrderAdmin/Assessment视图、NewInquiryEmail模板、SelectionView、Outbox/hold关联；只增加工程上下文 |
| 账户询盘详情/再次询盘 | 订单详情显示当时项目版本和工程范围，并与当前项目区别；订单权限与项目权限分别验证。Request again是新询盘意图，重新核当前商品/商务/工程差异，不能把旧工程批准直接复用 | AccountTemplates、InquiryList、DocumentDownload、Woo order-again适配；LC account/inquiry/summary/product-line片段。Saved solutions路线由另一研究负责 |

兼容证据不能仅复用旧`Products/Compatibility`的型号模式配对和三个verdict枚举：该类连接的是当前静态兼容数据，CheckCompatibility能力有单独调用入口，当前Sender.preflight不执行它。新交接应读取新内核的任务/模式/端口/附件评估及版本，保留unknown；**商务可以接收待核需求，工程已验证与询盘已接收是不同结论**。[Compatibility.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Products/Compatibility.php)、[CheckCompatibility.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Abilities/CheckCompatibility.php)。

### 必须继续成立的业务约束

- 访客可询盘，姓名/邮箱/留言与可选公司沿现有最小表单；无需强制账户、账单地址或VAT。审批管理价格可见性，不能替工程放行或询盘权限。现有CommerceState按Approval决定价格，PriceDisplay允许无可见价商品加入并将`_linker_price_reason`记入订单行。[CommerceState.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Gating/CommerceState.php)、[PriceDisplay.php:147](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Gating/PriceDisplay.php#L147)。
- Woo是商品/SKU、价格、库存和询盘权威；不建套装SKU，不引入支付/履约链。现有Issuer要求所有产品有价后才签PI；不把未报价/未公开价格行写成客户应付0元。
- 组件不在公开产品分类，出现在系统设计与项目报价；这是当期AGENTS产品约束，本轮没有以代码或夹具证明线上分类数据。新工程BOM应完整保留组件，不把“没有公开商品页”等同不可询价。
- EN/DE使用同一规范商品身份和工程run，呈现语言各自正确；Sender.line_language保留规范商品ID并写翻译名称。项目国家独立于界面语言，商务资料不得把德语界面改当德国项目。
- 访客订单认领沿AccountLink的订单key+相同邮箱校验；关联项目私有权限另核。不能凭邮箱或一个project_id暴露他人原始负荷/项目文件。[AccountLink.php](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/includes/Inquiry/AccountLink.php)。
- 网站表面继续由LC语义片段/WindPress承载；修复的是受影响信息和动作，不扩大为全商务页面改版。通知收件人与测试邮件仍按当期AGENTS执行，本研究未读取生产设置或发信。

## 5. 需要真正端到端验收的项目

以下是未来验收合同，不是本轮已通过。既有测试只能作为回归起点，不能拿“文件存在”充当执行证据。

| 场景 | 必须读回的证据 |
| --- | --- |
| 住宅/工商业同一handoff | 两类run都能提交同一可信合同；草稿/订单保留同一run、candidate、BOM hash及附件；无浏览器自报批准清单 |
| 重复、超时和多项目同SKU | 同handoff重试不重复加；A2+B3、手工行、更新同项目5→2的分配/总量一致；掉线后读回回执，不因同SKU已有足量就认新方案交接完成 |
| 必需附件失败/手工改动 | 一行失败保持真实partial/blocked状态；删附件或改数量后工程状态失效，询盘预览/团队记录保留具体差异；没有静默少行 |
| 国家/模式/证据变化 | 提交前输入改变、国家放行不足、硬件换型分别触发重核或明确待核询盘；不凭旧released徽章批准新图 |
| 组件及非SKU范围 | 无公开组件分类仍能在工程清单/项目报价需求中保留数量/单位/责任；PI交易子集与全部工程BOM差异可解释 |
| 访客及各审批状态 | 访客、待审、通过、限制、拒绝均走授权的询盘路径；价格API/页面/确认/账户/PI无泄漏、无伪0价；库存和RFQ产品按现行商务合同表现 |
| 接纳/审查/恢复/通知 | received、saved_review、pending、不确定结果、大小限制、hold/release分别读回原生状态；重复/恢复只关联一份Woo记录，不另造Inbox；规划成功不变成‘团队已收到邮件’ |
| Proforma及历史 | 员工报价补全后才签PI；双击/并发不重复签；后改项目、商品SKU或附件不改旧询盘工程依据及已存PDF；再次询盘重新核差异 |
| 权限和语言 | 访客原key认领、错邮箱/错主体拒绝、账号只见自己记录；EN/DE×1440/390真实走草稿、询盘预览、确认、账户详情及PI下载，工程国家保持不变 |
| 通知链 | Outbox内容断言核团队/客户路由、冻结工程关联及hold；测试按tester单地址与一次实发纪律；不能为此研究实发或向生产写入 |

可复用的现有夹具阅读点：[Store API数量/读回](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-tools/src/configurator/api/store.test.ts)、[OpenInquiryTest](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/tests/php/Integration/OpenInquiryTest.php)、[InquiryTest](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/tests/php/Integration/InquiryTest.php)、[ProformaTest](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/tests/php/Integration/ProformaTest.php)、[ProformaPriceGateTest](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/tests/php/Integration/ProformaPriceGateTest.php)、[ContactSelectionTest](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/tests/php/Integration/ContactSelectionTest.php)、[SafeIntakeTest](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/tests/php/Integration/SafeIntakeTest.php)、[NotificationHoldTest](https://github.com/AssassinFlash/de-linker/blob/340a11a9cc3a33f687ca8092fcd6285cb9dcfc42/plugins/linker-commerce/tests/php/Integration/NotificationHoldTest.php)。本轮全部未执行。

## 6. 可执行的修复边界

范围收口为：**新内核到Woo的可信handoff、完整BOM与商务行分配、原生询盘冻结关联及原有接纳状态衔接、PI/团队/确认/账户的对应读模型与再次询盘适配。** 应作为统一重构的一部分同时完成，不先给将被替换的旧住宅/商业引擎补线。

已有接纳、去重、隐私、通知路由、hold/release、原生账号/订单权限是依赖合同；只补工程关联所需适配，不重复建设。Saved solutions和设计报告生成由各自负责人承接，商务方只要求固定引用、权限及版本与此处相同。报告当前证明的是源码依赖与同步修复范围，尚无实现、线上或动态端到端验收结论。
