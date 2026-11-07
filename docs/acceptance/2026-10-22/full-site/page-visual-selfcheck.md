# 静态页机械视觉验收（page 批次）

20 个 page URL（blog、thank-you、for-installer、for-epc、faq-download、refund、imprint、terms、genie、compare-products + DE 对）× 1440/390，生产只读。证据：`page-visual-selfcheck-20261107.json`（最终探针复跑）。

## 首跑与探针修复

首跑 133 defect，其中 104 个为探针盲区：`a.lg-skip` 跳转链接（clip 到 focus 后 141×44 显形）与法律页 `button.lg-copy` 复制按钮（`h2:focus-within` 下 opacity→1）都是合法渐进显形。根因修复：规则 5 对不可见候选就地 focus 一瞬读 computed style（SETTLE 已禁 transition，伪类同步生效），focus 显形即豁免；fixture 增加 focus-reveal near-miss。selftest 通过。

## 复跑结果与裁定

复跑（最终探针）40 检查、0 失败加载、29 defect，全部裁定为**已过像素门的设计模式**（这些复刻页与原设计逐像素一致，几何即业主已批准的视觉）：

- 评价滑块 active 卡 `scale(1.02)` 强调（for-epc/fuer-epc 双语双视口，卡缘 3-10px 入裁切口为强调效果本身）
- `#desk` 分层 hero：visual/heading/dock 以 relative 层叠构图（overlapRatio 1 为整幅分层，非意外堆叠）
- 工具页 `lk-tool-route` 全出血 tab 条（390 下 390px 宽于 354px 容器，与原设计一致）
- FAQ 库 chips 横滚轨与 ~20px 内衬溢出、hero 4px 溢出（同上）

review 52 条（small-target）沿用既有裁定口径。

## 矩阵状态

40 条 page 视图条目 → partially-verified（`page_layout_selfcheck_20261107`，带裁定说明）。**三矩阵 visual_review pending 归零**：619 partially-verified / 88 not-applicable（有据）/ 1 partial-with-finding（services 项，他线负责）。交互轴（interaction pending）不在本机械批次范围，由各状态族与 customer-chain 验收覆盖。
