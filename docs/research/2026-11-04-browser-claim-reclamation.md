# Genie `browser_claim` 过期行的回收机制（#906，Part of #899）

研究票。只回答一件事：`linker_genie_browser_claim_<hash>` 这些 autoload=off 的 option 行为什么会永久留下、量级多大、三种回收机制各自付什么代价、`BROWSER_CLAIM_SECONDS` 改到 20 s 后并发还能不能收敛。结论供修复批直接采用。

生产只读（`ssh hostinger-de-linker` + WP-CLI / SQL），未写生产、未改 main、未部署。

---

## 0. 结论

1. **泄漏是结构性的，不是窗口太短**。claim 行只有一条创建路径（无 cookie 的 `entry_scope`）和一条删除路径（带 cookie 的 `entry_scope`），而删除路径在 `read_browser_claim()` 返回 `''` 时直接 return —— 这一条短路把「已过期」和「不存在」一起跳过，所以**过期的 claim 行连它自己的 tab 回来都不会被删**（`Conversations.php:750`）。真正删除它的只剩「同一 tab 在过期前再次带 cookie 请求」这一种。
2. **读路径惰性删除不可能修好这个 bug**。claim 的键是随机 tab UUID 的哈希（`Conversations.php:877`），泄漏的行属于「再也不会带着同一个 tab 出现的访客」；对这些行做惰性删除的前提是有人来读它，而永远不会有人来读。惰性删除只会删掉本来就会被 `add_option` 覆盖的少数行。
3. **建议：每小时一次有界扫描（复刻 `Protection\Resources` → `Replies::expire()` 的既有模式）+ 修正 close 路径的过期短路 + 发布时一次性清历史行。** 每日扫描（`Retention` 节奏）在量级上够用，但会给「一小时 3 600 行」的爬虫留出 24 h 的窗口；每小时更合适，且本仓已有每小时 cron 在跑（`linker_tools_reply_cleanup`，生产实测）。
4. **`BROWSER_CLAIM_SECONDS` 5→20 s 不改变日增**：创建量由「冷启动次数」决定，与窗口长度无关；窗口变长反而让更多「人工节奏的第二请求」落进窗口内，永久行**略减**。变长确实会把两个既有风险各放大 4 倍（tab id 持有者的采纳窗口、身份切换后的旧 key 采纳窗口），但都不改变收敛性；收敛性只会变好。
5. **真正的增长上限是接口速率，不是窗口**：`/linker-ai/v1/genie/entry-context` 是 `permission_callback => '__return_true'`（`EntryContext.php:31`）、无 RateLimit、无 admission（`ResourcePolicy::action()` 不含该路由），一个合法形状的 `tab` 就是一行。1 req/s 的爬虫 = 86 400 行/天。回收机制只能把「无限增长」压成「速率 × 扫描周期」，压不到零。

---

## 1. 机制事实（逐行）

### 1.1 一行是什么

| 项 | 值 | 证据 |
| --- | --- | --- |
| option 名 | `linker_genie_browser_claim_` + `substr(sha256(tab), 0, 32)`，共 59 字符 | `Conversations.php:62`、`:876-878` |
| 值 | `['key' => 32 hex, 'until' => time() + BROWSER_CLAIM_SECONDS]` | `Conversations.php:843-846` |
| autoload | `add_option(..., false)` → `autoload='off'` | `Conversations.php:848` |
| 序列化后大小 | 81 B（值）+ 59 B（名）；含索引页约 0.2–0.25 KB/行 | `php -r 'echo strlen(serialize(["key"=>str_repeat("a",32),"until"=>1793000000]));'` = 81 |
| 过期 | 常量 5 s | `Conversations.php:75` |
| 并发锁 | `GET_LOCK(<sha256(db/prefix/tab)>, 1)`，server-wide 命名锁 | `Conversations.php:86`、`:887-893`、`:912-922` |

`autoload='off'` 意味着这一行**不参与 `alloptions`**：它不会拖慢每次请求的 autoload 读取，也不会被 `wp_load_alloptions()` 带进内存。它的代价在表段、在按前缀做的范围扫描、在备份体积，不在请求热路径。

### 1.2 唯一创建路径

`entry_scope()`（`Conversations.php:713-733`）是唯一调用点链：

