# #297 内部通知认证 SMTP

实现 #297 中 Claude 的 2026-10-18 决定。工作树 `c297`，分支 `feat/297-internal-smtp`。仅使用本机实例 `c297`（WordPress 7.1.3 / WooCommerce 11.2.0 / PHP 8.3），无站点界面改动。没有生产部署、合并、生产写入或真实邮件发送；没有读取或放置真实凭据。

## 验收边界与结果

票据已指定测试边界：Outbox 的捕获/重试、WordPress `phpmailer_init` 与真实 loopback SMTP 投递、健康摘要。TDD 在这些公开边界进行，不测试私有方法。队列路由读取按票据与 AGENTS 测试邮件纪律用于路由断言。

| Done when | 实现与证据 | 状态 |
|---|---|---|
| 单元与集成：内部邮件认证 SMTP，auth user = From；客户邮件 `mail()`；秘密不进入日志/options | `Unit\Mail\InternalSmtpTest` 检查完整配置与身份；`Integration\InternalSmtpTest` 做真实 AUTH，验证复用对象后的客户通道、From 不符进重试、服务器回显假密码时日志/队列错误脱敏、options 写入没有凭据、tester 重写与限速；`NotificationRoutingTest` 验证六类内部生产者。 | 本地完成；`just check` / `just test` 通过 |
| 本机 SMTP sink 收到内部邮件，客户邮件不进入 SMTP | `smtp_sink.py` 由测试 `proc_open` 启动，随机端口仅绑定 `127.0.0.1`，只接受固定假账号。内部 MIME 实际进入 sink；客户 MIME 只写临时文件。测试后恢复 hooks、mailer、限速/选项、队列及进程与文件。 | 完成 |
| Spec 11 Mail 更新 | `docs/specs/11-commerce.md` 的“Mail：内部认证 SMTP（#297）”；同步 spec 74 健康区块。 | 完成 |
| 部署后，业主凭据就位，Claude 触发一封摘要，进入 sunriver 收件箱，DKIM 与 DMARC 通过 | 此实现会话不能执行，见下面准确步骤。 | **未完成（Claude）** |

真实 mail 集成组（CI 同组）本地连续两次通过：**26 tests / 280 assertions**。它包括 SMTP 四场景、六类通知生产者、旧重试、摘要与健康告警回归。SMTP 四场景另以 `--repeat 2` 连跑通过（8 tests / 100 assertions）；成功重试删除队列记录后，夹具仍保留自身 job ID 清理手动触发产生的重试排程。原生 Action Scheduler 读回的孤立待重试排程数为 0。每次自行清理本次夹具并恢复原状态。

全仓库门禁：`just check` **PASS**（PHPCS / PHPStan 8 / JS / Ruff / mypy / i18n / 构建）；`just test` **PASS**。默认商务套件中 82 个未加载真实 WP 的集成项按设计跳过，本票真实邮件链由上面的独立 26 项实际运行证明。其余门禁包括 PHP i18n 190 项、tools 188 项、mu 6 项；前端单元 128 项与 Playwright 9 项；Genie 723 项、engine 112 项、local 98 项、migrate 94 项（另 9 项按原配置跳过）、FAQ 20 项、pull 113 项、cutover 82 项。新增行旧标识符检查无命中，`git diff --check` 通过。

复跑：

```sh
cd plugins/linker-commerce
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c297/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  -c phpunit.integration.xml.dist \
  --filter 'InternalSmtpTest|NotificationRoutingTest|MailRetryTest|DigestTest|HealthMonitorTest'
```

红绿证据：

- `MessageTest::test_internal_marker_survives_the_queue` 起初因缺少 `is_internal()` 报错，新增显式标记读取后通过。
- `NotificationRoutingTest` 起初十二组内部生产者断言缺少标记；接入 TeamEmail、联系团队信、健康告警后十五项通过。
- `Unit\Mail\InternalSmtpTest` 起初缺少类，随后完整配置/缺文件/身份不符通过；新增“引号内空密码”断言先失败，再修正为未配置。
- loopback 投递测试起初缺少 `Outbox::configure_mailer`；接入原生钩子后实际 AUTH 与投递通过。
- 身份不匹配夹具暴露 `phpmailer_init` 在 WordPress 的 send try/catch 外；Outbox 接住 PHPMailer 异常后，错误进入重试而不使请求抛错。
- `InternalMailTest` 起初缺少健康区块；加入后单条异常通过。德语集成先出现英文，再随 `.po/.mo` 交付通过。

