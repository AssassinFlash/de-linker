# #302 配置器脚本译文

本地实例为 **c302**，地址 `http://127.0.0.1:9117`。
`just sync c302` 成功装入快照 `20261018-0541`，快照时间
`2026-10-17T21:49:21+00:00`；主题、uploads、线上 WindPress 缓存均随快照装入。
截图由 Computer Use 驱动本机 Chrome 采集，尺寸依据 AGENTS.md §5 的 1440 / 390 宽度要求。

## 完成标准与证据

| 票据要求 | 本分支证据 |
| --- | --- |
| 209 条配置器消息进入 PO，原有德语 msgstr 不变 | `configurator-before.json` 是基线原始 msgid → msgstr 映射；`translation-comparison.json` 为 209 → 209、丢失 0、增加 0、改动 0。所有条目有配置器源码与入口引用。 |
| 原生生成哈希名 JSON，移除手写文件，浏览器仍有德语 | `just i18n-tools` 使用 `wp i18n make-json --no-purge`；生成 `linker-tools-de_DE_formal-ff47dbd6ce1b77b210b406f2367c7ea7.json`。`de-runtime.json` 是浏览器实际内联脚本中的完整 209 条消息，source 为 `build/configurator.js`，与原始映射完全相同。 |
| 覆盖门在基线失败，修后通过 | `gate-before.txt`：当前门作用于基线提交的独立 `git archive`，`source gaps=201 JSON problems=1`、exit 1。`gate-after.txt` 保存修后结果。 |
| 源码完整性与 JSON 可再生性有可重复测试 | `tools/migrate/tests/test_i18n_coverage.py`：12 个测试，真实临时文件与原生 WP-CLI，覆盖 PHP/JS/TS、模板插值、JS 正则中的 `#`、文本域、开发文件与注释排除、手写/改动/缺失 JSON，以及不 purge PO。 |
| EN/DE 浏览器截图 | `screens/en-1440-input.jpg`、`en-390-input.jpg`、`de-1440-input.jpg`、`de-390-input.jpg`；另有两张 DE validation 状态。通过页头语言切换实际到达对应 URL，EN 保持英文、DE 为德语。 |
| `just check` 与 `just test` | 结果见 `validation.txt`。 |

`en-runtime.json` 确认 EN 页 `en-US`、390px 无横向溢出、不注入德语脚本；
`de-validation.json` 记录 DE 的邮编与必填错误原文。

## 共用英文消息的处理

三个既有英文消息在 Genie 与配置器中各有自己的德语措辞。
配置器使用 `configurator` gettext context，Genie 的生成 JSON 保持逐字节一致。
比较时只将该 context 前缀还原为原英文 msgid，德语字符串与复数数组逐项原样比较。
`App.test.tsx` 同时加载两工具译文后，检查未确认、重试和保存状态；
其余原有 i18n、术语、Sie 体与复数测试继续运行。
文案保留检查见 `copy-review.md`。

## 复跑

```sh
just i18n-tools
just i18n-coverage
uv run --locked --project tools/migrate pytest tools/migrate/tests/test_i18n_coverage.py -q
just check
just test
```

原生生成在临时目录逐字节比对，门禁不写回源 PO，也不依赖正在运行的实例。
迁移前映射可从 `translation-comparison.json` 中的基线提交及原手写 JSON 路径核实。
浏览器 payload 可直接与该映射重比：

```python
import json
from pathlib import Path

evidence = Path("docs/acceptance/2026-10-18/302")
before = json.loads((evidence / "configurator-before.json").read_text())
runtime = json.loads((evidence / "de-runtime.json").read_text())
after = {key.split("\x04")[-1]: value for key, value in runtime["messages"].items() if key}
assert before == after
```

## 未完成 (Claude)：评审与生产

本会话停在非草稿 PR、CI 通过、#302 留言待评审这一步。Claude 完成全量 diff 的
Spec / Standards 双评审后，按项目流程合并，并执行以下生产步骤：

1. 从合并后的提交运行 `just cutover backup`，记录备份目录与部署提交。
2. 运行 `just cutover deploy` 发布插件。该路径使用 `rsync --delete`，必须读回确认
   `wp-content/plugins/linker-tools/languages/` 下旧的 handle 命名文件已不存在、新哈希文件存在。
   WordPress 优先读取 handle 文件；残留旧文件会遮住新译文。
3. 运行 `just cutover verify`；在实际站点打开 `/solution-configurator/` 与
   `/de/loesungskonfigurator/`，用 1440 / 390 复核页面。DE 的
   `linker-tools-configurator-js-translations` 内应有 209 条消息、source 为
   `build/configurator.js`，未确认/重试/保存消息使用 `configurator` context。
   把生产读回与截图补到 #302。
4. 需要回滚时运行 `just cutover rollback --backup <本次备份目录>`，再读回页面与语言。

本票无凭据、选项、邮件、数据库或 VPS 服务迁移。
