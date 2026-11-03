# Genie 知识索引“缺证”关联只读取证审计报告（2026-11-03）

## 1. 审计结论摘要

| 维度 | 前序分析（`genie.json`，41,872 B）说法 | 本次 VPS 生产实测真值（2026-11-03） | 审计判定 |
| --- | --- | --- | --- |
| 当前线上 `activation_epoch` | `epoch 76`（索引版本 `20261103T033756Z-991839000`，`source_revision = cd9e9a990e18...`） | **`epoch 77`**（索引版本 `20261103T071623Z-963760000`，`source_revision = 113e8ad236d4...`） | **已演进 1 个 epoch**（2026-11-03 15:16 CST 因 #548 ETR 安装事实发布触发重发，缺证集合未变） |
| Woo 发布清单关联总数 | 原始清单 88 商品 / 147 文档 / 614 关联；Genie 过滤参考件后 85 商品 / 143 文档 / 610 关联 | 原始清单 **88 商品 / 147 文档 / 614 关联**；`Snapshot.read` 过滤 3 个参考组件/线缆商品及 4 份专属参考文档后为 **85 商品 / 143 托管文档 / 610 关联** | **成立** |
| 当前生产有证（permitted / prepared）关联数 | `610 - 1 = 609` 条（Q6 将其作为待独立复核的推导，标 `confidence: medium`） | **`609` 条关联有证**（`DocumentIndex.permissions(snap, None)` 实测放行 **4,819** 个 chunk rowid，精确覆盖 **609** 对 `(product_id, document_id)`） | **成立（已由 medium 升格为实测确证）** |
| 当前生产缺证（`unprepared_documents`）关联数 | **1 条**：`product_id = 1954`（`GW61.4-BAT-AC-G10`）× `doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a`（`c29cbf257d51...`，`reason = "no_proven_passage"`） | **1 条**：`1954`（`GW61.4-BAT-AC-G10`）× `doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a`（`GoodWe BAT-C 60–112.6 kWh User Manual (EN V1.0)`，`reason = "no_proven_passage"`） | **成立** |
| “`epoch 62 / 598 有证 / 19 缺证`”历史说法 | 来自 `docs/acceptance/2026-10-31/548/knowledge-coverage.md` 的历史里程碑，算术为 `612 - 19 = 593 prepared + 5 HS3 条件证书 = 598 permitted`（Q6 标 `medium`） | **数字本身是 `epoch 62`（`20261102T025848Z-011773000`）的真实历史快照，但已过时（该批 19 条 + 1 条 `1955 × 0ef4b1ccdcc4` 共 20 条已于 `epoch 75` 全部补证清零）；且 Q6 对 `598 - 593 = 5` 的归因有误**（非“HS3 条件证书”，见 §2.2 校正） | **历史数字过时；Q6 算术归因需校正** |

---

## 2. 对前序 `genie.json`（41,872 B）的逐项核实与校正

> **文件位置说明**：前序子代理在父会话 `726b9156-946c-4d61-8f19-554274e65b9e`（`seq: 744–782`）中将 41,872 B 的分析写在了 `/tmp/b2-out/genie.json`，后续提交 `7e7acbfe697ac1316788c7bf2b6eb8f0a7ad5f48`（#866）仅将 `conductor-facts.json` 与 `gateway-limits.json` 考入 `docs/acceptance/2026-11-03/548/evidence/`，未拷入 `genie.json`。本次审计从会话事件日志中完整提取了该 41,872 B JSON（含 Q1–Q6 全部字段与载荷）并与线上状态逐一比对。

### 2.1 `genie.json` 中成立的部分（Q1–Q5 及 Q6 线上计数）

