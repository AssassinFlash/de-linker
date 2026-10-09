# 框架选型：只按「复刻」与「适用」两条判（2026-10-09）

适用范围：de-linker 重建中的四层——三个前端工具（Advisor 抽屉＋四个入口、Planner、Site Detail）、插件构建管线、PHP 插件结构、Python 助手服务。
判据（业主指定，只有两条）：
- **复刻**：我们要复刻的产品实际用什么，我们所在的平台（WordPress 7.1 + WooCommerce 11.1）自己用什么。
- **适用**：放进我们的约束里能不能用、好不好用。约束包括：共享主机，主机上没有 Node；构建在 Mac 上完成；EN/DE；VPS 只有 1 vCPU；由 AI 执行者落地；团队里没有前端专家。

---

## 0. 结论先行

| 层 | 决定 | 相对 020 决议（"拍板版"）的变化 |
|---|---|---|
| 前端三工具 | **React + TypeScript**，React 用 WordPress 自带的那份（`react`/`react-dom`/`react-jsx-runtime` 作为 externals，目前是 18.3.1）。代码写成 React 19 兼容。每个工具挂在页面上的一个挂载点；入口由 PHP 在服务端渲染。Advisor 应用在用户第一次交互时才加载，不随页面加载 | 框架不变；改为用平台自带的 React，不再自己打包一份 |
| 插件构建 | **`@wordpress/scripts`**（webpack＋dependency extraction，生成 `.asset.php`；单元测试默认用 Vitest，端到端用 Playwright）。一个插件一个 npm 包，`src/{advisor,planner,site-detail,shared}` 多入口 | **Vite → `@wordpress/scripts`**；**pnpm workspace → 每个插件一个 npm 包**；自建 `packages/i18n` → `@wordpress/i18n` + `wp i18n make-json` |
| PHP 结构 | **Composer + PSR-4 命名空间**（与 WooCommerce core、create-woo-extension 模板相同）。`vendor/` 随插件发布；**PHPUnit 9.6** 配 WP 测试套件和 Brain Monkey；**PHPStan 2**（WordPress 与 WooCommerce stubs，新代码 level 8，存量代码用 baseline）；PHPCS 用 WPCS 3、woocommerce-sniffs 和 PHPCompatibilityWP；Composer `platform.php = 8.3` | **PHPUnit 11 → 9.6**；PHPStan 级别对齐 Woo；补上 PHP 平台锁定；更正事实："主机没有 Composer"是错的 |
| Python 服务 | **FastAPI + Pydantic AI 维持**。证据没有推翻原选择 | 无 |

每层最强的三条证据见第 9 节。

---

## 1. 方法与证据来源

- **外部事实一律经 Apify 获取**（REST API，token 取自 `apify.env`，没有落盘或打印），没有用任何非 Apify 的搜索。用到的 actor 和 run：
  | 用途 | actor | run / dataset |
  |---|---|---|
  | npm / GitHub API / PyPI / bundlephobia / GitHub raw 文件 | `apify/playwright-scraper` | `lfvARZpX38oTHSvWK` / `o1cqeePzHhQbjIPh8`；`o3JwXeXEILTCakZPV` / `yIoOmkksDc5rwCxq9`；`F5xZhBJQOayxwvGOo` / `pmZz59zCNdjS1g9yX` |
  | 前端框架运行时检测（31 + 7 + 9 个站点） | `apify/playwright-scraper` | `9GcmTQq8eZJymZHRr` / `lt7ZmMbqidPWEVAih`；`wlYAkBlhEt7gOqOTX` / `rGhZF9vFRkTcc6AdR`；`EkgsMjYa7b4qExOeW` / `uBpRbic4d7yT599Wt` |
  | 检索发现（57 个查询，换了中、英、德关键词） | `apify/google-search-scraper` | `dhEb13qXLsX5y0iww` / `OgeLv9gp2ffXcjMs2`；`9Ptr3FOgzKseFmVhD` / `aD0ALj5zbIufeblMh` |
  | 文档与博客全文（68 页） | `apify/website-content-crawler` | `DmAfxYvSr1nbktg1I` / `hcUkJpID3NRT3WkPV`；`io6HOtRsuYaqlgK5V` / `U5PvkiUYIFMznNy0i`；`bWyHvbWWcDfA2tWLd` / `wBqhjGUgkp3N1h6vM` |
  所有外部数据都取于 **2026-10-09**。npm 月下载量的统计区间是 2026-09-08..2026-10-07。
- **框架检测方法**：在页面脚本执行前注入一个 React DevTools hook。React 初始化时会把渲染器的包名和版本报给这个 hook，所以能拿到 `react-dom@x.y.z` 的确切版本。其他框架用 DOM 与全局指纹识别：Vue 看 `__vue_app__.version`，Angular 看 `ng-version`，Lit 看 `litElementVersions`，Next 看 `__NEXT_DATA__`，Remix 看 `__remixContext`，React Router 看 `__reactRouterContext`，Shopware 看 `PluginManager`，WordPress 看 `meta generator`。有一个检测 Preact 的启发式信号不够可靠，**全文不采用**。第一次 run `geZE7KY9DkXgZGtIZ` 的 pageFunction 有 bug，已中止并作废。
- **我们自己的系统**：通过 SSH 和 WP-CLI 只读实测生产主机，并读取本机工具链版本。这些是直接读取，不属于外部检索。
- **仓库**：读了 020 / 022 / 014 / 006 / 010 决议，以及 `docs/research/2026-10-09-*.md`。

---

## 2. 我们所在的平台：实测（2026-10-09，SSH + WP-CLI，只读）

| 项 | 实测值 |
|---|---|
| WordPress / WooCommerce | **7.1.3 / 11.1.0** |
| 主机 PHP / Composer / Node | PHP **8.3.33**；**Composer 2.9.8（有）**；`node`、`npm` 均不存在；WP-CLI 2.12.0 |
| WP 自带 React | `react` 18.3.1.1、`react-dom` 18.3.1.1、`react-jsx-runtime` 18.3.1；`wp-element` 依赖 react 与 react-dom；另注册了 `wp-react-i18n` |
| Woo 前台的 React 应用 | `wc-blocks-checkout`（Checkout 块）依赖 `react`、`react-dom`、`react-jsx-runtime`、`wp-element` 等 |
| Interactivity API | 共注册 105 个 script module，其中有 `@wordpress/interactivity` 和 `-router`；**`woocommerce/*` 的 iAPI 模块（不含 style）有 42 个**：product-button、mini-cart、product-collection、product-filters、add-to-cart-with-options、product-gallery、wishlist 等 |
| 站点前台现状 | 首页、Planner、Cart 页都**没有加载 React**。加载的是 Woo 经典的 jQuery 脚本，加上我们自己的 bundle（`linker-assistant.bundle.js`、`tool-frame.bundle.js`、`quote-configurator.bundle.js`）。Cart 页另外加载了 `wp-includes/js/dist/i18n.min.js` |
| 主题与编辑方式 | 启用的插件有 **classic-editor**、**LiveCanvas 4.9.3**、**WindPress 3.2.88**（Tailwind）。主题是 `picostrap5-child-base`（Bootstrap 5）。也就是说，页面内容不走块编辑器 |
| Woo 的 PHP 发布形态 | `woocommerce/vendor/` 随插件一起发布，内含 Composer `autoload.php`、`jetpack-autoloader` 和各依赖包；`woocommerce/src/` 是 PSR-4 命名空间目录（Abilities、Admin、Api、Blocks……） |
| 本机 | Node 22.23.2、pnpm 10.32.1、npm 10.9.8、**PHP 8.5.5（比主机高两个小版本）**、Composer 2.9.7、WP-CLI、uv 0.10.11；**没有 Docker** |

两条推论：一是主机上能跑 Composer，但我们的部署是逐文件、按字节核验的，所以 `vendor/` 应该像 Woo 一样作为构建产物随插件发布；二是本机没有 Docker，`wp-env`（默认依赖 Docker）不能直接用。

---

## 3. WordPress 与 WooCommerce 自己用什么（问题 1）

### 3.1 WordPress / Gutenberg
- Gutenberg trunk（`package.json` 版本 24.2.0-rc.1）：**npm workspaces**，构建脚本是 `npm run --workspace @wordpress/build-scripts build:all`，端到端测试用 Playwright ^1.63。来源：https://raw.githubusercontent.com/WordPress/gutenberg/trunk/package.json （2026-10-09）
- WordPress core trunk（7.2.0）的 `package.json` 写的是 `react: 18.3.1`。`composer.json` 的开发依赖里有 **PHPStan 2.3.0**、WPCS ~3.4.1、PHPCompatibilityWP ~2.1.3，以及 `yoast/phpunit-polyfills ^1.1.0`（对应 PHPUnit ≤ 9）。来源：https://raw.githubusercontent.com/WordPress/wordpress-develop/trunk/package.json 、…/composer.json
- React 19 暂缓：2026-05-27 宣布升级，06-05 回退，**07-24 宣布推迟到 7.1 之后**。官方点名的头号故障模式是："Bundling the `react/jsx-runtime` code directly in the plugin … instead of using the externalized `react-jsx-runtime` script provided by WordPress itself."。来源：https://make.wordpress.org/core/2026/07/24/react-19-punted-beyond-wordpress-7-1-experiment-in-gutenberg/ ；7.1 Field Guide 也写明 React 19 推迟：https://make.wordpress.org/core/2026/08/05/wordpress-7-1-field-guide/
- `@wordpress/element` 9.0.0 的 peer 依赖是 `react ^18 || ^19`，并导出 `createRoot`。"Why React"一节说明 WordPress 把 React 作为 UI 层的基础。来源：packages/element 的 package.json；https://developer.wordpress.org/block-editor/reference-guides/packages/packages-element/
- `@wordpress/dataviews`：提供 `DataViews`、`DataViewsPicker`、`DataForm`，**三者都是 React 组件**。7.1 继续完善 DataViews/DataForm，Abilities API 增加了"client-compatible JSON Schema preparation"。来源：https://developer.wordpress.org/block-editor/reference-guides/packages/packages-dataviews/ ；7.1 Field Guide

