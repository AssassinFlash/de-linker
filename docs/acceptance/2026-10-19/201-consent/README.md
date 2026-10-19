# GA4 与 CookieYes · 本次验收记录

从 main `f59cd9b5`、独立分支 `codex/201-ga4-consent-20261019`、实例 `c201_20261019`（9156）开始。装入20261019-1409完整线上快照，旧撤案PR不作为证据。

## 已核实

- 线上起点：Site Kit1.189.0已激活，Search Console保持；Analytics各ID为空，没有CMP。
- 用户改定CookieYes，取代原Complianz；本地停用Complianz。官方CookieYes3.5.7 + WP Consent API2.1.0，独立WordPress存储，不连接CookieYes云端。
- Google所有者亲自接受德国条款后创建专属账号、媒体资源、Web数据流，14个月事件保留，Google Signals关闭、广告个性化0/307。用户明确两位共同管理身份均管理员。真实ID及截图仅在私有vault的ga4-owner-checklist.md。
- 原生CookieYes双语存储、Polylang语言选择、WP Consent API类别、原生阻断与偏好面板；窄接线补服务端opt-in默认、解析器惰性Google脚本、始终拒绝Ads、撤回已执行标签和德语ARIA标签。Woo仍使用原生归因。
- 9项实际浏览器测试通过：EN/DE×1440/390首次与拒绝；仅分析、仅访问来源、双同意；仅分析与双目的撤回后下一页。Google实际库运行，测量传输截获到204，不向生产属性写本地夹具。
- Cookie实测：GA400天、CookieYes365天、Woo来源为会话、sbjs_session30分钟，见cookieyes/browser-evidence.json。
- 全仓 `just test` 退出0，包含cutover155、pull113项。针对性PHPUnit6项14断言通过。PHPStan level8通过；最终全仓静态检查与CI随PR记录。
- Computer Use已实走EN/DE×1440/390横幅与目的面板。默认外观被操作者否决，改为站点字体与圆角、桌面留边底部横幅、手机接受拒绝并排。最终德语454字符、英语433字符。文案和样式已获“可以了，英德两版一起上线”批准，见copy-review.md。默认旧截图只保留为迭代证据。
- 生产备份39820文件、完整目录验证、可解压数据库、SHA256 manifest均在仓外。标准分块复制因SSH逐文件延时较慢，改以原生可重试大块完成剩余plugins/mu-plugins，再重新读取数据库和options并验证完整树；不改变备份工具或全局配置。
- 线上已官方安装CookieYes3.5.7与WP Consent API2.1.0。生产启用与读回见下方最终状态，不在本节重复成未完成。

## 2026-10-19 样式例外（业主裁定）

CookieYes 横幅是插件自己的界面。横幅、按钮和标题的颜色留在 CookieYes 原生设置（`tools/migrate/201-consent.php`），不迁到 WindPress，也不改这些颜色。AGENTS.md §5 的站点样式规则约束站点页面，不约束这个第三方 CMP 的原生设置。WindPress `content/windpress/consent.css` 继续只管已批准的字体、圆角和页脚入口。

## 最终状态

生产门的记录在 [PR #358 的生产验收说明](https://github.com/AssassinFlash/de-linker/pull/358#issuecomment-6263281263)，不在本目录的原始网络日志里。该说明写明的、本仓库能对上的事实：

- PR #358 已合并为 `21020e094ac5011d63363e91691aa6eb68b174d0`。说明称合并前两个 CI 检查通过。本轮没有重跑那次 CI。
- 生产批次 `20261019T082705433994Z-21020e09` 已通过原生 `resume-deploy` 并归档备份，维护模式关闭。本轮没有再写生产。
- 说明称七个真实浏览器用例通过（无测量拦截、无 CSP 绕过），含首次访问/拒绝、独立目的和撤回。GA4 Realtime 显示一名活跃用户、首页浏览，以及 `page_view`、`session_start`、`first_visit`、`scroll`。原始请求、Cookie 和账号读回只在私有 vault：`marketing/00-system/ga4-owner-checklist.md`、`marketing/00-system/evidence/2026-10-19-ga4/`。
- 本地 before/after 在法律栏之外为 0 像素，见 [pixel-comparison.json](pixel-comparison.json) 的 `outside_legal_bar_pixels`。
- 同一说明写 EN1440、DE1440、DE390 的生产/本地全页一致，EN390 页脚英语语言胶囊有 90×34 的差异。仓库里的 `live/` 与 `after/` 全页 PNG 在 2026-10-19 复测对不上这个结果：四张图尺寸相同，精确 RGB 不同像素为 EN1440 79076、EN390 41207、DE1440 16612、DE390 45502，包围盒见 `live_vs_local_bbox`。差异落在页脚一带，并包含未加载成白块的图片。这里记文件本身的计数，不把说明里的“一致”写成这四张图的测量结果。
