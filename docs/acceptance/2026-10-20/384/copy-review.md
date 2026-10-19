# #384 复合极端问法 — 待协调者对抗评审

规则：AGENTS.md §2（业主 2026-10-09 / 2026-10-11：客户可见文案走对抗评审；EN 先定稿，DE 独立撰写，Sie 体，不是翻译）、§3 用词（产品 / Produkt、型号 / Modell；不说 catalogue、article、cart；禁止「不是…而是…」与 AI 句式）、linker-copywriting Hard Stops 1–9。这组句子是对话兜底，不是邮件主题，也不是页面文案。

范围：`services/genie/src/linker_genie/template.py` 里本轮新增或改由服务直接写出的两句。

- 点名客户写过的型号：`You named {codes}.` / `Sie haben {codes} genannt.`
- 价格门：`Approved partner accounts see net prices.` / `Freigegebene Partnerkonten sehen die Nettopreise.` 原先只作为给模型的提示（`prompts/en/system.md`、`prompts/de/system.md`，以及 `docs/acceptance/2026-10-18/242/copy-review.md` 里的指示句）。隐藏价格且同一问法写了型号时，服务现在把这句写进兜底正文。

沿用、本轮不改写的句子：极端赢家句 `The {model} meets the limit you named.` / `Das Modell {model} erfüllt die genannte Grenze.`（#368），以及 #379 已记录的范围句和「这轮没有搜」。`DEGRADED` 不在此列。

状态：下面的英文和德文是本轮写进代码的句子，核对清单是这一轮的判断。协调者的对抗评审还没有做。在协调者写回之前，不能把这篇当成已通过的评审。

设计理由：dossier `docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md` §1.1、§1.11 没有「极端问法同时点名若干型号」的成句可抄。赢家句和范围句沿用既有兜底；点名句和价格门是服务自己写的。

Coordinator sign-off: approved (2026-10-20)

## 英文

点名。客户在同一问法里写下的型号，赢家句之外再写一行。多个型号用逗号隔开，不排名，不说哪一个最便宜。

- `You named {codes}.`

价格门。账户看不到净价，而且这一问还写了型号。只说明谁能看见净价，不写金额，不把某个型号称作最便宜。

- `Approved partner accounts see net prices.`

## 德文

独立撰写，Sie 体，不是上面英文的逐句对译。不出现 „ich“。型号码原样保留。

点名。说的是客户已经写下的型号，不是服务替客户做的选择。不用 „nannten“，也不把英文的 named 收成 „benannt“。

- `Sie haben {codes} genannt.`

价格门。主语是账户，不是对客户下命令。可见的是净价这一事实，没有金额，也没有把某个型号说成最便宜。

- `Freigegebene Partnerkonten sehen die Nettopreise.`

## 核对清单

这一轮的判断写在每条后面。未签收不等于这些句子已通过对抗评审。

- Hard Stop 1：通过。没有 `proven`、`tier-1`、`leading`。
- Hard Stop 2：通过。没有把证书、协议、RMA 堆成卖点。
- Hard Stop 3：通过。没有「我们不是中间商」。
- Hard Stop 4：通过。没有 `direct` / `official` / `guaranteed`。`approved` / `freigegeben` 是账户状态，删掉之后句子不再为真。
- Hard Stop 5：通过。没有编造的时效。
- Hard Stop 6：通过。没有 `Get help…`，也没有 `Tell us` / `Send us`。
- Hard Stop 7：这两句是对话兜底，不是邮件主题。本轮不把它们放进邮件主题。公开面用词按 §3 核过：没有 catalogue、article、cart、Artikel、Katalog、Warenkorb。
- Hard Stop 8：通过。没有把接线或实验室验证写成卖点。
- Hard Stop 9：通过。没有 Actor、Future、Weight、Duration 的写法。点名句陈述客户已经写下的型号，不给客户布置下一步。
- AGENTS.md §3：通过。德文用 Produkt 的范围句不在本轮新句里。这两句没有系列词。
- 句式：通过。没有「不是…而是…」，没有 em dash，没有三连排比，没有收束句。
- 德语：通过这一轮的自查。Sie 体。点名句用 „genannt“，价格门以账户作主语，都不是英文的逐词对译。

## 本轮对原先问题的处理

1. 点名句只列型号码。它不说哪个最便宜，也不引出第二张赢家卡。
2. 价格门从「让模型自己说」改成服务写出的正文。英文沿用提示里已经在用的那句；德文按客户读到的句子另写，不是提示句 „Sagen Sie, dass …“ 的搬移。
3. 这两句留在对话兜底里，不作为邮件主题。

协调者若要改字，改 `template.py` 里的这两句，并改这篇记录。#368 的赢家句和 #379 的范围句不在此列。

## 协调者对抗评审（2026-10-20）

逐条复核核对清单，并对照 `template.py` 实际写出的句子：

- 英文 "You named {codes}." 只复述客户自己写下的型号，不加排序、不引出第二张卡；单型号时读作 "You named HS3-5K-T2." 成立。
- 德文 "Sie haben {codes} genannt." 是独立句式，Sie 体，型号码原样，不出现 „ich“；不是英文逐词对译。
- 价格门英文沿用 #242 提示里已经在用的 "Approved partner accounts see net prices."，德文以账户作主语，两句都不含金额、不称某型号最便宜。
- 与 `template.py:199/201/254/255` 的实际字符串一致；Hard Stop 1–9 与 §3 用词复核通过。
- 无改动。这两句按本记录定稿。
