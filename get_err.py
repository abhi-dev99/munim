import urllib.request
import json
req = urllib.request.Request('http://localhost:8000/api/v1/reports/generate/6d123264-9325-4a37-b769-274834a04085?month=6&year=2026', method='POST')
try:
    res = urllib.request.urlopen(req)
    print(res.read())
except Exception as e:
    print(e.read().decode())
