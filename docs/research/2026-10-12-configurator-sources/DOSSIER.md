# Solution Configurator 调研来源考古（DOSSIER）

日期：2026-10-12。任务：回答业主指令"（Solution Configurator）我们从哪调研的素材并且参考的最多的，采用 /prototype 技能去参考设计复刻并做出来原型供我选择"。

方法：只读遍历两个本地仓库的调研、规格、验收与票据文件；对每条结论给出真实存在的文件路径（全部 `ls` 验证过）；引用计数用 `grep -oi` 对 12 份配置器核心文献逐文件统计（文献清单见 ① 的"计数口径"）。外部研究一律是当时经 Apify 抓取的一手页面，本档案不新抓任何外页。

计数涉及的两个仓库：

- 新仓库（本仓库）：`/Users/chesterjohn/Documents/de-linker`
- 旧仓库（证据档案，只读）：`/Users/chesterjohn/Documents/de-linker-project`

---

## 一句话结论

**外部参考最多的是"德国本土 B2B 光储批发商同业组"（Memodo、Krannich、BayWa/Solar-Planit、Segen、IBC、EWS 为核心，两轮调研合计被引 260+ 次）——配置器的四条核心形态（即时结果、服务器端项目、BOM→报价、兼容三值放行）全部来自它；单一来源中被引最多的是 HTW Berlin（58 次/5 文件，定容方法权威，非视觉参考）；名字被引最多的单体设计工具是 BayWa Solar-Planit（19 次/3 文件）。但磁盘上有像素级可复刻素材的只有我们自己的旧线上 Linker Planner（1440×900 录屏 2 支、成片 9 支、分步截图 64 张、页面模板 1 份）和新栈 #14 三屏实现（EN/DE × 1440/390 × 全状态验收截图约 110 张 + 2 份报告 PDF）——外部工具全部在登录墙后，两轮调研都没有留下本地截图。**

---

## ① 素材来源清单（按参考权重排序）

**计数口径**：12 份配置器核心文献 = 旧仓 `docs/research/` 的 2026-08-28-solar-planner-benchmark、2026-08-29-canvas-imagery-lod2、2026-09-04-planner-input-sufficiency、2026-09-15-planner-implementation-map、2026-09-22-planner-interaction-for-demonstration、2026-09-22-site-detail-interaction-for-demonstration、2026-09-22-what-using-the-tools-is；新仓 `docs/research/2026-10-09/` 的 planner-methods、pv-wholesale-selection-tools、old-repo-plugin-and-planner-inventory、old-repo-021-planner-positioning；新仓 `docs/specs/14-solution-configurator.md`。"次"= 不区分大小写的字符串出现次数，"文件"= 出现过的文献数。目录简写：旧仓 `OR/docs/research/`，新仓 `NR/docs/research/2026-10-09/`。

### 第 1 层：德国 B2B 批发商同业组（参考最多，形态之父）

