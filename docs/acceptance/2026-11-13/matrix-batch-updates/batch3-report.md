# 营销 / 法务 / 联系 / 博客页面视觉与只读交互验收报告（Batch 3）

- **验收日期**：2026-11-13
- **验收环境**：生产站 `https://de-linker.com`（匿名访客只读访问，EN / DE 双语，1440×900 与 390×844）
- **仓库约束**：仅作只读验收与缺陷根因诊断，未修改任何仓库已跟踪文件；未提交任何联系表单、询盘、注册或发送邮件。
- **提案输出**：
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch3-rows.json`（112 条行更新提案）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/batch3-captures/`（14 张证据级截图）

---

## 一、验收范围与统计

本批从 `docs/acceptance/2026-10-22/full-site/page-matrix.json` 过滤出全部营销、法务、联系、文档库、博客索引与博客文章的 `interaction=pending` 行：

| 页面类别 | 独立 URL 数 | 矩阵行数（1440/390） | 机械加载失败 | `interaction` 更新 | `visual_review` 更新 |
| --- | ---: | ---: | ---: | --- | --- |
| 营销与文档库（Home / Solution×4 / Installer / EPC / About×2 / Services / FAQ） | 22（11 EN + 11 DE） | 44 | 0 | 43 `partially-verified` / 1 `partial-with-finding` | 35 `partially-verified` / 9 `partial-with-finding` |
| 联系与感谢（Contact / Thank You） | 4（2 EN + 2 DE） | 8 | 0 | 8 `partially-verified` | 8 `partially-verified` |
| 法务（Imprint / Privacy / Terms / Refund） | 8（4 EN + 4 DE） | 16 | 0 | 16 `partially-verified` | 8 `partially-verified` / 8 `partial-with-finding`（4 实显 + 4 潜在CSS） |
| 博客索引（Blog Index） | 2（1 EN + 1 DE） | 4 | 0 | 4 `partially-verified` | 4 `partially-verified` |
| 博客文章（20 篇 Blog Posts） | 20（10 EN + 10 DE） | 40 | 0 | 40 `partially-verified` | 32 `partially-verified` / 8 `partial-with-finding` |
| **合计** | **56** | **112** | **0** | **111 `partially-verified` / 1 `partial-with-finding`** | **87 `partially-verified` / 25 `partial-with-finding`** |

> **`interaction` 升级边界说明**：生产只读验收仅验证无副作用交互（页头桌面/手机菜单展开收起、EN↔DE 语言切换、页内锚点跳转与吸顶偏移、`<details>` 手风琴、受众/方案/工具 Tab 切换、Blog/FAQ/Genie 输入框只输入不提交、Contact 未提交编辑态切语言保留、博客检索 GET 与越界分页 301 跳转）。表单提交、Turnstile 验证、邮件投递、PDF 下载、Genie 模型发送与配置器流转仍保留为未覆盖边界，故不标 `pass`，统一标为 `partially-verified`（有明确缺陷的 `/de/fuer-installateur/@390` 标为 `partial-with-finding`）。

### 三轴执行统计

