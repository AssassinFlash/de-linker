# #229 页头 EN/DE 同构

## 实现与判据

德语较长的导航标签及联系按钮使现有 `header-menu.js::fit()` 在操作区已压缩后仍判定总宽度超出，
将整排导航和联系按钮一起折叠。既有 LC partial 本来就含六个入口，缺陷在布局可用空间。
布局只在既有 WindPress `chrome.css` 中收回德语桌面导航的水平留白；LC、PHP、英语及全部文案未改，`fit()` 未改。
逐状态验收另发现菜单关闭后延迟焦点会抢回焦点：在现有键盘处理里增加“仍展开且尚未完成焦点”判断，
防止关闭后的回调关闭下一菜单，以及已完成的回调覆盖下一次方向键选择。

英语线上实际结构：1280 折叠、1440/1920 整排、390 移动菜单。因此 1280 双方保留折叠，
符合英语像素零变化与两种语言同构；不把 CSS `min-width:1280px` 的候选布局当成实际显示结果。
详见 [裁定变更台账](change-ledger.md) 与 [文案核对定稿](copy-review.md)。

## 实例与复跑

- 唯一实例：`c229`，`http://127.0.0.1:9099`；工作树 `de-linker-worktrees/c229`，分支 `feat/229-header-parity`。
- `just sync c229` 建实例时遇到另一会话持有的快照锁，没有改锁或进程；先装完整快照 `20261018-0218` 取修改前证据。
- 该并发快照完成后，用 `just pull load c229 latest` 将最新完整快照 `20261018-0238` 装入本实例；快照时间 `2026-10-17T18:49:26+00:00`。
- 再运行 `just wp c229 linker-commerce present --allow-stale --user=1` 安装本票样式，`just windpress-compile c229 --user=857558227@qq.com` 完成官方后台编译。
- 本地邮件仅写文件；没有提交询盘、注册或发信动作。

```sh
LINKER_E2E_SKIP_SERVICES=1 \
LINKER_HEADER_CAPTURE=$PWD/docs/acceptance/2026-10-18/229/states \
just e2e c229 header-parity.spec.ts

bash docs/acceptance/2026-10-18/229/capture.sh \
  "$PWD/docs/acceptance/2026-10-18/229/pixels" http://127.0.0.1:9099
```

布局规则最终每侧 5px，六个入口从原有每侧 14px 收回总计 108px，保持原字号、文字和 44px 点击高度。

结构测试只需要快照 WordPress，不启动 Genie 或引擎。截图开关只输出文件，不修改实例数据。
像素脚本复用本仓库 `249/pixel/shoot.mjs` 的已验证拍摄条件：同机同 Chromium、同视口、匿名上下文、
软件光栅及 sRGB、禁动画与光标、等字体及图片完整解码；预览卡在各自临时浏览器中置为关闭，以记录静止页。
这是测试上下文设置，不改线上存储或用户已有浏览器会话。

`pixels.py` 对 RGB 三通道逐像素判异，容差 0、无掩膜；图片尺寸不一致即失败。
德语桌面裁定变化只可出现在页面顶部 89px 的页头，页身出现差异同样失败。

## TDD 与行为回归

公共测试边界由 #229 的完成标准指定：浏览器中实际呈现的页头与菜单行为。

- **Red**：德语 1440 的完整桌面导航可见性失败；[失败记录](red/test.log)。
- **Green**：同一条断言在 WindPress 编译后通过；[首轮通过记录](red/green.log)。
- 第二条边界回归：4px 初稿让德语 1280 提前展开，矩阵中两条断言失败（[记录](red/boundary.log)）；最终采用 5px，使 1280 保持英语既有折叠态。
- 菜单焦点回归：两条 DOM 事件测试先失败后通过，`red/focus-red.log` / `checks/focus-green.log`；页头脚本单元共 6 项通过。
- 最终矩阵：`tests/e2e/specs/header-parity.spec.ts`，EN/DE × 四宽度的结构与无重叠、1440/390 的五个菜单逐状态开关、跨宽度重排；结果见 `checks/header-matrix.log`。
- 连续复跑结果见 `checks/header-repeat.log`，无数据库清理、选项修改或依赖服务。

## 最终结果

| 视口宽度 | EN / DE 结构 | EN 全页差异像素 | DE 全页差异像素 | DE 差异边界 |
|---|---|---:|---:|---|
| 1280 | 双方折叠 | 0 | 0 | 无 |
| 1440 | 双方六个桌面入口 + 联系按钮 | 0 | 13,110 | (180,21)–(1416,67)，仅页头 |
| 1920 | 双方六个桌面入口 + 联系按钮 | 0 | 13,052 | (422,21)–(1656,67)，仅页头 |
| 390 | 双方移动菜单 | 0 | 0 | 无 |

四组英语全页均 0 差异；德语桌面变化已获裁定，页身 0 差异；没有掩膜或容差。
1280 的全页图片为 1296px 宽，是线上与本地共同存在的横向文档尺寸；两边浏览器视口均为 1280px，未裁切隐藏多出的像素。

- 最终浏览器矩阵 **14/14**，连续复跑 **14/14**。
- 重新 fetch / rebase `origin/main` 后，全量 `just check` 退出 0（`checks/just-check.log`）；全量 `just test` 结果单列于 `checks/just-test.log`。
- 页头脚本单元 **6/6**，包含两条先红后绿的延迟焦点回归。
- Computer Use：EN/DE × 1440/390；产品菜单、移动菜单、德语工具展开，手机语言切换 EN 落到英文首页；截图见 `computer-use/`。临时视口已恢复。

## 证据索引

| 证据 | 位置 |
|---|---|
| 全页 live/local + 精确像素计数 | `pixels/*-{live,local}.png`、`pixels/results.json` |
| 页头前后上下对照（上 live、下 local） | `pixels/*-headers.png` |
| 修改前德语四宽度 | `before/de-*-before.png` |
| EN/DE 桌面与移动菜单每个状态 | `states/` |
| Computer Use 实走 | `computer-use/` |
| 全量静态、单元与夹具检查 | `checks/` |

## Spec / Standards 自检

全量 diff：`git diff origin/main...HEAD`，执行会话分别按票规格与仓库标准自检；独立 PR 评审交 Claude。

- Spec：CSS 优先；保留全部德语标签；英语像素门及四档同构分别验，不把代码存在当成运行证据。
- Standards：样式仅进 WindPress volume，经 present 和后台编译；无 PHP 设计、内联 CSS、第二样式通道或新依赖。
- LC partial 与 Woo 数据装配原已对等承载六个入口，本票不新增自定义呈现通道。
- 全拆检查：新增代码未引入 `tv_b2b_` / `Linker_AI_` / `dlk-` 等旧标识符；既有 `.tv-*` 页头 DOM 钩子是当前 LC 与 WindPress 的公共接口。
- 账号、引擎、翻译、NLU 及模型通道无改动；登录／注册链接由 #223 处理。

未部署、未合并；回滚仅撤本票的 CSS 规则并重新 present / 编译。
