# #333 对抗测试矩阵 · 账号价格库存批 — 方法与证据

- 票：#333（地图 #329）。性质：只测不修。产品代码零改动。
- 日期：2026-10-19（本地电池、复查、线上问句冒烟）。
- 逐条判定、最小复现、分层归因在票上的中文评论。本文件只写怎么跑、跑在哪、证据在哪、哪些机器判定后来改了。

## 环境

- 实例 `c333`：WordPress `http://127.0.0.1:9184`，engine `:9185`，Genie `:9186`。数据库 `linker_c333`。
- 数据：线上快照 `20261019-1715`（`just pull load c333 latest`，212 商品、2756 附件，`ok: true`）。
- `just pull load c333 --live-code` 被工具拒绝（`linker-pull`：检出插件的实例不能用 `--live-code`）。本实例是线上数据库 + 线上主题/uploads/许可插件 + 本检出插件。插件 `linker-commerce`、`linker-i18n`、`linker-tools` 是指向本工作树的符号链接。
- 索引：`~/de-linker-data/index/builds/20261018T173840Z/index.sqlite`。
- 模型通道未动。本地轮次走实例自己的 Genie。
- 账号（只在证据目录，不入仓库）：访客无登录；pending 用户 43、restricted 用户 44、approved 用户 45。应用密码与登录 cookie 在 `~/de-linker-data/campaign-333/secrets.json`（mode 600）。RFQ 是商品模式 `tv_b2b_product_mode=rfq_only`（EN 1957 / DE 孪生 6800），不是账号状态。
- 标价商品：EN 4107 / DE 6628，SKU `DLK-SAJ-H210KT3`，常规价 1680。RFQ 商品存储价 33250，页面与能力面不对未获批账号展示这个数。
- 邮件：`~/de-linker-local/c333/mail/` 全程 0 个文件。`pre_wp_mail` 在建单和确认卡脚本里短路。没有调用联系路由，没有 POST 匹配的询盘摘要。
- 跑完后的商品：4107 / 6628 为 `1680` + `instock`。1957 / 6800 回到快照原状 `onbackorder`（库存阶段一度把它们推成 `instock`，复查时写回）。库存推送密钥已清。

## 驱动

| 文件 | 作用 |
|---|---|
| `harness/grade.py` | 纯判定：门句、金额、库存词、降级声明、确认卡、最终计数。单测锁这里。 |
| `harness/run_battery.py` | 本地电池：能力、令牌、页面、Store API、询盘列表、状态过渡、Genie 轮次、库存推送、登出。`--production` 只对公开 Genie 发问句。`--self-test` 跑金额/数量正则，并核对已记录日志的计入行。 |
| `harness/catalog.php` | 快照、恢复、HPOS 删单、读回、`C333Mint`。没有文件级 `const`，没有副作用。 |
| `harness/inquiry_flow.php` | 本地确认卡。读卡片、改价、再读、只 POST 旧摘要。匹配的摘要从不 POST。`wp eval-file` 会在方法内部 include 这个文件，文件级 `const` 会在编译期失败，所以价格和用户 id 是普通变量。关机钩子恢复价格，并删掉这次打开的会话帖。 |
| `harness/stock_edges.php` | 库存推送、缺货后的能力/页面/Store/轮次、onbackorder 徽标。一个 PHP 进程里做完，关机钩子恢复目录和推送密钥。 |
| `harness/price_turn.php` | 把标价改成 1701，已批准首页问一次，再恢复。1701 不是目录价。 |
| `harness/orders.php` | 三个账号各一张无行项目的询盘单，令牌读 `inquiry-status`，然后 `WC_Order::delete(true)` 并读回。 |
| `harness/transition.php` | 本地顾客 `c333-transition`，从待审到拒绝再回到批准。不碰用户 43/44/45。 |
| `harness/followup.py` | 第一次机器判定里需要重测的几条：查询串令牌、对比表价格行、已批准商品页、空会话上的对比/配置器/改价轮次、onbackorder 徽标。改价轮次走 `price_turn.php`。结尾的删单走 HPOS。 |
| `harness/tests/` | `pytest`。夹具 `recorded-verdicts.json` 只有 id、判定，以及 `inquiry-flow` 的那句失败备注。 |

