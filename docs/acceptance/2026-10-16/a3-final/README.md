# A3 终局像素包验收记录（2026-10-16）

对应登记册 `docs/debt/REGISTRY-CLOSEOUT-2026-10-15.md` §2 的执行包。执行者：执行会话
（分支 `docs/a3-final-package`）；执行日 2026-10-16。证据工作区：`.scratch/a3-final/`
（`README.md`＝执行包说明与掩膜逐项；`metrics.json`＝67 面数字；PNG 留本地不入库）。

## 1. 口径与两侧状态

| 项 | 值 |
|---|---|
| 门槛口径 | **local vs live**（AGENTS.md §5：同机同浏览器同视口、禁动画、等字体、600px 步进、图片 decode、全页 PNG，掩膜外差异=0） |
| 修复印证口径 | **旧线上参考 vs 新树上线上**（deploy 前 2026-10-14 的 `shots-20261014-before` 对照 2026-10-16 重拍） |
| 本地侧 | t73 `http://127.0.0.1:8939`，插件软链→main `621a9005`；快照 20261015-1852；拍摄前 `just present t73` + `just windpress-compile t73` |
| 线上侧 | `https://de-linker.com`（2026-10-16 部署后；拍摄期间 11:00–11:15 前后一次维护窗，维护期帧全部作废重拍） |
| 拍面 | **67**（登记册 §2 清单 63 + A4 复核 4）；逐面数字 `.scratch/a3-final/metrics.json` |
| 阈值 | >2/255（max-channel），条带口径 -300..300 步进 1 最优位移 |

## 2. 结果

- **0px 面 22/67**：A3 21（商务链空态 8、EN 分类 1440 六个、shop/archive 筛选 1440 两面、
  arch 抽屉 390、`blogarchive-de` 两视口、`search-en-390`、`search-de-1440`）+ A4 复核
  `archive-en-390`。
- **掩膜面 38**（逐项见 §3；含四向重拍实证）。
- **缺陷候选 14 条 DT-1…DT-14**（§4；不写成通过）。
- **判据类复核**（`.scratch/live-recheck/dom-counts.json`）：
  `/de/category/system-design/` 200 且 `<html lang="de-DE">`、差异像素 0（#175/#189 修复已部署并
  验证）；短代码字面量全站 0；contact 表单 4/4 面 form=1；搜索面 7 张博客卡、无产品条目、无分页；
  筛选 1-24/38 与 1-21/21；抽屉开态 `filterOpen=true` 两侧同态。

## 3. 掩膜（逐项申报；未声明差异像素即 FAIL）

### M1 · demo 视频播放帧（8 面）

页内 demo `<video autoplay muted loop>` 的播放帧在两侧/两次拍摄之间天然不同（同一 mp4 字节，
两侧 md5 相同；播放进度不同）。矩形取两侧视频元素并集（+4px）：

| 面 | 视频矩形（x, y, w, h，CSS px） |
|---|---|
| epc-en-1440 | (146, 4586) 593×423 与 (146, 4617) 593×423 → 并集 (146,4546)-(739,5080) |
| epc-de-1440 | (146, 4758) / (146, 4792) 各 593×423 → (146,4718)-(739,5255) |
| epc-en-390 | (38, 6170) 314×235 |
| epc-de-390 | (38, 6391) 314×235 |
| installers-en-1440 | (174, 1734) 660×412 与 (656, 2375) 648×404 |
| installers-de-1440 | (174, 1762)/(174,1795) 660×412 与 (656, 2476)/(656,2519) 648×404 |

证据：掩膜前 epc-en-1440 差 112 968 px → 掩膜后 9 544 px（≤32/255、>32 为 0）；
installers-en-1440 211 140 → 15 745。**海报态探针**（拦截 `**/*.mp4` 重拍两侧）：EPC 两面
112 968/190 199 → 10 141/9 539；installers-en-1440 211 140 → 17 706——视频帧的贡献被这对
探针独立证实（`novideo-local/`、`novideo-live/`）。

### M2 · Gravatar 头像槽位（4 面：blogpost EN/DE × 1440/390）

`img.tv-blog-single-author-avatar`：1440 为 (109,1081)-(163,1133)，390 为 (33,1016)-(87,1068)
（DE 390 y1077-1129）。两侧 URL 相同（`secure.gravatar.com/avatar/a2cc…?s=96&d=mm&r=g`、字节相同）；
本地被隔离 CSP 拦截（`tools/local/mu/000-linker-local-isolation.php` 的 img-src 白名单，
`requestfailed: csp`，自然尺寸 0×0；该件从不部署），线上正常加载。掩膜后四面残差 = 0。

### M3 · live 侧运行间栅格抖动（26 面）

同协议同页两次重拍：live 侧差 0–4 169 px（含页高翻转的面 0.77–214 万 px），本地侧恒 0–70 px。
**四向实验**（本地×2、线上×2 交叉两两比）在以下面直接命中「某次 live 运行与本地逐像素 0 差」：
`cat-inv-en-390`（L1-V2=0）、`cat-inv-de-390`（L2-V1=0）、`shop-filt-en-390`（L2-V1=0）、
`a4-shop-en-390`（a-c=0）、`cat-backup-en-1440`（b-c=0）。逐面数字（cross ≤ 实测噪声地板）：
`noise-floor.txt`、`selfrep-final.txt`。全部 ≤22/255 且落圆角/字边/照片边缘。

