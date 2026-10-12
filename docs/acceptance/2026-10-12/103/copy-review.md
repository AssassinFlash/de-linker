# #103 文案对抗评审记录（Genie 兜底的降级声明）

规则（AGENTS.md）：客户可见文案一律初稿 → 评审意见 → 定稿；EN 先行，DE 独立撰写非翻译；
基准 = linker-copywriting Hard Stops + 线上既有措辞与 .po 术语；Sie 体；禁 AI 句式；
不发明承诺。本条是**功能状态文案**（工具在轮次失败时的状态句，EN+DE 同步交付），
落点 `services/genie/src/linker_genie/template.py::DEGRADED`——兜底模板是它的唯一写者。

触发场景：一轮的两次尝试都没有可引用的工具结果（ability 全部不可达、或模型两轮
都没有产出合格结构）。原句 "Please contact our team." / "Bitte wenden Sie sich an
unser Team." 把失败读成了普通的转人工，降级被藏住了；本轮起必须明确声明。

## 1. 定稿与评审

| 语言 | 初稿 | 评审意见 | 定稿 |
|---|---|---|---|
| EN | `Sorry, I could not load the product data just now. Please try again soon, or write to our team: sales@de-linker.com.` | ① "could not load the product data" 在模型自身失败（结构两轮不合格、数据其实加载成功）时不成立，撒了失败原因——改为不指名原因的 "could not answer this time"，把失败限定在本轮，对两种成因都诚实；② 邮箱地址会让 Python 模板硬编码团队邮箱——该事实的唯一实现在 WordPress 侧 handoff-team（ability 返回句子与 mailto），模板不应复制第二份，删；③ "Sorry" 是填充语（Hard Stops），删；④ "try again soon" 隐含系统很快恢复——这是没把握的承诺，改 "in a moment"（重试指引，非时限承诺）。 | `I could not answer this time. Please try again in a moment, or write to our team.` |
| DE | `Ich konnte die Produktdaten gerade nicht laden. Bitte versuchen Sie es gleich noch einmal – oder schreiben Sie unserem Team: sales@de-linker.com.` | 同 EN ①②③④：原因不指名（"Ihre Frage diesmal nicht beantworten"）；地址删（同源理由）；破折号改逗号（两个并列祈使句用逗号更平实，且避免句式堆叠感）；"unserem Team schreiben" 换成既有的 "sich an unser Team wenden"（与原兜底句同 register，站点既有用法）。 | `Ich konnte Ihre Frage diesmal nicht beantworten. Bitte versuchen Sie es gleich noch einmal, oder wenden Sie sich an unser Team.` |

## 2. 对照 Hard Stops 的复核

- 不发明承诺：无时限、无"很快恢复"；"in a moment"/"gleich" 修饰的是客户的重试动作。
- 不暴露技术细节：不提 Redis、缓存、服务器、错误码。
- Sie 体：`Ihre Frage` / `versuchen Sie` / `wenden Sie sich`。
- 无 AI 句式：两个选项用一次 "or" 并列，无三连排比、无"不是…而是…"。
- 与既有措辞同 register：后半句沿用原兜底句的动词（contact our team /
  sich an unser Team wenden），客户看到的语言风格不变。
- 一处一实现：团队邮箱不出现在本串；句子只指向"团队"，地址由 handoff-team
  的句子（R8/R14 路径）或站内联系页承载。

## 3. 前端承载

`Handoff` 组件把 summary 渲染为普通段落（`linker-genie-app__handoff`），无新串、
无新组件；EN/DE 随轮次 locale 选择，无 .po 新键（服务端串，不走 WordPress i18n）。

## 未决（事实问题）

无。句子不断言故障原因与恢复时间，不需要业主裁定。
