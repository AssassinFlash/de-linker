import json, sys, time, urllib.request, uuid
qs = json.load(open(sys.argv[1]))
out = []
for lang, q in qs:
    body = {"messages": [{"role": "user", "content": q}], "locale": lang, "page": {"type": "other"}}
    req = urllib.request.Request("http://127.0.0.1:9033/wp-json/linker-ai/v1/genie/turn", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        raw = urllib.request.urlopen(req, timeout=180).read().decode()
    except Exception as e:
        raw = "ERROR " + str(e)
    out.append({"lang": lang, "q": q, "seconds": round(time.perf_counter() - t, 1), "raw": raw})
    print(len(out), lang, q[:50], out[-1]["seconds"], "s", flush=True)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
