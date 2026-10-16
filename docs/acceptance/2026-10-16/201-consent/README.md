# #201 同意横幅与 GA4 · 验收记录（2026-10-16）

分支 `t201/consent-ga4`；实例 `t201`（http://127.0.0.1:9051，快照 + 本分支插件软链）；
规格 `docs/specs/201-consent-ga4.md`；载体实测 `docs/research/2026-10-16/consent-ga4-carrier.md`；
文案对抗评审 `docs/acceptance/2026-10-16/201-consent/copy-review.md`。

**本记录的边界（先说没做的）**：线上部署、营销侧操作者的文案签字、以及"`just cutover verify` 对线上绿"
里的线上部分都**未执行**——业主侧的 Site Kit Analytics 连接尚未发生（见 §5 与 §6），而票面要求客户可见
文案先过操作者审稿再上线上（AGENTS §5）。本记录覆盖的是**仓库交付物 + 本地实例的全部实测与回归**。

## 1. 交付物清单

| 面 | 落点 | 是什么 |
|---|---|---|
| 规格 | `docs/specs/201-consent-ga4.md` | 载体、机制、穷尽证明、检查、所有者侧的单一说明 |
| 载体实测 | `docs/research/2026-10-16/consent-ga4-carrier.md` | 票面五项实测逐条 + 来源（含两处推翻票面前提的实测） |
| 仓库代码（唯一） | `plugins/linker-commerce/includes/Consent/Blocking.php` | 3 个 filter + 1 段 cookie 清理；零设计决策（穷尽证明见规格） |
| 回归夹具 | `plugins/linker-commerce/tests/php/Unit/Consent/BlockingTest.php`、`Unit/PluginTest.php`（4 条新期望） | 被改层的真实夹具测试 |
| 页脚入口 | `content/livecanvas/partials/footer.html`、`partials/de/footer.html` | LC partial 的按钮 + 一条样式（`present` 安装，与所有 partial 同通道） |
| 配置与文案（数据） | `tools/migrate/201-consent.py`、`tools/migrate/201-consent.json` | Complianz 设置/横幅行/DE 字符串/隐私政策两节的迁移（plan/apply/verify，幂等） |
| 迁移测试 | `tools/migrate/tests/test_201_consent_privacy.py` | 三次编辑落一次、二次跑为 no-op、漂移页面被拒 |
| e2e | `tests/e2e/specs/consent.spec.ts`（+ README 的 SKIP_SERVICES 声明、spec 16 的清单行） | 评审站回归：首层、扣住、放行、撤回 |
| 切换回归 | `tools/cutover`（`plan.CONSENT_STEP` 等 + `steps.consent` + `plan.MIGRATIONS` 里的 `201-consent.py` + CLI 接线 + 13 条测试） | 线上每次写之后的 `consent` 段 |
| 文案 | `copy-review.md` | 逐条 初稿 → 评审意见 → 定稿；两条被实测推翻的说法（§0） |
| 证据 | `evidence/`、`shots/` | 探针原始记录 + 横幅各状态截图 |

## 2. 票面五项实测（逐条，证据在 `evidence/`）

| 项 | 结论 | 证据 |
|---|---|---|
| 1. Complianz 能否挡住 Site Kit 已入队的 `gtag.js` | **不能**（白名单先于阻断规则命中）。挡前：`gtag.js` 已加载并发出采集请求（`gcs=G100`，点任何按钮之前）；接线后：零 Google 请求、脚本 `type="text/plain"` | `m1-baseline-complianz-default.json` vs `m2-deny-blocking.json` |
| 2. 放行后 consent update 是否生效 | **生效**：接受后请求的 `gcs=G101`（`analytics_storage` 位翻转），`ad_*` 信号从不出现 | `m1-accept-blocking.json` |
| 3. 缓存/合并 JS 是否打乱顺序 | **不会**：线上无页面缓存插件、无任何缓存响应头、重复抓取逐字节相同；线上同插件表未有合并类插件 | 研究文档 §实测 3（含一条不可复现观察的声明） |
| 4. Site Kit 的 Tag Gateway 默认开关 | **默认关**（`isEnabled=false`），选项在本地与线上都不存在；标签按标准 `googletagmanager.com` 打印（就是被扣住的那条） | 研究文档 §实测 4；`consent` 段把它当断言 |
| 5. Complianz 免费版能否经 Polylang 存 EN/DE 两套横幅 | **能**：同一横幅行 + Polylang 字符串；`/` 出英文、`/de/` 出德文（截图） | `shots/banner-{en,de}-{1440,390}-{first,purposes}.png` |

探针：`evidence/consent-probe.mjs`（放行 CSP 让真标签加载，每条到 Google 的采集请求被拦截记录、不发出）。

## 3. 回归

