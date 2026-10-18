"""Read-only Apify deployment readback. Start, inspect status, then collect."""
import argparse
import json
import os
import pathlib
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mode', choices=('start', 'status', 'collect'))
parser.add_argument('--run')
parser.add_argument('--output', type=pathlib.Path)
args = parser.parse_args()
token = os.environ.get('APIFY_TOKEN')
if not token:
    env_file = pathlib.Path.home() / '.config/terravolt-builder/apify.env'
    for line in env_file.read_text().splitlines():
        if line.startswith('APIFY_TOKEN='):
            token = line.partition('=')[2].strip().strip('\"\'')
if not token:
    raise SystemExit('APIFY_TOKEN is required from the environment file')


def api(path, payload=None):
    request = urllib.request.Request('https://api.apify.com/v2/' + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


if args.mode == 'start':
    routes = json.loads((ROOT / 'plugins/linker-i18n/tests/fixtures/german-routes.json').read_text())
    paths = sorted({r[k] for r in routes if not r['kind'].startswith('native Woo') for k in ('old', 'new')})
    page_function = r'''async function pageFunction({sendRequest, request}) {
      const result=[];
      for (const path of request.userData.paths) {
        const r=await sendRequest({url:'https://de-linker.com'+path,followRedirect:false,http2:false,throwHttpErrors:false,retry:{limit:2}});
        const html=String(r.body); const title=html.match(/<title>([\s\S]*?)<\/title>/i)?.[1]||'';
        result.push({path,status:r.statusCode,location:r.headers.location||'',title,
          metadata:[...html.matchAll(/<(?:link|meta)\b[^>]*(?:canonical|hreflang|og:url)[^>]*>/gi)].map(m=>m[0])});
      }
      if (!request.userData.sitemaps) return result;
      const index=await sendRequest({url:'https://de-linker.com/sitemaps.xml',http2:false,throwHttpErrors:false,retry:{limit:2}});
      result.push({path:'/sitemaps.xml',status:index.statusCode,xml:index.body});
      for (const m of String(index.body).matchAll(/<loc>([^<]+)<\/loc>/g)) {
        if (!m[1].startsWith('https://de-linker.com/') || !m[1].endsWith('.xml')) throw new Error('Unexpected sitemap');
        const r=await sendRequest({url:m[1],http2:false,throwHttpErrors:false,retry:{limit:2}}); result.push({path:new URL(m[1]).pathname,status:r.statusCode,xml:r.body});
      }
      return result;
    }'''
    batches = [paths[i:i+10] for i in range(0, len(paths), 10)]
    starts = [{'url':'https://de-linker.com/de/', 'uniqueKey':f'readback-{i}', 'userData':{'paths':batch, 'sitemaps':i == 0}} for i, batch in enumerate(batches)]
    run = api('acts/apify~playwright-scraper/runs', {'startUrls':starts,
        'maxRequestsPerCrawl':len(starts), 'maxConcurrency':2, 'maxRequestRetries':1,
        'pageFunctionTimeoutSecs':120,
        'maxScrollHeightPixels':0, 'waitUntil':'domcontentloaded',
        'preNavigationHooks':'[async ({page}, options) => { options.waitUntil="domcontentloaded"; }]',
        'pageFunction':page_function})['data']
    print(json.dumps({'run':run['id'], 'dataset':run['defaultDatasetId'], 'status':run['status']}))
else:
    if not args.run:
        parser.error('--run is required')
    run = api('actor-runs/' + args.run)['data']
    if args.mode == 'status':
        print(json.dumps({'run':run['id'], 'status':run['status']}))
    else:
        if run['status'] != 'SUCCEEDED':
            raise SystemExit('Run has not succeeded: ' + run['status'])
        if not args.output:
            parser.error('--output is required')
        data = api('datasets/' + run['defaultDatasetId'] + '/items?clean=true')
        routes = json.loads((ROOT / 'plugins/linker-i18n/tests/fixtures/german-routes.json').read_text())
        required = {r[k] for r in routes if not r['kind'].startswith('native Woo') for k in ('old', 'new')}
        missing = required - {r.get('path') for r in data}
        if missing or not data or any(not r.get('status') for r in data):
            raise SystemExit('Incomplete readback; missing paths: ' + str(sorted(missing)))
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'run':run['id'], 'items':len(data), 'output':str(args.output)}))
