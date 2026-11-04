# Genie 三处「未决即报错」的根因与修法依据

票 #901（Part of 地图 #899）· 2026-11-04

本报告只回答三件事的根因、生产实测数据和修法决策所需材料。所有结论都指到源码行、提交或实测数据；没有测量支撑的推断单独标注为推断。

---

## 0. 结论摘要

三处表面看起来都是「加载被当成失败」，但机制互不相同，修法不能合并：

| # | 表面 | 真实机制 | 根因类别 |
|---|---|---|---|
| 1 | `GenieCard.tsx:84` | 状态模型把一个 promise 的三种结果压成 `StoreProduct \| null` 的两种取值 | **状态建模缺失**：`null` 同时表示「未决」与「失败」 |
| 2 | `nativeScope.ts:20` | `5000` 是从已经因过小而废弃的商品元数据预算抄来的，从未针对 entry-context 测量 | **阈值无依据**：不是测出来的，是继承来的 |
| 3 | `request.ts:171-176` | 只有 `action === 'genie'` 有 owner 清理路径；其余 action 的 status 节点无主 | **生命周期缺口**：节点建了但没人负责回收 |

第 2 项的生产实测给出了硬结论：**30 路并发下 p95 = 5.003 s，已经越过 5000 ms 阈值**；安静态 p95 = 3.365 s。这台主机的 WordPress 冷启动地板本身就有 4.2–4.7 s（以最轻的 `GET /wp-json/` 为对照），所以 5000 ms 不是「留了余量」，而是贴着地板画的线。

---

## 1. 第 1 处：`GenieCard` 把未决读成失败

### 1.1 代码事实

`plugins/linker-tools/src/genie/components/GenieCard.tsx`：

- 第 60 行：`const [ product, setProduct ] = useState< StoreProduct | null >( null );`
- 第 63–82 行：`useEffect` 里 `store.products(...)` 与 `productModel(...)` 各自 `.then()`；**两者都没有 `.catch()`**，也没有失败标记。
- 第 84–90 行：`if ( ! product ) { return <p ...>{ __( 'Genie could not load this product.', 'linker-tools' ) }</p>; }`

初值 `null` 与「promise 被拒绝后 `product` 仍是 `null`」在这个类型里是同一个值。组件没有第三个可以存放结果的槽位，所以首帧必然落到失败分支——这不是「失败后显示错误」，而是**首帧就是错误**。

### 1.2 为什么 1–3.7 s 后会「自己修好」

`store.products()`（`plugins/linker-tools/src/configurator/api/store.ts:87-98`）走 Woo Store API `wc/store/v1/products`，是一个真实的跨网往返：

```ts
async products( ids, locale ) {
    ...
    const response = await fetcher( `${ base }/products?${ query }`, { credentials: 'same-origin' } );
    return response.ok ? response.json() : [];
}
```

注意第 97 行 `response.ok ? response.json() : []`：**非 2xx 也返回空数组而不是拒绝**。这意味着即便 promise 正常 settle，`first` 也可能是 `undefined`，`setProduct` 不会被调用，`product` 停在 `null`——**真失败与未决最终呈现完全相同的文案**。这正是父线观察到的「promise 未决与真失败不区分」的具体实现形态：不只是 `if ( ! product )` 写法问题，上游连「失败」这件事都没传下来。

1–3.7 s 的闪烁时长与第 2 节的 Store API 同级往返量级（生产 REST 往返 3–4.7 s）相符。

### 1.3 缺失的是哪一态

`ProductCard`（`plugins/linker-tools/src/shared/ProductCard.tsx`）**已经**有承载「加载中」的语汇：

```ts
export type CardState = 'idle' | 'pending' | 'added' | 'unverified' | 'retry';
```

`GenieCard` 把 `status` 原样转交给 `ProductCard`，但这个 `status` 是**卡片动作**（加入 Lösungsentwurf / 保存）的反馈，不是卡片**内容加载**的反馈。内容加载这一维在 `GenieCard` 里根本没有状态变量，所以「缺一态」的准确说法是：

缺的不是 `CardState` 里的一个值，而是**卡片内容自身的加载状态**（`loading | ready | failed`）。当前实现用 `StoreProduct | null` 承担了这个职责，而它只有两态。

### 1.4 谁调用了它

- `plugins/linker-tools/src/genie/App.tsx:2686`
- `plugins/linker-tools/src/hero/Hero.tsx:1093`

