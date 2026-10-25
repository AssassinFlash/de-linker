# 最新实际知识索引审计

审计对象为正常 worker 发布并已由实际 Genie 进程打开的 `20261023T175743Z`，source
`71567ab3481a9dcb25193ba185a764d441019705a764b71207a3c577ee14c4ed`。发布目录为
`/Users/chesterjohn/de-linker-local/publication614/knowledge/20261023T175743Z`，builder
目录为 `/Users/chesterjohn/de-linker-data/index/builds/20261023T175743Z`。

本次直接只读 SQLite、对应 corpus 与主线保存的实际进程/HTTP/Woo 回执。查询显式
关闭 encoder，使用 BM25；没有 provider、dense、模型回答、重建、OCR 或原件修改。
旧 `knowledge-current-audit.*` 对应 `163526`，原样保留。本文件及配套
[JSON](knowledge-final-audit.json) 只描述这一最新实际版本。

| 核验 | 当前实际结果 |
| --- | ---: |
| 原始 Woo 产品 / 资料 | 86 / 144 |
| Genie 普通产品 / 资料 | 85 / 142 |
| 资料与产品关联 | 608 |
| 全部资料块 | 10,906 |
| scope proof / runtime 许可块 | 769 / 769 |
| 满足检索条件的许可块 | 705 |
| 有可用资料依据产品 / 无可用依据产品 | 70 / 15 |
| 已覆盖关联 / 未准备关联 | 215 / 393 |
| 资料完整覆盖 / 部分覆盖 / 无安全段落 | 66 / 10 / 66 |
| PDF 已索引 / 解析失败 | 142 / 0 |
| 原 632 题至少一个期望页有可用许可段落 | 148 / 632 |

发布文件与 builder 文件均为 156,868,608 bytes，二进制 SHA 相同：
`dd493a365d64b96d26587f05cfa9f9734153202506ff8042db0e8ff8050543c6`。
corpus 与 SQLite 的全部块 ID、正文、header、页码、section、类型、语言、token 数、
chunk product IDs 及完整 scope proof 一致。所有发布产品 revision 与该次 Woo manifest
相等，全部 runtime 许可均通过当前快照重新计算。

[主线实际回执](knowledge-final-loaded.json) 的 index version 与 source revision
同发布 manifest、builder corpus、SQLite 及记录的 HTTP 源摘要一致。实际进程的
70 个 `product_id → product_revision` 与索引 ready 集合、Woo 原生
`loaded_products` mapping **逐项相等**。全部 393 条诊断也在索引、进程 loaded 与
Woo 回执间逐项相等。`preparation_complete=false`，Woo 状态为 pending，lease 为 0，
保留可重试的未完成准备状态。本次审计复用了主线已记录的 HTTP 读回，没有自行调用站点。

## 许可与准备覆盖

769 个 proof 分布为 passage 434、document_model 43、table_columns 25、common_terms
49、section_model 152、section 38、manual_peripheral 1、woo_document 27。
相较旧 `163526` 的 771 个 proof，当前数量变化不等于回答退化或准确率：原错误
直接段落许可被拒绝，同时正确的完整列参数与有原文角色的外设引用获得证明。

393 是 **608 条资料—产品关联中的未覆盖关联**，不是 393 个产品或文件。涉及
77 个产品、76 个文档 identity，全部为 `no_proven_passage`：327 条所在资料没有
任何产品可用的安全段落，66 条所在资料对其他关联产品有依据，但未覆盖这一关联。
没有 `document_unparsed`。诊断集合与按实际 runtime 许可重新计算的缺失集合完全一致。

无知识依据的 15 个产品仍为 SAJ H2/HS2/HS3，ID 为 1179、1181、1182、1183、1184、
1185、1186、1187、2063、2064、2198、2199、4107、4108、4109。这描述知识索引覆盖，
不代表 Woo 产品下架，也不评判其他产品事实入口的能力。

工程参考产品 8369 及其两份专用资料未进入 Genie 的普通产品、资料与 scope。
705 个可检索段落中，正文含字面 EcoFlow 的数量为 0；字面检查不冒充全部别名或
完整语义验证。原件与保留对象未被本次审计改动。

