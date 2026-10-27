# 全产品事实来源：精确绑定库存与新快照输入

2026-10-23（北京时间）。本轮只读 p548、本机托管文件及既有公开源记录；未改产品、数据库、设置或部署。承接 [FACT-INTAKE.md](../2026-10-23-capability-inputs/FACT-INTAKE.md) 已完成的 29 项设备事实，不重复审查它们的值或工程结论。本报告处理的是**原始事实如何保留、引用到底指向哪份字节、哪些绑定仍未成立**。

**可以建立新来源注册表，但不能把现有字符串 feed 放宽后当作工程放行。** 已形成 [registry-bootstrap.json](registry-bootstrap.json)：106 个 canonical 产品的原始 meta hash、80 个实际文件版本、38 个精确 PDF alias 及分级解析状态。23 个 alias 已有“精确源记录名→记录 SHA→托管清单→当前 p548 字节 SHA”的身份闭环；其余 15 个保留声明、候选或未决。文件身份成立、文档中的型号/页被审过、某字段成立、设备/项目放行，是四个不同结论。

## 1. 本机实际状态与覆盖量

实际 `GET http://127.0.0.1:9347/wp-json/linker/v1/engineering-feed` 于 `2026-10-22T18:07:39Z` 返回 HTTP 200，原响应 475,627 字节，SHA `03b690429303da5a8494760cdee18d910df5c8319e422042db21901a28d630f8`；`schema_version=1`、106 个唯一产品 ID。保存的 [p548-feed-public.json](p548-feed-public.json) 仅含本任务的公开产品字段及原响应身份，未复制兼容合同/overlay。其兼容版本为 `5d2a85676432d1501620997a21359782defcd8aa64b644c7799eb32d054a23b8`。

随后只读采集这 106 个 ID 的原始 `_tv_b2b_figures`、`_linker_documents`、语言配对及修改时间，见 [p548-source-public.json](p548-source-public.json)。全部 canonical ID 当前为 EN，各有唯一 DE 配对；没有把 DE 产品再数一次，也没有把 `value_de` 计成第二条事实。品牌分布为 GoodWe 49、SAJ 34、EcoFlow 21、Pylontech 1、Chint 1。这里不是全站含草稿/翻译的产品总数，也未核对 DE 原 meta 与 EN 是否同步。

实际加载的 `EngineeringFeed` 路径解析到本工作树，SHA 为 `320ac163dac1d84531761fc9dcc6dcffd746268368d2f35c6048fd88a70bd78e`。静态文件采集时 HEAD 为 `37198e86d3bb93c41a06360d8d34bbb15a1ded2b`；父线仍在实施，相关源文件各自 SHA 已保存，不能只依赖后来变化的 HEAD。第二次 feed 读回于 `18:19:12Z`，公开产品投影内容 SHA 与首取均为 `9e625141d35918613f45b2cbdcab221531f5daf5f5656fec323a50ec9ca4748e`，内容一致。[machine-readback.json](machine-readback.json)、[binding-summary.json](binding-summary.json)

收尾另于 `18:24:14Z` 只读复取全部 106 个产品的两个原 meta 字符串 SHA，与首取逐项相同，差异产品为 0；这是捕获期间的稳定性读回，不冒充数据库事务快照。[原 meta 读回](machine-readback.json)

| 全源范围 | 实测数量与含义 |
|---|---|
| Woo 原图值 | **2,482**；每条原字符串、unit、citation、evidence_refs、条件及本地化值完整保留 |
| 当前 feed 图值 | **610**；原来源不是只有这些值 |
| 原 citation 形状 | **1,137** 条 `{doc,page}`；**610** 条 `{url,page}`；**735** 条没有 citation |
| 735 条无 citation 的细分 | **518** 条仍有 evidence_refs；**217** 条连 evidence_refs 也没有。不能把 735 全部当成没有任何源线索 |
| evidence_refs | **2,140** 条图值携带、共 **2,148** 个引用项；有多个文档共同支撑同一字段的实例 |
| 原字段保留 | qualifier **4** 条、note **3** 条、value_de **429** 条；不是它们之外的事实就没有运行条件 |
| citation.doc token | **34** 个不同 token，其中一个实际是 URL；不能把它当普通文件 alias |
| PDF alias | 综合 citation.doc 与 evidence_refs，**38** 个非 URL PDF alias；不含 3 个不透明集合型 token |
| 产品文档 | `_linker_documents` **210** 条，声明 lang 为 EN 203 / DE 7；URL 去重后 **63** 份 |
| 当前全部源 URL | citation、产品文档、URL evidence_refs 与明确迁移映射的并集 **71**；原 citation.url 自身只有 **29** 个不同 URL |
| 当前字节 | 71 个文件全部存在，均成功读取 PDF 元数据，**71 个不同 SHA**；流式 hash 549,966,707 字节，未复制 PDF、未全量提取正文 |
| 补充可注册原件 | 精确既有 alias/SHA 清单另补 **3** 份；既有已核研究另有 **6** 份未出现在当前 71 URL 并集中；合计 **80 个不同字节版本** |

