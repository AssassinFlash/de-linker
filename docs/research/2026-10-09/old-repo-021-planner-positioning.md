# 021 决议：Planner 的定位是否正确（2026-10-09）

## 它今天是什么（005、链尖代码、线上）
意向收集（住宅 / 工商业 / 电站三段：年用电、kWp、相数、目标功率、备用负荷与时长、耦合偏好、屋顶面积/倾角/朝向、邮编）→ 引擎 `/design/quick`（PVGIS 发电量、储能容量、候选逆变器与电池家族、BOM：组件 + 线缆 + 连接器 + 电流互感器、20 年经济性）→ b2b-core 定价与计算凭证 → PDF/HTML/CSV → Project 行与报价提交。电站段只收集字段并转项目询价，不计算（bundle:4509、6154-6163；引擎无 utility 分支）。BOM 里线缆（Lapp）、连接器（Stäubli、Trina TS4）、互感器（MBS）都绑了商品且正常供货；参考组件 Trina 460 为 `not_supplied`、无商品。

## 行业怎么做（004）
批发商的"规划器"是**为一次询价做快速计算**：输入 kWp（或屋顶）、年用电、相数、备用 → 从自家库存推荐逆变器 + 储能（显示可用性、可替代现货）→ 带数量的物料清单 → 带 Logo 的报价 / 购物车 / 项目询价（EWS QuickCalc、Segen 报价工具、BayWa 储能容量图表引用 HTW 独立性计算器）。更深的设计（组串、单线图、支架）属于 Solar-Planit、PV Manager、pvXpert 这类设计工具，因为那些批发商卖组件与支架。制造商侧（Sunny Design、SolarEdge Designer）做经济性与储能推荐。

## 判断
**定位正确。** Planner 就是行业的"快速计算 → 物料清单 → 报价/Proforma"，与业主 10-05（工具 = Planner + Project）、10-02（电站按项目报价、组件只在系统设计里）一致。我原先只说"引擎保留、壳重建"是对的，但没有写出判断依据；现在写明。它的问题全是执行层面：
1. 销售范围硬编码在引擎里且已脱节（013）。
2. BOM 里的组件行是 `not_supplied`：必须在结果、PDF 与 Proforma 里标为"按项目供应 / 不含在 Linker 报价内"，不计入价格合计（188 的未知价格行机制可复用）；线缆/连接器/互感器行是可售商品，保留。
3. 经济性（上网电价、CAPEX 分档、20 年现金流）是给安装商转述终端客户的辅助，不是主标题；每个数字带来源与有效期，`valid_until` 过期后在结果里披露（013 的常量来源工作覆盖）。
4. "加装"路径（既有逆变器 → 可配电池）是行业选型的第一项（004），Planner 页面文案写了"existing equipment"，intake 字段里却没有既有设备型号；重建时必须有：既有逆变器型号 → `check-compatibility` → 只列有放行文件的电池。
5. 表单→引擎词汇改名 4–5 处、原因句翻译 3 份、报告 2 套（009）；5,170 行单模块、无源码（020）。
6. 工具框文案"Organise the goal, site and existing equipment into a project direction you can keep refining"含糊；功能 UI 文案可改：EN "Size your system and get the bill of materials" / DE "System auslegen und Stückliste erhalten"（功能文案，EN+DE，Law 6 修正案允许）。

## 不改的
三段式意向（住宅 / 工商业 / 电站询价）；引擎的计算链；结果 → Project 行 → 报价（ADR-0018/0019/0029）；只显示有货（业主规则）。
