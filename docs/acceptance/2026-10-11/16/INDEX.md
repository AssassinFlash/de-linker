# #16 验收证据索引（2026-10-11）

**状态口径：像素门未证，保持未证（本索引的页级数字是 2026-10-11 工作包实测，不是终局过门；见 §7 与 A3）。视觉证据已归档。
e2e 套件已在 main（`tests/e2e/`，PR #96），但本索引记录的那次运行没有跑它，不把「套件存在」写成「套件已通过」。** 本索引不含任何通过性结论。

工作树 `~/Documents/de-linker-worktrees/de-linker-t16`（分支 `t16/review-acceptance`）、
实例 t16（127.0.0.1:8924 / engine :8925 / genie :8926）。

## 1. 回归表（本 ask 内实跑）

| 门禁 | 命令 | 结果 |
|---|---|---|
| 静态与构建 | `just check` | **exit 0**（php-check ×4 项目、js-check、py-check ×5、pull::check、build::check；本轮先修 2 处 ruff-format：`services/genie/eval/judges/src/linker_judges/rubric.py`、`tools/migrate/13-media-meta.py`） |
| 测试 | `just test` | **exit 0**：linker-commerce PHPUnit 647/3258（14 skipped）、linker-i18n 135/292、linker-tools 25/113、JS 61/61 + playwright 10 passed、pytest 组 143/112/90/21+5skip/9/103 全过 |
| 页面可用性 | 17 URL × curl 200/301 | home、products、produkte、archive、produkt-kategorie、PDP（EN/DE）、cart、warenkorb、proforma-request、proforma-anfrage、my-account、mein-konto、linker-planner、linker-planer 全 200 |
| 渲染断言 | 同上 17 URL grep | `[woocommerce_`=0、`[linker_`=0、`via.placeholder`=0、字面 `&lt;p&gt;`=0（见 §4） |
| WindPress 编译 | `just windpress-compile t16` | 通过（缓存含锚类；上一轮 1791726070） |

e2e（新套件）：**本表那次没有运行。** 2026-10-11 写这句话时，`t16e/e2e-lane` 无 PR、`origin/main` 无 `tests/e2e/`。该事实已过期：套件随 PR #96 进入 main（`tests/e2e/specs/` 现有 genie、commerce、configurator、chrome、products、genie-dock、i18n），`just check` 含 `e2e-check`（类型与格式），`just e2e <instance>` 才是对运行中实例的 Playwright。本次回写没有跑 `just e2e`，所以套件仍是**未在本索引的验收里执行**，不是通过。

## 2. 视觉归档索引（截图 × 视口）

| 目录 | 内容 | 计数 |
|---|---|---|
| `working/replica-r4/` | **成对全页**：shop/archive/PDP × EN/DE × 1440/390 + ETA × EN/DE × 1440；差异可视化（红=差异）；`EVIDENCE.md`（协议、页级像素表、9 项逐项证据、块差杠杆、掩膜清单）；`tools/` 复跑脚本 | 14 对 = 28 张 + 14 张 diff |
| `working/site-wide/` | 商务五页型与配置器入口的 live|t16 对照：cart、checkout、account（EN/DE × 1440/390）+ planner、canvas（EN/DE × 1440） | 32 张 |
| `working/reference/` | 早期参考真值（live shop/archive/PDP/场景照、旧 t16 照）与 `jev-recal-run/` | 11 张 + 1 目录 |

页级像素（阈值 0，本包实测）：shop 43.4–44.5%（1440）/49.5%（390）；archive 34.1–41.6% / 46.8–54.7%；
PDP 28.7–31.1% / 67.3–69.4%；ETA 31.4%（EN）/38.3%（DE）。**未使用掩膜**（无动态值参与差异，理由见包内 §5）。

## 3. 区块级 parity（本 ask 实测，命令 `/tmp/blocks-probe.mjs`）

