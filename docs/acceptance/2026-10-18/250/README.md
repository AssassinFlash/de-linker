# #250 · 对话内询盘确认卡

依据：[票 #250](https://github.com/AssassinFlash/de-linker/issues/250)、`docs/specs/13-genie.md` 目标第 5 条（验收 A8）、
AGENTS.md §5（三件套、像素门、测试邮件纪律）；设计依据 `docs/research/2026-10-17-ai-assistants/`（§0.2、CN §5.1、INTL §5.2）。
文案评审：[copy-review.md](copy-review.md)。

## 链路

```text
客户在对话里说"发询盘"
  → 服务：模型可写 send_inquiry 动作（schema.ActionName）；客户明说时 inquiry.decide 自己补上
      · 模型文字永远不发送；说"已发送"的话被 ground._no_sent_claim 拒（重答一次，仍犯则兜底模板）
  → 壳：InquiryCard（src/genie/components/InquiryCard.tsx）挂在该回答之后
      GET linker-ai/v1/genie/inquiry（includes/Genie/InquiryRequest.php）
        · 解决方案草稿的逐行（Woo 购物车，与询盘页同一取法：get_price_html，价格门生效；DE 卡取德语行）
        · 留言 = #244 摘要的 note（可改），摘要正文可展开、默认附上
        · 访客字段 = 询盘页同项（Name / Reply email / Company 选填 / 同意句）；已登录客户从账号来
        · 缺内容（草稿与留言都空）→ 只给询盘页链接，不编造
        · 已发出且此后未说话 → 直接给已发出态（编号、状态、回执）
  → 客户点 Send inquiry
      POST 同一路由：FormGuard（蜜罐 + 签名起始时间，限额 3/小时、全站 10/天）
        · lines digest 与草稿一致才是这次确认（草稿变了 → 409，卡重读）
        · filter linker_tools_genie_inquiry_send → linker-commerce\Genie\Module::inquiry()
          → Inquiry\Sender::request($details, [], $summary) —— 与询盘页同一条 Woo 管线
            （Woo 订单、Proforma 网关、inquiry-received、团队邮件、回执上限）
        · 摘要在订单 meta `_linker_genie_summary`（关掉则 false，不存）；团队邮件照 #244 模板显示
        · 会话文章 meta `linker_genie_inquiry`（订单号、消息数、回执，一人一条）
  → 同一对话：InquirySent 显示 "Inquiry #… · Inquiry received"、承诺与查看链接（从记录读）
  → 刷新/后续轮次：会话读取路由返回 inquiries[]，已发出的卡留在原回答之后
```

A8 的两半：**结构**——模型没有任何写询盘的 ability，唯一写入口是这条 POST；**文字**——`ground._no_sent_claim`
拒绝"已发送/已提交"的模型句子（EN/DE，见 `services/genie/tests/test_inquiry.py`）。

## 代码

| 层 | 文件 |
|---|---|
| 服务 | `services/genie/src/linker_genie/inquiry.py`（短语表、`decide`）、`schema.py`（`send_inquiry`）、`ground.py`（`_no_sent_claim`）、`app.py`（回答后加动作）、`prompts/{en,de}/system.md`、`tests/test_inquiry.py`（41 项） |
| 路由 | `plugins/linker-tools/includes/Genie/InquiryRequest.php`（GET/POST、摘要、草稿行、已发出态）、`Plugin.php`、`linker-tools.php`、`Entries.php`（`data-inquiry-url`）、`Proxy.php`（历史 `inquiries`） |
| 发送 | `plugins/linker-commerce/includes/Genie/Module.php`（`INQUIRY_FILTER`、`INQUIRY_PAGE_FILTER`）、`includes/Inquiry/Sender.php`（`$summary` 参数）、`ReceiptLimit` 既有 |
| 摘要 | `plugins/linker-tools/includes/Genie/InquirySummary.php`（缓存键加语言——同一会话在 EN/DE 两页各得各的摘要） |
| 壳 | `src/genie/components/InquiryCard.tsx`（卡与已发出态）、`src/genie/api/inquiry.ts`、`src/genie/genie.css`（末节，全部取既有 token）、`App.tsx`、`config.ts`、`api/turn.ts` |
| 文案 | `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`（30 条，JED 由 `just i18n-tools` 生成） |
| 测试 | `plugins/linker-commerce/tests/php/Integration/GenieInquiryTest.php`（11 项）、`InquiryCard.test.tsx`（8 项）、`App.test.tsx`（2 项）、`tests/e2e/specs/genie-inquiry.spec.ts`（4 项：EN/DE × 1440/390） |

## 已验证

- 服务：`pytest` **980 passed**（含 `test_inquiry.py` 41 项）、`ruff check`、`ruff format --check`、`mypy` 全绿。
- PHP：linker-tools 单元 **234 passed**、PHPCS 干净、PHPStan 无错；linker-commerce 集成 **146 passed（9 skipped）**，含
  `GenieInquiryTest` 11 项：访客发送与逐行一致（订单 7572 的现场对照见下）、摘要开关、访客必填、草稿变更 409、
  价格变动 409（确认的是卡上那一行）、
  蜂蜜罐与伪造起始时间不写任何记录（A8 的"无点击不产生询盘"）、已登录账号、重复发送只一条、空草稿转询盘页、回执上限。
  行 digest 覆盖商品、数量、价格行与库存状态：卡展示后其中任何一项变了，旧确认作废（研究 §5.1 第 4 点）。
- JS：`vitest` **188 passed**、ESLint 0 warning、Prettier 干净、`tsc --noEmit` 干净、`npm run build` 通过。
- i18n：`i18n-coverage` clean（PO 无缺口、JED 与 make-json 逐字节一致）、`msgfmt --check` 通过。
- e2e：`tests/e2e/specs/genie-inquiry.spec.ts` EN/DE × 1440/390 全绿（真实模型、真实实例）。每例：问产品 → 加入草稿 →
  说"发询盘" → 卡出现（行、承诺、询盘页链接）→ 访客填三项 → 发送 → 已发出态显示记录编号与状态 → 团队邮件与回执各一封、
  收件人全部被测试模式改写成 tester → 刷新后已发出的卡仍在。截图在 [screens/](screens/)。
- 手工走查（实例 i250，快照 2026-10-18 04:39 UTC）：EN 从首页 dock 走通，订单 **#7572**；DE 从 `/de/` 走通，订单 **#7574**。
  订单读回：`created_via=checkout`、`payment_method=linker_proforma`、`_linker_inquiry_source=proforma`、
  `status=inquiry-received`、行 4107×1（与卡一致）、留言与卡一致、摘要 meta 与卡显示一致、回执未跳过。
  两封邮件都在实例 spool，`To:` 只有 tester250@example.test；团队邮件含 "Conversation with Genie" 与卡上的摘要。
  测试模式在走查前打开（`linker_commerce_test_mail_to`），实例为本地栈（邮件只落 spool）。
- 视觉：1440 的卡完整可见（工作区 768 px 列），390 的卡按手机宽度单列（商品行价格换行、字段竖排、按钮与链接同排）。
  截图见 `screens/`：`en-1440-offer/sent/reload`、`en-390-offer/offer-bottom/sent/reload`、`de-1440-…`、`de-390-…`。
  与既有 Genie 卡（联系卡）同一表面、同一组 token；没有裸样式面。

## 未验证（合并前必须知道）

1. **线上实走**：本票只在本地实例走通；线上安装与线上实走属 #237 的验收，未做（也不得在本票部署）。
2. **独立文案评审**：见 `copy-review.md` 末节——同一会话做了对抗复核，没有独立代理。若要求独立评审，合并前补一轮。
3. **读屏**：没有屏幕阅读器实测；卡是整块 `aria-live="polite"`（沿用 #243），发送后的状态变化预期播报。
4. **像素门**：工具页（Genie）不受像素门约束（业主 2026-10-10 裁定），本票只做 Genie 卡与对话内状态；营销页/产品页未改，
   无 parity 对照需要。
5. **摘要正文的语种**：已修（缓存键含语言，REST 路由按卡的语言切 locale），由现场 DE 卡复核；模型摘要措辞（第三人称）
   是 #244 的提示词行为，不在本票改动，客户可改留言或关掉摘要。

## 需要业主/协调方决定

- 文案独立评审是否必须由另一个代理重做（本会话只能做到"第二遍只读复核"）。
- 卡上留言的默认值是 #244 的摘要 note（模型写的第三人称句子，例如 "Der Kunde bittet darum …"）。它可编辑，也可以关摘要后自己写。
  如果业主要求默认值是客户自己的最后一句话（逐字），那是对 #244 预填规则的一处改动，需要一次裁定（本票未改，以免与询盘页分叉）。