### 3.2 Interactivity API（iAPI，WP 6.5+）
- 底层是 **Preact + Preact Signals**，指令写在服务端渲染出的 HTML 上。运行时约 10 KB（官方说法）；`@wordpress/interactivity` 7.0.0 按 bundlephobia 计 min+gzip 为 17.9 KB。
- 为什么不用 React：React 和其他框架"none of them (including React) are PHP-friendly or compatible with WordPress hooks or internationalization"。**编辑器作为"fully interactive application"仍然用 React**，没有改用 Preact 的计划。iAPI **可以脱离块使用**，见 `wp_interactivity_process_directives`。Alpine.js 被明确比较过并放弃。来源：https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/iapi-faq/ （2026-10-09）
- WooCommerce 已把店面交互迁到 iAPI：**10.4 版"replaces the legacy React-based Mini Cart … improved performance, smaller JavaScript bundles"**（https://developer.woocommerce.com/2025/12/10/woocommerce-10-4-the-interactivity-api-mini-cart-goes-live/ ）。性能路线图里写 iAPI Mini-Cart "removes the React dependency across much of your store's frontend"（https://developer.woocommerce.com/2025/10/01/improving-woocommerce-performance-at-scale/ ）。旧的 React 版 mini-cart 前端模块已删除：https://github.com/woocommerce/woocommerce/issues/61640 。我们主机上实测到 42 个 `woocommerce/*` iAPI 模块（§2），与此一致。

### 3.3 WooCommerce Blocks 与 Admin（monorepo trunk）
- monorepo 用 **pnpm@10.33.0**，Node 24.15，有 `catalogs`（与最低支持 WP 版本绑定的 `@wordpress/*` 版本表）。构建工具 catalog 里是 webpack 5.97 加 `@babel/preset-typescript`/`preset-react`。来源：https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/pnpm-workspace.yaml 、…/package.json
- `@woocommerce/block-library`（Blocks）：**React 18.3.x + TypeScript 5.7 + webpack**。依赖里有 `@wordpress/scripts` 32.6.0、`@wordpress/dependency-extraction-webpack-plugin`（另有 Woo 自己的 dependency-extraction 插件）；同时有 **Preact + `@wordpress/interactivity`**，用 `WP_EXPERIMENTAL_MODULES=true` 构建 script modules；**Storybook 10.5.10（react-webpack5）**、Jest 29 + Testing Library React、Playwright 1.63。来源：…/plugins/woocommerce/client/blocks/package.json
- `@woocommerce/admin-library`（Admin）：React 18.3 + TS 5.7 + webpack，依赖 `@wordpress/dataviews`、**zod ^3.22**、xstate、react-router-dom、ts-jest。来源：…/client/admin/package.json
- 小结：Woo 在**店面的轻交互**（mini-cart 抽屉、商品集合、筛选、加购）上用 iAPI；**表单很重的应用**（Checkout）和**后台**用 React + TS + webpack。

### 3.4 第三方插件怎样把 React 应用嵌进页面（官方做法）
WordPress Developer Blog 2024-03 给出的标准链路如下（https://developer.wordpress.org/news/2024/03/how-to-use-wordpress-react-components-for-plugin-pages/ ）：
1. `wp-scripts build` 生成 `build/index.js` 和 `build/index.asset.php`。
2. PHP 读取 `index.asset.php` 里的 `dependencies` 和 `version`，调用 `wp_enqueue_script`。
3. JS 里用 `@wordpress/element` 的 `createRoot(el).render(<App/>)`。

`.asset.php` 由 dependency-extraction 插件生成，内容是"list of WordPress script dependencies … also contains the unique version hash calculated based on the content of the entry point's files"。它把 `react`/`react-dom` 外部化到 WP 自带的那份（https://developer.wordpress.org/block-editor/reference-guides/packages/packages-dependency-extraction-webpack-plugin/ ）。
JS 的国际化走 `@wordpress/i18n` 的 `__()`，配合 `wp_set_script_translations()`，再用 `wp i18n make-pot` / `make-json` 生成 `${domain}-${locale}-${md5}.json`（https://developer.wordpress.org/block-editor/how-to-guides/internationalization/ ）。

### 3.5 `@wordpress/scripts` 与 `@wordpress/build`
- `@wordpress/scripts` **36.1.0**（Node ^22.22.2 || ^24.15 || >=26）：底层是 webpack。入口文件支持 `.ts/.tsx`（经 `babel-loader` 转译）。**`test-unit-js` 现在默认运行 Vitest**（需要 Vitest 5 + Vite 8），Jest 只保留一个维护用的适配器，"New testing features target Vitest"。`test-e2e` 用 Playwright。来源：https://raw.githubusercontent.com/WordPress/gutenberg/trunk/packages/scripts/README.md （2026-10-09）；npm 月下载 583,143。
- `@wordpress/build`（0.25.0，npm 月下载 249,855）：**用 esbuild 替代 webpack 和 Babel**，自动生成 PHP 注册代码（`build/build.php`）。Gutenberg 自己的 100 多个包已经用它构建。但官方原话是："**not ready for every use case yet**"；在独立插件里使用目前需要 npm workspaces、把 `@wordpress/*` 实际装进来，还隐含依赖 `@babel/core`，"None of this is documented"；"**Everyone else: stay on `@wordpress/scripts`**"。路线是让 wp-scripts 内部换用 wp-build 作为引擎，`wp-scripts build continues to work`。来源：https://developer.wordpress.org/news/2026/04/wordpress-build-the-next-generation-of-wordpress-plugin-build-tooling/ （2026-04-02）
- 一线做法：WooCommerce 开发者布道师 Brian Coords 在 2026-02-09 写道，他的 Woo 扩展是 React 后台页、DataViews、"Dynamic blocks with the Interactivity API are my default when I need frontend content"，构建用 **WordPress Scripts** 加 dependency extraction。他认为 wp-build "a bit too far into the future to reliably use right now"，还说 AI 写"generic React + Tailwind"很顺，写 WP 专用的 UI API 就吃力。来源：https://www.briancoords.com/my-wp-woo-plugin-scaffolding-in-2026/

### 3.6 Vite 在 WP 生态里的位置
- **Roots Sage 11**（2025-03，主题脚手架，13.3k★）从 Bud 换到了 Vite，目前是 `vite ^8`，加 `laravel-vite-plugin` 和 `@roots/vite-plugin`。它的 JS 翻译仍然用 `wp i18n make-pot/make-json`。来源：https://roots.io/sage-v11-and-acorn-v5-released/ ；https://raw.githubusercontent.com/roots/sage/main/package.json
- `kucrut/vite-for-wp`（插件和主题用）：327★，**最后一次推送在 2025-06-26**，npm 月下载 24,882。要把 react 外部化给 WP，需要再加 `rollup-plugin-external-globals`、`vite-plugin-external`，并且手动在 PHP 里声明依赖；README 自己写着"doesn't provide HMR support for building editor blocks"。`@roots/vite-plugin` 月下载 41,938，面向主题。`@roots/bud` 最后一次推送是 2025-02（已被 Sage 弃用）。
- 结论：**Vite 在 WP 生态里主要用于主题（Sage）；WP 和 Woo 官方的插件链路里没有 Vite。** 有一个例外值得注意：wp-scripts 的单元测试器现在用的是 Vitest，而 Vitest 依赖 Vite 8。所以 Vite 会作为测试引擎被装进来，但不承担打包。

### 3.7 问题 1 的回答
- **嵌入 WordPress 页面的应用，标准做法**：应用型 UI（编辑器、后台、Checkout 这类重表单）用 **React，并且用 WP 自带的 React**（`wp-element` 和外部化的 `react-*` handle）；附着在服务端渲染内容上的前台交互，用 **Interactivity API**（WooCommerce 的店面已经全面转向它）。
- **插件构建管线，标准做法**：**`@wordpress/scripts`**（webpack + dependency extraction + `.asset.php`，测试是 Vitest + Playwright）。esbuild 内核的 `@wordpress/build` 是官方宣布的下一代，会在 wp-scripts 内部替换掉 webpack。

---

## 4. 被复刻的产品用什么（问题 2）