1. **权限与证据门控链路（Q1–Q2）成立**：
   - 运行时检索入口 `services/genie/src/linker_genie/retrieval.py:583-601`（`_permitted_hits`）与 `retrieval.py:684-1049`（`DocumentIndex.permissions`）严格求交集：商品必须在 `publication_products` 且版本一致、文档关联必须在 `publication_documents` 且 `document_revision` / `blob_sha256` 一致、chunk 必须在 `chunk_products` 命中目标 `product_id`，且 `chunk_scopes.proof` 必须通过 `services/genie/src/linker_genie/publication_scope.py:430`（`authorize_chunk`）校验。
   - 构建期导出 `services/genie/index/store.py:243-336`（`export`）遍历 `proof["chunk_products"]` 与 `proof["chunk_scopes"]`，调用 `authorize_chunk(..., require_table_anchor=True)` 计算每个商品的 `covered` 与 `prepared` 文档集合；任何已索引（`status == "indexed"`）但不在 `prepared[pid]` 中的 `(product_id, document_id)` 关联均写入 `meta.unprepared_documents`，`reason = "no_proven_passage"`，并置 `preparation_complete = false`。
2. **线上过滤口径（Q4）成立**：
   - `services/genie/src/linker_genie/publication.py:92-105`（`Snapshot.read`）过滤掉 `engineering_role in ("reference_pv_module", "reference_cable")` 的 3 个参考商品及其独占的 4 份文档，因此 Woo manifest 的 `88 商品 / 147 文档 / 614 关联` 在 Genie 侧恒为 **`85 商品 / 143 托管文档 / 610 关联`**。
3. **当前线上实测（Q3 / Q6 当前状态）成立（epoch 已从 76 升至 77）**：
   - 在 `epoch 75`（`20261102T192055Z-751952000`）时，线上为 `609` 条关联，`unprepared_documents = []`（**0 缺证**，`preparation_complete = true`）。
   - `2026-11-03 11:33 CST`（`03:33 UTC`），Woo 生产环境给商品 `1954`（`GW61.4-BAT-AC-G10`）新增绑定了手册 `doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a`（`GoodWe BAT-C 60–112.6 kWh User Manual (EN V1.0)`，`blob_sha256 = c29cbf257d51...`），关联总数从 `609` 增至 `610`。
   - `epoch 76`（`20261103T033756Z-991839000`）与当前 `epoch 77`（`20261103T071623Z-963760000`）均已将该 PDF 解析入库（87 页、183 个 chunk，`status = indexed`），但未生成任何 `chunk_scopes` / `chunk_products` 记录，导致该新增关联成为**唯一 1 条** `no_proven_passage` 缺证关联，其余 **609 条关联全部有证且在 `DocumentIndex.permissions()` 中可检索**。

### 2.2 `genie.json` 说法校正点（针对 Q6 `confidence: medium` 的两处偏差）

1. **校正点一：“`epoch 62 / 598 有证 / 19 缺证`”是已完结的 11 月 2 日历史状态，不能代表当前生产索引**
   - `epoch 62`（索引版本 `20261102T025848Z-011773000`，记载于 `docs/acceptance/2026-10-31/548/knowledge-coverage.md:26,32,96-117`）当时的 19 条缺证关联（外加随后为 `1955` 新增绑定的 `0ef4b1ccdcc4` 共 20 条）已在 `2026-11-02 18:40 UTC` 发布的 `b43f1e99`（对应 VPS 上的 `epoch 75`，`20261102T192055Z-751952000`）中**全部完成源码锚定与补证**（详见 §5 逐条核实表）。
   - 当前 VPS 生产保留的三代索引实测演进如下：

| VPS 索引目录 | `activation_epoch` | `source_revision`（前 12 位） | 托管文档数 | 关联总数 (`publication_documents`) | 有证可检索关联数 (`permissions`) | 缺证关联数 (`unprepared_documents`) | `preparation_complete` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `20261102T192055Z-751952000` | `75` | `bd2bbe2ca7be` | 142 | 609 | **609** | **0** | `true` |
| `20261103T033756Z-991839000` | `76` | `cd9e9a990e18` | 143 | 610 | **609** | **1** (`1954 × doc-0ee8a88e...`) | `false` |
| `20261103T071623Z-963760000` (**`current`**) | **`77`** | `113e8ad236d4` | **143** | **610** | **609** | **1** (`1954 × doc-0ee8a88e...`) | **`false`** |

