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
- 线上已官方安装CookieYes3.5.7与WP Consent API2.1.0，目前未启用；后续发布和现场读回追加在下方。

## 当前待完成

最终像素记录、Spec/Standards复核、PR/CI、生产启用、GA4实时访问、撤回实测完成后才关票。
