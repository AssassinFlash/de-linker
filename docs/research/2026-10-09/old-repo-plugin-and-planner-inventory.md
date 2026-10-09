# linker-ai-assistant 与 design-engine 结构盘点（wt-190 @ 5117962a，只读，2026-10-09）

结论：业主判断成立，Planner 比 Advisor 更糟。Planner 前端是 6,853 行 bundle（`src/planner/index.js` 单模块约 5,170 行）；服务端大部分塞在 Advisor 的 `class-linker-ai-rest.php`；三个 bundle 源码不在仓库（ADR-0016:38："unminified esbuild output edited in place, no build step"）；测试靠文本标记从 bundle 里切函数（`tests/unit/planner-calculation-contract-test.mjs` 的 `source.indexOf('  function '+name+'(')`）。真正的资产是 design-engine 和 b2b-core 的 Project/材料/报价权威层。

## 1. PHP 模块（`includes/`）
| 文件 | 行 | 职责 | 主要依赖 | 服务工具 |
|---|---|---|---|---|
| answer-validator | 11,446 | 模型草稿与客户答案间的"最终信任边界"，规则重写/拒绝 | Contracts×78、Products×44、Task_Planner×26，22 个 `tv_*` | Advisor |
| authority-resolver | 5,566 | 把任务交给对应权威层（产品、兼容、商务、Project） | Products×75、Contracts×57；`:4600` 调 `REST::calculate_quick` | Advisor（并调 Planner 计算） |
| task-planner | 5,118 | 一句话拆任务；名叫 Planner，实为 Advisor 的 NLU | Products×60、Contracts×18 | Advisor |
| rest | 4,226 | 全部 `linker-ai/v1` 路由 + BOM 定价 + 设计代理 + 组件目录校验 + 指标 + 会话清洗 | Engine×19、Conversation_Store×12，34 个 `tv_*` | **四个工具全有（纠缠最重）** |
| products | 4,127 | 产品检索、价格与供货投影 | 29 个 `tv_*` | Advisor |
| contracts | 2,125 | 失败即关闭的数据契约 | — | Advisor + workspace |
| model | 1,776 | DeepSeek 对话、流式、熔断 | Settings、Validator | Advisor |
| vision | 1,637 | NVIDIA 视觉识别铭牌 | Model、Products | Advisor |
| compatibility | 1,466 | 兼容问题措辞与主体识别 | 14 个 `tv_b2b_material_compatibility_*` | Advisor |
| knowledge | 1,391 | 知识检索（embedding + 关键词） | `data/knowledge-index.json` | Advisor |
| linker-ai-assistant.php | 681 | 引导、资源、`LinkerAIConfig` | 全部 | 四工具 |
| orchestrator | 600 | 分阶段流水线接缝 | Validator、Planner、Resolver | Advisor + workspace |
| conversation-store | 569 | 自建表，按归属保存会话（ADR-0016/0017） | REST | Advisor |
| engine | 502 | design-engine HTTP 客户端（重试、熔断、证书固定） | Settings、`tv_b2b_project_calculation_inputs` | Planner、Canvas、Advisor |
| settings / provider-watch / weekly-report / tool-frame | 335/274/267/245 | 设置、供应商健康、周报、三工具共用页头 | — | 共用/运维 |

