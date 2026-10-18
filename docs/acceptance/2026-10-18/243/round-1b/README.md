# #243 · 评审第 1 轮之二：经 #246 的一份记录（PR #290 合并后）

实例 g243；分支重放到含 #290（#246）的 origin/main。对应评审第 1–3、5 条（第 4 条已在第 1 轮完成，这里按新链路重测）。

| 条 | 处理 | 证据 |
|---|---|---|
| 1 | 不另建记录：Genie 的交接是"经 Genie 来的联系留言"，进 #246 的联系记录 | 见第 2 条 |
| 2 | `ContactRequest` 以过滤器 `linker_tools_genie_contact_team` 交出交接；`Linker\Commerce\Genie\Module::contact()` → `Submission::from_handoff()`（名字可空）→ `Inquiry\Sender::message( $details, [ '_linker_genie_handoff' => … ] )`。团队邮件是 #246 的 `NewInquiryEmail`（仍是内部通知、仍走 `notify_to()`），记录带交接时以"Through Genie"一节代替"Contact form"一行，含原因标签、页面、客户最近的消息、整段对话链接、Lösungsentwurf 行与一个工作日承诺；#246 的邮件带得下这些，`Genie\ContactEmail` 与其模板删除 | `GenieContactTest::test_a_guest_request_reaches_the_team_with_the_whole_hand_off`：一条记录（`created_via=linker_contact`、来源 `contact`、客户留言 = 最后一句、交接在 meta、页面语言 `de_DE_formal`）+ 队列里团队一行（To 内部、Bcc、内部 From、Reply-to 访客、Genie 一节齐全、无"Contact form"）+ 回执一行（To 访客）；`NotificationRoutingTest::test_genie_contact_notification_routing`（默认与自定义内部发件人）；邮件样本 `team-mail-through-genie.html` |
| 3 | 访客得到与联系表单一样的回执（#246 的 `InquiryReceivedEmail`），受站点回执日上限（10）约束：超过时只拦回执，记录与团队邮件照发，卡与历史里的卡照实说"We have not sent a confirmation email."（#246 的原句）；访客勾选 #246 的同意句，未勾选 400、不记录 | `GenieContactTest::test_over_the_receipt_cap_the_team_gets_it_and_the_card_says_no_receipt`、`::test_a_guest_without_consent_is_refused`；`ContactCard.test.tsx`（同意、回执缺省、拒绝原因）；e2e `over the receipt cap the card says so`，截图 `screens/*-no-receipt.png` |
| 4 | 已发出的卡留在历史里，下一轮与重载后都在、只一张；`contacts` 带 `receipt` | `App.test.tsx`、`ProxyTest`；e2e 截图 `screens/*-after.png`、`*-reload.png` |
| 5 | 规格 13"转人工"改写为上述链路，规格 11 内部通知表改为"联系表单留言（含经 Genie 来的）" | diff |

e2e（`just e2e g243 specs/genie-contact.spec.ts`）**10/10**：EN/DE × 访客/已登录 × 1440/390（卡、发出、1440 的下一轮与重载）+ 回执上限两例；每例断言本地 spool 里有 #246 的团队邮件与回执各一封（本实例开着测试收件改写，见邮件样本注释）。集成：commerce 全套 133 例通过（Genie 与路由 35 例 338 断言，连跑两次一致，回执与联系计数的行原样还原）；tools 集成全套通过。

文案：卡上新出现的三句全部沿用 #246 已评审的措辞与译文，团队邮件 Genie 一节两句，记录见 `../copy-review.md` 末节"补记"。

`.mo` 与 main 对比（`../round-1/mo-compare.py`）：见 `mo-compare.txt`，两个插件 0 丢失、0 改动。
