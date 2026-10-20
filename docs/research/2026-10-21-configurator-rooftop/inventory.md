# 配置器与屋顶步功能清单（#444）

日期：2026-10-21。只读证据加本目录两份文档。没有改产品代码，没有部署，没有向设计、屋顶或报告端点 POST。评审后改过分类并补了行，计数以下面的表为准，不以先前的 41 / 16 / 7 为准。

父票 #437。集成矩阵归 #445；dossier 覆盖归 #446。本文件只记功能点。Genie 预填是配置器的一个入口，记在这里，并标明 #445 拥有集成矩阵。

## 口径

分类只有三档，一行一档：

- **已验**：有书面验收记录断言该行为通过。记录在 `docs/acceptance/`，或票 #14 的收口评论（2026-10-10，PR #48，squash `6531266`）点名了该行为并指向 `docs/acceptance/2026-10-10/14/`。
- **实现未验**：代码里有，没有书面验收断言它通过。单元测试、e2e 源码、Storybook 都不算验收记录。
- **规格错配**：规格或已记录的设计要求有、实现无（**规格有实现无**），或实现有、规格没有要求（**实现有规格无**）。
- 验收记录写成“不搬”、且规格不要求的原型控件，不进规格错配。C10 跟那份记录，验的是不做，不是控件存在。

`docs/specs/14-solution-configurator.md` 的验收框仍是未勾。那不表示未验收：票 #14 已于 2026-10-10 关闭。`docs/acceptance/2026-10-09/14/` 是收口评论写明“保留仅作参考”的 Storybook 旧档（票 #14 评论 2026-10-10T02:09:56Z：“2026-10-09 的 24 张 Storybook 旧档保留仅作参考。”），不引用为通过。

一行是一个客户能碰到的行为，或规格点名的引擎行为。不把 CSS 类、内部常量单独成行。常量写在它服务的那一行里。

业主裁定（AGENTS.md §2）：2026-10-10 工具页可以改设计；设计报告给 Stückliste，不给回本期；屋顶描绘是可选一步。2026-10-02 的产品与措辞裁定不改本清单的分类。

仓库里没有配置器原型目录。2026-10-12 的原型在已抛弃的本地分支 `proto/configurator-r1`（票 #14 评论），不在本工作树。设计选择记在票 #14 的 2026-10-12 评论，不记一个不存在的原型文件。

## 命名

客户看见的名字是 Solution Configurator / Lösungskonfigurator。屋顶步的客户名是 Roof detail / Dachdetails；应用内标题是 Roof。代码是 `RoofStep`。没有产品标识 “RoofTop”。旧工具是 Linker Site Detail，地址 `/design-canvas/`。本文件用票面的 RoofTop Canvas 只作本节标题，行内用客户名和代码名。

三屏是同一页的三段（输入 → 方案 → 设计报告），不是三条路由。规格 14 第 3 屏写明报告在方案下方。

## 本次线上只读（不执行脚本）

主机响应头 `Date` 为 `Tue, 20 Oct 2026`。落库的一次在 `live-get-2026-10-20.md`（`17:28–17:31 GMT`）。更早的 `16:56–16:59 GMT` 没有单独落成文件，事实与落库的一次同形。文档日期按票面路径 2026-10-21。只做了 GET 与不跟随的 301。没有点击屋顶，没有下载 PDF。

| 请求 | 结果 |
| --- | --- |
| `GET https://de-linker.com/solution-configurator/` | 200。`<title>Configure a Storage System \| Linker</title>`。`lang=en-US`。有 `data-linker-app="configurator"` 与 `data-engine-url` 含 `linker-ai/v1/engine`。无 `data-step`。无 `qcfg-root`。 |
| `GET https://de-linker.com/solution-configurator/?step=roof` | 200。仍无 `data-step`。 |
| `GET https://de-linker.com/de/loesungskonfigurator/` | 200。`<title>Lösungskonfigurator \| Linker</title>`。`lang=de-DE`。挂载同上，无 `data-step`。 |
| `GET https://de-linker.com/wp-json/linker-ai/v1/engine/health` | 200，正文 `{"status":"ok"}`。 |
| 301，不跟随 | `/linker-planner/` → `/solution-configurator/`；`/de/linker-planer/` → `/de/loesungskonfigurator/`；`/design-canvas/` → `/solution-configurator/?step=roof`；`/de/design-canvas/` 与 `/de/entwurfsflache/` → `/de/loesungskonfigurator/?step=roof`；`/quote-configurator/` → `/solution-configurator/`；`/de/angebots-konfigurator/` → `/de/loesungskonfigurator/`；`/de/solution-configurator/?step=roof` → `/de/loesungskonfigurator/?step=roof`（查询串保留）；`/request-a-project/` → `/solution-configurator/`。 |
| 首页与安装商页 | EN 首页工具卡 `href="/solution-configurator/"`，句中有 “The Roof detail step adds the building's layout.”。DE 首页 `href="/de/loesungskonfigurator/"`，句中有 “Der Schritt Dachdetails nimmt die Dachfläche auf.”。`/for-installer/` 有 `href="/solution-configurator/?step=roof"`。德语安装商页是 `/de/fuer-installateur/`（`/de/fuer-installateure/` 为 404），有 `href="/de/loesungskonfigurator/?step=roof"`。 |
| 补记的入口 | 见 `live-get-2026-10-20.md`：`/products/` 与 `/de/produkte/` 的筛选栏、页脚规划列、`/blog/` 与 `/de/blog/` 的 journal-tool。`/shop/` 301 到 `/products/`。 |

## 计数

从下表逐行数，不是从草稿估的。

| 分类 | 行数 | 行号 |
| --- | ---: | --- |
| 已验 | 44 | C01 C03 C04 C05 C07 C10 C11 C12 C13 C14 C15 C16 C20 C21 C23 C24 C26 C27 C29 C32 C33 C34 C35 C36 C37 C38 C40 C41 C42 C43 C45 C46 C47 C48 C49 C50 C58；R01 R03 R04 R07 R09 R12 R14 |
| 实现未验 | 24 | C08 C17 C18 C19 C22 C28 C30 C31 C39 C44 C53 C54 C55 C56 C57 C59 C60 C61；R05 R06 R08 R10 R11 R13 |
| 规格错配 | 7 | C02 C06 C09 C25 C52（规格有实现无）；C51（实现有规格无）；R02（规格有实现无） |

规格错配 7 = 规格有实现无 6 + 实现有规格无 1。C10 与曲线半边已离开错配；C51、C52 是新的错配。补行是 C51–C61。

