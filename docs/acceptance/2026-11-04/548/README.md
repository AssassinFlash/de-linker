# #548 · 2026-11-04 厂商证据大批量落库（计划与验证）

本批把 `docs/acceptance/2026-11-03/548/manufacturer-evidence.md` 的厂商事实一次性写成
**冻结的迁移计划**，并修掉执行过程中发现的三处真实缺陷。生产写入由父线统一执行；
本文件只记录计划、验证结果与未被写入的项。

分支 `fix/548-evidence-mega-batch`，PR #895。

## 1. 已完成

### (a) 电池并联上限 → `tools/migrate/548-battery-parallel-limits.{json,py,php}`

落点经过核对：`services/engine/src/linker_engine/planning/equipment_assessment.py:548` 读的是
`number(battery_id, "stacks_parallel_max", "count")`，即 **Woo figure**；
而 `services/engine/schemas/compatibility.schema.json` 把 `max_units` 定义为
「the most inverters one controller coordinates」。两者不是同一个概念，所以电池簇上限写 figure，
控制器上限才写 `max_units`。

| 产品 | `stacks_parallel_max` | 引用 |
| --- | --- | --- |
| 1956、1957 | 4 | `GW_BAT-C-208-261kWh_User-Manual-EN.pdf` p.53 |
| 3611、3612、6519、6520 | 12 | `GW_Lynx-D-G2_Datasheet_EU-EN_V1.1.pdf` p.1 |
| 6321 | 8 | `GW_ESA-261kWh_User-Manual-EN_V1.6.pdf` p.46 |
| 2003 | 6 | `OPTIMUSL260-OMNI_20240926105739A032.pdf` p.2 |

**没有写入的**（计划内 `unbound` 段逐条说明原因）：ET 50–100 kW 的「15 台逆变器并联」是系统上限；
SAJ B2/BU2 与 HS3 已由 `modules_per_stack_max` 表达；CB2 × CH2 是「每台逆变器接几个电池系统」，
没有 figure 能表达；BAT-S 系列在 feed 里没有产品；6521/6522 的 datasheet 未与之关联。

### (b)(d)(e) 安装事实 → `tools/migrate/548-installation-facts.json`

91 → **244 条 / 37 个产品**。

新增端子图（`basis: manufacturer_terminal_map`），每个机型族的域与页码见
`terminal-map-coverage.md`：ET、ETR、ESA 5–30 kW、ESA 3–10 kW、SAJ H2。

1954 装箱事实：`pack-interconnection-harness` ×5（p.34）、`expansion-anchor` ×4（p.33）。
该手册已在生产托管（`GET` 200，sha256 `c29cbf257d51…` 与 feed 一致），**不需要「先托管」步骤**。

revision 重绑：1946/1947/1948/1954–1958/6506 九个漂移产品，加 ETR 四型（6508–6511），
全部取生产 `engineering-feed` 的当前 `product_revision`。

### 本批修掉的三处真实缺陷

1. **70 条 quote 是改写而非原文**：1946/1947/1948/6506 各 10 条、1956/1957/1958 各 6 条、6508–6511 各 3 条（用严格归一化包含逐个核对原计划得出）。
   `InstallationFacts::bind()` 只校验文档关联与页码合法，不校验 quote 是否真在该页，
   所以这些 quote 一直没被发现。现在改为从 PDF 页面逐字提取，并加测试
   `test_every_quote_appears_on_the_page_its_source_cites`，用 `548-page-excerpts.json`
   （26 页原文摘录，31 KB）在 CI 里断言。**这条测试同时是今后所有安装事实的闸门。**
2. **1956–1958 的 COM 端子页混用了两处原文**：p.23 的 COM1/COM2 描述与 p.69/70 的措辞被拼在一起。
   已按 p.23 原文重写。
3. **`manufacturer-evidence.md` §3 的页码指向错误文档**：COM1/COM2/COM3 不在 65 页的
   ET 50–100 kW EN V1.3 里，只在 307 页的 `GW_ET-100kW_User-Manual-EN_V1.2` 里。
   本批按后者绑页，并在 `terminal-map-coverage.md` 记录。

