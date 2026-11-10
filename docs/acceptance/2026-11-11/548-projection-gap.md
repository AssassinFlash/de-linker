# #548 · 工程数据投影缺口（2026-11-11）

引擎的 design 在本地实例一直 `no_candidate`。本文件记录实际的原因链、修复面与端到端结果。
生产 feed 与本分支的 PHP 改动无关：**本 PR 不含任何生产数据写入**。

## 1. 结论先行

生产 feed 的 11 台目标逆变器**本来就有**引擎需要的 6 个 layout 字段：

```
GET https://de-linker.com/wp-json/linker/v1/engineering-feed  (2026-11-10T22:18:58Z, 85 products)
mppt_max_current_a 45 · n_mppt 45 · mppt_voltage_range_v 45 · max_pv_input_v 39 · strings_per_mppt 30
```

所以缺口不在"字段没写"，也不在"引擎键名错配"——`mppt_max_current_a` / `mppt_max_isc_a`
是 `docs/specs/8-field-mapping.md` 明写的注册表名改称，生产 feed 两种键都带且值相同：

| 键 | 产品数 | 例子（GW10K-ETA-G20） |
| --- | --- | --- |
| `max_input_current_per_mppt_a` | 11 | `21/21/21/21` |
| `mppt_max_current_a` | 45 | `21/21/21/21` |

只有 11 台同时有注册表原名；若把引擎读者改到注册表名，另外 34 台会退回 `no_candidate`。
**因此引擎读者保持 `mppt_max_current_a` / `mppt_max_isc_a` 不变。**

真实原因是本地副本的**绑定记账**：`Publication::revision()` 把条目连同 citation URL 一起哈希，
`tools/pull` 的 `search-replace` 把 `de-linker.com` 改写成 `127.0.0.1:<port>`，于是每条
figure 与每条厂商声明的 revision 都变了，而记录的绑定/确认仍是线上值。两个消费者都按
"记录版本必须等于当前版本"放行，结果：

- `Publication\EvidenceBindings` 丢弃这些条目 → feed 的 figures 大面积缺席（本地 405 条 vs 生产 981 条）；
- `Publication\CompatibilityClaims::projection()` 丢弃这些声明 → `compatibility` 投影 pairs 0 / requirements 0
  （生产 368 / 38），所有逆变器 `battery_release = 0`，design 必然 `no_candidate`。

之所以一直没被发现：`bind-figures` 是**增量**绑定（`adopt_existing = true` 会保留已有条目），
它按设计不会刷新已记录的值，而 `tools/pull` 在地址改写后只调用它。

## 2. 修复面

| 文件 | 改动 |
| --- | --- |
| `plugins/linker-commerce/includes/Products/Publication/EvidenceBindings.php` | 新增 `repair_unchanged( $id, $dry_run )`：仅当记录的 `document_id` 与 `blob_sha256` 都等于当前值时，把 `figure_revision` 更新为当前值。换文档、换字节、无法解析的引用一律不动。 |
| `plugins/linker-commerce/includes/Products/Publication/CompatibilityClaims.php` | 新增 `renew_unchanged( $owner, $manifest, $dry_run )`：同上判定，且重算后必须真的通过 `bind_row(..., bind: false)` 才写；声明其余部分未解析时不写。 |
| `plugins/linker-commerce/includes/Cli/PublicationCommand.php` | 新子命令 `repair-bindings [--dry-run]`，一次处理两类并分别输出计数。 |
| `tools/pull/src/linker_pull/load.py` | `_bind_publication()` 在 `bind-figures` 之后接 `repair-bindings`：地址改写造成的过时版本由加载步骤自己收敛。 |

两条路径都不会把旧值搭上新 PDF：只有 identity + 字节都对上才续期，因此
`614-publication-contract.md` 的"换字节不得重新绑定"规则保持有效。

## 3. 逐型号核实（只认托管数据手册）

11 台目标机本来就有的两个电流键，引用的是我们托管的原厂数据手册。本次逐页核对的字段与页码：

