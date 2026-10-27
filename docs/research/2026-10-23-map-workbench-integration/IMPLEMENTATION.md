# 统一工作台：地图、地点、绘制与工程几何的实施接缝

2026-10-23，后台研究。范围只补当前地图接入；不重做几何内核、系统计算或整体架构审计。只读基线为 `b0080ec15eb2dcab6b2c22b7b029180a2c1f73c2` 加本会话正在协作的工作目录；未改业务、依赖、实例、设置或生产，未取得或使用 Google key。以下 **V** 表示本轮实际读取/运行，**R** 表示继承的官方原件，**D** 表示本站待实现设计，**A** 表示须由真实账号/资料持有者提供的事实。研究不构成地图 UI、工程精度或全欧洲放行。

**实施状态读法，2026-10-24 更新：**下文保留研究时 `b0080ec1` 的事实快照，其中“尚未进入 `apps/planner`”“没有地理投影”“尚无几何 intake”等措辞不代表当前工作树。隔离应用现已锁定 MapLibre **5.24.0** / Terra Draw **1.35.0** / adapter **1.4.1**；有来源的地理几何导入和只读地图已进入同一项目链，边界见 [MAP-DISPLAY](MAP-DISPLAY.md)。完成后的坐标边界使用已接受的 `geographicOnRoof` 大地垂线与屋面求交，不能按本文早期水平求交草案替换它。绘制控制器与米制命令增量及其验收界限见 [DRAW-CONTROLLER](DRAW-CONTROLLER.md) 和 [source contract](../../acceptance/2026-10-24/548/map-drawing/SPEC.md)；该控制器现已挂入客户界面，新屋面绘制、原始草稿恢复及共同项目写入已有[界面增量与原生证据](../../acceptance/2026-10-24/548/map-drawing-ui/NATIVE.md)；既有屋面/开口/障碍/禁布边界的编辑正在按[边界编辑规格](../../acceptance/2026-10-24/548/map-ring-ui/SPEC.md)接入同一个恢复日志。完整原生触控与全站交付仍在原地图内继续执行。实现进展不会把原研究中的设计项整体改成已验收能力。

## 1. 可以马上实施的接缝

**把地图作为现有 `DesignEditor` 的第三个视图，保留 `GeometryDocument → GeometryCommand → ProjectEditor.editGeometry → editDraft` 这条写入链。** `MapViewport` 只管投影、交互和来源展示；Terra Draw 的快照是编辑草稿。新屋面、孔洞、障碍、禁布区经校准与来源检查后，提交一次 `group { before, edits }`。2D、3D、对象树、保存、重开继续消费同一米制文档和对象 ID。[现有合同](../../specs/548-workbench-application.md)、[几何合同](../../specs/548-design-geometry.md)、[commands](../../../apps/planner/src/domain/geometryCommands.ts)、[调用方](../../../apps/planner/src/components/ProjectEditor.tsx)

最先实施三个有明确边界的模块（D）：

1. **`GeographicBridge` / `GeometryImport`**：WGS84/声明 CRS 或自有图纸像素 → 有版本、可读回的校准 manifest → local ENU / roof UV；原始输入、导入问题和最终领域对象分开。
2. **`MapViewport` + `MapDrawController`**：按需加载地图，投影领域文档；把完成手势交给同一 `commit(command)`。本轮核过的安装组合为 MapLibre **5.24.0**、Terra Draw **1.35.0**、MapLibre adapter **1.4.1**，在旧插件包中确实存在；它们尚未进入隔离的 `apps/planner` 包，不能称 React 19/Vite 8 集成已通过。（V）
3. **`SourceIntake` / `LocationReference`**：分别处理用户原件、允许衍生的区域数据、Google 地点与 Solar 工作数据。只有许可适合永久保存的来源进入既有 `Assets` 永久库。地点选择不直接写永久地理锚点。（D）

不需要先换整套状态管理、地图框架或坐标内核。`coordinates.ts` 现在只做 ENU/UV/Three 向量变换，**没有地理投影功能**；在它旁边加具名边界，不能把经纬度直接传给 `roofCoordinates()`。现有 `set_coordinate_system` 只修改声明，也**不会旋转或重新定位已有对象**。[当前坐标函数](../../../apps/planner/src/domain/coordinates.ts)、[当前坐标表单](../../../apps/planner/src/components/design/CoordinatesForm.tsx)

## 2. 供应商入口、账号与实际能力

