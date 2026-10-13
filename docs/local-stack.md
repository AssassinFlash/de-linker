# 本地栈

`just up <name>` 在这台 Mac 上建出一个独立的 WordPress 实例：Homebrew 的 PHP 8.3、MySQL 与 Redis（对象缓存），WP-CLI，WordPress 7.1.3 + WooCommerce 11.2.0（线上版本）+ Polylang 3.8.10（linker-i18n 在插件头声明的前置，装好即启用）+ LiveCanvas 4.9.5（#12 的修复版，从本机归档 `~/de-linker-data/livecanvas-4.9.5/` 安装，wordpress.org 上没有）+ `de_DE_formal` 的 WordPress 与 WooCommerce 语言包，我们的三个插件以符号链接挂入当前检出。不用 Docker，不连线上。代码在 `tools/local/`（uv 项目 `linker-local`），规格是 `docs/specs/5-local-stack.md`。

## 前提（一次性）

```sh
brew install php@8.3 mysql redis wp-cli uv just composer
brew pin wp-cli          # WP-CLI 留在 2.12（线上的版本）；Homebrew 没有旧版本可装回
brew services start mysql
brew services start redis
```

- `mysql -u root` 经本机 socket 免密码登录（Homebrew MySQL 的默认）；`linker-local` 用它建库、建用户 `linker_local`。
- `php@8.3` 不替换默认的 `php`，justfile 把 `/opt/homebrew/opt/php@8.3/bin/php` 交给 `linker-local`（环境变量 `PHP`），实例的服务器与 WP-CLI 都在 8.3 上跑。`linker-local` 每次运行先确认 PHP 是 8.3、`wp` 是 WP-CLI 2.12（线上的版本；`brew upgrade` 换了版本就会报错）。
- 第一次 `up` 要联网：下载 WordPress、WooCommerce 与 Redis Object Cache（之后用缓存）；两个插件每次安装都要向 wordpress.org 核对校验和。

## 命令

| 命令 | 作用 |
|---|---|
| `just up <name>` | 实例不存在就建；存在就把 php.ini、路由、mu-plugin 与插件链接更新到当前检出，再（重）启服务器。2026-10-09 在本机实测：新建一个 11–43 秒（机器空闲时 11 秒；其他窗口把 load average 压到 36–40 时 43 秒；首次下载另计），已有实例约 6 秒 |
| `just up <name> --snapshot <dir>` | 同上，并装入快照目录里的插件、主题与 uploads（见"快照"） |
| `just down <name>` | 停服务器与服务，数据保留 |
| `just reset <name>` | 删库、删目录、清掉本实例的 Redis 键、重建（端口不变），可反复执行；2026-10-09 实测 11–43 秒（同上，随机器负载） |
| `just login <name> [--user <login>]` | 打印一次性登录链接：10 分钟内有效，用一次即作废；默认用户 `local-admin` |
| `just status` | 列出实例：地址、库、服务器与服务是否在跑、WordPress/WooCommerce 版本、链接到哪个检出 |
| `just serve <name>` | 用 uv 启动 `services/engine` 与 `services/genie`，地址写进实例。engine 需要的两份数据由它备好：检出里的 `plugins/linker-commerce/data/compatibility.json`，以及站点自己服务的工程 feed（`linker/v1/engineering-feed`，取回写进实例的 `engine/feed.json`）——站点答不上来就报错，不留一个没有数据的 engine |
| `just wp <name> <args…>` | 对实例运行 WP-CLI，例如 `just wp a plugin list` |

名字只能用小写字母、数字与 `_`，字母开头（它同时是库名、目录名）。每条工作线（每张票）用自己的实例，例如 `just up t7`。

## 一个实例有什么

| 项 | 值 |
|---|---|
| 地址 | `http://127.0.0.1:<port>`，后台 `/wp-admin/`，用户 `local-admin`，口令在 `admin.txt` |
| 端口 | 每个实例三个：WordPress、engine、Genie；从 8888（wp-env 的默认端口）起向上取空闲端口 |
| 数据库 | `linker_<name>`，用户 `linker_local`（口令在 `~/de-linker-local/linker_local.my.cnf`，600） |
| 对象缓存 | Homebrew 的 Redis（`127.0.0.1:6379`，各实例共用第 0 号库）+ Redis Object Cache 3.0.0；键前缀 `linker_<name>:`，`wp cache flush` 只清本实例的键；`WP_REDIS_GRACEFUL=true`——Redis 抖动时缓存读降级为请求内缓存（记日志），不杀请求 |
| 目录 | `~/de-linker-local/<name>/` |