```
entry_scope($tab)
  ├─ 已登录 → principal = user:<id>:<session token>          （不碰 claim）
  └─ 访客
      ├─ browser_key() === ''  → claimed_browser_key($tab)   → 可能写一行
      └─ browser_key() !== ''  → close_browser_claim($tab)   → 删一行
```

`claimed_browser_key()`（`:792-812`）：

1. 读一次 claim；未过期就采纳；
2. 否则 `GET_LOCK`（最多 1 s）；拿到锁 → 清缓存 → 再读 → 仍然没有才 `publish_browser_claim()`；
3. 拿不到锁 → 清缓存 → 再读一次 → 依然没有就**不持锁** `publish_browser_claim()`。

`publish_browser_claim()`（`:841-858`）先 `add_option`，失败则读回赢家，仍然读不到就 `update_option` 覆盖。

**谁在什么时候调 `entry_scope`**（这决定创建频率）：

- `EntryContext::read()`，`POST /linker-ai/v1/genie/entry-context`（`EntryContext.php:57-62`）；
- `EntryContext::stage_brief()`，`POST /genie/project-brief` 带 `tab` 时（`:106`）；
- 客户端 `useDraftContext` 挂载即 `verify(false)`（`useDraftContext.ts:47`），并在 `focus`/`pageshow`/`visibilitychange→visible` 上 `verify(true)`（`:48-52`）；`verify(true)` 绕过合并（`nativeScope.ts:124-126`），每次都是一个独立 HTTP 请求。

也就是说：**打开一次 Genie 至少一次，页面重新获得焦点每多一次**。

### 1.3 唯一删除路径，被过期短路掐死

`close_browser_claim()`（`:745-762`）：

```php
$this->forget_browser_claim_cache( $tab );
if ( '' === $this->read_browser_claim( $tab ) ) {
    return;                       // ← 过期与不存在一起跳过（:750）
}
... lock / delete ...
```

`read_browser_claim()`（`:819-833`）在 `until < time()` 时返回 `''`（`:829-831`）。因此：

| 场景 | 行会被删吗 |
| --- | --- |
| 同一 tab，5 s 内带 cookie 再请求（兄弟请求） | 会 |
| 同一 tab，6 s 后带 cookie 再请求 | **不会**（过期短路） |
| 访客关标签页 / 换设备 / 爬虫不再回来 | **不会**（永远没人读） |
| 同一 tab 再次冷启动（无 cookie） | 被 `add_option` 的 `ON DUPLICATE KEY UPDATE` 覆盖，行数不变 |
| 任何清扫 | 不存在 |

补一条对照，确认没有第二条通道：删除只出现在 `delete_browser_claim()`（`:777-781`），而它的两个调用点都在 `close_browser_claim()` 内（`:754`、`:758`）。全仓 grep `BROWSER_CLAIM_PREFIX` 只命中定义、`browser_claim_option()`、锁名与测试（`EntryScopeConcurrencyTest.php:389`）。**没有第二条回收通道。**

### 1.4 为什么「短窗口」这个设计本身没错，但回收接错了地方

5 s 窗口的原始目的写在注释里（`:64-74`）：客户端可能在收到 Set-Cookie 之前就发出第二个 entry-context，两个请求必须收敛到同一个 browser key。这是**兄弟请求去重**，不是**行回收**。把回收挂在这条路径上，等于要求「访客必须在 5 s 内再发一次带 cookie 的请求」——而人的第二次请求（点开、输入、focus）通常在 5 s 之后。于是回收只在机器节奏下生效，在人节奏下失效。

---

## 2. 生产量级（只读证据）

采样时间 2026-11-04 02:26–02:41 UTC。

### 2.1 当前状态

