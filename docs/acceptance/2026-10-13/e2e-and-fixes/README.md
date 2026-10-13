# E2E 复跑与修复轮（t110，2026-10-13）

对 t110（127.0.0.1:8975）跑 `tests/e2e` 全量套件：**首轮 19 败 → 终盘 56 过 / 1 败 / 5 跳**（11.3 分钟，`npx playwright test`，7 个 spec 62 例）。本记录列每类失败的根因、修复与复验；第 3 节是唯一残留失败的完整定位。

修复提交：`23fcec4`（网格 facet + 套件契约）、`3370616`（8-engineering --verify）、`5e40d14`（Genie 改名）、`6f1a3bf`（格式化）。

## 1. 失败分类与修复

| 组 | 首轮败 | 根因 | 修复 | 复验 |
|---|---|---|---|---|
| configurator（引擎直连） | 11 | t110 的产品**工程数据从未迁移**：feed `figures: {}` / `documents: []` → 引擎 `engineering_data` 检查把全部 home 机型排除 → `status: no_candidate`、`metrics: null`（引擎自测用夹具，全绿；差异在实例数据） | `7-facts.py --write`（36 项）+ `8-engineering.py --write`（807 项），`just serve t110` 重取 feed | **17/17 过**；`8-engineering --verify`：106 产品 / 107 计划图值 / **0 差异 0 未决**；引擎响应 `status: solution`、`metrics` 在位、GW10K-ETA-G20 选中 |
| products · 过滤窄化（EN+DE） | 2 | 家族网格（`[linker_products_families]`）读 `archive_product_ids()` = **过滤前**清单，facet 只写在主查询而网格不读主查询 → `?phase=1` 264 卡=全量（线上同参 93 卡） | `ProductFilters::filtered_product_ids()`（复用 `matching()` 权威；无选择=全量、无命中=空集）；网格/计数/分页三处改读 | EN **过**：`?phase=1` 159 卡且 GW60K 归零、`?phase=3` 回正；DE 见 §3 |
| products · 访客隐价（EN+DE） | 2 | 命中串 = **运费估价**（"Germany delivery estimate: €39.00 to €90.00" / "Voraussichtliche Lieferung … 39,00 € bis 90,00 €"）——线上访客页同样展示（2026-10-13 实测 live EN grep=1），非商品价泄漏 | `lib/copy.ts` 的 `withoutFreightEstimate()`（两 spec 共用）在价格正则前剔除该句 | **过**（EN+DE） |
| commerce · 商务链（EN+DE） | 2 | 三个次因：① 登出链接已迁入页头账户下拉（账号区按线上设计），旧断言要其常显；② t110 开着 #137 测试重写（`linker_commerce_test_mail_to=tester@example.test`），spool 的 To 全被改写而套件读 spool 真实路由；③ pending 隐价断言同样撞运费估价 | ① 先开账户下拉再断言；② 套件运行期**停放**重写（`parkTestMailRewrite`）、`afterAll` 恢复操作者设置（套件地址全为 @example.test，本地实例不外发）；③ 同表豁免 | **2/2 过**（EN/DE 全程 54s×2：注册→双邮件+Bcc→pending 门→批准→价格→草稿→询盘→Proforma→PDF 下载） |
| i18n · 150 德语地址 | 1 | `/de/linker-planer/` 按业主裁定（不保留旧 slug）现为设计内 301，spec 的 retired 清单未含 | 加入 retired 清单（注释注明裁定与去向） | **过**（33.4s） |

## 2. 顺带修复

- **12-site-chrome `verify` 旧名残留**：`ProductShortcodes` 的 "Ask Linker Advisor" 按钮 + 商品页文案（`single_product.html` EN/DE "Linker Advisor/Berater startet…"）→ 全部改 Genie（`.po` msgid/msgstr 同步 + `.mo` 重编）；`just present t110` + WindPress 编译后 **verify: OK**；PDP 线上核验 "Ask Genie"×2、旧名×0。
- **`8-engineering.py --verify` 的旧路由 404**：materials 路由随 #82 改名退役，verify 双读必然 404；改为**计划侧核对为主**（feed 每个计划图值：值+单位；计划删除的必须缺席），旧路由应答时才做对照（404 记注不判败）。t110 实测 0 差异。

## 3. 残留 1 败与根因（DE 商城过滤）——独立处置项

`de: the filters narrow the product listing`：`/de/produkte/` 渲染的是旧项目的家族页（`<title>Browse Inverters…`，无过滤轨/无 sf-card）。

定位链（全部实测）：
1. `/de/produkte/` = 页面 #6863，与 #1034（EN）在 Polylang 同组；两页正文都为空——渲染来自 LiveCanvas 动态模板。
2. 我方模板 #6564（`shop-page`，meta `is_shop_page`，en）服务 EN 商城 ✓；EN 分类档案与 DE 商城落在**旧项目遗留模板**：
   - `is_archive_for_post_type_product`：#231（en）/ #6915（de），post_name `template-for-archive-for-post-type-product` / `vorlage-fur-archiv-fur-beitragstyp-produkt`，内容 = "TerraVolt Product Archive Dynamic Template v1"，**发布态**。
   - 同族遗留：`is_single_product` #234/#6913、税分类 #607/#6889、单篇 #613/#6887、搜索 #619/#6885、404 #940/#6871、博客首页 #574/#6891（全部 en+de 孪生成对、发布态）。
3. LC 的 case 顺序在 `is_shop_page` 未命中（德语侧我方无该键模板——设计使然：四类结构性模板仅英文，由 `linker-i18n` 的 `lc_modify_template_id` 过滤器在"LC 未解析到任何模板"时回退 EN 锚）之后仍会继续，`is_archive_for_post_type_product` 命中 **#6915（德语）** → `$template_id` 非空 → 过滤器按契约放行（"已解析的模板不动"）→ 旧家族页。
4. 直证：给 #6863 手动指派 `lc_use_template_of_slug=is_shop_page` 无效（该 meta 不是这条路径的权威），已回退。

**为何不就地修**：处置方向是"旧 LC 模板族退役"（草稿化或删除），但 #231 同时可能正在服务 EN/DE 的 product 分类档案页（`/product-category/…`）——草稿化前必须先确定分类档案应走哪张模板（我方尚无对应导出），否则会连带打断分类页。这是**独立工作包**（含分类档案的模板归属决策），列为下一轮首要；DE 商城测试保持红灯即该项的精确信号。

## 4. 复现

```bash
cd /Users/chesterjohn/Documents/de-linker/tests/e2e
LINKER_E2E_INSTANCE=t110 npx playwright test            # 全量
LINKER_E2E_INSTANCE=t110 npx playwright test specs/products.spec.ts -g 'filters narrow'
python3 ../../tools/migrate/8-engineering.py --wp ~/de-linker-local/t110/wp.sh --verify
python3 ../../tools/migrate/12-site-chrome.py --wp ~/de-linker-local/t110/wp.sh verify
```
