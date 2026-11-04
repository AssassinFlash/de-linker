# Datasheet 表格零产品关联：根因、假绿门禁与波及面

日期：2026-11-04
范围：只读排查。生产（VPS `linker-services`）仅以 `sqlite3` 只读方式查询 `/opt/linker-genie/index/current/index.sqlite`；本地用与生产**字节一致**的构建产物（`~/de-linker-data/index/builds/20261103T203607Z-950501000/`，`index.sqlite` sha256 `2c0d2759acff6e1ceb57efcda361d71c2ed09185092ed0b3316ee8ae1dcc0442`，与生产 manifest 记录相同）重放编译。未修改生产、未部署、未合并。

关联工单：GitHub #900（Part of 地图 #899）

---

## 1. 结论摘要

1. **`chunk_products` 零关联不是写库丢的，是编译期就没有产出。** 生产 `chunk_products` 行数 5224，恰好等于 manifest 的 `permission_coverage.proven_chunks`；索引只写入通过 scope 编译的 chunk。裸表 = `compile_scopes` 没给它们任何 `ScopeProof`。
2. **六份 datasheet 的失败点分成四类，但共享同一个结构性缺口：整套表格授权只覆盖「多型号宽表 + 表头就是型号」这一种形态。**
   - **单型号窄表（3 份）** `c95aef48b1ea` / `7e445df02017` / `143fb6026284`：表是「属性 | 值」两列，`table_projection` 要求表头列是型号（`width >= 2` 且第 0 行第 1 列有型号标签），`_table_columns` 要求**至少 2 个型号**——两条路都不接受「一个型号的两列表」。GW ESA 两份还额外被表前 tail 里的未上架代次 `G11` 打成 conflict。
   - **表头几何错位（1 份）** `e00f9645d187`（SAJ HS3 DE）：表头确实是 6 列型号轴，但第 6 个表头单元格的 Docling bbox 落在自身墨迹**下方 4.6 pt**，严格包含判定拒绝该 span，`model_axis` 返回 `None`。
   - **德语组件行未隔离（1 份）** `2a76fb0815a2`（BAT-C DS DE）：型号轴在表前文本里识别成功，但表体内德语 `Batteriepack-Typ / Modell` 行被判 `blocked`，而 `pack_model_row()` 只认英文 `Pack Type / model` 且要求整 chunk 单行，整表被判 conflict。同系列 EN 版因分块切点不同而成功。
   - **解析结构损坏（1 份）** `4adebe72eb25`（ET 80–100 kW DE）：Docling 把 4 列参数表解析成 3 列并把多行文本并进标签列，任何下游规则都无法恢复型号列。
3. **假绿是真的，且机制明确。** `services/genie/index/store.py:283-324` 的准备判定是**按 (product_id, document_id) 对**算的：该产品在该文档下只要有**任意一段**通过 `authorize_chunk` 的 passage，就计入 `prepared`。整页参数表零关联不影响结论，因为 p.1 的营销文本块已经满足了这一对。
4. **波及面（生产实测）：**4708 个表格 chunk 中只有 405 个（8.6%）带产品关联；datasheet 60%（289/479）、manual 2%（82/3353）、certificate 5%（30/587）、compatibility 0%（0/266）。按「参数表」口径（≥4 行、≥2 列、有单位或工程属性词）筛出 969 个表格组，其中 **898 个无关联**，只有 71 个有关联。
5. **另一个量级更大的系统性缺陷：**174 个「型号轴已证明成立（`model_axis` 成功）但生产无关联」的表格组中，**146 个**是被 `_author_contexts` 的边界引用否决的，而那条边界引用**不含任何当前产品型号**（例如 `ESA Series 125kW/261kWh`）。`author_scope_allows` 要求每个边界的 product 集合包含目标产品，空集合直接判 False。

---

## 2. 生产基线（epoch 86 实测）

```
documents 143（datasheet 47 / certificate 44 / manual 39 / other 9 / compatibility 4）
chunks    19109（table 4708 / text 14401）
chunk_products 5224 = manifest.permission_coverage.proven_chunks
meta: preparation_complete=true  materialization_complete=true  unprepared_documents=[]
      activation_epoch=86  recipe_revision=93281f75…dd982c  serving_revision=fe2d8b8e…091ff8
```

当前工作树的 `recipe_revision()` 与生产记录**完全相同**（`93281f75e0f3ba59e3054cbd5800c377a50e6eac7f784a9774f3ed346cdd982c`），所以第 4 节的复现基线就是生产当时运行的编译代码。

`chunk_scopes` 的 basis 分布（生产实测，共 5224）：

| basis | 条数 | | basis | 条数 |
| --- | ---: | --- | --- | ---: |
| family_manual | 3307 | | document_model | 119 |
| warranty_terms | 305 | | common_terms | 114 |
| table_projection | 258 | | woo_document | 100 |
| passage | 250 | | warranty_procedure | 74 |
| section_model | 248 | | compatibility_inverter | 30 |
| certificate_subject | 173 | | table_columns | 25 |
| reviewed_manual | 143 | | 其余 7 类合计 | 84 |

注意 `table_columns` 只有 25 条。这是「表前文本声明型号轴」通道的全部产出量——它设计上覆盖 datasheet 的主形态，实际几乎没生效。

---

## 3. 关联路径与判定顺序（代码地图）

