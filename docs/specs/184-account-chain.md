# 184 · 重做账号链（登录/注册/忘记密码/重置/门禁/工作台/页头入口/一键登出）

整条账号链按业主 2026-10-15 验收通过的原型重做：guest 三页（含新增的重置表单覆写）、
四态门禁卡片化、工作台换新骨架与行结构、页头账户入口收窄、一键登出。Woo 拥有全部
字段、nonce、hook、校验与端点派发；本票只改呈现与数据装配。

设计基准（唯一）：`docs/design/2026-10-15-account-redesign/prototype/`
（16 页、每页 `?lang=en|de` × `?state=/?gate=/?tab=`，共享 `assets/app.css`）。
现状盘点与断点清单：`docs/design/2026-10-15-account-redesign/INVENTORY.md`。
文案对抗评审：`docs/acceptance/2026-10-15/184/copy-review.md`。

## 一、范围映射表（现状 → 新实现）

| 面 | 现状载体 | 新载体 |
| :--- | :--- | :--- |
| 登录 + 注册卡 | `templates/myaccount/auth/form-login.php`（居中两卡列） | 同文件重写：桌面 = **每张卡自带一个深绿品牌面板**（登录单元 = 登录文案，注册单元 = 注册文案，各自面板高度随各自的卡），移动 = 两卡竖排且无面板；注册三步编号组保留，只重排呈现。**后续变更（业主 2026-10-16）**：两卡拆成两个页面——登录卡留在 `/my-account/`（同文件），注册卡移到账号页的 `register` 端点（`templates/myaccount/auth/form-register.php`），见 `docs/specs/split-login-register.md` |
| 忘记密码请求 | `templates/myaccount/auth/form-lost-password.php` | 同文件重写：单卡（`.linker-auth--solo`），`Back to sign in` 留在卡内 |
| 发送成功确认 | Woo 默认 `myaccount/lost-password-confirmation.php`（裸文本落在页底） | **新增覆写** `templates/myaccount/auth/lost-password-confirmation.php`：同一张卡，Woo 的 notice + 过滤后的说明句进卡头 |
| 重置密码表单 | Woo 默认 `myaccount/form-reset-password.php`（裸模板，链路最差一环） | **新增覆写** `templates/myaccount/auth/form-reset-password.php`：卡 + 双密码字段 + Woo 自带眼睛 + Woo 自带强度计 |
| 账户细节（改密） | Woo 默认 `myaccount/form-edit-account.php` | **新增覆写** `templates/myaccount/account/form-edit-account.php`：资料卡 + 改密卡（说明行 + 干净标签） |
| pending 状态 | `Account/PendingGate.php` 整页替换审核卡 | `Account/AccountStatusNotice.php` 通过原生 `woocommerce_account_content` 在端点内容前显示 pending/restricted 共用的 LC 状态卡（restricted 含保存原因）；完整工作台、导航和联系卡保留（业主 2026-10-17，待审账号保持登录） |
| restricted / 空 Proforma / guest 带草稿门禁 | `Presentation/LoginGate.php` 的 `sf-checkout-empty` 文本块 | 同文件重写为卡片（badge + 标题 + 正文 + 动作）；guest 门禁两种形态（草稿空 = 取号，草稿有货 = 登录发送） |
| 工作台骨架 | `content/livecanvas/account/workspace.html` + `mobile-nav.html` | 重写：桌面 = 左侧栏（WORKPLACE/ACCOUNT 两组）；移动 = **只有底部胶囊 tab 栏**（顶部 `details/summary` 折叠菜单删除） |
| 询盘列表行 | `inquiry-card.html` 行内展开全量商品行 | 重写：`n Produkte` 摘要（`_n` 复数）+ 单号 + 状态胶囊 + 日期 + 金额 + `View` 箭头 |
| 工作台其余片段 | `overview/tiles/tile/recent/inquiry-row/summary/stage/proforma/documents/document-row/solutions/solution-card/empty*` | 全部按原型重写；`shortcuts.html` 删除（原型没有该组件） |
| 页头账户入口 | `ProductShortcodes::header_utilities`：guest 两条同址 + 登出走 Woo 端点的二次确认页 | guest 一条 `Sign in`；登出改 `linker_commerce_logout_url()`（`wc_logout_url()`，带 nonce），落回 `my-account/?signed-out=true` |
| 登出提示 | Woo 的确认页 | `AuthTemplates::signed_out_notice()` 在账号页加一条 Woo notice（`You have been signed out.`） |
| 样式 | `storefront.css` 的 account 块 + `auth.css` 的 639px 规则 + `account.css` | `auth.css` / `account.css` 整体重写为设计层（token 对齐 `tokens.css`）；`storefront.css` 删掉 account/gate 相关块（`.sf-account-*` / `body.sf-account-page` 一族见 §九） |
| JS | 无（整页 POST） | 新增 `assets/account-ui.js`：提交 is-loading（渐进增强）、双密码字段不一致行、随打字清错；强度计用 Woo 自带 |