| 来源 | 计数 | 证据路径与关键原句 |
|---|---|---|
| **Memodo** | 54 次/3 文件 | `OR/docs/research/2026-08-28-solar-planner-benchmark.md` §3.1（16 次）；`NR/pv-wholesale-selection-tools.md` §1.1（36 次，放行清单、筛选面板、PDP 配套关系）；`NR/planner-methods.md`（2 次）。关键句（pv-wholesale §1.1）："一个组合要成立，**逆变器厂商和电池厂商的放行必须同时存在**"——兼容三值语义的直接出处。 |
| **Krannich** | 54 次/2 文件 | benchmark §3.2（15 次）；pv-wholesale §1.2（39 次，WR-Speicher-Sets 446 个套装 SKU、筛选维度表、Trinity 2020 配置器先例）。关键句（benchmark §3.2）："curated inverter+storage bundle sets ('WR-Speicher-Sets') — pre-matched compatible combinations assembled by the distributor"。 |
| **BayWa r.e. + Solar-Planit** | 58 次/3 文件（BayWa 39 + Solar-Planit 19） | benchmark §1.3、§2.2；pv-wholesale §1.3（Solar-Planit 八步流程、Speicher-Sets、储能容量图表引 HTW）；`NR/old-repo-021-planner-positioning.md`。**Solar-Planit 是名字被引最多的单体设计工具**。关键句（pv-wholesale §1.3）：Solar-Planit 流程"1 选地点 → 2 屋顶类型和尺寸 → 3 支架和静力 → 4 排布组件 → 5 **选择匹配的逆变器和储能** → 6 用电曲线、经济性 → 7 附加商品 → 8 完整物料清单转入 BayWa 网店"。 |
| **Segen** | 38 次/4 文件 | benchmark §3.3（19 次，"the most built-out distributor planner in Europe"）；pv-wholesale §1.4（16 次）；planner-methods、old-repo-021 各 1 次。关键句（benchmark §4.1）："Design → order is one continuous motion… Quotes carry **price locks (7–30 days)**"。 |
| **IBC SOLAR（PV Manager / Speicherpakete）** | 33 次/3 文件（IBC 25 + PV Manager 8） | pv-wholesale §1.5（PV Manager：带 Logo 报价 PDF、完整物料清单一键下单）；old-repo-021。 |
| **EWS（pv.de，QuickCalc/QuickPlan）** | 12 次/3 文件 | pv-wholesale §1.6（9 次）；planner-methods §2.5（2 次，"用户提到的 QuickCalc：两次 Apify 检索都没找到同名的批发商工具"——即它在文献里的角色是"行业 quick calc 原型"）；old-repo-021。关键句（old-repo-021）："批发商的'规划器'是**为一次询价做快速计算**…（EWS QuickCalc、Segen 报价工具、BayWa 储能容量图表引用 HTW 独立性计算器）"。 |

**决策链**：benchmark §4.2/4.3 的总裁定写进了旧仓蓝图 v2（`OR/docs/blueprint/2026-08-29-restructure-blueprint-v2.md` M1）："行业对标（8 工具 + 5 平台）：无一例外即时出结果、服务器端项目、人工审核只作可选增值"；再落地为旧票 `OR/.scratch/restructure/issues/003-instant-results-all-viewers.md`（即时结果）与 `004-tool-frame-defunnel.md`（摘除漏斗、三工具平行入口）；最终进入新仓 `NR/docs/specs/14-solution-configurator.md`（三屏）与 AGENTS.md §1。

### 第 2 层：方法与数据权威（被引最多，但不是视觉参考）

| 来源 | 计数 | 证据路径与关键原句 |
|---|---|---|
| **HTW Berlin** | 58 次/5 文件 | `NR/planner-methods.md`（50 次，§2.2 全节）；`NR/docs/specs/14-solution-configurator.md`（4 次：定容三上限、查表）；`NR/docs/acceptance/2026-10-09/14/sources.md`（引擎规则逐条溯源 + `data/htw/` 查表 byte-read，附 Apify run id）。关键句（planner-methods §2.2）："可用容量 ≤1.5 kWh / kW PV；≤1.5 kWh / MWh·a"。 |
| **PVGIS（JRC）** | 47 次/9 文件 | 全线引用（canvas-imagery-lod2、planner-input-sufficiency、planner-methods、spec 14…）。产量物理链权威：`loss=14%` 默认值、TMY、printhorizon。 |
| **VDE-AR-N 4105 / IEC 60364-7-712 / IEC 62548** | 规则级 | `NR/docs/acceptance/2026-10-09/14/sources.md`（4.6 kVA 单相上限、30 kVA NA-Schutz、135 kW 分界、串熔断判据）。 |

### 第 3 层：厂商设计工具（报告与推荐面的参考）

