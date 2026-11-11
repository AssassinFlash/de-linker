# 地图链 e2e 复跑（审计 D 线 U1 的解除证据，2026-11-11）

审计结论 `548-domain-gap-matrix.md` 第 1 行把「地图/平面/3D」列为**需补验**，理由是地图域代码
2026-10-24 后未改动，而 11-06 起有 quick start 改版、通用模块分级、报告修复等 planner UI 变更，
该套件依赖 `#lp-design` 标签与按钮文案，可能已被打破。本文件是复跑结果。

**结论：通过。8/8 用例全绿，地图链在 11-11 的 planner UI 上仍然可用，无需改 spec、无需改功能。**

## 运行

```
cd tests/e2e
LINKER_E2E_INSTANCE=review npx playwright test specs/planner-map-chain.spec.ts --reporter=line
```

- 实例：`review`（`~/de-linker-local/instances.toml`），WP `http://127.0.0.1:8889`、
  engine `8890`、Genie `8891`。三个健康检查在开跑前均为 200（`/wp-json/`、两个 `/health`）。
- 环境：Playwright 1.64.0，Node v24.22.0，Chromium（`Desktop Chrome` device profile），
  单 worker 串行（`playwright.config.ts` 的 `workers: 1`）。
- 基线：`main` @ `0ddd666db`。独立 worktree `/tmp/h-spec-map`，`tests/e2e` 内单独
  `npm ci`（不符号链接主树）。

## 结果

连跑两次，两次全绿：

```
[1/8] en: the map workspace mounts from a plain project through the full chain
[2/8] en: external map requests wait for the street-map opt-in and recover from tile failure
[3/8] en: the design view triad carries the geometry across plan, map and 3D
[4/8] en: phone viewport · touch taps collect corners and one-finger drags scroll the page
[5/8] de: the map workspace mounts from a plain project through the full chain
[6/8] de: external map requests wait for the street-map opt-in and recover from tile failure
[7/8] de: the design view triad carries the geometry across plan, map and 3D
[8/8] de: phone viewport · touch taps collect corners and one-finger drags scroll the page
  8 passed (1.5m)
```

第二次以 JSON reporter 走标准输出复核，逐条带真实耗时（`stats`：`expected 8`、
`skipped 0`、`unexpected 0`、`flaky 0`、`duration 51 070 ms`、退出码 0）：

| 用例 | 行 | 耗时 |
| --- | --- | --- |
| en: the map workspace mounts from a plain project through the full chain | 244 | 12.0 s |
| en: external map requests wait for the street-map opt-in and recover from tile failure | 515 | 4.3 s |
| en: the design view triad carries the geometry across plan, map and 3D | 574 | 4.6 s |
| en: phone viewport · touch taps collect corners and one-finger drags scroll the page | 611 | 4.6 s |
| de: the map workspace mounts from a plain project through the full chain | 244 | 11.1 s |
| de: external map requests wait for the street-map opt-in and recover from tile failure | 515 | 4.3 s |
| de: the design view triad carries the geometry across plan, map and 3D | 574 | 4.6 s |
| de: phone viewport · touch taps collect corners and one-finger drags scroll the page | 611 | 4.8 s |

每条的 `results[*].status` 都是 `passed`、`errors` 为空，不是跳过：`expectedStatus`
为 `passed` 且 `skipped 0`，说明这 8 条是真跑真过。

## 这套用例实际覆盖了什么

这不是"页面能打开"的冒烟。8 个用例串起的是整条屋顶绘制链，每一环都由真实 UI 断言守住：

