# 账号链 · 注册表单最少问什么：同行字段对照、表单长度证据与 de-linker 字段清单

- 日期：2026-10-17（研究票 #224，地图 #220；下游实现票 #225）
- 性质：只读研究。没有改插件、服务、生产站或 WordPress；没有向任何同行提交表单。
- 外部取证：全部经 Apify（附录 A 列出 14 个运行的 run id 与起止时间）。每条外部事实附 URL 与抓取时间（UTC）；抓取集中在 2026-10-16 17:18–21:14 UTC（即 2026-10-17 本地时间）。
- 原文照录，不翻译；德语、荷兰语、波兰语、西班牙语原文保持原样。
- 原始数据：`raw/`（Apify 数据集 JSON；第三方页面里出现的 JWT 形式会话令牌已替换为 `<redacted-jwt>`，搜索结果里 Google 广告点击链接的 `sig=` 签名已替换为 `<redacted-ad-signature>`；网页正文去掉了与 markdown 重复的 text 字段；两份 GDPR 全文只保留被引用的条款摘录）。提交前做过令牌扫描（JWT、Apify 令牌形态与环境中三个 Apify 令牌的字面值），结果为 0。
- 业主事实（2026-10-17，地图 #220）：业主按注册时提供的信息自己查证，属实即批；所有国家都可注册，欧洲为重点；业主觉得现表单"像问卷"，要短。

---

## 0 结论（先读这一节）

### 0.1 推荐字段清单

现表单 11 个输入、10 个必填、三个编号小节。建议改为 **9 个输入：7 个必填 + "网站或 VAT ID 至少填一项"**，两个不编号的分组。

| # | 字段 | 现状 | 建议 | 一句话理由（证据见 §3–§9） |
|---|---|---|---|---|
| 1 | 公司名称 | 必填 | **保留·必填** | 业主查证的对象本身；21 份同行表单有 20 份问公司名（§3.3） |
| 2 | 业务类型（安装商 / EPC / 经销商） | 必填·下拉 | **保留·必填，改为 3 个单选按钮** | 判断"是不是同行客户"的自报项，同行普遍有这一问；3 个选项用下拉是公认的差设计（NN/g、Baymard、GOV.UK，§4.4），Segen 就用单选 |
| 3 | 国家 | 必填·全世界字母序 | **保留·必填；全部国家，欧洲在前，可搜索，带默认值** | 决定业主去哪个登记处、VIES 是否适用、后续增值税处理；排法见 §8 |
| 4 | 公司网站 | 无 | **新增·选填（与 5 合起来至少一项）** | 欧盟商业网站依法公示名称、地址、登记号、VAT 号（e-Commerce 指令第 5 条、德国 §5 DDG），业主在任何国家都能据此核对；21 份同行表单有 10 份问网站（§6.4、§3.3） |
| 5 | VAT ID | 选填 + VIES | **保留·选填（与 4 合起来至少一项），继续 VIES** | 欧盟申请人可秒级核验有效性；但实测 VIES 对德国号码**只回有效、不回名称地址**（§6.1），单凭它无法把号码对到公司，所以要和网站互为替代 |
| 6 | 名 | 必填 | **保留·必填，与 7 同一行** | Woo 原生账单字段，Proforma 上要用；Baymard 的单字段姓名证据作为可翻案项记录（§7.2） |
| 7 | 姓 | 必填 | **保留·必填，与 6 同一行** | 同上 |
| 8 | 邮箱 | 必填 | **保留·必填** | 登录与通知；业主可比对邮箱域名与网站域名 |
| 9 | 密码 | 必填 | **保留·必填** | Woo 原生；Woo 的"发送设置密码链接"可再省一个字段，但有代价（§7.3），不作默认 |
| — | 街道 / 邮编 / 城市 | 必填 ×3 | **移出注册，挪到 Proforma 请求页**（Woo 结账页原生账单地址） | 地址是开 Proforma 要用的，不是查证要用的；NN/g："collected more conveniently at a later date" 的字段应拿掉（§4.1、§10） |
| — | 电话、证件上传、法律形式、登记号、采购量、"从哪知道我们" | 无 | **不加** | 同行用它们开信用账户、排物流、做销售筛选；业主查证不需要；GDPR 最小化（§5、§7.4） |

### 0.2 挪到询盘 / Proforma 的信息

- **账单地址（街道、邮编、城市）**：Proforma 请求页就是 Woo 结账页，Woo 原生账单字段本来就收地址，并回写客户资料供下次预填。
- **VAT ID 的"法律必需"时点在 Proforma**：欧盟跨境 0% 供货要求买方提供另一成员国的有效 VAT 号（指令 2018/1910 修订后的第 138(1)(b) 条；§6a(1) Nr. 4 UStG，§10）。站上已有的 VAT 账单字段在 Proforma 请求页照常出现；注册时填过就预填。
- **电话**（若业主或物流需要）：同样在 Proforma 请求页用 Woo 原生账单电话字段收，不在注册时收。

### 0.3 国家下拉

全部国家都保留（业主裁定）。排序：**默认选中最可能的国家 → 欧洲国家块（按当前语言字母序）→ 其余国家（按字母序）**；"欧洲"直接用 WooCommerce 自带的大洲数据（`i18n/continents.php` 的 `EU` = Europe，53 个代码），不手写名单；下拉启用 Woo 自带的可搜索选择器（selectWoo / `wc-country-select`）。同行先例：Krannich 把 5 个重点国家放最前再列全部 251 个国家；Memodo 把 DE、CZ、PL、SK、UK 放最前（§3.2、§8）。

### 0.4 防机器人

1. **第一层（推荐立即做，零第三方、零界面负担）**：蜜罐字段 + 最短填写时间，用 Woo 原生钩子 `woocommerce_register_form` 渲染、`woocommerce_process_registration_errors` 拦截；在建号**之前**拒绝，所以不建账号、不发信。W3C 的 CAPTCHA 无障碍说明称蜜罐"easily implemented … and should be considered"；同行 Solar-West（BE）、Solarbex（ES）、Akkusys（DE）的注册表单里都有按字段名、位置与隐藏方式判断为蜜罐的字段（§9）。
2. **第二层（仅当第一层上线后仍有机器人注册）**：Cloudflare Turnstile 免费版（最多 20 个 widget、不限挑战次数），必须服务端 siteverify；代价是第三方脚本与数据（IP、TLS 指纹、User-Agent）流向 Cloudflare，需要隐私政策更新与同意义务的法律判断（§9.3，列为未知）。同行 BayWa r.e. 的注册表单用的就是 Turnstile。
3. **不用**：reCAPTCHA（数据流向 Google，交互式版本有无障碍问题）、图片验证码、Akismet（商业站点要付费）、"只靠邮箱验证"——GSA Search Engine Ranker（10-14 那条机器人的来源）官方页写明它能接 30 多种验证码服务并自动完成邮箱验证与注册（§9.1）。

### 0.5 怎样不像问卷

- 字段 11 → 9，必填 10 → 7（+1 选 1）；地址块整块消失。
- 去掉"1 / 2 / 3"编号步骤徽标，改为两个普通分组（`fieldset` + `legend`）："您的公司"（公司名、业务类型、国家、网站、VAT ID）与"您和您的登录"（名、姓、邮箱、密码）。编号让单页表单读起来像多步问卷；NN/g 的规则是"两个话题就分两组"（§4.2）。这是对业主 2026-10-15 验收原型的改动，进变更台账。
- 业务类型用 3 个可见单选按钮；名与姓同一行；网站与 VAT ID 放在一起，上方一句话说明"我们用它核实您的公司"（Baymard：说明为什么要问；NHS："why you need it"）。
- 必填与选填都标出（Baymard：两者都标的站只有 14%，但测试显示都标最好）；不用占位符代替标签（NN/g）。
- 保持单页，不做向导：Baymard 的数据是字段数比步骤数更影响可用性；旧站的三步向导票 #224 已写明不是目标。
- 具体措辞（EN/DE）不在本研究定稿：客户可见文案走对抗评审（AGENTS.md §2），由 #225 完成。

### 0.6 置信度

| 结论 | 置信度 | 主要依据 / 主要风险 |
|---|---|---|
| 地址移出注册、挪到 Proforma | 高 | NN/g、GOV.UK、GDPR 最小化；Woo 结账页原生收地址。风险：业主若要靠地址查证（网站与 VIES 已能给出地址） |
| 新增"公司网站" | 高 | e-Commerce 指令第 5 条；德国 VIES 不回名称（实测）；10/21 同行问网站 |
| "网站或 VAT ID 至少一项" | 中 | Sonepar"mindestens ein Kriterium"先例；风险：两样都没有的小公司被挡（兜底：sales@ 邮件） |
| 业务类型改单选 | 高 | NN/g、Baymard、GOV.UK 一致 |
| 国家：欧洲在前 + 可搜索 | 中高 | Krannich / Memodo 先例、NN/g"most common values first"、Baymard 自动完成；分组标题（optgroup）需要少量自定义标记 |
| 蜜罐 + 时间陷阱为第一层 | 高（做法）/ 中（对 GSA 的实际拦截率） | W3C、3 家同行；对 GSA 的拦截率没有一手数据，上线后计数 |
| Turnstile 为第二层 | 中 | BayWa 先例、官方文档；德国同意义务未判断 |

