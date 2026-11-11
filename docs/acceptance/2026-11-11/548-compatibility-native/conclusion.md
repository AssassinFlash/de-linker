# #548 域 6 兼容半 · 兼容合同与工程覆盖层的原生验收（2026-11-11）

域缺口矩阵（`docs/acceptance/2026-11-11/548-domain-gap-matrix.md`）第 6 行把兼容半
判为「需补验」：兼容合同的运行时证据只有生产 feed 的 377 对 pairs（#1081 修复后
读回），没有任何 2026-11-05 之后的**原生**验收——没人证明客户在界面上看到兼容结果
时，合同的裁决、条件和文档引用是真的到了屏幕上。

本记录补上这一段，并把断言固化成回归：
`tests/e2e/specs/planner-equipment-release.spec.ts`。

## 结论

**通过，无缺陷。** 合同、条件和文档引用在原生界面里逐字成立；工程覆盖层（Trina
参考组件）在它真正生效的两层上都可验证。共 10 条用例（EN/DE × 5 类），全绿。

| 断言线 | 观察到的真实结果 |
| --- | --- |
| discharged 配对（released） | `Manufacturer pairing · Checked requirements met`，2 条条件逐字渲染，5 个 `Source document` 链接 |
| 文档集不含该配对（not_released） | `Manufacturer pairing · Further checks required`，**不**出现 met 措辞 |
| released 且合同给页码 | `Source document · Page 12`、`Source document · Page 2` 真实渲染 |
| released 但配置违反条件 | 仍为 `Requirements not met`，不冒充通过 |
| 覆盖层物化（`products/current`） | Trina 参考件 1 条，绑定 Woo 产品与 overlay id，citation page 2 |
| 覆盖层设计披露（`/design/residential`） | 串布局引用该件，逐字披露句存在，BOM 不把它当产品 |

## 这条链为什么必须走原生

引擎的 `manufacturer_pair` 是三层数据（`services/engine/src/linker_engine/planning/equipment_assessment.py:417-432`）：

```
{"verdict": released|released_with_accessory|not_released|unknown,
 "conditions": [{en, de}, …],
 "documents": [{url, page}, …]}
```

合同本体在 `services/engine/src/linker_engine/compatibility.py`。前端把项目级与每系统级
`manufacturer_pair` 收进同一个 `<details>`（`EquipmentConditions.tsx`）：条件按页面语言取
en/de，文档渲染成 `<a href target="_blank" rel="noreferrer">Source document</a>`，只有当
`page` 是数字时才追加 ` · Page N`。引擎正确不等于屏幕正确——所以断言只认屏幕。

断言不是"我期望什么"，而是"屏幕与引擎这次真实答复一致"：用例在页面自己发出的
`rpc/runs/read` 轮询上挂路由，抓下该次运行的 assessment，再拿它去比对 DOM。工程实现见
`checkedPair()`。

## 四种状态，各自证明什么

1. **released（GoodWe GW80K-ET-G10 + GW61.4-BAT-AC-G10）** — 生产实走 2026-11-11 里
   被释放的那一对。屏幕给 met，两条条件（"Two GoodWe documents carry this pair…" 与电池
   电压/功率条件）逐字在页面上，5 个链接的 href 顺序与合同一致、rel/target 全等。
   这条配对合同**不给页码**（页码写在条件句里），所以断言同时要求页面**不出现**凭空
   的 `Page N`——这是防"多显示一点"的反向约束。
2. **not_released（GoodWe GW6K-ETA-G20 + SAJ B2-10.0-HV1）** — 合同写明"引用文档未列出
   此配对"。屏幕必须是 further checks，且绝不能出现 met。变异验证：把断言改成要求 met，
   EN/DE 双双失败（实际渲染 `Weitere Prüfung erforderlich`）。
3. **released 且带页码（SAJ HS2-6K-T2-X + BU2-5.0-HV1，2 模块）** — 合同给 `page: 12` 与
   `page: 2`，屏幕真实渲染 `Source document · Page 12` / `· Page 2`，链接集合逐个精确。
   这是 addendum 7「Source document · Page 2」先例在设备侧的等价物。
4. **released 但配置违反条件（同配对，1 模块）** — 合同 verdict 仍是 released（文档确实
   释放了这一对），但条件写明 HS2 接受 2–5 个模块，1 个越界。屏幕显示
   `Requirements not met`，不得显示 met。**这一条是本轮最有价值的发现**：它证明
   "released 不等于通过"在原生界面里确实成立，合同与配置判定是两条独立的线。

## 工程覆盖层：断言放在它真正生效的层

overlay 是 feed 里的 1 条 Trina 参考组件规则（`mat_trina_solar_tsm_460neg9r_28`）。查证后
它的客户可见性分三层，前两层可断言，第三层不存在：

