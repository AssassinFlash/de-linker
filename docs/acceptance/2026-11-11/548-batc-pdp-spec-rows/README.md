# BAT-C 产品页规格行上线（认证 + 额定电流/功率）

日期：2026-11-11。分支 `batc-pdp-rows`（worktree `/tmp/batc-pdp`，自 `origin/main` `0fa428d0a`）。
上级记录：`docs/acceptance/2026-11-11/548-batc-manual-publication.md`（PR #1117）§3.2 的解禁执行。
文案评审：`05-copy-review.md`（同目录）。

未碰 `apps/planner`、引擎、能量链；未改渲染层；未新增产品；未改营销正文。

## 0. 结论表

| # | 项 | 结果 |
| --- | --- | --- |
| 1 | 实现路径 | **写 legacy 表**（`_tv_legacy_acf_json` + `_linker_de_acf_json`），不改渲染层。理由见 §1 |
| 2 | 写入范围 | 1954 / 1955，各 2 份表；每份 +2 行 +1 组（2 行） |
| 3 | 认证行 | **两行**：`Safety` / `EMC`（手册 p82 认证块本就两行，registry 原只录一行，本批补齐） |
| 4 | 额定值行 | 电流 `100 / 100 A`（充/放对）；功率 `30.7 kW` / `56.3 kW`（**每款单值**，不是充放对） |
| 5 | 生产读回 | 四页（EN/DE × 两产品）全部渲染，值与 registry 逐字一致 |
| 6 | 缓存 | 1955 两页初次未更新（LiteSpeed hit）；已按 URL 精确失效，现 `miss` 且内容正确 |
| 7 | 回滚 | 见 §6 |

## 1. 实现路径决策

**结论：把三行数据补进 legacy 表，两份语言版本各写一次。**

理由：

1. **渲染层只有两个来源，且语言行为不同。** `ProductView::spec_groups()` 先读 `linker_specs`，无则
   `Materials::acf()`。`linker_specs` 是**单份** meta，没有语言覆盖；而德语表是
   `_linker_de_acf_json` 覆盖（`Materials::acf()` 在 `is_de()` 时读它）。写 `linker_specs` 会让
   DE 页读到英文行——一个改动同时破坏德语。legacy 这一对是站点既有的双语承载，写它才是最小且正确的落点。
2. **改渲染层读 registry 波及 24 个产品、38 行带 qualifier 的事实**（#1117 §3.2 已记录该估算）。
   `Materials::specs()` 的消费者只要 4 行（`key_stats`/`card_facts`），把 `specs()` 接进 PDP 表会同时
   改变所有产品的表格形状（行数、标签体系、qualifier 拼接），不是本批能验证的范围。
3. **数据同源。** 页面值逐字取自 registry，不是另抄一份数字；registry 仍是事实源，页面是它的客户面投影
   （见 §2 对照表）。这条保证两套来源今后不会出现两个不同值。

## 2. 页面行 ↔ registry 对照

| 页面行（EN / DE） | registry key | registry 值 | 手册页 |
| --- | --- | --- | --- |
| `Safety` / `Sicherheit` | `certification` | `IEC62619 / … / UN38.3` | 物理 p82（印刷 81） |
| `EMC` / `EMV` | `emc`（本批新增） | `IEC/EN 61000-6-1/2/3/4` | 物理 p82 |
| `Rated charge / discharge current` / `Nenn-Lade- / Entladestrom` | `rated_charge_discharge_current_a` | `100 / 100` A | 物理 p81（印刷 80） |
| `Rated charge / discharge power` / `Nenn-Lade- / Entladeleistung` | `rated_charge_discharge_power_kw` | `30.7` / `56.3` kW | 物理 p81 |

**页面 note 与 registry 的 `qualifier` 语义对应**（page note 去掉内部页码引用）：

| 语义 | registry qualifier | 页面 note |
| --- | --- | --- |
| 仅澳洲 | `GoodWe rates these values for Australia only (note 2, p. 83)` | `GoodWe rates these for Australia only;` |
| 随温度/SOC 降额 | `actual charge/discharge current and power derate with cell temperature and state of charge` | 同 |
| 最大值分列 | `The maximum ratings are stated separately.` | `The maximum ratings are listed above in this table.`（指向表内实际位置） |
| 清单不全 | `not all certifications and standards are listed … official website` | `GoodWe states that not all certifications and standards are listed; the full set is on its website.` |

