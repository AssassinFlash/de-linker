# 未覆盖面 fresh-diff：保留成果交回（2026-10-12）

**这不是全站验收报告。**最终指令要求停止续拍、扫描与实例操作，以已有成果整理 docs PR；本次只交回 **1 对成功 PNG**（首页 EN / 1440 / 访客静态页）。没有产品写入、部署、发信或线上登录；没有使用、记录业主密码。PR 留待 parent 独立 review，不 merge / auto-merge。

## 1. 基线、版本与保留的工作

| 项目 | 可核事实 |
|---|---|
| worktree / branch | `/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-r2debt` / `research/debt-freshdiff`，保留 |
| 截图对应源码 | **`e154e4662f75c92cd61ddca32e15600c65e094e2`**，不是当前 main |
| 实例 | `t112` / `http://127.0.0.1:8978`，保留；本轮未初始化、reset、装 snapshot、运行 just up/present/build |
| 原成功采集 | 2026-10-12 15:08（Mac 文件时间，+08:00）；URL 的 cbq 值见 `captures/dom-counts.json` |
| main 增量核对点 | 当次已存 `origin/main` **`b6bc08410d7c83a01fd6665b93e11bf555dccd5b`**；本交付不宣称这是随后一直不变的最新 main |
| 新规读取 | `/Users/chesterjohn/Documents/de-linker/AGENTS.md` + 当期 owner 指令；旧项目规则不作为依据 |
| 原成功文件 | `.scratch/debt-freshdiff/captures/` 的两张首页 PNG、DOM 计数、原采集脚本和 log 均保留，未覆盖或重拍 |
| 交回工件 | 本文、`DEBT-FRESH-OWNER.md`、`captures/` 原图及计数、`analysis/` 精确差异及对照、`sources/` 原脚本与 log |

`e154e466..b6bc084` 有五个已合入提交：配置器 D1/D2、Genie 取材档案、Genie dock C1/C2、账号/Advisor 取材档案、档案截图数更正。两处实现改动位于工具 CSS 与 build：配置器报告/移动步导航，以及 PDP 关闭态 dock/移动打开态 dock。**它们不使此首页 EN 1440 静态截图变成当前全树证据，也没有理由重拍所有旧图。**它们与本页营销主体没有已证相关改动；工具入口的功能状态仍未测，不能由这个判断推定当前可用。header/accountsync 在途工作未进入本截图，不拿本图否定或验收另一条线的结果。

### 接管盘点与失败边界

- 接管时这个 tree **没有已存 FRESH-DIFF 正文**；`.scratch/debt-freshdiff/` 中只有 `capture.mjs`、`freshdiff.py`、`capture-run.log`、两张首页原图、一个包含首页的 `dom-counts.json`。旧采集计划列 24 对，其中包括额外 spot checks；**计划不等于成功捕获**。
- 相关既有研究、像素工作包、欠账 registry 和账号线上取材是线索，不补算成这次 t112 成对覆盖。没有复制另一条线的登录态图来冒充本轮访客测试。
- 原采集进程停在首对之后，接管观察时已约 13 分钟无新输出。只终止该旧 `capture.mjs` 进程（PID 70310），不动 PHP/MySQL/Redis/engine/Genie 或共享浏览器 tabs。脚本有一个可以无限等待的失败图片分支：图片若已经 `complete=true` 且 `naturalWidth=0`，只挂后续 load/error listener，事件可能早已发生。**这只是停滞的代码候选解释；没有运行时 trace，不能写成已证根因。**本轮未修脚本、未再次采集。
- Browser Use 尝试实际返回 `Browser is not available in subagent`；这是本执行环境的能力边界，不是网页坏了。owner 另明确 provider/runtime 过载不是取消。遵循最后指令，停止工具修理、扫描和续拍，保留已有文件；不归罪 GLM、不重置模型。

## 2. 本轮覆盖：1 个静态状态有证据，55 个未完成

下面按 **14 页型 × EN/DE × 1440/390 = 56 个基础匿名状态**列覆盖账；这是为读者看清空白的计数，不代表全交互状态穷举，也不是新增产品范围。草稿/询盘仅指访客入口；有内容草稿、审批三态、登录后账号、发送后确认、Proforma 下载、表单校验与所有互动均未在本轮验收。