| 指标 | 值 | 命令 |
| --- | --- | --- |
| claim 行数 | **0** | `wp option list --search='linker_genie_browser_claim_%' --format=count`；SQL `LIKE 'linker\_genie\_browser\_claim\_%'` 同为 0 |
| `wp_options` 行数 | 924 | `SELECT COUNT(*)` |
| autoload 分布 | `auto` 379 / `on` 234 / `off` 310 / `no` 1 | `GROUP BY autoload` |
| `off` 总字节 | 4 113.9 KB（不是 claim；最大的是 `linker_i18n_german_copy_backup` 584 KB、`..._urls_backup` 538 KB、`_transient_dirsize_cache` 482 KB） | `SUM(LENGTH(option_value))` |
| `AUTO_INCREMENT` | **390 871** → 390 875（02:29:50 → 02:40:40） | `information_schema.tables` |
| Data_length / Index_length / Data_free | 8 404 992 / 147 456 / 426 770 432 | `SHOW TABLE STATUS LIKE 'wp_options'` |
| `AVG_ROW_LENGTH` | 8 330 | 同上 |
| object cache | **无** dropin；`wp redis status` = Not enabled（插件在装但未启用） | `ls wp-content/object-cache.php`；`wp redis status` |
| `DISABLE_WP_CRON` | `true`（`wp-config.php:100`），主机每分钟 CLI cron 驱动 | `grep` |
| cron 是否真的在跑 | `wp_scheduled_delete`、`delete_expired_transients` 均为 daily 且 `next_run` ≈ 10 h 后；`linker_tools_reply_cleanup` hourly；`linker_tools_planner_claim_sweep` 02:06 状态 `complete` | `wp cron event list`；`wp_actionscheduler_actions` |
| 部署版本 | 生产 `Conversations.php` sha256 = `747eb9f5…` = main | `sha256sum` 双端 |

**39 万自增 vs 924 行**是本票最硬的一个数字：这张表历史上被插入过约 39 万次并删掉了绝大部分。实测活行字节 `SUM(LENGTH(option_name)+LENGTH(option_value))` = 4 513 614 B（4.3 MB），而表段 `Data_length` = 8 404 992 B（8.4 MB）——约 3.7 MB、46% 的段被删除/重插的churn 占着。AUTO_INCREMENT 本身无害，但它是「写放大已经很大」的直接证据，也说明这张表不是「一行一行慢慢长」的。

### 2.2 增长模型

**「一次冷启动」= 一次真正跑起来的 `entry_scope`**，不是一次页面浏览。客户端只在 Genie 挂载后才发第一个 entry-context：helper 是点击/ask 后才 boot（`Entries.php:269` "A click or ask is what boots a helper"），workspace 页直接 boot（`print_loader(true)`），首页 hero 在交互后才展开。所以浏览 10 个页面而没打开 Genie = 0 行。

三个锚点：

1. **访客会话量**（`wp_posts` where `post_type='linker_conversation'`）：总量 859，其中 guest 827；按天 2026-10-20 = 425、10-19 = 134、10-18 = 207、10-21 = 14，10-22 起 2–8/天。
2. **浏览器 key 数**：`wp_postmeta` 中 `meta_key='linker_genie_browser'` 共 790 行、**786 个不同 key**，对应 827 条 guest 会话。一个 browser key 只在「这次冷启动真的开了一条会话」时才留 mark，所以 **786 是「至少发生过多少次冷启动」的下界**，也是「至少创建过多少条 claim 行」的下界（每次冷启动都先写一行，无论后续是否开会话）。786 ≈ 827 条 guest 会话也说明：在这个站点上一条会话对应一次冷启动，不是「一条会话被反复冷启动」。
3. **options 表写入速率**（三次采样）：390 865 @02:26:03 → 390 871 @02:29:50（6 行 / 227 s = 1.6 行/分）→ 390 875 @02:40:40（4 行 / 650 s = 0.37 行/分）。合计 **10 行 / 877 s ≈ 0.7 行/分 ≈ 1 000 行/天**，这是全表所有来源（transient、rate limit、claim、其它插件）的合计写入速率——即「claim 即使占到全部，也只有这个上限」。

每日泄漏量 ≈ 冷启动次数 × 「窗口内没有第二次带 cookie 请求」的比例：

| 场景 | 冷启动/天 | 永久行/天 | 一年活行 |
| --- | --- | --- | --- |
| 当前自然流量（2–8 条 guest 会话/天） | 2–8 | 2–8 | 0.7k–2.9k 行 ≈ 0.15–0.6 MB |
| 10-18~10-21 那种研究/实测日（约 195 条会话/天） | ~200 | ~150–200 | 但只持续几天 |
| 一次研究采样（父线记录的 164 行） | 164 | 164 | — |
| 一个 1 req/s 的爬虫打 `entry-context` | 86 400 | 86 400 | 31.5 M 行/年 ≈ 6 GB（按 0.2 KB/行） |

