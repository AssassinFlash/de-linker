# US5000 V1.3 手册替换与 410 链接：执行记录

日期：2026-11-11（北京时间）。分支 `b-us5000`，基于 main `37c62f15d`。
承接：本目录 `README.md` §6.1（US5000 跨版本）、§6.3（三个 Pylontech 数据表 410）。

范围：产品数据（`material-registry.json`）与 review 实例的托管文档 / 产品 meta。
**未改**引擎、插件代码、模板、生产站点。生产部署待主控验收后统一安排。

---

## 0. 结论表

| # | 项 | 结果 |
| --- | --- | --- |
| 1 | US5000 手册 V1.0 → V1.3 | **已完成**（review 实例附件 `9557`，SHA 与原件一致） |
| 2 | 电压窗口 43.5~53.5 → 43.5~53.2 | **已完成**（registry + 产品 figures，均引 V1.3 p14） |
| 3 | 推荐电流 80 → 100 A | **已完成**（产品 figures 记 `100 A`，V1.3 p14；registry 不加字段，理由见 §1.3） |
| 4 | 三个数据表 410 | **未按原判处理**：410 不是文件失效，是发布门对 draft 产品的正常拒绝。根因与处置见 §5 |
| 5 | 三个数据表的“重新托管” | **阻断**：现行官方数据表印刷错误，不能作为事实源。见 §6 |

---

## 1. 逐项：证据 → 改动 → 读回

### 1.1 US5000 手册替换（V1.0 → V1.3）

**证据**

- `originals/pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf`
  44 页，3,920,843 B，`sha256 43088b8060b082f3427913bfc0de471cc425474d9de7c1329c4d5d4eceeb4062`
  （本次独立复算，与 README §11 记录逐字节一致）。
  PDF 内嵌 CreationDate `2026-01-12 14:02:19 CST`，封面 `Information Version: 1.3 / 5PMPA08-20078`。
- 被替换件 `originals/pylontech_US5000_Installation-Manual_5PMPA08-00219_V1.0.pdf`
  36 页，2,430,453 B，`sha256 70ae894fc6f22bed50c51417c1b35d825ef88c02badb5f31f7694ef11c04b134`，
  封面 `Information Version: V1.0 / 5PMPA08-00219`。

**改动（review 实例，WP-CLI `media import`）**

| 项 | 值 |
| --- | --- |
| 附件 ID | `9557` |
| 标题 | `RESS-Installation Manual-US5000 US5000-B 5PMPA08-20078_V1.3` |
| URL | `http://127.0.0.1:8889/wp-content/uploads/2026/11/pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf` |
| MIME / 状态 | `application/pdf` / `publish` |
| 落盘 SHA-256 | `43088b80…4062`（与原件一致） |

命名沿用既有 `RESS-Installation Manual-<model> <doc-number>_<version>` 词序，只把文档号与版本换成本次原件。

**读回**：`wp_get_attachment_url()` 与 `hash_file('sha256')` 见 §4.1。

### 1.2 电压窗口 43.5 ~ 53.5 → 43.5 ~ 53.2

**证据（V1.3 原件物理 p14 = 印刷 p8，`System Specifications` 表）**

```
Operation Voltage Range (VDC)                 43.5~ 53.2
```

V1.0 同一表（物理 p11 = 印刷 p8）该处是**两行**：

```
Discharge Voltage (VDC)                       43.5 ~ 53.5
Charge Voltage (VDC)                          52.5 ~ 53.5
```

即 V1.3 把两个分开的行合并成一行 `Operation Voltage Range`，上界由 53.5 收窄到 **53.2**。

**改动**

- `plugins/linker-commerce/data/material-registry.json` → `materials.mat_pylontech_us5000.technical.specifications.module_voltage_range_v`
  `43.5 ~ 53.5` → **`43.5 ~ 53.2`**，`citation` `{doc: V1.0 旧件, page: 11}` → `{doc: pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf, page: 14}`。
- review 实例产品 `1134` 的 `_tv_b2b_figures.module_voltage_range_v` 同步为 `43.5 ~ 53.2`，citation 指向 V1.3 p14。

### 1.3 推荐电流 80 → 100 A

**证据（同一张表，V1.3 物理 p14）**

```
Recommended Charge/Discharge Current (A)*                        100
Maximum Continuous Charge/Discharge Current (A)*                 100
```

V1.0 物理 p11 同一位置：

```
Recommended Charge/Discharge Current (A) *                        80
Max. continuous Charge/Discharge Current (A) *                   100
```

