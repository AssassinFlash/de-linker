# #8 工程数据迁移

## 目标
产品与参考组件的事实、图值、资料关联及公开状态只在 Woo 维护。厂商兼容声明同样只在 canonical Woo 商品维护；`data/compatibility.json` 与 `data/engineering-overlay.json` 均仅保留作一次迁移和恢复输入，运行时不得回退到这两份文件。引擎只读 `linker-commerce` 生成的 feed，并在每次新动作前后消费 Woo 当前发布证明；当前合同见 [系统选型的当前发布依赖](617-publication-engine.md)。

## 来源（只读，旧仓库链尖 `git -C ~/Documents/de-linker-project show refs/landed/chain-tip:<path>`）
- `plugins/terravolt-b2b-core/data/material-registry.json`（285 条：identity、bindings.woo_product_ids、technical.specifications{value,unit,doc,page}、documents）。
- `knowledge/components-db/*.json`（253 个元件，specs 带 doc/page）。
- `contracts/compatibility-lists.json`（37 份文档、228 格裁决）。
- `knowledge/evidence-manifest.json` 与 `document-host-map.json`（档案文件名 → sha256 → 我们托管的 URL）。
- `knowledge/manual-decisions.json`（只取展示覆盖与绑定；AI 写的理由不迁）。

## 目标形状
1. **商品图值**：对每个已发布商品，把引擎需要的键写入 `_tv_b2b_figures`（已有键不覆盖，缺的补；每个值带 `citation: {url, page}`，url 必须是我们托管的文档）：`mppt_voltage_range_v`、`battery_voltage_range_v`、`n_mppt`、`strings_per_mppt`、`mppt_max_current_a`、`mppt_max_isc_a`、`ac_output_kw_nominal`、`max_pv_input_power_w`、`max_pv_input_v`、`phases`、`module_energy_kwh_nominal`、`module_energy_kwh_usable`、`system_operating_voltage_range_v`、`modules_per_stack_min`、`modules_per_stack_max`、`stacks_parallel_max`、`modules_per_system_max`、`max_battery_modules`、`battery_rated_energy`。单位原样保留，读侧按 #7 换算。
2. **系列属性**：全局属性 `pa_series`，值来自注册表 family（如 goodwe-etr、saj-h2），每个商品一个值；配置器与 Genie 用它表达"系列"，不再有五套系列概念。
3. **兼容声明**：canonical 英文 Woo 商品的 `_linker_compatibility_claims` 原生 meta 保存 `{schema_version:1,pairs:[],requirements:[]}`。pair 用 `battery_product_id`，requirement 归属所在逆变器；配件用 `product_id`，均为 canonical Woo ID。每行有稳定 `id`、原有裁决、可选模块数量范围、EN/DE 条件、配件数量与 system/stack/unit 基准、托管文档的 `document_id/document_revision/blob_sha256/product_id` 证据。当前投影保持 schema 1 的 `pairs/requirements/version` 及原型号字段，另显式携带 pair 的 `inverter_product_id/battery_product_id`、requirement 的 `inverter_product_id` 和 accessory 的 `product_id`；型号正则仅由当前名称派生，运行配对以 ID 为准。型号重名不能借用其他 SKU 的声明，改名不会丢失 ID 绑定。多个声明仍取最严格裁决并合并条件、资料和配件。
4. **参考组件**：`mat_trina_solar_tsm_460neg9r_28` 保留为工程 ID；事实与资料迁入隐藏销售展示的 Woo 原生参考记录，不建光伏产品分类、不成为销售候选。feed 的 overlay 由当前记录及已绑定资料生成，携带 canonical source、产品/参考修订及文档身份/修订/SHA/关联。未准备时 overlay 为空，不阻断无关产品。原 `data/engineering-overlay.json` 只供一次迁移，运行时不读取。
5. **feed**：`GET /wp-json/linker/v1/engineering-feed`（匿名、只读、可缓存、按 `?since=` 增量）→ 每个已发布商品 `{ id, sku, model, brand, series, device_class, application, phase, figures{key:{value,unit,citation}}, documents[{url,title,type,lang}] }` + overlay + Woo `compatibility` 投影全量与版本号（`version` 与 `compatibility_version` 同值），有效投影附 `compatibility_origin: "woocommerce"`。无声明时是有效的空投影；不支持的保存结构不出投影与 origin。`services/engine` 只读它。

