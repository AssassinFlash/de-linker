# 直接使用真实软件

本包用于研究屋顶规划和系统选型，不包含本站工具的生产实现。所有样例是软件厂商/开源项目的公开例子及本轮对它们的实际操作，没有客户项目数据。

## 先打开软件

无需注册的 Aladdin：
https://institute-for-future-intelligence.github.io/aladdin/

本轮已经在它的在线 2.0.7 应用中完成 584 片组件的三维车库屋顶示例、两种采样设置的年发电分析、CSV 与原生项目保存。

1. 点左上角 Main Menu → File → Open Local File。
2. 选择 `runtime/artifacts/linker-study-aladdin-garage-12-days.ala`。
3. 点 Main Menu → Analysis → Solar Panel → Analyze Yearly Yield。
4. Energy Analysis Options 可以查看 Days per Year、Times per Hour、Panel Discretization 和 Grid Cell Size。
5. 结果图右下的保存按钮导出 CSV；File → Save as Local File 保存整个三维项目。登录用于别的功能，上述本地流程本轮没有要求账号。

如果浏览器访问失败，不代表本包有本地可直接双击启动的桌面程序。`source/` 中是完整源码压缩包，需要常规开发环境构建；本轮没有安装依赖或执行构建。在线服务与取得的源码版本不同，见下文。

## 看什么文件

- `runtime/artifacts/*.ala`：两份实际导出的可编辑三维项目。
- `runtime/artifacts/*.csv`：分别为 4 个、12 个代表日方案的月量数据。
- `runtime/screens/aladdin-yearly-result-12-days.jpg`：真实软件的三维和结果截图。
- `runtime/runtime-comparison.json`：导出文件与界面总量的计算核查。
- `source/aladdin-7b939ab115ca6d78bafc274b07e0bd9cbb5b36aa.zip`：完整源码，25,329,681 bytes；源码 UI 常量版本 2.0.6。实际操作线上版本为 2.0.7，不能说同版复建已通过。
- `source/aladdin-LICENSE.txt`：MIT 许可原文。源代码使用/修改/分发须保留许可与版权声明；本包不代替逐项资产/三方许可清点。
- `source/examples/`：官方公开原生例子，来自固定源码；没有在本轮逐一导入运行。其 `.ala` 是相同 JSON 字节的原生扩展名副本。
- `references/official-resources.md`：Trace、K2 官方资料入口，以及本轮已取得原件的研究包链接；参考资料不是我们新生成的工程报告。
- `RESEARCH.md`：本轮结论与直接来源。

## 对数值的理解

4 代表日显示年量 282,262.24 kWh；12 代表日为 281,869.30 kWh。两次地点、三维几何和其他 world 设置相同。差异约 -0.1392% 是采样敏感性，不是相对于真实发电量的误差。两次都不是 365 天逐小时计算。示例在 Atlanta，不能代替欧洲现场、本站真实设备、光储联合、结构或并网校核。

PV*SOL online：
https://pvsol-online.valentin-software.com/#/

本轮匿名输入了 92 片 Trina 460 W 组件与商业负荷练习参数，成功求得逆变器/组串配置；年模拟停在验证码前，没有年发电结果。Trace archelios 真实设计器仍需要账号，本轮未注册。

## 文件校验

`bundle-manifest.json` 列出本压缩包内其他文件的原始字节数和 SHA256；源码 ZIP 的 SHA256 是：
`1441ac0f978a12d2930d390e22c195b338f35cb64bb8005e3aacd6f437bfb40a`

源码官方仓库：https://github.com/Institute-for-Future-Intelligence/aladdin
机构说明：https://intofuture.org/aladdin.html
取证日期：2026-10-22。
