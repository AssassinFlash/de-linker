# #66 验收记录：对比页重建 / Advisor 跳转 / 文档库页

实例 `t66`（http://127.0.0.1:8930，库 `linker_t66`）：`just up t66` + 摘检出软链 + `just pull load t66 20261010-0033 --live-code`（`ok:true`、106 商品、2755 附件、0 缺失、0 线上地址残留）→ 插件换装（linker-* 指向检出，terravolt-b2b-core / linker-ai-assistant inactive 留盘，polylang/redis-cache 激活）→ `wp linker-i18n setup --assign` → `wp linker-commerce present` → 9-i18n 迁移（335 导入 / 330 同步 / 5 留译者）→ `just serve`。

## 1. 检查（命令与结论）

| 检查 | 命令 | 结果 |
|---|---|---|
| 静态检查（全链） | `just check` | exit 0（PHPCS/PHPStan ×4 项目、js lint/type/format、ruff/mypy ×6、pull/build check） |
| 测试（全链） | `just test` | 见 §4（commerce 662（14 skipped 集成）、tools 25、js unit+e2e、pytest ×5、pull 103） |
| 呈现安装 + WindPress 门 | `just wp t66 linker-commerce present --user=1` | `created 0, updated 2, unchanged 8`；`windpress: cache is newer than the templates/tokens and contains the template classes` |
| WindPress 编译 | `just windpress-compile t66` | 通过一次：`cache recompiled (1783954645 -> 1791717446), anchor classes present`；随后同一 CLI 驱动出现 store 等待超时（见 §4 已知限制），编译产物经插件自己的锚类检查复核为 `[]`（无缺失类） |
| 页面 200 | `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8930{/compare-products/,/compare-products/?ids=6521,6523,/de/compare-products/?ids=6521,6523,/faq-download/,/de/faq-download/}` | 全部 200 |
| 跳转 | `curl -o /dev/null -w '%{http_code} %{redirect_url}' …/{/linker-advisor/,/de/linker-berater/,/de/linker-advisor/}` | 301 → `/products/`、`/de/produkte/`、`/de/produkte/`；`/linker-planner/`、`/compare-products/` 仍 200（不误跳） |
| 地址规范化 | `curl … '/compare-products/?ids=6521,6521,6523,9999'`、`'?ids=1,2,3,4,5'`、`'?ids=abc'` | 302 → `?ids=6521,6523,9999`、`?ids=1,2,3,4&capped=1`、裸页 |
| 芯片与选择态 | 浏览器 `sessionStorage.setItem('linkerCompareIds','["6521","6523"]')` 后打开 `/products/` | 芯片由隐藏变可见，计数 `2/4`，`href=…/compare-products/?ids=6521,6523` |
| 真实夹具（装配层） | `php vendor/bin/phpunit --filter ComparisonLiveCatalogueTest` | 3 项通过：线上 89 件商品夹具的真实图值（4107 10 kW AC / 20 kW PV、1832 4.5/5.0 kWh、范围 5–25）经 `Comparison::of()` 与 ability 输出逐字段一致 |
| 真实夹具（库） | `php vendor/bin/phpunit --filter 'DocumentLibraryTest|LibraryPageTest|ComparePageTest|ComparisonTest'` | 全部通过（装配、去重、类型/语言归一、德语标签、空态、上限提示、行渲染） |
| 文案定稿落地（评审轮） | `grep -rn -i 'catalogue\|katalog' plugins/linker-commerce/content/livecanvas/{compare_page.html,de/compare_page.html}` | 无匹配（exit 1）：两文件的引导句都是 copy-review §1.2 定稿；模板文章 6933/6934 经 `wp post get` 读出同为定稿句（`Your selection stays…` / `Ihre Auswahl bleibt…`） |
| 重装（评审轮） | `just windpress-compile t66` 后 `just present t66` | 编译 `cache recompiled (1791718500 -> 1791721819), anchor classes present`（本轮一次通过）；呈现 `created 0, updated 0, unchanged 10`，`windpress: cache is newer than the templates/tokens…`：模板改动已进库 |
| 重装后的页面 | `curl -s http://127.0.0.1:8930/compare-products/ \| grep -o 'Tick up to four products[^<]*'`（DE 同法，`/de/compare-products/`） | EN/DE 各输出定稿句逐字（`just present t66` 之后） |
| DE 地址一致（评审轮修复） | `curl -o /dev/null -w '%{redirect_url}' 'http://127.0.0.1:8930/de/compare-products/?ids=6521,6521,6523'` | 302 → `…/de/compare-products/?ids=6521,6523`（修复前落 `/compare-products/`）；EN 同法仍 → `/compare-products/?ids=6521,6523` |
| DE 芯片与页内链接 | `curl -s http://127.0.0.1:8930/de/produkte/ \| grep -o 'data-compare-page="[^"]*"'`；DE 对比页 `grep -o 'href="[^"]*"[^>]*>\(Entfernen\|Vergleich leeren\)'` | 芯片 `data-compare-page="…/de/compare-products/"`；`Vergleich leeren` → 裸 `/de/compare-products/`，两条 `Entfernen` → `/de/compare-products/?ids=6523`、`?ids=6521` |
| 单元测试（评审轮） | `php vendor/bin/phpunit --filter ComparePageTest` | OK (9 tests, 34 assertions)——新增德语地址、德语表片段两个用例（`page_url`、芯片 `data-compare-page`、清除/移除链接全在 `/de/`） |

