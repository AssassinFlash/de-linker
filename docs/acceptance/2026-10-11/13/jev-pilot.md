# #13 Jev 试点：真实管线回合的事后判分（2026-10-11）

Jev 评审级联在真实管线里的首次运行。对象：同日 deepseek-flash 直连复跑的全部 11 轮
（`docs/acceptance/2026-10-11/13/deepseek-flash/panel-*.json`，turn 177–187）。
级联形态（业主裁定 2026-10-11）：**jev-1.13 第一道（经 aihubmix `/v1/systemone`），
任一问置信度低于冻结阈值 → 整条升级 deepseek-flash 直连官方 API**；
`gemini-3.8-flash`（被封会话在 #33 规格里自拟的候选、业主从未认可）已全部清除。

## 判据（进仓库，#16 复用）

问题文案就是 #33 正式轮的同一套（`services/genie/eval/judges/src/linker_judges/rubric.py`，
"one wording, every judge"）：

- **grounded**（score 三档 0/1/2）：对照 `reference`（本轮工具实际返回）判答案中的产品事实——0 矛盾、1 不可证、2 支持；单位换算与措辞差异算一致。
- **appropriate**（noul）：是否越界（配送/库存量/安装/保修/价格/支付/公司本身只给 sales@de-linker.com 转接）。
- **better_pick**（choice A/B/equal）：两个候选回答哪个更好（对 `reference` 正确且不越界）。

试点专属的构造与级联决策在 `services/genie/eval/judges/src/linker_judges/turns.py`
（阈值 `TURN_THRESHOLDS`：grounded ≥ 0.85、appropriate ≥ 0.5、better_pick ≥ 0.6——
#33 正式轮校准集冻结值，原样沿用）；驱动脚本 `services/genie/eval/judges/pilot.py`
（归档流解析、能力回放、级联执行、记录落盘）。单测 `tests/test_turns.py`
（16 个测试含本模块 7 个）锁阈值与"低于阈值无回退 → unresolved，不静默取首道"。

## 每轮条目构造

- **question**：面板原问句（`pilot.py` QUESTIONS，与 `genie-panel.md` 一致；归档与 turn 日志不存问句原文）。
- **answer**：渲染层所见——text/handoff/ask/action 块文本 + `Products offered: <卡片 id 列表>`。
- **reference**：本轮实际发生的能力调用（turn 日志 `tool_calls`）**只读重放**（匿名 GET，`linker_genie.abilities` 同一 wire format），返回 JSON 原样作 reference。
- **answer_a/answer_b**（仅多候选行，共 8 行）：A = 真实回答；B = 机械换走一个卡片 id 的变体（换入 ETR 商用机 6507、未放行电池 3581、被劝退的 2199 等参照外产品），正确答案必须是 A。R8/R14（无候选）、R13（单候选）不问 better_pick。

## 逐轮结果（级联终审）

| 行 | grounded（来源） | appropriate（来源） | better_pick（来源） | 升级 | 与确定性一致 |
|---|---|---|---|---|---|
| R1 | 2（deepseek） | yes（jev） | A（jev） | 是 | ✓ |
| R2 EN | 2（deepseek） | yes（jev） | A（jev） | 是 | ✓ |
| R2 DE | 2（deepseek） | yes（jev） | A（jev） | 是 | ✓ |
| R5 | **0（deepseek）** | yes（jev） | A（jev） | 是 | **✗（见下）** |
| R8 EN | 2（jev，0.86 过阈） | yes（jev） | — | 否 | ✓ |
| R14 DE | 2（deepseek） | yes（jev） | — | 是 | ✓ |
| R10 | 2（deepseek） | yes（jev） | A（jev） | 是 | ✓ |
| r3 拼写类 | 2（deepseek） | yes（jev） | A（jev，0.62 过阈） | 是 | ✓ |
| r4 拼写类 | 2（deepseek） | yes（jev） | A（jev） | 是 | ✓ |
| r11 拼写类 | 2（deepseek） | yes（jev） | A（jev） | 是 | ✓ |
| r13 拼写类 | 2（deepseek） | yes（jev） | — | 是 | ✓ |

## 升级统计

- 升级条目：**10/11**（唯一未升级的 R8 EN：jev grounded 置信度 0.86 ≥ 0.85）。
- 升级全部由 **grounded** 驱动：jev 在大 reference 状态上的 grounded 置信度 0.00–0.83，全部低于 0.85；appropriate（0.82–0.94 ≥ 0.5）与 better_pick（0.62–1.0 ≥ 0.6）从未升级。
- **与确定性五核验一致率：29/30 ≈ 96.7%**（grounded 10/11、appropriate 11/11、better_pick 8/8）。确定性真值：全部落档行 grounded=true（→ grounded 应为 2）、行级行为符合面板期望（→ appropriate yes）、构造变体应落败（→ better_pick A）。

### 唯一分歧（R5 grounded=0）的分类

deepseek 升级判分的理由："answer lists product 4107 among the documented battery pairings, but the reference identifies 4107 as the H2-10K-T3 inverter itself"。**根因在试点构造，不在回答**：R5 的卡片集是 4107（页面本体）+ 7 块放行电池，构造把两种角色拍平成一个 `Products offered` 列表，判分模型把"对下列每块电池有 documented pairing"读成了对列表全员成立的断言。服务端确定性核验（cards ⊆ qualified、配对来自 search/check 工具结果）与回答文本本身均无此问题；同构造的 R10（含本体 3556）未被误判。后续若常态化，条目构造应区分卡片角色（页面本体 vs 推荐产品）——留给 #16。

## 成本与延迟（11 轮、30 问）

| 评审 | 调用 | 输入 tokens | 输出 tokens | 成本（按峰值价） | p50 / max |
|---|---|---|---|---|---|
| jev-1.13（aihubmix） | 11 | 60 995 | 676 | $0.0028 | 1.75 s / 2.49 s |
| deepseek-flash（直连，升级） | 10 | 56 813 | 18 014 | $0.0387 | 5.57 s / 23.23 s |

合计 ≈ **$0.042**（deepseek 按官方峰值价 $0.30/$1.20 每百万计——`api-docs.deepseek.com/quick_start/pricing`；本轮为周日，实际落谷段价约减半，故该数为保守上界）。运行记录（每次调用的原始判定、token、耗时、UTC 时刻）：`services/genie/eval/judges/runs/pilot-20261011/{items,jev,deepseek,cascade,summary}.jsonl`。

## 结论与移交

1. 级联在真实管线上可用：无一处把越界判为合规（appropriate 11/11），构造的错选变体 8/8 被识别（better_pick 全 A）。
2. jev 的 grounded 置信度在大 reference 状态上系统性偏低（10/11 升级）——#16 常态化时要么按本试点的实测重新校准 grounded 阈值，要么给 jev 更小的 reference 切片；本轮不改阈值（沿用 #33 冻结值）。
3. 唯一分歧为构造歧义（R5），分类与修法见上；确定性五核验仍是发布门槛，级联目前只做事后评测第一道，不进回答路径（§33 规格不变）。
