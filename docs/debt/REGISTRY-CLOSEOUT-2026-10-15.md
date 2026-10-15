# 登记册清零（2026-10-15）

登记册 `docs/debt/REGISTRY-2026-10-12.md` 的 54 条逐条终态。每条只有三种终态：**closed**（证据闭合）、
**delegated**（指针给出，负责人明确）、**dormant**（裁定依据明确，等待外部事实）。没有 open question。

## 基线与本轮核实方式

- 冻结观察点：登记册 `b6bc084`；清零观察点：main **`2f5fdc3`**（两者之间 303 个提交）。
- 关键事实变更（推翻登记册时点的现状描述）：
  1. **#17 已执行**：issue #17 `closedAt 2026-10-14T06:04:09Z`；执行记录
     `docs/acceptance/2026-10-14/17/README.md`（含预检 6 项工具缺口、窗口 ⑩ 段、回滚预案、深度审计、
     线上 vs 仓库 12 文件对账）。"暂停"状态被业主 2026-10-14 令（欠账清零后直接推进）取代。线上现为新树：
     `curl https://de-linker.com/products/` 含 `wp-content/plugins/linker-commerce/` 与 `sf-products` 标记
     （本轮实测 200）。
  2. **像素债定性台账** `docs/debt/ADJUDICATION-2026-10-14.md`（253 行四类定性 + 线上复核轮 25 族：
     reproduced 11 / fixed 11 / partial 5 / needs-owner 1→已按 Q5a 收口归零）。
  3. **清账决策** `.scratch/closure-decisions-2026-10-15.md`（21 项，主会话）。
  4. **修复泳道已并 main**：recheck 系 #147–#161（contact-form、commerce-empty、blog-relations、search-scope、
     header-thumbs、catalog、shortcode、fixnote-corrections）、closure 系 #163 twins-fill-only、#164 nits、
     #166 blog-template、#167 coverage。
- 本轮（本分支）做的核实：curl 线上 5+ 页（A2 与部署态）；GitHub issue/PR 终态；main 工件存在性
  （E1–E8 逐文件）；`tools/checks/i18n-coverage.py`；msgfmt 校验；linker-commerce PHPUnit 全套
  **1010 tests / 4799 assertions / 54 skipped，OK**（本轮实测）。
- 本轮做的代码修正：C16 的 6 条 fuzzy + 1 条错译（见 §3）；C3/C6 的注释用词残留（见 §3）。

## 1. 逐条终态表（54 条）

