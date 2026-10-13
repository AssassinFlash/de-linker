# 复刻收口证据包 — 工作态（2026-10-11）

**本包结论口径：复刻未达像素门。** 判决第 3 轮仍有 9 项未过，逐项证据见 §3；
本包不是验收证据，是主会话做升级决策的依据（按 #16「验收路径卫生」第 1 条，
本包位于 `working/` 目录）。

工作树：`~/Documents/de-linker-worktrees/de-linker-t16`，分支 `t16/review-acceptance`，
尖端 `2d2632f`（已推送 origin，PR #62 OPEN，未合并）。实例：t16（127.0.0.1:8924，
engine :8925，genie :8926）。

## 1. 协议与方法

- 成对全页截图：live|t16，同一 chromium（`plugins/linker-tools` 的 playwright
  channel=chromium）、同视口（1440×900 / 390×844）、同等待协议（domcontentloaded +
  2.5s + 走页促懒加载 + 回顶 + 1.5s）、每 URL 带 `?cbq=` 破缓存。脚本：
  `/tmp/cap-all-pairs.mjs`（本包可直接复跑，见 §7）。
- 页型与参考页：shop（/products/、/de/produkte/）、archive（/product-category/inverters/、
  /de/produkt-kategorie/wechselrichter/）、PDP（电池页 goodwe-gw5-1-bat-d-g21…，EN+DE）。
- 像素统计：`python3 .scratch/t16-closure/replica-diff.py <pairs> <out>`——逐像素
  RGB 最大通道差 >0 即计差异（阈值 0，符合「1 像素都算」）；同时输出差异可视化图
  （红=差异，浅灰=相同）与 `summary.json`。
- 区域口径：对每个被判项，先在该区域内搜索**全局最佳整数位移**（dx∈[-2,2]，
  dy∈[-140,140]），再统计残差像素——即评审所说的「最佳整数对齐」。脚本：
  `/tmp/frac-probe.mjs`、`/tmp/levers-probe.mjs`、`.scratch/t16-closure/r2-facts.mjs`。

## 2. 页级像素表（live|t16 成对全页）

| 页型 | 语言/视口 | live 页高 | t16 页高 | 差异像素 | 差异占比 |
|---|---|---|---|---|---|
| shop | EN 1440 | 9238 | 6582 | 4116159 | **43.43%** |
| shop | EN 390 | 12304 | 8478 | 1638269 | **49.55%** |
| shop | DE 1440 | 9238 | 6611 | 4236195 | **44.5%** |
| shop | DE 390 | 12642 | 8679 | 1676062 | **49.52%** |
| archive | EN 1440 | 9264 | 6494 | 3187237 | **34.08%** |
| archive | EN 390 | 12322 | 8472 | 1545306 | **46.77%** |
| archive | DE 1440 | 9264 | 6540 | 3915064 | **41.57%** |
| archive | DE 390 | 12671 | 8687 | 1852194 | **54.67%** |
| pdp | EN 1440 | 4300 | 4377 | 1922838 | **31.05%** |
| pdp | EN 390 | 6068 | 7185 | 1593599 | **67.34%** |
| pdp | DE 1440 | 4432 | 4480 | 1831819 | **28.7%** |
| pdp | DE 390 | 6187 | 7453 | 1673626 | **69.36%** |

| eta | EN 1440 | 4847 | 4947 | 2193487 | **31.43%** |
| eta | DE 1440 | 4941 | 5044 | 2724425 | **38.29%** |

（ETA 页为 ②/⑨ 的参照页，另加 1440 EN+DE 一对。）

成对原图：`pairs/`；差异可视化（红=差异像素）：`diffs/<pair>-diff.png`；逐对 JSON：`diffs/summary.json`。

## 3. 判决第 3 轮未过项逐项证据

> 每条含：评审判定 → 我方实测（live | t16）→ 机制状态（已定位/假说/未决）。

### ① 兼容记录区块卡片级残差（评审：首卡 4.21%，标题区 697/19600）
- 计数与内容已对齐：`<a class="pdp-pairing"`=11、名称 11 条逐字同（EN+DE）、chip 11=11。
- 卡几何：卡 280×**229.23**、卡图盒 88×100（pad 12、bg `rgb(240,244,239)`）、chip 999px
  bg `rgb(240,244,239)` —— 与 live 逐值相同（`.scratch/t16-closure/r2-facts.mjs` 输出）。
- 我方区域残差（本包 `pdp-en-1440` 成对图、最佳整数对齐）：首卡 **4.55%**
  （2954/64960）、整段 **2.20%**（23418/1066800，与评审 4.21%/同量级）。
- 机制状态：**假说未验证**——唯一可量化的差异是纵向分数偏移（t16 卡 y=2861.45、
  live 2798.58，对齐后余 ~0.13px 亚像素）；字号/字重/字体文件/图片字节均已核对相同。
  未做的验证实验：把该区块上游各块高度钉到与 live 相同的分数值后再复测（见 §4 杠杆）。

