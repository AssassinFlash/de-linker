# 配置器移动端适配

参照：业主 2026-10-13 提供的房产 App 设计稿，原图留档为 `ref-realestate-app.png`。

## 改动

只改 48rem 以下：

- 单列卡片、12px 圆角、16px 页面边距与步骤间距。
- 标签在上，输入、下拉和主按钮提高到 48–50px。
- 选择项改为整行触控卡片。
- 已有屋顶步改为地图加底部抽屉卡，不新造地图业务。
- 无合格候选使用居中标记、一句结果、原因列表和返回输入。
- 报告就绪使用对勾、说明和单个下载按钮。
- 住宅与工商业增加固定步骤底条；底条只滚动到既有展开区块，不计算、不提交、不改变候选。底条高度由组件实测后写入 `--linker-mobile-nav-height`，页面底部按该值留白。
- 屋顶步隐藏底条。电站只有一个既有询盘步骤，因此不造底条。
- 1440 桌面几何不变。EN 修改前后视口截图像素差为 0。

## 真实计算

t111 初次缺少工程数据。按既有迁移执行：

```text
python3 tools/migrate/8-engineering.py --wp 'just wp t111 --' --write --backup-dir ~/de-linker-local/t111/backups
```

补齐后，`just e2e t111 specs/configurator.spec.ts` 为 17 passed。浏览器页面也完成了住宅方案、无合格候选、工商业指示区间和屋顶地图加载。

## 证据

- `metrics.md`：1440、390、430 的尺寸、底条和遮挡。
- `ours-1440-before.png`、`ours-1440-after.png`、`ours-1440-de.png`。
- `ours-390/en/` 与 `ours-390/de/`：项目类型、输入、方案、报告、屋顶、空态、工商业和电站。
- `ours-430-report.png`：430×932 抽查。

## 检查

- `cd plugins/linker-tools && npm run test:unit`：17 files, 99 tests passed。
- `npm run build && node bin/build-manifest.mjs check`：`build/ matches its sources.`
- `npm run build:check`：`build/ matches its sources.`
- `just e2e t111 specs/configurator.spec.ts`：17 passed。
- 新增 CSS 色值扫描：无匹配。颜色使用既有 `--linker-*` 与 `--proto-*` 变量。
