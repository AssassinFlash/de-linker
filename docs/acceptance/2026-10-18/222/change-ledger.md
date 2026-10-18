# 待审账号保持登录 · 裁定变更台账

| 客户可见变更 | 裁定 | 边界 |
| --- | --- | --- |
| 账户页由整页审核卡改为完整工作台中的审核状态卡，保留导航、联系卡及端点内容 | 业主 2026-10-17：待审账号保持登录，只是不显示价格 | pending 与 restricted 账户；卡片复用线上设计，h2 标题，LC 组合、WindPress 样式 |
| 价格短提示补足审核状态 | 同一裁定与票的产品页审核提示要求 | EN `Account under review. Prices after approval.`；DE `Ihr Konto wird geprüft. Preise nach Freigabe.`；使用既有 CommerceState 的 approval 原因，不改价格规则 |

待审工作台新开放后，询盘概览、列表和详情的总额直接读取 CommerceState / PriceDisplay 的同一个金额规则；待审时不显示金额（含无价询盘原先显示的 €0.00）。

询盘入口、注册确认及批准邮件、approved 工作台、guest 登录与注册界面、注册确认及批准邮件均沿用现有合同。像素结果按真实测量另行记录，未声明差异不得记为通过。

第一轮补充裁定：restricted 账户页与 pending 共用局部状态卡，显示 Access currently limited / Restricted 及员工保存原因，复用询盘页 #246 的措辞。批准客户的旧无价询盘在行、概览与详情均隐藏总额；有价询盘行为保持。以上差异属于本票裁定范围。
