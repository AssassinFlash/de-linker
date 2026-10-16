# M2 文案批次 · 工具改名收官 + 禁词 cart/Warenkorb · 对抗评审记录

规则依据（AGENTS.md）：§3 用词（产品/产品分类；不说目录 catalogue、文章 article、篮子
basket/cart）与 §1 工具定名（Genie - Linker's AI assistant / Genie – der KI-Assistent
von Linker、Solution Configurator / Lösungskonfigurator；德语 Sie 体，de_DE_formal，禁
"不是…而是…"）。文案基准：linker-copywriting Hard Stops 1–9 与 25 条反模式、术语以
`plugins/*/languages/*.po` 与线上既有措辞为准。营销页文案冻结——本批只动工具名、被裁定的
旧工具名遗留、以及被禁词词表命中的串，不改其余句子。

证据基线：本地实例 `~/de-linker-local/t73`（快照 2026-10-15，与线上同内容；逐串已用
`ssh hostinger-de-linker` + WP-CLI 在线上回读核对，全部 1:1 命中）与线上
`de-linker.com` 的实时 HTML。命令与逐条计数见文末《评审证据》。

---

## 一、逐条评审（初稿 → 评审意见 → 定稿）

### 1. 首页 utility 卡第 4 项符号（post 13 EN / 6913 DE）— 禁词修正

- 初稿 EN：`Project quotes sized to the site`；初稿 DE：`Projektangebot pro Standort`。
- 评审：**修改（EN）**。旧句的犯规成立（禁词 cart + 反模式 19 否定句），但初稿 EN
  "Project quotes **sized** to the site" 的主语错位——被"设计/选型"的是系统，不是报价；
  复数 "quotes" 又暗示多份文件。卡片里它是四条中唯一一条"怎么买"的符号，其余三条是名词
  短语，单数名词短语读起来才并列。DE 初稿照旧句的正半句（`Angebot pro Standort`）走，无
  可挑。HTML 无实体，卡片覆层芯片已有 "Project quote"，故本符号只补"每个站点单独报"这一
  条事实。
- **定稿 EN**：`<li>A project quote for each site</li>`
- **定稿 DE**：`<li>Projektangebot pro Standort</li>`
- 备选（若业主偏好"项目"一词）：EN `A project quote per site`，DE `Projektangebot je Standort`。

### 2. SEOPress meta 描述（1755 EN / 6917 DE）— 禁词修正

- 初稿 EN：`…, quoted as a project for your site.`；初稿 DE：`…und Projektangebot für Ihren Standort.`
  评审：**修改**。旧句的正半句本身就是站内已用措辞（utility 页图层 alt 两处
  "quoted per project through Linker"），去掉否定半句即可，不必另造新短语；meta 少 20 字
  也更少被截断。DE 的 `projektbezogen angeboten` 是线上既用词（6917 自身旧 meta、6871、
  6909、6913、6919 均在用），与 EN `quoted per project` 严格互镜。旧 DE 161 字符已超 160
  上限，定稿 136。
- **定稿 EN**（107 字符）：
  `CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project.`
- **定稿 DE**（136 字符）：
  `Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten.`

### 3. privacy 1673 EN（法律页表格，与 6827 镜像）

- 初稿：`the Advisor`→`Genie`；`Advisor messages`→`Genie messages`；
  `Advisor conversations`→`Genie conversations`；`the Advisor's history`→`Genie's history`；
  CSS 注释内 "the Advisor button" 顺手清。
- 评审：**修改**。四处判定：① `ask Genie a question` 通过（与 DE 镜像同形）；②
  `Genie messages` 否决——正文里它与 `Genie conversations` 都可被读成"Genie 发出来的东西"，
  而这段话讲的是**访客数据**去了哪里；改 `your messages to Genie`（DE 同改
  `Ihren Nachrichten an Genie`）。③ `the Advisor's history` 否决——同页已写明会话
  "saved to the account"，把"历史"挂在 Genie 名下与同页自述矛盾；改 `your Genie history`。
  ④ 初稿漏了同一句表格的**可见** `<caption>`：`put to the Genie`（#12 的机械规则
  "the Linker Advisor → the Genie" 留下的冠词残渣——助手名不带冠词），本批必须一起改。
  注释串采纳（不可见，只为让收官的 grep 干净）。