## 4. 缺陷候选（DT-1…DT-14；不得写成通过）

判据：跨会话稳定、且超过该面噪声地板（两侧自发重复实测）的残差。全部为子像素/AA 级
（≤61/255，多数 ≤13/255）。

| # | 面 | 残差 px | 行带 / 幅值 | 性质 |
|---|---|---|---|---|
| DT-1 | installers-en-1440 | 15 745（>8 = 1 472；>32 = 3） | 散点；≥8 聚在 y609/718-742/4249-4325/4483-4619/6894-7232/7314-7419/8397-8513；≤35/255 | M1 掩膜后残差；live 自发重复 7 769 同带；3 px >32 在照片上 |
| DT-2 | installers-de-1440 | 14 729（>8 = 1 363；>32 = 3） | 同上；≤35/255 | 同上；live 页高 9 714↔9 767 翻转（+53） |
| DT-3 | epc-en-1440 | 9 544（>32 = 0） | 散点全页；≤32/255 | M1 掩膜后残差；live 页高 9 404↔9 467 翻转（+63） |
| DT-4 | epc-de-1440 | 9 539（>32 = 0） | 同 DT-3；≤32/255 | 同上（9 679↔9 747，+68） |
| DT-5 | epc-en-390 | 1 438（>8 = 56） | y37-551/2330-2391/3935-4133；≤32/255 | M1 掩膜后残差；两侧自发重复 0 → 稳定 |
| DT-6 | epc-de-390 | 1 438（>8 = 52） | 同 DT-5；≤32/255 | 同上 |
| DT-7 | contact-en-1440 | 495（≤45/255） | cp-hero-link 圆图 1px 弧线（y799-852，左侧 x55-63、右侧镜像 x844-852）+ y3323 x1055 单点 | 稳定（记录 495/复拍 509）；1px 圆弧 AA 相位差 |
| DT-8 | contact-de-1440 | 481（≤11/255） | 同 DT-7 图标形态 | 稳定 |
| DT-9 | contact-en-390 | 15（≤11/255） | 同源 | 稳定 |
| DT-10 | contact-de-390 | 2（≤5/255） | 同源 | 稳定 |
| DT-11 | bloglist-en-1440 | 355–471（≤61/255） | y1832-1836（featured 卡图角）、y2581-2605（卡图边缘） | 两侧自发重复 0 → 稳定；缩略图缩放 AA |
| DT-12 | bloglist-de-390 | 268（≤12/255） | y3984-4002 等 | 稳定 |
| DT-13 | sol-util-de-390 | 21（≤5/255） | 缩略图边缘 | 稳定 |
| DT-14 | sol-util-en-390 | 371–1 129（≤13/255） | 照片/文字边缘 | 记录差 1 129 高于 live 自发重复 758；复拍 371 |

**处置建议**：DT-1…DT-6 与 DT-11…DT-14 属 AA/缩放相位差量级，建议随掩膜一并进业主的允许差异
裁定（或业主决定单独立项回修）；DT-7…DT-10 为同一图标描边的 1px 相位差，量级更小。任何一条都
不构成本轮交付的阻塞项，但也**不得写成通过**——过门结论在业主裁定。

## 5. 旁证发现（不占 DT 号；供线上/后续跟进）

1. **live 页高竞态**：`/for-installer/`（live 9 714↔9 767；390 侧 10 368↔10 386、
   10 843↔10 934）与 `/for-epc/`（9 404↔9 467、9 679↔9 747）在 live 侧页高随运行翻转，本地侧
   恒定。原因指向页内 demo `<video>` 元素（元数据/海报加载时序改变布局高度）。对任何
   live|local 像素比对都会造成整页位移型假差异——建议线上侧跟进（预载元数据或钉死容器比例）。
2. **Gravatar 与本地隔离**：`secure.gravatar.com` 不在本地隔离 CSP 的 img-src 白名单内，
   博客单页作者头像本地为空、线上加载（两侧 URL/字节一致）。属本地隔离插件的既定行为
   （从不部署）；如需本地复刻线上渲染，可把该域加入白名单，但不属本轮交付范围。

## 6. 复跑命令

```sh
# 线上 97 面（GET-only）
node .scratch/live-recheck/shoot.mjs
# 本地补充面（协议逐字复制自 shoot.mjs）
node .scratch/a3-final/shoot-set.mjs local
# 数字 / 归因表
uv run --with pillow --with numpy python3 .scratch/a3-final/pair-metrics.py
python3 .scratch/a3-final/render-table.py
# 单面差异带 / OCR
uv run --with pillow --with numpy python3 .scratch/a3-final/diff-report.py <a.png> <b.png> --min 10
uv run --with pillow python3 .scratch/a3-final/band-ocr.py <a.png> <b.png> <y0> <y1> [x0 x1]
# 噪声地板（自发重复）
node .scratch/a3-final/selfrepeat.mjs <faces.json>
```
