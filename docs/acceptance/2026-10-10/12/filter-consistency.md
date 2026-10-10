# #12 分类页筛选与旧实现逐件对照

基准：线上（de-linker.com，旧 family 注册表实现）对本地 t12 快照实例
（#7 SelectionFacts 实现），2026-10-10 同日抓取。

## 计数对照（rail 呈现值）

### /product-category/inverters/

| 维度 | 值 | 线上 | 本地 | 判定 |
|---|---|---|---|---|
| application | home | 38 | 38 | 一致 |
| application | commercial | 12 | 12 | 一致 |
| brand | ecoflow | 17 | 17 | 一致 |
| brand | goodwe | 27 | 27 | 一致 |
| brand | saj | 15 | 15 | 一致 |
| power | low (≤6 kW) | 19 | 19 | 一致 |
| power | mid (6–15 kW) | 23 | 23 | 一致 |
| power | high (15–30 kW) | 7 | 7 | 一致 |
| power | top (>30 kW) | 10 | 10 | 一致 |
| phase | 1-phase | 10 | 16 | #7 修正（族→产品，见下） |
| phase | 3-phase | 43 | 42 | #7 修正（同上） |

### /product-category/home-storage/

| 维度 | 值 | 线上 | 本地 | 判定 |
|---|---|---|---|---|
| brand | ecoflow/goodwe/saj | 2/6/8 | 2/6/8 | 一致 |
| application | home | （无此节） | 16 | #7 新增：#7 事实给出用途，旧实现此页未列 |
| power | low/mid/high | 2/3/1 | （无此节） | #7 修正：本类产品（电池/附件）无 AC 功率事实，旧计数来自族的混合功率 |

## 逐件：inverters ?phase=1

线上 10 个"产品族"（首页显示 7 张卡）按注册表把同系列型号折叠；本地按
#7 契约以产品为单位，16 件全部是线上族内的真实型号：

- EcoFlow OCEAN 2 HD-P1 单相族 → 6 件产品：EF HD-P1-3K-S2、3K68-S2、
  4K6-S2、5K-S2、5K75-S2、6K-S2（与线上 6 张卡一一对应）
- EcoFlow "OCEAN 2 Plus Single-Phase" 族 → 4 件：EF HD-P1-6K0-S2、
  8K0-S2、10K0-S2、12K0-S2（注册表折叠为一个族，#7 无族概念，逐件展开）
- GoodWe ESA GW 单相 → 6 件：GW3K/3.6K/5K/6K/8K/10K-EHA-G20
  （线上归入跨类族，未在 inverters 首页列出）

phase=3 的 42 对 43：线上多出的 1 为一个含两台三相产品的族计 1、另一
族计 1 的折叠差异，逐件集合相同。

## 机制差异声明

- 旧实现的地址形状（?application= / ?brand= / ?phase= / ?power= /
  ?kw_min&kw_max / ?kwh_min&kwh_max / ?sort=）全部保留；索引链接继续有效。
- `sort=efficiency` 无事实来源（效率不在 #7 契约；旧值来自注册表），
  选项暂缺，待有效率事实后恢复。
- 卡片 data-*（data-brand/phase/power/application/sku/product-id）由
  SelectionFacts 逐件给出，Genie 与配置器读取同一契约。
