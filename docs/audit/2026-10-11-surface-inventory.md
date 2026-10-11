# 全系统面对照（旧系统 → 新仓库）

审计日期 2026-10-11。枚举方法：旧系统面从代码（旧仓库 `refs/landed/chain-tip` = f007a9dd，经 `git show` 只读）与线上只读 GET（sitemap en+de、/products/、/contact/、/faq-download/、/linker-advisor/、/compare-products/、产品页）穷举；新仓库状态从 main `2eb8da4` 代码与 docs/specs 判定。本清单是 #16/#17 验收与切换清单的骨架，与《2026-10-11 全拆审计》（旧代码存活）互补：那份管"代码是不是抄的"，这份管"面有没有丢"。

**业主指令背景（2026-10-11）**：全面重构不能依赖业主提名；穷举由工程线负责，业主只答业务事实。

## 0. 本轮抽验记录（主会话独立复核）

- GAP-6 证实：旧 `legacy-redirects.php` 872 行 / **305 条映射**；新 `Redirects.php` 仅 **5 条**。
- GAP-7 证实：新树生产代码零 `ld+json` 输出（命中全在 node_modules 三方包）。
- GAP-19 证实：新 mu 仅 3 件本地开发件（isolation/login/rewrites），无错误记录对应物。
- GAP-2 证实：线上德语产品页实测含 scenario/Anwendung 段（grep 命中 3+2 处）；新模板与 ProductView 零场景渲染。
- **纠正审计代理两处无出处结论**：①"bulk-order 随 spec 11 裁定废弃"——spec 11 全文无 bulk 字样，bulk order 属**未裁定**；②vision 同样未裁定（spec 6 只解释了本地按钮缺失的密钥原因，线上按钮真实存在）。两者均按 C 类默认处理（见 GAP 汇总）。

## 1. 客户可见页面（线上 sitemap：EN 152 条 = 26 页 + 11 博文 + 105 产品 + 10 分类；DE 150 条）

