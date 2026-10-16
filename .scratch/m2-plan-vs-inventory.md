# M2 计划对账：`12-site-chrome.py` plan vs 线上残留清单

日期：2026-10-16 · 分支 `fix/m2-chrome-pairs` · worktree `de-linker-worktrees/de-linker-m2`
命令（只读）：

```
python3 tools/migrate/12-site-chrome.py --wp "ssh hostinger-de-linker /usr/local/bin/wp --path=$HOME/domains/de-linker.com/public_html" plan
```

- 完整输出：`.scratch/plan-live.txt`（线上实测）；改前的同一命令输出：`.scratch/plan-before.txt`。
- 清单 = 调查日志 `agent-3y080pkz/output.log` §2 的 A/B/C/E 表（2026-10-16 早间实测）。
- 离线预演（同代码、同一份线上 dump）与线上 plan 的逐行比对见文末 §6。

口径：plan 的行 = `步骤 #post: 字段` + 每行替换（`Nx old -> new`；strict pair 不带计数，语义=恰好一次）。

## 1. §2.A EN href 缺口

| 清单 | 清单预测 | plan 实测 | 对账 |
|---|---|---|---|
| 13 `/` | `href="/linker-advisor/"` ×4 | `home-en #13: 4x 'href="/linker-advisor/"' -> 'href="/genie/"'` | ✓ |
| 623 `/thank-you/` | `href="/linker-planner/"` ×4 | `thank-you-en #623: 4x … -> 'href="/solution-configurator/"'` | ✓ |
| 746 `/solution/` | ×2 | `solution-en #746: 2x …` | ✓ |
| 749 residential | advisor ×5 | `residential-storage-en #749: 5x 'href="/linker-advisor/"' -> 'href="/genie/"'` | ✓ |
| 749 residential | planner ×5 | `…: 5x 'href="/linker-planner/"' -> 'href="/solution-configurator/"'` | ✓ |
| 792 commercial | advisor ×5 | `5x` | ✓ |
| 792 commercial | planner ×8 | `8x` | ✓ |
| 826 for-installer | advisor ×2 | `2x` | ✓ |
| 826 for-installer | planner ×3 | `3x` | ✓ |
| 2748 services-support | ×1 | `1x` | ✓ |
| 558 gateway post | ×1 | `gateway-post-en #558: 1x` | ✓ |
| 574 LC 模板 blog index | planner ×2 | **plan 无此行** | **偏差 D1**（见 §5）：线上 574/6881 内容已干净（#189 改好仓库文件 + `present` 于 10-16 01:59 重建） |

另：清单未列但同型的两处 page 链接由新增链接规则覆盖——623/6873 此前根本不在脚本的
`SURFACES` 里（无工具名、只有 href），本轮把 `thank-you` 加进了 `SURFACES`。

## 2. §2.B DE 各页

| 清单 | 清单预测 | plan 实测 | 对账 |
|---|---|---|---|
| 6633 title+noscript | 1+1 组 | `linker-berater-de #6633: content, title`，2 个既定对（noscript 两段） | ✓（为 10-14 旧对，plan 再次命中=已被 10-15 导回） |
| 6693 title | 1 | `linker-planer-de #6693: content, title`；`seo title: meta absent` | ✓ + **偏差 D4**（seo meta 已被导入抹掉） |
| 6693 href | ×1 | `1x 'href="/linker-planner/"' -> 'href="/de/loesungskonfigurator/"'` | ✓ |
| 6693 注释 | 清单标"可延后" | `2x '/de/linker-planer/'`、`1x '/linker-planner/'` | ✓（本轮做了，不延后） |
| 6700 | Planer ×8、Berater ×3、Standortdetails ×3、href ×1 | 3 既定对 + `1x 'Linker Berater'` + `6x 'Linker Planer'` + `1x 'href="/linker-planner/"'` | ✓（8=2 对+6；3=2 对+1；3=3 对） |
| 6869 | 既定对全套（6+6+2+2 等）+ 21 机械 + href 5 | 15 既定对（含 `<a href="/de/">` 新对）+ `1x des Linker Beraters`、`1x im Linker Berater`、`3x Linker Berater`、`11x Linker Planer` + advisor 2x + planner 3x | ✓（Berater 7 = 2 既定对[h3、·Technische Ressourcen]+1+1+3；Planer 14 = 3 既定对+11；Standortdetails 6 = 6 既定对，0 catch-all；href 2+3） |
| 6871 | 既定对 4 + Planer ×5 + href 2 | 5 个 pair 行（含 `Linker Planer:</strong>`）+ `4x 'Linker Planer'` + `2x href` | ✓（5 = 4 既定对 + 1 既有 pair 行；5 = 1 pair + 4 catch-all） |
| 6921 | Berater ×3、Planer ×14、href 5+8 | `1x der/2x Linker Berater`、`14x Linker Planer`、advisor 5x、planner 8x | ✓ |
| 6923 | Berater ×4、Planer ×12、href 5+5 | `2x Der/2x Linker Berater`、`12x Linker Planer`、advisor 5x、planner 5x | ✓ |
| 6913 | Planer ×2、href 4 | `2x` + advisor `4x` | ✓ |
| 6863 | Berater ×4、CTA href `/de/produkte/`→`/de/genie/`（采纳） | CTA 既定对（保留 `data-linker-assistant-open`）+ `1x Der/2x den/1x Linker Berater` | ✓ |
| 6865 / 6919 | 各 1 | `1x 'Linker Planer'` | ✓ |
| 6897 | Berater ×1、href ×1 | `1x 'Linker Berater'` + `1x href -> /de/genie/` | ✓ |
| 6873 | planner href ×4 | `4x 'href="/linker-planner/"' -> 'href="/de/loesungskonfigurator/"'` | ✓ |
| 6881 blog 模板 DE | 文案+href 旧（清单） | **plan 无内容行**（`blog-index-template-de #6881: no change`） | **偏差 D1**（同 574，已由 #189+present 修好） |

