# #14 Solution Configurator / Lösungskonfigurator

依据：`docs/research/2026-10-09/planner-methods.md`（方法规格与 P0/P1 清单）、`pv-wholesale-selection-tools.md`（同类形状）、`old-repo-plugin-and-planner-inventory.md`（旧引擎知识的来源），AGENTS.md §1。页面地址 `/solution-configurator/`（德语 `/de/loesungskonfigurator/`，业主 2026-10-12 裁定：不保留旧 slug；旧地址 301），标题改名。

## 三屏
1. **输入**（住宅 / 工商业 / 电站三段）
   - 住宅：年用电 kWh、光伏 kWp（或"还没有，按屋顶估"→ 屋顶步）、相数、备用电源（无 / 需要 / 需要且接受加配件）、热泵/电动车（是/否，只影响用电区间）、既有逆变器型号（加装场景，可选）、邮编。可选屋顶步：地图定位 → 官方建筑轮廓（LoD2，按旧规格重写）→ 倾角朝向 → 组件数估算（参考组件作为设计假设披露）。
   - 工商业：采集表（并网功率 kVA、年用电、目标：削峰/自用/备用、15 分钟负荷数据文件（CSV，可选）、现场条件）；有负荷数据 → 计算；无 → 指示区间 + 转询盘按钮。
   - 电站：询盘表单。
2. **方案**：推荐的整套系统（逆变器 + 电池 + 必要配件，数量、有货、放行依据），每件卡片可换成同类备选；一个按钮 "Add all to solution draft / Alles zum Lösungsentwurf hinzufügen"；"Save solution / Lösung speichern"（进账户）。
3. **设计报告**（方案下方，可下载带 Logo 的 PDF）：场地与输入、发电量估算（区间）、自给率与自用比例（区间）、选型依据（每条规则与命中值）、兼容放行与文件引用、Stückliste、假设与限制、下一步。无回本期与现金流。

## 引擎（`services/engine`，新包，FastAPI；只读 #8 的 feed 与 compatibility）
- `POST /design/residential`：输入上述字段 → `{yield:{kwh_year_range}, storage:{usable_kwh_range, basis:['HTW rule 1/2/3']}, metrics:{autarky_range, self_consumption_range}, candidates:{inverters[], batteries[], accessories[]}, selected:{...}, rules:[{id, passed, value}], warnings[]}`。
  - 产量：pvlib + PVGIS（按邮编、倾角、朝向；缓存按 0.05° 网格）。
  - 定容：HTW Berlin 三条上限（≤1.5 kWh/kWp、≤1.5 kWh/MWh 年用电、第三条按 planner-methods.md 的规格），备电预留另加；输出区间。
  - 自给率/自用比例：HTW 式查表（规格里的表），输出区间，不做逐小时模拟。
  - 资格：application=home、相数、单相 ≤4.6 kVA、DC/AC ≤ 厂商上限、`pv_input_kw ≥ kWp`、放行配对（三值）；备电请求另要求放行电池配置能容纳备电预留（见 2026-10-21 变更记录）。
  - Stückliste：逆变器、电池模块/柜（按堆叠规则）、必要配件（电表/互感器按放行条件、线缆与连接器按 Stückliste 规则，熔断器按每路 MPPT 并联数）。
- `POST /design/commercial`：有负荷数据 → 负荷持续曲线定 kW/kWh，并联台数按控制器数据手册；无 → 指示区间。
- `POST /report/pdf`：报告模板 EN/DE，Logo 上传。
- 常量集中 `rules.py`，每条带来源；无来源标 `unverified planning assumption` 并在报告"假设"里披露。
- 不做：经济性、上网电价、CAPEX。

## 前端（`plugins/linker-tools` React 入口 `configurator`）
表单 `react-hook-form` + 由 ability/引擎 JSON Schema 生成的校验；地图 `maplibre-gl` + `terra-draw`；状态：空、计算中、无合格候选（说明原因与可放宽的条件）、方案、已保存；"Add all" 走 Store API 并读回；保存经 `linker/v1/solutions`（登录或 claim cookie）。