2. **校正点二：Q6 将 `epoch 62` 中 `598 permitted` 与 `612 - 19 = 593 prepared` 的差值 `+5` 归因为“5 个 HS3 条件证书关联（`hs3_conditional_certificate`）”不成立**
   - **代码与数据真值**：根据 `services/genie/index/store.py:276-306`，`hs3_conditional_certificate` 并**未**被排除在 `prepared` 之外（只有 `basis == "warranty_procedure"` 被写成只进 `covered`、不进 `prepared`：`if proof.get("basis") != "warranty_procedure": prepared.setdefault(pid, set()).add(did)`）。
   - 在 `epoch 60 / 62` 时（见 `docs/acceptance/2026-10-31/548/knowledge-coverage.md:50,112-117`），SAJ 保修文档 `be0569b4602a`（`doc-48918fbb624fef78a46c4d8404402fc86b5d7e91343b16f600f2c4f38cd33dc4`）对 5 个 HS3 逆变器商品（`1185, 1186, 1187, 2198, 2199`）当时只有第 4 页的 `basis = "warranty_procedure"` chunk，还没有第 1 页的 `basis = "warranty_terms"` chunk。
   - 因此在 `epoch 62` 时，这 **5 条 `HS3 × be0569b4602a` 保修关联**：
     - 在 `DocumentIndex.permissions()` 中被放行（计入 `598` 条 permitted pairs）；
     - 但在 `store.py` 中因为 `basis == "warranty_procedure"` 不计入 `prepared`，故同时留在 `19` 条 `unprepared_documents` 中（直到 `epoch 75` 补入 `be0569b4602a-p1-hs3-warranty-terms-*` 的 `warranty_terms` chunk 后才从 `unprepared_documents` 消去）。
   - 所以 `epoch 62` 的真实算术恒等式是：**`612 总关联 - 19 unprepared (其中含 5 条仅具 warranty_procedure 的保修关联 + 14 条完全无放行 chunk 的关联) = 593 完备关联`；而 `DocumentIndex.permissions()` 放行数为 `593 + 5 (仅具 warranty_procedure 的保修关联) = 598`**，而非 Q6 猜测的“HS3 条件证书关联”。

---

## 3. VPS 生产索引当前真实状态（只读实测）

通过 `ssh linker-services`（只读查询 `/opt/linker-genie/index/current/index.sqlite` 与 `POST http://127.0.0.1:8902/knowledge/loaded`）及 `ssh hostinger-de-linker`（只读查询 `wp option get linker_publication_jobs`）交叉核实，三端状态 100% 一致：

- **VPS 服务进程与目录**：
  - `/opt/linker-genie/current` -> `/opt/linker-genie/20261102T184000000000Z-b43f1e99`
  - `/opt/linker-genie/index/current` -> `/opt/linker-genie/index/20261103T071623Z-963760000`
  - `index.sqlite` 大小：`294,567,936 B`，SHA-256：`6380fc8155877819fcba64f55cd7922cdd50cea23487e429da8430c805fa63c9`
- **版本与 Epoch 元数据（`meta` 表 & `/knowledge/loaded` & WP `linker_publication_jobs.knowledge`）**：
  - `version` / `index_version`: `"20261103T071623Z-963760000"`
  - `activation_epoch`: `77`
  - `source_revision`: `"113e8ad236d47e61d7b8af920fe6e0610d146b93bb4c4e0d4de477a0b9097534"`
  - `model_identity_revision`: `"e95fde6822b8616b3e5e98c05a933a9fd0cf5d93416220a580ec82ac24fb6c14"`
  - `recipe_revision`: `"01ec739f762ac29741de2bc6c3b2a4f06f6dd15bc10114e9330f6e5d791d6f1b"`
  - `serving_revision` / `expected_serving_revision`: `"04d54eec2d0aaf5b3d56507e1cb808a624398f9ee4e0704278fd762db0a129be"`
  - `materialization_complete`: `true`（85/85 商品均在 `publication_ready_products` 中）
  - `preparation_complete`: `false`
  - `unprepared_documents`:
    ```json
    [
      {
        "document_id": "doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a",
        "product_id": 1954,
        "reason": "no_proven_passage"
      }
    ]
    ```
