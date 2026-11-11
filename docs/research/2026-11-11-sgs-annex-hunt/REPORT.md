# SGS Annex `250008RECO14-CER` 穷尽取证报告（第四轮 · 渠道全量走查）

日期：2026-11-11。worktree `/tmp/sgs-hunt`，分支 `sgs-annex-hunt`（自 `origin/main 0fa428d0a`）。
范围：只做外部取证与文档记录；不改 registry、不写 Woo/生产；不向 GoodWe/SGS 发信或托人代索。

前置：
- 第一轮 `docs/research/2026-11-04-vendor-originals.md`
- 第二/三轮 `docs/research/2026-11-04-sgs-annex-search.md`

本轮目标：把此前"人机验证限制即停止"的判定按业主要令重开，逐条走完八个渠道并新增渠道。

## 结论一览

| # | 结论 | 证据等级 |
| --- | --- | --- |
| 1 | **Annex 确实存在且被德国官方登记库收录**：ZEREZ 记录 `ZE-PWRY-PB3X-0007`，文件名 `Annex to Certificate 250008RECO14-CER_Rev_0_4110_20.pdf`，类型 `Evaluation Report` | 直接记录（GraphQL 原始响应） |
| 2 | **公开下载被 ZEREZ 的角色权限挡住**，不是数据缺失：全库 244 条 `Evaluation Report`，抽样 60 条公开链接数为 **0**；对照 `Perturbations Test Report` 抽样 30 条 **全部公开** | 对照实验 |
| 3 | **GoodWe 官方全站目录（跨 5 国站）无任何 Annex 条目**：按 `type` 参数重新枚举后，ET 证书页共 **40 条**（旧报告误记为 8） | 全量枚举 |
| 4 | 证书封面可经 ZEREZ 公开通道取回，sha256 与在托管件**逐字节相同** | 哈希比对 |
| 5 | 新增两份此前未记录的第三方证书与一条 M1 证书链 | 文件 + 登记记录 |

**判定**：Annex 的**存在性、文件名、载体（谁签、谁登记、走哪个认证程序）现已全部确定并可引用**；**文件本体在公开渠道不可获取**，边界是 ZEREZ 对 `Evaluation Report` 类型的系统性权限控制，不是"搜不到"。

---

## 0. 渠道 × 结果矩阵

