# 地图、绘图与屋面数据适配合同

核实日期：2026-10-22 UTC（收口时本地为 2026-10-23）。用途：统一 Planning 工作台的生产实现决策。性质：原始源码和当前官方文档研究；本次没有申请或使用 Google key、启用计费、安装依赖、运行地图 UI 或核准某栋屋面的精度。源码读取基线为工作树 `7591075a779e98ea700dcf62de2aa1141c57bc68`；其他实施者仍在修改，本文件不描述生产站现状。

## 1. 可直接实施的决定

**采用成熟绘图层 Terra Draw；将地图渲染、地点搜索、屋面数据、工程几何四者分开。Google Maps 是可选的成熟渲染器，Solar API 是另一个独立的数据服务。** Google 官方当前就提供 Terra Draw + `TerraDrawGoogleMapsAdapter` 的绘图示例，包含选择、顶点编辑、拖动和旋转，并输出 GeoJSON；Terra Draw 自己同时支持 Google Maps、MapLibre、OpenLayers、Leaflet 等适配器。没有必要自行发明地图绘图框架，也没有证据要求沿用旧 MapLibre 页面或排除 Google Maps。[Google 绘图示例](https://developers.google.com/maps/documentation/javascript/examples/map-drawing-terradraw)、[Terra Draw 官方仓库](https://github.com/JamesLMilner/terra-draw)

**长期可编辑、可重算的屋顶项目，必须使用明确允许描绘、衍生和留存的几何来源。不能默认把 Google 卫星底图上的点击描边变成“用户自有几何”。** 当前 EEA 条款 §3.3.2(c) 明文以“从 Maps JavaScript API Satellite 底图描绘或数字化建筑轮廓”为禁止示例。这是数据来源限制，换绘图库、用户点确认、换文件格式或算出米制坐标都不会自动解除。用户自己的测量、合法图纸、明确允许衍生的正射影像/三维数据应走另一条有来源的几何输入通道。[EEA ToS §3.3.2](https://cloud.google.com/terms/maps-platform/eea)

推荐顺序：

1. **先建统一的 Terra Draw 编辑模式与米制领域接口**，地图供应商不进入计算内核。默认编辑底图由区域来源能力决定，须有可核对的描绘/留存权利；图纸、尺寸和测量输入也能进入同一个工程模型。
2. **Google Maps JS 可承担地点定位、环境参考、已有合法工程几何的显示，以及自有/另获许可影像的地图承载。** 使用其标准卫星内容时，不开放默认导出建筑描边的工作流；若要开放该用途，先取得明确覆盖该用途的合同授权。Maps JS 支持自定义 ImageMapType，技术上也可承载另获许可的图像来源，但来源对齐、归属与各自许可仍须验证。[地图类型与自定义图层](https://developers.google.com/maps/documentation/javascript/maptypes)、[EEA ToS §3.2.1(c)](https://cloud.google.com/terms/maps-platform/eea)
3. **Google Solar 作为可选屋面/太阳能数据适配器单独评估和放行。** 其专门的系统设计用途和固定介质留存例外值得采用，但不能将它误作“买了 Google 地图就自带全欧洲屋面”，也不能将其短期缓存自动写进永久不可变资产库。[Solar 概览](https://developers.google.com/maps/documentation/solar/overview)、[EEA Service Specific Terms §21](https://cloud.google.com/terms/maps-platform/eea/maps-service-terms)

上述是实现建议，不是已完成集成或法律许可确认。真正阻断特定来源的是该来源缺少所需能力/权利/凭证，而不是地图供应商的名字。

## 2. 已取得 Aladdin 源码究竟证明什么

固定源码为 `7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa`，本地 [源码 ZIP](/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-calculation-550/docs/research/2026-10-22-trace-software-access/reusable/raw/aladdin-7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa.zip)，25,329,681 bytes，SHA-256 `1441ac0f978a12d2930d390e22c195b338f35cb64bb8005e3aacd6f437bfb40a`。它是此前实际取得的源码包，本次仅用 `zipfile` 只读读取相关文件，没有解压、安装、执行其凭证或复制凭证。源码 UI 版本 2.0.6 与此前实操官网 2.0.7 分开记载；不能据此声明同版运行行为。

| 源码事实 | 定位 | 对本项目的意义 |
| --- | --- | --- |
| `GoogleMap` 来自 `@react-google-maps/api`；接受 center、zoom、tilt、mapTypeId | [groundMap.tsx:6、180–195](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/components/groundMap.tsx#L180) | 证明采用成熟 Google 渲染器，不证明特定 key、计费、精度或地图流程已跑通 |
| `useJsApiLoader`、`libraries=['places']`、`StandaloneSearchBox` | [mapPanel.tsx:11、24、120、312](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/panels/mapPanel.tsx#L312) | 旧 Places SearchBox 模式；新接入必须检查当前生命周期与 EEA 条款 |
| 选择结果写入经纬度、formatted_address、countryCode，并登记 undo/redo | [mapPanel.tsx:126–177](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/panels/mapPanel.tsx#L126) | 可以学习状态/撤销模式；地址来源、保存权利不能由源码继承 |
| 地图拖移后做反向 Geocoding；有 Ground Image 开关 | [groundMap.tsx:35](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/components/groundMap.tsx#L35)、[mapPanel.tsx:253](https://github.com/Institute-for-Future-Intelligence/aladdin/blob/7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa/src/panels/mapPanel.tsx#L253) | 不是 Solar API 调用证据，也不是底图截图/衍生内容可任意导出的许可证据 |
| 这两个组件没有承担屋顶多边形绘图 | 同上两文件 | 本次只能确认其位置与视口流程，不能把 Aladdin 全部 3D 编辑能力归到 Google Maps API 上 |

当前工作树旧 `plugins/linker-tools/src/configurator/roof/RoofStep.tsx` 使用 MapLibre、`TerraDrawPolygonMode`、MapLibre adapter；锁文件是 MapLibre 5.24.0、Terra Draw 1.35.0、MapLibre adapter 1.4.1。这只是旧代码事实，不构成新编辑体验、运行或全欧洲数据覆盖的验收。可复用的是成熟库及研究结论；新工作台无需保留旧状态机和旧坐标载荷。

## 3. 2026 年不能照抄的 Google 组件

| 能力 | 当前官方事实 | 实施决定 |
| --- | --- | --- |
| Drawing Library / DrawingManager | 2025-08 deprecated，**2026-05 起不可用**；当前 deprecations 明确列入 decommissioned，指向 Terra Draw | 不新增 `libraries=drawing`；旧 drawing-tools 示例仍存在，示例存在不代表 API 仍支持 |
| 旧 `google.maps.places.SearchBox` | 2025-03-01 起不向新客户提供；既有客户尚无停用日，仍修复重大回归，未来停用至少提前 12 个月通知 | 不将它作为新项目的默认搜索合同；不能误说所有既有 SearchBox 已失效 |
| 旧 `google.maps.places.Autocomplete` | 同日起不向新客户提供；官方推荐 `PlaceAutocompleteElement`，既有客户没有当前停用日 | 非 EEA 的迁移可评估新组件；EEA 还要满足下面的数据展示规则 |
| `PlaceAutocompleteElement` | 新 Places API 支持；当前指南“加到 Google Map”明确以 billing address 在 EEA 外为条件；选择事件用 `gmp-select`，再按需 `fetchFields()` | 不能直接把 Aladdin SearchBox 替换成它便宣布欧洲合规 |
| Places UI Kit `BasicPlaceAutocompleteElement` | 只返回所选 place ID；启用 Places UI Kit，不要求同时启用 Places API；有独立 UI Kit Autocomplete per Session SKU | EEA 地图关联搜索的首选 Google UI 路线，按官方 Basic + Place Details UI 的 location 示例验证，不手工重建 Google 地址/POI 卡片 |
| 旧 45° 影像 | Maps JS 3.65 / 2026-05 起 satellite/hybrid 不再自动切 45°，`setTilt(45)` 无效 | 平面测量/绘图固定正射/俯视模式；不要用“45° 倾斜能看屋顶”作为该 API 的既有能力 |

生命周期依据：[当前 deprecations（drawinglayer 已重定向至该内容）](https://developers.google.com/maps/deprecations#drawing-library)、[SearchBox / Autocomplete reference](https://developers.google.com/maps/documentation/javascript/reference/places-widget#SearchBox)、[新 Autocomplete 指南](https://developers.google.com/maps/documentation/javascript/place-autocomplete-new)、[Basic Autocomplete 当前指南](https://developers.google.com/maps/documentation/javascript/places-ui-kit/basic-autocomplete)。Terra Draw 接入依据是[当前 Google 示例](https://developers.google.com/maps/documentation/javascript/examples/map-drawing-terradraw)，不是尚未迁移的[旧 Drawing Tools 示例](https://developers.google.com/maps/documentation/javascript/examples/drawing-tools)。

Basic Autocomplete 的具体窄流程：加载一次 Maps JS → `importLibrary('places')` → 创建 `BasicPlaceAutocompleteElement` → 监听 `gmp-select`，读取 `event.place.id` → 使用 Places UI Kit Place Details 元素 → 其 `gmp-load` 后读取 `place?.location` 来定位地图。官方示例已有这个序列。保持 Google 提供的 UI、归属、条款链接和通知；不要把 Place Details UI 的内部地址/POI 文本抓出来重排进任意持久工程卡片。[Basic 示例](https://developers.google.com/maps/documentation/javascript/places-ui-kit/basic-autocomplete)、[UI Kit 迁移指南](https://developers.google.com/maps/documentation/javascript/adopt-places-ui-kit)

Basic 与传统 Place Autocomplete 不是同一组件，也不是同一 SKU。UI Kit overview 抓取结果的自动摘要仍含 Experimental 的泛称，而正文将 Advanced 元素逐项标为 preview；EEA FAQ 另称 UI Kit 引入 GA。**本报告不把整套 UI Kit 一概标为 GA 或 experimental**；以明确的元素指南和 release notes 判读，后者在普通版本记录 Basic 的改动，而将 Advanced 新增明确标为 beta。核心定位采用 Basic 路线，选择实际已验证的稳定 channel，不用 Advanced preview 满足稳定性要求。[UI Kit overview](https://developers.google.com/maps/documentation/javascript/places-ui-kit/overview)、[EEA FAQ](https://developers.google.com/maps/comms/eea/faq)、[当前 release notes](https://developers.google.com/maps/documentation/javascript/releases)

当前 versioning 正文列 `weekly=3.66`、`quarterly=3.65`，允许请求的编号为 3.63–3.66；编号会退出服务，错误/失效编号会落到默认 channel，不能靠写死 SDK URL 实现永久冻结。生产可以优先用可预测的 quarterly，前提是所用 Basic/UI 能力实际存在且验收通过；若需要 weekly，则在评审环境验证版本升级并记录实际版本。领域几何与 run 数值冻结不依赖长期可获取旧 Google UI SDK。[官方版本策略](https://developers.google.com/maps/documentation/javascript/versions)

## 4. EEA 与留存：必须进入领域合同

EEA 适用性按 **Cloud 项目关联 billing account 的地址**，不是屋顶所在国家、浏览器语言或访问者国籍。2025-07-08 后新项目/实质修改的集成适用新规则；新工具重构不能自行主张旧项目的未修改豁免。具体签署合同若有不同，以实际合同为准；本次没有读取 Linker 的 Cloud 账号或合同。[EEA FAQ](https://developers.google.com/maps/comms/eea/faq)

| 内容来源 | 已核事实 | 持久化与显示合同 |
| --- | --- | --- |
| Maps JS 标准 satellite / Street View | EEA ToS §3.3.2(a)–(c) 限制抓取、缓存及基于 Maps Content 创作，明确包括建筑轮廓描绘 | 不把底图瓦片/截图写入项目资产；不把在该底图描出的建筑轮廓认定为自由几何。未经用途授权不开放这类数字化路径 |
| 用户自己测量、上传且有权使用的图纸、允许衍生的区域数据 | Google 的禁止条款针对 Google Maps Content；MIT 绘图库不授予地图数据权利 | 这是我们建议的独立几何输入；分别验证上传者权限/数据许可后，才允许长期保存。仅声明“用户画的”不能证明它与 Google 来源无关 |
| Places API（legacy/new） | EEA SST §15.1 允许 lat/lng/place_id 与地图同用；其他内容不可与任何地图同用；“与地图”含旁边、视觉关联和链接 | 搜索/UI adapter 只输出获准的最小位置标识；EEA Google 富内容展示使用 UI Kit 例外，不在地图旁自绘 Google 地址/POI 结果卡 |
| Places UI Kit | EEA SST §15.3 豁免上述 Places 使用/展示限制；§16 要求保留 Google 提供的归属、链接、通知；lat/lng 可缓存至多 30 天 | UI 权利不是全部 API 响应永久存储权利；GeoReference 仍要记录来源/到期规则。place ID 可按允许它的文档长期保存并管理刷新 |
| Geocoding API | EEA SST §6.2.1 通常 lat/lng 30 天；§6.2.2 对发起该请求应用的直接最终用户功能，有特定、隔离、不能替代额外调用的长期缓存许可 | 不能把这个特定例外套到 Places 或 Solar，也不能把它当全用户通用地址库。是否满足条款用途应逐用途定义 |
| Solar Building Insights / Data Layers | EEA SST §21.1 专门允许能源系统可行性、设计/安装、特定 downstream transaction；§21.2 原始 Solar Data 缓存至多 30 连续日 | 原始响应、DSM/flux 等适用 Solar Data 不能默认入永久 CAS/备份；记录到期和删除，缓存过期影响重算能力 |
| 固定介质中的 Solar 数据 | §21.2 删除义务不适用于为 downstream transaction 纳入固定介质的 Solar Data；例子为能源设计、可行性研究、商业提案、营销材料；营销须用户 opt-in，设计/提案是用户为特定地址请求 | 可评估保留符合该条件的冻结设计/PDF；这不等于永久可编辑 raw JSON、可任意导出栅格或长期重放源模型。是否把机器可读归档当 fixed media，官方本条未明确，本报告不放行 |

条款原文：[EEA ToS §3.3.2 / §4](https://cloud.google.com/terms/maps-platform/eea)、[EEA SST §3、§6、§15、§16、§21](https://cloud.google.com/terms/maps-platform/eea/maps-service-terms)、[EEA Places 具体图示与定义](https://developers.google.com/maps/comms/eea/places)。这些限制与例外按具体服务读取，不能把一般政策页面的摘要当成覆盖 EEA 条款的结论。

Solar 的公开政策要求显示数据来源、保留归属；使用其数据或影像时注明 `Source: Includes solar data from Google`，新衍生内容另有 `Includes data from Google Maps` 的归属指导。页面还包含一般的地图显示规则，EEA 主合同去除了通用 non-Google map 禁令，因此需按实际账单区域和服务条款判定，不能一概声称“Solar 必须在 Google 地图上”或“可任意混用”。[Solar 政策与归属](https://developers.google.com/maps/documentation/solar/policies)、[EEA FAQ 的条款移除说明](https://developers.google.com/maps/comms/eea/faq)

**重算与冻结结果的冲突必须显性解决。** 自有且准许保留的几何可冻结为项目 revision 并固定字节。Solar 等短期许可资产应另设 `expires_at` / `retention_basis` / `deletion_state`。原始字节必须删除时，历史 manifest 只保留许可允许的来源证明与状态，不能继续声称该历史 run 可逐字节重算；应返回 `source_bytes_expired`，新的取得形成新资产/新 run，不覆盖旧 PDF。固定介质例外不是保留所有原始字节的借口。若业务要求无限期精确重放自动屋面，必须取得允许此用途的来源或合同，不能仅靠技术实现绕过期限。

## 5. Maps UI 与 Solar 数据的能力必须分开

| 服务 | 能带来什么 | 不能据此推导什么 |
| --- | --- | --- |
| Maps JavaScript API | roadmap / satellite / hybrid / terrain、视口、交互、覆盖物和自定义图像地图 | 自动屋面边界、坡度、障碍高度、太阳通量、工程尺寸精度、合法长期衍生几何 |
| Places / UI Kit / Geocoding | 地点搜索和定位 | 用户所点的建筑已正确识别、位置是测绘级、找到地址即拥有其屋顶模型 |
| Solar `buildingInsights` | 建筑位置、尺寸及太阳能潜力相关洞察 | 每个欧洲地址有结果、数据最新、真实屋面所有孔洞/障碍均完备、可替代勘测 |
| Solar `dataLayers` / `geoTiff` | 所选区域的 DSM、影像、年度/月度 flux、逐小时 shade 等数据 | 一旦返回就能长期存储或等同结构/电气设计放行；栅格分辨率不是整体工程误差界 |

Solar coverage 当前按 HIGH / MEDIUM / BASE 区分：HIGH 来自低空航空影像并以 0.1 m/pixel 处理；MEDIUM 为高空航空影像增强、0.25 m/pixel；BASE 为卫星增强、0.25 m/pixel。该文档提供 2026-05-06 coverage GeoJSON 下载链接。**这些是覆盖/处理分辨率，不是“全欧洲 10 cm 精度”保证**；实际项目仍须记录 imagery quality、拍摄/处理日期、请求点与所返回建筑身份，现场变化与障碍需要复核。本次没有下载整个覆盖文件，也没有用任何真实 key 请求一栋建筑。[coverage](https://developers.google.com/maps/documentation/solar/coverage)、[Solar 概览](https://developers.google.com/maps/documentation/solar/overview)

EEA Solar 调整页列出的当前技术差异是 Building Insights 缺少 `postalCode`、`administrativeArea`、`regionCode`。它没有宣布 EEA Solar 全面停用，也没有据此宣布无影像/无屋面；不能用这份调整说明反向虚构限制。[EEA Solar 调整](https://developers.google.com/maps/comms/eea/solar)

## 6. 窄 adapter 的输入、输出与边界

这是建议接口，不是现有代码已实现的描述。一个地图组件负责地图生命周期，一个绘图 controller 负责编辑状态；地址、数据抓取、几何变换由相邻模块负责。避免“大地图组件”同时请求产品、调用 PV 内核、写草稿和生成报告。

```text
MapViewportAdapter
  mount(container, locale, credentialsRef, consentState, mapSource)
  setView(WGS84 center, zoom, heading, tilt)
  showOverlay(GeoJSON, displayProvenance)
  events: ready / locationSelected / viewportChanged / error
  destroy()  // 清除监听器、绘图、DOM、网络取消句柄

DrawController(Terra Draw + selected renderer adapter)
  mode: select | roofPlane | obstacle | exclusion | static
  events: gestureStarted / draftChanged / featureCommitted / cancelled
  import/export: display GeoJSON only; no domain calculations

LocationSearchAdapter
  query/select -> LocationReference { provider, placeId?, WGS84?,
    origin, acquiredAt, retentionPolicy, displayContract }
  // Google EEA UI 优先 Basic Autocomplete + UI Kit，非任意重排地址内容

RoofDataAdapter
  acquire(request, applicableContract) -> SourceAsset | typedFailure
  // Solar 和区域 LoD/DSM/用户上传各自独立；不接管 MapViewport

GeometryBoundary
  commit(displayGeometry, sourceRef, calibration, georeference)
    -> validated local-metric RoofSurface / Obstacle / Exclusion
       | geometryInvalid | sourceRightsUnverified | scaleUnverified
```

每份几何至少包含：`source_kind`、`source_id`、取得日期、source/contract 版本、允许的用途/显示/衍生/留存/导出能力、证据引用、校准方式与误差状态、WGS84 地理参考、本地米制 CRS 定义/变换版本、单位、轴序、高程基准（已知才填）、屋面与障碍 ID。不要用 `licensed=true` 一个布尔值吞掉不同用途；不把未知权利写成 `false` 的永久事实，也不把未知写成通过。

`locationSelected` 首先只是搜索/视口结果，不能自动成为永久项目坐标。若地理参考来自有 30 日期限的 Places 位置，将它重投影成 ENU/本地米制点并不能清除来源期限；自有局部几何、外部地理锚点和地图视口应分开保存。永久项目地理参考须来自有相应留存权利的输入/来源，或确实满足该服务的特定例外；不能把“用户确认 Google 搜索结果”一概当作转为自有测量数据。

### React / WordPress / WindPress

- 外层采用 `@wordpress/element` 的 React lifecycle，Google 的官方 `importLibrary` loader / web component 放进一个窄 effect/adapter，不为地图额外打包第二份 React。`@react-google-maps/api` 是 Aladdin 的包装选择，不是必须复刻的依赖；若选用须额外验证当前 React/loader 兼容性。本次没有验证它的当前版本。[官方 loader 与按需加载](https://developers.google.com/maps/documentation/javascript/load-maps-js-api)
- 仅在工作台地图实际激活且满足本站隐私策略时初始化，单页面只加载一次 SDK；locale、网络和身份变化不留下重复 script/监听器。加载地图不要求网站账户已批准，也不因其价格/账户三态改地图几何；Google Cloud 身份与本站客户身份是两回事。
- WindPress 承接工具按钮、面板、状态、焦点和响应式样式。地图/库必要的渲染 CSS 不由 PHP 拼接；Google 归属、控件通知、UI Kit 合法边界不能被 CSS 裁掉。Shadow DOM 元素用官方公开 CSS custom properties/parts 调整，不能假定任意网站类名可修改其内部结构。
- 核心手势用 Terra Draw 的成熟 select / polygon / rectangle 模式，提供明确完成/取消、选中改点、删除和 undo/redo。障碍、孔洞、退距是领域类型与拓扑，绘图库生成一个 Polygon 不证明这些关系已正确；通过领域校验后才提交 revision。

### 统一米制几何

- GeoJSON 的 `[longitude, latitude]` 只在地图边界使用；Google 的 `{lat,lng}`、UI 坐标和领域米制点在类型上分开。Map pixel / Web Mercator world coordinate / zoom / CSS scale 都不能作为实际米数。
- 边界采用显式、固定版本的地理坐标变换，将 WGS84 映射到项目适用的本地米制 CRS；保存原点、完整 CRS/变换定义和轴序，逆变换用于显示。跨国不能套德国投影/邮编规则，不用一次经验性的 `cos(latitude)` 缩放代替坐标合同。
- `roofPlanXY_m` 是水平投影，真实斜面是另一个平面/局部基底。坡度、朝向、安装姿态分别存；不能拿平面地图的多边形面积直接当组件安装面面积。仅当该屋面确为单平面且坡度已知时，才可按该模型将投影变成斜面，不能让地图控件猜坡度。
- 绘图默认俯视、禁止编辑时透视/倾斜造成不明确测量；需要旋转时明确北向与领域方位。输入来源、校准长度、未知高度、投影面积与斜面面积要可查；地图供应商精度不是工程内核精度。
- 服务端校验 ring 闭合/去重、非自交、非零面积、合法洞/包含关系、单位和 CRS；组件 packing、碰撞、串联、容量或电气放行一律在领域/计算阶段完成。

## 7. 生产接入的身份、费用、隐私与故障

**Google Maps JS、Places UI Kit、Solar 独立启用，分别计量。** 官方 Maps JS 文档列 Dynamic Maps、Places 等不同 SKU；Solar 区分 Building Insights 与 Data Layers。不能把地图加载计费与 Solar 屋面请求混在一个“Google 费用”里，也不能把已过期的 $200 credit 当 2026 年承诺。本报告不报价；现行价格、项目 quota、需求量和可用免费额度应从当前 SKU / Cloud Console 对照。[Maps JS usage/billing](https://developers.google.com/maps/documentation/javascript/usage-and-billing)、[Solar usage/billing](https://developers.google.com/maps/documentation/solar/usage-and-billing)、[UI Kit get started](https://developers.google.com/maps/documentation/javascript/places-ui-kit/get-started)

| 条件 | 实施合同 |
| --- | --- |
| Cloud 项目、账单地址/合同、billing 与各 API enablement | 由真正的 Linker 项目承担；本次未读取，不能据 Aladdin 源码推定可用 |
| Maps JS / UI Kit browser key | 可到达客户端，但必须限定具体 website HTTP referrers 与允许 API；开发、评审、生产来源要正确授权。日志/报告不输出 key；不借用第三方源码或 demo 的 key |
| Solar / 其他 server web-service 身份 | 单独服务端凭证与限制；按官方可用方式使用受限 key 或 OAuth，不把 server key 发到 browser；客户端不能代理任意 URL/坐标批量抓取 |
| 配额与费用 | 使用应用级节流、请求去抖、按请求去重、错误退避和 Cloud quota；预算告警不应被当作自动硬停费。实际数字以该项目/该 SKU 当前控制台为准，不凭本报告设一个假定通用上限 |
| 隐私与定位 | ToS/Privacy 公开说明使用 Google；其服务会收集请求词、IP、坐标等。EEA ToS §4.3 对收集最终用户/设备位置要求事先、明确、可撤销同意；项目地址与用户设备实时位置要区分，不自动调用浏览器定位 |
| 无同意 / 禁止第三方 / CSP / key 错误 | 返 typed failure，保留已有几何和用户输入，提供可完成项目的合法图纸/尺寸路径；不悄悄向另一收费 provider 发送同一地址 |
| QUOTA、BILLING、DENIED、NO_COVERAGE、STALE、NETWORK | 分开状态；无屋面不等于无地图，无 Google 不等于无几何，无 coverage 不生成假屋面。自动请求失败不能清空人工修订 |

Google 身份限制依据：[API security best practices](https://developers.google.com/maps/api-security-best-practices)；隐私/数据与归属依据：[EEA ToS §3.2、§4.3–4.4](https://cloud.google.com/terms/maps-platform/eea)、[Maps JS policies](https://developers.google.com/maps/documentation/javascript/policies)。采用 Google 相关 SDK 不代表本站现有 CookieYes、CSP 或同意控制已经覆盖它，本次没有做动态核验。

Terra Draw 的[实际 LICENSE 全文](https://github.com/JamesLMilner/terra-draw/blob/main/LICENSE)是 MIT：保留版权与许可通知，软件按 AS IS 提供。Google 官方示例代码采用其页面所列 Apache 2.0 条件；MIT/Apache 许可均不授予 Google 影像、Places 或 Solar 数据使用权。[Terra Draw adapter README](https://github.com/JamesLMilner/terra-draw/blob/main/packages/terra-draw-google-maps-adapter/README.md)、[Google 示例许可尾注](https://developers.google.com/maps/documentation/javascript/examples/map-drawing-terradraw)

## 8. 选项比较与上线判定

| 路线 | 可复用的成熟能力 | 代价/真实边界 | 本报告建议 |
| --- | --- | --- | --- |
| Google Maps JS + Terra Draw Google adapter + EEA UI Kit | Google 地图 UI、地点搜索与成熟编辑层，另可展示自己的合法几何 | 自有 key/billing；EEA 展示/来源权利；不得默认描标准卫星建筑轮廓；无真实 key 动态证据 | 保留为生产候选，按数据用途接入，不能将“Google 有 Solar”当成用或不用它的理由 |
| MapLibre + Terra Draw + 允许衍生的区域影像/几何或自有图纸 | 通用地图引擎与同一绘图操作合同，工程几何可独立供应商 | 必须逐区域补来源、许可、覆盖、日期与精度；MapLibre 不自带影像/地址库，也不保证全欧洲一致 | 长期可编辑模型的优先来源路线之一；不要求复用旧 RoofStep，也不能以库存在代替生产证据 |
| Google Solar 数据 + 独立地图适配器 | building insights、DSM/flux/shade 等自动数据，专门能源设计用途 | 真实覆盖/返回建筑识别、EEA 缺字段、30 日缓存与固定介质例外、归属/费用 | 独立可选自动数据层；先解决合法留存与重算语义，按地址样本放行 |
| 上传图纸 / 实测尺寸 + 成熟编辑层 | 所有地区可进入同一米制领域模型，不依赖某家自动屋面覆盖 | 上传权限、标尺校准、真实坡面/障碍输入与质量状态 | 必须是一条完整可用的主路径；不能只是地图失败后的空白画布 |

上线前的真实验收应集中到下面这些结果，不能只做组件 mock 或 screenshot：

| 组 | 必须拿到的真实结果 |
| --- | --- |
| 自有身份与当前 API | 正确 billing 区域的 Linker key / 受限测试域，地图实际加载；UI Kit 搜索选择地点并定位成功；未加载 Drawing Library / legacy SearchBox；控制台对到预期 SKU、配额与费用事件 |
| 来源与权利 | 每种启用的 imagery/geometry 有用途、衍生、留存、导出证据；Google 标准卫星描建筑轮廓的默认工作流不被误放行；归属/条款链接在桌面和手机上始终可见 |
| 几何不随 renderer 改变 | 同一个有权保存的项目在两个选定 renderer 上显示/编辑，进入相同领域米制模型；换地图、zoom、拖移不改变实际长度/面积；round-trip 精度容差来自工程模型和来源，不能从小数位数推出 |
| 真实交互 | EN/DE、1440/390；画屋面/障碍、完成/取消、选择改点、移动、删除、undo/redo、触摸和键盘焦点；完成手势不被再次当作选择建筑；切语言/路由卸载不产生重复监听器 |
| 数据质量与失败 | 至少覆盖德国及非德国实际地址；有/无 Solar 结果、返回邻楼、不同质量/影像日期；key/referrer/billing/quota/网络/CSP/同意拒绝逐状态；项目不丢失，地图与屋面数据失败可区分 |
| 留存与复算 | 自有几何项目保存后重新打开、数值不变；短期 provider asset 到期后确实从缓存/备份策略处理，重算给明确状态；新请求生成新 run；冻结 PDF 保留及归属符合其具体例外，不偷偷重建永久 raw 仓库 |

本次验证到了“官方能力/生命周期/合同文本与已取得源码”的层次。**没有**真实 Google key、实际 EEA 项目、Solar 地址样本、项目级报价、地图实操或坐标变换独立精度证据，因此上述项目不能标成已通过。它们是具体实施/验收输入，不是研究结论里的隐含通过项。

## 9. 本次外部证据如何取得

所有外部读取经 Apify，使用既有环境凭证、`apify/website-content-crawler`、2048 MB、并发 2、`maxCrawlDepth=0`、遵循 robots；没有普通搜索/直接网站网络 fallback，没有改账户预算或权限。初始复用协调者已完成的四页 dataset；本次补抓围绕缺口。默认 readable 抽取会去掉某些 Deprecated 提示，所以 reference/places-widget 另以 `htmlTransformer=none` 和保留正文提示的清理选择器重抓；新客户限制引用后一次结果。一次错误的 `legacy/places-autocomplete` 路由返回 404，改为官方实际的 `legacy/place-autocomplete`；Terra Draw 根 README 的 LICENSE.md 链接返回 404，随后取得真实 `LICENSE`，不将 404 当许可原件。

下列 hash 是对应 dataset item 的 `markdown`（若无则 `text`）UTF-8 字节 SHA-256，**不是**页面所有 HTML、远程图片或整个 dataset 的 hash。只有公开 URL、run/dataset ID 和内容 hash 入库，凭证未打印或写入。

| 组 | Run | Dataset | 取证时状态 / item 数 |
| --- | --- | --- | --- |
| A | `fLYaXdMR5pH0HmBhF` | `hfkdb7S2iRCSwFWqN` | SUCCEEDED / 4 |
| B | `dJx5u7MyTXZ8mcbOY` | `BjPtwqrk1LVYsfvzO` | SUCCEEDED / 11 |
| C | `ICYaVDZkQ7e72amJC` | `qbdGR0trLZNXsEccP` | SUCCEEDED / 6 |
| D | `JrinaMjzU7BDj0Fox` | `oPI4tfMemO8bXJHR0` | SUCCEEDED / 3 |
| E | `VMWHVWi5X1OlRSdV2` | `aa4cO8yZcsFrnaY0d` | SUCCEEDED / 3 |
| F | `wirIobqCzE0UylgKw` | `4U7fXtQXAH8e54nt8` | SUCCEEDED / 5 |
| G | `dwRbRtvKrEXNN7NZJ` | `afohawhxocAFDyIiY` | SUCCEEDED / 3 |

| 组 | 官方公开页面 | Markdown UTF-8 SHA-256 |
| --- | --- | --- |
| A | [Map Types  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/maptypes) | `2e5a88cff350b9d725be5a258deaa1a08685c52949e968c9acf1c4c9ead8602e` |
| A | [Solar API overview  /  Google for Developers](https://developers.google.com/maps/documentation/solar/overview) | `58c04b2e6f1dcec6ac490b018b2dee3f051afe0d6bb3fed0d53821815861f29b` |
| A | [Solar API coverage  /  Google for Developers](https://developers.google.com/maps/documentation/solar/coverage) | `9d8937a7e1d54503f74b9974c61dc8f6511a046106853d87d318a2f1f04d3e57` |
| A | [Policies and attributions for Solar API  /  Google for Developers](https://developers.google.com/maps/documentation/solar/policies) | `bdea3f3d568e3bb0c8aad9a018544b08c46c70bcfba440800d94b14fd1314347` |
| B | [Deprecations  /  Google Maps Platform  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/drawinglayer) | `6469eb3c2eec625c4cdc40d10fa2b3547d9eb52e2959710cb111b63b6126d01b` |
| B | [Drawing Tools  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/examples/drawing-tools) | `35f5ad1c5073ada3703ac412ea11e3700c60e3f90a2a90d571e4efff5f9c9e0d` |
| B | [Place Autocomplete Widget  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/place-autocomplete-new) | `8a8e606e1db50afe0fba06a041ee57b63a0ece278ef7b1c17262d2244953c485` |
| B | [Google Maps Platform EEA Terms of Service / Google Cloud](https://cloud.google.com/terms/maps-platform/eea) | `0e644ea0eaa847c531651a19b9488160af91cdd4e6d3ce487bd3c5fdc2798c9b` |
| B | [Google Maps Platform EEA Service Specific Terms / Google Cloud](https://cloud.google.com/terms/maps-platform/eea/maps-service-terms) | `a1888cde8957c32dc9b8d578be68d3f876186eb668fcc549bc3cfa722e3fff88` |
| B | [Important changes for European Economic Area customers (EEA customers): Frequently Asked Questions  /  Google Maps Platform  /  Google for Developers](https://developers.google.com/maps/comms/eea/faq) | `d0ef36b5978efbd0d44fc5604e7dc182be0456415a6bd9576625db7aea9bbe97` |
| B | [Maps JavaScript API Usage and Billing  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/usage-and-billing) | `0b98509bdf1c398f330172aba3cb163d24d90c7eaacd6e6b1ecb28af5c391081` |
| B | [Google Maps Platform security guidance  /  Google for Developers](https://developers.google.com/maps/api-security-best-practices) | `6179fd3fe9d7babb378e82895d8b802df5efff25434e2530632c7e02efbd9e64` |
| B | [Solar API Usage and Billing  /  Google for Developers](https://developers.google.com/maps/documentation/solar/usage-and-billing) | `beee6fd93f3415dd3fffe804a282f1fd08751c19bcb2aeb30082ac5cc3ed0f64` |
| C | [Draw on a map using Terra Draw  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/examples/map-drawing-terradraw) | `7ce5985440ff154419ce982cad99c61235d58d5897dbedad60984fc5236958f1` |
| C | [Solar API adjustments for European Economic Area (EEA) customers  /  Google Maps Platform  /  Google for Developers](https://developers.google.com/maps/comms/eea/solar) | `c8953c6149d9bf5223988daa9cc9f36747dd18277534455ad9af20c496c66e07` |
| C | [Places API adjustments for European Economic Area (EEA) customers  /  Google Maps Platform  /  Google for Developers](https://developers.google.com/maps/comms/eea/places) | `d639a201673b6ee7dd807a6c094809af034b6fedd95d6eff47b00a83648895d9` |
| C | [GitHub - JamesLMilner/terra-draw: A library for drawing on maps that supports Mapbox, MapLibre, Google Maps, OpenLayers and Leaflet out the box · GitHub](https://github.com/JamesLMilner/terra-draw) | `797377a4e435076b9ea6c0bf95b5d615f5f06709744599ca17640b47763ef3b7` |
| C | [Policies and attributions for Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/policies) | `7488ea098f4617be5d2849da0e832af6a110a085d34538581cbe3824131cbd93` |
| D | [Adopt Places UI Kit for Existing Places API Users  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/adopt-places-ui-kit) | `9d67134ffd8a5a0fe094e301a355f2e53792bc90abca9a76dc4f1defbd888407` |
| D | [terra-draw/packages/terra-draw-google-maps-adapter/README.md at main · JamesLMilner/terra-draw · GitHub](https://github.com/JamesLMilner/terra-draw/blob/main/packages/terra-draw-google-maps-adapter/README.md) | `6844d91b774a998a9e8d037b60c541e8ddb61497818231b20408c7a2a240c8c0` |
| E | [Places Widgets  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/reference/places-widget) | `abbf03e1e825db9a5ef68fced05135695b657a97e6cfafbe2e4d49835d8e609a` |
| F | [Basic Place Autocomplete Element  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/places-ui-kit/basic-autocomplete) | `0d2fa79b4232822625952f1a897109af605de29591ee5eb8af3dab7acae85a33` |
| F | [Get Started with Places UI Kit  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/places-ui-kit/get-started) | `369eb94a94ead0b10ec12958cf1cb229057ff9fc4c016331f1dfec4d3ebee79a` |
| F | [Places UI Kit  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/places-ui-kit/overview) | `4b014b22a22c3deb2a1855935a1e18742c2e7ea49d50882c6c1fe99de02e7276` |
| F | [terra-draw/LICENSE at main · JamesLMilner/terra-draw · GitHub](https://github.com/JamesLMilner/terra-draw/blob/main/LICENSE) | `e2377b429e9243caaa882f627dfa9576cca2b0598e535b6af70fad04e4aac843` |
| G | [Maps JavaScript API Release Notes  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/releases) | `f47d77d24687c3dee288c67d926e018694ad3c217765a80287442641aa2dca0b` |
| G | [Versioning  /  Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/versions) | `1b46ff4b9629e050b0b3d3705c6e258aeb0663c209d24dd191ba3675ab4de214` |
| G | [Load the Maps JavaScript API  /  Google for Developers](https://developers.google.com/maps/documentation/javascript/load-maps-js-api) | `2fc917c5f668416e9ab4ad4475e43c473fecaecff997d9a1485f4e2f9b45a632` |
