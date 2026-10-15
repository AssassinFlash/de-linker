# 登录注册链路盘点（现状清单）

日期：2026-10-15。范围：https://de-linker.com/my-account/ 及整条认证链（登录、注册、忘记密码、重置、审批三态、登录后工作台），桌面端 + 移动端，EN + DE。
素材：线上截图 + 本地实例 t73（快照 20261015-1852，仓库 main 插件）真实流程走查（注册→审批→登录→改密→登出全程实操）。截图在 `assets/current-state/`。

## 一、链路总览

```
入口（页头人形图标 / 移动汉堡内人形图标 / 页脚 Account 面板
      / PDP「Sign in for partner pricing」价格门 / Proforma 请求门）
  │
  ▼
/my-account/（guest）= 登录卡 + 注册卡（同页上下排列）
  │                                    │
  │ 登录成功                           │ 注册成功（自动登录）
  ▼                                    ▼
工作台（approved）              「Your account is under review」（pending）
                                       │
                  团队审批 ──┬─ approved → 邮件通知 → 工作台全开
                             ├─ restricted → 邮件+原因 → 工作台在，价格/Proforma 暂停
                             └─ rejected → 邮件+原因 → 不能登录（登录表单显示拒因）

忘记密码环：登录卡「Lost your password?」→ /my-account/lost-password/
  → 填邮箱 → 「已发送」确认 → 邮件链接 → 重置表单（有效 key）→ 成功回登录卡
```

## 二、页面清单（guest 侧）

### 1. 登录 + 注册页（同一页）
- URL：EN `/my-account/`；DE `/de/mein-konto/`。
- 模块：居中卡片列。① 登录卡：标题 Sign in + 副文案、用户名/邮箱、密码（眼睛切换）、Remember me、Log in、Lost your password?、移动端另有「Create your business account」锚点链接。② 注册卡：标题 Create your business account + 「We review every new account before activation.」、三步编号分组（1 Company：公司名/业务类型 Installer·EPC·Distributor/VAT ID 选填含 VIES 说明；2 Contact and address：姓名/国家默认德国/街道/邮编/城市；3 Sign-in details：邮箱/密码）、Terms of Sale 链接、Register 按钮。
- 截图：`live-en-desktop-login.png`、`live-en-desktop-register-step12.png`、`live-en-desktop-register-step3.png`、`live-en-mobile-login.png`、`local-mobile-register-step3.png`。
- 状态：
  - 登录失败：登录卡顶部红标错误条「The username or the password is not correct.」，用户名保留、密码清空（`local-mobile-login-error.png`）。
  - 被拒绝账号登录：错误条换成拒因说明「This account is not approved for sign-in. We have emailed you the reason. …」（`local-mobile-login-rejected.png`）。
  - 注册校验：必填空值先被浏览器原生校验拦（注册表单无 `novalidate`；登录表单有——两者不一致）；过浏览器后服务器错误以 Woo notice 列在注册卡顶部（每条「X is a required field.」/邮编非法/业务类型必选）。
  - 重置密码成功后回到此页：`?password-reset=true` + 绿色成功条（`local-mobile-reset-success.png`）。
  - 注册成功：自动登录 → pending 审核页（见下）。

### 2. 忘记密码请求页
- URL：`/my-account/lost-password/`（入口：登录卡链接）。
- 模块：居中卡片：标题 Reset your password + 说明、用户名/邮箱、Reset password 按钮、Back to sign in。
- 截图：`live-en-desktop-lost-password.png`。
- 状态：
  - 发送成功：`?reset-link-sent=true`，绿勾条 + Woo 说明段落——**不在卡片里**，裸文本直接落在页面底色上（`local-mobile-reset-sent.png`）。
  - 无效/已用 key：红标错误条「This key is invalid or has already been used…」+ 回到请求表单（`live-en-mobile-reset-invalid-key.png`）。

### 3. 重置密码表单（邮件链接落地页）——断点 1
- URL：`/my-account/lost-password/?show-reset-form=true&…`（邮件里的链接）。
- 现状：**Woo 默认模板，没有覆写**（AuthTemplates 只接管登录卡和忘记密码请求卡）。无卡片、无标题层级，「Enter a new password below.」+ 两个密码框 + 左对齐小 Save 按钮——与登录/注册卡完全两套视觉。客户从邮件点链接落地的恰恰是这个页面。
- 截图：`local-mobile-reset-form-default-woo.png`。

