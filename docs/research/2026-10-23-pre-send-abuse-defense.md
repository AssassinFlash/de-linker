# 公开入口、资源与发送前反滥用：成熟免费方案适配研究

日期：2026-10-23（取证时间为 2026-10-22 UTC）。这是选型与实现依据，未安装组件，未改变生产策略，未调用真实模型或外发邮件。

## 推荐决定

**先补齐现有栈的五层防护，当前不加 Rspamd、CrowdSec 或第二套 WAF。** 保留普通客户直接提交询盘的路径；提交成功表示完整记录已保存。另由后台决定这条记录是否允许触发邮件。明确恶意自动隔离；判不清或服务故障保留原记录并自动恢复，不能超时后默认发信，也不能变成每小时一封“等待人工复核”。正常内容通过后发送完整、有用的通知。团队通知、客户自动回执、Genie 转询盘必须共用这条发送许可。

这是复刻成熟邮件系统的“扫描后放行、故障保留队列”契约，结合我们已有原生事务、Outbox、后台恢复和模型通道。Postfix 的 Milter 支持在入队前检查，错误可临时失败或隔离在 hold 队列；其同步代理文档同时警告并发、内存和吞吐代价。我们借鉴发送门和故障语义，把扫描放在客户提交之后、实际发信之前；不要求把现有 WordPress 邮件迁移到自建 MTA。[Postfix Milter](https://www.postfix.org/MILTER_README.html)、[before-queue filter](https://www.postfix.org/SMTPD_PROXY_README.html)（A/B）

**这也只是整个站点防护的一层。** 请求洪泛、WP 启动成本、重型文件解析与模型账单要在各自入口更早限制。OWASP 明确区分 CAPTCHA 对功能滥用的帮助与它无法承担的 DoS 防御，并要求先做便宜检查，再做昂贵验证、分配资源。[OWASP DoS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)（A）

## 业主范围与证据边界

当前业主要求见 `docs/specs/533-pre-send-abuse-defense.md`，研究时读取 planning commit `b7df07ae`。它明确推翻早先“只贴标签，所有标签及超时都通知”的发送策略；保留客户快速提交、既定模型路由、原生权限和预算。新政策仍需实现、双轴评审、真实夹具和生产读回。

源码基线固定为生产来源 `3c3c3c25fff1d6b6f1aed8a990a410cfd9149577`。下文源码事实均按该对象读取，不能用其他未合并工作树的改进冒充线上能力。独立的 PR583 仅停止自动 review reminder，不能当作完整内容门已完成。本文也不把局部收件箱观察推成全站攻击比例；Hostinger/VPS 实际 access/error/资源分布由协调者另行取证。

OWASP 的 OAT-017 覆盖恶意内容注入，并特意说明破损 form-to-email 被用来向非预期收件人发信属于实现缺陷，未归入该条威胁。这个区分适合本案：既要处理垃圾内容，也要修复它触发存储、后台工作和发信的路径。[OWASP OAT-017](https://owasp.org/www-project-automated-threats-to-web-applications/assets/oats/EN/OAT-017_Spamming)（B）

## 五层落点：共享主机与 VPS 分别能做什么

| 层 | 当前可核实的边界 | 本轮推荐落点与限制 |
| --- | --- | --- |
| 1. 边缘 / pre-PHP | WordPress 在 Hostinger 共享主机；VPS 不在它的必经入站链上。Hostinger 官方说明 ModSecurity 默认启用，Web/Cloud 不直接提供完整 php.ini 控制。 | 先读回当前 provider WAF、实际命中、缓存及可用前端请求限制；按真实被打的路径施策，保留正常客户正向样本。不能把“默认启用”写成已验证我们规则集/版本/每个入口。VPS 装 WAF 不会拦到直接访问 Hostinger 的请求；不以不可用 DNS 迁移为本轮前提。 |
| 2. WP / Woo 原生入口 | `Protection/Module.php` 注册 contact/inquiry、账户、密码重置、登录、草稿写入、评论等消费者。REST 大小检查执行时 WP/PHP 已启动。 | 保留 nonce、蜜罐、签名时间、原子 subject+site 额度、幂等与原生权限；覆盖直接 HTTP、REST、admin-post、wc-ajax、Store API 的实际别名。对明显无效/重复/过大请求在昂贵解析和 DB 写前返回。WP 插件只能减少后续开销，不能代替前端流量防护。 |
| 3. Genie / engine / model | 资源守卫在原生 `rest_dispatch_request` 回调前运行；已有私有服务认证、持久 provider 预算、Genie 实际执行 slots。 | 先保持这些硬边界，区分请求额度、实际模型尝试、运行中的计算和存储字节。实际进程未结束不能因 HTTP 断线退款。缓存/幂等只复用相同主体、完整输入与版本，不把不同附件/页面误并。扫描器本身也必须计并发/超时/正文上限，不能成为新的无界计算入口。 |
| 4. 内容 / 发信前 | 当前存在标签通知与 held lane 的断层，见下表。 | 完整保存 → 便宜确定性判定/去重 → 后台内容判定 → 原生持久发送许可 → Outbox 最终检查 → 发送。恶意、未知、失效许可均不得占用 SMTP/PHP 尝试额度。 |
| 5. 持续检测 / 响应 / 恢复 | 已有独立恢复心跳、原生状态及预算账本；持续攻击强度不能从单封邮件估计。 | 分层记录请求量/拒绝原因、WP 延迟与错误、DB/磁盘压力、实际 worker 数、provider 尝试/费用、隔离与未知年龄、发信额度和真实发送。只在状态变化、异常或恢复时提醒；不得按垃圾记录逐封通知或用重复汇总替代隔离。自动响应有有效期、范围和回退，禁止无限期全站封禁。 |

Hostinger 的部署限制来自[官方 PHP/ModSecurity 支持说明](https://www.hostinger.com/support/which-php-extensions-and-configuration-options-are-supported-at-hostinger/)（B）。各层检查顺序与资源边界依据上述 OWASP DoS 文档（A）；当前入口是[原生消费者清单](https://github.com/AssassinFlash/de-linker/blob/3c3c3c25fff1d6b6f1aed8a990a410cfd9149577/plugins/linker-commerce/includes/Protection/Module.php#L66)及[资源回调注册](https://github.com/AssassinFlash/de-linker/blob/3c3c3c25fff1d6b6f1aed8a990a410cfd9149577/plugins/linker-tools/includes/Protection/Resources.php#L43)。表内后续行为属于建议，未声称全部已生效。

VPS 只读快照（协调者 18:41 UTC）：Ubuntu 24.04.4 LTS、约 4 GiB RAM、约 3.1 GiB available、无 swap、根盘约 42.8 GiB 可用；Nginx 已装，Rspamd、Redis、CrowdSec、ModSecurity 模块、Fail2ban 未装；既有四项服务 active。这说明具备试验条件，**没有证明再装多个守护进程仍满足现有服务的内存和延迟要求**。原始证据保留私密目录 `review-mail-533/vps-compatibility-readonly.json`；不公开主机地址、认证信息或访问者数据。

### 基线实际缺口

| 实际消费者 | 固定源码证据 | 对新目标的影响 |
| --- | --- | --- |
| 未验证 / campaign held lane | `Sender::prepare()` 先走 `Intake::prepare()`，成功后不做 `Assessment\Queue::prepare()`；Intake 写 hold 和 pending=held。`Queue::process()` 又直接跳过 held。 | 保存并隔离与“已做内容判断”是不同事实。不能继续让整个 verification lane 永久绕过模型后只催人工。需要可恢复的评估状态，明确区分确定 campaign 与尚未判定的普通客户。 |
| 普通询盘团队通知 | `Queue::finish()` 只要没有 notification_job，就把首次结果交给 `queue_notice()`；没有标签对应的发送许可分支。超时及服务/恢复不可用也走 unknown 后通知。 | 标签改变不阻止邮件；只改 prompt 或加更聪明模型不会自动修复发送路径。 |
| 客户自动回执 | `InquiryReceivedEmail::trigger()` 只检查 ReceiptLimit skipped；`Sender::receive()` 为未 held 请求准备回执并触发收到状态。团队 `Queue::defer()` 明确只拦团队 listener。 | 正常验证请求的客户回执可能早于 Jev。仅改团队通知会漏掉向攻击者伪造邮箱发送的 backscatter 和额度消耗。基线回执已有固定正文保护，不应错误声称它会原样回显钓鱼正文。 |
| review reminder | `ReviewReminder::tick()` 在队列仍有记录、上次已过一小时且旧 job 不在时，可再造一封 count/age/time/link 汇总。 | 即使垃圾明细未发，聚合通知仍反复占额度。PR583 应独立停产并在最终 Outbox 处挡住既有 exact category；这项止血不等于内容门完成。 |
| Genie 转人工 / 询盘 | Tools 的 ContactRequest/InquiryRequest 走 Commerce 原生 Sender，不应另造一条“模型说可以”直发路径。 | 要沿真实原生记录和发送消费者统一许可；不能只保护网页上的两张表单。 |

源码定位：[held 与原生 prepare](https://github.com/AssassinFlash/de-linker/blob/3c3c3c25fff1d6b6f1aed8a990a410cfd9149577/plugins/linker-commerce/includes/Inquiry/Sender.php#L171)、[held 跳过 / 全标签通知](https://github.com/AssassinFlash/de-linker/blob/3c3c3c25fff1d6b6f1aed8a990a410cfd9149577/plugins/linker-commerce/includes/Inquiry/Assessment/Queue.php#L128)、[客户回执](https://github.com/AssassinFlash/de-linker/blob/3c3c3c25fff1d6b6f1aed8a990a410cfd9149577/plugins/linker-commerce/includes/Inquiry/Emails/InquiryReceivedEmail.php#L39)、[回执状态触发](https://github.com/AssassinFlash/de-linker/blob/3c3c3c25fff1d6b6f1aed8a990a410cfd9149577/plugins/linker-commerce/includes/Inquiry/Sender.php#L189)、[周期汇总](https://github.com/AssassinFlash/de-linker/blob/3c3c3c25fff1d6b6f1aed8a990a410cfd9149577/plugins/linker-commerce/includes/Health/ReviewReminder.php#L29)。

## 成熟候选：免费商业许可不等于适配当前入口

| 候选 | 免费 / 维护的第一方依据 | 覆盖与适配结论 |
| --- | --- | --- |
| **现有原生队列 + Jev / 官方 DeepSeek** | 无新增插件或服务许可。模型按调用/令牌计费；不能称免费模型。 | 首选：保留既有提交、事务、幂等和恢复，重用已有模型内容能力，增加真正的发送许可。Jev 原生 systemone；DeepSeek 仅用已批准的官方升级判分通道，显式预算，不是失败后的静默换模型。 |
| **Rspamd** | Apache 2.0；官方 release 页面抓到 4.2.3，21 Oct 发布。HTTP/JSON 原生协议；normal worker 明确支持非 MIME 内容。 | 真正可商用免费的成熟内容扫描候选。可以接 webform，**不要求先架 Postfix**。但需任务配置、可信上下文、样本与误判实测；当前不默认安装，先在相同冻结样本上与现有分类比较，证明增益后才引入。 |
| **CrowdSec Security Engine + WordPress remediation** | core 与 WP bouncer 都是 MIT；官方 WP 集成文档提供 bouncer 与 AppSec 接法，release 页有 v2.13.1。软件许可与 Console/第三方 blocklist 订阅分别核算，不假定商业 SaaS feed 全部免费。 | 对行为型攻击/IP 情报有价值；必须有看得到攻击的日志输入及会执行决策的 Hostinger/WP 端，VPS 单独装 engine 不会封掉共享 WP 入站。IP 信誉不能决定一条询盘是否诈骗。当前按真实日志评估，不先装。 |
| **OWASP CRS + 兼容 ModSecurity 引擎** | CRS Apache 2.0，官方明确允许商业使用；文档持续维护。 | 面向通用 Web 攻击，适合 SQLi/XSS 等规则；不是多语言询盘语义分类器。Hostinger 已有 provider WAF 的自定义规则权限、版本与命中必须先读回；VPS Nginx 的规则只覆盖经过 VPS 的流量。不要再叠一套未调优 CRS 当作本次垃圾邮件解法。 |
| **Antispam Bee** | 官方插件说明明确永久免费、可商用；抓取页版本 2.11.13、最近更新两个月内。 | 适用于 WordPress 原生评论/trackback。官方 FAQ 明确不保护其他表单插件或垃圾注册。不能拿它声称覆盖自定义 contact/inquiry REST/admin-post、Woo 或 Genie。 |
| **Wordfence Free** | 官方文档确有免费 WAF，Basic/Extended 两种保护层都可用；免费规则比实时版晚 30 天。 | 可作通用 WP 防漏洞/速率限制候选，存在误判和学习/优化配置成本。不能把 WAF 等同内容反垃圾。当前未核免费 key 全部许可条件/站点现有冲突，不把“无需账户、无限免费 API、已适配全入口”列作事实，也不选它替代原生预算。 |
| **Akismet** | 官方条款与 support 明确：免费 key 仅限个人、非商业站点；推广企业、使用电商平台等不属于免费范围。 | Linker B2B 站不满足其个人免费条件，排除本轮免费方案。插件免费下载安装不代表分类服务商用免费。 |
| **Cloudflare Turnstile** | 官方 Free plan 明列中小企业及多数生产应用，最多 20 widgets、每个 10 hostnames、不限挑战次数。 | 保留现有适用入口；它证明挑战通过，不判断客户内容/邮箱归属，也不保护 pre-PHP DoS。contact/inquiry 已有可用性裁定，不因这次研究重新强迫所有客户挑战。不能把“有验证码”当内容门或所有资源门。 |

第一方证据：[Rspamd 许可](https://github.com/rspamd/rspamd/blob/master/LICENSE.md)、[版本](https://github.com/rspamd/rspamd/releases)、[HTTP 协议](https://docs.rspamd.com/developers/protocol)、[非 MIME worker](https://docs.rspamd.com/workers/normal)（B/D）；[CrowdSec core 许可](https://github.com/crowdsecurity/crowdsec/blob/master/LICENSE)、[WP 集成](https://docs.crowdsec.net/u/bouncers/wordpress/)（B）、[WP bouncer 许可](https://github.com/crowdsecurity/cs-wordpress-bouncer/blob/main/LICENSE)、[发布记录](https://github.com/crowdsecurity/cs-wordpress-bouncer/releases)（F）；[CRS 官方文档](https://coreruleset.org/docs/index.print/)（A）；[Antispam Bee 官方 FAQ/维护信息](https://wordpress.org/plugins/antispam-bee/)（A，仅使用作者说明，未引用用户评论）；[Wordfence 官方 WAF 文档](https://www.wordfence.com/help/firewall/)（B）、[Free 版本界限](https://www.wordfence.com/wordfence-free/)（F）；[Akismet 免费/付费界限](https://akismet.com/support/getting-started/free-or-paid/)、[条款](https://akismet.com/tos/)（B）；[Turnstile 计划](https://developers.cloudflare.com/turnstile/plans/)、[服务器验证](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)（C）；[DeepSeek 官方计费说明](https://api-docs.deepseek.com/quick_start/pricing)（B）。

### 为什么 Rspamd 不能按默认邮箱部署后直接当真相

它能扫描。官方 `/checkv2` 接受 POST，返回 action、score 和 symbols；`Raw`/normal worker 的非 MIME 模式能处理评论、SMS 一类原始文本。因此“不走 SMTP 就不能用 Rspamd”是错误结论。它给建议，应用仍须负责实际放行/隔离和故障恢复。[协议](https://docs.rspamd.com/developers/protocol)、[normal worker](https://docs.rspamd.com/workers/normal)（D）

适配障碍在于信号：网页客户没有给我们一封可验证的原始来信。由本网站生成的 From、SMTP 登录、DKIM/SPF 描述的是我们自己的发信系统，不能证明提交人可信；不能伪造这些字段来给用户“认证”。官方 MTA 集成示例还包含对已认证发送者的跳过路径，照搬可能恰好跳过所有由本网站生成的邮件。这是由集成契约推导的风险，不是声称 Rspamd 无法配置。[Rspamd MTA 集成](https://rspamd.com/doc/tutorials/integration.html)（A）

若后续试验：由服务器构造固定、版本化 webform profile，原始业务内容作为数据；不让浏览器控制 `User`、`Settings`、跳过标记或 sender authentication。Rspamd 确有按 Settings-ID 选配置及启用/禁用规则的原生能力，所以可做窄适配，不必 fork 扫描器。记录启用哪些本地规则、URL/DNS/外部查询及其隐私范围。不要把 unknown 当 clean，也不要直接套默认邮件分数阈值。我们当前 no-extra-website-query 范围不因增加扫描器自动扩大。[官方 settings](https://docs.rspamd.com/configuration/settings)（F）

Bayes 默认推荐 Redis；统计文档存在最少学习量、最短 token 等条件，短询盘或未训练语料不能假定已有可靠统计。不能把未经人工校验的模型结果无限自动学习，形成错误强化或样本投毒。Rspamd 的完整部署指南还涉及 Redis、DNS resolver、任务并发和超时；扫描网络延迟与当前约 4 GiB VPS 的实际负载必须测量。它不是“Apache 许可免费，所以所有规则/查询/运维都零成本”。[统计配置](https://rspamd.com/doc/configuration/statistic.html)（A）、[安装与网络隔离](https://docs.rspamd.com/getting-started/installation)、[worker 任务限制](https://docs.rspamd.com/workers/normal)（D）

## 推荐的现有栈契约

以下是待实施的接口/状态约束，不宣称现有标签已经具备这些语义。

1. **先存原生完整记录。** 不等待模型再回客户；保持当前 EN/DE 字段、草稿、nonce、原生权限与可恢复 UUID。源记录、真实提交内容和有界后续工作必须一并可恢复；保存失败不能返回成功。服务器前置额度和容量保护先于昂贵工作，模型不用于筛查每个无效 HTTP 请求。
2. **隔离“已保存”和“允许发信”。** 为确切源记录、内容版本/摘要、真实收件路由、策略版本和邮件用途持久记录判定。结果先是 pending。normal 也必须经过服务器验证，不能直接信任模型看起来像许可的字符串。malicious/quarantined、unknown/retrying、erased/invalidated 都没有发送权。
3. **便宜规则处理已确认 campaign/重复。** 只使用审过的精确特征或完整内容去重；别用“有 URL、俄语、海外、公司未知、内容短”直接拒收。已知 campaign 与普通未验证 lane 分离。轮换 IP/邮箱不能给同一攻击无限新模型任务，subject+site 总预算同时保留；同一正常短句也不能粗暴跨客户合并。
4. **Jev 先判，必要时按已批准角色升级。** 固定 Jev 原生 systemone 和官方 DeepSeek，不静默切通道。保留完整已授权业务上下文，严格解析选择项/模型名/策略版本；提交内容、引用骗局和 prompt injection 都作为不可信数据。新发送门语义需要新 rubric/version，不能把旧 `inquiry-observation-v1` 结果直接复用成许可。Prompt 的文字说明不能成为授权边界。[OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)（B）
5. **故障安全地保留并恢复。** 沿用每次绝对最多 10 秒的现有调用窗，单次内部重试不续期。超时、非法响应、预算耗尽、DB/调度失败均为 unknown，不发内容邮件；由原生持久恢复安排有界后续尝试，预算不退款、不并发重复判同一版本。恢复尝试次数、退避、最大年龄/人工升级和隔离保留期限必须在冻结样本与故障测量后写进实施规格，不凭研究给新数字。不得把状态永久藏在后台；达到有界恢复边界时以可见异常/单次状态变化提醒处理，不能每条垃圾换发一封提醒。
6. **统一最后发送门。** 团队通知、客户自动回执、Genie 内容转询盘和已有排队工作，在真正扣 SMTP/PHP 尝试额度前，都校验当前许可与冻结 Message。状态变化、内容/收件路由改变、撤回/隐私删除、旧任务迟到均失效。原生客户回执状态 hook 不能绕过。允许后沿用原 Outbox，不另造平行队列；正常团队邮件包含实际内容与证据，避免只发“有待复核记录”。
7. **安全事务独立。** 密码重置、注册验证、审批与真正安全告警按自己的 purpose、原生身份检查、预算/重试处理，不能被一般询盘内容模型一起关掉。也不能让攻击者把公开内容伪装成 critical/security 类来使用其预留额度。内容提交人填写的地址未必归其所有；通过内容判断仍需现有 destination receipt cap/防重复保护，不能反推出已验证邮箱归属。
8. **人工纠错与审计保留。** 自动隔离可逆、不删除原证据；员工纠错绑定实际看到的源/观察快照，保留前后状态和操作者。人工事件、历史标签不被后到模型覆盖。解除一次持久放行仅对原版本/用途有效，不能变成永久白名单。没有自动删除已保存客户记录、批量放行历史 held 或退款旧预算的隐含授权。

成熟模式可复刻，SMTP 传输本身的未知结果仍需诚实处理。连接在远端接受后、本地 ACK 前断开时，仅凭本地重试/Message-ID 不能证明“永远只收到一封”。保存 delivery attempt 与未知状态，继续使用现有审计/恢复边界，避免宣称 exactly-once 的物理收件保证。

### pre-PHP 与持续攻击响应如何具体推进

先把两处真实日志按路径和成本关联，别从 IP 数量推恶意比例。区分普通页面 GET、扫描不存在路径、登录/密码重置、业务写、验证端点、Genie/engine/附件、静态资源；同时看成功正常客户、5xx、耗时、字节与资源消耗。隐私处理采用聚合和有期限的标识，不把正文、密码、token、完整认证头写入攻击报表。日志自身也要限制体积/保留，故障不能伪装成空集，避免攻击转为写满日志盘。[OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)（E）

VPS 已有 Nginx 可按实际私有服务路由限制请求速率和连接，并以主机总预算保护多 IP 洪泛；官方同时支持按 IP 与 server 的 key、dry-run 观察。连接限制不是原始 TCP 总量限制：Nginx 文档说明计的是已读完请求头、正在处理的连接，HTTP/2/3 各并发请求分别计数。因此还需现有 TLS/请求读超时和真实在途 worker 上限，不把它当所有 DoS 的防线。不要给正常文档/PDF 下载套同一个短请求门。[Nginx limit_req](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)、[limit_conn](https://nginx.org/en/docs/http/ngx_http_limit_conn_module.html)（E）

Hostinger 则先确认现有 provider ModSecurity/前端限制和缓存能力，不能复制 VPS 配置就宣称已部署。超出共享主机所能控制的 pre-PHP 攻击，需协调 provider 实际命中与上游处置，这是明确能力边界。Wordfence 自己也说明静态缓存若在 PHP 前直接响应，其 PHP rate limiting 可能不运行；它的速率保护不能据此冒充全站前端网关。[Wordfence rate limiting](https://www.wordfence.com/help/firewall/rate-limiting/)（E）

新增 CrowdSec 的前提是日志证明确有适合行为检测的重复攻击、可获得可信 client IP、已确认 Hostinger/WP remediation 接入位置，并实测误封与故障行为。其官方 WP 文档说明 engine 本身负责 detection、不负责执行阻断；WP 插件也覆盖不到绕过 WP bootstrap 的 PHP 和非 PHP 静态文件，部分场景需 auto_prepend_file 或服务器规则。[CrowdSec WP 技术边界](https://docs.crowdsec.net/u/bouncers/wordpress/)（B）

新增 CRS 的前提是确有可控制的兼容引擎和通用攻击命中需要；PL1 也可能误判，升高 paranoia level 会增加正常请求误封风险。为保护真实客户，先记录命中、对照正常提交，再决定具体规则/短期封禁；不按国家一刀切。[CRS 安装/误判/Paranoia 文档](https://coreruleset.org/docs/index.print/)（A）

## 验证计划与选择门

先用固定、相互独立的恶意与正常样本比较“现有 Jev rubric”与“新发送门 rubric”，如有必要再离线比较 Rspamd。样本至少覆盖：现有奖励/转账骗局及变体、批量推广、身份轮换、重复提交、多语真实技术询问、短回电、投诉/付款问题、合法链接、报价合作、引用骗局求助、恶意 prompt、Genie 转人工及两扇表单。正常控制样本不能由同一个攻击模板改写充数。

分别记录正常被误隔离数、恶意被放行数、unknown 数、总等待分布与每次真实 provider 尝试/资源开销；小样本 0 错只说明该样本，不能当生产误判率或承诺完全拦截。若 Rspamd 没有在相同约束下提供可测增益，就不添加服务。现有模型按次费用、VPS 额外 CPU/RAM/DNS、运维和规则更新都计入适配判断，不能只比较许可费用。

真实原生夹具应证明：恶意/unknown 零 transport、零 SMTP/PHP 尝试扣额、无替代 reminder；普通内容只生成原生正常 job，完整内容/收件人正确；所有客户回执/Genie 路径同门。覆盖 first-save 崩溃、队列写失败、外事务回滚、worker 断线/锁丢失、处理期间内容/邮箱改变、删除/擦除后晚结果、恢复重复运行与旧队列。日志读取失败不能显示为“没有攻击/没有待处理”；异常必须可区分。

分层压力夹具验证 cheap rejects 不触发模型/文件解析/新 DB 写，昂贵在途工作不因网络超时释放；另量化未受保护 pre-PHP 的请求成本。上线再依备份、精确源版本、配置/实际 hook、预算/心跳读回与已授权单封收件证明交付。开发样本、原生捕获、CI、生产投递是四种证据，分别记录。

## Apify 取证索引与未证事实

全部外部研究走 Apify。只使用官方文档/仓库及 WordPress 插件作者说明；搜索结果只用于定位原始来源。原始 JSON、HTML、run 元数据位于私密 `incident-20261022/pre-send-abuse-research/`，没有将令牌、真实正文、主机 IP、邮箱会话或 UA 放入仓库。

| 代号 | Run / dataset | 抓取范围与核验 |
| --- | --- | --- |
| Search | `VlwQrmfnK0Nkc2RmT` / `F9xvt75WY7wl4u3jA` | 10 个搜索请求，用于发现源，不作为事实本身。 |
| A | `mf03vhklXUXMWlJJD` / `tzkoi2SeJjp4amEhs` | Rspamd 集成/统计、Postfix proxy、OWASP DoS、CrowdSec intro、CRS 完整文档、Antispam Bee/Wordfence。Actor 13/13 request success；其中旧 Rspamd protocol URL 实际正文为 404，已排除，后由 D 正确路径补齐。 |
| B | `k0u3ExdmpX4YSoVYD` / `4LsEQ0H0KTWgaUki8` | Rspamd/CrowdSec 许可、Rspamd release、Hostinger、Akismet、Wordfence WAF、OAT-017、Postfix Milter、DeepSeek pricing、OWASP prompt injection。15 请求 14 成功 1 失败；另旧 CrowdSec install URL 返回 404，已排除。 |
| C | `FxYsI1bSxmZLbbQ2i` / `ZCicjzWn5cq64Q4bk` | Turnstile 官方入门/免费计划/服务端验证、Rspamd worker。7 请求 6 成功 1 失败；错误 protocol 和过时 Hostinger URL 返回 404，未作为依据。 |
| D | `NSc6Qgf752sOem2h9` / `5Xxru4V749dKQCKar` | 正确 Rspamd `/developers/protocol`、`/workers/normal`、安装文档。4 请求成功，但 `/modules/settings` 为 404，未用其内容。 |
| E | `nyixEMtMsGd7hIHSY` / `AmYrw7pfI1M9pctEe` | Nginx 两个原生限额模块、OWASP Logging、Wordfence rate limiting。4 请求 / 4 正常页面，Wordfence 首轮失败的页面在此补齐。 |
| F | `KLFYDoa5fXv6GUARL` / `adLyEmDInemHrKcib` | CrowdSec WP bouncer MIT/版本、Wordfence Free、正确 Rspamd settings。4 请求 / 4 正常页面。 |

实际 Turnstile Chrome 300030 与官方诊断页的私密证据另见 `configurator-normal/diagnosis.md`。官方 error-code 文档只把 300* 归为可重试的通用挑战失败；同 Chrome profile 在官方诊断页面也失败，说明问题不是 de-linker 集成独有，**并不能识别具体网络/profile 原因，也不能证明所有正常客户都会失败**。该文档此前由 Apify run `sz7EI20BzWt4GeFpM` 抓取。[官方错误码](https://developers.cloudflare.com/turnstile/troubleshooting/client-side-errors/error-codes/)

仍待实施规格/实际证据确定：当前各层攻击和成本分布；Hostinger 可设置的前端限额及真实生效 WAF；发送门恢复上限/退避/保留与异常升级阈值；独立正常样本误判；新增扫描器的实际增益和资源占用。本研究已给出当前推荐，不以这些未证事实假装组件已覆盖或生产已解决。
