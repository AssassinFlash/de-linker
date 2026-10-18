# 拆开登录与注册：一个 URL 各管一张卡

依据：业主 2026-10-16 指令——账号页现在是一页一长串（登录卡 + 注册卡上下排），拆成
sign-in 页与注册页两张独立页面，保留互相跳转入口。设计基准仍是业主 2026-10-15 验收
通过的账号链原型（`docs/design/2026-10-15-account-redesign/prototype/login.html` /
`register.html`：这两页在原型的索引里本来就是两个独立页面，本次实现把它们还原成
两个真实 URL）。

代码依据 = 本文件 + 仓库票据；上游事实 = WooCommerce 11.2 的实际行为（本机实例
`split` 逐项实测，见 §5）。

## 1. 现状 → 目标

| 面 | 现状（#187 合并后的 main） | 目标（本票） |
| :--- | :--- | :--- |
| `/my-account/`（DE `/de/mein-konto/`）guest | 一个模板 `templates/myaccount/auth/form-login.php` 出两个 `.linker-auth-unit`：登录单元 + 注册单元，卡内锚点互跳（`#linker-signin` / `#linker-register`） | 只出登录单元（品牌面板 + 登录卡）；卡底 `No partner account yet? Create your business account` 指向注册页 |
| 注册页 | 不存在（注册卡寄生在账号页下半） | **新增** `/my-account/register/`（DE 共享同一 slug：`/de/mein-konto/register/`）；只出注册单元（注册文案品牌面板 + 注册卡）；卡底 `Already have a partner account? Sign in` 指回 `/my-account/` |
| 注册表单 action | `#linker-register`（回账号页锚点） | 注册页自身（空 action = 本页），Woo 的校验错误落回注册页 |
| 端点注册 | 无 | `AuthTemplates` 经 `woocommerce_get_query_vars` 加 `register` 查询变量（与 `saved-solutions`/`documents` 同一机制） |
| 菜单 | 不含注册 | 同样不含：`Menu::items()` 把 `register` 列入"已知"，Woo 的 `wc_get_account_menu_items()` 不再把它当陌生端点补成一行 |
| 页脚 Konto 面板 `Anmelden` / `Sign in` | `/my-account/` | 登录仍到账号页；#223 在同一项目增加直达注册页的 `Create account` / `Konto erstellen` |

## 2. 选型：Woo 端点法（而非独立 WP 页 + LC 模板）

选 **端点法**，理由逐项：

1. **注册的处理链全在 Woo，且绑定在账号页上。** 注册表单的 nonce（`woocommerce-register`）、
   字段（`Registration\Fields` 挂在 `woocommerce_register_form_start`）、校验
   （`woocommerce_process_registration_errors`）、建号（`woocommerce_created_customer`）、
   自动登录与跳转（`WC_Form_Handler::process_registration()` 的
   `woocommerce_registration_auth_new_customer` + `wc_set_customer_auth_cookie`）都由
   `WC_Form_Handler` 在**任何**请求上执行——它不认识页面，只认识 POST 体。端点因此不需要
   搬运任何处理逻辑，只搬运"这一页渲染哪张卡"。
2. **端点检查、URL 生成、重写规则是 Woo 原生能力。** `is_wc_endpoint_url( 'register' )`、
   `wc_get_account_endpoint_url( 'register' )`、`add_rewrite_endpoint()` 全部免费；站点
   已有同型先例（`saved-solutions`、`documents`，见 `Account\Menu::ENDPOINTS`），重写缓存
   由 `Settings\WooOptions::flush_rewrites_when_endpoints_change()` 在查询变量集合变化后
   自动重建，不需要访问 Settings → Permalinks。独立 WP 页则要自建页面、自建 LC 模板、
   自建短代码，还要自己保证"注册 POST 落在这一页"——注册处理链挂在账号页的短代码上，
   另一条路只会把 Woo 的链拆成两半。
3. **POLYLANG 语言链路不变。** 端点 slug 跨语言共享是本站在线现状（`lost-password` 等
   同理），德语注册页自然是 `/de/mein-konto/register/`，`wc_get_account_endpoint_url()`
   在德语请求里返回德语地址；页面文案仍由 Polylang 的 locale 驱动 `.po`。
4. **pending 与登录用户的边界免费获得。** #222（2026-10-17 裁定）起 pending 账号保持登录与工作台，不再由门禁送回账号页；已登录账号访问注册页由本票的 `register_redirect()` 送回账号页（工作台或
   门禁卡），游客才是注册页的访客。
5. **没有新增设计决策。** 两张卡的 markup 与样式（`auth.css` 的 `.linker-auth-unit`
   两列/`.linker-auth-brand` 面板/`.linker-auth-steps` 三步）原样复用 #184 的成品，
   本次只是把它拆到两个请求上。

