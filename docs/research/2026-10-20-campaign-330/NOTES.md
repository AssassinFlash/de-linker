# #330 输入边界批 — 结果与缺陷清单

- 日期：2026-10-19/20。票 #330（地图 #329）。性质：只测试。服务与插件零改动。
- 本地：实例 `c330`（快照 20261019-1409 + live 代码；WP 127.0.0.1:9162，
  Genie 127.0.0.1:9164；文档索引 build 20261018T173840Z）。
- 证据（机器本地）：`~/de-linker-data/campaign-330/`
  - `evidence/cases.jsonl` — 111 例逐例原文（请求、SSE、meta、blocks、耗时）
  - `evidence/attribution.jsonl` — 与服务 turn log 的 join（词表命中、Jev 答案、
    路由、每次工具调用与结果）
  - `evidence/graded.jsonl` — 人工终判（pass/defect + 缺陷号 + 观察）
  - `smoke/smoke.jsonl` — 生产 10 探针（最终 URL、响应头、原文）
- 判定标准见 `README.md`。规则：每条结论以该次回答原文为证；"答得还行"不算过。

## 1. 结果总览（111 例 / 111 个真实回合）

| 类 | EN | DE | pass | defect |
|---|---|---|---|---|
| 错拼/模糊拼写 | 5 | 5 | 9 | 1 |
| emoji | 5 | 5 | 10 | 0 |
| 超长输入（>4k 字符） | 5 | 5 | 10 | 0 |
| 混合语言 | 5 | 5 | 10 | 0 |
| 大小写/连字符/空格（100% 门槛） | 6 | 5 | 11 | 0 |
| 品牌+型号冲突 | 5 | 5 | 8 | 2 |
| 不存在的型号 | 5 | 5 | 7 | 3 |
| 多产品同句 | 5 | 5 | 9 | 1 |
| 数量/单位 | 6 | 6 | 11 | 1 |
| 矛盾条件 | 5 | 5 | 9 | 1 |
| 零件清单边界（含 xlsx DoS 回归） | 7 | 1 | 8 | 0 |
| **合计** | **59** | **52** | **102** | **9** |

9 个缺陷回合归并为 **7 个缺陷**（D1 覆盖 3 个回合）。耗时：p50 8.2 s、
p95 20.0 s、最大 28.5 s——地图硬门槛 p95 ≤ 30 s 达标，目标 ≤ 15 s 未达
（dossier §1.14：无竞品 SLO 可抄，须自行设计）。

## 2. 缺陷清单（按客户痛感排序）

每条含最小复现（原文）、期望 vs 实际、分层归因、复刻/须自行设计裁定（引
dossier 章节）。原文均可在 `graded.jsonl` 按 case id 检索。

### D1 · 产品词搜索零结果 → 直接转团队，不澄清（3 个回合）
- **最小复现**（EN）：`Is the SAJ GW10K-ETA-G20 in stock?` →
  `{"type":"handoff","summary":"Our team will answer that at sales@de-linker.com."}`
  （meta `grounded=false, fallback=true, failures=["a products turn is not a question for the team"]`）
- **最小复现**（DE）：`Haben Sie den GW50K-ETA-G20 auf Lager?` → 同一句德语
  handoff；EN 同题 `Do you have the GW50K-ETA-G20 in stock?` 亦同。
- **工具证据**：`search-products {text:"GW10K-ETA-G20", brand:"saj"}` →
  `qualified: []`（excluded brand 72 / text 34）——品牌与型号被 AND 在一起，
  冲突输入必然零结果。
- **期望**：先点破"这是 GoodWe 的型号，不是 SAJ"，并给出该产品（同输入
  F1-DE 做对了）；不存在的型号明说没有并给最近型号（G2/G3/G4 做对了）。
- **实际**：兜底模板在 `qualified` 为空时只回一句转团队；无"没找到/请澄清"形态。
- **分层归因**：① 确定性匹配（`route._search_input` 把品牌与型号 AND 成一次
  查询，冲突即零结果）② 提示词/水合（`template.fallback` 无 qualified 分支只
  有 handoff 句）③ 模型（品牌冲突回合改写了 handoff-team）。
- **复刻/须自行设计**：确定性优先=复刻（dossier §1.1，京东政企 S24 / 1688
  S33）；**零结果后的澄清话术与品牌冲突消解属须自行设计**（§1.1 末段、
  §1.11 消歧、§2 排名第 10）。
- **生产复现**：S5（同 GW50K 题）→ `Our team will answer that at
  sales@de-linker.com.`（fallback=true）。非本地环境问题。

### D2 · 多产品同句：代码只搜第一个型号，模型把"没搜"说成"不存在"
- **最小复现**：`Do you have HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX and
  HS3-12K-T2-W/G-PX in stock?` → 回答 "These two model codes return no entry in
  our product data, so I cannot confirm them."——两件实际在售。