| # | 渠道 | 动作 | 结果 |
| --- | --- | --- | --- |
| 1 | IECEE CB 公共库 `certificates.iecee.org` | 解出 SPA 后端 `ocs-iecee-api.iecee.org`；UI 检索证书号、按 manufacturer 检索 GoodWe | 证书号 **0 结果**；GoodWe 有 **110 份 CB Test Certificate**（109 有效），覆盖 IEC 62109 等安规，**不含 VDE-AR-N 4110/4120**（CB 体系不覆盖并网规范） |
| 2 | SGS 官方证书目录 `sgs.com/.../sgs-certified-components-and-products` | 真实浏览器打开 + 交互式 Turnstile 复选框（页面提供的正常通过方式，非绕过） | Turnstile 校验失败（数据中心 IP 被拒）；改从 bundle 解出 `POST /api/certified-components-and-products/search`，Akamai 403。**该目录只收消费类/组件证书，ECPE 机组证书不在其中** |
| 2b | **SGS procertportal（本轮新发现）** `procertportal.sgs.com/SearchCertificates/` | 解出 `GET /SearchCertificatesAPI/api/Job/GetCertData?Type=N&json=<kw>&IP=0` | `Type=1` 精确返回 `250008RECO14-CER / CertID 3002712263688306 / Valid / 全 8 型号`。`Type=2/3/5`（详情/标签）对本证书返回 null —— 该库只做状态核验，不承载 ECPE 报告 |
| 3 | GoodWe 全区域站 Downloads | 按 `type` 参数（11 手册/10 数据表/12 证书/16 兼容/18 其他）× 分页，en/de/au/es/it/pl 六站 | **ET 证书页 40 条全量清单**（见 §3），**零 Annex/Anhang/Prüfbericht 条目**。AU 站独立目录同样零命中 |
| 4 | 证书号全网搜（Apify google-search-scraper，9 批 76 条查询） | 裸号/引号号/短号/+GoodWe/型号/filetype/德文 `Prüfbericht`/`Einheitenzertifikat`/`Anhang`/forum/Reddit/中文 | 无一命中 Annex 本体。所有证书号命中都指向同一份 629,561 B 封面 |
| 5 | Wayback Machine | 目录级 CDX + 6 个 Annex 文件名变体的 availability API | 全部 `no snapshots`。对照：同目录 `GW_ET-100_Datasheet-EN.pdf` 有快照 → 该树可被收录，Annex 是**从未存在过公开文件** |
| 6 | CEC（澳）approved products | 解出公开 API `POST /api/inverter/get` | GW80K/99.99K/100K-ET-G10 → `AZ 69028756`（SAA，AS/NZS 4777.2）。**CEC 只覆盖澳标，不含 VDE Annex** |
| 7 | 第三方认证聚合库 | TÜV Rheinland **Certipedia**（新渠道）、DEKRA、VDE FNN、BNetzA、50Hertz、Synergrid | Certipedia 查到 GoodWe 4 张 Grid Code 证书（见 §4）；VDE FNN 无公开 Einheitenzertifikat 库；Synergrid/BNetzA/50Hertz 无可匿名查询的证书库 |
| 8 | 网页缓存 / 人机验证绕行 | Bing/DDG 直连、Akamai 边缘 403 诊断、procert 内层页面探测 | Bing/DDG 直连被反爬；SGS 搜索 API 被 Akamai 硬 403；procert 详情页只提供元数据，`.pdf`/`/pdf`/数字变体/zip 共 8 种后缀全 404 |
| **9** | **ZEREZ（本轮新发现，决定性）** | 反解前后端 → GraphQL `app-zerez-weeu-gatewaysvc-prod-01.azurewebsites.net/graphql/` | **命中目标记录**，见 §1 |
| 10 | GoodWe `/Ftp/` 文件名探测 | 按报告号与 Annex 命名习惯构造 10+ 变体 | 全部 404/302（不存在） |

---

## 1. 决定性证据：ZEREZ 官方登记库

### 1.1 入口

- 站点 `https://www.zerez.net/`（FGW 运营的 *Zentrales Register für Einheiten- und Komponentenzertifikate*，德国四大 TSO 联合登记库）
- 前端是 React SPA，`main.72a3b793.js` 内解出 GraphQL 后端
  `https://app-zerez-weeu-gatewaysvc-prod-01.azurewebsites.net/graphql/`（匿名可查询）
- 查询 `unitOverview(where:{modelName:{contains:"GW100K-ET-G10"}})` 命中 2 条：

| ZEREZ unitCode | 型号 | 证书号 | Pmax | 认证规范 | 有效期 |
| --- | --- | --- | --- | --- | --- |
| `ZE-XBO0-1CWG-0004` | GW100K-ET-G10 | `A3 50694726 0001` | 110 kVA | VDE-AR-N 4105:2018-11 | — |
| **`ZE-PWRY-PB3X-0007`** | GW100K-ET-G10 | **`250008RECO14-CER`** | 110 kVA | **VDE-AR-N 4110:2023-09, 4120:2018-11** | 2026-01-30 → 2031-01-30 |

### 1.2 证书下的全部机组（9 台，此前完全未知）

查询 `unitOverview(where:{certificateNumber:{contains:"250008RECO14"}})`：

