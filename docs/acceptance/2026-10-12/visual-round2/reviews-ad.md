# A 组 #109 与 D 组 #110 的独立 Spec + Standards 评审

2026-10-13 回写。两张 PR 合并时，GitHub review 列表是空的（`gh pr view` 的 `reviews` 为 `[]`）。#110 当时已有两条 issue 评论（Spec、Standards），那是实施线自己的核对，不是这次独立评审。#109 连评论也没有。下面是本会话已完成的独立结论，同一正文发在对应 PR 的评论里。范围只到这两张 PR 的完整 diff，不把像素门或页头复测算进通过。

## #109 A 组 — Spec

完整 diff：`065f83e9..4722a6a`（一笔提交）。文件两份：`plugins/linker-commerce/content/windpress/catalogue.css`，以及 `docs/acceptance/2026-10-12/visual-round2/implemented-a/` 的测量与截图。

对照业主 2026-10-12 批准的 A1、A2（`proposals/README.md`）与实施记录：

- A1：`min-width: 1360px` 下商城与分类容器 1240→1360，卡片 488→548，身份列 446→506，主题 1280 封顶解开。实施记录的 after 与这些目标值一致，守卫 1200 before=after。
- A2：`min-width: 861px` 下分类筛选轨 sticky、top 104、自身滚动。实施记录 y=2000 时 top 104、可视高 772；守卫 860 抽屉 before=after。
- 影响面停在目录样式。没有顺手改产品页、页头或 390 列表。

**结论：无必改。** 两条观察，均已关闭：

1. 实施 README 把 before/after 的像素差归到页头窄带与右缘浮件，没有把页头写成已验收。页头复刻是另一条线（A1-retest），不在本 PR 的通过范围里。观察关闭：diff 里没有页头文件。
2. 测量是实施实例 t106 的盒子读数，不是像素门的掩膜外零差证书。本 PR 的要求是批准的改良落上去，不是把复刻像素门改判通过。观察关闭：不把测量表读成像素门 PASS。

## #109 A 组 — Standards

同一 diff。

- 落点是目录样式卷 `catalogue.css` 尾部两段 `@media`，与文件既有组织一致，没有第二份实现。
- 断点 1360 / 861 与批准试验一致；861 与既有 860 抽屉守卫相邻而不重叠。
- 无旧政权编号、无业务规则搬进 CSS。

**结论：PASS，必改 0。**

## #110 D 组 — Spec

完整 diff：`065f83e9..faeede3`（实施提交 + 评审修复提交）。文件：`plugins/linker-tools/src/configurator/configurator.css` 及其 build 产物，加上 `implemented-d/` 的测量与截图。

对照批准的 D1、D2：

- D1：`min-width: 1200px`，`.linker-report__rows` 两列、56px 列距、`align-items: start`。方案卡、Stückliste、假设段不动。
- D2：`max-width: 860px`，`.linker-steps` 钉在 89px 页头下。
- 实施线自己的 Spec 评论曾有一条必改（注释写七块，实测六块），已在 `faeede3` 改注释。本会话独立重读后，该条已关闭，不另开。
- 1100 守卫与 1440 桌面守卫在 `measurements-implemented.json` 里 before=after。本会话没有重跑那次测量，结论以该记录和 diff 为准，不新发像素证书。

**结论：无必改。** 一条观察，已关闭：D2 注释一度写「流不移动」，栏高其实 +16px、后续内容上移 16px。数值是批准的试验值，注释已在 `faeede3` 改成如实描述。观察关闭。

## #110 D 组 — Standards

同一 diff。

- 规则只在配置器样式源，build 产物与源一致（实施线 `build:check` 通过的记录在 PR 正文；本会话未重跑构建）。
- D1 / D2 与既有 `max-width: 48rem` 块选择器不相交。
- 无第二实现，无旧政权编号。

**结论：PASS，必改 0。** 实施线 Standards 评论里那条「流不移动」注释必改，与上面 Spec 观察是同一处，已在 `faeede3` 关闭。