**改动**：推荐电流记入 review 实例产品 `1134` 的 `_tv_b2b_figures.charge_discharge_current_recommend_a = 100`（V1.3 p14）。registry **不加**这个字段，理由见下。

说明两点，避免误读：

1. `max_charge_current_a = 100` / `max_discharge_current_a = 100` 承载的是 `Max. continuous`，在 V1.3 仍是 100，**值不变**，只把 citation 从 V1.0 p11 换到 V1.3 p14。registry 里从来没有“推荐电流”这一项，所以也没有 80 这个数需要删。
2. registry 的 `technical.specifications` 会经 `Materials::specs()` 直接渲染成产品页规格行，而 `Materials::key_label()` 对新 key 的兜底是 `str_replace('_',' ')` + 首字母大写 —— `charge_discharge_current_recommend_a` 会印成 **“Charge discharge current recommend a”** 这种读者不可用的标签。本票边界是不改插件代码，所以不往 registry 加这个字段；推荐电流作为产品级工程事实记在产品自己的 figures 里（`_tv_b2b_figures` 是 `SelectionFacts` 的正式载体，17 项已全部绑定 V1.3，见 §4.2）。
3. 旧手册的“推荐 80 A”约束因此失效。**产品文案里仍有 80 A**（见 §7.1），本轮按边界未改。

### 1.4 其余 14 个 spec 字段

值逐项与 V1.3 p14 核对，**全部不变**；只把 citation 从 V1.0 的 `:p11`（`chemistry` 为 `:p8`）重定向到 V1.3 的 `:p14`（`chemistry` 为 `:p13`）。

**页码偏移不是常数，必须逐项对页。** V1.3 在各处插入的内容长度不同，实测四个锚点得到四种偏移：

| 内容 | V1.0 物理页 / 印刷页 | V1.3 物理页 / 印刷页 | 物理页偏移 |
| --- | --- | --- | --- |
| `System Specifications` 表 | 11 / 8 | 14 / 8 | **+3** |
| 引言（`lithium iron phosphate battery`） | 8 / 5 | 13 / 7 | **+5** |
| Console / Contact 8 针 | 12 / 9 | 15 / 9 | **+3** |
| RJ45 端子表 + Power Terminals | 15 / 12 | 17 / 11 | **+2** |

印刷页号同样不遵守统一偏移（规格表两版都印 8，端子页 V1.0 印 12、V1.3 印 11）。因此本轮的每个 citation 都是逐页打开原件确认的，没有按某个固定偏移推算；citation 一律用**物理页**，与 registry 既有约定一致。

---

## 2. V1.3 规格表全文核对（物理 p14，逐行）

| 行 | V1.3 印刷值 | registry 现值 | 处置 |
| --- | --- | --- | --- |
| Nominal Voltage (VDC) | 48 | 48 | 不变 |
| Nominal Capacity (Wh) | 4800 | 4800 | 不变 |
| Usable Capacity (Wh) | 4560 | 4560 | 不变 |
| Depth of discharge (%) | 95 | 95 | 不变 |
| Dimensions (mm) | 442 (W) ×420 (D) ×161 (H) | 442*420*161 | 不变 |
| Weight (kg) | 39.7（US5000）/ 40（US5000-B） | 39.7 | 不变 |
| **Operation Voltage Range (VDC)** | **43.5~ 53.2** | 43.5 ~ 53.5 | **改** |
| **Recommended Charge/Discharge Current (A)** | **100** | （无此字段） | **新增** |
| Maximum Continuous Charge/Discharge Current (A) | 100 | 100 | 值不变，换页 |
| Peak Charge/Discharge Current (A) | 105~119@15 min / 120~200@15 s | （无此字段） | 见 §7.2 |
| Communication | RS485, CAN | RS485, CAN | 不变 |
| Configuration (max in 1 battery group) | 16 pcs | 16 | 不变 |
| Working Temperature (°C) | 0~50 Charge / −10~50 Discharge | 同 | 不变 |
| Shelf Temperature (°C) | −20~45 | （未建模） | 不变 |
| Short current/duration | <2000 A / 1 ms | （未建模） | 不变 |
| Cooling type | Natural | （未建模） | 不变 |
| Breaker | No（US5000）/ Yes（US5000-B） | （未建模） | 见 §7.3 |
| Protective class | I | （未建模） | 不变 |
| IP rating | IP20 | IP20 | 不变 |
| Humidity | 5%~95% RH no condensation | （未建模） | 不变 |
| Altitude (m) | ≤ 4,000 | （未建模） | 不变 |
| Certification | TÜV / CE / UL / UN38.3 | 同 | 不变 |
| Design life | 15+ (25 °C) | （未建模） | 不变 |
| Cycle Life | > 8,000 (25 °C) | （未建模） | 不变 |
| Reference standards | IEC62619, IEC63056, UL1973, UL9540A, IEC61000-6-2, IEC61000-6-3, UN38.3 | （未建模） | 不变 |

