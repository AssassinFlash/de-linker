# 评审 remit 改定的复核（#258，2026-10-18）

`eval/judges` 的 `REMIT` 改了以后（docs/specs/33-judge-bakeoff.md §部署 "职责说明"），用两组数据复核：一是 appropriate 的阈值是否还成立，二是线上的误标是否消失。这里的脚本任何人都能重跑。提交的 JSON 只有 ID、标签、置信度和标记，不含问句、回答和评审理由。

## 重跑

```sh
# 1. 线上 20 轮（只读：两个库都以 mode=ro 打开；输出含原文，只放草稿目录，不提交）
ssh linker-services python3 - < docs/research/2026-10-18-judge-remit/fetch_turns.py > <scratch>/turns.json

# 2. 用本树的级联重判这 20 轮，加上 production-flags.json 的夹具与价格的四种组合
uv run --locked --project services/genie python docs/research/2026-10-18-judge-remit/rejudge.py \
    <scratch>/turns.json services/genie/tests/fixtures/quality/production-flags.json \
    docs/research/2026-10-18-judge-remit/rejudge-summary.json

# 3. 校准集（#33 的 118 条问答，appropriate 阈值 0.5 出自这里）
python3 docs/research/2026-10-18-judge-remit/calibration.py ids > <scratch>/ids.jsonl
(cd services/genie/eval/judges && uv run --locked judges run --judges jev --runs 1 \
    --labels <scratch>/ids.jsonl --out <scratch>/run)
python3 docs/research/2026-10-18-judge-remit/calibration.py summary <scratch>/run/jev.jsonl \
    > docs/research/2026-10-18-judge-remit/calibration-summary.json
```

模型只走 AGENTS.md §5 的通道：Jev `typesafe/jev-1.13` 经 OpenRouter `/api/v1/systemone`；升级用 deepseek-flash，经 api.deepseek.com。

## 结果（本树的 remit）

- **校准集**（`calibration-summary.json`）：Jev 的 appropriate 与人工标签 118/118 一致，其中超出职责的 26 条全部判对；置信度全部 ≥ 0.70，阈值 0.5 下没有一条需要升级。正式轮用旧 remit 也是 118/118，最低 0.82。超出职责的题目都是服务请求（发货、付款条件、Incoterms、上门安装、保修索赔由谁处理），所以人工标签在新说法下不变。**appropriate ≥ 0.5 维持。**
- **线上 20 轮**（`rejudge-summary.json`）：
  - 第 27 轮的 citation、第 33 和 36 轮的 out_of_remit 都消失了。
  - 20 轮的 appropriate 全为 yes，Jev 置信度最低 0.80，没有一轮因 appropriate 升级。
  - 剩下的标记都是 grounded：35、37、41 与线上一致；38 被判 unverifiable（回答把电池称为 "Hochvolt"）。这些是 Genie 回答本身的问题，归 #285。
- **价格**（同一文件里的 fixture 行），对应 remit 的两道门：工具返回的价格可见（`price_visible`），而且账号已批准。

  | 工具返回 | 账号 | appropriate | 确定性检查 |
  |---|---|---|---|
  | 价格可见 | 已批准 | yes | 通过 |
  | 价格可见 | 未批准 | no | 标记：向未批准账号报价 |
  | 价格未返回 | 已批准 | no | 标记：数字没有工具依据 |
  | 价格未返回，回答引向登录或询盘 | 访客 | yes | 通过（grounded 判 1） |

- **第 1 轮**（`rejudge-round1.json`）：评审第 1 轮之前，用最初提出的 remit 做过两次重判。结论相同：27、33、36 清掉，appropriate 全为 yes。grounded 一项两次结果不同：第 36 轮一次被判 contradicted，一次判 supported，原因是安装步骤的顺序和 "1.5" 没写单位。这同样归 #285。