一个表格 chunk 想拿到 `product_id`，只有两条入口，且顺序固定：

**入口 A：`table_projection`（表头即型号轴）** — `services/genie/index/table_compiler.py:1050-1208`

```
groups[(doc_sha256, source_table)] = 同表的所有分片
  → read_cells(source_cells)                    # table_projection.py:476
  → model_axis(cells)                           # table_projection.py:903 → _model_axis_data:826
       ├─ 有 external_axis → _external_axis_data:617
       └─ 否则逐列检查第 0 行：column_header / col 对齐 / _axis_labels 数量 == 列宽 / model_spans 与 label 集合完全相等
  → axis 为 None → continue（该表零投影，无任何日志）
  → 逐个 axis 列取 current product → _scope(source, sha, pid)  # table_compiler.py:272
  → 若有 contexts[id] → 过滤边界后 _constrain → author_scope_allows  # :1115-1146
  → safe_rows 逐行过滤 → 产出新 chunk id "<sha12>-p<page>-model-<digest>"
```

**入口 B：`table_columns`（表前 `Technical Data` 声明）** — `services/genie/index/publication.py:127-275`

```
scopes 不是 table_projection 时，scope_proofs 查 columns:
  preceding_text 全部为同 section 的 text 且严格在前
  → 取最后一个 "Technical Data|Technische Daten" 之后的 tail
  → tail 里的型号标签数 >= 2、全为 published、无 unknown code
  → 表体每行宽度 == 标签数 + 1
  → 行内不再出现与列轴矛盾的型号
  → basis="table_columns"，table_header() 再复原一次表头  (publication_scope.py:508)
```

**关键事实：两条入口都不覆盖「单型号表格」。**

- `_model_axis_data` 要求 `width >= 2`（`table_projection.py:836`），且第 0 行第 1..n 列必须是型号标签；
- `_table_columns` 显式要求 `len(labels) >= 2`（`publication.py:211`），不足 2 个直接 `continue`（不是 conflict，是静默跳过）。

一个「属性 | 值」两列表，永远拿不到型号轴。这正是 GW ESA EN/DE 与 SEC3000C 的处境。

---

## 4. 六份 datasheet 逐份根因（真实数据复现）

复现方法见 §8。以下「失败点」均来自对生产同源 corpus 的 `compile_scopes` 重放，不是推断。

### 4.1 `c95aef48b1ea` GW ESA 261kWh EN — 单型号两列表 + 尾行混入未上架型号

```
p2 docling:p2:#/tables/0   69 行 × 2 列
r0: 'Battery Data' | 'LFP (LiFePO4)'         ← 表头无型号
表前文本: '…auto-dehumidification Technical Data GW125/261-ESA-LCN-G10' / 'GW125/261-ESA-LCN-G11'
```

- 入口 A 失败：表头第 1 列 `LFP (LiFePO4)` 的 `_axis_labels()` 返回 `[]`，`len(labels)=0 != width=1` → `model_axis=None`。
- 入口 B 失败：tail 解析出 2 个标签 `gw125/261-esa-lcn-g10`（Woo 有，pid 6321）与 `gw125/261-esa-lcn-g11`（**Woo 无此产品**）→ `unknown_models(tail, …)` 为真 → `_table_columns` 判 conflict。分类结果：`tail_unknown_code`。
- 即使把 G11 从 tail 里去掉也不会成功：只剩 1 个标签 → 撞上 `publication.py:211` 的 `len(labels) < 2` → 静默跳过。
- **双重缺陷**：① 单型号表无路径；② 原厂 datasheet 提到一个我们没有上架的代次（G10/G11 同页并列），直接把整表打成 conflict。

### 4.2 `7e445df02017` GW ESA 261kWh DE — 与 4.1 同构

```
p2 docling:p2:#/tables/0   67 行 × 2 列，header_rows=0（r0 连 column_header 都没标）
r0: 'Batterie-Daten' | 空
表前文本: '…Technische Daten GW125/261-ESA-LCN-G10' / 'GW125/261-ESA-LCN-G11'
```

失败点与 4.1 完全一致（分类同为 `tail_unknown_code`）。德语版还多一层：`header_rows=0`，说明 Docling 没把这行识别成表头，`column_header` 全 False。

### 4.3 `2a76fb0815a2` BAT-C DS DE V1.1 — 德语 pack 行没被隔离，整表被判 conflict

```
p2 docling:p2:#/tables/0   19 行 × 3 列
r0: 'Batteriesystem' | 'Batteriesystem' | 'Batteriesystem'
表前文本: '…Technische Daten GW61.4-BAT-AC-G10' / 'GW112.6-BAT-AC-G10'   ← 2 个型号，正确
表体: 'Batteriepack-Typ / Modell | Batteriepack-Typ / Modell | GW10.2-PACK-ACI-G10'
```

- 入口 B 的型号轴识别**成功**（2 个标签，均 published，表体 3 列 = 2+1）。
- 卡在 `publication.py:166-186`：表体内 `GW10.2-PACK-ACI-G10` 不是 Woo 产品 → 该分片 `blocked=True` → 进入 `excluded`。隔离检查要求 `pack_model_row(part.text)` 为真，而它要求**整个 chunk 只有一行**且首格匹配 `Pack Type / model`：
  - `services/genie/src/linker_genie/source_roles.py:48-66` 的正则只认英文 `Pack (Type / model|model(/type)?)`；
  - 德语 `Batteriepack-Typ / Modell` 不匹配；
  - 该表 DE 版只有 2 个分片，pack 行**混在 17 行的大分片里**，`len(lines) != 1`。
