# 验证代理 F 线 · 生产 commercial 配置器端到端实走报告

日期：2026-11-11 · 生产 https://de-linker.com · 真实 Google Chrome 157.0.8103.39（CDP 127.0.0.1:9223，独立 profile `/tmp/f-chrome-profile`）

## 一句话结论

**真人客户今天能零报错走到方案输出（690 个系统组合 + Stückliste/BOM），EN 与 DE 完全同等，390 移动端同样可用**——但有一条必须知道的路径约束：**只能一路到底、不能中途点侧栏导航**；中途切页会取消在途计算并留下僵尸请求，之后必须手工清理才能继续。

## 分步结果表

| 步骤 | EN@1440 | DE@1440 | EN@390 | DE@390 | 截图 |
|---|---|---|---|---|---|
| 1 首页入口 | 通过（顶部菜单 Plan with Linker → Solution Configurator） | 通过 | 通过（移动菜单） | 通过 | `shots/ho-{en,de}-{1440,390}-01-inputs.png` |
| 2 商业分支表单 | 通过：Project type=Commercial 后年用电变 30k/50k/100k/250k/500k kWh | 通过（Projektart=Gewerbe） | 通过 | 通过 | 同上 |
| 3 输入并提交 | 100 kWp / 250,000 kWh / 三相 / "Cut commercial peak demand" / 80331 → Generate solution | 同（"Gewerbliche Leistungsspitze kappen"） | 同 | 同 | 同上 |
| 4 项目创建 | 通过 `projects/create` 200 | 通过 | 通过 | 通过 | — |
| 5 设备搜索 | `runs/equipment-search` queued→running→**succeeded** | 同 | 同 | 同 | — |
| 6 方案输出 | **690 个组合**；`GoodWe GW80K-ET-G10 + GW61.4-BAT-AC-G10(6 模块/stack)`、`+GW112.6-BAT-AC-G10(11)`、`+GW208.9-BAT-LC-G10(4)`、`GW99.99K-ET / GW100K-ET / GW125K-ETR-G10` 系列、`SAJ H2-25K-T3` 系列 | 同样 690 组合、同型号 | **690 组合 + BOM** | 同 | `shots/ho-*-02-final.png` |
| 7 BOM | "Provisional bill of materials" 表格 | "Vorläufige Stückliste" | 有 | 有 | 同上 |
| 8 报告 PDF | **失败 HTTP 422** | 同 | — | — | — |
| 全程进度 | ~30 秒 | ~30 秒 | ~30 秒 | ~30 秒 |  |

## 明确回答三个问题

**1. 真人今天能否零报错走完 commercial 配置器到方案输出？**
能。填表 → 一次 Generate solution → 30 秒内自动完成项目创建、设备搜索（690 组合）、设备校验，并在同一屏显示推荐系统与 BOM。全程无 JS 异常、无失败请求（唯一 HTTP 错误见下）。

**2. EN / DE 是否同等？**
同等。同一输入在两语言下都得到 **690 个组合**、完全相同的厂商与型号（GoodWe GW80K-ET/GW99.99K-ET/GW100K-ET/GW125K-ETR-G10 + GW61.4/GW112.6-BAT-AC-G10 + GW208.9-BAT-LC-G10；SAJ H2-25K-T3 系列），德语侧 Stückliste 正常，数字格式为德式（2.880 / 57,189 kW / 19.013,59875 kWh）。

**3. 390 是否可用？**
可用。390×844 下配置器、Quick start 表单、方案输出全部可读可操作，**无横向滚动**（`scrollWidth == innerWidth == 390`）。两种语言都跑到 690 组合 + BOM。

## 发现的缺陷与证据（不修，交主控派工）

### A. 中途点侧栏导航会取消在途计算并卡死设备搜索（中等，影响真实客户）
- 现象：Generate solution 后在设备搜索仍在跑时点击侧栏（如 Equipment / Energy inputs），会出现
  `[reqfail] POST /wp-json/linker/v1/planner/rpc/runs/equipment-search :: net::ERR_ABORTED`，
  随后 Equipment 页常驻 **"Stored requests → Calculation request · revision 1 → Retry original calculation request / Discard stored request"**，
  且 **Find equipment combinations 永久 disabled**、Save project 也 disabled。
- 必须手工点 "Discard stored request"（DE：Gespeicherte Anfrage verwerfen）才解锁。
- 证据：`ho-*` 与 `eq-*`、`deeq.mjs` 日志；截图 `shots/eq-en-1440-02-after-discard.png`（点前后按钮状态对比）。
- 根因线索：`apps/planner/src/components/QuickStart.tsx` 的自动流程绑定在组件生命周期上（`lifetime.current`），
  组件卸载即放弃在途 run，但服务端已接受该 run，前端把它当作"待恢复的存储请求"锁住后续搜索。

### B. 报告 PDF 在无能量计算时返回 422（需判定是设计还是缺陷）
- 现象：Quick start 走完后点 Planning report → 选项全是 "Not included"、Generate planning report disabled；
  自动流程里的 `runs/report` 返回 **HTTP 422**。
- 页面文案（DE）："Das Geräteergebnis ist fertig; das PDF benötigt zusätzlich das Energiegebnis."
  即 PDF 需要能量计算结果，而 Quick start 传 `energy_run_id: null`。
- 服务端证据：`services/engine/src/linker_engine/planning/report_sources.py:851`
  `raise InvalidInput("select at least one completed analysis for the report")` → 422。
- 影响：商业客户走"一屏快速方案"时**拿不到 PDF 报告**，只有 BOM。

