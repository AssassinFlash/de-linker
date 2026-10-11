# #73 账号审批三态 · 客户可见文案对抗评审记录

规则（AGENTS.md §2 2026-10-09/10-11 裁定 + linker-copywriting Hard Stops，邮件主题属公开面）：EN 先行、DE 独立撰写非翻译；Sie 体、de_DE_formal；禁 em/en dash（新写文案）、禁目录（catalogue）等域外词、禁帮助台腔与客诉防御；术语锁 `.po`/线上：**Nettopreis / Partner-Anmeldung（Anmeldung） / Lösungsentwurf / Proformarechnung**。每处：初稿 → 评审意见 → 定稿。定稿即本票代码里的字面量（`Approval.php`、`ApprovalAdmin.php`、`templates/emails/linker-approval-*.php`、`LoginGate.php`、`PriceDisplay.php`）。渲染证据：`docs/acceptance/2026-10-11/73/email-render/*.eml`（EN/DE × 三动作，真实实例 `wp eval` 触发、本地隔离捕获）。

## 1. 登录拦截消息（拒绝客户尝试登录时，wp-login 与 My Account 表单）

- EN 初稿：`This account is not approved for sign-in. We have emailed you the reason. Write to sales@de-linker.com and we will look at it again.`
  评审：三短句、状态+原因去向+出路，无防御腔；"we will look at it again" 是三动作可逆的事实承诺（票面裁定），可保留。登录错误行宜短，但原因去向是票面要求的"显示状态与原因方向"，三句都承担义务。接受初稿。**定稿**：同初稿。
- DE 初稿：`Dieses Konto ist nicht zur Anmeldung freigegeben. Den Grund haben wir Ihnen per E-Mail geschickt. Schreiben Sie an sales@de-linker.com, wir sehen uns Ihr Konto erneut an.`
  评审：独立撰写非翻译；"nicht zur Anmeldung freigegeben" 用 Anmeldung（术语锁的词根）；第三句逗号连接改为分号更稳（德语两个主句以逗号相连是口语腔）。**定稿**：`Dieses Konto ist nicht zur Anmeldung freigegeben. Den Grund haben wir Ihnen per E-Mail geschickt. Schreiben Sie an sales@de-linker.com; wir sehen uns Ihr Konto erneut an.`

## 2. 状态标签（后台列/资料页/团队邮件值，staff 面=功能性 UI 文本）

- EN 定稿：`Pending review` / `Approved` / `Restricted` / `Rejected` / `No decision yet`。
- DE 初稿：`In Prüfung` / `Freigegeben` / `Eingeschränkt` / `Abgelehnt` / `Noch nicht entschieden`。
  评审：Freigabe 词族与 .po 既有串一致（`Freigeben`/`Preise nach Freigabe`）；"In Prüfung" 是德语后台惯用语；无名词堆砌。接受初稿。**定稿**：同初稿。

## 3. 资料页 Linker 区块（staff 面）

- EN/DE 定稿：`Linker approval`/`Linker-Freigabe`、`Approval`/`Freigabe`、`Approve`/`Freigeben`、`Restrict`/`Einschränken`、`Reject`/`Ablehnen`、`Reason`/`Grund`、`Last change %1$s by %2$s.`/`Letzte Änderung %1$s durch %2$s.`、`Required for restrict and reject; the customer reads it in the email about the change.`/`Pflicht beim Einschränken und Ablehnen; der Kunde liest ihn in der E-Mail zur Änderung.`
  评审：按钮用动词不定式（德语按钮惯例）；"der Kunde liest **ihn**"（Grund，阳性）指代正确；三条 wp_die 消息（权限 403、动作 400、缺原因 400）为功能性文本直述。接受初稿，无修订。

## 4. ②通过邮件（客户，`linker-approval-approved.php`）

- 主题 EN 初稿：`Your partner account is approved`。评审：公开面、平实 B2B、无 hype、无时间承诺。接受。**定稿**：同初稿。
- 主题 DE 初稿（独立撰写）：`Ihr Partner-Konto ist freigegeben`。评审：与 Freigabe 词族一致；德语主题不复制英文语序（英 "is approved" → 德状态被动 "ist freigegeben"）。接受。**定稿**：同初稿。
- 标题 EN/DE：`Partner account approved` / `Partner-Konto freigegeben`（主题的名词化短版）。接受。
- 正文 EN 初稿：`Your Linker partner account is approved.` + `Net prices are now shown with every product. Add the systems you need to your solution draft, and request the Proforma when the draft is ready.`
  评审：Hard Stop 9 Actor——"Add …" 是祈使句，但这是状态变更后告知"现在可以做什么"的事务性说明（先例：访客 gate 的 "Register, add your systems, and return here"），非把工作派给客户；术语锁全部就位（Net prices→Nettopreise、solution draft→Lösungsentwurf、Proforma）。接受初稿。