- **定稿**（逐串见文末表 E 组）：`When you ask Genie a question` ·
  `not sent with your messages to Genie` · `Conversations with Genie belonging to a signed-in
  account` · `from your Genie history` · `put to Genie` · 注释 `the Genie button` /
  `the Genie zone` / `Genie button zone`。

### 4. datenschutz 6827 DE（与 1673 镜像）

- 初稿：`Linker Berater`（th）→`Genie`；`Wenn Sie dem Berater eine Frage stellen`→`…Genie…`；
  `nicht mit Berater-Nachrichten übermittelt`→`nicht mit Genie-Nachrichten…`；
  `Berater-Konversationen`→`Genie-Konversationen`；`aus dem Verlauf des Beraters löschen`→
  `aus dem Verlauf von Genie löschen`。
- 评审：**修改**。① `Linker Berater`（th）**不属于本批**——#12 的 NAME_RULES_DE 已覆盖
  （实跑 plan 见证据 3），M2 重复写会让两条迁移互相吃掉；② `Wenn Sie Genie eine Frage
  stellen` 通过；③ `Genie-Nachrichten` 否决（同 3② 的方向歧义），改
  `nicht mit Ihren Nachrichten an Genie übermittelt`；④ `Genie-Konversationen` 否决，改
  `Konversationen mit Genie`（保留 `Konversation` 一词——本页自用，不改工具 UI 的
  "Gespräche"，那是另一层的词）；⑤ `aus dem Verlauf von Genie löschen` 否决，改
  `aus Ihrem Genie-Verlauf löschen`（属主是账户，且 DE 复合词比 `Verlauf von Genie` 自然）。
  注释串与 1673 同步清（否则两份镜像的 CSS 块不再逐字相同）。
- **定稿**：见文末表 E 组。

### 5. services-support 2748 EN（h3 / tab / aria / deliverable 共 5 处）

- 初稿 h3：`Solution Configurator Sizing & Compatibility Lists`；tab/aria 用 `Configurator Sizing`。
- 评审：**修改**。理由三条：① 同一列表的另四条表头都是**阶段名**（Digital Planning Tools ·
  Certificates for Grid Approval · Installation and Startup Support · Warranty and Continued
  Support），唯一带工具名的旧串 `Planner Sizing…` 正是不一致的那条；塞进四词工具名（50 字符）
  与邻条（22/30/32/30 字符）不再同调，且初稿"tab 用 Configurator Sizing"在英文里是两个名词硬拼，
  "Configurator Sizing" 会被读成"配置器的尺寸"。② 本页自己的媒体标签已写
  `02 · SIZING`，站点既有词是 **System Sizing**（826 的同型芯片 `Solution Configurator ·
  System Sizing`、页面徽章 `System Sizing`）。③ 工具名不会丢：本页 stage 01 的芯片是
  `Solution Configurator · Genie`，导语句也点了两个工具。故用站内既有词，不用工具名。
- **定稿**：`<h3>System Sizing &amp; Compatibility Lists</h3>` ·
  `aria-label="System sizing and compatibility lists"` ·
  `<b>System Sizing and Compatibility Lists</b>` ·
  `<h3 class="lk-sstage-h3">System Sizing and Compatibility Lists</h3>` ·
  `<strong>Deliverable:</strong> System Sizing · Complete Parts List`
- 否决的备选：初稿的工具名版（阶段名里唯一带工具、且太长）；`System Sizing &amp; Compatibility
  Lists` 之外的 `Sizing &…` 也不取（丢掉与页面标签同根的 System 限定）。

### 6. service-support 6700 DE（与 2748 镜像）

- 初稿 h3：`Auslegung im Lösungskonfigurator & Kompatibilitätslisten`；deliverable：
  `Auslegung im Lösungskonfigurator · Vollständige Stückliste`。
- 评审：**修改**，理由同第 5 条。德语站既有词 `Systemauslegung`（6867 可见标签
  `01 · Systemauslegung & Architektur`、6919、6875/6877 检索点），与页面媒体标签
  `02 · AUSLEGUNG` 同根；56 字符的工具名版会把五个阶段标题读成四个阶段加一个工具广告。
  `Stückliste` 按 AGENTS §3 保留。
