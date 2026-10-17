# #288 邮件修正验收

本轮按 [PR #291 第 1 轮评审](https://github.com/AssassinFlash/de-linker/pull/291#issuecomment-6238959144) 的六项决定收敛。生产取证已完成：Hostinger `/usr/sbin/hsendmail -t` 强制信封为 `noreply@srv1798.main-hosting.eu`，设置 PHPMailer Sender 前后 Return-Path、SPF 与收件箱归类均不变。SPF 已通过，de-linker.com 无 DMARC；客户邮件在 QQ 收件箱，sunriver 的垃圾箱判定来自 From 域。内部通知使用 #286 的 sunriver 身份，客户 From 继续遵守业主裁定。证据和规则已替换进 `docs/specs/11-commerce.md` 的 Mail 一节。

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

直接从当前 PHP、模板、源 JS 和 build 资源生成 POT，没有使用旧 POT 合并：

```sh
just wp c288 i18n make-pot \
  /Users/chesterjohn/Documents/de-linker-worktrees/c288/plugins/linker-commerce \
  /Users/chesterjohn/Documents/de-linker-worktrees/c288/plugins/linker-commerce/languages/linker-commerce.pot \
  --domain=linker-commerce \
  --include=linker-commerce.php,includes,templates,src,build \
  --exclude=vendor,node_modules,tests --skip-audit
msgmerge --update --backup=none --no-fuzzy-matching \
  plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po \
  plugins/linker-commerce/languages/linker-commerce.pot
# 从 PO 移除本轮删除的三条信封设置文案；其他 obsolete 译文保留。
msgfmt --check plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po \
  -o plugins/linker-commerce/languages/linker-commerce-de_DE_formal.mo
```

比较以评审前 `2a06c6dc` 的 PO 为 before，按 msgctxt、msgid、msgid_plural 分组，逐个比较全部 msgstr（含复数、obsolete；忽略位置和格式变化）。[translation-check.json](translation-check.json) 记录：864 → 861 组，861 组完全不变，changed_msgstr 为空，删除的恰好是三条信封设置文案；origin/main 的全部 861 组也都保留。POT 当前提取到 825 个有效条目，build/accounts.js 的词条直接来自 build 资源。失去源码引用的旧译文保留为 obsolete，未改译文内容。

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
