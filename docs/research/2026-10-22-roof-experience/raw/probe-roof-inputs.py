"""Pure local roof calculations; no accounts, messages, inquiries, or model calls."""
import datetime
import json
from pathlib import Path
import urllib.request
import urllib.error
BASE='http://127.0.0.1:9323/wp-json/linker-ai/v1/engine'
RING=[[11.5882,48.1402],[11.5885,48.1402],[11.5885,48.1405],[11.5882,48.1405]]
rows=[]
for name,tilt,azimuth in [('valid',35,180),('what_comma_inputs_become',0,0),('tilt_out_of_range',91,180),('negative_facing',35,-90)]:
    payload={'polygon':RING,'tilt_deg':tilt,'azimuth_deg':azimuth,'locale':'de'}
    request=urllib.request.Request(BASE+'/roof/pack',json.dumps(payload).encode(),{'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=30) as response:
            answer=json.loads(response.read())
            rows.append({'case':name,'request':payload,'status':response.status,'answer':{k:answer.get(k) for k in ['tilt_deg','azimuth_deg','area_m2','usable','excluded_reason','modules','kwp']}})
    except urllib.error.HTTPError as error:
        rows.append({'case':name,'request':payload,'status':error.code,'answer':json.loads(error.read())})
result={'utc':datetime.datetime.now(datetime.UTC).isoformat(),'base':BASE,'scope':'Local deterministic compute only; no browser rendering proof; comma mapping separately read from RoofStep.tsx','rows':rows}
Path(__file__).with_name('roof-input-probes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
