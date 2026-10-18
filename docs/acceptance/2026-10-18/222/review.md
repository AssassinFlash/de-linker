# #222 第一轮修正 · 全量 diff 双评审

固定基线 `origin/main = 0fddf100`，独立评审 HEAD `1581ac4c`，命令 `git diff origin/main...HEAD`。Spec 与 Standards 使用两个独立上下文，只读完整 diff、AGENTS、当前规格与 Claude 第一轮评审。修正见 `c19fa58d` 的后续提交链（以 git log 为准）；最终测试和运行时证据见 verification.md。

## Standards

**0 项文档规范违规；1 项 P3 判断项，已修正。** restricted 同时加入 warning 与 danger 两个连续选择器，前者立即被覆盖。已移除重复选择器，保留既有 danger 状态样式。

原生 Woo 内容 hook、LC 组合、WindPress 样式、PHP 转义数据、同模块直接共用金额规则、共享夹具进入 PHPCS 均符合 AGENTS §4/§5。`PriceDisplay::reason_text()` 只映射原因，pending 文案只有一处映射。

旧代码缺失检查：新增可执行 diff 无 `tv_b2b_`、`Linker_AI_`、`dlk-` 实现；已有 `tv_b2b_product_mode` 是不变的数据兼容键。结构比较确认删除整页模板替换、静态适配器、端点重定向和模板抢占，改为原生内容 hook。引擎、翻译器、NLU 实现无变化；无新模型通道、inline style、snippet 或运行时模板接管。

## Spec

**1 项行为发现，已修正；无范围扩张。** 原生询盘详情对已有价格的历史行会直接返回金额，账号由 approved 改为 restricted 后仍可读行价，违反规格 184 的“restricted … 价格隐藏”。pending/restricted/guest 三条失败测试先复现（3 failures），随后让该出口读取 CommerceState 当前原因。针对性 **51 tests / 154 assertions** 通过；真实 Woo 新夹具证明批准时有价，限制后原详情行价与总额同时隐藏。

其余第一轮要求的代码实现无遗漏：正常账户内容前的局部卡、pending/restricted 共用组件、保存原因位于联系信息之前、列表/概览/详情共用总额规则、历史无价原因由 CommerceState 决定、共享夹具只清理自己的记录。

**独立 EN/DE 文案复核无修改意见。** pending 短句准确描述当前审核与之后价格权限，不要求再次登录，不承诺审核时限。restricted 卡使用 #246 的英文与德语 Sie 体条目，明确询盘可用，员工原因转义原文输出。

## 第一轮裁定与最终门槛

run10 按 Claude 第一轮裁定关闭为本地共享 Redis 故障，非账号代码缺陷，规格 184 和 17 已同步。POT/PO/MO 经正式命令重新生成，先前的手工追加状态不再作为交付目录。中间 run8–14、reboot15/16 原始 JSON 已移除。

真实 WordPress、Computer Use、Genie、像素实测和目录比较分别保留实际结果；没有把静态实现或通过次数当成运行时证明。像素绝对门及线上实走的限制明确记在 verification.md。
