# FAQ 引文门缺陷复现与修复（PR #58 评审 Spec①，2026-10-10）

评审清单必改 ① 的前三步：复现 `tools/faq/generate.py` 门缺陷三处、修检查器、量化影响面。
恢复轮（对 58 条重跑门 + 重评审 + 同步 summary/withdrawn/_linker_faqs/docs）不在本步，见文末"遗留"。

## 背景

全库 272 条 FAQ（168 pass / 85 withdrawn / 19 reject）。85 条 withdrawn 中
**58 条的 reason 是确定性门的字符串 "a number is not in the cited passage"**（其余 27 条为模型判断撤下）。

## 三处缺陷

### A. retrieve() 的 1800 截断

`generate.py` 原第 160 行 `"text": hit.text[:1800]`：检索 chunk 文本送生成、送门之前都被砍到 1800 字符。
索引里 `length(text)>1800` 的 chunk 有 **328 条**（最长 5,407）。

机制实证（对全库 32,852 个 chunk 统计带量纲数字 `\d+[.,]?\d?\s?(mm|kg|Nm|kW|kWh|V|A|Hz)`）：
**4 条 chunk 的带量纲数字只存在于 1800 之后**（例：GW_Commercial-Smart-Inverter-Solutions_User-Manual-ET25-50kW-EN.pdf p.4，
len 2,884，`56.3kW`/`156kW` 只在目录行尾部出现）。截断是真实的信息损失机制。

**对 58 条的实际影响：0。** 对 58 条答案里的每个数字做逐 chunk 检查——没有任何一条的关键数字只存在于某 chunk 的
`text[1800:]`（复现脚本 `tail_only` 全空）。截断未造成这批误撤，但生成/评审模型同样只见截断文本，对后续
Spec② 重写轮是输入真实性隐患，故随本次一并去掉。

### B. flatten_passages() last-write-wins

原实现 `(url, page) -> text, last write wins`：同一文档页被索引成多个 chunk 时，门只看检索顺序里
最后一个 chunk 的文本。答案数字在兄弟 chunk 里 → 门误判 "a number is not in the cited passage" → 撤下。

**定量复现**（脚本见下）：对 58 条逐条取其 citation (url, page)，从索引取该页全部 chunk，用 `generate.py`
自己的 `numbers_supported`（含 MODELISH/skip 逻辑）在四种视图下验证答案：

| 视图 | 支持答案的条数 |
| --- | --- |
| 合并全文（该页所有 chunk 拼接） | **44** |
| 单个 chunk（全文，最好情形） | 31 |
| 合并后仍缺数字 | 14 |

31 条的答案数字集中在同页某一个 chunk 里——last-write-wins 恰好保住了别的 chunk；
**13 条的数字散落同页多个 chunk，任何单 chunk 都不支持，只有合并视图能通过**（例：saj-h2-10k-t3
"Which circuit breaker and AC cable…"引文 p.43 共 8 chunk，断路器数字与电缆截面数字分属不同 chunk；
goodwe-gmk330 "Which CT version…"引文 p.1 共 3 chunk）。

**44/58 = 75.9% 的撤下，其引文页本身完整支持答案**——与评审"抽样证明 58 条撤下全为假撤下（76% 连引文页不用换）"吻合。

### C. 密集页误撤具名样例

`saj-b2-5-0-hv1`（id 1832）问题 "How tall and how heavy is the assembled B2-5.0-HV1?"，答案
"dimensions are 261\*626\*365 mm … weight is 50.5 kg"，引文 B2 user manual EN p.10。
该页被索引为 **8 个 chunk**（规格表被切块，且同一张表重复解析出现两次），`50.5` **只存在于第 1 个 chunk**
（Weight 表行，`| Weight [kg] | 50.5 | 101 | 151.5 | 202 | 252.5 |`），其余 7 个 chunk 都没有。
last-write-wins 只要没保住第 1 个 chunk（7/8 概率）就撤下。58 条的页 chunk 数直方图：1×3、2×10、3×6、
4×6、5×7、6×2、8×16、9×1、11×3、12×2、14×1、16×1——引文页多为 4–16 chunk 的密集规格页。

