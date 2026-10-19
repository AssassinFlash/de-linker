# #330 对抗测试矩阵 · 输入边界批 — 执行记录

- 日期：2026-10-19/20。票 #330（地图 #329）。只测试、不修复：本目录只有
  测试装具与逐例笔记，服务与插件代码零改动。
- 环境：本地实例 `c330`（快照 20261019-1409 + live 代码，WP 127.0.0.1:9162，
  Genie 服务 127.0.0.1:9164，本工作树 `services/genie`，文档索引 build
  20261018T173840Z）。生产仅做冒烟（≤10 例，见 NOTES.md §冒烟）。
- 证据：`~/de-linker-data/campaign-330/`（feed.json 快照、evidence/cases.jsonl
  逐例原文）。判定规则：每条结论都引 cases.jsonl 里该次回答的原文；
  "Genie 答得还行"不是过，地图门槛才是（确定性产品词 100%、0 编造数字、
  每条回答有下一步、EN/DE 同结构、无静默降级）。

## 装具

- `harness/cases.py` — 117 例（10 类 × EN/DE 各 5–6 例 + 零件清单边界 9 例），
  每例锚定真实目录事实（快照 feed 的 product id）。
- `harness/xlsxgen.py` — 零件清单 .xlsx 探针（空表、重复行、超长行、250 行、
  zip 炸弹、billion laughs；.xlsx DoS 修复的回归）。
- `harness/run_battery.py` — 跑批：按壳的 TurnRequest 契约直接 POST /turn，
  收 SSE，机器分诊（TRIAGE_PASS / TRIAGE_REVIEW / TRIAGE_ERROR）+ 人工终判。

复跑：

```bash
just up c330 && just pull load c330 latest --live-code && just serve c330
cd docs/research/2026-10-20-campaign-330/harness
GENIE_URL=http://127.0.0.1:9164 \
GENIE_TOKEN=$(just wp c330 config get LINKER_GENIE_SERVICE_TOKEN --type=constant) \
python3 run_battery.py ~/de-linker-data/campaign-330/evidence
```

（`--live-code` 装载后 wp 里没有旧 `_linker_de_content` 页，pull 的德语终检会
报一条 LoadError；装载本身已完成——这是装具脚注，不是本批发现。）

## 逐类判定标准（过/缺陷，先写清楚再跑）

- **错拼 A**：真实产品仍被找出（模型层兜住）或一个决定性追问；把错拼型号
  当真作答（规格/库存）= 缺陷。
- **emoji B**：纯 emoji = 一句得体的引导（问要什么）；emoji 混入正题 =
  正题照常答对（命中产品、事实对）。
- **超长 C**：不 4xx/5xx、不超时、回答落在真正的问题上；内容被静默丢弃或
  编造行 = 缺陷。
- **混语 D**：回答单语（跟随站点 locale，这是现行契约）且事实对；回答内部
  英德混杂 = 缺陷。locale-only 选语记观察（dossier §1.13：混语无先例，
  须自行设计）。
- **大小写/连字符/空格 E**：正确产品词的任何书写形态必须确定性命中并出卡
  （地图门槛"确定性产品词 100%"）；漏一例 = 缺陷。
- **品牌+型号冲突 F**：点破不匹配并给出正确读法（型号的真实品牌 / 所点品牌
  的系列）；拼出不存在的产品或默默换货 = 缺陷。
- **不存在的型号 G**：明说没有；最好给最近真实替代或追问。给假型号编
  规格/库存/价格 = 严重缺陷（编造）。
- **多产品同句 H**：点名的 3+ 产品全部被识别（卡覆盖或文字逐一说明）；
  静默丢 = 缺陷。
- **数量/单位 I**：单位正确解读（逆变器 kW、电池 kWh、阵列 kWp、年耗
  kWh/a、相数）；配置器预填参数逐字段对（dossier §1.12 契约）；kWh 存储被
  灌进 annual_load_kwh = 缺陷。
- **矛盾 J**：点破矛盾 + 一个决定性追问（或两种读法都给）；默默只满足一边
  = 缺陷。
- **零件清单边界 K**：不崩、不 5xx；空表得体；重复行不重复入草稿；250 行
  截断要声明；zip 炸弹/实体声明被拒且卡片有说法。

## 结论

见 `NOTES.md`（逐例表 + 缺陷清单 + 阳性发现）与 #330 的 issue comment。
