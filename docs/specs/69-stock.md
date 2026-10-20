# 69 · ERP 库存接入通道

股票入口只有一个：WooCommerce 自己的库存。外部 ERP 通过一个 REST 端点把每个 SKU 的库存推进来，站点的一切库存呈现都从 Woo 的库存读出。规格 §17 切换时端点随行上线（休眠：无密钥即拒绝一切，无调用方即无行为）。

## 是什么

- **库存唯一权威**：`_stock_quantity`、`_stock_status` 与由此同步的 `product_visibility` 词项——全部 WooCommerce 原生字段。站点对客户只说状态（有货/暂时无货），从不说数量（`woocommerce_stock_format = no_amount`，WooOptions 钉住）。
- **推送**：`POST /wp-json/linker/v1/stock`，批量行 `{sku, qty?, state?}`，逐行回答；`linker-commerce` 插件 `includes/Stock/`。
- **不携带任何衰减语义**：库存就是最后推送的值。没有过期、没有"两天不推就下架"之类的政策。
- **配置面**：`wp linker-commerce stock-key` 设置/更换/清除推送密钥（`PushKey`）；除此之外零配置。

## 端点契约（给 ERP 接入方）

### 请求

```
POST {site}/wp-json/linker/v1/stock
Content-Type: application/json
X-Linker-Stock-Key: <推送密钥>

{ "items": [
    { "sku": "GW5.1-BAT-D-G20", "qty": 12 },
    { "sku": "HS2-6K-T2-X",     "state": "outofstock" },
    { "sku": "B2-10.0-HV1",     "qty": 3, "state": "instock" }
] }
```

- `sku` 必填，字符串，与商品 `_sku` 精确匹配（区分大小写）。
- `qty` 可选，整数 ≥ 0。写入走 `wc_update_product_stock()`；**商品必须已开启库存管理**（WooCommerce 的"管理库存"），未开启的行报错 `not_stock_managed`。
- `state` 可选，`"instock"` 或 `"outofstock"`。站点没有交割概念，不接受 `onbackorder`（报错 `invalid_state`）。
  - **对开启库存管理的商品，状态由数量决定**（WooCommerce 原生规则：每次保存都从数量重推状态，管理库存的商品后台也不显示状态选择）。`state` 只有与数量推导一致时才有意义：一致的行按数量处理；矛盾的行报错 `state_overridden`（拉下架就推 `qty: 0`）。
  - **对未开启库存管理的商品，`state` 是唯一的词**（数量对它无意义），经 `wc_update_product_stock_status()` 落库。
- `qty` 与 `state` 至少给一个（否则 `missing_target`）。
- **缺货阈值（Woo 原生选项）**：`woocommerce_notify_no_stock_amount` 参与状态推导——托管商品只有 `qty > 阈值` 才有货，`qty ≤ 阈值` 即缺货（WooCommerce 默认 0：`qty: 0` 即缺货，`qty ≥ 1` 即有货）。站点不改这个选项；接入方若见到数量 ≥ 1 仍缺货，先查实例上 `wp option get woocommerce_notify_no_stock_amount` 的实值。
- 批量建议 ≤ 500 行/次；无服务器侧上限。

### 响应

`200` = 批次已受理并逐行应用（**HTTP 状态不代表每行成功**，读 `results`）：

```json
{ "batch": 1234, "applied": 2, "unchanged": 1, "errors": 1, "results": [
    { "sku": "GW5.1-BAT-D-G20", "status": "applied",   "qty": 12, "stock_status": "instock" },
    { "sku": "HS2-6K-T2-X",     "status": "unchanged", "qty": 5,  "stock_status": "instock" },
    { "sku": "XX-UNKNOWN",      "status": "error",     "code": "unknown_sku" }
] }
```

- 行状态 `applied`（已写入）/ `unchanged`（同值重推，no-op，不写库、不触发 Woo 库存动作）/ `error`（本行报错，其余行照常）。
- 错误码：`invalid_item`（行不是对象）、`invalid_sku`（sku 缺失或非字符串）、`invalid_qty`（非整数或负数）、`invalid_state`（不在两个合法值内）、`missing_target`（qty/state 全空）、`unknown_sku`（SKU 不存在——**不回滚整批**）、`not_stock_managed`（qty 需要"管理库存"）、`state_overridden`（托管库存的商品上 state 与数量推导矛盾）。
- `400`（`linker_stock_no_items`）：items 缺失/为空/非数组。
- `401`（`linker_stock_unauthorized`）：头缺失、密钥不对、或站点未设密钥。
- `500`（`linker_stock_audit_failed`）：批次已应用但审计行写不进去；按重试约定重推（幂等，安全的）。