- **定稿**：`<h3>Systemauslegung &amp; Kompatibilitätslisten</h3>` ·
  `aria-label="Systemauslegung und Kompatibilitätslisten"` ·
  `<b>Systemauslegung und Kompatibilitätslisten</b>` ·
  `<h3 class="lk-sstage-h3">Systemauslegung und Kompatibilitätslisten</h3>` ·
  `<strong>Ergebnis:</strong> Systemauslegung · Vollständige Stückliste`

### 7. for-installer 826 EN（ROOF & PV PLANNING 阶段卡）

- 初稿：`The Roof detail step maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.`
- 评审：**通过**。与 #12 在同页已写定的主语式严格同形（`The Roof detail step maps the
  layout, …`、`Open the Roof detail step →`），冠词与大小写（"Roof detail step"）一致；本卡标
  题上方已有 `Solution Configurator – Roof detail`，句内不必再点工具。无实体、无禁词，
  长度与旧句相同（替换只动了主语）。
- **定稿**：同初稿。

### 8. loesung 6871 DE（2 处复合/裸用）

- ① `Der Planer modelliert geeignete …` → 初稿 `Der Lösungskonfigurator modelliert …`。
  评审：**通过**。EN 镜像 746 同段第二句就是
  `The Solution Configurator models suitable inverter and battery combinations…`（#12 已改定），
  德语保持同一句式；`Der` 配 `Lösungskonfigurator` 格正确。
- ② 表格单元 `Speicherpakete, Planer-Werkzeuge und Partnerpreise` → 初稿
  `Speicherpakete, Auslegungswerkzeuge und Partnerpreise`。评审：**通过**（并采纳"避开邻格
  `Planungswerkzeuge`"的理由）。`Auslegungswerkzeuge` 是线上德语既有词（6863：
  "Linker stellt vor der Bestellung Auslegungswerkzeuge und Verdrahtungsunterlagen bereit"）。
  **但缺 EN 镜像**：746 同格仍写 `Storage packages, Planner tools, and Partner pricing`
  （#12 的规则不含裸 `Planner`，实跑 plan 报 "no change"），本批必须同改，EN 对
  `sizing tools`（932 的线上英文既有词："Linker provides sizing tools and wiring references
  before the order"）。见文末"评审新增"第 12 条。
- **定稿**：`Der Lösungskonfigurator modelliert geeignete` ·
  `<td>Speicherpakete, Auslegungswerkzeuge und Partnerpreise</td>`（并入第 12 条 EN 对）。

### 9. faq-download 6863 DE CTA

- 初稿：`Linker Berater öffnen` → `Genie öffnen`；`href="/de/produkte/"` → `/de/genie/`。
- 评审：**修改**。三点：① 文案本身**不归本批**——#12 的 NAME_RULES_DE（`Linker Berater`
  → `Genie`）已生成 `Genie öffnen`（实跑 plan 证据 3）；M2 再写一遍会吃重复。② href 改向
  成立，但必须**连 EN 镜像一起改**（932 `href="/products/"` → `/genie/`），否则英德两个同型
  按钮的 no-JS 兜底指向不同语义；按钮文案说 "Open Genie"，兜底就该落在 Genie 自己的页
  （`/genie/`、`/de/genie/` 均为线上既有地址）。③ 需知悉：这条 CTA 所在的
  **post_content 已经不再渲染**——FAQ 页由 lc_dynamic_template 6969/6970 渲染
  （仓库文件 `plugins/linker-commerce/content/livecanvas/faq_page.html` 与 `de/faq_page.html`），
  页面 HTML 里已无 `rd-` 标记、H1 出自模板；FAQ 数据出自
  `plugins/linker-commerce/data/faq-trade.json`。所以这是"收官 grep 干净"的卫生修正，不是
  可见修复（可见面已干净）。
- **定稿**（只列 M2 应新增的两个 href 对）：见文末表 A 组第 18、19 行。

---

## 二、评审新增条目（初稿未覆盖，同一犯规或同一收官目标）

### 10. 746 EN `Design with Planner →`（可见 CTA，#12 规则漏网）

#12 的 NAME_RULES_EN 只有 `Design in Linker Planner →`，本串是 `Design **with** Planner`，
实跑 plan 对 746 报 "no change"。同页 DE 镜像（6871）的按钮 `Mit dem Linker Planer planen →`
由 #12 改成 `Mit dem Lösungskonfigurator planen →`，而该德语串与门店侧栏卡
（`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po`:1634
`msgstr "Mit dem Lösungskonfigurator planen"`）逐字相同，其英文源串是
`Plan with the Solution Configurator`。故英文按钮随之对齐，英德同义同长。
**定稿**：`Design with Planner →` → `Plan with the Solution Configurator →`

### 11. 792 EN `Model Project in Planner →`（可见 CTA）

同型漏网（#12 无裸 `Planner` 规则）。DE 镜像 6921 `Projekt im Linker Planer modellieren →`
由 #12 改成 `Projekt im Lösungskonfigurator modellieren →`，英文按 DE 的动作补足冠词。
**定稿**：`Model Project in Planner →` → `Model the project in the Solution Configurator →`

### 12. 746 EN 表格单元 `Storage packages, Planner tools, and Partner pricing`（第 8 条 EN 对）

理由见第 8 条②。`sizing tools` 取自 932 线上英文（`Linker provides sizing tools and wiring
references before the order`），与 DE `Auslegungswerkzeuge` 互镜。
**定稿**：`<td>Storage packages, sizing tools, and Partner pricing</td>`

### 13. 1673 EN 表格 caption `put to the Genie`（可见）

#12 把 `the Linker Advisor` 机械替换成 `the Genie`，留下工具名带冠词的残渣（先例：助手名前
一律不带冠词，见 `docs/acceptance/2026-10-10/12/copy-review.md` §10）。线上 EN 隐私页现在
就印着 `To answer a question put to the Genie, and to run the planning tools, …`。
**定稿**：`put to the Genie` → `put to Genie`

### 14. 1673 / 6827 CSS 注释内的 `Advisor`（不可见，随镜像一起清）

两份镜像的 `<style>` 里有 4 处英文注释（`the Advisor button` 1 处、`the Advisor zone` 2 处、
`Advisor button zone` 1 处）。不可见，但收官批的目标是让内容里不再有旧工具词汇；两份镜像
一起改，CSS 块才继续逐字相同。**定稿**：`the Genie button` / `the Genie zone` / `Genie button zone`。

### 15. 禁词 cart/Warenkorb 的同类残留（可见，初稿只修了首页与 meta）

词表依据：`plugins/linker-i18n/data/banned-de.json` 整词封禁 `Warenkorb*`/`Einkaufswagen*`；
AGENTS §3 禁 basket/cart；`docs/specs/11-commerce.md:117` 明写"全站可见文案无
order/checkout/payment/shipping/Versand/Kasse/Bezahlen/Warenkorb（引语除外）"。线上扫描
（见证据 2）在首页与 meta 之外还命中三处**可见**文案，全在营销/法律页面正文字里：

- **Application FAQ**（题面 "How does purchasing work for large, container-sized storage
  projects?"）：EN `…cannot simply be placed into an online shopping cart.` /
  DE `…lassen sich nicht einfach in einen Online-Warenkorb legen.` —— 与第 1 条同一犯规：
  禁词 + 反模式 19（回答"你们是不是网店"这个买家没问的问题）。改成正述：EN
  `are quoted per project.` / DE `werden projektbezogen angeboten.`，与第 2 条 meta 用词
  一致；句子尾巴（`They involve complex site engineering…`）逐字不动。
- **Privacy cookie 句**：EN `(session, cart, and login cookies)` /
  DE `(Session-, Warenkorb- und Login-Cookies)` → 用站点自己的名字（Lösungsentwurf）。
- **Terms of Sale 价格句**：EN `Volume tier prices apply automatically in the cart…` /
  DE `Mengenstaffelpreise werden im Warenkorb automatisch…` → 同一替换。

若本批只收"首页 + meta"，这三组（6 对）请从表里剔除**并写明是留给法务页批次的具名缺口**，
不要静默留白。

---

## 三、评审发现但**不**纳入本批（记录在案，需单独裁定）

1. **`catalogue` / `Katalog`**（AGENTS §3 禁"目录"，DE 词表整词封禁 `Katalog*`），四处可见：
   14 `<h3 class="tv-blog-resource-card-title">Browse the product catalog</h3>`；
   746 `when the package needs a quote beyond the catalog`；
   792 `Not rounded up from a product catalog.`（此句同时是反模式 3"截断式断句"+ 19，
   单换名词不解决句子本身）；6871 `wenn das Paket ein Angebot über den Katalog hinaus braucht`。
   建议连同 792 整句、由文案批次一并改；本记录不做定稿。
2. **privacy/terms 里的 `checkout` / `Kasse` / `Checkout`、`payment`、`shipping` / `Versand`**：
   1673、6827、1674、6825（法务页正文，涉及合同表述，例如 "Your checkout submission is a
   binding offer"）。另外营销页的 `Versand`（6913、6923、6921、6869、6867、6865、6863、
   6917）是"发货/物流"的事实词，与禁词清单里的**动作词**不同层。两类都超出本批授权
   （改名 + cart/Warenkorb），且改动等于重写法务句子，须业主或法务批次裁定。
3. **746 FAQ 答案里的 `you work directly with Linker` / DE `arbeiten Sie direkt mit Linker
   zusammen`**（Hard Stop 4 的删除测试：删掉 `directly` 句子照样成立 → 该词是焦虑；
  同页另有 `handles the manufacturer directly so you are not stuck in the middle` 与
  下一段 `You provide the site power needs, transformer setup, and schedule`，
   是 Hard Stop 9 Actor 的近亲形状）。营销页文案已冻结，改这些等于改冻结文案，故只记录。
4. **不可见旧词**（不影响交付，也不触发任何守卫）：1672 / 6829（Imprint）、1674 / 6825（Terms）、
   1038 / 6698（Refund）、3302 / 6693（配置器页退役 post_content）、749 / 792 / 6921 / 6923
   （模板里的 JS 注释 `Advisor remains the existing prototype route`）各有 `Advisor` /
   `Planner` / `Site detail` 注释串。若收官的 grep 要求全库干净，可把第 14 条的三对同一批
   扩到这 6 个法务页（同一批 4 处注释）；3302/6693 与 749 一族的注释属退役/应用层，建议留白。
5. **本地实例的 LC 层落后**：实例 6909（Kopfzeile）/6911（Fußzeile）/6881 里仍是
   `Linker Planer` / `Linker Berater` / `Linker Standortdetails`，而仓库
   `plugins/linker-commerce/content/livecanvas/partials/de/header.html` 与线上已是
   `Lösungskonfigurator` / `Genie`（实跑 plan 对线上 #6909/#6911/#6881 报 "no change"）。
   这不是本批的串，跑 `present`（或按部署流程重写 partial/模板）即对齐；本批的视觉验收
   截图前必须先做，否则页头页脚会带着旧名字进画面。

---

## 四、定稿字符串对（可进 12-site-chrome.py）

字段说明：`post_content` 取自 `wp post get <ID> --field=post_content`，`_seopress_titles_desc`
取自同名 postmeta。全部为库内实际存储形态（HTML 实体原样，例：`&amp;`、`·`、`→`）。
"次数"是旧串在该字段内出现的次数（1 = 字面量对；2 = 需按"替换全部"的规则处理）。

### A. 改名收官（初稿 1–9 的定稿）

| # | post | 字段 | 旧串（逐字） | 新串（逐字） | 次数 |
| --- | --- | --- | --- | --- | --- |
| 5 | 2748 | post_content | `<h3>Planner Sizing &amp; Compatibility Lists</h3>` | `<h3>System Sizing &amp; Compatibility Lists</h3>` | 1 |
| 6 | 2748 | post_content | `aria-label="Planner sizing and compatibility lists"` | `aria-label="System sizing and compatibility lists"` | 1 |
| 7 | 2748 | post_content | `<b>Planner Sizing and Compatibility Lists</b>` | `<b>System Sizing and Compatibility Lists</b>` | 1 |
| 8 | 2748 | post_content | `<h3 class="lk-sstage-h3">Planner Sizing and Compatibility Lists</h3>` | `<h3 class="lk-sstage-h3">System Sizing and Compatibility Lists</h3>` | 1 |
| 9 | 2748 | post_content | `<strong>Deliverable:</strong> Planner Sizing · Complete Parts List` | `<strong>Deliverable:</strong> System Sizing · Complete Parts List` | 1 |
| 10 | 6700 | post_content | `<h3>Planer-Auslegung &amp; Kompatibilitätslisten</h3>` | `<h3>Systemauslegung &amp; Kompatibilitätslisten</h3>` | 1 |
| 11 | 6700 | post_content | `aria-label="Planer-Auslegung und Kompatibilitätslisten"` | `aria-label="Systemauslegung und Kompatibilitätslisten"` | 1 |
| 12 | 6700 | post_content | `<b>Planer-Auslegung und Kompatibilitätslisten</b>` | `<b>Systemauslegung und Kompatibilitätslisten</b>` | 1 |
| 13 | 6700 | post_content | `<h3 class="lk-sstage-h3">Planer-Auslegung und Kompatibilitätslisten</h3>` | `<h3 class="lk-sstage-h3">Systemauslegung und Kompatibilitätslisten</h3>` | 1 |
| 14 | 6700 | post_content | `<strong>Ergebnis:</strong> Auslegung im Planer · Vollständige Stückliste` | `<strong>Ergebnis:</strong> Systemauslegung · Vollständige Stückliste` | 1 |
| 15 | 826 | post_content | `Site Detail maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.` | `The Roof detail step maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.` | 1 |
| 16 | 6871 | post_content | `Der Planer modelliert geeignete` | `Der Lösungskonfigurator modelliert geeignete` | 1 |
| 17 | 6871 | post_content | `<td>Speicherpakete, Planer-Werkzeuge und Partnerpreise</td>` | `<td>Speicherpakete, Auslegungswerkzeuge und Partnerpreise</td>` | 1 |
| 18 | 6863 | post_content | `href="/de/produkte/" data-linker-assistant-open` | `href="/de/genie/" data-linker-assistant-open` | 1 |
| 19 | 932 | post_content | `href="/products/" data-linker-assistant-open` | `href="/genie/" data-linker-assistant-open` | 1 |

> 6863 的按钮文案 `Linker Berater öffnen → Genie öffnen` **不列入**：由 #12 的
> NAME_RULES_DE 生成（实跑 plan 已打印该替换），M2 重复会互相吃掉。
> 932/6863 的 post_content 已不渲染（FAQ 页走 lc_dynamic_template 6969/6970），这两对是
> 卫生修正。

### B. 改名收官 · 评审新增（初稿漏网，同一犯规）

| # | post | 字段 | 旧串（逐字） | 新串（逐字） | 次数 |
| --- | --- | --- | --- | --- | --- |
| 20 | 746 | post_content | `Design with Planner →` | `Plan with the Solution Configurator →` | 1 |
| 21 | 792 | post_content | `Model Project in Planner →` | `Model the project in the Solution Configurator →` | 1 |
| 22 | 746 | post_content | `<td>Storage packages, Planner tools, and Partner pricing</td>` | `<td>Storage packages, sizing tools, and Partner pricing</td>` | 1 |
| 23 | 1673 | post_content | `put to the Genie` | `put to Genie` | 1 |
| 24 | 1673 | post_content | `the Advisor button` | `the Genie button` | 1 |
| 25 | 1673 | post_content | `the Advisor zone` | `the Genie zone` | 2 |
| 26 | 1673 | post_content | `Advisor button zone` | `Genie button zone` | 1 |
| 27 | 6827 | post_content | `the Advisor button` | `the Genie button` | 1 |
| 28 | 6827 | post_content | `the Advisor zone` | `the Genie zone` | 2 |
| 29 | 6827 | post_content | `Advisor button zone` | `Genie button zone` | 1 |

### C. 禁词 cart/Warenkorb（初稿 1、2 的定稿）

| # | post | 字段 | 旧串（逐字） | 新串（逐字） | 次数 |
| --- | --- | --- | --- | --- | --- |
| 1 | 13 | post_content | `<li>Quoted per site, not from the cart</li>` | `<li>A project quote for each site</li>` | 1 |
| 2 | 6913 | post_content | `<li>Angebot pro Standort, nicht aus dem Warenkorb</li>` | `<li>Projektangebot pro Standort</li>` | 1 |
| 3 | 1755 | _seopress_titles_desc | `CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project, not from the cart.` | `CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project.` | 1 |
| 4 | 6917 | _seopress_titles_desc | `Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten statt über den Warenkorb.` | `Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten.` | 1 |

### D. 禁词 · 评审新增（同类残留，见第 15 条）

| # | post | 字段 | 旧串（逐字） | 新串（逐字） | 次数 |
| --- | --- | --- | --- | --- | --- |
| 30 | 746 | post_content | `cannot simply be placed into an online shopping cart.` | `are quoted per project.` | 1 |
| 31 | 6871 | post_content | `lassen sich nicht einfach in einen Online-Warenkorb legen.` | `werden projektbezogen angeboten.` | 1 |
| 32 | 1673 | post_content | `(session, cart, and login cookies)` | `(session, solution draft, and login cookies)` | 1 |
| 33 | 6827 | post_content | `(Session-, Warenkorb- und Login-Cookies)` | `(Session-, Lösungsentwurf- und Login-Cookies)` | 1 |
| 34 | 1674 | post_content | `apply automatically in the cart` | `apply automatically in the solution draft` | 1 |
| 35 | 6825 | post_content | `werden im Warenkorb automatisch` | `werden im Lösungsentwurf automatisch` | 1 |

### E. 评审 3、4 条的隐私表定稿串（登记用，逐字）

| # | post | 字段 | 旧串（逐字） | 新串（逐字） | 次数 |
| --- | --- | --- | --- | --- | --- |
| 36 | 1673 | post_content | `When you ask the Advisor a question` | `When you ask Genie a question` | 1 |
| 37 | 1673 | post_content | `not sent with Advisor messages` | `not sent with your messages to Genie` | 1 |
| 38 | 1673 | post_content | `Advisor conversations belonging to a signed-in account` | `Conversations with Genie belonging to a signed-in account` | 1 |
| 39 | 1673 | post_content | `from the Advisor's history` | `from your Genie history` | 1 |
| 40 | 6827 | post_content | `Wenn Sie dem Berater eine Frage stellen` | `Wenn Sie Genie eine Frage stellen` | 1 |
| 41 | 6827 | post_content | `nicht mit Berater-Nachrichten übermittelt` | `nicht mit Ihren Nachrichten an Genie übermittelt` | 1 |
| 42 | 6827 | post_content | `Berater-Konversationen, die zu einem angemeldeten Konto gehören` | `Konversationen mit Genie, die zu einem angemeldeten Konto gehören` | 1 |
| 43 | 6827 | post_content | `aus dem Verlauf des Beraters löschen` | `aus Ihrem Genie-Verlauf löschen` | 1 |

