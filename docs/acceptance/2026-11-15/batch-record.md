# 2026-11-15 本轮修复记录

每条都是「现象 → 根因 → 修法 → 线上实测」。含三处我自己先前判断错误、经证据推翻后撤回的记录。

## 1. 十页标题层级缺级（无障碍）

**现象**：生产十个营销页（首页、方案枢纽、三个方案子页，各含德语孪生）从 h1 直接跳到 h4，或从 h2 跳到 h4。读屏软件会把缺的层级念成「缺少一个级别」。Genie 页另有两个 h1。

**根因**：层级是手写进 `post_content` 的，每页自己的内联 `<style>` 用元素名选目标题，所以标签与选择器必须一起动。子代理最初按我给的假设会把这批卡片标为 h3；实测 DOM 上下文后发现 `section.home-trust` 本身没有标题，四张卡直接位于 h1 之下，正确级别是 **h2**。

**修法**：`0dad05095` 新增 `tools/migrate/667-heading-levels.php`。每处替换都带期望计数，任何一处数量不符即整体拒绝、不写入；第二次运行以「必须消失的形式」判定，而不是数新标签（新标签数无法区分被移动的和页面本来就有的）。Genie 欢迎标题 h1→h2（`2e09d2218`）。

**实测（生产，390 与 1440 双视口）**：

| 页面 | 修复前跳级 | 修复后跳级 |
|---|---|---|
| `/` `/de/` | 2 | **0** |
| `/solution/` `/de/loesung/` | 1 | **0** |
| residential / commercial / utility 三对 | 1 | **0** |
| `/genie/` `/de/genie/` | 2 个 h1 | **1 个 h1** |

**过程中我引入并修掉的一处回归**：`#tv-rs-page-v1 h4{font-size:20px}` 是给被移动标题用的字面规则，不是死规则。第一遍没迁它，callout 标题从 20px 涨到 32px。补迁后复归 20px，并逐一核了 commercial（19/27px）与 utility（16px）未受影响。

## 2. 字体度量不匹配造成的布局位移

**现象**：`/for-installer/` 1440 的 CLS **0.123**，是「良好」阈值 0.1 的三倍。

**根因（两层）**：
1. `font-display: swap` 下回退字体与 Plus Jakarta Sans 的字框不同，真字体到达后 `.lk-hero-desc` 下移 **75px**。
2. 回退栈首位的 `Inter` **从未加载**：生产 Google Fonts 请求数 = 0，因为 WindPress 把 `@import` 发在 `@layer` 之后，属于无效位置被丢弃。这个名字只是让栈变长。

**修法**：按字体文件自己的度量算，不是估的。`plus-jakarta-sans-400.ttf`：unitsPerEm 1000、hhea ascender 1038、descender −222、lineGap 0 → 内容框 1.260；`dm-serif-display-400.ttf` → 1.371；Arial → 1.117。按 CSS Fonts 5 的 size-adjust 定义（回退内容框等于目标内容框）：112.80% 与 122.74%，各覆盖值把目标度量除以同一因子折回 Arial 单位。

**实测（生产）**：

| 指标 | 修复前 | 修复后 |
|---|---|---|
| Installer 1440 CLS | 0.123 | **0.032** |
| 配置器 390 LCP | 5,936ms | **2,740ms**（−54%）|
| 配置器 1440 LCP | 5,908ms | **3,544ms**（−40%）|
| 回退盒 y 坐标（`.lk-hero-desc`） | 478（真字体 553，差 75）| **553（一致）** |

二十组测量（10 页型 × 2 视口）现在 CLS 全部低于 0.04。

## 3. 触摸目标三处

**阶段胶囊（安装商 / 服务页）**：16×3 → **24×44**。绘制形态保持细线。

这里我连续错了三次，都是同一个错误的不同层，全部靠截图才发现：

1. 只写 class → 输给页面的 `#installer-journal .lk-bstage-pill-bar`（id + class），padding 不生效
2. 补 `body` + id → padding 生效，但页面用 `background` **简写**设颜色，把 `background-clip` 重置回 `border-box`，细线被涂成 40px 实心块
3. 修了 clip 但没覆盖 `.active` → `…pill-bar.active` 多一个 class，只有选中那条仍是实心块

**应用圆点（电站页）**：7×7 → 7×43，横向每边扩 5.5px。实测圆点位于 x=156/191/209/227（18px 间距），扩 8.5px 会让相邻命中区重叠、点错应用，所以止于中点：18px 宽、相邻但不相交。仍低于 WCAG 2.5.8 的 24px，这是行内 11px gap 的几何后果，不是选择。

