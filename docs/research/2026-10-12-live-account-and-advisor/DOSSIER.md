# 线上 Advisor 双形态 + 账号后台 实拍档案（2026-10-12）

调研对象：https://de-linker.com/ 线上站（英文界面）。方法：Playwright 真实浏览，1440×900 与 390×844 双视口截图 + `getComputedStyle` 逐件量取。本档案是结构/现状证据：Advisor 的视觉不是目标（业主已判定其"复刻 OpenAI 复刻成四不像"），要带走的是**形态结构、状态机与入口组织**；账号后台部分是重建**同步基线**，令牌数字均来自本机实测。

取证条件备注：
- 所有截图在 `captures/`，命名 `组件_状态_视口.png`。
- 演示伙伴账号（delinker_partner_demo，ID 3）按任务给定的口令两次原样提交均被线上拒绝（服务器返回统一错误"The sign-in details do not match an account…"，用户名/口令字段值已逐字校验无误）；改用本机对该演示账号既有的 magic-login 机制取得登录态（一次性 token，用后即焚、复用返回 401），全程未改动任何账户数据，拍毕已登出并复核 `logged-in=false`。口令从未写入任何文件。
- 采集期间浏览器出现与本项目无关的外来标签页（OpenAI 域名，来自共用此浏览器配置的其他进程），与本站无关，未影响采集。

---

## Ⅰ Advisor 双形态设计拆解

### 1.1 事实总览：其实是一个组件、两种 variant、四个入口面

线上 AI 助手叫 **Linker Advisor**，全部由同一个自定义元素 `<linker-assistant>` 承载（旧插件 lia-* 类名体系，Lit 渲染），一个组件两种形态：

| 形态 | 载体 | variant | 位置 |
|---|---|---|---|
| 坞（drawer） | 全站每页 body 直挂 | `class="lia lia--drawer"` `context="sitewide"` | 右下角浮动 |
| 完整页（workspace） | `/linker-advisor/` 页面 `.lia-workspace-mount` | `class="lia lia--workspace"` | 整页应用 |

两个形态**共享同一套消息/composer 组件类名与会话存储**：在坞里发出的会话，打开 `/linker-advisor/` 后左栏 "Today" 组里出现同名会话、主区直接续显——状态互通（浏览器本地存储）。`/linker-advisor/` 页本身 h1 "Linker Advisor" 视觉隐藏（0×0），页面 title 为 "Ask About a Product, Model or Datasheet | Linker"。

四个入口面：
1. **右下角坞**（全站，含 /linker-advisor/ 自身也挂坞）。
2. **完整页 `/linker-advisor/`**：页头导航 "Linker Advisor Chat"、页脚 "Linker Advisor" 链接、坞面板头部 "Open full screen" 钮、首页 hero 快捷问题链接，全部指向它。
3. **首页 hero 内嵌迷你控制台**（`section.hero-cinematic`）：输入行（placeholder "Search equipment models, battery pairings, or datasheets…"）+ 按钮 "Identify by nameplate photo / Attach schematic or document / Voice input" + 三条快捷问题（10 kW storage systems 等，均链到 /linker-advisor/）+ "Privacy & Data"。
4. **账号 Documents 页内联启动钮** `.lia-launch--inline`（167×47 pill，#172636，白字 14/700，label "Linker Advisor" 带图标）。

对应截图：`advisor_home_dock_closed_1440`（坞关闭）、`advisor_dock_closed_elem_1440` / `advisor_dock_hover_elem_1440`（坞元素关闭/hover）、`advisor_panel_open_1440` / `advisor_panel_open_elem_1440`（面板欢迎态）、`advisor_panel_typing_1440`（输入中）、`advisor_panel_conversation_1440`（对话往返后）、`advisor_hero_console_1440`（hero 内嵌）、`advisor_page_full_1440` / `advisor_page_viewport_1440`（完整页整页/首屏）、`advisor_page_rail_elem_1440`、`advisor_page_apptop_elem_1440`、`advisor_page_composer_elem_1440`（组件级）、390 组：`advisor_home_dock_closed_390`、`advisor_panel_open_390`、`advisor_home_dock_closed_after_390`、`advisor_page_viewport_390`、`advisor_page_rail_open_390`。

