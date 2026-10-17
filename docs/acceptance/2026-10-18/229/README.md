# #229 页头 EN/DE 同构

## 当前结果与判据

PR #294 第 1 轮修订以逐宽度边界为准，取代首稿的四宽度结构检查。
德语保留全部原文、六个导航入口和联系按钮；英语与线上四个验收宽度全页精确 RGB 比对须为 0。
当前结构由 [90 行扫描表](round1/sweep.md) / [原始数据](round1/sweep.json) 记录：

| 视口 | EN/DE 的共同状态 |
|---|---|
| 390、1276–1279 | CSS 移动菜单；无运行时 folded 属性 |
| 1280–1281 | 运行时折叠菜单 |
| 1282–1300（每 1px） | 完整导航与联系按钮 |
| 1310–1940（每 10px） | 完整导航与联系按钮 |

`data-tv-nav-folded` 与实际可见性分别断言；每个宽度同时验证六个入口、联系按钮、菜单按钮和无重叠。
另保留 EN/DE 的五类桌面/移动菜单交互及跨宽度恢复测试。

## 实现及原生承载

既有 LC partial 已含全部入口；Woo 数据装配无需改动。CSS-first 已足够：WindPress `chrome.css`
对德语桌面使用一个流动 `clamp()`，按实际可用空间分配最大 padding，封顶英语的 14px。
无需 LC 标记、PHP 布局或 `fit()` 语言分支；英语和移动端样式保持原状。

当前字体下，零 padding 的四块总宽 1156.5625px，容器最多 1360px，三处 gap 保持原有
`clamp(8px,1vw,16px)`。将剩余空间分给六个链接的 12 面，向下取 1/64px 布局单位。
最小值 4.546875px 让 1281 保持折叠、1282 起展开；这与 `fit()` 的 ceil/floor 和字体度量有明确耦合。
最大留白为 1300=6.03125、1366=11.359375、1440=13.34375、1920=12.953125px。
四宽度再加 1/64px 都会折叠，移除探针则恢复。原始量宽见 [layout-metrics.json](round1/layout-metrics.json)。

1440/1920 若使用 14px，所需总宽分别为 1367.7625/1372.5625px，超出 1360px 容器。
[裁定变更台账](change-ledger.md) 记录了四个宽度从固定 5px 到最大留白的前后截图及原因。
[文案记录](copy-review.md) 保持全部既有标签，无缩词、无新稿。

初轮的菜单焦点修复保留：关闭后不执行旧回调，过渡完成后兜底不覆盖后续方向键选择；
第 1 轮将三个重复读取统一为局部 `isOpen()`，不改变其行为。

## TDD 与第 1 轮评审逐项回应

1. 先写真实浏览器边界扫描，原 5px 在 **1282–1287** 六处出现 EN 已展开、DE 仍折叠：
   [红灯日志](round1/sweep-red.log) / [红灯数据](round1/sweep-red.json)。先用 4.55px 修齐边界，
   [90 宽度转绿](round1/boundary-green.log)。
2. 再写最大留白测试，固定 4.55px 在 1300 未达到可用 6px，
   [先红](round1/spacing-red.log)，再改为流动规则转绿。CSSOM 会截短小数，测试先归一到布局单位，
   才加下一个单位，避免把 12.953125 的序列化值 12.9531 当作实际布局值。
3. Standards 1：CSS 源注释同时写明联系按钮、共同折叠边界、字体和 `fit()` 耦合，指向扫描守卫。
4. Standards 2：局部 `isOpen()`；两条既有延迟焦点红绿测试继续保留。
5. Standards 3：单一 `navKeys` 常量；45s 测试预算与 900px 视口高度都有来源注释。
6. Standards 4：共享入口 `tests/visual/pixel-parity.mjs` 调用独立精确计数模块 `compare.py`；
   本票 `capture.sh` 只传验收参数，不再引用另一票的脚本，也不再持有计数副本。
   #249 既有材料保持原样。共享计数器的 CLI 夹具覆盖相同图片、单个绿色通道差 1、尺寸不等。

## 唯一实例与复跑

唯一实例 **c229**：`http://127.0.0.1:9099`，专用工作树 `de-linker-worktrees/c229`。
本轮重新 `just sync c229`；实例快照读回见 [instance.txt](round1/instance.txt)，
样式经 present 和官方后台编译读回，见 [编译记录](round1/windpress-compile.log)。

```sh
just sync c229
just wp c229 linker-commerce present --allow-stale --user=1
just windpress-compile c229 --user=857558227@qq.com
LINKER_E2E_SKIP_SERVICES=1 \
  LINKER_HEADER_CAPTURE="$PWD/docs/acceptance/2026-10-18/229/round1/states" \
  just e2e c229 header-parity.spec.ts
bash docs/acceptance/2026-10-18/229/capture.sh \
  "$PWD/docs/acceptance/2026-10-18/229/pixels" http://127.0.0.1:9099
python3 -m unittest discover -s tests/visual -p 'test_*.py'
just check
just test
```

浏览器测试不写实例数据，spacing 探针只改该测试页，结束后移除；无需清表。邮件留在本地文件。
像素比较共用同一 Chromium、同机、同视口，禁动画/过渡/光标，等待图片解码与字体。
每次只在一次性浏览器上下文中关闭主动预览卡。截图与 RGB 比较不提交表单、不写线上。

## 当前验收证据

刷新快照前后完整矩阵均 **8/8**（17.3s / 15.1s）；90 宽度均 0 不一致。
`just check` 与 `just test` 均 exit 0；共享计数器 1 个 CLI 测试的 3 个夹具场景通过。

| 视口 | 英语差异像素 | 德语差异像素 | 德语差异边界 |
|---|---:|---:|---|
| 1280 | 0 | 0 | 无 |
| 1440 | 0 | 13,090 | (189,21)–(1416,67) |
| 1920 | 0 | 13,084 | (430,21)–(1656,67) |
| 390 | 0 | 0 | 无 |

最终快照 `20261018-0328`，采集时间 `2026-10-17T19:40:54+00:00`。

- 全页 live/local 与精确计数：[pixels/results.json](pixels/results.json)；无掩膜、无容差。
- `pixels/*-headers.png` 上为线上、下为本地；四组英语必须为 0；德语变化只允许桌面页头 89px 内。
- 1280 的全页图片为 1296px 宽，来自线上和本地共同的横向文档尺寸；两边视口同为 1280，未裁切隐藏像素。
- 第 1 轮完整矩阵在刷新快照前后复跑：[刷新前](round1/e2e-before-sync.log) / [刷新后](round1/e2e.log)。
- 本地全量：[just-check.log](checks/just-check.log) / [just-test.log](checks/just-test.log)。
- Computer Use EN/DE × 1440/390：[本轮截图](round1/computer-use/)；实走桌面产品菜单、移动菜单、德语工具展开和手机语言切换。临时视口已恢复。
- 浏览器菜单逐状态截图与四宽度留白修改后截图：[round1/states/](round1/states/)。
- 首次提交的红绿记录及原始快照对照留在 `red/`、`before/`，当前判据以本轮记录为准。

## Spec / Standards 自检与边界

执行会话按两轴检查全量 diff，独立复评交 Claude。全部视觉修复留在 WindPress，LC 与 Woo 原生承载保持；
无第二样式通道、新依赖、PHP 设计或模型改动。新增代码不引入旧标识符；既有 `.tv-*` 是当前 LC 的公共接口。
登录／创建账户链接属于 #223，未修改。未部署、未合并、未写生产；[回滚方法](change-ledger.md) 无数据库迁移。
