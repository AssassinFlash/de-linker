# #145 Search Console 接入（Site Kit）：验收记录 2026-10-14

规格 `docs/specs/145-search-console.md`。真实账号不写本仓库（角色名：所有者账号、日常账号）。

## 本地（参照实例 t110，main 检出）
- 装 Site Kit 1.189.0（wordpress.org zip，sha256 `bd7d25d2e6d308cf76019a77c0a4caf17e3db073691c56662c76bfa5ffe45e85`）。
- 前台 HTML 对照（插件停用 vs 启用；`/`、`/de/`、`/products/`、EN/DE 产品页、`/my-account/`）：每页只多 `<meta name="generator" content="Site Kit by Google 1.189.0" />` 与 `<link rel='dns-prefetch' href='//www.googletagmanager.com' />`；无脚本、无 Cookie。
- 像素：首页 EN/DE × 1440/390 全页截图（Playwright Chromium，禁动画、等字体），基线两次自比 0 差，装 Site Kit 后对基线 **0 差像素**（4/4）。存档为启用后的截图 `home-*-sitekit.jpg`（压缩存档；比对在 PNG 上做）。
- 回归：`just e2e t110 specs/chrome.spec.ts` 6/6 通过；停用 Site Kit 后新断言变红，重新启用恢复。

## 线上
1. **备份**（读）：插件列表与 `googlesitekit*` 选项（空）→ `~/de-linker-data/t145-sitekit/before.json`。
2. **安装**：`wp plugin install google-site-kit --version=1.189.0 --activate`；读回 `google-site-kit active 1.189.0`；首页 200，generator 标记在。日志 `~/de-linker-data/t145-sitekit/install.log`。
3. **设置**（所有者账号在后台用户 1 的会话里完成，agent 经浏览器逐步点）：欢迎页 Analytics 与匿名使用数据两个勾都未勾 → 用 Google 登录（OAuth 范围只有 profile/email、siteverification、webmasters）→ Verify ownership → Allow metrics → Set up Search Console → 目标选「Sell products」（只决定仪表盘卡片，可在设置里改）→ Complete setup。未点「Set up Analytics」。
4. **读回**：`googlesitekit_search-console_settings` = `{"propertyID":"https://de-linker.com/","ownerID":1}`；用户 1 有 `wp_googlesitekit_site_verification_file` 与 `wp_googlesitekit_site_verified_meta = verified`；`/google<令牌>.html` 返回 200 + 令牌（带查询串 404，Site Kit 只认精确路径）。
5. **GSC**：资源 `https://de-linker.com/`，所有者账号 = Owner · Verified；日常账号加为 Owner（委托所有者）；未用验证令牌 0（截图含真实账号，存营销侧私有 vault，不入本仓库）。站点地图 `sitemaps.xml` 提交：首屏显示 Couldn't fetch，几分钟后刷新为 **Success**、类型 Sitemap index（`gsc-sitemaps-success.jpg`）。同时以 Googlebot UA 复核：索引与 4 个子站点地图全部 200、XML 合法，共 301 个 URL（德语 151）。
6. **回归对线上**：`just cutover verify` 退出码 0（`verify-live.log`）：既有子集全过 + `search-console` 段三项全过。

## 未解问题
无。
