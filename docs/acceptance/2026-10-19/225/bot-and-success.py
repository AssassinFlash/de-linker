"""
#225 live-walk evidence on the local instance c225.

Two real HTTP submissions of the register form, both from this machine's
single connection:

1. a bot: every field filled, the hidden trap ("website") filled too. It must
   create no account, queue no mail, and raise the observable counter.
2. a human: the same form without the trap. It must create the pending
   customer, store the two-step fields and send the two expected mails to the
   local mail sink.

Local instance only; test mail lands in ~/de-linker-local/c225/mail. The caller
resets the shared connection allowance first (see README) and removes the test
customer afterwards.
"""
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:9138"
REGISTER = BASE + "/my-account/register/"
MAIL = Path.home() / "de-linker-local/c225/mail"
TAG = "225-" + str(int(time.time()))
BOT_EMAIL = f"tester225-bot-{TAG}@example.test"
HUMAN_EMAIL = f"tester225-human-{TAG}@example.test"


def wp(*args):
    result = subprocess.run(
        ["just", "wp", "c225", *args], capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_form():
    with urllib.request.urlopen(REGISTER, timeout=60) as response:
        html = response.read().decode("utf-8")
    def field(name):
        match = re.search(
            r'name="%s"[^>]*value="([^"]*)"' % re.escape(name), html
        )
        return match.group(1) if match else ""
    return {
        "woocommerce-register-nonce": field("woocommerce-register-nonce"),
        "linker_started": field("linker_started"),
        "linker_started_nonce": field("linker_started_nonce"),
    }


def post(fields):
    opener = urllib.request.build_opener(NoRedirect)
    data = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(REGISTER, data=data, method="POST")
    try:
        response = opener.open(request, timeout=60)
        return response.status, response.headers.get("Location", ""), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Location", ""), error.read().decode("utf-8", "replace")


def mail_files():
    return sorted(path.name for path in MAIL.glob("*.eml"))


def registration(email, company, trap=""):
    hidden = get_form()
    time.sleep(3.4)  # PublicGuard's minimum fill time
    fields = {
        "billing_company": company,
        "linker_customer_role": "installer",
        "billing_country": "DE",
        "linker_company_website": "example.com",
        "billing_vat_id": "",
        "billing_first_name": "Maria",
        "billing_last_name": "Beispiel",
        "email": email,
        "password": "Muster-Solar-2026!",
        "register": "Register",
        "woocommerce-register-nonce": hidden["woocommerce-register-nonce"],
        "linker_started": hidden["linker_started"],
        "linker_started_nonce": hidden["linker_started_nonce"],
    }
    if trap:
        fields["website"] = trap
    return fields


def main():
    evidence = {"tag": TAG, "register_url": REGISTER}

    _, before_count, _ = wp("linker-commerce", "registration-blocks", "--user=1")
    mail_before = mail_files()

    # 1. The bot.
    status, location, body = post(registration(BOT_EMAIL, "Solarbau Botprobe GmbH", "http://spam.example"))
    evidence["bot"] = {
        "status": status,
        "location": location,
        "error_notice": "We could not process this registration." in body,
        "account_exists": wp("user", "get", BOT_EMAIL, "--field=ID")[0] == 0,
        "mail_added": len(mail_files()) - len(mail_before),
    }
    _, after_count, _ = wp("linker-commerce", "registration-blocks", "--user=1")
    evidence["counter_before"] = before_count
    evidence["counter_after"] = after_count

    # 2. The human.
    mail_before_human = mail_files()
    status, location, body = post(registration(HUMAN_EMAIL, "Solarbau Abnahme GmbH"))
    code, user_id, _ = wp("user", "get", HUMAN_EMAIL, "--field=ID")
    new_mail = [name for name in mail_files() if name not in mail_before_human]
    website = wp("user", "meta", "get", user_id, "linker_company_website")[1] if code == 0 else ""
    approval = wp("user", "meta", "get", user_id, "linker_approval_status")[1] if code == 0 else ""
    team_mail_has_website = False
    for name in new_mail:
        text = (MAIL / name).read_text(encoding="utf-8", errors="replace")
        if "Solarbau Abnahme GmbH" in text and "https://example.com" in text:
            team_mail_has_website = True
    evidence["human"] = {
        "status": status,
        "location": location,
        "user_id": user_id,
        "website_meta": website,
        "approval_meta": approval,
        "new_mail_files": len(new_mail),
        "mail_names": new_mail,
        "team_mail_has_website": team_mail_has_website,
    }
    evidence["human_email"] = HUMAN_EMAIL

    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
