# #1143 英德客户文案审校

原句以 `c2616abfe` 为准。页头、询盘、审批邮件以 `7892336de` 的差异为准，联系表单接续 `74f81b93d`。每处记录初稿、评审意见与定稿。评审由执行代理按 STSS 与 Linker 商业文案规则完成。

## 页头配置器

- **原句。** 英文桌面 `The Roof detail step adds the building's layout.`，移动 `The Roof detail step adds the layout.`。德文两处均为 `Der Schritt Dachdetails nimmt die Dachfläche auf.`
- **初稿。** EN `You can add a roof layout if needed.` / DE `Bei Bedarf können Sie die Dachfläche einzeichnen.`
- **评审。** 只说这个步骤做什么，客户仍不能判断没有屋顶图能否继续。配置器规格明确屋顶设计可选，桌面和移动入口都要给出同一事实。保留原来对整套方案和 Stückliste 的说明。
- **定稿。** 桌面和移动均采用初稿。

## 询盘确认页与客户回执邮件

- **原句。** EN `We reply within one business day.` + `The Linker team will reply to the email address you provided.` / DE `Wir antworten innerhalb eines Arbeitstags.` + `Das Linker-Team antwortet Ihnen an die angegebene E-Mail-Adresse.`
- **初稿。** EN `We reply within one business day to the address you entered.` / DE `Sie erhalten innerhalb eines Arbeitstags eine Antwort an die von Ihnen angegebene Adresse.`
- **评审。** `address` 和 `Adresse` 在商务链可指邮寄地址，应明确是电子邮箱。旧页面第二句在窄屏被隐藏。把时限和回复渠道放在同一条可见提示中，保留待审核和未寄回执时的专用提示。邮件也只说一次。
- **定稿。** EN `We reply within one business day to the email address you provided.` / DE `Sie erhalten innerhalb eines Arbeitstags eine Antwort an die angegebene E-Mail-Adresse.`

## 账户审批邮件

- **通过原句。** EN `Net prices are now shown with every product. Add the systems you need to your solution draft, and request the Proforma when the draft is ready.` / DE `Die Nettopreise werden jetzt zu jedem Produkt angezeigt. Legen Sie die benötigten Systeme in Ihren Lösungsentwurf und fordern Sie die Proformarechnung an, wenn er fertig ist.`
- **通过初稿。** EN `You can now see net prices where available. You can send your solution draft as an inquiry.` / DE `Sie sehen jetzt die verfügbaren Nettopreise. Ihren Lösungsentwurf können Sie als Anfrage senden.`
- **通过评审与定稿。** 按 `CommerceState::shows_price()` 保留价格可用范围。按 2026-11-08 报价裁定与询盘提交按钮说明客户下一步。初稿通过。
- **拒绝原句。** EN `We cannot approve your Linker partner account. Signing in therefore stays closed.` / DE `Wir können Ihr Partner-Konto bei Linker nicht freigeben. Die Anmeldung bleibt deshalb geschlossen.`
- **拒绝初稿。** EN `Your Linker partner account was not approved. You cannot sign in with this account.` / DE `Ihr Partner-Konto bei Linker wurde abgelehnt. Sie können sich mit diesem Konto nicht anmelden.`
- **拒绝评审与定稿。** 写清这次账户决定，以及该账户无法登录。保留审批人员给出的原因和 `sales@de-linker.com`。初稿通过。

## 联系表单