两处都是产品卡出现在回答里的路径，所以这个首帧错误在 dock、workspace 与首页 hero 三个表面上都能出现。

### 1.5 测试覆盖

`grep 'could not load this product'` 在 `plugins/linker-tools/src/` 里**只命中 GenieCard.tsx 自己**，没有任何测试断言这句话。也就是说这个首帧错误从未被测试钉住，改起来没有既有断言需要迁移。

---

## 2. 第 2 处：`CONTEXT_BUDGET_MS = 5000` 的来源与生产延迟

### 2.1 这个数字的完整谱系（git 考古）

**引入 commit：`eb097915d`（2026-10-22，"Preserve marketing questions through verified Genie entry recovery"）。**

同一提交改动的 `docs/specs/13-genie.md` 原文写明了它的依据：

> 5 秒辅助读取预算**沿用当前商品元数据读取约定**，独立于模型时限。

这句话是全部依据。它没有引用任何 entry-context 的测量，而是**继承当时商品元数据读取的展示预算**。`nativeScope.ts:19` 那句注释 `Existing auxiliary metadata deadline; independent of model transport.` 里的 "Existing" 指的就是这件事。

**被继承的那个约定，两天后就被推翻了。** `0a5a224c9`（2026-10-24，"Keep Genie customer reads within native operation budgets"）把商品元数据预算从 5 秒改成 20 秒，`docs/specs/13-genie.md` 同批改动写的理由是：

> 最多 20 秒（与服务端 `AbilityClient`、`PublicationClient` 既有单次原生读取预算一致；2026-10-24 当前资料实走中**有效读取需 8–10 秒，旧的 5 秒预算会误删可用资料链接**；这是呈现预算，不是服务端 SLA）

`plugins/linker-tools/src/genie/api/product.ts:75-80` 的注释与常量是这个结论的代码形态：

```ts
/**
 * Use the same 20-second native-read budget as Genie's AbilityClient and
 * PublicationClient. Current customer acceptance measured valid native reads
 * at 8–10 seconds; the former five-second presentation timer discarded their
 * current permissions and document links.
 */
export const ARTIFACT_TIMEOUT_MS = 20_000;
```

**entry-context 没有跟着迁移。** `0a5a224c9` 只动了 `product.ts` 与 `turn.ts` 的预算和规格里对应的两段，`nativeScope.ts` 的 5000 原样留下，规格里那句话只被改写成「身份核验保留独立的 5 秒预算；当前产品及发布许可读取使用下述 20 秒预算」。

所以答案是：**5000 没有任何针对 entry-context 的真实测量依据。** 它是一个被继承的数字，而它来源的那个判断（「5 秒够」）已经被同一批人在两天后用实测推翻，推翻的理由正是「5 秒会误删可用数据」。

### 2.2 服务端围着这个客户端值倒推

`plugins/linker-tools/includes/Genie/Conversations.php` 里两个常量都写明跟随客户端：

- 第 66–74 行 `BROWSER_CLAIM_SECONDS = 5`：*"Five seconds is that client's auxiliary identity budget (nativeScope.ts CONTEXT_BUDGET_MS)."*
- 第 78–86 行 `BROWSER_CLAIM_LOCK_SECONDS = 1`：*"The client aborts entry-context at five seconds. Waiting the same five seconds for the lock makes lock contention finish exactly at that client deadline, so a delayed winner is reported as a Genie load failure."*

第二段的措辞很关键：它把「锁等待恰好打到客户端 deadline」明确描述为「被报告为 Genie 加载失败」的成因。`docs/acceptance/2026-10-30/563-entry-context-deadline/README.md` 记录了这个成因在生产的实测形态：

```text
https://de-linker.com/wp-json/linker-ai/v1/genie/entry-context
duration: 5004.7 ms
responseStatus: null
```

那份验收文档还诚实标注了局限：*"That live timing proves the browser deadline expired; by itself it does not identify the server-side waiter... The exact original waiter was not separately instrumented."* 票 #563 的修复只把服务端锁等待降到 1 秒，**没有动客户端 5000**，并留下 *"Production deployment and browser readback remain required before this fix is complete."*

**这是一条硬约束：改 `CONTEXT_BUDGET_MS` 必须同时改 `BROWSER_CLAIM_SECONDS`。** 后者的语义是「无 cookie 的兄弟请求可以沿用本 tab 刚 mint 的 key 的时间窗」，窗长直接等于客户端预算。只改客户端会让两个并发首请求各自 mint 一把 key，破坏「同一 tab 的冷启动收敛到同一个 browser key」这个契约。`BROWSER_CLAIM_LOCK_SECONDS` 则应继续保持显著小于客户端预算。