## 1. 页面与入口

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | 英德配置器页挂载应用，浏览器不直连引擎 | 已验 | `/solution-configurator/`、`/de/loesungskonfigurator/`。LiveCanvas 模板印 `[linker_configurator]` | 无。短代码打印 `data-linker-app`、`data-engine-url`（同源 `linker-ai/v1/engine`）、`data-rest-url`、`data-rest-nonce`。不印 `data-step` | 空挂载点，脚本 `linker-tools-configurator` 接管。无旧标记 `qcfg-root` | `plugins/linker-commerce/content/livecanvas/configurator_page.html`；`plugins/linker-tools/includes/Configurator/Mount.php`；`plugins/linker-tools/src/configurator/index.tsx`；`config.ts` | `docs/acceptance/2026-10-13/pdp-present/README.md`（挂载 ×1，无 `qcfg-root`）；`docs/acceptance/2026-10-13/slug-move/README.md`（2026-10-13，新址 200）。本次线上 GET 同形 |
| C02 | 页面标题为 Solution Configurator / Lösungskonfigurator | 规格有实现无 | 浏览器标题与页内 h1 | 无 | 规格要的一对标题。德语文档标题已是 Lösungskonfigurator。英语文档标题是 “Configure a Storage System \| Linker”。源码 h1 文案是 “Solution Configurator”，本次只读 HTML，没有执行脚本，不能把渲染后的 h1 记成已看见 | `docs/specs/12-site-chrome.md` 第 5 行；`docs/specs/14-solution-configurator.md` 第 3 行“标题改名”；`plugins/linker-tools/src/configurator/App.tsx` 第 96–99 行 | 无通过记录。本次线上 `<title>` 如上 |
| C03 | 旧地址 301 到新址，并保留查询串 | 已验 | `/linker-planner/`、`/de/linker-planer/`、`/design-canvas/`、`/de/design-canvas/`、`/de/entwurfsflache/`、`/quote-configurator/`、`/de/angebots-konfigurator/`、`/request-a-project/`、`/de/solution-configurator/?step=roof` | 原请求的查询串。地图自己带 `?step=roof` 时以地图为准 | 301 到上表的新址。查询串保留不等于屋顶步被打开，打开失败见 R02 | `plugins/linker-tools/includes/Redirects.php`（`carrying_query`）；`docs/specs/12-site-chrome.md` 第 5 行与 N14 | `docs/acceptance/2026-10-13/slug-move/README.md`（本地 301）；`docs/acceptance/2026-10-14/17/README.md`（切换：`/design-canvas/` 301，`/de/design-canvas/` → `/de/loesungskonfigurator/?step=roof`，新址 200）。本次线上 301 同形 |
| C04 | 页头工具卡指向配置器，并写明 Roof detail / Dachdetails | 已验 | EN/DE 首页页头工具卡与移动链接 | 无 | EN `href="/solution-configurator/"`，描述含 “The Roof detail step adds the building's layout.”。DE `href="/de/loesungskonfigurator/"`，描述含 “Der Schritt Dachdetails nimmt die Dachfläche auf.” | `plugins/linker-commerce/content/livecanvas/partials/header.html`；`tools/migrate/12-site-chrome.py` | `docs/acceptance/2026-10-10/12/copy-review.md` §3。本次线上首页句与 href 同文 |
| C05 | 安装商页的屋顶入口是一条链接 | 已验 | `/for-installer/`、`/de/fuer-installateur/` 的主按钮 | 无 | EN `href="/solution-configurator/?step=roof"`，文案 “Open the Roof detail step →”。DE `href="/de/loesungskonfigurator/?step=roof"`，文案 “Dachdetail-Schritt öffnen →”。链接到达后是否打开屋顶步，见 R02，不在本行 | `tools/migrate/12-site-chrome.py`（Roof detail CTA） | `docs/acceptance/2026-10-10/12/copy-review.md`（CTA 定稿）；`docs/acceptance/2026-10-16/m2-copy/copy-review.md`（同页屋顶句通过）。本次线上 href 同文 |
| C06 | Genie `linker/size-hint` 的预填 URL 被配置器读入 | 规格有实现无 | 规格 13：选型走 size-hint，返回 `configurator_url`（预填）。对话里的按钮是另一件事 | 能力入参 `pv_kwp`、`annual_load_kwh`、`phase`、`backup`、`plz`。`lang` 接受后丢弃（#365、#393） | 能力拼出查询 `pv_kwp`、`annual_kwh`、`phase`、`backup`、`plz`。配置器 `readConfig` 不读 `URLSearchParams`，`App` 不把这些值传给住宅表单。预填是死入口。集成是否在对话里发生，归 #445 | `docs/specs/13-genie.md` 第 59 行；`plugins/linker-commerce/includes/Abilities/SizeHint.php` `execute()`；`plugins/linker-tools/src/configurator/config.ts`；`App.tsx` 第 177–181 行（`ResidentialPanel` 无 `defaults`）；`plugins/linker-tools/src/genie/components/ActionView.tsx` 第 27–33 行 | 无。配置器源码无 `URLSearchParams`。`ActionView` 在 `open_configurator` 且 `block.args.url` 时渲染 “Open the configurator”；文件头注释写明该 URL 过了 grounding，所以是工具返回的（size-hint 的 `configurator_url`）。按钮在，不表示配置器读查询串 |
| C58 | 产品列表筛选栏下的配置器入口 | 已验 | `/products/`、`/de/produkte/`，筛选折叠之后。`/shop/` 301 到 `/products/` | 无 | EN “Plan with the Solution Configurator” / “Configure a storage system from your site data; the result is a solution draft you can send as an inquiry.” / “Open the Solution Configurator”。DE “Mit dem Lösungskonfigurator planen” / “Lösungskonfigurator öffnen” | `plugins/linker-commerce/includes/Presentation/ProductShortcodes.php` 第 315–324 行 | `docs/acceptance/2026-10-10/12/copy-review.md` §B 定稿这三句。`live-get-2026-10-20.md`：`/products/` Date `Tue, 20 Oct 2026 17:30:26 GMT`，HTML 与定稿同文；德语页 17:30:31 GMT 同文 |
| C59 | 页脚 “Plan with Linker” 链到配置器 | 实现未验 | 页脚规划列 | 无 | 线上 EN 该列三条：Genie → `/genie/`，Solution Configurator → `/solution-configurator/`，Blog → `/blog/`。DE：Lösungskonfigurator → `/de/loesungskonfigurator/`。链接文字没有 Roof detail 句；那句在页头卡，见 C04。规格 12 第 4 行点名这个区块里的配置器卡 | `plugins/linker-commerce/content/livecanvas/partials/footer.html`；`partials/de/footer.html`；`docs/specs/12-site-chrome.md` 第 4 行 | 无验收记录点名这条页脚 href。`docs/acceptance/2026-10-10/12/visual-scope.md` 只说页头页脚两卡走 LC partial。本次线上 GET 看见链接 |
| C60 | 博客索引的配置器入口 | 实现未验 | `/blog/`、`/de/blog/` 的 journal-tool | 无 | EN “From reading to a system plan.” + “Open the Solution Configurator” → `/solution-configurator/`。DE “Von der Recherche zur Planung.” + “Lösungskonfigurator öffnen” → `/de/loesungskonfigurator/` | `plugins/linker-commerce/content/livecanvas/blog_index.html`；`content/livecanvas/de/blog_index.html`；`docs/specs/175-blog-legacy-templates.md` 第 215–216 行 | `docs/acceptance/2026-10-18/254/copy-review.md` 只说这两句保留，没有把链接当通过走查。本次线上 GET 看见同文 |
| C61 | 已登录账户的空方案页指向配置器 | 实现未验 | `/my-account/saved-solutions/` 无保存方案时 | 无 | LC 空态句 “Solutions you save in the Solution Configurator appear here, with their design report.” 加 CTA “Open the Solution Configurator”。规格 184 第 70 行点名这个空态 CTA。登录且 LiveCanvas 可用时走这条。PHP 模板的空分支只有那句、没有链接，那是 LC 不可用时的回退 | `docs/specs/184-account-chain.md` 第 70 行；`plugins/linker-commerce/content/livecanvas/account/empty-solutions.html`；`AccountTemplates.php` 第 111–112、470、472、592 行；`templates/myaccount/linker-saved-solutions.php` 第 18–21 行 | 无验收记录点名空态 CTA。本次未登录账户页 |

