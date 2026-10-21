# #497 屋顶步的签定回答 — 文案对抗评审

规则：AGENTS.md §2（业主 2026-10-09 / 2026-10-11：客户可见文案走对抗评审；EN 先定稿，DE 独立撰写，Sie 体，不是翻译）、§3 用词（产品 / Produkt、型号 / Modell、系列 / Serie；不说 catalogue、article、cart；禁止「不是…而是…」与 AI 句式）、linker-copywriting Hard Stops 1–9。本组句子是 Genie 对话里的规定回答，不是邮件主题。

范围：`services/genie/src/linker_genie/template.py` 的 `ROOF`（EN/DE 两条签定回答）。可点的一步 `open_configurator` 用既有 UI 文案 “Open the configurator” / “Konfigurator öffnen”（`ActionView.tsx`，`.po` 已有），本轮不改。

状态：下面的英文和德文是本轮写进代码的句子，核对清单是这一轮的判断。协调者已于 2026-10-21 签收（见文末）；本记录是定稿记录。Coordinator sign-off: approved (2026-10-21).

## 复刻来源

- 作用句逐字复用 #12 站点文案：EN `The Roof detail step adds the building's layout.`、DE `Der Schritt Dachdetails nimmt die Dachfläche auf.`（`docs/acceptance/2026-10-10/12/copy-review.md` §3）。
- 组件布置复用安装商页已通过的措辞：EN `module placement`（`docs/acceptance/2026-10-16/m2-copy/copy-review.md` §7）。
- 最后一句逐字复用引擎的 `limit.default_orientation`：EN `Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).`、DE `Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).`（`services/engine/src/linker_engine/texts.py` 第 559–561 行；`report.py` 第 360–361 行；#479 C57 实测记录 `docs/acceptance/2026-10-21/479/README.md` §2.1）。数字与措辞不改：35°、朝南、HTW 默认都来自这一句。

## 英文

屋顶步的作用与跳过它的代价。不写收益损失的数量（报告只说按 35° 估算，没有给差额），不写价格，不写回本期，不写邮箱，不写问号。

- `The Roof detail step adds the building's layout. It is optional and maps the roof surface and module placement. Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).`

评审：

- 首句逐字取 #12 已定稿的卡片句，主语式与站上一致，冠词与大小写（"Roof detail step"）一致。
- `It is optional` 的依据：配置器可以手填 kWp、不经过屋顶步，报告在请求没有 `planes` 时仍出（`report.py` 第 360–361 行）；这不是新承诺。
- `maps the roof surface and module placement` 取安装商页已通过的 `maps usable roof space, module placement around obstructions` 的两个成分；`maps` 同时覆盖 LoD2 官方建筑模型与手绘屋面两条入口（#480），不说 `draw`，因为不是只有手绘。
- 末句逐字是引擎披露句；`assumes` 保留，不改成 `drops` 或任何差额说法，不编造数字。
- 没有「不是…而是…」、没有三连排比、没有收束句、没有 `Get help…` / `Tell us…`。

本轮删过的英文候选：

1. `If you skip it, your yield estimate is less accurate.` — “less accurate” 是我们自己加的评价，报告只写按 35° 估算。删。
2. `The Roof detail step lets you draw your roof on a map.` — 只写手绘，漏掉 LoD2 入口；且配置器的屋顶步不只是画图。删。
3. `Skip the roof step and the report assumes 35° tilt facing south.` — 祈使句把动作派给客户（Hard Stop 9 Actor），且 `Skip` 是给读者的指令。删。

## 德文

独立撰写，Sie 体，不是上面英文的逐句对译。

- `Der Schritt Dachdetails nimmt die Dachfläche auf. Er ist optional und zeichnet die Lage der Module ein. Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).`

评审：

