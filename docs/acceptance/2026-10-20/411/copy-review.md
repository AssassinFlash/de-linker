# #411 失败后重新附上文件

协调人定稿（2026-10-20）。下面四句是定稿，不改字。

说明：says what happened and what to do; no blame; no promise; Sie-form.

## 单文件

- EN：`Attach %s again. It could not be kept for another try.`
- DE：`Bitte hängen Sie %s erneut an. Die Datei konnte für einen weiteren Versuch nicht gespeichert werden.`

## 多文件

- EN：`Attach these files again. They could not be kept for another try.`
- DE：`Bitte hängen Sie diese Dateien erneut an. Sie konnten für einen weiteren Versuch nicht gespeichert werden.`

Coordinator sign-off: approved (2026-10-20). Notes: says what happened and what to do; no blame; no promise; Sie-form.

定稿落在 `plugins/linker-tools/src/genie/shared/failure.ts` 的 `omittedFileNotice`，德语在 `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`。`%s` 只出现在单数，替换成那一个文件名。复数不列文件名。