---

## 1 方法与证据边界

**Apify（必经）**
- 发现：`apify/google-search-scraper` 两轮共 36 个查询（德、英、法、荷、波、西、意七种语言的"光伏批发注册"类查询 + 可用性、GDPR、查证、防机器人来源查询）。
- 表单实抓：`apify/playwright-scraper` 6 个运行（另有 1 个用于 VIES 实测、1 个用于 e-Justice 页面）。页面函数在真实 Chromium 里读出每个表单控件的类型、name、标签、required 属性、可见性、下拉选项，必要时点击"注册 / Open a trade account"进入下一层，并对 iframe 内表单（HubSpot）逐帧读取。只读不提交。
- 正文：`apify/website-content-crawler` 4 个运行，抓 Baymard、NN/g、GOV.UK、NHS、W3C、EUR-Lex、ICO、CNIL、BZSt、BMJV、Cloudflare、OWASP、GSA、WordPress.org、WooCommerce 文档。
- VIES 实测：在 VIES 自己的页面里调用其 REST 接口，查 4 个公开在对方 Impressum 上的 VAT 号（§6.1）。
- 排错记录：`apify/web-scraper` 要求在控制台授予"完全权限"后才能运行（HTTP 403 `full-permission-actor-not-approved`），这需要账户所有者操作，所以改用 playwright-scraper，未改动任何账户设置。5 个页面在数据中心代理下两次失败，改走 RESIDENTIAL 代理后 3 个成功（pvXchange、Akkusys、Undersun），SolarSell（UK）与 Power-SCS（PT）仍未取到；Rexel 的注册页两次（第二次用住宅代理并等待 25 秒）都只渲染出页脚，字段未取到，`/neukunde` 则重定向到首页（§11）。

**本地只读核对**：WooCommerce 11.2.0 源码（本机实例 `de-linker-local/t201`）；本仓 `plugins/linker-commerce/includes/Registration/*`、`Settings/WooOptions.php`、`templates/myaccount/auth/form-register.php`、`templates/emails/linker-new-customer.php`。

**业主调研库**（`~/Documents/de-linker-vault/marketing/00-research/`）：`industry-research-2026-09-20/` 09–22、28 与 `competitor-study-2026-10-01/`，逐条引用见 §3.4。

**计数口径**：只数默认可见、需要用户填或选的输入；同意勾选（隐私 / 条款 / 订阅）不计；"地址不同""另有会计联系人"一类开关不计，开关打开后出现的字段也不计；单选组、多选组各算一个输入。"*"、`required` 属性或 `aria-required` 记为必填。

**边界**：
- 同行表单只能匿名看到，我们没有提交，所以"提交后要等多久、审核实际问什么"只能引用对方自己的说明。
- 防机器人一栏是对页面 HTML 的特征检测（脚本或控件是否存在），只有控件位于表单内的才写成"表单使用"。
- 第三方页面会改版；表里的结论只代表抓取时刻。

---

## 2 现状：线上注册表单（实抓）

- EN：https://de-linker.com/my-account/register/ （抓取 2026-10-16T17:23:15Z）；DE：https://de-linker.com/de/mein-konto/register/ （2026-10-16T17:23:15Z）。
- 标题 "Create your business account" / "Erstellen Sie Ihr Firmenkonto"；三个编号小节 "1 Company / 2 Contact and address / 3 Sign-in details"（DE："1 Unternehmen / 2 Kontakt und Adresse / 3 Zugangsdaten"）。
- 11 个输入、10 个必填：Company name*、Business type*（下拉：Installer / EPC contractor / Distributor）、VAT ID (optional)、First name*、Last name*、Country / Region*、Street address*、Postcode / ZIP*、Town / City*、Email address*、Password*。字段定义在 `plugins/linker-commerce/includes/Registration/Fields.php`。
- 国家下拉：251 个选项（含占位项），从 Afghanistan / Åland Islands 起按字母序；页面上没有 select2 / selectWoo 容器，即**原生长下拉，不能输入搜索**。默认值是店铺所在国（`Fields::render()` 用 `WC()->countries->get_base_country()`，即德国）。
- 防机器人：表单内的隐藏控件只有 Woo 的 `woocommerce-register-nonce` 与 `_wp_http_referer`。WooCommerce 11.2 的 `WC_Form_Handler::process_registration()`（`includes/class-wc-form-handler.php` 第 1351–1407 行）只校验 nonce，然后套用 `woocommerce_process_registration_errors` 过滤器、调用 `wc_create_new_customer()`；整个 Woo 源码里没有 honeypot / captcha / turnstile 字样。nonce 写在页面里，机器人照样能取到，它不是防机器人手段。
- 2026-10-14 已有一条 "GSA Search" 机器人注册挂在待审（票 #224 已知）。
- **机器人注册的直接成本**：一次注册触发两封信——给团队的 `NewCustomerEmail` 和发到表单所填地址的 `RegistrationReceivedEmail`（两者都挂在 `linker_commerce_customer_registered` 上，见 `Registration/Emails/*.php`）。发信走 Hostinger `mail()`，四站共用 10 封/分钟、100 封/24 小时（AGENTS.md §4）。机器人一波注册就能吃掉当天配额，还会把"已收到"邮件发到被冒用的地址。所以拦截要发生在建号**之前**。

---

## 3 同行注册表单字段对照（a）

### 3.1 对照表

"必填"按 §1 口径计；"—"表示该页没有这一项或没有抓到，不等于对方线下不问。

