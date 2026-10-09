# 190 选型链路追踪（wt-190 @ 5117962a，2026-10-09，只读）

结论：候选选择的因果判断成立；三处与因果报告不符：①这句话的正文不经过模型，走确定性组装；②结尾团队邮件句来自第二句"Help me narrow the choice"被单独拆成的任务；③把条件写进 `design_basis` 与 SPEC D6 冲突。用主仓库 `.scratch/website-direction-review-20261008/probe-advisor-selection.php` 在本树复跑仍 RED（同 12 个型号）；用 `tests/fixtures/advisor-consultation.php` 跑完整 resolver + validator 复现了正文与邮件句。

## 请求全路径

| 步骤 | 位置 | 本句实际情况 |
|---|---|---|
| REST 入口 | `class-linker-ai-rest.php:3682 message()` → `:827 orchestrated_answer()` → `:891 Orchestrator::answer` | 只传原文 |
| 计划 | `class-linker-ai-task-planner.php:4854 plan()` | 第 1 句因 `requests_class()`（`products.php:2522`，planner `:4580`）定为 `product_lookup`；第 2 句无类型，`:4900` 进 `$unresolved` |
| 条件丢弃 | planner `:4976` | `extract_design_inputs()` 抽出 `{kwp:10, phase:three, segment:residential}`（`:248/:319/:351`），之后全文件未读；`design_basis` 只在 `project_direction` 且明确要求设计时才填（`:5027-5028`） |
| 合同重建 | `class-linker-ai-contracts.php:1532-1560 task_plan()` | 白名单重建任务，resolver `:5466` 再跑一次；新增字段必须进白名单（参照 `partner_class` `:1557`） |
| 第 2 句 | planner `:4682-4743 model_task_proposals()` | 为 "Help me narrow the choice" 提出 general / navigation_service 任务 |
| 解析 | resolver `:5387` → `scope_product_request()` `:2249` | `product_lookup_object()`（planner `:3941`）返回空（"need" 不在 `PRODUCT_LOOKUP_ACTION` `:70`）→ `resolve_product()` `:1229` → `family_results()` `:240` → `:291` 以整句调用 `Linker_AI_Products::resolve_class($query)` |
| 选品 | `products.php:2235` | `query_kinds()` 得 battery_module、battery_system、hybrid_inverter；无品牌/型号分数 → `class_families`/`class_qualified`；排序 `:2367`（分数→有 Woo 绑定的物料数→家族大小→strcmp），名额 `:2397`（两组各 6） |
| 第二道筛选 | resolver `:1016 family_evidence()` → `families_in_sales_range()` | 只按在售筛；`:1120-1133` 每商品一条 `visible_product`，标 `current_authority` |
| 正文模式 | validator `:2520` + `:4599-4600` | "three-phase" 命中 `\bphase`，`asked_spec_keys` 返回 `['phases']`，锁为 authoritative；Orchestrator `:120-131` 不调用 `Model::compose` |
| 卡片 | validator `:3289-3292` | 每条 `visible_product` 都发卡，默认角色 candidate（`:3335`） |
| 正文 | validator `:9634-9655` | 列前 6 个标题（`ENUMERATION_LIST_MAX` `:6483`） |
| 团队邮件句 | validator `:7899-7909` 合并第 2 句任务回答；出自 `:9911-9913` 或 `:9990-9992` `team_email_sentence` | 第 2 句不涉及商品 |
| 组装 | validator `build()` `:4900-4925` | 顶层 `design_inputs` 来自 `$design_result`（`:4914`），非设计轮次永远 `[]`，不能当通过信号 |

## 电池怎么进名额，"future battery" 该在哪处理

- `query_kinds()` 词表循环（`products.php:1415-1432`）用 `battery` 认领电池组；句中有 "I need"（`:1484-1488`），之后两类都进 `$asked`（`:1501`）。`without_reference_classes()`（`:1534`，正则 `:1591`）只认 for/with 之后 0–4 词内的类为参考；"with 10 kWp PV and a future battery" 中间 6 词，电池被判成购买对象。
- 修法（若在现结构上做）：`:1552-1606` 类名前紧跟 future/later/künftig/zukünftig/später 时算参考类，并记为选型条件 `future_kinds:['battery']`，只作为对逆变器的条件。