### 鉴权

- 密钥由站点侧 WP-CLI 设置：`wp linker-commerce stock-key`（生成并打印一次）/ `--set=<key>` / `--clear`。
- 站点只存密钥的 SHA-256 哈希（选项 `linker_stock_push_key_hash`，非 autoload）；比较为 `hash_equals()` 常数时间比较两个哈希。
- **密钥不设 = 端点拒绝一切请求**（这是切换时随行上线的休眠态）。

### 幂等与重试

推送前先比对目标值与现值（qty 相同且目标状态相同）→ `unchanged` 行，零写入。请求超时/5xx 后安全重试同一批；重推即 no-op。建议 ERP 对 `500`/网络错误整批重试，对 `200 + errors` 只补错误行。

### 审计

每个被鉴权受理的批次写一行私有 post（类型 `linker_stock_batch`，复用邮件队列 `Mail\JobStore` 的持久化模式）：收到的行、逐行结果、时间（`current_time('mysql', true)`，UTC）、密钥指纹（存储哈希前 12 位，不存密钥本身）。审计行写不进 → 响应 500（宁可让 ERP 重推，不留一笔无账的写入）。

审计行有保留期：**90 天**，`Stock\Retention` 的每日 WP-Cron 事件按批删除过期行（`wp_delete_post()`，不裸 SQL；每批 100 行、每日最多 20 批）。真 ERP 按约 15 分钟一批推送 ≈ 每天百行，稳态下 90 天 ≈ 9 000 行封顶——审计表随推送增长，但不永远增长。保留天数是政策（换数字是政策变更，不是代码变更），常量出自票 #69。

## 数据怎么走（推送之后）

qty 经 `wc_update_product_stock()` 落库 → 商品 `save()` → WooCommerce 原生对齐（`validate_props`：qty > 0 → instock，否则 outofstock，站点不开 backorder）→ 库存状态变化时 Woo 自动维护 `product_visibility` 词项。此后全部由 Woo 原生机制承载：

| 面 | 行为 | 载体 |
|---|---|---|
| 商城/分类页列表 | 缺货商品从目录消失 | Woo 原生选项 `woocommerce_hide_out_of_stock_items = yes`（WooOptions 钉住；"只显示有货"业主规则）+ Woo 目录查询排除 |
| 目录侧栏计数与筛选 | 计数不含缺货品 | `CatalogFilters::archive_product_ids()` 读同一选项，排除同一词项 |
| 商品页徽标 | "In stock" / "Currently unavailable"（DE：Auf Lager / Derzeit nicht verfügbar） | `ProductView` 读 `is_in_stock()`（既有行为） |
| Genie 工具面 | `in_stock` 反映真实状态 | `ProductCommerce::of()` 读 `is_in_stock()`（不再硬编码 true） |
| Genie 库存问句 | 一个商品说出商品页的状态句（In stock / Currently unavailable；德：Auf Lager / Derzeit nicht verfügbar），不报数量。几个商品状态不一致，或问句没有点名商品，用另写的句子（文案评审 `docs/acceptance/2026-10-20/415/copy-review.md`）。卡片徽标用商品页同一对词，不再空白。查不到状态时用降级句，不说推荐商品；搜索成功但没命中商品也答降级句。整句都在问库存（或配送）时服务直接作答；同一句还问了别的（效率、数据表），模型答完整问句，状态是其中一部分 | `route.stock`（#415）。单商品状态句是商品页已有的。WHICH_PRODUCT 与 MIXED_STATUS 是本票另写的。`route.stock_beside` 是复合问句 |
| Solution draft / 询盘 | 缺货商品加不进草案（`add_to_cart` 拒绝），恢复即重新可加 | Woo 原生库存门 + 既有词汇翻译 |

## 自定义代码的穷尽证明（三件套原生优先）

