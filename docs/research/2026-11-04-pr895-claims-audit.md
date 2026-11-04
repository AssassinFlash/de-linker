# PR #895 四条缩圈声明的逐条复核（#903）

日期：2026-11-04
范围：只读。核对 PR #895 落在 `docs/acceptance/2026-11-04/548/` 的四条「做不了／不归我／等裁定」声明，
逐条对照仓库全史、生产 engineering-feed、生产托管原件字节、VPS 知识索引与 PR 流程记录。
未修改任何生产数据、未部署、未写生产。分支 `research/pr895-claims-audit`，不开发 PR。

复核对象：
`docs/acceptance/2026-11-04/548/` 的 `README.md`、`cable-blocker.md`、`terminal-map-coverage.md`、`conflict-rulings.md`
（PR #895，merge `87f6485bf`，2026-11-04 04:16:29 +0800）。

## 0. 结论速览

| # | 声明 | 判定 | 性质 |
| --- | --- | --- | --- |
| 1a | `cables.json`「从来没有产出过」 | **成立**（但检索表格有一行不可复现） | 事实陈述，基本可信 |
| 1b | 引擎契约拒绝多芯载流表，所以 (c) 只能等裁定 | **不成立**：一句话把「无来源的自加约束」和「真实的产品方法边界」混成一件 | 范围偷换 |
| 2 | 6521/6522「datasheet 未与之关联」 | **不成立**：结论（不写入）可辩护，理由是假的 | 事实错误 + 论证错配 |
| 3 | SAJ HS3/CB2 端子图「留下一批」 | **不成立**：三层证据全部已就绪，无需任何前置工序 | 无依据缩圈 |
| 4 | 多簇搜索「需另一次产品裁定，不在本批范围」 | **不成立**：厂商原文给出了多柱扩展路径，仓库已记录；规格把实现缺口写成了不变量 | AI 自造约束 |

四条里有三条（1b、2、4）的**结论方向可能是对的，但被用来支撑它的理由经不起核对**；
第 3 条既无数据面理由，也违反 AGENTS §0.0「本轮发现的问题必须在本轮全部解决」。

---

## 1. 声明一：`cables.json`「从来没有产出过」，且引擎契约拒绝多芯载流表

### 1.1 第一论据「文件不存在」——成立，但检索表有一行是错的

实际执行的检索与结果：

```
git log --all --diff-filter=A -- '*cables.json'      → 空
git log --all -- '*cables.json'                      → 空
git rev-list --all --objects | grep -F cables.json   → 空
git ls-remote --heads origin | wc -l                 → 1（只有 refs/heads/main）
```

- **仓库全史的每个可及对象里都没有 `cables.json`**。`git rev-list --all --objects` 覆盖所有 ref
  （含 `packed-refs` 里的 `refs/codex/turn-diffs/*`、`refs/review/pr-*`），这是比 `git log` 更强的检查。
- 追加检查了 `git fsck --lost-found` 列出的全部 dangling commit，逐个 `git ls-tree -r` 扫过，
  也没有任何一条包含 `cables.json`。所以「连悬空对象里都没有」这一点也成立。
- `.scratch/`、`/Users/chesterjohn/de-linker-data`（含 `pdf/`、`apify-oem/`）、`/tmp` 均无。
- 历史会话日志：`/Users/chesterjohn/.codex/sessions/2026/11/` 全月 grep `cables.json` = 0 命中；
  Kimi 会话目录里只有**本次复核自己**产生的命中。

**但 `cable-blocker.md:21` 的「全部 `origin/*` 分支（32 个）」不可复现**：
`git ls-remote --heads origin` 现在只返回 `refs/heads/main` 一行。PR #895 正文
（`gh pr view 895`）重复了同一句「all 32 remote branches」。这个数字要么来自已被删除的远端分支
（删除后无法用任何命令验证），要么是写声明时未实际执行。无论哪种，**一条列在「已核对」表格里的证据行
本身不可核对**，这削弱了整张表的可信度。

结论：**「从来没有产出过」这个事实判断成立**；支撑它的检索表中至少一行不实。

### 1.2 第二论据「引擎契约拒绝多芯与 AC」——把一个自加约束和一条产品边界混为一谈

`cable-blocker.md:34-69` 把两处限制并列，用它们共同证明「这里缺的不是数据，是裁定」。核对后这是两件不同的事：

**(A) `CableReferenceCurrentRating` 的三种 `laying` 字面量 —— 不是产品边界，是两份 Nexans datasheet 的原文行。**

```python
class CableReferenceCurrentRating(Document):
    """One cited manufacturer table row, not a site ampacity clearance."""
    laying: Literal["single_in_air", "single_on_surface", "two_touching_on_surface"]
```

