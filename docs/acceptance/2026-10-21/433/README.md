# #433 · #332 系统失败批的缺失界面证据

- 日期：2026-10-21。票 #433（#332 的界面证据缺口，PR #409）。只补证据，不改产品代码。
- 实例：本地 `c332`，快照 `20261021-1023`（2026-10-21T02:26:29Z），插件来自本 worktree 的检出（补拍时 HEAD `4ca08d0e`）。WordPress `http://127.0.0.1:9187`，Genie `http://127.0.0.1:9189`。没有向生产注入故障，没有生产写入。
- 故障只用 `docs/research/2026-10-20-campaign-332/harness/` 在本机实现：`FaultServer` 的 SSE 截断代理、`stack.stop_genie()`（SIGTERM，8s 后 SIGKILL）。VPS-KILL 与 VPS-DOWN 停的都是本地 Genie。

## 补上的三处

票里缺的三处都看了屏，不再由别的状态推断：

- **390 宽的停靠条**：`*-390-*.png` 是 390×844 的视口。停靠条在 390 宽是整幅底部卡片（内容区 390×719，从 y=125 起）。
- **德语界面**：`*-*-de.png` 是 Polylang `/de/` 页（locale `de_DE_formal`）。失败句为 “Genie hat nicht geantwortet. Bitte versuchen Sie es erneut.”，按钮为 “Erneut versuchen”。
- **VPS-KILL 的当场错误**：`vps-kill-live-390-de.png`（以及 1440、EN 的对应图）。turn 路由回 502 `linker_genie_upstream`，当场是停靠条里的错误句，不再是“从 VPS-DOWN 的 502 推出来”。

VPS-DOWN 刷新后的状态也一起拍了：在 #411 之后它不是空停靠条，失败记录保留，首页 hero 自动展开并显示同一句错误。

## 状态表

文件名：`<state>-<live|reload>-<width>-<lang>.png`，宽 1440/390，语言 en/de。每个组合都有当场与刷新两张；每个组合另有 `runs/<state>-<width>-<lang>.json` 的原始记录。

| 状态 | 达到方式 | turn 记录 | 当场 | 刷新后 |
| --- | --- | --- | --- | --- |
| SSE-CUT | cut 代理保留第一条完整 `block`、去掉 `done` | 200，events `meta`、`block`，`stream_has_done` false | 停靠条，错误句 + Try again；问句留在 thread，输入框空 | 首页 hero 自动展开，同一句错误；问句仍在 thread |
| VPS-KILL | turn 开始 3s 后 `stop_genie()` | 502，`linker_genie_upstream`，`Genie did not answer.` | 停靠条，错误句 + Try again；问句回到输入框，thread 空 | 首页 hero 自动展开，同一句错误；问句仍在输入框 |
| VPS-DOWN | turn 之前停 Genie | 502，`linker_genie_upstream`，`Genie did not answer.` | 同 VPS-KILL 的当场 | 同 VPS-KILL 的刷新后 |

12 个组合（3 态 × 1440/390 × EN/DE）共 24 张图。`matrix.json` 是全部记录：每行有 `surface`（`dock` 或 `hero`）、`error_visible`、`retry_visible`、`field_value`、`thread_text`、`turns`；没有 `error` 行。

### 每态看到的

**SSE-CUT**（`sse-cut-live-*`、`sse-cut-reload-*`）

- 当场：HTTP 200，代理正文 699–1511 字节（随截断块里的文字变化），只有 `meta` 与一条完整 `block`，没有 `done`。停靠条显示 “Genie did not answer. Please try again.” / “Genie hat nicht geantwortet. Bitte versuchen Sie es erneut.”，`Try again` / `Erneut versuchen` 可见。截断块里的目录文字没有渲染。
- 刷新后：首页 hero 展开（记录 `surface: hero`、`opened: auto`），同一句错误；`thread_text` 仍是问句，输入框空。这是 #411 之后的行为，不是 2026-10-20 记录里的“刷新后错误消失”。

**VPS-KILL**（`vps-kill-live-*`、`vps-kill-reload-*`）

