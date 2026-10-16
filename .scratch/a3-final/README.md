# A3 终局像素包（2026-10-16）

登记册 `docs/debt/REGISTRY-CLOSEOUT-2026-10-15.md` §2「A3/A4/A6 部署后终局包清单」的执行包。
执行者：执行会话（执行分支 `docs/a3-final-package`）；执行日：2026-10-16。
回填：`docs/debt/REGISTRY-CLOSEOUT-2026-10-15.md` §2 与 §1 的 A3 行（回填日期与执行者见回填注）。

## 1. 两侧状态与协议

| 项 | 值 |
|---|---|
| 门槛口径 | **local vs live**（像素门本身：AGENTS.md §5，同机同浏览器同视口，掩膜外差异=0） |
| 修复印证口径 | **旧线上参考 vs 新树上线上**（deploy 前 2026-10-14 的 `shots-20261014-before` 对照新树 2026-10-16 重拍） |
| 本地侧 | t73 `http://127.0.0.1:8939`，插件软链→主仓库 main `621a9005`；快照 20261015-1852；拍摄前 `just present t73` + `just windpress-compile t73` |
| 线上侧 | `https://de-linker.com`（2026-10-16 部署后状态；拍摄期间 11:00–11:15 遇一次维护窗，维护期帧全部作废重拍，最终 97 面 0 张维护页） |
| 协议 | `.scratch/live-recheck/shoot.mjs` 同一套：禁动画、等字体、600px 步进懒加载、图片 decode（15s 预算）、全页 PNG、同机同浏览器同视口、阈值 >2/255 |
| 条带口径 | analyse-pairs.py 口径（-300..300 步进 1 全页垂直位移取最优；本包用 coarse-to-fine 收敛到同一最小值） |
| 采集 | 线上 97 面：`shoot.mjs`（`.scratch/live-recheck/shots/`）；A3 补充面与 A4 四 390 面：`.scratch/a3-final/shoot-set.mjs local|live`（协议逐字复制） |
| 面数 | **67 面**（A3 63 + A4 复核 4），逐面数字在 `metrics.json` |

## 2. 总结（回填给登记册 §2 的结论口径）

- **0px 面：22 / 67**（A3 21 面 + A4 复核 1 面）。含全部商务链空态 8 面（cart/checkout ×
  EN/DE × 1440/390）、六个 EN 分类 1440 面、shop/archive 筛选 1440 两面与 arch 抽屉 390、
  `blogarchive-de` 两视口（**#175/#189 德语归档修复已部署并验证：200 + lang=de-DE**）、
  `search-en-390`、`search-de-1440`、A4 `archive-en-390`。
- **掩膜面：38**，逐项申报（§3）；掩膜只覆盖两类真实动态区（demo 视频播放帧、Gravatar 外链
  槽位）与一类经实测的渲染抖动区（live 侧运行间栅格不稳定，四向实验证明同面某次 live 运行与
  本地逐像素 0 差）。
- **缺陷候选：14 条（DT-1…DT-14）**，全部为跨会话稳定、超过该面噪声地板的子像素/AA 级残差
  （≤61/255，多数 ≤13/255），逐条记 `defects.md`。**这些面不写成通过**——过门结论须业主对
  掩膜与允许差异的裁定。
- **修复印证（旧线上 vs 新树线上）**：67 面逐面数字在 `metrics.json` 的
  `repair_oldlive_vs_newlive`；短代码字面量全站归零、contact 表单 4/4 渲染（form=1）、搜索面
  全博客卡无产品无分页、九类 DE 归档 lang=de-DE、筛选计数 1-24/38 与 1-21/21 —— 即修复面
  「旧线上有、新树线上无」的差异全部兑现（对照见 `attribution-table.md` 修复印证表）。

## 3. 掩膜（逐项申报，未声明即 FAIL）

### M1 · demo 视频播放帧（8 面）

页内 demo `<video autoplay muted loop>` 的播放帧在两侧/两次拍摄之间天然不同（同一 mp4 字节，
两侧 md5 相同；播放进度不同）。矩形取两侧视频元素的并集（+4px）：

| 面 | 视频矩形（x, y, w, h，CSS px；两侧并集） |
|---|---|
| epc-en-1440 / epc-de-1440 | (146, 4546) 593×423 与 (146, 4586)/(146, 4792) 各 593×423 → 取 (146,4546)-(739,5080) 与 (146,4718)-(739,5255) 并集外包 |
| epc-en-390 | (38, 6170) 314×235 |
| epc-de-390 | (38, 6391) 314×235 |
| installers-en-1440 | (174, 1734) 660×412 与 (656, 2375) 648×404 |
| installers-de-1440 | (174, 1795) 660×412 与 (656, 2519) 648×404 |

