# 548 · 18 个电池产品 sales_unit 取证（2026-11-03）

引擎准入门：`services/engine/src/linker_engine/planning/equipment_search_space.py:49-60` 要求
`evidence.sales_unit(pid) ∈ {battery_module, battery_system}` 才入电池候选池；此前 18 个产品全部因
`sales_unit_evidence_missing` 被排除。本文件把每个产品的判定固定到「托管文档 + 页码 + 原文」；
机器可读版（含 document_id / document_revision / blob_sha256）在 `sales-unit-draft.json`。

取证方式：只读 FTS5 检索自托管知识索引（143 份文档，按页切片，
`/opt/linker-genie/index/current/index.sqlite`，经 `ssh linker-services`）；引文为索引内 PDF 原文，
页码为索引页码；三组哈希（document_id / document_revision / blob_sha256）于 2026-11-03 从生产 feed
`/opt/linker-engine/state/current/feed.json` 读回。先例：`tools/migrate/548-batc-sales-unit.json`。

## 结论总表

| 产品 | SKU | 型号 | sales_unit | 模块数/单元 | 准入 |
| --- | --- | --- | --- | --- | --- |
| 1832 | DLK-SAJ-B250HV1 | B2-5.0-HV1 | battery_system | 1 | 是 |
| 2067 | DLK-SAJ-B2100HV1 | B2-10.0-HV1 | battery_system | 2 | 是 |
| 2068 | DLK-SAJ-B2150HV1 | B2-15.0-HV1 | battery_system | 3 | 是 |
| 2069 | DLK-SAJ-B2200HV1 | B2-20.0-HV1 | battery_system | 4 | 是 |
| 2070 | DLK-SAJ-B2250HV1 | B2-25.0-HV1 | battery_system | 5 | 是 |
| 2090 | DLK-SAJ-BU250HV1 | BU2-5.0-HV1 | battery_module | — | 是 |
| 2092 | DLK-SAJ-BC2HV1 | BC2-HV1 | battery_controller | — | 否（非电池） |
| 2093 | DLK-SAJ-BU350TV2PRO | BU3-5.0-TV2-PRO | battery_module | — | 是 |
| 3611 | DLK-GOODWE-GW60BATDG20 | GW6.0-BAT-D-G20 | battery_module | — | 是 |
| 3612 | DLK-GOODWE-GW90BATDG20 | GW9.0-BAT-D-G20 | battery_module | — | 是 |
| 4103 | DLK-SAJ-CB2573HV5 | CB2-57.3-HV5 | battery_system | 4 | 是 |
| 4104 | DLK-SAJ-CB2716HV5 | CB2-71.6-HV5 | battery_system | 5 | 是 |
| 4105 | DLK-SAJ-CB2859HV5 | CB2-85.9-HV5 | battery_system | 6 | 是 |
| 4106 | DLK-SAJ-CB21003HV5 | CB2-100.3-HV5 | battery_system | 7 | 是 |
| 6519 | DLK-GOODWE-GW51BATDG20 | GW5.1-BAT-D-G20 | battery_module | — | 是 |
| 6520 | DLK-GOODWE-GW83BATDG20 | GW8.3-BAT-D-G20 | battery_module | — | 是 |
| 6521 | DLK-GOODWE-GW51BATDG21 | GW5.1-BAT-D-G21 | battery_module | — | 是 |
| 6522 | DLK-GOODWE-GW83BATDG21 | GW8.3-BAT-D-G21 | battery_module | — | 是 |

## 1. SAJ B2 系统（1832、2067–2070）：battery_system

每个 B2-XX 型号是**一个完整的电池系统**（BU2-5.0 模块 × N 垂直堆叠 + BC2-HV1 控制模块）：

- **B2 Series Datasheet (EN, BEU) p.2**（doc-2a01f2dd…，`B2-5-25K-HV1HV5-datasheet-EN-BEU.pdf`）：
  规格表 `Battery Module | BU2-5.0-HV1 (32S1P 102.4V50Ah) | … | No. of Modules | 1 | 2 | 3 | 4 | 5 |
  Rated Energy [kWh] | 5.0 | 10.0 | 15.0 | 20.0 | 25.0` —— 型号列即系统容量，模块数随型号固定。
- **B2 User Manual (EN) p.8**（doc-08413cff…）：`B2 battery is a high voltage battery system. The battery
  employs modular design for easy installation and wiring.`
- **B2/BU2 EU DoC p.1**（doc-ab0e445b…）：`Product name: Battery system Model: B2-5.0-HV1, …, B2-25.0-HV5
  BU2-5.0-HV1, BU2-5.0-HV5`（DE 版 p.12 同：`Batteriesystem`）。

每型号模块数（datasheet p.2 与 manual p.10 一致，可作 `modules_per_stack` 定值）：B2-5.0=1、B2-10.0=2、
B2-15.0=3、B2-20.0=4、B2-25.0=5。

## 2. SAJ BU2-5.0-HV1（2090）：battery_module

- **B2 Series Datasheet (EN, BEU) p.2**：规格表 `Battery Module` 行明确为 `BU2-5.0-HV1 (32S1P 102.4V50Ah)`
  —— 一个 BU2-5.0-HV1 SKU 就是组成 B2 系统的那节 5.0 kWh 电池模块。
