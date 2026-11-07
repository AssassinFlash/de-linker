# 产品视图机械视觉验收：归并方法与代表页结果

本文件记录 `page-matrix.json` 中产品视图待验项的归并方法、代表页批次结果与剩余核对范围。机械探针（`tests/visual/layout-selfcheck.mjs`）只证明布局几何无缺陷；数据级核对（每个物理型号的事实呈现）与 Computer Use 视觉走查另行记录，不在此冒充完成。

## 归并方法

数据源：`page-matrix.json` 中的 pending 产品视图与其商品记录，经 `linker_commerce_facts_product_id` canonical 映射归并。

| 步骤 | 数量 | 依据 |
| --- | --- | --- |
| pending 产品视图 | 277 | page-matrix.json 初建状态 |
| EN/DE 商品记录 | 139 | 视图去重到 Woo 商品 |
| 物理型号 | 71 | canonical 映射（同型号不同语言/记录归一） |
| 型号族 | 28 | 同系列不同容量/档位 |
| 结构签名 | 36 | figures/installation/documents/attributes/categories 五要素组合 |
| 代表页记录 | 69 | 36 个签名各取 1 条 EN/DE 记录（部分签名只有单语记录） |

代表页批次每条按 1440×900 与 390×844 双视口执行，共 138 个 page/viewport。选择签名的理由：产品页模板唯一（LC `single_product.html`，EN/DE 同构），视觉差异只来自五个结构要素的有无与组合；同签名内页面共享同一渲染路径，代表页覆盖该路径的全部分支。德语商品记录本地工程 meta 常为空不是缺陷：页面由英源 canonical 渲染（GoodWe ESA EN/DE 页面实测均有完整技术数据与文档）。

## 探针修复（本批次前置）

本批次之前的产品批次全部无效：`--paths` 以 `name=完整URL` 传入时 origin 与 base 双拼导致整批 failed load。产品页在此之前从未被探针真实检查过。修复与语义（均有线上实测证据）：

- `--paths` 接受裸路径（含 query）、`name=path`、绝对 URL（剥 origin）；德语识别 `/de` 精确前缀。
- `auto/scroll` 祖先按轴判可达：滚动轴内容可达不报，另一轴被 hidden/clip 仍报。
- wider laid-out track 仅在存在真正裁切它的祖先时按 carousel review，否则保持 defect。
- 关闭 `<details>` 内容是隐藏态不报（实测：产品页 project-check 关闭 49px、点开 359px，行为正确；此前 14 个误报 defect 全部来自该盲区）。

## 代表页批次结果

- 日期：2026-11-07；环境：生产 de-linker.com，匿名浏览器，确定性布局探针（`tests/visual/layout-selfcheck.mjs`）；签收运行为 r4 批次（最终探针，分支 `3e1392e10`），站点 release 运行期未变（main `31a5b64c6` 部署态）。早前 r2/r3 批次被后续探针修正取代（r2 的 carousel 判据漏掉 2 页真实 defect、r3 的关闭 details 豁免误吞 102 条 summary review），不作为签收依据。
- 138 个 page/viewport（69 条 EN/DE 记录 × 1440×900/390×844），0 个失败加载。
- **defect 4 个**（`3000-2409-de`、`10-2403-de`、`666-2281-de`、`3557-de`，全部 1440），同一根因：德语桌面 feature band 大标题 `h3.pdp-section-title`（该处 clamp 至 52px）遇到不可断行复合词（"Notstromumschaltung" 557px、"Nulleinspeisungsregelung…" 634px > 528px 内容盒）溢出可见（无任何裁切者容纳溢出，画在 navy 面板上）。手机端 ≤860px 早有 `overflow-wrap: anywhere`，桌面缺失。修复：把该规则上移到 `pdp.css` 基础 `.pdp-section-title`（对不溢出的标题零渲染变化），删除手机端冗余副本。修复效果已在全部 4 页免部署注入验证：h3 正常换行、scrollWidth=clientWidth、探针 0 defect、无新增问题。生产部署后须复测这 4 页 defect=0 再关闭 finding。
- **review 303 条**，全部 small-target，三组，全部裁定接受（单行文本控件略低于 24px 触靶线，宽度充足 61px–1280px，无客户受阻证据；批量改生产 CSS 走像素门变更台账不成比例，如需 WCAG 打磨另行批量处理）：
  - `.pdp-crumbs > a`（桌面面包屑"Products"链接，61×21.7px，67 条）
  - `.pdp-price-login` / `.linker-create-account`（未登录价签链接，214×20px，134 条）
  - `.pdp-stats-context summary`（"About these specifications" 折叠标题，20.1px，102 条）