### ② 文档引用（ETA）DE meta 与区域残差（评审：DE meta 仍英文；docs 区 3.15%）
- DE meta 已逐条德语化且与 live 同序：`Datenblatt · PDF · EN / Datenblatt · PDF · DE /
  Handbuch · PDF · EN / Handbuch · PDF · DE / Dokument · PDF · Mehrsprachig /
  Zertifikat · PDF · Mehrsprachig / Zertifikat · PDF · EN / Zertifikat · PDF · EN /
  Zertifikat · PDF · Mehrsprachig ×3 / Dokument · PDF · EN / Dokument · PDF · DE`
  （`document_kind_label()` 经 gettext，`Multilingual`→`Mehrsprachig`）。
- 计数：t16 `pdp-doc`=13 == live；`.pdp-doc-meta` 我实测 live=19=t16=19（评审所记 30 未复现）。
- 区域残差（本包）：电池页 docs 区 **0.48%**（2238/466200）；**ETA 页 docs 区 0.57%**
  （6788/1201200，最佳对齐 dy=11）——评审第 3 轮所测 3.15% 为修复前状态。
- 机制状态：文案与网格已定位并修复；剩余为与 ⑨ 同源的字形/位移残差。

### ③ 缩略图 srcset 候选（评审：t16 加载原图 vs live 300px 变体；区域 5.26%）
- 已改为加载与 live 相同的文件：t16 `currentSrc` = `…-300x225.png` / `…-300x208.png`
  == live（`/tmp/r2b-probe.mjs` 输出）；四个文件在双方同 URL 下字节相同（已核）。
- 机制（受控实验证据）：`/tmp/tag-test.mjs`、`/tmp/cand-test2.mjs` —— 同一 `<img>` 标记
  在本页无论属性顺序都解析到最大候选；而在 **live 页面**上 JS 注入的同样标记也取原图。
  故采取「钉 src 为该文件 + 去掉该 img 的 srcset」——**已声明的 DOM 偏差项**（像素优先）。
- 区域残差：待本轮成对图复测（上一轮 5.26%）。

### ④ 关键参数行字体度量（评审：dt 13 vs 14、dd 600 vs 500；区域 7.31%）
- 已修：`.pdp-spec-list dt` 14px、`dd` font-weight 500（`stat dd` 亦 500）。
- 复测（本包）：hero 参数表区域在最佳整数对齐下 **0/73692 像素差（0.00%）**。

### ⑤ 三按钮行 DE 文案（评审：第三按钮 "Unterlagen" vs live "Dokumente"）
- 已修：.po `msgid "Documents"` 条目改为 `Dokumente`（此前遗留 `Unterlagen`）；
  DE 实测 = `Vergleichen / Linker Berater fragen / Dokumente` == live。EN 侧相位差 0。

### ⑥ Plan-with 行单像素（评审：最佳对齐下 1/17759，x1396/y906，ΔRGB=1）
- 度量已对齐：`.pdp-project-check` 413.34×43.25、summary h41.3（list-item、pad 12/16）、
  h2 379×17 @15px/lh17.25，文字色像素在场。配送句逐字相同。
- 机制状态：**未复测**该单点坐标（如实登记）；其邻域残差与 §4 的分数偏移同源假说。

### ⑦ 描述区区域残差（评审：overview 3.68%、benefits 0.60%、discloses 2.25%）
- 我方复测（本包，最佳整数对齐）：overview **3.68%**（与评审同）、benefits **0.72%**、
  折叠行 **1.72%**；度量（面板 1360×276 / r28 / pad40 / kicker / 米色底 / grid 668×668）不变。
- 机制状态：**假说未验证**（同 ①：上游 +24px 的块差使对齐后余分数偏移；见 §4 杠杆 1）。

### ⑧ 技术数据分页签（评审：deck 16px、panel 2px、dd 字重、infodeck 12.81%；
ETA 页缺摘要与 32→28 statrow）
- ETA 摘要列已建：live 的 `.pdp-stats-summary` 内容即快照 `stats_claim`
  （label=kicker、cards=4 行、title/body=About these specifications）；GW10K-ETA 页
  statrows **32 = 32**（此前 28）。
- `stat dd` 字重已改 500。仍余：deck 高 **347.69 vs 363.69**（差 16 = panel 缺
  `margin-top:14px` + 2px 内高）、panel 289.69 vs 291.69；infodeck 区域残差本包复测
  **15.85%**（39879/251559，最佳对齐 dy=16；上一轮区域口径测得 11.41%）待下一轮。
- 本条为第 3 轮 9 项中体积最大的一项。

### ⑨ 文档区字重与区域残差（评审：grow font-weight 500 vs 400；docs 区 2.75%/3.15%）
- 已修 `.pdp-doc .grow` font-weight 400；本包复测：电池页 docs 区 **0.48%**、
  ETA 页 docs 区 **0.57%**。

## 4. 已定位的块差杠杆表（整页偏移的来源，全部 live|t16 实测）

