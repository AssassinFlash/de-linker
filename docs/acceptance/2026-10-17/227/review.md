# 全量 diff 评审与修复

2026-10-17，Spec、Standards 两名独立只读评审代理分别检查实现相对 `00363e699c959a7d4224753dd360da2c54358473` 的全部 diff。随后分支 rebase 到 `613b526ec2275148bf8482bd6e988f9cad8d1ae0`，该主线增量仅为 kickoff 规则说明。两路评审都知晓最新快照、通知模板与线上批准是未通过的外部门槛。

## Spec

| 发现 | 修复与验证 | 定向复核 |
|---|---|---|
| P2：Approved 筛选中，同一抽屉把账户限制再批准，历史行仍然隐藏。 | 每次保存都重新计算 `row.hidden`。真实浏览器新增 Approved → Restricted → Approved，分别断言隐藏及重新显示。修前 EN 1440 在恢复显示断言失败，DOM 为 `<tr hidden>`；修后重新运行四组语言/视口。 | 原评审代理确认修复与回归覆盖闭环。 |
| P3：仪表盘标题缺原型裁定的 `(N)`。 | 标题加入与菜单、顶栏共用的 `data-linker-account-count`；真实夹具检查初始数，浏览器检查批准后标题和顶栏同步递减。 | 原评审代理确认闭环。 |

新增的 390px 回归进一步发现 WordPress 移动表格 `display` 规则覆盖浏览器对 `hidden` 的默认处理。账户历史作用域内显式隐藏 `tr[hidden]`；同一回归直接检查最终可见性。

最终键盘路径还用 Computer Use 复现：已批准筛选中将账户限制，原行隐藏后 Esc 关闭抽屉，原触发链接不能接收焦点，`activeElement` 落到 BODY。关闭逻辑现只把焦点交还仍连接且可见的原入口；原入口被筛选移除时回到始终可见的顶栏审核入口。四组浏览器回归均在隐藏原行后关闭抽屉并断言顶栏收到焦点。

## Standards

唯一发现是 P2 文案评审记录尚留“待补齐”的占位句。已将实际 EN/DE 对抗意见、逐项定稿处置与 `.po` 权限句订正写入 `copy-review.md`。原 Standards 评审代理复核确认“初稿 → 意见 → 定稿”链条完整，缺口闭环；未发现实质性代码异味、原生机制绕行或旧代码回流。

## 旧代码检查

对新 Registration 模块、后台 React 源码、新真实夹具与新浏览器用例执行：

```sh
rg -n 'tv_b2b_|Linker_AI_|dlk-' \
  plugins/linker-commerce/includes/Registration \
  plugins/linker-commerce/src/accounts \
  plugins/linker-commerce/tests/php/Integration/AccountsAdminTest.php \
  tests/e2e/specs/accounts-admin.spec.ts
```

无匹配。结构核查：插件启动工厂确实实例化并注册新模块；实际后台挂载原生 dashboard / admin bar / list table；唯一状态写入仍是既有 `Approval`；User Switching URL 来自已安装插件，注册资料来自当前 Fields 与 Woo 存储，不携带原型数据或旧实现代码。先证后删另见 `parity-before-replacement.md/json`。
