# #184 账号链重设计 · 文案对抗评审记录

规则（AGENTS.md §2 文案评审 + §3 用词）：客户可见文案一律走对抗评审，EN 先行、
DE 独立撰写（Sie 体、`de_DE_formal`），基准 = linker-copywriting Hard Stops +
线上既有措辞与 .po 术语。本记录只覆盖本轮**新增或改动**的客户可见字符串；沿用
既有 .po 条目的文案（Anmelden、Arbeitsbereich、Proformarechnung、
Lösungsentwurf、Auslegungsbericht、Unternehmensdaten、Zu den Produkten …）不逐
条重列。设计基准 = 业主 2026-10-15 验收通过的原型
（`docs/design/2026-10-15-account-redesign/prototype/`）；原型的 EN/DE 文案是
初稿来源，逐条复审后定稿如下。

定稿即 `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` 与
模板/短代码里的字面量。

## 0. 预检：术语与硬停

- 德语 Sie 体：全部条目已核（无 du 形式、无 "man"）。
- 禁句：无 "nicht …, sondern …"、无三连排比、无 "nicht nur … sondern auch"。
- Hard Stop 3/4/6：无否定式自我辩护（"no broker"）、无强化词
  （direct/official/guaranteed）、无 "Tell us…" 式作业派发。
- Hard Stop 9 Actor：新句的动作主语是 Linker（"We review…"、"We answer…"）；
  唯一的祈使句是注册卡里的账户动作提示（"Use at least 8 characters…"）——
  属控件说明，不是服务作业。
- 事实核对：品牌面板第三条 "We answer inquiries within one working day" 与
  业主 2026-10-09 承诺（一个工作日内回复询盘）逐字一致；不写响应时间、
  不写发货承诺。

## 1. 品牌面板（登录/注册卡左侧，≥1080px）

- EN 初稿（原型）：`Your partner account` / `The workspace for installers,
  EPCs and distributors.`
  评审：两句都在公共面（卡标题级）。`partner account` 是站上既有说法
  （`Sign in or register`、pending 页 "Ihr Partner-Konto"），保留。
  **定稿**：同初稿。
- DE 初稿：`Ihr Partnerkonto` / `Der Arbeitsbereich für Installateure, EPCs
  und Händler.`
  评审：`Installateure` 与 .po 的注册选项不一致——.po 里 Installer =
  `Installationsbetrieb`、EPC contractor = `EPC-Unternehmen`、Distributor =
  `Händler`（票 #73 注册链的定名）。三个词改成 .po 术语；`der Arbeitsbereich`
  与 .po 的 `Workplace` = `Arbeitsbereich` 同源。`Partnerkonto` 连写与站上
  既有术语不符——pending 页与审批邮件都是 `Partner-Konto`（带连字符），
  统一为站上形态。名词堆两句连排可接受（列表短语，非排比句）。
  **定稿**：`Ihr Partner-Konto` /
  `Der Arbeitsbereich für Installationsbetriebe, EPC-Unternehmen und Händler.`

### 1b. 品牌面板三条要点

- EN 初稿：`Net prices and Proforma requests once approved` / `Every inquiry
  and document in one place` / `We answer inquiries within one working day`
  评审：第一条主语省略（列表短语体），但 "once approved" 是承诺的边界条件，
  必须留；`Every inquiry and document in one place` 与登录卡副文案
  `Your inquiries, documents and prices in one place.` 重复度高——刻意保留：
  面板讲的是什么（范围），卡讲的是给谁（你），且面板只在 1440 出现。
  第三条把 "one working day" 写进面子（业主承诺），保留。**定稿**：同初稿。
- DE 初稿：`Nettopreise und Proforma-Anfragen nach Freischaltung` /
  `Alle Anfragen und Dokumente an einem Ort` /
  `Wir beantworten Anfragen innerhalb eines Arbeitstages`
  评审：`Proforma-Anfragen` 是站上页面名（`Proforma-Anfrage` 德语页），保留；
  `Freischaltung` 初判与注册卡副文案同族，但 .po 里**价格的既有说法是
  `Preise nach Freigabe`**（价格门）；本句讲的是价格可见性，改用 `Freigabe`
  与既有术语一致（`Freischaltung` 专指账号开通，仍留在注册卡副文案与
  pending 句式里）。`Alle Anfragen und Dokumente an einem Ort` 与登录卡德语
  副文案 `Ihre Anfragen, Dokumente und Preise an einem Ort.` 同构。
  **定稿**：`Nettopreise und Proforma-Anfragen nach Freigabe` /
  `Alle Anfragen und Dokumente an einem Ort` /
  `Wir beantworten Anfragen innerhalb eines Arbeitstages`。

