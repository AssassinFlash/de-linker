# GAP-7 的核验：产品页的 Product JSON-LD 从哪来（#81）

核验日期 2026-10-11。核验对象是**留用的 SEO 插件是否已经在产品页输出 `Product` 节点**，
以及它输出的那个节点和线上今天真正输出的那个是否等价。结论在文末，命令与原始输出在中间。

实例：本地 `t81`（`just up t81` 后装 20261010-0033 快照，`--live-code`，线上代码与线上一启用列表），
端口 8933。所有本地请求带 `?cbq=`（LiteSpeed 全页缓存之外的证据才算证据）。
线上那一条是只读 GET。

## 1. 线上今天输出的节点（只读 GET）

```sh
curl -s "https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/?cbq=81-t81"
```

1 个 `application/ld+json` 块：

```json
{"@context":"https://schema.org","@type":"Product",
 "name":"GoodWe GW5.1-BAT-D-G21 (ESA battery module, 5.12 kWh)",
 "url":"https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/",
 "sku":"DLK-GOODWE-GW51BATDG21",
 "brand":{"@type":"Brand","name":"GoodWe"},
 "manufacturer":{"@type":"Organization","name":"GoodWe"},
 "category":"Home Storage",
 "description":"GW5.1-BAT-D-G21 is the 5.12 kWh rated ESA battery module …",
 "model":"GW5.1-BAT-D-G21",
 "image":"https://de-linker.com/wp-content/uploads/2026/09/goodwe-esa-6-battery-module-studio-logo-20260928.png",
 "offers":{"@type":"Offer",
           "url":"https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/",
           "availability":"https://schema.org/InStock"}}
```

键：`@context @type brand category description image manufacturer model name offers sku url`。**无价格**。

## 2. 那个节点由谁输出：关掉插件即消失

本地实例上逐个停用，每次都重新 curl 同一个地址：

| 插件状态 | 块数 | 谁在输出 |
|---|---|---|
| 线上代码原样（`terravolt-b2b-core` 与 `linker-ai-assistant` 都是 active） | 1 | 被删插件的输出（下面 §2.1 的值与线上逐字段相同） |
| `wp plugin deactivate terravolt-b2b-core linker-ai-assistant` | 1 | 留用的 SEO 插件（§2.2） |
| 再 `wp plugin deactivate wp-seopress-pro` | 0 | — |
| 再 `wp plugin deactivate wp-seopress` | 0 | — |

```sh
just wp t81 plugin deactivate terravolt-b2b-core linker-ai-assistant
curl -s "http://127.0.0.1:8933/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/?cbq=2"
just wp t81 plugin deactivate wp-seopress-pro
curl -s "…?cbq=3"
```

两者缺一即 0 —— 节点来自 SEO 插件本体（PRO 依赖它的基座），不是别的插件。

### 2.1 被删插件的输出（本地，与线上 §1 逐字段相同）

键：`@context @type brand category description image manufacturer model name offers sku url`；
`brand`/`manufacturer` = `GoodWe`，`category` = `Home Storage`，`offers.availability` = `InStock`，无价格。

### 2.2 留用 SEO 插件自己的输出（本地）

```json
{"@context":"https://schema.org","@type":"Product",
 "name":"GoodWe GW5.1-BAT-D-G21 (ESA battery module, 5.12 kWh)",
 "url":"http://127.0.0.1:8933/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/",
 "brand":{"@type":"Brand","name":"Linker"},
 "manufacturer":{"@type":"Organization","name":"Linker","url":"http://127.0.0.1:8933/"},
 "category":"Energy storage system"}
```

键：`@context @type brand category manufacturer name url`。没有 sku、model、image、description、offers。

## 3. 它从哪儿来：插件自己的模板库里的一个字面模板

```sh
just wp t81 eval-file /tmp/rs2.php   # post 978 的 meta
```