- **SQLite 表规模与授权统计**：
  - `publication_products`: **85** 个商品
  - `documents`: **143** 份托管 PDF（全部 `status = 'indexed'`，0 份 `failed`，共 4,700 页）
  - `publication_documents`: **610** 条 `(product_id, document_id)` 关联
  - `chunks`: **19,107** 个块（其中派生投影块 4,340 个）
  - `chunk_scopes` / `chunk_products`: **5,222** 个带作用域证明的块
  - `DocumentIndex.permissions(snap, None)` 实测放行：**4,819** 个块，覆盖 **609** 条 `(product_id, document_id)` 关联；仅缺 **1** 条关联。

---

## 4. 真实缺证关联清单、缺失证据字段与补证路径

### 4.1 唯一真实缺证关联（1 条）

| 字段 | 生产实测值 |
| --- | --- |
| `product_id` | `1954` |
| 商品型号 (`model`) | `GW61.4-BAT-AC-G10`（GoodWe BAT-C 61.4 kWh 工商储户外一体柜） |
| `document_id` | `doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a` |
| `document_revision` | `caa2e292a2c784906f32f2ab98153b4c3e2cfc1e05436627a53cf2caec7571bc` |
| `blob_sha256` | `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7` |
| 托管文档标题 (`title_en`) | `GoodWe BAT-C 60–112.6 kWh User Manual (EN V1.0)` |
| 托管 URL | `https://de-linker.com/wp-content/uploads/2026/10/GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf` |
| `doc_type` / `lang` / `pages` | `manual` / `en` / `87` 页（已解析为 **183** 个 `chunks` 行，`status = 'indexed'`） |
| 缺证原因码 (`reason`) | `no_proven_passage` |

### 4.2 缺失的证据表记录与字段（Missing Evidence Fields）

在 `/opt/linker-genie/index/current/index.sqlite` 中，文档 `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7` 虽然在 `documents`（1 行）和 `chunks`（183 行）中已完整物化，但在证据授权层**完全为空（0 行）**：

1. **`chunk_products` 表缺失记录**：对应该文档的 `chunk_id LIKE 'c29cbf257d51%'` 为 **0 行**（缺少 `(chunk_id, product_ids = "[1954]")` 绑定）。
2. **`chunk_scopes` 表缺失记录**：对应该文档的 `chunk_id LIKE 'c29cbf257d51%'` 为 **0 行**（缺少 `proof` JSON）。
3. **三条可选证据生成路径各自缺失的具体字段与根因**：
   - **路径 A（`basis = "table_projection"`，第 80–83 页技术参数表自动列投影）——因 0.0841 pt 行距阈值截断而缺失 `model_spans`**：
     - 在 `corpus/chunks.jsonl` 的第 80、81、82、83 页表格块（`c29cbf257d51-p80-9a9186aa`、`c29cbf257d51-p81-f7f7ffe9`、`c29cbf257d51-p82-62e685e0`、`c29cbf257d51-p83-a9817917`）中，表头第 0 行有 4 个型号列：
       - Col 1 (`GW61.4-BAT-AC-G10`)：**已生成** `model_spans`（含 `fragments: ["GW61.4-BAT", "AC-G10"]`）。
       - Col 2 (`GW92.1-BAT- AC-G10`)、Col 3 (`GW102.4-BAT- AC-G10`)、Col 4 (`GW112.6-BAT- AC-G10`)：**缺失 `model_spans` 字段**，且单元格 `text` 保留了 Docling 断行产生的空格 `'GW92.1-BAT- AC-G10'`。
     - **底层几何根因**：PDF 原件表头中 4 个型号均跨两行排印，PDFium 提取为 `GW...-BAT\ufffeAC-G10`。`services/genie/index/extract.py:914`（`_pdf_model_spans`）与 `services/genie/src/linker_genie/table_projection.py:311`（`_pdf_span`）校验上下两段 `SourceFragment` 的垂直间距条件为 `0 <= a[1] - b[3] <= min(a_h, b_h)`：
       - Col 1 (`GW61.4-BAT` / `AC-G10`)：`a[1] - b[3] = 671.9360 - 664.5620 = 7.3741 pt <= 8.9399 pt`（通过，`enrich_model_axes` 修复了单元格文本并写入 `model_spans`）；
       - Col 2–4 (`GW92.1-BAT`、`GW102.4-BAT`、`GW112.6-BAT` / `AC-G10`)：`a[1] - b[3] = 672.7660 - 663.7419 = 9.02405 pt > min_h (8.93994 pt)`，仅超出 **0.0841 pt（约 1%）** 即被丢弃！
     - 因为 Col 2–4 缺少 `model_spans` 且带空格，`_model_axis_data`（`table_projection.py:806-831`）对整张表返回 `None`，导致 Col 1（`GW61.4-BAT-AC-G10`）也无法生成派生投影块，进而缺失 `meta.external_axis_anchors` 及 `chunk_scopes.proof` 的 `{basis: "table_projection", table_chunk_id, column: 1, model: "GW61.4-BAT-AC-G10", source_location, source_cell, model_span, value_spans}`。
   - **路径 B（`basis = "reviewed_manual"`，人工核准手册证据表）——缺失 `MANUAL_EVIDENCE` 条目**：
     - `services/genie/src/linker_genie/manual_evidence_records.py`（于 2026-11-02 随 `b43f1e99` 发布）尚未收录 `2026-11-03 11:33 CST` 新绑定的 `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7`，因此 `compile_manual_evidence`（`services/genie/index/manual_evidence.py:130-198`）未生成 `{basis: "reviewed_manual", model: "GW61.4-BAT-AC-G10", source_chunk_ids, source_spans}`。
   - **路径 C（原文 `passage` 直通授权，`scope_proofs`）——因多型号共页被 `ambiguous` 拦截**：
     - 该手册涵盖 `GW61.4-BAT-AC-G10`（`1954`）、`GW92.1-BAT-AC-G10`（未上架）、`GW102.4-BAT-AC-G10`（未上架）、`GW112.6-BAT-AC-G10`（`1955`，已上架但 Woo 中未绑定 `doc-0ee8a88e...`）。所有点名 `GW61.4-BAT-AC-G10` 的原文块（p.3、p.19、p.34、p.80–83）均同时出现其余三个型号，被 `services/genie/index/publication.py:678-698` 的 `not matched.issubset(associated)` 与 `_unknown_models` 判定为多型号混杂而阻断。

