# #229 页头 EN/DE 同构 · PR #294 第 2 轮

## 当前判据及边界异常

德语保留原文、六个入口与联系按钮。英语 1280/1440/1920/390 与线上同机、同 Chromium、同视口的全页精确 RGB 差异须为 0，无掩膜、无容差。

本轮按评审将 90 宽度扫描扩到 Chromium、WebKit、Firefox：390，1276–1300 每 1px，1310–1940 每 10px。运行时 folded、实际导航/CTA 可见性、六个入口、菜单按钮与盒子无重叠分别断言。

**未完成：Firefox 的 1283–1287 英德同构。** 原规则在 Chromium/WebKit 全部一致，Firefox 在这五个宽度 EN 已展开、DE 仍折叠。按第 2 轮明确指示“先报表、别继续调参”，本轮保留边界区 1280–1287 原规则，记录完整表交评审裁定。测试继续断言一致性，失败未 skip、未改成预期成功。

## 安全余量的来源

既有 LC partial 已含全部入口；视觉调整只在 WindPress `chrome.css`，无 LC、PHP 或 `fit()` 的新布局分支。

[三引擎原始测量](round2/layout-metrics.json) 覆盖 1280–1300、1310–1940 与 1366，共 86 宽度/引擎，字体加载后强制紧凑操作区、临时将链接 padding 置 0，测量四块宽度；探针在同一页面计算后立即移除，不写实例或线上。

| 引擎 | 版本 | 零 padding 四块总宽 |
|---|---|---:|
| Chromium | 156.0.8078.4 | 1156.5625px |
| WebKit | 27.2 | 1156.5625px |
| Firefox | 157.0 | 1156.9166717529297px |

spread = 0.3541717529296875px。每个链接每侧另留 1px，六链接合计 12px；这是第 2 轮评审要求的压力余量，不是字体事实。

```text
预算 = ceil(最宽零 padding 部分 + 实测 spread + 6 × 2 × 1px)
     = ceil(1156.9166717529297 + 0.3541717529296875 + 12)
     = 1170px
```

从 1288px 起：容器可用宽度（32px 外侧留白、1360px 上限）减预算、减三处既有 fluid gap，余下分给 12 个 padding 面；向下取 1/64px 并封顶 EN 的 14px。对最宽引擎，1170px 预算在布局量化前留下 13.083328px，比最小目标 12.354172px 多出向上取整的 0.729156px。真实压力测试实际每侧追加 1px 后等待两帧，让 `fit()` 执行，导航及 CTA 仍须展开。

预算、来源及边界区处理均已写入 CSS 注释、[安全计算](round2/safety-margin.json)、[规格](../../../specs/12-site-chrome.md) 与 [变更台账](change-ledger.md)。复测量宽命令：

```sh
node docs/acceptance/2026-10-18/229/round2/measure.mjs \
  http://127.0.0.1:9099 /tmp/c229-header-metrics
```

## TDD 与复跑

先加 WebKit/Firefox 项目跑原样式：[扫描红灯](round2/sweep-red.log)，Chromium/WebKit 各 0 个不一致，Firefox 82 个。先写追加 12px 压力测试，[原样式在 1288 失败](round2/spacing-red.log)，再加入上述预算。原第 1 轮“再加 1/64px 即折叠”测试已被有余量的压力测试取代。

```sh
just sync c229
just wp c229 linker-commerce present --allow-stale --user=1
just windpress-compile c229 --user=857558227@qq.com
LINKER_E2E_SKIP_SERVICES=1 \
  LINKER_HEADER_CAPTURE="$PWD/docs/acceptance/2026-10-18/229/round2/states" \
  just e2e c229 header-parity.spec.ts
bash docs/acceptance/2026-10-18/229/capture.sh \
  "$PWD/docs/acceptance/2026-10-18/229/pixels" http://127.0.0.1:9099
python3 -m unittest discover -s tests/visual -p 'test_*.py'
just check
just test
```

Playwright 的两个新增项目仅匹配 `header-parity.spec.ts`；账号、模型等其他套件仍只跑 Chromium。测试截图按引擎分目录，避免互相覆盖。扫描的 Firefox 边界断言仍会报告上述五处失败，供评审裁定；其余压力及菜单状态测试应通过。

