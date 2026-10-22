# 导航图片加载与键盘展开

状态：本地实现、完整静态检查、相关单元测试和固定 660fe136 的双轴源码评审完成；原生重新编译后已实走英德桌面键盘、鼠标和手机抽屉。手机抽屉检查新发现的联系按钮宽度缺陷已修复并原生读回。最终范围评审、完整视觉门、CI 与线上验收仍待完成，不代表全站性能交付。

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
- 实际手机截图另发现抽屉联系按钮的 content-box 将 padding 和 border 加在 100% 宽度之外。仅对 `.tv-mobile-cta` 使用 border-box，保留现有颜色、文案与去向；修复抽屉本身的横向溢出，保留方案卡片原生横向滚动。

## 备份、安装与读回

本地改动前原生数据库快照：`/Users/chesterjohn/de-linker-data/snapshots/db-20261022T105056Z.sql.gz`，6,552,395 字节，SHA 前缀 bbdb5c8b96cd23b2。首次原生 present 只更新两个 header partial、其他 18 个模板不变，完成样式卷安装后按预期被旧缓存门拦下；未使用 allow-stale 绕过。

随后在本地 WindPress 原生界面 Generate，界面显示站点时间 19:02:00；原生缓存 709,814 字节，SHA `bf7e70470f8f80bd2da20ddaaf639af4792b30a9626ea7595e0910c9e2746c6c`。样式卷 chrome.css 与源码逐字节相同，编译 CSS 中闭合/展开 display 规则均存在。重新 present 成功且幂等。读取编译 CSS 时曾误用 minified 字符串匹配，错误诊断保留；修正格式匹配后确认真实缓存有效，没有通过修改输出凑校验。

编译使用本地管理员界面。之后已通过 WordPress 原生 Log Out 恢复匿名，再重新设置相同网络条件，才开始 AFTER。需确认角色、可见界面及匿名状态没有影响比较；保留这一操作间隔，不能宣称整个过程无会话操作。

## 完成条件

原始事件中关闭菜单不再启动菜单图片请求；展开时实际照片完整出现且所有链接与键盘/鼠标/触摸动作正常；EN/DE 与 1440/390 均留证。实际前后 FCP、load 和图片请求分别报告，不以节省的字节换算生产提速百分比。关闭视图和打开视图的几何、字体、颜色与布局需要独立视觉审查；回归 account 菜单和响应式收纳。

证据根：`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/menu-image-loading-20261022T1053Z/`。冻结六份源码/测试 aggregate `ab2ed107c92478401c7afe165f9be8c626ca9c1d4fa886783c16c27a652fc793`。本批不改变 WindPress 预设开关、隐私正文、营销文案、模型或通知逻辑。本地验证阶段尚未写入生产。

## 原生消费者与新增缺陷读回

最终 660fe136 在原生 present 时被旧缓存门正确拦住；WindPress 官方 Generate 后于 11:37:10 UTC 落盘，709,814 字节，SHA 与原实验缓存一致，原生 present 再次成功。其后均明确原生退出管理员，匿名再验证。

`final-660-runtime/` 保存英德 1440 的六个披露菜单与账户菜单首次 ArrowDown、后续方向键、Home/End、Escape、首次 ArrowUp 和快速 next/Escape 的实际焦点与 expanded 状态。产品和方案菜单的七张照片实际 complete/naturalWidth>0，其他关闭菜单不提前加载。鼠标真实 pointerenter/pointerleave、按钮点击和真正位于菜单之外的点击另留证。EN 的早期“outside-close”记录实际点中了覆盖标题的方案链接，已按最终 URL 判为驱动目标错误，不能作为外部关闭 PASS。

英德 390 五组原生 details 均实际展开/收起、照片完整出现，Escape 返回菜单按钮。新增 CTA 缺陷修复前 panel client=343、scroll=377，按钮宽377且右端393超过 panel 右端359；修复后英德 panel client=scroll=343，按钮宽343、44高、右端359。内部方案 rail 仍为 client343/scroll440，可真实横向滚至97，最后卡片完整落入视口并进入 `/solution/utility-storage/`。11:46:44 UTC 的原生缓存编译与 present 均完成。没有通过隐藏 panel overflow 来掩盖缺陷。

IAB 不支持 Input.dispatchTouchEvent；该尝试明确失败，已立即恢复 touch emulation=false，不能把鼠标点击当作真实触屏硬件验证。响应式额外发现：在已加载字体的 1366 视口，EN 保留桌面导航、DE 进入折叠菜单；这项英德收纳差异需要继续查明。不得把额外宽度检查写为 parity PASS。

24 次关闭菜单性能原始采样由独立 Spec 重算：12 次 AFTER 的 requestWillBeSent 也为零，并非只没有响应。局部 FCP 中位数减少45.6–47.3%，load减少42.1–49.8%。这些数字仅绑定原始本地六文件 aggregate，不将后来 CTA 盒模型修复、更新后的后端、生产或完整用户链路混进同一百分比。三组关闭截图完全一致；EN1440 仍有33像素差异，位于账户图标头部附近，最大通道差4，未证明成因，不能掩膜或签像素零差异。
