# Account workspace：Preline 形制 + 业主移动门户语言

2026-10-13，分支 `lane/dashboard-preline`，起点 `bbd5744`。接续同任务前序未提交内容，没有回退它们。全部实现/实例操作在本 worktree，唯一实例 t110（127.0.0.1:8975），没有 production / push / 其它实例操作。

## 先看什么

- [桌面 Overview 并排](compare-overview-1440.png)
- [移动 Overview 并排](compare-overview-390.png)
- [移动询盘详情并排](compare-inquiry-detail-390.png)
- [移动公司编辑并排](compare-company-390.png)
- [目标数值与最终值](metrics.md)
- [原始移动参照](ref-mobile-portal.png)，**来源：业主在当前简报提供的学生门户设计稿**。完整图留档；裁切区域写在 compare.py，便于复算。

这是重设计的视觉交付候选，不声称业主已满意、不声称同数据/同色皮肤像素一致。最终观感裁决仍归业主。

## 映射与采用值

### 桌面

- Overview：analytics 的侧栏/白卡分节，CRM index 的四统计卡（146px高、20px padding、20px gap、16px圆角）。不移植人口地图或虚构趋势。
- Inquiries：CRM customers 的单表/徽章/行操作；保留商品副行与所有现有操作。DE 标签更长时自然换行，不删动作缩行。
- Inquiry detail：customer-details 的信息区 + invoices 的 PI 下载；Woo 商品/总额/地址表仍原生输出。
- Documents：customer-details-invoices 的文件形制，保留现有 Document / Date / Download (PDF) 表头与真实 URL。
- Saved solutions：CMS posts 的列表密度 + invoices 的下载动作；当前 t110 没有私有 saved solution 数据，实拍为既有空态，未造记录。
- Company / Account：admin profile 的白卡、32px padding、38px输入、8px输入圆角。原生表单字段和提交链未替换。

现状工作区1240 / 主区888 / 侧栏240 → 采用全宽1440 / 主区1120 / 侧栏260；左右外边距20、栏间20。CSS max-width1600只在账户登录态消费；没有改共享 token。参照 admin 主卡1140，我们1120（20px差是保留两边对称工作台 gutter）。标题从20放大32/600/44.16，**主动高于 Preline 的18/600/28**，依据业主晚补“大气/沉浸感”，不伪称逐项完全相同。

### 移动（主参照为业主图）

- 欢迎区：首字母圆标 + Welcome back / 客户 first_name（无 first_name 时 display_name）+ 功能副题。采用无时区承诺的欢迎语，不推断“早上”。
- Home 四列快捷入口；四态统计两列，一键按状态到现有询盘路由。
- 列表：信息行/副行/状态 pill；文件表改 grid 行卡而不是窄表横向滚动。桌面表头仍在 DOM 与可访问树。
- Inquiry detail：信息左右对齐 + 金额24px + PI 下载固定底部；现有商品、文件、Request again 都可滚到、可点击。
- Company / Account：首字母块 + Woo 全宽编辑；Save 固定在 tabs 上方。Select2可见国家控件48px，密码显隐按钮44×44（不是只扩大 input）。
- 全面四键底栏 Overview / Inquiries / Documents / Account。完整七入口在 Account menu 的原生 details 折叠面（Saved solutions、Company、Logout未隐藏为不可访问）；桌面保留完整侧栏。
- 390侧边距16；两列统计173×116 / gap12；四快捷83.5×80 / gap8；底栏64+1边框=65。CTA底部偏移76+safe-area；普通页预留100、CTA页220+safe-area。逐面最后一链接 hit-test 证明可滚出固定 UI 覆盖区（mobile-check.json）。

原图是合成栅格，不存在DOM；图上的 exact CSS 不可获取。移动目标值是对原图语言的明确设计采用值；Preline移动实测另留390/430 PNG与JSON。裁切图放大到390×844并排，清楚标为 raster crop，不当作字体/pixel parity证据。

## 功能边界

LC组成在 `content/livecanvas/account/`；所有样式只在 `content/windpress/account.css`。PHP只提供菜单、客户名字、四态及已有字段，Woo继续端点分发、权限、表单、nonce与下载。

四态快捷曾试用 `?inquiries=state`，实测发现 **inquiries 同时是 Woo orders 端点的 page query var**，字符串状态被页码absint解释成错误页（UI空表但存储有1条）。修正为 `?inquiry-status=state`，不改端点 URL；白名单 selection 统一供 query / heading / tabs / pagination，保留customer/page/paginate，测试确认已存在 PI 从0行恢复1行。这里只增 read-only选择，不增状态规则。

不改 account.spec.ts / chrome.spec.ts / commerce.spec.ts。全套 PHP 首跑暴露两条已有 stale mock 注册断言（ArchiveSchema wp_head 与 Approval login_errors），只在授权 tests 路径补上真实已有钩子的断言，未改业务代码迎合测试。

## 新文案与双语

新增功能语句仅：`Welcome back` → `Willkommen zurück`、`Your account workspace` → `Ihr persönlicher Arbeitsbereich`。其它菜单/状态/字段复用已有i18n。