1. **机械轴（`tests/visual/layout-selfcheck.mjs`）**：56 页 × 2 视口 = 112 视图全量完成，0 加载失败、0 `image-broken`、0 `font-error`、0 整页 `horizontal-scroll`；`71` 条 `defect` 与 `361` 条 `review` 命中经 DOM 逐项复核后，确认为 **3 类真实布局/溢出缺陷**（其余属已裁定的叠层/缩放/全出血设计模式）。
2. **视觉轴（Playwright 协议全页截图 + `deepseek-flash` 识图 + DOM 复核）**：按 `tests/visual/README.md` 协议（禁动画/过渡/光标、`document.fonts.ready`、`img.loading="eager"` 与瞬时分段滚动触发懒加载）采集全部 112 张全页图并由 `deepseek-flash` 完成分段审查（106/112 返回有效识图结果，其余 6 视图 `/about/@1440`、`/de/@390`、`/de/danke/@1440`、`/de/fuer-epc/@390`、`/de/kontakt/@1440`、`/de/loesung/heimspeicher/@1440` 因模型空响应已补齐实时 Playwright DOM/CSS 全量负载核查并核对截屏）；所有视觉线索均经 DOM `getBoundingClientRect` / `getComputedStyle` / WCAG 对比度实测复核，筛除全部误报并实锤法务页 `"2713"` 转义损坏、DE 媒体英文残留、正文德语断词等缺陷。
3. **只读交互轴（Playwright Chromium）**：首轮 447/462 项通过；修正对隐藏响应式按钮（EPC `@1440` FAQ topic tabs 与 Installer `@1440` mobile switcher）与封面区内 `scrollY=700` 页头判定后，复测 `/about/`、`/de/ueber-uns/` chapter tabs、`/for-epc/` & `/de/fuer-epc/` `@1440` `<summary>` 与 workbench bar、`/for-installer/` & `/de/fuer-installateur/` `@1440` timeline/FAQ/input、10 个封面页 `scrollY=1600` 滚过封面后页头实底化、以及 12 对 EN↔DE 语言切换往返全部通过。

---

## 二、重点已知开放缺陷核查结论

