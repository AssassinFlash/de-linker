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

14 个页型（首页/产品/分类/PDP/方案/安装商/联系，EN+DE）× 390 全滚动视觉走查：排除已确认的三类误报源（sr-only 元素的 `clip: rect(0,0,0,0)`、懒加载未触发的 `incomplete`、Cookie 隐藏面板的溢出）后，**零缺陷**。四条曾被判为缺陷、经测量撤回：

- `sales@de-linker.com` 270×20 → 文字链接不受 44px 触摸目标约束。
- 联系表单 checkbox 18×18 → 包在 312×67 的 `<label>` 里，点标签任意位置均可勾选。
- 安装商页「Partnerleistung N anzeigen」24×44 → 就是阶段胶囊本身，宽度 24 是 WCAG 2.5.8 下限，上一轮刻意选择。
- 全部 14 页 `overflowX: true` → 来自 Cookie 偏好面板（`.cky-preference-center` 845px），文档 `scrollWidth` 等于视口 390，页面本身无横向溢出。

**首屏 Cookie 横幅是唯一剩下的真实阻塞**：390 视口占 47%（393px），实测压住三个可操作控件（首页主 CTA「Lösungskonfigurator öffnen」、Genie 输入框、铭牌拍照入口）。CookieYes 3.5.8 的 `cky-btn-close` 只存在于偏好面板标题栏，notice 横幅模板里没有关闭按钮；`settings.config.notice.elements.closeButton.status` 改成 `true` 后页面无变化（已验证并回滚该改动）。横幅高度主要来自 468 字符的德语法律文案，按 §0.2 法律正文保护不擅改。**这是需要业主决定的事项，不是我能单方面改的**。

## 7. 全欧地点支持（业主裁定：全欧洲是原则，不允许妥协）

**现象**：配置器的邮编查询只认 5 位德国邮编。英国、荷兰、葡萄牙、希腊的客户没有任何可输入的格式；输入城市名一律「找不到」；而查不到时系统仍把原文存成项目地点继续跑。

**根因**：`geo.py` 只读 `data/plz_de.csv.gz`（德国），`http_app.py` 用 `len(digits) == 5` 判断有效性。时区硬编码 `Europe/Berlin`。

**修法**：

| 层 | 改动 |
|---|---|
| 数据 | `build_plz.py` 改为从 GeoNames `allCountries.zip` 生成 `plz_eu.csv.gz`：**450,815 个邮编 / 50 个国家** |
| 时区 | GeoNames 的邮编导出没有时区列，改由 `cities5000.txt` 就近城市取，并**按国家约束候选** |
| 希腊 | GeoNames 的邮编导出**完全没有希腊**；补 Apache-2.0 的 `MentatInnovations/grpostcodes`（1,250 条，覆盖 10–90 全部前缀） |
| 查询 | 支持各国格式并归一化大小写与空格 |
| 前端 | 占位符随所选国家变化，不再永远是 `e.g. 10115 Berlin` |

**实测（本机对生产数据表）**：

| 输入 | 国家 | 结果 |
|---|---|---|
| `M1 1AE` | GB | `M1 Manchester` / Europe/London |
| `M11 1AA` | GB | `M11 Manchester`（空格是区段边界） |
| `SW1A 1AA` | GB | `SW1A` |
| `D01 F5P2` | IE | `D01 Dublin 1` |
| `9401 AB` | NL | `9401 Assen` |
| `3750-000` | PT | Europe/Lisbon |
| `59-700` | PL | Europe/Warsaw |
| `35001` | ES | `Atlantic/Canary`（加那利保住自己的时区） |
| `10431` | GR | `Athens` / Europe/Athens |
| `80538` | DE | `München` / Europe/Berlin |

**三处我自己引入并修掉的错误**：