### 2.3 生产实测

#### 采样方法

- 直连生产 `https://de-linker.com/wp-json/linker-ai/v1/genie/entry-context`，`POST`，`Content-Type: application/json`，body `{"tab":"<uuidv4>"}`。
- 每种条件**串行**发请求（除标注并发的批次），用 `curl -w '%{http_code} %{time_total}'` 记录状态码与总耗时。
- 冷 mint 条件每个请求使用**新的 tab UUID 且不带 cookie**，强制走服务端 `claimed_browser_key()` 的完整冷启动路径；温态条件使用首个响应 `Set-Cookie` 下发的 `linker_genie_browser` 值。
- 并发批次用后台子 shell 同时发起，各自独立 tab UUID（模拟不同访客），或同一 tab（模拟命名锁争用）。
- 全部为只读：端点的 `read()` 只计算并返回 HMAC scope，写入的只有 `linker_genie_browser` cookie 与 5 秒期的 claim option（既有行为，非本次引入）。没有改任何生产数据、配置或代码。
- 分位用 nearest-rank 法（`ceil(q·n)` 取序位），与样本量小的事实一致地保守。

#### 实测结果

| 条件 | n | 状态码 | min | p50 | p95 | max | mean |
|---|---|---|---|---|---|---|---|
| 冷 mint，串行 | 29 (1 个 TLS 失败) | 200 | 2.736 | **3.110** | **3.365** | 3.367 | 3.066 |
| 温态（带 cookie），串行 | 30 | 200 | 2.723 | **3.014** | **3.382** | 3.521 | 3.029 |
| 10 路并发，不同访客 | 10 | 200 | 2.722 | 2.987 | 3.192 | 3.192 | 2.974 |
| 8 路并发，同 tab（命名锁争用） | 8 | 200 | 3.046 | 3.053 | 3.370 | 3.370 | 3.188 |
| 30 路并发，不同访客（第 1 次） | 20 (+8×500, 2×TLS失败) | 200/500 | 4.046 | 4.223 | 4.494 | 4.517 | 4.301 |
| **30 路并发，不同访客（第 2 次）** | **30** | **200** | 2.889 | **4.742** | **5.003** | **5.030** | 4.613 |

#### 对照组（同主机、同方法）

| 端点 | n | min | p50 | max |
|---|---|---|---|---|
| `GET /wp-json/`（最轻的 REST 索引） | 9 (1 个 TLS 失败) | 3.984 | **4.533** | 4.730 |
| `GET /de/genie/`（页面本身，看 TTFB） | 6 | — | TTFB ≈ 3.47 | TTFB 3.54 |

#### 采样局限（必须与数字一起读）

1. **不是真实浏览器会话。** 没有 `X-WP-Nonce`、没有真实页面上的 `wp_rest` cookie，也没有浏览器侧的 TLS 会话复用。真实用户的首请求还包含导航与资源加载竞争，慢于此处的纯端点测量，不会更快。
2. **地理位置未知。** 采样机到 Hostinger 的 RTT 与业主浏览器不同；绝对数值不可直接搬到别的链路上，但**同机对照（`/wp-json/` 反而比 entry-context 慢）**说明瓶颈在 WordPress 冷启动而不在网络，因此相对结论稳定。
3. **TLS 握手失败是采样侧现象。** 几轮里出现过 `LibreSSL SSL_connect: SSL_ERROR_SYSCALL`，发生在高并发建立新连接时；未计入 200 样本。这本身也是「高并发下这条链路会掉」的旁证，但成因未进一步定位。
4. **第 1 次 30 路并发出现 8 个 HTTP 500。** 未取得响应体，未在服务端错误日志中找到对应条目（`~/error_log` 本次无相关记录）。成因未定，作为**待查风险**列出而非结论。第 2 次同条件 30 路全 200，所以不是稳定复现。
5. **样本量小。** n=29/30 的 p95 实际上是第 28–29 个序位值，尾部估计粗糙。

#### 判断：5000 ms 是否切实际

**不切实际。** 三条独立理由：