### C. `admin-ajax.php?action=rest-nonce` 稳定 400（复验结论：仍在，但无功能影响）
- 每次加载配置器都出现 `[http400] GET /wp-admin/admin-ajax.php?action=rest-nonce`，响应体 `0` 字节，`content-type: text/html`。
- 复验：**在宕机前后、四遍走查中均出现，且不影响任何功能**——planner 的 bootstrap 走 `/wp-json/linker/v1/planner/bootstrap`（200）并自带 `nonce`。
- 判定：噪声级缺陷，可清理但不阻断客户。

### D. 非缺陷，但值得记录的行为
- **Generate solution 后不自动进入工作台**：`apps/planner/src/components/Workspace.tsx:183` 的 `quickStarted()` 只刷新项目列表，属设计行为；`?step=roof`（首页主 CTA）落地要求先建项目名，是另一条独立路径。
- **本次新增确认**：不打断时 Quick start 会自动跑完整条链（含 `runs/equipment` 校验与 BOM），此前把它当作"到项目列表为止"是误判。

## 逐条上传（负荷曲线）实测

生成并按导入合同修正的 CSV：30 天 × 96 点 = **2880 行**，全 900 秒间隔，UTC 连续无重叠，显式 `+02:00`/`+01:00` 偏移（跨 2026-10-25 欧洲夏令时结束），工作日 08–18 时均值 ~45 kW、峰值 57.19 kW，其余时段 ~18 kW，年化 231 MWh。

导入结果（EN 与 DE 一致，服务端确认）：
- Data records **2,880** · Covered duration **720 h** · Gaps **0** · Longest original interval **15 min**
- Min interval mean **13.665 kW** · Max interval mean **57.189 kW** · Energy in covered intervals **19,013.59875 kWh**

导入 UI 是两步：选文件 + 分隔符 → "Preview columns / Spaltenvorschau" → 完整映射（Timestamp/Value column、Measurement point、Value meaning、Decimal separator、Source type、Interval boundaries + 分钟、Source time zone）+ 必填的 "Source label" 与 "Herkunft und Berechtigung/权限说明"。

## 通信与安全检查

- **未提交任何询盘、未点最终提交、未填写真实邮箱**，因此**没有触发任何真实邮件**（生产无收件人重写开关，已按要求停在提交前）。
- 所有输入用 `E2E-COMM-PROBE` 标记。
- 测试项目已在站内删除并读回确认：`{"deleted":true}` ×2，最终项目列表 `{"projects":[],"delBtns":0}`。
- Turnstile：本次四遍走查**未出现任何 Turnstile 挑战**（有头真实 Chrome + 独立 profile），无阻挡、无重试。

## 生产事故（宕机期间观察，已恢复）

走查首轮撞上整站宕机，已定位到根因层并记录：
- 08:52 起 `https://de-linker.com` 全部 TLS 握手超时；`46.202.156.7` 的 443/80/65002 **TCP 可连但 HTTP 无响应**；
  源站 `curl http://127.0.0.1/` 也 000。
- `wp db check` → `ERROR 2002 (HY000): Can't connect to server on '127.0.0.1' (115)`；3306 **Connection refused**；无 mysqld/mariadb 进程。
- 主机 15 分钟负载峰值 68.87（1 分钟已回落 1.9），磁盘 61%、inode 59%、内存正常 → 非容量问题。
- 结论：**MariaDB 进程消失导致全站不可用**（Hostinger 侧重启后恢复），与配置器代码无关。

## 截图与日志

- 截图（全部为生产真实页面，fullPage）：`/tmp/f-comm-probe/shots/`，共 **93 张**
  - 四遍终态：`ho-en-1440-02-final.png`、`ho-de-1440-02-final.png`、`ho-en-390-02-final.png`、`ho-de-390-02-final.png`
  - 输入态：`ho-*-01-inputs.png`
  - 导入映射：`imp-en-1440-01-filled.png`、`imp-de-1440-01-filled.png`、`en-1440-07-import-open.png`
  - 工作台：`en-1440-05-workspace.png`、`de-1440-05-workspace.png`
  - 设备结果：`eq-en-1440-04-find-result.png`、`de-1440-e02-result.png`
  - 僵尸请求：`eq-en-1440-02-after-discard.png`
- 全文证据：`ho-{en,de}-{1440,390}-final.txt`（页面全文）、`ho-*-log.txt`（网络/控制台）、`imp-*-result.txt`（导入回读）

## 资源回收

| 项目 | 结果 |
|---|---|
| 自己启动的 Chrome（CDP 9223） | 已终止；端口 9223 无监听（`lsof` 0 条） |
| 临时 profile `/tmp/f-chrome-profile` | 已删除，释放 **165 MB** |
| 用户自己的 Chrome（PID 1212） | 未触碰（无调试参数，确认为用户实例） |
| 后台 autorun/poll 脚本 | 已终止 |
| 截图与日志 `/tmp/f-comm-probe` | **保留 46 MB**（93 张截图 + 日志），作为本次验收唯一证据 |
| 磁盘 | 可用 1.3 TiB（66% 使用） |

按第 0 节"保留唯一验收证据"原则保留 `/tmp/f-comm-probe`；如需回收，可直接删除该目录。

> Archived from /tmp/f-comm-probe/REPORT.md (F-line production walk, 2026-11-11).
> Screenshots retained at /tmp/f-comm-probe/shots (93 files, 46 MB) until batch close.

## 主控验收结论

- 三问全答：真人零报错走通（EN/DE × 1440/390，690 组合+BOM）；EN/DE 同等；390 可用。
- 矩阵翻行：configurator `compatible-result` ×4（en/de × 1440/390）→ verified-production-20261111。
- `report`/`download-pdf` 行不翻：PDF 422 缺陷（B）修复前不构成覆盖。
- 缺陷 A（中途导航取消在途计算并卡死设备搜索）与 B（商用快速路径无 energy run → PDF 422）
  均为真实缺陷，已派修复线。