- 冲突记录：B2/BU2 EU DoC p.1 把 BU2-5.0-HV1/HV5 与全部 B2 型号一起列在 `Product name: Battery system`
  之下，属监管家族命名，非逐 SKU 结构陈述；按业主 2026-10-09 裁定（产品事实冲突以托管数据手册为准），
  以 datasheet 结构行为准 → battery_module。

## 3. SAJ BC2-HV1（2092）：battery_controller，不适用准入枚举

- **B2 Series Datasheet (EN, BEU) p.2**：`Control Module | BC2-HV1 | … | Max. Fault Current [A] | 100 |
  Dimension (H*W*D)[mm] | 200*626*365 | Weight [kg] | 11`。
- **B2 User Manual (EN) p.10**：型号表 `Control Module | BC2-HV1 | BC2-HV1 | BC2-HV1 | BC2-HV1 | BC2-HV1`。
- **B2/BC2 EU DoC p.1**（doc-94a13a0d…）：`We declare under our own responsibility that the product:
  Model: BC2-HV1`。

BC2-HV1 是 B2 堆叠的高压电池控制模块（BMS 顶控单元），不是电池；`battery_controller` 不在
`{battery_module, battery_system}` 枚举内，2092 按设计继续排除。

## 4. SAJ BU3-5.0-TV2-PRO（2093）：battery_module

- **BU3-5.0-TV2-PRO Battery Module (HS3) Datasheet (EN, EU) p.1**（doc-df9998a7…）：`Battery module
  integrated with a DC/DC optimiser, expandable whenever you need BU3-5.0-TV2-PRO`。
- 同 datasheet p.2 规格表：`Module | BU3-5.0-TV2-PRO | … | Rated Energy [kWh] | 5 | Usable Energy [kWh] | 4.8`。
- 冲突记录：BU3/BC3 EU DoC p.1（doc-bd73a72e…）同样用 `Product name: Battery system` 覆盖 BU3 全家族与
  BC3-TV 控制单元；专属 datasheet 措辞为准（业主 2026-10-09 裁定）。

## 5. SAJ CB2（4103–4106）：battery_system，模块数 4/5/6/7

- **CB2 User Manual (EN V0.0) p.8**（doc-62719dde…）：`The CB2 battery system is a high-voltage battery
  system that can integrate in the commercial and industrial (C&I) photovoltaic storage solutions. …
  One CH2 inverter can be integrated with four CB2 battery systems at maximum.`
- 同手册 p.12 规格表：`Model | CB2-57.3-HV5 | CB2-71.6-HV5 | CB2-85.9-HV5 | CB2-100.3-HV5 | …
  No. of Battery Modules | 4 | 5 | 6 | 7` —— 每型号为整机柜系统，内部模块数固定。

## 6. GoodWe Lynx D G2（3611、3612、6519、6520、6521、6522）：battery_module

每个 GW x.x-BAT-D-G2x SKU 是**一节可堆叠的电池模块**（单节自带 BMU，堆叠/并联组成系统）：

- **Lynx D G2 Datasheet (EN, EMEA V1.1) p.1**（doc-595423f7…）：`Each battery pack is a standalone unit
  with a dedicated Battery Management Unit (BMU), supporting up to 12 units in parallel and multicluster
  expansion. It also supports mixing of new and existing battery packs as well as different capacity
  modules, ensuring flexible and future-ready scalability.`
- 同 datasheet p.2：`Technical Data GW5.1-BAT-D-G20 GW8.3-BAT-D-G20 GW6.0-BAT-D-G20 GW9.0-BAT-D-G20`
  —— 四个 G20 型号各占一列，每列一个单节规格（仅覆盖 G20，不含 G21）。
- **ESA 5-30 kW User Manual (EN V1.4) p.47**（doc-ef7a3102…）：`The system supports battery capacity
  expansion, and the total battery capacity is determined by the quantity and specifications of battery
  modules. … A：GW5.1-BAT-D-G20，GW5.1-BAT-D-G21，GW6.0-BAT-D-G20 B：GW8.3-BAT-D-G20，
  GW8.3-BAT-D-G21，GW9.0-BAT-D-G20` —— G20 与 G21 同表按节数堆叠。
- 同手册 p.33：`Different models of battery modules support mixed use. • System supports 5-108kWh`。

G21（6521、6522）在 Lynx D G2 datasheet V1.1 中未列出；其证据取自 ESA 5-30 kW 文档（user manual
p.47/p.33、quick installation guide V1.7 p.1 堆叠表 `Battery Stack Quantity`），两处均按电池模块混用、
按数量堆叠描述。

## 落库提示（不属于本文件结论）

- `battery_system` 的 9 个产品可同时引用模块数定值（B2：datasheet p.2；CB2：manual p.12），
  契合 `battery_assembly` 的 `fixed_modules_per_stack` 语义。
- SAJ DoC 的 `Product name: Battery system` 是家族级监管命名（B2/BU2/BU3 三份 DoC 同一写法），
  不能单独用作逐 SKU 的 sales_unit 证据；须绑定 datasheet/manual 的结构性表述。