1. **它低于并发下的中位数。** 第 2 次 30 路并发 p50 = 4.742 s，只剩 258 ms 余量；p95 = 5.003 s 与阈值**完全重合**，max 已经越过。这不是「偶发超时」，是「并发一来就有一半流量贴着线走」。
2. **它贴着 WordPress 地板画线。** 同机最轻的 `GET /wp-json/` p50 = 4.533 s。任何需要启动 WordPress 的 REST 请求在这台主机上都不可能显著快于 4.5 s。为 entry-context 设 5 s 等于要求它比 `/wp-json/` 索引快 10%，而这没有任何工程依据。
3. **它比同一票域内其他预算都小，且小的那个已被证伪。** 同一插件的其他原生读取预算：`ARTIFACT_TIMEOUT_MS = 20_000`、`TURN_TIMEOUT_MS = 90_000`、`TURN_VERIFICATION_TIMEOUT_MS = 165_000`。entry-context 是最轻的一个（只算 HMAC，无模型、无数据库业务读取），却拿着最小的预算，而它继承自的那个 5 s 判断已被 `0a5a224c9` 的实测推翻。

---

## 3. 第 3 处：`request.ts` 的 detached status 永不回收

### 3.1 机制

`plugins/linker-tools/src/protection/request.ts`：

1. **第 108–115 行** `containerFor()`：`const slot = action === 'genie' ? ownedSlot?.() : undefined;`——**只有 `genie` 会尝试取 owner slot**。其余 action（含 `conversation_create`）的 `slot` 恒为 `undefined`。
2. **第 146–197 行** 建 DOM：新建 `div` + `p[role=status][aria-live=polite]`，挂 `linker:protection` 监听器，然后按有无 slot 分别插入到 slot 内、form 之前、或 `main`/`body` 末尾。**非 genie 的插入位置是普通 DOM，没有登记任何 owner。**
3. **第 151–183 行** 监听器分支：
   - `checking` / `interactive` / `retrying`：只改文案。
   - `ready`：清空文案。
   - `slot && action === 'genie'`（第 171–176 行）：`status.remove(); container.remove();` 并收合 slot 的 hidden。
   - **`else`（第 177–182 行）**：只把文案写成 `Verification could not be completed. No request has been sent in this attempt. Please try again.`，**不移除任何节点**。
4. **第 297–313 行** `finally`：只在 `verification` 命中 owned slot 时清 `status.textContent` 并隐藏 slot。非 genie 的 `verification` 挂在普通 DOM 上，`closest('[data-linker-resource-verification-slot]')` 返回 `null`，这段整体跳过。
5. **第 315–348 行** 成功路径：只有 `client.complete()` 返回真且 `verification` 处于 owned slot 时才 `status.remove(); container.remove();`（第 330–337 行）。非 genie 的 container 没有 slot，**成功路径也不回收节点**，只是清空文案。
6. **第 349–378 行** 失败路径：只调整 `operations` 里的 UUID，完全不碰 DOM。

### 3.2 `conversation_create` 的精确行为序列

`selectConversation()`（`plugins/linker-tools/src/genie/api/turn.ts:873-898`）以 `body: JSON.stringify( id ? { id } : {} )` 调 `resourceFetch`；`resourceAction` 对 `{}` 的 `/genie/conversations` 判定为 `conversation_create`（`request.ts:68-76`）。**它不传 `ownedSlot`** —— 全仓只有 `sendTurn`（`turn.ts:510` 起的 `resourceFetch(..., request.verification?.slot)`）传了。

于是：

| 步 | 发生的事 | DOM 后果 |
|---|---|---|
| 1 | 点「Neues Gespräch」→ `continueConversation()`（`App.tsx:1614-1629`）→ `selectConversation()` | — |
| 2 | `resourceFetch` → `containerFor('conversation_create', undefined)`；`slot === undefined` | 新建 `p[role=status]` + 空 `div`，插到 composer form 之前；登记进 `containers` / `statuses` |
| 3 | `client.proof()` 失败（Turnstile 300030 等）→ 抛 `verification_*` | proof 抛错前一般已派发 `interactive`/`retrying`，status 显示「Checking verification…」的对应德文 |
| 4 | `finally`：`verification` 有值，但 `closest('[data-linker-resource-verification-slot]')` 为 `null` | **不清任何东西** |
| 5 | 异常上抛到 `continueConversation` 的 `catch`（`App.tsx:1652-1658`）：仅 `setHistoryPhase('failed'); setOpen(true);` | App 自己的「历史加载失败」在历史面板里，**不是** `role=alert` 横幅，且不触碰这个 status |
| 6 | 监听器收到证明失败态，落入 `else` 分支 | status 文案变成「Die Prüfung konnte nicht abgeschlossen werden…」；**节点留着** |
| 7 | 业主再次 Senden → `ask()` → `sendTurn` → 新 `containerFor('genie', ownedSlot)` | genie 有自己的 slot，**不复用** `conversation_create` 的容器（`containers` 按 action 分键） |
| 8 | 此时 DOM 同时有：`conversation_create` 留下的 `p[role=status]`（失败文案）+ genie 槽里的 `p[role=status]`（「Die Überprüfung läuft …」） | **两条 `role="status"` 并存** |

