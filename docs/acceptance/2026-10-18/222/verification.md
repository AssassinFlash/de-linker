# 待审账号保持登录 · 本地验收

实例：`c222`，`http://127.0.0.1:9120`；工作树 `/Users/chesterjohn/Documents/de-linker-worktrees/c222`，分支 `feat/222-pending-signed-in`。快照 `20261018-1033`（记录时间 2026-10-18 02:42 UTC）；212 个已发布产品、2755 个附件，缺失文件 0。许可已施加，本地代码来自本分支。

WindPress 经管理员界面的官方 Generate 重新编译，产物 684089 bytes，模板与工具锚点齐全；`just present c222` 随后读回成功。最终 rebase 后又经指定员工重新编译，CSS 与验收截图所用产物逐字节一致（`windpress.json`）；再次 present 为 created 0 / updated 0 / unchanged 18，缓存新鲜且锚点齐全。页面组合由 LC 承接；账户状态是正常内容前的 h2 卡片，导航与联系卡仍在。

## 行为与状态

完整浏览器链使用真实注册表单及其 nonce，保持客户自己的浏览器上下文，通过指定员工的本地 WP-CLI 审批。审批写入后读回 `approved`，原客户 cookie 不变，下一次导航的价格可见；没有在客户上下文调用登录辅助函数。

EN/DE × 1440×900、390×900 的 `run8`、`run9` 各 **4/4 通过**；后续带安全状态记录的 `run11`、`run12`、`run13` 也各 **4/4 通过**；rebase 到 `0fddf100` 后移除临时探针的 `run14` 再次 **4/4 通过**。但 `run10` 出现一次批准后账户仍为待审的失败，根因未确定，稳定性标准仍记为未完成。每个通过的矩阵包括：

1. 注册并保留登录，账户正常内容与状态卡一起呈现。
2. 产品无价格，价格位显示当前审核提示；桌面检查产品栏，手机检查实际可见的固定操作栏。
3. 待审状态加入产品并真正提交询盘；Woo 记录的客户 id 与注册客户相同，状态为 Inquiry received、商品数量为 1。
4. 账户、询盘、文档、保存方案、公司与资料端点均可访问；账户不输出货币金额。
5. 批准后原 cookie 保持，产品价格出现，账户的审核提示消失；原无价询盘使用中性 Price on request / Preis auf Anfrage。
6. 限制原因出现在可用询盘表单上方；拒绝后原会话失效，回到登录表单。

`screens/` 保存最终重启后 `reboot16` 的 36 张全页状态截图；`run8/`、`run9/` 及 `run11/`–`run14/` 保存断言后的状态、队列路由与审批读回。`preview-*` 是便于目检的裁剪预览，原始全页图仍在，预览不用于像素门。

## TDD 与真实夹具

- `test_render_is_the_review_card`：先复现整页 h1，再通过 LC 内 h2 状态片段。
- 账户模块 hook 测试：先复现旧 template_redirect，再接入 Woo 内容 hook，正常端点继续执行。
- 导航与联系槽：先复现 pending 被排除，再恢复完整工作台。
- `test_texts_instead_of_prices`：先复现旧短提示，再加入审核状态。
- `test_approved_account_reads_a_neutral_note_on_its_pending_inquiry`：先复现批准后历史行仍说审核中，再改为既有中性文案。
- 真实浏览器断言先复现待审工作台显示 €0.00，再让总额读取共享价格可见性过滤器。

rebase 前 Commerce 单元测试为 **1057 tests / 5475 assertions**；rebase 后 `just test` 的 Commerce 全套 PHP 为 **1198 tests / 5475 assertions，126 skipped**（真实 WordPress 用例另外运行，见下）。`just check`、`just test` 均 exit 0；最后补充的浏览器用例通过 TypeScript 与 Prettier 检查。全仓测试最初出现部署探针采样 4 次而预期最多 3 次；单项及随后完整全仓复跑均通过（部署工具 143 tests）。rebase 后并行运行验收时，配置器 Steps 浏览器单测曾在 5 秒启动上限超时；无改码单独复跑为 3/3、2.9 秒，随后串行完整复跑通过，未放宽超时。

