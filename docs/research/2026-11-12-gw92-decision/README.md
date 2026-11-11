# GW92.1-BAT-AC-G10 型号决策：不上架

日期：2026-11-11 / 12（北京时间）。分支 `gw92-decision`，worktree `/tmp/gw92-decision`，基于 `origin/main` `b53084736`。
依据：`docs/specs/609-product-publication.md`（发布规则）、`AGENTS.md` §2（产品范围由本线按竞品映射与证据决定）、
`docs/research/2026-11-04-vendor-originals.md` §2/§5.2（该报告把本项登记为"由业主/采购线定"）、
`docs/acceptance/2026-11-10/goal-state-ledger.md` 的业主 2026-11-11 晚间裁定（"这类决策由线内按证据直接做"）。

范围：只做外部取证与决策记录。**未改 registry、未改 Woo、未新建产品、未写生产、未改代码。**
未接触 SE 线文件、direct-beam/天气路径、能量时序模块。

## 0. 结论

**不上架 GW92.1-BAT-AC-G10。**

该型号在 GoodWe 官方目录中真实存在，但**只存在于澳大利亚市场的产品页与澳大利亚版数据表**。
我们销售区（DE/EU）的 EMEA 产品页、EMEA 数据表、EMEA 兼容性总表三处均不列该型号。
GoodWe 为 EMEA 发布的 BAT-C 只有两个容量：61.4 与 112.6——正好就是我们现有的两款（Woo 1954/1955）。

## 1. 决策规则（本线自决，按证据）

R1 **区域目录是必要条件。** 型号进入我们目录的条件是：厂商在**我们销售区域（DE/EU）**的官方
产品页把该型号列为可配置型号，或在我们所售区域的数据表中列出该型号。其他区域的目录不构成依据。

R2 **规格事实源必须是本区域适用的原件。** 产品页规格取自托管原件、页码可核。跨区域手册的
技术数据表可以补充事实，但不能单独建立产品页：609 要求每款已发布产品有可公开的托管资料依据
（`Publication::allows_document()` 按当前产品-资料关联授权），且各区域原件的口径不同（见 §4 的
DOD 与额定功率差异）。把澳版数据表挂到面向德国客户的页面上，会让澳洲口径的数值出现在德国客户面前。

R3 **"填补容量空档"本身不是上架理由。** 中间容量是否常见由厂商目录决定，不由我们猜测。
EMEA 侧承认的中间容量是 102.4（EMEA 兼容性总表列它、EMEA 证书分页有 `GW_BAT-C 102.4-112.6kWh_Certificate-IEC62477`），
不是 92.1（见 §3.1、§3.2、§5）。

R4 **只在跨区域手册出现、且本区域产品页与数据表均不列的型号 → 不上架**，登记为区域外型号，
写明触发重新评估的条件（见 §7）。

## 2. 厂商正主证据：三份数据表与手册

| 原件 | 官方直链 | 版本（PDF 页脚） | 字节 | sha256 | 92.1 列? |
| --- | --- | --- | --- | --- | --- |
| **EMEA 数据表**（即在托管件 `delinker-goodwe_batc60-datasheet.pdf`） | `https://en.goodwe.com/Api/downloadFile?id=3301&mid=60&type=2` | `GoodWe-Single page-20260112-EMEA-EN-V1.1` | 680,989 | `845e51ffb2801f48971c8b53941629dde1e8bc114b9b45dbc4f08c49c5ef815c` | **否** |
| **Global 数据表** | `https://en.goodwe.com/Ftp/EN/Downloads/Datasheet/GW_BAT-60-112_Datasheet-EN.pdf` | `GoodWe-Single page-20260313-EN-V2.1` | 691,412 | `225c2995448789455b859687748f51d05555ecdfa621eacb073a8b0271e19319` | **否** |
| **AU 数据表** | `https://en.goodwe.com/Api/downloadFile?id=3631&mid=60&type=2` | `GoodWe-Single page-20260917-AU-V2.1` | 699,848 | `1184a6b686191e72ee95b226043c225d9a44025a2a45dce427f7497972e58da8` | **是** |
| 用户手册 V1.0 | `https://en.goodwe.com/Api/downloadFile?id=4626&mid=60&type=2` | 封面 `V1.0 2026-10-10`，87 页 | 5,440,295 | `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7` | **是**（p80/81） |