## 2. 三屏共用

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C07 | 项目类型三选一，每项带范围说明 | 已验 | 页内 “Project type” 单选组 | 点选 Residential / Commercial & industrial / Utility | 切到对应面板。范围句：住宅 “Home PV, storage and backup”；工商业 “Site load, peak power and operating profile”；电站 “Storage blocks, grid connection and project stage” | `plugins/linker-tools/src/configurator/App.tsx` 第 53–75、126–168 行 | `docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md` §4（aria 快照三枚 radio）；`docs/acceptance/2026-10-18/302/README.md`（EN/DE × 1440/390 输入屏截图） |
| C08 | 方向键在三个项目类型间移动 | 实现未验 | 焦点在当前 radio 上 | ArrowLeft / ArrowRight | 切换并聚焦下一项 | `App.tsx` `onTabKey` 第 77–86 行 | 无验收记录点名键盘 |
| C09 | 左侧步骤栏的当前步跟着屏幕走 | 规格有实现无 | 页内左栏 01 Inputs / 02 Solution / 03 Design report | 计算完成、报告出现、手机底栏滚动 | 规格 14 不点名步骤栏；它描述的是同一页上的三段。业主 2026-10-12 选定 B 左栏作为步骤导航。实现把 `current` 写死为 1，方案和报告出现后栏仍停在 01。C 的顶部进度条被明确不搬（同一页不做第二个步骤指示），所以缺的是这一栏的当前步，不是第二套进度条 | 票 #14 评论 2026-10-12；`App.tsx` 第 91 行 `<Steps current={ 1 } />`；`docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md` §4 | 栏的存在见 c-fidelity 与 `docs/acceptance/2026-10-13/configurator-mobile/README.md`。当前步前进无通过记录 |
| C10 | TASK 区与底部 Continue 不进入产品 | 已验 | 无。2026-10-12 评论里的原型控件，不是现行入口 | 无对应引擎字段 | 不渲染。提交条是 “Calculate system”，不是向导的 Continue | 票 #14 评论 2026-10-12；`docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md` §4 | 规格 14 不要求这些控件。c-fidelity §4 把不搬记成已关闭的设计选择：TASK 下拉和 Similar systems 是原型假输入，`residential-input.schema.json` 无字段，不伪造输入；顶部进度条不搬，因为左栏是选定的步骤导航。本行验的是这条不做的记录，不是控件存在。不进规格错配 |
| C11 | 手机底栏只滚动到已有区块 | 已验 | 48rem 以下，住宅与工商业 | 点 Inputs / Solution / Design report | 滚到既有展开区块。不计算、不提交、不改变候选。电站不造底栏 | `plugins/linker-tools/src/configurator/MobileNavigation.tsx`；`ResidentialPanel.tsx` 第 104–124 行 | `docs/acceptance/2026-10-13/configurator-mobile/README.md` |
| C12 | 同源引擎代理，健康检查可答 | 已验 | 浏览器只请求 `data-engine-url` | 白名单路径：`health`、`geo/plz/{plz}`、`design/residential`、`design/commercial`、`roof/outline`、`roof/pack`、`report/pdf`。上游地址是选项 `linker_engine_url` | 状态码原样透传。`GET …/engine/health` 本次线上 200 `{"status":"ok"}`。健康 200 不证明计算或 PDF 字节。PDF 字节路径见 C39 | `plugins/linker-tools/includes/Configurator/EngineProxy.php` `PATHS`、`flatten_headers`；`services/engine/src/linker_engine/app.py` `health`；`plugins/linker-tools/src/configurator/api/engine.ts` | 规格 14 变更记录 2026-10-14（浏览器直连自签证书失败后改道）。本地功能走查用过这条代理：`docs/acceptance/2026-10-15/coverage/README.md` D3。线上本次只验了 health |
| C13 | 德语脚本译文从 PO 经 make-json 进入页面 | 已验 | 德语页 `wp_set_script_translations` | `linker-tools-de_DE_formal.po` | 配置器入口的 JSON 译文。懒加载的屋顶组件用同一组。Sie 体 locale `de_DE_formal` | `docs/specs/14-solution-configurator.md` “脚本译文（#302）”；`plugins/linker-tools/languages/linker-tools-de_DE_formal.po` | `docs/acceptance/2026-10-18/302/README.md`（209 条、EN/DE 截图、DE 校验原文）。本次未再拆内联 JSON |

