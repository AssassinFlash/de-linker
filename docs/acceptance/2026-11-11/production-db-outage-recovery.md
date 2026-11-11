# 生产 DB 宕机恢复验证清单（2026-11-11 事故）

事故：主机侧 MySQL 消失（00:35 UTC 前后负载 49–69 → 3306 拒连），站点全球不可达。
主机负载已回稳但 DB 未归。恢复判定按序执行，全部通过才算恢复：

1. `mysql -h127.0.0.1 -uu388076051 -e 'SELECT 1'` → ok
2. `wp option get siteurl` → https://de-linker.com
3. `curl https://de-linker.com/` 与 `/de/` → 200（本机+VPS 双点）
4. VPS `systemctl start linker-engine-feed-sync.service` → success；
   engine `/resource/version` compat_revision 仍 `932e2ff6…`
5. `wp linker-commerce publication repair-bindings --dry-run` → 0 条需续期（无回退）
6. Woo 订单/询盘计数与宕机前快照（db-20261110T233636Z）比对，无丢失
7. 邮件队列出队正常（mail job 无 stuck）
8. `uptime` 负载回常态；查负载尖峰期间主机是否有异常 cron/进程记录
9. 恢复后重派：F 线（commercial 生产实走）与 I 线 IMAP 收件腿（若凭据可得）
