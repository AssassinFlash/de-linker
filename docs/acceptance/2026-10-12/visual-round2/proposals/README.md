# 视觉优化二轮提案包（2026-10-12）：复刻收口后扩展到更多层面

## 三栏对比图（业主过目用，2026-10-12 补）

每张图左→右三栏：**当前**（t16 复刻态，即本目录 before）｜**线上**（de-linker.com 同视口同取景的只读截图）｜**改良后**（本目录 after，浏览器 overlay，未进仓库样式）。栏间 2px 分隔线，栏顶标注「当前 / 线上 / 改良后」加提案编号与一句话。图在 `../comparisons/CMP_<编号>.png`，另拷一份到 `owner-review-20261011/`。宽图按比例缩到三栏总宽 ≤2400px。

线上截图协议与本包一致：chromium、1440×900 / 390×844、`?cbq=` 破缓存、只读 GET。账户两栏线上进不去（见下表注），按「线上无此元素」放灰底。

| # | 三栏图 | 一句话 | 影响面（实测数字） |
|---|---|---|---|
| A1 | `CMP_A1.png` | 商城/分类容器 ≥1360px 放宽到 1360，与产品页对齐 | 容器 `[100,1240]`→`[40,1360]`；卡 488→548；身份列 446→506；仅 ≥1360，1200 守卫未越界 |
| A2 | `CMP_A2.png` | 分类筛选轨钉在页头下，滚动全程可改筛选 | 滚动 y=2000 时轨从视口 y=−1569 钉到 y=104、可视高 772；仅 ≥861 左轨 |
| B1 | `CMP_B1.png` | 账户导航从裸链接串改为 230px 卡片菜单 | 导航 72→279 高、链接 18→36px 行、卡 230×279；1440 与 390 同一修复 |
| B2 | `CMP_B2.png` | 询盘行 View 白底描边，Request again 主色实底 | 两键同灰 `rgb(233,230,237)` → View 白底 / Request again `rgb(12,127,115)`；仅该表动作格 |
| C1 | `CMP_C1.png` | 产品页隐藏关闭态坞条，只留 50×50 圆钮 | 标题条 418×50→0，三枚动作键不再被压；仅产品页关闭态 |
| C2 | `CMP_C2.png` | ≤860px 点开助手后给出底部对话卡 | 面板 0×0 → 350×317；仅 ≤860 |
| D1 | `CMP_D1.png` | 设计报告 label/value ≥1200px 改两列 | 七块合计 1275→1008（−267），整页 5387→5120；仅 ≥1200，1100 守卫未越界 |
| D2 | `CMP_D2.png` | 配置器步骤条 ≤860px 钉在页头下 | 滚动 y=2384 时步骤条从视口 y=−2111 钉到 y=89；仅 ≤860 |
| E1 | `CMP_E1.png` | 页脚 Solutions 三张卡改三列一行 | 卡 392→258，列表高 150→70；仅 ≥1024 该面板 |

线上侧实测（2026-10-12，只读 GET）：

- A1/A2/E1：线上与「当前」同构（容器 1240、筛选轨滚走、Solutions 2+1），改良后的差异一眼可辨。
- C1：线上产品页没有新栈 Genie 坞（`.linker-genie` 不存在），右下是旧助手圆钮；购买盒三键完整可见，没有 420×50 白条。提案针对的是复刻栈，不是今天的线上。
- C2：线上商城移动端没有 "Ask Genie"，对应控件是 "Linker Advisor"。点开后旧助手以整屏抽屉出现（390×796），不是「点了没反应」。提案修的是复刻栈 `display:none` 把挂载树藏掉的问题。
- D1/D2：线上 `/linker-planner/` 仍是旧 Planner（`#qcfg-root`），没有 `.linker-steps`，也没有 `dl.linker-report__rows`。两列报告与 sticky 步骤条在线上都无对应元素；中栏放的是同 URL 同视口的旧页面，供对照「改的是哪一套」。
- B1/B2：线上 `/my-account/` 未登录即登录墙，`/my-account/inquiries/` 返回 404。账户导航与询盘行按钮登录前不存在，中栏按规则放灰底 +「线上无此元素」。

