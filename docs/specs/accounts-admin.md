# 后台账户审核

依据：账号链 · 后台账户页实现、业主选定变体 C、2026-10-17 会话澄清。状态随时可以改，不设倒计时或独立撤销流程。

## 原生承载与必要自定义

后台首页用 `wp_add_dashboard_widget` 的 normal/high 上下文；顶栏用 WP_Admin_Bar 节点；历史用 WP_List_Table 的搜索、分页、响应式列与状态视图。WordPress 的 edit_users 与每个目标的 edit_user 共同守门，只有 Approval::is_subject 定义的纯 customer 可审核。User Switching 完整拥有切换链接、nonce 和返回能力。

WooCommerce 的 WC_Customer、国家/地址字段与注册 Fields 是资料源；WordPress/Woo 没有本站批准、限制、拒绝及客户原因邮件的原生业务规则，继续由既有 Approval 和 Woo 事务邮件/Outbox 承载。LC tag 负责站点内容，没有 wp-admin 仪表盘或员工审核 API；本票不构造 LC 后台模板。后台专用 React/TS 只负责原生挂载点内的共享卡片、抽屉和操作反馈；样式只补其布局与抽屉打开期间的移动顶栏固定，不加载到站点前台，不新增 Tailwind 构建。

## 数据与接口

- 深链：`admin_url('admin.php?page=linker-accounts&focus=' . $id)`，统一方法 `AccountsAdmin::url($id)`。已决定的目标仍打开并展开；不存在或无权限时明确报错。
- `GET linker/v1/accounts?focus=<id>&status=<pending|restricted>`：省略参数时返回待审队列；指定 restricted 时返回等待客户补充资料的限制账户，附四状态计数；聚焦时返回该客户，无论其当前状态。
- `POST linker/v1/accounts/<id>/approval`：status 为 approved/restricted/rejected，reason 为客户原因。WordPress cookie + REST nonce 鉴权；没有 GET 写入口。返回已保存的卡片与计数。
- 员工语言控制卡片与列表；客户 locale 单独控制邮件。邮件钩子可能重载翻译域，所以 POST 的卡片在邮件作用域结束后独立渲染。WC 国家缓存随作用域刷新。
- 注册字段由 Fields::fields 的实际定义读取，再补原生 Woo 账单定义中的已存值。新网站字段在注册表定义后自动出现；历史地址仍能查看。密码、隐藏控件与任意内部用户 meta 不外发。
- 免费邮箱识别只认原型指定的初始名单，测试通过可替换名单使用保留域名；其他域名明确标为未核实。公司名按原型中的字面模式提示，既不自动拒绝，也不宣称没命中就是真客户。VIES 读取已保存结论。查证链接优先用注册时填写的网站，否则非免费邮箱提供 https://邮箱域名，并明确标为 Website (from email domain)。Google 查询使用当前员工语言的完整国家名；有可解析且受 VIES 支持的 VAT 时才显示已携带国家及号码的官方查询直达链接。VIES 7.3.0-HF1 表单不支持 URL 预填，所以使用该表单自身调用的公开号码查询地址；打开后由欧盟显示查询结果，不回写本站保存的检查。
- 后台与摘要待审计数只含 pending，包含未显式记录状态的默认待审纯 customer。Accounts 页另有“Restricted, awaiting customer information”卡片区域，限制账户不因离开待审而失联；拒绝仍在历史里随时再决定。摘要同一块另加限制数量与 status=restricted 链接，不并入待审数。后台四状态数量由一次聚合 COUNT(DISTINCT user.ID) 查询产生，同一 PHP 请求中的菜单、顶栏、页面和 API 读者共用；用户数据版本变化后失效。`PendingApprovals` 通过既有 `Digest\Block` 接口注册，标题显示数量，逐条链接与新注册、VAT 复核通知都使用 `AccountsAdmin::url()`。通知继续继承 `Mail\TeamEmail`，复用统一内部收件人及语言；本票不再等待另一会话接线。

## 替换与验证

`parity-before-replacement.md/json` 保存先证后删的记录。原用户列表与档案页只保留状态和审核链接，不再提交第二种审批表单。端到端 approveCustomer 辅助函数也通过新卡片执行。

真实实例测试覆盖队列、动态字段、检查、权限、三态、原因变更、重复提交、历史焦点、User Switching URL 与 Outbox 的 EN/DE 邮件。浏览器测试在 EN/DE × 1440/390 覆盖无 nonce/无原因拒绝、操作反馈、历史再决定、抽屉不跳页、Esc/焦点恢复与无横向溢出。固定快照重拉与最终视觉验收、线上真实机器人申请处理各自保留独立状态，未通过不记为上线完成。

## 布局取值来源

- admin bar 节点优先级 100：WordPress `WP_Admin_Bar::add_menus()` 的编辑节点 80 与次级组 200 之间，保留账户入口靠近原生编辑操作。
- 审核区最大宽 960px、抽屉 520px：本票卡片布局选择。聚焦卡片的详情以标签和值两列呈现，限制阅读宽度，避免横跨整个大屏；抽屉容纳一张 480px 卡片加两侧 20px 间距，避免原生原因框和德语按钮挤成窄列；EN/DE × 1440/390 截图验证，非业务阈值。
- 顶栏高度与定位继承核心 `wp-includes/css/admin-bar.css`：`--wp-admin--admin-bar--height` 桌面 32px、782px 以下 46px；600px 以下核心改为 absolute。只在 `#linker-accounts-dialog[open]` 时把移动顶栏固定，让用户关闭抽屉后焦点能回到同一入口；关闭时恢复原生 absolute 行为。深链滚动余量使用同一变量加一个字号。