## 2. 视觉验收（截图，1440/390 × EN/DE）

浏览器：Computer Use（Playwright 驱动），未登录访客态（价格门按 #11：登录态截图里价格照常显示，访客态显示同一句提示，本次未单独出图，页面文案由 §2.2 的 .po 覆盖）。

| 文件 | 页面/状态 | 核对结论 |
|---|---|---|
| `compare-1440-en-selection.png` | EN 对比页，2 个商品 | 面包屑/标题/引导句/清除链接/表格（列头、Artikelnummer…、行）+「Continue browsing」+ 页脚 chrome 正常；无溢出、无遮挡 |
| `compare-1440-en-empty.png` | EN 对比页，空选择 | 空态一句 + 按钮，无空表 |
| `compare-1440-de-selection.png` | DE 对比页，2 个商品 | 标签德语（Anwendung / Phasen / Bemessungsleistung AC (kW) …），产品名与链接按德语 |
| `compare-390-en-selection.png` / `compare-390-de-selection.png` | 对比页 390 | 表格横向滚动（`overflow-x-auto`），标签列可见，无版面撑破 |
| `faq-1440-en-hero.png` / `faq-1440-de-hero.png` | 文档库页 hero | kicker/h1/引导句/三区锚点/四个承诺；EN 与 DE 各自成文 |
| `faq-1440-en-documents.png` / `faq-1440-de-documents.png` | 文档目录 | 按品牌分组（含计数），每行：类型 / 标题 / 覆盖商品 / 语言 / Download；159 行 |
| `faq-1440-en-trade-rules.png` | 下单前规则 | 16 条冻结问答，5 类，`<details>` 静态展开 |
| `faq-1440-de-answers-open.png` | 产品问答（DE，展开一条） | 按品牌分组、折叠列表；**问题文本为数据自带语言（本机只有英文 ACF 问答，#15 字段为空）**，见 §4 |
| `faq-390-en-hero.png` / `faq-390-en-documents.png` | 文档库页 390 | 单列堆叠，行内五项折行，可读 |
| `chip-1440-en-catalogue-selection.png` | 目录页 + 选择态芯片 | 左下浮动胶囊 `Compare 2/4`；目录页样式本身归 #16（本实例目录页是插件 PHP 模板，未在本票范围内） |
| `faq-390-de-hero.png` / `faq-390-de-documents.png` | 文档库页 DE 390（补格） | 与 EN 390 同取景：页顶 hero（含页头、三个区锚点、四个承诺）；`#documents` 段起点（`DOKUMENTATION / Finden Sie das Dokument.` + Chint/GoodWe 行）。单列堆叠，`gilt für …`、`Herunterladen` 可读 |
| `faq-1440-de-trade-rules.png` / `faq-390-de-trade-rules.png` | 下单前规则 DE，1440 / 390（补格） | 整段单幅（1440 1541 px、390 1841 px）：`BEVOR SIE BESTELLEN` + `Kaufmännische Regeln und Handelsbedingungen.`，5 类 16 条问句逐条可见（Bestellung & Lieferung 4 / Konten & Preise 2 / Versand & Logistik 3 / Garantie & Service 3 / Konformität & Dokumentation 4），末条与冻结内容一致（`über Genie verfügbar?`） |
| `compare-1440-de-empty.png` | DE 对比页空态（补格） | 整页 1105 px：面包屑/标题/引导句（§1.2 定稿逐字）+ 空态一句 `Wählen Sie Produkte aus, um ihre technischen Daten zu vergleichen.` + `Weiter einkaufen`，无空表 |
| `faq-1440-en-answers.png` | 产品问答区 EN（补格） | 整段单幅（13,914 px）：`PRODUCT ANSWERS` kicker + §3.3 定稿句（`…gathered by brand. For a question this list does not answer, ask Genie.`）+ 5 个品牌组 272 条折叠列表，首尾内容核对见下 |

