# 统一项目工作台的 3D 栈：官方证据与接入边界

研究日期：2026-10-23（北京时间）。作者：Codex 后台研究代理。范围：外部库与本站接入设计；未读 Aladdin 源码 ZIP，未写业务代码、安装依赖、修改设置、提交或部署。本轮资料均先经 Apify 取得；Context7 仅补核官方仓库文档。

## 1. 本轮结论与用户最新裁定

**3D 是正式工作台能力，不能停在截图或展示模型。当前生产候选为隔离的 React 19 工具应用，使用稳定版 React Three Fiber 9、Drei 10、Three.js；WordPress 现有 React 18 继续承载站点。** 3D 中编辑的屋面、阵列与障碍物，必须是同一项目修订中的对象，能在 2D 中继续编辑、保存并重新打开。此为用户本轮新增要求及根代理转达的实施方向，不是已上线声明。

研究开始时按现有站点约束比较过“原生 Three + wp.element”和“Fiber 8 + Drei 9”。用户随后明确：先正确使用，再采用当前先进技术，允许调整架构，不必因站点 React 18 永久停留旧库。**该当期授权支持独立 React 19 runtime；不要求升级或改写全站 wp.element。** 根代理据此选择 `apps/planner` 独立包、Vite 构建、WordPress 按需 enqueue module 的专用入口。这个工具局部架构选择有当期用户授权，改变此前“工具也统一使用 WP React / wp-scripts”的约束；原站其他包保留原机制。旧兼容组合保留在下文作事实对照，已不作为最终默认推荐。

