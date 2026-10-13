# #138 注册确认邮件 · 客户可见文案对抗评审记录

规则（`/Users/chesterjohn/Documents/de-linker/AGENTS.md` §2 2026-10-11 裁定 + §3 用词 + linker-copywriting Hard Stops，邮件主题属公开面）：EN 先行、DE 独立撰写非翻译；Sie 体、`de_DE_formal`；禁 em/en dash（新写文案）、禁目录（catalogue）、禁帮助台腔与客诉防御。术语锁本插件 `.po`：**Anmeldung = 登录，Registrierung / registrieren = 注册**。每处：初稿 → 评审意见 → 定稿。定稿即本票代码与 `.po` 里的字面量（`RegistrationReceivedEmail.php`、`templates/emails/linker-registration-received.php`、`languages/linker-commerce-de_DE_formal.po`）。正文后两段与链接复用 #73 审核页已定稿的串，不重写。渲染证据：`docs/acceptance/2026-10-13/138/email-render/*.eml`。

## 1. 主题（公开面）

- EN 初稿：`We received your partner registration`。
  评审：Linker 作主语，直述收到的是注册，不是登录；无时限、无 hype、无 borrowed credibility。接受。**定稿**：同初稿。
- DE 初稿（独立撰写）：`Wir haben Ihre Partner-Anmeldung erhalten`。
  评审：词族撞车。本插件 `.po` 里 Anmeldung 是登录义：`Preise nach Anmeldung`（`linker-commerce-de_DE_formal.po:954`）、`Dieses Konto ist nicht zur Anmeldung freigegeben`（`:1526`）、`Die Anmeldung bleibt deshalb geschlossen`（`:2467`，#73 拒绝邮件定稿，指登录被关）。注册义走另一词族：`Registrieren`（`:2236`）、`Noch kein Konto? Registrieren`（`:944`）、`Registriert am %s`（`:1767`）、Woo 欢迎信改写 `vielen Dank für die Registrierung bei %1$s`（`:2400`）。主题说的是注册已收到，用 Anmeldung 会读成"登录已收到"。不保留。**定稿**：`Wir haben Ihre Partner-Registrierung erhalten`。

## 2. 标题（邮件内 H1，主题的短版）

- EN 初稿：`Registration received`。评审：后台邮件名与客户标题同一句，事务性、无口号。接受。**定稿**：同初稿。
- DE 初稿：`Anmeldung eingegangen`。
  评审：同一撞车。询盘状态已有 `Anfrage eingegangen`（`.po:22`），"eingegangen" 是收到义，主语必须是注册。**定稿**：`Registrierung eingegangen`。

## 3. 正文首句

- EN 初稿：`We received your partner registration.`。评审：与主题同句加句号，邮件打开即可核对主题没有改口。接受。**定稿**：同初稿。
- DE 初稿：`Wir haben Ihre Partner-Anmeldung erhalten.`。评审：与 §1 同一词族错误，句号版跟着改。**定稿**：`Wir haben Ihre Partner-Registrierung erhalten.`。

## 4. 正文其余（复用 #73 审核页定稿，不新写）

`templates/emails/linker-registration-received.php:24-27` 的后两段与链接是 #73 已定稿串，本票不改字面量：

- EN：`We are reviewing your partner account. Net prices and the Proforma request open as soon as it is approved, and we will email you.` / `Until then, browse the products and write to sales@de-linker.com with any question.` / `Browse products`。
- DE：`Wir prüfen Ihr Partner-Konto. Nettopreise und die Proforma-Anfrage öffnen sich mit der Freigabe; wir melden uns per E-Mail.` / `Bis dahin können Sie die Produkte ansehen und Ihre Fragen an sales@de-linker.com schreiben.` / `Zu den Produkten`。

评审：Hard Stop 9 Actor 的祈使只在已过评审的事务说明里；本票新写的三句（主题、标题、首句）没有给客户派活。`Nettopreis` / `Proforma-Anfrage` / `Freigabe` 仍锁在 #73 词族。不把 `Anmeldung` 写进这封信。

## 5. 后台说明（staff 面，非客户主题）

- EN：`Sent to the customer when the account is registered and waiting for review.`。
- DE 已有：`Geht an den Kunden, wenn das Konto registriert ist und auf die Prüfung wartet.`。
  评审：`registriert` 已是注册词族，与本票定稿一致。不改。

## 6. Hard Stops 核对（对本票新写三句）

- [x] HS1 借用信誉：无。
- [x] HS3 防御性否定：无。
- [x] HS4 服务强化词：无 direct / official / guaranteed。
- [x] HS5 虚假时限：无。
- [x] HS7 公开面：主题与标题是平实 B2B，无 RMA / BOM / Incoterms。
- [x] HS9 Actor / Future / Weight / Duration：新写三句只陈述"注册已收到"；不编造客户下一步，不把审核写成整份服务。
- [x] §3 用词：Sie 体；无 "不是…而是…"；无 em/en dash；英德同步。`Anmeldung` 留给登录，`Registrierung` 留给注册。

## 7. 渲染证据

`docs/acceptance/2026-10-13/138/email-render/`：`en-registration-received.eml`、`de-registration-received.eml`。

触发：实例 `pendinggate`（`http://127.0.0.1:8996`，检出即本工作树）。`wp linker-commerce test-mail on --to=chester@de-linker.com` 后，`wp eval` 建两个 customer（`locale` 分别为 `en_US`、`de_DE_formal`），同一进程内先 `do_action( 'linker_commerce_customer_registered', … )` 发 EN、再发 DE。本地隔离把 `wp_mail()` 写成 `~/de-linker-local/pendinggate/mail/*.eml`。核对后 `test-mail off`（选项读回不存在），两个临时用户已删。同一次动作还写出两封团队信 `New customer:`，不归档。

读回：

- EN：`Subject: We received your partner registration`；`lang="en-US"`；H1 `Registration received`；正文三句与 `Browse products` 为定稿。
- DE：`Subject: Wir haben Ihre Partner-Registrierung erhalten`；`lang="de"`；H1 `Registrierung eingegangen`（EN 先发，标题没有被冻成英文，#73 记过的 settings 缓存缺陷没有复发）；正文三句与 `Zu den Produkten` 为定稿。两封正文都没有 `Anmeldung`。
- To 一律 `chester@de-linker.com`（测试邮件纪律）。收件人重写只发生在投递；队列里的原路由由既有 `OutboxTest::test_test_mode_rewrites_at_send_time_only` 断言，本票不重跑。
