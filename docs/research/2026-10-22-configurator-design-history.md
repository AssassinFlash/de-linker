# Solution Configurator 是怎么设计出来的

调查日期：2026-10-22（Asia/Shanghai）。本笔记依据本机文档、Git 提交与 GitHub 票据回溯设计过程。本轮不抓外站、不改业务代码、不写生产。

调查范围：已核对界面与交互设计历史、计算依据、当前检出中的计算路径和原始交付记录。下文所说“当时”均指历史记录；本轮没有重新操作线上配置器，不将历史验收当作 2026-10-22 全链上线保证。

核心结论：业务形态来自欧洲光储批发商的快速计算与物料清单流程；工程方法采用 HTW Berlin、PVGIS 与厂商放行文件；桌面界面由业主选择 B+C 原型融合，手机端随后参考业主提供的房产 App 设计稿调整。它是围绕 Linker 商品与询盘链开发的工具。计算结果由代码、数据与规则产生。

## 已证实的界面结论

正式界面经过“调研同业的业务形态 → 做三组可操作原型 → 业主选 B+C 融合 → 按业主反馈补齐 C 的视觉 → 单独适配移动端”五步。没有证据支持“整套界面照抄某一个竞品”。最直接的界面选择记录是 2026-10-12 的 [Issue 14 评论](https://github.com/AssassinFlash/de-linker/issues/14#issuecomment-6123583871)：记录明确写明“业主 2026-10-12 选定”，保留 B 的左侧竖排步骤栏，右侧采用 C 的展开式表单。

## 一、外部参考究竟提供了什么

2026-10-12 的来源考古档案把参考分为三层：德国 B2B 光储批发商定义业务形态；HTW Berlin、PVGIS 等提供计算方法；我们自己的线上 Planner 与新栈第一轮验收提供实际可对照的界面素材。参见 [DOSSIER](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-12-configurator-sources/DOSSIER.md:16) 与 [同业调研](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/pv-wholesale-selection-tools.md:17)。

| 来源                                       | 当时借鉴的部分                                                                                                                       | 原始证据                                                                                                                                                                                                                     |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Memodo 工具箱、Vergleiche & Freigabelisten | 项目信息采集、逆变器与电池兼容/放行、带条件的备用电源能力                                                                            | [同业调研](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/pv-wholesale-selection-tools.md:27)；档案登记的一手页面：https://www.memodo.de/m/werkzeuge/memodo-vergleiche-freigabelisten/                      |
| Krannich WR-Speicher-Sets、专业选型工具页  | 以相数、功率、储能、备用能力等参数收窄组合，强调组合兼容，大项目交给项目询价                                                         | [同业调研](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/pv-wholesale-selection-tools.md:49)；档案登记的一手页面：https://shop.krannich-solar.com/de-de/WR-Speicher-Sets                                   |
| BayWa Solar-Planit                         | 地点与屋顶 → 组件 → 匹配逆变器/储能 → 物料清单转入业务链。它是来源档案里被提及最多的单体设计工具，但“出现次数”不能换算为视觉贡献比例 | [同业调研](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/pv-wholesale-selection-tools.md:60)；档案登记的一手页面：https://solar-planit.com/                                                                |
| Enphase System Builder（BayWa 的教学页面） | 有公开步骤记载的向导：国家/配置类型/相数 → 组件 → 微逆 → 电池与选项，最终形成物料清单                                                | [同业调研](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/pv-wholesale-selection-tools.md:80)；档案登记的一手页面：https://solar-distribution.baywa-re.de/blog/der-system-builder-von-enphase-energy/       |
| Segen Portal / Kit Builder                 | 快速报价与深度设计并存，配置后继续进入报价或采购工作                                                                                 | [同业调研](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/pv-wholesale-selection-tools.md:84)；档案登记的一手页面：https://www.segen.co.uk/portal/                                                          |
| IBC PV Manager、EWS QuickCalc              | 完整物料清单、带安装商 Logo 的文件、计算后交回团队/报价部门                                                                          | [同业调研](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/pv-wholesale-selection-tools.md:96)；档案登记的一手页面：https://www.ibc-solar.de/installateure/produkte/pv-manager/ 与 https://pv.de/leistungen/ |
| SMA Sunny Design、SolarEdge Designer       | 快速/详细双模式、按实际负荷作储能推荐、可分享报告等对照模式                                                                          | [DOSSIER](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-12-configurator-sources/DOSSIER.md:45)                                                                                                                |

这些网址本轮没有重新访问；它们用于标识当时档案登记的来源，不能据此声称今天竞品仍提供相同行为。

来源档案明确写明，两轮外部研究主要是 Apify 文字抓取，没有保存外部工具的本地截图或录屏；部分页面有公开图片 URL，很多实际工具在登录墙之后。因此有证据的是流程与输出形态的归纳，不能说 C 对某个外部工具做过逐像素复刻。见 [DOSSIER 外部素材边界](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-12-configurator-sources/DOSSIER.md:137)。

## 二、A / B / C 分别是什么

三组原型于 2026-10-12 归档。可追溯原始 [README（固定提交）](https://github.com/AssassinFlash/de-linker/blob/52a260d4e3968d5e3aded25eb505e82b4cbdc9ae/plugins/linker-tools/src/configurator/prototype/README.md) 与 [原型脚本](https://github.com/AssassinFlash/de-linker/blob/52a260d4e3968d5e3aded25eb505e82b4cbdc9ae/plugins/linker-tools/src/configurator/prototype/proto-configurator.js)。原型是用样例数据做的可点击设计实验，不计算、不保存、不发送询盘；其样例数字、产品组合与放行徽章不构成工程证据。

| 原型                  | 结构                                                           | 明确写下的参考                                                                                                          |
| --------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| A：工作表与结果双栏   | 左工作表、右结果摘要，同屏工作台                               | 之前线上 Linker Planner 的结构。README 明确说只是结构参考，不冒称逐像素复刻                                             |
| B：安静画布，逐题输入 | 窄步骤栏、逐题聚焦，回答折成摘要；结果和报告使用干净的文档排版 | README 明确写“参考 ChatGPT 的灰阶、留白与圆角输入”。这是作者记录的视觉参考，不等于配置器由 ChatGPT 对话模型生成选型结果 |
| C：分步向导           | 顶部步骤导航、单步表单、结构化结果表                           | 同业向导的流程组织；README 明确承认缺少外部工具真实截图的部分不能称忠实复刻                                             |

三组设计可用 A/B/C 参数直接切换，且都能直接查看 inputs / solution / report 三种状态。票据的 [原型交付评论](https://github.com/AssassinFlash/de-linker/issues/14#issuecomment-6120820908) 记载了桌面与手机的输入、结果、报告检查，以及原型手机溢出的修正。

## 三、业主选的是 B+C 融合

2026-10-12 19:43（Asia/Shanghai）的 [选择记录](https://github.com/AssassinFlash/de-linker/issues/14#issuecomment-6123583871) 明确写明：

- B 左侧竖排步骤栏：01 Inputs / 02 Solution / 03 Design report。
- C 右侧展开式表单：分区标题、右上 Step 指示、PROJECT TYPE 卡片组、TASK 区、底部 Continue。
- 保留真实计算、选型、询盘链路；换型后的滚动落点仍需可见。
- 原型只作设计参照，正规实现另开分支。

[PR 122](https://github.com/AssassinFlash/de-linker/pull/122) 的最终说明同样称 selected B+C design：左边 B 的竖排步骤栏，右边 C 的展开分区表单。该 PR 于 2026-10-12 21:59 合并。可据此说“你当时看过三个方案，选了 B 的导航加 C 的内容区”；不宜缩写成“你选了 C”，否则会遗漏最显眼的左栏来源。

## 四、为什么后来还补做一次 C 视觉移植

第一次 B+C 实现完成后，业主指出右侧只有 C 的内容骨架，没有 C 的视觉。[PR 126](https://github.com/AssassinFlash/de-linker/pull/126) 与 [C fidelity 证据](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md:1) 都记录了这次打回和修正。PR 于 2026-10-13 02:44 合并。

第二次移植补齐了以下外观：

- 白卡片浮在浅色画布上，边框、轻阴影与圆角。
- SITE / CONNECTION / GOALS / PROJECT 这些分组的小标签 chip。
- 项目类型的两行选择卡：粗体标题加灰色范围说明。
- 分区头的粗标题与右侧 Step 提示。
- 卡片底部的浅色提交条与右对齐深绿主按钮。
- 输入框、留白、字号、选择箭头与空态提示框。

当时保留 B 左栏；没有搬 C 的顶部步骤条，以免出现两份步骤导航。C 原型中的 TASK 下拉和 Similar systems 是演示用输入，正式引擎没有对应字段，所以没有搬入正式系统。这个差异是证据里明确登记的取舍，不宜对老板说原型的每个字段都已实现。见 [C fidelity §4](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md:95)。

视觉移植也不是机械复制每个渲染像素：记录中有三处 CSS font 简写在浏览器被丢弃，正式实现采用原型源码想表达的字号/字重，并明确记录了差异。对照截图和测量可以证明具体继承了哪些元素，却不应表述为“正式界面与 C 全屏像素完全一致”。见 [C fidelity §3](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md:71)。

## 五、移动端还有独立的视觉来源

2026-10-13 的 [移动适配 README](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-13/configurator-mobile/README.md:3) 明确注明参考“业主 2026-10-13 提供的房产 App 设计稿”，原图保存为 [ref-realestate-app.png](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-13/configurator-mobile/ref-realestate-app.png)。档案没有写这张图属于哪一家 App，不能凭图片命名猜品牌。

这次只改手机宽度：单列卡片、更大的输入和触控区域、整行选择卡、屋顶地图加底部抽屉、无候选与报告就绪状态、固定底部步骤导航。桌面 1440 的前后视口截图在当时记录为像素差 0。适配提交 [5f599b93](https://github.com/AssassinFlash/de-linker/commit/5f599b93ae0e1391ccb28e37792a17c9886ff7b0) 在 2026-10-13 23:07，合并 [3072ba51](https://github.com/AssassinFlash/de-linker/commit/3072ba518d217f9a38f6b9bea525e1a85ff015a8) 在 2026-10-14 00:06。

## 六、可以直接对老板说的界面解释

“这个配置器先研究了德国光储批发商怎么做安装商选型，主要看了 Memodo、Krannich、BayWa 的 Solar-Planit、Segen、IBC 和 EWS。借鉴的是从项目参数选到兼容系统、再给物料清单和报告的工作方式。界面我们另外做过三套可以操作的原型：双栏工作台、安静的逐题输入、分步表单。最后选的是融合方案，左边用 B 的三步导航，右边用 C 的展开表单和卡片。第一次实现后又按反馈补齐了 C 的视觉，手机端再参考当时给的房产 App 设计稿做触控和地图适配。所以它有同业流程依据，也有我们自己的原型选择过程。”

以上是一段依据记录整理的说明，不是业主当时说话的逐字转录。计算方法与选型数据见第八节，包含业务和方法的完整口头版本见第十节。

## 七、证据与推断的界线

已证实：三套原型存在；B 的 ChatGPT 视觉参考有 README 明文；B+C 的业主选择有票据明文；右侧 C 视觉被打回并补齐有 PR 与验收明文；移动端参考房产 App 设计稿有原图和 README。

调查者归纳：同业业务模式、内部既有实现、原型融合共同构成最终设计。可以解释为“为什么长成这样”，但不能冒充业主说过的设计理念。

不能据现有记录声称：整套照抄 Solar-Planit；老板单独选了 C；外部工具都有实操截图；引用频次等于实际设计贡献；原型样例组合是工程结果；2026-10-13 本地验收自动证明 2026-10-22 生产正在跑完全相同的代码。

## 八、计算和选型为什么这样设计

### 1. 先确定它服务哪一条业务链

规格把配置器定义为“输入 → 整套方案 → 设计报告”，方案可整体加入 Solution draft，再进入询盘；正式交易由团队线下处理。产品来自 WooCommerce，组合根据兼容数据计算，不新增套装 SKU。三种项目的处理深度不同：住宅快速选型；工商业有 15 分钟负荷数据时计算，没有时给指示范围和询盘出口；电站收集项目询盘。依据为 [规格三屏定义](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:5)、[项目业务定义](/Users/chesterjohn/Documents/de-linker/AGENTS.md:5) 与 [工商业实际计算入口](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:1)。

### 2. 计算方法曾经做过一次实质重写

2026-10-09 的方法复盘对旧实现做了离线复现实验：8 个典型户型的住宅可用电池推荐量为所引用 HTW 上限的 1.13–2.0 倍；报告还指出自给率偏乐观，以及不同工商业负荷形状得到同一推荐量。这是当时替换住宅定容、查表与工商业方法的具体证据。保留的是经核实的产品事实、兼容关系和物料知识；新仓库另写实现。见 [复盘结论](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/planner-methods.md:10)、[8 户型复现实验](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/planner-methods.md:457)。

新引擎、三屏应用、屋顶和 PDF 于 2026-10-10 15:19 经 [PR 48](https://github.com/AssassinFlash/de-linker/pull/48) 合入。票据的 [交付记录](https://github.com/AssassinFlash/de-linker/issues/14#issuecomment-6092557317) 当时记录了 10 kWp 三相系统、物料加入后读回、英德 PDF、真实屋顶夹具与本地界面验收；同时明确最初使用数据契约替身，后续要接真实数据。这个日期证明第一轮实现落地，不能覆盖之后所有集成与部署。

### 3. 当前检出中能直接看到的方法

| 部分             | 实际设计与来源                                                                                                                                                            | 当前代码 / 数据证据                                                                                                                                                                                                                                                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 发电量           | 由邮编定位和屋面功率、倾角、方位请求 PVGIS；通过 pvlib 获取其产量序列，汇总年/月数据，以历史年份差异形成区间                                                              | [pvgis.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/pvgis.py:1)、[residential.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/residential.py:74)                                                                                                                             |
| 住宅储能容量     | 采用所引用 HTW 的三条建议：PV 至少 0.5 kWp/MWh 年用电才建议日常自用储能；可用容量受 1.5 kWh/kWp 与 1.5 kWh/MWh 年用电两个上限约束；备电预留另算，热泵与电动车扩展用电区间 | [htw.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/htw.py:1)、[rules.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/rules.py:29)、[当时逐条来源取证](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-09/14/sources.md:13)                                     |
| 自给率、自用比例 | 使用 HTW 独立性计算器的预计算表，以双线性插值查值并输出区间。它依赖典型家庭参考模型，报告须表达假设与限制                                                                 | [htw.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/htw.py:105)、[原始表与来源哈希](/Users/chesterjohn/Documents/de-linker/services/engine/data/htw/source.json:1)                                                                                                                                          |
| 实际设备选型     | 从 Woo 商品生成的工程 feed 读取产品，按用途、相数、厂家 PV 输入上限等筛选；再按厂商兼容放行、模块堆叠与配件条件组成系统，保留同类备选和原因                               | [residential.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/residential.py:1)、[eligibility.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/eligibility.py:1)、[compatibility.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/compatibility.py:1) |
| 屋顶可选步骤     | 官方航拍与 LoD2 建筑数据提供轮廓/屋面基础，也有手绘路径；估组件布置、数量和功率，回填配置器。没有屋面信息时发电量默认 35° 朝南并披露                                      | [规格](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:7)、[residential.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/residential.py:74)、[取证中的地图与建筑来源](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-09/14/sources.md:95)                       |
| 工商业           | 上传 15 分钟负荷数据后按峰值、削峰面积和补电空间分析 kW/kWh；未提供时采用指示范围，交给团队继续处理                                                                       | [commercial.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:1)                                                                                                                                                                                                                                 |

一个便于口头解释的例子：10 kWp、家庭年用电 5,000 kWh，在没有热泵、电动车和备电预留时，代码中的 HTW 日常可用容量参考上限为 `min(1.5 × 10, 1.5 × 5) = 7.5 kWh`。随后还要映射到真实放行的离散电池配置；若最小合法配置已经高于参考上限，会在报告中提示，不能把 7.5 kWh 说成任意品牌都能精确买到的产品。见 [htw.size](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/htw.py:79) 与 [规格 2026-10-21 备电/堆叠说明](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:68)。

本轮直接读到的住宅计算链是 `app.py → residential.py → pvgis.py / htw.py / eligibility.py / compatibility.py`。这些路径执行代码规则、查表和数据校验，没有调用对话模型来生成工程数值。Genie 是配置器的另一入口，也能解释保存方案；两者的分工在 [规格 2026-10-21 Ask Genie 变更](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:72) 与 [应用入口](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/app.py:1) 中可追溯。

报告设计上输出场地输入、产量、自给率和自用比例区间、选型理由、兼容依据、物料清单、假设与限制及下一步，并提供英德 PDF 与 Logo；范围明确排除回本期、现金流与 CAPEX。这些是初步选型与询盘依据。参见 [报告规格](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:11)。

## 九、可回忆的时间线（北京时间）

| 时间       | 已找到的记录                                                                                                                                                                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-08-28 | 已有一轮制造商、独立设计平台和批发商的系统研究，记录快速/详细模式、即时结果、BOM 和项目保存。见 [当时研究](/Users/chesterjohn/Documents/de-linker-project/docs/research/2026-08-28-solar-planner-benchmark.md:1)                                       |
| 2026-10-09 | 补做德国批发商选型研究，复盘旧计算方法，建立新配置器规格。见 [方法复盘](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/planner-methods.md:1)、[规格](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:1) |
| 2026-10-10 | 新引擎、三屏 React、屋顶步和 PDF 第一轮实现合入。见 [PR 48](https://github.com/AssassinFlash/de-linker/pull/48)                                                                                                                                        |
| 2026-10-12 | 追查参考来源并交付 A/B/C 三套原型；19:43 的票据记录业主选 B+C；21:59 第一轮融合实现合入。见 [选择记录](https://github.com/AssassinFlash/de-linker/issues/14#issuecomment-6123583871)、[PR 122](https://github.com/AssassinFlash/de-linker/pull/122)    |
| 2026-10-13 | 02:44 按打回反馈补齐 C 视觉；23:07 完成单独手机适配提交。见 [PR 126](https://github.com/AssassinFlash/de-linker/pull/126)、[移动证据](/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-10-13/configurator-mobile/README.md:1)               |
| 2026-10-21 | 后续真实数据走查继续修正兼容配对、电表随箱事实和备电预留路径，并增加报告向 Genie 交接。设计骨架与真实数据质量是分别验收的层。见 [规格变更记录](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:68)                       |

## 十、可以直接向老板解释的完整版本

“这个 Solution Configurator 是围绕我们的安装商、EPC 和经销商客户开发的。先研究了德国及欧洲同行的选型工具，参考他们从项目参数选设备、形成物料清单、再进入报价或询盘的流程。我们把它收敛成输入、方案、设计报告三步，接到 Linker 的商品和询盘业务上。

“计算方面，发电量接 PVGIS，住宅储能容量和自给率参考 HTW Berlin 的方法与数据，再根据我们的实际商品、厂商兼容文件和必要配件选出整套系统。结果会列依据、假设和范围，团队可以据此继续核实和报价。

“界面做过三套原型，我最后选的是 B 的左侧步骤导航，加 C 的右侧表单和卡片，之后又补做了一轮视觉细节。手机端则参考我当时提供的房产 App 设计稿做了调整。它就是这样从行业调研、方法复核、原型选择逐步做出来的。”

这段为依据记录整理的可用讲法；不包含重新验证过的线上可用率、计算精度或商业效果保证。

## 十一、追问：为什么选择 Commercial 后没有 Roof design？

结论：现行重建把可选屋顶步骤只接到了住宅流程，工商业路径集中在负荷、削峰与储能测算。这是已查明的功能覆盖边界。现有证据不能支持“工商业不需要屋顶设计”或“业主明确要求取消工商业屋顶”。

- **规格层：** [规格第 7 行](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:7)把屋顶可选步写在住宅下；第 8 行的工商业只写采集表、15 分钟负荷数据、指示范围与询盘。它记录了范围收窄后的形态，没有给出工商业应排除屋顶的独立论证。
- **实现层：** [App.tsx](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/App.tsx:187)按项目类型挂不同面板。住宅面板包含 RoofStep 和采用结果后的回填；[CommercialPanel.tsx](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/commercial/CommercialPanel.tsx:1)没有屋顶组件和回填路径，只在自用目标下提供既有/计划光伏 kWp 的手填框。切换类型因此会卸载住宅面板，也就看不到其中的屋顶功能。
- **数据层：** [CommercialInput](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:396)只接受 `pv_kwp`，没有住宅模型的 `planes`、`location`、`roof_source`。所以补一个入口按钮也不能让工商业计算完整使用屋面朝向、倾角、位置和来源；还要明确结果怎样参与测算与保存。
- **原研究反证：** [工商业方法规格 §5.2](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/planner-methods.md:592)的输入明确列了“PV：既有或计划的 kWp 与屋面”。[后续研究缺口记录](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-21-configurator-rooftop/dossier-gap.md:145)也说明历史上工商业/电站的画布边界没有判定。不能将当前代码反推为成熟行业设计结论。

给老板的准确讲法：“目前这个版本把屋顶功能先接在了住宅流程；Commercial 做的是工商业储能和负荷测算，光伏容量目前依靠手填。工商业规划厂房光伏同样会涉及屋面，原研究也列了这项输入，这部分还没有接到工商业链路里，应该作为功能覆盖缺口补齐。”这里的“先”描述交付顺序，不声称已经找到一份明确批准该分期的业主裁定。

上一轮口头解释中“屋顶是配置器可选一步”应明确为“当前已实现的屋顶步骤属于住宅分支”；“输入—方案—报告”也是整体产品目标，现行各项目类型的完成深度有区别。

本次追问只调查与补记，没有变更业务代码、创建工单、合并或部署。
