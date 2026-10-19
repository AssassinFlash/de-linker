# #330 输入边界批 — 结果与缺陷清单

- 日期：2026-10-19 跑批，2026-10-20 第二轮改判。票 #330（地图 #329）。装具与笔记有改动，服务与插件零改动。
- 本地：实例 `c330`（快照 20261019-1409 + 当时的 live 代码；WP 127.0.0.1:9162，Genie 127.0.0.1:9164；文档索引 build 20261018T173840Z）。
- 已评分 111 个回合。装具现为 117 例（109 对话 + 8 零件）。A6、A7、I7 的 EN/DE 共 6 例未开跑，不计入本节数字。
- 证据（机器本地）：`~/de-linker-data/campaign-330/`
  - `evidence/final.jsonl` — 原始终稿（含 SSE）
  - `evidence/attribution.jsonl` — 第一轮按 `turn_id` 的 join
  - `evidence/grades.json` — 第一轮手判
- 仓库摘要：`verdicts.jsonl`（无原始 SSE；含完整请求、meta、blocks、判定、数字复核、指针 `final.jsonl#<case>`）。`cases.md` 是索引。
- 第二轮读的是 2026-10-19 的存档，没有对当前 main 重放。

## 1. 结果总览（111 例）

| 类 | EN | DE | pass | defect | parity |
|---|---|---|---|---|---|
| 错拼/模糊拼写 | 5 | 5 | 8 | 2 | 0 |
| emoji | 5 | 5 | 10 | 0 | 0 |
| 超长输入 | 5 | 5 | 8 | 2 | 0 |
| 混合语言 | 5 | 5 | 10 | 0 | 0 |
| 大小写/连字符/空格 | 6 | 5 | 11 | 0 | 0 |
| 品牌+型号冲突 | 5 | 5 | 6 | 3 | 1 |
| 不存在的型号 | 5 | 5 | 6 | 4 | 0 |
| 多产品同句 | 5 | 5 | 9 | 1 | 0 |
| 数量/单位 | 6 | 6 | 10 | 2 | 0 |
| 矛盾条件 | 5 | 5 | 8 | 1 | 1 |
| 零件清单边界 | 7 | 1 | 8 | 0 | 0 |
| **合计** | **59** | **52** | **94** | **15** | **2** |

15 个缺陷回合归成 D1–D12（D1 三个回合，D11 两个回合）。parity 两例（F1-DE、J5-DE）不计入 pass。94 + 15 + 2 = 111。

耗时不变：p50 8.2 s，最大 28.5 s。p95 用 nearest-rank：`ceil(0.95 × 111) − 1` = 下标 105，**22.5 s**。同一规则在 `services/genie/ops/turn_latency.py` 的 `_percentile`。第一轮写的 20.0 s 是 `int(n × 0.95) − 1`（下标 104）。p95 ≤ 30 s 仍达标，目标 ≤ 15 s 仍未达（dossier §1.14）。

直接打服务的客户端超时仍是 180 s。来源：`services/genie/eval/baseline/run.py` 记录原试验脚本用 180，该评测客户端后来改成 240。壳在 60 s 停下：`plugins/linker-tools/includes/Genie/Proxy.php` 的 `post()` `'timeout' => 60.0`，与 `prices.SHELL_TIMEOUT` 相同。180 不延长这 60 s。本批最慢 28.5 s，没有顶到客户端上限。

## 2. 缺陷清单

每条的最小复现和回合原文在 `verdicts.jsonl` 按 case id 检索。

### D1 · 零结果后直接转团队（3 个回合，两条不同的路径）

F1-EN 与 G1 不是同一种确定性失败。

