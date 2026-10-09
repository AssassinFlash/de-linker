# #6 线上只读拉取

## 目标
把线上的数据库、媒体、许可插件、站点选项以只读方式拉成快照，装入任一本地实例；快照不进仓库。

## 组成
- `tools/pull/`（同一个 uv 包，命令 `linker-pull`）：
  - `snapshot`：经 `ssh hostinger-de-linker` 在远端执行 `wp db export - | gzip`（只读）、`rsync -az` `wp-content/uploads/`、`rsync` 四个许可插件目录、`wp option list --format=json`（排除含密钥的选项：`*_api_key`、`*_secret`、`*token*`、`woocommerce_stripe_*`）、`wp plugin list --format=json`、`wp core version`。写入 `~/de-linker-data/<YYYYMMDD-HHMM>/`，生成 `manifest.json`（文件、sha256、行数）。
  - `anonymize`：对导出的 SQL 做伪名化：`wp_users.user_pass`、`user_activation_key` 置空；`wp_usermeta` 中应用密码删除；`billing_email`/`user_email`/订单地址等客户 PII 替换为 `customer-<n>@example.test` 与占位地址；员工账号（`administrator`/`shop_manager`）保留用户名、密码置为本地随机值。
  - `load <name> <snapshot>`：导入 SQL、`wp search-replace https://de-linker.com http://127.0.0.1:<port>`（含序列化）、复制 uploads、装插件、清缓存。
- 不进仓库：`~/de-linker-data/` 在 `.gitignore` 之外（仓库外路径）；仓库里只有脚本与 `manifest` 的 schema。

## 不做
不写线上；不拉取 Code Snippets 表之外的可执行内容进仓库（Snippets 表作为数据保留在 SQL 里，本地禁用该插件）。

## 验收
- [ ] 快照装入后：已发布商品 106、附件 2,755、德语 sitemap 150 条本地全部 200。
- [ ] `grep` 证明 SQL 中无 `$P$`/`$wp$` 密码哈希、无应用密码、无 `@`（除 `example.test` 与员工账号）。
- [ ] 两次 `snapshot` 的 manifest 可比对（增量清单）。

## 变更记录
- 2026-10-09（#5）：快照目录写成 `plugins/<slug>/`、`themes/<slug>/`、`uploads/` 三部分；`load` 装这些文件用 #5 的 `linker_local.snapshot.install`（`tools/local`，`just up <name> --snapshot <dir>` 用的也是它），自己只做导入 SQL、`search-replace`、清缓存，不再写第二份装文件的代码。线上主题 `picostrap5`、`picostrap5-child-base` 要进快照，否则本地首页对不上线上。线上数据库是 MariaDB 11.8.9，`wp db export` 的第一行是 MySQL 客户端不认的沙箱注释，导入本地 MySQL 前去掉（`docs/local-stack.md`）。
