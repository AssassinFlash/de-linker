# Security configuration readback

The full incident remains active. This record covers only two reversible management-plane changes and the obsolete mail forwarder. It does not establish that all public customer paths or mailbox delivery passed.

## WordPress native file editor

The production configuration did not previously define `DISALLOW_FILE_EDIT`. Before writing, its complete bytes were copied to the local private incident directory with mode 0600 and their SHA256 was checked against the remote original. Native WP-CLI set only `DISALLOW_FILE_EDIT=true`, followed by the existing opcode reset.

Actual native administrator readback:

| Capability or configuration | Before | After |
| --- | --- | --- |
| File editing disabled | false | true |
| `edit_plugins` | true | false |
| `edit_themes` | true | false |
| `manage_woocommerce` | true | true |
| Public protection configured/enforce/ready | true | true |
| Temporary strict business verification | true | true |

Rollback removes only the newly added constant via native WP-CLI and resets opcode. Restoring the entire earlier configuration would overwrite unrelated later settings and is not the rollback procedure. The private backup and native JSON are in `incident-20261022/admin-file-guard/` outside the repository.

## VPS root password login

A fresh SSH TCP connection using only the existing public key proved root access before the change; multiplexing, password and keyboard-interactive authentication were explicitly disabled for that check. Effective configuration previously allowed root password authentication. There were no `Match` sections or other explicit root policy directives.

Two independent operational reviews identified and corrected an automatic-rollback race and an in-place-write risk before execution. The applied script:

1. Saved the exact main configuration locally at mode 0600 and verified its SHA256.
2. Validated the candidate with `sshd -t/-T` and armed a 120-second directed automatic rollback before activation.
3. Changed only `PermitRootLogin yes` to `PermitRootLogin prohibit-password`, preserving file ownership/mode and using a validated same-directory atomic replacement.
4. Reloaded SSH and established a new nonmultiplexed public-key connection.
5. Stopped the rollback timer, verified its service and job queue were quiescent, then established another fresh key connection and reread effective policy, SHA256 and service states before recording success.

Final actual result: root password authentication disabled, existing public key retained, SSH and all four Linker services active. The final configuration SHA256 is `5c3cb63a19a325515ec9d569589ba47a0ecb0ed550a300402b617e33914596e0`. No key, password, other account policy, firewall, VPN or proxy setting changed.

Private evidence and the executed script are retained in `incident-20261022/ssh-root-guard/`. A deliberate rollback can reverse this one directive using the same validated atomic-write procedure through the working key connection. It must first check the expected current SHA and preserve concurrent configuration changes. The original file remains in the local private backup; no permanent host backup was created.

## Obsolete SunRiver Electric forwarding

The actual Hostinger primary mailbox plan is Starter Business Email, valid through 2028-03-09; its dashboard specifies 1,000 outgoing messages per 24 hours. This is the provider plan ceiling, not a promise about website delivery or a new application allowance.

After the owner's explicit confirmation, the only rule `sales@sunriverinverter.com → sales@sunriver-electric.com` was deleted. The native forwarder page now offers creation of the first rule. The source mailbox and stored messages remain. Before/after screenshots are in the local private `incident-20261022/mail/` directory. Old downstream delivery retries were not purged, and no production test message was sent.