```text
~/de-linker-local/
  instances.toml          实例登记表：名字 → 三个端口（本机所有检出共用）
  linker_local.my.cnf     MySQL 用户 linker_local 的口令
  .cache/                 WordPress、WooCommerce 与 Redis Object Cache 的安装包
  <name>/
    wordpress/            文档根；wp-content/plugins/linker-* 是指向检出的链接
    php.ini  router.php   PHP 内置服务器的配置与路由（每次 up 重写）
    admin.txt             后台登录说明（600）。干净安装是 local-admin 的口令；`just pull load` 之后口令已被快照换成不可逆占位，文件改写为剩余员工登录名与 `just login` 的用法
    mail/                 截获的邮件，*.eml
    logs/                 server.log、php-error.log、isolation.log、engine.log、genie.log
    run/                  pid 文件
```

`instances.toml` 在数据根而不在仓库：每张票一个工作树，它们共用一台 MySQL 与同一组端口，只有按机器的登记表才能保证两个实例不抢端口。

## 与线上一致的部分（来源）

| 项 | 本地 | 来源 |
|---|---|---|
| WordPress | 7.1.3，安装包 SHA-1 `13eb1d04…` 每次使用前核对 | 线上实测（`docs/research/2026-10-09/framework-choice.md` §2）；SHA-1 为 wordpress.org 发布的 `wordpress-7.1.3.zip.sha1` |
| WooCommerce | 11.2.0，`wp plugin verify-checksums` 逐文件核对 wordpress.org 的校验和 | 线上插件头（2026-10-09 SSH 只读）。线上会自动更新：WooCommerce 当天 07:54 UTC 从 11.1.0 升到 11.2.0，WordPress 设了 `WP_AUTO_UPDATE_CORE = 'minor'`；本地是钉死的，线上再变时改 `tools/local/src/linker_local/wordpress.py` 的版本与地址 |
| PHP | 8.3；`memory_limit`、`post_max_size`、`upload_max_filesize` 2048M，`max_execution_time`、`max_input_time` 360，`max_input_vars` 5000 | 主机 `~/.cl.selector/alt_php83.cfg`（2026-10-09 SSH 只读）；网页请求实际生效的值由 WooCommerce 系统状态核对（同日 REST 只读：`php_max_execution_time` 360、上传与 POST 上限 2 GB、`max_input_vars` 5000）。命令行里 `max_execution_time` 是 0：PHP 的 CLI 把它固定为 0，线上与本地 WP-CLI 都一样 |
| 对象缓存 | Redis 对象缓存（Redis Object Cache，PHP 客户端为插件自带的 Predis，php@8.3 没有 phpredis 扩展） | 线上切换时启用（规格 17"主机卫生"列了它与主机自带对象缓存两种，按实测选；选后者时本地跟着改）；本地同（规格 5） |
| 表前缀、固定链接 | `wp_`、`/%postname%/` | 线上 `wp-config.php` 与 `permalink_structure` |
| WP-CLI | 2.12 | 线上实测 |

不一致、且有意如此：

