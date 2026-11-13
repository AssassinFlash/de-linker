# 本地僵尸实例退役与本地 E2E 状态矩阵补跑报告

- **执行日期**：2026-11-13
- **工作树**：`/Users/chesterjohn/Documents/de-linker`（未修改任何仓库已跟踪源码文件）
- **串行单实例与测试邮件纪律**：全程严格单实例串行（先退役 `c332`/`graccess` → 启动并跑完 `c222` 后立即 `just down c222` → 启动并跑完 `review` 后立即 `just down review`）；所有邮件均由 `linker-local` 本地 `mail/` spool 与 `TestMode` 拦截，零外部真实邮件投递。
- **提案与归档产物**：
  - `docs/acceptance/2026-11-13/matrix-batch-updates/local-state-rows.json`（11 条 `state-matrix.json` 行更新提案）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/local-e2e/c222-pending-account-report.json`（+ `c222-pending-account-de-1440.json`、`c222-pending-account-de-1440-readback.json`）
  - `docs/acceptance/2026-11-13/matrix-batch-updates/local-e2e/review-account-report.json`
  - `docs/acceptance/2026-11-13/matrix-batch-updates/local-e2e/review-genie-reply-report.json`
  - `docs/acceptance/2026-11-13/matrix-batch-updates/local-e2e/review-genie-lazy-bundle-report.json`（+ `review-genie-lazy-bundle-summary.json`）

---

## 一、僵尸实例退役与 Redis 前缀清理明细（`docs/agents/local-storage.md`）

### 1. 干跑核查与正式退役

两个僵尸实例原指向的临时工作树 `/private/tmp/acct-work` 与 `/private/tmp/g-report-access` 均已不存在，且实例进程均为 `stopped`：

| 实例 | 原登记工作树 | 数据库 | 候选文件数 | 核查结论 | 执行命令与结果 |
| --- | --- | --- | ---: | --- | --- |
| `c332` | `/private/tmp/acct-work`（已删） | `linker_c332` | 42,868 | 仅含快照 `20261105-1208`（与保留实例 `c222`/`review` 相同）、标准 WP 文件、本地运行日志、测试邮件 spool 与 planner 临时库，无唯一未合并资产 | `linker-local retire c332 --discard engine --discard logs --discard mail --discard planner --discard snapshot.json --discard wordpress --write` → `status: retired` |
| `graccess` | `/private/tmp/g-report-access`（已删） | `linker_graccess` | 10,760 | 无快照，仅含裸 WP、运行日志与 planner 临时库，无唯一未合并资产 | `linker-local retire graccess --discard engine --discard logs --discard planner --discard wordpress --write` → `status: retired` |

### 2. Redis `SCAN` + `UNLINK` 清理明细（严守禁令，未使用 `FLUSHDB`/`FLUSHALL`）

| 指标 / 前缀 | 退役前 | 回收键数（`SCAN` + `UNLINK`） | 退役后独立 `SCAN` 复核 |
| --- | ---: | ---: | ---: |
| `linker_c332:*` | 8,106 keys | **8,106 keys** | **0 keys** |
| `linker_graccess:*` | 3,734 keys | **3,734 keys** | **0 keys** |
| **合计回收** | **11,840 keys** | **11,840 keys** | **0 keys** |
| `linker_c222:*`（保留） | 12,800 keys | 0 | 12,800 keys（完好） |
| `linker_review:*`（保留） | 8,175 keys | 0 | 8,175 keys（完好） |
| Redis `DBSIZE` | 33,090 | -11,840 | 21,250 |
| Redis `used_memory` | 67.49 MiB（70,769,584 B） | -15.90 MiB | 51.59 MiB（54,091,296 B） |

### 3. 本地存储与资源报告（前后对比）

- **磁盘占用与可用空间**：
  - `~/de-linker-local` 目录占用：`13,864,368 KiB`（`13G`）→ `9,161,404 KiB`（`8.7G`），**释放目录文件约 `4.49 GiB`（`4,702,964 KiB`）**（其中 `c332` `4,495,168 KiB`、`graccess` `207,796 KiB`）。
  - 根分区 APFS（`/`）可用空间：`1,266,212,944 KiB` → `1,271,018,868 KiB`（含 MySQL 表空间 `linker_c332` / `linker_graccess` 删除后**净增可用空间约 `4.58 GiB` / `4,805,924 KiB`**，总容量 `3.6Ti`，当前可用 `1.2Ti`）。
- **本次新增与临时产物回收**：
  - 新增验收归档：`docs/acceptance/2026-11-13/matrix-batch-updates/local-e2e/`（6 个 JSON，约 `160 KiB`）及本目录 `local-state-rows.json`、`local-e2e-report.md`。
  - 已立即回收的运行期临时产物：`.scratch/e2e-shots/pending-account/latest/`（约 `24 MiB` 临时截图）、`.scratch/e2e-shots/account-auth/`、`tests/e2e/artifacts/test-results/`（约 `31 MiB` 失败上下文附件）及 `genie-marketing-entries` 临时批次目录；`genie-reply-presentation.spec.ts` 写向 `docs/acceptance/2026-10-18/223/replies/*.webm` 的受跟踪历史录制文件已通过 `git checkout` 原样恢复，确保仓库已跟踪文件零改动。
- **仍需保留的资源及理由**：
  - `c222`（`4.3G`，`stopped`）与 `review`（`4.3G`，`stopped`，已重定向至主树 `/Users/chesterjohn/Documents/de-linker`）：当前主线本地验收与回归复用基线实例，收尾状态全部 `stopped`、零遗留后台进程。

---

## 二、本地 E2E 补跑执行统计

| 序号 | 实例 | Spec 文件 | 通过 / 总数 | 耗时 | 目标矩阵覆盖结果 | 归档报告 |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 1 | `c222` | `tests/e2e/specs/pending-account.spec.ts` | **3 / 4** | 2.2m（130s） | `de 1440`（34.0s）、`en 390`（33.1s）、`de 390`（32.1s）**全部通过** | `local-e2e/c222-pending-account-report.json` |
| 2 | `review` | `tests/e2e/specs/account.spec.ts` | **22 / 26** | 3.8m（228s） | `de-1440` 找回密码邮件确认（8.3s）与 `de-1440` 账户资料保存校验（5.1s）**全部通过** | `local-e2e/review-account-report.json` |
| 3 | `review` | `tests/e2e/specs/genie-reply-presentation.spec.ts` | **10 / 10** | 27.6s | `de-1440-dock`（4.1s）与 `de-1440-workspace`（2.0s）**全部通过** | `local-e2e/review-genie-reply-report.json` |
| 4 | `review` | `tests/e2e/specs/genie-marketing-entries.spec.ts` | **28 / 32** | 5.1m（306s） | `recovery-{en,de}-{1440,390}`（4/4）与 `bootstrap-{en,de}-{1440,390}`（4/4）及 `native-scope-{en,de}`（2/2）**全部通过** | `local-e2e/review-genie-lazy-bundle-report.json` |

---

## 三、`state-matrix.json` 11 条目标行收口映射

1. **3 条 `pending` → `pass`**：
   - `authentication:pending-submit:de:1440`：`c222` `pending-account.spec.ts` `de 1440`（34.0s 通过）。
   - `authentication:registration-success:de:1440`：`c222` `pending-account.spec.ts` `de 1440`（34.0s 通过，含会话 cookie 与德语注册确认邮件断言）。
   - `authentication:password-email-confirmation:de:1440`：`review` `account.spec.ts` `de-1440: the lost-password request answers and its link opens the new-password card`（8.3s 通过）。
2. **4 条空证据 `pass` 行补齐真实报告路径**：
   - `account:overview-pending:de:1440`：补齐 `c222-pending-account-report.json` + `c222-pending-account-de-1440.json`。
   - `account:overview-approved:de:1440`：补齐 `c222-pending-account-report.json` + `c222-pending-account-de-1440-readback.json`。
   - `account:account-details:de:1440`：补齐 `review-account-report.json`（`de-1440: account details save names its error and keeps the typing`，5.1s 通过）。
   - `genie:thinking:de:1440`：补齐 `review-genie-reply-report.json`（`de-1440-dock` 4.1s + `de-1440-workspace` 2.0s，10/10 全绿）。
3. **4 条 `genie:lazy-bundle-failure-retry-close-focus:{en,de}:{1440,390}`：`partially-verified` → `pass` 并归档 `resolved_findings`**：
   - `genie-marketing-entries.spec.ts` 中 `recovery-{en,de}-{1440,390}`（4.0s / 3.7s / 2.9s / 3.8s）与 `bootstrap-{en,de}-{1440,390}`（3.7s / 3.0s / 4.5s / 3.1s）完整覆盖全部 6 项 `required_contexts`：① React 挂载前真实拦截阻断 `genie.js` 触发 `[data-linker-genie-load-error]`；② 营销页浮层 helper（显示 `Close`/`Schließen`、响应 `Escape`）与独立 `/genie/`、`/de/genie/` workspace（无关闭按钮、`Escape` 不关闭、点击重试恢复输入框）双形态区分；③ 重试聚焦、`Close`/`Escape` 关闭并将焦点退回原页面发送按钮；④ 390px 手机端 `role="dialog"` + `aria-modal="true"` 8 次 `Tab` 焦点围栏（含访客账户链接可达）与 1440px 桌面非模态行为；⑤ 页面源输入框与持久化待发送草稿保留、零静默后台模型请求、新问题触发 `[data-genie-entry-review]` 显式确认；⑥ 显式关闭后真实 `genie.js` 延迟 `linker-genie-ready` 到达绝不自动重开或偷发请求。结合生产已验证的 PR #717（`699e2a554`）空根视口位移修复，全部升为 `pass`。

---

## 四、同文件非目标失败用例的精确报错与根因分析

本次运行的所有目标矩阵行对应测试全部通过；同一 spec 文件内附带执行的另外 9 个用例失败，均已定位到精确源码行（均属测试夹具或旧测试选择器未跟进近期业务/安全改动，非本次 11 条目标行的产品缺陷）：

### 1. `pending-account.spec.ts`：`en 1440` 末尾 `run('deliver-one')` 报错（1 条）

- **精确报错**：
  - `tests/e2e/specs/pending-account.spec.ts:346` 调用 `just wp c222 eval-file .../pending-account.php deliver-one` 退出码 `1`。
  - PHP 错误日志（`linker-errors/php.log:536`）：`PHP Fatal error: Uncaught TypeError: in_array(): Argument #2 ($haystack) must be of type array, null given in .../tests/e2e/fixtures/pending-account.php:74`。
- **根因分析**：
  - `tests/e2e/fixtures/pending-account.php:26` 将 `$jobs = $fixture->mail();` 赋值为 `BrowserFixture::mail()` 返回的消息结构体数组 `list<array{to, headers, subject}>`（而非 post ID 列表 `$fixture->jobs()`）。
  - 仅在 `en 1440` 分支（`pending-account.spec.ts:344`）执行的 `deliver-one` 分支（`pending-account.php:72-74`）仍把 `$jobs` 元素当作 `$id` 传给 `get_post_meta($id, '_linker_mail_message', true)`，返回 `false` 后 `json_decode` 得 `null`，导致 `$message['to']` 为 `null` 触发 PHP 8.3 `TypeError`。
  - **修复方向**：将 `tests/e2e/fixtures/pending-account.php:72` 的 `foreach ( $jobs as $id )` 改为 `foreach ( $fixture->jobs() as $id )`。

### 2. `account.spec.ts`：旧两步注册与受限横幅选择器失配（4 条）

- **失败 2a（2 条）**：
  - `en: the register form carries its client constraints and refuses a bad email server-side`（`tests/e2e/specs/account.spec.ts:456`）：`expect(locator('form[data-linker-register]')).toHaveAttribute('data-active-step', '2')` 失败，实际值仍为 `"1"`。
  - `en: sign-in and sign-up are two pages and link to each other`（`tests/e2e/specs/account.spec.ts:508`）：`expect(locator('#reg_email')).toBeVisible()` 失败，实际 `#reg_email` 为 `hidden` 且 `disabled`。
  - **根因分析**：两步注册上线后（`plugins/linker-commerce/templates/myaccount/auth/form-register.php:72`、`content/windpress/auth.css:576-577`，业主 2026-10-17 裁定），第 1 步必须填写 `#billing_company`、业务角色、`#billing_country` 及网站/VAT ID 至少一项才能进入第 2 步，且第 1 步激活时第 2 步面板 `[data-pane="2"]` 内的 `#reg_email` 默认隐藏并 `disabled`。`account.spec.ts:451-455` 未填国家和网址即点击 `[data-next]`，`account.spec.ts:508` 则在刚打开第 1 步时直接断言 `#reg_email` 可见。
- **失败 2b（2 条）**：
  - `en: a restricted account signs in, keeps the workplace and reads its gate on the inquiry page`（`tests/e2e/specs/account.spec.ts:820`）：未找到 `section[aria-label="Account with limited access"]`。
  - `de: the restricted gate speaks German and links its own address`（`tests/e2e/specs/account.spec.ts:876`）：未找到 `section[aria-label="Konto mit eingeschränktem Zugriff"]`。
  - **根因分析**：`plugins/linker-commerce/includes/Presentation/LoginGate.php:75-81` 渲染 `content/livecanvas/inquiry/restricted.html:1`（`<section class="linker-inquiry-restriction" aria-label="{{title}}">`）时，`{{title}}` 已统一为 `'Access currently limited'` / `'Zugriff derzeit eingeschränkt'`（旧词条 `"Account with limited access"` 在 `languages/linker-commerce-de_DE_formal.po:7182` 已标为废弃 `#~`）。`pending-account.spec.ts:360` 使用 `.linker-inquiry-restriction` 选择器在 EN/DE 下均正常通过，而 `account.spec.ts:815,874` 仍硬编码旧 `aria-label`。

### 3. `genie-marketing-entries.spec.ts`：`home-recovery-{en,de}-{1440,390}` 超时（4 条）

- **精确报错**：`tests/e2e/specs/genie-marketing-entries.spec.ts:1098` 四个视口/语种用例均触发 `Test timeout of 50000ms exceeded`；错误快照显示 `#linker-genie-hero-surface` 已展开并展示 `"Genie could not load."` 与 `"Try again"` 按钮，但 `.hero-prompt` 处于 `[disabled]` 状态。
- **根因分析**：`plugins/linker-tools/src/hero/controller.tsx:172-177,208` 在失败归属隔离修复中规定：当 `context.phase !== 'ready'`（例如 `home-recovery-*` 模拟 `/entry-context` 返回 HTTP 503 期间）时，强制将 `.hero-prompt` 设为 `prompt.disabled = true` 并隔离输入，防止未验证归属前向错误会话写入草稿（新版契约已由 `tests/e2e/specs/genie-failure-ownership.spec.ts` 承接）。而 `genie-marketing-entries.spec.ts:1153` 仍在点击 `"Try again"` 恢复 `entry-context` 之前对被禁用的 `.hero-prompt` 调用 `await source.fill(fresh)`，导致 Playwright `fill()` 一直等待元素变为 enabled 直至 50s 超时。