## 已有的商品事实读取函数（Products 现在都不用于选品）

| 事实 | 函数 | 返回 | 选品是否调用 |
|---|---|---|---|
| 用途 | `tv_woo_b2b_application()` `catalog-taxonomy.php:41-52`（读 `pa_application` slug） | `home`/`commercial`/`''` | 仅经 `product_segment()`（`products.php:153-157`）在 `search()` 用 |
| 相位、交流功率 | `tv_woo_b2b_product_traits($wc)` `reference-and-display.php:175-236` | phase `'3'/'1'/'na'`，power 瓦，kwh | 否；Woo `pa_phase` 无任何代码读 |
| 键值数据（ADR-0033） | `tv_b2b_product_figures()` `material-facts.php:1626`、`tv_woo_b2b_facts()` `product-page.php:252`、`tv_b2b_material_with_overrides()` `:1778` | 字段→`{value,unit,…}` | `product_record()` `:341-367` 仅展示 |
| 材料规格 | 注册表 `technical.specifications` | `phase/phases`、`ac_output_kw_nominal/rated_ac_power_kw`、`max_pv_input_power_w` | 否 |

注意：`max_pv_input_power_w` 单位混 W/Wp/kW，必须读 `unit`；`product_traits` 判三相用 `/3|three/i`，会把 "1/N/PE a.c. 230 V" 判成三相；注册表材料无用途字段，用途只在 Woo。

## 若在现结构上最小修复（仅作参考，业主已裁定不走此路）

1. planner `:4976`/`:5047-5063`：product_lookup 任务加 `selection={phase,segment,pv_kwp,future_kinds}`，不写 `design_basis`（D6）。2. `Contracts::task_plan()` 白名单加 `selection`。3. `without_reference_classes()` 加 future 修饰词规则。4. `resolve_class(query, limit, selection)` 在 in_range（`:2259-2262`）后、`family_scores()`（`:2285`）前过滤；缺字段记 unknown 保留；排序把"已知全匹配"作次级键。5. resolver `:291` 传入；全部排除时不得落回 `:298-306` 的无筛选猜测。6. planner `:4895-4901` 把 narrow/choose/eingrenzen 类无主语子句并入前一产品目标。
单靠代码排不掉 ETR：6 台均三相、PV 上限 160–250 kW，只有 Woo Application=Commercial 能排除。kWp 冲突实例：SAJ HS2-5K 上限 7 500 Wp、HS2-6K 9 000 Wp。

## 测试

- `php tests/unit/<name>-test.php`；`advisor-consultation-evidence-test.php` 1003 checks / 0 failures，约 18 s。
- fixture `tests/fixtures/advisor-consultation.php` 无 `wc_get_product`、未加载 `catalog-taxonomy.php`：用途永远 unknown，测用途要打桩。
- 相关：`advisor-consultation-evidence-test.php`（A05 `:628-684`、080-3 `:770-814`、resolve_class `:3381-3386`）、`advisor-sales-range-test.php`、`advisor-design-contract-test.php`、`faq-product-lane-test.php:238`、`advisor-asked-kinds-test.php`、`tests/integration/advisor-comparison-context.php`、`advisor-compatibility-scope.php`；`tests/advisor-prototype/*.mjs` 只测前端 bundle。
- "既有候选红断言"：主仓库未跟踪的 `.scratch/website-direction-review-20261008/replay-advisor-selection.py` + `probe-advisor-selection.php`；经 `git show` 读代码、单参数调用、无 Woo 数据。

## 与因果报告不一致处

1. `design_basis.inputs` 违反 D6，且响应 `design_inputs` 来自 validator `:4914`。2. 正文路径是 authoritative 确定性组装。3. 团队邮件句来自第 2 句的提案任务。4. 6 件 ESA 在注册表 kind 为 `battery_system`。5. 线上正文列 4 块、本树列 6 个标题，差异未核。6. 换成 "Find…" 会因 "for"+"PV" 进 MPPT 过滤（resolver `:2268-2275`），结果随措辞变。7. 用途判定已有两份（planner `:349-355` 与 `products.php:174 query_segment()`）。`Linker_AI_Engine` 不在此路径。