- **F1-EN** `Is the SAJ GW10K-ETA-G20 in stock?`：`route=products`。`search-products {text: GW10K-ETA-G20, brand: saj}` → `qualified: []`。随后 `handoff-team`，grounding 拒绝（"a products turn is not a question for the team"），fallback 句 `Our team will answer that at sales@de-linker.com.`
- **G1-EN / G1-DE** `GW50K-ETA-G20`：`route=model`，`matches` 为空，没有 search 调用，只有 handoff。该假型号不在词表里。G1-DE 的 jev unsure 0.70。这是空词表上的模型 handoff，不是品牌与型号的 AND。
- **期望**：F1 先点破"这是 GoodWe 的型号"（F1-DE 做了，见 parity）。G1 明说没有并给最近型号（G2/G3 做了）。
- **复刻/须自行设计**：F1 这条 AND 搜索零结果后的澄清，确定性优先=复刻（dossier §1.1），澄清话术须自行设计（§1.1 末段、§1.11）。G1 沿用同一句"没有澄清就 handoff"的缺口，机制按日志分开写。

### D2 · 多产品同句只搜第一个型号

- **最小复现**：`Do you have HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX and HS3-12K-T2-W/G-PX in stock?` → "These two model codes return no entry in our product data"。两件在售。
- **工具证据**：EN 只发 1 次 `search-products {text: HS3-5K-T2-W/G-PX}`（`route._search_input` 只取 `models[0]`）。H4-DE 由模型搜了三次，三件都命中。
- **复刻/须自行设计**：多查属复刻（千问 CN §2.1；dossier §1.1）。多型号聚合须自行设计（§1.11）。

### D3 · DE 配置器预填被模型写入客户没说的相数

- **最小复现**：`Meine PV-Anlage hat 12 kWp und ich möchte 15 kWh Batteriespeicher.` → URL `?pv_kwp=12&phase=1`。
- **工具证据**：Jev sizing 0.77 < 0.8，路由落 `model`，模型调用 `size-hint {pv_kwp: 12, phase: 1}`。EN 同题由代码直调，URL 是 `?pv_kwp=12`。
- 第一轮分诊把 I3/I5 标成 `prefill pv_kwp=None`，因为当时读的是 `args["pv_kwp"]`，动作参数实际是 `{url: "...?pv_kwp=&annual_kwh=&phase="}`。`annual_kwh` 对应预填字段 `annual_load_kwh`。那条旗标作废。I5-DE 的 `phase=1` 仍是缺陷：客户没说单相。I3-EN 的 URL `?pv_kwp=8&annual_kwh=4000&phase=3` 与问句一致，维持 pass。
- **复刻/须自行设计**：预填契约的正确性须自行设计（dossier §1.12）。

### D4 · 知识检索重试停在 1，兜底仍出无关卡（校准）

- **最小复现**：`Do you carry the EcoFlow OCEAN 3 HD-P3-20K0-S2?` → failures 为 pydantic-ai `Tool 'linker_search_knowledge' exceeded max retries count of 1`。回答 "Here are matching products from our range." + 卡 3608（OCEAN 2 Battery Base），没有 DEGRADED 句。
- **裁定：校准。** #103 已落地（`docs/specs/13-genie.md` 2026-10-12）：ability 的 5xx/连接异常退避重试 3 次；无可引用事实时 `template.py` 的 DEGRADED 声明失败并给出重试与团队出路。单测在 `tests/test_abilities.py`、`tests/test_cycle.py`。G5-EN 卡在工具自身的 retry=1，products 路由的兜底又从 `facts.product_ids` 打出卡，跳过了已有的 DEGRADED 句。重试与降级形态不是从零设计。

### D5 · 品牌冲突在 DE 没点破

- **最小复现**：`EcoFlow GW5K-ETA-G20 - lieferbar?` → "Zu EcoFlow GW5K-ETA-G20 finde ich in unserem Sortiment kein Produkt"。该型号是 GoodWe 在售产品。F4-EN 给了 GoodWe 卡并说明品牌。
- **复刻/须自行设计**：消歧须自行设计（dossier §1.11）。

### D6 · "最小 ≥30 kW" 选了商业线（EN）

