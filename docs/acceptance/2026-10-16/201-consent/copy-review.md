# #201 文案对抗评审记录（同意横幅 · 页脚入口 · 隐私政策两节）

规则（AGENTS.md §2 2026-10-09/10-11）：客户可见文案一律**初稿 → 评审意见 → 定稿**，记录在案；
EN 先行，**DE 独立撰写不是翻译**；Sie 体（`de_DE_formal`）；禁 "不是…而是…"、三连排比等 AI 句式、
禁 em/en dash（新写文案）；基准 = linker-copywriting Hard Stops + **线上既有措辞**与 .po 术语。
术语锁：Solution draft / **Lösungsentwurf**、Inquiry / **Anfrage**、Shop（线上隐私政策自称 "This shop" /
"Dieser Shop"）、Genie（德语不写 "Linker Genie"；"Linker Berater" 是已退役的旧名）。
**不发明承诺**：本次没有把任何时限承诺写进横幅。

评审是**对抗式自查**：先写 EN 初稿，再以 Hard Stops、线上既有措辞与**实测事实**逐条反驳，最后定稿；
DE 从语义重写（非逐词翻译）后同样反驳一遍。每条给"评审意见"的原话或要点。
定稿即 `tools/migrate/201-consent.json` 里的字面量（迁移脚本逐字写库）与页脚 partial 里的按钮文字。

## 0. 两处以**实测**推翻初稿的说法（本次评审最重要的两条）

初稿有两句话是"照常理写的"，实测不成立，按证据改：

1. **`_ga` 的保存期**。初稿写 "for up to two years"（GA4 可配置的上限）。本机实测（`/tmp/ga-expiry.mjs` 同法，
   探针放行 CSP 让真标签加载）：接受后 `_ga` 与 `_ga_T201LOCAL0` 的 `expires` 都是 **400 天**
   （2027-11-20，即 Google 现行默认 13 个月，我们的媒体资源没有改过它）。定稿改 **"for 400 days"** /
   **"für 400 Tage"**——写实测值，不写上限制。*待业主侧确认*：媒体资源若在 GA 后台调过保留期，这句话要跟着改；
   这一条登记在 `docs/specs/201-consent-ga4.md` 的"所有者侧"与验收 README。
2. **`sbjs_*` 的保存期**。初稿写 "The sbjs_… cookies end when you close the browser"。实测：
   7 个 `sbjs_*` 里 6 个是会话 Cookie（`expires` = 1970 时点，随浏览器关闭而结束），
   但 **`sbjs_session` 是 30 分钟的 Cookie**（实测 `lifetime_s 1796`）。定稿改精确：
   EN "The sbjs_… cookies are stored for your visit: most end when you close the browser,
   sbjs_session 30 minutes after your last page view."；DE 同义独立成句（见 §3）。
   评审意见：横幅里的目的说明允许一句话说清，但**不允许说不准的事实**；"up to"、"approximately" 之类
   含糊限定词救不了错句，只有实测数字能。

## 1. 横幅 · 标题与第一层按钮

| 位置 | 定稿 EN | 定稿 DE | 评审 |
|---|---|---|---|
| 标题 | `Your cookie choice` | `Ihre Cookie-Auswahl` | 初稿 EN 曾作 `Cookies on this site`——评审否：标题要说"这是你的决定"，不是"本站有 Cookie"（后者是事实陈述，不含主体）。"Cookie choice" 与 DE "Cookie-Auswahl" 各自成句，非互译。 |
| 接受 | `Accept all` | `Alle akzeptieren` | 与 DE 惯用一致（"Alle akzeptieren" 是德语横幅最常见的第一层接受句）。 |
| 拒绝 | `Reject all` | `Alle ablehnen` | 初稿 EN 曾作 `Decline`——评审否：`Decline` 比 `Accept` 弱（语感上更礼貌、更小），票面要求**第一层同等**；`Reject all` 与 `Accept all` 同长同结构。`Alle ablehnen` 同理（不用 "Nicht akzeptieren"，那是否定式，比肯定式弱）。 |
| 选目的 | `Choose purposes` | `Zwecke auswählen` | 初稿 EN 曾作 Complianz 默认的 `View preferences`/`Manage options`——评审否：那是插件腔、且"preferences"在本站指另一个（关闭的）目的类，会误导。`Choose purposes` 与页面上"两个目的"的措辞同源；DE `Zwecke auswählen` 直接用 DSGVO 的 "Zwecke" 一词（该词在德语法域里指处理目的，不是偏好）。 |
| 保存 | `Save my choice` | `Auswahl speichern` | EN 带 `my`：这是访客按自己的选择保存；DE 不带物主代词是德语按钮惯例（"Auswahl speichern"），不为了对齐 EN 而生造 "Meine Auswahl speichern"。 |