**合计 43 对**（A 15 对 + B 10 对 + C 4 对 + D 6 对 + E 8 对）。五组之间互不重叠，也不与 #12
的任何 pair 重叠；唯一相邻处是 6863：文本归 #12，属性归 M2。

**落库形态两条注记**：
- 次数为 2 的只有 `the Advisor zone`（1673 / 6827 各 2 处，同一串）。`Step.pairs` 是"必须恰好
  命中 1 次"的字面量通道，这一对要进 `rules`（任意次数、按序替换）那一列；其余 42 对全部
  命中 1 次，可直接进 `pairs`。同一字段里 **替换顺序有讲究**的两组：1673 的
  `Advisor conversations belonging…` 必须先于任何裸 `Advisor conversations` 规则（本表无裸串，
  安全）；6827 的 `Berater-Konversationen, die…` 同理。
- 长度核对（约束：项目符号 / CTA / meta 描述 ≤160 字符；h3 无硬限但同列表须同调）：
  新 meta 1755 = 107、6917 = 136（旧 6917 为 161，已超限，本批顺带压回）；
  新符号 13 = 29、6913 = 27（同卡另三条 38/39/42 与 41/58/46，新串最短但并列成立）；
  新 CTA 746 = 37（同区按钮 21–33，本区最长但同为一行）、792 = 48（同页按钮 19–35，
  与德语镜像 `Projekt im Lösungskonfigurator modellieren →` 44 同构——两处都保留全名，
  因为同页/同区按钮重复出现全名是站点既有做法：792 上已有
  `Open the Solution Configurator →` 33 与 `Start in the Solution Configurator →` 35）；
  新 h3/tab 2748 = 35、6700 = 39（同列表另四条 EN 22/30/32/30、DE 26/32/41/34，
  处在中位，不再是最长的工具名串）；826 新句 132 字符（与旧句逐字同长，只换主语）；
  746 表格单元 51 / 6871 的 53（同列另两格 54/58 与 58/58）。

