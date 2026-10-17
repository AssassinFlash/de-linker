# 后台账户审核 · 实现证据

> 本页保留 10 月 17 日的历史预览与先证后删记录。#252、#221 合并后的当天快照、通知/摘要接线和最终逐态截图见 [10 月 18 日最终本地验收](../../2026-10-18/227/README.md)。以下“未合并”等状态只描述当时情况。

实现票：[账号链 · 后台账户页实现](https://github.com/AssassinFlash/de-linker/issues/227)。变体 C，状态随时可改，没有倒计时或独立撤销机制。实现规格见 `docs/specs/accounts-admin.md`。

## 当前门槛

实现与本地行为检查通过；本记录**不是最终视觉或线上验收通过证明**。

| 要求 | 当前证据与状态 |
|---|---|
| 后台首页卡片、顶栏、Accounts 菜单及全部历史 | 真实 WP 原生 hook 与表格夹具、四组浏览器用例；早期预览已撤下，当前截图见 10 月 18 日验收目录。业主不经指引发现入口的最终验收尚未进行。 |
| 三态互转、必填原因、修改原因、幂等 | `AccountsAdminTest` 经实际 REST → Approval → 邮件 → Outbox；浏览器逐态操作。重复相同状态/原因不重发，限制/拒绝原因变化会通知。 |
| 动态注册资料及旧资料 | 当前 Fields 与 Woo billing 定义读取；真实夹具动态加 website、读取旧地址并排除隐藏字段/内部凭据。公司网站实现票合并后无需再维护字段表。 |
| VIES 与提示仅作线索 | 真实夹具覆盖全部保存的 VAT 结果、免费邮箱/未核实域名、可疑名称与无命中；提示不自动决定状态；查证链接当前规则见账户规格。 |
| User Switching | 原生权限/nonce URL 夹具；Computer Use 实际切到客户网站并 Switch back，见 `parity-before-replacement.md`。 |
| 深链 | 已处理、缺失与无权目标夹具；浏览器 `focus` 自动展开 Details。稳定地址 `/wp-admin/admin.php?page=linker-accounts&focus=<用户ID>`。 |
| 通知邮件与摘要接线 | #221 未合并。已按业主要求在[该票评论](https://github.com/AssassinFlash/de-linker/issues/221#issuecomment-6233563369)提供统一 URL 与 pending-only 口径；模板与收件人继续由该票接入。本票没有宣称真实通知邮件已带新链接。 |
| 旧入口先证后删 | 先保留旧入口运行新旧行为与邮件证据，再将旧用户列表/档案操作改成新页链接，删除 GET/第二套表单写通道；见 `parity-before-replacement.md/json`。 |
| 文案、Spec / Standards 与旧代码检查 | `copy-review.md`、`review.md`：独立两路全量 diff 评审发现的两处 Spec 问题、一处文案记录缺口均已修复并复核。 |
| 最新快照上的最终视觉验收 | **未通过**。#252 仍未合并；`just pull load a227 latest` 的 MariaDB VECTOR KEY → MySQL 导入错误已在[该票评论](https://github.com/AssassinFlash/de-linker/issues/252#issuecomment-6233626896)提供复现。合并后须重拉、重新跑四组浏览器并逐态截图签收。 |
| 线上账户 ID 38 处理 | 只读定位真实账户，仍 pending，没有写入或发信。拟操作及经过评审的客户原因见 `production-readonly.md`；合并、备份部署读回且取得该操作明确同意后再执行。 |

## 可重跑命令与结果

工作目录：`/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-227`。独立实例 `a227`，WordPress `http://127.0.0.1:9072/`；已成功导入完整快照 `20261015-1852`（212 个已发布商品、2755 个附件），不是裸实例。

```sh
just check
just test
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/a227/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php \
  plugins/linker-commerce/vendor/bin/phpunit \
  -c plugins/linker-commerce/phpunit.integration.xml.dist \
  --filter 'AccountsAdminTest|ApprovalTest'
LINKER_E2E_SKIP_SERVICES=1 just e2e a227 accounts-admin.spec.ts
```

| 检查 | 结果 |
|---|---|
| `just check` | 通过：PHPCS、PHPStan、JS lint/types/format、e2e types/format、Ruff/mypy、用词、翻译覆盖/编译、两个插件构建清单。 |
| `just test` | 通过：PHP、JS、Python 与本地栈测试。commerce 为 1080 tests / 5358 assertions；普通 mock 入口的 64 个真实实例用例跳过，由下列专门入口补本票覆盖。新增 React/API 6 项通过，tools 的 9 项浏览器测试通过。 |
| 实际 WP/Woo `AccountsAdminTest|ApprovalTest` | 18 tests / 273 assertions，通过。无客户邮件实发，检查 Outbox 目标收件人、EN/DE 主题与原因正文、数量。 |
| 实际后台浏览器 | 4 项通过，EN/DE × 1440/390；含无 nonce、空原因、三态往返、历史筛选行恢复、标题/顶栏计数、深链、抽屉不跳页、Esc/焦点恢复（含原行被筛选移除）及宽度。 |

代表性本地资料可通过 `plugins/linker-commerce/tests/fixtures/accounts-admin.php` 重建：只允许隔离实例，三名 `example.test` 客户；测试邮件统一为 tester，Outbox 被节流保持，不调用传输。Fixture 会把此专用实例的其他客户标为已批准以控制队列，不改源快照；不得用于共享实例或线上。

## 截图范围

早期预览已全部撤下。当前 EN/DE × 1440/390 逐态截图在 [10 月 18 日验收目录](../../2026-10-18/227/README.md)，只用虚构客户与保留域名。旧截图不再作为当前验收证据。
