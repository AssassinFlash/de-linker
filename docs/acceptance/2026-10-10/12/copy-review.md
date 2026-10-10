# #12 工具文案对抗评审记录

规则（AGENTS.md）：工具名 Genie - Linker's AI assistant / Genie – der KI-Assistent
von Linker、Solution Configurator / Lösungskonfigurator；德语 Sie 体、
de_DE_formal、禁 "不是…而是…" 与三连排比；营销正文冻结——本记录只改工具名与
工具卡句。每处：初稿 → 评审意见 → 定稿。定稿即 `tools/migrate/12-site-chrome.py`
里的字面量。名与链（机制替换）不逐条列：EN `Linker Advisor`→`Genie`、
`Linker Planner`→`the Solution Configurator`（介词后带 the、主语位 The）；
DE `Linker Planer`→`Lösungskonfigurator`（冠词随格保留）、`Linker Berater`
各格并 article 删除（"der/den/dem Linker Berater"→"Genie"）。

## 1. 页头工具卡 · Genie 名

- EN 初稿：`Genie - Linker's AI assistant`。评审：AGENTS 定名的逐字形式
  （连字符），不动。**定稿**：`Genie - Linker's AI assistant`。
- DE 初稿：`Genie – der KI-Assistent von Linker`。评审：AGENTS 定名（en
  dash），德语不写 "Linker Genie" 连写；无商标注册。**定稿**：
  `Genie – der KI-Assistent von Linker`。

## 2. 页头工具卡 · Genie 描述（原 Advisor 卡句改名续用）

- EN 初稿：`Bring a model, a compatibility question or a project detail. Genie
  finds the next useful step.`
  评审：旧句 "Bring a model, compatibility question or project detail. Linker
  finds the next useful step." 只需补冠词与改名；两个并列名词短语、无排比腔。
  接受初稿。**定稿**：同初稿。
- DE 初稿：`Bringen Sie ein Modell, eine Kompatibilitätsfrage oder ein
  Projektdetail ein. Genie findet den nächsten nützlichen Schritt.`
  评审：旧句以 "Linker findet…" 收尾，改为 Genie 后主语明确；Sie 体；无
  "nicht…sondern"。接受。**定稿**：同初稿。

## 3. 页头工具卡 · Solution Configurator 描述（须含 Roof detail 句）

- EN 初稿：`Turn your goal, site and equipment into a complete solution with a
  bill of materials — the Roof detail step adds the building layout.`
  评审：破折号连接读作一句，卡片文案两短句更清晰；"bill of materials" 是
  §3 定名（Bill of materials / Stückliste），保留；"building layout" 改属格
  "the building's layout" 更自然；动词 Bring 与 Genie 卡的 Bring 重复——
  保留重复是刻意的（两卡同构）。**定稿**：`Bring your goal, site and existing
  equipment into a complete solution with a bill of materials. The Roof detail
  step adds the building's layout.`
- DE 初稿：`Konfigurieren Sie aus Ziel, Standort und vorhandener Ausrüstung
  eine vollständige Lösung mit Stückliste. Der Schritt Dachdetails erfasst
  die Gebäudefläche.`
  评审："Gebäudefläche" 不是惯用词；屋顶步在地图上描绘屋顶，用 "nimmt die
  Dachfläche auf"（satellite map 语境也是 aufnehmen）；第一句换成与 EN 平行
  的 zusammenführen 句式，Sie 体。**定稿**：`Führen Sie Ziel, Standort und
  vorhandene Ausrüstung zu einer vollständigen Lösung mit Stückliste zusammen.
  Der Schritt Dachdetails nimmt die Dachfläche auf.`

## 4. 页头移动菜单 · 配置器行描述

- EN 初稿：`Configure a complete solution with a bill of materials. The Roof
  detail step adds the layout.`
  评审：桌面卡句的短版（移动行一短句截断），尾句 "adds the layout" 比
  "adds the building's layout" 省一格仍通顺。**定稿**：同初稿。
- DE 初稿：`Konfigurieren Sie eine vollständige Lösung mit Stückliste. Der
  Schritt Dachdetails nimmt die Dachfläche auf.`
  评审：与桌面卡同构的短版。**定稿**：同初稿。

## 5. 页脚 planning 区链接名

- EN/DE 定稿：与卡名一致的全名（`Genie - Linker's AI assistant` /
  `Solution Configurator` / `Genie – der KI-Assistent von Linker` /
  `Lösungskonfigurator`）。评审：链接行比旧名（Linker Advisor，13 字符）
  长，390px 下靠 flex 换行——视觉验收核对；Blog 链接不是工具，保留；
  计数徽章 04→03。

## 6. 助手页 noscript 文案

- EN 初稿：`Genie needs JavaScript to run. Without it, browse our products or
  write to sales@de-linker.com and a specialist will answer.`
  评审：只改名，其余旧句成立（邮箱是 §6 允许的公司自有邮箱）。**定稿**：
  同初稿。
