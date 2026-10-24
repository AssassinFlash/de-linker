"""Exact safe pinned-build INPUT plus one private intent correlation value.

The 51 observed safe defaults are data from the Apify primary capture at
2026-10-24-weather-transport/raw/weather-effective-input-baseline.json,
SHA256 361ce26601d9028ac3f76712f7be4977b99fc724c6a77054912ccfdd9a0cf5ab.
The immutable code snapshot retains this baseline; no runtime research-file
lookup, arbitrary future default or customer header is trusted.
"""

from __future__ import annotations

import re

from .canonical import Json, Object, decode_object, encode
from .weather_fetch_errors import WeatherResponseInvalid
from .weather_fetch_plan import WeatherFetchPlan

_BASELINE_JSON = b'{"aggressivePrune":false,"blockMedia":false,"clickElementsCssSelector":"[aria-expanded=\\"false\\"]","clientSideMinChangePercentage":15,"crawlerType":"cheerio","customHttpHeaders":{"Accept":"application/json","User-Agent":"python-requests/2.32.5"},"debugLog":false,"debugMode":false,"dynamicContentWaitSecs":10,"excludeUrlGlobs":[],"expandIframes":true,"htmlTransformer":"none","ignoreCanonicalUrl":false,"ignoreHttpsErrors":false,"includeUrlGlobs":[],"initialConcurrency":0,"keepElementsCssSelector":"","keepUrlFragments":false,"maxConcurrency":1,"maxCrawlDepth":0,"maxCrawlPages":1,"maxRequestRetries":1,"maxResults":9999999,"maxScrollHeightPixels":5000,"maxSessionRotations":10,"minFileDownloadSpeedKBps":1,"onlyCrawlPagesModifiedSince":"","pageFunction":"","proxyConfiguration":{"useApifyProxy":true},"readableTextCharThreshold":100,"removeCookieWarnings":true,"removeElementsCssSelector":"nav, footer, script, style, noscript, svg, img[src^=\'data:\'],\\n[role=\\"alert\\"],\\n[role=\\"banner\\"],\\n[role=\\"dialog\\"],\\n[role=\\"alertdialog\\"],\\n[role=\\"region\\"][aria-label*=\\"skip\\" i],\\n[aria-modal=\\"true\\"]","renderingTypeDetectionPercentage":10,"requestTimeoutSecs":90,"respectRobotsTxtFile":false,"reuseStoredDetectionResults":false,"saveContentTypes":"application/json","saveFiles":false,"saveHtml":true,"saveHtmlAsFile":false,"saveMarkdown":true,"saveScreenshots":false,"saveText":true,"signHttpRequests":false,"softWaitForSelector":"","startUrls":[{"url":"https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=52.52&lon=13.405&startyear=2005&endyear=2023&usehorizon=0&outputformat=json"}],"storeSkippedUrls":false,"summarize":false,"useLlmsTxt":false,"useSitemaps":false,"waitForSelector":""}'


def submission(plan: WeatherFetchPlan, nonce: str) -> Object:
    if not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise WeatherResponseInvalid("private weather intent correlation required")
    result = plan.actor_input()
    # The retained successful primary request supplied this explicit header.
    # The first trial omitted it and received 200/text-html; a separate trial
    # with it succeeded. Those observations do not establish header causality.
    result["customHttpHeaders"] = {
        "Accept": "application/json",
        "User-Agent": "python-requests/2.32.5",
    }
    result["startUrls"] = [
        {"url": plan.request.url, "userData": {"linker_weather_intent": nonce}}
    ]
    return result


def checked_effective_input(plan: WeatherFetchPlan, nonce: str, value: Json) -> Object:
    expected = decode_object(_BASELINE_JSON)
    expected.update(submission(plan, nonce))
    if not isinstance(value, dict) or encode(value) != encode(expected):
        # Do not persist/log arbitrary returned INPUT: it can contain hooks,
        # credentials, proxy URLs or temporary access fields in a changed build.
        raise WeatherResponseInvalid(
            "effective INPUT differs from the pinned safe submission"
        )
    return value
