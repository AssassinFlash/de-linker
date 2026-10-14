# #11 商务链 `linker-commerce`

依据：`docs/research/2026-10-09/account-workspace.md`、`mail-root-cause.md`、AGENTS.md §1–§3，账号审批=票据 73（业主 2026-10-11 裁定）。原则：Woo 原生能力优先，自定义只在 Woo 没有答案处。

## 用户旅程（EN / DE 文案按 AGENTS.md 规则逐处写，此处只给语义）
1. **访客**：看产品分类与产品，看不到价格（价格位显示 "Log in for prices" / "Preise nach Anmeldung"）；可用 Genie 与配置器；可把产品加入 Lösungsentwurf（按会话保存）。
2. **注册**（Woo 原生 My Account 注册表单 + 字段）：公司名、增值税号（VIES 实时校验，失败可提交但标记）、地址、角色（安装商 / EPC / 经销商）、姓名、邮箱、密码。**注册即 pending（票据 73）**：账号在团队批准前读站如访客；客户语言随注册写入 WP 用户 `locale`（询盘同源的取语规则）。邮件：注册确认（RegistrationReceivedEmail，Woo 原生欢迎信已关）+ 公司"新客户"提醒（含审批状态行与后台直达链接）。
3. **审批（票据 73）**：团队在 WP 后台两处操作——用户列表行内「Approve」一键（最高频）+ 用户资料页 Linker 区块（Approve / Restrict / Reject 三动作 + 原因 + 当前状态与最近一次变更的审计行）。全部可逆；Restrict / Reject 必须带原因，原因经邮件正式告知客户。权限=WP 自己的 `edit_users`（与资料页同一守门；shop_manager 默认无此权限，只见状态列）。
4. **四态 × 界面**：
   - **approved**：看价；Lösungsentwurf 合并会话内容；产品页按钮 "Add to solution draft / Zum Lösungsentwurf hinzufügen"；可提交询盘。
   - **pending**：与访客同视图——浏览无价产品、Genie 咨询（无价）、开放式询价走 /contact/ 通道；不可看价（价格位 "Prices after approval / Preise nach Freigabe"）、不可进账户工作台（`PendingGate` 把账户端点送回审核页）、不可提交询盘（请求页显示审核 gate，网关对未批准账号一律不开放——视图与服务端同一权威）。
   - **restricted**：保留工作台（询盘、资料、文件仍可读）；不可看价（价格位 "Not available for your account / Für Ihr Konto nicht verfügbar"）、不可提交询盘。Proforma request 显示 restricted gate，并写出限制原因（`LoginGate`，与工作台同一权威）。
   - **rejected**：登录被挡（`wp_authenticate_user`，登录表单显示状态与原因去向；拒绝同时终结该账号的全部登录会话）。
5. **询盘提交**（原 checkout 页，地址 `/proforma-request/`、`/de/proforma-anfrage/` 不变）：显示 Lösungsentwurf 行、数量、价格（未知价显示 "Price on request / Preis auf Anfrage"）、公司资料、备注；唯一"支付方式"是自建的 `ProformaGateway extends WC_Payment_Gateway`（`has_fields=false`、不显示银行账户、`process_payment` 直接落 `inquiry-received`）；提交按钮 "Request Proforma / Proforma anfordern"；页面写明 "We reply within one business day / Wir antworten innerhalb eines Arbeitstags"（德语成品用 Arbeitstag，与本插件 `.po` 一致）。提交后订单状态 `wc-inquiry-received`，减库存关闭。
6. **公司侧**（Woo 后台订单页，角色 shop_manager）：订单标题 "Inquiry #"；按钮 "Issue Proforma / Proforma ausstellen"：生成 PDF、状态改 `wc-proforma-issued`、给客户发邮件（附 PDF 链接，不附件）；之后手动 `completed` 或 `cancelled`。无其他动作。后台把状态直接改成 `wc-proforma-issued` 走同一条签发（`Issuer::ensure_issued`，钩在 `woocommerce_order_status_proforma-issued`）：号与 PDF 写上之后，客户侧才有下载入口。没有银行账户时按钮不出现，状态改过去也不签发——见下节，不补造账户。
7. **客户账户**（Woo My Account，端点改名）：Inquiries / Anfragen（列表：编号、日期、状态、金额、PI 下载）、Saved solutions / Gespeicherte Lösungen（定名，账户页与 `POST linker/v1/solutions` 的保存结果；保存的方案与设计报告 PDF，来自 #14）、Company / Unternehmen（资料与地址）、Documents / Unterlagen（本账户所有 PI 与设计报告）、页面顶部 "Your contact person / Ihre Ansprechperson"（姓名、邮箱、电话，来自设置）、每条询盘上 "Request again / Erneut anfragen"（复制为新的 Lösungsentwurf）。移除：订单、付款方式、下载（Woo 原生端点中不需要的隐藏）。