- 矩阵更新：134 条目 `visual_review` pending → partially-verified（新增 `layout_selfcheck_product_20261107` verified_check，evidence 指向本目录 JSON）；4 条 defect 页标 `partial-with-finding` + finding `pdp-de-feature-headline-overflow`。
- **finding 已关闭（生产实证）**：deploy `34cd20566`（cutover deploy + WindPress headless 重编译，缓存 1793958560 → 1794029105、body 变化、锚点齐全）后复测 4 页：0 defect、h3 干净、0 失败加载；回滚点 `/home/u388076051/deploy-prev/20261107T052008387414Z-34cd20566` 按策略保留。矩阵 4 条目已升级 partially-verified，post-deploy verified_check 与证据 `product-visual-selfcheck-postdeploy-20261107.json`。
- 证据：`product-visual-selfcheck-20261107.json`（r4 完整批次输出，含逐条 issue 几何）、`product-visual-selfcheck-postdeploy-20261107.json`（部署后复测）。

## 已接受 review 项

- `.pdp-stats-context summary`（产品页技术数据出处折叠标题）：高 20.1px，低于 24px 触靶线（WCAG 2.5.8）。裁定接受：控件为全宽行（390 视口下 350px 宽），实际易点，无客户受阻证据；为 4px 修改生产 CSS 需走产品页像素门变更台账，收益不成比例。如业主要求 WCAG 打磨，修复为 `pdp.css` 一行 `min-height: 24px`。

## 数据级核对（2026-11-07，生产实测）

对矩阵全部 214 条产品记录（107 个 slug）在生产做只读数据提取（页面渲染数据不变量）并与 WP-CLI 权威商品状态对账（`post list --post_type=product`，538 商品：176 publish / 362 draft）。证据：`product-data-check-20261107.json`。

- **170 条客户可见记录（85 EN/DE SKU 对）**：H1、SKU、库存状态词（85 "In stock" + 85 "Auf Lager"，0 wait 态——与业主"库存只说状态"裁定一致）、关键数据行 1–4、文档链接 ≥2、project-check 工具入口全部齐备；按 SKU 配对 85 对，specRows/docs/statCards/库存态/工具入口 **EN/DE 零不一致**。
- **44 条非客户页，矩阵改为 not-applicable（88 个视图条目，含原因字段）**：
  - 42 条 EcoFlow Ocean-2 "2026 flagship" 系列：生产 `post_status=draft`（WP-CLI 读回），草稿对访客 404 属 Woo 正常行为；
  - 2 条 Trina TSM-460NEG9R.28（EN 8349 带 `reference_pv_module` role，DE 8350 经 canonical 映射同 role）：`Publication` 有意把工程参考件排除出客户发布面（includes/Products/Publication.php 的 `! EngineeringReference::is_reference`）——404 是设计行为。
- 另核实 2 个矩阵外新发布商品（Nexans 电缆 8469/8470，publish）URL 亦 404：属分阶段发布机制（`published_in_current_read` 未放行），与设计一致；发布放行后需进入矩阵。

## 剩余核对范围

- ~~71 个物理型号的数据级核对~~ 已完成（见上节）：85 SKU 对零不一致，44 条非客户页改 not-applicable。
- **产品类条目全部收口（2026-11-07）**：69 条代表页直测 + 103 条兄弟记录按渲染结构键（specRows/statCards/docs/pairingRows/库存态）映射到已测代表页收口（形状共享，证据链 r4 + 数据级读数）；4 个结构独特页（gw208-9-bat-lcd、etr-125 各 EN/DE——前序会话已有首覆盖证据）补直测 0 defect（`product-visual-selfcheck-siblings-20261107.json`）。产品类 pending 归零；矩阵剩余 pending = term 70 + page 40（交互轴另计）。
- 71 个物理型号的 Computer Use 视觉走查（代表页机械探针通过 ≠ 人工视觉验收）仍待执行；产品页工具入口（project-check 按钮的 Genie 消费）不在数据级范围内，由 genie-entry-inventory 族覆盖。