## 二、原型态 → 实现映射

原型每页的每个态都有对应实现；`?lang=` 由 Polylang 决定，`?state=` 的写法换成真实状态。

### guest 链

| 原型 | 实现 | 触发 |
| :--- | :--- | :--- |
| `login.html?state=default` | `/my-account/`（guest）登录卡（2026-10-16 起注册卡不再同页，见下） | 访客 |
| `login.html?state=error` | 同页，Woo 的 `.woocommerce-error` 在登录卡内（`You have been signed out.` 之类同容器） | 凭据错误 |
| `login.html?state=rejected` | 同页，拒因由 `Registration\Approval::login_errors()` 写进同一条错误条 | 被拒账号登录 |
| `login.html?state=reset-success` | 同页，Woo 的 `.woocommerce-message`（`password-reset=true`） | 重置成功 |
| `login.html?state=signed-out` | 同页，Woo 的 `.woocommerce-info`（`signed-out=true`） | 一键登出后 |
| `login.html?state=loading` | 提交瞬时（`account-ui.js` 给按钮 `.is-loading`） | 提交 |
| `register.html?state=default/errors/loading/password-shown` | 注册卡（#225 两步：进度条 `Step 1 of 2 · Your company` / `Step 2 of 2 · You and your sign-in`；第 1 步公司名、业务类型三单选、国家、网站或 VAT ID，第 2 步名/姓/邮箱/密码；法务链接、Privacy 链接按 `get_privacy_policy_url()` 存在时出）；自 2026-10-16 起在 `/my-account/register/`（DE `/de/mein-konto/register/`） | 访客 |
| `lost-password.html?state=default` | `/my-account/lost-password/` 单卡 | 访客 |
| `lost-password.html?state=sent` | 同路径 `?reset-link-sent=true` → 确认卡 | 发送成功 |
| `lost-password.html?state=invalid-key` | 同路径，Woo 的错误条在卡内 | 无效/已用 key |
| `reset.html?state=default/mismatch/weak/loading` | `?show-reset-form=true` 的重置卡；不一致与过弱由 Woo 服务端校验（通知）+ `account-ui.js` 前端即时行 | 邮件链接落地 |
| `chrome.html` | 页头账户下拉：guest 一条；customer 菜单 + `Log out`（红色，带分隔线） | 任意页 |

### 门禁

| 原型 | 实现 | 触发 |
| :--- | :--- | :--- |
| `gates.html?gate=pending` | 账户各端点内容前的状态卡（badge `Under review`、h2）；Proforma 请求继续开放 | `Approval::PENDING` |
| `gates.html?gate=restricted` | `/proforma-request/`：badge `Access currently limited` + reason notice（`Our reason:` + 团队理由）+ mailto 链接 | `Approval::RESTRICTED` |
| `gates.html?gate=empty-proforma` | `/proforma-request/`（guest，草稿空）：`Get your Proforma` + Genie pill + 两个动作 | guest 且草稿空 |
| `gates.html?gate=guest-draft` | `/proforma-request/`（guest，草稿有货）：`Sign in to request your Proforma` + 草稿正文 + `Lost your password?` | guest 且草稿有货 |

空草稿的 approved 账号读 `Nothing to submit yet.`（原型未单列，文案走同一卡）。

### 工作台