## 3. 住宅输入

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C14 | 邮编、年用电、光伏 kWp | 已验 | 住宅面板。kWp 也可来自屋顶步（R07） | 五位德国邮编、年用电 kWh、kWp | 送入 `POST /design/residential` | `plugins/linker-tools/src/configurator/residential/ResidentialForm.tsx`；`schema/residential-input.schema.json` | `docs/acceptance/2026-10-10/14/inputs-*-empty.png`（票 #14 收口，2026-10-10） |
| C15 | 相数 1 或 3 | 已验 | 住宅表单 | 单相 / 三相 | 写入 `phase`。单相上限的排除见 C41 | `ResidentialForm.tsx`；规格 14 第 7 行 | 同上，空表单截图 |
| C16 | 备电选择：无 / 需要 / 需要且接受加配件 | 已验 | 住宅表单 | `none` / `needed` / 接受配件 | 选择本身进入请求。预留电量是否加在区间上，见 C17，本行不认那个效果 | `ResidentialForm.tsx`；规格 14 第 7 行 | 同上，空表单截图有该控件。没有把预留计算记进本行 |
| C17 | 备电预留（kW × h）加在 HTW 区间之上 | 实现未验 | 备电为需要时的附加字段 | `backup_load_kw`、`backup_hours` | 规格 14：备电预留另加，输出区间 | `services/engine/src/linker_engine/residential.py`；`services/engine/tests/test_htw.py::test_the_backup_reserve_comes_on_top`；`test_residential.py::test_backup_reserve_and_heat_pump_widen_the_range` | 无验收记录。只有单元测试 |
| C18 | 热泵 / 电动车只加宽用电区间 | 实现未验 | 住宅表单是/否 | `heat_pump`、`electric_vehicle` | 规格 14：只影响用电区间，不另造一条选型规则 | `services/engine/tests/test_htw.py::test_heat_pump_and_car_widen_the_consumption_and_the_limit` | 控件在空表单截图里。加宽效果无验收记录 |
| C19 | 既有逆变器型号：加装只留有放行的电池；未知型号转团队 | 实现未验 | 住宅表单可选字段 | 型号字符串 | 已知型号只列放行电池；未知型号要求联系团队 | `test_residential.py::test_retrofit_lists_only_released_batteries`；`test_an_unknown_existing_inverter_asks_for_the_team`；规格 14 第 7 行 | 无验收记录 |
| C20 | 计算中、失败、再试一次 | 已验 | “Calculate system” | 已通过 schema 的住宅输入 | 计算中态；失败后 “Try again”。产量服务 503 与未知邮编的专用句见 C22，本行是通用失败与计算中 | `ResidentialPanel.tsx` `calculate`；`App.stories.tsx` 的 computing / error | `docs/acceptance/2026-10-10/14/solution-*-computing.png`、`solution-*-error.png`；`docs/acceptance/2026-10-15/coverage/README.md` D3（本地，计算中被延时顶住） |
| C21 | 表单按引擎 JSON Schema 校验（五位邮编等） | 已验 | 提交时 | 例如邮编 `12` | 字段错误 “Enter a German postcode with five digits.”。德语校验原文在 #302 | `schema/residential-input.schema.json`；规格 14 前端节 | `docs/acceptance/2026-10-15/coverage/README.md` D3；`docs/acceptance/2026-10-18/302/README.md`（`de-validation.json`） |
| C22 | 真实但未知的邮编，以及产量服务不答 | 实现未验 | 引擎 422 `field=plz`，或 503 `yield_unavailable` | 通过了五位校验、但不在地名表的邮编；或 PVGIS 不答 | “We do not know this postcode. Check it and try again.” / “The yield service did not answer. Try again in a minute.” | `ResidentialPanel.tsx` `errorText` 第 59–74 行；`services/engine/src/linker_engine/app.py`（404/503 映射） | 无。D3 的邮编 `12` 是 schema 失败，不是这条引擎文案 |

## 4. 方案

工商业结果没有加入、保存、设计报告。规格 14 的工商业验收条只要求 kW/kWh 或指示区间加询盘，不要求这三项。那不是错配，不单列。见 C46、C48。

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C23 | 方案四项：发电量区间、可用储能、自给率、自用比例 | 已验 | 住宅计算成功且有选定系统 | 引擎 `yield`、`storage`、`metrics` | 区间，不是单点。自给率/自用比例是 HTW 式查表，不做逐小时模拟 | `plugins/linker-tools/src/configurator/solution/Solution.tsx`；规格 14 第 14–17 行；`services/engine/src/linker_engine/report.py` 节 `metrics` | 票 #14 收口（8 户型落上限并给区间）；`docs/acceptance/2026-10-10/14/solution-*-proposal.png`；`docs/acceptance/2026-10-13/e2e-and-fixes/README.md`（配置器 e2e 17/17，引擎直连） |
| C24 | 产品卡：方案数量、有货徽标、放行、文件、为何是这件 | 已验 | 选定系统与备选卡 | `selected.lines`、Store API `is_in_stock === true`、放行 `documents` | 有货时徽标 “In stock”。数量是方案件数，不是库存件数（AGENTS.md 2026-10-11：对客户不说库存数量）。暂时无货见 C25 | `Solution.tsx` 第 258–261 行；规格 14 第 10 行 | `docs/acceptance/2026-10-10/14/solution-*-proposal.png`、`solution-*-added.png`。通过的是有货路径 |
| C25 | 暂时无货 | 规格有实现无 | 方案卡；工商业系统卡 | `is_in_stock === false` | 规格 14 要求方案卡带“有货”。AGENTS.md 2026-10-11：对客户说有货或暂时无货。实现只在 `is_in_stock` 为真时画 “In stock”。PO 里有 “Currently unavailable”，配置器方案卡不用。工商业卡不画库存 | `Solution.tsx` 第 258–261 行；`commercial/CommercialResult.tsx`（无 `is_in_stock`）；`languages/linker-tools-de_DE_formal.po` msgid “Currently unavailable” | 无缺货态记录 |
| C26 | 换成同类逆变器或电池并重算 | 已验 | 方案卡上的备选 | 另一件已放出的候选 | 保持另一侧的选择，重新出方案 | `Solution.tsx`；`test_residential.py::test_a_swap_keeps_the_chosen_inverter_and_battery` | `docs/acceptance/2026-10-15/coverage/README.md` D3（“solution + 替代”）；`docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md`（换型后滚动落点） |
| C27 | 全部加入 Lösungsentwurf，并读回数量 | 已验 | “Add all to solution draft / Alles zum Lösungsentwurf hinzufügen” | 选定系统里带商品 id 的行 | Store API 写入后读回。票 #14 实例读回：商品 3556 ×1 与 3611 ×1，句 “All products are in your solution draft.” | `plugins/linker-tools/src/configurator/api/store.ts`；规格 14 第 10 行与验收第 2 条 | 票 #14 评论 2026-10-10（本地 t14，替身挂载）。`docs/acceptance/2026-10-10/14/solution-*-added.png`。切换后没有在线上再走一遍。见文末风险 |
| C28 | 加入未确认、重试、部分成功，以及短读后再读三次 | 实现未验 | 同一枚加入按钮 | Store API 500、回读数量对不上、只写入一部分 | 卡状态 `unverified` / `retry`；整单 `partial`。`SETTLE_MS = 250`、`SETTLE_READS = 3` 来自 2026-10-19 的 #251 e2e 观察，没有验收记录 | `store.ts` 第 24–38、146–185 行；`Solution.tsx` `addOutcome` | 2026-10-10 归档有 `added`，没有 `unverified`。Genie 卡片七态在 `docs/acceptance/2026-10-15/coverage/README.md` F3，那是另一条卡，不算配置器本行 |
| C29 | 保存方案到账户，并给出打开链接 | 已验 | “Save solution / Lösung speichern” | 已登录会话；正文是引擎输入 | `POST linker/v1/solutions`。成功句 “Saved to your account.” 加打开链接 | `plugins/linker-tools/src/configurator/api/solutions.ts`；`plugins/linker-commerce/includes/Account/SolutionsRoute.php`；规格 14 第 10 行 | 票 #14 评审修复评论（saved 状态测试 + 四张截图）；`docs/acceptance/2026-10-10/14/solution-*-saved.png`。访客路径见 C30 |
| C30 | 访客用 claim cookie 保存 | 实现未验 | 同一保存按钮，未登录 | claim cookie | 规格 14 写明“登录或 claim cookie”。`solutions.ts` 注释写了访客 cookie。没有验收走过未登录保存 | `plugins/linker-tools/src/configurator/api/solutions.ts` 文件头注释 | 无 |
| C31 | 保存失败 | 实现未验 | 保存请求失败 | `linker/v1/solutions` 非成功 | “Not saved. Try again.” | `ResidentialPanel.tsx` 保存状态 | 无。F3 的 save-failed 是 Genie 卡 |
| C52 | 配置器保存时带上设计报告 PDF | 规格有实现无 | 方案屏 Save；账户 Saved solutions | 规格 11 §7：保存的方案与设计报告 PDF 来自 #14。路由接受可选 `report_pdf` | `saveSolution` 只 POST `kind`、`title`、`input`、`lines`，不传 `report_pdf`。账户空态仍写方案会带着设计报告出现。PDF 链接只在 `report_path` 非空时出现，所以这条保存产不出 “Design report (PDF)”。“Add to solution draft” 是账户上另一条 POST（`SavedSolutions::ADD_ACTION`），保存卡上始终有，不依赖 PDF，不是本行的缺口 | `docs/specs/11-commerce.md` 第 16 行；`plugins/linker-tools/src/configurator/api/solutions.ts` 第 40–47 行；`ResidentialPanel.tsx` `save()` 第 181–195 行；`plugins/linker-commerce/includes/Account/SolutionsRoute.php` 第 93 行；`content/livecanvas/account/empty-solutions.html`；`solution-card.html` 第 8–9 行；`AccountTemplates.php` 第 464–465、587、593–599 行 | 无通过记录。空态句与 PDF 链接的文案在，字节不在 |
| C32 | 无合格候选：逐条被拒规则，以及可放宽的条件 | 已验 | 住宅计算返回无选定系统 | 例如单相 + 30 kWp | “No system in our range meets every rule” 与可放宽项 | `plugins/linker-tools/src/configurator/solution/NoCandidate.tsx`；`test_residential.py::test_no_candidate_names_what_to_relax` | `docs/acceptance/2026-10-10/14/solution-*-no-candidate.png`；coverage D3（2026-10-15，本地） |
| C33 | 安装商自备件（线缆、连接器、熔断器）单独成表，无商品 id | 已验 | 方案屏表格；报告 Stückliste 的 scope 列 | 引擎行 `product === null` | 表上标明不由 Linker 供应。报告用 `scope.installer` | `Solution.tsx`（installer 过滤）；`services/engine/src/linker_engine/report.py` `_bom_table`；规格 14 第 19 行 | 票 #14 收口的完整 Stückliste 与 `report-en.pdf` / `report-de.pdf`。屏上的表是同一批行，不另计一次通过 |

