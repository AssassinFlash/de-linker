# 管理身份 MFA、应用密码与客户无障碍边界

研究票：[#564](https://github.com/AssassinFlash/de-linker/issues/564) · 研究日期：2026-10-22 · 仓库基线：`2b2e826768aa640fca386289ef69dad6b0dc3b6b`。

## 推荐结论

采用 WordPress.org 的免费 **Two-Factor 0.17.0**，只为现有管理员登记 **TOTP 认证器 + 一次性恢复码**；Hostinger 托管账户单独启用认证器二步验证。客户的浏览、注册、登录、询盘不增加强制 MFA。WordPress 的邮件配额正在受保护，管理员第二因素优先使用离线生成的 TOTP 与恢复码，避免把登录可用性绑在网站邮件上。此处是经过官方机制与现状核实的推荐；本研究未安装或启用任何新机制。[S1–S4, N1, H1]

现有 `terravolt` 应用密码保留到消费者迁移得到验证之后。它属于管理员的另一条 API 身份入口，启用网页 TOTP 后仍可工作，不能宣称整个管理员身份已由 MFA 覆盖。现有工程确有相关的文档索引读取配置与源代码，贸然撤销有中断该工程读取的风险；11:48:05 UTC 经协调者另行授权的原生只读 hash 比对，已证明 DE REST 配置唯一匹配这条应用密码；比对前后原生应用密码元数据完全一致，未进行 HTTP 认证重放或记录使用。[S1, S5–S7, N1–N3, N6]

## 已核实的实际状态

| 层 | 证据与时间 | 能确认的事实 | 边界 |
|---|---|---|---|
| WordPress 身份 | 协调者原生只读快照，09:37:47 UTC [N1] | 共 15 个用户：1 administrator、13 customer、1 subscriber；高权限身份 1 个；应用密码 1 个。文件编辑禁用已生效。 | 本轮复用有时间戳的原始快照，没有重新登录或改变身份状态。 |
| WordPress MFA | 同一快照的已识别安全插件路径为空 [N1] | 未识别到独立 MFA 安全插件。 | 这不能证明所有因素均未启用，也不能排除外部身份提供方、主机接入保护、MU/自定义认证、现有会话等其他路径。 |
| Hostinger 正确托管账户 | 独立 Chrome 标签，只读安全页面，约 11:35–11:40 UTC [H1] | 账户归属已私密核对。面板明确显示“双重身份验证：关闭”；另一个“新设备或共享设备验证：开启”。 | 两项是不同保护；没有点击开启/关闭，没有检查 Google 身份提供方自己的 MFA。 |
| Hostinger 可选方法 | 同一安全页 [H1] | 面板介绍认证器或电子邮件，且一次只能激活一种方法。 | 未进入启用流程，因此账户具体恢复流程、恢复码是否已存在均未知。 |
| 既有 API 凭证 | 原生元数据 [N2] | 管理员 user ID 1 有一条名称为 `terravolt` 的应用密码；创建记录 05-18 13:12:59 UTC，最后使用记录 10-18 16:36:54 UTC。 | 名称只是一项标签；不据此判断应删除、已泄漏、被攻击者使用或目前绝对闲置。原生仅每 24 小时更新一次使用记录，时间与 IP 不是逐请求审计。 |
| 当前工程消费者 | 本地配置与当前仓库源代码 [N3, S7] | `services/genie/index/inventory.py` 默认读 `~/.config/terravolt-builder/rest-de.json`；目标为 de-linker.com，配置了应用密码，用户名与既有管理员配置一致。 | 未进行 HTTP 认证请求；经后续 N6 已证明配置值与该原生凭证匹配，但没有观察到当前索引任务实际执行。 |
| 配置→原生凭证绑定 | 原生只读比较，11:48:05 UTC [N6] | 配置用户名匹配原生管理员；用 WordPress 自身 `check_password()` 在内存比对，唯一匹配名称 `terravolt`；元数据前后完全一致。 | secret 经 SSH stdin 输入，不进 argv/文件；不输出 hash，不调用认证分发或 usage recording，不更新 last_used。 |

所有账户地址、IP、密码值、会话原文都留在本机私密目录。报告不包含原始账号标识或凭证。

## Two-Factor 的当前版本、兼容性与维护来源

通过 Apify 于本次研究重新读取 WordPress.org 插件页与 `WordPress/two-factor` 官方仓库：

| 项目 | 官方可见值 | 解释 |
|---|---|---|
| 当前发布版 | 0.17.0，2026-09-25 | 下载链接为 WordPress.org 的该版本包。使用此稳定版作为验证对象，不使用较旧版本或开发分支。 |
| WordPress 要求 | 7.0 或以上 | 当前站点的 7.1.3 在声明范围内。 |
| Tested up to | 7.1.3 | 官方插件页明确给出；仓库 master readme 的字段写 7.1。前者包含补丁版本，后者没有单列补丁号。 |
| PHP 要求 | 7.4 或以上 | 当前已取证的 PHP 8.3 系列满足最低版本声明；这不代替当前站点的运行验收。 |
| 许可/费用 | GPL-2.0-or-later，WordPress.org 免费分发 | 无需购买新插件或外部 MFA 订阅。 |
| 本次重要安全修复 | 0.17.0 修复 REST/XML-RPC 使用普通密码绕过双因素要求的问题 | 安装时必须核对实际落地版本；旧版本不能按最新版的认证边界作承诺。 |

以上是维护者的支持声明与变更记录，尚未在本站 WordPress 7.1.3 + WooCommerce + 当前自定义登录流程中安装、执行或完成浏览器验收。不能把“官方 Tested up to”改写成“本站已经实测通过”。[S1, S2]

## 用户级 TOTP、恢复与客户边界

官方配置以用户为单位：管理员进入自己的 Profile → Two-Factor Options，登记认证器；验证正确动态码之后才保存有效的 TOTP key。用户可启用多个提供方并选择主提供方。插件源代码读取该用户自己的已启用提供方；未配置的客户不会仅因插件安装就自动具有已登记的 TOTP。[S1–S3]

推荐的管理员配置为 TOTP 主方法、Backup Codes 备用方法。官方默认生成 10 个一次性码；每次成功验证会删除已用码，数据库保存其 hash。恢复码应由业主保存至自己控制的密码管理器或离线副本；不可放进 Git、工单、截图、浏览器会话导出或共享验收产物。新一批恢复码的生成与替换是有状态操作，本研究未执行。[S1, S4]

客户侧保持现有身份与权限，不要求认证器、不强制登记、不添加全员 MFA 插件或登录代理。验收必须确认 Woo 的客户登录、待审身份、密码重置和访客询盘仍按当前行为运行。仅凭用户级配置机制，还不能跳过对实际客户流程的验证。管理员用 Woo 登录页登录时也必须实际进入其第二因素流程；不能只验证 `/wp-login.php` 一个入口。[S1, S3；本段的上线门槛是依据本站多个身份入口提出的实施要求]

邮件型第二因素不是本次优先项。TOTP 和恢复码验证不依赖网站 `wp_mail()` 发送新邮件，适合当前受到通知容量约束的情况；邮件型提供方会引入额外发信依赖。Hostinger 的账户二步验证与网站通知邮件是两个独立系统，不能把 WordPress 的发信配额推成 Hostinger 的限制。[S1, S3, S4, H1]

## 应用密码为什么仍是独立入口

WordPress 原生应用密码通过 HTTPS Basic Auth 供 REST/XML-RPC 使用，不能直接用于正常 `wp-login.php` 人工登录。Two-Factor 从 0.14.0 起默认允许应用密码的 API 认证，0.17.0 另外修复普通密码的 API 绕过问题。因此，交互登录要求 TOTP 与程序继续持有应用密码可以同时存在。[S1, S5, S6]

本地生产恢复快照的 WordPress 7.1.3 `wp_authenticate_application_password()` 在密码验证和扩展错误检查后，返回所属的原始 `WP_User`。它本身没有因“这段客户端只发 GET”就把管理员权限降成只读；endpoint 的权限检查仍然重要。`terravolt` 名称、文档索引 User-Agent、GET-only Python 客户端均不是服务器权限隔离。[N4]

当前仓库的 owned plugins/MU 范围未检出应用密码约束或 Two-Factor 相关过滤器。这个静态无匹配只限定已检查的自有源代码，不排除主机配置、第三方插件或其他外部限制。[N5]

实际消费者 `RestClient` 读取该配置并组成 Basic Auth，随后 GET 媒体库和产品列表以建立托管文档 inventory。当前代码不做账户管理写入。然而，窃取该凭证的人不受这份 Python 客户端的 GET-only 约束。这是保护管理员身份时必须单独处理的残余风险。[S7, N3, N4]

最小执行顺序：先保护交互登录；再在本地验证一个专用于该读取任务、权限经过明确约束的服务身份/接口，证明其能读所需媒体和产品数据、不能进行管理写入；替换实际消费者并读回任务成功后，才计划撤销旧管理员应用密码。当前没有足够证据指定某个内置 Woo 角色就一定满足这份完整数据读取需求；不能直接改成客户角色或删除 API 通道。无需为所有客户关闭 REST API。[S5–S7, N4；迁移次序为研究推荐，尚未实施]

## 可以先完成的本地工作与一次设备交接

下面是下一张实现票的具体可执行范围，本研究没有安装插件、登记因素或新建任何用户/密码。

| 顺序 | 执行者 | 具体动作 | 过关证据 |
|---|---|---|---|
| 1 | 工程执行者，独立本地快照 | 从官方稳定渠道取得并核对 0.17.0，安装到隔离实例；使用本地夹具管理员验证 TOTP 和恢复流程，邮件仅本地收集。 | 插件版本读回；正确/错误 TOTP；未完成 MFA 不建立已认证会话；恢复码只可使用一次。 |
| 2 | 工程执行者，同一本地实例 | 只给夹具管理员登记因素；逐入口检查管理员登录与 Woo 客户流程、注册/重置、EN/DE 访客联系和询盘；验证应用密码 API 边界。 | 客户无新增强制 MFA；管理员各交互入口都有因素要求；客户询盘保存行为正常；普通密码不能通过管理员 REST/XML-RPC 绕开因素；既有应用密码行为单独记录。 |
| 3 | 协调者 | 按已授权部署规则先备份，安装已验收插件，读回版本；不预填或传播业主生产 TOTP secret。准备 WordPress Profile 与 Hostinger Security 两个正确账户页。 | 可回滚、可读回；没有强制客户登记，没有误撤销现有应用密码。 |
| 4 | **业主本人设备，一次连续交接** | 在自己的认证器中分别登记 WordPress 和 Hostinger 的实际账户：各扫一个真实二维码、完成各自动态码验证；亲自收存提供的恢复材料。 | 两个服务分别显示已启用；新会话完成一次管理员 TOTP 登录；本次应有的恢复材料在业主手里。 |
| 5 | 协调者 | 对上线后的客户路径作必要读回；实施应用密码消费者迁移必须有上述权限与读取验收后再安排撤销。 | 交互身份保护、客户无障碍和程序身份边界分别有证据，不能用其中一项代替另两项。 |

必须交给业主设备的是**真实账户因素的持有与验证，以及恢复材料的保管**。两个服务有不同的秘密与动态码，不能用同一个确认动作假装两边都已完成；可以安排在一次设备交接中连续处理。Computer Use 的认证凭证交接要求也限制代理代填新凭证。本研究不会要求业主现在扫描测试二维码，不会拿本地夹具 secret 当生产因素。[S3, S4, H1；设备交接要求来自本任务边界及 Computer Use 认证凭证规则]

## 未知、证据边界与未执行事项

- 未证明 WordPress 的所有外部认证路径都没有 MFA；没有安全插件不等于所有层都没有 MFA。
- 尚未安装或本地验证 Two-Factor，故本站兼容性仍只有官方支持声明，缺运行验收。
- 既有 DE REST 配置与单条原生应用密码已由 N6 的只读原生 hash 比较精确绑定；这证明凭证对应关系，不证明当下任务已执行、当前网络可达性或每个 API endpoint 都可成功。
- `last_used` 是约 24 小时粒度的原生记录，不能当作完整 API 调用历史或入侵证明。
- 已证明的是索引 inventory 的源代码与本地配置用途；未核实当下 VPS 调度或具体执行进程，不能宣称每次 Genie 对话都会使用这把应用密码，或撤销后现有对话必然立即失效。
- Hostinger 二步验证关闭、新设备验证开启已从实际面板确认；Google MFA、Hostinger 具体恢复步骤与现存恢复码未知。尝试的旧 Hostinger 帮助文章链接已 404，本报告不从旧 URL 推断恢复能力，也未进入产生凭证的开启流程。
- 本次不安装、创建、撤销或展示凭证；不改密码、角色、会话、安全设置或客户 MFA；不发邮件、不调用模型、不购买服务，不触碰 ACF、DNS、生产代码或队列。没有 PR、合并或部署。

## 可复核证据与来源

本机原始研究目录：`/Users/chesterjohn/de-linker-data/incident-20261022/admin-identity-research/`，目录 0700，文件 0600。外部读取全部经 Apify；不提交原始账号、IP、凭证或带秘密的页面。

- **S1**：[WordPress.org Two-Factor 官方插件页](https://wordpress.org/plugins/two-factor/)，Apify run `JHNdud3RcfvErZy59`，2026-10-22 11:37–11:38 UTC 抓取。私密 `source-page-1.md`；包含 0.17.0 下载、兼容字段、逐用户配置与安全变更记录。
- **S2**：[WordPress/two-factor 官方 readme](https://github.com/WordPress/two-factor/blob/master/readme.txt)，同一 run；私密 `source-page-2.md`。这是抓取时的 master，不把它当作已安装生产版本。
- **S3**：[官方 TOTP provider](https://github.com/WordPress/two-factor/blob/master/providers/class-two-factor-totp.php)、[官方 Core](https://github.com/WordPress/two-factor/blob/master/class-two-factor-core.php)，同一 run；私密 `source-page-4.md`、`source-page-3.md`。抓取可见部分用于 TOTP setup 验证与逐用户 provider 读取，不把 GitHub 未完整展开的长文件当作全量源码审计。
- **S4**：[官方 Backup Codes provider](https://github.com/WordPress/two-factor/blob/master/providers/class-two-factor-backup-codes.php)，同一 run；私密 `source-page-5.md`，验证一次性码生成/hash/消费机制。
- **S5**：[WordPress REST 认证文档](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/)，Apify run `RcdjZEDHpPwbK7oN8`；私密 `official-page-5.md`。
- **S6**：[WordPress Core Application Passwords Integration Guide](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/)，run `JHNdud3RcfvErZy59`；私密 `source-page-6.md`。历史设计文章中的每 24 小时记录与返回原用户行为，另以 N4 的当前 7.1.3 快照源代码核对，不拿历史规划当作当前全部能力声明。
- **S7**：[当前仓库的文档 inventory 消费者](https://github.com/AssassinFlash/de-linker/blob/2b2e826768aa640fca386289ef69dad6b0dc3b6b/services/genie/index/inventory.py)，默认配置、`RestClient`、媒体与产品 GET 的具体调用。
- **N1**：协调者私密 `incident-20261022/account-audit/readback.json`；本研究摘取 `native-identity.sanitized.json`，09:37:47 UTC 的原生身份/插件/文件编辑状态快照。
- **N2**：协调者私密 `account-audit/application-metadata-private.json`；只摘取数量、标签、UTC 日期，不公开应用 UUID、原始 IP 或密码。
- **N3**：`config-purpose.sanitized.json`；仅记录目标、凭证存在布尔值、管理员配置用户名一致性、消费者路径和没有 HTTP 认证重放的边界；后续绑定状态引用 N6。未复制密码。
- **N4**：本机生产恢复快照 `wp-restore/wordpress/wp-includes/user.php` 的 `wp_authenticate_application_password()` 与 `class-wp-application-passwords.php` 的 `record_application_password_usage()`；版本与 SHA256 记录在 `native-core-source.sanitized.json`。
- **N5**：基线 owned `plugins/`、`mu-plugins/` 中对 `wp_authenticate_application_password_errors`、`wp_is_application_passwords_available_for_user`、`application_password_is_api_request`、`two_factor_` 的只读静态查询无匹配；范围不扩展为所有已安装第三方运行时。
- **N6**：`native-hash-comparison.sanitized.json`，11:48:05 UTC。协调者明确授权后，SSH stdin 将已有配置交给同一原生站点；直接只读获取 user ID 1 的应用密码元数据，在内存调用 `WP_Application_Passwords::check_password()`，仅输出匹配/名称等非秘密结论。为避免 `get_user_application_passwords()` 的缺 UUID 时惰性补写路径，比较使用原始只读 SELECT + 内存反序列化；未调用认证分发、usage recording、setter 或 HTTP。比较前后的原始元数据相等；secret/hash 未落盘、未进入命令参数或输出。
- **H1**：实际 [Hostinger Security 页面](https://hpanel.hostinger.com/profile/security/two-factor-auth)。`hpanel-security.private.ax.txt`、`hpanel-security.private.png`、私密账户归属核对 AX；`hpanel-security.sanitized.json` 保存布尔结论及原始证据 hash。

Apify 原始返回、URL/状态/抓取时间与每份抽取文本的 SHA256 在私密 `official-source-manifest.json`、`apify-official-run.json`、`apify-source-run.json` 中。首次默认文本抓取未保留部分插件元数据/GitHub 代码，随后用同一官方 crawler 的浏览器模式与不裁剪正文补足；另一 Cheerio actor 的启动返回 403，未购买/绕过，未用直接外网请求替代 Apify。
