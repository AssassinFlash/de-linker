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
# 8) 汇总。aggregate 按稳定用例 id 只留时间戳最大的一条，
#    所以旧文件不会把总览撑出第二行。重跑前仍删掉该场景的 *.jsonl，
#    让目录和总览一致。保留 service-token.txt 与 _superseded/。
rm -f ~/de-linker-data/campaign-331/s1-topic-switch/*.jsonl \
      ~/de-linker-data/campaign-331/s2-anaphora/*.jsonl \
      ~/de-linker-data/campaign-331/s3-language-switch/*.jsonl \
      ~/de-linker-data/campaign-331/s4-repeat/*.jsonl \
      ~/de-linker-data/campaign-331/s5-handoff/*.jsonl \
      ~/de-linker-data/campaign-331/s6-reload/*.jsonl \
      ~/de-linker-data/campaign-331/s7-cross-device/*.jsonl \
      ~/de-linker-data/campaign-331/s8-concurrency/*.jsonl \
      ~/de-linker-data/campaign-331/s9-switching/*.jsonl
# 线上冒烟会再创建 linker_conversation，不在这次重跑里。
# 真要重跑时再单独删 production-smoke/production-*.jsonl，并接受新帖子。
node aggregate.mjs > ~/de-linker-data/campaign-331/overview.json
```

证据：`~/de-linker-data/campaign-331/<scenario>/*.jsonl`（逐轮 request/答案/meta/duration、最终 URL、选定响应头、check/verdict 行），原始线程回读在 `*-after.json`。`_superseded/` 是驱动修正前的旧跑，保留但不计入总览。case 头不再写入服务令牌；历史文件的擦除见文末「第二轮」。

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

- 浏览器用例的机械 pass/fail 不等于用例判定：`browser.spec.ts` 在 `finally` 写 `verdict` 行。断言抛错时这一行仍然落盘，判定为 defect。双标签页竞态不 expect 胜负，测试可以绿、JSONL 记 defect，整轮能跑完。以 JSONL 的 `verdict` 为准。
- 恢复后的线程只为最后一轮渲染投票按钮，因此"答案是否落地"以回答文本与 assistant 消息数为准（驱动已按此修正；修正前的旧跑在 `_superseded/`）。
- 中途 reload：首帧可能仍是欢迎面（mount 恢复是一次 fetch），不是数据丢失；等本轮在服务端落盘后再次 reload，问题与回答都在（s6 记录 `sawQ2Early: false`，settle 后 `q2Present: true`）。
- 直接服务电池会把上一轮回答的文本作为 assistant 消息回传（与壳的 `assistantMessage()` 一致）；卡片/文档块不随线程回传——这是壳的既有契约，不是本批发现。

## 第二轮（harness 修正，2026-10-19）

产品代码、模型路由、价格门、询盘发信都没有改。没有新增线上探针，也没有重跑模型电池。上一轮 37 例（30 通过 / 7 缺陷）仍以当时的 JSONL 为准；这一轮改的是驱动会不会把秘密写进证据、断言会不会空过。

### 令牌

case 头曾经整份写入 `targets`，里面有 Genie 服务令牌（`tools/local/src/linker_local/services.py` 的 `secrets.token_hex(32)`，64 位十六进制，请求头 `X-Linker-Service-Token`）。本轮把 `~/de-linker-data/campaign-331/` 里含令牌的 29 个 JSONL 就地改成 `[redacted]`，其中 7 个在 `_superseded/`。扫完之后，该目录除 `service-token.txt` 外没有 64 位十六进制串。`service-token.txt` 保留：驱动靠它认证，`scanDirectory` 跳过这个文件。

检索过的范围：本仓库 git 历史、PR #371 的正文与评论与评审、issue #331 的正文与评论。这些地方没有这枚令牌，也没有把 JSONL 挂到票或 PR 上。证据没有经这些通道离开这台机器。若另有拷贝被复制走，轮换 `LINKER_GENIE_SERVICE_TOKEN`。

之后 `evidence.mjs` 的 `record()` 在落盘前擦除字段名 token、secret、password、authorization、cookie、set-cookie、x-linker-service-token，以及任意 64 位十六进制串。擦完仍扫到令牌形状就拒绝写入。`node --test harness.test.mjs` 的扫描用例在残留时失败。

### 断言与阈值

S2：代词那一轮必须在回答文本或卡片上出现解析到的型号或 SKU。只出现 warranty 不再通过。`en-first-one` 仍允许回答里同时点名对比的另一台（ESA）；它要的是 H2 的型号或卡片，加上三相，并排除「first one is single」和「ESA … three-phase」。

S3：换语言后的配对回答要有 `text` 与 `cards`（document、ask 可以多出来）、有下一步、且没有 contact 块。下一步沿用 #330 的读法：问号，或块类型属于 cards、compare、action、document、parts、handoff、contact、ask（规格 13 目标 6，地图 #329 的「每条回答有下一步」）。容量追问（15 kWh）要有 `text` 与 `action`。EN/DE 孪生问句（「Welche Batterien passen zum SAJ H2-10K-T3?」与 “Which batteries work with the SAJ H2-10K-T3?”）比较块类型集合与卡片 id 集合。过滤只跑一侧时不写这条比较，避免缺一侧被记成通过。卡片集合在以后的模型跑里可能对不上；上一轮 D4 就是卡片集不稳定。对不上就记缺陷。

等待的出处在 `harness/timing.mjs`。180 s 是 `tests/e2e/lib/genie.ts` 的 `timeoutMs ?? 180_000`。70 s 是 `plugins/linker-tools/includes/Genie/Proxy.php` 的 `'timeout' => 60.0` 再加 10 s。8 s 是双击之后等第二条用户气泡：用户句在发送被接受时渲染（壳本地揭示上限 1.2 s，规格 13，业主 2026-10-18），这 8 s 盖住那次揭示。5 s 是竞态后的重读：mount 恢复是一次 GET（`plugins/linker-tools/src/genie/api/turn.ts` 的 `readThread`）。产品 id 用 `grounding.known.sajH2_10k_t3.id`，驱动里不写死帖子编号。

语言判断留在 S3：德语看出 umlaut 或 der/die/das/und/passen/Batterien/Wechselrichter；英语看功能词且没有德语标记。出处是 dossier §1.13 和 #329 的「EN/DE 同结构」。原先按「至少两个句式」计数的 `looksGerman` / `looksEnglish` 已删除，没有被调用。

### 驱动归并

SSE 解析在 `sse.mjs`，cookie jar 在 `cookies.mjs`，落盘、擦除、响应头选择在 `evidence.mjs`。`client.mjs`、`smoke-production.mjs`、`scenarios-proxy.mjs`、`browser.spec.ts` 共用它们。删掉了 `serializedOrMerged`、`.filter(... || true)`、`bodyHead = text.slice(0, 0)`。

### 出处

`grounding.json` 增加快照 `20261019-1409`（taken `2026-10-19T06:21:25+00:00`，loaded `2026-10-19T09:11:18+00:00`，与 `~/de-linker-local/c331/snapshot.json` 一致）和 `git_rev` `62b7616ef058bea7a246bc92ef40deb186954e8e`（写出这份 grounding 的提交，描述的是抓取当时的目录与代码）。再跑 `grounding.mjs` 会按当时的实例快照和当时的 HEAD 覆盖这四项。

每个驱动记录最终 URL 和选定响应头：content-type、cache-control、server、x-powered-by。`cf-ray` 只记 `present`。不记录 Cookie、Set-Cookie、服务令牌。

### 线上会话

`production-smoke/production-20261019104208.jsonl` 的四个探针各创建了一条线上 `linker_conversation`：P1 7458、P2 7459、P3 7460、P4 7461。请求是 `POST https://de-linker.com/wp-json/linker-ai/v1/genie/turn`，状态 200。只问句，没有联系卡、询盘卡、邮件。

地图 #329 的环境句：本地实例做破坏性/极端用例；线上只做真实端到端（公开 Genie 对话不发信；真实询盘每批最多 1 封到测试邮箱；不碰真实客户数据）。这四条是该句允许的只问句线上对话。决定：保留。删除它们是另一次线上写入，不在这次 harness 修正里做。本文件的线上冒烟驱动不再增加探针。