三份数据表都是 2 页，技术数据表在第 2 页；PDF 全文 `pdftotext -layout` 逐字核对。

**型号列原文（第 2 页技术数据表表头）**

- EMEA V1.1：`GW61.4-BAT-AC-G10`、`GW112.6-BAT-AC-G10`（两列）。Pack Configuration `2P96S` / `2P176S`；
  Number of Packs `6` / `11`；Nominal Energy `61.4` / `112.6`。全文 `102.4` 与 `92.1` 均 0 次。
- Global V2.1：`GW61.4`、`GW102.4`、`GW112.6`（三列）。Pack Configuration `2P96S` / `2P160S` / `2P176S`；
  Nominal Energy `61.4` / `102.4` / `112.6`。**无 92.1 型号列**。
- AU V2.1：`GW61.4`、`GW92.1`、`GW102.4`、`GW112.6`（四列）。Pack Configuration 含 `2P144S`；
  Number of Packs `6` / `9` / `10` / `11`；Nominal Energy `61.4` / `92.1` / `102.4` / `112.6`；
  Usable Energy `60` / `90` / `100` / `110`；Nominal Voltage `307.2` / `460.8` / `512.0` / `563.2`。

### 2.1 一个必须记下的误读陷阱

Global 数据表全文 `92.1` 出现 **1 次**，位置是第 2 页 Max Charge/Discharge Power 行：

```
Max. Charge / Discharge Power (kW)*2   55.2 / 67.5   92.1 / 112.6   101.3 / 123.9
                                        (GW61.4)      (GW102.4)      (GW112.6)
```

这里的 `92.1 / 112.6` 是 **GW102.4 这一列的最大充/放功率数值**，不是型号。任何以字符串搜索
"92.1" 判定 Global 数据表覆盖 92.1 型号的做法都会得到错误结论。型号覆盖只看表头型号行。

### 2.2 手册（V1.0）确实覆盖四型号

物理 p80（印刷 79）Technical Data 表头为四列 `GW61.4 / GW92.1 / GW102.4 / GW112.6-BAT-AC-G10`；
92.1 列：Pack Configuration `2P144S`、9 个模组、Nominal Energy `92.1 kWh`、Usable `90 kWh`、
Nominal Voltage `460.8 V`、Operating Voltage `413.28~519.84 V`。
物理 p81（印刷 80）：最大充/放功率 `82.9 / 101.3 kW`，额定充/放功率 `46.0 kW`，
最大充/放电流 `180/220 A` 与倍率 `0.9C/1.1C`（全型号共用）。

## 3. 官方产品页与下载中心的区域口径

| 面 | URL | 型号 | 92.1 出现次数 |
| --- | --- | --- | --- |
| **EMEA 产品页** | `https://emea.goodwe.com/bat112-series` | `GW61.4`、`GW112.6` | 0 |
| Global 产品页 | `https://en.goodwe.com/bat-60-112-series` | `GW61.4`、`GW102.4`、`GW112.6` | 0 |
| **AU 产品页** | `https://en.goodwe.com/au/bat-60-112-series` | `GW61.4`、`GW92.1`、`GW102.4`、`GW112.6` | 2（含 `92.1kWh`） |
| 德国站产品页 | `https://de.goodwe.com/bat112-series` | `GW61.4`、`GW112.6` | 0 |

**下载中心分页结构。** 页面首屏只渲染 Compatibility List 分页（8 项）；其余分页由
`POST /api/getfilenew.html`（`catid=4542`，EMEA 站）懒加载。**必须查分页，不能只看首屏。**

| 分页 | 计数 | 内容 |
| --- | --- | --- |
| User Manual | 24 | 含 `GW_BAT-C 61.4-112.6kWh_User Manual-EN`（4626，2026-10-14）等 |
| **Datasheet** | **12** | 见下 |
| Certificate | 8 | 见 §3.2 |
| Compatibility List | 8 | 见 §3.1 |

**Datasheet 分页全 12 项（EMEA 站，`type=10`，两页拉完：8 + 4）**：