| 公司（国别） | 形态 | 输入 / 必填 | 公司身份 | 证件 | 网站 | 国家下拉 | 防机器人 | 审核 / 门槛原文 | 来源（抓取 UTC） |
|---|---|---|---|---|---|---|---|---|---|
| **de-linker**（DE，现状） | 单页 3 编号节 | 11 / 10 | 公司名、VAT（选填） | — | — | 251 项字母序，默认 DE，不可搜 | 无 | "We review every new account before activation." | de-linker.com/my-account/register/（17:23:15Z） |
| **Memodo**（DE） | 单页 | 19 / 16 | 公司名、法律形式*（57 项）、HR 号与 Amtsgericht（按法律形式出现）、税号、USt-ID（选填）、职位*、工种* | 营业执照上传* | — | 38 项：DE、CZ、PL、SK、UK 在前，其后字母序 | 页面载入 reCAPTCHA | "Um bei uns Kunde zu werden, brauchst du einen Gewerbeschein und musst Installateur*in sein." | memodo.de/account/login?registerView=register（17:19:52Z） |
| **Krannich**（DE） | 单页 6 节 | 25 / 16 | 公司名、总机邮箱*、开票邮箱*、USt-IdNr.（选填）、行业*（PV-Fachbetrieb / Investor / EPC / Elektro-Großhandel / Sonstiges）、PV 员工数、年采购 MW、叉车* | 营业执照 / HR 摘录上传（选填，"beschleunigen"） | 选填 | 251 项：DE、BE、NL、AT、PL 在前，其后全部国家字母序 | 页面载入 reCAPTCHA | "Für die Registrierung benötigen Sie einen Gewerbeschein … Nach der Prüfung Ihrer Daten erhalten Sie eine E-Mail von uns mit weiteren Informationen und Ihren Zugangsdaten." | shop.krannich-solar.com/de-de/account/request-registration（17:20:31Z） |
| **BayWa r.e.**（DE） | 单页"Registrierungsanfrage" | 19 / 13 | 公司名（含法律形式）*、行业*、活动范围*、USt-ID、HR 号（选填） | 营业登记 / HRA 上传* | 选填 | 有（选项未取到） | **Cloudflare Turnstile** | "Da wir ausschließlich mit gewerblichen Installationsbetrieben zusammenarbeiten, benötigen Sie für Ihre Anmeldung einen gültigen Gewerbeschein." | solar-distribution.baywa-re.de/konto-eroeffnen/（17:23:12Z） |
| **IBC Solar**（DE） | 单页伙伴申请 | 18 / 14 | 公司名、USt-IdNr.*、语言*、电气安装经验*、做 PV 年数、去年 kWp、留言* | — | 选填 | 文本框 | 未见 | 同意句："Ich möchte ein Kundenkonto anlegen." | ibc-solar.de/installateure/（17:27:05Z） |
| **EWS**（DE） | 单页 | 21 / 15 + 图片验证码 | 公司名*、Ust.-IdNr.*、客户号、州/地区*、邮箱需输两次、密码需输两次 | 营业证明、HR 摘录上传（新客户） | 选填 | 29 个欧洲国家 + "weitere"；AT/CH 走国际站 | 图片验证码"Sicherheitscode" | "Nachdem Sie diesen Link geklickt haben prüfen wir gern Ihre Anfrage …" | pv.de/registrierung/（17:20:32Z） |
| **Segen**（UK / EU） | HubSpot 4 步 | EU 16 / 12；UK 19 / 13 | 公司名*、公司类型*、成立日期*、VAT（选填）、业务类型*（**单选**：Residential installer / Commercial installer / PV reseller / Electrical wholesaler）、月装量 | — | 选填 | 有（自带搜索） | 表单内 reCAPTCHA | "1. Fill out the form below 2. Our sales team will call you back for a brief conversation about your business 3. After verification, you will receive access to our purchasing portal." | segen.co.uk/contact-us/open-an-account/（20:58:37Z）；segensolar.eu/contact-us/（20:56:28Z） |
| **Libra Energy**（NL） | 多步 | 第 1 步 10 / 7 | 公司名*、VAT*、CoC 号*、IBAN（选填） | — | — | 全部国家字母序，预选 Netherlands | 未见 | （第 1 步只到公司与地址） | libra.energy/en/account/register（20:59:20Z） |
| **Wattkraft**（DE） | **无在线注册**，只有联系表 | — | — | — | — | — | 页面载入 reCAPTCHA | 联系表收件组含 HUAWEI / PHONO / CANADIAN / AIKO DISTRIBUTION 等 | wattkraft.com/kontakt/（17:33:43Z） |
| **Alma Solar**（LU） | 单页（B2C/B2B 混合） | 4 / 4 | — | — | — | — | 未见 | "Create your account in 2 clicks, benefit from our professional rates upon connection." | alma-solarshop.com/login?create_account=1（17:29:02Z）；…/content/40-professional-area（17:33:13Z） |
| **Sonepar**（DE） | 单页 | 19 / 9 + 至少一项 | 公司名*、法律形式（5 选 1）、总经理出生日期、HR 号 / 税号 / USt-ID **至少一项** | 营业执照上传 | — | 无（只收德国） | CaptchaFox | "Bitte teilen Sie uns mindestens ein Kriterium mit" | sonepar.de/…/kunden-registrierung（17:21:09Z） |
| **Rexel**（DE） | 注册页未渲染（§11） | — | （FAQ）HR 摘录 / 营业登记 | 需准备证明 | — | 只收德国公司 | — | "Bei Rexel Germany können sich Gewerbekunden mit Sitz in Deutschland registrieren." / "Nach sorgfältiger Prüfung Deiner Firmendaten und der Kreditwürdigkeit …" | rexel.de/rexeleasy/faq/registrierung（17:21:07Z） |
| Natec（NL） | 2 步 | ≈22 / ≈17 | VAT*、CoC 号*、职位*、现/预期年销量 MW*、公司描述* | — | **必填** | 38 个欧洲国家 | 页面载入 reCAPTCHA | — | natec.com/nl/en/become-a-customer-at-natec/（17:21:18Z） |
| PVSelected（DE） | 单页 | **7 / 5** | 公司名*、USt-ID* | — | 选填 | — | 表单内 reCAPTCHA | "Neue Konten unterliegen der Genehmigung." | b2b.pvselected.de/de/contactus（17:21:38Z） |
| Densys pv5（DE） | 单页（Zoho） | 14 / 11 | 公司名含法律形式*、公司总邮箱*、USt-IdNr.*（无则税号） | 营业证明上传 | 选填 | 文本框 | 未见 | "Nach der Registrierung überprüfen wir Ihre Angaben, das kann einige Tage dauern." | lp.densys-pv5.de/registrierung-shop/（17:21:38Z） |
| Senergia（DK/北欧） | 单页 | 13 / 11 | 组织号*、Tax/VAT*、开票邮箱* | — | — | 只有 DK / FI / NO / SE | 未见 | "As a distributor, we only sell to registered customers who are installers with a legal entity." | b2b.senergia.dk/…login-register（17:22:32Z） |
| Midsummer（UK） | 单页 | 20 / 11 | 公司号*（可填 N/A）、MCS 号*（可填 N/A）、开票邮箱* | — | — | 无（只收英国） | 未见 | "Please complete the short form below to register." | midsummerwholesale.co.uk/register（17:29:16Z） |
| Western Solar（IE） | 单页（Woo + B2BKing） | 14 / 12 | 公司注册号*、VAT*、开票邮箱* | — | 选填 | 无（只收爱尔兰） | 页面载入 reCAPTCHA 与 Turnstile 脚本 | — | westernsolar.ie/register-trade-account/（20:55:04Z） |
| Solar-West（BE） | 单页（Woo 原生注册） | 11 / 10 | Btw 号* | — | — | 5 国：BE、DE、FR、LU、NL | 蜜罐（推断）`sw_b2b_guard_website` + 页面载入 reCAPTCHA | "Na goedkeuring ontvangt u bericht en worden de B2B-prijzen zichtbaar." | solar-west.be/b2b-registratie/（17:32:18Z） |
| Rebor（NL） | 单页 | 11 / 10 | VAT* | — | — | — | 页面载入 reCAPTCHA | — | shop-rebor.com/en/pages/installer-registration（20:55:50Z） |
| Solarbex（ES） | 单页 | 16 / 14 | CIF/NIF*、主营业务* | — | 选填 | 3 国：ES、PT、FR | 蜜罐（推断）`sbx_web_extra_oculta` | "Entiendo que Solarbex puede aprobar, rechazar o retirar el perfil profesional si no puede verificar la relación con el sector fotovoltaico, eléctrico o energético." | solarbex.com/registro-profesional/（17:25:06Z） |
| iSolarPro（AT/DE） | 单页 | 9 / 9 | — | 营业执照上传* | — | — | 页面载入 reCAPTCHA / hCaptcha 脚本 | "… müssen geeignete Nachweise vorgelegt werden, wie z.B. Gewerbeschein, Firmenbuchauszug oder Berufsberechtigung." | isolarpro.de/pages/b2b（20:55:45Z） |
| Procarte（PL） | 单页 | 9 / 6 | 公司名、NIP（都选填） | — | — | — | 页面载入 reCAPTCHA | — | procarte.pl/zarejestruj-sie/（17:30:58Z） |
| Akkusys（DE） | 单页（Shopware） | 17 / 12 | 公司名*、USt-IdNr.（选填）、是否申请商户门户* | 营业证明上传 | — | 27 项：DE、AT 在前，其余欧盟 + UK、Monaco | 蜜罐（推断）`first_name_confirmation`（"Ihr Name"，隐藏） | — | akkusys.shop/kundenaccount-erstellen → /account（20:59:08Z） |

只抓到说明文字、没有字段的同行：
- **pvXchange**（DE）："Die Anmeldung ist ausschließlich Gewerbekunden vorbehalten. Nach der Prüfung Ihrer Daten informieren wir Sie über den weiteren Verlauf Ihrer Anfrage. Die Bearbeitungszeit Ihrer Registrierung wird schnellstmöglich bearbeitet und nimmt maximal 1 bis 3 Werktage in Anspruch." — https://www.pvxchange.com/ （20:58:41Z）
- **photovoltaik-shop.com**（DE）："Senden Sie uns eine Kopie Ihrer Gewerbe-Anmeldung per Mail an registration@photovoltaik-shop.com. Wir überprüfen Ihre Gewerbe-Anmeldung und schalten Ihr Händlerkonto frei." — https://www.photovoltaik-shop.com/haendleranmeldung （17:24:54Z）
- **ecoABM**（PL）："Po zakończeniu rejestracji zweryfikujemy Twój NIP oraz branżę." — https://ecoabm.com/pl/wspolpraca/ （20:56:20Z）
- **Undersun**（PL）：自动核验、即时开户："NIP sprawdzamy w wykazie podatników VAT (biała lista Ministerstwa Finansów). Aktywny NIP = konto firmowe od razu, bez czekania na akceptację." — https://undersun.pl/dla-instalatorow/ （20:59:10Z）

排除：libra.no 是 Libra-Plast AS（门、舱盖），不是光伏批发商；Solbian 是组件厂；actec 与 3Buy 的注册页是通用账户页，没有 B2B 字段；Search4Solar 是平台，表单未渲染。

### 3.2 逐家要点（只写与本票有关的）

- **Memodo**：德语站要法律形式（57 项），选到需要登记的形式才出现 HR 号与 Amtsgericht；英文站（memodo-shop.com）没有法律形式这一段，并解释为什么要 VAT 号："Please note that we may ship your goods from one of our warehouses located in other European countries and therefore we require you to enter your VAT ID number."（https://www.memodo-shop.com/account/login?registerView=register ，17:19:52Z）。门槛原文："In order to become a customer of ours, you need to hold a business licence and be an installer."
- **Krannich**：没有密码字段；审核后才发"Zugangsdaten"。上传是选填，标题明说用来提速："Helfen Sie uns Ihre Shop-Freischaltung zu beschleunigen & laden Sie Ihren Gewerbeschein bzw. Handelsregisterauszug jetzt hoch."（17:20:31Z）。叉车、开票邮箱、会计联系人这些都是**交货与收款**问题（业主调研库 `10-wholesaler-krannich.md` §2.3 也得出同样判断）。
- **BayWa r.e.**：与业主调研库 2026-08-28 抓取时相比，表单仍是"Registrierungsanfrage"，仍有行业下拉；本次新看到 Cloudflare Turnstile。
- **EWS**：国家只列 29 个欧洲国家加"weitere"，并写明 "Hinweis: Kunden aus Österreich und der Schweiz nutzen zur Registrierung bitte die Internationale Seite"。另设一个短得多的"Multiplikator"注册（公司、语言、联系人、地址、电话、邮箱 ×2、密码 ×2，https://pv.de/multiplikator/registrierung/ ，17:20:35Z）。
- **Segen**：4 步表单第一步只问 "Let's get to know each other: First name* Surname* Email* Phone number*"，公司信息在后面几步；提交后销售回电，再核实，再开门户。
- **Sonepar**：身份标识采用"至少一项"规则，并把"总经理出生日期"放进注册——这是信用审查用的。
- **Rexel**：只收德国公司；审核含信用报告，FAQ 明说超过两个工作日是因为 "der Bericht zur Kreditwürdigkeit Deines Unternehmens noch in Bearbeitung ist"（17:21:07Z）。
- **PVSelected**：小团队分销商（业主调研库 `competitor-study-2026-10-01/competitors/analysis.md` 记为 2023 年均 5 人），表单 7 项（单一"Vollständiger Name"字段），仍然人工审批。
- **Solar-West**：WooCommerce 原生注册，用 Woo 的"发送设置密码链接"模式（表单文字 "Er wordt een link om een nieuw wachtwoord in te stellen naar je e-mailadres verzonden."），所以没有密码字段；第一个字段名为 `sw_b2b_guard_website`、标签 "Website"，从命名与位置看是蜜罐（推断）。
- **Undersun**：用国家 VAT 纳税人白名单自动核验 NIP，核验通过即开户——这是"全自动查证"的另一端，业主现在选的是人工查证，作为将来可选项记录。