这与工单描述的生产序列逐项吻合（验证失败 300030 → 问题退回输入框 → 再 Senden → 两条 status 同时可见）。

### 3.3 「问题退回输入框」是另一个人做的

退回输入框不是 `request.ts` 的行为，是 `App` 的 composer 恢复。所以第 3 处的症状是**两个互不知情的 owner 各自做对了一半**：App 正确恢复了草稿，`request.ts` 正确地报告了证明失败，但没人负责把这个 `request.ts` 建的节点收掉。这解释了为什么它不是「谁漏了一行」，而是「没有人被指派这个所有权」。

### 3.4 影响面比 `conversation_create` 更大

`resourceFetch` 的 8 个调用点里只有 `sendTurn` 传了 `ownedSlot`。其余 7 个（`readThread` turn.ts:674、planner bootstrap turn.ts:740、`listConversations` turn.ts:838、`selectConversation` turn.ts:879、`deleteConversation` turn.ts:914、邮件 turn.ts:1003、投票 turn.ts:1057）一旦 proof 失败或成功，都会留下节点。`listConversations`/`readThread` 是 GET（`resourceAction` 返回 `''`，直接透传，不建容器），所以实际暴露的是 `selectConversation`、`deleteConversation`、邮件、投票这 4 个写操作——`conversation_create` 只是因为业主走到了「新建会话」这条路才被发现。

### 3.5 测试覆盖

`plugins/linker-tools/src/protection/request.test.ts` 有 5 类断言，其中：

- 「only actual successful %s completion clears its verification status」只覆盖 `design/residential`、`roof/pack`、`report/pdf`（`test.each`），断言的是 `status.textContent === ''`，**不断言节点被移除**。
- 没有任何用例断言失败后 DOM 里 `[role="status"]` 的数量。
- 没有任何用例覆盖 `conversation_create`。

所以这个缺口既没被测到，也被现有断言的形状（只看 textContent）掩盖了。

---

## 4. 全仓盘点：还有哪些「未决即渲染失败文案」的同类表面

方法：在 `plugins/linker-tools/src/` 与 `apps/planner/src/` 里搜 `could not` / `konnte nicht` / `missing`，逐个读该处的状态来源，判定「未决」与「失败」在该处是否可区分。

判定标准：**该表面是否存在一个必经过渡态**——即值尚未取得时是否必然先渲染失败文案。

