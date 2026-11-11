# #548 屋顶导入与辐照/遮挡域 · 当前状态复验（2026-11-11）

执行者：M 线。触发：`548-domain-gap-matrix.md` 第 2 行判定"需补验"，
理由是"citygml/lod2/packing 无验收；遮挡链仅单测；导入域验收早于 11-05"。

**结论：该行三条理由中两条不成立，一条成立但根因不是它写的那样。**

| 审计断言 | 复验结果 |
|---|---|
| citygml/lod2/packing 无验收 | **不成立。**真缺口另有其处（下详） |
| 遮挡链仅单测 | **成立，但这是规格边界**：两条链都没有客户入口 |
| 导入域验收早于 11-05 | **成立**，且缺的不是时间而是**取证维度** |

---

## 1. 规格边界：CityGML / LoD2 从来没有被承诺为导入能力

`docs/specs/548-roof-import-workflow.md` 与 `548-geographic-intake.md`
全文不含 citygml / lod2 / LoD 任何字样。两份规格承诺的唯一导入格式是

```
format: "geojson_wgs84_horizontal_v1"
```

并且 `548-geographic-intake.md` 明确写了"Known-height 3D geometry, another CRS,
image calibration and provider acquisition need their respective actual
operations; they cannot masquerade as this format."

LoD2 属于**另一条产品链**：`roof/service.py` 的 `/roof/outline`（按 PLZ + 点击
取官方建筑轮廓）与 `/roof/pack`（手绘平面算组件数），配置器规格只把它列为
"可选屋顶步"（`14-solution-configurator.md:7`）。`lod2.py` 自己的 docstring
写明萨克森-安哈尔特、黑森等州是门户工作流，"not fetched automatically, and the
roof step falls back to drawing the roof by hand there"。

**因此：CityGML/LoD2 自动识别不是缺口，规格未要求。**审计把一个可选能力
当成了规格承诺的验收项。

## 2. LoD2 / packing 既有验收不仅存在，今天实测通过

审计说"无任何验收或 e2e"不准确：`tests/e2e/specs/configurator.spec.ts:309-380`
（2026-11-09 提交 `9383d625f`）已经覆盖屋顶步，今天在 review 实例上跑绿：

```
just e2e review configurator.spec.ts -g "roof"
✓ roof step: a real Munich address yields an outline and a module count (8.1s)
✓ the German roof step answers in German on the same geometry (6.8s)
2 passed (16.2s)
```

同批的 API 级实测（engine 直连 `127.0.0.1:8890`，guest 主体）：

- `/roof/outline` PLZ 80538 → `found=true`、`building_id=DEBY_LOD2_5006490`、
  `address=St.-Anna-Platz 8`、`planes` 非空、`modules=125`、`kwp=57.5`、
  `source="LoD2 DE-BY"`、`licence="CC BY 4.0 (Bayerische Vermessungsverwaltung)"`、
  5 条 assumptions 逐条披露。真实巴伐利亚瓦片下载耗时 18.6 s。
- `/roof/pack` 约 10×6 m、30°/180° → `area_m2=80.28`、21 块、`kwp=9.66`，
  `module_polygons` 21 个与计数一致。
- 排除规则实测：方位 0°/30° → `usable=false, reason=roof_faces_north, modules=0`；
  70° → `reason=roof_too_steep, modules=0`；5° 平屋顶 30° 方位 → `usable=true`、
  14 块（平屋顶按南向排布，符合 `packing._facing`）。

单测：`test_roof.py` 8 passed（`triftstrasse_5` 真瓦片、索引只建一次、
四州 URL 网格、门户州回退手绘、手绘平面计数、越界拒绝）。

## 3. 导入域：真缺口是取证维度，不是时间

`docs/acceptance/2026-10-31/548/INDEX.md:1306` 记的原文是

> CUA Chrome and IAB were disabled by Work settings, so **EN/DE1440/390 browser
> visual acceptance remains open**.

而 `548-roof-import-workflow.md` 明确要求：

> Native EN/DE × 1440/390 evidence must exercise file selection,
> invalid/corrected input, actual preview/attach/save/reopen, retained holes,
> navigation refusal, focus restoration and overflow.