| 层 | 真实行为 | 本次断言 |
| --- | --- | --- |
| `products/current` 物化 | 发布记录里 1 条 `references`，`pv_modules[0]` 的 `source.woo` 绑定产品 8349 与 overlay id，citation `page: 2`，`gamma_pdc_per_c = -0.0029`（= −0.29 %/°C ÷ 100） | 逐字段比对，含 datasheet sha256 形状 |
| `/design/residential` | `selected.strings.module = "Trina Solar TSM-460NEG9R.28"`、`module_wp = 460`，且逐字披露 "The string layout uses … as a reference module; the module you install can change it."；BOM 里**没有**该型号，而是 "PV modules of your choice" | 断言引用身份、披露句与"不当作产品线" |
| 设计页模块表单 | **不存在**：`moduleTiers.ts` 明确写出档位模块 `source.kind` 只能是 `user_declared`、`woo` 必须缺席，"this is never a product reference"（`moduleTiers.ts:148-155`） | 不虚构断言 |

因此 10-05 addendum 7 那条 `Source document · Page 2` 的**设备侧等价物**是上面第 3 种
状态（SAJ 配对的 `Page 12` / `Page 2`），而不是模块表单——模块表单按设计不引用产品文档。
这一点此前没有被写清楚，本记录予以固定。

## 断言强度（变异验证）

断言不是空转的，用两次变异证明：

| 变异 | 预期 | 实际 |
| --- | --- | --- |
| not_released 用例改要求 "met" | 应失败 | EN/DE 双红，`unexpected value "Herstellerangaben zur Kombination · Weitere Prüfung erforderlich"` |
| released 用例改要求 "further" | 应失败 | EN/DE 双红，`unexpected value "… · Geprüfte Anforderungen erfüllt"` |

还原后复跑全绿。

## 一个会挂住跑批的写法陷阱（已在本 spec 内避开）

`NumberField` 用 `<label htmlFor>` 包住 input，所以 `getByLabel('Batteriemodule je Stack')`
返回的**就是 input 本身**；再写 `.locator('input')` 会永远匹配不到。Playwright 的
**action timeout 默认无上限**（`expect` 有超时，`fill`/`click` 没有），这一步因此会无限期
等待，整轮 run 挂死而没有任何报错输出。本 spec 改用
`label.lp-field` + `hasText` + `.locator('input')`。任何按可见标签定位输入框的新用例都
要避开这个组合。

## 运行

```
cd tests/e2e
LINKER_E2E_INSTANCE=review npx playwright test specs/planner-equipment-release.spec.ts
```

- 实例：`review`（WP 8889 / engine 8890 / genie 8891），三处健康检查开跑前均 200。
- worktree `/tmp/ac-compat`（`main` @ `1c2f86cbb`），`tests/e2e` 独立 `npm ci`（8 包，
  不符号链接主树）。
- `tsc --noEmit` 与 `prettier --check` 均通过。

## 一处实例状态（不是代码缺陷，未修）

review 实例的 `~/de-linker-local/review/planner/runtime.json` 缺 `equipment_search` 段。
`tools/local/src/linker_local/services.py:503` 已把这个段写进新建实例的默认配置，但该实例
生成于加入之前，于是 `RuntimeConfig.equipment_search_service()` 返回 None，
`POST /planning/runs/equipment-search` 直接 503（引擎日志两条对应记录；`/planning/version`
的响应也确实没有 `equipment_search` 键）。

**本记录没有改这个配置，也没有重启实例。** 影响面限于 quick start 的自动搜索；
`/runs/equipment`（资格判定，出 release 的那条）由 `equipment` 服务提供，不受影响——
本次验收走的就是手选设备路径。顺带说明：`planner-commercial-quickstart-report.spec.ts`
依赖搜索，在**这个**实例上会红；那是实例配置缺口，不是回归。建议下次 `just serve review`
或实例重建时自然带上该段。

## 边界（不要把这次结果读大）

- **只覆盖兼容合同与覆盖层这两条线。** 不构成 planner 全量回归。
- **只跑 review 实例的 Chromium、1440 宽**。390 与 DE 文案已在用例里参数化，但设备检查
  在手机宽度不是判据（工作台本身按 1440 设计）；本轮没跑 390 的这条链。
- **overlay 的断言在合同层与发布层，不在 DOM 层**——原因见上表第 3 行，这是设计事实
  而非覆盖缺口。
- 未改任何产品代码、未部署、未写生产（`production_changed: false`）。

## 资源

- 未新建实例、未重启 review 栈、未部署。
- 采集建了若干访客项目（每次运行 1 个/用例；10 条用例 ≈ 10 个项目），与
  `planner-map-chain` / `planner-identity` 等既有 planner spec 同法。
- worktree `/tmp/ac-compat` 与其独立 `node_modules` 在本 PR 生命周期内保留，关闭后删除。
- 一次性探针 spec 与 `/tmp/ac-compat-evidence/` 已在提交前删除，未入库。
- Playwright 产物在 `tests/e2e/artifacts/`（`.gitignore` 覆盖）。