| 表面 | 未决时的渲染 | 判定 |
|---|---|---|
| `genie/components/GenieCard.tsx:84` | 首帧即「Genie could not load this product.」 | **是，同类缺陷**（本报告 §1） |
| `genie/components/EntryInbox.tsx:17` | `inbox.identityError` 为真才渲染；未决时不渲染 | 否，正确 |
| `genie/App.tsx:2797`（`draftContext.phase`） | `loading` → 「One moment…」+ `role=status`；`unavailable` → 「Genie could not load.」+ `role=status` | **否，这是正确的参照实现**：显式三态（`loading`/`ready`/`unavailable`），未决有自己的文案和 live region |
| `genie/App.tsx:3444`（历史栏） | `phase === 'failed'` 才渲染；`phase === 'loading'` 走别的分支 | 否 |
| `genie/App.tsx:2889 / 2936 / 3044 / 3053`（voice / refused / conflict / failure） | 各自由显式布尔或字符串状态控制 | 否 |
| `genie/components/AttachmentCard.tsx:57` | `card.failed` 为真才渲染 | 否（失败是服务端读图结果，有独立布尔） |
| `genie/components/TurnProgress.tsx:16` | `verificationPending` 为真渲染「Checking verification…」，是**进行态**文案不是失败 | 否 |
| `marketing/entries.ts:159 / 218` | 159 是 `catch` 里，218 是 `phase === 'failed'` 事件 | 否（但 159 的 `catch` 把「身份核验失败」「恢复写入失败」等多种原因压成同一句「Genie could not load.」，见 §5.4 附注） |
| `hero/Hero.tsx:690 / 782` | `EntryScopeError && changed` 分支，是确证的身份变化 | 否 |
| `hero/Hero.tsx:1226` | `draftContext.phase !== 'ready'` 时，`loading` 走「One moment…」，其余走「Genie could not load.」 | 否（与 App.tsx:2797 同一实现形态） |
| `configurator/roof/RoofStep.tsx:480/510` | `Status` 联合类型显式含 `loading: 'Loading the aerial image…'`，`error` 是独立成员 | **否，这是正确的参照实现** |
| `configurator/report/ReportView.tsx:168/190/196` | `PdfState` 联合（`idle`/…/`failed`），`role=status` 里按成员渲染 | 否 |
| `configurator/residential/ResidentialPanel.tsx:469` | `Suspense fallback` 渲染「Loading the map…」 | 否 |
| `configurator/solution/Solution.tsx:161` | `if ( ! selected ) return null;` | **不是失败文案**，返回 `null` 即不渲染；虽然同样是「未决即空白」，但不产生错误文案，属另一类（空白）问题，不在本票范围 |
| `configurator/publication.ts:13 / 20` | 由调用方的显式状态决定 | 否 |
| `genie/components/EmailConversation.tsx:189 / 266` | `switch` 的结果态 | 否 |

### 盘点结论

1. **`GenieCard.tsx` 是唯一「首帧即失败文案」的组件。** 仓库里另外两处同类问题（RoofStep、ReportView）都已经用显式状态联合类型解决，`App.tsx:2797` / `Hero.tsx:1226` 的 `draftContext.phase` 三态是 Genie 内部的正确参照。GenieCard 是这批里唯一的例外，且它**没有测试**（§1.5）。
2. **`request.ts` 的第 3 处不是「文案」问题，是 DOM 所有权问题**，因此上面这张按文案扫出来的表抓不到它——需要用「有没有 owner」这个维度单独查，见 §3.4。
3. `Solution.tsx:161` 的 `return null` 是「未决即空白」，不会误导客户，本报告只记录不列为缺陷。

---

## 5. 修法决策材料

### 5.1 正确的状态模型

三处需要的共同模型是**把「未决」「失败」「已取消」分成三个不同的事实**，且取消不是失败：

```ts
type Load<T> =
    | { phase: 'loading' }
    | { phase: 'ready'; value: T }
    | { phase: 'failed'; retryable: boolean }
    | { phase: 'cancelled' };   // 客户离开/切换，不是错误
```

对照第 1 处，`GenieCard` 当前是 `StoreProduct | null`，压掉了 `loading` / `failed` / `cancelled` 三态。改后 `null` 不再有任何含义，`! product` 这个写法从类型上就不成立。

**这个模型仓库里已有两个可复用的先例**，不需要新发明：`RoofStep` 的 `Status` 联合（`loading` 与 `error` 并列成员）与 `draftContext` 的 `'loading' | 'ready' | 'unavailable'`（`App.tsx:2797`）。

### 5.2 各态应有的文案与 live region

| 态 | 文案 | ARIA | 依据 |
|---|---|---|---|
| `loading` | 无文案，或与卡片同尺寸的骨架 | 无（首帧骨架不该播报） | 仓库既有 `skeleton` 用法见 `TurnProgress.tsx:35-41` |
| `ready` | 卡片正文 | 无 | — |
| `failed` | 「Genie could not load this product.」+ 重试 | `role="alert"`（真失败才播报） | 现有文案保留，只是不再用于未决 |
| `cancelled` | 无文案，静默移除 | 无 | 与 `resourceFailure.ts:34-37` 的 `isVerificationCancellation` 一致：撤回不是失败 |

关键点：**`loading` 不能使用 `role="status"`。** `aria-live` 会在每次卡片进入视口时播报「加载中」，对一个正常 1–3 s 的往返是噪音。真失败才用 `role="alert"`。这与第 3 处的问题相反：第 3 处是「用 `role=status` 承载了失败」，这里是「不要用 live region 承载正常的等待」。

### 5.3 5000 应该改成什么依据

**不能改成另一个拍出来的数字。** 预算应绑定到一个真实约束。可选约束按强度排序：

