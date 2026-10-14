# Search Console 验证载体的选择（#145）

规格：`docs/specs/145-search-console.md`。外部事实 2026-10-14 经 Apify `apify/rag-web-browser` 读取。

## 结论
Site Kit by Google（业主 2026-10-14 裁定：用官方插件，这类接入不写代码）。

## 依据
- Site Kit 设置时自动把站点加进 Search Console：站点还没有资源时「Site Kit creates a URL-prefix property and connects it to your site」；已有已验证的网址前缀资源时自动连接；Search Console 是必连模块，不能断开。验证时「Site Kit first tries to place a virtual HTML file upload method, and if that fails … it tries to verify site ownership with an HTML tag」。——https://sitekit.withgoogle.com/documentation/supported-services/search-console/
- 营销侧选型调研（GA4 + 同意横幅）推荐 Site Kit 作 GA4 载体，并建议与 Search Console 共用；Site Kit 只要连了 Analytics 就会无条件入队 `gtag.js`，所以本票只连 Search Console。
- 验证会被定期复查，令牌绑定到账号；所有验证所有者失效时，委托所有者与用户在宽限期后一起失去访问。——https://support.google.com/webmasters/answer/9008080 、https://support.google.com/webmasters/answer/7687615
- 版本：wordpress.org 插件 API 2026-10-14 读得 1.189.0（更新于 2026-10-05）。本地参照实例装 1.189.0（zip sha256 `bd7d25d2…45e85`）：未连接时前台只多 generator meta 与 `googletagmanager.com` 的 dns-prefetch，首页 EN/DE × 1440/390 像素差 0。

## 撤回的方案
仓库 must-use 插件输出 `google-site-verification` meta（令牌在仓库里，回归可直接核对）。本票最初按它实现；业主裁定这类接入用官方插件、不写代码，撤回未合并。

## 规格里不写、但做决定时用到的事实
- Polylang 同样由 WP-CLI 从 wordpress.org 原生安装（规格 17 §3 的理由：原生安装器核对包，检出里 rsync 的副本是不可核对的第二来源），Site Kit 照此。
- Site Kit 只要连了 Analytics 就无条件入队 `gtag.js`（营销侧选型调研读源码 `includes/Core/Tags/GTag.php`），所以同意横幅上线前不连。
- 部署（`just cutover deploy`）只写三个插件、mu 目录与主题文件，不删仓库外插件；会拿掉验证的是回滚旧备份、手工清理插件或重置 Site Kit，这些情况下每页仍是 200——所以检查读验证本身，不读状态码。
- Site Kit 的虚拟验证文件只认精确路径：2026-10-14 线上实测 `/google<令牌>.html` 200，加 `?cbq=…` 即 404。