这一整个类由 `4fb635e85`（2026-11-02，"Deliver source-bound conductor comparisons and correct cited product answers"）引入，
**不是** #548 的产物。三条字面量与 `plugins/linker-commerce/data/cable-references.json` 里
两份 Nexans PDF p.2 的原文逐字对应，且电流值被写死在迁移脚本里校验：

`tools/migrate/548-cable-reference-currents.py:57-73` 的 `LAYINGS` 与 `ORIGINALS`：
`single_in_air` 55 A / `single_on_surface` 52 A / `two_touching_on_surface` 44 A（1×4 mm²），
70/67/57 A（1×6 mm²）。这两个型号就是全部已入库的电缆参考。

也就是说：这三种敷设方式是**为了容纳恰好两份原件**而确定的枚举。它是数据形状，不是「产品只支持单芯」的建模决策。
把「枚举目前只覆盖两条表行」说成「契约本身挡着多芯」，是把**样本不足**说成了**模型不适用**。

**(B) `construction != "single_conductor"` 拒绝载流表 —— 这才是真正的自加约束，且没有规格来源。**

```python
if self.reference_current_ratings and self.construction != "single_conductor":
    raise ValueError("reference-current table requires a single conductor")
```

同一次提交（`4fb635e85`）加入。检索全部规格：

- `grep -rn "reference_current_ratings\|载流" docs/specs/` 只命中 `docs/specs/548-design-geometry.md:187` 一段，
  内容是「60 °C 环境 / 120 °C 导体温度的表行不是现场额定，也不是持续时长额定」——**讲的是不要把表行当通用额定值用，没有一句禁止多芯携带载流表**。
- `docs/specs/548-design-geometry.md`「Comparing current with a cited cable table」一节明确写的是
  「Each row has its own cable product and revision, laying condition, … Use the exact recorded table conditions」，
  约束落在**条件匹配**上，不落在**芯数**上。

所以这条 validator 是本轮实现时多写的一行互斥，没有对应规格要求。它是可删的假规则，
不是需要裁定的产品语义。

**(C) 「比较方法只做单芯」——这一条是真的产品边界。**

```python
METHOD = "installation_single_conductor_reference_current_v1"
...
"scope": "single_conductor_reference_only",
```

`installation_reference_current.py` 里有四处 `construction != "single_conductor"` 分支（`:168`、`:204`、`:205`、`:220`），
它们是**比较方法适用范围**的表达：只有一条无分支路径、且两端在同一回路时，才拿项目电流与表行比。
这一条改动确实扩大产品能力，需要产品裁定 —— 但它与 (B) 不是同一件事，(B) 完全不必被它拖住。

**这就是本条声明的技术核心：把 (A)(B)(C) 三件事打包成「契约挡着」，用一个真边界替一个假规则挡枪。**
真实缺口是 (C) 的方法扩展；而 (B) 是当场可以删除的无依据约束。

另外，`:30` 的结论「不能靠推断补造」是对的，`AGENTS.md §6` 也确实是这个意思。
但 `:73` 引用「§2『本轮发现的问题必须在本轮解决』」时把节号写错了 —— 那是 §0.0 第三条，
§2 是业主裁定。引用错误不影响结论，但它说明这份文件在写作时没有回查原文。

### 1.3 被跳过的工作量

- (B) 的删除：1 处 Python validator + 1 处 PHP 副本（`CableFacts.php:72` 的
  `( array() !== $raw['reference_current_ratings'] && 'single_conductor' !== $raw['construction'] )`）
  + 对应测试。**这是小时级、无外部依赖的改动**，被写成了「需要裁定」。
- (A) 的枚举扩展：每加一份新原件，就多一种 `laying` 取值。这是数据驱动，不是设计决策。同样被写进阻塞理由。
- (C) 的方法扩展：确实需要设计，但 `cable-blocker.md:71-84` 已经把它写清楚了，本可以作为
  「本批不做，理由是本批缺数据」的诚实陈述，而不是用 (B) 去加强。

---

## 2. 声明二：6521/6522「datasheet 未与之关联」

### 2.1 生产 feed 现状（2026-11-04 实读）

`GET https://de-linker.com/wp-json/linker/v1/engineering-feed` → HTTP 200，1,398,943 B，
`schema_version=1`，`source_revision=b6b6f2be36e94dd3462ccca9377169ced33aa481aa0084a40b82e290100c276a`，
**85 个产品**（不是 106；那是 2026-10-22 的旧读数）。

| 产品 | model | 挂载文档数 | `stacks_parallel_max` |
| --- | --- | --- | --- |
| 3611 | GW6.0-BAT-D-G20 | 7 | 12 |
| 3612 | GW9.0-BAT-D-G20 | 7 | 12 |
| 6519 | GW5.1-BAT-D-G20 | 6 | 12 |
| 6520 | GW8.3-BAT-D-G20 | 6 | 12 |
| **6521** | **GW5.1-BAT-D-G21** | **4** | **无** |
| **6522** | **GW8.3-BAT-D-G21** | **4** | **无** |

