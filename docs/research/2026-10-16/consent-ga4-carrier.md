# #201 载体调研与五项实测：Complianz 免费版 + WP Consent API + Site Kit Analytics

问题：de-linker.com 要一条**同意先行**的统计链路——访客对「统计」作答之前，浏览器不与
Google 发生任何联系（Consent Mode **Basic**）；WooCommerce 订单来源（`sbjs_*`）归「营
销」类，同意前不写；撤回与同意一样容易。载体只能是 wordpress.org 免费插件（不买新插
件），配置要能作为数据写库并读回。

环境：本地实例 t201（`docs/local-stack.md` 的栈；Complianz `complianz-gdpr` 7.5.6、
WP Consent API 2.1.0、Site Kit 1.189.0、WooCommerce 11.2.0、Polylang 3.8.10），
2026-10-16 实测。浏览器测量仪器：`.scratch/t201/consent-probe.mjs`（副本在
`docs/acceptance/2026-10-16/201-consent/evidence/`）——放行 CSP，让 `gtag.js` 真加载
（同意处理是上游那份），每条到 Google 的采集请求都被拦截记录、不发出；记录每个阶段的
`gcs`/`gcd`、脚本 `type`、Cookie 与 dataLayer。线上侧只有只读检查（插件表、选项、响应头、
HTML）。

## 选型结论

| 角色 | 载体 | 为什么不是别的 |
|---|---|---|
| 横幅、阻断、同意记录 | Complianz 免费版 7.5.6 | wordpress.org 免费；第一层可做同等「接受/拒绝」+「选择目的」；阻断器按类别扣脚本；设置全在数据库（`cmplz_options` + `wp_cmplz_cookiebanners`），可迁移 |
| 同意状态接口 | WP Consent API 2.1.0 | WooCommerce 11.2 原生对接它（`src/Internal/Integrations/WPConsentAPI.php`），Complianz 也对接它；横幅与插件之间不需要我们写一行桥接 |
| 统计标签 | Site Kit 1.189.0（#145 已装已连 Search Console） | 业主裁定「在其中连接 Analytics」；标签与 consent defaults 都由它打印 |
| 多语言 | Polylang 的 WPML API 兼容层 + Complianz 自己的字符串注册 | Complianz 的横幅字段经 `icl_register_string`/`wpml_translate_single_string` 走 WPML 接口，Polylang 提供同一个接口（`src/modules/wpml/wpml-api.php`），不装第二个插件（实测 5） |

独木难支的那一件：**Complianz 挡不住 Site Kit 的 `gtag.js`**（实测 1），需要仓库插件里
一段最小接线（`Linker\Commerce\Consent\Blocking`，三个 filter + 一段 cookie 清理，零设计
决策）。逐条穷尽证明见 `docs/specs/201-consent-ga4.md`。

## 实测 1：Complianz 能否在执行前挡住 Site Kit 已入队的 `gtag.js`？

**不能。** 机制：`integrations/plugins/google-site-kit.php` 的
`cmplz_google_site_kit_whitelisted_script_tags()` 把 `google_gtagjs-js`（标签脚本本身）
与 `google_gtagjs-js-after`（标签后的内联配置）放进 `cmplz_whitelisted_script_tags`；阻断
器先查白名单、命中即跳过（`class-cookie-blocker.php` 的 `whitelisted_scripts()` 与它的
调用点），所以白名单优先于任何阻断规则。Complianz 免费设置里没有关掉这个集成的开关
（`cmplz_google_site_kit_filter_fields()` 只摘掉的是 `configuration_by_complianz`、
`gtag-basic-consent-mode` 等字段），Site Kit 侧也没有。

留证（同一台实例、同一探针，只差一个临时 mu-plugin 恢复上游白名单）：

| | 上游默认（白名单在） | 仓库插件的接线（白名单摘掉） |
|---|---|---|
| 页面加载后、点任何按钮之前 | `gtag.js` **已加载**（脚本 `type` 无阻断标记）、`before-consent` 阶段已发出一条到 `google-analytics.com` 的采集请求（`gcs=G100`、`gcd=13p3p3p3p5l1`、`en=page_view`） | 无任何到 Google 的请求；`#google_gtagjs-js` 的 `type="text/plain"`，`data-category="statistics"` |
| 证据 | `.scratch/t201/evidence/m1-baseline-complianz-default.json`（= acceptance 的 `evidence/m1-baseline-complianz-default.json`） | `.scratch/t201/evidence/m2-deny-blocking.json`、`m1-accept-blocking.json` |

读数只报观测：默认全 denied 时请求里的 `gcs=G100`，统计已同意、广告位未同意时
`gcs=G101`——两位数字里只有最后一位变了，而那正是 `analytics_storage` 从 denied 变
granted 的那一次。要点在**请求照发**：这正是 Advanced 模式的形状（无 cookie 的
ping），不是 Basic；Basic 的要求是**连请求都没有**。因此默认集成不满足票面目标，
仓库插件的接线是必需项，不是优化项。