原生优先、配置格式、数字与阈值来源见 spec 11。无新增插件或依赖；无 LC、WindPress、客户页面修改，因此本票无页面像素变化。内部摘要文案评审见同目录 `copy-review.md`。

## 未完成（Claude）：生产步骤

以下是交接说明，本会话未执行。先完成 Spec + Standards 全量 diff 评审并合并；生产写入只由 Claude 的部署会话执行。

1. **业主放置凭据**：由业主在主机 `$HOME/.config/terravolt-builder/sunriver-smtp.env` 放置四个变量。主机为 `smtp.hostinger.com`，用户为 `sales@sunriverinverter.com`，端口使用 Hostinger 账户的 TLS 配置（465 隐式 TLS，587 STARTTLS）；密码仅业主填写。文件在 web root 外、仅账户本人可读（0600）。Claude 不打开、不打印、不传递该文件。
2. **备份、部署、读回**：在最新合并后的专用部署工作树按已有管线执行 `just cutover backup`，记录本次备份路径；执行 `just cutover deploy`，然后 `just cutover verify`。部署范围为本票插件与语言包，无服务部署或数据库迁移。
3. **配置读回只输出布尔值**：通过 `ssh hostinger-de-linker`，在 `/home/u388076051/domains/de-linker.com/public_html` 用 `/usr/local/bin/wp` 执行下面只读命令。`configured` 只证明文件完整且用户匹配内部 From；若为 `not-configured`，由业主修复文件后再继续，不读取文件内容。

   ```sh
   /usr/local/bin/wp eval 'echo ( new Linker\Commerce\Mail\InternalSmtp() )->authenticated() ? "configured\n" : "not-configured\n";'
   /usr/local/bin/wp eval 'echo wp_json_encode( array( "from" => ( new Linker\Commerce\Settings\Options() )->notify_sender()->email, "to" => ( new Linker\Commerce\Settings\Options() )->notify_to(), "bcc" => ( new Linker\Commerce\Settings\Options() )->notify_bcc() ) ) . "\n";'
   /usr/local/bin/wp linker-commerce test-mail status
   /usr/local/bin/wp cron event list --fields=hook,next_run_gmt
   ```

   未设 `linker_commerce_notify_from` 时由 `Options::notify_sender()` 回到 `sales@sunriverinverter.com`；不因 option 不存在判故障。确认内部 To 为业主允许的 sunriver 地址，Bcc 仅保留此前已验证且允许的地址；这些属于现有路由读回，任何调整由 Claude 记录在票上。确认没有待触发的同一摘要，避免 cron 与手动触发重复。
4. **只触发一封真实摘要**：在上述生产 WordPress 目录执行 `/usr/local/bin/wp cron event run linker_commerce_digest`。不执行注册、客户邮件或额外探针发送。查看 WooCommerce → Status → Logs 的 `linker-mail`：确认这一封有成功记录、没有新增失败/待重试消息；检查下一次摘要已排期。日志成功只证明投递接口成功，不能替代下一步。
5. **收件箱与头部验收**：在 `sales@sunriverinverter.com` 的 **Inbox** 找到这一封摘要；仅在 Junk 找到算失败。保存脱敏的时间/主题与认证头，确认 `From: Linker <sales@sunriverinverter.com>`，以及 `dkim=pass` 且 `d=sunriverinverter.com`、`dmarc=pass`。在 #297 评论并补入验收记录；完成前保留“未完成（Claude）”。
6. **回滚**：本票无 schema 或设置迁移；若传输导致故障，使用步骤 2 记录的部署前备份恢复 `wp-content/plugins/linker-commerce`，并读回旧版本与原有 `mail()` 行为。保留现有路由选项、Outbox 队列和限速记录，不重放已经成功的邮件；凭据文件不由 Claude 删除或改动。恢复旧代码会恢复内部 PHP `mail()`，认证问题也随之恢复，应在票上记录。需要完整站点回滚时沿用 `just cutover rollback --backup <步骤2路径> --write`，由部署者按该次备份评估是否适用，不能盲目覆盖新业务数据。