### 1c. 注册卡的品牌面板（本轮返工新增：每张卡自己的面板）

V1 偏差修正：品牌面板不再横跨两卡，登录卡与注册卡各带自己的面板
（原型 login.html 与 register.html 各自的 `.brand` 内容），故注册侧文案
本轮新入 .po。四条新串：

- EN 初稿（原型）：`Create your partner account`（面板标题）/
  `For installers, EPCs and distributors: net prices, documents and inquiries
  in one workspace.` / `You see net prices on every product after approval` /
  `We run the VAT ID check in VIES for you`
  评审：面板标题与卡标题 `Create your business account` 不重复——面板讲身份
  （partner account），卡讲动作（business account）；副文案与登录面板
  `The workspace for installers, EPCs and distributors.` 同族（同一批受众）。
  第二条要点 "net prices … after approval" 与登录面板第一条同义，但在这里
  是"你能看到什么"（注册者视角），第三条 VIES 检查是本票既有机制的实话
  （`Registration\VatProfile` 在注册时调 VIES，e2e 有夹具）。
  **定稿**：同初稿。
- DE 初稿（原型）：`Legen Sie Ihr Partnerkonto an` /
  `Für Installationsbetriebe, EPC-Unternehmen und Händler: Nettopreise,
  Dokumente und Anfragen in einem Arbeitsbereich.` /
  `Nettopreise sehen Sie zu jedem Produkt nach der Freigabe` /
  `Die USt-IdNr.-Prüfung im VIES übernehmen wir`
  评审：`Partnerkonto` 连写改站上既有形态 `Partner-Konto`（同 §1）；
  受众三词沿用 .po 术语（`Installationsbetriebe` / `EPC-Unternehmen` /
  `Händler`）；第二条 `nach der Freigabe` 与既有 `Preise nach Freigabe` 同源；
  第四条改为动词在前的 `Wir prüfen die USt-IdNr. im VIES für Sie`——与同列表
  的 `Wir beantworten Anfragen innerhalb eines Arbeitstages` 同构，德语读起来
  不吊尾。**定稿**：`Legen Sie Ihr Partner-Konto an` /
  `Für Installationsbetriebe, EPC-Unternehmen und Händler: Nettopreise,
  Dokumente und Anfragen in einem Arbeitsbereich.` /
  `Nettopreise sehen Sie zu jedem Produkt nach der Freigabe` /
  `Wir prüfen die USt-IdNr. im VIES für Sie`。

## 2. 登录卡 · 双入口

- EN 初稿：`No partner account yet?` + `Create your business account`
  评审：注册卡标题 `Create your business account` 是 .po 既有条目（保留）；
  新增的是引导句。`partner` 一词与站上既有文案一致。**定稿**：同初稿。
- DE 初稿：`Noch kein Partnerkonto?` + `Erstellen Sie Ihr Firmenkonto`
  评审：`.po` 里 `Create your business account` = `Erstellen Sie Ihr
  Firmenkonto`（既有条目，不动）；引导句与 .po 的
  `Noch kein Konto? Registrieren Sie sich auf der Kontoseite.` 同族，缩为
  `Noch kein Partner-Konto?`（`Partnerkonto` 连写改站上既有形态
  `Partner-Konto`）。**定稿**：`Noch kein Partner-Konto?` +
  `Erstellen Sie Ihr Firmenkonto`。

- EN 初稿：`Already have a partner account?` + `Sign in`
  评审：与登录卡引导句成对，动词词组 `Sign in` 用 .po 既有 `Sign in` =
  `Anmelden`，不新造。**定稿**：同初稿。
- DE：`Sie haben bereits ein Partner-Konto?` + `Anmelden`
  评审：`.po` 既有 `Returning customer?` 的替换是
  `Already have an account?` = `Sie haben bereits ein Konto?`（Proforma 页），
  这里加 `Partner`（`Partner-Konto`，站上既有形态）与登录卡引导句对称，
  句法沿用既有条目。**定稿**：同初稿。

## 3. 密码说明行（注册、重置、账户细节三处共用）

- EN 初稿：`Use at least 8 characters with a mix of letters, numbers and
  symbols.`
  评审：`at least 8 characters` 是控件要求的事实描述；站位在输入框下、
  强度条旁，属深面控件说明（Hard Stop 7 左栏？不——表单说明句是控件文案，
  不是营销面）。WP 自带强度计提示句（`wp_get_password_hint()` =
  "Hint: The password should be at least twelve characters long…"）与我们的
  8 字符下限冲突，因此不用 WP 那句。**定稿**：同初稿。