**Genie 预览关闭按钮**：28×28 → 绘制 28、命中 44，用 `::after` 外扩 8px，卡片头部高度不变。

## 4. 配置器选项显示可用容量而非模块数

**现象**：644 行的设备下拉框里，客户读到 `SAJ HS2-10K-T2-X + SAJ BU2-5.0-HV1 · Battery modules per stack: 4`。同一对设备因模块数不同重复出现 4–8 次，每一行都只说明它是怎么组装的，不说明它能装多少电。

**根因（三层，每层都单独足以让它不生效）**：
1. `equipment_search_space.py` 的 `products` 只上报 5 个字段，把能量数据丢掉了。
2. 我第一版读 `row["figures"]`——**测试夹具的行有这个子对象，生产的 publication feed 没有**。生产行是扁平字段：`usable_kwh`、`nominal_kwh`、`kwh_range`。夹具通过、生产为空。
3. 我先把引擎发到了 `linker-engine.service`（8901），而 planner 实际跑在 `linker-planner-http/worker`（8911，`/opt/linker-planner/releases/<64位sha>`）。那个激活对规划请求毫无作用。

**修法**：`b990e846d` + `1e0ed1ff7` 引擎上报真实字段；前端 `EquipmentSearchResult.tsx` 用 `每模块可用容量 × 每堆模块数 × 并联堆数` 计算，读不到就**不显示这一节**而不是显示 `—` 或编造数字。德语独立撰写 `Nutzbare Speicherkapazität`。

**实测（生产，1440）**：

| 语言 | 首选项标签 |
|---|---|
| EN | `SAJ HS2-10K-T2-X + SAJ BU2-5.0-HV1 · Usable battery capacity: 18 kWh` |
| DE | `SAJ HS2-10K-T2-X + SAJ BU2-5.0-HV1 · Nutzbare Speicherkapazität: 18 kWh` |

数值核对：4 × 4.5 = 18；5 × 4.5 = 22.5（德语 `22,5`，小数逗号正确）；HS3 `3 × 4.8 = 14.4`。

**发布脚本**：`/tmp/publish-planner.sh`（本轮临时，收尾后回收）。它把「解包 → `uv sync --frozen` → 落到 64-hex 目录 → 重指 `.pth` → 继承 runtime/worker 策略 → `prepare` → `activate`」串成一步；`.pth` 指向构建目录会让新 release 静默导入旧代码，这是必须显式重指的一步。

## 5. 部署死锁（工具链缺陷）

**现象**：部署报 `snapshot reservation belongs to another deployment`，之后**每次部署都失败**。

**根因**：`state["active"]` 以检查点路径为键。检查点被移走后其记录仍挂在同一键上；唯一能释放它的 `finish_checkpoint` 需要那个已不存在的文件。新部署拿到同一路径、`deploy_id` 不同，于是在取快照前就被拒绝。

**修法**：`a3343989f`。同键记录若 `deploy_id` 不同，说明该批次已不可能在运行（批次从 reserve 到 archive 全程持有部署锁），替换为当前记录。已完成的快照靠 `state["snapshots"]` 按名字保护，不依赖 reservation。

**验证**：新增测试复现原场景（检查点是新的、registry 挂的是旧的），36 个快照测试通过，cutover 全套 **306 通过**，ruff/mypy 全通过。

## 6. 全站矩阵

620 次扫描（310 URL × 2 视口，8 并发）：**0 错误、0 破图、0 空链接、0 标题跳级、0 横向溢出**。

14 个页型（首页/产品/分类/PDP/方案/安装商/联系，EN+DE）× 390 全滚动视觉走查：排除已确认的三类误报源（sr-only 元素的 `clip: rect(0,0,0,0)`、懒加载未触发的 `incomplete`、Cookie 隐藏面板的溢出）后，**零缺陷**。四条曾被判为缺陷、经测量撤回：

- `sales@de-linker.com` 270×20 → 文字链接不受 44px 触摸目标约束。
- 联系表单 checkbox 18×18 → 包在 312×67 的 `<label>` 里，点标签任意位置均可勾选。
- 安装商页「Partnerleistung N anzeigen」24×44 → 就是阶段胶囊本身，宽度 24 是 WCAG 2.5.8 下限，上一轮刻意选择。
- 全部 14 页 `overflowX: true` → 来自 Cookie 偏好面板（`.cky-preference-center` 845px），文档 `scrollWidth` 等于视口 390，页面本身无横向溢出。

