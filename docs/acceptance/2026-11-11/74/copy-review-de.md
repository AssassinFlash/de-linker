# #74 每日摘要 · 运行健康块（DE）文案评审记录

规则：内部业务邮件的主题、标题、各块标题与空态句同过对抗评审
（`docs/specs/74-daily-digest.md`「邮件」一节；先例
`docs/acceptance/2026-10-11/74/copy-review.md`）。
基准：linker-copywriting Hard Stops、既有 .po 术语。

范围：本记录只覆盖 2026-11-11 新增的德语（`Operations health` 块此前没有
任何德语条目）。英文与中文定稿在 #1098 已随实现发布，本次未改动其中文字；
本次只把两条中文源串改为英文源串（中文译文不变，见 PR #1114）。

评审方式：按上述基准逐条对照，先写初稿再逐项判定，记录被否的备选与理由。
与先例一样，这是实现者按既定基准记录的一轮评审，不是独立第三方复核。

## 1. 块标题 `Operations health` → `Betriebsstatus`

- 初稿 `Betriebsstatus`。备选 `Betriebszustand`（更偏"系统状态机"）、
  `Systemzustand`（与前两个同样准确但对读者不解释为什么收到这封信）。
- 判定：这一行每天出现在团队邮件里，读者要知道"今天哪里不对"，而
  `Betriebsstatus` 是德语运营语境里"运行状况"的常用词，与既有标题
  `Authentifizierung interner E-Mails`（Internal mail authentication）同样
  是名词短语、同样不自造概念。**定稿**：`Betriebsstatus`。

## 2. 空态句 `All within bounds — %s.` → `Alles im Rahmen — %s.`

- 初稿 `Alles im Rahmen — %s.`。备选 `Alle Werte im Rahmen`（更长，且四个
  维度里有三个不是"值"而是计数与状态）、`Keine Auffälligkeiten`（过诺：
  探测失败时该维度一无所知，不能称"无异常"——这正是该块要防的错）。
- 判定：保留破折号插入语结构，与英文同形；`im Rahmen` 与既有
  `Freigabe`/`Obergrenze` 语境一致，不引入新词。**定稿**：同初稿。

## 3. 主题里的计数短语

- `%d inquiry awaiting follow-up` / `%d inquiries awaiting follow-up`
  → `%d Anfrage wartet auf Bearbeitung` / `%d Anfragen warten auf Bearbeitung`。
- `%d account awaiting approval` / `%d accounts awaiting approval`
  → `%d Konto wartet auf Freigabe` / `%d Konten warten auf Freigabe`。
- 判定：动词取单复数两式（德语必须，不能像中文那样一式通用）；名词沿用
  块标题既有译法 `Anfragen warten auf Ihre Bearbeitung` 与
  `Konten, die auf die Freigabe warten`，同一封信里不出现第二套说法。
  主语是询盘/账号而不是人，无作业派发。**定稿**：同上。
- 分隔符 `: %s` → 德语 `: %s`（半角冒号）；中文目录给 `：%s`。判据：德文
  正字法用半角冒号加空格，中文用全角。定稿即此。

## 4. 紧凑行的维度缩写

`queue %1$s (%2$s)` → `Warteschlange %1$s (%2$s)`；`nothing late` →
`nichts überfällig`；`mail %1$d/%2$d PHP, %3$d/%4$d SMTP` → `E-Mail …`；
`intake %1$d/%2$d unhandled, %3$d quarantined` →
`Eingang … unerledigt, %3$d in Quarantäne`；`publication %1$d/%2$d
engineering, %3$d knowledge` → `Veröffentlichung … technisch, %3$d Wissen`。

- 判定：这一行是"一切正常"时的唯一读数，读者要能横向比较四个维度，故
  每个维度一个德语名词 + 数字，不写完整句子。`quarantined` 译
  `in Quarantäne`（德语的固定搭配），`unhandled` 译 `unerledigt`（与
  `unerledigte Anfragen` 一致），`knowledge` 译 `Wissen`（短、可比较）。
  **定稿**：同上。

## 5. 告警句与明细句（技术数据句，不属公开面）

这些行只在越界时出现，内容是阈值与处置动作，不含承诺、不含营销措辞，
按"事实准确、术语一致"评审而非广告效果：

- `%d queued delivery action is more than a day overdue.` →
  `%d Zustellauftrag ist mehr als einen Tag überfällig.`（复数
  `%d Zustellaufträge sind …`）。`Zustellauftrag` 沿用 `Zustellwarteschlange`
  的词根，不用 `Versand`——`Versand*` 在 `tools/checks/commerce-terms.txt`
  里是禁用词（店面语汇），本块讲的是邮件投递队列。
- `Ordinary mail stops at %1$d; the last %2$d attempts are held for …` →
  `Die normale Zustellung endet bei %1$d; die letzten %2$d Versuche bleiben
  für Passwort-Zurücksetzungen, Freigaben und Team-Warnungen reserviert. …`
  初稿曾写 `Normaler Versand`，被 `commerce-terms` 判为禁用词，改
  `Zustellung`。`attempts` 译 `Versuche`，与既有
  `Der letzte SMTP-Versuch ist fehlgeschlagen.` 同词。
- `Engineering feed prepared %1$d of %2$d products.` →
  `Der technische Datenbestand hat %1$d von %2$d Produkten vorbereitet.`
  初稿用英借词 `Engineering-Feed`；目录里既有的说法是
  `Die technischen Daten aller veröffentlichten Produkte`，改用
  `technischer Datenbestand`，同一封信里不出现第二种叫法。
- `The planner builds from this feed.` → `Der Lösungskonfigurator baut auf
  diesem Datenbestand auf.`：读者是团队，`Lösungskonfigurator` 是目录里对
  planner 的既有称呼（`Der Lösungskonfigurator`），`planner` 是内部代号，
  不写给读者。
- 其余 `could not be read` 系列统一 `konnte nicht gelesen werden`；明细句
  `Das ist keine Nullmessung: Die Messung selbst ist fehlgeschlagen, daher ist
  zu dieser Dimension heute nichts bekannt.` 与英文同义，明确"这不是零"，
  防止读者把测量失败读成健康。

## 结论

以上 35 条德语（含 5 个复数对：两组计数短语、逾期条数、小时与天三档）与 4 条中文新增定稿即
`plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` 与
`linker-commerce-zh_CN.po` 里的字面量；由
`tests/php/Unit/Digest/DigestCatalogTest.php` 从源码抽取 msgid、对编译产物
`.mo` 校验两种语言，改 `.po` 未重编译即在 CI 之外也会失败。
