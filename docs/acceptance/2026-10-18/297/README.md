# #297 内部通知认证 SMTP · Review round 1

本轮依据 PR #300 的“Review, round 1 (#297)”裁定。工作树 `c297`，分支 `feat/297-internal-smtp`；无生产写入、部署、合并或真实邮件发送。测试的配置、账号与密码均为假值，SMTP 只到测试自启的 loopback sink，PHP mail 只写文件。

## 评审逐项交付

| 项 | 最终行为与证据 |
|---|---|
| Spec 1：任何内部 SMTP 失败立即 fallback | Outbox 对同一投递副本立即尝试 PHP `mail()`；连接、认证、发送失败记录 `smtp_failure`，From/auth user 不符记录 `identity_mismatch`。`SmtpOutcome` 仅存 Unix 时间、结果与固定分类；fallback 成功保留 SMTP 失败，后续 SMTP 成功才更新。真实认证失败、身份失败、摘要 fallback 与双失败后原队列恢复均有夹具测试。 |
| Spec 2：HOME 共用机制与 web 读回 | `Settings\PrivateConfigDirectory` 是唯一的 SMTP 私有目录定位入口。当前 spec 10 已退役 QueryEmbedding；退役前其 HOME 代码在 `load_env_file()` 内，没有独立公共 helper。本轮提取同一 `getenv('HOME') → .config/terravolt-builder` 机制，不恢复编码器或复制一份 SMTP 内部路径实现。下面单列 web 上下文验收，不能用 CLI 结果替代。 |
| Spec 3：SMTP 配额来源 | spec 11 引用 `mail-root-cause.md` §3、§9 与其中 Hostinger 原始来源：试用每邮箱 100/滚动 24h，Business Starter 1000/滚动 24h；共享 8/80 继续限制每条通道。sunriver 自己发信也占邮箱额度；实际套餐由 Claude 从 hPanel 填下面的字段。 |
| Standards 1：配置加密与 reset | `LINKER_SMTP_SECURE` 显式控制 `ssl`/`tls`/空；缺省 465→ssl，其他端口→tls。生产不再有主机为 127.0.0.1 的特殊分支。reset 恢复 PHPMailer 原生 Port=25、SMTPAutoTLS=true，并清掉认证。真实 PHPMailer 属性边界有断言。 |
| Standards 2：注入 Options | `InternalSmtp` 构造函数接收 `Options`，配置读取内部不再 `new Options()`。 |
| Standards 3：marker 单一常量 | 名称和值只在 `Message::INTERNAL_HEADER` 定义；添加与清除都使用它，clear 从常量解析名称。 |
| Standards 4：失败文字单一常量 | `InternalSmtp::FAILURE_MESSAGE` 同时供钩子失败与异常路径使用，服务器回显不保存。 |
| Standards 5：单一标记 helper | `Message::mark_internal()` 支持 WP 两种 header 形态；TeamEmail、TeamMessageEmail、Monitor 都调用它。原六类通知队列断言继续通过。 |
| Standards 6：Blocks 注释 | 明确 Digest 的三块业务数据与 `Health\InternalMail` 的归属，健康块继续留在 Health。 |
| Standards 7：手工 KEY=VALUE | 首个等号切分、可选成对引号、空行和整行 # 注释；值内 `;#=` 原样传到真实本机 AUTH 验证器。 |
| Standards 8：sink 类型检查 | `smtp_sink.py` 补全类型；`just check` 的 py-check 显式执行其 Ruff、format 与 strict mypy，无新依赖。 |
| Standards 9：Exception import | Outbox 通过 `use PHPMailer\PHPMailer\Exception` 捕获，和其他导入一致。 |

## 可复跑验证

本轮测试边界沿用票据与已裁定评审：Outbox/原生 PHPMailer 的真实投递、配置文件边界、最后结果健康块、员工 REST 权限与读回。SMTP 成功后不 fallback；SMTP 失败但 mail 成功不排队；两者皆失败才保留原队列。测试模式只重写发送副本，队列保留原 To/Bcc。一个逻辑尝试占一个共享限速 slot，任一通道每 slot 最多尝试一次。

```sh
cd plugins/linker-commerce
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c297/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  -c phpunit.integration.xml.dist \
  --filter 'InternalSmtpTest|NotificationRoutingTest|MailRetryTest|DigestTest|HealthMonitorTest'

# SMTP 整组连跑：每次保存并还原选项、hooks、mailer、队列与本次排程，关闭自己的 sink。
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c297/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  -c phpunit.integration.xml.dist --filter InternalSmtpTest --repeat 2
```

TDD 红绿证据：原 INI 对含 `;#=` 的假密码认证失败，手工解析后通过；认证失败最初没有 mail 文件，接入 fallback/结果记录后通过；本机显式 ssl 最初被主机名分支改为空，改为配置来源后通过；marker helper 与 HOME helper 最初缺接口，加入后公开接口测试通过；sink strict mypy 最初报 16 个未标注类型错误，补类型后零错误。员工 REST 夹具最初缺入口，加入后匿名 401、员工 200、响应只有状态与固定结果字段。

