# #548 安装事实线 · 验收索引（2026-10-31）

这份索引只做一件事：让人一眼看出每项**验证到什么程度**、证据在哪、还有什么没验证。
详细记录在两份文档里，这里不重复内容，只给判断。

状态用词是固定的：

- **已读回** —— 在生产上取到了实际数据或报告内容，不是推断。
- **已隔离** —— 失败被定位到具体代码路径，且证明了这是正确行为或已知缺口。
- **未验证** —— 没有证据，附解除条件。

## 生产状态

| 项 | 值 | 状态 |
| --- | --- | --- |
| `knowledge` / `engineering` 消费者 | 均 `ready` | 已读回 |
| 带 `_linker_installation_facts` 的商品 | 534 中 9 个，79 条 | 已读回 |
| `source_revision` | `dc2b9fa7d994…` | 已读回 |
| `preview --production` | `{"changes": 0}` | 已读回 |

## 功能项

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 事实写入商品元数据 | 9 商品 79 条，`verify` 无待办 | `installation-facts-apply.md` |
| 工程 feed 携带事实 | `EngineeringFeed::item()` 含 `installation_facts` | 同上 |
| 引擎物料投影 | `status: documented`，字段与计划一致 | 同上 |
| `project_materials` 消费 | 真实 feed 产 17 条带页码行 | 同上 |
| 报告 BOM（德文，生产读回） | 13 行，德语标签与 `p.152–155` | `installation-facts-apply.md` 德文报告读回 |
| 报告 BOM（英文，生产读回） | 13 行，英文标签与 `p.153–155` | `installation-facts-apply.md` 英文报告读回 |
| 设备检查 | `succeeded`，5 项检查 3 satisfied | 同上 |
| **多台逆变器 + 线缆 + 安装事实** | ✅ 生产读回：项目 `260a61d2…` 报告 25 章节，BOM 16 行含 2 台逆变器与 12 条事实，路由 3 行 | `installation-facts-apply.md` 末节 |
| 路由报告 | `succeeded`，含 `installation-routing` 与免责声明 | 同上 |
| 已保存方案读取（作者） | 返回原始输入，不含旧价格 | `saved-solution-readback.md` |
| 已保存方案权限边界 | 他人读取得 404，不泄露 | 同上 |

## 已隔离的两处"看起来像缺陷"

| 现象 | 结论 | 依据 |
| --- | --- | --- |
| `Installation routing` 显示 0 | 正确行为 | 该字段来自兼容合同的 `meter`/`backup`，不读安装事实；路由报告另需 `installation.cable_runs` |
| `product_evidence_changed` 拒绝设备检查 | 准备状态的时间差，非数据不一致 | `engineering` 未 `ready` 时 `prepared_view` 不含该商品；恢复后同一项目成功 |

## 未验证（附解除条件）

| 项 | 缺什么 | 解除条件 |
| --- | --- | --- |
| 界面读回 `?saved_solution=8207` | 一个能登录 user 1 的浏览器会话 | 提供凭据，或授权临时启用一次性登录后移除 |
| 真实询盘与 Genie 提交 | 保护**正常工作**；自动化客户端不触发交互，拿不到 token | 人工在浏览器中打开询盘页或 Genie，聚焦表单产生 token 后提交。见下方「Turnstile 的准确状态」 |

## 已合并的修复

| PR | 内容 |
| --- | --- |
| #794 | 引擎拒因码在网关原样透传；文档哈希请求内复用；计划重冻 |
| #795 | 主线计划重冻（原计划 `preview` 直接拒绝） |
| #796 | `refresh` 命令，重 pin 不再靠手改 |

拒因码透传已验证在生产生效：错误码从 `linker_planner_upstream` 变为
`linker_planner_not_found`。哈希复用实测同请求第二次 `manifest()`
从 4.8 s 降到 0.67 s，内容一致。

## 方法注记

`ProductEvidenceChanged` 的 12 个 raise 点共用一个错误码，引擎又丢弃 message。
本轮据此连续做出 6 个错误推断（主机负载 → manifest 重建 → 旧 manifest →
LiteSpeed 缓存 → 兼容合同 → 平台夹具）。正确顺序是**先复现、再读代码**。

另需注意：`sources/saved-solution` 是**网关层路径**（`Gateway.php:302`），
经 `Transport` 直连引擎会得到 `not_found`，看起来像功能坏了，实际不是。

## Turnstile 的准确状态（更正早前的描述）

早前记录写作「Turnstile 拦截询盘」，这个说法**不准确**。实测后的事实：