**为什么「一次采样 = 164 行」：** tab id 存在 `sessionStorage`（`nativeScope.ts:45-65`），browser key 存在 cookie。无头/自动化浏览器若每次导航都用全新上下文，两者都不保留 → **每个请求都是一个新 tab、一次冷启动、一行 claim**。164 行就是这个模式下一次采样会话的请求数，而不是 164 个真实访客。同样的机制也解释了「换设备」「隐私模式重开」为什么各留下一行。

最后一档才是真风险：接口没有限速，也没有「每 IP/每 tab 只允许一行」的语义，回收机制只能把它压成「速率 × 清扫周期」。

**20 s 窗口后的变化：0。** 创建量由冷启动次数决定；窗口只影响「第二次请求是否落在窗口内」，而落在窗口内的第二次请求是**删除**不是创建。5→20 s 会让更多人工节奏的第二请求（比如 8 s 后的一次 focus）成功触发删除，永久行略减。

---

## 3. 三种机制对比

先列出仓内已经存在的两条同表清理先例，它们说明「在 wp_options 上做回收」在本仓不是新发明：

- `Genie/RateLimit.php:74-80`：每次 `take()` 先 `DELETE FROM wp_options WHERE option_name LIKE 'linker_tools_limit_<name>.%' AND RIGHT(option_name,10) < <当前桶>`，再 `INSERT IGNORE` + 条件 `UPDATE`。写路径自带清扫，无 cron、无锁；行数以「活跃调用者 × 窗口」为界。生产现在只剩 **2 行**。
- `Protection/Replies.php:127` + `Resources.php:55-59`：每小时 WP-Cron `linker_tools_reply_cleanup` → `get_posts(... posts_per_page 1000 ... meta 过期)` → 逐条 `wp_delete_post`。有界批、有现实运行记录（生产 hourly）。
- `Genie/Retention.php:106-137`：每日扫描，`SCAN_BATCH=100` × `MAX_BATCHES=20`，逐条投给 Action Scheduler 删除作业（`:130`）。

### (a) 沿用每日扫描（Retention 模式）

| 维度 | 评价 |
| --- | --- |
| 钩子 | `add_action('init', schedule)` + `wp_schedule_event(time(), 'daily', HOOK)`（`Retention.php:73-88`）。生产的 `DISABLE_WP_CRON=true` 不影响它：主机每分钟跑一次 `wp cron event run --due-now`，daily 事件在到期后 ~1 分钟内执行（实测 `wp_scheduled_delete` / `delete_expired_transients` 都在表里且 next_run 正常）。 |
| 批量边界 | 一次 SQL 只能按 `option_name` 前缀做索引范围；过期时间在**序列化值**里（`i:<10 位>;}`），不能直接比较。可行形态：`SELECT option_name, option_value ... WHERE option_name LIKE 'prefix%' AND option_id > <cursor> ORDER BY option_id LIMIT 500`，PHP 反序列化判 `until < now - grace`，再 `DELETE ... WHERE option_name IN (...)`；游标沿用 `ClaimOutbox.php:201-208` 的 `update_option(<cursor>)` 写法。 |
| 锁 | 不需要 `GET_LOCK`。前提是 grace（如 1 h）远大于 `BROWSER_CLAIM_SECONDS`：清扫只命中「早就过期」的行，正常 mint 的行永远不会进入谓词；唯一可能的交叉是同一行刚好在清扫读取与删除之间被重新 publish，代价是那个 tab 重新 mint 一次（一行的分叉），可接受。 |
| 表膨胀 | 有界：行数上限 = 泄漏速率 × 24 h。 |
| 正常访客延迟 | 0（请求路径完全不变）。 |
| 主机负载 | 一次运行 O(claim 行数)，几十毫秒到几百毫秒；在共享主机上一天一次可以忽略。 |
| 问题 | 24 h 窗口太宽。1 req/s 的爬虫一天能堆 86 400 行；备份、`wp option list`、任何按前缀的扫描都要跨这 8 万行。 |

### (b) 读路径惰性删除（过期即 DELETE）

