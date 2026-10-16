# #201 同意横幅与 GA4（Complianz 免费版 + WP Consent API + Site Kit Analytics）

## 是什么

线上 de-linker.com 有同意横幅：第一层同等「接受全部 / 拒绝全部」（EN 与 DE 各一套独立文案），GA4 经 Site Kit 接入，Consent Mode 落在 Google 定义的 **Basic**——访客对「统计」作答之前，浏览器不向 Google 加载任何资源、不发送任何请求。WooCommerce 订单来源（Sourcebuster，`sbjs_*`）纳入横幅的「营销」类：同意前不写、同意后照常记录。撤回与同意一样容易（每个页面页脚的「Cookie-Einstellungen / Cookie settings」）。本条链路与 #145 的 Search Console 连接共用 Site Kit，**不 Reset、不 Disconnect、不删连接者用户**。

## 载体（选型证据：`docs/research/2026-10-16/consent-ga4-carrier.md`，本机实测五条）

- **Complianz（免费版 `complianz-gdpr` 7.5.6）**：横幅、脚本阻断器、同意记录。免费版没有按访客地理位置切换法域的开关（`settings/config/fields/wizard/general.php` 的 `regions` 是单值 radio，`other_region_behaviour` 只在 premium 的 `use_country` 下生效，见实测 5），因此选定的 EU/GDPR 规则对每个访客生效——这正是本网站要的（站点由德国主体经营，TDDDG §25 的同意要求不分访客所在地）。
- **WP Consent API（`wp-consent-api` 2.1.0）**：`wp_has_consent()`/`wp_set_consent()` 与 `wp_listen_for_consent_change` 事件，横幅与各插件之间的唯一接口。
- **Site Kit by Google（#145 已装 1.189.0）**：在其中连接 Analytics；Site Kit 自己的 Consent Mode 开关打开（它决定是否在页面上打印 consent defaults）。**Complianz 自己的 Consent Mode 不开**（`cmplz_options['consent-mode'] = 'no'`）——两个都开会打两份 defaults。
- **Complianz 配置是数据**：`tools/migrate/201-consent.py` 从 `tools/migrate/201-consent.json` 写入线上并读回（`plan`/`apply --write`/`verify`），不走后台手点、不走 Code Snippets。

### 为什么还需要仓库插件的 `Consent\Blocking`（三件套原生优先的穷尽证明）

客户可见面的默认实现顺序是 LC 原生 tag → Woo 原生机制 → WindPress 管线，自定义代码是最后手段。本条链路的四件事里三件由原生机制承接，第四件原生的两条路都走不通，逐项如下：

| 事 | 谁做 | 依据 |
|---|---|---|
| 横幅、第一层双按钮、同意记录、撤回 | Complianz 原生 | 本票实测 2/12 |
| 「统计」→ `analytics_storage`、「营销」→ 订单来源 | WP Consent API + WooCommerce 原生（`WPConsentAPI::$consent_category = 'marketing'`，`wc_order_attribution_allow_tracking` 经 `wp_has_consent()` 门控；`src/Internal/Integrations/WPConsentAPI.php`） | 实测 1（同一个探针里 `sbjs_*` 只在营销同意后出现） |
| consent defaults 全 denied | Site Kit 原生 `googlesitekit_consent_defaults` 过滤点 + 本插件把 `region` 键去掉 | 见下 |
| **拦住 gtag.js** | **原生的两条路都走不通**：Complianz 的 Site Kit 集成把 `google_gtagjs-js`/`google_gtagjs-js-after` 加进阻断器的白名单（`integrations/plugins/google-site-kit.php`），而白名单在白名单检查里先于一切阻断规则命中（`class-cookie-blocker.php` 的 `whitelisted_scripts()`）；Complianz 免费设置里没有关掉它的开关，Site Kit 侧也没有。**实测 1 记录了这个默认行为：横幅出现之前 `_ga` 已写、`gtag.js` 已加载、`page_view` 已发出。** | 最小后备：在两家自己的过滤点上做接线，零设计决策（`Consent\Blocking`，3 个 filter + 1 段 cookie 清理） |

