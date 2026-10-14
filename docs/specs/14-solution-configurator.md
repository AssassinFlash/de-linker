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
  - 资格：application=home、相数、单相 ≤4.6 kVA、DC/AC ≤ 厂商上限、`pv_input_kw ≥ kWp`、放行配对（三值）。
  - Stückliste：逆变器、电池模块/柜（按堆叠规则）、必要配件（电表/互感器按放行条件、线缆与连接器按 Stückliste 规则，熔断器按每路 MPPT 并联数）。
- `POST /design/commercial`：有负荷数据 → 负荷持续曲线定 kW/kWh，并联台数按控制器数据手册；无 → 指示区间。
- `POST /report/pdf`：报告模板 EN/DE，Logo 上传。
- 常量集中 `rules.py`，每条带来源；无来源标 `unverified planning assumption` 并在报告"假设"里披露。
- 不做：经济性、上网电价、CAPEX。

## 前端（`plugins/linker-tools` React 入口 `configurator`）
表单 `react-hook-form` + 由 ability/引擎 JSON Schema 生成的校验；地图 `maplibre-gl` + `terra-draw`；状态：空、计算中、无合格候选（说明原因与可放宽的条件）、方案、已保存；"Add all" 走 Store API 并读回；保存经 `linker/v1/solutions`（登录或 claim cookie）。

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