### 这批 figure 不会自动放大搜索范围（如实说明）

`stacks_parallel_max` 落库后，`equipment_assessment.py` 的 `parallel_stacks` 判定就有了可核对的上限，
但 `equipment_search_space.py:180` 仍固定 `parallel_stacks = 1`，注释写明
「The supported template has one external battery assembly. No undocumented parallel count is invented to
satisfy demand.」也就是说：**本批补的是证据，不是新的搜索能力**。要让配置器真的给出多簇方案，
需要另一次产品裁定（模板是否支持外部多簇、报表如何呈现），不在本批范围。

同理，SEC3000C 的 `max_units = 60` 只对**显式选择了该控制器**的并联组生效
（`applicability.controller_product_id = 2409`），不会让裸并联的逆变器凭空获得上限。

### 兼容合同 SEC3000C 60 / 10

`compatibility.json` 的 LAN 方案原本 `max_units` 为空。现在：

- LAN 方案 `max_units = 10`
- 新增 RS485 方案 `max_units = 60`，并引用 SEC 手册 p.53「单路 RS485 最多 20 台」与 p.19 端口占用
- `version` 按内容哈希重算（`cea8748a…` → 最终值见文件）

引擎测试同步更新：`test_shipped_et_lan_scheme_…` 从断言 `max_units is None` 改为 `== 10`，
并新增 `test_shipped_et_rs485_scheme_carries_the_sixty_inverter_limit`。
**原断言把「没有证据」当成了规则本身**，这是本轮修掉的第四个问题。

## 2. 阻塞，未落库

### (c) 52 条电缆载流数据

`docs/acceptance/2026-11-03/548/evidence/cables.json` **不存在**（仓库、32 个远端分支、
`.codex/worktrees`、`de-linker-data`、`/tmp` 全无）。`manufacturer-evidence.md` §6 同样列为未解决。

即使拿到数据，现有契约也拒绝大部分行：`CableReferenceCurrentRating` 只允许三种单芯敷设方式，
`CableFacts` 在 `construction != single_conductor` 时拒绝载流表（Python 与 PHP 双侧一致）。
详见 `cable-blocker.md`。

## 3. 验证

| 检查 | 结果 |
| --- | --- |
| `tools/migrate` ruff / format / `mypy --strict`（74 文件） | 通过 |
| `tools/migrate` pytest | **366 passed, 32 skipped** |
| `services/engine` 全量 | **1319 passed**（6 分 32 秒） |
| `services/engine` `test_compatibility.py` | **21 passed** |
| `plugins/linker-commerce` PHPUnit（Compatibility/EngineeringData/EngineeringFeed） | **66 passed / 641 assertions** |
| `plugins/linker-commerce` PHPStan | No errors |
| `tools/checks`（Python 3.12，CI 用的版本） | **63 tests OK** |
| 244 条事实经真实 `InstallationFacts::bind()` | **37 产品 / 244 条 / 0 错误** |
| 244 条 quote 对所引 PDF 页 | **244/244 命中** |
| 8 条并联上限 quote 对所引 PDF 页 | **8/8 命中** |
| `compatibility.json` version = 内容哈希 | 通过 |

`tools/checks` 用本机默认 `python3`（3.9）会报 3 个语法错误（`zip(strict=)`）；同样的错误在
`main` 上存在，与本次改动无关，CI 使用 3.12。

## 4. 生产写入

本 PR 只提交计划与测试，**未执行任何生产写入**。父线按既有 `preview → apply → rollback`
流程执行时需注意：

- `548-battery-parallel-limits.py` 只有 `preview` / `apply` / `rollback` 三个动作；
  `apply` 自身带读回校验且幂等，没有独立 `verify`（早期版本把 `verify` 放进写入分支，已修）。
- `548-installation-facts.py` 的 `refresh` 可重新钉当前 revision，用于 apply 前确认。
- 每个迁移都需要新的 0600 receipt，且不会覆盖已有 receipt。
