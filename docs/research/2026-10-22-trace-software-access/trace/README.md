# Trace Software：实际软件入口、账号门槛与已取得原件

调查日期：2026-10-22（北京时间；Apify原始记录使用UTC）。本分工只调查Trace官方获取路径并读取公开原件，主会话独占浏览器实操。没有注册、发送表单/邮件、接受协议、购买或安装软件；也没有修改业务代码或实例。

**已取得6份官方PDF原件，共38页、11,029,769字节，包含elec calc安装/激活指南、2026.0操作变更说明和archelios PRO 2025.1变更说明。实际软件入口也已定位，但没有取得可登录账号、安装包、许可证或可编辑原生项目。** 现有Trace证据不能写成“已经实走完成一个设计”。本轮主线可用其他已实际运行的参照继续，不等待Trace注册。

所有外部网页与文件只经Apify获取。原件由Apify从官方域下载后，再从Apify存储回读到本地，核对PDF魔数、字节、SHA-256、页数，并渲染关键完整页面。来源与运行记录见 [raw/source-index.json](raw/source-index.json)，原件哈希见 [raw/file-index.json](raw/file-index.json)。

## 1. 最早能进入实际软件的位置

### archelios PRO国际网页应用

官方PRO产品页明确它是web application，并直接链接到 [国际登录入口](https://www.archelios.com/online/bin/Archelios-Online-Login.php?lang=en)。这是实际应用登录页，不是宣传页。入口正文有用户名/密码、`Try archelios PRO`和注册面板。[官方PRO产品页](https://www.trace-software.com/en/our-solutions/solar-pv-design-software/)

注册面板明确要填写Name、First name、Email、Company、Postcode、Telephone、Country；还需要接受Trace Standard Terms of Use与Privacy Policy，再提交`Send my password`。页面称密码会发送到邮箱。因此实际进入工作区需要账号及可接收邮件的地址，本轮没有执行这些动作。页面没有证明是否还需要人工批准，也没有证明提交后一定立即开通；不据此断言“自动批准”或“必须销售批准”。[实际登录与注册面板](https://www.archelios.com/online/bin/Archelios-Online-Login.php?lang=en)

本轮在该登录页及所查官方产品入口未找到guest工作区或免账号示例工程入口。隐藏的“其他设备已登录”弹窗是页面预置文案，不表示本次已经登录；不能把抓取HTML中存在该文字当作登录成功。

### 中国区网页应用与试用

[中国区实际登录入口](https://www.archelios.cn/online/bin/Archelios-Online-Login.php?lang=cn)也要求用户名/密码。[中国区Free/试用页](https://www.tracesoftware.cn/archelios-pro/free-pv-design-software/#freeversion)的CTA称先开通黄金版试用、到期转免费版；表单收姓名、公司/机构、Email、城市、手机、职务、国家、需求、购买计划及验证码。它是提交试用申请，不是直接进入guest设计器。本轮没有提交，试用天数、发号方式、审批与实际许可未获确认。

### elec calc / SOLAR

[中国区试用入口](https://www.tracesoftware.cn/trial-request/)列出elec calc、BIM、GRID、SOLAR；同时明确archelios PRO需另走申请。表单要求城市、公司、姓名、职务、手机、Email、当前工具、业务需求等信息。它能发起申请，但本轮没有申请，也没有收到安装包或试用许可证。

官方导航的[用户下载区](http://support.trace-software.com/Pages/login.aspx)实际返回`Authentication required`，有Email、Password和注册账号入口。未登录时没有取得下载列表；不能从“存在Register an account”推断所有人注册后都有软件许可或安装包。

## 2. Free的容量限制存在官方区域差异

| 当前已取官方页 | 页面明确写的范围 | 本轮结论 |
| --- | --- | --- |
| [英文archelios PRO Free](https://www.trace-software.com/en/our-solutions/archelios-pro-free-free-pv-design-software/)及[PRO比较表](https://www.trace-software.com/en/our-solutions/solar-pv-design-software/) | 9kWp/project | 英文当前公开页面给9kWp；Free属于PRO产品范围，有功能限制，并非免账号guest |
| [中文Free页](https://www.tracesoftware.cn/archelios-pro/free-pv-design-software/) | 36kWp；比较列又使用`<36kWp` | 中文页面给36kWp，边界表述并不完全一致；未进入账号验证实际限制 |

两者不能合并为“全球免费36kWp”。本轮无法确认差异来自区域许可、发布版本或未同步页面，不能自行给出原因。英文Free页的`Request`链接指向本页`#formulaire-apfree-en`，该位置嵌HubSpot申请表；不是直接软件下载链接。其申请表的实际运行/邮件结果没有测试。

## 3. 产品职责、平台和依赖

| 产品 | 官方当前定位 | 平台/依赖的已获证据 | 获取状态 |
| --- | --- | --- | --- |
| archelios PRO | 光伏项目布置/三维建模、逆变器与组串配置、产量/自用及储能分析、技术经济分析和交付物 | 官方明确web application；当前比较表列内建3D建模，并将SketchUp插件、Revit插件列为特定版本集成能力，不能把所有PRO使用都写成必须先安装SketchUp。具体插件主机/版本支持需另核 | 已到真实登录页；无账号，未进入设计工作区。[产品及比较表](https://www.trace-software.com/en/our-solutions/solar-pv-design-software/) |
| archelios PRO Free | 同一PRO范围的免费受限版本 | 英文9kWp与中文36kWp差异见上；不能默认拥有付费版全部3D、输出与集成功能 | 申请/注册入口已定位；未开通。[英文Free页](https://www.trace-software.com/en/our-solutions/archelios-pro-free-free-pv-design-software/) |
| archelios CALC | 从组件经逆变器到电网的光伏电气设计、线缆/保护与规范检查 | 当前产品页仍存在，并明确其经验正在向elec calc SOLAR更完整的电气项目演进；本轮没有取得CALC专属当前OS要求或安装包 | 页面仍列商业订阅；不能断言已停产，也不将它假定为最新产品主线。[CALC当前产品页](https://www.trace-software.com/en/our-solutions/archelios-calc/) |
| elec calc | 高/低压电气网络设计与计算，覆盖保护、短路、压降、工作场景等 | 已取得安装指南F01，PDF p3明确Windows10/11 64位、20GB磁盘、管理员安装；安装程序为供应方提供的自解压exe，文中称`Install.exe`。未取得Mac原生安装包 | 公开指南可下载；运行软件仍需安装程序及许可证。[产品页](https://www.trace-software.com/en/our-solutions/electrical-installations-calculation-software/)、[F01官方原件](https://dl.trace-software.com/dl//frk/docs/Installing/01_FR_elec_calc_Guide_d_installation_du_logiciel_et_d_activation_de_la_licence.pdf#page=3) |
| elec calc SOLAR | 在同一电气项目中完成光伏DC链、交流配电、负载/EV充电及并网侧设计与选型 | 现行订阅页正文明确推荐Windows11、32GB RAM、20GB、i5，安装/更新需联网。该网页标题误写IRVE，正文和商品说明明确SOLAR，不能仅按标题认错产品 | 试用需申请；本轮无安装包或许可。[官方SOLAR页](https://www.trace-software.com/en/our-solutions/elec-calc-solar-complete-pv-design-software-from-panel-to-ev-charging-point/)、[SOLAR订阅页正文](https://www.trace-software.com/en/product/elec-calc-solar-annual-subscription/) |

F01 p3的RAM一行原样写`16b`、推荐显示分辨率一行也有印刷问题；没有将其自行“修正”为精确最低配置。SOLAR订阅页的32GB与1920×1080是另一份当前公开来源，可独立引用。没有核实Mac虚拟机/兼容层的厂商支持，不推测其可用性。

关于许可，F01 p5描述取得许可证号后经网络或邮件激活；p4说明单机需本地许可证服务/管理器，p7说明浮动许可。它描述正式许可流程，不证明试用必须先购买，也没有给公开exe下载URL。2016年旧许可手册F04仅作历史资料，不用其旧端口/许可细节替代当前规则。

### 现行PRO → SOLAR的实际文件级证据

F02《elec calc 2026.0更新说明》PDF p5（印刷3）明确PRO项目可直接导入elec calc，恢复组件与逆变器型号引用和项目总体结构，继续电气选型与规范检查；功能适用于elec calc SOLAR或带SOLAR模块的elec calc。p3–4有真实DC单线图、交流连接和报告示意。已看完整渲染：[p3](raw/files/elec-calc-2026-notes-p3.png)、[p4](raw/files/elec-calc-2026-notes-p4.png)、[p5](raw/files/elec-calc-2026-notes-p5.png)。这是官方操作资料证据，尚未用软件导入过一个项目。[F02原文](https://dl.trace-software.com/dl//frk/docs/Changelog/01_FR_Note_de_mise_a_jour_2026.0.pdf#page=5)

中国区[当前SOLAR说明](https://tracesoftware.cn/products-2/software-for-sizing-elec-calc-solar/)与[PRO登录入口关联新闻页](https://tracesoftware.cn/archelios-pro-news/)也描述PRO→SOLAR导入、单线图、交直流、负荷/充电桩和BOM。这与F02吻合；不再只以较早的PRO→CALC宣传推定现行工作流。

## 4. 已实际拿到的文件

所有下列文件均为官方公开原件，没有填写表单或绕过认证。完整SHA、HTTP状态、Apify run/dataset/record和PDF元信息记录在 [file-index.json](raw/file-index.json)。

| 编号 | 本地可打开原件 | 物理页数 / 字节数 | 版本与适用范围 |
| --- | --- | --- | --- |
| F01 | [elec calc安装与许可激活指南](raw/files/01_FR_elec_calc_Guide_d_installation_du_logiciel_et_d_activation_de_la_licence.pdf) | 11 / 4,954,203 | 可见封面没有版本号；PDF元信息创建2026-08-18，不冒充特定软件发行版。已核p1/3/5/7/11完整页面 |
| F02 | [elec calc 2026.0更新说明](raw/files/01_FR_Note_de_mise_a_jour_2026.0.pdf) | 8 / 2,072,413 | 明确2026.0；PDF元信息2026-04-30；包含SOLAR、电气建模及PRO导入实际示意 |
| F03 | [archelios PRO 2025.1更新说明（DE）](raw/files/04_DE_Update-Notiz_2025.1.pdf) | 7 / 1,404,216 | 明确2025.1；PDF元信息2025-11-18。可学结果报告与错误/恢复状态，但不是本轮实走 |
| F04 | [旧elec calc许可管理手册（FR）](raw/files/Managing_License_Elec_Calc_FR.pdf) | 4 / 189,897 | 封面Ind:B / 2016-04-25，明确历史材料 |
| F05 | [旧archelios PRO宣传册（FR）](raw/files/FlyerACpro_FR_LT.pdf) | 4 / 763,019 | 元信息创建2015、修改2016；只作历史界面资料，不据此确定现行功能/许可 |
| F06 | [旧archelios suite宣传册（FR）](raw/files/FlyerACsuite_FR_LT.pdf) | 4 / 1,646,021 | 元信息2015；只作历史资料，不替代现行SOLAR路线 |

关键SHA：

- F01：`83c793a4a74bdc9268a92c10459c3cec6eaf1408dfea299c1846eb87f76ec12c`
- F02：`512760d3752676825bfdba0038421806e174969cfc6f199be39573b0f9353ceb`
- F03：`80905f3239d55446bff97256f3192d489a08e570aece81958a5a232e8322cbc9`

F03 PDF p3（印刷1）同时展示屏幕产量指标与PDF报告的P50/P75/P90等信息，可直接比较屏幕与交付物的数据承接，见 [完整页](raw/files/archelios-2025-notes-p3.png)。PDF p7（印刷5）记录电池数据手册缺字段的错误弹窗说明、CSV“含储能”行、温度参数与电池老化修复，见 [完整页](raw/files/archelios-2025-notes-p7.png)。它们能给后续实际观察提供检查点，不能据此认定我们已验证其数值算法或现版本所有状态。[F03原件](https://dl.trace-software.com/dl/archelios_PRO/04_DE_Update-Notiz_2025.1.pdf)

## 5. 官方公开操作视频入口

以下链接直接来自已取得的Trace官方页面，已核其被官网挂载。视频文件未下载，视频播放及完整内容未由本子任务验证；浏览器实走由主会话负责。

| 对象 | 官方页面证据 | 直达入口 |
| --- | --- | --- |
| PRO操作/介绍 | [PRO产品页](https://www.trace-software.com/en/our-solutions/solar-pv-design-software/)内嵌 | [YouTube 6EUY8g4-hFs](https://www.youtube.com/watch?v=6EUY8g4-hFs) |
| CALC操作/介绍 | [CALC产品页](https://www.trace-software.com/en/our-solutions/archelios-calc/)内嵌 | [YouTube k35qrA2U4rk](https://www.youtube.com/watch?v=k35qrA2U4rk) |
| SOLAR操作/介绍 | [SOLAR产品页](https://www.trace-software.com/en/our-solutions/elec-calc-solar-complete-pv-design-software-from-panel-to-ev-charging-point/)内嵌 | [YouTube GZXW7L3b_PU](https://www.youtube.com/watch?v=GZXW7L3b_PU) |
| 中国区PRO课堂 | [官方网上课堂](https://tracesoftware.cn/services/technical-webinars/)内嵌并链接官方账号 | [B站 BV1G44y1T7Xm](https://www.bilibili.com/video/BV1G44y1T7Xm/)、[官方账号](https://space.bilibili.com/1136485040) |
| 中国区Free页面示范 | [中文Free页](https://www.tracesoftware.cn/archelios-pro/free-pv-design-software/)内嵌 | [B站 BV1Th4y1h7vm](https://www.bilibili.com/video/BV1Th4y1h7vm/) |
| 其他公开演示 | [官方Videos/Webinars页](https://www.trace-software.com/en/our-services/webinars/)列多段视频 | [Trace官方YouTube频道](https://www.youtube.com/@TraceSoftware) |

[官方PRO培训页](https://www.trace-software.com/en/our-services/trace-software-training/training-course-archelios-pro/)将Online与SketchUp培训分开，并要求SketchUp培训者先完成PRO Online课程。可取得的是课程说明；没有预约课程或声称取得全部培训项目文件。

## 6. 本轮尚未取得的东西与真实门槛

| 目标 | 实际结果 | 下一步所需，不能冒充已完成 |
| --- | --- | --- |
| 可交互PRO设计工作区 | 取得真实登录/注册面板；未登录 | 需账号、邮件及条款处理；是否人工审批未知。中国区也可走试用申请，但本轮不提交 |
| elec calc / SOLAR安装包 | 未拿到exe/msi或安装包字节 | 官方试用申请/已授权下载账号；F01描述如何装已提供的Install.exe，不是下载地址 |
| 许可证 | 未取得、未激活 | 厂商试用或现有授权；正式许可文档不能证明试用交付机制 |
| 可编辑原生样例项目 | 未取得 | 所查官网产品、资源、下载入口及官方域定向搜索没有取得公开原生项目；不断言厂商完全不提供 |
| 独立完整示例报告 | 未取得项目导出的完整报告文件 | F02/F03只有报告截图/片段；不能把更新说明PDF冒充客户项目完整报告 |
| 现行营销宣传册 | 取得下载落地页，未取得该落地页对应的新PDF | [PRO落地页](https://contenu.trace-software.com/en/download-our-archelios-pro-software-brochure)、[CALC落地页](https://contenu.trace-software.com/en/download-our-archelios-calc-software-brochure)、[elec calc落地页](https://contenu.trace-software.com/en/download-our-brochure-on-elec-calc-software)、[SOLAR落地页](https://contenu.trace-software.com/en/download-the-elec-calc-solar-software-brochure)含HubSpot表单嵌入；没有填写或执行领取。F05/F06是另外公开地址的旧册，不能混用 |
| 视频实走 | 取得官网内嵌与直达URL | 是否成功播放、时长、具体操作结果由主会话浏览器证据另行确认 |

本分工到此停止扩展来源。接下来若继续以Trace做完整对照，明确尚缺“账号进入→建立/打开原生项目→修改输入→计算→查看失败→导出”的实际操作链；已经下载的安装/操作资料可以立即打开学习。主线无需等待这个账号步骤，可使用本轮另已取得并实跑的参照推进。

## 7. 原始证据、可复核性与采集限制

- [source-index.json](raw/source-index.json)按URL列出官方网页的实际HTTP状态、loadedUrl、run/dataset、原始JSON位置与HTML/正文哈希；搜索输出只作发现线索，产品结论均回到实际官方页或PDF。
- [file-index.json](raw/file-index.json)保存6个PDF原件的字节、SHA、来源HTTP200与Apify存储记录。原件、提取文本和关键整页渲染在 [raw/files/](raw/files/)。
- 所有成功采集的crawler run使用1024MB、maxConcurrency2。一次尝试通用web-scraper时收到`full-permission-actor-not-approved`，没有批准新增权限；改用已有website-content-crawler的`htmlTransformer=none`取得完整导航、表单和链接。见 [collection-limitations.json](raw/collection-limitations.json)。
- 两次PDF run的crawler摘要分别记录`0 succeeded / 2 failed`和`0 succeeded / 4 failed`，原因是内容解析未成功；同时dataset保留了6个HTTP200的fileUrl，原件已从Apify KV回读并验证。文件取得与网页正文解析是两项不同证据，不用actor总状态代替原件核验。
- Apify token仅由既有安全helper读取，并只放Authorization头；没有复制凭据。存档JSON剥除了临时Apify记录URL签名，以run/dataset/record标识和原件哈希复核。
- 没有解锁用户门户、猜测许可证、发送信息、接受协议或安装程序；不把未执行步骤写为软件验证成功。