| 维度 | 评价 |
| --- | --- |
| 能不能回收 | **不能**。读的人只有「同一个 tab 又回来」，而泄漏行的键是随机 tab（`crypto.randomUUID()` 存在 sessionStorage，`nativeScope.ts:45-65`），回不来的人永远不会触发读。 |
| 额外写放大 | 每个「带着过期行的 tab 回来」的冷启动多一次 DELETE；而这些行本来就会被 `publish_browser_claim()` 的 `add_option()` 重新写成新值（`add_option` 先判存在，已存在则返回 false，随后 `update_option` 覆盖），净收益 0。 |
| 正常访客延迟 | 冷启动多一次写（只有命中过期行时）。 |
| 变体：写时前缀修剪（RateLimit 的做法） | 可行，但当前命名 `prefix + hash` **没有时间桶**，前缀 DELETE 无法只命中过期行——除非把名字改成 `prefix + <bucket> + hash` 让名字本身按时间有序。收益是把清扫变成纯索引范围删除；代价是改键名 + 一次性兼容。生产现在 0 行，改名的迁移成本此刻最低，但**没有必要**（见 §5.5）。 |

### (c) 组合（推荐）

每小时有界扫描（兜底，覆盖所有不再回来的行）+ 修 close 的过期短路（把「人节奏的第二请求」这一类立即回收，零额外请求）+ 发布时一次性清理。

| 维度 | 评价 |
| --- | --- |
| 表膨胀 | 行数上限 = 泄漏速率 × 1 h（+ grace）。1 req/s 爬虫 ≈ 3 600 行常驻，几 MB 级，可接受。 |
| 正常访客延迟 | 0；close 路径的修正只为正确性，语句数反而增加（见 §5.2）。 |
| 主机负载 | 每小时一次 O(几千行) 的扫描；与 `linker_tools_reply_cleanup` 同节奏，已有先例。 |
| 锁/竞态 | 扫描：无锁 + grace。close：沿用现有的 `GET_LOCK` 语义不变。 |
| 失败模式 | 扫描被跳过 → 退化为 (a) 的 24 h；不会丢数据、不会影响 mint 正确性。 |

---

## 4. `BROWSER_CLAIM_SECONDS` 20 s 后的并发收敛

### 4.1 锁语义

`lock_browser_claim()` 用 `SELECT GET_LOCK(<64 字符 sha256>, 1)`（`:887-893`）。MySQL/MariaDB 的命名锁是 **server 级、按连接持有、连接断开自动释放**（注释 `:881-886` 已写明）。名字里混入 `DB_NAME` 和 `$wpdb->prefix`（`:912-922`），避免同主机多站点互撞。

### 4.2 两条路径

- **拿到锁**（正常情况）：清缓存 → 再读 → 有则采纳，无则 publish。
- **拿不到锁**（1 s 超时）：清缓存 → 再读 → 有则采纳，无则**不持锁** publish（`:797-801`）。

### 4.3 20 s 对收敛的影响：单调变好

| 竞争形态 | 5 s | 20 s |
| --- | --- | --- |
| A 持锁 publish，B 1 s 超时后重读 | B 读到 A 的行（只要 A 已提交）→ 同一 key | 同左，且 A 的行有效期更长，B 在任何稍晚的重读里也仍然读得到 → **更稳** |
| B 在 A 提交前重读（读不到）→ 不持锁 publish → `add_option` 与 A 撞唯一键 | 撞键后读回 A；若 A 已提交则收敛 | 同左，且读回成功率高得多 |
| 两次冷启动间隔 6–20 s（同一 tab，cookie 尚未写入/被丢） | 第二次重新 mint → **两个 key** | 第二次采纳第一个 key → **收敛** |
| 两次冷启动间隔 > 20 s | 重新 mint（正确：新访客） | 同（20 s 后同样重新 mint） |

窗口变长只会把「重新 mint」的判定阈值推后，不会引入新的分叉。

### 4.4 残余竞态（与窗口无关，但值得同批处理）

