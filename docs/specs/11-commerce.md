# #11 商务链 `linker-commerce`

依据：`docs/research/2026-10-09/account-workspace.md`、`mail-root-cause.md`、AGENTS.md §1–§3，账号审批=票据 73（业主 2026-10-11 裁定）。原则：Woo 原生能力优先，自定义只在 Woo 没有答案处。

## 用户旅程（EN / DE 文案按 AGENTS.md 规则逐处写，此处只给语义）
1. **访客**：看产品分类与产品，看不到价格（价格位显示 "Log in for prices" / "Preise nach Anmeldung"）；可用 Genie 与配置器；可把产品加入 Lösungsentwurf（按会话保存）。
2. **注册**（Woo 原生 My Account 注册表单 + 字段）：公司名、增值税号（VIES 实时校验，失败可提交但标记）、地址、角色（安装商 / EPC / 经销商）、姓名、邮箱、密码。**注册即 pending（票据 73）**：账号在团队批准前读站如访客；客户语言随注册写入 WP 用户 `locale`（询盘同源的取语规则）。邮件：注册确认（RegistrationReceivedEmail，Woo 原生欢迎信已关）+ 公司"新客户"提醒（含审批状态行与后台直达链接）。
3. **审批**：后台首页原生仪表盘小工具展示待审卡片，顶栏红旗在任意后台页打开同一审核抽屉；Accounts 菜单通向原生列表历史。全部状态随时可再决定，Restrict / Reject 必须带客户可读原因，经既有邮件链告知；相同决定重复提交不重复发信，限制/拒绝的原因变更也通知。资料页与用户列表保留状态及深链，原 GET / 资料表单写入通道在对等验证后移除。权限为 `edit_users` 加每用户 `edit_user`，只审核纯 customer。详情与原生优先证明见 `accounts-admin.md`。
4. **四态 × 界面**：
   - **approved**：看价；Lösungsentwurf 合并会话内容；产品页按钮 "Add to solution draft / Zum Lösungsentwurf hinzufügen"；可提交询盘。
   - **pending**：与访客同视图——浏览无价产品、Genie 咨询（无价）、可在请求页或联系页发送询盘；不可看价（价格位 "Prices after approval / Preise nach Freigabe"）、不可进账户工作台（`PendingGate` 把账户端点送回审核页）；可以提交询盘，账户审核页的访问规则由账号票维护。
   - **restricted**：保留工作台（询盘、资料、文件仍可读）；不可看价（价格位 "Not available for your account / Für Ihr Konto nicht verfügbar"）；可以提交询盘，账户中仍显示限制原因。
   - **rejected**：登录被挡（`wp_authenticate_user`，登录表单显示状态与原因去向；拒绝同时终结该账号的全部登录会话）。
5. **询盘提交**（#246，业主 2026-10-17）：原 checkout 地址 `/proforma-request/`、`/de/proforma-anfrage/` 不变。访客填写姓名、邮箱、公司（选填）、一个开放留言框（选填）与隐私同意，不问国家、地址、VAT 或电话，不自动注册。左边表单、右边可编辑的 Lösungsentwurf；已登录客户的回复资料折叠为一行，可展开更改本次询盘资料，留言与发送按钮直接可用。产品随询盘带上；空草稿可以只留言，但产品和留言均空时拒绝。访客、pending、restricted、approved 共用发送入口，价格门保持现状。提交后原生 Woo 感谢页与回执保留，状态 `wc-inquiry-received`，库存不扣减。回执与感谢页给访客一个可选注册链接（本次邮箱预填；须带正确订单 key 才能将该询盘附到新账号）。地址和 VAT 从账号已有数据带入，或由团队开 Proforma 时补。
6. **公司侧**（Woo 后台订单页，角色 shop_manager）：订单标题 "Inquiry #"；按钮 "Issue Proforma / Proforma ausstellen"：生成 PDF、状态改 `wc-proforma-issued`、给客户发邮件（附 PDF 链接，不附件）；之后手动 `completed` 或 `cancelled`。无其他动作。后台把状态直接改成 `wc-proforma-issued` 走同一条签发（`Issuer::ensure_issued`，钩在 `woocommerce_order_status_proforma-issued`）：号与 PDF 写上之后，客户侧才有下载入口。没有银行账户时按钮不出现，状态改过去也不签发——见下节，不补造账户。
7. **客户账户**（Woo My Account，端点改名）：Inquiries / Anfragen（列表：编号、日期、状态、金额、PI 下载）、Saved solutions / Gespeicherte Lösungen（定名，账户页与 `POST linker/v1/solutions` 的保存结果；保存的方案与设计报告 PDF，来自 #14）、Company / Unternehmen（资料与地址）、Documents / Unterlagen（本账户所有 PI 与设计报告）、页面顶部 "Your contact person / Ihre Ansprechperson"（姓名、邮箱、电话，来自设置）、每条询盘上 "Request again / Erneut anfragen"（复制为新的 Lösungsentwurf）。移除：订单、付款方式、下载（Woo 原生端点中不需要的隐藏）。

