# Solution Configurator 初始锚点落地修复验收（2026-11-13）

## 缺陷与根源

带 workspace hash（`#lp-design` 等）直接加载时，浏览器在吸顶栏（站点页头 +
项目操作栏）高度被测量前就执行锚点滚动：`scroll-margin-top` 的回退值是
0px（planner.css `calc(var(--lp-site-header-height, 0px) +
var(--lp-project-bar-height, 0px) + 16px)`），目标落在吸顶栏之下。Chromium
的滚动锚定通常会在随后的布局变化中纠正位置，Safari 无此机制，不会自愈。

修复（dc1d96a6a，已部署生产）：`measurePlannerChrome.ts` 增加一次性
arm/reveal/disarm——加载时武装初始 hash，每次页头/项目栏测量后按当前
`scroll-margin-top` 校正一次，用户滚动（wheel/touchstart）或 4 秒后解除；
`useSiteIntegration` 与 `useProjectBar` 的测量闭包均挂校正。判定逻辑单测
6 例（apps/planner/tests/measure-chrome.test.mjs）。

## 验收方法（生产实走，2026-11-13）

同浏览器上下文（保留项目会话令牌）+ 跨文档全新加载（about:blank 跳转），
390×844，EN 与 DE，入口态与标定面板展开态各一屏。几何探针为地面真值
（sectionTop 应精确等于 scroll-margin-top，标定按钮完整可见），视觉模型
复核截图。

两个测试陷阱（此前多轮复现失败的原因，记录以防重犯）：

1. Playwright `goto` 与当前 URL 只差 fragment 时是**同文档导航**，不重新
   加载，应用状态不会重置；
2. 新建浏览器上下文**没有项目会话令牌**，跨上下文打不开同一项目。

## 结果（全 PASS）

| 场景 | sectionTop vs scrollMargin | 标定按钮位置 |
| --- | --- | --- |
| EN 入口态 | 260 == 260px | y=625，完整可见 |
| DE 入口态 | 310 == 310px（德语吸顶栏更高） | y=752，完整可见 |
| EN 标定展开 | 应用自身聚焦滚入 | y=120 |
| DE 标定展开 | 应用自身聚焦滚入 | y=170 |

截图：`en-390-entry.png` / `de-390-entry.png` / `en-390-calibration.png` /
`de-390-calibration.png`。视觉复核四张均无遮挡、溢出、贴边、异常空白。

## 顺带否决的两条视觉误报（DOM 探针复核）

- "Plan/Map/3D 无激活态"：planner.css:194 激活样式生效（白底+teal+阴影，
  aria-pressed=true）。
- "空状态卡片只有图标、留白过大"：视口截图只见卡片顶部 94px；全卡内容
  （图标 24px→标题 12px→正文 16px→按钮）间距协调，内容 296px 居中于
  350px 卡片。