### 3.3 频率小结（21 份抓到字段的表单）

21 份 = Memodo、Krannich、BayWa、IBC、EWS、Segen、Libra（第 1 步）、Alma、Sonepar、Natec、PVSelected、Densys、Senergia、Midsummer、Western Solar、Solar-West、Rebor、Solarbex、iSolarPro、Procarte、Akkusys。

| 字段 | 问的表单数 | 其中必填 | 读法 |
|---|---|---|---|
| 公司名 | 20 | 19 | 通用 |
| 地址（街道/邮编/城市） | 19 | 18 | 通用——同行把注册当客户主数据（信用、送货）；PVSelected 与 Alma 不问 |
| 电话 | 19 | 17 | 通用——与"销售回电"模式配套（Segen 明写回电） |
| VAT ID | 18 | 11（另 1 份"至少一项"） | 常见，一半以上必填；欧盟以外的申请人没有欧盟 VAT 号，需要替代标识 |
| 国家 | 13 | 12（Libra 预选、不标必填） | 不问的 8 份多是只做一国的店 |
| 网站 | 10 | 1（Natec） | 常见，几乎都是选填 |
| 公司登记号 | 8 | 6 | 常见 |
| 证件上传 | 8 | 3 | 常见；多数是选填或"提速" |
| 业务类型 / 行业 / 从业经验 | 8 | 7 | 常见 |
| 销售筛选（量、员工、来源） | 8 | 3 | 销售用途 |
| 注册时设密码 | 8 | 8 | 12 份不设密码：审核后发登录信息或发设置链接 |
| 姓名：分开 / 单一字段 | 16 / 4 | — | 单一字段：PVSelected、Midsummer、Western Solar、iSolarPro |

中位数 16 个输入、11 个必填（Segen 按 EU 版、Libra 只计第 1 步）；最短的真 B2B 审批表单是 PVSelected（7/5）。de-linker 现状 11/10，建议 9/7+1。

### 3.4 读法：为什么同行问这么多，哪些不适用 de-linker

1. **同行的注册 = ERP 客户主数据 + 信用开户 + 发货档案。** Rexel 做信用报告，Sonepar 要总经理出生日期，Krannich 问叉车、开票邮箱、会计联系人，Memodo 的付款页写信用额度需要 Creditreform 查询（业主调研库 `16-persona-epc-procurement.md` 引 memodo.de/zahlung）。de-linker 没有在线下单、没有账期、发货线下，开户只解锁"看净价 + 提交询盘"，注册不需要承担这些。
2. **同行的"审核"很多由销售完成**（Segen 回电；论坛里 Krannich 外勤发邮件追问"wie lange man denn schon im Geschäft sei"并要营业登记，见业主调研库 `11-wholesaler-baywa-ibc.md` §6.2 与 `20-friction-distributor-installer.md` §6.1）。电话字段跟这种模式配套。业主的模式是"按注册信息自己查证"（地图 #220），所以只需要**可查证的锚点**，不需要电话。
3. **证件上传是最重的一项**，同行 8 份有、3 份必填，而业主调研库记录的买家抱怨正是"Gewerbeanmeldung schicken"和半年排队。旧站表单也有上传、三步向导、电话必填，票 #224 已写明它不是目标；业主对现表单的评价是"像问卷"。
4. 业主调研库 `28-purchasing-procurement.md` 没有注册表单方面的内容（只涉及招标与采购单据），本研究没有引用它的结论。

---

## 4 表单长度、分组、必填的证据（b）

### 4.1 字段越少越好，能以后收的就以后收

- NN/g（Kathryn Whitenton，2016-05-01；抓取 17:23:08Z，https://www.nngroup.com/articles/web-form-design/ ）："**Keep it short**. … Remove fields which collect information that can be (a) derived in some other way, (b) collected more conveniently at a later date, or (c) simply omitted. … Every time you cut a field or question from a form, you increase its conversion rate — the business case for this guideline is that simple."
- Baymard（2024-06-26；抓取 17:24:19Z，https://baymard.com/research-articles/checkout-flow-average-form-fields ）："our research shows that, in general, the **number of form fields** in a checkout impacts overall usability far more than the number of steps." 以及 "most sites need only **8 form fields** in total for a checkout flow — yet the average in 2024 was 11.3 form fields"。同文："The average checkout flow in 2024 is 5.1 steps long and contains 11.3 form fields — and 17% of users have abandoned due to checkout complexity"。
- Baymard 同文对开户表单："Requiring users to create an account … will result in at least some users being **forced to consider** fields like *'Create a Password'* and *'Birthdate'* — which may cause some to abandon due to the intimidating nature of the checkout process."
- 注意：Baymard 的数据来自零售结账，不是 B2B 注册；方向（字段数比步骤数更重要、每个字段都有成本）可以迁移，具体百分比不能直接套用。

### 4.2 分组与单列

- NN/g（同上）："**Visually group related labels and fields**. … If your form asks about two different topics, section it into two separate groups of fields (and tag the groups for screen readers)." 以及 "**Present fields in a single column layout**. … (Exceptions to this rule: short and/or logically related fields such as *City*, *State*, and *Zip Code* can be presented on the same row.)"
- W3C WAI（抓取 17:23:40Z，https://www.w3.org/WAI/tutorials/forms/grouping/ ）："Grouping needs to be carried out visually and in the code, for example, by using the `<fieldset>` and `<legend>` elements to associate related form controls. Also, related entries of a `<select>` element can be grouped using `<optgroup>`."
- Baymard（2023-10-31；抓取 17:25:24Z，https://baymard.com/research-articles/avoid-multi-column-forms ）："single-column layouts resulted in fewer skipped fields, misinterpreted fields, and errors compared to multicolumn layouts"，并允许"Zip code"与"City"同一行这种概念上相连的小例外。
- W3C WAI 多页表单（17:23:40Z，https://www.w3.org/WAI/tutorials/forms/multi-page/ ）建议"divide long forms into multiple smaller forms"——这是对**长**表单；9 个字段不属于长表单，且 Baymard 的结论是步骤数次要。

### 4.3 每个问题都要说得出用途（question protocol）

- NHS 服务手册（抓取 17:25:52Z，https://service-manual.nhs.uk/content/how-to-write-good-questions-for-forms/make-sure-you-need-each-question ）："Only include a question when you know these things: you need the information to deliver the service; why you need it; who in the organisation uses the information and how; … how you'll check that the information is accurate (including any validation rules) …" 以及 "If you do not know how you'll use an answer, find out or remove the question."
- GOV.UK Design System（17:23:38Z，https://design-system.service.gov.uk/patterns/question-pages/ ）："You should make sure you know why you're asking every question and only ask users for information you really need." 与 "Make sure to only ask for a piece of information once within a single journey."
- 用到本票：§7 的每个字段都写明"业主怎么用它查证"；说不出查证用途的（电话、地址、采购量）就不在注册时问。

### 4.4 选项少用单选，选项多给搜索

- NN/g（同上）："Avoid drop-downs when there are only 2 or 3 options that could be displayed as radio buttons (which require only a single click or tap)." 以及 "for field values, also consider usage frequency, and list the most common values first when possible."
- Baymard（2018-11-12；抓取 17:24:37Z，https://baymard.com/research-articles/drop-down-usability ）："Drop-downs are generally a poor choice for offering fewer than 5 or more than 10 options"；"**78% of sites** in our benchmark include a country-selector drop-down in their checkout"；"Long country drop-downs, which often include **over two hundred options,** can be very difficult for users to get an overview of."；替代方案："a well-performing alternative to a drop-down is an **autocomplete field.**"
- GOV.UK Select 组件（17:23:38Z，https://design-system.service.gov.uk/components/select/ ）："The select component should only be used as a last resort in public-facing services because research shows that some users find selects very difficult to use."
- Baymard 移动结账（2013-10-01；17:25:37Z，https://baymard.com/research-articles/mobile-checkout ）："For country selection this can be IP geo-targeting or at the very least an intelligent country auto-complete."

### 4.5 必填与选填

