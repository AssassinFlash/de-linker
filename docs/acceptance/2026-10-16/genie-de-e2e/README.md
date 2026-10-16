# Genie 德语四行 e2e 恢复（2026-10-16）

`tests/e2e/specs/genie.spec.ts` 的 `PENDING_MAIN` 自 2026-10-11 携带四条德语行
（R3-de / R5-de / R6-de / R7-de，均"measured 2026-10-11"，运行时 skip）。
本记录写每行的终态：两行复测恢复、一行是服务缺陷（已修）、一行是套件过期（已修）；
另修一处套件采样判定。改动后 `PENDING_MAIN` 清空，不同行终态不同，逐行给证据。

## 环境

- 实例 `m4check`（http://127.0.0.1:9033；engine :9034、genie :9035）：
  `just up m4check` → `just pull load m4check 20261015-1852`（ok:true，212 发布商品 / 2755 附件 /
  0 缺失 / 0 线上地址残留）→ `just serve m4check`（服务从本分支 worktree 起）。
- 服务级探针直接 `POST :9035/turn`（与套件同一个契约）；套件为
  `LINKER_E2E_INSTANCE=m4check npx playwright test specs/genie.spec.ts --grep "…"`。
- 轮次记录后仍可查：`~/.cache/linker-genie/turns.sqlite`（`GENIE_LOG` 默认路径）。

## 逐行终态

| 行 | 原 pending 原因（2026-10-11） | 2026-10-16 实测 | 终态 |
|---|---|---|---|
| R3-de | grounding 拒 raw number → 兜底模板不点名 HS3-5K（行有 `mustMention: ['HS3-5K']`） | 服务级 3/3 grounded（其一 2 次内部尝试后过）；e2e 各轮过 | 恢复（重采样/重试自愈） |
| R5-de | placeholder `compat.verdict` 不在本轮工具 → 兜底无文档 | 服务级 3/3 grounded（8 卡=7 放行电池+页面本体，文档在正文）；e2e 过 | 恢复 |
| R6-de | ①placeholder 不在本轮工具 ②德语答案含英文句子碎片 | 修复前 3 份德语采样全带英文条件句（turns 991–993）；修复后水合为德语条件句 | 服务缺陷，已修 |
| R7-de | 德语 Proforma 问题被答成团队邮箱句 | 产品自 2026-10-13 起答定稿登录句；套件正则认不出该句 | 套件过期，已修 |

### R6-de 根因与修复

兼容合同的条件是双语对（`plugins/linker-commerce/data/compatibility.json` 每条的
`conditions[].{en,de}`，`Compatibility::for_models` 两语齐发），而
`services/genie/src/linker_genie/facts.py::collect` 恒取 `en` 侧：
德语轮次里模型按提示词写的 `{fact:compat.condition…}` 水合后，把英文句子插进德语答案——
行的判据（`ENGLISH_ONLY` 正则，与 `template.german_is_clean` 同一形状）即失败。
2026-10-16 修复前（主检出服务）的 3 份德语采样 turns 991–993 全部带该英文句；
修复后（本分支服务）手工探针 turns 1002/1003 水合出德语条件句并 grounded。

修复：轮次 locale 透传到事实层——

- `agent.py::make_generate` 以 `request.locale` 建 `_ability_runner`
  （工具签名与 `INPUT_DOCS` 不变）；
- `abilities.py::AbilityClient.record(…, locale)` 转交 `collect`；
- `facts.py::_condition_text` 按轮次语言取侧（`de` 轮取 `de`、缺 `de` 回退 `en`，与
  `TradeRules::word` 同规则；`en` 轮只取 `en`，反向不泄漏；旧的字符串/`text` 形状仍可读），
  search-products 的 pairings 与 check-compatibility 两个调用点共用。

判分测试：`services/genie/tests/test_hydrate.py::test_a_german_turn_reads_the_german_side_of_a_condition`
（德语取侧、半写对回退）、`test_collect_check_compatibility_records_documents`（第二调用点）、
`services/genie/tests/test_agent.py::test_the_runner_hands_the_turn_language_to_the_ability_client`。

