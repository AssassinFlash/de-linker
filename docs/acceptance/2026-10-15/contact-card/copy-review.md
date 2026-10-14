# /contact/ 卡文案对抗评审记录（2026-10-15，清账决策 2）

规则（AGENTS.md §2）：客户可见文案（含事务邮件）一律初稿 → 评审意见 → 定稿记录在案；
EN 先行、DE 独立撰写非翻译（德语 Sie 体、`de_DE_formal`）；基准 = linker-copywriting
Hard Stops + 线上既有措辞与 `.po` 术语。定稿即 `.po` 的 msgstr 与代码里的 msgid
（`plugins/linker-commerce`）。

本篇覆盖清账决策 2 移植的整卡（`[linker_contact_form]`）带来的客户可见串，以及团队信
新增的一行；**并逐条交代它与 `docs/acceptance/2026-10-11/68/copy-review.md` 三处定稿
（该文件 §2 的同意句、提交按钮、按钮下小字）的关系**。

## 0. 与 #68 定稿的关系（不取代，附理由）

#68 的三处定稿**原样保留**，本票不动它们：

| 位置 | 定稿（保留） | 本票为何不取旧线上原文 |
|---|---|---|
| 同意勾选 | `I agree that my details may be used to respond to this message.` / `Ich bin damit einverstanden, dass meine Angaben zur Beantwortung dieser Nachricht verwendet werden.` | 旧线上是 `…this enquiry.` / `…dieser Anfrage…`。若改回，页面口径变成 enquiry，而**客户回执邮件**（`includes/Contact/Emails/ReceiptEmail.php` 主题 `We received your message`、`templates/emails/linker-contact-receipt.php` 正文 `Thank you for your message…`）仍是 message，页面与回执两个口径并存；把回执也改成 enquiry 又会与**询盘链**自己的状态词（询盘四状态 `Inquiry received / Anfrage eingegangen`，AGENTS §3）撞词——正是 #68 评审否掉 `Anfrage` 的理由。故本票不推翻该定稿。 |
| 提交按钮 | `Send message` / `Nachricht senden` | 同上。#68 评审原话：线上按钮是 `Send enquiry`/`Anfrage senden`，"本表单不是询盘（询盘 = Proforma 链）…按钮沿用 enquiry 会让客户以为进了询盘流程"。#68 之后该判断的任何反证据未出现（询盘链仍是唯一带 Proforma 的链，AGENTS §1）。 |
| 按钮下小字 | `Your message goes to the Linker team. We reply to the address you give here.` / `Ihre Nachricht geht an das Linker-Team. Wir antworten an die Adresse, die Sie hier angeben.` | 旧线上是 `Your question goes to the Linker team. Keep the receipt to check its progress.` / `Ihre Anfrage geht an das Linker-Team. Mit dem Beleg können Sie den Stand prüfen.`。两句都只陈述路由与回复去向，但旧句的 "receipt / Beleg" 指的是退役运行的**回执工作区**（页面上的保存回执、可按状态复查，见 `docs/acceptance/2026-10-14/contact-form/README.md`），本实现没有它；照抄会给客户一个不存在的去处。 |

**因此本票的两处口径只有一个：message/Nachricht**（页面与两封客户可见邮件一致）。
若本线日后要改成 enquiry/Anfrage，那是一次跨页面 + 回执邮件 + 询盘链状态词的整套改写，
需要新的评审记录，不在本票。

## 1. 本次移植引入的客户可见串（初稿 → 评审 → 定稿）

初稿 = 旧线上原文（2026-10-12/13 旧线上截图与页面自带样式表；主题标签的字母逐一取自
退役运行时的 `labels` 表，`contact-request.js` 的 `labels`——截图闭合态与样式表都读不到
那些字）。评审为对抗式自查：以 Hard Stops、AGENTS §3 用词、`.po` 既有术语与站上现状逐条
反驳；DE 是站点自己的德语（旧线上德文即德语版原文），不是 EN 的逐词翻译。