**缺陷登记项已修，不放图。** 产品页 "Ask Linker Advisor" 派发旧事件名 `lia:ask`、新栈无人监听的问题，已在 `78591ab` 修复（PDP ask buttons dispatch the Genie dock's `linker-genie-ask` event，#106）。本对比轮不再为它出图。

---

依据：业主 2026-10-12 预批方向——在复刻收口（`5b25ba4`）之后，把"原设计不合理处走优化提案轮"的
做法扩展到商城/分类、账户区、Genie 坞与对话卡、配置器三屏、页头页脚五个层面；本轮**只出提案包**，
不改任何仓库样式，全部"after"为浏览器 overlay 试验，采纳与否全部待业主。

**本轮仓库样式零改动**：`plugins/*/content/**` 一行未动。全部"after"只是试验脚本在浏览器里注入的
一段 overlay 样式（每项的"试验样式"原文见下；脚本 `/tmp/r2-trials.mjs` 与 `/tmp/r2-trials-fixups.mjs`，
同轮运行产出 `measurements.json`）。PR 只含本目录的 README、PNG 与 measurements.json。

对照协议与首轮一致（docs/acceptance/2026-10-11/16/working/proposals）：同一 chromium、同视口
（1440×900 与 390×844）、同等待协议（fonts.ready + 逐屏滚动 + 图片 decode 后截图）；
before = 当前复刻态，after = 注入试验样式后。

## 实例与准备（t105）

- `just up t105` + `just pull load t105 20261010-0033 --live-code`（装入 live 树与快照库；
  live 树里的旧 linker-i18n 目录移出插件目录后，`just up` 重建三个检出符号链接并激活
  linker-commerce/linker-i18n/linker-tools，评审站插件清单与其余 t 实例一致：ACF、classic-editor、
  LiveCanvas、Polylang、Redis、SEOPress、WindPress、Woo + 三个新插件）。
- `wp linker-i18n setup --assign`、`wp linker-commerce present`（模板 unchanged 10）、
  `just windpress-compile t105`（"anchor classes present"）。工程数据快照已带
  （`8-engineering.py`：0 to apply, 803 done）。
- `just serve t105`（engine :8958 / Genie :8959；本机进程加
  `LINKER_ENGINE_CORS_ORIGINS=http://127.0.0.1:8954`，否则配置器的浏览器请求被 CORS 拦截——
  这是本地服务的 env，不是仓库改动）。
- 配置器页面挂载沿用 t14 的实例本地 mu-plugin stand-in（`100-t14-configurator-mount.php`
  复制为 `100-t105-configurator-mount.php`，注释注明 never deployed）：快照库里的
  /linker-planner/ 页面内容仍是旧应用的挂载，新配置器挂载点由该 stand-in 打印——与 #14
  视觉验收同一条路径。
- 登录视图用快照客户 customer-3（50 张询盘，账单地址已填），本地口令 + 一次性魔法登录；
  另一本地改动： brew Redis 未在跑导致 Store API 500，`brew services start redis` 后 200。

本轮只做 EN（与首轮同）；DE 措辞不在本轮范围。

---

## A1 商城/分类容器宽度：内容盒 1240px，与页头（全宽）和产品页（1360px）不一致

- **位置**：商城页与分类页 `#tv-woo-b2b-catalog.sf-catalog .container`
  （catalogue.css：`--sf-container: 1240px`，`width: min(1240px, calc(100% - 64px))`；
  另受主题 `.container` 的 `max-width: 1280px` 二次封顶）。
- **现状（实测 1440）**：目录内容盒 1240px @ x=100（左右各留 100px），而页头内容延伸到
  24px 边距、产品页容器 1360px @ x=40——同一屏里商城明显"内缩"。卡片 488px 宽，其中
  卡内身份列（品牌/型号/条目号）只有 446px，型号名三行折行。
- **建议**：≥1360px 时把商城/分类容器放宽到 1360px（同产品页），并解除主题 max-width 封顶：
  卡片 488→**548px**、身份列 446→**506px**（+13.5%），与产品页左右边缘对齐。