符号：`F` = 成功成对截图，但 raw pixel 非零，**未过像素门**；`—` = 没有本轮成功成对证据，**未完成，不推定产品失败**。

| 面 | EN 1440 | EN 390 | DE 1440 | DE 390 | 受影响的人 / 本轮说明 |
|---|:---:|:---:|:---:|:---:|---|
| home | F | — | — | — | 匿名访客；只有 EN 桌面静态图，详见 §4 |
| Solution draft / Lösungsentwurf（cart 入口） | — | — | — | — | 整理选型清单的访客；未测空/有内容状态 |
| 询盘 / Proforma 入口（checkout 历史名称） | — | — | — | — | 想询价的访客；**付款 checkout 已撤销，不恢复支付链** |
| account 登录页 | — | — | — | — | 注册/登录客户；账号现有功能/菜单保留，视觉同步归 accountsync |
| about | — | — | — | — | 公司信息访客；冻结营销文案，不改版 |
| contact | — | — | — | — | 联系团队的访客；未发信、未提交 |
| installer | — | — | — | — | 安装商；静态营销复刻未测 |
| services | — | — | — | — | 寻求服务的客户；静态营销复刻未测 |
| blog index | — | — | — | — | 文章读者；未测 |
| blog archive/category | — | — | — | — | 按分类浏览的读者；原脚本没有独立类别 archive 对，未冒充 blog index 已覆盖 |
| blog single | — | — | — | — | 单篇文章读者；未测 |
| search | — | — | — | — | 找产品/内容的访客；原计划 PV 查询不是已测结果 |
| 404 | — | — | — | — | 走无效链接的访客；未测 |
| compare | — | — | — | — | 比较型号的访客；未测空/有产品状态 |

**状态汇总：56 个基础状态 = 1 个成对捕获但像素 FAIL + 55 个未完成；PASS 0。**另有原脚本里的 EPC、FAQ/documents、solution、PDP、products spot checks，也都没有本轮成功成对成果，不纳入上述指定范围的分母。

## 3. 方法与数字的边界

原 `sources/capture-original.mjs` 对两侧使用同机同次 Chromium launch、独立匿名 context，视口 **1440×900**（移动计划 390×844，但未成功）；导航 URL 带 `cbq`。注入禁动画/transition/caret CSS，等待 `document.fonts.ready`，滚动触发 lazy loading 后回顶，再等待 image decode-or-error，最后 full-page PNG。原脚本对 load/networkidle timeout 使用 catch，**没有保存超时、每个失败图片、最终 scrollX/scrollY、browser version 的检查日志**。不能事后补写这些 measurement；完成 screenshot 证明执行走到了保存点，不等于每个资源成功加载的逐项凭证。

| 精确比较字段 | 数字 / 口径 |
|---|---|
| live PNG | 1440×8264 |
| t112 PNG | 1440×8264 |
| 总像素 | 11,900,160 |
| RGB 任一通道不同即不同 | **1,039,251 像素，8.733084261%** |
| 两图高度差 | **0 px** |
| 动态掩膜 | **未使用，0 区**；没有把图片、大区域或“不好解释”的内容掩掉 |
| 对齐/位移/缩放 | 原始比较没有；owner 全页预览仅缩小展示，数值一律来自原生 PNG |
| DOM scrollWidth / scrollHeight | 两侧 1440 / 8264；来自原计数文件 |
| DOM 计数差 | a 104→94、form 1→0、button 41→29、h2 11→10、h3 10→9、input 1→0；img 30→30、h1 1→1 |

这里的 8.73% 不是“结构缺失占比”，更不是可忽略噪音。页高相同不能消除图片像素/控件差异；也没有以 overlap 的小百分比、条带平移或 `0.015%` 报零差异。DOM 计数包含隐藏结构，**form 少 1 不足以证明 contact/询盘消失**。计数不是 DOM 元素边框 measurement；本次没有后者。

`analysis/raw-summary.json` 来自原 `freshdiff.py`（RGB threshold=0）；`analysis/regions.json` 的 region 是事后人工阅读区段，**不是掩膜、自动精确元素边界或批准差异区**。它们加总仍等于上述原始全页数字。

## 4. 首页差异账：只有工具更名可按批准范围解释，其他不洗成噪音

