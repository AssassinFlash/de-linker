# 执行票的交付与验收协议（自旧项目决议迁入，按 AGENTS.md 修订）

## 1. 执行票票面必须包含
头部三行 `Parent: #3`（地图）/ `Batch` / `Blocked-by`（全部关闭才能开工），label `wayfinder:task`；**交付结果**（一段，可验收的终态）；**范围（文件）**（逐文件，含行号或函数名）；**不做**；**验收**（复选框，每行写清用什么真实数据、在哪个环境、量什么）；**证据入口**。没有这六节的票不派。

## 2. 执行会话规则
- 每票一个全新会话：`gh issue view 3` 看地图，`gh issue view N` 看票（头部 `Blocked-by` 全部关闭才能开工），从 `main` 切 `t<N>/<slug>`；工作树放 `~/Documents/de-linker-worktrees/de-linker-t<N>`，主检出 `~/Documents/de-linker` 保持 main。
- 本轮发现的问题本轮修（含票外问题），不开 follow-up；修完全量再评审。
- 任何数字/阈值/规则先追来源；外部核实只走 Apify。
- 子代理用 Opus 5.5；一张票不并行写同一文件。

## 3. 三件套（缺一不交付）
**A. 代码审查**：Spec（需求与业务结果，对照票面 + 关联决议）与 Standards（职责、数据流、重复、复杂度）两名独立评审，看从起始提交到最新的全量 diff（含未提交）；发现项必须有位置、触发、影响；必改项清零后再全量评审一轮；无必改即停，不空转。
**B. 自动化测试**：改动所在层的真实夹具测试，入口统一为 `just test`（PHPUnit、Vitest、Playwright、pytest 都由它调度；`just check` 跑静态检查，`just build` 与 `just build::check` 负责构建产物）；回归用例表（§5）中与本票相关的行必须有可运行断言并通过；不跑与改动无关的全量套件。
**C. 基于 Computer Use 的视觉验收**：在真实浏览器（本地实例的登录态用 `just login <name> [--user <login>]` 打印的一次性链接，不用密码）对本票触及的每个页面/状态，在 1440 与 390 两种视口、EN 与 DE 两种语言下截图并逐项核对：布局（不溢出、不遮挡、不撑高）、字体（族、字号、行高与设计稿一致）、配色（token 一致、对比度）、交互反馈（pending/success/error/retry 可见且稳定）、细节状态（空态、长文案、键盘 Tab 顺序、焦点环）。基准 = 设计稿 / 票面需求 / 交互预期（复刻面的像素门按 AGENTS §5 执行）；任何影响理解、操作或品牌一致性的问题在交付前修复。截图归档：`docs/acceptance/<date>/<票号>/`，文件名 `<page>-<viewport>-<lang>-<state>.png`（本地与线上对照时 state 写 `local`/`live`）。

## 4. 上线与回滚
- 本仓库对线上只有一次上线：`tools/cutover` 的一次性切换（`docs/specs/17-cutover.md`；窗口前在本地实例 `just cutover drill` 演练完整切换 → 回滚 → 再切换，演练跑的就是窗口里那份代码）。生产写入走 SSH（AGENTS §5：`ssh hostinger-de-linker`，WP-CLI 在 `/usr/local/bin/wp`，每次写入先备份、后读回）。
- 服务发布经 `just cutover services`：engine 与 genie 都由 `services/genie/ops/release.sh` 以发布根参数发布（版本目录 + `current` 软链 + 回滚）；Genie 的文档索引经 `ops/publish_index.py` 发布（`/opt/linker-genie/index/`，服务读 `current/index.sqlite`）。
- 切换窗口后的验证是 `just cutover verify` 的只读回归（双语 URL、Genie R1/R2 真实请求、产品页 `Product` 节点恰为 1、旧地址 301 抽验）加上 §5 回归表与票面的断言。
- 回滚：恢复切换前的备份——插件目录、`.htaccess`、`wp-content/mu-plugins/` 与 mysqldump 导出的数据库（spec 17 §8；`drill` 已在本地演练同一份代码）。

## 5. 回归用例表（期望集合取自 `live-catalogue-facts.md`；EN/DE 各跑一次）
| # | 入口 | 输入 | 期望 |
|---|---|---|---|
| R1 | 聊天 EN | 住宅三相 10 kWp 原句 | qualified ⊆ 住宅三相集合；无 ETR/ESA；卡片 ⊆ 正文 refs；一个追问 |
| R2 | 聊天 DE | 同一句的德语版 | 同 R1，德语文案 |
| R3 | 冲突 | "12 kWp … HS3-5K?" | HS3-5K 不推荐，说明 PV 上限 10 kWp |
| R4 | 事实不足 | "hybrid inverter for a home" | 追问相数或 kWp 一项，列出单相+三相 |
| R5 | 商品页 | 在 H2-10K-T3 页问"哪些电池有文件配对" | 只列 documented 的，附文件 |
| R6 | 购物车 | "我的购物车能配一起吗" | 读购物车，逐对 compatibility |
| R7 | 账户 | "我上一份 Proforma 到哪一步了" | 登录 → 阶段条；未登录 → 要求登录 |
| R8 | 范围外 | "你们做安装吗" | 只有团队邮箱句（服务附联系卡时为邮箱句 + 卡，#243；卡不连续两轮） |
| R9 | 禁词 | 任何问价/库存 | 无 Incoterms、无数量/日期、价格按门控 |
| R10 | 加装 | "I have a GoodWe GW10K-ET and want to add a battery" | 只列对 ET 有放行文件的电池，三值标注，附文件 |
| R11 | 电压等级 | "48 V battery for a single-phase home" | 追问或按 48 V 筛，HV 机型不出现 |
| R12 | 备用电源 | "three-phase hybrid with backup for a home" | 只列备用=yes 或 with accessory 的，条件写明 |
| R13 | 入口 | 商品页 H2-10K-T3 点"What pairs with this model?" | 等同 R5，上下文自动带 product_id |
| R14 | 披露与范围 | 打开 dock | 披露句出现一次；问"Lieferzeit?" 只有邮箱句 |

## 6. 本线 review 入口
执行 AI 交付时在票的 Notes 写：起始/最终提交、三件套证据路径、未解问题 = 0 的声明。本线派 Spec 与 Standards 两名独立评审审全量 diff、抽查视觉证据、复核真实请求（R1/R2 适用时）；无必改项才 squash 合并 PR 并关票，否则打回原执行会话修复后再审。

## 7. 2026-10-09 修订（新仓库）
- 票在 GitHub Issues（地图 #3）；分支名 `t<票号>/<slug>`；PR 标题以票号开头；PR 描述附三件套证据路径。
- 工具名：Genie - Linker's AI assistant；Solution Configurator / Lösungskonfigurator。用词与 FAQ/文案规则以 AGENTS.md 为准。
- R7 的"订单状态"改为"询盘状态"（四状态）；R1–R14 其余不变；配置器用例见票 #14。
- 没有硬规则：协议可被证据推翻，改时写明证据。
- §3C 的登录与截图归档改为本仓库的做法（#5）：本地登录用 `just login`；旧仓库的 `tools/magic_login.py` 要经 Code Snippets 在线上开桥，本仓库没有也不用它。截图归档 `docs/acceptance/<date>/<票号>/`，与规格 5 的验收一致。