- **工具证据**：EN 回合只发 1 次 `search-products {text:"HS3-5K-T2-W/G-PX"}`
  （代码 `route._search_input` 只取 `models[0]`）；DE 同一输入的回合由模型
  三次搜索，三件全部命中（H4-DE 通过）——**EN/DE 不同结构**。
- **分层归因**：确定性路由（多型号只查第一个）+ 模型（把未检索断言为不存在，
  grounding 未拦 absence 断言）。
- **复刻/须自行设计**：一句多条件有先例（千问 CN §2.1；dossier §1.1）→
  多查属复刻；多型号确定性多查后的聚合无公开实现 → **须自行设计**
  （§1.11 消歧）。

### D3 · DE 侧配置器预填被模型加入客户未声明的相数
- **最小复现**：`Meine PV-Anlage hat 12 kWp und ich möchte 15 kWh
  Batteriespeicher.` → `open_configurator` URL
  `?pv_kwp=12&phase=1`——客户从未说单相。
- **工具证据**：Jev sizing 置信 0.77 < 0.8 → 路由落 `model`，模型自行调
  `size-hint {"pv_kwp": 12, "phase": 1}`；EN 同题置信 ≥0.8 由代码直调，URL
  正确为 `?pv_kwp=12`。
- **分层归因**：Jev 路由（阈值下掉入模型代调）+ 提示词（工具参数没有"只准
  用客户原话"约束）+ 配置器预填契约。
- **复刻/须自行设计**：**预填参数契约的正确性属须自行设计**（dossier §1.12
  明写）；"确定性优先、模型只表达"=复刻（§1.1）。

### D4 · 不存在型号触发知识检索重试超限 → 降级模板出不相干产品卡且无降级声明
- **最小复现**：`Do you carry the EcoFlow OCEAN 3 HD-P3-20K0-S2?` →
  failures=`["Tool 'linker_search_knowledge' exceeded max retries count of 1 …"]`，
  回答 "Here are matching products from our range." + 卡 3608（OCEAN 2 LFP
  Battery Base，与问题无关）+ 一个 backup 追问。
- **分层归因**：工具（`retry=1` 不足，pydantic 错误原文进 failures）+ 水合/
  模板（products 路由无 qualified 时仍从 `facts.product_ids` 出卡；降级未按
  DEGRADED 声明）+ 基础设施（模型工具调用超限）。
- **复刻/须自行设计**：失败 UX 的模式语言可复刻（uxpatterns.dev"恢复路径
  匹配失败模式"，dossier §1.15）；**重试次数与降级形态属须自行设计**（§1.15）。

### D5 · 品牌冲突在 DE 没点破（EN 同题做对）
- **最小复现**：`EcoFlow GW5K-ETA-G20 - lieferbar?` → "Zu EcoFlow
  GW5K-ETA-G20 finde ich in unserem Sortiment kein Produkt"；该型号是 GoodWe
  在售产品。EN 同输入（F4-EN）给了 GoodWe 卡并说明型号属 GoodWe。
- **分层归因**：确定性匹配（brand+text AND → 0 结果）+ 模型（未跨品牌纠正）
  + 路由（Jev company_logistics_service 0.44 低置信，交模型）。
- **复刻/须自行设计**：消歧**须自行设计**（dossier §1.11，无竞品先例）。

### D6 · "最小 ≥30 kW" 选错（EN）
- **最小复现**：`What is your smallest inverter with at least 30 kW?` →
  答 **GW75K-ET-G10**（75 kW）；实际最小为 GW30K-ETA-G20（30 kW）。DE 同题
  正确（GW30K-ETA-G20，并对照 SAJ H2-30K-T3-DE 29.999 kW）——EN/DE 不同结构。
- **分层归因**：检索（search-products 的默认排序，未按 `ac_power_kw` 过滤
  ≥30 再取最小）+ 提示词（无"最/极值"类聚合规则）；数字本身均可追溯，无编造。
- **复刻/须自行设计**：参数纠偏仅千问方向性证据（§1.1）；**极值/聚合问题
  须自行设计**（dossier §1.1 末段）。

### D7 · 拼写变体：3 字符型号码不入词表（"BD-8"）
- **最小复现**：`Looking for Ecoflow Ocean two batteries, the BD-8 one.` →
  返回 Battery Base 卡并说找不到电池，实际有 **EF BD-8-S2**（id 3582）。
- **证据**：`lexicon.MIN_CODE = 4`（"BD8" 3 字符被排除；注释：two-/three-
  character tokens 是后缀，防误匹配）；词表只有 "OCEAN 2" 系列别名与
  "Battery Base" 标题。
- **分层归因**：确定性匹配（词表无此键）+ 检索（模型拿不到该候选）。
- **复刻/须自行设计**：**错拼与短码匹配策略属须自行设计**（dossier §1.1
  末段；§2 排名第 7）。

## 3. 观察（不判缺陷，供修复票参考）