- 正文 DE 初稿（独立撰写）：`Ihr Partner-Konto bei Linker ist freigegeben.` + `Die Nettopreise werden jetzt zu jedem Produkt angezeigt. Legen Sie die benötigten Systeme in Ihren Lösungsentwurf und fordern Sie die Proformarechnung an, wenn er fertig ist.`
  评审："bei Linker" 仿 Genie 定名的 von-Linker 结构，避免 "Linker-Partnerkonto" 巨型复合词；"wenn er fertig ist"（der Entwurf）指代正确；无 werden-Futur 冗余。接受。**定稿**：同初稿。
- 链接：`Browse products`/`Zu den Produkten`（.po 既有串复用）、`Your account`/`Ihr Konto`（新串）。评审：复用既有串是术语一致性的要求。接受。

## 5. ③限制邮件（客户，重头：诚实且留住关系）

- 主题 EN 初稿：`Your partner account access is limited`。评审：直述不委婉（票面要求诚实）。接受。**定稿**：同初稿。
- 主题 DE 初稿：`Der Zugriff Ihres Partner-Kontos ist derzeit eingeschränkt`。评审：独立撰写；"derzeit" 承载"可逆"的方向而不许诺时间。接受。**定稿**：同初稿。
- 正文 EN 初稿：`Your partner account has been limited for now.` + `You can keep browsing the products, and you can reach us any time at sales@de-linker.com. Net prices and the Proforma request are paused while the account is limited.` + `Our reason: {原因}` + `Write to sales@de-linker.com and we will look at your account again.`
  评审①："catalogue" 一词违禁（域语言），初稿曾用，改为 "the products"。评审②：sales@ 在一封短信里出现两次，第二次改 "Write to us"（Reply-To 已带邮箱）。评审③："Our reason:" 是 Linker 作主语、own the decision，符合 Brand Rule 7（不自辩、只陈述）。**定稿**：P4 改 `Write to us and we will look at your account again.`，其余同初稿（含 P2 的修订）。
- 正文 DE 定稿（独立撰写）：`Ihr Partner-Konto ist vorerst eingeschränkt.` + `Sie können die Produkte weiterhin ansehen und uns jederzeit unter sales@de-linker.com erreichen. Nettopreise und Proforma-Anfrage sind pausiert, solange das Konto eingeschränkt ist.` + `Unser Grund: {原因}` + `Schreiben Sie uns, und wir sehen uns Ihr Konto erneut an.`
  评审："vorerst" 对应 for-now 的可逆方向；Nettopreis/Proforma-Anfrage 术语锁就位；无 "nicht…sondern"。

## 6. ④拒绝邮件（客户）

- 主题 EN：`Your partner account was not approved`。DE：`Ihr Partner-Konto wurde nicht freigegeben`。评审：被动直述，无道歉模板腔。接受。
- 正文 EN 初稿：`We cannot approve your Linker partner account. Signing in therefore stays closed.` + `Our reason: {原因}` + `If something about this was unclear, write to sales@de-linker.com.`
  评审①：首句 Linker 作主语、own the decision ✓。评审②：第三句 "was unclear" 预设客户困惑，居高临下，改中性提问邀请（允许的邀请接触 CTA）。**定稿**：第三句改 `If you have questions, write to sales@de-linker.com.`
- 正文 DE 定稿：`Wir können Ihr Partner-Konto bei Linker nicht freigeben. Die Anmeldung bleibt deshalb geschlossen.` + `Unser Grund: {原因}` + `Bei Fragen schreiben Sie an sales@de-linker.com.`

## 7. 请求页 gate（pending / restricted 登录后视图，`LoginGate::approval_gate`）

