# #251 Genie · 零件清单变成产品 — 验收

实例 g251（快照见 `just status`；本地与线上同页），`just serve g251`。规格：`docs/specs/13-genie.md`
"零件清单 → 产品"（#251）。文案：`docs/acceptance/2026-10-19/251/copy-review.md`。

## 一条链

粘贴清单 / 上传 CSV 或 Excel / 拍手写清单 → 服务 `parts.py` 逐行解析 → #233 的产品词表逐行匹配
（品牌 / 型号 / 系列 / SKU / 分类，EN/DE，大小写与连字符变体）→ 服务写答案与 `parts` 卡
（行状态、第一条待确认行的候选、未确认行全部解决后出现的唯一加入按钮）→ 客户逐条确认 →
浏览器**一次** `store.addAll` 写入 Lösungsentwurf。文件走 #236 的 `attachments` 通道，
文件本身不保存；清单状态不另存，每轮由会话消息与 reading 重建。整轮不经模型（provider=service，
model=none），图片转写仍是 #236 的 deepseek-flash 官方通道。

## 20 行混合清单（EN，DE 同构）

`services/genie/tests/test_parts.py::test_a_mixed_list_matches_row_by_row` 逐行断言；
`tests/e2e/specs/genie-parts.spec.ts` 在本地实例上重复同一清单（EN/DE × 1440/390）。

| 行 | 客户写法 | 数量 | 结果 |
|---|---|---|---|
| 1 | 2x SAJ H2-10K-T3 | 2 | matched · SAJ H2-10K-T3 |
| 2 | 1 x S.A.J. H2-12K-T3 | 1 | matched · SAJ H2-12K-T3 |
| 3 | 3 Stk. GoodWe GW10K-ETA-G20 | 3 | matched · GoodWe GW10K-ETA-G20 |
| 4 | SAJ H2-15K-T3 - 2 | 2 | matched · SAJ H2-15K-T3 |
| 5 | 1× SAJ H2-20K T3 | 1 | matched · SAJ H2-20K-T3 |
| 6 | 4 x GoodWe GW5.1-BAT-D-G21 | 4 | matched · GoodWe GW5.1-BAT-D-G21 |
| 7 | 2 x SAJ B2-10.0-HV1 | 2 | matched · SAJ B2-10.0-HV1 |
| 8 | 1 x EcoFlow EF BD-8-S2 | 1 | matched · EcoFlow OCEAN 2 Battery 8.03 kWh |
| 9 | 2 x EcoFlow EF BD-5-S2 | 2 | matched · EcoFlow OCEAN 2 Battery 5.02 kWh |
| 10 | 10 x GoodWe GM330 | 10 | matched · GoodWe GM330 |
| 11 | 1 x Chint DTSU666 | 1 | matched · Chint DTSU666 |
| 12 | 2 x Pylontech L260-OMNI | 2 | matched · Pylontech OPTIM US L260-OMNI |
| 13 | 1 x GoodWe GW7K-HCA-20 | 1 | matched · GoodWe HCA G2 GW7K-HCA-20 |
| 14 | 3 x SAJ eSolar AIO3 | 3 | matched · SAJ eSolar AIO3 |
| 15 | 1 x SAJ BC2-HV1 | 1 | matched · SAJ BC2-HV1 |
| 16 | 2 x SAJ BU2-5.0-HV1 | 2 | matched · SAJ BU2-5.0-HV1 |
| 17 | 2 x GoodWe HCA | 2 | uncertain · GW11K-HCA-20 / GW22K-HCA-20 / GW7K-HCA-20 |
| 18 | 4 x SAJ H2 | 4 | uncertain · H2-10K / 12K / 15K / 20K / 25K / 30K-T3-DE（6 个候选） |
| 19 | 2 x SMA Sunny Boy 5.0 | 2 | missing（不在我们的范围） |
| 20 | 1 x Fronius Symo 10 | 1 | missing（不在我们的范围） |

确认第 17 行 = GW7K-HCA-20（与第 13 行同一产品，数量相加 1+2=3），第 18 行 = H2-15K-T3
（与第 4 行同一产品，2+4=6）；确认后加入动作只有一条：16 个产品、18 行，合并为 16 个商品条目。

## 真实服务结果（本地实例，live 快照 2026-10-19 00:27）

浏览器 e2e 的同一份清单经代理到服务，轮次日志（`~/de-linker-local/g251/genie/turns.sqlite`）：

| 轮次 | 语言 | 结果 |
|---|---|---|
| 43 | EN | `16 of 20 lines match our products. 2 lines need your confirmation: one at a time. 2 lines are not in our product range.`；行 17 uncertain（3 个候选：GW11K / GW22K / GW7K-HCA-20），行 18 uncertain（6 个 SAJ H2 型号），行 19/20 missing |
| 44 | EN | 确认行 17 = GW7K-HCA-20（与行 13 合并，数量 3）；行 18 仍待确认；`17 of 20` |
| 45 | EN | 确认行 18 = H2-15K-T3（与行 4 合并，数量 6）；`18 of 20`；唯一加入载荷：16 个产品、18 行 |
| 40–42 | DE | 与 43–45 逐行相同（`16/17/18 von 20`，same product IDs/quantities/candidates）；加入载荷逐字节相同 |