| 原型 | 实现 | 备注 |
| :--- | :--- | :--- |
| `workspace-overview.html`（default/empty） | `/my-account/`：欢迎头 + 四个状态磁贴（点击 → 筛选后的询盘列表）+ Recent inquiries 5 行 + Documents 入口 3 行 + 联系人卡 | 磁贴数与行数来自 Woo 查询，非示例值 |
| `inquiries.html`（All/Open、状态筛选、分页、空态） | `/my-account/inquiries/`：`All inquiries` / `Open inquiries` tab、`?inquiry-status=` 筛选、`?page=` 分页、空态带 `Browse products` | Woo 的查询由页面本身执行，adapter 只窄化 status |
| `inquiry-detail.html`（四态进度条） | `/my-account/inquiry/<id>/`：四段 tracker（`data-state="done|now|todo"`，取消态用中性色）+ 概要 kv + 商品行（含 Datasheet PDF）+ 小计/VAT/合计 + Proforma 下载条 + `Request again` + 公司块 | 进度由 `has_proforma()` 与状态判定，不发明历史 |
| `solutions.html`（default/empty/added） | `/my-account/saved-solutions/`：方案卡（标题/保存日期/商品行/`Add to solution draft`/设计报告）+ 空态 CTA `Open the Solution Configurator` | 加入动作沿用 `SolutionsRoute` |
| `documents.html`（default/empty） | `/my-account/documents/`：行 = 图标 + 标题 + 日期 + `Download (PDF)` 幽灵按钮 | 下载 URL 仍是带 nonce 的私有下载 |
| `company.html` + `company-edit.html` | `/my-account/company/` 与 `/my-account/company/billing/`：Woo 的地址表单走新样式（`.linker-account-forms`），无 PHP 设计决策 | 表单仍由 Woo 渲染 |
| `account.html`（改密 + 强度条） | `/my-account/edit-account/`：两块 panel + Woo 自带强度计（`wc-password-strength-meter` 绑定 `form.edit-account #password_1`） | 强度计文案是 WP 的 `pwsL10n`（`wp.i18n`） |
| 登出 | 菜单项 = `wp-login.php?action=logout&redirect_to=…signed-out=true&_wpnonce=…` | 无二次确认页 |

## 三、通道与归属（AGENTS.md）

- **LC 动态模板**：工作台页面组合全在 `content/livecanvas/account/*.html`（短代码 = 数据装配，零内联样式、零设计决策）。`AccountTemplates` 只把 Woo 的授权参数翻成 LC 能读的行数据。
- **WindPress**：样式只在 `content/windpress/auth.css`（设计层 + guest 链 + 门禁）与 `account.css`（工作台）。两文件被 `WindPressVolume::files()` 发现并 import 进 `main.css`；四个锚类进了 `WindPressCache::ANCHOR_CLASSES`（`.linker-auth-card` / `.linker-gate` / `.linker-account-welcome` / `.linker-account-pill`），编译缺失即报警。
- **Woo 原生优先**：字段、nonce、hook、校验、端点派发、强度计、眼睛切换、notice、地址表单全部是 Woo 的；自定义只有呈现与数据装配。
  - 逐项穷尽证明（自定义先于原生之处）：
    1. 重置/确认/改密三张卡 → Woo 无卡片模板可用，覆写是官方支持的模板通道（`wc_get_template`）。
    2. guest 门禁（LoginGate）→ Woo 只有"重定向到草稿"的行为，无门禁页；短代码是本线既有机制。
    3. 一键登出 URL → Woo 的 `wc_logout_url()` 就是原生 API，不需要自定义。
    4. is-loading / 不一致行 → Woo 只有强度计，无提交态与字段级不一致提示；纯渐进增强，无 JS 时表单照常提交。
- **PHP 不解决设计问题**：`LoginGate` 输出语义标记 + 类名（badge/section/actions），无内联样式，无布局决策。

## 四、门禁与状态机（与既有实现一致，仅换呈现）

