# CSV 导入客户文案：初稿与独立对抗审阅

2026-10-23。状态：**review complete / final pending**。评审者只写本记录和 [PROFILE-COPY-DRAFT.json](PROFILE-COPY-DRAFT.json)，未修改 UI、PO、构建物或实例。

本轮新增的用户价值维度是**将一份时间序列资料解释为可检查、可追溯的项目输入**。审查对象是操作说明、字段、质量事实、错误和恢复状态。营销页面的销售话术不适合这层界面；必要的操作指引保留，避免给客户编造采购任务。

## 范围与提取方法

- 基线 HEAD：`220c824e9b3b02409a106d31ee8c6269559ce827`。其 Planner 源码有 **99 条**去重的字面量 `__` 消息，本轮原样保留。
- 对工作树 `ProfileIntake / ProfileMapping / ProfileLabels / ProfileError / ProfileReview / OwnedProfile` 和 `ProjectEditor` 新增段使用 TypeScript AST 提取，取得 **125 条新增消息**。每条原文、源路径、提取时行号、七个文件的 SHA-256 均在 JSON。
- 提取时刻：`2026-10-22T23:26:22.101Z`。这是施工中文案快照；父线持续改 UI，行号会漂移。它不是正式固定 SHA 代码评审。
- 每条均提供独立撰写的 `final_proposed.en / final_proposed.de`。**`final: null` 表示尚待父线取舍与应用**，不代表已发布、已进入翻译包或已获视觉验收。
- “新增消息”按英文 msgid 去重；复用的原 99 条只列入 `reused_messages`。原有 `Save project / Projekt speichern` 等措辞作为相邻语境，未主动重写。
- 另有 **10 条**建议新增或按状态显示的消息 `CSV-A001–A010`。它们不冒充已存在的源码消息。

## 必须收口的四项

父线已采纳下列四个问题的方向；具体 EN／DE 仍以其最终选择为准。

| 编号 | 初稿／问题 | 评审决定与适用条件 |
| --- | --- | --- |
| COPY-01 | `Use this profile in the project` 易被理解成项目已在服务器保存；“Remove selection”也没有明确只改草稿。 | CTA 明确 `open draft`。选择成功后提醒 `Save project`，不得显示成服务器保存回执；移除选择保留原件。见 CSV-122、124、125 与 A002、A003、A009。 |
| COPY-02 | `Source and retention basis` 抽象，帮助只说 privately，未讲清永久存储及用户需要说明的依据。文件名也未成为保存的来源名称。 | 说明来源及**永久私有存储的权限依据**。用用户自己填写的 source label 标识；不擅自保存／展示原文件名。示例是自有电表导出或有权保留的数据，不构成本站核验授权。见 CSV-023–025 与 A003、A004。 |
| COPY-03 | `Retry to confirm its result` 在已经拿到 asset 回执、等待选择时仍出现，而重试按钮已隐藏。队列也可能包含这种已保存但未选择的资料。 | unknown 与 confirmed-awaiting-selection 两态分开。队列中性称 `Imports to review`；若实现保证只收未知回执，原 `Unconfirmed profile imports` 才准确。见 CSV-002、005–007 与 A001。 |
| COPY-04 | 原通用错误 `Your open input has been kept` 也用于只读 preview，且浏览器存储可能失败。 | 通用错误只说明未能确认及重试；仅在真实队列／当前页状态下说明保留范围。浏览器恢复失败不得承诺刷新仍可恢复。见 CSV-004、088 与 JSON 的真实历史 rejected variant。 |

可直接采用的关键对照如下，全部仍是 **final proposed**：

| ID／状态 | EN 建议 | DE 建议 |
| --- | --- | --- |
| CSV-122 · 采用按钮 | Use this profile in the open draft | Profil im offenen Projektentwurf verwenden |
| CSV-A002 · 草稿采用成功 | The profile is selected in the open draft. Save the project to record this selection. | Das Profil ist im offenen Projektentwurf ausgewählt. Mit „Projekt speichern“ wird diese Auswahl im Projekt gespeichert. |
| CSV-005 · 未知回执 | The import result is not confirmed. Retrying uses the original file, mapping and request key. | Das Importergebnis ist noch nicht bestätigt. Ein erneuter Versuch verwendet die ursprüngliche Datei, die Spaltenzuordnung und die ursprüngliche Anfragekennung. |
| CSV-A001 · 原件已确认 | The source is stored. Review its interpretation before selecting it in the open draft. | Die Quelle ist gespeichert. Prüfen Sie die Interpretation, bevor Sie das Profil im offenen Projektentwurf auswählen. |
| CSV-088 · 通用错误 | The data request could not be confirmed. Please retry. | Die Datenanfrage konnte nicht bestätigt werden. Bitte versuchen Sie es erneut. |
| CSV-024 · 留存字段 | Source and permission for permanent private storage | Herkunft und Berechtigung zur dauerhaften privaten Speicherung |
| CSV-025 · 留存说明 | This records where the data came from and your permission to store it permanently with this private project. Examples include your own meter export or data you are authorised to retain. | Hier werden die Herkunft der Daten und Ihre Berechtigung zur dauerhaften Speicherung in diesem privaten Projekt dokumentiert. Beispiele sind Ihr eigener Zählerexport oder Daten, die Sie mit entsprechender Berechtigung aufbewahren dürfen. |