| # | 选择器 | 属性 | live | t16 | 差 | 来源 |
|---|---|---|---|---|---|---|
| 1 | `.pdp-section-nav` | margin-top | 0px | **24px** | +24 | 旧卷 CSS 的 margin 未被我方规则覆盖 |
| 2 | `.pdp-faqs .pdp-disclose` | margin-bottom | 0px | **24px** | +48（2 行） | `.pdp-disclose` 的 24px 需只作用于描述区折叠行 |
| 3 | `.pdp-info-panel`（spec deck） | margin-top | **14px** | 0px | −16（含 2px 内高） | 我方 pdp.css 未设 |
| 4 | `.pdp-avail` | height | 100.69 | **104.69** | +4 | 注释行盒 |
| 5 | `.pdp-benefits` | height | 97.38 | **98.38** | +1 | 文本行盒舍入 |

净效果：整页高 4376 vs 4299（+77）；这些块差经位移在整页差分中被放大为 31%。
（命令：`node /tmp/levers-probe.mjs <live> <t16>`；输出见本包 §7 复现命令。）

## 5. 掩膜清单

**本包未使用任何掩膜。** 三点对照图（页头页脚/主体/Genie 坞）内未发现动态值参与差异：
购物车计数两侧均为 0、页脚年份相同、Genie 坞默认收起、无时间戳/随机元素渲染。
所有差异均为结构性（块高差→位移、文本亚像素渲染），若主会话需要掩膜口径，
可对「Genie 坞区」（首次交互后才渲染）声明为可选掩膜项——本轮实测其不参与差异。

## 6. 未决与不属于像素的缺口

2026-10-13 按项注明去向。本包仍是工作态，不是终局像素证书；下面「已有实现」只说明 main 里现在有对应代码，不改写本节上面的页级差。

1. **e2e 套件**：写本包时套件在并行线、无 PR，本阶段没有运行。该句已过期——套件随 PR #96 进入 main（`tests/e2e/`）。本包没有补跑 `just e2e`，所以这里仍无套件通过记录。当时那笔自跑非绿（"the cascade judge agrees with the deterministic checks = False"）是并行线自己的 report，不是本次复跑。
2. **商城家族分组 / 搜索芯片**：本包实测 live 65 家族、每页 24，t16 是 104 商品、每页 16。main 现由 `[linker_catalog_families]` 按每页 24 个家族输出。目录芯片现为 Filters + Ask Genie；live 4 条里的 Batch import / Nameplate photo 是业主终裁不做的两项，不是漏建。族级 facts 序变体本包没有新测量。
3. **SAJ 描述区**：本包记的是 highlights 表、`.pdp-overview-secondary`、`.pdp-feature` 尺寸未对齐。main 已有这两组标记与样式（`CatalogShortcodes` 的 feature 块、`storefront.css` / `pdp.css`）。尺寸是否与 live 一致，本包没有复测，不销。
4. **移动端（390）——待 A4 判定，不在本包销账。** 本包实测：live 用 `display:contents` 拆购买栏并走 2 列栅格，t16 单列，页高差约 1,100px。其后 `pdp.css` 在 `max-width: 860px` 写入了同一拆法（`.pdp-purchase` / `.pdp-buy-inner` 为 `display: contents`，注释指向本条）。代码落上不等于终局像素门已判：A4 的范围是列表页 390 的终局判定仍未核，本条的 PDP 390 页高差同样没有新的掩膜外零差证据。不写 PASS，也不把本包的 1,100px 说成今天仍测得的差。
5. **页头 chrome——归 A1-retest，不在本包销账。** 本包记的是搜索/购物车/账户/EN-DE 与 live 不同位。页头复刻由 `fix/header-live-sync`（PR #119，已合并）承接；其验收记录写明功能核对通过、零像素对照 NOT PASS / not certified。本包不把页头改判为已对齐。
6. 缩略图 img 的 srcset 为已知 DOM 偏差（本包当时记像素已对齐，§3 ③）。范围限于那次测量。

## 7. 复现命令

```sh
本包自带全部脚本（`tools/`，与运行时用的同一份拷贝）：

```sh
# 成对全页截图：live|t16 × {shop,archive,pdp} × {EN,DE} × {1440,390}（+ ETA 1440）
node tools/cap-all-pairs.mjs <出图目录>
node tools/cap-eta.mjs <出图目录>

# 像素统计 + 差异可视化（红=差异）+ summary.json（阈值 0）
python3 tools/replica-diff.py <出图目录> <diff 出图目录>

# 逐项区域残差（最佳整数对齐）与块差杠杆
python3 tools/r4-regions.py                  # 本包 pdp/eta 的区域残差
node tools/frac-probe.mjs <live-url> <t16-url>
node tools/levers-probe.mjs <live-url> <t16-url>
node tools/r2-facts.mjs                      # 配对卡/缩略图/文档卡/Plan-with/目录卡
node tools/review-facts.mjs                  # 页型级事实（含 --proto-accent/compare 计数）
```

成对原图见 `pairs/`（14 对 = 28 张），差异图见 `diffs/`（14 张 + `summary.json`）。
