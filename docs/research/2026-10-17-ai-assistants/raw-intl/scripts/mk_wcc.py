"""Build an apify/website-content-crawler input that fetches exactly the listed URLs (depth 0).

Usage: python3 -I mk_wcc.py <urls.txt> <out.json> [crawlerType] [proxyGroup] [htmlTransformer]
crawlerType: playwright:adaptive (default) | playwright:firefox | cheerio
proxyGroup: '' (datacenter) | RESIDENTIAL
htmlTransformer: readableText (default) | none (keeps list items that readability drops)
"""
import json
import pathlib
import sys

urls = [u.strip() for u in pathlib.Path(sys.argv[1]).read_text().splitlines() if u.strip() and not u.startswith("#")]
crawler = sys.argv[3] if len(sys.argv) > 3 else "playwright:adaptive"
group = sys.argv[4] if len(sys.argv) > 4 else ""
transformer = sys.argv[5] if len(sys.argv) > 5 else "readableText"
proxy = {"useApifyProxy": True}
if group:
    proxy["apifyProxyGroups"] = [group]
body = {
    "startUrls": [{"url": u} for u in urls],
    "crawlerType": crawler,
    "maxCrawlDepth": 0,
    "maxCrawlPages": len(urls) + 5,
    "maxResults": len(urls) + 5,
    "useSitemaps": False,
    "respectRobotsTxtFile": False,
    "removeCookieWarnings": True,
    "htmlTransformer": transformer,
    "readableTextCharThreshold": 100,
    "saveMarkdown": True,
    "saveHtml": False,
    "proxyConfiguration": proxy,
    "maxConcurrency": 8,
    "requestTimeoutSecs": 60,
    "dynamicContentWaitSecs": 10,
    "removeElementsCssSelector": "nav, footer, header, script, style, noscript, svg, img, picture, [role=\"banner\"], [role=\"contentinfo\"], [role=\"navigation\"], [aria-modal=\"true\"]",
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(body, indent=1))
print(len(urls), "urls", crawler, group or "datacenter", transformer)
