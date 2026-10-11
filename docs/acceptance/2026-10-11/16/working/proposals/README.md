# 优化提案包（2026-10-12）：复刻收口后的视觉提案

依据：业主 2026-10-11 裁定方向——"原设计不合理处（如 Technical data 左右分栏左空右挤）走'优化提案轮'：
before/after 对照 + 变更台账呈业主过目后才动，不与像素复刻混淆"。

**本轮不做任何线上语义改动、不动主分支样式**：全部"after"是本地试验——只在浏览器里注入一段
overlay 样式（脚本 `/tmp/t16-proposals.mjs`，CSS 原文见每项的"试验样式"），仓库的 WindPress 样式
（`plugins/linker-commerce/content/windpress/*.css`）一行未改。判定与采纳与否全部待业主。

对照图（同浏览器 chromium、同视口、同等待协议；before = 当前复刻态，after = 本地试验态）：
`P1_technical-1440-{before,after}.png`、`P2_pairings-1440-{before,after}.png`、
`P3_faq-1440-{before,after}.png`、`P4_specstrip-390-{before,after}.png`；逐项实测值见 `measurements.json`。

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

## 2. 兼容记录卡：固定 4×280px 列，1440 下右侧空 192px

- **位置**：产品页兼容记录段 `.pdp-pairings`（`grid-template-columns: repeat(4, 280px)`）。
- **现状（实测 1440）**：11 张卡 4 列排布，行宽 1168px，**容器 1360px，右缘空 192px**；卡高 229/210/245 不齐。
- **建议**：≥1200px 改 `repeat(auto-fill, minmax(280px, 1fr))` → 4 张卡各 **328px**、右缘对齐，
  区块高 716 → **577px**（实测）。
- **影响面**：仅该段（页高 4323 → 4184）；≤1200 不变。

## 3. Product questions（FAQ）：整行单卡，右侧半幅空置

- **位置**：产品页 FAQ 段 `.pdp-faqs`（每个问答一张 1360px 全宽卡）。
- **现状（实测 1440）**：2 条问答各占满 1360px（行高 57px），右半幅只有折叠箭头，区块 237px 高。
- **建议**：≥1200px 双列（每卡 **668px**，与描述区折叠行同宽）→ 区块 237 → **180px**（实测）。
- **影响面**：仅该段（页高 −57）；≤1200 不变。

## 4. 移动端（390）关键参数条：四列 82px、标签 10px

- **位置**：产品页 390 视口 `.pdp-spec-list`（四列 `repeat(4,1fr)`，每格 82px，标签 10px/值 14px）。
- **现状（实测 390）**：四格 82×59，10px 标签 + 14px 值在 82px 内换行，读数困难（"Usable energy"
  一类标签被挤成两行）。
- **建议**：≤480px 改两列 → 每格 **174px**、4 格分两行（41px 高），标签可读；区块 95 → 125px
  （页高 6115 → 6145）。
- **影响面**：仅 390 窄屏该条；≥481 不变。

---

### 台账汇总（位置 / 现状 / 建议 / 影响面）

| # | 位置 | 现状（实测） | 建议 | 影响面 |
|---|---|---|---|---|
| 1 | PDP `#stats` 两列 | 左列 627px 空 364px；值列 321px，备注 3 行 | ≥1200 单列 + 摘要双列；值列 654px | 该段；页高 −4px |
| 2 | PDP `.pdp-pairings` | 固定 4×280，右空 192px | `auto-fill minmax(280px,1fr)`，卡 328px | 该段；页高 −139px |
| 3 | PDP `.pdp-faqs` | 全宽单卡 1360px | ≥1200 双列 668px | 该段；页高 −57px |
| 4 | PDP 390 `.pdp-spec-list` | 4 列 82px，标签 10px | ≤480 两列 174px | 390 该条；页高 +30px |

以上均**未实施**；实施与否、以及是否连带调整其它区块，待业主裁定后另行开票。