这些是该时点截图的可见差异/候选，不是对今日 main 根因的断言。**本页未见可据此确认的批准更名像素区域**；工具页允许重设计不豁免嵌入首页的静态营销块。旧功能移除不当 bug；但残留旧能力外观也不能靠截图宣称可用。

| ID / 归类 | 已存证据与触发 | 客户影响与解释边界 | 落点 / 不重复谁 |
|---|---|---|---|
| H-X / 页头交叉项 | y=21–66 有控件差异：live 右侧 icon/search、draft、account、EN/DE；t112 只显 Search + Contact。页头段 raw 2,111 像素 | 导航控制外观不同；本轮不测点击、不另开整页头 audit | 仅交叉 header 同步线；不得拿这张旧图否定在途修复 |
| H-1 / **未解释候选：营销图片像素** | hero y=136–1076：294,653；sourcing y=1450–2390：77,564；solutions y=2390–4470：262,630；project y=4470–5470：69,613；CTA y=6800–7740：332,677。原生 crop 见 `analysis/CMP_home-image-detail.png` | 实际同一区域 PNG 非零；肉眼版式和文案近似，不代表像素一致。图像压缩/srcset/解码/裁切是可能原因，**没有本轮资源/DOM measurement 证明具体原因**；不能称噪音或已批准工具更名 | 后续先核相关图片源/呈现与 snapshot assembly，仅有因果证据才归 assembly 或产品修复；不改冻结营销图片 |
| H-2 / **未解释候选：微小正文残差** | intro cards y=1076–1450 有 3 个精确差异像素（1112/1114/1116 行）；未设阈值抹去 | owner 像素门下仍不等于零；不知道原因，不能用“看不出来”过门。不是另一个已证业务 bug | 待局部解释；无需重扫整站 |
| H-3 / **未测能力：旧首页交互外壳** | 两张 PNG 均显示 nameplate photo / attachment / mic 外壳，计数却不同；本轮没有 click/网络证据 | 不把已撤销的独立旧工具移除列为缺实现，也不因可见旧按钮认定新功能存在。若仍是旧承诺/无效入口，须另作 scoped 验证；**当前只是未测** | 静态图片不替代交互验收；Genie 重设计不需对 live 工具内页像素一致 |
| H-4 / **未测范围问题：线上交易措辞** | 两图 CTA 都有 “Order online or quote a project.”，见 `analysis/CMP_home-cta.png` | 线上内容冻结与新“询盘后线下”范围之间的交叉线索；两图文字相同，不是复刻差异。本轮不改文案、不发明支付需求 | 按新业务边界判断链接承接，不复制付款流程；实际链接点击本轮未测 |
| H-Z / 本次局部零值，不是全页 PASS | testimonials y=5470–6800、footer y=7740–8264 均 raw 0 | 只证明这张图这些区段相等；不能扩为 EN/DE、390、其他页或交互通过 | 保留已有证据即可 |

H-1 的五处是**同一个未解释营销图片差异类别**，不是五个已确认独立缺陷。H-2 是小残差，H-X 是别线交叉项，H-3/H-4 是未测行为/范围线索。**没有已确认 assembly 故障、没有已确认新产品缺功能。**不能从没有安装内容的旧实例截图推出 repo 没实现。

## 5. Scoped code/assembly 已知事实（只读盘点，不补验收）

为避免“stand-in 未安装 = 产品缺实现”误报，接管时已有一次 t112 WP-CLI 只读查询：

- `linker-commerce`、`linker-i18n`、`linker-tools`、LiveCanvas、WindPress、Polylang、Woo 为 active；旧 core / AI plugin、Code Snippets、Stripe 为 inactive。这是 **t112 当时**状态，不是 live 或全树清除证明。
- t112 的三个新插件 symlink 指向本 worktree。LC 页面里已有 cart/account/checkout 动态模板（6565/6567/6566），compare EN/DE（6570/6571）、FAQ EN/DE（6572/6573），以及 snapshot 的 blog/search/404 模板。
- repo `plugins/linker-commerce/includes/Presentation/Templates.php` 的 `FILES` / `PAGES` 有这些内容注册；文件或 post 存在 **不证明正在渲染、匹配 repo 字节或通过 parity**。本轮没有把任何缺截图项叫 stand-in 故障或缺实现。
- `/checkout/` 等既有 URL 重定向不能当“页面缺失”；Proforma/询盘独立于付款 checkout，付款后续流程、legacyform 不恢复。`Presentation/LoginGate.php`、`Inquiry/Checkout.php`、`Shortcodes.php` 的历史实现仅用于明确 reader，不以旧机制/注释强推当前业务。
- 账号本线只看登录页覆盖，现功能/菜单保持；不移植 live 菜单替换现菜单，不碰 accountsync 文件。工具页重新设计有许可，不欠“对 live 工具内页像素一致”。

