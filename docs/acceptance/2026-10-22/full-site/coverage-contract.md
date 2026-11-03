# 全站覆盖合同与待验边界

本文件是待执行的清单合同，不是运行结果。本文件只定义待验合同；其存在不证明已执行验收、修复或发布。基础清单为352个独立URL/704个视口条目；状态清单由初始784行扩到1044行（22族、261种状态的EN/DE×1440/390组合），初建时全部pending。当前状态与已验范围以JSON为准；31个模板的候选关联不写入rendered_routes。完整性必须持续由真实入口、当前产品能力和业主裁定复核，不能从这些数字推导全站完整。

## 记录形状与判定

每个实际case至少记录：contract_id、matrix_keys、entry_id/surface、environment、release/build与内容或模板指纹、requested_url、final_url、resolved_locale、viewport/输入模式、普通客户角色与审批状态、fixture引用、触发步骤、expected_result、actual_result、截图/原始读回文件、render/interaction/manual_visual结论。私有key/token/nonce只用脱敏fixture引用，不把秘密放入公开证据。

一条case可关联多个矩阵行。按 AGENTS.md 第0.1节，入口、语言、视口、身份、输入、相关实现及运行条件未变时，直接复用有效结果；无关release、合并、换会话或换报告不使结果失效。记录证据实际环境与版本，以及未变的相关范围，不将本地结果冒充线上结果。需多个入口或文档的行，所有required_contexts均完成才能关闭；部分完成保留pending并列出已有证据。新增case不得清空他人已记录的结果或证据。

`required_fixture_contracts` 是本行适用条款的章节关联，不把该章节或整个 family 的所有链路都设成本行的关闭前置。用本行 `required_contexts` 明确实际 surface、入口、身份和该动作的完成条件；没有列出时也应按本状态对应条款解释，不能推导为整章重复执行。`consumer-readback` 验证本动作的消费者：数量保存读回、删除结果、撤销恢复分别成立。普通无项目备注的草稿 empty／quantity／Remove／Undo 不等待完整项目备注链；项目备注的48行及跨账户、报告、询盘、通知的整体门仍各自保留。菜单打开／关闭状态不等待搜索分页，搜索结果状态仍须验证自己的实际结果和分页。

Family／全链路完成取全部适用状态和独有 `required_contexts` 的并集。局部状态通过不能代替未完成的注册、审批、权限、原生 received、隔离 Outbox、项目备注或文件消费者；不删除这些状态、不批量改 PASS，也不将未实现能力改为不适用。每行直接关联既有文件及具体 case／JSON 路径，说明实际环境与范围，已完成的无关动作不再次加入本行验证。

`pending`表示尚未证明。`not-applicable`必须写原因及依据：例如实际响应式分支没有该控件，或有裁定的入口已关闭并实测重定向。未实现、当前数据没有现成样本、未申请测试账号、测试失败都不构成不适用。合成数据只能在隔离本地/评审环境建立，注明与生产的边界。

<a id="route-fixtures"></a>
## route-fixtures：动态路径与端点

建立可重放的最小fixture manifest，按当前Woo endpoint API和已启用rewrite生成EN/DE真实地址，不把内部query key、旧slug或候选路径当成已验证URL。每组覆盖1440/390；账号/订单对象采用隔离fixture，不提交真实询盘或邮件。

| 路径组 | 必须实例化的变体与结果 |
|---|---|
| 登录/注册/重置密码 | 直接进入注册、已登录回退、重置有效/过期/错误key、成功与验证失败；原输入、错误位置与返回路径保留。 |
| 账号 | Overview、Inquiries/分页、具体Inquiry、Saved solutions、Documents、Company、Account details、Logout；直接URL、刷新、返回、缺失/其他owner对象。当前菜单与端点是权威。 |
| 询盘确认 | 通过原生order-received端点生成的确认URL、正确/缺失/错误key、对应语言；Contact thank-you页面不能代替原生询盘确认。 |
| 搜索/分页 | 实际query、结果为空、第二页、越界页、过滤/排序组合后的下一页；记录final_url和实际结果集合。 |
| 404/旧地址 | 一个确认未占用的EN/DE路径，当前404模板和返回动作；实际启用的旧slug/endpoint/pagination别名记录跳转链与正确语言。 |
| 其他公开归档 | 对已启用或有真实入口的author/date/tag/其他公开taxonomy作发现检查。有真实HTML入口才纳入；关闭/重定向需证据，不凭WordPress默认能力臆造页面。 |

