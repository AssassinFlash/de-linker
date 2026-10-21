# #482 / #483 engine copy · 定稿

状态：定稿（对抗评审，2026-10-21）。改动的客户可见文案都在引擎 `texts.py` 与
`data/compatibility.json` 的放行条件里；前者随方案屏与设计报告出现，后者出现在
逆变器行的“随机附电表”依据与检查器证据里。

## 1. 新增与改写的串

| 位置 | EN 定稿 | DE 定稿 |
| --- | --- | --- |
| `rule.backup_storage` | `Released battery configuration covers the backup reserve` | `Freigegebene Batteriekonfiguration deckt die Notstromreserve` |
| `value.backup_storage` | `{value} kWh usable for a {limit} kWh reserve` | `{value} kWh nutzbar für eine Reserve von {limit} kWh` |
| `relax.backup_storage` | `Less backup reserve: the largest released configuration in this selection holds {kwh} kWh.` | `Kleinere Notstromreserve: Die größte freigegebene Konfiguration dieser Auswahl fasst {kwh} kWh.` |
| `relax.backup_storage_none` | `Less backup reserve: no released configuration in this selection can hold it.` | `Kleinere Notstromreserve: Keine freigegebene Konfiguration dieser Auswahl kann sie aufnehmen.` |
| H2 meter condition | `The H2 T3 ships with a smart meter, three current transformers and a 10 m meter communication cable (H2 manual, section 2.2 Unpacking, PDF p. 36 English / p. 7 German).` | `Der H2 T3 wird mit einem Smart Meter, drei Stromwandlern und einem 10 m langen Zähler-Kommunikationskabel geliefert (H2-Handbuch, Abschnitt 2.2 Auspacken, PDF-S. 36 englisch / S. 7 deutsch).` |
| `warn.no_storage_backup` | `With less than 0.5 kWp of PV per MWh of consumption, HTW Berlin advises against a battery for self-consumption. The battery in this proposal holds the backup reserve.` | `Bei weniger als 0,5 kWp PV-Leistung je MWh Verbrauch rät die HTW Berlin von einem Batteriespeicher zur Eigenverbrauchsoptimierung ab. Der Speicher in diesem Vorschlag deckt die Notstromreserve.` |

删除的旧串：`rule.backup`（`Backup supply`）、`value.backup.native/accessory/none`、
`relax.backup`（`Accept an accessory for backup supply.`）。旧串只服务于已移除的
“备电输出”硬资格，不再出现在任何客户可见面。

## 2. 对抗评审记录

- **事实基准**：H2 手册 §2.2 Auspacken（PDF-S. 36 英文 / S. 7 德文）逐项列出
  `Smart meter *1`、`Current transformer *3`、`Meter COMM cable *1 (10m)`；原条件写的
  §4.1.2 / PDF-S. 12 不符，已改正。备电句的 `{kwh}` 来自客户输入（3 kW × 4 h）与
  引擎既有的放电效率，不是新常数。
- **EN 先行**：新句都是陈述句或名词短语，无第二人称、无承诺、无时限；`released battery`
  与 `usable` 沿用引擎既有措辞（`Battery released by the manufacturers`、
  `Proposed usable capacity`），`backup reserve` 与报告既有行
  `Usable capacity, HTW upper limit plus backup reserve` 同词。
- **DE 独立撰写，非英文直译**：`Freigegebene Batteriekonfiguration` 沿用 `Battery released by the
  manufacturers` 的既有译法 `Batterie von den Herstellern freigegeben` 的词干；
  `Notstromreserve` 沿用报告既有 `Notstromreserve`；`nutzbar` 沿用
  `Nutzbare Kapazität`；`fasst` 用于电池容量是德语常规搭配；`Auswahl` 指本次候选集。
- **Sie 体与禁词**：无 du/dein 形式；无 `Warenkorb|Kasse|Artikel|Katalog|catalogue`；
  无“不是…而是…”与三连排比；不出现旧政权编号。
- **英德同义**：EN `holds {kwh} kWh` = DE `fasst {kwh} kWh`；EN `can hold it` =
  DE `kann sie aufnehmen`；`Less backup reserve` = `Kleinere Notstromreserve`，
  都是“降低预留”的放宽方向，不把无候选说成系统错误。`warn.no_storage_backup` 只在
  HTW 不建议配储、但客户要备电时出现：EN 说“电池用于自助消费不被建议，提案中的电池
  覆盖备电预留”，DE 用 `Eigenverbrauchsoptimierung` 与 `Notstromreserve`，同义；
  它取代原来“提案只含逆变器、电池以后再加”的句子，避免与所选备电电池矛盾。
- **一处一实现**：新串只在 `services/engine/src/linker_engine/texts.py`；H2 条件在
  `plugins/linker-commerce/data/compatibility.json`（运行时合同）、
  `plugins/linker-commerce/data/compatibility-lists.json`（合同数据源）与
  `services/engine/scripts/build_fixtures.py` 的生成器覆盖里是同一句，引擎测试夹具
  用它生成；UI 不复制。
- **结论**：通过，可上线。
