# 商城样式重写后的承载记录（2026-10-13）

登记册 C6 要求按已核视觉重写 `content/windpress/storefront.css` 与 `catalogue.css`，替换复制自旧插件的样式，并在替换后验证承载。C7 要求这次替换留下可重跑的受影响面记录。本文是那份记录。

页头卷 `chrome.css` 已由 PR #119 独立合入，本轮不改它，也不在这两份卷里重写页头规则。两份卷与 `chrome.css` 的选择器交集只有颜色字面量（`#fff`、`#f3f7f2` 等），没有 `#lc-header` / `#tv-header-v2`。

## 替换了什么

重写前两份卷的头部写明出处是旧插件 `terravolt-b2b-core` 的 `assets/storefront.css` 与 `assets/catalogue.css`，版本 `0.12.413`。

重写后：

- 选择器与声明保持原样。注释去掉之后，声明行与 `origin/main` 逐行相同（storefront 4324 行，catalogue 217 行，catalogue-mounts 104 行）。
- 注释按本仓库的卷职责重写：共享 token、产品列表、产品页、方案草稿、询盘、账户。页头明确留给 `chrome.css`。
- `catalogue.css` 写明它以 `body` 前缀重述列表类，盖过 `storefront.css` 的低特异度基座；`catalogue-mounts.css` 仍只负责工具条宽度和联系带。
- `catalogue-mounts.css` 里两处把这两卷称作复制件的句子改成卷名。规则未动。
- 类名未改。类名清零是另一条并行线的事。

旧出处字符串 `terravolt-b2b-core` 与 `0.12.413` 在这三份卷里已不存在。

## 这次在 t110 上跑过的命令

实例 `t110`（`http://127.0.0.1:8975`）当时被其他车道轮流绑定。编译读的是 `uploads/windpress/data/`，不读插件树，所以没有改它的插件链接。

1. 把本分支的三份卷复制进 `~/de-linker-local/t110/wordpress/wp-content/uploads/windpress/data/`（`storefront.css`、`catalogue.css`、`catalogue-mounts.css`）。`chrome.css` 未动。
2. 编译前、编译后核对卷 md5，三份都与本分支源文件相同：

   - `storefront.css` `7e6952c48532ed2507cf6a8a942f8bcb`（147454 字节）
   - `catalogue.css` `d5a8febdeddb08ab7a650452b5cdf3ff`
   - `catalogue-mounts.css` `53dfdd248d44ae68bf0009847ca75af6`

3. 用实例管理员的一次性登录跑官方编译脚本：

```text
node tools/windpress-compile.mjs <one-time-login-url> 1791827163
```

返回 `{"compiled":true,"last_generated":1791827290,"file_size":588763,"toast":false,"ms":37105}`。缓存文件时间从 `2026-10-13 01:46:03` 变为 `01:48:10`，体积 588763 字节，与编译前相同。体积不变是预期：声明没有改，编译器丢掉注释。

第一次编译（`last_generated` 1791827163）作废：当时卷目录已被另一条车道在 01:39 写回旧复制件。承载结论只认第二次，即卷 md5 与本分支一致的那一次。

## 三页抽查

缓存参数 `?cbq=`，样式表地址带 `?ver=1791827290`。

| 页 | URL | HTTP | 页面上的根 | 计算样式 |
|---|---|---|---|---|
| shop | `http://127.0.0.1:8975/products/` | 200 | `#tv-woo-b2b-catalog.sf-catalog` | 背景 `rgb(247, 247, 241)`；`.sf-card` 圆角 `18px`；`.wb-title` 字重 `600` |
| catalogue | `http://127.0.0.1:8975/product-category/inverters/` | 200 | 同上，另有 `.sidebar-filters`、`.catalog-layout` | 背景 `rgb(247, 247, 241)`；侧栏字号 `12px`；网格 `display:grid` |
| PDP | `http://127.0.0.1:8975/product/goodwe-gw60k-sts-g10/` | 200 | `#tv-storefront-pdp`，含 `.pdp-layout`、`.pdp-gallery`、`.pdp-h1` | 字体 Plus Jakarta Sans；标题字重 `600`；布局 `display:grid` |

德语产品页 `http://127.0.0.1:8975/de/produkt/goodwe-gw60k-sts-g10/` 仍由旧的 `#tv-product-template-v5` 模板渲染，没有 `#tv-storefront-pdp`。这不是这次重写引入的：选择器没变，英文产品页才是这卷的宿主。抽查因此用英文产品页。

同一份缓存（页面引用的 URL 与磁盘文件字节相同，588735 字符）里，这三页用到的选择器都在：`#tv-woo-b2b-catalog` 340 次，`.sf-catalog` 127 次，`.sf-card` 43 次，`.card-exact-article` 9 次，`#tv-storefront-pdp` 648 次，`.pdp-layout` 6 次，`.sidebar-filters` 7 次，`.catalog-grid` 6 次。

## 重跑

在已装快照、WindPress 已激活的实例上：

```text
# 1. 把本分支 content/windpress/{storefront,catalogue,catalogue-mounts}.css
#    复制到 <instance>/wordpress/wp-content/uploads/windpress/data/
# 2. 记下缓存 mtime，取一次性登录，跑官方编译
node tools/windpress-compile.mjs <one-time-login-url> <cache-mtime-before>
# 3. 编译前后 md5 必须与分支源文件相同，否则编进去的不是这版
# 4. curl 三页，确认 HTML 引用的 tailwind.css?ver= 等于新的 last_generated
curl -s -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:8975/products/?cbq=1'
curl -s -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:8975/product-category/inverters/?cbq=1'
curl -s -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:8975/product/goodwe-gw60k-sts-g10/?cbq=1'
# 5. 在编译缓存里数选择器
#    #tv-woo-b2b-catalog .sf-card .sidebar-filters #tv-storefront-pdp .pdp-layout
```

`just present <instance>` 会从实例当前绑定的插件树复制卷。实例被其他车道绑定时，直接复制卷文件，不要改插件链接。

## 没有声称的事

- 没有做像素对照。C6 写明拷了样式不等于整页外观已验收。
- 没有改类名，也没有删 `chrome.css`。
- 没有合并。