- **影响面**：仅 ≥1360px 视口的商城/分类容器与卡片；1200px 守卫 before=after（未越界）。
- **试验样式**：
  ```css
  @media (min-width:1360px){
    body #tv-woo-b2b-catalog.sf-catalog{--sf-container:1360px}
    body #tv-woo-b2b-catalog.sf-catalog .container{width:min(1360px,calc(100% - 64px));max-width:none}
  }
  ```
- **对照图**：`A1_catalog-container-1440-{before,after}.png`；实测：容器
  `[100,1240]`→`[40,1360]`，卡 488→548，身份列 446→506，页高 9237 不变（横向卡片不增行）。

## A2 分类页筛选轨：长列表（24 项 ≈ 8100px）滚动后筛选器完全离开视野

- **位置**：分类页左轨 `.sidebar-filters`（210px 宽，Home Storage 分类实测高 1006px）。
- **现状（实测 1440，滚动到 y=2000）**：筛选轨随页面滚走（视口内 y=−1569，完全不可见），
  用户改筛选条件必须滚回页首。
- **建议**：≥861px 时筛选轨 sticky（`top:104px`，自限高 `calc(100vh - 128px)` + 内部滚动），
  滚动全程可改筛选；实测滚动 y=2000 时轨钉在视口 y=104、可视高 772px。
- **影响面**：仅 ≥861px 的商城/分类左轨；卡片网格不动。
- **试验样式**：
  ```css
  @media (min-width:861px){
    body #tv-woo-b2b-catalog.sf-catalog .sidebar-filters{position:sticky;top:104px;align-self:start;max-height:calc(100vh - 128px);overflow-y:auto}
  }
  ```
- **对照图**：`A2_catalog-rail-1440-{before,after}.png`（同滚动位置截图）。

## B1 账户区导航（四页共用）：裸链接串 + 大面积空栏，改为卡片菜单

- **位置**：`.woocommerce-MyAccount-navigation .list-group`（标记已带
  `list-group-item list-group-item-action` 语义类，但没有任何样式命中——7 个链接以
  `display:inline` 文本流渲染，"Overview Inquiries Saved solutions … Log out" 挤成 2–4 行，
  下方 ~560px 空白（Inquiries 页左栏高 629px，导航仅 72px）。
- **现状（实测 1440）**：链接行高 18px、无当前页状态、无卡片容器。
- **建议**：按页头账户下拉菜单的既有卡片语言（chrome.css：padding 8、圆角 12、边框 #e2e5e5、
  投影 `0 10px 30px rgba(12,15,15,.08)`）把导航落成 230px 卡片菜单，链接块级 36px 行、悬停
  反白。四页共用一处样式。
- **影响面**：账户区六页的左导航（1440 与 390 同一修复）；无当前页高亮（快照主题的导航标记
  不输出 active 类——若业主采纳，active 态需在标记层补一个类，超出本轮 CSS 试验范围，已记录）。
- **试验样式**：
  ```css
  .woocommerce-account .woocommerce-MyAccount-navigation .list-group{display:flex;flex-direction:column;gap:2px;padding:8px;border:1px solid #e2e5e5;border-radius:12px;background:#fff;box-shadow:0 10px 30px rgba(12,15,15,.08);width:230px}
  .woocommerce-account .woocommerce-MyAccount-navigation .list-group-item{display:block;padding:8px 10px;border-radius:8px;color:#172636;font-size:14px;line-height:1.4;text-decoration:none}
  .woocommerce-account .woocommerce-MyAccount-navigation .list-group-item:hover{background:#f3f7f2}
  ```
- **对照图**：`B1_account-nav-1440-{before,after}.png`（菜单卡 230×279）、
  `B2_account-nav-390-{before,after}.png`（390 上同一导航从文本串变为菜单卡，栏高 72→279）。

## B2 询盘列表行内动作：View 与 Request again 同灰同权，无层级

- **位置**：Inquiries 表动作格 `.woocommerce-orders-table__cell-order-actions`
  （View = 看单据，Request again = 再发一次询盘——后者是这一行的主动作）。
- **现状（实测 1440）**：两枚按钮同为 `btn-outline-primary` 渲染的灰底深灰字
  （`rgb(233,230,237)` / `rgb(81,81,81)`、圆角 3px），视觉权重完全一致。
