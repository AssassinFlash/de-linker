# 共享资料适用性裁定与两处窄修

结论：原固定样本的 7/12→2/12 同时包含必要排除和真实误拒。不能把七个旧页命中都
当作正确答案，也不能把全部下降解释成下架保护的必要代价。下述两处当前型号的
厂家依据可安全自动证明，构成上线前须修的能力缺口；G10/G11 的排除应继续保留。

本次只核三个原命中。基线为 normal-worker 的不可变实际索引 `20261023T163526Z`，
source `04a8e966a46143279a81c6db3b30bbc1df45252a4f83aa8d1cc61c4339c41268`，
10,894 块、771 个 scope。关联状态指该次 Woo 快照，不冒充当前 HTTP 读回。
全程未调用当前站点 HTTP、改 Woo、改原 PDF、OCR、重嵌入或切换运行索引。

依据为 [609 规则](../../../specs/609-product-publication.md) 的共用原件条款：A 仍有
有效依据时可继续使用 A 适用内容，不能把 B 的事实或候选放出；以及
[615](https://github.com/AssassinFlash/de-linker/issues/615) 的逐块适用性证明要求。
本轮主线明确接受“主机事实主体与原文明确标注的外设引用分开绑定”的窄合同。

| 案例 | 原始页、heading、型号顺序 | 旧 proof 拒绝原因 | 裁定 |
| --- | --- | --- | --- |
| `0065e3e240-en`，1958 / GW261.2-BAT-LCD-G10 | PDF p.2；`Friendly & Thoughtful Design` 下原文 `Technical Data`；左 GW208.9-BAT-LC-G10，右 GW261.2-BAT-LCD-G10 | 同一个大块含未知 `GW52.2-PACK-LC-G10`，整 TableItem 因 blocked fragment 不继承两列 scope | 当前系统的独立参数行被误拒；可用原生行与完整列证明 |
| `00506d0f0c-en`，1959 / CHS2-29.9K-T4-X | p.4 `1.1. Scope of Application` 列 29.9K、30K、49.9K、50K；p.27 `6.5.9. Meter Connection for Single Deployment` | 49.9K 未知使整个 manual ambiguous；DTSU666 是当前 2281，却没有该主机 manual 关联；原大段还混入图中文字 | 有效主机兼容句被误拒；可按原文主机范围与明确 meter 角色独立证明 |
| `00cc9d826a-en`，6321 / GW125/261-ESA-LCN-G10 | p.1 写 G10；p.2 `Scalable and flexible C&I allin-one energy storage solution` 下原文明确写 GW125/261-ESA-LCN-G11 | 当前 G10 无权用 G11 参数表；198.5 A 在 G11 页 | 必要排除；原件对本题存在版本冲突，不自动恢复 |

## GW261.2：原表的当前型号列与未知部件行

原件 SHA `027415a66a00234f03d1268e180129fa016e601aaf1ecb7cda643a24aecb7d38`；
资料 identity `doc-56fa939acf90470677e98c7bd9729f23a31ddd53a7c66b3d65ba440ddab13ebb`，
revision `8627cceb38bde44f93992f73f09743a19e54153fc66153f0c3cba769c0dd9c95`。
1956 和 1958 均有本次 Woo 快照的实际当前关联。

原生 Docling `#/texts/27`、`#/texts/29` 按顺序声明两列。p.2 `#/tables/0`
为三列（行名加两个型号列）。原始 row index 14、col index 2 的值为 `180 / 180`，
对应行 `Max. Input / Output Current (A)`；左列为 `-`。未知型号仅在 row 3 的
`Pack Type / model` 属性行。这里的部件字段不构成系统型号列的替换声明。
原实际索引答案块为 `027415a66a00-p2-cc5c1c5c`；原文数值存在但没有 scope。

窄修保留未知部件行及原件，把该完整原生属性行独立分块并继续拒绝。其余行仍须有
完整原始当前系统列轴，proof 记录 TableItem、原始 row indices、文本摘要、header
source IDs 与被排除的部件角色行锚点。原表任一未知系统列、局部型号轴反序/不同、
缺列、缺行来源或另一未证明型号行，继续拒绝全组。旧大块不能套用这项例外。
检索返回完整两列及原列顺序，不返回未知 Pack 行。

## CHS2：主机适用声明与外设角色

原件 SHA `92b45188a10eac6d72eefc0345165b3c6ade83316555ddd6fdcf6c46cd67a262`；
资料 identity `doc-29633b9228fd277e32dada64d0647420282373a0d6a67cbad21fd72c36f86705`，
revision `83ce89032356b364e0677170f1526914842b9d400b11c8da04e7fe8334900803`。
当前主机关联为 1959、1960、1961；DTSU666 是已发布产品 2281，未借造主机资料关联。

p.4 原生 `#/texts/30` 为厂家正向声明，`#/texts/31–32` 按原序列出
CHS2-29.9K-T4-X、CHS2-30K-T4-X、CHS2-49.9K-T6-X、CHS2-50K-T6-X。
p.27 `#/texts/771` 原句：`The METER.485 port can connect with meter CHINT's DTSU666
to provide RS485 communication.` 原实际索引块 `92b45188a10e-p27-5e83f06b` 未获许可。
该 section 没有本地其他技术型号覆写。原文明确的 `meter CHINT's DTSU666` 是角色
证据；不能只凭型号相似、分类或 Woo 关联猜测。

窄修只为这一类独立非参数原文句保存 `manual_peripheral` proof：厂家正向适用声明
后的明确型号列表提供主机主体；主体必须各有当前 manual 关联。`referenced_products`
另存电表的当前 Woo revision、角色、literal quote 与 source chunk ID。它不授予电表
对主机 manual 的技术事实许可，按 2281 查询不能取到该手册。2281 草稿/版本改变、
主机关联消失、缺原文角色、未知外设、其他局部型号或数值参数都会拒绝该句。
完整源版本仍在检索后、输出前复验。

## G10/G11：保留拒绝对照

原件 SHA `c95aef48b1ea4fbd0ae8729c104774ce2b5ee7137809fc8fe20642be2780bbfe`；
资料 identity `doc-982aed912e09eb0d8ed806cf2ae483ec9cc782a57cc2d77e2d5fcfd35fb3dc03`。
Woo 当前关联的 6321 是 G10。p.2 原生 `#/texts/19` 明确写 G11，`#/tables/0`
row 24 的最大 AC 输出电流为 198.5。该表不为 G10 取得许可，不能用同一 PDF、
p.1 标题或通用 heading 盖过原文变体。此次修复没有改动这项拒绝。

## 验证边界

新增回归先在原缓存上复现两项失败（2 failed / 8 passed），再验证 scope → corpus →
实际 FTS5 SQLite → 当前 permission → BM25/邻块链路。冻结原文压缩夹具保存原解析
字节摘要，未改厂家数据。最终全量 **2,170 passed、1 skipped、195 deselected、6 xfailed**，
70.40 秒；完整 `mypy .` 194 files、`ruff check .`、`ruff format --check .` 199 files 全绿。
没有把这两项有限恢复写成全库 parity 或最终模型答案准确率。

[冻结源的双文档 shadow 回放](knowledge-scope-shadow.json) 使用实际索引的全部原块与
proof，仅把上述两份原件的 209 个块按现有离线 BAAI/bge-m3 tokenizer 重新分为
213 块，不重新解析或嵌入；其余 140 份资料不变。临时、无向量的 FTS5 SQLite
已自动删除。原固定十二题的 guarded 页命中由 2/12 变为 3/12：CHS2 兼容原句恢复，
GW261.2 仍为一次页命中，但这次真正可取得 180/180 A 行；G10/G11 继续拒绝。
原始 7→2 记录保留。这个 shadow 不是新的 normal-worker release，也不是 dense
或端到端回答测试。撤下电表 2281、撤下表格另一列 1956 及以 2281 借读主机资料的
反例全部拒绝；未知 Pack 行仍无 scope。回放耗时 3.29 秒，原实际 index SHA
仍为 `1b46bc7c164ce2ad79dad78b14006ee2917bd13d76b31978f7e8ff030e0356c2`。

已在运行的实际索引仍是上述 771 scope 版本。本代码还需由主线正常 worker 生成并
确认新的实际 loaded/ack；不能只改磁盘源码就宣称两处生产能力已恢复。