| 位置 | 原句 EN / DE | 初稿 EN / DE | 具体评审 | 定稿 EN / DE |
|---|---|---|---|---|
| 引言 | `Tell us what you need. We’ll use the email below for your reply.` / `Beschreiben Sie Ihr Anliegen. Für die Antwort verwenden wir die unten angegebene E-Mail-Adresse.` | `Tell us what you need.` / `Beschreiben Sie Ihr Anliegen.` | 引言引导客户填写问题。邮箱字段本身已说明输入内容。 | 同初稿 |
| 联系资料标题与邮箱字段 | `Where can we reply?`、`Reply email` / `Wohin dürfen wir antworten?`、`E-Mail für die Antwort` | `Your contact details`、`Email address` / `Ihre Kontaktdaten`、`E-Mail-Adresse` | 这一组还包含姓名和可选公司名。标题概括字段，标签说明格式。邮箱仍必填，关联标签与自动填充沿用原实现。 | 同初稿 |
| 按钮下方 | `Your message goes to the Linker team. We reply to the address you give here.` / `Ihre Nachricht geht an das Linker-Team. Wir antworten an die Adresse, die Sie hier angeben.` | `The Linker team replies within one business day.` / `Das Linker-Team antwortet innerhalb eines Arbeitstags.` | 客户在发送前需要知道由谁回复、何时回复。时限取现行业主约定，也已在 `includes/Contact/Form.php` 的 `sent_no_receipt` 和 `templates/emails/linker-inquiry-received.php` 的共用回执中可见。移除重复的回复地址说明，保留同意条款、免账号与免项目说明、失败后恢复提示。 | 同初稿 |

`FormTest`、`CheckoutTest`、`ApprovalTest` 与 `inquiry-states.spec.ts` 分别覆盖联系表单、询盘确认、审批邮件与客户确认页的文案。德语来自 `linker-commerce-de_DE_formal` 字典，页头两语直接来自对应 LiveCanvas 局部模板。

## 站点报价文案

十对页面的逐句英德原句与初稿见 `98f9dc9af:tools/migrate/quotation-page-copy.py` 的 `REVISIONS`，按下表页号定位。该提交的第二项是初稿，未改的德语句取 WordPress 正文。定稿以本轮 `quotation-page-copy.py` 同一键下的第二项为准。询盘、报价与线下交易依据见 [11-commerce.md 的「用户旅程」和「银行账户」](../../../specs/11-commerce.md)。

| 页面（EN / DE） | 初稿处理 | 质询与适用边界 | 定稿 |
|---|---|---|---|
| Terms of Sale / Verkaufsbedingungen（1674 / 6825） | 免账号询价或留言，说明草稿询盘、报价含适用税额及正式发票才有付款银行信息。 | 网站收到的是询盘，成交、开票和支付是线下步骤。报价 PDF 按 Woo 税务配置列税额，正式发票载明银行信息有业主裁定，二者应分开。电子单据条款、运费计入时点、预付条件及税率资格需要另有线下事实依据。 | 四处均用初稿。适用范围为访客入口、询盘至报价的顺序、报价所列适用 VAT 和银行信息出现的位置。 |
| Refund and Returns Policy / Rückerstattungs- und Rücksenderichtlinie（1038 / 6698） | `You can request a quotation or send us a message without an account.` / `Auch ohne Konto können Sie ein Angebot anfordern oder uns eine Nachricht senden.` | 免账号是询盘能力。退货条文中原 Proforma 编号的替代凭证尚未确认，不能猜成报价号、订单号或发票号。 | 用初稿。仅修改开头的免账号说明。 |
| Contact / Kontakt（28 / 6907） | 用 `quotation requests` / `Angebotsanfrage` 更新产品与资料问答。 | 客户可以问库存、数据手册、安装指南并询价。这条问答承诺的是团队协助，表单回执及一个工作日内回复见上节。 | 用初稿。仅修改该问答，保留可直接联系团队的入口。 |
| About / Über uns（862 / 6865） | 团队准备报价并与客户讨论商务条件。 | 客户需要知道由谁接手。合同成立、付款要求及任何交付日期由具体交易文件或沟通确定。 | 用初稿。仅修改团队承接商务环节的原句。 |
| Capability / Leistungsfähigkeit（874 / 6919） | 英文初稿改成 `before order confirmation`，德文已写 `vor der Auftragsbestätigung`。 | 两句把技术核对移到了订单确认前。客户需要先明确设备配置，英文本来把核对放在签发报价前。评审站两篇正文及英文修订 `8550` 已核对。 | EN `Before we prepare your quotation, we review the available technical data with you to narrow down the configuration.` / DE `Bevor wir Ihr Angebot erstellen, prüfen wir mit Ihnen die verfügbaren technischen Daten und grenzen die Auswahl passender Konfigurationen ein.` 仅调整核对时点，前句列举的选型因素继续有效。 |
| For EPC / Für EPC（842 / 6867） | 发运按订单的交付约定，配置在报价编制期间仍可调整。 | 评审站英文的现场条件已写 `while we prepare your quotation`，德文同段仍承诺投产前可改。工程团队需要看到同一个可调整阶段，发运描述沿用逐单约定。 | 初稿其余句保留。德语现场条件句定为 `Wenn sich die Standortbedingungen während der Angebotserstellung ändern, können wir die Konfiguration noch anpassen.` 适用于报价编制阶段及原段项目协作，不推断投产后的变更条件或运费。 |
| For Installer / Für Installateure（826 / 6869） | 保留德国仓库、项目资料和交付规划，将阶段改称报价与交付。 | 有货的备件和设备、随询盘可索的项目资料以及可安排的交付，都有采购价值。原句把交付日期绑定到 Proforma，需要明确团队按每笔订单和当时库存讨论预计日期。 | 用初稿中的引言、阶段名称与说明、团队流程及交期答复。适用于项目询盘与交期沟通。 |
| Residential Storage / Heimspeicher（749 / 6923） | 将步骤标签和标题统一为报价与可用性，说明德国仓库核查和预估交期用于安排安装。 | 客户需要知道何时能计划安装。报价与后续商定订单交期是两步，预计日期不等于保证日期。 | 用初稿。仅调整此步骤的标题、标签和正文。 |
| Utility-Scale Storage / Großspeicher（1755 / 6917） | 保留项目报价中的设备、价格、保修三项，单独把交付排期移到订单沟通。 | 报价 PDF 的设备行和价格已核实，模板没有保修条款字段。项目价值是看到所选设备及价格，并与团队安排交付。 | EN `Your project quotation lists the equipment and prices for your storage system. We work out the delivery schedule with you when arranging the order.` / DE `Ihr Projektangebot führt die Geräte und Preise für Ihr Speichersystem auf. Den Lieferplan stimmen wir bei der Auftragsabwicklung mit Ihnen ab.` 适用于项目报价与交付规划，原页其他设备和资料卖点保留。 |
| Privacy Policy / Datenschutzerklärung（1673 / 6827） | 现有询盘和发票记录行改用报价术语，沿用答复询盘、制作报价与法定记账的用途。 | 报价可以作为询盘文件归类。税率声明的采集时点、个人数据字段、处理和保存范围需要真实数据流程依据。 | 用初稿。仅替换现有文件名称及对应的报价用途，税率声明一行另行核实。 |