## 迁移脚本 `tools/migrate/8-engineering.py`
- `plan`：对比每件商品现有图值与注册表/组件库，列出"补充/冲突/漂移"（已知 17 件漂移，以数据手册页为准逐件决定，决定写入 `docs/specs/8-decisions.md`）。
- `write`：幂等写入；引用改写经 host-map；写不出引用的值不写（记入报告）。
- `verify`：feed 与旧 `linker/v1/materials` 字段映射表逐键对比，差异逐条列出。

## 后台
标准产品编辑里增加"图值引用"元框：每个图值一行（键、值、单位下拉、文档下拉（本商品的文档）、页码）。改值即要求重填引用。

## Woo 兼容声明维护与一次迁移（2026-10-25）

标准产品编辑器新增 Manufacturer compatibility declarations 元框，复用 Woo 产品、现有 Documents 关联与相同 Publication 资料权限。Woo 原生属性能保存标量；原生 related/up-sell/cross-sell 只表达推荐关系，均不能承载“裁决 + 数量范围 + 双语条件 + 资料字节版本”。因此采用已有原生商品 meta/元框与 Woo CRUD 保存机制承载结构化声明，不建独立产品/能力库、分类或套装 SKU。

入口仅在 canonical 英文产品编辑，条件分别维护 EN/DE，普通后台文案走现有 gettext/PO/MO。保存校验 nonce、`edit_post` 权限、autosave/revision 和 canonical 身份。商品/配件选择来自同一当前 Publication，文档必须已公开且关联到声明涉及的商品。新建、改行或接受新的 PDF 版本须逐行明确确认；普通保存保留未变行的旧绑定；表单末尾完整性标记与原有行 ID 核对避免输入截断删除声明。资料变字节、修订或关联后旧声明不能自动绑定新文件；相关 scope 不能正面放行，证据仍有效的否定裁决保留，避免删掉失效的限制行后留下较宽的正面裁决。正常 Woo meta/CRUD 保存继续触发既有准备失效链。只有非空声明内容进入该商品事实指纹，空字段和迁移恢复标记不改变无关商品修订。

`EngineeringData::compatibility($manifest)`、PHP `Compatibility`、EngineeringFeed 和 Publication 的 `compatibility_revision` 共用 `Publication\CompatibilityClaims::projection`。同一次 manifest 组装内投影，不递归读取 manifest。此读路径不读静态兼容文件；源声明结构损坏时不授予新放行。旧冻结结果仍由各消费者既有历史收据策略读取，不能被误当当前许可。

迁移入口复用已注册的 publication 命令：

```sh
wp linker-commerce publication migrate-compatibility --dry-run
wp linker-commerce publication migrate-compatibility --apply --source-sha256=<预览 source_sha256> --publication-revision=<预览 publication_revision>
wp linker-commerce publication migrate-compatibility --rollback --dry-run
wp linker-commerce publication migrate-compatibility --rollback --apply
```

默认只预览，输出源文件 SHA-256、当前 publication revision、所有将变 meta 的 before（含是否存在）/after（含 `recovery_meta` 的恢复标记）、保留项和所有未解析原声明。`--input` 可指定保留输入。只有迁移入口按旧 patterns 展开当前已发布 canonical Woo IDs，逐项保留原裁决/条件/范围；未发布、已撤回或身份不明的范围不会因此上架或获准。缺少当前资料/配件的声明保留为 unresolved，不进放行投影。已有非空 Woo 声明不覆盖；同源重复运行幂等。

apply 重新核对预览的源 hash、当前修订与每项 before，通过正常 Woo `update_meta_data/save` 写入，不改 SKU、价格、库存、分类和发布状态。`_linker_compatibility_migration` 仅保存本次 before 与 after 摘要，rollback 只恢复仍与迁移 after 一致的记录，保护后续人工编辑。执行者使用本批已有的恢复记录保留完整预览，并遵守写入前已有备份要求；本轮实现本身不写任何实际 WP 数据。

