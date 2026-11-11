# #548 域缺口矩阵（审计 D 线，2026-11-11）

只读审计。判定标准：**可发布** = 有实现且有 2026-11-05 之后的生产证据；
**需补验** = 实现存在但证据早于 11-05 或覆盖不全；**需实现** = 能力缺失。

| # | 域 | 结论 | 关键缺口 |
|---|---|---|---|
| 1 | 地图/平面/3D | 可发布（能力层） | 地图链 e2e 11-11 复跑 8/8 绿（PR #1087，11-06 UI 改版未破坏）；验收重归 11-11；图像标定仍未实现（规格未要求，复刻优先） |
| 2 | 屋顶导入与辐照/遮挡 | 可发布（能力层） | M 线纠正：citygml/LoD2 从未进规格（唯一声明格式 geojson_wgs84）；direct-beam 有版本门控真实入口；导入 4 格 e2e 新建（#1093）；W 线评估补生产配额实测（#1106） |
| 3 | PV 发电与能量时序 | 可发布（能力层） | W 线纠正：direct-beam 1 次+geometric 7 次生产实跑全成功（#1106）；Y 线补能量域 10 次生产证据+合同核对零缺陷（#1107，但 9/10 在 11-05 前窗口外、输入为自有合成夹具、另两内核零生产执行——评级限单内核）；configurator 12 行已全部翻绿（#1089/#1110） |
| 4 | 项目工作台与修订 | 可发布 | 两处维持记录已解除（2026-11-11，`docs/acceptance/2026-11-11/548-domain4-claim-launch/`）：recovery outbox 在真 WP+真 Action Scheduler+真引擎上验证了持久化/退避 1-2-4-8-15 分钟/失败保留/确认后删除与引擎回执；launch protection 在真实可执行对上验证了 (a) 存储版本拒绝、(b) 不同运行时 worker 与 HTTP 拒绝、(c) 未标版本已填充存储拒绝、(d) 拒绝先于 drain/stop/同步/重启/option 写入 |
| 5 | 商务链贯穿 | 可发布 | G 线三层测试落地（#1089，变异证明）；商用 PDF 修复生产四组合验证+8 行翻绿（#1102/#1110）；BOM 表渲染已在 #1110 的 PDF 正文核对中覆盖 |
| 6 | 产品身份与兼容 | 可发布 | 身份半已关闭（#1111：git 零改动+四组合逐字一致+更严回归 spec）；兼容合同运行时证据=生产 377 对 pairs（#1081 修复后）；兼容半原生验收已补（`548-compatibility-native/conclusion.md`，`planner-equipment-release.spec.ts` 10 用例 EN/DE 全绿+变异证明）：released 条件与文档引用逐字、not_released 不冒充通过、released 但条件被违反仍报 not met、覆盖层 Trina 在 `products/current` 与 `/design/residential` 两层可验 |
| 7 | 服务托管 | 可发布 | 配额已按工作量实测（#1106：normal geometric 95.6% 用量、expanded 28%、direct-beam 0.03% RSS 48MB）；调度单元 launchd 双修防轮转（#1108/#1109）；knowledge/engineering 双消费者生产就绪（#1101/#1103） |
| 8 | 国家/DSO 规则 | 需补验（扩国已进 AT） | L 线 e2e 已补 EN+DE UI 链+engine 拒绝合同（#1094，N 线解除 readiness 后规则结果页可达）；**AT 已入包**（TOR Typ A v1.4 + ElWG，6 条判定，证据 `docs/research/2026-11-11-at-country-rules/EVIDENCE.md`，见 `COUNTRY-EVIDENCE.md` §13）；**SE 仍为下一候选**；DSO 级放行证据对四国均未取得 |

实跑只读测试合计：engine 468 passed、planner 509 passed，零失败。

## 三个优先发现（主控已抽查 2/2 属实）

1. 规格分叉：`548-pv-preparation.md:83-86` 称 weather journal 未实现，
   `planning/weather_journal.py` 已完整实现且 11-05 生产跑通（H 线修正）。
2. 客户文件访问链零测试：询盘客户下载报告的唯一通道无任何用例（G 线补）。
3. 地图域 e2e 依赖 `#lp-design` 标签与按钮文案，11-06 起 UI 改版后未复跑（H 线复跑）。

国家规则域的下一批：按 #562 方法论（原文+哈希+生效日期）逐国补规则包是
研究+证据线，先补现有 3 国的 e2e，再按证据充足度扩国。
