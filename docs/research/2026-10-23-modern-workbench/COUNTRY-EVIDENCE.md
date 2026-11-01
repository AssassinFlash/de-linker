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

**版次缺口：**当前 FNN 4105 页面已列 2026-03，上表两份 4105 证书采用 2018-11。本轮取得的公开页面没有解决旧版证书的过渡承认、存量项目条件或具体 DSO 接受情况。应记录“版次/过渡适用性未核实”；既不能自动声称符合 2026-03，也不能仅凭年份将证书判为无效。初轮未访问签发机构实时证书状态库；后续仅对 SGS 250008RECO14-CER 完成了数据库状态读回，见第 7 节。其他证书仍不能仅凭 PDF 印出的日期/有效期视为已核实当前状态。

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

本轮完成的是上述边界和可引用来源。**尚未完成**各国规则包、现场版本/设置核实、SGS 附录补齐、旧 4105 版次过渡承认、其余证书的签发机构实时有效性核验，以及任何项目的保护/电网评估与 DSO 许可。它们应保留为具体缺项，不由计算成功或产品文件存在抵消。

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

## 7. SGS 250008RECO14-CER 完整附录定向追索

2026-10-27 08:49–09:20 UTC，仅追索现有 Woo 附件所指的 **164 页附录、revision 0、2026-01-30**，没有扩大产品或标准研究。

