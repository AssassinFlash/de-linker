# 自动知识联动验收记录

状态：实现及本地回归已验证；最终评审、当前 recipe 全库解析、实际向量/模型路径及生产部署读回仍在进行。本文件不将源码、ready 数量或本地成功表述为线上完成。

工作树：`codex/615-knowledge-followthrough`，基点 `ad20bad5d00d339f9392624913c7e08bf5584b98`。沿用[现有 Genie 与知识库任务](https://github.com/AssassinFlash/de-linker/issues/615)，未新开后续票。唯一实例 `knowledge615` 装入 2026-10-24 10:00 UTC 线上快照，实际本地地址 `http://127.0.0.1:8888`；172 条已发布语言产品记录、2756 媒体、0 缺失附件，许可证已应用。它与其他任务的数据库、端口和源码隔离。

## 已执行

| 检查 | 结果 |
| --- | --- |
| Genie 全套 pytest | 2377 passed、1 skipped、195 deselected、6 xfailed；87.35 秒 |
| Genie 全目录 Ruff / format | 通过；173 文件格式检查 |
| Genie `mypy .` | 212 个源码文件通过 |
| 原始 H2/HS2/HS3 适用性回归 | 33 项通过；涵盖全部 15 型号正确列、物理表头、单位水合、EN/DE 原生检索及撤权 |
| 构建/embedding/SQLite/tokenizer 集成 | 11 项通过；投影先于 embedding，SHA/recipe/epoch 保留，处理中源码改变拒绝 |
| 真实目录原子发布及 activation fence | 15 项通过；旧任务晚到、同 epoch 冲突、中断恢复、受管恢复及仅 stdin 传密钥 |
| 当前快照原生 WordPress 准备测试 | 6 项 / 94 断言通过；4 分 24.520 秒，峰值 158 MB |
| 生命周期 PHP 单元及静态 | 16 项 / 101 断言；WPCS 与 PHPStan level8 通过 |

失败缓存重试与原准备状态均有针对原实现的真实 RED 记录；新实现证明同 SHA 下次重新执行转换、成功后再复用完整缓存。测试没有实发邮件，也没有改变原生产产品和资料。

## 真实全库第一轮

从既有完整 Docling 原始缓存读取当前 native Woo source，native 识别只返回所提供原文中实际出现的型号状态，前后 source 相同。未调用模型或 embedding API。142 PDF、10906 原始片段均读取，0 失败；生成 2328 个每型号独立片段、3162 个已证明片段，85/85 产品具有实际可读依据。

该预检使用无向量 SQLite。15 型号英文问题均有命中；五个 HS3 的德语关键词对英文资料无命中，这不是已通过跨语言向量/模型验收。完整的新 parser recipe 正在对同一批原 PDF 重做解析；最终将以匹配 recipe 的正式向量索引及真实 EN/DE 回合验收。

319 条 `no_proven_passage` 是资料关联级诊断，未被改成 ready；成功物化与每个关联都有技术答案分开。已识别的歧义包括 H2 表格底部逻辑行错位，以及 HS3 原表星号对区域型号限定不清。原件和所有已有诊断保留；工具不得填入无法对应的参数。

私人运行证据根位于 `/Users/chesterjohn/de-linker-data/ecoflow-withdrawal-20261023/knowledge-followthrough-615/`；完整原文、索引、解析缓存及恢复资料不进仓库。任务资源表记录唯一实例、快照、处理缓存的用途、负责人和完成后的回收条件。
