import requests

SUPABASE_URL = "https://iblmxloizfpxmucypquv.supabase.co"
SUPABASE_KEY = "sb_secret_zSYRfcAOjwdwnVwu9VoRgw_rbafuTBh"

url = f"{SUPABASE_URL}/rest/v1/documents?status=eq.failed"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

data = {
    "status": "awaiting_fallback_parse",
    "error_message": "Ready to track live!"
}

resp = requests.patch(url, headers=headers, json=data)
print(resp.status_code, resp.text)
