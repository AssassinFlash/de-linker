# 国家与接网文件证据：设备适用性和项目批准的边界

2026-10-27，#548 研究补充。只研究文件证据与适用域，不改变产品、代码、服务或配置，不重做数值模型和完整设备审计。沿用本目录的 **P = 一手资料、I = 本站设计推导** 区分；下文没有设备实测、现场验收或接网批准结果。

**建议建立“设备文件与适用条件”模块。单元证书可以支持指定设备、版本和条件下的证据匹配；国家参数、项目接网评估和电网运营商的批准必须另有依据。不能由“找到证书”生成整套方案或整个国家的绿色放行。**

## 1. 本轮来源与产品权威

- 当前本地已安装的 Woo 托管派生来源是 [p548 engine/feed.json](/Users/chesterjohn/de-linker-local/p548/engine/feed.json)：`generated_at = 2026-10-26T18:25:22+00:00`，`source_revision = e1773a35f189b2eec9267b9f757a55c60bd996e62df9e5d1812d90f0b8c337d4`。本轮限定读回下文四份证书；文件身份表采用这一安装版本的 `document_revision`。这不是生产商品状态的新读回。
- [planner/current-woo-product-source.json](/Users/chesterjohn/de-linker-local/p548/planner/current-woo-product-source.json) 是**历史 intake 快照**，不是当前安装 feed。其 `feed.generated_at = 2026-10-24T17:40:39+00:00`，`feed.source_revision` 与 `manifest.source_revision` 均为 `cc9e1356348df8ec0e2349971e4131d9339342ef4af2b35c2ce8ffe49916a108`；它保留初次 PDF 阅读时的附件修订与关联记录。
- 四份证书逐项比较历史 intake 与当前安装 feed，**仅 `document_revision` 变化**；`document_id`、URL、`blob_sha256`、商品关联及其余附件字段未变。因此复用 [既有文件覆盖读回](/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/initial-render-media-current-main-20261024/public-file-coverage.json) 的 `results[url].content.first_page_text`、页数与 SHA，以及先前对 p548 uploads 内 SAJ CHS2、GoodWe ET 4110/4120 原件的完整条款阅读。四份既有内容 hash 仍与安装 feed 相符，无需重新抓取或解析；下文 PDF 内容结论继续成立。没有另建产品或证书注册表。
- 外部标准、法规和机构页面全部经 **Apify** 取得，一手资料截止本次读取日。EVS 是爱沙尼亚标准机构，使用的是其 EN 标准公开 scope；没有购买、复制或声称读完付费标准全文。外部来源说明通用规则边界，不能补写 Woo 商品事实。Apify 仅用于本次研发取证，不进入客户运行链。

## 2. 标准实际覆盖什么（P）