1. **时区跨国误标**：只用「最近城市」时，1,411 个边境邮编取了邻国时区（西班牙 `Portbou` 得到 `Europe/Paris`）。加上同国家约束后，西班牙只剩 Madrid / Canary / Ceuta，葡萄牙只剩 Lisbon / Madeira / Azores。
2. **德国市场被打残**：最初设计「共用邮编必须指定国家」，但实测 **10,815 个德国邮编里有 4,754 个（44%）与其他国家重号**，等于让近半数德国客户用不了。改为无国家时优先德国。
3. **州代码语义被我改坏**：表里存 GeoNames 的短码 `BY` 与地名 `Bavaria`，而 `lod2-sources.json` 的键是 `DE-BY`，导致屋顶步骤报 `no LoD2 source for Bavaria`。加 `Place.iso_region`，屋顶与报告各取所需。

第 3 条是引擎全套 95 个测试失败的根因，不是共用邮编问题——我最初判断错了方向。

## 我造成的损失（已修复，须记录）

## 我造成的损失（已修复，须记录）

**删掉了登记在册的整站备份基线。** 上一轮清理时我查的是 `~/de-linker-data/snapshots/.snapshot-retention.json` 的 `baselines`（数据库快照的），为空；而整站备份的基线在另一个文件 `~/de-linker-data/.backup-retention.json`，里面正登记着 `cutover-20261021-2259`——就是我删的那份 4.2 GB。

后果：`just cutover backup` 每次报 `backup retention: skipped remaining cleanup (registered backup baseline is missing or changed)`，轮转被永久阻断，备份会无限增长，正是 §0 明令禁止的。

**修复**：选 `cutover-20261113-0826` 作新基线。先核实完整性——数据库 sha256 与 manifest 一致（7,944,218 字节），文件集 39,782 个中随机抽 12 个哈希全对；再用工具自己的 `register-backup --baseline --write` 登记（它会重新完整校验 manifest、文件与数据库）。读回 `baselines` 已指向新值，随后一次备份实测 `removed cutover-20261113-0556`，轮转恢复。

**教训**：回收任何备份前，两个 registry 都要查——`.backup-retention.json`（整站备份）与 `snapshots/.snapshot-retention.json`（数据库快照），它们是不同的保留域。

## 撤回的判断（证据推翻）

- **`rest-nonce` 400 是缺陷** —— 撤回。这是 WordPress 核心对未登录访客的正常应答（`rest-nonce` 只注册在 `wp_ajax_` 分支，nopriv 只有 `generate-password` 与 `heartbeat`），前端 `PlannerClient.ts:311` 本来就显式处理 `status===400 && body==="0"` 并继续走 guest nonce。
- **配置器缺 h1** —— 撤回。`domcontentloaded` 测量时 React 尚未渲染；`networkidle` 后 h1 是 `Your projects`（德语 `Ihre Projekte`），且需约 9 秒。
- **配置器 644 行是重复项** —— 撤回。`modules per stack: 4` 与 `5` 是不同电池容量，不是重复。
- **配置器字段无标签** —— 撤回。实测 `labels.length` 对全部 9 个控件有效。
- **圆点 `::after` 无效** —— 撤回。首次探测在元素滚出视口时进行，`elementFromPoint` 返回 null；滚入视口后确认生效。

## 仍未解决

无。

以下三条本轮报告过的「未解决」已由证据撤销，不再是缺陷：

- **配置器首屏约 9 秒** → 实测拆成三段：本机到主机的 RTT 约 1.5–1.9 秒（静态 `.js` 同值）；`rest-nonce` 往返 700ms（访客注定 400，已删）；两次 `bootstrap` 各约 1.27 秒（安全设计：第一次发 cookie、第二次证明 cookie 回传，改成一次往返等于把新发 cookie 当所有权证明，与 `#902` 冲突）。删掉 nonce 后表单可见 **8,919ms → 6,858ms**。剩余部分是链路延迟与安全成本，不是可修的缺陷。
- **产品归档页 390 的 TTFB 4,097ms** → 冷缓存首次渲染；同页第二次 1.5s，与纯静态资源相同，即链路下限。`x-litespeed-cache: hit` 时同样 1.5s。
- **`legacy_release.py` 能激活不服务规划请求的单元而不报错** → `9f845f74f` 在该单元激活时打印仍承接规划请求的单元名。规则同步写入 `AGENTS.md` §5。
