# #145 Search Console 接入（Site Kit by Google）

## 是什么
`https://de-linker.com/` 是 Google Search Console 中已验证的网址前缀资源，站点地图 `https://de-linker.com/sitemaps.xml`（`robots.txt` 声明、SEOPress 输出）已提交。营销侧的数据回流（收录、展示、点击，经服务账号读 Search Console API）全部来自这个资源。**这是数据回流的前提，不得移除。**

## 载体
Site Kit by Google（wordpress.org `google-site-kit`），WP-CLI 从 wordpress.org 安装。所有者账号在后台 Site Kit 里用 Google 登录，Site Kit 建资源、验证（虚拟 HTML 文件 `/google<令牌>.html`）并连接 Search Console。**只连 Search Console，不连 Analytics、不开匿名使用数据**；GA4 由同意横幅票接入。本仓库不为验证写代码。

- 前台：每页 `<head>` 多 Site Kit 的 generator meta 与 `//www.googletagmanager.com` 的 dns-prefetch；无脚本、无 Cookie、无像素变化。
- 状态在数据库：`googlesitekit_search-console_settings`（`propertyID`、`ownerID` = 连接者的后台用户）与连接者的用户选项 `<表前缀>googlesitekit_site_verification_file`。**不得删除连接者那个后台用户，不得在 Site Kit 里 Reset / Disconnect。**
- 选型理由与证据：`docs/research/2026-10-14/search-console-carrier.md`。

## 检查
| 检查 | 谁跑、何时 | 断什么 |
|---|---|---|
| `just cutover verify` 的 `search-console` 段（`steps.search_console`） | 每次写线上之后（部署、回滚、插件变动），对生产主机；`--target local:…` 不跑这一段 | Site Kit 启用；`propertyID` = `https://de-linker.com/` 且有 `ownerID`；连接者有验证文件令牌；`/google<令牌>.html` 不带 cache-buster 返回 200 且含令牌。任一不成立退出码 1 |
| `tests/e2e/specs/search-console.spec.ts` | 评审站回归（`just e2e <实例>`） | 首页有 Site Kit 的 generator 标记。评审站须按 `tests/e2e/README.md` 从 2026-10-14 之后的线上快照以 `--live-code` 装入，Site Kit 才在 |

## 所有者侧（角色名；真实账号只在营销侧私有 vault）
所有者账号完成 Site Kit 设置 → 在 Search Console 把日常账号加为所有者（委托所有者）→ 提交 `sitemaps.xml`。

## 变更记录
- 2026-10-14（#145）：首版。
