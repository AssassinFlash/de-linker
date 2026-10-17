# #288 信封发件人验收

线上快照：`20261018-0218`，记录时间 `2026-10-17T18:25:44+00:00`（本地 2026-10-18 02:25）。`just sync c288` 完整导入，许可证已施加。

本地实例：`c288`，`http://127.0.0.1:9093/`。分支：`feat/288-envelope-sender`。本票只实现与验证应用邮件发送层；没有生产写入、DNS 修改或真实发信。

## 已实现

- WooCommerce → Settings → Inquiries 新增 Mail delivery / E-Mail-Zustellung，Envelope sender / Envelope-Absender；选项 `linker_commerce_envelope_sender`，默认 `sales@sunriverinverter.com`，来源为 #288 的 SPF 取证。
- `Mail\EnvelopeSender` 在每次 `phpmailer_init` 设置原生 `Sender`，包括即时投递、旧队列重试、复用 mailer；不伪造 Return-Path 头。收件服务器写入 Return-Path，生产效果仍待验。
- 客户 From 保留 WooCommerce 设置；内部 From 保留内部设置。`Options::notify_sender()` 统一名称与地址，默认信封地址与内部默认发件地址在 Options 共用同一来源。
- Proforma 前缀剔除首尾连字符；保留 `DLK-PF` 内部连字符。
- NotificationRoutingTest 的 Reply-To 断言按邮件 ID 分支，摘要/健康告警也断言不新增 Reply-To。

## 可重复验证

在本工作树根运行：

```sh
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c288/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php plugins/linker-commerce/vendor/bin/phpunit \
  -c plugins/linker-commerce/phpunit.integration.xml.dist \
  --filter 'EnvelopeSenderTest|NotificationRoutingTest|MailRetryTest|MailChainTest|HealthMonitorTest'
just check
just test
```

邮件层首轮先红后绿：Options 的新 envelope 读取最初 4 项 undefined-method 错误；mailer 策略最初 class-not-found；模块钩子最初缺少 `phpmailer_init` 期待；设置字段最初缺失，`--DLK-PF--` 最初仍保留首尾连字符。实现后均通过。`just test` 的 commerce PHP 套件：1,109 项、5,408 个断言，73 项未配置的实例测试跳过；本票邮件实例测试另在真实 c288 上执行。真实本地邮件套件：11 项、916 个断言，通过。

集成矩阵：12 封 Linker 邮件 + 2 封启用的 Woo 邮件，另有普通 WordPress 通知和两个服务健康告警；默认/自定义信封设置 × EN/DE。队列保存原始 From 与收件路由；改设置后才投递，PHPMailer Sender 使用当前设置；成功 MIME 的 From、单 tester 收件人、Reply-To 不变；最后再验证即时 wp_mail。邮件一律由本地 mu-plugin 的 postSend 写 `.eml`，没有真实发送。每组还断言原定时重试已撤销；选项、locale、回调、文件、限速记录与新队列在 teardown 还原/清理。

全仓门禁：`just check` 与 `just test` 均退出 0。`just test` 包含 PHP、JS、9 项 Playwright 配置器回归，以及 Genie、engine、本地栈、迁移、FAQ、快照与切换测试。

## Computer Use 视觉验收

通过 Chrome 同一会话检查新设置，截图前已完成当天线上快照导入。本票新增面只有 Woo 后台原生设置，不改客户页面、邮件模板、LC markup 或 WindPress 样式；客户页面像素复刻面无变更。本地与线上共有的 Team mailbox、内部通知 Sender email 的设置来源保持原样，新字段为裁定内新增。

| 语言/视口 | 截图 | 观察 |
|---|---|---|
| EN 1440×1000 | [settings-en-1440.jpg](settings-en-1440.jpg) | 默认信封地址、原团队邮箱、内部发件人并列可见；原生 Woo 设置样式。 |
| EN 390×844 | [settings-en-390.jpg](settings-en-390.jpg) | 输入宽 330 px，页面宽 390 px，无页面横向溢出，帮助文字自然换行。 |
| DE 1440×1000 | [settings-de-1440.jpg](settings-de-1440.jpg) | 三条新文案为正式德语，与既有 Absenderadresse 区分。 |
| DE 390×844 | [settings-de-390.jpg](settings-de-390.jpg) | 标签、地址与帮助文字可读，无新字段溢出。 |

浏览器临时视口覆盖已重置，截图用的本地用户 locale 已恢复。快照环境复验邮件套件仍为 11 项、916 个断言；投递全在本地文件。读取结果：客户 From `Linker <sales@de-linker.com>`，内部 From `Linker <sales@sunriverinverter.com>`，信封地址默认 `sales@sunriverinverter.com`。完整头部与收件箱归类不由这些截图证明。

## 翻译生成

先保留原 POT（现有压缩 JS 中的词条需要继续保留），用 WP-CLI 提取并合并：

```sh
git show origin/main:plugins/linker-commerce/languages/linker-commerce.pot > /tmp/c288-existing.pot
just wp c288 i18n make-pot \
  /Users/chesterjohn/Documents/de-linker-worktrees/c288/plugins/linker-commerce \
  /Users/chesterjohn/Documents/de-linker-worktrees/c288/plugins/linker-commerce/languages/linker-commerce.pot \
  --domain=linker-commerce --exclude=vendor,node_modules,tests \
  --merge=/tmp/c288-existing.pot --skip-audit
msgmerge --update --backup=none --no-fuzzy-matching \
  plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po \
  plugins/linker-commerce/languages/linker-commerce.pot
msgfmt --check plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po \
  -o plugins/linker-commerce/languages/linker-commerce-de_DE_formal.mo
```

既有译文语义全部保留；新增三条后台文案见 [copy-review.md](copy-review.md)，双评审见 [review.md](review.md)。

## 生产完成标准（未完成，Claude 部署后执行）

| 完成标准 | 状态 | 原因/接手方 |
|---|---|---|
| 改前/改后完整邮件头（去个人信息） | 未完成 | 需要生产真实邮件，由 Claude 在 #288 留证；本地 MIME 不能替代 Received/SPF/Return-Path 实证。 |
| 改后客户邮件在 sunriver 与指定测试邮箱均进入收件箱、截图 | 未完成 | 归类由接收方判断，只能生产实投验证；本实现会话禁止真实发信。 |

允许的真实测试邮箱仅 `857558227@qq.com`、`chester@de-linker.com`、`sales@sunriverinverter.com`。可见 From 必须保持原值；若真实验收失败，按 #288 由 Claude 基于证据决定下一步。

部署/回滚交接：设置无须数据库迁移；未保存的站点会立即使用默认值。Claude 按既有部署流程先备份，部署后读取设置及 PHPMailer Sender，再按票中测试邮件纪律取头部和归类证据。回滚插件到合并前版本即恢复原投递行为，删除 `linker_commerce_envelope_sender` 只撤保存值（本版本会回默认值，不是关闭策略）。
