# 原厂原件缺口批次取证报告（vendor originals for #548）

日期：2026-11-04。分支 `research/vendor-originals`（自 main `8c9e6d809`）。
范围：只做外部取证与对照，不改 registry、不写 Woo/生产。所有下载仅在 `/tmp/vendor-originals`，哈希后已全部删除（见 §6 资源报告）。

四个目标：SGS 164 页 Annex、GoodWe BAT-C 60–112 kWh 定量曲线、ET 75–100 kW 运行包络、SAJ HS3/CB2 端子图。

结论一览：

| # | 目标 | 结论 |
| --- | --- | --- |
| 1 | SGS Annex（`250008RECO14-CER`） | **公开副本未取得**：GoodWe 官方下载中心与德国分销 BayWa 都只发布与在托管件字节相同的 1 页封面；SGS 证书目录的实际交互搜索受人机验证限制。不得外推 164 页 Annex 的内容。 |
| 2 | BAT-C 60–112 kWh 定量资料 | **取得**：GoodWe 官方 `GW_BAT-C 61.4-112.6kWh_User Manual-EN`（V1.0, 2026-10-10，87 页）。有全系列定量参数表（含 92.1 kWh 型号、最大 0.9C/1.1C、180/220 A、循环寿命、效率），**无绘制的 SOC×温度降额曲线**（手册脚注只声明降额存在）。 |
| 3 | ET 75–100 kW 运行包络 | **部分**：所持三份文档（数据表 V2.1、Solution Manual V1.3、User Manual V1.2）经与 GoodWe 官方下载中心逐字节比对**均为当前版**；三份均只定性提及降额，定量多维包络只在未公开的 SGS Annex 测试报告里。 |
| 4 | SAJ HS3/CB2 端子图 | **确认所持即当前官方原件**：HS3 V4 与 CB2 手册均与 saj-electric.com hubfs 官方文件字节相同，且无更新版本；两份手册自身已含最全的公开端子/针脚定义，不存在更全的独立端子图。 |

---

## 0. Apify 使用记录（外部检索按 AGENTS.md §6 先走 Apify）

Actor 统一为 `apify/website-content-crawler`（浏览器渲染 Firefox、`maxCrawlDepth=0`、不递归、不注册、不联系厂商）。3 个 run 全部 SUCCEEDED，结束后 12 个远端资源（run+dataset+KVS+queue ×3）全部 DELETE 204。

| run | 目的 | 结果 |
| --- | --- | --- |
| `b4ubNDmBefxu96eJV` | 渲染抓取 4 个官方页：`en.goodwe.com/au/download-bat-series-60-112kwh`、`en.goodwe.com/au/download-et-series-50-100kw`、`saj-electric.com/services-support-download`、`saj-electric.com/hs3` | 取得列表首页：BAT-C 列表含 User Manual（2026-10-14）与证书条目；ET 列表 85 文件、SAJ 下载中心仅首屏（懒加载） |
| `4OznL9WPrIMb4k3Cv` | 同两个 GoodWe 列表页 + injectPageFunction 自动滚动 | 快照字节与首抓相同：列表为客户端分页，滚动不追加 |
| `UHlT7xORGbtCremKI` | ET 列表页 + 点击 Certificate 标签/翻页 | 仍只回 8 个文件 id（分页 AJAX 未被触发）；此路线按两次止损停止，改用 robots 允许的直链与检索枚举 |

补充手段（Apify 之后的合法补充）：WebSearch 定位官方直链；`curl` 直下 robots.txt 允许的路径（`en.goodwe.com/robots.txt` 仅禁 `/download*` 与 `/Index/search`；`/Ftp/**`、`/au/download-*`、`/Api/downloadFile` 不在禁列；`br.goodwe.com`、`saj-electric.com` 无实质禁止）。未对任何站点绕过 robots 或处理验证码。

---

## 1. SGS Annex（证书 `250008RECO14-CER`）——公开副本未取得，官方查询受限

背景：在托管件 `GW_ET-75-100kW_Certificate_VDE-AR-N-4110-4120.pdf`（1 页，629,561 B，sha256 `da4d0f336bb0b6e7828ad18f4e89534698383d0191c28a4c4dedbb7a94f4c61f`）正文写明证书由 1 页 + 164 页 Annex（Rev.0/2026-01-30）组成。

本次证据链：