## 模块（PSR-4 `Linker\Commerce\`，一类一文件，各有测试）
- `Registration`（字段、VIES 客户端、角色元数据、提醒邮件）。
- `Registration\Approval`（**审批权威，票据 73**：状态机、读写与审计、登录拦截；唯一的 meta 读写方）。
- `Registration\ApprovalAdmin`（用户列表状态列及列表/资料页审核深链；只读）。
- `Registration\AccountsAdmin` / `AccountsTable` / `AccountsController`（原生后台入口、历史与受权限/nonce 保护的 POST 决定），`Accounts` / `RegistrationInformation` / `AccountSignals`（同一审批权威、动态注册资料与检查线索）。
- `Gating`（价格隐藏：模板过滤 + `wc/store/v1` 价格置空；可加入 Lösungsentwurf 与发询盘不受账号审批限制；`rfq_only` 产品标记显示 "Quoted per project / Angebot pro Projekt"）。`rfq_only` 读英文商品的标记：德语孪生经 `linker_commerce_facts_product_id`（linker-i18n 回答，与选型事实同一入口）换成英文商品再读。孪生上残留或缺失的 `tv_b2b_product_mode` 照旧留作数据（Polylang 免费版不同步 Woo meta），任何读取都必须走这条事实 ID 路径，永不直接对孪生 `get_post_meta`（2026-10-17 快照里 1957 的德语孪生 6800 没有自己的标记，德语产品页曾向已批准账号显示 33.250,00 €）。价格位置印什么由 `CommerceState::reason( $product, CARD|PAGE )` 决定，一个函数两个表面：`CARD`（Woo 自己的价格 HTML、Store API 的 `price_html`、Lösungsentwurf 与询盘的行、草稿汇总）先说商品——线上 2026-10-18 访客的 `/wc/store/v1/products/1957` 的 `price_html` 是 "Quoted per project"；`PAGE`（产品页、对比页、Genie 的产品卡）先说账号——同日线上访客的 1957 产品页是 "Net price after partner sign-in"。产品页与对比页共用 `ProductView::price_html`：访客 "Net price after partner sign-in"、待审 "Prices after approval"、限制 "Not available for your account"，已批准账号在按项目报价的商品上 "Quoted per project"、无价商品 "Price on request"；Genie 的产品卡读同一行（#242，见 13-genie.md「价格跟账号走」）。其他插件经过滤器 `linker_commerce_visitor_sees_prices` 问同一条规则（唯一回答者 `PriceDisplay::sees_prices`）。
- `Inquiry`（状态注册与颜色、网关类 `ProformaGateway extends WC_Payment_Gateway`、减库存关闭、订单标题与列表列；`Checkout::gateways` 只保留询盘网关，不按审批状态拦截）。
- `Proforma`（PDF：dompdf 或 mpdf（MIT/LGPL），模板 EN/DE，编号 `DLK-PF-YYYY-NNNN`（按年计数，选项 `linker_commerce_proforma_prefix`，空则 `DLK-PF`），银行条款（设置页填写），有效期 30 天，税额行按 Woo 税设置显示；生成后存 `wp-content/uploads/proforma/<order>/` 私有目录，账户内经鉴权下载）。线上 `de-linker.com` 的号是 `DLK-PF-年份-订单ID`（下单即写入账本，不是后台按钮才编）；本站保留同一前缀，序号按年递增，不沿用订单 ID。
- `Mail`（`wp_mail` 统一：内部通知一封主信 To 内部通知收件人 + Bcc（设置页，见下文“内部通知收件人”）；每封投递在 WooCommerce 日志 `linker-mail` 留一行 info（主题、收件人与 Bcc，客户回执的行里因此有客户邮箱；保留期 = WooCommerce → Settings → Advanced → Logs 的 Retention period，线上未改即 Woo 缺省 30 天，到期由 Woo 自己删；文件在 `wp-content/uploads/wc-logs/`，目录有 Woo 写的 `.htaccess` deny from all，只能经后台 WooCommerce → Status → Logs 看，需要 `manage_woocommerce` 权限，即管理员与 Shop manager）；队列 Action Scheduler；失败重试：1、5、30 分钟、2、6、12、24 小时；Woo 事务邮件也经队列；VAT 审核提醒只在结论变化时发；本地隔离下写文件）。**测试邮件开关**（AGENTS.md 测试邮件纪律，2026-10-11；`Mail\TestMode`，与 #73/#94 同一实现）：选项 `linker_commerce_test_mail_to` 设了地址时，Outbox 的发送路径把每封信的全部 To/Cc/Bcc 重写成该单地址（每封信只发一份），队列里的消息保留原路由——多收件路由的正确性以队列数据（`_linker_mail_message`）断言，不做多封实发。默认未设=生产路由；`wp linker-commerce test-mail on|off|status` 设与撤（默认收件人 chester@de-linker.com，`--to=` 可换），不是设置页字段（#17 切换冒烟时开，验证后撤）。
- `Account`（端点注册、模板、对接人设置、再次询盘）。
- `Vocabulary`（gettext 覆盖 Woo 自带字符串：Cart → Solution draft / Lösungsentwurf 等；全部通过 `.po`）。
- `Settings`（后台一页：对外团队邮箱、内部通知收件人、发件人与 Bcc 列表、对接人、银行条款、PI 前缀）。
- `Health`（`Monitor`：WP cron daily 依次 GET `linker_genie_url`/`linker_engine_url` 的 `/health`（实例配置，本地 `just serve` 写、切换 #17 写），非 200 或不可达或地址为空 → 经 `wp_mail`（即 Outbox 队列）发内部通知，To 内部通知收件人（`Options::notify_to()`）+ Bcc（#221 起；此前 To 对接人）；两服务都健康不发。主题与正文 EN 先行、DE 独立撰写，对抗评审记录 `docs/acceptance/2026-10-11/67/copy-review.md`）。

## Mail：内部认证 SMTP（#297）