| # | 已知缺陷 | 生产现状 | 源码根因与修复提案 |
| --- | --- | --- | --- |
| 1 | **DE Heimspeicher H1 断词 & 英文 planner 演示媒体**（`/de/loesung/heimspeicher/`） | **仍未完全关闭（OPEN, P2）** | **断词**：当前 `h1.lk-hero-title` 在 1440/390 下文字虽未折断，但 `getComputedStyle(h1).hyphens` 仍为 **`auto`**（继承自 `plugins/linker-commerce/content/windpress/site-base.css:37`），原因在于 `plugins/linker-commerce/content/windpress/marketing-rhythm.css:42-67` 收录了 `#tv-cs-page-v1 .lk-hero-title` 等却**遗漏了 `#tv-rs-page-v1 .lk-hero-title`**；此外正文 `<p>` 仍为 `hyphens: auto`，产生 `Batteriespei-cher-Paket`、`Hochvolt-Batte-rie-türme` 硬拆。<br>**媒体**：`#tool-pane-0`（`planner-de.jpg`）与 `#tool-pane-1`（`...-de-poster.webp`）已本地化，但 **`#tool-pane-2`（`03 · SUPPORT`）仍嵌入英文视频 `/wp-content/uploads/2026/09/linker-advisor-lookup-for-installers.mp4` 及英文封面**（同类英文 Genie 视频亦见于 `/de/loesung/gewerbespeicher/` `tool-pane-2` 与 `/de/fuer-installateur/`）。<br>**提案**：在 `marketing-rhythm.css:45` 补入 `#tv-rs-page-v1 .lk-hero-title`，并补充德语版 Genie 查询演示视频/封面。证据：`batch3-captures/defect-heimspeicher-de-1440.png`、`batch3-captures/defect-heimspeicher-de-390.png`、`batch3-captures/evidence-de-heimspeicher-toolpane2-en-video.png`。 |
| 2 | **粘性页头透字**（95% 白底 + blur，`findings.md:87`） | **已修复上线（RESOLVED）** | `plugins/linker-commerce/content/windpress/chrome.css:26` 已改为 `header#lc-header{position:sticky;top:0;z-index:1000;background:#fff;border-bottom:1px solid var(--proto-neutral-200)}`。生产实测 `/faq-download/`、`/de/faq-dokumente/`、`/blog/`、`/de/kontakt/`、`/hybrid-inverter-vs-ac-coupled-storage/` 在 `scrollY=700` 以及 10 个摄影封面页滚动离开首屏封面后（`scrollY=1600`），`header#lc-header` 均呈 `rgb(255, 255, 255)` 纯白实底、`backdropFilter: none`。证据：`batch3-captures/defect-sticky-_faq-download_-1440.png`、`batch3-captures/defect-sticky-_de_kontakt_-1440.png`。 |
| 3 | **DE 博客独立封面 `alt` 英文**（`batteriegroesse-heimspeicher-notstrom`、`innen-vs-aussen-akku-planung`） | **指定两篇已修复上线（RESOLVED）；另新发现 2 对（4 篇）封面 `alt` 为空（OPEN, P2）** | 生产 DOM 实测 `/de/batteriegroesse-heimspeicher-notstrom/` `alt="GoodWe Lynx Home F Hochvolt-Batterie"`，`/de/innen-vs-aussen-akku-planung/` `alt="Eine GoodWe-Batterie und ein Hybrid-Wechselrichter sind an der Außenwand eines Hauses montiert."`；前 8 对（16 篇）博客均有正确 EN/DE `alt`。<br>**新发现**：`/de/heimspeicher-notstrom-eigenverbrauch/` 与 `/de/gewerbespeicher-lastspitzenkappung-notstrom-skalierbarkeit/` 及英文原篇 `/residential-storage-backup-self-consumption/`、`/ci-storage-peak-shaving-backup-scalability/` 封面 `alt=""`。<br>**根因**：`plugins/linker-i18n/includes/CoverAlt.php:64-67` 依赖英文附件 `_wp_attachment_image_alt`，该 2 个媒体附件在 WP 媒体库中 alt 为空。<br>**提案**：在 WP 媒体库为上述 2 个附件补全英文 `_wp_attachment_image_alt`，触发 `CoverAlt::after_meta()`（`plugins/linker-i18n/includes/CoverAlt.php:102-108`）自动生成德语译文。 |
| 4 | **Contact 编辑态切语言丢输入** | **已修复上线（RESOLVED）** | `plugins/linker-commerce/includes/Contact/LanguageDraft.php` 与 `plugins/linker-commerce/src/contact-language/navigation.ts`（`build/contact-language.js`）已上线。生产实测 EN→DE (`@1440`)、DE→EN (`@390`) 及带 `?intent=product&source=...` (`@1440`) 切换语言后，`name`/`email`/`company`/`message`/`intent`/`consent` 全部完整保留。 |
| 5 | **DE Installer textarea placeholder `"Handbüchern"` 被裁**（`/de/fuer-installateur/`） | **未完全修复（OPEN, P2）** | `#installer-mobile-query` (`<textarea rows="3">`) 已通过 `tools/migrate/marketing-controls.py:86-103` 与 `marketing-rhythm.css:14-18` 在 390 下显示 3 行完整占位符；**但**原本仅在桌面端显示的 `#lki-hero-query` (`<input>`)，其页面内联移动端隐藏规则（`#installer-journal .lk-console-input-row{display:none}`）被 **`plugins/linker-commerce/content/windpress/marketing-rhythm.css:26-29` 无断点高权重规则 `#installer-journal .lk-hero-console .lk-console-input-row { display: grid; ... }` 覆盖复活**，导致 `@390` 下 `#lki-hero-query` 仍可见（可用宽 `328px` < placeholder 实测宽 `564.1px`），因 `marketing-rhythm.css:35-38` 设 `text-overflow: ellipsis` 而裁切 `"Handbüchern"`（`@1440` 下可用宽 `583px` 可完整显示）。<br>**提案**：将 `marketing-rhythm.css:26-38` 包裹在 `@media (min-width: 761px)`（或匹配页面自身移动端断点）内，使移动端仅显示 `#installer-mobile-query`。证据：`batch3-captures/probe-installer-de-clean-390.png`、`batch3-captures/probe-installer-de-clean-1440.png`、`batch3-captures/evidence-de-installer-390-tools.png`。 |
| 6 | **`services-audience-tabs-small`**（`/de/kundendienst/@390`） | **已修复上线（RESOLVED）** | `plugins/linker-commerce/content/windpress/marketing-rhythm.css:98-108` 与 `service-intro.css:208-211` 已覆盖旧 `10px/43px` 规则。生产 DOM 实测 `/de/kundendienst/@390` 两个 tab（`Für Solarinstallateure`、`Für gewerbliche EPCs`）均为 `font-size: 14px`、`height: 44px`、`min-height: 44px`，点击切换正常。证据：`batch3-captures/defect-kundendienst-de-390.png`。 |

---