| 项 | 实测值 |
| --- | --- |
| `Configuration::active_mode()` | `enforce` |
| `ready()` / `configured()` | `true` / `true` |
| `test_keys` | `false`（真实密钥，非测试密钥） |
| `/proforma-request/` 页面 | `200`，**页面内没有 Turnstile 脚本** |
| 验证发生的位置 | 提交时，服务端调 `Protection/Turnstile.php` 的 siteverify |

也就是说：

- **页面不被拦截**。询盘页正常渲染。
- **保护在提交时生效**，且配置正确、使用真实密钥。
- 我的自动化验收拿不到有效客户端 token，因此**提交被正确拒绝**。

这属于「保护按设计工作，自动化客户端不被允许」，不是功能缺陷，也不是「外部条件导致功能未完成」。

真实询盘与 Genie 提交需要**人工在浏览器中完成**——这正是该保护的用途。用自动化绕过它去换取验收通过，是错误的做法，本线没有这样做。

### 一处自我更正

排查过程中我 grep 到两个 `pow`，一度认为存在 proof-of-work 机制。实际是
`/product-category/accessories/backup-power/` 里的子串，属误匹配，已推翻。

### 完整机制（从 `protection.js` 与生产页面读出）

我早先 grep「`/proforma-request/` 页面里没有 Turnstile 脚本」，这句本身没错，
但据此得出的「被拦截」结论是错的。真实设计是**交互触发、异步加载**：

1. 页面加载时**不**注入 `challenges.cloudflare.com/turnstile/v0/api.js`；
2. 用户第一次 `focusin` 或 `pointerdown` 表单时，`warm()` 才异步加载脚本并渲染 widget；
3. 提交时走两步：服务端 `POST /wp-json/linker/v1/protection/prepare` 换取 sitekey，
   客户端取得 token，再 `POST …/verify` 换取有时效的 proof；
4. `linker_proof` 隐藏字段由此填充，服务端再调 Cloudflare siteverify。

生产实测确认这套链路已注入：

```
linkerPublicProtectionConfig = {
  "api": "https://de-linker.com/wp-json/linker/v1/protection",
  "nonce": "754057849d",
  "mode": "enforce",
  "businessVerification": "required",
  "language": "en"
}
```

`protection.js` 在页面中出现 3 次（不同区块各挂一次）。

因此：**自动化客户端不触发交互、拿不到 token，提交被正确拒绝。**
这不是缺陷，也不需要「修复」。人工在浏览器中打开询盘页、聚焦表单，widget 会正常出现。

### 受保护动作清单与两种挂载方式

服务端 `Configuration::verification_required()` 对以下动作全部返回 `true`：

```
inquiry      required=yes
contact      required=yes
draft_write  required=yes
genie        required=yes
```

`Protection/Actions.php` 另列 `genie_contact`、`genie_inquiry`；
`Protection/BusinessPolicy.php` 把 `contact`、`inquiry`、`genie_contact`、
`genie_inquiry`、`conversation_mail` 归为业务验证类。

**两种挂载方式，同一套 proof 机制：**

| 入口 | 取 proof 的方式 |
| --- | --- |
| 询盘、联系、草稿写 | `FormFields.php:33` 渲染 `linker_proof` 隐藏字段，`protection.js` 提交前填充 |
| Genie | React 组件调 `window.linkerPublicProtection.proof('genie', widget)`，不走表单字段 |

实测：`/genie/` 与 `/de/genie/` 均注入 `linkerPublicProtectionConfig`（`mode: enforce`），
但页面中**没有** `data-linker-protected-action` 属性——这是 React 挂载方式的正常表现，
不是保护缺失。

因此「Genie 与询盘的失败提示不同」不表示两套机制，只是同一个 proof 在两种界面上
的呈现差异；根因一致：都需要真人交互产生 token。

## 客户侧报告 PDF 下载：生产上无样本，未验证

报告的 **API 内容**已逐行读回（英德各 13 行，见前文）。但**客户拿到的 PDF 文件**
走的是另一条路径，本轮未能验证。

### 机制

`Planning/ReportDownload.php` 注册：

```
GET /wp-json/linker/v1/inquiries/{id}/planning-report/{handoff}?key=...
```

- `{handoff}` 是 32 位十六进制 id，存在订单元数据 `_linker_planning_projects` 里
  （`Context::META`），由 `Context::stored()` 按 `valid_reference()` 过滤后返回。
- 权限三重之一：`manage_woocommerce`、订单客户本人、或持订单 `order_key`。
- 内容由 `linker_tools_planning_report_content` 过滤器供给，默认返回 503。

### 生产实测

扫描全部订单的 `Context::stored()`：

```
orders with report contexts: 0
```

**没有任何订单持有可下载的报告 handoff。** 因此该下载路径在生产上从未被真实使用过，
本轮无法读回一个真实的客户 PDF。

