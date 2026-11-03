# #548 · 厂商证据冲突裁决（2026-11-04）

`docs/acceptance/2026-11-03/548/manufacturer-evidence.md` §4 列了四处**文档互相矛盾**的厂商事实。
业主既定裁定（AGENTS.md §2，2026-10-09）是「产品事实冲突时以我们托管的数据手册为准」。
本文件逐处按该裁定裁决，并记下依据的文档、页与原文。

裁决只对**可核对的字面事实**生效。凡是数据手册没有载明的，一律保持 `unresolved`，不用推理补。

## 1. GoodWe GW6.0-BAT-D-G20 · 可用能量

| 来源 | 值 | 原文 / 位置 |
| --- | --- | --- |
| Lynx D G2 datasheet（EU, EN, V1.1） | **5.8 kWh** | p.2 `Usable Energy (kWh) 5.0*1 8.0*1 5.8*2 8.7*2` |
| ESA 5–30 kW Benutzerhandbuch（DE, V1.4） | 5.9 kWh | PDF p.368 `Nutzbare Energie (kWh)*1 5.9 8.85` |

**裁决：5.8 kWh。** 依据：产品 3611 的关联文档里，英文 Lynx D G2 datasheet 直接列出该型号的可用能量并带脚注；
德语 ESA 手册是**同一数据表的德文版本**，两者差异属版本漂移。按「以我们托管的数据手册为准」，
英文 datasheet 是 spec sheet 本体，取 5.8。
德语手册的 5.9 保留在文档内可见，不改写厂商正文。

## 2. GoodWe GW9.0-BAT-D-G20 · 可用能量

| 来源 | 值 | 原文 / 位置 |
| --- | --- | --- |
| Lynx D G2 datasheet（EU, EN, V1.1） | **8.7 kWh** | p.2 `Usable Energy (kWh) … 5.8*2 8.7*2` |
| ESA 5–30 kW Benutzerhandbuch（DE, V1.4） | 8.85 kWh | PDF p.368 `Nutzbare Energie (kWh)*1 5.9 8.85` |

**裁决：8.7 kWh。** 与第 1 条同源同页，理由相同。

生产 feed 现状（2026-11-04 读取）：`3611 usable_kwh = 5.8`、`3612 usable_kwh = 8.7`，
`module_energy_kwh_usable` 均引用 `GW_ESA-5-30kW_Datasheet-EN.pdf p.3`。**现状与裁决一致，无需改动。**

## 3. SAJ BU3-5.0-TV2-PRO · 可用能量

| 来源 | 值 | 原文 / 位置 |
| --- | --- | --- |
| SAJ HS3 3–12K-T2 User Manual（EN V4） | 4.8 kWh | PDF p.114 `Usable Energy [kWh] 4.8` |
| 同一文档 | 4.5 kWh | PDF p.121 `Usable Energy [kWh] 4.5` |
| SAJ 官方 datasheet `DLK-SAJ-BU350TV2PRO_datasheet.pdf` | **4.8 kWh** | p.2 `Usable Energy [kWh] 4.8` |

**裁决：4.8 kWh。** 依据：同一份手册内部自相矛盾，而该产品关联的**数据手册**（datasheet p.2）写 4.8，
手册 p.114 的电池包规格表也写 4.8；只有手册 p.121 的 9.3.2 节写 4.5。两处 4.8 对一处 4.5，且数据手册优先。

生产 feed 现状：`2093 module_energy_kwh_usable = 4.8`（引用 `DLK-SAJ-BU350TV2PRO_datasheet.pdf p.2`）。**与裁决一致。**

## 4. GoodWe GW25K / GW29.999K / GW30K-ETA-G20 · 每 MPPT 串数

| 来源 | 值 | 原文 / 位置 |
| --- | --- | --- |
| ESA 5–30 kW datasheet（EN, V2.1） | **1/1/2/2** | p.2 `Number of Strings per MPPT 1/1/1 1/1/1/1 1/1/2/2` |
| ESA 5–30 kW Benutzerhandbuch（DE, V1.4） | 1/1/2/2 | p.337（同表德文版） |
| 该手册外观图 | 4 | PDF p.51–52（示意图标注） |

**裁决：1/1/2/2。** 依据：规格表（datasheet p.2 与手册 p.337 的表格）两票一致；
外观图是安装示意，不是电气规格表，其「4」指 MPPT 路数而非每路串数。

生产 feed 现状：`6516/6517/6518 strings_per_mppt = 1/1/2/2`（引用 `GW_ESA-5-30kW_Datasheet-EN.pdf p.2`）。**与裁决一致。**

## 未裁决项（保持 unresolved，不用本文件绕过）

- `manufacturer_pair` 要求「已发布且无 condition」，而 51/51 已发布 pair 都带 condition。
- AC / 多芯 / >6 mm² 载流表：`cable-references.json` 仍只有 2 根单芯 DC 光伏电缆（见本目录 `cable-blocker.md`）。
- 无条件连续充放电 AC 功率标量：feed `0/106`。
- GoodWe ET 50–100 kW 的「最多 15 台逆变器并联」（EN V1.3 p.11）：这是**整机系统**上限，
  不是「一台控制器带几台」，`compatibility.schema.json` 把 `max_units` 定义为后者，因此不写入，详见
  `tools/migrate/548-battery-parallel-limits.json` 的 `unbound` 段。

## 附：1954 装箱事实所引手册已托管（(d) 的前置条件已满足）

任务 (d) 要求把 GW61.4-BAT-AC-G10 的「每柜 5 根包间线束 + 4 个膨胀螺栓」写成装箱事实，
并先核对 87 页 BAT-C 手册是否已托管到本站。核对结果：

```
GET https://de-linker.com/wp-content/uploads/2026/10/GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf
→ 200
sha256 c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7
```

该 sha 与生产工程 feed 中 `doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a`
的 `blob_sha256` 完全一致，且该文档已绑定产品 1954。
**因此不需要「先托管」步骤**，装箱事实可直接引用它，页码为 PDF p.33（`Expansion Anchors×4`）
与 p.34（`Pack interconnection harness … GW61.4-BAT-AC-G10：×5`）。
