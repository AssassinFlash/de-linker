# CSV 与时段用电导入：成熟工具的证据及本站界面约束

2026-10-23（北京时间）。有界研究；所有外部搜索、页面取得均经 Apify。未登录、操作或导入任何客户数据到竞品。本轮证据是**官方帮助正文**，不是软件实走结果；不把本站已做的夹具或此前 PV*SOL 屋顶操作当成竞品 CSV 验证。

可直接采用的模式是：在同一项目内选择数据来源，声明时间与单位，查看导入解释，再明确确认采用。三家并不证明“任意 CSV 自动映射”：PV*SOL 与 SAM 的文件导入是单列约定，OpenSolar 当前说明要求使用其模板。全欧洲真实时间轴、净输入测点与不明回执恢复仍需按本站已有合同实现。

## 1. 官方页面明确写了什么（D：文档事实）

### PV*SOL

- 导入前填名称、可选注释、分钟间隔、可用天数、单位和数字格式；显示预期点数。文件为无表头单数值列 TXT/CSV，再按读取按钮。数字格式可选点/逗号及特定分组形式。**这不是通用表头映射器的证据。** [Consumption／Import load profile](https://help.valentin-software.com/pvsol/en/pages/consumption/#measured-appliances)（S01）。
- 短期资料可进入另一步，用百分比估算缺月份；选定曲线可调整总耗电且不改原曲线。应区分原件与估算后的曲线。[同一官方导入说明](https://help.valentin-software.com/pvsol/en/pages/consumption/#measured-appliances)（S01）。
- 负荷相关组件按声明的负荷间隔仿真；消费曲线由选定负荷与设备相加后交给仿真。[页面说明](https://help.valentin-software.com/pvsol/en/pages/consumption/)、[Calculation／Consumption](https://help.valentin-software.com/pvsol/en/calculation/consumption/)（S01、S02）。

### OpenSolar

- 项目 Energy → Electricity Usage → Interval Data → Upload CSV；支持 15/30/60 分钟、横向/竖向结构，但当前文档要求使用下载模板并保持表头。上传后确认或调整单位。[How to upload interval data](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data)（S03，页面更新 2026-05-08）。
- 允许跨年及不足 12 月，页面明确会自动外推缺失部分。不能把此行为描述成测得的数据完整，也不能将“必须完整日历年”当成此导入器的限制。[同一官方说明](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data)（S03）。
- Energy 页需要保存改动；仅用最大小时用电量作为需量可能不准确。[How to customize electricity usage](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage)（S04，页面更新 2026-05-08）。

本轮取得的 PV*SOL 正文只写“选择单位格式”，OpenSolar 正文只写“确认或调整单位”，**两页均未枚举 W／kW／Wh／kWh 的可选列表**。因此本报告不推定这些产品支持哪一套完整单位。SAM 文件导入的平均 kW 则有正文依据；本站当前 kW 区间均值／kWh 区间能量支持来自本站合同，未来 W／Wh 等换算需另行明确设计和验证。[PV*SOL 原文](https://help.valentin-software.com/pvsol/en/pages/consumption/)、[OpenSolar 原文](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data)（S01、S03）。

### SAM（原 NREL；现在线帮助由 NLR 发布）

- 文件导入约定是单列**每步平均 kW**，首行忽略；小时数据为 8760 点，15 分钟为 35040 点。Edit Data → 设置时间步 → 打开 → 表格检查 → OK；随后显示月/年能量及最大步值。[Electric Load](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#time-step-and-convention)（S06）。
- 文档明确不计夏令时和闰年。小时气象与次小时负荷并用时，能量费用取小时均值，需量保留次小时信息。原曲线与缩放曲线可同时查看。[时间约定](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#time-step-and-convention)、[View load data](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#adjust-load-profile-to-monthly-usage)（S06）。
- **同页存在单位冲突**：剪贴板段写 kWh，而导入／时间步段写平均 kW。本轮未跑软件核实剪贴板，不能将两者互换。[剪贴板段](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/electricity_load.html#pasting-load-data-from-your-computer-s-clipboard)（S06）。

SAM 新帮助地址是从其官方帮助首页、Electricity Rates and Load 索引追到的，两个猜测的路径实际返回 404，未作为事实证据。发布页说明帮助已迁到开源平台；不能把旧域未取到等同于 SAM 没有该功能。[帮助首页](https://natlabrockies.github.io/SAM/doc/index.html)、[负荷索引](https://natlabrockies.github.io/SAM/doc/electricity-rates-and-load/index.html)、[发布说明](https://natlabrockies.github.io/SAM/doc/reference/release_notes.html)（S05、S07、S08）。

## 2. 查到了什么、没有查到什么（U：本轮未证）

| 事项 | 已证的范围 | 本轮不能声称的内容 |
| --- | --- | --- |
| 列预览／映射 | SAM 有读入后的数据表；PV*SOL 单列；OpenSolar 模板 | 三家都支持任意 CSV 表头自动映射 |
| 单位 | PV*SOL 读前选，OpenSolar 读后确认，SAM 文件约定平均 kW | 未指定单位时能从数值大小或文件名可靠猜测 |
| 起／止时间 | SAM 单列按约定时间步，并要求随气象时间约定 | 已证明任意时间戳列的 start/end 自动识别 |
| 时区／DST | SAM 明说忽略 DST／闰年 | 已证明三家完整处理 IANA、秋季重复时刻、UTC offset、fold |
| 缺测／间隔 | PV*SOL 有显式短期外推步骤；OpenSolar 自动补全年 | 缺测一定保留为空，或外推已成为新的测量证据 |
| 负号／测点 | SAM 描述建筑负荷，另有 critical load 入口 | 已证明负 net import 可直接充当 gross load，或三家会重建站点总负荷 |
| 采用／计算 | 读取／检查／确认或保存后成为项目输入 | 打开文件、成功上传就等于当前方案已采用并适合计算 |

这是页面内容的证据边界，**不是对竞品真实软件不存在相关功能的断言**。OpenSolar 关于模板、跨年与外推以专用 interval 文章为准，另一篇泛用说明中的全年建议不应被误读成格式拒绝规则。

## 3. 对本站 CSV 界面的具体约束（I：设计推导，非竞品原话）

以下结合上述模式及本站 [Profile interpretation 合同](../../specs/548-profile-intake-view.md)、[Time-series 合同](../../specs/548-time-series.md)、[Workbench 合同](../../specs/548-workbench-application.md)；这些是本次实施建议，不声称已经实现。

1. **选择文件与列解释。** 同一项目内打开文件；先显示有界列／记录样本、表头及物理起始行。再选择时间列、数值列、可选结束时间与 fold 列。模板导入可以是预设，仍显示其有效映射。文件选择不能立即改项目 scenario。
2. **声明数据含义。** 明确区分 kW 区间均值与 kWh 区间能量，声明 gross／critical／net import 等测点；按 UI 语言预选的数字格式必须可见，拒绝不明分组。1 小时数据中 kW 与 kWh 数值相同，不能据此推断单位。
3. **声明时间。** 提供开始／结束标记约定；采用固定时长或明确结束列。项目 IANA 时区独立于界面语言，含 offset 的时间戳优先；DST 歧义要明确 offset／fold。SAM 的固定年简化不能覆盖本站真实 UTC 时间轴。
4. **后端完整解释与质量预览。** 样本预览不代替全文件校验。确认页显示原始单位、映射、起止 UTC、覆盖／跨度、缺口总数和时长、符号积分能量、区间均值范围，以及原生／有效分辨率和重建历史。不能只显示“上传成功”或一个漂亮曲线。
5. **明确采用一个已确认资产。** 展示与保存同一原件 hash、metadata hash、捕获 TZif／解释版本；只在明确动作后把已授权 asset ID 附到 editable scenario，并产生正常项目修订。解析成功、适合某个目标、已经采用是三种状态。
6. **缺测另行建模。** 原测量分支保持缺口；若后续提供外推，必须另建明确 modelled 派生资料，记录方法和参数、对照原曲线，并重新判断计算适用性。不要把 OpenSolar 的补全年行为直接写进 measured 上传路径。
7. **错误与不明回执。** 显示稳定 issue、物理记录起始行与映射角色；错误不回显单元格。未知上传结果保留精确原件、映射、原 key／请求，显式查回执或重试；换身份不能把旧请求自动作为新账号提交。此处的上传恢复仍需实际实现，现有 creation 队列不等于 upload 队列。

## 4. 实施前可以直接采用的验收材料

- 同一 15 分钟记录分别用 kW 与 kWh，验证后端积分与显示单位；保留 EN 小数点、DE 小数逗号及分组拒绝样本。
- start／end 两种时间标记、显式结束列、春季缺时、秋季两次相同本地时间、跨年及闰日；预览总量不依赖当前页。
- 缺口、重复／重叠、带引号多行单元格、空行、坏数字及数值溢出；错误的物理行和角色准确，原件未被默默修改。
- signed net import 与非负 gross/critical 分开；小时均值不可当瞬时或 15 分钟计费峰值。
- 解释预览后未采用、已采用、方案后来改变、未知上传结果、两个 tab、换账号分别实走。所有“已采用／已保存”须有对应真实回执。

这些是本站合同的验证门，不是本轮对竞品跑过的测试。

## 5. 证据与复现范围

- [PRIMARY-SOURCES.json](PRIMARY-SOURCES.json)：8 个 HTTP 200 官方页面的 URL、run/dataset、采集信息、正文文件及 SHA-256；`primary/` 保存 Apify 回读的正文。
- `raw/*-input.json`：全部公开 actor 输入；`raw/*-run.json`：选择保留的运行状态；`raw/*-items.json`／`search-results.json`：回读结果。搜索摘要及 AI overview 只用于定位，未作为产品事实依据。
- 使用既有安全 helper 的 `api()`，凭据只在 Authorization header 中读取。没有令牌写盘、普通搜索绕行、竞品账号或生产操作。
- 原域及猜测路径失败已保留 metadata；Apify run 标为成功并不意味着每个 URL 都有效，以 source index 的逐页 HTTP 状态为准。
- 调研不证明版本部署、实际 CSV 控件行为、储能选型正确性或任何本站能力已交付。未作额外模板下载、注册或竞品实操；本轮到此收口。
