# 图像标定（image calibration）：设计定稿与实现边界

2026-11-11。本票实现工作台图像标定的第一段：**圆点定尺 + 独立第二校核 + 在图上描出屋面轮廓**，把结果落到既有 `geometry.sources[]` 的来源精度信息上。它不是完整工程复核，也不是 provider 采集或透视矫正。

## 为什么这样设计（复刻依据）

`docs/specs/548-interactive-design.md:16` 把 source 空间精度与标定记为"明确未记录"，`:66` 把 import/calibration 列为 active goal 的义务；`docs/specs/548-geographic-intake.md:6,49` 明确规定"image calibration … need their respective actual operations; they cannot masquerade as this format"；`docs/specs/548-design-geometry.md:25` 要求 source 记录保留 calibration 且与 derivation 分开；`docs/specs/548-roof-import-workflow.md:4` 与 `548-map-display.md:62` 同样把它列为未完成项。

既有成熟模式写在 `docs/research/2026-10-23-map-workbench-integration/IMPLEMENTATION.md:91`，本票直接复刻，不新造：

1. 保留原件 hash 与像素尺寸；
2. 用户选两个点并给出实际长度，记录 `m_per_pixel = L / d_pixel`；
3. 声明已知方向与像素 Y 轴向；
4. **另用第二条独立尺寸检查比例**；
5. 两点量尺只确定均匀尺度，**不能校正透视照片或非均匀缩放**——这类来源只作参考；
6. 斜面图、水平总平图、透视照片必须区分；图纸斜长不再重复换算坡度。

同一 dossier 的 E1 竞品记录（`docs/research/2026-10-22-roof-europe-precedents/REPORT.md:93`）指出 OpenSolar Manual mode 与 Easy PV Quick Roof 的既有做法就是"上传图纸 → 两点实测长度校准 → 每面坡度与障碍"。本票的交互流与之同构：上传 → 两点定尺 → 描画。没有先例的部分（结构化字段名、参考态阈值由用户声明）按上面 dossier 的 §4 建议列写明理由，不另立假设。

## 入口与交互

入口在屋顶步骤（Roof design）内，与既有 `GeometryIntake`（GeoJSON 导入）并列的第二个按钮 **Calibrate a roof image / Dachbild kalibrieren**。三步：

| 步骤 | 内容 |
| --- | --- |
| 01 Image and roof | 选择 PNG/JPEG/WebP（≤8 MB）；浏览器解码后显示真实像素尺寸；选绘图类型（水平总平 / 屋面斜面视图 / 透视照片）；选目标屋面（新建，或替换既有屋面的轮廓） |
| 02 Scale | 在图上点出比例尺两点 → 真实长度；可选第二独立校核两点 → 真实长度 + 用户声明的允许相对差；屋面 U 方向相对图像右缘的旋转角；屋面坡度。实时显示 `m/pixel`、测量状态与校核偏差 |
| 03 Outline | 在同一张已标定的图上点出屋面轮廓（≥3 点）；显示点数与屋面平面面积；填写来源与权限声明后加入当前设计 |

交互约定：
- 图像**不上传**；本段只把标定记录写进项目（原件身份靠 hash，未提供原件时为 null 并在文案中说明）。
- 每个测量步骤都在同一画布上留痕（比例点 / 校核点 / 轮廓点可分别清除或撤销最后一点）。
- 三步骤控件始终挂载（`hidden` 切换），回到前一步改字段后仍能重新校验，与 GeoJSON 导入的面板同形。
- 点选按 SVG `xMidYMid meet` 规则去掉 letterbox 再换算成图像像素；图外点击不落点。
- 前景：无法量尺时**不静默给零**——透视照片与校核失败一律显示"Reference only / Nur als Referenz"，且 `metricRing` 返回 null。

## 数据落点

标定属于 source 的精度信息，沿用 `GeometrySource`，不新建平行结构：

```text
geometry.sources[].calibration = {            # 可选；缺失＝未记录，不是零误差
  schema_version: 1
  method: "two_point_uniform_scale_v1"
  view: horizontal_plan | roof_slope_elevation | perspective_photo
  image: { media_type, pixel_width, pixel_height }
  control_points: { first: [x,y], second: [x,y] }        # 图像像素
  known_length_m, m_per_pixel
  rotation_deg                                            # 图像右缘 → 屋面 U 方向
  check: { points, declared_length_m, residual_ratio, status } | null
  check_tolerance_ratio                                   # 用户声明，不是测绘规则
  applied_pitch_deg                                       # 仅水平总平有；记录一次余弦换算
  measurement_status: usable_uniform_scale | reference_only
  note
}
```