- **建议**：View 保持安静（白底描边），Request again 用站点主色 `#0c7f73` 实底白字；
  圆角统一 10px、字 12px、40px 高。每行 10 行 × 2 键，一眼可分辨"看"与"再发"。
- **影响面**：仅询盘表动作格两键的配色/圆角；表格结构不动。
- **试验样式**：
  ```css
  .woocommerce-account .woocommerce-orders-table__cell-order-actions a{border-radius:10px;font-size:12px;min-height:40px;display:inline-flex;align-items:center;padding:6px 14px}
  .woocommerce-account .woocommerce-orders-table__cell-order-actions a.view{background:#fff;border:1px solid #dfe7ec;color:#172636}
  .woocommerce-account .woocommerce-orders-table__cell-order-actions a.request-again{background:#0c7f73;border:1px solid #0c7f73;color:#fff}
  ```
- **对照图**：`B3_inquiry-actions-1440-{before,after}.png`；实测 View
  `rgb(233,230,237)`→白底描边、Request again `rgb(233,230,237)`→`rgb(12,127,115)` 白字。

## C1 产品页 Genie 坞条：静息白条 420×50 常驻压住购买盒动作行

- **位置**：`.linker-genie-app__bar`（应用关闭态的标题条 "Genie - Linker's AI assistant | Open"，
  fixed 右下 `bottom:84px; right:20px; width:min(420px,…)`，z-index 10000），PDP 购买盒
  `.pdp-buy-inner` 为 sticky（top 84px，高 776px）——两者横向完全重叠，坞条正压在
  Compare / Ask Linker Advisor / Documents 三键行上（实测 3 枚按钮在坞条投影矩形内）。
- **现状（实测 1440）**：坞条 420×50 @ (1001,765)，动作行 y=776..852——只要页面在滚动，
  遮挡全程存在（sticky × fixed）。
- **建议**：PDP（`body:has(.pdp-buy-inner)`）上隐藏**关闭态**的标题条，只留右下 50×50 圆形
  启动钮（入口功能重复：条上的 Open 与圆钮同职）；对话打开时标题条作为卡头保留
  （`:not(:has(> .linker-genie-app__panel))` 只命中关闭态）。实测 after：标题条 418×50→0，
  三枚动作键完整可见，圆钮 50×50 原位。
- **影响面**：仅产品页的坞条关闭态；其余页面（坞条不压购买盒）不动，对话卡打开态不动。
- **试验样式**：
  ```css
  body:has(.pdp-buy-inner) .linker-genie-app:not(:has(> .linker-genie-app__panel)) > .linker-genie-app__bar{display:none}
  ```
- **对照图**：`C1_pdp-dock-1440-{before,after}.png`。

## C2 移动端（≤860）Genie：Ask Genie 点了没有任何可见反应（挂载树整体 display:none）

- **位置**：`genie.css` 的 `@media (max-width:860px){.linker-genie{display:none}}` 把坞的整棵
  挂载树（圆形启动钮 + 对话面板）藏掉；而商城/分类移动端工具行的 "Ask Genie" 键
  （`data-linker-genie-open`，Entries.php）点击后**确实**启动应用、解开挂载 `hidden`、把
  `aria-expanded` 置 true——全部发生在 `display:none` 的祖先里。
- **现状（实测 390 商城）**：点 "Ask Genie" 后挂载 `aria-expanded="true"`、`panel.hidden=false`，
  但面板量出 0×0 @ (0,0)——移动访客得不到任何对话界面（产品页的同类问题见"缺陷登记"）。
- **建议**：≤860px 时，凡是打开态（任一 `[data-linker-genie-open][aria-expanded="true"]`）
  就把挂载树放出来作为底部对话卡：fixed 左右 10px / 底 10px、白卡圆角 14、最大高 72vh 内滚、
  打开期间藏 50px 圆钮。实测 after：面板 0×0 → **350×317** 底部卡（披露句、提问键、输入行
  齐备），点应用的 Open 后对话区展开，全部在卡内。