- 结果：整表 conflict，分类 `excluded_fragment_not_pack_row`。

**EN 版对照（决定性证据）**：`845e51ffb280`（同系列 EN V1.1）有 3 个分片，chunker 在 `chunking.py:225` 用 `pack_model_row(line)` 把这行**单独切成一个 chunk**（`| Pack Type / model | | GW10.2-PACK-ACI-G10 |`），于是 `excluded` 片段满足隔离条件，整表通过。同一份 PDF 的英德两版，因为分块切点不同，一侧成功一侧失败。

### 4.4 `4adebe72eb25` ET 80–100 kW DE — Docling 把 4 列解析成 3 列

```
p2 docling:p2:#/tables/0   65 行 × 3 列，header_rows=0
r0: 'Batterieeingangsdaten' | 空 | 空
表前文本: '…Technische Daten GW80K-ET-G10' / 'GW99.99K-ET-G10' / 'GW100K-ET-G10'   ← 3 个型号
表体: 'Nennspannung (V) 600' | 空 | 空      ← 属性与值被并进同一格
      'Max. Dauerladestrom (A) 100 × 2 110 × 2 …' | 'Max.' | 'Max.'
```

- 型号轴识别成功（3 个标签）。
- 卡在宽度：轴 3 个标签 → 需要 4 列（1 标签列 + 3 型号列），表体只有 3 列 → `body_width_mismatch`。
- **这不是授权规则的问题，是解析层的问题**：Docling 把 4 列表压成 3 列，并把多个属性/值并进标签格。任何下游规则都无法从一个结构错误的网格里恢复型号列。
- 对照：EN 版 `4f7178042e8f`（ET 75–100 kW）表体 5 列 / 4 标签，`table_columns` 通过，生产确实有 6 个 `table_columns` 关联。同系列、不同解析结果。

### 4.5 `e00f9645d187` SAJ HS3 5–12K DE — 第 6 个表头单元格的 bbox 不含自身墨迹

```
p2 docling:p2:#/tables/0   29 行 × 6 列，column_header 全部为 True
r0 c1..c5: HS3-5-12K-T2-W/G-P1 … P5
model_spans: c1=1  c2=1  c3=1  c4=1  c5=0     ← 只有 P5 缺
```

逐 token 实测（PDF 文字层，TOPLEFT 坐标）：

| 表头格 | Docling bbox top | 墨迹 y 范围 | 墨迹中心 | 中心是否在框内 |
| --- | ---: | --- | ---: | --- |
| c1 | 27.7 | 27.4 – 32.0 | 29.7 | 是 |
| c2 | 27.7 | 27.4 – 32.0 | 29.7 | 是 |
| c3 | 27.7 | 27.4 – 32.0 | 29.7 | 是 |
| c4 | 27.7 | 27.4 – 32.0 | 29.7 | 是 |
| **c5** | **32.6** | 27.4 – 32.0 | 29.7 | **否** |

- `enrich_model_axes`（`services/genie/index/extract.py:1906-1956`）要求 span 中心落在 cell bbox 内才接受 `model_spans`（接受域判定在 `:1918-1924`）；c5 的格框整体落在墨迹**下方**（32.6 > 32.0，连相交都没有），故被拒。
- `_model_axis_data` 随后要求 `len(spans) == len(labels)`（`table_projection.py:860-869`），5≠0 → 整表 `model_axis=None`。
- 现有容差救不了：`_header_cell_wrap` / `_span_stays_in_cell` 的 0.5 pt 亚字形容差（`table_projection.py:252-279`、`extract.py:1751-1770`）针对的是框比墨迹**小一丁点**，这里是 4.6 pt 的完全错位。
- 该页是 1190.55 pt 宽的双页拼版（`page.get_bbox()=(595.276,0,1190.55,807.87)`），文字层里同时存在裁切外那页的同名型号（`box[0]≈356-538`，`inside_crop=False`）与裁切内的型号（`box[0]≈763-1149`）。裁切外那些被 `_pdf_model_spans` 的边界检查正确丢弃，**不是**本处失败原因。
- **EN 版对照**：`b4a653fd2c0b`（HS3 EN）表头写 `HS3-5K-T2-W/G-PX`，5 个表头格全部取到 span，生产产出 5 个 `table_projection` 关联（1185/1186/1187/2198/2199）。同一份 PDF 的两个语种版本，一侧成功一侧失败。

### 4.6 `143fb6026284` SEC3000C EN — 单产品、单型号、两列表

```
p1 docling:p1:#/tables/0   28 行 × 2 列
r0: 'Communication' | 空
表前: 'GoodWe Smart Energy Controller SEC3000C enables centralized monitoring…'
表内出现 'GM330'（另一产品），'Datalogger | EzLogger3000C × 1'
```

- 产品集合只有 1 个（`{2409}`，模型 `SEC3000C`）。
- 入口 A：`width=2` 但第 1 列是 `Communication` → `labels=0` → `model_axis=None`。
- 入口 B：表前文本里的 `SEC3000C` 不在 `Technical Data` 之后的 tail 里（这份 datasheet 没有 `Technical Data` 标题行）→ 无 columns；且只有 1 个型号，即使有 tail 也撞 `len(labels) < 2`。
- 剩余匹配靠文本块（`passage` / `section`），表本身无关联。分类 `single_product_no_axis`。
- 另有次要因素：表内 `GM330` 让该分片 `blocked=True`（`GM330` 是另一产品、不在本文档关联里）。