- Baymard（2018-10-01，2021 基准；17:24:52Z，https://baymard.com/research-articles/required-optional-form-fields ）："failing to explicitly mark both required and optional fields leads to unnecessary validation errors, user confusion over which fields they must complete, a slower checkout process, and even **abandonments**"；"only 14% of sites marking both fields"。
- NN/g（同上）："Limit the form to only 1 or 2 optional fields, and clearly label them as optional." 建议方案的选填正好是 2 个（网站、VAT ID）。
- NHS 的做法相反（"Do not mark essential fields"，只标选填）。现站已用 Woo 的"*"加"(optional)"，与 Baymard 一致，保持。

### 4.6 姓名字段

- Baymard（同 4.1 文）："During testing, **42%** of participants typed their full name in the *'First Name'* field at least once." 以及 "**89%** of sites in our e-commerce UX benchmark have more than one *'name'* field."；"When testing sites with a *'Full Name'* field, **only 4% of users** briefly hesitated"。
- 同行：21 份里 16 份分开、4 份单字段（§3.3）。本票的取舍见 §7.2。

---

## 5 数据最小化（DSGVO Art. 5(1)(c) 与 Art. 25(2)）

- Art. 5(1)(c) 原文（DE，抓取 17:28:20Z，https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32016R0679 ）：personenbezogene Daten müssen "dem Zweck angemessen und erheblich sowie auf das für die Zwecke der Verarbeitung notwendige Maß beschränkt sein („Datenminimierung“)"。EN（17:23:52Z）："adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed (‘data minimisation’)"。
- Art. 25(2)（EN）："The controller shall implement appropriate technical and organisational measures for ensuring that, by default, only personal data which are necessary for each specific purpose of the processing are processed. That obligation applies to the amount of personal data collected …"
- Recital 14（EN）："This Regulation does not cover the processing of personal data which concerns legal persons and in particular undertakings established as legal persons, including the name and the form of the legal person and the contact details of the legal person." —— 公司名、公司网站、法人的 VAT 号不是个人数据；联系人姓名、邮箱、电话是；个体户（Einzelunternehmer）的地址与税号也是个人数据。
- ICO（17:24:16Z，https://ico.org.uk/…/data-minimisation/ ）："So you should identify the minimum amount of personal data you need to fulfil your purpose. You should hold that much information, but no more."
- CNIL（17:26:41Z，https://www.cnil.fr/fr/minimiser-les-donnees-collectees ）："Vous ne devez collecter que les données personnelles qui sont adéquates, pertinentes et nécessaires au regard des finalités de votre traitement telles que définies au moment de la collecte." 并举例：地理定位一类非必要功能应让用户自己选择是否使用。
- **用到本票**：注册的目的是"开账户 + 让业主查证公司"。为此必要的个人数据是联系人姓名、邮箱、密码；电话与个体户地址不是这一目的所必需，按 Art. 25(2)"by default"不应在注册时收，到 Proforma（开具单据这一目的）时再收。

---

## 6 业主怎样用最少的输入查证一家公司

### 6.1 VAT ID 与 VIES：欧盟内有效，但德国号码不回名称

- VIES FAQ（抓取 17:22:26Z，https://ec.europa.eu/taxation_customs/vies/#/faq ）："Depending on the national rules on data protection, some Member States / Northern Ireland will also provide the name and address linked to the given VAT number as they are recorded in the national databases." 以及 "it is possible that a VAT number, even if correct, will not be validated through VIES, because the owner of that VAT number is not involved in intra-EU transactions or did not register for that purposes with his/her tax administration."
- Your Europe（17:26:09Z，https://europa.eu/youreurope/business/finance-and-tax/vat/check-vat-number-vies/index_en.htm ）："VIES … is a **search engine** (not a database)"；查不到时："request more information at **national level with your national authorities**. You should then be able to confirm … if the VAT number is 'associated with' a certain **name and address**."
- **实测（Apify run `KIEtMOAObWdiPjEJa`，2026-10-16T20:56:41Z–20:56:47Z，VIES REST `/rest-api/ms/{CC}/vat/{number}`；号码取自对方 Impressum）**：

| 号码（来源） | isValid | name | address |
|---|---|---|---|
| DE191691979（EWS Impressum，业主调研库 peer-10） | true | `---` | `---` |
| DE328945324（PVSelected Impressum，业主调研库 peer-1） | true | `---` | `---` |
| NL819150757B01（Libra Energy 公司信息页，本次抓取） | true | `LIBRA ENERGY B.V.` | `EENDRACHTSSTRAAT 00199 1951AX VELSEN-NOORD` |
| HU12538306（Solar&Solar Impressum） | true | `SOLAR&SOLAR KERESKEDELMI ÉS SZOLGÁLTATÓ KORLÁTOLT FELELŐSSÉGŰ TÁRSASÁG` | `VERES PETER ÚT 51 1163 BUDAPEST` |

- 结论：对荷兰、匈牙利等国，VIES 一步就能把号码对到公司名与地址；**对德国（核心市场）只能证明"存在一个有效的德国号码"**，申请人填了别人的号码也看不出来。现站的 VIES 校验（`Registration/ViesClient.php`）只存有效/无效，不存名称。
- BZSt 的"qualifizierte Bestätigung"能对名称地址，但对象是**外国**号码（抓取 17:26:25Z，https://www.bzst.de/DE/Unternehmen/Identifikationsnummern/Umsatzsteuer-Identifikationsnummer/AuslaendischeUSt-IdNr/auslaendische_ust_idnr_node.html ）："Das Bestätigungsverfahren ermöglicht deutschen Unternehmen die Prüfung, ob zum Zeitpunkt der Leistungserbringung die Lieferung oder sonstige Leistung an ein in einem anderen EU-Mitgliedsstaat registriertes Unternehmen erbracht wird"。德国客户的号码不在这条路上。

### 6.2 德国：Handelsregister 免费可查

- BMJV（17:26:28Z，https://www.bmjv.de/DE/themen/wirtschaft_finanzen/handels_gesellschaftsrecht/handelsregister/handelsregister_node.html ）："Das Registerportal unter www.handelsregister.de … kann von jedem eingesehen werden." 以及 "Seit dem 1. August 2022 ist der Abruf dieser Dokumente beim Handelsregisterportal und beim Unternehmensregister kostenfrei möglich."
- 限制：独资的 Handwerksbetrieb 常常不在 Handelsregister（只有 Gewerbeanmeldung），所以 HR 号不能做必填项——这也是 Sonepar 采用"至少一项"的原因。
- 其他欧盟国家的登记处可经欧盟 e-Justice 门户统一检索（抓取 2026-10-16T21:13:41Z，https://e-justice.europa.eu/topics/registers-business-insolvency-land/business-registers-search-company-eu_en ）："As of June 2017 the business registers of all EU countries have been interconnected and become searchable."

### 6.3 英国、瑞士

- 英国 Companies House（17:21:47Z，https://find-and-update.company-information.service.gov.uk/ ）：按 "company name, number or officer name" 免费检索；页面同时提示 "Companies House does not check the accuracy of the information filed"。
- 英国 HMRC（17:21:52Z，https://www.gov.uk/check-uk-vat-number ）："Use this service to check: if a UK VAT registration number is valid; the name and address of the business the number is registered to"，并写 "You can find the VAT numbers for most businesses and organisations on their invoices, receipts or website."
- 瑞士 UID 登记（17:22:02Z，https://www.uid.admin.ch/ ）：按 "Name / UID" 公开检索，结果含 "VAT register status"；Zefix（https://www.zefix.admin.ch/ ，17:27:26Z）为商业名称索引。

### 6.4 网站：所有欧盟国家都适用的查证锚点

- e-Commerce 指令 2000/31/EC 第 5(1) 条（抓取 17:23:53Z，https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32000L0031 ）："the service provider shall render easily, directly and permanently accessible … at least the following information: (a) the name of the service provider; (b) the geographic address at which the service provider is established; (c) … his electronic mail address …; (d) where the service provider is registered in a trade or similar public register, the trade register in which the service provider is entered and his registration number …; (g) where the service provider undertakes an activity that is subject to VAT, the identification number …"
- 德国 §5 DDG（17:24:07Z，https://www.gesetze-im-internet.de/ddg/__5.html ）：要求公示 "den Namen und die Anschrift …"、"die Angabe des Handelsregisters … und die entsprechende Registernummer"、以及 "eine Umsatzsteueridentifikationsnummer nach § 27a … die Angabe dieser Nummer"。
- 所以：申请人给出网站 → 业主打开其 Impressum / Legal notice → 核对公司名、地址、登记号、VAT 号是否与注册信息一致 → 需要时再去 VIES 或登记处二次确认。这对德国申请人恰好补上 §6.1 的缺口；对欧盟以外的申请人也通常可行（多数公司网站有法律声明，但非欧盟没有同等法定义务——列为局限）。邮箱域名与网站域名是否一致，是业主顺手可看的第二信号（推断，非来源结论）。
- 适用边界：e-Commerce 指令约束"信息社会服务"提供者；纯展示型小网站是否必然在列是法律细节，但德国商业网站普遍带 Impressum。没有网站的小公司走 VAT ID 一路（§7.1 的"至少一项"）。

### 6.5 每国一句话查证路径（给业主）

