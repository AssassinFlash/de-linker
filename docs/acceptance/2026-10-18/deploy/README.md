# #298 · 部署文件旁置上传与 rename 切换

## 实现与本地证据

根因与裁定：[票 #298](https://github.com/AssassinFlash/de-linker/issues/298)。此前逐文件覆盖插件，曾在约 30 秒的部署窗口里产生 10 条 `Options::notify_sender()` 不存在的 fatal。本改动只替换文件发布机制，插件激活、语言包安装、readback 与 `verify` 保持既有路径。

- 插件：先通过原有 `Target.copy_in` 分块上传完整目录到 `wp-content/plugins/.<slug>.next`，上传成功后在同一条目标机 shell 中执行 `mv <slug> .<slug>.prev`、`mv .<slug>.next <slug>`。两个目录具有相同父目录；上传与 Composer 安装不在这段切换内。
- mu-plugin 的 PHP/PEM、仓库管理的子主题文件：上传到同目录的 `.<filename>.next`，旧文件先 `cp -p` 到 `.<filename>.prev`，再用一次 `mv -f` 替换 live。主机自己的 mu-plugin 与子主题其余资产原样保留。
- 隐藏的旁置目录避免被当成另一个常规插件；mu 文件备份不以 `.php` 结尾。每次成功发布保留上一版，下一次发布在上传成功后更新它。首次新增路径用 `.prev-absent` 记录之前不存在，回滚时移除新增项。
- 插件目录第二次 rename 失败，或间隙中收到 HUP/INT/TERM，EXIT trap 把上一版放回 live。传输失败不改变 live 和已有 `.prev`；重跑会清理未完成的 `.next`。
- 每个切换返回 `rename <relative>: <seconds> s`，由 Bash `time` 测量切换命令块，不含上传、备份文件复制、SSH 建连。Bash 的显示精度为毫秒；它不是内核 syscall 延迟。

这里采用票据明确允许的两次目录 rename，没有引入 `current` 符号链接。两次 rename 之间有短暂的目录缺席间隙，各插件也分别切换；这不构成全站单事务。不能用本地通过代替 Hostinger 的运行时验收。

可重复运行的本地证据（仅临时目录，无 SSH、邮件或 WordPress 实例）：

```sh
just cutover check
just cutover test
```

`tests/test_atomic.py` 证明旧目录 inode 在 `.prev` 中保留、整树替换清除旧文件、单文件保持旧打开句柄可读、回滚新增/既有路径、回滚预检、传输失败后重试、第二次 rename 失败与 TERM 后恢复。`test_deploy_and_rollback_use_real_filesystem_on_local_stand_in` 从 `steps.deploy` 走真实 shell/rsync，覆盖全部仓库插件、mu PHP/证书和主题文件，再调用回滚；只有 WP-CLI 边界使用夹具。`tests/test_cli.py` 覆盖 dry run 与写入开关。TDD 中分别观察到缺失发布接口、文件上传路径错误、缺失回滚接口、TERM 留空路径、缺失 CLI 命令/耗时回执的失败，再实现至通过。

Spec / Standards 对全量 `c12a9a22...854068be` 分别评审：Spec 无阻塞发现；Standards 发现目录回滚的 TERM 间隙，已先加失败夹具，再补恢复 trap，定向复核确认解决、无新发现。`test_interrupted_rollback_keeps_live_available_and_can_be_retried` 验证中断后仍可读 live，并可重新完成回滚。部署工具专项结果：Ruff、mypy 通过，pytest **94 passed**。本票不改客户界面。

## 一条命令回滚文件发布

在**执行该次部署的同一检出版本**运行：

```sh
just cutover rollback-deploy
```

该命令预检所有发布路径的 `.prev` / `.prev-absent`，然后恢复文件，不重新上传、不导入数据库、不改激活列表。目录通过 rename 恢复，文件通过单次 rename 覆盖；成功回滚消耗上一版，不能再次运行同一命令作为 redo。预检失败时没有任何路径被改变。它适用于本机制成功完成的一次文件发布；中途失败时先处理失败回执，不把旧部署遗留的备份混当同一批版本。

本地实例的同一入口为 `just cutover rollback-deploy --target local:c298`。要只看计划，使用 `uv run --locked --project tools/cutover linker-cutover rollback-deploy`（`just` 写入配方会自动加 `--write`）。完整数据库/文件备份的原回滚入口仍为 `just cutover rollback --backup <backup-directory>`。

## 未完成（Claude）：生产实走与读回

本会话没有部署或写生产，也没有真实发信。合并并通过评审后，Claude 在负责部署的检出版本独占执行下面步骤，将结果补到票 #298。保持正常站点请求可用，不开启维护页掩盖 REST 失败；本票不需要触发任何邮件。

1. `just cutover backup`，记下完整备份路径，确认成功后才继续。
2. 运行下方探针。它在部署前先证明只读 REST 端点有效；部署过程中连续请求该端点，部署后再请求一次。SSH 只读取 fatal 日志的 inode/大小和插件目录 inode；不会读取配置或密钥。部署回执和探针 JSON 只写本机 `~/de-linker-data/c298-proof/`。
3. `just cutover verify`，按既有 readback 检查插件/语言包与实际站点。检查 `deploy.log` 的逐路径 rename 耗时；`proof.json` 必须为部署 exit 0、全部 REST 成功、所有 fatal 文件字节无增量，以及每个旧 live 目录的 device/inode 等于部署后的 `.prev`。
4. 将回执、请求数量/起止时间、耗时、fatal 前后元数据与 inode 读回结果附到票上。若日志发生轮转/截断或任意检查失败，本项不通过，排查后重新验证。需要撤回时运行上一节的一条命令，再跑 `just cutover verify`；不为证明回滚而强制改动生产两次。

```sh
python3 - <<'PY'
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

evidence = Path.home() / 'de-linker-data' / 'c298-proof'
evidence.mkdir(parents=True, exist_ok=True)
root = '/home/u388076051/domains/de-linker.com/public_html'
slugs = ('linker-commerce', 'linker-i18n', 'linker-tools')
url = 'https://de-linker.com/wp-json/linker/v1/catalog-search?q=SAJ&limit=2&lang=en'

def metadata():
    script = (
        f'set -eu\ncd {root}\n'
        "find wp-content/uploads/wc-logs -maxdepth 1 -type f "
        "-name 'fatal-errors-*.log' -printf 'log\t%p\t%i\t%s\n'; "
        'for slug in linker-commerce linker-i18n linker-tools; do '
        'for path in "wp-content/plugins/$slug" "wp-content/plugins/.$slug.prev"; do '
        'if [ -e "$path" ]; then stat -c "tree %n %d %i" "$path"; fi; '
        'done; done'
    )
    raw = subprocess.check_output(
        ['ssh', '-o', 'BatchMode=yes', 'hostinger-de-linker', script], text=True
    )
    logs, trees = {}, {}
    for line in raw.splitlines():
        if line.startswith('log\t'):
            _, path, inode, size = line.split('\t')
            logs[path] = [int(inode), int(size)]
        elif line.startswith('tree '):
            _, path, device, inode = line.split()
            trees[path] = [int(device), int(inode)]
    if not trees:
        raise RuntimeError('missing directory metadata')
    return {'logs': logs, 'trees': trees}

requests = []
def probe():
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        request = urllib.request.Request(url + '&cbq=' + str(time.time_ns()))
        # A 10-second per-request bound prevents a stalled probe hiding deploy completion.
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
            ok = response.status == 200 and isinstance(payload.get('items'), list)
        requests.append({'at': stamp, 'ok': ok})
    except Exception as error:
        requests.append({'at': stamp, 'ok': False, 'error_type': type(error).__name__})

probe()
if not requests[-1]['ok']:
    raise RuntimeError('REST baseline failed; deployment not started')
before = metadata()
(evidence / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
with (evidence / 'deploy.log').open('w') as output:
    deploy = subprocess.Popen(['just', 'cutover', 'deploy'], stdout=output, stderr=output)
    while deploy.poll() is None:
        probe()
        # #298's former approximately 30-second window: 0.1 s samples it about 300 times.
        # This is the chosen acceptance probe interval, not a runtime service threshold.
        time.sleep(0.1)
probe()
after = metadata()
logs_unchanged = all(
    after['logs'].get(path) == value for path, value in before['logs'].items()
) and all(path in before['logs'] or value[1] == 0 for path, value in after['logs'].items())
renamed = all(
    before['trees'].get('wp-content/plugins/' + slug) is not None and
    before['trees'].get('wp-content/plugins/' + slug) ==
    after['trees'].get('wp-content/plugins/.' + slug + '.prev')
    for slug in slugs
)
result = {
    'before': before, 'after': after, 'deploy_exit': deploy.returncode,
    'requests': requests, 'request_count': len(requests),
    'fatal_logs_unchanged': logs_unchanged, 'directory_rename_proved': renamed,
}
(evidence / 'proof.json').write_text(json.dumps(result, indent=2) + '\n')
assert deploy.returncode == 0 and all(item['ok'] for item in requests)
assert logs_unchanged and renamed, 'production acceptance failed; inspect proof.json'
print('PASS:', len(requests), 'REST probes;', evidence)
PY
```
