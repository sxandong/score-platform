"""API测试 — 运行: python test_api.py"""
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000/api"

def api(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

print("=" * 50)
print("1. Login...")
r = api("POST", "/auth/login", {"username": "admin", "password": "admin123"})
assert r["code"] == 200, f"Login failed: {r}"
token = r["data"]["access_token"]
print(f"   OK - User: {r['data']['user']['real_name']}")

print("2. Get profile...")
r = api("GET", "/auth/me", token=token)
print(f"   OK - Roles: {r['data']['roles']}")

print("3. Create exam...")
r = api("POST", "/exams", {
    "name": "Test Exam",
    "exam_type": "midterm",
    "semester_id": 1,
    "grade_id": 1,
    "subjects": [
        {"subject_id": 1, "full_score": 150},
        {"subject_id": 2, "full_score": 150},
    ]
}, token=token)
assert r["code"] == 200, f"Create exam FAILED: {r}"
print(f"   OK - Exam ID={r['data']['id']}")

print("4. List exams...")
r = api("GET", "/exams", token=token)
print(f"   OK - Total: {r['meta']['total']}")

print("5. List users...")
r = api("GET", "/users", token=token)
print(f"   OK - Total: {r['meta']['total']}")

print()
print("ALL TESTS PASSED.")