上述只读命令结果未保存完整输出工件，故不伪造新的 dump；本文记录可核摘要及限制。原始截图/DOM计数才是本 PR 可携带的实测证据。

## 6. 可预览与交回清单

- `DEBT-FRESH-OWNER.md`：一屏优先的 owner 表，不让业主圈修复顺序；工程债修复已授权，未完成覆盖不冒充验收。
- `captures/home-en-1440-{live,t112}.png`：原生全页 PNG，原文件不变。
- `captures/dom-counts.json`：唯一成功状态的 DOM 计数与实际 cbq URL。
- `analysis/CMP_home-en-1440.png`：两张原图生成的同尺度全页 LIVE | T112 对照预览，非重拍。
- `analysis/CMP_home-image-detail.png`、`CMP_home-cta.png`、`CMP_home-header-crossref.png`：由原图裁出的原生分辨率同位置对照。
- `analysis/home-en-1440-diff.png`：原生全页精确差异图（红=不同，灰=相同）。
- `analysis/raw-summary.json`、`regions.json`：精确数值；无掩膜、无平移。
- `sources/capture-original.mjs`、`freshdiff-original.py`、`capture-original.log`：失败线已有脚本与成功进度，**不声称已修、可无期限顺跑**。

后续只在有相关实现/assembly 变更时更新该面的证据；当前以这份明确不完整的成果交回，停止新采集与产品变更。**本轮像素门未通过、完整 Spec/Standards 与当前产品验收未完成；docs PR 的 CI 绿也不能改变这个结论。**

## 7. 续跑（同日，从检查点接着拍）

上一节是停止续拍时的交回。本节是之后按同一协议把 56 个状态拍完的记录。**不覆盖 §1–§6 的原图、原计数、原脚本。**不合并，不宣称整站通过。登录后账号、有内容草稿、表单提交、发送后确认、Proforma 下载、点击与其它交互仍未测。

### 7.1 续跑条件

| 项 | 实测 |
|---|---|
| worktree / HEAD | 续跑开始时 `40d5cb335e61917a2bebce26954298d20c67324f`，仍是 `research/debt-freshdiff` |
| 实例 | `t112` / `http://127.0.0.1:8978` 仍是 14:52 拉起的 PHP 进程；续跑前 `curl -sI` 首页 200。未 `just up`、未 reset、未重装 snapshot |
| 浏览器 | 树内 `plugins/linker-tools` 的 Playwright，`channel: 'chromium'`，启动读到 `156.0.8078.4`。两侧同一 launch、独立匿名 context |
| 协议 | 视口 1440×900 / 390×844，URL 带 `cbq`，注入禁动画 CSS，`document.fonts.ready`，滚动触发 lazy，再等图片，全页 PNG。无掩膜、无平移 |
| 原证据 | `docs/debt/captures/home-en-1440-*.png` SHA-256 仍是 `fcabfefb55d87ccf…` / `b6fa300fc203bb39…`，文件时间仍是 15:08。`--resume` 跳过已有成对 PNG |
| 脚本窄修 | 原 `capture.mjs:107-113` 在 `complete && naturalWidth===0` 时只挂未来的 load/error，事件已发生则永不返回。续跑脚本改为：已 `complete` 的图直接 decode-or-resolve，并加 15 秒上限。只改这一处等待，外加 `--resume` 与补全的 URL 表。副本：`sources/capture-resume.mjs`。原 `sources/capture-original.mjs` 未改 |

冒烟：修完后单独跑 `home-en-390`，两侧都写出 PNG（live/t112 均为 390×8827），进程以 `done` 退出。这证明死等已解开，不证明像素通过。

### 7.2 56 状态账本

符号：`FAIL` = 本轮真实跑过，未过像素门。`PASS` 要求原始差异像素 = 0 且页高差 = 0。**PASS = 0。**数字来自 `python3 freshdiff.py`（threshold 0，无掩膜），摘要在 `analysis/resume-summary.json`；DOM 与最终 URL 在 `captures/dom-counts-resume.json`。15:08 的 `captures/dom-counts.json` 仍只含首页 EN 1440。

