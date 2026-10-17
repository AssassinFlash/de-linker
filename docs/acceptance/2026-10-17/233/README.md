# #233 Genie 理解层 · 验收证据（2026-10-17）

本地实例 `g233`（`just up g233` + `just pull load g233 latest`，快照 2026-10-15）；本地 Genie `just serve g233`。

| 文件 | 内容 |
|---|---|
| `bare-words.json` / `.txt` | 裸品牌、型号、系列、分类词 75 条（EN 38 / DE 37），经站点 Genie 路由 `/wp-json/linker-ai/v1/genie/turn` 实跑：**EN 38/38、DE 37/37 出对应产品，0 例问候 / 称呼**；全部由代码走 `products` 路由。脚本 `services/genie/eval/understanding/run.py`。 |
| `jev-vps.json` / `.txt` | Jev 评测在 VPS（`srv1791674`，部署 venv，VPS 自己的 OpenRouter 密钥）上复跑，生产客户端 `jev.py` 的四题：**意图 73/75 = 97.3%**（#260 原 60 条 58/60；线上真实问句 15/15，其中 2 条按"also"第二意图计；严格单标签 71/75 = 94.7%，那 2 条置信 0.47 / 0.67，按设计交 deepseek-flash）；about_this_page 74/75，wants_person 74/75；p50 0.14 s。脚本 `eval/understanding/jev_eval.py`。 |
| `trial-genie.json` / `trial-summary.txt` | `docs/research/2026-10-17-knocket/raw/trial/questions.json` 20 题对 g233 实跑（`raw/trial/genie.py`，端口从 9033 改为 9057，其余不变）。 |
| `copy-review.md` | 新增客户可见文案（选型兜底句、文档兜底句、页码缩写）的对抗评审。 |

线上真实问句来自线上站 Genie 会话文章（`linker_conversation` 的 `linker_genie_thread`，2026-10-14 至 10-17，只读读取）；15 条去重后均不含姓名、邮箱、电话，原文入集。VPS 的 `turns.sqlite` 不存问句（只存输出与工具调用）。

界面：新增 `document` 块的渲染（`DocumentLink.tsx`，链接沿用 action 链接的现有样式，无新 CSS）。1440/390 × EN/DE 截图待 #252 合并后重新拉快照再拍（开工提示词规定）。
