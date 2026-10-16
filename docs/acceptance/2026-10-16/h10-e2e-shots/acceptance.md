# H10 · e2e 截图不再写进仓库 docs · 验收记录（2026-10-16）

台账 H10（H1 施工中发现）：`tests/e2e/specs/account.spec.ts:41` 把每一张验收截图写进
`docs/acceptance/2026-10-13/account-auth/shots/`——那是**已入库的目录**，于是
`just e2e` 的每一次运行都在工作树里重写 15 张 PNG，留下与本次改动无关的版本噪音
（`docs/acceptance/2026-10-16/split/acceptance.md` §6 记录过同一现象：那个票明确
"不把那些重写纳入提交"）。

## 1. 做了什么

- `shot()` 的输出路径从
  `../../docs/acceptance/2026-10-13/account-auth/shots/<name>.png`
  改为 `<repo>/.scratch/e2e-shots/account-auth/<name>.png`。
- `.gitignore` 增加 `.scratch/e2e-shots/`（一行三注释）：`.scratch/` 是仓库的
  工作区（里面可以有意提交东西），截图是「本次运行渲染了什么」的证据，不进版本库。
- `tests/e2e/README.md` §Shape 增加一条：截图落点与理由，并指向 H10。
- 历史 PNG（`docs/acceptance/2026-10-13/account-auth/shots/` 15 张 + README）
  **保留不动**——那是 #184 验收轮的记录。本票只把「运行会重写它们」这件事停掉。
  （详见 §3 的引用检查。）

## 2. 实测

在 `nfinal` 上跑 `just e2e nfinal specs/account.spec.ts`（H11 分支的树）：

- 13 passed；截图全部写进 `.scratch/e2e-shots/account-auth/`（`en-wrong-password.png`
  等 14 张 + 本轮 #184 新增的 `*-reset-*.png` 一并落在那）。
- `git status` 里没有 `docs/acceptance/2026-10-13/account-auth/` 的任何改动——
  历史 PNG 一个字节没被重写（`git diff` 空）。
- `git check-ignore -v .scratch/e2e-shots/account-auth/en-wrong-password.png`
  → `.gitignore:39:.scratch/e2e-shots/`（忽略生效）。

## 3. 历史 PNG 的现状（说明，不删）

15 张 PNG 仍在库里，且**不再被任何流程引用**：唯一写到这个目录的是
`account.spec.ts` 的 `shot()`（本票改掉），文档引用只有
`docs/acceptance/2026-10-13/account-auth/README.md`（该轮验收的记录）与
`docs/acceptance/2026-10-16/split/acceptance.md` §6（描述「套件曾重写它」这一现象，
正是本票要修的）。它们作为 #184/account-auth 验收轮的历史记录被保留；删除与否留给
后续的内容清理裁定（不在本票范围）。

## 4. 结论

e2e 截图是运行产物，落到 `.scratch/`（已有约定路径）+ `.gitignore`；仓库里的历史
PNG 保持原样、不再被运行改写。`just e2e-check`（types + prettier）绿。
