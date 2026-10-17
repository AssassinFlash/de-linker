# #246 询盘对所有人开放：本地实现证据

> 本页保留首次交回的历史实走和截图。PR #290 第 1 轮修改后的当前接口、最新测试、补拍与像素归因，以 [round-1/README.md](round-1/README.md) 为准。

工作树 `c246`，分支 `feat/246-inquiry-open`，实例 `http://127.0.0.1:9087`。继续使用前一执行会话的改动，逐项核对后保留；没有更改主检出、其他实例、生产、模型通道或账号审批机制。快照来自 `20261018-0059`（线上采集时间 `2026-10-17T17:11:58+00:00`），通过 `just sync c246` 装入；LC `present` 与 WindPress 编译均在该实例完成。

## 完成标准

| 标准 | 结果 | 证据 |
|---|---|---|
| 访客无需登录，姓名与邮箱必填，公司/留言选填，不问国家；产品随询盘保存 | 完成 | 浏览器 EN #7243、DE #7238；[数据库及本地邮件读回](runtime-readback.json)；`OpenInquiryTest` |
| 允许没有产品、只有留言；产品与留言均空时拒绝 | 完成 | 浏览器 DE #7332；`received-message-de-*`、`empty-*`、`error-*`；真实夹具断言 |
| 已登录资料折叠，approved/pending/restricted 均可直接发送，价格权限不变 | 完成 | 实走 #7244/#7245/#7246；`approved-*`、`pending-*`、`restricted-*`；三状态数据提供器 |
| 左表单、右草稿，可改数量，移动端顺排 | 完成 | [访客 EN 桌面](guest-en-1440.jpg)、[访客 DE 手机](guest-de-390.jpg)、`draft-updated-de-*`；Woo 原生数量更新后返回询盘页 |
| 一份询盘一个发送入口，供 #244/#250 调用 | 完成 | `Inquiry\Sender::request(Submission, array $billing = [])` / `message(Submission)`；两扇门共用核心；原生 AJAX/Store API checkout 旁路在写入前拒绝 |
| 联系表单可见组成保持不变，进入同一询盘列表 | 完成 | `OpenInquiryTest::test_contact_message_creates_one_inquiry_without_consuming_the_draft`；联系表单源代码的可见组成未改；像素残差另列 |
| 内部通知继承 TeamEmail，经 notify()/Options 通知路由与 Outbox | 完成 | `test_sender_routes_the_team_mail_and_receipt_through_outbox` 强制入队，断言 To/Bcc 与客户回执分开；实际浏览器邮件仅捕获到本地文件 |
| 回执/感谢页可选注册，同邮箱预填，正确 key 才可附到新账号 | 完成 | `test_account_link_claim_requires_both_the_key_and_the_same_email`；访客成功页截图；不自动创建账号 |
| 蜜罐与签名填写时间拦机器人；失败保留字段、切换语言后提示跟随当前语言 | 完成 | `PublicGuard`、`Handler` 的真实夹具及语言回归测试；`error-en-*`、`error-de-*` |
| EN/DE × 1440/390，含访客/三类账号/展开/空态/错误/成功 | 完成 | 下方截图矩阵；Chrome Computer Use 实走，非 HTML 静态预览 |
| 文案对抗评审，Spec/Standards 全量评审 | 完成 | [文案初稿、意见与定稿](copy-review.md)、[双评审与修复](review.md) |
| 全页像素零差异门 | **未完成** | [原始计数](pixel-comparison.json)、`contact-diff-*`；表单区域局部计数不代表全页通过，详见视觉记录 |
| 线上实走、真实投递、部署读回 | **未执行：执行会话禁生产写入** | 由 Claude 部署后按 #237 路径验收；本地邮件全部到文件，未实发 |

## 可重复验证

```bash
just sync c246
just wp c246 linker-commerce present --allow-stale --user=1
just wp c246 eval '(new \Linker\Commerce\Presentation\WindPressVolume())->install();'
just windpress-compile c246
just check
just test
cd plugins/linker-commerce
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c246/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit -c phpunit.integration.xml.dist
```

最终命令与结果见 [checks.txt](checks.txt)。最后一次 fetch 带入 `fa4f323a`（#227 后台账号审核）；手工合并保留上游 Accounts 入口和本票共享询盘入口，重新生成语言文件并保留全部 793 个上游词条及本票 25 个词条。合并后另存 `post-rebase-approved-{en,de}-{1440,390}.jpg`、`post-rebase-received-de-*` 与 [再次实发到本地文件的读回](post-rebase-readback.json)。像素对照属于合入该后台变更前的快照，最终全页门仍为未完成。集成套件真实写入临时用户、Woo 产品/订单及 Outbox，然后恢复选项、会话与邮件队列；9 个需另行指定产品 HTTP 夹具站点的既有测试跳过，#246 新增测试无跳过。`just test` 的单元配置本身跳过真实 WordPress 集成测试，故单独执行上述集成命令。