- **回答语言跟站点 locale，不跟问句语言**：EN 站德语问（D3-EN）答英语、DE
  站英语问（D3-DE）答德语。现行系统提示按 locale 写死（`prompts/{en,de}`）；
  与 dossier §1.13 的"德语问德语答"（同一 DE 站内）不冲突，记为现行契约。
- E6-EN（"GOODWE inverters — which models"）只列单相 EHA 六款，未提 ETA 三相
  系列：不假，但不完整。
- 空 xlsx（K2）被描述成"could not read"，实为"读到了、没有数据行"——话术
  可更准。
- 粘贴列表的引导句（"Here is my equipment list"）被当作 missing 行显示
  （C1-EN/C5-EN）——诚实，但显示为"不在产品范围"。
- H5-EN/H5-DE：第 5 个型号因工具预算（4 次）未出卡，回答明确说明并可再查
  ——按本批标准算过，但说明"3+ 型号一句问"在预算内只能覆盖到 4 个。

## 4. 阳性发现（战役需要两面）

1. **确定性产品词 100%**（地图门槛）：E 类 11/11 命中——小写、全小写连写
   （H210KT3）、空格、逗号小数（GW5,1）、DE 问句全部出卡。E 类之外，A 类
   9/10 的错拼由模型层纠正（A1 "K not O"、A4 "GooodWe/G2O"、A5 "SAJJ …
   1OK" 都答对）。
2. **0 编造数字**：E5 的 108 来自目录 `kwh_range`，I6 的 29900/29999 分别引
   手册与证书块，D4-DE 的 108 同源；Grounding 数字门在生效（I1-DE 模型写
   "2" 被拦，走诚实兜底）。
3. **型号消歧**：ESA EHA/ETA 单三相（B5、J3、J4、F1-DE、I4）、OCEAN 2 单三
   相（B5-DE）全部正确；J4-EN 明说"三相 GW5K-EHA-G20 不存在"。
4. **假型号拒绝**：G2/G3/G4/G5-DE 明说没有 + 给最近真实型号；G4-EN 拒绝为
   编造 SKU 报价。
5. **零件清单边界全过**：正常/空表/重复行/超长行/250 行截断（`truncated:
   true`，正文"first part"）/zip 炸弹/billion laughs 共 8 例优雅处理；zip
   炸弹与实体声明被 reader 的 8 MiB 上限与 DOCTYPE 拒绝拦下（.xlsx DoS
   回归通过）。
6. **超长输入**：10/10 无 4xx/5xx、无超时；160 次重复问句仍答对；220 行
   列表 0.0 s 出 parts 卡。
7. **单位纠偏**：I2-EN 把 "10 kW of storage" 改读为 kWh 并给 10 kWh 电池；
   I6 双文档精确值对照。
8. **线上冒烟 10/10 HTTP 200**；E/H/J/单位与本地一致；A 类线上版本更强
   （S1/S10 指出字母 K vs O 并列出全系）。

## 5. 生产冒烟（10 探针，全部 HTTP 200）

终点 URL 均为 `https://de-linker.com/wp-json/linker-ai/v1/genie/turn`；响应头
一致：`Server: LiteSpeed`、`X-Powered-By: PHP/8.3.35`、`Content-Type:
application/json; charset=UTF-8`、`X-Robots-Tag: noindex`、`Link:
<https://de-linker.com/wp-json/>; rel="https://api.w.org/"`（每次日期头见
`smoke.jsonl`，2026-10-19 09:44–09:46 GMT）。公开 Genie 对话不发信；未点任何
询盘/联系发送。

| 探针 | 本地 case | 结果 | 与本地一致 |
|---|---|---|---|
| S1-A-EN 拼写 | A1-EN | H2-10K-T3 指出 K vs O，6 卡 | 是（线上更完整） |
| S2-B-EN emoji | B1-EN | 读作 storage，5 卡 + 追问 | 是 |
| S3-E-EN 变体 | E1-EN | 三相，卡 3556 + 文档 | 是 |
| S4-F-EN 品牌冲突 | F1-EN | GoodWe 3556 + 可用性（23.0 s，attempts=2） | 本地兜底、线上成功——**同缺陷采样相关** |
| S5-G-EN 假型号 | G1-EN | handoff "Our team will answer that at sales@de-linker.com." | **是：D1 线上复现** |
| S6-H-EN 多产品 | H3-EN | compare 三件，13.5/9/4.5 kWh | 是 |
| S7-I-EN 单位/预填 | I3-EN | URL `?pv_kwp=8&annual_kwh=4000&phase=3` | 是（预填线上正确） |
| S8-J-EN 矛盾 | J3-EN | 指出 EHA 单相→ETA 三相 | 是 |
| S9-E-DE 变体 | E1-DE | 德语、三相、卡 + 文档 | 是 |
| S10-A-DE 拼写 | A1-DE | 德语指出 K vs O，6 卡 + 追问 | 是 |

## 6. 复跑

见 `README.md`。批次可裁剪：`run_battery.py <dir> --ids A1-EN,...`；生产
`prod_smoke.py`（只读，无询盘/联系动作）。
