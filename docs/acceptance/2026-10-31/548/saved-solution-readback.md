# 已保存方案恢复入口 · 生产读回（#548）

日期：2026-10-31 · 生产 `de-linker.com` · 视口 390×844

## 结论

契约成立，**未完成登录态读回**。本次只证明了访客路径与数据契约；以记录作者身份打开恢复入口的真实读回仍未执行，因为浏览器会话不是 `857558227@qq.com` 的登录态。

## 生产数据事实

`linker_solution` 全站只有 1 条记录（`wp_posts` 查询）：

| 字段 | 值 |
| --- | --- |
| ID | 8207 |
| 标题 | `SAJ BU2-5.0-HV1` |
| 状态 | `private` |
| 作者 | `1`（`857558227@qq.com`，administrator） |
| 创建 | 2026-10-22 15:55:22 |
| `_linker_solution_design` | 150 bytes，`kind=residential`，`input` 是 JSON 对象 |
| `_linker_solution_items` | 34 bytes，1 元素数组 |

`SavedSolutionSource::read()` 的五个拒绝条件全部不成立（post_type / post_status / author / `kind` 是字符串 / `input` 是对象 / items 是数组），因此该记录**在作者登录时会被正常读出**。

## 实际读回

打开 `https://de-linker.com/solution-configurator/?saved_solution=8207`，390×844，未登录：

```
Your projects
Site information, roof layout and system planning belong to the same project.
The saved inputs could not be loaded in this session.
Try again   Continue without these inputs
Saved projects
Production Roof Acceptance 1946   Revision 12 · Oct 30, 2026
Guest projects are available in this browser session. Signing in links them to the account.
```

判定：**符合设计**，不是缺陷。

- `SavedSolutionSource::read()` 在 `'user' !== $principal->kind` 时返回 `404 saved_solution_unavailable`。
- `SavedSolutionStart` 收到 404 后渲染 "The saved inputs could not be loaded in this session."；只有 401/403 才触发 `recheck()`。
- 确认未登录：同一会话打开 `/my-account/` 显示 Sign in 表单；页面自身也声明 "Guest projects are available in this browser session"。

## 未验证项（如实保留）

- **登录态下的真实恢复**：需要用 `857558227@qq.com` 登录后重开 `?saved_solution=8207`，确认进入新工作台、`Original inputs` 折叠区可下载 JSON、且不导入旧快照价格/公式/产品事实。
- **访客转账户 claim**：`SavedSolutions` 的 48 小时会话 claim 路径未在本轮生产读回中触发。

## 实现契約（供后续读回对照）

`SavedSolutionStart.tsx` → `NewProject` 携带 `saved_solution_reference`；`SavedSolutionReference.tsx` 只在 `authority === "historical_user_input"` 时渲染，且只提供原始输入 JSON 下载，不含旧价格与产品事实。

## 登录态读回（2026-10-31 补充，已完成后半段）

此前本节记为未验证。现已在生产上以记录作者身份直接调用
`SavedSolutionSource::read()` 完成读回。

调用方式说明：`sources/saved-solution` 是**网关层路径**，由
`Gateway.php:302` 转给 `SavedSolutionSource`；`Transport` 直连引擎时该路径不存在，
直接打引擎会得到 `not_found`。因此本次直接调用 PHP 类，并先 `wp_set_current_user( 1 )`。

作者（user 1）读回：

```
title=SAJ BU2-5.0-HV1
kind=residential
recorded_items=1
input keys: locale, plz, annual_kwh, pv_kwp, phase, backup, heat_pump, electric_vehicle
source_sha256: 6dfee710c8f17869…
```

`input` 只含客户原始输入字段，**不含**旧快照价格、公式或产品事实，符合
`SavedSolutionSource` 的设计（"Only original customer inputs and recorded IDs/counts
cross this seam"）。

### 权限边界

另建一个临时 `customer` 用户后以该身份读取同一记录：

```
other-user code=linker_planner_saved_solution_unavailable status=404
```

拒绝而非泄露。临时用户已在同一请求内删除，复核生产上 `ss-probe` 前缀用户数为 **0**。

### 仍未验证

浏览器内以该账号登录后打开 `?saved_solution=8207` 的**界面**读回（恢复后进入新工作台、
`Original inputs` 折叠区可下载 JSON）。本次验证的是数据与权限层，不是界面。

### 界面读回：当前无法验证，缺一个登录凭据

要验证「登录后打开 `?saved_solution=8207` 进入新工作台并看到 `Original inputs` 折叠区」，
需要一个能登录 user 1 的浏览器会话。

现状与判断：

- 浏览器会话是访客，因此页面正确显示 "The saved inputs could not be loaded in this session."
  （`SavedSolutionStart` 对 404 渲染该提示，只有 401/403 才触发 `recheck()`）。
- 生产 `wp-content/mu-plugins/` **没有**一次性登录插件。`linker_local_login_url`
  只存在于 `tools/local/mu/001-linker-local-login.php`，属本地实例工具。
  生产没有它是**正确的**，我不会为了完成验收而给它装一个后门。

界面层的静态证据（不能替代真实读回）：

- `Workspace.tsx:249`：`savedSource !== null` 时挂载 `SavedSolutionStart`；
- `SavedSolutionStart` 用 `sources/saved-solution` 取数，并据状态码决定提示与否；
- `SavedSolutionReference` 只在 `authority === "historical_user_input"` 时渲染，
  且只提供原始输入 JSON 下载，不含旧价格与产品事实。

数据与权限层已验证（见上一节）；**渲染与交互未在真实浏览器中读回**。

解除方式（二者其一，由业主决定）：

1. 提供 user 1（`857558227@qq.com`）的登录凭据；
2. 授权在生产临时启用一次性登录插件、完成读回后立即移除。

在满足其一之前，此项保持未验证。
