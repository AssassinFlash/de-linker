# BAT-C 用户手册上架与定量规格行（609 流程）

日期：2026-11-11。分支 `batc-publication`（worktree `/tmp/batc-publication`，自 `origin/main` `c05ff12bf`）。
依据：`docs/specs/609-product-publication.md`、`docs/research/2026-11-04-vendor-originals.md` §2/§5.1。
未改引擎、模板、WindPress；未新增产品、未改营销正文。

## 0. 结论表

| # | 项 | 结果 |
| --- | --- | --- |
| 1 | 手册托管与版本 | **已存在**：附件 8508，review 与生产 uploads 同字节（5,440,295 B，sha256 `c29cbf25…7fcb7`），与官方直链一致 |
| 2 | 产品关联 | 生产 1954/1955 均已关联；**review 快照缺 1955 那一条**，本批补齐并对齐生产 |
| 3 | 定量规格行 | 33 → **34** 项（新增 `certification`），澳规限定改为可见 `qualifier`，见 §3 |
| 4 | 澳规脚注口径 | 额定电流/功率带 EN/DE `qualifier`；最大值行不带限定，两者分列不混称 |
| 5 | 消费者读回 | 生产 manifest / engineering-feed / 产品页链接 / 文件 200 全部读回，见 §5 |
| 6 | HS3 针脚批 | **未做**，判断依据见 §6 |

## 1. 原件身份（复核，非转述）

```
文件    GW_BAT-C 61.4-112.6kWh_User Manual-EN.pdf（封面 V1.0 2026-10-10）
页数    87（pdfinfo）
字节    5,440,295
sha256  c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7
来源    https://en.goodwe.com/Api/downloadFile?id=4626&mid=60&type=2（HTTP 200）
```

三处字节一致：本次直下、review uploads、生产 uploads。

**研究报告一处事实更正。** `2026-11-04-vendor-originals.md` §2 规格表把认证行记为
`IEC 62040/N143(应为 N1438 手册原文)`。原件物理 p82（印刷 p81）印的是：

```
IEC62040/N140/EU 2023/1542/UN38.3
```

已用 `pdftoppm -r 150` 渲染该页逐字读图确认，不是 `pdftotext` 抽取问题。本批按原件写 `N140`，
并在测试里断言值中不含 `N143`，防止旧记录回流。

## 2. 609 流程逐步执行与读回

609 没有另立一套上架程序：授权源是 Woo 产品上的 `_linker_documents` 行，版本由
`DocumentFiles::id()`（规范化路径）与 `document_revision`（清单内容含 `blob_sha256`）派生，
读取时由 `Publication::allows_document()` 按当前关联重新校验。因此本批只做数据写入，不新增流程。

| 609 环节 | 本批动作 | 读回证据 |
| --- | --- | --- |
| 唯一维护入口（Woo 产品与资料） | review 实例 `update_post_meta(1955,'_linker_documents',…)` 追加手册行（与 `DocumentsMetaBox::save()` 同一写入口） | review `manifest`：`manual EN c29cbf257d51… pids [1954,1955] rev 245ea9711b` |
| 版本登记（同 URL 换内容即新版本） | 未换内容，`blob_sha256` 与官方一致 | manifest `document_revision=caa2e292a2c7`（生产）/`245ea9711b`（review 本地地址） |
| 资料与产品关联 | 1954 原有、1955 补齐 | 生产 manifest：两者 `product_ids` 均含 1954、1955 |
| 派生数据不授权 | 仅读取，未把 feed/索引当许可 | 见 §5 的 `allows_document` 与 410 语义 |
| 准备待办自动产生 | 关联变化后 `reconcile` 建待办 | `knowledge status=pending source=6327de50…`、`engineering status=ready` |
| 撤权立即生效 | 未撤权；本条不适用 | — |

### 2.1 review 快照与生产不一致

`wp post meta get 1955 _linker_documents` 在 review 上是 10 行（无 BAT-C 手册），生产是 11 行（有）。
生产产品页因此一直显示 BAT-C 手册，review 不显示。这是快照漂移，不是产品缺陷。
本批把 review 对齐到生产，两个实例此后同构。

写入前后像（回滚用）：