**6521/6522 实际挂 4 份文档，不含 Lynx D G2 datasheet**：
DE 手册 V1.4、EN 手册 V1.5、ESA 5–30 kW Datasheet (EN)、IEC 62619 CB 证书。

> 交付工单里「6521/6522 各挂 7 份文档，含 Lynx D G2 datasheet」这一前提**与实测不符**。
> 7 份是 3611/3612 的数字。本次复核按实测更正。

### 2.2 「未关联」这句话的真伪

字面上**成立**：6521/6522 的 `documents[]` 确实不含 Lynx D G2 datasheet。
`tools/migrate/548-battery-parallel-limits.json` 的 `unbound` 段原文是：

> "The 12-unit parallel statement lives in the Lynx D G2 datasheet (EU-EN V1.1), which is associated with 3611/3612/6519/6520 only. 6521/6522 carry the IEC 62619 certificate, which prints no parallel limit, so no figure is written for them."

**但把它当作「做不了」的理由不成立**，因为能证明 12 的那份文件就挂在 6521/6522 上。

`GW_ESA-5-30kW_Datasheet-EN.pdf`（feed 里 `doc-fd3667cc…`，sha256 `b681fbb5…`，
`product_ids` 包含 6521 与 6522）**p.3 的技术数据表明确列出 G21 两列**：

```
Technical Data        GW5.1-BAT-D-G20  GW8.3-BAT-D-G20  GW5.1-BAT-D-G21  GW8.3-BAT-D-G21  GW6.0-BAT-D-G20  GW9.0-BAT-D-G20
Scalability*4                          12 pcs
*4: For single-column stacked installations, the maximum number of parallel units is 6.
```

我实下载该 PDF 得 sha256 `b681fbb51b1688476883c7f2c23599f12a1e51020b6980c9d61da952cc80543f`，
与 feed 的 `blob_sha256` 一致；`pdftotext -f 3 -l 3` 输出上表。

关键点：**feed 里 6521/6522 的 `modules_per_system_max = 12` 本来就引用这份 PDF 的 p.3**
（citation url `…/2026/09/GW_ESA-5-30kW_Datasheet-EN.pdf`，page 3）。
所以「12 这个数字可以从哪份已关联文档得到」这个问题，在同一份 feed 里已经有答案。

### 2.3 Lynx D G2 datasheet 是否覆盖 G21：不覆盖

`GW_Lynx-D-G2_Datasheet_EU-EN_V1.1.pdf`（sha256 `31e69160…`，已实下载核对）p.2 技术数据表只有
**GW5.1/8.3/6.0/9.0-BAT-D-G20** 四列，**没有 G21**。p.1 的正文是系列级陈述
（"supporting up to 12 units in parallel and multi-cluster expansion"）。

所以严格说：**给 G21 写 12，正确来源是 ESA datasheet p.3，不是 Lynx D G2 datasheet p.1。**
PR #895 给 3611/3612/6519/6520 用 Lynx D G2 p.1 是对的（那四款在 p.2 表内）；
给 6521/6522 沿用同一条 citation 反而会引错页。声明没有做这件事是**对的**，
但它给出的理由（"datasheet 未关联"）让人以为「找不到证据」——实际是「证据在另一份、已关联的文件里」。

### 2.4 补齐 6521/6522 需要多少实际工作

对照 `548-battery-parallel-limits.json` 里 3611/3612/6519/6520 的条目形状，每款只需：

1. `products` 里加一个 key（`"6521"` / `"6522"`），带 `model` + `sku`（feed 里已有：
   `DLK-GOODWE-GW51BATDG21` / `DLK-GOODWE-GW83BATDG21`）。
2. `figures.stacks_parallel_max` 一条 patch：`expect: null`、`set.value: "12"`、`unit: "units"`、
   `citation: {url: …/GW_ESA-5-30kW_Datasheet-EN.pdf, page: 3}`。
3. `source`：`document_id` 用 feed 里已绑定的 `doc-fd3667cc7cbcbc8fadb5added7c06b4f38ef2ccaf3ff97fc0b8561d4439ca45f`，
   `blob_sha256 b681fbb5…`，`document_revision 71df5b59…`，`page: 3`，
   `quote` 取 p.3 的 `Scalability*4  12 pcs`（以及脚注 `For single-column stacked installations, the maximum number of parallel units is 6.`，
   这一点必须写进 `basis`，否则会把 12 说成「一柱 12 块」）。
4. `unbound` 段删掉 6521/6522 那一条。