```
3301  2026-01-21  GW_BAT-C 61.4-112.6kWh_Datasheet_EMEA-EN
3307  2026-01-21  GW_BAT-C 61.4-112.6kWh_Ficha técnica_EMEA-ES
3308  2026-01-21  GW_BAT-C 61.4-112.6kWh_Fiche technique_EMEA-FR
3310  2026-01-21  GW_BAT-C 61.4-112.6kWh_Gegevensblad_EMEA-NL
3377  2026-01-21  GW_BAT-C 61.4-112.6kWh_Datasheet_EMEA-UA
3905  2026-01-21  GW_BAT-C 61.4-112.6kWh_Datasheet_EMEA-HU
3306  2026-01-21  GW_BAT-C 61.4-112.6kWh_Datenblatt_EMEA-DE
3309  2026-01-21  GW_BAT-C 61.4-112.6kWh_Dati tecnici_EMEA-IT
3311  2026-01-21  GW_BAT-C 61.4-112.6kWh_Karta katalogowa_EMEA-PL
3376  2026-01-21  GW_BAT-C 61.4-112.6kWh_Fișă tehnică_EMEA-RO
3633  2026-01-21  GW_BAT-C 61.4-112.6kWh_Datasheet-PT
3305  2026-01-21  GW_BAT-C 61.4-112.6kWh_Datový list_EMEA-CZ
```

**12 项全部是同一份 EMEA 数据表的 12 种语言版本，全部 2026-01-21，全部只覆盖 61.4 与 112.6。**
EMEA 下载中心没有第二个 BAT-C 60–112 数据表，也没有任何覆盖 92.1 的 EMEA 数据表。

德语版单独核验（德国客户实际会下载的那一份）：
`https://admin.goodwe.com/Api/downloadFile?id=3306&mid=60&type=2`，682,009 B，
sha256 `2a76fb0815a2b6adbaee9159b958e24549e480d90b519cd5181209448cd45eb7`，
表头 `Technische Daten | GW61.4-BAT-AC-G10 | GW112.6-BAT-AC-G10`，`92.1` 与 `92,1` 全文 0 次。

AU 站同类分页计数为 User Manual 24 / **Datasheet 17** / Certificate 8 / Compatibility 8 / Maintenance 1 / Others 2，
数据表比 EMEA 多 5 项——92.1 的覆盖就落在 AU 的那 17 项里（其中 `id=3631` 已核，见 §2）。

### 3.1 兼容性总表：Global 与 EMEA 不一致

| 总表 | 直链 | 字节 | sha256 | 型号 |
| --- | --- | --- | --- | --- |
| EMEA | `https://admin.goodwe.com/Api/downloadFile?id=1889&mid=60&type=2` | 364,905 | `d303ef76eb410cd48e192c04909b0c3d8d00e9307273dbc72e361526c1bef4fb` | 61.4 / 102.4 / 112.6 |
| Global | `https://admin.goodwe.com/Api/downloadFile?id=542&mid=60&type=2` | 412,542 | `80d7f502861eeb88a2c12483b09f52ffb1fcd2d04daae3ceb429f3b1a15c7db1` | 61.4 / **92.1** / 102.4 / 112.6 |
| DE | `https://admin.goodwe.com/Api/downloadFile?id=922&mid=60&type=2` | 376,934 | `19fcbb51bdb3aa30bc95bc4c7a118276f36d8704b3ca6b7920d710df71330473` | 61.4 / 102.4 / 112.6 |

即：GoodWe 自己的文件之间也不一致——Global 兼容总表列 92.1，Global 数据表与 Global 产品页不列。
这份不一致不能当作"目录在售"的依据；面向德国客户的 DE 兼容总表不列 92.1。

### 3.2 证书分页：EMEA 按 102.4 出证书，没有 92.1 的

Certificate 分页全 8 项（`type=12`）：

