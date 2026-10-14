# #145 Search Console 接入（Site Kit by Google）

## 是什么
`https://de-linker.com/` 在 Google Search Console 里是一个**已验证**的网址前缀资源，站点地图 `https://de-linker.com/sitemaps.xml`（`robots.txt` 声明的那份，SEOPress 输出）已提交。营销侧的数据回流（收录、展示、点击，经服务账号读 Search Console API）全部来自这个资源。

**这是数据回流的前提，不得移除。** Search Console 会定期复查验证；验证不在了，该所有者在宽限期后失效，最后一个验证所有者失效时委托所有者与用户一起失去这个资源。

## 载体
Google 官方插件 **Site Kit by Google**（wordpress.org `google-site-kit`，免费），用 WP-CLI 从 wordpress.org 原生安装（与 Polylang 同一做法）。所有者账号在本站后台 Site Kit 里「用 Google 登录」：Site Kit 自动建网址前缀资源、自动验证并连接 Search Console。**只连 Search Console，不连 Analytics**（连了就会无条件加载 `gtag.js`；GA4 与同意横幅由后续票一起接）。本仓库不为验证写任何代码。

- 前台影响（本地参照实例实测，未连接状态）：每页 `<head>` 多两行——`<meta name="generator" content="Site Kit by Google …">` 与 `<link rel='dns-prefetch' href='//www.googletagmanager.com'>`；不加载脚本、不写 Cookie；首页 EN/DE × 1440/390 像素差 0。
- 验证状态存在数据库里（Site Kit 的 `googlesitekit_*` 选项与连接它的那个后台用户的用户选项）。**不要删除连接 Site Kit 的那个后台用户，不要在 Site Kit 里重置或断开**——那会撤掉验证。
- 选型理由与证据：`docs/research/2026-10-14/search-console-carrier.md`。

## 防冲掉
部署不会删除仓库之外的插件；会把验证拿掉的是回滚到旧备份、手工清理插件或重置 Site Kit——这些情况下每页仍是 200。两道检查：

| 检查 | 在哪 | 断什么 |
|---|---|---|
| `just cutover verify` 的 `search-console` 段（`steps.search_console`） | 线上（默认目标） | Site Kit 启用；`googlesitekit_search-console_settings.propertyID` = `https://de-linker.com/`；连接者（`ownerID`）的用户选项 `<前缀>googlesitekit_site_verification_file` 有令牌；`/google<令牌>.html` **不带** cache-buster 返回 200 且含令牌（Site Kit 只认精确路径，带查询串即 404；Google 也按精确路径取）。任一不成立 → 退出码 1 |
| `tests/e2e/specs/chrome.spec.ts`「Site Kit by Google is still active」 | 评审站 / 本地实例 | 首页有 Site Kit 的 generator 标记（本地实例连不上 Google，只断插件在） |

2026-10-14 线上状态：Site Kit 1.189.0，连接者 = 后台用户 1（唯一管理员），验证方式 = 虚拟 HTML 文件。

## 所有者侧（角色名；真实账号只在营销侧私有 vault）
所有者账号：在后台 Site Kit 里完成设置（不勾 Analytics、不勾匿名使用数据）→ 在 Search Console 把日常账号加为**所有者**（委托所有者）→ 在「站点地图」提交 `sitemaps.xml`。

## 变更记录
- 2026-10-14（#145）：首版。载体最初按「仓库 mu 插件输出验证标记」实现，业主改裁定为官方 Site Kit、验证不写代码，mu 插件方案撤回未合并。