| 面 | 旧行为（证据） | 新仓库状态 | 证据 | 处置 |
|---|---|---|---|---|
| 营销页（home、about×2、for-installer、for-epc、solution×4、services-support、refund-returns、terms-of-sale、imprint、privacy-policy） | 快照携带；#12 只改页头页脚与工具文案 | 数据携带 via #6 快照 | specs/12 §1/§4 | — |
| 博客（/blog/ + 11 文 ×2 语） | WP 内容 + LC 动态模板 | 数据携带；#9 翻译队列覆盖德语 | linker-i18n Jobs.php | — |
| 产品分类页 10 个 + /products/ | 筛选 + **搜索框**（`id="search-box" type="search"`，线上实测）+ min/max 数字输入 | archive 模板 + CatalogFilters（GET 链接，无任何 `<input>`）+ Genie 芯片；**无搜索输入** | storefront-archive-product.php:59–77；Entries.php:29/180 | **GAP-1 → 票 A**（spec 13 本就写了搜索框识别问句出芯片，属漏建非新增） |
| 产品页 105 ×2 语 | 图库/正文/参数/FAQ/文档/**场景段**/BOM 抽屉入口 | 图值 #7、参数 linker_specs、FAQ #15、文档、按钮价格 #11、Genie 芯片；**场景段无渲染** | 旧 product-scenarios.php:5–10；本轮线上实测 | **GAP-2 → #16 逐区块对账**（产品页裁定=复刻线上设计） |
| compare 独立页 /compare-products/ | compare-products.php + compare-selection.js（线上 200，含 data-compare） | 页面随快照 200 但交互 JS 属旧插件，切换即死；新有 Genie ability + 产品页 Compare 芯片 | 旧 includes/compare-products.php；新 Abilities/CompareProducts.php | **GAP-3 → 票 B：301 至 /products/**（对比功能由 Genie 代偿；独立选择页留待有客户需求再议） |
| FAQ 页 /faq-download/ | linker-ai 知识/文档工作台（线上实测 linker-ai-workspace）+ refdesk 问答 | 页面随快照 200，工作台 JS 属旧插件；#15 只做产品内 FAQ | 线上 GET；旧 reference-and-display.php:2500 | **GAP-4 → 票 B：改静态 FAQ/文档目录页**（Q&A 由 Genie search-knowledge 代偿，保 URL 与 SEO） |
| /linker-advisor/ | Advisor 聊天整页（线上 linker-ai-assistant ×8） | Genie 为芯片+常驻 dock，无整页挂载，Redirects 无此路径 | Entries.php:29–32 | **GAP-5 → 票 B：301 至 /products/** |
| /design-canvas/、/quote-configurator/ | 旧独立工具页 | 301 → /linker-planner/ 已重建 | Redirects.php:33–39 | — |
| /linker-planner/ 配置器 | 旧 planner 七条 design REST | 重建 #14（三屏+屋顶步+LoD2） | src/configurator/（15 文件） | — |
| /cart/ → Lösungsentwurf | 旧 cart-render/cart-session | 重建：cart_page.html + Vocabulary 改名 | content/livecanvas/ | — |
| /proforma-request/ 询盘提交 | 旧 checkout-online-shop + proforma-workflow | 重建 #11：ProformaGateway、wc-inquiry-received | Inquiry/ProformaGateway.php | — |
| 旧 /checkout/ slug 301（ticket 187） | commerce-pages.php:269–293 | **不在新 Redirects.php** | 旧 commerce-pages.php:269 | **并入 GAP-6 → #17** |
| 账户区 /my-account/ | orders/inquiries、documents、quotes、projects、bulk-order、payment-methods、settings | Inquiries、Saved solutions、Company、Documents + ContactCard + Request again | includes/Account/*（9 文件） | quotes/projects/payment-methods 已裁定废弃（spec 11）；bulk-order 见 GAP-11（C 类默认） |
| legal 4 页 | 快照携带 | 数据携带 | page-sitemap1.xml | — |
| 站内 `?s=` 搜索结果页 | 旧 i18n 把搜索限定为文章 | WP core 行为保留但无限定（结果混入产品/页面） | 旧 class-linker-i18n-search.php:6–10 | **并入 GAP-1 → 票 A**（搜索框重建时一并定结果页范围） |
| Product JSON-LD / CollectionPage / BreadcrumbList | 旧 public-schema.php（源自旧 #26 brand guard） | 新插件零输出；SEOPress Pro 留用但其 schema 输出未核 | 本轮 grep 证实 | **GAP-7 → #17：先核 SEOPress，缺则补输出** |

## 2. REST 路由面

旧全量 43 条（grep `register_rest_route`）→ 新 5 条 + Abilities API 12 个 + Woo Store API 价格门。

| 旧路由 | 新对应 | 状态 |
|---|---|---|
| `tv-b2b/v1/catalog-search` | 无 | GAP-1（随搜索框） |
| `tvb2b/v1/contact-context` / `contact-receipt` / `contact-request` | 无 | GAP-8 → 票 A |
| `tvb2b/v1/stock`（旧系统的 SKU 推库存端点，设计上带两天 TTL） | 无（读 Woo 原生库存） | **GAP-9 → 票 #69（业主 2026-10-11 事实确认：真实 ERP 存在、待接入）**。审计时的"按无处理"默认被翻转：本地模拟 ERP 先行 → 新实现接入通道（Woo 原生库存为唯一权威，不抄旧代码、不携带旧 TTL）→ #17 随行休眠上线 → 真 ERP 到位即接 |
| `tvb2b/v1/funnel`（10 事件粗粒度） | 无 | GAP-10 → **裁定废弃**（无消费方、无报表存在过；后续若做分析属新产品工作非对等项） |
| `tvb2b/v1/storage-compatibility` | ability `linker/check-compatibility` | 重建 |
| `linker/v1/materials` + `tvb2b/v1/material-runtime` | `linker/v1/engineering-feed` | 重建 |
| `tvb2b/v1/product-figures-migration`（一次性） | tools/migrate/7-facts | 重建（一次性承接） |
| `tv-b2b/v1/release-state`（运维诊断快照） | 无；services/{engine,genie} 有 /health | GAP-12 → **裁定：不补 REST**（/health + 日志够用；事故驱动再加） |
| `tvb2b/v1/projects` 全组 10 条 | `POST linker/v1/solutions` + #14 + 询盘 | 简化重建（裁定：旧 Project 评审/媒体流废弃）；媒体部分 GAP-13 |
| `tvb2b/v1/quotes` + accept | 无 | 废弃-裁定（spec 11） |
| `tv-refdesk/v1/answers` | 无（Genie search-knowledge 部分代偿） | 随 GAP-4 |
| `linker-ai/v1/vision/intent` / `extract`（铭牌照片） | 无（Genie 无图像输入） | **GAP-14 → C 类默认：切换不带**。线上按钮真实存在（spec 6 记录），但无使用证据、旧链路质量本就弱；一句话可翻案 |
| `linker-ai/v1/workspace/analyze` | 无 | 随 GAP-4 |
| `linker-ai/v1/assistant/*`（message/suggest/chat×6） | `linker-ai/v1/genie/turn` + vote；会话 CPT | 重建 |
| `linker-ai/v1/admin/reindex` / `status` / `tool-truth-baseline` | 无 REST；索引发布走 services/genie/ops | 重建（运维形态变化注记） |
| `linker-ai/v1/design/*` 7 条 | services/engine 3 条（配置器直连） | 重建 |
| `linker/v1/components` | engineering-feed + #14 candidates | 重建 |
| （新增） | `linker/v1/selection-facts` | 新面（#7 契约） |
| 旧 store-api-gate.php（wc/store/v1 价格门） | Gating/StoreApiPrices.php | 重建 |

**命名沿用裁定（来自第二路全拆审计，2026-10-11）**：新树出现旧 `tv-woo-b2b-catalog`/`tv-storefront-pdp` DOM id、`--dlk-radius` 变量、`linker/v1`+`linker-ai/v1` REST 命名空间、`~/.config/terravolt-builder/` 凭据路径。裁定：**全部保留**——DOM id 服务"复刻线上设计"（逐区块对账的比对锚点），REST 命名空间保外部连续性，凭据路径是本机既定位置；随 #16 呈现层正规化自然消解，不为改名而改名。

## 3. 邮件面

| 旧邮件 | 新对应 | 状态 |
|---|---|---|
| 新客户 → 管理员 | NewCustomerEmail + 客户欢迎信（Woo 原生经队列） | 重建 |
| 客户状态变更（审批通过/限制/拒绝）→ 客户 | 无 | 废弃-裁定（无审批） |
| 公司资料变更 → 管理员 | 无 | **GAP-15 → 裁定：废弃**（变更即邮件属审批时代口径；当前量级不需要，事件驱动再加） |
| VAT 校验失败 → 管理员 | VatReviewEmail（仅结论变化时） | 重建（口径收窄为裁定） |
| 发票号分配 → 客户 | 无；ProformaIssuedEmail 替代 PI 事件 | 废弃+重建 |
| 每日摘要（09:00 待审+待付） | 无 | **GAP-15 → 裁定：废弃**（审批/在线支付已废；每询盘即邮件已覆盖"未处理提醒"功能；量级变化再议） |
| contact 表单回执 + 团队 | 无 | GAP-8 → 票 A |
| project 提交 ack（客户+团队） | InquiryReceivedEmail + NewInquiryEmail | 重建 |
| project 评审结果 → 客户 | 无 | 废弃（人工评审流由 PI 流替代） |
| From 身份/收件路由/Bcc | Outbox/TeamEmail + Settings Bcc | 重建 |
| 邮件失败重试 + wp_mail_failed 日志 | Outbox/JobStore/Throttle（更强，全 wp_mail 入队） | 重建 |
| Woo 事务邮件 Sie 体 + on-hold 附 PI | CustomerOrderEmail + 模板 + de_DE_formal.po | 重建 |
| AI provider watch 告警（daily） | 无（Genie 有 SQLite 日志+投票） | **GAP-16 → 票 C：服务健康告警最小件**（不搬旧 watch，做 genie/engine /health 失败发邮件的一次性检查） |
| AI weekly report（weekly） | 无（#16 持续评估套件代偿，测试口径非运行时） | **裁定：废弃** |
| 密码重置/新用户（WP core） | Outbox 拦截全部 wp_mail | 重建（经队列） |

## 4. 后台/管理面

| 旧 | 新 | 状态 |
|---|---|---|
| "Linker B2B Ops" 运营台 + 15 个 wp_ajax + audit-log + admin-users | 无（新仓库零 wp_ajax） | 废弃-裁定（spec 11 删除清单） |
| 订单 meta box | Proforma/AdminBox + Inquiry/OrderAdmin | 重建 |
| 商品编辑器"Linker product data" | 参数表/卖点 → #8 迁移 + `linker_specs` meta（按 spec 12 §6 只在标准编辑器维护）；图值 → FiguresMetaBox | 重建 |
| 商品文档 meta box | 无编辑入口（前端读迁移的 URL） | **GAP-17 → 票 A（小件）** |
| 商品 availability meta box（"不供应"标记） | 无；库存口径 = Woo 原生（+GAP-9 若 ERP 为真） | 随 GAP-9 |
| AI 设置页 | 无 WP 设置页；Genie 配置服务端收口 | 形态变化注记（裁定） |
| （新增） | SettingsTab（对接人/Bcc/银行条款/PI 前缀）、FaqsMetaBox | 新面 |

## 5. 定时任务与队列

| 旧（hook） | 新 | 状态 |
|---|---|---|
| i18n 翻译队列 ×3 | Jobs.php（AS 队列+重试） | 重建 |
| 管理员邮件重试 + 发票通知重试 | Outbox.php:167（AS） | 重建 |
| 业务邮件副本 job | Outbox Bcc | 重建 |
| 每日摘要 | 无 | GAP-15 裁定废弃 |
| 报价过期扫尾 | 无 | 废弃-随报价 |
| Stripe 支付对账 | 无（#17 step3 删网关） | 废弃-裁定 |
| 库存镜像回填 | 无 | 随 GAP-9（默认不做） |
| VIES 复查（15min） | 注册时同步校验 + VAT 邮件 | 重建（设计变更裁定） |
| AI 对话清理（daily） | 无；`linker_conversation` CPT 无保留策略 | **GAP-18 → 票 C：保留策略**（匿名会话过期清理，共享主机防 PPT 无界增长） |
| AI provider watch / weekly report | 无 | GAP-16（票 C）/ 废弃 |
| project 媒体清理 | 无 | **GAP-13 → 裁定：随旧 Project 媒体流废弃**（#14 屋顶步+CSV 覆盖设计输入；一句话可翻案） |

## 6. 客户旅程横切

注册（无审批+VIES+角色）→ 登录（语言无关门）→ 密码重置（经 Outbox）→ 看价（三重 Gating+访客指引）→ 加购 Lösungsentwurf → 询盘（→ wc-inquiry-received）→ PI（PI-YYYY-NNNN/30 天/403 门）→ 账户四页 → 再询盘（挂 Woo order-again）→ 对比（Genie；独立页 GAP-3）→ 文档下载 → 配置器（含保存方案 + claim cookie）→ Genie。旧"Project 场地事实主人"对应物 = save solution + roof step + Saved solutions（简化裁定）。

## 7. 运营/基础设施面

| 面 | 旧 | 新 | 状态 |
|---|---|---|---|
| Redis 对象缓存 | 无 | #5 本地已启；#17 主机启用 | 重建 |
| LiteSpeed | 全页缓存 + ?cbq | #17 step6 全清+每分钟 cron+DISABLE_WP_CRON | 重建 |
| 部署管线 | 临时桥 + snippet 退役/清除 | #17 step3：删 code-snippets 插件、先导出 3 条活动行并确认被覆盖 | 重建（snippet 生态消失） |
| 生产错误记录 | mu linker-error-recorder.php（主机 log_errors=OFF 是既证事实） | **无** | **GAP-19 → #17 部署清单**（转世为独立 mu 或并入 linker-tools 小模块） |
| 监控/日志 | watch 告警、weekly、release-state | /health、SQLite 日志+投票 | 部分（GAP-12/16/19） |
| 备份/快照 | backend_snapshot、snippet_archive | tools/pull snapshot（更强）+ #17 step1 | 重建 |
| 自助登录 | magic_login.py（审批后台用） | 本地 `just login`；线上无审批流 | 废弃-随审批 |
| 日常内容运维工具 | audit_german_site 等 | tools/{pull,migrate,faq}；德语审计按需 | 按需 |
| mu-plugin 遗留 | linker-i18n-mu-loader.php（删旧插件后无害空转） | #17 未列 | **切换卫生项 → #17**（顺带删除） |
| SEO 重定向 304 条 | legacy-redirects.php（255 产品+31 分类+18 退役页，含旧 /checkout/） | Redirects.php 仅 5 条 | **GAP-6 → #17：三张表迁入，不补则切换当天旧外链全 404** |
| 旧 design-engine VPS | services/design-engine | services/engine（重写）+ ops/release | 重建 |

## GAP 汇总（19 项终局处置）

### 已裁定（本轮，工程线按证据自裁，业主可一句话翻案）
- GAP-3 compare 页、GAP-5 advisor 页 → **301 至 /products/**（Genie 代偿）。
- GAP-4 faq-download → **静态 FAQ/文档目录页**（保 URL/SEO；Q&A 由 Genie 代偿）。
- GAP-10 funnel 计量、GAP-12 release-state、GAP-15 摘要+资料变更通知、weekly report、GAP-13 project 媒体上传 → **废弃**（理由各见对应行）。
- 命名沿用四类（tv-* id、--dlk-*、REST 命名空间、凭据路径）→ **保留**。

### C 类默认（证据支撑的默认路径，业主一句话可翻案）
- **GAP-9 ERP 推库存：已翻案（业主 2026-10-11：真实 ERP 存在、之后接入、细节未交付）→ 票 #69：本地模拟先行 + 新接入通道 + 切换随行。** 审计时的"按无"默认及证据保留在案说明当时推断依据。
- **GAP-11 bulk order/CSV：不带**（未裁定项纠正为默认废弃；无使用证据）。
- **GAP-14 vision 铭牌识别：切换不带，留待客户需求**（线上按钮存在但零使用证据）。

### 落票
- **票 A（切换前面收口）**：GAP-1 搜索框+?s= 范围（spec 13 既定设计）；GAP-8 contact 表单管线化；GAP-17 文档维护入口。
- **票 B（旧工具页处置）**：GAP-3/5 两条 301 + GAP-4 静态页。
- **票 C（生产观测小件）**：GAP-16 健康告警最小件 + GAP-18 会话保留策略。
- **#16 追加**：GAP-2 场景段渲染（产品页=复刻线上裁定）+ Storefront 删除后重跑全拆审计（已登记）。
- **#17 追加**：GAP-6 重定向 304 条迁移；GAP-7 先核 SEOPress schema 再定补否；GAP-19 错误记录；i18n-mu-loader 卫生删除；守卫测试升级（TokensTest 改规范化哈希对照，拦 CSS 整体搬运——本轮两路审计共同发现它拦不住）。

## 审计方法局限

1. 线上未登录 GET：账户区子页/checkout 内部以新仓库验收记录+代码为准，未线上实测登录态。
2. 线上 3 条活动 snippet（#27/#351/#372）未逐行展开；#17 step3 已要求切换时导出复核，若含未入本清单的面以导出为准。
3. sitemap 只覆盖可索引 URL；noindex 面靠代码枚举，可能漏掉仅由主题/LC 模板承载的边缘模板。
4. Woo core 能力按 Woo-first 原则视为不变项，未逐版本核对行为差异。
5. 本表"已重建"以 main 2eb8da4 为准；#16/#17 实施后需增量复核。
6. 旧 repo 一切以 `refs/landed/chain-tip`（f007a9dd）为准，未落地改动未审计。