| 区块 | live | t16 | 判定 |
|---|---|---|---|
| 容器边距（商城） | `.container` x100 w1240，margin 100/100 | 同 | 一致 |
| 容器边距（PDP） | `.sf-container` x40 w1360，margin 40/40 | 同 | 一致 |
| 页头/页脚高 | 89 / 574 | 89 / 574 | 一致（德语页头页脚见 §5） |
| 规格展开区（签带） | `.pdp-info-tabs` x707 693×58 pad5 | 同 | 一致 |
| 规格展开区（deck 高） | 364 | **348** | **差 −16**（杠杆：panel 缺 margin-top 14px + 2px） |
| 规格行 | h49.8 pad14/16 fs13 | 同 | 一致 |
| Genie 入口（PDP 工具行） | Compare / Ask Linker Advisor / Documents | 同 | 一致 |
| Genie 入口（商城 chips） | 4 条：Filters · 0 / Batch import / Nameplate photo / Linker Advisor | **2 条：Filters / Ask Genie** | **未清**（数量与文案） |

## 4. 渲染断言表（短代码泄漏，逐 URL）

home、products、produkte、archive、produkt-kategorie、PDP EN、PDP DE、cart、warenkorb、
proforma-request、proforma-anfrage、my-account、mein-konto、linker-planner、linker-planer、
design-canvas（301）、entwurfsflache（301）——**全部 `[woocommerce_`=0、`[linker_`=0、
`via.placeholder`=0、字面 `&lt;p&gt;`=0**。

## 5. 德语五步与德语页头页脚

- ① `linker-i18n repair-partials --user=1` → “0 repairs, 1 roles left alone”。
- ② 六个 EN `lc_dynamic_template` 全 publish 且 lang=en（234/231/6564/6565/6566/6567）。
- ③ 六个 DE 孪生 publish 成组（6911/6913/6937/6939/6941/6943）；单产品孪生经
  `linker-i18n import` 更新（德语静态文案取线上实测串）。
- ④ `just windpress-compile t16` 通过（缓存含锚类）。
- ⑤ `/de/` 五页型 200 且 lang=de-DE（produkte、warenkorb、proforma-anfrage、mein-konto、DE 产品页）。
- 德语页头页脚：`working/site-wide/` 的 DE 全页截图（cart/checkout/account/planner × DE）与
  `working/replica-r4/pairs/*-de-*` 覆盖；页头/页脚高 89/574 与 live 相同（§3）。
- DE 文档 meta 逐条德语化（Datenblatt/Handbuch/Dokument/Zertifikat/Mehrsprachig），DE 三按钮行
  `Dokumente`（== live）。

## 6. eval 数字与 Jev 重校准（引自 `knowledge-index-recal.md`，本 ask 未重跑）

- `just eval`（984 问）：vectors/by product Recall@5 **52.8% → 56.2%**、keywords/by product
  **26.9% → 30.8%**、vectors/whole library 42.8% 持平；页码正确率 83.1% → 82.8%（噪声级）；
  有商品映射 878/984 → **984/984**；EN 55.1→57.5、DE 50.6→54.9。
- 两阶段重排（`index/eval/rerank.py`）：候选池页级上限 depth 50 = 84.5%、**depth 100 = 98.0%**
  （过线最小池深）、depth 200 = 99.0%。
- Jev 级联：grounded 阈值 **0.85 → 0.6** 落仓库（turns.py 带证据），离线复算 agreement 11/11、
  升级 3/11；供应商迁移到 OpenRouter 后本轮实测：Jev 调用返回校准概率（0.93）与 `usage.cost`；
  gemini-embedding-2 向量与迁移前索引向量 cosine **1.000000 ×3**。
- 运行记录：`working/reference/jev-recal-run/`。

## 7. 未解问题清单