## 2. 横幅 · 正文（`message_optin`）

**EN 初稿**（前任会话的 r1 稿，本票接手后逐条评审）：

> We would like to use cookies and similar technologies for two optional purposes. **Statistics:**
> Google Analytics counts visits and page views, so we can see which pages help our visitors. Google Ireland
> Limited processes this data for us, and it may be transferred to Google LLC in the USA. **Marketing:** we
> record which website, campaign or link brought you here and keep that note with an inquiry you send us. Both
> stay off until you accept. You can change your choice at any time under "Cookie settings" at the foot of every page.

评审意见（逐条反驳）：

- "We would like to use" —— 软化词。同意请求是**陈明处理**，不是表达愿望（Hard Stops 的删词测试：
  删掉 "would like to" 句意不变 → 它只制造距离）。**改为 "We use"**。
- "for two optional purposes" 保留（"optional" 是事实：两个目的都可拒绝）。
- "so we can see which pages help our visitors" —— "help our visitors" 是对**收益**的断言（谁受益？怎么算帮助？），
  同意说明要描述**处理**。**改为 "so we can see how the shop is used"**。
- "Both stay off until you accept." 保留，但初稿没说**拒绝的后果**——访客要能预测结果（可预见性也是有效同意的要件）。
  **补一句 "If you reject, the shop works the same."**（陈述事实：拒绝不影响功能；不含威胁，也不含"否则不能使用"）。
- 结尾的 "You can change your choice at any time under "Cookie settings" at the foot of every page." 保留：
  指路到实际存在的入口（页脚按钮，本票加的），不是空承诺。
- 引号：EN 用弯引号 “Cookie settings”；DE 用 „Cookie-Einstellungen“（德语引号惯例）。

**EN 定稿**（= JSON 的 `banner.message_optin`）：

> We use cookies and similar technologies for two optional purposes. **Statistics:** Google Analytics counts visits
> and page views, so we can see how the shop is used. Google Ireland Limited processes this data for us, and it may
> be transferred to Google LLC in the USA. **Marketing:** we record which website, campaign or link brought you here
> and keep that note with an inquiry you send us. Both purposes stay off until you accept. If you reject, the shop
> works the same. You can change your choice at any time under “Cookie settings” at the foot of every page.

**DE 独立撰写**（从语义重写，不照 EN 语序）：

> Wir setzen Cookies und ähnliche Technologien für zwei freiwillige Zwecke ein. **Statistik:** Google Analytics zählt
> Besuche und Seitenaufrufe, damit wir sehen, wie der Shop genutzt wird. Die Daten verarbeitet Google Ireland Limited
> in unserem Auftrag; eine Übermittlung an Google LLC in den USA ist möglich. **Marketing:** Wir halten fest, über
> welche Website, Kampagne oder welchen Link Sie zu uns gekommen sind, und speichern diese Angabe mit einer Anfrage,
> die Sie uns senden. Beide Zwecke bleiben aus, bis Sie zustimmen. Wenn Sie ablehnen, funktioniert der Shop unverändert.
> Ihre Auswahl können Sie jederzeit über „Cookie-Einstellungen“ am Ende jeder Seite ändern.

