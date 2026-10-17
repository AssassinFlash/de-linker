# #288 · 第 2 轮 LC 词条提取修正

依据：[Review, round 2](https://github.com/AssassinFlash/de-linker/pull/291#issuecomment-6239594631)。本轮只修翻译重建 blocker；邮件实现与模板 markup 沿用已接受结果。

## 来源与根因

`Clear search` 最初在 `4a23c63a` 的 `LibraryPage::config()` 中作为 PHP `__()` 词条进入 POT。`bc4ae4b7` 删除这个不再由 JS 使用的 config key；LC 的清除按钮仍保留 `aria-label="Clear search"`。`1f097828` 将 POT 引用从 PHP 改为 `content/livecanvas/faq_page.html:13`，该阶段的规格记录采用旧 POT 的 `make-pot --merge` 保留条目；仓库没有可重复的 LC 提取器。

上一轮去掉旧 POT 合并后，只扫 PHP/JS/build，把仍在 LC 中使用的词条标为 obsolete。PO 保留 msgstr 不代表 MO 保留条目；上一轮将 `Clear search` 判为可以 obsolete 的结论有误。本轮同时核验源使用、active 状态和编译后的 MO。

## 可重复命令

```sh
just i18n-commerce c288
just i18n-coverage
just i18n-validity
```

`justfile` 中的 `i18n-commerce` 配方依次：

1. 使用 c288 的 WP-CLI，从 PHP/模板/源 JS/build 提取全新 `code.pot`，无 `--merge`。
2. `tools/checks/i18n_sources.py` 读取 PO 中已有的消息字典（含 obsolete），在 LC 源码的文本、aria-label/title/placeholder/alt 和短代码标签中查找实际使用，生成带真实源码位置的全新 `fragments.pot`。LC 英德 twins 继续承载各自正文；没有新增或改写译文。
3. `msgcat --use-first --sort-by-file` 组合两个全新提取结果，随后 `msgmerge --no-fuzzy-matching` 更新 PO，`msgfmt --check` 编译 MO。

旧 POT 从不作为输入。命令已连续执行成功；两次均提取 29 个仍使用的 LC 目录词条，恢复其中 9 个 active 条目。

## TDD：现有公开门禁

边界是 `just i18n-coverage` 对仓库真实源码与发行目录的检查。先加门禁、运行当前坏目录，退出 **1**：不再只统计 untranslated，也拒绝 PHP gettext、JS/build gettext 和 LC 片段中仍使用的 obsolete 消息。报错包含真实源码位置，见 [round2-red.txt](round2-red.txt)。

该失败列出 `Clear search` 及另外八个有效 LC 词条。执行提取配方后，同一门禁退出 **0**，见 [round2-green.txt](round2-green.txt)。技术常量、注释和词条自己的 PO/POT 文件不作为活跃使用；gettext 调用识别包含构建产物的 `(0,x.__)(...)` 形式。

## 编译 MO 比较

以 rebased `origin/main = d27d1a3e` 为基线。计数与评审一致，包含 MO 的 header 条目；复数的内部 lookup keys 另列在 JSON 中。

| 项 | 结果 |
|---|---|
| 主线 MO | 782 条 |
| 第 2 轮修正前 | 777 条 |
| 修正后 MO | 786 条 |
| 从主线删除 | 仅下列 4 条退役审批文案 |
| 共享译文改动 | **0** |
| `Clear search` | **Suche leeren**，active 且已进入 MO |
| 新进入 MO | 8 条仍在 LC 中使用的既有 obsolete 译文 |
| PO msgid/msgstr 对 | **861 / 861** 完全不变（含 obsolete、复数与多行文本） |

允许移除的四条为：

- `Choose approve, restrict or reject.`
- `Last change %1$s by %2$s.`
- `A restriction or rejection needs a reason; the customer reads it in the email.`
- `Required for restrict and reject; the customer reads it in the email about the change.`

恢复进 MO 的另外八条为 `Applications`、`Breadcrumb`、`Check this model for the project`、`Description`、`Product filters`、`Product questions`、`Product sections`、`Technical data`；msgstr 均来自原 PO。完整结果见 [mo-comparison-round2.json](mo-comparison-round2.json)。

c288 的实际 WordPress `translate()` 在 `de_DE_formal` 下读出九条正确德语译文，随后还原 locale，见 [runtime-translations-round2.json](runtime-translations-round2.json)。本轮未改页面 markup/CSS；没有真实发信、部署或合并。

## 本地门禁与评审

最终执行结果在推送前写入本节。
