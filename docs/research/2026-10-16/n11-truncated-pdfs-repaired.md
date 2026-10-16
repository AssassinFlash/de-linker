# N11：线上 3 份截断 PDF 补传原件与重索引（2026-10-16）

来源：`docs/research/2026-10-09/embedding-bakeoff.md` §1 失败清单（3 份 hosted PDF 的字节本身截断，无 `%%EOF`）；台账 `.scratch/debt-sweep/LEDGER.md` N11。

三份附件的线上字节与 bake-off 记录逐字节一致（3538700 / 3014411 / 1163020），确认是托管件本身截断，不是下载中断。

## 0. 结论

三份截断件**各自**是 SAJ 官网原件的**字节前缀**（截断件 == 原件 `[:截断长度]`，逐字节），即同版同文件的被截断上传；原件已按同一文件名写回线上同一路径（URL 不变），附件记录与 URL 未动，仅把 `_wp_attachment_metadata.filesize` 从截断值改为真实值。三份手册已进索引。

## 1. 截断件取证（`/tmp/n11/`，2026-10-16 从线上重新下载）

| 附件 | 文件 | 线上字节 | sha256（截断） | 取证 |
|---|---|---|---|---|
| 1277 | `hs2-as2-manual-en.pdf` | 3,538,700 | `2927d72f9ec7b92f…` | 无 `%%EOF`；Poppler "Couldn't read xref table"；头部 `/Type/Pages /Count 42`；封面 **THREE PHASE** ALL-IN-ONE / HS2-5~10K-T2 / AS2-5~10K-T / **V0.2** |
| 1278 | `hs2-manual-3-6k.pdf` | 3,014,411 | `49a97350a2b72761…` | 无 `%%EOF`；同行错误；头部 `/Count 43`；封面 **SINGLE PHASE** ALL-IN-ONE / HS2-3~6K-S2 / AS2-3~6K-S / **V0.0** |
| 1461 | `HS3-SinglePhase-EU.pdf` | 1,163,020 | `94b6b77b485073ad…` | 无 `%%EOF`；线性化 PDF 头部自述 `/Linearized 1 /L 1691898 /N 4`（原件 1,691,898 B、4 页）；封面 "HS3 Single Phase All-in-One Solution" |

**两份 HS2 文件不是同一手册的两个截取**：`hs2-as2-manual-en.pdf` 是三相 5~10K（42 页），`hs2-manual-3-6k.pdf` 是单相 3~6K（43 页），两份不同文档（页数、机型、版本均不同）。

## 2. 原件来源与同版判定

判定方法：**字节前缀相等**——截断件恰好是原件的第一个 N 字节（N = 线上字节数）。压缩流与对象逐字节相同，不是"标题版本相同"的弱证据，而是同一文件的直接证明。

| 截断件 | 原件（下载源） | 原件字节 | 页 | 原件 sha256 | 前缀判定 |
|---|---|---|---|---|---|
| `hs2-manual-3-6k.pdf` | `https://img.saj-electric.com/file/Manual%20%20HS2-AS2-3-6K-S2-20230112085130750.pdf` | 11,089,345 | 43 | `7ce4dc9e4ee71035…` | 截断 3,014,411 B == 原件前 3,014,411 B（100%） |
| `hs2-as2-manual-en.pdf` | `https://img.saj-electric.com/file/Manual%20HS2-AS2-5-10K-T2-20230112085420716.pdf` | 8,447,134 | 42 | `f9c4435a133c0c22…` | 截断 3,538,700 B == 原件前 3,538,700 B（100%） |
| `HS3-SinglePhase-EU.pdf` | `https://img.saj-electric.com/file/HS3%20All-in-One%20Solution--%E8%8B%B1%E5%9B%BDEN-0923-20241024062333504.pdf` | 1,691,898 | 4 | `49b6ed45da22b359…` | 截断 1,163,020 B == 原件前 1,163,020 B（100%） |

- 两份 HS2 手册是 2023-01-12 同批上传（时间戳 085130750 / 085420716）；pdfinfo Title 为 `30301763 HS2-AS2-3-6K-S2说明书（EU）V0` / `30301764 HS2-AS2-5-10K-T2说明书（EU）V0`（Word 内部标题未随封面版本更新，封面分别为 V0.0 / V0.2，与截断件封面一致——前缀相等已含封面字节）。
- HS3 那份的原件 `/L 1691898` 与线性化头的声明完全吻合，且 `CreationDate 2024-10-24` 与截断件内部 `LastModified(D:20240924183249)` 同一批次（文件名 `0923`）。
- 备选件不符合同版，未使用：UK/IE 与 North 的 hubfs datasheet（680,716 / 684,375 B，与截断件在第 16 字节即分叉）——是另外的版面/版本，不是被截断上传的那一份。
- HS2 三相原件的镜像（smv-energy.bg，同名文件）与 SAJ 原件 sha256 相同（`f9c4435a…`），互为旁证。

