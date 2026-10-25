# 发布状态与方案下一步：英德文案对抗

依据：[统一发布规则](https://github.com/AssassinFlash/de-linker/issues/609)、[选型实现](https://github.com/AssassinFlash/de-linker/issues/617)。范围仅为工具应用已有动作的失败状态，保留现有布局。新增维度是“这次动作能否继续，以及输入/清单结果是否已确认”，不描述厂商、库存或项目收益。

采用 linker-copywriting Hard Stops、本地百科词汇及 humanizer。产品、方案、Lösungsentwurf 沿项目与既有工具用语；EN 先写，DE 按德语状态提示独立成句。

## 初稿与反对意见

- 原通用 503 说辐照服务没有响应。对 Woo 当前权威无法读取的情况，原因错误。失败也不能被推断为产品已下架。
- “Products have changed / withdrawn”无法概括所有需重算的情景：结果过期、记录缺失也会失效；nonce、操作冲突、验证码和配额错误则不属于产品变化。
- 原“有些产品没有确认”源于逐项加入。现在服务端整套写入，网络中断后不能声称部分成功或清单没有变化。
- 主会话复核接受下面三条完整说明的准确性与术语，要求未知结果保留不确定性、不以“未加入”替代。
- 完整说明在每张卡重复会占用手机宽度。卡片压缩为两个同义短标签，动作区与 PDF/保存状态保留完整说明。

## 定稿

| 状态 | English | Deutsch |
| --- | --- | --- |
| 需重算 | This solution needs a new calculation before the next step. | Für den nächsten Schritt muss diese Lösung neu berechnet werden. |
| 当前权威不可核验 | The current product data could not be checked. Your entries are still here. | Die aktuellen Produktdaten konnten nicht geprüft werden. Ihre Angaben bleiben erhalten. |
| 整套加入未确认 | The addition could not be confirmed. The solution draft may already contain these products. | Das Hinzufügen konnte nicht bestätigt werden. Die Produkte können bereits im Lösungsentwurf stehen. |
| 卡片未确认 | Addition not confirmed. | Hinzufügen nicht bestätigt. |
| 卡片需重算 | New calculation required. | Neue Berechnung erforderlich. |
| 保存请求结果未确认（复用既有文案） | The request status could not be confirmed. Please check before sending it again. | Der Status Ihrer Anfrage konnte nicht bestätigt werden. Bitte prüfen Sie ihn vor einem erneuten Versand. |

仅明确的发布/选型失效码进入重算状态；显式旧逆变器或电池的失效 422 也适用，其他 409 不冒充产品变化。发布权威无法核验时显示产品数据提示，真实辐照/LoD2 故障保留原提示。保存、Ask Genie、新 PDF 与整套加入失败均保留当前屏幕，不自动换产品或重算，不编造清单写入结果。

补充复核：保存的 POST 可能已在服务端成功，但响应丢失、5xx 或成功回执无法解析时，原先“无法保存，请重试”超出了已知事实。Save 与 Ask Genie 的保存步骤改用上表既有“请求状态未确认”说明，不自动重发、不宣称没有保存，也不打开未经确认的账户记录。该句已在正式德语 PO 的 `includes/Protection/Replies.php` 来源上存在；配置器增加原生 bundle reference。服务端明确拒绝保留原失败说明；保存 POST 之前的 PDF 生成失败仍明确没有发出保存动作，继续走既有失败状态。本增量仅纠正旧入口的既有状态提示，不建立新的保存/恢复架构。

参考组件证据的补充复核：参考资料未准备或无法取得当前许可属于既有产品数据 503；旧回执未包含参考证明、在途证据撤回或版本变动属于需重算 409。继续使用上表已审定的 EN/DE 提示，保留输入和结果，不把参考资料问题说成辐照故障或直接断言产品已下架。新增 `reason=reference_evidence_unavailable` 仅供机器诊断；`api/engine.ts` 只按 code/field 选择现有状态，不将服务端英文 message 直接呈给客户。此次不新增客户文案、品牌提示或自动重试。

## Pre-delivery

- [x] Encyclopedia loaded (non-PDP): one new dimension; category words attested.
- [x] Hard Stops 1–9 hold on every visible line.
- [x] Actor: no second-person imperative assigning extra work.
- [x] Future: no invented customer trajectory or “We know you…” claim.
- [x] Weight: no small slice written as the whole offer.
- [x] Duration: no unspecified ongoing service or duration claim.
- [x] No slogan formulas, false contrast, rhetorical triplets or inflated promises.
- [x] No manufacturer brand on this surface.
- [x] Quotes: no fabricated quoted speech or testimonial.
- [x] Humanizer: no invented facts, boilerplate reassurance, process boasting or jargon; uncertainty follows an actually unconfirmed write.
- [x] German follows the formal register and Lösungsentwurf term.

Locale PO/JSON/MO 由主会话统一写入、原生生成并做覆盖检查；本文案记录不代替 EN/DE 390/1440 状态截图与完整呈现验收。