LC 模板法被否的理由：注册链的载体是 Woo 的模板与表单处理（`wc_get_template` 通道已由
`AuthTemplates` 接管），换 LC 页面等于在 `[woocommerce_my_account]` 之外再引一条短代码
进同一条链，违背"三件套原生优先"（AGENTS.md §5：LC tag → Woo 原生 → WindPress，自定义
是最后手段）。

## 3. 变更台账（业主过目）

| 变更 | 裁定 | 范围 |
| :--- | :--- | :--- |
| 登录与注册拆成两个页面（`/my-account/` = 登录；`/my-account/register/` = 注册），两页互跳 | **业主 2026-10-16 指令**："现状一页一长串，拆成 sign in 页 + 注册页，保留互相跳转入口" | 账号链 guest 面：账号页 + 新端点页；卡内布局、字段、nonce、校验、处理链不动 |
| 新增公开 URL `/my-account/register/`（DE `/de/mein-konto/register/`） | 同上（端点法，§2） | 站点 url 表新增一条端点 URL；canonical 仍指向 `/my-account/`（SEOPress 对账号页各端点的既有行为，与 `/my-account/documents/` 完全一致）；`<title>` 沿用账号页标题（同一既有行为） |
| 空草稿页（cart）guest 框的 `No account yet? Register` 改指注册页 | 同上（该链接自称 Register，目标页就是注册页） | `Gating\DraftSummary::guest_totals()` 一处链接；文案不变 |
| 页头 / 页脚 / 访客登录提示的入口 | 业主 #223 指令推翻原来只经登录卡分流的选择 | 每个访客登录提示旁均有直接注册入口。询盘已对访客开放；空 Proforma 登录门禁不再存在，不恢复它 |

## 4. 实现映射

| 载体 | 文件 | 做什么 |
| :--- | :--- | :--- |
| 端点登记 + 分流 | `includes/Account/AuthTemplates.php` | `query_vars()` 注册 `register`；`template()` 在注册端点请求上把 `myaccount/form-login.php` 换成 `auth/form-register.php`；`register_url()`（Woo 端点 URL）；`is_register_request()`（端点 + 账号页双重判断，因为 `?register=1` 查询变量在任何页都会被映射）；`register_redirect()` 把已登录账号送回账号页 |
| 登录页模板 | `templates/myaccount/auth/form-login.php` | 只留登录单元；卡底注册链接改指 `AuthTemplates::register_url()`（WooCommerce 关闭注册时不出链接） |
| 注册页模板 | `templates/myaccount/auth/form-register.php`（新） | 注册单元 + 注册文案品牌面板；表单空 action（提交回本页）；Woo 的 notice 印在注册卡内；`woocommerce_register_form_start/_form/_form_end/_after_customer_login_form` 钩子各触发一次，与 Woo 的 `form-login.php` 同序 |
| 菜单 | `includes/Account/Menu.php` | `AuthTemplates::REGISTER_ENDPOINT` 进"已知端点"集合，`wc_get_account_menu_items()` 不再为它补一行 |
| 空草稿框 | `includes/Gating/DraftSummary.php` | `Register` 链接改指 `AuthTemplates::register_url()` |
| 模板加载 | `includes/Account/Module.php` | 不变（`AuthTemplates::register()` 内部新增两个过滤器/动作） |

字段、nonce、name 逐字不动：注册页模板的 `#billing_*` / `#linker_customer_role` /
`#reg_email` / `#reg_password`、`wp_nonce_field( 'woocommerce-register', 'woocommerce-register-nonce' )`、
`name="register"`、`woocommerce_register_form_tag` 与 #184 的注册卡完全一致（e2e 的
`registerPartner()` 与 `commerce.spec` 的注册流因此不需要改选择器，只改 URL）。

## 5. 实测（本机实例 `split`，快照 + 本分支）

| 检查 | 结果 |
| :--- | :--- |
| `/my-account/` guest | HTTP 200，`.linker-auth-unit` × 1（登录单元），注册卡不在页上，卡底链接 `…/my-account/register/` |
| `/my-account/register/` guest | HTTP 200，`.linker-auth-unit` × 1（注册单元），`#reg_email` 等字段齐全，`linker-auth-register` 计数 3（section/step/…），卡底 `…/my-account/` |
| `/de/mein-konto/register/` guest | HTTP 200，德语（`Erstellen Sie Ihr Firmenkonto`、`Sie haben bereits ein Partner-Konto? Anmelden`） |
| 已登录账号访问注册页 | 302 → `/my-account/`（工作台；pending 账号同样保持工作台，#222） |
| 注册提交 | e2e `account.spec.ts` 的 VAT 两条用例走注册页提交 → 自动登录 → 账号待审批标记写入（WP-CLI 读回） |
| 登录错误回本页 | e2e `en/de: a wrong password is refused with the form's own error` 断言仍在 `/my-account/` 上、`#username` 在页 |
| 注册错误回注册页 | e2e `en: the register form … refuses a bad email server-side` 断言 URL 仍在 `/register/`、notice 与 `#reg_email` 在页、`#username` 不在页 |