德语"句子级"条目（清单 §2.B 内标注 1673/6827 privacy、2748/6700 "Planer-Auslegung" 类、826 Site Detail 句、6871 复合词、首页"not from the cart"）**不在本脚本**——按任务范围留文案评审批次。

## 3. §2.C 附件 alt

| 清单 | 清单预测 | plan 实测 | 对账 |
|---|---|---|---|
| Advisor alt | ×11 | **11 条**（3461/3475/4881/4882/4903/4904/5065–5068/6272） | ✓ |
| Planner alt | ×14（清单 ID 列 15 个） | **15 条**（4838–4840/4901/4902/5005–5008/5069–5072/6194/6195） | **偏差 D2**：清单表头 ×14 与其自己的 ID 列表 15 个不符；线上实测 15 |
| Site Detail alt | 未列 | **4 条**（5073–5076，"Linker Site Detail tutorial…"） | **新增 D3**：清单漏项；不修则旧名 grep 门不归零 |

媒体文件名一律不动（`linker-advisor-*.webp/mp4` 被正文引用）。alt 合计 11+15+4=30 条。

## 4. §2.E 草稿页

| 清单 | plan 实测 | 对账 |
|---|---|---|
| 2747 | `request-a-project-en #2747: content, title`（2x Linker Planner + 3x 地址 + title） | ✓（新步骤） |
| 3198 | `design-canvas-en #3198: content`（1 既定对 + 1x 规则）+ `seo title -> 'Solution Configurator: …'` | ✓ |
| 3998/3999 | `content, title`（规则+地址）+ 3998 `seo desc` | ✓ |
| 6635/6637 | `content, title` + 6637 `seo desc` | ✓ |
| 6702 | `request-a-project-de #6702: content, title` | ✓（新步骤） |
| 6696 | `design-canvas-de #6696: content` + `seo title -> 'Dachdetails: …'` | ✓ |

注：3999/6635 此前根本不在脚本里（`quote-configurator-2` 是新 resolve 键）；seopress desc 由新的
`Step.seo_desc` 承载；seopress title 走既有 `Step.seo`。

## 5. 清单 vs 现实的偏差（含新增项）