证据：`~/de-linker-data/campaign-333/evidence/cases.jsonl`（每条：账号态、请求、meta、blocks、价格/库存、是否用了旧值、耗时、verdict）。线上在 `evidence/production.jsonl`。确认卡原文在 `evidence/inquiry-flow.raw.txt`。

## 怎么重跑

```bash
just up c333 && just pull load c333 latest && just serve c333
# 账号脚本不在仓库里。沿用证据目录里已有的 accounts.json，或按 NOTES 的用户 id 重建。
cd docs/research/2026-10-20-campaign-333/harness
uv run --locked pytest
uv run --locked python run_battery.py --self-test
uv run --locked python run_battery.py
uv run --locked python followup.py
uv run --locked python run_battery.py --production
```

`--from-phase` 可以接着跑后面的阶段。跳过 `turns` 时登出阶段读不到本轮的会话 cookie。

线上冒烟只 POST `https://de-linker.com/wp-json/linker-ai/v1/genie/turn`，然后 DELETE 本轮会话。不要对线上 POST 询盘或联系。

## 机器判定里后来改掉的 11 条

jsonl 是追加的。同 id 的第一行仍是初跑结论，复查行以 `retest-` 开头，或在初跑失败之后又写了一条同名通过行。计入票面的是复查结论。

| 初跑 id | 初跑为什么报缺陷 | 复查 |
|---|---|---|
| `token-query-only-get-product` | 令牌被塞进 `input[X-Linker-User-Context]`，能力模式返回 400，空行对不上访客句 | 令牌作为查询参数、不进 `input[]`。HTTP 200，正文没有价格。`retest-token-query-only` 通过 |
| `page-visitor-compare-en/de` | `visible_text()` 丢掉标签属性。访客价格句在登录链接的 `aria-label` 里 | 价格行含门句，不含金额。`retest-page-visitor-compare-*` 通过 |
| `page-approved-priced-en/de` | 能力行 `€1,680.00` / `1.680,00 €` 不是页面可见文本的子串（货币符号在单独的 span，德语用 NBSP） | 页面有 `1,680.00` / `1.680,00`，没有访客门句。通过 |
| `turn-approved-en-compare`、`turn-approved-en-config`、`turn-approved-after-price-change` | 夹具只送一条新用户消息。这句话和线程开头相同，`#373` 把它当成短快照，代理 409 `linker_genie_turn_conflict`。壳发送的是整段线程 | 删掉用户 45 的会话后再问。对比页与配置器卡片 `€1,680.00`，正文无金额。改价后的卡片 `€1,701.00`，不是 `1,680`，正文无金额 |
| `inquiry-flow` | 文件级 `const` 在 `wp eval-file` 里编译失败，WordPress 只打印 critical error | 去掉 `const` 后确认卡跑通。见下两条 |
| `price-change-confirmation`（复查第一版） | 评分器找子串 `1701`，卡片写的是 `1,701.00` | 原文：卡片变为 `€1,701.00`，旧摘要 POST 409 `linker_genie_inquiry_changed`，订单数不变。后一条同名记录为通过 |
| `stock-backorder-product-1957/6800` | 读数发生在恢复推送把这两件写成 `instock` 之后，请求里仍写着 `onbackorder` | 写回 `onbackorder` 后再读。`in_stock=true`，页面 "In stock" / "Auf Lager"。与 `is_in_stock()` 一致，规格 69 的徽标读的就是这个 |

确认卡改库存：商品缺货时 `add_to_cart` 为 false，卡片行为空，旧摘要 409，没有新订单。规格 69 写明缺货加不进草案。

## 计入的结果

