# 文案对抗评审记录（未登录询盘状态的登录句，PR #135）

规则（AGENTS.md）：客户可见文案一律初稿 → 评审意见 → 定稿；EN 先行，DE 独立撰写非翻译；
基准 = linker-copywriting Hard Stops + 线上既有措辞与 .po 术语；Sie 体；禁 AI 句式；
不发明承诺。本条是**功能状态文案**（未登录问询盘进度时的状态句，EN+DE 同步交付）。

落点（四处必须逐字节相同，grounding 只接受 `LOGIN_REQUIRED` 的原文）：

- `services/genie/src/linker_genie/template.py::LOGIN_REQUIRED`（唯一写者）
- `services/genie/prompts/en/system.md`、`prompts/de/system.md`（模型被要求原句照抄）
- `services/genie/src/linker_genie/agent.py` 每轮提醒（同一句）

触发场景：未登录问「Wo steht meine Proforma?」/「Where does my Proforma stand?」。
`inquiry-status` 回 401，记成 `inquiry.login_required`。协议 R7 未登录半边是「要求登录」，
不是团队邮箱句。本句在两条路径上出现：模型照抄，或 grounding 拒答后由兜底模板写出。

## 1. 定稿与评审

| 语言 | 初稿（PR #135 已合入代码、未经本记录） | 评审意见 | 定稿 |
|---|---|---|---|
| EN | `Please log in to see where your Proforma stands.` | ① 第二人称祈使把登录动作派给读者（Hard Stop 9 Actor）。登录是进账户的必要动作，站点既有句也用 `Please log in`，故保留祈使，不改成「Linker 替你登录」这种假动作；② 「see where your Proforma stands」把询盘四状态说成位置/进度条，协议 R7 的登录半边只要求登录，不承诺阶段条长什么样；③ 与站点既有句不对齐：`linker-commerce` `Terms.php` 已有 `Please log in to your account to view this inquiry.`（`.po` 2319）。定稿逐字节采用该句，不另造、不改动词。 | `Please log in to your account to view this inquiry.` |
| DE | `Bitte melden Sie sich an, um zu sehen, wo Ihre Proforma steht.` | ① 不是独立德语句：`um zu sehen, wo … steht` 是 EN「to see where … stands」的逐词翻译；② 「steht」把状态说成站位，和询盘四状态（eingegangen / ausgestellt / abgeschlossen / storniert）不是同一套说法；③ 站点既有 DE 是 `Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.`（`.po` 2319–2320），Sie 体、`Anfrage` 是询盘的既有词、`anzeigen` 只承诺显示、不承诺进度形态。定稿采用该句，不另译 EN。 | `Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.` |

EN 定稿与 `Terms.php` / `.po` msgid 逐字节相同。DE 定稿与同一条 msgstr 逐字节相同，不是 EN 的翻译：`anzeigen` 是账户页既有动词，不另造 `sehen, wo … steht`。

## 2. 对照 Hard Stops 的复核

- 不发明承诺：不说阶段条、不说回复时限、不说「您的 Proforma 在某一步」。
- 不暴露技术细节：不提 401、会话、cookie。
- Sie 体：`melden Sie sich` / `Ihrem Konto` / `diese Anfrage`。
- 无 AI 句式：一句祈使，无三连、无「不是…而是…」。
- 与既有措辞同 register：`Anmelden` / `Anfrage` / `Konto` 与账户页 `.po` 相同；不新造 `einloggen`。
- Actor：祈使是登录门本身，与 `Please log in to your account to view this inquiry.` 同一形状；没有给读者布置「把记录发给我们」之类的作业。
- 一处一实现：客户看到的句子以 `LOGIN_REQUIRED` 为准；提示词与提醒引用同一句，不另写变体。

## 3. 前端承载

无新组件、无新 .po 键。句子由服务端文本块下发，Genie 按普通文本渲染。EN/DE 随轮次 locale 选择。

## 未决（事实问题）

无。句子不断言询盘处于哪一状态、也不断言回复时间。
