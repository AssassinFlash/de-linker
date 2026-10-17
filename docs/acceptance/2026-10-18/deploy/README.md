# #298 · 整批 rename 发布与站外回滚备份

依据：[票 #298](https://github.com/AssassinFlash/de-linker/issues/298) 与 [PR #299 第 1 轮已裁定意见](https://github.com/AssassinFlash/de-linker/pull/299#issuecomment-6241352856)。本记录按该轮意见更新，取代此前逐插件切换和备份留在 web root 的方案。

## 发布路径

```text
一个库存函数
  → 全部输入验证、全部本地构建
  → 全部 .next 上传
  → 站外目录 / 同文件系统预检、备份准备
  → 一个远端 shell：整批 rename + 一套失败恢复 trap + 总耗时
  → 插件激活、语言包
  → 既有 verify
  → 全部备份 rename 到站外，读回并清除上一批备份
```

- `steps.deployment_artifacts()` 同时定义发布和回滚的库存；没有两份 globs。`atomic._siblings()` 统一 `.next/.prev/.prev-absent` 名字，`publish()` 返回带 deploy ID、总切换耗时、路径和站外目录的 `Receipt`。
- 所有插件、mu PHP/PEM、子主题文件先上传，再在一个远端 shell 中完成全部 live rename。失败/可捕获中断恢复整批。普通文件的旧副本在计时前准备；构建、上传、SSH、复制备份不进入 live 切换计时。
- deploy ID 为 UTC 时间加 git SHA；站外 manifest 为每个备份记录同一 ID 和 device/inode，并记录新 live inode、旧路径是否存在。回滚拒绝混批 ID、不同库存、备份缺失/被替换及未登记的 live 变更，逐项报路径，预检不写入。
- rename 的选择理由与既有请求、opcache 时间戳重验的残余风险记录在[规格 17](../../../specs/17-cutover.md#文件发布与回滚298pr-299-第-1-轮裁定)。总耗时以实际回执为准；本地通过不代表生产零 fatal。
- 发布前检查站外目录解析后不在 web root，且与所有目标父目录同 device；跨文件系统在 live 切换前失败。Hostinger 备份根为账户的 `~/deploy-prev/`；本地替身为目标根目录旁的 `deploy-prev/`。
- verify 通过后把 `.prev` / `.prev-absent` 按 rename 放到 `~/deploy-prev/<deploy-id>/files/<relative>`，manifest 为 `archived`。读回备份 inode，并确认对应 `.next/.prev/.prev-absent` 不再留在 web root。**只保留最近一批部署备份**，下一批 verify / 归档成功才删除较早 manifest 所属目录。
- verify 失败为非零，manifest 保持 `pending`，同目录备份继续可回滚；先处理失败回执并及时回滚，不把这次失败部署当作交付。下一批发布拒绝覆盖未完成的 pending 批次。

## 本地 TDD 与验收证据

测试继续走真实 `Target.shell` / rsync / rename 的临时目录替身，不连接生产、不发邮件。

```sh
just cutover check
just cutover test
```

| 评审决定 | 实现与证据 |
| --- | --- |
| 1 全部 stage 后一次 switch | `test_all_artifacts_are_uploaded_before_one_switch` 在后续上传期间断言所有 live 仍旧，并记录一次切换 shell；后段 rename 失败和 TERM 的夹具证明前面目录/文件一并恢复。回执报告总耗时。 |
| 2 选择 rename 的理由 | 规格 17 记录 WordPress realpath、`__DIR__` / `plugin_basename()`、opcache 键及残余风险；不进行生产 symlink 试验。 |
| 3 deploy ID 与一致性预检 | `test_rollback_rejects_mixed_deploy_ids_before_changing_live`；缺失和替换备份测试；manifest 的 ID、库存、inode 与实际备份逐项比对。 |
| 4 回滚后读回 | `test_rollback_restores_whole_batch_and_reports_actual_identities` 与完整 `steps.deploy` / `finish_deploy` / `rollback_deploy` 夹具：真实 inode、active 列表及同一 verify；inactive 会返回失败。 |
| 5 verify 后站外归档 | `test_verify_gates_archive_and_rollback_checks_plugins_and_pages`、`test_verified_backup_moves_outside_web_root_and_only_latest_is_kept`、跨文件系统拒绝测试；archive / rollback 保留原目录 inode，主机自己的 mu / 主题邻居保持原样。 |
| 6 smells | 一个 `_siblings()`、一个 `deployment_artifacts()`；typed `Receipt`；耗时为 `switch_seconds`；探针从 `Target` 与 `plan` 取配置。 |
| 7 多端点探针 | `tests/test_probe.py` 用真实 loopback HTTP 服务，覆盖所有指定端点的 before/during/after；200 但 REST 结构错误阻止开始部署，新增 fatal 或错误响应使最终验收失败。 |

本轮观察到失败后实现至通过的切片包括：缺失批量发布接口、缺失 manifest / deploy ID 检查、回滚没有恢复整批文件、缺失站外归档、缺失 verify 门、缺失多端点探针及 CLI 入口。失败恢复测试还复现了“回滚中断后单文件 inode 改变无法重试”和“备份复制失败留下残件阻止重试”，均在本分支修复。代码不改客户界面或邮件文案。

本轮增量 `580d09c1...b9bb2eb3` 的双评审与修复复核：

- **Standards**：没有规则违背或新增待处理 smell；发现的早期回滚临时硬链接、归档 manifest 提交后中断两项正确性问题，已补失败夹具、修复并定向复核通过。
- **Spec**：1–7 项均有实现，无范围外改动；同两项恢复边界已复现、修复，定向复核无剩余发现。测试分别覆盖首个/末个插件处中断，以及真正完成 archived manifest rename 后立即 TERM，再证明可重试并回滚。

专项验证：`just cutover check` 通过，`just cutover test` **107 passed**，新增部署与探针测试无跳过。

## 一条命令回滚

在**执行该次部署的同一检出版本**运行：

```sh
just cutover rollback-deploy
```

命令先预检整批 manifest，再 rename 恢复 pending 同目录或 archived 站外备份；逐路径打印读回的 device/inode 或 `absent`，打印三个插件实际状态，并运行同一 verify。任一读回、active 或 HTTP / Search Console 检查不通过都会返回非零。成功回滚消耗上一版，不能重复调用作为 redo。无需上传、Composer 构建或数据库导入。

本地入口：`just cutover rollback-deploy --target local:c298`。只看计划使用 `uv run --locked --project tools/cutover linker-cutover rollback-deploy`（`just` 写入配方自动加 `--write`）。完整备份回滚入口仍为 `just cutover rollback --backup <backup-directory>`。

## 未完成（Claude）：生产实走

本实现会话没有生产写入。评审合并后，Claude 从负责部署的检出版本独占运行：

1. `just cutover backup`，确认成功并记录完整备份路径。
2. 使用下面的一条探针命令。它先验证全部只读端点的基线，再运行真正的 `deploy --write`，并发循环请求各端点，最后读回 fatal 文件元数据和站外备份 inode。普通 deploy 自行完成 verify 和站外归档；这里不打开维护页遮住真实请求。

   ```sh
   just cutover probe --evidence "$HOME/de-linker-data/c298-proof"
   ```

3. 要求命令 exit 0，`proof.json` 的 `successful`、`fatal_logs_unchanged`、`directory_rename_proved` 全为 true，deploy exit 0，所有端点每阶段都有成功样本。日志轮转/截断、任何端点状态/结构错误或 rename 证据不符都不通过。`deploy.log` 要含 deploy ID、总 switch duration、verify 结果和站外归档路径。文件只存在本机指定 evidence 目录，不包含响应正文或密钥。
4. 将 proof / deploy 回执与请求起止时间、数量、总切换耗时补到票 #298。若需撤回，运行上一节的命令；它已经包含读回和 verify，不为证明回滚强制把生产改动两次。

端点配置在 `plan.DEPLOY_PROBE_ENDPOINTS`：首页、联系页、Proforma 请求页、`VERIFY_PRODUCT_PATHS` 中的英文产品页、commerce 产品搜索、i18n 的 `wp/v2/pages?lang=de`、tools 的只读 `genie/conversation`。i18n 自己没有 REST 命名空间，实际由 `RestLang` 进入语言并过滤原生路由；探针要求返回非空、全部为德语地址。tools GET 只读已有线程，不创建对话、不调用模型、不发信。root / base URL 从 `Target` 来，插件名单从 `plan.NEW_PLUGINS` 来，README 不另写一套主机路径或 slug。

只查看端点计划，不部署：

```sh
uv run --locked --project tools/cutover linker-cutover probe
```
