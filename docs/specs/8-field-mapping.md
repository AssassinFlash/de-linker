# #8 engineering-feed 与旧 linker/v1/materials 的字段映射

验证命令：`python3 tools/migrate/8-engineering.py --wp ~/de-linker-local/t8/wp --verify`（2026-10-10 本地实例 t8，快照 20261010-0033 + #7 + #8 两包已写）：

```
feed products: 106, old materials: 279, bound pairs checked: 99
  1185 ac_output_kw_nominal: '12000*' -> '12000' [decided]
  1959 max_pv_array_power:   '59800' -> '59998' [decided: #7 已按手册改正]
  1959 rated_ac_power:       '29900' -> '29999' [decided: #7 已按手册改正]
3 differences, 0 undecided.
```

## 映射表

| 旧 `linker/v1/materials` | 新 `linker/v1/engineering-feed` | 说明 |
|---|---|---|
| `material_id` | — | 材料标识不迁移；feed 条目以 Woo 商品 ID 为准 |
| `bindings.woo_product_ids` | `id` | 99 个绑定对（96 商品，1959/1960/1961 双材料）由 `8-engineering.json` 的 `verify.bindings` 携带用于逐键对比 |
| `identity.model` | `model` | pa_model term name（106/106 有） |
| `identity.manufacturer` | `brand` | pa_brand term name（106/106 有） |
| `identity.family_id` | `series` | 新属性 pa_series（本票写入，106/106） |
| `identity.kind` | `device_class` | 商品分类（#7 SelectionFacts 的同一读取）；不保留 kind 概念 |
| — | `application` | pa_application（#7） |
| — | `phase` | pa_phase / 图值相位归一（#7） |
| `technical.specifications[k].value/unit` | `figures[k].value/unit` | 键名同名，除 `max_input_current_per_mppt_a`→`mppt_max_current_a`、`max_isc_per_mppt_a`→`mppt_max_isc_a` |
| `technical.specifications[k].citation`（旧公开路由不出） | `figures[k].citation{url,page}` | feed 只带我们托管 URL 的引用；无引用值不进 feed |
| `technical.documents[{title,kind,url}]` | `documents[{title,type,url,lang}]` | kind→type；lang 由标题推导（8-decisions §5） |
| `identity.deliverable_type`、`delivery.*`、`supply.*`、`bindings.component_codes/legacy_tokens` | — | 供货与交付属商务链（#11），不在工程 feed |
| — | `overlay`、`compatibility_version`、`modified_gmt`、`sku`、`generated_at` | 新增：非商品工程元件、兼容合同版本、增量游标 |

## 键集合差异（按 verify 逐键行走的口径）

- 旧路由的 498 个规格键里，feed 只承诺 19 个引擎键 + 引用可达的其余键；不在 feed 的键：无引用的展示键（ip_rating、comms 等，留在 Woo 商品 meta 供展示层读）。
- 站内有、注册表无的引擎键值（站内来源）原样进 feed（引用来自 components-db 或保持无引用不进）。
- `?since=` 增量：`GET …/engineering-feed?since=<时刻>` 只回 `modified_gmt` 晚于该时刻的商品；删除不传播（调用方定期全量，#14 的职责）。