- 数据库服务器是 Homebrew MySQL（未固定版本，2026-10-09 为 9.6.0），线上是 MariaDB 11.8.9；表的排序规则同为 `utf8mb4_unicode_520_ci`。自 10.5.25、10.6.18、10.11.8、11.0.6、11.1.5、11.2.4、11.4.2 这几个版本起（线上的 11.8.9 在其后），`mariadb-dump` 在导出文件第一行写入沙箱注释 `/*!999999\- enable the sandbox mode */`，MySQL 8.4 及更早的客户端会在这一行报错（MariaDB 基金会《mariadb-dump file compatibility change》，2026-10-09 经 Apify 读取）。本机的 MySQL 9.6 客户端把这一行当普通注释接受，#6 的实测（tests/test_load.py）是线上 dump 原样导入，不去掉首行。
- PHP 的 `disable_functions` 等主机加固项不复制。
- 插件的 `vendor/` 由 `just` 按 `composer install` 装（含开发依赖，`just check`/`just test` 要用），所以本地每个请求都会多加载 PHPUnit、Mockery 的全局函数；线上发布不带开发依赖。
- 本地是干净安装：WooCommerce 用它自己的默认设置（美元、商店页对访客显示"即将开业"；线上是欧元、已开业），主题是 Twenty Twenty-Five。线上的主题（`picostrap5` / `picostrap5-child-base`）、插件（2026-10-09 经 SSH 只读读 `active_plugins` 与各插件头：启用的有 LiveCanvas 4.9.3、SEOPress 10.3、SEOPress PRO 10.2.1、WindPress 3.2.88、ACF PRO 6.3.1、Classic Editor 1.7.0 等）、页面、设置与内容都随 #6 的快照来；快照带哪些由 #6 定。
- LiveCanvas 的版本有意分叉：`up` 的干净安装钉 4.9.5（修复线上 4.9.3 在 `/wp/v2/` 第二页响应里加 HTML 前缀的缺陷，`docs/specs/12-site-chrome.md` 第 3 条），从快照装入或重建的实例按快照回到线上的 4.9.3——漂移是故意的，`up` 的版本警告会报出它，等线上升级后由快照带走。

## 隔离（`tools/local/mu/`，每次 `up` 复制进实例）

- **邮件**：`wp_mail()` 照常组信，发送一步改为写文件 `mail/<时间>-<UUID>.eml`，内容就是线上 `mail()` 会收到的那封（含 To、Subject、Cc、Bcc）；写不进去时 `wp_mail()` 照常报失败。WordPress 默认发件人 `wordpress@127.0.0.1` 会被 PHPMailer 拒绝，本地改为 `wordpress@example.test`。绕过 `wp_mail()` 直接调 `mail()` 的代码会失败：实例的 php.ini 设了 `sendmail_path = /usr/bin/false`，邮件到不了本机的 sendmail（macOS 的 Postfix 会真的投递）。
- **外联**：WordPress 的 HTTP API 只放行 `127.0.0.1`（实例自己、engine、Genie）；其余请求返回错误 `linker_local_blocked`，并记一行到 `logs/isolation.log`（时间、方法、URL）。从 127.0.0.1 重定向到别处也会被拦下（方法记为 `REDIRECT`）。WordPress 自己的更新检查也会出现在这里：建好的实例日志里就有几行 `api.wordpress.org`，都已被拦下；日志里的每一行都是一次没有发出的请求。
- **浏览器**：经过 WordPress 的每个响应都带 `Content-Security-Policy: default-src 'self' http://127.0.0.1:* …; form-action 'self'`，页面只能从本机加载资源、只能把表单提交给自己；以及 `X-Robots-Tag: noindex, nofollow`。`php -S` 直接返回的静态文件（图片、脚本）不带这两个头。
- **改写**：`router.php` 做线上 LiteSpeed 改写规则做的事（文件照原样给，目录补斜杠，其余交给 `index.php`）；mu-plugin 让 `got_url_rewrite()` 返回真，否则"设置 → 固定链接"会给每种结构前面加 `/index.php`。

隔离只管 WordPress 的 HTTP API 与邮件；插件若绕开 HTTP API 自己开连接，挡不住。`services/` 不在隔离之内（engine 要调 PVGIS，Genie 要调模型）。

## 对象缓存

每个实例建好时，`linker-local` 先删掉本实例前缀下的旧键，再装 Redis Object Cache 并自己复制它的 `object-cache.php`：插件自带的 `wp redis enable`、`disable`、`update-dropin`，后台的启用/停用按钮，以及停用插件，都会执行 FLUSHDB，把共用的第 0 号库连同别的实例的缓存一起清空，所以本地不用它们。要清一个实例的缓存，用 `just wp <name> cache flush`（只清本前缀）。一次性登录链接的 token 存在 transient 里，也就是 Redis 里，所以 `just login` 也要 Redis 在跑。

## 快照（#6 的装入接口）

`--snapshot <dir>` 认这样的目录（#6 的 `linker-pull snapshot` 按此写出，见 `docs/specs/6-live-pull.md` 的变更记录）：

```text
<dir>/plugins/<slug>/    插件目录，如 wp-content/plugins 里一样（规格 6 列的是 livecanvas、wp-seopress、wp-seopress-pro、windpress）
<dir>/themes/<slug>/     主题目录，如 wp-content/themes 里一样（线上是 picostrap5、picostrap5-child-base）
<dir>/uploads/           wp-content/uploads
```