## 三、本轮确认缺陷总表（含新发现缺陷、根因与修复提案）

### D1 · P1（内容转义损坏）：`/refund-returns/` 与 `/de/rueckgabe-erstattung/` 第 4 节列表项显式输出 `"2713"`（影响 4 个法务视图 + 4 个潜在视图）

- **实测现象**：视觉模型捕捉到第 4 节列表编号异常，DOM + CSS 探针实证：`/refund-returns/`、`/de/rueckgabe-erstattung/`、`/privacy-policy/`、`/de/datenschutz/` 4 个页面的内联 `<style>` 中 `content: "\2713"` 丢失反斜杠变成 **`content: "2713"`**（对比 `/imprint/`、`/de/impressum/`、`/terms-of-sale/`、`/de/verkaufsbedingungen/` 仍完整保留 `content: "\2713"`）。在 `/refund-returns/` 与 `/de/rueckgabe-erstattung/` 的 `#section-4` 下，3 个列表项 `<li>::before` 直接渲染为 `"2713"` 贴在首字母前（如 `2713Contact Linker...` / `2713Kontaktieren Sie Linker...`）；`/privacy-policy/` 与 `/de/datenschutz/` 当前 DOM 中无 `<li>` 命中该规则（`lis2713Count: 0`），属潜在 CSS 损坏。
- **证据**：`batch3-captures/evidence-de-refund-section4-1440.png`。
- **源码根因**：历史 `wp_update_post()` 写入法务页 `post_content` 时未包裹 `wp_slash()` 导致 CSS 转义符 `\` 被剥离（与 `findings.md:7` 隐私页 `\u003c` 同源；尽管 `tools/migrate/201-consent.php:257-260` 与 `tools/migrate/repair-legal-script.php:86-90` 后续已使用 `wp_slash()`，但此前落库的 `content: "2713"` 未修复）。
- **修复提案**：复用 `tools/migrate/repair-legal-script.php` 的事务 + `wp_slash()` 通道，将页面 `1038`、 `6698`、`1673`、`6827` 内联 `<style>` 的 `content: "2713"` 替换为 `content: "\2713"`（或直接改用 UTF-8 字符 `✓`），保存后执行字符级读回校验。

### D2 · P2（桌面横向溢出）：`/de/kundendienst/@1440` 与 `/services-support/@1440` Hero H1 超出 `950px` 容器（+41px / +13px）

- **实测现象**：`layout-selfcheck.mjs` 捕获 `h1.lk-hero-h1` `overflow-x-visible`；DOM 实测 `h1.lk-hero-h1` `max-width: 950px`（`right: 1046`），但其子元素 `<span class="service-hero-display">` 计算 `font-size: 108px`、`white-space: nowrap`，使 `"Technischer Rückhalt"` 宽 `990.8px`（溢出 **40.8px**）、`"Engineering backing"` 宽 `963px`（溢出 **13px**）。
- **证据**：`batch3-captures/evidence-de-kundendienst-1440-h1.png`。
- **源码根因**：页面内联规则 `#service-redesign .service-hero-display { font-size: clamp(59px, 7.8vw, 108px); white-space: nowrap; }` 在 `1440px` 视口达到 `108px` 上限且禁止折行，超出父级 `h1.lk-hero-h1` 的 `950px` 约束；`plugins/linker-commerce/content/windpress/marketing-rhythm.css` 未对其做兜底约束。
- **修复提案**：在 `plugins/linker-commerce/content/windpress/marketing-rhythm.css` 中为 `#service-redesign .service-hero-display` 调整桌面字号上限或允许在 `950px` 容器内自然折行（如 `font-size: clamp(56px, 7.1vw, 96px)` 或 `white-space: normal`）。

### D3 · P2（移动端组件溢出）：`/de/loesung/@390` 规模 Tab 文本 `.sol-tab-label` 溢出 `106px` 盒宽（+3px / +7px）

