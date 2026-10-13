# 账户与认证边界验收（t110，2026-10-13）

业主问："输错密码、忘记密码、表单校验、客户后台的各种操作——有没有测过？"此前**没有**成体系的证据（验收矩阵里这些行一直是 unverified）。本记录就是补上的那套：`tests/e2e/specs/account.spec.ts`，**7/7 通过（47.3s）**，可重跑：

```bash
cd tests/e2e && LINKER_E2E_INSTANCE=t110 npx playwright test specs/account.spec.ts
```

## 覆盖与实测行为

| # | 用例（EN 与 DE 各跑一份的标了双） | 实测行为（断言即证据） | 截图 |
|---|---|---|---|
| 1 | **输错密码**（EN+DE） | 提交错误密码 → 表单自己的 `.woocommerce-error` 出现、访客停留登录表单、未建立会话 | `en-wrong-password.png` / `de-wrong-password.png` |
| 2 | **忘记密码**（EN+DE） | 重置请求表单在位；填账号提交 → 答讯出现、无错误（已存在账号不被拒） | `en-lost-password.png` / `de-lost-password.png` |
| 3 | **注册表单校验** | 客户端约束在位（email 类型/必填）；坏邮箱 `x@y`（浏览器接受、站点拒绝）由**服务端**拒绝并回错误通告 | `en-register-invalid-email.png` |
| 4 | **账户详情保存 + 登出** | 只填名字 → 服务端答 "Last name is a required field."（校验真实存在）；补全后保存成功、重载回读；登出走菜单真实链接（带 nonce）→ 回到登录表单 | `en-account-details-saved.png` / `en-signed-out.png` |
| 5 | **公司资料保存**（/my-account/company/billing/） | 必填逐项被拦（街道/邮编/城市）；补全后保存成功、重载回读公司名 | `en-company-saved.png` |
| 6 | **新账号空态** | 询盘 "No inquiries yet."；Documents "Your Proforma invoices and the design reports of your saved solutions will appear here."；Saved solutions "Solutions you save in the Solution Configurator appear here…" | `en-inquiries-empty.png` / `en-documents-empty.png` / `en-saved-solutions.png` |

两条实现事实（已写进 spec 注释，避免下次误判为缺陷）：
- **Company 页地址是 `/my-account/company/`**——账号端点整体改过名（`orders→inquiries`、`view-order→inquiry`、`edit-address→company`）；旧的 `/my-account/edit-address/` 404 是改名的结果，不是断链。
- 注册按钮在这套构建里需**键盘提交**（指针 click 不触发表单提交，commerce.spec 已有同样的注记）。

## 尚未覆盖（诚实清单，按重要性）

1. **VIES 增值税号实时校验**的两态行为（校验失败可提交但标记 / 校验服务超时）——注册链里的公司步没有 e2e。
2. **审批后台的完整操作**：commerce 链跑通了"批准"路径；`restrict`/`reject` 的后台操作与两种拒绝邮件未进 e2e（邮件单测覆盖了三封的模板）。
3. **有数据态**：Saved solutions 加入/移除（配置器侧）、Documents 列表有行、询盘详情四态——部分由 commerce 链与人工实拍覆盖，未自动化断言。
4. **德语注册向导的逐步校验**（DE 侧目前只覆盖错密码/忘记密码）。
5. 账户端点页上的**语言切换**行为（EN↔DE 保持当前端点）。

这些随下一轮（账户区仪表盘重做）一并补进 e2e。
