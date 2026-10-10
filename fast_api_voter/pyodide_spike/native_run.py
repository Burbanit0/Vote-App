"""The same dispatcher in CPython, for an exact comparison with Pyodide's output."""
import json, sys, time
sys.path.insert(0, sys.argv[1])
from pyodide_spike import handle
out, ms = {}, {}
for path, body in json.load(open(sys.argv[2])).items():
    times = []
    for _ in range(3):
        t = time.perf_counter(); status, res = handle(path, json.dumps(body)); times.append(round((time.perf_counter() - t) * 1000))
    out[path] = json.loads(res); ms[path] = [status, times]
json.dump(out, open(sys.argv[3], 'w'))
print(json.dumps(ms))