## 3. 补传（线上写入）

- 备份截断件：`~/n11-truncated-backup-20261016/`（含 `backup-sha256.txt`、`attachment-metadata-before/after.txt`）。
- 写回路径：`~/domains/de-linker.com/public_html/wp-content/uploads/2026/07/<同名>`（scp 覆盖，`_wp_attached_file` 与 URL 不变）。
- 读回校验（服务器 sha256）：1277 `f9c4435a…`（8,447,134 B）、1278 `7ce4dc9e…`（11,089,345 B）、1461 `49b6ed45…`（1,691,898 B）；文件属主/权限保持原样。
- HTTP 读回：三份 `Content-Length` 8417134 / 11089345 / 1691898（原为截断值）。
- 附件记录：ID、URL、标题、`modified_gmt` 未动；仅 `_wp_attachment_metadata.filesize` 由截断值改为真实值（`{"filesize":3538700}` → `{"filesize":8447134}` 等），使媒体库与索引管线的尺寸校验一致。

## 4. 重索引与发布

`just index`（2026-10-16）：

| 项 | 修复前（`20261010T082155Z`） | 修复后（`20261016T072222Z`） |
|---|---|---|
| 文档 / 入索引 / 失败 | 383 / 380 / 3 | 383 / **383 / 0** |
| 页 / 有块 | 11,697 / 11,613 | **11,786** / 11,702 |
| 块 | 32,852 | **33,172** |
| 模型 | gemini-embedding-2（3072 维） | 同 |
| 索引 sha256 | — | `ad9d0807ee1c58bd…`（465,891,328 B） |

增量恰好对上：+89 页 = 43+42+4，+320 块 = 157+149+14。三份手册的 coverage 全部 `indexed`、`pages_with_chunks` = 总页数（43/42/4），无空页。

**发布**：`ops/publish_index.py publish … --host linker-services` → `/opt/linker-genie/index/current -> 20261016T072222Z`，`sha256_ok: true`。读回：VPS 上 documents 383 / indexed 383 / chunks 33,172，三份手册 43/42/4 页、157/149/14 块。

**检索抽查**（在 VPS 上用服务自己的 venv 与 `linker_genie.retrieval.DocumentIndex` 跑，查询向量经 OpenRouter）：`HS2 single phase installation clearance` → 首选 `hs2-manual-3-6k.pdf` p.14；`HS3 single phase battery modules` → 前三名全部 `HS3-SinglePhase-EU.pdf`。

**`just eval`（984 问，出厂路径）**：召回@5 51.7%、页码正确率 83.1%（阈值 90%/95%，与 #10 记录的整体差距同量级）。这一 −1.1pp 是**加内容**的效果，已定位到字节：

- 用今天的代码与编码器把旧索引（`20261010T082155Z`）重跑一遍出厂路径 → 召回@5 **52.85%**，与旧 `eval.json` 记录的 52.85% 逐位相同——**harness 与查询编码器没有变**，旧数字可复现。
- 新旧索引逐块对比：380 份共有文档的 chunk 集合**逐字节相同**（文档行也无变化），只有三份手册是新增（+320 块）；抽样 1,000 个共有 chunk 的向量**逐字节相同**；商品圈定相同（76 个黄金型号里 63 个有映射、878/984 有商品）。
- 因此 52.85% → 51.73% 的来源只有一个：三份手册的 320 块进了候选池，把少数问题的金页挤出前 5。页码正确率未动（83.06% → 83.12%）。
- 三份手册**不在黄金集的证据文档里**（逐行核过 984 行 `evidence`，0 命中），没有一条问题"本该由它们回答"，所以这一变化不是"修好了本该命中的题"，而是新内容参与竞争的正常代价。

### 发现的回归（已修，`services/genie/index/build.py`）