| 来源 | 计数 | 证据路径与关键原句 |
|---|---|---|
| **SolarEdge Designer** | 31 次/4 文件 | benchmark §1.2（15 次）；pv-wholesale §3.2（9 次，2026-09 版储能推荐"按实际日用电量优先推荐合适容量"）；planner-methods（6 次）。厂商侧被引最多的单体。 |
| **SMA Sunny Design** | 12 次/5 文件 | benchmark §1.1（quick/detailed 双速模式："quick planning mode with system design in just a few steps"）；planner-input-sufficiency §1.4。 |
| **Fronius Solar.creator** | 29 次/2 文件（含 Fronius 其它条目） | benchmark §1.3（向导式 step-by-step、可分享报告）。 |
| **Huawei SmartDesign 2.0 / GoodWe EzDesigner II / Enphase System Builder / Solargraf** | 19/9/11/8 次 | benchmark §1.4–1.5、pv-wholesale §1.3、§3.2。**Enphase System Builder 是文献里唯一逐步骤记下的厂商配置器流程**（BayWa 博客四步：国家与配置类型（含加装）→ 组件功率/数量/朝向 → 微逆与相数/kWh → 电池与选项，pv-wholesale §1.3，博客带公开截图 URL）。 |
| **PV*SOL / PVsyst / Aurora / HelioScope** | 3/5/3 次 | planner-input-sufficiency（输入充分性分级、P50/P90 语义）；`OR/.scratch/encyclopedia-research/26-tools-not-linker.md`（四类工具边界，文案防串味）。 |

### 第 4 层：独立设计平台（2026-08-28 基准的对照样本）

OpenSolar（16 次/2 文件，"Ada"秒出多方案、跨分销商一键下单）、Easy PV / Midsummer（14 次/1 文件，benchmark §2.2 称其为 "the closest analogue to de-linker's ambition"，四档设计深度 + BOM 一站购）、K2 Base（11 次/2 文件，BOM 直传分销商购物车）。三者均为一次性基准样本，后续文献不再复引。

### 第 5 层：调研过但被明确裁定"不适用"的

- **EcoFlow PowerOcean 业主配置器**（pv-wholesale §3.2 调研，§4.5 裁定）："这些都**面向业主**…de-linker 的买家是安装商"。注意：`OR/.scratch/ecoflow-evidence-gate/` 是 EcoFlow **商品页**事实/FAQ/图片的证据门，与配置器无关；新仓 EcoFlow 高频出现（67 文件）全是商品品牌语境。
- **Amazon Alexa for Shopping / 美团小团 / 淘宝千问**（`OR/.scratch/website-direction-review-20261008/competitor-prototype/research.md`）——Advisor（Genie）的竞品研究，不是配置器的。
- **Preline AI 模板**（`OR/docs/research/2026-09-12-preline-ai-reference.md`）——Advisor 对话 UI 的参考，不是配置器的。

### 我们自己的旧实现（内部证据，磁盘素材最全）

- 旧线上 **Linker Planner**（`https://de-linker.com/linker-planner/`，WP page，bundle `quote-configurator.bundle.js` 6,853 行）：交互实录 `OR/docs/research/2026-09-22-planner-interaction-for-demonstration.md`、`2026-09-22-what-using-the-tools-is.md`；结构盘点 `NR/docs/research/2026-10-09/old-repo-plugin-and-planner-inventory.md`；页面模板 `OR/pages/linker-planner/page.html`。
- 旧线上 **Linker Site Detail**（屋顶步的前身）：实录 `OR/docs/research/2026-09-22-site-detail-interaction-for-demonstration.md`；LoD2/影像链 `OR/docs/research/2026-08-29-canvas-imagery-lod2.md`。
- 新栈 **#14 Solution Configurator**（已实现）：`NR/docs/specs/14-solution-configurator.md`；源码 `NR/plugins/linker-tools/src/configurator/`；验收 `NR/docs/acceptance/2026-10-09/14/` 与 `2026-10-10/14/`；改良提案 `NR/docs/acceptance/2026-10-12/visual-round2/`（D1 报告两列、D2 步骤条 sticky）。

---

## ② 最常参考来源的设计语言拆解

### ②-A 德国批发商同业组定义的"quick calc"形态（外部参考的主干）

从两轮调研文献合并拆解（无本地截图，形态以文献原句为准）：

