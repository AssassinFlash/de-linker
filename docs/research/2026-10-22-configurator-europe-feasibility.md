# 工商业屋顶与全欧洲扩展可行性

调查日期：2026-10-22，Asia/Shanghai。本地代码审计快照：`2b2e826768aa640fca386289ef69dad6b0dc3b6b`。

本轮只读业务代码、既有研究，执行无网络的模型校验探针，并经 Apify 实时读取欧洲官方数据与方法资料；没有实现、创建工单、提交 PR 或部署。本笔记是可行性调查，不是当前生产站的功能验收。

**对用户的判断：有把握扩展为面向欧洲的工商业方案工具。** 产品目标应包含工商业屋面、当地发电、实际负荷、设备选型和报告/询盘闭环。全欧洲的项目与人工屋面工作流可统一建设；自动高精屋面按实际地区数据接入并验收。并网、结构、消防等结论各有独立证据要求，不能用一个国家的参数代替。

## 本地审计结论

**技术上有可复用的底座，足以支持扩展；现有系统没有达到“工商业全功能 + 欧洲全域相同精度 + 各国合规保证”。** 分开看，把现有画布接进工商业的 UI 与手绘几何复用较有把握；接入欧洲地点和逐地区地图数据有清楚的工程改动点；商业光储联合计算、跨气候自给率、逐国并网与认证，需要新增方法/数据契约和真实验收。不能只删德国校验或给 Commercial 多加一个按钮后宣告完成。

## 一、工商业目前缺的不是一个显示开关

1. **屋顶组件没有限定必须住宅，具备提取为共享能力的接口。** `RoofStepProps` 接收邮编、语言、引擎、`onApply`、`onClose`，没有 `segment` 限制；`apply()` 交出 kWp、组件数、各坡倾角/方位、地点、地址和来源。[RoofStep.tsx](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/roof/RoofStep.tsx:78)、[apply()](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/roof/RoofStep.tsx:444)。这是 UI/数据复用的证据，不等于工商业已消费这些数据。

2. **工商业输入合同接不住屋顶结果。** `CommercialInput` 只有标量 `pv_kwp`，没有 `planes`、`location`、`roof_source`；基类 `Strict` 禁止额外字段。前端 `CommercialValues` 与 `toCommercialInput()` 同样只带 `pv_kwp`。需要改模型、导出的 schema、表单状态与实际计算消费者，不能只在 React 里打开画布。[models.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:396)、[Strict](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:20)、[CommercialPanel.tsx](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/commercial/CommercialPanel.tsx:38)、[序列化](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/commercial/CommercialPanel.tsx:73)。生成 schema 的德国邮编约束也真实存在：[commercial-input.schema.json](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/schema/commercial-input.schema.json:38)。

3. **工商业有真实储能削峰计算底座，但没有 PV 与负荷联合计算链。** `shave()` 按输入的 15 分钟负荷求功率、能量与回充空间；有 CSV 的设计分支没有调用 PVGIS，也没有按屋面生成同时刻 PV 并从负荷扣除。`pv_kwp` 的计算使用只在无 CSV 的自用指示式里。换言之，把屋顶算出的 kWp 填给商业表单，目前只会改善一个经验区间，无法自动得到新增光伏后的削峰与自用联合方案。[commercial.py shave](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:125)、[CSV 分支](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:333)、[pv_kwp 指示式](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:398)。

4. **负荷文件需要跨国家、跨格式的时间语义。** 现解析器取每行最后一个数值，允许最少一周；没有解析时间戳、时区、夏令时、缺点或不同时间间隔。计算按每 96 点划日，再按记录天数外推年耗。现阶段可以说“复用有序 15 分钟序列计算”，不能说“任意欧洲电表导出均可直接使用”。[commercial.py parse_load_profile](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:73)、[summary](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:97)、[按日计算](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:125)。

5. **原研究本来就包含工商业屋面。** 方法文件的工商业输入明确要求“既有或计划的 kWp 与屋面”，规则还要求先扣除同时刻 PV 得到净负荷。正式规格只把屋顶接到住宅，未完整承载这部分研究；本轮没有找到业主排除商业屋顶的明确决定。[planner-methods §5.2](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/planner-methods.md:584)、[PV 输入](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/planner-methods.md:592)、[净负荷规则](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-09/planner-methods.md:601)、[正式规格](/Users/chesterjohn/Documents/de-linker/docs/specs/14-solution-configurator.md:7)。

## 二、德国绑定的具体位置

