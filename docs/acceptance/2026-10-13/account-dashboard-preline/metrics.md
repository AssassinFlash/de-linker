# 目标值 vs 实现值（真实 computed style / rect）

量测：`measure.mjs`；参照=file:// Preline Pro，本地=t110 登录态；1440×900、390×844、430×932。
原始数据保留在 measurements-ref.json / measurements-baseline.json / measurements-ours.json / measurements-ours-de.json；null 表示无对应元素，不以猜值补齐。

## 桌面尺度：现状 → 参照目标 → 采用值

| 维度 | 接续前序现状 | 参照目标 | 最终实现 | 采用理由 |
|---|---|---|---|---|
| 工作区宽度 | 1240 | 1440 | 1440 | 全宽工作台，不再锁 1240 |
| 主内容宽度 | 888 | 1140 | 1120 | 260 侧栏 + 20 gap + 两侧 20；与参照 1140 相差 20 |
| 左侧栏宽度 | 240 | 260 | 260 | 精确 260 |
| 页面标题字号 | 20px | 18px | 32px | 业主要求抬高存在感，主动采用 32 而非 18 |
| 页面标题字重 | 600 | 600 | 600 | 600 |
| 页面标题行高 | 27.6px | 28px | 44.16px | 消费 leading-title，随 32 字号放大 |
| 瓦片宽 | 207 | 309 | 265 | 参照无侧栏；我们保留侧栏后四列 265 |
| 瓦片高 | 120.38 | 146 | 146 | 精确 146 |
| 瓦片间距 | 20px | 20px | 20px | 精确 20 |
| 瓦片内边距 | 20px | 20px | 20px | 精确 20 |
| 瓦片圆角 | 16px | 16px | 16px | 精确 16 |

## 桌面形制与皮肤

| 元素/属性 | Preline 实测 | 我们实测 | 说明 |
|---|---|---|---|
| 卡片圆角 | 12px | 12px | 12px |
| 卡片边框宽 | 1px | 1px | 1px |
| 卡片背景 | rgb(255, 255, 255) | rgb(255, 255, 255) | proto-canvas-white |
| 卡片边框色 | oklch(0.928 0.006 264.531) | rgb(226, 229, 229) | proto-neutral-200 |
| 卡片阴影 | rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.05) 0px 1px 2px 0px | rgba(21, 53, 47, 0.06) 0px 2px 8px 0px | 保留 proto-shadow-1，不新造色值 |
| 卡片标题字号 | 18px | 18px |  |
| 卡片标题字重 | 600 | 600 |  |
| 表格单元内边距 | 12px 16px | 12px 16px | 12px 16px |
| 表格行高 | 57 | 93 | 真实商品副行+三个动作，高于单行姓名表；不删信息凑高度 |
| 表头字体 | 12px | 12px | CMS 12px uppercase 形制 |
| 表头字色 | oklch(0.551 0.027 264.364) | rgb(90, 99, 99) | proto-neutral-500 |
| 正文行高 | 24px | 19.32px | 我们继承 proto-leading-title |
| 徽章圆角 | 6px | 6px | 6px 桌面 |
| 徽章内边距 | 4px 8px | 4px 8px | 4px 8px |
| 徽章字号 | 12px | 12px | 12px |
| 输入高度 | 38 | 38 | 38px 桌面，48px 移动 |
| 输入圆角 | 8px | 8px | 8px |
| 输入边框宽 | 1px | 1px | 1px |
| 表单卡内边距 | 32px | 32px | 32px |
| 区块间距 | 20px normal | 24px | 我们使用 24px，为增大尺度有意差 4px |

## 移动设计目标（业主图优先，Preline 移动仅兜底）

业主图是 736×1104 合成设计稿，没有 CSS/DOM；下列目标为从图中观察结构后采用的 390 布局尺度，不能声称是 getComputedStyle 的图稿测值。图稿裁切放大只用于并排观感，不作像素一致或字体测量证据。

| 面 | 主参照映射 | 导航形态 | 瓦片列数 | 最小触控高 | 页面侧边距 | 底栏整高 |
|---|---|---|---|---|---|---|
| overview | Home: greeting + shortcuts | 四键 fixed + 七入口折叠菜单 | 四快捷入口 / 四态两列 | 44px（目标 ≥44） | 16px（目标16） | 65px（64+1边框） |
| inquiries | My Courses: status rows | 四键 fixed + 七入口折叠菜单 | 不适用 | 44px（目标 ≥44） | 16px（目标16） | 65px（64+1边框） |
| inquiry-detail | Fee Summary: amount + CTA | 四键 fixed + 七入口折叠菜单 | 不适用 | 44px（目标 ≥44） | 16px（目标16） | 65px（64+1边框） |
| documents | Fee Summary: date + download | 四键 fixed + 七入口折叠菜单 | 不适用 | 44px（目标 ≥44） | 16px（目标16） | 65px（64+1边框） |
| saved-solutions | My Courses: list/empty | 四键 fixed + 七入口折叠菜单 | 不适用 | 44px（目标 ≥44） | 16px（目标16） | 65px（64+1边框） |
| company | My Profile: initials + full-width edit | 四键 fixed + 七入口折叠菜单 | 不适用 | 44px（目标 ≥44） | 16px（目标16） | 65px（64+1边框） |
| account-details | My Profile: initials + full-width edit | 四键 fixed + 七入口折叠菜单 | 不适用 | 44px（目标 ≥44） | 16px（目标16） | 65px（64+1边框） |

移动补充：状态瓦片 173×116、两列 gap12；快捷瓦片 83.5×80、四列 gap8；标题24/32/600；输入48px；save CTA48px固定在底栏之上，间隔11px（CTA 下沿 768 → 底栏盒顶 779）；无 CTA 页面底部预留100px，有 CTA 页面预留220px，均另加 safe-area。
390/430 × EN/DE 的最后一个可交互元素 hit-test 与全菜单七入口证明见 mobile-check.json；未伪造空态中不存在的动作。
颜色取 shared tokens；主参照的学生/课表/学费/进度不复制，既有四态数据与 PI 金额是唯一对应物。

## 横向溢出

| 本地截图组 | 通过 |
|---|---|
| EN 7页 × 3视口 | 21/21 |
| DE 7页 × 3视口 | 21/21 |