---

## 5. 更广的同类缺陷（已量化）

除六份目标文档，同一批规则在其它文档上产生五种可复现的失败形态。

### 5.1 表头型号轴已证明成立，却被「不含型号的章节标题」否决 —— 146 个表格组

生产里有 174 个表格组 `model_axis` 成功但无关联。逐个归因：

| 归因 | 组数 |
| --- | ---: |
| 边界引用**不含任何当前型号** | **146** |
| 轴上的型号不在 Woo（型号写法差异） | 20 |
| 边界引用指向另一个产品 | 5 |
| 无 author context（另有原因，见 5.3） | 3 |

典型证据（`0adfb3d5e6df` GW ESA 261kWh User Manual EN V1.6，p94）：

```
axis = ['GW125/261-ESA-LCN-G10', 'GW125/261-ESA-LCN-G11']   ← 物理轴成立
contexts[p94 表] 的边界:
  heading      'ESA Series 125kW/261kWh'                      subj={}      ← 空
  heading      '· GW125/261-ESA-LCN-G10 · GW125/261-ESA-LCN-G11'  subj={6321}
  heading      'Parallel Connection via SEC3000C ■'           subj={2409}
  declaration  'Only the GW125/261-ESA-LCN-G10 requires installation of the MSD switch'  subj={6321}
```

- `compile_scopes:1131-1142` 会把 `Parallel Connection via SEC3000C ■` 过滤掉（`_quote_shares_axis_family` 返回 False），但**保留** `ESA Series 125kW/261kWh`（它不含型号 → `if not subjects: return True`，被当作必须遵守的收窄）。
- 随后 `author_scope_allows`（`publication_scope.py:70-98`）要求 `wanted ⊆ subjects`，而该边界的 subjects 为空 → 返回 False → 整表该列 `continue`。
- `_author_contexts` 的 docstring 明说这是 deliberate fail-closed（"deliberately fails closed across that boundary instead of guessing a sibling hierarchy"）。问题是它把一个**带容量数字的章节标题**（`125kW/261kWh`）当成了型号收窄声明。`rating_cover` 豁免只在 `page == 1` 且标题含 `All-in-One` 时生效（`table_compiler.py:227-243`），p94 的表完全不在保护范围内。

同一模式在 `29bb252c549a`（ESA 5–30 kW DE 手册）p311 上是 `'WiFi/LAN Kit-20 ·'`。

### 5.2 型号写法与 Woo 不一致 —— 20 个表格组

轴标签存在但不在 Woo：`HS3-12K-T2-W-P`（Woo 是 `HS3-12K-T2-W/G-PX`）、`CH2-29.9K-T4/CH2-30K-T4/CH2-50K-T6`（Woo 是 `CHS2-*`）、`B2-5.0-HV5` 系列、`GW3K-BHA-G20` 系列。这是原厂型号与上架型号的命名差异，需要**显式别名表**而不是放宽匹配（放宽会引入错误授权）。

### 5.3 表前型号行存在但不构成轴 —— 见于 datasheet 5 处

`e381476b618c`(EzManager3000)、`d623d58abfb8` / `f9e736af39f7` / `43c5a844e1b4`(SAJ eManager)、`1833312ad717`(eSolar AIO3) 等：型号只出现在表前散文本里、且该文本不是 `Technical Data` 声明，或只有 1 个型号。归入 `preceding_line_no_heading`。

### 5.4 未隔离的组件型号行 —— 1 个表格组（德语 BAT-C）

见 §4.3。`pack_model_row()` 是英文专用正则（`source_roles.py:48-66`），且要求整 chunk 单行。任何「组件型号行混在大分片里」的语言版本都会整表 conflict。

### 5.5 型号在表前文本里被换行拆断 —— 2 个表格组（ETR 80–125 kW 英德两版）

```
8ced72d8cec0 (ETR 80–125 DE) p3 / 76df70ea8474 (ETR 80–125 EN) p3
表前文本: 'GW110K-\nETR-G10\nGW124.99K-\nETR-G10\nGW125K-\nETR-G10'
r0: 'Efficiency' / 'Wirkungsgrad'（分段标题行，不是表头）
```

`model_pattern()` 把型号写成 `gw110k\-etr\-g10`（`source_models.py:33-36`），只容忍**空格**，不容忍换行；原文在连字符处断行，于是 tail 一个标签都解析不出 → `model_axis=None` 且无 columns。同系列 p2 的表因为型号列表在同一行，30 个表正常关联。

这一条值得单列，因为它是**纯文本归一化问题**，修法最简单（在 tail 归一化时把 `-\n` 折叠为 `-`），且很可能同时影响 §5.2 里的部分型号失配。

---

## 6. 假绿根因

### 6.1 准备门到底检查什么

`services/genie/index/store.py:246-330`：

