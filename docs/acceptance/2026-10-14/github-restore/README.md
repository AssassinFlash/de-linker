# GitHub 工作流恢复：2026-10-14

业主令："把 github 这块搞定——当时是私有仓库导致一切后续都无法进行了；改成公有是不是就解决？"
**结论：是。根因=私有仓库在 GitHub Free 的 Actions 免费额度（2,000 分钟/月）耗尽；改为公有后 Actions 无额度上限，当即恢复。**

## 根因证据链（全部来自 GitHub 自身）

- 每次失败 job 的官方 annotation：*"The job was not started because recent account payments
  have failed or your spending limit needs to be increased."* —— 且 `steps: 0`、3-5 秒即死（无日志）。
- 全仓 run 账：**478 个 run、累计约 1,902 分钟**（私有免费额度 2,000/月），最后一次成功
  2026-10-12 18:54；跨线后所有 run 立刻被拦。18:50 那个 steps=14 的失败是真红测试，与本因无关。
- 10-12 的会话据此把推送整体转为本地暂缓——本次解除后积压 **125 个提交**一次补齐。

## 公开前门（凭"公开=永久可克隆历史"倒逼的检查，全部通过）

- **密钥扫描**：全历史 462 个提交的**所有 blob**流式扫描（deepseek/openrouter/aihubmix/apify/
  GitHub/私钥/ssh 形态）——唯一命中是测试夹具里的显式占位符 `sk-012345678…`；工作树同扫零真命中。
- **敏感面速览**：价/毛利/保密类词全仓库抽样——命中皆为词形巧合（commissioning 等），无商务机密面。

## 执行与验收

- `gh repo edit --visibility public`（描述同步，"local-first (the delivery repo)"）。
- **CI 实证**：翻公开前 3 秒死；翻公开后 dispatch 的 run `38501403509` = **success**（完整执行）。
- **积压推送**：`git push origin main` 把 `5b21ef9 → 4d1de3f`（125 提交）推上远端。
  **经验教训**：该推送的 137 MB pack 经业主本机代理隧道（198.18.0.1 假 IP）反复中途停摆（pack-objects
  阻塞于 xwrite、0% CPU）；**小包推送秒过**。为此在 VPS（直连网络）建了常备中继：
  `/root/de-linker-mirror.git`（bare 克隆）+ 仓库部署密钥 `vps-mirror (push relay via linker-services)`
  （id 166377117，**read-write、可随时吊销**）。大包推送的兜底路径 = 本地 bundle → VPS 收编 → VPS 直推。
- **首次真 CI 抓出的红与修复**（此前本地从未跑过完整门，CI 一上线就连环兑现价值）：
  ① `ApprovalTest.php` 3 条 phpcs 对齐警告（phpcbf）；
  ② PHPStan `alreadyNarrowedType`——追到**我自己**在 `serve_pdf` 上的假 docblock（过滤器参数实为
  mixed，守卫正是代码要点；docblock 改为实话，`orders_query` 同法加宽）；
  ③ `EngineProxyTest` 联合类型未收窄（补 assertInstanceOf）；
  ④ `App.tsx` prettier 换行 + 重建 build；⑤ e2e `products.spec.ts` prettier；⑥
  `test_12_site_chrome_quoting.py` 的 mypy（dict 捕获改双列表）。
  修复后：本地 `just check` **EXIT=0**、`just test` **EXIT=0**（与 CI 同门），提交 `3bb94cf`、`667c32b`。
- **CI 终态**：`667c32b` 那次跑到倒数第三门时又抓出一处环境差——`i18n-coverage`（积压带来、旧 CI 从未
  跑过的新门）需要 gettext 的 `msgattrib`，runner 镜像没有；工作流补 `apt-get install -y gettext`
  后（提交 `c68020f`），push 触发的 run **全绿**（`just check` + Playwright 安装 + `just test`——
  含 10 条 e2e，均在 runner 上通过 + build 复现检查）。

## 常备事项

- 恢复后的工作流：本地 `just check` + `just test` 全绿 → 推送；大包用 VPS 中继。
- 部署密钥如不再需要：`gh repo deploy-key delete 166377117`；VPS 镜像亦可删（`rm -rf /root/de-linker-mirror.git`）。