真实 WordPress/Woo 集成测试初轮为 **117 tests / 1231 assertions，0 failures，9 skipped**；rebase 后、最终浏览器链之后再次运行为 **133 tests / 1386 assertions，0 failures，9 skipped**。Genie 价格真实 HTTP 集成为 **10 tests / 124 assertions** 全过。跳过的是本快照未具备的博客夹具，不属于账户状态验收。

## 邮件与夹具恢复

注册已收到、已批准邮件保留，浏览器链均断言原始队列主题和客户收件人。每轮只选一封客户邮件交给本地文件捕获，To 只有 tester222@example.test，Cc/Bcc 为空；原始内部/客户路由保留在队列断言记录，不向真实邮箱投递。

浏览器夹具只删除自身唯一客户邮箱对应的客户、询盘、邮件与调度动作，保存并恢复测试收件人与限流选项。中间复跑发现：SQL 选项已删除，但持久缓存仍返回旧夹具/测试收件人，随后 `update_option` 无法更新不存在的行。现在只失效夹具拥有的三个 option 键，捕获与恢复实际存储值；没有全实例或共享 Redis flush。中间一轮德语桌面审批旧读，以及 `run10` 德语手机“产品已见价、账户卡仍待审”的失败，均未认定已修复。

## 审批旧提示稳定性：未完成

`run10` 的审批 CLI 与 SQL 均为 approved，原客户产品页价格出现，紧接着账户页仍有一个待审卡，15 秒断言超时。`diagnostics/run10-failure.txt` 保留原始失败；`diagnostics/readback.json` 保存缩小复现与诊断结论。

缩小用例连续 9 轮、108 次审批后账户/产品导航没有复现；其中后 3 轮使用与注册一致的显式 pending meta。完整链带临时本地只读探针连续 3 轮、12 组通过，记录中没有已存审批状态与用户缓存状态的分歧；集成测试后再次完整运行也通过。它们不能证明历史失败已消除。探针已经删除，没有引入新的审批缓存、轮询、强制登出或第二价格规则。永久浏览器用例只保存安全响应读回，仍要求原 cookie 不变、首次产品导航见价、首次账户导航不含审核卡；不重试页面以放宽条件。

**未完成：偶发旧提示的根因与修复。** 当前环境无法稳定复现，提交供 Claude 评审时明确保留此项；不能用通过次数将它改记为完成。

## 用户重启后的重试

用户重启后只恢复 c222，先读回并清理被中断的 `tester222-fault-*` 客户及测试邮件选项，再从清洁夹具串行执行。`reboot15`、`reboot16` 的 EN/DE × 1440/390 均为 **4/4 通过**；记录保存在同名目录，最终 screens 采用 reboot16。两轮之后顺序执行真实 WordPress 集成为 **133 tests / 1386 assertions，9 skipped，0 failures**。期间本地 PHP 日志新增 Redis 连接异常为 0。最终清理与 Redis 连通状态见 `cleanup.json`，命令状态见 `gates.json`。GitHub 可达，fetch 后主线仍为 `0fddf100`。

进一步读回历史日志发现：run10 审批记录为 03:12:12 UTC，产品截图为 03:12:14 UTC，本地 PHP 在其中的 03:12:13 UTC 记录 Redis 连接读失败；另一轮 03:19:37 UTC 记录 Redis BUSY。时间相关性保存在 `diagnostics/cache-availability.json`，不能据此认定完整根因已证明；故障模拟被重启打断，没有产出结论。历史异常仍保持未完成，不新增未经证实的审批缓存补丁。

## 完成边界

- 夹具恢复读回：`cleanup.json` 证明自身客户和邮件队列剩余 0、夹具与测试收件人选项已撤、临时探针已移除；实例绑定本工作树。
- 文案与双评审：见 `copy-review.md`、`review.md`；裁定视觉变化见 `change-ledger.md`。
- **未完成：live/local 像素门。** 16 组中 8 组零差异，其余差异数和尺寸不一致全部保留于 `pixel/results.json`；关联既有页头票 #229 与询盘开放/同步工作 #246 / #252。没有扩大掩膜或容差。
- **未完成：线上注册与审批实走、已批准客户账户的 live/local 比对。** 本会话仅本地写入，留给 Claude 合并部署后的线上验收；票与地图没有关闭。
