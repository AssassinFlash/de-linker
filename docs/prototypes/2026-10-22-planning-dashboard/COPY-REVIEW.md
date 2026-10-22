# 统一方案工作台原型：三语文案与产品语义对抗评审

日期：2026-10-22。评审者：独立 Codex 评审代理。范围：中文、英文、德文的客户可见文案、状态与产品语义；只写本文件，未修改 JS/CSS/HTML，未调用真实 API、发信或提交询盘。

## 初稿固定点

- 文件：[prototype.js](prototype.js)，471行。
- 首轮 SHA256：`e179112ef857f62d9233483f66d7bb48dc55f9d846dd55fa97f18a0170628cb6`。
- 初稿是工作树内尚未提交的原型，不把其他会话的后续修改混成首轮版本。下述行号均指此哈希；复核将以新哈希另记。
- 初稿实际行为来自只读代码：`state`保存同一项目；报告保存输入快照；保存只写内存；聊天只返回固定文本；询盘仅组装本地记录；导出仅生成HTML。没有进行浏览器/视觉验收，不能把源码中的提示证明成各视口都可见。

## 依据与判断边界

- 项目 [AGENTS.md:26](../../../AGENTS.md) 要求客户文案保留初稿→意见→定稿记录；[AGENTS.md:53](../../../AGENTS.md)附近给出 Solution draft / Lösungsentwurf、Bill of materials / Stückliste、德语Sie等用词。精确条文以同树AGENTS为准。
- 已读取 [linker-copywriting SKILL.md](/Users/chesterjohn/.agents/skills/linker-copywriting/SKILL.md) 的Hard Stops、Procedure及术语百科；并读取 [humanizer SKILL.md](/Users/chesterjohn/.agents/skills/humanizer/SKILL.md) 的句子层检查。百科中与当前AGENTS冲突的旧产品/工具名不作依据。
- 该界面新增的维度是“同一项目中的屋顶编辑、目标、设备方案和版本交接”，不是再写一页品牌营销。工具字段/准确操作指令允许使用技术词和简短祈使语；不把“输入尺寸”误判成营销文案给客户布置作业。工程字段的kW/kWh/kWp、SOC、MPPT允许出现在相应深层检查项。
- 真实Journal参考：[桌面实际截图](../../acceptance/2026-10-18/254/current/journal-en-1440.png)、[源模板](../../../plugins/linker-commerce/content/livecanvas/blog_index.html:7)、[设计反馈记录](../../acceptance/2026-10-18/254/change-ledger.md:46)。取其安静的侧栏、内容分层和短标签；不沿用影视平台里未存在的社交/播放承诺，也不让“dashboard”成为功能已完成的证据。
- 最新产品依据：[统一项目/全欧洲/工作台决定](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-system-route-548/docs/research/2026-10-22-roof-system-rebuild/PRODUCT-STRUCTURE.md)。本轮是原型认可前的审查，不表示现有工程、国家覆盖或下游集成已通过。

## 首轮意见：修改后才能收口

### C01 · P1：主按钮承诺检查，实际只生成示例报告

位置：L122 `预览方案检查 / Preview system checks / Systemprüfung ansehen`。

`createRun()`（L352–362）仅冻结输入、演示进度并打开报告，未运行系统检查。“检查”会让客户误读为系统已被核验，其他地方的免责声明不能替按钮纠正。

定稿建议：**生成报告预览 / Create report preview / Berichtsvorschau erstellen**。全三语与L218、L201既有动作一致。此处改文案不会构成数值正确性修复；真实检查仍需后续实现。

### C02 · P1：国家切换拼出不存在的示例地址

位置：L266 `示例地址 / Example address / Beispieladresse`后拼接`Lyon · countryName(state.country)`；项目国家可改DE/CH/GB，而建筑仍是里昂示例。当前解释虽说不会移动真实坐标，主显示仍是“Lyon · Germany”等错误组合。

定稿建议：该行固定为 **示例建筑 / Sample building / Beispielgebäude**，值为本地化的 **里昂，法国 / Lyon, France / Lyon, Frankreich**；项目国家继续在下方独立字段显示。或者去掉城市组合，只展示“尚未设置真实地点”；不能让假地址变成全欧洲项目能力的展示。

### C03 · P1：产品入口声称保留设备上下文，实际只保留来源枚举

