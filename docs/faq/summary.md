# #15 FAQ 重生成盘点

来源：`docs/faq/questions.json`（`python3 tools/faq/export.py --wp 'just wp t6'`，106 已发布产品、272 条现有问题）+ 每产品 `docs/faq/<slug>.{json,md}`。

生成：DeepSeek `deepseek-v4-flash`（`~/.config/terravolt-builder/deepseek.json`）；检索：`DocumentIndex.search`，索引 `~/de-linker-data/index/builds/20261010T082155Z/index.sqlite`。评审为另一次无历史的 DeepSeek 调用，评审输入经 `review_projection` 只带问题/答案/引文（PR #58 评审 S4）。

## 评审修复轮后（2026-10-10，PR #58 必改 ①② 落地）

恢复轮见 `docs/faq/recovery-2026-10-10.md`；门缺陷复现与修法见 `docs/faq/gate-defects-2026-10-10.md`。

| 口径 | 数 |
|---|---|
| 已发布产品 | 106 |
| 现有问题（EN，角度保留） | 272 |
| 通过并写入 `_linker_faqs` | **221** |
| 撤下（每条带文档依据） | **51** |
| 打回 | **0**（19 条全部终态：10 过 / 9 撤） |
| 无现成问题、未编造角度 | 3（EcoFlow HD-P3 5K0-S2 / 15K-G2 / 15K-G2F） |
| 至少 1 条通过的产品 | 100 |
| 写入后 FAQ 列表为空的产品 | 6 |

引文语言（S7 裁定：EN FAQ 只引 EN 文档；无 EN 版才引 DE 版、答案语言保持 EN）：pass 引文含 EN 手册/数据手册、
DE-EN 与多语合订手册（含 EN）；纯 DE 引文保留两类——SAJ HS2-AS2 手册（EN 孪生 0 chunk 未解析）、
EcoFlow 单相安装指南（无 EN 版），共 22 条。

样例：通过 `docs/faq/saj-ats1-t63-a.md`；撤下（手册页不可读）`docs/faq/chint-dtsu666.md`；IOT dongle 六产品统一口径见 `docs/faq/ecoflow-ocean-2-hd-p1-3k-s2-3-kw-single-phase-hybrid.md`。

导入：`python3 tools/faq/import.py --wp 'just wp t6' --from docs/faq --write`（恢复轮后需重跑；数字以本轮导入读回为准）。
