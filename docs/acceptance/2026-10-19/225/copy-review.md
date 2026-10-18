# #225 注册表单文案对抗评审

日期：2026-10-19。范围：两步注册卡新增或改写的全部客户可见文案，以及注册防机器人/限流错误与验证提示。邮件主题与正文未新增文案（新客户通知沿用既有主题与正文结构，字段标签来自 `.po`）。

依据：AGENTS.md §2（业主 2026-10-17 两步裁定）、§3（用词、Sie 体、禁止 AI 句式）、§5（EN 先行、DE 独立撰写、对抗评审）；线上现有措辞与 `linker-commerce-de_DE_formal.po` 既有术语；原型 `docs/prototypes/2026-10-17-registration/`（只作参考）。

## 1. EN 定稿（先行）

| 位置 | 定稿 | 说明 |
|---|---|---|
| Step 1 进度 | `Step 1 of 2 · Your company` | 业主裁定点名的两段进度条文案 |
| Step 2 进度 | `Step 2 of 2 · You and your sign-in` | 与第二步标题一致 |
| 第一步标题 | `Your company` | 章节名，不编号 |
| 第二步标题 | `You and your sign-in` | “sign-in”与站内 “Sign in” 导航一致；不用 “login” |
| 网站/VAT 上方 | `We use one of these to verify your company. Enter at least one.` | 说明用途与“至少一项” |
| 网站标签 | `Company website` | 既有 `.po` 术语 |
| VAT 标签 | `VAT ID` | 既有术语 |
| VAT 说明 | `We check EU VAT IDs in the European Commission's VIES system.` | 保留在 VIES 说明内，不再承诺“无 VAT 也可注册”（与“至少一项”冲突） |
| 国家标签 | `Country / Region` | 线上既有 Woo 标签 |
| 国家分组 | `Europe` / `Other countries` | Woo 的 Europe 大洲列表；德国置顶 |
| 邮箱提示 | `You sign in with it. We send the approval to this address.` | 明确“批准发到这个地址” |
| 继续 | `Continue` | 原型用词 |
| 返回 | `Back` | 原型用词 |
| 网站格式错误 | `Enter a web address such as example.com.` | 给出可操作示例 |
| 网站/VAT 都空 | `Enter your company website or VAT ID, so we can verify your company.` | 与上方说明呼应 |
| 第一步客户端必填 | `Please complete the required fields.` | 只在 Continue 的本步校验里出现 |
| 机器人/时钟被拒 | `We could not process this registration. Please check your entries and try again.` | 不提示蜜罐或时间阈值 |
| 连接限流 | `We received several registrations from this connection. Please try again later or write to sales@de-linker.com.` | 与询盘限流句同一结构；客户可见邮箱用 sales@de-linker.com |

## 2. DE 定稿（独立撰写，Sie 体）

| 位置 | 定稿 |
|---|---|
| Step 1 进度 | `Schritt 1 von 2 · Ihr Unternehmen` |
| Step 2 进度 | `Schritt 2 von 2 · Sie und Ihre Anmeldung` |
| 第一步标题 | `Ihr Unternehmen` |
| 第二步标题 | `Sie und Ihre Anmeldung` |
| 网站/VAT 上方 | `Mit einem dieser Werte prüfen wir Ihr Unternehmen. Bitte tragen Sie mindestens einen ein.` |
| 网站标签 | `Unternehmenswebsite`（既有） |
| VAT 标签 | `USt-IdNr.`（既有） |
| VAT 说明 | `EU-USt-IdNr. prüfen wir im VIES-System der Europäischen Kommission.` |
| 国家标签 | `Land / Region` |
| 国家分组 | `Europa` / `Weitere Länder` |
| 邮箱提示 | `Damit melden Sie sich an. An diese Adresse senden wir auch die Freigabe.` |
| 继续 | `Weiter` |
| 返回 | `Zurück` |
| 网站格式错误 | `Geben Sie eine Webadresse wie example.com ein.` |
| 网站/VAT 都空 | `Tragen Sie die Unternehmenswebsite oder die USt-IdNr. ein, damit wir Ihr Unternehmen prüfen können.` |
| 第一步客户端必填 | `Bitte füllen Sie die Pflichtfelder aus.` |
| 机器人/时钟被拒 | `Wir konnten Ihre Registrierung nicht verarbeiten. Bitte prüfen Sie Ihre Angaben und versuchen Sie es erneut.` |
| 连接限流 | `Von dieser Verbindung sind mehrere Registrierungen eingegangen. Bitte versuchen Sie es später erneut oder schreiben Sie an sales@de-linker.com.` |

