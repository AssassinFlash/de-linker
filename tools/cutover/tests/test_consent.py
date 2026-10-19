"""Deployment checks must notice consent carriers disappearing or bypassing the CMP."""

import json

from linker_cutover import steps
from linker_cutover.target import Target


class ConsentSite(Target):
    """WP-CLI settings and served HTML at the deployment boundary."""

    def __init__(self) -> None:
        super().__init__(
            label="consent",
            root="/site",
            base_url="https://de-linker.com",
            prefix=("wp",),
            shell_prefix=None,
            rsync_remote=None,
        )
        self.active = True
        self.options = {
            "googlesitekit_consent_mode": {"enabled": True},
            "googlesitekit_analytics-4_settings": {
                "measurementID": "G-FIXTURE",
                "useSnippet": True,
            },
        }
        self.tag = '<script type="text/plain" data-cookieyes="cookieyes-analytics" src="https://www.googletagmanager.com/gtag/js?id=G-FIXTURE"></script>'
        self.withdrawal = '<script id="linker-consent-withdrawal-js"></script>'

    def wp_json(self, *args: str) -> object:
        return [
            {
                "name": args[2].removeprefix("--name="),
                "status": "active" if self.active else "inactive",
            }
        ]

    def wp(self, *args: str, check: bool = True) -> str:
        return json.dumps(self.options.get(args[2], {}))

    def http(self, path: str, *, cache_buster: str | None = None) -> tuple[int, str]:
        return (
            200,
            '<div class="ckyBannerTemplate"></div>' + self.tag + self.withdrawal,
        )


def test_blocked_tags_and_required_carriers_pass() -> None:
    assert not steps.consent(ConsentSite()).notes


def test_a_google_tag_that_executes_before_consent_fails() -> None:
    site = ConsentSite()
    site.tag = (
        '<script src="https://www.googletagmanager.com/gtag/js?id=G-FIXTURE"></script>'
    )
    assert any("hold every Google tag" in note for note in steps.consent(site).notes)


def test_lost_carrier_or_disconnected_analytics_fails() -> None:
    site = ConsentSite()
    site.active = False
    site.options["googlesitekit_analytics-4_settings"] = {}
    notes = steps.consent(site).notes
    assert any("must remain active" in note for note in notes)
    assert any("Analytics must be connected" in note for note in notes)


def test_missing_withdrawal_script_fails() -> None:
    site = ConsentSite()
    site.withdrawal = ""
    assert any("withdrawal adapter" in note for note in steps.consent(site).notes)