### 1.2 坞（drawer）形态

**关闭态** `.lia-launch`（button，aria-label "Linker Advisor"，aria-expanded 切换）：
- body 直接子元素；`position:fixed; right:20px; bottom:20px`；1440 视口 50×50（390 视口 45×45）。
- 圆形胶囊 `radius:999px`，底色 **#172636**（rgb 23,38,54），白图标（`lia-launch-mark` 内 SVG 火花纹），label span `display:none`（纯图标）。
- 阴影 `rgba(11,31,51,.28) 0 10px 26px, rgba(11,31,51,.18) 0 2px 6px`；字体栈 Inter, Arial, sans-serif；过渡仅 `opacity .12s linear`（hover 无展开动画、无几何变化）。

**面板** `.lia-panel`（点坞展开）：
- 1440：`position:fixed`，**400×600**，白底，`radius:16px`，`border:1px #E1E6E9`，阴影 `rgba(18,34,56,.15) 0 18px 64px, rgba(18,34,56,.08) 0 4px 16px`，flex column。
- 390：**全屏 bottom sheet**：`inset 0 0 0 0`，390×796，`radius:0`。
- 打开状态跨导航保持（sessionStorage 级：切页后仍 is-open）。

面板内部（自上而下）：
1. **头部** `.lia-panel-head` h53，padding 8/12/8/18，flex gap8：
   - `.lia-drawer-brand`：`h2.lia-title` "Linker Advisor"，13px/650，#0B1F33。
   - `.lia-head-btns` 四枚 32×36 图标钮（透明底 radius9）：New conversation（+）/ **Open full screen**（→ /linker-advisor/）/ Conversations（开历史）/ Close advisor。
2. **历史抽屉** `.lia-history`（默认 0 高，Conversations 钮展开）。
3. **会话区** `.lia-conversation`（flex column gap12，padding 20/18）：
   - 欢迎态 `.lia-empty.lia-welcome.lia-helper-welcome`：h3 "Get help with your solar project" 22px/650 #0B1F33 **居中**；副文 12px 级；`.lia-helper-suggestions` 两枚 38px 链接式快捷钮（"Check compatibility"…）。
   - 用户消息 `.lia-message--user lia-message--editable`：**深色气泡 #0B1F33**，白字 13.5px/19.6，`radius:14px 14px 5px`（右下小尾角），padding 11/14，`max-width:84%`，margin-left≈58px（右对齐）。
   - 助手消息 `article.lia-message--assistant lia-message--linker-confidence`：白底无框，`radius:14px 14px 14px 5px`（左下尾角），结构：
     - `.lia-answer-state` 置信徽章行：12px/600，"Open points remain" 色 **rgb(138,75,18)**（琥珀）；
     - `.lia-answer-text` 13.5px/20.9 #172636（正文）；
     - `.lia-answer-list` 证据列表；
     - `.lia-answer-tools` 工具 chips：12px pill `radius:999`，`border:1px #DFE7EC`，#5F6B7C，padding 6/12——"Copy answer"、"Discuss with Linker"。
4. **输入区** `.lia-composer-zone`（padding 0/12/10）：
   - `form.lia-form`：374×53，白底 `radius:16px`，`border:1px #D7DFE1`，padding 9/10/8，微阴影 `rgba(32,51,52,.024) 0 3px 8px`。
   - `.lia-input-row` flex gap7：
     - `.lia-vision-button` 34×34 白 `radius:9` `border #DFE7EC`（"+"——传图/文档，隐 `input.lia-vision-input`）；
     - `textarea.lia-input` 无边框透明，14px，placeholder **"Model or datasheet"**；
     - `.lia-voice` 34×34 无底灰图标（语音）；
     - `.lia-send` 34×34 `radius:10px`，**bg #087C73（teal）** 白箭头；空输入禁用态灰。
   - `.lia-privacy` 脚注行 10px #5F6B7C：Examples / 联系 / Privacy 链接。

