# 拆分登录/注册 · 验收记录（2026-10-16）

业主指令："现状一页一长串，拆成 sign in 页 + 注册页，保留互相跳转入口"（2026-10-16）。
规格与选型理由：`docs/specs/split-login-register.md`；文案判断：
`./copy-review.md`。

## 1. Spec + Standards

- **范围**：`AuthTemplates`（端点登记 / 端点 URL / 模板分流 / 已登录重定向）、
  `Menu`（`register` 不成行）、`DraftSummary`（空草稿框的 Register 指向端点）、
  `form-login.php`（只留登录单元）、`form-register.php`（新增）、两条 e2e、四条单测、
  `.pot`/`.po`/`.mo`。
- **Woo 原生优先**：端点走 `woocommerce_get_query_vars`（站点既有先例 saved-solutions /
  documents），URL 走 `wc_get_account_endpoint_url()`，判定走 `is_wc_endpoint_url()`，
  重写缓存由 `Settings\WooOptions` 的既有签名机制重建；表单的 nonce、字段、name、hook
  序列照抄 Woo 11.2 的 `templates/myaccount/form-login.php`（版本 9.9.0），逐条保留。
- **零回流**：本票未触碰 `storefront.css`/LC 模板/旧标识符；`grep -rn "tv_b2b_|Linker_AI_|dlk-"`
  命中数与 main 相同（既有复刻层，不属本票）。
- **PHP 零设计**：两个模板只排布 Woo 的字段，无内联样式；样式仍只在
  `content/windpress/auth.css`。

## 2. 真实夹具测试

本地实例 `split`（快照 + 本分支 + `just present` + `just windpress-compile`）。

### 端到端（真浏览器，`just e2e split …`）

- `specs/account.spec.ts` **13/13 通过**（49.8s）。本票相关行：
  - `en: sign-in and sign-up are two pages and link to each other`（新增）：账号页只有登录卡
    （`#reg_email` 计数 0）、注册链接 href 命中 `/my-account/register/`、点击后注册页只有注册卡
    （`#password` 计数 0）、回跳链接命中 `/my-account/`、点击后回到登录卡。
  - `en: the register form … refuses a bad email server-side`（改走注册 URL）：URL 仍在
    `/register/`，错误条与 `#reg_email` 在页，`#username` 不在页。
  - VAT 两条注册用例（改走注册 URL）：注册 → 自动登录 → WP-CLI 读回 `linker_vat_*` 标记。
  - 登录错误回本页、忘记密码、重置链、账号细节、空态、restricted/rejected 门禁全部照旧通过。
- `specs/commerce.spec.ts`：注册流改走注册 URL（`register()` 助手改 `PAGES[locale].register`）。

### 单元与静态

- `phpunit --testsuite unit`：1004 tests 全绿（`AuthTemplatesTest` 新增 5 条、`MenuTest`
  新增 1 条断言、`ModuleTest` 新增 2 个钩子期望、`DraftSummaryTest` 改端点 URL）。
- `phpcs` 0 error、`phpstan` level 8 0 error、`node --test tests/js/*.test.mjs` 45 通过。
- i18n：`msgfmt --check` 通过，`just i18n-coverage` / `just i18n-validity` 绿。

### 手工实测（curl，本机实例）

| 场景 | 结果 |
| :--- | :--- |
| `/my-account/` guest | 200；1 个 `.linker-auth-unit`；`#linker-signin` 在页；注册链接 → `/my-account/register/` |
| `/my-account/register/` guest | 200；注册单元；`#billing_company` / `#linker_customer_role` / `#billing_vat_id` / `#reg_email` / `#reg_password` 齐全 |
| `/de/mein-konto/register/` guest | 200 德语（`Erstellen Sie Ihr Firmenkonto` / `Sie haben bereits ein Partner-Konto? Anmelden`） |
| 注册 POST（真 nonce + 全套字段） | 302 → `/my-account/`；随后页面是 pending 门禁卡；WP-CLI 读回 `linker_approval_status = pending` |
| 已登录（approved）访问 `/my-account/register/` 与 `/de/…` | 302 → `/my-account/` / `/de/mein-konto/`（工作台） |
| pending 账号访问注册页 | 302 → 本语言账号页，门禁卡（`PendingGate` 先于模板分流） |

## 3. 视觉验收（Computer Use，实例 `split`）

对照基准：`prototype/account-redesign` 的 `login.html` / `register.html`
（业主 2026-10-15 验收通过的原型；本票把原型里本就是两页的两张卡放回两个 URL）。

截图（`shots/`，同机同浏览器，fullPage，1440 与 390，EN 与 DE 各一张）：
`signin-en-1440`、`register-en-1440`、`signin-de-1440`、`register-de-1440`、
`signin-en-390`、`register-en-390`、`signin-de-390`、`register-de-390`。

逐项核对：

| 检查 | 结果 |
| :--- | :--- |
| 登录页 ≥1080px | 左侧品牌面板（`Your partner account` + 副文 + 三条要点）与右侧登录卡同高，单元圆角/阴影与 #184 成品一致；卡底 `Lost your password?` 与 `No partner account yet? Create your business account` 两行并列 |
| 注册页 ≥1080px | 左侧品牌面板（注册文案）+ 右侧注册卡三步骤；底部法务行 → `Register` → `Already have a partner account? Sign in` |
| 登录页 390 | 面板隐藏（媒体查询既有行为），单卡居中；注册入口在主按钮下方可见 |
| 注册页 390 | 单卡，三步竖向；`Firmenname` / `Unternehmensart` / `USt-IdNr.` 德语字段与标签正确 |
| 德语页 | 标题、步骤、字段、互跳句子全部德语（`Erstellen Sie Ihr Firmenkonto` / `Sie haben bereits ein Partner-Konto? Anmelden`） |
| 页头/页脚 | 无变化：页头 guest 一条 `Sign in`（→ 登录页），页脚 Konto 面板 `Anmelden`/`Sign in`（→ 登录页）——注册从登录卡进入，与原型 `gates.html` 的单主按钮形态一致 |

## 4. 变更台账条目（业主过目）

| 变更 | 裁定 | 影响面 |
| :--- | :--- | :--- |
| 登录与注册拆成两个页面，`/my-account/register/`（DE `/de/mein-konto/register/`）新增 | 业主 2026-10-16 指令 | 账号链 guest 面：账号页 URL 的可见内容减半（登录卡单独成页），新增一条端点 URL；登录/注册的处理链、字段、nonce、校验、邮件一律不动 |
| 空草稿页 guest 框 `No account yet? Register` 改指注册页 | 同上 | 一处链接目标；文案不变 |
| 账号页 `<title>` 与 canonical 不变（仍为账号页的） | 既有行为 | SEOPress 对账号页各端点的既有表现，与 `/my-account/documents/` 完全一致；若业主希望注册页独立标题，落点在 SEO 标题层（spec §7） |

## 5. 结论

通过。PR #188（`fix/split-login-register`）。

## 6. 附注

- `tests/e2e` 的运行会重写 `docs/acceptance/2026-10-13/account-auth/shots/` 里的 #184 截图
  （该目录是套件的固定输出目标）。本票不把那些重写纳入提交：实测显示其中多数（账号细节、
  联系公司、空态等与本票无关的页）在正常重跑下也会变化（渲染环境差异），只有本票自带的
  视觉证据（`shots/` 下 8 张）与 `copy-review.md` 是本票的记录。
- 本票在实例上临时创建的测试账号（`e2e-split-login`、`split-register-test@example.test`）已删除。