```
3698  2026-01-21  GW_BAT-C 61.4-112.6kWh_Certificate-IEC 62040
3257  2026-01-21  GW_BAT-C 61.4-112.6kWh_Certificate-IEC62619_IEC63056_EN62477
3255  2026-01-21  GW_BAT-C 102.4-112.6kWh_Certificate-IEC62477
3699  2026-01-21  GW_BAT-C 61.4-112.6kWh_Certificate-VDE 2510-50
3256  2026-01-21  GW_BAT-C 61.4-112.6kWh_Certificate-CE LVD
3254  2026-01-21  GW_BAT-C 61.4-112.6kWh_EU Declaration of Conformity_POLY
3692  2025-10-29  GW_ET 80-100kW_Certificate-CEI 0-21+BAT
3690  2025-10-29  GW_ET 80-100kW_Certificate-CEI 0-16+BAT
```

`3255` 的文件名是 `GW_BAT-C 102.4-112.6kWh_Certificate-IEC62477`——**EMEA 侧按 102.4 出过合规证书**，
说明 EMEA 认可的中间容量是 102.4。**证书列表里没有任何 92.1 条目。**
这是"EMEA 的中间容量是 102.4 而不是 92.1"的最直接厂商证据。

## 4. 为什么"手册里有"不足以上架

1. **区域口径不同。**
   - DOD：AU 数据表 Depth of Discharge 行 `98% / 98% / 100% / 98%`（61.4/92.1/102.4/112.6），
     脚注 `*1: Test conditions, 98% DOD …`；EMEA 数据表为 `100%`；Global 数据表 `100%` + 脚注
     `For Australia, DOD is 98%`。
   - 额定值：手册物理 p83（Note 2）与 EMEA 数据表脚注 `*2` 都写明额定充放电流/功率**仅适用于澳大利亚**。
     2026-11-11 的 `docs/acceptance/2026-11-11/548-batc-manual-publication.md` §3.1 已据此把额定值行
     挂 `qualifier`。
   - 若为 92.1 建页，唯一能给出 92.1 全部规格的数据表是**澳版**（含 98% DOD 与澳规条件），
     把它挂到 DE 产品页就是把澳洲口径卖给德国客户。
2. **609 要求每款已发布产品有可公开的托管资料依据**（`Publication::allows_document()` 按当前
   产品-资料关联授权，派生数据不授权）。手册虽然已托管并与 1954/1955 关联，但手册是四型号共用件，
   它不是"该型号的数据表"，用它单独支撑一个新的产品页等于让产品事实来自跨区域手册，
   与"托管数据表即产品事实源"的既有纪律不符。
3. **交付清单同样只有手册背书。** `tools/migrate/548-batc-small-delivery-source.json` 记录的
   包装清单（`GW92.1-BAT-AC-G10：×8` 模组间线束）出自 ET 50–100 kW 手册 p.33 的表格，
   没有第二份独立原件可交叉验证。

## 5. 竞品映射：欧洲安装商向目录列什么

| 站点 | 市场 | 列出的 BAT-C 型号 | 92.1 |
| --- | --- | --- | --- |
| `photovoltaikshop.eu`（兼容性索引） | DE | `GW61.4` / `GW102.4` / `GW112.6` | 无 |
| `memodo.de` | DE | BAT112（112.6 kWh） | 无 |
| `solarmarkt.ch` | CH | `GW112.6-BAT-AC-G10` | 无 |
| `solarics.de` | DE | `GW112.6-BAT-AC-G10` | 无 |
| `shop.krannich-solar.com`（B2B） | DE | 搜索 `BAT-AC-G10` 只回 `GW5.1-BAT-D-G20` B-Ware，无 BAT-C 大容量 | 无 |
| `solarproof.com.au` | AU | **`GW92.1-BAT-AC-G10` 92.1 kWh** | 有 |

结论：
- **中间容量在欧洲是常见做法**（`photovoltaikshop.eu` 的德国兼容索引把 102.4 与两个端型号并列），
  但欧洲渠道列出的是 **102.4**，不是 92.1。
- **在被查的 5 家欧洲安装商向站点中，0 家列 92.1**；唯一找到的 92.1 零售条目在澳洲。
- 因此"中间容量有价值"支持的是 102.4（若日后要补中间容量），不支持 92.1。

## 6. 顺带发现：102.4 也不在 EMEA 产品页/数据表，我们的两款与 EMEA 目录完全对齐