```python
for cid, ids in proof.get("chunk_products", {}).items():
    ...
    supported = authorize_chunk(chunk.doc_sha256, ids, links, scope, ...)
    for item in supported:
        covered.setdefault(item["product_id"], set()).add(item["document_id"])
        if not scope or scope.get("basis") != "warranty_procedure":
            prepared.setdefault(item["product_id"], set()).add(item["document_id"])

for product in manifest["products"]:
    if covered.get(pid): ready.append(...)
    for did in product["documents"]:
        if document is None or status != "indexed":  reason = "document_unparsed"
        elif did not in prepared.get(pid, set()):     reason = "no_proven_passage"
        else: continue
        unprepared.append({...})

complete = not unprepared and len(ready) == len(manifest["products"])   # :324
```

判定的粒度是 **(product_id, document_id) 二元组**：只要该产品在该文档下有**任意一段**可用 passage，这一对就算「已准备」。`unprepared` 只在这一对**一段都没有**时登记。

所以六份 datasheet 的实际情况正好落在盲区：

| 文档 | 有关联的文本块 | 表格 | 门禁结论 |
| --- | --- | --- | --- |
| c95aef48b1ea | p1 `passage` `[6321]` ×1 | 4 张全裸 | prepared |
| 7e445df02017 | p1 `passage` `[6321]` ×1 | 4 张全裸 | prepared |
| 2a76fb0815a2 | p1+p2 `passage` ×2（1954/1955） | 2 张全裸 | prepared |
| 4adebe72eb25 | p1+p2 `passage` ×2（1946 / 1947,1948） | 5 张全裸 | prepared |
| e00f9645d187 | `hs3_datasheet_de` ×5 | 5 张全裸 | prepared |
| 143fb6026284 | `passage` ×2 + `section` ×1（2409） | 1 张全裸 | prepared |

结果是 `preparation_complete=true`、`unprepared_documents=[]`，而实测 **6321 全部 212 个可检索 chunk 里只有 1 个带规格词汇**（`1282f97a30ca` p2 证书页的 `Energy [kWh]`），datasheet 的参数表一条都进不来。这就是工单里「对 6321 的规格问题只能答未命中技术表」的直接原因。

### 6.2 三层各自的失效点

1. **写库层（`store.py`）**：只看「有没有至少一段」，不看「该文档的表格是否有任何关联」。`document_unparsed` 只覆盖解析失败，不覆盖「解析成功但整页参数表零关联」。
2. **PHP 门（`PreparationJobs.php:397-420`）**：完全信任 worker 上报的 `preparation_complete` 与 `unprepared_documents`，只校验行格式（`document_id` 存在、`product_id` 在 `product_ids` 里、`reason ∈ {no_proven_passage, document_unparsed}`，见 `:618-637`）。worker 说 complete 它就 complete。
3. **检索层（`retrieval.py:316-327`）**：`preparation_complete` 只做 `bool(model_identity_revision) and meta=='true'` 的与运算，不参与任何内容判断。

三层没有一处对「文档里有参数表但零关联」这件事有断言。

---

## 7. 波及面

### 7.1 生产真值（表格 chunk 关联率）

| doc_type | 文档 | 表格 chunk | 有关联 | 关联率 | 全部表格皆裸的文档 |
| --- | ---: | ---: | ---: | ---: | ---: |
| manual | 39 | 3353 | 82 | 2% | 23 |
| certificate | 44 | 587 | 30 | 5% | 22 |
| datasheet | 47 | 479 | 289 | 60% | **6** |
| compatibility | 4 | 266 | 0 | 0% | 4 |
| other | 9 | 23 | 4 | 17% | 5 |
| **合计** | 143 | **4708** | **405** | **8.6%** | 60 |

### 7.2 「应关联 vs 合理无关联」

「裸」不等于「应关联」。certificate 的表格多是版式产物（页眉、签名框、勾选表），manual 的表格多是警告/符号/清单——这些本来就与型号无关。按**参数表**口径（≥4 行、≥2 列、且含单位或工程属性词）筛：

```
参数表型表格组 969
  有关联         71   (7%)
  无关联        898
```

无关联 898 个的归因（`bare_final.json` + `param_final.py`）：

| 归因 | 组数 | 说明 |
| --- | ---: | --- |
| `no_model_axis` | 608 | 表头无型号、表前也无型号 —— 多数为**合理无关联**（多产品文档里的通用参数/告警表），少数属应关联（见 7.3） |
| `axis_ok_but_no_assoc` | 148 | **确属应关联**：型号轴物理成立，仍被否决。其中 146 是 §5.1 的标题否决 |
| `single_product_no_axis` | 138 | 单产品文档的两列表 —— **结构上应有单一产品授权**，当前无路径 |
| `tail_unknown_code` | 2 | GW ESA EN/DE（G11 未上架） |
| `excluded_fragment_not_pack_row` | 1 | BAT-C DS DE（德语 pack 行） |
| `body_width_mismatch` | 1 | ET 80–100 kW DE（解析结构损坏） |

按 doc_type 拆分「参数表型且无关联」：

| doc_type | 受影响文档 | 组数分解 |
| --- | ---: | --- |
| manual | 32 | no_model_axis 528 / axis_ok 137 / single_product 122 |
| certificate | 14 | no_model_axis 48 / single_product 15 |
| datasheet | 15 | axis_ok 11 / no_model_axis 3 / single_product 1 / 其余 3 |
| compatibility | 2 | no_model_axis 15 |
| warranty | 3 | no_model_axis 3 |
| Handbuch/Kompatibilität | 2 | no_model_axis 11 |

### 7.3 datasheet 全部表格皆裸的 6 份（即工单对象）

