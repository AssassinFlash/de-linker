# 全站安全升级与持续询盘接收：事件防护研究

日期：2026-10-22。研究票：[536](https://github.com/AssassinFlash/de-linker/issues/536)；事件地图：[533](https://github.com/AssassinFlash/de-linker/issues/533)。研究基线：`dcd5560dc301c07a9d4f8405d2b2e753d5a49ce0`。本文是官方资料核实与实施建议，**不代表任何建议已经部署或通过线上验收**。

本子任务只读研究：没有修改生产、DNS、邮箱、账号、模型通道，没有购买服务，没有发邮件或访问垃圾邮件中的落地页。外部资料全部经 Apify 取得。原始公开资料暂存于本机 `/tmp/incident-defense-research-20261022/`，凭证只从环境读取，本文不含密钥、用户提交明文或攻击利用代码。

## 1. 结论与优先级

当前需要同时处理两个独立风险：**公开表单被批量利用，耗尽通知资源**；**PHP 新披露的两项远程代码执行漏洞必须确认实际运行环境已修补**。表单垃圾证明业务入口遭到滥用，不能单凭垃圾记录推断主机已经失陷；PHP 漏洞公告也不能证明本次垃圾投递使用了该漏洞。应分别取得入口、请求、通知、文件与账号证据。

推荐的最终结构是：**受保护的接入层 → 低成本共享准入 → 持久化接收 → 活动去重与可恢复复核 → 有预算的内容判断 → 按优先级通知 → 可追踪的人工恢复**。不同环节分别解决流量、重复活动、邮件与模型消耗、误判恢复；验证码和 Jev 都不能单独承担全部防护。

实施优先级建议：

1. **P0：运行时漏洞补丁与事件止血并行。** 保存证据与恢复点；确认网站 Web SAPI、其他站点与 VPS 上是否存在 PHP，核实两项 CVE 的实际修补状态；对已人工确认的同一垃圾活动抑制重复通知和重复模型调用。临时严格验证只作为应急开关，保留已知真人失败证据，尽快替换为有恢复入口的策略。
2. **P1：保护询盘接收与通知容量。** 增加活动级去重、可恢复复核、通知优先级与容量预留，修好队列按时启动和超时恢复；取消对已弃用 SunRiver Electric 地址的转发依赖。先区分队列成功、发送服务接受与收件箱实际到达，再谈成功率。
3. **P2：边缘代理与源站同时接入。** 用 Cloudflare Free 的实际能力做低风险防护；验证源站绕过与真实客户端地址。仅迁 DNS、仅开 Turnstile、仅在页面放组件都不构成全站保护。
4. **P3：账号、文件、API 与 AI 成本闭环。** 管理员 MFA、最小权限、升级与恢复演练；公开副作用入口逐一实走；模型/文件/工程任务先预留成本再执行、完成后结算，不能从未保护的 VPS 地址绕过。

以上为研究判断。数值目标和流转规则是待实施的验收要求，不能作为当前已达到的成绩。

## 2. PHP 公告：已核实，需单独设最高优先级

PHP 官方在 2026-10-21 发布的公告确认两项可导致未认证远程代码执行的漏洞：`CVE-2026-109618`（内存不足时请求初始化/清理状态损坏）与 `CVE-2026-109619`（请求释放后仍残留的全局状态被后续请求使用）。官方固定版本为 **8.5.12、8.4.27、8.3.36、8.2.35**，因此业主收到的这些版本号与官方公告一致。[PHP 官方公告](https://www.php.net/archive/2026.php#2026-10-21-5)、[OOM 公告](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w)、[残留全局状态公告](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp)

官方将所有处理 Web 请求的 PHP 安装列入风险范围，明确包括 PHP-FPM、Apache mod_php、php-cgi、FrankenPHP、LiteSpeed。mod_php 有应用代码执行前即可触发的已展示攻击路径；OOM 公告对 FPM、LSAPI 的风险与已验证范围作了更细区分，不能把“尚未展示该 SAPI 的完整利用”解释成安全。WordPress 插件执行得更晚，不能代替运行时补丁。[PHP 官方公告](https://www.php.net/archive/2026.php#2026-10-21-5)、[SAPI 条件说明](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w)

**发行版安全回补必须按包版本判断。** Ubuntu 两个 CVE 页面当前均列出以下已修补包，说明上游小版本号较旧并不必然未修补。不能把 `php -v` 的 `8.3.6` 直接和上游 `8.3.36` 比较后下结论。[Ubuntu CVE-2026-109618](https://ubuntu.com/security/CVE-2026-109618)、[Ubuntu CVE-2026-109619](https://ubuntu.com/security/CVE-2026-109619)

| 安装来源/分支 | 本次官方确认的修补标识 | 如何验收 |
| --- | --- | --- |
| PHP 上游 8.3 | 8.3.36 | 证明实际 Web worker 运行已更新构建；不能只看 CLI |
| PHP 上游 8.2 / 8.4 / 8.5 | 8.2.35 / 8.4.27 / 8.5.12 | 在当前兼容分支内更新；无需为修补随意跨大分支 |
| Ubuntu 24.04 noble，官方 php8.3 包 | 8.3.6-0ubuntu0.24.04.13 | 核对发行版、包完整版本、仓库来源与运行 worker |
| Ubuntu 22.04 jammy，官方 php8.1 包 | 8.1.2-1ubuntu2.28 | 同上；这是 Ubuntu 回补，不是 PHP 上游恢复支持 |
| Ubuntu 26.04 resolute，官方 php8.5 包 | 8.5.4-0ubuntu1.5 | 同上 |
| Ubuntu 26.10 stonking，官方 php8.5 包 | 8.5.9-0ubuntu2.1 | 同上 |
| Debian / 第三方 PHP 仓库 / 容器 | 按该来源安全公告与镜像构建判断 | 不套用 Ubuntu 包标识，不仅看主版本 |
| Hostinger 托管网站 PHP | 由托管方提供已修补构建 | 核对域名当前 Web SAPI、实际版本/构建与托管方修补确认；本机/VPS 的 apt 不能更新另一台托管主机 |

Ubuntu 的 [USN-8948-1](https://usn.ubuntu.com/USN-8948-1) 同时列出 FPM、CLI、CGI 与 Apache 模块包的修补版本，可用于实际包核对。Debian 安全跟踪已登记两项漏洞及 `DSA-6574-1`、`DLA-4848-1`；本次 cheerio 抓取未保留其版本表，DSA 页面也未提取到正文，因此本文**不虚构 Debian 的固定包号**，实施时应读实际发行版对应公告与包元数据。[Debian 109618](https://security-tracker.debian.org/tracker/CVE-2026-109618)、[Debian 109619](https://security-tracker.debian.org/tracker/CVE-2026-109619)

推荐升级动作：先记录系统/安装来源、当前包与 worker、共享站点和扩展依赖，形成可恢复备份；查看目标包及变更范围，再更新对应 PHP 包/托管运行环境；重启或替换**实际处理请求的所有相关 worker**；通过受控、临时且不公开配置的诊断取得 Web 侧版本与 SAPI 后移除诊断；验证 EN/DE 商品浏览、访客询盘、注册登录、Genie、附件、配置器及计划任务。对自带 PHP 的容器应更新镜像并重新创建容器，仅升级宿主机包不够。以上是实施建议，不是本子任务已完成的操作。

官方明确：只有包含补丁的更新是完整处置。其配置缓解各自只覆盖部分路径。尤其 `memory_limit=-1` 需要额外的进程/容器资源边界，不能在共享主机上当作普通“加固”随意启用；`.user.ini` 或应用内 `ini_set()` 也不能替代请求解析前的保护。不要为赶时间盲目执行全系统升级、设置无限内存或仅隐藏错误信息。[官方缓解边界](https://www.php.net/archive/2026.php#2026-10-21-5)

补丁后仍需检查是否失陷：核心与已知插件完整性、非预期可执行文件、uploads 内脚本、管理员/角色/应用密码变更、计划任务、选项和外发连接、Web 与认证日志、备份差异。若发现确实失陷，保全证据后从已知可信构建恢复并轮换受影响凭证；不要通过只删可疑文件宣称清理完成，也不要用旧数据库覆盖新真实询盘。此段为事件调查建议，具体结论由现场证据决定。

## 3. Cloudflare 免费档能做什么，不能做什么

独立 Turnstile 不要求网站 DNS 或流量经 Cloudflare 代理；边缘 WAF/DDoS/速率控制则需要对应 HTTP(S) 记录实际走代理。两者不能混为一项。[Turnstile 接入](https://developers.cloudflare.com/turnstile/get-started/)、[代理状态](https://developers.cloudflare.com/dns/proxy-status/)

| 能力 | 本次官方资料核实 | 本站建议 |
| --- | --- | --- |
| Turnstile Free | 最多 20 个 widget，每个 10 个 hostname，所有 widget 类型，验证请求不限量，分析最多回看 7 天；Enterprise 才有 Ephemeral IDs 等能力 | 现有账号可继续，无需购买新插件；本站自己保留必要的脱敏指标，不能依赖免费分析长期取证 |
| WAF 自定义规则 | Free 5 条规则，支持 Block/Managed Challenge 等；Free 不支持 Log 动作或正则 | 精确匹配少量敏感 HTML 入口/已确认高风险流量；先模拟表达式并本地记录影子决策，不承诺免费 WAF Log 模式 |
| WAF 托管规则 | Free Managed Ruleset 提供高影响、被广泛利用漏洞的子集；完整 Managed/OWASP 功能取决于套餐 | 免费子集作为一层，不声称已覆盖此次 PHP 新 CVE；运行时补丁照做 |
| 速率规则 | Free 只有 1 条；表达式字段限 Path/Verified Bot，按 IP 计数，计数/缓解窗口均 10 秒 | 用于明显突发、专用路径的粗保护；按浏览器/账号/小时/费用的公平额度仍在应用实现 |
| Bot Fight Mode | Free 可用，覆盖整个域名；不能通过 WAF 自定义 Skip 例外排除；可能挑战 API/mobile | **不默认整站开启**，否则可能影响 Genie/REST/监控且无法做所需精细例外 |
| 精细 Bot Score | `cf.bot_management.score` 要求 Enterprise+Bot Management | 不写基于该字段的免费方案，不默认采购 |

来源分别为：[Turnstile plans](https://developers.cloudflare.com/turnstile/plans/)、[Custom rules](https://developers.cloudflare.com/waf/custom-rules/)、[Managed rules](https://developers.cloudflare.com/waf/managed-rules/)、[Rate limiting availability](https://developers.cloudflare.com/waf/rate-limiting-rules/)、[Bot Fight Mode](https://developers.cloudflare.com/bots/get-started/free/)、[Bot score](https://developers.cloudflare.com/ruleset-engine/rules-language/fields/reference/cf.bot_management.score/)。

免费速率规则不能按表单内容、收件邮箱、浏览器身份或模型花费组合计数，也不能在该规则中直接要求“仅 POST”。若联系/询盘共用 `admin-post.php` 或 `admin-ajax.php`，直接给整个文件套小额度会连带限制其他业务；应保留应用 action 粒度或先设计专用路径，再依据正常流量确定粗阈值。Cloudflare 官方也说明边缘计数更新存在延迟，不能保证精确数量的请求抵达源站；它不能代替数据库原子资源预留。[限制和计数延迟](https://developers.cloudflare.com/waf/rate-limiting-rules/)

Managed Challenge 的插页返回 HTML，会中断期待 JSON 的 AJAX/XHR/fetch。不能给 `/wp-json/`、`admin-ajax.php` 或 Genie 的所有请求直接套插页挑战；应在初始 HTML 页面完成相应验证，或在满足代理 zone 条件后单独设计 Turnstile pre-clearance，再保留业务动作的服务端 token 校验。pre-clearance 是新的接入决策，不能视为现有独立 Turnstile 已自动启用。[插页兼容性](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/)

DNS/代理实施前应导出当前 zone、记录主机和 DNSSEC/DS 状态、TTL、回滚方式；只代理适合的 Web 记录，保全 MX、邮件主机、SPF/DKIM/DMARC 等邮件记录。HTTPS 使用可验证源站证书的 Full (strict)，不要用 Flexible 绕过证书问题。[代理边界](https://developers.cloudflare.com/dns/proxy-status/)、[Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/)

## 4. 源站与信任边界：避免“边缘有防护，源站仍裸露”

Cloudflare 官方列出隐藏/轮换源站地址、审查 DNS-only 记录、源站只允许可信代理网络、Authenticated Origin Pulls、Tunnel 或受控 secret header 等方式。它们需要不同的源站权限：Tunnel 要安装 daemon，AOP 要配置服务端证书校验，网络白名单要主机防火墙能力。Hostinger 托管主机能否逐项支持应现场确认，不能把“Cloudflare 免费可用”等同于“本托管计划能配置”。[Protect your origin server](https://developers.cloudflare.com/fundamentals/security/protect-your-origin-server/)、[AOP](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/)

建议分两类源站：

- **托管 WordPress**：优先取得托管方支持的可信 Cloudflare 真实 IP 恢复与源站访问限制；若只能用应用级 secret header，应由可信边缘覆盖该头并在原生写入前检查，保留不泄露 secret 的直连拒绝测试。应用级检查不能代替防护发生在 PHP 解析前的运行时补丁和主机层防护。
- **自管 Genie/工程 VPS**：反向代理只开放必要端口；优先限制源站网络入口或使用可验证网关身份。服务端需验证短期签名/可信调用凭证与范围、请求绑定、重放、超时；不能因为 WordPress 已检查过，就让直达服务的匿名调用免费消耗模型/工程预算。只限制浏览器 CORS 不构成服务端身份验证。

当前源码 `BusinessPolicy.php` 的连接额度取自 `REMOTE_ADDR`。上代理后若运行环境没有恢复真实客户端 IP，正常客户可能共享边缘节点额度；若直接信任任意 `CF-Connecting-IP`/`X-Forwarded-For`，攻击者又可能直连伪造身份。实施必须同时证明可信代理边界、正确原始地址与直连拒绝，不能孤立改一个请求头。此处为当前源码检查与架构推断；Cloudflare 官方说明了真实客户端地址头及 Workers 子请求等变体，实际信任链须按部署核实。[HTTP request headers](https://developers.cloudflare.com/fundamentals/reference/http-request-headers/)

## 5. 业务入口：用风险与恢复机制替代全开/全堵

WordPress nonce 主要用于 CSRF 防护，可在生命周期内重用，不是身份、权限或防重放凭证；默认未登录访客共享 user ID 0。因此保留 nonce 的同时仍需业务身份、幂等与资源预算。[WordPress nonces](https://developer.wordpress.org/apis/security/nonces/)

建议统一流转，但区分风险：

| 流量/失败类别 | 接收与保存 | 模型、邮件与后续 |
| --- | --- | --- |
| 基础字段合法、非已确认活动、正常业务提交 | 不等模型；持久化成功后给唯一接收编号，重试返回同一记录 | 有界异步 Jev；正常/不确定均进团队业务视图。模型不确定本身不拒收 |
| 人工已确认的同一诈骗活动，命中窄组合指纹 | 保存首份及有限证据；重复计数聚合，保留关联和人工恢复入口 | 不每条调用模型、不逐条发团队邮件、不向未经验证的任意邮箱发回执；首次警报加有预算摘要 |
| Jev 单独标“疑似垃圾”，没有独立确认 | 保留可查业务记录，不硬删 | 标签、置信/理由与人工复核；单模型标签不自动升级为永久封禁 |
| 第三方验证持续失败/不可用，但有真实客户可能 | 保留表单输入，明确错误与重试；可用独立严格容量的待核验接收区保存并给真实状态编号 | 不让第三方故障变成无限免验证业务旁路；限制重复、体积和副作用，允许员工恢复为正式业务 |
| 缺 nonce、伪造请求绑定、非法上传、已耗尽资源预算 | 在相应副作用前拒绝该动作，返回可解释错误及恢复时机 | 不调用付费服务、不发送回执；不把服务错误伪装成客户恶意 |
| Genie 对话/图片/PDF/工程作业 | 各动作服务端 proof、大小/解析/并发/预算检查 | 先原子预留成本再调用，结算/释放可审计，达限保留草稿与转人工信息 |

**“活动指纹”是建议新增机制**：组合使用规范化留言/目的落地域、重复轨迹与人工确认；保留版本与可撤销范围。不能只按俄语、中国地址、外国客户、免费邮箱或出现网址判垃圾，也不能永久封禁整个共享平台 `workers.dev`。归一化应防 Unicode/空白/追踪参数变化，但不得把合法技术参数和联系方式误合并；精确与近似规则分开实测。

待核验接收区必须有按主体、活动、全站的容量、保留期和人工处理承诺；容量将满时显示明确替代路径并告警，不能悄悄丢掉。新增复核流转与暂停通知改变了先前“全量只打标签”策略，应明确记录当前事件裁定、适用范围和恢复方法，不能悄悄扩大到所有疑似询盘。

Turnstile 服务端 token 有效 300 秒、单次使用；后端应校验成功结果、预期 hostname/action，并将重试绑定原提交标识。前端有 success/error/expired/timeout 回调与自动/手动重试支持；保留留言和产品草稿，给有界重试与恢复路径。[服务端验证](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)、[客户端错误处理](https://developers.cloudflare.com/turnstile/troubleshooting/client-side-errors/)

本站已发生真人 Chrome `300030` 失败的事实由主调查保存；本次官方抓取未提供该完整代码的专属根因说明，只确认 300/600 家族表示检查失败。**不能据此断言该客户是机器人，或把某个扩展/国家当已查明根因。** 官方列出网络、浏览器、扩展、自动化与设备条件等挑战完成问题；目标客户网络/设备必须实测，本文不承诺中国大陆可用或零误拒。[Challenge solve issues](https://developers.cloudflare.com/cloudflare-challenges/troubleshooting/challenge-solve-issues/)、[错误处理](https://developers.cloudflare.com/turnstile/troubleshooting/client-side-errors/)

## 6. 全站覆盖与账号、文件加固清单

入口台账应由代码、已注册路由与线上实际请求共同生成，至少含：联系、访客/登录询盘、两步注册、Woo 与 WordPress 原生登录/忘记密码/重置、账户审批、评论/REST 评论/引用通知、solution draft 与重发邮件、Genie 会话/消息/转询盘/转团队/导出与邮件、图片/PDF/语音、配置器/屋顶/地图/报告/PDF、所有 `admin-post`/`admin-ajax`/REST 原生替代路径、Cron/服务回调、VPS 直达地址。每行记录权限、CSRF/凭证、proof、幂等、配额、资源成本、持久化、邮件及异常消费者；“某页面有组件”不算该动作已覆盖。

当前源码已对原生评论与 REST 评论接入共享准入，并在 enforce 时移除 `pingback.ping`；其余认证 XML-RPC 方法仍保留。后续先查实际消费者，再禁用无用途方法/应用密码，不能为了“全站安全”盲目关全部 REST/XML-RPC/`admin-ajax`，影响 Woo、LC 和工具。REST 私有写操作需同时检查身份、nonce 与能力，不能依赖路由隐藏。[REST authentication](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/)

管理员和高权限员工必须使用独立账号、强且唯一的密码、MFA 与可恢复的备用认证；WordPress 核心不自带 MFA，可优先评估 WordPress 官方插件目录的免费 Two-Factor 或现有身份提供方，避免新增付费安全插件。需要实体设备登记的 MFA 步骤必须由真实账号持有人完成，不能用代理临时密钥把员工锁在外面。[WordPress 暴力登录防护](https://developer.wordpress.org/advanced-administration/security/brute-force/)、[Two-Factor](https://wordpress.org/plugins/two-factor/)

更新核心、主题、插件及服务依赖；删除前先确认用途，不保留停用但有风险的旧组件；禁止后台文件编辑、限制文件写权限，保护配置与备份不被公开读取。`DISALLOW_FILE_EDIT` 只减少一种编辑路径，并不能阻止已能上传恶意文件的攻击者。自动更新、权限与生产发布管线需协同，不对全树盲目 `chmod`。[WordPress hardening](https://developer.wordpress.org/advanced-administration/security/hardening/)

附件建议采用业务允许类型白名单、扩展与实际内容联合校验、大小/页数/像素/解压/解析时间限制、安全重命名、隔离存储、最小下载权限与禁执行；不能信任上传者的 MIME/原文件名。PDF、图片、语音解析与模型读取分别计费/并发，附件内部指令仅作为不可信内容。具体可接受大小依据业务文件样本确定，不为新 PHP 公告盲目调大上传限制。[OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)、[OWASP Denial of Service Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)

## 7. 通知、模型与运营容量

Hostinger 官方当前明确内置 sendmail/PHP mail/类似服务器发信路径为 **10 封/分钟、100 封/滚动 24 小时**；超额会暂时限制。认证 SMTP 使用其邮件服务自己的套餐限制，并不代表不限量。官方同时提供每小时更新的 sendmail rate-limit 日志；可将它与本应用 Outbox/发送账本比较，区分应用侧和主机侧瓶颈。[Hostinger limits](https://www.hostinger.com/support/6976044-parameters-and-limits-of-hosting-plans-in-hostinger/)、[PHP mail 与日志](https://www.hostinger.com/support/11393648-php-mail-limitation-explained-how-to-improve-email-delivery-with-smtp/)

应用已有更保守的 8/分钟、80/滚动 24 小时预算；本次事件快照由主调查取得，不能把发信任务结束等同于逐封收件。应先对已确认活动聚合，并为真实业务、账号安全和恢复类通知预留容量，再评估现有已授权邮箱的认证 SMTP，核对 SPF/DKIM/DMARC、envelope 与 From、退信、重试、禁用旧转发。SMTP 替换不能替代准入，直接放出积压垃圾只会消耗新通道与发件信誉。保留真实业务通知的可恢复 Outbox，不因日限额删单。

SunRiver Electric 已由业主确认过期且不续费，应移除它在路由、转发和健康检查中的依赖；不要与实际主接收地址 `sales@sunriverinverter.com` 混淆。新账号、回执、内部通知等收件策略以当前业主裁定为准；验证只使用授权单一 tester，其余收件路由检查队列数据。

AI/工程维持现有四条授权模型通道：Genie=deepseek-flash 官方直连；Jev=OpenRouter 原生 systemone 的 typesafe/jev-1.13；embedding=OpenRouter gemini-embedding-2；Jev 级联评分=deepseek-flash 官方直连。**不以安全升级临时增加其他模型、备用网关或静默降级**。这是 AGENTS 的本站合同，非外部供应商能力判断。

预算建议分浏览器/账号、连接、全站、动作、并发和实际成本；已审批账号与仅完成注册的账号分别评估信任，不能用廉价注册无限扩容。直接询盘不与聊天额度混用；后台 Jev 重复活动只检查代表样本，超时/服务故障可见且不自动封禁。模型调用、上传解析、PDF、地图/工程供应商和邮件各自有成本熔断，原子预留+幂等恢复防并发重复花费。阈值先用真实正常流量与预算选定，记录依据；免费边缘计数不能承担精确账本。

## 8. 验收、指标与回滚

| 目标 | 验收口径与建议门槛 | 不能冒充的结果 |
| --- | --- | --- |
| PHP 修补 | 每个真正承载 PHP 的 Web SAPI/容器均有来源、完整构建/包号、重启与 Web 读回，落在对应官方修补范围 | CLI 已升级、切了主版本下拉框、WAF 已开 |
| 正常询盘可接收 | EN/DE × 1440/390；Chrome/另一主流浏览器；快填/长填/共享公司网络/产品链接/正常俄文/未登录/待审/已审批；全部受控场景保存一次并可恢复 | 若干夹具全过即全站误拒率为零 |
| 已确认活动不耗通知 | 当前活动变体按已定义窄规则命中；仅首次警报+有界摘要；重复不创建独立即时邮件/模型请求；可人工恢复误归组记录 | 禁俄语、封整国、封共享域名即防护完成 |
| 供应商与验证失败 | 过期/重用/伪造/action-hostname 不匹配/网络失败分别记录；保留输入，限定重试；待核验容量与满额响应可测 | CAPTCHA 成功夹具证明所有真实设备成功 |
| 初判时效 | 建议目标：首次通知有效初判覆盖率先达到 ≥95%，另报排队时间和模型时间的 p50/p95；仍守客户不等模型和 10 秒合同 | 单个 0.75 秒样本代表整体，或把等待总时间都算模型耗时 |
| 真实误拒/误标 | 用人工独立标注的真/假询盘计算；保存样本数、期间、分母与置信边界；每起已知真人失败都追具体环节 | 模型自己的标签当真实答案，或只有保存记录没有失败尝试分母 |
| 资源预算 | 覆盖全部副作用动作，直达源站也不能绕过；并发/重试/登录登出/多入口不能重复花费 | 单 IP 限流或 CORS 当全部预算 |
| 通知可靠性 | 应用队列年龄/失败、主机拒信/限额、服务端接受、指定主邮箱到达分别取证；真实业务不因活动垃圾长期排队 | 应用任务结束等于已读/全部送达 |
| 源站保护 | 可信代理身份/真实 IP 可核验，直连 HTTP 写入与 VPS 资源调用被拒，管理员和必要服务有恢复通道 | 源 IP 在页面看不见，或只改 DNS |
| 恢复能力 | 人工释放一条测试误归组记录，幂等生成一次业务/通知；演练配置/代码/数据恢复且保留新增真询盘 | 有备份文件即恢复可用 |

建议分别保留以下阶段指标：原始状态、严格验证、取消普通表单强制验证、当前应急模式、分层防护。不同阶段用相同合法/恶意夹具回放，线上按明确时间窗、风险原因、入口、匿名主体统计。历史未记录的原始成功率不补造；当前攻击时期与正常时期的混合率不能当升级因果效果。

回滚按层进行：边缘规则逐条禁用；恢复 DNS/DS 时按事前导出与传播状态操作；应用活动规则版本可撤销但保留证据/记录；通知队列不批量清空；模型/工程额度保持保护；PHP 回滚只允许回到仍含两项安全补丁的可信构建。发现真人被错误阻挡时先缩小对应规则并恢复该提交，不能把全站重新变成无限免验证入口。

本研究不建议新购付费插件。Cloudflare Free 和已有账号可以覆盖一部分边缘与验证能力；若实际流量/托管能力证明不足，再按已测缺口比较付费边缘功能、发信服务或主机方案。任何候选都需明确价格/限制/迁移边界与真实客户验证，不能承诺零误判或任意地区无障碍。

## 9. 官方来源与 Apify 抓取证据

所有下列外部读取发生于 2026-10-22 UTC，actor 为 `apify/website-content-crawler`（cheerio、深度 0）或用于发现的 `apify/google-search-scraper`。下表的“抓取完成”只是运行结果；HTTP 404 和缺少正文的页面不用于事实。正文归档在本机临时研究目录，本文为唯一入库产物。

| Apify run / dataset | 核实范围 | 正文/边界 |
| --- | --- | --- |
| `3Knkq0GISrtXoyAYj` / `qKV7rSB4SaS40iKFn` | Cloudflare custom/rate rules、origin、Turnstile plans/server validation；WordPress hardening/brute force/REST/nonces/Two-Factor | 18 URL；17 HTTP 200；旧 `/waf/plans/` HTTP 404 未使用；专属 error-codes 子页正文不足以解释 300030 |
| `OwMe5MsVabzJwVu2V` / `AznIi2P3oauyakiVb` | PHP 官方公告发现搜索 | 仅用于发现；Hostinger 精确邮件标题未搜到不表示通知虚假 |
| `9ceym2EsJRnPw8rfL` / `aTJgAVbxlKHxsLcpI` | PHP 首页、发行索引、支持周期、ChangeLog | 4 HTTP 200；从 PHP 首页核实 CVE、修补版本与公告 |
| `6doOtFPjGoEj6uqcy` / `Hy0NwRReFJrv3rX6K` | Turnstile errors、插页、Bot Fight Mode、bot score、PHP archive | 7 URL；旧 Free Managed Ruleset 专属路径 HTTP 404，改用有效总览 |
| `5ecUSFHuj8n4g6Lc1` / `laytsd3H15uTYNK2s` | Hostinger mail 文档发现 | 搜索用于发现，具体额度以随后官方正文核实 |
| `tmfDFmMtfzTGVBoBc` / `0aoudCFZoFyPCvwny` | 两个 PHP GHSA、两个 Ubuntu CVE、两个 Debian CVE | 6 HTTP 200；Debian 当前版本表未被正文抽取，不猜包号 |
| `CjMIIp1PALlQeUrKH` / `HIUcriB0ume6bCq1R` | Hostinger mail 两正文、Cloudflare managed rules/代理/StrictTLS | 7 URL；CloudPanel 猜测旧安全路径 HTTP 404，不用其证明升级方式 |
| `mC4D3Ex8zGszZMV90` / `kZPNquaIgvHg3figB` | OWASP 上传/拒绝服务、Cloudflare headers、Ubuntu USN、Debian DSA | 5 HTTP 200；DSA 无提取正文，不作为固定包号证据；其余正文已核对 |

核心引用链接已就近给出。Turnstile 独立于 DNS 接入的基础事实复用前一日研究的官方 get-started 来源；其计划、后端验证与失败处理本次已重新读取。对中国或任意网络的真实通过率、当前服务器是否失陷、Hostinger 账号实际可配置的源站功能、当前套餐发信收件路由，本文均不以公开文档代替现场验证。
