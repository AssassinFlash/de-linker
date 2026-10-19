# #331 对抗测试矩阵 · 对话状态批 — 方法与证据

- 票：#331（地图 #329 "Genie 完美化"）。性质：**只测不修**；产品代码零改动。
- 日期：2026-10-19（本地电池 + 线上冒烟）。
- 结果（逐条、最小复现、分层归因、复刻/须自行设计标注）：见票上的中文评论。本文件只写怎么跑、跑在哪、证据在哪。

## 环境

- 实例 `c331`：WordPress `http://127.0.0.1:9165`，engine `:9166`，Genie `:9167`。
- 数据：线上快照 `20261019-1409`（`just pull load c331 latest`，212 商品、2756 附件、search-replace 6,439 处、`ok: true`）。
- **偏离说明**：`just pull load c331 --live-code` 被工具自身拒绝（`linker-pull`：检出插件的实例不能用 `--live-code`，线上代码会顶掉检出）。本实例因此是"线上数据库 + 线上主题/uploads/许可插件 + 本检出插件"——正是要测的 Genie 代码；线上快照的强制项（主题、uploads、内容）全部满足。裸 WordPress 未参与。
- Genie 文档索引：`~/de-linker-data/index/builds/20261018T173840Z/index.sqlite`（`just serve` 选最新）。
- 模型通道未动：对话 deepseek-flash（官方），Jev 经 OpenRouter；本电池只调服务与壳，无任何路由改动。
- 测试邮件纪律：本地 `~/de-linker-local/c331/mail/` **全程为空**（没有任何联系卡/询盘卡被提交）；线上冒烟只发问句，未提交任何卡。

## 四套驱动

| 文件 | 驱动对象 | 覆盖 |
|---|---|---|
| `harness/scenarios-direct.mjs` | Genie 服务 `POST /turn`（与 `tests/e2e/lib/genie.ts` 同形：整条线程重发） | S1 话题切换、S2 指代、S3 中途换语言、S4 重复问题、S5 转人工规则 |
| `harness/scenarios-proxy.mjs` | WordPress 代理 `linker-ai/v1/genie/{turn,conversation}`（cookie jar，同 dock 的 `credentials: same-origin`） | S8 同一会话并发轮次（EN/DE） |
| `harness/browser.spec.ts` | 真浏览器（Playwright，复用 e2e 的 DOM 词汇） | S6 reload/重开/dock 重开、S7 跨设备、S8 双标签页与双击、S9 会话列表切换 |
| `harness/smoke-production.mjs` | `https://de-linker.com` 的同一代理，仅问句 | 4 个线上冒烟用例（P1 话题切换、P2 指代、P3 语言、P4 持久化） |

判定口径取地图：同结构 EN/DE、无编造数字、每条回答有下一步、无上下文串味；产品集合来自实例 `linker/v1/engineering-feed`（`harness/grounding.json` 由 `grounding.mjs` 生成）。转人工规则取 `docs/specs/13-genie.md` "转人工" 表（同一问题第三轮一次、不连续两轮、asked 每次提供）。

## 怎么重跑

```bash
# 1) 实例
just up c331 && just pull load c331 latest && just serve c331
# 2) 服务令牌（只在证据目录，不入仓库）
just wp c331 config get LINKER_GENIE_SERVICE_TOKEN --type=constant | tail -1 \
  > ~/de-linker-data/campaign-331/service-token.txt
# 3) 产品集合
cd docs/research/2026-10-20-campaign-331/harness
node grounding.mjs http://127.0.0.1:9165 grounding.json
# 4) 直接服务电池（S1–S5）
node scenarios-direct.mjs            # 可带前缀过滤，如 node scenarios-direct.mjs s1
# 5) 代理并发（S8，EN/DE）
node scenarios-proxy.mjs
# 6) 浏览器电池（S6/S7/S8/S9）：借用 e2e 已安装的 Playwright
ln -s "$PWD/../../../../tests/e2e/node_modules" node_modules
LINKER_E2E_INSTANCE=c331 ./node_modules/.bin/playwright test --config playwright.config.ts
rm node_modules                       # 符号链接不提交
# 7) 线上冒烟（只问句；每个 probe 记录最终 URL 与响应头）
node smoke-production.mjs
# 8) 汇总
node aggregate.mjs > ~/de-linker-data/campaign-331/overview.json
```

证据：`~/de-linker-data/campaign-331/<scenario>/*.jsonl`（逐轮 request/答案/meta/duration + check/verdict 行），原始线程回读在 `*-after.json`。`_superseded/` 是驱动修正前的旧跑，保留但不计入总览。

## 结果索引（37 用例：30 通过 / 7 缺陷，4 个缺陷类）

| 场景 | 用例 | 通过 | 缺陷 |
|---|---|---|---|
| s1 话题切换/上下文串味 | 5 | 5 | 0 |
| s2 指代 | 5 | 5 | 0 |
| s3 中途换语言 | 2 | 1 | 1 |
| s4 重复问题 | 2 | 1 | 1 |
| s5 三轮转人工 | 6 | 5 | 1 |
| s6 reload/重开 | 4 | 4 | 0 |
| s7 跨设备 | 2 | 2 | 0 |
| s8 同一会话并发轮次 | 4 | 1 | 3 |
| s9 会话列表切换 | 3 | 3 | 0 |
| 线上冒烟 | 4 | 3 | 1 |

缺陷类：D1 并发写丢失（3 例：EN/DE 代理并发 + 浏览器双标签页）、D2 德语页内英语问题仍德语作答（2 例：本地 + 线上复现）、D3 重复提议被填充词打断（1 例）、D4 同问首轮卡片集不稳定（1 例）。

## 判读注意

- 浏览器用例的机械 pass/fail 不等于用例判定：`browser.spec.ts` 在 JSONL 写 `verdict` 行（如双标签页竞态记 defect 但测试本身不 assert，便于整轮跑完收集证据）。以 JSONL 的 `verdict` 为准。
- 恢复后的线程只为最后一轮渲染投票按钮，因此"答案是否落地"以回答文本与 assistant 消息数为准（驱动已按此修正；修正前的旧跑在 `_superseded/`）。
- 中途 reload：首帧可能仍是欢迎面（mount 恢复是一次 fetch），不是数据丢失；等本轮在服务端落盘后再次 reload，问题与回答都在（s6 记录 `sawQ2Early: false`，settle 后 `q2Present: true`）。
- 直接服务电池会把上一轮回答的文本作为 assistant 消息回传（与壳的 `assistantMessage()` 一致）；卡片/文档块不随线程回传——这是壳的既有契约，不是本批发现。
