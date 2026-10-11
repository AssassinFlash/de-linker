# #17 一次性切换上线

## 前提
#16 通过；业主确认维护窗口（夜间，停机以分钟计）；本地演练过完整切换脚本两次（干净快照 → 切换 → 回滚 → 再切换）。

## 脚本 `tools/cutover/`（经 `ssh hostinger-de-linker`，每步可单独重跑）
1. **备份**：`wp db export`、`wp-content/uploads`、`wp-content/plugins`、`.htaccess`、选项导出 → 本地 `~/de-linker-data/cutover-<date>/`，sha256 清单。
2. **维护模式开**（`wp maintenance-mode activate`）。
3. **部署**：rsync 三个新插件（含 `vendor/` 与 `build/`）、Polylang、新 `.po/.mo`；停用并删除 `terravolt-b2b-core`、`linker-ai-assistant`、旧 `linker-i18n`、`woocommerce-gateway-stripe`、`code-snippets`（先导出三条活动行的代码到 `docs/acceptance/<date>/17/snippets/` 并确认其功能已由新插件覆盖）、`terravolt-b2b-core-broken-20260704/` 与两个备份压缩包。
   - **mu 目录**：把 `mu-plugins/linker-error-recorder.php` 装到 `wp-content/mu-plugins/`（新记录件，替换线上同名文件：主机 `log_errors=OFF` 且没有可读的错误日志，记录件是唯一能回答"站点为什么坏了"的面；文件写进 `wp-content/linker-errors/php.log`，256 KB 轮转，目录带 `.htaccess` 拒绝与空 `index.html`）。
   - **mu 卫生**：删除 `wp-content/mu-plugins/linker-i18n-mu-loader.php`（旧 i18n 的早载垫片；请求语言解析现在归 Polylang 与 linker-i18n）与 `linker-error-recorder.php.bak-*`（旧记录件的备份）；保留 LiveCanvas 自带的 `livecanvas-must-use-plugin.php` 与主机平台的 `hostinger-*`。删除前把这两个文件复制到 `docs/acceptance/<date>/17/mu/` 存档（作为删除记录，不作代码继续使用）。
4. **数据**：运行 #7、#8、#9 的迁移脚本（`write`）；`python3 tools/migrate/80-customers.py --wp <WP-CLI> --user <admin> plan` 复核后 `apply --write`（存量客户一次性置为已通过，见该脚本的头部说明与 `rollback` 子命令：切换前就在的客户不该被账号审批门挡在外面）；Polylang 配置；运费区域清空；Woo 邮件收件人；选项清理（旧插件选项按清单删除）。
5. **服务**：发布 `services/engine` 与 `services/genie`（含索引）到 VPS；写入服务地址与令牌到 WP 选项（令牌不经仓库）。
6. **主机卫生**（共享主机留用、不升级）：启用 Redis 对象缓存（Hostinger 提供的对象缓存或 `wp plugin install redis-cache` + 主机 Redis 套接字，二选一按实测）；hPanel 设每分钟 cron 调 `wp cron event run --due-now`，并 `DISABLE_WP_CRON`；`wp post delete $(wp post list --post_type=revision --format=ids)` 清修订版并在 wp-config 设 `WP_POST_REVISIONS=5`；删除旧插件遗留的自定义表（`wp_tv_b2b_*`、`wp_linker_*`，先备份）；`wp option list --autoload=on --format=json` 审查 autoload 体量，清理旧 transients 与过期选项；LiteSpeed 全清；固定链接刷新；`wp cache flush`。
7. **维护模式关**；跑线上只读回归子集（150 个德语 URL、首页、分类页、产品页、Genie R1/R2 真实请求）；抽验旧地址 301（`data/legacy-redirects.json` 的三张表各取若干条 EN 与 DE，含 `/checkout/` → `/proforma-request/`、`/de/kasse/` → `/de/proforma-anfrage/`、`/shop/` → 商城页地址、`/produkt/<撤回 slug>/` 与其 `/product/` 兄弟同落点）；一次真实询盘（测试账号，随后撤销并删除）。

   mu 件生效实证：`wp eval 'trigger_error( "cutover smoke", E_USER_WARNING );'` 之后 `wp-content/linker-errors/php.log` 里必须出现该行（文件不存在或为空即视为部署失败）。
8. **回滚**（预案，演练过）：恢复备份的插件目录与 `.htaccess`，导入备份数据库，重新激活旧插件，清缓存。

## 验收
- [ ] 线上全部英文页面与 150 个德语 URL 200；`/design-canvas/` 301。
- [ ] `wp plugin list` 无旧插件；Snippets 表不存在或为空；插件目录无残留；`wp-content/mu-plugins/` 只剩 LiveCanvas 自带、主机平台的两件与新记录件。
- [ ] 旧地址 301 抽验通过（三张表各若干条 EN/DE，`data/legacy-redirects.json`）；存量客户全部为已通过（`tools/migrate/80-customers.py verify`）。
- [ ] 测试邮件只发一封、只发 chester@de-linker.com（AGENTS.md 测试邮件纪律，业主 2026-10-11）；多收件路由（客户副本/团队/Bcc）以 Outbox 队列收件人数据断言，不做多封实发。
- [ ] 视觉验收：首页、产品页、配置器、Genie、账户 × EN/DE × 1440/390（线上）。