化学体系不在规格表里：V1.3 物理 p13（印刷 7）正文写 `US5000/US5000-B lithium iron phosphate battery` 与 `Cathode material made from LiFePO4`，据此把 `chemistry` 的 citation 放到 p13。

---

## 3. 改动清单（文件级）

### 3.1 仓库（本 PR）

`plugins/linker-commerce/data/material-registry.json` —— 单行 JSON，`1 file changed`，形态与既有取证提交 `3b30a4230`（BAT-C 数值）一致。

- `materials.mat_pylontech_us5000.technical.specifications`：**16 个字段，数量与 HEAD 相同**，全部重定向 citation/evidence_refs 到 V1.3；其中 `module_voltage_range_v` 改值。不新增字段（理由见 §1.3 第 2 点）。
- 新增 `materials.mat_pylontech_us5000._note_v13_2026_11_11`：记录版本口径、SHA、页码**非统一**偏移、为何不新增推荐电流字段，以及“US5000-B Breaker 未建模”。
- **未改** `revision` / `schema` / `source_manifest` / `rejected_inputs` / `unresolved_inputs`。依据是既有提交 `3b30a4230` 同样只改 materials 内容、`revision` 保持 `e291715b…` 不变（该值在 `3b30a4230^`、`3b30a4230`、`HEAD` 三个版本上完全相同）。仓库内没有任何代码读取或校验这个字段，它标的是源快照而非内容哈希。
- 285 个 material 中只有 `mat_pylontech_us5000` 发生变化（逐 material 比对 HEAD 确认）。

`docs/research/2026-11-10-manufacturer-docs/apply-us5000-v13.md` —— 本文件。

### 3.2 review 实例（数据库，不入仓库）

| 对象 | 改动 |
| --- | --- |
| 附件 `9557` | 新增 V1.3 手册 |
| 产品 `1134`（Pylontech US5000，EN，draft） | `_tv_b2b_figures` 重写为 17 项、全部引 V1.3；`_linker_documents` 4 行（3 数据表 + 1 manual）；`_linker_documents_managed = 1` |
| 产品 `6845`（DE twin，draft） | 未改。该行原本就没有 figures / documents，`canonical_id(6845) = 1134`，事实读 EN 源行 |

`_tv_b2b_figures` 存为 **JSON 字符串**而不是 PHP array：`Storefront\ProductView::figures()` 先 `(string)` 再 `json_decode`，存 array 会让产品页规格行整体消失。写入过程曾误存 array，已改回字符串并复验（见 §4.2 的过程记录）。

---

## 4. 读回证据

### 4.1 附件与文件

```
附件 ID        9557
URL            http://127.0.0.1:8889/wp-content/uploads/2026/11/pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf
mime           application/pdf
status         publish
path           ~/de-linker-local/review/wordpress/wp-content/uploads/2026/11/pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf
sha256         43088b8060b082f3427913bfc0de471cc425474d9de7c1329c4d5d4eceeb4062
bytes          3,920,843
```

与 `originals/` 原件逐字节相同。

### 4.2 产品 1134 的 figures

```
figures=17  bound=17  unbound=0
voltage=43.5 ~ 53.2   citation.page=14
recommend=100 A       citation.page=14
max_charge_current_a=100
temp value_de=0 °C ~50 °C Laden / -10 °C ~50 °C Entladen   （既有德语值保留）
```

`_linker_publication_figures` 17 条全部带
`blob_sha256 = 43088b8060b082f3427913bfc0de471cc425474d9de7c1329c4d5d4eceeb4062`
与 `document_id = doc-3af5712e…b566`。

这条检查是必须的：`Publication::figures_for()` 只在 citation 能绑定到该产品自己的当前文档时才放行，绑定失败的 figure 会**静默消失**，不报错。17/17 全部绑定，说明 V1.3 手册与 `_linker_documents` 的关联、以及 citation 的文件名，三者一致。

### 4.3 产品 1134 的文档列表