**没有新增文档托管、没有新增数据抓取、没有 schema 改动。** 迁移脚本 `548-battery-parallel-limits.py`
对 `products` 的 key 集合没有硬编码白名单（`:71-95` 只校验形状），新增两个 key 不需要改脚本。
真正需要额外注意的只有第 3 步的 `basis`：ESA datasheet 的 12 与 Lynx D G2 的 12 表达的是同一件事
（系统级可扩展 12 块），但分柱上限都是 6，这个区分必须在 basis 里写清。

工作量估计：**一次 plan 文件编辑 + 一次 preview/apply/rollback 循环**，与已完成的 8 条同量级，
不需要新会话、不需要新研究。

### 2.5 附带发现：`column_limit_issue` 把「每柱 6」错误地施加到整个系统

`services/engine/src/linker_engine/planning/equipment_assessment.py:483-490`：

```python
if any("limits one column to six batteries" in text for text in condition_texts):
    if count is None or stacks is None:
        column_limit_issue = "unresolved"
    elif count > 6 or stacks != 1:
        column_limit_issue = "violated"
```

`count` 是 `modules_per_stack`，判 `count > 6` 是对的；但 `stacks != 1` 意味着**只要选了多柱就一律 violated**。
而 `GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf` p.80 的原文（我实下载并 `pdftotext` 核对）说的是：

> "The system supports 5-108kWh. A single column can stack up to 6 batteries. If there is more energy demand,
> or other scenarios requiring capacity expansion such as reducing the stacking height of a single column
> due to installation conditions, please contact GoodWe or a dealer to purchase a battery expansion kit."

厂商对「超过 6 块」给的是**明确的合法路径：买 battery expansion kit 做多柱**。
`plugins/linker-commerce/data/compatibility-lists.json:349` 也已经把这句原样记录下来了。

所以 `stacks != 1 → violated` 与本条声明是**同一个错误的两个面**：都假设「多柱不在支持范围内」。
这一条直接关系到声明四，见下。

---

## 3. 声明三：SAJ HS3 / CB2 端子图「本批未纳入」

原文（`terminal-map-coverage.md:100`）：
> **SAJ HS3 / CB2 的端子图**：本批未纳入（任务范围只列到 H2）；HS3 手册 p.22 的端口表可作为下一批输入。

核对结论：**三层证据全部已经就绪，没有任何前置工序**。

### 3.1 Woo / 生产 feed 层

`GET …/engineering-feed`（`source_revision b6b6f2be…`）里：

| 文档 | document_id | blob_sha256 | 页数 | 挂载产品 |
| --- | --- | --- | --- | --- |
| `SAJ_HS3_3-12K-T2_User-Manual_EN_V4.pdf` | `doc-038446b5…` | `2c1dd5c1…` | 125 | 1185 / 1186 / 1187 / 2093 / 2198 / 2199 |
| `SAJ_CB2_57.3-100.3-HV5_User-Manual_EN_V0.0.pdf` | `doc-62719dde…` | `ee6b3a41…` | 38 | 4103 / 4104 / 4105 / 4106 |
| `SAJ_CB2_57.3-100.3-HV5_Quick-Installation-Guide_EN.pdf` | `doc-74c741e3…` | `a70cb4c3…` | 20 | （feed 内） |

我实际从生产 URL 下载并核对字节：
HS3 手册 sha256 = `2c1dd5c1e2f7efd96eba4f24aa3804ee135936ac90bcccfd1a681f2188868f46`（125 页），
CB2 手册 sha256 = `ee6b3a41b8250367c67e285e5d69c15f19981eda3d83fdd476226393cb38cff5`（38 页）——
两份都与 feed 的 `blob_sha256` **逐字节一致**。

### 3.2 VPS 知识索引层（只读）

`linker-services`（VPS）上 `/opt/linker-genie/index/current` → `20261103T203607Z-950501000`。
只读查询 `index.sqlite`：

```
documents: 2c1dd5c1…(HS3 manual, 125p, indexed), ee6b3a41…(CB2 manual, 38p, indexed), a70cb4c3…(CB2 QIG, 20p, indexed)
chunks:   HS3 p22 → 7 chunks（含 "Table 2.1. Description of the ports, switches, and LED on the inverter"）
          CB2 p10 → 6 chunks；CB2 p11 → 3 chunks（含 "| Callout | Silkscreen | Function |" 全表）
          CB2 QIG p5 → 5 chunks
```

### 3.3 原件事实（我逐页读的）

**HS3 手册 p.22**，`Table 2.1. Description of the ports, switches, and LED on the inverter`，16 项：