1. **步骤结构 = 收窄漏斗，不是自由画布。** 同业输入顺序（pv-wholesale §4.1）："项目类型（新建/加装/换机/商用）→ 相数 → 功率 → 储能（HV/48V、可用 kWh）→ 备用电源（ja/ja mit Zubehör/nein）→ 接口与控制 → 可选年用电量"。Enphase System Builder 四步与 Solar-Planit 八步是同一形状的两种深度。
2. **双速 UX。** SMA quick/detailed 双模式、Easy PV 四档设计深度、Segen Quick Quote vs System Designer（benchmark §4.1 第 5 条："Dual-speed UX. Quick lane + detailed lane, switchable"）。我们的"屋顶步可选"即此模式的裁剪。
3. **输出 = 带数量的物料清单（Stückliste/BOM）→ 购物车/报价 PDF/项目询价。** benchmark §4.1 第 4 条："Design → order is one continuous motion"。报价带 7–30 天锁价（Segen）；报告带 Logo（IBC PV Manager、EWS QuickCalc）。
4. **兼容 = 三值放行语义。** freigegeben / mit Zubehör / nicht freigegeben，条件附 DC 降额、最少模块数、固件下限（Memodo 放行清单，pv-wholesale §2.3/§4.2）。
5. **入口准入。** 价格登录可见、说明与放行清单公开（Krannich "Preis anfragen"、Memodo、Segen、BayWa、IBC 一致，pv-wholesale §4.4）。
6. **双受众输出。** 安装商面（BOM、净价、组串）与终端客户面（收益、无贸易价）分开（Easy PV FAQ，benchmark §4.1 第 7 条）。
7. **终点留人。** "工具最后都交回给人"（pv-wholesale §0 第 3 条：EWS 指向报价部门、Krannich Projektanfrage、PVSelected 24 小时人工报价）。

### ②-B 我们自己两代实现的实际设计语言（磁盘素材可复刻的部分）

**旧线上 Linker Planner（2026-09-22 实测，模板 `OR/pages/linker-planner/page.html`）：**

- **骨架**：双栏壳 `qcfg-card lp-shell`——左栏工作表 `lp-brief`（1.48fr，右分隔线）+ 右栏结果面板 `lp-plan`（0.78fr，`lg:sticky lg:top-6`，浅底 `#fbfcfd`）；壳为白卡、圆角 22px、大投影 `0 28px 70px rgba(11,31,51,.12)`；≤980px 折单栏（page.html:244-249）。
- **输入面控件形态**：三张项目类型分段卡（Residential / Commercial & industrial / Utility，选中青色描边）→ 五张任务意图卡（New system / Extend / Replace / Check a model / Not sure）→ 系统优先级卡 → 场地步（邮编 5 位校验、年用电、kWp、相数；备用负载/时长可空）→ 主按钮 "Build the initial solution"（计算中变 "Calculating…"，shimmer 骨架屏四块）。
- **结果/报告版式**：右栏 "Your Project" 四事实行（Project type / Specified hardware / System priority / Site basis，各带 Edit）+ KPI 四格（Storage / Inverter / Self-sufficiency / Annual generation）+ "CURRENT ASSUMPTIONS" 假设块（邮编质心、35°/180°、H25 曲线）+ 物料清单行（可得性、净价小计）+ 储能量扫 6 档（5/7.5/10/12.5/15/20 kWh，点档重算）+ 出口排（PDF/CSV/客户报告/Site Detail/Advisor/Technical Review/Add to cart/Save as quote）。
- **状态机**：前置拒绝（缺相数点名 "Grid phase"；设备用途须重确认；超范围 422 `unsupported_scope` 回退"方向而非计算"）；数字与假设永远分列。

**新栈 #14 三屏实现（`NR/plugins/linker-tools/src/configurator/`，验收截图为准）：**

