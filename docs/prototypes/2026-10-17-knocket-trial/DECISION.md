# 原型 · Knocket 本地试装（#259，地图 #220）

- `knocket-trial.php`：只在本地实例、只在带 `?knocket=1` 的请求里生效。它为这一个响应放宽本地隔离 CSP，在 `</body>` 前原样输出业主的安装 snippet，同时隐藏 Genie 的入口。用法：放进本地实例的原型 mu-plugin 加载器，打开 `http://127.0.0.1:9033/?knocket=1`。
- 用途：业主要求在本地实际用一次 Knocket，并与 Genie 对比。结果见 `docs/research/2026-10-17-knocket/TRIAL.md`。
- 结论：不采用（DOSSIER §0 + TRIAL §0）。这个文件只是一次性试装，不进入任何插件，也不上线。
