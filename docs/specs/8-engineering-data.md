# #8 工程数据迁移

## 目标
运行时只剩三份手工源：Woo 商品（含带引用的工程图值）、`data/compatibility.json`、`data/engineering-overlay.json`。旧仓库的注册表、组件库、投影链不进新仓库。引擎读 `linker-commerce` 生成的 feed。

## 来源（只读，旧仓库链尖 `git -C ~/Documents/de-linker-project show refs/landed/chain-tip:<path>`）
- `plugins/terravolt-b2b-core/data/material-registry.json`（285 条：identity、bindings.woo_product_ids、technical.specifications{value,unit,doc,page}、documents）。
- `knowledge/components-db/*.json`（253 个元件，specs 带 doc/page）。
- `contracts/compatibility-lists.json`（37 份文档、228 格裁决）。
- `knowledge/evidence-manifest.json` 与 `document-host-map.json`（档案文件名 → sha256 → 我们托管的 URL）。
- `knowledge/manual-decisions.json`（只取展示覆盖与绑定；AI 写的理由不迁）。

## 目标形状
1. **商品图值**：对每个已发布商品，把引擎需要的键写入 `_tv_b2b_figures`（已有键不覆盖，缺的补；每个值带 `citation: {url, page}`，url 必须是我们托管的文档）：`mppt_voltage_range_v`、`battery_voltage_range_v`、`n_mppt`、`strings_per_mppt`、`mppt_max_current_a`、`mppt_max_isc_a`、`ac_output_kw_nominal`、`max_pv_input_power_w`、`max_pv_input_v`、`phases`、`module_energy_kwh_nominal`、`module_energy_kwh_usable`、`system_operating_voltage_range_v`、`modules_per_stack_min`、`modules_per_stack_max`、`stacks_parallel_max`、`modules_per_system_max`、`max_battery_modules`、`battery_rated_energy`。单位原样保留，读侧按 #7 换算。
2. **系列属性**：全局属性 `pa_series`，值来自注册表 family（如 goodwe-etr、saj-h2），每个商品一个值；配置器与 Genie 用它表达"系列"，不再有五套系列概念。
3. **`data/compatibility.json`**：`{ "pairs": [ { "inverter": "<model pattern>", "battery": "<model pattern>", "verdict": "released|released_with_accessory|not_released", "conditions": ["…"], "documents": [{ "url": "…", "page": n }] } ] }`，由旧合同格子与 patterns 翻译而来；运行时用 pattern 匹配商品型号（`pa_model`）即时得出配对，不再有 relationships 投影。
4. **`data/engineering-overlay.json`**：非商品元件（参考组件 `mat_trina_solar_tsm_460neg9r_28` 等约 3 条）的工程字段与引用；只供引擎用。
5. **feed**：`GET /wp-json/linker/v1/engineering-feed`（匿名、只读、可缓存、按 `?since=` 增量）→ 每个已发布商品 `{ id, sku, model, brand, series, device_class, application, phase, figures{key:{value,unit,citation}}, documents[{url,title,type,lang}] }` + overlay + compatibility 版本号。`services/engine` 只读它。

## 迁移脚本 `tools/migrate/8-engineering.py`
- `plan`：对比每件商品现有图值与注册表/组件库，列出"补充/冲突/漂移"（已知 17 件漂移，以数据手册页为准逐件决定，决定写入 `docs/specs/8-decisions.md`）。
- `write`：幂等写入；引用改写经 host-map；写不出引用的值不写（记入报告）。
- `verify`：feed 与旧 `linker/v1/materials` 字段映射表逐键对比，差异逐条列出。

## 后台
标准产品编辑里增加"图值引用"元框：每个图值一行（键、值、单位下拉、文档下拉（本商品的文档）、页码）。改值即要求重填引用。

## 不做
不改 SKU/名称/描述；不保留 `_delinker_type`、registry kind；不生成任何投影文件。

## 验收
- [ ] 在售 99 条材料的引擎字段逐键对比旧注册表：差异逐条有数据手册依据。
- [ ] 5,739 条引用全部解析为我们托管的 URL；无引用的值不进 feed。
- [ ] `pa_series` 覆盖全部已发布商品。
- [ ] feed 对本地实例返回与旧 materials 等价的字段集合（映射表附 PR）；`?since=` 增量正确。
- [ ] PHPUnit：合同 pattern 匹配对 10 对已知配对（含 released_with_accessory 与 not_released）给出正确裁决。

## 变更记录
- 2026-10-10（#14，评审线 Spec 裁定登记）：`data/compatibility.json` 的形状在规格 3 条（pairs 之外）新增第 4 份必填键 `requirements`，pair 内新增可选 `modules`（`{min,max}` 堆叠数区间）与 `accessories`（`[{model, quantity, per}]` 放行条件所需配件）；引擎（`services/engine/tests/fixtures/compatibility.json` 与 `src/linker_engine/compatibility.py` 的 schema）已按此消费——`requirements` 按逆变器型号给出 meter/backup/parallel-controller 所需件与 `max_units`（并联台数上限，取自控制器数据手册）。#8 落地时必须产出此形状；引擎侧 schema 即契约。