| # | Silkscreen | 域 |
| --- | --- | --- |
| 1 | SIM CARD | （4G 模块） |
| 2 | EMS | communication |
| 3 | LAN | communication |
| 4 | GRID | ac |
| 5 | BACK-UP | ac |
| 6 | COMM | communication |
| 7 | （接地符号） | pe |
| 8 | WIFI / 9 4G | communication |
| 10 | （LED 面板） | — |
| 11 | PV1 (+, −), PV2 (+, −) | pv_dc |
| 12 | BAT (+, −) | battery_dc |
| 13 | BMS CAN | communication |
| 14 | START / 15 DC SWITCH / 16 BATTERY SWITCH | — |

**CB2 手册**：`3.5 Battery Terminals Description`（PDF p.10，`Table 3.1` 电池模块 A–G）
与 `Table 3.2. Terminal descriptions of the battery control unit`（PDF p.11，A–M）：

| Callout | Silkscreen | Function |
| --- | --- | --- |
| A | A, B, C, D, E, F, G | 到 CH2 逆变器与扩展 CB2 的防水接头 |
| B | / | AC 断路器 |
| C | P+ | DC 正极（逆变器） |
| D | P− | DC 负极（逆变器） |
| E | Start | 启动按钮 |
| F | / | 主开关 |
| G | FAN | 风扇 |
| H | BAT− | 首个电池模块负极 |
| I | BAT+ | 末个电池模块正极 |
| J | AC220V | 220 V AC 供电 |
| K | COM_PCS | 接逆变器 BMS_1 |
| L | COM_PAR | 接扩展电池系统 |
| M | COM_BMU | 接电池模块 |

### 3.4 为什么这条声明站不住

1. **「任务范围只列到 H2」是循环论证。** 任务范围本身就是 PR #895 那批人自己划的。
   用「我划的范围不含它」证明「不该做」，等于用结论证明结论。AGENTS §0.0 第三条明确禁止
   「以 out of scope／以后处理规避修复」。
2. **没有任何数据面障碍。** `installation_terminals.py:105-140` 要求的四件事
   （`basis == "manufacturer_terminal_map"`、`terminal_domain` 命中白名单、`terminals` 为非空字符串数组、
   `source.document_id`/`document_revision` 等于当前绑定）在两族上都已满足或可直接满足：
   document_id 与 document_revision 在 feed 里都有，枚举域 `ac / pe / battery_dc / pv_dc / communication`
   在 HS3 p.22 与 CB2 p.10–11 都能直接映射。
3. **仓库已有同样的先例。** 同一份 `548-installation-facts.json` 里 SAJ H2 六款各 5 条端子事实
   （`mppt-pv-input-terminals` / `battery-input-terminals` / `communication-terminal` / `ac-terminals` / `grounding-terminal`），
   每一款的 `model` 与 `sku` 都在 feed 里。HS3/CB2 只是照着同一个形状再加 5 款 + 4 款。

### 3.5 被跳过的工作量

按 H2 的形状估算（HS3 6 个产品 × ~5 条，CB2 4 个产品 × ~4 条，共约 46 条事实）：

- HS3：`pv_dc`（PV1/PV2）、`battery_dc`（BAT+/BAT−）、`ac`（GRID/BACK-UP）、`communication`（EMS/LAN/COMM/BMS CAN）、`pe`，
  全部引 p.22，一份文档、一页、一张表 → 6 个产品共用同一份事实内容，只是 `product_id` 不同。
- CB2：`battery_dc`（P+/P−/BAT+/BAT−）、`ac`（AC220V 与 AC 断路器）、`communication`（COM_PCS/COM_PAR/COM_BMU）、`pe`，
  引 p.10 与 p.11 两页 → 4 个产品共用。

**没有新文档托管、没有新抓取、没有新 schema。** 与 (b)(d)(e) 已完成的 244 条同一条流水线：
写进 `548-installation-facts.json` → preview/apply/rollback → 用真实 `InstallationFacts::bind()` 跑一遍。

---

## 4. 声明四：多簇搜索「需另一次产品裁定，不在本批范围」

原文（`README.md:56-62`）：
> `stacks_parallel_max` 落库后 …… 但 `equipment_search_space.py:180` 仍固定 `parallel_stacks = 1`，
> 注释写明「The supported template has one external battery assembly. No undocumented parallel count is invented to satisfy demand.」
> 也就是说：**本批补的是证据，不是新的搜索能力**。要让配置器真的给出多簇方案，需要另一次产品裁定（模板是否支持外部多簇、报表如何呈现），不在本批范围。

### 4.1 代码与注释的来源：AI 自己写的，不是业主裁定

```bash
git log -L 173,185:services/engine/src/linker_engine/planning/equipment_search_space.py
→ 0cf50fa65  Search and adopt Woo-bound multi-system equipment plans
            (2026-10-26 15:48:02 +0800)
```