| 申请人国家 | 先看 | 再看 |
|---|---|---|
| 德国 | 网站 Impressum（名称、地址、HR 号、USt-IdNr.） | handelsregister.de 免费检索；VIES 只确认号码有效 |
| 其他欧盟国家 | VIES（多数国家回名称与地址） | 网站法律声明；e-Justice 门户的欧盟登记处联网检索 |
| 英国 | gov.uk 的 VAT 号查询（回名称与地址） | Companies House |
| 瑞士 | uid.admin.ch（含 VAT 状态） | Zefix；网站 Impressum |
| 其他国家 | 网站 | 业主自行判断；必要时邮件追问（sales@） |

---

## 7 推荐字段清单的详细理由（c）

### 7.1 公司分组（"您的公司"）

1. **公司名称（必填）**——查证对象；Woo 原生 `billing_company`，Proforma 请求页也已设为必填（`Settings/WooOptions.php` 固定 `woocommerce_checkout_company_field = required`）。
2. **业务类型（必填，3 个单选）**——是"同行客户"的自报项（AGENTS.md §1：客户是安装商、EPC、经销商），业主拿它和网站内容对照；同行 8 份有同类问题。3 个选项用单选：NN/g、Baymard、GOV.UK 一致（§4.4），Segen 的同类问题就是单选。
3. **国家（必填）**——决定查证路径（§6.5）、VAT 处理（§10），见 §8。
4. **公司网站（选填）** 与 5. **VAT ID（选填）**，**两者至少一项**：
   - 理由：只有公司名 + 国家时，业主要靠搜索引擎猜是哪家公司；给出网站或 VAT ID，就有了可直接核对的官方锚点（§6）。
   - 为什么不是网站必填：并非每个小安装商都有网站；21 份同行表单只有 Natec 要求必填网站。
   - 为什么不是 VAT 必填：德国号码在 VIES 里对不到名称（§6.1）；欧盟以外的申请人没有欧盟 VAT 号；部分小企业没有 USt-IdNr.。
   - 先例：Sonepar 的 "Bitte teilen Sie uns mindestens ein Kriterium mit"（HR 号 / 税号 / USt-ID）。
   - 两项都没有的申请人：表单提示一句写邮件到 sales@de-linker.com（AGENTS.md §2：公司类问题一句话转团队邮箱）。
   - VIES 校验照旧，结果照旧只作标记、不挡注册（`VatProfile` 现行规则）。
   - 实现提示（给 #225）：网站字段用文本输入 + `inputmode="url"`，服务端补全 `https://`；不要用 `type="url"`（浏览器会拒绝"www.firma.de"这种写法）。蜜罐字段**不能**再叫 website / url（§9.2）。

### 7.2 联系人与登录分组（"您和您的登录"）

6–7. **名、姓（必填，同一行）**：保留 Woo 原生两个字段，因为 Proforma 与账单地址用的是 Woo 的 `billing_first_name` / `billing_last_name`，把一个"全名"拆成两段在代码里是有损的（如 "van der Berg"）。Baymard 的单字段证据（§4.6）记为**可翻案项**：如果 #225 的视觉/可用性验收发现用户把全名填进"名"，再评估改单字段。同一行排布符合 NN/g 的"logically related fields"例外，也是 Woo 账单字段默认的 `form-row-first` / `form-row-last` 排法。
8. **邮箱（必填）**：登录名与通知地址；同行全部都有。
9. **密码（必填）**：Woo 原生，带 Woo 自带强度计。

### 7.3 可选：再少一个字段（不作默认）

WooCommerce 原生设置 "**Send password setup link** — Send new users an email with a link to set up their password."（Woo 文档，抓取 17:21:24Z，https://woocommerce.com/document/configuring-woocommerce-settings/accounts-and-privacy/ ；本仓现在固定为 `woocommerce_registration_generate_password = no`）。Solar-West 就是这么做的。好处：少一个字段，并证明邮箱能收信。代价：Woo 原生欢迎信在本站已关（`RegistrationReceivedEmail` 取代），设置密码的链接要并入现有邮件；用户在批准前后都要先收到这封信才能自己登录；它对机器人没有阻挡作用（GSA 能自动完成邮箱验证，§9.1）。所以不作默认，列为业主可选。

### 7.4 不加的字段及理由

| 字段 | 同行情况 | 不加的理由 |
|---|---|---|
| 电话 | 19/21 问 | 同行用于销售回电；业主查证不靠电话（地图 #220）；GDPR 默认最小化（§5）。需要时在 Proforma 收 |
| 地址 | 19/21 问 | 见 §10，挪到 Proforma |
| 证件上传 | 8/21，3 份必填 | 最重的摩擦；业主可在登记处自己查；存储证件文件增加个人数据处理 |
| 法律形式、登记号 | 8/21 | 网站 Impressum 与登记处能查到；独资经营者常常没有 HR 号 |
| 采购量、员工数、"从哪知道我们" | 8/21 | 销售筛选，与查证无关（NHS："If you do not know how you'll use an answer … remove the question"） |
| 称谓（Anrede） | 常见 | Sie 体邮件可用全名称呼；不影响查证 |

---

## 8 国家下拉（d）

### 8.1 证据

- 同行实测（§3.1）：
  - 全部国家、重点在前：**Krannich**（DE 站 Deutschland、Belgien、Niederlande、Österreich、Polen 在前，其后全部国家字母序，共 251 项）；**Libra Energy**（预选 Netherlands，其后全部国家字母序）。
  - 只列服务区域、重点在前：**Memodo**（DE、CZ、PL、SK、UK 在前，其后字母序，共 38 项）；**Akkusys**（DE、AT 在前，共 27 项）；**EWS**（29 个欧洲国家 + "weitere"）。
  - 只列极少国家：Senergia（4）、Solar-West（5）、Solarbex（3）。
- NN/g："list the most common values first when possible"（§4.4）。
- Baymard 国家选择器（2011；抓取 17:22:57Z，https://baymard.com/labs/country-selector ）："we turn a standard drop-down into an advanced auto-complete field. This means the drop-down remains accessible, while providing a much better experience in modern browsers - handling typos, multiple spelling sequences, synonyms and prioritization."
- W3C：`<optgroup>` 用于给下拉条目分组（§4.2）。
- WooCommerce 11.2 源码：
  - 国家列表默认按语言排序（`WC_Countries::get_countries()` 中 `woocommerce_sort_countries` 过滤器，默认 true，`wc_asort_by_locale`）。
  - 允许国家可用 `woocommerce_countries_allowed_countries` 过滤器重排（`class-wc-countries.php` 第 493–498 行）。
  - `woocommerce_form_field()` 的 `country` 类型只输出扁平的 `<option>`，不支持 `<optgroup>`（`includes/wc-template-functions.php` 第 3457–3483 行）。
  - Woo 自带大洲数据 `i18n/continents.php`：`'EU' => array( 'name' => __( 'Europe', 'woocommerce' ), 'countries' => array( 'AD', 'AL', 'AT', … 'XK' ) )`，共 53 个代码（含 GB、CH、NO、TR、UA），并有 `get_continents()`、`get_continent_code_for_country()`。
  - 可搜索选择器：Woo 在账户页加载 `selectWoo`（`class-wc-frontend-scripts.php` 第 491–493 行），但把国家下拉变成可搜索的 `wc-country-select` 脚本只作为结账 / 地址脚本的依赖加载；线上注册页实测没有可搜索容器（§2）。

### 8.2 建议

1. **国家范围**：全部国家（Woo 销售地区保持 "all"，业主裁定）。
2. **排序**：用 `woocommerce_countries_allowed_countries` 把 Woo 大洲数据里属于 Europe 的国家排在前面（各自按当前语言字母序），其余国家随后（字母序）。这只是 Woo 原生过滤器上的排序，没有手写名单。
3. **分组标题**：是否在"欧洲 / 其他国家"之间加 `<optgroup>` 标签，由 #225 在视觉评审时决定。不加标题时，字母序在欧洲块结束处重新开始，可能让人困惑；加标题需要在 `woocommerce_form_field_country` 输出上做少量自定义标记（只是语义 HTML，没有样式），属于"Woo 原生做不到"的最后手段，须按 AGENTS.md §5 在规格里写明穷尽证明。Krannich、Memodo 的做法是不加标题、只把重点国家前置。
4. **可搜索**：在注册端点加载 Woo 自带的 `wc-country-select`（selectWoo 增强），满足 Baymard 的自动完成建议与 GOV.UK"select 是最后手段"的顾虑；无 JS 时仍是原生下拉。
5. **默认值**：现在默认德国（店铺所在国），保留。可选增强：Woo 原生地理定位（"Default customer location: Geolocate"，需要免费的 MaxMind GeoLite2 许可证，Woo 文档 https://woocommerce.com/document/maxmind-geolocation-integration/ ，抓取 17:21:36Z），用 `wc_get_customer_default_location()` 预选访客所在国。CNIL 把地理定位列为应让用户自己选择的非必要功能（§5）；这里只是一个可改的默认值、IP 查询在本机数据库完成，是否启用由业主定。

---

## 9 防机器人（e）

### 9.1 对手是谁