自定义面只有**通道**（鉴权 + 批量 + 审计 + 密钥生命周期 + 审计行的保留清扫）；所有库存规则本身都是 Woo 原生。逐项：

1. **LC 原生 tag**：LC 的 `lc_*` 词汇是模板取数 tag，不提供任何外部写入通道。不适用。
2. **Woo 原生写入通道（wc/v3 REST，`PUT /wc/v3/products/<id>` 改 `stock_quantity`）不用**，理由：
   - 按内部商品 ID 寻址，不认 SKU；ERP 侧需先 `GET /wc/v3/products?sku=` 往返解析，批量 = N+1 请求，且无逐行结果行；
   - 无幂等 no-op 语义（同值 PUT 仍写库、仍触发动作）；
   - 无批次审计行；
   - 鉴权是 WP 用户级 consumer key/secret：一个对产品**全字段**（名称、价格、描述）有写权限的凭据，而本通道的密钥只能改库存——推送面收敛在 `wc_update_product_stock()` / `wc_update_product_stock_status()` 两个函数上，密钥泄露不扩大成价格/内容泄露；
   - 密钥生命周期（WP-CLI 设置、清除即休眠）按票据设计，wc/v3 做不到"未设密钥即拒绝一切"。
3. **WindPress**：样式管线，无数据面。不适用。
4. 与合格先例同构（B2B 价格门 = `Gating\PriceDisplay` 在源头隐藏价格：Woo 原生不做门；这里 = ERP 推送通道：Woo 原生不做带密钥的 SKU 批量库存推送）。通道内每个动作仍是 Woo 原生函数。

## 怎么算做完

- 单元：`Stock`（密钥、批次行、审计行、保留清扫、路由、模块、CLI）——`tests/php/Unit/Stock/`、`Unit/Cli/StockKeyCommandTest.php`。
- 真实夹具（集成，`tests/php/Integration/StockTest.php`，对真实实例跑）：批量推送→库存断言→错 SKU 分支不回滚→幂等重推不触发库存动作→缺货关闸/恢复开闸（草案链）→密钥门→保留清扫（过期行删、年轻行留、每日事件在表上）。
- 端到端：`just mock-erp <inst>` 对快照实例推序列，断言目录徽标、只显示有货、加车闸门；配方与脚本可重跑，收尾清除推送密钥（实例回到休眠态）。
- 全套：`just check && just test` 绿。

变更记录
- 2026-10-11 初版（票据 #69）。
- 2026-10-11 修复轮（评审必改）：审计行保留清扫（90 天、每日 cron 批量删，`Stock\Retention`）与缺货阈值（`woocommerce_notify_no_stock_amount`）说明。
- 2026-10-20（#415）：Genie 库存问句说出当前状态，不报数量。见上表 Genie 行。
- 2026-10-20（#415 评审第 2 轮）：上表原先写「句子是商品页已有的，不另写」。这只对单商品的状态句成立。没点名商品的问句（WHICH_PRODUCT）和状态不一致的句子（MIXED_STATUS）是另写的，定稿 `docs/acceptance/2026-10-20/415/copy-review.md`。`lieferbar` 写进 `route._LOGISTICS` 之后，`with_page()` 对每一个含这个词、且本身不是库存路由的本页问题都改走团队：`with_page` 见到物流词且 `route.stock` 为假就换成 `service()`。这超出 #415 的库存问句。以前本页问题里的 delivery、shipping、lieferung、versand、fracht 会这样，`lieferbar` 以前不会。配送仍不报库存，把 `lieferbar` 算进物流说得通，但这是库存问句以外的行为变化，记在这里。同轮库存词补上 stock status、Lagerstatus、unavailable、ausverkauft。配送词（含 lieferbar）仍不是库存问句。Jev 把这些库存词记成 `company_logistics_service` 时仍走库存，不进 `service()`。
- 2026-10-20（#415 评审第 3 轮）：只有整句都在问库存（或配送）时服务才直接写状态句（`route.stock_beside` 为假）。同一句还问了别的，模型答完整问句，库存状态是其中一个事实/提示。商品页上的规格问句（“Is 3-phase available?”）不因页面商品而变成库存问句。库存搜索成功但没命中商品时答降级句，不答 “No product matched.”。
