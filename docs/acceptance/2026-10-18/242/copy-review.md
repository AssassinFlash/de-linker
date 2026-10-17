# #242 · 文案评审：Genie 产品卡的价格行与问价时的说法

基准：linker-copywriting Hard Stops、AGENTS.md §3 用词、线上既有措辞与 `.po` 术语（先例 `docs/acceptance/2026-10-10/12/copy-review.md`）。EN 先定，DE 独立写（Sie 体）。

## 1. 卡上的价格行（客户可见，`GenieCard::priceLine`）

| 原因 | 初稿 EN | 评审意见 | 定稿 EN | 定稿 DE |
|---|---|---|---|---|
| 价格可见 | 产品页的价格行原样（`€1,680.00` / `1.680,00 €`） | 不加 "Net price:" 前缀：产品页本身也只印金额（`.pdp-price-net`），加了就和产品页不一致 | 同初稿 | 同初稿（德语格式由 LocaleFormat 生成） |
| login（访客） | "Log in for prices"（PriceDisplay 在购物车行的说法） | 卡的对照物是产品页，不是购物车；产品页同一位置写的是 "Net price after partner sign-in"，用它 | Net price after partner sign-in | Nettopreis nach Partner-Anmeldung |
| pending | Prices after approval | 产品页原句，保留 | Prices after approval | Preise nach Freigabe |
| restricted | Not available for your account | 产品页原句，保留 | Not available for your account | Für Ihr Konto nicht verfügbar |
| project | Quoted per project | 产品页原句；同时修正产品页：已批准账号在按项目报价的商品上原来读到 "Not available for your account"，与事实不符（账号并无问题） | Quoted per project | Angebot pro Projekt |
| unpriced | Price on request | 产品页（经 `woocommerce_empty_price_html`）原句，保留 | Price on request | Preis auf Anfrage |

德语逐字取自 `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` 的现行译文（已在线上），写入 `plugins/linker-tools/languages/linker-tools-de_DE_formal-linker-tools-genie.json`。没有新造的句子。

## 2. 问价时模型的说法（提示词，`prompts/{en,de}/system.md` 与每轮提醒）

不是固定文案，但决定客户读到的话，按同一基准评。

- **初稿 EN**："the product's card shows it, as the customer's account allows (`partner=True`: the net price, as on the product page; any other account reads on the card why there is none)…"
- **初稿 DE**："Die Produktkarte zeigt den Preis so, wie das Konto … es erlaubt (… jedes andere Konto liest auf der Karte, warum dort kein Preis steht) …"
- **实测**（g242，2026-10-18 第一轮 e2e，访客 DE 390）：模型照抄机制说明——"…ist kein freigegebenes Partnerkonto hinterlegt, liest man auf der Karte, warum dort kein Preis steht." 生硬，像系统说明；"liest man" 也不是对客户的 Sie 体。
- **评审意见**：提示词只说该对客户说什么，不讲机制；对非伙伴只说一次"已批准的合作伙伴账号看得到净价"，不猜金额。
- **定稿 EN**："show the product as a card, and the service puts the price line on it for the customer's account. When `partner=True`, say that the card shows the net price. Otherwise say once, plainly, that approved partner accounts see net prices; never guess an amount."
- **定稿 DE**（独立撰写）："Zeigen Sie das Produkt als Karte; die Preiszeile setzt der Dienst passend zum Konto … darauf. Bei `partner=True` sagen Sie, dass die Karte den Nettopreis zeigt. Sonst sagen Sie einmal und schlicht, dass freigegebene Partnerkonten Nettopreise sehen; nennen Sie nie einen geschätzten Betrag."
- **复测**（同一 e2e，截图本目录）：访客 DE 390 "Den Preis zeigt die Produktkarte – freigegebene Partnerkonten sehen dort Nettopreise."；已批准 EN 390 "Its card below shows the price; as an approved partner account, you see the net price there." 无禁用词、无金额出现在正文。