```
documents=4
  datasheet | pylontech-us-series.pdf                              | Pylontech US Series Datasheet (EN)
  datasheet | Pylontech_US2000C_US3000C_Datasheet_EN.pdf           | Pylontech US2000C+US3000C Datasheet EN
  datasheet | Pylontech_US3000C_Datasheet.pdf                       | Pylontech US3000C Datasheet
  manual    | pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf   | Pylontech US5000 Series Operation Manual V1.3 (5PMPA08-20078, 44 pp, 2026-01-12)
managed=1
```

`.pdf` 的字节存在性、HTTP 状态见 §5，不在此重复。

### 4.4 registry（仓库侧）

```
json valid     yes
materials      285（与 HEAD 相同，仅 mat_pylontech_us5000 变化）
spec 项        16（与 HEAD 相同，无增删）
值变更         1 项：module_voltage_range_v 43.5 ~ 53.5 -> 43.5 ~ 53.2
citation 重定向 16 项：15 项 p11->p14，chemistry p8->p13
revision/schema/source_manifest/rejected_inputs/unresolved_inputs  与 HEAD 相同
```

**实例侧无法读回 registry 改动**：review 实例的
`wp-content/plugins/linker-commerce` 是指向 `/tmp/p548-projection/plugins/linker-commerce`
的符号链接，该 worktree 属于另一条工作线，且带未提交改动
（`Cli/PublicationCommand.php`、`Products/Publication/EvidenceBindings.php`、
新测试 `RepairBindingsTest.php`）。我没有改动他人 worktree，因此实例加载的
registry 仍是旧值（`43.5 ~ 53.5`、p11）。这条要在该线合并后、部署时才生效。

---

## 5. 三个 410：根因不是文件失效

README §6.3 记的是「三个 Pylontech 数据表的托管字节已不可取」。本轮实测否定了这个前提。

**三个文件都在盘上，字节完好**：

| URL | 落盘 | sha256 | 页 |
| --- | --- | --- | --- |
| `/wp-content/uploads/2026/07/pylontech-us-series.pdf` | 1,163,080 B | `641a9794…4d55f` | 4 |
| `/wp-content/uploads/2026/07/Pylontech_US3000C_Datasheet.pdf` | 67,406 B | `261eb6ce…14df30` | 1 |
| `/wp-content/uploads/2026/07/Pylontech_US2000C_US3000C_Datasheet_EN.pdf` | 688,157 B | `aac14fca…a88316` | 8 |

410 来自 `Products\Publication\DocumentAccess::response()`：`null === $file` 时返回
`410 Content-Length: 0`，而 `$file` 为 `null` 是因为 `allows_document()` 找不到任何
**当前已发布**产品与这三个 URL 的有效关联。产品 `1132`/`1133`/`1134` 在 review 上
全是 `draft`（registry 侧 `linker_supply_relation: not_supplied`，
`_note_featured_scope_2026_10_01` 记录业主选定的 Pylontech 在售品只有 2003 L260-OMNI）。

**对照实验（同一台实例、同一时刻）**：

| URL | 关联产品状态 | HTTP |
| --- | --- | --- |
| `…/2026/10/pylontech-l260-omni-125kw-260kwh-datasheet-270d7e015db5.pdf` | 2003 `publish` | **200** `application/pdf` 1,610,345 B |
| `…/2026/07/pylontech-us-series.pdf` | 1134 `draft` | **410** `text/html` 0 B |
| `…/2026/07/Pylontech_US3000C_Datasheet.pdf` | 1133 `draft` | **410** |
| `…/2026/07/Pylontech_US2000C_US3000C_Datasheet_EN.pdf` | 1132 `draft` | **410** |
| `…/2026/11/pylontech_US5000_User-Manual_V1.3_5PMPA08-20078.pdf`（本轮新增） | 1134 `draft` | **410** |

新增的 V1.3 手册同样 410，这是决定性证据：一份刚落盘、SHA 正确、已挂到产品的文件也拿不到 200，说明 410 与文件、与文档挂载都无关，只与**产品发布状态**有关。新挂的 manual 行在 `_linker_documents` 里能读到，但对外仍是 410。

**这不是缺陷，是 609 规则的正常执行**（`docs/specs/609-product-publication.md`：下架产品撤权不依赖异步任务；原 URL、别名与已缓存引用都在范围内）。退役产品的资料不该对客户可下载，410 正是要求的行为。

**因此「修复 410」的正确形态不是补文件，而是产品发布决定**：三款 US 系列是否重新上架。这超出「只动产品数据与托管文档」的边界（改变上架状态会同时影响选型候选、兼容声明、知识检索与报价链），按纪律不自行决定，交主控裁定。

