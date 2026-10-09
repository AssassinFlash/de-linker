# #6 线上只读拉取

## 目标
把线上的数据库、媒体、许可插件、站点选项以只读方式拉成快照，装入任一本地实例；快照不进仓库。

## 组成
- `tools/pull/`（uv 项目，命令 `linker-pull`，just 模块 `tools/pull/pull.just`）：
  - `snapshot`（`just pull`）：经 `ssh hostinger-de-linker` 只读读取线上，写入 `~/de-linker-data/<YYYYMMDD-HHMM>/`（先写 `.<名字>.partial/`，完整后改名）：
    - `db.sql.gz`：主机上 `mysqldump --single-transaction --skip-dump-date --order-by-primary`（连接参数由 `wp config get` 在主机上读出，密码只进 mysqldump 的环境），gzip 后流回本机，**边读边伪名化**，原始导出不落盘；写完后扫描文件本身，不合格即删除并失败。
    - `uploads/`：`rsync -az` `wp-content/uploads/` 的白名单：媒体库年份目录、WooCommerce 占位图、`windpress/`（页面加载的编译 CSS）。
    - `plugins/<slug>/`：四个许可插件（livecanvas、wp-seopress、wp-seopress-pro、windpress）；`themes/<slug>/`：当前主题与父主题。
    - `live/plugins/`、`live/mu-plugins/`：线上其余插件目录与 must-use 插件（主机平台的除外），供 `load --live-code` 在本地得到线上站点的副本。
    - `site/`：`options.json`（伪名化后的 wp_options，不含临时项与含密钥的选项）、`plugins.json`（`wp plugin list`）、`themes.json`（`wp theme list`）、`sitemaps/`（robots.txt 声明的线上 sitemap）。
    - `manifest.json`：每个文件的 sha256 与大小；每张表的行数与行内容 sha256；文章按类型/状态计数；伪名化报告（只有计数与名称）；扫描结果。结构：`tools/pull/manifest.schema.json`。
    - 没变的文件硬链接到上一份快照（与中断留下的 `.partial/`）。
  - `anonymize`：伪名化规则（快照内联调用；也可对一个 dump 文件单独运行）：
    - 账号：`administrator`/`shop_manager` 为员工，保留用户名与邮箱，密码置为由线上值派生的本地值（`local-…`，不是任何哈希，任何密码都登不进；两次快照对同一账号得出同一值）；其余账号改为 `customer-<ID>`（用户名、显示名、邮箱 `customer-<ID>@example.test`），密码与 `user_activation_key` 置空，账单/收货/公司字段换占位值，其余非设置类 usermeta 置空；所有人的应用密码、登录会话、按 IP 定位的位置、Stripe 客户号删除。
    - 其余任何位置的邮箱（订单、评论、选项、计划任务、正文）：账号邮箱换成该账号的伪名，其余换成 `customer-<n>@example.test`（n 从 100001 起）；保留员工账号、`example.test` 与公司自有域名（de-linker.com、sunriverinverter.com）的邮箱。
    - 订单：同一条规则作用于订单表与两种存储的订单 meta（经典订单在 `wp_postmeta`、HPOS 在 `wp_wc_orders_meta`）：地址、电话、IP、UA、客户备注、支付商标识、旧插件的买家快照（`tv_b2b_document_ledger_v2`、`tv_b2b_order_vat_snapshot` 等）替换或置空；订单 key 的每一份副本换成同一个本地 key。
    - 旧插件的客户提交（联系与项目请求、项目事件与产物、审计日志、增值税声明、AI 对话）、计划任务（Action Scheduler 的任务与日志）以及会话、限流、API key、支付 token 表：保留表结构，不保留行。
    - 选项：删除临时项、含密钥的选项（`*_api_key`、`*_secret`、`*token*`、`woocommerce_stripe_*`，及证据补充的 `lc_apikey`、`*licen[cs]e*`、`edd_sl_*`、`wcstripe_cache_*`、`mailserver_pass`、`recovery_keys`、`woocommerce_share_key`）与旧插件的邮件/请求日志。
    - Code Snippets：未在运行（`active` ≠ 1）的片段代码置空；运行中的片段去掉写在代码里的凭据。
    - 全库：密码哈希、可识别形态的密钥、Stripe 对象号删除；任何表的序列化/JSON 值里，键名以凭据词结尾（`api_key`、`secret`、`token`、`password`、`pass`、`license_key`、`private_key`，可带 `_encrypted`）且不是空值/数字/yes-no 的值置空。
    - 写完后扫描文件本身：密码哈希前缀、应用密码、密钥形态与按名存放的凭据（JSON、序列化、PHP 代码）、Stripe 对象号、明文或 URL 编码的邮箱；不合格即删除并失败。
  - `load <name> <snapshot> [--port N] [--live-code]`：实例是 linker-local 的——按名字在它的登记表（`instances.toml`）里解析（`just up <name>` 建立并登记；名字过 `check_name`；`--port` 覆盖写进数据库的地址），数据库 `linker_<name>`，`wp-config.php` 必须指向它。装入前先拒三样：实例的 WordPress/WooCommerce 版本与快照的（manifest 的 `source.wordpress` 与 `site/plugins.json`）不一致；`db.sql.gz` 不是可读的 gzip 或 sha256 与 manifest 不符；`--live-code` 时实例的插件链接到某个检出。然后才清空并导入 `wp_` 表（MariaDB 的 dump 原样导入，本机 MySQL 9.6 客户端接受其首行）、`wp search-replace` 把 `https://de-linker.com` 的原样/JSON 转义/URL 编码三种写法换成 `http://127.0.0.1:<port>`（含序列化）、立即 `wp cache flush`（本地栈启用 Redis 对象缓存，旧值已失效）；文件全部用 #5 的 `linker_local.snapshot.install` 装（`--live-code` 时传 `live_code=True`，连 `live/` 两棵树也由它装）——插件与主题目录整体替换同名项，uploads 合并进去；不传 `--live-code` 时启用实例原有插件加许可插件，传时沿用线上启用列表；Code Snippets 始终不启用；`wp rewrite flush`；最后对照 manifest 报告已发布商品数、附件数、缺失附件文件、残留线上地址，不一致即失败，并列出员工登录名（装入后用户来自快照，`just login <name> --user <员工登录名>` 进后台）。
  - `diff <旧> <新>`：两份快照的增量清单（文件增/删/改、表与文章计数的变化）；`scan <快照>`：重扫 SQL；`check-urls <快照> --base <url>`：逐个请求快照里线上 sitemap 的地址。
