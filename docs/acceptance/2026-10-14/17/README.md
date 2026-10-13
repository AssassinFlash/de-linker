# #17 一次性切换：2026-10-14 夜执行记录

业主 2026-10-14 令：欠账清零后直接推进 #17，不等确认，早间见完成。本文件是执行记录；
工具与运行面的最终形态描述在 docs/specs/17-cutover.md 的变更记录（2026-10-14 条）。

## 预检（对生产只读；全部在窗口前）

- `just cutover data`（无异无--write）= 807 项待应用、0 漂移；7-facts/8-engineering plan exit 0；
  9-i18n plan 在部署前报 `linker-i18n` 命令未注册——预期（该命令随新插件部署存在，数据步在部署之后）。
- `just cutover hygiene`（报告模式）= 待删修订 2108、9 张旧表、103 个旧选项；autoload 快照落备份。
- `just cutover services`（报告模式）= 两条发布命令 + 两个地址变量；窗口运行前工具尚无远程发布实现（见修复）。
- 生产访问实证：`ssh hostinger-de-linker` = 共享主机 u388076051（/root 不可写）；服务 VPS = `linker-services`
  （新 ssh 别名，root@72.62.97.95，key codex_linker_vps_20260723）。线上插件面与 spec 17 §3 的删除清单一致。

## 预检暴露并修复的工具缺口（各带测试；均为此前只跑本地演练的后果）

1. 远程 shell 引用（两次实伤：hygiene 探针、备份 dump 收到裸 `set`）→ `Target.shell_command` 唯一实现。
2. `services --run` 发布目标 = 站主机（`/root` 不可写）→ 改 `linker-services`；暂存 mkdir 先行。
3. 发布随船 678 MB 本机 arm64 `.venv` → 排除；主机 uv `--frozen` 自建。
4. 备份/恢复脚本内嵌 ssh 前缀 → `Target.wp_on_target()`（`--path` 形式）+ bash 数组。
5. 远程目录大传输被站主机掐断（uploads 2.6 GB/8 分钟）→ `copy_out` 分块（每块一条 tar 流一条连接）。
6. 备份脚本把失败当成功写清单（tar 返回码未查）→ 两端返回码均查，任一失败即中止。

## 服务 VPS 运行面（窗口前已就位；命令按序可重放）

- 发布：`just cutover services --run`（LINKER_ENGINE_URL/LINKER_GENIE_URL 环境变量给出）→
  `/opt/linker-engine/<ver>/`、`/opt/linker-genie/<ver>/` + `current` 软链；两个 WP 选项写入。
- venv：`cd /opt/linker-{engine,genie}/current && /root/.local/bin/uv sync --locked`。
- 环境：`/etc/linker-engine.env`（FEED/COMPATIBILITY/CORS）、`/etc/linker-genie.env`（GENIE_WP_URL）；
  密钥以既有回退路径装到 `/root/.config/terravolt-builder/*.env`（600）。
- 单元：`linker-engine.service`（8901）、`linker-genie.service`（127.0.0.1:8902）；nginx 8443 加 `location /genie/`。
- 烟测：WP 主机 `curl -sk https://72.62.97.95:8443/genie/health` = `{"status":"ok"}` ✓；引擎 8443 旧单元仍在（旧令牌要求，属预期）。

## 窗口（进行中——每一步的输出与证据在本文件末尾追加）

（待录）