## 实测 2：放行后 dataLayer 的 consent update 生效吗（GA4 请求的 `gcs` 为已同意）？

**生效。** 接受路径（`m1-accept-blocking.json`）：点「接受全部」之后 `gtag.js` 才加载，
随后发出的采集请求带 `gcs=G101`（就是实测 1 里那个末位变化的位）、`gcd=13p3r3p3p5l1`（与全 denied 时的 `13p3p3p3p5l1` 相比 `r` 位出现）、`en=page_view`。广告位保
持 denied，因为 `Consent\Blocking` 把 `googlesitekit_consent_category_map` 的
`marketing` 置空：站点没有 Google 广告标签，「营销」的实际含义是 WooCommerce 自己的订单
来源（票面「不做」一节的 `ad_*` 要求由此满足）。

同一份证据里的 Cookie 侧：接受之前 `[]`；接受之后 `_ga`、`_ga_T201LOCAL0`（`_ga_<stream>`）
与 `sbjs_current`、`sbjs_current_add`、`sbjs_first`、`sbjs_first_add`、`sbjs_migrations`、
`sbjs_session`、`sbjs_udata` 出现；刷新后保持。`sbjs_*` 不是我们写的：WooCommerce 的
`WPConsentAPI` 把订单来源归到 WP Consent API 的 `marketing` 类
（`WPConsentAPI::$consent_category`），`wc_order_attribution_allow_tracking` 用
`wp_has_consent( 'marketing' )` 门控（`src/Internal/Integrations/WPConsentAPI.php`）。

拒绝路径（`m2-deny-blocking.json`）：全过程**零** Google 请求，`_ga` 与 `sbjs_*` 至始
至终不存在，`gtag.js` 的 `type` 保持 `text/plain`，刷新后不变。

## 实测 3：缓存 / 延迟合并 JS 会不会打乱「default → 横幅 → 放行」的顺序？

**不会，这一层在线上不存在。** 2026-10-16 只读实测：

- `wp plugin list`（线上）：无 `litespeed-cache`、无任何页面缓存插件；启用的是
  `redis-cache`（对象缓存——存选项与 transient，不产出 HTML）。
- 线上响应头（`/privacy-policy/`，两次请求）：只有 `server: LiteSpeed`、
  `x-powered-by`、`strict-transport-security`、`x-frame-options`、`x-content-type-options`，
  **没有任何 `x-litespeed-cache`、`cache-control`、`age` 或 CDN 头**；两次响应体逐字节相
  同（同一 md5）。这与仓库此前的线上测量一致（`docs/research/2026-10-09/i18n-audit.md`
  「页面缓存」行：HTML 响应无 `x-litespeed-cache` 头，页面缓存实际未生效）。
- 页面内的顺序由 PHP 打印顺序决定，实测（本地实例 = 线上同一份插件与选项）：
  Site Kit 的 consent-defaults 内联片段（`google_gtagjs-js-consent-mode-data-layer`）在
  `<head>` 前部，`gtag.js` 紧随其后，横幅标记随后；JS 侧 `wp_consent_type_defined` 与
  `wp_listen_for_consent_change` 的订阅都在这些之后注册。无合并、无延迟（线上同插件
  表，未装合并类插件）。
- 一条诚实的保留：16:5x 的一次线上 `/privacy-policy/` 抓取曾拿到 M2 文案之前的版本
  （「session, cart, and login cookies」），同一 URL 稍后的抓取（带与不带 cache-buster）
  都是 M2 之后的版本（「session, solution draft, and login cookies」），且此后重复抓取
  逐字节相同。差异不可复现，上述响应头里也没有任何缓存标记；记为**观察**，不作为结论，
  更不作为「线上有页面缓存」的说法。

## 实测 4：Site Kit 的 Google Tag Gateway 默认开还是关？

**默认关，且线上/本地都没有打开过。** `Google_Tag_Gateway_Settings::get_default()` =
`array( 'isEnabled' => false, 'isGTGHealthy' => null, 'isScriptAccessEnabled' => null )`，
选项名 `googlesitekit_google_tag_gateway`；本地实例的选项表里查不到它（从未写过）。因
此标签按标准 `//www.googletagmanager.com/gtag/js` 打印——就是实测 1 里被阻断器扣住的那
一条，不需要覆盖什么第一方 URL。票面「不开 Tag Gateway（除非实测其阻断覆盖）」据此保持：
`tools/cutover` 的 `consent` 段会把「它没被打开」也当作回归断言。