- 首句逐字取 #12 已定稿的德语卡片句，`Dachdetails` 与站上工具卡、安装商页同名。
- `Er ist optional` 与英文同据（手填 kWp 路径与无 `planes` 的报告分支）；德语用 `optional`，与 `.po` 里既有的 `Unternehmen (optional)` 同一词。
- `zeichnet die Lage der Module ein` 用 `einzeichnen`，是配置器画布语境的自然动词；不造 `Modulbelegung` 这类术语，也不写只有手绘的 `zeichnen Sie`。
- 末句逐字是引擎披露句；`Vorgabe des HTW-Rechners` 不改写、不省略。
- Sie 体；没有「nicht … sondern」、没有三连排比、没有 `Katalog` / `Artikel` / `Warenkorb`。

本轮删过的德文候选：

1. `Ohne den Dachschritt rechnet die Auslegung mit 35° nach Süden.` — 把 `Ertrag` 换成 `Auslegung`、把 `Vorgabe des HTW-Rechners` 省掉，等于改写了披露句。删，回到逐字。
2. `Der Schritt Dachdetails ist freiwillig.` — `freiwillig` 读作「自愿」，不是流程上的可选步骤；且 `.po` 与站上已用 `optional`。删。
3. `Sie können den Dachschritt überspringen.` — 给客户派任务（Hard Stop 9 Actor），且回答「跳过会怎样」时不需要让客户跳过。删。

## 核对清单

这一轮的判断写在每条后面。协调者的签收见文末。

- Hard Stop 1：通过这一轮的自查。没有 `proven`、`tier-1`、`leading`。
- Hard Stop 2：通过这一轮的自查。没有把证书、协议、RMA 堆成卖点。
- Hard Stop 3：通过这一轮的自查。没有「我们不是中间商」。
- Hard Stop 4：通过这一轮的自查。没有 `direct` / `official` / `guaranteed`。
- Hard Stop 5：通过这一轮的自查。没有编造的时效，也没有一个工作日。
- Hard Stop 6：通过这一轮的自查。没有 `Get help…`，没有 `Tell us` / `Send us`。可点的一步是 `open_configurator`；正文不号召。
- Hard Stop 7：这些句子是对话回答，不是邮件主题。公开面用词按 §3 核过：没有 catalogue、article、cart。
- Hard Stop 8：通过这一轮的自查。没有把接线或实验室验证写成卖点。
- Hard Stop 9：通过这一轮的自查。Actor 是 Linker 的步骤与报告，正文不给读者布置任务。英文 `maps` / `assumes` 的主语是步骤与产量；德文 `nimmt … auf` / `zeichnet … ein` 的主语是步骤，`nimmt der Ertrag … an` 的主语是产量。
- AGENTS.md §3：通过这一轮的自查。没有 catalogue、article、cart、Artikel、Katalog、Warenkorb。`Produkt` / `Modell` 未在这组句子里另造系列名。
- 句式：通过这一轮的自查。没有「不是…而是…」，没有三连排比，没有收束句。`35°` 的度号来自引擎句，不是散文里的符号装饰。
- 德语：通过这一轮的自查。Sie 体。首句与末句逐字取自已定稿的站点句与引擎句，中间句独立写成，不是英文的逐句对译。
- 数字：`35°` 与 `HTW Berlin calculator default` / `Vorgabe des HTW-Rechners` 只出现在逐字复用的引擎句里；回答没有其它数字。`optional`、`maps`、`zeichnet … ein` 不是数字断言。

## 协调者对抗评审（2026-10-21）

逐句复核：作用句逐字=#12 已定稿卡句（EN/DE）；末句逐字=引擎 limit.default_orientation（#479 C57 实测）；中句 optional 有手填 kWp 路径与无 planes 报告分支为据，非新承诺；maps module placement 取安装商页已通过措辞。与 template.py ROOF 实际字符串一致。Hard Stop 1–9 与 §3 复核通过；被删的三个候选（less accurate 评价、只写手绘、祈使 Skip）删得对。无改动，定稿。
