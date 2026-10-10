# #8 工程数据迁移 — 逐件决定记录

实施记录，来源都在正文注明。规格：`docs/specs/8-engineering-data.md`。

## 来源与读法

旧仓库链尖 `f007a9dd`（只读 `git show refs/landed/chain-tip:<path>`）：

- `plugins/terravolt-b2b-core/data/material-registry.json`（285 条材料，`technical.specifications{value,unit,citation{doc,page},value_de?}`，共 5,764 个带 `evidence_refs` 的规格条目，其中 5,739 条带 `citation{doc,page}`）
- `knowledge/components-db/{chint,ecoflow,goodwe,mbs,pylontech,saj}.json`（253 元件，specs 带 `doc`/`page`）
- `contracts/compatibility-lists.json`（37 文档、25 逆变器系列、16 电池系列、228 格）
- `knowledge/evidence-manifest.json`（257 证据文件：`file`（`<evidence_id>__<名>`）、`sha256`、`hosted_url`、`also_cited_as`）
- `knowledge/document-host-map.json`（我们托管的 URL → sha256/bytes/media id）
- `knowledge/materials/manual-decisions.json`

站内侧：本地实例 t8 装入快照 `20261010-0033`（2026-10-10 只读拉取）后的 106 件已发布商品读取。

## 1. 引用解析链（验收"5,739 条引用全部解析"）

旧注册表的 `citation.doc` 是证据库里的文件名。解析按下列顺序尝试，第一条命中即止（`tools/migrate/8-engineering.json` 里写入的是最终 URL）：

| 步骤 | 规则 | 命中数 |
|---|---|---|
| 1 | 名字（`file` 去掉 `<id>__` 前缀、`also_cited_as`、evidence id）→ 该证据条目的 `hosted_url` | 2,646 |
| 2 | 同上，但 `hosted_url` 为空 → 以 `sha256` 对 `document-host-map` 的同哈希 URL | 1,744 |
| 3 | 名字 = 某个托管 URL 的文件名 | 656 |
| 4 | 同 3，忽略大小写与标点（`240831_Datasheet_Vertex S+_...` vs 下划线） | 401 |
| 5 | 名字忽略大小写标点后命中证据名 → `hosted_url` | 115 |
| 6 | 同 5，但 `sha256` 换 URL | 176 |
| 7 | `citation.doc` 本身就是托管 URL | 1 |
| 8 | 托管文件名去掉 `_YYYYMMDDHHMMSS[A-Z]NNN` 时间戳尾巴后等于 `doc`（Pylontech Force H3X 两册手册） | 0（并入第 3/4 步的实际形态） |
| 合计 | | **5,739 / 5,739，0 条未解析** |

## 2. 引擎键（规格的 19 键）

规格列出 19 键（`mppt_voltage_range_v` … `battery_rated_energy`）。与注册表的两个改名：

| 规格键 | 注册表键 |
|---|---|
| `mppt_max_current_a` | `max_input_current_per_mppt_a` |
| `mppt_max_isc_a` | `max_isc_per_mppt_a` |

其余 17 键同名。站内 106 件已发布商品对这 19 键的覆盖（迁移前）：483 条与注册表等值但**无一条**带 `citation{url,page}`（旧表单时代写入），107 条缺失（53×2 为改名键，站内只有旧键名；1 为 3581 的 `module_energy_kwh_usable`）。

## 3. 漂移逐件决定（全量比对：站内 `_tv_b2b_figures` vs 注册表，全部共享键）

规格说"已知 17 件漂移"；以 2026-10-10 快照重算，**与注册表有任何键不等价的已发布商品共 21 件**，逐件如下。引擎键（19 键）上的值漂移只涉及 4 件，其余为展示键差异。

### 3a. 引擎键值漂移

| 商品 | 键 | 站内 | 注册表 | 决定 |
|---|---|---|---|---|
| 1959 CHS2-29.9K-T4-X | `ac_output_kw_nominal`、`max_pv_input_power_w` | 29900 W / 59800 Wp | 29999 / 59998（数据手册 p2） | **不改**：#7 的 `7-facts.json` 已按手册 p2 改正并带引用；本票的包不重复覆盖（切换时 #7 先跑，见 §7） |
| 1959 / 1960 / 1961 CHS2 三件 | `battery_rated_energy` | `'57.3–100.3'` | `'100.3'`（unit 注明"merged value printed across all CHS2 models"） | **保持现值**：CHS2 数据手册 p2 对全系列印一个合并区间，注册表的 100.3 只是区间上限，同样不是本型号的值；按业主 2026-10-09 裁定"手册取不到就保持现值"。无引用可写（值与注册表不等），该键不带引用 → 不进 feed；堆叠规则由模块商品的 `modules_per_*` 图值承担 |
| 1185 HS3-12K-T2-W/G-PX | `ac_output_kw_nominal` | `'12000'` | `'12000*'`（污染格式：星号是手册脚注标记） | **保持站内 12000 W，补引用**（注册表 citation 指向同页 p2）：写入 `citation{url,page}`，值不动。`ac_output_kw_max`/`max_output_current_a`/`rated_output_current_a` 的 `'12000*'`/`'17.4**'` 同理属注册表侧污染，站内值保持 |