```
前  10 行，末行 = manual | EN | GW_ET-100kW_User-Manual-EN_V1.2.pdf
后  11 行，末行 = manual | EN | GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf
回滚 delete_post_meta 后按原 10 行数组回写即可；生产未写入，无需回滚
```

### 2.2 1955 上的 ET 手册为什么保留

1955 的 `_linker_documents` 另有一行 `GW_ET-100kW_User-Manual-EN_V1.2.pdf`（`type: manual`）。
它不是错挂：ET 手册 p100 §3.2.4「Battery Delivery Item (BAT Series 92.1-112.6kWh)」就是该柜体的
供货包件依据（`tools/migrate/548-batc-112-delivery.json` 的 source 全部指向它）。改动它的 `type`
会改变 `document_revision`，使已绑定的事实失效，因此本批不动。

## 3. registry 规格行

`plugins/linker-commerce/data/material-registry.json`，仅 `mat_goodwe_gw61_4_bat_ac_g10`、
`mat_goodwe_gw112_6_bat_ac_g10` 两份变化：每份 33 → 34 项。

| 字段 | 值（61.4 / 112.6） | 页码（物理页 = 印刷页 + 1） |
| --- | --- | --- |
| `system_usable_energy_kwh` | 60 / 110 | p80（印刷 79） |
| `system_operating_voltage_range_v` | 275.52 ~ 346.56 / 505.12 ~ 635.36 | p80 |
| `max_charge_current_a` / `max_discharge_current_a` | 180 / 220 | p81（印刷 80） |
| `rated_charge_discharge_current_a` *2 | 100 / 100 | p81 |
| `c_rate` *2 | 0.9C / 1.1C | p81 |
| `max_charge_discharge_power_kw` *2 | 55.2 / 67.5 · 101.3 / 123.9 | p81 |
| `rated_charge_discharge_power_kw` *2 | 30.7 / 56.3 | p81 |
| `cycle_life` *3 | ≥6000 @ 25±2 °C、0.5C、100% DOD、70% SOH | p81 |
| `round_trip_efficiency` *3 | 96% @ 100% DOD、0.2C、25±2 °C | p81 |
| `storage_temp_c` / `relative_humidity_pct` / `max_operating_altitude_m` | 见 registry | p82（印刷 81） |
| **`certification`（本批新增）** | IEC62619/IEC63056/IEC60730/IEC62477/VDE2510/ISO13849; IEC62040/N140/EU 2023/1542/UN38.3 | p82 |

### 3.1 澳规脚注口径（报告 §2 明确要求）

原件物理 p83（印刷 p82）Note 2 原文：

> Actual Dis-/Charge Current and power derating will occur related to Cell Temperature and SOC. …
> **Rated Charge/Disharge Current & Rated Charge/Discharge power only for Australia.**

处理：额定电流与额定功率两行各带 `qualifier{en,de}`，写明「仅澳大利亚、随电芯温度与 SOC 降额、
最大值另行分列」；最大值行（180/220 A、55.2/67.5 kW）**不带**该限定。两者分列，不混称。

原先这两行的限定只写在 `note` 字段里，而 `note` 不被任何渲染路径读取——等于限定对客户不存在。
本批改为 `qualifier`，并扩展 `Materials::spec_text()`：原来只对 `temp` 一个 key 拼 qualifier，
现在按显式白名单 `QUALIFIED_ROWS`（`temp` + 本批三行）生效。

**为什么是白名单而不是全 key。** registry 里共 38 行带 `qualifier`、覆盖 16 个 key。若改成"任意 key
都拼"，会同时改动**另外 24 个产品、36 行**的客户可见规格文案（最长 +228 字符），这些限定从未按
页面评审过。白名单把本批的影响面限制在 BAT-C 三行，`temp` 保持原行为；扩表需要单独评审。

## 4. 改动清单

| 文件 | 改动 |
| --- | --- |
| `plugins/linker-commerce/data/material-registry.json` | 两行额定值改挂 `qualifier`（EN/DE）、新增 `certification`（含 note 5 的“未列全”限定） |
| `plugins/linker-commerce/includes/Products/Materials.php` | `spec_text()` 的 qualifier 从仅 `temp` 改为显式白名单 `QUALIFIED_ROWS`（`temp` + 本批三行） |
| `plugins/linker-commerce/tests/php/Unit/Products/MaterialsQualifierTest.php` | 新增 4 项：限定必须出现、不得变成 label、白名单外的 key 不变、已发布数据必须带页码与限定 |