本轮真实邮件集成组：31 tests / 323 assertions；SMTP 九场景连跑两轮：18 tests / 186 assertions；商务单元：1046 tests / 5443 assertions。PHPCS、PHPStan 8、sink strict mypy 与词条完整性检查通过。最新全仓库门禁与 CI 结果在 PR 的 Evidence 段及本轮交回评论。默认 `just test` 跳过未加载真实 WordPress 的集成项，本票上述集成命令在 c297 实际运行，CI 的临时 WordPress 实例执行同组。

## 未完成（Claude）：生产事实字段

部署时由 Claude 读取 hPanel，只记录非秘密套餐信息，不查看密码。研究中的配额按每邮箱、滚动窗口计；sunriver 自用邮件同样消耗该额度。

| 字段 | 当前值 |
|---|---|
| `sunriver_mailbox_plan (hPanel)` | **未完成（Claude）** |
| `sunriver_mailbox_daily_limit (rolling 24h, hPanel)` | **未完成（Claude）** |
| `hPanel_readback_at_UTC` | **未完成（Claude）** |
| `web_SMTP_configured_readback` | **未完成（Claude）** |
| `single_digest_inbox_DKIM_DMARC` | **未完成（Claude）** |

## 未完成（Claude）：生产步骤与回滚

以下是交接命令，本实现会话未执行。先完成 Spec + Standards 全量 diff 评审并合并。

1. **业主放置文件**：业主自行在服务器 `$HOME/.config/terravolt-builder/sunriver-smtp.env` 放置 HOST/PORT/USER/PASS，可选 SECURE；主机为 `smtp.hostinger.com`、用户为 `sales@sunriverinverter.com`，生产用 465/ssl 或邮箱支持的 587/tls。文件在 web root 外、0600；Claude 和执行者不打开或传递密码。格式是字面的 KEY=VALUE，不使用 shell 转义或变量展开；值的外围引号可选。
2. **备份、部署、读回**：部署工作树执行 `just cutover backup`，记下备份路径；`just cutover deploy` → `just cutover verify`。无服务部署、schema 迁移或凭据安装步骤。先填上面的 hPanel 套餐字段。
3. **web 上下文独立验收**：已登录的管理员或 Shop manager 打开同站任意后台页，在该页开发者控制台执行以下代码。nonce 仅用于本次请求，不打印或保存。WordPress 原生 `rest-nonce` AJAX 提供 cookie 会话的 REST nonce（本地 WP 7.1.3 `wp-admin/includes/ajax-actions.php::wp_ajax_rest_nonce` 已核实）。

   ```js
   const nonce = await fetch('/wp-admin/admin-ajax.php?action=rest-nonce', {
     credentials: 'same-origin'
   }).then(response => response.text());
   const response = await fetch('/wp-json/linker/v1/mail-health', {
     credentials: 'same-origin', headers: { 'X-WP-Nonce': nonce }
   });
   console.log(response.status, await response.json());
   ```

   需要 HTTP 200、`smtp_configured: true` 与 `label: "SMTP configured"`（德语为 `SMTP konfiguriert`）。响应只含配置布尔状态、标签、最后 SMTP 结果；不含路径、主机、用户或密码。保存这份非秘密读回到 `web_SMTP_configured_readback`。若 web 为 false 而 CLI 为 true，停止触发摘要，由部署会话核对 wp-config 给 web PHP 的 HOME；不读取 env 文件内容。
4. **CLI 前置读回**：SSH `hostinger-de-linker`，在 `/home/u388076051/domains/de-linker.com/public_html` 运行以下命令，只输出非秘密状态。确认 From/To/Bcc 为业主允许的路由、没有待触发的同一摘要，避免与 cron 重复。

   ```sh
   /usr/local/bin/wp eval 'echo ( new Linker\Commerce\Mail\InternalSmtp() )->authenticated() ? "configured\n" : "not-configured\n";'
   /usr/local/bin/wp eval 'echo wp_json_encode( array( "from" => ( new Linker\Commerce\Settings\Options() )->notify_sender()->email, "to" => ( new Linker\Commerce\Settings\Options() )->notify_to(), "bcc" => ( new Linker\Commerce\Settings\Options() )->notify_bcc() ) ) . "\n";'
   /usr/local/bin/wp linker-commerce test-mail status
   /usr/local/bin/wp cron event list --fields=hook,next_run_gmt
   ```

5. **只触发一封真实摘要**：`/usr/local/bin/wp cron event run linker_commerce_digest`。读 `linker-mail`、队列与下一次排期；再执行步骤 3 的 web 读回，`last_outcome.status` 必须为 `success`。若是 failure，fallback 可能已经投递，不能把“收到”当作 SMTP 验收成功，也不要重发一封探针。
6. **Inbox 与头部**：在 sunriver **Inbox** 找到这封摘要，记录脱敏的主题/时间与认证头：From 为 sunriver、`dkim=pass d=sunriverinverter.com`、`dmarc=pass`。只在 Junk 到达不通过。填 `single_digest_inbox_DKIM_DMARC` 并补到 #297，之前保持“未完成（Claude）”。
7. **回滚**：恢复步骤 2 备份里的 linker-commerce 插件，保留原路由选项、队列、限速记录与无秘密的最近结果记录，不重发成功邮件。凭据不由 Claude 改动或删除。完整站点回滚只有部署者评估新业务数据后才使用 `just cutover rollback --backup <路径> --write`，不盲目覆盖业务数据；读回旧版本与 PHP mail 行为并在票上记录。