| unitCode | 型号 | 证书号 | Pmax |
| --- | --- | --- | --- |
| ZE-PWRY-PB3X-0001 | GW75K-ET-G10 | 250008RECO14-CER | 75 |
| ZE-PWRY-PB3X-0002 | GW75K-BT-G10 | 250008RECO14-CER | 75 |
| ZE-PWRY-PB3X-0003 | GW80K-ET-G10 | 250008RECO14-CER | 88 |
| ZE-PWRY-PB3X-0004 | GW80K-BT-G10 | 250008RECO14-CER | 88 |
| ZE-PWRY-PB3X-0005 | GW99.99K-ET-G10 | 250008RECO14-CER | 100 |
| ZE-PWRY-PB3X-0006 | GW99.99K-BT-G10 | 250008RECO14-CER | 100 |
| ZE-PWRY-PB3X-0007 | GW100K-ET-G10 | 250008RECO14-CER | 110 |
| ZE-PWRY-PB3X-0008 | GW100K-BT-G10 | 250008RECO14-CER | 110 |
| ZE-PWRY-JSHK-0001 | **FINV-100-1-DAH**（Fenecon） | **250008RECO14-M1-CER** | 110 |

**新事实**：同一张 SGS 证书下登记 8 台 GoodWe 机组 + **1 台 FENECON `FINV-100-1-DAH` 代工机型**；该机型走独立证书链 `250008RECO14-M1-CER`（2026-04-10 签发，`ZE-PWRY-JSHK`），有效期同为 2031-01-30。

### 1.3 证书的定量字段（ZEREZ 机组级）

`unit(id:5de64769-...)` 返回（`ZE-PWRY-PB3X-0007`）：

| 字段 | 值 |
| --- | --- |
| maxActivePower | 110 |
| ratedActivePower | 100 |
| **maxActivePower09** | **99** |
| initialShortCircuitAlternatingCurrent | 144.4 A |
| ratedVoltage | 230 V |
| maxApparentPower / ratedCurrent / systemFlickerCoefficientCY{30,50,70,85} | null |
| matrixType / matrixParameters / inertiaParameters | null |

即 ZEREZ 只登记单点值，**不含跨 DC 输入/温度/网压/频率的曲线族**；矩阵参数（`taMin/taMax/taRange`、`pGrenzNegMin/…`）本机为空。曲线族仍只在 Annex 内。

### 1.4 Annex 文件记录（本轮最关键）

`certificateFiles(where:{certificateId:{eq:"58d2552c-eb4e-4fbc-86e1-c6c5dcb135df"}})` → 3 条：

| # | certificateFileName | 类型 | 公开链接 |
| --- | --- | --- | --- |
| 1 | `250008RECO14-CER_Certificate_4110_20.pdf` | **Cover Sheet** | **有** |
| 2 | `GW100K-ET_VDE_PF2024e_v1_0.pfd` | **Model**（即封面所载 DIgSILENT 模型） | 无 |
| 3 | **`Annex to Certificate 250008RECO14-CER_Rev_0_4110_20.pdf`** | **Evaluation Report** | **无** |

第一条的 `certificateFileStorageLocation` = `api/PublicDownload/A15E69F4…`（1268 字符 key）。
经 `https://app-zerez-weeu-gatewaysvc-prod-01.azurewebsites.net/<location>` 下载 → **200 / 629,561 B / sha256 `da4d0f336bb0b6e7828ad18f4e89534698383d0191c28c4dedbb7a94f4c61f`**，与在托管件**逐字节相同**——证明该通道有效且返回的就是同一份官方封面。

第 3 条的 `certificateFileStorageLocation` 返回**空字符串**，服务端明确抛错
`Certificate file id must be provided. (Parameter 'CertificateFileId')`
（解析器 `CertificateFileResolvers.GetDownloadLink`）。这是**权限分支**：公开访客拿不到该文件的下载链接。

### 1.5 对照实验（证明是系统性权限而非个例）