`revision` / `schema` / `source_manifest` / `rejected_inputs` / `unresolved_inputs` 未改，与既有
取证提交 `3b30a4230`、`df5bb5940` 一致（该字段标源快照而非内容哈希，仓库内无读取方）。

## 5. 消费者读回（生产）

| 层 | 命令 | 结果 |
| --- | --- | --- |
| Woo 关联 | `wp post meta get 1955 _linker_documents` | 11 行，含 BAT-C 手册 |
| 授权清单 | `wp linker-commerce publication manifest` | 1954/1955 的 `documents` 均含该手册，`blob_sha256=c29cbf257d51…`，`ready {knowledge:true, engineering:true}` |
| 工程 feed | `GET /wp-json/linker/v1/engineering-feed` | 1954 rev `eb0d56104ffe` docs 9；1955 rev `51a6177f2cb5` docs 11；两者手册行 SHA 一致 |
| 产品页（EN） | `GET /product/goodwe-gw112-6-bat-ac-g10/` | 出现 `…/GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf` 链接 |
| 产品页（DE） | `GET /de/produkt/goodwe-gw112-6-bat-ac-g10/` | 同上 |
| 原文件下载 | `GET /wp-content/uploads/2026/10/GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf` | 200，5,440,295 B |

review 实例同类读回：manifest 显示 `pids [1954,1955]`；写入后 `ready` 由 `{true,true}` 变
`{false,false}`（source_revision 变了、旧准备代次失效，这是 609 的预期行为）。执行
`just serve review` 后引擎重拉 feed，`/resource/version?ready=1` 读回 `source_revision=6327de50…`、
`prepared_products=88`（含 1954 `0ad49f21…`、1955 `4f3919a0…`），manifest 恢复 `engineering:true`。

**knowledge 侧未追平**：Genie 仍加载索引 `4a3abcd6…`，服务端按规则拒绝确认
（`genie_source_mismatch`）。重建是一次 143 文档 / 19,193 段的 Docling 全库编译（上代实测
parse 合计 3,594 s），且本机有自动 worker（`com.linker.knowledge-publication`）负责，本批不手搓
全库重建，如实登记为待追平项。

## 6. HS3 针脚批：不做

报告 §5.4 把 HS3 Table 5.1（p78）+ RJ45 针脚（p81）列为可选增量。判断：**不在本批做**。

1. **风险不同源**：BAT-C 是“同一份已核 SHA 的公开手册挂到两款在售产品”，HS3 是往 `mat_saj_hs3_*`
   增加针脚级事实，需要逐端子对照 125 页手册的表格结构与跨行含义，评审面比本批大三倍。
2. **没有当前消费者**：针脚级端子事实目前没有工具读（`equipment_assessment` 读的是功率/电压类
   figure），加进去只会是无人使用的数据，违反“不引入没有消费者的新事实”（615 的既有裁定）。
3. **不得与 BAT-C 混批**：两批的依据、页码体系、复核深度完全不同，合并会让 BAT-C 这批的读回证据
   被 HS3 的未验证部分污染。

留给下一次 SAJ 规格批次，按报告 §5.4 原文执行。

## 7. 门禁

```
phpunit（worktree，全量）    2315 tests, 8919 assertions, 543 skipped → OK
phpunit（新测试）            MaterialsQualifierTest 4 tests / 29 assertions → OK
phpcs                       clean（0 error 0 warning）
phpstan (level 8)           No errors
commerce-terms              hits=28 baselined=28 findings=0 → clean
german-copy / i18n-coverage  clean（gap=0）
internal-home-urls          clean
```

## 8. 资源

- 新建：worktree `/tmp/batc-publication`（交付后按主控安排回收）；`/tmp/batc-dl`（原件与渲染页，
  核对完成后删除）；worktree 内 `composer install` vendor 132 MB（可重建）。
- 复用：review 实例（8889/8890/8891）既有进程，未新建实例、未新建浏览器窗口。
- 未接触生产写入；未发任何邮件；未使用 Apify。