父线提出的操作式帮助 `State where the data came from and your permission to store it permanently with this private project, for example your own meter export or data you are authorised to retain.` 在事实层面也成立。JSON 给出陈述式备选，避免这段变成要求客户额外申请审批的暗示。两者都不声称已验证用户权限，也不承诺任何未实现的删除或数据合规机制。

父线后续取舍已明确：采纳 must-resolve 与实质准确性／精度／清晰度方向；保留 CSV-003、068、078、080、082、090–093 的直白主动操作说明；CSV-021 改完整 sprintf 消息。父线将接手选择最终原句、写 PO 和记录 final，评审者不据此伪填最终文本或刷新初稿来源快照。

## 其余实质意见与精度边界

| 编号／优先级 | 原文或风险 | 明确建议 |
| --- | --- | --- |
| COPY-05 · 语义准确性 | `Total building load` 收窄了 gross_load 的整个站点边界；`Recorded PV generation` 容易先声称实测，但 source type 可选 modelled。净输入说明还可能使人误以为站点必定已有 PV／储能。 | CSV-057 用 `Total site load / Gesamte Standortlast`；CSV-061 用 `PV generation · AC / PV-Erzeugung · AC`；来源是否 measured 留给独立来源声明。CSV-107 用 `can be affected`；A005 说明净电量是区间内进口减出口。不要据净输入反推总站点消耗。 |
| COPY-06 · 数据定义 | 共享 review 可展示 PVGIS 模型来源，不能一律标 user declaration；数据可测得／建模／模板／测试生成，`Select what was measured` 过窄。瞬时样点、区间均值和区间能量须分清。只写 daylight-saving 也过窄，IANA 历史缺时可来自其他时钟调整。 | CSV-094 复用 CSV-042 的 \`Source type / Art der Datenquelle\`，不新增另一条翻译。新增 \`Original value meaning / Bedeutung der Originalwerte\` 见 A010。CSV-034 讲 values represent；CSV-036–038 明确仅 kW 区间均值／kWh 区间能量。CSV-073 用 clock change。CSV-083 同时覆盖有限范围和正负号，避免非有限功率也只提示负号。错误提示不声称源可自动修复。 |
| COPY-07 · 错误定位 | `Physical line` 技术上正确，但客户可能按 Excel 行号查。 | CSV-020、089 用 starting file line；A006 解释空行和引号内换行计入文件行。它不是 profile interval index，也不回显原值、列名值或文件名。 |
| COPY-09 · 本地化组合 | 当前“本地化数字 + 英文片段 `data records; ...`”在 1 条数据时产生 `1 data records`，也限制译文语序。 | CSV-021 改为一个含 `%s` 的完整可翻译消息，传入已按 locale 格式化的计数。此条需要父线同步改调用，不能只把带占位符的译文塞进旧拼接位置。 |
| COPY-10 · 质量术语 | “Missing duration”仅指第一至最后已提供区间之间的缺口，不等于目标年缺失量。“Interpretation SHA-256”实际是包含来源／映射／依赖的 metadata hash。 | CSV-098 明确 within source period；CSV-118 称 Import metadata SHA-256。CSV-100 用 longest 而非 largest 表达时间。Effective resolution limit 可保留；A008 解释更短输出步长不增加原始观测精度。 |
| COPY-08 · 可选文风 | provenance、captured、inspect 等在首轮操作上偏内部记录语言；很多提示可直接说明约束。 | JSON 将其标为 optional style／plain language，不当工程阻断。CTA、字段、错误修复指引允许必要动作语；不新增营销强词、虚构速度、认证或客户任务。 |

`Energy in covered intervals`、源起止 UTC、原生／有效分辨率、最小／最大区间均值、缺口与 transformation 信息都应保留。不能为简短删除单位、条件或适用边界。A005 只在 net_import 下显示。小时均值没有变成瞬时峰值，也没有自动变成计费需量；资料可解释与适合具体工程计算仍是两件需要分别证明的事实。

JSON 中每条有 `review.priority`，用于区分：
- 四项状态／承诺问题：`must_resolve_before_copy_acceptance`；
- 其他事实边界：准确性／精度建议；
- 纯文风：可选，父线可以保留原句；
- 原 EN 合格：`keep_english`，只提供 DE。

## 英德术语与语气

- **Interval data → Zeitreihendaten**：此面同时承接站点负荷、净输入、PV 与辅助用电。具体负荷资料可称 Lastgang；所有来源都叫 Lastgang 会错误地缩成用电资料。
- **Open draft → offener Projektentwurf**：这里指浏览器可编辑项目草稿，避免与商务链 `Solution draft / Lösungsentwurf` 混为同一清单。
- **Net grid import → Netto-Netzbezug**；负值清楚称 Einspeisung。
- **Interval-average power → mittlere Leistung je Intervall**；kW、kWh、UTC、ISO 日期示例按真实含义保留。
- **Repeated-time column → Spalte für doppelte Ortszeiten**：帮助明确 0／1 第一次／第二次；offset 仍优先且不能同时提供 fold。end 列独立说明，见 A007。
- DE 独立按语境撰写，使用 Sie／Ihre，不用 du／dein，不套英语词序。点／逗号示例是**文件数据格式选项**，DE 不得把 `Point · 12.5` 的 12.5 改成 12,5，否则两个选择失去差别。
- 闭合的 source／mapping／request key 可放在深层详情；按钮不使用 source hash、版本号、内部 RPC 或“兼容放行”作卖点。

## 对抗检查与结果

已加载 [linker-copywriting 技能](/Users/chesterjohn/.agents/skills/linker-copywriting/SKILL.md)、其百科、anti-patterns 与 positive examples。百科中旧商业链、工具命名／存废等描述与现行 AGENTS、CONTEXT、当期产品决定冲突的部分未作为本次事实依据。正例中 ROI、固定 15 分钟等也未当本站承诺。

本轮证据依据：
- [资料解释合同](../../../specs/548-profile-intake-view.md)；
- [成熟导入模式研究](../../../research/2026-10-23-profile-intake/RESEARCH.md)；
- 上述七个实际工作树组件及其调用状态；
- 父线本轮明确给出的私有原件、选择／保存、未知回执和 source label 产品事实。

Pre-delivery：
- [x] 百科加载；本段维度为资料解释与项目采用，沿用 load profile／Lastgang 等常用概念。
- [x] 没有借厂商品牌／认证抬高本站，没有虚构精度、速度、ROI 或现场服务。
- [x] 原始单位、净输入边界、缺口、来源声明与草稿／服务器保存条件保留。
- [x] 没有虚构客户动机、未来项目或采购任务。必要的界面动作、错误修复说明保持可执行。
- [x] Actor／Future／Weight／Duration 检查按本操作面的真实任务应用；无营销式“请给我们发资料”或空泛持续服务。
- [x] 不使用“X 不是 Y 而是 Z”营销句式或三连口号；真实技术选项及错误条件的否定说明保留。
- [x] 不生成评价、背书或第三方引语；ISO 时间和数字例子是格式示例。
- [x] JSON 中全部 EN／DE 已审阅，`%d`／`%s` 需同步实现的合同明确。
- [ ] 父线选择最终 EN／DE 并更新 `final`。
- [ ] UI／PO／逐脚本 JSON 实际采用与覆盖证明。
- [ ] 固定 SHA Spec／Standards 和 EN／DE × desktop／mobile CUA。

**当前不能写“文案定稿／已部署／界面已通过”。** 父线定稿后应记录：选择哪些 CSV ID、最终 EN／DE、应用 commit、gettext bundle 覆盖与实际显示证据。若父线修改建议文本，应保留 original → review → selected final 的轨迹。该记录不替代正式代码或视觉验收。

## Server-confirmed selection notice

The independent Spec reviewer approved the exact pair “This profile selection is saved with the project.” / “Diese Profilauswahl ist im Projekt gespeichert.” The parent selected and applied it. This notice requires an owned import receipt whose asset ID is present in the server-confirmed project baseline. An open draft selection keeps the earlier save reminder. Native gettext was regenerated for the actual `build/planner/assets/planner.js` entry; visual verification remains a separate gate.