| 位置 | EN 定稿 | DE 定稿 | 评审 |
|---|---|---|---|
| 眉题 | `CONTACT LINKER` | `KONTAKT ZU LINKER` | 与邀请带（`[linker_contact_invitation]` 的 epc 面）同串、已在 `.po`；DE 大写形与页面渲染一致。不改。 |
| 标题 | `What can we help with?` | `Wie können wir helfen?` | 旧线上原文。评审：不涉询盘/订单承诺，只是提问口吻；Sie 体；与 #68 的 `Your question`/`Ihre Frage` 同一语义场。定稿同初稿。 |
| 引导句 | `Tell us what you need. We’ll use the email below for your reply.` | `Beschreiben Sie Ihr Anliegen. Für die Antwort verwenden wir die unten angegebene E-Mail-Adresse.` | 旧线上原文（含 `We’ll` 的弯引号）。评审：句里承诺的只有"用下面这个地址回复"，与实现一致（回执与团队信都按客户填的地址回）；不含时限承诺（#68 已否 "one business day"，此处不复活）。定稿同初稿。 |
| 问题占位 | `What would you like to know?` | `Was möchten Sie wissen?` | 旧线上原文。评审：与 `Kontaktformular` 的 `Ihre Frage` 标签并列不重复；占位不是标签的复述（标签问"你的问题"，占位给例子式引导）。定稿同初稿。 |
| 主题标签 | `This is about` | `Es geht um` | 旧线上原文。评审：与团队信新行同词（见 §2），一处词面两处使用。定稿同初稿。 |
| 主题选项（7） | `A question` / `Product guidance` / `Price & availability` / `Product documents` / `Discuss a project` / `Support for an order` / `Work with Linker` | `Eine Frage` / `Produktberatung` / `Preis und Verfügbarkeit` / `Produktunterlagen` / `Projekt besprechen` / `Hilfe zu einer Bestellung` / `Zusammenarbeit mit Linker` | 取自退役运行时的 `labels` 表（值 `general/product/offer/document/project/support/partnership`）。评审逐条：①`Product guidance`/`Produktberatung` 是服务词，不碰 AGENTS §2 的 Product/Model/Series 定名；②`Price & availability`/`Preis und Verfügbarkeit` 是报价前的常规询问，不等于 Proforma 链的状态词；③`Support for an order`/`Hilfe zu einer Bestellung`——站上**没有**订单链（AGENTS §1），此选项不承诺任何自助订单流程（选了也只进同一封团队信），指"客户在我们这买过设备后的支援"这一线下事实，保留；④其余三项为一般事由描述。定稿同初稿。 |
| 回复区小标题 | `Where can we reply?` | `Wohin dürfen wir antworten?` | 旧线上原文。评审：只问回信去向，与实现一致（`Reply email` 必填）。DE "dürfen wir" 是征询许可的礼貌式，Sie 体成立。定稿同初稿。 |
| 免账号说明 | `No account or Project is needed to ask a question.` | `Für eine Frage brauchen Sie weder ein Konto noch ein **Projekt**.` | EN 同初稿。**DE 改一词**：旧线上德文写的是英文名词 `Project`（退役运行的"已保存 Project"是英文名的功能，该功能在新树不存在）；德语客户可见句里放英文名词是文字缺陷，且站上德语一律 `Projekt`（`.po` 的 `Discuss a project`→`Projekt besprechen`、页面正文 `Projektanforderungen`）。句子结构与含义不变（"既不需要账号也不需要项目"）。 |
| 副卡一二 | `Prefer email?` / `Send your question directly to our team. Opening your email app does not send a message.` / `Still exploring?` / `Take your time.` / `Use Genie to explore the options, then return to your question.` / `Explore with Genie` | `Lieber per E-Mail?` / `Schreiben Sie unserem Team direkt. Das Öffnen Ihres E-Mail-Programms sendet noch keine Nachricht.` / `Noch in der Orientierung?` / `Nehmen Sie sich Zeit.` / `Mit Genie können Sie Ihre Möglichkeiten erkunden und später zu Ihrer Frage zurückkehren.` / `Mit Genie weiterdenken` | 旧线上原文，工具名按改名记录替换（`docs/acceptance/2026-10-10/12/copy-review.md:7`：EN `Linker Advisor`→`Genie`、DE `Linker Berater`→`Genie`）——旧线上两句里的 `Linker Advisor`/`Advisor` 因此写作 `Genie`。评审：①`Prefer email?` 下的地址是团队邮箱本身（`Options::team_to()`），与表单落地同一处，不另开通道；②"打开邮件应用不等于发送"是必要的实话（mailto 不静默发送）；③`Take your time.` 不催单、无时限承诺；④`Noch in der Orientierung?`（"还在找方向？"）是旧线上德文，非直译。定稿同初稿。 |

## 2. 团队信新增行（内部面，照记录）

`templates/emails/linker-contact-team.php`：