也就是说：11-05 那次（`workbench-engineering-chain.md` Addendum 4）证明了
`geometry/import` 200 与屋顶进计划视图，但它是一次生产 RPC + UI 点选，
**没有双语言双视口的原生浏览器取证**。这条一直挂着，与"验收早于 11-05"
无关——它根本不早，它压根没有。

### 3.1 今天补齐的原生 e2e

新增 `tests/e2e/specs/planner-roof-import.spec.ts`，四格
EN/DE × 1440/390，每格都走完整真实链：

```
npx playwright test specs/planner-roof-import.spec.ts   (review 实例)
✓ en @1440 (12.5s)   ✓ en @390 (10.1s)
✓ de @1440 (15.3s)   ✓ de @390 (16.4s)
4 passed (56.0s)
```

每格断言的是服务端结果，不是控件状态：

1. 真实上传仓库自带的 `fixtures/planning/source-roof-wgs84.geojson`
   （3-4-5 屋顶 + 1 个内洞）；
2. 三步向导：文件/屋顶 → 平面（36.87°、180°、相对高 5 m、基准说明）→
   来源声明与留存授权（德语用逗号小数）；
3. `Prepare roof preview` 后从**prepared manifest** 读回
   `Roof-plane area 187.67 m²`（后端值 `187.66430950859078`）与
   `Openings retained = 1`——预览的是被接受的真实几何，不是回显输入；
4. `Add roof to current design` → `Save project` → `.lp-save-state` 显示已保存；
5. **reload 后从服务器读回** `Imported 3-4-5 roof`，证明屋顶真的在项目里；
6. 收尾删除该项目（应用自身的删除命令），实例回到原状。

德语格用的是德语控件名（`Dachgeometrie importieren`、`Dachneigung`、
`Fläche in der Dachebene`、`Übernommene Aussparungen`、`Projekt löschen` 等），
逐条对照 `linker-tools-de_DE_formal.po` 的 msgstr，不是英文页面套壳。

### 3.2 API 级导入链（同一实例，独立复验）

`/planning` 私有边界（三 header：service token + principal kind + subject），
guest 主体，project `956e39fa…`：

| 步骤 | 结果 |
|---|---|
| `projects/create` | 200，revision 1 |
| `geometry/import` | 200，asset `b32f3039…` |
| `projects/revise`（attachments） | 200，revision 2 |
| `projects/read` | `geometry_imports.selected` 与 source `reference_sha256` 一致 |

manifest 关键值：

- `plane_intersection_method = geodetic_vertical_line_v1`
- `projection.proj = 9.8.1`、`pyproj = 3.8.0`、`grid_dependencies = []`
- `original_content_sha256 = content_sha256 = 47770a0d…`（原字节未被改写）
- `boundary_uv` 4 点、`holes_uv` 1 洞（内洞保留）
- v 轴 `(0, 0.8, −0.6)` 范数 1；水平 11.12 m 映射为坡长 13.906 m，
  即 **5/4 坡长关系成立**（规格要求的 3-4-5 保持）

`geometry/review` 对该屋顶：`geometry_status=no_conflicts_detected`、
`review_complete=true`、`uv_resolution_m=1.78e-15`（限 1e-9）、
`engineering_status=not_evaluated`、3 条 `missing_input` 诊断（源精度、
边缘净距、障碍净距未给——正是规格要求的"未知保持 null"）。

### 3.3 组件级恢复语义（既有，非本轮新增）

`apps/planner/tests/geometry-import.test.mjs` 10 个用例覆盖 IndexedDB 恢复：
丢失确认保留原字节/键、未知 422 保留冻结意图而 typed refusal 释放、
native admission 撤回阻止派发、journal 写失败阻止上传、
关窗/换 scope 不能接受迟到结果、零高基准绕过被拒高度但保留更正路径、
跨 Back 保留原始 locale 输入与洞。这些是恢复语义，不替代 3.1 的原生链。

## 4. 遮挡链：规格边界，且今天单测全绿

`direct_beam_*` 与 `geometric_pv_*`：

