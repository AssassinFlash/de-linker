# H1 · storefront.css 死规则清理 · 验收记录（2026-10-16）

清理 `plugins/linker-commerce/content/windpress/storefront.css` 里 `body.sf-account-page*`
一族的死规则（#184 §九 记录项，debt-sweep 台账 H1）。这是**删除票**：没有新增行为，
验收的全部内容是①证明这些规则真的死了 ②证明删掉后没有任何东西变样。

## 1. 死亡取证（产出端为零）

选择器要命中，必须有一个元素带 `sf-account-page` / `sf-account-home` / `sf-account-inner`
类之一。这些类只可能来自 `body_class` 过滤器（帐号页的 body 类由旧 storefront 层加）。
按下列顺序证明产出端为零：

| 检查 | 命令 | 结果 |
|---|---|---|
| PHP 里有没有 `body_class` 生产者 | `grep -rn "body_class" --include="*.php" plugins/ mu-plugins/ themes/` | 命中只在 `vendor/` 的 stub 与 `ModuleTest` 的说明注释——**仓库零生产者** |
| 全仓 `sf-account-*` 引用 | `grep -rn "sf-account" --include="*.php" --include="*.js" --include="*.tsx" --include="*.html" plugins/ mu-plugins/ themes/ tools/ services/` | 唯一命中是 `tests/php/Unit/Presentation/ModuleTest.php:36` 的注释（说明该过滤器已删） |
| LC 模板产出端 | `grep -rn "sf-account" plugins/linker-commerce/content/livecanvas/` | 零命中 |
| 运行时（真实页面） | 实例 335 个 URL 全量抓取，见 §3 | **0 命中**（登录态与匿名态各一遍） |

`ModuleTest::test_register_adds_exactly_the_module_hooks` 的 docblock 是这条链的存档说明：
「there is deliberately no body_class filter left, because the sf-account-page body class had
no consumer after the storefront CSS was retired」。WP_Mock 严格模式会把任何多余的钩子判失败，
即"过滤器被重新加回来"这件事本身会被 CI 拦住。

选择器族内还有一批 `sf-account-*` **元素类**（`.sf-account-card`、`.sf-account-btn`…）与
`.tv-b2b-*`、`.linker-project-*` 类名。它们同样只在死规则里出现：全 CSS 卷内
`grep 'sf-account-'` 在 storefront.css 之外零命中，`linker-project` 在 `windpress/` 目录下
只存在于 storefront.css（且全部带 `body.sf-account-page` 前缀），LC 模板与 PHP 里的
`linker-project` 命中是**另一个东西**（PDP 的 `pdp-project-check` / `data-linker-project-*`）。

## 2. 删除范围与数字

删除按"整条规则的逗号分隔选择器清单全部为死载体"判定，混合规则（清单里既有死载体又有活选择器）
**拆开保留**——实测**不存在**混合规则（0 条），所以没有需要拆的：

- 死载体出现次数：**347**（`sf-account-page` 334 / `sf-account-home` 7 / `sf-account-inner` 6）
- 带载体的行数：**342**（= 台账"329 处"的同一口径只数 `sf-account-page` 一型：**329 行**，
  与台账逐字相符；余下 13 行是 `-home` / `-inner` 两型，台账括注里写了它们）
- 删除的规则块：**287**（独立复算：删除区间内 `{` 296 个 − at-rule 开括号 9 个 = 287）
- 删除的选择器部分：**342**
- 删除的注释：**12**；随之清空的 at-rule 空壳：**9**
- 字节：**102 368 → 60 080**，净删 **42 288 字节**（文件行数 3379 → 2148）。
  其中纯删除部分是 42 463 字节；改写的那条注释补回 175 字节。
  脚本口径（字符数）102 307 → 59 903，差值是删除区间里的多字节字符（`──` 等框线）。
- 存活规则：**375 个规则块（346 个唯一选择器清单）前后逐字节一致**（脚本内置不变量：任何存活规则的文本必须与原文完全相同；不变量在「无重复 prelude」前提下成立，本文件的 22 个重复 prelude 已由独立逐字节残留复核覆盖，
  否则拒绝写盘；`missing 0 / changed 0 / extra 0`）
- 存活规则只有一处**注释**改写：`body.woocommerce-account.logged-in .woocommerce` 上方的
  旧注释写的是已删族（"Account home, inner navigation…"），改成描述这条规则现在的职责。

### 那一条"看起来像 account 却必须留"的规则