页码留在 registry 与本文档，不进客户页面。

## 3. 一处自查纠正（额定功率不是充放对）

第一次写入时我把额定功率写成 `30.7 / 56.3 kW`（把两款产品的值当成充/放对，两款同值）。读回时发现
四页都显示 `30.7 / 56.3 kW`，与手册列不符。

核对手册 p80（物理）该行四个型号列各印一个数：`30.7 | 46.0 | 51.2 | 56.3`。即**每款一个额定功率**。
用额定电流乘额定电压复核：307.2 V × 100 A = 30.72 kW（手册 30.7）、563.2 V × 100 A = 56.32 kW
（手册 56.3），逐位吻合（手册按一位小数截断）。

registry 侧本来就是单值（`30.7` / `56.3`），是我在页面行上写错。已改为按产品取值的
`per_product` 映射并重写；当前生产四份表全部为正确单值。**这类把两个不同产品的值误读成一行内
两个值（充/放）的错误，只有逐产品对照才抓得到**——批量写入 + 只读一页会漏掉 1955。

## 4. 生产写入

### 4.1 备份（前像）

| 层 | 内容 | 位置 |
| --- | --- | --- |
| 全库 | `mysqldump --single-transaction --quick --skip-dump-date --order-by-primary`，62 张表，8.6 MB gz | `/tmp/batc-pdp-backup/batc-pdp-pre-2026-11-11.sql.gz` |
| 目标 meta | 1954/1955 × （`_tv_legacy_acf_json`、`_linker_de_acf_json`、`_linker_de_source_acf_json`）原文 | `/tmp/batc-pdp-backup/before-meta.json` |

取库方式与 `tools/pull/src/linker_pull/live.py::dump_script()` 同一脚本形状（主机 `exec()` 被禁，
`wp db export` 不可用；密码只进 mysqldump 环境）。

前像 sha256（前 16 位）：

```
1954 _tv_legacy_acf_json        ce14501c9a2cb9b3   7207 B
1954 _linker_de_acf_json        7507bd35b394baaa   7503 B
1954 _linker_de_source_acf_json ce14501c9a2cb9b3   7207 B  (= EN 表快照)
1955 _tv_legacy_acf_json        278ed90c326f5b66   6986 B
1955 _linker_de_acf_json        88574645dbbdf6dc   7028 B
1955 _linker_de_source_acf_json 278ed90c326f5b66   6986 B  (= EN 表快照)
```

### 4.2 后像

```
1954 _tv_legacy_acf_json  groups=[Battery and electrical, Cabinet and installation, Certification]           rows=[9,5,2]  8036 B  789edd93581f9e5c
1954 _linker_de_acf_json  groups=[Batterie und elektrische Daten, Schrank und Aufstellung, Zertifizierung]     rows=[9,5,2]  8685 B  172def7df3aa77fd
1955 _tv_legacy_acf_json  groups=[Battery and electrical, Cabinet and installation, Certification]           rows=[9,5,2]  7804 B  196fe9634cbe22e2
1955 _linker_de_acf_json  groups=[Batterie und elektrische Daten, Schrank und Aufstellung, Zertifizierung]     rows=[9,5,2]  8209 B  7c2724182959aedf
```

（字节数与 sha256 为最终态，含 §5 记录的德文正文措辞修正。）

原 12 行（7+5）不变，新增 2 行落在 `Battery and electrical` 末（紧跟 `Max. …` 两行），
新增组 `Certification` / `Zertifizierung` 2 行。

`_linker_de_source_acf_json` **未改**：它是德语译文所依据的快照，而 `spec_groups` 不在
linker-i18n 的翻译字段里（`Translation\Fields::of_post()` 只处理 title/excerpt/content + 可翻译 meta），
所以它不代表德语表的当前状态。

### 4.3 写入工具与幂等

