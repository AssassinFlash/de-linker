# #288 邮件修正验收

本轮按 [PR #291 第 1 轮评审](https://github.com/AssassinFlash/de-linker/pull/291#issuecomment-6238959144) 的六项决定收敛。生产取证已完成：Hostinger `/usr/sbin/hsendmail -t` 强制信封为 `noreply@srv1798.main-hosting.eu`，设置 PHPMailer Sender 前后 Return-Path、SPF 与收件箱归类均不变。SPF 已通过，de-linker.com 无 DMARC；客户邮件在 QQ 收件箱，sunriver 的垃圾箱判定来自 From 域。内部通知使用 #286 的 sunriver 身份，客户 From 继续遵守业主裁定。证据和规则已替换进 `docs/specs/11-commerce.md` 的 Mail 一节。

第 2 轮的 LC 提取修正、先红后绿门禁与编译 MO 比较见 [round2.md](round2.md)。

## 最终改动

- 删除信封实现、模块钩子与依赖、Options 常量/读取方法、Woo 设置区、三条文案、专用测试及其旧验收截图/文案记录；没有替代信封机制。
- `Options::notify_sender()` 是唯一公开的内部身份 accessor，返回 readonly `Mail\Identity`（name、email）。`TeamEmail`、`TeamMessageEmail`、`Health\Monitor` 使用这一身份，Monitor 注释已更正。
- 保留 `sanitize_prefix` 去首尾连字符、内部发件人集中定义、按邮件 ID 独立的 Reply-To 断言。
- 通知路由按新客户、VAT、询盘、联系留言、摘要、健康告警拆为独立测试；两个原生设置保存行为也各自测试。不再有 health 与其他邮件混用的分支。

## TDD 与本地夹具

沿用本票既有公开边界：Options 读取、Woo 原生设置保存、Outbox 队列及本地邮件输出。Identity 测试先因类不存在而失败（4 个配置用例）；返回值对象并更新五个消费点后通过。无效、空、错误类型配置仍回到内部默认地址，内部 recipient/public mailbox 与 sender 互相独立。

```sh
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c288/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php plugins/linker-commerce/vendor/bin/phpunit \
  -c plugins/linker-commerce/phpunit.integration.xml.dist \
  --filter 'NotificationRoutingTest|MailRetryTest|MailChainTest|HealthMonitorTest'
just check
just test
```

实例仅用 c288（`http://127.0.0.1:9093/`）。`just sync c288` 成功导入新快照 `20261018-0306`（记录时间 `2026-10-17T19:14:34+00:00`），本地许可已施加。新快照上的邮件夹具通过 **18 tests / 155 assertions**；前后读回 queued_mail=0、pending_retries=0，见 [runtime-readback.json](runtime-readback.json)。邮件在本地隔离下写 `.eml`。本轮没有真实发信、部署、合并或生产写入。最终结果见 [verification.txt](verification.txt)。

## 翻译生成与比较

第 2 轮补齐 LC 片段提取。重复执行以下命令即可从当前源码重建，无旧 POT 输入：

```sh
just i18n-commerce c288
just i18n-coverage
just i18n-validity
```

配方先用 WP-CLI 从 PHP/模板/源 JS/build 生成全新 POT，再从 LC 源码提取仍使用的既有目录词条，使用 `msgcat` 组合这两个全新提取结果；最后 `msgmerge --no-fuzzy-matching` 保留原译文并编译 MO。PO 只作为既有消息字典，LC 源文件决定是否仍有效；LC 的 EN/DE twins 已承载各语言正文，本轮不生成新译文。

POT 当前 **839** 个有效条目，LC 提取 **29** 个已有词条，其中 **9** 个从 obsolete 恢复为 active。[translation-check.json](translation-check.json) 与 [mo-comparison-round2.json](mo-comparison-round2.json) 记录原评审前 **861** 个既有 PO msgid/msgstr 对不变，最新主线 `97f6fc14` 的 **866** 对也全部保留。MO 与主线比较：仅删除四条真正退役的审批文案，改动 **0**；`Clear search → Suche leeren` 已恢复。另有八条原在主线 PO obsolete 区、仍存在 LC 片段的译文恢复进 MO。完整先红后绿与命令来源见 [round2.md](round2.md)。

## 评审与验收

Spec/Standards 评审见 [review.md](review.md)。设置页的最终 EN/DE、1440/390 Computer Use 截图用于确认信封区已消失，内部发件人及原字段仍可见。该设置删除没有客户页面或邮件正文/主题变更。

| 语言 / 视口 | 最终截图 | 结果 |
|---|---|---|
| EN 1440×1000 | [desktop](settings-final-en-1440.jpg) | 信封区已移除，内部 Sender email 与既有字段保留。 |
| EN 390×844 | [mobile](settings-final-en-390.jpg) | 内容宽度 390、页面宽度 390，无横向溢出。 |
| DE 1440×1000 | [desktop](settings-final-de-1440.jpg) | 正式德语原字段及 Absenderadresse 可见，无信封文案。 |
| DE 390×844 | [mobile](settings-final-de-390.jpg) | 内容宽度 390、页面宽度 390，无横向溢出。 |

截图使用新快照，通过 Computer Use 浏览器完成；临时视口已 reset，本地用户 locale 已恢复 zh_CN。

回滚：恢复合并前插件版本即可；本轮无数据迁移。应用层已无信封选项的读取或写入，不需要操作生产选项。