- **三屏**：Inputs（三段 tab：住宅/工商业/电站 + 可选屋顶步）→ Solution（方案卡可换同类备选、"Add all to solution draft"、"Save solution"）→ Design report（方案下方，带 Logo PDF）。
- **令牌**：`configurator.css` 头部声明全部用站点 `--proto-*` 令牌（fallback 即线上值）：ink `#0c0f0f`、muted `#5a6363`、line `#e2e5e5`、accent `#0c7f73`（青）、soft `#f1f9f8`、radius 12px、容器 77.5rem、字体 Plus Jakarta Sans。与门店（replication-spec §2 实测令牌：ink `#15352f`、teal `#0c7f73`、cream `#f7f7f1`）**同族不同壳**——门店是像素级复刻线上，工具页允许自有设计但共用色彩/字体/圆角语汇（AGENTS.md 2026-10-10 裁定：只有工具应用内页可有自己的设计）。
- **步骤条**：`Steps.tsx` 数字步骤 1/2/3（`linker-steps`），≤860px 有 sticky 改良提案（visual-round2 D2）。

---

## ③ 可复用素材资产表（绝对路径，均已 ls 验证）

### A. 新栈 #14 配置器验收截图（当前实现的权威视觉记录，git 已跟踪）

| 路径 | 内容 | 规格 |
|---|---|---|
| `/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-10/14/` | 三屏全状态验收：inputs-empty/roof-applied、solution-{proposal,computing,error,no-candidate,added,saved,unverified}、report-report、roof-outline、commercial-{empty,indicative,sized}、utility-form、logo-{en,de} | 约 60 个 PNG，EN/DE × 1440/390；例 solution-1440-en-proposal.png 为 1440×5029 全页图 |
| `/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-10/14/report-en.pdf` 与 `report-de.pdf` | 设计报告 PDF 样张（EN/DE） | 各 1 份 |
| `/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-09/14/` | 同套早期轮（含 `sources.md` 引擎规则溯源） | 约 50 个 PNG |
| `/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-12/visual-round2/comparisons/CMP_D1.png`、`CMP_D2.png` | 配置器改良提案三栏对比图（当前/线上/改良后）：D1 报告两列、D2 步骤条 sticky | 2 个 PNG |
| `/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-12/visual-round2/proposals/D1_report-columns-1440-{before,after}.png`、`D2_steps-sticky-390-{before,after}.png` | D1/D2 提案前后对照 | 4 个 PNG |
| `/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/` | 现行源码（App/Steps/Field/Table/configurator.css 等）+ `.storybook` | 可直接跑 Storybook |

### B. 旧线上 Planner/Site Detail 实测素材（旧仓，只读）

| 路径 | 内容 | 规格 |
|---|---|---|
| `/Users/chesterjohn/Documents/de-linker-project/.scratch/six-tool-trial-cuts/recordings/planner-logged-in.webm` | 伙伴登录态 Planner 全程操作录屏 | 1440×900，40.7 s |
| `…/recordings/planner-logged-out.webm` | 匿名态 Planner 录屏 | 1440×900，36.4 s |
| `…/recordings/advisor-logged-{in,out}.webm` | Advisor 录屏（交接链参考） | 1440×900 |
| `…/002-seen/`（logged-{in,out}-{commercial,utility}）、`003-seen/`、`004-seen/`、`005-seen/` | 分步截图 + 每步 yml 元数据：商业/电站段、四类任务改写问题、Site Detail 到组件数、Advisor 其它路径；如 `002-seen/logged-out-commercial/05-initial-solution.png` | 共 40 张 PNG（1440×900） |
| `…/001-residential-path-seen.md` 至 `007-site-detail-modules-en.md` | 每条路径"屏幕上实际发生了什么"的逐屏文字记录（006 为业主核对记录） | 7 个 md |
| `…/films/site-detail-modules-en/out/planner-walk-en.mp4`、`planner-walk-de.mp4` | Planner 成品演示片（EN/DE，字幕烧入） | 1512×762，71.1 s / 70.1 s |
| `…/out/design-canvas-walk-en.mp4`、`design-canvas-walk-de.mp4` | Site Detail 成片（屋顶步参考） | 1512×890，78.5 s / 72.3 s |
| `…/out/planner-how-to-en.mp4`、`site-detail-modules-en.mp4`、`advisor-compare-en.mp4` | 其余成片（"How this tool works" 系列） | 1440×900，56 s / 22 s / 23.5 s |
| `…/films/site-detail-modules-en/public/` | 源素材：planner-walk-src.mp4、canvas-{en,de}-src.mp4、planner-de-src.mp4、still-canvas-*.png、open/outline/sizing.png、captions JSON、旁白 wav/mp3 | 71 个文件 |
| `/Users/chesterjohn/Documents/de-linker-project/pages/linker-planner/page.html` | 旧线上 Planner 页面模板（双栏壳标记与全部文案） | 1 份 HTML |
| `/Users/chesterjohn/Documents/de-linker-project/output/tool-demonstration-films/planner-en.mp4`、`planner-de.mp4` | 线上工具影片的本地拷贝（"How this tool works · 39s"） | 1440×900，34.5 s / 34.2 s |
| `…/output/planner-jev-demo/planner-demo.mp4` | Planner 演示裁片 | 1440×900，15.1 s |
| `…/output/visual-completion-100/`（planner-de-desktop.png、live-planner-mobile-de-{metrics,documents}.png、live-planner-320-de-documents.png、canvas-de-390.png、live-canvas-{final-de,equipment-and-conditions}.png 等） | 旧线上 Planner/Site Detail 视觉完成度证据（桌面+移动） | 8+ 个 PNG |
| `…/output/advisor-remediation/`（planner-metrics-en-336.png、planner-exact-335.png、tool-frame-planner-en-1440.png、canvas-*.png 等 24 张） | 旧线上 Planner/Canvas 各状态治理前后截图 | 24 个 PNG |
| `…/output/system-delivery/`（planner-actions-{before,after}-{en,de}.png、canvas-interaction/、releases/linker-planner-en/<17 个时间戳>/） | 交付与发布记录截图 | 30+ 个 PNG |