| ID | 标题 | 终态 | 证据 | 指针 |
|---|---|---|---|---|
| A1 | 页头与线上差异 | closed | Q5a 收口（ADJUDICATION 族 24 收口段，`docs/acceptance/2026-10-12/header-live-sync/ACCEPTANCE.md:5`）：五点位重量后两非差异（激活色、字重），三属重建件内部视觉微调（下划线几何、分隔线、390 位移）判 intentional；切换后线上页头即新树形态（cutover ⑦-4 present+WindPress 编译）。 | 无；若业主日后要求与旧线上逐像素对齐，一条独立小修回改 |
| A2 | 页头/页脚 `[linker_contact_link]` 两侧行为 | closed | 本轮 curl 实测：live 首页/imprint/privacy/impressum/datenschutz 五页 `linker_contact_link` 字面量计数 **0**；live 渲染 `<a class="tv-header-cta"…>Contact Linker</a>`、`tv-header-cta tv-mobile-cta`、`<a class="footer-contact-link"…>` 三处（与新树 shortcode 输出同形）。代码：`Shortcodes.php:39,71-111`；placement 三处 `partials/header.html:199,281` + `partials/footer.html`（de 孪生同）；单测 `ShortcodesTest.php:617-671+`。补拍包同结论：`docs/acceptance/2026-10-15/coverage/README.md` §3 H·A2（两侧均渲染设计化链接、shortcodes 探针空数组）。 | 无 |
| A3 | 复刻像素门缺可复核终局包 | delegated | 已建立并已可重跑：`docs/acceptance/2026-10-15/coverage/README.md` §3 H·A3（PDP 四对 local/live + `h-pairs-metrics.json`；结构差主因=实例侧缺「Inverter side」规格组，已恢复+复拍；残余=FAQ 带 2,132px + 页尾 188px 位移）；过门结论仍须业主掩膜/允许差异裁定。**PDP 面作废：#174 业主裁定 2026-10-15**（PDP 验收基准改为该票验收过的原型变体 A，见 `docs/specs/174-pdp.md` §变更台账条目），本条只余 PDP 之外的复刻面。**部署后终局包清单见 §2**，由主会话执行并回填。 | 本文件 §2；`docs/acceptance/2026-10-15/coverage/README.md` §3 H·A3、§6-4；`docs/specs/174-pdp.md` |
| A4 | 列表页 390 终局像素门判定 | closed | 四个默认态 390 面 local vs live **差异像素 = 0（0.0000%）**、页高逐格相等（12252/12590/12270/12619）：`coverage/README.md` §3 H·A4 + `h-pairs-metrics.json`。 | 无 |
| A6 | 条带对齐 vs 全页像素门口径 | closed | 两口径逐项呈报（9 面）：5 面两口径同为 0；PDP 四面最优位移=0、两口径数值相同：`coverage/README.md` §3 H·A6 表。与 A3 同根不相加。 | 无 |
| B1 | Genie/配置器三屏可重设计 | closed（记录） | 裁定 8（工具页免像素门+已重设计）：Genie PR #123/#139、配置器 PR #126/#122/#121 + configurator-mobile 已并。 | 无 |
| B2 | PDP P1–P4 技术数据/兼容卡/FAQ/390 参数条改良 | closed（记录） | 已批准并落地 `f7f10bc`；第 6 条裁定（PR #129 PDP 样式卷重写）。 | 无 |
| B3 | 移动动作条两 chip 不做 | closed（记录） | 第 2 条裁定；业主 2026-10-13 再确认「不补齐」（`docs/specs/13-genie.md` C 节）；#154 已把误加的芯片删回。 | 无 |
| B4 | rail-help 因批准工具名换行变高 | closed（记录） | 第 2 条裁定（文案/更名结果，~20.1px）。 | 无 |
| B5 | 缩略图 srcset 钉 src 声明偏差 | closed（记录） | 第 2 条裁定时代既定处理；`replica-r4/EVIDENCE.md` §3-③/§6-⑥。 | 无 |
| B6 | 相位计数不沿用旧误判算法 | closed（记录） | bug 修复差异（第 2 条台账追加）；产品事实另经 C15 逐台核对（C15 行）。 | 无 |
| B7 | PDP Genie 浮动入口可见性 | closed（记录） | Genie 坞 C1/C2（2026-10-12）+ 裁定 8；不豁免 #113 F1（C2 行已修）。 | 无 |
| B8 | DE PDP overview 既定措辞多一行 | closed（记录） | PR #62 台账 4 的批准措辞/排版差异。 | 无 |
| B9 | funnel/release-state/AI weekly report/独立媒体上传不恢复 | closed（记录） | `docs/audit/2026-10-11-surface-inventory.md` GAP-10/12/13。 | 无 |
| B10 | 独立 bulk order/CSV 与 vision 铭牌入口不做 | closed（记录） | GAP-11/14 业主终裁；与 #82 同列。 | 无 |
| B11 | 命名净化范围外保留项 | closed（记录） | 保留 `tv-*` DOM id、`--dlk-radius`、REST namespace 与凭据目录名。 | 无 |
| B12 | design-canvas/quote-configurator 旧地址 301 | closed（记录） | `linker-tools/data/legacy-redirects.json` retired_tools 5 条；cutover ⑦ 抽验 `/design-canvas/` 301。 | 无 |
| B13 | 无托管依据 FAQ 撤下、部分产品列表为空 | closed（记录） | `docs/faq/summary.md`：221 通过、51 撤下；裁定 7（#15 逐产品重写 + #66 文档库化）。 | 无 |
| B14 | `data-faq-count` 内部计数器不复刻 | closed（记录） | replication-spec §6-6。 | 无 |
| B15 | DE 对比页德语孪生产品 id | closed（记录） | replication-spec §6-7 + 裁定 8（#66 重建）。 | 无 |
| C1 | #17 一次性切换 | closed | issue #17 `closedAt 2026-10-14T06:04:09Z`；`docs/acceptance/2026-10-14/17/README.md` 全文（预检、窗口⑩段、回滚两层、深度审计、线上-仓库 12 文件对账 9 同 3 注释级已同步）。 | 无 |
| C2 | #16 交回项 + #113 入口必改 | closed | ①#113 F1 已修：`Genie/Entries.php:129` PDP Ask 按钮自身携带 `data-linker-genie-open`，首次点击即 boot；e2e `genie-dock.spec.ts:36`「never mask failure with a second click」、R13 芯片问、R7 登录问覆盖。②#16 issue CLOSED；e2e 套件 #96 已并且 `final-merged/README.md` 记 `just e2e t110` 68 passed。③hreflang 实现：`linker-i18n/includes/Seo.php`（`pll_rel_hreflang_attributes` 过滤 + 404 规则）；cutover ⑩ 德语 149 URL 全 200+lang=de 实测。④R1/R2 真机三轮修复记录在 17 README ⑧（含 LiteSpeed 编码斜杠、证书钉扎、双渲染三缺陷修复）。 | 无 |
| C3 | #82 域语言净化执行段 | closed | 88b1c70「Rename Catalog classes and selectors to Products」：`catalogue.css→products.css`、`catalogue-mounts.css→products-mounts.css`、`CatalogText→ProductText`、`CatalogShortcodes` 族清出；issue #82 CLOSED。本轮补清注释用词残留（§3）。 | 无 |
| C4 | #98 embedding 实测尾项 | closed | issue #98 CLOSED；通道实现 `includes/Abilities/QueryEmbedding.php` 在 main；#17 已执行，服务链上线（cutover ⑧ R1/R2 真机真答案；`/opt/linker-engine`、`/opt/linker-genie` 版本化发布+烟测 200）。 | 无 |
| C5 | #69 ERP 真实接入 | dormant | issue #69 CLOSED（通道+本地模拟已建，`includes/Stock/` + `tools/mock_erp.py`）；真实 ERP 接入细节仍待业主/外部提供（AGENTS.md §2 库存裁定：真实 ERP 存在、之后接入）。 | 等待 ERP 接入事实 |
| C6 | 商城样式 fresh authoring | closed | #129（`docs/audit/2026-10-13-storefront-fresh-author.md`：旧出处串 `terravolt-b2b-core`/`0.12.413` 清出、注释按卷职责重写、声明保持、t110 编译+三页承载验证）；`coverage/README.md` §3 H·C6（`git ls-files | grep -c catalogue\.css`=0、出处串零命中）；本轮把注释里的 catalogue 用词清掉（§3）。视觉差异由分类/商城面族行承载，A4 已给 390 四默认面 0px。 | 无 |
| C7 | 全拆审计修后记录 | closed | 修后记录即 `docs/audit/2026-10-13-storefront-fresh-author.md`（含可重跑命令清单：卷复制→md5→编译→三页 curl→缓存选择器计数）；teardown-audit 的违规宿主 `assets/storefront.css` 已随 #62 删除。 | 无 |
| C8 | 本地快照特色图 | closed | `16/INDEX.md` §9：`_thumbnail_id` 546 行、212 个已发布商品全有、缺行 0；ADJUDICATION 族 25 销账（compare ids 表两图在、img 16=空态 14+2）；cutover ⑦-3 线上被清 273 组已写回（restored=273 skipped=0，Polylang 同步补孪生至 546）。 | 无 |
| C9 | #18 旧仓库归档与文档收口 | closed | issue #18 CLOSED；文档部分随 PR #103 并；归档动作随 #17 执行记录内的「深度审计（旧仓回溯）」完成；旧 repo/worktree 未删除的卫生项见 C14。 | 无 |
| C10 | 账户视觉同步（Q6） | closed | 被 2026-10-13 裁定 3 取代：账号区改仪表盘风（`Merge lane/account-dashboard: independent review passed`），视觉差异转有意变更（ADJUDICATION 族 6 四行 + 族 13 C10 行）；功能/菜单保持（Q6）。B 段 9 行登录后账号面已在 coverage 包 captured+功能核验。 | 无 |
| C11 | #3 重建地图伞票 | delegated | issue #3 仍 OPEN（伞票本就不应因工件并入而自动关）；子项 #66–#98 已全 CLOSED、#17 CLOSED。伞票随残余子项收口。 | issue #3 自身 |
| C12 | 检索/索引评估留档口径 | closed | `16/INDEX.md` §6 已载「本 ask 未重跑」注释 + `16i/systemone-probe-20261011.json` 在；口径判断（只在结果改变交付判断时做针对性评估）成立——切换已过，线上 Genie 以真机真答案验证（cutover ⑧），不需要为交付判断重跑 11 轮一致率。 | 无 |
| C13 | visual-round2 提案/实施交付尾项 | closed | #109/#110 已并（2026-10-12，含自测测量）；#112 CLOSED 作废；#113 已并且其 F1 缺陷在 C2 修复；E1 业主明言否决（保持两列 2+1）。#109/#110 的独立 Spec/Standards 评审无独立记录，但其承载面已在后续评审轮覆盖：recheck 泳道对 catalog 组成做过 review round（#154 各提交含 review 修正）、A4 四默认 390 面 0px、e2e 68 passed（`final-merged/README.md`）。 | 无 |
| C14 | 分支/worktree 清理线索 | closed（记录） | 非客户债；`git worktree list` 现存原型/修复/实测 lane 为合法在途或已合残留，不删他人 worktree。 | 无 |
| C15 | 相位/功率事实差残余候选 | closed | #125 已并 main（`git merge-base --is-ancestor 1875217 HEAD`=yes）：`tools/migrate/c15-facts.json`（424 行）+ `7-facts.py/.php` legacy_copy 组 + 注册表/FAQ/测试；五台逐台结论在 `docs/debt/C15-phase-power-2026-10-13.md`（#1178 补三相、功率无法核实；#2409 补三相、无额定功率；#6482 补三相+application、15kW 销账；#6529/#6530 三相+电流按手册改+30kW 逆变器侧双来源恢复）；cutover plan 含 `7-facts.py --plan tools/migrate/c15-facts.json` 迁移步（`plan.py:145-152`）且 #17 已执行。`SelectionFacts::phase_count()` 已解析 `3P4W`/`1P2W`（`includes/Products/SelectionFacts.php:243-268`），测试在 `SelectionFactsTest.php`。 | 无 |
| C16 | 6 条 fuzzy REST schema 描述 | closed | 本轮修复：`languages/linker-commerce-de_DE_formal.po` 六条 fuzzy 全部按当前 msgid 重译并去标记，另修一条非 fuzzy 错译（`Rated AC power…` 原 msgstr「Übernehmen」）；`msgfmt --check` 通过、`.mo` 重生成；`tools/checks/i18n-coverage.py` clean（54 untranslated=54 exempt gap=0，其中 EngineeringFeedController 剩 1 条为 #14 schema 版本串、登记豁免、机器面）；linker-commerce PHPUnit 1010/4799 OK（§3）。 | 无 |
| C17 | `card-exact-article` 命名 | closed | 并入 C3：88b1c70 改名后 `card-exact-article` 全树 0 命中；本行不独立加算。 | 无 |
| C18 | 检索 live 重排超时 | closed | 证据核在：`16i/knowledge-index-and-jev.md:50,107`（`--sample 20 --depth 50` 到 10 分钟上限 exit 124、无产出）+ 候选池上限五组实测（`runs/pool-ceiling/`）；未发现任何业主豁免记录——登记册「撤销 B16 豁免」更正成立并保持。是否补测依上线决策：切换已过、线上以真机真答案验证（cutover ⑧），重排 live 实测不再改变交付判断。 | 无 |
| D1 | Genie 重设计 | closed（记录） | 原型已落地：9793163「rebuild the helper dock to the reference's completeness」+ PR #123/#139；对话面 F 段补拍 captured+往返实测（`coverage/README.md` §3 F）。 | 无 |
| D2 | 旧 Advisor 双形态输入 | closed（记录） | PR #114 档案已并；Genie 原型已消费（dock 重建）。 | 无 |
| D3 | 账户同步输入 | closed（记录） | 被裁定 3 取代（C10 行）；account-dashboard lane 已并+独立评审通过。 | 无 |
| D4 | 配置器源流输入 | closed（记录） | PR #108 档案已并；配置器三 lane（#126/#122/#121 + configurator-mobile + present-pdp-configurator）已并。 | 无 |
| D5 | 页脚 E1 已否决方案 | closed（记录） | 业主原话「最后一个可不改」= 否决，保持原两列（2+1）；`CMP_E1.png` 留档。 | 无 |
| E1 | #66 旧工具页承接 | closed | issue #66 CLOSED；`Presentation/ComparePage.php`、`Presentation/LibraryPage.php`、`content/livecanvas/compare_page.html`、`faq_page.html`、`Redirects.php` 均在 main（本轮逐文件核）；C8 特色图另已闭合（C8 行）；compare 空态/ids 表差异属裁定 8 有意变更（ADJUDICATION 族 7）。 | 无 |
| E2 | #67 健康告警与会话保留 | closed | issue #67 CLOSED；`Health/Monitor.php`、`Stock/Retention.php`（原 `Genie/Retention.php`，本轮核路径）在 main；生产运作由 #17 执行 + 线上 12 文件对账（9 同 3 注释级）背书。 | 无 |
| E3 | #68 搜索/联系/文档维护 | closed | issue #68 CLOSED；`Products/ProductSearch.php`、`ProductSearchController.php`、`SearchScope.php`、`Contact/Emails/`、`DocumentLibrary` 在 main；`assets/search-ask.js` 随 88b1c70 改名族（本轮核 `assets/` 无旧名文件）；搜索范围修复在 #158（blog-only）+ #154（分类搜索）。 | 无 |
| E4 | #73 账号审批三态 | closed | issue #73 CLOSED；`Registration/Approval*.php`、`Emails/ApprovedEmail.php` 在 main；审批后台三态按钮缺陷由 #167 修复并实机复验（`coverage/README.md` §3 C2、§5-2、§5bis）。 | 无 |
| E5 | #74 团队摘要 | closed | issue #74 CLOSED；`Digest/DigestEmail.php` 在 main；生产调度由 cutover 装入 hPanel 每分钟 cron 且读回 next_run 证明在跑（17 README「欠账盘点」段）；禁止实发测试的纪律保持（coverage 包 test-mail on/off 记录）。 | 无 |
| E6 | #80 切换工件预建 | closed | issue #80 CLOSED；`mu-plugins/linker-error-recorder.php` 在 main；**记录校正**：登记册「315 条」已过时——`legacy-redirects.json` 现 **316 条**（products 255 + categories 31 + pages 23 + checkout 2 + retired_tools 5；pages 由 19 增至 23：+`/shop/`、`/product-category/uncategorized/`、4 条改名工具路径中的 2 条净增，改名路径随 cutover ⑦-1 chrome 迁移加入）；cutover 实际执行（⑤ deploy、⑥ plugins/data/hygiene 全过）。 | 无 |
| E7 | #81 cutover 脚件与演练 | closed | issue #81 CLOSED；`Storefront/ProductSchema.php`（本轮核路径）在 main；演练未重跑的历史说法被实际切换取代：cutover 窗口 ⑩ 段逐缺陷修并带测试（e20d575/8a5a09e/0eddb93/fa38938/bab7de4/48c2032 等），verify EXIT=0、EN/DE 产品页各恰 1 Product 节点。 | 无 |
| E8 | #98 QueryEmbedding 通道 | closed | issue #98 CLOSED；`Abilities/QueryEmbedding.php`（本轮核路径）在 main；环境尾项随 #17 闭合（C4 行）。 | 无 |
| E9 | 面清单状态回写 | closed | `docs/audit/2026-10-11-surface-inventory.md` 文末「GAP 状态回写（2026-10-13，main c51cb2d）」按范围三种状态（已实现/已预建/切换后生效）逐项回写，非一批改全过；**记录校正**：GAP-6 行的「19 页路径」现为 23（E6 行同源）。 | 无 |
| E10 | 验收索引状态 | closed | `16/INDEX.md` 已更正：抬头「像素门未证，保持未证」；§1 e2e 过期字样已改（套件随 #96 在 main、本索引未跑）；§6 标注未重跑；§7 保持不写 PASS（A3）。与登记册要求逐条一致。 | 无 |
| E11 | r4 六项去向 | closed | `replica-r4/EVIDENCE.md` §3 ①–⑨ 逐项证据、§6 非像素缺口在；六项去向：e2e（#96 并，68 passed）、分组搜索（`[linker_catalog_families]` PER_PAGE_FAMILIES）、描述区（`.pdp-feature/.pdp-overview-secondary`）、srcset（§3-③ 声明 DOM 偏差=B5）、390（A4 已判 0px）、header（A1 已收口 intentional）。 | 无 |

