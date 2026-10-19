# #380 并发冲突文案 · 定稿

状态：定稿（协调方对抗评审，2026-10-19）。

## 409 `linker_genie_turn_conflict`

模型已经答完，写入时会话被另一轮改过，这一轮没有存进去。问句留在输入框，附件留着，顾客再发一次。

- EN：`The conversation changed while Genie was answering. Send your question again.`
- DE：`Während Genie geantwortet hat, ist in diesem Gespräch eine weitere Nachricht eingegangen. Stellen Sie Ihre Frage noch einmal.`

上游失败（502）仍用既有句 `Genie did not answer. Please try again.` / `Genie hat nicht geantwortet. Bitte versuchen Sie es erneut.`

## 对抗评审记录

- 词汇：无 catalogue/catalog/article/basket/Warenkorb/Artikel；产品名 Genie 正确，不连写 Linker Genie。
- 语气：陈述事实 + 一个动作；不承诺时限，不解释内部机制（锁/写入），不指责客户。
- 德语：Sie 体；"Gespräch" 与站内会话列表用词一致；独立撰写，非英文直译。
- 英德同义：EN 说"会话在 Genie 回答时被改过"，DE 说"期间有一条新消息进入"，指向同一事件；两语都要求重发问句。
- 动作：问句留在输入框、附件保留（壳已实现），文案只说"再发一次"，不说"已发送/已保存"。
- 结论：通过，可上线。