- DE 初稿：`Genie benötigt JavaScript, um ausgeführt zu werden. Ohne dieses
  können Sie …`
  评审：`um ausgeführt zu werden` 生硬，改 `um zu funktionieren`；`Ohne
  dieses` 指代弱，改 `Ohne JavaScript`；句尾 "und ein Spezialist wird
  antworten" 的 werden-Futur 冗余，改 "`; ein Spezialist antwortet Ihnen.`"；
  旧德语页的产品链接指到英文 `/products/`，改指 `/de/produkte/`。
  **定稿**：`Genie benötigt JavaScript, um zu funktionieren. Ohne JavaScript
  können Sie <a href="/de/produkte/">unsere Produkte</a> ansehen oder an
  sales@de-linker.com schreiben; ein Spezialist antwortet Ihnen.`

## 7. 工具页标题与浏览器标题

- post_title 定稿：`Solution Configurator` / `Lösungskonfigurator` /
  `Genie - Linker's AI assistant` / `Genie – der KI-Assistent von Linker`
  （slug 全部不动；H1 由主题的页面标题渲染，随改名自动正确）。
- SEO 标题初稿：`Configure a Storage System and Get a Price | Linker` 保留。
  评审：Get a Price / Nettopreise einsehen 是价格承诺；#11 起价格为伙伴
  登录后可见，对访客该承诺过宽（Law：承诺须可执行）。收窄。**定稿**：
  `Configure a Storage System | Linker` /
  `Speichersystem konfigurieren | Linker`。助手页 SEO 标题不提工具名、内容
  仍准确，保留。

## 8. 配置器旧 app 内静态求助链接

- EN `not sure? ask Linker Advisor` → **`not sure? ask Genie`**；
  DE `unsicher? Linker Berater fragen` → **`unsicher? Genie fragen`**。
  评审：仅静态标记文本；bundle 的 i18n 覆盖随 #14 重建消失。

## 9. Site Detail 折叠（For Installer 工具切换器 · Services & Support · Application）

- 评审基准：票面"Site Detail 的卡改为配置器的 Roof detail 功能描述"。
  For Installer 三槽位保留（冻结布局），第一槽改为配置器的屋顶步：
  tab `01 Roof detail / 01 Dachdetails`，H3 `Solution Configurator – Roof
  detail / Lösungskonfigurator – Dachdetails`，CTA `Open the Roof detail
  step → / Dachdetail-Schritt öffnen →`，href 直达 `?step=roof`；槽二
  `02 Configurator`、槽三 `03 Genie`。三工具句改两工具句：
  EN `Two Linker tools to prepare the installation before you order.`；
  DE `Zwei Werkzeuge für Ihr eigenes Tempo: … im Lösungskonfigurator, und
  fragen Sie Genie …`。Application 页工具标签 `Site Detail:`→`Roof detail:`、
  `Linker Standortdetails:`→`Lösungskonfigurator, Schritt Dachdetails:`，
  卫星图句以 "The Roof detail step / Der Schritt Dachdetails" 为主语。
  aria/alt 同步（无 "Linker Site Detail" 残留）。

## 10. 其余名替换的语法裁定（规则表依据）

- EN 主语位补 The（"Linker Planner sizes" → "The Solution Configurator
  sizes"），介词后补 the（"sized in Linker Planner" → "sized in the
  Solution Configurator"）；旧句中 "the Linker Planner"（S&S）与 SEO 描述
  里 "The Linker Advisor"（主语）各设显式规则，避免 "The Genie"。
- DE 冠词随格：im/dem/den/der Linker Planer → im/dem/den/der
  Lösungskonfigurator；Berater 并格删冠词（der/den/dem Linker Berater →
  Genie），属格与 "im"（预览语义）→ "von Genie"。
- 三处 SEO 描述（for-installer、commercial-storage、advisor EN/DE 及其
  德语对）随体句规则同步，验证器把 `_seopress_titles_desc` 纳入旧名守卫。

## 11. 门店模板文案（linker-commerce storefront，EN msgid → DE）

基准：德语措辞**照线上德语页**（本地外观=线上的硬要求；线上
`/de/produkte/`、`/de/produkt/saj-hs3-6k-t2-w-p/` 逐串比对）。
译文落在 `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po`
（63 条）。分两类：

**A. 线上已有德语（照抄，含标点与缩写）**——Filter、Kategorie、Marke、
Anwendung、Phase、Leistung、AC-Leistung、Nutzbare Energie、Bis 6 kW /
6 bis 15 kW / 15 bis 30 kW / Über 30 kW、Privat、Gewerbe、%d-phasig
（线上 1-phasig/3-phasig）、Alle Produkte、Produkte anzeigen、
Zurücksetzen（Clear）、Übernehmen（Set）、Empfohlen、Neueste zuerst、
Name A-Z、Leistung niedrig-hoch / hoch-niedrig、Artikelnr.（Item no.）、
Artikelnummer:、Produkt ansehen、Produkt anfragen、Auf Lager、
Nettopreis nach Partner-Anmeldung、Für Partnerpreise anmelden、
Beschreibung、Technische Daten、Dokumente、Produktbereiche
（Product sections）、Produktbild、Brotkrumen（Breadcrumb）、
Produktdaten（Key product data）、Filter schließen、Produktfilter、
Produkte sortieren、Minimale/Maximale AC-Leistung in Kilowatt、
Minimale/Maximale nutzbare Energie in Kilowattstunden、Produkte。
评审：逐串与 2026-10-10 线上 HTML 比对一致；EN msgid 与线上英文页
同源（Item number:/In stock/Sign in for partner pricing 等），未改英文。

