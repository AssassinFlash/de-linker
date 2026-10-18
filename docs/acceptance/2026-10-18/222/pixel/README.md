# #222 第一轮 · 纯 main 归因对照

快照：`20261018-1220`；实例仅 c222。两次均使用 `tests/visual/pixel-parity.mjs`，宽度 1440/390、初始高度 900、同机 Chromium、全页、禁动画、等字体和图片。无掩膜、无容差。

| 比较 | 零差异 | 未通过区域 |
| --- | --- | --- |
| 本分支 local vs live | 11/16 | 四组 DE 1440 页头各 13061 pixels；EN 390 产品页兼容产品缩略图区域 7597 pixels |
| 纯 main local vs live | 12/16 | 四组 DE 1440 页头各 13061 pixels |
| 本分支 local vs 纯 main local | **16/16，每组 0 pixels** | 无 |

两次 live 捕获的 EN 390 产品兼容缩略图相差 7597 pixels；第二次 live 捕获与两次完全相同的 local 捕获一致，表明该次差异发生于 live 捕获间。这里只记录图像变化，不推断缓存或图片服务根因。

因此本票未引入这些复刻面差异；绝对 live/local 像素门仍为 **未完成**，不能记为通过。德语页头属于现有 [页头 · EN/DE 完全一致](https://github.com/AssassinFlash/de-linker/issues/229) 范围；图片同步/呈现差异关联 [本地与线上同步 + 后台杂项提示清理](https://github.com/AssassinFlash/de-linker/issues/252)。本轮按 Claude 第一轮要求提供 main 对照并报告，不修改这些既有基线。

纯 main 从 `git archive origin/main`（`0fddf100`）导出三个仓库插件到当前工作树 scratch；Composer locks 与本分支相同，依赖复制在该导出中，未使用指回本分支源码的 vendor symlink。仅临时切换 c222 的插件 symlink，重启 c222 自己的 PHP server 后验证实际加载文件，重新 present/官方 WindPress 编译，再拍摄相同 16 组。工作树分支一直为 feat/222-pending-signed-in；没有在主 checkout 实施或操作其他实例。

主线 32 张截图已拍完后，uv 子进程中的 Python 缺 Pillow 导致比较器停止；使用已具备 Pillow 的系统 Python 重跑同一官方 `compare.py`，产生本目录 `main-only/results.json`，保留真正的四组页头 FAIL。没有调整截图、容差或比较算法。

`branch-causality.json` 保存全部逐页差异数、主线提交、实际类文件路径与恢复证据。`main-only/` 保留完整主线截图；根目录保留分支截图。对照结束后恢复本分支，类加载文件路径读回正确，WindPress CSS 与对照前逐字节相同；恢复后的账户浏览器矩阵与 Approval 夹具再验收。

最终 fetch 时主线合并 #308，rebase 到 `c2106969`。经 git tree 比较，`0fddf100:plugins` 与 `c2106969:plugins` 完全相同；新增内容只有部署 OPcache 重置及其测试/规格，因此上述纯 main 网站插件对照仍适用于最终基线。