`tools/migrate/548-batc-pdp-spec-rows.php`（`wp eval-file`）。默认只报告；`BATC_PDP_APPLY=1` 才写。
按 label 比对：相同→不动，不同→原位替换，不存在→按 `after` 锚点插入或追加到组末。
重复执行读回 `already as reviewed`（已实测两轮）。

## 5. 读回（生产）

| 层 | 方法 | 结果 |
| --- | --- | --- |
| meta | WP-CLI 读四份表 | 见 §4.2，值与 registry 逐字一致 |
| EN 1954 `/product/goodwe-gw61-4-bat-ac-g10/` | curl 全文 | 出现 `Rated charge / discharge current / 100 / 100 A`、`Rated charge / discharge power / 30.7 kW`、`Safety`、`EMC / IEC/EN 61000-6-1/2/3/4` |
| EN 1955 `/product/goodwe-gw112-6-bat-ac-g10/` | curl 全文 | 同上，功率 `56.3 kW` |
| DE 1954 `/de/produkt/goodwe-gw61-4-bat-ac-g10/` | curl 全文 | `Nenn-Lade- / Entladestrom / 100 / 100 A`、`Nenn-Lade- / Entladeleistung / 30,7 kW`、`Sicherheit`、`EMV` |
| DE 1955 `/de/produkt/goodwe-gw112-6-bat-ac-g10/` | curl 全文 | 同上，功率 `56,3 kW` |
| 逐字断言 | 脚本比对页面文本 vs registry 值 | 4 页 × 4 值 + 3 项限定语义，全 OK |

**第二次纠正（德文正文斜杠空格）。** 首版德文 note 沿用表格标签写法 `Lade- / Entladestrom`（斜杠两侧
空格）。标签这样写是对的（同表 `Max. Lade- / Entladestrom` 同形），但连续正文里德语惯例是
`Lade-/Entladestrom`。已把 note 正文改为不带空格（与 registry 德语 qualifier 同形），标签保留原样，
重写并读回两页德文。

**缓存。** 首次写入后 1954 两页即时更新，1955 两页仍是旧内容（响应头 `x-litespeed-cache: hit`，
字节数与写入前完全相同）。按 URL 失效（`do_action('litespeed_purge_url', …)`，LiteSpeed 插件注册的
动作）后，四页均为 `miss` 并渲染新行。

期间 `LiteSpeed\Purge::purge_all()` 与 `purge_url()` 直接调用在 `wp eval` 下触发站点 critical error
（未落盘日志可读），改用插件自己的动作钩子后正常——**记录在此，避免下次再踩**。

## 6. 回滚

任一层失败都可独立回滚：

**A. 精确回滚（推荐）。** 用备份里的原文覆盖四份 meta：

```
wp eval-file tools/migrate/548-batc-pdp-spec-rows.php   # 不带 BATC_PDP_APPLY，确认现状
# 用 before-meta.json 里 1954/1955 的 _tv_legacy_acf_json、_linker_de_acf_json 原文回写
wp post meta update 1954 _tv_legacy_acf_json  '<原文>'
wp post meta update 1954 _linker_de_acf_json  '<原文>'
wp post meta update 1955 _tv_legacy_acf_json  '<原文>'
wp post meta update 1955 _linker_de_acf_json  '<原文>'
do_action('litespeed_purge_url', …)  # 四条 URL
```

**B. 全库回滚。** `gzip -dc batc-pdp-pre-2026-11-11.sql.gz | mysql …`（8.6 MB，含写入前全部 62 张表）。
只在 A 不足以恢复时使用——它会同时回退写入之后其他人的改动。

回滚后必须读回：四页不再出现 `Certification`/`Zertifizierung`、`Rated charge`/`Nenn-Lade` 字符串，
且两表回到 12 行 2 组。

## 7. 改动清单

