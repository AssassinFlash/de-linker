# 对抗审查修复轮 — 验收证据汇总（2026-11-04）

地图：[#899 对抗审查根因地图](https://github.com/AssassinFlash/de-linker/issues/899)（七票全决，地图已收口关闭）。

## 决策 → PR → 生产 对照

| 缺陷组 | 决策票 | 修复 PR | 生产证据 |
|---|---|---|---|
| 参数表零关联+假绿 | #900 | #911、#916（15 张裸表根治） | 配对发布读回（见下方 Genie 段） |
| Genie 三处过早失败 | #901 | #908 | 首页入口无错误闪现；单元/集成测试与 CI 绿 |
| SessionBoundary 冻结 | #902 | #909 | 生产 /solution-configurator/ 焦点往返工作区原样立即可见，无门无错误 |
| #895 缩圈声明 | #903 | #910 | ESA 六产品生产 meta `stacks_parallel_max=3 expansion groups`（CAS 读回） |
| 多簇硬编码 | #904 | #909（引擎）+#910（数据） | 同上 + 引擎枚举测试（3 组×≤4=手册算术） |
| browser_claim 泄漏 | #906 | #908 | 部署后 `Conversations.php` 与 main 逐字节一致；hourly 回收 sweep 随 cron |
| 禁用词残留 | #905 | #907、#913、#914、#915 | 最终生产扫描 `findings=0`（见下） |
| CI base-race（本轮发现） | — | #912 | #912 自身 run 41781717968 的 planner 验证步骤通过 |

## 文案施写记录（#905 链）

- 营销 6 对页 post_content 施写（`/tmp/apply-copy.py`，逐页精确断言+读回）：13(15)、6913(14)、746/6871(3+3)、792(4)、874/6919(6+4)、2748/6700(9+11)、932(3)、6863(1)。
- 全站扩展（live-apply-plan.json，66 对/20 文档）：14、552、623、749、792、826、842、862、1755、2748、3302、6693、6698、6867、6869、6873、6885、6915、6917、6923 全部 OK；6865 由 MT 管线先行产出干净译文（GONE-DIFFERENT=MT 已覆盖，最终扫描无残留）。
- 法律页外科修正：隐私 1673/6827 各 5 组（法定留存年限与 §12 UStG 依据原样）；退货 1038/6698 各 2 组（order confirmation→delivery documents、order number→Proforma number / Auftragsbestätigung→Lieferdokumente、Bestellnummer→Proformanummer）。
- FAQ：docs/faq 数据修正（#914）+ 生产 import；GMK330 新措辞在新存储 `_linker_faqs` 与渲染层双重读回（页面文本 `Which CT version is included with this GMK330?` 可见）。
- 最终生产扫描（合并 #915 规则后）：`hits=2 baselined=2 legal=41 findings=0 → clean`。法律豁免集 8 页，全部命中句按三分法分诊在案（copy-review.md A.5）。

## 部署与数据安全

- WP 代码部署：`just cutover deploy`，部署自带 DB 快照；回滚点 `deploy-prev/20261104T055106307068Z-5329b7d7f`；部署后全页型探针 200、法律页/同意链完好。
- 数据写入前完整备份：`cutover-20261104-0607`（增量硬链，保留滚动回收最旧份）。
- 工具根因记录：远端 `eval-file`/`include` 对无 `<?php` 开标签载荷按纯文本回显——施写器一律带标签 + 标记包裹输出 + 幂等重试。

## Genie 配对发布

- **成功**：candidate 运行时 `20261104T084415175869Z-c8160ead`（源 c8160eada），索引 epoch 86→**91**（index_version 20261104T084814Z-400898000），双单元 active，ready ACK accepted+complete（journal 按规约自动删除）。
- 过程拦截记录：①首次尝试被 #900 新硬门诚实拦截（15 张裸 datasheet 表）→ #916 根治；②第二次因 A 的孤儿租约（local-rebuild-batchA2）认领失败 → 清退为自然到期态；③第三次因 ET DE 孪生覆盖漏算原生 table_columns 授权（仍 1 裸表）→ #917 修复后归零通过。
- 生产索引门禁读回：datasheet 66 表 / 55 带 scope / **0 张阻塞裸表**；豁免带理由（device_not_published 6、device_not_associated 2、parse_structure_damaged_sibling_covered 2）。
- Woo 队列终态：status=ready、materialization_complete=true、epoch 91；`preparation_complete=false` + 112 条 `table_without_scope` 为**诚实的逐关联覆盖报告**（旧版假绿 [] 的对立面）。
- 调度器 com.linker.knowledge-publication 已以新源（releases/c8160eada1f7）恢复运行（900s 轮询）。

## 发布验收中抓到的独立新缺陷（另立项根治）

- **Genie 答案数字丢失**：服务层真问（turn 732）grounded 回答引用了正确的 ESA 手册页面，但全部数字槽位丢失；检索块带正确标签 `[n1=4]/[n2=6]/[n3=3]`，故根因在答案侧数字填充/校验而非知识索引。**已根治并上线**：#918（封口器 `_seal_attachment_figures` 从未许可知识块数字事实；修复=被引用块许可其自身数字，守卫不减弱），配对发布至运行时 20261104T094242259491Z-8c9e6d80、索引 epoch 92。**生产复测通过**：同一 ESA 问题的回答现含「bracket 3 / 离墙 4 / 沿墙 6 / 混能每组 3」并如实说明手册未给全系统总数。
- Turnstile 在自动化浏览器内阻挡公开 Genie 发送（"No request has been sent"）——真问验收因此改走 VPS 服务层（缺陷所在层）通道完成。**根因定性**：WP 侧 prepare 健康（200/enforce/真实 sitekey），失败在 Cloudflare 对自动化浏览器的判定（按设计）；**另发现真实 UX 缺陷**=每个 turn 都要有效证明 + Proof::LIFETIME=300（持续对话每 5 分钟重验），由 `fix/genie-session-trust`（会话级信任+按需挑战+本地测试密钥配方）处理中。

## 本轮引入并根治的回归（写入路径）

- **法律页脚本反斜杠损伤**：主线自定义文案写入未做 `wp_slash()`，WP `wp_update_post` 的 unslash 吃掉脚本转义（隐私/退货四页）。1673/6827/1038 的损伤还带有旧伤成分（其参照修订版已无反斜杠）。修复：以已修好的 6698 的完好 `tv-legal-js` 块为参照整块替换 + `wp_slash` 写入 + 逐字节读回（四页均恢复 29 个反斜杠）。教训入规约：任何自定义 `wp_update_post` 写入必须 `wp_slash`，部署验收的法律脚本检查正是这类损伤的哨兵。
- **发布流程的卫生**：孤儿租约清退、journal 残留处理、本地 main 与合并源同步核对——均在 #899 的配对发布段记录。
- 来源旅程：2026-10-21 垃圾邮件 → 最小打扰防护 → 真实攻击 → 紧急分层防护（Turnstile enforce 由此而来）；业主双重要求「挡机器人+不误伤真人」继续同时生效。