- `Approval` 四状态：`pending` 注册后保持登录，工作台及端点照常使用，局部状态卡提示审核中；`approved` 按 `CommerceState` 规则显示价格；`restricted` 保留工作台与询盘入口并显示原因，价格隐藏；`rejected` 登录被拦且现有会话终止。批准后原会话下一次请求显示价格，无需重新登录。
- 询盘对所有人开放，pending 与 restricted 同样可以发送；空草稿与访客行为依照询盘开放规格。账户状态卡不接管询盘页面，restricted 的保存原因仍显示在可用表单上方。
- 登出：`customer-logout` 端点 URL 已不在任何菜单/页头链接里（只有 nonce URL）。直接访问端点 URL 时 Woo 仍会要求确认——那是 Woo 的原生行为，站点不再指向它。

## 五、文案

`docs/acceptance/2026-10-15/184/copy-review.md`（EN 先行、DE 独立撰写、Sie 体、
逐条 初稿→评审→定稿）。本轮共 **26 条**新串（25 单数 + 1 条 `_n` 复数）已入
`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` 并编译 `.mo`；
入门 `linker-commerce.pot` 同步重新生成（`wp i18n make-pot --merge`）。
`just i18n-coverage` / `just i18n-validity` 全绿。
#180 所列两处 .po 缺口经当前树核实已由上游关闭（评审记录 §9）。

## 六、测试与验收

- PHP：`composer install` 后 `vendor/bin/phpcs -q`（0 error）、`vendor/bin/phpstan analyse --memory-limit=-1`（level 8，0 error）、`vendor/bin/phpunit --testsuite unit`（999 tests 全绿，含 `AuthTemplatesTest` / `AccountStatusNoticeTest`（当时为 `PendingGateTest`，整页门禁在 #222 被状态卡取代）/ `LoginGateTest` / `AccountTemplatesTest` / `DocumentsTest` / 两个 `ModuleTest` 的新断言）。
- JS：`node --test plugins/linker-commerce/tests/js/*.test.mjs`（45 tests，含 `account-ui.test.mjs` 的 7 条：提交态不禁用按钮、提交中不重发、原生校验优先、不一致阻止提交并给字段、不一致被打回后按钮复活、行随打字清除、一致时提交）。
- e2e（`tests/e2e`，实例 a184 + `just serve`）：`specs/account.spec.ts` 12 项、`specs/empty-draft.spec.ts` 4 项、`specs/commerce.spec.ts` 2 项 **全过**。断言随新结构更新：登出选择器改 `action=logout`、登出后断言 signed-out notice、门禁选择器改 `.linker-gate` / `.linker-gate-genie-pill`、Proforma 下载从列表行（已无行内下载）改到询盘详情页的 `[data-action="proforma"]`。
- **忘记密码的真实夹具（评审 S10）**：两个语言的用例续跑整条重置链——WP-CLI 读账号自己的 `get_password_reset_key()`，`goto <lost>?show-reset-form=true&key=…&id=…` 打开重置卡，断言卡标题 / `#password_1` / `#password_2` / `reset_key` / `reset_login` / `woocommerce-reset-password-nonce` 都非空；再断言弱密码被 Woo 自带强度计挡在页面内（按钮 disabled，服务端无强度门）、两个不同密码由链自己的行当场指出（不发请求），最后用同一个卡真正保存新密码 → 落到登录卡带 Woo 的确认条 → 用新密码登录成功。德语 restricted 门禁同样有真夹具用例（德语句子 + 邮件链接 + 原因 notice 有底色）。
- **提交态不能禁用按钮**：WooCommerce 读的是被按下的按钮自身的 name/value（`login`、`register`、`save_account_details`），`disabled` 的控件不进提交数据——早先版本在提交瞬间禁用按钮，登录/注册会静默不生效（真实夹具 e2e 抓到）。`account-ui.js` 只用 `.is-loading` + `aria-busy` 表状态，重复提交由表单自身的 `data-account-state` 挡回；回归测试在 `tests/js/account-ui.test.mjs`。
- `specs/chrome.spec.ts` 的两项（德语工具页重定向）在本实例 404：该 spec 需要跑过 `tools/migrate/*.py` 的实例（tests/e2e/README 明列），a184 只装了快照 + `present`，与本票无关。
- 本地实例验证（a184，快照 2026-10-15-1852 + 本票分支）：guest 两语言登录/注册/忘记密码/重置全链、pending/restricted/两种 guest 门禁、工作台各端点 EN+DE、页头 guest/customer 下拉、一键登出落回带提示、账号四态询盘与空态。

