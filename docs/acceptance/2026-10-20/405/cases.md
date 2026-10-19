# #405 页面缓存回归（登记给 #339）

四条要一台本地实例，不进 `just test`。`just up <name>` 之后：

```bash
just page-cache-chain <name>
```

实例需要 Polylang 的 en 与 de（`just wp <name> linker-i18n setup --user=local-admin`）。配方会先跑这句。CI 的 mu-smoke 任务在邮件集成之后跑同一配方，用的是当次 `just up smoke` 的空实例。

夹具：`services/genie/tests/fixtures/405/page-cache.json`。`services/genie/tests/test_page_cache_405.py` 只核对夹具、本文件和集成测试还在，不启动 WordPress。`just test` 会收集它。

链是 `wp_update_post` → `wp_after_insert_post` → `get_permalink` → `wp_remote_post` → 门 → `PageReader.invalidate` → 下一次读页。读和失效打在同一个 Genie 进程上（`services/genie/tests/page_cache_probe.py`，测试才挂上的读路由，不随服务发布）。Genie 不重启。

| id | 页面 | 通过 |
|---|---|---|
| `405-product-en` | 英文商品 | 下一次读到新标题和新句子 |
| `405-product-de` | 德语商品孪生 | 同上，路径含 `/de/` |
| `405-blog-en` | 英文博文 | 下一次读到新标题和新句子 |
| `405-blog-de` | 德语博文孪生 | 同上，路径含 `/de/` |

同一次保存还会点博客首页、博文分类和标签、商城、商品分类（单元测试 `PageCacheTest`）。超过 `schema.CACHE_SIZE` 的路径分成两次 POST，也在那个测试里。`draft:` 命名空间在 `services/genie/tests/test_page.py`。筛选、搜索、分页的列表不在失效里，规格 13 写明它们仍等 10 分钟。

不放进 `services/genie/eval/regression/339-product-words.jsonl`。那份文件是产品词。