- **影响面**：仅 ≤860px；桌面坞不动。纯 CSS（选择器挂在加载器已写入的 aria-expanded 上，
  不改任何 JS）。
- **试验样式**：
  ```css
  @media (max-width:860px){
    .linker-genie:has([data-linker-genie-open][aria-expanded="true"]){display:block;position:fixed;inset:auto 10px 10px 10px;z-index:10000}
    .linker-genie:has([data-linker-genie-open][aria-expanded="true"]) > .linker-genie-open{display:none}
    .linker-genie:has([data-linker-genie-open][aria-expanded="true"]) .linker-genie-app{background:#fff;border:1px solid #e2e5e5;border-radius:14px;box-shadow:0 18px 50px rgba(12,15,15,.22);padding:12px;max-height:72vh;overflow:auto}
  }
  ```
- **对照图**：`C2_genie-mobile-390-{before,after}.png`（before 即"点了没反应"的现状）。

## D1 配置器设计报告：label/value 行全部单列通栏，报告拉得过长

- **位置**：设计报告的七个 `dl.linker-report__rows`（Site and inputs / PV yield / Storage
  sizing / Self-sufficiency / Selection basis / Manufacturer releases 等；每行 = DT+DD）。
- **现状（实测 1440）**：每行 1160px 通栏，标签在左值在右，视线横穿 1160px；七块合计高
  **1275px**，报告区把整页撑到 5387px。
- **建议**：≥1200px 时 `dl.linker-report__rows` 改两列网格（列距 56px，`align-items:start`），
  同类短行并排；实测七块合计 **1008px**（−267），整页 5387→**5120**；1100px 守卫
  before=after（未越界）。
- **影响面**：仅 ≥1200px 的设计报告 label/value 行；Solution 卡、BOM 表、假设清单不动；
  移动端保持单列。
- **试验样式**：
  ```css
  @media (min-width:1200px){
    [data-linker-app="configurator"] .linker-report__rows{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:56px;align-items:start}
  }
  ```
- **对照图**：`D1_report-columns-1440-{before,after}.png`。

## D2 配置器步骤导航：滚入 Solution/报告后三步指示完全离开视野（移动端）

- **位置**：`ol.linker-steps`（① Inputs ② Solution ③ Design report，页面顶部 y≈289/310）。
- **现状（实测 390，滚动到 y=2384）**：步骤条随页滚走（视口内 y=−2111）；配置器三屏是同页
  三段，长滚动后没有方位感。
- **建议**：≤860px 时步骤条 sticky 在页头下（`top:89px`，半透明底 + blur，`padding:8px`），
  滚动全程可见；实测滚动 y=2384 时钉在视口 y=89。桌面可选同样处理（本轮试验只做移动端，
  桌面暂不动）。
- **影响面**：仅 ≤860px 的步骤条。
- **试验样式**：
  ```css
  @media (max-width:860px){
    [data-linker-app="configurator"] .linker-steps{position:sticky;top:89px;z-index:40;background:rgba(246,249,245,.94);backdrop-filter:blur(6px);padding:8px 0;margin:-8px 0 0}
  }
  ```
- **对照图**：`D2_steps-sticky-390-{before,after}.png`。

## E1 页脚 Solutions 面板：三张卡 2 列排布，第三张孤行

- **位置**：页脚 `#tv-footer-v2 #footer-panel-solutions .footer-route-list`
  （`grid-template-columns: repeat(2, minmax(0,1fr))`，列表高 150px = 两行）。
- **现状（实测 1440）**：Residential/Commercial/Utility-Scale 三卡排 2+1，第三张独占一行，
  面板右下留空 392px 宽的缺口。
- **建议**：≥1024px 改三列一行：卡 392→**258px**，列表高 150→**70px**（−80px）。
  其余面板（Services / Plan with Linker）的列表保持 2 列不动（实测未受影响）。
- **影响面**：仅 ≥1024px 的页脚 Solutions 面板列表。
- **试验样式**：
  ```css
  @media (min-width:1024px){
    #tv-footer-v2 #footer-panel-solutions .footer-route-list{grid-template-columns:repeat(3,minmax(0,1fr))}
  }
  ```
