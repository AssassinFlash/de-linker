# #11 商务链 `linker-commerce`

依据：`docs/research/2026-10-09/account-workspace.md`、`mail-root-cause.md`、AGENTS.md §1–§3。原则：Woo 原生能力优先，自定义只在 Woo 没有答案处。

## 用户旅程（EN / DE 文案按 AGENTS.md 规则逐处写，此处只给语义）
1. **访客**：看产品分类与产品，看不到价格（价格位显示 "Log in for prices" / "Preise nach Anmeldung"）；可用 Genie 与配置器；可把产品加入 Lösungsentwurf（按会话保存）。
2. **注册**（Woo 原生 My Account 注册表单 + 字段）：公司名、增值税号（VIES 实时校验，失败可提交但标记）、地址、角色（安装商 / EPC / 经销商）、姓名、邮箱、密码。注册即可用（无审批）。邮件：客户欢迎信（Woo 原生）+ 公司"新客户"提醒。
3. **登录后**：看价；Lösungsentwurf 合并会话内容；产品页按钮 "Add to solution draft / Zum Lösungsentwurf hinzufügen"。
4. **询盘提交**（原 checkout 页，地址 `/proforma-request/`、`/de/proforma-anfrage/` 不变）：显示 Lösungsentwurf 行、数量、价格（未知价显示 "Price on request / Preis auf Anfrage"）、公司资料、备注；唯一"支付方式"是改名的 BACS（标题 "Proforma invoice / Proformarechnung"，不显示银行账户）；提交按钮 "Request Proforma / Proforma anfordern"；页面写明 "We reply within one business day / Wir antworten innerhalb eines Werktags"。提交后订单状态 `wc-inquiry-received`，减库存关闭。
5. **公司侧**（Woo 后台订单页，角色 shop_manager）：订单标题 "Inquiry #"；按钮 "Issue Proforma / Proforma ausstellen"：生成 PDF（下方）、状态改 `wc-proforma-issued`、给客户发邮件（附 PDF 链接，不附件）；之后手动 `completed` 或 `cancelled`。无其他动作。
6. **客户账户**（Woo My Account，端点改名）：Inquiries / Anfragen（列表：编号、日期、状态、金额、PI 下载）、Solution drafts / Lösungsentwürfe（保存的方案与设计报告 PDF，来自 #14）、Company / Unternehmen（资料与地址）、Documents / Unterlagen（本账户所有 PI 与设计报告）、页面顶部 "Your contact person / Ihre Ansprechperson"（姓名、邮箱、电话，来自设置）、每条询盘上 "Request again / Erneut anfragen"（复制为新的 Lösungsentwurf）。移除：订单、付款方式、下载（Woo 原生端点中不需要的隐藏）。

## 模块（PSR-4 `Linker\Commerce\`，一类一文件，各有测试）
- `Registration`（字段、VIES 客户端、角色元数据、提醒邮件）。
- `Gating`（价格隐藏：模板过滤 + `wc/store/v1` 价格置空；可购买性 = 已登录；`rfq_only` 产品标记显示 "Quoted per project / Angebot pro Projekt"）。
- `Inquiry`（状态注册与颜色、网关类 `ProformaGateway extends WC_Payment_Gateway`（`has_fields=false`，不显示账户，`process_payment` → `inquiry-received`）、减库存关闭、订单标题与列表列）。
- `Proforma`（PDF：dompdf 或 mpdf（MIT/LGPL），模板 EN/DE，编号 `PI-YYYY-NNNN`（按年计数，选项存储），银行条款（设置页填写），有效期 30 天，税额行按 Woo 税设置显示；生成后存 `wp-content/uploads/proforma/<order>/` 私有目录，账户内经鉴权下载）。
- `Mail`（`wp_mail` 统一：一封主信 To sales@ + Bcc 三个邮箱（设置页）；队列 Action Scheduler；失败重试：1、5、30 分钟、2、6、12、24 小时；Woo 事务邮件也经队列；VAT 审核提醒只在结论变化时发；本地隔离下写文件）。
- `Account`（端点注册、模板、对接人设置、再次询盘）。
- `Vocabulary`（gettext 覆盖 Woo 自带字符串：Cart → Solution draft / Lösungsentwurf 等；全部通过 `.po`）。
- `Settings`（后台一页：对接人、Bcc 列表、银行条款、PI 前缀）。

## 删除/不存在
运费与发货（Woo 运费区域清空、所有 "shipping" 文案隐藏）、报价、锁价、阈值、分组、审批、发票、Stripe、下载产品、订单跟踪。

## 验收
- [ ] 本地：注册 → 看价 → 加入 Lösungsentwurf → 提交询盘 → 后台出 PI → 客户账户下载 PI，EN 与 DE 各一次；本地邮件捕获里：欢迎信、公司提醒、询盘确认、PI 邮件各一封，主信含 Bcc。
- [ ] 全站可见文案无 order/checkout/payment/shipping/Versand/Kasse/Bezahlen/Warenkorb（引语除外）。
- [ ] PI 编号连续、PDF 含银行条款与 30 天有效期；未登录访问 PI 链接 403。
- [ ] 重试队列测试：模拟 `wp_mail` 失败 3 次后成功，仅一封送达。
- [ ] 视觉验收：注册、产品页、Lösungsentwurf、提交页、账户 × EN/DE × 1440/390。