位置：L254产品入口说明 `Keep the starting context from a product or existing PV system...`、L428 toast `Starting context retained within the same project.`；实现L426–428仅写`state.origin='product'`并切workspace，没有产品/型号/已有系统数据。

定稿建议：

- 中文：**此处模拟从产品页进入同一项目；当前没有导入产品型号或已有系统数据。**
- EN：**This simulates a product-page entry into the same project. No product model or existing-system data is imported.**
- DE：**Hier wird der Einstieg von einer Produktseite in dasselbe Projekt gezeigt. Produktmodelle und Daten einer bestehenden Anlage werden nicht übernommen.**

toast：**已切换示例入口，项目保持不变。 / Example entry changed; the project is unchanged. / Beispieleinstieg gewechselt; das Projekt bleibt erhalten.**

未来保留设备上下文仍是所需能力，不能把原型缺失改写成产品不需要它。

### C04 · P1：已有光伏、纯储能和备电的操作文案超出当前可演示输入

位置：L174 `Existing PV or storage-only needs continue here.`；当前`candidate`只有PV和PV+storage（L89/201），没有纯储能方案或已有逆变器/光伏资料字段。L186备电卡 `Add critical loads and duration`却没有相应输入。

这会导致评审者以为这些路径已在原型内可操作。本次原型可以暂不演全功能，但应准确标识缺口。

定稿建议：

- L174：**此原型暂未演示已有光伏和纯储能的输入。 / Existing-PV and storage-only inputs are not shown in this preview. / Eingaben für bestehende PV-Anlagen und reine Speicherprojekte sind in dieser Vorschau noch nicht dargestellt.**
- 备电卡副文：**关键负载与供电时长待补充 / Critical loads and duration required / Kritische Lasten und Überbrückungszeit erforderlich**。

这是原型覆盖说明；最终工具必须支持统一项目中的相关输入，不可仅靠这句边界文案替代实现。

### C05 · P2：德国界面和导出残留英文

- L122 breadcrumbs固定`Solution Configurator`：改为`t('方案设计','Solution Configurator','Lösungskonfigurator')`或等价三语名称。
- L116固定`DESIGN PROTOTYPE`：改为**设计原型 / DESIGN PROTOTYPE / DESIGNPROTOTYP**。
- L367导出`<title>Linker example report</title>`：改为 **Linker · 示例报告 / Linker · Example report / Linker · Beispielbericht**。

`Journal`是既有栏目名，可保留；kWp等单位、HTML文件格式名不需要翻译。中文作为本轮评审语言不等于新增生产语言。

### C06 · P2：功率、容量与器件名称统一

位置：L129和L223 `组件直流容量 / Module DC capacity / DC-Modulleistung`。显示单位kWp，中文“容量”容易混同储能kWh，EN也应明确是PV直流装机量。

定稿建议：**光伏装机功率（DC） / PV capacity (DC) / PV-Leistung (DC)**，相同指标保持同名。来源说明中的乘法也用“直流装机功率 / PV DC capacity / PV-DC-Leistung”，不要把电池容量与组件装机功率叫同一个“capacity”。L213 `Montage`作为物料行不等于支架，建议 **Montagesystem, Schutzgeräte und Leitungen**，对应EN **Mounting system, protection and cables**。

### C07 · P2：统一项目信息应当是演示过程，而非声称团队已接收

位置：L177 `System options, reports and inquiries carry the same project version. The team can see...`是全产品能力肯定句，当前团队完全没有连接；L300中文“团队会接到这些内容”也比英文would更肯定。

定稿建议：

- 中文：**此处预览设备方案、报告与询盘如何关联同一项目版本，以及交接时保留哪些已知条件和待核验项。**
- EN：**Preview how system options, reports and an inquiry can reference the same project version, including defined inputs and open checks.**
- DE：**Die Vorschau zeigt, wie Systemvarianten, Bericht und Anfrage auf dieselbe Projektversion verweisen und festgelegte Angaben sowie offene Prüfungen enthalten.**
- 收据标题统一：**团队交接内容示例 / Example handoff to the team / Beispiel für die Übergabe an das Team**。

原型条、询盘“模拟提交·不发送”和收据无邮件声明应保留。无需删除用户需要的同版本交接能力；只需不把演示写成已上线。

### C08 · P2：保存和恢复的实际边界要在就近文案准确

