# de-linker

de-linker.com 的重建：WordPress + WooCommerce 上的德国 B2B 光伏储能询盘网站。私有仓库。

工作规则在 `AGENTS.md`，执行票的交付与验收在 `docs/acceptance/protocol.md`，证据在 `docs/research/`。交付管线：本地 → 评审站 → 线上。

## 目录

| 路径 | 内容 |
|---|---|
| `plugins/linker-commerce` | 商务链、产品事实与 Abilities。PHP，`Linker\Commerce\` → `includes/` |
| `plugins/linker-i18n` | Polylang 伴侣插件。PHP，`Linker\I18n\` → `includes/` |
| `plugins/linker-tools` | Genie 与 Solution Configurator：PHP 壳（`Linker\Tools\` → `includes/`）和 React 应用（`src/`，入口 `genie`、`configurator`、`shared`），构建产物提交在 `build/` |
| `services/genie` | Genie 的代理循环服务（FastAPI，`linker_genie`；与 `linker-tools` 里转发请求的 PHP 代理不是一回事） |
| `services/engine` | Solution Configurator 的引擎（FastAPI，`linker_engine`） |
| `tools/` | just 模块（`build.just`、`pull.just`）、PHP 项目共用的工具配置（`php/`：PHPCS 规则；PHPStan 设置，`phpstan.neon` 全部 PHP 项目共用，`phpstan-plugins.neon` 再加插件用的 WooCommerce stubs 与测试 bootstrap；插件的 PHPUnit bootstrap）、本地栈 `local/`（uv 项目 `linker-local`，见 `docs/local-stack.md`）、数据迁移 `migrate/`（每票一个 `<票号>-<名>.py` + 计划 `.json` + WordPress 侧 `.php`，经 WP-CLI 执行；uv 项目，PHP 由 `linker-commerce` 的 PHPCS/PHPStan 检查）、线上只读快照 `pull/`（uv 项目 `linker-pull`） |
| `docs/` | 验收协议、各票规格（`docs/specs/`）与研究证据 |

PHP 类按 PSR-4 一类一文件，测试在各插件的 `tests/php/`。各插件的 `phpcs.xml.dist`、`phpstan.neon.dist`、`tests/php/bootstrap.php` 只写本插件的文件、文本域与前缀，其余引用 `tools/php/`；`phpunit.xml.dist` 每个插件一份，因为 PHPUnit 9.6 的配置文件之间不能共享根元素属性。JS 单测是 `src/` 与 `bin/` 下的 `*.test.ts(x)`，端到端测试在 `plugins/linker-tools/tests/e2e/`。Python 服务是 uv 的 src 布局：规格里写作 `services/genie/retrieval.py` 的模块就是 `services/genie/src/linker_genie/retrieval.py`；包外的脚本（如 `services/genie/index/`）同样受 Ruff 与 mypy 检查（两者都对整个服务目录运行）；测试在各服务的 `tests/`。`tools/local` 同时是 uv 项目（`src/linker_local/`、`tests/`）与只做静态检查的 Composer 项目（实例用的 mu-plugin `mu/` 与 PHP 服务器路由 `router.php`）。

`tools/migrate` 是 uv 项目（测试在 `tools/migrate/tests/`）；它的 WordPress 侧 `*.php` 经 `wp eval-file` 运行，借用 `plugins/linker-commerce` 的 `phpcs.xml.dist`/`phpstan.neon.dist` 检查（迁移的是这个插件读的商品数据），不另设 Composer 项目。需要真实站点的测试——`linker-commerce` 的 `tests/php/Integration`（`LINKER_COMMERCE_TEST_SITE`，站点地址）与 `tools/migrate/tests/test_7_facts_wordpress.py`（`LINKER_MIGRATE_TEST_WP`，WP-CLI 命令）——在没有这两个环境变量时跳过，CI 上就是跳过。

## 工具链

| 项 | 版本 | 来源 |
|---|---|---|
| PHP | 8.3 | 生产主机实测 8.3.33（`docs/research/2026-10-09/framework-choice.md` §2）。写在各插件 `composer.json` 的 `config.platform.php`（PHPStan 从这里读）与 `tools/php/phpcs.xml` 的 `testVersion` |
| WordPress / WooCommerce | 7.1 / 11.2 | 主机实测 7.1.3（§2）；WooCommerce 由主机自动更新，2026-10-09 07:54 UTC 起是 11.2.0（当天 SSH 只读读插件头，§2 写的 11.1.0 是更新前测的）：插件头 `Requires at least`、`minimum_wp_version`、`php-stubs/wordpress-stubs ~7.1.0`、`php-stubs/woocommerce-stubs ~11.2.0` |
| PHPUnit | 9.6 | WP_Mock 1.1 要求 `phpunit/phpunit ^9.6`；WordPress 与 WooCommerce 也用 9.6（§6） |
| PHPStan | level 8 | AGENTS.md §4；WooCommerce core 用 level 8（§6）。写在 `tools/php/phpstan.neon` |
| PHPCS | WPCS 3 + woocommerce-sniffs + PHPCompatibilityWP | AGENTS.md §4；规则集 `WooCommerce-Core` 包含三者。锁定的 PHPCompatibility 是 9.3.5（2019-12 发布，早于 PHP 8.0；woocommerce-sniffs 2.0 要求 phpcompatibility-wp ^2.1.7，后者要求 php-compatibility ^9.0），它没有 PHP 8.x 的 sniff，`testVersion 8.3-` 几乎不起作用：真正挡住新于 8.3 的语法与函数的是 PHPStan（按 `config.platform.php` 的 8.3 解析）和 CI 上的 PHP 8.3 |
| Node | 22 | `@wordpress/scripts` 36 的 engines 为 `^22.22.2 \|\| ^24.15.0 \|\| >=26.0.0` |
| React | 18.3.1 | WordPress 7.1.3 自带的版本（§2；wordpress-develop 7.1.3 的 `package.json`）。构建时 React、JSX 运行时与 `@wordpress/*` 都外部化，页面用 WordPress 那份；`node_modules` 里的只供测试与类型检查 |
| `@wordpress/element` / `i18n` / `dom-ready` | 8.3.0 / 6.24.0 / 4.51.0 | WordPress 7.1.3 自带的版本：wordpress-develop 7.1.3 的 `package.json` 把 Gutenberg 钉在提交 `dd294ab8`，这是该提交里各包 `package.json` 的版本（2026-10-09 经 Apify 读取）；钉死，不用 `^`，测试才与页面上的行为一致 |
| TypeScript | 6.0 | `@wordpress/eslint-plugin` 27 依赖的 typescript-eslint 8.71.1 只接受 `typescript >=4.8.4 <6.1.0`，所以是 `~6.0.3`，不是 7 |
| Vitest / Playwright / Storybook | 5 / 1.64 / 10.6 | `@wordpress/scripts` 36 的 `test-unit-js` 只支持 Vitest 5（`node_modules/@wordpress/scripts/docs/vitest-migration.md`）；Playwright 与 Storybook 与 Gutenberg（Playwright ^1.63）、WooCommerce Blocks（Storybook 10.5）同代（§3.1、§3.3），取安装时的最新版 |
| Python | 3.12 | VPS（§7）；各服务的 `.python-version` |
| uv | 0.10.11 | 写出 `uv.lock` 的版本，CI 固定同一版本 |
| just | 1.58 | 本机版本，CI 固定同一版本 |
| WP-CLI | 2.12 | 生产主机实测 2.12.0（§2）；本地实例用 Homebrew 的 `wp`，在 PHP 8.3 上运行，`linker-local` 每次检查它是 2.12 |
| MySQL | Homebrew，未固定版本（2026-10-09 为 9.6.0） | 本地实例的数据库；生产是 MariaDB 11.8.9（2026-10-09 SSH 只读），差异见 `docs/local-stack.md` |
| Redis | Homebrew，未固定版本（2026-10-09 为 8.10.2） | 本地实例的对象缓存，配 Redis Object Cache 3.0.0；生产在切换时启用（规格 5、17） |

### 与 framework-choice.md §9 的差异

- 端到端测试用 `playwright test` 而不是 `wp-scripts test-e2e`/`test-playwright`：后者每次运行先下载全部浏览器（`node_modules/@wordpress/scripts/scripts/test-playwright.js`），默认配置还假定 wp-env 与 WordPress 后台登录；#5 的本地站点出现之前，端到端用例驱动的是 Storybook。
- 没有 `automattic/jetpack-autoloader`：它解决的是多个插件发布同一 Composer 包的版本冲突，而三个插件目前没有运行时依赖；出现共享的运行时包时再引入。
- Storybook 用 `@storybook/react-vite` 而不是 WooCommerce Blocks 的 react-webpack5：Vite 已随 Vitest 安装，TSX 不需要另配 Babel。
- Vitest 不装 React 插件：Vite 8 按 tsconfig 的 `jsx: react-jsx` 编译 TSX（`vitest.config.mts`）。

### 包管理器：npm

`plugins/linker-tools` 是仓库里唯一的 npm 包，用 npm 与 `package-lock.json`。依据（framework-choice.md §9.2）：WordPress 的插件脚手架与 Gutenberg 都用 npm；这里没有跨包共享的 JS，pnpm 工作区的好处用不上；`@wordpress/build` 将来的接入方式是 npm workspaces。

`package-lock.json` 里的下载地址写 `registry.npmjs.org`。插件目录的 `.npmrc` 设 `replace-registry-host=always`，npm 一律从当前机器配置的源下载（本机是 npmmirror，CI 是 npmjs），与锁文件里写的主机无关。

### PHP 8.3

本机默认的 `php` 是 Homebrew 的 8.5。安装 8.3：

```sh
brew install php@8.3
```

`php@8.3` 不替换默认的 `php`。justfile 优先用 `/opt/homebrew/opt/php@8.3/bin/php`，没有时用 PATH 上的 `php`（CI 就是这样），`PHP=/path/to/php just check` 可以覆盖；Composer、PHPCS、PHPStan、PHPUnit 都用这个 PHP 运行，不是 8.3 时直接报错。

## 命令

| 命令 | 内容 |
|---|---|
| `just check` | 三个插件与 `tools/local` 的 PHPCS 与 PHPStan；`tools/pull` 的 Ruff（lint + format）与 mypy（strict）；ESLint、`tsc --noEmit`、Prettier；两个服务与 `tools/local`、`tools/migrate` 的 Ruff（lint + format）与 mypy（strict），都覆盖整个项目目录；最后 `build::check` |
| `just test` | 三个插件的 PHPUnit（WP_Mock 严格模式）；Vitest（jsdom）与 Playwright（Chromium 驱动 Storybook）；两个服务与 `tools/local`、`tools/migrate` 的 pytest（tools/local 含用真实 MySQL/Redis/PHP/WP-CLI 建两个实例的端到端测试，CI 上跳过）；`tools/pull` 的 pytest（装入测试在本机建真实 WordPress，CI 没有 MySQL/WP-CLI 时跳过） |
| `just build` | 用 `@wordpress/scripts` 构建 `plugins/linker-tools/build/`，再写 `build/manifest.json` |
| `just build::check` | 源码或产物与 `build/manifest.json` 不一致就失败，并列出是哪些文件 |
| `just up <name>` / `down` / `reset` / `login` / `status` / `serve` / `wp` | 本地 WordPress 实例（WordPress 7.1.3 + WooCommerce 11.2.0 + Redis 对象缓存，插件链接到当前检出）：建立与启动、停止、重建、一次性登录链接、列表、启动 engine 与 Genie、WP-CLI。见 `docs/local-stack.md` |
| `just pull` | 线上只读快照到 `~/de-linker-data/<YYYYMMDD-HHMM>/`；`just pull load …` 等子命令见下文“线上快照” |

每条命令先按锁文件安装所需依赖（`composer.lock`、`package-lock.json`、`uv.lock`），锁文件与清单不一致就失败（`composer validate`、`npm ci`、`uv --locked`），干净克隆上可以直接运行。CI（`.github/workflows/check.yml`）运行 `just check` 与 `just test`，再运行 `just build`，重建出的 `build/` 必须与提交的逐字节相同。

票面写的是 `just build:check`。just 的配方名不能含 `:`（`build:check:` 会解析报错），`::` 是 just 的模块路径分隔符，所以 `build` 是模块 `tools/build.just`：`just build` 运行它的默认配方，`just build::check` 运行检查。npm 脚本仍叫 `build` 与 `build:check`。

### 构建产物

改了 `plugins/linker-tools/src/`（`*.test.*` 与 `*.stories.*` 除外）、`package.json`、`package-lock.json` 或 `webpack.config.js` 之后，运行 `just build` 并连同 `build/` 一起提交。`build/manifest.json` 记录每个源文件与每个产物的 SHA-256（只算 git 会收录的文件，`.DS_Store` 之类被忽略的文件不算）；源码改了没重建、产物被手改，`build::check` 都会失败并列出文件。

### 三条链的样例

- PHP：`linker-commerce` 的 `Abilities\Registrar` 在 `wp_abilities_api_categories_init` 与 `wp_abilities_api_init` 上注册分类 `linker` 与 ability `linker/get-commerce-version`（只读、可走 REST、仅管理员可执行），两处都先检查 `function_exists`；ability 名沿用 `docs/specs/13-genie.md` 的 `linker/` 前缀，一个 ability 一个类。`linker-tools` 的 `Assets` 从 `build/*.asset.php` 读依赖与版本，把每个入口注册为脚本 `linker-tools-<入口>`；只注册不加载，加载由输出挂载点的代码负责。各插件的钩子都列在 `Plugin::register()`。
- JS：每个入口在 DOM 就绪后挂载到 `<div data-linker-app="<入口>">`，文案走 `@wordpress/i18n`（文本域 `linker-tools`）。端到端测试在 Storybook 上跑，不需要 WordPress。
- Python：每个服务有 `GET /health`。

样例不在任何页面上显示：脚本只注册、不入队，页面上也还没有挂载点。

### Storybook 端口

`npm run storybook` 不固定端口（Storybook 10.6 每次取空闲端口）；端到端测试由 `plugins/linker-tools/playwright.config.ts` 自己启动一个实例并固定在 6006（`--exact-port`，`reuseExistingServer: false`），所以开发中的 Storybook 与 `just test` 可以同时运行、互不占用。6006 只是 `storybook init` 的默认值，用作测试实例的已知地址。

### 线上快照（`just pull`）

`tools/pull`（命令 `linker-pull`，规格 `docs/specs/6-live-pull.md`）经 `ssh hostinger-de-linker` 只读地把线上站点拉成快照，放在仓库外的 `~/de-linker-data/<YYYYMMDD-HHMM>/`（`$LINKER_PULL_DATA` 可改）：

| 路径 | 内容 |
|---|---|
| `db.sql.gz` | 数据库：主机上 mysqldump，到达本机时边读边伪名化，原始导出不落盘；写完再扫一遍（无密码哈希、应用密码、密钥、按名存放的凭据、Stripe 对象号；邮箱只剩员工账号、`example.test` 与公司自有域名），不过关就删掉并失败。规则见 `docs/specs/6-live-pull.md` |
| `uploads/` | 媒体库年份目录、WooCommerce 占位图、WindPress 编译的 CSS；`wc-logs/`、`tv-b2b-private/` 留在主机 |
| `plugins/<slug>/` | 四个许可插件，每个本地实例都装 |
| `themes/<slug>/` | 当前主题与父主题 |
| `live/plugins/`、`live/mu-plugins/` | 线上其余插件（含旧自定义代码）与 must-use 插件（主机平台的除外），只在 `--live-code` 时装，用来在本地得到线上站点的副本 |
| `site/` | `options.json`（去掉临时项与密钥的 wp_options）、`plugins.json`、`themes.json`、`sitemaps/`（线上 robots.txt 声明的 sitemap） |
| `manifest.json` | 每个文件的 sha256 与大小、每张表的行数与 sha256；结构见 `tools/pull/manifest.schema.json` |

快照先写进 `.<名字>.partial/`，完整后才改名；没变的文件硬链接到上一份快照与中断留下的 `.partial/`（`rsync --link-dest`）。同一时间只拍一份（数据目录里有锁），各工作树共用 `~/de-linker-data`。旧快照随时可以删：没变的文件是硬链接，只要还有任何一份快照引用着某个数据，删除其中一份不会丢它；保留策略就是「最近的够用就删更早的」。

| 命令 | 内容 |
|---|---|
| `just pull load <实例> <快照\|latest> [--port N] [--live-code]` | 装入本地实例（约定见下） |
| `just pull diff <旧> <新> [--json]` | 两份快照的增量清单：文件增删改、表与文章数的变化 |
| `just pull scan <快照>` | 重新检查快照的 SQL |
| `just pull anonymize <源.sql[.gz]> <目标.sql.gz>` | 伪名化一个 mysqldump 文件并做同样的检查（规则同快照），不过关就删掉结果 |
| `just pull check-urls <快照> --base http://127.0.0.1:<端口> [--sitemap de-sitemap.xml]` | 逐个请求快照里线上 sitemap 的地址，统计状态码 |

`load` 的实例是 #5 的实例：按名字在 linker-local 的登记表里解析（`just up <实例>` 建立并登记；`--port` 覆盖写进数据库的地址），数据库 `linker_<实例>`，`wp-config.php` 必须指向它。装入前先拒绝：实例的 WordPress/WooCommerce 版本与快照不一致（线上会自动更新，被新版迁移过的库没有回退路径）、`db.sql.gz` 不可读或与 manifest 的 sha256 不符、`--live-code` 时实例的插件链接到某个检出。然后清空并导入 `wp_` 表（MariaDB 的 dump 原样导入），把线上地址的三种写法（原样、JSON 转义、URL 编码）换成 `http://127.0.0.1:<端口>`，清空对象缓存，文件全部用 #5 的 `snapshot.install` 装（插件与主题目录替换同名项，uploads 合并进去；`--live-code` 连 `live/` 两棵树也由它装），保留实例原来启用的插件再加上许可插件；`--live-code` 沿用线上的启用列表。Code Snippets 始终不启用。最后对照 manifest 报告已发布商品数、附件数、缺失的附件文件与残留的线上地址，不一致即失败。装入后用户来自快照：结果里列出员工登录名，用 `just login <实例> --user <员工登录名>` 进后台。实例必须把邮件与外发请求留在本机（#5 的隔离 mu-plugin）。