## 2. A3/A4/A6 部署后终局包清单（主会话执行并回填）

已建立部分（2026-10-15 coverage 包）：PDP 四对（A3；**PDP 面已随 #174 作废，见 §1 A3 行**——不再参与终局包）、
列表 390 四默认面 0px（A4）、9 面两口径表（A6）——`docs/acceptance/2026-10-15/coverage/README.md` §3 H +
`.scratch/coverage/h-pairs-metrics.json`。

**回填义务（部署 recheck 修复 + closure 修复之后，主会话执行）**：

1. **要拍的面**（repaired 面，对照旧线上参考；1440/390 × EN/DE 各侧齐）：
   - 分类/商城组成（族 2/9EN/10EN/11EN）：九个 EN 分类页 1440 + 4 个 390、`/products/?brand=goodwe&sort=name` 与 inverters 归档同参数两视口、390 筛选抽屉开态。
   - 营销缺块与短代码带（族 1/4/14/15/21）：Solution utility 四面、For EPC 四面、contact EN/DE 两视口、services EN/DE 两视口、installer(s) EN/DE。
   - 商务链空态与询盘入口（族 13/20）：cart/proforma-request EN/DE 两视口空态。
   - 博客族（族 16/22）：blog 列表、`/category/system-design/` 归档、同篇单页 EN/DE；**判据含 `/de/category/system-design/` 200 + lang=de-DE**（读回判据，closure 决策 17；本轮实测 live 仍 301 到英文页——修复待部署+迁移）。
   - 搜索面（族 17/23）：`?s=PV` EN/DE 两视口，判据=博客文章卡、无产品条目、无分页。