- pending EN 初稿：H1 `Your account is under review`；P1 `We are reviewing your partner account. Net prices and the Proforma request open as soon as it is approved — we will email you.`；P2 `Until then, browse the catalogue and write to sales@de-linker.com with any question.`
  评审①：em dash 违禁（新写文案），改逗号句。评审②："catalogue" 违禁，改 "the products"。**定稿**：H1 同；P1 `We are reviewing your partner account. Net prices and the Proforma request open as soon as it is approved, and we will email you.`；P2 `Until then, browse the products and write to sales@de-linker.com with any question.`
- pending DE 定稿：H1 `Ihr Konto wird geprüft`；P1 `Wir prüfen Ihr Partner-Konto. Nettopreise und die Proforma-Anfrage öffnen sich mit der Freigabe; wir melden uns per E-Mail.`；P2 `Bis dahin können Sie die Produkte ansehen und Ihre Fragen an sales@de-linker.com schreiben.`
- restricted EN 初稿：H1 `Access currently limited`；P1 `Your partner account is limited for now: the catalogue and your questions stay open, net prices and the Proforma request are paused.`；原因行 `Our reason: {原因}`；P2 `Write to sales@de-linker.com and we will look at your account again.`
  评审："catalogue" 违禁，改 "the products"。**定稿**：P1 `Your partner account is limited for now: the products and your questions stay open, net prices and the Proforma request are paused.`，其余同初稿。
- restricted DE 定稿：H1 `Zugriff derzeit eingeschränkt`；P1 `Ihr Partner-Konto ist vorerst eingeschränkt: Produkte und Ihre Fragen bleiben offen, Nettopreise und Proforma-Anfrage sind pausiert.`；`Unser Grund: {原因}`；`Schreiben Sie an sales@de-linker.com, und wir sehen uns Ihr Konto erneut an.`

## 8. 价格位标签（pending / restricted 看到的价格文本，`PriceDisplay::label`）

- EN 初稿：`Prices after approval`（pending）/ `Not available for your account`（restricted）。
- DE 初稿：`Preise nach Freigabe` / `Für Ihr Konto nicht verfügbar`。
  评审：价格位只有一行之地，两个状态分开措辞是诚实要求（pending 是"还没到"，restricted 是"不可用"）；Freigabe 词族一致。接受初稿。**定稿**：同初稿。

## 9. ①团队通知改造（`linker-new-customer.php`）

- 改动：行数据表加 `Approval` / `Freigabe` 行，值固定 `Pending review` / `In Prüfung`（注册即 pending）；"Open the customer"（既有串，链到资料页即审批区块所在）保持不动——票面"附后台直达链接"由该既有链接承载。
- 评审：团队邮件是站点默认语言（既有设计），本行让通知可执行（知道该去批准）；无客户可见面。接受，无修订。

## 10. Hard Stops 核对表（对 §1–§9 的定稿逐条）

- [x] HS1 借用信誉：无（无 proven/tier-1/authorised 词）。
- [x] HS3 防御性否定：拒绝邮件首句是决定陈述，非品类自辩。
- [x] HS4 服务强化词：无 direct/official/guaranteed。
- [x] HS5 虚假时限：无新增时限（"one business day" 未用于审批邮件）。
- [x] HS7 公开面词典：subject 全部平实 B2B；无 RMA/BOM/Incoterms 级深词。
- [x] HS9 Actor/Future/Weight/Duration：祈使句仅用于事务性 how-to（§4 评审记录）；无编造客户轨迹；原因段按票面为必须承载的信息。
- [x] 人类化：新写文案零 em/en dash；DE 无 werden-Futur 冗余、无 "nicht…sondern"、Sie 体；EN 无 slogan 公式。
- [x] 术语锁：Nettopreis（§5/§7/§8 DE）、Anmeldung（§1 DE）、Lösungsentwurf（§4 DE）、Proformarechnung/Proforma-Anfrage（§4/§5/§7 DE）全部按 `.po` 既有词族。

## 11. 渲染证据

`docs/acceptance/2026-10-11/73/email-render/`：EN/DE × approved/restricted/rejected 六封 `.eml`，真实实例同进程连发（EN 客户→DE 客户），主题与正文逐封核对为对应语言。过程发现并修复一个真实缺陷（`CustomerApprovalEmail::get_subject()/get_heading()` 重读 settings——Woo 的 settings 缓存会把同请求第一次渲染的语言冻结给后续客户）；修复前后对照见本目录 Git 历史（修复前 DE 客户收到 EN 主题 + DE 正文）。