### 1.3 完整页（workspace）形态 `/linker-advisor/`

布局 `.lia-shell.lia-workspace`（grid，满视口 1440×812，白底）：

- **左栏** `.lia-rail` 宽 **218px**，bg **#F8F9FA**：
  - `.lia-rail-top`：brand mark 图标 + `.lia-rail-title` "Linker Advisor"；
  - `.lia-rail-new` 按钮 "New consultation"（h40）；
  - `.lia-rail-list` 会话历史：分组标题 `.lia-rail-group`（"Your conversations" / "Today"，37px）；条目 `.lia-rail-item`（h36）——**当前项高亮：bg #E9EEED + 文字 #17685F + 600**，radius 8，padding 8/10；
  - `.lia-rail-bottom` 两枚 `.lia-rail-link`：**"Open Project"**、**"How Linker Advisor helps"**。
- **主区** `.lia-panel.has-conversation`：
  - 顶条 `.lia-app-top` h54 白，flex gap12 padding 8/24：`.lia-rail-toggle`（移动端才显示的汉堡 44×44）+ `h2.lia-app-title`（=当前会话标题）+ `details.lia-tool-menu > summary.lia-context-chip` **"Tools"**（展开 popover：`ol.lkt-spine` 步脊 + `aside.lkt-aside`——配置器/工具入口挂在此菜单）+ `.lia-project-context`（项目上下文槽）。
  - `.lia-conversation` 会话区（与坞完全同构的消息组件）。
  - composer：`form.lia-form` **800px 居中**，`radius:15px`，其余同坞。

**响应式（390×844）**：rail 变 262px 抽屉（transform 平移出屏），顶条出现 `.lia-rail-toggle` 汉堡；panel 全宽 390。dock 面板变全屏 sheet（见 1.2）。

### 1.4 状态机（观察所得）

```
[坞关闭 aria-expanded=false]
   └─click→ [面板开：欢迎态(快捷问题) ─输入─ 发送#087C73 激活]
                 ├─发送→ 用户深色气泡 → (生成) → 助手白气泡{置信徽章+正文+引文+工具chips}
                 ├─New conversation → 重置欢迎态
                 ├─Conversations → lia-history 展开(会话列表)
                 ├─Open full screen → /linker-advisor/ workspace(同一会话续显)
                 └─Close advisor → 坞关闭
/workspace: rail 换会话/新建；Tools 菜单挂配置器；会话与坞互通
```
回答带**置信分级**：`lia-message--linker-confidence` + 徽章（观察到 "Open points remain" 琥珀态；对应还有已证实态）。回答必须引用站内托管文档（回答正文出现 "Battery Compatibility Overview lists…" 等文件引用）。

### 1.5 令牌提取（Advisor 域，实测）

- 字体：**Inter**（widget 全域：panel/title/消息/composer 均 `Inter, Arial, sans-serif`）——与站点主体 **Plus Jakarta Sans** 是并存的两套。
- 深navy：#172636（坞钮/内联钮底）、#0B1F33（标题/用户气泡，两值并存）。
- teal 行动色：**#087C73**（send 钮）；workspace 近邻色 #17685F（rail 当前项）、#0C7F73（账号域表头，见Ⅱ）。
- 灰阶：正文 #172636、次要 #5F6B7C、边线 #D7DFE1 / #DFE7EC / #E1E6E9、rail 底 #F8F9FA。
- 徽章语义色：琥珀 rgb(138,75,18)（open points）。
- 圆角体系：气泡 14（带 5px 尾角）、面板 16、钮 9–10、chip 999。
- 尺寸：坞 50（m45）、面板 400×600（m 全屏）、rail 218（m 抽屉 262）、composer 坞内 374 / 页内 800、图标钮 32–34。

### 1.6 两形态分工（重建可带走的结构结论）