### 4.1 运行时实测（2026-10-09，方法见 §1）
| 站点 | 实测结果 | 备注 |
|---|---|---|
| shopify.com | **React 18.3.1** + React Router（ESM chunk） | Shopify 官网 |
| hydrogen.shop | **React 18.3.1** + Remix | Shopify 的 headless 演示店 |
| shop.app（重定向到 shop.com） | **React 19.2.8** + React Router | Shopify 面向消费者的购物 app 网页版 |
| admin.shopify.com | 被 Cloudflare 挑战页拦住，无法测 | 用 §4.2 的一手工程博客代替 |
| accio.com | **React 19.2.5**，ESM 资源（`s.alicdn.com/@g/accio-phoenix/…/assets/index.js`） | 阿里 Accio |
| alibaba.com | **React 18.2.0**（alicdn 上的 UMD），webpack | |
| taobao.com / tmall.com | **React 18.2.0 + 18.3.1**，webpack（`pegasus-project-tbhome-2024`） | |
| meituan.com | **Next.js（pages）+ React 18.2.0** | dianping、i.meituan 被反爬验证页拦住 |
| amazon.com（首页） | 服务端渲染的 AUI + "AmazonUIjQuery"；**Lit 4.2.2 Web Components**（`AmazonHomepageBuzzWebComponents`） | 商品页返回反爬中间页；Rufus 面板匿名用户看不到，**无法测** |
| woocommerce.com | WordPress 7.1.3，React 18.3.1（直接用 WP 自带的那份），页面上有 iAPI 指令 | 平台方自己的站 |
| **PV 工具** | | |
| SMA Sunny Design Web | **Angular 19.2.9 + AngularJS 1.8.0** 混合（含 `roofplanner` chunk） | 厂商的设计 SaaS |
| Fronius Solar.creator | **Angular 14.3.0** + Lit 4.2.1 编辑器组件 + jQuery | 厂商的设计 SaaS |
| EcoFlow Solarrechner（energy.ecoflow.com/de/design） | **Next.js + React 18.2.0 + Google Maps** | 公开的 PV 测算工具，带地图 |
| sun.store | **Nuxt + Vue 3.5.39** | 光伏 B2B 交易平台 |
| Memodo、Krannich 网店 | **Shopware 6**（服务端渲染 + JS PluginManager） | Krannich 的 Auslegungstools 页只是厂商工具的链接汇总 |
| BayWa r.e. 网店 | OXID / TYPO3 + jQuery，服务端渲染 | Solar-Planit 的营销页跑在 WordPress 7.0.7 + Elementor 上；应用本体在 `solar-planit.de/solarplanit/…` |
| IBC Solar 目录 | jQuery，外加一个 **Vite 构建**的 `parts-list-generator` 模块（`modulepreload-polyfill`） | 这个模块用什么框架无法判定 |
| EWS（pv.de） | jQuery 4.0.0；`/leistungen/anlagenplanung/` 会跳到 Partner-Login | QuickCalc / QuickPlan 要经销商登录，**无法测** |
| Huawei SmartDesign 2.0（eu5.smartdesign.huawei.com） | **React 18.3.1**，另加 twaver canvas 库 | 厂商的设计 SaaS（Krannich 工具页上有链接） |
| GoodWe Designer | **Vue 3.5.26 + Konva**（canvas） | 厂商的设计 SaaS |
| SolaX Design | **Vue 3.5.43** | 厂商的设计 SaaS |
| Renusol PV-Configurator（支架） | **Angular 16.1.3** + Material | 厂商的配置器 |
| SigenStack Calculator | Vue 2 + Lit + jQuery（营销页上的计算器） | |
| Solar-Planit 应用（solar-planit.de/solarplanit/html/home） | **jQuery 1.8.3**，服务端渲染（Java `*.do` 路由） | BayWa 的设计工具本体，属于老一代架构 |
| Solar-Log 配置器 | jQuery 3.6.0 | |
| SolarEdge Designer | designer.solaredge.com 和 solaredge.com 上的工具页**都超时，无法测** | |