保存L418–420确实只写`state.saved`，toast已说刷新清空，保存抽屉也有清晰限制；**没有发现“已保存到真实账户”的虚假成功句**。但L270 `You are not signed in`是对身份的断言，独立原型并没有检测WordPress登录；L270 `Restoring inputs creates a new input version`也不总真：L327–331只有值变更才revision++。

定稿建议：

- 保存说明：**此预览未连接账户，保存仅在当前页面内有效；刷新后会清空。 / This preview is not connected to an account. Saves last only on this page and are cleared on refresh. / Diese Vorschau ist mit keinem Konto verbunden. Gespeicherte Eingaben gelten nur auf dieser Seite und gehen beim Neuladen verloren.**
- 恢复说明：**恢复后这些输入成为当前项目输入，已有报告继续保留。 / Restored inputs become the current project inputs; existing reports remain available. / Die wiederhergestellten Eingaben gelten für das aktuelle Projekt; vorhandene Berichte bleiben erhalten.**

主按钮可以保留`Save project`以演示未来动作，但必须保留当前页/抽屉/成功toast的就近原型限定。不会要求真实注册或真实账户写入来验收这个抛弃原型。

### C09 · P2：去掉口号及固定桌面空间承诺

- L171 `ONE PROJECT, FROM ROOF TO SYSTEM / EIN PROJEKT, VOM DACH ZUM SYSTEM`符合被禁的from-X-to-Y营销模板，且重复同项目说明。替换为 **当前项目 / CURRENT PROJECT / AKTUELLES PROJEKT**。
- L182“右侧始终显示 / Inputs and assumptions stay beside the canvas”在窄屏通常不是右侧或始终同屏，不应在未看图前写死。替换为 **当前输入与假设在这个工作区内查看。 / View the current inputs and assumptions in this workspace. / Die aktuellen Eingaben und Annahmen finden Sie in diesem Bereich.**

### C10 · P2：德语自然度与既有词汇

| 初稿位置/字符串 | 建议 | 原因 |
|---|---|---|
| L171 `Aus Standortdaten wird ein besprechbarer Entwurf` | `Ein Anlagenentwurf auf Basis Ihrer Standortdaten` | `besprechbar`在此生硬；无需把整个产品说成“一份可说话的草案” |
| L175 `Systemvarianten besprechen` | `Systemvarianten ansehen` | 按钮实际切到比较界面，没有团队对话 |
| L223 `Land: nur Projektdatum.` | `Das Land ist nur als Projekteingabe erfasst.` | `Projektdatum`容易读成项目日期 |
| L275 `Der bestehende Genie wird nicht aufgerufen` | `Diese Vorschau ist nicht mit Genie verbunden.` | 前者拟人化语法生硬，后者准确说明连接状态 |
| L186 `Increase self-use`；L223 `self-use` | `Increase self-consumption`；`self-consumption` | 与既有英德指标和AGENTS的self-consumption/Eigenverbrauchsanteil一致 |
| L96/218/219 `Report & materials` | `Report & bill of materials` | 这是具体报告和清单工作区，非含糊的材料入口；德语`Bericht & Stückliste`保持 |

Genie抽屉读取的是`latestRun()`（L273），并不是当前选中的旧报告；若保留“我正在查看报告”的台词，建议改 **示例说明基于最新报告 / Example explanation for the latest report / Beispielerläuterung zum neuesten Bericht**，避免用户选R1却误以为助手仍在解释当前R1。真实Genie上下文选择属于后续集成，不以改这句证明实现。

## 已通过的语义，不建议改掉