同一逻辑也解释了为什么 `engineering-feed` 里查不到 1134：feed 只含已发布产品（85 件），1134/1133/1132 均不在其中，2003 在。**「feed 反映新值」这一验收项对 draft 产品在定义上不成立**，只能在产品恢复发布后复核。

---

## 6. 数据表替换：被原件自身的印刷错误阻断

README §8 第 3 条建议「重新托管当前官方数据表（`EN-SD-*` 系列在 Product Portfolio 分类）」。本轮枚举了官方 `downloadTypeId=134`（Product Portfolio，34 件）全部分类，与 US5000 对应的现行件是：

```
title  US 5000 Spec
path   /profile/upload/2026/06/23/US 5000 Spec_1782186290116.pdf
```

实际下载（HTTP 200，`application/pdf`，1,749,999 B，2 页，PDF 标题 `US 5000 spec（7.31印刷）`，CreationDate `2025-07-31`，末页印 `EN-SD-250424`）。**它不能作为事实源**，第 2 页表格有三处明确印刷错误：

| 行 | 印出的值 | 同一厂商其他原件 | 判定 |
| --- | --- | --- | --- |
| Nominal Voltage (VDC) | **8** | 48（V1.0 手册 p11、V1.3 手册 p14、2021 数据表、2020 数据表） | 截断，应为 48 |
| Single String Quantity (pcs) | **20** | 16（V1.0 p11、V1.3 p14、2021 数据表、2020 数据表） | 与全部其他件冲突 |
| Working Temperature (°C) Charge | **−10~55** | 0~50（V1.0 p11、V1.3 p14） | 与手册冲突 |

已用 `pdftoppm` 渲染第 2 页并逐字读图确认，不是 `pdftotext` 抽取错误：图上是 `8`、`20`、`-10~55`。同页另有 `Cycle life >6,000`（手册 V1.3 为 `>8,000`）与 `Nominal Capacity` 标为 `Battery Module Capacity`，与手册口径不同代。

按「不天然相信现有代码与文档中的数字」与「产品事实冲突时以我们托管的数据手册为准」，这份数据表不能替换现有托管件：挂上去等于把 8 V / 20 pcs / −10~55 三条错值放进客户可见的资料库。

现有托管件 `pylontech-us-series.pdf` 的真实身份也顺便查清了：它是 **2021 年 4 页宣传册**，末页印 `Pylontech datesheet-PY21LVUSB-12-1`，PDF CreationDate `2021-12-10`，规格表列的型号是 **US2000C / US3000C / US5000-B**（不是 US5000），推荐电流 80 A、最大连续 100 A —— 与 V1.0 手册同代。所以：

- 它作为 US5000 的 datasheet 行，**型号对不上**（写的是 US5000-B），且规格是 V1.0 口径（80 A / 53.5 V 上界隐含在 Discharge 行）。
- 但它是我们目前唯一有 US 系列完整参数表的托管件，且**没有印刷错误**。

结论：不替换，也不删除，把冲突如实登记。数据表替换需要厂商出更正版，或改由手册承担 datasheet 角色（本轮的 `_linker_documents` 已把 V1.3 手册以 `type: manual` 挂上，datasheet 行保持原样等裁定）。

---

## 7. 发现但按边界未改的问题

### 7.1 产品文案仍写「80 A 推荐电流」（客户可见，需改）

产品 `1134` 的 `description_media.hairlines[0]` 与德语对应字段仍写旧值：

```
EN  Delivers 80 A recommended continuous current (approx. 3.8 kW) and up to 100 A max continuous current (4.8 kW).
DE  Liefert 80 A empfohlenen Dauerstrom (ca. 3,8 kW) und bis zu 100 A maximalen Dauerstrom (4,8 kW).
```

出现在 `_tv_legacy_acf_json`、`_linker_de_acf_json`、`_linker_de_source_acf_json` 三处。

按 V1.3，推荐电流已是 100 A = 最大连续 100 A，这句话的“80 A 推荐 / 100 A 最大”对比结构整体失效。同页其他文案（`short_intro`、`stats_claim`、`p7_claims`）写的是 100 A 连续，与新手册一致，不用动。

未改原因：这是营销正文，AGENTS.md §0.2 要求「营销正文的主动文案改写保持原裁定」，且英德必须同步交付、走文案对抗评审。这份文案改写应由文案线统一处理，不在“产品数据”范围内自行改。

### 7.2 Peak 电流口径变了，但 registry 没有对等字段