现代化的判断依据是可用能力、明确数据与生命周期边界及实跑结果。稳定版 R3F 9 已有官方 WebGPU 初始化路径，无须采用 Fiber 10 alpha 才能做该验证。[官方 Canvas 文档](https://r3f.docs.pmnd.rs/api/canvas)、[官方版本配对说明](https://r3f.docs.pmnd.rs/getting-started/introduction)。

## 2. 当前精确版本与 peer 交集

下表为本次从包发布者的 npm registry 元数据实际取回的 `latest`，不是猜测或只看 README。取回时间为 2026-10-22 18:27–18:36 UTC，即北京时间 2026-10-23 02:27–02:36。安装时使用精确版本及锁文件，不能在客户浏览器中动态追 `latest`。原件长度、SHA-256、发布 tarball integrity、Apify 存储定位和字段投影在 [package-primary-metadata.json](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/research/2026-10-23-3d-workspace/package-primary-metadata.json)。

| 包 | 本次取回版本 | 官方元数据中的关键约束 | 本轮结论 |
| --- | --- | --- | --- |
| `react` | **19.3.1** | MIT | 工具私有模块依赖；不写 `window.React` |
| `react-dom` | **19.3.1** | peer `react: ^19.3.1`，MIT | 与工具 React 精确对齐；使用自己的 `createRoot` |
| `@react-three/fiber` | **9.8.2** | `react`、`react-dom`: `>=19 <19.4`；`three >=0.156`；MIT | React/DOM 19.3.1 满足范围 |
| `@react-three/drei` | **10.7.9** | `react ^19`、`react-dom ^19`、Fiber `^9.0.0`、Three `>=0.159`；MIT | 与上述组合满足直接 peer 关系 |
| `three` | **0.186.1** | MIT；ESM；exports 包含 `./addons/*`、`./webgpu`；无 React peer | 稳定发布的渲染与场景基础 |
| `@types/three` | **0.186.0** | MIT；`typeScriptVersion: 5.6` | 与 Three 同 r186 系列，需实际编译所有用到的 API |
| `@types/react` | **19.3.0** | MIT；`typeScriptVersion: 5.6` | 工具单独使用；不把全站 React 18 类型全局替换 |
| `@types/react-dom` | **19.3.0** | peer `@types/react ^19.3.0`；MIT；最低 TS 5.6 | 与工具 React 类型对齐 |
| `vite` | **8.3.5** | MIT；Node `^20.19.0 \|\| >=22.12.0` | `apps/planner` 独立静态模块的构建候选 |
| `@vitejs/plugin-react` | **6.1.2** | MIT；peer Vite `^8.0.0`；Node `^20.19.0 \|\| >=22.12.0` | 满足 Vite 8.3.5；不要求顺便启用 React Compiler |

一手元数据：[React](https://registry.npmjs.org/react/latest)、[ReactDOM](https://registry.npmjs.org/react-dom/latest)、[Fiber](https://registry.npmjs.org/@react-three%2ffiber/latest)、[Drei](https://registry.npmjs.org/@react-three%2fdrei/latest)、[Three](https://registry.npmjs.org/three/latest)、[Three 类型](https://registry.npmjs.org/@types%2fthree/latest)、[React 类型](https://registry.npmjs.org/@types%2freact/latest)、[ReactDOM 类型](https://registry.npmjs.org/@types%2freact-dom/latest)、[Vite](https://registry.npmjs.org/vite/latest)、[Vite React 插件](https://registry.npmjs.org/@vitejs%2fplugin-react/latest)。

这些字段证明直接依赖范围相交，**没有证明整套依赖已在本站 TypeScript 6.0.3、独立 Vite 包、所有浏览器与所有 Drei 组件中验证**。类型包声明最低 TS 5.6，不等于已实测 TS 6；构建、锁定的传递依赖和真实运行仍是下文的 POC 门。Drei 提供很多可选能力，不能因安装了包便把视频、物理、动画等无关能力全部导入。

本机 `node --version` 实读为 **v24.22.0**，满足 Vite 和 plugin-react 的声明范围；尚未因此证明构建成功。plugin-react 的 React Compiler、OXC transform、Babel 插件 peers 在发布元数据中均为 optional。本轮为 3D 引入工具链，不把这些可选编译方案一并作为依赖前提。Vite 的后端接入文档给出生产 build manifest、带 hash 的模块入口及依赖导入关系，适合由 WP 专用入口消费；开发服务器与 HMR 不能当生产接入方式。[Vite 环境要求](https://vite.dev/guide/)、[官方 backend integration](https://vite.dev/guide/backend-integration.html)。

历史兼容核查：Fiber **8.18.0** 的 React/DOM peer 为 `>=18 <19`，Drei **9.122.0** 为 React/DOM `^18`、Fiber `^8`，所以能作为站点 React 18 的备选；这不代表它们获得长期维护保证，也不证明任意未来 Three 版本兼容。[Fiber 8 原始元数据](https://registry.npmjs.org/@react-three%2ffiber/8.18.0)、[Drei 9 原始元数据](https://registry.npmjs.org/@react-three%2fdrei/9.122.0)。官方页面明确 Fiber 8 对 React 18、Fiber 9 对 React 19，并把 Fiber 10 标为 alpha。[官方说明](https://r3f.docs.pmnd.rs/getting-started/introduction)。

## 3. 渲染后端如何选择与验证

Three 当前官方手册说明：`WebGLRenderer` 继续维护，仍推荐给纯 WebGL 2 应用；主要新功能开发方向已转向 `WebGPURenderer`。后者优先 WebGPU，在设备或浏览器不支持 WebGPU 时可自动改用 **WebGL 2 backend**，并支持 `forceWebGL: true` 强制测试。[Three 官方手册](https://threejs.org/manual/pages/webgpurenderer.html)、[WebGPURenderer 参数](https://threejs.org/docs/pages/WebGPURenderer.html)。

R3F 当前官方 Canvas 文档给出异步 `gl` 工厂：从 `three/webgpu` 构建 `WebGPURenderer`，`await renderer.init()` 后返回 renderer，并通过相应的元素扩展使用 node material。因此 **React 19 + Fiber 9 可以实际验证 WebGPU-first**，不必先升级到 Fiber 10 alpha。[官方 Canvas 示例](https://r3f.docs.pmnd.rs/api/canvas)。

这条 WebGL 2 fallback 仍属于 `WebGPURenderer` 的后端选择，**不等价于自动改回另一套 `WebGLRenderer` 应用**。官方仍把新 renderer 标为 experimental，并列出真实差异：旧 `ShaderMaterial` / `RawShaderMaterial` / `onBeforeCompile` 定制和旧 `EffectComposer` 不能照搬，需适配 node material、TSL 及新后处理。某些场景可能功能缺失或 WebGLRenderer 更快。[官方迁移说明](https://threejs.org/manual/pages/webgpurenderer.html)。

本轮推荐的实际路线：在同一领域场景上验证 WebGPU-first、强制 WebGL 2 backend，以及必要时单独的稳定 WebGLRenderer 适配器；公开路径选择由真实材质、控件、阴影、拾取、设备恢复和性能结果决定。实验标签是需要核实的风险，不是拒绝现代技术的理由；`init()` 或设备失败也不能未经验证就被描述成必定自动恢复。若硬件连 WebGL 2 都无法使用，要回到同一项目的 2D 编辑器；这条产品恢复路径须由我们实现，renderer 不会代做。

## 4. 成熟能力对应什么，哪些仍由领域内核承担

| 客户要完成的操作 | 复用的成熟模块 | 应由本站负责的语义与验证 |
| --- | --- | --- |
| 旋转、平移、缩放观察屋顶；正交俯视与透视切换 | Three cameras；Drei `OrbitControls`，底层官方 OrbitControls | 项目地点、北向、真实比例与当前工作区；观察动作不改工程修订 |
| 选中屋面、阵列、单块组件或障碍物 | R3F pointer events + Three `Raycaster`；实例命中 `instanceId` | 将渲染命中映射回稳定领域 ID；透明对象/遮挡事件策略和触控选择 |
| 移动或旋转阵列，改变障碍物位置和高度 | Drei `TransformControls`，底层官方同名 addon，支持空间选择与吸附 | 坡面约束、尺寸单位、禁止穿屋面、禁布区、输入有效性、命令提交与失败恢复 |
| 显示坡顶、平顶、开孔与实体障碍 | `BufferGeometry`、`ShapeUtils.triangulateShape`、`ExtrudeGeometry` | 屋面平面、孔洞、相邻面与高度的有效几何；这些绘制 API 不是工程 CAD 或屋面事实来源 |
| 大量相同组件、重复支架或阵列 | `InstancedMesh`；需要时选用 Drei 对应封装 | 每个实例稳定 ID、排除状态和精确位置；变更后更新矩阵、bounding volume 和选择索引 |
| 撤销、重做、编辑后重算 | 参考 Three 官方 editor `History` 的 command/undo/redo 机制 | 我们的类型化领域命令、批量拖动合并、版本冲突、不可变修订、旧结果失效 |
| 保存、重开、跨 2D/3D 回看 | R3F 只订阅共享项目状态；React DOM 属性表和 Canvas 同步 | 已有项目/资产/修订/任务权威；不把 Three 场景 JSON 或 GPU 缓存当工程真相 |
| 导入客户模型 | 官方 `GLTFLoader`，只按实际需要加解码器 | 私有原件、许可与来源、尺寸校准、局部坐标变换、可计算语义和资源限制 |

一手依据：[OrbitControls](https://threejs.org/docs/pages/OrbitControls.html)、[Drei controls](https://drei.docs.pmnd.rs/controls/introduction)、[Drei TransformControls](https://drei.docs.pmnd.rs/gizmos/transform-controls)、[官方 TransformControls](https://threejs.org/docs/pages/TransformControls.html)、[Raycaster](https://threejs.org/docs/pages/Raycaster.html)、[R3F events](https://r3f.docs.pmnd.rs/api/events)、[InstancedMesh](https://threejs.org/docs/pages/InstancedMesh.html)、[BufferGeometry](https://threejs.org/docs/pages/BufferGeometry.html)、[ShapeUtils](https://threejs.org/docs/pages/ShapeUtils.html)、[ExtrudeGeometry](https://threejs.org/docs/pages/ExtrudeGeometry.html)、[Three editor History 原件](https://raw.githubusercontent.com/mrdoob/three.js/dev/editor/js/History.js)、[GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html)。History 仅为成熟模式证据，不建议搬入整个官方编辑器或 Aladdin app。

R3F 的 `useThree`、`useFrame` 只应在 Canvas 子树中使用；前者订阅 renderer/camera/尺寸等，后者参与逐帧工作。可计算项目的提交不应每帧产生持久修订；拖动使用临时预览，结束时提交一个领域命令，再使依赖该输入的结果过期。此为基于官方 hooks 生命周期和现有不可变修订架构的设计推导，不是库已经实现的项目系统。[官方 hooks](https://r3f.docs.pmnd.rs/api/hooks)、[项目权威决定](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/adr/0001-unified-project-authority.md)。

选择也不是装上 events 即完成：官方说明 R3F 事件会递送到多个相交对象，`stopPropagation()` 会阻止后方对象；pointer capture 与 DOM 行为存在差异。Three 对 mesh 的 raycast 默认不命中背面，必要时用明确的双面策略；共享边可能出现重合命中，应按领域对象去重。Drei 会帮助在拖 gizmo 时暂时关闭默认相机控件，但要实测“拖对象”和“转视角”不会冲突。[官方事件](https://r3f.docs.pmnd.rs/api/events)、[Raycaster 限制](https://threejs.org/docs/pages/Raycaster.html)、[Drei 联动说明](https://drei.docs.pmnd.rs/gizmos/transform-controls)。

## 5. 地图、米制场景与 2D/3D 双向编辑

官方事实有三条，不能混写：

1. Three 的 `Object3D.DEFAULT_UP` 默认是 `(0,1,0)`，不是 Z-up。原件本次捕获第 1694 行明确赋值；相关 SHA 和行摘录在 provenance 中。[官方源码](https://raw.githubusercontent.com/mrdoob/three.js/dev/src/core/Object3D.js)。
2. Three 的物理灯光等假定一世界单位为一米；角度 API 需区分相机视角的度与多数旋转的弧度。[官方单位说明](https://threejs.org/manual/pages/debugging-javascript.html)。glTF 2.0 §3.4 明确右手系、+Y 向上、线性距离为米、角度为弧度。[Khronos 规范](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units)。
3. MapLibre `MercatorCoordinate` 是投影世界宽度为一单位、原点在西北角的坐标，不是本地工程米；官方 `meterInMercatorCoordinateUnits()` 用于局部比例换算。[官方 MapLibre 坐标说明](https://maplibre.org/maplibre-gl-js/docs/API/classes/MercatorCoordinate/)。

因此建议领域数据使用有明确地理原点、源 CRS、垂直基准和转换版本的本地米制 ENU：`(East, North, Up)`。渲染适配器显式变换为 Three 的 `(E, U, -N)`，保持右手性；逆变换必须用于从画布写回领域命令。**这是本站设计选择，不冒充 Three 推荐 Z-up。** 不全局修改 `Object3D.DEFAULT_UP`，不把国家投影坐标的巨大绝对值、经纬度或 MapLibre 世界单位直接塞入组件尺寸。

客户 glTF 已是 Y-up，导入需记录其朝向、比例和相对于项目原点的变换，经过校准转换进入 ENU；不能再把同一变换重复应用两次。若数据源没有可靠屋高或屋面，只能保存为已知精度的手工或参考几何，不能因 3D 看起来真实就提高来源置信度。

2D 地图与 3D Canvas 只是同一项目修订的两个编辑视图：稳定的 `roofPlaneId`、`arrayId`、`obstacleId` 和组件实例 ID 贯穿两边；屋面坡度/方位/尺寸、阵列行距/离地高度、障碍物轮廓/高度在一处存储与验证。3D 拖动后 2D 位置及属性表更新，2D 修改后 3D 重建相应对象，保存重开后仍一致。渲染选择、相机姿态等 UI 状态与工程修订分开；正式计算冻结原始项目与资产版本。

住宅坡顶需要真实分面的三维几何、屋面内局部基及凸起/天窗等障碍；商业平顶需要阵列倾角、朝向、排距、高度、通道和排间遮挡。二者是同一几何模型的不同参数与约束，不应再按“commercial”切断屋顶能力。具体结构、消防、风雪与电气判断由对应有依据的模型给出，Three 的网格并不提供这些结论。

## 6. 必须区分的四层结果

| 层 | 可证明的输出 | 不得由这一层代替的结论 |
| --- | --- | --- |
| 3D 展示与编辑 | 当前修订里的位置、尺寸、材质、选择、几何编辑反馈 | 建筑资料本身精确、屋顶承重合格 |
| 场景几何与遮挡可视化 | 按给定太阳方向展示阴影；或对固定几何做可追溯相交测试 | 已计算年度组件电损失 |
| 几何遮挡/辐照模型 | 有方法、太阳位置、采样/收敛、直散射处理、地平线、来源和误差证据的时序输入 | 旁路二极管、组串失配和 MPPT 后的电气损失 |
| 电气与能流模型 | 使用已验证拓扑、设备能力、时序及适用条件的可复算结果 | 由像素阴影或 Three 材质亮度直接得到的设备放行 |

Three 默认 shadow map 的机制是从投影光源视角再渲染，受阴影相机覆盖、纹理分辨率和偏移等显示配置影响；增加投影光源还会增加渲染工作。[官方 shadows 手册](https://threejs.org/manual/pages/shadows.html)。因此浏览器里的阴影不是正式计算数据。Raycaster 可以成为几何验证或显示的构件，但不会自动给出漫射遮挡、旁路二极管、组串失配或年度损失模型。上述分层是本研究对工程责任的推导，未宣称已有完整算法。

## 7. 用户模型导入与许可的最低合同

Three 与本次候选包的 MIT 许可允许复用库；Three 原始 LICENSE 同时要求保留相应许可与版权声明。**库许可不授予任意建筑模型、航拍、纹理和设备模型的使用权。** Khronos 自己的样例库也逐模型标注 credits/license，并要求查看各模型 README。[Three LICENSE](https://raw.githubusercontent.com/mrdoob/three.js/dev/LICENSE)、[Khronos 样例许可说明](https://github.com/KhronosGroup/glTF-Sample-Assets)。

因此用户模型作为私有项目资产保存原件 hash、来源、权利说明/依据、上传身份与转换记录；系统不能从缺省的 copyright 或“glTF 格式”推导许可。自动屋面/地图数据继续携带各自来源与归属。glTF/GLB 可携带外部 buffer/image URI，**GLB 也不保证完全自包含**；进口路径要明确可访问资源与限制，不能让客户模型随意从网络补取依赖。[glTF 官方文件结构](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#glb-file-format-specification-structure)。

首批导入以能实际验证的 glTF/GLB 为候选，不顺带承诺 IFC、CityJSON 或任意 CAD 均已可编辑。导入前后核尺寸、轴向、原点、bounding volume、纹理与几何资源预算；原始装饰 mesh 和可用于工程计算的屋面/障碍语义分开。缺工程语义时，允许作为参考并人工标定，不能默认为完成屋顶建模。

## 8. React 19 与站点 React 18 的隔离验收

本站实读证据：本机 [WP react.js](/Users/chesterjohn/de-linker-local/p548/wordpress/wp-includes/js/dist/vendor/react.js:16) 为 **18.3.1**；[linker-tools package](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/plugins/linker-tools/package.json:26) 同样锁 React/DOM 18.3.1、MapLibre 5.24.0、Terra Draw 1.35.0；[webpack 配置](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/plugins/linker-tools/webpack.config.js:1) 明确 React、JSX runtime、WordPress 包由 WP 提供。候选 3D 依赖在这次核查时尚不在该 package 中。

**不能沿用该默认 external 规则后，以为工具已经运行 React 19。** 新工具 runtime 在 `apps/planner` 有单独可审计的依赖与 Vite 构建边界，将它的 React、ReactDOM、JSX runtime 和 R3F 保持同一私有模块图；现有站点包继续 WP React external 与 wp-scripts 行为。WordPress 按需注册专用 module 入口，实际产物、lazy chunks 和缓存路径均需验证。WindPress 仍是唯一 Tailwind/CSS 生成管线；采用 Vite 不等于再建一套 Tailwind，也不需要购买插件。

React 官方允许在部分使用 React 的页面上给不同 DOM 区域建立 root，并提供 `root.unmount()` 清理。[createRoot 官方文档](https://react.dev/reference/react-dom/client/createRoot)。**该文档不是“任意混版本组件可交叉使用”的保证**；下面是本站的必要隔离设计及验证门：

- 工具 root 只使用工具 React/DOM 19；不能把使用 wp.element 18 hooks 的组件、React context、React 元素或 portals 跨 runtime 传进去。跨界面只交换可验证的项目数据、DOM 事件或服务接口。
- 工具代码不赋值/替换 `window.React`、`window.ReactDOM` 或 `wp.element`。加载前后核对象身份和版本，旧 Genie、账户、商务页仍实际可操作；不能只用 `npm ls` 代替此证据。
- 正常站点页面未进入工具时不预先下载三维大块；进入工具后按需加载，离开时 unmount 清理 canvas、controls、监听器、帧循环及自建资源。严格模式下重复挂载与退出仍可靠。
- 工具的新源码进入现有 WindPress 扫描面；页头、Journal 风格、手机属性面板和 EN/DE 文案继续既有站点合同。
- 本轮未在研究分支执行这套集成；根代理将执行 `apps/planner` 的实际构建与浏览器验证。私有 HTTP/身份/所有权边界属于同一交付范围，不能为了先展示 3D 绕过或取消。

## 9. 性能、低端设备和失去 GPU 的恢复

官方 R3F 建议静止场景按需渲染、复用 geometry/material、用实例减少 draw calls；Drei 控件可配合需求渲染触发刷新。直接修改对象的临时预览不会自动被 React 侦测，按需渲染下应正确触发 `invalidate()`，防止领域状态与画面不同步。[官方性能说明](https://r3f.docs.pmnd.rs/advanced/scaling-performance)。原生 Three 也有按需渲染模式。[官方按需渲染](https://threejs.org/manual/pages/rendering-on-demand.html)。应按实测调像素比、投影阴影和细节，不把“GPU 加速”当成手机性能保证。

实例化不是免费的空间索引：官方 API 要求变更 instance matrix 后更新相关数据与 bounding volume；Raycaster 返回实例 ID。大量对象的拾取、框选和几何运算仍需测量，必要时再引入空间加速库或 worker，**本轮不先把另一套物理引擎、状态库或地图引擎作为必需依赖**。[InstancedMesh](https://threejs.org/docs/pages/InstancedMesh.html)、[Raycaster](https://threejs.org/docs/pages/Raycaster.html)。

Three 要求释放几何、材质、纹理等资源，单纯从场景移除对象不等于释放 GPU 资源。[官方 cleanup](https://threejs.org/manual/pages/cleanup.html)。WebGLRenderer 官方源码实际处理 `webglcontextlost` / `webglcontextrestored`，lost 时停止正常渲染、restore 时重建内部 GL 状态，dispose 时解除相应监听器；原件 SHA 与行摘录在 provenance。公开 API 也提供 `forceContextLoss()` / `forceContextRestore()` 进行模拟，依赖 `WEBGL_lose_context` 扩展。[官方源码](https://raw.githubusercontent.com/mrdoob/three.js/dev/src/renderers/WebGLRenderer.js)、[官方 API](https://threejs.org/docs/pages/WebGLRenderer.html)。这些机制不等于项目自动保存或输入自动恢复；WebGPU 设备丢失也不能拿 WebGL 的事件证明。

产品恢复要求：GPU 失败时保留规范化项目和未提交编辑的明确状态，显示原因并允许切换同一项目的 2D/属性输入；不能只显示不可操作的 Canvas fallback 文案。重建三维视图后从项目数据恢复，而不是从丢失的 GPU 对象恢复。手机须能用数值表完成精确编辑、选择/撤销、保存，不能只提供拖拽 gizmo。

## 10. 从库表进入真正 POC 的通过门

以下均为待实证门，不是本研究已经通过的验收：

1. **原生包构建与运行隔离**：锁定本表组合，用实际 `apps/planner` Vite/TypeScript 6.0.3 构建；在带线上快照的 WP 实例以专用 module 入口按需加载，读取真实工具 runtime 版本，并验证站点 wp.element 18 未改变。审构建 manifest、chunk URL、缓存和 console，运行既有站点关键入口；现有 WP 包仍按原 wp-scripts 管线构建。
2. **同项目双向编辑**：一个住宅坡顶含开孔和障碍物、一个商业平顶含倾斜阵列与通道；3D 修改 → 2D/属性更新 → undo/redo → 保存到真实私有项目 → 重开。反向从 2D 修改后也一致；验证尺度、北向、稳定 ID、修订 hash 和旧结果 stale。
3. **现代渲染的真实后端矩阵**：支持 WebGPU 的设备实际读回所用后端；强制 WebGL 2 backend；无 WebGPU 的环境；初始化失败；必要时独立 WebGLRenderer。控件、选取、实例、材质、导入与阴影都用同一领域夹具验证；不能只测一个旋转立方体。
4. **单位与导入夹具**：已知米制模型、Y-up glTF、ENU 项目、不同纬度地图、不同高度基准来源；检查变换往返和尺寸/朝向不漂移。模型含外部资源、缺许可或资源过大时给可恢复结果，原项目保留。
5. **性能与恢复**：在指定桌面和低端手机记录组件数量、draw calls、首载、帧时间、拾取延迟、内存及交互结果，容量承诺由测量决定。模拟 context loss / 恢复、导航反复挂载、断网保存、冲突与服务错误，仍可操作同一项目的 2D/属性路径。
6. **计算与显示分离**：同一修订改变阴影贴图分辨率/renderer 后，正式能流输入不能跟着像素变化；遮挡模型如参与发电，必须另有数值夹具、可追溯时序输出和电气语义验证。保存和报告仍指向相同冻结输入与模型版本。

## 11. 取证说明与尚未验证的事项

官方页面、发布元数据与必要源代码均经 Apify `website-content-crawler`，每次 memory 1024、maxConcurrency 2；没有输出或落盘 APIFY_TOKEN。旧 `/manual/en/` 页面只返回重定向提示，已改抓 `/manual/pages/` 正文。Cheerio Scraper 曾因账户未批准 full-permission 拒绝启动；没有批准权限或更改设置，改用已获准 Content Crawler 的 `saveContentTypes` 成功保存 JSON/纯文本，再从 Apify 存储实际回读、哈希。不能用 actor 的 SUCCEEDED 标签代替正文/原件成功：文件下载在 actor 汇总中显示 failed 计数，但本报告引用的文件均有 HTTP 200、可回读原件及 hash。

主要 runs/datasets：首轮官方文档 `dgrxIiyrB0DIHohFh / H7qcB9bnHZACEndYz`；详情 `viuhzT4a6PZP2iXuK / MFXDaDdMLxD8LoMRF`；包元数据 `vn4v5qRLWoDalRScA / m0atPGqWMMH4Ea4GN`；生命周期原件 `ur1uYSEUQgqIqnGCq / P31hr0F5xMRUGCSV6`；现代 runtime `SYn9d2SbP4XkjDh3e / S2jK4c9C0ozxjyoK3`；Vite 构建 `hiwEdQk5K6prVAsa4 / tjJQ7BFBnbu6qzG36`。输入、状态、来源 URL、取回时间及 hash 见 [PRIMARY-PROVENANCE.json](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/research/2026-10-23-3d-workspace/PRIMARY-PROVENANCE.json)；存储地址均去掉临时签名参数。该小文件保存所用正文摘录、完整抓取文本 hash 和 Apify 定位；大原文留在对应 Apify dataset/KV，未把整份 glTF 规范镜像入库。

Context7 补核使用 `/mrdoob/three.js` 与 `/pmndrs/react-three-fiber`，仅回看其官方仓库的 renderer、Canvas、hooks、性能和安装文档，未用它绕开 Apify 取得外部原件。

仍未验证：本表组合的实际安装/构建、浏览器/WebGPU/低端设备矩阵、完整三维编辑保存重开、工程遮挡与电损模型、真实用户模型导入。Aladdin 的实际库版本、轴向与操作研究由根代理独立负责；本文件不重复或假称完成那部分。本研究是生产选型证据与 POC 合同，正式集成结果需另附真实运行证据。