| 型号 | n_mppt | strings_per_mppt | mppt_voltage_range_v | max_pv_input_v | 手册 / 页 |
| --- | --- | --- | --- | --- | --- |
| HS2-5K/6K/8K/10K-T2-X | 2 | **手册未印**（见下） | 180～900 | 1000 | `saj_hs2_5_10k_t2_x_datasheet_en.pdf` p.2 |
| GW80K/99.99K/100K-ET-G10 | 8 | 2 | 160 ~ 950 | 1000 | `GW_ET-75-100kW_Datasheet-EN-20260708-V2.1.pdf` p.2 |
| GW8K-ETA-G20 | 3 | 1/1/1 | 120 ~ 950 | 1000 | `GW_ESA-5-30kW_Datasheet-EN.pdf` p.2 |
| GW10K/12K/15K-ETA-G20 | 4 | 1/1/1/1 | 120 ~ 950 | 1000 | 同上 p.2 |

原文（GoodWe ET p.2）：`Max. Input Voltage (V) 1000`、`MPPT Operating Voltage Range (V) 160 ~ 950`、
`Max. MPPT Current (A) 42 × 8`、`Max. MPPT Short Circuit Current (A) 55 × 8`、
`Number of MPPTs 8`、`Number of Strings per MPPT 2`。

原文（GoodWe ESA p.2）：`Max. Input Voltage (V) 1000`、`MPPT Operating Voltage Range (V) 120 ~ 950`、
`Number of MPPTs 3 / 4`、`Number of Strings per MPPT 1/1/1 / 1/1/1/1 / 1/1/2/2`。

原文（SAJ HS2 p.2）：`Max. DC Voltage [V] 1000`、`MPPT Voltage Range [V] 180～900`、
`Max. DC Input Current [A] 16/16`、`Max. DC Short Circuit Current [A] 19.2/19.2`、`No. of MPPT 2`。

### SAJ 的 `strings_per_mppt`：无法核实，且不需要

SAJ HS2 数据手册没有 "strings per MPPT" 这一行；`SAJ_HS2-AS2_5-10K-T2_User-Manual_DE_V0.3.pdf`
（46 页，5.7 PV 接线章）与本仓库托管的 `H2_HS2_HS3_AS2_AS3_Configuration_Instructions_V1.0_en.pdf`
（91 页）都只讲接线，不给每 MPPT 串数上限。**因此不写该键，不用猜测值填充。**

引擎不需要它：`services/engine/src/linker_engine/strings.py:108` 在缺该键时按 `[1] * n_mppt`
起步，每路容量再由 `max_input_current_per_mppt_a` / `max_isc_per_mppt_a` 与模块
`impp` / `isc` 收紧（16 A / 19.2 A 对 Trina 460 的 10.9 A / 11.5 A ⇒ 每路 1 串）。
实测 4 台 SAJ 都产出正确 layout（见第 4 节）。

## 4. 端到端验证（review 实例，非生产）

实例：`http://127.0.0.1:8889`（WP）+ `http://127.0.0.1:8890`（engine），真实 Published feed。

### 4.1 修复前后对照

| 指标 | 修复前 | 修复后 | 生产 |
| --- | --- | --- | --- |
| feed figures 总数 | 405 | 982 | 981 |
| `mppt_max_current_a` / `n_mppt` | 0 / 0 | 45 / 45 | 45 / 45 |
| `mppt_voltage_range_v` | 0 | 45 | 45 |
| `max_pv_input_v` | 0 | 39 | 39 |
| `strings_per_mppt` | 0 | 30 | 30 |
| compatibility pairs / requirements | 0 / 0 | 377 / 38 | 368 / 38 |

`repair-bindings` 在实例上续绑 568 条 figure 绑定与 415 条声明；**换字节与无法解析的条目 0 条被采纳**
（实例上不存在该类条目，函数本身对它们计数为 0）。

### 4.2 design（10 kWp、3 相、10115、4500 kWh/a）