```
c95aef48b1ea  4 表  GW ESA 261kWh Datasheet EMEA EN V1.1
7e445df02017  4 表  GoodWe ESA 125 kW / 261 kWh datasheet (DE)
2a76fb0815a2  2 表  GoodWe BAT-C Series 61.4–112.6 kWh Datasheet (DE)
4adebe72eb25  5 表  GoodWe ET Serie 80–100 kW Datenblatt (DE)
e00f9645d187  5 表  SAJ HS3 5–12K-T2 Three-Phase Datasheet (German)
143fb6026284  1 表  GoodWe SEC3000C Datasheet (EMEA, EN)
```

### 7.4 工单提到的「约 23 份 manual 的表格 chunks」——核实为 23 份文档

生产里「全部表格皆裸」的 manual 恰为 **23 份**（实测清单）：

```
0adfb3d5e6df  ESA 261kWh UM EN V1.6        63 表
5876178f27d0  ESA 261kWh UM DE V1.6        67
5cd104b9e006  ESA 3-10kW UM EN V1.8       300
894ef3bd6dac  ESA 5-30kW UM EN V1.4       300
363be3f64d74  ETR 50-125kW UM DE          257
50bdd49b7be0  ETR 50-125kW UM EN          229
ef85dd1a58fc  BAT-C 208.9-261.2 UM EN      55
6f2149de8cfe  BAT-C 208-261 UM DE          56
26a5052fc859  ET 50-100kW Systemhandbuch   26
f66efb70d0d8  ET 50-100kW Solution Manual  24
40681261da52  HCA G2 UM DE                 35
6a8d11d5afde  HCA G2 UM EN                 27
91ceb16b37a9  EzManager3000 UM             51
6fbecc058303  GM330/GMK330/GMK360 UM       11
f4d53810d74c  ESA 261 maintenance UM       36
d5167d27d5e4  ESA 261 microgrid UM         29
6bdd27e577fc  ESA 261 on-grid UM           25
307b704c87f2  ETR quick install guide       3
a92c63a47dc0  SAJ HS2/AS2 UM DE            41
ee6b3a41b825  SAJ CB2 57.3-100.3 HV5 UM    26
a70cb4c39824  SAJ CB2 quick install guide   4
af395be79aee  SAJ eSolar AIO3 QIG          3
4cc6c9d37afa  chint dtsu666/dssu666 UM     25
```

其中 20 份含至少一个 `model_axis` 已成立却被否决的表格组，合计 162 组 —— 也就是 §5.1 那类缺陷在这批手册里最密集。

---

## 8. 证据与复现方法

### 8.1 生产只读查询（VPS）

```bash
ssh linker-services 'python3 - <<PY
import sqlite3, json
db=sqlite3.connect("file:/opt/linker-genie/index/current/index.sqlite?mode=ro",uri=True)
print(db.execute("select count(*) from documents").fetchone())          # 143
print(db.execute("select count(*) from chunks").fetchone())             # 19109
print(db.execute("select count(*) from chunk_products").fetchone())     # 5224
print(dict(db.execute("select key,value from meta where key in
  ('preparation_complete','materialization_complete','activation_epoch','recipe_revision')")))
PY'
```

表格关联率（按 doc_type 聚合、按 `(doc, source_table)` 归组）见 `/tmp/final_scan.py` 的同款查询。**关键口径**：`table_projection` 产出的是**新 chunk**（`<sha12>-p<page>-model-<digest>`），原生表格 chunk 永远保持 `pids=None`。因此判断「这张表是否被关联」必须看**派生 chunk**，不能看原生 chunk 的 `chunk_products` 行——这一点如果搞错，会把 174 个正常组误判成失败（我第一版统计就犯了这个错）。

### 8.2 本地重放

```bash
cd services/genie
uv run python /tmp/replay2.py     # 逐表打印 model_axis 成败与 scope basis
uv run python /tmp/diag_cols.py   # 逐表打印 _table_columns 的拒绝子条件
uv run python /tmp/ctxstat.py     # 统计 author-context 否决
```

基线：`~/de-linker-data/index/builds/20261103T203607Z-950501000/corpus/chunks.jsonl`（19109 chunks，与生产同 sha256 构建）。

### 8.3 表头几何（SAJ HS3 DE）

```bash
cd services/genie && uv run --group index python /tmp/hs3_predicate.py
# 输出：c5 bbox=(492.1,32.6,553.7,89.7)；墨迹 'HS3-5-12K-T2-W/G-P5' box=(493.3,27.4,554.5,32.0)，centre=(523.9,29.7)，in_y=False
```

### 8.4 一条已知的复现限制

本地用 `identify_texts` 打桩重放时，`family_manual` 会膨胀到 16101 条（生产 3307），因为 `_recognized` 的真实结果依赖在线 Woo 端点，未随构建落盘。**因此「basis 计数」不能本地重放核对**；本报告的 basis 数字全部取自生产 `chunk_scopes`。表级根因（`model_axis` / `_table_columns` 的判定）不依赖该打桩，可本地复现。

---

## 9. 系统性修法建议（决策材料，非实施）

按「修一次解决一类」排序，前三条覆盖 6 份 datasheet 中的 5 份。

### 9.1 补「单型号表格」的授权路径（覆盖 4.1、4.2、4.6 与 138 个 `single_product_no_axis` 组）