状态矩阵中的dynamic-routes是发现与执行合同；没有fixture URL和消费者结果不能关闭。

<a id="library"></a>
## library：FAQ与文档库

基线路径为EN页面932、DE页面6863。分别检查FAQ/Documents tab与键盘状态、搜索建议listbox、上下键/Enter/Esc、命中与空结果、clear、结果计数、分类rail/手机chips、切tab/语言后的状态，以及从实际条目打开原文件。现有blog搜索、PDP文档tab或页面render不能替代此族。

<a id="taxonomy-context"></a>
## taxonomy-context：语言未知与别名

inventory-baseline中39条term记录的lang=false，去掉5组同URL品牌别名后为34个独立URL。lang=false是未决归属，不是英语已通过或无需德语。对每个URL记录实际queried taxonomy/term、resolved_locale、语言切换目标、当前产品集合/计数、筛选与分页。若EN/DE共用同一URL，需用明确的实际语言请求上下文证明两种呈现；若跳到别的路径则记录最终路径，不猜造`/de/`地址。

5组别名是Chint、EcoFlow、GoodWe、Pylontech、SAJ，各有product_brand与pa_brand记录。相同URL可共享基础页面证据，但两条taxonomy记录的count并不总相同；必须确认当前resolver及预期产品集合，不能把另一个term的count当成画面应显示的数量。完整待核URL见下方清单。

<a id="marketing-entries"></a>
## marketing-entries：每个真实入口到Genie消费者

按`genie-entry-inventory/inventory.md`的实际入口登记entry_id，不笼统拦截所有`/genie/`链接。受影响的Residential EN749/DE6923、Commercial EN792/DE6921与Installer EN826/DE6869各有响应式分支：住宅/商业输入及Installer手机进入当前Genie，Installer desktop的Plan进入当前语言Configurator。普通Genie导航、首页与产品当前控制器是回归对照。

每个实际输入入口证明完整原问题成为一条用户消息、仅一次turn；建议胶囊先prefill且可编辑。冷/暖加载、失败/重试、同tick重复操作、IME/Shift+Enter、已有未发draft/忙碌turn都要有明确归属。附件/语音用现有机制证明文本和已接受文件一起到达；取消、拒绝、关闭、刷新需保留文本并明确需要重选的文件。只证明导航URL、event spy、控件enabled或DOM出现不算消费完成。

<a id="brief-consumers"></a>
## brief-consumers：项目备注与Plan连续性

本族来自`genie-entry-inventory/repair-design.md`的新设计；当前源码、持久化、部署能力均未由本合同证明，保持pending，不以原型内存状态充当实现证据。

- 原始note逐字保留；不从型号/温度等任意数字猜五个计算字段。当前defaults、carried values、confirmed、not entered分开。备注不是严格ResidentialInput的一部分；同一计算输入的数值结果不因备注改变。
- Source stage/readback→Configurator显式可见note→refresh/back/语言切换→result→save/guest claim/owner账户→screen/PDF→真实Woo draft→inquiry/received order，每个消费者验证相同ID/revision及完整文本。报告不截断；保存/报告复用随revision变化失效。
- 现有浏览器记录不是权限。跨用户、logout、User Switching、guest claim失败、过期scope不得渲染旧客户缓存。新scope/存储/claim机制须实际fixture，不把设计中的API视为已存在。
- 产品写入与note写入部分失败有明确部分状态；只重试note不能重复增加数量。不同项目并存；同项目更新比较expected revision，不让迟到请求覆盖新版。
- 询盘提交比较用户审阅的selected IDs/revisions，server scope/owner仍为权威；revision漂移在建单前拒绝并保留输入。成功只消费该次已包含的原revision，失败保留。非空selected note-only有效；全部排除且无产品/独立message时沿用空请求恢复。
- 客户message、project notes与Genie summary分开。普通原生PDP/draft/direct询盘不能自动带入无关历史Genie问题；只有显式、当前scope的handoff/reviewed inclusion可预填，未触碰/已有/主动清空/failed-POST草稿的优先级必须证明。

<a id="search-pagination"></a>
## search-pagination：查询状态和语言

覆盖实际Header搜索、公共搜索模板、产品列表、博客、FAQ/Documents各自存在的实现。每族至少一组有结果/无结果、第二页/末页/越界、筛选或排序后翻页与清除；不把库内搜索当全站搜索。切语言后核查query、page、filters、hash及endpoint的保留/重置是否符合各入口合同，不能只验站点仍为200。默认页的352URL基线不包含这些查询变体。

