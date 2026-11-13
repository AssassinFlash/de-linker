# Genie 配对问答恢复：两个真实缺陷与生产读回

- **日期**：2026-11-14
- **生产运行时**：`serving_revision = 8d50d2cfba0a831dfa26039a012f88ce49bdee196821a16d015432bb9bb9da0a`
- **生产索引**：`index_version = 20261113T172753Z-024519000`，`job status = ready`
- **证据**：本目录 `readback-*.sse`（生产服务真实 SSE 应答，未经改写）

## 一、现象

英语与德语问「GoodWe GW125K-ETR 配哪些电池柜」，两个语言都只回一句：

```
Here are matching products from our range. Compatible models:
GW125K-ETR-G10, GW208.9-BAT-LCD-G10, GW261.2-BAT-LCD-G10.
```

119 / 126 字符，**零文档引用**。德语在数小时前还能给出 1,387 字符、3 份 PDF 的完整配对条件，说明这是回退。

## 二、排除过的假设（都不是原因）

| 假设 | 判定 | 依据 |
|---|---|---|
| 索引缺少配对数据 | **否** | 索引里存在 `compatibility_inverter` scope：`inv 3595 / bat 1958 / series ETR 80-125kW / model GW125K-ETR-G10` |
| 配对表缺 scope（`table_without_scope`） | **否** | 该 scope 的 chunk 内容同时证明逆变器与电池：`GW125K-ETR-G10 \| ETR 80-125kW` 与 `GW261.2-BAT-LCD-G10 \| ETR 80-125kW \| ●`，且在 FTS 中可检索 |
| `engineering-feed` 缺配对 | **否** | `pairs` 中 `3595+1958 → released`、`3595+1957 → released` |
| 型号-系列映射缺失 | **否** | `_axis_contains("GW125K-ETR-G10", "ETR 80-125kW") == True` |
| 页面上下文影响路由 | **否** | `home` / `product` / `solution` 三种 `page_context` 结果一致 |
| 语言通道本身失效 | **否** | 同期 SAJ 配对英语一次通过（`grounded=true`，755 字符，4 文档） |

## 三、缺陷一：兜底丢弃本回合已取得的配对证据

`services/genie/src/linker_genie/template.py`

模型草稿两次被 grounding 拒绝（`failures: ["Remove introductory text blocks. Copy the
complete matching warranty_answers value …"]`），随后 `fallback()` 走到末尾分支，输出
「Here are matching products from our range」。

该分支**丢弃了本回合 `search-products` 返回的 `compat.condition.PARTNER.N` 与
`compat.document.PARTNER.N`**——而 `_not_released_fallback()` 已经确立了正确做法：从工具事实
装配答案，服务不自行造句。

**修复**：新增 `_released_pair_fallback()`，在一个已发布配对集合存在时，用该集合自己的
条件与文档装配答案；无条件事实则返回 `None`，保持原有行为不变。

## 四、缺陷二：`--from-corpus` 把索引绑到已不存在的运行时

`services/genie/index/build.py`

`embed_corpus()` 从源 corpus 复制 `serving_revision`，且**没有向 manifest 写入该字段**。
一旦服务代码变化，重建出的索引就绑在一个不存在的运行时上，此后每次
`search-knowledge` 都失败：

```
linker/search-knowledge: document index unavailable:
  managed knowledge index needs matching serving rules
```

客户只看到 `I could not answer this time`。**修复**：新构建计算当前运行时
`serving_revision()`，同时写入 corpus meta 与 manifest。

## 五、生产读回（修复后）

| 问题 | 修复前 | 修复后 |
| --- | --- | --- |
| GoodWe 配对 EN | 119 字符 / 0 文档 | **1222 字符 / 3 文档** |
| GoodWe 配对 DE | 126 字符 / 0 文档 | **1387 字符 / 3 文档** |
| SAJ 配对 EN | — | 755 字符 / 4 文档，`grounded=true` |
| SAJ 配对 DE | 727 字符 / 4 文档 | 470–965 字符 / 1–4 文档，`grounded=true`（连测 3 次，模型文档选择有波动，均达标） |
| MPPT 数量 EN | 124 字符 / 1 文档 | 88 字符 / 1 文档，`grounded=true` |
| GoodWe 效率 DE | — | 740 字符 / 3 文档，`grounded=true` |
| Pylontech 容量 / GW25K 配对 / 产品对比 / 价格 | — | 全部 `grounded=true`，169–526 字符 |

英语答案现在包含真实条件：手册 pp. 24–25（单机系统表）、pp. 26–27（并联系统，
需 SEC3000C 主程序 V7.8.19 或更高）、以及兼容性总览未列该电池因此不构成完整保修的说明。

## 六、部署过程中被证实并修复的三个环境缺陷

1. **直接替换 `template.py` 会打断生产**：`serving_revision` 变化后与 WordPress 的
   `expected_serving_revision` 不匹配，所有知识查询失败。已回滚并用配对发布修复。教训：
   运行时源码只能经 `paired_release.py` / `publication_worker.py` 发布。
2. **`GENIE_WP_URL` 在 Mac 构建机上必须显式导出**：`publication.current()` 回退到
   `http://127.0.0.1`，构建在一小时 chunk 之后死于
   `PublicationUnavailable: Woo publication permission unavailable`。已写入
   `services/genie/ops/PUBLICATION.md`。
3. **launchd 发布源是独立副本**（`de-linker-ops/knowledge-publication/source`），
   与主树无关。未同步时发布器会用旧编译器构建。已同步并验证 `.py` 全等、
   `serving_revision` 与 VPS 一致。

## 七、测试

- `services/genie`：`3000 passed, 1 skipped, 6 xfailed`
- 新增 `test_degradation.py`：已发布配对保留条件、未发布配对保持原形、无条件不造句子
- 新增 `test_build.py`：`--from-corpus` 重新计算 `serving_revision`
- CI：`ef0bc92a8` → `completed / success`