### C. 外部产品素材

**无本地截图、无录屏。** 两轮外部调研都是 Apify 文字抓取：`NR/docs/research/2026-10-09/pv-wholesale-selection-tools.md` 开头明说"**本次没有在本地截图。**下文给出各工具官方页面上公开的截图 URL"；benchmark 对登录墙工具逐一标注 "(login wall)"。文献里给出的唯一公开截图 URL 族：IBC PV Manager 两张（`OR/docs/research/…` 未存，见 pv-wholesale §1.5 引用的 ibc-solar.de fileadmin PNG）、BayWa 博客的 Enphase System Builder 四步截图（pv-wholesale §1.3）、Sonepar Suisse PV-Konfigurator 帮助页截图（§1.8）。复刻外部工具需按 AGENTS.md §6 经 Apify 现抓。

---

## ④ 给 /prototype 的复刻建议

业主要的是"参考设计复刻并做出来原型供我选择"。按证据，建议 **一条主线 + 两条对照线**，共三组原型：

**主线（P0）：复刻旧线上 Linker Planner 的双栏壳，落到三屏骨架上。**
- 参照素材：`recordings/planner-logged-{in,out}.webm`（动效）+ `002-…-005-seen/`（分步静帧）+ `pages/linker-planner/page.html`（结构）+ 新栈 `docs/acceptance/2026-10-10/14/`（三屏现状）。
- 复刻面：① 左工作表/右 sticky 结果面板的双栏壳（1.48fr/0.78fr、22px 圆角白卡、右栏浅底）；② 分段卡+意图卡的输入控件族；③ KPI 四格 + CURRENT ASSUMPTIONS + 储能量扫档条的结果版式；④ 前置拒绝态（点名缺项、方向性回退）。
- 视口：**1440×900**（全部既有素材的视口）+ 390×844（新验收已有移动态，D2 提案证明 ≤860 需 sticky 步骤条）。

**对照线 1（P1）：同业"quick calc"形态原型。** 以 Solar-Planit 八步与 Enphase System Builder 四步为骨（文献证据最全的两个外部流程），做"输入 → 即时方案（1–3 个可换备选）→ Stückliste → 询盘/加草稿"的单栏向导。此线无本地像素素材，只能按 ②-A 的文献拆解重建；若要贴真实页面，先经 Apify 现抓（外部研究铁律），不要凭记忆画。
**对照线 2（P2）：新栈现状 + D1/D2 改良。** 以 `docs/acceptance/2026-10-10/14/` 为底，套用 visual-round2 的 D1（报告两列）与 D2（移动 sticky 步骤条），验证"最小改动路线"的观感。