### R7-de 根因与修复

2026-10-13 服务端已改（`template.LOGIN_REQUIRED`，文案对抗评审
`docs/acceptance/2026-10-13/genie-facts-protocol/copy-review.md` 定稿）：
「Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.」。
套件 R7 的登录判据正则只认 `anmelden|log ?in|sign ?in`——定稿句是可分动词
「melden Sie sich … an」，永不匹配，故产品修好后该行仍以"the guest is not asked to log in"
被记为 pending。修复：正则补上定稿句形态（`melden Sie sich [^.]*\ban\b`）。
实测：turns 1008 / 1018 三次德语采样全为定稿句（grounded），新判据通过。

### 套件采样判定缺陷（本轮发现，一并修）

行循环原来用 `expect(attempts).toEqual([])` 判"过"，而 `askRow` 在"第 N 次采样才达标"时
返回的 `attempts` 仍带前面各次的失分记录——**首采样失分、后采样达标的行会被记成失败**
（pending 行则被记成 skip）。这与四处写明的设计相反：

- 文件头（原"asked once more … a row that misses them twice is a failure"）；
- `askRow` 注释（"the panel's own practice was to rerun a row until it shipped a compliant
  turn"）；
- PR #96 描述（前段"最多两次采样、两次都不过才算失败"，后段"最多三次采样…全不过才算失败"——新判定 = 全部采样失分才算失败，两种陈述同时满足）；
- 同文件 R7 自己的循环（达标时 `measured.length = 0`，只有全失才报告）。

暴露点：2026-10-16 整文件跑，R6-en 首采样因占位符写成 `compat.verdict.3611` 落兜底、
第二采样达标，行仍被记红（turns 1027/1028）。修复：行循环以 `result === null` 判——
三采样全失才是失败（pending 行则 skip），`attempts` 只作 measured 报告；
文件头同步改写为该语义。

## 复跑证据

四行 `--grep`（每轮 = 4 tests：R3/R5/R6 各最多 3 采样、R7 两语各 3 采样），本分支服务 + 本分支 spec：

| 轮 | 结果 | 耗时 |
|---|---|---|
| 1 | 4 passed | 48.5s |
| 2 | 4 passed | 34.1s |
| 3 | 4 passed | 59.9s |

`services/genie`：`uv run --locked pytest`（161 passed）、ruff check/format、mypy 全绿。
整文件 `specs/genie.spec.ts`（R1–R14 + 级联判分，23 tests）：

- 修前一轮（行循环缺陷未修）：除 R6-en 外全部行过；R6-en 首采样失分、二采样达标仍被记红
  ——上面"采样判定缺陷"的暴露点；判分步骤为先修套件而手动终止。
- 修后一轮（本分支最终码 + 最终服务）：**23 passed（8.1m）**，零 skip、零 fallback 轮次；
  级联判分 24/24 item 有终标签，`grounded` 无 0、`appropriate` 全 yes、`better_pick` 全 A
  （判分记录 `~/de-linker-local/m4check/e2e-judge/20261016-102356/`）。
- `specs/genie-dock.spec.ts`（浏览器半边，抽跑）：2 passed、2 skipped——两条 skip 是该文件
  自己的 pending-main（R13 芯片与套件客户），与本轮无关。

四行在修后整轮中的账：R3-de/R5-de/R6-de 首采样即达标；R7-en/R7-de 定稿句过判据。

判分行（本记录写就时的轮次原文，`turns.sqlite`）：

- R7-de（turns 1008 / 1018 三次采样）：`{"language": "de", "blocks": [{"type": "text",
  "text": "Bitte melden Sie sich in Ihrem Konto an, um diese Anfrage anzuzeigen.", "refs": []}]}`
  ——定稿句、grounded、无询盘数据。
- R6-de（修复后 turns 1002/1003）：答案含「Das GoodWe-ESA-Datenblatt nennt die Module … (S. 3)」
  ——德语条件句（修复前 turns 991–993 为英文原句）。