构建管线把 `embedder.model` 记为索引的 `embedding_model`。`GeminiEmbedder.model` 是**供应商线上名**（OpenRouter 叫 `google/gemini-embedding-2`，由 #99 的"只走 OpenRouter"改动引入），而 `retrieval.query_encoder` 按 **provider-neutral 名**（`gemini-embedding-2`）解析，指纹里也一直是后者。后果：任何用当前代码新建的索引，打开时 `query_encoder` 返回 None → **dense 路径静默退化为 keywords**（bake-off 采信的出厂路径失效）。10-10 的构建早于 #99，所以旧索引不受影响；本次重建第一次暴露它——第一版重建（`20261016T065329Z`）的 eval 就是 keywords-only（27.0%/82.6%），与旧索引的 dense 结果（52.8%）对照即证据。

修法：新增 `index/build.py:model_identity(embedder)`，索引记录 `fingerprint["model"]`（没有才回落到 `.model`），三处写入点（`embed_corpus` 的 meta/manifest、`build` 的 meta）都改用它。对开源模型是无操作（两者相同）。回归测试 `tests/test_build.py::test_the_index_records_the_encoders_identity_not_its_wire_name`（`WireNamedEmbedder`：wire 名 `vendor/counting`、身份 `counting`）。

**注意**：VPS 上仍留着第一版重建 `20261016T065329Z`（KEEP=3 策略保留为回滚目标）——它的索引 meta 带这个缺陷，**回滚到它会丢掉 dense 路径**（keywords-only）。是否清理由发布通道决定，本轮未动。

## 5. 留给业主的一件事：线上客户面检索仍是空的（与 N11 无关，但会被"检索恢复"的问法撞上）

三份 PDF 修好、索引重建并发布到 VPS 之后，**线上客户面（Genie → `linker/search-knowledge`）仍然返回空**：

- 实测：`GET /wp-json/wp-abilities/v1/abilities/linker/search-knowledge/run?input[query]=…&input[lang]=en` → `{"hits":[]}`（HTTP 200）。
- 原因：PHP 侧 `SearchKnowledge` 读的是 WordPress 库里的 `wp_genie_*` 表（位置 A 的形态），线上库里**没有这些表**——`SHOW TABLES` 59 行、`LIKE '%genie%'` 0 行，`wp options` 里只有 `linker_genie_url`。也就是说 #16/#16i 把索引导进 MariaDB 只做过本地实例（`linker_t16`/`linker_t16i`），**生产库从未导入**。
- VPS 的 SQLite 索引（本轮发布的这份）目前只有 `index/eval`、`tools/faq/generate.py` 和检索测试在读；`linker_genie.agent` 的工具调用全部经 HTTP 打到 WordPress ability，服务本身不在请求路径里读这份 SQLite。
- 要把线上客户面接上，需要一条 N11 之外的写入：`just index --mariadb wp_` 产出 `index-mariadb.sql`（约 1.2 GB）并导入共享主机生产库（备份后读回）。这是**生产库的大体量写入**，超出本票授权（本票授权的是补传附件与索引发布通道），故不动，列在此处待业主裁定。

## 6. 复现

```bash
# 取证（截断件已不在线上；用备份的截断字节与厂商原件比对前缀）
scp hostinger-de-linker:~/n11-truncated-backup-20261016/hs2-manual-3-6k.pdf /tmp/n11/truncated-3-6k.pdf
curl -o /tmp/n11/orig-3-6k.pdf 'https://img.saj-electric.com/file/Manual%20%20HS2-AS2-3-6K-S2-20230112085130750.pdf'
python3 -c "d=open('/tmp/n11/truncated-3-6k.pdf','rb').read(); o=open('/tmp/n11/orig-3-6k.pdf','rb').read(); print(len(d), len(o), d==o[:len(d)])"   # 3014411 11089345 True
# 线上现状（三份都应是完整件）
for f in hs2-manual-3-6k.pdf hs2-as2-manual-en.pdf HS3-SinglePhase-EU.pdf; do
  curl -sSI "https://de-linker.com/wp-content/uploads/2026/07/$f" | awk -v f="$f" '/^content-length/{print f, $2}'; done
# 重索引与发布
just index && just eval
uv run --project services/genie python services/genie/ops/publish_index.py publish ~/de-linker-data/index/builds/20261016T072222Z --host linker-services
```

## 7. 台账与代码

- 代码改动（**未提交**，在 main 工作区）：`services/genie/index/build.py`（`model_identity` + 三处调用）、`services/genie/tests/test_build.py`（`WireNamedEmbedder` + 一条回归测试）。
- 验证：`just py-check`（ruff/format/mypy 全部项目）绿；`just py-test` 全绿（genie 162、engine 112、local 92、migrate 93+8 skip、faq 20）；`just eval` 见 §4。
- 备份：`~/n11-truncated-backup-20261016/`（截断件 + 前后元数据 + sha256 清单）。

