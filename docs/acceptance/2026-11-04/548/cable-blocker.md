# #548 · 电缆载流数据（c) 的阻塞记录（2026-11-04）

任务要求把 `docs/acceptance/2026-11-03/548/evidence/cables.json` 里的 **52 条电缆载流数据**
按引擎消费端真实 schema 写入 `plugins/linker-commerce/data/cable-references.json`。
本文件记录为什么这一项**没有落库**，以及要落库必须先满足什么。

## 1. 输入文件不存在

`docs/acceptance/2026-11-03/548/evidence/` 下只有：

- `conductor-facts.json`（导体截面推荐，不是载流表）
- `gateway-limits.json`（SEC3000C 等组网上限）
- `sales-unit-draft.json` / `sales-unit-draft.md`
- `etr-walk/`（截图）

没有 `cables.json`。已核对的检索范围：

| 范围 | 结果 |
| --- | --- |
| 仓库全树（含 `.scratch`） | 只有 `conductor-facts.json`，无 `cables.json` |
| 全部 `origin/*` 分支（32 个） | 无 `cables.json` |
| `/Users/chesterjohn/.codex/worktrees` | 无 |
| `/Users/chesterjohn/de-linker-data`（含 `pdf/`、快照） | 无 |
| `/tmp`、`/private/tmp` | 无 |

`manufacturer-evidence.md` §6 自己也把这一项列为**已知未解决**：
「AC/多芯/>6 mm² 载流表（`cable-references.json` 仍只有 2 根单芯 DC 光伏电缆）」。
即这份数据从来没有产出过，不是本轮丢失。

**结论：没有可用的输入数据。本项无法在本轮落库，且不能靠推断补造（AGENTS.md §6）。**

## 2. 引擎契约本身也挡着多芯与 AC

即使数据到手，现有消费端会拒绝大部分行。两处硬闸门：

`services/engine/src/linker_engine/planning/cable_facts.py`：

```python
class CableReferenceCurrentRating(Document):
    id: Identifier
    laying: Literal["single_in_air", "single_on_surface", "two_touching_on_surface"]
    ambient_temperature_c: Number
    rated_conductor_temperature_c: Number
    current_a: Positive
    source: CableEvidence

class CableFacts(Document):
    construction: Literal["single_conductor", "multicore_cable"]
    ...
    @model_validator(mode="after")
    def identities(self) -> Self:
        ...
        if self.reference_current_ratings and self.construction != "single_conductor":
            raise ValueError("reference-current table requires a single conductor")
```

`plugins/linker-commerce/includes/Products/Publication/CableFacts.php:72` 是同一规则的 PHP 侧副本：

```php
if ( ! is_array( $raw['reference_current_ratings'] ) || ! array_is_list( $raw['reference_current_ratings'] ) || ( array() !== $raw['reference_current_ratings'] && 'single_conductor' !== $raw['construction'] ) ) { ... }
```

即：**多芯电缆不允许带载流表**，而任务里的 52 条明确包含「AC / 多芯 / >6 mm²」。
`installation_reference_current.py` 的方法名也写死为
`installation_single_conductor_reference_current_v1`，报告层只呈现单芯对比。

这两处不是笔误：`CableReferenceCurrentRating` 的 docstring 说得很清楚——
「One cited manufacturer table row, not a site ampacity clearance」。当时的建模范围就是
「单芯 DC 光伏电缆的厂商表行」。

## 3. 要解除阻塞，需要的不是数据，是裁定

按 AGENTS.md §2「本轮发现的问题必须在本轮解决」的字面要求，这里本应直接改底层。
但改它意味着**扩大产品语义**，不是修 bug：

1. 多芯电缆的载流表必须带「芯数 × 截面 × 敷设方式」的组合键，而 `CableReferenceCurrentRating`
   现在只有单值 `current_a` 与 `cross_section_mm2`（在 `CableFacts` 上，单值）。
   一条多芯行表达的是「4×50 mm² 五芯在空气中」，与现有单值模型不同构。
2. AC 载流还与频率、功率因数、三相平衡有关，现有 `parameter_sets` 的 AC 分支要求
   `frequency_hz` + `reactance_ohm_per_km` + `arrangement`，而载流表没有这些字段。
3. 报告与 UI（`apps/planner/src/components/installation/CableReferenceFacts.tsx`）只渲染单芯对比。

在没有原始载流数据的前提下改这个模型，等于**凭空设计一个我们无法用证据验证的 schema**，
与 §6「不天然相信数字、无依据直接修底层」的方向相反：这里缺的正是依据。

## 4. 本轮实际做了什么

- 不伪造 52 条数据，不把 `conductor-facts.json` 的截面推荐当成载流表。
- 在 `manufacturer-evidence.md` §6 已列的三项之外，把**引擎契约的第四项限制**
  （多芯不得带载流表、AC 载流缺字段）记录在本文件，避免下一个人再误以为「只要补数据就行」。
- 已落库的两条单芯 Nexans 记录保持不动（它们本来就符合契约）。

## 5. 解除条件（可核对）

要真正落库，需要同时具备：

1. 原始载流数据（每行：型号 / 芯数 / 截面 / 敷设方式 / 环境温度 / 导体温度 / 电流 / 文档页 + 原文）。
2. 对「多芯 + AC 载流」建模的裁定（谁能写、报告怎么呈现、与单芯是否共用一张表）。

在此之前，`plant_assessment` 的载流判定对多芯与 AC 保持 `unresolved` 是**正确行为**，
不是待修缺陷。