<a id="permissions"></a>
## permissions：角色、审批与文件

普通customer的guest/pending/restricted/approved分别验证；rejected验证登录拒绝、原因/恢复提示及旧session撤销，不存在rejected overview。Staff是独立角色，不能替代approved customer；用户自己的对象、其他客户对象、访客和无效对象须分开。

历史卡片恢复在workspace/dock/homepage Hero以及切会话/reload/发送前/重试等实际入口，重读当前客户价格authority；旧approved金额不能回退。接口失败或权限字段不完整时清旧价，原对话正文不被翻译或回写。附带文档UI用当前语言，原PDF语言、标题事实、URL与页码不改。

普通自主输入的失败缓存也须独立验证，不能只使用营销entry夹具。由实际文字、语音或image/PDF prepare生成失败记录，覆盖A换B、退出为新guest、200空历史和403历史、同页身份变化、reload与跨surface恢复；回显文字/文件名和最终运输均须核验归属。初始scope等待、暂时不可用、准备附件中、新输入出现及恢复完成的每个异步出口，都不得覆盖另一个owner或让旧稿失去可达的恢复路径。未带可证明owner的旧v1记录不得自动绑给当前身份；未知旧内容的隔离、保留及迁移须单独评审。具体已确认的本地消费者缺陷与修复前提见genie-failure-isolation-discovery.md，诊断通过不代表风险已修复。

私有文件验证实际响应与可读内容：当前DocumentDownload合同为访客/非owner 403，pending/restricted owner的Proforma 404且无PDF bytes，approved owner与staff的授权路径另验；缺失文件也404。不从“有下载按钮”推断权限正确。

<a id="files-print"></a>
## files-print：真实文件与打印

由实际产品/库条目构造去重文件manifest（URL、文档类型、原语言、标题与引用页），覆盖已链接的datasheet/manual/certificate等实际类型，不只点一个示例PDF。打开消费者核实状态、内容类型、非空有效文件、正确标题/原语言、页锚点和可读正文。已有文件URL若失效，记录事实与本轮修复，不以源码meta存在视为成功。

四份实际法律文档（Imprint、Privacy、Terms of Sale、Refund & Returns）分别核native print preview/PDF的完整正文、表格、首末页、页边界、UI控件隐藏；每种语言都检查，手机触发入口另验。Privacy还保留正文hash、反斜杠、原生重复保存与最终部署读回门。Design report/Proforma用真实生成/下载后的文件验证完整文本与权限；logo、长note及多页内容只在相应真实能力存在或本轮明确新设计要求时建立本地fixture。

<a id="overlay-responsive"></a>
## overlay-responsive：响应式与浮层

1440/390为逐页必需视口。Desktop/mobile menu、phone table scroll、touch gestures等组合先确认实际控件与输入模式；不在该分支的组合保留适用性pending，取得依据后才可标not-applicable。对已发现的320px长德语与实际响应式断点，用共享模板代表页补查，不机械把352页乘所有宽度。

实际search/menu/cookie/Genie/contact/upload/report浮层按存在的入口检查：打开/关闭/外部点击/Esc、焦点移入与返回、背景滚动/锁定、可达按钮、可见区域和滚动到底。对fixed/sticky手机输入和composer补窄可视区/键盘态，桌面Tab遍历不能代替；多浮层只验用户可实际同时打开的组合。静态“无overflow”或“无遮挡”不证明上述状态。

<a id="template-binding"></a>
## template-binding：31个模板的运行归属

模板route_candidates只提供待查路径，不是使用证明。由真实请求记录LC模板/partial ID或等价确定证据、当前assignment/slug、effective locale与state。六个按slug嵌入的Genie/Configurator/FAQ模板、Compare模板不能因assignment为空视为未用；metadata lang=en不能覆盖显式DE用途。产品归档须检查category/brand/series/属性等实际入口是否用了预期模板。

Header/Footer在其实际页面类型和语言中验证，至少长/短页面与交互状态；一份首页截图不能证明全部模板承载。Global JavaScript必须证明代码执行及实际消费者行为，不能用“已登记”或空画面关闭。模板只在所需真实上下文均完成后标pass，仍保持实际rendered_routes与applicable_states证据字段。

