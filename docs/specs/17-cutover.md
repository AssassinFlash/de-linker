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
- [ ] Genie R1/R2 线上通过；询盘流程线上通过；邮件 24 小时内到达 sales@ 与 Bcc。
- [ ] `wp plugin list` 无旧插件；Snippets 表不存在或为空；插件目录无残留；`wp-content/mu-plugins/` 只剩 LiveCanvas 自带、主机平台的两件与新记录件。
- [ ] 旧地址 301 抽验通过（三张表各若干条 EN/DE，`data/legacy-redirects.json`）；存量客户全部为已通过（`tools/migrate/80-customers.py verify`）。
- [ ] 视觉验收：首页、产品页、配置器、Genie、账户 × EN/DE × 1440/390（线上）。

## 变更记录
- 2026-10-09（#5）：切换时写入两个选项，指向 VPS 上的服务：`linker_engine_url`（#14 的引擎）与 `linker_genie_url`（#13 的 Genie）。本地由 `just serve` 写入同名选项。
- 2026-10-11（#80）：部署面加错误记录件 `mu-plugins/linker-error-recorder.php`（轮转，非 WordPress 依赖）；mu 卫生点名旧 `linker-i18n-mu-loader.php` 与旧记录件备份进删除清单；数据步加存量客户迁移 `tools/migrate/80-customers.py`；验收加旧地址 301 抽验、存量客户状态与记录件实证。
- 2026-10-11（#80 修复轮）：抽验清单补上本轮数据化的两条线上硬编码规则——退役归档 `/shop/` 与英文 `/produkt/<撤回 slug>/` 别名基底（映射表 pages 的 `/shop/` 一条与 `requested_product()` 的路径解析），两者落点以线上实测为准。