- EMEA 产品页（`emea.goodwe.com/bat112-series`）与 EMEA 数据表（12 个语种）都只有 61.4 / 112.6 两个容量。
- Global 数据表、EMEA 兼容性总表、**EMEA 证书分页（`GW_BAT-C 102.4-112.6kWh_Certificate-IEC62477`）** 都提到 102.4；
  EMEA 产品页与 EMEA 数据表不列它。
- 我们现有 Woo 1954（`GW61.4-BAT-AC-G10`）与 1955（`GW112.6-BAT-AC-G10`）恰好等于 EMEA 目录的两个容量。

即：**当前产品组合与 EMEA 官方目录一一对应，没有"EMEA 目录有而我们缺"的型号。**
102.4 是否值得为德国市场补一款，是独立的业务决策（按 R1，EMEA 产品页目前也不列它，同样不满足上架条件），
本记录只登记证据，不执行。

## 7. 重新评估的触发条件

出现以下任一情况时，本决策重开：

1. GoodWe 在 EMEA 产品页（`emea.goodwe.com/bat112-series` 或后继页）把 `GW92.1-BAT-AC-G10` 列为可配置型号；
2. GoodWe 发布覆盖 92.1 的 **EMEA** 数据表（V1.2 或新版本，或 EMEA Datasheet 分页出现第二份 BAT-C 60–112 文件），
   且该版本给出 92.1 的 EMEA 口径 DOD 与额定值；
3. EMEA 证书分页出现 92.1 条目；
4. 我们改变销售区域（`identity.sales_region` 不再是 DE/EU），使 AU 或 Global 口径成为适用口径。

满足其一后按 609 走：托管该区域数据表 → 登记版本 → Woo 产品（名称/SKU 按现有 `DLK-GOODWE-<MODEL>` 规则；
`DLK-GOODWE-GW921BATACG10`）→ registry 规格行（带页码）→ 双语产品页 → feed/消费者读回。

## 8. 复核命令（任何人可重跑）

```bash
# 三份数据表：型号列
curl -sL -o emea.pdf "https://en.goodwe.com/Api/downloadFile?id=3301&mid=60&type=2"
curl -sL -o glob.pdf "https://en.goodwe.com/Ftp/EN/Downloads/Datasheet/GW_BAT-60-112_Datasheet-EN.pdf"
curl -sL -o au.pdf   "https://en.goodwe.com/Api/downloadFile?id=3631&mid=60&type=2"
for f in emea glob au; do echo "== $f"; shasum -a 256 $f.pdf
  pdftotext -layout $f.pdf - | grep -E "GW[0-9]+\.[0-9]+-BAT-AC-G10" | head -2; done

# EMEA 下载中心 Datasheet 分页（首屏不含，必须 POST）
curl -s -X POST "https://emea.goodwe.com/api/getfilenew.html" \
  -H "X-Requested-With: XMLHttpRequest" \
  --data "catid=4542&page=1&type=10&country=&lang=&clear=2" \
  | python3 -c "import json,sys,re; h=json.load(sys.stdin)['html']; \
print('\n'.join(re.findall(r'<h2>(.*?)</h2>',h)))"

# 产品页型号
for u in emea.goodwe.com/bat112-series en.goodwe.com/bat-60-112-series en.goodwe.com/au/bat-60-112-series; do
  echo -n "$u 92.1 hits: "; curl -sL "https://$u" | grep -c '92\.1'; done
```

## 9. 资源

- 新建：worktree `/tmp/gw92-decision`（本 PR 交付后回收）；取证目录 `/tmp/gw92-evi`（原件与中间文本，核对完成后删除）。
- 未新建本地实例、未新建浏览器窗口、未接触生产、未发邮件、未改 Woo/registry/代码。
- Apify：3 个 `apify/google-search-scraper` run（dataset `m4IwmFCF4JicsupCW`、`3SDbzCfQKhylTXdKw`、
  第 3 个站点搜索 run 的 dataset），远端 dataset 已 DELETE；另有 1 次因账号内存上限被拒、未启动的请求
  （这是本账号其他并行任务的运行占用所致，非本任务泄漏）。无截图、无持续进程。