| 跑什么 | 命令 | 结果 |
|---|---|---|
| 插件单元测试 | `plugins/linker-commerce` 的 PHPUnit `--testsuite unit` | **1021 passed**（含 `Consent\BlockingTest` 7 条、`PluginTest` 的 4 条新期望） |
| 迁移测试 | `tools/migrate` 的 pytest | **100 passed, 8 skipped** |
| 切换工具 | `tools/cutover` 的 pytest / ruff / mypy | **91 passed**；ruff、mypy 干净 |
| 评审站 e2e | `LINKER_E2E_SKIP_SERVICES=1 just e2e t201 specs/consent.spec.ts` | **5 passed**（EN/DE × 首层+放行，EN 撤回链） |
| 迁移幂等 | `201-consent.py plan` 二次 | 四处 `nothing to do` |
| 迁移读回 | `201-consent.py --base http://127.0.0.1:9051 verify` | `ok`（含渲染面：横幅、页脚入口、两个首层按钮） |
| 切换 `consent` 段（对本地实例直调 `steps.consent`） | 见 §4 末 | `ok`（线上跑法：`just cutover verify`，目标为生产时才含此段） |

e2e 的 `LINKER_E2E_SKIP_SERVICES=1` 是本仓已声明的例外（只渲染 WordPress、不碰 engine/Genie 的页面 spec）；
本票把它扩为两个 spec 并在 `tests/e2e/README.md` 与 `docs/specs/16-review-acceptance.md` 写明。

## 4. 视觉验收

### 4.1 横幅各状态（裁定过的变更，票据要求）

`shots/banner-en-1440-first.png`、`banner-en-1440-purposes.png`、`banner-en-390-first.png`、
`banner-en-390-purposes.png` 与四张 `de` 对应件（共 8 张，1440×900 与 390×844@2x，EN/DE，
首层与"选择目的"展开态），外加 `banner-{en,de}-1440-descriptions.png`（两个目的说明展开——
两条保存期的定稿句子在那里可见）。读数：

- 首层：`Accept all` / `Reject all` 两个实心同色按钮 + 白底 `Choose purposes`（EN）；
  `Alle akzeptieren` / `Alle ablehnen` + `Zwecke auswählen`（DE）——同权重、同尺寸。
- 展开态：`Notwendig`（Immer aktiv）/ `Statistik`（关）/ `Marketing`（关）；`Preferences` 行不出现
  （`category_prefs.show = 0`）。
- 底部文档链接：EN `Privacy Policy` / `Imprint`，DE `Datenschutzerklärung` / `Impressum`（Polylang 页面映射）。

### 4.2 "横幅关闭后其余像素 0 差异"——本机实测与归属

**镜头噪声下限 = 0 像素**：同状态同条件连拍两次，逐字节相同（`/tmp` 记录，imprint-en-390，5936×780）。

**改动前 vs 改动后**（`.scratch/t201/` 的 36 面 × 严格逐像素比较，阈值 0）：差异**只**落在三类区域，
逐面可观：

| 面 | 差异区域 | 归属 |
|---|---|---|
| 全部 36 面 | 横幅所在区域（1440 下 x≈787–1439、390 下几乎全宽；全页截图里固定元素重复出现） | 裁定过的变更（横幅） |
| 全部 36 面 | 页脚 `Legal` 行（y≈5819–5837 @390；y≈8188+ @1440） | 裁定过的变更（页脚入口） |
| `privacy-{en,de}-{1440,390}` | 页面高度变化（EN 4412→4721、DE 5232→5537 @1440）与新增行/句 | 裁定过的变更（隐私政策两节） |
| `imprint-{en,de}-390` | 两处小区域（31px 与 15px 高，1–3px 的文本位移："On this page" 与一处列表项） | **页脚入口的连带布局位移**——把页脚 partial 回滚（`linker-commerce rollback`）后这两处消失、只剩页脚行；即由裁定过的变更引起，非无关改动 |

即：36 面上没有一处差异来自本票之外。**未做的**：live|local 的 36 面全量像素扫（票面口径）。
抽样 6 面（home EN/DE × 1440/390、隐私 EN/DE × 1440）的 live vs local 实测显示：本地实例的快照
**落后线上内容**——首页在 y≈5817–6707（1440）等区域存在与本题无关的既有差异（本地快照更旧），
隐私页高度也因内容差而不同。这一项必须在**新快照的评审实例**上重跑（`just pull load` 流程），
否则测的是快照陈旧度而不是本票的改动。此发现按事实记录，不当作本票缺陷，也不当作已通过。

### 4.3 切换 `consent` 段对本地实例的实跑

