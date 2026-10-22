# #538：Hostinger / CloudLinux Alt-PHP 回补与部署确认

日期与读取时间：2026-10-22 07:11–07:14 UTC。关联任务：[PHP 运行环境修补 #538](https://github.com/AssassinFlash/de-linker/issues/538)。这是对本目录既有 DOSSIER 的新增证据，未改写既有报告，也未进行生产、账号、软件包或配置写入。

## 结论

**发现正面的官方回补与部署证据，不能因为 `/opt/alt/php83` 显示 8.3.35 就判定仍有漏洞。** CloudLinux 明确说明两项 CVE 通过安全回补修复，包内上游版本号可能仍较低；Hostinger 随后明确宣布其所有 managed hosting 服务器已经完成 PHP 升级。以下结论须与主调查确认的实际托管账号、主机和 Web SAPI 关联，不能拿来证明另一台 VPS 或任意安装已经修补。

| 判断层次 | 本次证据 | 可下的结论 |
| --- | --- | --- |
| 供应商是否提供固定版本 | CloudLinux 官方公告与状态事件，均明确两项 CVE、Alt-PHP 回补与 stable 发布 | **是，已提供**；不必为了显示上游固定版本号盲目跨分支 |
| Hostinger managed fleet 是否完成部署 | Hostinger 专属状态事件于 22 日 06:44 UTC 明确宣布所有 managed hosting 服务器完成 PHP 升级 | **供应商已宣布完成**，范围与站点托管归属应匹配 |
| 本机是否独立核对到已安装 RPM 的 CVE changelog/构建号 | 本子任务没有生产权限操作；主调查报告 CageFS 不提供 rpm | **没有独立包级证明**，不能声称亲眼核对了该包的两个 CVE |
| 实际承载网站的 worker 是否使用对应构建 | 由主调查 Web SAPI 读回负责 | CLI 版本和文件 mtime 不足，需实际 Web 路由/运行环境关联 |
| 当前表单攻击是否利用这些 CVE | 官方公告不提供本站事件归因 | **不能据此归因**，继续分别调查 |

## 1. CloudLinux：低版本号确实可以已修补

CloudLinux 官方公告的当前版本标注最后更新 **2026-10-22 06:00 UTC**。它明确说明：Alt-PHP、ea-php 及 CloudLinux native PHP 的两项修补以 backport 方式提供，会保留低于 PHP 上游修补版的版本号；要求以软件包 changelog 中的 `CVE-2026-109618` 和 `CVE-2026-109619` 确认，而非只比较 `php -v`。[CloudLinux 公告](https://blog.cloudlinux.com/php-cve-2026-109618-and-cve-2026-109619#step-3-update-cloudlinux-php-packages)

官方状态事件还给出了 **ea-php** 已修补完整包号示例，包括 `ea-php83: 8.3.35-2.elX.cloudlinux.2`、`ea-php84: 8.4.26-2.elX.cloudlinux.1`。这直接说明 8.3.35、8.4.26 可以存在已回补构建；**这些是 ea-php 标识，不是 `/opt/alt` Alt-PHP 的安装包标识，不能跨产品套用。**[CloudLinux 状态事件，21 日 20:55 UTC](https://cloudlinux.statuspage.io/incidents/zl0vt1yq3dj5)

Alt-PHP 的当前发行范围：CloudLinux 7、8、9 的 5.2–5.6、7.0–7.4、8.0–8.5 已进入 stable；CloudLinux for Ubuntu 22.04 的 5.2、5.6、7.0–7.4、8.0–8.5 亦已在 stable；CloudLinux 10 有自身仓库与 ELS 仓库划分；CloudLinux 6 尚未确认。**安装来源和发行版必须分清。**[CloudLinux 公告](https://blog.cloudlinux.com/php-cve-2026-109618-and-cve-2026-109619)、[发布状态](https://cloudlinux.statuspage.io/incidents/zl0vt1yq3dj5)

CloudLinux 同时指出当时 OVAL/UpdateInfo 安全公告元数据尚未发布，`yum --security` 等“只装安全更新”的过滤可能不会列出这些包。对有 root 权限的自管相应系统，应按供应商针对该包来源的正常更新方法处理并重启 Apache/FPM/LiteSpeed；此建议不授权在 Hostinger CageFS 内装仓库或盲目执行系统升级。[CloudLinux 确认方法](https://blog.cloudlinux.com/php-cve-2026-109618-and-cve-2026-109619#step-3-update-cloudlinux-php-packages)

**公告发生过更正，不能引用早期搜索摘要作结论。** 21 日 19:00 UTC 的初始 Alt-PHP 发布说法，在 21:45 UTC 被更正为首先进入 TuxCare ELS 仓库。状态事件在 22 日 01:19 UTC 进一步说明 CloudLinux OS stable 的完整发布实际完成时间为 **22 日 00:07 UTC**；博客在 01:25 UTC 汇总为已进入 stable。[状态事件的更正与更新](https://cloudlinux.statuspage.io/incidents/zl0vt1yq3dj5)

## 2. Hostinger：其 managed hosting 已有明确完成公告

Hostinger 的第一方说明将 managed hosting 和 VPS 分开：除 VPS 外由 Hostinger 管理 PHP、自动部署修补；VPS 中由客户自己安装和维护的 PHP 需自行升级并重启。它说明部署了已知攻击模式的防火墙规则、关闭特定 upload-progress 路径并安装 PHP 修补；同时明确防火墙只覆盖已知形态，PHP 更新才修复根因。[Hostinger 工程说明](https://www.hostinger.com/blog/protecting-php2shell/)

它链接的专属状态事件提供了较博客“正在推出”文字更新、更具体的部署状态：

| 官方事件时间（UTC） | 发布内容的含义 |
| --- | --- |
| 21 日 17:44 | 识别两项 CVE，实施附加防护并开始部署修补 PHP |
| 21 日 19:12 | Agency infrastructure 已完成；其他 managed hosting 继续升级 |
| 22 日 03:34 | cPanel 服务器已更新到含修补的 cPanel build 138.18 及最新 Alt-PHP |
| **22 日 06:44** | **明确宣布所有 managed hosting 服务器的 PHP 升级已完成，进入 Monitoring** |

以上均来自 [Hostinger：PHP Security Update Across Managed Hosting Plans](https://statuspage.hostinger.com/incidents/pj2zs1lx3n9d)，于本子任务 07:13 UTC 经 Apify 抓取。应保留这份带时间的供应商完成声明，而不是只引用较早的“供应商承诺会提供”。

对确属该 managed fleet 的站点，可准确报告为：**“供应商已公告部署完成；本站运行环境已关联/读回；独立 RPM changelog 是否可见另行说明。”** 不应报告“仍旧 8.3.35 所以肯定未修”，也不应把这称为对本站二进制实施了独立安全审计。

## 3. 对主调查已读到信息的解释边界

主调查报告（非本子任务重新读取）：`/opt/alt/php83` 为 8.3.35，82/84/85 分别为 8.2.34、8.4.26、8.5.11；多个版本文件在 21 日重建。PHP83 mtime `1792620608` 对应 **21 日 22:10:08 UTC**，PHP84 `1792621488` 对应 **22:24:48 UTC**。

这些信息与“供应商在原有版本上回补”相容，但 **mtime 不等于编译时间、安装时间或 changelog**，也不能从早于 stable 发布时间反推一定未修补。构建可以先于发布；同一上游版本也可有多个不同 release。仅凭时间戳无法区分。

hPanel 仅提供 8.2/8.3/8.4/8.5 分支选择而不提供 patch selector 时，切到另一分支不能作为修补的证据。应优先保留现有兼容 8.3，关联供应商完成公告与实际 Web SAPI；如需更强包级证据，由 Hostinger 提供当前主机 `alt-php83` 对应包的完整 version-release/构建标识、两个 CVE 的 changelog 记录和 worker 重启情况。**不要借助公开 `phpinfo()` 页面泄露全量配置，不执行漏洞利用请求“验补丁”。**

可以要求供应商确认的具体字段：域名对应服务器与 managed 产品范围；Web SAPI 与实际包来源；Alt-PHP 包完整 release/build ID；该构建是否包含两个 CVE 的修补；部署与所有相关 worker 切换完成时间。只回答“有 WAF”或“显示 PHP 8.3”不能替代以上范围说明。

本报告未取得 Alt-PHP83 的精确固定 EVR 清单或本站 package changelog；该边界保持显性。官方源已足以确认“存在保留旧上游号的修补包”和“Hostinger 宣布其 managed fleet 部署完成”，但不能伪造独立二进制验证。

## 4. 来源与抓取记录

所有外部搜索与页面读取均经 Apify；没有使用邮件追踪链接、第三方博客或漏洞利用代码。公开原始结果位于本机 `/tmp/incident-defense-vendor-538/`，不含本站凭证和客户内容。

| Actor run / dataset | 范围与结果 |
| --- | --- |
| `2q1qEdWIK2eu0bMgt` / `0iEvJdCyKAD09DGRo` | google-search-scraper：CloudLinux/Hostinger 的两个精确 CVE、Alt-PHP 发行发现；摘要不作最终结论 |
| `EKtuoy6m9OpbUyyfh` / `yIPz4uoUA4J0yZRjj` | website-content-crawler：CloudLinux blog 与 docs；旧 hardened_php 路径 404，未用于结论 |
| `xeOUVShgA2DL5G7Xq` / `XfKbKchhqKgAVooj1` | 两家供应商精确公告和 Hostinger 状态首页；3 HTTP 200，全文已核对 |
| `V9rNKqJqogquV5W1q` / `LnaylWT47j42j9yg7` | 两个精确 incident 页面；2 HTTP 200；确认 06:44 managed hosting 完成声明与 CloudLinux 回补/发布时间/更正记录 |

本子任务未更新生产、切换 PHP 分支、发送测试邮件或创建支持会话。文档与凭证扫描是本次唯一仓库验证；运行时修补结论由 #538 的现场读回及上述供应商证据共同形成。
