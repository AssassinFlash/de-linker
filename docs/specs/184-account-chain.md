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
| 登录 + 注册卡 | `templates/myaccount/auth/form-login.php`（居中两卡列） | 同文件重写：桌面 = 左深绿品牌面板 + 右两张卡（`≥1080px`），移动 = 两卡竖排；注册三步编号组保留，只重排呈现 |
| 忘记密码请求 | `templates/myaccount/auth/form-lost-password.php` | 同文件重写：单卡（`.linker-auth--solo`），`Back to sign in` 留在卡内 |
| 发送成功确认 | Woo 默认 `myaccount/lost-password-confirmation.php`（裸文本落在页底） | **新增覆写** `templates/myaccount/auth/lost-password-confirmation.php`：同一张卡，Woo 的 notice + 过滤后的说明句进卡头 |
| 重置密码表单 | Woo 默认 `myaccount/form-reset-password.php`（裸模板，链路最差一环） | **新增覆写** `templates/myaccount/auth/form-reset-password.php`：卡 + 双密码字段 + Woo 自带眼睛 + Woo 自带强度计 |
| 账户细节（改密） | Woo 默认 `myaccount/form-edit-account.php` | **新增覆写** `templates/myaccount/account/form-edit-account.php`：资料卡 + 改密卡（说明行 + 干净标签） |
| pending 门禁 | `Account/PendingGate.php` 清 workplace hook 后打印 inline 文本 | 换账页模板（`wc_get_template` 优先级 40 → `templates/myaccount/auth/pending.php`），卡片来自 `LoginGate::pending_html()`；workplace 骨架根本不渲染 |
| restricted / 空 Proforma / guest 带草稿门禁 | `Presentation/LoginGate.php` 的 `sf-checkout-empty` 文本块 | 同文件重写为卡片（badge + 标题 + 正文 + 动作）；guest 门禁两种形态（草稿空 = 取号，草稿有货 = 登录发送） |
| 工作台骨架 | `content/livecanvas/account/workspace.html` + `mobile-nav.html` | 重写：桌面 = 左侧栏（WORKPLACE/ACCOUNT 两组）；移动 = **只有底部胶囊 tab 栏**（顶部 `details/summary` 折叠菜单删除） |
| 询盘列表行 | `inquiry-card.html` 行内展开全量商品行 | 重写：`n Produkte` 摘要（`_n` 复数）+ 单号 + 状态胶囊 + 日期 + 金额 + `View` 箭头 |
| 工作台其余片段 | `overview/tiles/tile/recent/inquiry-row/summary/stage/proforma/documents/document-row/solutions/solution-card/empty*` | 全部按原型重写；`shortcuts.html` 删除（原型没有该组件） |
| 页头账户入口 | `ProductShortcodes::header_utilities`：guest 两条同址 + 登出走 Woo 端点的二次确认页 | guest 一条 `Sign in`；登出改 `linker_commerce_logout_url()`（`wc_logout_url()`，带 nonce），落回 `my-account/?signed-out=true` |
| 登出提示 | Woo 的确认页 | `AuthTemplates::signed_out_notice()` 在账号页加一条 Woo notice（`You have been signed out.`） |
| 样式 | `storefront.css` 的 account 块 + `auth.css` 的 639px 规则 + `account.css` | `auth.css` / `account.css` 整体重写为设计层（token 对齐 `tokens.css`）；`storefront.css` 删掉 account/gate 相关块 |
| JS | 无（整页 POST） | 新增 `assets/account-ui.js`：提交 is-loading（渐进增强）、双密码字段不一致行、随打字清错；强度计用 Woo 自带 |

## 二、原型态 → 实现映射

原型每页的每个态都有对应实现；`?lang=` 由 Polylang 决定，`?state=` 的写法换成真实状态。

### guest 链

