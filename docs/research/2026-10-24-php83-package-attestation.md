# #538：PHP 8.3.35 的供应商修补确认与包级核验边界

研究日期：2026-10-24（Asia/Shanghai）；官方页面抓取于 **2026-10-23 16:04–16:07 UTC**。这是对既有 `5268d99c:docs/research/2026-10-22-incident-defense/RUNTIME-538.md` 的增量核实，只回答 Hostinger managed hosting 上 `/opt/alt/php83` 的修补确认问题。没有操作生产、安装软件包、切换 PHP 分支、重启、发送邮件或联系支持。

## 结论与建议

**在原有 managed hosting 全量部署公告及本站安全修复横幅之外，本轮取得了供应商定义的具体确认方法，并与本站 Build Date 对应。** 当前工程说明和状态事件均规定：在 hPanel 的站点 Dashboard 打开 PHP Info，**Build Date 为 2026-10-21 或之后，即表示该托管站点包含本次修复**。本站保留的同一路径原生读回正是 `Build Date Oct 21 2026 00:00:00`；正确账号下 de-linker.com 的 Business Web Hosting 后台另有“已应用安全修复，无需操作”的声明。两者构成供应商定义的方法与本站结果的对应，强于只比较 PHP 上游版本号。[Hostinger 工程说明](https://www.hostinger.com/blog/protecting-php2shell/)、[Hostinger 状态事件，22 日 06:44 UTC 更新](https://statuspage.hostinger.com/incidents/pj2zs1lx3n9d)

**建议保留兼容的 PHP 8.3 分支，完成主调查已有的实际 WordPress LiteSpeed 运行环境关联后，将原两项 CVE 记为“按供应商官方方法确认修补”。** 精确安装包 NEVRA、changelog 及 ELF 标识的独立对应仍未取得，应继续明确保留这一证据边界；不应为满足上游版本号显示而盲目切换分支，也不应把独立二进制逆向审计增加为原票的必需工作。

| 问题 | 本次实际证据 | 可下结论 |
| --- | --- | --- |
| 是否确有保留 8.3.35 等旧上游号的修补构建？ | CloudLinux 当前公告继续说明 backport；早期固定包受保护，无须为新版本号再次采取紧急措施 | **有**；`8.3.35` 单独不足以判定未修补 |
| Alt-PHP83 是否已有与 PHP 上游号一致的版本？ | CloudLinux blog 与状态页明确公布 `alt-php83 8.3.36-1` 已进 stable | **有**；这是公开发行版本，不是本站已安装包的证明 |
| 本站是否符合 Hostinger 自己公布的确认方法？ | hPanel PHP Info 的 Oct 21 Build Date；对应站点的安全修复通知 | **符合**，属于可复核的供应商确认 |
| 已知 CLI/LSAPI 二进制 SHA、GNU Build ID 能否独立对应到固定包？ | 两个实际文件标识已知；CageFS 不暴露包查询工具/RPMDB；本次已读取官方页未提供匹配表 | **尚不能**；未伪造安装 EVR、包 changelog 或独立二进制确认 |
| 是否证明正在承载 WordPress 的进程加载了相同文件？ | 供应商 CGI/FastCGI helper 和主调查补充的已安装 LSAPI 子进程诊断均符合日期条件 | **本报告单独不能**；诊断不等同于已服务的 WordPress 请求，实际 Site Health/LiteSpeed 和 worker 关联由主调查的原生证据承担 |

上述 CloudLinux 发布结论来自其[当前公告的确认方法](https://blog.cloudlinux.com/php-cve-2026-109618-and-cve-2026-109619#step-3-update-cloudlinux-php-packages)与[状态历史](https://cloudlinux.statuspage.io/incidents/zl0vt1yq3dj5)。没有用 ea-php 的固定包号替代 Alt-PHP 的包号。

## 1. 与 22 日研究相比新增的官方证据

CloudLinux 公告自报最后更新 **23 日 08:40 UTC**。它现在明确列出 Alt-PHP83 的 `8.3.36-1`，并说明此前固定包已含同样的修复；这次发行使显示版本与 PHP.net 一致。状态页的 **23 日 00:08 UTC** 更新确认 CloudLinux 8/9 stable，**13:10 UTC** 更新又补充 CloudLinux 7。公开说明只给 version-release，未在该段给出本站相关包的完整 epoch、发行版后缀、架构或二进制校验值，故本报告不把它写成完整安装 NEVRA。[CloudLinux 公告](https://blog.cloudlinux.com/php-cve-2026-109618-and-cve-2026-109619)、[CloudLinux 状态事件](https://cloudlinux.statuspage.io/incidents/zl0vt1yq3dj5)

Hostinger 工程说明当前包含 **23 日 13:25 UTC** 更新，原两项 CVE 的修补段则给出了上述 PHP Info Build Date 确认方法。其状态页 **22 日 06:44 UTC** 的现存文字也包含该方法。**这是本次读取时该历史更新的当前内容，不声称该方法在 22 日首次发布时已经存在。** 本次没有依赖旧搜索摘要或旧抓取替代当前原文。[Hostinger 工程说明](https://www.hostinger.com/blog/protecting-php2shell/)、[Hostinger 状态事件](https://statuspage.hostinger.com/incidents/pj2zs1lx3n9d)

## 2. 本站原生证据与准确的证明范围

读取了主调查现有的四份原生材料，没有由本子任务重新访问主机：

- `/Users/chesterjohn/de-linker-data/incident-20261022/hosting-logs/php-security-correct-account-20261023.dom.txt`：站点选择器、面包屑及正文均对应 de-linker.com；套餐为 Business Web Hosting；安全通知明确表示本站 PHP 修复已应用。
- `/Users/chesterjohn/de-linker-data/incident-20261022/hosting-logs/php-info-helper-20261023.json`：23 日 11:12:58 UTC 的供应商原生 PHP Info；Build Date 为 Oct 21；版本 8.3.35，配置在 `/opt/alt/php83`，构建系统属 CloudLinux el9；`session.upload_progress.enabled` 的 Local/Master 均 Off。**该证据自述 CGI/FastCGI helper，不能改称实际 WordPress LiteSpeed worker。**
- `/Users/chesterjohn/de-linker-data/incident-20261022/hosting-logs/package-metadata-20261023T155653Z.json`：23 日 15:56:53 UTC 的只读文件身份/包元数据可见性。`rpm`、`rpmquery`、`dpkg-query` 不可用；四个已测试 RPMDB 路径不可见。结论限于已测试路径，不能据此断言物理主机上没有包数据库。
- `/Users/chesterjohn/de-linker-data/incident-20261022/hosting-logs/native-lsapi-selected-info-20261023T160840Z.json`：主调查补充的 23 日 16:08:40 UTC 只读 `lsphp -i`。已安装 LSAPI 文件 SHA 与上表完全相同，Build Date 为 Oct 21，Server API 为 `lsapi V8.3 CloudLinux 1.3`，配置与扫描目录同上；`session.upload_progress.enabled`、`session.auto_start` 均 Off/Off。站点根目录 `.user.ini`、`php.ini` 不存在，当前 `.htaccess` 无 upload-progress 指令，SHA 保持已核实值。**这是更接近本站 SAPI 的已安装 LSAPI 子进程诊断，仍不是一个实际已服务的 WordPress 请求。**

已记录的文件身份如下；**这些标识确认所检查的是哪些文件，不自行证明它们包含某项安全补丁**：

| 路径 | SHA-256 | GNU Build ID |
| --- | --- | --- |
| `/opt/alt/php83/usr/bin/php` | `5e0c2aadd20a731a03641e14e4517ac4a0c017087d5f1c8909b6ddab982f2511` | `605058436566e28ad84dbd7c9e2af993674b2bc4` |
| `/opt/alt/php83/usr/bin/lsphp` | `8f4575fb1585f9ac9909f10ee680f191ba02fabf48f537049e7a40f56db55f13` | `0570191f464ddde5b13c24ffb6d46499af12279e` |

两个文件的 mtime 均为 `1792620608`。mtime 与 PHP 编译内嵌的 Build Date 含义不同；本报告使用的是 **Hostinger 明确规定的 PHP Info Build Date 方法**，没有把 mtime 冒充安装时间或修补 changelog。

## 3. 精确包映射做到了哪里、在哪里停止

当前 CloudLinux 指导仍以已安装包的 changelog 查询为 backport 确认途径。实际捕获的官方 incident 页没有给出上述两个 SHA/GNU Build ID 对应的包、文件清单或 ELF 标识关联。此次检索还发现官方 [`alt-php83` changelog](https://changelog.cloudlinux.com/alt-php83) 页面；已分别取得静态页面和浏览器渲染页面，但静态抓取只有应用标题，渲染后的正文提取只返回一个无关的 `DEF-49472` 条目，未返回可用于本问题的包下载/校验值关联。**不能由提取不全推断官方页面不存在 CVE 条目。搜索结果中的额外旧版本 release 号没有经正文确认，因此未作为固定包证据。**

截至本次有界读取，准确表述是：**未取得本站二进制到已修补 RPM 的独立匹配；已取得供应商明确的方法与本站符合该方法的结果。** 没有下载 RPM、遍历仓库、反汇编、发漏洞请求或安装包查询工具。

若将来需要进一步包级签认，只需让主机方针对本站承载服务器提供这些字段，无需重新调查整个漏洞：

1. 上述两个路径各自所属软件包的完整 name、epoch、version、release、arch，以及仓库/构建来源；不能用 ea-php 的包号代答。
2. 同一安装构建包含 `CVE-2026-109618`、`CVE-2026-109619` 修补的 changelog 或供应商签认，并将记录与两个 SHA/Build ID 对应。
3. 实际 WordPress LSAPI 的生效构建与 worker 切换时间；不能只提供 CLI 版本。

这些是进一步签认所需字段，**本子任务没有提交支持请求，也不把供应商回复列为已经取得的证据。**

## 4. 新增的 CVE-2026-115560 与原两项分开记录

Hostinger 在 **23 日 13:25 UTC** 工程更新与 **12:53 UTC** 状态更新中又提到 `CVE-2026-115560`。它表示 managed hosting 已由 21 日实施的措施保护，PHP 未来常规版本会包含修复；对自行维护 PHP 的 VPS，其具体措施是在请求解析前生效的 `php.ini` 或 PHP-FPM pool 配置中关闭 `session.upload_progress.enabled` 并重启全部 PHP worker。不能依赖请求进入后执行的 `ini_set()`。[Hostinger 工程说明及其链接的 PHP 公告](https://www.hostinger.com/blog/protecting-php2shell/)、[Hostinger 23 日状态更新](https://statuspage.hostinger.com/incidents/pj2zs1lx3n9d)

这是**供应商对新增漏洞的保护声明和配置条件**，不等同于已有第三项 CVE 的新二进制修补已经安装，也不能倒推仅关闭 upload progress 就完整修复了原两项漏洞。helper 与补充的已安装 LSAPI 诊断均为 Off/Off，且已检查站点根目录覆盖项；这些是具体的支持性证据，仍不冒充对所有现存 WordPress worker 的独立检查。本研究没有重新验证第三项漏洞机制，未访问漏洞利用工具。

## 5. 抓取记录与交付校验

全部外部发现、读取与一次修复后的重取均通过 Apify。捕获目录：`/Users/chesterjohn/de-linker-data/incident-20261022/hosting-logs/php83-attestation-research-20261024/`；目录 0700、文件 0600。`evidence-manifest.json` 保留抓取原件及所读本地证据的 SHA-256、字节数与核验范围。抓取不含站点凭证或客户内容。

| 用途 | Actor run | Dataset | 结果 |
| --- | --- | --- | --- |
| 四个精确官方页面，首轮 | `MJHRQxMhAgsnyT0Ve` | `haBK30qjPCBfRKMjM` | FAILED；日志明确 512 MiB 内存耗尽并退出，保留失败记录，未据此下页面结论 |
| 四个有界官方域查询，仅发现来源 | `QvLUFWZU69XK6nvRc` | `wcwQhWqwLSY1QlLxx` | SUCCEEDED；四项查询，摘要不代替正文 |
| 同四个官方页面，内存改 2 GiB、并发改 1 后重取 | `1a0MhOBJeB0eP5wGh` | `Gz1NgzNiKBWmE8cba` | SUCCEEDED；四页 HTTP 200，含更新时间、Alt-PHP 发布及 Hostinger 方法 |
| 官方 changelog 静态读取 | `H01cyC6A6ic6tMeRh` | `HFanfJU7CJB2fZDJX` | SUCCEEDED；正文只有应用标题，证据不足 |
| 同一 changelog 通过 Apify 浏览器渲染 | `S7h0Fp98twxaxrs5S` | `ID1EwAcu3KrTOG0dN` | SUCCEEDED；正文提取不完整，不作为精确固定 release 或二进制映射证据 |

本次唯一仓库新增是这份报告；仅做文档、凭证泄露和捕获完整性检查，不以软件测试代替供应商修补证明。ACF、DNS、MFA 和配置器的业主裁定保持原范围，不由这份 PHP 研究重新开启。