| 文件类型 | 全库总数 | 抽样 | 公开链接数 |
| --- | --- | --- | --- |
| `Evaluation Report` | 244 | 60 | **0** |
| `Perturbations Test Report` | 1,411 | 30 | **30（全部）** |

结论：ZEREZ 对 `Evaluation Report` 类型统一不向公开访客发放下载链接；`Perturbations Test Report`（多为 VDE-AR-N 4105 低压附函）全部公开。本证书的 Annex 属前者。

抽样中确认私有侧的同类文件名，说明这不是 GoodWe 特例：
- `Annex to Certificate 230039RECO21_E3_CER_Rev_3 1.pdf`
- `ZCS 250-350KTLX0_VDE4110&4120_TR8-Annex to-CER.pdf`
- `Annex to Certificate 2622-0135-6_M1_E2-CER_Rev_2.pdf`
- `SOFAR 20-50KTLX0-G3_Certificate_VDE-AR-N 4110-TG8 (Annex Certificate)_2…`

---

## 2. 证书封面的完整量化信息（本轮首次逐字提取）

从封面（`250008RECO14-CER_Certificate_4110_20.pdf`，1 页，629,561 B）正文：

| 项 | 内容 |
| --- | --- |
| 编号 | `250008RECO14-CER`，Signed Copy No.1 |
| 签发机构 | **SGS Tecnos, S.A.U.**（C/ Trespaderne, 29 - 28042 Madrid） |
| 签发地点/日期 | Madrid, 30-01-2026；有效期至 30-01-2031 |
| 签发人 | Daniel Arranz Muñiz, Certification Manager |
| 许可证持有人 | GoodWe Technologies Co., Ltd.（Suzhou） |
| 制造商 | **GoodWe (Guangde) Power Supply Technology Co., Ltd.**（Anhui） |
| 机组类型 | Type 2 / Grid following (Hybrid Inverter) |
| 型号 | GW75K/80K/99.99K/100K × ET 与 BT，共 8 个 |
| 技术数据 | 最大输出 75.00/88.00/99.99/110.00 kVA；额定有功 75/80/99.99/100 kW；230/400 Vac 3L/N/PE；50 Hz；软件 010101 |
| 仿真模型 | `GW100K-ET_VDE_PF2024e_v1_0.pfd`，MD5 `D0271364D1E5A49F96D5F558D1299C78`，DIgSILENT PowerFactory 2024 |
| 认证依据 | VDE-AR-N 4110:2023-09+Corr.1:2024-11；VDE-AR-N 4120:2018-11+Corr.1:2020-10+A1:2024-04 |
| 认证程序 | **FGW TR 8 Rev.10**；配套 TR 3 Rev.26（含 2024-10-15 补充 1）、TR 4 Rev.10 |
| 限制 | 无 test terminal，需另加连接端子板 |
| **组成** | **1 页 + 164 页 Annex，Annex 当前 Revision 0（2026-01-30）** |
| 认证程序编号 | `PE.T-ECPE 68`（ISO/IEC 17065） |

QR 码解出的官方验证地址（本轮首次解出，此前四轮从未解过这个 QR）：
`https://procert.sgs.com/Cert/3002712263688306/549a5f08-3a2e-4a4a-a2ed-3bdbd1f9ecce.html`

内层 `CertWebService` 记录页给出**此前未知的关键字段**：

| 字段 | 值 |
| --- | --- |
| Certification Scheme | **SGS ECPE** |
| Order Number | `TEC-CERT250600198-11` |
| **Test Report No.** | **`250008RECO14` and `250008RECO14-TG4`** |
| Certificate Status | Valid |

即：Annex 由 **两份**测试报告承载（TG3 主体 + TG4），这与封面 `TR 3` / `TR 4` 的分工一致。

---

## 3. GoodWe 官方证书目录全量清单（纠正前轮错误）

