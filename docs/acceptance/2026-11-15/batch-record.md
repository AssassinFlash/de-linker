# 2026-11-15 本轮修复记录

每条都是「现象 → 根因 → 修法 → 线上实测」。含三处我自己先前判断错误、经证据推翻后撤回的记录。

## 1. 十页标题层级缺级（无障碍）

**现象**：生产十个营销页（首页、方案枢纽、三个方案子页，各含德语孪生）从 h1 直接跳到 h4，或从 h2 跳到 h4。读屏软件会把缺的层级念成「缺少一个级别」。Genie 页另有两个 h1。

**根因**：层级是手写进 `post_content` 的，每页自己的内联 `<style>` 用元素名选目标题，所以标签与选择器必须一起动。子代理最初按我给的假设会把这批卡片标为 h3；实测 DOM 上下文后发现 `section.home-trust` 本身没有标题，四张卡直接位于 h1 之下，正确级别是 **h2**。

**修法**：`0dad05095` 新增 `tools/migrate/667-heading-levels.php`。每处替换都带期望计数，任何一处数量不符即整体拒绝、不写入；第二次运行以「必须消失的形式」判定，而不是数新标签（新标签数无法区分被移动的和页面本来就有的）。Genie 欢迎标题 h1→h2（`2e09d2218`）。

**实测（生产，390 与 1440 双视口）**：

| 页面 | 修复前跳级 | 修复后跳级 |
|---|---|---|
| `/` `/de/` | 2 | **0** |
| `/solution/` `/de/loesung/` | 1 | **0** |
| residential / commercial / utility 三对 | 1 | **0** |
| `/genie/` `/de/genie/` | 2 个 h1 | **1 个 h1** |

**过程中我引入并修掉的一处回归**：`#tv-rs-page-v1 h4{font-size:20px}` 是给被移动标题用的字面规则，不是死规则。第一遍没迁它，callout 标题从 20px 涨到 32px。补迁后复归 20px，并逐一核了 commercial（19/27px）与 utility（16px）未受影响。

## 2. 字体度量不匹配造成的布局位移

**现象**：`/for-installer/` 1440 的 CLS **0.123**，是「良好」阈值 0.1 的三倍。

**根因（两层）**：
1. `font-display: swap` 下回退字体与 Plus Jakarta Sans 的字框不同，真字体到达后 `.lk-hero-desc` 下移 **75px**。
2. 回退栈首位的 `Inter` **从未加载**：生产 Google Fonts 请求数 = 0，因为 WindPress 把 `@import` 发在 `@layer` 之后，属于无效位置被丢弃。这个名字只是让栈变长。

**修法**：按字体文件自己的度量算，不是估的。`plus-jakarta-sans-400.ttf`：unitsPerEm 1000、hhea ascender 1038、descender −222、lineGap 0 → 内容框 1.260；`dm-serif-display-400.ttf` → 1.371；Arial → 1.117。按 CSS Fonts 5 的 size-adjust 定义（回退内容框等于目标内容框）：112.80% 与 122.74%，各覆盖值把目标度量除以同一因子折回 Arial 单位。

**实测（生产）**：

| 指标 | 修复前 | 修复后 |
|---|---|---|
| Installer 1440 CLS | 0.123 | **0.032** |
| 配置器 390 LCP | 5,936ms | **2,740ms**（−54%）|
| 配置器 1440 LCP | 5,908ms | **3,544ms**（−40%）|
| 回退盒 y 坐标（`.lk-hero-desc`） | 478（真字体 553，差 75）| **553（一致）** |

二十组测量（10 页型 × 2 视口）现在 CLS 全部低于 0.04。

## 3. 触摸目标三处

**阶段胶囊（安装商 / 服务页）**：16×3 → **24×44**。绘制形态保持细线。

这里我连续错了三次，都是同一个错误的不同层，全部靠截图才发现：

1. 只写 class → 输给页面的 `#installer-journal .lk-bstage-pill-bar`（id + class），padding 不生效
2. 补 `body` + id → padding 生效，但页面用 `background` **简写**设颜色，把 `background-clip` 重置回 `border-box`，细线被涂成 40px 实心块
3. 修了 clip 但没覆盖 `.active` → `…pill-bar.active` 多一个 class，只有选中那条仍是实心块

**应用圆点（电站页）**：7×7 → 7×43，横向每边扩 5.5px。实测圆点位于 x=156/191/209/227（18px 间距），扩 8.5px 会让相邻命中区重叠、点错应用，所以止于中点：18px 宽、相邻但不相交。仍低于 WCAG 2.5.8 的 24px，这是行内 11px gap 的几何后果，不是选择。

**Genie 预览关闭按钮**：28×28 → 绘制 28、命中 44，用 `::after` 外扩 8px，卡片头部高度不变。

## 4. 配置器选项显示可用容量而非模块数