<a id="consumer-readback"></a>
## consumer-readback：链路完成条件

产品加入→真实Woo draft及数量；配置器整套加入→每行/数量；保存→owner saved-solutions列表与报告；文件按钮→实际文件；营销输入→Genie真实消息；询盘→received记录/确认与隔离Outbox队列。不能把mocked toast或card success等同这些消费者结果。UI错误/处理中/取消/失败/恢复分别保留输入并验证可继续操作。通知文案可在隔离环境render/readback；真实邮件仍遵守项目tester纪律，本合同不授权发生产邮件。

<a id="inquiry-native-entry"></a>
## inquiry-native-entry：真实原生入口

从PDP实际Add链接进入，不手动跳canonical掩盖命令query。验证Add一次、更新2、remove/Undo仍2、reload仍2、qty0删除，左侧未发送字段/同意不丢；更新pending时Send disabled且程序submit被阻止，完成后恢复。直接从draft继续、空draft留言、失败验证、正确语言确认也分别记录。原生update/delete/undo notice与print/file结果各有消费者，不能用一个已正则化URL的case替代。

<a id="provenance"></a>
## provenance：证据有效范围

基础render、interaction、manual visual独立判定。媒体等待重试通过只证明那次就绪，模型回复/截图文件/无overflow不证明完整视觉。逐页长内容应按实际滚动覆盖首中末与lazy媒体，细看排版/留白/截断/对比/图标/状态与点击热区。

证据如实保留原release/local/fixture边界。只有相关代码、内容、数据、运行条件变化，新失败出现，或原证据明确无效时，重测受影响部分；不因存在较新release而重新全站采样。共享模板先验共同机制，各页仍须补足首次独有内容、交互与例外。完整目标有未覆盖或未解决项时保持进行中。计数以JSON实时汇总，人工findings中的旧计数不是权威；历史失败和原始产物不改写。

## 待核taxonomy URL清单

以下34个共享品牌/系列归档根路径（对应39条 `lang=false` term记录、EN/DE共68个物理URL及5对同canonical品牌别名）已于 2026-10-31 完成生产匿名HTTP与Chrome 1440/390共享模板/筛选/分页/切语核实（证据见 `docs/acceptance/2026-10-31/548/INDEX.md` 第1229–1242行）。