## 6. 测试与验收

- 单元：`AuthTemplatesTest`（端点查询变量、端点 URL、端点分流、已登录重定向、游客留在本页、
  账号页外的同名查询变量不算）、`MenuTest`（`register` 不成菜单行）、`ModuleTest`（新钩子）、
  `DraftSummaryTest`（`Register` 指向端点 URL）。`phpunit --testsuite unit` 全绿。
- 端到端：`tests/e2e/specs/account.spec.ts` 的注册/登录链路改走注册 URL，并新增一条
  "两页互跳"断言（登录页 → 注册页 → 登录页，两页各自不含对方卡片）。
- 静态：`phpcs` 0 error / `phpstan` level 8 0 error / `node --test tests/js` 绿。
- i18n：`wp i18n make-pot --merge` 重生成 `.pot`；`.po` 的 `#:` 引用按新模板位置刷新；
  `.mo` 重编译；`just i18n-coverage` / `just i18n-validity` 绿。
- 文案：本轮**无新客户可见文案**（两页的标题、副文案、按钮、互跳句子全部是 #184 已评审
  的定稿；`docs/acceptance/2026-10-16/split/copy-review.md` 记录该判断与逐条出处）。

## 7. 可翻案处

- 注册页沿用账号页的 SEO 标题与 canonical（站点对账号页全部端点的既有行为）。若业主希望
  注册页有自己的 `<title>`，落点是 SEO 标题层（SEOPress 模板 + `Labels`），与本票无关。
- #223 已裁定全部访客登录提示旁提供独立注册入口，包括密码找回、文档 403 和 Genie。文档和询盘的账户归属检查不变；新建账户不授予原账户的权限。注册开关关闭或访客已登录时不提供创建账户入口。

## 8. #223 入口数据适配：原生能力逐项核对

2026-10-18 在唯一实例 `c223` 的已安装 LiveCanvas 源码核对：
`modules/templating-shortcodes.php:7–23` 的 `lc_wp_func` 只调用无参数函数；
`modules/templating-shortcodes-woocommerce.php:607–615` 的 `lc_wc_get_page_url`
只用 `wc_get_page_id(page)` 和 `get_permalink()` 取页面，不能生成账户端点；该模块的
`lc_wc_product` 为商品数据标签，`lc_wc_label` 只在 WooCommerce 文案域查词，不能读取
本插件的注册入口文案。两文件与 `modules/shortcodes.php`
没有访客状态与 Woo 注册选项的组合条件标签。原生 `lc_get_partial` 负责装入片段，不能
把这两个条件和当前语言端点绑定到片段内的链接。没有在 LC 中执行 PHP 或新增表单处理。

| 窄适配 | 优先尝试的原生能力 | 余下的最小自定义部分 |
| :--- | :--- | :--- |
| `linker_create_account` | Woo `wc_get_account_endpoint_url()` 经现有 `AuthTemplates::register_url()`；Polylang 原生本语言账户页；LC fragment | 同时判断 `is_user_logged_in()` 与 `woocommerce_enable_myaccount_registration`，转义 URL 和 gettext 文案，填入 LC 的单链接片段。原生页面 URL 标签不能生成 `register` 端点或有条件地移除整条链接 |
| `linker_guest_account_links` | Woo `wc_get_page_permalink('myaccount')`；上一行注册数据；LC `account/guest-links.html` | 访客条件下填入两个本语言目标，向既有 Genie 挂载适配提供 LC 内容；React 根外组成仍在 LC，服务和模型文字不参与判断 |
| `linker_footer_account` | LC 每语言 footer partial + `account/footer-entry.html`；Woo 本语言账户地址 | 原有一条项目要容纳两个独立目标，复用同一访客／注册条件；PHP 只填数据。换成硬编码 href 会丢失 Polylang 和注册关闭条件 |
| `linker_footer_account_count` | LC 页脚原有计数位置 | 原计数 03，在注册目的地可用时为 04；与同一可用性数据保持一致。原生标签没有计算该条件计数的接口，不在模板硬编码永远 04 |
| 草稿价格单元、草稿摘要、私有文档拒绝页 | Woo 原生价格过滤器／cart collaterals、既有下载拒绝处理 | 既有回调只传递转义后的状态、地址和链接数据给 `account/*.html`；组成移到 LC，不增加权限、端点、表结构或 CSS 通道 |

样式全部进 `content/windpress/account-links.css`，由现有 WindPress provider 扫描这些
LC 文件并官方编译。页头 `fit()`、断点、安全余量及 #229 的 Firefox 五个例外不变。