`publish_browser_claim()` 用的是 `add_option()`（`:848`）。核心实现是 `INSERT INTO wp_options (...) VALUES (...) ON DUPLICATE KEY UPDATE option_name=VALUES(option_name), option_value=VALUES(option_value), autoload=VALUES(autoload)`（生产 WP 7.1.4 `wp-includes/option.php`），也就是**写值覆盖**而不是失败。`add_option()` 自己会先 `get_option()` 判存在（存在即返回 false），所以「A 已提交」这类常见情况会被它挡住；真正漏网的是**窄窗口**：

- B 在 A 的 INSERT 之后、B 自己的存在性检查之前读不到 → B 的 INSERT 会覆盖 A 的 key；
- 结果：A 返回 key_A、B 返回 key_B，两次响应各自 Set-Cookie，行里留后到者；
- 客户端若两个响应都收下（不同文档/不同 surface），其中一个 surface 的 scope 就与 cookie 不一致。

触发条件是「两个冷启动真并发 + 落败者 1 s 超时后走到不持锁 publish」；`nativeScope` 的同页合并（`nativeScope.ts:127-138`）已经挡掉了同文档并发，所以概率低。修法很便宜：把 publish 改成**首写者胜**（`INSERT IGNORE`，或 `ON DUPLICATE KEY UPDATE option_value = option_value`），再读回赢家。这与窗口长度无关，但和「把 `BROWSER_CLAIM_LOCK_SECONDS` 从 1 s 提高」是同一批的事——锁等得越久，走到不持锁 publish 的请求越少。

### 4.5 注释已经过期的那一段

`:77-86` 的注释按 5 s 客户端预算写的：「The client aborts entry-context at five seconds. Waiting the same five seconds for the lock makes lock contention finish exactly at that client deadline… 」。客户端预算改成 20 s 后，这句话的前提消失，1 s 锁等待不再有「刚好等于客户端截止时间」的含义。同批应：

- 把 `BROWSER_CLAIM_LOCK_SECONDS` 提到 3–5 s（仍远小于 20 s 预算），让落败者更可能等到赢家，直接消掉 §4.4 的大半窗口；
- 重写 `:64-86` 两段注释，说明「窗口 = 客户端辅助身份预算」与「锁等待 = 窗口的一小部分」这两条现在各自对齐到什么值。

### 4.6 20 s 放大的两个既有风险（不改变结论，但要在票上写明）

1. **tab id 持有者窗口**：claim 只按 tab 哈希寻址，任何知道该 UUID 的请求都能读到 key 并把它写进自己的 `linker_genie_browser` cookie。5→20 s 把「偷到 tab id 后的冒用窗口」放大 4 倍。tab id 是 128 位随机、只存在 sessionStorage，风险低但不为零。
2. **身份切换后的旧 key 采纳**：`signed_out()`（`:505-508`）与 `claim_for()`（`:518-563`）都会换一个新 browser key；如果切换后 20 s 内出现一个**不带 cookie** 的请求（切换前发出的、延迟返回的），它会采纳切换前的 claim。客户端有 generation 校验（`nativeScope.ts:104`、`:167-171`）会丢弃旧响应，但 Set-Cookie 已经落在浏览器里。5 s 时这个窗口小到基本不可能，20 s 时变成「可能」。

---

## 5. 机制建议（修复批可直接采用）

### 5.1 清扫：新增 `Genie\BrowserClaim`（或放进 `Conversations` 的静态方法），每小时一次

```
HOOK   = 'linker_tools_browser_claim_sweep'
GROUP  = 'linker-tools'（沿用 Retention::GROUP）
GRACE  = 3600 s            // 远大于 BROWSER_CLAIM_SECONDS，杜绝与 mint 交叉
BATCH  = 500               // 每次 SELECT/DELETE 的行数
MAX_BATCHES = 20           // 单次运行上限 10 000 行
```

- 注册：`add_action('init', schedule)` + `wp_schedule_event(time() + HOUR_IN_SECONDS, 'hourly', HOOK)`，与 `Resources.php:57-59` 完全同形；`register_deactivation_hook` 里 `wp_clear_scheduled_hook`（`Retention.php:94-99` 同形）。
- 扫描：