## 5. 设计报告

报告只在住宅、且有选定系统时出现（`ResidentialPanel.tsx` `reportReady`）。工商业与电站没有这一屏。规格验收条也不要求它们有报告。

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C34 | 报告屏各节 | 已验 | 方案下方 | 住宅设计结果 | 节 id：`site`、`yield`、`storage`、`metrics`、`basis`、`releases`、`bom`、`warnings`、`assumptions`、`next`。规格点名的是场地与输入、发电量区间、自给率与自用比例、选型依据、放行与文件、Stückliste、假设与限制、下一步。`storage` 与 `warnings` 多出来，对应规格引擎节的定容与 `warnings[]`，不单列错配 | `services/engine/src/linker_engine/report.py` `residential()`；`plugins/linker-tools/src/configurator/report/ReportView.tsx` | `docs/acceptance/2026-10-10/14/report-*-report.png`；`test_report.py::test_sections_follow_the_ticket` 被收口评论盖住，截图是验收 |
| C35 | 报告中的 Stückliste | 已验 | 报告节 `bom`；PDF 同一模型 | 选定系统的行 | 数量、名称、型号、供应方。含安装商自备行 | `report.py` `_bom_table`；规格 14 第 11 行；AGENTS.md §1 | 票 #14 收口；`docs/acceptance/2026-10-10/14/report-en.pdf`、`report-de.pdf` |
| C36 | 不给回本期、现金流、电价、CAPEX，并在假设里写明 | 已验 | 报告假设节；引擎不做这些字段 | 无经济性输入 | 假设句 `limit.no_payback`。收口评论：经济性只剩披露句 | `report.py` 第 356 行；`services/engine/tests/test_report.py::test_no_economics_anywhere`；规格 14 第 11、23 行；AGENTS.md 2026-10-09 | 票 #14 收口评论 2026-10-10 |
| C57 | 手填 kWp、没有屋面时，报告写明按 35° 朝南估算 | 实现未验 | 报告假设节，且请求没有 `planes` | 手填 kWp，不采用屋顶步 | 句 `limit.default_orientation`：EN “Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).” DE “Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).” 屋顶步绘制框的默认倾角 35、朝向 180 是同一组默认，但是输入框，不是这句披露 | `services/engine/src/linker_engine/texts.py` 第 517–519 行；`report.py` 第 360–361 行；`RoofStep.tsx` 第 92–93 行 | 无验收记录点名这句 |
| C37 | 可选 Logo（PNG 或 JPEG，至多 500 kB）印在 PDF 上 | 已验 | 报告屏 “Choose logo” | PNG/JPEG，客户端拒绝大于 `500 * 1024` 字节的文件 | PDF 带该图。超限拒绝句没有单独的验收走查，不把拒绝路径算进本行的通过 | `ReportView.tsx` `LOGO_BYTES`；`services/engine/src/linker_engine/pdf.py`；规格 14 第 21 行 | `docs/acceptance/2026-10-10/14/logo-en.png`、`logo-de.png`，以及两份带 Logo 的 PDF |
| C38 | 引擎直接渲染 EN/DE PDF | 已验 | `POST /report/pdf`（e2e 打的是引擎自己的 URL，不是站点代理） | 住宅输入，可选 logo | `application/pdf`，体以 `%PDF-` 开头，文件名 `linker-design-report-{plz}-{locale}.pdf` | `services/engine/src/linker_engine/app.py` `report_pdf`；`tests/e2e/specs/configurator.spec.ts` “the design report is a PDF in both languages” | `docs/acceptance/2026-10-10/14/report-en.pdf`、`report-de.pdf`；e2e 17/17 见 `docs/acceptance/2026-10-13/e2e-and-fixes/README.md`。这不是经站点代理的下载 |
| C39 | 浏览器里点 Download PDF，经站点代理得到 PDF 文件 | 实现未验 | 报告屏 Download PDF | 浏览器 POST `…/wp-json/linker-ai/v1/engine/report/pdf` | 客户点按钮后应得到 PDF 文件。代理字节路径在修复后有实例 curl，没有浏览器再点这个按钮 | `EngineProxy.php` `flatten_headers`；`ReportView.tsx` `engine.reportPdf` | D2（`docs/acceptance/2026-10-15/coverage/README.md`）记的是修复前：下载落成 JSON 包着 PDF 文本（73 237 B，头 `{"det…`）。同一文件 §5bis 记修复后、同一实例上的 curl：`POST http://127.0.0.1:8975/wp-json/linker-ai/v1/engine/report/pdf` 返回 `proxy 200 application/pdf 48837`（头 `%PDF-1.4`，3 页）与 `proxy-de 200 application/pdf 49529`。那是实例 curl，不是浏览器点击，也不是线上。未验的只是浏览器 Download 按钮。本次线上未下载 |