## 七、变更台账（业主过目）

| 变更 | 裁定 | 范围 |
| :--- | :--- | :--- |
| 账号链整链重设计 | 业主 2026-10-15 验收原型通过 | guest 三页 + 重置/确认/改密覆写、四态门禁、工作台全端点、页头下拉、一键登出（含 1440/390 × EN/DE） |
| 页头 guest 下拉由两条同址收为一条 `Sign in` | 同上（原型 chrome.html） | 复刻面的像素差异点，仅在这个下拉打开时的浮层内容里 |
| 页头 `Log out` 指向 nonce URL（不再指向 `customer-logout` 端点） | 同上（业主 2026-10-15 一键登出裁定） | 只改 href；浮层样式（14px 圆角 + 阴影 + 红色登出行）沿用既有 chrome.css，未动 |

本票是"工具页重设计"裁定（2026-10-10）与"登出一键化"裁定（2026-10-15）的落地：
账号链属工具面（非复刻面），像素门不适用；登出二次确认按裁定去除。

## 八、返工轮（2026-10-16，双评审 + 视觉验收）

### 视觉（主线验收偏差）

- **V1 每张卡自带品牌面板**：`form-login.php` 的外层从"一个面板跨两卡"改为两个 `.linker-auth-unit` 单元——登录单元（面板文案 = 登录语义）与注册单元（面板文案 = 注册语义，来自原型 `register.html` 的 `.brand`）；`auth.css` 里 `.linker-auth-unit`（≥1080px 两列、`align-items: stretch`、圆角与阴影落在单元上）取代原 `.linker-auth-inner` 的两列规则，`grid-row: 1 / span 2` 删除。移动端结构不变（面板 `display: none`，两卡竖排）。
- **V2 联系人卡回到 `.panel` 骨架**：`Account/ContactCard.php` 输出 `.linker-account-panel` + `-heading` + `-body`（原型 `workspace-overview.html` 的 contact panel），body 里一行 `.linker-account-contact-line`（信封图标 + 邮箱链接；设了姓名/电话时同格排列）；样式在 `account.css`。
- **V3 restricted 原因块**：`.notice.notice-info` 的底色/边框/圆角/图标排布写进 `auth.css`（原先只有 Woo notice 的样式，我方 notice 元素是裸文本），并把 reason 块移回正文之后（原型顺序：正文 → reason → 联系方式）。

### 评审（Spec / Standards）

- **St1 目录**：`linker-commerce.pot` 用 `wp i18n make-pot … --merge` 重新生成（799 条，含本轮全部新串）；`.po` 里 26 条新条目的 `#:` 引用改为真实来源（`templates/myaccount/**`、`LoginGate.php`、`AccountTemplates.php`、`AuthTemplates.php`），句柄 `%s` 的两条串已同步 `translators:` 注释；`.mo` 重新编译；`just i18n-validity` / `just i18n-coverage` 全绿。
- **St2 页面地址解析收成一处**：新增 `Presentation/PageUrls::translated( $slug ): string`（'' 表示没有），`AccountTemplates`、`ProductShortcodes::{compare_page_url,configurator_page_url}`、`Shortcodes::contact_page_url`、`LoginGate::genie_pill` 五处调用它，回退由各调用方自己给。
- **St3 `PendingGate::output()` 委托已注册实例**：`PendingGate::register()` 记 `self::$adapter` 并挂 `template_redirect`（`Account\Module` 调它），模板只走 `self::$adapter?->render()`——不再现场 new 一个 Approval/LoginGate 与线上实例不同源的 PendingGate。
- **St4 邮件地址走占位符**：门禁两句改为 `Write to %s …` / `Until then, … write to %s …`，`mailto_sentence()` 用 `sprintf` 把 `<a mailto>` 填进去；翻译改词或换序都不会静默吞掉链接（`mails/linker-registration-received.php` 共用同一 msgid，按纯文本地址填）。德语 msgstr 同步为 `%s` 形态（copy-review §10 表注）。
- **St5 `data-count` 无消费者**：删掉 `inquiry-card.html` 的 `data-count` 与 `AccountTemplates::order_row()` 里配套的 `items-count`（列表显示的是 `items-summary` 文本），单测改为断言该键不存在。
- **S6 文案记录与实交对齐**：德语统一 `Partner-Konto`（记录 11 处）；重置卡的两个字段标签改由 linker-commerce 域打印，`Re-enter new password` 的德语定稿 `Neues Passwort wiederholen` 因此真的可达（原先落在 Woo 语言包）；计数统一为 **26 条 = 25 单数 + 1 `_n` 复数**（首轮 22 条 + V1 注册面板 4 条）。§4/§5 的字段名分叉说法改为按交付（改密语境 `bestätigen`、重置语境 `wiederholen`，与 EN 侧一致）。
- **信息项**：品牌面板 logo 换成 WebP（`assets/linker-logo-wordmark.webp`，248×94 @2x，10 KB；原 PNG 717×273 319 KB，按 124px 展示），标记 `width="124" height="47"` 不变。