## 2. JS（`assets/`）
| 文件 | 行 | 职责 | 路由 | 加载 |
|---|---|---|---|---|
| linker-assistant.bundle.js | 7,171 | Advisor（index.js ≈ 4,870 行） | chat/stream、chat/conversations、suggest、vision/*、design/pdf、tvb2b/v1 | enqueue 全站 |
| quote-configurator.bundle.js | 6,853 | **Planner**（index.js ≈ 5,170 行），自带 HTML 报告与 CSV | design/quick、design/snapshot、design/pdf、tvb2b/v1/{solution-scope/preview, storage-compatibility, project-products, quotes} | **页面正文硬写 `<script>`**（`pages/linker-planner/page.html:495`，`?v=0.13.457`，插件现为 0.13.474） |
| design-canvas.bundle.js | 3,871 | Site Detail / Canvas（index.js ≈ 2,500 行） | design/roof、roof-orientation、plz | 同上（`pages/design-canvas/page.html:223`，`config/asset-pins.json`） |
| ai-workspace.js / solution-scope.js / result-reading.js / tool-frame.bundle.js | 288/169/91/258 | 嵌入分析与共用小件 | workspace/analyze | enqueue |
| planner.js / planner-engine.js | 5/44 | **死代码** | — | 未加载 |

## 3. Planner 端到端
1. 输入：`readProjectIntake()`（bundle:4461+）按住宅/工商业/电站读表单 → `engineInputs()`（:4598-4640）改名成引擎词汇。
2. 服务端：`POST linker-ai/v1/design/quick` → `REST::calculate_quick`（rest.php:2832）→ `Engine::calculation_payload` 调 b2b-core `tv_b2b_project_calculation_inputs`（project-intake.php:1246）再改名 → 引擎 `/design/quick` → `price_package_materials`（rest.php:2092–≈2390）按 `tv_b2b_material_current`、`tv_b2b_product_commerce_state` 定价 → `tv_b2b_project_solution_scope`、`tv_b2b_project_preview_proof_issue`（计算凭证）、`tv_b2b_project_review_suggestion`。
3. 插件自算的只有定价投影、凭证、评审建议、本地化；**选型、sizing、BOM 全在引擎**。
4. 引擎路由：`/design/quick`、`/design/roof`、`/design/roof-orientation`、`/geo/plz/{plz}`、`/design/pdf` 在用；`/design/sld`、`/strings/enumerate`、`/yield/simulate`、`/storage/sweep`、`/econ/cashflow` 网站不调用。计算链：pvlib（SPA、Perez、Martin-Ruiz、Faiman、Huld cSi）+ PVGIS 5.3 TMY（`weather.py:87`，系统损失 14%）、PVGIS printhorizon 遮挡、LoD2 屋顶（`lod2.py`、`modules.py`）、BNetzA 上网电价（`tariffs.yaml`）、weasyprint PDF。
5. 物料：引擎直接读 `knowledge/components-db`；插件内 1.6 MB `data/components-db.json` 只服务 `linker/v1/components`；可订购性读 `/var/cache/linker-engine/material-registry.json`（`ops/sync_material_registry.py`）；价格 Woo 经 b2b-core。
6. 成为 Project/BOM：Planner 向 `tvb2b/v1/quotes` 提交显式 `lines` + `artifact_type/version` 或 `calculation_proof`（bundle:5040-5059，ADR-0018）；Advisor 用 `from_project`；ADR-0019 一行一产品；ADR-0029 套装无 material。

### 业务规则与硬编码（出处）
| 规则 | 位置 | 有据? |
|---|---|---|
| 每 kWp 5 m² | `design.py:34` | 注释"行业经验值"，无来源 |
| DC/AC 目标 1.15 | `design.py:35` | "blueprint row 6 practice" |
| **DC/AC 区间 0.7/0.8–1.6、舒适带 0.95–1.35** | `design.py:296, 340-344, 1123, 1522-1528` | **无来源，内联 4 次，住宅下限 0.7 与复核下限 0.8 不一致** |
| 电池可用 0.9、往返 0.92、拐点 90% 增益 | `design.py:13-15, 40-41, 1028` | "规划假设"/"HTW 风格" |
| `MAX_CI_UNITS = 8` | `design.py:116` | **无** |
| 候选逆变器/电池系列表 | `design.py:64-115` | 部分引数据表；**实为硬编码在代码里的销售范围** |
| 系列→兼容契约映射 | `design.py:120-181` | 部分 |
| 参考组件 Trina 460 | `design.py:62` 与 `bom.py:36` | 有裁定，但两份定义 |
| 线缆/连接器/CT material id、DC 线长 15 m | `bom.py:29-56` | 15 m 无说明 |
| CAPEX 分档 | `econ.py:228-240` | Fraunhofer/HTW |
| 上网电价 | `tariffs.yaml` `valid_until: 2027-01-31` | BNetzA 2026-08-02；过期仅置 `tariff_verified=false`（`design.py:1922`） |

## 4. 偏离信号
| 信号 | 证据 |
|---|---|
| 同一规则 3 份 | 引擎原因句德语：`l10n.py:239 _RULES`、bundle:2371 `REASON_DE`、b2b-core `engine-reason-l10n.php`（文件头自认"第三份"，靠 `reason-cases.json` 防漂移） |
| 输入词汇改名 4–5 处 | bundle:2263、:4598-4640；`project-intake.php:1195-1216`、`:1246-1275`；`class-linker-ai-engine.php:412-427` |
| 兼容"所属系列"2 份 | Python 硬编码字典（`design.py:120-181`）vs PHP 文本匹配（`material-compatibility.php:126-237`）；`contracts/` 与 b2b-core `data/` 各一份同字节 `compatibility-lists.json` |
| 两套报告 | 引擎 PDF（`report.py`）与 Planner 白标 HTML（bundle:3776 `buildCustomerReportHtml`） |
| BOM 定价放错地方 | 三工具共用，却在 Advisor 的 REST 类（rest.php:2092） |
| 正则编码产品知识 | 正则次数：Validator 388、Task_Planner 316、Resolver 87、Products 75；"fourth review of 142 part 2" 式补丁注释：Validator 113、Planner 84、Resolver 47、Products 38 |
| 死代码 | `planner.js`、`planner-engine.js` |
| 无调用方路由 | `admin/tool-truth-baseline`、`design/sld`、`assistant/message`（仅脚本/测试）、`chat/history`、引擎 4 个计算路由 |
| 构建链缺失 | 无 `src/`；Planner/Canvas 脚本带版本号写在页面正文 |
| 重复数据 | `spec-labels.json` 两插件各一份 |
| 硬日期/开关 | 逻辑里无硬日期；开关只有 `LINKER_AI_*` 常量 |

## 5. 可原样保留
`services/design-engine` 整体（确定性、可追溯到数据表页码、48 个 pytest、版本化发布与回滚；需把 DC/AC 区间提成具名常量、系列表移到数据）；会话存储（ADR-0016/0017）；`Linker_AI_Engine` 客户端；b2b-core 的 Project/材料/报价权威层（`tv_b2b_project_calculation_inputs`、凭证、`tv_b2b_material_current`、`tv_b2b_product_commerce_state`、`tvb2b/v1/quotes`）；组件库、注册表、`contracts/compatibility-lists.json`、`tools/rebuild_projections.py`；后台产品面板（ADR-0033/0034）；Tool Frame；provider-watch、weekly-report。
需重做：Advisor 的 NLU/Validator/Resolver 正则链；三个 bundle（恢复源码与构建）；REST 类按工具拆开。

## 6. 测试
| 位置 | 规模 | 运行 |
|---|---|---|
| `tests/unit` | 266 文件（121 php、106 py、37 mjs），≈76 个与 AI 工具相关 | `php file.php`（桩化 WP）；mjs 用 `node:vm` 跑真实 bundle；11 个 py 用 Playwright；**都从 bundle 按文本切函数** |
| `tests/integration` | 87 文件（63 php、24 py） | 需本地 WP 与引擎隔离主机（127.0.0.1:8795/8815）；5 个访问线上 |
| `tests/advisor-prototype` | 3 mjs | node 只读跑 bundle |
| `services/design-engine/tests` | 48 文件，带 PVGIS TMY 夹具 | `PYTHONPATH=. pytest -q tests/`，激活版本时自动执行 |
| 总入口 | `scripts/validate.py --profile fast|release|full` | |