首页交付资料清单不在这十对页面中。销售条款的线下运费及电子单据、退货凭证和隐私税率声明沿用现行正文，待相应事实确认后再定稿。

### 写入与验收

评审站原有七对页面已采用定稿。主线在 11:21 UTC 保存 `local:review` 增量恢复点 `cutover-20261118-1121` 后，应用其余三对的五处正文更正，涉及 Capability（874、6919）、EPC（6867）和大型储能（1755、6917）。

从二十个英德公开入口逐页读取定稿，各页返回 HTTP 200，十对页面的原生翻译基线均为 `current=true`。

正式写入时依次读取快照并调用 `plan_pair`，将有差异的载荷交给现有 `reviewed_page_pair.invoke`。每对必须完整匹配原始版或旧候选的精确片段，写入器仍核对两页完整正文和翻译元数据并在同一事务采纳德语基线。全部定稿片段仍须有原生 `current=true` 才报告 `Already applied`。若正文已定稿而基线过期，预览报错并停止，由原生双语流程核对并恢复基线。

## 德语 Lösungsentwurf 图片链接

- **原句。** 附件 4462 为 `SAJ B2-10.0-HV1: three white modules on a grey base`，附件 2085 为 `SAJ BC2-HV1 control module on top of the B2 stack`。每张图均由对应英德商品共用，没有德语附件配对。
- **初稿。** 给链接加「Produkt ansehen」和商品名称，沿用英文图片描述。
- **质询。** Woo 在缩略图过滤器之后生成链接，原生可访问名称取图像 `alt`。一条本地化的同义描述可以同时保留识别目的地的型号和图像内容。适用范围为德语 Woo 草稿中的这两条现有描述，其他附件及原语种仍从原数据渲染。
- **定稿。** `SAJ B2-10.0-HV1: drei weiße Module auf einem grauen Sockel` / `SAJ BC2-HV1: Steuermodul oben auf dem B2-Stapel`。在 `de_DE_formal` 用真实商品和 Woo 原生购物车模板核对，图片地址保持原值。评审站加载候选插件后，访客从两个德语商品页加购，在 Lösungsentwurf 中按上述图片名称均能找到对应商品链接。Chromium 整页回归通过。