| 面 | EN 1440 | EN 390 | DE 1440 | DE 390 |
|---|---|---|---|---|
| home | FAIL 1,039,251 / 8.73% / Δh 0 | FAIL 250,156 / 7.27% / Δh 0 | FAIL 空壳 | FAIL 空壳 |
| Solution draft（`/cart/`） | FAIL 890,752 / 64.77% / Δh −232 | FAIL 302,445 / 71.47% / Δh −296 | FAIL 空壳 | FAIL 空壳 |
| 询盘入口（`/proforma-request/`） | FAIL 971,154 / 63.38% / Δh +78 | FAIL 366,166 / 84.58% / Δh +178 | FAIL 空壳 | FAIL 空壳 |
| account 登录页 | FAIL 1,384,657 / 65.41% / Δh +243 | FAIL 405,286 / 68.10% / Δh +632 | FAIL 空壳 | FAIL 空壳 |
| about | FAIL 847,364 / 6.38% / Δh 0 | FAIL 176,011 / 4.28% / Δh 0 | FAIL 空壳 | FAIL 空壳 |
| contact | FAIL 3,834,460 / 84.45% / Δh −371 | FAIL 568,872 / 79.49% / Δh −508 | FAIL 空壳 | FAIL 空壳 |
| installer | FAIL 846,797 / 6.29% / Δh 0 | FAIL 207,326 / 5.14% / Δh 0 | FAIL 空壳 | FAIL 空壳 |
| services | FAIL 4,530,082 / 42.15% / Δh +14 | FAIL 2,507,621 / 66.67% / Δh +223 | FAIL 空壳 | FAIL 空壳 |
| blog index | FAIL 244,567 / 2.82% / Δh 0 | FAIL 180,877 / 4.24% / Δh 0 | FAIL 重定向 | FAIL 重定向 |
| blog archive（`/category/system-design/`） | FAIL 142,184 / 3.55% / Δh 0 | FAIL 26,526 / 1.85% / Δh 0 | FAIL 重定向 | FAIL 重定向 |
| blog single | FAIL 2,158,743 / 35.47% / Δh −175 | FAIL 911,790 / 38.69% / Δh −267 | FAIL 空壳 | FAIL 空壳 |
| search（`?s=PV`） | FAIL 2,962,800 / 59.69% / Δh +657 | FAIL 1,403,752 / 60.01% / Δh +1,671 | FAIL 空壳 | FAIL 空壳 |
| 404 | FAIL 408,088 / 10.01% / Δh 0 | FAIL 316,286 / 17.66% / Δh 0 | FAIL 空壳 | FAIL 空壳 |
| compare | FAIL 1,359,146 / 89.46% / Δh −59 | FAIL 412,950 / 88.68% / Δh −33 | FAIL 空壳 | FAIL 空壳 |

**56 = 28 个英文成对 FAIL + 24 个德语空壳 FAIL + 4 个德语重定向 FAIL。PASS 0。**

德语 URL 用的是线上 hreflang，不是猜的 slug：`/de/warenkorb/`、`/de/proforma-anfrage/`、`/de/mein-konto/`、`/de/ueber-uns/`、`/de/kontakt/`、`/de/fuer-installateur/`、`/de/service-support/`、`/de/blog/`、`/de/category/system-design/`、`/de/hybridwechselrichter-vs-ac-speicher/`、`/de/?s=PV`、`/de/audit-404-20261012/`、`/de/compare-products/`。

t112 只读核验（WP-CLI，未写）：`language` 词项 `en` count=161、`de` count=0；`pll_get_post_translations` 对 home/cart/about/contact/blog 等只有 `en`。所以：

- **空壳**：t112 停在所请求的 `/de/…`，但渲染的是 “Sorry, no posts matched your criteria.”（首页滚动高 66/90，其余多为 185，search 为 42）。这是实例没有德语内容，不是采集超时。
- **重定向**：`/de/blog/` 与 `/de/category/system-design/` 被 Polylang 301 到英文 `/blog/`、`/category/system-design/`（最终 URL 记在 `dom-counts-resume.json`）。英文页不能冒充德语对，记 FAIL。

