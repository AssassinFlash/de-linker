# 拆分登录/注册 · 文案对抗评审记录

依据：业主 2026-10-16 指令（拆成 sign-in 页 + 注册页，保留互相跳转入口）。规则同
`docs/acceptance/2026-10-15/184/copy-review.md`（AGENTS.md §2/§3：客户可见文案一律走
对抗评审，EN 先行、DE 独立撰写、Sie 体；基准 = linker-copywriting Hard Stops + 线上既有
措辞与 .po 术语）。

## 结论：本轮无新客户可见文案

拆分只改变**页面的组织**（两卡分置两个 URL），不改变任何一句话。登录页与注册页上的
每一个可见字都是 #184 已评审固定的条目，逐条出处如下（`msgstr` 见
`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po`）：

| 出现处 | 字符串 | #184 评审位置 |
| :--- | :--- | :--- |
| 登录卡头 | `Sign in` / `Anmelden`；`Your inquiries, documents and prices in one place.` / `Ihre Anfragen, Dokumente und Preise an einem Ort.` | §2 卡文案（沿用原型 login.html，既有 .po 条目） |
| 登录卡字段 | `Username or email address`、`Password`、`Remember me`、`Log in` | Woo 语言包（`woocommerce` 域，未改） |
| 登录卡链接行 | `Lost your password?`（Woo 域）；`No partner account yet?` + `Create your business account` / `Noch kein Partner-Konto?` + `Erstellen Sie Ihr Firmenkonto` | §2 既有点；"partner account" = 站上既有说法（评审 §1） |
| 登录单元品牌面板 | `Your partner account` / `Ihr Partner-Konto`；`The workspace for installers, EPCs and distributors.` / `Der Arbeitsbereich für Installationsbetriebe, EPC-Unternehmen und Händler.`；三条要点 | §1 与 §1b（面板文案定稿，逐字未动） |
| 注册卡头 | `Create your business account` / `Erstellen Sie Ihr Firmenkonto`；`We review every new account before activation.` / `Wir prüfen jedes neue Konto vor der Freischaltung.` | §2/§3 |
| 注册三步标题 | `Company`、`Contact and address`、`Sign-in details` / `Unternehmen`、`Kontakt und Adresse`、`Zugangsdaten` | §3 |
| 注册字段标签 | `Company name`、`Business type`、`VAT ID`、`Please choose`、`Installationsbetrieb` 等 | §3 与 .po 既有注册术语 |
| 注册法务行 | `Terms of Sale`、`Privacy` / `Verkaufsbedingungen`、`Datenschutz` | §3（链接按页面存在与否出） |
| 注册提交 | `Register` / `Registrieren` | Woo 域（未改） |
| 注册卡底 | `Already have a partner account?` + `Sign in` / `Sie haben bereits ein Partner-Konto?` + `Anmelden` | §2 既有点（原为锚点跳转，现为跨页跳转，文字未动） |
| 注册单元品牌面板 | `Create your partner account` / `Legen Sie Ihr Partnerkonto an`；`For installers, EPCs and distributors: …`；三条要点 | §1b/§V1（面板文案定稿，逐字未动） |

## 变更之处也不产生新文案

- 空草稿页 guest 框的 `No account yet? Register` / `Noch kein Konto? Registrieren`：文字
  与译文逐字沿用既有 `.po` 条目（德语 `Anmelden und Proforma anfordern` / `Noch kein
  Konto? Registrieren`），只把目标从 `/my-account/` 改为端点 URL。
- 登录卡与注册卡的互跳句子原为页内锚点（`#linker-register` / `#linker-signin`），本票
  改为真实 URL，句子本身逐字不变。
- 未新增 `__()` 调用：`git grep` 本票 diff 的 `.pot` 只出现引用行（`#:`）变化与两条
  历史悬空条目（写了字面邮箱地址的旧句，被 `%s` 占位形态取代后的残留）的清除，无新
  `msgid`。见 `docs/specs/split-login-register.md` §6。

## 预检

- 德语 Sie 体：未新增句子，既有条目已核。
- 禁句 / Hard Stops / Actor：未新增句子。
- 事实口径：未新增承诺。
- 术语：`Partner-Konto`（连写带连字符）、`Proforma-Anfrage`、`Freischaltung`、`Niederlassung`
  等沿用 #184 定稿，本票未触碰。
