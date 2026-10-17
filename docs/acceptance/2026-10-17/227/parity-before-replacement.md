# 替换旧审批入口前的对等承载证据

2026-10-17，独立实例 a227，完整 20261015-1852 快照。最新快照装载被同步票正在修复的 VECTOR KEY 兼容问题挡住，本记录是通道替换证据，不代替重拉后的最终视觉验收。

- 此时用户列表与资料页原审批入口仍注册，见 parity-before-replacement.json 的 legacy_hooks_present=true。
- 实际 WordPress/Woo 测试同时运行原审批夹具和新 AccountsAdminTest，覆盖状态/原因、审计、价格权威、拒绝登录与客户邮件队列。
- Computer Use 在真实后台通过 focus=65 依次执行批准、限制和拒绝；原因写入并显示；再从已处理账户进入 User Switching，以客户身份看到网站，并用插件的 Switch back 返回员工后重新打开同一申请。
- 员工语言切为 de_DE_formal，通过 focus=66 执行限制、再批准；卡片的国家、业务类型、状态、检查、字段标签与操作反馈均为德语。客户原因在 Outbox，见 JSON。
- 发信后的语言保持问题用 test_staff_language_applies_to_all_card_values 复现并修复：邮件钩子重载域后，响应在独立员工语言作用域内渲染。LocaleSwitch 只弹出自己实际压入的语言栈。

新通道行为已对等承载后，才将用户列表/资料页旧操作改为新审核页链接，并删除原 GET 写入和资料表单写入处理器。状态列与普通 WordPress 资料编辑保留。