### 脚本译文（#302）

德语唯一编辑源为 `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`。
`just i18n-tools` 用 `wp i18n make-json --no-purge` 生成按入口路径 MD5 命名的脚本 JSON，
并用 `msgfmt --check` 编译 PHP 的 MO；不手改 JSON，不清除 PO 中的脚本消息。
配置器条目保留真实源码引用，并通过 `build/configurator.js` 引用归到已 enqueue 的入口，
因此懒加载屋顶组件也使用入口预载的同一组译文。
`Assets::register()` 的 `wp_set_script_translations()` 沿 WordPress 原生路径读取该文件。

配置器与 Genie 已有的不同德语措辞通过 `configurator` gettext context 保留：
`Sent, but the draft does not show it yet. Please check.`、`Not added. Try again.`、
`Saved to your account.`；两侧 EN/DE 正文均不改写。
`just i18n-coverage` 检查 linker-tools 运行时 PHP、JS、TS 的消息是否进入 PO，
并在临时目录调用原生 `make-json --no-purge`，逐字节比较所有随插件发布的 JSON；
缺失、多余或改动的 JSON 都失败。CI 安装与本地栈一致的 WP-CLI 版本运行此门。

## 验收
- [ ] 8 个典型户型（planner-methods.md 表）输出落在 HTW 上限内并给区间；3 个合规用例（单相 6 kW 排除、PV 上限不足排除、每路 MPPT 熔断数量）通过。
- [ ] 住宅三相 10 kWp：方案含住宅三相逆变器 + 有放行文件的电池；全部加入后 Lösungsentwurf 数量正确；报告 PDF EN/DE 各一份。
- [ ] 工商业：带 15 分钟 CSV 得到 kW/kWh；不带得到指示区间与询盘按钮。
- [ ] 屋顶步：一个真实地址（PLZ 80538 慕尼黑夹具）得到轮廓与组件数。
- [ ] 视觉验收：三屏 + 屋顶步 + PDF，EN/DE × 1440/390。

## 页面装配（工具页归一，2026-10-13）
配置器页 `/solution-configurator/`（德语 `/de/loesungskonfigurator/`）与对比页、Genie 工作区同一条路：LiveCanvas 每页模板 + 数据短代码，页面正文不再承载应用。
- 模板文件 `plugins/linker-commerce/content/livecanvas/configurator_page.html`（EN/DE 共用一个文件：模板只是挂载点，页面上每个字都由应用自己按页面 `lang` 出），模板 slug `linker-configurator` / `linker-configurator-de`，模板文章由 `present` 从文件建立，`Templates::assign_pages()` 把 `/solution-configurator/`（en）、`/de/loesungskonfigurator/`（de）分别指派到各自语言的模板。
- 挂载点由 `linker-tools` 的短代码 `[linker_configurator]` 打印（`includes/Configurator/Mount.php`）：`data-linker-app="configurator"`、引擎地址（选项 `linker_engine_url`）、REST 根与 `wp_rest` nonce，并 enqueue 构建条目 `linker-tools-configurator`。零设计、零文案——应用自己的 `build/configurator.css` 决定尺寸与颜色。
- 在此之前，本机实例的挂载靠实例本地 mu-plugin（`100-t109-configurator-mount.php`，从不部署），没有它的实例（如 t110）该页渲染的是页面正文里旧项目的 Planner 应用。装配进入 `present` 后，任何实例 `just present <name>` 即得同一页面。

## 变更记录
- 2026-10-12（业主裁定，slug 不保留）：页面地址 `/linker-planner/` → `/solution-configurator/`（德语 `/de/linker-planer/` → `/de/loesungskonfigurator/`）。旧地址入 `legacy-redirects.json` 的 `pages` 表 301（德语请求经 Polylang 孪生落到德语新址，一跳到 200）；页头/页脚、`SizeHint`、侧栏卡片链接与迁移工具 `12-site-chrome.py`（新增 slug 改名步，`resolve` 按新旧两种 slug 找页）同步。
- 2026-10-13：页面装配入 `present`（上节）：`Templates::PAGES` 增两条指派、新增模板导出与 `[linker_configurator]`；证据为本机 t110 修改前后（修改前 `curl /linker-planner/` 出现旧应用标记 `qcfg-root` ×121 且无 `data-linker-app="configurator"`，修改后 1 处挂载点、0 处旧标记）。
- 2026-10-09（#5）：引擎的地址在选项 `linker_engine_url`：本地由 `just serve <name>` 写入 `http://127.0.0.1:<端口>`，线上由切换（#17）写入 VPS 地址；调用引擎的代码从这个选项读。

