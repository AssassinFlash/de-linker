# 欠账①：PDP 上 SEOPress 的重复 Product 节点

2026-10-14，t110（`http://127.0.0.1:8975`）。修复前对照：`seopress-schema-before.txt`。修复后对照：`seopress-schema-after.txt`。

## 现象

`/product/saj-ats1-t63-a/` 的 head 里有两个 `application/ld+json` 块，都是 `@type: Product`。

- 第一块：`brand` 与 `manufacturer` 都是 `Linker`，`category` 是 `Energy storage system`，没有 sku、model、图、availability。
- 第二块：`brand` `SAJ`，`sku` `DLK-SAJ-ATS1T63A`，`availability` `InStock`。这是 `plugins/linker-commerce/includes/Storefront/ProductSchema.php` 发的，保留。

## 来源

不是 SEOPress 的自动 WooCommerce Product 设置，也不是 option 里的一条开关。`seopress_pro_option_name` 里与 schema 有关的只有总开关：

```
just wp t110 -- option get seopress_pro_option_name --format=json
seopress_rich_snippets_enable = 1
```

总开关开着是对的：它同时放行文章、关于、联系这些模板，那些没有错。

真正发第一块的是 SEOPress PRO 的 schema 库，一篇已发布的 `seopress_schemas` 文章。

发射路径（实例上的插件，未改）：

1. `wp-seopress-pro/inc/functions/options.php:117` 把 `seopress_pro_rich_snippets` 挂在 `wp_head` 优先级 2。
2. 该函数在非后台请求里 `require` `options-automatic-rich-snippets.php`。
3. 文件顶部要求 `getRichSnippetEnable() === '1'`（即上面那个总开关），并且当前是 singular。
4. `options-automatic-rich-snippets.php:345-360` 用 `WP_Query` 取 `post_type=seopress_schemas`（默认 `post_status=publish`），对每篇调用 `seopress_is_content_valid_for_schemas()`。
5. 规则存在 `_seopress_pro_rich_snippets_rules`。匹配后，type 为 `custom` 的行从 `_seopress_pro_rich_snippets_custom_manual_custom_global` 读出整段 JSON-LD 原文，经 `seopress_automatic_rich_snippets_custom_option()` 替换 `%%post_title%%` / `%%post_url%%` 后打印。

t110 上的行（`just wp t110 -- eval` 列出全部 `seopress_schemas`）：

| id | 标题 | status | type | 规则 | body 含 Product |
|---|---|---|---|---|---|
| 978 | TerraVolt Product Entity Schema | publish | custom | `post_type equal product` | 是 |
| 979 | TerraVolt Blog Article Schema | publish | articles | `post_type equal post` | 否 |
| 1009 | TerraVolt About Page Schema | publish | custom | `postId equal 862` | 否 |
| 1010 | TerraVolt Contact Page Schema | publish | custom | `postId equal 28` | 否 |
| 1012 | TerraVolt FAQ Download Schema | publish | custom | `postId equal 932` | 否 |
| 1013 | TerraVolt Projects Collection Schema | publish | custom | `postId equal 693` | 否 |

978 的 body 原文：

```json
{
  "@type": "Product",
  "name": "%%post_title%%",
  "brand": {"@type": "Brand", "name": "Linker"},
  "manufacturer": {"@type": "Organization", "name": "Linker"},
  "category": "Energy storage system"
}
```

规则是文章类型等于 `product`，所以每一篇商品详情页都打上这一块，品牌一律写成站点名。

## 改法

把 978 设为草稿，不删。插件自己的查询只读已发布行，草稿就是它的关闭开关，后台也能手工发回去。总开关不动，其余五行不动：它们不是 Product，也没有别的发射器替代。

迁移：`tools/migrate/69-seopress-schema.py`（plan / apply [--write] / verify）。登记在 `tools/cutover/src/linker_cutover/plan.py` 的 `SCHEMA_MIGRATION`（与 `SCHEMA_RETIRED` 同一处），元组结构与 `MIGRATIONS` 的条目相同：`Migration("69-seopress-schema.py", subcommand=("apply",))`，`--write` 由调用方追加在子命令之后。

没有追加进 `MIGRATIONS`。规格 17 §4 点名的就是那四个条目，`tools/cutover/tests/test_plan.py` 的 `test_the_migrations_are_the_ones_spec_17_names_and_in_order` 对这个元组做全等断言。追加会让该测试失败，而那个测试文件不在本线可改的路径里。切换窗口自己的 `schema` 步（`steps.retire_stale_schema`）仍是窗口里退役这条模板的实现；`SCHEMA_MIGRATION` 是窗口之外、实例上可重跑的那一份，并且会拒绝它不认识的 Product 模板，而不是一律草稿。

取舍：关掉之后 PDP 上不再有 SEOPress 的那一块。那一块没有 sku、没有真实品牌，没有需要保留的字段。首页的 `WebSite` / `Organization` 不走这条 schema 库（`wp-seopress/src/Actions/Front/Schemas/PrintHeadJsonSchema.php` 只在首页、且只发 organization），不受影响。

## 重跑

`tools/checks/product-schema.py` 对一个实例的商品详情页做两件事：数 JSON-LD 里的 Product 节点（含 `@graph`，解析失败算失败不算零），并断言这一个节点的 brand 不是站点名、带 sku。站点名默认从首页 `WebSite` 节点读，`--site-name` 可覆盖。

```
python3 tools/checks/product-schema.py [--base http://127.0.0.1:8975]
python3 tools/checks/product-schema.py --product /product/<slug>/ [--product /product/<other>/]
```

不给 `--product` 时，从公开 Store API 取第一篇在售商品。`--base` 默认 `http://127.0.0.1:8975`（t110）。

退出码：0 每篇都干净；1 有断言失败；2 实例没应答，或找不到商品页、读不出站点名。

README 的命令表不在本线可改的路径里（另一条线在用仓库其余文件），所以用法写在这里和脚本开头的 docstring，不写进 README。