- **实测现象**：`layout-selfcheck.mjs` 捕获 `#sol-scale-tab-1`（`GEWERBLICHER SPEICHER`，`109px > 106px`）与 `#sol-scale-tab-2`（`GROSSSPEICHER`，`113px > 106px`）`overflow-x-visible`。
- **证据**：`batch3-captures/evidence-de-loesung-390-tabs.png`。
- **源码根因**：`plugins/linker-commerce/content/windpress/marketing-rhythm.css:150-156` 将 `.lk-arena-tag` 字号由原 10px 提升到 `14px`（`var(--proto-size-sm)`），但页面内联 `@media` 规则保留了 `#tv-solution-v1 .sol-tab-label { max-width: 106px; }`（按 10px 字号设计），导致单行全大写德语词 `GROSSSPEICHER` 在 14px 下超出 106px 框宽（尽管外层按钮已按 `marketing-rhythm.css:214-216` 堆叠为 `340px` 全宽单列）。
- **修复提案**：在 `plugins/linker-commerce/content/windpress/marketing-rhythm.css:214-216` 的 `@media (max-width: 760px)` 块内增加 `#tv-solution-v1 #arenas .sol-scale-tabs .sol-tab-label { max-width: none; }`。

### D4 · P2（已知未闭合）：DE Installer `@390` 桌面输入框复活并截断 `"Handbüchern"`（见第二节 #5）

- **根因**：`plugins/linker-commerce/content/windpress/marketing-rhythm.css:26-29` 无视断点覆盖了页面内联移动端隐藏规则。

### D5 · P2（已知未闭合与扩面）：DE Heimspeicher 断词规则遗漏 & 工具区英文视频 + 4 篇博客空 `alt`（见第二节 #1、#3）

- **根因**：`plugins/linker-commerce/content/windpress/marketing-rhythm.css:42-67` 遗漏 `#tv-rs-page-v1 .lk-hero-title`；`tool-pane-2` 仍指向英文视频资源；`plugins/linker-i18n/includes/CoverAlt.php:64-67` 依赖的两张博客封面附件本身无 `_wp_attachment_image_alt`。

---

## 四、视觉模型与机械探针误报复核记录

### 1. 视觉模型（`deepseek-flash`）误报复核（9 类假阳性，全部排除）

| 视觉模型线索（页面/视口） | 误报内容 | DOM / CSS / HTTP 实测复核结论 |
| --- | --- | --- |
| `/remote-monitoring-after-installation/@390`、`/residential-storage-backup-self-consumption/@390`、`/@390`、`/installer-handover-documentation-checklist/@1440` | “导航选中了 DE，但页面内容为英文” | DOM 实测 `documentElement.lang === "en-US"`，`EN` 链接带 `is-active` 与 `aria-current="true"`，`DE` 为 `null`；模型将移动端胶囊激活底线误判为右侧。 |
| `/de/innen-vs-aussen-akku-planung/@390`、`/de/installateur-checkliste-wechselrichter-akku/@390` | “Passende Beiträge 左侧配图为灰色占位框” | DOM 实测 `.tv-blog-single-related-img img` `naturalWidth=300, naturalHeight=382, opacity=1`，实为浅灰卡片底上的白色电池产品图。 |
| `/de/danke/@390` | “Nützliche Seiten 列表左侧图标为空白占位框” | DOM 实测为 `15×15` / `18×18` 绿色 `<svg>`（`opacity=1`）；0×0 仅来自桌面端隐藏导航 SVG。 |
| `/de/impressum/@1440`、`/residential-storage-backup-self-consumption/@1440`、`/imprint/@390`、`/size-battery-storage-residential-backup/@1440`、`/contact/@390` | “页脚法律链接/电话/目录导航对比度不足” | 实测计算 WCAG 对比度：`#64748b`/`#fff` = **4.76:1**，`#596e67`/`#fff` = **5.48:1**，`#12664f`/`#fff` = **6.80:1**，`#4c5861`/`#e8ebed` = **5.98:1**，全部满足 WCAG AA（≥4.5:1）。 |
| `/de/ueber-uns/@1440` (`einfacherumsetzen`)、`/de/@1440` (`Vonder`)、`/de/loesung/grossspeicher/@1440` (`Einsatzweck`)、`/de/kundendienst/@390` (`Zertifikate den`)、`/de/solar-speicher-inbetriebnahme-checkliste/@390` (`Firmwareund`)、`/de/batteriegroesse-heimspeicher-notstrom/@390` (`untersützung`)、`/faq-download/@1440` (`Soluitions`) | “德/英文单词连写缺空格或拼写错误” | DOM `textContent` 与 `plugins/linker-commerce/content/livecanvas/partials/de/footer.html:149` 源码均完全正确（`"einfacher umsetzen"`、`"Von der"`、`"Der Einsatzzweck"`、`"Zertifikate für den"`、`"Firmware und"`、`"Projektunterstützung"`、`"Solutions"`），属压缩长图 OCR 幻觉。 |
| `/hybrid-inverter-vs-ac-coupled-storage/@390` | “缺少可见 H1 主标题” | DOM 实测 `h1` 位于 `y=537px, 342×112.5px, color: rgb(21,53,47), opacity: 1`，系长图分段边界切割伪象。 |
| `/privacy-policy/@1440` | “第 2 节第 1 张卡缺失标题与正文” | DOM 实测 `#section-2` 后 `.lg-table-wrap` 高度 `1963px`、`textLen: 2211`，完整表格渲染正常。 |
| `/about/capability/@390` | “第 4 卡与 HARDWARE PORTFOLIO 间有 300px 空隙” | DOM 实测各 `<section>` 纵向坐标精确首尾相接（`919 → 1362 → 4031 → 4389 → 4835`），无异常留白。 |
| `/@1440`、`/for-installer/@1440`、`/for-epc/@1440`、`/de/fuer-epc/@1440` | “区块内部出现纯白/浅绿/纯黑空框” | 实为折叠 Tab 内的 `display: none` 懒加载图、暗调工业现场照片（`natW=2400`）或未播放首帧的 `<video>`（带合法 `poster`）；所有图片 URL `curl -I` 均为 HTTP 200，`layout-selfcheck.mjs` 报 `0` `image-broken`。 |