### 视觉走查中自己抓到、并修掉的两处

- **Woo notice 的图标压到首字上**：WooCommerce 自带的 `.woocommerce-error/-message/-info::before` 是 `position: absolute; top: 1em; left: 1.5em`（配它自己 `padding: 1em 2em 1em 3.5em` 的盒子），而链上的 notice 是 `display: flex` + `padding: 14px 16px` 的行——图标因此正压在首词上（"You have been signed out." 的 Y 上）。修法：把 `::before` 拉回文档流（`position: static; display: block; flex: none; margin-top: 1px; font-size: 18px; line-height: 1`），成为 flex 行的第一项，与原型"图标 + 12px 间隙 + 文字"一致。
- **Woo 自己的 `frontend/lost-password.js` 在每次 submit 时禁用重置按钮**（`$('.lost_reset_password').on('submit', … attr('disabled','disabled'))`，假定页面即将离开）。重置卡在两个密码不一致时**留在页面上**，于是修正后再次点 Save 毫无反应（按钮已被禁用，只有刷新才能继续）。修法：`account-ui.js` 在打回不一致提交时调 `keepButtonLive()`，用 `setTimeout(…, 0)` 在该次事件派发全部处理完之后把按钮清回来（Woo 的处理在同一次派发内、晚于本文件）。回归测试在 `account-ui.test.mjs`：夹具照抄 Woo 的行为（submit 时禁用按钮），断言打回后按钮复活、可再次提交。e2e 的整条重置链（两个语言）也覆盖到这一步。

## 九、存量死 CSS（本轮记录，不属本票清理）

`content/windpress/storefront.css` 里 329 处 `body.sf-account-page`（及 `body.sf-account-inner` / `body.sf-account-home`）选择器**没有任何生产者**：`sf-account-page` body 类随旧 storefront 层退役（`Presentation\Module` 的 body_class 过滤器已删，`ModuleTest` 有对应说明），仓库内除 storefront.css 与该测试注释外零引用。它们是复刻层遗留的死规则，但**不属本票清理范围**：这些选择器与仍在用的规则（`.tv-b2b-*` 项目面、`body.sf-account-inner`…）混在同一条选择器列表里（例如 `body.sf-account-page .tv-b2b-bulk-order, body.sf-account-page .tv-b2b-bulk-result {}`），逐个摘除等于重写 3400 行复刻样式表里的大量混合规则，风险面远大于收益。归后续一次专门的死 CSS 清理（附像素回归）。

## 十、可翻案处

- 桌面品牌面板（≥1080px）只在登录/注册两页出现，且每张卡一个（V1）；辅助页（忘记密码、重置、确认）保持居中单卡，与原型一致。
- 移动端工作台导航只有底部胶囊栏；1024px 是侧栏/胶囊的切换点（与原型 `app.css` 一致）。
- 强度计复用 Woo 的判分与文案（`pwsL10n`），不自定义阈值；`min_password_strength` 沿用 Woo 默认 3。

## #222 第一轮评审裁定（2026-10-18）