## 文档维护入口（票 #68，GAP-17）

商品编辑器的 "Documents" meta box（`Linker\Commerce\Admin\DocumentsMetaBox`）维护
`_linker_documents`（`{url,title,type,lang}`，与迁移写入同形）：标题、URL、类型
（datasheet|manual|warranty|document）、语言（en|de）逐行可改，行可删除，留 2 行空行供新增；
保存走 `save_post_product` + nonce + `edit_post` 权限，只接受本机（本站域名）的 URL——
外链一律拒绝并保留原值，空 URL 的行删除。box 顶部写明两条常设规则：文件在自家媒体库
（无来源链接）与"内容改动逐项确认"（本票只做入口，不改内容）。

## 不做
不改 SKU/名称/描述；不保留 `_delinker_type`、registry kind；不生成任何投影文件。

## 验收
- [ ] 在售 99 条材料的引擎字段逐键对比旧注册表：差异逐条有数据手册依据。
- [ ] 5,739 条引用全部解析为我们托管的 URL；无引用的值不进 feed。
- [ ] `pa_series` 覆盖全部已发布商品。
- [ ] feed 对本地实例返回与旧 materials 等价的字段集合（映射表附 PR）；`?since=` 增量正确。
- [ ] PHPUnit：原有已知配对用例经一次迁移到 Woo 后仍给出同样裁决；canonical ID、失效资料、显式重新确认与幂等迁移有针对性覆盖。

## 变更记录
- 2026-10-10（#14，评审线 Spec 裁定登记）：`data/compatibility.json` 的形状在规格 3 条（pairs 之外）新增第 4 份必填键 `requirements`，pair 内新增可选 `modules`（`{min,max}` 堆叠数区间）与 `accessories`（`[{model, quantity, per}]` 放行条件所需配件）；引擎（`services/engine/tests/fixtures/compatibility.json` 与 `src/linker_engine/compatibility.py` 的 schema）已按此消费——`requirements` 按逆变器型号给出 meter/backup/parallel-controller 所需件与 `max_units`（并联台数上限，取自控制器数据手册）。#8 落地时必须产出此形状；引擎侧 schema 即契约。

- 2026-10-10（#8 实施）：逐件决定与来源见 `docs/specs/8-decisions.md`；feed 与旧 materials 的字段映射表见 `docs/specs/8-field-mapping.md`。规格的 19 键中 `mppt_max_current_a`/`mppt_max_isc_a` 是注册表 `max_input_current_per_mppt_a`/`max_isc_per_mppt_a` 的改名。overlay 实际为 1 条（Trina 460 参考组件；其余无绑定材料是已发布模块的组合或无规格占位，见 8-decisions §8）。数据文件落在 `plugins/linker-commerce/data/`（compatibility.json 248 对、engineering-overlay.json），feed 路由 `linker/v1/engineering-feed` 由 linker-commerce 提供。
- 2026-10-11（#68）：`_linker_documents` 的后台维护入口（Documents meta box）落地：编辑标题/URL/类型/语言、删行、空行新增；只收本站 URL。入口只做维护，文档内容仍逐项确认。
- 2026-10-21（#493）：feed 在版本号之外携带 `compatibility` 全量（`data/compatibility.json` 原对象）；引擎的 `sync-feed.py` 用同一次抓取把 `state/compatibility.json` 一并校验、原子换、失败保旧，合同变更不再人工 scp。合同文件不可读时该键缺席（feed 其余部分照常），引擎保留旧合同。`feed.schema.json` 把该键列为可选对象，合法性由引擎的 `Compatibility` 加载器判定；新引擎对键的有无都接受，部署顺序照旧先 services、后 site。

- 2026-10-25：兼容合同维护权迁入 Woo；上述当前维护与迁移规则取代此前运行时静态文件/pattern 匹配及保留旧合同放行的描述。保留文件与既有冻结产物只作历史/迁移证据，不能授权当前新动作。