## 固定十二题与当前原文证明

保持原先选定的十二个英文 `(model, question category)`，没有替换题目。在同一最新
实际索引上，无 guard 的期望页命中为 **7/12**，有当前许可后为 **3/12**。旧版本
7→2 与此前双文档 shadow 2→3 作为各自历史保留，不用于冒充本版本结果。

| 固定样本 | 当前无 guard 页命中 | 当前有 guard 页命中 | 当前目标片段 |
| --- | --- | --- | --- |
| `00506d0f0c-en` CHS2-29.9K-T4-X | 是 | 是 | 电表连接原句可用且实际返回 |
| `005ddc4c7d-en` BU3-5.0-TV2-PRO | 否 | 否 | 本次未证明目标片段可放 |
| `0065e3e240-en` GW261.2-BAT-LCD-G10 | 是 | 是 | 180/180 A 参数行可用且实际返回 |
| `009ea1c839-en` HS2-10K-T2-X | 否 | 否 | 本次未证明目标片段可放 |
| `00cc9d826a-en` GW125/261-ESA-LCN-G10 | 是 | 否 | G11 页不能授予 G10 参数事实 |
| `0121878b05-en` L260-OMNI | 是 | 是 | 98%（single string）片段可用且实际返回 |
| `015253f935-en` GW30K-STS-G10 | 是 | 否 | STS series 期望页当前未获许可 |
| `015d0655fa-en` GW3K-EHA-G20 | 否 | 否 | 本次未证明目标片段可放 |
| `0172d5937a-en` GW80K-ETR-G10 | 否 | 否 | 本次未证明目标片段可放 |
| `01dfea3e55-en` H2-30K-T3-DE | 是 | 否 | 混合变体表/保修期望页当前未获许可 |
| `01f767ac23-en` GW5.1-BAT-D-G20 | 否 | 否 | 本次未证明目标片段可放 |
| `0212b70d6e-en` GW61.4-BAT-AC-G10 | 是 | 否 | 泛 BMS 定义片段当前未获许可 |

三处关键检查直接使用本版本的新块与 proof：

- GW261.2 的 p.2 参数块 `027415a66a00-p2-6b052231` 为 `table_columns`，保留
  GW208.9 → GW261.2 原列顺序、原 TableItem 与 row 14；180/180 A 位于第二型号列。
  原生未知 Pack row 3 独立为 `027415a66a00-p2-e5a98a81`，仍无 scope。正文、行号与
  被排除角色锚点均同 corpus 一致。
- CHS2 的 p.27 原句块 `92b45188a10e-p27-a38b4312` 为 `manual_peripheral`，依据
  厂家正向主机适用声明和 `meter CHINT's DTSU666` 原文角色。主机主体为 1959、1960、
  1961，外设 2281 单独绑定当前 revision，不取得主机资料许可。仅在内存快照中
  撤下或改动 2281 的 revision 后，原句全部拒绝；直接按 2281 查询不能借读该手册。
- G11 数据页的全部 p.2 块都不能供当前 G10 产品 6321 使用。其 198.5 A 旧命中
  保持拒绝，没有用同 PDF 的 p.1 G10 标题覆盖局部版本冲突。

另外，HCA 当前三列参数表仍可检索；仅在内存移除伴随型号 3557 后，对目标 3586
拒绝该表。没有实际修改任何 Woo 产品、原件、corpus 或 SQLite。

配套 JSON 将旧七次命中的文字判断明确嵌在 `historical_assessment`，并保留来源与
`historical_only=true`。当前块、许可、引用匹配及真实检索结果另列；CHS2 与 GW261.2
不再沿用旧“当前不可放”结论。页命中、148/632 的期望页可用性和原文定位均不等于
答案准确率，本次没有运行 dense 或模型回答，不构成全库问答 parity 验收。

全量只读核查及上述反例耗时 7.28 秒。新报告保留实际准备/加载/回执证据与仍未覆盖
的范围，未把 pending 描述为准备完成。