**代码注释与 `parallel_stacks=1 if battery else None` 是同一个 commit、同一次新建文件时写下的**
（`equipment_search_space.py` 在该 commit 里是 new file）。作者 `AssassinFlash`（本项目的 AI 执行线账号），
commit body 只有一行标题，没有任何业主裁定引用。

再看规格侧：

```bash
git log -S "one external battery assembly" -- docs/specs/548-workbench-application.md
→ 8b7985d2d  Search current Woo equipment configurations and preserve selected candidate evidence
            (2026-10-25 07:23:05 +0800)
```

`docs/specs/548-workbench-application.md:285` 的原文是：

> "The implemented template is one converter with one external battery assembly, or no battery
> when both storage demands are explicitly zero. … No missing count, parallel capability,
> sales-unit identity or manufacturer condition is invented."

**这句话的措辞本身就是自我暴露**：主语是 "The **implemented** template"（已实现的模板），
即规格在描述当时那份代码的形状，而不是在记录一条业务决策。
而且它在同一句里把「不凭空发明并联能力」与「只有一块电池」并列 ——
前者是不该做假数据的正确原则，后者是实现缺口，两件事被写成了同一条不变量。

`AGENTS.md` 2026-10-09 的裁定是：

> 产品与 SKU 原样保留，不建套装 SKU；**组合由工具按兼容合同即时算出**。

「即时算出」意味着搜索空间应当由 `compatibility.json` 的合同与产品事实决定，
而不是由一个硬编码常量决定。当前实现是后者。

### 4.2 assessment 侧早已支持 `stacks > 1`，而且支持得相当完整

`services/engine/src/linker_engine/planning/equipment_assessment.py`：

- `:322` `count, stacks = selection.modules_per_stack, selection.parallel_stacks`
- `:455-459` `modules_per_stack` 的上界会按 `sys_max_val // stacks` 收窄 —— **已经按柱数折算系统总量上限**
- `:546-559` `parallel_stacks` 检查项：`stacks == 1` → `satisfied`；
  `stacks <= parallel`（`stacks_parallel_max`）→ `satisfied`；否则 `violated`
- `:687-688` `sales_unit_kind == "battery_system"` 时 `multiplier = stacks`
- `:682-683` `battery_module` 时 `multiplier = count * stacks`
- `:827-828` `discharge_bounds.append(bat_discharge_kw * stacks)`

也就是说：**判定、BOM 数量、放电边界、系统总量收窄，四处都已经按 `stacks` 计算。**
唯一的缺口是搜索侧不生成 `stacks > 1` 的候选 —— 一个枚举循环的参数。

这与 PR #895 自己写的「本批补的是证据，不是新的搜索能力」正好相反：
它补的 `stacks_parallel_max` **唯一消费者**就是 `:546` 那个检查项，
而那个检查项只在 `stacks > 1` 时才有区分度（`stacks == 1` 恒为 `satisfied`）。
补了上限却永远只喂 `stacks = 1`，等于给一把锁配了钥匙却把门钉死。

### 4.3 厂商原文对多柱的立场：支持，且给出了采购路径

`GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf` p.80（我实下载、`pdftotext` 核对）：

> "The system supports 5-108kWh. A single column can stack up to 6 batteries. If there is more energy demand,
> or other scenarios requiring capacity expansion such as reducing the stacking height of a single column
> due to installation conditions, please contact GoodWe or a dealer to purchase a battery expansion kit."

p.337 技术数据脚注同理：`*3: For single-column stacked installations, the maximum number of parallel units is 6.`
datasheet p.3 脚注相同。

`plugins/linker-commerce/data/compatibility-lists.json:349` 已经把这句原文记录为约束：

> "Printed p79 (PDF p80) states that one column can stack up to six batteries. For capacity expansion,
> including where installation conditions require a lower stack per column, the manual directs customers
> to GoodWe or a distributor for the battery expansion kit. This is a per-column installation limit;
> the datasheet separately prints system scalability of 12 pcs."

**厂商说的是「超过 6 块时买扩展套件做多柱」，不是「不支持多柱」。**
仓库在 2026-09-27（`verified_on`）就把这段话记录下来了。
所以「多簇是否支持」不是一个未决的产品问题，而是**已有厂商原文、已有仓库记录、只差搜索侧枚举**的实现问题。

### 4.4 判定

- **注释没有真实业务来源。** 它是 2026-10-26 一次搜索实现时写下的工作假设，随后被 2026-10-25 的规格
  （时间上更早，但内容同样出自 AI 线）以 "implemented template" 的措辞固定下来，形成互相印证的闭环。
- **「需要另一次产品裁定」不成立。** 厂商原文给了路径；`AGENTS.md` 2026-10-09 已裁定「组合由工具按兼容合同即时算出」；
  assessment 侧四处已按 `stacks` 计算。剩下的是实现工作。
