# #5 本地栈 `just up`

## 目标
在这台 Mac 上一条命令建出与线上同版本的 WordPress 实例，供每张票独立开发与验收；不依赖 Docker；不触碰线上。

## 组成
- `tools/local/`（Python 包，uv 管理，命令入口 `linker-local`）：
  - `~/de-linker-local/instances.toml`（数据根，全机一份）：实例名 → 三个端口（WordPress、engine、Genie）；数据库 `linker_<name>`、数据目录 `~/de-linker-local/<name>/` 由名字推出。
  - `up <name>`：若不存在则创建：建数据库（Homebrew MySQL，用户 `linker_local`）、下载 WordPress 7.1.4（校验 sha）、安装（站名 "Linker (local <name>)"、管理员 `local-admin`、随机密码写入实例目录 `admin.txt`，权限 600）、安装 WooCommerce 11.2.0（`wp plugin verify-checksums` 核对）、从 #6 的快照装入许可插件（LiveCanvas、SEOPress、SEOPress PRO、WindPress）、主题与 `wp-content/uploads`（`--snapshot <dir>`）、符号链接 `plugins/linker-*` 到仓库、装入隔离 mu-plugin、固定链接 `/%postname%/`（`router.php` 承担改写）、启动 `php -S 127.0.0.1:<port>`（php@8.3，`php.ini` 取线上的限额：`memory_limit`、`post_max_size`、`upload_max_filesize` 2048M，`max_execution_time`、`max_input_time` 360，`max_input_vars` 5000），并启用本地 Redis 对象缓存（brew redis + Redis Object Cache 插件，每个实例一个键前缀），与线上切换后的配置一致。
  - `down <name>`、`reset <name>`（删库删目录重建）、`login <name>`（生成一次性登录链接：WP-CLI `wp user session create` 不存在，用 `wp eval` 生成带 nonce 的临时自动登录 token，10 分钟过期，用后即删）、`status`。
  - `serve`：以 uv 启动 `services/engine`（端口按实例分配）与 `services/genie`，并用 `wp option update` 把地址写入实例。
- 隔离 mu-plugin（`tools/local/mu/000-linker-local-isolation.php`）：`wp_mail` 改为写入实例目录 `mail/*.eml`（本地邮件捕获）；`pre_http_request` 只放行 127.0.0.1（重定向同样只许 127.0.0.1），拦下的记入隔离日志；CSP 放行本机端口；把站点标为 noindex。
- `docs/local-stack.md`：安装前提（`brew install php@8.3 mysql redis wp-cli uv just composer`）、命令、目录、常见故障。

## 不做
不做多机复现；不做 Docker；不改线上。

## 验收
- [ ] `just up a && just up b` 并存；`just status` 列出两者；`just reset a` 可重复。
- [ ] 两实例的 `/`、`/de/`、`/products/`、`/proforma-request/` 均 200；`wp core version` = 7.1.4，`wp plugin get woocommerce --field=version` = 11.2.0。
- [ ] 提交一个本地表单后 `mail/` 里出现 `.eml`，线上没有任何请求（隔离日志里没有线上主机的行，每一行都是一次被拦下的请求）。
- [ ] Computer Use：本地与线上首页 EN/DE × 1440/390 对照截图入 `docs/acceptance/<date>/5/`。

