# 配置器项目类型卡文案对抗评审（fix/configurator-c-fidelity）

规则（AGENTS.md）：客户可见文案初稿 → 评审意见 → 定稿；EN 先行，DE 独立撰写非翻译；
基准 = linker-copywriting Hard Stops + 线上既有措辞与 .po 术语；Sie 体；禁 AI 句式；不发明承诺。
本条是**工具内功能文案**（项目类型选择卡：标题 + 一句范围说明），随 `src/configurator/App.tsx`
交付，DE 落点 `languages/linker-tools-de_DE_formal-linker-tools-configurator.json`。

设计基准（只读）：原型 C 输入屏 `proto-configurator.js` 的 `DEMO.segments`
（`Residential / Commercial & industrial / Utility` 及其三句范围说明）。业主裁定：
三句说明是真实分型事实，不是原型演示数字。

## 1. 定稿与评审

| 卡 | EN 定稿 | DE 初稿 | 评审意见 | DE 定稿 |
|---|---|---|---|---|
| 1 | `Residential` / `Home PV, storage and backup` | `Wohngebäude` / `PV, Speicher und Notstrom fürs Eigenheim` | ① "PV" 单独作前缀不是本站写法，本站既有 `PV array` → `PV-Leistung`、`PV array, existing or planned` → `PV-Anlage, bestehend oder geplant`，改为 `PV-Anlage`；② "fürs" 是口语缩写，正式书面用 `im Eigenheim`；③ `Notstrom` 保留：字段标签用全称 `Notstromversorgung`（`Backup supply` 的既有译法），卡片内三词并列用行业短式 | `Wohngebäude` / `PV-Anlage, Speicher und Notstrom im Eigenheim` |
| 2 | `Commercial & industrial` / `Site load, peak power and operating profile` | `Gewerbe und Industrie` / `Last am Standort, Spitzenleistung und Betriebsprofil` | ① 三段并列要求同为复合名词，`Last am Standort` 破格，行业写 `Standortlast`；② `Spitzenleistung` 是纯物理量、本站无此词；本站的峰值为 `Spitzenlast`（`Peak shaving` → `Spitzenlastkappung`、`Annual peak from the bill` → `Jahreshöchstlast laut Rechnung`），C&I 分型考的正是削峰，故用 `Spitzenlast`；③ `Betriebsprofil` 是标准词，保留 | `Gewerbe und Industrie` / `Standortlast, Spitzenlast und Betriebsprofil` |
| 3 | `Utility` / `Storage blocks, grid connection and project stage` | `Großanlagen` / `Batterieblöcke, Netzanschluss und Projektphase` | ① `Batterieblöcke` 把 EN 的 `storage blocks` 窄化成只含电池，改为 `Speicherblöcke`（覆盖电芯柜与 PCS 柜）；② `Netzanschluss` 与本站既有译法一致（`Grid connection` → `Netzanschluss`），保留；③ `Projektphase` 对 `project stage`，不用 `Inbetriebnahme`（那只指调试那一步），保留 | `Großanlagen` / `Speicherblöcke, Netzanschluss und Projektphase` |

EN 侧评审（定稿即业主给设计基准的三句，逐句核过）：

- 三句都是范围名词短语，无第二人称祈使（Hard Stop 9 Actor），不布置作业。
- 无借来的信誉、无证明清单堆叠、无防御性否定（Hard Stops 1–3）。
- 无时限/无承诺：不出现"很快""保证"；`backup`/`peak power`/`project stage` 是工程事实，不是承诺。
- 一秒测试：安装商办公室文员可读（`Home PV, storage and backup` 与 `Site load, peak power and
  operating profile` 都是站点已用的说法，见 `Backup supply`、`Peak shaving`、`Site conditions`）。

## 2. 对照 Hard Stops 的复核（DE 定稿）

- 无 `du/dein/dich/dir` 形式；无 `Warenkorb|Kasse|Artikel|Katalog`（与 `i18n.test.ts`
  的两条正则一致，测试即门）。
- 三行都没有主语与祈使句，不存在非 Sie 体风险。
- 无 AI 句式：不是三连排比修辞，而是三个并列名词（范围列举）；无"不是…而是…"。
- 术语与既有译文同源：`PV-Anlage`、`Notstromversorgung`/`Notstrom`、`Netzanschluss`、
  `Spitzenlast`、`Stromversorgung` 类词全部取自本文件既有条目。
- 一处一实现：三句只出现在 `App.tsx` 的项目类型卡；`Utility-scale inquiry` 等既有串不动。

## 3. 标签变更（EN 与 DE 同步）

设计基准卡的标题取代了站上原有的项目类型标签：

| 原标签 | 现标签 | DE |
|---|---|---|
| `Residential` | `Residential`（不变） | `Wohngebäude`（不变） |
| `Commercial` | `Commercial & industrial` | `Gewerbe` → `Gewerbe und Industrie` |
| `Utility-scale` | `Utility` | `Großanlagen`（不变） |

这是措辞决定、不是事实问题，按规则由本线定并记录：标题取自业主给的设计基准（原型 C 的
项目类型卡）。已知的措辞张力：本站产品分类与工具区内仍有 `Utility-Scale Storage` /
`Utility-scale inquiry`（`Großspeicher`），即"Utility"这个短标签与之一处宽一处窄；改回去只需
改 `App.tsx` 的两行与翻译文件的两键，故按基准交付并在此显式记录。DE 侧 `Gewerbe und
Industrie` 与分类页 `Gewerbespeicher` 同根，`Großanlagen` 沿用原标签。

## 4. 未决（事实问题）

无。三行不声明价格、时限、资质、证明，也不含目录数据；`i18n.test.ts` 的
"every configurator text has a German translation" 与 "holds only texts the code uses"
两条测试是本文件的机械门。