| 层                     | 当前绑定与证据                                                                                                                                                                                                                                                                                                                                                                    | 扩到欧洲需要解决的问题                                                                                                                                                       |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 地点身份               | `Plz` 为 `^\d{5}$`，说明为 German postcode；请求没有 country。[models.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:15)                                                                                                                                                                                                                  | 国家与邮编分开；允许不同邮编格式、同号跨国冲突、坐标/地址定位。EN/DE 语言不等于德国/其他国家                                                                                 |
| 定位数据               | `geo.py` 只加载 `data/plz_de.csv.gz`，返回德国州码，供地图源选择。[geo.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/geo.py:1)                                                                                                                                                                                                                     | 地点服务与国家/地区语义；住宅即使给了屋顶坐标，仍先查德国邮编。[residential.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/residential.py:784) |
| 经纬度                 | 纬度限 47.0–55.2，经度限 5.8–15.1；同时约束 `Location` 和手绘 polygon。[models.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:37)、[RoofPackRequest](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:314)                                                                                              | 使用正式服务范围和坐标校验；不能把欧洲行政范围简单写成一个德国扩大的矩形来代表已覆盖                                                                                         |
| 航拍                   | `imagery.py` 从按德国州索引的 WMS 配置取图；`PlaceResult` 返回对应图片与许可。[imagery.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/imagery.py:1)、[imagery.json](/Users/chesterjohn/Documents/de-linker/services/engine/data/imagery.json:1)                                                                                                     | 按地区/供应商接入、许可与署名、跨域、影像分辨率与可用性。MapLibre 本身不是德国绑定                                                                                           |
| 官方屋顶               | `RoofService.outline()` 先查德国邮编再取州级 LoD2；所有下载适配器在德国州表中。[service.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/service.py:69)、[lod2-sources.json](/Users/chesterjohn/Documents/de-linker/services/engine/data/lod2-sources.json:4)                                                                                    | 地区数据覆盖与格式适配。无官方模型时仍允许手绘，并准确说明数据来源与能力                                                                                                     |
| 当前 LoD2 的可靠性边界 | 即使德国，Hessen 与 Sachsen-Anhalt 的门户流程也未自动抓取，代码走不可用/手绘。[lod2.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/lod2.py:13)、[fetch](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/lod2.py:206)                                                                                             | 不能把“有地区配置”当“每座建筑必然自动出屋顶”。应独立呈现定位、航拍、官方屋面、手绘四种覆盖                                                                                   |
| 几何投影               | 手绘 `_zone()` 固定在 UTM32/33；官方适配器使用 `EPSG:258{zone}`。[service.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/service.py:150)、[lod2.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/lod2.py:69)                                                                                                  | 根据地点选合适投影/局部坐标系并验证精度，尤其欧洲西部、东部、北部与岛屿；不只调整坐标上限                                                                                    |
| 交互文案               | 手绘拒绝句写“too large or outside Germany”；手绘默认35°朝南。[RoofStep.tsx](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/roof/RoofStep.tsx:113)、[拒绝句](/Users/chesterjohn/Documents/de-linker/plugins/linker-tools/src/configurator/roof/RoofStep.tsx:477)                                                                                     | 国家/地区语义与假设改为与实际输入一致，英德同步                                                                                                                              |
| 手绘工作量限制         | 单平面最多 3,000 m²；每坡 `PlaneInput.kwp` 最大 100；住宅总 kWp 最大100。[models.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:24)、[面积限制](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:37)、[住宅输入](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/models.py:62) | 大厂房不能无依据直接放开限制，需证明多屋面/大平面排布的准确性、耗时、并发与资源边界。3,000 m² 仅为手绘限制，不是所有官方轮廓的面积限制                                       |

## 三、几何能复用，现有排布不能升级称为完整商业屋顶设计

`packing.py` 已使用 Shapely，在坡面局部框架中拉伸、退边距，再放入完整组件矩形；这里没有住宅或国家判断，可复用几何骨架。[packing.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/packing.py:52)。

但实际算法只是参考组件的纵向网格计数。平屋顶全部按朝南、零坡处理；只有 2 cm 组件间隙，没有支架抬高角度、阵列行距、东西向安装、自遮挡、天窗/烟囱/消防通道/承载等输入。边退距0.3 m、北向排除45°、坡度阈值等都明确标 `verified=False`。不能把这些未核实规划假设当作全欧洲或工商业规范。[packing.py facing/usable](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/packing.py:34)、[排布循环](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/roof/packing.py:68)、[rules.py 屋顶假设](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/rules.py:285)。