**现象**：644 行的设备下拉框里，客户读到 `SAJ HS2-10K-T2-X + SAJ BU2-5.0-HV1 · Battery modules per stack: 4`。同一对设备因模块数不同重复出现 4–8 次，每一行都只说明它是怎么组装的，不说明它能装多少电。

**根因（三层，每层都单独足以让它不生效）**：
1. `equipment_search_space.py` 的 `products` 只上报 5 个字段，把能量数据丢掉了。
2. 我第一版读 `row["figures"]`——**测试夹具的行有这个子对象，生产的 publication feed 没有**。生产行是扁平字段：`usable_kwh`、`nominal_kwh`、`kwh_range`。夹具通过、生产为空。
3. 我先把引擎发到了 `linker-engine.service`（8901），而 planner 实际跑在 `linker-planner-http/worker`（8911，`/opt/linker-planner/releases/<64位sha>`）。那个激活对规划请求毫无作用。

**修法**：`b990e846d` + `1e0ed1ff7` 引擎上报真实字段；前端 `EquipmentSearchResult.tsx` 用 `每模块可用容量 × 每堆模块数 × 并联堆数` 计算，读不到就**不显示这一节**而不是显示 `—` 或编造数字。德语独立撰写 `Nutzbare Speicherkapazität`。

**实测（生产，1440）**：

| 语言 | 首选项标签 |
|---|---|
| EN | `SAJ HS2-10K-T2-X + SAJ BU2-5.0-HV1 · Usable battery capacity: 18 kWh` |
| DE | `SAJ HS2-10K-T2-X + SAJ BU2-5.0-HV1 · Nutzbare Speicherkapazität: 18 kWh` |

数值核对：4 × 4.5 = 18；5 × 4.5 = 22.5（德语 `22,5`，小数逗号正确）；HS3 `3 × 4.8 = 14.4`。

**发布脚本**：`/tmp/publish-planner.sh`（本轮临时，收尾后回收）。它把「解包 → `uv sync --frozen` → 落到 64-hex 目录 → 重指 `.pth` → 继承 runtime/worker 策略 → `prepare` → `activate`」串成一步；`.pth` 指向构建目录会让新 release 静默导入旧代码，这是必须显式重指的一步。

## 5. 部署死锁（工具链缺陷）

**现象**：部署报 `snapshot reservation belongs to another deployment`，之后**每次部署都失败**。

**根因**：`state["active"]` 以检查点路径为键。检查点被移走后其记录仍挂在同一键上；唯一能释放它的 `finish_checkpoint` 需要那个已不存在的文件。新部署拿到同一路径、`deploy_id` 不同，于是在取快照前就被拒绝。

**修法**：`a3343989f`。同键记录若 `deploy_id` 不同，说明该批次已不可能在运行（批次从 reserve 到 archive 全程持有部署锁），替换为当前记录。已完成的快照靠 `state["snapshots"]` 按名字保护，不依赖 reservation。

**验证**：新增测试复现原场景（检查点是新的、registry 挂的是旧的），36 个快照测试通过，cutover 全套 **306 通过**，ruff/mypy 全通过。

## 6. 全站矩阵

620 次扫描（310 URL × 2 视口，8 并发）：**0 错误、0 破图、0 空链接、0 标题跳级、0 横向溢出**。

## 撤回的判断（证据推翻）

- **`rest-nonce` 400 是缺陷** —— 撤回。这是 WordPress 核心对未登录访客的正常应答（`rest-nonce` 只注册在 `wp_ajax_` 分支，nopriv 只有 `generate-password` 与 `heartbeat`），前端 `PlannerClient.ts:311` 本来就显式处理 `status===400 && body==="0"` 并继续走 guest nonce。
- **配置器缺 h1** —— 撤回。`domcontentloaded` 测量时 React 尚未渲染；`networkidle` 后 h1 是 `Your projects`（德语 `Ihre Projekte`），且需约 9 秒。
- **配置器 644 行是重复项** —— 撤回。`modules per stack: 4` 与 `5` 是不同电池容量，不是重复。
- **配置器字段无标签** —— 撤回。实测 `labels.length` 对全部 9 个控件有效。
- **圆点 `::after` 无效** —— 撤回。首次探测在元素滚出视口时进行，`elementFromPoint` 返回 null；滚入视口后确认生效。

## 仍未解决

- **配置器首屏约 9 秒**才从「Loading projects…」进入表单（390 与 1440 同）。
- **产品归档页 390 的 TTFB 4,097ms**，其余页型 1.4–2.5s。
- **`legacy_release.py` 能成功激活一个不服务规划请求的单元而不报错**：`linker-engine.service`（8901）与 `linker-planner-http/worker`（8911）是两棵树，前者激活成功对后者毫无影响。本轮因此有一次发布落在无效目标上。工具层应拒绝在无请求服务的单元上激活，或在输出里明确该单元不承接规划流量。