- **D1 · 574/6881 已修**（清单说 href 仍旧）：#189 把仓库里两个 blog_index 文件的文案与 href 改好并合并；线上两个 LC 模板于 2026-10-16 01:59 被 `present` 重建，内容 0 旧串。脚本只保留**元数据刷新**（见 D5）使二者一致。
- **D2 · Planner alt 15 个不是 14 个**（清单自身计数错误）。
- **D3 · Site Detail alt ×4（5073–5076）清单漏项**，已并入替换规则。
- **D4 · 两处 seo meta 已被抹掉**：6693 `_seopress_titles_title`、6633 `_seopress_titles_desc` 现已**不存在**（10-15 导入按 `Twins::meta` 语义在德语侧删空值）。旧脚本的 apply 会在此处 `SystemExit("SEO title is neither old nor new")` 崩掉；本轮改为**报告并容忍**（写回去也会被下一次导入再删，属 §D 词表/词典问题的症状），verify 同样以 note 放行。plan 行：`seo title: meta absent (the i18n import wipes it); left alone`。
- **D5 · 德语源 metas（清单未列，本轮新增，事故级）**：`_linker_de_content`/`_linker_de_title`（21 个英文源）是 `9-i18n.py` 导入的**德语来源**。2026-10-15 部署跑 `just cutover data` 时从这些旧值重导，把 10-14 已改名的德语页**整页导回旧名**（mod 时间 10-15 02:08–02:21；6633 标题、6869/6920 系列内容与台账一致）。不在脚本内刷新它们，下一次 `cutover data` 会**第三次**回滚。本轮把每个德语页的源 meta 刷新为**德语页的新状态**（内容=新德语；title 按既定对；幂等）。plan 中每个源一条 `german source #id _linker_de_content: … -> follows the German page`。
- **D6 · 工具页注释地址**：3302/6693 正文里的历史测量注释含 `/linker-planner/`、`/de/linker-planer/`；此前四个"工具页"步骤没有链接规则，本轮补上（`linker-*-en/de` 步骤各带本语言 `LINK_RULES`）。
- **D7 · 结构性漂移（确认）**：清单测得的德文旧名状态在 10-15 后依然成立（未再变）；EN 侧维持 10-14 的干净状态。即**10-15 导入只回滚了德语页**，EN 与 partial/template 未受影响（`TRANSLATED_TYPES = page,post,product`，partial/template 不在导入面）。
- **D8 · EN 6863 的孪生问题**：采纳的是 DE CTA `/de/produkte/`→`/de/genie/`（6863）；EN 932 同型 CTA 仍是 `href="/products/"`（非旧地址）。清单只点名 DE、`F 节`标记 EN 932 为已核实干净——本轮**不动**，此处记差异供裁定（英德同步口径）。
- **D9 · 留档不动**：`_seopress_redirections_value`（3993/3995）仍指 `/linker-planner/`（清单 §D，301 目标改单跳）；`linker_i18n_chrome_map`（3332 条，含旧对）与 `linker_i18n_slug_map`（§D）；`linker_commerce_present_backup`（安全网）；seopress_404 日志 3983–3987；修订版（inherit 状态）约 60 条含旧名——与 10-15 清账口径一致（不可见历史，随修订策略淘汰）。
- **D10 · 其他观察**：草稿/退役页 3198/3302/6696 的死标记里还有旧插件资产路径 `/wp-content/plugins/linker-ai-assistant/…`（非工具名/地址，不在本任务口径）。

## 6. 离线预演（同代码同数据，防线上长跑盲区）

- `.scratch/m2/rehearse.py`：用线上 dump（`live-dump.json` + `live-alts.json`）在本地跑 **同一份 `do_plan`**；输出 `.scratch/m2/rehearsal-plan.txt`。**与线上 plan 输出逐字节一致**（`diff` 除 `exit=` 行外为空；线上即 `.scratch/m2/plan-live.txt`）。
- `--check`：对每个步骤的线上原文套用 pairs+rules，断言**应用后不再有**旧名/旧地址（`stale left behind: 0`）。首次运行抓到了 D6（两个工具页），已修。
- `.scratch/m2/rehearse_verify.py`：在内存里模拟"已完成 apply"的状态（内容+标题+状态+seo+源 meta+alt 全部套用）跑同一份 `do_verify` → `verify: OK`（唯一输出 note=6693 seo title 缺失）。
- dump 未入库（3.2 MB 站点内容）；重新生成：`.scratch/m2/fetch-live-dump.php` 经 `wp eval-file -` 存为 `live-dump.json`，alt 列表为 `live-alts.json`（已在库）。

## 7. 本轮实现暴露并修复的缺陷（记录）

- **`wp eval-file` 作用域**：读 `$wpdb` 的 PHP 片段必须自带 `global $wpdb;`（eval-file 在函数作用域内执行）——第一次线上 plan 在媒体 alt 阶段以 "critical error" 告终（`.scratch/plan-live-attempt1.txt` 尾部）。已修 + 测试钉住（扫描所有 `*_PHP` 常量：用 `$wpdb` 就必须有 `global $wpdb;`）。
- **工具页链接规则缺口**：离线 `--check` 首跑发现 3302/6693 注释地址未改（D6）。
- **seo meta 缺失容忍**（D4）：旧代码 apply 会在此 `SystemExit`；现为报告+放行。
