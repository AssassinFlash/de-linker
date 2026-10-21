# 公开入口防机器人与垃圾通知：选项核实

日期：2026-10-21（Asia/Shanghai）。研究票：[核实公开表单的人机验证与垃圾判定选项](https://github.com/AssassinFlash/de-linker/issues/506)。所属地图：[公开入口防机器人与垃圾通知治理](https://github.com/AssassinFlash/de-linker/issues/505)。

这是实现前研究。没有改变代码、生产配置或数据，没有发邮件，没有打开本次垃圾链接。外部来源全部通过 Apify 抓取；本文的建议是依据资料和本站约束作出的推断，尚未替代后续处置策略决策。

## 已有证据与问题边界

主代理本次 Computer Use 在企业邮箱看到 Linker 的新询盘通知，正文标明 Contact form，Notes 与业主报告的垃圾内容一致；生产只读核对确认询盘 8009 为访客经 `linker_contact` 创建。线上处理器已执行 nonce、蜜罐、至少 3 秒签名时间和每连接每小时 3 次额度。这些事实记录于地图 Notes；本研究未重新操作生产。

仓库 `Contact/Handler.php` 与 `Inquiry/PublicGuard.php` 表明基础防护通过后会进入 `Inquiry/Sender.php`，创建询盘并以状态变化触发邮件。邮件排期与客户回执上限各有用途，均没有判断留言是不是垃圾。此次证据足以定位表单滥用，无法据此推断服务器被入侵。

## 官方资料核实

| 问题 | 一手资料给出的事实 | 对本站的含义（推断） |
| --- | --- | --- |
| nonce 能否替代人机验证？ | WordPress nonce 在有效期内可重复使用，不能防重放，也不应承担身份或权限控制；默认访客共享用户 ID 0。[S1] | 保留 nonce；另加机器人防护。会读取公开页面的机器人可以拿到表单字段。 |
| Turnstile 是否需迁 DNS？ | Turnstile 是独立服务，站点无需经 Cloudflare 代理；需要 Cloudflare 账号及客户端组件、服务端验证。[S2] | 可在现有 WordPress/Hostinger 架构试接，不必为此迁站或更换 DNS。 |
| 是否有可用免费档？ | Free 档支持最多 20 个 widget、每个 10 个 hostname、所有 widget 类型、无限 challenges/验证请求；分析回看最多 7 天，保留 Cloudflare 品牌。Enterprise 需联系销售。[S3] | Free 可作为本站首个验证候选，不以购买插件为前提；不要把免费档说成包含所有企业功能。 |
| 后端必须检查什么？ | 每次将客户端 token 送 Siteverify；token 有效期 300 秒、仅能验证一次。官方示例和最佳实践要求校验预期 action、hostname；支持 `idempotency_key` 安全重试。[S4] | 验证应在创建记录、账号、邮件或调用模型之前。仅插入前端组件无法保护直接 HTTP 提交。不同入口使用不同 action；生产域名显式允许。 |
| 动态 Genie 界面怎么放组件？ | 官方支持静态页面隐式渲染及动态内容/SPA 显式渲染；成功回调取得 token 后仍须服务端验证。[S5] | LC 表单与 React 工具可共用后端验证能力，分别按页面生命周期挂载组件。 |
| 无脚本、网络阻断和误判会怎样？ | 官方说明 Turnstile 依赖 JavaScript；网络、扩展、浏览器和检测错误可能让真人陷入重复挑战。[S6] 客户端有错误/超时回调和重试能力。[S7] | 必须设计可见失败、重试及联系团队的路径，不能无限转圈，也不能失败即默认放行。 |
| 怎样做内容垃圾判定？ | Akismet 的接口可处理 `contact-form`、`signup` 等，区分 spam、not spam 与错误；其示例把一般垃圾放入复核队列。[S8] | 内容判定与人机验证应分层；真人、打码服务或绕过检测的自动化仍可能提交垃圾。可恢复隔离是成熟处置模式。 |
| Akismet 是否免费适合本站？ | 官方定价将个人与商用分开，当前商用起档为每月 $9.95、按年付，含每月 500 次检查与 1 个站点。[S9] | 它是新增付费服务且需传输提交内容/IP 等数据，本轮没有采购依据；可借鉴隔离模式，不默认接入。 |

上述来源没有证明中国大陆任意网络都能稳定完成 Turnstile，也没有本站各地区、浏览器的成功率与耗时数据。本轮未实测这些网络。因此“中国及海外均无影响”属于**无法核实**，必须在选型试验中以实际访客路径验证。

## 明确推荐：Managed 按需显示，内容风险可恢复隔离

优先选 **Turnstile Free 的 Managed 模式，`appearance=interaction-only`**，与现有检查、可恢复隔离、邮件和 AI 预算组合。官方把 Managed 列为推荐模式，由风险决定是否显示勾选框；Invisible 始终隐藏组件。[S11] `interaction-only` 仅在需要访客交互时显示组件。[S12] 这适合业主“尽量不影响正常访问和询盘”的偏好。正常访客需要额外点击的比例仍须实测，不能承诺零误判或零等待。

以下为研究建议，处置与参数留给后续决策票确认：

1. **保留现有低成本检查，补服务端人机验证。** 覆盖联系、询盘、注册及 Genie 中创建记录、发邮件或消耗模型资源的入口。正常浏览商品无需挑战。推荐表单开始填写/工具首次实际交互时预热验证，提交时检查 token 可用；直接提交而未预热时，验证成功后自动继续原提交，不要求客户再点一次发送。官方支持 `execution=execute` 按需启动，也建议尽早启动以降低提交等待。[S5][S12] 在首次表单交互时启动是本站保留静态页面体验的折中选择；不能把“等点击发送才启动”当作天然更快。
2. **在业务副作用前判断内容风险。** 针对明显无关的转账/中奖诱导、重复投递、相同垃圾链接等组合信号评估；单独俄语、国别或合法网址不构成拒绝依据。可疑内容先进入有容量约束、可复核恢复的隔离区，暂停即时团队通知和自动回执。隔离是否形成 Woo 询盘及恢复流程仍需明确，避免把垃圾当正式商机或把隔离区变成无限存储入口。
3. **给邮件和 AI 资源分别设预算。** 在单连接检查之外，评估会话、目标邮箱、重复内容及全站额度；不同公开入口不能各自形成绕行通道。邮件投递节流只决定何时发送，须在入队前控制滥用。客户填入的邮箱并非已验证归属：未经确认的回执使用固定内容并限制频次，避免把任意留言反射给第三方。
4. **失败路径可见且受控。** token 失效允许刷新，暂时网络失败保留用户输入并给重试方式；验证服务持续不可用时不能悄悄放行，也不能丢失用户输入。是否允许进入受限隔离通道、由团队人工接回，需要处置策略决策，不能把备用通道做成无限免验证提交口。

客户端使用官方重试及过期刷新能力，并实现 success/error/expired/timeout 状态；服务端设有界超时、按同一提交标识重试及去重。长时间填写后刷新过期 token，不清空产品草稿和留言。[S4][S7][S12] JavaScript 禁用、第三方脚本阻断或持续故障时，显示明确说明、保留输入、提供重试和团队联系地址；不默认增加免验证 HTTP 提交旁路。若业务选择“先暂存待人工核验”，须另受容量、去重和预算约束，且不能立即发信或调用模型。

**本方案不启用 pre-clearance。** 普通 Turnstile 的一次性 token 直接由本站后端验证即可，无需代理站点。[S2] pre-clearance 则额外发 `cf_clearance` cookie，用于同一 Cloudflare zone 后续请求绕过其 WAF 挑战；官方要求 widget hostname 匹配有 WAF 规则的 zone，且功能默认关闭。[S13] 不应把它作为现有 Hostinger 表单接入的前提，也不能拿 cookie 代替本站每次提交的 Siteverify 检查。若以后引入边缘 WAF，再单独决定 zone/代理与源站保护，不把独立 Turnstile 和 Cloudflare 边缘挑战混为一项。

现有 3 秒规则应列入快速填写/密码管理器自动填充夹具：代码会拒绝所有不足 3 秒的提交，条件本身不区分真人。蜜罐也须验证浏览器和密码管理器不会误填隐藏字段；本轮没有观察到实际自动填充误伤。每直接连接地址的共享额度可能影响同公司网络的多人提交，故应把连接额度与会话、已验证客户、全站预算组合；这些是代码机制带来的待测边界，不能未经证据直接删除原有防护或随意信任转发 IP 请求头。

不建议用单个恶意域名黑名单作为主要措施：本次 URL 仅是样本，域名/路径变化即可能绕过。不建议仅增加等待秒数或只收紧单 IP 次数，这些措施仍不能判断内容，还可能影响共享公司网络中的真实客户。这里的边界分析来自本站公开表单机制和上述来源的综合推断，未开展绕过攻击测试。

## 实现前应写进验收的条件

- 所有有副作用的公开入口均列清楚；每条路径在创建账号/记录、邮件入队或模型请求前执行策略，不能只保护某个页面按钮。
- token 缺失、伪造、过期、重复使用、错误 hostname/action、并发重复提交均有明确结果；网络错误与“判为垃圾”分开记录，不把服务错误当已通过。
- 用正常国际客户资料、带真实产品网址的询盘、俄文正常留言及本次垃圾样本作夹具，验证不会按语言/链接一刀切。阈值、隔离保留期、容量与全站预算由运营证据或业主认可的初始参数决定，本文不凭空指定数字。
- Cloudflare 提供通过、失败、已使用 token 等 dummy keys，适合本地自动化；生产密钥不会接受 dummy token。[S10] 在本地/评审站用该机制测试，所有邮件按既有纪律重写 tester，并以 Outbox 收件人/数量断言验证路由，不向真实第三方发送攻击邮件。
- EN/DE、390/1440 下检查等待、过期、重试、失败、隔离后反馈及正常成功；再用中国及目标海外网络检查真实 widget 可完成性。真实可用性验证与自动化 dummy-key 通过分别记录。
- 生产验收只读核对配置、防护调用与观测记录，不以在线恶意提交或真实群发证明有效。

## 来源与抓取记录

抓取日期均为 2026-10-21 UTC。Apify actor 为 `apify/website-content-crawler`，`cheerio`，深度 0；内容与 HTTP 状态保存在本目录 `raw/`。原始数据不包含本站用户提交内容或凭证。

| ID | 官方来源 | Apify run / dataset |
| --- | --- | --- |
| S1 | [WordPress Nonces](https://developer.wordpress.org/apis/security/nonces/) | `sL0wSgo35cBZxWF7X` / `GjaMBbBlOz6HcUODL` |
| S2 | [Turnstile Get started](https://developers.cloudflare.com/turnstile/get-started/) | 同上 |
| S3 | [Turnstile Plans](https://developers.cloudflare.com/turnstile/plans/) | 同上 |
| S4 | [Turnstile Validate the token](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/) | 同上 |
| S5 | [Turnstile Client-side rendering](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/) | `UkGrXwiOoGK89iqRi` / `FdjpGqbSD6pBB1kZf` |
| S6 | [Cloudflare Challenge solve issues](https://developers.cloudflare.com/cloudflare-challenges/troubleshooting/challenge-solve-issues/) | 同上 |
| S7 | [Turnstile Client-side errors](https://developers.cloudflare.com/turnstile/troubleshooting/client-side-errors/) | 同上 |
| S8 | [Akismet Comment check](https://akismet.com/developers/comment-check/) | `sL0wSgo35cBZxWF7X` / `GjaMBbBlOz6HcUODL` |
| S9 | [Akismet Pricing](https://akismet.com/pricing/) | 同上 |
| S10 | [Turnstile Testing](https://developers.cloudflare.com/turnstile/troubleshooting/testing/) | `UkGrXwiOoGK89iqRi` / `FdjpGqbSD6pBB1kZf` |
| S11 | [Turnstile Overview](https://developers.cloudflare.com/turnstile/) | `4Q966ituh8eNTIDLC` / `6nPGH7D4q8IUpzPGh` |
| S12 | [Turnstile Widget configurations](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/widget-configurations/) | 同上 |
| S13 | [Cloudflare Clearance](https://developers.cloudflare.com/cloudflare-challenges/concepts/clearance/) | `bCYgx7ch1TtEwAVPc` / `WctPvETYYOFrL8mxp` |

首轮 8 条抓取中，一个旧 widget-configurations 路径返回 HTTP 404，未用于任何事实结论（actor 将其请求记作完成不代表页面存在）；其余 7 条 HTTP 200。第二轮 4 条均 HTTP 200。第三轮 3 条均 HTTP 200，其中旧 pre-clearance 路径只有导航壳，无实质正文，未作为其要求的证据。第四轮按 Overview 链接取得 Clearance 正文，HTTP 200。原始失败/不足项保留，以免把失败检索当成有效证据。

[S1]: https://developer.wordpress.org/apis/security/nonces/
[S2]: https://developers.cloudflare.com/turnstile/get-started/
[S3]: https://developers.cloudflare.com/turnstile/plans/
[S4]: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
[S5]: https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/
[S6]: https://developers.cloudflare.com/cloudflare-challenges/troubleshooting/challenge-solve-issues/
[S7]: https://developers.cloudflare.com/turnstile/troubleshooting/client-side-errors/
[S8]: https://akismet.com/developers/comment-check/
[S9]: https://akismet.com/pricing/
[S10]: https://developers.cloudflare.com/turnstile/troubleshooting/testing/
[S11]: https://developers.cloudflare.com/turnstile/
[S12]: https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/widget-configurations/
[S13]: https://developers.cloudflare.com/cloudflare-challenges/concepts/clearance/
