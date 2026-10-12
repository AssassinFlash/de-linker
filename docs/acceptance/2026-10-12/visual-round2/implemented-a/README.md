# 视觉二轮 A 组实施记录（2026-10-12）：A1 容器宽度、A2 筛选轨 sticky

业主 2026-10-12 批准 A1、A2 两项（提案与试验样式原文见 `../proposals/README.md`）。
本目录是实施与复验产物：两项已按试验 CSS 原文落入
`plugins/linker-commerce/content/windpress/catalogue.css`（文件末尾两段
`@media`，注释标明业主批准与台账出处），实例 t106（live 快照 20261010-0033
+ live code，装配步骤同 t105）`just present` + `just windpress-compile` 后实测。

测量脚本 `tools/r2a-implemented.mjs`：同一 chromium（linker-tools 的 playwright
channel=chromium）、同等待协议（fonts.ready + 逐屏滚动 + 可见图片 decode）、URL 带
`?cbq=` 破缓存；before 与 after 是同一实例、同一协议下的两次真实运行（before 在
改动落库前采集，不是注入还原）。对照图：`A1_catalog-container-1440-{before,after}.png`
（商城页全页）、`A1_category-container-1440-{before,after}.png`（分类页首屏）、
`A2_catalog-rail-1440-{before,after}.png`（分类页滚动 y=2000 时的视口）。

## 逐项实测（measurements-implemented.json，盒子为 [x, 页内y, 宽, 高]）

| 项 | 指标 | before | after | 目标 | 判定 |
|---|---|---|---|---|---|
| A1 商城 1440 | 容器 | [100,·,1240,·] | **[40,·,1360,·]** | [40,1360] | 达标 |
| A1 商城 1440 | 卡片宽 | 488 | **548** | 548 | 达标 |
| A1 商城 1440 | 身份列宽 | 446 | **506** | 506 | 达标 |
| A1 商城 1440 | 页高 | 9237 | **9237** | 不变 | 达标 |
| A1 分类 1440 | 容器 | [100,·,1240,·] | **[40,·,1360,·]** | 同商城 | 达标 |
| A1 分类 1440 | 卡/身份列 | 488 / 446 | **548 / 506** | 同商城 | 达标 |
| A1 守卫 1200 | 容器/卡/身份列/页高 | [88,·,1024] 380 338 9274 | **逐一相同** | before=after | 达标 |
| A2 分类 1440 y=2000 | 轨 rect.top | −1569（滚出视野） | **104** | 104 | 达标 |
| A2 分类 1440 y=2000 | 轨可视高 | 1006（随页滚走） | **772** | ≈772 | 达标 |
| A2 分类 1440 y=2000 | computed | static | **sticky / top 104px / max-height 772px / overflow auto** | sticky | 达标 |
| A2 守卫 860 | 轨状态 | fixed+hidden 抽屉 [860,·,360,900] | **逐一相同** | before=after | 达标 |

补充：A1 after 的 `containerMaxWidth` 由 1280px（主题封顶）变为 `none`，
`--sf-container` 计算值 1240px→1360px；A2 after 的轨 x=40（原 100）是 A1 放宽
容器的左缘（两项同时生效的合量），top=104 与可视高 772 与提案试验一致。

before 状态与提案轮（t105）完全对齐：商城页容器/卡/身份列/页高、守卫 1200 各值、
A2 y=2000 轨位全部同数；before 全页截图与提案轮 before 图的像素差全部落在四个
窄带（页头两段、右缘两段——fixed 元素在全页拼接里的落点，Genie 圆钮等浮件），
商品目录内容区零差异。