```
pytest test_direct_beam_index.py test_direct_beam_job.py
       test_direct_beam_visibility.py test_geometric_pv.py
       test_geometric_pv_job.py test_geometric_pv_witness.py
38 passed in 432.57s
```

**没有任何客户入口调用它们**：`/planning` 的 `runs/direct-beam` 与
`runs/geometric-pv` 只在 `runtime_config` 显式配置
`direct_beam_visibility` / `geometric_pv_generation` 时才注册，review 实例的
`planner/runtime.json` 未配置这两项，实测返回 `503 version_unavailable`。
生产侧同样没有执行记录（与 `548-domain-gap-matrix.md` 第 3 行一致）。

因此：**"无生产执行"是事实，但不是本域的缺口**——两条链没有面向客户的通路，
规格也没有承诺它们在当前产品里可用。单测绿是它们当前的全部验收，符合现状。

## 5. 辐照取源链：本实例未配置 weather（部署边界，非代码缺口）

`runs/weather` 同样返回 `503 version_unavailable`：review 实例的
`planner/runtime.json` 没有 `weather_acquisition` 与 `pv_preparation` 段，
而 `runtime_config.weather_service()` 在这两项缺失时返回 `None`。

这是部署配置，不是实现缺陷——11-05 生产验收已经跑通完整 PVGIS 链
（`workbench-pv-tail-chain.md`：`runs/weather` succeeded、8760 小时间隔、
PV → 储能 → 报告 PDF 53 197 字节）。本轮不重复该链，也不把它记作缺口。

PVGIS 端点在复验时可达（`re.jrc.ec.europa.eu` 2.4 s / HTTP 200），
配置一旦就位即可复跑。

## 6. 本轮执行过的命令与结果

```
# 单测
pytest test_roof.py test_geometry_import.py test_geographic.py -q
  → 37 passed in 2.19s
pytest test_direct_beam_{index,job,visibility}.py test_geometric_pv{,_job,_witness}.py -q
  → 38 passed in 432.57s

# 既有 e2e
just e2e review configurator.spec.ts -g "roof"
  → 2 passed (16.2s)

# 新增 e2e
npx playwright test specs/planner-roof-import.spec.ts   (LINKER_E2E_INSTANCE=review)
  → 4 passed (56.0s)

# 静态
npx tsc --noEmit -p tests/e2e/tsconfig.json      → clean
npx prettier --check specs/planner-roof-import.spec.ts → clean
```

## 7. 资源与清理

- review 实例全程复用，未重启（WP 8889 / engine 8890 / genie 8891 未动）。
- 本轮创建的测试项目共 8 个（1 个 API roundtrip + 7 个 e2e 迭代），
  全部经应用自身 `projects/delete` 删除；复验后
  `SELECT COUNT(*) FROM projects WHERE title LIKE 'm-roof%'` = **0**。
- 实例 workspace 项目总数在执行前后为 62 → 62（期间其他并行线新增的
  `K final`、`Map chain e2e`、`Country probe` 等**非本线创建**，
  按纪律未触碰）。
- 未新建实例、未新建 worktree 之外的运行资源；e2e 的 `node_modules` 在
  `/tmp/m-roof/tests/e2e` 内独立 `npm ci`（未符号链接主树）。
- 未向生产写入任何数据，未发送任何邮件。

## 8. 仍未覆盖（如实列出，不掩盖）

- `planner-roof-import.spec.ts` 未覆盖规格里"无效输入被拒后同一份可编辑
  原始值仍在"的浏览器取证——该语义由 `geometry-import.test.mjs` 的
  10 个用例覆盖（DOM 级），但双语言双视口的原生失败态举证仍缺一格。
- 规格提到的"未完成导入阻止离开工作区与项目"、"焦点恢复"、
  "错误字段滚动清除两条 sticky bar" 三项，本轮未取证。
- `runs/weather` / `runs/direct-beam` / `runs/geometric-pv` 在 review
  实例上不可用（部署未配置），未在本实例验证。

以上三项需要时可在同一 e2e 文件内继续扩展，不需要新的环境。
