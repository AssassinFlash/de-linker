# #222 · 待审账号保持登录，只是不显示价格

本目录的证据按 `verification.md` 组织；`gates.json` 是机器可读的运行记录。

## 第二轮评审（2026-10-18）修正

- **草稿页文案**（Spec 评审第 1 项）：`DraftSummary::guest_totals()` 对已登录但未批准的账号不再打印"没有账号？注册"（注册页会把该账号送回账户页）；pending 与 restricted/rejected 各自读自己的状态句，只保留"发送询盘"。新增 `test_pending_and_restricted_accounts_read_their_state`（三种状态）。
- **规格同步**：`11-commerce.md`（pending 不再整页门禁）、`13-genie.md`（价格行原句）、`split-login-register.md`（PendingGate 描述）、`184-account-chain.md`（测试类名）、`AdminAccessNotice` 注释。
- **模板目录**：两条新德语句子已入 `.po`/`.mo`，`i18n-coverage` clean。
- 价格夹具 `services/genie/tests/fixtures/prices.json` 是 2026-10-17 的抓取快照（当时账号文案为旧句）；服务测试验证的是"原句透传"。等三态夹具账号在实例上重建后用 `eval/prices/capture_prices.py` 重抓，届时夹具与现行文案一致。

## 仍待完成（不变）

- 线上注册 → 审批实走（合并部署后）。
- live/local 绝对像素门：本分支 vs 纯 main 为 16/16 零差异；四条 DE 1440 页头差异在纯 main 上同样存在（#229）。
