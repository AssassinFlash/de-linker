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

## 5. 第二轮（同日晚，接业主追问后继续）

首份报告里"后续入口"不是客套：一类是真缺陷、一类是修复已落地但证据待重拍。本轮完成真缺陷类的主体：

| 项 | 根因（全部实测） | 修复 | 复验 |
|---|---|---|---|
| DE 商城/分类页渲染旧家族页 | present 按"元键认领"复用旧模板做容器：档案的 EN 锚 = #231（`is_archive_for_post_type_product`）已被写成我方导出；**德语孪生 #6915 从未被写**（`DE_FILES` 只列了单商品）→ 德语档案请求解析到 TerraVolt 内容 | `DE_FILES` 增 `is_archive_for_post_type_product => de/archive_product`（德语导出文件，字面词 Filter/Produktaktionen/Produktfilter，其余为自翻译短代码） | DE 商城与分类页：TerraVolt 20→0、网格/过滤轨/德语 Filter 在位；products spec **6/6 过**（含此前唯一红灯） |
| DE 卡片不声明 AC 功率 | `Materials::card_facts` 直接读传入商品（DE 记录无图值 `_tv_b2b_figures`），而 `SelectionFacts` 经 i18n 的 `linker_commerce_facts_product_id` 映射到英文记录——两条读取路径不一致 | card_facts 走同一权威做孪生映射（同 `has_filter` 守卫；无语言层时自问自答） | DE 卡出现 `AC-Nennleistung 30 kW` 等行，**与线上德语卡逐字相同**（2026-10-13 live 实测） |
| 测试词表过期 | products spec 的功率正则只认 `AC power\|AC-Leistung`；线上与本站德语卡实际用 `AC-Nennleistung`（`AC-Leistung` 是过滤轨表单的标签） | 正则扩为 `AC power\|AC-Nennleistung\|AC-Leistung`（注释注明线上实测） | 6/6 |
| 旧 404 模板（#940/#6871）供旧标记 | 旧 404 模板内容内嵌旧插件字体/CSS 引用（terravolt-b2b-core，资产仍在所以是 200 而非死链）；主题自带 404 更干净 | t110 与 t109 均将 #940（+t110 的 #6871）转草稿 | 404 页 h1 "Page not found"、terravolt 引用 0；可见文本无旧品牌（404/搜索/博客三面实测） |

**本轮终盘 E2E**：56 过 / 1 败（genie R2=德语轮"三相机推荐"单轮把配对电池当卡片给出——LLM 抖动，单独复跑 32.8s 即过，非数据回归）/ 5 跳。products 组 6/6、commerce 链 EN/DE、configurator 17/17、i18n 150 地址全绿。

**仍在册的残留**（同一"旧 LC 模板族与实例平价"工作包）：
- 旧模板族其它成员（#607/#6889 税分类、#613/#6887 单篇、#619/#6885 搜索、#574/#6891 博客首页）仍供旧标记；三面可见内容已实测干净，但页面仍引用旧插件资产（t109 DE 商城 12 处、t110 商城各 1 处）。归属 = 切换迁移步（#17 暂停中）：随旧插件移除一并停用/退役。
- t109 的 DE 目录更深一层（其构建早于 present 全量装配：DE 商城无网格）——预览实例，建议随下次 `just reset` 以新工具链重建。
- 视觉验收重拍（188 对静态基线 + PDP/配置器/Genie 修复面）：工具齐备（`.scratch/freshdiff-full/capture.mjs` + `freshdiff.py`），尚未重跑。

## 6. 复现（补充）

```bash
# DE 档案孪生与卡片事实的实例侧验证
curl -s 'http://127.0.0.1:8975/de/produkte/?kw_min=15&cbq=x' | grep -c 'AC-Nennleistung'
curl -s 'http://127.0.0.1:8975/de/produkt-kategorie/wechselrichter/?cbq=x' | grep -ci terravolt   # 期望 0
just wp t110 eval '$p=wc_get_product((int)pll_get_post(4107,"de")); echo json_encode(array_column(\Linker\Commerce\Products\Materials::card_facts($p,4),"key"));'  # 期望以 ac_power 开头
```