`body.woocommerce-account.logged-in .woocommerce`（1360px 框）不是死规则，它的载体是
`woocommerce-account`，WooCommerce 原生输出。实测它是**承重**的：把它的声明 neutralize 后
框宽从 1360px/40px 内外边距变成 1440px/0（`account.css` 的
`body.woocommerce-account .linker-account.woocommerce { width:100% }` 与它同权重，
靠 `main.css` 的 import 顺序分胜负——storefront.css 在 account.css 之后导入）。
像素回归的 0 差异正是它留在原位的证据。

## 3. 运行时全量扫描（产出端零命中的直接证据）

实例 `h1clean`（http://127.0.0.1:9045），装入本分支 + 快照 `20261015-1852`
（ok:true，212 商品 / 2755 附件 / 0 缺失 / 0 线上地址）+ 本分支的 WindPress 卷 + 重编译。

`urls.sh` 从数据库取每个已发布对象（page / post / product 两语言）、每个非空 term 归档、
首页、搜索页、购物车、结账、帐号端点，共 **335 个 URL**；`scan-classes.sh` 逐个抓取
（`-L` 跟随 301）并 grep 三个载体类名。

> 复现用的脚本在 `.scratch/h1-dead-css/`（该目录按仓库约定不进版本库，随会话留在工作机）：
> `urls.sh`（取 URL 清单）、`scan-classes.sh`（全量抓取 + 类名扫描）、
> `delete_dead.py`（删除 + 不变量断言）、`compare.py`（逐字节像素比对）、
> `capture.sh` / `pairs-*.json`（12 配对拍摄）、`wrong-password.mjs`（通知态对照）、
> `probe-rule.mjs`（承重性实测）。拍摄工具复用 `.scratch/acceptance-tools/shoot.mjs`。

| 会话 | URL 数 | 载体类命中 | 非 200 |
|---|---|---|---|
| 匿名 | 335 | **0** | 0 |
| 登录（customer-2） | 335 | **0** | 0 |

`GET /my-account/`、`/my-account/register/`、`/de/mein-konto/`、`/de/mein-konto/register/`
的 `<body class="…">` 实测为 `woocommerce-account woocommerce-page …`，**无 `sf-account-page`**。

这个实例装的是**线上快照的数据库与主题**（链接的只有 `linker-*` 三个插件是检出），
所以"渲染出来的页面不带这个类"这条不只对我们的树成立，对线上内容也成立。

补充一条旁证：线上自己的 WindPress 卷副本（快照带来的 `uploads/windpress/data/storefront.css`，
151 736 字节，未随本票改动）**同样带着这 347 处载体**（`sf-account-page` 334 / `-home` 7 /
`-inner` 6），而快照的插件树里没有任何 `sf-account-page` 字符串——即这层样式在线上也是
无人产出的遗留物；本票只处置我们仓库里的那份（部署时由 `WindPressVolume::install` 覆写）。

## 4. 像素回归（验收基准 = #184 原型）

删除前后各拍一轮，同一浏览器、同机、同视口、禁动画、等字体图片：

- 轮 A（删前）：`just up h1clean` + `just pull load h1clean 20261015-1852` + `just present` +
  `just windpress-compile`（缓存 719 748 字节）
- 轮 B（删后）：同一实例换装本分支 CSS（`just present` 卷更新）+ `just windpress-compile`
  （缓存 **678 035** 字节，−41 713）
- 对照轮 A2（同一份删前代码重拍一遍）用于测量噪声底噪

**噪声底噪 = 0**：轮 A vs A2（代码逐字节相同、两次独立拍摄）12 张全部 0 差异像素
（含 390 宽 DPR 2 的 780px 位图、全页高度 2782–5224px）。即这条流水线的重拍噪声本来就为 0。

**A vs B = 0 差异像素**，12 个配对，无掩膜：

| 页面 | 视口 | 语言 | 尺寸 | 差异像素 |
|---|---|---|---|---|
| 登录卡 | 1440 | EN | 1440×1419 | 0 |
| 登录卡 | 390 | EN | 780×2782 | 0 |
| 登录卡 | 1440 | DE | 1440×1419 | 0 |
| 登录卡 | 390 | DE | 780×2908 | 0 |
| 注册卡 | 1440 | EN | 1440×2268 | 0 |
| 注册卡 | 390 | EN | 780×5052 | 0 |
| 注册卡 | 1440 | DE | 1440×2268 | 0 |
| 注册卡 | 390 | DE | 780×5224 | 0 |
| dashboard（登录后） | 1440 | EN | 1440×1436 | 0 |
| dashboard | 390 | EN | 780×3114 | 0 |
| dashboard | 1440 | DE | 1440×1436 | 0 |
| dashboard | 390 | DE | 780×3182 | 0 |

