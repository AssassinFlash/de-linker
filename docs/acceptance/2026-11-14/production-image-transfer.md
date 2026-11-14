# 生产图片传输：实测、根因与全站扩展（2026-11-14）

这份记录只写实测到的字节、查明的根因，以及线上读回的结果。它不代表全站性能目标完成。

## 测量方法更正（重要）

本文件早期版本用 `for (const i of document.images) i.loading = 'eager'` 强制加载后统计，得到首页 4,307,997 字节。**那个数字不可用作客户实际传输量**：强制 eager 会让轮播中隐藏的 4 张幻灯片也下载（`linker-support-after-the-order-1.webp` 344,190、`linker-match-inverter-battery-accessories-1.webp` 335,850、`linker-order-the-system-1.webp` 311,268、`linker-trade-pricing-and-availability-1.webp` 130,800），把首页从约 299 KB 虚高到 1.9 MB。

**此后所有数字统一采用自然懒加载**：真实视口 → 逐屏 `scrollTo` + `waitForTimeout(55–70ms)` → 等待 900–1200 ms → 读 `performance.getEntriesByType('resource')` 的 `transferSize`。前后两组数字若方法不同，不得直接相减。

## 本批最终读回（自然懒加载，匿名，2026-11-14）

| 页面 | 视口 | 图片字节 | 文件数 |
|---|---|---|---|
| 首页 EN | 1440 | **456,975** | 14 |
| 首页 EN | 390 | **278,895** | 14 |
| 首页 DE | 1440 | **423,965** | 13 |
| 首页 DE | 390 | **278,895** | 14 |
| services-support EN | 1440 | **390,129** | — |
| for-epc EN | 1440 | **585,763** | — |
| utility-storage EN | 1440 | **630,595** | — |
| contact EN | 1440 | **181,538** | — |
| contact EN | 390 | **135,962** | — |
| about EN | 1440 | **238,437** | — |

首页 HTML 传输：EN **79,093** 字节、DE **97,189** 字节。

全部组 `broken=0`、`docOverflowX=0`、`jsErr=0`。

## 三个独立根因（不是同一个问题）

### 1. 手写 `<img>` 绕过 WordPress 响应式输出

20 个营销页的正文是整段手写 HTML 存在 `post_content`（about 页 98 KB），`grep` 全仓库找不到源码。这些 `<img>` 只有 `src`，没有 `srcset`/`sizes`，浏览器按原图取。磁盘上变体齐全（例 `linker-residential-hybrid-from-linker-300x129.webp`），但页面从不使用。

修法：`tools/perf/add-responsive-images.php` 按附件 metadata 生成 `srcset`，`sizes` 来自 `tools/perf/site-sizes.json`。

### 2. `sizes` 表必须由实测生成，手写追不上

早先维护一张 28 条的手写 `sizes` 表，只能覆盖「记得住的那几张」，因此 `services-support` 3,000,095 字节、`for-epc` 2,712,283 字节长期没被处理。

现在 `tools/perf/sizes-from-measurement.mjs` 从浏览器实测 JSON 生成整张表（**76 个文件**，覆盖 36 个页面 × 390/1440 两视口）。规则写进注释：

- 同一文件在多个位置出现时取**最大实测盒**——宁可多下几 KB，绝不因低估而模糊。
- 只用 768px 一个断点（主题自己的手机/桌面分界），不编造未测过的中间断点。
- 满幅横带识别为 `100vw`；已有 `srcset` 的一律不动。

### 3. 桌面端下载永久不可见的图

`mobile-photo-topics.js`（内联在 about / services / epc 六页正文，三份副本 md5 各不相同）用 JS 创建 `.mt-visual img`，该层在 `>800px` 是 `display:none`，但 `<img>` 一插入就无条件下载：`authorised-supply` 472,468、`inverter-protocol` 319,894、`container-bess` 275,156、`outdoor-cabinets` 224,578、`trade-partner-portal` 102,964 = **1,395,060 字节**，桌面访客一个字节都用不上。

合成页实测确认机制：`display:none` 内的 `<img>` 加 `loading="lazy"` 后 `complete=false`、零字节传输；不加则立刻下载。

修法：`tools/perf/about-images.php` 给三份副本的 `photo`/`thumbnail` 注入 `loading="lazy"`。读回 about 1440 从 2,199,546 降到 **238,437**，`hiddenFetched=false`。

### 4. CSS 背景图无法用 srcset

`initiatorType` 为 `css`/`link` 的图片是背景图，`srcset` 机制不适用。实测：services 539,400（三张）、about 197,262、home 139,776。这部分**未处理**，是已知待办。

## 内联 CSS/JS 的规模与作用域审计

20 个页面把样式与脚本内联在正文：**CSS 1,019,538 字节 / 17 个块**、**JS 248,688 字节 / 12 个块**，每个页整份重发。这些在仓库里**没有对应源码文件**。

作用域审计（对全部 70 个已发布 URL 的渲染 HTML 做 token 泄漏测试）：**9,160 个选择器中的 53 个未加页级前缀，但没有任何一个能在自身页面族之外匹配到元素**。也就是说把它们合并进单一 WindPress 来源在渲染上安全。这是后续工作，不在本批。

## 仍开放的

- 分类归档、法律页、工具页未单独采样
- LCP / CLS 未测
- CSS 背景图 539 KB（services）未处理
- 配置器首屏：`planner-core` 1,414 KB（gzip 380 KB）、`SceneViewport` 1,514 KB、`MapViewport` 1,161 KB、`EnergyFlowChart` 542 KB；地图与 3D 已按需加载，首屏主体是应用自身代码 + Ajv schema 校验

## 备份与回滚

- `/home/u388076051/backups/about-img-20261114/`（6 页正文，784 KB）
- `/home/u388076051/backups/sizes-20261114/`（12 页正文，1.4 MB）
- `/home/u388076051/backups/sizes2-20261114/`（4 页正文）

每份目录内逐文件记录字节数与 md5。回滚：把对应 `.html` 写回 `post_content`，`clean_post_cache()`，随后 `do_action('litespeed_purge_all')`。

## 工具清单

| 文件 | 作用 |
|---|---|
| `tools/perf/sizes-from-measurement.mjs` | 实测 JSON → `sizes` 表 |
| `tools/perf/site-sizes.json` | 生成的表（76 文件） |
| `tools/perf/add-responsive-images.php` | 按表补 `srcset`/`sizes`，默认 dry-run |
| `tools/perf/about-images.php` | about 族正文图 + 移动层懒加载，默认 dry-run |
| `tools/perf/backup-pages.php` | 写入前备份页面正文 |
| `tests/e2e/measure-image-boxes.mjs` | 六断点实测布局盒 |