`post_type=seopress_schemas` 的 978 号条目，`_seopress_pro_rich_snippets_type = custom`、
`_seopress_pro_rich_snippets_custom = manual_custom_global`，规则
`filter=post_type, cond=equal, cpt=product`；`_seopress_pro_rich_snippets_custom_manual_custom_global`
是一段写死的 JSON-LD 文本，`name`/`url` 用 `%%post_title%%`、`%%post_url%%` 占位，其余是字面值 ——
即上面 §2.2 的内容。同一 CPT 另有 4 条（collection、article、local business、about/contact/faq/projects
各页），本次未动。

## 4. 结论

1. **留用的 SEO 插件确实在产品页输出 `Product` 节点**，来源是它模板库里那条写死的 Product 模板，
   而那条模板对每个产品都说 `brand`/`manufacturer` 是 "Linker"、`category` 是 "Energy storage system"，
   并且没有 sku、model、image、description、offers。
2. 线上今天真正输出的节点来自**切换要删掉的那个插件**（§2.1）——两者不等价：少的是产品的
   真实事实（厂商品牌、型号、SKU、图、文、可用性），多的是两个不成立的断言（这条产品由
   Linker 制造；它属于 "Energy storage system" 分类）。
3. 该模板活在数据库里，仓库看不见也测不到它。切换删掉旧插件之后，产品页的结构化数据就只剩它。
4. 因此按票面"补结构化数据输出"分支处理：产品页的 `Product` 节点收回 `linker-commerce`
   （`Storefront\ProductSchema`，语义与 §1 的今天一致：无价格、availability 取 Woo 原生库存、
   brand 取产品自己的 `pa_brand`、型号/SKU/图/文同样取产品自己的字段），SEO 插件模板库里那条
   Product 模板随切换退役（`just cutover schema`：`wp post update … --post_status=draft`——
   该 CPT 不支持回收站，draft 同样不再被插件的查询取到，且可以手工放回）。`/products/` 的
   CollectionPage/BreadcrumbList 与首页的 WebSite/Organization 仍由它输出，未动。

## 5. 切换后的实测（本地演练的第二遍结束时）

演练（`just cutover drill t81`）第二遍结束后的实例状态：四个旧插件已删、三个新插件已装、Polylang 已激活、
SEO 插件模板库里那条 Product 模板已是 draft。

```sh
curl -s "http://127.0.0.1:8933/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/?cbq=gap7post"
```

**1 个** `Product` 块，逐字段与线上今天那个（§1）相同——只有随主机而变的值不同（`url`、`image`、
`offers.url` 带本地主机名），`offers.availability` 相同，`brand`/`manufacturer` = `GoodWe`、`model`、
`sku`、`category`、`description` 相同，**无价格**。字段集合也相同：

`@context @type brand category description image manufacturer model name offers sku url`

德语页那一支：演练实例里 Polylang 没有任何语言、产品没有德语对象（配置德语对象的是数据迁移 #9，
演练按设计只跑它的计划），所以 `/de/produkt/…` 这一路由是线上旧插件留在 rewrite 规则里的、指向英文对象的。
线上是另一个样子——只读 GET `https://de-linker.com/de/produkt/…` 的 `<html lang="de-DE">`、
canonical 与它自己的 JSON-LD 的 `url` 都是德语地址，`name` 是德语标题。本插件的规则是"读当前页面自己的那个产品对象"，
所以页面是德语对象时，块里就是该对象的地名与名字（单元测试 `test_the_url_is_the_permalink_of_the_page_that_prints_the_block` 锁这一条）。

## 6. 这条结论对窗口的意义

- 产品页的结构化数据不再依赖任何"删掉它就会一起消失"的东西：它由本插件输出，随插件一起上线。
- 留用 SEO 插件的那条模板必须退役（由 `just cutover schema` 做，dry run 会先打印它找到的行），
  否则每个产品页会有两个互相矛盾的 `Product` 节点。
- 德语页那一半由数据迁移 #9 决定：演练里它是只读的，所以演练后的德语页面 404（见 `drill.md`）。
