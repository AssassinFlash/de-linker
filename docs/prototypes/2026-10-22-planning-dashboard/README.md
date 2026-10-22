# 统一方案工作台：待用户评审的界面原型

这是回答“统一后的 Solution Configurator / 屋顶设计应当长什么样、怎样操作”的可点击原型。A版信息结构已获用户明确确认；用户进一步要求毛玻璃、少圆框与符合站点设计系统的按钮、字体和配色，已按该方向细化。原型不作为已实现功能或生产准确度的证明。

## 打开与运行

在本工作树根目录执行：

~~~sh
python3 docs/prototypes/2026-10-22-planning-dashboard/preview.py
~~~

仅监听 127.0.0.1:8794。端口被占用时可加 --port 8795，不终止其他会话的进程。

- 主版：[A · Journal 工作台](http://127.0.0.1:8794/solution-configurator/?variant=A&lang=zh)。
- [B · 画布优先](http://127.0.0.1:8794/solution-configurator/?variant=B&lang=zh&workspace=roof)。
- [C · 分步引导](http://127.0.0.1:8794/solution-configurator/?variant=C&lang=zh&workspace=roof)。
- lang=en / lang=de 可看完整英德界面；中文仅为本轮设计评审辅助。
- 底部浮动栏可切 A/B/C；左右方向键也可切换，在输入框、选择框或弹窗内不拦截方向键。

三个版本是同一项目的结构比较。A 保留 Journal 的完整左导航、中间工作区、右侧上下文；B 将屋顶画布置于主位、收窄导航并把输入嵌在画布旁；C 用横向步骤与当步说明组织首次操作。切布局、工作区与语言都保留当前示例项目。

## 建议试用路径

1. 打开 A，先看概览中的输出预期、屋顶示意与缺项。
2. 进入“屋顶与排布”，输入尺寸并应用；支持逗号小数，非法值显示校验并保留原值。点击组件可排除/恢复，也可键盘 Enter/Space 操作；撤销、平面/立体视图及天窗示例均可用。
3. “用能与目标”可独立选择国家、年用电量与目标；合成负荷曲线只是图表演示。
4. “设备与方案”比较 PV 与 PV+storage 两种构成。具体型号与适配保持开放。
5. 生成报告后再改一次屋顶。旧报告保留原数量并显示待更新，不能将过时结果带入新交接；可以生成下一版并切回旧版。
6. 将当前报告带入 Solution draft、预览询盘并“模拟提交”。交接内容保留同一报告版本、物料、缺项、联系人、公司与留言，无真实提交。
7. 保存后修改并恢复；点 Genie 看它引用当前选中的报告；点“看站点入口”体验首页/产品页进入同一项目的关系。

## 原型边界

所有项目、保存、报告、聊天和询盘记录只在页面内存，刷新会清空。服务器仅提供固定文件，无 API、目录列表或写入入口；CSP 禁止网络连接和原生表单提交。没有 WordPress、WooCommerce、真实账户、Genie、邮件、支付或工程服务连接。

已执行的算术仅限矩形网格示例及保留组件数量 × 460 Wp。固定 2.00 × 1.15 m 组件、1 m 边距、0.22/0.50 m 网格间隙、中央通道及天窗都是原型常量，**没有规范依据**，不能代表商业平屋顶精度、支架、结构或工程设计。方向按钮仅切示意，不计算倾角、遮挡或荷载。

年发电量、自给率、自用比例、储能调度、SOC、组串校验、设备兼容、结构及并网放行均未实现，保持“尚未计算/待核验”。国家下拉验证国家与界面语言分离，包含英国、瑞士、挪威等非欧盟国家；它不是逐国支持认证，也不是最终欧洲范围清单。真实地点、地图描绘、多屋面、已有PV/纯储能输入、真实设备与厂家规则仍属于正式实现范围。

报告可以实际导出独立 HTML 示例，未冒称 PDF。Genie 为固定脚本。产品入口只记录来源枚举，没有导入实际型号。入口卡片预览导流位置与上下文，原站页面没有修改。

## 站点与设计来源

- 使用既有 /solution-configurator/ 路由形状；德语也可在 /de/loesungskonfigurator/?lang=de 打开。
- 这是独立静态工具原型，未接管 WordPress 路由。它以真实品牌/Journal外观承载新的项目状态，不充当本地 WordPress 快照实例，不作营销/商务页像素一致性验收。
- 真实 Journal：[桌面截图](../../acceptance/2026-10-18/254/current/journal-en-1440.png)、[手机截图](../../acceptance/2026-10-18/254/current/journal-en-390.png)、[模板](../../../plugins/linker-commerce/content/livecanvas/blog_index.html)、[样式](../../../plugins/linker-commerce/content/windpress/journal.css)。
- Logo 从本机既有站点快照 de-linker-local/r549/wordpress/wp-content/uploads/2026/07/de-linker-logo-1.webp 复制；字体从本仓库 plugins/linker-commerce/assets/fonts/ 复制，OFL 许可在 assets/plusjakartasans-OFL.txt。
- 屋顶为本原型生成的 SVG，没有集成 Aladdin 的渲染、项目或仿真。
- 依据：[统一工作台决定](https://github.com/AssassinFlash/de-linker/blob/e1bfc71801e2a4a6f89fb95a5141264f348dd068/docs/research/2026-10-22-roof-system-rebuild/PRODUCT-STRUCTURE.md)、[整体架构](https://github.com/AssassinFlash/de-linker/blob/e1bfc71801e2a4a6f89fb95a5141264f348dd068/docs/research/2026-10-22-roof-system-rebuild/ARCHITECTURE.md)、[全站同步修复](https://github.com/AssassinFlash/de-linker/blob/e1bfc71801e2a4a6f89fb95a5141264f348dd068/docs/research/2026-10-22-roof-system-rebuild/SITE-IMPACT.md)。

## 评审与后续

[原型票](https://github.com/AssassinFlash/de-linker/issues/553)将记录用户对A版的明确确认。没有实施PR、合并或部署。相邻 2026-10-22-roof-system/ 的旧流程原型没有覆盖。

- [A版确认后的材质、按钮与设计系统细化](VISUAL-REFINEMENT.md)。
- [初稿、对抗意见与定稿复核](COPY-REVIEW.md)。
- [操作与截图证据](EVIDENCE.md)。

用户已确认 A 为主版，并授权从头到尾实施；B/C保留为结构比较。正式实现须重写项目/计算/报告合同并同步修复全站消费者。原型按抛弃约束编写，不直接晋升生产。