### 4.3 补证路径（在 143 份托管手册中的候选文档、页码与 Chunk 锚点）

该缺证关联**完全可在现有 143 份托管文档内部核实并补证**（无需外部找资料，更不存在“无法核实”）：

- **目标托管文档**：`GoodWe BAT-C 60–112.6 kWh User Manual (EN V1.0)`
  - `document_id`: `doc-0ee8a88e3e74d10e542a38aaab00259352253f35e80216b2cea1b63460f1d52a`
  - `blob_sha256`: `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7`
  - 托管 URL: `https://de-linker.com/wp-content/uploads/2026/10/GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf`
- **手册内明确锚定 `GW61.4-BAT-AC-G10`（`product_id = 1954`）的候选页码与已解析 Chunk**：
  1. **第 80–82 页（`9 Technical Data` 规格主表，首选 `table_projection` 补证面）**：
     - **Page 80**（`chunk_id = c29cbf257d51-p80-9a9186aa`，`docling:p80:#/tables/50`）：第 1 列 `GW61.4-BAT-AC-G10` 完整给出电芯类型 `LFP (LiFePO4)`、电芯容量 `100 Ah`、额定容量 `200 Ah`、电池包型号 `GW10.2-PACK-ACI-G10`（`10.24 kWh`）、成组配置 `2P96S`、包数 `6`、标称能量 `61.44 kWh`、可用能量 `60 kWh`、额定电压 `307.2 V`、工作电压范围 `268.8~345.6 V`。
     - **Page 81**（`chunk_id = c29cbf257d51-p81-f7f7ffe9`，`docling:p81:#/tables/51`）：第 1 列 `GW61.4-BAT-AC-G10` 给出充放电温度范围 `-20~+55 ℃`、最大充放电电流 `180/220 A`、消防系统 `Aerosol (Pack&Cabinet Level)`、防护等级 `IP55`。
     - **Page 82**（`chunk_id = c29cbf257d51-p82-62e685e0`，`docling:p82:#/tables/52`）：第 1 列 `GW61.4-BAT-AC-G10` 给出最高海拔 `4000 m`、冷却方式 `Air Conditioner`、通信 `CAN (RS485 Optional)`、重量 `＜950 kg`、尺寸 `1030×1100×2200 mm`。
  2. **第 3、19、34 页（适用型号、铭牌释义与交付件清单，可选 `reviewed_manual` 补证面）**：
     - **Page 3**（`chunk_id = c29cbf257d51-p3-2efeb18b`，章节 `Applicable Products`）：明确声明 `"This document applies to battery systems of the following models: GW61.4-BAT-AC-G10 · GW92.1-BAT-AC-G10 · GW102.4-BAT-AC-G10 · GW112.6-BAT-AC-G10"`。
     - **Page 19**（`chunk_id = c29cbf257d51-p19-32774294`，章节 `Model Description`，`docling:p19:#/tables/10`）：明确定义型号代码 `"61.4: Rated energy of 61.4 kWh; 6 battery packs in the cabinet"`。
     - **Page 34**（`chunk_id = c29cbf257d51-p34-f2ef484f`，章节 `3.2 Items Supplied`，`docling:p34:#/tables/18`）：明确列出 `GW61.4-BAT-AC-G10` 的包间互联线束数量 `Packinterconnection harness GW61.4-BAT-AC-G10：×5`（该证据亦是 #548 绑定本手册的直接业务原因）。