## 变更记录
- 2026-10-09（#5）：切换时写入两个选项，指向 VPS 上的服务：`linker_engine_url`（#14 的引擎）与 `linker_genie_url`（#13 的 Genie）。本地由 `just serve` 写入同名选项。
- 2026-10-11（#81）：脚本落在 `tools/cutover/`（uv 项目 `linker-cutover`，just 模块 `tools/cutover/cutover.just`），第 1–8 步各是一个可单独重跑的子命令；`just cutover drill <实例>` 在一台本地实例上跑完整切换、回滚、再切换，并写出 `docs/acceptance/<date>/17/drill.json`。同一份代码两个目标：`--target local:<实例>` 与默认的生产主机（`ssh hostinger-de-linker`），因此演练证明的是窗口里要跑的那份代码，不是一套排练装置。三处对本文的偏差，各有证据：
  - **§1 的 `wp db export` 换 mysqldump**。生产主机的 PHP `disable_functions` 含 `exec`，而 WP-CLI 的 export 在碰 mysqldump 之前先调 `exec()`（wp-cli/db-command `DB_Command.php:655`），在那里是致命错误；理由与脚本同 `docs/specs/6-live-pull.md` 的变更记录。备份与恢复都走 mysqldump/mysql，且两个脚本只读写标准流——本地实例与主机上运行的是同一段脚本。顺带修一处本地栈缺陷：MySQL 8.0.32 起，`--single-transaction`（线上与本地都在用的那个一致性开关）会先 `FLUSH TABLES`，那是全局权限，而 `linker_local` 只有自己库的权限，因此本地实例无法按线上的方式被 dump——`tools/local` 的建库路径现在补授 `FLUSH_TABLES, RELOAD`。
  - **§3 的 Polylang 用 WP-CLI 装**（`wp plugin install polylang --activate`），不是 rsync。原生安装器会核对 wordpress.org 的包；从某个检出 rsync 一份会是同一个插件的第二个、不可核对的来源。
  - **§3 的 snippets 导出落在仓库外**（备份目录里的 `snippets/`），仓库里只留"三条活动行的功能由新插件承接"的确认记录。理由：本仓库不携带旧树的自定义代码（AGENTS.md 第 5 节），而导出物的用途是那次确认。
  - 另有两处补进清单：§3 的删除清单按现状写成数据（`terravolt-b2b-core`、`linker-ai-assistant`、`code-snippets`、`woocommerce-gateway-stripe`、两个备份压缩包与 `terravolt-b2b-core-broken-20260704/`、旧 i18n 的 mu-loader）；`linker-i18n` 走同 slug 就地替换，不列删除。`linker-error-recorder.php` 保留——它的替代物是错误记录那条独立事项，先删会把一项能力连同它的实现一起拿走。
  - §6 的 hPanel 每分钟 cron 与 LiteSpeed 全清框不进脚本：那两件只能在主机的控制面板里做，脚本把它们打印出来，不声称做过。
  - 新增一步不在本文里：`just cutover schema` 退役留用的 SEO 插件自己那份 Product 模板（见下条）。
- 2026-10-11（#81，GAP-7 的核验与落点）：在产品页上用 curl 断言（证据见 PR 与 `docs/acceptance/2026-10-11/17/`）——留用的 SEO 插件**确实**输出一个 `Product` 节点，来源是它自己的 schema 模板库（一个 `seopress_schemas` 条目，规则匹配 `post_type=product`），内容是一条写死的模板：`"brand": "Linker"`、`"manufacturer": "Linker"`、`"category": "Energy storage system"`，没有 sku、model、image、description、availability。关掉它（或关掉它依赖的基座）该节点即消失（1 → 0），来源因此可证。而线上今天真正输出的那个节点来自切换要删掉的那个插件：sku、brand/manufacturer = 厂商名、model、category、description、image、offers{url, availability}，**无价格**。两者不等价，且模板库内容在仓库里不可见、不可测——所以按票面"补结构化数据输出"分支：产品页的 `Product` 节点由 `linker-commerce` 输出（`Storefront\ProductSchema`，与读同样字段的 `ProductView` 同处；语义与今天一致：无价格、availability 取 Woo 原生库存、brand 取产品自己的 `pa_brand`），SEO 插件模板库里那条 Product 模板由切换退役（`just cutover schema`，入 trash 不 delete）。`/products/` 的 CollectionPage/BreadcrumbList 与首页的 WebSite/Organization 仍由它输出，未动。
- 2026-10-11（#80）：部署面加错误记录件 `mu-plugins/linker-error-recorder.php`（轮转，非 WordPress 依赖）；mu 卫生点名旧 `linker-i18n-mu-loader.php` 与旧记录件备份进删除清单；数据步加存量客户迁移 `tools/migrate/80-customers.py`；验收加旧地址 301 抽验、存量客户状态与记录件实证。
- 2026-10-11（#80 修复轮）：抽验清单补上本轮数据化的两条线上硬编码规则——退役归档 `/shop/` 与英文 `/produkt/<撤回 slug>/` 别名基底（映射表 pages 的 `/shop/` 一条与 `requested_product()` 的路径解析），两者落点以线上实测为准。
