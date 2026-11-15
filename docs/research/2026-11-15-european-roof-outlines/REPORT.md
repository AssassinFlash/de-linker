# 全欧屋顶轮廓：哪些国家真有官方 3D 数据

2026-11-15。#548 全欧范围扩张的调研结论。业主裁定：不允许任何功能再以「仅德国」为边界。

## 一、当前实现的事实

`services/engine/data/lod2-sources.json` 覆盖德国 16 个州，每个下载地址在 2026-07-18 用真实下载验证过。`roof/service.py` 的 `outline()` 原先对任何非德国国家直接拒绝；现已改为按区域查源，无源时明确报「该区域没有轮廓源」，由客户手绘兜底（`/roof/pack`）。手绘路径不检查国家，全欧可用。

`models.py` 的三处德国限定已按本裁定删除：坐标范围从德国（47.0–55.2 N / 5.8–15.1 E）扩到地理欧洲（27.0–71.5 N / −32.0–47.0 E，含加那利、亚速尔、北角）；`Plz` 从「5 位数字」改为「该国自己的样子」（`^\d{5}$` → 2–12 位字母数字加空格连字符）；`PlaceResult` 的 `country`/`region`/`timezone` 不再默认德国。`roof/service.py` 的 `_zone()` 从「柏林以西 32、以东 33」改为标准 UTM 六度分区（里斯本 29、雅典 34、柏林 33）。

## 二、外面的世界（每条都实际验证过）

| 数据源 | 覆盖 | 几何级别 | 许可 | 取得方式 | 判断 |
|---|---|---|---|---|---|
| **Overture Maps buildings** | 全球，含全部目标国 | 2D 轮廓 + `building_part`，部分含高度/层数 | **ODbL**（因以 OSM 为主融合源） | 月度 Parquet（S3 与 Azure 同路径，已实测可列目录） | **可用，非德首选**。商用允许，但有署名与衍生库同许可义务 |
| **Microsoft Building Footprints** | 225 个区域，含全部目标国；欧洲精度 94.3%、误检 1.4% | 2D 轮廓，部分含高度（缺失记 −1），带置信度 | **CDLA Permissive 2.0**（README 2026-08 版实测） | `dataset-links.csv`（30,341 个 quadkey 分片，实测存在）+ 批量下载 | **可用**，无同许可义务，含希腊 600 万、法国 380 万+580 万、比利时 180 万、荷兰 160 万 |
| **Geofabrik 分国 OSM** | 每国都有，含小国 | 建筑**多边形**；`height`/`building:levels`/`roof:shape` 标签存在但稀疏不均 | ODbL | 分国 `.osm.pbf`，自行托管 | **可用**，作补充与标签层，不能作几何权威 |
| **Google Open Buildings V3** | **无任何欧洲国家**（实测官方国家列表） | 2D | — | — | **不适用** |
| **EUBUCCO** | EU-27 + UK/NO/CH，3.22 亿栋 | 2D 轮廓，高度「覆盖 43.2%」但**仅 16.6% 为实测** | 继承 55 个上游源 | Parquet + Zenodo 快照 | **可作批量播种，不能作报价依据**——机器学习估的高度不可辩护 |
| **Copernicus / EEA / Eurostat** | 全欧 | **没有单栋轮廓**，只有 100 m 建成区栅格 | — | — | **不适用** |

## 三、哪些国家真有官方 3D 屋脊几何

**答案：极少。** 德国之外，全国性开放的 LoD2 级 CityGML 只有三处，加一个城市级：

| 国家 | 数据集 | 几何 | 许可 | 验证 |
|---|---|---|---|---|
| **NL** | **3D BAG**（TU Delft/3DGI） | 全国 3D 建筑，LoD1.2/1.3/2.2（**含屋顶面**） | **CC BY 4.0**（API 规范页实测） | 实测：`api.3dbag.nl/collections/pand/items` 返回真实建筑，含 `b3_dak_type=slanted`、`b3_h_nok=15.0`、`b3_h_dak_min=7.47`、`b3_bouwlagen=4`、`MultiSurface` 几何 |
| **CH** | swissBUILDINGS3D 3.0 Beta（swisstopo，2026-06-04 发布） | 3D 含屋顶几何与挑檐，两种模型变体 | 瑞士「免费地理数据」条款（署名；商用允许） | 产品页实测；条款页未能读取，属高置信而非全文核过 |
| **AT（仅维也纳）** | 通用化屋顶模型 LoD2.1（维也纳 OGD） | 屋顶形态 | CC BY 4.0（data.gv.at 惯例） | 搜索页验证，许可为推断 |
| **FR** | BD TOPO v3.5 有建筑高度，IGN LiDAR HD 可推导 LoD2，但**没有公开的全国 LoD2** | 2D + `hauteur` | Licence Ouverte 2.0 | 未完全验证（站点拒绝本机连接） |
| DE | 现有 16 州 | LoD2 面 | — | 已有 |

**其余约 25 国只有 2D 轮廓**（ES/IT/PT/PL/CZ/SK/HU/RO/BG/GR/HR/EE/LV/LT/IE/GB/SE/NO/FI/DK/BE/LU/SI）。这不是工具缺陷，是数据现实：这些国家的倾斜与朝向必须来自客户输入或手绘平面，与工作台今天的做法一致。

## 四、落地路径

1. **轮廓层**：Overture buildings 按月拉 Parquet 进自己的瓦片库；Microsoft 分国分片作第二来源与部分高度补充。两者都自托管，客户链路里不调第三方 API。
2. **屋脊几何**：德国 LoD2 保持；新增 **NL 3D BAG（CC BY 4.0）** 与 **CH swissBUILDINGS3D** 两个全国性适配器；维也纳作城市级附加。
3. **其余国家**：2D 轮廓 + 客户给坡度/朝向，或手绘平面。
4. **Overpass 公共端点不可用**（实测 502「所有查询进程繁忙，本端点面向浏览器与人工操作」），已从候选里排除；内部工具可自建 Overpass，客户链路不需要。

**许可结论**：上述推荐源没有禁止商用的。ODbL 有署名与衍生库同许可义务；CC BY 4.0 / CC0 / CDLA-Permissive 2.0 / Licence Ouverte 均商用友好。西班牙 Catastro 有复用条件，上线前需一次法律阅读。明确不可用的只有 Overpass 公共端点与 Google Open Buildings（无欧洲覆盖）。

**未完成**：FR IGN、ES Catastro、GB OS 的整页验证因这些主机拒绝本机连接而未做，属于各国适配器开工时的第一步。Microsoft 与 Overture 的实际抽样下载尚未执行——上表判断基于官方 README/目录结构与文件可用性，不是已导入的瓦片。