---

## 五、评审证据

1. **旧串逐字回读**：`wp --path=~/de-linker-local/t73/wordpress post get <ID> --field=post_content`
   与线上 `ssh hostinger-de-linker 'wp --path=…/public_html post get <ID> …'`（本批涉及的
   13 / 6913 / 1755 / 6917 / 1673 / 6827 / 2748 / 6700 / 826 / 746 / 792 / 6871 / 6863 / 932）
   每个旧串在两侧都命中且计数相同；1755 / 6917 的 meta 与线上 `<meta name="description">`
   逐字相同（`curl https://de-linker.com/solution/utility-storage/` 与
   `/de/loesung/grossspeicher/`）。
2. **禁词扫描**（线上，published page/post/lc_partial/lc_dynamic_template，去 `<style>`/
   `<script>`/注释后计数）：`cart` 只命中 13、746、1035(`[woocommerce_cart]`)、18(href)、
   6962(类名/短代码)、1673(cookie 句)、1674(terms 句)；`Warenkorb` 只命中 6913、6871、
   6827、6825、18/6911(href `/de/warenkorb/`)；`catalog`/`Katalog` 命中 14、746、792、6871
   （另见第三节 1、2 的处理决定）。页头页脚的可视标签在线上已是 `Lösungskonfigurator` /
   `Genie`（本地实例的 partial 落后，见第三节 5）。