- **具体工程修复落点（供后续实现票执行，本次审计只读不改）**：
  - **方案 1（根治解析器跨行型号拼接，推荐）**：在 `services/genie/index/extract.py:914`（`_pdf_model_spans`）与 `services/genie/src/linker_genie/table_projection.py:311`（`_pdf_span`）中，将 `\ufffe` 断行片段的垂直间距容差从严苛的 `<= min(a_h, b_h)`（`8.94 pt`）放宽至 `<= 1.25 * min(a_h, b_h)`（或 `<= max(a_h, b_h) + 1.0`），即可让 `c29cbf257d51` 第 80–83 页 Col 2–4（`gap = 9.024 pt`）正常产出 `model_spans`，从而由 `table_compiler.py:926-991` 自动为 `1954`（`GW61.4-BAT-AC-G10`）生成 `basis = "table_projection"` 的派生块与作用域证明（若 Woo 同时将该手册绑给 `1955` `GW112.6-BAT-AC-G10`，Col 4 也会自动为 `1955` 生成 `table_projection`）。
  - **方案 2（补充 `MANUAL_EVIDENCE` 显式锚点）**：在 `services/genie/src/linker_genie/manual_evidence_records.py` 中为 `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7`（`model = "GW61.4-BAT-AC-G10"`）登记基于 p.3（`c29cbf257d51-p3-2efeb18b`）、p.34（`c29cbf257d51-p34-f2ef484f`）及 p.80（`c29cbf257d51-p80-9a9186aa`）的 `ManualEvidenceRecord`（`basis = "reviewed_manual"`）。

---

## 5. 历史“19 缺证（+1）”关联在当前生产索引（Epoch 77）中的核实清单

为彻底消除前序报告对“`epoch 62 / 598 有证 / 19 缺证`”的疑虑，下表列出 `epoch 62` 的全部 19 条历史缺证关联（外加同批处理的第 20 条 `1955 × 0ef4b1ccdcc4`）在当前 VPS 生产 `index.sqlite`（`epoch 77`）中的实测状态——**全部 20 条均已有证（`prepared` & `permitted`），0 条缺证**：

