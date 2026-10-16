# #190 PDP 三条欠账（死按钮 / 库存圆点 / 原型缺失元素）

依据：票 #190。三条都是 #174 验收后的残留，同一分支同一 PR 修。
基准不变：`docs/specs/174-pdp.md`（验收过的原型变体 A）。本票不改设计，只补齐原型里已有而实现缺失的
两处数据字段，删掉一处假承诺，修一处恒值的状态类。

## 通道（谁承担什么）

- **结构**：`content/livecanvas/single_product.html` 与其德语孪生 `de/single_product.html`
  （FAQ 块加一层 `.pdp-faq-wrap` / `.pdp-faq-main`，侧图由短代码输出）。
- **样式**：`content/windpress/pdp.css`（仅此一处，仍是 PDP 的唯一所有者）。
- **数据装配**：`includes/Presentation/ProductShortcodes.php`（`pdp_availability` 的状态类、
  `pdp_features` 的 kicker、新增 `linker_pdp_faq_side`）。零设计决策，零内联样式。
- **行为**：`assets/pdp-ui.js`（净减少一个监听器块）。

## M1 nameplate 死按钮（删）

- 事实：按钮派发 `lia:open`，全站无监听者（Genie 监听 `linker-genie-open`/`linker-genie-ask`）；
  业主 2026-10-13 裁定 Nameplate photo 类芯片「不补齐」（`docs/acceptance/2026-10-15/deploy/README.md` §8），
  Genie 无图片入口——接上任何事件都是假承诺。
- 落点：`pdp_project_choices()` 删按钮与其 docblock 措辞；`pdp-ui.js` 删 `[data-linker-assistant-open]`
  监听器块（`lia:open` 整个名字随之消失）；CSS **无** `.pdp-project-choice--nameplate` 规则
  （`grep -rn "nameplate" content/ assets/` 只剩 `products-mounts.css` 里关于目录芯片的既有注释，仍属实）。
- 孤儿内容：`languages/linker-commerce.pot` 与 `-de_DE_formal.po` 删该 msgid（附德语译文），`.mo` 重编译；
  `.po` 的 `#:` 引用按新行号刷新（`ProductShortcodes.php` 内的引用逐条重映射，其余文件不动）。

## N1 库存圆点两态（修）

- 根因：`pdp_availability()` 硬编码 `class="pdp-dot is-wait"`，#174 又把 `.pdp-dot.is-wait` 规则
  连同复刻层删掉，所以圆点永远是 accent 绿——无货商品显示与有货完全相同的色。
- 处置：按 2026-10-11 库存裁定（状态由 `WC_Product::is_in_stock()` 推导；托管库存的商品由数量推导状态）
  出类名——有货 `pdp-dot`、无货 `pdp-dot is-wait`；`pdp.css` 恢复 `is-wait` 的 warn 色
  `#f97316`（线上实测 `rgb(249,115,22)`，`docs/design/2026-10-11-replication-spec.md` §2/§3.1，
  改前为 `storefront.css` 的 `.pdp-dot.is-wait`）。文案不变（Woo 状态词，EN `In stock`/`Currently unavailable`，
  DE `Auf Lager`/`Derzeit nicht verfügbar`），数量仍不出现在页面上（`woocommerce_stock_format=no_amount`）。

## N2 原型里已有的两处数据（按原型恢复）

先取证：验收基准是原型变体 A（`docs/design/2026-10-15-pdp-prototype/index.html`，业主 2026-10-15 裁定），
两处元素都在原型里：

| 原型 | 原型出处 | 原型用的数据 | 恢复后的数据源 |
|---|---|---|---|
| FAQ 侧图 | index.html:893-904（`.faq-wrap` > `.faq-side` + 右栏） | `goodwe-sts-30-60kw-g10-product-20261007-02.png`（attachment 6505） | `Materials::gallery_ids()` 的最后一项——6505 正是 GW60K 的 `_product_image_gallery`（`6504,6505`）的最后一张（既有字段，零新增） |
| 特性带 kicker | index.html:771-772（`.band-copy` 的 `.kicker`，文案 `ESA Series`） | 系列名 | `ProductView::fields()['series']`（`_tv_legacy_acf_json` 的 `product_series`，目录卡同名数据源） |