1. 证书 PDF 内嵌超链接（从字节流解出）指向 `https://www.sgs.pl/en/vr/sgs-certified-components-and-products`（SGG 波兰验证入口，跳转到 sgs.com 全球目录）。该目录表单含 `cf-turnstile-response` 隐藏字段（2026-11-01 前次批次已实测定位，见 `docs/acceptance/2026-10-31/548/installation-facts-apply.md` §SGS 各节）；按纪律不处理人机验证，交互查询到此为止。
2. GoodWe 官方下载中心 `/Ftp/` 直链 `https://en.goodwe.com/Ftp/EN/Downloads/Certificate/GW_ET-75-100kW_Certificate-VDE4110_VDE4120.pdf`（HTTP 200, 629,561 B）——sha256 与在托管件**逐字节相同**。即 GoodWe 自己也只发布 1 页封面。
3. 德国分销 BayWa r.e. 副本 `https://solar-distribution.baywa-re.de/out/media/19_ET-G10_Serie_GW_ET-75-100kW_Certificate-VDE4110_VDE4120.pdf`（629,561 B）——同样**逐字节相同**。
4. 检索（`"250008RECO14"`、`site:sgs.com`、`Einheitenzertifikat annex GoodWe ET` 等多组查询）无任何索引到的 164 页 Annex 或含 Annex 的合并件。
5. GoodWe `/Ftp/` 猜名探测（`…-Annex.pdf` 三个变体）全部 302（不存在）。

判定：**公开副本未取得，但不能据此断言 Annex 不存在**。SGS 目录的实际交互搜索触发人机验证；公开详情接口对证书号及已核实的直接 sourceSystem 尝试只返回占位符。不得外推 Annex 内容，也不得把索取当作本代理可执行的路径。

对产品事实的影响：现 registry/知识库对 ET 75–100 的引用只要只引 1 页封面所述范围（型号、软件 010101、VDE-AR-N 4110/4120、无 test terminal 需另加连接端子板），即无需改动；不得外推 Annex 内容。

发布注意（609）：证书封面此前已按现有关联托管，本报告不改变其公开状态；若日后取得 Annex，作为同一证书的组成部分需走原件托管与版本记录流程，公开范围仍按产品-资料关联判定。

## 2. GoodWe BAT-C 60–112 kWh 定量资料——取得（参数表），曲线未发布

**取得的文件**：`GW_BAT-C 61.4-112.6kWh_User Manual-EN.pdf`
- 官方来源：GoodWe 下载中心条目 `GW_BAT-C 61.4-112.6kWh_User Manual-EN`（列表日期 2026-10-14），直链 `https://en.goodwe.com/Api/downloadFile?id=4626&mid=60&type=2`。
- 身份：封面 **V1.0 2026-10-10**，PDF 共 **87 页**，5,440,295 B。
- sha256：`c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7`
- 覆盖产品：GW61.4 / GW92.1 / GW102.4 / GW112.6-BAT-AC-G10（registry 现有 `mat_goodwe_gw61_4_bat_ac_g10`、`mat_goodwe_gw112_6_bat_ac_g10`）。

数据表/快装指南之外新增的定量事实（手册 §9 Technical Data，物理页 80–84，打印页 79–82）：

| 事实 | 值 | 页 |
| --- | --- | --- |
| 型号补全 | 官方还有 **GW92.1-BAT-AC-G10**（9 模组，2P144S）与 GW102.4（10 模组，2P160S）；数据表只列 61.4/102.4/112.6 | p.80 |
| 电芯/系统 | LFP 100 Ah cell，200 Ah 系统；模组 GW10.2-PACK-ACI-G10，10.24 kWh/模组，<90 kg | p.80 |
| 可用能量 | 60 / 90 / 100 / 110 kWh（对应 61.4/92.1/102.4/112.6） | p.80 |
| 工作电压 | 275.52–346.56 V（61.4）… 505.12–635.36 V（112.6） | p.80 |
| 最大充/放电流 | **180 A / 220 A**（全部型号） | p.81 |
| 额定充/放电流 | 100 A / 100 A | p.81 |
| 最大倍率 | **0.9C / 1.1C** | p.81 |
| 最大充/放功率 | 55.2/67.5 → 101.3/123.9 kW（按型号） | p.81 |
| 额定充/放功率 | 30.7 → 56.3 kW（按型号） | p.81 |
| 循环寿命 | ≥6000 次 @ 25±2 °C、0.5C、100% DOD，至 70% SOH | p.81 |
| 往返效率 | 96% @ 100% DOD、0.2C、25±2 °C | p.81 |
| 充/放温度范围、存储、湿度、海拔 | −20~+55 °C；+35~+45 °C(<6 月)/−20~+35 °C(<1 月)；0–100% 无凝露；4000 m | p.82–83 |
| 认证清单 | IEC 62619/63056/60730/62477/VDE 2510-50/ISO 13849；IEC 62040/N143(应为 N1438 手册原文)/EU 2023/1542/UN38.3 | p.83 |

