"""Read public local HTML, retaining tool anchors only; no cookies or nonces saved."""
import datetime
import json
from html.parser import HTMLParser
from pathlib import Path
import urllib.request

BASE = 'http://127.0.0.1:9323'
PATHS = ['/', '/de/', '/products/', '/de/produkte/', '/for-installer/', '/de/fuer-installateur/', '/blog/', '/de/blog/', '/solution-configurator/', '/de/loesungskonfigurator/', '/product/goodwe-gw60k-sts-g10/', '/de/produkt/goodwe-gw60k-sts-g10/', '/solution/', '/de/loesung/', '/solution/residential-storage/', '/de/loesung/heimspeicher/', '/solution/commercial-storage/', '/de/loesung/gewerbespeicher/', '/hybrid-inverter-vs-ac-coupled-storage/', '/de/hybridwechselrichter-vs-ac-speicher/']

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = {'href':dict(attrs).get('href',''), 'text':[]}
    def handle_data(self, text):
        if self.current is not None:
            self.current['text'].append(text)
    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.current['text'] = ' '.join(' '.join(self.current['text']).split())
            row = self.current
            self.current = None
            if any(term in (row['href']+' '+row['text']).lower() for term in ['configurator','konfigurator','step=roof','roof detail','dachdetail','design-canvas']):
                self.links.append(row)

def run():
    rows = []
    for path in PATHS:
        try:
            with urllib.request.urlopen(BASE+path,timeout=30) as response:
                parser = Anchors()
                parser.feed(response.read().decode('utf-8','replace'))
                rows.append({'path':path,'status':response.status,'final_url':response.url,'links':parser.links})
        except Exception as error:
            rows.append({'path':path,'error':str(error)})
    return {'utc':datetime.datetime.now(datetime.UTC).isoformat(),'base':BASE,'identity':'cookie-free HTTP client; HTML anchors, not browser visibility proof','rows':rows}

if __name__ == '__main__':
    result = run()
    Path(__file__).with_name('entry-links.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'pages':len(result['rows']),'rows':[{'path':r['path'],'status':r.get('status'),'tool_links':len(r.get('links',[])),'error':r.get('error')} for r in result['rows']]},ensure_ascii=False,indent=2))
