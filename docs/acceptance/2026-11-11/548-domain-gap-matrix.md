# #548 域缺口矩阵（审计 D 线，2026-11-11）

只读审计。判定标准：**可发布** = 有实现且有 2026-11-05 之后的生产证据；
**需补验** = 实现存在但证据早于 11-05 或覆盖不全；**需实现** = 能力缺失。

| # | 域 | 结论 | 关键缺口 |
|---|---|---|---|
| 1 | 地图/平面/3D | 可发布（能力层） | 地图链 e2e 11-11 复跑 8/8 绿（PR #1087，11-06 UI 改版未破坏）；验收重归 11-11；图像标定仍未实现（规格未要求，复刻优先） |
| 2 | 屋顶导入与辐照/遮挡 | 可发布（能力层） | M 线纠正：citygml/LoD2 从未进规格（唯一声明格式 geojson_wgs84）；direct-beam 有版本门控真实入口；导入 4 格 e2e 新建（#1093）；W 线评估补生产配额实测（#1106） |
| 3 | PV 发电与能量时序 | 需补验（单内核可发布，两内核生产不可执行） | W 线纠正：direct-beam 1 次+geometric 7 次生产实跑全成功（#1106）；Y 线补能量域 10 次生产证据+合同核对零缺陷（#1107，但 9/10 在 11-05 前窗口外、输入为自有合成夹具）；configurator 12 行已全部翻绿（#1089/#1110）。**plant_ac/shared_dc 两内核（`docs/acceptance/2026-11-11/548-energy-two-kernels/`）**：生产 0 次，root cause 已定位到设备事实门——两内核的电池参数必须经 `prepare_dc_parameters()` 从现行 Woo 事实派生，且门是三道串联（可用能量+完整电压窗口 → 逆变器电池端口声明 → 充电电流条件；42 台逆变器里只有 4107 声明端口）。在**签名固定**的 86 产品就绪池上（扫描前后集合 SHA-256 一致，drifted=False）穷举 1763 次派生，**0 通过**；一次 3444 次的不绑签名扫描给出失败分布 2708/712/6，其 18 次"通过"不可复现，已丢弃。唯一实证可行的链 `4107+1954@mps=6/BAT1`（`usable_window_kwh=60.0`，且与 `pv_dc_kw` 无关）因 1954 `ready.engineering=false` 被 `prepared_view()` 撤下。生产 178 个 revision 从未出现 plant/shared_dc 场景；5 个既有电池资产全是无 DC 依赖的用户显式场景。官方 BDEW/VDEW 画像已实测可原样作 `gross_load`（H25 35040 区间/59 952.142 kWh，gap 0.059952 如实上报）。解除条件=恢复 1954 就绪或给就绪电池补齐事实（属 Woo 数据，C 线） |
| 4 | 项目工作台与修订 | 可发布 | 两处维持记录已解除（2026-11-11，`docs/acceptance/2026-11-11/548-domain4-claim-launch/`）：recovery outbox 在真 WP+真 Action Scheduler+真引擎上验证了持久化/退避 1-2-4-8-15 分钟/失败保留/确认后删除与引擎回执；launch protection 在真实可执行对上验证了 (a) 存储版本拒绝、(b) 不同运行时 worker 与 HTTP 拒绝、(c) 未标版本已填充存储拒绝、(d) 拒绝先于 drain/stop/同步/重启/option 写入 |
| 5 | 商务链贯穿 | 可发布 | G 线三层测试落地（#1089，变异证明）；商用 PDF 修复生产四组合验证+8 行翻绿（#1102/#1110）；BOM 表渲染已在 #1110 的 PDF 正文核对中覆盖 |
| 6 | 产品身份与兼容 | 可发布 | 身份半已关闭（#1111：git 零改动+四组合逐字一致+更严回归 spec）；兼容合同运行时证据=生产 377 对 pairs（#1081 修复后）；兼容半原生验收已补（`548-compatibility-native/conclusion.md`，`planner-equipment-release.spec.ts` 10 用例 EN/DE 全绿+变异证明）：released 条件与文档引用逐字、not_released 不冒充通过、released 但条件被违反仍报 not met、覆盖层 Trina 在 `products/current` 与 `/design/residential` 两层可验 |
| 7 | 服务托管 | 可发布 | 配额已按工作量实测（#1106：normal geometric 95.6% 用量、expanded 28%、direct-beam 0.03% RSS 48MB）；调度单元 launchd 双修防轮转（#1108/#1109）；knowledge/engineering 双消费者生产就绪（#1101/#1103） |
| 8 | 国家/DSO 规则 | 需补验（扩国已进 AT+SE，账号背书目标用尽） | L 线 e2e 已补 EN+DE UI 链+engine 拒绝合同（#1094，N 线解除 readiness 后规则结果页可达）；**AT 已入包**（TOR Typ A v1.4 + ElWG，6 条判定，证据 `docs/research/2026-11-11-at-country-rules/EVIDENCE.md`，见 `COUNTRY-EVIDENCE.md` §13）；**SE 已入包**（EIFS 2018:2 + RfG Art. 5.2 北欧门槛 + ellagen 4 kap.，7 条判定，证据 `docs/research/2026-11-12-se-country-rules/EVIDENCE.md`，见 `COUNTRY-EVIDENCE.md` §14）；**账号背书的扩国目标至此用尽**（DE=11、US=3 非欧洲电网规则域、SE=1、AT=1、NL=1 均已覆盖），后续按新证据重排；DSO 级放行证据对五国均未取得 |

实跑只读测试合计：engine 468 passed、planner 509 passed，零失败。

## 三个优先发现（主控已抽查 2/2 属实）

1. 规格分叉：`548-pv-preparation.md:83-86` 称 weather journal 未实现，
   `planning/weather_journal.py` 已完整实现且 11-05 生产跑通（H 线修正）。
2. 客户文件访问链零测试：询盘客户下载报告的唯一通道无任何用例（G 线补）。
3. 地图域 e2e 依赖 `#lp-design` 标签与按钮文案，11-06 起 UI 改版后未复跑（H 线复跑）。

国家规则域的下一批：按 #562 方法论（原文+哈希+生效日期）逐国补规则包是
研究+证据线，先补现有 3 国的 e2e，再按证据充足度扩国。