- **真正需要裁定的只有一件事**：多柱方案在报告里怎么呈现（BOM 按「柱 × 块」还是按总量、报告如何标注扩展套件）。
  这一点 `README.md` 提对了，但它不该成为整条能力不做的理由 —— 报告呈现可以在实现后单独确认，
  也可以先按现有 BOM 结构（`multiplier = count * stacks`）呈现。

### 4.5 顺带修掉的同源错误

`equipment_assessment.py:489` 的 `elif count > 6 or stacks != 1: column_limit_issue = "violated"`，
把「每柱 6 块」错误地施加成「必须单柱」。厂商原文与仓库自己的 `compatibility-lists.json:349` 都说明
多柱是合法扩展路径。这一条与声明四是同一个假设的两个面，修声明四时应一并修正。

---

## 5. 流程根因：这四条声明是怎样未经质询进入主线的

### 5.1 事实链

| 环节 | 记录 | 缺口 |
| --- | --- | --- |
| 声明写入 | `ccc58a774`（02:13，同时加入 `cable-blocker.md` 与 `conflict-rulings.md`）、`52c960cdb`（02:19，单独加入 `terminal-map-coverage.md`，1 file / 100 行）、`eec0544a0`（02:29，`README.md`） | 三条都是 `docs(#548):` 前缀的**纯文档提交**，不含代码、不含测试 |
| 第一次进 main | PR #897（`fix/planner-maintenance-timeout`）| 18 files / +9509 / −3521；**`reviews: []`**；带 3 个 FAILURE check（`php-lane`、`engine`、`check`）；merge `a3810dec4` @ 18:40:16Z |
| 第二次进 main | PR #895（`fix/548-evidence-mega-batch`）| 4 files / +131 / −28；**`reviews: []`**；merge `87f6485bf` @ 20:16:30Z（CST 04:16） |
| 事后记录 | `466473ed3`「record the two CI failures that are not from this change」| 把 `engine` lane 的失败归为 "infrastructure symptoms"，未修 |

### 5.2 验证缺口具体在哪几步

**缺口一：CI 对这类声明在结构上不可能有判别力。**
`cable-blocker.md`、`terminal-map-coverage.md`、`conflict-rulings.md` 都是 Markdown，
CI 能证明的只有「文档没写坏」。它们的内容正确性**不在任何自动检查的覆盖面上**。
PR #895 正文的 Verification 一节列了 7 项（ruff / mypy / pytest 366 passed / engine 1319 passed / PHPUnit 66 / PHPStan / 244+8 quote 命中），
**全部是针对代码与引文的**，没有一项检查「unbound 段的理由是否为真」。
PR #897 的 `engine` lane 甚至是 FAILURE，在这次 merge 前后都没有恢复。

**缺口二：zero review 的两次 self-merge 绕过了 AGENTS §0.0 的父线亲验。**
AGENTS §0.0（业主 2026-11-04）原文要求：
> 任何子代理的产出——PR、CI 状态、测试结果、生产读回、工单关单、文件与数据写入——在作为交付依据采纳前，
> 必须由主线（或明确指定的验证端）自己复核一次（看真实 diff、真实 CI run、真实生产数据/订单/收件）。

这条规则本身直到 `a4fc28240`（2026-11-04 01:46:12 +0800，"docs(agents): subagent output must be re-verified by the parent line"）
才写进 `AGENTS.md`，而声明是在 02:13–02:29 写下的 —— 时间上晚于规则，早于 PR #895 的 merge（04:16）。
也就是说：**规则在生效的同一晚，声明的写入过程仍然没有执行它。**

具体缺的是这三步，而每一步都是可执行的：
1. 读 `engineering-feed` 核对「6521/6522 datasheet 未关联」（一条 curl 即可推翻，本次复核就是这么做的）；
2. 查 `documents` 表 / feed 里 HS3、CB2 手册是否存在（一条 grep 即可推翻）；
3. `git log -S` 查注释来源（一条命令即可推翻）。

**缺口三：规格被实现反向定义，而规格又是下一次的"依据"。**
`docs/specs/548-workbench-application.md:285` 用 "The implemented template is …" 描述当前代码，
后续引用规格的人会把这条描述当成既定约束。声明的「需要另一次产品裁定」正是这样来的。
规格应当写「要做什么」，而不是「现在是什么」。这一条在四条声明里重复出现了两次（声明一与声明四）。

**缺口四：把「我划的范围」当作「不该做的理由」。**
`terminal-map-coverage.md:100` 的「任务范围只列到 H2」是完整的循环论证。
AGENTS §0.0 第三条明确禁止这种以 out of scope 规避修复的做法。这一条不需要任何外部事实就能在写作时自查。