### 2. 机械探针（`layout-selfcheck.mjs`）已裁定设计模式记录

以下 `layout-selfcheck.mjs` 命中项经 `docs/acceptance/2026-10-22/full-site/page-visual-selfcheck.md` 口径与本次 DOM 坐标复核，确认为既定视觉设计（非缺陷）：
- `/about/capability/` & `/de/ueber-uns/leistungsfaehigkeit/` & `/for-epc/` & `/de/fuer-epc/`：`active-center` 评价卡片 `scale(1.02)` 强调裁切；
- `/about/` & `/de/ueber-uns/` & `/for-epc/` & `/de/fuer-epc/` & `/solution/residential-storage/` & `/de/loesung/heimspeicher/` & `/solution/utility-storage/` & `/de/loesung/grossspeicher/`：`.mt-visual` / `.bg` / `.rs-contact-photo` / `.us-engineering-visual` 分层背景叠加；
- `/blog/` & `/de/blog/`：`.journal-feature-image` 与 `.journal-feature-copy` `grid-area: 1/1` 图文叠加；
- `/for-installer/` & `/de/fuer-installateur/@390`：`.lk-tool-route` 390px 全出血破框；
- `/faq-download/` & `/de/faq-dokumente/@390`：`.linker-library-main` 20px 全出血横滚轨；
- `/services-support/` & `/de/kundendienst/@390`：`.service-stage-side` 为预留 2px+4px 焦点环所设 `-8px` 负外边距（`marketing-rhythm.css:532-533`）。

---

## 五、资源回收记录

- 临时 Playwright / Python 脚本 `tests/e2e/batch3-*.tmp.*`、临时全页截图目录 `/tmp/batch3-screens/` 以及中间合并 JSON/目录（`selfcheck/`、`selfcheck-p1/`、`selfcheck-p2/`、`full-accept-*.json`、`known-defects-probe*.json`、`followup-*.json`、`dom-*.json`、`final-checks*.json`、`de-hyphen-*.json`、`vision-review.*`）已全部清理，仅保留 `batch3-rows.json`、`batch3-report.md` 与 `batch3-captures/` 下 14 张证据截图。
