# 合并终态验收（2026-10-14，t110）

四支分支并入 main（ca29402 仪表盘 → 55ed669 PDP/FAQ → 5677a2f 登录表单 → 3072ba5 配置器），
另有两笔收口提交：ea8ee1c 低优清扫、6aed01a 短代码守卫补第 48 项。
t110 重锚回主检出、present 收敛、WindPress 重编后，全部门在同一状态上跑：

- `just e2e t110`：**68 passed / 0 failed / 5 skipped**（12.2m；含配置器 17 项、账户 11 项、i18n、Genie 判定组）
- `python3 tools/checks/legacy-surfaces.py`：**CLEAN，exit 0**（13 面 0 资产引用 / 0 品牌词 / 0 旧域名）
- 全量 phpunit：**929 tests / 4377 assertions / 0 failures**（45 条集成按环境跳过）
- linker-tools vitest 99/99；`build:check`：build/ matches its sources

本目录 16 张截图 = 合并后 t110 的终态：账户工作台（登录态 1440/390）、询盘列表、登录注册（访客 1440/390、DE 390）、
PDP（访客与批准客户 1440/390）、FAQ（EN 1440/390、DE 390）、配置器（1440/390）、DE 账户 390。
各线自己的「参照 vs 我们」并排图在 docs/acceptance/2026-10-13/<line>/ 下（仪表盘 24 张 compare-*，PDP/FAQ 与配置器的 ours-* + ref-*，登录表单的 ours-*/ref-*）。