浏览器夹具（仅本地，随机密码不输出）可重建：

```bash
just wp c246 eval-file "$PWD/docs/acceptance/2026-10-18/246/browser-fixtures.php" setup
just login c246 --user linker246-approved
# 其余：linker246-pending、linker246-restricted
# 证据读回后，清理本票测试用户与其测试询盘：
just wp c246 eval-file "$PWD/docs/acceptance/2026-10-18/246/browser-fixtures.php" cleanup
```

真实浏览器提交的两封邮件均由本地 mail spool 捕获：客户回执到虚构的 `example.test`，团队通知读 #221 的配置，当前快照 To 为 `sales@sunriverinverter.com`、Bcc 为 `chester@de-linker.com`；无实发。队列路由的正确性以 PHPUnit Outbox 数据断言为准。读回 JSON 只保留测试地址、订单事实与邮件头，去掉订单 key、登录链接和邮件正文。

## 截图矩阵

每个前缀都有 `-1440.jpg` 与 `-390.jpg`：

| 状态 | EN 前缀 | DE 前缀 |
|---|---|---|
| 访客带产品 | `guest-en` | `guest-de` |
| 已批准，资料折叠 | `approved-en` | `approved-de` |
| 已批准，展开编辑 | `approved-expanded-en` | `approved-expanded-de` |
| 待审 | `pending-en` | `pending-de` |
| 受限 | `restricted-en` | `restricted-de` |
| 空草稿 | `empty-en` | `empty-de` |
| 验证错误、保留资料 | `error-en` | `error-de` |
| 访客成功 | `received-en` | `received-de` |

补充：`received-approved-de`、`received-pending-de`、`received-restricted-de`、`received-message-de`、`draft-updated-de`。截图使用合成测试资料；像素对照另以同机同 Chrome 的 PNG 保存。

## 视觉记录与变更台账

询盘页面主体按业主 2026-10-17 裁定采用左表单、右 Lösungsentwurf；字段、卡片、按钮和色彩沿用线上商务设计。组合在 LC HTML，样式在 WindPress 卷，数据片段不带内联样式。以下是本票预期变更，供评审确认：

1. 访客与待审/受限产品按钮可加入草稿，不再先要求登录；价格门保持。
2. 请求页减为最少回复资料和开放留言，已登录资料折叠；标题/按钮改为准确的询盘动作。
3. 感谢卡在桌面也显示（修复原有仅移动端显示）；增加可选注册入口。无价产品与无产品留言不显示误导性的 €0 总额。
4. 待审页、注册回执、限制邮件和登录说明同步说明询盘已开放，审批影响净价。
5. 联系表单仅增加不可见反机器人字段，提交管道合并；可见组成未改。

联系页对照：`live-contact-{en,de}-{1440,390}.png` / `local-contact-…`。视口为 1440×1000 与 390×844；等字体与可见图片完成、禁动画与过渡、滚动为 0 后拍摄；具体 PNG 尺寸与几何见 JSON。临时截图样式在重新加载后撤销，视口也恢复。区域坐标在 [contact-form-geometry.json](contact-form-geometry.json)，精确 RGB 逐像素比较，无容差、无批准掩膜。最终表单比较区域 EN1440 为 57，其余三组为 0；全页分别为 133967、431、4496、393 个不同像素。移除后台工具栏后的计数分别为 129712、38、0、0，英语图片/局部呈现仍有残差。**本记录不将其排除为已批准动态区，不声称全页 PASS，也没有为消差改动不属于本票的图像或页头。** 原图与差异图可供 Claude 定位与决定是否通过视觉门。可用 `python3 docs/acceptance/2026-10-18/246/compare.py` 重算，依赖已安装的 Pillow。

## 边界、交接与回滚

#244 负责对话摘要，#250 负责 Genie 确认卡；两者调用这里的 Sender，不另建询盘写入。两步注册表单的范围属于 #225，本票只加回执注册链接与安全附单。#237 负责上线后按业主路径实走。付款、签发 PI、后续履约、模型与线上部署不在本票。

没有部署、合并或写生产。本地变更随分支提交；交接后如需撤销，可在集成分支反向撤销本票提交并按常规 present/编译重新呈现。浏览器与 PHPUnit 夹具的清理只作用于 c246，不改生产或其他实例。