## 变更记录
- 2026-10-09（#5）：`instances.toml` 放在数据根 `~/de-linker-local/`，不在仓库：每张票一个工作树，它们共用一台 MySQL 与同一组端口，只有按机器的登记表能保证端口不冲突。每个实例登记三个端口（WordPress、engine、Genie），从 8888（wp-env 的默认端口）起向上取空闲端口；库名与目录由名字推出。
- 2026-10-09（#5）：`php.ini` 取线上实测值：`memory_limit`、`post_max_size`、`upload_max_filesize` 2048M，`max_execution_time`、`max_input_time` 360，`max_input_vars` 5000（主机 `~/.cl.selector/alt_php83.cfg`，SSH 只读）。原写的 512M/64M 没有来源。
- 2026-10-09（#5）：`pre_http_request` 只放行 127.0.0.1，删去 PVGIS 开关：PVGIS 由 `services/engine` 调用（#14 规格"引擎"节），不经过 WordPress 的 HTTP API，WordPress 侧没有调用方。
- 2026-10-09（#5）：不写 `.htaccess`：`php -S` 不读它，`tools/local/router.php` 做同样的改写；mu-plugin 让 `got_url_rewrite()` 为真，否则后台固定链接页给每种结构加 `/index.php`。
- 2026-10-09（#5）：WordPress 默认发件人 `wordpress@127.0.0.1` 被 PHPMailer 拒绝（本地每封核心邮件都会失败），隔离 mu-plugin 把它改为 `wordpress@example.test`。
- 2026-10-09（#5）：一次性登录：mu-plugin 的 `linker_local_login_url()` 生成 token（只存 SHA-256），`linker-local login` 经 `wp eval` 调用；10 分钟与一次性按 NIST SP 800-63B-4 "Out-of-Band Verifiers"。
- 2026-10-09（#5）：#6 的快照尚不存在，`up` 先做 WordPress 7.1.3 + WooCommerce 11.1.0 的干净安装；`--snapshot <dir>` 装入快照的 `plugins/<slug>/` 与 `uploads/`（数据库归 #6）。干净安装上 `/de/`、`/products/`、`/proforma-request/` 不存在（404），它们来自 #6 的数据与 #9 的语言层。
- 2026-10-09（#5，评审后）："隔离日志为空"改为可量的说法：建好的实例日志里就有 WordPress 自己的更新检查（api.wordpress.org，http 与 https 各一次），都已被拦下；量度是"日志里没有线上主机 `de-linker.com` 的行、每一行都是一次被拦下的请求"。Requests 自己跟随重定向，`pre_http_request` 只看第一个 URL，所以隔离也拦从 127.0.0.1 重定向到别处的请求（`requests-requests.before_redirect`）。
- 2026-10-09（#5，评审后）：快照接口另装 `themes/<slug>/`（只复制，启用哪个由数据库定）：线上主题 `picostrap5` / `picostrap5-child-base` 不在规格 6 的四个许可插件里，没有它们，装入线上数据库后的本地首页也对不上线上（规格 6 的变更记录同步）。
- 2026-10-09（#5，第二轮评审）：WooCommerce 改钉 11.2.0。线上会自动更新插件，WooCommerce 在 2026-10-09 07:54 UTC 从 11.1.0 升到 11.2.0（线上插件头与 `woocommerce_db_version`，SSH 只读）；11.1.0 是更新前测的（framework-choice.md §2）。WordPress 仍是 7.1.3（线上设了 `WP_AUTO_UPDATE_CORE = 'minor'`）。插件与 `tools/local` 的 `php-stubs/woocommerce-stubs` 同步改为 `~11.2.0`。线上再自动更新时，改 `tools/local/src/linker_local/wordpress.py` 的版本与地址。
- 2026-10-09（#5，第三轮评审，接 #35）：本地 Redis 对象缓存：Homebrew `redis` + wordpress.org 的 Redis Object Cache 3.0.0（`verify-checksums` 核对），每实例 `WP_REDIS_PREFIX = linker_<name>:` 与 `WP_REDIS_SELECTIVE_FLUSH`，建实例时 `wp redis enable` 后清本前缀，reset 后读不到旧库留下的键。`max_execution_time` 保留 360，不取 #35 写的 0：线上网页请求的值是 360（WooCommerce 系统状态 `php_max_execution_time`，2026-10-09 REST 只读；`~/.cl.selector/alt_php83.cfg` 同为 360）；0 是命令行里的值，PHP 的 CLI 把它固定为 0，本地 WP-CLI 也是 0。WooCommerce 11.2.0 的来源另记：2026-10-09 线上 `wp plugin get woocommerce --field=version`（#7 执行会话）。
- 2026-10-09（#5，第四轮评审）：Redis Object Cache 的 `wp redis enable`（以及 `disable`、`update-dropin`、后台按钮、停用插件）执行 FLUSHDB，清空共用的第 0 号库、连带别的实例；所以建实例时先只删本前缀的键，再自己复制插件的 `object-cache.php`，不用这些命令。端口登记：任何数据根（包括测试的）分配端口时都避开 `~/de-linker-local/instances.toml` 里登记的端口，并共用同一把机器锁。
- 2026-10-12（#103）：wp-config 增 `WP_REDIS_GRACEFUL=true`（`tools/local/src/linker_local/objectcache.py` 的常量表）。Redis Object Cache 没有这个常量时 `fail_gracefully` 为关，第一次失败的缓存读就 `show_error_and_die`——评审站实例的 PHP 错误日志里那批 `Predis\Connection\ConnectionException` 与失败 Genie 轮次一一对应，就是这条死法。常量打开后 drop-in 记日志、本次请求改走请求内缓存，读失败降级为缓存未命中；`just login` 依赖 Redis 存 token 的既有口径不变（Redis 全停时一次性登录链接仍不可用）。线上切换的主机卫生带同一常量（规格 17）。
- 2026-10-29：线上只读快照已是 WordPress 7.1.4；本地下载、状态断言与当前文档同步更新。
