# 可实际进入的屋顶、光伏与系统设计软件

取证日期：2026-10-22。任务是给主线提供现在可以打开、下载或照着操作的官方入口与材料。主线独占浏览器实操；本子任务只用 Apify 取证，没有操作软件界面、注册账号、接受协议、下载或安装试用程序。

**可以直接打开 [PV*SOL online](https://pvsol-online.valentin-software.com/#/)：主线已无账号填入商业练习参数并求得设备/串配置。** 年模拟尚停在 reCAPTCHA 前，不能称全程仿真已跑通。[Sunny Design](https://www.sunnydesignweb.com/sdweb/#/) 当前官方手册也明确保留匿名权限，但尚无主线 UI 验证。静态 HTTP 200 和官方功能说明不能代替运行记录。

本轮实际取得的是：5 类软件的官方访问路径、30 个页面/文件的抓取记录、两份 K2 原生报告说明 PDF、三个关键 PDF 页的可读图、官方教程与导出操作步骤。**尚未取得可编辑的 `.pvprj` / K2 项目文件、桌面安装包、本人新生成的项目报告或已登录试用环境。** 原始抓取、文件 SHA256、账号与功能边界均留在本目录。

## 1. 能进入哪里，门槛是什么

| 工具 | 现在的精确入口 | 平台和访问门槛 | 官方明确的可练能力 / 限制 | 本子任务实际取得与未运行 |
| --- | --- | --- | --- | --- |
| **PV*SOL online** | [在线工具](https://pvsol-online.valentin-software.com/#/) | 浏览器；主线已实际匿名填表并求解配置 | 地点、负荷曲线及年电量、组件数量/姿态、逆变器品牌；自动搜串配置；官方说明仿真后有年发电量、PR、自用、solar fraction、月图，但主线实际年模拟被验证码挡住。公开说明不足以证明它承载完整屋顶几何或工商业储能工程。 | 官方入口 HTTP 200；主线取得 2×GW20KLV-MT / 92 片的配置，详情见下文。没有在本子任务点 Run。[官方原文](https://pvsol-online.valentin-software.com/) |
| **SMA Sunny Design** | [启动](https://www.sunnydesignweb.com/sdweb/#/)；[权限矩阵](https://manuals.sma.de/SDesign/en-US/14559946891.html) | 浏览器，官方支持 Safari 17.1+ 等；匿名、注册、PRO 权限不同 | 匿名可做含/不含自用的 PV 和 PV power plants；不能保存管理项目、创建自有组件/地点/负荷曲线、做 peak-shaving storage simulation。Energy systems、逐时导出与高级文档属于 PRO。 | 已保存产品页、当前手册权限表和应用 HTML；应用 HTML 包含未求值模板，不能算已运行。未登录、未启用 PRO。[系统要求](https://manuals.sma.de/SDesign/en-US/14314408459.html) |
| **PV*SOL / PV*SOL premium** | [官方试用下载页](https://valentin-software.com/en/downloads/)；[premium 下载链接](https://valentin-software.com/downloads/pvsol-premium/latest)；[PV*SOL 下载链接](https://valentin-software.com/downloads/pvsol/latest) | **Windows 10/11 64 位**；本机 macOS 不能按官方要求原生运行；下载按钮公开可见，安装/激活阶段未进入 | 当前下载页为 premium 2026 R8 / PV*SOL 2026 R6，30 天试用；premium 有 3D+2D 遮挡，普通版只有 2D。试用**不能打印或保存项目报告**。 | 已取得下载路径、系统要求与授权说明；未下载 exe、未安装、未接受许可。[premium 产品与系统要求](https://valentin-software.com/en/products/pvsol-premium/)、[试用限制](https://help.valentin-software.com/pvsol/en/licensing/) |
| **Easy PV** | [官网](https://easy-pv.co.uk/) → Login / Register Now；[Whole-system design 原生操作手册](https://help.easy-pv.co.uk/books/getting-started-f2k/page/whole-system-design) | 浏览器；官网要求注册后探索设计功能；Basic 免费、Pro 为另一档 | 官方手册可照做：画/导入屋顶 → Recommended systems → 选屋顶/假设 → Use system；免费账号使用站点维护的 kit，修改自己的设备和价格组合需要 Pro。 | 已保存带截图链接的官方完整流程和报告保存教程；未注册、未建项目。首页链接的 [Speedy PV](https://easy-pv.co.uk/speedy-pv) 在这次抓取缺项，不能当已验证公开 demo；它的 lead-generation 用途也不能证明完整编辑器匿名开放。[官网](https://easy-pv.co.uk/)、[文档管理](https://help.easy-pv.co.uk/books/reports-documents-and-emails/page/pro-document-management) |
| **K2 Base** | [官方 Test now](https://base.k2-systems.com/#/dashboard)；[MyK2](https://my.k2-systems.com/) | 官方写 PC/Mac 浏览器免安装、免费；MyK2 注册可访问 K2 服务，实际账号墙由主线 UI 判断 | 屋顶/多组件区、风雪荷载、紧固件/压载、安装图与 BOM、PDF 报告；限定 K2 安装系统。官网明确能把数据转给 Sunny Design、PV*SOL premium、archelios Pro 等。 | 应用入口只抓到 7 字符 JS shell，**没有运行**；已实际保存两份公开 PDF 和三个关键页面。未创建 MyK2 账号。[工具说明](https://k2-systems.com/en/digital-services/k2-base/)、[MyK2 注册说明](https://k2-systems.com/en/digital-services/myk2-registration/) |
| **OpenSolar** | [登录](https://app.opensolar.com/#/login) / [Create Pro Account](https://app.opensolar.com/#/register) | 浏览器；官方免费 Pro 账号入口，未进入账号创建流程 | 官方 Swipe proposal 手册有 Demo，但它位于组织账号的 Control → Proposals & Contracts 内，需已完成项目和 payment options 才能真实预览。**不是公开免注册项目 demo。** | 保存官网入口和原生 proposal 操作说明；未注册、未建项目、未发送 proposal。[官方产品页](https://www.opensolar.com/pro/)、[Demo 所在实际步骤](https://support.opensolar.com/hc/en-us/articles/13440054388239-Editing-in-the-Sales-Machine-Proposal-SMP) |

PV*SOL online 与桌面 PV*SOL 属同一家软件的两种获取方式，因此上表覆盖 5 家最贴近本任务的工具，而不是把所有在线计算器都列进来。

SMA 的“Starting Sunny Design”手册描述的是 **SMA ID 登录路径**，首次登录要求同意使用条款和数据保护声明；它与权限矩阵里的匿名档同时存在。因此下一步应从真实界面找到匿名入口，不能用登录说明推断匿名已被取消，也不能从权限矩阵推断所有功能匿名开放。[登录步骤](https://manuals.sma.de/SDesign/en-US/14317168267.html)、[权限矩阵](https://manuals.sma.de/SDesign/en-US/14559946891.html)

### 主线已经做出的 PV*SOL online 操作

以下来自同日主线的实际浏览器记录，本子任务核对了原始 UI 文本；未复制主线拥有的证据到本分支。

- 输入：BDEW G1 商业负荷，80,000 kWh/year；92×Trina TSM-460 NEG9R.28 Vertex S+；10° / 180°；Mounted-roof；逆变器品牌 GoodWe。
- 实际点击 **Get best configuration**：得到 **2×GW20KLV-MT**，每台 `MPP 1: 2×8 - MPP 2: 2×8 - MPP 3: 2×7`，即每台 46 片、全案 92 片；界面显示 dimensioning factor **105.8%**。
- 后续 **Simulate PV system** 前出现 reCAPTCHA；未完成验证码、未运行年模拟、未取得该项目的年发电结果或报告。

这证明匿名访问和实际设备/串配置求解可用；不据此声称解的设备可采购、工程上已复核，或发电量/储能联合仿真已验证。原始证据为主线工作树中的 [UI 文本](/Users/chesterjohn/Documents/de-linker-worktrees/research-trace-software-access/docs/research/2026-10-22-trace-software-access/coordinator/raw/pvsol-configured.txt) 与 [配置截图](/Users/chesterjohn/Documents/de-linker-worktrees/research-trace-software-access/docs/research/2026-10-22-trace-software-access/coordinator/screens/pvsol-real-configuration.jpg)；本研究包的 30 项官方抓取计数不包含这两项主线证据。

## 2. 已经拿到的原生材料

### K2：可以直接打开和逐页研究的报告样例材料

| 本地文件 | 来源与校验 | 已核查的内容 | 可支持的学习范围 |
| --- | --- | --- | --- |
| [平屋顶荷载分布，12 页](captured-files/file-014c42e-Load-distribution-flat-roof-en.pdf) | [官方 PDF](https://catalogue.k2-systems.com/media/15/24/91/Load-distribution-flat-roof-en.pdf)；2,261,751 bytes；SHA256 `ca4bab5a0c0754e6e6b972095079d52cf6688305c0c96d537c52f9673106a049` | 已看完整第 3 页：屋顶构造剖面、K2 Base project report 的压力/荷载组合页面片段、保温材料允许持续压应力的对照要求、Additional Mat S 的结果选项。 | 能复做“项目输入/支承面/报告值/材料允许值”的解释链；它是官方说明内嵌的报告片段，**不是完整可编辑项目或全套静力证明**。 |
| [Base Report 德文注释，10 页](captured-files/file-6033e6f-Base-Report-annotations-de.pdf) | [官方 PDF](https://catalogue.k2-systems.com/media/11/5f/79/Base-Report-annotations-de.pdf)；907,061 bytes；SHA256 `a030b7c520aa46ef33638f612acbb87c8ae85aa009064b41039028d164d34034` | 已看完整第 1、5 页：标准/风载输入的编号解释，以及保温层压力、保护垫有效面积和汇集面积的报告字段。 | 可学习结果字段旁的编号解释方式。PDF 创建日期为 2023-07-21；其样例数字、所列标准与默认值**不作为我们全欧洲新算法的规则**。 |

三张核查图在 [evidence/](evidence/)；原始字节、Poppler 元数据和哈希在 [captured-files.json](captured-files.json)。PDF 仅渲染和读出文本，没有改写。荷载分布说明的 PDF 元数据创建日期为 2026-06-02，正文包含较早版本报告片段，因此也不把它冒称当前软件所有报告格式的完整快照。

K2 官网当前明确列出与 **archelios Pro、PV*SOL premium、Sunny Design** 等的转接。这是学习“安装系统设计 → 发电/电气系统设计”接力方式的现成入口；本轮没有实际执行这些软件间的导入导出。[官方工具页](https://k2-systems.com/en/digital-services/k2-base/)

### 可照着做的官方流程已经保存，项目文件未获得

| 工具 | 官方原生流程 | 保存位置 / 具体边界 |
| --- | --- | --- |
| SMA | [模板建项目](https://manuals.sma.de/SDesign/en-US/14329256331.html)：个人主页 Templates → 选模板 → New project with this template → 项目名 → Accept changes | `raw/access-instructions-items.json` 对应 URL。这里的模板是个人账号区域中的模板，未取得公开模板项目文件。 |
| SMA | [项目 PDF](https://manuals.sma.de/SDesign/en-US/14462685579.html)：Create project documentation → 选择内容 → Refresh preview → 选设计备选/纸张 → Download project documentation | 同上。官方说明可作为实际操作路线，不能证明匿名账号此次已经导出成功。 |
| PV*SOL premium | [屋面平行安装完整视频教程文章](https://valentin-software.com/en/product-news-blog-en/master-solar-design-with-this-pvsol-premium-video-tutorial/)：新项目 → 气候数据 → 3D 模型 → 仿真 → 报告 | `raw/access-instructions-items.json`。完整运行需要 Windows 试用/许可环境，本次未运行。 |
| PV*SOL premium | [2026-10-13 原生报告教程](https://valentin-software.com/en/product-news-blog-en/creating-a-customer-presentation-in-pvsol-premium/)：Results 运行 → Presentation → Customer presentation - Compact → 语言 → PDF 或 DOCX | 同上。已保存原生界面图的官方链接；试用不允许报告保存，不能据此承诺试用版可执行全部步骤。 |
| PV*SOL | [Presentation 帮助](https://help.valentin-software.com/pvsol/en/pages/presentation/)和 [Plans and Parts list](https://help.valentin-software.com/pvsol/en/pages/plans-and-parts-list/) | `raw/access-projects-items.json`。分别可学习报告模板/预览/导出与原理图/尺寸图/串图的分工；未导出本人文件。 |
| PV*SOL | [官方 tutorials](https://help.valentin-software.com/pvsol/en/tutorials/) 公开嵌入的 7 个原生教学视频 | 原生 iframe 链接已保存至 [native-resource-index.json](native-resource-index.json)。索引虽写 sample projects，但本次没找到下载的 `.pvprj`；没有把视频当可编辑项目。 |
| Easy PV | [Whole-system design](https://help.easy-pv.co.uk/books/getting-started-f2k/page/whole-system-design)：完成屋顶后推荐系统 → 选屋顶/排序/假设 → Use system → 普通项目继续改设备/串配置 | `raw/access-instructions-items.json`，带官方截图/GIF URL。没有进入账号或应用生成任何系统。 |
| Easy PV | [Document management](https://help.easy-pv.co.uk/books/reports-documents-and-emails/page/pro-document-management)：报告预览右侧 Save → 项目文档管理 | `raw/access-projects-items.json`。页面明确属于 Pro，不作免费匿名导出承诺。 |
| OpenSolar | [Swipe proposal](https://support.opensolar.com/hc/en-us/articles/13440054388239-Editing-in-the-Sales-Machine-Proposal-SMP)：Control → Proposals & Contracts → Sales Machine Proposal Templates → Swipe → Demo | `raw/access-projects-items.json`。Demo 是账号内部按钮；未取得公开 sample proposal URL，未点击 checkout/accept/send。 |

没有下载教学视频，也没有通过第三方搬运站取得程序或工程文件。公开教程的页面正文和原生资源链接已落盘，仍需实际环境运行的部分在上表逐项标出。

## 3. 交给主线的实际试用顺序

1. **PV*SOL online：匿名配置求解已经完成，年模拟停在验证码前。** 主线已保存练习参数、自动选出的设备与串配置。后续若在可用环境完成年模拟，仍需另存月年结果；当前不能用官方示例值或其他软件的发电量补上这个缺口。[在线工具官方输入/输出说明](https://pvsol-online.valentin-software.com/)
2. **Sunny Design：确认匿名路径和其真实边界。** 先进入含 self-consumption 的 PV 类型，记录建项目、配置、运行与结果是否可达；尝试查看文档页面。保存或自定义负荷出现权限墙时，记录原文。不要用匿名 PV 项目代替尚未获得的 commercial peak-shaving / energy-system 试验。[匿名矩阵](https://manuals.sma.de/SDesign/en-US/14559946891.html)
3. **商用平屋顶先直接读已取得 K2 样例。** 将第 3 页的输入、支承面、荷载组合、材料允许值与解释标注整理成观测表。完整 K2 Base 实操需要先确认实际 MyK2 门槛；本轮无账号授权，因此不创建账号。输入值与整屋结构适用性还需真实项目条件和厂家要求。[K2 原生样例](https://catalogue.k2-systems.com/media/15/24/91/Load-distribution-flat-roof-en.pdf)
4. **需要更深联合仿真时，先明确环境。** PV*SOL premium 是 Windows 试用路线，报告导出受限；Sunny Design PRO 是登录后个人主页 Test it now 的 30 天试用，期满 energy-system 项目暂不可访问但不会删除。两种环境都未在本子任务启用。[PV*SOL 试用](https://valentin-software.com/en/downloads/)、[SMA PRO 试用](https://manuals.sma.de/SDesign/en-US/14326011403.html)

上述顺序以“实际填表/建模/运行/结果”为证据目标。Easy PV / K2 / OpenSolar 的账号门槛、Windows 环境、试用许可与协议接受属于尚未跨过的具体获取条件；这里没有把未来注册后的承诺写成当前已取得的能力。

## 4. 取证索引和复现

- [source-index.md](source-index.md)：逐页 URL、HTTP、文本长度、Apify dataset，含缺项。
- [sources.json](sources.json)、[collection-status.json](collection-status.json)：机器可读来源与抓取状态。
- [native-resource-index.json](native-resource-index.json)：官方页面实际嵌入/链接的资源；链接出现不代表二进制已取得。
- [captured-files.json](captured-files.json)：两份实际取得 PDF 的字节数、SHA256、Apify record URL、PDF 元数据。
- [raw-sha256.json](raw-sha256.json)：当前保存的原始 JSON 证据文件哈希。
- `raw/*-seed.json` / `*-input.json` / `*-run.json` / `*-items.json` / `*-evidence.json`：Apify 查询/抓取请求、运行 ID、原文与 HTML 链接提取。原 HTML 只保留哈希和链接/标题；完整响应留在该 dataset，Cookie 与签名查询不进入仓库。

示例复现命令，需已有环境凭据；不会注册任何软件账号：

```sh
python3 docs/research/2026-10-22-trace-software-access/alternatives/collect_access.py crawl docs/research/2026-10-22-trace-software-access/alternatives/raw/access-official-seed.json access-official
python3 docs/research/2026-10-22-trace-software-access/alternatives/read_captured_files.py
python3 docs/research/2026-10-22-trace-software-access/alternatives/index_sources.py
```

这些窄脚本复用本分支上一轮的 Apify 读取器与证据索引器；只写本目录。Actor memory 固定 2048 MB，源站并发 1–2；未变更账号预算、代理、模型或全局设置。最后一次搜索期间本机代理短暂 503；复用了已创建 run `9ofto4WE1MOeSd90t` 的结果，没有重开重复任务或绕过 Apify。

`access-native-docs` 的 Actor 汇总是 “3 succeeded, 2 failed”，但两项 PDF 各自有 HTTP 200、正确 `application/pdf`、完整字节和实际可读 PDF；本报告依据逐文件核查。Easy PV Speedy URL 没有返回保存项，已按缺项记录。K2 应用 shell、Sunny Design 未求值模板和公开页面均不算实操通过。