- DE 初稿（原型）：`Verwenden Sie mindestens 8 Zeichen mit Buchstaben, Zahlen
  und Sonderzeichen.`
  评审：Sie 体祈使句在控件说明里成立（与 .po 的
  `Bitte geben Sie eine gültige Postleitzahl ein.` 同族）；`mindestens 8
  Zeichen` 与 WP 德语提示不冲突（我们不展示 WP 那句）。**定稿**：同初稿。

## 4. 重置密码卡（reset.html：链路里原先的裸 Woo 模板）

- EN 初稿：`Choose a new password` / `New password` / `Re-enter new password`
  / `The passwords do not match.`
  评审：标题不再用 Woo 的 "Reset password"（与请求页 `Reset your
  password` 重复）；`Choose a new password` 是德语链路的对应动词。
  字段标签的英文沿用 Woo 的 `New password` 与 `Re-enter new password` 措辞，
  但**由本模板以 linker-commerce 域打印**（不是 Woo 域）：德语定稿
  `Neues Passwort wiederholen` 要说得出，就得走我们自己的 .po——留在 Woo 域
  只会落到 Woo 语言包的 `Neues Passwort erneut eingeben`，定稿变成死条目。
  **定稿**：同初稿（域名见 §10 表注）。
- DE 初稿：`Wählen Sie ein neues Passwort` / `Neues Passwort` / `Neues
  Passwort wiederholen` / `Die Passwörter stimmen nicht überein.`
  评审：`wiederholen` 与 Woo 德语的 `Neues Passwort bestätigen` 及
  账户页的 `Neues Passwort bestätigen` 不一致——统一为
  `Neues Passwort wiederholen`？两处会分叉。改：字段标签统一用
  `Neues Passwort` / `Neues Passwort wiederholen`（与原型一致），账户页
  第三字段沿用同句，避免同一字段两种说法。**定稿**：同初稿。

## 5. 账户细节页（account.html）

- EN 初稿：`Your details`（卡的无障碍名）/ `Password change` /
  `Leave the password fields blank to keep your current password.` /
  `Current password` / `New password` / `Confirm new password`
  评审：Woo 原生标签是 `Current password (leave blank to leave unchanged)`，
  括号重复且长；改标题级说明行 + 干净标签（说明行讲规则，标签讲字段）。
  `Create a password` 与 `Password change` 之间取后者（动作是改，不是建）。
  `Your details` 只作 aria-label（原型里第一张卡没有可见标题）。
  **定稿**：同初稿。
- DE 初稿：`Ihre Angaben` / `Passwort ändern` /
  `Lassen Sie die Passwortfelder leer, um Ihr aktuelles Passwort zu behalten.`
  / `Aktuelles Passwort` / `Neues Passwort` / `Neues Passwort bestätigen`
  评审：`Passwort ändern` 与 .po 的
  `ändern Ihr Passwort und Ihre Kontodetails` 同源；`Ihre Angaben` 是德语界面
  对 "your details" 的常规说法（.po 无条目）。第三字段在改密语境用
  `Neues Passwort bestätigen`（Woo 德语习惯）；与 §4 重置语境的
  `Neues Passwort wiederholen` 并存——EN 侧本就分叉
  （`Confirm new password` vs `Re-enter new password`），两页不同屏不同时机
  出现，按 §10 补记允许分叉。**定稿**：见 .po。

## 6. 门禁（gates.html 四态）

- EN 初稿（badge）：`Under review`；DE：`In Prüfung`。
  评审：badge 是短标签，正文标题已是 `Your account is under review`
  （.po 既有）。`In Prüfung` 与 .po 的 `Ihr Konto wird geprüft` 同源。
  **定稿**：同初稿。