**曲线结论**：手册脚注（p.84）只声明“实际充/放电电流与功率随电芯温度与 SOC 降额、最大倍率持续时间受 SOC/电芯温度/环境温度影响；额定值仅适用于澳大利亚”——**没有任何绘制的定量降额曲线**。BAT-C 208–261 手册 p.78 脚注同样只声明存在条件限制。判定：GoodWe 未公开出版 SOC×温度×倍率的定量曲线；registry 现有“扁平”数据表值（V1.1，已验证即当前版，见下）加上本手册的定量表就是可得的全部。任何更细曲线属厂商内部测试数据。

顺带核对（ BAT-C 数据表货币性）：`https://en.goodwe.com/Api/downloadFile?id=3301&mid=60&type=2`（列表名 `GW_BAT-C 61.4-112.6kWh_Datasheet_EMEA-EN`，2026-01-21）= 680,989 B，sha256 `845e51ffb2801f48971c8b53941629dde1e8bc114b9b45dbc4f08c49c5ef815c`，与在托管件 `delinker-goodwe_batc60-datasheet.pdf`（V1.1 2026-01）**逐字节相同** → 所持数据表即当前版。

发布注意（609）：该手册为 GoodWe 公开下载中心的免费分发件，与已在托管的同系列快装指南同性质；若上架，走既有原件托管+版本+产品关联流程（Bat-C 系列两款在售产品可直接关联）。手册明示“额定充/放电流/功率仅适用于澳大利亚”，欧洲口径引用时以最大值/额定值分列并保留脚注，不得混称。

## 3. GoodWe ET 75–100 kW 运行包络——所持即当前版；定量包络随 Annex 未公开

“ET 80–125 kW”按 registry 事实族 `goodwe-et-80-100k`（ET 75/80/99.99/100K-ET-G10 混合逆变器）+ GW125K-STS 理解。DE 数据表解析损坏另行处理；本节核 EN 当前原件与更全包络文档。

当前版逐字节核对（全部 HTTP 200 官方直链）：

| 在托管件 | GoodWe 官方当前直链 | sha256（两者相同） | 结论 |
| --- | --- | --- | --- |
| `GW_ET-75-100kW_Datasheet-EN-20260708-V2.1.pdf`（V2.1 2026-07-08） | `https://en.goodwe.com/Ftp/EN/Downloads/Datasheet/GW_ET-100_Datasheet-EN.pdf`（684,740 B） | `4f7178042e8faf03bd926dc33a5ff0b85ffcd4f46e12f1dcf86d6db10befee4d` | **当前版**，无更新 |
| `GW_ET-50-100kW_User-Manual-EN_V1.3.pdf`（Solution Manual V1.3 2026-06-30，65 页） | `https://admin.goodwe.com/En/Api/downloadFile?id=3259&mid=60&type=2`（en 站 302 跳转；列表名 `GW_Commercial & Industrial Smart Inverter Solutions_User Manual-ET 50-100kW-EN`；24,656,520 B） | `f66efb70d0d8927a92355980e0a0bd09359f580664976e082c4e510320e6d5a0` | **当前版** |
| ET 50–100 kW User Manual V1.2 2026-07-02（307 页，41,900,846 B） | `https://en.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_ET-100kW_User-Manual-EN.pdf` | `0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615` | **当前版** |

包络内容核对：User Manual V1.2 仅有三处定性降额表述（约 p.17/18 区域“输出功率可能降额”“网压/频率变化可能引起降额”，及后文高温降额提醒；COM 端子表在 p.189–192，2026-10-31 批次已记录）；Solution Manual 仅一处定性降额。**跨 DC 输入/温度/网压/频率/P-Q 的定量运行包络在三份当前文档中均不存在**——它正是 SGS Annex（164 页测试报告）的内容，随 §1 结论一并未公开。

判定：EN 权威当前原件已在手且经哈希锁定；缺口只剩 Annex。此前记录的端子表原文疑点（COM2 reserved 含 5 与同表 5=CAN-L 冲突、STS 分支 5/6 与 7/8 重复）在当前版中未变化，仍属“原厂表述疑点”，无更正版可取。

## 4. SAJ HS3 / CB2 端子图——所持即当前官方原件；无更全独立端子图

