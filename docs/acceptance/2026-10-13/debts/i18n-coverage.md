# 德语目录覆盖清账（2026-10-14）

范围：`plugins/*/languages/*-de_DE_formal.po`。盘点命令是 `msgattrib --untranslated --no-obsolete`。空 `msgid` 的 catalog 头不算未译条目。多行 `msgstr` 只要有内容就不算未译。

实例：t110，`http://127.0.0.1:8975`。本线用 `just up t110` 把插件链接重锚到 `lane/debt-de-coverage` 的 worktree。没有改页面内容，没有编译 present/windpress。

## 盘点

| catalog | 改前未译 | 改后未译 | 豁免 | 缺口 |
|---|---:|---:|---:|---:|
| `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` | 80 | 54 | 54 | 0 |
| `plugins/linker-i18n/languages/linker-i18n-de_DE_formal.po` | 0 | 0 | 0 | 0 |
| `plugins/linker-tools/languages/linker-tools-de_DE_formal.po` | 0 | 0 | 0 | 0 |

改前 80 含一条德语 `msgid`：`Vocabulary/Labels.php:118` 把已有德语整句再包进 `__()`，用来做字面量替换。它的 `msgstr` 是空的，所以 `msgattrib` 把它算成未译。页面上客户看到的是 `msgid` 本身（已经是德语）。本线把同一句写进 `msgstr`，空翻译消失，行为不变。其余 79 条是真正的空翻译；其中 24 条已译，55 条里 54 条进豁免，1 条是上面这条德语 msgid。

`linker-i18n` 与 `linker-tools` 改前就是 0。没有重编它们的 `.mo`。

## 分类方法

逐条读 `.po` 的 `#:` 引用，再读对应 PHP。判断标准：

- 客户或员工能在页面、邮件列表、后台设置里读到的，翻译。
- 只出现在 JSON Schema、`wp_register_ability()` 的 label/description、ERP 的 JSON 错误、或 `show_ui => false` 的私有 post type 上的，豁免。

客户可见的规格标签走 `Materials::key_label()`（`plugins/linker-commerce/includes/Products/Materials.php:736`），经 `specs()`（同文件 `:367`）进购买面板 `key_stats()` 和目录卡 `card_facts()`。产品页大表的行标签来自产品自己的 `spec_groups`（`ProductView.php:371`），不是这条 map。所以新译的规格词不一定出现在当前目录卡的前四行，但 locale 一切换就会用上。

Abilities 的 label 和 description 进 `wp_register_ability()` 的参数（例：`CheckCompatibility.php:54-55`），`RestMeta.php:31` 把 schema 暴露在 REST。Genie 服务读的是返回的数据，不是这些句子。库存推送是 `POST linker/v1/stock`，调用方是持有 push key 的 ERP（`StockController.php:75`、`:102`）。`Stock pushes` 是私有 post type 的 label，`BatchLog.php:35-36` 写了 `public => false`、`show_ui => false`。

## 豁免

清单：`tools/checks/i18n-exempt.json`。54 条，全部在 linker-commerce。每条有一句理由和源码位置。分组：

- Abilities API 的 label、description、JSON Schema 属性说明：44 条（`includes/Abilities/`）。
- 工程 feed 的 schema 说明：1 条（`EngineeringFeedController.php:120`）。
- 库存推送的参数说明、JSON 错误、应答 schema、私有审计 post type：9 条（`includes/Stock/`）。

门会拒绝过期豁免：一条已经译了或从 catalog 里消失的豁免，退出码也是 1。

## 原文 → 德语

术语沿用已译条目：`Proformarechnung`、`Anfrage`、`Lösungskonfigurator`、`Lösungsentwurf`、`Batteriespannung`（`linker-i18n` 的属性标签）、`Max. Ladestrom` → `Max. Entladestrom`、`Nennspannung` → `Systemnennspannung`、`AC-Nennleistung` → `AC-Ausgang (Nennwert)`。Sie 体。没有英语夹杂。

