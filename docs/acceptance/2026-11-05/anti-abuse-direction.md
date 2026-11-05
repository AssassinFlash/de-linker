# Anti-abuse direction, production acceptance 2026-11-05 (D line, both directions)

Companion to `inquiry-guest-chain.md` / `inquiry-guest-chain-de.md` (normal
passage) and `pending-account-price-gate.md` (permission gate). This record is
the other direction: abuse is actually stopped on the real production chain.

**Result: PASS — malicious submission classified, held, and zero mail.**

## Real spam submission (production, real guest form)

Obvious crypto-lottery/phishing text submitted through
`https://de-linker.com/proforma-request/` (test mode ON, so any mail would go
to the tester only):

- Submission saved as inquiry 8607 (the form does not hard-block content at
  the transport; the assessment decides).
- AI mail assessment (Jev primary + deepseek-flash escalation, the correct
  channels): decision **`malicious`**, basis **`fraud_or_phishing`**.
- `NotificationHold::held(8607)` = **yes**: the record is held for staff
  review, isolated from normal inquiry processing.
- **Zero outgoing mail** for 8607: no customer receipt to the abuser and no
  normal new-inquiry notice to the team (mail log has no 8607 entries).

## Both directions on production (this date)

| Direction | Evidence |
| --- | --- |
| Normal guest inquiry passes | 8603 (EN): normal → both mails; 8606 (DE): unknown → conservative retry, record kept |
| Normal Genie turn passes | Real Chrome: invisible challenge, retry 200, correct sourced answer |
| Pending account permission | user 51: "Account under review", no net prices |
| Malicious submission stopped | 8607: malicious/fraud_or_phishing, held, zero mail |

## Cleanup (all read back)

- Assessment jobs for 8607 unscheduled; order 8607 deleted; test mail OFF.
- Screenshot `~/de-linker-data/inquiry-readback-20261105/spam-8607-confirmation.png`.