`steps.consent(local_target('t201'))` → `ok`，actions 含：三插件 active、`cmplz_options` 三项、
横幅三处文案非空、`googlesitekit_analytics-4_settings[measurementID]=G-T201LOCAL0`、
`googlesitekit_consent_mode[enabled]=True`、`google_tag_gateway[isEnabled]=None`、
`/` 与 `/de/` 各 200 且 `tag held=True executable gtag script=no`。

## 5. 所有者侧（未做，阻塞线上三条证据）

线上 2026-10-16 读回（只读）：`googlesitekit_analytics-4_settings` 是空对象（`measurementID` 空）、
无 `googlesitekit_active_modules`、`googlesitekit_consent_mode.enabled = false`。**Analytics 未连接**，
因此线上现在一行 Google 标签都不打印——`consent` 段的 Analytics 断言会红，这是设计使然。
业主/营销侧需要：建 GA4 媒体资源（Europe/Berlin、EUR、网站数据流）并在 Site Kit 里连 Analytics。
连上之后，本地实测证明的那条链路（Basic：同意前零请求）在线上同样成立（同一份插件与选项）。

## 6. 票面 6 条验收 · 逐条状态

| # | 票面验收 | 状态 | 依据 |
|---|---|---|---|
| 1 | 五项实测逐条有证据（本地/评审站） | **完成** | §2 + `evidence/` + 研究文档 |
| 2 | 横幅、页脚入口、隐私政策 EN/DE 文案：对抗评审记录 + 营销侧操作者审稿"可以了" | **前半完成，签字未做** | `copy-review.md`（EN 先行、DE 独立、两条实测纠错）；操作者审稿属 PR 交付后的人工步骤 |
| 3 | 视觉验收 1440/390 × EN/DE：横幅各状态截图；横幅关闭后其余像素 0 差异 | **前半完成，后半部分完成并声明边界** | §4.1 八张截图；§4.2 的 36 面改动前后严格比较（差异全部归属裁定变更，噪声下限 0）；live\|local 全量扫需新快照实例，抽样已指出快照陈旧，未冒充通过 |
| 4 | `just check` / `just test` 绿，CI 绿；`just cutover verify` 对线上绿（含新 `consent` 段与原 `search-console` 段） | **本地部分完成；线上未跑** | §3 分项全绿；`consent` 段在本地实例实跑 `ok`。线上那一次要等业主连 Analytics + 部署窗口（§5） |
| 5 | 线上三条证据：拒绝前无 GA4 请求、无 `sbjs_*`；接受后 GA4 实时报告可见；撤回可用 | **未做** | 需要线上部署 + Analytics 连接（§5）。同三条在本地已逐条实测（§2 项 1/2 + `m1-accept-blocking.json` 的撤回阶段零请求） |
| 6 | 验收记录 `docs/acceptance/<date>/<本票>/README.md` | **完成** | 本文件 |

## 7. 本轮发现、按实测定稿的修正（不硬实现错误前提）

1. **票面把"Complianz 挡不挡 gtag.js"当待测项**：实测是确定行为（白名单先于阻断规则命中），
   因此仓库插件的最小后备是**必需项**，不是"若实测 1 不成立"的可选分支。已写进规格。
2. **票面把"打开 Site Kit 的 Consent Mode"当作单一开关**：实测 defaults 分段打印（欧洲区列表内才
   denied，列表外全部视为 granted），且横幅对每个访客都显示（免费版无地理法域开关）——只打开开关
   不够，`deny_everywhere` 是缺口的补丁。写进研究文档 §实测 4 与规格的变更记录。
3. **文案两处被实测推翻**：`_ga` 保存期实测 400 天（初稿写"最多两年"）、`sbjs_session` 实测 30 分钟
   （初稿写"关闭浏览器即结束"对所有 `sbjs_*` 不成立）。已改并记录在 `copy-review.md` §0。
4. **线上 EN/DE 术语分叉**：线上 DE 隐私政策写 `Lösungsentwurf`，EN 同句仍写 "cart"（AGENTS §3 的禁词）。
   本票改写的正是那一句，因此 EN 一并改为 "solution draft"。属必要后果，记录在 §5 文案评审。
5. **线上 DE 隐私政策的退役工具名**：第 4 节表 caption 仍写 "Linker Berater"（12-site-chrome 的改名
   漏网 5 处之一）。本票改写的正是那句（要加 Google 的计量目的），因此同时改为 `Genie`（AGENTS §1）。
   其余 4 处**不在本票范围**，未动——登记在此供后续票处理。
6. **本地实例快照落后线上**：§4.2 已述。评审实例应按 `tests/e2e/README.md` 重新装快照后再做全量像素扫。
7. **Complianz 会回填隐藏类目的说明文字**：`preferences_text` 置空后，插件在 `save()` 里用它的默认值
   回填（实测），因此迁移不写该字段（该类目 `show=0`，访客看不到）。