| 文件体系 | 可以支持的范围 | 不能从标准名称或单元证书推出的结论 |
| --- | --- | --- |
| **VDE-AR-N 4105** | 低压发电设施的规划、建设、连接、运行及电气特性证明。VDE FNN 说明 DSO 会将其电网特定要求加入 TAB。 | 某型号有 4105 证书，不代表已完成当地 TAB、接网设计或项目接网流程。当前 FNN 页面已列 **4105:2026-03**；证书采用的版次必须单独保留。[VDE FNN 4105，2026-05-28 更新](https://www.vde.com/de/fnn/themen/tar/tar-niederspannung/erzeugungsanlagen-am-niederspannungsnetz-vde-ar-n-4105-2018) |
| **VDE-AR-N 4110** | 接网点位于中压网的客户设施，包括发电、储能、用电和混合设施。FNN 区分单元认证、设施认证和最终设施符合性声明；FAQ 11.2.1 另明确单元证书需要经验证的软件仿真模型。 | 单元证书不能替代设施级评估；设备端 400 V 不能直接决定接网点属于哪一级网络。FNN 的适用范围 FAQ 明确区分接网电压、单元电气特性和现场设置。[VDE FNN 4110，范围与 FAQ 11.2.1](https://www.vde.com/de/fnn/themen/tar/tar-mittelspannung-vde-ar-n-4110) |
| **VDE-AR-N 4120** | 高压客户设施的接网与运行，含储能和混合设施；存在设施证书和单独证明流程。FNN 另说明 4120/A1 对部分功率范围的简化。 | 不是只凭单台设备 kW 或证书上同时列出 4110/4120，就能选择整个项目的证明路线。该页面也列有 2026 年**草案**咨询，草案不能当成已生效要求。[VDE FNN 4120 / A1](https://www.vde.com/de/fnn/themen/tar/tar-hochspannung-vde-ar-n-4120) |
| **EN 50549-1:2019+A1:2023** | 与交流**低压配电网并联**的发电设施保护功能和运行能力；至 Type B，A/B/C 功率分界考虑各国实施；满足条件的储能包括在内。 | 不覆盖接网点选择、电网影响评估、接网规划核查；也不证明独立孤岛运行、人员安全或直流网络接入。[EVS 公开 scope，-1 含 A1](https://www.evs.ee/en/evs-en-50549-1-2019-a1-2023-consolidated) |
| **EN 50549-2:2019+A1:2023** | 对应交流**中压配电网并联**的上述要求，至 Type B，同样受国家实施和 DSO / 负责机构的具体要求约束。 | 不能将 -1 与 -2 按设备名称互换。公开 scope 中 ≤150 kVA 可用 -1 的替代路线允许 DSO / 负责机构另定门槛，因此不能做成跨国固定默认。[EVS 公开 scope，-2 含 A1](https://www.evs.ee/en/evs-en-50549-2-2019-a1-2023-consolidated) |
| **EN 50549-10:2022** | 发电单元与接口保护的电气特性型式试验及评价，可用于证明单元满足 -1/-2 的相应要求。 | **设施层面的符合性评估明确在范围外**；变压器、电缆、多单元组合仍须在最终设施中评价。评价报告应说明哪些条款已覆盖、哪些未覆盖；各成员国特定试验要求仍适用。[EVS 公开 scope，-10](https://www.evs.ee/en/evs-en-50549-10-2022) |

EN 50549-1/-2 的公开 scope 均明确：DSO、TSO、成员国或监管机构可能定义要求，国家实施、国家规则及 DSO 技术要求仍须遵守。由此可得的本站设计结论（I）是：**界面语言、项目国家、标准适用域、国家保护/控制设置和具体 DSO 应分别记录**；一个 EN 标准号不能自动展开为欧洲国家清单或出厂国家设置。上述 EVS 页面只证明标准范围，没有核实任何厂商型号具备哪些国家 profile。

## 3. 德国项目证明仍有独立条件（P → I）

2026-10-27 读取的 [NELEV §2](https://www.gesetze-im-internet.de/nelev/__2.html) 将项目证明置于向主管 DSO 提交的运行许可流程中。§2(2a) 对相关 Type B/C 项目规定的证明至少包括设施证书和符合性声明；这与单元证书是不同对象。§2(4) 同时存在受条件约束的例外：涉及接网点最大馈电 270 kW、同一接网点后的累计装机及有效单元/组件证书；中压或更高电压下 >270–500 kW 的路线还要求合格安装、投运的解列保护等试验记录。**不能将其压成“≤500 kW 自动通过”，也不能将旧 FAQ 的 135 kW 示例写成通用现行门槛。**

同一法规 §2(2b) 的附条件设施证书签发期限明确止于 **2025-12-31**；2026 年的工具不能因旧介绍仍可读就把该签发路线当成当前可用。§2(6) 要求运行软件更新不得覆盖 DSO 规定的电气特性。这支持把国家/DSO 设置及其版本作为独立证据保留，**并不证明任意新版固件都包含在旧证书内**。本轮据此确定证据模块边界；完整法条判定仍需规则包。

## 4. 当前安装 feed 的四份证书所示版本与配置边界（P）

| 当前 Woo 关联与文件 | 原件明确写出的适用条件 | 本轮仍无法证明 |
| --- | --- | --- |
| SAJ CHS2；商品 **1959 / 1960 / 1961**；[A3 50661614 0001](https://de-linker.com/wp-content/uploads/2026/10/SAJ_CHS2_Certificate_VDE-AR-N-4105.pdf#page=1)，9 页 | 固件 **V1.023**；CHS2-29.9K-T4-X / 30K-T4-X / 40K-T5-X / 50K-T6-X / 63K-T6-X；X 明列四组电池额定电压/容量/可用能量配置。按 **4105:2018-11、DIN VDE V 0124-100:2020-06** 测试；PDF 第 3 页为 E.4 单元证书。 | 实际候选或现场设备的固件、X 配置、国家设置；不同固件/配置是否有扩展覆盖。证书列出的 40K、63K 型号不能据此变为新增 Woo 商品。 |
| GoodWe ET；商品 **1946 / 1947 / 1948 / 6506**；[A3 50694726 0001](https://de-linker.com/wp-content/uploads/2026/10/GW_ET-75-100kW_Certificate_VDE-AR-N-4105.pdf#page=1) | GW75K-ET-G10 / GW80K-ET-G10 / GW99.99K-ET-G10 / GW100K-ET-G10；固件 **010101**；**4105:2018-11、0124-100:2020-06**；细节引用报告 CN25J408 001。 | 未核实现场固件或报告完整条件；不能凭同一品牌、ET 字样或功率相近扩展到其他型号。 |
| 同一组 GoodWe ET 商品；[SGS 250008RECO14-CER](https://de-linker.com/wp-content/uploads/2026/10/GW_ET-75-100kW_Certificate_VDE-AR-N-4110-4120.pdf#page=1) | **Type 2 / Grid following**；同四款 ET 及文件另列的 BT；软件 **010101**；**4110:2023-09 + Corr.1:2024-11**、**4120:2018-11 + Corr.1:2020-10 + A1:2024-04**。验证模型为 `GW100K-ET_VDE_PF2024e_v1_0.pfd`，MD5 `D0271364D1E5A49F96D5F558D1299C78`，平台 PowerFactory 2024。必要时须另装试验端子排。 | **当前附件只有 1 页**；正文写明另有 **164 页附录，revision 0，2026-01-30**，其配置/辅助设备/单元特性细节本轮没有。模型文件也没有因封面列名就得到核实。文件列 BT 不构成新增商品或 grid-forming 证明。 |
| GoodWe ESA；商品 **6321**；[A3 50714939 0001](https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_Certificate_EN-50549-1_EN-50549-10.pdf#page=1) | 型号 GW125/261-ESA-LCN-G10、G11；固件 **010101**；印刷标准为 **EN 50549-1:2019+A1、EN 50549-10:2022**；引用 CN25QGUM 002。 | 当前 Woo 关联商品为 G10；不能借文件新增 G11。封面没有列各国参数、全部试验条款覆盖或项目批准；A1 未在封面印出年份，不自行补写证书的 A1 年号。 |

上述 TÜV 符合性证书均将结论限定于指定产品样本及所列评价要求，且说明不包含生产评估。历史 intake 中另一份同样由 Woo 标为 `type=certificate` 的 [GoodWe ET EU Declaration of Conformity](https://de-linker.com/wp-content/uploads/2026/10/GW_ET-G10_EU-Declaration-of-Conformity.pdf#page=1) 列的是 RED / EMC / LVD / RoHS 等产品合规事项；此次四份证书的安装读回不扩展到该声明。**附件类型 `certificate` 不能单独区分产品声明、单元并网证据和设施批准。**

**版次缺口：**当前 FNN 4105 页面已列 2026-03，上表两份 4105 证书采用 2018-11。本轮取得的公开页面没有解决旧版证书的过渡承认、存量项目条件或具体 DSO 接受情况。应记录“版次/过渡适用性未核实”；既不能自动声称符合 2026-03，也不能仅凭年份将证书判为无效。本轮也没有访问签发机构实时证书状态库，PDF 印出的日期/有效期不等于当前有效状态已核实。

### 可复用的文件身份（当前安装 feed 版本）

以下只引用安装 feed 中已存在的四份附件，`document_revision` 为上述 `e1773a35…` 来源的值；历史 intake 修订保留在 `cc9e1356…` 快照中。内容 hash 未变，所以复用先前 PDF 阅读；修订变化不能被当成内容变化。它们不是第二份可维护的产品源，商品、语言映射、角色和后续修订仍由 Woo 托管发布链提供。

| 文件 | `document_id` | `document_revision` | `blob_sha256` |
| --- | --- | --- | --- |
| SAJ CHS2 4105 | `doc-4f3d3b63dd9e58a25d7e0fd44f778e5f9401022e5f910bf77bf5da474acf6b8b` | `da29517746432b6e96dee64922c3f5a7b9b8c332af1f024d6fe4f0c3ebe3f019` | `71ac1076d3160e19eeb404cffec54b9472e2ed893f70f69260ded32ab8fba6e2` |
| GoodWe ET 4105 | `doc-b11bf27e66e770e8dbd27085b04d6a43fdf55e351f345615471c69f80eec0f68` | `6b735253bea97d7e386006776d2cca58c452389d4809e6820bd85eab37b729b8` | `d7b7f3908f84c129234d5de8edc78dbe3893cfde03bba0c953d231fff72dcdd4` |
| GoodWe ET 4110/4120 | `doc-2228549d7c1dacdd30ac0601dc5950b8bdc078e13c6069cc5519229e4ad77716` | `d9dc34c2583e5f894d87ea5a80a087e58ac68a3929f40a53da6fa895c4a9b11d` | `da4d0f336bb0b6e7828ad18f4e89534698383d0191c28a4c4dedbb7a94f4c61f` |
| GoodWe ESA EN 50549 | `doc-3b8ae1df39b5bc7097b9b472943657c8e593c5180ff748e6c11be1c2b7663aad` | `8b7fc38ac40a1900915ffa2ed25b869650581ca08fa645b69cfaec706d9dfff8` | `10bd9539a35d41b054917e25f28be161a2d606e2b4fde83ad22633f701515aab` |

## 5. 文档证据模块的最小职责（I，待实现）

1. **沿用 Woo 权威编译证据。**输入为当前允许消费的 product/document ID、商品修订、附件修订与内容 hash。先按原文分为产品声明、单元/接口保护证据、设施证书、试验/投运记录及 DSO 文件；不能由文件名、证书数量或 `type=certificate` 直接生成资格结论。摘取内容保留页码、条款和原文条件。
2. **逐条件匹配设备。**分别记录完整型号/后缀、固件或软件、已知硬件/辅助设备/电池配置、运行模式、保护/控制设置、标准版次/修订、附录与报告、仿真模型版本及签发状态核实时间。仅按文件明确的列表或范围匹配；未记录版本不猜“最新”，升级后的覆盖要有 Woo 托管的扩展/等效证据。只有配置已知且必要条件有依据时，才给相应证据匹配结论。
3. **按项目解析国家规则。**国家、接网点电压、项目/模块类型及汇总功率、DSO、申请/投运或变更日期决定待核规则包；各国规则来源独立于商品事实。保留国家/DSO 设置的来源和实际值。没有规则包或具体设置时显示待核，不能以 EN 50549 证书替代。
4. **输出范围化结果。**每一义务使用“有证据支持 / 有条件 / 信息不足 / 明确冲突”，附命中的文件、版本、条件和缺项。另列“项目接网评估 / 所需设施证明 / DSO 运行许可”的真实状态；本模块的设备文件匹配不会把这些状态改为批准。缺附件或未知固件属于信息不足；只有与明确条件矛盾才是冲突。
5. **报告与保存保留同一边界。**屏幕、PDF、BOM 和冻结 run 引用相同来源修订与结论。商品/文件下线、hash、设备固件/配置、规则版次或接网条件变化时，仅使受影响判断待复核；旧 run 仍说明当时采用的文件，当前商品/文档可见性由既有发布机制判断。示例输出为“已找到与所选型号关联的单元证书；固件、国家设置及项目接网资料待核实”，不使用“欧洲已批准”“整站合规”之类合并结论。

本轮完成的是上述边界和可引用来源。**尚未完成**各国规则包、现场版本/设置核实、SGS 附录补齐、旧 4105 版次过渡承认、签发机构实时有效性核验，以及任何项目的保护/电网评估与 DSO 许可。它们应保留为具体缺项，不由计算成功或产品文件存在抵消。

## 6. 本轮 Apify 取证索引

只保留小型索引，不复制新原始资料包；下列成功数据集可定位本轮读取。声明只采用上文实际读取的一手正文，搜索摘要、第三方评论和抓取失败条目均不作为结论依据。

| Actor / run | Dataset | 本文采用的内容 |
| --- | --- | --- |
| `apify/rag-web-browser` · `n6mAIrcwQDLLXPpqt` | `LU5VsYFFD68z2OfQS` | VDE FNN 4110 正文及 FAQ，读取 2026-10-27 00:26 UTC |
| `apify/website-content-crawler` · `2R2VuKXmckHBdysXn` | `VWy2W0qVddgaSUyZD` | VDE FNN 4120 正文，00:28 UTC |
| `apify/website-content-crawler` · `NP4zGHXhJsJs1wNKD` | `MoijayZJdLwsRWMOC` | NELEV §2 现行汇编正文，00:29 UTC |
| `apify/website-content-crawler` · `aYQo3dw9vUnzuhKSV` | `XgsAcdVOWeofcAqn1` | EVS EN 50549-10:2022 scope，00:29 UTC |
| `apify/website-content-crawler` · `i2AQfhVBU0cjbVX7S` | `UtmdZdqIJes4JKyiM` | VDE FNN 4105、EVS -1/-2 含 A1:2023 的公开 scope，00:31 UTC |

取证故障已在同一通道内处理：初始并发默认内存触发账户总内存限制，后续显式用 1024 MB 的 actor 请求完成；RAG 的 raw-http 不接受 PDF，产品证书改为复用现有本地原件，标准范围读取官方 HTML；猜测的旧 4105 路径返回 404 后，经 Apify 搜索定位有效官方地址。未改账户设置，未使用普通网络搜索或其他抓取通道作为替代。
