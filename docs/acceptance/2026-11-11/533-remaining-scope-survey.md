## 审计范围与方法

只读盘点，未改任何文件、未启动实例、未连生产、未做任何攻击性测试。核实来源：`gh issue view 533`（body + 15 条 comment）、15 张子票状态与正文、`docs/acceptance/2026-11-11/security-dual-proof/`、`docs/audit/2026-11-10-*`（4 份）、`docs/acceptance/2026-11-10/goal-state-ledger.md`、`docs/specs/533-*.md` 等 8 份规格，以及源码侧 `plugins/linker-commerce/includes/**`、`plugins/linker-commerce/includes/Protection/**`、`services/*/ops/*`、`.github/workflows/check.yml`、`tools/checks/`。

地图元数据显示 `sub-issues-completed: 15/15`，但地图本身仍 OPEN——因为 2026-11-04 17:59 的 comment 主动重开了它，理由原文是「防滥用与真人通行需要同时成立……不使用历史关单替代这些结果」。下文把这两件事分开记。

---

## ① 已闭项清单

| 票 | 一句话结论 |
| --- | --- |
| #534 攻击入口、规模与入侵边界 | 87 条同活动诈骗 + 1 条授权测试均走正常访客联系表单，88 条都有完成准入回执（≠成功 Turnstile）；轮换廉价浏览器身份，未发现原子额度绕过；未据此排除主机/认证/第三方漏洞 |
| #535 通知投递、邮件容量与安全恢复边界 | 80/滚动 24h 容量耗尽、38 条排队全部匹配同一活动；52 次初判超时在模型开始前已排队 ≥10 秒；实际内部 SMTP 已启用 |
| #536 完整防护分层与真实客户通行方案 | PHP 两项 RCE 公告经官方核实；CF 免费 WAF 限制、API 挑战副作用、源站真实 IP 信任均已查清；结论是不能用整站验证码或 WAF 代替补丁 |
| #537 攻击通知持久暂缓与单条人工恢复 | 持久发送门 + 员工单条恢复原子上线，原生回调与生产界面读回完成 |
| #538 托管 PHP 与组件漏洞修补 | PHP 8.3.36 + `session.upload_progress=Off` 实际读回；ACF PRO 6.3.1 按「缓解接受」结案（0 前台调用、`/wp/v2/users` 拦截、`acf` 载荷空） |
| #539 VPS 源站直达与资源预算边界 | loopback/专用 TLS 身份、28 次匿名 POST 401、6MiB/30MiB 信封、四服务 PID/额度账本读回，独立双审通过 |
| #542 联系与询盘的有界接收 | 站级接收/未处理条数/字节信封 + 确认活动隔离上线；生产 `verification_failed` 恢复路径实测 |
| #543 询盘初判独立有界后台派发 | 生产 10 秒窗口实测通过：签发后 0.633s 被 worker 领取，Jev 0.283s + DeepSeek 3.402s，总 5.862s |
| #545 通知运输原子预算与关键容量 | 原子 transport 扣账（`next_id 26→28`）+ 主收件箱同 `Message-ID` 实收（UID 1441） |
| #563 Genie 正常请求与失败恢复 | 真实 EN/DE 会话回答 + 原生幂等恢复；PDF 有效下载 4/4 字段、3/3 页 |
| #564 管理身份 MFA/应用密码边界 | 官方免费 Two-Factor 0.17.0 仅管理员 TOTP+恢复码；Hostinger 实际 2FA 关闭、设备验证开启 |
| #565 管理员 MFA 准备与客户无障碍 | 本地完整验证后按 **not_planned** 关闭（业主拒绝设备绑定），证据保留、未冒称已启用 |
| #568 已验证业务站级接收与积压上限 | 原 87 条可靠处置，102/394625B → 15/35685B；252 原始记录全留存、38 旧任务全隔离、账本未重置 |
| #569 公开注册站级与待审账号容量 | 16/h、32/日共享准入；待审 128 账号/8MiB；通知 ACK 绑定真实账号+完整 Message+job |
| #574 既有索引凭证服务端只读 | 同一凭据收窄为 PDF/产品集合只读，设置与用户资料 200→403；418 PDF 与 265 产品原生对照通过 |

另外，2026-11-11 的双向证明（`security-dual-proof.json`）本身已经把「防滥用与真人通行同时成立」这一重开理由做实：20/分钟窗口 429、in-flight 3×429、2 秒节奏不误拒、四个私密端点 401/403/404 无存在性预言、日志按命名维度一一对应、探针 token 在四表 0 命中、凭证扫描 0 真命中。按指示未重验。

---

## ② 未完项清单

按可派工性排序。每项都给了证据路径与责任层。

