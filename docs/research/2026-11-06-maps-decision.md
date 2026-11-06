# 地图与地点搜索的采用决策（2026-11-06）

业主 2026-11-06 授权：若 Google Maps 收费可接受则采用；否则换免费方案。经官方定价页实时核实（Apify 抓 `developers.google.com/maps/billing-and-pricing/pricing`），结论与边界如下。

## 1. 费用结论：采用 Google，成本为零

| SKU | 每月免费额度 | 超出后 | 我方用法 |
| --- | --- | --- | --- |
| Dynamic Maps（含卫星视图加载） | 10,000 次 | $7.00 / 1,000 | 客户打开配置器看位置的次数 |
| Autocomplete Requests | 10,000 次 | $2.83 / 1,000 | 客户输入地址时的每次补全 |
| Places API Place Details Essentials | 10,000 次 | $5.00 / 1,000 | 选中建议后取坐标 |
| Solar API Building Insights | 10,000 次 | $10.00 / 1,000 | **暂不启用** |

B2B 客户体量下（每月数百至数千次配置），三项核心 SKU 均在免费额度内，实际支出 **$0**。Solar API 虽也有免费额度，但单价高、且其 `RoofSegmentSizeAndSunshineStats` 不返回完整屋面边界 ring（见 `docs/research/2026-10-23-map-workbench-integration/IMPLEMENTATION.md` §2），本期不启用。

## 2. 已启用的 Google 能力（实测读回）

- 项目：`de-linker-playbook`（已绑定有效结算账号 `01B460-F25551-881844`）
- 已启用：`Maps JavaScript API`、`Places API (New)`，二者均出现在「已启用的 API 和服务」列表
- API 密钥：`Maps Platform API Key`，已设 API 限制为该两项
- 实测：`GET https://maps.googleapis.com/maps/api/js?key=…&libraries=places` → HTTP 200；`POST https://places.googleapis.com/v1/places:autocomplete`（`Marienplatz München`）→ 返回真实 `placeId`
- 密钥存放：`~/.config/de-linker/google-maps.env`（权限 600），**不进仓库、不进客户端明文常量以外的任何持久化位置**

## 3. 必须遵守的用途边界（不是可选项）

Google Maps Platform EEA 条款 §3.3.2(a)–(c) 明确禁止**从 Google 卫星图描绘建筑轮廓并作为自有工程几何保存**，示例中直接点名 "tracing building footprints from Google Maps JS Satellite"。本站屋顶描绘的产物正是要进入工程几何的项目数据，因此：

- **允许**：用 Places API 做地址/邮编搜索与定位（`placeId` + 经纬度），用 Google 地图作为**视觉背景**让客户确认地点。
- **禁止**：把在 Google 卫星图上圈出的多边形当作项目屋面几何入库、参与面积/排布/发电计算或写入报告。
- 依据与完整条款解读见 `docs/research/2026-10-23-map-workbench-integration/IMPLEMENTATION.md` §3。

## 4. 因此采用的组合方案

| 环节 | 采用的来源 | 理由 |
| --- | --- | --- |
| 地址/邮编搜索（全欧洲） | **Google Places API (New)** | 覆盖与补全质量最好，免费额度内零成本 |
| 地点确认与视觉背景 | **Google 地图（动态地图）** | 客户一眼确认位置正确 |
| 屋面描绘与面积计算 | **引擎已有的德国 16 州官方 DOP20 正射影像**（`services/engine/data/imagery.json`，许可 dl-de/zero-2-0 / CC BY 4.0 / dl-de/by-2-0，已逐州核过 GetMap 与许可） | 许可明确允许描绘与商用，且我方可保留派生几何；这正是旧仓库验证过的合规路径 |
| 德国以外的屋面描绘 | 按国家接入对应官方正射服务；未接入前回到「直接选装机档位」，不阻断主链 | 不用未获许可的来源冒充工程几何 |

这条组合把「合规」和「好用」分开处理：客户仍然是一个地址搜索框就定位到屋顶，但真正参与计算的几何来自许可允许的来源。

## 5. 待补的加固项

密钥尚未设置 HTTP 引荐来源网址限制（`de-linker.com` + 本地开发域）。当前已有 API 级限制（只能调 Maps JS 与 Places），风险受限但未清零。补齐方式：Cloud Console → 凭据 → 该密钥 → 应用限制选「网站」→ 添加 `https://de-linker.com/*`、`https://*.de-linker.com/*`、`http://localhost:*/*`、`http://127.0.0.1:*/*`。
