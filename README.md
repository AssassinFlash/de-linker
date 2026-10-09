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
| `tools/` | just 模块（`build.just`）与三个插件共用的 PHP 工具配置（`php/`：PHPCS 规则、PHPStan 设置、PHPUnit bootstrap） |
| `docs/` | 验收协议、各票规格（`docs/specs/`）与研究证据 |

PHP 类按 PSR-4 一类一文件，测试在各插件的 `tests/php/`。各插件的 `phpcs.xml.dist`、`phpstan.neon.dist`、`tests/php/bootstrap.php` 只写本插件的文件、文本域与前缀，其余引用 `tools/php/`；`phpunit.xml.dist` 每个插件一份，因为 PHPUnit 9.6 的配置文件之间不能共享根元素属性。JS 单测是 `src/` 与 `bin/` 下的 `*.test.ts(x)`，端到端测试在 `plugins/linker-tools/tests/e2e/`。Python 服务是 uv 的 src 布局：规格里写作 `services/genie/retrieval.py` 的模块就是 `services/genie/src/linker_genie/retrieval.py`；包外的脚本（如 `services/genie/index/`）同样受 Ruff 与 mypy 检查（两者都对整个服务目录运行）；测试在各服务的 `tests/`。

## 工具链

| 项 | 版本 | 来源 |
|---|---|---|
| PHP | 8.3 | 生产主机实测 8.3.33（`docs/research/2026-10-09/framework-choice.md` §2）。写在各插件 `composer.json` 的 `config.platform.php`（PHPStan 从这里读）与 `tools/php/phpcs.xml` 的 `testVersion` |
| WordPress / WooCommerce | 7.1 / 11.1 | 主机实测 7.1.3 / 11.1.0（§2）：插件头 `Requires at least`、`minimum_wp_version`、`php-stubs/wordpress-stubs ~7.1.0`、`php-stubs/woocommerce-stubs ~11.1.0` |
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
| `just check` | 三个插件的 PHPCS 与 PHPStan；ESLint、`tsc --noEmit`、Prettier；两个服务的 Ruff（lint + format）与 mypy（strict），都覆盖整个服务目录；最后 `build::check` |
| `just test` | 三个插件的 PHPUnit（WP_Mock 严格模式）；Vitest（jsdom）与 Playwright（Chromium 驱动 Storybook）；两个服务的 pytest |
| `just build` | 用 `@wordpress/scripts` 构建 `plugins/linker-tools/build/`，再写 `build/manifest.json` |
| `just build::check` | 源码或产物与 `build/manifest.json` 不一致就失败，并列出是哪些文件 |

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