| 原文 | 德语 | 面 |
|---|---|---|
| Home（breadcrumb） | Startseite | 目录面包屑，页面印成 STARTSEITE |
| About these specifications | Zu diesen Angaben | 产品页规格说明的 summary |
| Proforma invoice issued | Proformarechnung ausgestellt | Woo 邮件列表里员工看到的邮件名 |
| Numbers read PREFIX-YEAR-NNNN… | Nummern haben die Form PRÄFIX-JAHR-NNNN… | Woo 设置里员工看到的说明 |
| Nominal apparent power | Nennscheinleistung | 规格行 |
| Battery voltage | Batteriespannung | 规格行；与 linker-i18n 属性标签同一译法 |
| Max. discharge current | Max. Entladestrom | 规格行；购买面板在该键排进前四行时显示 |
| Cycle life | Zyklenlebensdauer | 规格行 |
| Transformer ratio | Übersetzungsverhältnis | 规格行 |
| Rated burden | Nennbürde | 规格行 |
| Devices supported | Unterstützte Geräte | 规格行 |
| AC output (nominal) | AC-Ausgang (Nennwert) | 规格行 |
| System voltage | Systemspannung | 规格行 |
| Role | Funktion | 规格行 |
| Ambient humidity | Umgebungsfeuchte | 规格行 |
| Applicable standards | Anwendbare Normen | 规格行 |
| Certification | Zertifizierung | 规格行 |
| Cable length | Kabellänge | 规格行 |
| AC surge protection | AC-Überspannungsschutz | 规格行 |
| Battery type | Batterietyp | 规格行 |
| System nominal voltage | Systemnennspannung | 规格行 |
| Backup apparent power | Notstrom-Scheinleistung | 规格行 |
| Backup output frequency | Notstrom-Ausgangsfrequenz | 规格行 |
| Nominal apparent power to grid | Nennscheinleistung zum Netz | 规格行 |

另有一条不是新译、是补齐：`Labels.php:118` 的德语 msgid，`msgstr` 写成同一句。

## 门

```
python3 tools/checks/i18n-coverage.py
just i18n-coverage
```

`just check` 现在包含 `i18n-coverage`（`justfile` 第 34 行）。每个 catalog 打一行：`untranslated`、`exempt`、`gap`。`gap` 不为 0，或豁免指向已经不存在的句子，退出码为 1。

改过的 catalog 用既有方式重编：

```
msgfmt --check-format -o /dev/null plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po
msgfmt -o plugins/linker-commerce/languages/linker-commerce-de_DE_formal.mo plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po
```

## t110 抽取

重锚后插件链接指向本 worktree。抽取面：

- `http://127.0.0.1:8975/de/produkte/`：面包屑链接文字是 `STARTSEITE`，HTML `lang=de-DE`。证据 `evidence/01-shop-de.png`、`evidence/05-startseite.png`、`evidence/shop-de.html`。
- `http://127.0.0.1:8975/de/produkt/chint-dtsu666/`：`<summary>Zu diesen Angaben</summary>`。证据 `evidence/03-pdp-dtsu.png`、`evidence/dtsu-de.html`。
- `http://127.0.0.1:8975/de/produkt/goodwe-gw112-6-bat-ac-g10/`：同一句 summary，购买面板有 `Nutzbare Energie`、`Max. Ladestrom`（这两条是已有译法，用来确认德语 catalog 在生效）。证据 `evidence/02-pdp-gw.png`、`evidence/04-about-specs.png`、`evidence/gw112-de.html`。
- 员工面：用户 `i18n-staff`（locale `de_DE_formal`，shop_manager）打开 Woo → 设置 → 电子邮件。页面含 `Proformarechnung ausgestellt`，不含英语原句。证据 `evidence/06-emails-admin.png`、`evidence/06-email-title-de.png`。

`switch_to_locale('de_DE_formal')` 后直接调用得到：`Startseite`、`Zu diesen Angaben`、`Proformarechnung ausgestellt`、`Zyklenlebensdauer`、`Max. Entladestrom`、`Systemnennspannung`、`Umgebungsfeuchte`、`Funktion`。对产品 1955（GoodWe GW112.6-BAT-AC-G10）`Materials::specs()` 打出 `cycles | Zyklenlebensdauer`、`discharge_a | Max. Entladestrom`、`system_nominal_voltage_v | Systemnennspannung`。

当前快照里，`ratio`、`rated_burden_va`、`ac_apparent_power`、`devices` 没有产品带这些键，所以对应译法没有页面可抽。`role`、`ambient_humidity`、`cable`、`certification` 有数据，但购买面板和目录卡的前四行用的是别的键，大表行标签又来自产品自带的德语 `spec_groups`。这些译法的页面证据是 locale 下的函数输出，不是某一张产品页的 `<dt>`。

测试用户：`i18n-de`（customer，`linker_approval_status=approved`，id 205）、`i18n-staff`（shop_manager，locale `de_DE_formal`，id 206）。一次性登录用 `just login t110 --user …`，用过即废。