## 6. 规格点名的资格与户型

这些是引擎行为。e2e `tests/e2e/specs/configurator.spec.ts` 打的是已部署引擎的契约，不是浏览器点选。2026-10-13 的 17/17 是那次本地实例的记录，不是本次线上。

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C40 | 八个典型户型落在 HTW 三条上限内，并给区间 | 已验 | `POST /design/residential` | planner-methods 表中的 kWp / 年用电，邮编夹具 80538 | 可用容量 ≤ 1.5 kWh/kWp 且 ≤ 1.5 kWh/MWh·a；发电量、自给率、自用比例为区间 | 规格 14 第 16–17、45 行；`services/engine/tests/test_residential.py::test_typical_households_stay_within_htw_and_get_ranges`；`tests/e2e/specs/configurator.spec.ts` | 票 #14 收口；`docs/acceptance/2026-10-13/e2e-and-fixes/README.md`（17/17） |
| C41 | 单相馈入不超过 4.6 kVA | 已验 | 同上，`phase: 1` | 单相 6 kW 一类请求 | `EF HD-P1-6K0-S2`、`GW6K-EHA-G20` 因 `single_phase_limit` 排除；候选交流功率 ≤ 4.6 | `services/engine/src/linker_engine/eligibility.py` `single_phase_limit`；规格 14 第 18 行 | 票 #14 收口点名该测试；e2e 同名用例在 17/17 里 |
| C42 | 光伏输入小于所问 kWp 的逆变器排除 | 已验 | 同上，10 kWp | 机型自身的 `pv_input_kw` | `HS2-5K-T2-X`、`HS2-6K-T2-X` 因 `pv_input` 排除。10 kWp 等于 HS3-5K 上限时仍为候选 | `eligibility.py` `pv_input` | 票 #14 收口；e2e “an inverter whose PV input is too small is excluded” |
| C43 | 熔断器按每路 MPPT 的并联串数计，不按整阵计 | 已验 | Stückliste / 组串布局 | 参考组件的串布局 | 每组熔断数为 0 或 `串数 × 2`。部署产品每路最多两串，故组读 0。四串并联的计数在引擎单测 | `services/engine/src/linker_engine/rules.py`（`STRING_FUSE_*`）；`services/engine/tests/test_strings.py`；e2e “fuses are counted per MPPT string group” | 票 #14 收口点名 `test_strings.py`。e2e 锁的是部署布局的不变量 |
| C53 | 电池数量按数据手册堆叠范围与放行模块范围取值 | 实现未验 | 住宅选定系统的电池行 | 逆变器、电池、放行配对、容量上限 | `stacking.configurations` 给出允许的数量；`pick` 取上限内最大的一档，否则取超上限的最小一档并标记。规格 14 第 19 行点名堆叠规则。收口的完整 Stückliste 没有点名这个取值 | `services/engine/src/linker_engine/stacking.py`；`residential.py` 第 150–152 行 `stacking.pick` | 无验收记录点名堆叠取值。单测不算 |
| C54 | 电表按放行条件列入 Stückliste，已含在机内的不计 | 实现未验 | 住宅 Stückliste 的 meter 行 | `compatibility.requirements(inverter.model, "meter")`，且 `not included`、相数匹配 | 配件行，数量来自放行条件。规格 14 第 19 行点名电表/互感器按放行条件。代码按 kind `meter` 过滤，没有单独的互感器 kind | `residential.py` `_requirement_lines` 第 418–430 行 | 无验收记录点名电表行。`test_compatibility.py::test_meters_in_and_beside_the_box` 是单测 |
| C55 | 直流电缆与连接器按每串规则计长度和对数 | 实现未验 | 安装商自备行里的 cable / connector。屏上的表是 C33，熔断器是 C43 | 串数 × 每串规则 | 电缆 `串数 × 2 × 15 m`（每极每串 15 m；规则注明是占位、`verified=False`）。连接器 `串数 × 2` 对（每串 2 对）。规格 14 第 19 行点名线缆与连接器按 Stückliste 规则 | `residential.py` `installer_lines` 第 483–520 行；`rules.py` `DC_CABLE_M_PER_STRING`、`CONNECTOR_PAIRS_PER_STRING` | 无验收记录点名这两条计量。C33 验的是表在，不是米数和对数 |
| C56 | 放行三值取更严的一档，未覆盖的配对不做放行 | 实现未验 | 住宅候选的配对 | 逆变器型号 × 电池型号 | 三值 `released`、`released_with_accessory`、`not_released`，再加 `unknown`。`_STRICTNESS` 为 2 / 1 / 0，`pair()` 取最小（更严）。无匹配返回 `unknown`，不假定放行。`released()` 只含前两值。规格 14 第 18 行点名三值配对。卡片上显示某一放行是 C24，本行是取值规则 | `services/engine/src/linker_engine/compatibility.py` 第 23–27、61–62、112–123 行 | 收口点名的是选定系统为放行或带配件放行，没有点名更严者优先。单测不算 |
| C44 | 资格里的 application=home 与 DC/AC 不超过厂商上限 | 实现未验 | 住宅候选过滤 | 逆变器 `application`、`pv_input_kw / ac_power_kw` | 规格 14 第 18 行列了这两条，与相数、单相上限、`pv_input_kw ≥ kWp`、放行配对并列。收口评论点名的合规用例只有 C41–C43 | `eligibility.py` `application`、`dc_ac_ratio` | 无验收记录点名这两条 |