1. **drawer = 全站轻问答**：欢迎语+快捷问题+单轮/多轮对话，无历史栏（历史折叠在头部按钮里），400×600 浮层。
2. **workspace = 会话管理台**：常驻历史 rail（分组+当前项高亮）、会话标题入顶条、Tools 菜单挂载其他工具（配置器）、800px 宽幅 composer。
3. 同一组件双 variant、同一消息 DOM 词汇（lia-message/lia-answer-*）、同一会话存储——重建时应保持"一套消息组件 + 容器差异"的架构，而不是两套 UI。
4. 入口网络：坞(全站) + 页头/页脚/坞内"全屏"钮 + hero 内嵌台 + Documents 页内联钮 → 都汇到 /linker-advisor/。
5. 视觉本身（居中大标题欢迎语、OpenAI 式布局）按业主裁定不作目标；本节的价值是状态机、组件切分与入口拓扑。

---

## Ⅱ 线上账号后台逐页拆解（重建同步基线）

### 2.0 登录面与"为什么之前看不到"

- 未登录 GET `/my-account/`：**HTTP 200，无重定向**，标题 "Partner Account: Sign In or Register | Linker"。即：它不是隐藏页，而是**登录+注册合页**；未登录看到的是表单（截图 `account_login_loggedout_1440`），后台内容仅登录后渲染。
- 结构：h1 "My account" → h2 "Sign in" 表单（Username or email address* / Password* + "Show password" 切换 + Remember me + "Forgot your password?" → /my-account/lost-password/ + Sign in 钮）→ 登录失败错误条（文案见取证条件备注）→ "Create account" 锚点滚动到同页注册区（h2 "Create account"；分节 "Account and contact" / "Company" / "Delivery and review"；文案 "Trade accounts only. Linker supplies installers, EPCs and resellers. We read every registration ourselves and email you when the account is open."，失败可寄 sales@de-linker.com）。页头另有 Sign in 按钮。
- 登录成功后 title 变 "My account | Linker"，body 加 `logged-in`。

### 2.1 导航组织（重要：没有左侧栏）

账号后台**页面内没有侧导航**。导航 = **页头右侧 "My account" 图标钮**（`.tv-b2b-acct`，44px）hover/click 弹出**下拉菜单** `.tv-b2b-acct-menu`（截图 `account_nav_dropdown_open_1440`）：

- 292×471 白卡，`radius:14px`，`border:1px #DFE7EC`，阴影 `rgba(11,36,57,.2) 0 24px 50px`，锚在页头账号钮下方右对齐。
- 9 项（`.tv-b2b-acct-link`）：**Overview / Proformas / Quotes / Documents / Bulk order / Projects & Support / Settings / Addresses / Log out**（末项 `is-out`）。
- 项样式：13.5px/600，#172636，padding 9/11，radius 9，行高 41px；**无当前页高亮**（下拉不标示所在页）。
- 移动端：该下拉不渲染（0×0）；页头汉堡面板只给 "My account" 根链接（截图 `account_mobile_menu_open_390`），页内导航靠**上下文链接**（"View all Proformas"、"View all quotes"、Settings↔Addresses 返回链等）。

### 2.2 页面容器与字体体系（全域基线）

- 主题 picostrap5；内容容器 `main .container > .row > .woocommerce-MyAccount-content`。
- 1440 视口内容宽 **896–1072px**（x≈272 起，视页面块而定）；390 视口 **311–343px**（边距 32px 级）。
- 每页统一页头：`.tv-b2b-top-header-bar > h1`（20px/500 #15352F）+ 副标 p（14px，#596E67）；订单上下文时加面包屑。
- 字体：**Plus Jakarta Sans**（@font-face 400/500 由插件提供，页面用到 500/600/800 字重）；正文 16px/1.5 基准，正文色 **#15352F**（深墨绿），次要 **#596E67**。
- 卡片色环：底 **#F3F7F2**（淡鼠尾草绿）、边 **#D6DED7**、白内芯 #FFF。
- 按钮体系：
  - 主 `.sf-account-btn`：**#0C7F73 底**，白字 14/500，`radius:8px`，padding 12/16，h48。
  - 次 `.sf-account-btn--ghost`：白底，#15352F 字，`border:1px #D6DED7`，同尺寸。
  - 链接 `.sf-account-link`。