### 4.2 一手文档、工程博客与招聘信息
- **Shopify Admin（Sidekick 所在的宿主）**：已在 React/**Remix** 上重建（SPA mode），**Vite** 是构建系统，代码是 **3,184,248 行 TypeScript**，route manifest 在构建期被 Search 和 Sidekick 读取。来源：https://shopify.engineering/remixing-admin （2025-06-30）
- **Shopify Polaris**：React 实现已归档："On October 1, 2025, we released our Polaris Web Components … technology-agnostic foundation"（https://github.com/Shopify/polaris ，archived=true）。在 UI 扩展这一侧，"UI extensions are scaffolded with **Preact** by default"（https://shopify.dev/docs/api/polaris/using-polaris-web-components ）。Checkout Blocks 团队把 React 迁到 Preact + Polaris WC + TS，传输体积下降 40–85%，结账扩展有 **64 KB gzip 硬上限**，迁移"heavily AI-assisted"（https://shopify.engineering/upgrading-checkout-blocks-app-to-polaris-web-components ，2026-07-16）。
- **Shopify 主题（店面）**：Horizon 的原则是 "**Server-rendered** … Async and on-demand rendering … sparingly as a progressive enhancement"，"Web-native in its purest form"。来源：https://raw.githubusercontent.com/Shopify/horizon/main/README.md
- **Shopify Sidekick 的服务端**：基于 Anthropic 所说的 "agentic loop"；工具数在 0–20 个时边界清晰，20–50 个开始变得模糊；用 JIT instructions 和 LLM-judge 做评测。文中没有提到任何编排框架。来源：https://shopify.engineering/building-production-ready-agentic-systems （2025-08-26）
- **Amazon Rufus**：招聘信息（Rufus SDE II、Rufus SDET；ACE SDE III 写的是"Java, Python, and TypeScript"）**都没有公开前端框架**（https://amazon.jobs/en/jobs/10502024 、…/10463819 、…/10509601 ）。所以 **Rufus 的 UI 技术栈不公开**；能测到的只有亚马逊零售首页（服务端渲染的 AUI 加 Lit）。
- **美团**：到店技术团队说"整体的技术栈分 **Vue 和 React** 两部分"，开发期用 Vite，存量项目构建用 Webpack，增量项目整体走 Vite（https://tech.meituan.com/2023/08/03/meituan-Rome-Practice.html ）。2026 年的招聘要求是"熟练使用主流框架(React/Vue)"（zhaopin.meituan.com 职位，检索摘要，2026-02）。
- **阿里**：`alibaba/ice`"基于 React 的渐进式应用框架"，18.6k★，2026-04 仍在推送；`alibaba/rax` 最后一次推送是 2023-03（已停滞）。BOSS 直聘上有"阿里Accio-Agent 前端开发"岗位（检索摘要）。

### 4.3 小结
- **AI 购物助手和电商平台的网页端**：凡是能测到的都是 **React**，包括 Shopify Admin/Sidekick、Shop、Accio、淘宝、天猫、Alibaba.com、美团官网。React 18.2–19.2 并存，新产品（Accio、Shop）已经在 React 19 上。
- **店面这一层**（Amazon 首页、Shopify 主题、Woo mini-cart、Shopware/OXID 网店）共同的做法是"**服务端渲染 + 轻量增强**"，有的用 Lit/Web Components，有的用 iAPI，有的用 jQuery。**体积受限的嵌入式 UI**，Shopify 选的是 **Preact**。
- **PV 设计工具没有统一的框架**（共测到 11 个）：**Angular** 3 个（SMA Sunny Design、Fronius Solar.creator、Renusol），**Vue** 3 个（GoodWe Designer + Konva、SolaX Design、SigenStack 用的是 Vue 2），**React** 2 个（Huawei SmartDesign、EcoFlow Solarrechner + Google Maps），**老一代 jQuery / 服务端渲染** 3 个（BayWa Solar-Planit 应用本体、Solar-Log、EWS 外壳）。批发商网店是 Shopware/OXID，服务端渲染；B2B 交易平台 sun.store 用 Vue/Nuxt。这些都是厂商**独立部署**的 SaaS，没有一个嵌在 WordPress 里。所以 PV 工具这一行**选不出唯一的框架**，选型的复刻分主要来自"平台"和"AI 购物助手 / 电商网页端"这两组证据。

---

## 5. 候选方案逐项（问题 3）

数据：npm = 近 30 天下载（2026-09-08..10-07）；★ = GitHub stars（2026-10-09）；体积 = bundlephobia min+gzip（2026-10-09）；SO = Stack Overflow 2025 "web frameworks"（全部受访者，n=23,678）。

| 方案 | WP 嵌入 | 表单与校验 | 地图 / canvas（maplibre + terra-draw） | i18n | 测试 | TS | 执行者熟悉度 | 运行时体积 |
|---|---|---|---|---|---|---|---|---|
| **React** | 官方链路：`wp-element`、外部化的 `react-*`、`.asset.php`、`createRoot`（§3.4）；WP 自带 18.3.1 | react-hook-form 251M/月 + `@hookform/resolvers` 209M/月（支持 zod、**ajv/JSON Schema**、standard schema）；rjsf 5.1M；TanStack Form 14.4M | `react-map-gl/maplibre` 9.8M + `@vis.gl/react-maplibre` 6.75M；terra-draw 作者给了 React 用法（#172） | `@wordpress/i18n` + `@wordpress/react-i18n` + make-json；i18next 99M | Vitest（wp-scripts 默认）、Testing Library React 274M、Playwright 290M、Storybook React 93M | `@types/react`，Woo 用 TS 5.7 | npm 791M/月（年 5.70B），251k★，**SO 44.7%**；v0、Lovable 默认生成 React | react-dom 42.6 KB + react 2.6 KB（18.3.1）；与 WP 共用一份时可缓存 |
| Preact（+compat） | WP 不提供 Preact 作为应用运行时（只在 iAPI 内部用）；只能自带一份 | 通过 compat 可用 React 生态，但有兼容风险 | 同左 | 可调用 `@wordpress/i18n` | Testing Library Preact、Vitest | 有 | 154M/月（大部分是传递依赖），38.9k★ | **4.8 KB** |
| Vue 3 | 只能自带运行时，手工 enqueue（vite-for-wp 有 Vue 示例） | vee-validate 5.1M、FormKit 0.59M | vue-maplibre-gl **3.2k/月** | vue-i18n 16.5M；`.vue` 源文件 make-pot 解析不了，只能扫构建产物 | Testing Library Vue 3.7M、Storybook vue3 5.0M | 原生 TS | 72M/月，54.6k★（core），SO 17.6% | 44.1 KB（完整包入口） |
| Svelte 5 | 自带运行时；SvelteKit 是整站框架，不适合嵌入 | superforms 1.17M（偏 SvelteKit）、felte 115k | svelte-maplibre 115k、svelte-maplibre-gl 41k | svelte-i18n 0.49M、paraglide 2.8M | Testing Library Svelte 3.9M | 有 | 26.5M/月，88.4k★，SO 7.2% | 10.7 KB（运行时，组件代码另计） |
| SolidJS | 自带运行时 | modular-forms 127k、solid-form 223k | 无主流封装 | @solid-primitives/i18n 0.94M | Testing Library Solid 1.1M | 有 | 24.5M/月，36.1k★；State of JS：约 10% 使用，满意度连续五年第一 | 8.3 KB |
| Lit / Web Components | 自定义元素可挂在任意位置；Shadow DOM 能隔离站点的 Bootstrap 和 Tailwind | 基本要自己写（TanStack lit-form 9k） | 命令式接入，没问题 | @lit/localize 0.44M | open-wc 0.54M、Storybook WC 1.0M | 原生 TS | 31.9M/月（多为传递依赖），21.8k★ | 6.0 KB |
| Interactivity API | **WP core 自带**；PHP 服务端渲染加指令；可脱离块使用 | 没有表单库，状态放在 store 里 | 没有封装，要在 store 回调里自己写命令式代码 | 服务端直接调 `__()`（FAQ） | 主要靠端到端测试；store 有 TS 文档 | 有 | 341k/月；Brian Coords：AI 写 WP 专用 UI 吃力 | 约 10 KB（官方），17.9 KB（bundlephobia） |
| htmx + PHP 片段 | 由 PHP 输出 HTML 片段 | 服务端校验 | 地图编辑器不合适 | PHP gettext | 只能端到端测试 | — | 1.17M/月，49.5k★ | 17.9 KB |
| Alpine.js | 自带；iAPI FAQ 比较后明确放弃了它 | 要自己写 | 不合适 | 自己接 | 弱 | 弱 | 3.1M/月，32.0k★ | 15.6 KB |
| Headless（Next.js / React Router 接 Store API） | **需要 Node 运行时**（主机没有，VPS 只有 1 vCPU），等于另起一个前端，违背"同域名一次性更新原站"（Q13） | React 生态 | React 生态 | 要另起一套 i18n，与 WP gettext 分开 | 齐全 | 齐全 | next 267M/月，SO 20.8% | 整站都要加载 JS |
| （补充）Angular | 自带运行时；WP 生态里没有先例 | Angular Forms | 命令式 | 自有 i18n 体系 | 内置 | 原生 | SO 18.2% | 重 |

三类应用的特殊需求，逐条对应：
- **Advisor**（流式回复、卡片、追问、执行动作）：现成的开源组件几乎都是 React。`@assistant-ui/react` 月下载 8.15M、12.5k★，自带 streaming、tool UI（把工具调用渲染成组件），可以接自定义后端 runtime（`useDataStreamRuntime` 或 custom runtime），见 https://raw.githubusercontent.com/assistant-ui/assistant-ui/main/README.md 。AI SDK UI 的 React 版月下载 38.4M，Vue 版 6.9M，Svelte 版 2.4M。框架无关的 `deep-chat` 是 100k/月。
- **Planner**（表单为主）：WP 和 Woo 里最接近的先例是 Checkout 块，用的是 React（§2、§3.3）。ability 本身已经带 JSON Schema（7.1 增强了"client-compatible JSON Schema"）。用 `@hookform/resolvers` 的 ajv resolver 就可以直接拿 ability 的 schema 做前端校验，**规则只有一份**，不需要再手写一份 zod，符合 Law 4。
- **Site Detail**（地图 / canvas）：maplibre-gl（287 KB gz）和 terra-draw（45.7 KB gz）都是与框架无关的命令式库；terra-draw 内置 MapLibre v4/5、Mapbox、Google、Leaflet、OL、ArcGIS 的适配器（README）。不论选哪个框架，地图都是"组件里持有一个命令式实例"。React 有现成的 `react-map-gl/maplibre`，并已支持 MapLibre v6。在这一页上，框架运行时的体积和地图库相比可以忽略。

---

## 6. PHP 插件结构（问题 4）

| 来源 | 结构 | 测试与质量工具 |
|---|---|---|
| **WooCommerce core**（trunk composer.json / phpstan.neon / phpcs.xml） | `psr-4: Automattic\WooCommerce\ → src/`；legacy `includes/` 用 classmap；`config.platform.php = 7.4`；**`vendor/` 随插件发布**（我们主机上实测） | **PHPUnit ^9.6**、mockery、yoast/phpunit-polyfills ^2.0；**PHPStan ^2.1 level 8 + baseline + szepeviktor/phpstan-wordpress ^2.0 + wordpress-stubs ^6.8**（`phpVersion: 70400`）；PHPCS 用 WPCS，另有 woocommerce-sniffs |
| **create-woo-extension**（Woo 官方扩展脚手架，`npx @wordpress/create-block -t @woocommerce/create-woo-extension`） | composer.json：`psr-4: {Slug}\ → includes/`，依赖 `automattic/jetpack-autoloader`；主文件 `require vendor/autoload_packages.php`，`use {Slug}\Admin\Setup`；JS 用 **wp-scripts**，webpack.config 继承 wp-scripts 并换成 Woo 的 dependency extraction；带 `.wp-env.json`；`tests/Test.php` | `phpunit/phpunit ^9.0`；"PHP and Javascript unit testing, linting" |
| Woo 编码规范文档 | 加前缀，`function_exists` | "WooCommerce Sniffs and WordPress Code Standards"；要求单元测试和 E2E |
| WP 插件手册 | "Prefix Everything"，或者用 `namespace`（两者都认可） | — |
| WordPress Plugin Boilerplate（DevinVinson，7.8k★） | 类名加前缀、Loader 类；README 写明**有意去掉了 Composer**；**最后一次推送 2024-07-12** | 无 |
| WP core 测试手册 | — | 文档链接全部指向 **PHPUnit 9.6**；推荐 Docker；不用 Docker 时需要本机 PHP + MySQL |
| WP_Mock（10up） | — | **`require: phpunit/phpunit ^9.6`**（硬性要求） |
| Brain Monkey | — | 开发依赖 `phpunit ^8.5.52 || ^9.6.34`；README 写"8.5 or higher" |
| PHPUnit 官方支持表 | — | PHPUnit 9 的 bugfix 支持 2024-02 结束（之后进入 life support，即持续适配新版 PHP）；**PHPUnit 11 的 bugfix 支持 2026-02-06 已结束**；12 要求 PHP ≥ 8.3，支持到 2027-02 |
| wp-env | — | 默认依赖 **Docker**；Playground runtime 还是实验性的 |

结论：Composer + PSR-4 + 命名空间类正是 Woo 自己用的、也是 Woo 推给扩展开发者的结构。PHPUnit 版本应跟随 WP、Woo、WP_Mock、Brain Monkey 共同使用的 **9.6**，不是 11。本机没有 Docker，集成测试按 WP 手册的非 Docker 流程跑：`wp scaffold plugin-tests` 加本机已有的 MySQL（本地 QA 站点已有 MySQL）。

---

## 7. Python 服务（问题 5，只在证据推翻时才改）

| 证据 | 数据 |
|---|---|
| 被复刻的产品 | Sidekick 是自建的 agentic loop，提到了工具数纪律（0–20 个最清晰）和 JIT instructions，没有提到编排框架（§4.2）。Rufus 不公开。**我们只有 6–10 个工具，正好落在 Sidekick 说的"清晰区间"。** |
| Pydantic AI | 2.54.0，"Production/Stable"，`requires_python >=3.10`（VPS 是 3.12）；PyPI 月下载 5.38M，加上 `pydantic-ai-slim` 23.9M；20.5k★。早先的研究（`docs/research/2026-10-09-reusable-commerce-agent-components.md`）确认它原生支持 `deepseek:` 和 Anthropic，提供 `output_validator`/`ModelRetry` |
| 备选 | LangGraph 月下载 44.8M、42.9k★，定位是"durable execution"图编排，对单轮导购来说太重；OpenAI Agents SDK 12.4M，接 Anthropic 要经 LiteLLM；Agno 1.78M；直接用 Anthropic SDK 写循环（anthropic 150M/月）只适用于 Claude |
| FastAPI | PyPI 月下载 381.6M，102.9k★，0.143.0；**SO 2025 使用率 14.8%，比上年 +5 个百分点，问卷原话 "one of the most significant shifts"**；VPS 上的设计引擎已经在跑 FastAPI |

**没有任何证据与原选择相矛盾**，维持 FastAPI + Pydantic AI；直接用 Anthropic SDK 写循环是第二选项。

---

## 8. 决策矩阵

打分规则：每个子项 0–3 分，每一格都对应上文某条证据。**复刻**和**适用**各折算成 0–10 分，再等权相加（满分 20）。

### 8.1 前端框架（三个工具）
复刻：R1 = 平台在同类界面上用不用（抽屉 / 重表单应用 / 编辑器类应用）；R2 = 被复刻的产品用不用。
适用：F1 = 主机与部署（主机无 Node、产物是静态文件）；F2 = WP 集成（共享运行时、`.asset.php`、React 19 过渡）；F3 = 能否走同一条 WP gettext 管线；F4 = 三类应用的现成开源组件；F5 = 执行者熟悉度；F6 = 测试与 TS；F7 = 全站页面的运行时体积。

| 方案 | R1 | R2 | F1 | F2 | F3 | F4 | F5 | F6 | F7 | 复刻/10 | 适用/10 | **合计/20** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **React + TS（用 WP 自带的 React）** | 3 Checkout / 编辑器 / DataForm；主机注册了 18.3.1 | 3 Shopify Admin+Sidekick、Shop、Accio、淘宝、天猫、Alibaba、美团、EcoFlow、Huawei SmartDesign | 3 | 3 | 3 | 3 | 3 | 3 | 1 约 45 KB | 10.0 | 9.0 | **19.0** |
| Interactivity API | 2 Woo 店面 42 个模块、mini-cart 从 React 改了过来；但 WP 明确"完全交互的应用"用 React | 1 只是理念相同（Horizon、AUI 的服务端渲染 + 渐进增强） | 3 | 3 | 3 | 1 | 1 | 1 | 2 | 5.0 | 6.7 | 11.7 |
| Preact（+compat） | 1 只在 iAPI 内部用 | 1 Shopify 扩展 | 3 | 1 | 2 | 2 | 2 | 2 | 3 | 3.3 | 7.1 | 10.5 |
| Vue 3 | 0 iAPI FAQ 中被放弃 | 2 GoodWe Designer、SolaX Design、sun.store；美团一半栈 | 3 | 1 | 2 | 2 | 2 | 3 | 2 | 3.3 | 7.1 | 10.4 |
| Lit / Web Components | 0 | 2 Amazon 首页、Polaris WC、Fronius | 3 | 2 | 2 | 1 | 1 | 2 | 3 | 3.3 | 6.7 | 10.0 |
| Angular（补充） | 0 | 2 SMA、Fronius、Renusol | 3 | 1 | 1 | 2 | 2 | 3 | 0 | 3.3 | 5.7 | 9.0 |
| Headless Next / React Router | 0 | 2 Hydrogen、美团、EcoFlow | 0 主机无 Node；违背 Q13 | 0 | 1 | 3 | 3 | 3 | 1 | 3.3 | 5.2 | 8.5 |
| htmx + PHP | 0 | 1 只是理念相同 | 3 | 1 | 3 | 0 | 1 | 1 | 2 | 1.7 | 5.2 | 6.9 |
| Alpine.js | 0 iAPI FAQ 中被放弃 | 1 只是理念相同 | 3 | 1 | 2 | 1 | 1 | 1 | 2 | 1.7 | 5.2 | 6.9 |
| Svelte 5 | 0 | 0 | 3 | 1 | 2 | 1 | 1 | 2 | 3 | 0 | 6.2 | 6.2 |
| SolidJS | 0 | 0 | 3 | 1 | 2 | 1 | 1 | 2 | 3 | 0 | 6.2 | 6.2 |

敏感性：把 F7（体积）的权重加倍，React 是 18.3 分，iAPI 11.7，Preact 10.8，排序不变。React 唯一的弱项是体积。§9 的"按交互加载"可以处理它，而且这一做法本身也有复刻依据：Woo 把 React 从店面上拿掉，Shopify 在嵌入式 UI 上改用 Preact，两者优化的都是"页面加载时的 JS"。

### 8.2 插件构建管线
| 方案 | R1 平台 | R2 被复刻产品 | F1 WP externals | F2 依赖/版本清单与 PHP 注册 | F3 i18n JSON | F4 TS | F5 测试 | F6 成熟度 | F7 在 WP 页内的开发循环 | 复刻/10 | 适用/10 | **合计** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **`@wordpress/scripts`** | 3 Woo Blocks、Woo Admin、create-woo-extension；官方"stay on wp-scripts" | 1 淘宝、阿里、美团的构建都是 webpack | 3 | 3 `.asset.php` 含内容 hash | 3 | 2 Babel 只转译，类型检查另跑 `tsc --noEmit` | 3 Vitest 默认 + Playwright | 3 v36，583k/月 | 2 `start --hot` | 6.7 | 9.0 | **15.7** |
| Vite + vite-for-wp / @roots/vite-plugin | 1 只在主题里（Sage） | 2 Shopify Admin、Hydrogen；美团增量项目；IBC 的模块 | 1 要额外插件，依赖手写 | 2 manifest + PHP 库 | 2 Sage 对构建产物跑 make-json | 3 | 3 | 2 Vite 本身成熟，但 WP 桥接很小（25k/月，2025-06 后无推送） | 3 HMR | 5.0 | 7.6 | 12.6 |
| `@wordpress/build`（esbuild） | 2 Gutenberg 自用，是未来的内核；但官方说"not ready" | 0 | 3 | 3 自动生成 PHP 注册 | 2 未写明 | 3 | 1 不带测试器 | 1 v0.25，独立插件的接入"undocumented" | 2 | 3.3 | 7.1 | 10.4 |
| 自写 esbuild 脚本（现状的变体） | 0 | 0 | 1 | 0 要手工维护 asset-pins | 2 | 3 | 0 | 1 | 1 | 0 | 3.8 | 3.8 |

### 8.3 PHP 结构
| 方案 | R1 平台 | R2 | F1 主机 | F2 可测性 | F3 静态分析 | F4 熟悉度 | F5 与规模相称 | 复刻/10 | 适用/10 | **合计** |
|---|---|---|---|---|---|---|---|---|---|---|
| **Composer PSR-4 命名空间 + vendor 随发布（Woo 模式）** | 3 Woo core、create-woo-extension | n/a（被复刻的产品不用 PHP） | 3 | 3 PHPUnit 9.6 + Brain Monkey / WP 测试套件 | 3 Woo 用 level 8 | 3 PSR-4 是 PHP 标准 | 3 | 10.0 | 10.0 | **20.0** |
| 全局前缀函数（WP 手册的最低要求；b2b-core 现状） | 2 | n/a | 3 | 1 | 1 | 2 | 2 | 6.7 | 6.0 | 12.7 |
| PSR-4 + DI 容器框架（如 Acorn） | 1 Woo 内部有容器，但模板不给扩展用 | n/a | 2 | 3 | 3 | 1 | 1 | 3.3 | 6.7 | 10.0 |
| WordPress Plugin Boilerplate | 1 已停滞，且去掉了 Composer | n/a | 3 | 2 | 2 | 2 | 2 | 3.3 | 7.3 | 10.6 |

（PHP 这一层的 R2 不适用：Shopify、Amazon、阿里不以 PHP 交付，所以复刻只看平台，折算时用 R1×10/3。）

### 8.4 Python 助手服务
| 方案 | R 复刻（Sidekick 式的薄 agentic loop） | F1 DeepSeek+Anthropic 原生 | F2 类型化工具 + 输出校验/重试 | F3 与 FastAPI、3.12、1 vCPU 的契合度 | F4 采用度 | F5 复杂度与 6–10 个工具是否相称 | 复刻/10 | 适用/10 | **合计** |
|---|---|---|---|---|---|---|---|---|---|
| **Pydantic AI** | 2 | 3 | 3 | 3 | 2 | 3 | 6.7 | 9.3 | **16.0** |
| Anthropic SDK 自写循环 | 2 | 1 | 2 | 3 | 3 | 3 | 6.7 | 8.0 | 14.7 |
| OpenAI Agents SDK | 1 | 1 要经 LiteLLM | 2 | 2 | 3 | 2 | 3.3 | 6.7 | 10.0 |
| LangGraph | 1 | 2 | 2 | 2 | 3 | 1 | 3.3 | 6.7 | 10.0 |
| Agno | 1 | 2 | 2 | 2 | 2 | 2 | 3.3 | 6.7 | 10.0 |

---

## 9. 每层的推荐与三条最强证据

### 9.1 前端三工具：React + TypeScript，运行在 WordPress 自带的 React 上
**怎么做**
- 一套代码出三个入口：`advisor`、`planner`、`site-detail`。
- `react`、`react-dom`、`react/jsx-runtime` 都外部化到 WP 的 handle，绝不自己打包 jsx-runtime。
- 只写 React 18.3 与 19 都支持的 API：用 `createRoot`；函数组件不用 `defaultProps`；不用字符串 ref 和旧式 context；`inert` 写成布尔值。
- 入口（目录搜索框、商品页"问这款"、购物车页/Proforma 页、账户页）由 PHP 服务端输出标记。Advisor 应用平时只注册不入队，用户第一次交互时才插入脚本（可用一个很小的原生 loader 读取 PHP 输出的 handle 与 URL），这样 React 不进入页面首次加载。
- Planner 与 Site Detail 是专用页，正常加载即可。
- 现成组件：Advisor 用 `@assistant-ui/react`，接自定义 runtime；Planner 用 react-hook-form，配 `@hookform/resolvers` 的 ajv 版，直接用 ability 的 JSON Schema 校验；Site Detail 用 `react-map-gl/maplibre`，terra-draw 的实例放在组件里由 ref 持有。
- 文案统一走 `@wordpress/i18n`。

**三条最强证据**
1. **平台**：我们主机上的 WP 7.1.3 注册的就是 React 18.3.1。Woo 自己表单最重的前台应用（Checkout 块）依赖它。WP 明确说"fully interactive application"继续用 React，而且点名要求插件使用外部化的 React，否则 React 19 升级时会出问题（§2；iAPI FAQ；make.wordpress.org 2026-07-24）。
2. **被复刻的产品**：能测到的 AI 购物与电商网页端全部是 React，包括 Shopify Admin（Sidekick 的宿主，318 万行 TS，Remix）、Shop（React 19.2.8）、Accio（React 19.2.5）、淘宝、天猫、Alibaba.com（React 18）、美团官网（Next.js）。PV 工具没有统一框架（Angular、Vue、React 各 2–3 个），其中公开可用的测算器 EcoFlow Solarrechner 和 Huawei SmartDesign 是 React（§4）。
3. **适用**：三类应用的开源组件集中在 React 生态，见 §5 的下载量对比（assistant-ui 8.15M/月、react-hook-form 251M、react-map-gl 9.8M；Vue 和 Svelte 的同类库少一到三个数量级）。执行者也最熟悉 React：npm 791M/月，SO 2025 44.7%，v0 和 Lovable 默认生成 React，Woo 布道师说 AI 写"generic React"很顺。

**不选的理由（只摘最关键的一条）**
- iAPI：WP 自己把"完全交互的应用"划给 React；iAPI 只用于"服务端渲染内容上的交互"。我们的入口按同样的原则由服务端输出。
- Preact：WP 不提供 Preact 作为应用运行时，用它就要再带一套运行时，开源组件还要承担 compat 风险。它解决的体积问题，用"按交互加载"已经解决。
- Vue：有几个 PV 厂商工具在用（GoodWe、SolaX），这是它唯一的复刻分；但 WP 与 Woo 不用（iAPI FAQ 比较后放弃），AI 电商端没有一个用它，Advisor 与地图的开源组件比 React 少一到三个数量级（vue-maplibre-gl 每月 3.2k）。
- Svelte / Solid / Alpine：平台不用，被复刻的产品里一个都没测到，生态最弱。
- Lit：Amazon 和 Shopify 用它做设计系统和店面组件，不用来做应用；表单和聊天都要从零写。
- Headless：主机上没有 Node，而且违背"同域名一次性更新原站"。
- Angular：只有厂商的独立 SaaS 在用，WP 里没有先例，也最重。

### 9.2 插件构建：`@wordpress/scripts`
**怎么做**
- `plugins/linker-ai-assistant/package.json` 是**唯一的 npm 包**（npm，`package-lock.json`）。
- 运行 `wp-scripts build src/advisor/index.tsx src/planner/index.tsx src/site-detail/index.tsx`，或者写一个继承默认配置的 `webpack.config.js`，产出 `build/*.js` 和 `build/*.asset.php`。
- PHP 用 `.asset.php` 里的 `dependencies` 和 `version`（内容 hash）注册脚本。原来手写的 asset-pins 和版本号递增流程可以删掉。部署前的哈希校验直接读 `version`。
- 类型检查单独跑 `tsc --noEmit`。单元测试用 `wp-scripts test-unit-js`（Vitest 5），端到端用 `wp-scripts test-e2e`（Playwright）。Storybook 只给状态多的 UI 组件用，Woo Blocks 有先例。
- i18n：先 `wp i18n make-pot`，再更新 `.po`（德语由 AI 同步翻译），最后 `wp i18n make-json`，配 `wp_set_script_translations`。
- 不用 pnpm workspace，因为没有跨插件共享的 JS 包，也不发布任何包。Woo 用 pnpm 是为了它约 70 个包的 monorepo。脚手架和 Gutenberg 都用 npm，wp-build 将来的接入也要求 npm workspaces。

**三条最强证据**
1. **平台**：Woo Blocks 和 Woo Admin 都用 webpack 加 WP 的 dependency extraction 构建；Woo 官方扩展脚手架的 `webpack.config.js` 就是在 `@wordpress/scripts` 默认配置的基础上扩展的。
2. **平台路线**：WP Developer Blog（2026-04-02）说下一代 esbuild 内核 `@wordpress/build` "not ready for every use case"，独立插件的接入还没写文档，"Everyone else: stay on `@wordpress/scripts`"；它会在 wp-scripts 内部替换掉 webpack，使用方"`wp-scripts build` continues to work"。现在选 wp-scripts，等于将来不用迁移就能换上新内核。
3. **适用**：WP 专属的几件事在 wp-scripts 里都是开箱即用的：externals 指向 WP 的 React（React 19 的兼容层由 WP 负责）、`.asset.php` 依赖和内容 hash、`@wordpress/i18n` 加 make-json、TS/TSX 入口。它的单元测试器已经换成 Vitest，再加上 Playwright。反观 Vite 的 WP 桥接：vite-for-wp 月下载 25k，2025-06 之后没有推送；@roots/vite-plugin 42k/月，面向主题。

### 9.3 PHP：Composer + PSR-4（WooCommerce 模式），PHPUnit 9.6
**怎么做**
- 每个插件一个 `composer.json`，采用 `psr-4: Linker\B2BCore\ → src/`（或 `includes/`）这样的映射，按 create-woo-extension 用 `automattic/jetpack-autoloader`。
- `config.platform.php = "8.3"`：本机是 8.5，主机是 8.3，Woo 也锁 platform。
- `vendor/` 用 `composer install --no-dev -o` 生成，随插件文件部署。主机上虽然有 Composer，但部署要求逐字节核验，所以发布构建产物。
- 测试：`phpunit/phpunit ^9.6`。纯单元测试用 Brain Monkey；需要 WP 环境的用 `wp scaffold plugin-tests` 加本机已有的 MySQL 跑 WP 测试套件（不用 Docker）。
- 静态分析与规范：`phpstan/phpstan ^2` + `szepeviktor/phpstan-wordpress ^2` + `php-stubs/wordpress-stubs` + `php-stubs/woocommerce-stubs`，新代码 level 8，旧代码进 baseline（`phpVersion: 80300`）；`wp-coding-standards/wpcs ^3` + `woocommerce/woocommerce-sniffs` + `phpcompatibility/phpcompatibility-wp`（testVersion 8.3-）。

**三条最强证据**
1. **平台**：WooCommerce core 采用 PSR-4（`Automattic\WooCommerce\ → src/`），`vendor/` 随插件发布（我们主机实测），PHPUnit ^9.6，PHPStan ^2.1 level 8 加 phpstan-wordpress，并锁定 platform php。
2. **平台给扩展的模板**：create-woo-extension 的 `composer.json` 用 PSR-4，依赖 jetpack-autoloader 和 phpunit ^9.0，命名空间类是 `Admin\Setup`，带 `tests/Test.php` 和 wp-env。
3. **适用与工具约束**：WP_Mock 硬性要求 phpunit ^9.6，Brain Monkey 在 ≤9.6 上测试，WP core 测试套件按 PHPUnit 9.6 编写。020 选的 PHPUnit 11 在 2026-02-06 已经停止 bugfix，而且与这几样都不配套。Plugin Boilerplate 自 2024-07 起停滞，还刻意去掉了 Composer，所以不选。

### 9.4 Python：FastAPI + Pydantic AI（维持）
**三条最强证据**
1. **复刻**：Sidekick 是自建的薄 agentic loop，强调工具数纪律和 JIT instructions，没有用重型编排；我们的 6–10 个工具落在它说的"清晰区间"。
2. **适用**：Pydantic AI 2.54.0 已经是 Production/Stable，原生支持 DeepSeek 和 Anthropic，用 `output_validator` 加 `ModelRetry` 正好实现 006 的锚定核验，Python ≥3.10 与 VPS 的 3.12 匹配。
3. **采用度**：FastAPI 在 SO 2025 比上年 +5 个百分点，PyPI 月下载 381.6M，VPS 上的引擎已经在跑 FastAPI；pydantic-ai 加 slim 每月约 29M 下载。各备选的短处见 §7，没有一条推翻原结论。

---

## 10. 对 020 / 022 的具体修正（执行票按此改写）

| 020 / 022 原文 | 改为 | 依据 |
|---|---|---|
| pnpm 工作区，`apps/*` + `packages/{ui,api-client,i18n,config}` | 插件内只有一个 npm 包：`src/{advisor,planner,site-detail,shared/{ui,api,hooks}}`，多入口 | §3.5、§9.2 |
| React 18 + **Vite**；用 Vite manifest 解析带哈希的文件名 | React + TS，用 **`@wordpress/scripts`**；React 外部化到 WP；用 `.asset.php` 提供依赖和版本 | §3.4、§3.5、§8.2 |
| `packages/i18n`，typed keys 自建目录 | `@wordpress/i18n` + `.pot/.po` + `make-json` + `wp_set_script_translations`，与 PHP 共用一条 gettext 管线（Law 4） | §3.4、Sage 也这样做 |
| `pnpm build:check` 比对自建 manifest | 部署脚本校验 `build/*.asset.php` 里的 `version`（内容 hash）与源码构建结果是否一致 | dependency-extraction 文档 |
| 所有页面都放挂载点并加载应用 | Advisor 入口由服务端渲染，应用按交互加载；Planner、Site Detail 照常加载 | Woo mini-cart、Shopify 64 KB 预算 |
| PHPUnit 11 | **PHPUnit 9.6**（+ Brain Monkey + WP 测试套件，不用 Docker） | §6 |
| PHPStan level 6 | PHPStan 2 level 8 + baseline（与 Woo 一致） | Woo phpstan.neon |
| "宿主无 Composer" | 更正：主机有 Composer 2.9.8。仍然发布 `vendor/` | §2 实测 |
| （缺） | Composer `platform.php = 8.3`、PHPStan `phpVersion: 80300`、PHPCompatibilityWP | 本机 8.5 / 主机 8.3 |
| Vitest / Playwright / Storybook | 保留（wp-scripts 自带 Vitest 和 Playwright；Storybook 只给状态多的组件用） | §3.3、§3.5 |
| Python：uv / pyproject / ruff / mypy / pytest；FastAPI + Pydantic AI | 不变 | §7 |

---

## 11. 未核实与风险（如实列出）

- **Rufus 的前端技术栈不公开**：商品页被反爬拦住，招聘信息也不写框架。Amazon 只计入首页实测（AUI + Lit）。
- **Shopify Admin 没有实测**（Cloudflare 拦截），用的是 Shopify 自己的工程博客。美团点评和美团 H5 被验证页拦住，只测了 meituan.com。
- EWS QuickCalc 要经销商登录，SolarEdge Designer 三次都超时，这两个**无法测**。Solar-Planit 只测到应用的公开首页（jQuery 1.8.3，服务端渲染），登录后的编辑器无法测。厂商 SaaS 的技术栈本来就不一致（§4.3），而且都不嵌在 WordPress 里，不影响结论。
- State of JS 2025 页面的图表数值没能抽成文字，只引用了页面里的定性句子。Stack Overflow 2025 用的是页面正文里的百分比。
- bundlephobia 的数字是"包入口"的 min+gzip，对 Vue 和 Svelte 这类依赖 tree-shaking 或编译的框架只能做量级参考。react-dom@19.2.0 的入口只是薄门面（1.4 KB），所以统一用 18.3.1 的数字（即 WP 实际提供的版本）。
- `@hookform/resolvers` 的 ajv resolver 能不能直接吃 ability 的 JSON Schema（draft 版本、`format` 关键字），要在执行票里用一个真实的 ability schema 验证。
- 按交互加载 Advisor 的具体机制（loader 怎样拿到 WP 注册的 handle 和 URL）由执行票实现，并用实测确认首屏不再加载 React。
- 顺带发现，与本题无关：生产主机的插件目录里有一个 `terravolt-b2b-core-broken-20260704/` 文件夹（WP 插件列表里没有出现，说明主文件头无效或缺失），是 2026-07 遗留下来的副本。

---

## 附录 A：来源索引（全部经 Apify 获取，取于 2026-10-09）

### A.1 文档、博客、问题单全文（`apify/website-content-crawler`）
- https://shopify.dev/docs/api/polaris  （run DmAfxYvSr1nbktg1I）
- https://github.com/WordPress/WordPress-Coding-Standards  （run DmAfxYvSr1nbktg1I）
- https://shopify.dev/docs/api/checkout-ui-extensions  （run DmAfxYvSr1nbktg1I）
- https://shopify.dev/docs/storefronts/headless/hydrogen  （run DmAfxYvSr1nbktg1I）
- https://github.com/Shopify/polaris  （run DmAfxYvSr1nbktg1I）
- https://developer.woocommerce.com/docs/extensions/getting-started-extensions/  （run DmAfxYvSr1nbktg1I）
- https://developer.woocommerce.com/docs/best-practices/coding-standards/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/packages/packages-scripts/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/iapi-about/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/iapi-faq/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/packages/packages-dataviews/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/packages/packages-dependency-extraction-webpack-plugin/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/how-to-guides/internationalization/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/packages/packages-env/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/news/2024/03/how-to-use-wordpress-react-components-for-plugin-pages/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/packages/packages-element/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/plugins/plugin-basics/best-practices/  （run DmAfxYvSr1nbktg1I）
- https://make.wordpress.org/core/2024/03/04/script-modules-in-6-5/  （run DmAfxYvSr1nbktg1I）
- https://make.wordpress.org/core/handbook/testing/automated-testing/phpunit/  （run DmAfxYvSr1nbktg1I）
- https://github.com/kucrut/vite-for-wp  （run DmAfxYvSr1nbktg1I）
- https://roots.io/sage/docs/installation/  （run DmAfxYvSr1nbktg1I）
- https://bud.js.org/  （run DmAfxYvSr1nbktg1I）
- https://roots.io/sage/  （run DmAfxYvSr1nbktg1I）
- https://survey.stackoverflow.co/2025/technology  （run DmAfxYvSr1nbktg1I）
- https://2025.stateofjs.com/en-US/libraries/front-end-frameworks/  （run DmAfxYvSr1nbktg1I）
- https://github.com/JamesLMilner/terra-draw  （run DmAfxYvSr1nbktg1I）
- https://visgl.github.io/react-map-gl/docs/get-started  （run DmAfxYvSr1nbktg1I）
- https://svelte.dev/docs/llms  （run DmAfxYvSr1nbktg1I）
- https://github.com/Brain-WP/BrainMonkey  （run DmAfxYvSr1nbktg1I）
- https://github.com/10up/wp_mock  （run DmAfxYvSr1nbktg1I）
- https://github.com/szepeviktor/phpstan-wordpress  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/  （run DmAfxYvSr1nbktg1I）
- https://developer.wordpress.org/news/2026/04/wordpress-build-the-next-generation-of-wordpress-plugin-build-tooling/  （run io6HOtRsuYaqlgK5V）
- https://roots.io/sage-v11-and-acorn-v5-released/  （run io6HOtRsuYaqlgK5V）
- https://make.wordpress.org/core/2026/07/24/react-19-punted-beyond-wordpress-7-1-experiment-in-gutenberg/  （run io6HOtRsuYaqlgK5V）
- https://make.wordpress.org/core/2026/05/27/react-19-upgrade-in-wordpress/  （run io6HOtRsuYaqlgK5V）
- https://github.com/WordPress/gutenberg/blob/trunk/packages/wp-build/README.md  （run io6HOtRsuYaqlgK5V）
- https://make.wordpress.org/core/2026/08/05/wordpress-7-1-field-guide/  （run io6HOtRsuYaqlgK5V）
- https://make.wordpress.org/core/2026/05/14/wordpress-7-0-field-guide/  （run io6HOtRsuYaqlgK5V）
- https://github.com/woocommerce/woocommerce/issues/60820  （run io6HOtRsuYaqlgK5V）
- https://www.briancoords.com/my-wp-woo-plugin-scaffolding-in-2026/  （run io6HOtRsuYaqlgK5V）
- https://developer.woocommerce.com/docs/getting-started/scaffolding/  （run io6HOtRsuYaqlgK5V）
- https://github.com/woocommerce/woocommerce/issues/61640  （run io6HOtRsuYaqlgK5V）
- https://developer.woocommerce.com/docs/extensions/getting-started-extensions/building-your-first-extension/  （run io6HOtRsuYaqlgK5V）
- https://tech.meituan.com/2023/08/03/meituan-Rome-Practice.html  （run io6HOtRsuYaqlgK5V）
- https://amazon.jobs/en/jobs/10502024/software-development-engineer-ii-rufus-engineering  （run io6HOtRsuYaqlgK5V）
- https://www.amazon.jobs/en/jobs/10463819/software-dev-engineer-in-test-conversational-shopping  （run io6HOtRsuYaqlgK5V）
- https://www.amazon.jobs/en/jobs/10509601/software-development-engineer-iii-agentic-client-experience-ace-builder-foundations  （run io6HOtRsuYaqlgK5V）
- https://shopify.engineering/building-production-ready-agentic-systems  （run io6HOtRsuYaqlgK5V）
- https://shopify.dev/docs/api/app-home/polaris-web-components  （run io6HOtRsuYaqlgK5V）
- https://lovable.dev/blog/frontend-development-with-lovable  （run io6HOtRsuYaqlgK5V）
- https://www.maplibre.org/maplibre-gl-js/docs/examples/draw-geometries-with-terra-draw/  （run io6HOtRsuYaqlgK5V）
- https://github.com/JamesLMilner/terra-draw/issues/172  （run io6HOtRsuYaqlgK5V）
- https://vercel.com/i/what-is-shadcn  （run io6HOtRsuYaqlgK5V）
- https://developers.google.com/maps/documentation/javascript/examples/map-drawing-terradraw  （run io6HOtRsuYaqlgK5V）
- https://www.zhipin.com/zhaopin/a5d47be4f20c05171n1729W8EQ~~/  （run io6HOtRsuYaqlgK5V）
- https://github.com/roots/vite-plugin  （run io6HOtRsuYaqlgK5V）
- https://developer.woocommerce.com/2025/12/10/woocommerce-10-4-the-interactivity-api-mini-cart-goes-live/  （run bWyHvbWWcDfA2tWLd）
- https://shopify.engineering/remixing-admin  （run bWyHvbWWcDfA2tWLd）
- https://developer.woocommerce.com/2025/10/01/improving-woocommerce-performance-at-scale/  （run bWyHvbWWcDfA2tWLd）
- https://shopify.dev/docs/api/polaris/using-polaris-web-components  （run bWyHvbWWcDfA2tWLd）
- https://shopify.engineering/upgrading-checkout-blocks-app-to-polaris-web-components  （run bWyHvbWWcDfA2tWLd）
- https://shopify.engineering/shopifys-platform-is-the-web-platform  （run bWyHvbWWcDfA2tWLd）
- https://github.com/woocommerce/woocommerce/issues/66516  （run bWyHvbWWcDfA2tWLd）
- https://www.assistant-ui.com/  （run bWyHvbWWcDfA2tWLd）
- https://developer.wordpress.org/block-editor/reference-guides/packages/packages-wp-build/  （run bWyHvbWWcDfA2tWLd）

### A.2 仓库原始文件、API 与元数据（`apify/playwright-scraper`）
- https://raw.githubusercontent.com/WordPress/gutenberg/trunk/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/WordPress/gutenberg/trunk/packages/scripts/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/WordPress/wordpress-develop/trunk/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/WordPress/gutenberg/trunk/packages/scripts/README.md  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/WordPress/wordpress-develop/trunk/composer.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/WordPress/gutenberg/trunk/packages/interactivity/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/WordPress/gutenberg/trunk/packages/element/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/pnpm-workspace.yaml  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/plugins/woocommerce/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/plugins/woocommerce/composer.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/plugins/woocommerce/phpcs.xml  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/plugins/woocommerce/client/blocks/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/plugins/woocommerce/phpstan.neon  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/plugins/woocommerce/client/admin/package.json  （run lfvARZpX38oTHSvWK）
- https://api.github.com/repos/woocommerce/woocommerce/contents/packages/js/create-woo-extension  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/packages/js/create-woo-extension/README.md  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/packages/js/create-woo-extension/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/packages/js/create-woo-extension/index.js  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/kucrut/vite-for-wp/main/README.md  （run lfvARZpX38oTHSvWK）
- https://api.github.com/repos/woocommerce/woocommerce/contents/packages/js/create-woo-extension/project-template  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/roots/sage/main/vite.config.js  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/roots/sage/main/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/roots/sage/main/composer.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/Brain-WP/BrainMonkey/master/composer.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/10up/wp_mock/trunk/composer.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/DevinVinson/WordPress-Plugin-Boilerplate/master/README.md  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/Shopify/polaris/main/README.md  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/Shopify/hydrogen/main/package.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/Shopify/horizon/main/README.md  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/WordPress/WordPress-Coding-Standards/develop/composer.json  （run lfvARZpX38oTHSvWK）
- https://raw.githubusercontent.com/szepeviktor/phpstan-wordpress/master/composer.json  （run lfvARZpX38oTHSvWK）
- https://registry.npmjs.org/@wordpress/build/latest  （run o3JwXeXEILTCakZPV）
- https://registry.npmjs.org/@wordpress/scripts/latest  （run o3JwXeXEILTCakZPV）
- https://registry.npmjs.org/@wordpress/interactivity/latest  （run o3JwXeXEILTCakZPV）
- https://registry.npmjs.org/@roots/vite-plugin/latest  （run o3JwXeXEILTCakZPV）
- https://registry.npmjs.org/@kucrut/vite-for-wp/latest  （run o3JwXeXEILTCakZPV）
- https://pypi.org/pypi/fastapi/json  （run o3JwXeXEILTCakZPV）
- https://api.github.com/repos/woocommerce/woocommerce/contents/packages/js/create-woo-extension/variants/default  （run o3JwXeXEILTCakZPV）
- https://api.github.com/repos/WordPress/gutenberg/contents/packages/wp-build  （run o3JwXeXEILTCakZPV）
- https://api.github.com/repos/woocommerce/woocommerce/contents/packages/js/create-woo-extension/variants/default/src  （run o3JwXeXEILTCakZPV）
- https://pypi.org/pypi/pydantic-ai/json  （run o3JwXeXEILTCakZPV）
- https://raw.githubusercontent.com/WordPress/gutenberg/trunk/packages/wp-build/package.json  （run o3JwXeXEILTCakZPV）
- https://raw.githubusercontent.com/WordPress/gutenberg/trunk/packages/wp-build/README.md  （run o3JwXeXEILTCakZPV）
- https://phpunit.de/supported-versions.html  （run o3JwXeXEILTCakZPV）
- https://survey.stackoverflow.co/2025/technology  （run o3JwXeXEILTCakZPV）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/packages/js/create-woo-extension/variants/default/%24slug.php.mustache  （run F5xZhBJQOayxwvGOo）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/packages/js/create-woo-extension/variants/default/composer.json.mustache  （run F5xZhBJQOayxwvGOo）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/packages/js/create-woo-extension/variants/default/webpack.config.js.mustache  （run F5xZhBJQOayxwvGOo）
- https://raw.githubusercontent.com/woocommerce/woocommerce/trunk/packages/js/create-woo-extension/variants/default/.wp-env.json.mustache  （run F5xZhBJQOayxwvGOo）
- https://api.github.com/repos/woocommerce/woocommerce/contents/packages/js/create-woo-extension/variants/default/includes  （run F5xZhBJQOayxwvGOo）
- https://raw.githubusercontent.com/react-hook-form/resolvers/master/README.md  （run F5xZhBJQOayxwvGOo）
- https://api.github.com/repos/woocommerce/woocommerce/contents/packages/js/create-woo-extension/variants/default/tests  （run F5xZhBJQOayxwvGOo）
- https://raw.githubusercontent.com/assistant-ui/assistant-ui/main/README.md  （run F5xZhBJQOayxwvGOo）
- npm 下载量：`https://api.npmjs.org/downloads/point/last-month/<pkg>`（区间 2026-09-08..2026-10-07）和 `…/last-year/…`；GitHub 元数据：`https://api.github.com/repos/<owner>/<repo>`；PyPI：`https://pypistats.org/api/packages/<pkg>/recent`；体积：`https://bundlephobia.com/api/size?package=<pkg>`（run lfvARZpX38oTHSvWK，dataset o1cqeePzHhQbjIPh8）

### A.3 运行时框架检测（`apify/playwright-scraper`，注入 React DevTools hook 并采集 DOM 与全局指纹）
- run 9GcmTQq8eZJymZHRr：https://creator.fronius.com/、https://www.segen.co.uk/portal/、https://pv.de/、https://solar.huawei.com/at/smart-design/、https://www.amazon.com/dp/B09B8V1LZ3、https://www.amazon.de/、https://www.amazon.com/、https://woocommerce.com/、https://www.shopify.com/、https://hydrogen.shop/、https://admin.shopify.com/、https://www.accio.com/、https://www.alibaba.com/、https://www.taobao.com/、https://www.tmall.com/、https://www.meituan.com/、https://www.dianping.com/、https://i.meituan.com/、https://www.sunnydesignweb.com/sdweb/、https://shop.app/、https://solar-planit.com/、https://www.memodo.de/photovoltaik/heimspeicher/、https://www.memodo.de/、https://shop.krannich-solar.com/de-de/、https://shop.ibc-solar.de/、https://energy.ecoflow.com/de/design、https://sun.store/en、https://solar-distribution.baywa-re.de/de/
- run wlYAkBlhEt7gOqOTX：https://solar-planit.com/、https://pv.de/leistungen/、https://shop.krannich-solar.com/de-de/Services/Auslegungstools、https://solar-distribution.baywa-re.lu/en/services/free-engineering-tool-solar-planit、https://www.ibc-solar.de/installateure/produkte/pv-manager/
- run EkgsMjYa7b4qExOeW：https://eu5.smartdesign.huawei.com/sdwebportal/app.html#/login、https://solar-planit.de/solarplanit/html/home、https://konfigurator.solar-log.com/、https://pv.de/leistungen/anlagenplanung/、https://design.solaxcloud.com/#/login、https://www.pv-configurator.com/login?register=、https://designer.goodwe.com/、https://www.sigenergy.com/en/service/sigenstack_tool
- 未拿到结果的：accounts.shopify.com（403/429）、app.solar-planit.com（DNS/隧道失败；真实地址在第二轮被找到）、designer.solaredge.com 与 solaredge.com 的 Designer 页（超时）。

### A.4 检索发现（`apify/google-search-scraper`）
- run dhEb13qXLsX5y0iww（40 个查询）、9Ptr3FOgzKseFmVhD（17 个查询）。查询语言覆盖中、英、德，用于找到上面的一手页面；正文结论不引用检索摘要，只有标注为"检索摘要"的两处例外。

### A.5 我们自己的系统（直接读取，2026-10-09）
- 生产主机：`ssh hostinger-de-linker` 后执行 `php -v`、`composer --version`、`wp --version`、`wp core version`、`wp plugin list`、`wp eval`（读取 `wp_scripts()` 和 `wp_script_modules()` 的注册表）、`ls wp-content/plugins/woocommerce/vendor`。全部只读。
- 前台：`curl` 读取 `https://de-linker.com/`、`/linker-planner/`、`/cart/` 的 HTML，列出加载了哪些 JS。
- 本机：`node`、`pnpm`、`npm`、`php`、`composer`、`docker`、`wp`、`uv` 的版本。