```json
{"status": "solution",
 "selected": {"inverter": {"id": 3556, "model": "GW10K-ETA-G20"},
              "battery": {"product": {"id": 3611, "model": "GW6.0-BAT-D-G20"}, "usable_kwh": 5.8},
              "strings": {"module_count": 22, "array_kwp": 10.12,
                          "groups": [{"mppt":1,"strings":1,"modules_per_string":11},
                                     {"mppt":2,"strings":1,"modules_per_string":11},
                                     {"mppt":3,"strings":0},{"mppt":4,"strings":0}]}}}
```

Stückliste（`selected.lines`，原文节选）：

```
inverter    DLK-GOODWE-GW10KETAG20  GW10K-ETA-G20    1 pcs  Hybrid inverter
battery     DLK-GOODWE-GW60BATDG20  GW6.0-BAT-D-G20  1 pcs  Battery modules
pv_module   —                       (Trina TSM-460NEG9R.28)  22 pcs
mounting    —                       1 set
dc_cable    —                       60 m   2 strings × 2 poles × 15 m
connector   —                       4 pairs
ac_protection —                     1 set
```

### 4.3 11 台目标机全部可选中

强制 `inverter_id`（residential 端点，photovoltaic 屋顶按机型额定功率）：

| id | 型号 | kWp | status | 模块 | 组串（每路） |
| --- | --- | --- | --- | --- | --- |
| 1182 | HS2-10K-T2-X | 10 | solution | 22 | 1/1 |
| 1183 | HS2-6K-T2-X | 6 | solution | 13 | 1/0 |
| 1184 | HS2-8K-T2-X | 8 | solution | 17 | 1/0 |
| 4109 | HS2-5K-T2-X | 5 | solution | 11 | 1/0 |
| 3556 | GW10K-ETA-G20 | 10 | solution | 22 | 1/1/0/0 |
| 3583 | GW8K-ETA-G20 | 8 | solution | 17 | 1/0/0 |
| 3584 | GW12K-ETA-G20 | 12 | solution | 26 | 1/1/0/0 |
| 3585 | GW15K-ETA-G20 | 15 | solution | 33 | 1/1/1/0 |

ET 三型（1946/1947/1948）属于 commercial 产品类，residential 端点按 `application`
规则拒绝是正确行为；引擎库直接调用 `strings.layout` 在 20/40/60/80/100 kWp 下均出 layout：

```
1946 GW80K-ET-G10  n_mppt=8 spm=[2 × 8] win=(160,950) vmax=1000 I=[42 × 8] Isc=[55 × 8]
   20 kWp -> 42 modules 19.32 kWp 3 strings fuses=0
   60 kWp -> 130 modules 59.8 kWp 10 strings fuses=0
  100 kWp -> 221 modules 101.66 kWp 13 strings fuses=0
```

## 5. 测试

| 检查 | 结果 |
| --- | --- |
| `plugins/linker-commerce` PHPUnit | **2270 tests / 8763 assertions / 531 skipped，全绿** |
| 新增 `RepairBindingsTest` | 6 用例（含"字节被替换绝不采纳"、"未知引用保持未绑定"、"dry-run 不写"） |
| 新增 `CompatibilityTest` 两用例 | 续期只对同字节生效；换字节保持撤回 |
| `plugins/linker-commerce` PHPStan level 8 | No errors |
| `plugins/linker-commerce` PHPCS | 0 errors |
| `services/engine` pytest 全量 | 见下方提交说明（本分支未改引擎源码） |
| `tools/pull` pytest（除需本机 MySQL 的 `test_load.py`） | **134 passed** |
| `tools/pull` ruff / `mypy --strict` | 通过 |

## 6. 未做 / 不在本票

- **没有改引擎读者键名**：见第 1 节，改会打断另外 34 台。
- **没有给 SAJ 写 `strings_per_mppt`**：手册没有该值，引擎也不需要（第 3 节）。
- **没有写生产**：本 PR 只提交代码与测试。
- **commercial 端点仍返回 `status=indicative`（`systems` 为空）**：这是该端点既有行为，
  与 #548 的 layout 投影无关，未在本票改动。