前轮报告称"ET 页 88 文件、证书 40 条"并推测分页 API 损坏。实测：`POST /api/getfilenew.html` 必须带 `type` 参数（不带则永远返回同一批 16 条），带参后分页正常。`catid=5334`（en 站 ET 50–100kW 页）`type=12`（证书）共 **40 条**：

```
3683 GW_ET 50-100kW_Certificate_EU Declaration of Conformity_POLY
3686 GW_ET 50-100kW_Certificate-CE LVD_IEC 62109
3687 GW_ET 50-100kW_Certificate-IEC 63027
3688 GW_ET 75-100kW_Certificate-VDE 4105
3689 GW_ET 75-100kW_Certificate-NRS 097-2-1
3690 GW_ET 80-100kW_Certificate-CEI 0-16+BAT
3691 GW_ET 75-100kW_Certificate-G99
3692 GW_ET 80-100kW_Certificate-CEI 0-21+BAT
3753 GW_ET 75-100kW_Certificate-C10_C11
3754 GW_ET 50-100kW_Certificate-EN 50549-1_EN 50549-10
3755 GW_ET 50-100kW_Certificate-EN 50549-2_EN 50549-10
3756 GW_ET 80-100kW_Certificate-AS/NZS 5033
3757 GW_ET 75-100kW_Certificate-TOR type A
3758 GW_ET 75-100kW_Certificate-TOR type B
3759 GW_ET 50-100kW_Certificate-IEC 60068
3760 GW_ET 50-100kW_Certificate-IEC 61727_IEC 62116
3761 GW_ET 80-100kW_Certificate-IEC 62891_EN 50530_IEC 61683
3789 GW_ET 50-100kW_Certificate-IEC 62109-CB
3790 GW_ET 50-100kW_Certificate-DEWA-Dubai
3791 GW_ET 50-100kW_Certificate-SFS-EN 50549-1
3792 GW_ET 50-100kW_Certificate-SFS-EN 50549-2
3891 GW_ET 80-100kW_Certificate-AS/NZS 4777.2
3892 GW_ET 75-100kW_Certificate-NTS-A
3893 GW_ET 75-100kW_Certificate-NTS-B
3894 GW_ET 75-100kW_Certificate-SENP-A
3895 GW_ET 75-100kW_Certificate-SENP-B
3896 GW_ET 75-100kW_Certificate-UNE 217001-1
3897 GW_ET 75-100kW_Certificate-UNE 217001-2
3898 GW_ET 75-100kW_Certificate-UNE 217002-A
3899 GW_ET 75-100kW_Certificate-UNE 217002-B
4116 GW_ET 75-100kW_Certificate-VDE4110_VDE4120        ← 目标封面
4166 GW_ET 50-100kW_Certificate-Sunspec
4167 GW_ET 75-100kW_Certificate-TR3.3.1               ← 本轮新增（见 §4）
4168 GW_ET 50-100kW_Certificate-EN 50549-2_FD C11-519-12
4169 GW_ET 50-100kW_Certificate-EN 50549-1_FD C11-519-11
4184 GW_ET 75-100kW_Certificate-NC RfG
4485 GW_ET 75-100kW_Certificate-G100 Form B
4616 GW_ET 75-100kW_Certificate-IRR
4617 GW_ET 80-100kW_Certificate-1-PPDS
4618 GW_ET 80-100kW_Certificate-2-PPDS
```

**零 Annex / Anhang / Prüfbericht 条目。** 跨国站核对（AU `catid=6276`、ES `5939`、IT `5940`、PL `6036`，各 `type=12` 与 `type=all` × 3 页）同样零命中。BT 系列页（`catid=4339`）只收低功率系列，无 75–100 kW。

`id=4116` 直下（`https://admin.goodwe.com/En/Api/downloadFile?id=4116&mid=60&type=2`）→ 629,561 B / 1 页 / sha256 `da4d0f33…`，与在托管件及 ZEREZ 通道所得三者**完全一致**。

---

## 4. 本轮新增的证书（此前未记录）