## 模块（PSR-4 `Linker\Commerce\`，一类一文件，各有测试）
- `Registration`（字段、VIES 客户端、角色元数据、提醒邮件）。
- `Registration\Approval`（**审批权威，票据 73**：状态机、读写与审计、登录拦截；唯一的 meta 读写方）。
- `Registration\ApprovalAdmin`（用户列表列与行内一键、资料页区块；admin-post + 每用户 nonce）。
- `Gating`（价格隐藏：模板过滤 + `wc/store/v1` 价格置空；可购买性 = 已登录且已批准；`rfq_only` 产品标记显示 "Quoted per project / Angebot pro Projekt"）。
- `Inquiry`（状态注册与颜色、网关类 `ProformaGateway extends WC_Payment_Gateway`、减库存关闭、订单标题与列表列；`Checkout::gateways` 对未批准账号返回空=服务端拦截点）。
- `Proforma`（PDF：dompdf 或 mpdf（MIT/LGPL），模板 EN/DE，编号 `DLK-PF-YYYY-NNNN`（按年计数，选项 `linker_commerce_proforma_prefix`，空则 `DLK-PF`），银行条款（设置页填写），有效期 30 天，税额行按 Woo 税设置显示；生成后存 `wp-content/uploads/proforma/<order>/` 私有目录，账户内经鉴权下载）。线上 `de-linker.com` 的号是 `DLK-PF-年份-订单ID`（下单即写入账本，不是后台按钮才编）；本站保留同一前缀，序号按年递增，不沿用订单 ID。
- `Mail`（`wp_mail` 统一：一封主信 To sales@ + Bcc 三个邮箱（设置页）；队列 Action Scheduler；失败重试：1、5、30 分钟、2、6、12、24 小时；Woo 事务邮件也经队列；VAT 审核提醒只在结论变化时发；本地隔离下写文件）。**测试邮件开关**（AGENTS.md 测试邮件纪律，2026-10-11；`Mail\TestMode`，与 #73/#94 同一实现）：选项 `linker_commerce_test_mail_to` 设了地址时，Outbox 的发送路径把每封信的全部 To/Cc/Bcc 重写成该单地址（每封信只发一份），队列里的消息保留原路由——多收件路由的正确性以队列数据（`_linker_mail_message`）断言，不做多封实发。默认未设=生产路由；`wp linker-commerce test-mail on|off|status` 设与撤（默认收件人 chester@de-linker.com，`--to=` 可换），不是设置页字段（#17 切换冒烟时开，验证后撤）。
- `Account`（端点注册、模板、对接人设置、再次询盘）。
- `Vocabulary`（gettext 覆盖 Woo 自带字符串：Cart → Solution draft / Lösungsentwurf 等；全部通过 `.po`）。
- `Settings`（后台一页：对接人、Bcc 列表、银行条款、PI 前缀）。
- `Health`（`Monitor`：WP cron daily 依次 GET `linker_genie_url`/`linker_engine_url` 的 `/health`（实例配置，本地 `just serve` 写、切换 #17 写），非 200 或不可达或地址为空 → 经 `wp_mail`（即 Outbox 队列）发团队邮件，To 对接人（`Settings::contact()`，缺省回落团队邮箱）+ Bcc；两服务都健康不发。主题与正文 EN 先行、DE 独立撰写，对抗评审记录 `docs/acceptance/2026-10-11/67/copy-review.md`）。

## 邮件（票据 73 起四封随审批走，注册确认是第五封）
- ① 注册 → 团队（`NewCustomerEmail`，含审批状态行与后台直达链接）。
- ② 通过 → 客户（`ApprovedEmail`）③ 限制 → 客户（`RestrictedEmail`，原因段）④ 拒绝 → 客户（`RejectedEmail`，原因段）。三封经 `linker_commerce_approval_changed` 动作（Woo `_notification` 事务邮件机制 → Action Scheduler → Outbox 重试队列），客户语言=用户 `locale`。状态不变更不重发；限制/拒绝必须带原因才可写入。
- ⑤ 注册确认 → 客户（`RegistrationReceivedEmail`，发到注册时留下的地址）。Woo 原生欢迎信（`customer_new_account`）已关：那封信说账号已可用，pending 账号不是。文案定稿：`docs/acceptance/2026-10-13/138/copy-review.md`。