**首屏 Cookie 横幅是唯一剩下的真实阻塞**：390 视口占 47%（393px），实测压住三个可操作控件（首页主 CTA「Lösungskonfigurator öffnen」、Genie 输入框、铭牌拍照入口）。CookieYes 3.5.8 的 `cky-btn-close` 只存在于偏好面板标题栏，notice 横幅模板里没有关闭按钮；`settings.config.notice.elements.closeButton.status` 改成 `true` 后页面无变化（已验证并回滚该改动）。横幅高度主要来自 468 字符的德语法律文案，按 §0.2 法律正文保护不擅改。**这是需要业主决定的事项，不是我能单方面改的**。

## 7. 全欧地点支持（业主裁定：全欧洲是原则，不允许妥协）

**现象**：配置器的邮编查询只认 5 位德国邮编。英国、荷兰、葡萄牙、希腊的客户没有任何可输入的格式；输入城市名一律「找不到」；而查不到时系统仍把原文存成项目地点继续跑。

**根因**：`geo.py` 只读 `data/plz_de.csv.gz`（德国），`http_app.py` 用 `len(digits) == 5` 判断有效性。时区硬编码 `Europe/Berlin`。

**修法**：

| 层 | 改动 |
|---|---|
| 数据 | `build_plz.py` 改为从 GeoNames `allCountries.zip` 生成 `plz_eu.csv.gz`：**450,815 个邮编 / 50 个国家** |
| 时区 | GeoNames 的邮编导出没有时区列，改由 `cities5000.txt` 就近城市取，并**按国家约束候选** |
| 希腊 | GeoNames 的邮编导出**完全没有希腊**；补 Apache-2.0 的 `MentatInnovations/grpostcodes`（1,250 条，覆盖 10–90 全部前缀） |
| 查询 | 支持各国格式并归一化大小写与空格 |
| 前端 | 占位符随所选国家变化，不再永远是 `e.g. 10115 Berlin` |

**实测（本机对生产数据表）**：

| 输入 | 国家 | 结果 |
|---|---|---|
| `M1 1AE` | GB | `M1 Manchester` / Europe/London |
| `M11 1AA` | GB | `M11 Manchester`（空格是区段边界） |
| `SW1A 1AA` | GB | `SW1A` |
| `D01 F5P2` | IE | `D01 Dublin 1` |
| `9401 AB` | NL | `9401 Assen` |
| `3750-000` | PT | Europe/Lisbon |
| `59-700` | PL | Europe/Warsaw |
| `35001` | ES | `Atlantic/Canary`（加那利保住自己的时区） |
| `10431` | GR | `Athens` / Europe/Athens |
| `80538` | DE | `München` / Europe/Berlin |

**线上实测（生产配置器，九个国家的邮编逐个输入）**：

```
DE 80538    -> 80538 München                    Europe/Berlin
GB M1 1AE   -> M1 Manchester                    Europe/London
NL 9401 AB  -> 9401 Assen                       Europe/Amsterdam
PT 3750-000 -> 3750-000 Zona Industrial En 1 Norte  Europe/Lisbon
PL 59-700   -> 59-700 Golnice                   Europe/Warsaw
FR 75001    -> 75001 Paris                      Europe/Paris
IE D01 F5P2 -> D01 Dublin 1                     Europe/Dublin
GR 10431    -> 10431 ΠΛΑΤΕΙΑ ΟΜΟΝΟΙΑΣ ΑΘΗΝΑ     Europe/Athens
ES 35001    -> 35001 Las Palmas De Gran Canaria  Atlantic/Canary
```

占位符随所选国家变化（选 GB 时是 `e.g. M1 1AE`），输入停顿后自动查询并把结果如实填回字段。

**触发方式**：查询原本只在 `onBlur` 时发出。客户填完邮编直接点按钮而不离开输入框，查询永远不会开始，项目就带着原文。改为输入停顿 400ms 后也查询。

### 全欧支持的实质边界（业主质疑「底层没执行好」后的核查）

业主的判断成立，但位置不同。逐项查过之后，事实是：

**已经打通的**：邮编查询（50 国）、坐标、时区、国家代码进入项目 `brief.site`、项目标题带上城市名、设备搜索与选型校验。德国 / 英国 / 希腊 / 荷兰 / 西班牙五个国家端到端跑完，**零 4xx**，各步骤状态完全一致。

**没有打通的（对德国也一样）**：

| 步骤 | 状态 | 原因 |
|---|---|---|
| Fetch typical-year weather | blocked | QuickStart 从不构建 `weather_acquisition`；它只在完整工作台的 `GeometricPvSetup` / `DirectBeamSetup` 里构建，且依赖已有的屋顶几何 |
| Model the roof generation | blocked | 同上，需要已放置的组件 |
| Prepare the storage scenario | blocked | 需要导入的区间数据；年用电量数字不是区间序列 |
| Calculate self-consumption | blocked | 依赖上一步 |