另一条同源实测：Site Kit 的 consent defaults 默认带 `region => Regions::get_regions()`
（欧洲区列表，`includes/Core/Consent_Mode/Consent_Mode.php`），列表外 Google 视为全部
granted。本机（不在列表内）用上游默认值实测过：点任何东西之前 `_ga` 已写、`page_view`
已发（这正是仓库插件里 `deny_everywhere` 的理由，见 `Consent\Blocking` 的注释）。站点对
每个访客都显示横幅（免费版没有按地理位置切换法域的开关——`regions` 是单值 radio，
`other_region_behaviour` 只在 premium 的 `use_country` 下生效），所以 defaults 也必须对
每个访客 deny。

## 实测 5：Complianz 免费版能否经 Polylang 为 EN / DE 各存一套横幅文案？

**能。** 机制：Complianz 的横幅字段在保存时经 `icl_register_string` 与
`wpml_register_single_string` 注册（`cookiebanner/class-cookiebanner.php` 的
`register_translation()`），读出时经 `apply_filters( 'wpml_translate_single_string', … )`
（同文件 `get_banner_html` 路径与 `functions.php`）；Polylang 提供这两个接口
（`src/modules/wpml/wpml-legacy-api.php`、`wpml-api.php`）并把译文存进语言 term 的
`_pll_strings_translations`（`src/mo.php`）。因此 DE 横幅 = Polylang 的字符串译文，不需要
第二个横幅行、不需要复制插件。

留证：`docs/acceptance/2026-10-16/201-consent/shots/banner-{en,de}-{1440,390}-{first,purposes}.png`
——同一套横幅、同一套设置，`/` 出英文（`Your cookie choice` / `Accept all` / `Reject all` /
`Choose purposes`），`/de/` 出德文（`Ihre Cookie-Auswahl` / `Alle akzeptieren` /
`Alle ablehnen` / `Zwecke auswählen`），分类标题与三条目的说明同样各一套；底部的
`Privacy Policy`/`Imprint` 链接在 DE 页是 `Datenschutzerklärung`/`Impressum`（横幅的文档
链接走 Polylang 的页面映射）。迁移把英文写入横幅行、把德文写进 Polylang
（`tools/migrate/201-consent.py` 的第 3 步），幂等且可读回。

## 附：三件事为什么不写代码

- **订单来源的「同意前不写」**：WooCommerce 11.2 自带 WP Consent API 集成，`marketing`
  类即它的 `$consent_category`；拒绝时它自己删 `sbjs_*`（`assets/js/frontend/order-attribution.js`
  的 `removeTrackingCookies()`，由 `wp-consent-api-integration.js` 在同意变更时调用）。零代码。
- **「营销」不给 Google 任何权限**：`googlesitekit_consent_category_map` 一个 filter 把
  `marketing` 置空（`Consent\Blocking::statistics_only`）。
- **撤回容易**：Complianz 的 JS 用事件委托监听 `button.cmplz-manage-consent`
  （`cmplz_add_event( 'click', 'button.cmplz-manage-consent', … )`，处理器把横幅状态置回
  `show`）；站点自己的页脚入口（LC partial）带上这个类名即完整的一条撤回路径，实测
  （`m1-accept-blocking.json` 的 `revokeOpened.bannerVisible = true`）：点页脚
  「Cookie settings」→ 横幅重开 → 点「拒绝全部」→ `_ga` 与 `sbjs_*` 即刻清空、此后零
  Google 请求（`after-revoke` 与 `after-revoke-reload` 两个阶段的请求日志都是空的，
  脚本 `type` 回到 `text/plain`）。

## 来源

- Complianz 7.5.6 源码（本地实例 `wp-content/plugins/complianz-gdpr/`）：`class-cookie-blocker.php`、
  `integrations/plugins/google-site-kit.php`、`cookiebanner/class-cookiebanner.php`、
  `cookiebanner/js/complianz.js`、`cookiebanner/class-banner-loader.php`、
  `settings/config/fields/wizard/general.php`、`settings/config/fields/general-settings/settings.php`。
- Site Kit 1.189.0：`includes/Core/Consent_Mode/Consent_Mode.php`、
  `includes/Core/Tags/Google_Tag_Gateway/Google_Tag_Gateway_Settings.php`、
  `includes/Core/Tags/Guards/Tag_Environment_Type_Guard.php`。
- WP Consent API 2.1.0：`assets/js/wp-consent-api.js`（`wp_listen_for_consent_change`、
  `wp_has_consent`、`wp_consent_type`）、`inc/`。
- WooCommerce 11.2.0：`src/Internal/Integrations/WPConsentAPI.php`、
  `src/Internal/Orders/OrderAttributionController.php`、
  `assets/js/frontend/order-attribution.js`、`assets/js/frontend/wp-consent-api-integration.js`。
- Polylang 3.8.10：`src/modules/wpml/wpml-api.php`、`src/modules/wpml/wpml-legacy-api.php`、
  `src/mo.php`。
- 线上只读实测（2026-10-16）：`wp plugin list`、`wp option get googlesitekit_*`、
  `/privacy-policy/` 的响应头与重复抓取。
- 探针与原始记录：`docs/acceptance/2026-10-16/201-consent/evidence/`。