- OWASP OAT-019 Account Creation（抓取 17:24:53Z，https://owasp.org/www-project-automated-threats-to-web-applications/assets/oats/EN/OAT-019_Account_Creation ）："Bulk account creation, and sometimes profile population, by using the application's account sign-up processes. The accounts are subsequently misused for generating content spam, … and skewing search engine optimisation (SEO), reviews and surveys."；相关 CWE 含 "799 Improper Control of Interaction Frequency"。
- GSA Search Engine Ranker 官方产品页（抓取 17:26:49Z，https://www.gsa-online.de/en/product/search_engine_ranker/ ）："It dynamically discovers new platforms, creates accounts and submits content."；"Seamlessly connects with 30+ CAPTCHA services"；"**Automated Email Verification & Account Registration** — Import email accounts and use them for registration and verification tasks as part of a project."
- 推论：图片验证码（可外包识别）和"邮箱验证"（能自动完成）单独都挡不住这类工具；它冲的是能识别的平台注册表单——WooCommerce 的账户注册页正是这种平台表单。

### 9.2 第一层：蜜罐 + 最短填写时间（推荐立即做）

- W3C APA 工作组《Inaccessibility of CAPTCHA》（Group Draft Note，2021-12-16，工作草案，按文件自述只能作为 work in progress 引用；抓取 17:23:48Z，https://www.w3.org/TR/turingtest/ ）§2.2.4："Providing a CAPTCHA visible to robots but not to humans appears to be sufficiently successful to be supported in several content management systems … The form is created to attract robots and then hidden from the user by markup such as CSS-Hidden. It's an approach that is easily implemented even in hand authored markup and should be considered." 同文 §2.2.5 也列出"Limited-Use Accounts"——de-linker 的待审账户本来就是受限账户。
- 同行实证（§3.1）：Solar-West 的 `sw_b2b_guard_website`（标签 "Website"，排在姓名之前，表单里没有别的网站字段）、Solarbex 的 `sbx_web_extra_oculta`（"oculta" 即"隐藏"，排在最前；真正的网站字段 "Web de la empresa" 在后面）、Akkusys（Shopware）的隐藏字段 `first_name_confirmation`（标签 "Ihr Name"，与真实的名字段并存）。三者都是按字段名、位置与隐藏方式**推断**为蜜罐，对方页面没有自述。
- 做法要点（交 #225 规格）：
  - 用 Woo 原生钩子：`woocommerce_register_form` 输出隐藏字段与签名时间戳，`woocommerce_process_registration_errors`（现有 `Fields::validate()` 所在的过滤器）判定；失败在 `wc_create_new_customer()` 之前抛错，因此**不建账号、不发信**。
  - 蜜罐字段名不要用 website / url / homepage（表单将新增真实的网站字段，且浏览器自动填充可能填它）；加 `autocomplete="off"`、`tabindex="-1"`、`aria-hidden="true"`；隐藏用 WindPress 里的样式类，不在 PHP 里写内联样式（AGENTS.md §5）。
  - 时间戳用 HMAC 签名，不依赖会话；最短秒数必须写来源注释（AGENTS.md §4）——本研究没有找到高可信的阈值来源，建议 #225 用真实填写时间（含浏览器自动填充）实测后定，列为未知（§11）。
  - 拦截时给通用错误并留 sales@ 联系方式，不要假装成功（误伤的人会以为已注册）。
  - 用 Woo 自带日志（`wc_get_logger()`）计数拦截次数，作为是否上第二层的依据。
- 成本与隐私：零第三方、零 Cookie、零界面负担；不把访客数据交给任何外部服务。

### 9.3 第二层：Cloudflare Turnstile（仅当第一层不够）

- 免费与限制（Cloudflare 文档，最后更新 2026-08-14，抓取 17:24:41Z，https://developers.cloudflare.com/turnstile/plans/ ）：Free 计划 "Up to 20 widgets"、"Unlimited challenges (traffic or verification requests)"、"WCAG 2.2 AAA compliance: Yes"。
- 部署方式（17:24:27Z，https://developers.cloudflare.com/turnstile/ ）："Turnstile can be embedded into any website without sending traffic through Cloudflare and works without showing visitors a CAPTCHA."；Managed 模式 "Automatically chooses between non-interactive or checkbox challenge based on visitor risk level. No images or text to decipher."（https://developers.cloudflare.com/turnstile/concepts/widget/ ，17:28:41Z）。
- 必须服务端校验（最后更新 2026-09-16，17:24:40Z，https://developers.cloudflare.com/turnstile/get-started/server-side-validation/ ）："You must call the Siteverify API to complete your Turnstile implementation. The client-side widget alone does not protect your forms."；"**Tokens can be forged.**"；"**Tokens expire.** Each token is valid for 300 seconds (5 minutes) after generation."；"**Tokens are single-use.**"
- 数据（Turnstile Privacy Addendum，2025-06-18，17:24:41Z，https://www.cloudflare.com/turnstile-privacy-policy/ ）："Cloudflare Turnstile processes a variety of client-side signals (“Signals”) such as client IP address, TLS Fingerprint, User-Agent Header and Sitekey and associated origin."；Cloudflare 对网站保护是 processor，对"improve Turnstile's bot detection capabilities"是 controller，依据其 legitimate interests。
- 同行：BayWa r.e. 的注册页使用 Turnstile；Western Solar 页面载入了 Turnstile 脚本。
- 代价：注册路径多一个外部依赖（Cloudflare 不可用时要决定放行还是拦截）；个人数据流向美国公司，需要更新隐私政策、签处理协议，并判断德国 TDDDG §25 的同意义务（本研究未做法律判断，§11）；300 秒令牌对填得慢的人需要自动刷新。
- 实现：放在仓库插件里（AGENTS.md §5：代码只进仓库插件）。免费插件 "Simple Cloudflare Turnstile" 支持 WooCommerce 注册表单（"this plugin is completely free with no paid version"，https://wordpress.org/plugins/simple-cloudflare-turnstile/ ，17:25:03Z），可作为参考实现，但不建议为此新增插件。

### 9.4 不推荐的选项

| 选项 | 不推荐的理由 |
|---|---|
| Google reCAPTCHA | 数据流向 Google；W3C 同文记录 v2 音频替代被撤后部分用户被拒之门外；同行多用它，但它与"零第三方"的第一层相比没有必要 |
| 图片验证码（EWS 的 Sicherheitscode） | GSA 接 30 多种验证码识别服务（§9.1）；W3C 记录的无障碍问题；Baymard："CAPTCHAs are **difficult to decipher**. … obscuring text and asking your visitors to repeat that text will hurt your conversion rate badly."（2009，https://baymard.com/research-articles/captcha-conversion-rate ，17:25:02Z） |
| Akismet | 商业站点要付费（"Pro … For professional or commercial sites and blogs. $9.95 per month, billed yearly"，https://akismet.com/pricing/ ，17:21:17Z）；AGENTS.md：不买新付费插件 |
| WP Armour（免费蜜罐插件） | 免费版支持列表有 "WP Registraton"、"WooCommerce Reviews Pro"，没有 WooCommerce 账户注册表单（https://wordpress.org/plugins/honeypot/ ，17:25:14Z）；且第一层在仓库插件里只需很少代码 |
| 只靠邮箱验证 | GSA 能自动完成（§9.1） |
| 只靠人工审批 | 审批挡得住"看价"，挡不住建号和两封邮件的成本（§2） |

---

## 10 挪到询盘 / Proforma 的信息

- **为什么能挪**：Proforma 请求页就是 Woo 结账页（`Inquiry/Checkout.php`），使用 Woo 原生账单字段；账单地址、国家、公司（本站已固定为必填）都在这里收，并保存到客户资料，下次询盘预填。客户也可在账户的公司页（`edit-address` 端点改名为 `company`）随时填写。
- **为什么应该挪**：地址印在 Proforma 上，是开单所需；业主查证要的是公司身份（§6），不是街道。NN/g 的"collected more conveniently at a later date"（§4.1）与 GDPR"by default only … necessary for each specific purpose"（§5）指向同一做法；GOV.UK"only ask … once"——地址只在 Proforma 问一次。
- **VAT ID 在 Proforma 处是法律必需（跨境欧盟）**：
  - 指令 2018/1910 修订后的第 138(1)(b) 条（抓取 17:23:53Z，https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32018L1910 ）："the taxable person or non-taxable legal person for whom the supply is made is identified for VAT purposes in a Member State other than that in which the dispatch or transport of the goods begins and has indicated this VAT identification number to the supplier."；其 recital 7 说明 VIES 登记的 VAT 号由形式要求变为 "a substantive condition for the application of exemption"。
  - §6a(1) Nr. 4 UStG（17:28:20Z，https://www.gesetze-im-internet.de/ustg_1980/__6a.html ）："der Abnehmer … hat gegenüber dem Unternehmer eine ihm von einem anderen Mitgliedstaat erteilte gültige Umsatzsteuer-Identifikationsnummer verwendet."
  - 站上现有的 VAT 账单字段（`Registration/BillingVatField.php`）已在 Proforma 请求页出现并做 VIES 校验，询盘上留存校验结论；注册时填过就预填。是否把它在"欧盟跨境"时设为必填，属于 Proforma 规则，不在本票范围（交 #225 或后续）。