## 3. 对抗评审意见与处理

评审一（英文，清晰度/承诺/术语）：

1. **“here”指代不明**：初稿 `You sign in with it, and we send the approval here.` 的 “here”可被读成当前页面。定为 `You sign in with it. We send the approval to this address.`，一句一件事，去掉 and 连接的双句。
2. **“Fill in”与错误句“Enter”不一致**：说明句初稿用 `Fill in at least one.`，错误句用 `Enter your company website…`。统一为 `Enter`/`Enter`，德语统一为 `tragen … ein`。
3. **VAT 旧说明自相矛盾**：旧文案 `You can register without one.` 与“网站或 VAT 至少一项”冲突；删掉该承诺，只保留 VIES 说明。
4. **“connection”是技术词**：保留。询盘限流已对客户用同一词（`Inquiry\Handler`），改词会让同一个限制在站内出现两种说法；这是线上既有措辞优先。
5. **“Europe”分组实际是 Woo 的 Europe 大洲**：保留分组名与数据一致；瑞士、英国等在欧洲组，非欧盟成员国也在内，不是“欧盟”分组，因此不能写成 “European Union”。
6. **两步标题与进度句重复**：保留。进度句报告位置，标题命名章节；两者服务不同阅读路径（屏幕阅读器与视觉）。
7. **“sign-in”而非“login”**：站内客户可见入口一律 “Sign in”（页头、按钮）；德语对应 `Anmeldung`。不引入 “login” 作为客户用词。
8. **双重错误提示**：客户端通用提示与“网站/VAT 至少一项”同时出现。两者信息不同（前者说还有必填项，后者说这一组至少要一项），且客户端提示在服务器返回错误的页面上不显示（`hidden`），不会与 WooCommerce 通知叠加。
9. **限流句中的邮箱**：按 AGENTS.md §2，客户可见地址是 sales@de-linker.com；内部收件人不出现在客户文案里。

评审二（德语，独立撰写/Sie 体/禁用词）：

1. 全文用 Sie；无 du、无 “nicht … sondern”、无三连排比。
2. `Firmenkonto`、`Firmenname`、`Unternehmensart`、`Unternehmenswebsite`、`USt-IdNr.`、`Anmeldung` 均沿用既有 `.po`，不新造同义词。
3. `Weitere Länder` 比 `Andere Länder` 更自然，且不暗示“剩下的不重要”。
4. `Mit einem dieser Werte prüfen wir Ihr Unternehmen.` 把“我们用它核实”放在句首，避免英语语序；`Bitte tragen Sie mindestens einen ein.` 明确“一项”。
5. 错误句 `Wir konnten Ihre Registrierung nicht verarbeiten.` 不透露蜜罐/时间/限流细节；限流句 `Von dieser Verbindung sind mehrere Registrierungen eingegangen.` 与既有询盘限流句同构。
6. `Damit melden Sie sich an. An diese Adresse senden wir auch die Freigabe.` 两句各一件事；`auch` 承接“登录与批准都发这里”。
7. 禁用词检查：无 `Artikel`、`Katalog`、`Warenkorb`、`Basket`、`Cart`、`catalogue`、`article`。

## 4. 结论

定稿通过。EN/DE 均由上述文本生成 `.po`，`just i18n-coverage` 为 clean。德语不是英语的逐句翻译；两版在“至少一项”和“批准发到该地址”上的信息相同。文案的视觉呈现见 `screens/`（EN/DE × 1440/390，两步与错误态）。