`geometry.sources[].calibration_note` 仍是人类可读摘要（既有字段，`RoofForm`/`SourceForm`/`MapSourceDetails` 已消费），两者并存：结构化记录供校验，摘要供阅读。

**兼容处理**：`calibration` 在 Pydantic 与浏览器 schema 中都是可选字段，且不在 `required` 里；`geometry.schema.json` 的差异为纯新增 188 行，未改动任何既有 `$defs` 引用。旧修订（无该字段）读取后 `calibration is None`，语义与之前完全一致。引擎侧拒绝自相矛盾的记录：比例不等于 `L/d`、点在图外、残差与状态不一致、状态与证据不一致、非水平总平却带 `applied_pitch_deg` 等。

**完整输入写入器契约**：标定随 `inputs.geometry` 保存，旧版完整输入写入器若重写 `geometry` 会把记录抹掉。按既有机制新增 `geometry_image_calibration_v1`（`project_input_contracts.py` 的 `required_contracts` 检测 `sources[].calibration != null`），并同时更新 `apps/planner/src/contracts/project-input-contracts.json` 与 `plugins/linker-tools/project-input-contracts.json`（两份逐字节一致）。

## 明确不做（本段边界）

- 不上传/不保留图像原件；`reference_sha256` 保持 null（既有导入路径仍可绑定 GeoJSON 原件）。原件 CAS 与图像 intake 属于独立操作。
- 不做透视矫正、镜头畸变、非均匀缩放的拟合；这类图只能记比例并标为参考。
- 不做自动识别屋面边线、不做机场/卫星影像采集、不做 provider 许可。
- 标定不改变工程的 1e-9 m 数值精度策略，也不产生任何验收或结构/消防结论。
- 描出的轮廓进入既有的 `RoofFace.boundary_uv`；洞口仍在屋面属性里编辑（本段不采集洞口点）。

## 验收要求（本票已执行）

- planner 单测：`src/domain/imageCalibration.test.ts` 11 项（比例、重合点、第二校核、透视照片、缺校核、Y 向下与一次坡度换算、旋转、自相矛盾记录、水平总平必须有坡度、schema 可选与旧修订兼容）。
- planner DOM 测试：`tests/image-calibration.test.mjs` 3 项（真实三步提交成一条历史、透视照片 reference-only、比例输入不完整时不写历史）。
- 引擎测试：`services/engine/tests/planning/test_image_calibration.py` 14 项（含浏览器契约逐字节一致、写入器契约必需性）。
- e2e：`tests/e2e/specs/planner-image-calibration.spec.ts`，EN/DE × 1440/390 **4/4 通过**（review 实例，真实引擎/网关/项目修订）：上传 1200×800 图纸 → 两点定尺 600 px = 12 m → 面板显示 `0.02 m per pixel` 与 `Usable uniform scale` → 480 px 独立校核 9.6 m（0 %）→ 描 4 点轮廓、面积 144 m² → 加入设计 → 保存 → 重开读回屋面与来源声明（德语断言同样跑 `0,05` 的小数逗号）。
- planner DOM 测试现有 4 项（新增德语小数默认值一项）。
- 德语：52 条新词条写入 `linker-tools-de_DE_formal.po`（Sie 体），`just i18n-tools` 重新生成 `.mo` 与 5 个 script JSON；`i18n-coverage`、`german-copy`、`commerce-terms`、`internal-home-urls` 全绿。

## e2e 实走发现并已修复的两个真实缺陷

1. **德语小数默认值**：容差字段默认写成字面量 `0.01`。德语 `parseDecimal` 把点视为千分位，整步被拒（`Prüfstrecke (2 von 2)` 但无法继续）。改为 `formatDecimal(0.01, locale)`，德文显示 `0,01`；并加 DOM 回归测试（`the declared tolerance default follows the page language`）。这是 e2e 存在的直接价值，不是测试瑕疵。
2. **390 宽度点击偏移**：绝对坐标 `page.mouse.click` 在窄屏与德语长文案下落到别处，标记不登记。改为 Playwright 元素相对 `click({position})` + `scrollIntoViewIfNeeded`，letterbox 换算保留。

两处都不是产品代码的回归；它们是「实走才暴露」的布局与本地化耦合。第二个在修之前，德语 1440 也会失败（`Prüfstrecke (0 von 2)`），说明它不是窄屏特例。

## 权限与文案

新文案全部为用户可见（按钮、步骤、字段、帮助句、错误句）。英文初稿在上表；德文由 `linker-tools-de_DE_formal.po` 独立撰写（Sie 体），不是逐字翻译；`commerce-terms` 与 `german-copy` 均通过，没有引入任何店铺/购物车/订单类词汇。