- **最小复现**：`What is your smallest inverter with at least 30 kW?` → **GW75K-ET-G10**（75 kW，卡 6506）。家用 GW30K-ETA-G20（6518，30 kW）在目录里。
- **工具证据**：第二次调用是 `search-products {device_class: inverters, application: commercial, limit: 12}`。`application=commercial` 是模型传入的参数，这一过滤拿掉家用 GW30K-ETA-G20。J5-DE 用文本搜 "30 kW" / "30K"，没有这个过滤，答对了 6518。
- 第一轮写成"默认排序"。日志不是默认排序。
- **复刻/须自行设计**：极值/聚合仍须自行设计（dossier §1.1 末段）。

### D7 · 3 字符型号码不入词表（"BD-8"）

- **最小复现**：`Looking for Ecoflow Ocean two batteries, the BD-8 one.` → Battery Base 卡，说找不到电池。在售 **EF BD-8-S2**（id 3582）。
- **证据**：`lexicon.MIN_CODE = 4`。词表只有 "OCEAN 2" 与 "Battery Base"。
- **复刻/须自行设计**：短码匹配须自行设计（dossier §1.1 末段；§2 排名第 7）。

### D8 · F3-DE 否认在售的 SAJ H2-15K-T3

- **最小复现**：`Ist der GoodWe H2-15K-T3 von euch?` → "Den GoodWe H2-15K-T3 führen wir nicht"，随后 GoodWe ESA 卡（6512 等）。SAJ H2-15K-T3 是 id 2063。F3-EN 答对了这个 id。这张卡没有出现。

### D9 · G4-DE 否认 CHS2 系列

- **最小复现**：DE 回答说该编号没有，"unter der Serie CHS2" 也没有，然后给出无关 SAJ 卡（数据记录器、EMS、ATS、家用电池）。G4-EN 拒绝编造型号，并给出真实 CHS2 卡 1959、1960、1961。
- 提问原文在 `verdicts.jsonl` 的 G4 行。现行夹具改用 `NEX-` 前缀，不再把商店前缀用在编造型号上。

### D10 · I1-DE 没有把 kWh 改读成逆变器的 kW

- **最小复现**：`Ich brauche einen 10-kWh-Wechselrichter.` → 兜底句 "Hier sind passende Produkte"，没有单位纠正。I1-EN 写了逆变器按 AC 输出选型、客户说的是储能容量。
- grounding 拦住了模型正文里的数字 "2"（`model text contains numbers ['2']`），于是走了兜底。拦住一个数字，不等于做了单位纠正，也不能当作"0 编造数字"的证据。

### D11 · C1 的超长列表没有回答后面的问题（EN 与 DE）

- **最小复现**：列表以 "Which of these are single-phase inverters?" / "Welche davon sind einphasige Wechselrichter?" 结束。回合走了 parts（200 行，截断），正文是匹配计数。问题没有回答。
- 第一轮把缺引导句记成观察并判 pass。类标准是回答要落在真正问的那句话上。C5 的列表以无效行结束，仍是 pass（引导句被当成 missing 行，观察保留）。

### D12 · A4-EN 把电流行号读成电压

- **最小复现**：`what is the output of the GooodWe GW5K-ETA-G2O?` 找到了 GW5K-ETA-G20（卡 6512），然后写证书额定输出电压是 "10 / 30 V and 11 / 30 V, 3L/N/PE"。
- **证书**：本地 `GW_ESA-5-30kW_Certificate_IEC-62109.pdf` 第 2 页，`pdftotext -f 2 -l 2 -layout` 读到 `Rated Output Volt. [Va.c.] : 3L/N/PE, 220/380, 230/400`。Backup 行相同。第 10、11 行是电流 `10)45.5@380V` / `11)45.5@380V`，以及功率行里的 29.999 / 30。`verdicts.jsonl` 的 A4-EN 记了这次重读（`pdf_reread: true`）。
- 分诊只旗标了 "11"：10 和 30 被 10 kW 与文档标题 "ESA 5–30 kW" 解释掉了。手判"全部可追溯"不成立。拼写被纠正到正确型号，电压句是缺陷。

