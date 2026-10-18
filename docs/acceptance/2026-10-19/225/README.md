# #225 · 注册表单按研究结论改（两步）

实例 **c225**，<http://127.0.0.1:9138>，worktree
`/Users/chesterjohn/Documents/de-linker-worktrees/c225`，branch
`feat/225-registration-two-step`，快照 **20261019-0005**（2026-10-18 16:13 UTC 拉取）。
仅本地实例；未部署、未合并、未写生产。测试邮件只落本地
`~/de-linker-local/c225/mail`；实走创建的测试账号已删除。

## 交付

WooCommerce 注册表单是业主 2026-10-17 选定的**变体 B · 两步**（AGENTS.md §2）：

- 第 1 步 `Your company`：公司名、业务类型（三个单选块）、国家（全部国家，德国置顶，Europe 其余，其余最后，Woo selectWoo 搜索）、公司网站或 VAT ID 至少一项。
- 第 2 步 `You and your sign-in`：名、姓、邮箱、密码。
- 顶部两段进度条 + `Step 1 of 2 · Your company` / `Step 2 of 2 · You and your sign-in`；必填 `*` 与 `(optional)`：Woo 字段由 Woo 渲染器标出，国家字段由 `CountryField` 自己的渲染器输出同一套标记。
- 街道/邮编/城市移出注册（Proforma 请求页原生字段收）；电话不收。
- `Inquiry\PublicGuard` 在 `woocommerce_register_form` 打印蜜罐与签名起始时间，在 `woocommerce_process_registration_errors`（字段校验后、建号与发信前）复用蜜罐/时钟/最短填写时间/每连接原子限额；被拒计数可观测。
- 新客户通知与后台账户页通过同一个 `RegistrationInformation` 读同一套字段定义，网站自动出现。
- EN 先行、DE 独立撰写（Sie 体），对抗评审见 `copy-review.md`；布局变更台账见 `change-ledger.md`。

## 完成标准与证据

| 完成标准 | 状态 | 证据 |
|---|---|---|
| 两步字段、进度条与步骤文案 | 完成 | `screens/<lang>-<width>-step-1.png`、`-step-2.png`；`FieldsTest`、`CountryFieldTest` |
| 必填/选填标记、网站/VAT 上方说明 | 完成 | 截图；`FieldsTest::test_fields`；`form-register.php` |
| 地址与电话不在注册 | 完成 | `FieldsTest::test_fields`；`RegistrationFormTest::test_the_rendered_form_keeps_the_step_order_and_drops_the_address`；截图 |
| 国家：全部、德国置顶、Europe、其余、可搜索 | 完成 | `CountryOptionsTest`；`RegistrationFormTest::test_the_rendered_form…`；`screens/*-country-open.png` |
| 防机器人复用 PublicGuard 于两个 hook，建号/发信之前 | 完成 | `ModuleTest`（hook + 优先级 20）；`RegistrationFormTest::test_the_guard_refuses_and_counts…`；`bot-attempt.json` |
| 拦截计数可观测 | 完成 | `BlockedRegistrationsTest`、`RegistrationBlocksCommandTest`；实走 `honeypot: 1`（`bot-attempt.json`） |
| 真实 Register 按钮：裸域名与完整 URL | 完成 | `tests/e2e/specs/registration-two-step.spec.ts`；`checks/e2e-registration.log`（3 passed） |
| 通知邮件与后台账户页显示同一套字段（含网站） | 完成 | `RegistrationFormTest::test_a_registration_saves_the_fields_and_the_team_letter_shows_them`（Outbox body）；`AccountsAdminTest::test_the_registered_website_appears_in_the_review_card`；`screens/accounts-admin-website-1440.png` |
| 设计遵循线上认证卡 | 完成 | `before/`（线上）与 `screens/` 对照；`change-ledger.md` |
| EN/DE × 1440/390 两步与错误态截图 | 完成 | `screens/` 24 张 + 后台卡 + `login-error-1440.png` |
| 文案对抗评审 | 完成 | `copy-review.md`（EN 先行、DE 独立、18 条 `.po` msgstr，`just i18n-coverage` clean） |
| `just check` / `just test` 全绿 | 完成 | `checks/just-check.log`、`checks/just-test.log`（末行 `EXIT:0`）、`checks/integration.log` |
| CI 绿 | 完成 | PR 的 checks（合并前） |
| 线上 EN/DE × 1440/390 实走注册 | **未完成** | 本会话不部署；部署后按 #237/#220 由业主实走。本地真实按钮实走见 `tests/e2e/specs/registration-two-step.spec.ts` 与 `checks/e2e-registration.log` |