加入载荷（EN turn 45 与 DE turn 42 相同）：

```
items: 4107×2, 4108×1, 3556×3, 2063×6, 2064×1, 6521×4, 2067×2,
       3582×1, 3581×2, 2394×10, 2281×1, 2003×2, 3586×3, 3573×3,
       2092×1, 2090×2
products: 16, rows: 18
```

## 旧版 .xls

只收 Excel 的 OOXML `.xlsx`（`text/csv` 与本表这一种 Excel 类型）。旧版二进制 `.xls` 需要新依赖
（如 xlrd）；本票不新增依赖，因此不收，类型文案写 "CSV or .xlsx"。若业主需要 `.xls`，另开票裁定。

## 测试

- 服务：`uv run --locked pytest`，**1027 passed**（`tests/test_parts.py` 33 条、附件清单/失败/截断 9 条、
  理解层 2 条、应用层 2 条；含 CSV/XLSX 伪造引用、实体膨胀、超 60 000 字符、200 行截断、续问判定）；`ruff`、`mypy` 通过。
- 壳：`npm run test:unit`，**215 passed**（`PartsCard.test.tsx` 4 条、`PartsApp.test.tsx` 1 条：
  一次 `store.addAll`；`prepare.test.ts` 的 CSV/Excel 与上限；预览卡清单入口）。
- PHP：`just php-test`（`AttachmentsTest` 新增清单类型、二进制伪装 CSV、CSV 上限）。
- 端到端：`tests/e2e/specs/genie-parts.spec.ts`（EN/DE × 1440/390：粘贴清单、逐条确认、
  一次加入、草稿页读回；CSV、.xlsx、手写清单照片，以及一个不是工作簿的 .xlsx 的失败清单卡）。

## 截图

`LINKER_E2E_SHOTS=<this directory>/shots just e2e g251 genie-parts`（首轮结果见下）。

| 文件 | 状态 |
|---|---|
| `{lang}-1440-0-card.png` | 首页预览卡的"上传清单"入口（390 无卡，按设计走事件） |
| `{lang}-{width}-1-prompt.png` | 打开后的"Choose a file" |
| `{lang}-{width}-2-parts.png` | 视口内的清单卡（滚动到作答处） |
| `{lang}-{width}-2-parts-card-top.png` / `-bottom.png` | 卡的首行与末行（16 matched、2 uncertain、2 missing） |
| `{lang}-{width}-3-parts-one-answered.png` | 第一条不确定行已确认，第二条待答 |
| `{lang}-{width}-3-parts-card-top.png` / `-bottom.png` | 卡的首行与末行（17 matched、1 uncertain） |
| `{lang}-{width}-4-parts-ready.png` | 全部确认，加入按钮出现 |
| `{lang}-{width}-4-parts-card-top.png` / `-bottom.png` | 卡的首行与末行（18 matched、2 missing，一个加入按钮） |
| `{lang}-{width}-5-parts-added.png` | 一次写入后卡内 "In your solution draft." |
| `{lang}-{width}-6-draft.png` | Lösungsentwurf 页显示加入的产品 |
| `{lang}-1440-csv-0-card.png` | CSV 测试的首页入口（1440） |
| `{lang}-{width}-csv-1-prompt.png` | CSV 测试的“Choose a file” |
| `{lang}-{width}-csv-1-csv-parts.png` | CSV 上传读成同一张卡（16 matched、2 missing） |
| `{lang}-{width}-csv-1-xlsx-parts.png` | .xlsx 上传读成同一张卡（16 matched、2 missing） |
| `{lang}-{width}-csv-1-photo-parts.png` | 手写清单照片经 #236 读图：3 matched、2 uncertain、1 missing |
| `{lang}-{width}-csv-1-bad-list.png` | 不是工作簿的 .xlsx：失败清单卡，给出"Choose a file"而不是"Choose another photo" |

## 照片清单

手写清单照片的转写是 #236 的文档通道：photo → deepseek-flash 逐行转写（`kind: "document"`）→
`parts.parse_text`。真实图片夹具 `services/genie/eval/parts/list-handwritten.png`（Bradley Hand 字体，
由同目录 `make_fixtures.py` 生成，无第三方素材）经本地实例的 deepseek-flash 官方通道读成 6 行，
e2e 断言至少 2 matched、至少一个明确型号（`H2-10K-T3` 或 `DTSU666`）被读对、至少 1 uncertain、至少 1 missing
（EN/DE × 1440/390）。转写有轻微波动（一次跑出 4 matched：模型把 `SAJ H2` 读成了具体型号），
所以断言取范围，逐行以每次的卡截图为准。纯转写字符串的单元测试保留
（`test_parts.py::test_a_photographed_list_is_a_list_without_a_list_word`）；PDF 数据表不会被误当清单
（`test_a_datasheet_pdf_is_not_taken_for_a_list`）。
浏览器的清单入口在上传文件且未输入文字时发出 "Here is my parts list."，照片文件名不再决定它是不是清单。