这里的 71/80 是明确集合的计数，不能混称为整个 uploads 或全站全部文件。原件路径、字节数、SHA、物理页数及每次引用位置见 [document-inventory.json](document-inventory.json)、[additional-recorded-alias-documents.json](additional-recorded-alias-documents.json)、[additional-reviewed-documents.json](additional-reviewed-documents.json)。

## 2. 哪些绑定真实存在，哪些只是关联

使用三类明确证据，未使用模糊文件名、品牌相同或“看起来同一系列”推断：

1. **精确历史源身份记录 + 当前字节。** 本机既有公开 evidence manifest 的 `file`、`recovered_from` 末段或 `also_cited_as` 精确命中 alias；记录带 SHA，托管清单以相同 SHA 指向 URL，本轮再 hash p548 文件。仅提取这部分公共数据，不继承原系统的代码、规则或放行状态。25 条记录涵盖 23 个 alias，均匹配当前文件；两个重复记录没有增加 alias 或版本数。[recorded-alias-evidence.json](recorded-alias-evidence.json) 保留原数据文件位置、完整源文件 SHA、匹配字段、记录 ID 和目标 SHA。
2. **仓库中明确声明的迁移映射。** `tools/migrate/8-engineering.json` 的 `basis` 精确写 alias/page，同行写托管 citation URL；在本 106 ID 范围提取到 590 条此类关联。它证明“当时声明要如此绑定”，不单独证明 PDF 型号、地域和每个字段都正确。真实例子可从 [该文件:977](../../../tools/migrate/8-engineering.json#L977) 的 H2、[该文件:3217](../../../tools/migrate/8-engineering.json#L3217) 的 BAT-C 及 [该文件:1445](../../../tools/migrate/8-engineering.json#L1445) 的 EcoFlow 查看。
3. **同字段引用共现。** 486 条 alias evidence_ref↔citation.url、21 条 citation.doc↔URL evidence_ref。它们只能先登记为支持同一字段的关联候选，不能直接升级为“同一文件”。所有 1,097 条声明、32 个 alias/URL 对及 JSON pointer 见 [binding-claims.json](binding-claims.json)。

最终 38 个 alias 的两个维度分别保留在 [alias-inventory.json](alias-inventory.json)：`raw_association_inventory_state` 是原始关联的数量/目标状态；`resolution_state` 是补入字节证据后的状态，不把二者混成一个布尔值。

| 最终状态 | alias 数 | 可消费边界 |
|---|---:|---|
| `recorded_alias_identity_sha_matched` | **23** | 精确源记录与当前字节身份闭合；仍不等于字段含义/型号适用/工程放行已核 |
| `declared_target_has_prior_selected_model_page_review` | **3** | ET75–100 表、BEU B2 表、ESA261 表存在明确目标和既有 SHA/选页依据；可为新注册表明确策展，不能声称已比对过原 alias 的独立文件字节 |
| `declared_association_candidate_only` | **9** | 有明确同行关联，尚缺独立身份或适用性核验；保留候选，不能直接绑定 |
| `unresolved_with_exact_name_locator_lead_only` | **2** | ET50–100 V1.3 手册、SEC3000C 表有精确名的托管定位线索；没有本次所定义的已声明 alias 等价记录。精确名是线索，不是原件身份凭证 |
| `invalid_co_support_as_identity_has_reviewed_locator_lead` | **1** | ESA5–30 V1.5 手册与 STS 数据表的共现，若当作等价会产生物理页越界；真实手册另有已知位置 |

对 1,137 条 doc-only 图值，按主 citation 的源身份计：889 条落在已匹配字节身份的 alias，96 条有既有已核目标声明，131 条仅候选，20 条只有精确名定位线索，另 1 条把完整 URL 放在 doc 键里。这是补齐来源链的覆盖量，不是 889 条值均被逐条工程验证。[figure-source-index.json](figure-source-index.json)、[binding-summary.json](binding-summary.json)

## 3. 真实案例与可直接采用的边界

**ESA261（6321）**：15 条原图值均以 `GW_ESA-261kWh_Datasheet_EMEA-EN_V1.1.pdf` 为 doc，同时 URL evidence_ref 明确指向同名托管路径。本轮文件 SHA `c95aef48b1ea4fbd0ae8729c104774ce2b5ee7137809fc8fe20642be2780bbfe` 与 [document-inventory.json](document-inventory.json) 的 S09 记录一致；该目标与已核 S09、`case-facts` C01–C11 的相应源引用连接。其价值是可以将旧字符串引用转成明确 document version/page，而不是从文件名重新猜功率/能量；各事实究竟使用哪些 S09/S10/S11/S12 页，继续按既有 fact record，不把 S09 一份表代替所有工程资料。[既有事实记录](../2026-10-23-capability-inputs/case-facts.json)

**H2（4107 等）**：`saj_h2_10_30k_datasheet_eu_en.pdf` 在独立源身份记录中带 SHA `0f0e75ad3f318318d1ba3f1d84a0f2c1f4864555b2deb45f4a1d0fd4cfa7acd7`，与 p548 的 `H2-10-30K-T2T3-datasheet-EN-BEU.pdf` 相同。迁移声明与当前 raw 引用另作交叉证据；S13 p2 的已核 H2-10K-T3 条件可以继承其明确范围，不能因别的 H2 SKU 引用同表就自动扩大已核字段/型号集合。[源身份记录](recorded-alias-evidence.json)、[既有事实记录](../2026-10-23-capability-inputs/case-facts.json)

**B2/BU2（1832/2067/2068/2090/2092）**：AU alias 有精确源身份链，SHA 为 `99c1d10fae6486e314e4aa6a3767b664aa5637ce88eb2bfddbf8e11cbb85367b`；BEU 目标 SHA 为 `74d86778ee033622d64deeb3bc2f0017e814f1cecd3a484c491c939be9529a2a`，二者不同。实际产品原始字段混用 AU 名义量/模块数与 BEU usable 量；这里保留两个版本和已有 R02 `conflicting_document_variant_to_resolve`。不能因为 alias/页面相似，或部分值相等，就把两者合成一个“欧洲已核来源”。[既有 R02 及原件清单](../2026-10-23-capability-inputs/case-facts.json)、[原始产品字段](p548-source-public.json)

**ET80 / GW61.4（1946/1954）**：ET 表目标 SHA 为 `4f7178042e8faf03bd926dc33a5ff0b85ffcd4f46e12f1dcf86d6db10befee4d`，有明确迁移目标和 S01 p2 依据；旧 BAT-C alias 另有精确字节身份链，指向 `delinker-goodwe_batc60-datasheet.pdf`，SHA `845e51ffb2801f48971c8b53941629dde1e8bc114b9b45dbc4f08c49c5ef815c`。1954/1955 的 usable-energy qualifier 是 EN/DE 结构化条件，必须完整带入；同字段引用 p1/p2 是同文件的多个定位，不能取一个页码后丢掉另一页条件。X01–X04 的端口与功率结论继续按原 fact record，来源绑定不重算或升级设备放行。[原始字段](p548-source-public.json)、[既有 X01–X04](../2026-10-23-capability-inputs/case-facts.json)

**Pylontech L260-OMNI（2003）**：旧 alias 可以由精确记录 SHA `bb6712735d77af454a30605abc5b93542f723efe3206d73eee5d73bb086a1699` 绑定至原 `OPTIMUSL260-OMNI_20240926105739A032.pdf`。但 `max_parallel_no`、`working_temp_range_c` 同时保留三份 URL：原表、另一份两页摘录（SHA `270d7e015db51b233920640cac612bdff1c461743c896124581c462709f7a083`）及 44 页 portfolio（SHA `fd58ff91d790920e22ab49f547f9e944e361e1220d3fd85ea41d63b41f89df3f`）的 p21。它们支持同一事实，不是三个同义文件。当前文档列表还含另一份两页 portfolio 摘录，不能把原 portfolio 的物理 p21 直接移到摘录 p21。此案例只完成源身份/结构核验，没有新增并机或温度工程结论。[原始字段](p548-source-public.json)、[字节/页数](document-inventory.json)

**SAJ ATS1（1178）**：旧 alias 精确原件为西语 `ATS1-Datasheet-ES.pdf`，SHA `4326828242f2a72bba05c90bc49096d7458f5d00a2846ccd88b076f786583e9d`；当前产品文档列表却是另一份 EN-BEU 表。它们不因产品相同自动同原件。本轮已 hash 到该西语文件作为额外的可注册源，尚未判定所有西语字段是否能转用英文表或其地区适用性。[额外精确原件](additional-recorded-alias-documents.json)

**EcoFlow 与 STS 的共现反例**：3582 的 `modules_per_stack_max` 同时有 `Matrix Table for Batteries and Inverters 20260713.pdf:p1` 与 BD-8 用户手册的 citation URL；不能把 matrix alias 直接绑定成手册。6530 的 `inverter_side_rated_power_kw` 原 note 明说两份独立文档，refs 是 STS 表 p2 与 ESA V1.5 手册 p339–340，citation 指向 STS 表。STS 只有 2 个物理页；若据同行引用自动换 alias，就出现可机械检出的页越界。真正 ESA V1.5 手册另有 351 页、SHA `67a7f715ca9db734edba1b4f15b50d1a29c866b172ffd1909759e0abc66c8d2a`。[binding-conflicts.json](binding-conflicts.json)、[原 note/refs](p548-source-public.json)

现有研究清单 18 份原件 SHA 本轮均匹配；其中 12 份进入当前 71 URL，并有 6 份额外研究原件。`case-facts.json` 为其中 14 个文件版本给出具名型号/物理页的具体 fact records，其余已选页文档仍应保留原选页审查范围。没有把“文件 hash 成功”升级为 80 份文档已逐页核实。[既有原件清单](../2026-10-23-capability-inputs/p548-document-manifest.json)、[registry-bootstrap.json](registry-bootstrap.json)

## 4. 新版本来源注册表与事实快照合同

`registry-bootstrap.json` 是**真实公开数据组成的研究候选合同**，不是已上线 API schema。父线可用其中 80 个精确版本、23 个已闭合 alias 及全部未决记录启动 compiler，剩余状态继续显性存在。建议分离以下实体：

| 实体 | 必须冻结的内容与边界 |
|---|---|
| `DocumentVersion` | `content_sha256` 为身份，字节数、媒体类型、物理页数、精确 hosted locator；URL/文件名/产品列表的 title/lang 只是定位或声明元数据。相同 URL 换字节即新版本；页定位必须属于该 SHA。 |
| `AliasBindingClaim` | 精确 token、源快照/命名空间、候选 document ID、关系类型、原 JSON pointer、证据与解析状态；共同行为关系不能冒充文档同一性。 |
| `SourceReview` | 文档 SHA、明确型号/地域/版次、物理页/表格定位、事实记录 ID 与审查范围；与字节身份独立。未知项保持未知，不从文件名生成适用国。 |
| `ProductFactSnapshot` | canonical ID、SKU/model/brand、translation IDs、原 meta 字符串与 UTF-8 hash、原 entry hash；完整保留 value/unit/value_de/citation/evidence_refs/qualifier/note，区分缺失、null、空值与明确 0/false。 |
| `ResolvedSourceRef` | raw reference、解析后的文档 SHA/物理页或 range、resolution status；未解引用必须仍能返回原 token 和候选/失败理由。多个支持源用数组保存，不静默选首个。 |
| `TypedFact / Capability` | 在上述闭包上由专门 compiler 得到量纲、计量边界、端口、方向、条件、拓扑与适用范围；可追溯转换/推导。字符串可解析、来源可定位、数值被支持、工程约束通过分别记录。 |

对 518 条只有 refs、没有 citation 的原图值，也可以构造明确的多来源引用结构；不要求伪造一个 citation.url 才让原信息存在。3 个集合型 token（`goodwe_hca_etr_docs_2026_07_28` 等）只有组名，不自带文件/页，保留为 `unresolved_source_group`，不能由模型挑一个产品文档填上。一个完整 URL 被放入 `citation.doc` 的实例可以作为明确语法迁移案例，保留原字段后生成 URL 型 source ref，不能将此特例放宽成任意字符串可信。

快照版本必须包含原始字段 hash、所有已绑定原件 SHA、绑定/审查清单版本及 compiler 版本；只换 `generated_at` 不应产生假“事实更新”。新运行只能使用冻结闭包，不能回头查询同 URL 的最新字节后继续沿用旧来源身份。源补齐/改版产生新事实版本，旧项目 revision/run 保留旧源和旧能力快照。复用已核 29 项时也应复用其条件和 `equipment_release` 边界，而不是只导入 value。[原事实合同](../2026-10-23-capability-inputs/FACT-INTAKE.md#7-可直接实施的事实合同与成熟模式映射)

## 5. 旧 v1 消费者与迁移影响

当前出口仍是 v1：[`EngineeringFeed.php:27`](../../../plugins/linker-commerce/includes/Products/EngineeringFeed.php#L27) 固定版本；[`figures():132–153`](../../../plugins/linker-commerce/includes/Products/EngineeringFeed.php#L132) 只允许托管 citation.url，再只输出 value/unit/citation；[`documents():333`](../../../plugins/linker-commerce/includes/Products/EngineeringFeed.php#L333) 另投影产品文档列表。完整原字段不会因 URL 解析成功自动贯通。

当前 schema 的 product/figure/citation/document 均有严格字段约束，citation 必须有 URL；figure 不接受 qualifier、原 refs 或 source hash。Python [`Figure/Citation` 与 `_figures():44–79`](../../../services/engine/src/linker_engine/products.py#L44) 只构造既有字段；[`Products.from_feed():255`](../../../services/engine/src/linker_engine/products.py#L255) 先验证整个 feed。同步器 [`sync-feed.py:203`](../../../services/engine/ops/sync-feed.py#L203) 明确只收 schema_version=1，并用发布环境加载器验证后替换；不能直接改同 URL 返回新形状而称消费者已支持。[feed.schema.json](../../../services/engine/schemas/feed.schema.json)

实施应新增明确版本的 raw/source snapshot 与 typed capability 合同，先让新注册表/编译器和真实 project/worker 读取同一冻结版本；现有 v1 消费者继续有明确的旧投影或接口适配，直到真实消费者迁移与回读通过。避免仅删 `additionalProperties=false`、在 v1 偷塞新字段，或只对缺失 alias 一律选第一个 PDF。后两种会使字段继续丢失，或使错误映射被静默“成功”。本轮没有改变旧 v1 的行为。

验收应至少包含：106 ID 全覆盖且语言不重复；原 meta 的每项 refs/qualifier/note 无损；23 个精确 alias 的 hash 身份重现；AU/BEU 不合并；Pylontech 多源不塌成单 alias；STS/ESA 的错误等价因物理页越界而拒绝；未决来源在新 API/报告可见；原件换字节会生成新版本，旧 run 仍读旧源；所有 v1 消费者的明确迁移及新项目实际消费均有证据。完成这些之前，不能把此库存或一次编译成功当全 SKU 能力放行。

## 6. 交付文件及不足

- [binding-summary.json](binding-summary.json)：计数、源文件 SHA、语言去重、两类 alias 状态与当前引擎源版本。
- [p548-source-public.json](p548-source-public.json)、[p548-feed-public.json](p548-feed-public.json)：实际公开源与运行投影；不使用 tests fixtures 代替机器状态。
- [document-inventory.json](document-inventory.json) 及两个 additional 文件：80 个版本的本机 SHA/定位/页数依据，无 PDF 副本。
- [recorded-alias-evidence.json](recorded-alias-evidence.json)、[binding-claims.json](binding-claims.json)、[alias-inventory.json](alias-inventory.json)、[binding-conflicts.json](binding-conflicts.json)：身份、声明、候选和冲突分开，原记录可追。
- [figure-source-index.json](figure-source-index.json)：每条图值的原 source pointer、entry/meta hash、原 citation/refs/qualifier/note；完整原值仍在 raw source。
- [registry-bootstrap.json](registry-bootstrap.json)：具体候选注册表与 canonical 产品原字段指针；未决没有被删掉或伪装成已核。

边界：本轮未重新访问生产站、未做新外网查询、未全量读取 PDF 正文、未验证 80 份全部型号/页面/欧洲适用性，也未重复 29 项设备事实。来源解析仍有 15 个 alias 的不同层次未决；217 条图值既无 citation 也无 refs；EN/DE 原 meta 的同步和源文件今后的发布读取仍需各自验收。这些缺口应由新合同保留并显示，不能因库存报告完成而消失。
