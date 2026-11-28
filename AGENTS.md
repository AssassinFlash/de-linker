- # de-linker · 工作规范

  ## 1. 工作原则

  - **直接解决问题**：基于真实需求和已核实的事实设计方案，保持实现简洁。多个方案均合理时直接选定并说明取舍；仅在涉及不可逆风险、权限边界或缺少业务事实时向业主确认。
  - **按客户结果交付**：从真实用户入口走通完整链路，按“七岁孩子首次使用即可无指导完成”的标准设计界面与交互。核心任务最多 3 步完成（同页填写并提交算 1 步），系统自动保存状态。配置器、Genie、报告和导出中的光伏组件均使用项目参数，询盘供货项取自 WooCommerce。
  - **干净交付**：代码、注释、commit、PR 描述与工作汇报只呈现最终正确结果，贴合项目现有风格，不留试错过程与 AI 署名。
  - **工具链执行**：
    - 任务启动、阶段切换与交付前，实际调用 `stop-that-shit:stop-that-shit`（按任务选 `change` 或只读）及 `stop-that-shit:stss`。
    - 工程环节按需使用 Matt Pocock skills：`domain-modeling` / `codebase-design`（设计）、`tdd`（实现与验证）、`code-review`（Spec + Standards 双轴评审）。
  - **有效验证**：先用源码、接口与现成测试定位问题；涉及界面与交互时，在真实页面实操并核看 EN/DE 及 1440/390 截图。页面复刻按同视口、资源就绪、禁动画条件验收动态区外像素一致（重设计模块除外）。未变更且仍有效的测试结果直接复用。

  全站各批次按[业主确认的整站蓝图](https://github.com/AssassinFlash/de-linker/issues/1167#issuecomment-7018452827)推进，验收范围写回[整站总图](https://github.com/AssassinFlash/de-linker/issues/548)。

  ## 2. 业务边界与核心流程

  - **站点定位**：`de-linker.com`（Linker Technology GmbH），WordPress + WooCommerce 搭建的 B2B 光伏储能询盘站，面向安装商、EPC 与经销商，英德双语同等。
  - **核心商务链**：产品或系统方案 → Solution draft / Lösungsentwurf → 询盘 → 报价单（Quotation / Angebot，有效期 30 天，无银行账号及付款指令）→ 线下交易（发票、收款、采购、发货全在线下完成）。询盘承诺 1 个工作日内回复，支持无产品、无账号直接留言。
  - **客户工具**：
    - **Genie - Linker's AI assistant**（德语：**Genie – der KI-Assistent von Linker**）：首条消息明示 AI 身份，不注册商标；公司、服务、物流类问题一句话转 `sales@de-linker.com`。规格见 [docs/specs/13-genie.md](docs/specs/13-genie.md)。
    - **Solution Configurator / Lösungskonfigurator**：覆盖全欧洲、新建光储、已知光伏规模、旧系统改造、已选设备、纯储能及大型项目（屋顶描绘可选）；输出整套方案、选型依据、兼容与资料引用、Stückliste 及可带 Logo 的 PDF。能源指标须有计算依据，不含回本期。按“比较初步方案 → 选方案 → 核对并提交询盘”验收。完整目标与视觉裁定见 [Issue #1132](https://github.com/AssassinFlash/de-linker/issues/1132) 和 [Issue #1153](https://github.com/AssassinFlash/de-linker/issues/1153)（视觉参照业主指定的 Preline 风格）。

  ## 3. 产品、账号、邮件与多语言

  - **产品与库存**：
    - WooCommerce 为唯一商品与库存事实源。保留原产品与 SKU，系统组合由工具按兼容规则实时计算。
    - **光伏组件边界**：站点不销售光伏组件，产品目录不含光伏组件；系统配置与报价中的组件统一设为通用参数，不带任何品牌或具体型号。
    - 产品参数以托管的原厂数据手册为准；资料缺失时标注待核实并保留现值。对外统一使用 `Product / Model / Series`（`Produkt / Modell / Serie`），不出现 Incoterms。发布与资料变更读 [docs/specs/609-product-publication.md](docs/specs/609-product-publication.md)。
    - 开启库存管理的商品按数量推导状态，前端仅展示“有货 / 暂时无货”（`woocommerce_stock_format = no_amount`）。
  - **账号与询盘**：
    - 全球国家开放注册（欧洲为主），分两步：① 公司名、业务类型、国家、网站或 VAT ID（至少填一项）；② 名、姓、邮箱、密码（不收地址与电话）。
    - 待审账号保持登录、隐藏价格、可询盘；限制账号展示原因并可询盘；拒绝账号无法登录。
    - 访客询盘仅收姓名、邮箱、公司（选填）、留言与隐私同意，自动带入草稿产品。页面左表单、右草稿；登录信息折叠为一行。联系留言与产品询盘共用一套存储。
    - 四个询盘状态：`Inquiry received / Anfrage eingegangen`、`Quotation in preparation / Angebot in Vorbereitung`、`Completed / Abgeschlossen`、`Cancelled / Storniert`。报价单在账户 Documents 下载。详细流程见 [docs/specs/11-commerce.md](docs/specs/11-commerce.md)。
  - **邮件路由**：
    - 客户可见发件与联系地址为 `sales@de-linker.com`（走既有 PHP `mail()`）；内部通知暂发 `sales@sunriverinverter.com`（走独立认证 SMTP），`chester@de-linker.com` 确认收信后抄送。
    - 测试发信只向单个测试邮箱发送（重写 To/Cc/Bcc），多收件路由通过 Outbox 队列断言。经授权的线上注册实测仅发通知、已收到、已批准三封，收件人限定 `sales@sunriverinverter.com` 与业主测试邮箱，测完关闭测试模式。
  - **多语言与文案**：
    - 德语统一使用 `de_DE_formal`（Sie），术语以 [tools/checks/commerce-terms.txt](tools/checks/commerce-terms.txt) 为准（校验命令：`just commerce-terms`）。
    - Polylang 免费版负责多语言基座，翻译目录用 `.po/.mo` 与 WordPress JSON。德语自动同步覆盖页面、产品、博客及可翻译词项并自动生效，同时保留人工德语；仓库模板经 `present` 发布并保持 Polylang 配对。
    - 商业文案使用 `linker-copywriting`，以业主确认原稿为底稿，追求自然流畅的 EN 与正式 DE。客户可见新文案（含事务邮件）走初稿 → 对抗评审 → 定稿并记入任务记录，参考 [docs/acceptance/2026-10-10/12/copy-review.md](docs/acceptance/2026-10-10/12/copy-review.md)。

  ## 4. 技术架构与模型

  - **前端与样式**：
    - 双运行时隔离：经典插件使用 WordPress React + `@wordpress/scripts`；`apps/planner` 为独立 React/Vite 应用（见 [docs/adr/0002-isolated-planner-runtime.md](docs/adr/0002-isolated-planner-runtime.md)）。
    - 页面排版在 LiveCanvas 动态模板，样式统一走 WindPress / Tailwind 单份 tokens（`apps/planner` 共用同一样式管线），PHP 只装配语义数据片段。已有付费许可为 LiveCanvas 与 SEOPress PRO，不新增付费插件或服务。
    - 前端源码修改须重建对应产物（planner 输出至 `plugins/linker-tools/build/planner/`），提交前运行 `build:check` 核对同步。
  - **后端与工具**：
    - PHP：Composer / PSR-4、WP_Mock / PHPUnit、PHPStan、WPCS + Woo sniffs。
    - Python：uv、FastAPI、ruff、mypy、pytest、Pydantic AI。具体版本以 `composer.json`、`pyproject.toml` 及锁文件为准。
  - **AI 模型与检索**：
    - Genie 对话、铭牌/附件识别、德语自动翻译、Jev 级联判分：`deepseek-flash` 官方通道。
    - Jev：`typesafe/jev-1.13`（OpenRouter 原生 `/v1/systemone`）。
    - Embedding：`gemini-embedding-2`（OpenRouter；仅在业主指定时启用 aihubmix 备用，异常显式抛出）。
    - PDF 检索：Docling 解析 + SQLite FTS5 + sqlite-vec（服务读取 `current/index.sqlite`），模型仅引用检索块 ID，数值由服务端回填。
  - **地图与外部底图**：
    - 仅在用户同意后加载外部底图，遵循服务端返回的 origin 白名单；用户撤回同意即停止加载外部资源。

  ## 5. 协作、部署与按需文档

  - **并行与隔离**：
    - 独立任务并行推进；每个并行子代理使用独立 git worktree 与独立 `node_modules`。
    - 主线负责集成、核验实际 diff 与测试、合并及发布。未经授权不执行提交、推送、合并或部署。
  - **环境与部署**：
    - 推进顺序：本地 → 评审站 → 线上。UI 验收实例先载入线上主题、uploads 与数据快照。
    - 部署前读 [docs/specs/17-cutover.md](docs/specs/17-cutover.md)。Hostinger 通过 `ssh hostinger-de-linker` 连接，WP-CLI 路径为 `/usr/local/bin/wp`。
    - 代码部署前留存本机数据库快照并原子切换；发现 `.prev` / `.failed` 残留时，核对 manifest 后按 `resume-deploy` / `rollback-deploy` 处理。
    - Engine 与 planner 独立发布（planner 入口：`tools/planner/publish/cli.sh`）。目标内生产部署与数据写入已有 2026-10-18 授权，操作须包含备份、回滚预案与线上读回验证。
  - **本地资源**：操作备份、实例与 worktree 前先读 [docs/agents/local-storage.md](docs/agents/local-storage.md)。任务结束即停用临时进程与浏览器、回收可重建副本，并汇报磁盘空间。
  - **外部调研**：优先使用 Apify（令牌仅从本地安全配置读取，不入库），配合浏览器、官方 API、Firecrawl、Crawl4AI 核实；不向厂商发送或代拟索件邮件。
  - **按需文档索引**：
    - 全局背景与架构决策：[CONTEXT.md](CONTEXT.md) · [docs/agents/domain.md](docs/agents/domain.md)
    - 议题与分诊：[docs/agents/issue-tracker.md](docs/agents/issue-tracker.md) · [docs/agents/triage-labels.md](docs/agents/triage-labels.md)
    - 商务与邮件规格：[docs/specs/11-commerce.md](docs/specs/11-commerce.md)
    - Genie 规格：[docs/specs/13-genie.md](docs/specs/13-genie.md)
    - 产品与资料发布：[docs/specs/609-product-publication.md](docs/specs/609-product-publication.md)
    - 切换与发布：[docs/specs/17-cutover.md](docs/specs/17-cutover.md)
