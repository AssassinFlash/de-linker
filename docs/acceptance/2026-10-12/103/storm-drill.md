# #103 风暴演练记录（拔 Redis 实测降级路径）

实例：`t103`（本分支工作树 `de-linker-t103` 的检出插件 + 快照 `20261010-0033` 数据，
与评审站实例 t16e 同形态；t103 为本票新建）。wp-config 第 89 行
`define( 'WP_REDIS_GRACEFUL', true );`（本分支 `tools/local` 产出）。
站点 `http://127.0.0.1:8960`，Genie `http://127.0.0.1:8962`。

注：票面给的 `--live-code` 装入形式被 `tools/pull` 按设计拒绝——它要求实例不带检出
插件链接（装入的是线上旧插件代码），而演练必须跑本分支的能力代码；因此按 t16e 的
实际形态装入（`just pull load t103 20261010-0033`，检出插件 + 快照数据）。

## 1. 基线（Redis 正常，04:01 UTC）

- `POST /turn`（EN，"hybrid inverter … three-phase home … 10 kWp"）→
  `{"grounded": true, "fallback": false, "attempts": 1}`，SSE 完整（meta/block/done）。

## 2. 风暴窗口 04:02:44–04:07:43 UTC（`brew services stop redis`，`redis-cli ping` = Connection refused）

| 步骤 | 命令（要点） | 结果 |
|---|---|---|
| 站点页 | `curl -w '%{http_code}' http://127.0.0.1:8960/` | **HTTP 200**，389,228 字节正文，无 "Error establishing a Redis connection" 错误页 |
| ability 直调 | `curl …/wp-abilities/v1/abilities/linker%2Fsearch-products/run?input[device_class]=inverters&input[lang]=en` | **HTTP 200**，协议 JSON `{"qualified":[],"excluded":{"by_reason":[]},"unknown_fields":[]}` |
| 真实 Genie 轮次 | `POST /turn`（EN，"Which battery systems do you have for a home?"） | **HTTP 200**，`{"grounded": true, "fallback": false, "attempts": 1}`，块=文本+一个 ask（kwh），`done` 事件收尾 |
| php-error.log | `grep Predis logs/php-error.log` | 9 条 `Predis\Connection\ConnectionException: Connection refused [tcp://127.0.0.1:6379]`（04:02:52–窗口内），与 t16e 事故同异常类——区别是这一次每条只记日志，请求全部活着（对照 t16e：每条对应一个死请求、失败轮次时刻一一对应） |

降级机理：drop-in 的 `handle_exception` 在 `WP_REDIS_GRACEFUL` 下记日志并把请求切到
请求内缓存，读失败=缓存未命中，DB 兜上；下一个命令重连。

## 3. 能力全断的降级声明（同一窗口内，②的实测）

storm 版 Genie（`GENIE_WP_URL=http://127.0.0.1:1`，ability 全部不可达）跑一轮：

```
event: meta
data: {"turn_id": 654, "grounded": false, "fallback": true, "attempts": 2,
       "failures": ["linker/search-products returned 503 for …"], "language": "en"}

event: block
data: {"type": "handoff", "summary": "I could not answer this time. Please try
       again in a moment, or write to our team."}
```

- 服务层对 5xx/连接异常退避重试（3 次尝试、0.25 s/0.5 s）后才放弃；
- 轮次以 `fallback: true` + 失败明细落地为**声明的降级**（文案对抗评审的定稿句），
  而非 500、而非伪装成普通转人工（curl exit 0，SSE 完整，`done` 收尾）。

## 4. 复原（04:07:43 UTC）

- `brew services start redis` → `redis-cli ping` = PONG；
- `just serve t103` 恢复正常服务；`just wp t103 redis status` = **Status: Connected**；
- 复原后一轮：`{"grounded": true, "fallback": false}`。

## 5. 已知的环境限制（非本票）

快照 `20261010-0033` 的商品没有工程属性层（`linker/v1/engineering-feed`
products=0），`search-products` 因此 qualified 恒空——工程数据由切换步骤的
迁移脚本生成（规格 8），与 Redis 风暴与本分支改动无关；基线轮次与风暴轮次的
grounded 判定不受影响（模型按"目录里没有"作答仍是真话）。
