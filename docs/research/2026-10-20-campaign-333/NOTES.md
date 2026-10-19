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
| `harness/run_battery.py` | 本地电池：能力、令牌、页面、Store API、询盘列表、Genie 轮次、库存推送、登出。`--production` 只对公开 Genie 发问句。`--self-test` 只跑金额/数量正则。 |
| `harness/inquiry_flow.php` | 本地确认卡。读卡片、改价、再读、只 POST 旧摘要。匹配的摘要从不 POST。`wp eval-file` 会在方法内部 include 这个文件，文件级 `const` 会在编译期失败，所以价格和用户 id 是普通变量。 |
| `harness/followup.py` | 第一次机器判定里需要重测的几条：查询串令牌、对比表价格行、已批准商品页、空会话上的对比/配置器/改价轮次、onbackorder 徽标。 |

证据：`~/de-linker-data/campaign-333/evidence/cases.jsonl`（每条：账号态、请求、meta、blocks、价格/库存、是否用了旧值、耗时、verdict）。线上在 `evidence/production.jsonl`。确认卡原文在 `evidence/inquiry-flow.raw.txt`。

## 怎么重跑

```bash
just up c333 && just pull load c333 latest && just serve c333
# 账号脚本不在仓库里。沿用证据目录里已有的 accounts.json，或按 NOTES 的用户 id 重建。
python3 docs/research/2026-10-20-campaign-333/harness/run_battery.py --self-test
python3 docs/research/2026-10-20-campaign-333/harness/run_battery.py
python3 docs/research/2026-10-20-campaign-333/harness/followup.py
python3 docs/research/2026-10-20-campaign-333/harness/run_battery.py --production
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

- 本地：101 通过，7 条缺陷用例，3 个缺陷。7 条是同一处德语永久链接的 4 个账号态，加上待审/受限询盘金额 2 条，加上缺货回答 1 条。
- 轮次耗时（22 条含复查）：p50 3.6s，最长 11.51s（`turn-approved-en-stock`）。
- 线上 4 个问句都是 200，卡片或正文没有金额。DELETE 详见票面：第一次冒烟的四条访客会话没有删掉。

## 线上冒烟留下的会话

`run_production` 第一次用逗号切 `Set-Cookie`。`Expires` 里的逗号把 cookie 切碎，DELETE 没有带上 `linker_conversation`，`/conversations/7568`、`7569`、`7570`、`7571` 都是 404。这四条是这次问句开的访客会话，问的是价格和库存，没有询盘、没有联系方式。

夹具已改为 `HTTPMessage.get_all("Set-Cookie")`。本地用修好的读取删掉会话 7456，DELETE 200，响应里没有欧元。没有为了补删再向线上发一轮问句。