### U1 · 自然客户完整链路门未取证（治理冲突，非代码缺陷）

**问题**：#542/#543/#545 三票共用一张门——「首条自然到达的正常询盘 → 分类 → 完整通知许可 → 真实 transport 扣账/ACK → 同 `Message-ID` 收件」。三票在 2026-11-03 用验收询盘 **#8535/#8457** 关闭；而地图 2026-11-06 段自己把 8535/8457 归为「验收记录」，并写明「维持不得用验收询盘或重发替代」，11-04 重开时又写「不使用历史关单替代这些结果」。11-09 之后自然询盘确有到达，但仓库内**没有任何自然订单的 permit/transport/Message-ID 读回记录**——`_linker_inquiry_send_` 在 `docs/` 只出现 1 次且属 548 文档，`Message-ID` 在 11 月验收目录 0 命中。

**证据**：`gh issue view 533` 的 `unified-security-current` 块与 2026-11-04T17:59:09Z comment；`gh issue view 545` body「本票暂留唯一正常生产验收门 G545…」；`docs/audit/2026-11-10-production-inquiry-evidence.md:26`（最新自然订单 8680，2026-11-09 20:22 UTC）。

**责任层**：生产只读读回（WP-CLI + HPOS/postmeta + IMAP `EXAMINE INBOX`），不改代码。
**规模**：小时级（一次只读关联快照）。
**标注**：这是「票据状态 vs 地图契约」的冲突，需上级裁定是补证还是显式豁免；不是我可以自行结案的。

### U2 · 运营告警阈值与推送整体缺失

**问题**：现状只有三个部件，且都不构成「告警」：

- `plugins/linker-commerce/includes/Health/Monitor.php:18` — 每天一次 GET `/health`，失败发一封，无阈值、无升级、无静默期。
- `plugins/linker-commerce/includes/Mail/CapacityHealth.php:3` — 注释原文「a capacity failure never sends an alert email」，只写一条固定诊断进 option。
- `plugins/linker-commerce/includes/Digest/Blocks.php:35-41` — 日报五个块（待回复询盘/在办报价/失败邮件/内部认证/待审询盘）**全是业务计数，无安全、队列年龄、容量接近上限维度**。

`HealthPage`（`Protection/HealthPage.php:26`）只在后台展示准入计数，不给任何阈值判定或推送。规格自己承认这项没做完：`docs/specs/533-security-upgrade.md:50` P2 行「完整启动与告警仍未验收」。VPS 侧同样无失败告警——`services/genie/ops/linker-engine-feed-sync.service`、`services/engine/ops/*.service` 全部无 `OnFailure=`。

**责任层**：WP 插件（新增 Digest 告警块 + 阈值判定）+ VPS（systemd `OnFailure=` / journald 已有但无消费者）。
**规模**：天级（要定阈值、走文案对抗评审、EN/DE 双语、还要避免告警疲劳）。

### U3 · 误拒申诉/恢复的客户侧最小工具缺失

**问题**：客户侧唯一出口是「稍后再试 / 写 sales@」。`plugins/linker-commerce/includes/Inquiry/Handler.php:58` 的 `linker_inquiry_throttled` 文案本身就把客户导向邮箱。全站 `grep appeal|dispute|申诉|误拒|false positive` 在 `plugins/**/includes` 与 `plugins/linker-tools/src` 均为 0 命中。员工侧有 `Protection/IntakeRelease.php` 与 `Mail/NotificationHold.php` 手工恢复，但客户无法自查「我的提交是被暂缓了还是没到」。这正是地图 `Not yet specified` 第 3 项。

**责任层**：WP 插件（可能需 LC 模板承接页面）。
**规模**：天级。

### U4 · 边缘层无通用限速、无 WAF

**问题**：VPS 专用网关只有请求体上限与超时，无 `limit_req` / `limit_conn`：`services/engine/ops/nginx.conf:62`（6m）、`:83`（16m）、`:97`（30m）、`:63`/`:99`（proxy 超时）；该文件里 `limit_req`/`limit_conn` 0 命中。主机侧只有 6 条精确 `REMOTE_ADDR` 全路径拒绝（枚举式，非通用限速）。地图 P2「边缘与源站」因业主无法取回阿里云账号而停。

**证据**：上述 nginx 行号；`533` body「源站已有 6 个本轮确认来源的精确 REMOTE_ADDR 全路径拒绝」+ P2 行。

**责任层**：VPS（nginx 自身可加限速）+ 主机/VPS 网络边界（需外部账号）。
**规模**：天级（阈值要压测、不能误伤真实客户、可能与主机层协调）。

### U5 · CI 无密钥扫描