`Consent\Blocking` 只做四件数据/行为接线，不产生任何样式、不输出任何可见标记：

1. `cmplz_whitelisted_script_tags`：把 `google_gtagjs-js` 与 `google_gtagjs-js-after` 从白名单摘掉（阻断器从此把标签扣在 `type="text/plain" data-category="statistics"`），保留 consent-definitions 内联片段本身（它必须在横幅之前执行，且白名单按子串匹配，所以它单独一条精确项）。
2. `googlesitekit_consent_defaults`：去掉 `region` 键。Site Kit 默认只对欧洲区列表内的访客写 denied defaults，列表外 Google 视为全部 granted——本机（不在列表内）实测：点任何东西之前 `_ga` 已写、`page_view` 已发。站点对每个访客都要同意，所以 defaults 对每个访客都是 denied。
3. `googlesitekit_consent_category_map`：`marketing => []`。站点没有 Google 广告标签，`ad_storage`/`ad_user_data`/`ad_personalization` 保持 denied——对「营销」说 yes 不给 Google 任何权限（营销类的实际含义是 WooCommerce 自己的订单来源）。
4. `_ga`/`_ga_<stream>` 的撤回清理：挂在 WP Consent API 自己的脚本上（`wp_add_inline_script`），在「统计」不是 allow 时（同意变更事件 + 每次页面加载，覆盖在另一个标签页里撤回的情况）按键名删除。Complianz 免费只删它 cookie 数据库里的 cookie（`cookie-statement: none` 时该库为空），GA4 不会自己删自己的 cookie——不删就没有真正的撤回。

## 横幅与 GDPR 口径（数据，不是代码）

`tools/migrate/201-consent.json` 是本文件之外的唯一一份数值来源，迁移脚本逐字写库：

- 两个可选目的：**Statistics**（Google Analytics，Google Ireland Limited，可能传 Google LLC USA；`_ga`、`_ga_…`，实测保存期 400 天——本机探针读数，2026-10-16；默认值，我们没有配置过它）与 **Marketing**（我们自己的来源记录：`sbjs_*`，实测为会话 Cookie，其中 `sbjs_session` 30 分钟；随询盘保存，不转交第三方）。`Preferences` 目的关闭（站点不设偏好 cookie）；该类目的说明文字**不写进迁移**——Complianz 在 `save()` 里用它的默认值回填空串（实测），写它只会制造假漂移。
- 第一层按钮：`Accept all` / `Reject all`（同等，两个都是第一层可见）；`Choose purposes` 展开逐目的开关。位置 `bottom-right`，无关闭按钮（`close_button: 0`），不随滚动/超时消失。
- 调色板取站点 token（`#0c7f73` 主色、`#ffffff` 面板、8px 面板圆角、6px 按钮圆角、13px 字号），数据写在 JSON 里。
- `manage_consent_options: hide-everywhere`（Complianz 自己的浮动 tab 关掉）：撤回入口在页脚（LC partial EN/DE），见下。
- 文案的起草、对抗评审与修订记录：`docs/acceptance/2026-10-16/201-consent/copy-review.md`（EN 先行、DE 独立撰写）。

## 页脚入口与隐私政策（客户可见的另外两处，都是裁定过的变更）

- **页脚「Cookie settings / Cookie-Einstellungen」**：LC partial 的仓库源文件 `plugins/linker-commerce/content/livecanvas/partials/footer.html` 与 `partials/de/footer.html`（`present` 把它们装进 LC——与其他 partial 变更同一条通道），在 `.tv-footer-bar-legal` 行各加一个 `<button type="button" class="cmplz-manage-consent">` 及它的一条样式（既有 partial 自带的 `data-site-css` 块内，与旁边的链接同款）。Complianz 的 JS 用事件委托监听 `button.cmplz-manage-consent`（`cookiebanner/js/complianz.js` 的 `cmplz_add_event( 'click', 'button.cmplz-manage-consent', … )`，处理器把横幅状态置回 `show`），点它即重开横幅；按钮本身是站点设计，不是插件 tab 的样式（插件的 tab 用 `hide-everywhere` 关掉；插件所有 `.cmplz-manage-consent` 规则都限定在 `#cmplz-manage-consent` 容器下，页脚这颗在容器外，因此不会被插件的 `display:none` 波及）。不加 `href`，不加内联样式。
- **隐私政策**：EN `privacy-policy`（ID 1673）与 DE `datenschutz`（ID 6827）的第 3 节（Cookies）与第 4 节（Recipients and transfers）——现文「不使用分析、广告或跟踪 Cookie」在 GA4 接入后不再成立；第 4 节的处理器表加一行 Google（Google Ireland Limited, EU；transfer to Google LLC in the USA）。两节都与线上既有版式同构（同一 `lg-*` 结构），只改文字与一行表格。