- 一份`model()`贯穿屋顶、用能、设备、报告；切A/B/C只换结构，没有三个独立项目。country与lang分离，符合本轮产品方向。
- 首屏原型条、报告旁注、工程缺项、sources、进度窗都明确没有真实工程引擎。数值是组件数量×460Wp；年量/自给率/自用比例保持未计算。没有用免责声明替代真实工程正确性，也没有宣称厂商放行。
- sources明确排布常量没有标准依据；方向切换不改变能量结果；没有将风雪荷载、消防、并网自动判成合格。
- 国家下拉包含CH/GB/NO等非欧盟国家；说明明确所有国家的规则均未接入。**没有发现“全欧洲已验证”承诺**。当前列表并非欧洲国家穷尽清单；本轮原型选择器不能证明最终全欧洲覆盖，正式范围仍须按目标清单验证。
- 改输入会保留旧报告并标过时；handoff会拒绝过时版本；这是可演示的正确状态关系，不应为了让界面好看删掉它。
- PDF没有冒充已实现：动作明确导出示例HTML，toast又说明其非PDF/工程报告；保留这些区别。
- Genie有AI身份、脚本演示和固定回答说明，没有调用模型。这里只要求措辞和上下文一致，不要求原型连接生产模型。
- 询盘无账号入口、邮箱/姓名/公司选填/留言构成与站点方向一致；模拟提交明确不发邮件、不创建线上询盘。没有新增真实付费、采购或物流承诺。
- 同一项目中备选方案A/B与原型结构A/B/C是两种维度。当前标识基本可辨认；视觉验收若出现混淆，可把设备方案小标签改成“PV/PV+储能”而不是继续叠字母，这不是本轮文案硬阻断。

## 首轮Procedure与放行状态

- [x] 已加载术语百科；本轮新增维度是统一项目的编辑、来源和版本交接。
- [x] 已按Humanizer句子层和Hard Stops 1–9检查；未发现借品牌信用、物流时限、营销参数证明堆砌、虚构客户轨迹、持续服务承诺。
- [ ] 所有可见行通过Hard Stops：C09口号待改。
- [x] 工具字段、明确操作说明与营销“客户作业”区分；没有为了形式去删正常操作提示。
- [x] 未出现被禁品牌、编造评价或引用第三方宣传句。
- [ ] EN/DE名称、指标、按钮与状态语义一致：C01/C05/C06/C10待改。
- [ ] 国家/已有系统/团队交接/保存的局部文案准确：C02–C04/C07/C08待改。
- [ ] 定稿复核：等待作者改JS后重新读取并记录新hash。

**首轮结论：需要修改后再放行。** 当前未发现伪造真实询盘或真实AI调用，但局部动词和输入状态仍会把可操作原型说成已检查/已导入/已关联团队。不得把首轮评审写成最终文案已通过。

## 最终复核（待作者修改）

作者修改完成后由同一评审代理追加：新JS哈希、逐项处理结果、仍需保留的真实能力边界。此段当前没有定稿通过结论。


## 最终三语语义复核结果 · 2026-10-22

**结论：原型客户文案与产品语义复核通过，当前无剩余阻断。** 通过的范围是此固定版本的可操作界面原型，不是工程计算、逐国覆盖、真实账户/Genie/询盘集成或视觉验收。作者正在独立进行浏览器验收；本代理本轮没有操作浏览器，也没有将作者通报的操作结果冒称为自己的实测。

最终复核文件仍为[prototype.js](prototype.js)，SHA256：

`9f8f152bb1791c31d6e22236cdcffe26c74289523d6b6eb504fc12390fe384b8`

复核方式：重新读取三语字符串及其使用状态，逐项核对首轮意见；对先前误导字符串作残留检索，核实所述动作的对应代码。初稿及首轮意见保持原样；上方未勾选项是首轮历史状态，由本段逐项结果替代为本次定稿结论。

| 意见 | 定稿核对结果 | 新版位置 |
|---|---|---|
| C01 检查/报告承诺 | 三语主按钮均为生成报告预览；进度窗、完成toast继续说明没有工程计算。没有把示例报告包装成系统放行 | L122、L305–307、L357–366 |
| C02 示例地址 | 建筑固定为里昂，法国/Lyon, France/Lyon, Frankreich；项目国家另列且解释不改变真实坐标或加载规则 | L268–271 |
| C03 产品入口载荷 | 三语明确仅模拟产品页入口、没有导入型号或已有系统数据；toast只说入口切换、项目保留 | L258、L431–433 |
| C04 尚未演示的输入 | 已有PV/纯储能输入明确未在此预览演示；备电只列关键负载及供电时长为所需资料，没有指令去填不存在的控件 | L175、L187 |
| C05 三语完整性 | 原型标签本地化；德语breadcrumb为Lösungskonfigurator；导出HTML标题随当前语言切换。既有Journal栏目名保留 | L116、L122、L372 |
| C06 功率/物料术语 | 主指标与报告采用光伏装机功率（DC）/PV capacity (DC)/PV-Leistung (DC)；来源算术改直流装机功率；支架一行DE为Montagesystem, Schutzgeräte und Leitungen | L129、L214、L224、L262 |
| C07 团队交接语态 | 概览明确preview how；收据标题为三语团队交接内容示例，继续保留模拟无发送说明；不声称团队已经收到 | L178、L303–304 |
| C08 保存与恢复 | 不再判断用户真实登录状态；明确未连接账户、仅当前页面、刷新清空；恢复说明不再保证每次创建新版本 | L273–275、L423–428 |
| C09 口号/布局承诺 | 概览为当前项目/CURRENT PROJECT/AKTUELLES PROJEKT；工作区说明不再承诺输入永远在右侧同屏 | L172、L183 |
| C10 语言自然度/报告上下文 | 生硬DE短语已替换；self-consumption统一；报告导航为Report & bill of materials；Genie与当前选中的报告版本一致 | L96、L172、L176、L187、L219–224、L277–279 |

