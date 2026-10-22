# 导航图片加载与键盘展开

状态：本地实现和相关单元测试完成；浏览器优化后、原生消费者、双评审、CI 与线上验收待完成。不代表全站性能交付。

## 问题与依据

实际初始请求追踪显示，隐私正文页面仍会请求关闭导航中的大图。原始 partial 的桌面七张图虽然使用 native lazy，关闭面板仍以 visibility/opacity 隐藏并参与布局；手机抽屉五张图没有 lazy 属性，即使抽屉 display:none 也开始加载。logo 正常 eager。

隔离本地 9290、匿名 IAB 同一上下文，EN/DE 隐私页 × 1440/390 × 三轮，共 12 次原始基线：桌面每轮 7 个菜单图片响应、1,998,117 字节完成传输；手机每轮 5 个、1,623,441 字节。使用自定义 100 ms 延迟、512 KiB/s 下载、256 KiB/s 上传及禁用缓存，场景只用于可重复诊断，不称为客户真实 4G 或生产结果。

最初限速采样因为 dataReceived 事件多于缓存容量，主 Document 事件被淘汰，已拒绝计入。修正为导航期间持续读取原始事件，完整保留每次原始 loader/frame、生命周期和完成信息；不能用丢失的事件计算收益。

## 实现约束

- 每个图片保留真实、站内绝对 src 和原来的照片、alt、链接、版式；不用 data-src、手工图片注入、隐藏内容删除或新加载框架。
- 十二张菜单图都使用浏览器 native lazy/async；可见品牌 logo 继续 eager/async。
- WindPress 的关闭 mega panel 为 display:none，aria-expanded=true 时 display:block。现有脚本继续决定展开状态，桌面布局、尺寸、颜色和点击去向保留；本次明确让关闭面板不再生成布局盒子，首次展开即时显示。
- 首次方向键展开后直接聚焦对应链接。去掉原先等待 visibility transition/250 ms 回调的路径，避免旧回调覆盖后续键盘选择；继续验证上下方向、Home/End、Escape 返回触发器、鼠标、外部点击与手机抽屉原生 details。
- 风格属于 LC partial 与 WindPress，披露状态属于现有 header-menu.js；没有 PHP 布局、Snippet 或第三方图片工具。

## 备份、安装与读回

本地改动前原生数据库快照：`/Users/chesterjohn/de-linker-data/snapshots/db-20261022T105056Z.sql.gz`，6,552,395 字节，SHA 前缀 bbdb5c8b96cd23b2。首次原生 present 只更新两个 header partial、其他 18 个模板不变，完成样式卷安装后按预期被旧缓存门拦下；未使用 allow-stale 绕过。

随后在本地 WindPress 原生界面 Generate，界面显示站点时间 19:02:00；原生缓存 709,814 字节，SHA `bf7e70470f8f80bd2da20ddaaf639af4792b30a9626ea7595e0910c9e2746c6c`。样式卷 chrome.css 与源码逐字节相同，编译 CSS 中闭合/展开 display 规则均存在。重新 present 成功且幂等。读取编译 CSS 时曾误用 minified 字符串匹配，错误诊断保留；修正格式匹配后确认真实缓存有效，没有通过修改输出凑校验。

编译使用本地管理员界面。之后已通过 WordPress 原生 Log Out 恢复匿名，再重新设置相同网络条件，才开始 AFTER。需确认角色、可见界面及匿名状态没有影响比较；保留这一操作间隔，不能宣称整个过程无会话操作。

## 完成条件

原始事件中关闭菜单不再启动菜单图片请求；展开时实际照片完整出现且所有链接与键盘/鼠标/触摸动作正常；EN/DE 与 1440/390 均留证。实际前后 FCP、load 和图片请求分别报告，不以节省的字节换算生产提速百分比。关闭视图和打开视图的几何、字体、颜色与布局需要独立视觉审查；回归 account 菜单和响应式收纳。

证据根：`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/menu-image-loading-20261022T1053Z/`。冻结六份源码/测试 aggregate `ab2ed107c92478401c7afe165f9be8c626ca9c1d4fa886783c16c27a652fc793`。本批不改变 WindPress 预设开关、隐私正文、营销文案、模型或通知逻辑。本地验证阶段尚未写入生产。