jsonl 是追加的。`summarize()` 取每个用例 id 的最后一行。`retest-*` 替换它点名的初跑 id，一对只计一次。`inquiry-flow` 在判定为缺陷且备注含 `flow script failed` 时不计：那是 `wp eval-file` 的文件级 `const` 编译失败，确认卡两行是重跑。

按这个规则，已记录的 122 行、120 个 id 计入 **108：101 通过，7 缺陷**。打印的那一行是 `counted 108: 101 pass, 7 defect`。7 条缺陷用例：

- `store-visitor-de`（`retest-store-visitor-de-links` 仍是缺陷，只计一次）
- `store-pending-de`
- `store-restricted-de`
- `store-approved-de`
- `inquiry-own-pending`
- `inquiry-own-restricted`
- `turn-visitor-en-stock-after-out`

`summary.json` 里旧的 107/18 把每一行都加总了，作废。`uv run pytest` 用 `tests/fixtures/recorded-verdicts.json` 锁住上面那一行。下次电池把新探针追加进去之后，计数跟着每个 id 的最后一行走。

- 轮次耗时（22 条含复查）：p50 3.6s，最长 11.51s（`turn-approved-en-stock`）。
- 线上 4 个问句都是 200，卡片或正文没有金额。会话 7568–7571 已删，见下。

## 数字从哪来

写在 `harness/grade.py` 开头。标价 EN 4107 / DE 6628，常规价 1680。RFQ EN 1957 / DE 6800，存储价 33250。都是快照 `20261019-1715` 上的 SKU。`TURN_TIMEOUT` 180 是夹具上限：壳 60 秒，`UserContext::TTL` 是它的两倍，`prices.LOOKUP_DEADLINE` 50 秒。未知用户 999999 在快照里没有这一行。金额正则认这两种目录价的英语分组、德语分组和裸整数。数量正则认「数字 + 单位」或 qty 标签。`in stock` 不是数量。它也是 `not in stock` 的子串，所以库存词先删掉否定短语，再找肯定短语。

## D1、D2 这轮证据到哪为止

D1。`store-*-de` 判的是 Store API 返回的永久链接字符串。`lang=de` 且 `include=4107,1957` 时，链接仍是 `/product/...`，没有 `/de/`。这轮没有打开德语 Genie 卡片，也没有点卡片上的链接。#413 仍是产品票。这些用例的备注带 `D1_NOTE`。`store-*-de-twin` 直接查 DE 帖 6628 和 6800，看孪生自己的链接。卡片复现不在这轮。

D2。`orders.php` 建的单没有行项目，`set_total` 写成目录价。`InquiryStatus::item` 把 `$order->get_total()` 写进列表。这证明能力层把这个总数交了出去。客户看得见的询盘列表可能在别处被挡住。#414 的范围是这个能力。approved 看见 1680 是该看见的。备注带 `D2_NOTE`。

## 清理

订单在 HPOS 的 `wc_orders`，不在 posts。`wp_delete_post` 删不掉。`catalog.php` 的 `c333_delete_orders` 走 `WC_Order::delete(true)`，再按 id 用 `wc_get_order` 读回。还在的 id 记成 `inquiry-orders-cleanup` 缺陷。会话帖 `linker_conversation` 仍用 `wp_delete_post`。

会改目录或账号的脚本各在一个进程里做完。进探针之前注册 `register_shutdown_function`。Python 被 SIGKILL 之后，这个 PHP 进程自己退出，钩子把进脚本时的快照写回去。`main` 的 `finally` 再按 `accounts.json` 强制写回已知目录：标价 1680 且 instock，RFQ onbackorder，推送密钥清除。读回对不上，这次运行失败。

## 这轮补上的探针

伪造查询串。规格 13 要的是 401。`token-forged-query-string` 仍对只接受 POST 的 turn 路由发 GET，带有效令牌，404 且不漏金额算通过。已记录的那一行因此不变。新用例 `token-forged-query-string-401` 请求 `GET /wp-json/wp/v2/users/me?x=/wp-abilities/v1/abilities/linker/get-product/run`，头里是有效的 `X-Linker-User-Context`。只接受状态 401，且正文没有金额。和 `GeniePricesTest::test_the_token_is_bound_to_its_abilities` 是同一条。