## 检查

| 检查 | 谁跑、何时 | 断什么 |
|---|---|---|
| `just cutover verify` 的 `consent` 段（`steps.consent`） | 每次写线上之后，对生产主机；`--target local:…` 与 `drill` 不跑这一段 | 三个插件启用；Complianz 横幅开、阻断器开、Complianz 自己的 consent mode 关；横幅行两个可选目的（统计、营销）都有文案；Site Kit Analytics 已连（`measurementID` 非空）且 Consent Mode 开；首页 HTML 里 `//www.googletagmanager.com/gtag/js` 没有可执行形式（只有被阻断的 `type="text/plain"`），且 consent defaults 内联片段在。任一不成立退出码 1 |
| `tests/e2e/specs/consent.spec.ts` | 评审站回归（`just e2e <实例>`） | 横幅在、第一层两个按钮同等、拒绝后无 Google 请求、无 `sbjs_*`、`_ga` 不存在；接受后 `type` 恢复为可执行、`sbjs_*` 出现；页脚入口把横幅找回、撤回后 `_ga` 与 `sbjs_*` 被清。评审站页面有本地 CSP（`tools/local/mu/000-linker-local-isolation.php`），Google 请求出不去，所以断言落在机制上（标签 type、dataLayer、cookie），这一点在 spec 里写明 |
| `plugins/linker-commerce` 的 PHPUnit（`Unit/Consent/BlockingTest.php`） | `just php-test` / CI | 三个 filter 的行为：白名单摘除与保留、`region` 键去除、`marketing` 置空、清理脚本只在 WP Consent API 脚本在队时挂上 |
| 视觉验收 | 1440 / 390 × EN / DE，横幅各状态截图 | 横幅本身就是裁定过的变更；横幅关闭后其余像素 0 差异（`docs/acceptance/2026-10-16/201-consent/`） |

## 所有者侧（角色名；真实账号只在营销侧私有 vault）

所有者账号建 GA4 账号 + 媒体资源（时区 Europe/Berlin、币种 EUR）+ 网站数据流；日常账号加账号层管理员；服务账号加查看者；**在 Site Kit 里连 Analytics**（#145 只连了 Search Console：2026-10-16 线上读回 `googlesitekit_analytics-4_settings` 为空对象、`googlesitekit_active_modules` 不存在）。这一步没做之前线上一行 Google 标签都不打印——`consent` 段的 Analytics 断言会红，这是设计使然。

## 变更记录

- 2026-10-16（#201）：首版。载体为 Complianz 7.5.6 + WP Consent API 2.1.0 + Site Kit 1.189.0；`Consent\Blocking` 是本票唯一的仓库代码（前言穷尽证明）；横幅文案与隐私政策两节的评审见 `docs/acceptance/2026-10-16/201-consent/copy-review.md`。

- 2026-10-16（#201，前提修正，按证据）：票面把「Complianz 挡不挡 Site Kit 的 gtag.js」列为待测项、把「Site Kit 的 Consent Mode 打开」当作设置动作。本机实测把两处收窄为：①挡不住是**确定行为**（白名单先于阻断规则命中），不是偶然，所以仓库插件的最小后备是必需项而不是可选项；②Site Kit 的 Consent Mode 分段打印 defaults（欧洲区列表内才 denied），仅打开开关不足以让列表外访客也走 Basic——`Consent\Blocking` 的 `deny_everywhere` 是这个缺口的补丁。两条都记在 `docs/research/2026-10-16/consent-ga4-carrier.md` 的实测 1 与实测 4。