1. **绑定服务端自己的等待上限（最强）。** entry-context 的服务端路径最长的一次阻塞是 `BROWSER_CLAIM_LOCK_SECONDS = 1`（`Conversations.php:86`）。完整路径 = 命名锁等待 + `GET_LOCK` 两次往返 + `add_option`/`get_option` + HMAC。客户端预算必须 **严格大于** 这条路径的最坏值，否则服务端还没返回，客户端已经 abort——那正是 #563 记录的现象（`5004.7 ms, responseStatus: null`）。
2. **绑定同主机同层级的既有预算。** `ARTIFACT_TIMEOUT_MS = 20_000` 是同一插件给「读商品元数据」定的原生读取预算，其后端是 `AbilityClient`（真正查数据库、跑 Woo 价格门）。entry-context 只算 HMAC，**不会比它贵**，所以没有理由拿比它小 4 倍的值。
3. **绑定实测分布。** 本次实测最差条件（30 路并发）p95 = 5.003 s、max = 5.030 s；加上「真实浏览器还会更慢」的保守余量。

三条指向同一结论：**5000 太小，20 秒与既有原生读取预算一致且明显覆盖实测最坏值。** 具体取值属实现决策，本报告只主张「必须 ≥ 并发 p95 的实测值并留余量，且与 `BROWSER_CLAIM_SECONDS` 成组修改」。

**必须一起改的：**

- `Conversations::BROWSER_CLAIM_SECONDS`（当前 5）——语义就是客户端预算，不改会导致冷 mint 去重失效（§2.2）。
- `Conversations::BROWSER_CLAIM_LOCK_SECONDS`（当前 1）——应保持显著小于新的客户端预算；1 s 相对 20 s 仍是合理的小值，可不改。
- `docs/specs/13-genie.md` 第 166 行那句「身份核验保留独立的 5 秒预算」。
- `nativeScope.ts:19` 的注释 `Existing auxiliary metadata deadline`——它现在描述的是一个不存在的继承关系（被继承方已改成 20 s）。

**另一个独立问题（不在本票范围，但要写下来）：** 5000 ms 在安静态也只比 p95 高 1.6 s，而 `/wp-json/` p50 就有 4.53 s。真正的根因是这台主机的 WordPress 冷启动 ~4.5 s。把预算放大只是让前端不再误报，**用户的等待仍然是 3–5 s**。#563 只修了服务端锁，没有触及冷启动成本。这是本报告顺带记录的一个未解决问题，不属于 #901 的三处根因。

### 5.4 第 3 处：清理应挂在哪个生命周期

**结论：清理必须挂在 container 自己的 owner 上，与 `displayOwners` 同一层，而不是 `resourceFetch` 的 `finally`。**

理由：

1. `resourceFetch` 的 `finally` 已经在做 owner 检查（`displayOwners.get(verification) === displayOwner`），说明这个文件已经选定了「container 归它最后一次写的人所有」这个模型。缺的不是新机制，是**这个机制只为 genie 打了洞**（`containerFor: line 112` 的 `action === 'genie'` 判定）。
2. 把清理挪到 `finally` 会误伤：`finally` 在 `fetcher` 返回后立刻跑，但此时 response body 可能还没读完，节点收早了会丢掉 proof 完成后的状态。真正该收的时机是**这次 attempt 确定结束**——即 `linker:protection` 收到终局态（失败/取消）时，或 response 已完整交付且 `client.complete()` 已消费 proof 时。
3. 因此最小改动是：**让所有 action 都拥有 owner 语义**，把第 171 行的 `slot && action === 'genie'` 条件放宽为「本次 attempt 仍是这个 container 的 owner」，在失败/取消终局态移除节点（有 slot 时同时收合 slot），并让第 330–337 行成功路径同样对所有 action 生效。

同时应补的测试（当前完全缺失，见 §3.5）：

- 非 genie action（`conversation_create`）proof 失败后，`document.querySelectorAll('[role="status"]').length` 必须回到尝试前的值。
- 同一 action 连续两次失败，不得累积出两个 status。
- 失败后再次发送，DOM 里 `[role="status"]` 只有本次 attempt 的那一个。
- 现有断言不能只看 `textContent === ''`——那正是掩盖缺口的形状，要改成断言节点存在性。