- 2026-10-14（线上引擎自签证书下浏览器直连不可行，实测后改道）：配置器不再由浏览器直连引擎，`Mount` 交给前端的
  `data-engine-url` 是 `linker-tools` 自己的同源路由 `linker-ai/v1/engine/<path>`（`Configurator\EngineProxy`），
  由站点 PHP 带着既有证书钉扎完成服务端跳跃（与 Genie 同一条路）；白名单=应用实际调用的路径集，状态码原样透传，
  `report/pdf` 走字节流直出。选项 `linker_engine_url` 仍是服务端地址（代理与健康监控读它）。前端配置形状不变
  （仍读 `data-engine-url`）。

- 2026-10-21（#482、#483，走查 #478）：
  - **H2 T3 的电表只有一条事实**：合同对 H2 只保留 `included` 一条。H2 手册 §2.2 Auspacken（PDF-S. 36 英文 / S. 7 德文）把智能电表、三只电流互感器和 10 m 通信线列进交付范围；原条件写的 §4.1.2 / PDF-S. 12 不符，已改。SAJ 配置说明 §5.1（PDF-S. 32–33）的 DTSU666 是这只随箱三相表的配置对象，不是加购件。重复的 `included: false` H2 电表记录已删；`_requirement_lines` 仍只列 `not included`。同一事实也落在 `data/compatibility-lists.json`（H2 的 `meter_documented` 删除、交付文本改正）；引擎夹具生成器 `scripts/build_fixtures.py` 增加同一条覆盖，重生成不会带回旧引用。回归读 shipping 合同：H2 的 Stückliste 没有额外电表行，GW10K 没有电表行，HS2 仍有一只 DTSU666。
  - **备电是定容输入，不是逆变器资格**：本规格第 16 行只要求预留另加，第 18 行的资格清单没有点名 backup。线上 feed 不含户用逆变器的 `backup_power_kw`（产品 meta 有该图值，但引用只写文档名、没有托管 URL，feed 只收带托管引用的图值），所以把 backup 当硬资格会让 `needed` 与 `needed_accessory_ok` 成为死输入。现在只检查**放行电池配置的可用容量 ≥ 备电预留**（`backup_storage`）；配置上限取自数据表堆叠上限（`stacking.configurations` 的 `modules_per_stack` / `stacks_parallel_max` / `modules_per_system_max` / `max_battery_modules`），不新增阈值。HTW 区间仍是上限：电池不必顶到区间顶，但必须能把预留从日常循环中留出。`needed_accessory_ok` 仍把合同写明的备电配件列入 Stückliste。没有电池能容纳预留时返回 `no_candidate`，放宽句给出本选择中最大的放行配置容量，不再表现为死输入。候选电池只保留能容纳预留的配置，换电池不能绕过这道检查；区间内最大一档低于预留时，按既有的 smallest-above 规则提出能容纳预留的下一档并标“高于 HTW 上限”，不因上一档低于预留而丢掉整只电池。HTW 不建议配储（PV < 0.5 kWp/MWh）时，备电请求仍按预留定容并检查放行电池，不再返回不带电池的方案；提示语改用 `warn.no_storage_backup`（电池用于备电预留，不再说“提案只含逆变器”）。报告只证明预留可被放行电池容纳，不声明逆变器有备电输出；这一点由团队在询盘阶段按数据手册核实。回归（EN/DE）：#478 C17（80538 / 5000 kWh / 10 kWp / 三相 / 3 kW × 4 h）得到方案，预留 12.77 kWh，所选 20 kWh 电池覆盖预留。