问题：`model_axis` 与 `_table_columns` 都要求 ≥2 个型号，单产品文档的 2 列表永远无路可走。

规模实测（生产）：47 份 datasheet 里 **18 份只关联 1 个产品**（产品数分布 `{1:18, 2:5, 3:5, 4:5, 5:3, 6:5, 7:4, 13:1, 17:1}`）。六份目标文档中落在这一档的是 `c95aef48b1ea`、`7e445df02017`、`143fb6026284`（各 1 个产品）；`2a76fb0815a2` 是 2 个、`4adebe72eb25` 是 3 个、`e00f9645d187` 是 5 个，不适用本条。

最小修法：在 `compile_scopes` 的表循环里增加一条**单型号分支**，条件全部可物理验证，不放宽任何现有规则：

- 该 `(doc_sha256, source_table)` 组只有一个分片，且 `read_cells` 通过；
- 该文档在 Woo 里只关联**一个**当前产品（`len(doc["product_ids"]) == 1`），且该产品 `published`；
- 表前同一页存在**唯一**一条型号声明，其模型与上述产品完全相等（用现有 `model_pattern` 严格匹配，不做模糊）；
- 表体通过 `render_projection` 的等价校验（属性/值配对、无 `|`/换行、无未解析脚注标记）。

产出仍走 `table_projection` 的证明结构（`model_column` 记 0 或单列），并绑定 `source_chunks` 为该表全部分片 + 那条型号声明。这样 `valid_projection` 的运行时复核仍然生效。

风险：单产品文档里若有「另一产品的参数表」，会被误授权。用「表内出现其他产品型号即拒绝」`safe_rows`/`blocked` 现有机制兜住（SEC3000C 的 `GM330` 行正好会被这条挡住，需要按行隔离而不是整表拒绝——见 9.4）。

### 9.2 表头 span 的几何恢复（覆盖 4.5）

问题：Docling 的 `cell.bbox` 与自己的文字层墨迹可以整体错位 4.6 pt（SAJ HS3 DE c5）。

最小修法：在 `enrich_model_axes`（`extract.py:1874-1967`）里，算完每页 `row_start == 0` 且 `column_header` 的单元格后：

1. 先按现有规则匹配 span；
2. 若某表头格匹配到 0 个 span，而**同一行其它表头格**匹配到了，用它们的**墨迹 y 带并集**（不是 cell bbox）作为该格的纵向接受域重试一次；
3. 重试仍需 `_span_stays_in_cell` 的横向包含 + 同一列 x 中心，且必须**恰好 1 个**候选。

这不是放宽容差，而是用同一行已证明的几何修正一个错误的框。所有落盘证据（`source_cells`）不变，`valid_projection` 复核不变。

### 9.3 `pack_model_row` 支持德语，且按行而非按 chunk 隔离（覆盖 4.3）

问题：`source_roles.py:48-66` 只认英文 `Pack Type / model`，且要求整个 chunk 单行。德语 `Batteriepack-Typ / Modell` 不匹配；DE 版又把该行混在 17 行的大分片里。

最小修法两步：

1. 正则扩展为多语种等价式：`Pack\s+(Type\s*/\s*model|Model\s*/\s*Type)` ∪ `Batteriepack-(Typ|Modell)\s*/\s*(Modell|Typ)` ∪ `Pack-(Typ|Modell)\s*/\s*(Modell|Typ)`。必须仍然是**完全匹配整格**，不接受前缀/模糊。
2. `publication.py:166-186` 的隔离判定从「整 chunk 是 pack 行」改为「chunk 内**存在** pack 行，且 `source_rows` 能定位到具体行」——用已有的 `source_rows` 把该行从 conflict 判定里摘出去，其余行照常走 `safe_rows`。`chunking.py:225` 的 `isolated` 切分保持现状（它是优化，不是正确性依赖）。

### 9.4 未上架型号不应毒化整表（覆盖 4.1、4.2 的 G11）

问题：`_table_columns` 里 `unknown_models(tail, …)` 命中任意未知 code 就 conflict。GW ESA 的 tail 同时含 `G10`（我们的产品）与 `G11`（未上架），结果整表报废。

最小修法：把「tail 里有未知 code」从 **conflict** 降级为 **排除该标签**——只保留能在 Woo 里解析、且在该文档 `product_ids` 内的标签构成轴；若排除后标签数 `< 2`，按 9.1 的单型号路径处理；若排除后仍 `< 1`，静默跳过。理由：`unknown_models` 的职责是「不能把未知 code 当成权限」，不是「有未知 code 就连带否定已知 code」。

需要同时保留的护栏：排除的标签必须在 `scope` 里留痕（记录被排除的 code 与原文），便于审计；且**不得**因此把表授权给排除项对应的产品（它不在 Woo 里，本来就取不到 pid）。

### 9.5 带容量数字的章节标题不应成为型号收窄（覆盖 §5.1 的 146 组）

问题：`_author_contexts` 把 `ESA Series 125kW/261kWh` 这类标题记为收窄声明；`author_scope_allows` 要求每个边界的 subjects ⊇ 目标产品，空集合直接 False。

最小修法：把 `rating_cover` 的判据从「`page == 1` + `All-in-One` + 带 rating」推广为**与页无关**的通用形式：一个 heading 若

- 不含任何当前型号（`contained` 为空），且
- 含单位型工程范围（现有 `ratings` 正则），且
- 去掉该范围后不再产生 unknown model，