DE 评审意见：

- "freiwillige Zwecke"（不是 "optionale Zwecke"）：德语法域里 "freiwillig" 是同意语境的定词（§ 25 Abs. 1 TDDDG 的
  "freiwillige Einwilligung"），"optional" 是英语借词。
- "Die Daten verarbeitet Google Ireland Limited in unserem Auftrag" —— 主动句 + Auftrag（委托处理）是德语隐私语的
  标准说法，比 "Die Daten werden von … verarbeitet" 少一层被动；**"in unserem Auftrag" 是事实性的**（GA 作为
  Auftragsverarbeiter），与隐私政策第 4 节的处理器表同一口径。
- "Beide Zwecke bleiben aus" 不用第二人称假设句，"bleiben aus" 是技术事实（不开）；评审曾考虑 "ausgeschaltet"，
  否：那更像"被谁关掉"，"bleiben aus" 是状态。
- "Wenn Sie ablehnen, funktioniert der Shop unverändert." —— 对应 EN 的后果句；"unverändert" 比 "genau gleich"
  更书面、无口语感。
- 无 em/en dash（新写文案），无三连排比，无 "nicht … sondern"。

## 3. 横幅 · 目的说明与分类名

| 位置 | EN 定稿 | DE 定稿 | 评审 |
|---|---|---|---|
| 分类（必要） | `Necessary` | `Notwendig` | 线上德语隐私政策同词（"technisch notwendige Cookies"），照用。 |
| 分类（统计） | `Statistics` | `Statistik` | 与隐私政策第 3 节口径一致。 |
| 分类（营销） | `Marketing` | `Marketing` | **有争议，记录在此**：本站这一类的实际处理是**我们自己的**订单来源记录（第一方、会话级、不转交），把它叫 "Marketing" 会让人联想到广告追踪（更 invasiv）。否决改名的理由：①票面明确把这一类命名为「营销」；②WP Consent API 的类别键就是 `marketing`（WooCommerce 把订单来源归到它），显示名与机制名不一致会给后续维护埋坑；③真正要害是**说明**要说准——所以说明句逐字写明"这是我们自己的记录"且"不转交任何人"。**决议：类名保留 Marketing，说明句承担准确性**。 |
| 必要说明 | `Keeps the shop working: your session, your solution draft, your sign-in, your language and this cookie choice. These are always on.` | `Hält den Shop am Laufen: Ihre Sitzung, Ihr Lösungsentwurf, Ihre Anmeldung, Ihre Sprache und diese Cookie-Auswahl. Sie sind immer aktiv.` | 初稿写 "Keeps the **site** working" —— 评审改 "shop"：线上隐私政策自称 "This shop" / "Dieser Shop"，术语取线上既有措辞。DE 用 `Lösungsentwurf`（.po 术语），不用 "Warenkorb"（AGENTS §3 禁 basket/cart 一类词）。`sign-in`/`Anmeldung` 与 .po 既有串一致。 |
| 统计说明 | `Google Analytics (Google Ireland Limited; transfer to Google LLC in the USA possible). It sets the cookies _ga and _ga_… for 400 days and shows us how the shop is used.` | `Google Analytics (Google Ireland Limited; eine Übermittlung an Google LLC in den USA ist möglich). Setzt die Cookies _ga und _ga_… für 400 Tage und zeigt uns, wie der Shop genutzt wird.` | 保存期按 §0.1 实测改 400 天。DE 第二句省略主语（"Setzt die Cookies …"）是德语标签体惯例，主语由括号内的产品名承接，不重复 "Es"。 |
| 营销说明 | `Our own record of where your visit came from (the referring website, campaign or link). The sbjs_… cookies are stored for your visit: most end when you close the browser, sbjs_session 30 minutes after your last page view. The note goes with an inquiry you send us and is not passed to anyone else.` | `Unsere eigene Notiz, woher Ihr Besuch kam (verweisende Website, Kampagne oder Link). Die Cookies sbjs_… werden für Ihren Besuch gespeichert: Die meisten enden, wenn Sie den Browser schließen, sbjs_session 30 Minuten nach Ihrem letzten Seitenaufruf. Die Angabe geht mit einer Anfrage an uns und wird an niemanden weitergegeben.` | 保存期按 §0.2 实测改精确说法。"Our own record" / "Unsere eigene Notiz" 明确第一方；"is not passed to anyone else" / "wird an niemanden weitergegeben" 与隐私政策"不售卖、不转交"的口径一致（不是"我们不会出售"那样的防御句）。 |