3. **#12 实跑计划**（`uv run --project tools/migrate python tools/migrate/12-site-chrome.py
   --wp "ssh hostinger-de-linker wp --path=…/public_html" plan`，只读）确认：
   - `#1673 / #2748 / #746(en) / #792(en) / #6827` 的**旧工具名共搭配对**已在线上生效
     （`privacy-policy-en #1673: no change`、`services-support-en #2748: no change`、
     `solution-en #746: no change`、`commercial-storage-en #792: no change`），
     本批命中的都是 #12 规则**不覆盖**的裸用/裸复合串；
   - `#6863` 的 `Linker Berater → Genie`、`#6827` 的 `den Linker Berater / Linker Berater`
     由 #12 生成，M2 不重复；
   - `#6909 / #6911 / #6881` 线上 "no change"（线上 LC 层已新），本地实例仍旧。
4. **渲染来源核对**：FAQ 页（932 / 6863）由 lc_dynamic_template 6969 / 6970 渲染
   （`SELECT ID, post_name FROM wp_posts WHERE post_type='lc_dynamic_template'` 与
   `plugins/linker-commerce/content/livecanvas/faq_page.html`、`de/faq_page.html`），
   线上页面无 `rd-` 标记、H1 为模板里的 `Antworten und Dokumente.`，FAQ 数据出自
   `plugins/linker-commerce/data/faq-trade.json`；配置器页（3302 / 6693）的挂载点是
   `plugins/linker-commerce/content/livecanvas/configurator_page.html` 的
   `[linker_configurator]`，页面 post_content 里的 `qcfg-*` 工作单标记已退役。
