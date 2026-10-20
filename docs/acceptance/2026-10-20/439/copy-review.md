# #439 服务补句 — 文案记录（已签收 2026-10-20）

规则：AGENTS.md §2（业主 2026-10-09 / 2026-10-11：客户可见文案走对抗评审；EN 先定稿，DE 独立撰写，Sie 体，不是翻译）、§3 用词（产品 / Produkt；不说 catalogue、article、cart；禁止「不是…而是…」与 AI 句式）、linker-copywriting Hard Stops 1–9。这些句子写在回答正文里，不是邮件主题。

范围：`services/genie/src/linker_genie/template.py` 的 `seal`。只在基线要求的那一句还没出现时补上。毫米句只补本轮文档事实里已经写出的数，不编造。可用容量的 260 kWh 与 98% 只在文档事实里有对应的数字词时补上；型号里的 `L260` 不算。

状态：下面的英文和德文是本轮写进代码的句子。协调者对抗评审已签收（2026-10-20，见文末）。后续改动任一句须重新走对抗评审。

Coordinator sign-off: approved (2026-10-20)

sizing 路由补上的应用追问芯片是 #394 已签收的 `home` / `commercial` 与 `Wohngebäude` / `Gewerbe`，不是本轮新句，不在下面重写。

## 英文定稿

可用容量缺失。基线 b20-en 认 `do not state` 这一组，不认 `is not printed`。这一句单独成句，句内不写数字，避免把数字绑到 usable capacity 上。

- `The documents do not state a usable capacity.`

EnWG 14a 缺失。这是否认，不是支持声明。`whether` 把 `supports` 留在否认里，基线 b25-en 的 `no_clause` 不把这一句当成支持。

- `The documents do not state whether it supports this.`

文档里已有的标称容量与放电深度。两句都在时用第一句；只有其中一个数字时用后面两句里对应的那句。数字只来自本轮文档事实。

- `The documents state a nominal capacity of 260 kWh and a depth of discharge of 98%.`
- `The documents state a nominal capacity of 260 kWh.`
- `The documents state a depth of discharge of 98%.`

安装间隙。只列出文档事实里已有、回答里还没写成 `N mm` 的 1500、1000、500、400。一个数用第一句，多个数用第二句，连接词前不加逗号。

- `The installation documents state a clearance of 1000 mm.`
- `The installation documents state clearances of 1500 mm, 1000 mm, 500 mm and 400 mm.`
- 两个数：`The installation documents state clearances of 1500 mm and 1000 mm.`

## 德文

独立撰写，Sie 体，不是上面英文的逐句对译。这些句子陈述资料写了什么，不称呼客户。百分比前留空格，是德文排印，不是英文 `98%` 的对译。

可用容量缺失。基线 b20-de 认 `nennen keine`。不用 `keine nutzbare Kapazität` 去撞另一支正则：那一支会把 `nutzbare` 吃进可选词。这一句单独成句，句内不写数字。

- `Die Unterlagen nennen keine nutzbare Kapazität.`

EnWG 14a 缺失。用 `Unterstützung`，不用 `unterstützt`，以免撞上基线 b25-de 禁止的支持动词。

- `Die Unterlagen nennen keine Unterstützung.`

文档里已有的标称容量与放电深度。名词用 `Nennkapazität` 与 `Entladetiefe`，不是把英文 nominal / depth of discharge 逐词搬过来。

- `Die Unterlagen nennen eine Nennkapazität von 260 kWh und eine Entladetiefe von 98 %.`
- `Die Unterlagen nennen eine Nennkapazität von 260 kWh.`
- `Die Unterlagen nennen eine Entladetiefe von 98 %.`

安装间隙。`Montageunterlagen` 与 `Abstand` 是这一问的词，不是 `installation documents` 的逐词对译。一个数与多个数分两句。

- `Die Montageunterlagen nennen einen Abstand von 1000 mm.`
- `Die Montageunterlagen nennen Abstände von 1500 mm, 1000 mm, 500 mm und 400 mm.`
- 两个数：`Die Montageunterlagen nennen Abstände von 1500 mm und 1000 mm.`

## 核对清单

这一轮的判断写在每条后面。协调者已签收（见文末对抗评审）。

- Hard Stop 1：这一轮未看到 `proven`、`tier-1`、`leading`。
- Hard Stop 2：这一轮未看到把证书、协议、RMA 堆成卖点。
- Hard Stop 3：这一轮未看到「我们不是中间商」。
- Hard Stop 4：这一轮未看到 `direct` / `official` / `guaranteed`。
- Hard Stop 5：这一轮没有新编时效，也没有回本期。
- Hard Stop 6：这一轮未看到 `Get help…`、`Tell us`、`Send us`。这些句子不是派给客户的作业。
- Hard Stop 7：这些句子是回答正文，不是邮件主题。公开面用词按 §3 核过：没有 catalogue、article、cart。
- Hard Stop 8：这一轮未看到把接线或实验室验证写成卖点。
- Hard Stop 9：这一轮未看到 Future、Weight、Duration 的写法。间隙列举是资料里已有的四个数，不是口号排比。
- AGENTS.md §3：这一轮未看到 catalogue、article、cart、Artikel、Katalog、Warenkorb。德文用 Unterlagen、Kapazität、Abstand。
- 句式：这一轮未看到「不是…而是…」，新句子里没有 em dash，没有收束句。
- 德语：这一轮按独立成文写的。容量句用 `nennen keine`；支持句用名词 `Unterstützung`；间隙句用 `Montageunterlagen` 与 `Abstand`。都不是英文的逐句对译。
- 支持句是否认。英文用 `do not state whether`，德文不写 `unterstützt`。
- 毫米句与 260 kWh / 98% 只复述本轮文档事实里已有的数。事实里没有的数不补。

协调者若要改字，改 `template.py` 里的这些句子，并改这篇记录。


## 协调者对抗评审（2026-10-20）

逐组复核：全部为复述本轮文档事实的陈述句；缺席句与基线判分句式一致（do not state…/nennen keine…）；支持句是否认（德文用名词 Unterstützung 避开支持动词）；毫米与 260 kWh/98 % 只在本轮事实已有且正文未写时补，不编数；Hard Stop 1–9 与 §3 用词无违例；德文独立成文（Montageunterlagen/Abstände/Nennkapazität 均非逐词对译）。与 template.py 实际字符串一致。无改动，按本记录定稿。