### 一处差点误判（记录下来避免重犯）

我先查了 `_linker_planning_handoff`，发现 10 个询盘全无，一度准备据此写
「客户报告从未交付」。但那实际是 `DraftTransfer::LINE_META`——**购物车行**上的
方案草稿转移标记，与报告 handoff 是完全不同的东西。元数据键相似不等于语义相同。

正确的键是 `_linker_planning_projects`；用它查出的结论才是上面那个。

### 解除条件

需要一个持有报告 handoff 的询盘。产生方式：客户在配置器里生成报告后
把方案发成询盘，`Context` 才会写入 contexts。本轮已有的询盘都早于该能力，
或未走这条路径。

### 权限层已实测（2026-10-31）

下载路径的权限与拒绝行为已在生产验证，均为只读探测：

| 请求 | 结果 |
| --- | --- |
| 无 `key`、无登录会话 | `404 planning_report_not_found` |
| 持该订单有效 `order_key`、但无对应 handoff | `404 planning_report_not_found` |

两次返回**同一个** 404，不区分「你没权限」与「报告不存在」——报告的存在性因此不会
通过该端点泄露，这是正确行为。

### 仍未验证的部分

**一次成功的 PDF 下载。** 需要一份真实持有 handoff 的询盘；生产上 `Context::stored()`
对所有订单均为空。

生产上要产生 handoff，只能由 `DraftTransfer::apply()` 在真实会话中写入，
而它需要引擎签发的完整回执。**我不会伪造这个回执**——伪造出来的「验收通过」
不是客户路径，等于自欺。

解除条件：客户在配置器里生成报告后把方案发成询盘，`Context::capture()` 才会写入
contexts；届时可用该询盘读回一次真实 PDF。

## 3D 视图：生产实测渲染成功

地图 #548 的一条旧记录写作「Chrome 3D context availability remains unproven」。
现已在生产环境实际验证。

### 实测

项目 `88e747eb…`（`Production Roof Acceptance 1946`，revision 12，24 块组件）：

1. 打开 Roof design 工作区（`#lp-design`）；
2. 视图切换 `Plan / Map / 3D` 中点击 **3D**；
3. 视口渲染出**带透视的屋顶平面**（梯形几何），3D 按钮进入激活态；
4. 页面无报错，未出现降级提示。

代码侧对应实现：`apps/planner/src/components/design/SceneViewport.tsx`
（Three.js / React Three Fiber），并在 `webglcontextlost` 时监听恢复，
失败时渲染「3D rendering is unavailable. The design remains available in the plan
view and numeric properties.」——**降级路径也有文案出口**，不会白屏。

### 边界（不要过度解读）

这次验证的是**渲染可用**，不是：

- 3D 视图的交互完整性（旋转、缩放、选中已在 Plan 与 Map 下验证，3D 下未逐一操作）；
- 像素级视觉验收（工具页不受像素门约束，但也没有做 1440/390 × EN/DE 全矩阵）；
- 在不同 GPU / 浏览器下的兼容性——只在当前环境验证。

### 结论

「3D 不可用」这条旧记录**可以关闭**。地图上应改为：3D 渲染在生产可用，
失败时的降级提示存在；交互与跨环境兼容性未做全矩阵。

## 德语界面：生产实测完整

英文界面此前已多处读回；德文界面这次在浏览器里实际走了一遍。

打开 `/de/loesungskonfigurator/?project=88e747eb…`：

- 页面标题 **`Lösungskonfigurator | Linker`**
- 导航：`Aktuelles Projekt` · `Projektübersicht` · `Standort und Projekt` ·
  `Dachplanung` · `Energiedaten` · `Energieberechnung` · `Geräte` ·
  `Leitungswege der Installation`
- 屋顶工作区：`Dachplanung` · `Draufsicht` / `Karte` / `3D` ·
  `Dachfläche hinzufügen` · `Modulspezifikation hinzufügen` ·
  `Dachgeometrie importieren` · `Aktive Dachfläche` · `Nordbezug erfasst` ·
  `Planungsobjekte`
- 顶部动作：`Genie fragen` · `Gespeichert · Version 12` · `Projekt speichern`

界面文案完整德语，无残留英文标签。

### 一处看似漏译，实际不是

设计对象面板显示 `Owned synthetic roof for release acceptance`（英文）。
核对 `DesignEditor.tsx:528`：该名称直接渲染 `{face.name}`，**不经过 `__()`**。

这是正确设计——`face.name` 是用户在项目里给屋顶起的名字，属用户数据。
德语用户自己起的名字，界面不应替他翻译。

### 边界

验证的是**文案与布局**，未做 1440/390 全矩阵截图比对，
也未在两语种下逐一操作每个控件。