- **SGS 同号记录已核实，附录未取得。**从现有 PDF 二维码解出[专属 ProCert 入口](https://procert.sgs.com/Cert/3002712263688306/549a5f08-3a2e-4a4a-a2ed-3bdbd1f9ecce.html)，沿其 iframe 读取 [SGS 证书详情](https://procert.sgs.com/CertWebService/3002712263688306/549a5f08-3a2e-4a4a-a2ed-3bdbd1f9ecce.html)。08:51 UTC 的数据库记录与原件的证书号、2026-01-30 签发日期、四款 ET / 四款 BT 型号和软件 **010101** 一致；状态显示 **Valid**，到期日期 2031-01-30，报告号为 `250008RECO14` 与 `250008RECO14-TG4`。该公开 HTML 只有元数据，没有附件或下载链接；SGS 同时明确该网页不是证书。此状态读回不填补附录内容和项目批准。
- **GoodWe 的真实 Download 入口仍只给同一封面。**读取[官方 ET 75–100 kW 下载页](https://en.goodwe.com/download-et-series-50-100kw)，依其实际接口读取 `catid=5334`、Certificate `type=12`、DEU `country=14` 的两页，共 12 条文件名/链接。对应条目为 `GW_ET 75-100kW_Certificate-VDE4110_VDE4120`；[Preview，id=4116/type=1](https://admin.goodwe.com/En/Api/downloadFile?id=4116&mid=60&type=1) 和独立的 [Download，id=4116/type=2](https://admin.goodwe.com/En/Api/downloadFile?id=4116&mid=60&type=2) 均实际取回 **629,561 字节、1 页** PDF，SHA-256 均为 `da4d0f336bb0b6e7828ad18f4e89534698383d0191c28a4c4dedbb7a94f4c61f`，与 Woo 附件完全相同。证书号、全部八个型号、010101、签发日期及 revision 0 / 164 页附录引用均逐项匹配；不是另一张封面。该相同 PDF 没有嵌入附件或 Portfolio。查到的这两页证书文件列表也没有单列该附录；这不等于其他入口不存在。
- **具体检索与工具修复。**先查 `"250008RECO14"`、证书号配 `site:goodwe.com` / `site:sgs.com`，再查型号与 VDE 关键词；精确编号没有有效索引结果，放宽检索后转入上述官方系列页。普通内容抽取跳过 JSON，通用 Cheerio / Web Scraper actor 又返回 `full-permission-actor-not-approved`；没有变更账户权限。最终沿用已批准的 `apify/website-content-crawler`，以完整查询参数和 `saveContentTypes` 保存原始 JSON / PDF，修复读取。下载触发导航时页面统计显示 failed，原始文件实际成功存入 Apify KV；本文依据实际字节、PDF 页数和 hash 读回，不以运行状态代替文件验证。

**本次外部限度：**已核实的 SGS 公开详情只给证书元数据，GoodWe 对应 Preview 与 Download 都只给现有单页文件；没有取得附录正文，不能核实其中的配置、辅助设备和完整限制。尚无法判断完整附录是否由持有人另行提供、位于其他未发现入口或未公开，不能称其不存在。继续核对所需的明确原件仍是 **250008RECO14-CER 对应的 164 页 Annex，revision 0，2026-01-30**。外部检索结果没有写回 Woo，也不授权新增型号、资料或接网放行。本轮未对外联系；因只取得重复封面，未另存本地副本。

| 本次有效来源 / 目的 | Apify run | 实际保留的远端证据定位 |
| --- | --- | --- |
| SGS 同号详情 | `y18V1Z84FIToiChd3` | dataset `7TKZGJuhMJBQkU5Ho` |
| GoodWe DEU 证书列表第 1 / 2 页 | `qgPFmrKDCbHho1kdN` / `6IhRkhvIZao3seDgu` | KV `WETTthwY2NTURJYUT` · `file-82704b8-getfilenew.html` / KV `eaVQDw3sE5TkbU01d` · `file-13056f6-getfilenew.html` |
| GoodWe Preview 实际 PDF | `NIUQ5hdh9GeqAWaHS` | KV `CP42HAOhduugEjZEm` · `file-d145cc8-downloadFile` |
| GoodWe Download 实际 PDF | `T1nN38s6Am0ixmeLC` | KV `WopsxJMzGnf4GVvvJ` · `file-037ff3f-downloadFile` |

### 2026-10-27 19:10–19:22 UTC：当前维护关联及 ZEREZ 公共下载补查

- **先核当前 Woo，未沿用旧缺失标签。**只读查询生产 Woo 的商品 `1946 / 1947 / 1948 / 6506`：四者仍只关联上述 SGS 封面，没有单列此 Annex。媒体库中按 `250008`、`Annex`、`4110 / 4120` 定向核对，相关 ET 附件仍是 `6376`；实际服务器文件为 **629,561 字节**、SHA-256 `da4d0f336bb0b6e7828ad18f4e89534698383d0191c28a4c4dedbb7a94f4c61f`，与先前核过的单页原件相同。既有受维护资料清单与本 dossier 未提供另一份该编号的完整 Annex；这不是对所有未关联资料或当前 Genie 全部语料作不存在判断。
- **新增的公开镜像仍是重复封面。**经 Apify 的精确型号、Annex、4110 检索，取得 [BayWa 所托管的同名证书](https://solar-distribution.baywa-re.de/out/media/19_ET-G10_Serie_GW_ET-75-100kW_Certificate-VDE4110_VDE4120.pdf)。实际原件同为 **629,561 字节**、同一 SHA-256；没有补出附录，也不另保留相同字节的本地 PDF。
- **ZEREZ 的公共下载动作已定位，不能冒称取得正文。**在 [GW75K 的精确单位页](https://www.zerez.net/units/1dd4aab1-4a63-4310-6c58-08de5fee9eea)，无需登录的 `Deckblatt` 下载控件实际生成文件名 **`250008RECO14-CER_Certificate_4110_20.pdf`**。`Evaluierungsbericht` 与 `Modell` 仍显示 `Gesperrt`。本次没有打开锁定内容，也没有证据可把其中某一项等同于所缺的 164 页 Annex。
- **下载字节的剩余障碍属于采集工具。**公共控件能触发下载，但浏览器给的是临时 Blob；直接重读已撤销的 Blob URL 返回 `NetworkError`，改用下载流／页内 FileReader 后发生 Firefox `Target page, context or browser has been closed`。没有取得可校验的 ZEREZ PDF 字节，故不填写其 hash 或页数，也不把这些工具错误当成来源拒绝、附件不存在或必须私密访问的证明。完成这一有界排障后停止，没有继续扩大关键词或绕开登录。

| 新增有效定位 / 目的 | Apify run | 保留的证据定位 |
| --- | --- | --- |
| ZEREZ 公共 Deckblatt 的实际文件名、锁定分类边界 | `nvepcL3S4nkIfai2b` | dataset `x2bGqkTyXE0zIzt25` |
| 精确型号 Annex 检索，定位 BayWa 对应文件 | `xRifRGfSdu8n93HKq` | dataset `EdmY0ivObBlcbilue`；仅作入口定位，不把搜索摘要当成 PDF 正文 |
| BayWa 原始字节与现有封面 hash 相等 | `niHrlE8f21SWmU32u` | KV `tIX5TwmzRjpeexX6q` · `PROVENANCE`；重复原件已删除并读回，保留第 7 节既有 GoodWe 同 hash 原件 |
| 最后一次有界浏览器采集故障 | `OxoIFYYJkBeuNRdj0` | run log：浏览器上下文关闭；没有形成 PDF 原件证据 |

**仍缺的确切原件与下一事实：**SGS **250008RECO14-CER，Annex，164 页，revision 0，2026-01-30** 的完整 PDF，或由 SGS／GoodWe 明确指向它的合法公共 URL／已识别的 ZEREZ 附件及访问条件。现在仍不能确认该附录是否公开、是否与锁定评估报告同一文件，或是否须由持有人提供。没有对外联系、创建账号、绕过鉴权或写入 Woo／runtime；未知配置和项目适用性继续保持未核实。

### 2026-10-27 21:50 UTC 起：ZEREZ 公共下载修复及精确证书页收口

- **公共下载已修复，不再以 Blob 故障解释缺件。**复用先前单位页与真实下载控件，仅在 `URL.createObjectURL` 生成时保留原始 Blob，并阻止下载用的 `blob:` anchor 关闭采集上下文；没有修改站点请求、身份或锁定控件。实际公开请求是 ZEREZ gateway 的 `GET /api/PublicDownload/{opaque}`，返回 HTTP 200。取回的 **`250008RECO14-CER_Certificate_4110_20.pdf` 为 629,561 字节、1 页**，SHA-256 **`da4d0f336bb0b6e7828ad18f4e89534698383d0191c28a4c4dedbb7a94f4c61f`**，与 Woo 附件 `6376` 及既有 GoodWe 原件完全相同；PDF 无嵌入附件。正文明确为 `Page 1 of 1`，仍只引用而未包含 **164 页 Annex、revision 0、2026-01-30**。原始字节保留在下表 Apify dataset 的 `ANNEX_PUBLIC_FILE.file.base64`；未另建重复本地 PDF，不记录临时下载地址中的不透明凭据材料。
- **精确 certificate route 已实际渲染，壳页障碍也已排除。**读取[同一 SGS 证书详情](https://www.zerez.net/certificates/58d2552c-eb4e-4fbc-86e1-c6c5dcb135df)，实际显示同号、`Gültig / Verifiziert`、2026-01-30 至 2031-01-30，以及文件区 `Deckblatt / Gesperrt / Evaluierungsbericht / Modell`。文件区只有一个 `Download file` 按钮，未列出单独的 Annex 条目或其文件 href；同号单位页的公开 Deckblatt 原件已在上一项校验。没有点击编辑、验证、撤销、锁定项或登录入口。公开文本没有给出另两类文件的实际文件名、页数或可确认的 Annex 身份，不能把它们直接认作目标附录，也不能据 `Gesperrt` 推断目标 Annex 必须登录才可取得。

**本分支的具体结论：**原先未完成的公开 Deckblatt 下载现已完成，且精确证书页已经可读；两处都没有提供目标 Annex 原件。剩余缺口是 **164 页 Annex 本身的已识别合法文件入口／访问授权及正文**，不是采集 Blob 的技术失败。此结论只覆盖这个已定位的 ZEREZ 公共分支，不声称全网无文件、附录不存在或锁定评估报告就是该附录。本轮仅做一次修复后的公共下载和一次精确证书路由读取，到此停止；未扩搜、创建账号、付费、对外联系、绕过鉴权或写回 Woo／运行系统。后续只有取得可确认身份的原件或持有人／签发机构明确指出的合法访问条件，才可继续核查附录配置与限制。

| 本轮实际证据 | Apify 定位 |
| --- | --- |
| 已修复的公共下载、实际 PDF 字节、文件名及 HTTP 200 | run `Uee7shd3VKNNjILbJ` · dataset `pnD5NzghiAsXb2r5o` · `ANNEX_PUBLIC_FILE`；已批准 actor `apify/website-content-crawler`，build `0.3.102`，`maxRequestRetries=1` |
| 同号 certificate route 的实际渲染文件区、唯一下载按钮与访问边界 | run `4Snc6Kh2BeyWJN6zc` · dataset `c9XvsoNE2inTauZjS` · `ANNEX_CERTIFICATE_STATE`；同一 actor/build |

## 8. 4105:2026-03 对 2018-11 单元证书的过渡条件

2026-10-27，限定核查旧版单元证书继续被承认的申请/投运时间条件。**未取得能够确定该条件的正式原文，当前判断继续为“版次/过渡适用性未核实”。**本次具体来源边界如下：

- 复用[既有 FNN 4105 官方页面](https://www.vde.com/de/fnn/themen/tar/tar-niederspannung/erzeugungsanlagen-am-niederspannungsnetz-vde-ar-n-4105-2018)：已取内容确认 2026-03 版并包含 FAQ 介绍，没有提供目标过渡条款。[VDE VERLAG 的公开规范说明](https://www.vde-verlag.de/p/normen/vde-ar-n-4105-vde-ar-n-4105-anwendungsregel-2026-03/0100940-DE-PR)进一步明确其替代 2018-11 及 2020-10 勘误，但公开说明没有给出旧单元证书继续使用的申请或投运截止。**标准替代关系不能直接转成旧证书的失效日期或继续承认条件。**
- 读取 FNN 公开的[新版 Anhang F 表单原件](https://www.vde.com/resource/blob/1785304/f23a9f50f050aaad54dc4a280aa82377/vde-ar-n-4105-formulare-anhang-e-data.pdf)，实际为 23 页；这份表单材料没有补足本次所需的 2018-11 证书过渡原文，不能由新表单的存在推出旧证书的接受期限。
- 核查签发机构的[TÜV Rheinland 官方并网认证入口](https://www.tuv.com/germany/de/netzanschluss-von-pv-anlagen.html)。该页的明确日期条件涉及 **2019-04-27** 投运与 **2018-05-18** 主要部件购买的旧一轮转换，没有标识为 4105:2026-03 的过渡说明；这些旧日期不能移用于本次 2018→2026 判断。

**尚缺的明确原件：**VDE-AR-N 4105:2026-03 中针对既有 **2018-11 Einheitenzertifikate** 的过渡适用原文，或 FNN / 签发机构正式发布的对应解释，明确继续承认范围、申请/报装与投运条件及例外。所查公开入口未给出该原文，不等于没有过渡规定。本次没有新增可用于放行或判定失效的期限，也没有改变任何产品、证书或项目状态；到此来源边界停止检索。

| 本次实际采用的官方入口 | Apify 定位 |
| --- | --- |
| 复用 FNN 4105 页面 | 既有 run `i2AQfhVBU0cjbVX7S` · dataset `UtmdZdqIJes4JKyiM` |
| VDE VERLAG 2026-03 公开说明 | run `dWZlf2D8gof8pgjFa` · dataset `pGBGhyd3DPcUcxdtf` |
| FNN Anhang F 免费表单 | run `tLHzkBrvIBYyseb0O` · KV `dQYiswxE1Q9cdeCW4` · `file-7680133-vde-ar-n-4105-formulare-anhang-e-data.pdf` |
| TÜV Rheinland 并网认证说明 | run `J9E1uZJHIkDQyeOCV` · dataset `ctZr4RcJDzjZjFINQ` |


## 9. ZEREZ：四款 ET-G10 的登记读回与文件边界

2026-10-27 14:15–14:33 UTC，仅沿 [ZEREZ 官方首页](https://www.zerez.net/)的公开入口进入[单位与证书表](https://www.zerez.net/units-and-certificates)，使用页面真实搜索字段筛选 `ET-G10`。实际应用的公开 GraphQL 响应返回 **8 条**记录：四个既有 Woo 型号各有下列两组登记；本次没有扩大产品范围。

| 既有 Woo 型号 | 4110 / 4120 单位登记 | 4105 单位登记 |
| --- | --- | --- |
| GW75K-ET-G10 | [ZE-PWRY-PB3X-0001](https://www.zerez.net/units/1dd4aab1-4a63-4310-6c58-08de5fee9eea) | [ZE-XBO0-1CWG-0001](https://www.zerez.net/units/8062ecc6-2ce2-4e97-fdfe-08ddf1c90eeb) |
| GW80K-ET-G10 | [ZE-PWRY-PB3X-0003](https://www.zerez.net/units/f037a3c2-7f49-4c15-6c5a-08de5fee9eea) | [ZE-XBO0-1CWG-0002](https://www.zerez.net/units/d3f106e2-360b-46ef-fdff-08ddf1c90eeb) |
| GW99.99K-ET-G10 | [ZE-PWRY-PB3X-0005](https://www.zerez.net/units/4e8b2015-1149-4658-6c5c-08de5fee9eea) | [ZE-XBO0-1CWG-0003](https://www.zerez.net/units/26778716-46ec-46a6-fe00-08ddf1c90eeb) |
| GW100K-ET-G10 | [ZE-PWRY-PB3X-0007](https://www.zerez.net/units/5de64769-7813-4fa3-6c5e-08de5fee9eea) | [ZE-XBO0-1CWG-0004](https://www.zerez.net/units/40c733c1-ee61-4c26-fe01-08ddf1c90eeb) |

- **登记状态已读回。**八条 API 记录均为 `Valid / Ongoing`、`isVerified=true`。4110/4120 组共用 ZEREZ 证书码 **ZE-PWRY-PB3X**、证书号 **250008RECO14-CER**、证书 UUID `58d2552c-eb4e-4fbc-86e1-c6c5dcb135df`，标准为 **4110:2023-09 / 4120:2018-11**；[GW75K 实际详情](https://www.zerez.net/units/1dd4aab1-4a63-4310-6c58-08de5fee9eea)显示 SGS TECNOS, S.A.、2026-01-30 签发、有效至 2031-01-30。4105 组共用 **ZE-XBO0-1CWG**、**A3 50694726 0001**、证书 UUID `9ce0c83b-1f4f-45c7-a057-4d7456398caf`；[GW100K 实际详情](https://www.zerez.net/units/40c733c1-ee61-4c26-fe01-08ddf1c90eeb)显示 **4105:2018-11**、2025-09-15 签发、有效且已验证，限制栏未指定内容。这是当前登记状态，不能替代文件全文或项目接网批准。
- **SGS 限制全文已展开取得。**上述 GW75K 详情的完整限制说明：认证产品不提供测试端子；必要时须另装连接端子板。条件中的“必要时”保留，不扩成所有项目无条件必装，也不从这条简短限制推断 164 页附录的其他条件。该页的 `Software Version` 实际填写 **DIgSILENT PowerFactory 2024**，不能将它当成设备固件或据此补证固件 **010101** 的适用性。
- **文件入口有新定位，原件仍未取得。**SGS 单位详情给出[真实证书路由](https://www.zerez.net/certificates/58d2552c-eb4e-4fbc-86e1-c6c5dcb135df)；本次直接读取该路由仅得到动态壳页，未取得额外证书内容。单位详情文件区显示公开的封面下载按钮，评估报告与模型标为锁定；不能据文件类别认定锁定内容就是目标附录。4105 详情另显示封面及 NA 保护证书/试验报告两个下载按钮，并给出[证书路由](https://www.zerez.net/certificates/9ce0c83b-1f4f-45c7-a057-4d7456398caf)。这些按钮没有公开在 DOM 中的实际文件 href；本轮没有取得可供已批准 crawler 直接读取的文件 URL。SGS 下载尝试未捕获浏览器下载事件，因同一工具错误自动重启后已主动终止，未继续反复尝试。**本轮没有取得 PDF 字节，因此没有新增文件哈希、字节数或页数，也不由“封面”标签猜测文件只有一页。**未新存本地文件或重复已知 PDF。
- **4105 过渡缺口保持。**本次目标筛选的八条记录没有 4105:2026-03 条目；其中 4105:2018-11 当前标为有效，仍不能推出其继续承认的申请、报装或投运条件。首页表偶见其他型号的 2026-03 登记，不适用于这四款型号，也不是过渡条款原文。第 8 节的“版次/过渡适用性未核实”不变。

**收口：**本次新增了八个精确单位登记、两组证书的当前登记读回及一条完整 SGS 限制，仍未补齐 **250008RECO14-CER 的 164 页 Annex、revision 0、2026-01-30**，也未取得新文件原件、额外固件适用性说明或 4105:2026-03 过渡原文。Woo 继续是唯一维护的产品与资料来源；外部登记没有写回 Woo，没有新增型号、替换证书或形成接网放行。本次没有对外联系或绕过锁定文件。

上述“未取得文件／路由仅壳页”是 14:15–14:33 UTC 这一轮的历史采集限度。第 7 节 21:50 UTC 起的定向补查已修复这两处工具障碍，实际取回同一单页封面并渲染精确证书页；164 页 Annex 的身份、合法入口及正文缺口仍未关闭。

| 本次有效来源 / 具体限度 | Apify 定位（均为已批准的 `apify/website-content-crawler`） |
| --- | --- |
| 公开登记页与真实搜索字段 | run `tiR12zC9L9XpiyNUU` · dataset `hWPIvRHxoXVp8hRH6` |
| `ET-G10` 筛选及完整 8 条 GraphQL 响应 | run `xBzS7jww1ebRDhscF` · dataset `FGY7enFefYRIRF539`；实际接口 `https://app-zerez-weeu-gatewaysvc-prod-01.azurewebsites.net/graphql/` |
| SGS 单位详情及文件区 | run `PugHIxNc3dh4Uk9PP` · dataset `CseMdcoDa40NbyWRz` |
| SGS 完整限制展开 | run `M167kNSTV4qsK3jCm` · dataset `IONha0DlXIBL1zjWj` |
| 4105 GW100K 代表详情；SGS 证书路由仅壳页 | run `14KdJ2uExsbzN9p26` · dataset `hkVVwX8Dd9vgWHZOx` |
| 未取回文件的下载事件失败（已终止） | run `i9GkKXPYUipewJVxR` · KV `hzrta9KBHI0lZVOHK`；日志定位，不作为 PDF 原件 |

## 10. 法国、德国、荷兰：下一组可进入版本化国家/DSO 合同的规则

2026-10-28，#548 研究补充。只补国家规则层与 DSO 放行边界的证据，不改业务代码、不写产品数据、不作任何放行判断。选 FR / DE / NL 的理由是当前实例与验收夹具实际使用这三个国家（`country_code` 取值见 `artifacts/548/workbench/geometry-editor/native-saved-revision6.json`、`docs/acceptance/2026-10-22/548/import-native/1652209c/amsterdam-server-readback.json`、`docs/acceptance/2026-10-24/548/energy-workspace/*.json`）。沿本 dossier 的 **P = 一手资料、I = 本站设计推导** 区分。

**本节不证明任何型号在任一国家获准并网，也不构成全欧洲、单国或某个 DSO 的批准。** 三类项目国家只补到“法定条文层”和“DSO 结构层”；具体 DSO 的 TAB 数值、并网许可与投运记录仍缺（见 §10.7）。

### 10.1 三条必须分开的记录轴（P → I）

| 轴 | 由谁决定 | 本节可引用的证据 | 不能由此推出 |
| --- | --- | --- | --- |
| **设备单元证据** | 制造商 / 认证机构 | 本 dossier §4 的四份 Woo 附件、§9 的 ZEREZ 登记 | 项目适用性、固件/配置匹配、DSO 接受 |
| **国家规则包** | 国家法规 + 监管机构 | §10.2–§10.4 的法定条文 | 具体 DSO 的补充要求 |
| **项目并网放行** | 配电网运营商（DSO）+ 安装/投运记录 | 只核到 DSO 的法定职责与文件结构 | 任何具体项目已获许可 |

三国的一手条文都把**功率分档**作为义务入口，而不是把设备证书作为入口：FR 用 `Pinstallée`（同一接网点上可同时运行的发电机组最大有功功率之和），NL 用 `elektriciteitsopslageenheid` 的“最大可交付有功功率”，DE 用 `installierte Leistung` 与 TAB。**（I）因此国家规则包的第一键必须是“项目功率 + 口径 + 计量点”，证书只能在此之后作为单元证据被匹配。**

### 10.2 法国（P）

法定技术文本是 [Arrêté du 9 juin 2020 relatif aux prescriptions techniques de conception et de fonctionnement pour le raccordement aux réseaux d'électricité](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000042032189/)。已实际读回的条款：

- **Article 3 适用域与功率口径。** 该编适用于“持续或间歇地向公共输电或配电网络交付全部或部分发电量、或与该网络耦合”的发电设施。`Pinstallée` 定义为同一公共电网接网点上**可能同时运行**的发电机组单机最大有功功率之和；按约定，接在 **BT（低压参考域）** 的发电设施取**视在功率**，接在其他电压参考域的取**有功功率**。[Article 3](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042036844)
- **Article 34 与欧盟条例的关系及“实质性变更”界限。** 本章规定**附加于**欧盟 2016/631（RfG）的通用要求；对 Type C/D，功率增加使同步机组最终功率超过原并网功率 **20%**（含至少三台机组的水力设施为 **30%**），或使非同步机组群超过 **10%**，或导致电压等级变化，即属实质性变更。[Article 34](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042036858)
- **Article 35 的 Type 分档（法国值）。** Type A `0,8 kW ≤ Pmax < 1 MW`；Type B `1 MW ≤ Pmax < 18 MW`；Type C `18 MW ≤ Pmax < 75 MW`；Type D `75 MW ≤ Pmax`，均以 `Uracc < 110 kV` 为条件；`0,8 kW ≤ Pmax` 且 `Uracc ≥ 110 kV` 另列。[Article 35](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042036860)

DSO 侧结构（[Enedis 生产接入流程页](https://www.enedis.fr/raccordement-installation-production-electrique)、[Enedis 全部自消费页](https://www.enedis.fr/autoconsommer-la-totalite-de-lenergie-produite-par-vos-panneaux)）：

- **DSO 不唯一。** Enedis 覆盖本土约 **95%** 领土；其余由本地配电企业（ELD）负责，须先按 GRD 名录核实。任何“法国 = Enedis”的规则包都是错的。
- **三种合同框架**：CAE（需 ARPE 平衡责任归属）+ 买方购电合同、CU-I（与购电方直签）、CACSI（全部自消费不售电时与 Enedis 签）。
- **零注入也必须申报**：全部自消费的发电设施**无论功率**均须在 Enedis-Connect 申报，并接受 CACSI 的“不注入”承诺。
- **投运前必须有 Consuel 符合性证明**：在改动既有回路或**加装电池**时强制；页面写明“已组装且符合 NF EN 50549-1-4 的 plug & play 设备”可能豁免——**该写法按原文记录，`-1-4` 的所指未核，不自行改写成 `-1/-2`。**
- **投运前注入被禁止且不予报酬。**
- 接入申请档案为工程与许可文件（地籍图、总平面图、城市规划许可、功率平衡表、委托书），**不是设备证书清单**。

**（I）法国规则包的可用结论：** Type A 起点 `0,8 kW`、Type B 上限 `18 MW`、功率口径在 BT 为 **kVA**；项目级聚合按同一接网点的可同时运行机组求和。证书匹配不能改变这三项。

### 10.3 德国（P）

- **接入与拒绝的法定结构。** [EnWG §17(1)](https://www.gesetze-im-internet.de/enwg_2005/__17.html) 把“**Anlagen zur Speicherung elektrischer Energie**”明列为应接入对象，条件是“适当、无歧视、透明、且不低于关联企业同类情形”；§17(2) 允许 DSO 在证明“运营或其他经济/技术原因下不可能或不合理”时拒绝，拒绝须以文本说明理由，容量不足时**须给出为完成接入所需的具体措施与相关成本**。
- **TAB 的法定地位与效力边界。** [EnWG §19(1)](https://www.gesetze-im-internet.de/enwg_2005/__19.html) 要求 DSO 就发电设施、**电储能设施**、配电网、直连客户设施、联络线及直供线制定并公布技术最低要求（TAB），并据此纳入并网合同；§19(1a) 明确：**与通用技术最低要求相抵触的 TAB 条款无效**；对通用要求的“补充”仅在为保障该电网因技术特殊性所需的安全或可靠性、或法律要求时才允许，且**必须连同其合法性理由一并公布**；BDEW 制定的 TAB **Musterwortlaut** 与高/超高压 TAB 的补充不适用该公布义务。§19(4) 规定通用技术最低要求由电网运营商共同制定、**VDE 为受托机构**，分别依 RfG Art. 7(1)、DCC Art. 6(1)、HVDC Art. 5(1) 通过。
- **入网控制是另一条义务线。** [EnWG §14a](https://www.gesetze-im-internet.de/enwg_2005/__14a.html) 针对“**steuerbare Verbrauchseinrichtungen** / 可控并网口”以降低电网费为对价做网向控制，可经经济激励、并网功率约定或单设备控制实现；联邦网络局得以 Festlegung 规定定义与前提。
- **上网功率控制的触发是分档且附条件的。** [EEG §9](https://www.gesetze-im-internet.de/eeg_2014/__9.html)：§9(1) 要求运行方保证技术状态使电网运营商**随时可调取实际上网量并可全部或分级远方降低上网功率**；同款末句豁免“总装机 ≤ **2 kW** 且逆变器 ≤ **800 VA**”的插电式光伏设备。§9(2) 在智能电表与控制装置装好前：**≥100 kW** 须具备随时调取与全部/部分远方降低能力；**25–<100 kW** 须具备远方降低能力，且**仅对按 EEG §19(1) 第 2/3 项归入上网电价（Einspeisevergütung）或 Mieterstrom 补贴的设施**须把最大有功上网限至装机 **60%**；**<25 kW** 归入上述电价/补贴的设施同样限 60%。（此处 `§ 19 Absatz 1 Nummer 2 oder Nummer 3` 指 **EEG** 自己的 §19，不是 EnWG §19。）
- **项目证明与单元证书是不同对象。** 沿用 §3 已读的 [NELEV §2](https://www.gesetze-im-internet.de/nelev/__2.html)：证明置于 DSO 运行许可流程；§2(2a) 对 Type B/C 项目要求设施证书与符合性声明；§2(2b) 的设施证书签发路线止于 **2025-12-31**；§2(6) 要求软件更新不得覆盖 DSO 规定的电气特性。

**（I）德国规则包的可用结论：** 国家层可版本化的是“TAB 不得抵触通用最低要求、补充须有理由并公布”这一效力规则，以及 EEG §9 的三档控制义务；**60% 上限不是通用义务**，只挂在归入上网电价/Mieterstrom 的设施上。具体 DSO 的补充值属另一层，本轮未取得（§10.7）。

### 10.4 荷兰（P）

**先纠正一条会被写错的前提：荷兰的 `Netcode elektriciteit` 已于 2026-02-21 废止。** [ACM 2026-02-05 决定 ACM/UIT/666113](https://zoek.officielebekendmakingen.nl/stcrt-2026-4089.html)（Stcrt. 2026, 4089）核准并确定 **Systeemcode elektriciteit 2026**，其 **Artikel 14.5** 明确撤销 Netcode elektriciteit 与 Samenwerkingscode elektriciteit，**14.6** 规定公布次日生效，**14.7** 为引用名。所抓取的 95 条 wetten.nl 条文信息页全部标注“Regeling vervallen per 21-02-2026”（该合并总览页本身不带此标记，故以条文页与 Stcrt 决定互证）。决定说明其与旧 Netcode 之间以**政策性中性**改写为主，附 transponeringstabel。以下条文均引自 Systeemcode elektriciteit 2026 正文（同上 Stcrt 链接）。

- **分档阈值。** Artikel 3.1（对应 RfG Art. 5(2)）：Type B 阈值 **1 MW**、Type C **50 MW**、Type D **60 MW**。
- **储能单列的适用阶梯。** Artikel 2.9(3)(a)：储能单元按**最大可交付有功功率**比照发电单元——`≥0,8 kW 且 <1 MW` → Type A；`≥1 MW 且 <50 MW` → Type B；`≥50 MW 且 <60 MW` → Type C；`≥60 MW` → Type D；同步耦合与非同步耦合分别适用 RfG 的不同条款组。
- **储能的两项运行能力要求。** Artikel 2.9(3)(b)：须具备 NC ER Art. 15(3)(a)(b) 的**储存模式→发电模式自动切换**与**自动解列**能力。(g)：限频敏感模式在**低频、且储存与发电两种模式下**，`>0,8 kW 且 <1 MW` 的 statik 为 **2%**，`≥1 MW` 为 **1%**。
- **申报义务先于分档。** Artikel 2.9(2)：接入方须**及时告知 DSO** 其安装或变更发电单元或储能单元的意向；2.9(1)：设施中不得含有可向 DSO 系统馈电的设备，除非满足第 3 章对发电单元的附加条件。
- **<800 W 与 Type A 的关系。** §3.2 只规定“**<800 W 的发电单元**”（含自动并网 Art. 3.3、功率因数 0,9、保护与中性点等）；Art. 3.10(2)：接于低压的 **<11 kW** Type A 单元亦须满足 §3.2（Art. 3.3 除外）。
- **可用于合同的具体整定值。** Art. 3.11：47,5–48,5 Hz 持续 30 min、48,5–49,0 Hz 30 min、49,0–51,0 Hz 不限时、51,0–51,5 Hz 30 min；频率梯度 1 Hz/s（同步）/ 2 Hz/s（power park module）；LFSM-O 阈值可设 50,2–50,5 Hz、默认 **50,2 Hz**，statik 可设 4–12%、默认 **5%**；重合闸条件为电压 0,90–1,10 pu、频率 49,9–50,1 Hz 持续 **60 s**，功率梯度 **20%/min**。Art. 3.12：低压 **>11 kW** 须有输出电流测量、并网状态信号，及三相欠压（80% 时 2 s、70% 时 0,2 s）、过压（110% 时 2 s）、过流/过载、频率（47,5 与 51,5 Hz，2 s，可单相）保护，并允许在电压恢复后数分钟再并网。
- **保护配合与设备合规的评价对象是设施，不是证书。** Art. 2.6：设施保护须与 DSO 保护**选择性配合**，DSO 须就保护哲学、短路功率最小/最大值、中性点处理、绝缘配合、系统结构与运行方式告知并协商；Art. 2.7：设施中的设备须符合适用标准，且设施须能承受 DSO 现场预期的短路功率。

**（I）荷兰规则包的可用结论：** 分档键是“储能单元最大可交付有功功率”，Type B/C/D 阈值为 **1 / 50 / 60 MW**；`<800 W` 与 `0,8 kW` 之间如何归类**未在已读条文中给出**（§3.2 的文字指向“发电单元”）。整定值是 DSO 可直接引用的具体数字，但不能反过来当作设备证书的替代。

### 10.5 三条跨国硬约束（P → I）

1. **Type 阈值不可跨国外推。** FR 的 Type B 是 `1–18 MW`、C 是 `18–75 MW`、D 是 `≥75 MW`；NL 的 B 是 `1–50 MW`、C 是 `50–60 MW`、D 是 `≥60 MW`。同一台 30 MW 项目在法国属 Type C、在荷兰属 Type B，义务组不同。**（I）`Type` 字段只有在带上国家与规则版次时才可存储。**
2. **功率口径与计量点不可省略。** FR 在 BT 取**视在功率（kVA）**、其他电压域取有功；NL 取**最大可交付有功功率**；DE 用 `installierte Leistung` 并落到 TAB 与并网功率约定。**（I）任何功率值都必须同时记录口径（kVA/kW）、电压参考域与计量点，否则不能参与分档。**
3. **聚合规则是国家规则，不是通用常量。** FR 把同一接网点上可同时运行的机组求和为一个 `Pinstallée`；NL 以单个 `elektriciteitsopslageenheid` 分档并要求意向申报。**（I）项目级“合计功率”必须按国家规则计算，不能默认相加。**

另有一条与文案直接相关的边界：德国的 **60% 上网上限只挂在归入上网电价/Mieterstrom 的设施**上，荷兰用 statik/LFSM 整定值，法国用合同框架区分是否注入。**不得把“60% 限制”写成对三国或全欧洲的通用事实。**

### 10.6 规则包最小字段（I，待实现）

延续 §5 的模块职责，本节把它落到国家/DSO 层。每条规则至少携带：`country`、`rule_edition`（法定文本版次/生效日）、`instrument_id`（条文号）与官方 URL、`retrieved_at`、`voltage_reference_domain`、`power_basis`（kVA / kW）与`measurement_point`、`type_thresholds`、`aggregation_rule`、`notification_or_permit_duty`、`protection_settings`（区分固定值、可设范围与默认值）、`control_or_telemetry_duty` 及其触发条件、`contract_frameworks`、`dso_resolution`（该站点由哪家 DSO 覆盖、如何核实），以及逐项的 `有证据支持 / 有条件 / 信息不足 / 明确冲突`。缺任一项即显示待核，不以 EN 50549 单元证书或邻国默认值填补。

### 10.7 仍缺的具体原件与权限（不猜、不补默认值）

- **德国具体 DSO 的低压 TAB 正文未取得。** Westnetz 的 `tab-niederspannung-01092025.pdf` 连续 10 次会话错误后由 unblocker 重试，仍被判为不可解析；Netze BW 的安装商页只列**中压**与**高压** TAB，未列低压 TAB 链接；把 PDF 直接作为起始 URL 时采集器不解析（`saveContentTypes` 只作用于页面内链接文件）。因此德国包只能承载国家层与“TAB 不得抵触通用最低要求、补充须有理由并公布”的效力规则，**不能给出任何 DSO 的具体补充数值**。
- **`§14a` 是否覆盖储能未核实。** BNetzA 的 Festlegung（BK6-22-300）本轮未取得；§14a 正文只写“steuerbare Verbrauchseinrichtungen”与由 Festlegung 定义前提。**不得默认把储能归入 §14a，也不得据 §14a 推断储能义务。**
- **法国整份 arrêté 未全文取得。** Legifrance 的 JO PDF 两次失败（Cheerio 判为不可解析；Playwright 返回 0 条），仅取得条文级页面。因此**保护整定附录、符合性证明附录与被引用表格未读**，法国包目前只能覆盖 §10.2 所列条款。
- **法国 `NF EN 50549-1-4` 的所指未核。** 按 Enedis 原文记录，不擅自改写为标准号；该豁免的适用条件（设备类型、功率、安装方式）亦未核。
- **荷兰 `<800 W` 与 `0,8 kW` 之间的归类未核。** 已读的 §3.2 文字指向“发电单元”，储能在该区间的处理没有条文支撑。
- **荷兰 RfG 条文本身未读。** Systeemcode 大量条款以“比照 RfG Art. x”方式引用欧盟 2016/631；本轮未取得这些条款正文，故只能记录引用关系，不能记录条款内容。
- **荷兰概念定义未读。** `Begrippencode elektriciteit 2026` 中“一个 elektriciteitsopslageenheid”的边界（多机并联是否合一）未核，直接影响分档与聚合。
- **三国共同缺口**：无任何项目的并网申请/许可/投运记录；本轮未把任何 Woo 证书与 FR / NL 规则匹配；未取得 4105:2026-03 的过渡原文（§8 仍开放）。

### 10.8 本轮 Apify 取证索引

只保留实际产生被引用内容的运行；搜索摘要、被反爬拦截的请求与解析失败条目均不作为结论依据，其失败形态记录在 §10.7。

| 采用内容 | Actor / run | Dataset 或 KV |
| --- | --- | --- |
| FR arrêté Article 3（适用域、`Pinstallée` 口径） | `apify/website-content-crawler` · `xeZWlPv9eZ3ufy0To` | dataset `RxqupzpuMlqbTTjXh` |
| FR arrêté Article 34 / 35（实质性变更、Type 分档表） | `apify/website-content-crawler` · `4Zj6PaK39Pk3sVPUN` | dataset `OCUWjiowZQCCDcdal` |
| FR Enedis 接入流程（三框架、Consuel、投运前禁止注入） | `apify/website-content-crawler` · `k9ZczQwjZv4XRzpoB` | dataset `S9szEu9ZHD2EUAUMN` |
| FR Enedis 全部自消费（零注入亦须申报、CACSI） | 同上 run | 同上 dataset |
| FR Enedis DSO 覆盖与非 Enedis 区域、申报档案清单 | `apify/website-content-crawler` · `37ZrtBPpIy7HJOAXF` | dataset `gyC8QIOrtO5Fon8xh` |
| FR 官方入口定位（Enedis / CRE / Legifrance） | `apify/google-search-scraper` · `dX78HUmrCRkPbg781` | dataset `2AmbcUGBtdIXI1t3z` |
| DE EnWG §17 / §19（储能在接入与 TAB 义务内、§19(1a) 效力边界） | `apify/website-content-crawler` · `SxtAdQNuQ09ahL5aO` | dataset `3MkTEadSLcoiokdkP` |
| DE EnWG §14a（可控负荷的网向控制） | `apify/website-content-crawler` · `CdJtc9MUhzmsNVbOs` | dataset `rXN9ealbb9Rro9hAc` |
| DE EEG §9（2 kW/800 VA 豁免、100/25/60% 三档） | `apify/website-content-crawler` · `xeZWlPv9eZ3ufy0To` | dataset `RxqupzpuMlqbTTjXh` |
| DE DSO 站点结构（Netze BW TAB 法定义务与已列 TAB 种类） | `apify/website-content-crawler` · `pEA4oEPq5VrXacwiL` | dataset `iVNkvXDNZdecZY8Le` |
| NL ACM 决定：Netcode 废止、Systeemcode 2026 全文与生效 | `apify/website-content-crawler` · `LYEhwNSiBjG5WOmMr` | dataset `NiggWqEf971s52Jwm` |
| NL Systeemcode Artikel 2.9 / 3.1 / 3.2 / 3.6 / 3.10–3.12 原文 | 同上 run（正文出自同一 Stcrt 页面） | 同上 dataset |
| NL 官方入口定位（wetten.overheid.nl / ACM） | `apify/google-search-scraper` · `W88CDSCECYgiwPgjf` | dataset `YeYcwY6eIZ0gssMe0` |

**本轮收口：** 新增了 FR / DE / NL 三国的国家层法定条文证据、荷兰 Netcode 已废止这一前提纠正、以及“Type 阈值与功率口径不可跨国外推”的硬约束。**未取得**德国具体 DSO 的低压 TAB 正文、法国 arrêté 全文与附录、荷兰 RfG 条文与概念定义、`§14a` 对储能的适用性结论。据此**没有任何一个国家的规则包可以标为完成**，也没有任何设备或项目因此获得并网放行。

### 2026-11-01 德国接网适用域核对

VDE FNN 的中压规则页面列出 VDE-AR-N 4110:2023-09，自 2023-09-01 起适用。其 FAQ “1 Anwendungsbereich” 以 350 kWp 光伏接入低压公共电网为例，区分低压接网点的连接评价和发电单元须提供的电气特性证据。FAQ 指向 4105 第 8.4 章。不能将项目填报的接入容量 kVA 与有功功率 kW 直接比较后，给整个接网点指定 4110。本次读的是 2026-10-27 00:26 UTC 留存的官方页面内容。它没有证明 4105:2026-03 的过渡条款或当前项目取得 DSO 放行。[VDE FNN 中压接入规则与 FAQ](https://www.vde.com/de/fnn/themen/tar/tar-mittelspannung-vde-ar-n-4110)

### 2026-11-01 法国、荷兰和德国原文重新读回

旧研究数据集当前对已配置账号返回 `403 insufficient-permissions`。本次经 Apify `website-content-crawler` 单批实际读取以下官方页面，均 HTTP 200。下表 SHA-256 是采集器 `text` 字段的 UTF-8 字节哈希，用来标识本次**正文提取**，不是官方签名或原始 HTML/PDF 哈希。读取日期与法规本身的生效日分开记录。

| 原文 | 实际读取时间 UTC | 正文提取 SHA-256 | 本次可确认的版本范围 |
| --- | --- | --- | --- |
| [法国 arrêté，Article 3](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042036844) | 2026-11-01 20:50:05 | `e6ffbe4aa4e80a2b7561dc3b41e2357bfb06b49e962da0251c366e5ee63c4c63` | 页面标明自 2020-06-26 生效；该次读取确认至 2026-11-01。 |
| [同一 arrêté，Article 35](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042036860) | 2026-11-01 20:49:53 | `4d35445b56b2d705e6afb81e93a4beec10f896ffcd3f14b1e69feda61794dfb3` | 同上。表内变量是 `Pmax` 与接网点电压 `Uracc`。 |
| [荷兰 Staatscourant 2026, 4089 原始决定](https://zoek.officielebekendmakingen.nl/stcrt-2026-4089.html) | 2026-11-01 20:49:12 | `b4e19cdd6997bb341b083e528c24ae9f7d7b28697f73d80ef000ff9827f3f3f0` | 原始 Systeemcode 2026 决定；本次读回不证明后续未修订。 |
| [德国 EEG §9](https://www.gesetze-im-internet.de/eeg_2014/__9.html) | 2026-11-01 20:49:09 | `dfbff2f705291e19c119bcbefec5ed046917044e20a8c20d43e993000df3958f` | 该次官方页面的现行汇编；页面单独展示并未证明适用每个存量项目的过渡规则。 |
| [德国 EnWG §19](https://www.gesetze-im-internet.de/enwg_2005/__19.html) | 2026-11-01 20:49:10 | `7dbf22b9f82a3bf380d25975e4d9fe9c68fa37c9feb4ee7972e3272f91f0b208` | 该次官方页面的现行汇编；不确定具体运营方 TAB 的适用性。 |

核对时发现三个决定性边界：

1. 法国 Article 35 对发电单元以 `Pmax` 和 `Uracc` 分档。Article 3 定义的 `Pinstallée` 是另一变量；仅有设备铭牌、BT 的 kVA 或按 Article 3 求和的总值，不能自动作为 Article 35 的 `Pmax`。
2. 荷兰 Article 2.9(3)(a) 对能向电网馈电的储能单元按其最大可交付有功功率给出 A/B/C/D 对应条款。2.9(3)(g) 的低频敏感模式 2% 档从 **大于** 0.8 kW 开始，而 A 对应条款从 **大于或等于** 0.8 kW 开始；两者不得合并。单元边界、欧盟被引用条款以及后续修订仍须另核。
3. 德国 EEG §9(2) 的暂时义务与智能计量及控制设备的安装**和首次控制测试**有关，不能只据“已安装智能表”判断已经越过该阶段。§9(3) 的同地、十二个月、同一接网点等聚合规则亦不能用单台逆变器功率替代；具体旧项目的过渡适用性尚待独立证据。

荷兰随后补读[官方汇编 BWBR0052336 的 2026-10-01 版](https://wetten.overheid.nl/BWBR0052336/2026-10-01)，2026-11-01 20:52:36 UTC HTTP 200，页面标明该版自 2026-10-01 起至读取时有效；正文提取 UTF-8 SHA-256 为 `d20979cca5d06af7da83962f2a6afaef8112fe2cf2411ec540e84b08436831e0`。已逐段确认 Article 2.9(3)(a)、(g) 的上述功率档与原始决定相同。页面同时提示 2027-01-01 的未来修订和另有生效日未定修订，因此这次读取不证明读取日之后的条款。单元边界与项目许可仍须另核。

本次原文读取分别来自 Apify run `ED2yCmajhagfn79oK`（FR/DE 与 NL 原始决定）、`KtT6I586EX7bSj1bV`（NL 汇编）和 `IUOM0bLjiD5BrC2Js`（Enedis）；`HXikWGnxV8JsEsQVH` 只定位荷兰官方汇编，不作为规则证据。下方保留直接用于实现的原文节选及上方正文哈希，远端临时存储在核实归属后回收。

具名 DSO 的流程也在同一 Apify 通道重新核对：[Enedis 全自发自用](https://www.enedis.fr/autoconsommer-la-totalite-de-lenergie-produite-par-vos-panneaux) 2026-11-01 21:01:20 UTC HTTP 200，正文提取 SHA-256 `3741f1e39b855240554fc7348cd130d08f8b186e2e3a38dd831b2c708b4ff673`；[Enedis 发电接入流程](https://www.enedis.fr/raccordement-installation-production-electrique) 同时 HTTP 200，正文提取 SHA-256 `f170c4b32846d4c1dd1a618a2a0391b3693e398fa366d53d1f2e7d341fc1f366`。前者限定全部光伏发电现场自用且不向公共电网注入；要求通过 Enedis-Connect 申报、接受 CACSI，并提交 Consuel 或荣誉声明。页面对修改既有电路或加装电池写明须 Consuel，同时提到某些符合其原文标准表述的 plug-and-play 设备可能例外；不据此推断任一产品符合例外或项目已获许可。该页面未给可确认的生效版本日期，只记录本次读取日；运营区域和适用性仍须核实。

本次尝试获取 Westnetz 原文。首次采集的浏览器进程在 1 GiB 限额内存压力下超时，结果为空。改用静态 HTTP 精确请求 Westnetz 官方单页，原站返回 403，无正文。10 月 28 日登记的 EnWG §19 数据集本次也未获读取权限。复用上表的既有条文核对，不补写原件哈希、法规生效日期或 Westnetz 数值。两个运行均已结束，分别为 c56M3SKLiUH26q1mt 与 nDS78XVMulbNA0UgP。

现行 WordPress 的旧配置器短代码转入统一 Planner，旧商用代理返回退休响应；隔离的商用计算接口不能证明客户已获得国家规则判定。统一 Planner 的国家结果目前仍为待核。项目提供的接网点电压、运营商和适用 TAB 来源，应与独立核实的文件版本、法规适用性、最终并网许可分别记录。

#### 规则实现所用原文节选

以下为上述同一采集器 `text` 原文的对应条款，空白压缩；不是对项目适用性或 DSO 接受的结论。

<details>
<summary>Enedis：全自发自用、申报与 CACSI</summary>

```text
L’autoconsommation totale signifie que toute l’électricité produite par votre installation photovoltaïque est consommée sur place, sans aucune injection sur le réseau public. L’installation d’un système de stockage (batterie)vous permet de différer vos usages dans les cas où vous ne consommez pas la totalité de votre production à un instant donné. Aucun revenu n’est généré, puisque vous ne vendez pas votre électricité. La déclaration d’une installation de production en autoconsommation totale est obligatoire, même sans injection, quel que soit son niveau de puissance. Mes démarches pour déclarer mon installation La déclaration est à réaliser via le portail Enedis-Connect : https://connect-racco.enedis.fr. Vous devrez : Remplir le formulaire de demande Joindre un consuel ou une attestation sur l’honneur Le certificat Consuel est délivré par l’organisme Consuel et exigé dans les cas de travaux électriques modifiant le circuit existant ou dans le cas d’ajout de batterie. (Dispense possible pour les équipements “plug & play” déjà assemblés et conformes à la norme NF EN 50549-1-4). Accepter les termes de la CACSI qui formalise votre engagement à ne pas injecter sur le réseau.
```

</details>

<details>
<summary>法国 Article 35</summary>

```text
Pour l'application du règlement UE n° 2016/631, les catégories significatives des unités de production d'électricité sont définies de la manière suivante : Catégorie de l'unité Plage de puissance maximale Tension au point de raccordement Type A 0,8 kW ≤ Pmax < 1 MW Uracc < 110 kV Type B 1 MW ≤ Pmax < 18 MW Uracc < 110 kV Type C 18MW ≤ Pmax < 75 MW Uracc < 110 kV Type D 75 MW ≤ Pmax Uracc< 110 kV 0,8 kW ≤ Pmax Uracc ≥ 110 kV
```

</details>

<details>
<summary>荷兰汇编 Article 2.9(1)–(3)</summary>

```text
1 De elektrische installaties bevatten geen bedrijfsmiddelen die tot invoeding in het systeem van de systeembeheerder kunnen leiden, tenzij aan de aanvullende voorwaarden voor elektriciteitsproductie-eenheden uit hoofdstuk 3 wordt voldaan. 2 De aangeslotene stelt de systeembeheerder tijdig op de hoogte van zijn voornemen tot het plaatsen of wijzigen van een elektriciteitsproductie-eenheid of een elektriciteitsopslageenheid, opdat de systeembeheerder eventueel noodzakelijke wijzigingen in het systeem kan doorvoeren. 3 Indien het bedrijfsmiddel dat tot invoeding in het systeem van de systeembeheerder kan leiden, bedoeld in het eerste lid, een elektriciteitsopslageenheid betreft: a. zijn aansluitvoorwaarden als bedoeld in Verordening (EU) 2016/631 (NC RfG) en de daarbij behorende onderdelen van hoofdstuk 3 van overeenkomstige toepassing met dien verstande dat: 1°. een synchroon gekoppelde elektriciteitsopslageenheid voldoet aan de voorwaarden, bedoeld in de artikelen 13 tot en met 19, artikel 40, de artikelen 42 tot en met 46 en de artikelen 51 tot en met 53 van Verordening (EU) 2016/631 (NC RfG); 2°. een niet-synchroon gekoppelde elektriciteitsopslageenheid voldoet aan de voorwaarden, bedoeld in de artikelen 13 tot en met 16, de artikelen 20 tot en met 22, artikel 40, artikel 42, artikel 43, de artikelen 47 tot en met 49 en de artikelen 54 tot en met 56 van Verordening (EU) 2016/631 (NC RfG); 3°. een elektriciteitsopslageenheid met een maximaal te leveren werkzaam vermogen groter dan of gelijk aan 0,8 kW en kleiner dan 1 MW voldoet aan de bepalingen die van toepassing zijn op een elektriciteitsproductie-eenheid van het type A; 4°. een elektriciteitsopslageenheid met een maximaal te leveren werkzaam vermogen groter dan of gelijk aan 1 MW en kleiner dan 50 MW voldoet aan de bepalingen die van toepassing zijn op een elektriciteitsproductie-eenheid van het type B; 5°. een elektriciteitsopslageenheid met een maximaal te leveren werkzaam vermogen groter dan of gelijk aan 50 MW en kleiner dan 60 MW voldoet aan de bepalingen die van toepassing zijn op een elektriciteitsproductie-eenheid van het type C; 6°. een elektriciteitsopslageenheid met een maximaal te leveren werkzaam vermogen groter dan of gelijk aan 60 MW voldoet aan de bepalingen die van toepassing zijn op een elektriciteitsproductie-eenheid van het type D. b. beschikt de elektriciteitsopslageenheid over de mogelijkheid tot het automatisch overschakelen van de opslagmodus naar de opwekkingsmodus, bedoeld in artikel 15, derde lid, onderdeel a, van Verordening (EU) 2017/2196 (NC ER), alsmede over de mogelijkheid tot automatisch ontkoppelen, bedoeld in artikel 15, derde lid, onderdeel b, van Verordening (EU) 2017/2196 (NC ER); c. zijn de relevante artikelen van Verordening (EU) 2016/1388 (NC DCC) en paragraaf 4.1 van overeenkomstige toepassing indien de elektriciteitsopslageenheid is aangesloten op een transmissiesysteem; d. zijn de relevante artikelen van Verordening (EU) 2016/1388 (NC DCC) en paragraaf 4.2 van overeenkomstige toepassing indien de elektriciteitsopslageenheid vraagsturing levert aan een systeembeheerder; e. zijn voor de gegevensuitwisseling tussen de aangeslotene die beschikt over een elektriciteitsopslageenheid en de systeembeheerder de artikelen 12.1, 12.11 en 12.21 of 12.2, 12.12 en 12.22 van overeenkomstige toepassing; f. zijn voor de gegevensuitwisseling tussen de aangeslotene die beschikt over een elektriciteitsopslageenheid en de systeembeheerder tevens de artikelen 12.3, 12.13 en 12.23 of 12.4, 12.14 en 12.24 van overeenkomstige toepassing indien de elektriciteitsopslageenheid vraagsturing levert aan een systeembeheerder; g. geldt in afwijking van onderdeel a dat voor de gelimiteerde frequentiegevoelige modus – onderfrequentie in zowel de opslag- als in de opwekkingsmodus de statiek ingesteld is op: 1°. 2% voor elektriciteitsopslageenheden groter dan 0,8 kW en kleiner dan 1 MW; en 2°. 1% voor elektriciteitsopslageenheden groter dan of gelijk aan 1 MW; en h. is artikel 9.36 van overeenkomstige toepassing op het beïnvloeden van het via het overdrachtspunt van de aansluiting van een elektriciteitsopslageenheid uit te wisselen werkzaam vermogen.
```

</details>

<details>
<summary>德国 EEG §9(1)–(2)、(3)</summary>

```text
(1) Betreiber von Anlagen oder KWK-Anlagen haben den ordnungsgemäßen technischen Zustand der Anlage und der jeweiligen elektrischen Anlage hinter der Hausanschlusssicherung sicherzustellen, so dass 1. der Messstellenbetreiber seine Verpflichtungen zum Einbau und Betrieb von intelligenten Messsystemen und Steuerungseinrichtungen nach den §§ 3, 29 und 45 des Messstellenbetriebsgesetzes erfüllen kann und 2. Netzbetreiber oder andere Berechtigte jederzeit die Ist-Einspeisung abrufen und die Einspeiseleistung bei Anlagen und KWK-Anlagen, die Strom in das Netz einspeisen, vollständig oder, sobald jeweils die technische Möglichkeit besteht, stufenweise oder stufenlos ferngesteuert regeln können. Dabei sind vorbehaltlich sonstiger Rechtsvorschriften die allgemein anerkannten Regeln der Technik zu beachten. Die Sätze 1 und 2 sind nicht anzuwenden auf Steckersolargeräte mit einer installierten Leistung von insgesamt bis zu 2 Kilowatt und mit einer Wechselrichterleistung von insgesamt bis zu 800 Voltampere, die hinter der Entnahmestelle eines Letztverbrauchers betrieben werden. (2) Bis zum Einbau von intelligenten Messsystemen und Steuerungseinrichtungen nach § 29 Absatz 1 Nummer 2 des Messstellenbetriebsgesetzes und zur erstmaligen erfolgreichen Testung der Anlage oder KWK-Anlage auf Ansteuerbarkeit durch den Netzbetreiber über diese neu eingebaute Technik sowie unbeschadet weiterer Vorgaben im Zusammenhang mit der netzorientierten Steuerung von steuerbaren Verbrauchseinrichtungen nach § 14a des Energiewirtschaftsgesetzes müssen 1. Betreiber von Anlagen oder KWK-Anlagen, die jeweils eine installierte Leistung von mindestens 100 Kilowatt haben, sicherstellen, dass diese Anlagen jeweils mit technischen Einrichtungen ausgestattet sind, mit denen der Netzbetreiber jederzeit die Ist-Einspeisung abrufen und die Einspeiseleistung ganz oder teilweise ferngesteuert reduzieren kann, 2. Betreiber von Anlagen oder KWK-Anlagen, die jeweils eine installierte Leistung ab 25 Kilowatt und von weniger als 100 Kilowatt haben, a) sicherstellen, dass diese Anlagen jeweils mit technischen Einrichtungen ausgestattet sind, mit denen der Netzbetreiber jederzeit die Einspeiseleistung ganz oder teilweise ferngesteuert reduzieren kann, und b) soweit es sich um Anlagen handelt, die der Einspeisevergütung oder dem Mieterstromzuschlag nach § 19 Absatz 1 Nummer 2 oder Nummer 3 zugeordnet sind, am Verknüpfungspunkt ihrer Anlage mit dem Netz die maximale Wirkleistungseinspeisung auf 60 Prozent der installierten Leistung begrenzen oder 3. Betreiber von Anlagen, die der Einspeisevergütung oder dem Mieterstromzuschlag nach § 19 Absatz 1 Nummer 2 oder Nummer 3 zugeordnet sind und die eine installierte Leistung von weniger als 25 Kilowatt haben, oder von KWK-Anlagen, die jeweils eine installierte Leistung von weniger als 25 Kilowatt haben, am Verknüpfungspunkt dieser Anlagen mit dem Netz jeweils die maximale Wirkleistungseinspeisung auf 60 Prozent der installierten Leistung begrenzen. Die Pflicht nach Satz 1 kann bei mehreren Anlagen oder KWK-Anlagen, die gleichartige erneuerbare Energien einsetzen und über denselben Verknüpfungspunkt mit dem Netz verbunden sind, auch mit einer gemeinsamen technischen Einrichtung erfüllt werden, wenn hiermit die jeweilige Pflicht nach Satz 1 für die Gesamtheit der Anlagen oder KWK-Anlagen erfüllt werden kann. Der Netzbetreiber hat die Testung auf Ansteuerbarkeit nach Satz 1 spätestens im Rahmen der nächsten auf den Einbau des intelligenten Messsystems und der Steuerungseinrichtungen nach § 29 Absatz 1 Nummer 2 des Messstellenbetriebsgesetzes folgenden, nach § 12 Absatz 2b Satz 1 des Energiewirtschaftsgesetzes durchzuführenden testweisen Anpassungen sowie Abrufung der Ist-Einspeisung vorzunehmen. Satz 1 Nummer 3 ist nicht anzuwenden auf Steckersolargeräte mit einer installierten Leistung von insgesamt bis zu 2 Kilowatt und mit einer Wechselrichterleistung von insgesamt bis zu 800 Voltampere, die hinter der Entnahmestelle eines Letztverbrauchers betrieben werden.

(3) Mehrere Solaranlagen gelten unabhängig von den Eigentumsverhältnissen und ausschließlich zum Zweck der Ermittlung der installierten Leistung im Sinne der Absätze 1, 1a und 2 als eine Anlage, wenn 1. sie sich auf demselben Grundstück oder Gebäude befinden und 2. sie innerhalb von zwölf aufeinanderfolgenden Kalendermonaten in Betrieb genommen worden sind. Abweichend von Satz 1 gelten mehrere Solaranlagen, die ausschließlich auf, an oder in einem Gebäude oder einer Lärmschutzwand angebracht sind und die nicht hinter demselben Netzverknüpfungspunkt betrieben werden, nicht als eine Anlage. Bei der Fiktion nach Satz 1 bleiben Steckersolargeräte unberücksichtigt, 1. deren installierte Leistung insgesamt bis zu 2 Kilowatt beträgt, 2. deren Wechselrichterleistung insgesamt bis zu 800 Voltampere beträgt und 3. die hinter der Entnahmestelle eines Letztverbrauchers betrieben werden. Entsteht eine Pflicht nach Absatz 1, 1a oder 2 für einen Anlagenbetreiber erst durch den Zubau von Anlagen eines anderen Anlagenbetreibers, kann er von diesem den Ersatz der daraus entstehenden Kosten verlangen.
```

</details>
