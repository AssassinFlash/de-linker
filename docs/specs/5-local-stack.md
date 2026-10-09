# #5 本地栈 `just up`

## 目标
在这台 Mac 上一条命令建出与线上同版本的 WordPress 实例，供每张票独立开发与验收；不依赖 Docker；不触碰线上。

## 组成
- `tools/local/`（Python 包，uv 管理，命令入口 `linker-local`）：
  - `instances.toml`：实例名 → 端口、数据库名、数据目录（`~/de-linker-local/<name>/`）。
  - `up <name>`：若不存在则创建：建数据库（Homebrew MySQL，用户 `linker_local`）、下载 WordPress 7.1.3（校验 sha）、安装（站名 "Linker (local <name>)"、管理员 `local-admin`、随机密码写入实例目录 `admin.txt`，权限 600）、安装 WooCommerce 11.1.0、从 #6 的快照装入许可插件（LiveCanvas、SEOPress、SEOPress PRO、WindPress）与 `wp-content/uploads`、符号链接 `plugins/linker-*` 到仓库、装入隔离 mu-plugin、写入 `.htaccess`/固定链接、启动 `php -S 127.0.0.1:<port>`（php@8.3，`php.ini` 固定 `memory_limit=512M`、`upload_max_filesize=64M`）。
  - `down <name>`、`reset <name>`（删库删目录重建）、`login <name>`（生成一次性登录链接：WP-CLI `wp user session create` 不存在，用 `wp eval` 生成带 nonce 的临时自动登录 token，10 分钟过期，用后即删）、`status`。
  - `serve`：以 uv 启动 `services/engine`（端口按实例分配）与 `services/genie`，并用 `wp option update` 把地址写入实例。
- 隔离 mu-plugin（`tools/local/mu/000-linker-local-isolation.php`）：`wp_mail` 改为写入实例目录 `mail/*.eml`（本地邮件捕获）；`pre_http_request` 只放行 127.0.0.1 与 PVGIS（可开关）；CSP 放行本机端口；把站点标为 noindex。
- `docs/local-stack.md`：安装前提（`brew install php@8.3 mysql`）、命令、目录、常见故障。

## 不做
不做多机复现；不做 Docker；不改线上。

## 验收
- [ ] `just up a && just up b` 并存；`just status` 列出两者；`just reset a` 可重复。
- [ ] 两实例的 `/`、`/de/`、`/products/`、`/proforma-request/` 均 200；`wp core version` = 7.1.3，`wp plugin get woocommerce --field=version` = 11.1.0。
- [ ] 提交一个本地表单后 `mail/` 里出现 `.eml`，线上没有任何请求（隔离日志为空）。
- [ ] Computer Use：本地与线上首页 EN/DE × 1440/390 对照截图入 `docs/acceptance/<date>/5/`。