- EN 初稿：`This is about: %s`（`%s` = 主题标签，见 §1）。
- 评审：这封信只发给团队邮箱与 Bcc（客户不可见），但仍入本记录，因为它决定卡上选择
  的去处。三问：①要不要把主题值原样回显？——不，值经 `Submission::INTENT_FIELD` 白名单
  校验，白名单外一律落到 `general`，信里只会出现卡上给过的七个标签之一，不会回显任意
  输入；②用哪个词？`This is about` 与卡上标签 `This is about` 同词，团队看到信就知道客户
  在卡上看到的是哪一问；③`%s` 占位符给 `esc_html` + `esc_html__`，`.po` 有德语。
  **定稿**同初稿：`This is about: %s` / `Es geht um: %s`。
- 说明：本行不承载复信路由（`Reply-to` 仍是客户地址，先于本行），也不进入客户回执。

## 2b. 同意行的取值选择（几何取旧线上、颜色取现行 tokens）

同意行（`.linker-form-consent`）的可见几何本票取**旧线上参考卡**的值，不取 #68 登记过的
`text-xs text-neutral-600` 意图：

| 项 | 取值 | 来源 |
|---|---|---|
| 行字号 / 行高 | 11px / 1.85 | 旧线上卡 `contact-journal.css` 的 `.lkc-check{font-size:11px;line-height:1.85}` |
| 行颜色 | `--proto-neutral-500` | 旧线上是 `--cp-muted`（旧卡绿灰）；按清账要求颜色用现行 tokens |
| 复选框 | 18×18、上边距 2px、`accent-color: var(--proto-accent)` | 旧线上 `.lkc-check input{width:18px;height:18px;margin:2px 0 0}`；色用现行 token |
| Privacy 链接 | `--proto-teal-600`、下划线、offset 3px | 旧线上 `.lkc-check a{color:var(--cp-teal);text-decoration:underline;text-underline-offset:3px}` |
| 方框与文字间距 | 10px | 旧线上 `.lkc-check{gap:10px}` |

理由：/contact/ 是复刻面、像素门按旧线上卡逐行比，同意行是可见面；几何照旧线上可少一条
登记差异，颜色一律落在现行 tokens（清账泳道明令"只移植组成/结构/间距，颜色用现行 tokens"）。
另一条候选（#68 的 12px/`neutral-600` + 浏览器默认 13px 方框）不取：它小于旧线上一档、
且方框明显更小，会在像素门上留下整行差异。实测（本机机读，1440/390 × EN/DE 四格一致）：
字号 11px、行高 20.35px、色 `rgb(90,99,99)`、方框 18×18/2px、链接 `rgb(12,127,115)` +
underline + offset 3px。

为什么这行要写进本记录而不是只写进验收 README：上一轮该行的样式落在标记的工具类上，
在 `#theme-main` 内被编译缓存里一条未分层的 `all: revert` 规则吃掉（实测见
`docs/acceptance/2026-10-15/contact-card/README.md`），计算值是 15px / 13×13 —— 即
**"取哪个值"这件事当时并没有真正落地**。本轮把它移进卡自己的样式表，本表即其定稿。

## 3. 本票相对旧线上卡面的**有意差异**（供像素门登记）

移植目标面是复刻面在像素门内，因此下列与旧线上原文不同处须逐条进变更台账、给业主过目
（AGENTS §5 像素门：允许的差异只有裁定过的变更）：

1. 三处按 #68 定稿：按钮 `Send message`/`Nachricht senden`、同意句 `…this message.`/
   `…dieser Nachricht…`、小字 `Your message goes to the Linker team…`/`Ihre Nachricht geht…`
   （理由见 §0）。
2. 一处德语文字修正：`…noch ein Projekt.`（旧线上 `…noch ein Project.`，理由见 §1）。
3. 工具名替换：副卡里的 `Explore with Genie`/`Mit Genie weiterdenken`（旧线上为
   `Explore with Advisor`/`Mit Advisor weiterdenken`；改名记录见 §1 同一行）。
   另有旧线上 `Use Linker Advisor to explore…`/`Mit Linker Advisor können Sie…` 同因写作
   `Genie`。
4. 颜色不照旧线上（全站冷色调现行裁定，清账泳道明令"只移植组成/结构/间距，颜色用现行
   tokens"）——几何与颜色差异按像素门逐项登记，不在本记录重复。

不属"有意差异"的其余字面（眉题、标题、引导句、占位、主题标签与七选项、回复区小标题、
免账号说明的 EN 与 DE 句构、两张副卡的标题与正文）逐字取自旧线上原文，像素门按复刻面
要求比对。