2026-10-18 的最新裁定与证据见 [#297](https://github.com/AssassinFlash/de-linker/issues/297)：仅改可见 From 后，内部摘要仍进 sunriver 垃圾箱；`hsendmail` 的服务器信封与 sunriver From 不对齐，且没有 DKIM。内部通知改走 `smtp.hostinger.com` 的认证 SMTP，客户邮件继续 PHP `mail()`，From 继续 `sales@de-linker.com`。下面 #288 是此前的取证记录，其“仅改内部身份解决”的推断由本次实际摘要头取代。

- **原生传输入口**：`Mail\Module` 注册 `phpmailer_init`，由正在投递的 `Outbox` 选择传输。六类内部生产者通过同一个 `Message::mark_internal()` 添加 `Message::INTERNAL_HEADER`（名称和值只有一份常量）；PHPMailer 清头也由该常量解析名称。标记随队列、重试与 tester 重写保留，出站 MIME 移除。收件人、主题、From 不用于猜测内部身份；未标记消息使用 `isMail()`。
- **凭据唯一来源**：`Mail\InternalSmtp` 通过 `Settings\PrivateConfigDirectory` 定位 `$HOME/.config/terravolt-builder/sunriver-smtp.env`，读取 `LINKER_SMTP_HOST`、`LINKER_SMTP_PORT`、`LINKER_SMTP_USER`、`LINKER_SMTP_PASS` 和可选 `LINKER_SMTP_SECURE`。`Options` 由构造函数注入。文件在 web root 外，仅业主放置密码并限制权限；执行者和 Claude 不读取、创建、传递密码。手工逐行解析 `KEY=VALUE`：只在首个 `=` 切分，剥除成对外围单/双引号，忽略空行和以 `#` 开头的整行注释；值内的 `;`、`#`、`=` 原样保留，不执行 shell、不插值、不使用 INI 语义。凭据不进入 WP options、队列、日志、仓库或后台字段；测试只注入假文件。
- **身份与加密**：SMTP 用户须同时等于注入的 `Options::notify_sender()->email` 和本封实际 From；不匹配则记录 `identity_mismatch`，立即以原 From 和原消息走 PHP `mail()`。加密由 `LINKER_SMTP_SECURE` 决定：省略时端口 465 为 `ssl`、其余为 `tls`；显式空值表示不加密，本机 sink 在测试中显式设置。生产代码没有依主机名判断的测试例外。证书校验保留原生缺省；每次发送前后关闭连接、清空认证、恢复 `mail()`，并恢复 PHPMailer 的 Port=25、SMTPAutoTLS=true 原生默认值。
- **故障回退与最近结果**：缺文件、不可读、字段/格式无效时直接 PHP `mail()`，摘要提示未配置。内部 SMTP 的连接、TLS、认证、投递或身份失败时，**同一封消息立即 fallback 到 `mail()` 一次**，包括每日摘要；SMTP 成功不走 fallback。`Mail\SmtpOutcome` 在 `linker_commerce_internal_smtp_outcome` 只保存 `{at: Unix秒, status: success|failure, reason: smtp_failure|identity_mismatch|空}`；失败另以固定分类写 `linker-mail`，不保存服务器文本。fallback 成功不覆盖该 SMTP 失败；下一次 SMTP 成功才更新最近结果。`Health\InternalMail` 每封摘要仅一个健康项，报告最近 SMTP 失败时间/分类或成功时间；无记录时明确尚无尝试，不把“配置存在”当作成功。失败的摘要同样 fallback；SMTP 与 fallback 都失败才沿原 Outbox 梯重试。全部内部错误共用 `InternalSmtp::FAILURE_MESSAGE`，协议 debug 关闭。
- **配额与重试（Spec 3）**：共用 `Throttle` 的 8/分钟、80/滚动 24 小时。一个逻辑尝试占一个 slot：SMTP 最多一次，失败后 PHP mail 最多一次，所以任一通道的本站尝试数都受 8/80 约束；双失败才入重试。研究 `docs/research/2026-10-09/mail-root-cause.md` §3、§9（2026-10-09 经 Apify 取证）列出：服务器 PHP mail 为 10/分钟、100/滚动 24 小时；Hostinger SMTP 按每个邮箱计额，免费试用 100/滚动 24 小时，Business Starter 1000/滚动 24 小时（原始来源：[Hostinger Mail limits](https://www.hostinger.com/support/4625828-parameters-and-limits-of-hostinger-email/)）。本站预留后的 8/80 低于这两类限额；**sunriver 自己的发信也共用该邮箱 SMTP 配额**，不能把本站限速当作整个邮箱的用量。实际套餐字段 `sunriver_mailbox_plan (hPanel)` 与 `sunriver_mailbox_daily_limit (rolling 24h)` 由 Claude 部署时读取 hPanel 后填写，不推测套餐。重试仍为 1、5、30 分钟与 2、6、12、24 小时；To/Bcc 随同一封消息走，测试只改投递副本。
- **HOME 与网页上下文（Spec 2）**：当前树的 `QueryEmbedding` 已随 VPS 索引方案退役（spec 10）；退役前它直接使用 `getenv('HOME')` 拼接私有目录，没有独立 helper 可调用。本票将同一 HOME 机制提取为 `Settings\PrivateConfigDirectory`，SMTP 不再另写一份目录定位代码，也不恢复退役的查询编码器。线上 web PHP 的 HOME 仍由 wp-config 提供。员工只读 `GET /wp-json/linker/v1/mail-health`（`manage_woocommerce`）返回 `smtp_configured`、翻译后的状态标签及 `last_outcome`，不返回路径或配置值；README 要求先在已登录后台的浏览器上下文读回，再用 CLI 触发单封摘要，两者不能互相替代。
- **原生优先证明**：WordPress 已附带 PHPMailer 和 `phpmailer_init`，无需新 SMTP 插件、依赖或传输协议实现；Woo `TeamEmail` 只给出内部身份和标记，Outbox 负责已有队列边界与通道选择。全站 SMTP 插件会改变客户邮件通道，无法满足本票的身份分流。
- **本地证明与生产验收分开**：`InternalSmtpTest` 用自启动的 loopback sink 做真实 AUTH/投递及失败后重试，客户与缺配置邮件落本地文件；`NotificationRoutingTest` 验六类生产者的队列标记与身份；CI 在既有临时实例跑同组测试。生产的 sunriver 收件箱、`dkim=pass d=sunriverinverter.com`、`dmarc=pass` 由 Claude 部署后以单封摘要验证，未验前本票不算生产完成。操作与回滚见 `docs/acceptance/2026-10-18/297/README.md`。

## Mail：Hostinger 投递证据（#288，历史证据）

[PR #291 第 1 轮评审](https://github.com/AssassinFlash/de-linker/pull/291#issuecomment-6238959144) 记录了 Claude 在 2026-10-17 18:42–18:51 UTC 的生产取证：同样的 `wp_mail()` 消息、可见 From `Linker <sales@de-linker.com>`，先不设 Sender，再通过 `phpmailer_init` 把 Sender 设为 `sales@sunriverinverter.com`；探针确认钩子执行，`Mailer=mail`、Sender 为指定地址。

| 取证项 | 不设 Sender | 设置 Sender 后 |
|---|---|---|
| Return-Path | `noreply@srv1798.main-hosting.eu` | 相同 |
| SPF | `pass`，核验 `noreply@srv1798.main-hosting.eu` | 相同 |
| DKIM / DMARC | `none` / `none` | 相同 |
| 客户 QQ 邮箱 | 收件箱 | 收件箱 |
| sunriver（Hostinger 入站） | 垃圾箱，`X-Spam: Yes` | 相同 |

生产的 `sendmail_path` 是 `/usr/sbin/hsendmail -t`。Hostinger 强制覆盖信封为服务器地址，之后经 MailChannels 发出；站点设置 PHPMailer Sender 对实际信封没有效果。SPF 已按 `main-hosting.eu` 通过；`de-linker.com` 的 `_dmarc` 记录为 NXDOMAIN，没有 DMARC 对齐判断。因此不提供信封设置，也不添加替代信封机制。

sunriver 的垃圾箱结论来自 Hostinger 入站过滤器（Cloudmark `X-CM-*`）对 From 域 `de-linker.com` 的判断，不能归因于已经通过的 SPF。2026-09-30 的对照邮件 From 为 `sunriverinverter.com`，进入收件箱。内部通知由 #286 使用 sunriver 发件身份解决；客户可见 From 按 AGENTS.md 2026-10-17 裁定继续为 `sales@de-linker.com`，客户邮件已记录为 QQ 收件箱。以上改前/改后证据完成本票的生产取证要求，无需部署信封代码或再次实投。

内部身份统一由唯一公开读取方法 `Options::notify_sender()` 返回只读 `Mail\Identity`（`name`、`email`），供 `Mail\TeamEmail`、`Contact\Emails\TeamMessageEmail` 与 `Health\Monitor` 使用。Woo 原生发件人设置继续控制客户 From；Outbox 保留捕获时的 From 和收件路由，投递与重试沿用现有路径。`NotificationRoutingTest` 按通知类型分别断言队列 To/Bcc、From 和各邮件 ID 的 Reply-To；健康告警单独测试。

## 共用询盘入口（#246，供 #244 / #250）

`Inquiry\Sender::submit(Contact\Submission $details, bool $with_draft = true): WC_Order|WP_Error` 是“发一份询盘”的唯一业务入口。`Submission::from_post($fields, false)` 校验姓名、邮箱、同意与字段长度，留言可空；`lang` 经 Polylang 的语言模型解析，未提供时才读当前请求语言。公开调用方必须在调用前验证 nonce 与 `Inquiry\PublicGuard`（签名开始时间 + 空蜜罐；最短 3 秒是本票的初始防自动提交阈值，非行业常量）。只有客户实际点击发送的请求才调用该入口。Sender 不接收客户端的 customer_id、产品、价格或合计。

- 请求页：`admin_post[_nopriv]_linker_inquiry` → `Inquiry\Handler::process()` → Submission → Sender。表单语言也决定验证错误与失败回跳语言；失败保留四个输入值，草稿不变。`Handler::process()` 是可重复夹具测试的公开请求边界；`handle()` 负责 transport 与 redirect。
- 产品来自当前 Woo 会话：校验原生草稿有效性与库存，`WC_Checkout::create_order()` 装配产品、数量、价格原因与账号已有地址/VAT。成功才清空草稿。右栏更新数量与移除行使用 Woo 的 `update_cart` + `woocommerce-cart` nonce，不另造草稿存储。
- 联系页：可见字段与外观不变，仍走原 contact admin-post、原每连接限流；通过相同 bot guard 后调用 `Sender::submit($details, false)`。创建没有产品的 Woo 询盘，保留客户原草稿。主题选择写入 `_linker_inquiry_topic`，在团队信与后台来源列可见。
- 两个门的来源为 `_linker_inquiry_source=proforma|contact`，在 Woo 原生询盘列表显示，状态均为 `inquiry-received`。同一条状态迁移触发既有 `InquiryReceivedEmail` 与 `NewInquiryEmail`；团队信继承 `Mail\TeamEmail` 并调用 `notify()`，收件人仍由下节 #221 的设置读取。多收件路由只以 Outbox 数据断言，无实发测试。
- #244 的摘要与预填应接这一个入口的经验证数据，不另造记录；#250 在确认卡实际发送时调用同一入口，须保留该调用方的 nonce、bot guard 与客户确认。当前入口只接受当前会话草稿，传入的产品/价格字段不会参与创建。
- 可选注册：`Inquiry\AccountLink` 以 Woo 订单 key 校验持有者，只允许客单且注册邮箱与该单邮箱一致；不以邮箱匹配开放其他询盘，也不自动建账号。价格仍须批准。

原生优先证明：LC 动态 checkout 模板仍承载页面，布局在 `content/livecanvas/inquiry/`，样式进入 WindPress 卷。短代码只装配转义数据、语言文案、nonce 与 Woo 产品行。LC 的产品循环没有“当前 Woo 会话草稿”与“按 nonce 接收公开询盘”的能力；Woo 原生 checkout 要求地址等账单字段且不能同时表示联系页的无产品消息，故自定义窄表单 adapter；订单创建、存储、四状态、邮件、原生草稿更新与感谢页全部沿用 Woo。原生 AJAX checkout 另挂同一 PublicGuard，避免绕开公开表单的机器人校验。

## 内部通知收件人（#221，业主 2026-10-17；#286 发件人拆分）

客户团队邮箱与内部通知的收件人、发件人分开设置，互不回落：

| 用途 | 读取 | 设置（WooCommerce → Settings → Inquiries） | 缺省 |
|---|---|---|---|
| 客户看得到的团队邮箱：Proforma 卖方邮箱、页面 mailto（产品页联系带、联系页直达地址、邀请带）、Genie 转人工句（`linker/handoff-team`）、对接人缺省 | `Options::team_mailbox()` | Team mailbox（`linker_commerce_team_to`） | `sales@de-linker.com` |
| 内部通知的收件人：新注册、VAT 复核、新询盘、联系表单留言、每日摘要、服务健康告警 | `Options::notify_to()` | Internal notifications → Recipient（`linker_commerce_notify_to`） | `sales@sunriverinverter.com` |
| 内部通知的发件人地址（名称固定为 `Linker`） | `Options::notify_sender()->email` | Internal notifications → Sender email（`linker_commerce_notify_from`，紧邻 Recipient） | `sales@sunriverinverter.com` |
| 内部通知的抄送 | `Options::notify_bcc()` | Internal notifications → Blind copies（`linker_commerce_team_bcc`，沿用原选项名，线上值不迁移） | 空 |

内部通知的 From 为 `Linker <内部发件地址>`（#286；默认 `Linker <sales@sunriverinverter.com>`），空值、无效地址或非字符串值回到此默认值。`Mail\TeamEmail` 与联系留言的 `Contact\Emails\TeamMessageEmail` 通过 Woo 原生 `get_from_name()` / `get_from_address()` 提供发件人，Woo 只在发送该封信时安装过滤器；健康告警是普通 `wp_mail()`，显式携带同一内部发件人头。Outbox 在捕获时将已解析的 From 固化到队列消息，之后重试保留。客户邮件继续读取 WooCommerce → Settings → Emails 的发件人设置（线上 `Linker <sales@de-linker.com>`），内部设置不改该值；两类邮件的 Reply-to 规则不变（与客户相关的内部通知回复客户，联系留言回复访客，摘要与健康告警不新增 Reply-to）。

**新增一封内部通知的唯一做法**（#243"让 Linker 联系我"等）：继承 `Mail\TeamEmail`（`WC_Email` 子类），在 `trigger()` 里设好占位符后调 `notify( $order_or_user )`；收件人与 Bcc 由基类从 `notify_to()` / `notify_bcc()` 填，From 由基类读取 `notify_sender()`，内部路由标记由基类加入，Reply-to 是该订单或用户；在本模块的 `woocommerce_email_classes` 注册，员工在 Woo 邮件列表里可见可关。不是 Woo 邮件的纯 `wp_mail()`（如健康告警）直接用 `notify_to()` 作 To、`notify_sender()` 的名称与地址拼 `From:` 头、`notify_bcc()` 拼 `Bcc:` 头，并必须携带 `Mail\Message::INTERNAL_HEADER`。两种都经 Outbox（限速、重试、日志）。不要自己写地址，也不要读 `team_mailbox()` 发内部信。

验证：`tests/php/Integration/NotificationRoutingTest.php` 以默认及自定义内部发件地址覆盖六类内部通知的 From、相关客户和访客的 Reply-to，并验证客户询盘和联系回执继续使用 Woo 发件人；同一文件以 Outbox 队列数据断言六类内部通知都只到 `notify_to()` + Bcc、不含 `sales@de-linker.com`，并断言上表第一行各处仍是 `sales@de-linker.com`；新加的内部通知照此加一行断言。

## 邮件（票据 73 起四封随审批走，注册确认是第五封）
- ① 注册 → 团队（`NewCustomerEmail`，含审批状态行与后台直达链接）。
- ② 通过 → 客户（`ApprovedEmail`）③ 限制 → 客户（`RestrictedEmail`，原因段）④ 拒绝 → 客户（`RejectedEmail`，原因段）。三封经 `linker_commerce_approval_changed` 动作（Woo `_notification` 事务邮件机制 → Action Scheduler → Outbox 重试队列），客户语言=用户 `locale`。状态和规范化原因都不变时不重发；限制/拒绝的原因实质改变时重新通知，原因必填才可写入。
- ⑤ 注册确认 → 客户（`RegistrationReceivedEmail`，发到注册时留下的地址）。Woo 原生欢迎信（`customer_new_account`）已关：那封信说账号已可用，pending 账号不是。文案定稿：`docs/acceptance/2026-10-13/138/copy-review.md`。

## 变更台账条目（2026-10-18，#242）

| 项 | 内容 |
|---|---|
| 变更 | ① 已批准账号在按项目报价的商品（1957）产品页："Not available for your account" → "Quoted per project"；② 1957 的德语孪生（6800）产品页向已批准账号显示 33.250,00 € → "Angebot pro Projekt"（`is_rfq_only` 读英文商品的标记）；③ 对比页 `/compare-products/` 的 "Net price" 行：已批准账号在 1957 上 "Net price after partner sign-in" → "Quoted per project"，待审账号 "Net price after partner sign-in" → "Prices after approval"（与产品页共用 `ProductView::price_html`） |
| 裁定 | 业主 2026-10-17：价格跟账号走，账号通过了哪里都显示价格（#242）；按项目报价的商品对谁都不显示价格（`rfq_only`，线上目录数据）；产品页与 Genie 卡"与产品页一致"。PR #301 评审第 1 轮要求入台账 |
| 允许差异 | 只在已登录的已批准、待审、限制账号的视图里（上表三处）；访客看到的产品页、对比页与 Store API 不变（像素门不受影响）；待审账号的 1957 产品页不变（截图对照） |
| 证据 | g242（2026-10-17 20:44 UTC 线上快照），1440：`docs/acceptance/2026-10-18/242/ledger/before-*.png`（main 的代码）与 `after-*.png`（本分支），1957 英 / 德产品页与对比页 × 已批准 / 待审 |
| 台账呈现 | 本规格 + PR #301 描述呈业主过目 |

## 审批状态契约（meta 键与取值，#74 每日摘要照此读）
| 项 | 值 |
|---|---|
| 状态 | `linker_approval_status` ∈ `pending` \| `approved` \| `restricted` \| `rejected`（全部 `string`） |
| 原因 | `linker_approval_reason`，自由文本；approve 时写空串 |
| 审计 | `linker_approval_changed_at`（Unix 秒，`int`）、`linker_approval_changed_by`（WP 用户 id，注册写入时为 0=系统） |
| 缺省 | meta 不存在且角色恰为 `customer` ⇒ `pending`；其他角色 ⇒ `approved`（职员不受审批门约束） |
| 待审批口径（#74） | 纯 `customer` 且状态为 `pending`（含缺省）的账号数；限制数量另列，不并入待审 |
| 语言 | WP 用户 `locale`（注册时写入请求语言；迁移回填最近一次询盘的 `_linker_locale`） |
| 权威 | 只经 `Approval::status()/sees_prices()` 读；三重 Gating（PriceDisplay / CommerceState / StoreApiPrices）读同一权威，无第二实现；请求页与询盘网关对所有人开放 |

## 迁移（切换时执行，载体=#80 ④ 的 `tools/migrate/80-customers.py`）
审批与语言回填合为一个迁移（#73/#80 契约裁定③：一条载体，两条并行脚本作废；#73 的 `73-approval.py` 删除）：
`python3 tools/migrate/80-customers.py --wp <wp-cli> apply --write` 把存量客户全部置 `approved`（幂等），并把最近一次询盘的 `_linker_locale` 回填进空的用户 `locale`（已有 locale 不动，无询盘者留站点默认语言）；`plan` 干跑并打出台账（状态 + 将回填的 locale）、`verify` 校验全量 approved、`rollback --write` 只撤审批状态（locale 是注册本该写下的值，不回撤）。WordPress 侧 `80-customers.php`（`wp eval-file -`）读最近询盘走 Woo 的 `wc_get_orders`，HPOS 与 posts 存储同一路径。

## 原生优先的穷尽证明（AGENTS §5，逐项）
- **审批状态机**：Woo 无账号审批概念（角色只有 customer，无 pending 账号、无审批 UI）；WP 原生存储（user meta）+ 原生登录拦截点（`wp_authenticate_user`）+ 原生会话终结（`WP_Session_Tokens`）即全部所需，自定义 `Approval` 只做规则与数据装配，零设计决策。
- **后台入口**：仪表盘用 `wp_add_dashboard_widget`，顶栏用 `WP_Admin_Bar`，Accounts 菜单用 `add_menu_page` 与 `WP_List_Table`；同一卡片经受 nonce 和用户权限保护的 REST POST 保存。用户列表、档案页用核心扩展点显示状态和深链。旧 GET/admin-post 审批入口已在对等验证后移除（见 `accounts-admin.md`）。
- **客户可见面**：价格位/目录/Store API 已有 B2B 价格门（`Gating\PriceDisplay` 在源头隐藏价格：不可见的价在请求里根本不存在，模板/挂件/feed/API 都取不到；Woo 原生不做门——合格先例），审批只是给这一门加输入；未审批 gate 文案沿用既有 LoginGate 的类名与结构，零新站点 CSS、零新页面模板。

## 联系表单（票 #68，GAP-8）

`/contact/` 与 `/de/kontakt/` 的最小表单，接同一条 Mail 管线：

- 组件：短代码 `[linker_contact_form]`（`Linker\Commerce\Contact\Form`），服务器端渲染
  （无 JS 也能看与提交），语义 markup + Tailwind 类，样式经 WindPress 扫描（页面内容里
  do_shortcode 的 LC provider 已覆盖）；挂载点=页面的 `[data-linker-contact-mount]`。
  `tools/migrate/68-contact-form.py`（plan/apply --write/verify，幂等）把旧的
  `cp-contact-fallback` 换成短代码并移除 `noscript` 行，但它不在切换清单里，
  部署实例的页面内容仍是旧挂载。`Contact\Module::mount_form` 在 `the_content`
  优先级 9（`do_shortcode` 为 11）对 `/contact/` 与其德语孪生做同一次替换：
  短代码已注册才替换，未注册则原样留下兜底行——正文里已经写着短代码也一样，
  未注册的标签展开后什么都不剩，兜底行不能先去掉。已注册且已挂短代码的页面只去掉残留兜底。

### 原生优先的穷尽证明（联系表单挂载，AGENTS §5）

要补的不是一块新设计，是部署页正文里缺的那一次挂载。逐项：

1. **LC 原生 tag**：表单不是商品循环、不是字段、不是相关产品。LC 词汇表（`lc_loop` / `lc_get_cf` / `lc_wc_*`）没有「把一段页面正文里的兜底 div 换成短代码」的 tag。
2. **线上渲染路径（LC 页；2026-10-14 只读实测，2026-10-15 复核）**：线上两个 contact 页都是 LC 页——page 28（`/contact/`）与 page 6907（`/de/kontakt/`）的 `_lc_livecanvas_enabled=1`、模板 meta `page-templates/empty.php`、livecanvas 4.9.3 活动、主题 `picostrap5-child-base`（ssh 只读 `wp post meta get` / `wp plugin get livecanvas` / `wp plugin list` / `wp option get stylesheet`）。非编辑态下 LiveCanvas 从 `the_content` 上摘掉的是**核心回调**（`livecanvas/modules/content-filtering.php:33-45`：do_blocks(9)/wptexturize/convert_smilies(20)/wpautop/shortcode_unautop/prepend_attachment/wp_filter_content_tags/wp_replace_insecure_home_url/capital_P_dangit(11)/embed(8,8)/wp_filter_content_tags(12)）；`remove_all_filters('the_content')` 只在编辑态（同文件 `:22-25`，需 `?lc_page_editing_mode` + `edit_pages`）。本插件的挂载过滤器（优先级 9）与 `do_shortcode`（11）都不在摘除名单里，照常运行。LC 动态模板对 LC 页也不接管：`livecanvas/modules/templating.php:19` 要求 `!lc_post_is_using_livecanvas($post->ID)` 才接管 singular。两处行号取自 t110 实例的插件拷贝（`…/plugins/livecanvas/modules/`）逐行比对。所以线上正文经 `the_content` 输出时不被 wpautop 等改写——复核 2026-10-15：live HTML 里 `/contact/` 的挂载区段与 `pages.json` 的存储区段逐字节相同，锚点间干净换行，无 `<br />`、无包出来的 `<p>`。
3. **Woo 原生机制**：Woo 没有联系表单。`[contact-form-7]` 一类短代码属于未购买、也不在本站启用的插件。现成的载体是本插件已注册的 `[linker_contact_form]`（#68）。
4. **WindPress**：样式已在 `content/windpress/auth.css` 的 `#contact-form .linker-contact-form` 规则里，经 `WindPressVolume::files()` 进卷。本步不新增样式。
5. **为何不跑 `tools/migrate/68-contact-form.py`，也不把它塞进切换清单**：那条脚本是同一次替换的内容写入版（`MOUNT` / `NOSCRIPT` 与这里的正则同一变换），另外还删页面脚本注释里的旧运行时署名，并在正文别处仍带该署名时拒绝写入。切换清单 `tools/cutover/src/linker_cutover/plan.py` 的 `MIGRATIONS` 由规格 17 §4 点名并被 `tools/cutover/tests/test_plan.py` 全等锁死，本泳道不改那份清单。内容迁移要在每个已部署实例上跑一次写操作；渲染时替换随插件部署生效，不改页面正文，已跑过迁移的实例（正文里已有短代码）走「只清残留兜底」分支，不双挂。两处实现是同一变换：脚本负责还没部署、可以写内容的实例；过滤器负责已经部署、正文不会再被迁移碰的实例。
6. **迁移脚本的其余步骤为何不在这条过滤器里发生**：删注释、拒收残留署名是内容卫生，不是表单能不能渲染。过滤器不改存储的正文，所以也不改那条注释。页面脚本本身仍在（它排英雄区与故事面板），注释不进客户可见面。把署名从已部署正文里抹掉仍是那条迁移脚本的事，本步不冒充它已经跑过。
- 字段：message（问题，≤5000）、name、company（选填）、email、consent 勾选、蜜罐
  `website`（`hidden` + `aria-hidden`，人不可见）、nonce、隐藏 `lang`（页面语言）与
  回跳地址。校验在 `Contact\Submission`（服务端，与浏览器约束并行）。
- 提交：`admin_post[_nopriv]_linker_contact`（`Contact\Handler`）：nonce 校验 → 蜜罐
  （填了=当成功回应、不发送）→ 每连接限流（transient，3 次/小时；地址取 `REMOTE_ADDR`，
  不信任转发头）→ 校验 → 发送 → 302 回页面带状态 `?contact=sent|invalid|throttled#contact-form`。
- 邮件：客户回执（`Contact\Emails\ReceiptEmail`，收件人=访客，语言=提交语言）与团队信
  （`Contact\Emails\TeamMessageEmail`，收件人=内部通知收件人（`Options::notify_to()`），Bcc=SettingsTab 的
  盲抄列表，Reply-to=访客，语言=站点默认）——两封都是 `wp_mail()`，因此走既有 Outbox 队列/
  重试/限速/日志。两封都注册进 `woocommerce_email_classes`，员工可在 WooCommerce →
  Settings → Emails 看到并改主题。文案评审：docs/acceptance/2026-10-11/68/copy-review.md
  （未把 Proforma 链的"一个工作日"承诺搬进本表单）。
- 不做：旧表单的 workspace/项目绑定/回执查询会话（无对应物；回执不承诺"回来查进度"）。


## 删除/不存在
运费与发货（Woo 运费区域清空、所有 "shipping" 文案隐藏）、报价、锁价、阈值、分组、发票、Stripe、下载产品、订单跟踪。审批**存在**（票据 73），旧系统的运营台不复活。

## 银行账户（签发 Proforma 的配置，业主数据）

Proforma 上的收款账户只来自 WooCommerce → Settings → Inquiries（`?page=wc-settings&tab=linker_inquiries`）。四项都是选项，没有默认账户，代码不发明、不回落测试值：

| 设置页字段 | 选项键 | 写入 PDF | 签发门槛 |
|---|---|---|---|
| Account holder | `linker_commerce_bank_holder` | 有则印账户持有人，空则印卖方名 | 否 |
| Bank | `linker_commerce_bank_name` | 非空才印银行名 | 否 |
| IBAN | `linker_commerce_bank_iban` | 必印，四位一组分隔 | **是：空则不能签发** |
| BIC | `linker_commerce_bank_bic` | 非空才印 | 否 |

IBAN 按 ISO 13616 校验位保存（`SettingsTab::sanitize_iban`）；校验失败保留原值。BIC 只收 ISO 9362 的 8 或 11 位（`SettingsTab::sanitize_bic`）。

IBAN 为空时：订单页不显示 Issue Proforma，框内说明去 Settings → Inquiries 填写（`Issuer::blocker`）。此时把状态改成 `wc-proforma-issued` 也不生成号、不生成 PDF，订单备注记下同一句原因（`Issuer::ensure_issued`）。客户侧询盘详情与 Documents 只在订单 meta `_linker_proforma_number` 非空时给出下载链接和号；没有号就没有入口，不显示一个点下去 404 的链接。

这是配置要求，不是缺陷。生产账户由业主在切换时填写；本地验收用测试账户（示例见 `tests/e2e/specs/commerce.spec.ts` 的 `ensureBccConfigured`），用完删除，不写进仓库当生产值。

## 验收
- [ ] 本地：注册 → pending → 团队邮件 → 行内一键通过 → 看价 → 加入 Lösungsentwurf → 提交询盘 → 后台出 PI → 客户账户下载 PI，EN 与 DE 各一次；本地邮件捕获里每封信只有 tester 单地址（测试邮件开关开着），注册确认、公司提醒、审批邮件、询盘确认、PI 邮件的路由（收件人/Bcc）以 Outbox 队列数据断言（AGENTS.md 测试邮件纪律，2026-10-11）。
- [ ] 全站可见文案无 order/checkout/payment/shipping/Versand/Kasse/Bezahlen/Warenkorb（引语除外）。
- [ ] PI 编号连续、PDF 含银行条款与 30 天有效期；未登录访问 PI 链接 403。
- [ ] 重试队列测试：模拟 `wp_mail` 失败 3 次后成功，仅一封送达。
- [ ] 审批（票据 73）：四状态 × Gating 行为矩阵、三动作 × 邮件断言、原因注入、存量迁移=全部 approved、可逆转换；EN/DE 渲染邮件截图归档。
- [ ] 视觉验收：注册、产品页、Lösungsentwurf、提交页、账户 × EN/DE × 1440/390；以及访客提交后邮件确认链接（带 key）**未登录**打开的状态（评审 2026-10-10：此前重放全程登录态，该页漏扫）× EN/DE。

## 变更记录
- 2026-10-18（#288）：生产改前/改后证明 Hostinger `hsendmail` 强制信封，SPF 已通过，de-linker.com 无 DMARC，客户邮件在 QQ 收件箱；取消无效的信封设置。保留并入修正：内部发件身份集中为唯一公开的 `Options::notify_sender()` / readonly `Mail\Identity`，Proforma 前缀去首尾连字符，Reply-To 按邮件 ID 独立断言，通知路由拆分测试；WP-CLI 从源码与 build 直接重建 POT，既有译文不变。证据见上文 Mail 一节与 `docs/acceptance/2026-10-18/288/`。
- 2026-10-18（#286）：内部通知使用独立发件地址，默认 `Linker <sales@sunriverinverter.com>`；客户邮件仍用 WooCommerce 的 From，Reply-to 不变。后台 Sender email / Absenderadresse 字段与 Recipient 同节；同一设置保存保留既有 Proforma 前缀中的连字符（`DLK-PF` 不变），继续清除其余非字母数字符号；文案评审与本地验收见 `docs/acceptance/2026-10-18/286/`。线上单封内部通知的收件箱验证由 Claude 在 #285 留证。
- 2026-10-17（#221）：内部通知改投 `sales@sunriverinverter.com`（业主裁定），与客户可见的团队邮箱拆成两个设置（见“内部通知收件人”）；`Options::team_to()`/`team_bcc()` 改名为 `team_mailbox()` 与 `notify_to()`/`notify_bcc()`，不改任何选项值。健康告警由“To 对接人”改为内部通知收件人，发件人由 WordPress 缺省（`wordpress@…`）改为 WooCommerce 的发件人（评审第 1 轮）。集成测试的邮件隔离统一为 `IntegrationTestCase::isolate_mail()`（保存并还原限速记录、删掉本测试写的队列行），整套可连跑。Outbox 每次投递写一行 `linker-mail` info 日志：线上 cron 由 CLI PHP 跑，主机的 `~/.logs/mail.log` 只记 Web PHP 的 `mail()`，此前摘要、健康告警与队列重试在主机上不留任何痕迹。
- 2026-10-16：登录与注册拆成两个页面（业主裁定）。`/my-account/` 只出登录卡；注册卡移到账号页的 `register` 端点（EN `/my-account/register/`，DE `/de/mein-konto/register/`，slug 跨语言共享），两页互跳。注册的处理链（Woo 的 nonce、字段、校验、建号、自动登录、pending 门禁）逐字不动，只有呈现分置两个请求。规格：`docs/specs/split-login-register.md`。
- 2026-10-13：Proforma 号与 PDF 不再只挂在 Issue 按钮上。状态进入 `wc-proforma-issued` 时 `Issuer::ensure_issued` 补签发（已有号或 PDF 的不动，避免按钮路径签两次）。客户侧询盘详情（摘要卡号 + 下载链接）与 Documents 只读 `_linker_proforma_number`；Completed 后号还在，下载仍在。银行账户缺失时按钮隐藏、状态路径不签发，配置键见上节，不补造账户。默认号前缀由 `PI` 改为 `DLK-PF`，与线上 `DLK-PF-年份-…` 一致；空前缀走默认，已保存的自定义前缀不动。
- 2026-10-13（#138）：注册邮件改为注册确认（`RegistrationReceivedEmail`；Woo 原生欢迎信仍关）。邮件清单补第 5 封。pending 停在审核页；restricted 保留工作台，Proforma request 显示限制原因。文案定稿 `docs/acceptance/2026-10-13/138/copy-review.md`。
- 2026-10-11（#67，GAP-16）：新增 `Health` 模块（服务健康告警最小件）。WordPress/Woo 没有外部服务健康监视的原生能力，检查本身是本插件的；机制全部原生：调度 WP cron daily（`init` 懒登记 + 停用 `wp_clear_scheduled_hook`），HTTP 走 WP HTTP API，邮件走 `wp_mail` 即 #11 的 Outbox 队列（复用限流与重试）。验收：单元 `MonitorTest`（7 项）+ 实例集成 `HealthMonitorTest`（cron 钩子触发路径、失败一封 To 对接人+Bcc、健康零邮件、每日事件在排期），实例级 `wp cron event run linker_commerce_health_check` 健康/失败两跑实证。
- 2026-10-14：线上 `/contact/` 与 `/de/kontakt/` 仍渲染旧兜底（form=0）。根因是挂载替换只在迁移脚本里，而该脚本不在切换清单，部署后的页面内容没有短代码。渲染时替换补上这一步。兜底行在短代码未注册时留下，正文里已经写着短代码也一样。本页渲染的是 #68 重建的最小表单（`docs/acceptance/2026-10-11/68/README.md` §4 原文：线上像素级比对不适用本票两块新面——搜索框芯片与联系表单是新建/重建面，非复刻面）；该记录与业主 2026-10-10 像素门裁定（所有客户可见页遵循线上现有设计，营销页按页型对拍）对 `/contact/` 的适用关系曾随本票报业主（PR #159 openQuestions），**已收口**（清账决策 2，2026-10-15，`.scratch/closure-decisions-2026-10-15.md` 第 2 条）：**移植旧线上整卡设计**——`/contact/` 是客户可见页，#68 的「重建面」记录说的是实现管线，不豁免设计层；**PR #165 已执行**（旧线上 What can we help with? 整卡 + 副卡移植进 LC/WindPress 层，表单仍走 #68 管线，文案三轮对抗评审后保持 #68 定稿）。
- 2026-10-11（#68）：联系表单（最小）落地并接 Mail 管线：短代码 `[linker_contact_form]`、admin-post 处理（nonce/蜜罐/限流/校验）、客户回执 + 团队信（Bcc 走 SettingsTab）；`tools/migrate/68-contact-form.py` 换挂载点；同轮修 Figures/FAQ meta box 的保存形态（浏览器实际提交的是嵌套数组，两个箱子此前对真实 POST 从不写入，证据与复现见 docs/acceptance/2026-10-11/68/README.md §3）。
