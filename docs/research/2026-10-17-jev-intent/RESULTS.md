# Genie · 实测 Jev 能否做意图识别（#260，地图 #220）

日期：2026-10-17。业主问：能不能让 Jev 在 Genie 回答之前先识别客户意图，减轻 deepseek-flash 的识别负担？别的 AI 说"Jev 不是这样用的"。

## 结论

**能，而且这正是 Jev 的官方用法。** TypeSafe 文档"Intent routing"（https://docs.typesafe.ai/patterns/intent-routing ，2026-10-17 经 Apify 读取）原话："Classify incoming requests and route each to the optimal handler: deterministic logic, a specialist LLM, or a human. TypeSafe can sit in front of all of these as a fast, cheap classifier that determines which handler to invoke." 设计指南（/concepts/how-to-build-with-system-one）："Keep control flow, deterministic rules, and side effects in code. Break broad judgments into narrow, typed questions … Use probabilities and confidence to act, ask for review, or escalate."
别的 AI 说对的只有一半：Jev 不写字，不能把问句改写成一句更好的话；它回答有类型的小问题（选项 / 是否 / 打分，带置信度）。对 Genie 这比改写更好——代码可以直接按答案路由。

## 实测（typesafe/jev-1.13-20260917，经 OpenRouter `/api/v1/systemone`；同形状的 `/api/alpha/decisions` 也可用）

60 条客户消息（EN 32 / DE 28），页面上下文分首页、产品页（SAJ H2-10K-T3）、分类页、Lösungsentwurf、账户页。三个问题一次发出：`intent`（10 选 1）、`about_this_page`（是否）、`wants_person`（是否）。脚本 `eval.py`，原始响应 `raw/run1.json`、`raw/run2.json`。

| 指标 | 结果 |
|---|---|
| 意图准确率 | 58/60 = 97%（EN 31/32，DE 27/28） |
| 高置信（≥0.8）覆盖 / 其中准确率 | 57/60 = 95% / 56/57 = 98% |
| "saj" / "SAJ" / 德语页"saj" | 全部 find_products，置信 0.99–1.00；goodwe、zendure、H2-10K-T3、GW10K-ET、CB2-100.3-HV5 同 |
| about_this_page | 59/60 |
| wants_person（找人 / 不满） | 59/60 |
| 两次重跑一致性 | 60/60 意图完全相同 |
| 延迟 | p50 2.6 s，p90 2.8 s（本机 → OpenRouter） |
| 费用 | 每条约 $0.000033 |

两个错：德语"Erzähl mir einen Witz"判成 small_talk（期望 other，两者处理相同）；"what happens after I send the inquiry?"判成 inquiry_status，置信 0.58——低置信，按设计交 deepseek-flash 决定。

## 据此采用的设计（写入 `docs/specs/13-genie.md` 目标第 2 条）

每条消息：① 代码先做产品词确定性匹配；② Jev 一次问意图 / 是否问本页 / 是否找人 / 是否要追问；③ 代码按答案路由（高置信直接调对应工具：产品、文档向量检索、兼容、询盘状态、转人工；低置信交 deepseek-flash 决定——即 AGENTS.md 已裁定的"deepseek-flash 作 Jev 级联升级"）；④ deepseek-flash 只根据工具结果写回答；⑤ 回答发出后 Jev 质检（#258）。阈值 0.8 为本测试的起始值，上线后按线上数据调。