- 状态徽章（pill 999，12px/500，padding 4/10，h30）：
  - 通过/激活：字 **#176457**，底 **#EBF8F4**，边 #9FD5CA（"Partner account active"、"Online ordering active"）；
  - 失败：字 **#8A3128**，底 **#FFF0EE**，边 #E2B4AF（"VIES check failed"）；
  - 幽灵动作钮：#F3F7F2 底 + `1px dashed #D6DED7`（"Re-check VAT ID"）。

### 2.3 逐页

**① Overview `/my-account/`**（`account_dashboard_full_1440` / `account_dashboard_viewport_390`）
- 区块（h2 18px/500 #15352F）：**"Inquiries with your email address"**（h3 15px/500 引导）→ **"Needs your action (1)"** → **"Linker is working on this (0)"** → **"Payment is being processed (0)"** → **"Recent Proformas (45)"**。
- 每区块列询盘行（编号 #1600 等 + View order 钮 + "View all …" 链接）；计数直接写在标题里。45 条 Recent 全量平铺（页高约 1.08 万 px）。

**② Proformas `/my-account/orders/`**（`account_proformas_full_1440` / `_card_elem_1440` / `account_proformas_full_390`）
- 标题 "Proforma history"；计数 "45 Proformas"。
- **Tabs**：All Proformas / Open Proformas（34px pill `radius:8`；当前项 bg #F3F7F2 + 500 字重，未选中透明）。
- **卡片列表**（非 Woo 表格）：`.sf-account-cards` grid gap20；每张 `.sf-account-card` h183：
  - 外壳 bg #F3F7F2、`border #D6DED7`、`radius:16`、padding 6；
  - `.sf-account-card__meta`（grid，padding 12/16）：label 12px #596E67（Status/Order number/Date/Total）+ 值 13.5px/500 #2A2A2A；**状态值随语义降灰**（Cancelled → #596E67）；
  - `.sf-account-card__body` 白芯 `radius:12` padding 16/20/20，微阴影 `rgba(15,23,42,.04) 0 1px 2px`：商品摘要行（"GoodWe GW6.5K-ET" 14px）；
  - 右侧 `.sf-account-btn` "View order"（teal 主钮）。
- 底部分页 `.page-numbers`（h44）。

**③ Proforma 详情 `/my-account/view-order/1600/`**（`account_proforma_detail_1600_full_1440` / `_summary_elem_1440` / `_table_elem_1440` / `_full_390`）
- 面包屑 Proformas / #1600；h1 "Order #1600"；状态 "Awaiting bank transfer"。
- **阶段条** `.tv-b2b-stagebar`（flex gap8）：Recorded→Proforma→Invoice→Delivery 四段 pill（12px，`radius:8`，`border #BFE9E2`，绿字 **#15803D**；类 `is-done/is-active/is-next`）。
- **摘要卡** `.tv-b2b-order-summary`：大图标 + 单号 **DLK-PF-2026-1600** + 状态文案 + "Open Proforma" 主钮（h44）+ facts `<dl>`（PAYMENT TERMS / PAYABLE AMOUNT €191.58 / VAT TREATMENT Standard VAT）+ 尾部两链接 "Contact Linker about this order"、"Warranty & Replacements"。
- 附块：Delivery（h3 13px）、Order history（OL）、Document history（"Proforma" 下载链接）。
- **订单明细表**（Woo 原生 `woocommerce-table--order-details`，被样式化）：白底 `radius:12` padding 16/20；**th 11.5px/800 #0C7F73 于 #F3F7F2 条**，padding 12/16；td 14px padding 12/16，行线 #F3F7F2，行高 46。

**④ Quotes `/my-account/quotes/`**（`account_quotes_full_1440` / `_full_390`）
- 副标 "Quotes waiting for acceptance, and quotes whose price lock has ended."
- 同一套 sf-account-card：Status（"Price lock ended"）/ Quote number（#5341）/ Date / Total（€49,275.31）/ Price lock 字段；body 商品摘要（"Pylontech US5000 + 4 more items"）；"View quote" 主钮。共 4 张。