- **FAQ 侧图**：`[linker_pdp_faq_side]` 取 gallery 最后一张出 `.pdp-faq-side`（`.faq-side` 的 mist 矩形 +
  图内缩 12%，原型自己的行内样式）。gallery 只有特色图的产品不出面板，`:has(.pdp-faq-side)` 让栅格退回单列
  （原型 ≤1023 也是单列、侧图 200px 高）。**不改 FAQ 行本身**（仍是既有的 `.pdp-disclose` 手风琴语言）。
- **kicker**：`pdp_features()` 在标题前输出 `<p class="pdp-kicker">{series}</p>`（无 series 则不出），
  颜色按原型 `.band .band-copy .kicker` 取 `rgba(255,255,255,.75)`（深色横幅上的浅色 kicker，
  不是页面 muted ink）。文案不新增——series 是产品自身字段的直出。
- **裁定**：两条都在验收过的原型里 → 按原型恢复（题面口径：原型里没有才记「不补」；本票没有「不补」项）。
  数据源只用既有字段/既有读取器，没有新设计、没有新文案串。

## 验收条目

1. `pdp_availability()`：有货 → `class="pdp-dot"` + `In stock`；无货 → `class="pdp-dot is-wait"` + `Currently unavailable`（两语言各自的 .po 词）。
2. `pdp.css`：`.pdp-dot` = `var(--pdp-teal)`、`.pdp-dot.is-wait` = `var(--pdp-wait)` = `#f97316`。
3. `pdp_project_choices()`：三个阶段按钮（`data-project-message` ×3），无 `nameplate`、无 `data-linker-assistant-open`；
   `pdp-ui.js` 源码不含 `lia:open`/`data-linker-assistant-open`，且带该属性的死按钮点击后不发任何事件。
4. `pdp_features()`：有 `product_series` → `.pdp-kicker` 打头；无 → 不出 kicker 行。
5. `pdp_faq_side()`：gallery ≥2 张 → `.pdp-faq-side` 取最后一张；只有特色图 → 空串。
6. 模板（EN+DE）：`.pdp-faq-wrap` 包住 `[linker_pdp_faq_side]` 与 `.pdp-faq-main`（标题 + FAQ 行在右栏）。
7. 模块注册短代码数 59 → 60（`linker_pdp_faq_side`）。
8. i18n：`just i18n-coverage` / `just i18n-validity` 绿；被删 msgid 在 `.pot`/`.po`/`.mo` 三处都不再存在。

## 测试与验证

- PHP 夹具：`ProductShortcodesTest`（四条：圆点两态、三阶段按钮、band kicker、FAQ 侧图取最后一张/回退空）、
  `PdpStylesTest`（三条：圆点两态规则、FAQ 栅格轮廓 + 200px 手机高、band kicker 色）、`ModuleTest`（60）。
- JS 夹具：`tests/js/pdp-ui.test.mjs`（项目选择仍派发 `linker-genie-ask`；带 `data-linker-assistant-open`
  的死按钮不发 `lia:open`；源码不含该名字）。
- e2e（`tests/e2e/specs/products.spec.ts`）：`en`/`de` 各一条库存圆点两态（WP-CLI 真翻转 `stock_status` 后还原，
  读类名/颜色/文案），一条 FAQ 块侧图（临时写 `_linker_faqs` 一行后删除，断言侧图取 6505、侧栏比正文栏窄）。
- 本地实例视觉抽查：`pdpfix`（端口 9030，快照 2026-10-15-1852）+ `present` + WindPress 重编译；
  PDP 有货/无货两态的圆点与按钮区、FAQ 侧图两语言。

## 变更台账条目（业主过目）

| 项 | 内容 |
|---|---|
| 变更 | PDP 三处修复：删 nameplate 死按钮；库存圆点按状态着色（有货绿/无货橙）；特性带补 series kicker、FAQ 块补侧图 |
| 裁定 | 死按钮＝业主 2026-10-13「不补齐」+ 无监听者的直接后果（删除）；圆点＝2026-10-11 库存裁定（只对客户说状态）；kicker 与侧图＝#174 验收过的原型变体 A 里已有，按原型恢复，数据源只用既有字段 |
| 允许差异 | 客户可见变化仅这三处：一个按钮消失、无货商品圆点由绿转橙、特性带多一行系列名与 FAQ 块多一张产品图 |
| 台账呈现 | 本规格 + PR 描述呈业主过目 |
