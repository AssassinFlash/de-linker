# #257 文档检索的三种状态：实测记录（2026-10-17，本机，索引 20261016T072222Z）

脚本放在会话草稿目录，只调 `KnowledgeSearch` 与 `cycle.run`，用的是真实索引与真实端点；错误密钥用的是一个明显无效的占位值，没有打印任何真实密钥。

## 1. 正常：向量检索，gemini-embedding-2 经 OpenRouter

```
case=ok ranking=vector encoder=google/gemini-embedding-2
INFO linker_genie.knowledge: document search ranking=vector encoder=google/gemini-embedding-2 index=20261016T072222Z hits=16
hits 16 first 770ccafa080c-p37-63a0f610
```

评测集每一轮的工具调用记录（`eval/run-*.json` 的 `tool_calls`）都带 `ranking: vector`、`encoder: google/gemini-embedding-2`、`index_version: 20261016T072222Z`。线上上线后，同样的字段会写进 VPS 的 `turns.sqlite`。

## 2. 配置了编码器，但编码失败：报错，不退回关键词

错误密钥（OpenRouter 返回 401，4xx 不重试）：

```
case=badkey ranking=vector encoder=google/gemini-embedding-2
ERROR linker_genie.knowledge: document search failed: google/gemini-embedding-2: HTTP 401 on attempt 1 of 2
raised EmbeddingError google/gemini-embedding-2: HTTP 401 on attempt 1 of 2
turn fallback True failures ['google/gemini-embedding-2: HTTP 401 on attempt 1 of 2']
turn text [{'type': 'handoff', 'summary': 'I could not answer this time. Please try again in a moment, or write to our team.'}]
```

（输出是在当前代码上复跑的。）这一轮落到既有的降级句，失败原文进了这一轮的 `failures`，也就进了轮次日志。整个过程没有出现关键词检索。

端点不可达（`OPENROUTER_BASE_URL` 指向一个不可路由的地址）：每次尝试 10 s，共 2 次，中间隔 0.5 s，然后报错：

```
ERROR linker_genie.knowledge: document search failed: google/gemini-embedding-2: URLError after 2 attempts: <urlopen error timed out>
raised EmbeddingError after 20.5s: google/gemini-embedding-2: URLError after 2 attempts: <urlopen error timed out>
```

超时的取值依据是实测的编码耗时：VPS 中位 0.46 s、最大 0.83 s；本机中位 3.8 s、最大 5.35 s；各 12 次，见 `embedding.py` 的来源注释。最初定的 5 s × 3 在本机评测里超时过一次（第 8 题），因此改成了 10 s × 2。

## 3. 主机上没有查询编码器：BM25，日志写明

不设密钥，HOME 指向一个空目录：

```
case=nokey ranking=keywords encoder=None
WARNING linker_genie.retrieval: document search by BM25: no query encoder for gemini-embedding-2 on this host (index 20261016T072222Z)
INFO linker_genie.knowledge: document search ranking=keywords encoder=None index=20261016T072222Z hits=16
```

## 单元测试

`tests/test_embedding.py` 覆盖了 401/400/404 立即失败、429/502/503 与连接错误按次数重试后失败、坏响应立即失败。`tests/test_retrieval.py` 覆盖了编码器失败时抛错而不排关键词、无编码器时用 BM25 并写日志。`tests/test_knowledge.py` 覆盖了失败要记日志并上抛，以及索引读不了时抛 `KnowledgeUnavailable`。
