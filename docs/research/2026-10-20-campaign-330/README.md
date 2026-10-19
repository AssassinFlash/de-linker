# #330 对抗测试矩阵 · 输入边界批 — 执行记录

- 日期：2026-10-19 跑批，2026-10-20 第二轮改判。票 #330（地图 #329）。本目录只动装具与笔记，服务与插件代码不改。
- 环境：本地实例 `c330`（快照 20261019-1409 + 当时的 live 代码，WP 127.0.0.1:9162，Genie 127.0.0.1:9164，文档索引 build 20261018T173840Z）。第二轮不重放已改判的回合：产品修复落地之后的 main 答不出 2026-10-19 存档里的原文。
- 已评分的是那 111 个回合（103 条对话 + 8 条零件清单）。装具现在是 117 例 = 109 条对话 + 8 条零件清单。多出的 6 例（A6、A7、I7 的 EN/DE：SKU 尾号错拼、品类词错拼、证书电压）还没有成绩，不计入下面的 94 / 15 / 2。
- 证据在 `~/de-linker-data/campaign-330/`。仓库里的 `verdicts.jsonl` 是可复现摘要：case、完整请求、meta、blocks、判定、数字复核、指向 `final.jsonl#<case>` 的指针。原始 SSE 不入库。`cases.md` 只做索引，不再用截断的请求列充当原文。
- 每条结论引该次回答的原文。"Genie 答得还行"不是过。门槛按第二轮改判后的记录写，见 `NOTES.md`。

## 装具

- `harness/cases.py` — 117 例。零件清单是 K1–K7（EN）和 K8（DE），共 8 例。编造型号用 `NEX-` 前缀。
- `harness/xlsxgen.py` — 零件清单 .xlsx 探针（空表、重复行、超长行、250 行、zip 炸弹、billion laughs）。
- `harness/run_battery.py` — 按壳的 TurnRequest 直接 POST 服务的 `/turn`，收 SSE。`--workers` 默认 1：三个并发时 K3 的 SSE 带上了 K1 的 `turn_id`。
- `harness/attribution.py` — 用 `(conversation_id, 回合序号)` 连接 turn log。问题或答案对不上、或两条用例落到同一行，进程退出码 1。
- `harness/prod_smoke.py` — `POST /genie/turn` 会经 `Proxy::turn` 新建私密对话。生产主机（`de-linker.com`、`www.de-linker.com`）没有 `--confirm-production` 就拒绝，退出码 2，且不发起连接。每个探针记录 `geturl()` 的最终 URL、跳转链、选定响应头、conversation id、turn id，再用同一 cookie `DELETE` 该对话。这是一次有记录的写入。询盘与联系发送不调用。
- `harness/regrade.py` — 读存档 `final.jsonl`，套用第二轮改判，写出 `verdicts.jsonl` 与 `cases.md`。导入该模块不需要证据文件。
- 本目录是独立 uv 工程（`package = false`，与 `tools/faq` 相同）。`just check` 的 `py-check` 与 `just test` 的 `py-test` 会跑这里的 ruff、mypy、pytest。

复跑本地批次：

```bash
just up c330 && just pull load c330 latest --live-code && just serve c330
cd docs/research/2026-10-20-campaign-330/harness
GENIE_URL=http://127.0.0.1:9164 \
GENIE_TOKEN=$(just wp c330 config get LINKER_GENIE_SERVICE_TOKEN --type=constant) \
uv run --locked python run_battery.py ~/de-linker-data/campaign-330/evidence
```

（`--live-code` 装载后 wp 里没有旧 `_linker_de_content` 页，pull 的德语终检会报一条 LoadError；装载本身已完成。这是装具脚注，不是本批发现。）

生产冒烟会写对话，跑完按 cookie 删除。2026-10-20 这一轮没有再请求 `https://de-linker.com`。要对公开站跑，必须显式确认：

```bash
uv run --locked python prod_smoke.py --site http://127.0.0.1:9162
uv run --locked python prod_smoke.py --site https://de-linker.com --confirm-production
```

改判已存档的 111 例（不重放）：

```bash
uv run --locked python regrade.py
```

## 逐类判定标准（过/缺陷，先写清楚再跑）

- **错拼 A**：真实产品仍被找出（模型层兜住）或一个决定性追问；把错拼型号当真作答（规格/库存）= 缺陷。
- **emoji B**：纯 emoji = 一句得体的引导（问要什么）；emoji 混入正题 = 正题照常答对（命中产品、事实对）。
- **超长 C**：不 4xx/5xx、不超时、回答落在真正的问题上；内容被静默丢弃或编造行 = 缺陷。
- **混语 D**：回答单语（跟随站点 locale，这是现行契约）且事实对；回答内部英德混杂 = 缺陷。locale-only 选语记观察（dossier §1.13：混语无先例，须自行设计）。
- **大小写/连字符/空格 E**：正确产品词的任何书写形态必须确定性命中并出卡（地图门槛"确定性产品词 100%"）；漏一例 = 缺陷。
- **品牌+型号冲突 F**：点破不匹配并给出正确读法（型号的真实品牌 / 所点品牌的系列）；拼出不存在的产品或默默换货 = 缺陷。
- **不存在的型号 G**：明说没有；最好给最近真实替代或追问。给假型号编规格/库存/价格 = 严重缺陷（编造）。
- **多产品同句 H**：点名的 3+ 产品全部被识别（卡覆盖或文字逐一说明）；静默丢 = 缺陷。
- **数量/单位 I**：单位正确解读（逆变器 kW、电池 kWh、阵列 kWp、年耗 kWh/a、相数）；配置器预填参数逐字段对（dossier §1.12 契约）；kWh 存储被灌进 annual_load_kwh = 缺陷。电压以证书为准。
- **矛盾 J**：点破矛盾 + 一个决定性追问（或两种读法都给）；默默只满足一边 = 缺陷。
- **零件清单边界 K**：不崩、不 5xx；空表得体；重复行不重复入草稿；250 行截断要声明；zip 炸弹/实体声明被拒且卡片有说法。
- **parity**：同一问句 EN 与 DE 结构不同，且 DE 实质答对。DE 单独记 parity，不记 pass，也不另开一条产品缺陷。

## 结论

见 `NOTES.md` 与 `cases.md`。已评分 111 例：pass 94，defect 15，parity 2。耗时 p50 8.2 s，nearest-rank p95 22.5 s，最大 28.5 s。