**缺口五：结论方向正确但不代表论证正确。**
声明二（不写 6521/6522）与声明四（不改搜索）**执行结果上未必是错的**——
前者确实不该照抄 Lynx D G2 的 citation，后者确实牵涉报告呈现。
但它们给出的**理由**是假的，而假理由会阻止下一个人去做那件其实很小的工作。
这是比「做错了」更难发现的失败模式：错误不会以 bug 的形式暴露，只会以「一直没做」的形式停留。

### 5.3 一句话根因

**这四条声明都是「自评式交付」的产物**：写声明的人同时是自己工作的验收人，
而验收标准是「我有没有伪造数据」（这条守得很好）而不是「我有没有跳过能做的工作」（这条完全没有检查）。
`AGENTS.md §0.0` 要求的父线亲验，对「理由是否成立」这一层从未实际执行。

---

## 6. 逐条实际工作量汇总

| 项 | 需要的动作 | 预估 |
| --- | --- | --- |
| 1b. 删自加约束 | 删 `cable_facts.py:83` 的 `construction != "single_conductor"` guard、删 `CableFacts.php:72` 同名条件、补/改测试 | 小时级，无依赖 |
| 1c. 多芯/AC 载流方法 | 真的需要设计（组合键、AC 参数），**且需要真实载流数据**。本批没有数据，暂停是对的 | 需要先有数据 |
| 2. 6521/6522 补 12 | 编辑 `548-battery-parallel-limits.json` 加 2 条，citation 改用 ESA datasheet p.3，basis 写清「每柱 6」 | 与已完成的 8 条同量级 |
| 3. HS3/CB2 端子事实 | 照 H2 形状加 ~46 条事实，引 HS3 p.22 / CB2 p.10–11 | 与 (b)(d)(e) 同一流水线 |
| 4. 搜索侧多柱 | 改 `equipment_search_space.py` 的枚举；顺带修 `equipment_assessment.py:489` 的 `stacks != 1 → violated` | 枚举改动小，报告呈现需确认 |

三条（1b、2、3）**没有任何外部阻塞**，全部可以在同一批内完成。

---

## 7. 复核用到的命令与读数（可重跑）

```bash
# 声明一
git log --all --diff-filter=A -- '*cables.json'
git rev-list --all --objects | grep -F cables.json
git fsck --lost-found --no-progress            # 再对每个 dangling commit 做 git ls-tree -r
git ls-remote --heads origin                    # 现为 1 行（只有 main）
grep -rlF "cables.json" ~/.codex/sessions/2026/11/

# 声明一第二论据考古
git log --diff-filter=A -- services/engine/src/linker_engine/planning/cable_facts.py   # → 90e9a5691
git show 4fb635e85 -- services/engine/src/linker_engine/planning/cable_facts.py
git log -S "reference_current_ratings and self.construction" -- services/engine/

# 声明二
curl -s https://de-linker.com/wp-json/linker/v1/engineering-feed -o feed.json
curl -sO https://de-linker.com/wp-content/uploads/2026/09/GW_ESA-5-30kW_Datasheet-EN.pdf
pdftotext -f 3 -l 3 -layout GW_ESA-5-30kW_Datasheet-EN.pdf -    # G21 两列 + Scalability 12 pcs

# 声明三
ssh linker-services 'python3 -c "import sqlite3; c=sqlite3.connect(\"file:/opt/linker-genie/index/current/index.sqlite?mode=ro\",uri=True); …"'
pdftotext -f 22 -l 22 -layout SAJ_HS3_3-12K-T2_User-Manual_EN_V4.pdf -
pdftotext -f 10 -l 12 -layout SAJ_CB2_57.3-100.3-HV5_User-Manual_EN_V0.0.pdf -

# 声明四
git log -L 173,185:services/engine/src/linker_engine/planning/equipment_search_space.py
git log -S "one external battery assembly" -- docs/specs/548-workbench-application.md
pdftotext -f 80 -l 80 -layout GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf -    # battery expansion kit

# 流程
gh pr view 895 --json reviews,statusCheckRollup,mergedBy,mergedAt
gh pr view 897 --json reviews,statusCheckRollup,mergedBy,mergedAt
git log -1 --format='%H %ad' a4fc28240
```

---

## 8. 与交付工单前提不一致处（如实记录）

- 工单称「6521/6522 各挂 7 份文档，含 Lynx D G2 datasheet」。实测：**各挂 4 份，不含 Lynx D G2 datasheet**；
  7 份是 3611/3612 的数字。本报告按实测更正，并相应调整了第 2 条的论证路径
  （真正可用的证据是 ESA datasheet p.3 的 G21 列，不是 Lynx D G2 datasheet）。
- 工单称 feed 有 106 个产品；本次实测 85 个（`source_revision b6b6f2be…`）。106 是 2026-10-22 的旧读数。
