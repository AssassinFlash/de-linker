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
