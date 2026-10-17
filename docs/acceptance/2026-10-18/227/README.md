# 后台账户审核 · 当前本地验收

PR：[账号链 · 原生后台账户审核、顶栏抽屉与历史](https://github.com/AssassinFlash/de-linker/pull/278)。本轮落实 Claude 第 1 轮六项必须修改；主线基准为 `b7cbbf40cc5c5ec56656e2fd956e99c3dcb77c86`。线上目标只保留用户 ID **38**；本 PR 不做生产写入、不部署、不合并，推送后等待评审。

## 当天快照

- 实例 `a227`，`http://127.0.0.1:9072/`，工作目录 `/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-227`。
- 已执行 `just sync a227`，快照 `20261018-0007`（上海 10 月 18 日 00:15），212 个已发布商品、2755 个附件，缺失文件 0，线上地址残留 0。VECTOR 兼容导入成功。曾刷新工作目录旧虚拟环境的 linker-local 项目依赖后，用同一份当天快照重装；未退回旧快照。
- LiveCanvas、SEOPress 本地授权 applied。顶部没有授权和重定向杂项提示；未通过 CSS 隐藏提示或点击忽略伪造结果。
- 当前矩阵只使用三名虚构客户（ID 151、152、153），邮箱均为 `example.test`，VAT 是虚构号码、已存结论是本地夹具。截图中的历史搜索限定这些夹具。Outbox 保持满额，所有决定只入队，无邮件实发。

```sh
just wp a227 eval 'require "/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-227/plugins/linker-commerce/tests/fixtures/accounts-admin.php";'
```

## 六项修订

1. **隐私与历史**：文档删除真实注册资料，仅留目标 ID；夹具及五张参考原型图改为虚构资料和保留域名。早期 12 张预览全部撤下，当前生产实现的 52 张逐态图全部重拍，保留两张不含真实客户资料的 User Switching 证据。已把本 PR 新增历史压成一个清理后的提交，使用明确旧头的 force-with-lease。共享主线已经存在的原型提交、GitHub 旧提交/缓存不属于本分支历史重写能抹除的范围，需要维护者协调清理；本 PR 当前树也清掉这些继承的原型资料。
2. **限制账户待办**：Accounts 页单列 Restricted, awaiting customer information，共用卡片、原因、三态操作；修改状态即时进入/移出。摘要同一 Block 另列限制数量及 `status=restricted` 链接，零也显示；pending 红旗/菜单计数保持只含 pending。
3. **网站查证**：先用已填公司网站；缺省时非免费邮箱提供邮箱域名的 HTTPS 链接，并写明 Website (from email domain)。可替换免费邮箱名单让测试只用保留域名。
4. **数字与顶栏**：100 的原生菜单排序、960/520 的阅读布局选择均写来源；偏移改为 WordPress 原生顶栏高度变量。手机 fixed 只在抽屉打开时生效，关闭恢复核心 absolute 行为。
5. **Google/VIES**：Google 使用当前员工语言的完整国家名；只有受 VIES 支持的已填号码才显示官方按国家/号码直达查询。当前官方表单忽略 URL 参数，因此使用同一官方应用的号码查询地址，实际带入 VAT；实测与来源见 [vies-link.md](vies-link.md)。不会更新本站已保存结论。
6. **计数**：一个按状态分组的 COUNT(DISTINCT user.ID) 查询，不加载全体 WP_User；同一请求不同读者共用结果。原生 users 缓存版本在状态、meta、角色变化后使结果失效。真实 SQL 夹具断言四次读只运行一次查询，修改状态/角色后正确更新。

建议项同步完成：Approval::decisions()、AccountSignals 注入、商务规格中的幂等与原因变更通知契约。

## 通知与摘要

新注册和 VAT 复核邮件继续继承 Mail\TeamEmail，内部收件人、Bcc、Reply-to 与站点语言仍由其控制。两个模板与 Digest\Block 均用 AccountsAdmin::url()：`/wp-admin/admin.php?page=linker-accounts&focus=<用户ID>`。已决定的账户仍显示当前决定、展开 Details。浏览器从实际 Outbox 通知正文提取链接打开，不以自行拼接代替通知证据。

PendingApprovals 标题数量、条目只含 pending 纯客户，未显式保存状态也按 pending。限制账户单独数量行；拒绝不再当作新申请。cron 无需登录员工即可渲染。

## 验证

| 检查 | 当前结果 |
|---|---|
| 真实 WP/Woo AccountsAdminTest、ApprovalTest、NotificationRoutingTest | 连续两轮 25 tests / 425 assertions 通过；包含三态、原因/修订/幂等、Outbox 收件人/语言/正文、通知深链、摘要 EN/DE、限制集合、动态字段、免费邮箱、网站优先级、Google 国家名、VIES 号码、权限/nonce、一次聚合计数与失效。选项、数据、队列自行还原。 |
| EN/DE × 1440/390 实际后台浏览器 | 4 项通过（1.8 分钟），新增限制区域同步与手机顶栏关闭 absolute / 打开 fixed / 再关闭 absolute 断言；包括原有历史、原因、深链、Esc、焦点、计数与宽度检查。 |
| just check | 全部通过：PHPCS、PHPStan、TS/JS、Python、翻译覆盖/有效性、构建清单。 |
| just test | 全部通过。commerce 1081 tests / 5350 assertions，71 个真实实例用例在普通入口跳过，本票由专门真实入口补齐。commerce React/API 6、tools JS 98、工具浏览器 9、Genie 658、engine 112、local 98、pull 113、cutover 82 项通过。 |
| 文案对抗与全量双评审 | 见 [copy-review.md](copy-review.md)、[review.md](review.md)。评审记录写明范围、意见和修复。 |
| 隐私扫描 | 对已跟踪文本和 59 张当前图片（54 张生产实现证据 + 5 张参考原型）做私有字串 / OCR 检查，文本和 OCR 均 0 处命中，结果及边界见 [privacy-review.md](privacy-review.md)。扫描只报告计数和路径，不复制隐私值。 |

```sh
just check
just test
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/a227/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php \
  plugins/linker-commerce/vendor/bin/phpunit \
  -c plugins/linker-commerce/phpunit.integration.xml.dist \
  --filter 'AccountsAdminTest|ApprovalTest|NotificationRoutingTest'
LINKER_E2E_SKIP_SERVICES=1 just e2e a227 accounts-admin.spec.ts
```

## 当前截图

`screens/` 有 54 张：52 张本轮 Computer Use 重拍（13 状态 × EN/DE × 1440/390），两张既有虚构客户 User Switching / Switch back 证据。四组文件名为 `{en,de}-{1440,390}-<状态>.png`：

| 状态 | 文件后缀 |
|---|---|
| 后台顶部，没有授权/重定向提示 | admin-top |
| 首页待审卡片 | dashboard |
| 顶栏待审抽屉 | drawer-pending |
| 限制原因输入与通知提示 | drawer-reason |
| 已处理深链自动展开详情 | deeplink-details |
| 限制决定及原因 | restricted |
| 拒绝决定、原因与反馈 | rejected |
| 拒绝后重新批准 | approved |
| 只含虚构客户的账户历史搜索 | history-search |
| 独立限制待办区域与数量 | restricted-queue |
| 限制待办清空 | restricted-empty |
| 零待审抽屉与计数 | empty |
| 不存在的深链目标 | unavailable |

390px 实测没有横向溢出；手机长卡片可纵向滚动。顶栏保持核心滚动行为，抽屉打开期间固定。截图只证明本地呈现和操作结果；业主不经指引发现入口、部署后线上读回与目标账户处理仍属于后续线上验收，未在本 PR 冒充完成。