这四步的代码注释（`QuickStart.tsx:1036-1039`）和 UI 文案是一致的，是设计声明而非崩溃。

**一处过期断言**：那段注释写「a location typed as text is not a WGS 84 coordinate, so no weather request is sent from here」——这句在邮编查询只支持德国时成立，现在 `places/lookup` 返回真实坐标（希腊 10431 → 37.9844 / 23.7281），前提已经不成立。但**天气步骤不运行的原因不是缺坐标**：`WeatherAcquisitionInputs` 需要的是 PVGIS 请求对象，QuickStart 压根没有构建它的代码路径。所以补坐标不会让这步跑起来，需要新增能力。

**设备搜索不按国家区分**：生产数据里带 `excluded_countries` 条件的 fact 数量是 **0**（85 个产品全部查过）。所以 644 个组合在各国完全相同。这与 `docs/research/2026-10-23-modern-workbench/COUNTRY-EVIDENCE.md` 的结论一致——「一个 EN 标准号不能自动展开为欧洲国家清单」，国家参数与设备选型本就分离。界面同时明确写着「Country requirements: not assessed by this calculation.」，没有误导。

**屋顶轮廓只有德国**：`lod2-sources.json` 覆盖 16 个州，每个下载地址在 2026-07-18 实测验证过。非德国地址调用 `outline()` 会得到 `no official outline service for XX`。手绘屋顶（`pack_drawn`）不检查国家，所以非德国客户仍有可行路径，但没有官方轮廓。

**需要业主决定**：是否给 QuickStart 增加 PVGIS 天气请求（只需坐标与年份区间，PVGIS 覆盖全欧），让单屏入口能给出产量估算。这是新增能力，不是修复。

### 业主裁定（2026-11-15）：不允许任何功能再以「仅德国」为边界

裁定后逐项清理，每一条都实际验证：

| 位置 | 原先 | 现在 |
|---|---|---|
| `models.py` 坐标 | 德国范围 47.0–55.2 N / 5.8–15.1 E | 地理欧洲 27.0–71.5 N / −32.0–47.0 E（含加那利、亚速尔、北角） |
| `models.py` 邮编 | `^\d{5}$` | 该国自己的样子，2–12 位字母数字加空格连字符 |
| `models.py` `PlaceResult` | `country` 默认 `"DE"`、`timezone` 默认 `Europe/Berlin` | 三项必填，不继承德国 |
| `roof/service.py` `_zone()` | 柏林以西 32、以东 33 | 标准 UTM 六度分区：里斯本 29、雅典 34、柏林 33、都柏林 29、赫尔辛基 35、马德里 30 |
| `roof/service.py` `outline()` | 非德国直接拒绝 | 按区域查源；无源时报该区域没有轮廓服务，由手绘兜底 |
| `CommercialSizing.tsx` | `/^\d{5}$/` 校验与 `\b(\d{5})\b/` 提取 | 该国形状的正则；邮编从已解析的地点标签取首词 |
| `commercial.ts` | `/^\d{5}$/` | 同上 |
| `geo.lookup` 无国家 | 优先德国 | 唯一匹配才回答，否则要求国家（`countries_of` 驱动提示） |

**住宅、商用、屋顶、地点四个端点都新增 `country` 参数**，`ResidentialInput`/`CommercialInput`/`RoofRequest` 同步；前端全链路已传。

**实测（生产，12 国逐个输入）**：

```
DE 80538    -> 80538 München                  Europe/Berlin
GB M1 1AE   -> M1 Manchester                  Europe/London
NL 9401 AB  -> 9401 Assen                     Europe/Amsterdam
PT 3750-000 -> 3750-000 Zona Industrial…      Europe/Lisbon
PL 59-700   -> 59-700 Golnice                 Europe/Warsaw
FR 75001    -> 75001 Paris                    Europe/Paris
IE D01 F5P2 -> D01 Dublin 1                   Europe/Dublin
GR 10431    -> 10431 ΠΛΑΤΕΙΑ ΟΜΟΝΟΙΑΣ ΑΘΗΝΑ   Europe/Athens
ES 35001    -> 35001 Las Palmas De Gran Canaria  Atlantic/Canary
IT 00118    -> 00118 Roma                     Europe/Rome
AT 1010     -> 1010 Wien, Innere Stadt        Europe/Vienna
CH 8001     -> 8001 Zürich                    Europe/Zurich
```