### 4. 入口点现状
- 桌面页头：人形图标按钮开下拉——guest 显示「Sign in」+「My account」**两条指向同一 URL**（冗余）；登录后显示完整账户菜单（含 Log out）。
- 移动汉堡菜单内：购物车图标 + 人形图标（`live-en-mobile-menu.png`）。
- 页脚 Account 面板：Sign in / Solution draft / FAQ & Downloads。
- PDP 价格门：「Net price after partner sign-in」+「Sign in for partner pricing」按钮 → my-account（`live-en-desktop-pdp-price-gate.png`）。
- 空 Proforma 请求门（guest 访问 `/proforma-request/` 且草稿为空）：「Get your Proforma」+ Genie pill + 两个按钮——纯文本页，无卡片（`live-en-desktop-empty-checkout-gate.png`）。
- **guest 草稿非空**访问 `/proforma-request/`：顶部「Already have an account? Log in」提示条，点开是 **Woo 默认内联登录表单**（第三套样式：小灰按钮、无卡片），下方文案「Please log in to request a Proforma invoice. No account yet? Register on the account page.」（`local-mobile-checkout-guest.png`、`local-mobile-checkout-inline-login.png`）。

## 三、审批三态页面

| 状态 | 行为 | 页面 |
|---|---|---|
| pending | 可登录；账户区整页替换为审核页；任何 endpoint URL 被弹回 /my-account/ | 「Overview / Your account is under review…」纯文本页 + Browse products 按钮，无卡片（`local-desktop-pending-review.png`） |
| restricted | 工作台保留（询盘/方案/文档/公司可见）；价格与 Proforma 请求暂停 | Proforma 请求页显示「Access currently limited」+ Our reason + 联系邮箱，纯文本页（`local-mobile-restricted-gate.png`） |
| rejected | **不能登录**（密码正确也拦在登录表单）；已登录会话被销毁 | 登录卡错误条显示拒因与申诉邮箱（`local-mobile-login-rejected.png`） |

## 四、登录后工作台（approved）

骨架：LC 模板 `account_page.html` + LC 片段（`content/livecanvas/account/*.html`）。桌面=左侧栏（WORKPLACE：Overview/Inquiries/Saved solutions/Documents；ACCOUNT：Company/Account details/Log out）+ 右内容；移动=顶部「Account menu」折叠条 **+ 底部固定 tab 栏（Overview/Inquiries/Documents/Account）——双导航并存**。

| # | 页面 | URL | 模块 | 截图 |
|---|---|---|---|---|
| 1 | Overview | `/my-account/` | 欢迎头（头像字母+姓名）、4 个状态磁贴（可点→跳到筛选后的询盘列表）、Recent inquiries 5 行、Documents 入口 3 行、Your contact person 卡 | `local-desktop-dashboard.png`、`local-mobile-dashboard.png`、DE `local-de-mobile-dashboard.png` |
| 2 | Inquiries | `/my-account/inquiries/` | All inquiries / Open inquiries 两个 tab；行=单号+**全量商品行**+状态胶囊+日期+金额+View+Request again；分页 Previous/Next；`?inquiry-status=` 筛选 | `local-desktop-inquiries.png` |
| 3 | Inquiry 详情 | `/my-account/inquiry/<id>/` | 四态进度条（当前态高亮）、概要卡、商品明细（含 Datasheet PDF 链接）、小计/VAT/合计、Request again、Company details；已开票时有 Proforma 下载 | `local-desktop-inquiry-detail.png` |
| 4 | Saved solutions | `/my-account/saved-solutions/` | 方案卡（标题/保存日期/商品行/Add to solution draft/Design report PDF）；空态文案 | `local-desktop-saved-solutions-empty.png` |
| 5 | Documents | `/my-account/documents/` | Proforma 发票+设计报告下载行（带 nonce 的私有下载 URL）；空态文案 | `local-desktop-documents-empty.png` |
| 6 | Company | `/my-account/company/` | 公司地址卡 + Edit Company details → `/my-account/company/billing/` 预填表单（含 VAT ID；德国无州字段） | `local-desktop-company.png`、`local-desktop-company-edit.png` |
| 7 | Account details | `/my-account/edit-account/` | 姓名/显示名/邮箱、改密码三字段（当前/新/确认）、Save changes；保存后 Woo notice | `local-desktop-account-details.png` |
| 8 | Log out | `/my-account/customer-logout/` | **不是直接登出**：先出 Woo 确认提示「Are you sure you want to log out? Confirm and log out」（`local-mobile-logout-confirm.png`） | |