## 审批状态契约（meta 键与取值，#74 每日摘要照此读）
| 项 | 值 |
|---|---|
| 状态 | `linker_approval_status` ∈ `pending` \| `approved` \| `restricted` \| `rejected`（全部 `string`） |
| 原因 | `linker_approval_reason`，自由文本；approve 时写空串 |
| 审计 | `linker_approval_changed_at`（Unix 秒，`int`）、`linker_approval_changed_by`（WP 用户 id，注册写入时为 0=系统） |
| 缺省 | meta 不存在且角色恰为 `customer` ⇒ `pending`；其他角色 ⇒ `approved`（职员不受审批门约束） |
| 待审批口径（#74） | `role=customer` 且状态 ≠ `approved` 的账号数 |
| 语言 | WP 用户 `locale`（注册时写入请求语言；迁移回填最近一次询盘的 `_linker_locale`） |
| 权威 | 只经 `Approval::status()/sees_prices()` 读；三重 Gating（PriceDisplay / CommerceState / StoreApiPrices）与请求页 gate、网关过滤读同一权威，无第二实现 |

## 迁移（切换时执行，载体=#80 ④ 的 `tools/migrate/80-customers.py`）
审批与语言回填合为一个迁移（#73/#80 契约裁定③：一条载体，两条并行脚本作废；#73 的 `73-approval.py` 删除）：
`python3 tools/migrate/80-customers.py --wp <wp-cli> apply --write` 把存量客户全部置 `approved`（幂等），并把最近一次询盘的 `_linker_locale` 回填进空的用户 `locale`（已有 locale 不动，无询盘者留站点默认语言）；`plan` 干跑并打出台账（状态 + 将回填的 locale）、`verify` 校验全量 approved、`rollback --write` 只撤审批状态（locale 是注册本该写下的值，不回撤）。WordPress 侧 `80-customers.php`（`wp eval-file -`）读最近询盘走 Woo 的 `wc_get_orders`，HPOS 与 posts 存储同一路径。

## 原生优先的穷尽证明（AGENTS §5，逐项）
- **审批状态机**：Woo 无账号审批概念（角色只有 customer，无 pending 账号、无审批 UI）；WP 原生存储（user meta）+ 原生登录拦截点（`wp_authenticate_user`）+ 原生会话终结（`WP_Session_Tokens`）即全部所需，自定义 `Approval` 只做规则与数据装配，零设计决策。
- **后台入口**：用户列表与资料页是 WP 核心屏幕；扩展点全用核心的 `manage_users_columns` / `manage_users_custom_column` / `user_row_actions` / `edit_user_profile`；表单走核心 `admin-post.php` + `wp_nonce_field`；**零** `add_menu_page`、**零** `wp_ajax_*`。资料页 Woo 区块（`woocommerce_customer_meta_fields`）只能出输入框，三动作按钮用 `formaction` 指向 admin-post（WP 资料页自带 form，不可嵌套 form）。
- **客户可见面**：价格位/目录/Store API 已有 `linker_price` 门（Woo 原生不做门——既有合格先例），审批只是给这一门加输入；未审批 gate 文案沿用既有 LoginGate 的类名与结构，零新站点 CSS、零新页面模板。

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

1. **LC 原生 tag**：表单不是商品循环、不是字段、不是相关产品。LC 词汇表（`lc_loop` / `lc_get_cf` / `lc_wc_*`）没有「把一段页面正文里的兜底 div 换成短代码」的 tag。contact 页也不是 LC 动态模板：线上模板 meta 是 `page-templates/empty.php`，主题模板调用 `the_content()`，正文就是页面自己的 HTML。
2. **Woo 原生机制**：Woo 没有联系表单。`[contact-form-7]` 一类短代码属于未购买、也不在本站启用的插件。现成的载体是本插件已注册的 `[linker_contact_form]`（#68）。
3. **WindPress**：样式已在 `content/windpress/auth.css` 的 `#contact-form .linker-contact-form` 规则里，经 `WindPressVolume::files()` 进卷。本步不新增样式。
4. **为何不跑 `tools/migrate/68-contact-form.py`，也不把它塞进切换清单**：那条脚本是同一次替换的内容写入版（`MOUNT` / `NOSCRIPT` 与这里的正则同一变换），另外还删页面脚本注释里的旧运行时署名，并在正文别处仍带该署名时拒绝写入。切换清单 `tools/cutover/src/linker_cutover/plan.py` 的 `MIGRATIONS` 由规格 17 §4 点名并被 `tools/cutover/tests/test_plan.py` 全等锁死，本泳道不改那份清单。内容迁移要在每个已部署实例上跑一次写操作；渲染时替换随插件部署生效，不改页面正文，已跑过迁移的实例（正文里已有短代码）走「只清残留兜底」分支，不双挂。两处实现是同一变换：脚本负责还没部署、可以写内容的实例；过滤器负责已经部署、正文不会再被迁移碰的实例。
5. **迁移脚本的其余步骤为何不在这条过滤器里发生**：删注释、拒收残留署名是内容卫生，不是表单能不能渲染。过滤器不改存储的正文，所以也不改那条注释。页面脚本本身仍在（它排英雄区与故事面板），注释不进客户可见面。把署名从已部署正文里抹掉仍是那条迁移脚本的事，本步不冒充它已经跑过。
- 字段：message（问题，≤5000）、name、company（选填）、email、consent 勾选、蜜罐
  `website`（`hidden` + `aria-hidden`，人不可见）、nonce、隐藏 `lang`（页面语言）与
  回跳地址。校验在 `Contact\Submission`（服务端，与浏览器约束并行）。