既有研究也明确区分“只输出组件数”和“会改变工程答案的组串/遮挡/支架”，认为现屋顶步停在组件数缺少同行范本。[dossier-gap §5.1](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-21-configurator-rooftop/dossier-gap.md:225)。这说明增加 Commercial 入口有实际价值的前提，是定义它究竟负责几何采集、光伏容量估算，还是进一步参与商业光储计算。不能把用户本次询问自动扩大到静力、消防或支架设计；这些能力也有既有范围限制，[同文件 §6](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-21-configurator-rooftop/dossier-gap.md:337)。

## 四、欧洲发电量与欧洲自给率是两条不同计算链

**发电量服务底座可复用。** 当前 PVGIS 适配器接收经纬度、坡度、朝向，由 pvlib 调用 PVGIS；底层函数没有写死德国坐标。住宅按各坡 kWp 汇总年度/月度发电量。德国限制主要在上游位置模型与邮编服务。[pvgis.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/pvgis.py:66)、[per_kwp](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/pvgis.py:135)、[residential.estimate_yield](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/residential.py:86)。PVGIS 的实时官方区域说明见第八节；覆盖说明不等于本工具已在相应地点完成端到端验收。

**自给率不能借用这个事实就声称全欧洲同样有效。** `htw.metrics()` 输入只有 kWp、年用电范围、可日常循环电池容量；没有地点、实际发电时序或 PVGIS 实际产量。它固定读 HTW 的参考家庭表，按 1,024 kWh/kWp·a 的参考产量估算自用比例区间；住宅代码在 PVGIS 完成后仍独立调用该查表函数。现有超范围提示检查年耗、表边界、热泵和电动车，没有按国家/气候验证。[htw.py metrics](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/htw.py:129)、[1024常量](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/rules.py:66)、[住宅调用](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/residential.py:909)。因此，南欧/北欧数据能算年发电量，并不证明当前 HTW 表能可靠给出当地自给率；工商业更不能套住宅表。跨地区需要验证适用域或采用与当地发电/实际负荷相配的时序模型，并诚实限制输出。

**住宅 HTW 定容经验也需要区分复用与已验证。** 三条规则可作为有明确出处的住宅规划基线，不能直接称为所有欧洲家庭、商业项目的普适最佳配置。代码目前不按国家/地点切换；热泵与电动车额外用电区间同样来自 HTW 的既有样本。[htw.py size](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/htw.py:79)、[consumption](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/htw.py:59)、[rules.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/rules.py:82)。

**串电压温度参数也有地域适用性问题。** 固定光伏电池片最低设计温度 -10°C、最高70°C 均标未核实假设，直接用于 Voc/Vmpp 校验；没有按项目地点取设计温度。国际扩展时，硬件公式可复用，气候设计输入要按地点/依据补齐。[rules.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/rules.py:197)、[strings.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/strings.py:56)。

## 五、兼容性、并网规范与国家认证应分别证明

现有产品/电池放行与堆叠、并联控制器合同是可复用资产：Commercial 根据厂商 documented max_units 限制并联，住宅资格检查读取真实产品参数。这能证明某些硬件组合及数量有厂商依据。[commercial.py systems](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:168)、[compatibility.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/compatibility.py:99)。

它不自动证明该组合在任意欧洲国家可以并网。当前输入没有 country；`Product` 的强类型选型字段没有国家证书适用域，`PairResult` 也只是逆变器/电池配对。型号可能在泛型 `figures` 或 documents 中有 grid_codes，但本轮查看的选择路径没有按项目国家执行国家认证 gate，不能把“有文档”当成“已逐国校验”。[products.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/products.py:82)、[PairResult](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/compatibility.py:52)、[eligibility.py](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/eligibility.py:30)。

4.6 kVA 单相门、30 kVA NA-Schutz、135 kW 的并网提示及100 MWh RLM 提示均在代码中直接引用德国依据，没有国家配置。住宅和商业路径直接使用这些全局值。它们的当前德国有效性也不是本轮重新查法标准的结果；扩国必须独立核对各国家/电网运营商规则，未完成时只应输出范围内规划结果及待核项。[rules.py 并网](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/rules.py:128)、[RLM](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/rules.py:335)、[住宅门](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/eligibility.py:42)、[商业提示](/Users/chesterjohn/Documents/de-linker/services/engine/src/linker_engine/commercial.py:328)。

## 六、无网络本地探针结果