其余样例：saj-h2-10k-t3 "Which circuit breaker and AC cable…"（引文 p.43，8 chunk）；goodwe-esa-gw10k-eta-g20
"How many BAT-D modules…"（2 chunk）。

### 14 条维持撤下（非门缺陷）

引文页合并全文也确实不含答案数字（例：saj-hs2-6k-t2-x 答案 `102,4` 不在引文页；goodwe-gw112-6-bat-ac-g10
答案 `1400` 不在引文页）——模型引错页或数字来自别处，撤下成立。恢复轮对这 14 条需另判（重引文页或维持）。

## 修法（三选：合并同页 chunk + 去截断）

选 **合并同页 chunk（首现顺序、去重拼接）+ 去掉 1800 截断**；不选 chunk 级引文，理由：

- 合并修复全部可恢复面（44/44），确定性，citation 数据形状（url/page/title）不变，`_linker_faqs`/import.py 零牵连；
- `numbers_supported` 对文本单调（超集只会更容易命中），168 条 pass 重放修复后的门 168/168 仍 pass，无回退；
- chunk 级引文要模型填对 chunk_id 且 `to_record` 根本不落 chunk_id——牵连 import/wordpress/数据形状；且
  44 条里 13 条的数字散落多 chunk，即使 chunk_id 全对也救不回；模型幻觉 chunk_id 反而引入新的假撤下，最不稳；
- 单独去截断修不了任何一条（B 是成因），但去掉后生成/评审模型与门看到完整 chunk，消除 Spec② 重写轮的输入失真。

改动（`tools/faq/generate.py`）：
- `retrieve()`：`hit.text[:1800]` → `hit.text`；
- `flatten_passages()`：last-write-wins → 同 `(url, page)` 全部 chunk 首现顺序去重、`\n` 拼接；
- `gate_item()` 不变（仍按 (url, page) 取合并文本）。

测试（`tools/faq/test_generate.py`，新增 3 个，`python3 -m pytest test_generate.py -v` → **8 passed**）：
- `test_flatten_merges_chunks_of_one_page`：同页两 chunk 拼接、跨页分键；
- `test_gate_judges_the_whole_cited_page_not_the_last_chunk`：数字在首 chunk、尾 chunk 无数字，门 pass，
  并断言旧 last-write-wins 视图确实判否（钉住回归）；
- `test_retrieve_ships_the_full_chunk_text`：断言 `retrieve` 源里 1800 截断不回归。

## 修复后复验（离线重放，不调模型）

以修复后的模块对 58 条跑真实 `flatten_passages + gate_item` 路径（hits 由索引按 rowid 构造）：
**44 条 gate pass，14 条维持 withdrawn（同一 reason）**；168 条 pass 条目重放 **168/168 仍 pass**。
对 44 条的答案数字逐条核验：全部数字出现在引文页合并全文（EN 与 DE 同过）。

复验命令与脚本主体（可复跑；索引路径 `~/de-linker-data/index/builds/20261010T082155Z/index.sqlite`，只读）：

```bash
python3 -m pytest tools/faq/test_generate.py -v
# 重放：对 docs/faq/*.json 的 58 条 gate-withdrawn / 168 条 pass，按 citation (url,page)
# 取索引该页全部 chunk 构造 hits，gen.flatten_passages() + gen.gate_item()，统计输出状态
```

ruff（uvx ruff check，两文件）：改前 11 条发现 → 改后同 11 条，**零新增**（存量 EXE001/FURB167/RUF100/TRY004
与 format 欠账属 Standards R1 的 tools/faq 入管线票，本票不清洗未触碰行）。

## 遗留（恢复轮，评审必改 ① 的剩余部分）

1. 对恢复面重跑门 + 重评审：44 条的 EN/DE 答案与引文已在档（`docs/faq/<slug>.json` 保留完整 EN/DE 答案），
   门确定性翻绿；但 `review` 字段仍是 "withdrawn"，须重跑独立评审会话（DeepSeek）确认后才能翻 pass。
2. 同步 `summary.json` / `withdrawn.md` / `_linker_faqs`（线上只读，经本地栈）/ docs 档案。
3. 14 条维持撤下的：按评审裁定口径处理（同题不同裁统一，IOT dongle 例）；或换正确引文页。
4. Spec② 19 条 reject 终态、Standards R1–R3 与建议项：各自票。