- EN 初稿（guest 带草稿）：`Sign in to request your Proforma` + 正文
  `Your solution draft is saved. Log in with your partner account to send the
  inquiry — no account yet? Register on the account page; the draft waits for
  you.`
  评审：标题与另一态 `Get your Proforma` 区分（有草稿：动作是发送；无草稿：
  动作是取号）。正文 43 词偏长——但该页原先只有一行 Woo 默认表单，用户
  需要知道草稿还在；拆句后读作"草稿在 → 登录发送 → 没有账户则注册 → 草稿等
  你"，四段信息都是必要的。破折号连接保留（原型同）。
  末句 `the draft waits for you` 是承诺还是事实？草稿确实在会话/账户里——
  guest 的草稿在 session cookie，注册后 claim 走
  `woocommerce_load_cart_from_session`（SavedSolutions::claim），故这句话
  有机制支撑。**定稿**：同初稿。
  DE：`Melden Sie sich an, um Ihre Proformarechnung anzufordern` /
  `Ihr Lösungsentwurf ist gespeichert. Melden Sie sich mit Ihrem Partner-Konto
  an, um die Anfrage abzusenden — noch kein Konto? Registrieren Sie sich auf
  der Kontoseite; Ihr Entwurf wartet dort auf Sie.`
  评审：`abzusenden` 对应站上 "send the inquiry" 的既有说法
  （`Sends the inquiry without payment` = `Sendet die Anfrage…`）；
  `dort` 指 Kontoseite（德语更喜欢带位置副词，避免悬垂）。**定稿**：同初稿。
- EN 初稿（approved 空草稿）：`Nothing to submit yet.` + 正文
  `Your solution draft is empty. Add matched systems, then come back for your
  Proforma.`
  评审：`matched systems` 是站上兼容合同的公共说法（.po：`Add matched
  systems` 家族已有 `Add to solution draft`；`matched` 出现在
  compatibility 文案）。**定稿**：同初稿。
  DE：`Noch nichts zu senden.` / `Ihr Lösungsentwurf ist leer. Fügen Sie
  passende Systeme hinzu und kehren Sie dann für Ihre Proformarechnung
  zurück.`
  评审：.po 已有同句 `Your solution draft is empty. Add matched systems,
  then come back for your Proforma.` 的德语；直接沿用既有译文（修一处）：
  既有译文 = `Ihr Lösungsentwurf ist leer. Fügen Sie passende Systeme hinzu
  und kehren Sie dann für Ihre Proformarechnung zurück.`（本轮**保留既有
  条目**，仅新增标题 `Noch nichts zu senden.`）。**定稿**：见 .po。

## 7. 一键登出提示

- EN 初稿：`You have been signed out.`
  DE 初稿：`Sie wurden abgemeldet.`
  评审：英文用被动语态是 Woo/WP 通知的常规语域（同类信息条
  `Password reset email has been sent.`）。德语 `abgemeldet` 是 Woo 德语
  `Log out` = `Abmelden` 的过去分词，语域一致（不用 `ausgeloggt`）。
  **定稿**：同初稿。

## 8. 工作台 · 询盘列表摘要

- EN 初稿：`%s product` / `%s products`（`_n`）；
  DE 初稿：`%s Produkt` / `%s Produkte`。
  评审：`.po` 的 `Product` 术语在德语是 `Produkt`（票 #73 注册链
  `Products` = `Produkte`）；数字用 `number_format_i18n()`，德语千分位为点。
  单复数用 `_n`（WP 复数形式），不用 `%d products` 硬拼。**定稿**：同初稿。

## 9. 两处 .po 缺口核对（#180 关闭评论所列）

- `empty-documents`：`Your Proforma invoices and the design reports of your
  saved solutions will appear here.` → 现有德语条目
  `Hier erscheinen Ihre Proformarechnungen und die Auslegungsberichte Ihrer
  gespeicherten Lösungen.` 已存在且非空（核实于 2026-10-15 当前树，
  `msgattrib --untranslated` 未列该条）。**结论：缺口已由上游票据关闭，
  本轮无需动作。**
- `Terms.php` 的 Request-again 两条：源串是 Woo 侧
  `The cart has been filled with the items from your previous order.`，
  映射目标是我们自己的
  `Your solution draft has been replaced with the products of the earlier
  inquiry.` —— 该 msgid 的德语条目
  `Ihr Lösungsentwurf wurde durch die Produkte der früheren Anfrage ersetzt.`
  已存在。Woo 源串本身不需要 .po 条目（它不是我们的 msgid）。
  **结论：同上，缺口已关闭；本轮复核后无动作。**

## 10. 新增 .po 条目（本轮）

入门：`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po`
（**26 条** = 25 条单数 msgid + 1 条 `_n` 复数，全部为客户可见字符串，
故按覆盖门必须翻译）。其中 22 条是首轮评审的交付内容（S6 计数的 21+1），
另 4 条是 V1 返工后注册卡自带品牌面板新增的串（§1c），本轮一并入 .po。
下表 26 行与 .po 当前树逐条对应：

