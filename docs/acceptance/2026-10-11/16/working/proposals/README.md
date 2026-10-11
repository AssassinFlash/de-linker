# 优化提案包（2026-10-12）：复刻收口后的视觉提案

依据：业主 2026-10-11 裁定方向——"原设计不合理处（如 Technical data 左右分栏左空右挤）走'优化提案轮'：
before/after 对照 + 变更台账呈业主过目后才动，不与像素复刻混淆"。

**本轮不做任何线上语义改动、不动主分支样式**：全部"after"是本地试验——只在浏览器里注入一段
overlay 样式（脚本 `/tmp/t16-proposals.mjs`，CSS 原文见每项的"试验样式"），仓库的 WindPress 样式
（`plugins/linker-commerce/content/windpress/*.css`）一行未改。判定与采纳与否全部待业主。

对照图（同浏览器 chromium、同视口、同等待协议；before = 当前复刻态，after = 本地试验态）：
`P1_technical-1440-{before,after}.png`、`P2_pairings-1440-{before,after}.png`、
`P3_faq-1440-{before,after}.png`、`P4_specstrip-390-{before,after}.png`；逐项实测值见 `measurements.json`。

**实施记录（业主 2026-10-11 深夜批准全部四项，2026-10-12 实施）：** 四项已全部落 WindPress 层
`plugins/linker-commerce/content/windpress/pdp.css`，实施提交 **`f7f10bc`**（#16 三段）；实例 t16
经 `just present t16` 装卷 + `just windpress-compile t16` 重编译（"anchor classes present"，
独立复核 `missing_anchor_classes` 返回 `[]`），随后按与本节同一浏览器/视口/等待协议重测：
四项 after 数值与本节提案数字一致（值列 **654px** / 首卡 **328px** / FAQ **668px 双列** /
390 格 **174px**），1440 页高 4323→**4123**（=−4−139−57，三项之和）、390 页高 6115→**6145**。
数据 `measurements-implemented.json`、脚本 `tools/pdp-proposals-implemented.mjs`（另含 1100/481
断点守卫：before=after，规则未越界）。**实施后本页与 live 的这四处差异为业主裁定豁免，不计复刻失败。**

---

## 1. Technical data 左右分栏：左标题下大块空白，参数全挤在右列（业主点名）

- **位置**：产品页 `#stats` 段（`.pdp-stats-layout` = `minmax(0,1fr) 693px` 两列；标题在左列，
  分页签参数表在右列）。
- **现状（实测 1440）**：左列 627px 只有一行标题，其下是 364px 高的空白；右列 693px 承载 3 个
  页签 + 表格，参数**值列只有 321px**，备注被迫折成 3 行（`dd` 420/654 → 换行）。
- **建议**：≥1200px 时该段改为**单列**（标题在上、参数表占满 1360px），左侧空列消失、值列从
  321px 变为 **654px**（实测），长备注不再三行。
- **影响面**：仅 `#stats` 段（页高 4323 → 4319，−4px）；不动其它段、不动移动端（≤1200 保持现状）。
- **试验样式**：
  ```css
  @media (min-width:1200px){
    #tv-storefront-pdp .pdp-stats-layout{grid-template-columns:minmax(0,1fr);gap:24px}
    #tv-storefront-pdp .pdp-stats-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 40px}
  }
  ```
- **已实施（业主 2026-10-11 批准）**，提交 `f7f10bc`；实施后实测：值列（`.pdp-stat-row dd`）
  **654px**（前 321）、`#stats` 段高 505→**501**、摘要列 `display:grid` 660px×2（该电池页摘要为空，
  列宽取计算样式 `660px 660px`）——与提案 after 逐项一致（页高 −4）。

## 2. 兼容记录卡：固定 4×280px 列，1440 下右侧空 192px

- **位置**：产品页兼容记录段 `.pdp-pairings`（`grid-template-columns: repeat(4, 280px)`）。
- **现状（实测 1440）**：11 张卡 4 列排布，行宽 1168px，**容器 1360px，右缘空 192px**；卡高 229/210/245 不齐。
- **建议**：≥1200px 改 `repeat(auto-fill, minmax(280px, 1fr))` → 4 张卡各 **328px**、右缘对齐，
  区块高 716 → **577px**（实测）。
- **影响面**：仅该段（页高 4323 → 4184）；≤1200 不变。
- **已实施（业主 2026-10-11 批准）**，提交 `f7f10bc`；实施后实测：首卡 **328px**（前 280）、
  区块高 716→**577**、11 卡 4 列右缘对齐（列 328px×4）——页高 −139，与提案一致。

## 3. Product questions（FAQ）：整行单卡，右侧半幅空置

- **位置**：产品页 FAQ 段 `.pdp-faqs`（每个问答一张 1360px 全宽卡）。
- **现状（实测 1440）**：2 条问答各占满 1360px（行高 57px），右半幅只有折叠箭头，区块 237px 高。
- **建议**：≥1200px 双列（每卡 **668px**，与描述区折叠行同宽）→ 区块 237 → **180px**（实测）。
- **影响面**：仅该段（页高 −57）；≤1200 不变。
- **已实施（业主 2026-10-11 批准）**，提交 `f7f10bc`；实施后实测：两列 **668px + 668px**
  （第二卡 x=732，行高 57）、区块 237→**180**——页高 −57，与提案一致。