### 3b. 展示键差异（非 19 键，不属本票写范围）

| 商品 | 键 | 说明 | 决定 |
|---|---|---|---|
| 1178 ATS1-T63-A | backup/grid/inverter_input_current、operating_temperature_range | 站内为更细的表述（"50 rated / 63 max."；-25~+45°C vs 注册表 -25~+50°C） | 保持站内（已有键不覆盖）。温度区间差异记录在案：注册表 `operating_temperature_range` -25~+50 对站内 -25~+45，无手册页可裁决的引用条目对应，不动 |
| 1182/1183/1184/4109 HS2 四件 | battery_scalability、comms、pv_connection（MC4/D4 vs MC4/H4）、ups_switchover_ms、warranty_years（'10' vs '5/10/15/20'）、grid_codes（尾随空格差异） | 展示措辞与保修选项写法不同 | 保持站内；无引擎影响 |
| 1186/1187/2198/2199 | grid_codes（尾随空白差异） | 字符串比较的空白噪声 | 不动 |
| 1832/2067-2070 B2 五件 | dimensions_mm（深 +200 mm）、weight_kg（+11 kg） | 站内比注册表大一圈：与含底座/包装的写法一致 | 保持站内（尺寸非引擎键）；**事实问题留档**：B2 数据手册的净尺寸/重量两说并存，需要时由 #10 的按页索引逐页核对后再定 |
| 3582 OCEAN 2 Battery 8.03 | chemistry `'LiFePO₄'` vs `'LFP'` | 同一事实的两种写法 | 保持站内 |
| 3611/3612 GW6.0/9.0-BAT-D-G20 | bms_comms `'CAN'` vs `'CAN & 485'` | 注册表更宽 | 保持站内（展示键） |

**结论：本票对引擎键做了 0 次值改正**——1959 的两键属 #7，battery_rated_energy 按裁定保持现值，1185 是注册表侧污染。本票新增 107 条图值（全带引用）并给 484 条等值图值补引用。

## 4. pa_series

- 已存在的全局属性 `pa_series`（attribute_id 2，"Series"）沿用；其 4 个孤儿词条 `b`、`h`、`one`、`link`（0 商品使用，旧导入残渣）在 write 时删除（PHP 先断言 `count == 0`）。
- 96 件有注册表绑定的商品：值 = 绑定材料的 `identity.family_id`（1959/1960/1961 双绑定的两个材料同属 `saj-ci-line`）。
- 10 件无绑定商品的值：
  - 6480/6481/6482（OCEAN 2 HD-P3-5K0/15K-G2/15K-G2F）→ `ecoflow-ocean2-hd-p3-s2`（同线已绑定兄弟 3555/3574-3576 的家族）
  - 6483-6488（OCEAN 2 HD-P1-…-S2）→ `ecoflow-ocean2-plus-hd-p1-s2`（同上）
  - 6321 GW125/261-ESA-LCN-G10 → `goodwe-esa-lcn`（型号自带系列名 ESA-LCN；注册表无此系统）
- 覆盖：106/106 已发布商品。

## 5. 文档清单 `_linker_documents`

- 96 件绑定商品：注册表 `technical.documents`（url/title/kind）原样带入，`type` = kind（datasheet|manual|warranty|document），共 195 条；全部是我们托管的 URL（对 host-map 校验）。
- 10 件无绑定商品：商品自身 `_delinker_datasheet_url`/`_delinker_manual_url`（canonical 化为 `https://de-linker.com/...`），title 由文件名生成，type 按字段。
- `lang` 由标题机械推导：含 DE 标记（`\bDE\b`、Datenblatt、Handbuch、`(DE`、`-DE-`、`_DE_`、Kompatibilit…）→ `de`；ES 标记 → `es`；其余 → `en`（170 en / 7 de / 18 无标记按 en，无标记多为 GoodWe 英文保修文档）。规则保守：德语标记显式才判 de。
- 这是 feed `documents[]` 与后台元箱"文档下拉"的唯一来源。

## 6. compatibility.json 的翻译

228 格 → 248 对（20 条型号级 model_constraints 拆为独立条目并排在家族条目之前，首条命中即裁决）：

| 旧状态 | 新 verdict | 数量（基条目） | 条件 |
|---|---|---|---|
| `listed` | `released` | 29 | constraint（+model_constraints 拆分） |
| `listed`（配对须经另行销售的部件） | `released_with_accessory` | 2 | 附件要求为第一条条件 |
| `one_way` | `released` | 7 | 单边列名 + 另一家保修范围为条件 |
| `not_listed` | `190` → `not_released` | 190 | "所引文档未列此配对，不构成不兼容论断，也不对未查文档作任何主张" + warranty 文本（如有） |