- 不进仓库：`~/de-linker-data/` 在仓库之外；`.gitignore` 另挡 `*.sql.gz` 与 `de-linker-data/`。仓库里只有脚本、manifest 的 schema 与合成数据的测试夹具。

## 不做
不写线上；不拉取 Code Snippets 表之外的可执行内容进仓库（Snippets 表作为数据保留在 SQL 里，本地禁用该插件）。

## 验收
- [ ] 快照装入后：已发布商品 106、附件 2,755、德语 sitemap 150 条本地全部 200。
- [ ] `grep` 证明 SQL 中无 `$P$`/`$wp$` 密码哈希、无应用密码、无 `@`（除 `example.test`、员工账号与公司自有域名 de-linker.com / sunriverinverter.com 的邮箱）。
- [ ] 两次 `snapshot` 的 manifest 可比对（增量清单）。

## 变更记录
- 2026-10-09（#5）：快照目录写成 `plugins/<slug>/`、`themes/<slug>/`、`uploads/` 三部分；`load` 装这些文件用 #5 的 `linker_local.snapshot.install`（`tools/local`，`just up <name> --snapshot <dir>` 用的也是它），自己只做导入 SQL、`search-replace`、清缓存，不再写第二份装文件的代码。线上主题 `picostrap5`、`picostrap5-child-base` 要进快照，否则本地首页对不上线上。线上数据库是 MariaDB 11.8.9，`wp db export` 的第一行是 MySQL 客户端不认的沙箱注释，导入本地 MySQL 前去掉（`docs/local-stack.md`）。
- 2026-10-09（#6，实测修正 #5 的假设）：MySQL 9.6 的客户端把 MariaDB dump 的沙箱首行当普通注释接受，线上 dump 原样导入、不去掉首行（tests/test_load.py 用真 MySQL + 真 dump 验证；`docs/local-stack.md` 末句同步改写）。
- 2026-10-09（#5）：`load` 先比对快照 manifest 里的 `wp core version` 与 WooCommerce 版本和实例装的是否一致，不一致就拒绝装入：线上会自动更新（WooCommerce 2026-10-09 从 11.1.0 升到 11.2.0），把新版本迁移过的库装进旧代码是降级，没有迁移路径。#5 在干净安装上无法验收的几项，在装入后验：`/products/`、`/proforma-request/` 返回 200，本地与线上首页对照截图重做一次；`/de/` 归 #9。
- 2026-10-09（#5）：验收里"德语 sitemap 150 条本地全部 200"移到 #9：德语路由由 #9 的 Polylang 与 linker-i18n 提供（`snapshot.install` 不收线上旧的 `linker-*` 插件），规格 9 的验收已含 150 个德语 URL；#6 装入后验英文路由（`/products/`、`/proforma-request/`）与首页对照。
- 2026-10-09（#6）：`wp db export` 改为主机上直接 mysqldump。证据：主机 CLI 的 PHP `disable_functions` 含 `exec`，`wp db export -` 在 `DB_Command.php:655` 调用 `exec()` 即致命错误（2026-10-09 SSH 实测）；mysqldump 正是 WP-CLI 本会调用的程序。
- 2026-10-09（#6）：快照另带 `themes/` 与 `live/`（线上其余插件与 must-use 插件），`load --live-code` 装入。证据：`/de/` 路由与德语 sitemap 由线上旧 linker-i18n 提供（`docs/research/2026-10-09/i18n-audit.md`），不装它本地德语 URL 无法 200；页面依赖当前主题。这些代码只在仓库外的快照里。
- 2026-10-09（#6）：uploads 改为白名单。证据：线上 `wp-content/uploads/` 另有 `wc-logs/`（邮件与错误日志）与 `tv-b2b-private/`（一位客户的营业文件）。
- 2026-10-09（#6）：旧插件的客户提交表只保留结构。证据：2026-10-09 的 dump 中这些表含姓名、电话、地址、站点坐标与自由文本（审计日志 19.6 万行），没有任何规格读取它们（`docs/specs/*`）。
- 2026-10-09（#6）：验收的邮箱例外加上公司自有域名。证据：已发布页面与页脚含 `sales@de-linker.com` 等公司邮箱、`sales@sunriverinverter.com` 是站点通知副本收件人；它们不是客户数据，替换会改动本地页面内容。
- 2026-10-09（#6）：`options.json` 取自伪名化后的 dump 的 wp_options，与 SQL 同一时刻、同一套规则，不再另跑 `wp option list`。
- 2026-10-09（#6，评审后）：计划任务表只保留结构，未运行的 Code Snippets 代码置空，旧插件的邮件/请求日志选项删除，订单 meta 里旧插件的买家快照置空，Stripe 对象号删除，按键名清空凭据扩展到所有表，扫描加宽到按名存放的凭据、PHP 代码、Stripe 对象号与 URL 编码的邮箱。证据：首份快照里有 NVIDIA API 密钥（snippet 224）、引擎令牌明文（snippet 276）、`woocommerce_send_queued_transactional_email` 任务参数里的新账号明文密码、`tv_b2b_document_ledger_v2` 与日志选项里的买家姓名电话地址、订单备注里的 22 个 Stripe 对象号；旧扫描没有发现这些。这两份快照已删除。
- 2026-10-09（#6，评审后）：员工密码不是"随机值"而是由线上值派生的本地值。理由：两次快照对未变化的账号得出同一行，manifest 的逐表比对才有意义；它不是哈希，任何密码都登不进。
- 2026-10-09（#6，Spec 第 2 轮评审后）：`plugin list`/`theme list` 加 `--skip-update-check`，全部远端 WP-CLI 命令加 `--skip-plugins --skip-themes`。证据：wp-cli 2.12.0 phar 的 `CommandWithUpgrade::_list()`（extension-command）在没有该参数时先 `delete_site_transient('update_plugins'|'update_themes')` 再调 `wp_update_plugins()/wp_update_themes()`——快照对线上的写，"只读"是二元的；不加载插件/主题则不让线上旧插件在读取时初始化。
- 2026-10-09（#6，Spec 第 2 轮评审后）：Stripe 对象号前缀表补全 pyr_（退款，快照 wp_comments 的 "Refunded … Refund ID: pyr_…"）、seti_（setup intent）与 tok_（卡令牌）。证据：旧表只认 pi|ch|py|re|cus|pm|src，那个 pyr_ 号漏过了扫描；seti_/tok_ 是 WooCommerce Stripe 扩展其余会记录的支付对象。
- 2026-10-09（#6，Spec 第 2 轮评审后）：manifest 的表清单按本规格"每张表"列出——没有 INSERT 的表也记 rows 0 与空内容的 sha256；此前只列有 INSERT 的表。
- 2026-10-09（#6，Spec 第 2 轮评审后）：夹具与测试里的引擎令牌是替身（0f0f…，与真令牌无公共片段）；曾把真令牌前 6 hex 写进旧 PR #43 历史里的一个提交（该分支已压成单提交强推替换），换新 PR 后 origin 分支历史不再含它（旧 PR 的 refs/pull 残留 24 bit 前缀，密码学上无害，新 PR 描述注明）。
- 2026-10-10（#6，评审线 Spec+Standards 复审后）：`load` 重接线到 #5——实例解析用 `linker_local.Registry`/`Instance`，装文件只用 `linker_local.snapshot.install`（`live/` 两棵树经其 `live_code` 参数装入，`up --snapshot` 不传它，实例的 `linker-*` 插件仍来自检出）；装入前先做版本守卫（实例的 WP/WooCommerce 版本 ≠ 快照的即拒，数据库被新版迁移过就没有回退路径）并校验 dump 可读且 sha256 与 manifest 一致。裁定与证据见 PR #47 评审。
- 2026-10-10（#6，评审线复审后）：`wp config get` 纳入 READ_ONLY，dump 脚本里的 `wp config get` 同样带 `--skip-plugins --skip-themes`；`scan` 命令对非 gz 的 `.sql` 与其它读法对齐；扫描的 docstring 写明它是枚举已知形态而非排除证明；check-urls 长跑每 30 秒报进度；rsync 计数按文件/目录分列；README 写明快照可以随时删（硬链接保证只被现存快照引用的数据不丢）。
- 2026-10-10（#6，Spec 复审第 3 轮后）：`load --live-code` 在 search-replace 之后重算被地址改写破坏的旧 i18n 德文新鲜度指纹（`_linker_de_source_sha`、`_linker_de_excerpt_sha`）：经 `wp eval-file` 在实例内调用旧插件自己的 `Translator::content_sha`/`Document::key`/`mark_current`，且仅当"把内容里的本地地址换回线上地址后、插件自己的公式能复现存档指纹"时才重算——失配须证明是改写引起的，装入前本就过期的德文保持过期。证据：首份装入里 61 篇重算、0 篇装入前过期；德文首页曾因此回退英文（316 篇存德文中 18 个页面受影响，h1 变 "Linking Value. Serving You."）。过渡脚手架，随 #18 旧插件删除而删除。verify 同时增加语言保真抽验（--live-code 且装了旧 i18n 插件时：抽 3 个存德文页面的德语路由，`<html lang>` 与正文词汇都须是德语，否则 ok=false），使回退不能再藏在 ok:true 后面。
- 2026-10-10（#6，追加查明）：`--live-code` 副本首页的"Identify by nameplate photo"按钮（相机入口）系统性缺失的根因：伪名化按规则清空了 `linker_ai_settings_v1` 的加密密钥字段（快照不带凭据是本票的法律），旧助手插件的能力门（ticket 008 设计）据此把 `capabilities.vision` 判 false，前端 bundle 隐藏所有 nameplate 入口——线上有密钥所以显示。本地不修：给它真密钥等于在实例盘上明文放密钥、且隔离层本就禁止外发（能力是假的）；改门等于分叉旧插件规则。视觉一致性的归属在新栈（#12 外壳/#13 Genie 入口）。