## 五、邮件链（本地实例实发验证）

| 触发 | 收件人 | 主题 |
|---|---|---|
| 注册提交 | 客户 | We received your partner registration |
| 注册提交 | 团队 | New customer: {公司名} |
| 审批通过 | 客户 | Your partner account is approved |
| 设为受限 | 客户 | Your partner account access is limited（含原因） |
| 设为拒绝 | 客户 | Your partner account was not approved（含原因） |
| 忘记密码 | 客户 | Reset your password for Linker（WP 核心模板，非 Woo 卡片邮件） |
| 密码已改 | 管理员 | [Linker] Password Changed（WP 核心） |
| VIES 复核失败 | 团队 | VAT review（代码在，本次未触发） |

注册**不发** Woo 的 customer_new_account 邮件（未重复欢迎信）——现状正确。

## 六、发现的断点与缺口（按严重度）

1. **德语页 Woo 原生字符串全是英文**。根因已查明（2026-10-15，线上 SSH 只读核实）：**线上 `wp-content/languages/` 目录根本不存在**——WP 核心与 WooCommerce 的德语语言包从未安装过。影响面=所有 text domain 为 `woocommerce` 与 `default`（WP 核心）的字符串：德语登录/注册/忘记密码页的标签与按钮、地址字段标签、全部 Woo notice（"Password reset email has been sent."、"Are you sure you want to log out?"…）、checkout/Proforma 表单标签、WP 核心邮件（重置密码、密码已改通知）（证据：`live-de-desktop-login-mixed-language.png`）。**不缺的部分**：页面内容（Polylang 翻译）与我们插件自有文案（插件自带 de_DE_formal .po/.mo 随插件发布）都是德语——所以网站大部分看起来是德语，唯独 Woo/WP 核心的字符串漏英文。修法很简单：`wp core language install de_DE_formal` + Woo 的 de_DE_formal 语言包（WP-CLI 装一次即可）；但要在部署流程里钉住，否则下次部署/快照会被抹掉。**这是缺陷，超出「重设计」范围，建议单独修。**
2. **重置密码表单是 Woo 默认模板**（邮件落地页，链路里视觉最差的一环）——见上断点 1。
3. **注册无邮箱验证环节**：注册即可登录（pending），邮箱从未被验证；参考图 1 的 OTP「Verify Code」在本站不存在。→ **业主 2026-10-15 裁定：不加邮箱验证，现阶段不做这么复杂。**
4. **三处门禁页（pending / restricted / 空 Proforma）是纯文本页**，与登录注册卡片的视觉语言不一致；guest 有草稿时的 Proforma 请求页是 Woo 默认内联登录表单（第三套样式）。
5. **移动端账号区双导航**：顶部折叠菜单 + 底部固定 tab 栏重复。
6. **询盘列表行内全量商品行**：10 个商品的询盘行占一屏多，列表不可扫读。
7. 页头 guest 下拉「Sign in」+「My account」两条同址冗余。
8. 注册卡只有 Terms of Sale 链接，无隐私政策链接（隐私政策页未设置）。
9. 所有表单是整页 POST：无加载态（无 spinner/disabled）、无防重复提交视觉。
10. 边角：`/my-account/company/edit/`（无效地址类型）回退渲染空的 shipping 表单而非 404；登录表单有 `novalidate`、注册表单没有（校验体验不一致）。
11. 无社交登录（参考图 1 有 Apple/Google/Facebook）→ **业主 2026-10-15 裁定：不做。**

## 七、业主裁定与遗留问题

已定（2026-10-15）：
- 社交登录：不做。
- 邮箱验证：不加，保持现状（注册→pending→审批）。
- 登出：**改一键登出**，去掉 Woo 的二次确认（重设计范围内实现）。

待业主拍板：
- 清单完整性：以上页面/状态/邮件有没有遗漏？

已定（2026-10-15 补充）：德语语言包缺失**并入本工程修复**——当日已完成：根因=线上只有旧站遗留的 de_DE 非正式体 WP 核心包、WooCommerce 无德语包、WP 不在 formal/非 formal 间回退；线上已装 de_DE_formal 双包并读回验证（德语登录页全德语）；部署通道钉住见 PR #181（cutover deploy 新增语言包步骤）。票 #178。