**附注（`marketing/entries.ts:159`）：** 首页入口的 `catch` 把身份核验失败、恢复写入失败、投递失败等多种原因统一写成「Genie could not load.」。这不是「未决当失败」，但属于同一族「错误文案丢失原因」的问题：客户无法据此判断该重试还是该换页面。不在本票三处根因内，记录供后续合并处理。

---

## 6. 未解决项与局限

本报告是研究交付，**没有改任何代码**。以下事项明确没有做完：

1. **第 1 次 30 路并发的 8 个 HTTP 500 未定位。** 无响应体、服务端 `~/error_log` 无对应条目。第 2 次同条件全 200。属待查风险，不是结论。
2. **没有真实浏览器会话的测量。** 本次用 curl 无 nonce、无 cookie 的直连。真实浏览器首请求（含导航、nonce 获取、资源竞争）应当更慢，本报告的 p95 是**下界**。
3. **#563 的生产读回状态未知。** 那份验收文档自己写着 *"Production deployment and browser readback remain required before this fix is complete."* 本次没有核实它是否已部署读回。
4. **`BROWSER_CLAIM_SECONDS` 改成 20 秒后的副作用未评估。** 窗长变长意味着「同一 tab 的无 cookie 请求」在一个更长的时间窗内共享同一 browser key；这对匿名访客的身份收敛是更宽松的语义，但会改变「cookie 未落地」这段窗口的长度。本报告只指出「必须成组修改」这条硬约束，没有做行为影响分析。
5. **`/wp-json/` p50 = 4.53 s 的根因未查。** 这是 Hostinger 上 WordPress 冷启动的真实成本，影响所有 REST 端点。本报告只用它做对照，没有深入。
6. **`Solution.tsx:161` 的 `return null`** 是「未决即空白」，已记录但判定不在本票范围。

## 7. 报告用到的证据位置

| 主张 | 位置 |
|---|---|
| GenieCard 首帧失败 | `plugins/linker-tools/src/genie/components/GenieCard.tsx:60,63-82,84-90` |
| Store API 把非 2xx 压成空数组 | `plugins/linker-tools/src/configurator/api/store.ts:87-98` |
| `CardState` 已有状态语汇 | `plugins/linker-tools/src/shared/ProductCard.tsx:21` |
| GenieCard 的两个调用点 | `plugins/linker-tools/src/genie/App.tsx:2686`、`plugins/linker-tools/src/hero/Hero.tsx:1093` |
| 5000 的引入与依据 | `eb097915d`；`docs/specs/13-genie.md` 该提交的 diff |
| 商品元数据 5 s → 20 s 的推翻 | `0a5a224c9`；`plugins/linker-tools/src/genie/api/product.ts:75-80` |
| 服务端两个常量跟随客户端 | `plugins/linker-tools/includes/Genie/Conversations.php:66-86` |
| 生产 5004.7 ms 记录与 #563 局限 | `docs/acceptance/2026-10-30/563-entry-context-deadline/README.md` |
| `containerFor` 的 genie 专属判定 | `plugins/linker-tools/src/protection/request.ts:108-115` |
| 非 genie 的 else 分支只改文案 | `plugins/linker-tools/src/protection/request.ts:171-182` |
| `finally` 只清 owned slot | `plugins/linker-tools/src/protection/request.ts:297-313` |
| 成功路径只对 owned slot 移除节点 | `plugins/linker-tools/src/protection/request.ts:315-348` |
| `conversation_create` 的判定 | `plugins/linker-tools/src/protection/request.ts:68-76` |
| `selectConversation` 不传 ownedSlot | `plugins/linker-tools/src/genie/api/turn.ts:873-898` |
| 只有 `sendTurn` 传 ownedSlot | `plugins/linker-tools/src/genie/api/turn.ts:510`；其余 7 处在 674/740/838/879/914/1003/1057 |
| `continueConversation` 的 catch 不碰 DOM | `plugins/linker-tools/src/genie/App.tsx:1652-1658` |
| 正确的三态参照实现 | `plugins/linker-tools/src/genie/App.tsx:2781-2800`、`plugins/linker-tools/src/hero/Hero.tsx:1212-1230`、`plugins/linker-tools/src/configurator/roof/RoofStep.tsx:45,479-511` |
| 撤回不是失败 | `plugins/linker-tools/src/genie/shared/resourceFailure.ts:10-37` |
| 既有预算对照 | `plugins/linker-tools/src/genie/api/product.ts:76`、`plugins/linker-tools/src/genie/api/turn.ts:285,297` |