## 3. parity（不记 pass）

- **F1**：DE 说明 GW10K-ETA-G20 属于 GoodWe，卡 3556 与 1182。EN 是 D1 的 handoff。同一问句，结构不同。
- **J5**：DE 答 GW30K-ETA-G20（6518）。EN 在 `application=commercial` 之后答 GW75K-ET-G10，即 D6。

locale 跟随站点语言仍是观察，不是缺陷（D3-EN 德语问、英语答；D3-DE 反过来）。

## 4. 数字复核

"0 编造数字"撤回。18 条带 `numbers to verify` 的回答各有一条记录，在 `verdicts.jsonl` 的 `numbers_verification`。A4-EN 是编造。其余不把"待核→已核：全部可追溯"当作复核。

| case | 旗标 | 状态 | 记录 |
|---|---|---|---|
| A4-EN | 11 | 编造 | 证书 220/380、230/400。回答写成 10/30 V、11/30 V |
| A2-DE | 10, 12, 9.999 | 引用文档 | 手册型号表里的 GW10K / GW9.999K / GW12K。PDF 本轮未重读 |
| A4-DE | 100, 4.5, 4.8, 5 | 快照 + 引用 | id 2093：nominal 5 kWh，usable 4.8。100 Ah 与另一处 4.5 在回答引用的手册句里。手册 PDF 未重读 |
| B4-DE | 10000, 11000, 16500, 60 | 引用文档 | HS2-10K 数据表的 W/VA/60 s。id 1182 的 figures 为空。PDF 未重读 |
| C3-EN | 0.8 … 50 | 引用文档 | H2-10K 数据表/手册句（功率、电流、电压窗、海拔、温度、尺寸）。id 4107 figures 为空。PDF 未重读 |
| D1-EN | 96.4, 98.0, 98.00 | 引用文档 | GW5K-ETA-G20 效率三句。id 6512 figures 为空。PDF 未重读 |
| D4-DE | 108 | 快照 | ESA `kwh_range` max 108（id 3556 等）。回答写 5–108 kWh |
| D5-DE | 97.6, 98.0 | 引用文档 | HS2 数据表效率。PDF 未重读 |
| E2-DE | 10000, 11000 | 引用文档 | H2 手册/数据表的 W 与 VA。PDF 未重读 |
| E3-EN | 10000, 11000, 14.5, 16.0 | 引用文档 | H2-10K 数据表电流与功率。PDF 未重读 |
| E5-EN | 108 及模块数 | 快照 + 引用 | 108 是 id 6519 的 `kwh_range` max。其余电流/电压/温度在回答引用的数据表 p.3、手册 pp.334–335。PDF 未重读 |
| H1-EN / H1-DE / I2-EN | 108 | 快照 | 同上，ESA `kwh_range` max 108 |
| I6-EN | 29900, 29999 | 引用文档 | 手册 29900 VA、数据表 29999 VA。快照 id 1959 的 `ac_power_kw` 是 29.999，分诊没旗标它。PDF 未重读 |
| I6-DE | 29.999, 29900, 29999 | 快照 + 引用 | 29.999 对齐 id 1959。29900/29999 在引用的手册、数据表、证书句里。PDF 未重读。该回合另外没出卡 1959 |
| J5-DE | 2, 29.999 | 快照 | 29.999 是回答点名的 H2-30K-T3-DE（id 1181）的 `ac_power_kw`。旗标里的 2 来自型号 H2。出卡的是 6518 |
| K5-EN | 199 | 零件计数 | parts 块的 "199 match" 句子 |

## 5. 其余观察

- E6-EN 只列单相 EHA，没提 ETA。不假，不完整。
- K2 空表被说成 could not read。表是读到了，没有数据行。
- H5-EN/H5-DE：第 5 个型号因工具预算没出卡，回答写明了。按本批标准算过。
- 回答语言跟站点 locale。现行契约，见 §3。

## 6. 仍成立的阳性结果