| 来源/服务 | 已核入口和能力 | 账号、key、费用边界 | 当前接入决定 |
| --- | --- | --- | --- |
| MapLibre + Terra Draw | 本机已安装的库、MapLibre adapter；自定义 raster/GeoJSON 来源与绘制（V）。MapLibre 的 `MercatorCoordinate` 一单位是投影世界宽度，不能当工程米数。[官方坐标文档](https://maplibre.org/maplibre-gl-js/docs/API/classes/MercatorCoordinate/) | 这两个客户端库不要求开 Google 账号；瓦片、影像、地址与测量数据是另一供应合同。MIT/BSD 软件许可不授予数据许可。 | 优先接已核组合；只增加实际需要的隔离包依赖和库必要 CSS。不得从旧 RoofStep 复制业务代码或沿用它的尺寸/坡度默认值。 |
| Google Maps JavaScript API | [官方 loader](https://developers.google.com/maps/documentation/javascript/load-maps-js-api)，SDK 入口 `https://maps.googleapis.com/maps/api/js`；地图显示、视口、图层、自有覆盖物与自定义影像；不是自动屋面服务（R）。 | 真实 Cloud 项目、启用 API、billing、browser key；website referrer 与 API 限制。地图加载与地点请求按各自 SKU 计费。[Maps billing](https://developers.google.com/maps/documentation/javascript/usage-and-billing) | 保留可选地图 renderer；用现有 React 19 effect 包住官方 SDK 生命周期，不为地图再增加 React wrapper。没有 key/billing 实证时显示未配置状态，人工工程路径仍完整。 |
| Google 地点搜索 | EEA 新集成优先 [BasicPlaceAutocompleteElement](https://developers.google.com/maps/documentation/javascript/places-ui-kit/basic-autocomplete)：`gmp-select` 得 place ID，再经 UI Kit Place Details `gmp-load` 读 location 定位（R）。 | 启用 Places UI Kit，有独立计费；不能把旧 SearchBox 当新客户默认入口。Maps key 可复用与否取决于其 API 限制和实际项目配置，不能从源码推断。 | 搜索只改变临时地点/视口；保留 Google UI、署名、链接。把定位来源、许可期限与工程 anchor 分开。 |
| Google Solar Building Insights | `GET https://solar.googleapis.com/v1/buildingInsights:findClosest`，输入明确 lat/lng 与 `requiredQuality`；最邻近已知建筑、拍摄/处理日期、quality、太阳能潜力和屋面分段（V/P1）。 | 独立启用 Solar、billing，API key 或 OAuth；本站应经私有服务端窄请求，不把 server key 或任意 URL 代理交给浏览器。[Solar billing](https://developers.google.com/maps/documentation/solar/usage-and-billing) | 作为独立自动数据 acquisition。先让用户确认返回建筑；失败不清空手工几何，不能把“地图可见”当 Solar 有 coverage。 |
| Google Solar Data Layers / GeoTIFF | `GET https://solar.googleapis.com/v1/dataLayers:get`，再使用其返回的 `geoTiff:get` 资源；请求中心、半径、view、quality、pixel size（V/P1）。 | Building Insights 与 Data Layers 是不同 SKU；真实项目配额/价格/实际免费额度由其控制台和现行价格页决定。本报告不假定每次地图打开都要请求屋面数据。 | 原始 DSM、mask、RGB、flux、shade 是带期限工作数据；提取和工程确认另有步骤，不直接进永久 CAS。 |
| 区域开放数据 | 继承的一手目录证明奥地利 basemap.at 正射、荷兰 PDOK CityJSON、瑞士 swissBUILDINGS3D 等是可适配来源（R/E1）；国家间产品/年份/许可不同。 | 开放下载并不保证无配额或所有图层无账号。按产品条款决定下载、署名、衍生、保留与服务成本，不能从国家门户“免费”推断完整商用权。 | 用具名区域能力记录启用；先做一条小范围真实来源路径，再按地区放行。不能给一个 `europe_supported=true`。 |
| 用户自有测量/图纸/几何 | 用户有权使用的图像、工程文件、测量点和尺寸可进入同一永久项目（D）；已有永久 `Assets` 与 owner/receipt 机制可复用（V）。 | 不需要 Google key；需要原件权利声明、实际测量依据、尺度/北向/高度状态。用户确认不会自动洗去 Google 或其他供应商来源。 | 必须是完整输入→校准→编辑→保存→重开→报告路径；禁止只给空白画布或把它降为错误页。 |

Google 的 Drawing Library 已退役；本接入不加载 `libraries=drawing`。新地图不使用 legacy SearchBox。既有研究已核这些生命周期，见 [MAP-ADAPTER §3](../2026-10-22-planning-implementation/MAP-ADAPTER.md#3-2026-年不能照抄的-google-组件) 及其官方 URL/Apify 原件表；本轮没有重抓同一组页面。该文件的 WordPress React 外壳建议早于隔离 runtime 裁定，当前实施采用 `apps/planner` 的 React **19.3.1** / TS **6.0.3** / Vite **8.3.5**，站点 runtime 保持隔离。[当前包](../../../apps/planner/package.json)

**Solar 的一个实际接口缺口（V）：** `RoofSegmentSizeAndSunshineStats` 包含 `center`、`boundingBox`、`pitchDegrees`、`azimuthDegrees`、`planeHeightAtCenterMeters`，没有完整逐面边界 ring；矩形包围框不能转换成真实屋面边界。其高度字段描述为海拔，不能直接当 WGS84 椭球高或项目相对 Up。自动屋面路径还需明确的 DSM/mask/已有工程几何提取与确认方法；返回的 `solarPanels` 也采用该服务的 panel 参数，不等于本站模块型号、排布和数量。[官方 RoofSegment 字段](https://developers.google.com/maps/documentation/solar/reference/rest/v1/buildingInsights/findClosest#RoofSegmentSizeAndSunshineStats)

`requiredQuality` 省略时相当于只接受 HIGH；如果本站希望允许 MEDIUM/BASE，必须显式请求、保留返回质量并分别验收，不能静默放宽。Data Layers 的半径与 view/pixel size 有联合限制，需按官方请求合同校验，不能设成无界的“下载周边”。[Building Insights query parameters](https://developers.google.com/maps/documentation/solar/reference/rest/v1/buildingInsights/findClosest#query-parameters)、[Data Layers query parameters](https://developers.google.com/maps/documentation/solar/reference/rest/v1/dataLayers/get#query-parameters)

## 3. Google 欧洲合同：具体限制不应变成功能删除

EEA 规则看 Cloud billing account 的地址及实际合同，不看屋顶国家或 EN/DE。现有研究核过新/实质修改集成的适用性；本轮没有读取 Linker Cloud 项目或签署合同。（R、A）[官方 EEA FAQ](https://developers.google.com/maps/comms/eea/faq)

| 具体内容/用途 | 官方段落依据（R，已重新从原 Apify dataset 回读） | 本站可实施的边界（D） |
| --- | --- | --- |
| 标准 Google 卫星图描建筑 | [EEA ToS §3.3.2(a)–(c)](https://cloud.google.com/terms/maps-platform/eea)：限制抓取/缓存/创作；示例明确列从 Maps JS Satellite 描建筑、从 45° imagery 建 3D 模型，也列用 Places lat/lng 作 point-in-polygon analysis。 | 不把标准卫星描边存成自有工程几何；地点搜索坐标不用于建筑包含判定。提供许可适合描绘的正射、自有图纸与测量输入；若要启用该 Google 内容用途，需真实合同覆盖，不能让用户一个勾选绕过。 |
| Google Maps 与自有 3D | 上述条款禁止的是**基于特定 Google 内容创造模型**；不是对所有自有 3D 编辑器的禁令。 | 自有/获许可几何可在独立 3D 视图中编辑。来源血缘随几何保留；不能把 Google 瓦片搬进 Three 纹理、从 45° 图重建，或用换 renderer 宣称清除了来源限制。 |
| Places / UI Kit 与第三方地图 | [EEA SST §15.1–15.4、§16](https://cloud.google.com/terms/maps-platform/eea/maps-service-terms)：一般 Places 除 lat/lng/place_id 外内容不可 With any Map；UI Kit 有该展示限制例外，署名/通知不得改。lat/lng 通常只缓存 30 日。With any Map 包含旁边、视觉关联和链接。 | 用官方 UI Kit 完成搜索展示；不要在 MapLibre 旁重画 Google 地址/POI 结果卡。保留 place ID 按其允许的生命周期管理；位置期限不因变成 ENU 数字而消失。 |
| Geocoding 长期缓存例外 | 同页 §6.2.2 允许具特定条件、隔离于该最终用户且用于发起应用直接功能的长期缓存；不是所有 Google 位置内容的通用许可。 | 若选此服务，给该具体用途独立定义/审查；不把例外套给 UI Kit、Places 或 Solar。 |
| Solar 做能源设计 | 同页 §21.1 明确允许可行性、设计/安装及其定义的 downstream transaction；§21.2 允许 Building Insights/Data Layers 缓存至多 30 连续日。 | 保留自动屋面和能源设计能力；新增有到期/删除/readback 的 provider 工作数据层。既有永久 `Assets` 正确拒绝这类暂存来源，不能由 browser 宣称 permanent 绕过。 |
| Solar 固定介质保留 | 同页 §21.2 对为指定 downstream transaction 纳入 fixed media 的 Solar 数据给予删除例外，例子包括设计、研究、提案。 | 可以实现用户请求的特定地址冻结设计/PDF，满足署名与用途；条款未明确把任意永久可编辑 JSON/原始栅格归档都当 fixed media。本报告不把这种不确定性扩成取消设计，也不据此放行永久 raw 仓库。 |
| Solar 与非 Google 地图/3D | EEA FAQ 说明移除通用 non-Google map 限制；当前 EEA Solar §21 没有单独的 With any Map 禁令；[Solar 政策](https://developers.google.com/maps/documentation/solar/policies)另给数据/新创作内容的归属要求。Pre-GA 服务仍有相邻非 Google map 限制，不能跨服务概括。 | 在适用 EEA 合同、获准用途、稳定服务与署名下评估 Solar→独立 map/3D 的具体数据管线；不存在“只能全部 Google”或“任何混用均自由”的通用结论。获取真实合同差异后更新 capability policy，不能靠地图名字删功能。 |

Solar 原始/未修改数据显示保留政策要求的 `Source: Includes solar data from Google`；新创作内容按政策的 Google Maps 数据归属要求执行。本站需要把 provider 与其他来源的署名分清、保持可见，PDF 与地图/3D 各自验证，不能把 Google 署名贴到完全自有测量数据上。[官方归属段落](https://developers.google.com/maps/documentation/solar/policies#other-attribution-requirements)

**coverage 不是工程精度。** 既有官方 coverage 原件分 HIGH（0.1 m/pixel）、MEDIUM/BASE（0.25 m/pixel），这是来源处理分辨率；没有“整个欧洲 10 cm 工程误差”的保证。按实际地址响应记录 quality、imageryDate、imageryProcessedDate、返回建筑、区域与版本；无数据、邻楼、陈旧数据分开。EEA Solar 调整页只列 Building Insights 少了若干地址字段，并未取消 EEA Solar。[coverage](https://developers.google.com/maps/documentation/solar/coverage)、[EEA Solar 差异](https://developers.google.com/maps/comms/eea/solar)

历史 Solar 原始数据到期后，永久项目只保留许可允许的来源证明与冻结交付；逐字节复算若已不可行，明确 `source_bytes_expired`，不能假装原 run 仍能重放。重新取得产生新 source/run；用户补入自己的测量也形成新来源和修订，不能倒改旧来源。确需永久精确重算 provider 模型时，选择许可满足该要求的数据或取得覆盖该用途的合同。（D，承接既有 MAP-ADAPTER §4）

## 4. GeoJSON → ENU → roof UV：不能遗漏的校准合同

### 地理坐标边界

RFC 7946 §3.1.1、§3.1.6、§4：GeoJSON 使用 WGS84、**`[longitude, latitude]`**；可选第三维为椭球高米；首尾重复的闭合 ring 与孔洞位置有明确意义。投影 Easting/Northing 文件不能冒充标准 GeoJSON；必须经独立 import envelope 声明 CRS、轴序和单位。旧 `crs` 成员不构成 RFC 7946 当前支持。（V/P1）[RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946#section-4)

本站 GeographicBridge（D）应提供两条具名输入：

- `geographic_3d`：已知水平 CRS、垂直基准/单位、原点三维坐标。先按真实 CRS/基准转换，再做 topocentric ENU；记录实际 operation、PROJ/pyproj 版本、使用的 grid 依赖/精度状态，缺必需转换数据显性报错，禁止静默近似变换。
- `geographic_2d`：只有 lon/lat。只求明确声明的水平定位；例如以 `h0=0` 作为 **horizontal-only 数值约定** 的 WGS84 椭球面投影，另由测量/图纸/明确场景提供 roof plane 和相对 Up。manifest 必须区分“计算约定 0”与“实际高程未知”，不能从 2D 点生成真实屋高或让曲率产生的 Up 当屋面起伏。量尺确认和来源误差仍保留。

PROJ 官方定义 geographic→topocentric 需要先 `cart` 再 `topocentric`，原点包含 lon0/lat0/h0，或 X0/Y0/Z0；`topocentric` 单独不是 lon/lat 转换。本站管线显式声明 WGS84 椭球，不依赖 PROJ 默认 GRS80。逆变换只用于地图投影，不改写原始 metric 文档。[官方 cart](https://proj.org/en/stable/operations/conversions/cart.html)、[官方 topocentric](https://proj.org/en/stable/operations/conversions/topocentric.html)

**投影实现合同（D）：**服务端复用已经实际安装的 pyproj/PROJ，可信 import 记录完整 pipeline 与版本；不新增第二个服务或任意 CRS 推断。浏览器只需隔离的 `enuToWgs84 / wgs84ToEnu` 窄 WGS84 ECEF↔topocentric 边界，以同一原点/椭球/单位对照服务器 oracle；不因此引入通用地理可视化或完整 GIS 依赖。非 WGS84 工程文件先由服务端按其声明 CRS 转换。支持范围、异常与数值 fixture 明确，未实现的垂直基准变换不回退成 0。此边界不修改已接受的 roof UV/pose 数学。

```text
GeoJSON [lon, lat, optional ellipsoid h]
  → declared CRS/vertical operation, if necessary
  → geodetic WGS84 → ECEF cart → project topocentric ENU metres
  → confirmed roof plane → UV metres
  → GeometryCommand → one authoritative GeometryDocument

GeometryDocument → ENU points → inverse GeographicBridge → map GeoJSON
GeometryDocument → existing toRender(e,n,u) = (e,u,-n) → 3D
```

地图 pixel、zoom、Web Mercator world coordinate 和渲染比例都不能作为尺寸权威。[MapLibre 官方说明](https://maplibre.org/maplibre-gl-js/docs/API/classes/MercatorCoordinate/) 明确其归一化单位。不同纬度、地图 heading/pitch、换 renderer 不应改变领域长度/面积。编辑时使用俯视、明确北向；视口旋转不能悄悄旋转工程几何。

**已有未定向几何与地图对齐是独立变更。** v1 的 anchor 只有经纬度、来源和 datum；north reference 记录依据，没有 heading/scale/reprojection manifest。添加 anchor 或改 `north_reference` 不会把任意本地坐标自动对准真北。需要用户确认控制点/方向，构造显式 frame-change：全部相关 origin、U/V 轴、extrusion axis 与必要位置一起变换，以同一 undoable group 提交，旧 run 失效；不能只改坐标表单后宣称已对齐。只要没有足够控制点/方向，继续在局部平面编辑，不伪造地理叠加。（D）

### 屋面平面与像素图纸

已有 `roofCoordinates(roof, enu)` 仅把 **已在屋面上的 3D 点** 投到 U/V。地图点击只给水平 E/N 时，应先用明确 roof plane 求交：令 `n=U×V`，`z=(n·O−n_e E−n_n N)/n_u`，再调用 roofCoordinates；当水平投影不可逆/数值不受支持时显性拒绝该地图编辑，保留数值 UV 路径。不能直接把 `(E,N,0)` 投上坡顶，否则斜长会缩短。新屋面缺坡面/高度时先留 raw draft；用户明确选择的“平面、项目相对高程场景”可用，但需记录为场景，不能冒充实测。（D，符合现有几何合同）

自有平面图纸的完整校准（D，成熟先例 R/E1）：保留原件 hash、页码/像素尺寸；用户选两个点并给实际长度，记录 `m_per_pixel=L/d_pixel`；确认已知方向/北箭头、像素 Y 向下与工程轴关系，另用第二条独立尺寸检查比例。两点量尺只确定均匀尺度，不能校正透视照片或非均匀缩放；这种来源需要实际控制点/适用 rectification 或保留为参考，不能沿用单比例标工程可量。斜面图、水平总平图、透视照片必须区分；图纸斜长不再除/乘一次坡度。没有 geographic tie 也能完成局部工程项目。

GeoJSON 外环和所有内环都保留；仅格式转换首尾闭合点，不静默修复自交、填洞、合并多栋或删除重复/退化问题。MultiPolygon 与多面工程文件经用户确认拆为多个独立屋面 ID，绝不合成一个包围框。带 Z 工程点需校验共面性和残差；容差来自来源/项目确认，不能借屏幕像素或库默认 epsilon 定义工程精度。来源精度未知仍为 null。（D）

### 结构化来源与导入 manifest

现有 `Source` 能保存 derive/retain/export 权限、来源 URL/hash、取得日期、precision、校准说明；它没有结构化 CRS/变换、原件资产引用或到期生命周期。不能把新增字段随意塞进 strict `GeometryDocument`。现有 `Assets` 仅接受 permanent，HTTP 通道目前也没有通用几何/图纸 intake。（V）[Source wire](../../../apps/planner/src/domain/geometry.ts)、[永久 Assets](../../../services/engine/src/linker_engine/planning/assets.py)、[当前 intake](../../../services/engine/src/linker_engine/planning/http_asset_intake.py)

建议新增具名 `GeometryImportV1` 合同和可信 intake（D），与既有 Assets/receipts 集成：

```text
GeometryImportV1
  schema_version, source_id, source_kind
  original_asset_id/hash, source_feature_ids, acquired_at
  source_crs, axis_order, horizontal_unit, vertical_reference/unit
  project_origin, conversion_pipeline, implementation_version/grid_hashes
  calibration_method, control_points, declared_lengths, heading_basis
  residuals/precision_status, plane_model/elevation_basis
  provider/contract/licence_reference, attribution
  allowed_display/derive/retain/export, retention_basis
  output_object_ids, output_geometry_hash
```

永久 import manifest 可作为 owned asset；在项目 `inputs.geometry_imports` 中以 source_id 关联它，**同时**扩充严格的 server/browser schema 与 foreign-asset/项目所有权检查，参考现有 profile selections 的验证模式。这里是建议存放位置，不是当前字段已存在。`GeometrySource.reference_sha256` 的语义必须明确引用哪份原件/manifest，不能一个 hash 同时代表两者；原件 hash 与转换 manifest hash 分列。人类可读 calibration_note 只是摘要。（D）

暂存 Google/Solar 来源使用独立 provider store：`acquired_at / expires_at / contract_basis / deletion_state / attribution`，明确缓存、备份和派生内容的具体许可。服务器按允许列表建立权利事实；浏览器不能把 provider raw 标成 `user_measurement` 或 `permanent`。`export=unknown` 与 retain/derive 分开，报告/原生文件导出按实际许可检查。（D）

## 5. Terra Draw 1.35.0：真实事件与领域历史的接法

以下为实际安装包 `.d.ts` 与发布 sourcemap 的一手源码，附录记录 hash；本轮还做了无地图/无网络的公共 API 探针。它们证明接口行为，未证明地图上的鼠标/触控或 React 19 运行。（V）

| 核实结果 | 对应接缝 |
| --- | --- |
| `on('finish', (id, {mode,action}))`；`change(ids,type,context)` 有 create/update/delete/styling，API 更新带 `origin:'api'`，几何更新还有 `target:'geometry'`。`on/off` 必须用同一个 callback。 | 监听 `change` 更新 preview/错误，不逐事件提交文档；回填 guard 与 origin 过滤防循环。selection/styling 不进工程历史。 |
| `addFeatures()` 返回每项 validation；`getSnapshot()/getSnapshotFeature()` 是复制；`idStrategy` 可自定义，默认 ID 规则不是所有领域字符串。 | 复用现有 domain ID，或显式 binding；每次检查 addFeatures 失败，不允许静默缺图。自定义 `getId/isValidId` 同时覆盖新建和已加载 ID；不能使用数组下标、最大数加一、地图 feature 行号当领域身份。 |
| Base adapter 默认 `coordinatePrecision=9`；实际 probe 中更高小数精度的 longitude 被拒，reason 为 `Feature has coordinates with excessive precision`。 | 显式配置并验证地图 display precision，对生成的显示 GeoJSON 做具名量化；精度不当测绘误差。未编辑 metric 点不经过 display round-trip 回写，完整文档不因地图加载而量化。 |
| Select 模式具有顶点拖动、插入/删除、feature drag、旋转/缩放 flags。源码在中点插入时可先发 `finish(insertMidpoint)`，随后继续同一次拖动；不能假设 finish 与一次完整 pointer 手势一一对应。 | controller 以完整 gesture transaction 合并 finish/change；pointerup 后读取最终快照，一次提交；无 pointer 的独立键盘操作按明确动作边界。旋转/缩放也用统一 transaction/final snapshot，不能仅按 finish action 名猜已经覆盖全部动作。 |
| **Polygon 验证明确拒绝 `coordinates.length !== 1`，带孔 Polygon 不可直接进入该编辑模式。** `GeoJSONStoreGeometries` 仅 Polygon/LineString/Point，不是任意 GeoJSON union。 | 底层 MapLibre 可显示完整带孔屋面；Terra 的 editable handles 为外环及各孔的单环 Polygon。孔属于同一个 `RoofFace.holes_uv`，提交时一次 put_roof；不能因绘图库不收孔就填掉。 |
| undo/redo 是显式 opt-in；公共 API 探针中未配置时 `undo()` 返回 false。库提供 mode/session 两层 history，但它不了解源资产、项目 revision、账户和其他视图。 | 现有 domain history 是完整项目唯一 undo。不要启用独立 Terra session history；未完成画线若使用 mode 内部撤顶点，明确它只处理当前 raw drawing，完成后进入 domain history。全局 Ctrl/Cmd+Z 由焦点和 gesture 状态统一调度。 |

`MapDrawController` 的最小事件桥（D）：

1. 激活地图后保存 `baseGeometry`、编辑目标、坐标/来源 manifest 和稳定 binding；不把每次地图 `move` 当 revision。draw start 后缓存原状态；地图绘制结束的同一 click 不再触发自动建筑选择——现站已有该真实事件次序的测试/验收经验，需在新路径重新验证，不能复制旧状态机。
2. 每次变化只更新 raw draft、屏幕预览和量尺；绘图属性里只允许白名单 domain binding，忽略 closing point / coordinate point / midpoint 等库辅助 feature。API 回填以 guard 包住，避免其 change 被当用户输入。
3. 手势最终结束后，调用 `prepareGeometryImport`，得到带出处/校准的 candidate 或具体 issues；缺 plane/比例/来源时保留原输入与用户文字。新对象及其 Source 一次 group 提交；修改使用现存 object.before，group.before 保护整个坐标 frame。
4. 若其他视图先改过项目，现有 `geometry_frame_changed` 拒绝过时提交，保留 raw draft 供重新确认；不从最后地图快照覆盖整个文档。accepted 后重新从权威文档投影地图，undo/redo 同样重投影。
5. 屋面外环和孔 handles 绑定 `roof_id + ring kind/index + base hash`。当前 holes 没有独立永久 ID，不能伪称已有；同一事务结束前禁止 index 漂移，过时就重新绑定。孔增删更新一个 roof。Obstacle/keepout 则使用它们现有独立 ID，先明确目标 roof plane。
6. 删除走领域命令。删除屋面确认 expected_dependents；库的 delete key 不能先清文档再推测依赖。失败、cancel、Esc、route unmount、provider switch 均不擦掉确认过的工程对象。

顶点编辑只替换实际编辑的点；整体移动/旋转/缩放若语义为刚体/等比例领域变换，应从手势计算 metric delta/pivot/angle/scale，再作用于事务开始时的原始 metric 几何。不能把投影量化后的整个环无条件反写，导致未触点漂移或 geographic screen 旋转改变本来应保留的实际长度。新增描绘则以其明确地图/来源精度进入 candidate。（D）

raw draft 与合法文档分开：未闭合 ring、无效数值字符串、待选图纸控制点可存在编辑 draft；不能用 `0`、空 Source 或伪造 anchor 让它过 strict geometry。若要刷新恢复该 raw draft，新增有 schema/版本的恢复记录，以 verified session scope + project + draft UUID 管理；沿现有 DraftStore 的身份隔离/迁移/容量与失效提示规则。保存按钮不能把未完成 raw draft 说成已保存的工程几何。（D）

地图组件用 effect 创建/销毁资源，回填只在 style/sources 真正可用后进行；切换语言/路由/账户、React StrictMode 重挂载要 `off → stop → map.remove` 并清理自己监听、observer、网络句柄和 DOM。`stop()` 的库注释与实现不可代替本站资源回收验证；map/GPU/key/CSP/同意失败走 typed 状态并保留数值/2D路径。（D）

## 6. 首条完整可验收路径与后续数据放行

**首条路径 M1（D）：自己的测量/图纸 + 明确位置 → 地图参考/绘制 → 同一米制文档 → 2D/3D → 保存/重开。** 不需要先取得 Google key，也不取消 Google 搜索/Solar 后续能力。

1. 用户输入/导入自己的 WGS84 位置，或先做无地理锚点的本地项目；国家/时区与 EN/DE 独立。上传其有权使用的已知尺寸图纸/工程 GeoJSON，保留 owned 原件与回执。
2. 图纸完成尺度、方向、平面/高度与质量确认。可以用自有、可配准的图像作为地图来源；使用区域正射时先通过该产品的显示/描绘/留存权利与真实网络加载门。不能直接把 Google 搜索位置替代此长期锚点。
3. draw roof→hole→obstacle/keepout，选择、顶点编辑、移动、数值改正与 cancel；一手势一 history。缺测项原样可见，不在图上默补坡度/障碍高度。
4. 切 2D/3D/对象树，核相同 ID、坡面长度、孔洞、数量与来源；布局调用现有 review，结果绑定当前 geometry hash。
5. undo/redo、保存、刷新/重开同一项目，校准 manifest、原件 hash、对象与数值一致。冲突/断网/地图失败不丢原件和 raw draft；导出与后续结果继续使用该 revision 和许可合同。

**M2 地址搜索与具体地图 provider**：取得真实受限 Google key/billing/EEA 合同，走官方 UI Kit 选择→视口定位→自有几何叠加。实际验证 SKU/归属/同意/key denied/quota/网络，不把可加载脚本当完成；未取得持有者事实前可完成接口与 synthetic fixture，但不能声称真实搜索已通过。

**M3 自动屋面**：先选择一个许可/CRS/年份明确的真实区域 LoD/工程数据小样本，经 trusted source adapter→原件/质量→roof candidates→建筑确认→同一 geometry import。Google Solar 采用其专用能源设计与暂存路径：先解决 raw data lifecycle，再以有/无 coverage/邻楼/陈旧影像样本验证提取，不能用 segment bbox 或 3D 地形网格凑精确屋面。

既有欧洲来源中，荷兰 PDOK 给分析用 CityJSON，3D Tiles 主要用于展示；LoD 2.2/1.3 与年份需逐对象读取。奥地利正射不是 3D 屋面；瑞士 3.0 Beta 的覆盖不能说成全瑞士；England DSM 不是整个 UK；LoD1 平顶不是实际平屋顶事实。详见 E1 原件。图层可显示、文件解析成功、几何可布局、结构/消防/电气/设备国家资格分别验收；M1–M3 都不自动放行完整欧洲工程。

## 7. 少量必须优先的夹具

这些是新增地图边界 fixture；已解决的布局/数值矩阵继续沿用，不重写另一套。

| 夹具 | 必须证明的结果 |
| --- | --- |
| F1 地理轴/单位/纬度 | 科隆、伦敦、赫尔辛基的具名 synthetic 经纬度偏移与 PROJ/ECEF oracle 对照；lon/lat 交换、EPSG:3857 米数伪装 GeoJSON、missing Z/不明垂直基准都得到明确结果。zoom/heading/地图 renderer 不改变 metric 文档；独立数值容差与来源精度分别标注。 |
| F2 坡顶/孔洞/图纸 | 已知 3-4-5 坡面：水平 4m 对应斜长 5m；有洞屋面在地图显示/各 ring 编辑→2D→3D→review 全程保洞。图纸两点量尺+第二尺寸，透视/非均匀缩放不被误当可量。原始 ring 与 source hash 可读回。 |
| F3 编辑与历史 | API 回填、select/styling 不创建 history；中点插入后继续拖、顶点拖、feature drag、旋转/缩放、delete/cancel 一动作一次提交。其他视图中途改 frame→旧地图手势拒绝且 raw draft 可恢复；undo/redo 后所有 view 数值一致。 |
| F4 来源/生命周期 | Google Places 定位不永久污染 anchor，不用于 point-in-polygon；标准卫星描边不能伪装 user-owned；合法图纸/区域来源成功。Synthetic Solar 到期从缓存及备份策略确实处理，冻结 PDF 与 raw 重算状态分别读回；不能只改 expires_at 字段。 |
| F5 真实完整用户链 | M1 至少德国及非德国项目；M2/M3 每个启用 provider 有真实成功/无数据/错误样本。EN/DE × 1440/390 完成绘制、数值替代、保存重开和地图失败恢复；键盘/触控、署名可见、卸载无重复请求/监听。第三方调用仅在实际启用的隐私合同下。 |

## 8. 本轮已验证、持有者事实与证据索引

### 本轮实际运行

- 本机安装核对（V）：`plugins/linker-tools/node_modules/` 的 MapLibre **5.24.0** / Terra Draw **1.35.0** / adapter **1.4.1**；adapter peer 是 Terra Draw `^1.0.0`、MapLibre `>=4`。`apps/planner/package.json` 当前没有这三个依赖。没有把安装证据冒称新 app build/浏览器证明。
- Terra API 无网络探针（V）：自定义 ID `roof-domain-17` 的 `addFeatures` 返回 valid；修改 snapshot 不影响 store；add/update/remove 的 change 都标 origin=api，update 标 target=geometry；默认 `undo()` 返回 false。带孔输入返回 `valid:false / Feature has holes`；超过9位小数的坐标返回 `valid:false / Feature has coordinates with excessive precision`。没有地图 UI、tile、pointer 或 React runtime 测试。
- 已有 engine venv 的 **pyproj 3.8.0 / PROJ 9.8.1**（V）。直接执行官方 topocentric 样例得到 `(-189013.869, -128642.040, -4220.171)` 米，与官方三位小数一致。另用独立写出的 WGS84 ECEF+ENU 公式对照 PROJ：三地点各偏移 `(+0.0001°, +0.0001°)`，高度约定 0；最大 ENU 差约 `1.23e-15 m`，逆变换最大角差约 `7.11e-15°`。这只是转换实现探针，不是实测屋顶/测绘误差门。

| synthetic anchor (lon, lat) | PROJ ENU metres, input anchor+(0.0001°,0.0001°), h=0 |
| --- | --- |
| `(6.96, 50.94)` | `(7.028802470, 11.124717635, -0.000013573)` |
| `(-0.1276, 51.5072)` | `(6.942942240, 11.125801937, -0.000013479)` |
| `(24.9384, 60.1699)` | `(5.551347374, 11.141521293, -0.000012132)` |

### 仅真实持有者能提供的事实（A）

Google Cloud 项目 ID/计费地址及实际协议、已启用 API/配额、由持有者设置好的浏览器/服务器凭证与允许域；实际图纸/测量原件的使用权、控制点/尺寸/垂直基准和现场变化。这些事实不阻断 GeographicBridge、draft/command 接缝、图纸 intake 与 synthetic 测试；没有它们不冒称相应生产 provider 已验证。本轮未申请账号、启用计费、打印/写入密钥或借用 demo key。

### 一手原件与取得方法

本轮外部取证全部以 Apify 为入口；没有普通搜索或直接网站 fallback。下表 hash 是对应 dataset item 的 markdown/text UTF-8，不是整个网页全部资源。既有 Google/欧洲材料只读取原件与索引，不重新下载整组资料。

一次补核 NRW WMS 的尝试未形成可用原件：`6vZXLhF2LWasPwQPw / rmyYlKCflCEygWKs4` 取得 capabilities HTTP200 但正文/HTML为空，另两页长时间未完成，已主动中止。尝试换官方 `apify/cheerio-scraper` 时 API 明确返回 `403 full-permission-actor-not-approved`，未批准账号全权限、未改设置；随后继续用已获准的 website-content-crawler 缩成单 URL、设超时/重试和 raw 提取参数重跑，`yeibiWfm0g3ZG8mQd / DYoR0pdTI75Ky7tMW` SUCCEEDED/HTTP200，仍无 XML 正文。**不把这些 run 的成功状态当作该 WMS 图层、当前许可、CORS 或真实 tile 加载已通过。** 旧实现中的 `https://www.wms.nrw.de/geobasis/wms_nw_dop` / `nw_dop_rgb` 仅是可继续核的调用线索；M1 可用自有图纸/合法原件完整推进，不以此未解抓取冒充默认区域底图已放行。

| 证据 | 官方 URL/具体依据 | Apify run / dataset 或已存在原件 |
| --- | --- | --- |
| P1 新取转换/GeoJSON/Solar 接口 | [PROJ topocentric](https://proj.org/en/stable/operations/conversions/topocentric.html) 定义、Usage；[cart](https://proj.org/en/stable/operations/conversions/cart.html)；[RFC7946](https://datatracker.ietf.org/doc/html/rfc7946) §3.1.1/3.1.6/4；[MapLibre MercatorCoordinate](https://maplibre.org/maplibre-gl-js/docs/API/classes/MercatorCoordinate/) 单位；[Building Insights](https://developers.google.com/maps/documentation/solar/reference/rest/v1/buildingInsights/findClosest) Query/RoofSegment；[Data Layers](https://developers.google.com/maps/documentation/solar/reference/rest/v1/dataLayers/get) Query；[GeoTIFF](https://developers.google.com/maps/documentation/solar/reference/rest/v1/geoTiff/get) HTTP | `Tu1p7ogciRdG2UnNK` / `9oV6esjQ5cH6fGIAd`，SUCCEEDED，7/7 URL HTTP200；cheerio、depth0、并发2、robots、无整覆盖文件下载。 |
| G1 Google 合同/计费/身份（R，本轮重新读回） | EEA ToS §3.3.2；EEA SST §6/15/16/21；EEA FAQ；Maps/Solar billing 与 key security | `dJx5u7MyTXZ8mcbOY` / `BjPtwqrk1LVYsfvzO`。逐 URL/hash 已列 [MAP-ADAPTER §9](../2026-10-22-planning-implementation/MAP-ADAPTER.md#9-本次外部证据如何取得)。 |
| G2 coverage/署名（R，本轮重新读回） | Solar coverage HIGH/MEDIUM/BASE；policies 的 Other attribution requirements / new content | `fLYaXdMR5pH0HmBhF` / `hfkdb7S2iRCSwFWqN`，原件索引同上。 |
| G3 当前绘图/EEA差异/地点 UI（R） | Google Terra Draw sample、EEA Solar/Places；Basic Autocomplete / UI Kit / loader | `ICYaVDZkQ7e72amJC` / `qbdGR0trLZNXsEccP`；`wirIobqCzE0UylgKw` / `4U7fXtQXAH8e54nt8`；`dwRbRtvKrEXNN7NZJ` / `afohawhxocAFDyIiY`。具体 URL、hash 和限制沿用 MAP-ADAPTER。 |
| E1 欧洲资料与人工路径（R，本轮只读 git 原件） | [OpenSolar Manual](https://support.opensolar.com/hc/en-us/articles/13251322728975-How-to-design-in-Manual-mode)、[Easy PV Quick Roof](https://help.easy-pv.co.uk/books/buildings-and-roofs/page/introduction-to-quick-roof-design-mode)；[PDOK API/许可](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1)、[basemap.at](https://basemap.at/)、[swisstopo OGD](https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices) | 固定 commit [`768cc73e…/REPORT.md §4/6`](https://github.com/AssassinFlash/de-linker/blob/768cc73e921d3b07afd5548d51c43f47b2e5fc5c/docs/research/2026-10-22-roof-europe-precedents/REPORT.md)、同目录 `sources.json` 和 `raw/`。官方 geo `w939akEsOLMazBWMs` / `fIWOSxRwJ0sVhgUVk`；final `tgo7ltkiuAUVG8LiD` / `nYgyb86mTKcm3POmX`；许可正文 `oOm29iMITSWT9b5M6` / `Y8SRNBmuRA4rJFDL4`。 |

P1 内容 hash：

```text
topocentric afbf15feeea9460f7d28142a14d8d2f1a9cdf50a1ecfeb85dc4aea4e16909a0e
cart 58256b9dd948286193705467b8a95c463bbcf9676b9f86a1cce6030448643092
RFC7946 d7602d21d52f7a87d4b2787e82e13acea5951771e3a7b390f0794f495cea9cca
MercatorCoordinate 39403ae42104380bc11d5c0a94c5245acd579f5739ef735b696fcf3db7160e63
buildingInsights 55dca8b4ea5c051413da3c3fad1e39bf9b96780aef290530758afe5caa3b7d63
dataLayers a3d97c97d74d506e3478bafaca7af272c7a40bc138a4d23161be2f20e31523a9
geoTiff ded8bbf2132e717f6b90d7920a3e6cf39705295baf9fa9acda4857f638fe79ff
```

V1 安装包一手证据：`plugins/linker-tools/node_modules/terra-draw/dist/terra-draw.d.ts` SHA256 `f05e80a6f1f7be0227115e1c2601c75ceda7e32ff098634f0d2cdc9bfea924cc`；`common.d.ts` `92878d2bf635173da4922f0abb212c954d43e6380c7b44b8621d59db298153ad`；`terra-draw.modern.js.map` `52684d483063ff148d5b9fdc94d94c2c8657a82ac955372ca8043d0f3237ef25`。sourcemap 内发布源码：`src/terra-draw.ts` SHA256 `24fae11bc2fe2fbe33694f68fe536a623b14c2abd6db94c7aeb202a83bb5ded4`，API origin/ID/events；`src/modes/select/select.mode.ts` SHA256 `3ad142f07b9717b1c59e63b34920cc5c53e09e31719e63262ca1852fe82cbecf`，中点 finish/drag-end；`src/validations/polygon.validation.ts` SHA256 `a0458a411787e008e8a5580234b2cc65f980e931207458d3e144c0e63fd2b016`，带孔拒绝。未复制库源码或其依赖入研究目录。

研究交付只创建此文件；没有给地图接入、全欧洲覆盖或工程整体状态打 PASS。最先实施的接缝是 **GeographicBridge + 有来源/校准的 import candidate → 现有一次 group commit**，随后接 MapViewport/Terra handles 与真实 M1 用户链。Google key/合同和现场事实是具体 provider/数据的验收输入，不是暂停全部工程编辑的理由。