## 7. 工商业

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C45 | 采集表 | 已验 | 工商业面板 | 邮编、并网 kVA、年用电、目标（削峰 / 自用 / 备用）、峰值 kW、可选目标峰值、可选光伏 kWp、备电 kW 与小时、负荷单位 kW 或 kWh、室内/室外/未知、备注、可选 CSV | 送入 `POST /design/commercial`。无加入、无保存、无设计报告 | `plugins/linker-tools/src/configurator/commercial/CommercialPanel.tsx`；规格 14 第 8 行 | `docs/acceptance/2026-10-10/14/commercial-*-empty.png` |
| C46 | 有 15 分钟 CSV 时给出 kW 与 kWh，并列出系统 | 已验 | 上传 CSV 后计算 | 30 天 × 96 点一类曲线；可选 `target_peak_kw` | `status: sized`。功率与能量为区间。系统列出并联台数。无 “Add all” | `services/engine/src/linker_engine/commercial.py`；`CommercialResult.tsx`；规格 14 第 20、47 行 | 票 #14 收口（`test_peak_shaving_from_the_profile` 与 sized 截图）；coverage D4（2026-10-15，本地，with-csv） |
| C47 | 工商业用负荷持续曲线定 kW/kWh，并给出选项表 | 已验 | 有 CSV 的工商业结果 | `load.duration_curve_kw`；引擎 `options` | 规格 14 第 20 行：有负荷数据则用负荷持续曲线定 kW/kWh。页面 `Curve` 画这条曲线。选项表是收口评论点名的输出。“Size for N kW” 按钮不在本行，见 C51 | `docs/specs/14-solution-configurator.md` 第 20 行；`CommercialResult.tsx` `Curve` 第 166–172 行；`services/engine/src/linker_engine/commercial.py` | 票 #14 评论 2026-10-10T02:09:56Z：`test_peak_shaving_from_the_profile`（CSV → kW/kWh + 选项表）；sized 截图。曲线是规格里的定容方法，不是实现多出来的图 |
| C51 | “Size for N kW” 把选项表的某一档设成封顶 | 实现有规格无 | 选项表每一行的按钮 | 点 “Size for %s kW” | 调用 `onChooseCap(option.cap_kw)`，用该 kW 重算。规格 14 要求的是曲线定出的 kW/kWh 与选项表，不要求这个封顶按钮 | `CommercialResult.tsx` 第 251–262 行 | 无记录把这个按钮写成规格要求。从原 C47 拆出。类是错配，不是未实现 |
| C48 | 无 CSV：指示区间，加询盘 mailto | 已验 | 不上传曲线即计算 | 并网、年用电、目标、峰值 | `status: indicative`。`systems` 为空。`inquiry` 含 `sales@de-linker.com`。按钮 “Send us an inquiry” | `CommercialResult.tsx` 第 320 行；规格 14 第 8、47 行 | 票 #14 收口；`docs/acceptance/2026-10-10/14/commercial-*-indicative.png`；coverage D4 |
| C49 | 工商业的计算中、校验错误、超配空结果 | 已验 | 同一面板 | 邮编 `12`；或并网 1 kVA、峰值 5 000 kW | 计算中 `aria-busy`；字段错误；空结果。规格没有单独的工商业空结果条。这是 C46 的失败态，coverage 记了通过，不另作错配 | `CommercialPanel.tsx` | `docs/acceptance/2026-10-15/coverage/README.md` D4 |

## 8. 电站

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C50 | 电站询盘是一封 mailto，不是站内询盘记录 | 已验 | Utility 段 “Write to our team” | 场地、功率 MW、容量 MWh、并网、计划投运、项目说明。六个自由文本，无 schema | `mailto:sales@de-linker.com?subject=Utility-scale storage inquiry`，正文为已填字段。句中承诺一个工作日内回复。不创建站内询盘。规格 14 写“询盘表单”，2026-10-15 把这条 mailto 接受为提交。无校验错误态（coverage D5：该状态不存在），不单列错配 | `plugins/linker-tools/src/configurator/utility/UtilityForm.tsx` `TEAM_EMAIL`；规格 14 第 9 行 | `docs/acceptance/2026-10-10/14/utility-*-form.png`；`docs/acceptance/2026-10-15/coverage/README.md` D1 |

## 9. RoofTop Canvas（屋顶步）

这是配置器的可选一步，不是独立产品，也不是第四条路由。客户名 Roof detail / Dachdetails / Roof。代码 `RoofStep`。地图是 MapLibre，手绘是 terra-draw，按需加载。

假设常量在 `services/engine/src/linker_engine/roof/service.py`：`CLICK_TOLERANCE_M = 3.0`；`ROOF_ASSUMPTIONS` = `roof_flat`、`roof_max_tilt`、`roof_north`、`roof_edge_inset`、`module_gap`。来源记录 `docs/acceptance/2026-10-09/14/sources.md` 把这些标成未核实的规划假设。它们随 R09 披露，不各自成行。

