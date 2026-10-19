# #380 并发冲突文案 · 初稿

状态：初稿 / 未评审。本文件只记下待审的顾客文案，不是定稿。

## 409 `linker_genie_turn_conflict`

模型已经答完，写入时会话被另一轮改过，这一轮没有存进去。问句留在输入框，附件留着，顾客再发一次。

- EN 初稿：`The conversation changed while Genie was answering. Send your question again.`
- DE 初稿：`Während Genie geantwortet hat, ist in diesem Gespräch eine weitere Nachricht eingegangen. Stellen Sie Ihre Frage noch einmal.`

上游失败（502）仍用既有句 `Genie did not answer. Please try again.` / `Genie hat nicht geantwortet. Bitte versuchen Sie es erneut.`

评审：未进行。