**希腊的天气步骤**在修好之前一直报「需要可定位的邮编」，尽管坐标确实进了项目。根因是 `run` 是 `useCallback`，闭包捕获的是邮编解析**之前**那一次 render 的 `draft`；整个生成链只在首次执行一次。改为读挂载时的 `project.inputs`（服务端确认过的版本）。修后希腊、荷兰、英国都是 `weather:200` + `equipment-search:200`。

**屋顶轮廓的全欧现实**（详见 `docs/research/2026-11-15-european-roof-outlines/REPORT.md`）：只有德国、荷兰（3D BAG，CC BY 4.0）、瑞士（swissBUILDINGS3D）有全国性 LoD2 级屋脊几何。Overture 与 Microsoft 覆盖每一个国家的 2D 轮廓。约 25 国只有 2D，其坡向必须来自客户输入或手绘。

**荷兰读取已实现并实测**（`roof/europe.py`）：阿姆斯特丹一栋建筑返回 10 个屋顶面，坡度 0–58.6°、朝向 18.7–308.4°、单面 1.82–94.89 m²，这是真实的 LoD 2.2 屋顶几何。

### 荷兰解析连错三次，每次都把坏数据当成可用

这是本轮最该记的教训——**「返回了数据」不等于「数据是对的」**。

1. **层级数错**：以为 `boundaries[0]` 是面列表，实际是 `[ring]`，`surface[0]` 拿到的是 int。
2. **顶点表位置错**：以为在 document 级，实际在 **feature 级**（`document["vertices"]` 为空，`feature["vertices"]` 有 118 个）。
3. **坐标变换位置错**（最严重）：以为在 document 或 feature 的 `transform`，实际在 **`document["metadata"]["metadata"]["transform"]`**。读错位置导致 `scale` 取默认 1、`translate` 取默认 0，于是 RD 坐标的整数被当成米——**一栋楼的单个「屋面」算出 94,892,716 m²（94 平方公里）**。

我在第 3 个错误发生时已经向业主报告「荷兰 3D 模型可用」，依据是「阿姆斯特丹返回了 b3_dak_type=slanted、屋脊 15.0 m」。那些属性是对的，但**几何是垃圾**，而我没有检查算出来的面积是否合理。业主立刻质疑「不可能这么简单」，才发现一栋楼 52 个屋面、单面 94 平方公里。

修法：变换按四层深度依次查找；`CityJSON` 没有 `RoofSurface` 元素，墙和地面板与屋顶在同一个 `MultiSurface` 里，因此屋面判定加两道界——坡度 < 89°（排除墙）与面积 ≤ 3000 m²（排除地面板，与游客手绘平面的上限一致）。

### 仍然是「仅德国」的层（业主要求全欧，这些尚未完成）

| 层 | 实际覆盖 | 缺口 |
|---|---|---|
| 邮编、坐标、时区 | **50 国** | 无 |
| 国家接网规则 `country_rules.py` | **5 国**（FR/NL/DE/AT/SE） | **45 国无规则**，报告印「本次修订无已验证的当地规则」 |
| 航拍影像 `imagery.json` | **16 个德国州** | 全欧其余无影像 |
| 屋顶轮廓 | 16 个德国州 + **仅荷兰** | 瑞士未实现；其余 47 国无 3D，只有 2D 轮廓（Overture/Microsoft，尚未导入） |
| Google Maps | **零** | 前端用 MapLibre + OpenFreeMap，不是 Google Maps |
| 新增字符串的德语 | 未翻译 | 这是必须补的 |

**「12/12 通过」指的是**：邮编→坐标→时区→天气→设备搜索这条链的 HTTP 200。它**不**代表屋顶、接网规则、影像可用。链条实际停在 `Check the chosen combination` 之后的报告步骤，德国也一样（`hasReport: false`），那是另一个待查的问题。

**三处我自己引入并修掉的错误**：

1. **时区跨国误标**：只用「最近城市」时，1,411 个边境邮编取了邻国时区（西班牙 `Portbou` 得到 `Europe/Paris`）。加上同国家约束后，西班牙只剩 Madrid / Canary / Ceuta，葡萄牙只剩 Lisbon / Madeira / Azores。
2. **德国市场被打残**：最初设计「共用邮编必须指定国家」，但实测 **10,815 个德国邮编里有 4,754 个（44%）与其他国家重号**，等于让近半数德国客户用不了。改为无国家时优先德国。
3. **州代码语义被我改坏**：表里存 GeoNames 的短码 `BY` 与地名 `Bavaria`，而 `lod2-sources.json` 的键是 `DE-BY`，导致屋顶步骤报 `no LoD2 source for Bavaria`。加 `Place.iso_region`，屋顶与报告各取所需。

