# CookieYes：当前方案

2026-10-19 用户改定：CookieYes 官方免费版3.5.7（WordPress.org slug cookie-law-info）替代 Complianz。以下 Complianz 调查仅为被替代方案的历史证据，不再用于最终配置。

来源经 Apify 实取（2026-10-19）：[官方插件说明](https://wordpress.org/plugins/cookie-law-info/)与[官方 Consent Mode 指南](https://www.cookieyes.com/documentation/implementing-google-consent-mode-using-cookieyes/)。最终采用 standalone WordPress 存储，不建 SaaS 账号。

当前官方包原生能力：lite/includes/class-i18n-helpers.php 读取 Polylang 当前语言；Banner/Settings 原生类保存双语配置；frontend/js/wca.js 将 analytics 映射 statistics，advertisement 映射 marketing。前台 Script blocker 处理 provider 与 data-cookieyes 标签；静态 Site Kit 脚本先以 text/plain 输出，避免解析器先请求再被 MutationObserver 移走。

首次无选择的 CookieYes Site Kit 分支会提前 return，尚未定义 opt-in。WP Consent API 没有 consent type 时会允许 Woo 的来源追踪，因此服务端通过 wp_get_consent_type 明确 optin。来源脚本不再由 provider 阻断，由 Woo 原生 WP Consent API 接线控制初始化和撤回。

## 被替代的 Complianz 调查

# 本次接入依据复核

2026-10-19 由 Apify Website Content Crawler 重新抓取三份一手资料，未沿用旧 PR 的完成结论。

- [Google：Consent mode overview](https://developers.google.com/tag-platform/security/concepts/consent-mode)：Basic 在选择前阻止 Google 标签加载，拒绝后不发测量数据；Advanced 在拒绝状态仍可发无 Cookie ping。本票按 Basic 验证网络，不能仅凭 `_ga` 不存在判通过。
- [Site Kit：Consent mode](https://sitekit.withgoogle.com/documentation/using-site-kit/consent-mode/)：同意 UI 由 CMP 承接，WP Consent API 沟通类别，Site Kit 更新 Google 信号；同时启用 CMP 自己的 Consent Mode 可能冲突。官方点名 Complianz 原生集成。
- [TDDDG §25](https://www.gesetze-im-internet.de/ttdsg/__25.html)：终端存储/访问通常须先知情同意，传输必要或用户明确请求服务绝对必要的情形有例外。统计与可选询盘来源不作为必需 Cookie。

## 本机原生实现核对

从 wordpress.org 官方包重新安装的 Complianz 7.5.6 仍在 `integrations/plugins/google-site-kit.php` 的 `cmplz_whitelisted_script_tags` 中豁免 `google_gtagjs-js` 与 `google_gtagjs-js-after`；`class-cookie-blocker.php` 在阻断匹配前检查白名单。只填 Script Center 不能消除该豁免，须将这两个测量脚本移出白名单；保留 Site Kit consent defaults 与本地 consent-mode JS。

Site Kit 1.189.0 的 `Core/Consent_Mode/Consent_Mode.php` 默认值包含地区列表；同一 opt-in 合同适用于所有访问者，过滤器移除地区限制。其原生类别映射会把 marketing 映射到三种 Google 广告信号；本站的 marketing 类只承接 Woo 原生归因，故移除该广告映射。

WooCommerce 11.2.0 的 `src/Internal/Integrations/WPConsentAPI.php` 原生使用 marketing 类，前端 `wp-consent-api-integration.js` 在同意变化时调用 `setOrderTracking`。保留原生接线，由浏览器夹具核实同意前不写、同意后记录、撤回清理。

Complianz 的 `cmplz_set_consent` 只对 marketing 从 allow 到 deny 安排重载；统计单独撤回不能依赖这一支。Google 标签一旦执行，删 Cookie 不能撤掉其事件处理器；本票在 WP Consent API 的捕获阶段先设 Google 原生 `ga-disable-<measurementID>`，清分析 Cookie，再重载到拒绝状态。统计单独撤回有独立网络回归。

上述源码是原因定位，完成与否以本次浏览器网络、Cookie、视觉及线上 GA4 实时证据为准。