## 最终证据

| 引擎 | 扫描宽度 | 不一致宽度 | 1288 以上展开宽度 | 德语实测余量 |
|---|---:|---|---:|---:|
| chromium | 90 | 0 | 77 | 13.4500–13.6200px |
| webkit | 90 | 0 | 77 | 13.4500–13.6200px |
| firefox | 90 | 1283, 1284, 1285, 1286, 1287 | 77 | 13.0333–13.2834px |


完整 90 行表与原始 JSON：[Chromium](round2/chromium-sweep.md)、[WebKit](round2/webkit-sweep.md)、[Firefox](round2/firefox-sweep.md)。汇总：[sweep-summary.json](round2/sweep-summary.json)。三引擎在 1280/1440/1920/390 均同构；Firefox 的另外五个边界宽度保持未完成。

最终矩阵 **23 passed / 1 failed，59.3s**，无 skip / xfail；唯一失败是 Firefox 边界扫描的 1283–1287，共五个宽度。每个引擎的六点加压测试通过，共 18 点；五类桌面/移动菜单交互与 resize 恢复测试均通过，见 [最终日志](round2/e2e.log) 和 `round2/*-spacing.json`。

| 视口 | EN 差异像素 | DE 差异像素 | DE 边界 |
|---|---:|---:|---|
| 1280 | 0 | 0 | 无 |
| 1440 | 0 | 13,059 | [188, 21, 1416, 67] |
| 1920 | 0 | 13,074 | [429, 21, 1656, 67] |
| 390 | 0 | 0 | 无 |


[全页像素 JSON](pixels/results.json)、[捕获日志](round2/pixels.log)。DE 非零只在获准的桌面页头 89px 内，页身差异为 0。1280 视口下双方文档宽为 1296px，未裁切；图像尺寸不同也会失败。

本轮新快照 **20261018-0409**，manifest.created=`2026-10-17T20:17:30+00:00`；重新 present 后由官方后台编译，缓存 last_generated=1792268374、676880 bytes，见 [实例读回](round2/instance.txt) / [编译](round2/windpress-compile.log)。本地全量 [just check](checks/just-check.log)、[just test](checks/just-test.log) 均 exit 0；共享像素计数器的三个 CLI 场景通过，见 [comparator.log](round2/comparator.log)。基线 `606b1883`。

Computer Use 实走 EN/DE 1440/390、德语产品菜单、英德移动菜单、手机语言切换和德语工具展开：[现场截图](round2/computer-use/)。临时视口已恢复。提交的逐状态浏览器截图保留 [Chromium](round2/states/chromium/)；其余引擎的完整数据及执行记录保留在三表和日志中，复跑 capture 选项会生成全部引擎截图。

Firefox 的 viewport-aligned DOMRect.right 会读成 1283.0000305175781；[原始四宽度探针](round2/firefox-rects.jsonl) 显示边缘多 1/32768px。几何检查使用 1/1024px 数值精度范围，远低于 1/64px 布局单位，仅修正读数误报；真正的 1/64px 越界仍失败。精确 RGB 比较保持零容差。修正前记录保存在 [sweep-before-rect-normalization.log](round2/sweep-before-rect-normalization.log)。

原始第 1 轮证据保存在 [round1/](round1/)，不以其 Chromium 单引擎结论代替当前三引擎验收。

## 范围与交接

执行会话只使用 **c229**，`http://127.0.0.1:9099`，专用工作树 `de-linker-worktrees/c229`。本轮重新同步线上快照并用本地密钥，邮件留在文件；没有提交表单或发信。

全部原词及 .po 术语保留，见 [文案复核](copy-review.md)。首轮延迟焦点修复及局部 `isOpen()` 不变。新增代码不引入旧标识符；`.tv-*` 是当前 LC 的公共接口。登录／创建账户链接属于 #223，未修改。未部署、未合并、未写生产。独立 Spec/Standards 复评交 Claude；Firefox 1283–1287 的例外必须由评审决定，本轮不自行批准。