2. **协议**：`.scratch/live-recheck/shoot.mjs` 同一套（禁动画、等字体、600px 步进懒加载、图片 decode 15s、全页 PNG、同机同浏览器同视口）。**新树 id 选择器（closure 决策 7，已落在 shoot.mjs）**：抽屉 `#product-filter-open`（`shoot.mjs:226`）、compare 控件 `[data-compare-product]`（旧 `[data-compare-article]` 保留兼容，`shoot.mjs:145-148,235`）。
3. **归因表模板**（每面一行，回填后逐项呈报业主）：

   | 面 × 语言 × 视口 | 全页差异 px | 全页 % | 最优位移 | 条带差异 px | 条带 % | 页高 local/live | 归因（裁定变更/掩膜/缺陷候选） | 台账行 |
   |---|---|---|---|---|---|---|---|---|
   | … | | | | | | | | |

   归因只允许三类：已裁定变更（引裁定出处）、掩膜（逐项申报）、缺陷候选（进修复队列，不得写成通过）。
4. **标注**：本清单在部署 recheck 修复 + closure 修复（含 `repair-post-categories` 与分类导入迁移）到线上后由主会话执行，结果回填本文件 §2 与 A3 行；回填前 A3 保持 delegated。

## 3. 本轮代码修正（本分支）