| 原型 | 实现 | 触发 |
| :--- | :--- | :--- |
| `login.html?state=default` | `/my-account/`（guest）登录卡 + 注册卡 | 访客 |
| `login.html?state=error` | 同页，Woo 的 `.woocommerce-error` 在登录卡内（`You have been signed out.` 之类同容器） | 凭据错误 |
| `login.html?state=rejected` | 同页，拒因由 `Registration\Approval::login_errors()` 写进同一条错误条 | 被拒账号登录 |
| `login.html?state=reset-success` | 同页，Woo 的 `.woocommerce-message`（`password-reset=true`） | 重置成功 |
| `login.html?state=signed-out` | 同页，Woo 的 `.woocommerce-info`（`signed-out=true`） | 一键登出后 |
| `login.html?state=loading` | 提交瞬时（`account-ui.js` 给按钮 `.is-loading`） | 提交 |
| `register.html?state=default/errors/loading/password-shown` | 注册卡（三步、法务链接、Privacy 链接按 `get_privacy_policy_url()` 存在时出） | 访客 |
| `lost-password.html?state=default` | `/my-account/lost-password/` 单卡 | 访客 |
| `lost-password.html?state=sent` | 同路径 `?reset-link-sent=true` → 确认卡 | 发送成功 |
| `lost-password.html?state=invalid-key` | 同路径，Woo 的错误条在卡内 | 无效/已用 key |
| `reset.html?state=default/mismatch/weak/loading` | `?show-reset-form=true` 的重置卡；不一致与过弱由 Woo 服务端校验（通知）+ `account-ui.js` 前端即时行 | 邮件链接落地 |
| `chrome.html` | 页头账户下拉：guest 一条；customer 菜单 + `Log out`（红色，带分隔线） | 任意页 |

### 门禁

| 原型 | 实现 | 触发 |
| :--- | :--- | :--- |
| `gates.html?gate=pending` | `/my-account/`（pending 账号）与空的 `/proforma-request/`：同一张卡（badge `Under review`） | `Approval::PENDING` |
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

- `Approval` 三态：`pending`（可登录，只见审核卡；任何 endpoint 请求 302 回 `/my-account/`）、`restricted`（工作台在，价格与 Proforma 请求暂停）、`rejected`（登录被拦，登录卡显示拒因）。
- 空 Proforma 请求：guest 两种门禁（按草稿有无）；approved 空草稿 = 空态卡；无审批账号 = 对应门禁卡。`[linker_checkout]` 在 guest 上**总是**走门禁（访客没有 checkout 资格）。
- 登出：`customer-logout` 端点 URL 已不在任何菜单/页头链接里（只有 nonce URL）。直接访问端点 URL 时 Woo 仍会要求确认——那是 Woo 的原生行为，站点不再指向它。

## 五、文案

`docs/acceptance/2026-10-15/184/copy-review.md`（EN 先行、DE 独立撰写、Sie 体、
逐条 初稿→评审→定稿）。新增 21 条 msgid 已入
`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` 并编译 `.mo`
（`_n` 复数条目一条）。`just i18n-coverage` / `just i18n-validity` 全绿。
#180 所列两处 .po 缺口经当前树核实已由上游关闭（评审记录 §9）。

## 六、测试与验收

- PHP：`composer install` 后 `vendor/bin/phpcs -q`（0 error）、`vendor/bin/phpstan analyse --memory-limit=-1`（level 8，0 error）、`vendor/bin/phpunit --testsuite unit`（974 tests 全绿，含 `AuthTemplatesTest` / `PendingGateTest` / `LoginGateTest` / `AccountTemplatesTest` / `DocumentsTest` / 两个 `ModuleTest` 的新断言）。
- JS：`node --test plugins/linker-commerce/tests/js/*.test.mjs`（21 tests，含 `account-ui.test.mjs` 的 5 条：提交态、原生校验优先、不一致阻止提交并给字段、行随打字清除、一致时提交）。
- e2e（`tests/e2e`）：账号链相关断言已随新结构更新（登出选择器改 `action=logout`、签名后断言 signed-out notice、门禁选择器改 `.linker-gate` / `.linker-gate-genie-pill`）。
- 本地实例验证（a184，快照 2026-10-15-1852 + 本票分支）：guest 两语言登录/注册/忘记密码/重置全链、pending/restricted/两种 guest 门禁、工作台各端点 EN+DE、页头 guest/customer 下拉、一键登出落回带提示、账号四态询盘与空态。

## 七、变更台账（业主过目）

| 变更 | 裁定 | 范围 |
| :--- | :--- | :--- |
| 账号链整链重设计 | 业主 2026-10-15 验收原型通过 | guest 三页 + 重置/确认/改密覆写、四态门禁、工作台全端点、页头下拉、一键登出（含 1440/390 × EN/DE） |

本票是"工具页重设计"裁定（2026-10-10）与"登出一键化"裁定（2026-10-15）的落地：
账号链属工具面（非复刻面），像素门不适用；登出二次确认按裁定去除。

## 八、可翻案处

- 桌面品牌面板（≥1080px）只在登录/注册两页出现；辅助页（忘记密码、重置、确认）保持居中单卡，与原型一致。
- 移动端工作台导航只有底部胶囊栏；1024px 是侧栏/胶囊的切换点（与原型 `app.css` 一致）。
- 强度计复用 Woo 的判分与文案（`pwsL10n`），不自定义阈值；`min_password_strength` 沿用 Woo 默认 3。