## 4. 移动端（390）关键参数条：四列 82px、标签 10px

- **位置**：产品页 390 视口 `.pdp-spec-list`（四列 `repeat(4,1fr)`，每格 82px，标签 10px/值 14px）。
- **现状（实测 390）**：四格 82×59，10px 标签 + 14px 值在 82px 内换行，读数困难（"Usable energy"
  一类标签被挤成两行）。
- **建议**：≤480px 改两列 → 每格 **174px**、4 格分两行（41px 高），标签可读；区块 95 → 125px
  （页高 6115 → 6145）。
- **影响面**：仅 390 窄屏该条；≥481 不变。
- **已实施（业主 2026-10-11 批准）**，提交 `f7f10bc`；实施后实测（390）：4 格两列 **174px**、
  格高 59→**40**、区块 95→**125**、页高 6115→**6145**；481px 守卫 before=after，未越界。

---

### 台账汇总（位置 / 现状 / 建议 / 影响面）

| # | 位置 | 现状（实测） | 建议 | 影响面 | 状态 |
|---|---|---|---|---|---|
| 1 | PDP `#stats` 两列 | 左列 627px 空 364px；值列 321px，备注 3 行 | ≥1200 单列 + 摘要双列；值列 654px | 该段；页高 −4px | **已实施（业主 2026-10-11 批准）`f7f10bc`**；实测值列 654px |
| 2 | PDP `.pdp-pairings` | 固定 4×280，右空 192px | `auto-fill minmax(280px,1fr)`，卡 328px | 该段；页高 −139px | **已实施（业主 2026-10-11 批准）`f7f10bc`**；实测卡 328px |
| 3 | PDP `.pdp-faqs` | 全宽单卡 1360px | ≥1200 双列 668px | 该段；页高 −57px | **已实施（业主 2026-10-11 批准）`f7f10bc`**；实测 668px 双列 |
| 4 | PDP 390 `.pdp-spec-list` | 4 列 82px，标签 10px | ≤480 两列 174px | 390 该条；页高 +30px | **已实施（业主 2026-10-11 批准）`f7f10bc`**；实测 174px |

以上四项**均已实施**（业主 2026-10-11 批准，提交 `f7f10bc`）；实际落点与提案数字对照见上文各项
"已实施"行与 `measurements-implemented.json`。连带区块未调整（提案未涉及）。

---

### 实施样式原文（落 `plugins/linker-commerce/content/windpress/pdp.css`，提交 `f7f10bc`）

与试验完全同文（试验态即试验脚本 `/tmp/t16-proposals.mjs` 注入的样式）：

```css
@media (min-width: 1200px) {
	#tv-storefront-pdp .pdp-stats-layout {
		grid-template-columns: minmax(0, 1fr);
		gap: 24px;
	}

	#tv-storefront-pdp .pdp-stats-summary {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0 40px;
	}

	#tv-storefront-pdp .pdp-pairings {
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
	}

	#tv-storefront-pdp .pdp-faqs {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0 24px;
	}

	#tv-storefront-pdp .pdp-faqs > .pdp-section-title {
		grid-column: 1 / -1;
	}
}

@media (max-width: 480px) {
	body:has(#tv-storefront-pdp) #tv-storefront-pdp .pdp-spec-list {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
```

---

## 5. 侧栏工具卡（rail-help）：文案来自 #12 裁定改名，卡高 +20.1px 是其结果（不修，登记）

- **位置**：目录页筛选栏（`.rail-help`）——live 卡文案 "Send a Project to Linker / Open Project Brief"，
  t16 为 "Plan with the Solution Configurator / Open the Solution Configurator"。
- **来源**：文案是 **#12 对抗评审批准的工具改名定稿**（业主工具命名裁定：
  `docs/acceptance/2026-10-10/12/copy-review.md`；实现见 `CatalogShortcodes.php` 的 rail-help 段，
  EN/DE 均入 .po/.pot 并 msgfmt 重编）。
- **实测（2026-10-12，1440，`.rail-help` 卡）**：live 210×**178.7** @(100, 1846.9) 标题一行；
  t16 210×**198.8** @(100, 1846.9) 标题两行——**卡高 +20.1px**，卡的位置逐值相同；标题由一行
  变两行（"Plan with the Solution Configurator" 折行）是改名文案本身的排版结果，不是复刻缺陷。
- **判定**：**登记为裁定改名，非复刻失败；不改回 live 文案**。像素对照中该卡的差异
  （标题两行、卡高 +20.1px）为业主裁定豁免；若业主日后改回 "Send a Project to Linker"，
  改 .po 串 + rail-help 段即可复位。
- **证据**：`.scratch/t16-verdict/final4/crops/sidebar-3way.png`（live | t16 三栏对照）、
  `.scratch/t16-verdict/final4/analysis/landmarks.json`（live 卡 178.7px 与 t16 卡几何）。
