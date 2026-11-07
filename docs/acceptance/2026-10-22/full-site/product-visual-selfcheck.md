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

- 日期：2026-11-07；环境：生产 de-linker.com，匿名浏览器，确定性布局探针（`tests/visual/layout-selfcheck.mjs`，分支 `visual/layout-selfcheck-paths`）；站点 release 运行期未变（main `31a5b64c6` 部署态）。
- 138 个 page/viewport（69 条 EN/DE 记录 × 1440×900/390×844），0 个失败加载。
- **defect 2 个**（`3000-2409-de@1440`、`10-2403-de@1440`），同一根因：德语桌面 feature band 大标题 `h3.pdp-section-title`（该处 clamp 至 52px）遇到不可断行复合词（"Notstromumschaltung für die Klasse ET 80 bis 100 kW" 557px > 528px 内容盒）溢出 6/29px。手机端 ≤860px 早有 `overflow-wrap: anywhere`，桌面缺失。修复：把该规则上移到 `pdp.css` 基础 `.pdp-section-title`（对不溢出的标题零渲染变化），删除手机端冗余副本。修复效果已在两页免部署注入验证：h3 正常换行（高 168/225px）、scrollWidth=clientWidth、探针 0 defect、无新增问题。生产部署后须复测这两页 defect=0 再关闭 finding。
- **review 305 条**，三组 small-target，全部裁定接受（同性质：单行文本控件略低于 24px 触靶线，宽度充足 61px–1280px，无客户受阻证据；批量改生产 CSS 走像素门变更台账不成比例，如需 WCAG 打磨另行批量处理）：
  - `.pdp-crumbs > a`（桌面面包屑"Products"链接，61×21.7px，67 条）
  - `.pdp-price-login`（未登录价签链接，214×20px，134 条）
  - `.pdp-stats-context summary`（"About these specifications" 折叠标题，20.1px，102 条）
- 矩阵更新：136 条目 `visual_review` pending → partially-verified（新增 `layout_selfcheck_product_20261107` verified_check，evidence 指向本目录 JSON）；2 条 defect 页标 `partial-with-finding` + finding `pdp-de-feature-headline-overflow`，待部署复测后升级。
- 证据：`product-visual-selfcheck-20261107.json`（完整批次输出，含逐条 issue 几何）。

## 已接受 review 项

- `.pdp-stats-context summary`（产品页技术数据出处折叠标题）：高 20.1px，低于 24px 触靶线（WCAG 2.5.8）。裁定接受：控件为全宽行（390 视口下 350px 宽），实际易点，无客户受阻证据；为 4px 修改生产 CSS 需走产品页像素门变更台账，收益不成比例。如业主要求 WCAG 打磨，修复为 `pdp.css` 一行 `min-height: 24px`。

## 剩余核对范围

- 71 个物理型号的数据级核对（facts 呈现、文档链接、库存状态词）未由本批次覆盖；代表页通过不外推到未检查的独有内容。
- review 项逐条判定记录见上；无 defect 才可把 36 个签名对应矩阵条目标为机械视觉通过。