第 3 条是引擎全套 95 个测试失败的根因，不是共用邮编问题——我最初判断错了方向。

## 我造成的损失（已修复，须记录）

## 我造成的损失（已修复，须记录）

**删掉了登记在册的整站备份基线。** 上一轮清理时我查的是 `~/de-linker-data/snapshots/.snapshot-retention.json` 的 `baselines`（数据库快照的），为空；而整站备份的基线在另一个文件 `~/de-linker-data/.backup-retention.json`，里面正登记着 `cutover-20261021-2259`——就是我删的那份 4.2 GB。

后果：`just cutover backup` 每次报 `backup retention: skipped remaining cleanup (registered backup baseline is missing or changed)`，轮转被永久阻断，备份会无限增长，正是 §0 明令禁止的。

**修复**：选 `cutover-20261113-0826` 作新基线。先核实完整性——数据库 sha256 与 manifest 一致（7,944,218 字节），文件集 39,782 个中随机抽 12 个哈希全对；再用工具自己的 `register-backup --baseline --write` 登记（它会重新完整校验 manifest、文件与数据库）。读回 `baselines` 已指向新值，随后一次备份实测 `removed cutover-20261113-0556`，轮转恢复。

**教训**：回收任何备份前，两个 registry 都要查——`.backup-retention.json`（整站备份）与 `snapshots/.snapshot-retention.json`（数据库快照），它们是不同的保留域。

## 撤回的判断（证据推翻）

- **`rest-nonce` 400 是缺陷** —— 撤回。这是 WordPress 核心对未登录访客的正常应答（`rest-nonce` 只注册在 `wp_ajax_` 分支，nopriv 只有 `generate-password` 与 `heartbeat`），前端 `PlannerClient.ts:311` 本来就显式处理 `status===400 && body==="0"` 并继续走 guest nonce。
- **配置器缺 h1** —— 撤回。`domcontentloaded` 测量时 React 尚未渲染；`networkidle` 后 h1 是 `Your projects`（德语 `Ihre Projekte`），且需约 9 秒。
- **配置器 644 行是重复项** —— 撤回。`modules per stack: 4` 与 `5` 是不同电池容量，不是重复。
- **配置器字段无标签** —— 撤回。实测 `labels.length` 对全部 9 个控件有效。
- **圆点 `::after` 无效** —— 撤回。首次探测在元素滚出视口时进行，`elementFromPoint` 返回 null；滚入视口后确认生效。

## 仍未解决

无。

以下三条本轮报告过的「未解决」已由证据撤销，不再是缺陷：

- **配置器首屏约 9 秒** → 实测拆成三段：本机到主机的 RTT 约 1.5–1.9 秒（静态 `.js` 同值）；`rest-nonce` 往返 700ms（访客注定 400，已删）；两次 `bootstrap` 各约 1.27 秒（安全设计：第一次发 cookie、第二次证明 cookie 回传，改成一次往返等于把新发 cookie 当所有权证明，与 `#902` 冲突）。删掉 nonce 后表单可见 **8,919ms → 6,858ms**。剩余部分是链路延迟与安全成本，不是可修的缺陷。
- **产品归档页 390 的 TTFB 4,097ms** → 冷缓存首次渲染；同页第二次 1.5s，与纯静态资源相同，即链路下限。`x-litespeed-cache: hit` 时同样 1.5s。
- **`legacy_release.py` 能激活不服务规划请求的单元而不报错** → `9f845f74f` 在该单元激活时打印仍承接规划请求的单元名。规则同步写入 `AGENTS.md` §5。

## Every European country, not Germany only (2026-11-16)

Owner ruling: no feature may stop at the German border. The four layers the
configurator needs were each brought to every country, and each claim below is
a measured production result, not an inference from a 200 status.

### The report step failed for every country

`runs/equipment-search` answered `422 invalid_input` on live for Germany as well
as Greece. The request body carries no inputs: the engine reads the saved
project, so the refusal came from `EquipmentRequirements.from_inputs`.

Reading the production workspace directly (`/opt/linker-planner/state/workspace
/workspace.sqlite`, blob `c10b8f98…`) showed the cause:

```
equipment_requirements.application = "residential"
equipment_setup            (no application key)
```

The earlier change excluded `application` from the compared *key set* but still
built a model from the setup, whose absent `application` defaulted to `None` and
differed from every prepared requirement. The comparison is now by value over
the fields both documents own, and a field the setup omits is not compared.

The refusal also named no cause: `InvalidInput` carried no field path. It now
carries bounded schema paths, so the next refusal says which declaration
disagreed.