1. **C16**：`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` 六条 fuzzy（`EngineeringFeedController.php:115/128/185/189/193/197`）按当前 msgid 重译并去 fuzzy 标记；`EngineeringFeedController.php:181`（Rated AC power）错译「Übernehmen」→「AC-Nennleistung in kW oder unbekannt (#7 SelectionFactSet)」。
   `:120`（feed schema 版本串）保持空译+豁免（机器面，`tools/checks/i18n-exempt.json` 已有豁免；翻译它反而会使豁免失效、门禁失败）。
   `msgfmt --check` 通过；`languages/linker-commerce-de_DE_formal.mo` 重生成；`python3 tools/checks/i18n-coverage.py` = clean；
   linker-commerce PHPUnit 全套 **Tests: 1010, Assertions: 4799, Skipped: 54, OK**。
2. **C3/C6 注释用词残留**：`content/windpress/products-mounts.css` 五处、`content/windpress/storefront.css:4214` 的 catalogue/article 用词改为产品用词（仅注释，规则零改动）。

## 4. 未在本轮的（有裁定支撑，非欠账）

- 未拍功能态 50 行：B–H 段已由 #167 coverage 包清零（33 行 captured、1 行拍不到+替代证据=D6 屋顶瓦片，阻塞原因在 `coverage/README.md` §6-3）；A 段 16 互补格是矩阵未要求，非采集欠账。
- 旧政权词汇/模型路由/测试邮件纪律铁律项：本轮无新发现；`tools/checks/legacy-surfaces.py` CLEAN（`final-merged/README.md`）。
- Q5a 页头项：已收口 intentional（A1 行）。