- 提交：`admin_post[_nopriv]_linker_contact`（`Contact\Handler`）：nonce 校验 → 蜜罐
  （填了=当成功回应、不发送）→ 每连接限流（transient，3 次/小时；地址取 `REMOTE_ADDR`，
  不信任转发头）→ 校验 → 发送 → 302 回页面带状态 `?contact=sent|invalid|throttled#contact-form`。
- 邮件：客户回执（`Contact\Emails\ReceiptEmail`，收件人=访客，语言=提交语言）与团队信
  （`Contact\Emails\TeamMessageEmail`，收件人=SettingsTab 的团队邮箱，Bcc=SettingsTab 的
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
- 2026-10-13：Proforma 号与 PDF 不再只挂在 Issue 按钮上。状态进入 `wc-proforma-issued` 时 `Issuer::ensure_issued` 补签发（已有号或 PDF 的不动，避免按钮路径签两次）。客户侧询盘详情（摘要卡号 + 下载链接）与 Documents 只读 `_linker_proforma_number`；Completed 后号还在，下载仍在。银行账户缺失时按钮隐藏、状态路径不签发，配置键见上节，不补造账户。默认号前缀由 `PI` 改为 `DLK-PF`，与线上 `DLK-PF-年份-…` 一致；空前缀走默认，已保存的自定义前缀不动。
- 2026-10-13（#138）：注册邮件改为注册确认（`RegistrationReceivedEmail`；Woo 原生欢迎信仍关）。邮件清单补第 5 封。pending 停在审核页；restricted 保留工作台，Proforma request 显示限制原因。文案定稿 `docs/acceptance/2026-10-13/138/copy-review.md`。
- 2026-10-11（#67，GAP-16）：新增 `Health` 模块（服务健康告警最小件）。WordPress/Woo 没有外部服务健康监视的原生能力，检查本身是本插件的；机制全部原生：调度 WP cron daily（`init` 懒登记 + 停用 `wp_clear_scheduled_hook`），HTTP 走 WP HTTP API，邮件走 `wp_mail` 即 #11 的 Outbox 队列（复用限流与重试）。验收：单元 `MonitorTest`（7 项）+ 实例集成 `HealthMonitorTest`（cron 钩子触发路径、失败一封 To 对接人+Bcc、健康零邮件、每日事件在排期），实例级 `wp cron event run linker_commerce_health_check` 健康/失败两跑实证。
- 2026-10-14：线上 `/contact/` 与 `/de/kontakt/` 仍渲染旧兜底（form=0）。根因是挂载替换只在迁移脚本里，而该脚本不在切换清单，部署后的页面内容没有短代码。渲染时替换补上这一步。兜底行在短代码未注册时留下，正文里已经写着短代码也一样。设计口径沿 #68 验收记录：联系表单是重建面，不是旧线上整卡的复刻面（`docs/acceptance/2026-10-11/68/README.md` §4）。
- 2026-10-11（#68）：联系表单（最小）落地并接 Mail 管线：短代码 `[linker_contact_form]`、admin-post 处理（nonce/蜜罐/限流/校验）、客户回执 + 团队信（Bcc 走 SettingsTab）；`tools/migrate/68-contact-form.py` 换挂载点；同轮修 Figures/FAQ meta box 的保存形态（浏览器实际提交的是嵌套数组，两个箱子此前对真实 POST 从不写入，证据与复现见 docs/acceptance/2026-10-11/68/README.md §3）。
