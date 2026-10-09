# #5 本地栈 `just up`

## 目标
在这台 Mac 上一条命令建出与线上同版本的 WordPress 实例，供每张票独立开发与验收；不依赖 Docker；不触碰线上。

## 组成
- `tools/local/`（Python 包，uv 管理，命令入口 `linker-local`）：
  - `instances.toml`：实例名 → 端口、数据库名、数据目录（`~/de-linker-local/<name>/`）。
  - `up <name>`：若不存在则创建：建数据库（Homebrew MySQL，用户 `linker_local`）、下载 WordPress 7.1.3（校验 sha）、安装（站名 "Linker (local <name>)"、管理员 `local-admin`、随机密码写入实例目录 `admin.txt`，权限 600）、安装 WooCommerce 11.1.0、从 #6 的快照装入许可插件（LiveCanvas、SEOPress、SEOPress PRO、WindPress）与 `wp-content/uploads`、符号链接 `plugins/linker-*` 到仓库、装入隔离 mu-plugin、写入 `.htaccess`/固定链接、启动 `php -S 127.0.0.1:<port>`（php@8.3，`php.ini` 按线上实测设 `memory_limit=2048M`、`max_execution_time=0`、`upload_max_filesize=2048M`（来源：2026-10-09 经 SSH 读取线上 lsphp 8.3 配置），并启用本地 Redis 对象缓存（brew redis），与线上切换后的配置一致）。
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

## 变更记录
- 2026-10-09（#5）：`instances.toml` 放在数据根 `~/de-linker-local/`，不在仓库：每张票一个工作树，它们共用一台 MySQL 与同一组端口，只有按机器的登记表能保证端口不冲突。每个实例登记三个端口（WordPress、engine、Genie），从 8888（wp-env 的默认端口）起向上取空闲端口；库名与目录由名字推出。
- 2026-10-09（#5）：`php.ini` 取线上实测值：`memory_limit`、`post_max_size`、`upload_max_filesize` 2048M，`max_execution_time`、`max_input_time` 360，`max_input_vars` 5000（主机 `~/.cl.selector/alt_php83.cfg`，SSH 只读）。原写的 512M/64M 没有来源。
- 2026-10-09（#5）：`pre_http_request` 只放行 127.0.0.1，删去 PVGIS 开关：PVGIS 由 `services/engine` 调用（#14 规格"引擎"节），不经过 WordPress 的 HTTP API，WordPress 侧没有调用方。
- 2026-10-09（#5）：不写 `.htaccess`：`php -S` 不读它，`tools/local/router.php` 做同样的改写；mu-plugin 让 `got_url_rewrite()` 为真，否则后台固定链接页给每种结构加 `/index.php`。
- 2026-10-09（#5）：WordPress 默认发件人 `wordpress@127.0.0.1` 被 PHPMailer 拒绝（本地每封核心邮件都会失败），隔离 mu-plugin 把它改为 `wordpress@example.test`。
- 2026-10-09（#5）：一次性登录：mu-plugin 的 `linker_local_login_url()` 生成 token（只存 SHA-256），`linker-local login` 经 `wp eval` 调用；10 分钟与一次性按 NIST SP 800-63B-4 "Out-of-Band Verifiers"。
- 2026-10-09（#5）：#6 的快照尚不存在，`up` 先做 WordPress 7.1.3 + WooCommerce 11.1.0 的干净安装；`--snapshot <dir>` 装入快照的 `plugins/<slug>/` 与 `uploads/`（数据库归 #6）。干净安装上 `/de/`、`/products/`、`/proforma-request/` 不存在（404），它们来自 #6 的数据与 #9 的语言层。