`released_with_accessory` 的两格（判据：文件的原话使配对本身经由一个单独售卖、且不在任一配对商品交付清单里的部件）：

- `eco-po|eco-ocean2-bat`（H2 格同理由）→ 实为 `saj-h2-t3|saj-bat` 与 `eco-po|eco-po-b`：
  - **SAJ H2 + B2/BU2**：B2 只能作为"1-5 个 BU2-5.0 模块 + 1 个 BC2-HV1 控制模块"的整套使用（B2 手册 V1.2 p5），BC2-HV1 是单独商品；
  - **EcoFlow PowerOcean（单相）+ EF BD-5.1-S1**：单相手册 p1 写塔 = "EF BD-5.1-S1 × N **with EF BD-B-S1 × 1**"，底座是单独商品（1990）且电池本体交付清单不含它。
- EcoFlow OCEAN 2 三相 + 电池的 EF BD-JC-S2 接线盒只是多塔级联才需要 → 记为 `released` + 条件，不改 verdict；ESA 的"电池扩展件"同理。

保留而未迁移的旧字段：`stack_range`/`stack_source`（电池商品自身的 `modules_per_stack_min/max` 图值承担）、`battery_label(_de)`、家族 `delivery_contents`/`meter_documentated`（电表问题属 #13/#14 的配件加购规则，来自旧合同的家族级数据，届时从旧仓库同一只读来源再取）。`constraint`/`constraint_de`/`warranty`/`warranty_de` 全部保留为 `conditions`/`conditions_de`（并行数组）。

模式语义：旧匹配是对每个 pattern 做**不带外层锚点的 preg_match**（模式自带 `^`/`$`）；新文件多模式家族合并为 `(?:p1|p2)`，每个模式保留自己的锚（`^SAJ BU2-` 前缀语义不变）。匹配对象是 `"<brand> <model>"`（pa_brand 与 pa_model 的 term name）。37 份文档的 URL 全部是我们托管的（对 host-map 校验，37/37）。

## 7. 与 #7 的次序

切换（#17）时数据包按 **7-facts → 8-engineering** 顺序执行：#7 改正 1959 的两键并带引用，#8 的包对这两键**不含任何条目**（`SEVEN_OWNS`），互不干扰；两包都幂等，重复执行收敛到同一状态。本地演练正是按此顺序做的。

## 8. overlay

引擎需要的非商品元件经全量核对只有 **1 条**：`mat_trina_solar_tsm_460neg9r_28`（参考光伏组件，业主 2026-08-10 裁定不售组件；串列设计与屋面排布仍要对一块真实组件取值）。30 条图值全部带引用（Trina Vertex S+ NEG9R.28 数据手册 EN 2024_C p2），2 份文档（EN+DE 数据手册）。规格说"约 3 条"，实际：
- 其余 46 条无 Woo 绑定的材料里，`fixed_system`/`battery_system`/`storage_system` 34 条是已发布模块商品的组合（ESA 塔、PowerCube 系统等，由引擎按模块图值组合）；
- `mat_trina_solar_tsm_450neg9r_28`（450 W 上代）2026-08-10 已弃（德国渠道无货）；
- `mat_linker_svc_ac_board_01`（现场定制的并网/开关箱占位）无任何规格与文档，不属工程数据。

## 9. feed 的实现决定

- `figures` 只含带"我们托管 URL"引用的条目（验收"无引用的值不进 feed"）；每条只发 `{value, unit, citation}`（存储侧的 `evidence_refs`/`value_de` 不进 feed）。
- `?since=` 在服务端把时刻归一化为 **GMT 朴素串**再进 date_query：WP 会把带偏移/Z 的时刻按站点时区（本站 +08:00）再解释一次，对 `post_modified_gmt` 列比出错误窗口（实测 `2026-10-10T02:40:00Z` 曾返回 0 条）。不可解析的 `since` 是 400（validate_callback）。
- 顶层 `compatibility_version` = `data/compatibility.json` 的 sha256；`overlay` 为 overlay 文件内容原样。
- 实例依赖注意：Polylang 启用但商品无语言时，语言过滤会把全部商品从查询里剔除（`0=1`）——这是 #9 的 setup（`wp linker-i18n setup --assign`）负责赋语言之后才成立的状态；本票演练时按 #9 的工具补齐。

## 10. 后台图值引用元箱

- 标准产品编辑的一个元箱，每个图值一行（键只读、值、单位下拉、本商品文档下拉、页码）；无引用的行有警告图标。
- 改值/单位而未同时给出文档+页码 → 拒绝该行（保持原条目），重定向参数带被拒键名并出错误通知；给全引用的改动照常写入。元箱不改键名、不增删键。

## 11. 本票不做（复核规格"不做"）

不生成任何投影；不保留 `_delinker_type`/registry kind（feed 的 `device_class` 来自商品分类，经 #7 的 SelectionFacts 同一读取）；不改 SKU/名称/描述/价格/库存（write 的 protected 校验在本地演练中 0 变更）。