## 安装商博客

551–560 与十篇德语孪生以评审站 WordPress 原文为准。下表列出七对确有工程选型误导的文章。逐句英德原文和独立撰写的定稿见 [博客迁移](../../../../tools/migrate/installer-blog-copy.py) 对应 ID，553 / 6887 的摘要也同步改为按负荷与运行时段定容。

| 文章 EN / DE | 初稿处理 | 对抗评审 | 定稿 |
|---|---|---|---|
| 混合逆变器与 AC 耦合 551 / 6883 | 将效率比较从耦合方式改为设备实测。 | 删除转换次数与效率结果之间的必然因果，同时说明共用 AC 布线与监测控制的区别。保留新装和改造各自的选型价值。 | DC 耦合充电省去先转 AC 的步骤。AC 耦合改造可利用已有 PV 逆变器。比较时看预期负荷下的系统实测效率，并计入第二台逆变器的调试。 |
| 逆变器与电池配对 552 / 6885 | 将电池优先的开机顺序改为设备说明书指引。 | GoodWe ET 与 SAJ H2 手册的开机顺序不同。电池品牌、总线名称或固定电压分类也不能确认具体机型组合获准使用。 | 让型号、模块数、电压窗口、通信接口和固件回到兼容表与安装说明，保留交接前的读数及充放电测试。 |
| 家用备电定容 553 / 6887 | 按停电时段算 kWh，同时沿用 5 → 4.5 kWh 的 LFP 例子。 | 按 24 小时均摊掩盖停电时段的实际用电。SAJ 的 90% 与 Pylontech 的 95% 是不同机型规格。铭牌可用能量也不能直接视作停电时送到负荷的能量。 | 分开校核同时负荷和启动峰值。假设四小时平均负荷 0.3 kW，回路需 1.2 kWh。将 5 → 4.5 kWh 明确归于 SAJ B2-5.0-HV5，并写出起始荷电状态、限值和损耗。卡片摘要同步。扩容按选定电池及逆变器的允许模块数执行。 |
| 室内外储能 554 / 6889 | 将通用防护等级和温度标称改成按型号核对。 | SAJ B2 的充电起点为 0 °C、放电起点为 −10 °C，已与原文统一的 −20 °C 不符。SAJ B2 也支持落地安装。IP 等级无法独立说明所有安装条件。 | 保留室内通风、间距和摆位价值。室外段写选用厂商明确支持相应环境的型号，核对现场暴露条件和充放电各自的温度范围。 |
| 光储调试 555 / 6891 | 采用产品手册的开机顺序，保留调试检查项。 | 不在通用文章中复述某套设备的开关步骤。兼容文档对不同设备组合列出不同固件条件。 | 按安装组合的说明书开机、设定固件、核对读数并做功能测试，实际并网参数和限发值按项目条件执行。 |
| 家用储能与自用 559 / 6899 | 去掉 50–70% 外送和超过 80% 自用的固定比率。 | 用电时段与 PV 出力决定电量重叠。发生停电时，备电回路和 PV 能否继续供电也受设备及接线影响。 | 比较同一家庭有无储能，按时间匹配发电与负荷，并纳入可用容量、充放电能力和损耗。备电段只讲项目实际接入的回路。 |
| 工商业削峰 560 / 6901 | 保留 500 → 350 kW、150 kW / 300 kWh，估算单个计费时段的费用影响。 | 满额削峰要区分电池输出功率、区间送出能量和可用容量。一个区间变低不足以证明账单峰值降低。Netze BW 同时列有年度与月度费率，不能预设按月，也没有通用备电时长。 | 例中持续一刻钟须输出 150 kW、送出 37.5 kWh。若实际费率取最高一刻钟均值且整个计价周期的峰值由 500 降至 350 kW，费用差为 150 kW 乘当期同一功率单价。备电按可同时运行的负荷、目标时长与预留能量计算。 |

