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

`quotation-page-copy.py --wp <WP-CLI 前缀>` 只读预览十对正文。实读本地 `review` 的原生 WordPress 正文和翻译基线，七对已应用。剩余五处在 Capability（874、6919）、EPC（6867）和大型储能（1755、6917）。三对旧候选的基线均为 `current=true`，载荷逐字比对确认只改这五处。

本轮停在只读预览。既有 `local:review` 备份 `/Users/chesterjohn/de-linker-data/cutover-20261118-0921/db.sql.gz`（09:21:17 UTC）可正常解压，保存的是旧候选应用前的状态。六页中仅 6919 的正文与当前相同，相关翻译元数据均有差异。应用更正前需要保留当前六页正文和四类翻译元数据作为精确回退点。

正式写入时依次读取快照并调用 `plan_pair`，将有差异的载荷交给现有 `reviewed_page_pair.invoke`。每对必须完整匹配原始版或旧候选的精确片段，写入器仍核对两页完整正文和翻译元数据并在同一事务采纳德语基线。全部定稿片段仍须有原生 `current=true` 才报告 `Already applied`。若正文已定稿而基线过期，预览报错并停止，由原生双语流程核对并恢复基线。