则它是「产品线/容量段标题」，不是型号收窄，标 `rating_cover = True` 并跳过。现有 p1 特例是这条通用规则的一个子集，可以直接替换。

对 `29bb252c549a` p311 的 `WiFi/LAN Kit-20 ·` 则属于另一类：它是**配件**标题。建议一并处理——heading 里唯一带数字的 token 若不在 `models` 也不在 `family_labels`，且该 heading 不是 `column_header` 语境，则视为配件/主题标题，不作型号收窄。

### 9.6 型号别名表（覆盖 §5.2 的 20 组）

`HS3-12K-T2-W-P` → `HS3-12K-T2-W/G-PX`、`CH2-*` → `CHS2-*`、`GW3K-BHA-G20` → 待确认。这必须是一张**显式的、逐条有原厂出处**的别名表（放 `services/genie/index/` 的数据文件，随 `recipe_revision` 变更生效），不能靠正则放宽。同时要有一条「别名只能收敛到已发布产品」的校验。

### 9.7 门禁如何显性报警（治假绿）

三层各加一条，粒度从粗到细：

**① 写库层（`store.py`，最有效）**

在 `preparation_complete` 之外新增一个**内容覆盖**指标，并让 `unprepared` 支持第三种 reason：

```
reason ∈ {no_proven_passage, document_unparsed, table_without_scope}
```

判定：对该 (product, document) 对，若该文档存在 ≥1 个 `kind == "table"` 且 `source_rows` 覆盖 ≥N 行（建议 N=4）的分片组，而该组**没有任何**带 pids 的派生/原生 chunk，则登记 `table_without_scope`。

这条要按 **doc_type 区分标准**，不能一刀切：

- `datasheet` / `Datenblatt`：**任何** ≥4 行的参数表零关联 → 必须报警（这是工单要求的「按 doc_type 区分准备标准」）；
- `manual`：只有「表头或表前存在型号、且轴成立」的表才要求关联；通用告警/符号/清单表豁免；
- `certificate`：豁免（版式表格为主）；
- `compatibility`：**所有**表格都应有双产品关联 → 最严格（目前 0/266）。

实现上建议用与 `is_passage` 同层的确定性函数，不引入启发式评分。

**② PHP 门（`PreparationJobs.php:618-637`）**

把 `table_without_scope` 加入允许的 reason 枚举，并在 `preparation_complete` 的与运算里保持「诊断非空即 false」（现有逻辑已如此）。同时把该 reason 在后台与每日摘要里显示——现在 `no_proven_passage` 只在一对完全没有 passage 时出现，正是让这类缺陷沉默的原因。

**③ 构建产物（`manifest.json`）**

在 `permission_coverage` 里并列一个 `table_coverage`：

```json
"table_coverage": {
  "datasheet": {"tables": 479, "with_scope": 289, "parameter_tables_without_scope": 16},
  "manual": {...}, "certificate": {...}, "compatibility": {...}
}
```

这是发布前唯一能一眼看出「这一批表格授权退化了」的地方。建议在 `ops/publish_index.py` 里对 datasheet 的 `parameter_tables_without_scope` 设硬阈值（>0 阻断），其它 doc_type 只报告。

### 9.8 不建议的方向

- **不要**放宽 `_model_axis_data` 的中心点包含判定为「相交即可」：SAJ HS3 DE c5 与墨迹**完全不相交**，放宽到相交仍救不了，却会给别的文档引入错误轴。
- **不要**用「文档级 document_model」兜底授权表格：`scope_proofs` 已有 `document_model` basis，但对表格一旦放开，任何多产品文档里的任意参数表都会被授权给全文档产品。这正是当前 `no_model_axis` 608 组保持沉默的正确理由。
- **不要**靠给 datasheet 补 `manual` 记录绕过：`manual_evidence_records.py` 的 reviewed_manual 是人工逐条核对的产物，无法覆盖 47 份 datasheet × 多语言。

---

## 10. 未解决与需父线裁决

1. **§9 全部是建议，未实施。**本报告不含任何代码改动。
2. **单型号路径的产品集合口径**（9.1）需要业主/父线确认：`document.product_ids` 当前是否已经保证「该 datasheet 只关联它描述的那一个产品」。生产里 `143fb6026284` 关联 `[2409]`、`c95aef48b1ea` 关联 `[6321]`，看起来成立，但没有全库验证「datasheet 是否都只关联一个产品」。
3. **G11 是否应该上架**是业务问题，不是代码问题。若不打算上架，9.4 的「排除未知标签」是必须的；若打算上架，则 4.1/4.2 会自动变成 2 标签轴，但仍受 §9.1（单型号）与 §9.5（标题否决）影响。
4. **ET 80–100 kW DE 的解析损坏**（4.4）需要在 `index.parse` / Docling 配置层处理（可能是 `TableFormer` 模式或 OCR 触发条件），本次未深入；同一系列 EN 版解析正常，说明是可定位的解析差异。
5. **146 组标题否决**只做了一次聚合统计 + 1 个样本的逐条验证。逐文档确认需要在实施 9.5 时按文档回归。
6. 本地打桩重放无法复现生产的 `family_manual` / `warranty_*` basis 数量（§8.4），后续任何「basis 计数」结论都必须取自生产或真实调用 Woo 端点的构建。