**⑤ Documents `/my-account/documents/`**（`account_documents_full_1440` / `account_documents_viewport_390`）
- 副标 "Every document from every project: Proformas, invoices, corrections." + **页头内联 Linker Advisor 启动钮**（见Ⅰ.1）。
- **真表格** `table.sf-account-table`（外层 `.sf-account-table-wrap` overflow-x:auto；390 下表格自动收窄到 343 无横滚）：
  - 列：Document / Status / Project / Reference / Date / 操作（View | PDF）；
  - th 12px/500 #596E67，h52，`border-bottom #D6DED7`，padding 16；
  - td 14px #15352F，h56，同边线。
  - 行例：Quote · DLK-Q-2026-5432 · Current · "Residential · Max autarky · 39179" · #5432 · 2026-09-16 · View/PDF。

**⑥ Bulk order `/my-account/bulk-order/`**（`account_bulk_order_full_1440` / `_full_390`）
- 副标 "Paste an item-number list or upload a CSV. Each line is checked against our products."（+ Add to Project 与 Add to cart 的去向说明）。
- 表单 `.tv-b2b-bulk-order__form`：粘贴 textarea（"item-number,quantity"，无数量=1）+ CSV 上传区 + 按钮组 **"Add to Project"（主）/"Add to cart"（ghost）** + "Open current cart" 链接（h44）。

**⑦ Projects & Support `/my-account/projects/`**（`account_projects_full_1440` / `account_projects_viewport_390`）——即"保存的方案"
- 副标 "Continue each design, product list, quote, and Project request without starting again."
- 顶部 "Start a Project" 主钮；`linker-project-card` 列表（sf-account-card 变体，h169/196）：
  - meta：编号 **DLK-P-2026-0225** · 状态（Draft/Current）；
  - body：项目画像 "Residential · Self-consumption · 80538" + 方案版本 "Initial solution · Version 2 · 0 materials" + "Updated 2026-09-24" + "Open Project" 钮。

**⑧ Settings `/my-account/edit-account/`**（`account_settings_full_1440` / `_badges_elem_1440` / `_full_390`）
- 副标 "Identity, password, and the company identifiers used for account review."
- **状态徽章行** `.tv-b2b-settings-status`：Partner account active（绿）/ Online ordering active（绿）/ VIES check failed（红）+ "Re-check VAT ID" 虚线动作钮；支持行 "Questions about your account? Email sales@de-linker.com."
- **手风琴** `details.tv-b2b-settings-group` ×3（summary h47）："Account & contact"（login·email）/ "Company & tax"（公司名 de-linker Demo Partner GmbH）/ "Password change"（•••• + Edit）；首组默认展开。
- 表单件：输入框 白 `radius:8` `border #D6DED7` padding 12/16 h52；label 14/500 #15352F（宽 272 双列）。
- 尾部 "Manage addresses" 链接 → edit-address。

**⑨ Addresses `/my-account/edit-address/`**（`account_addresses_full_1440` / `_columns_elem_1440` / `_full_390`）
- 近 Woo 原生双列：Billing address / Shipping address（各 h2 19px + "Edit … address" 链接 + `<address>` br 分行）；页首有 "Settings" 返回链（h44）。
- 390 视口两列堆叠（各 343px 宽）。

### 2.4 重建同步基线速记

1. 导航=页头账号下拉（9 项，无当前项高亮，无页内侧栏；移动端靠上下文链接）——与 Woo 默认"左侧栏 + endpoints"结构完全不同，重建须复刻这一组织。
2. 三层卡片词汇：外卡 #F3F7F2/#D6DED7/r16 → 白芯 r12 → meta label/value 行；列表页一律卡片（除 Documents 真表格）。
3. 按钮双色：teal #0C7F73 实心主 / 白底 ghost；状态徽章三色 pill；阶段条四段 pill。
4. 语义命名两套并存：`tv-b2b-*`（页头/订单/设置/坞下拉）与 `sf-account-*`（卡片/表格/按钮）——重建映射时按此对照。
5. 文档命名体系：DLK-P-（项目）/ DLK-Q-（报价单）/ DLK-PF-（Proforma）；询盘四态、45 条演示数据、VIES 徽章等业务状态均已在截图中留证。