| # | `product_id` | 商品型号 | `document_id`（前 20 位） | `blob_sha256`（前 12 位） | 托管文档标题与核实页码 | 当前线上状态 | 线上 `chunk_scopes.proof.basis` 与代表 `chunk_id` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `1954` | `GW61.4-BAT-AC-G10` | `doc-d78c367ed40dc7e3...` | `627e5444f47b` | `GoodWe Lynx C 60 kWh quick installation guide` (p.2, p.6) | **已补证 (1 chunk)** | `reviewed_manual`: `627e5444f47b-p2-manual-evidence-46482f7fe78adebc` |
| 2 | `1955` | `GW112.6-BAT-AC-G10` | `doc-d78c367ed40dc7e3...` | `627e5444f47b` | `GoodWe Lynx C 60 kWh quick installation guide` (p.2, p.6) | **已补证 (1 chunk)** | `reviewed_manual`: `627e5444f47b-p2-manual-evidence-d1645076295f8513` |
| 3 | `1955` | `GW112.6-BAT-AC-G10` | `doc-cbd6d3d2db163cf7...` | `0ef4b1ccdcc4` | `GoodWe ET 50–100 kW user manual (EN)` (p.29, p.92) | **已补证 (1 chunk)** | `reviewed_manual`: `0ef4b1ccdcc4-p29-manual-evidence-b784a7ea62394d2d` |
| 4 | `3595` | `GW125K-ETR-G10` | `doc-423a567c97612820...` | `307b704c87f2` | `GoodWe ETR 50–125 kW user manual (EN)` (p.1, p.27–28, p.60–61) | **已补证 (3 chunks)** | `reviewed_manual`: `307b704c87f2-p1-manual-evidence-4794c3a82f9a3734` 等 3 块 |
| 5 | `6507` | `GW80K-ETR-G10` | `doc-423a567c97612820...` | `307b704c87f2` | `GoodWe ETR 50–125 kW user manual (EN)` (p.1, p.27–28, p.60–61) | **已补证 (3 chunks)** | `reviewed_manual`: `307b704c87f2-p1-manual-evidence-7d33dc72df36d338` 等 3 块 |
| 6 | `6508` | `GW99.99K-ETR-G10` | `doc-423a567c97612820...` | `307b704c87f2` | `GoodWe ETR 50–125 kW user manual (EN)` (p.1, p.27–28, p.60–61) | **已补证 (3 chunks)** | `reviewed_manual`: `307b704c87f2-p1-manual-evidence-0ada33337b676bae` 等 3 块 |
| 7 | `6509` | `GW100K-ETR-G10` | `doc-423a567c97612820...` | `307b704c87f2` | `GoodWe ETR 50–125 kW user manual (EN)` (p.1, p.27–28, p.60–61) | **已补证 (3 chunks)** | `reviewed_manual`: `307b704c87f2-p1-manual-evidence-7f2f1caaa786b4ff` 等 3 块 |
| 8 | `6510` | `GW110K-ETR-G10` | `doc-423a567c97612820...` | `307b704c87f2` | `GoodWe ETR 50–125 kW user manual (EN)` (p.1, p.27–28, p.60–61) | **已补证 (3 chunks)** | `reviewed_manual`: `307b704c87f2-p1-manual-evidence-0364f4105f3ed506` 等 3 块 |
| 9 | `6511` | `GW124.99K-ETR-G10` | `doc-423a567c97612820...` | `307b704c87f2` | `GoodWe ETR 50–125 kW user manual (EN)` (p.1, p.27–28, p.60–61) | **已补证 (3 chunks)** | `reviewed_manual`: `307b704c87f2-p1-manual-evidence-0fa9bda4cd7dcec0` 等 3 块 |
| 10 | `4103` | `CB2-57.3-HV5` | `doc-74c741e3ff765006...` | `a70cb4c39824` | `SAJ CM2 / CB2 Series User Manual` (p.1, p.8, p.20) | **已补证 (3 chunks)** | `family_manual`, `reviewed_manual`: `a70cb4c39824-p1-family-2c7f2a4a4e682bdb` 等 3 块 |
| 11 | `4104` | `CB2-71.6-HV5` | `doc-74c741e3ff765006...` | `a70cb4c39824` | `SAJ CM2 / CB2 Series User Manual` (p.1, p.8, p.20) | **已补证 (3 chunks)** | `family_manual`, `reviewed_manual`: `a70cb4c39824-p1-family-5a8671a9dc9aff9c` 等 3 块 |
| 12 | `4105` | `CB2-85.9-HV5` | `doc-74c741e3ff765006...` | `a70cb4c39824` | `SAJ CM2 / CB2 Series User Manual` (p.1, p.8, p.20) | **已补证 (3 chunks)** | `family_manual`, `reviewed_manual`: `a70cb4c39824-p1-family-17451b370774753e` 等 3 块 |
| 13 | `4106` | `CB2-100.3-HV5` | `doc-74c741e3ff765006...` | `a70cb4c39824` | `SAJ CM2 / CB2 Series User Manual` (p.1, p.8, p.20) | **已补证 (3 chunks)** | `family_manual`, `reviewed_manual`: `a70cb4c39824-p1-family-1c4a3d6bc7a37ea9` 等 3 块 |
| 14 | `1957` | `GW208.9-BAT-LCD-G10` | `doc-3314557a1810e2fc...` | `ea081f6f6fb2` | `GoodWe Commercial & Industrial Compatible Battery Statement` (p.1, p.6) | **已补证 (1 chunk)** | `compatibility_overview_statement`: `ea081f6f6fb2-p1-56d02ba2` |
| 15 | `1185` | `HS3-12K-T2-W/G-PX` | `doc-784554fad43dd1b2...` | `e00f9645d187` | `SAJ HS3 Series Technical Datasheet (DE)` (p.1–2) | **已补证 (1 chunk)** | `hs3_datasheet_de`: `e00f9645d187-p1-hs3-datasheet-02ff21b7d192356a` |
| 16 | `1186` | `HS3-6K-T2-W/G-PX` | `doc-784554fad43dd1b2...` | `e00f9645d187` | `SAJ HS3 Series Technical Datasheet (DE)` (p.1–2) | **已补证 (1 chunk)** | `hs3_datasheet_de`: `e00f9645d187-p1-hs3-datasheet-6ec9ca6d4113cf86` |
| 17 | `1187` | `HS3-8K-T2-W/G-PX` | `doc-784554fad43dd1b2...` | `e00f9645d187` | `SAJ HS3 Series Technical Datasheet (DE)` (p.1–2) | **已补证 (1 chunk)** | `hs3_datasheet_de`: `e00f9645d187-p1-hs3-datasheet-0741a4663f861d26` |
| 18 | `2198` | `HS3-5K-T2-W/G-PX` | `doc-784554fad43dd1b2...` | `e00f9645d187` | `SAJ HS3 Series Technical Datasheet (DE)` (p.1–2) | **已补证 (1 chunk)** | `hs3_datasheet_de`: `e00f9645d187-p1-hs3-datasheet-8eec4b1d23d9cbba` |
| 19 | `2199` | `HS3-10K-T2-W/G-PX` | `doc-784554fad43dd1b2...` | `e00f9645d187` | `SAJ HS3 Series Technical Datasheet (DE)` (p.1–2) | **已补证 (1 chunk)** | `hs3_datasheet_de`: `e00f9645d187-p1-hs3-datasheet-ad6c7223a69f2ab8` |
| 20 | `2093` | `BU3-5.0-TV2-PRO` | `doc-48918fbb624fef78...` | `be0569b4602a` | `SAJ Limited Warranty Guidelines (EMEA)` (p.2) | **已补证 (1 chunk)** | `warranty_terms`: `be0569b4602a-p1-hs3-warranty-terms-243437aee9d946e1` |
| (附) | `1185, 1186, 1187, 2198, 2199` | `HS3-5K..12K-T2-W/G-PX` (5 款) | `doc-48918fbb624fef78...` | `be0569b4602a` | `SAJ Limited Warranty Guidelines (EMEA)` (p.1–2, p.4) | **已补证 (各 2 chunks)** | `warranty_terms` (p.1) + `warranty_procedure` (p.4) |

---

## 6. 资源与只读合规报告（AGENTS.md §0）

- **生产只读边界**：本次在 `linker-services` 与 `hostinger-de-linker` 上仅执行了只读 `SELECT`、`POST /knowledge/loaded`、`sha256sum` 与 `wp option get`，未修改任何生产文件、数据库或服务进程；未改动 `services/genie/` 或任何业务源码。
- **新增持久化文件**：
  - `/Users/chesterjohn/Documents/de-linker/docs/acceptance/2026-11-03/genie/audit.md`（本审计报告，负责人：genie 取证子代理，用途：#548 验收取证归档）
  - `/tmp/genie-sub-heartbeat.txt`（按任务指令追加心跳记录）
- **遗留进程/临时副本**：无任何遗留后台进程、无临时副本或未关闭句柄。