- 账户状态适配器名为 `AccountStatusNotice`，通过 Woo 原生内容 hook 输出局部 LC 卡片；pending 与 restricted 共用组件，后者同时显示状态和保存原因。询盘页沿用同一原因片段。价格原因由 `CommerceState::reason()` 决定，包括批准后历史无价询盘的 `UNPRICED`；文案层只映射原因。账户列表、概览与详情直接共用 `PriceDisplay::shows_order_total()`，无价询盘不输出货币零值或空 Amount 标签。
- **run10 稳定性：已关闭，非代码缺陷。** [Claude 第一轮评审](https://github.com/AssassinFlash/de-linker/pull/310#issuecomment-6245533011) 确认：本地共享 Redis DB 0 在审批秒发生 Predis 读错误，graceful 模式使一次请求回退数据库、下一次读取旧缓存。产品与卡片均经 `Approval::status()` → `get_user_meta`，原生 `update_user_meta` 负责失效，并无第二个审批来源。线上只读核实没有 object-cache drop-in（`wp cache type` 为 Default），LiteSpeed Cache 不活跃，账户响应为 `private, no-cache`，因此当前线上配置不具有该故障路径。原始时间线与日志见 `docs/acceptance/2026-10-18/222/diagnostics/cache-availability.json`、`run10-failure.txt` 和 `readback.json`。不新增审批缓存、轮询或会话机制；未来启用 Redis 必须通过规格 17 的一致性条件。

前文 St3 的 `PendingGate::output()` 记录为当时实现；现已由上述原生 Woo 内容 hook 取代，无模板替换器。

## #225 注册表单两步（2026-10-19）

业主 2026-10-17 裁定变体 B（AGENTS.md §2），取代 2026-10-15 验收版的三段编号单页。

- **字段与两步**：`Registration\Fields` 定义第 1 步（`billing_company`、`linker_customer_role` 三单选、`billing_country`、`linker_company_website`、`billing_vat_id`，网站与 VAT 至少一项）和第 2 步（`billing_first_name`、`billing_last_name`；邮箱与密码仍是 Woo 模板自己的字段）。街道、邮编、城市移出注册，由 Proforma 请求页原生账单字段收；电话不收。`Account\AuthTemplates::split_field_blocks()` 把缓冲的字段切成 `company`/`verify`/`you` 三块，未知布局不丢字段。
- **呈现**：`templates/myaccount/auth/form-register.php` 一个 Woo 表单两个 pane；`account-ui.js` 加 `.is-split` 后隐藏非当前 pane、禁用隐藏 pane 的控件（浏览器不会校验看不见的必填项），Continue 先校验第 1 步；没有 JS 时两个 pane 都显示、单个 Register 提交整张表单。服务端拒绝时 `Fields::active_step()` 决定重新打开哪一步：第 1 步字段有错回第 1 步，否则停留第 2 步。
- **国家**：`CountryOptions` 用 Woo 国家表与 Europe 大洲：德国置顶、欧洲其余、其余按名排序；`CountryField` 经 `woocommerce_form_field_linker_country` 输出两个 `<optgroup>`，`account-ui.js` 初始化 Woo 的 selectWoo（`wc-country-select` 提供译名）。全部国家开放，默认德国。
- **防机器人**：`BotGuard` 在 `woocommerce_register_form` 打印 `Inquiry\PublicGuard` 的蜜罐与签名起始时间，在 `woocommerce_process_registration_errors`（优先级 20，字段校验之后、建号与发信之前）复用同一个守卫：蜜罐、时钟、过短被拒，并共用每连接每小时 3 次的原子限额。被拒计数写入 `linker_commerce_registration_blocked`（不 autoload，按原因分桶 + 最后时间），`wp linker-commerce registration-blocks [--reset]` 可读，`linker_commerce_registration_blocked` action 可接监控。
- **通知与后台**：`NewCustomerEmail` 与后台账户页都通过 `RegistrationInformation::rows()` 读同一套字段定义，网站自动出现在新客户通知与审核卡（以及卡片上的 Company website 链接）；VAT 检查与审批状态行仍附在后面。
- **验收**：`docs/acceptance/2026-10-19/225/`（EN/DE × 1440/390 两步与错误态、线上 before、机器人拦截/成功实走、Outbox 断言、文案对抗评审、变更台账）。注册卡属裁定重设计，不做整页像素相等声明。