证据：掩膜前 epc-en-1440 差 112 968 px、掩膜后 9 544 px（≤32/255、>32 为 0）；installers-en-1440
掩膜前 211 140 → 掩膜后 15 745。另做**海报态探针**（拦截 `**/*.mp4` 后重拍两面）：EPC 两面差
从 11.3 万/19 万 px 崩到 1.0 万/0.95 万 px，installers-en-1440 从 21.1 万崩到 1.8 万——视频帧
对差异的贡献被这一对探针独立证实（`novideo-local/`、`novideo-live/`）。

### M2 · Gravatar 头像槽位（4 面：blogpost EN/DE × 1440/390）

`img.tv-blog-single-author-avatar` 44×44（1440；390 同尺寸），两侧都指
`https://secure.gravatar.com/avatar/a2cc…?s=96&d=mm&r=g`。本地侧被
`tools/local/mu/000-linker-local-isolation.php` 的隔离 CSP（img-src 白名单）拦截
（`requestfailed: csp`，自然尺寸 0×0），线上加载 96×96 JPEG。掩膜该槽位后四面残差 = 0。
矩形（并集）：1440 = (109,1081)-(163,1133)；390 = (33,1016)-(87,1068)（DE 390 为 y1077-1129）。

### M3 · live 侧运行间栅格抖动（26 面，逐项）

同协议同页两次重拍：live 侧差 0–4 169 px（含页高翻转的面 0.77–214 万 px），本地侧恒 0–70 px。
四向实验（本地×2、线上×2 交叉）在以下面直接命中「某次 live 运行与本地 0 差」：
`cat-inv-en-390`（L1-V2=0）、`cat-inv-de-390`（L2-V1=0）、`shop-filt-en-390`（L2-V1=0）、
`a4-shop-en-390`（a-c=0）、`cat-backup-en-1440`（b-c=0）——即这些像素差**在 live 侧自己
的重拍里就不稳定**，是渲染抖动不是内容差。逐面数字（cross ≤ 实测噪声地板）见
`noise-floor.txt` 与 `attribution-table.md`；全部 ≤22/255 且落圆角/字边/照片边缘。

## 4. 逐面归因表

见 `attribution-table.md`（登记册 §2 第 3 条表头逐列：面 | 全页差异 px | % | 最优位移 |
条带差异 px | % | 页高 local/live | 归因 | 台账行），含修复印证表（旧线上 vs 新树线上）。

归因三类落法：**已裁定变更**——本次门槛口径下两侧同为 0 的面其旧-新差异即修复兑现（属已裁定
的修复面，出处：2026-10-15 部署 README §5 + 清账决策 16-18）；**掩膜**——M1/M2/M3（§3）；
**缺陷候选**——DT-1…DT-14（`defects.md`），不得写成通过。

## 5. 产物

| 文件 | 内容 |
|---|---|
| `metrics.json` | 67 面 × 两口径（门槛 local\|live、修复印证 old-live\|new-live）+ 非零面行带（`bands`） |
| `attribution-table.md` | §2 表头逐列归因表 + 修复印证表 |
| `defects.md` | DT-1…DT-14 台账（含上线侧旁证发现 2 条） |
| `attribution.json` / `render-table.py` | 归因映射与渲染脚本（可重跑） |
| `shoot-set.mjs` | 补充面采集驱动（协议复制自 shoot.mjs；`--dump` 可导出面表） |
| `shoot-frozen.mjs` / `shoot-novideo.mjs` / `selfcheck.mjs` / `selfrepeat.mjs` | 冻结视频 / 海报态 / 双向重拍 / 自发重复探针 |
| `band-ocr.py` / `diff-report.py` / `band-ocr` 工具 | 行带定位与 OCR 复核 |
| `local/`、`live/`、`selfrep/`、`frozen-*/`、`novideo-*/`、`crops/` | 全页 PNG 证据（**不入库**，留本地；`ls` 可复核） |
| `noise-floor.txt`、`selfrep-final.txt`、`gt32-sweep.txt`、`blocked-scan.json`、`probe-local.json`、`probe-live.json` | 数字原始件（本次一并提交的小体量文本/JSON） |

## 6. 复跑命令

```sh
# 线上 97 面（GET-only）
node .scratch/live-recheck/shoot.mjs
# 本地补充面
node .scratch/a3-final/shoot-set.mjs local
# 数字
uv run --with pillow --with numpy python3 .scratch/a3-final/pair-metrics.py
# 归因表
python3 .scratch/a3-final/render-table.py
# 单面差异带 / OCR
uv run --with pillow --with numpy python3 .scratch/a3-final/diff-report.py <a.png> <b.png> --min 10
uv run --with pillow python3 .scratch/a3-final/band-ocr.py <a.png> <b.png> <y0> <y1> [x0 x1]
# 噪声地板（自发重复）
node .scratch/a3-final/selfrepeat.mjs <faces.json>
```
