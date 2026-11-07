# dynamic-routes 族生产验收（2026-11-07）

证据：`dynamic-routes-20261107.json`（rewrite 清单、404/搜索/归档 HTTP 实测）、`inquiry-received-key-states-20261107.json`（部署 a052d6875 后三 key 状态浏览器实测）。

## 收口状态（16 行 closed）

- **404-unknown-route-and-locale**：确认未占用路径 EN/DE 均 404 无跳转。
- **public-search-query-and-pagination**：`?s=` 实词/空结果/第 2 页 200，越界第 99 页 404，DE 搜索 200。
- **public-archive-discovery-and-applicability**：author 档 404、年份档 301 回首页、月份档 404、tag 基址 404——无意外公开归档暴露。
- **inquiry-detail-and-received-key**：本族执行中发现真实缺陷并修复（PR #985，deploy a052d6875）——错误/缺失 key 原先渲染 HTTP 200 + 空白卡（Woo 失配分支唯一内容被我们的 CSS 隐藏，且默认文案对无效链接是假话）。修复：Labels 按 `$order` 分支（有效=原成功文案；false=诚实失败态，指引确认邮件与 sales@de-linker.com）+ CSS 仅在无订单概览时取消隐藏。生产复测：错误 key EN/DE、无 key EN 全部显示可见失败态文案；正确 key EN/DE 仍为邮箱验证门，行为不变。

## 未收口（12 行 pending）

- **account-direct-endpoint-and-refresh**、**password-reset-token-states**：需要真实账号 fixture（登录态/重置 token 各状态），属账号链（authentication/account families）执行面；届时随该线一并跑。
- **retired-alias-redirect-and-language**：需要逐条核实当前实际启用的旧 slug 别名（rewrite 清单已归档，待与旧 URL 库比对）。
