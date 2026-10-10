# #15 FAQ 重生成盘点

来源：`docs/faq/questions.json`（`python3 tools/faq/export.py --wp 'just wp t6'`，106 已发布产品、272 条现有问题）+ 每产品 `docs/faq/<slug>.{json,md}`。

生成：DeepSeek `deepseek-v4-flash`（`~/.config/terravolt-builder/deepseek.json`）；检索：`DocumentIndex.search`，索引 `~/de-linker-data/index/builds/20261010T082155Z/index.sqlite`。评审为另一次无历史的 DeepSeek 调用。

| 口径 | 数 |
|---|---|
| 已发布产品 | 106 |
| 现有问题（EN，角度保留） | 272 |
| 通过并写入 `_linker_faqs` | **168** |
| 撤下（文档不支持或引用页对不上数字） | **85** |
| 打回（评审：答非所问 / AI 句式 / 超引文） | **19** |
| 无现成问题、未编造角度 | 3（EcoFlow HD-P3 5K0-S2 / 15K-G2 / 15K-G2F） |
| 至少 1 条通过的产品 | 91 |
| 写入后 FAQ 列表为空的产品 | 15 |

导入：`python3 tools/faq/import.py --wp 'just wp t6' --from docs/faq --write`。`linker_t6` 上 `_linker_faqs` 106 行，`JSON_LENGTH` 合计 168，空列表 15。

样例：通过 `docs/faq/saj-ats1-t63-a.md`；撤下（手册页不可读）`docs/faq/chint-dtsu666.md`；三条全撤 `docs/faq/saj-hs2-8k-t2-x.md`。
