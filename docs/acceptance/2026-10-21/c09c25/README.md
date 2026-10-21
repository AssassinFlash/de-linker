# fix/437-c09-c25 — 步骤栏当前步与“暂时无货”（证据）

票：#437 清单第 C09、C25 行（`docs/research/2026-10-21-configurator-rooftop/inventory.md`）。
工具应用内页不受像素门约束（业主 2026-10-10：工具页设计可改动）；这里记录的是交互状态。

## C09 左侧步骤栏的当前步

改前：`App.tsx` 写死 `<Steps current={ 1 } />`，算完、报告出现后仍停在 01。

改后：`App` 持有当前步；面板把“流程走到哪”报到 `App`：
计算开始即离开输入（住宅 `status !== 'empty'`，工商业 `result || failure || busy`）→ 02；
`MobileNavigation` 已在用的“页面在哪一段”（同一个滚动判据）把报告段到达时抬到 03。
取两者较大值：宽屏上左栏不吸顶、只有回到页首才看得见，计算完成后回到页首仍读 02（不倒退）；
手机上吸顶栏与底条在报告段同为 03。计算前滚动到空的方案段不前进（步骤描述的是流程）；
三个项目类型各自从 01 开始，点已选中的类型不重置（面板与结果都还在）。

`docs/acceptance/2026-10-21/c09c25/` 里的 `rail-01/02/03-*.png` 是 1440 与 390、EN 与 DE 的三种状态；
`checks.txt` 是截图当刻从 DOM 读到的当前步（`01Inputs` / `02Solution` / `03Design report`，德语
`01Eingaben` / `02Lösung` / `03Auslegungsbericht`）。1440 的左栏在页面滚动后离开视口，所以 02 的
1440 图是算完回到页首的状态，03 的 1440 图是全页截图（左栏位于文档顶部），另附从该图裁出的左栏
`rail-03-report-1440-*-crop-rail.png`。

## C25 暂时无货

改前：方案卡只在 `is_in_stock` 为真时画 “In stock”；工商业系统卡不画库存。

改后：`stockBadge()` 用 PO 里已有的 “Currently unavailable / Derzeit nicht verfügbar”（与 Genie 同一
措辞与 warn 色调）。方案卡按该产品自身的 store 数据；工商业系统卡按整机（逆变器与电池）判断——
两者都来自既有的 Store API 产品读数，工商业面板补读了结果里已带的电池 id，没有新增数据源。
读不到 store 数据时不画徽标（不猜）。Genie 卡片仍各自内联同一判断（Genie 是另一条工具面，本票不动；
措辞来自同一对 msgid，不会分叉）。

| 图 | 内容 |
|---|---|
| `stock-residential-in-{1440,390}-{en,de}.png` | 方案两卡 “In stock / Auf Lager” |
| `stock-residential-out-{1440,390}-{en,de}.png` | 方案两卡 “Currently unavailable / Derzeit nicht verfügbar” |
| `stock-commercial-in-{1440,390}-{en,de}.png` | 三个系统 “In stock” |
| `stock-commercial-out-{1440,390}-{en,de}.png` | 1954 电池不可用的两个系统报缺货，1955 的系统仍 “In stock” |

`checks.txt` 记录每次截图的 rail 当前步与卡片徽标文本（EN/DE 各一次）。

## 出图方法

```
plugins/linker-tools: npx storybook dev --ci --exact-port --port 6006
docs/acceptance/2026-10-21/c09c25: node tools/shots.mjs
```

故事用引擎的既有录制答案与 `fakeStore`（新增可选参数把指定产品报为无货）；德语走故事工具栏的
语言，加载的是 WordPress 页面会收到的同一份 `build/configurator.js` 目录 JSON。

两处只为让故事与页面同构、不影响线上渲染（线上有站点 tokens）：

- `.storybook/preview.tsx` 给 `Configurator/` 故事套上页面的 `data-linker-app="configurator"` 挂载点，
  `Steps` 发布的 `--linker-steps-scroll-offset` 才会生效，滚动落点与页面相同。
- `.linker-mobile-nav` 的 `inset/padding/gap/font-size/focus` 补上等于站点 tokens 的回退值；故事里没有
  `--proto-*` 时底条原本贴在静态位置而不是视口底部。

## 检查

| 项 | 命令 | 结果 |
|---|---|---|
| JS 单元测试 | `npm run test:unit` | 46 files, 362 tests passed |
| 浏览器 e2e | `npm run test:e2e` | 18 passed（含本票新增 5 条） |
| 类型 / ESLint / Prettier | `lint:types`、`lint:js`、`lint:format` | clean |
| 构建 | `npm run build && npm run build:check` | `build/ matches its sources.` |
| 译文 | `just i18n-tools`、`just i18n-coverage`、`just german-copy`、`just i18n-validity` | clean |