1. **E 类确定性产品词 11/11**（小写、连写、空格、逗号小数、DE 问句都出卡）。A 类 8 pass / 2 defect：A3-EN 是 D7，A4-EN 找到了 GW5K-ETA-G20，电压句是 D12。第一轮"A4 GooodWe/G2O 都答对"不成立。
2. **数字**：见 §4。编造有一条记录（A4-EN）。其余 17 条旗标按快照字段或回答里的文档句归档，没有再用一句"全部可追溯"盖过去。
3. **型号消歧**：ESA EHA/ETA 单三相（B5、J3、J4、I4）、OCEAN 2 单三相（B5-DE）在存档里是对的。J4-EN 写明三相 GW5K-EHA-G20 不存在。F1 的 EN/DE 分裂见 parity，不放进这条。
4. **假型号**：G2、G3、G5-DE、G4-EN 明说没有。G4-DE 是否认整个 CHS2 系列（D9）。G1 是 D1，G5-EN 是 D4。
5. **零件清单 8/8**：空表、重复行、超长行、250 行截断（`truncated: true`）、zip 炸弹、billion laughs。zip 与实体声明被 8 MiB 上限和 DOCTYPE 拒绝拦住。
6. **超长输入的传输**：10 例都没有 4xx/5xx、没有超时。C1 两例的内容缺陷是 D11（没回答列表后面的问题），传输本身没有失败。
7. **单位**：I2-EN 把 "10 kW of storage" 改读为 kWh。I1-DE 没有做对应纠正（D10）。I3 的预填 URL 与问句一致。

## 7. 生产冒烟是写入

2026-10-19 的 10 次 `POST /wp-json/linker-ai/v1/genie/turn` 经 `Proxy::turn` 建了私密对话 **7444–7453**，turn 行 **90–99**。当时的客户端没存 cookie（`linker_conversation` / `linker_genie_browser`），删不掉那 10 条。本轮不删生产数据，也没有再请求 `https://de-linker.com`。

`prod_smoke.py` 现在的行为：

- 生产主机没有 `--confirm-production` 就退出 2，不连接。
- 每个探针用新的 cookie jar。记录 conversation id、turn id、`geturl()` 的最终 URL、跳转链（`status` / `from` / `location`）、选定响应头（有则记：Date、Server、X-Powered-By、Content-Type、X-Robots-Tag、Link、Location）。
- 用同一 cookie `DELETE /genie/conversations/{id}`。`delete_http` 不是 200 则进程退出 1。
- 307/308 保持 POST 与正文。urllib 默认拒绝这种跳转。301/302/303 仍按 urllib 转成 GET。
- 不调用询盘、联系或 `/email`。
- 客户端等待 180 s，不延长壳的 60 s。

第一轮 `smoke.jsonl` 里的终点 URL 是 `SITE + ROUTE` 拼出来的。`http.client` 不跟随跳转。那 10 条 HTTP 200 的对照表仍在旧文件里，不再写成"只读"，也不再把拼出来的 URL 叫做观察到的最终 URL。

## 8. 归因连接

第一轮 attribution 只按 SSE `turn_id` 连接，`--workers` 默认 3。K1-EN 与 K3-EN 的流都写了 `turn_id` 117，问句都是 "Here is my parts list."。日志里 117 是 `c330-K1-EN-1792402592`，116 是 `c330-K3-EN-1792402592`。K3 的回答文本对得上 116。SSE 自己的 turn id 竞态留在产品侧，本轮不改。

装具现在把 `conversation_id` 写进每条结果，按 `(conversation_id, 序号)` 连接。没有 conversation id 的旧档，若答案文本只对上唯一一行，就改接过去并仍记 mismatch。两条用例落到同一 turn id 也记 mismatch。有 mismatch 则退出码 1。`--workers` 默认 1。

## 9. 复跑

见 `README.md`。`just check` 含本目录的 ruff / mypy，`just test` 含 pytest。改判：`uv run --locked python regrade.py`。