| msgid (EN) | msgstr (DE, 定稿) |
| :--- | :--- |
| `Your partner account` | `Ihr Partner-Konto` |
| `The workspace for installers, EPCs and distributors.` | `Der Arbeitsbereich für Installationsbetriebe, EPC-Unternehmen und Händler.` |
| `Net prices and Proforma requests once approved` | `Nettopreise und Proforma-Anfragen nach Freischaltung` |
| `Every inquiry and document in one place` | `Alle Anfragen und Dokumente an einem Ort` |
| `We answer inquiries within one working day` | `Wir beantworten Anfragen innerhalb eines Arbeitstages` |
| `No partner account yet?` | `Noch kein Partner-Konto?` |
| `Already have a partner account?` | `Sie haben bereits ein Partner-Konto?` |
| `Use at least 8 characters with a mix of letters, numbers and symbols.` | `Verwenden Sie mindestens 8 Zeichen mit Buchstaben, Zahlen und Sonderzeichen.` |
| `Choose a new password` | `Wählen Sie ein neues Passwort` |
| `New password` | `Neues Passwort` |
| `Re-enter new password` | `Neues Passwort wiederholen` |
| `The passwords do not match.` | `Die Passwörter stimmen nicht überein.` |
| `Your details` | `Ihre Angaben` |
| `Password change` | `Passwort ändern` |
| `Leave the password fields blank to keep your current password.` | `Lassen Sie die Passwortfelder leer, um Ihr aktuelles Passwort zu behalten.` |
| `Current password` | `Aktuelles Passwort` |
| `Confirm new password` | `Neues Passwort bestätigen` |
| `Under review` | `In Prüfung` |
| `Sign in to request your Proforma` | `Melden Sie sich an, um Ihre Proformarechnung anzufordern` |
| `Your solution draft is saved. Log in with your partner account to send the inquiry — no account yet? Register on the account page; the draft waits for you.` | `Ihr Lösungsentwurf ist gespeichert. Melden Sie sich mit Ihrem Partner-Konto an, um die Anfrage abzusenden — noch kein Konto? Registrieren Sie sich auf der Kontoseite; Ihr Entwurf wartet dort auf Sie.` |
| `You have been signed out.` | `Sie wurden abgemeldet.` |
| `%s product` / `%s products`（`_n` 复数） | `%s Produkt` / `%s Produkte` |
| `Create your partner account` | `Legen Sie Ihr Partner-Konto an` |
| `For installers, EPCs and distributors: net prices, documents and inquiries in one workspace.` | `Für Installationsbetriebe, EPC-Unternehmen und Händler: Nettopreise, Dokumente und Anfragen in einem Arbeitsbereich.` |
| `You see net prices on every product after approval` | `Nettopreise sehen Sie zu jedem Produkt nach der Freigabe` |
| `We run the VAT ID check in VIES for you` | `Wir prüfen die USt-IdNr. im VIES für Sie` |

表注（域名与占位符，两条本轮修正）：

- `Net prices and Proforma requests once approved` 的德语由
  `nach Freischaltung` 改为 `nach Freigabe`（§1b：与既有 `Preise nach Freigabe`
  一致）。
- `New password` / `Re-enter new password` 由重置卡以 **linker-commerce 域**
  打印（§4），德语才落到本表定稿；此前模板用的是 Woo 域，本表条目不可达。
- 门禁两句（§6）的邮箱改为占位符：`Write to %s and we will look at your
  account again.` / `Until then, browse the products and write to %s with any
  question.` —— 地址由 `sprintf` 填入并把整句做成 mailto 链接，翻译改词或
  换序都不会静默吞掉链接。德语 msgstr 同位置 `%s`（`Schreiben Sie an %s,
  und wir sehen uns Ihr Konto erneut an.` / `Bis dahin können Sie die Produkte
  ansehen und Ihre Fragen an %s schreiben.`）。

补记（一致性）：`Confirm new password` 与 `Re-enter new password` 是同一字段
在两个表单里的两个上下文（改密 vs 重置）。德语定稿分别
`Neues Passwort bestätigen`（Woo 德语习惯，改密语境）与
`Neues Passwort wiederholen`（重置语境）—— 允许分叉，因为 EN 侧本就分叉，
且两页不同屏不同时机出现。

## 11. 未列入本轮的既有文案（复核确认不动）

- 登录失败/拒绝登录失败行、pending/restricted 正文、注册卡副文案与三步标题、
  Overview/Inquiries/Documents/Saved solutions/Company/Account details 菜单名、
  空态文案、`Saved on`、`View all`、`Browse products`、`Sign in or register`：
  全部走既有 .po 条目，本轮只换承载它们的卡片与列表结构。