文案自审初稿曾考虑 Good morning；反向检查指出没有客户时区，换为 Welcome back，不造事实。最终两句功能标签经过 linker-copywriting 九项 Hard Stops：无借信、证明堆砌、否定对比、强保证、物流/时间承诺、helpdesk命令、术语泄漏、维修式卖点或用户未来/作业。Actor/Future/Weight/Duration与slogan均不触发。**独立对抗文案复核由后续workflow reviewer完成，本线自审不冒充双评审。**

`__()`均 linker-commerce域；PO/POT/MO更新。`msgfmt --check`编译；`wp i18n make-json --no-purge`输出 Created 0 files（此插件账户无JS源码/handle），按简报额外交付 account Jed JSON镜像，运行时PHP仍读MO；不新增脚本加载层。

## 可重跑

```bash
cd /Users/chesterjohn/Documents/de-linker-worktrees/lane-dash-preline
just up t110
just serve t110
# present先同步volume，若cache stale会明确退出非0；不使用allow-stale绕门
just present t110
just windpress-compile t110
just present t110
node docs/acceptance/2026-10-13/account-dashboard-preline/measure.mjs ref
node docs/acceptance/2026-10-13/account-dashboard-preline/measure.mjs ours e2e-en-1791887434348
CAPTURE_LOCALE=de CAPTURE_PREFIX=ours-de node docs/acceptance/2026-10-13/account-dashboard-preline/measure.mjs ours e2e-en-1791887434348
node docs/acceptance/2026-10-13/account-dashboard-preline/mobile-check.mjs e2e-en-1791887434348
python3 docs/acceptance/2026-10-13/account-dashboard-preline/compare.py
python3 docs/acceptance/2026-10-13/account-dashboard-preline/metrics.py
(cd plugins/linker-commerce && /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit)
just e2e t110 specs/account.spec.ts
just e2e t110 specs/chrome.spec.ts
just e2e t110 specs/commerce.spec.ts
```

截图使用前序 e2e 已有 approved 客户133、自己的空用户 dash-preline。每次 mint one-time link，链接/密码不写证据；不写页面内容，不生成询盘/方案夹具。e2e自有用户写入与商务实测属用户明确要求的检查。

## 本线已跑结果

- PHPUnit：`Tests: 926, Assertions: 4363, Skipped: 45.`（无失败；45个集成测试无真实WP夹具环境，诚实保留skip，非926全部执行）
- account：11 passed；chrome：5 passed；commerce：2 passed（完整命令见LaneResult）。
- changed PHPCS：0错误；targeted PHPStan `[OK] No errors`。
- WindPress：cache新版mtime及anchor类通过；present结束 `Success: Presentation installed.`。先同步volume/后compile/再present。不能只compile旧volume再看“cache较新”的时间戳。
- measure：本地EN/DE各7面×3视口共42，overflow均为视口宽；前序390 Overview document586溢出已消除。
- mobile-check：7面×EN/DE×390/430共28，menu=7、目标高宽≥44、末项hit-test、CTA和tab不碰撞全部通过；四状态链接被独立重跑，已有proforma实测1行。
- rg：账户相关源码0个硬编码十六进制色；使用 token色、token混色，未碰其它卷颜色。

## 并排 PNG：桌面（1440×900 原尺寸）

- compare-overview-1440.png
- compare-inquiries-1440.png
- compare-inquiry-detail-1440.png
- compare-documents-1440.png
- compare-saved-solutions-1440.png
- compare-company-1440.png
- compare-account-details-1440.png
- compare-region-tiles-1440.png / compare-region-table-1440.png（未缩放区域）

## 并排 PNG：移动（390×844，业主图裁切 vs t110）

- compare-overview-390.png / compare-de-overview-390.png
- compare-inquiries-390.png / compare-de-inquiries-390.png
- compare-inquiry-detail-390.png / compare-de-inquiry-detail-390.png
- compare-documents-390.png / compare-de-documents-390.png
- compare-saved-solutions-390.png / compare-de-saved-solutions-390.png
- compare-company-390.png / compare-de-company-390.png
- compare-account-details-390.png / compare-de-account-details-390.png

ref-*.png为参照原尺寸；ours-*.png为t110 viewport；ours-en/de-*-bottom-390/430.png是末项可点证据。baseline-*记录接续前序状态，不是新的验收结果。

## 未能验证 / 限制

- t110当前没有private saved solution，列表有数据态与该数据的report/add-to-draft操作没有造夹具实测（被禁present之外数据写入），只交付真实空态、现有服务单测、完整四入口与形制；不新造saved solution详情路由。
- 没有approved多页询盘客户可用；customer-3有49个cancelled但approval meta不存在→pending gate。未给既有迁移客户写approval以绕门；pagination状态保留以单测验证。
- PHPUnit45项集成测试skip；未设置 LINKER_TEST_WP。
- Computer Use专属验收与独立Spec/Standards review没有在施工agent执行；PNG/DOM是本线证据，独立复核在workflow后续。业主最终观感不属于自动测试。
- 原图无法提供DOM目标值；没有伪造像素阈值。工具 still_crops 因cv2缺失失败，随后直接Pillow裁切/并排成功，脚本可复算，无全局环境修补。