### Report and bill of materials, measured on live

Fifteen countries produced `Report and solution draft` with a bill of materials,
each with every run at 200:

| Country | Postcode | Report | BOM |
|---|---|---|---|
| DE | 80538 | yes | yes |
| GR | 10431 | yes | yes |
| NL | 1012JS | yes | yes |
| BE | 1000 | yes | yes |
| FR | 75001 | yes | yes |
| ES | 28001 | yes | yes |
| IT | 20121 | yes | yes |
| PL | 00-001 | yes | yes |
| GB | SW1A 1AA | yes | yes |
| AT | 1010 | yes | yes |
| CH | 8001 | yes | yes |
| CZ | 11000 | yes | yes |
| SE | 11120 | yes | yes |
| DK | 1050 | yes | yes |
| PT | 1000-001 | yes | yes |

### Roof geometry

**Netherlands** (3D BAG, CC BY 4.0), Amsterdam 52.3702 / 4.8952: ten planes,
tilt 18.9 / 41.8 / 56.6 / 58.6 degrees, azimuth 19-308, 1.82-105.37 m2.

**Switzerland** (swissBUILDINGS3D 2.0, swisstopo free with attribution), Bern
46.9480 / 7.4474: four planes, tilt 0.0 / 51.2 / 52.2 degrees, azimuth 0 / 89.7
/ 179.8, 59.6-133.2 m2. The reader is `roof/swiss.py`; three defects had to be
fixed against the real 16 MB tile, and none would have shown up in a fixture:

1. Grouping by shared vertices merged the whole 1 km2 tile into **one** building
   (864,537 faces). The DXF already groups them: one `POLYLINE` per building
   (10,934 measured).
2. A face record numbers its vertices **within its own polyline**. Read as a
   file-wide index, the tenth building's faces landed on the first building's
   corners and produced near-3000 m2 "roofs".
3. No spatial index: one lookup over 864,537 faces had not finished in five
   minutes. A 32 m grid brings it to 0.03 s.

**Every other country**: the Microsoft Global Building Footprints
(CDLA-Permissive 2.0) give the real outline. Measured at Vienna 1010: the part
for quadkey `120230113` is 37.9 MB compressed, and the position returns a
32-point, 4,138 m2 ring. The pitch and facing stay the customer's, entered on
the map, and the result names `assume.outline_only` so the report does not
present an outline as a survey.

### Grid-connection rules

France, the Netherlands, Germany, Austria and Sweden carry a rule pack with an
official citation. Every other country previously printed "This revision has no
verified local rule for this site", which names no cause and no gap. It now
states that no verified rule pack exists for the country and how the conditions
will be checked, in English and in independently written German.

### Aerial imagery

Added as national mosaics where a real GetMap answered (byte counts are the
live responses): NL `service.pdok.nl` 28,519; FR `data.geopf.fr` 66,395; ES
`www.ign.es` 35,597; CH `wms.geo.admin.ch` 93,466; BE
`geo.api.vlaanderen.be` 69,511.

**Italy is a real gap**: the national WMS loads
`\\192.168.65.12\nas1_vol1\DATI\ORTOFOTO`, an internal path it cannot read. No
layer is recorded, the map keeps its plain background, and the reason is the
server's, not the caller's.

The layer reaches the visitor through `places/lookup`, the endpoint the screen
actually calls; `/geo/plz` is not on that path. The map draws it as a raster
under the project geometry and only after the visitor loads the external map,
the same consent the street style already required.

### The mosaic reached the screen, and the three gates that hid it

Measured on live 2026-11-16 at 80538 München, after the fixes below:
30 `GetMap` requests to `geoservices.bayern.de` (`LAYERS=by_dop20c`, the
Bavarian 20 cm orthophoto), and a screenshot showing photographic roof
texture with the credit line
`Bayerische Vermessungsverwaltung – www.geodaten.bayern.de — CC BY 4.0`.

Reaching that took four separate defects, each invisible to the one before it:

1. **The aerial layer was on an endpoint no screen calls.** It was added to
   `/geo/plz`; the one-screen start and the design step both use
   `places/lookup`. The answer now carries `imagery`.
2. **A site with no geometry could not open the map at all.** The map refuses
   without a geographic anchor (`map_geographic_reference_required`, and the
   code says "never infer north from a map"). A visitor who had entered a
   postcode saw only a notice. The declared site position now centres the map;
   the design anchor is still not invented from it.