使用现有 `services/engine/.venv/bin/python`，`PYTHONDONTWRITEBYTECODE=1`，只导入模型/方法，不发请求、不保存数据。结果：

```text
Location Munich: accepted
Location Paris: rejected; longitude
Location Vienna: rejected; longitude
Location Madrid: rejected; latitude, longitude
Commercial postcode 80538: schema accepted; German lookup found=True
Commercial postcode 75001: schema accepted; German lookup found=False
Commercial postcode 1010: schema rejected
Commercial postcode SW1A 1AA: schema rejected
Commercial planes: rejected; extra_forbidden
Hand-drawn projection _zone(-3.7)=32, _zone(2.35)=32, _zone(16.37)=33, _zone(28.98)=33
HTW metrics parameters: kwp, use, usable_kwh
```

注意：商业计算本身不查 `geo.lookup`，所以某些国外五位邮编会通过商业 schema，但仍套用德国提示；不能笼统说“国外全都被拒”。上面 lookup 探针只证明该号不在德国表。法国75001的真实国家归属不是本探针的验证对象，只把它作为五位字符串测试。

## 七、本地证据支持的交付拆分

| 能力                            | 本地可行性判断                                       | 达成后能说什么                                             |
| ------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| 工商业打开共享屋顶、手绘与采集  | 较高把握；复用组件/几何，但需补商业输入与消费者      | 商业项目可以采集/估算光伏屋面，结果进入同一项目            |
| 欧洲位置、坐标、手绘底座        | 较高把握；需移除结构性德国绑定并验证投影、边界和负载 | 欧洲范围可定位和手绘；不承诺每处都有高分航拍或自动屋面     |
| 全欧洲统一自动航拍+LoD2识别     | 仅凭本地代码不能保证；数据可用性/许可需逐地区证据    | 按地区公布自动能力，无覆盖时仍有手动路径                   |
| 商业新增PV后的削峰/自用联合方案 | 有削峰与产品合同底座，尚缺PV时序和联合调度           | 按可核对的净负荷与实际设备参数给规划方案                   |
| 全欧住宅自给率/储能建议         | 发电量底座可用，HTW跨气候适用性尚未证明              | 仅在已验证的方法域给对应指标，其他地区标明限制或换验证方法 |
| 全欧洲并网/国家认证自动放行     | 当前缺 country/证书适用域与逐国规则，不能承诺        | 针对已验证国家/接入条件给放行依据，未知则显式待核          |

上表是工程可行性分解，不是已获批准的实施计划、期限或报价。实时来源与建议的覆盖策略如下。

## 八、2026-10-22 实时官方来源核实（全部经 Apify）

检索 Actor `apify/google-search-scraper` run `ejD38vCqfG7XbFRXd`，数据集 `RmFJR0Sf7VGJhGeor`；页面读取 Actor `apify/website-content-crawler` run `vM06HVKbFax03LMUx`，数据集 `mznXYAwcRZMd9xmnD`。读取的六个官方页面均返回 HTTP 200。原始输出、输入与运行标识保存在 [raw 目录](/Users/chesterjohn/Documents/de-linker/docs/research/2026-10-22-configurator-europe/raw/official-pages.json)。JRC 总览本次只提取到短摘要，区域判断采用已完整读取的用户手册，未把短摘要当完整核实。