1. **像素门未证，保持未证。** 本包页级数字（PDP 1440 28.7–31.1%、390 67.3–69.4%；shop 43.4–44.5%/49.5%；archive 34.1–41.6%/46.8–54.7%；ETA 31.4/38.3%）是 2026-10-11 工作包实测，不是一份按掩膜与批准变更分解过的终局过门包。后来的成对截图（`.scratch/t16-verdict/final4/`，12 对）也不替代该判定。不把本行改成 PASS，也不用后来的代码改动倒写成「这些百分比今天仍是页面的差」。9 项逐项证据与 5 条块差杠杆见 `working/replica-r4/EVIDENCE.md` §3/§4。
2. **e2e：套件已在 main，本索引的运行没有执行它。** 「套件未合并」是过期字样，更正见 §1。未跑 `just e2e`，无通过结论。
3. **Genie 入口（商城 chips）**：本包实测 live 4 条 vs t16 2 条。其后 main 的目录芯片是 Filters（模板按钮）+ Ask Genie（`Entries::chips_for()` 的 category 组一条）。live 4 条里的 Batch import / Nameplate photo 对应业主终裁不做的两项（面清单 GAP-11/14），不是漏建；本行不改写成像素对齐。
4. `design-canvas`/`entwurfsflache`：t16 **301 → /linker-planner/?step=roof**。这是本站自己退役的工具入口，现已在 `legacy-redirects.json` 的 `retired_tools`（5 条）里，由 `Redirects` 分发。live 当时保留独立 Site-Detail 页；是否算允许的工具页重设计，仍按允许偏差清单，不在本次改成已验收。
5. 非像素项的去向（实现存在 ≠ 像素已证）：商城家族分组现由 `[linker_catalog_families]` 按每页 24 个家族输出（`PER_PAGE_FAMILIES`）；SAJ 描述区有 `.pdp-feature` / `.pdp-overview-secondary` 的标记与样式；移动端 390 的购买栏拆分写在 `pdp.css` 的 `max-width: 860px`（`display: contents`），**终局像素判定仍待核（A4），本索引不写 PASS**；页头 chrome 位次归页头复刻线复测（A1-retest），PR #119 的功能核对通过、像素门其验收记录自己写明 NOT PASS / not certified。
6. 缩略图 srcset 为已声明 DOM 偏差项（本包记录像素已对齐）。该声明的范围是本包当时的测量，不是新的像素门证书。

## 9. 本地对比页特色图（C8，2026-10-13，t110）

对比页所需的三件商品是规格里那次线上对照用的 `?ids=6521,6522,6523`（`docs/specs/19-tool-pages.md` §1）。查的是实例 t110（`127.0.0.1:8975`，`~/de-linker-local/t110/wp.sh`），不是生产。

2026-10-13 复测（`~/de-linker-local/t110/wp.sh`，`127.0.0.1:8975`）：`wp_postmeta` 里 `_thumbnail_id` 546 行（`meta_id` 52418–52981，546 行全在这段，0 行在段外）。212 个已发布商品全部有这一行，缺行 0。不是「只补三件、其余仍缺」——那句是本记录写下时的状态，补全发生在本记录之后。这 546 行是同一次写入留下的区间：头三对是对比商品与其草稿（52418–52423），中间被 14 行别的 meta（`_linker_i18n_*`、`linker_genie_*`）隔开，主体 534 行在 52441–52974，尾部再夹 1 行后以 6 行 `_thumbnail_id` 收到 52981。

快照 `~/de-linker-data/20261011-1732/db.sql.gz` 里有 273 条 `_thumbnail_id` 绑定。273 条的 post 在本实例都在，值与快照逐条一致（0 条不符）。另外 273 行是快照里没有的 post（6575 起），不在那 273 条绑定里。三件对比商品的现值：

| post | 快照绑定 | 现值 meta_id | 读回 | 文件 |
|---|---|---|---|---|
| 6521 | 5887（快照 meta_id 45162） | 52418 | 5887 | `2026/09/goodwe-esa-6-battery-module-studio-logo-20260928.png` |
| 6522 | 5934（快照 meta_id 45199） | 52420 | 5934 | `2026/09/goodwe-bat-d-g20-plate-20260928.png` |
| 6523 | 6500（快照 meta_id 45237） | 52422 | 6500 | `2026/10/goodwe-esa-3-10kw-eha-g20-cover-20261007-01.png` |

`get_the_post_thumbnail_url` 对这三件返回上述 URL。

## 8. 复现命令

```sh
just check && just test                      # §1
just windpress-compile t16                    # §1
node working/replica-r4/tools/cap-all-pairs.mjs <out>   # §2 成对截图
python3 working/replica-r4/tools/replica-diff.py <pairs> <diffs>
node /tmp/blocks-probe.mjs <live-url> <t16-url>         # §3 区块级
# §4 断言（逐 URL）：curl -s "$U?cbq=$RANDOM" | grep -c '\[woocommerce_\|\[linker_\|via.placeholder'
```