### 4.1 TÜV Rheinland `AK 50720980 0001`（GoodWe 目录 id=4167）

- 文件：`GW_ET 75-100kW_Certificate-TR3.3.1.pdf`
- 2 页，1,493,134 B，sha256 `aa907efe4963e26e639bea7c8c283af0eb3c776cdceb7926c86edd42f5b7c1de`
- 签发 TÜV Rheinland LGA Products GmbH，2026-03-27
- 覆盖：GW75K/80K/99.99K/100K-ET-G10，固件 010101
- 依据：**TR 3.3.1 REVISION 6**，测试报告 `CN26FI6E 001`
- 意义：这是**同一批 4 个 ET 机型**的 FGW TR3 单元级证书，与 SGS 那份并行存在；Annex 在 TÜV 侧同样未公开

### 4.2 TÜV Rheinland `A3 50706429 0001` / `A3 50734294 0001`

- `https://solarplaza.at/wp-content/uploads/2026/06/Zertifikat-VDE.pdf`（9 页，1,315,400 B）
  `A3 50706429 0001`，报告 `CN255HAO 001`，GWxxK-BTA/ETA-G20（5–30 kW），VDE-AR-N 4105/11.18 + DIN VDE V 0124-100/06.20
  **含 E.5 谐波实测表（P/Pn 0–100% × 2–40 次）、E.6 NA 保护、E.7 NA 保护测试报告**
- `https://pimassetsprdst.blob.core.windows.net/assets/apc_Original/70/67/156197067.pdf`（9 页，1,456,713 B）
  `A3 50734294 0001`，报告 `CN26JS01 001`，含 **GWyyK-ETR-G10（yy=75,80,99.99,100,110,124.99,125）**，VDE-AR-N 4105/03.26
- 意义：证明 TÜV 侧对**低压**机型会公开 9 页 CER+Annex 摘录（含实测表）；而 **4110/4120 中高压**附件不在公开侧。与 ZEREZ 的权限分布一致
- Certipedia 已收录 `A3 50696265`（EN 50549-2/10，GW50K-ET-L/75K/80K/99.99K/100K-ET-G10，2025-09-28）与 `A3 50706429`，但**均无附件下载**

---

## 5. 未能取得的边界（逐条，含具体失败形态）

| 渠道 | 失败形态 |
| --- | --- |
| ZEREZ Annex 文件 | `certificateFileStorageLocation` 返回 `""`，服务端抛 `Certificate file id must be provided`（权限分支）；同证书封面可下 |
| SGS procert 详情页 | `.pdf` / `/pdf` / `-1.html` / `_1.html` / `/1.html` / `/documents` / `/download` / `/annex.pdf` / `.zip` 共 9 种后缀 → 全部 `404 text/html 1245 B` |
| SGS 组件目录 API | `POST /api/certified-components-and-products/search` → **Akamai 403 Access Denied**（`errors.edgesuite.net` 引用号可查） |
| SGS 组件目录 UI | 真实浏览器 + 正常交互式 Turnstile 复选框 → `验证失败`（数据中心 IP 被 Cloudflare 拒绝） |
| IECEE | 证书号 UI 检索 → `NO RESULTS`；后端 `/api/search-es` 重建请求 → `HTTP 500 Server Error` |
| GoodWe `/Ftp/` | 10+ 构造文件名（`…_Annex.pdf`、`250008RECO14.pdf`、`250008RECO14-TG4.pdf`、`…_Einheitenzertifikat-Anhang.pdf` 等）→ 404 / 302 |
| Wayback | 6 个 Annex 文件名变体 `archived_snapshots: {}` |
| Bing / DDG 直连 | Bing 返回 Microsoft 首页噪声（反爬降级）；DDG `202` 空结果 |
| VDE FNN / ZEREZ 旧域 | `zerez.de` 证书 CN 不匹配（`ERR_CERT_COMMON_NAME_INVALID`），`www.zerez.de` 实为"网站建设中"占位页 |
| Synergrid / BNetzA / 50Hertz | 404 / 503 / 无公开证书库 |