**B. 线上没有对应（本票新写，EN 先行、DE 独立写）**：

- 分类页空态。EN `No product matches these filters. Clear one to see
  more.`（线上 EN 是 "No products match this filter set."，本票模板加了
  指引后半句——功能性 UI 允许）。DE 初稿 `Kein Produkt passt zu dieser
  Filterauswahl.` 评审：前半句就是线上德语空态原文，保留；补后半句
  `Setzen Sie einen Filter zurück, um mehr zu sehen.`（Sie 体、动词
  第二位、与 Zurücksetzen 按钮同词根）。**定稿**：两句相连。
- 侧栏工具卡（替换线上旧 "Projekt an Linker senden" 卡）：EN `Plan with
  the Solution Configurator` / `Configure a storage system from your site
  data; the result is a solution draft you can send as an inquiry.` /
  `Open the Solution Configurator`。DE 初稿 `Mit dem
  Lösungskonfigurator planen`、`Konfigurieren Sie aus Ihren
  Standortdaten ein Speichersystem; das Ergebnis ist ein
  Lösungsentwurf, den Sie als Anfrage senden können.`、
  `Lösungskonfigurator öffnen`。评审：Lösungsentwurf 是 #11 已用的
  购物车名（Lösungsentwurf= solution draft），术语一致；"aus Ihren
  Standortdaten" 与页头卡 "aus Ziel, Standort und vorhandener
  Ausrüstung" 不冲突（更窄语境）；CTA 无冠词冠词歧义（工具名做
  宾语，öffnen 配第四位格不变）。**定稿**：同初稿。
- 单品页四条空态（线上内容齐全无空态，机制需要）：
  ① `Product photography for this model is in preparation.` → `Die
  Produktfotografie für dieses Modell wird vorbereitet.`
  ② `Introduction in preparation. The specification below carries the
  values from the datasheet on file.` → `Die Einleitung wird
  vorbereitet. Die Spezifikation darunter enthält die Werte des
  hinterlegten Datenblatts.` 评审：darunter（页面语篇）优于 unten；
  "des hinterlegten Datenblatts"（on file=已归档在案）。
  ③ `The specification table for this product is in preparation. Ask
  us for the datasheet.` → `Die Spezifikationstabelle für dieses
  Produkt wird vorbereitet. Fragen Sie uns nach dem Datenblatt.`
  ④ `No documents are attached to this product yet. Ask us and we
  will add them.` → `Für dieses Produkt sind noch keine Dokumente
  hinterlegt. Fragen Sie uns, wir ergänzen sie.` 评审：**改**——初稿
  "Wir werden sie hinzufügen" 是 werden-Futur 冗余（同 §6 裁定），
  改现在时 "wir ergänzen sie"；主句换 "Für dieses Produkt sind …
  hinterlegt"（状态句）避免英文被动直译。
- 状态与 CTA：`Currently unavailable` → `Derzeit nicht verfügbar`；
  `Add to solution draft` → `Zum Lösungsentwurf hinzufügen`（方向
  补语，与 Woo "Zum Warenkorb hinzufügen" 同构）；`Close image
  viewer` → `Bildbetrachter schließen`（aria，线上全屏查看器用
  "Bildschirmfüllendes Bild" 是另一动作，不复用）；`Specifications`
  → `Spezifikationen`；`FAQs` → `Produktfragen`（线上德语 h2 原词，
  英文页同位是 Product questions——DE 遵线上，EN msgid 保持 FAQs）；
  `Compatible products` → `Kompatible Produkte`；`Grid phases` →
  `Netzphasen`；`Energy capacity` → `Nutzbare Energie`（与侧栏同一
  事实一个德语词，避免两个词指同一 kWh 事实；EN 保留两个 msgid）。

**验证**：/de/produkte/ 七个 facet（Kategorie/Anwendung/Marke/Phase/
Leistung/AC-Leistung/Nutzbare Energie）与线上德语页同名同序；桶
Bis 6 kW…Über 30 kW、1-phasig/3-phasig、按钮 Zurücksetzen/Übernehmen/
Produkte anzeigen 均为线上措辞；/de/produkt/saj-hs3-6k-t2-w-p/ 上
spec_ 域英文串零残留（grep 证据见 PR）。

**rebase 注记（2026-10-10 双评审后）**：.po 与 #11 商务链并集（338 条）
时 'Documents' 对撞——#11 账户菜单=Unterlagen（线上同）、门店附件区=
Dokumente（线上同），Law 6 精确故两存：门店模板改用
_x( 'Documents', 'product attachments', … ) 消歧，无上下文的
'Documents' 留给账户区。
