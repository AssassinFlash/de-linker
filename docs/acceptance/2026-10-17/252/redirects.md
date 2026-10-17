# SEOPress 81 条重定向提示 · 逐条判断（#252）

来源：线上选项 `seopress_can_post_redirect`（2026-10-17 只读取出，81 条：74 条删除、7 条改 slug）。日期由提示 id 换算（PHP `uniqid` 的前 8 位十六进制是秒）。“线上状态”是 2026-10-17 对 `https://de-linker.com<旧地址>` 不跟随跳转的 GET 结果。“进过 sitemap”查的是 `~/de-linker-data/` 里 10-10 至 10-17 每份快照所存的线上 sitemap。

判断规则：已经 301 或地址仍在服务的，提示已经过时，清除；404 且有对等货架的，建 301，去向与旧地址表里同系列的兄弟条目相同；404 且没有对等页面的，保持 404（没有对等内容的重定向会被搜索引擎当作软 404），清除提示；德语博客分类的地址归 #254。

| 结论 | 条数 |
|---|---|
| 已有 301，清除 | 43 |
| 保持 404，清除 | 23 |
| 新建 301 | 6 |
| 交 #254，清除 | 5 |
| 地址仍在，清除 | 4 |
| 合计 | 81 |

| 日期 | 类型 | 旧地址 | 新地址 | 线上状态 | 进过 sitemap | 判断 |
|---|---|---|---|---|---|---|
| 2026-07-02 | delete | `/product/terravolt-b5/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-h3/` |  | 301 | 否 | 已 301 → `/product-category/inverters/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-h6/` |  | 301 | 否 | 已 301 → `/product-category/inverters/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-h8-3p/` |  | 404 | 否 | **建 301** → `/product-category/inverters/`（本分支 legacy-redirects.json） |
| 2026-07-02 | delete | `/product/terravolt-h10-3p/` |  | 404 | 否 | **建 301** → `/product-category/inverters/`（本分支 legacy-redirects.json） |
| 2026-07-02 | delete | `/product/terravolt-h12-3p/` |  | 404 | 否 | **建 301** → `/product-category/inverters/`（本分支 legacy-redirects.json） |
| 2026-07-02 | delete | `/product/terravolt-h15-3p/` |  | 404 | 否 | **建 301** → `/product-category/inverters/`（本分支 legacy-redirects.json） |
| 2026-07-02 | delete | `/product/terravolt-h20-3p/` |  | 404 | 否 | **建 301** → `/product-category/inverters/`（本分支 legacy-redirects.json） |
| 2026-07-02 | delete | `/product/terravolt-b8/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-b8-outdoor/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-b16/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-b20/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-one-5/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-one-10/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-one-25/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-one-3p/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-one-plus/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-one-ci/` |  | 301 | 否 | 已 301 → `/product-category/commercial-storage/all-in-one-systems/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-link-lite/` |  | 301 | 否 | 已 301 → `/product-category/ems-monitoring/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-link-pro/` |  | 301 | 否 | 已 301 → `/product-category/ems-monitoring/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-link-100/` |  | 301 | 否 | 已 301 → `/product-category/ems-monitoring/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-meter/` |  | 301 | 否 | 已 301 → `/product-category/accessories/meters-current-transformers/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-stick/` |  | 301 | 否 | 已 301 → `/product-category/ems-monitoring/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-cloud/` |  | 301 | 否 | 已 301 → `/product-category/ems-monitoring/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-02 | delete | `/product/terravolt-h5/` |  | 301 | 否 | 已 301 → `/product-category/inverters/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product/goodwe-lx-u5-4-l/` |  | 404 | 否 | **建 301** → `/product-category/home-storage/`（本分支 legacy-redirects.json） |
| 2026-07-10 | delete | `/product-category/ci-ac-coupled-storage/` |  | 301 | 否 | 已 301 → `/product-category/commercial-storage/all-in-one-systems/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/ci-battery-systems/` |  | 301 | 否 | 已 301 → `/product-category/commercial-storage/battery-systems/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/ci-hybrid-storage/` |  | 301 | 否 | 已 301 → `/product-category/commercial-storage/all-in-one-systems/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/monitoring-accessories/` |  | 301 | 否 | 已 301 → `/product-category/ems-monitoring/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/residential-storage-catalog/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/all-in-one-ess/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/battery-storage/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/hybrid-inverters/` |  | 301 | 否 | 已 301 → `/product-category/inverters/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-10 | delete | `/product-category/monitoring-accessories/` |  | 301 | 否 | 已 301 → `/product-category/ems-monitoring/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-11 | delete | `/product-category/commercial-storage/commercial-all-in-one/` |  | 301 | 否 | 已 301 → `/product-category/commercial-storage/all-in-one-systems/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-11 | delete | `/product-category/commercial-storage/commercial-battery-systems/` |  | 301 | 否 | 已 301 → `/product-category/commercial-storage/battery-systems/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-11 | delete | `/product-category/commercial-storage/` |  | 200 | 是 | 地址仍在服务（同 slug 分类删后重建）；清除提示 |
| 2026-07-11 | delete | `/product-category/inverters/` |  | 200 | 是 | 地址仍在服务（同 slug 分类删后重建）；清除提示 |
| 2026-07-11 | delete | `/product-category/home-storage/` |  | 200 | 是 | 地址仍在服务（同 slug 分类删后重建）；清除提示 |
| 2026-07-11 | delete | `/product-category/accessories/` |  | 200 | 是 | 地址仍在服务（同 slug 分类删后重建）；清除提示 |
| 2026-07-11 | delete | `/product-category/balcony-power/` |  | 301 | 否 | 已 301 → `/products/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-11 | delete | `/product-category/ev-charging/` |  | 301 | 否 | 已 301 → `/product-category/ev-chargers/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-11 | delete | `/product-category/residential-storage/res-ev-chargers/` |  | 301 | 否 | 已 301 → `/product-category/ev-chargers/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/product-category/all-in-one-ess/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/product-category/balcony-power-and-storage/` |  | 301 | 否 | 已 301 → `/products/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/product-category/battery-storage/` |  | 301 | 否 | 已 301 → `/product-category/home-storage/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/product-category/energy-management-and-smart-meters/` |  | 301 | 否 | 已 301 → `/product-category/accessories/meters-current-transformers/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/product-category/hybrid-inverters/` |  | 301 | 否 | 已 301 → `/product-category/inverters/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/product-category/microinverters/` |  | 301 | 否 | 已 301 → `/products/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/product-category/solar-modules/` |  | 301 | 否 | 已 301 → `/products/`（linker-tools 旧地址表）；清除提示 |
| 2026-07-17 | delete | `/brand/aiko-solar/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/byd/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/das-solar/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/foxess/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/fronius/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/hoymiles/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/huasun-energy/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/kostal/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/msmd/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/sma/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/solaredge/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/sungrow/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/tenka/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-07-17 | delete | `/brand/zendure/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-08-10 | delete | `/product-category/pv-modules/` |  | 404 | 否 | 业主 2026-10-02：产品分类里没有光伏组件，没有对等页面；保持 404；清除提示 |
| 2026-08-10 | delete | `/product-category/pv-modules/` |  | 404 | 否 | 业主 2026-10-02：产品分类里没有光伏组件，没有对等页面；保持 404；清除提示 |
| 2026-09-01 | delete | `/brand/staubli-test-047/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-09-01 | delete | `/brand/staeubli/` |  | 404 | 否 | 不经营的品牌或重复/测试词项，没有对等页面；保持 404；清除提示 |
| 2026-10-08 | update | `/checkout/` | `/proforma-request/` | 301 | 否 | 已 301 → `/proforma-request/`（linker-tools 旧地址表）；清除提示 |
| 2026-10-13 | delete | `/pa_series/b/` |  | 404 | 否 | 旧 TerraVolt 系列属性的归档地址（系列现用 /series/），没有对等页面；保持 404；清除提示 |
| 2026-10-13 | delete | `/pa_series/h/` |  | 404 | 否 | 旧 TerraVolt 系列属性的归档地址（系列现用 /series/），没有对等页面；保持 404；清除提示 |
| 2026-10-13 | delete | `/pa_series/one/` |  | 404 | 否 | 旧 TerraVolt 系列属性的归档地址（系列现用 /series/），没有对等页面；保持 404；清除提示 |
| 2026-10-13 | delete | `/pa_series/link/` |  | 404 | 否 | 旧 TerraVolt 系列属性的归档地址（系列现用 /series/），没有对等页面；保持 404；清除提示 |
| 2026-10-13 | delete | `/category/uncategorized-de/` |  | 404 | 否 | 空的默认博客分类，没有对等页面；保持 404；清除提示 |
| 2026-10-13 | update | `/linker-advisor/` | `/genie/` | 301 | 是 | 已 301 → `/genie/`（linker-tools 旧地址表）；清除提示 |
| 2026-10-15 | update | `/de/category/anwendungen/` | `/de/category/applications-blog/` | 404 | 否 | 德语地址归 #254（德语地址德语专属；现址 `/de/category/applications-blog/` 含英文段，可能改回原德语 slug）；此处不建 301，免得与 #254 的改动成环；清除提示 |
| 2026-10-15 | update | `/de/category/batteriespeicher/` | `/de/category/battery-storage-blog/` | 404 | 否 | 德语地址归 #254（德语地址德语专属；现址 `/de/category/battery-storage-blog/` 含英文段，可能改回原德语 slug）；此处不建 301，免得与 #254 的改动成环；清除提示 |
| 2026-10-15 | update | `/de/category/installation-inbetriebnahme/` | `/de/category/installation-commissioning/` | 404 | 否 | 德语地址归 #254（德语地址德语专属；现址 `/de/category/installation-commissioning/` 含英文段，可能改回原德语 slug）；此处不建 301，免得与 #254 的改动成环；清除提示 |
| 2026-10-15 | update | `/de/category/uberwachung-energiemanagement/` | `/de/category/monitoring-energy-management/` | 404 | 否 | 德语地址归 #254（德语地址德语专属；现址 `/de/category/monitoring-energy-management/` 含英文段，可能改回原德语 slug）；此处不建 301，免得与 #254 的改动成环；清除提示 |
| 2026-10-15 | update | `/de/category/systemauslegung/` | `/de/category/system-design/` | 404 | 否 | 德语地址归 #254（德语地址德语专属；现址 `/de/category/system-design/` 含英文段，可能改回原德语 slug）；此处不建 301，免得与 #254 的改动成环；清除提示 |