| # | 功能 | 分类 | 入口 | 输入 | 输出 | 文件 | 验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R01 | 有效邮编之后，从住宅表单打开屋顶步 | 已验 | “No PV figure yet? Estimate from the roof” / 已有屋顶时的更换入口。先 `trigger('plz')` | 五位邮编 | 打开屋顶面板。`GET /geo/plz/{plz}` 给出地点、州、影像服务 | `ResidentialForm.tsx` `openRoof`；`plugins/linker-tools/src/configurator/roof/RoofStep.tsx` | `docs/acceptance/2026-10-10/14/inputs-*-roof-applied.png`、`roof-*-outline.png`；coverage D6（2026-10-15，地图面板打开） |
| R02 | `?step=roof` 与旧 Site Detail 地址打开屋顶步 | 规格有实现无 | 安装商页 CTA、`/design-canvas/` 及其德语别名的 301（C03 已验的是跳转本身） | 查询 `step=roof`。页面没有预填邮编 | 规格 12 与 `config.ts` 写明 `data-step="roof"` 应先打开屋顶步。`Mount.php` 不印 `data-step`。本次线上 `?step=roof` 的 HTML 无该属性。即便印了，`ResidentialPanel` 还要求 `defaults.plz`，而 `App` 不传 `defaults`。深链停在第一步 | `docs/specs/12-site-chrome.md` 第 5 行；`config.ts` 第 8–9、39 行；`Mount.php` 第 62–71 行；`ResidentialPanel.tsx` 第 126–130 行；`App.tsx` 第 177–181 行 | 无打开记录。跳转的通过记录不能算打开 |
| R03 | 官方航拍、缩放、归属行 | 已验 | 屋顶面板里的地图 | 邮编对应州的影像服务 | 航拍与归属。80538 的归属是 Bayerische Vermessungsverwaltung，许可 CC BY 4.0。2026-10-15 本地走查看见归属行，但 WMS 瓦片取不到，画布是灰底 | `services/engine/src/linker_engine/app.py` `place`（`imagery.for_state`）；`RoofStep.tsx` | 票 #14 收口（实例上真实巴伐利亚 WMS，截图 credit 该句）；coverage D6 看见归属行，没有拍到瓦片 |
| R04 | 点击航拍得到 LoD2 轮廓、屋面、组件数 | 已验 | 地图点击 | 邮编 + 点击坐标。夹具 PLZ 80538 / Triftstraße 5。墙外 3 m 内仍选中该建筑 | `found`、`building_id`、地址、轮廓、屋面（倾角、朝向、可用、组件多边形）、组件总数、kWp、参考组件、许可、假设。邮编中心不在建筑上时组件数为 0，不编造屋顶 | `roof/service.py` `outline`；`tests/e2e/specs/configurator.spec.ts` “roof step: a real Munich address…”；`services/engine/tests/test_roof.py::test_triftstrasse_5_has_an_outline_planes_and_modules` | 票 #14 收口（轮廓 PNG + 该测试）。coverage D6 引擎探针 `found:true`、`building_id=DEBY_LOD2_5006493`、`address=Triftstraße 5`、坐标 48.140278, 11.588411，但轮廓叠加没拍到。本次线上没有 POST |
| R05 | 勾选或取消可用屋面，总数跟着变 | 实现未验 | 屋面列表的复选框 | 一个 `usable` 屋面的勾选 | 组件数与 kWp 合计应变化 | `RoofStep.tsx`；`plugins/linker-tools/src/configurator/roof/geometry.ts` | 无验收记录写过一次勾选改变合计 |
| R06 | 屋顶面板上始终可以手绘一个平面，再打包组件 | 实现未验 | 面板上的 “Draw a plane yourself”。绘制框一直在，不是没有轮廓才出现 | 多边形；倾角默认 35，朝向默认 180（南） | `POST /roof/pack`。过大或德国境外则拒绝。界限在 `models.py`：纬度 47.0–55.2，经度 5.8–15.1，`MAX_DRAWN_PLANE_M2 = 3000`，`RoofPackRequest.roof_sized` 超面积即拒。`RoofStep.tsx` 只有拒绝句 “Draw the plane on one roof: this one is too large or outside Germany.”，不执行界限。规格验收条要的是真实地址的 LoD2 轮廓，不是手绘 | `RoofStep.tsx` 第 92–93、412–414、532–549 行；`services/engine/src/linker_engine/models.py` 第 37–42、325–338 行；`app.py` `roof_pack` | 无验收记录走完手绘。c-fidelity 的 storybook e2e 不是验收记录 |
| R07 | “Use this roof” 把 kWp、屋面、地点和来源写回住宅输入 | 已验 | 屋顶面板的采用按钮 | `RoofSelection`：kWp、planes、location、modules、address、`source` 为 `lod2` 或 `drawn` | 住宅 kWp 被写成屋顶结果；随后计算带着这些屋面 | `ResidentialForm.tsx` 第 143 行附近；`residential/ResidentialPanel.tsx` | `docs/acceptance/2026-10-10/14/inputs-*-roof-applied.png` |
| R08 | 更换屋顶，或改回手填 kWp | 实现未验 | 已采用之后的 “Change roof” / “Enter kWp instead” | 点击 | 重新打开屋顶步，或清掉屋顶选择、恢复手填 kWp | `ResidentialForm.tsx` | 无验收把这两个按钮当动作走过。截图只证明采用后的摘要在 |
| R09 | 披露参考组件与未核实的排布假设 | 已验 | 屋顶面板的假设段；报告假设节 | 引擎返回的 `module`、`module_wp`、`licence`、`assumptions` | 组件型号、Wp、许可，以及五条未核实假设（平屋顶、最大倾角、北向、边距、组件间隙）。报告对无来源规则追加 `limit.unverified` | `roof/service.py` `ROOF_ASSUMPTIONS`；`report.py`；`docs/acceptance/2026-10-09/14/sources.md`；规格 14 第 7、22 行 | 票 #14 收口（轮廓结果含组件数与假设）；规格要求披露，收口的 PDF 含假设节 |
| R10 | 地图上写出排除原因（北向、过陡、平屋顶） | 实现未验 | 不可用屋面 | `excluded_reason` | 面上的原因句。常量本身的披露在 R09，本行是走过的排除 UI | `RoofStep.tsx`；`roof/geometry.ts` `exclusionText` | 无验收打开过一块被排除的屋面并核对原因句 |
| R11 | 无建筑、LoD2 不可用、手绘被拒、加载失败的状态句 | 实现未验 | 点击落空、503 `lod2_unavailable`、打包拒绝、地图加载失败 | 引擎错误种类 | `RoofStep.tsx` 的消息表 | `RoofStep.tsx` 状态联合与文案映射 | 无。e2e 只断言邮编中心的 `modules === 0`，那是引擎契约，不是这四句 UI |
| R12 | 手机：地图加底部抽屉；底栏在屋顶步隐藏 | 已验 | 48rem 以下进入屋顶步 | 无额外输入 | 抽屉卡。`MobileNavigation` 不显示。1440 桌面几何在该次改动中保持 | `RoofStep.tsx`；`MobileNavigation.tsx` | `docs/acceptance/2026-10-13/configurator-mobile/README.md` |
| R13 | 不采用就关闭屋顶步 | 实现未验 | 关闭控件 | 点击 | 回到住宅表单，kWp 保持手填 | `RoofStep.tsx` | 无验收记录 |
| R14 | 提交条与屋顶面板之间留 24px，不重叠 | 已验 | 屋顶面板打开时，在住宅提交条下方 | 无 | 1440 与 390 的测量：gap 24px，`overlaps: false`。修的是负边距把 24px 压成 6px | `docs/acceptance/2026-10-13/configurator-c-fidelity/EVIDENCE.md` §5a | 该文件 §5a，2026-10-13 |

## 不单列的边界

- 工商业没有加入、保存、设计报告：规格验收条不要求。见 C46。
- 电站 mailto 不落站内询盘记录：coverage D1 把 mailto 接受为提交。见 C50。
- 报告多出的 `storage`、`warnings` 两节：对应规格引擎响应里的定容与 `warnings[]`。见 C34。
- 旧引擎的单线图、组串枚举等路由：规格 14 的路由表没有它们。代理白名单也没有。不是本工具的缺项。
- 经济性、上网电价、CAPEX：规格写明不做，实现以缺席加披露句满足。见 C36。
- 2026-10-12 原型不在本仓库。不把“找不到原型文件”记成一行。

## 复刻前最需要再走一遍的五点

这五点是未在线上按客户路径再验的入口，不是本表之外的新功能。

1. `?step=roof` 与 `/design-canvas/` 的 301 不到达屋顶步。线上 HTML 无 `data-step`。`Mount.php` 不传查询。即便传了，`ResidentialPanel` 还要 `defaults.plz`，页面从不传。见 R02。
2. Genie size-hint 的 `configurator_url` 带了 `pv_kwp`、`annual_kwh`、`phase`、`backup`、`plz`，配置器不读。见 C06。矩阵归 #445。
3. 浏览器里点 Download PDF，还没有再验收。修复前的失败是 coverage D2（JSON 包裹，73 237 B）。修复后同一文件 §5bis 的实例 curl 已得到 `application/pdf`（EN 48837 B，DE 49529 B，头 `%PDF-1.4`）。未验的只是浏览器 Download 按钮，不是整条代理字节路径，也不是“修后只有单测”。本次健康检查 200 不证明这个按钮。线上未下载。见 C39。
4. 真实航拍上的 LoD2 轮廓，验收是 2026-10-10 的本地 t14。2026-10-15 因 WMS 不可达没有拍到叠加。本次没有点击线上屋顶。见 R04。
5. 全部加入的数量读回和保存到账户，验收是 2026-10-10 的本地 t14，切换后没有在线上再走。暂时无货从不显示（C25）。步骤栏停在第 1 步（C09）。手绘平面没有验收记录（R06）。