**整页栅格的边界（本轮实测）**：DE 文档库页在 390 宽下高 51,634 px，超出浏览器单幅栅格的成功范围——51,634 px 的 `fullPage` 截图在末段重复页顶内容（不是 trade-rules 与页脚），26,000 px 视口的截屏在页坐标 49,000–51,000 段显示问答区内容（该段实际是 trade-rules 段，`#before-you-order` 在 390 下位于页坐标 49,039）。故 DE 390 一格沿用 EN 390 的取景约定（页顶 hero + `#documents` 段起点各一屏），trade-rules 段另以整段单幅交付；`faq-1440-en-answers.png`（13,914 px）与两幅 trade-rules（1,541 / 1,841 px）首尾内容（首行 kicker、末条问句）经逐条核对成立。

## 3. 文案与规格

- 文案对抗评审：`copy-review.md`（EN 先行、DE 独立撰写；线上既有德语逐字沿用；工具改名那一处只换名）。
- 规格与原生优先穷尽证明、目录卡/芯片集成点、附带修复：`docs/specs/19-tool-pages.md`。

## 4. 已知限制与留档（不在本票范围）

1. **本地快照缺商品特色图**：`SELECT COUNT(*) FROM wp_postmeta WHERE meta_key='_thumbnail_id'` = 0，而快照 dump 里有（`(45427,6528,'_thumbnail_id','6500')`，本机无 meta_id 45427）。对比表图片列因此为空，线上有图；代码路径与线上同一调用。归 #6 load/anonymize。
2. **德语产品的文档与问答数据**：文档与 FAQ 字段在英文商品上，目录读数走 #7 的孪生交换取源语言；`_linker_faqs` 在本机为空，问答回落产品自己的 ACF 问答（英文）。#15 字段落库后德语页读 `question_de`/`answer_de`。
3. **`just windpress-compile` 的 store 等待不稳定**：修复 LiveCanvas provider 的扫描响应损坏（spec §6）后有一次完整成功（31s，锚类全过）；此后同一配方出现 `no cache store within 300s`（浏览器 worker 仍报 `o.contents is not iterable`，即某次 provider 响应体不可解析——本机 PHP 内置服务器并发 8 路 provider 扫描、单响应最大 2 MB 量级）。缓存内容经插件自己的 `missing_anchor_classes()` 复核为 `[]`，且 mtime 晚于所有模板/`tokens.css`，`present` 的门通过；配方本身的偶发超时留档给 #5/#16 的工具线，不在本票范围。
4. **页头/页脚的三处 `[linker_contact_link]`**：旧插件短代码在线上 partial 里按原文输出，归 #12/#16 的 chrome 线。