| 一手来源                                                                                                                                                      | 本轮直接读到的事实                                                                                                                                                  | 对扩展的含义与边界                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| [欧盟 JRC PVGIS 用户手册](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en) | PVGIS-SARAH3 覆盖欧洲等区域；高纬度等卫星覆盖不足区域有 ERA5 再分析数据。工具允许按位置计算产量并提供逐时序列；手册还说明不同辐照数据的时间戳含义                   | 发电数据底座可以支持欧洲扩展。仍需按地点验证数据可得性、所选数据库、年份和时间对齐，不能把一个样本地点的成功说成全域验证                  |
| [荷兰 PDOK 3D Basisvoorziening 官方集合接口](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections)                                             | 分析用建筑提供 CityJSON，通常 LoD2.2，没有 AHN 数据的区域为 LoD1.3；另提供面向可视化的 3D Tiles                                                                     | 荷兰存在可接的数据源，但格式不同于当前德国 CityGML；LoD1.3 不应伪装成已知真实坡度/朝向的屋顶                                              |
| [瑞士 swisstopo swissBUILDINGS3D 3.0 beta](https://www.swisstopo.admin.ch/en/landscape-model-swissbuildings3d-3-0-beta)                                       | 产品含三维建筑、屋顶几何与屋檐，可提供闭合体或屋顶/立面/足迹分离的元素                                                                                              | 欧洲扩展不应局限欧盟成员国；该数据是瑞士屋面适配的候选，仍需验证下载、版本、许可和真实场地精度                                            |
| [法国 IGN Géoplateforme 服务说明](https://geoservices.ign.fr/services-web-experts-ortho)                                                                      | 官方提供 WFS/WMS/TMS/WMTS 等服务说明入口                                                                                                                            | 说明法国有官方服务体系，不足以证明每一地区的分辨率、具体图层和屋顶模型均满足本工具要求；法国详细数据核实仍属于接入工作                    |
| [HTW 独立性计算器官方 FAQ](https://solar.htw-berlin.de/faq-unabhaengigkeitsrechner/)                                                                          | 预计算基于德国 Brandenburg 的 DWD 气象、VDI 4655 单户家庭负荷，按分钟模拟；模型家庭没有热泵和电动车。FAQ 明说位置、朝向、倾角与真实负荷会影响结果，只能提供初步参考 | 官方说明进一步确认：现有表不能直接当作欧洲工商业的自给率模型。跨气候、商业负荷应使用当地发电与适用负荷/实测负荷的联合时序，并验证设备调度 |

本轮没有下载法国、荷兰、瑞士的完整建筑数据，也没有完成许可评审或渲染接入。这些来源证明存在实现路径，不构成已经支持这些国家的产品声明。

## 九、建议的产品目标与验收边界

### 统一基础能力

1. 地点采用国家、地址/坐标和邮编的明确语义；服务范围按欧洲市场定义，包含英国、瑞士、挪威等非欧盟市场，不能把 EU27 当作欧洲的全部。页面语言与项目国家分开。
2. 屋面作为住宅和工商业共用的项目数据，支持多栋建筑、多坡面和数据来源记录。自动数据、手绘、带比例的客户图纸/正射图上传各是明确来源；无自动模型时仍有可完成工作的人工路径。图纸上传与比例校准是需要新增的能力，当前代码没有完成。
3. 商业排布根据实际支持的安装方式处理平屋顶、东西向阵列、行距及障碍区；结果明确记录参考组件、安装假设与未做的结构验算。参考成熟工具模式并给出真实夹具对照，不能只把住宅网格扩大。
4. 产量用当地气象和各坡输入；商业光储使用具有时区/间隔/缺点语义的负荷文件，与发电序列对齐，按真实设备功率、容量和效率计算。已有 PV 时需要区分总负荷与净电表负荷，防止把发电重复扣除。
5. 屋面输入与计算结果进入同一方案，再接实际商品物料清单、报告、保存、加入 Solution draft 与询盘。Commercial 当前缺少的报告与保存等环节应作为目标设计与实现，不能因原代码没有而从产品承诺删除。
6. 厂商配对放行与项目国家的并网证据分别记录；国家规则未核实的结论显示待核，不能给默认通过。保持初步方案和询盘可继续，报告清楚写出已算范围与团队需核实的事项。

### 自动能力按数据增强

按地区适配已有官方或经许可的影像、建筑和高程数据，不要求所有国家使用相同格式。对用户呈现明确能力：能定位、能加载影像、能取足迹、能取真实屋面、能做遮挡分别证明；没有足够数据时，请用户补比例/坡度/朝向，不能从普通地图猜出高精三维结果。

### 验收应证明什么

- 地理：德国回归，加欧洲西部、东部、南部、北部以及非欧盟地区代表点；按明确国家清单做基础输入与服务范围验证。代表地点测试不等于所有建筑自动覆盖。
- 几何：厂房平屋顶、多坡、多栋、障碍区、大面积的模块边界、数量、性能和资源限制有实际夹具证据。
- 能量：不同朝向/气候、时区与夏令时、既有/新增 PV、无 PV 的商业储能、缺失负荷数据有可核对输出；能流守恒、设备功率/容量限制和备电预留不重复使用。
- 业务：EN/DE × 1440/390 从地点和屋面到方案、报告、保存、草稿与询盘逐状态实走，并核对实际运行数据版本。
- 国家依据：德国规则不会错误套到别国；证书或并网依据未知时不会被显示为已放行。

结论仍是“有把握建设”，并附清楚的工程路径和验收线。本轮没有给出日期或工期承诺；完整逐国数据清单、范围规格与设计原型应先成为可评审的实施依据。