- **对照图**：`E1_footer-solutions-1440-{before,after}.png`；页脚总高 574px 不变
  （面板不是页脚的最高列，节省体在自己面板内）。

---

## 缺陷登记（本轮 CSS 无法修，需代码修复，不随提案实施）

**产品页 "Ask Linker Advisor" 与项目按钮（`data-pdp-ask` / `data-project-message`）在新栈上无人监听。**
`plugins/linker-commerce/assets/pdp-ui.js` 的 `ask()` 派发的是旧助手的事件名 `lia:ask`
（pdp-ui.js:76–80），而新 Genie 应用监听的是 `linker-genie-ask`
（`plugins/linker-tools/src/genie/App.tsx:139`，派发方只有 search-ask.js 的搜索框链路）。
实测（t105，1440 与 390）：点击后无线程消息、应用状态不变——按钮全视口失效；线上今天能用是
因为旧助手插件还活着并监听 `lia:ask`。修复落点：pdp-ui.js 改派 `linker-genie-ask`（或桥接一次），
属代码改动，等业主裁定后与 C2 一并处理。

## 查过但不提案的面

- **页头（1440）**：顶部 6 项 + mega menu（产品面板 3 列 267px 列宽、13.5px 链接）与线上
  复刻态一致；工具簇在 x=1154 起，头部高 89px。密度正常，改动会打破复刻面的像素对照，
  不提案。
- **页脚快捷五卡（Solutions/Services/Plan with Linker/Account/Contact Linker）**：1440 上
  5×162px 居中、390 上 5×61px，均无挤压，不提案。
- **移动端商城卡片（390）**：单列 358×421，参数 11px/12px 起步可读；对比首轮产品页
  10px 标签问题，此处现状可接受，不提案。

## 台账汇总（位置 / 现状实测 / 建议 / 影响面）

| # | 位置 | 现状（实测） | 建议 | 影响面 | 状态 |
|---|---|---|---|---|---|
| A1 | 商城/分类容器 | 内容盒 1240（页头全宽、产品页 1360）；卡 488、身份列 446 | ≥1360 容器 1360；卡 548、身份列 506 | ≥1360 该两页型；守卫 1200 未越界 | 待业主 |
| A2 | 分类页筛选轨 | 滚动 y=2000 时轨在视口外（y=−1569） | ≥861 sticky top 104 + 内滚，钉在 104 | ≥861 左轨 | 待业主 |
| B1 | 账户导航（六页共用） | inline 链接串、行高 18、无容器 | 230px 卡片菜单、36px 行、沿用页头账户卡语言 | 1440+390 同一修复；active 态需补标记类（已记录） | 待业主 |
| B2 | 询盘行动作 | 两键同灰 `rgb(233,230,237)`、圆角 3 | View 白底描边、Request again `#0c7f73` 实底；圆角 10 | 仅该表动作格 | 待业主 |
| C1 | 产品页坞条 | 静息条 420×50 恒压三键行（sticky×fixed） | PDP 隐藏关闭态标题条，圆钮 50×50 保留 | 仅产品页关闭态 | 待业主 |
| C2 | 移动端对话卡 | 点 Ask Genie 无可见反应（挂载树 display:none，面板 0×0） | 打开态放行挂载树为底部对话卡（350×317 实测） | 仅 ≤860 | 待业主 |
| D1 | 设计报告 label/value | 七块单列通栏共 1275px，页 5387 | ≥1200 两列，块高 1008、页 5120 | ≥1200 报告区；守卫 1100 未越界 | 待业主 |
| D2 | 配置器步骤条 | 滚动后离开视野（y=−2111 @ 2384） | ≤860 sticky 页头下（top 89） | 仅 ≤860 | 待业主 |
| E1 | 页脚 Solutions 列表 | 2 列 392×2，第三卡孤行（列表高 150） | ≥1024 三列 258，列表高 70 | 仅该面板列表 | 待业主 |

以上十项**均未实施**：`plugins/*/content/**` 与插件代码本轮零改动；试验后实例 t105 上注入的
样式随浏览器会话结束即消失。全部待业主过目后另行裁定实施顺序与落点（WindPress 层/
LC 标记/工具应用样式，按三件套原生优先的既有顺序）。
