# 548 · 2026-11-03 生产验收记录

本目录记录 #548 在本日落到生产、并从生产读回的改动。证据以生产响应为准，本地测试只作为前置。

## 1. ETR 50–125 kW 安装事实落库（4 个产品）

**来源文档**：`GW ETR-50-125kW User-Manual-EN V1.0`（215 页），`document_id`
`doc-e135c80bd4befdcd3c7e807944036da9a13c966b4c61ad40e6ff7886cf10b42f`，
`document_revision` `f802c3c76d87d6e4dc6b724b400a1ce6fe9ebcb38a3475f3e4d5dcfaffc2ba63`。
事实与页码见 `manufacturer-evidence.md` 第 9 节。

**写入前备份**（生产主机 `disable_functions` 禁了 `exec`，`wp db export` 静默失败，
必须走 mysqldump 直连，见 `tools/cutover/src/linker_cutover/backup.py:13`）：

```
cd tools/cutover && .venv/bin/python -m linker_cutover.cli snapshot --write
→ ~/de-linker-data/snapshots/db-20261103T070621Z.sql.gz
  8,104,894 B, sha256 71f00f4a2504f1f7…
```

**preview**（作用域收窄到 4 个 ETR，绕开 9 个老产品的 revision 漂移）：

```json
{"action":"preview","site":"https://de-linker.com","changes":4,
 "source_revision":"cd9e9a990e1801afee18354379e7f87831fa1f56fafe78a05411dbd6fe11fdf6"}
```

**apply**（apply 只认 receipt，不接受 `--plan`）：

```json
{"action":"apply","site":"https://de-linker.com","changes":4,
 "source_revision":"113e8ad236d47e61d7b8af920fe6e0610d146b93bb4c4e0d4de477a0b9097534"}
```

**verify**（幂等复跑）：`changes: 0`，`source_revision` 不变。

**生产读回**：`GET https://de-linker.com/wp-json/linker/v1/engineering-feed`

| id | 新 product_revision | `installation_facts.status` | 条数 |
|---|---|---|---|
| 6508 | `6d219f809af9…` | documented | 3 |
| 6509 | `3b7f8c0e00af…` | documented | 3 |
| 6510 | `5a0d03c3019d…` | documented | 3 |
| 6511 | `e06d299cdcdd…` | documented | 3 |

6508 的事实形状（其余三个同构）：

| id | basis | 页 |
|---|---|---|
| `ac-conductor` | `manufacturer_recommended_ac_conductor` | 61 |
| `protective-earth-conductor` | `manufacturer_recommended_pe_conductor` | 60 |
| `battery-cluster-conductor` | `manufacturer_model_specific_conductor` | 60 |

三个 `basis` 与 item id 正好命中引擎契约
（`services/engine/src/linker_engine/planning/installation_conductor_comparison.py:100-108`），
`conditions: []` 满足 `_source_is_current` 之外的条件项。

**影响面**：4 个产品 revision 已变，计划/报价按新 revision 取数。

**回滚**：同一 receipt `rollback`；整库可用上面的快照 `restore-snapshot`。

## 2. 未完成项（本日不宣称完成）

- 引擎对外层仍保留刻意 unresolved 的工程边界项（scenario 参数基准、模型域、DSO/TAB 签核等，
  见 #548 与 `manufacturer-evidence.md` 第 5、6 节），这些**不因本条写入而变绿**。
- 剩余 9 个已漂移产品的计划需要重新 binding，不在本条范围。
