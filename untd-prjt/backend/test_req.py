import urllib.request, json

data = json.dumps({
    "code": "print('hello')",
    "language": "python",
    "analysis_options": {"profile": "fast"}
}).encode("utf-8")

req = urllib.request.Request("http://127.0.0.1:8000/api/analyze", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode("utf-8"))