V1.0 `101-120@15min / 121~200@15sec` → V1.3 `105~119@15min / 120~200@15sec`。registry 里 US5000 没有 peak 字段（全局有 `peak_discharge_a` 这个 key，但 US5000 未建）。本轮不加：任务只要求改“推荐电流、电压窗”，加 peak 会引入没有消费者、没有验收的新事实。登记待规格线决定是否建模。

### 7.3 US5000-B 的 Breaker 段是 V1.3 新增的可施工信息，未建模

V1.3 新增独立 Breaker 端子说明（type C，60 VDC，125 A，Icu 10 kA，UL1077 / IEC60947-2）；V1.0 只在规格表写 `Breaker: Yes/No`。这属于安装/施工事实，工作台若要消费需单独立字段，本轮不扩。

### 7.4 US3000C 是否有同类跨版本缺口：**没有**

官方目录 `downloadTypeId=128`（Operation Manual，57 件）全量检索 `US3000C|US2000C|US5000`，只有四份 US 系列手册：

```
RESS-Installation Manual-US5000 US5000-B 5PMPA08-00219_V1.0      ← 我们引用的（已被 V1.3 取代，且不在该目录里）
RESS-Installation Manual-US3000C 5PMPA08-00222_V1.0              ← 我们引用的，即当前最新
RESS-Installation Manual- US3000C UL 5PMPA08-00221_V1.0
RESS-Installation Manual-US2000C-5PMPA08-00220-V1.0              ← 我们引用的，即当前最新
```

US3000C 与 US2000C 引用的都是官方目录里的**最新版**，不存在 US5000 这种跨两代的缺口。注意一个反常点：US5000 V1.3 **不在** Operation Manual 分类里，只能经 `/pdf?id=44` 路由取得（README §6.1 已记录该 id 空间是混合索引、无法按号段推断），所以「按目录枚举」不足以发现这个缺口——这是本次缺口长期未被察觉的机制原因。

### 7.5 US3000C 电流字段语义问题（README §6.2）仍未解决

`max_charge_current_a` / `max_discharge_current_a = 37` 对 US3000C 是「推荐稳态」，对 US5000 是「最大连续」，两款语义不一致。本轮**没有**改动 US3000C：这是字段语义统一问题，需要规格线先定口径（README §8 第 2 条已列为待决），且本轮 scope 是 US5000。登记不扩。

---

## 8. 资源报告

- **review 实例**：沿用已在运行的 `review`（8889），未新建实例，未新建浏览器窗口。
- **临时文件**：`/tmp/b-us5000/`（官方数据表与渲染图，用于 §6 的印刷错误核对）在核对完成后已删除；`/tmp/b-us5000-wt/` 是本 PR 的 worktree，交付后按主控安排回收。
- **Apify**：本轮未使用（取证已在 README 完成，本轮只做原件复核与官方目录直连）。
- **凭据**：未接触任何令牌；未写入仓库。
- **磁盘**：仓库侧净增 1 个 JSON 字段批次（registry 字节 −47）与本记录文件；实例侧新增 1 份 PDF（3.9 MB）。

---

## 9. 环境说明：读回期间实例被并发占用

本轮执行期间，review 实例（8889）的插件目录是指向 `/tmp/p548-projection/plugins/linker-commerce`
的符号链接，该 worktree 属于另一条工作线并在本时段内持续被编辑：

| 文件 | 最后修改 |
| --- | --- |
| `includes/Cli/PublicationCommand.php` | 06:28 |
| `includes/Products/Publication/CompatibilityClaims.php` | 06:30 |
| `includes/Products/Publication/EvidenceBindings.php` | 06:21 |
| `tests/php/Unit/Products/CompatibilityTest.php` | 06:30 |
| `tests/php/Unit/Products/Publication/RepairBindingsTest.php`（新增） | 06:28 |

约 06:30 起 `wp eval` 开始返回 “critical error”，而站点本体仍健康
（`/` 301、`/wp-json/linker/v1/engineering-feed` 200）；三个被改文件的 `php -l` 均无语法错误，
因此判定为他人进行中的运行期改动所致，与本轮写入无关。

本报告 §4 的全部读回证据均在 06:27 之前取得，早于该故障，仍然有效。
为不干扰另一条工作线，本轮未修改 `/tmp/p548-projection` 中的任何文件，
也未在其上重跑读回。

后续若要复核 §4，需等该线合并、实例恢复后重跑；registry 的实例侧读回同样受此限制（§4.4）。