```sql
SELECT option_name, option_value
FROM wp_options
WHERE option_name LIKE 'linker_genie_browser_claim\_%'
  AND option_id > <cursor>
ORDER BY option_id ASC
LIMIT 500
```

  PHP 反序列化，`until < time() - GRACE` 的进删除集；名字格式不符 / 值损坏的也删（它们永远不可能被采纳）。删除用一次 `DELETE FROM wp_options WHERE option_name IN (...)`（`$wpdb->prepare` + 占位符），游标用 `option_id` 存进一个 autoload=off 的 option，沿用 `ClaimOutbox.php:201-208` 的写法。

  两个实现细节：① 前缀末尾是下划线，**必须**用 `$wpdb->esc_like()` 拼 `LIKE`，否则 `_` 会退化成单字符通配（`linker_genie…` 里的每个 `_` 都是）；`RateLimit.php:76` 就是照这个写的。② 值损坏的行只可能来自外部改写，删它们顺手，不必为它们写额外分支。

- **不需要 `GET_LOCK`**：grace 保证不会碰活行；万一与一次重新 publish 撞上，结果只是那个 tab 多 mint 一次。
- 为什么 hourly 而不是 daily：daily 的窗口是 24 h，1 req/s 的爬虫就是 86 400 行；hourly 把它压到 3 600 行，且生产已有 hourly 先例（`linker_tools_reply_cleanup`）。

### 5.2 close 路径：删掉过期短路（3 行改动）

`close_browser_claim()` 现在先用 `read_browser_claim()` 判断「有没有未过期的行」，过期就 return。改成「只要这个 option 存在就删」：

```php
$stored = get_option( $this->browser_claim_option( $tab ), false );
if ( false === $stored ) {
    return;
}
```

收益：所有「人节奏」的第二请求（8 s 后的 focus、30 s 后的第一次发送）都能回收自己那一行。成本要说清楚，别拿它当性能优化：命中一行时现在与改后都是 5 条语句（`SELECT`(read) + `GET_LOCK` + `SELECT`(delete_option 内部) + `DELETE` + `RELEASE_LOCK`）；命中过期行的这条路径现在只做 1 次 `SELECT` 就 return，改后会多 4 条。收益是**正确性**（该回收的行真的被回收），不是延迟。要省掉这一步的第二次 `get_option`，可以直接调 `delete_browser_claim()` 而不先判存在：`delete_option()` 自己会先 `SELECT autoload`，行不存在时只花这一条就返回。

### 5.3 发布时一次性清理

发布脚本里一次 `DELETE FROM wp_options WHERE option_name LIKE 'linker_genie_browser_claim\_%'`（此时全部行都已无意义：最老的也已过期数天；唯一代价是某个恰好在此刻冷启动的 tab 重新 mint 一次）。生产当前 **0 行**，这一步在 de-linker 上是空操作，但对本地实例/其它站点（同一份代码）是必要的。属于数据写入，按 AGENTS §5 先备份后读回。

### 5.4 同批要改的常量与注释

| 位置 | 现在 | 建议 | 理由 |
| --- | --- | --- | --- |
| `Conversations.php:75` `BROWSER_CLAIM_SECONDS` | 5 | 20（与 `nativeScope.ts:20` 同批） | 票面约束 |
| `Conversations.php:86` `BROWSER_CLAIM_LOCK_SECONDS` | 1 | 3–5 | §4.4/§4.5：1 s 的理由已随客户端预算失效 |
| `Conversations.php:64-86` 注释 | 按 5 s 写 | 按 20 s 重写两段 | 注释与代码必须同步 |
| `nativeScope.ts:20` `CONTEXT_BUDGET_MS` | 5 000 | 20 000 | #901 已裁定 |

### 5.5 明确不做

- **不改 option 名去塞时间桶**：`prefix+hash` 的前缀范围已经足够小，清扫成本 O(claim 行数)，改成时间有序只在「每天几十万行」时才值得；那属于另一个量级的问题。
- **不加 `GET_LOCK` 到清扫**：grace 已经排除交叉，加锁只会引入失败路径。
- **不给 `entry-context` 加 RateLimit**（本票范围内）：真正的速率上限是另一个决策（会给 NAT 后的真实客户带来误伤），而 hourly 清扫已经把「无限增长」变成「速率 × 1 h」。票上应记录这个残余上限（§2.2 最后一档），交给修复批决定要不要单独处理。

### 5.6 测试

