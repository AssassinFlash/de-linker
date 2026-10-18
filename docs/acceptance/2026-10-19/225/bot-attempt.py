"""
#225 live-walk evidence on the local instance c225: the bot attempt.

One real HTTP submission of the register form with every field filled and the
hidden trap ("website") filled too. It must create no account, queue no mail,
and raise the observable counter. The human walk is not done here: it runs
through the real Register button in the browser, in
`tests/e2e/specs/registration-two-step.spec.ts` (both a bare host and a full
https URL), whose run is saved in `checks/e2e-registration.log`.

The caller resets the shared connection allowance and the block counter first;
test mail would land in ~/de-linker-local/c225/mail.
"""
import json
import re
import subprocess
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
        match = re.search(r'name="%s"[^>]*value="([^"]*)"' % re.escape(name), html)
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
        return (
            response.status,
            response.headers.get("Location", ""),
            response.read().decode("utf-8", "replace"),
        )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            error.headers.get("Location", ""),
            error.read().decode("utf-8", "replace"),
        )


def mail_files():
    return sorted(path.name for path in MAIL.glob("*.eml"))


def main():
    evidence = {"tag": TAG, "register_url": REGISTER}
    _, before_count, _ = wp("linker-commerce", "registration-blocks", "--user=1")
    mail_before = mail_files()

    hidden = get_form()
    time.sleep(3.4)  # PublicGuard's minimum fill time
    fields = {
        "billing_company": "Solarbau Botprobe GmbH",
        "linker_customer_role": "installer",
        "billing_country": "DE",
        "linker_company_website": "example.com",
        "billing_vat_id": "",
        "billing_first_name": "Maria",
        "billing_last_name": "Beispiel",
        "email": BOT_EMAIL,
        "password": "Muster-Solar-2026!",
        "register": "Register",
        "woocommerce-register-nonce": hidden["woocommerce-register-nonce"],
        "linker_started": hidden["linker_started"],
        "linker_started_nonce": hidden["linker_started_nonce"],
        "website": "http://spam.example",
    }
    status, location, body = post(fields)
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
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