**色彩与令牌**：三组共用站点令牌（accent teal `#0c7f73`、ink、line、12px radius、Plus Jakarta Sans——replication-spec §2 与 configurator.css 一致），保证原型无论选哪组都不脱离门店语汇（业主 2026-10-10：工具页可自有设计，但站点外观是硬约束的参照系）。

**不要参考的**：EcoFlow 业主问答式配置器（面向业主，已裁定不适用）、屋顶 3D/静力计算类全设计工具（Solar-Planit/PV Manager/pvXpert 的支架与静力面——benchmark §4.2 明确"屋顶描绘只有在喂给真实工程时才值得"）、Amazon/美团/淘宝式对话购物（属 Genie 范围）。

---

## ⑤ 明确写明"参考了 XX"的决策记录（问题 5 的直接答案）

1. `NR/docs/specs/14-solution-configurator.md` 第 3 行（依据行）："依据：`docs/research/2026-10-09/planner-methods.md`（方法规格与 P0/P1 清单）、`pv-wholesale-selection-tools.md`（同类形状）、`old-repo-plugin-and-planner-inventory.md`（旧引擎知识的来源）"。
2. `NR/docs/acceptance/2026-10-09/14/sources.md`：引擎每条规则逐条登记来源——HTW Berlin（三上限、效率、查表 byte-read + Apify run id）、VDE-AR-N 4105、PVGIS 14%、IEC 60364-7-712/62548 串熔断、MsbG §55、Intilion/Voltfang（C&I 定容）。
3. `OR/docs/blueprint/2026-08-29-restructure-blueprint-v2.md` M1："行业对标（8 工具 + 5 平台）：无一例外即时出结果、服务器端项目"——指向 benchmark 全体 11 工具。
4. `OR/.scratch/restructure/issues/003-instant-results-all-viewers.md` 与 `004-tool-frame-defunnel.md`：即时结果与摘除漏斗两张票（benchmark 结论的落地件）。
5. `NR/docs/research/2026-10-09/old-repo-021-planner-positioning.md` §行业怎么做："EWS QuickCalc、Segen 报价工具、BayWa 储能容量图表引用 HTW 独立性计算器……更深的设计（组串、单线图、支架）属于 Solar-Planit、PV Manager、pvXpert 这类设计工具……制造商侧（Sunny Design、SolarEdge Designer）做经济性与储能推荐"。
6. `NR/docs/specs/8-decisions.md`：`mat_trina_solar_tsm_460neg9r_28` 参考组件裁定（屋顶步的设计假设披露来源）。
7. `NR/docs/acceptance/2026-10-12/visual-round2/proposals/README.md`：D1/D2 配置器改良提案（当前栈对照线上旧 Planner 的实测记录）。

## 引用计数附表（12 文献 corpus，2026-10-12 grep）

| 来源 | 总次数 | 出现文件数 |
|---|---|---|
| HTW | 58 | 5 |
| BayWa（含 Solar-Planit 19） | 58 | 3 |
| Memodo | 54 | 3 |
| Krannich | 54 | 2 |
| Segen | 38 | 4 |
| SolarEdge | 31 | 4 |
| PVGIS | 47 | 9 |
| Fronius（含 Solar.creator） | 29 | 2 |
| IBC（含 PV Manager 8） | 33 | 3 |
| Huawei SmartDesign | 19 | 2 |
| OpenSolar | 16 | 2 |
| Easy PV | 14 | 1 |
| Enphase | 11 | 1 |
| K2 Base | 11 | 2 |
| QuickCalc（EWS） | 12 | 3 |
| Solargraf | 8 | 1 |
| EcoFlow | 9 | 2 |
| EzDesigner（GoodWe） | 9 | 2 |
| Aurora / HelioScope / PV*SOL | 5 / 3 / 3 | 各 1–2 |

（GoodWe/EcoFlow 在新仓全库的高频出现主要是**在售商品品牌**语境，不代表设计参考；本表已限定在配置器文献 corpus 内。）