| 基线URL | term记录（taxonomy:id，原始count） | 当前语言与结果验证 |
|---|---|---|
| [/brand/chint/](https://de-linker.com/brand/chint/) | product_brand:205，count=2；pa_brand:208，count=2 | 已核（EN `/brand/chint/` 200 `en-US` 1卡 / DE `/de/brand/chint/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/brand/ecoflow/](https://de-linker.com/brand/ecoflow/) | pa_brand:45，count=42；product_brand:194，count=38 | 已核（EN `/brand/ecoflow/` 200 `en-US` 0卡 / DE `/de/brand/ecoflow/` 200 `de-DE` 0卡，共享归档模板与语言路由一致） |
| [/brand/goodwe/](https://de-linker.com/brand/goodwe/) | pa_brand:70，count=98；product_brand:191，count=48 | 已核（EN `/brand/goodwe/` 200 `en-US` 24卡 / DE `/de/brand/goodwe/` 200 `de-DE` 24卡，共享归档模板与语言路由一致） |
| [/brand/pylontech/](https://de-linker.com/brand/pylontech/) | product_brand:193，count=2；pa_brand:78，count=2 | 已核（EN `/brand/pylontech/` 200 `en-US` 1卡 / DE `/de/brand/pylontech/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/brand/saj/](https://de-linker.com/brand/saj/) | product_brand:192，count=68；pa_brand:94，count=68 | 已核（EN `/brand/saj/` 200 `en-US` 13卡 / DE `/de/brand/saj/` 200 `de-DE` 13卡，共享归档模板与语言路由一致） |
| [/series/chint/](https://de-linker.com/series/chint/) | pa_series:507，count=2 | 已核（EN `/series/chint/` 200 `en-US` 1卡 / DE `/de/series/chint/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/ecoflow-battery-installation-accessories/](https://de-linker.com/series/ecoflow-battery-installation-accessories/) | pa_series:519，count=2 | 已核（EN `/series/ecoflow-battery-installation-accessories/` 200 `en-US` 0卡 / DE `/de/series/ecoflow-battery-installation-accessories/` 200 `de-DE` 0卡，共享归档模板与语言路由一致） |
| [/series/ecoflow-ocean-2-battery/](https://de-linker.com/series/ecoflow-ocean-2-battery/) | pa_series:518，count=2 | 已核（EN `/series/ecoflow-ocean-2-battery/` 200 `en-US` 0卡 / DE `/de/series/ecoflow-ocean-2-battery/` 200 `de-DE` 0卡，共享归档模板与语言路由一致） |
| [/series/ecoflow-ocean2-hd-p3-s2/](https://de-linker.com/series/ecoflow-ocean2-hd-p3-s2/) | pa_series:511，count=14 | 已核（EN `/series/ecoflow-ocean2-hd-p3-s2/` 200 `en-US` 0卡 / DE `/de/series/ecoflow-ocean2-hd-p3-s2/` 200 `de-DE` 0卡，共享归档模板与语言路由一致） |
| [/series/ecoflow-ocean2-lfp-battery-s2/](https://de-linker.com/series/ecoflow-ocean2-lfp-battery-s2/) | pa_series:516，count=4 | 已核（EN `/series/ecoflow-ocean2-lfp-battery-s2/` 200 `en-US` 0卡 / DE `/de/series/ecoflow-ocean2-lfp-battery-s2/` 200 `de-DE` 0卡，共享归档模板与语言路由一致） |
| [/series/ecoflow-ocean2-plus-hd-p1-s2/](https://de-linker.com/series/ecoflow-ocean2-plus-hd-p1-s2/) | pa_series:515，count=20 | 已核（EN `/series/ecoflow-ocean2-plus-hd-p1-s2/` 200 `en-US` 0卡 / DE `/de/series/ecoflow-ocean2-plus-hd-p1-s2/` 200 `de-DE` 0卡，共享归档模板与语言路由一致） |
| [/series/goodwe-bat-c/](https://de-linker.com/series/goodwe-bat-c/) | pa_series:502，count=10 | 已核（EN `/series/goodwe-bat-c/` 200 `en-US` 3卡 / DE `/de/series/goodwe-bat-c/` 200 `de-DE` 3卡，共享归档模板与语言路由一致） |
| [/series/goodwe-ems/](https://de-linker.com/series/goodwe-ems/) | pa_series:510，count=4 | 已核（EN `/series/goodwe-ems/` 200 `en-US` 2卡 / DE `/de/series/goodwe-ems/` 200 `de-DE` 2卡，共享归档模板与语言路由一致） |
| [/series/goodwe-esa-3-10kw-eha-g20/](https://de-linker.com/series/goodwe-esa-3-10kw-eha-g20/) | pa_series:523，count=12 | 已核（EN `/series/goodwe-esa-3-10kw-eha-g20/` 200 `en-US` 6卡 / DE `/de/series/goodwe-esa-3-10kw-eha-g20/` 200 `de-DE` 6卡，共享归档模板与语言路由一致） |
| [/series/goodwe-esa-5-30kw-eta-g20/](https://de-linker.com/series/goodwe-esa-5-30kw-eta-g20/) | pa_series:512，count=22 | 已核（EN `/series/goodwe-esa-5-30kw-eta-g20/` 200 `en-US` 8卡 / DE `/de/series/goodwe-esa-5-30kw-eta-g20/` 200 `de-DE` 8卡，共享归档模板与语言路由一致） |
| [/series/goodwe-esa-bat-d-g20/](https://de-linker.com/series/goodwe-esa-bat-d-g20/) | pa_series:520，count=12 | 已核（EN `/series/goodwe-esa-bat-d-g20/` 200 `en-US` 5卡 / DE `/de/series/goodwe-esa-bat-d-g20/` 200 `de-DE` 5卡，共享归档模板与语言路由一致） |
| [/series/goodwe-esa-lcn/](https://de-linker.com/series/goodwe-esa-lcn/) | pa_series:522，count=2 | 已核（EN `/series/goodwe-esa-lcn/` 200 `en-US` 1卡 / DE `/de/series/goodwe-esa-lcn/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/goodwe-et-80-100k/](https://de-linker.com/series/goodwe-et-80-100k/) | pa_series:501，count=8 | 已核（EN `/series/goodwe-et-80-100k/` 200 `en-US` 1卡 / DE `/de/series/goodwe-et-80-100k/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/goodwe-etr/](https://de-linker.com/series/goodwe-etr/) | pa_series:517，count=12 | 已核（EN `/series/goodwe-etr/` 200 `en-US` 6卡 / DE `/de/series/goodwe-etr/` 200 `de-DE` 6卡，共享归档模板与语言路由一致） |
| [/series/goodwe-hca/](https://de-linker.com/series/goodwe-hca/) | pa_series:513，count=6 | 已核（EN `/series/goodwe-hca/` 200 `en-US` 1卡 / DE `/de/series/goodwe-hca/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/goodwe-meters/](https://de-linker.com/series/goodwe-meters/) | pa_series:508，count=4 | 已核（EN `/series/goodwe-meters/` 200 `en-US` 2卡 / DE `/de/series/goodwe-meters/` 200 `de-DE` 2卡，共享归档模板与语言路由一致） |
| [/series/goodwe-sts-125k/](https://de-linker.com/series/goodwe-sts-125k/) | pa_series:509，count=2 | 已核（EN `/series/goodwe-sts-125k/` 200 `en-US` 1卡 / DE `/de/series/goodwe-sts-125k/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/goodwe-sts-30-60k/](https://de-linker.com/series/goodwe-sts-30-60k/) | pa_series:524，count=4 | 已核（EN `/series/goodwe-sts-30-60k/` 200 `en-US` 2卡 / DE `/de/series/goodwe-sts-30-60k/` 200 `de-DE` 2卡，共享归档模板与语言路由一致） |
| [/series/pylontech-optim-utility/](https://de-linker.com/series/pylontech-optim-utility/) | pa_series:505，count=2 | 已核（EN `/series/pylontech-optim-utility/` 200 `en-US` 1卡 / DE `/de/series/pylontech-optim-utility/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/saj-accessories/](https://de-linker.com/series/saj-accessories/) | pa_series:496，count=2 | 已核（EN `/series/saj-accessories/` 200 `en-US` 1卡 / DE `/de/series/saj-accessories/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/saj-b2-bu3/](https://de-linker.com/series/saj-b2-bu3/) | pa_series:500，count=12 | 已核（EN `/series/saj-b2-bu3/` 200 `en-US` 2卡 / DE `/de/series/saj-b2-bu3/` 200 `de-DE` 2卡，共享归档模板与语言路由一致） |
| [/series/saj-b2-hv-5-25kwh/](https://de-linker.com/series/saj-b2-hv-5-25kwh/) | pa_series:506，count=4 | 已核（EN `/series/saj-b2-hv-5-25kwh/` 200 `en-US` 2卡 / DE `/de/series/saj-b2-hv-5-25kwh/` 200 `de-DE` 2卡，共享归档模板与语言路由一致） |
| [/series/saj-ci-line/](https://de-linker.com/series/saj-ci-line/) | pa_series:503，count=14 | 已核（EN `/series/saj-ci-line/` 200 `en-US` 2卡 / DE `/de/series/saj-ci-line/` 200 `de-DE` 2卡，共享归档模板与语言路由一致） |
| [/series/saj-data-collectors/](https://de-linker.com/series/saj-data-collectors/) | pa_series:514，count=2 | 已核（EN `/series/saj-data-collectors/` 200 `en-US` 1卡 / DE `/de/series/saj-data-collectors/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/saj-emanager-c1-pro/](https://de-linker.com/series/saj-emanager-c1-pro/) | pa_series:504，count=2 | 已核（EN `/series/saj-emanager-c1-pro/` 200 `en-US` 1卡 / DE `/de/series/saj-emanager-c1-pro/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/saj-emanager/](https://de-linker.com/series/saj-emanager/) | pa_series:521，count=2 | 已核（EN `/series/saj-emanager/` 200 `en-US` 1卡 / DE `/de/series/saj-emanager/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/saj-h2/](https://de-linker.com/series/saj-h2/) | pa_series:497，count=12 | 已核（EN `/series/saj-h2/` 200 `en-US` 1卡 / DE `/de/series/saj-h2/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/saj-hs2/](https://de-linker.com/series/saj-hs2/) | pa_series:498，count=8 | 已核（EN `/series/saj-hs2/` 200 `en-US` 1卡 / DE `/de/series/saj-hs2/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
| [/series/saj-hs3/](https://de-linker.com/series/saj-hs3/) | pa_series:499，count=10 | 已核（EN `/series/saj-hs3/` 200 `en-US` 1卡 / DE `/de/series/saj-hs3/` 200 `de-DE` 1卡，共享归档模板与语言路由一致） |
