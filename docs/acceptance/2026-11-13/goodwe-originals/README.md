# GoodWe BAT-C 官方原件全量取证（2026-11-13）

来源：GoodWe EMEA 官方下载中心 BAT Series 60-112kWh 专属页
（`https://emea.goodwe.com/download-bat-series-60-112kwh`），文件清单经其自身 XHR
`POST /api/getfilenew.html`（`catid=4542&type=all&country=9`，翻页 1-7）取得
**54/55 项**的 id-文件名对照（清单尾部一项格式变体未匹配，非关键）。
下载经官方端点 `https://admin.goodwe.com/Api/downloadFile?id=<N>&mid=60&type=2`。

## 我方托管件定案（逐字节一致，无需替换）

| 我方托管件 | 官方 id | md5 |
| --- | --- | --- |
| GW_BAT-C-60-112kWh_User-Manual-EN_V1.0.pdf（2026-10 上传） | 4626 | 5527df2c3fdf671a18f55be7b7162cdd（87 页） |
| delinker-goodwe_batc60-datasheet.pdf（2026-07 上传） | 3301 | acb5cd27083f2c750df1cde9f7fab716（2 页） |
| Quick-Installation-Guide-POLY_V1.7（2026-10 上传） | 4663 | 官方件为纯图像无文字层；我方 V1.7 带完整文字层，同代更优，不换 |

## 新取得原件（我们未托管；sha256）

| id | 文件 | bytes | sha256 |
| --- | --- | --- | --- |
| 3749 | BAT-C 60-112kWh Maintenance Manual EN | 2895447 | 70b360058411ccbae62cf388502331c1022a1f72304a10e795091b338caf8501 |
| 3254 | EU Declaration of Conformity (POLY) | 872605 | 0ad8ac3f70f0552beabf501222a9711f78c4f46341b5f013e55d4f427da6f6c2 |
| 3257 | Cert IEC62619/IEC63056/EN62477 — TÜV R 50669810 0001, 报告 CN25NR28 001 | 1544674 | ebe5ddd559c2629f7ccfc0b7f90a63ea709c657be6453cf2bbe5020f08292fa2 |
| 3256 | Cert CE LVD | 1469556 | 060c100c25b6896a5dced8452bcf4d7260502df05144e4bccca2484627bccf64 |
| 3255 | Cert IEC62477 (102.4-112.6kWh) | 421081 | 0af4212d59c32cca3db4dd1697fe798d83484fa19e59fb04efa1df6e592c158c |
| 3698 | Cert IEC 62040 | 1395720 | dd4e40ef588d6e59117d3b694f2bc5983b32258fa8a6d9ecb95ee1bf051173fb |
| 3699 | Cert VDE 2510-50 | 1463893 | 7a43b31b355a5e3264c80d47e99665f94751859ec97260040dce974da9087306 |
| 4663 | Quick Installation Guide POLY（纯图像版） | 3079675 | 2e539846bb89ee755d4cc717e6063d945467a6016cf1f44868690ebc9cf49c70 |
| 4740 | Products Suitable for Coastal Areas EN | 320742 | b8b8ae4c6f36c901b6ad495e3734079e46f120ace668658b7f8c28126ad831df |
| 4809 | Product Coastline Installation Statement EN（定案见下节） | 637758 | eadffedb6dbcecdbf7eff8370b3bb9f2a59307ca9f6f528140cc7976a815b22d |

## 4809 定案（OCR 全文核读，2026-11-13）

标题 **Goodwe Product Coastline Installation Statement**（Statement Letter），
GoodWe Solution Center 负责人 Frank Li（李翔）签发，日期 2026-11-09，无证书/文件编号。
引用标准 ISO 12944-2:2017；声明产品满足 C4/C5 防腐等级，但**禁止安装于海岸线 500m
内的 CX 环境**，500m 内适用产品指向官方清单 4740（GW_Products-Suitable-for-Coastal-Areas-EN.pdf）。
全文不含任何具体型号列表（无 BAT-C 型号）→ **跨产品通用声明函，不作为 BAT-C
产品文档挂附件**（与 publication-receipt.json 的 skipped 判定一致）。

## 与 PDP 的关系

- 3257/3255/3256/3698/3699 是 BAT-C 产品页 Safety 行所列标准的官方原始背书
  （TÜV 证书族）。发布入 Woo 后可在产品页文档区引用。
- 3749 维护手册是全新文档类型，客户价值最高，为下一发布批首选。

## 后续（609 流程）

3749/3257/3256/3255/3698/3699 已于 2026-11-13 发布为媒体附件 **8736–8741**
并写入产品 1954/1955 的 `_linker_documents`（15/17 行），EN/DE 四页 + feed +
Genie 索引读回通过——明细见 publication-receipt.json 与 goal-state-ledger。
临时取证件目录 `/tmp/gw-batc/`（127MB）已回收。

注：上一会话子代理（agent-34）所称"ETR 3 页原件"未能在官方清单中对应任何
文件——清单中不存在该名称；该线索按不可证实处理。搜索全程 Apify（token
soexn/org507）+ 官方 API 直调。
