# #17 一次性切换上线

## 前提
#16 通过；业主确认维护窗口（夜间，停机以分钟计）；本地演练过完整切换脚本两次（干净快照 → 切换 → 回滚 → 再切换）。

## 脚本 `tools/cutover/`（经 `ssh hostinger-de-linker`，每步可单独重跑）
1. **备份**：`wp db export`、`wp-content/uploads`、`wp-content/plugins`、`.htaccess`、选项导出 → 本地 `~/de-linker-data/cutover-<date>/`，sha256 清单。
2. **维护模式开**（`wp maintenance-mode activate`）。
3. **部署**：rsync 三个新插件（含 `vendor/` 与 `build/`）、Polylang、新 `.po/.mo`；停用并删除 `terravolt-b2b-core`、`linker-ai-assistant`、旧 `linker-i18n`、`woocommerce-gateway-stripe`、`code-snippets`（先导出三条活动行的代码到 `docs/acceptance/<date>/17/snippets/` 并确认其功能已由新插件覆盖）、`terravolt-b2b-core-broken-20260704/` 与两个备份压缩包。
4. **数据**：运行 #7、#8、#9 的迁移脚本（`write`）；Polylang 配置；运费区域清空；Woo 邮件收件人；选项清理（旧插件选项按清单删除）。
5. **服务**：发布 `services/engine` 与 `services/genie`（含索引）到 VPS；写入服务地址与令牌到 WP 选项（令牌不经仓库）。
6. **主机卫生**（共享主机留用、不升级）：启用 Redis 对象缓存（Hostinger 提供的对象缓存或 `wp plugin install redis-cache` + 主机 Redis 套接字，二选一按实测）；hPanel 设每分钟 cron 调 `wp cron event run --due-now`，并 `DISABLE_WP_CRON`；`wp post delete $(wp post list --post_type=revision --format=ids)` 清修订版并在 wp-config 设 `WP_POST_REVISIONS=5`；删除旧插件遗留的自定义表（`wp_tv_b2b_*`、`wp_linker_*`，先备份）；`wp option list --autoload=on --format=json` 审查 autoload 体量，清理旧 transients 与过期选项；LiteSpeed 全清；固定链接刷新；`wp cache flush`。
7. **维护模式关**；跑线上只读回归子集（150 个德语 URL、首页、分类页、产品页、Genie R1/R2 真实请求）；一次真实询盘（测试账号，随后撤销并删除）。
8. **回滚**（预案，演练过）：恢复备份的插件目录与 `.htaccess`，导入备份数据库，重新激活旧插件，清缓存。

## 验收
- [ ] 线上全部英文页面与 150 个德语 URL 200；`/design-canvas/` 301。
- [ ] Genie R1/R2 线上通过；询盘流程线上通过；邮件 24 小时内到达 sales@ 与 Bcc。
- [ ] `wp plugin list` 无旧插件；Snippets 表不存在或为空；插件目录无残留。
- [ ] 视觉验收：首页、产品页、配置器、Genie、账户 × EN/DE × 1440/390（线上）。
