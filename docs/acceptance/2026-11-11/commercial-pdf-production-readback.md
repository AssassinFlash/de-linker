# 商用快速路径报告 PDF · 生产读回（缺陷 B 修复验证）

日期：2026-11-11 · 生产 https://de-linker.com · 有头 Google Chrome 157.0.8103.39
（CDP `127.0.0.1:9223`，独立 profile `/tmp/aa-chrome-profile`）

## 一句话结论

**缺陷 B 已在生产修复。** 商用快速路径走完后，报告步骤 `done`，PDF 下载 **HTTP 200**，
四份文件都是 A4 五页的真报告（EN 与 DE 各两份，1440 与 390 各一份），
**不再出现 422**。矩阵里 `configurator` 的 `report` / `download-pdf` 八行据此翻为
`verified-production-20261111`。

## 缺陷与修复（背景）

F 线 2026-11-11 生产实走（`docs/acceptance/2026-11-11/commercial-production-walk.md` §B）
报告：商业客户走完一屏快速方案拿到 690 个组合与暂定 BOM 后，点报告得 HTTP 422，没有 PDF。

R 线修复 PR [#1102](https://github.com/AssassinFlash/de-linker/pull/1102)（已合并）：
快速面板把选中候选写成项目的 `equipment_candidate` 后，又在同一请求里点名
`runs/equipment` 的 run，形成两个设备来源，服务端按合同拒绝。修法是报告步骤只传候选
（`equipment_run_id: null`），与工作台的表单一致。本条验收验证的是**部署后的生产行为**。

## 部署已在位（先读回，再实走）

| 项 | 读回 |
|---|---|
| `planner/vite-manifest.json` | 入口 `assets/planner.js`，核心 `assets/planner-core-BaCygMK5.js` |
| 该核心文件 | HTTP 200，**1,406,738 字节**（2026-11-11 14:53 CST 读回） |
| 与仓库产物 | 文件名哈希 `BaCygMK5` 与仓库 `plugins/linker-tools/build/planner/vite-manifest.json` 的 `planner-core` 一致，即 PR #1102 合并后的构建，不是旧缓存 |
| 线上代码形态 | 下载的 bundle 内快速路径报告调用为 `{locale, energy_run_id:null, pv_run_id:null, equipment_run_id:null, logo:null}`；工作台表单是另一种形态（有候选时不传 run），两条路径各自符合合同 |

## 实走路径

`solution-configurator`（DE 用 `/de/loesungskonfigurator/`）→ `Start a solution`
（DE：`Lösung starten`）→ 一屏表单：
Project type **Commercial** / PV **100 kWp** / **250,000 kWh per year** / 三相 /
System goal **削峰**（Cut commercial peak demand）/ 邮编 **80331**
→ `Generate solution` → 等自动链（save → search → qualify → report）→ `Download PDF`。

输入与 e2e `tests/e2e/specs/planner-commercial-quickstart-report.spec.ts` 完全一致，
唯一差别是位置字段带 `E2E-PDF-PROBE` 标记：快速表单没有标题字段，自动生成的标题是
测试标记唯一能落地的地方，也让随后的删除只针对本次探针项目。

## 结果（四组合）

| 组合 | 报告步骤 | 用时 | `runs/report` | PDF HTTP | 字节 | 页数 | 标题 |
|---|---|---|---|---|---|---|---|
| EN@1440 | done | 51 s | 200 | **200** | 62,372 | 5 | Project planning report |
| DE@1440 | done | 43 s | 200 | **200** | 63,490 | 5 | Projektplanungsbericht |
| EN@390 | done | 43 s | 200 | **200** | 62,368 | 5 | Project planning report |
| DE@390 | done | 45 s | 200 | **200** | 63,490 | 5 | Projektplanungsbericht |

四次 `runs/report` 的请求体实测都是
`{"expected_revision":2,"options":{"locale":"<lang>","energy_run_id":null,"pv_run_id":null,"equipment_run_id":null,"logo":null}}`
——就是修复后的形态；下载走 `rpc/assets/content`，四次都 200。

自动链每一步的终态四次一致：

```
save=done  weather=blocked  pv=blocked  scenario=blocked  energy=blocked
search=done  qualify=done  report=done
```

`weather` / `pv` / `scenario` / `energy` 为 blocked 是设计行为（快速面板没有屋顶坐标与
导入的区间曲线，它如实说明缺什么，不拿年度值冒充区间序列），与本条修复无关；
690 个组合与暂定 BOM 在四组合中照常产出（DE 显示 `690 passende Kombinationen`）。

## 断言（逐项）

| 断言 | 结果 |
|---|---|
| 报告步骤不再 422 | **通过**：`runs/report` 200，步骤 `done`，无失败提示 |
| PDF 下载 HTTP 200 | **通过**：四次 `rpc/assets/content` 均 200 |
| `%PDF-` 魔数 | **通过**：四份均以 `%PDF-1.4` 开头 |
| 字节数 > 0 | **通过**：62,368 / 62,372 / 63,490 / 63,490 |
| 页数 ≥ 1 | **通过**：四份均 **5 页**（`file` 与 `pdfinfo` 双重确认，非仅凭字节正则） |
| 文件是完成的报告 | **通过**：`pdfinfo` 报 A4 595.276 × 841.89 pts、`%%EOF` 完整、Title 与语言相符；正文含项目标题 `Commercial · 100 kWp · E2E-PDF-PROBE 80331`、`Input revision 2`、设备校核引用 SAJ H2 数据手册第 2 页 |
| 文件名格式 | **通过**：`linker-planning-<32 hex>-r2-<lang>.pdf`，与 e2e 断言的规则一致 |

逐组合的文件与 sha256：

| 组合 | 文件名 | sha256 |
|---|---|---|
| EN@1440 | `linker-planning-c5fac5b61d2f499cb60f8550a42c1a6f-r2-en.pdf` | `c2a225b85bf0e7003054c932fa4ba01009862522a2b006230e029aafde35d3c6` |
| DE@1440 | `linker-planning-734b5234b1544d63853035ac328ccc75-r2-de.pdf` | `d6ce2b0a75b6d098d6716c44ce0f0e5ff45be5bb618f2526f2653a623353f172` |
| EN@390 | `linker-planning-0e1001eae83f4b20bc1db809d9854e6b-r2-en.pdf` | `5e845184c2090f10d63c9fca2b8f006cd6f78e096b9f9bc3eece1ab3e576d293` |
| DE@390 | `linker-planning-89c850e540c449dda90b21dea5beda69-r2-de.pdf` | `c3bb3e7c337e4f3e2ef93e457605b0cd7d1f941521f6ae1d1a67c5afb291b703` |

DE@1440 与 DE@390 字节数相同但 sha256 不同（生成时间戳不同），不是同一份文件被读了两次。

## console 与失败请求

四组合一致：**pageerror 0、失败请求 0、console error 仅 1 条**，
内容都是 `GET /wp-admin/admin-ajax.php?action=rest-nonce` → **400**。

这是 F 线已记录的既有噪声（planner bootstrap 走
`/wp-json/linker/v1/planner/bootstrap` 并自带 nonce，该 400 不影响任何功能），
本轮复验仍在，**与本条缺陷无关，未修**。

## 清理与邮件纪律

- 四个探针项目全部删除。**不拿"列表为空"当证据**：删除后用页面自己的 guest 会话
  （scope `390cdaa7…c533`，`projects/list` 200 且 `items: []`）对四个项目 ID 逐个
  `projects/read`，**全部 404 `not_found`**——是真删，不是换了 scope 看不见。
- **未提交询盘、未触发任何真实邮件**（生产无收件人重写开关，全程停在下载，不碰询盘与账号）。
- Turnstile 未出现挑战（有头真实 Chrome + 独立 profile），无重试、无人工干预。

## 证据文件

- 机器可读逐组合证据：`docs/acceptance/2026-11-11/commercial-pdf-production-readback.json`
- 交付在仓库内的原件：`docs/acceptance/2026-11-11/commercial-pdf-readback-files/`
  ——4 份 PDF、12 张截图（`*-01-inputs` / `*-02-report` / `*-03-after`）与 4 份原始 JSON 记录（共约 1.4 MB）。
  PDF 与 sha256、字节数、页数一并保留，可直接复核本文件的每个数字，不依赖 `/tmp`。

## 资源回收

| 项 | 结果 |
|---|---|
| 自己启动的 Chrome（CDP 9223） | 已终止；端口无监听 |
| 独立 profile `/tmp/aa-chrome-profile` | 已删除 |
| 保留的唯一证据 | 已随 PR 交付进仓库：`docs/acceptance/2026-11-11/commercial-pdf-readback-files/`（4 份 PDF 约 246 KB、12 张截图约 1.1 MB、4 份原始 JSON，共约 1.4 MB） |
| 已删除的失效产物 | 两次被取代的失败截图（首版脚本的 `ENOENT`、EN@390 的瞬时连接中断）——两次都已重跑成功，不构成产品证据 |
| 临时副本 | `/tmp/aa-walk`、`/tmp/aa-pdf-shots` 已在仓库内留存后删除 |
| worktree `/tmp/aa-pdf` | 提交后用 `git worktree remove` 回收 |