| 环节 | 断言的可观察结果 |
| --- | --- |
| 项目创建 → 站点锚点 | `Create project` 后 `?project=`、`.lp-save-state` 出现（hydration 证据）|
| 进入屋顶工作区 | `#lp-design` URL 段、`Add roof face` 表单提交 |
| 坐标参考门 | `true_north` + 经纬度 + 来源两项，`Start roof drawing` 由禁用转可用 |
| maplibre 画布挂载 | `.maplibregl-canvas` 可见、`[aria-label="Project map"]` 可见 |
| 四角采集 | 画布内四次点击，`role="status"` 计数 0→1→2→3→4 |
| 撤销/重做 | `Remove last corner` 使计数 4→3，重点同一位置回到 4 |
| 闭合 → 屋顶属性 | `Close outline and review` → `Roof properties` 链接可见 |
| 暂停后变陈旧 | `Pause drawing`、加模块规格后提示 `The project geometry has changed since this drawing began`，`Discard drawing` 后重新开始 |
| 编辑顶点 | 边中点拖拽使计数 4→5，不离开复核态 |
| 域校验错误 | `pitch=90` 命中 `[aria-invalid="true"][name="pitch"]` 与字段级 `.lp-field-error` |
| 保存 → 边界选择器 | `Save project` 后两个屋顶边界都在选择器里 |
| 障碍物 | 三点画 footprint → `Chimney` 1.5 m → 保存后 `Obstacle footprint` 出现在边界选择器 |
| 外部请求同意门 | opt-in 前外部请求数 = 0（断言 `toEqual([])`）；`Load street map` 后 > 0 |
| 瓦片失败恢复 | 拦截 `tiles.openfreemap.org` → 失败提示可见且几何不变；解除拦截重试后提示消失 |
| Plan / Map / 3D 三态 | 3D 出 `role="img"` 屋顶图、Plan 出 `.lp-plan-svg`、Map 出 canvas |
| 手机 390×844 | CDP touch 事件采角；单指拖拽滚动页面而非移动地图 |

最后一条尤其相关：它验证的是**协作手势**——单指拖页面、地图不抢手势，这是 UI 改版最容易
打碎的交互契约之一。

## 为什么这次能证明"UI 改版没有打破地图链"

- **选择器与文案全部命中。** 该 spec 依赖四个 `#` 稳定锚点（`#lp-design` 容器、`#lp-site`、
  `#lp-map-roof-properties`、`#lp-map-feature-properties`）以及若干 `lp-*` 类锚点，还要英德各自
  41 条文案键命中（`Start roof drawing` / `Zeichnung beginnen`、
  `Close outline and review` / `Umriss schließen und prüfen` 等）。
  任何一条被改版改掉，对应用例都会红。全绿说明 11-06 起的 quick start、模块分级、报告修复
  都没有触及这些锚点。
- **不是靠放宽超时蒙过的。** 用例本身对 hydration、地图挂载、域提交分别给了 30s/60s/60s 的
  显式预算，且串行有状态断言（计数逐次递增、边界选择器覆盖两个屋顶），这类断言不能靠等待过关。

## 边界（不要把这次结果读大）

- **只跑了地图域这一套。** 不构成 planner 全量回归，也不覆盖 quick start、模块分级、报告修复本身。
- **只跑了 review 实例。** 生产行为需另证；本记录不涉及任何生产写入或生产读回。
- **只跑了 Chromium。** `playwright.config.ts` 里 webkit/firefox 仅用于 `header-parity.spec.ts`，
  地图链没有跨引擎覆盖。
- **图像标定仍未实现**（`548-domain-gap-matrix.md` 第 1 行同时列出的另一缺口），本次没有触碰，
  状态不变。
- 本次没有改动 `planner-map-chain.spec.ts`：没有需要对齐的选择器，也没有需要修的功能。

## 资源

- 无新建实例（只用既有 `review`）。无 docker 容器、无新增端口监听。
- worktree `/tmp/h-spec-map` 与其独立的 `tests/e2e/node_modules`（`npm ci`，8 个包）随本 PR
  存在期间保留，PR 关闭后删除。
- Playwright 产物在 `tests/e2e/artifacts/`，已被 `.gitignore:23` 覆盖，不入库。