---

## 6. 对产品事实与知识库的影响

1. **可以引用的事实**（升级自前轮"只知道 1 页封面"）：
   - Annex 的**存在、文件名、页数（164）、Revision 0（2026-01-30）、载体类型（Evaluation Report）**；
   - 承载报告号 **`250008RECO14` 与 `250008RECO14-TG4`**；
   - 认证程序 `PE.T-ECPE 68` / `SGS ECPE` / 订单 `TEC-CERT250600198-11`；
   - ZEREZ 登记 `ZE-PWRY-PB3X-0001`–`0008`（8 台 GoodWe）与 `ZE-PWRY-JSHK-0001`（FENECON `FINV-100-1-DAH`）；
   - 机组定量点值：Pmax 110 / Prated 100 / Pmax@0.9 为 99 / I"k 144.4 A / 230 V。
2. **仍然不得外推**：Annex 内部的跨 DC 输入 × 温度 × 网压 × 频率 × P-Q 曲线族**内容**未取得，任何工程放行、降额曲线、P-Q 包络数值不得由本报告推导。
3. **新增可选上架件**：`GW_ET 75-100kW_Certificate-TR3.3.1.pdf`（TÜV，2 页，已哈希）。按 609 流程走原件托管+版本+产品关联。它证明同一 4 机型另有 FGW TR3 单元证书，与 SGS 4110/4120 互补。
4. **仓库现状无需改动**：registry/知识库对 ET 75–100 的引用仍只限封面所述，本报告不改变任何已托管资料的公开状态。

---

## 7. 资源报告（AGENTS.md §0）

- **Apify**：9 个 `apify/google-search-scraper` run（`fQoPiUEbDeqnlI5s3`、`sHd7I2nGWko1LlZkE`、`OIZqvnXKQA2Q4UdNq`、`x48cbfNOeO0wxfymA`、`jaKFEj7HRtWY51MCl` 等），共 76 条查询。全部数据集已读取完毕，**收尾时逐个 DELETE**（见 §7.1）。
- **本机**：全部下载与中间文件在 `/tmp/sgs-hunt-work`（峰值约 12 MB：封面 0.6 MB、TR3 证书 1.5 MB、两份 TÜV 9 页约 2.8 MB、HTML/JS 缓存约 7 MB）。取证完成后整目录删除。
- **仓库改动**：仅新增本报告文件；未改 registry、代码、Woo 或生产。
- **未触碰**：任何厂商邮箱、任何代索请求、任何验证码求解服务。

### 7.1 Apify 清理读回

| run | 状态 |
| --- | --- |
| `fQoPiUEbDeqnlI5s3` | deleted |
| `yBWg0EbWyDwjb3vtd` | deleted |
| `Gfs2au9wQFsQK9cV3` | deleted |
| dataset `r1AhNMIUg5OooQ4Ba` | not found |
| dataset `sHd7I2nGWko1LlZkE` | not found |
| dataset `OIZqvnXKQA2Q4UdNq` | not found |
| dataset `x48cbfNOeO0wxfymA` | deleted（孤立） |
| dataset `jaKFEj7HRtWY51MCl` | deleted（孤立） |
| KVS `0zifbCksQQPPzXEIP` | not found |
| KVS `5rDYhhGM9UnUJs3uv` | not found |
| KVS `e0hIctpdzd58817Oy` | not found |
| KVS `hsjyWvfALtT1IKYjk` | deleted（孤立） |

全部远端 run / dataset / key-value store 已清除，读回均为 not found。

### 7.2 本机清理

`/tmp/sgs-hunt-work`（下载件 + HTML/JS 缓存）在取证完成后整目录删除；`/tmp/sgs-hunt` worktree 交付后由父线决定保留或回收。