插件与主题逐个替换实例里的同名目录，插件随后启用，主题只复制（启用哪个由数据库决定）；uploads 合并进实例；`linker-*` 只能来自检出，快照里出现即报错。安装这些文件的是 `linker_local.snapshot.install`，#6 的 `load` 也用它；数据库由 #6 装入。装入同时改写实例目录的 `admin.txt`：快照把每个账号口令换成不可逆占位（`anonymize.local_password`），`provision()` 写下的口令不再能登录，文件改为列出仍在的员工登录名，并指向 `just login <name> --user=<login>`。

## 服务

`just serve <name>` 先 `uv sync --locked`，再以 `uv run --locked … uvicorn` 在实例的两个端口上启动 engine 与 Genie，然后写两个选项：

| 选项 | 值 |
|---|---|
| `linker_engine_url` | `http://127.0.0.1:<engine 端口>` |
| `linker_genie_url` | `http://127.0.0.1:<Genie 端口>` |

这两个选项是插件找服务的约定（`docs/specs/13-genie.md`、`14-solution-configurator.md` 的变更记录）：本地由 `just serve` 写入，线上在切换时写入 VPS 的地址。`just down` 一并停掉。

## 测试

`just test` 跑 `tools/local` 的单元测试，并用真实的 MySQL、Redis、PHP 8.3 与 WP-CLI 建两个实例 `pytesta`、`pytestb` 验证：并存、版本、各自的 Redis 对象缓存、路由、改写、结账端点留在结账页所在位置、线上的 PHP 限额、邮件截获与 Bcc、写不了信时报失败、直接 `mail()` 失败、外联与重定向拦截、响应头、一次性登录与它的 10 分钟、快照装入（只激活线上当时已激活的插件）、错误快照路径先被拒绝、服务、重复 reset（含清掉旧缓存、不动另一个实例的缓存）。共 19 个；2026-10-09 测得 17 个时的计时：机器空闲时约 90 秒，并行的工作窗口占满 CPU 时（load average 25–40）130–215 秒。

- 这两个实例有自己的数据根（`LINKER_LOCAL_HOME`，结束后删除），但 MySQL、Redis、下载缓存和端口是全机共用的：同一时间只有一组在跑，其余检出的 `just test` 在锁 `~/de-linker-local/stack-test.lock` 上等候；分配端口时也避开 `~/de-linker-local/instances.toml` 里登记的端口。
- 若真有实例叫 `pytesta` 或 `pytestb`，测试拒绝运行，免得删掉它的库。
- CI 上没有这些工具，这组测试跳过；本机缺工具则失败。

## 常见故障

| 现象 | 处理 |
|---|---|
| `port … is in use by another program` | 另一个程序占了实例的端口：`lsof -nP -iTCP:<port> -sTCP:LISTEN` 查是谁 |
| `mysql` 报 `Can't connect … socket` | MySQL 没在跑：`brew services start mysql` |
| `… is incomplete (an earlier up stopped part-way)` | 上次建到一半失败：`just reset <name>` |
| `PHP 8.3 is required` | 直接运行了 `linker-local`：经 `just` 运行，或设 `PHP=/opt/homebrew/opt/php@8.3/bin/php` |
| `Redis is not running` | `brew services start redis` |
| `WP-CLI 2.12 is required` | `wp` 被升级或换掉了。Homebrew 没有旧版本，所以先 `brew pin wp-cli`；已经升级的，从 WP-CLI 的发布页取 2.12.0 的 phar 放到 PATH 上的 `wp` |
| `… exists but is not a registered instance` | 这个名字的目录或数据库不是 `linker-local` 建的（例如别的窗口手搭的栈）：换个名字，或把那个目录与库移走 |
| `vendor/ is missing` | 插件的 Composer 依赖没装：`just up` 会先装 |
| `verify-checksums` 失败 | 需要联网；或缓存的安装包损坏：删 `~/de-linker-local/.cache/` 里那个文件重来 |
| 首次进后台被带到 WooCommerce 页面 | WooCommerce 新装后的一次性欢迎跳转，之后正常 |
| 页面缺图、缺字体 | 外部资源被 CSP 挡住；干净安装没有线上内容，等 #6 的快照 |