5. **对表自检**：脚本对 43 对逐条断言 `count(旧串) == 期望次数` 且 `count(新串) == 0`
   （在本地实例内容上），全部通过；`the Advisor zone` 两处为同一字符串，按 2 次规则处理。
6. **仓库侧门禁**：`just banned-words`（justfile）只覆盖 `catalogue|katalog`，且只扫仓库内的
   `plugins/linker-commerce/{content/livecanvas,templates,languages}` 与
   `plugins/linker-tools/content`；本批 43 对新串不含这些词，门禁不受影响（跑一次仍应
   "banned-words: clean"）。实例内容里的 `cart`/`Warenkorb` 残留在门禁范围之外——这正是
   本批存在的理由。
7. **新 href 目标存在**：`/genie/` 与 `/de/genie/` 在线上首页页头页脚的链接里各出现 3 次
   （`href="/genie/"`、`href="/de/genie/"`），且 `plugins/linker-tools/data/legacy-redirects.json`
   把 `/linker-advisor/`、`/linker-berater/` 301 指向它们；本地实例两者均 200。
   **观察**：本会话末段线上全站（含首页）连续返回 503（此前同一会话内均为 200，期间本线
   未对线上做任何写入）；若 503 持续，部署前需先确认站点恢复。

**未做**：本记录只写文档，未对线上或本地实例做任何写入。
