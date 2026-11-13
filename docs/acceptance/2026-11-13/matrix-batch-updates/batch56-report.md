# Batch 5/6 商务与工具页（28 行）及响应式适用性（24 行）收口报告

- **执行日期**：2026-11-13
- **覆盖范围**：
  1. `docs/acceptance/2026-10-22/full-site/page-matrix.json` 最后 **28 行商务与工具页面**（`products`、`cart`/`loesungsentwurf`、`proforma-request`/`proforma-anfrage`、`my-account`/`mein-konto`、`solution-configurator`/`loesungskonfigurator`、`genie`、`compare-products`/`produkte-vergleichen` × `en`/`de` × `1440`/`390`）的只读交互与全页截图 + DOM 几何复核；
  2. `docs/acceptance/2026-10-22/full-site/state-matrix.json` 全部 **24 行 `applicability.status == "pending"`** 响应式与表面适用性判定。
- **生产只读边界**：全程拦截任何非只读 POST，0 次表单提交、0 个测试账号/询盘创建、0 封邮件触发、0 次模型计费调用。
- **交付产物**：
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch56-rows.json`（52 条：28 条 `page` + 24 条 `state`）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch56-captures/capture-manifest.json` + `screenshots/*.png`（28 张生产全页截图）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch56-captures/vision-review.json` + `dom-vision-audit.json`
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch56-captures/page-interactions.json`
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch56-captures/state-applicability-probes.json`

---

## 一、28 行商务与工具页面审计结论（28 / 28 通过）

1. **只读交互与路由一致性（`page-interactions.json`）**：
   - 全部 28 行均返回 HTTP 200，`docLang` 与预期语言一致（`en-US` / `de-DE`），`scrollWidth == clientWidth`（`1440` 与 `390` 均零横向溢出），导航折叠/抽屉开关与双语 `hreflang` / 页头语言切换配对 100% 匹配。
   - `/de/produkte/` 在提交 `12150da77` 部署后稳定命中 `LC DT ID: 6961`（H1=`Produkte`，24 张产品家族卡片，筛选折叠与第 2 页链接正常）；`/de/produkte/@390` 历史残留的 `mobile-compare-chip-covers-account`（已由 PR #664 修复）复测无遮挡，正式移入 `resolved_findings`。
2. **视觉识图与 DOM 探针逐项交叉复核（`vision-review.json` + `dom-vision-audit.json`）**：
   - 视觉模型在长图切片上报告的所有疑似拼写/裁切项均经真实 DOM 几何与文本探针逐一核实为切片边界或 OCR 假阳性：
     - `/solution-configurator/@390` `"Generate solution"` 按钮：真实 DOM `height=44px, scrollHeight=42px, padding="10px 18px", overflow="visible"`，处于未填邮编时的标准禁用态（`disabled=true, opacity=0.45`），无任何裁切；
     - `/de/loesungskonfigurator/@1440`：`docScrollWidth=1440, docClientWidth=1440`，标题区 `left=262.6px, right=1382.4px`（内边距 `57.6px`），德语引号为标准 `„…“`（`U+201E` / `U+201C`），零越界；
     - `/de/produkte/@1440`：DOM 实测卡片字段标签为 `"Modell"`（零 `"Model"`），参数数值使用德语逗号（`"10,0 kW"`、`"12,5 kg"`、`"97,5 %"`，`allDotDecimalsInFacts=[]`），页头与页脚文本精确为 `"Über uns"`、`"Heimspeicher"`、`"Großspeicher"`（零拼写错误）；
     - `/de/mein-konto/@390` 页脚胶囊条：父容器 `left=32, right=358, width=326, scrollWidth=326`，末项 `"Service"` `right=358`（左右各留 `32px` 边距，零裁切）。

---

## 二、24 行 `state-matrix.json` 适用性判定汇总（`applicability.pending`: 24 → 0）

| 状态族与状态名 | `1440` 判定 | `390` 判定 | 实测依据（`state-applicability-probes.json`） |
| --- | --- | --- | --- |
| `global-navigation:mobile-menu-open` (`en`/`de` `@1440`) | `not-applicable` (`not-applicable-today`) | —（已验） | `1440` 下 `details.tv-mobile-navigation` 与 `#tv-mobile-toggle` 均为 `display: none`（`0×0`），渲染桌面导航 |
| `comparison:phone-table-scroll` (`en`/`de` `@1440`, `@390`) | `not-applicable` (`not-applicable-today`) | `applicable` | `1440` 下 2/3 列对比表 `scrollWidth == clientWidth == 1126`（`scrollablePx=0`，提示隐藏）；`390` 下 `clientWidth=356, scrollWidth=496/688` 且显示横向滚动提示 |
| `roof:mobile-gestures` (`en`/`de` `@1440`, `@390`) | `applicable` | `applicable` | 屋顶画布在桌面与触屏视口均挂载统一指针/缩放/拖拽手势处理，已由 PR #1052 `planner-map-chain.spec.ts` 8 用例覆盖通过 |
| `document-library:rail-and-mobile-chips` (`en`/`de` `@1440`, `@390`) | `applicable` | `applicable` | `1440` 显示桌面侧栏（`232×428px`）并隐藏胶囊条；`390` 显示吸顶胶囊条（`390×65px`）并隐藏桌面侧栏 |
| `global-navigation:mobile-input-visible-area` (`en`/`de` `@1440`, `@390`) | `not-applicable` (`not-applicable-today`) | `applicable` | `1440` 为桌面视口；`390` 下输入框（`308×51px`）与固定浮层交集为 `0` |
| `genie:dock-keyboard-focus-escape-and-return` (`en`/`de` `@1440`) | `applicable` | —（已验） | `1440` 下 Genie 助手以非模态浮层打开（`bodyOverflow=visible`），`Escape` 正常关闭 |
| `genie:ordinary-draft-failure-owner-isolation` (`en`/`de` `@1440`, `@390`) | `applicable` | `applicable` | 首页 Hero、独立 `/genie/` 工作台与侧栏 Dock 三处表面在 `1440`/`390` 下均接受私有草稿并受 `DraftContext` 归属隔离保护 |