复用 `EntryScopeConcurrencyTest` 的夹具风格（它已经在 `tearDown`（`:86`）里调 `delete_claim()`（`:379-389`）按前缀删行）：

1. 扫描前写入 3 行：1 行未过期、1 行过期 2 h、1 行名字合法但值损坏 → 运行 `sweep()` → 只剩未过期那行。
2. grace 边界：过期 30 s 的行在同一次 sweep 里**保留**（证明不会碰刚从过期边缘回来的 tab）。
3. close 修正：先 mint（行未过期），把 `until` 改成过去，再带 cookie 调 `entry_scope` → 行消失（当前实现会留下）。
4. 批量边界：写 `BATCH + 1` 行过期数据 → 一次 sweep 后游标推进、第二批在下一轮被清掉。

---

## 6. 未决与限制

1. **未在生产验证「合法 tab → 200 + 一行」**：那会写生产。代码路径清楚（`permission_callback => '__return_true'`，`rest_cookie_check_errors` 在无 nonce 时按未认证放行），我只验证了非法 tab 的 400（`rest_invalid_pattern`）。修复批在本地实例上一条 curl 即可确认。
2. **`Data_free = 426 770 432`（约 407 MB）未进一步证实**：共享主机账号没有 `PROCESS` 权限，读不到 `INNODB_SYS_TABLESPACES`，无法区分「这张表的空闲 extent」与「共享表空间」。已证实的只有 `Data_length` 8.4 MB 对活行 4.3 MB（约 46% 段开销，见 §2.1）。若 407 MB 确属这张表，`OPTIMIZE TABLE wp_options` 能回收，但那是表重建，属于修复批的独立决定。
3. **没有访问日志**：无法直接数 `entry-context` 的调用次数，§2.2 的日增是「会话量 + browser mark 比例 + 全表写入速率」三个实测锚点推出来的区间，不是精确计数。修复批可以先上清扫，再用清扫日志（删了多少行/次）反推真实泄漏率——这是最省成本的测量方式。
4. 研究票不判断「要不要顺手治爬虫」，只把上限写清楚（§2.2、§5.5）。

---

## 7. 证据与复现命令

```bash
# claim 行数（两种口径，都应为同一个数）
ssh hostinger-de-linker "/usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html \
  option list --search='linker_genie_browser_claim_%' --format=count"
ssh hostinger-de-linker "/usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html \
  db query \"SELECT COUNT(*) FROM wp_options WHERE option_name LIKE 'linker\\_genie\\_browser\\_claim\\_%'\""

# 表形态与写放大
ssh hostinger-de-linker "/usr/local/bin/wp --path=… db query \"SHOW TABLE STATUS LIKE 'wp_options'\""
ssh hostinger-de-linker "/usr/local/bin/wp --path=… db query \"SELECT AUTO_INCREMENT FROM information_schema.tables \
  WHERE table_schema=DATABASE() AND table_name='wp_options'\""

# 会话量（泄漏上界的锚点）
ssh hostinger-de-linker "/usr/local/bin/wp --path=… db query \"SELECT DATE(post_date_gmt) d, COUNT(*) n \
  FROM wp_posts WHERE post_type='linker_conversation' GROUP BY d ORDER BY d DESC LIMIT 30\""

# cron 是否真的在跑
ssh hostinger-de-linker "/usr/local/bin/wp --path=… cron event list --fields=hook,next_run_relative,recurrence"

# 部署版本一致性
shasum -a 256 plugins/linker-tools/includes/Genie/Conversations.php
ssh hostinger-de-linker "sha256sum …/wp-content/plugins/linker-tools/includes/Genie/Conversations.php"
```

代码引用一览：`Conversations.php:62,75,86,505-508,518-563,694-696,713-733,745-762,767-770,777-781,792-812,819-833,841-858,865-869,876-878,881-893,900-922`；`Retention.php:31,44,52,61,73-99,106-137`；`RateLimit.php:31,67,74-90`；`Replies.php:127`；`Resources.php:55-59`；`ClaimOutbox.php:201-208`；`EntryContext.php:31,57-62,106`；`nativeScope.ts:20,45-65,104,119-139,167-171`；`useDraftContext.ts:47-52`；`Plugin.php:96-109`；`EntryScopeConcurrencyTest.php:107-146,153-197,203-243,250-340`。