附加核对：

- Genie现在取`currentRun() || latestRun()`（L277）；切换历史报告后不再无条件解释最新报告。抽屉仍说明脚本预览、固定回答、未调用AI，未把这次上下文修正当成真实Genie接入。
- 收据保留公司和留言（L304），并继续从`receipt.run`呈现同一保留输入版本。只确认源码中显示与对应文案一致，不将其称为团队通知已送达。
- 语言切换先清理旧语种toast（L346–350）；导航活动项的滚入视口属于作者的交互修复/浏览器验收，不在文案审核里单独宣称通过。
- 原型依然没有任何国家的真实气象、并网或电价计算。国家列表含非欧盟欧洲市场，不等于全欧洲逐国工程覆盖已建成。
- 示例组件网格与460Wp数量算术保持示意标签，年量/储能/电气/结构/国家规则结果仍无伪造数字或通过状态。后续工程能力必须实际建设与验证。
- 保存仍只在内存，HTML仍不是PDF，产品入口仍不导入真实设备，询盘仍仅本地模拟；这些限制已经明确，不因原型文案通过而消失。
- 一个项目中的屋顶、目标、设备与报告关系保持统一；A/B/C是界面结构变体，当前未被文案表述为三个独立软件。

最终Procedure：

- [x] 术语百科已加载，当前AGENTS与本轮产品决定优先于旧资料。
- [x] 初稿、意见、定稿固定点齐全；本次无from-X-to-Y概览口号、借信用或虚构工程成功。
- [x] 操作指令与对应原型能力一致；未演示输入、未连接服务和本地模拟有明确说明。
- [x] EN/DE关键动作、状态、报告指标与草稿/清单术语一致；德语Sie语境及自然表达通过本次独立审读。
- [x] 保存、Genie、询盘、导出和全欧洲目标的真实边界保留；没有用修文案代替数值正确性修复。
- [x] 此哈希文案与产品语义可进入用户设计评审；视觉布局选择、浏览器验收和正式实施由主代理按用户后续裁定处理。

本次仅追加本评审文件，未修改JS/CSS/HTML，未自行commit。


## 最终实操补正 · Genie三语动态标点

日期：2026-10-22。主代理在最终实操发现Genie报告说明拼接了固定中文冒号和句号。作者仅将L279这两处改为`t('：',': ',': ')`和`t('。','.','. ')`，使中文保留中文标点，EN/DE使用半角标点与句间空格。

本次最终JS SHA256：

`9ea451c355df6f120623aabf26c65addb9b92bf02474b1008368798e4f24444d`

评审代理已只读核对两处三语拼接，并在内存中反向还原这两个替换；还原文本的SHA256精确等于前次复核的`9f8f152bb1791c31d6e22236cdcffe26c74289523d6b6eb504fc12390fe384b8`。因此确认JS没有夹带其他修改，**前次C01–C10逐项通过结论适用于本次最终哈希，当前仍无文案或产品语义阻断**。

主代理本轮实操补充（来源为主代理报告，本评审代理没有操作浏览器）：历史R1/v1保留101组件，最新R2/v2为100组件；重新选R1后，Genie显示R1/v1、101组件及过时提示，证明其引用的是当前选中版本。实际示例HTML已成功导出且格式正确；本轮浏览器error/warn为空。这些结果仅针对原型，不意味着真实AI、工程计算、PDF、持久账户或真实询盘链已接入。

本次仍只追加本评审文件，保留全部初稿与复核历史；未修改其他文件，未自行commit。
