# Genie 首问静默丢弃缺陷（生产实证 2026-11-07）

## 现象（客户可见）

在 de-linker.com 德语首页（也复现于 EN 首页一次），打开 Genie dock 后输入问题并回车：

- 输入框里的文字**视觉上消失**
- 回车**无任何反应**：无发送、无错误提示、无等待指示
- 问题不进入对话列表；直到整页刷新前，后续发送全部被吞
- 刷新后 dock 显示 "Bisheriger ungesendeter Entwurf"（前次未发送草稿）恢复区（EN: previous unsent draft），点击 "Bisherigen Entwurf wiederherstellen" 可把问题放回输入框——输入并未永久丢失，但**当场无任何可达反馈**

## 复现（3 次干净复现，签名一致）

方法：业主真实 Chrome（WebBridge）→ de-linker.com/de/ → 点 dock → key_type 输入 "Welche Batterie passt zum GW10K-EHA-G20?" → 真实 Enter（send_keys）。已排除合成事件伪影（全部真实键盘事件）。

签名（三次一致）：
1. composer 清空；无 /genie/turn 出站请求（fetch 全量日志实证）
2. 无 TurnProgress 行（MutationObserver 全程无 "Checking verification/thinking" li 出现）
3. 无失败记录落盘（sessionStorage turn-failure store active=null 或 kind=null 的发送预留）
4. Enter 瞬间有 0-2 个 entry-context 请求，全部 200，scope 全程稳定（017854b5cd1362cc…，四次相同）
5. EN 线同会话早前 turn 正常（Q4 智能电表问成功获得真实答案），故非账号/信任问题

对照：早前 EN Q3 一次同样签名（当时疑为合成事件伪影）；EN 正常 turn（Q1/Q2/Q4）走完整链路成功。

## 根源（代码级）

1. **composer 受控值绑定**（`plugins/linker-tools/src/genie/App.tsx` ~3199）：
   `value={ draftContext.phase === 'ready' ? input : '' }`
   draftContext 任何重新校验（phase→'loading'）都会让输入框**渲染为空**——用户正在打的字视觉消失。校验的隔离意图（"Revalidation quarantines already mounted text"）保护的是换身份后的旧文本，但把**同一身份的瞬态校验窗口**也当成隔离条件，误伤正在输入的真人。
2. **ask() 静默早退**（App.tsx ~1128）：`const lease = draftContext.capture(); if ( ! lease ) { return false; }`
   phase!=ready 时 capture()=null，回车被吞，无提示、无排队、无校验完成后重试。
3. **enqueue 失败路径 sending 标志可能不复位**（App.tsx ~1196-1200 等）：所有权失效（owns=false）时 `sending.current = false` 不执行且 retainUnverifiedTurn 同样 no-op——一旦进入该分支，后续所有发送静默被吞直到刷新。

## 影响

- 违反业主第一原则（真人零阻挡零无反馈）与 coverage contract "普通自主输入…失败…可达的恢复路径"。
- 触发面：dock 打开后任何 draftContext 重新校验窗口内的输入/发送（德语首页复现率高；EN 亦见一次）。

## 修复要求（按根源，不是补丁）

1. 瞬态校验（同身份 re-verify）期间 composer **不得清空用户文本**；隔离只在身份/scope 实际变化时执行（invalidate/dispose 已有该语义）。
2. ask() 在校验进行中时**不得静默吞 Enter**：给可见等待状态，并在校验完成后继续发送（或明确失败提示 failureText）。
3. enqueue 所有退出路径保证 `sending.current` 复位（finally），失败保留输入并显示失败句。
4. 回归测试覆盖：校验窗口内输入/发送、校验后自动继续、身份切换隔离仍生效。

## 证据

- 复现日志与时间线：本会话 wire.jsonl（compaction 后窗口）；关键快照已摘录于上
- 关联验证事实：12h 信任（Trust.php）生产实证有效；挑战流程实证（失败→重试→自动通过→答案）；product-add→Woo draft 读回通过；history-and-restore 通过——见 genie-live-turns-20261107.json