DE 孪生。6628 和 6800 以前几乎不按 id 查。能力矩阵和 Store API 各加 `-twin` 行：`lang=de`，id 就是孪生帖。`lang=de` 配英语 id 的旧探针还在。

状态过渡。`transition.php` 在本地建 `c333-transition`，角色 customer。不碰用户 43/44/45。邮件用 `pre_wp_mail` 短路。pending 的 cookie 有效，价格关着。`Approval::set` 到 approved 之后不重新登录，同一张 cookie 仍有效，下一次请求看得到价格。再设为 rejected，要带理由。cookie 失效。`wp_authenticate` 的错误码是 `linker_approval_rejected`。强制 `wp_set_current_user` 仍看不见价格。`CommerceState::visitor_reason` 没有 rejected 分支，已登录的拒绝账号读的是受限那句。再设回 approved 之后，`wp_authenticate` 成功，价格打开。然后删用户，按登录名读回，确认没有了。密码不打印。关机钩子按登录名再删一次。

缺货回答。`grade_stock_after_out` 先看 `meta.fallback`。走了回落、正文里却没有规格 13 的降级句（`template.DEGRADED`），判缺陷。备注写明没有降级声明。已记录的 D3 回答是 "Here are matching products from our range."，`fallback=true`，按这条会判缺陷。确认卡除了状态 409，还要错误码 `linker_genie_inquiry_changed`。缺货时 `added_after_stock` 必须为假，卡片 `lines` 必须是空数组。

## 测试

`harness/` 是 `package = false` 的 uv 项目。`pytest` 锁 `grade.py` 里的判定。这四步都过了，`justfile` 的 `py_projects` 才把这个目录算进去：

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy .
uv run --locked pytest
```

`mypy` 不检查 `run_battery.py` 和 `followup.py`。这两份是无类型的编排，负责子进程和 HTTP。判定在 `grade.py`。

## 线上冒烟留下的会话

`run_production` 第一次用逗号切 `Set-Cookie`。`Expires` 里的逗号把 cookie 切碎，DELETE 没有带上 `linker_conversation`。四条访客会话留在线上。问的是价格和库存，没有询盘，没有联系方式。

2026-10-20 用主机上的 WP-CLI 删掉了。删之前 `wp post get` 读到的是这些帖（站点时区，作者 0，类型 `linker_conversation`，状态 private，评论 0，正文空）：

| ID | 站点时间 | GMT | 标题 | slug |
|---|---|---|---|---|
| 7568 | 2026-10-19 23:53:52 | 15:53:52 | What is the net price of the SAJ H2-10K-T3? | genie-382 |
| 7569 | 2026-10-19 23:54:02 | 15:54:02 | Was kostet der SAJ H2-10K-T3? | genie-383 |
| 7570 | 2026-10-19 23:54:14 | 15:54:14 | Is the SAJ H2-10K-T3 in stock? | genie-384 |
| 7571 | 2026-10-19 23:54:28 | 15:54:28 | What is the price of the GoodWe GW208.9-BAT-LCD-G10? | genie-385 |

原文备份在 `~/de-linker-data/campaign-333/evidence/conversations-7568-7571-before.jsonl`，不入仓库。

未登录的 DELETE，删之前和删之后都是 404，正文 `linker_genie_conversation` / "Unknown conversation."。没有 cookie 时 `may_use` 失败，帖子还在也是这个 404。未登录的 GET 是 `rest_no_route`，这条路由只有 DELETE。帖子不在的证据是 `wp post get` 退出码 1：`Could not find the post with ID …`。2026-10-20 复查，四条仍是这个结果。

夹具已改为 `HTTPMessage.get_all("Set-Cookie")`。本地用修好的读取删掉会话 7456，DELETE 200，响应里没有欧元。没有为了补删再向线上发一轮问句。
