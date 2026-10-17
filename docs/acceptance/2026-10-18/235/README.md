# #235 Genie · 会话全部保留 — 验收记录（含评审第 1 轮的修改）

实例：g235（`just sync g235`，快照 20261018-0252；`just serve g235`，真实 Genie：deepseek-flash 官方通道）。
截图由 `tests/e2e/specs/genie-sessions.spec.ts` 在真实浏览器里按业主路径拍下
（`LINKER_E2E_SHOTS=… just e2e g235 specs/genie-sessions.spec.ts`，EN/DE × 1440/390 四轮全绿）。
截图编号：1 新建不收侧栏 · 2 访客三个会话 · 3 切回 · 3b dock 也列出 · 4 邮箱表单 · 5 确认链接已发 ·
6 确认邮件（1440）· 7 打开链接后的页面 · 8 对话邮件（1440，带产品）· 9 登录后三个 · 10 另一设备三个 ·
11 删除确认 · 12 删除后。

## 完成标准 → 证据

| 完成标准 | 证据 |
|---|---|
| 访客连开三个会话都在列表里 | `*-2-guest-three.png`；集成 `ConversationListTest::test_a_guest_keeps_every_conversation_of_this_browser` |
| 可切回；列表按最近活动 | `*-3-switched-back.png`、`*-1440-3b-dock-three.png`；`test_continuing_an_old_conversation_moves_it_to_the_top` |
| 新建不收起面板 | `*-1440-1-new-keeps-rail.png`；vitest `a new conversation and a switch keep the wide workspace rail open`；手机浮层 `on a phone the rail overlay folds once a conversation is picked` |
| 登录后三个都在账户下，不重排，换新钥匙 | `*-9-signed-in-three.png`；`test_signing_in_moves_every_conversation_into_the_account`（顺序与活动时间不变、钥匙更换）、`test_a_new_account_takes_the_browsers_conversations` |
| 换设备登录也在 | `*-10-other-device-three.png`；同上集成测试 |
| 退出登录换新访客钥匙；User Switching 不认领 | `test_signing_out_starts_a_new_guest_key`、`test_user_switching_claims_nothing` |
| 可清除（A9） | `*-11-delete-confirm.png` → `*-12-deleted.png`；`test_clearing_a_conversation_deletes_it`、`ConversationRoutesTest::test_delete_clears_only_the_visitors_own_conversation` |
| 发到自己邮箱（A12）· 访客先确认地址 | `*-4`…`*-8`；e2e：确认邮件只到 tester、不含对话文字；点链接前没有对话邮件；点链接后恰好一封对话邮件；集成 `test_a_guest_confirms_the_address_before_the_conversation_goes`（一次性）、`test_an_expired_link_sends_nothing` |
| 机器人防护 | `test_the_bot_guard_sends_nothing`（蜜罐、太快、伪造、过期的起始时间：都回 202，什么都不发、不生成链接） |
| 每日上限、不排队 | `test_at_the_daily_cap_nothing_is_sent_or_queued`（429 `capped`，`wp_mail()` 一次都没被调用）；每连接上限 `test_the_route_refuses_what_it_must_not_send` |
| 原子限额 | `RateLimitTest::test_parallel_requests_cannot_pass_the_limit`（8 个进程同时取、上限 3：恰好 3 个通过）、`test_limiters_do_not_purge_each_other` |
| 邮件保留产品（Spec 1） | `*-1440-8-conversation-message.png`；`test_each_answer_keeps_its_products`；commerce `GenieConversationEmailTest`（德语产品名、"Modell H2-10K-T3"、德语产品页链接） |
| 发件人（Spec 2） | commerce `GenieConversationEmailTest`：Outbox 行含 `From: Linker <sales@de-linker.com>` 与 `Reply-to: Linker <sales@de-linker.com>`，无 Bcc |
| 浏览器端存储与服务端记录的关系写进 13-genie.md | §C "会话全部保留（#235…）" 与变更记录 |
| 文案对抗评审 | `copy-review.md`（第 1、2 轮） |
| i18n：德语 JS 字符串进 .po、JSON 由 make-json 生成 | `i18n-proof.txt`（main 上 48 条一条不少、译文零改动，新增 18 条） |

测试邮件纪律：本地实例的邮件只写入文件（`~/de-linker-local/g235/mail/`），e2e 每轮只发 tester 一封确认与一封对话；
集成测试在 `pre_wp_mail` 截停或用 Outbox 队列行断言，不实发。邮件里的域名本地显示 127.0.0.1（`home_url()` 的主机名），线上即 de-linker.com。