比对是**逐字节 RGB 相等**（无容差阈值），不是"接近"。

### 通知态：删掉的 `.sf-account-notice*` 一族本来要生效的那个状态

死规则里有一族 `.sf-account-notice`（错误/暂停/成功三种色调），它唯一可能生效的状态是
"口令错误后回显 notice"。这条状态是可到达的，所以单独做了对照：固定用户名
（`customer-2`，避免 e2e 时间戳用户名带来的必然差异）提交错误口令，等 notice 可见后拍摄。

| 面 | 视口 | 语言 | 尺寸 | 差异像素 |
|---|---|---|---|---|
| 错误口令 notice | 1440 | EN | 1440×1489 | 0 |
| 错误口令 notice | 390 | EN | 780×2964 | 0 |
| 错误口令 notice | 1440 | DE | 1440×1489 | 0 |
| 错误口令 notice | 390 | DE | 780×3090 | 0 |

两轮的通知文本逐字相同（EN "The username or the password is not correct." /
DE "Benutzername oder Passwort ist nicht korrekt."），像素 0 差异——
即这一族即使在它被写出来的那个状态里也从未生效过。

## 5. WindPress 编译验证

- `just present h1clean` 把卷内 `storefront.css` 更新为分支版本（md5 与仓库一致：
  `6e7027f2a87334a7620ab7f5394d5fbb`）；卷内与仓库同名的样式文件共 16 个，**除 storefront.css
  之外的 15 个逐一 md5 相等**——即两轮之间只有这一个文件变了。卷内另 4 个（`main.css`、
  `terravolt-components.css`、`terravolt-theme.css`、`wizard.css`）是站点自带的，不属本仓。
- `just windpress-compile h1clean`：`{"compiled":true,…,"file_size":678035}`，
  缓存 mtime 更新，anchor classes 检查通过。
- 编译产物 `tailwind.css` 里 `sf-account` 出现次数：删前 **286** → 删后 **0**。
- 存活规则确实进了产物（抽查 `#linker-products .rail-summary`、`body.woocommerce-cart`、
  `#tv-woo-b2b-checkout .sf-checkout-facts`、`body.woocommerce-account.logged-in .woocommerce`
  均有命中），不是"整块没编进去"。

## 6. 静态与测试

- `just php-check`：五个 PHP 项目 PHPCS + PHPStan level 8 全 `No errors`
- `just php-test`：1069 / 152 / 113 / 6 通过，跳过 54（与 main 基线逐项相同）
- `ProductShortcodesTest` 的一处行号引用（`storefront.css:192`）在**本次改动之前就已失准**
  （该规则实测在 212 行；`git log -S` 显示 c4489394 引入该引用时就已写 192——引入即失准）。
  按"本轮发现的问题本轮修"改正为 212，并在改动后的文件上复核。
- 文件级测试 `PdpStylesTest::test_the_storefront_stylesheet_leaves_the_product_page_alone`
  读的就是这个文件，仍绿。
- `just e2e h1clean specs/account.spec.ts`（真实例 + engine/Genie 起齐，走标准门禁而非
  `LINKER_E2E_SKIP_SERVICES`）：**13 passed (58.7s)**。被删 CSS 所在层就是这条链，
  这是规格要求的"改动所在层的真实夹具测试"。

### 为什么没有再加一条"这族不许回来"的守卫测试

复活一条 `body.sf-account-page` 规则需要两件事同时发生：CSS 规则回来，**且** body 类回来。
后者的复发路径已经被既有测试挡住——`ModuleTest::test_register_adds_exactly_the_module_hooks`
在 WP_Mock 严格模式下跑，多一个过滤器就失败（该测试的 docblock 明写"there is deliberately no
body_class filter left"）。再加一条 CSS 侧断言只是复述 diff，属无谓测试膨胀
（本线纪律：修复期复用既有测试，只给被改行为加断言），故不加。

## 7. 结论

产出端为零已由静态（零生产者）+ 运行时（670 次页面抓取 0 命中）双向证实；删除是纯删除
（0 行新增，除一处注释改写与一处行号引用修正）；存活规则逐字节未动；
16 个配对像素差异 0、底噪 0、无掩膜；编译产物无残留类。