## 机器人拦截与真实按钮实走

`bot-attempt.py` 对本地实例发一次真实 HTTP POST（机器人：全部字段 + 蜜罐 `website`，同一连接）；正常注册走浏览器真实 `button[name="register"]`，不是 `form.submit()`：

| 场景 | 结果 |
|---|---|
| 全部字段 + 蜜罐 `website` | 200，页面显示 `We could not process this registration.`；无账号；无新邮件；`wp linker-commerce registration-blocks` 从 “No blocked registrations.” 变为 `honeypot: 1` |
| 裸域名 `example.com`，真实 Register 按钮 | 浏览器两页填写 → 302 `/my-account/`；账号 `linker_company_website = https://example.com`；`linker_approval_status = pending` |
| 完整 `https://example.com/legal`，真实 Register 按钮 | 同上；账号 `linker_company_website = https://example.com/legal` |

机器人输出：`bot-attempt.json`。两个真实按钮用例在 `tests/e2e/specs/registration-two-step.spec.ts`，运行记录 `checks/e2e-registration.log`；每个用例先清空共享连接限额、结束后删除测试账号。错误态截图需要绕过客户端校验才能到服务器错误，因此 `capture.mjs` 对错误态使用 `form.submit()`；成功路径不经过它。

## Outbox / 邮件内容

`RegistrationFormTest` 把 Outbox 队列填满后触发真实注册：队列里的团队邮件正文包含
`Company name`、`Business type`、`Installer`、`Country / Region`、`Company website`、
`VAT ID`、`First name`、`Last name`、`Login email` 与 `https://example.com`，不含
`Street address` / `Postcode`；后台直达链接仍在。客户确认邮件照旧，welcome 邮件仍关。

## 视觉

- `before/`：线上 de-linker.com 注册页（只读），EN/DE × 1440/390；可见三段编号、地址字段、业务类型下拉。
- `screens/`：本地实现后同条件，EN/DE × 1440/390 的 step 1、step 2、客户端错误、第 1 步服务器错误、第 2 步服务器错误，另加国家下拉打开态、后台账户卡，以及 `login-error-1440.png`（登录卡单条错误通知仍是 flex 布局，证明 #225 的注册卡列表 grid 没有波及登录/忘记密码卡）。
- 注册卡属裁定重设计（工具/裁定变更），不做整页像素相等声明；其他页面不属于本票。

## 复跑

```bash
just sync c225
just present c225            # 第一次会因缓存过期报错；随后
just windpress-compile c225 --user=857558227@qq.com
node docs/acceptance/2026-10-19/225/capture.mjs

# Real-button walk (bare host and full https URL), then the bot attempt:
LINKER_E2E_SKIP_SERVICES=1 just e2e c225 registration-two-step
just wp c225 eval 'global $wpdb; $wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( "linker_commerce_limit_" ) . "%" ) );'
just wp c225 linker-commerce registration-blocks --reset --user=1
python3 docs/acceptance/2026-10-19/225/bot-attempt.py

cd plugins/linker-commerce
php vendor/bin/phpunit                     # unit
LINKER_WP_ROOT="$HOME/de-linker-local/c225/wordpress" \
  php vendor/bin/phpunit -c phpunit.integration.xml.dist
```

`capture.mjs` 在每个服务器错误态前清空本地实例的 `linker_commerce_limit_*` 选项（与
`IntegrationTestCase` 的隔离方式一致），因为共享限额是每连接每小时 3 次；它只用
`form.submit()` 绕过客户端校验来拍服务器错误态，不用于成功路径。成功路径是 e2e 里的真实
`button[name="register"]` 点击。

## 回滚

代码回滚：撤销本分支的 `Registration/*`、`AuthTemplates`、注册模板、`auth.css`、
`account-ui.js` 与 `.po` 改动即可；无数据库 schema、无迁移、无新端点。注册字段的 meta
（`linker_company_website`）对旧代码无害，可留在账号上。部署流程按仓库的原子切换保留
上一版代码；本票不执行部署。