**HS3**：官方 hubfs `https://www.saj-electric.com/hubfs/Guides%20and%20Manuals/HS3/HS3-T/HS3-(3K-12K)-T2-(W%2CG)-(B%2CP)X_User_Manual_EU_TH_V4_en.pdf`（HTTP 200，11,804,387 B）sha256 `2c1dd5c1e2f7efd96eba4f24aa3804ee135936ac90bcccfd1a681f2188868f46`，与在托管件 `SAJ_HS3_3-12K-T2_User-Manual_EN_V4.pdf`（125 页，PDF 创建 2025-09-28）**逐字节相同**。V5 及其他 V4 命名变体探测均 404 → **V4 即最新**。
端子内容最全集就在本手册内：除 registry 已引的 p.22 端口总表外，连接端子排逐端子定义见 Table 5.1（p.78：DO1+ 干接点输出等端子-功能映射）、RJ45 针脚定义（p.81：Pin 1=MET-A、Pin 2=MET-B 等）。**不存在比手册更全的公开端子图**；未发现独立的 HS3 端子/通信协议公开件。

**CB2**：官方 hubfs（西班牙站镜像）`https://sp.saj-electric.com/hubfs/Guides%20and%20Manuals/CB2/CB2-(57.3K-100.3K)-HV5_User_Manual_en.pdf`（8,154,683 B，PDF 创建 2025-01-21，38 页）sha256 `ee6b3a41b8250367c67e285e5d69c15f19981eda3d83fdd476226393cb38cff5`，与在托管件 `SAJ_CB2_57.3-100.3-HV5_User-Manual_EN_V0.0.pdf` **逐字节相同** → 在托管的“V0.0”就是 SAJ 当前官方用户手册。
端子内容：§3.5 Battery Terminals Description（p.10–11，Table 3.1 电池模组端子 A–F、Table 3.2 控制单元端子 P+/P−/BAT+/BAT−/COM_PCS/COM_PAR/COM_BMU/AC220V）与 registry 今日记录的 p.10–11 一致。另有全球版数据表 `https://us.saj-electric.com/hubfs/Global/products/C%20I/Download%20Center/datasheet/CHS2/CHS2+CH2+CB2_datasheet_en_Global.pdf`（4 页，sha256 `b7045c8723ad2d18602776ca141c094f86482aa76461234bb819b9b6b39342a1`）——**不含端子图**，仅性能行，不构成端子增量。

判定：目标 4 的“更全端子图”**不存在**；registry 现有 HS3 p.22 / CB2 p.10–11 引用即取自当前官方原件，正确且为最全公开粒度。可选增量：把 HS3 Table 5.1（p.78）与 RJ45 针脚（p.81）作为补充规格挂到 `mat_saj_hs3_*`（针脚级事实，安装方真实需要），由实现票决定。

发布注意（609）：两份手册已在托管并关联在售产品，本次仅确认版本货币性，无状态变化。

---

## 5. 建议的后续动作（不在本批执行）

1. **BAT-C 用户手册上架**（§2 文件）：按 609 流程托管+登记版本+关联两款 BAT-C 在售产品；新增定量规格行建议同批进入 registry 评审（注意澳规脚注口径）。
2. **GW92.1-BAT-AC-G10 型号决策——已决：不上架**（2026-11-12，`docs/research/2026-11-12-gw92-decision/`）。
   官方手册证实该型号存在（9 模组 92.1 kWh），但它只出现在 AU 数据表与 AU 产品页；EMEA 产品页、
   EMEA 数据表、DE 兼容总表三处均不列。GoodWe 为 EMEA 发布的 BAT-C 只有 61.4 与 112.6 两个容量，
   即我们现有两款。
3. **SGS Annex 证据边界**：证书编号 `250008RECO14-CER`（Rev.0/2026-01-30）仅用于公开来源核验；公开副本未取得，官方交互查询受人机验证限制，不向厂商索取，不外推 Annex 内容。
4. HS3 针脚级端子规格（p.78/p.81）可并入下一次 SAJ 规格批次。

## 6. 资源报告（AGENTS.md §0）

- Apify：3 run（全部 `apify/website-content-crawler`）+ 12 个远端资源已全部 DELETE 204；无遗留远端存储。费用约 $0.15 以内（computeUnits 合计 ~0.15）。
- 本机：下载与中间文件全部在 `/tmp/vendor-originals`，哈希与页码取证完成后整个目录已删除（回收约 130 MB 峰值占用）。无浏览器/实例/常驻进程；无凭据落盘（Apify token 仅从 `~/.config/terravolt-builder/apify.env` 读入环境）。
- 仓库改动：仅新增本报告文件；未改 registry、代码、Woo 或生产。