- 当场：turn 路由 502，正文 `{"code":"linker_genie_upstream","message":"Genie did not answer."}`（88 字节）。停靠条显示错误句；问句回到输入框，thread 为空（502 没有可渲染的回答）。
- 刷新后：首页 hero 展开，错误句和输入框里的问句都回来（390 宽的长问句在输入框单行显示，全文在记录的 `field_value`）。
- 问句：票 #332 用的库存问句现在由 `simple_stock` 路径直接作答（turn log 的 provider 为 `service`、model 为 `none`），会在 SIGTERM 的 8s 宽限内答完。这一轮的 VPS-KILL 用会走模型的问题：数据表问句与三相混合逆变器推荐问句（本机实测同型问题 12–21s）。每条 `runs/*.json` 的 `question` / `question_key` 写明该组合用的哪一句；390-DE 与 1440-EN 都是数据表问句，1440-DE 与 390-EN 的 `question_key` 是 `model`，即第二次尝试，第一次 doc 尝试没有达到当场错误（未落图）。

**VPS-DOWN**（`vps-down-live-*`、`vps-down-reload-*`）

- 当场：502 `linker_genie_upstream`，停靠条错误句 + 重试；问句回到输入框。这一张与 SSE-CUT 的当场不是同一个文件，VPS 两态也不再靠推断。
- 刷新后：首页 hero 展开，错误与问句保留。2026-10-20 的“刷新后空停靠条”在当前代码上已不存在；旧的 `ui/vps-down-error.png` 与 `sse-cut-live-error.png` 字节相同的问题，这一轮由各自的当场图取代。

### 390 与刷新后的画面

- 390 宽下首页的停靠条入口气泡在 860px 以下由 `plugins/linker-tools/src/genie/genie.css` 的 `@media (max-width: 860px)` 隐藏，刷新后没有可点的停靠条入口；首页 hero 会自动展开并显示失败记录。记录里的 `surface` 因此是 `hero`，不是 `dock`。这是当前实现的行为，不是截图缺失。
- 1440 宽下刷新后同样是首页 hero 自动展开；停靠条可在页面上用气泡打开，本轮没有另拍“点开后的停靠条”，状态表记的是实际看到的 hero。

## 与 2026-10-20 记录的关系

- #332 的 defect 判定（含 D3、D4）保持 2026-10-20 的原样，是当时的证据。SSE 截断与 502 刷新丢状态的修复是 #411，本轮补拍跑在修复后的当前代码上。
- 因此本轮刷新后的画面与 #332 当时的记录不同：错误和问句保留，hero 展开。不要把这两段时间的行为混写成一条。
- 生产冒烟没有重跑；生产写入没有发生。

## 证据位置

- 仓库（随 PR 提交）：`docs/acceptance/2026-10-21/433/`，含 24 张 PNG、`runs/*.json`、`matrix.json`、`capture.py`、`capture.mjs`。
- 电池证据目录（与票里的 `ui/` 对应）：`~/de-linker-data/campaign-332/ui/`，同样的 24 个文件名，由 `capture.py` 在最后复制。
- 仓库这份是权威副本；`ui/` 那份是电池目录里的同一批文件。

## 复跑

```bash
just up c332 && just pull load c332 latest && just serve c332
uv run --locked --project docs/research/2026-10-20-campaign-332/harness \
  python docs/acceptance/2026-10-21/433/capture.py
```

部分重跑与重建索引：

```bash
# 只重跑 VPS-KILL 的 390 德语；其他状态的行保留在 matrix.json
uv run --locked --project docs/research/2026-10-20-campaign-332/harness \
  python docs/acceptance/2026-10-21/433/capture.py --states vps-kill --combos 390-de --no-ui-copy

# 只从现有 runs/ 重建 matrix.json 与 ui/ 副本
uv run --locked --project docs/research/2026-10-20-campaign-332/harness \
  python docs/acceptance/2026-10-21/433/capture.py --matrix-only
```

部分重跑只替换所选状态与组合的行，其他行从现有 `matrix.json` 保留；`--matrix-only` 从 `runs/` 重建全部十二行并刷新 `ui/` 副本。

`capture.py` 在开始前要求 Genie 健康且 `linker_genie_url` 指回 `http://127.0.0.1:9189`；结束时恢复 URL。VPS-KILL 最多试四次（doc / model 交替），只有当场错误真正出现才落图；一次 turn 在故障生效前答完会立刻记错并重试。尝试次数与每次的 `question_key` 写在每条 VPS-KILL 记录的 `attempts` 里：1440-EN 与 390-DE 第一次命中，1440-DE 与 390-EN 第二次命中。

## 仍然没有的

这些不在本票的“三处”里，也没有写成本轮看过：

- 半条 `block`、attachment 事件、reading 事件截断的截图（#332 已对 c332 重放，仍无截图）。
- 模型 500 的德语截图（M500-DE 的德语句子仍是 API 正文）。
- Jev 502 与 AB-500 handoff 句的截图。
