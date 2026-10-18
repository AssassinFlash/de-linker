# #222 第一轮修正 · 验收记录

实例仅 `c222`（http://127.0.0.1:9120）；工作树 `/Users/chesterjohn/Documents/de-linker-worktrees/c222`，分支 `feat/222-pending-signed-in`。`just sync c222` 拉取并装入快照 `20261018-1220`（taken 2026-10-18T04:29:32Z），匿名化检查通过。员工审批与 WindPress 官方编译使用指定账号；本会话未合并、部署或写生产。

## 实现与行为

`AccountStatusNotice` 在原生 Woo 内容 hook 输出 LC 局部状态卡，pending 与 restricted 共用组件；restricted 卡包含保存原因，工作台、导航、联系卡及原端点继续可用。原因片段同时用于询盘表单。价格由 `CommerceState` 决定，`PriceDisplay` 只映射提示；ProductView 复用同一映射。批准后原会话下一次导航见价，无轮询或新会话机制。

账户列表、概览和 Woo 详情直接共用同一金额规则：approved 的历史无价询盘隐藏总额，pending/guest 隐藏金额，概览不留空 Amount 标签。独立评审进一步发现已有行价在账号受限后可能继续显示；三条失败测试复现后修正，真实 Woo 夹具也覆盖批准时有价、限制后原详情隐藏行价与总额。

## 浏览器与真实夹具

EN/DE × 1440×900、390×900 初轮与重复轮分别 **4/4 通过**；纯 main 对照并恢复本分支后再次 **4/4 通过**。每组均通过真实注册表单建立登录会话，待审时浏览产品、加入草稿并发询盘，访问全部账户端点，经独立员工 CLI 批准后原 cookie 不变、下一次产品导航见价、账户状态卡消失。随后 restricted 在账户和可用询盘表单显示原因；rejected 结束会话并回登录。注册已收到及已批准邮件仍在 Outbox 中按主题和原始路由断言。

`screens/` 为恢复分支后最终 40 张全页截图，含四组 restricted 账户页；`matrix.json` 为最终四行矩阵与安全响应读回。初轮与恢复后 CSS 逐字节相同；状态卡已人工查看两语言与两宽度，原因和联系方式换行正常，无水平溢出。文案对抗评审见 `copy-review.md`，裁定视觉变化见 `change-ledger.md`。

pending-account 与 public-inquiry 共用 `BrowserFixture`，两入口和 helper 均进入 PHPCS；入口兼容 WP-CLI eval-file，strict typing 在 include 的 helper 中。每次保存/恢复选项、限流计数与 contact transient，删除自己的客户、询盘、产品、Outbox 和调度动作。公共询盘共享夹具 EN/DE × 1440/390 × 两入口 × 收据/额度上限 **16/16 通过**，运行截图写入 scratch，不覆盖其他票的验收证据。

## 测试与目录

- 已 fetch/rebase 到当前 `origin/main`（`c2106969`，最终 fetch 合入部署 OPcache 重置 #308，网站插件树与对照基线完全相同）。`just check`、`just test` 均 exit 0；全仓 Commerce PHP 为 **1209 tests / 5493 assertions，127 skipped**，真实 WordPress 测试单独运行。
- 真实 WordPress/Woo：**134 tests / 1402 assertions，0 failures，9 skipped**。跳过项为快照缺失的博客夹具，不是账号状态。
- `just i18n-commerce c222` 正规生成 POT/PO/MO，按源文件排序，旧 `Prices after approval` 已过时；i18n-coverage 为 gap 0，i18n-validity 通过。相对当前 main 的 MO：**既有译文 changed 0**，仅移除不用的旧短句，加入新的完整审核提示；明细见 `catalog-comparison.json`。
- 真实 Genie 价格浏览器矩阵 **16/16 通过**：EN/DE × 1440/390 × approved/pending/restricted/guest，卡片价格位逐字与产品页一致；见 `genie-prices.txt` 与 `screens/genie-prices/`。

测试邮件仅进入 c222 本地文件捕获，单次投递重写至 tester222@example.test，Cc/Bcc 为空；原始多收件路由仅在 Outbox 数据中断言。最终恢复读回见 `cleanup.json`。

## run10 稳定性裁定

**已关闭，非代码缺陷。** Claude 第一轮确认本地共享 Redis DB 0 在审批秒发生 Predis 读错误，graceful 模式一次回退数据库、下次读到旧缓存。产品与卡片均读取 `Approval::status()` → `get_user_meta`，原生 `update_user_meta` 已负责失效。线上只读证据为无 object-cache drop-in、cache type Default、LiteSpeed Cache inactive、账户 `private, no-cache`，当前线上没有该故障路径。

裁定已进入规格 184；规格 17 要求未来启用 Redis 时先实证故障期间审批写读一致，满足后才启用 graceful。保留 `diagnostics/run10-failure.txt`、`cache-availability.json`、`readback.json` 支持该结论；run8–14、reboot15/16 的中间原始 JSON 已移除。不新增审批缓存或故障规避轮询。

## 像素与交接边界

按指定 `tests/visual/pixel-parity.mjs`、同机同浏览器同视口、全页、禁动画并等字体图片重新拍摄全部 16 组。分支对 live 为 **11/16 零差异**；四组 DE 1440 页头各 13061 pixels，EN 390 产品页五个兼容产品缩略图区域 7597 pixels。全部差异无掩膜、无容差。纯 main 对 live 为 **12/16 零差异**，仍有相同的四组 DE 页头差异；EN 手机产品图在两次 live 捕获间变化，第二次 live 与 local 相同。**本分支 local vs 纯 main local 全部 16/16、每组 0 pixels**，证明本票未造成这些差异。绝对 live/local 门仍为未完成，关联现有页头 #229 与同步 #252 范围；完整逐页归因与双构建截图见 `pixel/`。对照后已恢复本分支，实际类路径读回正确，CSS 与对照前逐字节相同；恢复后 Approval 真实夹具再验为 **9 tests / 148 assertions，0 failures**。

线上注册与审批实走、approved 客户账户的 live/local 比对：**未完成，本轮仅本地写入授权，按第一轮交给 Claude 合并部署后执行**。本票和地图均未关闭。Spec/Standards 独立评审及修正记录见 `review.md`。

最终基线刷新后已安装主线新增的部署 MU 插件，普通账户 GET 返回成功；指定员工再次完成官方 WindPress 编译及 present 读回，CSS 仍逐字节相同。Approval 再验为 9/148，原生夹具客户和邮件队列读回均为 0，测试收件人已撤。

最终 rebase 后 `just i18n-commerce c222`、`just check`、`just test` 再次全部 exit 0；主线新增的部署工具测试一并通过（cutover 147 tests）。MO 比较已更新到 `c2106969`，译文仍为 changed 0。