## 4. 页脚入口（LC partial，EN / DE）

| 位置 | 定稿 | 评审 |
|---|---|---|
| 按钮文字 EN | `Cookie settings` | 与横幅正文里的指路句**逐字同串**："under “Cookie settings” at the foot of every page" —— 访客按正文找得到那个词。不用 `Manage cookies`（"manage" 是插件腔）或 `Cookie preferences`。 |
| 按钮文字 DE | `Cookie-Einstellungen` | 同上，与 DE 正文里的 „Cookie-Einstellungen“ 逐字同串。复数形式与德语页面惯例一致（"Einstellungen" 是德语 UI 的标准词）。 |
| 位置 | `.tv-footer-bar-legal` 行末 | 与 Imprint / Privacy Policy / Terms of Sale / Refund & Returns 同排；不是浮动 tab（插件自带 tab 已关），也不放进任一面板——撤回入口要在每个页面的同一处、一眼可见。 |
| 无障碍 | `<button type="button">` | 不是 `<a href="#">`：它执行动作（重开对话框），不是跳转。键盘焦点环走页脚既有 `:focus-visible` 规则。 |

## 5. 隐私政策 · 第 3 节（Cookies）

**EN 初稿**（线上现文，逐字）："This shop uses only technically necessary cookies (session, cart, and login cookies).
We currently use no analytics, advertising, or tracking cookies."

评审意见：

- 第二句在 GA4 接入后**不成立**，必须改（票面点名的两节之一）。
- 第一句里的 **"cart"** 是 AGENTS §3 明令不用的词（篮子/basket/cart），且 DE 页早已写 `Lösungsentwurf`（线上 EN/DE 在此分叉）。
  本次既已改写这一句，**顺手按术语表改成 "solution draft"**——这不是顺手改别的，是改我正在改的那句里的禁词（AGENTS §2 的"必要后果"）。
- 新增：撤回方式与**撤回不溯及既往**（GDPR Art 7(3) 的告知）；只陈述事实，不承诺时限。
- 不写 "we anonymise" 之类——GA4 默认未开 IP 匿名化开关，写了就是编造。

**EN 定稿**：

> This shop uses technically necessary cookies only (session, solution draft, and login cookies) unless you allow more.
> With your consent, Google Analytics sets the cookies `_ga` and `_ga_…` to measure how the shop is used, and our own
> order-source note stores how you found us (the cookies `sbjs_…`). Both purposes stay off until you accept. You can
> change or withdraw your choice at any time under “Cookie settings” at the foot of every page; the withdrawal does
> not affect the lawfulness of the processing before it.

**DE 定稿**（独立撰写）：

> Dieser Shop verwendet nur technisch notwendige Cookies (Session-, Lösungsentwurf- und Login-Cookies), solange Sie
> nicht mehr erlauben. Mit Ihrer Zustimmung setzt Google Analytics die Cookies `_ga` und `_ga_…` ein, um zu messen, wie der
> Shop genutzt wird; unsere eigene Herkunftsnotiz speichert, wie Sie zu uns gekommen sind (die Cookies `sbjs_…`).
> Beide Zwecke bleiben aus, bis Sie zustimmen. Ihre Auswahl können Sie jederzeit über „Cookie-Einstellungen“ am Ende
> jeder Seite ändern oder widerrufen; der Widerruf berührt nicht die Rechtmäßigkeit der Verarbeitung bis dahin.

