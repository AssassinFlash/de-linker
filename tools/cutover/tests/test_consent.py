"""Deployment checks must notice consent carriers disappearing or bypassing the CMP."""

import base64
import json
import re
from pathlib import Path

from linker_cutover import plan, steps
from linker_cutover.target import CutoverError, Target


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
        self.tag = '<script type="text/plain" data-cookieyes="cookieyes-analytics" id="google_gtagjs-js" src="https://www.googletagmanager.com/gtag/js?id=G-FIXTURE"></script>'
        self.withdrawal = '<script id="linker-consent-withdrawal-js"></script>'
        self.paths: list[str] = []

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
        del cache_buster
        self.paths.append(path)
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


def test_product_pages_are_checked_with_the_homepages() -> None:
    site = ConsentSite()

    assert not steps.consent(site).notes
    assert site.paths == list(steps.CONSENT_PAGES)
    assert "/product/saj-b2-10-0-hv1/" in site.paths
    assert "/de/produkt/saj-b2-10-0-hv1/" in site.paths
    assert set(plan.VERIFY_PRODUCT_PATHS) <= set(site.paths)


def test_a_missing_google_handle_fails_even_when_the_url_is_held() -> None:
    """A rename can still be held by URL; deploy verify must say the handle is gone."""
    site = ConsentSite()
    site.tag = site.tag.replace("google_gtagjs-js", "gtag-renamed-js")

    notes = steps.consent(site).notes

    assert any("google_gtagjs handle is absent" in note for note in notes)
    assert any("/product/saj-b2-10-0-hv1/" in note for note in notes)


def _payload(source: str) -> dict[str, object]:
    match = re.search(r"'([A-Za-z0-9+/=]+)'", source)
    assert match is not None
    parsed = json.loads(base64.b64decode(match.group(1)))
    assert isinstance(parsed, dict)
    return parsed


class ReplayTarget(Target):
    """Records the write-then-verify pair configure_consent sends."""

    def __init__(self) -> None:
        super().__init__(
            label="replay",
            root="/site",
            base_url="https://de-linker.com",
            prefix=("wp",),
            shell_prefix=None,
            rsync_remote=None,
        )
        self.payloads: list[dict[str, object]] = []
        self.fail_readback = False

    def wp(self, *args: str, check: bool = True) -> str:
        del check
        payload = _payload(args[1])
        self.payloads.append(payload)
        if self.fail_readback and payload.get("write") is False:
            raise CutoverError("consent plan drift")
        return ""


def _repository(tmp_path: Path) -> Path:
    directory = tmp_path / "repo" / "tools" / "migrate"
    directory.mkdir(parents=True)
    (directory / "201-consent.php").write_text(
        "<?php\n( '__LINKER_CONSENT_PAYLOAD__' );\n", encoding="utf-8"
    )
    (directory / "201-consent.json").write_text('{"copy":{}}\n', encoding="utf-8")
    return tmp_path / "repo"


def test_configure_consent_writes_then_reads_back_and_repeats(tmp_path: Path) -> None:
    site = ReplayTarget()
    repository = _repository(tmp_path)

    first = steps.configure_consent(site, repository=repository)
    second = steps.configure_consent(site, repository=repository)

    assert first == second == ["consent: native CMP settings replayed and verified"]
    assert [payload["write"] for payload in site.payloads] == [
        True,
        False,
        True,
        False,
    ]
    assert site.payloads[0]["plan"] == site.payloads[2]["plan"]
    assert site.payloads[1] == site.payloads[3]


def test_configure_consent_fails_when_the_readback_drifts(tmp_path: Path) -> None:
    site = ReplayTarget()
    site.fail_readback = True

    try:
        steps.configure_consent(site, repository=_repository(tmp_path))
    except CutoverError as error:
        assert "drift" in str(error)
    else:
        raise AssertionError("a drifting read-back must fail the deploy step")
    assert [payload["write"] for payload in site.payloads] == [True, False]