- **电话**：Woo 11.2 的账单电话字段是否必填由 `woocommerce_checkout_phone_field` 决定（`CartCheckoutUtils::get_phone_field_visibility()`，`src/Blocks/Utils/CartCheckoutUtils.php` 第 288–301 行；经典与区块结账共用）：选项未设置时，区块结账默认回落为 optional，其余情况回落为 required。本站未在 `WooOptions` 里固定这一项，线上实际取值未核实（§11）。
- **给 #225 的连带改动**：团队通知邮件 `templates/emails/linker-new-customer.php` 目前有 "Address" 一行，应改为显示网站（可点击）、VAT ID 与校验结论、国家；后台账户页显示同一套信息（#225 完成标准已写明"通知邮件与后台账户页显示同一套信息"）。

---

## 11 未知与待证（f）

1. **"网站或 VAT ID 至少一项"会挡掉多少正当申请人**：没有数据。上线后看被这条规则拦下又发邮件来的数量。
2. **蜜罐 + 时间陷阱对 GSA 的实际拦截率**：没有一手数据（W3C 只说"sufficiently successful"，GSA 官方页不谈蜜罐）。上线后用日志计数；若仍有机器人注册，再上 Turnstile。
3. **时间陷阱的秒数**：没有高可信来源；须在 #225 实测后定，并按 AGENTS.md 写来源注释。
4. **Turnstile 的法律评估**：德国 TDDDG §25 是否要求同意、隐私政策措辞、处理协议——未判断。
5. **业主是否会打电话核实申请人**：若会，电话就成了查证字段（同行 19/21 问电话，Segen 明写回电）。这是只有业主知道的事实。
6. **Rexel 注册表单的字段**：`https://www.rexel.de/register` 在两次 Apify 运行（`ajn56odWa3VIrIdYE`；`HDAYXbespdEVNb5ox`，住宅代理、等待 25 秒）中都只渲染页脚，字段未取到；本研究只用其 FAQ。Segen 德国门户的注册是脚本弹层，未取到；用的是同一家 SegenSolar GmbH 欧洲站的 HubSpot 表单。Libra Energy 只取到第 1 步。SolarSell（UK）与 Power-SCS（PT）两种代理下都没打开，未列入对照。
7. **线上 Proforma 请求页的字段配置**（电话是否必填、地址必填项）：需要已批准账号登录才能看，本研究未实走。
8. **欧洲块的边界**：Woo 的 Europe 包含 RU、BY、TR、UA 等；"所有国家都可注册"是业主裁定，涉及受制裁国家的销售限制不在本研究范围，由业主的人工审批把关。
9. **自动核验（Undersun 模式）**：VIES 对多数欧盟国家能回名称与地址，理论上可做"名称一致即自动批准"，但业主现在选择人工查证；作为将来选项记录，不展开。
10. **e-Justice 欧盟登记处联网检索**：只取到说明页（检索界面是脚本组件，未实际查询）；各国查询是否都能免费看到完整登记信息，取决于各国规则，未逐国核实。

---

## 附录 A：Apify 运行与原始数据

| run id | actor | 用途 | 开始 / 结束（UTC） | 条目 | raw 文件 |
|---|---|---|---|---|---|
| uJGH4NVjIpwj70O1V | apify/google-search-scraper | 注册页发现（18 个查询，7 种语言） | 2026-10-16 17:18:36 / 17:19:38 | 18 | `raw/out-serp-1.json` |
| Zkh60GTMq3SyY2jCX | apify/google-search-scraper | 可用性、GDPR、查证、防机器人来源发现（18 个查询） | 17:20:23 / 17:20:56 | 18 | `raw/out-serp-2.json` |
| Tc4wxjkt4ffu3GwqR | apify/playwright-scraper | 表单实抓第 1 批（含 de-linker EN/DE） | 17:19:23 / 17:26:16 | 16 | `raw/out-forms-1.json` |
| yLWiHQgxCJ3agF7zV | apify/website-content-crawler | 来源正文第 1 批 | 17:21:10 / 17:27:05 | 33 | `raw/out-wcc-1.json` |
| fbLTubknHdkOL3LvO | apify/website-content-crawler | 来源正文第 2 批 | 17:24:00 / 17:27:45 | 21 | `raw/out-wcc-2.json` |
| btYejpzM8o8wb63XF | apify/playwright-scraper | 表单实抓第 2 批 | 17:24:39 / 17:38:19 | 22 | `raw/out-forms-2.json` |
| 1yn6F9GhZSUDKoXNN | apify/website-content-crawler | 来源正文第 3 批（DSGVO DE、§6a UStG 等） | 17:28:12 / 17:30:05 | 8 | `raw/out-wcc-3.json` |
| smtxGnDNKyj4Jtn9n | apify/playwright-scraper | 点击进入注册入口 + 失败重试 | 20:53:49 / 20:57:27 | 11 | `raw/out-forms-3.json` |
| KIEtMOAObWdiPjEJa | apify/playwright-scraper | VIES REST 实测 4 个号码 | 20:56:27 / 20:56:49 | 1 | `raw/out-vies.json` |
| ajn56odWa3VIrIdYE | apify/playwright-scraper | iframe 内表单（Segen HubSpot）、Libra、Rexel | 20:58:19 / 20:59:23 | 5 | `raw/out-forms-4a.json` |
| LaYnPHKPO8LiDZvmw | apify/playwright-scraper（RESIDENTIAL 代理） | 数据中心代理失败页重试 | 20:58:22 / 20:59:14 | 3 | `raw/out-forms-4b.json` |
| HDAYXbespdEVNb5ox | apify/playwright-scraper（RESIDENTIAL，等待 25 秒） | Rexel 注册页再试 | 21:02:44 / 21:03:28 | 1 | `raw/out-forms-5.json` |
| kgxsU5wg8VERhRopB | apify/website-content-crawler | e-Justice 登记处检索页（第 2 次；第 1 次在 yLWiHQgxCJ3agF7zV 中失败） | 21:02:47 / 21:10:20 | 0 | — |
| 799LbM4bqJeEaSRtq | apify/playwright-scraper（RESIDENTIAL） | e-Justice 登记处检索页（第 3 次，成功） | 21:13:12 / 21:13:42 | 1 | `raw/out-forms-6.json` |

未成功的尝试：`apify/web-scraper` 两次启动均被拒（需在 Apify 控制台授予完全权限，属账户所有者操作，未代为授予）；e-Justice 页面前两次在 website-content-crawler 下返回 0 条，第三次换 Playwright + 住宅代理成功。

## 附录 B：本仓与本机核对点（只读）

- `plugins/linker-commerce/includes/Registration/Fields.php`（字段、校验、保存、默认国家）
- `plugins/linker-commerce/includes/Registration/{VatProfile,ViesClient,VatNumber,BillingVatField}.php`（VIES 与 VAT 账单字段）
- `plugins/linker-commerce/includes/Registration/Emails/{NewCustomerEmail,RegistrationReceivedEmail}.php`（注册触发的两封信）
- `plugins/linker-commerce/includes/Settings/WooOptions.php`（固定的 Woo 选项）
- `plugins/linker-commerce/templates/myaccount/auth/form-register.php`（三编号小节的模板）
- `plugins/linker-commerce/templates/emails/linker-new-customer.php`（通知邮件字段行）
- WooCommerce 11.2.0：`includes/class-wc-form-handler.php`（注册处理）、`includes/class-wc-countries.php`（排序与允许国家过滤器）、`includes/wc-template-functions.php`（country 字段渲染）、`includes/class-wc-frontend-scripts.php`（selectWoo 加载条件）、`i18n/continents.php`（Europe）、`src/Blocks/Utils/CartCheckoutUtils.php`（电话字段默认）

## 附录 C：业主调研库引用

- `industry-research-2026-09-20/09-wholesaler-memodo.md`（登录面板原文 "Registration only takes a few moments and is exclusively reserved for business customers."；本次实抓的 Memodo 注册表单补上了库里缺的字段层）
- `industry-research-2026-09-20/10-wholesaler-krannich.md` §2.3（Krannich 字段，2026-08/09 抓取；本次复核一致）
- `industry-research-2026-09-20/11-wholesaler-baywa-ibc.md` §4.3、§6.2 与 IBC HomeOne 问卷句（"Nach einer internen Bewertung melden wir uns bei Ihnen."，https://www.ibc-solar.de/installateure/ibc-home-one-partner/ ）
- `industry-research-2026-09-20/12-wholesaler-sonepar-rexel.md` §2（Sonepar 字段、Rexel FAQ）
- `industry-research-2026-09-20/13-persona-meisterbetrieb.md` §4.8（注册墙原文列表）
- `industry-research-2026-09-20/16-persona-epc-procurement.md`（Memodo "Position*"、BayWa 行业选项、Natec 问卷，2026-08-28 抓取）
- `industry-research-2026-09-20/18-persona-secondary-distributor.md`（EWS Multiplikator 注册）
- `industry-research-2026-09-20/20-friction-distributor-installer.md` §2.1、§6.1（Memodo FAQ 所需证件、Krannich 半年排队论坛帖）
- `competitor-study-2026-10-01/competitors/analysis.md`（PVS12、DEN3/DEN4、AKS15、SEN3/SEN4、C2P11、KRA4/KRA5、MEM3）与 `peer-10.md`（EWS 注册）、`peer-1.md`（PVSelected）
- 14、15、17、19、21、22、28 号文件中没有与注册字段直接相关的证据。