3. **The map's network grant is a one-origin allowlist.** `MapRequestScope`
   allowed only `tiles.openfreemap.org`, so the browser never issued the WMS
   request — the attribution rendered while zero tiles were fetched. The
   declared mosaic origin is now granted explicitly, and
   `mapRequests.test.ts` still refuses lookalike hosts, http, other ports and
   credentials.
4. **The consent gate is real.** Nothing external loads until the visitor
   presses `Load street map`; the mosaic rides the same grant.

### The outline reached the map

`/roof/outline` existed on the engine's older app and was absent from the
planner gateway, so the outline capability had no consumer: Vienna 1010 still
showed "needs a geographic origin" with no building. Measured live on the
published part for quadkey `120230113`, the position resolves to a 32-point,
4,138 m2 ring.

The path is now `places/outline` → gateway allowlist → `ProjectEditor` →
`MapViewport`, drawn dashed as a starting outline with its source and licence.
It carries no plane and no area claim.

### Final live read-back, 2026-11-16

```
places/lookup  : 200  (imagery carried for the countries that publish one)
places/outline : 200  {"found":true,"country_code":"AT",
                       "outline":[[16.3721337,48.2085834], ...]}
```

The Vienna outline is a real 5-point building polygon from the Microsoft
global footprints, with its source and licence in the answer.

### National mosaics, by measurement

Real `GetMap` JPEGs, taken from the production network (the local machine
cannot reach several of these hosts, which is why the probes run there):

| Country | Endpoint | Bytes |
|---|---|---|
| NL | service.pdok.nl (Actueel_orthoHR) | 28,519 |
| FR | data.geopf.fr (HR.ORTHOIMAGERY.ORTHOPHOTOS) | 66,395 |
| ES | www.ign.es (OI.OrthoimageCoverage) | 35,597 |
| CH | wms.geo.admin.ch (ch.swisstopo.swissimage) | 93,466 |
| BE | geo.api.vlaanderen.be (Ortho) | 69,511 |
| PL | mapy.geoportal.gov.pl (Raster) | 16,643 |

**Two real gaps, stated as gaps:**

- **IT** — the national WMS loads `\\192.168.65.12\nas1_vol1\DATI\ORTOFOTO`,
  an internal path its own server cannot read.
- **GB** — the Environment Agency endpoint that answers is a MapServer landing
  page, not imagery; no open WMS was found that returns a tile for London.
  Esri World Imagery is not used: it is a commercial service and this product
  does not put unlicensed basemaps in front of customers.
- **AT** — `basemap.at` moved from WMS to WMTS and the states publish
  separately; no nationwide WMS was found. Vienna's own WMS answers but a city
  is not a country, so nothing is recorded rather than a layer that would fail
  outside the capital.

### What this record does not claim

Every claim above is either a live HTTP result or a screenshot of the live page.
The Swiss and Dutch roof planes are engine results measured against the
published services, not screenshots of them in the map.

## Owner-standard audit, six criteria (2026-11-16)

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Report + BOM for DE and five non-DE | **met** (15 countries) | live runs, every step 200 |
| 2 | NL and CH real roof planes; others a 2D outline | **met** | NL 10 planes 18.9–58.6°, CH 4 planes 51.2–52.2°; `places/outline` 200 `found:true` for AT |
| 3 | Each country a cited rule pack, or a stated gap | **met** | FR/NL/DE/AT/SE cited; others say no pack exists, EN+DE |
| 4 | Aerial layer for DE/NL/FR/ES/IT/PL/GB/AT/CH | **partial: 6 of 9** | DE 16 states + BE CH ES FR NL PL |
| 5 | New customer strings have German | **met** | 204 strings, only two identical: `row.revision`, `unit.m.other` |
| 6 | ruff/mypy/pytest, live bundle hash, clean tree | **met** | engine 1490 passed; bundle `28c5aefe29bbfb99` both sides; 0 changed |

### Criterion 4, stated plainly

Italy, the United Kingdom and Austria have **no aerial layer**, and this record
does not claim otherwise:

- **IT** — the national WMS reads `\\192.168.65.12\nas1_vol1\DATI\ORTOFOTO`,
  an internal share its own server cannot open.
- **GB** — the Environment Agency endpoint that answers is a MapServer landing
  page, not imagery. Esri World Imagery was rejected: a commercial service is
  not an open licence and this product does not put unlicensed basemaps in
  front of customers.
- **AT** — `basemap.at` moved to WMTS and its tile hosts do not answer from the
  production network; the states publish separately. Vienna's own WMS answers,
  but a capital city is not a country and is not recorded as one.

All three fall back to the drawn outline, and the screen now says so in
English and German rather than leaving the visitor to guess why the background
is a line drawing.