登录态、空/有内容草稿、表单校验、提交后确认、Proforma 下载、点击，本轮都没有跑。不把访客静态页的 FAIL 说成这些状态的结论。

原脚本里的 EPC、FAQ、solution、PDP、products 也拍了，同样不是像素 PASS（例如 `faqdl-en-1440` 页高 5167→28287）。它们不在 56 的分母里。

### 7.3 首页 EN 1440 营销图归因

§4 的 H-1 当时没有资源测量。续跑补了测量，对象仍是 15:08 那一对原图，没有重拍。

| 测量 | 结果 |
|---|---|
| 30 个 `<img>` 的文件名 | 两侧一一相同（`de-linker-logo-1.webp`、`linker-one-stand-for-solar-and-storage.webp` 等） |
| 抽查 6 个 WebP 的字节 | SHA-256 相同。例：`linker-one-stand-for-solar-and-storage.webp` 两侧都是 `4f57199e043aec96…`，197,622 字节，`WEBPVP8`，1280×720 |
| 同一次 Chromium 里的绘制框 | 30/30 的 `getBoundingClientRect` 相同；`devicePixelRatio` 两侧都是 1；UA 都是 HeadlessChrome/156 |
| 浏览器 canvas 像素 | 同一 WebP，live URL 与 t112 URL 的 `getImageData` 差异为 0 |
| Pillow 解码 | 两个本地副本差异为 0 |
| 全页 PNG 幅度 | 1,039,251 中 **994,967（95.7%）通道差正好是 1**；`mag>=10` 只有 1,846，其中 1,663 在 y=21–66 |

结论：营销图区的成片差异**不是换文件、不是 srcset 选了另一张、不是裁切框不同、不是解码像素不同**。canvas 与截图像素不一致，且同一 URL 连拍两次截图可以相同、换 host 就出 1 级差——差在 Chromium 把页面合成进 PNG 的那一步，不在图文件。未改浏览器、未重建环境；这个合成差修不掉，也不把它掩掉。1 级差仍然算 FAIL。

结构差（`mag>=10`）另计，不混进营销图：

- **页头 y=21–66，1,663 px。**线上 `header-portal.js`（`terravolt-b2b-core` 0.12.413）在 `.tv-desktop-actions` 里插入 cart 与 account，并画出 EN/DE。t112 该插件 inactive，槽里只有 LC 模板的 Search 链接，文字 “Search” 可见，所以是一颗宽按钮而不是 46px 图标。这是控件缺失，不是图片压缩。390 页头同样少 EN/DE（y=17–62）。
- **首页 DOM。**h2 少的是 “Linker Advisor”；h3 少的是 “Get help with your solar project”；form 少的是 `lia-form`；button 41→29 含线上后注入的 “Sign in”。与 15:08 计数一致，现在对得上节点，不再只是数字。
- **390 的 y=774–823。**`#testimonials.is-stor-carousel` 的 inline 脚本用 `setInterval` 每 4 秒换帧，只在 `prefers-reduced-motion: reduce` 时停止。注入 `animation: none` 停不了它。两侧停在不同帧。这是协议没盖住的动态区，不是已批准的掩膜；像素仍算 FAIL。
- **404 同高但仍有 10.01%。**卡片盒 `getBoundingClientRect` 两侧相同（x=130/531/931）。错位感来自 WebP 合成进 PNG 的同一类差，不是 DOM 位移已证。

同高英文页里，`mag==1` 占原始差异的 88.5%–98.5%（about/installer/blog 与 home 同类）。页头带在这些页上重复出现。页高不同的英文页（cart、询盘入口、account、contact、services、blog single、search、compare）是版面差，不是 1 级合成差能解释的；本轮没有逐页改产品。

### 7.4 仍未做

- 未登录、未提交、未发信、未下 Proforma。
- 未重建 t112，未补德语内容。德语 28 态因此停在空壳/重定向，不继续造页面。
- 未把 1 级合成差修进浏览器或加掩膜。
- 全页 diff PNG 留在工作区 `.scratch/debt-freshdiff/analysis-resume/`（约 6.5MB 可视化），不进本 PR；原图在 `.scratch/debt-freshdiff/captures/`（约 148MB），同样不进 PR。可复核的数字是 `analysis/resume-summary.json` 与 `captures/dom-counts-resume.json`。
