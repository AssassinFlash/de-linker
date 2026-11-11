# #548 域 6 · 产品身份与兼容 · 身份披露复验（2026-11-11）

D 线 `docs/acceptance/2026-11-11/548-domain-gap-matrix.md` 第 6 域判为「需补验」：
`ToolIdentity.tsx` 最后一次改动是 2026-10-23（`81cd1c5b1`），而 11-06 一屏 quick
start、11-08 通用模块分级、11-09 报告修复都重建了它周围的界面。本记录补上原生
复验，并把断言固化成可进回归的 e2e。

## 结论

**无回归。** 四组合（EN/DE × 1440/390）加英文项目列表，共 5 处挂载点，全部与
2026-10-22 基线一致：

| 检查项 | 基线（10-22） | 本次（11-11） | 判定 |
| --- | --- | --- | --- |
| 产品名 | `Solution Configurator` / `Lösungskonfigurator` | 相同 | 一致 |
| 归属行 | `by Linker` / `von Linker` | 相同 | 一致 |
| 边界声明（EN） | “a displayed model provides no engineering approval” | 整句逐字相同 | 一致 |
| 边界声明（DE） | 三句，末句 “Die Darstellung ersetzt keine fachtechnische Freigabe.” | 三句逐字相同 | 一致 |
| 署名链接 | 10 | 10（含 `rel`/`target` 全等） | 一致 |
| 整块文本 | — | 两宽度归一化后逐字相同 | 一致 |
| 保存态 | `Saved · revision 3` / `Gespeichert · Version 3` | 同为 revision 3 | 一致 |
| 横向溢出 | 0 | 0 | 一致 |
| 字体 | loaded | loaded | 一致 |

德语署名第 9 条是本地化的 `© OpenStreetMap-Mitwirkende`（基线亦如此），不是英文
遗漏 —— 两语言链接总数同为 10，href 指向同一 `copyright` 页。

## 差异判定的取证

以 git 追史定案，不是靠推断：

```
git log 81cd1c5b1..main -- apps/planner/src/components/ToolIdentity.tsx   → 0 条
git log 81cd1c5b1..main -- apps/planner/src/components/CreditText.tsx     → 0 条
git log -S'lp-tool-identity' -- plugins/linker-commerce/content/windpress/planner.css
                                                                         → 仅 81cd1c5b1
```

身份组件、署名链接表与 13 行 `lp-tool-*` 样式规则自引入后无人改动；11-06 之后的
提交只动 `ProjectEditor`、`QuickStart`、`Workspace` 与报告链。挂载点也仍在
`apps/planner/src/main.tsx:60`，位于 `SessionBoundary` 之内、`Workspace` 之后，
项目列表与每个工作区共用同一处。因此本次若出现差异，只会是回归；实际未出现。

## 一处需要说明的非契约差异

**revision 数值不是常量。** 10-22 基线的 `revision 3` 是当时那个项目被编辑三次的
计数；本次复验通过站点区块两次真实保存把项目推到 revision 3，使两记录可逐字段
对照。合同要求的是「身份块框在一个已保存的修订上」，不是「必须等于 3」——
e2e 断言写成 `/^Saved · revision \d+$/`（德语 `/^Gespeichert · Version \d+$/`），
不把数字写死；矩阵记录实际观测值。

## 断言与证据

`tests/e2e/specs/planner-identity.spec.ts`——四行（EN/DE × 1440/390），在 review
实例上跑真 bundle、真建项目：

- 产品名、归属行、角色说明、边界段落、`Software and data credits` 标题；
- 整块 `innerText` 归一化后与合同全文逐字相等（两宽度之间也不得漂移）；
- 10 条链接以 `[label, href, rel, target]` 四元组精确比对，顺序固定；
- 无横向溢出；身份块有实际布局盒；
- 同行读取 `.lp-save-state`，确认框的是已保存修订而非未保存草稿。

实跑：`4 passed (12.8s)`，`tsc --noEmit` 与 `prettier --check` 均通过。

`native/` 下 5 组 PNG/JSON 对（元素级 CSS 尺寸截图 + 同帧 DOM 读回），
`native-matrix.json` 按 10-22 基线的字段结构索引；`capture.mjs` 是生成脚本，
依赖从 `tests/e2e` 解析，不需要二次安装。

## 边界

本记录只覆盖身份披露。域 6 的「产品兼容」另一半（兼容合同、工程覆盖层的运行时
证据）不在本次范围，D 线矩阵中该域的判定需连同这部分一起补。工具页设计可改
（业主裁定），但产品名、边界声明与 10 条署名的**事实内容**按合同固定，本次未改动
任何产品代码。