| 文件 | 改动 |
| --- | --- |
| `plugins/linker-commerce/data/material-registry.json` | 两款 BAT-C 各新增 `emc` 事实（34 → 35 项），p82 |
| `plugins/linker-commerce/includes/Products/Materials.php` | 标签表新增 `emc` → `EMC` |
| `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` / `.mo` | `msgid "EMC"` → `msgstr "EMV"` |
| `plugins/linker-commerce/languages/linker-commerce.pot` | 同上（模板） |
| `plugins/linker-commerce/tests/php/Unit/Products/MaterialsQualifierTest.php` | +1 测试（EMC 独立行）、已发布数据断言补 EMC 页与值 |
| `tools/migrate/548-batc-pdp-spec-rows.php` | 新增：双语表写入/读回/幂等（phpcs 全包规则下的前缀/对齐/输出转义均按仓库既有 `7-facts.php` 写法处理） |
| `docs/acceptance/2026-11-11/548-batc-pdp-spec-rows/` | 本记录 + 文案评审 |

## 8. registry 与 legacy 的一致性（#1117 白名单核对）

`Materials::QUALIFIED_ROWS` 仍为 `temp` + 三行（`rated_charge_discharge_current_a`、
`rated_charge_discharge_power_kw`、`certification`）。`emc` **不入**该白名单：手册对 EMC 行没有
附加条件（限定只在 Note 5 说「清单不全」，那句已挂在 `certification` 行），入白名单会拼出一句空限定。
`MaterialsQualifierTest::test_the_emc_row_is_its_own_labelled_row` 断言它在页面上是未加括号的纯值。

不冲突确认：

- legacy 表原有的 `Max. charge / discharge current`（180 / 220 A）与 `Max. charge / discharge power`
  是**最大值**，新增两行是**额定值**，label 分别以 `Max.` / `Rated` 起头，不重名、不重复。
- 认证行原先在 legacy 表**完全不存在**（`certifications` 字段是空数组 `[]`），因此是纯新增，不是改值。
- 两套来源同值：#1117 的 registry 值与本批页面值逐字一致（§5 断言）。

## 9. 门禁

```
phpunit（worktree 全量）        2316 tests, 8942 assertions, 543 skipped → OK
phpunit（Materials 相关）       MaterialsQualifierTest 5 tests / 37 assertions → OK
                                MaterialsQualifier+Voltage+Comparison 23 tests / 98 assertions → OK
phpcs                           clean（**全包 `phpcs -q`**，含 tools/migrate 的新脚本）
phpstan (level 8)               No errors（含新迁移脚本）
commerce-terms                  hits=28 baselined=28 findings=0 → clean
german-copy                     clean
i18n-validity                   9 catalogs clean
i18n-coverage                   gap=0（四个 catalog 全部 clean）
```

### 9.1 CI

PR #1124。run `43043258088`（第一次）与 `43045878334`（修正 phpcs 后的全量）：

- **通过**：`php-lane (plugins/linker-commerce)`（3m1s，覆盖本批全部 PHP 改动与测试）、
  `build (commerce)`、`build (tools)`、`engine`、`genie`、`js-lane (commerce/e2e)`、
  `php-lane (mu-plugins / linker-i18n / linker-tools / tools/local)`、`planner`、
  `python-lane (harnesses / tools/pull / tools/cutover)`、`secrets`、`plan`。
  第二次 run 的 `php:commerce` 由 CI 自己的复用证明指向第一次 run 的 green job（plan 日志可见
  `reuse run 43043258088 attempt 2 job 130609353290; same inputs …`），即本批 PHP 侧在两次 run 中都为绿。
- **未通过**：`content`、`python-lane (tools/local)`、`python-lane (tools/migrate)` 与若干 `mu-smoke`。
  逐个 job 读原始日志，失败点全部是同一条：
  `sudo apt-get update && sudo apt-get install -y gettext` →
  `Temporary failure resolving 'azure.archive.ubuntu.com'` → `E: Failed to fetch … gettext … exit code 100`。
  DNS 失败计数：`python-lane (tools/local)` 10 次、`(migrate)` 10 次、`mu-smoke` 各 16 次。
  **这些不是代码失败**：`tools/local` 本批一个文件都没动；宿主 runner 当晚在 `azure.archive.ubuntu.com`
  上间歇性 DNS 故障（同一 run 内不同 job、不同时间点都在同一镜像解析失败）。`js-lane (tools)` 撞的是
  同一镜像上的 Playwright 字体包（`fonts-ipafont-gothic`、`fonts-freefont-ttf` 等），`content` 撞的是
  `gettext`——三处都是 apt 取包阶段，与仓库内容无关。