### 552 / 6885 家储入口

**原句。** 两篇均链接到旧电池分类，按钮分别为 `Explore compatible batteries` 和 `Kompatible Batteriespeicher entdecken`。

**初稿。** 改用两语家储分类，按钮分别写 `Explore home storage` 和 `Heimspeicher entdecken`。

**质询。** 旧分类 202 无德语配对，公开访问跳到英文家储分类。正式英德分类 450 / 613 互为配对，均返回 HTTP 200。按钮应说明客户将打开家储分类，具体设备能否配对仍由文章中的厂家兼容表判定。

**定稿。** 采用初稿，英文链接 `/product-category/home-storage/`，德文链接 `/de/produkt-kategorie/heimspeicher/`。

**评审站只读核对。** WordPress 原生读取确认 552 / 6885 互为配对，英文源的翻译基线为 `current=true`。实际英文章按钮仍为 `Explore compatible batteries`，指向旧分类路径。实际德文章按钮仍为 `Kompatible Batteriespeicher entdecken`，公开 HTML 的链接已指向德文家储分类，存储正文仍使用旧分类路径。

**目标分类与待应用差异。** 单独请求两条正式分类 URL 均返回 HTTP 200。英文页标题为 `Home Storage`，页面语言为 `en-US`。德文页标题为 `Heimspeicher`，页面语言为 `de-DE`。两页均显示 `SAJ BC2-HV1`，商品链接使用各自语种。迁移预览只替换两篇存储正文中的分类链接及按钮文字。`cutover-20261118-1213` 早于两篇当前评审正文，无法精确恢复当前状态。本轮仅完成只读核对，两个 CTA 待应用，点击验收待执行。

原始依据

- AC/DC 耦合与自用率模型使用 HTW Berlin 的系统实测及负荷假设。[Stromspeicher-Inspektion 2026](https://solar.htw-berlin.de/studien/stromspeicher-inspektion-2026/) · [Unabhängigkeitsrechner FAQ](https://solar.htw-berlin.de/faq-unabhaengigkeitsrechner/)
- 开机次序与固件条件采用所售相关设备的原厂资料。[GoodWe ET / ET Plus / BT §7.2](https://de-linker.com/wp-content/uploads/2026/09/goodwe-et-et-plus-bt-user-manual-en.pdf) · [SAJ H2 §5.1](https://de-linker.com/wp-content/uploads/2026/10/SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf) · [GoodWe EMEA 兼容表](https://de-linker.com/wp-content/uploads/2026/09/GW_Battery-Compatibility-Overview_EMEA-EN_20260910.pdf)
- 备电按关键负荷和停电时段，电池用实际产品的可用容量。SAJ B2 数据表也给出充放电温度和安装方式。[REopt Module 6](https://www.nlr.gov/reopt/curriculum/videos/reopt-lite-tutorial-module-6-text) · [SAJ B2 数据表](https://de-linker.com/wp-content/uploads/2026/10/SAJ_B2_5-25kWh_HV1-HV5_Datasheet_DE.pdf) · [Pylontech Force H3 数据表](https://de-linker.com/wp-content/uploads/2026/09/Pylontech_Force-H3_Datenblatt_DE-SD-260507.pdf)
- 示例的一刻钟为明确假设。当地实际计费应看适用费率的量价合同。[Netze BW 2026 费率表 1、3](https://assets.cdn.netze-bw.de/xytfb1vrn7of/7eQvxehZzn3ECbR9rALmyD/ecc795b9dcd666ce1f53d9d04362a321/netzentgelte-strom-netze-bw-gmbh-2026.pdf) · [Netze BW 2026 规则 §4.1.1 及年度最大需量定义](https://assets.cdn.netze-bw.de/xytfb1vrn7of/2xbvzba27IJwe250rd5DmE/f7821823df3bf261de1e55a472b35db2/regelungen-fuer-die-nutzung-des-stromverteilnetzes-2026.pdf)

评审站七对文章的原生翻译基线均为 `current=true`。已从评审站公开入口读回 14 篇文章正文及 553 / 6887 各自的文章页摘要。`/blog/` 和 `/de/blog/` 的文章卡片显示标题和日期。
