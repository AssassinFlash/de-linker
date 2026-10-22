# 当前屋顶工具的完整用户路径有哪些可复现问题？

调查票：[当前屋顶工具的完整用户路径有哪些可复现问题？](https://github.com/AssassinFlash/de-linker/issues/549)。地图：[屋顶规划与系统选型可信性审查及重构路线](https://github.com/AssassinFlash/de-linker/issues/548)。日期：2026-10-22，Asia/Shanghai。

## 结论与研究边界

当前实现可以作为重构调查的运行样本，不能当作已获业主认可的产品。用户本次明确：老板认可的是产品想法，没有认可现有界面、操作和结果；屋顶、系统选型、报告、物料清单与业务消费必须一起审。历史“通过”、原型选择和现有测试均不能代替本次判断。

本票聚焦入口、理解、操作、错误恢复、状态/结果一致性，以及界面如何传达“已核实/估算/有条件/未知”。**系统选型是否可信优先于界面外观；本票不证明选型公式、产品匹配或工程结果正确，也不以改文案代替计算修复。** 引擎数学和欧洲数据源由同地图其他调查负责。RX06已经证明即使旧结果按旧输入算对，界面也会让新输入继续对应旧报告；计算正确性和结果版本正确性必须分别通过。现有证据已经足以要求重构统一项目状态、结果依据与下游消费；不应把“代码本来这样”当成维持现状的理由。

## 环境、身份与证据等级

- 独立工作树 `/Users/chesterjohn/Documents/de-linker-worktrees/research-roof-experience-549`，分支 `research/roof-experience-549`，代码基线 `123aea57`，来自当时 `origin/main`。
- 本地 `r549`：WordPress `http://127.0.0.1:9323`，engine `9324`，Genie `9325`。快照 `20261022-1653`，拍取时间 2026-10-22 16:56:45，载入时间 17:19:28。212 个已发布商品、2,756 个附件、缺文件 0、许可已施加；CSP/noindex 在，初始本地邮件文件数 0。[环境读回](raw/environment.json)、[快照结果](raw/snapshot-load.json)。
- HTTP 入口采样不带任何登录 cookie；本地 Computer Use 由父会话集中操作，使用访客。父会话起初打开的线上页带 Editorial Team 登录态，不能当作首次访客证据；本报告的本地证据与该线上观察分开。
- 本地 EN/DE 配置器挂载各 1 份，脚本/样式版本 `b3f5e0260a82fa964995`；懒加载屋顶脚本在浏览器日志中为 `555.js?ver=07be35653daada62a5b0`。
- **B** = 本轮浏览器截图/操作观察；**R** = 本轮 cookie-free HTTP 或确定性本地请求；**S** = 当前源码路径；**H** = 历史记录/既有测试，仅作对照。只有 S 的项目不得写成“浏览器已复现”。
- 截图按父会话原文件保存；虽然扩展名是`.png`，实际编码为JPEG。像素尺寸为1440×900或390×844，完整性、编码与SHA256在[证据清单](raw/evidence-manifest.json)，未转换图像，也不据这些图宣称无损像素对照通过。

### 评审状态与实际调用记录

按当时项目分工先尝试安装的 Claude CLI，只开放 Read/Glob/Grep/Bash/Skill、plan 权限，不改全局设置。原调用 stderr 显示实际路由为 `ccs-claude-deepseek--deepseek-flash[1m]`，父协调者要求终止；本票只终止了自己工作树对应 PID，stdout 没有结论。父协调者随后报告真正 Claude 单次直连的 OAuth 已过期、无法刷新。**没有把 CLI 品牌名或其他模型输出算作 Claude 研究完成。** 经父协调者明确指示，继续直接审计原始源码、HTTP 与浏览器事实。[调用提示](raw/claude-prompt.txt)、[路由 stderr](raw/claude-initial.stderr)、[中止状态](raw/claude-invocation-status.json)。

**2026-10-22，用户明确：“不必理会claude，全权交给你来负责。”** 由此解除本轮研究必须由 Claude 执行或审读的人员要求，Codex 对结论负责，可以依据本轮实证与研究范围收口，不再等待 Claude。上述调用失败保留为历史事实，不再构成人员前置条件；没有声称 Claude 审读完成。

人员要求的解除不改变真实证据边界：自动屋面、实际手绘/修订恢复、PDF字节、账户认领及询盘消费等未实测项，继续按下文保留为证据缺口，不能据此宣称全链验收通过。此次仅修订本节评审状态，未重复测试；原始取证材料未变，`raw/evidence-manifest.json` 封存的 README 哈希对应前一提交 `b12377a5` 的取证稿，本节的新状态以当前提交为准。

## 真实路径与入口采样

[entry-links.json](raw/entry-links.json) 记录 20 个实际地址的 HTML 工具链接：EN/DE 首页、商城、安装商、博客列表、配置器、一个商品、方案总页、住宅/工商业方案页、一个博客正文，均 HTTP 200。复跑脚本：[collect-entry-links.py](raw/collect-entry-links.py)。这是链接与文案的证据，不证明每个菜单已经展开可见或用户一定能发现。

| 起点 | 实际入口 | 期望与实际承接 |
|---|---|---|
| 首页/页头桌面与移动 HTML、页脚 | 配置器根地址，页头描述提到 Roof detail / Dachdetails | 屋顶藏在系统配置器之内；需浏览器评估是否能被想先画屋顶的人发现 |
| 安装商页 | “Open the Roof detail step” → `?step=roof`，DE 同形 | 承诺直接打开屋顶；当前实际仍是住宅初始表单，见 RX01 |
| 商城、方案总页、住宅方案页、博客列表 | 配置器根地址 | 没有携带项目类型、当前产品或用途；到达后重新输入 |
| 工商业方案页 | “Plan peak-shaving”“Plan solar self-consumption”“Size an EV charging buffer”“Plan backup for critical loads” | 四个具体意图全部指向同一配置器根地址，没有 commercial/goal 参数；当前默认 Residential，进入后还要自行重新选择 |
| 商品页、博客正文样本 | 采到的配置器链接仅全站页头/移动/页脚 | 没有在本样本中发现正文专属屋顶入口；不能外推为全站每个商品/博客均无专属入口 |

本轮用户路径目标不是让客户完成一张图后结束：发现 → 理解范围与依据 → 输入 → 自动/手绘屋面 → 修订/恢复 → 采纳 → 系统计算 → 审阅依据和限制 → 物料清单/报告 → 草稿/账户/询盘/Genie 消费同一方案。以下问题按这个完整链路判断。

## 发现清单

严重度为本轮调查优先级：P1 可能改变输入/结果含义、误导结果可信性或阻断主要链路；P2 为明确的恢复/解释/发现障碍。S 级项目先列风险与证据缺口，不冒充已测用户结果。

| ID | 严重度与发现 | 复现或核对步骤、影响 | 本轮证据与当前边界 |
|---|---|---|---|
| RX01 | P1，屋顶入口承诺与落点不一致 | 从安装商“Open the Roof detail step”进入；仍看到默认住宅输入，要再找屋顶按钮。`?step=roof` 的 HTTP200不是屋顶已打开 | **B+R+S**：[EN1440](browser/local-en-roof-deeplink-1440.png)、[EN390](browser/local-en-roof-deeplink-390.png)、[DE390](browser/local-de-roof-deeplink-390.png)、[EN/DE挂载读回](raw/roof-landing-readback.json)。Mount 仅传 size-hint 五键，不传 step；config 读 data-step，ResidentialPanel 还要求有效邮编。S1/S2/S3 |
| RX02 | P1，航拍失败却仍给“可看图点屋顶”的就绪指导 | 80538 打开屋顶；本次 WMS 多个瓦片 Failed to fetch，画布全灰，界面仍说“Click the roof … in the aerial image”，Draw plane 仍可用，未解释航拍失败/没有可定位依据 | **B+S**：[失败 UI](browser/local-en-roof-tile-failure-ui-1440.png)、[原始浏览器日志](browser/local-en-roof-tile-failure-logs.json)。这是“外部来源本次不可达”与“产品未反映该失败”两件事，不能说永久没有该影像。S4 |
| RX03 | P1，德语小数逗号/无效字符静默变成 0° | 手绘输入35,5、180,5；当前序列化分别是 `Number(x)||0` 和 `%360`，会发送0/0。字母和空白也变0，不是字段错误。普通住宅表单却会先把逗号换点，行为不一致 | **R+S**：[转换探针](raw/input-conversion.json)、[计算请求](raw/roof-input-probes.json)。同矩形35/180与0/0均HTTP200且返回不同组件数；尚未将这个转换冒称为DE浏览器截图复现。S5/S6 |
| RX04 | P2，角度错误被解释为面积或德国范围错误 | 对同一德国境内矩形提交91°或-90°，API422明确是倾角/方位范围；前端所有 invalid 都显示“too large or outside Germany”，用户不知道该改哪个字段 | **R+S**：[API原始422](raw/roof-input-probes.json)。EngineError 只尝试 detail.field，而 Pydantic detail 是数组；roof invalid 统一进入 refused。浏览器实际错误排版待补。S5/S7 |
| RX05 | P1，屋顶允许的结果不一定能进入后续配置器 | 小于3000m²的矩形35°/180°，屋顶HTTP200返回172.5kWp；Use this roof仅检查>0，但住宅请求总kWp和单坡均≤100，采纳后kWp只读。大屋面可在第一步成功、下游被拒，又无逐面缩小/删改工具 | **R+S**：[172.5kWp响应](raw/roof-input-probes.json)。本票不评该数量是否准确；这里证明两个步骤的适用边界不一致。S5/S6/S8 |
| RX06 | P1，输入修改后没有与结果版本绑定的失效状态 | 先用4500kWh/10kWp算出方案，改年耗为6000、不重算；报告仍写4500，PDF/Save保持可点，“已存账户”仍在，没有过时标记。客户屏上新输入与实际被保存/下载的旧结果混在一起 | **B+S，DE390受控气象夹具**：[输入/报告/按钮读回](browser/local-de-stale-result-and-guest-save.json)、[截图](browser/local-de-input-changed-stale-report-390.png)。Form内部值变化没有通知Panel，后续动作仍消费上次input/result。未声称所有字段均逐一实测。S3/S6/S9 |
| RX07 | P2，屋顶修订/关闭缺少工作恢复契约 | Draw完成后TerraDraw清空并static；当前列表只有勾选，没有修改/删除某块已绘面的动作。Close直接卸载；Change roof重新挂载时未传此前几何。刷新/换项目类型同样没有恢复入口 | **S**，需区分“勾选可变”与“几何可编辑”。本票没有把刷新丢失或Close丢失列成浏览器已证。S3/S5/S10 |
| RX08 | P1，访客保存成功文案与真实落点不一致 | 访客成功方案点“Lösung speichern”，显示“In Ihrem Konto gespeichert.”；点击保存链接实际进入登录页。API代码guest返回202,id0、只留Woo会话；另一个Ask Genie入口才有“仅留在浏览器，需登录”说明 | **B+S，DE390受控气象夹具**：[保存截图](browser/local-de-guest-save-390.png)、[实际落点](browser/local-de-guest-saved-link-login-390.png)、[读回](browser/local-de-stale-result-and-guest-save.json)。访客PDF不随会话保存为源码事实；本轮未登录/注册，也未声称已验证登录后认领。S9/S11/S12 |
| RX09 | P1，屋顶假设未随结果完整进入报告 | 报告明确排除五条ROOF_ASSUMPTIONS，理由称屋顶面板已披露；面板假设details却只在有官方result时渲染。纯手绘不setResult，采纳payload不带假设；即使自动路径看过，PDF仍不保留这些排布假设 | **S**，报告排除行为已核源码；纯手绘浏览器与实际PDF待核。不能把“源码标unverified”当成客户/团队能看到它。S5/S13 |
| RX10 | P1，存在“部分已验/估算”被整套系统肯定句覆盖的风险 | 首屏“Size your system and get the bill of materials”，结果区“The released system for these inputs”，报告与购买工作动作只按selected非空开放。厂商配对放行、参考组件组串、平均家庭自给率、实际现场/并网核查是不同证明层级，当前没有共同的项目就绪模型 | **S+R**：受控响应有真实报告栏目；尚不据文案就判定数值错误。必须结合引擎审计决定哪些状态能发布结果，不能只改标题后称可信。S3/S9/S13/S14 |
| RX11 | P1，下游“全案”与仅商品清单之间缺少明确承接 | Add all只发送productId/quantity；屋面几何不进入该动作。账户保存带计算input，但无polygon；账户表只有加草稿/PDF，没有恢复编辑。普通询盘从Woo草稿取商品，并不自动获得roof/solution artifact。Genie保存方案读取则会按已存input重算 | **S**，不能说商品加入成功就证明屋顶/报告已随询盘交付；本轮未发送询盘，也未登录账户。需后续spec明确哪份项目版本/附件必须交给团队。S9/S11/S12/S15/S16 |
| RX12 | P2，具体工商业目标导流丢失项目意图 | 从商用方案页的削峰、自用、充电缓冲、备电任一CTA进入；实际href均为根页且默认住宅。客户要自行切Commercial并重新选择目标；切Commercial又没有屋顶 | **B+R+S**：[入口清单](raw/entry-links.json)、默认住宅深链截图、[DE1440商业面板无屋顶](browser/local-de-commercial-no-roof-1440.png)。没有把全部商用场景都称为已支持；输入/计算能力由引擎调查另核。S10 |

### 已有行为中实际得到证据支持的部分

空邮编点屋顶按钮会聚焦邮编并显示“Enter a German postcode with five digits.”，[截图](browser/local-en-roof-empty-postcode-1440.png)。该条校验工作，不代表国家范围/入口说明符合新产品目标。

报告代码确实包含PVGIS来源、HTW方法、参考组件、默认朝向、部分未核实规划假设、配对条件及文件链接，不能说“完全没有披露”。但层级、时机、可追溯性与下游保留仍有RX09–RX11的问题；披露不能把错误方法变正确。S13/S14。

## 外部失败与受控成功必须分开

首次实际网络状态：父会话浏览器在80538看到航拍瓦片失败；关闭屋顶后用4500kWh/10kWp计算，实际出现“The yield service did not answer. Try again in a minute.”及Try again，[截图](browser/local-en-yield-unavailable-1440.png)。不能由这次错误界面推断公式正确或错误，也不能把后续受控成功写成外网已恢复。

为继续审下游，经父协调者明确授权，仅向本实例PVGIS缓存复制现有仓库录制夹具 `services/engine/tests/fixtures/pvgis/48.15_11.60_t35_a180_l14.json`，未改业务代码、feed、兼容合同、算法或线上。源/目标SHA256相同：`7b12df13e8dce9505400ec9e96a9f09f415219fdab3836ceaa22b3bc2e35a548`；原缓存不存在。时间17:30:20。[缓存操作记录](raw/controlled-cache.json)。

受控同源请求：80538、4500kWh、10kWp、三相、无备电、默认35°朝南，原引擎和快照feed返回HTTP200，GoodWe GW10K-ETA-G20 + GW6.0-BAT-D-G20，报告九个栏目。完整输入与输出在[controlled-residential-response.json](raw/controlled-residential-response.json)。随后父会话DE390访客真实操作得到方案/报告并验证RX06/RX08。它证明该本地受控数据下结果展示有可运行的后端；不证明当日PVGIS可达、自动屋顶成功、公式/产品组合正确或现场可施工。

从保存链接进入登录页后，浏览器Back回来，父会话看到邮编80538/年耗6000/10kWp仍留在表单DOM，但方案/报告消失。**不能概括成“返回后所有输入都丢失”。** 本次浏览器会话故障恢复过一次，该工具会话故障未算产品缺陷；没有将故障恢复后的中间截图计作保存成功。

## 面向重构方案的约束

1. 先定义一个可保存、可修订的项目：场地、用途、屋面、负荷、现有设备及数据来源。屋顶和SC应消费同一项目，客户可从任一入口开始；不能把组件React状态当作唯一事实。
2. 计算结果必须绑定输入版本、产品/放行数据版本、方法版本和适用域。输入变化后旧结果明确失效；有条件、估算、未知和已核实分别进入输出和操作准入。哪些结果能进入草稿/报告，须由引擎可信性调查决定。
3. 报告、BOM、保存、Genie、询盘携带同一方案身份及依据。尤其团队收到询盘时，要能知道客户使用了哪份屋顶、哪些假设、哪些待核项，而不只是收到几个SKU。
4. 对每条输入采用统一EN/DE数值解释与字段校验；无效输入不允许静默变零。自动数据与手绘都能回看、修订、删除和恢复；地图/产量服务不可达时显示明确状态和保留工作。
5. 入口必须兑现其语义：点屋顶先进入屋顶任务，点商用削峰先带商业与目标。初访者在投入填写前知道适用国家、输入要求、会得到什么、哪些仍需安装商/团队核实。

这些是本轮证据导出的需求约束，未指定保留B+C布局、当前路由或组件边界，也未批准任何现有视觉；不在本票施工。

## 未得到本轮完整证据的范围

| 浏览器组合 | 本轮实际观察 | 未由这组截图证明的内容 |
|---|---|---|
| EN1440 | 屋顶深链、空邮编校验、打开屋顶、瓦片失败、产量服务失败与重试入口 | 自动屋面成功、手绘成功、报告/保存成功 |
| EN390 | 新鲜入口下`?step=roof`仍落默认Residential且屋顶关闭 | 手机屋顶绘制、计算与报告全状态 |
| DE390 | 深链；受控Munich气象下的方案/报告、访客保存落登录、改输入旧结果 | 当日真实PVGIS成功、自动屋面成功、登录后保存认领 |
| DE1440 | 商业面板无屋顶入口 | 其他商业/屋顶/报告全状态 |

真实自动屋面成功、实际手绘与几何修订/恢复、下载PDF字节和草稿/账户/询盘消费没有在本轮全部走完；未实测项已经逐项标S或证据缺口。没有登录生产、注册账号、发信或提交询盘。指定Claude审读未完成；本报告不作“全链验收完成”表述，也不宣称完整四组合逐状态矩阵通过。

## 源码索引（均为本票基线123aea57，S级）

- S1：`plugins/linker-tools/includes/Configurator/Mount.php:51,72–115`，深链键与挂载。
- S2：`plugins/linker-tools/src/configurator/config.ts:43–79`，只读dataset、openRoof与预填。
- S3：`plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx:115–151,190–227,394–420,492–517`，内存状态、计算、屋顶挂载和结果操作。
- S4：`plugins/linker-tools/src/configurator/roof/RoofStep.tsx:116–130,142–244,462–488`，地点就绪、航拍与消息状态；没有把瓦片error转为用户状态。
- S5：同文件`:295–342,361–420,444–459,527–647,648–683`，读取/手绘/解析/采纳/列表/假设。
- S6：`plugins/linker-tools/src/configurator/residential/ResidentialForm.tsx:62–100,131–151,205–261`，小数解析、旧roof与新plz、采用后只读。
- S7：`plugins/linker-tools/src/configurator/api/engine.ts:39–68,123–130`，错误映射与pack请求。
- S8：`services/engine/src/linker_engine/models.py:24–42,50–93,314–340`，住宅/手绘边界；生成前端schema同源。
- S9：`plugins/linker-tools/src/configurator/residential/ResidentialPanel.tsx:229–285,317–369,431–442`；`solution/Solution.tsx:319–379`，草稿/保存/Genie/就绪措辞。
- S10：`plugins/linker-tools/src/configurator/App.tsx:39–96,189–208`，默认项目类型和条件挂载；商业面板不接roof。
- S11：`plugins/linker-commerce/includes/Account/SolutionsRoute.php:126–156`；`SavedSolutions.php:95–159`，保存落点与访客会话。
- S12：`plugins/linker-commerce/templates/myaccount/linker-saved-solutions.php:35–59`；`plugins/linker-tools/src/configurator/report/ReportView.tsx:170–180`，账户动作与guest提示差异。
- S13：`services/engine/src/linker_engine/report.py:21–28,60–68,119–134,158–190,264–267,306–378`，报告来源/规则/条件/假设。
- S14：`services/engine/src/linker_engine/texts.py:230–234,502–510,540–609`，超范围/方法/假设/下一步文案。
- S15：`plugins/linker-tools/src/configurator/api/store.ts:100–189`；`plugins/linker-commerce/includes/Inquiry/Sender.php:39–87,138–176`，商品加入与询盘消费者。
- S16：`plugins/linker-commerce/includes/Abilities/ReadSolution.php:194–248,300–353`；`plugins/linker-tools/src/configurator/types.ts:144–167`，已存输入重算与无polygon的输入形状。

在GitHub复核代码时使用固定基线：[123aea57 源码树](https://github.com/AssassinFlash/de-linker/tree/123aea57)。研究分支承载证据，不合并、不部署。