**问题**：`.github/workflows/check.yml` 与 `tools/checks/` 全无 gitleaks / trufflehog / detect-secrets（grep 0 命中）；仓库也无 pre-commit hook（只有 `.git/hooks/pre-commit.sample`）。凭证卫生完全依赖人工周期性 sweep（`docs/audit/2026-11-10-credential-exposure-sweep.md`，以及 11-06 的 25 文件复查）。`.gitignore` 只忽略 `.env`。

**责任层**：CI（`.github/workflows/`）+ `tools/checks/`。
**规模**：小时级（加 pinned action + baseline 清理存量）。

### U6 · Exa 旧密钥仍未撤销（凭证残项）

**问题**：11-06 22:00 记录原文——替换 key 已在 Kimi/agent-mcp 生效且真实 `web_fetch_exa` 通过，但「The former key still returns 200 on Contents, so it is NOT yet revoked」；官方 `DELETE /team-management/api-keys/{id}` 返回 401，两个 Google 身份报告 `AccountDisabled`，剩余身份需本机 passkey。此后 `docs/` 无任何跟进记录。

**证据**：`gh issue view 533` comment `2026-11-06T22:00:52Z`。
**责任层**：凭证/账号治理；阻塞在业主本机 passkey 或厂商支持通道。
**规模**：小时级（受外部阻塞）。

### U7 · 安全规格 4 条证据链接悬空（证据不可复核）

**问题**：`docs/specs/533-security-upgrade.md` 指向 `../acceptance/2026-10-22/533/` 的 4 个文件全部不存在，且该路径 `git log --all` 为空——从未入库：

```
docs/specs/533-security-upgrade.md:32 -> ../acceptance/2026-10-22/533/release-003cedd3.md
docs/specs/533-security-upgrade.md:50 -> ../acceptance/2026-10-22/533/recovery-check.md
docs/specs/533-security-upgrade.md:75 -> ../acceptance/2026-10-22/533/comparison.md
docs/specs/533-security-upgrade.md:89 -> ../acceptance/2026-10-22/533/entry-matrix.md
```

连带后果：`recovery-check.md` 是「恢复演练」唯一的公开证据载体，它不存在，等于恢复演练的「完整启动」从未被可复核地证明（规格 P2 行的「完整启动仍未验收」标注也因此无法追溯）。同类：地图 body 与 11-03 结案评论大量引用本机 `incident-20261022/…`，本机也无该目录。

**责任层**：文档/仓库治理（非代码）。
**规模**：小时级（补录或改指向可复核证据）。

---

## 已知边界与已裁定排除（不算未完项）

- **管理员 MFA 真实因素**：#565 按 `not_planned` 关闭，业主拒绝设备绑定。工程准备在 `docs/acceptance/2026-10-22/565/` 完整保留，未冒称启用。
- **ACF PRO 6.3.1**：#538 按缓解接受结案，采信依据是 0 前台调用 + `enable_shortcode=false` + `/wp/v2/users` 拦截 + `acf` 载荷空。
- **`Linker\Commerce\Health\ReviewReminder::tick()`**（`includes/Health/ReviewReminder.php:30`）是业主 2026-10-23 明确永久禁用的空实现，不是遗漏。
- **TLS 观测的隐私上界**：`docs/specs/533-tls-observability.md` 自己写明 only 新的 access payload 有字段保证，private error 仍可能含 PII、syslog 可丢、保留上界不保证七天。属已知限制。

---

## 需要上级确认的两处不确定项

1. **U1 的票据状态**：#542/#543/#545 已闭但按地图契约未满足。是补一次只读读回，还是把「自然询盘门」显式降级为「验收询盘即可」？这决定 U1 是小时级补证还是治理裁定。
2. **「196 external inquiries」的构成**：`docs/audit/2026-11-10-production-inquiry-evidence.md` 用 196 条外部询盘支撑真人腿，但这些记录与 10-22 攻击波（87 条，同样是 `wc-inquiry-received` 且同样「通过完整 guard chain」）落在同一状态池里（#568 的 102 条未处理里 87 条是攻击）。我没有生产读权限，无法区分这 196 条中攻击记录占多少。若含攻击，则「196 个真实客户」这一表述需下调；双证的人类腿本身仍由 `#8703/#8704` 支撑，不受影响，但那两条是驱动式探针而非自然客户——与 U1 是同一个问题。

---

## 建议派工顺序

小时级先行、可并行：**U5**（CI 扫描，纯增量）与 **U1**（一次只读读回，前提是上级确认口径）与 **U7**（文档补录，纯文档）。
天级且需前置决策：**U2**（告警阈值）与 **U3**（申诉工具）——两者都要过文案对抗评审 + EN/DE + 视觉验收。
外部阻塞：**U4**（边缘账号）与 **U6**（业主 passkey）。