DE 评审意见：

- 线上 DE 原文的 "(Session-, **Lösungsentwurf**- und Login-Cookies)" **保留原样**（它已经是术语表的形状，没有 "Warenkorb"，
  这次不改它）——EN 向 DE 对齐，不是反过来。此处两语的差别只源于线上 EN 未同步术语，本次一并修。
- "solange Sie nicht mehr erlauben" 是德语里说"默认如此、除非你允许更多"的自然说法；不用 "es sei denn"（更生硬）。
- "der Widerruf berührt nicht die Rechtmäßigkeit der Verarbeitung bis dahin" 是 Art 7(3) 的德语标准表述；
  比 "bereits erfolgte Verarbeitung bleibt rechtmäßig" 少一层名词化。

## 6. 隐私政策 · 第 4 节（接收方与传输）

表格 caption 与新增行的**必要性**：现表 caption 只说 Genie 与规划工具用的处理器，Google 不属于这一类，
但把 Google 塞进一张 caption 不覆盖它的表里是错的；因此 caption 扩写（这是本次唯一改动的既有句子）。
DE caption 里含**已退役的旧工具名** "Linker Berater"（12-site-chrome 迁移漏网的 5 处之一），
本次既已改写该句，按 AGENTS §1 用现任名 `Genie`（德语不连写 "Linker Genie"）。

| 位置 | EN 定稿 | DE 定稿 | 评审 |
|---|---|---|---|
| 表 caption | `To answer a question put to Genie, to run the planning tools, and to measure how the shop is used with your consent, we use the following processors:` | `Um eine an Genie gerichtete Frage zu beantworten, die Planungstools auszuführen und mit Ihrer Zustimmung die Nutzung des Shops zu messen, setzen wir die folgenden Auftragsverarbeiter ein:` | 三件事并列，第三个带 `with your consent` / `mit Ihrer Zustimmung`（说明它的前提条件）；去掉初稿的 `specialised`（含糊形容词）。 |
| Google 行 · 处理器 | `Google Ireland Limited` | `Google Ireland Limited` | 与站上既有的欧盟主体表述一致（不是 "Google"、"Google LLC"）。 |
| Google 行 · 地点 | `Ireland; transfer to Google LLC in the USA possible` | `Irland; eine Übermittlung an Google LLC in den USA ist möglich` | 与同一张表里既有的中美传输表述同口径；第三国传输必须写明，不能只写 "EU"。 |
| Google 行 · 数据与目的 | `Visits and page views, only if you allow statistics; used to measure how the shop is used.` | `Besuche und Seitenaufrufe, nur wenn Sie Statistik erlauben; zur Messung, wie der Shop genutzt wird.` | "only if you allow statistics" 是**条件**，不能省（该行在没有同意时不发生任何处理）；陈述目的，不写"改进服务"之类的收益承诺。 |

## 7. 未决（留给业主/操作者，非本线可自行决定）

- **横幅与隐私政策文案的营销侧操作者审稿**：票面验收要求"营销侧操作者审稿「可以了」"。本记录是**本线自己的
  对抗评审**，不是操作者签字；PR 交付后由营销侧操作者按此定稿逐句审，签字后才进线上窗口（AGENTS §5：
  线上不是任何功能第一次被看到的地方）。
- **GA4 媒体资源的保留期**：若操作者在 GA 后台把 `_ga` 保留期改成别的值，§3 的 "400 days" / "400 Tage" 要跟着改
  （本句写的是**实测的现行值**，不是配置意图）。
- **"Marketing" 类名的再议**（§3 表内已记录理由）：若操作者认为德语访客会把 "Marketing" 读作广告追踪，
  可改为 `Order source` / `Herkunft`；那是显示名改动，机制不动，改一处 JSON 即可。
