# 本地回滚演练记录（#81 / spec 17 的前提）

命令：`just cutover drill t81 --administrator=857558227@qq.com`。
机器可读的完整记录：`drill.json`（四份指纹 + 每一步的动作与说明，两次完整通过）。

实例 `t81`：`just up t81` → `just pull load t81 20261010-0033 --live-code`，即线上代码 + 线上数据的本地副本。
演练跑的就是维护窗口要跑的那份代码：`Target` 只有两个实现（本地实例 / `ssh hostinger-de-linker`），
步骤本身不知道自己在哪，所以这份记录是关于窗口的证据，不是关于一套排练装置的。

## 做了什么

第一遍：备份 → 维护模式开 → 部署（三个插件 + Polylang）→ 导出 snippet 行 → 停用并删除四个旧插件、
清残留目录与旧 mu-loader → 三个数据迁移（**只打印计划**）→ 退役 SEO 插件那条 Product 模板 → 主机卫生 →
维护模式关 → 只读回归子集。

然后**回滚**：导入备份数据库、还原插件目录与 uploads、清缓存。

第二遍：同样的十二步再来一次。

## 断言（演练自己校验，不通过即失败）

| 断言 | 结果 |
|---|---|
| 起点是装入的干净快照（四个旧插件在盘上） | ✓ 否则当场拒绝 |
| 回滚后与切换前**逐项相同**（插件清单与状态、发布商品数、维护模式、十个入口的响应码） | ✓ `before == after_rollback` |
| 第二遍结束时与第一遍结束时相同（窗口可以重跑） | ✓ `after_first == after_second` |

十个入口的响应码（前 → 切换后 → 回滚后 → 再切换后）：

| 地址 | 前 | 切换后 | 回滚后 | 再切换后 |
|---|---|---|---|---|
| `/` | 200 | 200 | 200 | 200 |
| `/de/` | 200 | 200 | 200 | 200 |
| `/products/` | 200 | 200 | 200 | 200 |
| `/de/produkte/` | 200 | **404** | 200 | **404** |
| `/proforma-request/` | 200 | 200 | 200 | 200 |
| `/de/proforma-anfrage/` | 200 | **404** | 200 | **404** |
| `/my-account/` | 200 | 200 | 200 | 200 |
| `/de/mein-konto/` | 200 | **404** | 200 | **404** |
| `/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/` | 200 | 200 | 200 | 200 |
| `/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/` | 200 | 200 | 200 | 200 |

## 三个 404 是什么，以及演练证明不了什么

三个德语页面在切换后 404，是因为**德语对象由数据迁移 #9 创建**（把旧 i18n 的德语对象导入 Polylang），
而迁移在演练里按设计只打印计划：`9-i18n` 要调翻译服务，本地隔离层按法律挡住外发；写下去的迁移会让实例
不再是"干净快照"，第二遍就失去意义。演练跑完的实例里 Polylang 一个语言都没有（`pll_languages_list()` 为空），
所以德语页面这一半不存在——这不是切换脚本的缺陷，是"数据那一步还没执行"的可见后果。

演练因此证明的是**切换机制**：备份可回滚、删除清单正确、插件换装正确、每一步可单独重跑、回滚真的把站点还原。
它证明不了**数据结果**：德语页面、产品事实、Polylang 语言与翻译关系都要靠窗口里 `just cutover data --write`
（连同 #7/#8/#9）真正写下去。窗口的只读回归子集（spec 17 §7 的 150 个德语 URL）是这两件事合起来之后才成立的检查。

`/design-canvas/` 在演练后仍是 200 而不是 301：它 301 是 spec 12 的重定向工作，属另一条在途线；
演练把这条差异如实报出来（`verify` 的 note），不改它。

## 演练暴露并当场修掉的东西（都不是靠读代码发现的）

- 主机 PHP 禁用 `exec`，`wp db export` 在那里不可用 → 备份改 mysqldump（与 tools/pull 同源理由）。
- MySQL 8.0.32 起 `--single-transaction` 需要全局 `FLUSH TABLES` 权限，本地实例的库用户没有 → `tools/local` 的建库路径补授。
- 备份里的 `SET @@GLOBAL.GTID_PURGED` / `SET @@SESSION.SQL_LOG_BIN` 需要 SUPER，站点自己的库用户导不进去 →
  dump 端加 `--set-gtid-purged=OFF`（只在 mysqldump 认得它时）与 `--no-tablespaces`。
- macOS 的 bash 3.2 在 `set -u` 下把空数组的 `"${a[@]}"` 当未绑定变量 → 脚本改用 `${a[@]+"${a[@]}"}`，
  并加了两个真跑 shell 的回归测试。
- `wp plugin install polylang` 在本地实例上必然失败（隔离层挡 wordpress.org）→ 已装则只激活。
- `wp post delete` 对 `seopress_schemas` 不支持回收站 → 退役改成 `--post_status=draft`。
- `wp option list --fields=…,size` 没有 `size` 字段 → autoload 体量改为写 JSON 报告（213 条、18768 字节）。
- 9-i18n 的 `--user` 必须写在 `apply` 之前（argparse 的子命令）→ 迁移命令行按 argparse 的位置拼。
- 演练自己出错时会把站点留在维护模式 → 失败路径现在先把维护模式关掉，且不再覆盖最初的错误。