- 汇总门 `check` 对已跑完的模块给出的判定是 `php: success / build: success / planner: success /
  engine: success / genie: success`，只有被 apt 打断的 `js / python / content / native` 记为 failure。
  **PHP 侧（本批改动的唯一代码面）在汇总门里也是 success。**
- 该 run 已 `--failed` 重跑（attempt 2）；GitHub API 同期也在超时（`TLS handshake timeout`），属同一网络事件。

最终 commit `68e5b921d` 的 run `43049848137`（21:36–23:5x）：

```
success 16   php-lane (mu-plugins / linker-i18n / linker-tools / tools/local)
             build (commerce) / build (tools) / js-lane (commerce) / js-lane (e2e)
             planner / engine / genie / secrets / plan
             python-lane (harnesses / tools/pull / tools/cutover)
             php:commerce → CI 复用证明指向 run 43048832103 的 green job 130620468568
                           （plan 日志：`same inputs e4c0d7df3fb8…`；该链路上唯一变化是
                            一行验收文档，故输入哈希与上一轮 PHP 实测通过的那轮相同）
failure 11   全部为 apt 取包阶段 DNS 故障（逐个 job 读原始日志确认）：
             content → gettext；js-lane (tools) → Playwright 字体包；
             python-lane (tools/local) / (tools/migrate) → gettext；
             mu-smoke (admin/core/inquiry/inventory/mail/runtime) → 各 16 次 DNS 失败；
             check → 汇总门，因上述 lane 记 failure 而整体失败
             （该门对已跑完模块的判定：php: success / build: success / planner: success /
               engine: success / genie: success）
skipped  3
```

`php-lane (plugins/linker-commerce)` 在 `e4a415702` 上**实际执行并通过**（2m16s，run 43048832103
job 130620468568），本批代码面因此不算未验证。`content` 等 lane 的失败点在安装依赖，不在
`Validate module` 之后。

首次 CI 确实抓到本批一个真问题（已在 §7 修正并重跑）：`ci-php-package` 跑的是**全包 phpcs**，
新迁移脚本有 5 个 error（全局函数前缀 ×2、注释参数对齐 ×2、`echo $report` 未转义）。本地只对
两个改动文件跑 phpcs，漏了它。

## 10. cycle_life DoD 条件冲突 —— 已按既定裁定解决（2026-11-12）

**`cycle_life` 的 DoD 条件三处厂商原文冲突**（页面表无此行，registry 值未改）：

- registry（据数据表 p2）：`6000 (25 ± 2 °C, 0.5C, 90% DoD, 70% EOL)`
- 手册物理 p81：`≥6000 times until 70% SOH under 25±2°C, 0.5C and 100% DOD`
- 手册 Note 3（p83）：`For Australian DOD is 98%`

初版记录把 AGENTS 的"产品事实冲突时以我们托管的**数据手册**为准"误读为"手册优先"并挂起待业主裁定。
2026-11-12 复核：裁定原文的数据手册即 datasheet（数据表），数据表优先于手册正文。据此
**数据表 p2 的 `90% DoD` 成立，registry 现值正确不变**；手册 p81 的 100% 与 Note 3 的 98%
（澳洲区域注释，与 EU 商店无关）均为手册层差异，不改变 registry。无需业主或原厂口径，关闭。

## 11. 资源

- 新建：worktree `/tmp/batc-pdp`（含 vendor 约 132 MB，可重建）、`/tmp/batc-pdp-backup`
  （全库备份 8.6 MB + 前像 JSON）、`/tmp/batc-manual.pdf` 与 `/tmp/batc-de.pdf`（原件核对用）、
  若干 `/tmp/*.html` 读回快照。
- 复用：无新建实例、无新建浏览器窗口、未起本地站点（文档与数据写入，按 §0.1 不启动站点）。
- 邮件：未发任何邮件。Apify：未使用。
- 生产：写入 4 份 postmeta + 4 次按 URL 缓存失效。
